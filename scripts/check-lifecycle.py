"""Check deletion dependencies and stable desired state across readiness changes."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
XR = {
    "apiVersion": "workloads.hops.ops.com.ai/v1alpha1", "kind": "WebService",
    "metadata": {"name": "echo", "namespace": "preview-67"},
    "spec": {"image": "hashicorp/http-echo:1.0.0", "port": 5678,
             "auth": {"enabled": True}},
}
PLATFORM = {
    "apiVersion": "apiextensions.crossplane.io/v1beta1", "kind": "EnvironmentConfig",
    "metadata": {"name": "webservice-default"},
    "data": {
        "baseDomain": "example.com",
        "privateGateway": {"namespace": "istio-ingress", "service": "private.example.com"},
        "auth": {"issuerURL": "https://auth.example.com", "projectId": "test-project",
                 "allowedGroups": ["developer"], "caBundle": "public-test-ca"},
    },
}
AUTH_EDGES = {("service", "client-secret"), ("service", "cookie"),
              ("client-secret", "oidc"), ("cookie", "cookie-generator")}
ROUTE_EDGES = {("route", "gateway"), ("route", "backend-grant"), ("route", "service")}
TLS_EDGES = {("gateway", "certificate"), ("gateway", "tls-grant"),
             ("certificate", "tls-secret")}
CA_EDGE = {("service", "issuer-ca")}


def render(directory, xr, platform, observed=()):
    (directory / "xr.json").write_text(json.dumps(xr))
    (directory / "platform.json").write_text(json.dumps(platform))
    (directory / "observed.yaml").write_text(yaml.safe_dump_all(list(observed)))
    relative = directory.relative_to(ROOT)
    output = subprocess.check_output([
        "up", "composition", "render", "--quiet", "--xrd=apis/webservices/definition.yaml",
        "apis/webservices/composition.yaml", str(relative / "xr.json"),
        "--extra-resources=" + str(relative / "platform.json"),
        "--observed-resources=" + str(relative / "observed.yaml"),
    ], cwd=ROOT, text=True, timeout=180)
    docs = [doc for doc in yaml.safe_load_all(output) if doc and doc["kind"] in ("Object", "Oidc", "Usage")]
    for doc in docs:
        native = doc.get("spec", {}).get("forProvider", {}).get("manifest", {})
        if native.get("apiVersion") != "serving.knative.dev/v1":
            continue
        containers = native["spec"]["template"]["spec"]["containers"]
        serving = next(container for container in containers if container.get("ports"))
        assert all(env["name"] != "PORT" for env in serving.get("env", [])), "Knative reserves PORT on its request container"
        if serving["name"] == "login":
            app = next(container for container in containers if container["name"] == "app")
            assert any(env["name"] == "PORT" for env in app["env"]), "The non-serving application needs its own port"
    return docs


def managed(docs):
    return {doc["metadata"]["name"]: doc for doc in docs if doc["kind"] != "Usage"}


def observe_ready(docs):
    observed = copy.deepcopy(list(managed(docs).values()))
    for doc in observed:
        doc["metadata"]["namespace"] = "preview-67"
        key = doc["metadata"]["annotations"]["crossplane.io/composition-resource-name"]
        doc["metadata"]["annotations"]["crossplane.io/composition-resource-name"] = key
        doc["metadata"]["annotations"]["gotemplating.fn.crossplane.io/composition-resource-name"] = key
        doc["status"] = {"conditions": [{"type": "Ready", "status": "True"}]}
        if doc["kind"] == "Object":
            native = copy.deepcopy(doc["spec"]["forProvider"]["manifest"])
            native["metadata"]["uid"] = "fixture-" + key
            if key == "service":
                native["status"] = {"url": "https://echo.preview-67.example.com",
                                    "latestReadyRevisionName": "echo-00001"}
            doc["status"]["atProvider"] = {"manifest": native}
    return observed


def edges(docs):
    result = set()
    for doc in docs:
        if doc["kind"] != "Usage":
            continue
        spec = doc["spec"]
        assert spec["replayDeletion"] is True
        by, of = (spec[field]["resourceRef"]["name"] for field in ("by", "of"))
        edge = (by.removeprefix("echo-"), of.removeprefix("echo-"))
        assert edge not in result, ("duplicate Usage", edge)
        result.add(edge)
        assert by in managed(docs) and of in managed(docs), ("unknown dependency", edge)
        for field in ("by", "of"):
            target = managed(docs)[spec[field]["resourceRef"]["name"]]
            assert (spec[field]["apiVersion"], spec[field]["kind"]) == (target["apiVersion"], target["kind"])
    # A cycle would prevent garbage collection from making progress.
    def visit(node, path):
        assert node not in path, ("cyclic deletion dependency", path, node)
        for by, of in result:
            if by == node:
                visit(of, path | {node})
    for by, _ in result:
        visit(by, set())
    return result


(ROOT / ".tmp").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT / ".tmp", prefix="lifecycle-") as temporary:
    directory = Path(temporary)
    bootstrap = render(directory, XR, PLATFORM)
    assert not edges(bootstrap), "bootstrap must not lock resources that have never become ready"
    observed = observe_ready(bootstrap)
    ready = render(directory, XR, PLATFORM, observed)
    expected = AUTH_EDGES | ROUTE_EDGES | TLS_EDGES | CA_EDGE
    assert edges(ready) == expected
    assert len(managed(ready)) == 12
    repeated = render(directory, XR, PLATFORM, observed)
    assert managed(repeated) == managed(ready), "identical observations changed desired managed resources"
    assert edges(repeated) == expected
    print("PASS full authenticated TLS graph is acyclic, typed and stable", flush=True)

    unready = copy.deepcopy(observed)
    for doc in unready:
        if doc["metadata"]["name"] in ("echo-service", "echo-oidc"):
            doc["status"]["conditions"][0]["status"] = "False"
    dipped = render(directory, XR, PLATFORM, unready)
    assert managed(dipped) == managed(ready), "a readiness dip deleted or replaced a managed resource"
    assert edges(dipped) == {edge for edge in expected if "service" not in edge and "oidc" not in edge}
    print("PASS readiness dips release only applicable locks, retaining workload and credentials", flush=True)

    for label, exposure, auth, tls, expected in [
        ("public auth", "public", True, True, AUTH_EDGES),
        ("private HTTP", "private", False, False, ROUTE_EDGES),
        ("cluster", "cluster", False, False, set()),
    ]:
        xr, platform = copy.deepcopy(XR), copy.deepcopy(PLATFORM)
        xr["spec"].update(exposure=exposure, auth={"enabled": auth})
        platform["data"]["auth"].pop("caBundle")
        platform["data"]["tls"] = {"enabled": tls}
        initial = render(directory, xr, platform)
        final = render(directory, xr, platform, observe_ready(initial))
        assert edges(final) == expected, label
        print("PASS " + label + " has only its applicable dependencies", flush=True)

    shared = copy.deepcopy(PLATFORM)
    shared["data"]["privateGateway"]["shared"] = {"name": "private-platform", "sectionName": "https-preview"}
    shared_edges = AUTH_EDGES | CA_EDGE | {("route", "backend-grant"), ("route", "service")}
    initial = render(directory, XR, shared)
    final = render(directory, XR, shared, observe_ready(initial))
    assert edges(final) == shared_edges
    objects = {d["metadata"]["annotations"]["crossplane.io/composition-resource-name"]: d for d in final if d["kind"] == "Object"}
    assert not {"gateway", "certificate", "tls-secret", "tls-grant"} & objects.keys()
    assert objects["shared-gateway"]["spec"]["managementPolicies"] == ["Observe"]
    query = objects["shared-gateway"]["spec"]["readiness"]["celQuery"]
    assert 'https-preview' in query and "l.protocol == 'HTTPS'" in query and "ResolvedRefs" in query
    assert objects["shared-gateway"]["spec"]["forProvider"]["manifest"] == {
        "apiVersion": "gateway.networking.k8s.io/v1", "kind": "Gateway",
        "metadata": {"name": "private-platform", "namespace": "istio-ingress"}}
    route = objects["route"]["spec"]["forProvider"]["manifest"]
    host = "10-preview-67-echo.example.com"
    assert route["spec"]["hostnames"] == [host]
    assert route["spec"]["parentRefs"] == [{"name": "private-platform", "namespace": "istio-ingress", "sectionName": "https-preview"}]
    assert route["metadata"]["annotations"]["external-dns.alpha.kubernetes.io/controller"] == "platform-wildcard"
    oidc = next(d for d in final if d["kind"] == "Oidc")
    assert "https://" + host + "/oauth2/callback" in str(oidc)
    dipped = observe_ready(initial)
    for d in dipped:
        d["status"]["conditions"][0]["status"] = "False"
    assert managed(render(directory, XR, shared, dipped)) == managed(final)
    print("PASS shared ingress observes platform ownership, isolates hosts, disables DNS and retains resources during readiness dips", flush=True)

    for name, namespace, explicit in [("x" * 63, "preview-67", None), ("echo", "other-preview", None), ("gateway", "preview-67", "preview-67.example.com")]:
        xr = copy.deepcopy(XR)
        xr["metadata"].update(name=name, namespace=namespace)
        if explicit:
            xr["spec"]["hostname"] = explicit
        docs = render(directory, xr, shared)
        route = next(d["spec"]["forProvider"]["manifest"] for d in docs if d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == "route")
        label = route["spec"]["hostnames"][0].removesuffix(".example.com")
        assert len(label) <= 63 and "." not in label
        assert label == namespace or label.startswith(str(len(namespace)) + "-" + namespace + "-")
    print("PASS long service names, separate namespaces and explicit primary hostnames remain single-label and namespace-owned", flush=True)

    # Mode changes must never elevate a shared observer into an owning resource.
    from_owned = render(directory, XR, shared, observed)
    shared_key = next(d for d in from_owned if d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == "shared-gateway")
    assert shared_key["spec"]["managementPolicies"] == ["Observe"]
    assert not any(d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == "gateway" for d in from_owned)
    from_shared = render(directory, XR, PLATFORM, observe_ready(render(directory, XR, shared)))
    owning_key = next(d for d in from_shared if d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == "gateway")
    assert owning_key["spec"]["forProvider"]["manifest"]["metadata"]["name"] == "echo-preview-67"
    assert not any(d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == "shared-gateway" for d in from_shared)
    print("PASS profile transitions use separate observe-only and owning Gateway identities", flush=True)

    for last_label, explicit, expected_length in [(42, None, 253), (44, True, 247)]:
        platform = copy.deepcopy(shared)
        domain = ".".join(["a" * 63] * 3 + ["a" * last_label])
        platform["data"]["baseDomain"] = domain
        xr = copy.deepcopy(XR)
        if explicit:
            xr["spec"]["hostname"] = "preview-67." + domain
        docs = render(directory, xr, platform)
        route = next(d["spec"]["forProvider"]["manifest"] for d in docs if d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == "route")
        assert len(route["spec"]["hostnames"][0]) == expected_length
    print("PASS complete DNS hostname boundary accepts valid generated and explicit hosts", flush=True)

    external = copy.deepcopy(XR)
    external["spec"]["auth"]["existingClient"] = {
        "clientSecretRef": {"name": "workforce-client"},
        "cookieSecretRef": {"name": "workforce-session"},
    }
    platform = copy.deepcopy(PLATFORM)
    platform["data"]["auth"].pop("projectId")
    platform["data"]["auth"]["requireExistingClient"] = True
    initial = render(directory, external, platform)
    final = render(directory, external, platform, observe_ready(initial))
    assert not any(d["kind"] == "Oidc" for d in final), "external mode provisioned a client"
    keys = {d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] for d in final}
    assert not {"oidc", "client-secret", "cookie", "cookie-generator"} & keys
    assert edges(final) == ROUTE_EDGES | TLS_EDGES | CA_EDGE
    native = next(d["spec"]["forProvider"]["manifest"] for d in final if d["metadata"]["name"] == "echo-service")
    login = next(c for c in native["spec"]["template"]["spec"]["containers"] if c["name"] == "login")
    refs = {e["name"]: e["valueFrom"]["secretKeyRef"] for e in login["env"]}
    assert refs == {
        "OAUTH2_PROXY_CLIENT_ID": {"name": "workforce-client", "key": "client_id", "optional": False},
        "OAUTH2_PROXY_CLIENT_SECRET": {"name": "workforce-client", "key": "client_secret", "optional": False},
        "OAUTH2_PROXY_COOKIE_SECRET": {"name": "workforce-session", "key": "cookie_secret", "optional": False},
    }
    assert "--cookie-name=_hops_echo_external" in login["args"]
    assert "--allowed-group=developer" in login["args"]
    assert "--code-challenge-method=S256" in login["args"]
    assert "--oidc-issuer-url=https://auth.example.com" in login["args"]
    assert not any("skip-jwt-bearer" in a for a in login["args"])
    # The existing TLS Secret observer remains necessary for private ingress.
    secret_objects = {d["metadata"]["annotations"]["crossplane.io/composition-resource-name"]
                      for d in final if d.get("spec", {}).get("forProvider", {}).get("manifest", {}).get("kind") == "Secret"}
    assert secret_objects <= {"tls-secret"}, "external mode created an authentication Secret"
    # Switching from managed observations must not reintroduce owning resources.
    migrated = render(directory, external, platform, observed)
    old_auth_keys = {"oidc", "client-secret", "cookie", "cookie-generator"}
    retained = {d["metadata"]["annotations"]["crossplane.io/composition-resource-name"]: d for d in migrated if d["metadata"]["annotations"]["crossplane.io/composition-resource-name"] in old_auth_keys}
    assert retained.keys() == old_auth_keys
    for key, d in retained.items():
        assert d["spec"]["managementPolicies"] == ["Observe", "Update", "LateInitialize"]
        old = next(o for o in observed if o["metadata"]["annotations"]["crossplane.io/composition-resource-name"] == key)
        assert {k: v for k, v in d["spec"].items() if k != "managementPolicies"} == {k: v for k, v in old["spec"].items() if k != "managementPolicies"}
    unready_legacy = copy.deepcopy(observed)
    for d in unready_legacy:
        d["status"]["conditions"][0]["status"] = "False"
    assert managed(render(directory, external, platform, unready_legacy)) == managed(migrated)
    retired = copy.deepcopy(external)
    retired["spec"]["auth"]["existingClient"]["retainManagedResources"] = False
    assert managed(render(directory, retired, platform, observed)) == managed(final)
    custom = copy.deepcopy(external)
    custom["spec"]["auth"]["existingClient"]["clientSecretRef"].update(clientIdKey="app_id", clientSecretKey="app_secret")
    custom["spec"]["auth"]["existingClient"]["cookieSecretRef"]["key"] = "session"
    custom_docs = render(directory, custom, platform)
    custom_native = next(d["spec"]["forProvider"]["manifest"] for d in custom_docs if d["metadata"]["name"] == "echo-service")
    custom_login = next(c for c in custom_native["spec"]["template"]["spec"]["containers"] if c["name"] == "login")
    assert {e["valueFrom"]["secretKeyRef"]["key"] for e in custom_login["env"]} == {"app_id", "app_secret", "session"}
    print("PASS external registration has no local identity/Secret ownership, requires fresh sessions, preserves private enforcement and maps Secret keys", flush=True)

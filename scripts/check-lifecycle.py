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

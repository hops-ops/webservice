# /// script
# dependencies = ["pyyaml"]
# ///
"""Exercise the installed source package on an explicitly selected Hops local cluster."""
import argparse
import base64
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.parse

import yaml

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--context", required=True)
parser.add_argument("--issuer-url", default=os.environ.get("WEBSERVICE_TEST_ISSUER_URL"),
                    help="existing local Zitadel HTTPS issuer; or set WEBSERVICE_TEST_ISSUER_URL")
args = parser.parse_args()
if args.context not in ("kind-hops", "colima"):
    parser.error("this fixture targets kind-hops or colima only")
if not args.issuer_url:
    parser.error("set --issuer-url or WEBSERVICE_TEST_ISSUER_URL to the existing local Zitadel HTTPS issuer")
try:
    issuer = urllib.parse.urlsplit(args.issuer_url)
    valid_issuer = (issuer.scheme == "https" and issuer.hostname and issuer.port in (None, 443)
                    and not issuer.username and not issuer.password
                    and issuer.path in ("", "/") and not issuer.query and not issuer.fragment)
except ValueError:
    valid_issuer = False
if not valid_issuer:
    parser.error("the local issuer fixture requires an HTTPS origin on port 443")
ISSUER_URL = args.issuer_url.rstrip("/")
ISSUER_HOST = issuer.hostname
CTX = args.context
NAMESPACES = ("websvc-54", "websvc-67")
forwards = []
owned_namespaces = []
cleanup_errors = []
platform_written = False

def kubectl(*parts, doc=None):
    return subprocess.check_output(
        ["kubectl", "--context", CTX, *parts],
        input=None if doc is None else json.dumps(doc).encode(),
        stderr=subprocess.STDOUT,
    )

def get(kind, name=None, namespace=None):
    parts = ["get", *kind.split()]
    if name:
        parts.append(name)
    if namespace:
        parts.extend(["-n", namespace])
    return json.loads(kubectl(*parts, "-o", "json"))

def apply(doc):
    kubectl("apply", "-f", "-", doc=doc)

def apply_file(name):
    kubectl("apply", "-f", str(ROOT / "local" / name))

def wait(check, label, timeout=180):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            if check():
                print("PASS", label, flush=True)
                return
        except (subprocess.CalledProcessError, KeyError, ssl.SSLError, OSError):
            pass
        time.sleep(1)
    raise AssertionError("Timed out: " + label)

def ready(kind, name, namespace):
    obj = get(kind, name, namespace)
    return any(c["type"] == "Ready" and c["status"] == "True"
               and (c.get("observedGeneration") == obj["metadata"]["generation"]
                    if kind == "webservice" else c.get("observedGeneration", obj["metadata"]["generation"]) == obj["metadata"]["generation"])
               for c in obj.get("status", {}).get("conditions", []))

def forward(name, target_port, namespace="istio-ingress", resource="svc"):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        ["kubectl", "--context", CTX, "-n", namespace, "port-forward",
         resource + "/" + name, str(port) + ":" + str(target_port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    forwards.append(process)
    wait(lambda: socket.create_connection(("127.0.0.1", port), timeout=1).close() is None,
         "isolated port forward", timeout=20)
    return port

def request(port, hostname, tls_context=None, path="/", extra_headers=None):
    sock = socket.create_connection(("127.0.0.1", port), timeout=30)
    if tls_context:
        sock = tls_context.wrap_socket(sock, server_hostname=hostname)
    try:
        headers = "".join(key + ": " + value + "\r\n" for key, value in (extra_headers or {}).items())
        sock.sendall(("GET " + path + " HTTP/1.1\r\nHost: " + hostname + "\r\n" + headers + "Connection: close\r\n\r\n").encode())
        response = http.client.HTTPResponse(sock)
        response.begin()
        return response.status, {key.lower(): value for key, value in response.getheaders()}, response.read()
    finally:
        sock.close()

def host(name, namespace):
    return f"{name}.{namespace}.webservice.localhost"

def absent(kind, namespace):
    return not get(kind, namespace=namespace)["items"]

# Refuse to mutate an existing namespace or shared Knative configuration.
for ns in NAMESPACES:
    assert not kubectl("get", "namespace", ns, "--ignore-not-found", "-o", "json").strip(), "fixture namespace already exists: " + ns
assert not kubectl("get", "environmentconfig", "webservice-local", "--ignore-not-found", "-o", "json").strip(), "fixture platform already exists"
for config in yaml.safe_load_all((ROOT / "local/knative-config.yaml").read_text()):
    current = get("configmap", config["metadata"]["name"], "knative-serving")
    assert all(current.get("data", {}).get(key) == value for key, value in config["data"].items()), "prepare isolated Knative prerequisites first: " + config["metadata"]["name"]

def cleanup_step(label, operation):
    try:
        operation()
        return True
    except Exception as error:
        cleanup_errors.append(label)
        print("FAIL cleanup", label, type(error).__name__, flush=True)
        return False

with tempfile.TemporaryDirectory(prefix="webservice-smoke-") as tmp:
    try:
        for ns in NAMESPACES:
            kubectl("create", "-f", "-", doc={"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": ns, "labels": {"hops.ops.com.ai/webservice-test": "true"}}})
            owned_namespaces.append(ns)
        apply_file("prerequisites.yaml")
        apply_file("tls.yaml")
        for resource in yaml.safe_load_all((ROOT / "local/issuer.yaml").read_text().replace("auth.example.localhost", ISSUER_HOST)):
            apply(resource)
        wait(lambda: ready("certificate.cert-manager.io", "webservice-ca", "cert-manager"), "local CA")
        ca = base64.b64decode(get("secret", "webservice-ca", "cert-manager")["data"]["tls.crt"])
        ca_path = Path(tmp) / "ca.pem"
        ca_path.write_bytes(ca)
        tls = ssl.create_default_context(cafile=str(ca_path))
        apply_file("auth-project.yaml")
        wait(lambda: ready("project.project.zitadel.m.crossplane.io", "webservice-local-test", "websvc-67"), "isolated identity project")
        project_id = get("project.project.zitadel.m.crossplane.io", "webservice-local-test", "websvc-67")["status"]["atProvider"]["id"]
        platform = yaml.safe_load((ROOT / "local/platform.yaml").read_text())
        platform["data"]["tls"]["enabled"] = True
        platform["data"]["auth"].update(issuerURL=ISSUER_URL, projectId=project_id, caBundle=ca.decode())
        platform_written = True
        apply(platform)
        apply_file("webservices.yaml")
        login = yaml.safe_load((ROOT / "local/authenticated.yaml").read_text())
        gateway_ip = get("svc", "webservice-private-istio", "istio-ingress")["spec"]["clusterIP"]
        login["spec"]["podTemplate"]["hostAliases"] = [{"ip": gateway_ip, "hostnames": [ISSUER_HOST]}]
        apply(login)
        for ns, names in [("websvc-54", ["echo"]), ("websvc-67", ["echo", "api", "gateway", "login"])]:
            for name in names:
                wait(lambda ns=ns, name=name: ready("webservice", name, ns), "ready " + ns + "/" + name)
        # A healthy login proxy must not hide an unready application container.
        cookie_before = get("secret", "login-cookie", "websvc-67")["data"]
        previous_revision = get("ksvc", "login", "websvc-67")["status"]["latestReadyRevisionName"]
        def patch_probe(port):
            kubectl("-n", "websvc-67", "patch", "webservice", "login", "--type=merge", "-p", json.dumps({"spec": {"probes": {"readiness": {"tcpSocket": {"port": port}}}}}))
        blocked_pod = {}
        def app_probe_blocks():
            revision = get("ksvc", "login", "websvc-67")["status"]["latestCreatedRevisionName"]
            if revision == previous_revision:
                return False
            for pod in get("pods -l serving.knative.dev/revision=" + revision, namespace="websvc-67")["items"]:
                statuses = {c["name"]: c["ready"] for c in pod.get("status", {}).get("containerStatuses", [])}
                if statuses.get("login") is True and statuses.get("app") is True and statuses.get("queue-proxy") is False:
                    blocked_pod["name"] = pod["metadata"]["name"]
                    blocked_pod["revision"] = revision
                    return get("ksvc", "login", "websvc-67")["status"].get("latestReadyRevisionName") != revision
            return False
        patch_probe(5679)
        wait(app_probe_blocks, "login proxy cannot hide application probe failure")
        proxy_probe = forward(blocked_pod["name"], 4180, "websvc-67", "pod")
        app_probe = forward(blocked_pod["name"], 5678, "websvc-67", "pod")
        queue_probe = forward(blocked_pod["name"], 8012, "websvc-67", "pod")
        wait(lambda: request(proxy_probe, "localhost", path="/ready")[0] == 200, "login proxy itself is healthy")
        assert request(app_probe, "localhost")[0] == 200
        queue_status = request(queue_probe, "localhost", extra_headers={"K-Network-Probe": "queue", "User-Agent": "kube-probe/webservice-smoke"})[0]
        assert queue_status == 503, "aggregate readiness status: " + str(queue_status)
        print("PASS aggregate readiness rejects failing application probe", flush=True)
        patch_probe(5678)
        def app_recovered():
            status = get("ksvc", "login", "websvc-67")["status"]
            return ready("webservice", "login", "websvc-67") and status.get("latestCreatedRevisionName") != blocked_pod["revision"] and status.get("latestCreatedRevisionName") == status.get("latestReadyRevisionName")
        wait(app_recovered, "application readiness recovery")
        assert get("secret", "login-cookie", "websvc-67")["data"] == cookie_before
        print("PASS cookie stable across readiness changes", flush=True)
        private = forward("webservice-private-istio", 443)
        public_http = forward("platform-istio", 80)
        public = forward("platform-istio", 443)
        for ns in NAMESPACES:
            code, _, body = request(private, host("echo", ns), tls)
            assert code == 200 and ("echo-" + ns).encode() in body
            assert request(public_http, host("echo", ns))[0] == 404
        print("PASS independent private previews and public isolation", flush=True)
        assert request(public_http, host("api", "websvc-67"))[0] == 404
        assert get("webservice", "api", "websvc-67")["status"]["url"].endswith("svc.cluster.local")
        assert request(public, host("gateway", "websvc-67"), tls)[0] == 200
        code, headers, _ = request(private, host("login", "websvc-67"), tls)
        assert code == 302
        location = urllib.parse.urlsplit(headers["location"])
        assert location.scheme == issuer.scheme and location.netloc == issuer.netloc
        query = urllib.parse.parse_qs(location.query)
        assert query["redirect_uri"] == ["https://" + host("login", "websvc-67") + "/oauth2/callback"]
        assert query["code_challenge_method"] == ["S256"]
        assert "Secure" in headers.get("set-cookie", "")
        print("PASS OIDC client, verified issuer, HTTPS callback, PKCE and secure cookie", flush=True)
        for exposure in ["public", "private"]:
            kubectl("-n", "websvc-54", "patch", "webservice", "echo", "--type=merge", "-p", json.dumps({"spec": {"exposure": exposure}}))
            wait(lambda: ready("webservice", "echo", "websvc-54"), "exposure " + exposure)
            port = public if exposure == "public" else private
            wait(lambda: request(port, host("echo", "websvc-54"), tls)[0] == 200, "trusted TLS after " + exposure)
            assert request(private, host("echo", "websvc-67"), tls)[0] == 200
        assert request(public_http, host("echo", "websvc-54"))[0] == 404
        wait(lambda: absent("pods -l serving.knative.dev/service=echo", "websvc-54"), "scale to zero", timeout=130)
        start = time.monotonic()
        assert request(private, host("echo", "websvc-54"), tls)[0] == 200
        print("PASS trusted private cold start in", round(time.monotonic() - start, 3), "seconds", flush=True)
    finally:
        for process in forwards:
            cleanup_step("stop port forward", process.terminate)
        for process in forwards:
            if not cleanup_step("wait for port forward", lambda process=process: process.wait(timeout=10)):
                cleanup_step("kill port forward", process.kill)
        managed_clean = set()
        for ns in owned_namespaces:
            deleted = cleanup_step("request workload teardown " + ns, lambda ns=ns: kubectl("-n", ns, "delete", "webservices", "--all", "--wait=false"))
            if deleted and cleanup_step("managed teardown " + ns, lambda ns=ns: wait(
                lambda: absent("webservices", ns) and absent("objects.kubernetes.m.crossplane.io", ns)
                and absent("oidcs.application.zitadel.m.crossplane.io", ns), "managed teardown " + ns)):
                managed_clean.add(ns)
        project_clean = False
        if "websvc-67" in managed_clean:
            project_clean = cleanup_step("delete identity project", lambda: kubectl("-n", "websvc-67", "delete", "project.project.zitadel.m.crossplane.io", "webservice-local-test", "--ignore-not-found", "--wait=false"))
            if project_clean:
                project_clean = cleanup_step("identity project teardown", lambda: wait(lambda: absent("project.project.zitadel.m.crossplane.io", "websvc-67"), "identity project teardown"))
        for ns in managed_clean:
            if ns != "websvc-67" or project_clean:
                cleanup_step("delete owned namespace " + ns, lambda ns=ns: kubectl("delete", "namespace", ns, "--wait=true", "--timeout=90s"))
        if platform_written and len(managed_clean) == len(owned_namespaces):
            cleanup_step("delete fixture platform", lambda: kubectl("delete", "environmentconfig", "webservice-local", "--ignore-not-found"))
        if cleanup_errors:
            raise RuntimeError("Cleanup incomplete; dependencies preserved where required: " + ", ".join(cleanup_errors))

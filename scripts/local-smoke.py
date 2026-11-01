# /// script
# dependencies = ["pyyaml"]
# ///
"""Exercise the installed source package on an explicitly selected Hops local cluster."""
import argparse
import base64
import http.client
import json
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
args = parser.parse_args()
if args.context not in ("kind-hops", "colima"):
    parser.error("this fixture targets kind-hops or colima only")
CTX = args.context
NAMESPACES = ("websvc-54", "websvc-67")
forwards = []

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
               and c.get("observedGeneration", obj["metadata"]["generation"]) == obj["metadata"]["generation"]
               for c in obj.get("status", {}).get("conditions", []))

def forward(name, target_port):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        ["kubectl", "--context", CTX, "-n", "istio-ingress", "port-forward",
         "svc/" + name, str(port) + ":" + str(target_port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    forwards.append(process)
    wait(lambda: socket.create_connection(("127.0.0.1", port), timeout=1).close() is None,
         "isolated gateway port forward", timeout=20)
    return port

def request(port, hostname, tls_context=None):
    sock = socket.create_connection(("127.0.0.1", port), timeout=30)
    if tls_context:
        sock = tls_context.wrap_socket(sock, server_hostname=hostname)
    try:
        sock.sendall(("GET / HTTP/1.1\r\nHost: " + hostname + "\r\nConnection: close\r\n\r\n").encode())
        response = http.client.HTTPResponse(sock)
        response.begin()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        sock.close()

def host(name, namespace):
    return f"{name}.{namespace}.webservice.localhost"

def absent(kind, namespace):
    return not get(kind, namespace=namespace)["items"]

# These namespaces are exclusive fixtures. Refuse to reuse anyone else's namespace.
for ns in NAMESPACES:
    raw = kubectl("get", "namespace", ns, "--ignore-not-found", "-o", "json")
    if raw.strip():
        existing = json.loads(raw)
        assert existing["metadata"].get("labels", {}).get("hops.ops.com.ai/webservice-test") == "true"
        assert absent("webservices", ns), "fixture namespace already has a WebService"

with tempfile.TemporaryDirectory(prefix="webservice-smoke-") as tmp:
    try:
        apply_file("prerequisites.yaml")
        apply_file("tls.yaml")
        apply_file("issuer.yaml")
        apply_file("knative-config.yaml")
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
        platform["data"]["auth"].update(issuerURL="https://auth.gitkb.localhost", projectId=project_id, caBundle=ca.decode())
        apply(platform)
        apply_file("webservices.yaml")
        login = yaml.safe_load((ROOT / "local/authenticated.yaml").read_text())
        gateway_ip = get("svc", "webservice-private-istio", "istio-ingress")["spec"]["clusterIP"]
        login["spec"]["podTemplate"]["hostAliases"] = [{"ip": gateway_ip, "hostnames": ["auth.gitkb.localhost"]}]
        apply(login)
        for ns, names in [("websvc-54", ["echo"]), ("websvc-67", ["echo", "api", "gateway", "login"])]:
            for name in names:
                wait(lambda ns=ns, name=name: ready("webservice", name, ns), "ready " + ns + "/" + name)
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
        assert location.scheme == "https" and location.hostname == "auth.gitkb.localhost"
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
        for p in forwards:
            p.terminate()
        for p in forwards:
            p.wait(timeout=10)
        for ns in NAMESPACES:
            kubectl("-n", ns, "delete", "webservices", "--all", "--wait=false")
            wait(lambda ns=ns: absent("webservices", ns) and absent("objects.kubernetes.m.crossplane.io", ns)
                 and absent("oidcs.application.zitadel.m.crossplane.io", ns), "managed teardown " + ns)
        kubectl("-n", "websvc-67", "delete", "project.project.zitadel.m.crossplane.io", "webservice-local-test", "--ignore-not-found", "--wait=false")
        wait(lambda: absent("project.project.zitadel.m.crossplane.io", "websvc-67"), "identity project teardown")
        for ns in NAMESPACES:
            kubectl("delete", "namespace", ns, "--wait=false")
        kubectl("delete", "environmentconfig", "webservice-local", "--ignore-not-found")

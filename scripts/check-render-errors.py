"""Bad operator settings must fail rendering, never erase the desired resources."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
XR = {
    "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
    "kind": "WebService",
    "metadata": {"name": "echo", "namespace": "preview-67"},
    "spec": {"image": "hashicorp/http-echo:1.0.0", "port": 5678},
}
PLATFORM = {
    "apiVersion": "apiextensions.crossplane.io/v1beta1",
    "kind": "EnvironmentConfig",
    "metadata": {"name": "webservice-default"},
    "data": {
        "baseDomain": "example.com",
        "privateGateway": {"namespace": "istio-ingress", "service": "private.example.com"},
        "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "fixture-project",
            "allowedGroups": ["platform.developer"],
            "caBundle": "public-test-ca",
        },
    },
}

missing = copy.deepcopy(PLATFORM)
missing["metadata"]["name"] = "webservice-other"
empty = copy.deepcopy(PLATFORM)
empty["data"] = {}
collision = copy.deepcopy(XR)
collision["spec"].update(auth={"enabled": True}, podTemplate={"volumes": [{"name": "oidc-ca", "emptyDir": {}}]})
cases = [
    ("missing platform", XR, missing, "operator platform configuration webservice-default is missing"),
    ("empty platform", XR, empty, "operator platform configuration webservice-default data is required"),
    ("reserved issuer volume", collision, PLATFORM, "volume oidc-ca is reserved"),
]


for label, change, message in [
    ("reserved proxy sidecar", {"sidecars": [{"name": "login", "image": "example/worker:v1"}]}, "sidecar names must be unique"),
    ("reserved app sidecar", {"sidecars": [{"name": "app", "image": "example/worker:v1"}]}, "sidecar names must be unique"),
    ("duplicate sidecars", {"sidecars": [{"name": "worker", "image": "example/worker:v1"}] * 2}, "sidecar names must be unique"),
    ("sidecar request port", {"sidecars": [{"name": "worker", "image": "example/worker:v1", "ports": [{"containerPort": 9000}]}]}, "sidecars cannot declare request ports"),
    ("reserved app mount", {"volumeMounts": [{"name": "oidc-ca", "mountPath": "/tmp/ca"}]}, "application mount oidc-ca is reserved"),
    ("public hostname override", {"hostname": "legacy.example.com", "exposure": "public"}, "hostname overrides require private exposure"),
]:
    invalid = copy.deepcopy(XR)
    invalid["spec"].update(change)
    cases.append((label, invalid, PLATFORM, message))

shared = copy.deepcopy(PLATFORM)
shared["data"]["privateGateway"]["shared"] = {"name": "private-platform", "sectionName": "https-preview"}
for label, hostname in [("foreign namespace", "other.example.com"), ("foreign domain", "preview-67.other.com"), ("nested hostname", "echo.preview-67.example.com"), ("overlong hostname", "10-preview-67-" + "x" * 64 + ".example.com")]:
    invalid = copy.deepcopy(XR)
    invalid["spec"]["hostname"] = hostname
    cases.append((label, invalid, shared, "shared private hostname must be one label"))
for label, change in [("empty shared configuration", {"privateGateway": {"namespace": "istio-ingress", "service": "private.example.com", "shared": {}}}), ("missing shared listener", {"privateGateway": {"namespace": "istio-ingress", "service": "private.example.com", "shared": {"name": "private-platform"}}}), ("shared plaintext", {"tls": {"enabled": False}})]:
    invalid = copy.deepcopy(shared)
    invalid["data"].update(change)
    cases.append((label, XR, invalid, "shared private ingress requires name, sectionName and TLS"))
invalid = copy.deepcopy(XR)
invalid["metadata"]["namespace"] = "n" * 63
cases.append(("overlong namespace", invalid, shared, "namespace is too long for a bounded hostname"))

invalid = copy.deepcopy(XR)
invalid["metadata"]["namespace"] = "10-preview-67-echo"
invalid["spec"]["hostname"] = "10-preview-67-echo.example.com"
cases.append(("primary versus generated collision", invalid, shared, "shared private hostname must be one label"))

# Up's Docker renderer mounts the project, so fixtures must stay under it.
(ROOT / ".tmp").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT / ".tmp", prefix="render-errors-") as directory:
    directory = Path(directory)
    for label, xr, platform, message in cases:
        (directory / "xr.json").write_text(json.dumps(xr))
        (directory / "platform.json").write_text(json.dumps(platform))
        result = subprocess.run(
            ["up", "composition", "render", "--quiet", "--xrd=apis/webservices/definition.yaml",
             "apis/webservices/composition.yaml", str((directory / "xr.json").relative_to(ROOT)),
             "--extra-resources=" + str((directory / "platform.json").relative_to(ROOT))],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or message not in output:
            raise AssertionError(label + " did not fail safely:\n" + output[-2000:])
        print("PASS reject " + label, flush=True)

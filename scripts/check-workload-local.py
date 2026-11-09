"""Exercise an isolated XR through the active local GitOps tree, without taking ownership."""
import argparse
import base64
import copy
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--context', required=True, choices=['orbstack', 'kind-hops', 'colima'])
parser.add_argument('--composition', help='Explicit isolated source Composition instead of the installed default')
parser.add_argument('--tree', type=Path, required=True, help='Already watched local Cluster manifest tree')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
fixture = json.loads((root / 'local/workload.json').read_text())
if args.composition:
    next(doc for doc in fixture['items'] if doc['kind'] == 'WebService')['spec']['crossplane'] = {'compositionRef': {'name': args.composition}}
ns = 'webservice-workload-proof'
path = args.tree / 'stacks/webservice-workload-proof.yaml'
assert args.tree.is_dir() and not path.exists(), 'Refuse a missing tree or existing fixture file'
base = ['kubectl', '--context', args.context]

def kube(*argv):
    return subprocess.check_output(base + list(argv), text=True, stderr=subprocess.PIPE, timeout=35)

def read(kind, name, namespace=ns):
    return json.loads(kube('get', kind, name, '-n', namespace, '-o', 'json'))

def ready():
    obj = read('webservice', 'collector')
    return any(c['type'] == 'Ready' and c['status'] == 'True' for c in obj.get('status', {}).get('conditions', []))

def wait(label, check, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                print('PASS ' + label, flush=True)
                return result
        except (subprocess.CalledProcessError, KeyError, ValueError):
            pass
        time.sleep(3)
    raise RuntimeError('Timed out: ' + label)

def pod():
    rows = json.loads(kube('get', 'pods', '-n', ns, '-l', 'serving.knative.dev/service=collector', '-o', 'json'))['items']
    return next(p for p in rows if not p['metadata'].get('deletionTimestamp') and all(c.get('ready') for c in p.get('status', {}).get('containerStatuses', [])))

def snapshot(name):
    code = "import pathlib,json;p=pathlib.Path;print(json.dumps({'ticks':int(p('/tmp/workload/ticks').read_text()),'worker':int(p('/tmp/worker').read_text()),'credential':p('/var/run/fixture/token').read_text()}))"
    return json.loads(kube('exec', name, '-n', ns, '-c', 'app', '--', 'python3', '-B', '-c', code))

existing = kube('get', 'namespace', ns, '--ignore-not-found', '-o', 'name')
assert not existing.strip(), 'Refuse an existing test namespace'
setup_verified = False
active_fixture = fixture
try:
    path.write_text('\n---\n'.join(json.dumps(doc) for doc in fixture['items']))
    wait('GitOps fixture applied', lambda: kube('get', 'namespace', ns, '--ignore-not-found', '-o', 'name').strip(), timeout=600)
    wait('XR ready', ready)
    current = pod()
    name, uid = current['metadata']['name'], current['metadata']['uid']
    initial = wait('mounted configuration and companion worker', lambda: snapshot(name))
    assert initial['credential'] == 'fixture-first'
    secret_uid = read('secret', 'credential')['metadata']['uid']
    setup_verified = True
    time.sleep(30)
    idle = snapshot(name)
    assert idle['ticks'] >= initial['ticks'] + 20 and idle['worker'] >= initial['worker'] + 20
    print('PASS application and companion work continue without user HTTP requests', flush=True)
    rotated = copy.deepcopy(fixture)
    next(d for d in rotated['items'] if d['kind'] == 'Secret')['stringData']['token'] = 'fixture-second'
    active_fixture = rotated
    path.write_text('\n---\n'.join(json.dumps(doc) for doc in rotated['items']))
    wait('GitOps credential update applied', lambda: base64.b64decode(read('secret', 'credential')['data']['token']).decode() == 'fixture-second', timeout=600)
    wait('projected credential rotates', lambda: snapshot(name)['credential'] == 'fixture-second', timeout=180)
    assert read('pod', name)['metadata']['uid'] == uid, 'Rotation restarted the pod'
    print('PASS credential rotation preserves the running pod', flush=True)
finally:
    # Remove only the XR from desired state, keeping caller dependencies in GitOps.
    path.write_text('\n---\n'.join(json.dumps(doc) for doc in active_fixture['items'] if doc['kind'] != 'WebService'))
    wait('GitOps XR teardown', lambda: not kube('get', 'webservice', 'collector', '-n', ns, '--ignore-not-found', '-o', 'name').strip(), timeout=600)
    wait('managed workload removed', lambda: not kube('get', 'services.serving.knative.dev', 'collector', '-n', ns, '--ignore-not-found', '-o', 'name').strip())
    if setup_verified:
        assert read('secret', 'credential')['metadata']['uid'] == secret_uid
        print('PASS caller-owned credential survives XR teardown', flush=True)
    path.unlink(missing_ok=True)
    wait('GitOps fixture namespace removed', lambda: not kube('get', 'namespace', ns, '--ignore-not-found', '-o', 'name').strip(), timeout=600)
    wait('GitOps platform fixture removed', lambda: not kube('get', 'environmentconfig', 'webservice-workload-proof', '--ignore-not-found', '-o', 'name').strip(), timeout=600)

"""Exercise an isolated XR through the active local GitOps tree, without taking ownership."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--context', required=True, choices=['orbstack', 'kind-hops', 'colima'])
parser.add_argument('--tree', type=Path, required=True, help='Already watched local Cluster manifest tree')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
fixture = json.loads((root / 'local/workload.json').read_text())
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
try:
    path.write_text(json.dumps(fixture))
    wait('XR ready', ready)
    current = pod()
    name, uid = current['metadata']['name'], current['metadata']['uid']
    initial = wait('mounted configuration and companion worker', lambda: snapshot(name))
    assert initial['credential'] == 'fixture-first'
    time.sleep(30)
    idle = snapshot(name)
    assert idle['ticks'] >= initial['ticks'] + 20 and idle['worker'] >= initial['worker'] + 20
    print('PASS application and companion work continue without user HTTP requests', flush=True)
    rotated = copy.deepcopy(fixture)
    next(d for d in rotated['items'] if d['kind'] == 'Secret')['stringData']['token'] = 'fixture-second'
    path.write_text(json.dumps(rotated))
    wait('projected credential rotates', lambda: snapshot(name)['credential'] == 'fixture-second', timeout=180)
    assert read('pod', name)['metadata']['uid'] == uid, 'Rotation restarted the pod'
    print('PASS credential rotation preserves the running pod', flush=True)
finally:
    # Stop the owner reapplying first, then delete the XR while dependencies remain.
    path.unlink(missing_ok=True)
    kube('delete', 'webservice', 'collector', '-n', ns, '--ignore-not-found', '--wait=false')
    wait('XR teardown', lambda: not kube('get', 'webservice', 'collector', '-n', ns, '--ignore-not-found', '-o', 'name').strip())
    wait('managed workload removed', lambda: not kube('get', 'services.serving.knative.dev', 'collector', '-n', ns, '--ignore-not-found', '-o', 'name').strip())
    read('secret', 'credential')
    print('PASS caller-owned credential survives XR teardown', flush=True)
    kube('delete', 'namespace', ns, '--ignore-not-found', '--wait=false')
    kube('delete', 'environmentconfig', 'webservice-workload-proof', '--ignore-not-found')

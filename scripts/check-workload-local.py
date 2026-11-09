"""Exercise mounted configuration and idle work in an exclusive local namespace."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--context', required=True, choices=['orbstack', 'kind-hops', 'colima'])
parser.add_argument('--composition', help='Explicit isolated source Composition instead of the installed default')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
fixture = json.loads((root / 'local/workload.json').read_text())
if args.composition:
    next(doc for doc in fixture['items'] if doc['kind'] == 'WebService')['spec']['crossplane'] = {'compositionRef': {'name': args.composition}}
ns = 'webservice-workload-runtime-proof'
base = ['kubectl', '--context', args.context]

def kube(*argv, document=None):
    return subprocess.check_output(base + list(argv), input=json.dumps(document) if document else None,
                                   text=True, stderr=subprocess.PIPE, timeout=35)

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

assert not kube('get', 'namespace', ns, '--ignore-not-found', '-o', 'name').strip(), 'Refuse an existing test namespace'
setup_verified = False
try:
    kube('apply', '-f', '-', document=fixture)
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
    rotated = copy.deepcopy(next(doc for doc in fixture['items'] if doc['kind'] == 'Secret'))
    rotated['stringData']['token'] = 'fixture-second'
    kube('apply', '-f', '-', document=rotated)
    wait('projected credential rotates', lambda: snapshot(name)['credential'] == 'fixture-second', timeout=180)
    assert read('pod', name)['metadata']['uid'] == uid, 'Rotation restarted the pod'
    print('PASS credential rotation preserves the running pod', flush=True)
finally:
    # Caller dependencies remain until both the XR and managed workload are gone.
    kube('delete', 'webservice', 'collector', '-n', ns, '--ignore-not-found', '--wait=false')
    wait('XR teardown', lambda: not kube('get', 'webservice', 'collector', '-n', ns, '--ignore-not-found', '-o', 'name').strip())
    wait('managed workload removed', lambda: not kube('get', 'services.serving.knative.dev', 'collector', '-n', ns, '--ignore-not-found', '-o', 'name').strip())
    if setup_verified:
        assert read('secret', 'credential')['metadata']['uid'] == secret_uid
        print('PASS caller-owned credential survives XR teardown', flush=True)
    kube('delete', 'namespace', ns, '--ignore-not-found', '--wait=false')
    kube('delete', 'environmentconfig', 'webservice-workload-runtime-proof', '--ignore-not-found')
    # Namespace GC can retain the Pod's original five-minute grace estimate.
    wait('fixture namespace removed', lambda: not kube('get', 'namespace', ns, '--ignore-not-found', '-o', 'name').strip(), timeout=600)

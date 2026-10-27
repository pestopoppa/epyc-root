#!/usr/bin/env python3
"""Stage-one supervisor using the reviewed r11 process-group helpers."""
import json, os, pathlib, runpy, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from split import ROOT, identity

reference = ROOT / 'r11-supervisor-reference.py'
namespace = runpy.run_path(str(reference), run_name='split_reference')
run = namespace['run']
g = run.__globals__
g['R'] = ROOT / 'stage1-results'
g['LIMIT'] = 20 * 1024**3

def guard():
    if g['stop_reason']: raise RuntimeError(g['stop_reason'])
    q = subprocess.run(['/bin/bash', str(ROOT / 'admission.sh')], capture_output=True)
    if q.returncode: raise RuntimeError('admission refused: ' + q.stderr.decode())

g['guard'] = guard
source, state = ROOT / 'source-view', ROOT / 'stage1-state'
command = ['/usr/bin/python3', '-I', str(ROOT / 'split.py'), 'prepare19', str(source), str(state)]
guard()
if state.exists() or (source / '.gitnexus').exists(): raise SystemExit('stage1 target is not fresh')
if identity(source) != json.loads((ROOT / 'preseal.json').read_text()): raise SystemExit('preseal mismatch')
subprocess.run(['/usr/bin/sha256sum', '-c', str(ROOT / 'native-dependencies.sha256')], check=True, stdout=subprocess.DEVNULL)
guard()
if os.environ.get('FILLER_PREFLIGHT') == '1':
    subprocess.run(['/usr/bin/python3', '-I', '-B', '/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/deps/dryrun_check.py',
                    'boundary', '--job', str(ROOT / 'body.sh'), '--effect', 'cache-write'], check=True)
    print('STAGE1_EXACT_FIRST_EFFECT_T1 ' + json.dumps(command))
    raise SystemExit(0)
g['R'].mkdir(exist_ok=False)
os.environ['SPLIT_RUNNING'] = '1'
env = dict(os.environ, GNX_OUTER_SUPERVISOR='1')
run('prepare', command, seconds=3300, env=env)
subprocess.run(['/usr/bin/sha256sum', '-c', str(ROOT / 'native-dependencies.sha256')], check=True, stdout=subprocess.DEVNULL)
print('STAGE1_PREPARED_ONLY; NO COMPLETE GRAPH')

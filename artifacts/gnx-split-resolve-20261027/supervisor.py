#!/usr/bin/env python3
"""Private stage2: full replay, then read-only native sentinels."""
import json, os, pathlib, runpy, subprocess, sys
ROOT=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase'); P=ROOT/'stage2-packet-r2'; R=ROOT/'stage2-results-r2'
m=runpy.run_path(str(ROOT/'r11-supervisor-reference.py'),run_name='split2_reference')
run=m['run']; g=run.__globals__; g['R']=R; g['LIMIT']=20*1024**3
def guard():
    if g['stop_reason']: raise RuntimeError(g['stop_reason'])
    q=subprocess.run(['/bin/bash',str(P/'guard.sh')],capture_output=True)
    if q.returncode: raise RuntimeError('admission refused: '+q.stderr.decode())
g['guard']=guard
guard()
if R.exists(): raise SystemExit('non-resumable stage2 results already exist')
subprocess.run(['/usr/bin/python3','-I','-B',str(ROOT/'verify-capsule.py')],check=True)
subprocess.run(['/usr/bin/sha256sum','-c',str(ROOT/'native-dependencies.sha256')],check=True,stdout=subprocess.DEVNULL)
command=['/usr/bin/python3','-I',str(ROOT/'split.py'),'resolve',str(ROOT/'source-view'),str(ROOT/'stage1-state')]
guard()
if os.environ.get('FILLER_PREFLIGHT')=='1':
    subprocess.run(['/usr/bin/python3','-I','-B','/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/deps/dryrun_check.py','boundary','--job',str(P/'body.sh'),'--effect','private-graph-write'],check=True)
    print('STAGE2_EXACT_FIRST_EFFECT_T1 '+json.dumps(command)); raise SystemExit(0)
R.mkdir(exist_ok=False)
os.environ['SPLIT_RUNNING']='1'
env=dict(os.environ,GNX_OUTER_SUPERVISOR='1')
run('resolve',command,seconds=2700,env=env)
guard()
run('sentinels',['/usr/bin/python3','-I','-B',str(P/'sentinels.py')],seconds=600,env=env)
guard()
subprocess.run(['/usr/bin/sha256sum','-c',str(ROOT/'native-dependencies.sha256')],check=True,stdout=subprocess.DEVNULL)
if not (R/'SENTINELS.json').is_file(): raise SystemExit('sentinel receipt missing')
result={'status':'SCOPED_C72_SENTINELS_PASS_REVIEW_ONLY','fold_authority':False,
        'sentinels_sha256':__import__('hashlib').sha256((R/'SENTINELS.json').read_bytes()).hexdigest()}
tmp=R/'RESULT.json.tmp'; tmp.write_text(json.dumps(result,indent=2)+'\n'); tmp.replace(R/'RESULT.json')
print('PRIVATE_GRAPH_SCOPED_SENTINELS_PASS_REVIEW_ONLY')

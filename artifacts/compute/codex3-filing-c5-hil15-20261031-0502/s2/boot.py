import hashlib,json,os,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;OLD=Path('/mnt/raid0/llm/tmp/hil15-s2-unarmed-executor-v1-20261029')
sys.path[:0]=[str(D),str(OLD),'/mnt/raid0/llm/tmp/pip03-matched-successor-20261029']
manifest=D/'SOURCE.sha256';anchor=os.environ['HIL15_MANIFEST_SHA']
if hashlib.sha256(manifest.read_bytes()).hexdigest()!=anchor:raise SystemExit('source anchor mismatch')
for line in manifest.read_text().splitlines():
 digest,name=line.split('  ',1);p=Path(name)
 if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit('source changed: '+name)
from mixed_executor import load_plan
from raid_storage import check as check_storage
check_storage(D)
if sys.argv[1:]==['--check-complete']:
 from check_complete import check
 print(json.dumps(check(),sort_keys=True));raise SystemExit(0)
if sys.argv[1:]==['--preflight']:
 load_plan();print('static source/history passed; no model started');raise SystemExit(0)
if len(sys.argv)==3 and sys.argv[1]=='--smoke' and sys.argv[2] in ('normal','cutoff'):
 root=Path(os.environ['HIL15_SMOKE_ROOT'])
 if root.is_symlink() or not root.is_dir() or root.parent!=D or not root.name.startswith('real-unit-smoke-'):raise SystemExit('unsafe canary root')
 from s2_smoke_v2 import admission
 admission(root)
 argv=['/usr/bin/python3','-B','-I',str(D/'output_fence.py'),str(root),'/usr/bin/python3','-B','-I',str(D/'s2_smoke_v2.py'),sys.argv[2],'1']
 os.execv(argv[0],argv)
if sys.argv[1:]:raise SystemExit(64)
load_plan()
from s2_grant_contract_v1 import parse,active,binding,WindowMarginReached,INITIAL_REPLAY_BUDGET_S
try:
 ident='codex-hil15-s2-r13-pid-20261031';grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ident+'.grant')
 if grant.is_symlink():raise RuntimeError('unsafe own grant')
 start,end=parse(grant.read_text(),os.environ['FILLER_CPUS']);end,deadline=active(start,end,time.time(),minimum_remaining_s=INITIAL_REPLAY_BUDGET_S)
 binding(os.environ,identifier=ident,stop=Path('/mnt/raid0/llm/tmp/hil15-s3-t1-repair-20261030/s2-r13-pid-20261031/STOP'),end=end,deadline=deadline)
except WindowMarginReached as exc:
 print(json.dumps({'partial':True,'reason':str(exc),'new_replay_exposures':0}),flush=True);raise SystemExit(75)
root=D/'s2-official-results'
if root.is_symlink():raise SystemExit('unsafe output root')
root.mkdir(mode=0o700,exist_ok=True);os.environ['HIL15_SOURCE_MANIFEST']=str(manifest)
argv=['/usr/bin/taskset','-c',os.environ['FILLER_CPUS'],'/usr/bin/python3','-B','-I',str(D/'output_fence.py'),str(root),'/usr/bin/python3','-B','-I',str(D/'s2_native_v3.py')]
os.execv(argv[0],argv)

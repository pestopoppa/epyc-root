#!/usr/bin/env python3
"""KPF-20: scan members, then index the pinned scratch checkout under admission."""
import json, os, subprocess, sys
from pathlib import Path
TREE=Path('/mnt/raid0/llm/tmp/kvfork/kpf20-orchestrator')
OUT=Path('/mnt/raid0/llm/tmp/kvfork/kpf20-v2/out')
HEAD='488b31c96c6c148768508b3dcaefcb6c4c297664'

def run(cmd, name=None, accepted=(0,)):
 p=subprocess.run(cmd,cwd=TREE,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if name:
  (OUT/(name+'.stdout')).write_text(p.stdout); (OUT/(name+'.stderr')).write_text(p.stderr)
 if p.returncode not in accepted: raise RuntimeError(f'{cmd} rc={p.returncode}: {p.stderr[-1000:]}')
 return p.stdout

def check():
 if not (TREE/'.git').is_file() or (TREE/'.git').is_symlink(): raise RuntimeError('source must be a registered detached worktree; prepare it outside the grant')
 if 'worktree '+str(TREE.resolve()) not in run(['git','worktree','list','--porcelain']).splitlines(): raise RuntimeError('source worktree destination is unregistered')
 if run(['git','symbolic-ref','-q','HEAD'], accepted=(0,1)).strip(): raise RuntimeError('source must remain detached')
 assert run(['git','rev-parse','HEAD']).strip()==HEAD
 assert not run(['git','diff','--name-only','HEAD']).strip()
 assert (TREE/'scripts/gitnexus-analyze.sh').is_file()

check()
if '--check' in sys.argv: print('Pinned checkout clean and wrapper present'); sys.exit(0)
OUT.mkdir(parents=True,exist_ok=True)
pattern=r'\.(acquire|_fits|reservation_tokens|history_prefill_estimate|get_slot_for_prompt|infer|_pin_slots_enabled|compute_waves|remember|lookup|run_scouts|choose_fanout_mode|delegate)[[:space:]]*\('
scan=run(['git','grep','-n','-E',pattern,HEAD,'--','src'], 'member_calls')
if not scan.strip(): raise RuntimeError('pinned member-call scan returned no matches')
with (OUT/'results.jsonl').open('w') as f:
 f.write(json.dumps({'type':'member_call_scan','source_commit':HEAD,'lines':scan.splitlines(),'partial':True})+'\n'); f.flush(); os.fsync(f.fileno())
if os.environ.get('FILLER_SMOKE')=='1' or Path(os.environ.get('FILLER_STOPFILE','/nonexistent')).exists(): sys.exit(75)
run(['bash',str(TREE/'scripts/gitnexus-analyze.sh')], 'analyze')
run(['gitnexus','status'],'status')
run(['/usr/bin/python3','-I',str(TREE/'scripts/gitnexus-guard.py'),'--repo','app'],'guard')
targets=[('acquire','src/scheduling/kv_pool_admission.py'),('_fits','src/scheduling/kv_pool_admission.py'),('reservation_tokens','src/scheduling/kv_pool_admission.py'),('history_prefill_estimate','src/scheduling/kv_pool_admission.py'),('get_slot_for_prompt','src/inference/prefix_cache.py'),('infer','src/inference/prefix_cache.py'),('_pin_slots_enabled','src/inference/prefix_cache.py'),('compute_waves','src/parallel_step_executor.py'),('PrefixHistory','src/scheduling/prefix_history.py'),('remember','src/scheduling/prefix_history.py'),('lookup','src/scheduling/prefix_history.py'),('run_scouts','src/api/routes/chat_pipeline/scout_stage.py'),('choose_fanout_mode','src/typed_decisions/fanout_policy.py'),('delegate','src/api/routes/delegate.py')]
for symbol,path in targets:
 if Path(os.environ.get('FILLER_STOPFILE','/nonexistent')).exists(): sys.exit(75)
 for kind,args in [('context',['gitnexus','context',symbol,'--file',path]),('impact',['gitnexus','impact',symbol,'--direction','upstream','--file',path])]:
  run(['/usr/bin/python3','-I',str(TREE/'scripts/gitnexus-guard.py'),'--repo','app'])
  raw=run(args,kind+'-'+symbol)
  data=json.loads(raw)
  if data.get('error') or data.get('status')=='ambiguous' or (kind=='impact' and data.get('risk') in (None,'UNKNOWN')): raise RuntimeError(f'{kind} {symbol}: unresolved {data}')
  with (OUT/'results.jsonl').open('a') as f: f.write(json.dumps({'type':kind,'symbol':symbol,'path':path,'source_commit':HEAD,'result':data})+'\n'); f.flush(); os.fsync(f.fileno())
check()
(OUT/'COMPLETE').write_text('All required context, upstream impact and member-call scan outputs captured. Review risks before editing.\n')

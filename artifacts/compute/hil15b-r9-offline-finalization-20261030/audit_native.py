#!/usr/bin/env python3
import hashlib,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
from collections import Counter
S=Path(__file__).parent
H=Path('/mnt/micron/codex3-hil15b-heavy-r9-20261030')
ENGINE=Path('/mnt/raid0/llm/worktrees/hil15a-fix-20261022')
OLD=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15b-four-family-api-v2')
sys.path[:0]=[str(H),str(ENGINE)]
from verify_replay import verify
from predecessor_check import check as check_predecessor
from overlay_controller import tree_hash
from src.trace.dependency_features import auc_table,load_runs

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,name):
 with (S/(name+'.stdout')).open('x') as so,(S/(name+'.stderr')).open('x') as se:
  p=subprocess.run(args,stdout=so,stderr=se)
 return p.returncode
started=time.time()
original_source=sha(H/'source.sha256')
check_predecessor()
inv=json.loads((H/'inventory.json').read_bytes())
rows=[];new=[];unknown=[]
for unit,slots in sorted(inv['units'].items()):
 n=unit[-2:]
 for i in range(3):
  s=slots[str(i)]
  if s['state']=='unknown':
   assert (n,i) in [('11',0),('12',2),('16',1),('19',0)]
   assert tree_hash(Path(s['attempt']))==s['tree_sha256']
   unknown.append({'unit':n,'slot':i,'attempt':s['attempt'],'tree_sha256':s['tree_sha256']});continue
  if s['state']=='accepted':
   a=Path(s['attempt']);expected=s['result']
  else:
   assert s['state']=='unexposed'
   attempts=list((H/'results-remaining'/unit/f'slot-{i}').iterdir())
   assert len(attempts)==1 and attempts[0].is_dir() and not attempts[0].is_symlink()
   a=attempts[0];expected=None
  before=tree_hash(a)
  verify_path=Path(expected['attempt']) if expected is not None and n=='05' and i==0 else a
  result=verify(verify_path,n,i,H/'tasks.json',OLD)
  if expected is not None:assert result==expected
  d=a/f'driver-{i}';m=json.loads((d/'manifest.json').read_bytes())
  labels=json.loads((d/'labels.json').read_bytes());rid=f'filter-{n}-p{i}-r0'
  assert labels=={rid:[f'filter-{n}-p{i}',m['runs'][0]['pass']]}
  auc=json.loads((d/'auc_table.json').read_bytes())
  native_auc=auc_table(load_runs(d/'events.sqlite'),{k:(v[0],bool(v[1])) for k,v in labels.items()})
  assert auc==m['auc_table']==native_auc
  with sqlite3.connect(f'file:{d/"events.sqlite"}?mode=ro',uri=True) as db:
   counts=dict(db.execute('select category,count(*) from event group by category'))
  row={'unit':n,'slot':i,'prior_state':s['state'],'attempt':str(a),'native_answer_pass':m['runs'][0]['pass'],'native_join':m['join'],'native_auc':auc,'event_counts':counts,'native_manifest_sha256':sha(d/'manifest.json'),'native_db_sha256':sha(d/'events.sqlite'),'native_auc_sha256':sha(d/'auc_table.json'),'tree_sha256':before,'native_verifier':result}
  if s['state']=='unexposed':
   name=f'replay-{n}-{i}'
   rc=run([sys.executable,'-S',str(ENGINE/'scripts/trace/replay_flip_run.py'),'verify','--db',str(d/'events.sqlite'),'--run-id',rid,'--cas-dir',str(d/'cas')],name)
   assert rc==0,(name,rc)
   row['repeated_offline_replay']={'rc':rc,'stdout_sha256':sha(S/(name+'.stdout')),'stderr_sha256':sha(S/(name+'.stderr'))}
   new.append(row)
  assert tree_hash(a)==before
  rows.append(row)
assert len(rows)==44 and len(new)==5 and len(unknown)==4
u=H/'results-remaining'/'unit-20'
assert run([sys.executable,'-S',str(S/'unit-original.py'),'validate',str(u),'20'],'original-unit20-control')!=0
assert 'auc' in (S/'original-unit20-control.stderr').read_text()
assert run([sys.executable,'-S',str(S/'unit-fixed.py'),'validate',str(u),'20'],'fixed-unit20-native')==0
# Retained dependency-bearing case validates unchanged under the same fix.
u4=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15b-heavy-continuation-20261028/results-remaining/unit-04')
assert run([sys.executable,'-S',str(S/'unit-fixed.py'),'validate',str(u4),'04'],'fixed-unit04-retained')==0
assert sha(H/'source.sha256')==original_source
passes=sum(x['native_answer_pass'] for x in rows)
report={'schema':'hil15b-original-r9-offline-finalization/v1','event_id':'codex3-hil15b-heavy-r9-split-20261030','original_exit_rc':1,'original_failure_class':'validator','original_failure':'unit.py hardcoded AUC n_runs=1,n_tasks=1 despite canonical dependency-only AUC 0/0 on valid no-dependency runs','audit_started_epoch':started,'audit_finished_epoch':time.time(),'source_manifest_sha256':original_source,'fix_sha256':sha(S/'unit-fixed.py'),'original_validator_sha256':sha(S/'unit-original.py'),'inventory_sha256':sha(H/'inventory.json'),'case_count':48,'prior_accepted_count':39,'new_native_verified_count':5,'known_count':44,'unknown_count':4,'unexposed_count':0,'new_native_answer_passes':sum(x['native_answer_pass'] for x in new),'native_answer_passes_observed':passes,'scope_pass_count_bounds':[passes,passes+4],'scope_pass_rate_bounds':[passes/48,(passes+4)/48],'scope':'original units05-20,48slots; fulloriginal20units60slots notclaimed','quality_verdict':None,'auc_verdict':'insufficient; zero new dependency-bearing runs; no AUC or dependency-effectiveness finding','model_or_cohort_runs_added':0,'native_artifacts_modified':False,'new_cases':new,'all_known_cases':rows,'immutable_unknown_cases':unknown,'rule_met':'All five original unexposed slots now have retained native outcomes; collection exhausted with original four unknowns preserved. No full-cohort quality verdict.'}
with (S/'OFFLINE-FINALIZATION.json').open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:report[k] for k in ['known_count','unknown_count','unexposed_count','new_native_answer_passes','native_answer_passes_observed','scope_pass_count_bounds','model_or_cohort_runs_added','auc_verdict']}))

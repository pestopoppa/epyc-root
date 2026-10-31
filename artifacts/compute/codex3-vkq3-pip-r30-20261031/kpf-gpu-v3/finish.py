#!/usr/bin/env python3
"""Capture 27B GPU leg and its actual e332 comparison, without cross-model claims."""
import json,os,sys
from pathlib import Path
from aggregate_c import aggregate
D=Path('/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3')
control = len(sys.argv)==3 and sys.argv[1]=='--control'
if len(sys.argv)!=1 and not control:raise SystemExit('invalid consumer invocation')
root=Path(sys.argv[2]) if control else D/'full'
paths=sorted((root/'records').glob('*.json'));records=[json.loads(p.read_text()) for p in paths]
cp=sorted((root/'comparator'/'records').glob('*.json'));comparisons=[json.loads(p.read_text()) for p in cp]
if not paths or len(comparisons)!=2:raise SystemExit('native or e332 comparator records missing')
byarm={r.get('arm'):r for r in comparisons}
if set(byarm)!={'champion','fork_off'}:raise SystemExit('unexpected comparator arms')
champ,off=byarm['champion'],byarm['fork_off']
if champ.get('binary_sha256')!='8a3710ad9f0bea535dd9cbd84ff49d8b8af9e2783979077fb109db13a5620b7b' or off.get('binary_sha256')!='2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635':raise SystemExit('comparator binary mismatch')
if champ.get('prompt_set_sha256')!=off.get('prompt_set_sha256'):raise SystemExit('comparator prompt mismatch')
def normalized(argv):
 out=[];i=1
 while i<len(argv):
  if argv[i] in ('--slot-save-path','--slot-fork-min-tokens','--port'):
   i+=2;continue
  out.append(argv[i]);i+=1
 return out
if normalized(champ.get('argv') or [])!=normalized(off.get('argv') or []):raise SystemExit('comparator target parameter mismatch')
result={'schema':'epyc.kpf181.gpu-leg.v2','partial':False,'task_gate_complete':False,
 'scope':('public 0.8B control only; no target inference' if control else '27B Q8 target DFlash2 Q8 on/off and no-drafter; same-binary fork-off and exact e332 GPU comparison'),
 'record_paths':[str(p) for p in paths], 'C':None if control else aggregate(records,list(range(7168,7680,32))),
 'comparator':{'record_paths':[str(p) for p in cp],'prompt_set_sha256':champ.get('prompt_set_sha256'),
               'champion_binary_sha256':champ.get('binary_sha256'),'fork_off_binary_sha256':off.get('binary_sha256'),
               'target_parameters_match':True,'native_off_equals_champion':off.get('equivalence',{}).get('off_equals_champion')},
 'mtp':'CPU 35B separate; not combined','historical':'prior S1 observations retained separately; these are explicit new replications',
 'slot_observation':'active samples require task and slot identity match; absent samples remain unknown; post-completion slot retained separately',
 'gate_note':'Original full KPF-18.1 remains open pending other unmet criteria.'}
if control:
 children=[c for r in records if r.get('arm')=='A_ckpt' for c in r.get('cells',[]) if c.get('role')=='sibling']
 if len(children)!=1:raise SystemExit('control fork child missing')
 c=children[0];e=c.get('active_slot_evidence') or {}
 if e.get('status')!='observed' or e.get('n_fork_tokens')!=c.get('n_fork_tokens') or not isinstance(c.get('n_fork_tokens'),int) or c['n_fork_tokens']<=0:raise SystemExit('no task-matched active fork sample')
 result['active_fork_control']=e
name='CONTROL-RESULT.json' if control else 'RESULT.json'
tmp=root/(name+'.tmp')
with tmp.open('w') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
os.replace(tmp,root/name);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)

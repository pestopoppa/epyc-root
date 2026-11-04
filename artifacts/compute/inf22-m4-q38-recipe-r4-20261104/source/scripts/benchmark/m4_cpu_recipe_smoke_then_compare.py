#!/usr/bin/env python3
"""Run a short actual native smoke for both enrolled Q38FN images."""
from __future__ import annotations
import argparse,copy,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PRODUCER=ROOT/'scripts/benchmark/m4_cpu_producer'
sys.path.insert(0,str(PRODUCER));sys.path.insert(0,str(ROOT/'scripts/benchmark'))
import m4_cpu_recipe_compare as comparison
from native.k35_stack_context_matrix_runner import cleanup_proved_complete

def parse_cpus(value: str) -> tuple[list[int],str]:
    cpus=set()
    for part in value.split(','):
        bits=part.split('-')
        if len(bits)==1: cpus.add(int(bits[0]))
        elif len(bits)==2:
            lo,hi=map(int,bits)
            if hi<lo or hi-lo>255: raise ValueError('invalid allocated CPU range')
            cpus.update(range(lo,hi+1))
        else: raise ValueError('invalid allocated CPU set')
    ordered=sorted(cpus)
    if len(ordered)!=4 or ordered[0]<0: raise ValueError('smoke requires exactly four allocated CPUs')
    return ordered,','.join(map(str,ordered))

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--smoke-only',action='store_true',required=True)
 p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
 p.add_argument('--smoke-root',type=Path,required=True);p.add_argument('--cpus',required=True)
 a=p.parse_args(); bound=comparison.verify(a.plan,a.plan_sha256,full_hash=True); plan=bound['plan']
 if not os.environ.get('M4_OWNED_CGROUP') or not os.environ.get('M4_SERVER_PID_REGISTRY'):
  raise RuntimeError('native smoke requires the existing row watcher cgroup and PID registry')
 if a.smoke_root.exists(): raise RuntimeError('native smoke output already exists')
 cpus,cpu_list=parse_cpus(a.cpus);a.smoke_root.mkdir(parents=True)
 runner=PRODUCER/'native/k35_stack_context_matrix_runner.py'; arms=[]
 for index,arm in enumerate(('baseline','candidate')):
  cfg=copy.deepcopy(plan['recipes']['canonical_t48']);cfg['cpu_affinity']=a.cpus
  cfg['threads']=min(int(cfg['threads']),len(cpus))
  out=a.smoke_root/arm;out.mkdir()
  env=dict(os.environ);env['M4_SCENARIO_JSON']=json.dumps(cfg,sort_keys=True,separators=(',',':'))
  env['M4_TREATMENT']='default-off' if arm=='baseline' else 'srpf-cap512'
  for key in list(env):
   if key.startswith('LLAMA_ARG_') or (key.startswith('GGML_') and not (key=='GGML_IQK' and env[key]=='1')) or key in ('LD_PRELOAD','LD_AUDIT'):
    env.pop(key,None)
  env['GGML_IQK']='1'
  cmd=[sys.executable,'-B',str(runner),'--execute','--only',cfg['name'],'--context','1024','--max-tokens','16',
       '--min-completion-tokens','8','--reps','1','--output-dir',str(out),'--binary',str(bound['images'][arm]/'bin/llama-server'),
       '--port-base',str(19280+index*20),'--allow-dirty-host']
  with (out/'smoke.log').open('xb') as log:
   subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  summary=json.loads((out/'summary.json').read_bytes())
  results=summary.get('results',[])
  if summary.get('status')!='ok' or len(results)!=1 or results[0].get('status')!='ok' or not cleanup_proved_complete(results[0].get('cleanup')):
   raise RuntimeError(f'{arm} native response/owned-child cleanup did not pass')
  r=results[0];tokens=int(r.get('completion_tokens') or 0)
  if not 8<=tokens<=16: raise RuntimeError(f'{arm} decoded token count outside 8..16: {tokens}')
  arms.append({'arm':arm,'scenario':cfg['name'],'image_source_commit':plan['champion'] if arm=='baseline' else plan['candidate'],
               'cpu_affinity':a.cpus,'threads':cfg['threads'],'summary':str(out/'summary.json'),'status':'ok',
               'completion_tokens':tokens,'decode_tps':float(r['decode_tps']),'prompt_tps':float(r['prompt_tps']),
               'elapsed_s':float(r['elapsed_s']),'cleanup_proved':True})
 smoke={'schema':'epyc.m4.q38.native-first-step-smoke.v1','plan_sha256':a.plan_sha256,'cpu_ids':cpus,
        'scope':'two actual native 1024-context canonical_t48 responses, 8-16 decoded tokens each; outside 12-cell denominator','arms':arms}
 with (a.smoke_root/'SMOKE-COMPLETE.json').open('x') as f: json.dump(smoke,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as exc:
  print(f'REFUSED: {exc}',file=sys.stderr);raise SystemExit(2)

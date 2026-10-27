#!/usr/bin/env python3
"""Capture operator-reviewed post-reload identities; never send inference."""
import argparse, hashlib, json, math, os
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('--input', required=True); p.add_argument('--output', required=True)
a=p.parse_args(); x=json.loads(Path(a.input).read_text())
required=('api_workers','backend_pid','model_paths','future_kv_state_gib','reservation_gib','budget_evidence','source_commit','source_tree','backend_port')
if any(k not in x for k in required) or not x['api_workers'] or not x['model_paths']: raise SystemExit('missing owner bindings')
if any(isinstance(x[k],bool) or not isinstance(x[k],(int,float)) or not math.isfinite(x[k]) for k in ('reservation_gib','future_kv_state_gib')) or x['reservation_gib']<=0 or x['future_kv_state_gib']<0: raise SystemExit('invalid owner budget')
evidence=Path(x['budget_evidence']); tree=Path(x['source_tree'])
if not evidence.is_file() or not tree.is_dir(): raise SystemExit('missing budget evidence or source tree')
def birth(pid): return Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')',1)[1].split()[19]
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
 return h.hexdigest()
procs=x.get('resident_processes',[])
if not procs or int(x['backend_pid']) not in procs or not set(map(int,x['api_workers'])).issubset(set(map(int,procs))): raise SystemExit('resident inventory incomplete')
x['births']={str(pid):birth(pid) for pid in procs}; x['budget_evidence_sha256']=digest(evidence)
x['models']=[{'path':str(Path(m).resolve()),'size':Path(m).stat().st_size} for m in x['model_paths']]
x['source_files']={str(tree/p):digest(tree/p) for p in ('src/backends/prompt_layout.py','src/backends/serving_calls.py','src/backends/dispatch_log.py','src/api/routes/openai_compat.py','src/prompt_builders/builder.py','scripts/analysis/prompt_layout_live_check.py','scripts/analysis/prompt_layout_reader.py')}
x['executables']={str(pid):os.readlink(f'/proc/{pid}/exe') for pid in procs}
x['binding_version']='rte-live-v1'; Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
print('Captured identities; owner must verify complete process, model and KV inventory.')

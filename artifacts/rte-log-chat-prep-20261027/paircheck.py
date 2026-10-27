"""Check that one chat request produced paired, lease-attributed layout records."""
from datetime import datetime
import os

def holds_inode(line, pid, device, inode):
 fields=line.split()
 expected=f'{os.major(device):02x}:{os.minor(device):02x}:{inode}'
 return len(fields)>=6 and fields[4]==str(pid) and fields[5]==expected

def validate(serving_rows, dispatch_rows, session, workers, port, samples):
 serving=[r for r in serving_rows if r.get('method')=='infer' and r.get('caller',{}).get('parent_request_id')==session]
 if not serving: raise ValueError('no matching serving records')
 ids={r.get('caller',{}).get('request_id') for r in serving}
 if None in ids or len(ids)!=len(serving): raise ValueError('missing or duplicate call IDs')
 dispatch=[r for r in dispatch_rows if r.get('kind')=='dispatch' and r.get('request_id') in ids]
 if len(dispatch)!=len(ids) or {r['request_id'] for r in dispatch}!=ids: raise ValueError('dispatch join')
 byid={r['request_id']:r for r in dispatch}
 for s in serving:
  d=byid[s['caller']['request_id']]; pid=s.get('provenance',{}).get('pid'); task=s.get('caller',{}).get('task_id'); ts=datetime.fromisoformat(s['ts_start'].replace('Z','+00:00')).timestamp(); te=datetime.fromisoformat(s['ts_end'].replace('Z','+00:00')).timestamp()
  run_id=s.get('provenance',{}).get('run_id')
  if pid not in workers or s.get('server',{}).get('port')!=port or not isinstance(run_id,str) or not run_id or run_id!=d.get('provenance',{}).get('run_id') or pid!=d.get('provenance',{}).get('pid'): raise ValueError('worker/backend mismatch')
  if not task or not any(z['entry'].get('pid')==pid and z['entry'].get('request_tag')==task and ts<=z['time']<=te and z.get('owned') and set(z['owned'])==set(z['entry'].get('regions',[])) for z in samples): raise ValueError('native lease unobserved')
  for r in (s,d):
   if r.get('source')!='benchmark' or not r.get('blocks') or not isinstance(r.get('layout_chars'),int) or any(r.get(k) is None and (r.get('result') or {}).get(k) is None for k in ('prompt_tokens','cached_prompt_tokens')): raise ValueError('layout/source/token fields')
 return serving,dispatch

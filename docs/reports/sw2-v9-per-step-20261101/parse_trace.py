#!/usr/bin/env python3
"""Bounded per-request v9 native trace interpretation; unknowns stay unknown."""
import json,re,sys
from pathlib import Path
START=re.compile(r'launch_slot_: id\s+(\d+) \| task (\d+) \| processing task')
STEP=re.compile(r'id\s+(\d+) \| task (\d+) \| accepted\s+(\d+)/\s*(\d+) draft tokens(?: \(restore checkpoint\))?')
END=re.compile(r'release:\s*id\s+(\d+) \| task (\d+) \| stop processing')
def classify(segment,cap,total):
 starts=START.findall(segment); ends=END.findall(segment); steps=STEP.findall(segment)
 if len(starts)!=1 or starts[0][0]!='0' or ends!=starts or not steps: return {'status':'UNKNOWN','reason':'incomplete task attribution or no per-step records'}
 if any((s,t)!=starts[0] for s,t,_,_ in steps): return {'status':'UNKNOWN','reason':'cross-task trace'}
 widths=[int(n) for _,_,_,n in steps]
 if any(int(a)>int(n) or int(n)<1 for _,_,a,n in steps): return {'status':'UNKNOWN','reason':'invalid trace counter'}
 if not isinstance(total,int) or sum(widths)!=total: return {'status':'UNKNOWN','reason':'trace total differs from native response'}
 return {'status':'WITHIN_CAP' if max(widths)<=cap else 'OVER_CAP','widths':widths,'count':len(widths),'max':max(widths),'total':total}
def main(root):
 root=Path(root); logs=list(root.glob('server-*.log')); out=[]
 if len(logs)!=1: raise SystemExit('UNKNOWN: expected one server log')
 data=logs[0].read_bytes()
 if len(data)>16*1024*1024: raise SystemExit('UNKNOWN: trace exceeds bound')
 caps=[7,1,2,7]
 for i,cap in enumerate(caps):
  try:
   r=json.loads((root/f'{i}.response.json').read_text()); b=json.loads(r['raw']); start=r['server_log_start'];end=r['server_log_end']; assert r['parsed']==b and r['http_status']==200 and b['id_slot']==0 and b['generation_settings']['speculative.n_max']==cap and 0<=start<end<=len(data)
   result=classify(data[start:end].decode('utf-8'),cap,b['timings'].get('draft_n'))
  except (OSError,ValueError,KeyError,TypeError,AssertionError,UnicodeDecodeError): result={'status':'UNKNOWN','reason':'missing or malformed raw record or log bounds'}
  out.append({'case':i,'cap':cap,**result})
 print(json.dumps({'schema':'sw2.v9.per-step.analysis.v1','cases':out,'interpretation':'WITHIN_CAP is a bounded observation; a positive >1 control is required to establish discrimination. Never infer behavior for v10.'},indent=2))
if __name__=='__main__':main(sys.argv[1])

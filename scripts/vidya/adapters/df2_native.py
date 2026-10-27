"""Strict rederivation of model-free AKX per-shape width observations."""
import json,re
SHAPES={(5120,17408),(6144,5120),(17408,5120)}
LABEL=re.compile(r'D27:W\[ne00=(\d+),ne01=(\d+)\]')
HEX=re.compile(r'[0-9a-f]{64}')
def read_cells(path,cell_id):
 records=[json.loads(x) for x in open(path) if x.strip()]; headers=[x for x in records if x.get('record')=='run']; done=[x for x in records if x.get('record')=='row_done']
 if len(headers)!=1 or headers[0].get('backend_bound')!='ROCm0' or headers[0].get('kmax')!=8 or headers[0].get('repeats')!=3 or headers[0].get('seed')!='674854' or len(done)!=1 or done[0].get('id')!=cell_id: raise ValueError('native header or row completion')
 summaries={}; widths={}
 for x in records:
  if x.get('record') not in ('cell','k'): continue
  key=(x.get('id'),x.get('sub'),x.get('sub_label')); match=LABEL.fullmatch(str(key[2]))
  if key[0]!=cell_id or type(key[1]) is not int or not match or tuple(map(int,match.groups())) not in SHAPES: raise ValueError('native shape/id')
  if x['record']=='cell':
   if key in summaries or x.get('status')!='OK' or x.get('kmax')!=8 or x.get('repeats')!=3 or any(x.get(k)!=[] for k in ('unstable_ks','unsupported_ks','err_ks','k1_identity_violation')) or 'first_fail_k' not in x: raise ValueError('partial/invalid native summary')
   summaries[key]=x
  else:
   k=x.get('k'); index=(key,k)
   if type(k) is not int or k not in range(1,9) or index in widths or x.get('status')!='OK': raise ValueError('native width coverage')
   a,b=x.get('digest_batched'),x.get('digest_serial')
   if not isinstance(a,list) or not isinstance(b,list) or len(a)!=3 or len(b)!=3 or any(not isinstance(v,str) or not HEX.fullmatch(v) for v in a+b) or len(set(a))!=1 or len(set(b))!=1: raise ValueError('unstable/missing native repeat digests')
   diffs=[av!=bv for av,bv in zip(a,b)]
   if x.get('width_differs_by_repeat')!=diffs or x.get('width_differs')!=any(diffs) or x.get('batched_repeat_stable') is not True or x.get('serial_repeat_stable') is not True: raise ValueError('native diff not rederived')
   widths[index]=any(diffs)
 if len(summaries)!=3 or {tuple(map(int,LABEL.fullmatch(k[2]).groups())) for k in summaries}!=SHAPES or len(widths)!=24: raise ValueError('incomplete declared shape/width coverage')
 result={}
 for key,summary in summaries.items():
  if any((key,k) not in widths for k in range(1,9)) or widths[(key,1)]: raise ValueError('missing width or k1 violation')
  first=next((k for k in range(2,9) if widths[(key,k)]),None)
  if summary['first_fail_k']!=first: raise ValueError('first failure not rederived')
  result[key]=first
 return result

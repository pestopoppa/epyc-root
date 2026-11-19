#!/usr/bin/env python3
import hashlib,json,os,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
ROOT=Path('/mnt/raid0/llm/epyc-orchestrator/logs')
FILES={'serving':ROOT/'serving_calls/serving_calls.jsonl','dispatch':ROOT/'dispatch/dispatch.jsonl'}
CUTS=(1024,2048,4096,8192,16384,65536)
stop=False
def on_signal(*_):
 global stop
 stop=True
signal.signal(signal.SIGTERM,on_signal);signal.signal(signal.SIGINT,on_signal)
def boundary():
 if stop or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()): raise RuntimeError('STOP')
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))): raise RuntimeError('deadline')
def snapshot(p):
 boundary()
 with p.open('rb') as f:
  a=os.fstat(f.fileno())
  if a.st_size>64*1024*1024: raise RuntimeError('input exceeds 64MiB bound')
  raw=f.read(a.st_size+1);b=os.fstat(f.fileno())
 if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns) or len(raw)!=a.st_size: raise RuntimeError('input changed')
 if raw and not raw.endswith(b'\n'): raise RuntimeError('incomplete frontier')
 rows=[]
 for line in raw.splitlines():
  x=json.loads(line)
  if not isinstance(x,dict): raise RuntimeError('non-object input')
  rows.append(x)
 return rows,{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def analyze(serving,dispatch):
 idx={}; duplicates=set()
 for d in dispatch:
  if d.get('schema')!='epyc.orchestrator.dispatch.v1' or d.get('kind')!='dispatch': continue
  rid=d.get('request_id')
  if not isinstance(rid,str) or not rid: continue
  if rid in idx: duplicates.add(rid)
  else: idx[rid]=d
 seen_serving={}; duplicate_serving=set()
 for s in serving:
  c=s.get('caller') if isinstance(s.get('caller'),dict) else {}; rid=c.get('request_id')
  if isinstance(rid,str) and rid:
   if rid in seen_serving: duplicate_serving.add(rid)
   seen_serving[rid]=True
 roles={};counts={'serving':len(serving),'dispatch':len(dispatch),'invalid_or_unmatched':0,'ambiguous_dispatch':0,'ambiguous_serving':0,'missing_role':0,'joined':0}
 for s in serving:
  boundary()
  if s.get('schema')!='epyc.orchestrator.serving_call.v1': counts['invalid_or_unmatched']+=1;continue
  caller=s.get('caller') if isinstance(s.get('caller'),dict) else {}; rid=caller.get('request_id')
  if rid in duplicate_serving: counts['ambiguous_serving']+=1;continue
  if rid in duplicates: counts['ambiguous_dispatch']+=1;continue
  d=idx.get(rid); result=s.get('result') if isinstance(s.get('result'),dict) else {}
  if not d or result.get('success') is not True: counts['invalid_or_unmatched']+=1;continue
  role=d.get('role');p=result.get('prompt_tokens');c=result.get('cached_prompt_tokens')
  if not isinstance(role,str) or not role or len(role)>128: counts['missing_role']+=1;continue
  if role not in {'frontdoor','coder_escalation','architect_general','worker_summarize','fixture'}: role='other_or_unknown'
  if type(p) is not int or type(c) is not int or not 0<=c<=p: counts['invalid_or_unmatched']+=1;continue
  client=d.get('client') if isinstance(d.get('client'),dict) else {}
  # Only fixed labels appear in output; direct and unknown data cannot become fleet claims.
  kind='direct' if d.get('method')=='direct' else 'other_or_unknown'
  v=p-c; key=(role,kind); roles.setdefault(key,[]).append(v);counts['joined']+=1
 out=[]
 for (role,kind),vs in sorted(roles.items()):
  total=sum(vs); bins=[]
  for cut in CUTS:
   under=[v for v in vs if v<cut]; share=sum(under)/total if total else None
   bins.append({'cut_tokens':cut,'request_count_below':len(under),'uncached_tokens_below':sum(under),'uncached_token_share':share,'illustrative_ceiling_rho_1_325':share*(1-1/1.325) if share is not None else None})
  out.append({'role':role,'dispatch_group':kind,'requests':len(vs),'uncached_tokens':total,'bins':bins})
 return {'counts':counts,'roles':out,'rho_scope':'1.325 historical log median; not a controlled measurement','scope':'aggregate joined traffic only; direct and other/unknown are separate; no production representativeness claim'}
def write(p,obj):
 boundary();p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output exists')
 q=p.with_suffix('.tmp');
 with q.open('x') as f:json.dump(obj,f,sort_keys=True);f.write('\n')
 boundary();os.replace(q,p)
def main():
 if sys.argv[1:]==['--complete']:
  smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text())
  assert r['status']==('SMOKE_PASS' if smoke else 'CENSUS_COMPLETE') and r['schema']=='hsf4.serving-histogram.v1'
  if smoke: assert r['counts']['joined']==1 and r['roles'][0]['uncached_tokens']==3
  else: assert set(r['custody'])==set(FILES)
  boundary();return
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if smoke:
  assert len(os.sched_getaffinity(0))==4
  serving=[{'schema':'epyc.orchestrator.serving_call.v1','caller':{'request_id':'fixture'},'result':{'success':True,'prompt_tokens':5,'cached_prompt_tokens':2}}]
  dispatch=[{'schema':'epyc.orchestrator.dispatch.v1','kind':'dispatch','request_id':'fixture','role':'fixture','method':'direct'}]
  r=analyze(serving,dispatch);r.update(schema='hsf4.serving-histogram.v1',status='SMOKE_PASS');write(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),r);return
 serving,ss=snapshot(FILES['serving']);dispatch,ds=snapshot(FILES['dispatch']);r=analyze(serving,dispatch);r.update(schema='hsf4.serving-histogram.v1',status='CENSUS_COMPLETE',custody={'serving':ss,'dispatch':ds});write(D/'out/RESULT.json',r)
if __name__=='__main__':main()

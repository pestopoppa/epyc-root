#!/usr/bin/env python3
"""Per-request durable TALE evaluation using the original scorer and prompts."""
import hashlib,json,os,signal,sys,time,subprocess
from pathlib import Path
from dataclasses import asdict
import urllib.request
import eval_tale_budget as e
import confined_score
D=Path(__file__).resolve().parent
POOL=Path('/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.prbt4-refresh-20260917.jsonl')
SUITES=['math','olympiadbench','mmlu_pro','livecodebench']
WARRANT=None

def put(path, value):
 if WARRANT is not None:
  value=dict(value);value.setdefault('write_warrant',WARRANT);value.setdefault('writer_pid',os.getpid());value.setdefault('written_unix',time.time());value.pop('record_sha256',None)
  value['record_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_name(path.name+'.tmp.'+str(os.getpid()))
 with tmp.open('x') as f:
  json.dump(value,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def main():
 if os.environ.get("PRB_QUALIFIED_EXECUTION")!="1": raise SystemExit("PROTOTYPE ONLY: no qualified execution")
 global WARRANT
 ep=Path(os.environ['PRB_ENVELOPE']);raw=ep.read_bytes();envelope=json.loads(raw)
 if not envelope.get('gpu_resident') or not envelope.get('model_sha256') or not envelope.get('source_catalog_sha256'):raise RuntimeError('native launch envelope incomplete')
 WARRANT={'envelope_path':str(ep),'envelope_sha256':hashlib.sha256(raw).hexdigest(),'run_id':'codex3-prbt4-r1-20261031'}
 smoke=os.environ.get('PRB_SMOKE')=='1'
 if smoke:
  qs=[{'id':'public-smoke-fixture','suite':'math','prompt':'In several complete sentences, explain how to make a cup of tea and why each step matters.','expected':'public-control-no-quality-grade','scoring_method':'exact_match','scoring_config':{}}]
 else:
  sample=json.loads((D/'SAMPLE.json').read_text()); qs=e.load_questions(SUITES,400,seed=42,pool_path=POOL)
  ids=[{'suite':q.get('suite'),'id':str(q.get('id',q.get('question_id','?')))} for q in qs]
  if ids!=sample['ids'] or len(qs)!=1600 or sample['preflight_defects'] or e.preflight_oracles(qs): raise RuntimeError('sample or preflight mismatch')
 original_score=e.score_question
 def bounded_score(answer,question):
  if question.get('scoring_method')=='code_execution': return confined_score.score(e.strip_think_blocks(answer),question)
  return original_score(answer,question)
 e.score_question=bounded_score
 cfg=e.GenConfig(base_url=os.environ['PRB_ENDPOINT'],temperature=.1,seed=42,max_tokens=64 if smoke else 8192,model=None,chat_template_kwargs={'enable_thinking':False},budget_unit='tokens',timeout=1200)
 out=Path(os.environ['PRB_OUTPUT']); out.mkdir(parents=True,exist_ok=True)
 stop=Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE'])
 interrupted=[False]
 def halt(*_): interrupted[0]=True
 signal.signal(signal.SIGTERM,halt);signal.signal(signal.SIGINT,halt)
 def attempt(q,idx,condition,estimate=None):
  path=out/f'{idx:04d}'/(condition+'.json')
  if path.exists():
   v=json.loads(path.read_text())
   if v['status']=='in_flight': v.update(status='unknown_interrupted',note='exposure began; no automatic redraw');put(path,v)
   return v
  reserve_s=20 if smoke else 1265
  if interrupted[0] or stop.exists() or time.time()+reserve_s>=deadline: raise InterruptedError('stop or insufficient request reserve')
  started=time.time()
  put(path,{'status':'in_flight','question_id':str(q.get('id',q.get('question_id','?'))),'condition':condition,'started':started})
  calls=[]
  def post(url,body,timeout):
   req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=min(timeout,max(1,deadline-time.time()-5))) as resp: status=resp.status;obj=json.load(resp)
   calls.append({'request':body,'status':status,'response':obj})
   usage=obj.get('usage')
   if status!=200 or not isinstance(usage,dict) or isinstance(usage.get('completion_tokens'),bool) or not isinstance(usage.get('completion_tokens'),int) or usage['completion_tokens']<0:raise RuntimeError('native completion token usage unavailable')
   if not isinstance(obj.get('model'),str) or not obj['model']:raise RuntimeError('native response model identity unavailable')
   return obj
  cfg.poster=post
  try:
   if condition=='estimate': result=asdict(e.estimate_tale_budget_full(q.get('prompt',q.get('question','')),cfg))
   else: result=asdict(e.run_trial(q,condition,cfg,estimate))
   if len(calls)!=1: raise RuntimeError('unexpected request count')
   choice=calls[0]['response']['choices'][0]; finish=choice.get('finish_reason')
   if not isinstance(finish,str): raise RuntimeError('missing finish_reason')
   v={'status':'complete','condition':condition,'started':started,'finished':time.time(),'finish_reason':finish,'cap_reached':finish=='length','result':result,'http':calls[0],'scorer_witness':confined_score.LAST if condition!='estimate' and q.get('scoring_method')=='code_execution' else {'kind':'in_process','pid':os.getpid()}}
   put(path,v);return v
  except BaseException as ex:
   put(path,{'status':'unknown_error','condition':condition,'started':started,'finished':time.time(),'error':type(ex).__name__+': '+str(ex),'http':calls,'partial':True})
   if isinstance(ex,(KeyboardInterrupt,SystemExit)): raise
   return {'status':'unknown_error'}
 for i,q in enumerate(qs):
  try:
   est=attempt(q,i,'estimate')
   attempt(q,i,'baseline');attempt(q,i,'static')
   if est['status']=='complete': attempt(q,i,'tale',e.BudgetEstimate(**est['result']))
   else:
    path=out/f'{i:04d}'/'tale.json'
    if not path.exists(): put(path,{'status':'unknown_dependency','condition':'tale','reason':'estimator unavailable; not redrawn'})
  except InterruptedError:
   put(out/'PARTIAL.json',{'partial':True,'next_index':i,'reason':'STOP or deadline'});return 75
 if smoke:
  put(out/'DONE.json',{'partial':False,'sample_count':len(qs),'note':'public control only'})
  return 0
 put(out/'COLLECTION_COMPLETE.json',{'partial':False,'sample_count':len(qs),'note':'all exposures accounted; unknowns retained'})
 if interrupted[0] or stop.exists() or time.time()+300>=deadline:
  put(out/'PARTIAL.json',{'partial':True,'reason':'finalizer requires 300s reserve'});return 75
 try:
  grade=subprocess.run([sys.executable,'-B',str(D/'offline_grade.py'),str(out),str(out/'FINAL.json')],timeout=max(1,deadline-time.time()-10),capture_output=True,text=True)
 except subprocess.TimeoutExpired:
  put(out/'PARTIAL.json',{'partial':True,'reason':'finalizer deadline'});return 75
 (out/'finalizer.log').write_text(grade.stdout+'\n'+grade.stderr)
 if grade.returncode not in (0,2):raise RuntimeError('strict finalizer failed rc='+str(grade.returncode))
 final=json.loads((out/'FINAL.json').read_text())
 put(out/'DONE.json',{'partial':False,'sample_count':len(qs),'final_status':'COMPLETE' if grade.returncode==0 else 'INCOMPLETE','final_path':str(out/'FINAL.json'),'scientific_verdict_available':grade.returncode==0})
 return 0
if __name__=='__main__': sys.exit(main())

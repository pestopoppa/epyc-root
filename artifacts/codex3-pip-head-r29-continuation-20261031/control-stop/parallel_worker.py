#!/usr/bin/env python3
"""Concurrent page workers with per-shard native journals and one bounded request gate."""
import concurrent.futures, hashlib, importlib.util, json, os, pathlib, sys, threading, time
BASE=pathlib.Path('/mnt/raid0/llm/tmp/pip02-pipeline-prep-20261029')
HERE=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/control-stop')
for path in (BASE/'opencv-overlay-v1',BASE/'opencv-headless-v1'):sys.path.insert(0,str(path))
for name,digest in (json.loads((BASE/'opencv-overlay-v1-hashes.json').read_bytes()) | json.loads((BASE/'opencv-headless-v1-hashes.json').read_bytes())).items():
 if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=digest:raise RuntimeError('overlay hash mismatch')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
class RequestBudget:
 def __init__(self,limit,concurrency,deadline=None,min_remaining=0): self.limit=limit;self.used=0;self.refusals={};self.lock=threading.Lock();self.slots=threading.BoundedSemaphore(concurrency);self.deadline=deadline;self.min_remaining=min_remaining
 def begin(self,record):
  if not self.slots.acquire(timeout=60):raise TimeoutError('server request slot unavailable')
  try:
   with self.lock:
    if self.used>=self.limit:raise TimeoutError('segment request budget exhausted before exposure')
    if self.deadline is not None and time.time()+self.min_remaining>=self.deadline:raise TimeoutError('deadline before request exposure')
    record();self.used+=1
  except BaseException:self.slots.release();raise
 def note_budget_refusal(self,prefix):
  with self.lock:self.refusals[prefix]=self.refusals.get(prefix,0)+1
 def refused(self,prefix):
  with self.lock:return self.refusals.get(prefix,0)
 def release(self):self.slots.release()
 def available(self):
  with self.lock:return self.used<self.limit

def main():
 if len(sys.argv)!=3:raise ValueError('config and sha required')
 raw=pathlib.Path(sys.argv[1]).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=sys.argv[2]:raise RuntimeError('config identity')
 c=json.loads(raw);required={'mode','shards','output_roots','population_sha256','image_root','layout_dir','endpoint','deadline_epoch','stop_path','campaign','capture_path','legacy_roots','prior_output_roots'}
 if set(c)!=required or c['mode'] not in ('normal','smoke') or (len(c['shards'])!=len(c['output_roots']) or len(c['shards'])!=len(c['legacy_roots']) or len(c['shards'])!=len(c['prior_output_roots'])):raise ValueError('config scope')
 plan_path=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/english755-fresh-plan.json') if c['mode']=='normal' else BASE/'population.json'
 plan_raw=plan_path.read_bytes()
 if hashlib.sha256(plan_raw).hexdigest()!=c['population_sha256']:raise RuntimeError('population identity')
 plan=json.loads(plan_raw);pages=plan['pages'];groups=[]
 if c['mode']=='normal':
  if len(pages)!=755 or len(c['shards']) not in (2,3) or len(set(c['shards']))!=len(c['shards']):raise ValueError('two or three unique five-page shards required')
  for i in c['shards']:
   if type(i)!=int or not 0<=i<=4:raise ValueError('shard')
   group=pages[5*i:5*(i+1)]
   if len(group)!=5:raise ValueError('shard population')
   groups.append([x for x in group if x['index'] not in plan['prior_original_page_exposures_unknown']])
 else:
  if c['shards']!=[807,836] or len(pages)<=309:raise ValueError('smoke controls')
  groups=[[pages[i]] for i in c['shards']]
 capture=json.loads(pathlib.Path(c['capture_path']).read_bytes());identity={'campaign_sha256':hashlib.sha256(json.dumps(c['campaign'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'model_pins':c['campaign'].get('server_pins'),'source_pins':capture['source_pins']}
 remaining=0 if c['mode']=='smoke' else 1000
 context={'provenance':{'identity':identity,'origin_grant':capture['grant'],'origin_capture_sha256':hashlib.sha256(pathlib.Path(c['capture_path']).read_bytes()).hexdigest()},'deadline_epoch':c['deadline_epoch'],'min_remaining_s':remaining,'request_budget':RequestBudget(5,12,c['deadline_epoch'],remaining)}
 writer_mod=load('parallel_writer','/mnt/raid0/llm/tmp/inf51-streamingllm-full-20261029/bounded_writer.py'); journal_mod=load('parallel_journal',HERE/'journal_layered.py');layer=load('parallel_layer',HERE/'layered_writer.py'); driver=load('parallel_driver',HERE/'pages_driver_checkpoint.py');worker=load('parallel_native_worker',HERE/'pipeline_worker_generic.py');trace=load('parallel_trace',BASE/'trace_capture.py')
 from paddleocr import PaddleOCRVL
 active=lambda:time.time()<c['deadline_epoch'] and not pathlib.Path(c['stop_path']).exists()
 cpus=sorted(os.sched_getaffinity(0));count=min(1,len(cpus),sum(map(len,groups)))
 if count<1:raise RuntimeError('empty worker pool')
 writers=[]; jobs=[]
 try:
  for group,out,legacy,prior in zip(groups,c['output_roots'],c['legacy_roots'],c['prior_output_roots']):
   out=pathlib.Path(out);w=layer.LayeredWriter([legacy,prior],out,writer_mod.Writer,192*1024**2);writers.append(w);j=journal_mod.Journal(w,c['campaign'])
   for page in group:jobs.append((page,j))
  def work(i,page,journal):
   os.sched_setaffinity(0,{cpus[i%len(cpus)]})
   if not active() or not context['request_budget'].available():return {'missing':1,'complete':0,'unknown':0,'invalid':0}
   try:return driver.run([page],c['image_root'],c['layout_dir'],c['endpoint'],PaddleOCRVL,journal,worker,active,trace,context)
   except BaseException as exc:
    key='region-'+hashlib.sha256(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()[:24]+'-'
    if context['request_budget'].refused(key):return {'partial':'request-budget-before-exposure','page':page.get('image'),'no_redraw':True}
    return {'error':type(exc).__name__+': '+str(exc),'page':page.get('image')}
  with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
   futures=[pool.submit(work,i,page,journal) for i,(page,journal) in enumerate(jobs)]
   values=[f.result() for f in futures]
  print(json.dumps({'schema':'pip02-paddle-parallel-pages/v1','pool_workers':count,'shards':c['shards'],'results':values,'new_requests':context['request_budget'].used,'partial':True},sort_keys=True),flush=True)
  return 0 if c['mode']=='normal' and len(jobs)==5*len(groups) and all(x.get('complete')==1 for x in values) else 75
 finally:
  for writer in writers:writer.close()
if __name__=='__main__':raise SystemExit(main())

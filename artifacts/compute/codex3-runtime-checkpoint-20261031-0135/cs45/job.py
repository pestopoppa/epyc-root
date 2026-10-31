#!/usr/bin/env python3
"""820 x 10 CS-45.1 native jobs; checkpoint each exposure without redraw."""
import concurrent.futures, hashlib, itertools, json, os, pathlib, queue, signal, subprocess, sys, tempfile, threading, time, wave
D=pathlib.Path(__file__).resolve().parent; V=D.parent/'venv312/bin/python'; clips=pathlib.Path('/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-1-tail-v1/manifest/clips.jsonl'); audio=pathlib.Path('/mnt/raid0/llm/datasets/turntaking-cs45-1-tail-v1/clips')
STOP=threading.Event(); ACTIVE=set(); LOCK=threading.Lock()
def stop(*args):
 STOP.set()
 with LOCK:
  for p in list(ACTIVE):
   try: os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError: pass
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile('w',dir=p.parent,delete=False) as f: json.dump(v,f); f.flush(); os.fsync(f.fileno()); name=f.name
 os.replace(name,p)
def pcmsha(path):
 with wave.open(str(path),'rb') as w: return hashlib.sha256(w.readframes(w.getnframes())).hexdigest()
def one(job,cpu,out,control):
 cid,arm,variant,expect=job; key=arm+('_'+variant.replace(',','_') if variant else '')+'__'+cid; done=out/'cells'/f'{key}.json'; exposed=out/'cells'/f'{key}.exposure.json'
 if done.exists() or exposed.exists() or STOP.is_set(): return
 clipdir=pathlib.Path('/mnt/raid0/llm/tmp/cs-47-20261020/clips') if control else audio
 if pcmsha(clipdir/f'{cid}.wav')!=expect: raise RuntimeError('PCM mismatch '+cid)
 save(exposed,{'job':key,'started':time.time()}); ids=out/'ids'/f'{key}.txt'; ids.parent.mkdir(exist_ok=True,parents=True); ids.write_text(cid+'\n'); raw=out/'raw'/f'{key}.jsonl'; raw.parent.mkdir(exist_ok=True,parents=True)
 env=os.environ.copy(); env.update(CS45_CLIP_DIR=str(clipdir),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1')
 argv=['taskset','-c',str(cpu),'nice','-n','10',str(V),str(D/'source/worker.py'),'--arm',arm,'--clips',str(ids),'--out',str(raw)]
 if variant: argv+=['--variant',variant]
 with open(out/'raw'/f'{key}.log','wb') as log:
  p=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  with LOCK: ACTIVE.add(p)
  try: rc=p.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try: p.wait(timeout=10)
   except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); p.wait()
   rc=124
  finally:
   with LOCK: ACTIVE.discard(p)
 if STOP.is_set(): return
 try:
  lines=raw.read_text().splitlines(); data=json.loads(lines[0]) if len(lines)==1 else None
 except Exception: data=None
 if rc==0 and data and data.get('clip')==cid and data.get('arm')==arm and (not variant or data.get('variant')==variant): save(done,{'status':'ok','data':data,'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest()})
 else: save(done,{'status':'failure','rc':rc,'reason':'timeout or missing/malformed native output'})
def main():
 control=sys.argv[1]=='smoke'; out=D/('smoke-result' if control else 'results'); out.mkdir(exist_ok=True)
 if control:
  f=pathlib.Path('/mnt/raid0/llm/tmp/cs-47-20261020/clips/tt1-p0001-a.wav'); records=[('tt1-p0001-a',pcmsha(f))]
 else:
  rows=list(map(json.loads,clips.read_text().splitlines())); assert len(rows)==820; records=[(r['clip_id'],r['pcm']['pcm_sha256']) for r in rows]
 variants=['%s,%d,%s'%p for p in itertools.product(('fp32_fp32','fp32_selfdec'),(80,160),('decoder','full'))]; arms=[('silero',''),('smartturn','')]+[('parakeet',x) for x in variants]
 jobs=[(cid,arm,v,sha) for cid,sha in records for arm,v in arms]; cpus=sorted(os.sched_getaffinity(0))[:(1 if control else 8)]; slots=queue.Queue()
 for cpu in cpus: slots.put(cpu)
 def work(j):
  cpu=slots.get()
  try: one(j,cpu,out,control)
  finally: slots.put(cpu)
 with concurrent.futures.ThreadPoolExecutor(max_workers=len(cpus)) as pool:
  active=set(); it=iter(jobs)
  while not STOP.is_set():
   if (D/'STOP').exists(): stop(); break
   while len(active)<len(cpus):
    try: active.add(pool.submit(work,next(it)))
    except StopIteration: break
   if not active: break
   finished,active=concurrent.futures.wait(active,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
   for f in finished:
    try: f.result()
    except Exception as e: print('job unknown',repr(e),flush=True)
 if STOP.is_set(): save(out/'partial.json',{'partial':True}); return 75
 files=list((out/'cells').glob('*.json')); results=[json.loads(p.read_text()) for p in files if not p.name.endswith('.exposure.json')]; ok=sum(r.get('status')=='ok' for r in results); failures=sum(r.get('status')=='failure' for r in results); unknown=len(jobs)-len(results)
 if not control and not failures and not unknown:
  rc=subprocess.run([str(V),str(D/'collect.py')]).returncode
  if rc: save(out/'TERMINAL-INCOMPLETE.json',{'n_jobs':len(jobs),'ok':ok,'failures':0,'unknown':0,'analysis_rc':rc,'complete':False}); return 1
 save(out/('COMPLETE.json' if not failures and not unknown else 'TERMINAL-INCOMPLETE.json'),{'n_jobs':len(jobs),'ok':ok,'failures':failures,'unknown':unknown,'complete':not failures and not unknown})
 return 0
if __name__=='__main__': sys.exit(main())

#!/usr/bin/env python3
"""CS-8.G1B worker: consumes an independently frozen manifest; no cohort selection here."""
import concurrent.futures, hashlib, importlib.util, json, os, pathlib, queue, signal, subprocess, sys, tempfile, time
D=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('g1',D/'original-g1.py'); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
STOP=False
CHILDREN=set()
def stop(*_):
 global STOP
 STOP=True
 for p in list(CHILDREN):
  try: os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError: pass
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(p, value):
 p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile('w',dir=p.parent,delete=False,encoding='utf8') as f:
  json.dump(value,f,ensure_ascii=False,sort_keys=True); f.flush(); os.fsync(f.fileno()); n=f.name
 os.replace(n,p)
def run(argv,env,log,stdin=None,timeout=900):
 with open(log,'wb') as f:
  p=subprocess.Popen(argv,env=env,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  CHILDREN.add(p)
  try:
   p.communicate(input=stdin.encode() if stdin is not None else None,timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL); p.wait(); return -9
  finally: CHILDREN.discard(p)
  return p.returncode
def worker(cell,cpu,out):
 cid=cell['id']; result=out/'cells'/f'{cid}.json'; pending=out/'cells'/f'{cid}.exposure.json'
 if result.exists(): return
 # A durable exposure precedes any child; interrupted cells are unknown, never redrawn.
 if pending.exists(): return
 atomic(pending,{'id':cid,'state':'started','at':time.time()})
 root=out/'raw'/cid; root.mkdir(parents=True,exist_ok=True)
 env={k:v for k,v in os.environ.items() if k not in ('LD_LIBRARY_PATH','LD_PRELOAD')}
 env.update(HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1')
 src=cell['pcm']; assert sha(src)==cell['pcm_sha256']; reference=cell['text']; lang=cell['lang']; item={'id':cid,'lang':lang,'arm':cell['arm'],'seed':cell.get('seed'),'source_pcm_sha256':cell['pcm_sha256'],'ref':reference,'modes':{}}
 wav=src
 if cell['arm']=='tts_rt':
  assert sha(cell['voice_ref'])==cell['voice_ref_sha256']
  raw=root/'tts.24k.wav'; wav=str(root/'tts.16k.wav')
  e=env.copy(); e.update(GGML_BACKEND='CPU',LD_LIBRARY_PATH=g.QWEN+':/opt/rocm/lib',SHIM_NPROCS='2',LD_PRELOAD=g.SHIM)
  rc=run(['taskset','-c',str(cpu),g.QWEN+'/qwen-tts','--model',g.TTS_MODEL,'--codec',g.TTS_CODEC,'--lang',cell['tts_language'],'--seed',str(cell['seed']),'--ref-wav',cell['voice_ref'],'-o',str(raw)],e,root/'tts.log',reference+'\n')
  item['tts_rc']=rc
  if STOP: return
  if rc==0 and raw.is_file():
   try: g.resample_16k(str(raw),wav); item['wav_sha256']=sha(wav)
   except Exception as exc: item['wav_error']=repr(exc); wav=None
  else: wav=None
 for mode,lflag in [('forced',lang),('auto','auto')]:
  hyp=''; rc=None
  if wav:
   base=str(root/('asr-'+mode)); e=env.copy(); e['LD_LIBRARY_PATH']=g.WHBIN+':/opt/rocm/lib'
   rc=run(['taskset','-c',str(cpu),g.WHBIN+'/whisper-cli','-m',g.WH_MODEL,'-t','1','-ng','-l',lflag,'-nt','-otxt','-of',base,'-f',str(wav)],e,root/('asr-'+mode+'.log'))
   if STOP: return
   try:
    if rc==0: hyp=pathlib.Path(base+'.txt').read_text(encoding='utf8').strip()
   except OSError: pass
  r=g.norm(reference,lang); h=g.norm(hyp,lang); rw=r.split(); hw=h.split()
  item['modes'][mode]={'rc':rc,'hyp':hyp,'ref_words':len(rw),'word_errors':g.edit(rw,hw),'ref_chars':len(r),'char_errors':g.edit(list(r),list(h))}
 atomic(result,item)
def main():
 manifest=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); cells=json.loads(manifest.read_text())['cells']
 cpus=sorted(os.sched_getaffinity(0))[:int(os.environ.get('G1_WORKERS','10'))]; assert cpus
 out.mkdir(parents=True,exist_ok=True); (out/'cells').mkdir(exist_ok=True)
 # Source manifest has the full primary and repeated-seed matrix; smoke can use an explicit control-only manifest.
 slots=queue.Queue()
 for cpu in cpus: slots.put(cpu)
 def work(c):
  cpu=slots.get()
  try: worker(c,cpu,out)
  finally: slots.put(cpu)
 with concurrent.futures.ThreadPoolExecutor(max_workers=len(cpus)) as pool:
  active=set(); iterator=iter(enumerate(cells))
  while not STOP:
   if (D/'STOP').exists(): stop(); break
   while len(active)<len(cpus):
    try: i,c=next(iterator)
    except StopIteration: break
    active.add(pool.submit(work,c))
   if not active: break
   done,active=concurrent.futures.wait(active,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
   for f in done:
    try: f.result()
    except Exception as exc: print('cell error; exposure remains unknown:',repr(exc),file=sys.stderr,flush=True)
 if STOP or (D/'STOP').exists(): atomic(out/'partial.json',{'partial':True,'reason':'stop'}); return 75
 missing=[c['id'] for c in cells if not (out/'cells'/f"{c['id']}.json").exists()]
 atomic(out/('TERMINAL-INCOMPLETE.json' if missing else 'COMPLETE.json'),{'complete':not missing,'unknown':missing,'manifest_sha256':sha(manifest),'n':len(cells)})
 return 0
if __name__=='__main__': sys.exit(main())

#!/usr/bin/env python3
import fcntl,hashlib,json,os,pathlib,signal,subprocess,sys,time,wave
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-ultra-torch-reference-v2'); V1=pathlib.Path('/mnt/raid0/llm/tmp/codex3-ultra-torch-reference'); SMOKE=os.getenv('CS8_SMOKE')=='1'; OUT=D/(os.environ.get('CS8_SMOKE_DIR','smoke-final') if SMOKE else 'engineering25-results'); OUT.mkdir(exist_ok=True)
DEADLINE=float(os.environ['CS8_DEADLINE']) if SMOKE and 'CS8_DEADLINE' in os.environ else (time.time()+265 if SMOKE else int(os.environ['FILLER_DEADLINE'])-45)
STOP=False
def on_signal(*_):
 global STOP;STOP=True
signal.signal(signal.SIGTERM,on_signal);signal.signal(signal.SIGINT,on_signal)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atomic(p,obj,replace=False):
 tmp=p.with_name(p.name+f'.tmp.{os.getpid()}');tmp.write_text(json.dumps(obj,sort_keys=True)+'\n')
 if replace:os.replace(tmp,p)
 else:os.link(tmp,p);tmp.unlink()
def rows():
 if SMOKE:
  return [{'clip_id':'jfk','wav_path':'/mnt/raid0/llm/whisper.cpp/samples/jfk.wav','wav_sha256':'59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e'}, {'clip_id':'tone','wav_path':str(V1/'control-tone.wav'),'wav_sha256':'78112ce72576feab43cdb556c28d1df4fd1e32fc23936cf5d4d896a0d5b03b63'}]
 assert sha(D/'engineering25.json')=='f9f18362165121af8b590a901cdea34881dbbc96ae389bfaedef1e72195a6fec'
 return json.loads((D/'engineering25.json').read_text())['records']
def binding(row,arm,pcm):
 return {'clip_id':row['clip_id'],'arm':arm,'wav_sha256':row['wav_sha256'],'pcm_s16_sha256':pcm,'catalog_sha256':os.environ['CS8_SOURCE_SHA'],'plan_sha256':os.environ['CS8_PLAN_SHA'],'input_manifest_sha256':'public-controls' if SMOKE else sha(D/'engineering25.json'),'ultra_model_sha256':'c9608f36d0ab956c14bfcc525479b0746b3b42a56f6949ec85c14eb7466717dc','native_model_sha256':{'f32':'9b1de82be5ace1518e1953262ec9195f2e44432dd8454125c1680bea96ddad4c','q8':'225a877bd3adc74344e2fabbe19b4be5ea76ec47900c9483737427b0fe2a911c','torch':'none'}[arm],'processor_config_sha256':'8346a93a3b987fa1dec57a78f045cd0817d21786589a5a096b41a57a446fd1d7','generation_config_sha256':'b141de6ec6d7f982ece13f98f604e3fe1807ea9c0e839185d0ab7064604209d0','native_library_sha256':os.environ['CS8_NATIVE_SHA']}
def required(arm):
 return ['frontend.npy','attention_mask.npy','encoder.npy','joint_logits.npy','result.json'] if arm=='torch' else ['pcm.f32','mel.f32','encoder.f32','joint_logits.f32','steps.tsv','shapes.txt']
def verify(case,arm,b):
 exp=case/(arm+'.exposure.json');res=case/(arm+'.result.json');seal=case/(arm+'.seal.json')
 if not exp.exists():
  if res.exists() or seal.exists() or (case/arm).exists() or (case/(arm+'-run.stdout')).exists() or (case/(arm+'-run.stderr')).exists():raise RuntimeError('orphan output without exposure '+arm)
  return 'unexposed'
 if json.loads(exp.read_text())!=b:raise RuntimeError('exposure binding changed '+arm)
 if not res.exists() or not seal.exists():return 'unknown'
 fingerprint=json.loads(seal.read_text())
 if fingerprint!={'exposure_sha256':sha(exp),'result_sha256':sha(res)}:raise RuntimeError('result fingerprint changed '+arm)
 r=json.loads(res.read_text())
 actual={str(p.relative_to(case)) for p in (case/arm).rglob('*') if p.is_file()} if (case/arm).exists() else set()
 actual |= {x for x in (arm+'-run.stdout',arm+'-run.stderr') if (case/x).is_file()}
 if set(r['files'])!=actual:raise RuntimeError('output inventory changed '+arm)
 for path,digest in r['files'].items():
  p=case/path
  if not p.is_file() or sha(p)!=digest:raise RuntimeError('missing or tampered '+str(p))
 if r['interrupted']:return 'unknown'
 if r['rc']!=0:return 'fault'
 expected={str((case/arm/x).relative_to(case)) for x in required(arm)} | {arm+'-run.stdout',arm+'-run.stderr'}
 if set(r['files'])!=expected:raise RuntimeError('output manifest incomplete '+arm)
 return 'ok'
def run(cmd,env,case,arm):
 so=case/(arm+'-run.stdout');se=case/(arm+'-run.stderr');interrupted=False
 with so.open('xb') as a,se.open('xb') as b:
  p=subprocess.Popen(cmd,env=env,stdout=a,stderr=b);started=time.monotonic()
  while p.poll() is None:
   if STOP or (D/'STOP').exists() or time.time()>=DEADLINE or time.monotonic()-started>200:
    interrupted=True;p.terminate()
    try:p.wait(5)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    break
   time.sleep(.1)
 files={}
 for path in (case/arm).rglob('*') if (case/arm).exists() else []:
  if path.is_file():files[str(path.relative_to(case))]=sha(path)
 files[so.name]=sha(so);files[se.name]=sha(se)
 if p.returncode==0 and not interrupted:
  for name in required(arm):
   if str((case/arm/name).relative_to(case)) not in files:raise RuntimeError('required output missing '+str(case/arm/name))
 result=case/(arm+'.result.json');atomic(result,{'rc':p.returncode,'interrupted':interrupted,'files':files})
 atomic(case/(arm+'.seal.json'),{'exposure_sha256':sha(case/(arm+'.exposure.json')),'result_sha256':sha(result)})
 return 'unknown' if interrupted else ('ok' if p.returncode==0 else 'fault')
def worker(row,cpu):
 os.sched_setaffinity(0,{cpu});wav=pathlib.Path(row['wav_path'])
 if sha(wav)!=row['wav_sha256']:raise RuntimeError('WAV changed')
 with wave.open(str(wav),'rb') as f:
  if (f.getnchannels(),f.getsampwidth(),f.getframerate())!=(1,2,16000):raise RuntimeError('WAV format')
  pcm=hashlib.sha256(f.readframes(f.getnframes())).hexdigest()
 if 'pcm_sha256' in row and row['pcm_sha256']!=pcm:raise RuntimeError('PCM changed')
 case=OUT/hashlib.sha256(row['clip_id'].encode()).hexdigest();case.mkdir(exist_ok=True)
 state={}
 for arm in ('torch','f32','q8'):
  b=binding(row,arm,pcm);status=verify(case,arm,b)
  if status=='unexposed':
   lock=None
   if SMOKE:
    lock=(OUT/'smoke-model.lock').open('a')
    while True:
     try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
     except BlockingIOError:
      if STOP or (D/'STOP').exists() or time.time()+210>=DEADLINE:lock.close();return 75
      time.sleep(.1)
   try:
    if STOP or (D/'STOP').exists() or time.time()+210>=DEADLINE:return 75
    atomic(case/(arm+'.exposure.json'),b)
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    dest=case/arm
    if arm=='torch':cmd=[str(V1/'host-venv/bin/python'),str(V1/'reference.py'),str(wav),str(dest)]
    else:
     dest.mkdir();env.update(CS8_STAGE_MODEL=arm,CS8_STAGE_WAV=str(wav),CS8_ULTRA_DUMP_DIR=str(dest));cmd=[str(V1/'native/probe.sh')]
    status=run(cmd,env,case,arm)
   finally:
    if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
  state[arm]=status
  if status=='unknown':return 75 if STOP or (D/'STOP').exists() or time.time()>=DEADLINE else 3
  if status=='fault':return 2
 if STOP or (D/'STOP').exists():return 75
 ref=json.loads((case/'torch/result.json').read_text())
 if ref['audio_file_sha256']!=row['wav_sha256'] or ref['samples']*4!=len((case/'f32/pcm.f32').read_bytes()):raise RuntimeError('decoded length/hash mismatch')
 verdict={}
 for arm in ('f32','q8'):
  pcmfile=case/arm/'pcm.f32';pcm_hash=sha(pcmfile)
  if pcm_hash!=ref['pcm_sha256'] or pcmfile.stat().st_size!=ref['samples']*4:raise RuntimeError('decoded PCM mismatch '+arm)
  tmp=case/(arm+f'.compare.{os.getpid()}.tmp');target=case/(arm+'.comparison.txt')
  with tmp.open('wb') as out:rc=subprocess.run([str(V1/'host-venv/bin/python'),str(D/'compare.py'),str(case/'torch'),str(case/arm)],stdout=out,stderr=subprocess.STDOUT).returncode
  os.replace(tmp,target)
  if rc not in (0,1):raise RuntimeError('comparison parser failure '+arm)
  verdict[arm]={'status':'match' if rc==0 else 'token_or_duration_mismatch','comparison_sha256':sha(target),'decoded_pcm_float32_sha256':pcm_hash}
 atomic(case/'verdict.json',{'clip_id':row['clip_id'],'arms':verdict},replace=True)
 return 1 if any(v['status']!='match' for v in verdict.values()) else 0
if len(sys.argv)>1:
 try:sys.exit(worker(rows()[int(sys.argv[1])],int(sys.argv[2])))
 except Exception as e: print('HARNESS FAULT',repr(e),flush=True);sys.exit(2)
rs=rows(); cpus=sorted(os.sched_getaffinity(0)); unique=[];seen=set()
for c in cpus:
 if c%96 not in seen:unique.append(c);seen.add(c%96)
width=min(2 if SMOKE else 8,len(unique));assert width==(2 if SMOKE else 8), 'insufficient distinct granted cores'
active={};next_i=0;counts={'match':0,'negative':0,'fault':0,'unknown':0};interrupted=False
while next_i<len(rs) or active:
 while not STOP and not (D/'STOP').exists() and not interrupted and next_i<len(rs) and len(active)<width:
  free=next(c for c in unique[:width] if c not in active.values());p=subprocess.Popen([sys.executable,__file__,str(next_i),str(free)]);active[p]=free;next_i+=1
 for p in list(active):
  rc=p.poll()
  if rc is None:continue
  del active[p]
  if rc==75:interrupted=True
  elif rc==0:counts['match']+=1
  elif rc==1:counts['negative']+=1
  elif rc==3:counts['unknown']+=1
  else:counts['fault']+=1
 if STOP or (D/'STOP').exists() or interrupted:
  for p in active:
   if p.poll() is None:p.terminate()
  for p in active:p.wait()
  audit={'unexposed':0,'unknown_exposed':0,'completed':0,'failed':0}
  for row in rs:
   case=OUT/hashlib.sha256(row['clip_id'].encode()).hexdigest()
   for arm in ('torch','f32','q8'):
    exp=case/(arm+'.exposure.json');result=case/(arm+'.result.json');seal=case/(arm+'.seal.json')
    if not exp.exists():audit['unexposed']+=1
    elif not result.exists() or not seal.exists():audit['unknown_exposed']+=1
    else:
     value=json.loads(result.read_text())
     if value['interrupted']:audit['unknown_exposed']+=1
     elif value['rc']!=0:audit['failed']+=1
     else:audit['completed']+=1
  atomic(OUT/'PARTIAL.json',{'started':next_i,'unstarted_cases':len(rs)-next_i,'case_counts':counts,'arm_audit':audit},replace=True);sys.exit(75)
 time.sleep(.1)
atomic(OUT/'TERMINAL.json',{'schema':'ultra-cpu-engineering25/v2','cases':len(rs),'counts':counts,'status':'harness_failure' if counts['fault'] else ('unknown' if counts['unknown'] else ('negative' if counts['negative'] else 'match')),'engineering_reuse':not SMOKE,'hip_gate':False},replace=True)
sys.exit(2 if counts['fault'] else (3 if counts['unknown'] else 0))

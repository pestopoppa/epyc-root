#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,subprocess,sys,tempfile,time,wave
from chunk_materialize import materialize,verify_record
from long_chunk_plan import LIMIT
from vad_splice import parse
from voxtral_tokens import parse as parse_tokens
D=pathlib.Path(__file__).resolve().parent
MANIFEST=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/fleurs-validation-pcm/manifest.json')
A=pathlib.Path('/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter')
S=pathlib.Path('/mnt/micron/codex3-cs8-stt2-crisp-20261030/install')
BINS={'vox480':A/'voxtral480-traced/crispasr','vox960':A/'voxtral960-traced/crispasr'}
MODEL=pathlib.Path('/mnt/raid0/llm/models/cs8-cstr--voxtral-mini-4b-realtime-GGUF/voxtral-mini-4b-realtime-q8_0.gguf')
TRANS=pathlib.Path('/mnt/raid0/llm/tmp/codex3-cs8-stt3-transcribe-20261030');VAD=pathlib.Path('/mnt/raid0/llm/models/silero-vad-cs22-v0-20261029/ggml-silero-v6.2.0.bin')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atomic(path,obj):
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.atomic-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(obj,f,sort_keys=True,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(tmp,path)
 finally:os.unlink(tmp)
def main():
 smoke=os.environ.get('CS8_SMOKE')=='1'; out=D/(os.environ.get('CS8_SMOKE_DIR','smoke-result') if smoke else 'validation-results');out.mkdir(exist_ok=True);chunkdir=out/'chunks';chunkdir.mkdir(exist_ok=True)
 plan=os.environ['CS8_PLAN_SHA'];source=os.environ['CS8_SOURCE_SHA'];input_sha=os.environ['CS8_INPUT_SHA'];pin=json.loads((D/'INPUT-PINS.json').read_text());models=pin['models'];binaries=pin['runner_binary_sha256']
 if smoke:
  w=pathlib.Path('/mnt/raid0/llm/whisper.cpp/samples/jfk.wav')
  with wave.open(str(w),'rb') as a:pcm=a.readframes(a.getnframes())
  records=[{'clip_id':'jfk-smoke','language':'en_us','wav_path':str(w),'wav_sha256':sha(w),'pcm_sha256':hashlib.sha256(pcm).hexdigest()}];matrix=[('vox480','auto'),('vox960','auto')]
 else:
  if sha(MANIFEST)!=input_sha:raise RuntimeError('input manifest drift')
  records=json.loads(MANIFEST.read_bytes())['records'];matrix=[('vox480','auto'),('vox960','auto')]
 deadline=time.time()+230 if smoke else int(os.environ['FILLER_DEADLINE'])-45
 stopped=False
 def stop(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 def partial():
  p=out/'partial.json';p.write_text(json.dumps({'partial':True,'at':time.time()})+'\n')
 def run(cmd,so,se,env,timeout):
  with so.open('xb') as a,se.open('xb') as b:
   p=subprocess.Popen(cmd,stdout=a,stderr=b,env=env);started=time.monotonic();timedout=False
   while p.poll() is None:
    if stopped or (D/'STOP').exists() or time.time()>=deadline or time.monotonic()-started>=timeout:
     timedout=time.monotonic()-started>=timeout;p.terminate()
     try:p.wait(5)
     except subprocess.TimeoutExpired:p.kill();p.wait()
     if not timedout:partial();raise InterruptedError
     break
    time.sleep(.1)
  return p.returncode,p.poll() is not None,timedout,time.monotonic()-started
 def chunks(row):
  key=hashlib.sha256(row['clip_id'].encode()).hexdigest();saved=chunkdir/(key+'.chunks.json');wav=pathlib.Path(row['wav_path'])
  if saved.exists():
   result=json.loads(saved.read_text());verify_record(result)
   if result['id']!=row['clip_id'] or result['original_wav_sha256']!=row['wav_sha256'] or result['original_pcm_sha256']!=row['pcm_sha256']:raise RuntimeError('chunk origin drift')
   return result
  if sha(wav)!=row['wav_sha256']:raise RuntimeError('audio drift')
  with wave.open(str(wav),'rb') as w:n=w.getnframes()
  spans=None
  if n>LIMIT:
   exp=chunkdir/(key+'.vad.exposure.json');res=chunkdir/(key+'.vad.result.json');so=chunkdir/(key+'.vad.stdout');se=chunkdir/(key+'.vad.stderr')
   binding={'clip_id':row['clip_id'],'wav_sha256':row['wav_sha256'],'pcm_sha256':row['pcm_sha256'],'source_sha256':source,'plan_sha256':plan,'vad_model_sha256':pin['vad_model_sha256'],'vad_binary_sha256':pin['vad_binary_sha256']}
   if exp.exists():
    if json.loads(exp.read_text())['binding']!=binding:raise RuntimeError('VAD exposure drift')
    if not res.exists():return None
    v=json.loads(res.read_text())
    if v['binding']!=binding or not v['reaped'] or v['rc']!=0 or v['stdout_sha256']!=sha(so) or v['stderr_sha256']!=sha(se):return None
   else:
    if stopped or time.time()+620>=deadline and not smoke:raise InterruptedError
    cmd=[str(TRANS/'build/bin/transcribe-cli'),'-m',str(VAD),'--backend','cpu','--threads','1','--vad-threshold','0.5',str(wav)]
    atomic(exp,{'binding':binding,'cmd':cmd});env={**os.environ,'LD_LIBRARY_PATH':str(TRANS/'install/lib')}
    rc,reaped,timedout,wall=run(cmd,so,se,env,600)
    v={'binding':binding,'rc':rc,'reaped':reaped,'timedout':timedout,'stdout_sha256':sha(so),'stderr_sha256':sha(se),'wall_s':wall};atomic(res,v)
    if rc!=0:return None
   try:spans=parse(so.read_text())
   except ValueError:return None
  result=materialize(row,spans,chunkdir/'pcm');verify_record(result);atomic(saved,result);return result
 counts={};unknown=0
 try:
  for model,mode in matrix:
   for row in records:
    if stopped or (D/'STOP').exists() or time.time()+620>=deadline and not smoke:raise InterruptedError
    chunk=chunks(row)
    if chunk is None or chunk['status']!='ok':unknown+=1;continue
    for part in chunk['chunks']:
     key=hashlib.sha256((model+'|'+mode+'|'+row['clip_id']+'|'+str(part['index'])).encode()).hexdigest();exp=out/(key+'.exposure.json');res=out/(key+'.result.json');prefix=out/key;wav=pathlib.Path(part['wav_path'])
     binding={'clip_id':row['clip_id'],'chunk_index':part['index'],'chunk_pcm_sha256':part['pcm_sha256'],'chunk_wav_sha256':part['wav_sha256'],'input_sha256':input_sha,'plan_sha256':plan,'source_sha256':source,'model_sha256':models[model],'binary_sha256':binaries[model],'library_set_sha256':pin['runner_library_set_sha256'][model],'mode':mode}
     if res.exists():
      v=json.loads(res.read_text())
      if not exp.exists() or json.loads(exp.read_text())['binding']!=binding or v['binding']!=binding or v['reaped'] is not True or not isinstance(v['rc'],int):raise RuntimeError('invalid exposure')
      for suffix in ('stdout','stderr','txt'):
       f=out/(key+'.'+suffix);digest=v[suffix+'_sha256']
       if (digest is None and f.exists()) or (digest is not None and (not f.exists() or sha(f)!=digest)):raise RuntimeError('native bytes drift')
      txt=out/(key+'.txt');status='error'
      if v['rc']==0:
       try:status='ok' if parse_tokens((out/(key+'.stderr')).read_text(),txt.read_text() if txt.exists() else '')['hypothesis_with_unk'].strip() else 'error'
       except (ValueError,UnicodeError):unknown+=1;continue
      counts[status]=counts.get(status,0)+1;continue
     if exp.exists():unknown+=1;continue
     if stopped or time.time()+620>=deadline and not smoke:raise InterruptedError
     if sha(wav)!=part['wav_sha256']:raise RuntimeError('chunk drift')
     threads=2 if smoke else len(os.sched_getaffinity(0));language='auto' if mode=='auto' else row['language'].split('_')[0]
     cmd=[str(BINS[model]),'-m',str(MODEL),'--backend','voxtral4b','--threads',str(threads),'--no-timestamps','--lid-backend','off','-l','auto','-ng','-otxt','-of',str(prefix),'-f',str(wav)]
     env={**os.environ,'LD_LIBRARY_PATH':(str(A/'voxtral960')+':' if model=='vox960' else '')+str(S/'lib'),'CS8_VOXTRAL_TOKEN_TRACE':'1'};env.pop('CS8_VOXTRAL_SMOKE_KV',None)
     atomic(exp,{'binding':binding,'command':cmd,'started_epoch':time.time()})
     rc,reaped,timedout,wall=run(cmd,out/(key+'.stdout'),out/(key+'.stderr'),env,600)
     v={'binding':binding,'rc':rc,'reaped':reaped,'timedout':timedout,'wall_s':wall}
     for suffix in ('stdout','stderr','txt'):
      f=out/(key+'.'+suffix);v[suffix+'_sha256']=sha(f) if f.exists() else None
     atomic(res,v);txt=out/(key+'.txt');status='error'
     if rc==0:
      try:status='ok' if parse_tokens((out/(key+'.stderr')).read_text(),txt.read_text() if txt.exists() else '')['hypothesis_with_unk'].strip() else 'error'
      except (ValueError,UnicodeError):unknown+=1;continue
     counts[status]=counts.get(status,0)+1
 except InterruptedError:partial();return 75
 done=out/('COMPLETE.json' if not unknown and not counts.get('error') else 'TERMINAL-INCOMPLETE.json')
 if not done.exists():atomic(done,{'partial':False,'chunk_counts':counts,'unknown':unknown,'utterances':len(records),'matrix':matrix,'selection_only':not smoke})
 return 0
if __name__=='__main__':sys.exit(main())

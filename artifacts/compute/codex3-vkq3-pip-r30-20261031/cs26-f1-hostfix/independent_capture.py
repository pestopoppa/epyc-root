#!/usr/bin/env python3
"""CS-26.F1 independent-arm native capture draft; not yet qualified or READY."""
import hashlib,json,os,pathlib,re,signal,subprocess,sys,tempfile,threading,time
D=pathlib.Path(__file__).resolve().parent;BIN='/mnt/raid0/llm/kernels/production/cpu';SPEECH='/mnt/raid0/llm/kernels/builds/stt-20260731-b30737922/bin';L=D.parent/'lex2'; MODEL='/mnt/raid0/llm/models/Qwen3-1.7B-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf';W='/mnt/raid0/llm/models/whisper-ggml/ggml-large-v3-turbo.bin';TINY='/mnt/raid0/llm/models/whisper-ggml/ggml-tiny.bin';P='/mnt/raid0/llm/models/ggml-parakeet-tdt-0.6b-v3-f16.bin';N='/mnt/raid0/llm/models/nemo-speech-nemotron35-1c8deae'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def birth(pid):
 try:return pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
 except (OSError,IndexError):return None
def atom(p,obj):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(obj,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['F1_MODE'];assert mode in ('smoke','full');out=D/os.environ.get('F1_OUT','run');out.mkdir(exist_ok=True);aff=sorted(os.sched_getaffinity(0));cpus=aff[:2 if mode=='smoke' else 8];cpu=','.join(map(str,cpus));deadline=int(os.environ['FILLER_DEADLINE'])-30;fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_text() if gp and gp.exists() else None
 if mode=='full' and (len(cpus)!=8 or not grant):raise RuntimeError('quarter grant absent')
 stopped=False
 def handle(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handle);signal.signal(signal.SIGINT,handle)
 def stop():return stopped or (D/'STOP').exists() or time.time()>=deadline
 def partial(reason):
  p=out/'.partial.tmp';p.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(p,out/'PARTIAL.json')
 def env(lib):
  x=os.environ.copy();x.update(LD_LIBRARY_PATH=str(lib),OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1');return x
 def speech_cmd(arm,clip):
  if arm.startswith('whisper-'):
   th=int(arm.rsplit('-',1)[1]);binary=str(pathlib.Path(SPEECH)/'whisper-cli') if 'production' in arm else str(D/'whisper-build/bin/whisper-cli');lib=SPEECH if 'production' in arm else str(D/'whisper-build/bin');return ['taskset','-c',cpu,binary,'-m',TINY if mode=='smoke' else W,'-f',clip,'-ng','-nfa','-t',str(th if mode=='full' else 1),'-bo','1','-bs','1','-tp','0','-nf','-l','en','-nt'],env(lib)
  if arm=='in-tree-parakeet-1':return ['taskset','-c',cpu,str(pathlib.Path(SPEECH)/'parakeet-cli'),'-m',P,'-ng','-t','1','-f',clip],env(SPEECH)
  th=int(arm.rsplit('-',1)[1]);x=env(str(L/'install/lib')+':/mnt/raid0/llm/tmp/codex3-cs8-stt2-nemospeech-20261030/deps/prefix/usr/lib/x86_64-linux-gnu');x['LEX2_SPM_PATH']=N+'/tokenizer.model';return ['taskset','-c',cpu,str(L/'install/bin/nemo-speech'),'transcribe',clip,'--model',N+'/nemotron-3.5-asr-streaming-0.6b.q8_0.gguf','--device','cpu','--stream','--asr.backend.threads',str(th),'--no-warmup'],x
 clips=json.loads((D/'CLIPS.json').read_text())['clips'];plan=json.loads((D/'INDEPENDENT-PLAN.json').read_text());arms=[a['id'] for a in plan['arms']];blocks=plan['blocks']
 if mode=='smoke':clips=clips[1:2];arms=['whisper-production-1'];blocks=1
 total=len(clips)*len(arms)*blocks;counts={'ok':0,'failure':0,'unknown':0}
 for b in range(blocks):
  for arm in arms:
   for clip in clips:
    key=hashlib.sha256(f'{b}|{arm}|{clip["id"]}'.encode()).hexdigest();exp=out/(key+'.exposure.json');result=out/(key+'.result.json');log=out/(key+'.native.jsonl');binding={'schema':'cs26.f1.independent-attempt.v1','plan_sha256':sha(D/'INDEPENDENT-PLAN.json'),'clip_manifest_sha256':sha(D/'CLIPS.json'),'input_catalog_sha256':sha(D/'INPUTS.sha256'),'arm':arm,'block':b,'clip_id':clip['id'],'wav_sha256':clip['wav_sha256'],'affinity':cpus,'grant_id':fid,'grant_text':grant,'mode':mode}
    if sha(clip['wav'])!=clip['wav_sha256']:raise RuntimeError('clip drift')
    if result.exists():
     r=json.loads(result.read_text());e=json.loads(exp.read_text())
     for k in ('plan_sha256','clip_manifest_sha256','input_catalog_sha256','arm','block','clip_id','wav_sha256','mode'):
      if e['binding'][k]!=binding[k]:raise RuntimeError('cached binding drift '+k)
     if r['binding']!=e['binding'] or r['native_log_sha256']!=sha(log) or r['stdout_sha256']!=sha(out/(key+'.stdout')) or r['stderr_sha256']!=sha(out/(key+'.stderr')) or r['solo_stdout_sha256']!=sha(out/(key+'.solo.stdout')) or r['solo_stderr_sha256']!=sha(out/(key+'.solo.stderr')):raise RuntimeError('cached evidence drift')
     counts[r['status']]+=1;continue
    if exp.exists():
     old=json.loads(exp.read_text())['binding']
     for k in ('plan_sha256','clip_manifest_sha256','input_catalog_sha256','arm','block','clip_id','wav_sha256','mode'):
      if old[k]!=binding[k]:raise RuntimeError('exposed immutable binding drift '+k)
     counts['unknown']+=1;continue
    if stop() or (mode=='full' and time.time()+1850>=deadline):partial('before pair or insufficient budget');return 75
    atom(exp,{'binding':binding,'epoch':time.time()});active=[];events=[];reader_threads={};lock=threading.Lock()
    def record(v):
     with lock:
      events.append(v)
      with log.open('a') as f:f.write(json.dumps(v,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    def neighbour(label):
     args=['taskset','-c',cpu,BIN+'/llama-bench','-m',SMALL if mode=='smoke' else MODEL,'-p','0','-n',str(1 if mode=='smoke' else 32),'-t',str(len(cpus)),'-r','400','--progress','-o','jsonl','-ngl','0'];p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env(BIN),text=True,bufsize=1);active.append(p);record({'kind':'neighbor_start','label':label,'pid':p.pid,'birth':birth(p.pid),'epoch':time.time(),'argv':args})
     def read():
      for line in p.stderr:
       record({'kind':'progress' if 'generation run' in line or 'warmup' in line else 'neighbor_stderr','label':label,'pid':p.pid,'epoch':time.time(),'text':line.strip()})
     reader_threads[p.pid]=threading.Thread(target=read,daemon=True);reader_threads[p.pid].start();return p
    def end(p,label):
     if p.poll() is None:
      p.terminate()
      try:p.wait(5)
      except subprocess.TimeoutExpired:p.kill();p.wait()
     if p.pid in reader_threads:
      reader_threads[p.pid].join(5)
      if reader_threads[p.pid].is_alive():raise RuntimeError('neighbor stderr reader not drained')
     record({'kind':'drain','label':label,'pid':p.pid,'rc':p.returncode,'epoch':time.time()})
    def wait_progress(label,count,limit):
     endtime=time.monotonic()+limit
     while time.monotonic()<endtime and not stop():
      if sum(e['kind']=='progress' and e['label']==label and 'generation run' in e['text'] for e in list(events))>=count:return True
      time.sleep(.1)
     return False
    def watch_exit(proc):
     data={}
     def watcher():
      proc.wait();data['mono']=time.monotonic();data['epoch']=time.time()
     th=threading.Thread(target=watcher,daemon=True);th.start();return th,data
    try:
     cmd,ee=speech_cmd(arm,clip['wav']);solo_out=out/(key+'.solo.stdout');solo_err=out/(key+'.solo.stderr');solo_samples=[];solo_timedout=False
     with solo_out.open('xb') as stdout,solo_err.open('xb') as stderr:
      solo=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=ee);active.append(solo);solo_start=time.monotonic();solo_watch,solo_end=watch_exit(solo);record({'kind':'solo_start','pid':solo.pid,'birth':birth(solo.pid),'epoch':time.time(),'argv':cmd})
      while solo.poll() is None:
       try:
        task=pathlib.Path('/proc')/str(solo.pid)/'task';ss=[]
        for q in task.iterdir():
         stat=q.joinpath('stat').read_text().rsplit(') ',1)[1].split();ss.append({'tid':int(q.name),'utime_ticks':int(stat[11]),'stime_ticks':int(stat[12])})
        solo_samples.append({'epoch':time.time(),'threads':ss});record({'kind':'solo_thread_ticks',**solo_samples[-1]})
       except (OSError,ValueError):pass
       if stop() or time.monotonic()-solo_start>=600:
        solo_timedout=not stop();end(solo,'solo-timeout' if solo_timedout else 'solo-stop');break
       time.sleep(.5)
      solo_watch.join(5)
      if solo_watch.is_alive() or 'mono' not in solo_end:raise RuntimeError('solo exit watcher not drained')
      solo_elapsed=solo_end['mono']-solo_start;solo_rc=solo.poll();record({'kind':'solo_end','epoch':solo_end['epoch'],'rc':solo_rc,'elapsed_s':solo_elapsed})
     if stop():partial('interrupted exposed solo');return 75
     before=neighbour('A-before');a=wait_progress('A-before',3,150 if mode=='full' else 90);end(before,'A-before')
     if stop():partial('interrupted exposed neighbor baseline');return 75
     co=neighbour('B');ready=wait_progress('B',2,150 if mode=='full' else 90)
     if stop():partial('interrupted exposed neighbor warmup');return 75
     cmd,ee=speech_cmd(arm,clip['wav']);so=out/(key+'.stdout');se=out/(key+'.stderr');t0=time.time();ticks=[];speech_timedout=False
     with so.open('xb') as stdout,se.open('xb') as stderr:
      speech=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=ee);active.append(speech);record({'kind':'speech_start','pid':speech.pid,'birth':birth(speech.pid),'epoch':t0,'argv':cmd});start=time.monotonic();speech_watch,speech_end=watch_exit(speech)
      while speech.poll() is None:
       try:
        task=pathlib.Path('/proc')/str(speech.pid)/'task';sample=[]
        for q in task.iterdir():
         stat=q.joinpath('stat').read_text().rsplit(') ',1)[1].split();sample.append({'tid':int(q.name),'utime_ticks':int(stat[11]),'stime_ticks':int(stat[12])})
        ticks.append({'epoch':time.time(),'threads':sample});record({'kind':'thread_ticks',**ticks[-1]})
       except (OSError,ValueError):pass
       if stop() or time.monotonic()-start>=600:
        speech_timedout=not stop();end(speech,'speech-timeout' if speech_timedout else 'speech-stop');break
       time.sleep(.5)
      speech_watch.join(5)
      if speech_watch.is_alive() or 'mono' not in speech_end:raise RuntimeError('speech exit watcher not drained')
      elapsed=speech_end['mono']-start;rc=speech.poll();t1=speech_end['epoch'];record({'kind':'speech_end','epoch':t1,'rc':rc,'elapsed_s':elapsed});end(co,'B')
     if stop():partial('interrupted exposed pair');return 75
     after=neighbour('A-after');c=wait_progress('A-after',3,150 if mode=='full' else 90);end(after,'A-after')
     if stop():partial('interrupted exposed pair');return 75
     events.sort(key=lambda e:e['epoch']);runs=[e['epoch'] for e in events if e['kind']=='progress' and e['label']=='B' and 'generation run' in e['text']];inside=[{'start':x,'end':y,'tokens_per_s':(1 if mode=='smoke' else 32)/(y-x)} for x,y in zip(runs,runs[1:]) if t0<=x<y<=t1];status='failure' if rc!=0 or solo_rc!=0 else 'ok' if a and ready and c and inside and ticks and solo_samples else 'unknown';atom(result,{'binding':binding,'status':status,'solo_rc':solo_rc,'solo_wall_s':solo_elapsed,'solo_rtf':solo_elapsed/clip['duration_s'] if solo_rc==0 else None,'solo_timeout_counted_above_cap':solo_timedout,'solo_thread_cpu_tick_samples':solo_samples,'solo_stdout_sha256':sha(solo_out),'solo_stderr_sha256':sha(solo_err),'speech_rc':rc,'speech_wall_s':elapsed,'rtf':elapsed/clip['duration_s'] if rc==0 else None,'timeout_counted_above_cap':speech_timedout,'neighbor_intervals':inside,'thread_cpu_tick_samples':ticks,'native_log_sha256':sha(log),'stdout_sha256':sha(so),'stderr_sha256':sha(se),'quality_verdict':None});counts[status]+=1
    finally:
     for p in active:
      if p.poll() is None:end(p,'finally')
 atom(out/'TERMINAL.json',{'partial':False,'state':'complete_raw' if not counts['unknown'] and not counts['failure'] else 'incomplete_raw','scope':'independent arms only','counts':counts,'expected_pairs':total,'quality_verdict':None});return 0
if __name__=='__main__':sys.exit(main())

#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,subprocess,sys,tempfile,time
D=pathlib.Path(__file__).resolve().parent
manifest=pathlib.Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/inf79-speech-inference-ready/fleurs-select-q2/evidence/manifest.json')
reference=pathlib.Path('/mnt/raid0/llm/tmp/codex-cs8-cpu-full-20261028/full-attempts/1793217501197626296/COMPLETE.json')
model=pathlib.Path('/mnt/raid0/llm/models/parakeet-tdt-0.6b-v3-F16.gguf'); binary=D/'build/bin/transcribe-cli'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
 return h.hexdigest()
def write(path,obj):
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.write-')
 with os.fdopen(fd,'w') as f: json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
def disposition(out,i,binding):
 exposure=out/f'{i:02d}.exposure.json'; result=out/f'{i:02d}.json'
 if result.exists() and not exposure.exists(): raise RuntimeError('result without exposure')
 if not exposure.exists(): return 'unexposed'
 x=json.loads(exposure.read_text())
 if x.get('binding')!=binding: raise RuntimeError('exposure binding mismatch')
 if not result.exists(): return 'unknown'
 r=json.loads(result.read_text())
 if r.get('binding')!=binding or r.get('clip_id')!=binding['clip_id']: raise RuntimeError('result binding mismatch')
 for key in ('stdout','stderr'):
  p=out/f'{i:02d}.{key}'
  if not p.is_file() or sha(p)!=r.get(key+'_sha256'): raise RuntimeError('native output changed')
 if r.get('child_reaped') is not True or not isinstance(r.get('rc'),int): raise RuntimeError('invalid child completion')
 if r['rc']==0 and isinstance(r.get('transcript'),str): return 'success'
 return 'failed'
def main():
 smoke=os.environ.get('CS8_SMOKE')=='1';out=D/('smoke-result' if smoke else 'results');out.mkdir(exist_ok=True)
 refs=json.loads(reference.read_text())['results'];records={x['clip_id']:x for x in json.loads(manifest.read_text())['records']}
 if len(refs)!=40 or len({x['clip_id'] for x in refs})!=40: raise RuntimeError('reference cohort invalid')
 limit=time.time()+240 if smoke else int(os.environ['FILLER_DEADLINE'])-45
 pins={'source_commit':'db678a031cf4c524bcab2c45a0dc6a7813106e4a','model_sha256':sha(model),'binary_sha256':sha(binary),'transcribe_lib_sha256':sha(D/'install/lib/libtranscribe.so.0.4.0'),'source_manifest_sha256':sha(D/'SOURCE-SHA256SUMS'),'manifest_sha256':sha(manifest),'reference_sha256':sha(reference)}
 if pins['model_sha256']!='d9ec7e2c39da7b4fec3e01e71e82c7f7bbe97741e08c0c054091bf3d520a41d3': raise RuntimeError('model hash mismatch')
 pins_path=out/'pins.json'
 if pins_path.exists() and json.loads(pins_path.read_text())['pins']!=pins: raise RuntimeError('resume pin mismatch')
 if not pins_path.exists(): write(pins_path,{'pins':pins,'co_tenancy':'UNKNOWN','affinity':sorted(os.sched_getaffinity(0)),'environment':{k:os.environ.get(k) for k in ('LD_LIBRARY_PATH','OMP_NUM_THREADS','FILLER_ID','FILLER_CPUS','WS58_REGIONS')},'captured_epoch':time.time(),'smoke_unsealed':smoke})
 stopped=False
 def stop(sig,frame):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 selected=refs[:1] if smoke else refs; bindings=[]
 for ref in selected:
  rec=records[ref['clip_id']];bindings.append({'clip_id':ref['clip_id'],'wav_sha256':ref['wav_sha256'],'reference_transcript_sha256':hashlib.sha256(ref['transcript'].encode()).hexdigest(),'pins':pins})
 for i,(ref,binding) in enumerate(zip(selected,bindings)):
  if disposition(out,i,binding)!='unexposed': continue
  if stopped or (D/'STOP').exists() or time.time()+30>=limit: write(out/'partial.json',{'partial':True,'next':i});return 75
  wav=pathlib.Path(records[ref['clip_id']]['wav_path'])
  if sha(wav)!=ref['wav_sha256']: raise RuntimeError('WAV digest mismatch')
  args=[str(binary),'-m',str(model),'--backend','cpu','--threads','1','--timestamps','none',str(wav)]
  write(out/f'{i:02d}.exposure.json',{'binding':binding,'args':args,'exposed_epoch':time.time()})
  stdout_path=out/f'{i:02d}.stdout';stderr_path=out/f'{i:02d}.stderr';start=time.monotonic();started_epoch=time.time()
  with stdout_path.open('w') as stdout_file,stderr_path.open('w') as stderr_file:
   p=subprocess.Popen(args,stdout=stdout_file,stderr=stderr_file,text=True)
   while p.poll() is None:
    if stopped or (D/'STOP').exists() or time.time()>=limit:
     p.terminate()
     try:p.wait(5)
     except subprocess.TimeoutExpired:p.kill();p.wait()
     write(out/'partial.json',{'partial':True,'next':i,'interrupted_child':p.pid,'child_reaped':True,'child_rc':p.returncode});return 75
    time.sleep(.1)
  stdout=stdout_path.read_text();lines=[line[6:] for line in stdout.splitlines() if line.startswith('text: ')];transcript=lines[0] if len(lines)==1 else None
  write(out/f'{i:02d}.json',{'binding':binding,'clip_id':ref['clip_id'],'wall_s':time.monotonic()-start,'transcript':transcript,'reference_transcript':ref['transcript'],'exact_text_equal':transcript==ref['transcript'].strip() if transcript is not None else None,'rc':p.returncode,'started_epoch':started_epoch,'finished_epoch':time.time(),'child_pid':p.pid,'child_reaped':True,'stdout_sha256':sha(stdout_path),'stderr_sha256':sha(stderr_path)})
 states=[disposition(out,i,b) for i,b in enumerate(bindings)]
 if stopped or (D/'STOP').exists() or time.time()>=limit: write(out/'partial.json',{'partial':True,'states':states});return 75
 if all(x=='success' for x in states):write(out/'COMPLETE.json',{'count':len(states),'diagnostic_only':True,'partial':False,'states':states})
 else:write(out/'TERMINAL-INCOMPLETE.json',{'count':len(states),'diagnostic_only':True,'partial':False,'states':states})
 return 0
if __name__=='__main__':sys.exit(main())

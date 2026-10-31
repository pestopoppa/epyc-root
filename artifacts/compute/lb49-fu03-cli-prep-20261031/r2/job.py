#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,subprocess,sys,time
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r2')
BASE=pathlib.Path('/mnt/raid0/llm/tmp/lb49-codex-evidence-20261028')
SMOKE=sys.argv[1]=='smoke'; tag=sys.argv[2]; out=D/tag; out.mkdir(exist_ok=True)
model=pathlib.Path('/mnt/raid0/llm/models/gemma-3-1b-it-Q8_0.gguf') if SMOKE else pathlib.Path('/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf')
stop=pathlib.Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE']); threads=2 if SMOKE else 24
state={'partial':True,'diagnostic_only':True,'full_target_tested':not SMOKE,'arms':[]}
# Bind the exact original shard digests, not a newly accepted mutable model.
pins=json.loads(pathlib.Path('/mnt/raid0/llm/tmp/lb49-r11-source-draft-20261028/pins.json').read_text())
models=[pins['smoke_model']] if SMOKE else pins['models']
state['models_verified']=[]
state['pins_sha256']=hashlib.sha256(pathlib.Path('/mnt/raid0/llm/tmp/lb49-r11-source-draft-20261028/pins.json').read_bytes()).hexdigest()
if not SMOKE:
 r=subprocess.run(['/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r2/ram_admit.sh','739','ds41'],capture_output=True,text=True)
 if r.returncode: raise RuntimeError('RAM admission refused: '+r.stdout+r.stderr)
for item in models:
 path=pathlib.Path(item['path']); h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(8*1024*1024):
   h.update(chunk)
   if stop.exists() or time.time()>deadline-20:
    (out/'PARTIAL.json').write_text(json.dumps(state)); sys.exit(75)
 if h.hexdigest()!=item['sha256']: raise RuntimeError('model sha mismatch '+str(path))
 state['models_verified'].append({'path':str(path),'sha256':h.hexdigest(),'size':path.stat().st_size})

def save():
 p=out/'PARTIAL.json'; t=p.with_suffix('.tmp'); t.write_text(json.dumps(state,indent=2)+'\n'); os.replace(t,p)
def interrupted(): return stop.exists() or time.time()>deadline-20
for name,build,extra in [('baseline-1','off',[]),('baseline-2','off',[]),('candidate','feature',['--cpu-iqk-fa','on'])]:
 if interrupted(): save();sys.exit(75)
 marker=out/(name+'.started'); done=out/(name+'.json')
 if done.exists(): state['arms'].append(json.loads(done.read_text()));continue
 if marker.exists(): state['unknown_interrupted_arm']=name;save();sys.exit(75)
 marker.write_text('exposed\n');fd=os.open(marker,os.O_RDONLY);os.fsync(fd);os.close(fd)
 bindir=BASE/('build-deterministic-'+build)/'bin'; exe=bindir/'llama-cli'
 env=os.environ.copy(); env.update(LD_LIBRARY_PATH=str(bindir),OMP_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='');env.pop('LD_PRELOAD',None);env.pop('LD_AUDIT',None)
 verify='/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh'
 with (out/(name+'-linkage.log')).open('wb') as f:
  if subprocess.run([verify,str(exe),str(bindir)],env=env,stdout=f,stderr=subprocess.STDOUT).returncode: raise RuntimeError('linkage')
 cmd=[str(exe),'-m',str(model),'--device','none','-ngl','0','-fa','on','--perf','-t',str(threads),'-tb',str(threads),'-c','512','-n','8','--temp','0','--seed','42','--single-turn','--no-display-prompt','-p','The capital of France is']+extra
 start=time.monotonic(); log=out/(name+'.log')
 with log.open('wb') as f:
  p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  while p.poll() is None:
   if interrupted():
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL);p.wait()
    state['unknown_interrupted_arm']=name;state['child_rc']=p.returncode;save();sys.exit(75)
   time.sleep(.2)
 if p.returncode: raise RuntimeError(f'{name} rc {p.returncode}')
 data=log.read_bytes()
 if b'Generation:' not in data or b'Exiting...' not in data: raise RuntimeError('missing generation/exit')
 arm={'arm':name,'argv':cmd,'rc':p.returncode,'wall_s':time.monotonic()-start,'log':str(log),'sha256':hashlib.sha256(data).hexdigest()}
 done.write_text(json.dumps(arm,indent=2)+'\n');state['arms'].append(arm);save()
state['partial']=False
(out/'RESULT.json').write_text(json.dumps(state,indent=2)+'\n')
(out/'PARTIAL.json').unlink(missing_ok=True)

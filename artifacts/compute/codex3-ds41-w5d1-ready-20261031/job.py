#!/usr/bin/python3
"""Private DS41-W5d.1 runner draft. Not qualified or published."""
import hashlib, importlib.util, json, os, pathlib, signal, subprocess, sys, time
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-wholehost-20261031-0310')
B='/mnt/raid0/llm/kernels/builds/cpu-20261023-141e4bcf5-lbh/bin'
MODEL='/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf'
SMALL='/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf'
interrupted_signal=False
def on_signal(_signum,_frame):
 global interrupted_signal
 interrupted_signal=True
signal.signal(signal.SIGTERM,on_signal); signal.signal(signal.SIGINT,on_signal)
mode=sys.argv[1]; assert mode in ('control','full')
out=D/(('control-'+sys.argv[2]) if mode=='control' else 'full'); out.mkdir(exist_ok=True)
stop=pathlib.Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE'])
cpus=os.environ['FILLER_CPUS']
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
if digest(B+'/llama-bench')!='f78b8ba80b76a215caca66dfd04119c56aa4ef864e0ea9978ef1b9234b5b0214': raise SystemExit('benchmark identity mismatch')
if digest(D/'original_analyze.py')!='bbb1736a16a499fbf18d804633abfa26f492625bbf31f83f56e796851c6b7eb3': raise SystemExit('analyzer identity mismatch')
env=os.environ.copy(); env.update(OMP_PROC_BIND='spread',OMP_PLACES='cores',OMP_WAIT_POLICY='active',OMP_DYNAMIC='false',GGML_IQK='1',LD_LIBRARY_PATH=B)
def status(state, **kw):
 p=out/'PARTIAL.json'; q=out/'PARTIAL.tmp'; q.write_text(json.dumps(dict(state=state,partial=state!='complete',**kw),indent=2)); os.replace(q,p)
def quiet():
 def sample():
  x=list(map(int,pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:8])); return sum(x),x[3]+x[4]
 a=sample(); time.sleep(6); b=sample(); busy=100*(1-(b[1]-a[1])/(b[0]-a[0]))
 with (out/'quiet.jsonl').open('a') as f: f.write(json.dumps({'time':time.time(),'busy_percent':busy})+'\n')
 return busy<=3.0
def run(tag, warm=False):
 if interrupted_signal or stop.exists() or deadline-time.time()<30: status('interrupted',at=tag); return 75
 if mode=='full':
  if not quiet(): status('quiet_refused',at=tag); return 75
  if subprocess.run(['/bin/bash','/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh','739','ds41']).returncode: status('admission_refused',at=tag); return 75
  argv=['taskset','-c',cpus,'numactl','--interleave=all',B+'/llama-bench','-m',MODEL,'-t','48','-fa','1','-mmp','0','-p','512','-n','128','-r','3','-o','json']
 else:
  argv=['taskset','-c',cpus,B+'/llama-bench','-m',SMALL,'-t','2','-fa','1','-mmp','0','-p','128','-n','32','-r','1','-o','json']
 (out/(tag+'.argv.json')).write_text(json.dumps(argv)); started=time.time()
 attempt=tag+'.attempt-'+str(time.time_ns())
 with (out/(attempt+'.json.tmp')).open('w') as stdout, (out/(attempt+'.stderr')).open('w') as stderr, (out/(attempt+'.residency.jsonl')).open('w') as samples:
  p=subprocess.Popen(argv,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
  interrupted=False
  while p.poll() is None:
   if interrupted_signal or stop.exists() or time.time()>=deadline-15 or (mode=='full' and time.time()-started>=1800):
    interrupted=True; os.killpg(p.pid,signal.SIGTERM)
    try: p.wait(timeout=5)
    except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); p.wait()
    break
   try:
    s=pathlib.Path('/proc/%d/status'%p.pid).read_text(); fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in s.splitlines() if line.startswith(('VmRSS:','RssAnon:','RssFile:'))}; samples.write(json.dumps({'time':time.time(),'pid':p.pid,**fields})+'\n'); samples.flush()
   except FileNotFoundError: pass
   time.sleep(1)
  rc=p.wait()
 if interrupted: status('interrupted',at=tag,rc=rc); return 75
 if rc: status('failed',at=tag,rc=rc); return rc
 tmp=out/(attempt+'.json.tmp')
 try:
  data=json.loads(tmp.read_text()); assert isinstance(data,list) and data
 except Exception as e: status('invalid',at=tag,error=str(e)); return 1
 os.replace(tmp,out/(tag+'.json'))
 if mode=='full':
  spec=importlib.util.spec_from_file_location('original_analyze',str(D/'original_analyze.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
  try: values, within=mod.check_proc_a(data,' '.join(argv),3)
  except Exception as e:
   (out/'VOID').write_text(str(e)); status('invalid',at=tag,error=str(e)); return 1
  (out/(tag+'.checked.json')).write_text(json.dumps({'stage':'a','seq':int(tag[-2:]) if tag.startswith('sample-') else -1,'ok':True,'values':values,'within_cv_pct':within}))
 (out/(tag+'.completed.json')).write_text(json.dumps({'started_unix':started,'ended_unix':time.time(),'elapsed_s':time.time()-started,'warmup':warm,'argv':argv,'native_result_sha256':digest(out/(tag+'.json')),'attempt':attempt}))
 return 0
if mode=='full':
 if cpus != '0-95': raise SystemExit('whole-host physical grant required')
 check=subprocess.run(['/bin/bash','/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',B+'/llama-bench',B],capture_output=True,text=True)
 (out/'linkage.txt').write_text(check.stdout+check.stderr)
 if check.returncode: raise SystemExit('linkage failed')
 identity=[]
 for i in range(1,10):
  p=pathlib.Path(MODEL.replace('00001-of-00009','%05d-of-00009'%i)); size=p.stat().st_size; h=hashlib.sha256()
  with p.open('rb') as f:
   h.update(f.read(64*1024**2)); f.seek(max(0,size-64*1024**2)); h.update(f.read(64*1024**2))
  identity.append({'path':str(p),'size':size,'edge_sha256':h.hexdigest()})
 path=out/'model-identity.json'
 if path.exists() and json.loads(path.read_text())!=identity: raise SystemExit('model identity changed between segments')
 if not path.exists(): path.write_text(json.dumps(identity,indent=2))
 capture={'schema':'ds41-w5d1-native-capture/v1','captured_before_unit_unix':time.time(),'predeclared_sha256':digest(D/'PREDECLARED.md'),'source_catalog_sha256':digest(D/'SOURCES.sha256'),'launcher_sha256':digest(D/'launch.sh'),'benchmark_sha256':digest(B+'/llama-bench'),'benchmark_mtime_ns':os.stat(B+'/llama-bench').st_mtime_ns,'model_identity_sha256':digest(path),'regions':cpus,'gpu_quiet':'exclusive via launcher grant','environment':{k:env[k] for k in ('OMP_PROC_BIND','OMP_PLACES','OMP_WAIT_POLICY','OMP_DYNAMIC','GGML_IQK','LD_LIBRARY_PATH')},'stopfile':str(stop),'deadline':deadline,'scope':'native capture; projection and canary pending'}
 (out/('capture-start-'+str(time.time_ns())+'.json')).write_text(json.dumps(capture,indent=2))
# An interrupted unit is discarded and repeated; completed, predeclared units survive.
if (out/'VOID').exists(): status('invalid',error=(out/'VOID').read_text()); sys.exit(1)
for tag in (['control'] if mode=='control' else ['warmup']+['sample-%02d'%i for i in range(6)]):
 if (out/(tag+'.completed.json')).exists(): continue
 rc=run(tag,tag=='warmup')
 if rc: sys.exit(rc)
if mode=='full':
 spec=importlib.util.spec_from_file_location('original_analyze',str(D/'original_analyze.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
 rows=[json.loads((out/('sample-%02d.checked.json'%i)).read_text()) for i in range(6)]
 result=mod.build_a(rows); result['w5d1_tg128_process_cv_at_most_4_pct']=result['metrics']['tg128']['cv_pct']<=4.0; (out/'RESULT.json').write_text(json.dumps(result,indent=2))
else:
 (out/'RESULT.json').write_text(json.dumps({'control':True,'complete':True}))
status('complete'); (out/'SUCCESS').write_text('complete\n')

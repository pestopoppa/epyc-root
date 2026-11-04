#!/usr/bin/env python3
"""Historical E1/A1 chain capture with a single server, deadline, and owned-PID VRAM guard."""
import argparse,json,os,signal,subprocess,sys,threading,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
IMAGE=Path('/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin')
MODEL=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TEMPLATE=Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
PORT=int(os.environ.get('FILLER_PORT','18438'))
KFD=Path('/sys/class/kfd/kfd/proc'); GIB=1024**3; SAFE=63.8; TARGET=55.0
CHILDREN=[]; ACTIVE_ROOT=None; ACTIVE_RESULT=None; GUARD_STOP=threading.Event(); GUARD_HIT=threading.Event(); GUARD_PEAK=0.0; GUARD_THREAD=None

def put(p,x):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,indent=2)+'\n'); t.replace(p)
def stop(p):
 if p and p.poll() is None:
  p.terminate()
  try:p.wait(timeout=15)
  except subprocess.TimeoutExpired:p.kill(); p.wait(timeout=15)
def health(port):
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2) as r:return r.status==200
 except Exception:return False
def own_gib(pid):
 try:return sum(int(x.read_text()) for x in (KFD/str(pid)).glob('vram_*'))/GIB
 except (OSError,ValueError):return None
def guard(pid,root,server):
 global GUARD_PEAK
 while not GUARD_STOP.wait(.1):
  v=own_gib(pid)
  if v is None:continue
  GUARD_PEAK=max(GUARD_PEAK,v)
  if v>SAFE:
   GUARD_HIT.set(); put(root/'guard.json',{'status':'OWN_PID_VRAM_LIMIT','pid':pid,'vram_gib':v,'ceiling_gib':SAFE,'at':time.time()}); stop(server); return
def partial(reason):
 if ACTIVE_RESULT:put(ACTIVE_RESULT,{'status':'PARTIAL','partial':True,'reason':reason,'at':time.time()})
 if ACTIVE_ROOT:put(ACTIVE_ROOT/'partial.json',{'status':'PARTIAL','reason':reason,'at':time.time()})
def sigterm(_sig,_frame):
 partial('signal-or-stop-window'); raise SystemExit(75)
def check_chain(d):
 from validate_chain_capture import EXPECTED,validate
 callsfiles=list((d/'native').glob('*/*/calls.jsonl'))
 reportsfiles=list((d/'native').glob('*/*/report.json'))
 if len(callsfiles)!=1 or len(reportsfiles)!=1:raise RuntimeError(f'expected one calls/report file, got {len(callsfiles)}/{len(reportsfiles)}')
 calls=[json.loads(x) for x in callsfiles[0].read_text().splitlines() if x.strip()]
 report=json.loads(reportsfiles[0].read_text())
 attr=json.loads((d/'phase-attribution.json').read_text())
 samples=[json.loads(x) for x in (d/'kfd.jsonl').read_text().splitlines() if x.strip()]
 issues=validate(report,calls,attr,samples,EXPECTED)
 if issues:raise RuntimeError('native chain validation failed: '+'; '.join(issues))
 return report,calls,attr,samples

def run(mode):
 global ACTIVE_ROOT,ACTIVE_RESULT,GUARD_PEAK
 deadline=float(os.environ['FILLER_DEADLINE']); cpus=os.environ['FILLER_CPUS']
 if mode=='smoke':
  dry=Path(os.environ['FILLER_DRYRUN_DIR']); d=dry/'capture'; ACTIVE_RESULT=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
 else:
  d=HERE/'out/chain-E1-A1'; ACTIVE_RESULT=HERE/'out/RESULT.json'
 ACTIVE_ROOT=d; d.mkdir(parents=True,exist_ok=True); (d/'slots').mkdir(exist_ok=True)
 if not MODEL.is_file() or MODEL.stat().st_size!=29047086048:raise RuntimeError('pinned model path/size mismatch')
 snap=json.loads((HERE/'model-pregrant.json').read_text()); st=MODEL.stat()
 if snap.get('path')!=str(MODEL) or snap.get('size')!=st.st_size or snap.get('inode')!=st.st_ino or snap.get('mtime_ns')!=st.st_mtime_ns:raise RuntimeError('model changed since pregrant snapshot')
 if not TEMPLATE.is_file() or not (IMAGE/'llama-server').is_file():raise RuntimeError('pinned E1 server/template missing')
 if subprocess.check_output(['ss','-ltnH',f'sport = :{PORT}']).strip():raise RuntimeError(f'port {PORT} occupied')
 if any(x.name.isdigit() for x in KFD.iterdir()):raise RuntimeError('foreign KFD process present')
 binary=IMAGE/'llama-server'; shim=HERE/'helper/libhipmalloc_trace.so'
 common=[str(binary),'-m',str(MODEL),'--host','127.0.0.1','--port',str(PORT),'-np','1','-t',str(min(8,len(os.sched_getaffinity(0)))),'-ub','2048','--flash-attn','on','--jinja','-ctk','q8_0','-ctv','q8_0','--no-mmap','-ngl','all','--cache-ram','0','--chat-template-file',str(TEMPLATE),'--device','ROCm0','--slot-save-path',str(d/'slots'),'--verbosity','4','-c','524288','--rope-scaling','yarn','--rope-scale','2','--yarn-orig-ctx','262144','--override-kv','qwen35.context_length=int:524288,qwen35.rope.scaling.type=str:yarn,qwen35.rope.scaling.factor=float:2,qwen35.rope.scaling.original_context_length=int:262144']
 env={k:v for k,v in os.environ.items() if not (k.startswith(('LLAMA_ARG_','GGML_CUDA_','ROCBLAS_')) or k in ('LD_PRELOAD','LD_LIBRARY_PATH'))}
 env.update(LD_LIBRARY_PATH=f'{IMAGE}:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib',HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0',GGML_IQK='1',OMP_NUM_THREADS='1',LD_PRELOAD=str(shim),KVU16H_SHIM_LOG=str(d/'hipmalloc.jsonl'))
 log=d/'server.log'; rf=log.open('ab'); p=subprocess.Popen(['taskset','-c',cpus,*common],env=env,stdout=rf,stderr=subprocess.STDOUT,start_new_session=True); CHILDREN.append(p)
 started=time.time(); put(d/'launch.json',{'argv':common,'pid':p.pid,'image':str(IMAGE),'image_manifest':str(HERE/'image.sha256'),'server_start_epoch':started,'deadline_epoch':deadline,'model_path':str(MODEL),'model_size_bytes':MODEL.stat().st_size,'model_hashing':'not performed inside grant; pregrant provenance gate required'})
 sampler=subprocess.Popen([sys.executable,str(HERE/'helper/kfd_sampler.py'),'--pid',str(p.pid),'--out',str(d/'kfd.jsonl'),'--interval','0.1'],stdout=(d/'sampler.log').open('w'),stderr=subprocess.STDOUT); CHILDREN.append(sampler)
 GUARD_THREAD=threading.Thread(target=guard,args=(p.pid,d,p),daemon=True); GUARD_THREAD.start()
 try:
  end=min(time.time()+280,deadline-60)
  while time.time()<end and p.poll() is None and not health(PORT):time.sleep(2)
  if p.poll() is not None or not health(PORT) or own_gib(p.pid) is None:raise RuntimeError('E1 server load/own-PID residency failed')
  maps=Path(f'/proc/{p.pid}/maps').read_text(); libs=sorted({x.split()[-1] for x in maps.splitlines() if 'libggml' in x and '.so' in x})
  if not libs or any(str(IMAGE) not in x for x in libs):raise RuntimeError(f'non-E1 ggml mapping: {libs}')
  put(d/'runtime-proof.json',{'pid':p.pid,'ggml_paths':libs,'kfd_path':str(KFD/str(p.pid)),'image':str(IMAGE),'at':time.time()})
  if time.time()>deadline-(90 if mode=='smoke' else 300):raise TimeoutError('insufficient time remains')
  if mode=='smoke':
   body=json.dumps({'prompt':'Explain one memory allocation in one short sentence.','n_predict':8}).encode()
   req=urllib.request.Request(f'http://127.0.0.1:{PORT}/completion',data=body,headers={'Content-Type':'application/json'})
   t0=time.time()
   with urllib.request.urlopen(req,timeout=min(60,max(1,deadline-time.time()-30))) as response: reply=json.load(response)
   t1=time.time()
   samples=[json.loads(x) for x in (d/'kfd.jsonl').read_text().splitlines() if x.strip()]
   if not reply.get('content') or not any(t0<=x['t']<=t1 and x.get('pid_vram_gib') is not None for x in samples):raise RuntimeError('smoke response or in-request own-PID KFD sample missing')
   timings=reply.get('timings') or {}; predicted_n=int(timings.get('predicted_n') or reply.get('tokens_predicted') or 0)
   predicted_ms=float(timings.get('predicted_ms') or 0); decode_tps=float(timings.get('predicted_per_second') or (predicted_n*1000/predicted_ms if predicted_ms>0 else 0))
   if predicted_n<=0 or decode_tps<=0:raise RuntimeError('native completion response lacks numeric predicted_n/decode_tps')
   smoke={'status':'DRYRUN_OK','scope':'native-entry-qualification','same_source_e1_a1_load':True,'first_completion_ok':True,'predicted_n':predicted_n,'decode_tps':decode_tps,'own_kfd_peak_gib':max(x['pid_vram_gib'] for x in samples if t0<=x['t']<=t1 and x.get('pid_vram_gib') is not None),'request_start':t0,'request_end':t1,'server_pid':p.pid,'at':time.time()}
   smoke['native_response']=reply; put(d/'smoke-response.json',smoke); put(ACTIVE_RESULT,smoke)
   return 0
  runenv=dict(os.environ,YARN_E1_RESULTS=str(d/'native'),YARN_E1_GATE=str(HERE/'out/gate'),YARN_E1_SEGMENT_TOKENS=str(HERE/'stage-token-counts.json'))
  cmd=['/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python',str(HERE/'yarn_needle.py'),'--arm','A1','--i-own-the-window','--port',str(PORT),'--server-log',str(log),'--suites','smoke,needle','--stages','128k,240k,400k,500k']
  with (d/'runner.log').open('w') as f:
   r=subprocess.Popen(cmd,env=runenv,stdout=f,stderr=subprocess.STDOUT); CHILDREN.append(r)
   while r.poll() is None and time.time()<deadline-30 and not GUARD_HIT.is_set():time.sleep(1)
   if GUARD_HIT.is_set():stop(r); partial('own-pid-vram-ceiling'); return 72
   if r.poll() is None:stop(r); partial('deadline-during-run'); return 75
   if r.returncode:partial(f'yarn_needle-rc-{r.returncode}'); return r.returncode
  subprocess.run([sys.executable,str(HERE/'analyze_phase.py'),str(d)],check=True,stdout=(d/'analyze.log').open('w'))
  report,calls,attr,samples=check_chain(d)
  own=[x['pid_vram_gib'] for x in samples if x.get('pid_vram_gib') is not None]
  peak=max(own) if own else None
  over=[x for x in samples if x.get('pid_vram_gib') is not None and x['pid_vram_gib']>TARGET]
  first=None
  if over:
   t=over[0]['t']; first=next((s for s,v in attr['stages'].items() if v['start']<=t<=v['end']),'smoke-or-inter-stage')
  decision={'criterion':'continuous-chain own-PID peak <=55 GiB','pass':peak is not None and peak<=TARGET,'peak_gib':peak,'first_phase_over_55_gib':first,'excess_gib':max(0,peak-TARGET) if peak is not None else None,'safety_ceiling_gib':SAFE}
  put(d/'complete.json',{'status':'COMPLETE','mode':'single_server_chain','image':'E1','arm':'A1','stages':['128k','240k','400k','500k'],'native_report':str(list((d/'native').glob('*/*/report.json'))[0]),'phase_attribution':str(d/'phase-attribution.json'),'continuous_chain_peak_gib':peak,'memory_criterion':decision,'server_pid':p.pid,'server_start_epoch':started,'at':time.time()})
  put(ACTIVE_RESULT,{'status':'COMPLETE','single_server':True,'steps':[['E1','A1',x] for x in ('128k','240k','400k','500k')],'memory_criterion':decision,'complete':str(d/'complete.json'),'at':time.time()})
  return 0
 except BaseException as e:
  partial(repr(e)); raise
 finally:
  GUARD_STOP.set()
  for c in CHILDREN[::-1]:stop(c)
  rf.close()
  if GUARD_THREAD:GUARD_THREAD.join(timeout=2)
  subprocess.run([str(HERE/'raw-seal.sh'),str(d)],check=True)

def main():
 global ACTIVE_ROOT
 ap=argparse.ArgumentParser(); ap.add_argument('--smoke',action='store_true'); args=ap.parse_args()
 mode='smoke' if args.smoke else 'full'
 if mode=='smoke' and not os.environ.get('FILLER_DRYRUN_DIR'):raise RuntimeError('smoke requires isolated FILLER_DRYRUN_DIR')
 if mode=='smoke' and not os.environ.get('FILLER_DRYRUN_RESULT_PATH'):raise RuntimeError('smoke requires FILLER_DRYRUN_RESULT_PATH')
 signal.signal(signal.SIGTERM,sigterm)
 try:return run(mode)
 except SystemExit as e:
  if isinstance(e.code,int):return e.code
  return 1
 except BaseException as e:
  partial(repr(e)); return 1
 finally:
  GUARD_STOP.set()
  for child in CHILDREN[::-1]:stop(child)
  assert all(child.poll() is not None for child in CHILDREN), 'owned child survived cleanup'
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Grant-bound PFX-2 CPU probe; own server, private port and private state."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,time,urllib.request
P=pathlib.Path(__file__).resolve().parent
MODEL=pathlib.Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
BIN=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu/llama-server').resolve()
TEMPLATE=pathlib.Path('/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja')
PORT=18971

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()

def drain(p):
 if p is None:return True
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=20)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
 return p.poll() is not None

def admitted_threads(env, affinity):
 # Keeper qualification deliberately grants only one CPU quarter. Production
 # remains pinned to the original full physical-core grant and affinity.
 cpus = env.get('FILLER_CPUS', '')
 if env.get('FILLER_DRYRUN') == '1':
  quarters = {f'{start}-{start + 23}': set(range(start, start + 24)) for start in (0, 24, 48, 72)}
  if cpus not in quarters or set(affinity) != quarters[cpus]:
   raise ValueError('dryrun requires exactly the keeper-granted quarter')
  return 24
 if cpus != '0-95' or set(affinity) != set(range(96)):
  raise ValueError('real run requires full original 0-95 grant')
 return 96

def main():
 assert os.environ.get('FILLER_ID')=='handoff-rte-pfx2-v1-20261101'
 threads=admitted_threads(os.environ,os.sched_getaffinity(0))
 stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=int(os.environ['FILLER_DEADLINE'])
 assert time.time()+150<deadline and not stop.exists()
 assert digest(BIN)=='4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c'
 assert digest(TEMPLATE)==TEMPLATE.stem
 assert digest(P/'prefix.txt')=='d95770fbd35a31295e622715aed129e9c751c653c24a0ea1ce1500ff1c11357a'
 assert MODEL.stat().st_size==37801097504
 with MODEL.open('rb') as f:
  h=hashlib.sha256();h.update(f.read(64*1024**2));f.seek(-64*1024**2,2);h.update(f.read()); assert h.hexdigest()=='07b181eed5d3b8c0317427faea571256f2f6bb3d97265bf6ccc096f5e9dac6a9'
 with socket.socket() as s:s.bind(('127.0.0.1',PORT))
 phase='dryrun' if os.environ.get('FILLER_DRYRUN')=='1' else 'run'
 out=P/phase/str(time.time_ns());out.mkdir(parents=True)
 slots=out/'slots';slots.mkdir()
 argv=[str(BIN),'-m',str(MODEL),'--host','127.0.0.1','--port',str(PORT),'-np','4','-c','262144','-t',str(threads),'-ub','2048','--flash-attn','on','--jinja','-ctk','q8_0','-ctv','q8_0','--mlock','--no-mmap','--cache-ram','32768','--ctx-checkpoints','32','--chat-template-file',str(TEMPLATE),'--spec-type','draft-mtp','--spec-draft-n-max','4','--reasoning','off','--slot-save-path',str(slots)]
 env={k:v for k,v in os.environ.items() if not k.startswith(('GGML_','LLAMA_ARG_')) and k not in ('LD_PRELOAD','SHIM_NPROCS','OMP_NUM_THREADS')}
 env.update(LD_LIBRARY_PATH='/usr/lib/llvm-20/lib:'+str(BIN.parent),OMP_PROC_BIND='spread',OMP_PLACES='cores',OMP_WAIT_POLICY='active',OMP_DYNAMIC='false',KMP_BLOCKTIME='10',GGML_IQK='1',WINDOW_CONFIRMED='1')
 link=subprocess.run(['/bin/bash',str(P/'runtime/verify_ggml_linkage.sh'),str(BIN),str(BIN.parent)],env=env,text=True,capture_output=True)
 (out/'linkage.txt').write_text(link.stdout+link.stderr);assert link.returncode==0
 server=None;child=None;rc=1
 try:
  with (out/'server.log').open('w') as log:
   server=subprocess.Popen(['numactl','--interleave=all']+argv,env=env,stdout=log,stderr=subprocess.STDOUT)
   if os.environ.get('FILLER_PIDFILE'):
    with open(os.environ['FILLER_PIDFILE'],'a') as pf:pf.write(str(server.pid)+'\n')
   birth=pathlib.Path(f'/proc/{server.pid}/stat').read_text().rsplit(') ',1)[1].split()[19]
   ready=False; health_limit=min(deadline-120,time.time()+900)
   while time.time()<health_limit:
    if stop.exists():rc=75;return rc
    assert server.poll() is None,'server exited'
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=2) as response:
      if response.status==200:
       ss=subprocess.run(['ss','-ltnp',f'sport = :{PORT}'],capture_output=True,text=True,check=True).stdout
       if f'pid={server.pid},' in ss:ready=True;break
    except OSError:pass
    time.sleep(1)
   assert ready,'owned listener health not established'
   maps=pathlib.Path(f'/proc/{server.pid}/maps').read_text();assert 'libggml-cpu.so' in maps and 'libggml-hip.so' not in maps
   header={'schema':'epyc.rte_pfx2.header.v1','binary_mtime':time.ctime(BIN.stat().st_mtime),'cache_ram_mib':'32768','slot_prompt_similarity':'server default (flag absent)','n':4,'trials':5,'seed':20261021,'phase':phase,'role':'frontdoor','binary_sha256':digest(BIN),'model_edge_sha256':h.hexdigest(),'model_bytes':MODEL.stat().st_size,'template_sha256':digest(TEMPLATE),'prefix_sha256':digest(P/'prefix.txt'),'argv':argv,'pid':server.pid,'birth':birth,'window_end_unix':deadline,'slot_identity_caveat':'stream id_slot is not id_task; reuse/buffering cannot be excluded','window_claim':('keeper qualification quarter '+os.environ['FILLER_CPUS'] if phase=='dryrun' else 'filler region-lock 0-95 with gpu quiet exclusive'),'started_unix':time.time()}
   (out/'RUN_HEADER.json').write_text(json.dumps(header,indent=2)+'\n')
   cmd=[str(P/'runtime/bin/python3'),'-B',str(P/'probe.py'),'--server',f'http://127.0.0.1:{PORT}','--n','4','--trials','5','--prefix-file',str(P/'prefix.txt'),'--n-predict','16','--seed','20261021','--output',str(out/'probe.json')]
   child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
   while child.poll() is None:
    if time.time()>deadline+10:raise TimeoutError('probe exceeded deadline')
    time.sleep(1)
   rc=child.returncode
   if rc==0:
    data=json.loads((out/'probe.json').read_text());assert len(data['results'])==15
   return rc
 finally:
  a=drain(child);b=drain(server)
  (out/'drain.json').write_text(json.dumps({'child_dead':a,'server_dead':b})+'\n')
  if not a or not b:raise RuntimeError('owned process drain failed')
  if rc==0 and phase=='run':
   grant=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (os.environ['FILLER_ID']+'.grant')
   fields=dict(x.split('=',1) for x in grant.read_text().split() if '=' in x)
   assert fields.get('regions')=='0-95' and fields.get('start') and fields.get('end')
   sys.path.insert(0,str(P/'runtime/vidya'))
   from adapters.rte_pfx2_capture import write_belief_measurements
   write_belief_measurements(out,run_id=os.environ['PFX_INVOCATION'],producer='handoff-rte-pfx2-v1-20261101',probe_path=out/'probe.json',header_path=out/'RUN_HEADER.json',role='frontdoor',window={'window_id':os.environ['FILLER_ID'],'region_lock_claim':'0-95; role bench; gpu-quiet exclusive','start_utc':fields['start'],'end_utc':fields['end']})
  if rc==0:
   (P/phase/'COMPLETE.json').write_text(json.dumps({'output':str(out),'invocation':os.environ['PFX_INVOCATION'],'phase':phase,'status':'complete'})+'\n')
if __name__=='__main__':sys.exit(main())

#!/usr/bin/env python3
"""Provisional own-server supervisor; execution remains disabled pending review."""
import json,os,signal,subprocess,sys,time,urllib.request,datetime,hashlib
from pathlib import Path
import owned_drain,lock_witness,gpu_smoke_admission
D=Path(__file__).resolve().parent
PORT=18979
STORE=Path('/mnt/raid0/llm/kernels/production/gpu')
MODEL='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
TEMPLATE='/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja'
KFD=Path('/sys/class/kfd/kfd/proc')

def kfd():
 out={}
 for x in KFD.iterdir():
  if x.name.isdecimal():
   n=0
   for f in x.glob('vram_*'):
    try:n+=int(f.read_text())
    except (FileNotFoundError,ValueError):pass
   out[int(x.name)]=n
 return out

def owned_port(pid,port):
 inodes=set()
 for table in ('/proc/net/tcp','/proc/net/tcp6'):
  for line in Path(table).read_text().splitlines()[1:]:
   p=line.split()
   if p[3]=='0A' and int(p[1].split(':')[-1],16)==port:inodes.add(p[9])
 for fd in Path('/proc',str(pid),'fd').iterdir():
  try:
   if os.readlink(fd) in {f'socket:[{i}]' for i in inodes}:return True
  except FileNotFoundError:pass
 return False

def mapped_identity(pid,expected,digest):
 st=expected.stat();matched=[]
 for line in Path('/proc',str(pid),'maps').read_text().splitlines():
  f=line.split(maxsplit=5)
  if len(f)<6:continue
  dev=f[3].split(':')
  if len(dev)==2 and int(dev[0],16)==os.major(st.st_dev) and int(dev[1],16)==os.minor(st.st_dev) and int(f[4])==st.st_ino:matched.append(f[5])
 if not matched:raise RuntimeError('expected DSO inode not mapped: '+str(expected))
 with expected.open('rb') as fh:got=hashlib.file_digest(fh,'sha256').hexdigest()
 if got!=digest:raise RuntimeError('mapped DSO digest mismatch: '+str(expected))
 return {'expected':str(expected),'device':st.st_dev,'inode':st.st_ino,'sha256':got,'mapped_paths':sorted(set(matched))}

def main():
 if os.environ.get('PRB_NATIVE_REVIEWED')!='1':raise SystemExit('UNQUALIFIED: native supervisor not yet reviewed')
 started_epoch=time.time();started_mono=time.monotonic()
 mode=sys.argv[1];smoke=mode in ('smoke','cutoff')
 if mode not in ('smoke','cutoff','normal'):raise SystemExit(64)
 if owned_drain.children():raise RuntimeError('preexisting owned children')
 owned_drain.enable();stopped=[False]
 def stop(*_):stopped[0]=True
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,stop)
 flags=Path('/mnt/raid0/llm/tmp/compute-flags')
 stopfile=Path(os.environ['FILLER_STOPFILE']);end=int(os.environ['FILLER_END']);deadline=int(os.environ['FILLER_DEADLINE'])
 if smoke: gpu_smoke_admission.check()
 else:
  grant=flags/'grants'/('codex3-prbt4-r1-20261031.grant');snap=grant.read_bytes()
  reg=snap.decode().split()[0]
  if reg!='regions=mi210_0,184-191':raise RuntimeError('wrong GPU grant')
  parts=dict(x.split('=',1) for x in snap.decode().split())
  if set(parts)!={'regions','start','end'}:raise RuntimeError('malformed grant')
  start=datetime.datetime.fromisoformat(parts['start'].replace('Z','+00:00')).timestamp()
  grant_end=datetime.datetime.fromisoformat(parts['end'].replace('Z','+00:00')).timestamp()
  if not start<=time.time()<deadline or grant_end!=end or deadline!=end-90:raise RuntimeError('grant window mismatch')
  if os.environ.get('FILLER_CPUS')!='184-191':raise RuntimeError('wrong serving affinity')
 owner,identity=lock_witness.capture_gpu();lock_witness.verify_gpu(owner,identity)
 if kfd():raise RuntimeError('GPU is not quiet before server launch')
 out=D/(f'smoke-{time.time_ns()}' if smoke else f'attempts/{time.time_ns()}');out.mkdir(parents=True)
 slots=out/'slots';slots.mkdir()
 model=MODEL
 cmd=[str(STORE/'llama-server'),'-m',model,'--host','127.0.0.1','--port',str(PORT),'-np','2','-c','65536','-t','2' if smoke else '8','-ub','8192','--flash-attn','on','--jinja','-ctk','q8_0','-ctv','q8_0','--no-mmap','-ngl','all','--reasoning','off','--device','ROCm0','--slot-save-path',str(slots)]
 cmd+=['--chat-template-file',TEMPLATE,'--spec-type','draft-mtp','--spec-draft-n-max','8','--device-draft','ROCm0']
 env=dict(os.environ,LD_LIBRARY_PATH=str(STORE)+':/opt/rocm/lib',HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0')
 server=None;client=None;rc=1;vram=0;completed_rounds=0;cutoff_triggered=False;samples_file=(out/'gpu-samples.jsonl').open('a')
 def current_authority():
  pending=[os.getpid()]; seen=set(); total=0
  while pending:
   pid=pending.pop()
   if pid in seen:continue
   seen.add(pid)
   try:
    st=Path('/proc',str(pid),'status').read_text()
    total+=int(next(x.split()[1] for x in st.splitlines() if x.startswith('VmRSS:')))*1024
    for task in Path('/proc',str(pid),'task').iterdir():
     try:pending.extend(map(int,(task/'children').read_text().split()))
     except (FileNotFoundError,ProcessLookupError):pass
   except (FileNotFoundError,StopIteration,ProcessLookupError):pass
  if total>48*1024**3:raise RuntimeError('owned-tree sampled RSS exceeds 48 GiB')
  if stopped[0] or stopfile.exists() or time.time()>=deadline:return False
  try:lock_witness.verify_gpu(owner,identity)
  except Exception:return False
  if smoke:
   try:gpu_smoke_admission.check()
   except Exception:return False
  else:
   try:
    if grant.read_bytes()!=snap:return False
   except OSError:return False
  return True
 def end_child(p):
  if p is None:return
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
  if p.poll() is None:raise RuntimeError('owned child survived cleanup')
 try:
  with (out/'server.log').open('wb') as log:
   server=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
   (out/'server.pid').write_text(str(server.pid)+'\n')
   if not smoke:
    with open(os.environ['FILLER_PIDFILE'],'a') as pf:pf.write(str(server.pid)+'\n');pf.flush()
   start=time.monotonic();ready=False
   while current_authority() and time.monotonic()-start<240:
    if server.poll() is not None:raise RuntimeError('server exited before ready')
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=1) as r:ready=json.load(r).get('status')=='ok'
    except Exception:pass
    if ready and owned_port(server.pid,PORT) and kfd().get(server.pid,0)>0:break
    time.sleep(.5)
   else:
    if not current_authority():rc=75;return rc
    raise RuntimeError('server health, own-port or residency not established')
   with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/props',timeout=5) as r:props=json.load(r)
   if os.path.realpath(props.get('model_path',''))!=os.path.realpath(model):raise RuntimeError('served model mismatch')
   (out/'props.json').write_text(json.dumps(props,indent=2)+'\n')
   dso=[]
   for expected,digest in [(STORE/'libggml-hip.so.0.16.0','f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079'),(STORE/'libllama-server-impl.so','d9f143d7b056c0bc24a1822fb309ddd01c96df2b63b1b1bc61791e97f519e96f')]:
    row=mapped_identity(server.pid,expected,digest);dso.append(row);print(json.dumps({'event':'mapped_dso',**row}),flush=True)
   ma=json.loads((D/'MODEL-ATTESTATION.json').read_text());mst=Path(model).stat()
   if any(getattr(mst,k)!=v for k,v in ma['identity'].items()):raise RuntimeError('model differs from full-hash attestation')
   birth=int(Path('/proc',str(server.pid),'stat').read_text().rsplit(') ',1)[1].split()[19])
   log.flush();native_log=(out/'server.log').read_text(errors='replace')
   env_record={'schema':'epyc.prbt4.native_envelope.v1','run_id':'codex3-prbt4-r1-20261031','observed_unix':time.time(),'mode':mode,'source_catalog_sha256':os.environ['PRB_SOURCE_SHA'],'launcher_sha256':hashlib.sha256((D/'launch.sh').read_bytes()).hexdigest(),'predeclared_sha256':hashlib.sha256((D/'PREDECLARED.md').read_bytes()).hexdigest(),'sample_sha256':hashlib.sha256((D/'SAMPLE.json').read_bytes()).hexdigest(),'model_path':model,'model_sha256':ma['sha256'],'model_attestation':ma,'binary_path':str(STORE/'llama-server'),'binary_sha256':'2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b','template_sha256':'1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551','server_pid':server.pid,'server_uid':Path('/proc',str(server.pid)).stat().st_uid,'server_birth_ticks':birth,'server_argv':cmd,'props':props,'dso':dso,'gpu_resident':kfd().get(server.pid,0)>0,'gpu_vram_bytes':kfd().get(server.pid,0),'gpu_lock_owner':owner,'gpu_lock_identity':identity,'grant':None if smoke else snap.decode(),'end_epoch':end,'deadline_epoch':deadline,'mtp_log_evidence': 'adding speculative implementation \'draft-mtp\'' in native_log,'mtp_unavailable_evidence': 'speculative decoding not supported by this context' in native_log or 'failed to initialize speculative decoding context' in native_log,'server_log':str(out/'server.log'),'terminal_path':str(out/'RESULT.json')}
   ep=out/'ENVELOPE.json';et=out/'ENVELOPE.json.tmp'
   with et.open('x') as ef:ef.write(json.dumps(env_record,sort_keys=True,indent=2)+'\n');ef.flush();os.fsync(ef.fileno())
   os.replace(et,ep)
   env2=dict(env,PRB_ENDPOINT=f'http://127.0.0.1:{PORT}',PRB_QUALIFIED_EXECUTION='1',PRB_SMOKE='1' if smoke else '0',PRB_ENVELOPE=str(ep))
   t0=time.monotonic();zero_start=None
   while current_authority():
    data=out/f'round-{completed_rounds}' if smoke else D/'results'
    env2['PRB_OUTPUT']=str(data)
    client=subprocess.Popen([sys.executable,'-B',str(D/'campaign.py')],env=env2)
    while client.poll() is None and current_authority():
     if server.poll() is not None:raise RuntimeError('server exited during requests')
     live=kfd();v=live.get(server.pid,0)
     samples_file.write(json.dumps({'unix':time.time(),'server_pid':server.pid,'own_vram_bytes':v,'kfd':live},sort_keys=True)+'\n');samples_file.flush()
     if v>0:vram+=1;zero_start=None
     elif zero_start is None:zero_start=time.monotonic()
     elif time.monotonic()-zero_start>5:raise RuntimeError('GPU residency absent during requests')
     if any(p!=server.pid and m>0 for p,m in live.items()):raise RuntimeError('foreign GPU residency during request')
     if mode=='cutoff' and completed_rounds>0 and time.monotonic()-t0>20:cutoff_triggered=True;stopped[0]=True;break
     time.sleep(.25)
    if not current_authority():rc=75;break
    client_rc=client.wait()
    if client_rc==75:rc=75;break
    if client_rc!=0:raise RuntimeError('campaign exited nonzero: '+str(client_rc))
    completed_rounds+=1
    if mode!='cutoff':
     if vram<2:raise RuntimeError('less than two during-request residency samples')
     rc=0;break
   if stopped[0] or not current_authority():rc=75
 finally:
  cleanup_errors=[]
  try:samples_file.close()
  except Exception as exc:cleanup_errors.append('samples: '+repr(exc))
  for name,obj in (('client',client),('server',server)):
   try:end_child(obj)
   except Exception as exc:cleanup_errors.append(name+': '+repr(exc))
  registry=D/'score-cgroups'
  if registry.exists():
   for receipt in registry.iterdir():
    try:
     rec=json.loads(receipt.read_text());group=Path(rec['path'])
     if group.parent!=Path('/sys/fs/cgroup') or not group.name.startswith('codex3-prb-score-'):raise RuntimeError('invalid score cgroup receipt')
     if group.exists():
      st=group.stat()
      if st.st_uid!=os.getuid() or st.st_dev!=rec['dev'] or st.st_ino!=rec['ino']:raise RuntimeError('score cgroup identity mismatch')
      if (group/'cgroup.procs').read_text().strip():(group/'cgroup.kill').write_text('1')
      for _ in range(100):
       if 'populated 0' in (group/'cgroup.events').read_text():break
       time.sleep(.05)
      else:raise RuntimeError('score cgroup not drained')
      group.rmdir()
     receipt.unlink()
    except Exception as exc:cleanup_errors.append('cgroup '+receipt.name+': '+repr(exc))
  try:owned_drain.drain()
  except Exception as exc:cleanup_errors.append('descendants: '+repr(exc))
  if cleanup_errors:raise RuntimeError('cleanup failures: '+repr(cleanup_errors))
  summary={'mode':mode,'started':started_epoch,'ended':time.time(),'wall_s':time.monotonic()-started_mono,'rc':rc,'partial':rc==75,'gpu_samples':vram,'completed_rounds':completed_rounds,'server_pid':server.pid if server else None,'server_dead':server is None or server.poll() is not None,'client_pid':client.pid if client else None,'client_dead':client is None or client.poll() is not None,'cleanup_errors':cleanup_errors,'cutoff_triggered':cutoff_triggered}
  (out/'RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
  print(json.dumps(summary),flush=True)
 return rc
if __name__=='__main__':sys.exit(main())

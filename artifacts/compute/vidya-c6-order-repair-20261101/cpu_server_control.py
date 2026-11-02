#!/usr/bin/env python3
"""R11 CPU-only server/probe lifecycle control of the original ab_probe source."""
import hashlib,json,os,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
STORE=Path('/mnt/raid0/llm/kernels/builds/cpu-20261030-729599d69-c6')
MODEL=Path('/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf')
PORT=19077

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ident(pid):
 p=Path('/proc')/str(pid);s=(p/'stat').read_text().rsplit(') ',1)[1].split()
 return {'pid':pid,'birth':int(s[19]),'uid':p.stat().st_uid,'ticks':int(s[11])+int(s[12]),'rss_bytes':int((p/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')}
def stop(p,fd):
 if p.poll() is None:
  signal.pidfd_send_signal(fd,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:signal.pidfd_send_signal(fd,signal.SIGKILL);p.wait(timeout=5)
 return not Path('/proc',str(p.pid)).exists()
def main():
 if len(sys.argv)!=3:raise RuntimeError('usage cpu_server_control.py OUT STOP')
 out=Path(sys.argv[1]);stopfile=Path(sys.argv[2]);assert not out.exists() and not stopfile.exists()
 cpus=set(os.sched_getaffinity(0));assert len(cpus)==2 and cpus=={126,127} and os.environ.get('R11_CPUS')=='126,127'
 assert not any(os.environ.get(k,'') for k in ('HIP_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES'))
 import sys as _sys;_sys.path.insert(0,str(HERE))
 sums={line.split(None,1)[1].strip():line.split()[0] for line in (STORE/'SHA256SUMS').read_text().splitlines()};server=STORE/'bin/llama-server'
 assert sums['bin/llama-server']==sha(server) and json.loads((STORE/'BUILD-IDENTITY.json').read_text())['source_sha']=='729599d69871181d67af715a4c2f9162d5153a2e'
 with socket.socket() as sock:
  sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
  try:sock.bind(('127.0.0.1',PORT))
  except OSError:raise RuntimeError('private control port occupied')
 out.mkdir(parents=True);env={**os.environ,'LD_LIBRARY_PATH':str(STORE/'bin')+':/opt/rocm/lib','GGML_BACKEND_PATH':str(STORE/'bin'),'GGML_IQK':'1','OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'','ROCR_VISIBLE_DEVICES':'','CUDA_VISIBLE_DEVICES':''}
 argv=[str(server),'-m',str(MODEL),'--host','127.0.0.1','--port',str(PORT),'-np','1','-c','2048','-t','1','-ngl','0']
 pre={'schema':'c6.gpu27b_r11_control_pre.v1','store':str(STORE),'server_sha256':sha(server),'model':str(MODEL),'model_size':MODEL.stat().st_size,'model_mtime_ns':MODEL.stat().st_mtime_ns,'source':'729599d69871181d67af715a4c2f9162d5153a2e','probe_source_sha256':sha(HERE/'original/ab_probe.py'),'client_adapter_sha256':sha(HERE/'control_client.py'),'argv':argv,'cpus':sorted(cpus),'gpu_execution':False,'started_at':time.time()}
 (out/'PRE-RUN.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
 with (out/'server.stdout.log').open('wb') as sout,(out/'server.stderr.log').open('wb') as serr:
  s=subprocess.Popen(argv,stdout=sout,stderr=serr,env=env,start_new_session=True)
  sid=ident(s.pid);sfd=os.pidfd_open(s.pid);client=None;cfd=None;sent=False;active=None
  try:
   deadline=time.monotonic()+260
   while time.monotonic()<deadline:
    if s.poll() is not None:raise RuntimeError('server exited before /health')
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=.5) as resp:
      if resp.status==200:break
    except Exception:time.sleep(.05)
   else:raise RuntimeError('server health timeout')
   props=subprocess.run([sys.executable,'-B',str(HERE/'original/ab_probe.py'),'props','--port',str(PORT),'--commit','729599d','--model',str(MODEL)],capture_output=True,text=True,timeout=10)
   (out/'props.json').write_text(props.stdout);assert props.returncode==0 and json.loads(props.stdout)['ok'] is True
   with (out/'client.stdout.log').open('wb') as cout,(out/'client.stderr.log').open('wb') as cerr:
    client=subprocess.Popen([sys.executable,'-B',str(HERE/'control_client.py'),str(out),str(PORT)],stdout=cout,stderr=cerr,env=env);cid=ident(client.pid);cfd=os.pidfd_open(client.pid)
    while client.poll() is None and time.monotonic()<deadline:
     if stopfile.exists():
      marker=out/'REQUEST-ACTIVE.json'
      if not marker.exists():raise RuntimeError('STOP before active HTTP request')
      active=json.loads(marker.read_text());assert active['pid']==client.pid and active['status']=='ACTIVE'
      now=ident(s.pid);assert now['birth']==sid['birth'] and now['uid']==os.getuid() and now['ticks']>sid['ticks']
      sent=True;break
     time.sleep(.01)
    if time.monotonic()>=deadline:raise RuntimeError('R11 control deadline')
    if sent:
     assert stop(client,cfd) and stop(s,sfd)
    else:client.wait(timeout=5)
   if not sent:
    probe=json.loads((out/'probe.json').read_text());assert client.returncode==0 and probe['ok'] is True and len(probe['identity_text'])==2
  finally:
   if client is not None and cfd is not None:stop(client,cfd);os.close(cfd)
   dead=stop(s,sfd);os.close(sfd)
  assert dead
 result={'schema':'c6.gpu27b_r11_control_result.v1','status':'PARTIAL_STOP' if sent else 'NATIVE_COMPLETE','server_pid_birth':sid,'client_pid_birth':cid,'server_dead':dead,'client_dead':client is not None and not Path('/proc',str(client.pid)).exists(),'probe_sha256':sha(out/'probe.json') if (out/'probe.json').exists() else None,'props_sha256':sha(out/'props.json'),'active_at_stop':active,'gpu_execution':False,'server_stdout_sha256':sha(out/'server.stdout.log'),'server_stderr_sha256':sha(out/'server.stderr.log'),'client_stdout_sha256':sha(out/'client.stdout.log'),'client_stderr_sha256':sha(out/'client.stderr.log')}
 (out/'RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 return 75 if sent else 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('R11_SERVER_CONTROL_REFUSED:',repr(e),file=sys.stderr);sys.exit(2)

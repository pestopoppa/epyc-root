#!/usr/bin/env python3
"""One-shot own-child breakpoint qualification; never a layout or task witness."""
import hashlib,json,os,secrets,signal,subprocess,sys,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvu/observer-findslot-v1')
B=D/'fixture'; P=D/'pins.json'; G=D/'observe.gdb'
BIN='078cafd6e72d274f40d82c50012b0170f80d2f0d8e72f5574cca6f88e7de7d7d'
ROW='kvu-kpf131-findslot-observer-20261104'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(ok,msg):
 if not ok: raise ValueError(msg)
def interrupt(signum, frame): raise InterruptedError('termination signal')
def cleanup(proc,pidfile):
 if pidfile.exists():
  info=json.loads(pidfile.read_text()); pid=info['pid']
  try:
   fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError: fields=None
  if fields is not None:
   check(int(fields[1])==proc.pid==info['ppid'] and fields[19]==info['birth'],'inferior ownership changed; refusing signal')
   os.kill(pid,signal.SIGKILL)
 if proc.poll() is None: proc.kill()
 proc.communicate()
 if pidfile.exists():
  pid=json.loads(pidfile.read_text())['pid']
  check(not Path(f'/proc/{pid}').exists(),'inferior death unverified')
def main():
 signal.signal(signal.SIGTERM,interrupt); signal.signal(signal.SIGINT,interrupt)
 check(sha(B)==BIN,'fixture executable drift')
 check(sha(P)=='d4447b28bd561d77bba6f94b8c0e905e8af59edc53917f7acc7d93b834bf9ef8','pins drift')
 dry=os.environ.get('FILLER_DRYRUN_RESULT_PATH'); check(dry or os.environ.get('FILLER_ID')==ROW,'missing row grant')
 nonce=None
 if not dry:
  nonce=secrets.token_hex(24); (D/'out').mkdir(parents=True,exist_ok=True)
  (D/'out/RESULT.json').unlink(missing_ok=True)
  (D/'out/attempt.json').write_text(json.dumps({'row_id':ROW,'nonce':nonce}))
 env=dict(os.environ,KPF_PINS=str(P),LD_LIBRARY_PATH='/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin',DEBUGINFOD_URLS='')
 rows=[]
 for arm,answer in [('honest','RESULT PASS 2 3'),('skip_apply','RESULT DETECTED 0 1')]:
  check(not Path(os.environ.get('FILLER_STOPFILE',str(D/'STOP'))).exists(),'STOP')
  check(time.time()<int(os.environ.get('FILLER_DEADLINE',str(int(time.time()+120)))),'deadline')
  cap=D/(arm+'.json'); cap.unlink(missing_ok=True)
  env['KPF_CAPTURE']=str(cap)
  pidfile=D/(arm+'.pid'); pidfile.unlink(missing_ok=True); env['KPF_PID']=str(pidfile)
  proc=subprocess.Popen(['gdb','-q','-nx','-batch','-x',str(G),'--args',str(B),arm],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
  try:
   stdout,stderr=proc.communicate('g\nq\n',timeout=45)
  except (subprocess.TimeoutExpired,InterruptedError):
   cleanup(proc,pidfile)
   raise ValueError('debugger interrupted or timed out; captured children cleaned')
  (D/(arm+'.stdout')).write_text(stdout);(D/(arm+'.stderr')).write_text(stderr)
  check(proc.returncode==0 and cap.exists(),'debugger failed '+arm)
  data=json.loads(cap.read_text()); events=data['events']
  check(data['exit_code']==0 and len(events)==2 and answer in stdout,'missing observations or fixture result '+arm)
  check(all(x['ids']==[0] and x['exe_sha256']==BIN for x in events),'unexpected ubatch or executable')
  check(events[0]['mapped']==events[1]['mapped'],'mapping drift')
  rows.append({'arm':arm,'capture':data,'answer':answer})
 out=Path(dry) if dry else D/'out/RESULT.json'; out.parent.mkdir(parents=True,exist_ok=True)
 tmp=out.with_name(out.name+'.tmp'); tmp.write_text(json.dumps({'schema':'kpf131.findslot-observer.v1','status':'OBSERVER_FIXTURE_PASS','row_id':ROW,'attempt_nonce':nonce,'case_count':2,'answer':2,'records':rows,'smoke':bool(dry),'timestamp_ns':time.time_ns(),'scope':'model-free own-child entry observer; not physical layout, task binding, or historical control'},indent=2)+'\n'); os.replace(tmp,out)
 print('OBSERVER_FIXTURE_PASS')
if __name__=='__main__':
 try: main()
 except Exception as e: print('INVALID:',repr(e),file=sys.stderr);sys.exit(1)

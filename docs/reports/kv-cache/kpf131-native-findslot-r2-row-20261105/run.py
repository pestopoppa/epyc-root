import json,os,secrets,select,signal,subprocess,sys,time
from pathlib import Path
from validate import D,ROW,BIN,check,sha,seal,validate
from map_identity import verify_snapshot
B=D/'fixture'; PINS=json.loads((D/'pins.json').read_text())
STOPPED=False
BOOT=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def stopped(signum,frame):
 global STOPPED
 STOPPED=True
for s in (signal.SIGTERM,signal.SIGINT): signal.signal(s,stopped)
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+'.tmp'); tmp.write_text(json.dumps(v,indent=2)+'\n'); os.replace(tmp,p)
def birth(pid):
 return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
def guard():
 check(not STOPPED and not (D/'STOP').exists() and not Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists(),'STOP')
 check(time.monotonic()<LIMIT,'fixture wall deadline')
 if os.getenv('FILLER_DEADLINE'): check(time.time()<float(os.environ['FILLER_DEADLINE']),'grant deadline')
def line(proc):
 data=b''
 while not data.endswith(b'\n'):
  guard(); check(proc.poll() is None,'child exited before answer')
  if select.select([proc.stdout],[],[],0.2)[0]:
   c=os.read(proc.stdout.fileno(),1); check(bool(c),'child stdout EOF'); data+=c
   check(len(data)<512,'oversize child line')
 return data.decode().strip()
def snapshot(proc,ticks):
 guard(); check(proc.poll() is None and birth(proc.pid)==ticks,'child birth changed')
 with open(f'/proc/{proc.pid}/exe','rb') as f:
  st=os.fstat(f.fileno()); h=__import__('hashlib').sha256()
  while b:=f.read(1048576): h.update(b)
  end=os.fstat(f.fileno())
 check((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(end.st_dev,end.st_ino,end.st_size,end.st_mtime_ns,end.st_ctime_ns),'exe changed while hashing')
 target=B.stat(); check((st.st_dev,st.st_ino)==(target.st_dev,target.st_ino) and h.hexdigest()==BIN,'executable pin mismatch')
 maps=verify_snapshot(Path(f'/proc/{proc.pid}/maps').read_text().splitlines(),PINS)
 check(set(maps)==set(PINS) and len(maps)==5,'DSO set mismatch')
 check(proc.poll() is None and birth(proc.pid)==ticks,'child exited during snapshot')
 return {'pid':proc.pid,'birth_ticks':ticks,'boot_id':BOOT,'executable':{'device':st.st_dev,'inode':st.st_ino,'sha256':h.hexdigest()},'maps':{p:{'device_inode':list(maps[p]),'sha256':PINS[p]} for p in sorted(maps)}}
def cleanup(proc,fd):
 if proc.poll() is None:
  if fd is not None: signal.pidfd_send_signal(fd,signal.SIGTERM)
  else: proc.stdin.close()
  try: proc.wait(timeout=2)
  except subprocess.TimeoutExpired:
   check(fd is not None,'pidfd unavailable; child not confirmed dead')
   signal.pidfd_send_signal(fd,signal.SIGKILL); proc.wait(timeout=2)
 check(proc.returncode is not None,'child not reaped')
def case(arm,folder):
 guard(); rec={'arm':arm}; save(folder/(arm+'.json'),rec)
 env=dict(os.environ);env['LD_LIBRARY_PATH']='/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin';env.pop('LD_PRELOAD',None);env.pop('LD_AUDIT',None)
 fd=None; proc=None
 try:
  with open(folder/(arm+'.stderr'),'wb') as err:
   proc=subprocess.Popen([str(B),arm],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,env=env,bufsize=0)
   fd=os.pidfd_open(proc.pid,0)
   ticks=birth(proc.pid);rec.update(pid=proc.pid,birth_ticks=ticks,boot_id=BOOT,pidfd_captured=True);save(folder/(arm+'.json'),rec)
   check(line(proc)=='READY '+str(proc.pid),'missing READY')
   rec['before']=snapshot(proc,ticks);save(folder/(arm+'.json'),rec)
   proc.stdin.write(b'g\n');proc.stdin.flush()
   rec['answer']=line(proc);save(folder/(arm+'.json'),rec)
   check(rec['answer']==('RESULT PASS 2 3' if arm=='honest' else 'RESULT DETECTED 0 1'),'unexpected native answer')
   rec['after']=snapshot(proc,ticks);save(folder/(arm+'.json'),rec)
   check(rec['before']==rec['after'],'before/after identity changed')
   proc.stdin.write(b'q\n');proc.stdin.flush();proc.stdin.close()
   while proc.poll() is None:
    guard()
    try: proc.wait(timeout=0.2)
    except subprocess.TimeoutExpired: pass
   rec['returncode']=proc.returncode
   rec['extra_stdout']=proc.stdout.read().decode(errors='replace')
   save(folder/(arm+'.json'),rec)
   check(rec['returncode']==0 and rec['extra_stdout']=='','child exact exit/extra stdout mismatch')
 except BaseException as exc:
  rec['error']=repr(exc);raise
 finally:
  try:
   if proc is not None:
    cleanup(proc,fd);rec['returncode']=proc.returncode;rec['cleanup_confirmed']=True
  finally:
   if fd is not None: os.close(fd)
   save(folder/(arm+'.json'),rec)
 return rec
LIMIT=time.monotonic()+60
smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
nonce=secrets.token_hex(24)
folder=D/'out'/('smoke' if smoke else 'full')
if smoke: folder=folder/nonce
out=folder/'RESULT.json'
a={'row_id':ROW,'nonce':nonce,'smoke':smoke,'result_path':str(out),'seal_sha256':None}
r={'schema':'kpf131.native-findslot.v2','row_id':ROW,'status':'INVALID','case_count':0,'records':[],'attempt_nonce':nonce,'smoke':smoke,'seal_sha256':None,'fixture_binary_sha256':BIN,'fixture_source_sha256':sha(D/'fixture.cpp'),'build_manifest_sha256':sha(D/'build-manifest.json'),'first_placement_evidence':'The sealed fixture.cpp rejects any first find_slot selection other than 0,1 with exit 23. The first placement is inferred from the exact sealed fixture binary/source binding and recorded child rc=0; only the second placement is printed. The build manifest is retrospective, not an independent reproducible-build attestation.'}
try:
 check(os.getenv('FILLER_ID')==ROW,'wrong row attempt')
 if smoke:
  check(bool(os.getenv('FILLER_DRYRUN_RESULT_PATH')),'missing publisher native result path')
  requested=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
  check(requested.is_absolute(),'publisher native result path must be absolute')
  check(not requested.resolve().is_relative_to((D/'out/full').resolve()),'smoke/full path collision')
  check(not requested.exists(),'publisher native result path already exists')
 check(smoke or not folder.exists(),'full attempt already exists; no retries')
 folder.mkdir(parents=True,exist_ok=False)
 digest=seal();a['seal_sha256']=digest;r['seal_sha256']=digest
 save(folder/'attempt.json',a);save(out,r)
 m=json.loads((D/'build-manifest.json').read_text())
 check(m['binary_sha256']==BIN and sha(B)==BIN and m['source_sha256']==sha(D/'fixture.cpp') and m['source_commit']=='a1f0c8cf9bd7102415a72577474f307b8ba94db9','build binding mismatch')
 for arm in ('honest','skip_apply'):
  r['records'].append(case(arm,folder));r['case_count']=len(r['records']);save(out,r)
 guard();r['status']='FIXTURE_PASS';validate(r,a,smoke);guard();save(out,r)
 if smoke:
  guard();save(requested,r)
 guard()
 print('FIXTURE_PASS '+str(out),flush=True)
except BaseException as exc:
 r['status']='INVALID';r['error']=repr(exc)
 # Never overwrite a prior full attempt on an accidental retry.
 if (folder/'attempt.json').exists() and json.loads((folder/'attempt.json').read_text()).get('nonce')==nonce: save(out,r)
 print('INVALID '+repr(exc),file=sys.stderr);sys.exit(1)

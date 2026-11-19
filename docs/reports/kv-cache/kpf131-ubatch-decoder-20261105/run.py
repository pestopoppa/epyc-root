#!/usr/bin/python3
import ctypes,hashlib,json,os,pathlib,signal,struct,subprocess,sys,time,secrets
D=pathlib.Path(__file__).resolve().parent
ROW='kpf131-ubatch-decoder-20261105'
assert os.getenv('FILLER_ID')==ROW
smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
nonce=secrets.token_hex(16)
folder=D/'out'/('smoke' if smoke else 'full')/nonce
assert not folder.exists()
folder.mkdir(parents=True)
result={'row_id':ROW,'nonce':nonce,'status':'INVALID','records':[],'smoke':smoke,'cases_completed':0}
def save():
 p=folder/'RESULT.json'; t=p.with_suffix('.tmp'); t.write_text(json.dumps(result,indent=2)+'\n'); os.replace(t,p)
def stop(sig,frame): raise RuntimeError('signal/timeout '+str(sig))
for sig in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT): signal.signal(sig,stop)
limit=time.monotonic()+60
def guard():
 assert time.monotonic()<limit and not (D/'STOP').exists()
 assert not pathlib.Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists()
 if os.getenv('FILLER_DEADLINE'): assert time.time()<float(os.environ['FILLER_DEADLINE'])
remaining=60
if os.getenv('FILLER_DEADLINE'): remaining=min(remaining,max(0.001,float(os.environ['FILLER_DEADLINE'])-time.time()))
signal.setitimer(signal.ITIMER_REAL,remaining)
save(); guard()
pins=json.loads((D/'libs.json').read_text())
def sha(p):
 with open(p,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
for p,h in {**pins,**json.loads((D/'build-pins.json').read_text())}.items():
 guard()
 if sha(p)!=h: raise SystemExit('PIN DRIFT '+p)
SOURCE=pathlib.Path('/mnt/raid0/llm/tmp/kpf-p1-20261004/src-store-p1r-20261020')
image='/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin'
assert pins[image+'/libllama.so.0.0.10348']=='33bf73eaedfee5a52aa07312d0d12431133e23c54d411744e7bd51bccf375f64'
assert sys.byteorder=='little' and struct.calcsize('P')==8

# The subreaper adopts orphaned descendants, so every remaining child can be
# captured by birth time and pidfd before an individual signal is sent.
libc=ctypes.CDLL(None, use_errno=True)
if libc.prctl(36,1,0,0,0)!=0: raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
def birth(pid): return pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
def capture(pid):
 fd=os.pidfd_open(pid)
 try: born=birth(pid)
 except BaseException: os.close(fd); raise
 return fd,born
def cleanup(pid,fd,born):
 old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM,signal.SIGTERM,signal.SIGINT})
 seen=[]; pending={pid:(fd,born)}; until=time.monotonic()+5
 try:
  def add(p,f,b):
   try:
    if birth(p)!=b: raise RuntimeError('PID birth changed')
    signal.pidfd_send_signal(f,signal.SIGKILL)
   except (ProcessLookupError,FileNotFoundError): pass
   seen.append({'pid':p,'birth_ticks':b})
  add(pid,fd,born)
  while True:
   children=pathlib.Path(f'/proc/{os.getpid()}/task/{os.getpid()}/children').read_text().split()
   for child in map(int,children):
    if child in pending: continue
    try: childfd,childborn=capture(child)
    except (ProcessLookupError,FileNotFoundError): continue
    pending[child]=(childfd,childborn); add(child,childfd,childborn)
   for child,(childfd,childborn) in list(pending.items()):
    try: reaped,_=os.waitpid(child,os.WNOHANG)
    except ChildProcessError: reaped=child
    if reaped:
     os.close(childfd); del pending[child]
   if not pending and not pathlib.Path(f'/proc/{os.getpid()}/task/{os.getpid()}/children').read_text().split(): return seen
   if time.monotonic()>=until: raise RuntimeError('cleanup deadline; survivors '+repr(sorted(pending)))
   time.sleep(.02)
 finally:
  for childfd,_ in pending.values(): os.close(childfd)
  signal.pthread_sigmask(signal.SIG_SETMASK,old)
publisher=folder/'publisher'
cmd=['/usr/bin/x86_64-linux-gnu-g++-15','-std=c++17','-O2','-I'+str(SOURCE/'src'),'-I'+str(SOURCE/'include'),'-I'+str(SOURCE/'ggml/include'),str(D/'publisher.cpp'),'-L'+image,'-Wl,-rpath,'+image,'-lllama','-lggml','-lggml-base','-o',str(publisher)]
compiler=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
cfd,cborn=capture(compiler.pid)
try:
 out,_=compiler.communicate(timeout=max(.01,limit-time.monotonic())); (folder/'build.log').write_bytes(out); assert compiler.returncode==0
finally:
 compiler_children=cleanup(compiler.pid,cfd,cborn)
guard(); publisher_hash=sha(publisher); result.update(publisher_sha256=publisher_hash,compiler_pid=compiler.pid,compiler_birth_ticks=cborn,compiler_cleanup_confirmed=True,compiler_captured=compiler_children,build_argv=cmd); save()
def trial(mode):
 guard()
 rec={'mode':mode,'cleanup_confirmed':False}; result['records'].append(rec); save()
 p=subprocess.Popen([str(publisher),mode],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':image,'LC_ALL':'C'})
 pidfd,born=capture(p.pid); rec.update(pid=p.pid,birth_ticks=born,pidfd_acquired=True); save()
 try:
  fields=p.stdout.readline().split(); assert len(fields)==3 and fields[0]=='READY' and int(fields[1])==p.pid
  _,st=os.waitpid(p.pid,os.WUNTRACED); assert os.WIFSTOPPED(st) and os.WSTOPSIG(st)==signal.SIGSTOP
  born=birth(p.pid); rec.update(pid=p.pid,birth_ticks=born); save(); assert pathlib.Path(f'/proc/{p.pid}/status').read_text().split('PPid:')[1].split()[0]==str(os.getpid())
  base=int(fields[2]); assert base>0
  maps=pathlib.Path(f'/proc/{p.pid}/maps').read_text().splitlines(); ranges=[]; files=set()
  for line in maps:
   f=line.split(None,5); lo,hi=(int(x,16) for x in f[0].split('-'))
   if 'r' in f[1]: ranges.append((lo,hi))
   if 'x' in f[1] and len(f)==6 and f[5].startswith('/'):
    assert not f[5].endswith(' (deleted)'); files.add(str(pathlib.Path(f[5]).resolve()))
  assert files==set(pins)|{str(publisher)} and os.readlink(f'/proc/{p.pid}/exe')==str(publisher) and sha(publisher)==publisher_hash and birth(p.pid)==born
  assert all(sha(f)==pins[f] for f in files if f!=str(publisher)); rec['mapped_executable_files']={f:(publisher_hash if f==str(publisher) else pins[f]) for f in sorted(files)}; save()
  mem=os.open(f'/proc/{p.pid}/mem',os.O_RDONLY)
  def read(addr,n):
   assert addr>0 and 0<n<=4096 and any(lo<=addr and addr+n<=hi for lo,hi in ranges)
   data=os.pread(mem,n,addr); assert len(data)==n; return data
  try:
   header=read(base,0x40)
   n=struct.unpack_from('<I',header,4)[0]
   posp,countp,ownerp=struct.unpack_from('<QQQ',header,0x28)
   assert n==4
   pos=struct.unpack('<4i',read(posp,4*n))
   counts=struct.unpack('<4i',read(countp,4*n))
   assert all(1<=count<=2 for count in counts)
   ptrs=struct.unpack('<4Q',read(ownerp,8*n))
   owners=[list(struct.unpack('<'+'i'*count,read(ptr,4*count))) for ptr,count in zip(ptrs,counts)]
  finally: os.close(mem)
  assert birth(p.pid)==born
  expected_pos=[10,91 if mode=='pos' else 11,12,13]
  expected_owners=[[1,2],[1],[2],[1,7 if mode=='owner' else 2]]
  assert list(pos)==expected_pos and owners==expected_owners
  rec.update(positions=list(pos),owners=owners); guard()
 finally:
  try:
   captured=cleanup(p.pid,pidfd,born)
   rec.update(cleanup_confirmed=True,termination='SIGKILL',captured=captured)
  finally: save()
try:
 for mode in ('honest','pos','owner'):
  trial(mode); result['cases_completed']+=1; result['records'][-1]['cases_completed']=result['cases_completed']; save()
 results=result['records']; assert all(x['cleanup_confirmed'] for x in results)
 assert results[0]['positions']!=results[1]['positions'] and results[0]['owners']==results[1]['owners']
 assert results[0]['positions']==results[2]['positions'] and results[0]['owners']!=results[2]['owners']
 guard(); result['status']='FIXTURE_PASS'; save()
 if not smoke:
  target=D/'out/full/RESULT.json'; assert not target.exists(); target.write_text(json.dumps(result,indent=2)+'\n')
 if smoke:
  target=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']); assert target.is_absolute() and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(result,indent=2)+'\n')
 print('FIXTURE_PASS',flush=True)
except BaseException as exc:
 result['status']='INVALID'; result['error']=repr(exc); save(); raise

#!/usr/bin/env python3
"""Private build supervisor: owned pidfds, bounded stop/drain, resumable rc75."""
import ctypes,hashlib,os,pathlib,select,shutil,signal,subprocess,sys,time
import pidfd_custody_v2 as custody
import pidfd_subreaper_v3 as subreaper
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(36,1,0,0,0):raise OSError(ctypes.get_errno(),'subreaper')
src,build,packet,raw_deadline,mode=sys.argv[1:];deadline=float(raw_deadline);packet=pathlib.Path(packet);floor=150*2**30
if mode not in ('full','smoke','cutoff'):raise RuntimeError('invalid mode')
stop_flag=packet/'STOP'; interrupted=None

def on_signal(sig,_frame):
 global interrupted
 if interrupted is None:interrupted=signal.Signals(sig).name
signal.signal(signal.SIGTERM,on_signal);signal.signal(signal.SIGINT,on_signal)

def partial(reason):
 path=packet/'BUILD-PARTIAL';tmp=packet/'BUILD-PARTIAL.tmp'
 with tmp.open('w') as f:f.write(reason+'\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path);fd=os.open(packet,os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def reason_now():
 if interrupted:return 'signal '+interrupted
 if stop_flag.exists():return 'STOP'
 if time.time()>=deadline-30:return 'deadline'
 return None

def dead(fd):
 poll=select.poll();poll.register(fd,select.POLLIN);return bool(poll.poll(0))

def drain(leader):
 """TERM then KILL after three seconds, only captured direct/adopted children."""
 owned={};term=0;kill=0
 while True:
  entries=subreaper.children()
  for pid in entries:
   if pid not in owned:
    try:fd,identity=custody.open_child(pid)
    except ProcessLookupError:continue
    owned[pid]={'fd':fd,'birth':identity['birth'],'term_at':None,'kill_sent':False}
    print(f'CAPTURED_CHILD pid={pid} birth={identity["birth"]}',flush=True)
  for pid,x in list(owned.items()):
   fd=x['fd']
   if pid==leader.pid:
    leader.poll()
    if leader.returncode is not None:
     os.close(fd);del owned[pid];continue
   elif dead(fd):
    try:subreaper.reap(fd)
    except RuntimeError:
     if pathlib.Path('/proc',str(pid)).exists():raise
    os.close(fd);del owned[pid];continue
   now=time.monotonic()
   if x['term_at'] is None:
    try:custody.send(fd,signal.SIGTERM);term+=1
    except ProcessLookupError:pass
    x['term_at']=now
   elif not x['kill_sent'] and now-x['term_at']>=3:
    try:custody.send(fd,signal.SIGKILL);kill+=1
    except ProcessLookupError:pass
    x['kill_sent']=True
  if not owned and not subreaper.children():
   if leader.poll() is None:raise RuntimeError('leader vanished without wait status')
   print(f'DRAIN_COMPLETE leader={leader.pid} leader_rc={leader.returncode} term={term} kill={kill} children=0',flush=True)
   return
  time.sleep(.05)

def stop_or_raise(reason,leader,compiler_seen):
 drain(leader);partial(reason)
 print(f'GUARD_CUTOFF reason={reason} compiler_seen={compiler_seen} leader_reaped={leader.poll() is not None} children_drained=true',flush=True)
 if mode=='cutoff' and (reason!='deadline' or not compiler_seen):sys.exit(78)
 sys.exit(75)

def size(root):
 total=0
 for d,_,files in os.walk(root):
  for f in files:
   try:total+=os.lstat(os.path.join(d,f)).st_size
   except FileNotFoundError:pass
 return total

def compiler_alive(leader):
 pending=[leader.pid];seen=set()
 while pending:
  pid=pending.pop()
  if pid in seen:continue
  seen.add(pid)
  try:
   cmd=pathlib.Path('/proc',str(pid),'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if cmd and os.path.basename(cmd.split()[0]) in ('cc1plus','clang++','c++','g++'):
    return (pid,custody.stat(pid)['birth'],cmd)
   for t in pathlib.Path('/proc',str(pid),'task').iterdir():
    try:pending.extend(map(int,(t/'children').read_text().split()))
    except FileNotFoundError:pass
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return None

if os.path.realpath(src)!='/mnt/micron/codex3-lanes/kpf-e332-src' or os.path.realpath(build)!='/mnt/micron/codex3-lanes/kpf-e332-build':raise RuntimeError('wrong paths')
if (packet/'BUILD-SUCCESS').exists():raise RuntimeError('stale success marker')
initial=reason_now()
if initial:partial(initial);sys.exit(75)
if shutil.disk_usage('/mnt/micron').free<floor+20*2**30 or shutil.disk_usage('/mnt/raid0/llm').free<floor+2**27:partial('disk reserve');sys.exit(75)
raid=size(packet);objects=['src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o','tools/server/CMakeFiles/server-context.dir/server-context.cpp.o']
# Only remove the two own, unlinked objects in bounded smoke modes. No detached subprocess.
if mode in ('smoke','cutoff'):
 for obj in objects:
  try:pathlib.Path(build,obj).unlink()
  except FileNotFoundError:pass
cmd=['cmake','--build',build,'--target','llama-server','-j',str(min(8,len(os.sched_getaffinity(0))))] if mode=='full' else ['ninja','-C',build,'-j2',*objects]
p=subprocess.Popen(cmd,start_new_session=True)
print(f'GUARD_ID pid={os.getpid()} birth={custody.stat(os.getpid())["birth"]}',flush=True)
print(f'GUARD_STARTED mode={mode} leader={p.pid} deadline={deadline}',flush=True)
compiler_seen=False
while p.poll() is None:
 found=compiler_alive(p)
 if found and not compiler_seen:
  print(f'COMPILER_OBSERVED pid={found[0]} birth={found[1]} args={found[2][:300]}',flush=True);compiler_seen=True
 reason=reason_now()
 if not reason and (size(build)>=19*2**30 or size(packet)-raid>=112*2**20):reason='output cap'
 if not reason and (shutil.disk_usage('/mnt/micron').free<floor+2**30 or shutil.disk_usage('/mnt/raid0/llm').free<floor+16*2**20):reason='disk floor'
 if reason:stop_or_raise(reason,p,compiler_seen)
 time.sleep(.1)
rc=p.returncode;drain(p)
reason=reason_now()
if reason:partial(reason);sys.exit(75)
if rc:sys.exit(rc)
if mode in ('smoke','cutoff'):
 if mode=='cutoff':raise RuntimeError('cutoff test unexpectedly completed')
 obj=pathlib.Path(build,objects[0]);other=pathlib.Path(build,objects[1]);z=obj.read_bytes();w=other.read_bytes()
 if not z or not w:raise RuntimeError('empty object')
 with open(packet/'SMOKE-OBJECTS.sha256','w') as fh:
  for ob in (obj,other):fh.write(hashlib.sha256(ob.read_bytes()).hexdigest()+'  '+str(ob)+'\n')
  fh.flush();os.fsync(fh.fileno())
 print(f'OBJECT_SMOKE_PASS compiler_seen={compiler_seen} leader_reaped=true children_drained=true',flush=True);sys.exit(0)
bin=pathlib.Path(build,'bin/llama-server');env=os.environ.copy();env['LD_LIBRARY_PATH']=str(bin.parent)+':/opt/rocm/lib'
def check_bounded(cmd,output):
 reason=reason_now()
 if reason:partial(reason);sys.exit(75)
 with open(output,'w') as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  print(f'VALIDATION_STARTED pid={proc.pid} command={cmd[0]}',flush=True)
  while proc.poll() is None:
   reason=reason_now()
   if reason:stop_or_raise(reason,proc,compiler_seen)
   time.sleep(.1)
  rc=proc.returncode;drain(proc)
  reason=reason_now()
  if reason:partial(reason);sys.exit(75)
  if rc:raise RuntimeError('validation failed: '+str(cmd))
check_bounded([str(bin),'--help'],str(packet/'BUILD-HELP.log'))
check_bounded(['/bin/bash',str(packet/'verify_ggml_linkage.sh'),str(bin),str(bin.parent)],str(packet/'BUILD-LINKAGE.log'))
if not (packet/'BUILD-HELP.log').read_bytes():raise RuntimeError('help output empty')
if 'PASS: all linked ggml libraries resolve inside '+str(bin.parent) not in (packet/'BUILD-LINKAGE.log').read_text():raise RuntimeError('linkage pass evidence missing')
impl=bin.parent/'libllama-server-impl.so';common=bin.parent/'libllama-common.so';layout=bin.parent/'libllama.so'
with open(packet/'BUILD-DIGESTS.txt','w') as f:
 for ob in (bin,impl,common,layout,bin.parent/'libggml-cpu.so'):f.write(hashlib.sha256(ob.read_bytes()).hexdigest()+'  '+str(ob)+'\n')
 f.flush();os.fsync(f.fileno())
reason=reason_now()
if reason:partial(reason);sys.exit(75)
with open(packet/'BUILD-SUCCESS','w') as f:f.write(str(bin)+'\n');f.flush();os.fsync(f.fileno())

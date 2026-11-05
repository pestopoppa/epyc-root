#!/usr/bin/env python3
import ctypes, os, signal, subprocess, sys, time, re, select
from pathlib import Path
libc=ctypes.CDLL(None,use_errno=True)
assert libc.prctl(36,1,0,0,0)==0
v=ctypes.c_int(); assert libc.prctl(37,ctypes.byref(v),0,0,0)==0 and v.value==1
stop=False
def handler(*_):
 global stop
 stop=True
for sig in (signal.SIGTERM,signal.SIGINT): signal.signal(sig,handler)
def children(pid):
 try:
  result=set()
  for p in Path(f'/proc/{pid}/task').iterdir():
   try: result.update(map(int,(p/'children').read_text().split()))
   except FileNotFoundError: pass
  return result
 except FileNotFoundError: return set()
def birth(pid):
 try: return int(Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19])
 except (FileNotFoundError,ProcessLookupError): return None
owned={}
def capture(pid, parent=None):
 if pid in owned: return
 if parent is not None and pid not in children(parent): return
 before=birth(pid)
 if before is None: return
 try: fd=os.pidfd_open(pid)
 except ProcessLookupError: return
 try:
  info=Path(f'/proc/self/fdinfo/{fd}').read_text()
  after=birth(pid)
  # A pidfd readable with POLLIN refers to an exited process. Short-lived
  # compiler children routinely exit between enumeration and capture.
  poll=select.poll(); poll.register(fd,select.POLLIN)
  exited=bool(poll.poll(0))
  if exited: return
  if after != before or not re.search(r'^Pid:\s*'+str(pid)+r'\s*$',info,re.M):
   raise RuntimeError('live identity capture failed')
  if parent is not None and pid not in children(parent):
   # Reparenting is not ownership proof; the subreaper sweep captures adopted
   # children independently. If it is still live, fail closed.
   poll=select.poll(); poll.register(fd,select.POLLIN)
   if poll.poll(0): return
   raise RuntimeError('live parent identity changed during capture')
  owned[pid]=(after,fd); fd=None
 finally:
  if fd is not None: os.close(fd)
def scan(root):
 todo=[root]; seen=set()
 while todo:
  p=todo.pop()
  if p in seen: continue
  seen.add(p)
  for c in children(p):
   capture(c,p)
   if c in owned: todo.append(c)
def drain():
 end=time.monotonic()+8; sent={}
 while time.monotonic()<end:
  for p in children(os.getpid()):
   capture(p,os.getpid())
   if p in owned: scan(p)
  for p,(b,fd) in list(owned.items()):
   if birth(p)!=b: continue
   if p in children(os.getpid()):
    try:
     if os.waitpid(p,os.WNOHANG)[0]: continue
    except ChildProcessError: pass
   now=time.monotonic(); first=sent.get(p)
   if first is None or (first and now-first>2):
    sig=signal.SIGTERM if first is None else signal.SIGKILL
    try: signal.pidfd_send_signal(fd,sig)
    except ProcessLookupError: pass
    sent[p]=now if first is None else 0
  if not children(os.getpid()) and all(birth(p)!=b for p,(b,_) in owned.items()): return
  time.sleep(.02)
 raise RuntimeError('cleanup incomplete')
stopfile,deadline,*cmd=sys.argv[1:]; p=None; failed=False
try:
 if stop or Path(stopfile).exists() or time.time()>=int(deadline): raise RuntimeError('STOP/deadline')
 p=subprocess.Popen(cmd)
 try:
  capture(p.pid)
  if p.pid not in owned: raise RuntimeError('direct child capture failed')
 except BaseException:
  # Direct child remains unreaped; its PID cannot have been recycled.
  p.kill(); p.wait(timeout=5)
  raise
 while True:
  scan(p.pid)
  rc=p.poll()
  if rc is not None: break
  if stop or Path(stopfile).exists() or time.time()>=int(deadline): raise RuntimeError('STOP/deadline')
  time.sleep(.1)
 if rc: raise RuntimeError(f'command exit {rc}')
except BaseException as e:
 failed=True; print(str(e),file=sys.stderr)
finally:
 try: drain()
 except BaseException as e: failed=True; print(str(e),file=sys.stderr)
 for _,fd in owned.values(): os.close(fd)
sys.exit(75 if failed else 0)

"""Experimental exclusive subreaper, signals and reaps through captured pidfds.

Precondition: no existing children and no unrelated subprocess creation until
full drain. On failure caller must remain alive and retry; not a launcher.
"""
import ctypes,os,signal,time
from pathlib import Path
import pidfd_custody_v2 as custody

def children():
 out=set()
 for task in Path('/proc/self/task').iterdir():
  try:out.update(int(p) for p in (task/'children').read_text().split())
  except FileNotFoundError:continue
 return sorted(out)

def enable():
 if children():raise RuntimeError('preexisting children')
 libc=ctypes.CDLL(None,use_errno=True)
 if libc.prctl(36,1,0,0,0):raise OSError(ctypes.get_errno(),'subreaper')

def reap(fd):
 try:return os.waitid(os.P_PIDFD,fd,os.WEXITED|os.WNOHANG) is not None
 except ChildProcessError:raise RuntimeError('pidfd no longer owned child')

def drain(timeout=10):
 until=time.monotonic()+timeout
 while True:
  entries=children()
  if not entries:return
  if time.monotonic()>until:raise RuntimeError('descendants remain; stay alive and retry')
  for pid in entries:
   try:fd,_=custody.open_child(pid)
   except ProcessLookupError:continue
   try:
    if reap(fd):continue
    try:custody.send(fd,signal.SIGTERM)
    except ProcessLookupError:pass
    grace=time.monotonic()+.3
    while time.monotonic()<grace:
     if reap(fd):break
     time.sleep(.02)
    else:
     try:custody.send(fd,signal.SIGKILL)
     except ProcessLookupError:pass
     reap(fd)
   finally:os.close(fd)
  time.sleep(.05)

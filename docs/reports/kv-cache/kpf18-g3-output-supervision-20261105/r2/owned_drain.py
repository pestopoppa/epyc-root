#!/usr/bin/env python3
"""Subreaper cleanup: never return while an adopted child is still live."""
import ctypes,os,signal,time
from pathlib import Path
def enable():
 if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0): raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
def children():
 found=set()
 for task in (Path('/proc')/str(os.getpid())/'task').iterdir():
  try: found.update(map(int,(task/'children').read_text().split()))
  except FileNotFoundError: continue
 return sorted(found)
def drain():
 """Only call when this subreaper had no preexisting children; remain alive if stuck."""
 announced=set()
 while True:
  pids=children()
  if not pids: return
  for pid in pids:
   try: fd=os.pidfd_open(pid)
   except ProcessLookupError: continue
   try:
    try:
     if (Path('/proc')/str(pid)).stat().st_uid!=os.getuid(): raise RuntimeError('foreign adopted child')
     signal.pidfd_send_signal(fd,signal.SIGTERM)
    except ProcessLookupError:
     try: os.waitpid(pid,os.WNOHANG)
     except ChildProcessError: pass
     continue
    end=time.monotonic()+.3
    while time.monotonic()<end:
     try:
      if os.waitpid(pid,os.WNOHANG)[0]: break
     except ChildProcessError: break
     time.sleep(.02)
    else:
     try: signal.pidfd_send_signal(fd,signal.SIGKILL)
     except ProcessLookupError: pass
     if pid not in announced: print('waiting for owned child to drain:',pid,flush=True);announced.add(pid)
    try:os.waitpid(pid,os.WNOHANG)
    except ChildProcessError:pass
   finally: os.close(fd)
  time.sleep(.05)

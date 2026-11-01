"""Captured-child pidfd signaling only; no numeric PID or PGID signaling.

This is a building block, not a complete descendant/subreaper drain.
"""
import os,signal
from pathlib import Path

def stat(pid):
 raw=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
 return {'state':raw[0],'ppid':int(raw[1]),'birth':int(raw[19])}

def open_child(pid):
 fd=os.pidfd_open(pid,0)  # acquire stable identity before inspecting /proc
 try:
  info=(Path('/proc/self/fdinfo')/str(fd)).read_text().splitlines()
  target=int(next(x.split(':',1)[1] for x in info if x.startswith('Pid:')))
  if target!=pid:raise RuntimeError('pidfd target changed or exited')
  identity=stat(pid)
  if identity['ppid']!=os.getpid():raise RuntimeError('not a direct child')
  uid=(Path('/proc')/str(pid)).stat().st_uid
  if uid!=os.getuid():raise RuntimeError('foreign child uid')
  # Reconfirm pidfd target and /proc start time after ownership inspection.
  info2=(Path('/proc/self/fdinfo')/str(fd)).read_text().splitlines()
  if int(next(x.split(':',1)[1] for x in info2 if x.startswith('Pid:')))!=pid or any(stat(pid)[k]!=identity[k] for k in ('ppid','birth')):
   raise RuntimeError('child identity changed during capture')
  return fd,identity
 except BaseException:
  os.close(fd);raise

def send(fd,sig):
 if sig not in (signal.SIGTERM,signal.SIGKILL):raise ValueError('unsupported signal')
 signal.pidfd_send_signal(fd,sig)

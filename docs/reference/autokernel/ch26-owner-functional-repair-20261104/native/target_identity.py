"""Pidfd-bound target identity facts; not proof of perf FD attachment."""
import os,select
from owner_marker import identity
class Target:
 def __init__(self,pid):
  if type(pid) is not int or pid<=0:raise ValueError('positive target pid required')
  self.pid=pid;self.fd=None;self.closed=False
  before=identity(pid);fd=os.pidfd_open(pid,0)
  try:
   if identity(pid)!=before or self._dead(fd):raise ValueError('target changed or exited during attach')
  except BaseException:os.close(fd);raise
  self.fd=fd;self.start_ticks,self.boot_id=before
 @staticmethod
 def _dead(fd):
  p=select.poll();p.register(fd,select.POLLIN|select.POLLHUP|select.POLLERR);return bool(p.poll(0))
 def snapshot(self):
  if self.closed or self.fd is None or self._dead(self.fd) or identity(self.pid)!=(self.start_ticks,self.boot_id):raise ValueError('target unavailable or identity changed')
  return {'pid':self.pid,'start_ticks':self.start_ticks,'boot_id':self.boot_id}
 def close(self):
  if not self.closed:
   self.closed=True;os.close(self.fd);self.fd=None

"""Owned Linux inode write lease; fail closed, no ledger/fold policy changes.

Primary contract: https://man7.org/linux/man-pages/man2/F_SETLEASE.2const.html
A peer conflicting open/truncate requests a break. Existing peer descriptors or
unsupported filesystems refuse acquisition. No name-pattern process operations.
"""
import fcntl,os,signal,stat,threading

class LeaseBroken(RuntimeError):pass

class OwnedWriteLease:
 def __init__(self,path):self.path=os.fspath(path);self.fd=None;self.broken=False;self.appending=False
 def __enter__(self):
  if threading.current_thread() is not threading.main_thread():raise RuntimeError('lease requires main-thread signal ownership')
  for key in ('F_SETLEASE','F_GETLEASE','F_SETOWN'):
   if not hasattr(fcntl,key):raise RuntimeError('Linux leases unsupported; refuse mutation')
  self.previous=signal.getsignal(signal.SIGIO)
  if self.previous not in (signal.SIG_DFL,signal.SIG_IGN):raise RuntimeError('SIGIO already owned; refuse lease')
  self.fd=os.open(self.path,os.O_RDWR|os.O_APPEND|os.O_CLOEXEC|os.O_NOFOLLOW)
  self.inode=os.fstat(self.fd)
  if not stat.S_ISREG(self.inode.st_mode):os.close(self.fd);self.fd=None;raise RuntimeError('lease target is not regular file')
  def broken(signum,frame):
   self.broken=True
   # Complete an in-progress native append, then abort before another append.
   if not self.appending:raise LeaseBroken('peer requested inode lease break')
  signal.signal(signal.SIGIO,broken)
  try:
   fcntl.fcntl(self.fd,fcntl.F_SETOWN,os.getpid())
   fcntl.fcntl(self.fd,fcntl.F_SETLEASE,fcntl.F_WRLCK)
   self.check();return self
  except BaseException:
   self.__exit__(None,None,None);raise
 def check(self):
  now=os.stat(self.path,follow_symlinks=False)
  if self.broken or fcntl.fcntl(self.fd,fcntl.F_GETLEASE)!=fcntl.F_WRLCK:raise LeaseBroken('write lease lost/requested; refuse additional append')
  if (now.st_dev,now.st_ino)!=(self.inode.st_dev,self.inode.st_ino):raise LeaseBroken('ledger pathname inode changed')
 def read_bytes(self):
  self.check();size=os.fstat(self.fd).st_size;chunks=[];offset=0
  while offset<size:
   chunk=os.pread(self.fd,min(1048576,size-offset),offset)
   if not chunk:raise RuntimeError("short lease read")
   chunks.append(chunk);offset+=len(chunk)
  self.check();return b"".join(chunks)
 def append(self,ledger,frame):
  self.check();self.appending=True
  try:return ledger.append(frame)
  finally:
   self.appending=False;self.check()
 def __exit__(self,*args):
  if self.fd is not None:
   try:fcntl.fcntl(self.fd,fcntl.F_SETLEASE,fcntl.F_UNLCK)
   finally:os.close(self.fd);self.fd=None;signal.signal(signal.SIGIO,self.previous)

from ledger import Ledger,_link_hash

class _DescriptorPath:
 """Path facade for native read/cache checks; never opens the leased inode."""
 def __init__(self,lease):self.lease=lease;self.parent=os.path.dirname(lease.path)
 def exists(self):return True
 def stat(self):self.lease.check();return os.fstat(self.lease.fd)
 def read_bytes(self):return self.lease.read_bytes()
 def __str__(self):return self.lease.path

class LeasedLedger(Ledger):
 """Native Ledger mechanics over the owned descriptor; fail instead of repair."""
 def __init__(self,lease):
  # Native initialization opens no file; replace path before inherited operations.
  super().__init__(lease.path);self.lease=lease;self.path=_DescriptorPath(lease)
 def _write_record(self,record,*,sync_dir):
  if sync_dir:raise RuntimeError('existing inode required; no create under lease')
  self.lease.check();payload=record.to_line()+b'\n';offset=0
  while offset<len(payload):
   count=os.write(self.lease.fd,payload[offset:])
   if count<=0:raise RuntimeError('short lease write')
   offset+=count
  os.fsync(self.lease.fd)
  self._cached_head=(record.seq,_link_hash(record.prev_hash,record.frame_hash,record.seq))
  self._cached_size=os.fstat(self.lease.fd).st_size
 def _truncate_to(self,records):raise RuntimeError('no torn-tail repair in reviewed replay')

"""Initialize only missing canonical lock metadata, then lock and re-fence it."""
import os,fcntl,stat
from pathlib import Path
def acquire(parent,shard):
 if not isinstance(shard,int) or not 0<=shard<=150:raise ValueError('shard')
 dfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 rootfd=None;fd=None
 try:
  name=f'shard-{shard:02d}'
  try:os.mkdir(name,0o700,dir_fd=dfd);os.fsync(dfd)
  except FileExistsError:pass
  os.fsync(dfd)
  rootfd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=dfd);st=os.fstat(rootfd)
  if st.st_uid!=os.getuid() or st.st_mode&0o077:raise RuntimeError('unsafe canonical shard directory')
  try:
   fd=os.open('campaign.serial.lock',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=rootfd);os.fsync(fd);os.fsync(rootfd)
  except FileExistsError:fd=os.open('campaign.serial.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=rootfd)
  os.fsync(fd);os.fsync(rootfd)
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.getuid():raise RuntimeError('unsafe canonical lock')
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);current=os.stat('campaign.serial.lock',dir_fd=rootfd,follow_symlinks=False)
  if (st.st_dev,st.st_ino,st.st_nlink)!=(current.st_dev,current.st_ino,current.st_nlink):raise RuntimeError('canonical lock replaced')
  parent_now=os.stat(name,dir_fd=dfd,follow_symlinks=False);root_now=os.fstat(rootfd)
  if (parent_now.st_dev,parent_now.st_ino)!=(root_now.st_dev,root_now.st_ino):raise RuntimeError('canonical shard directory replaced')
  ret=fd;fd=None;return ret
 finally:
  if fd is not None:os.close(fd)
  if rootfd is not None:os.close(rootfd)
  os.close(dfd)

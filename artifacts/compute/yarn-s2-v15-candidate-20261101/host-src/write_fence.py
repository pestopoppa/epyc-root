#!/usr/bin/python3
"""Exec with Landlock write access only to explicit pre-existing directories."""
import ctypes,os,resource,sys
from pathlib import Path
class Ruleset(ctypes.Structure):_fields_=[('access',ctypes.c_uint64)]
class PathBeneath(ctypes.Structure):_fields_=[('access',ctypes.c_uint64),('fd',ctypes.c_int32)]
HANDLED=sum(1<<i for i in (1,4,5,6,7,8,9,10,11,12,13,14))
ALLOW=(1<<1)|(1<<8)|(1<<14)
def apply(paths):
 lib=ctypes.CDLL(None,use_errno=True)
 abi=lib.syscall(444,0,0,1)
 if abi<3:raise RuntimeError("Landlock ABI below 3")
 ruleset=Ruleset(HANDLED);fd=lib.syscall(444,ctypes.byref(ruleset),ctypes.sizeof(ruleset),0)
 if fd<0:raise OSError(ctypes.get_errno(),"landlock ruleset")
 opened=[]
 try:
  for name in paths:
   p=Path(name)
   if not p.is_absolute() or p.is_symlink() or not p.is_dir():raise ValueError("invalid output directory")
   d=os.open(p,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW);opened.append(d);rule=PathBeneath(ALLOW,d)
   if lib.syscall(445,fd,1,ctypes.byref(rule),0):raise OSError(ctypes.get_errno(),"landlock rule")
  if lib.prctl(38,1,0,0,0) or lib.syscall(446,fd,0):raise OSError(ctypes.get_errno(),"landlock restrict")
 finally:
  for d in opened:os.close(d)
  os.close(fd)
def main(args):
 if '--' not in args:raise ValueError("missing command")
 i=args.index('--');paths=args[:i];argv=args[i+1:]
 if not argv or not Path(argv[0]).is_absolute():raise ValueError("absolute executable required")
 apply(paths)
 resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024**2,128*1024**2))
 os.execve(argv[0],argv,dict(os.environ))
if __name__=='__main__':main(sys.argv[1:])

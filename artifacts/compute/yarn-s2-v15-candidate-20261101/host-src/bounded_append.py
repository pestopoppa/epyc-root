"""Bounded append for upstream per-arm results; retains all bytes."""
import fcntl,json,os,stat
from resource_budget import ResourcePause
from pathlib import Path
MAX_LINE=2*1024*1024
MAX_FILE=32*1024*1024
ALLOWED={'A0.jsonl','A1.jsonl','A0.errors.jsonl','A1.errors.jsonl'}
RESULT_ROOT=None
def configure(root):
 global RESULT_ROOT
 r=Path(root)
 if r.is_symlink() or not r.is_dir():raise ValueError('invalid result root')
 RESULT_ROOT=r.resolve(strict=True)
def append(path,record):
 p=Path(path)
 if RESULT_ROOT is None or p.name not in ALLOWED or p.parent.is_symlink() or p.parent.resolve(strict=True)!=RESULT_ROOT:raise ValueError("unexpected output path")
 raw=(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
 if len(raw)>MAX_LINE:raise ResourcePause("result line exceeds bound")
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
 try:
  if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError("not regular")
  fcntl.flock(fd,fcntl.LOCK_EX)
  if os.fstat(fd).st_size+len(raw)>MAX_FILE:raise ResourcePause("result file exceeds bound")
  view=memoryview(raw)
  while view:
   n=os.write(fd,view)
   if n<=0:raise OSError("short append")
   view=view[n:]
  os.fsync(fd)
 finally:os.close(fd)

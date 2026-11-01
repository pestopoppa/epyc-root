import fcntl,sys,time
from pathlib import Path
root=Path(sys.argv[1]);root.mkdir(exist_ok=True)
files=[(root/str(i)).open('a+b') for i in range(192)]
deadline=time.monotonic()+12
try:
 while time.monotonic()<deadline and not (root/'STOP').exists():
  for f in files:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for f in files:fcntl.flock(f,fcntl.LOCK_UN)
finally:
 for f in files:f.close()

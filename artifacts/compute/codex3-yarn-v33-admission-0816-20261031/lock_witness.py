"""Read-only exclusive q0 lock ancestry witness; no lock or lease mutation."""
import os
from pathlib import Path
def birth(pid):
 p=Path('/proc')/str(pid)
 return (p.stat().st_uid,int((p/'stat').read_text().rsplit(') ',1)[1].split()[19]))
def ancestors():
 result=[];seen=set();pid=os.getppid()
 while pid>1:
  if pid in seen:raise RuntimeError("ancestor cycle")
  seen.add(pid);result.append(pid)
  pid=int((Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()[1])
 return result
def match(lines,owner,st):
 key=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)
 for line in lines.splitlines():
  f=line.split()
  if len(f)<8 or f[1:4]!=['FLOCK','ADVISORY','WRITE'] or f[4]!=str(owner):continue
  try:
   a,b,c=f[5].split(':');actual=(int(a,16),int(b,16),int(c))
  except (ValueError,IndexError):continue
  if actual==key and f[6:8]==['0','EOF']:return True
 return False
def capture(path=Path('/mnt/raid0/llm/tmp/cpu_region.GLOBAL.q0.lock')):
 st=path.stat();lines=Path('/proc/locks').read_text()
 candidates=[pid for pid in ancestors() if match(lines,pid,st)]
 if len(candidates)!=1:raise RuntimeError("unique q0 owner not proven")
 owner=candidates[0];ident=birth(owner)
 if ident[0]!=os.getuid():raise RuntimeError("foreign lock owner")
 verify(owner,ident,path)
 return owner,ident
def verify(owner,identity,path=Path('/mnt/raid0/llm/tmp/cpu_region.GLOBAL.q0.lock')):
 if owner not in ancestors() or birth(owner)!=tuple(identity):raise RuntimeError("lock owner changed")
 st=path.stat()
 if not match(Path('/proc/locks').read_text(),owner,st):raise RuntimeError("exclusive q0 lock absent")
 if birth(owner)!=tuple(identity) or not match(Path('/proc/locks').read_text(),owner,path.stat()):raise RuntimeError("lock lost")
 return True

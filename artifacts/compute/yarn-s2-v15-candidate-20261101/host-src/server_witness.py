"""Owned server/listener witness; no claim that no-mmap weights remain mapped."""
import hashlib,os
from pathlib import Path

def file_identity(p):
 s=Path(p).stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def digest(p,active=lambda:True):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  while True:
   if not active():raise TimeoutError("admission lost during hash")
   b=f.read(1024*1024)
   if not b:break
   h.update(b)
 return h.hexdigest()
def procstat(pid):
 x=(Path("/proc")/str(pid)/"stat").read_text().rsplit(") ",1)[1].split();return x[0],int(x[1]),int(x[19])
def listener(pid,port):
 inodes=set()
 for row in Path("/proc/net/tcp").read_text().splitlines()[1:]:
  x=row.split();addr,p=x[1].split(":")
  if x[3]=="0A" and addr=="0100007F" and int(p,16)==port:inodes.add(x[9])
 found=set()
 for fd in (Path("/proc")/str(pid)/"fd").iterdir():
  try:x=os.readlink(fd)
  except FileNotFoundError:continue
  if x.startswith("socket:[") and x.endswith("]") and x[8:-1] in inodes:found.add(x[8:-1])
 if len(found)!=1 or found!=inodes:raise RuntimeError("listener ambiguous or shared")
 return next(iter(found))
class Witness:
 def __init__(self,child,port,binary,model,model_sha,binary_sha,argv,libraries=(),active=lambda:True):
  self.child=child;self.port=port;self.binary=Path(binary);self.model=Path(model);self.argv=list(argv);self.owner=os.getpid()
  if self.argv.count("--cache-ram")!=1 or self.argv[self.argv.index("--cache-ram")+1]!="0" or self.argv.count("-m")!=1 or self.argv[self.argv.index("-m")+1]!=str(self.model):raise ValueError("model/cache argv mismatch")
  self.model_id=file_identity(model);self.binary_id=file_identity(binary)
  if digest(model,active)!=model_sha or digest(binary,active)!=binary_sha:raise ValueError("pin mismatch")
  self.libs=[]
  for path,sha in libraries:
   identity=file_identity(path)
   if digest(path,active)!=sha or file_identity(path)!=identity:raise ValueError("library pin mismatch")
   self.libs.append((str(path),identity,sha))
  state,parent,self.birth=procstat(child.pid)
  if parent!=self.owner or state in ("Z","X"):raise RuntimeError("unowned server")
  self.model_sha=model_sha;self.binary_sha=binary_sha
 def check(self):
  state,parent,birth=procstat(self.child.pid)
  if state in ("Z","X") or parent!=self.owner or birth!=self.birth:raise RuntimeError("server identity changed")
  binary=os.stat("/proc/%d/exe"%self.child.pid)
  if (binary.st_dev,binary.st_ino)!=self.binary_id[:2] or file_identity(self.binary)!=self.binary_id or file_identity(self.model)!=self.model_id:raise RuntimeError("file identity changed")
  maps=(Path("/proc")/str(self.child.pid)/"maps").read_text().splitlines()
  for path,identity,sha in self.libs:
   if file_identity(path)!=identity:raise RuntimeError("library file changed")
   device=f"{os.major(identity[0]):02x}:{os.minor(identity[0]):02x}"
   if not any(len(x.split())>=5 and x.split()[3]==device and int(x.split()[4])==identity[1] for x in maps):raise RuntimeError("pinned library not mapped")
  cmd=(Path("/proc")/str(self.child.pid)/"cmdline").read_bytes().split(b"\0");cmd=[os.fsdecode(x) for x in cmd if x]
  if cmd!=self.argv:raise RuntimeError("argv changed")
  first=listener(self.child.pid,self.port);second=listener(self.child.pid,self.port)
  if first!=second:raise RuntimeError("listener identity changed")
  return {"pid":self.child.pid,"birth":birth,"parent":parent,"listener_inode":second,"model_sha256":self.model_sha,"binary_sha256":self.binary_sha,"libraries":{p:h for p,_,h in self.libs},"model_binding":"prehashed file plus witnessed argv; served model /props requires separate check"}

"""YaRN smoke-only parent confinement before any boot/model child."""
import ctypes,hashlib,json,os,resource,sys
from pathlib import Path
D=Path(__file__).resolve().parent
root=Path(sys.argv[1]);args=sys.argv[2:]
if args[:1]!=['--'] or not root.is_dir() or root.is_symlink() or root.parent!=D or not root.name.startswith('smoke-'):raise ValueError('smoke root/command')
raw=(D/'SOURCE-MANIFEST-v32.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=os.environ['YARN_BUNDLE_SHA']:raise ValueError('manifest anchor')
obj=json.loads(raw)
for name in ('smoke_root_exec.py','write_fence.py'):
 if hashlib.sha256((D/name).read_bytes()).hexdigest()!=obj['files'][name]:raise ValueError('fence source pin')
sys.path.insert(0,str(D));import write_fence as fence
lib=ctypes.CDLL(None,use_errno=True)
if lib.syscall(444,0,0,1)<3:raise RuntimeError('Landlock ABI below3')
rules=fence.Ruleset(fence.HANDLED);fd=lib.syscall(444,ctypes.byref(rules),ctypes.sizeof(rules),0)
if fd<0:raise OSError(ctypes.get_errno(),'smoke ruleset')
try:
 for path,rights in ((root,fence.ALLOW|(1<<7)),(Path('/dev/null'),(1<<1)|(1<<14))):
  opened=os.open(path,os.O_PATH|os.O_NOFOLLOW)
  try:
   rule=fence.PathBeneath(rights,opened)
   if lib.syscall(445,fd,1,ctypes.byref(rule),0):raise OSError(ctypes.get_errno(),'smoke root rule')
  finally:os.close(opened)
 if lib.prctl(38,1,0,0,0) or lib.syscall(446,fd,0):raise OSError(ctypes.get_errno(),'smoke restrict')
finally:os.close(fd)
resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024**2,128*1024**2))
os.environ['TMPDIR']=str(root)
os.execve(args[1],args[1:],dict(os.environ))

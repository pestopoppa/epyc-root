"""Recognize the actual exec'd canonical region-lock transport; never claim locks."""
import hashlib,json,os
from pathlib import Path
D=Path(__file__).resolve().parent
IDENTITY=json.loads((D/'R13-IDENTITY.json').read_bytes())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def require(pid,args,identity=None):
 expected=IDENTITY if identity is None else identity
 if args[:4]!=[expected['python_argv'].encode(),b'-m',expected['module'].encode(),b'run']:raise RuntimeError('noncanonical region-lock module/interpreter argv')
 if b'--no-preflight' in args:raise RuntimeError('outer strict preflight disabled')
 proc=Path('/proc')/str(pid);fields=(proc/'stat').read_text().rsplit(') ',1)[1].split();birth=int(fields[19])
 if proc.stat().st_uid!=os.getuid():raise RuntimeError('region-lock interpreter UID differs')
 if sha(proc/'exe')!=expected['python_exe_sha256']:raise RuntimeError('region-lock actual interpreter bytes differ')
 a=(proc/'cwd').stat();b=Path(expected['cwd']).stat()
 if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):raise RuntimeError('region-lock actual cwd differs')
 for key in ('shim','module'):
  p=Path(expected[key+'_path']);task=proc/'root'/str(p).lstrip('/')
  if sha(p)!=expected[key+'_sha256'] or sha(task)!=expected[key+'_sha256']:raise RuntimeError('region-lock '+key+' source differs')
 after=(proc/'stat').read_text().rsplit(') ',1)[1].split()
 if int(after[19])!=birth or [v for v in (proc/'cmdline').read_bytes().split(b'\0') if v]!=args:raise RuntimeError('region-lock changed during transport observation')
 return {'pid':pid,'birth':birth,'module':expected['module'],'interpreter_sha256':expected['python_exe_sha256'],'cwd':expected['cwd'],'strict_preflight':True}

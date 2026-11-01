"""Verify anchored private and predecessor source bytes before child creation."""
import hashlib,json,re
from pathlib import Path
def identity(p):
 s=p.stat();return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns
def digest(p,active):
 a=identity(p);h=hashlib.sha256()
 with p.open('rb') as f:
  while True:
   if not active():raise TimeoutError("admission lost during source verification")
   b=f.read(1024*1024)
   if not b:break
   h.update(b)
 if identity(p)!=a:raise ValueError("source changed during hashing")
 return h.hexdigest()
def checkpin(path,expected,active,snapshots):
 before=identity(path)
 if digest(path,active)!=expected or identity(path)!=before:raise ValueError("source mismatch: "+str(path))
 snapshots[str(path)]=before
def verify(root,manifest,expected,active):
 root=Path(root).resolve()
 raw=Path(manifest).read_bytes()
 if not re.fullmatch('[0-9a-f]{64}',str(expected)) or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError("manifest anchor")
 obj=json.loads(raw)
 if not isinstance(obj.get('files'),dict):raise ValueError("manifest files")
 snapshots={}
 for name,sha in obj['files'].items():
  if '/' in name or name in ('.','..') or not re.fullmatch('[0-9a-f]{64}',str(sha)):raise ValueError("manifest entry")
  checkpin(root/name,sha,active,snapshots)
 predecessor=Path(obj['predecessor_manifest'])
 checkpin(predecessor,obj['predecessor_manifest_sha256'],active,snapshots)
 count=0
 for line in predecessor.read_text().splitlines():
  sha,name=line.split('  ',1);p=Path(name)
  if not p.is_absolute() or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError("predecessor entry")
  checkpin(p,sha,active,snapshots)
  count+=1
 if not count:raise ValueError("empty predecessor")
 external=obj.get("external_files",{})
 if not isinstance(external,dict) or not external:raise ValueError("external source pins missing")
 for name,sha in external.items():
  path=Path(name)
  if not path.is_absolute() or not re.fullmatch('[0-9a-f]{64}',str(sha)):raise ValueError("external source entry")
  checkpin(path,sha,active,snapshots)
 return {"private_files":len(obj['files']),"predecessor_files":count,"external_files":len(external),"source_identities":snapshots}
def unchanged(snapshot):
 try:return all(identity(Path(name))==tuple(value) for name,value in snapshot.items())
 except OSError:return False

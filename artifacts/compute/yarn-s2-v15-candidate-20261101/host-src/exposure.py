"""Create-only per-item exposure markers; indeterminate requests cannot be retried."""
import hashlib,json,os
from pathlib import Path
def key(arm,item,prompt_sha):
 if arm not in ('A0','A1') or not isinstance(item,str) or not item or not isinstance(prompt_sha,str) or len(prompt_sha)!=64 or any(c not in '0123456789abcdef' for c in prompt_sha):raise ValueError("bad exposure identity")
 return hashlib.sha256(json.dumps([arm,item],separators=(',',':')).encode()).hexdigest()
def put(path,obj):
 data=(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode()
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600)
 try:
  view=memoryview(data)
  while view:
   n=os.write(fd,view)
   if n<=0:raise OSError("short write")
   view=view[n:]
  os.fsync(fd)
 finally:os.close(fd)
 fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def state(directory,arm,item,prompt_sha):
 k=key(arm,item,prompt_sha);d=Path(directory);begin=d/(k+'.start');end=d/(k+'.response')
 if begin.is_symlink() or end.is_symlink():raise ValueError("symlink")
 if end.exists() and not begin.exists():raise ValueError("response without start")
 if not begin.exists():return "unexposed"
 try:
  rec=json.loads(begin.read_bytes())
  if rec.get("schema")!="private.yarn.exposure.v1" or rec.get("arm")!=arm or rec.get("item_id")!=item or rec.get("prompt_sha256")!=prompt_sha:return "unknown"
  if not end.exists():return "unknown"
  response=json.loads(end.read_bytes());h=response.get("response_sha256")
  if response.get("schema")!="private.yarn.response.v1" or not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):return "unknown"
  return "responded"
 except (OSError,ValueError,TypeError,AttributeError):return "unknown"
def begin(directory,arm,item,prompt_sha,grant_sha,kind="grant"):
 if kind not in ("grant","r11"):raise ValueError("bad admission kind")
 if not isinstance(grant_sha,str) or len(grant_sha)!=64 or any(c not in '0123456789abcdef' for c in grant_sha):raise ValueError("bad grant hash")
 if state(directory,arm,item,prompt_sha)!="unexposed":raise ValueError("exposure already exists")
 k=key(arm,item,prompt_sha)
 put(Path(directory)/(k+'.start'),{"schema":"private.yarn.exposure.v1","arm":arm,"item_id":item,"prompt_sha256":prompt_sha,"admission_kind":kind,"admission_sha256":grant_sha})
def response(directory,arm,item,prompt_sha,response_sha):
 if not isinstance(response_sha,str) or len(response_sha)!=64 or any(c not in '0123456789abcdef' for c in response_sha):raise ValueError("bad response hash")
 if state(directory,arm,item,prompt_sha)!="unknown":raise ValueError("no unique in-flight start")
 rec=json.loads((Path(directory)/(key(arm,item,prompt_sha)+'.start')).read_bytes())
 if rec.get("schema")!="private.yarn.exposure.v1" or rec.get("arm")!=arm or rec.get("item_id")!=item or rec.get("prompt_sha256")!=prompt_sha:raise ValueError("start identity mismatch")
 put(Path(directory)/(key(arm,item,prompt_sha)+'.response'),{"schema":"private.yarn.response.v1","response_sha256":response_sha})

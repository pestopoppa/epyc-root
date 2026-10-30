"""EVL44 task-private child supervisor, not an admission or inference launcher."""
import os,resource,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/mnt/raid0/llm/tmp/yarn-judged-cell-prep-20261029')
from descendant_custody import Custody,proc
FLOOR=150*1024**3
MAX_RSS=8*1024**3
MAX_LOG=16*1024**2

def rss(pid):
 try:
  for line in Path('/proc',str(pid),'status').read_text().splitlines():
   if line.startswith('VmRSS:'):return int(line.split()[1])*1024
 except FileNotFoundError:return 0
 raise RuntimeError('RSS sample unavailable')
def supervise(command,output,*,seconds=300,required_headroom=0,mem_limit=MAX_RSS,stop=lambda:False,disk_path='/mnt/raid0/llm'):
 if not 0<seconds<=300 or type(required_headroom) is not int or required_headroom<0 or not 0<mem_limit<=MAX_RSS:raise ValueError('invalid limits')
 custody=Custody();start=time.monotonic();deadline=start+seconds;peak=0;samples=0;reason=None;p=None
 def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_LOG,MAX_LOG))
 try:
  free=os.statvfs(disk_path).f_bavail*os.statvfs(disk_path).f_frsize
  if free<FLOOR+required_headroom:raise RuntimeError('disk admission refused')
  with Path(output).open('xb') as log:
   p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=cap)
   while p.poll() is None:
    known=custody.scan();current=rss(os.getpid())+sum(rss(pid) for pid in known if proc(pid) is not None)
    samples+=1;peak=max(peak,current)
    free=os.statvfs(disk_path).f_bavail*os.statvfs(disk_path).f_frsize
    if current>mem_limit:reason='rss limit';break
    if free<FLOOR:reason='disk floor';break
    if stop():reason='stop';break
    if time.monotonic()>=deadline:reason='deadline';break
    time.sleep(.05)
   rc=p.poll()
 finally:
  drained=custody.drain()
 if not drained:raise RuntimeError('descendant drain failed')
 return {'rc':rc,'reason':reason,'rss_peak_sampled':peak,'samples':samples,'elapsed':time.monotonic()-start,'drained':drained,'owned_pids':list(custody.known)}

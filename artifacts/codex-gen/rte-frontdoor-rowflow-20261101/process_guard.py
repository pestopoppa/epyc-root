"""Task-local captured-process and listener guards."""
import os,pathlib,signal,time
SESSIONS={}
def register_session(p,birth):
 if os.getsid(p.pid)==p.pid:SESSIONS[p.pid]=birth

def ident(pid):
 try:
  x=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split();return int(x[19]),x[0]
 except (OSError,ValueError):return None

def alive(pid,birth):
 x=ident(pid);return x is not None and x[0]==birth and x[1]!='Z'

def discover(owned):
 # A captured private session preserves descendants even after its parent exits.
 if SESSIONS:
  for entry in pathlib.Path('/proc').iterdir():
   if not entry.name.isdigit():continue
   try:
    row=(entry/'stat').read_text().rsplit(') ',1)[1].split()
    if int(row[3]) in SESSIONS:owned.setdefault(int(entry.name),int(row[19]))
   except (OSError,ValueError):pass
 # Capture live descendants before parents disappear; never use argv/name matching.
 for pid,birth in list(owned.items()):
  if not alive(pid,birth):continue
  try:children=pathlib.Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
  except OSError:continue
  for child in children:
   child=int(child);x=ident(child)
   if x and child not in owned:owned[child]=x[0];discover(owned)

def listener_witness(pid,birth,port=8070):
 if not alive(pid,birth):raise RuntimeError('captured server identity not live')
 inodes=set()
 for table in ['/proc/net/tcp','/proc/net/tcp6']:
  for line in pathlib.Path(table).read_text().splitlines()[1:]:
   row=line.split()
   if row[3]=='0A' and int(row[1].rsplit(':',1)[1],16)==port:inodes.add(row[9])
 fds={}
 for fd in pathlib.Path(f'/proc/{pid}/fd').iterdir():
  try:target=os.readlink(fd)
  except OSError:continue
  if target.startswith('socket:['):fds[target[8:-1]]=fd.name
 own=inodes.intersection(fds)
 if not inodes or own!=inodes:raise RuntimeError('port listener not exclusively owned by captured server')
 return {'pid':pid,'birth':birth,'port':port,'listener_inodes':sorted(inodes),'socket_fds':{i:fds[i] for i in own},'observed_at':time.time()}

def drain(owned,handles):
 discover(owned)
 for sig,seconds in [(signal.SIGTERM,15),(signal.SIGKILL,3)]:
  discover(owned)
  for pid,birth in list(owned.items()):
   if alive(pid,birth):
    try:os.kill(pid,sig)
    except ProcessLookupError:pass
  until=time.monotonic()+seconds
  while any(alive(pid,birth) for pid,birth in owned.items()) and time.monotonic()<until:
   discover(owned);time.sleep(.025)
 for p in handles:
  try:p.wait(timeout=1)
  except Exception:pass
 return [pid for pid,birth in owned.items() if alive(pid,birth)]

def resource_sample(owned,output_dir,rss_limit=80*1024**3,output_limit=1024**3):
 discover(owned);rss=0
 for pid,birth in list(owned.items()):
  if not alive(pid,birth):continue
  try:
   for line in pathlib.Path(f'/proc/{pid}/status').read_text().splitlines():
    if line.startswith('VmRSS:'):rss+=int(line.split()[1])*1024
  except OSError:pass
 size=0
 if output_dir:
  for p in output_dir.rglob('*'):
   try:
    if p.is_file():size+=p.stat().st_size
   except OSError:pass
 return {'at':time.time(),'owned_tree_rss_bytes':rss,'output_bytes':size,'boundary':rss>rss_limit or size>output_limit}

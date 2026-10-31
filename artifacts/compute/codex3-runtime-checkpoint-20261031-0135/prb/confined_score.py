"""Bound each native code scorer using an invocation-owned cgroup."""
import json,os,subprocess,sys,time,uuid
from pathlib import Path
D=Path(__file__).resolve().parent
LAST={}

def score(answer,question):
 global LAST
 LAST={}
 c=Path('/sys/fs/cgroup')/f'codex3-prb-score-{os.getpid()}-{uuid.uuid4().hex[:12]}'
 c.mkdir();p=None
 registry=D/'score-cgroups';registry.mkdir(exist_ok=True)
 receipt=registry/c.name
 st=c.stat()
 with receipt.open('x') as f:f.write(json.dumps({'path':str(c),'dev':st.st_dev,'ino':st.st_ino})+'\n');f.flush();os.fsync(f.fileno())
 try:
  launch='import os,sys;from pathlib import Path;Path(sys.argv[1],"cgroup.procs").write_text(str(os.getpid()));os.execv(sys.executable,[sys.executable,"-B",sys.argv[2]])'
  p=subprocess.Popen([sys.executable,'-B','-c',launch,str(c),str(D/'scorer_child.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
  try:birth=int(Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19])
  except (OSError,IndexError):birth=None
  LAST={'pid':p.pid,'birth_ticks':birth,'cgroup':str(c),'cgroup_dev':st.st_dev,'cgroup_ino':st.st_ino,'status':'running'}
  inp={'answer':answer,'expected':question.get('expected',''),'config':question.get('scoring_config') or {}}
  timeout=min(max(int(inp['config'].get('timeout',10))+5,6),60)
  deadline=time.monotonic()+timeout; first=True; reason=None
  while True:
   try:
    out,err=p.communicate(json.dumps(inp) if first else None,timeout=.1);break
   except subprocess.TimeoutExpired:first=False
   members=(c/'cgroup.procs').read_text().split(); rss=0
   for pid in members:
    try:
     status=Path('/proc',pid,'status').read_text(); rss+=int(next(x.split()[1] for x in status.splitlines() if x.startswith('VmRSS:')))
    except (FileNotFoundError,StopIteration): pass
   if len(members)>16 or rss>512*1024 or time.monotonic()>deadline:
    reason='scorer resource or wall limit';LAST['limit_reason']=reason;(c/'cgroup.kill').write_text('1');out,err=p.communicate(timeout=5);break
  remaining=(c/'cgroup.procs').read_text().split()
  if remaining:(c/'cgroup.kill').write_text('1');return None
  LAST.update(status='exited',returncode=p.returncode)
  if reason or p.returncode!=0:return None
  rec=json.loads(out);LAST['outcome']=rec;return rec.get('correct') if isinstance(rec.get('correct'),bool) else None
 finally:
  if c.exists():
   members=(c/'cgroup.procs').read_text().split()
   if members:(c/'cgroup.kill').write_text('1')
   for _ in range(100):
    if 'populated 0' in (c/'cgroup.events').read_text():break
    time.sleep(.05)
   else:raise RuntimeError('score cgroup did not drain')
   c.rmdir()
   LAST['cgroup_drained']=True
   receipt.unlink(missing_ok=True)

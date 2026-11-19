#!/usr/bin/env python3
"""Synthetic observer overhead on a fixed CPU-time controlled workload; never a floor."""
import hashlib,json,os,pathlib,resource,select,signal,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(D/'native'))
from owner_hook import RequestCapture
CHILD='''import hashlib,json,os,sys,time
os.sched_setaffinity(0,{int(sys.argv[1])})
print('READY',flush=True)
if sys.stdin.readline().strip()!='RUN':raise SystemExit(40)
wall=time.monotonic_ns(); cpu=time.process_time_ns(); budget=int(float(sys.argv[2])*1e9); count=0; x=1
while time.process_time_ns()-cpu<budget:
 for i in range(4096): x=(x*1664525+1013904223)&0xffffffff
 count+=4096
print(json.dumps({'count':count,'checksum':x,'wall_ns':time.monotonic_ns()-wall,'cpu_ns':time.process_time_ns()-cpu}),flush=True)
if sys.stdin.readline().strip()!='RELEASE':raise SystemExit(41)
'''

def line(p,timeout,stop,deadline):
 end=min(time.monotonic()+timeout,time.monotonic()+max(0,deadline-time.time()))
 while True:
  active(stop,deadline)
  remaining=end-time.monotonic()
  if remaining<=0:raise TimeoutError('controlled target response timeout')
  r,_,_=select.select([p.stdout],[],[],min(.2,remaining))
  if r:
   s=p.stdout.readline()
   if not s:raise RuntimeError('controlled target closed output')
   return s.strip()


def active(stop,deadline):
 if stop.exists() or time.time()>=deadline: raise TimeoutError('STOP/deadline')

def target_identity(pid):
 raw=pathlib.Path(f'/proc/{pid}/stat').read_text(); prefix,sep,tail=raw.rpartition(') ')
 if not sep or prefix.split(' (',1)[0]!=str(pid):raise ValueError('bad target process identity')
 return {'pid':pid,'start_ticks':int(tail.split()[19]),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()}

def main():
 signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(InterruptedError('SIGTERM')))
 signal.signal(signal.SIGINT,lambda *_: (_ for _ in ()).throw(InterruptedError('SIGINT')))
 smoke=os.getenv('FILLER_DRYRUN')=='1'
 admitted=set()
 for p in os.environ['FILLER_CPUS'].split(','):
  b=[int(x) for x in p.split('-')];admitted.update(range(b[0],b[-1]+1))
 available=admitted & os.sched_getaffinity(0)
 cpus=set(sorted(available)[:4]) if smoke else set(range(96))
 if (smoke and len(cpus)!=4) or not cpus<=admitted or not cpus<=os.sched_getaffinity(0):raise ValueError('claim/affinity insufficient')
 os.sched_setaffinity(0,cpus)
 # 480 perf sessions plus duplicated same-FD guards, descriptors and headroom.
 soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE); required=2*len(cpus)*5+128
 if soft!=resource.RLIM_INFINITY and soft<required: raise ValueError(f'RLIMIT_NOFILE {soft} below required {required}')
 deadline=float(os.environ['FILLER_DEADLINE']);stop=pathlib.Path(os.environ['FILLER_STOPFILE'])
 result=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'RESULT.json'
 outdir=result.parent/(result.stem+'-evidence');outdir.mkdir(parents=True,exist_ok=False)
 pairs=1 if smoke else 24; seconds=.1 if smoke else 16.0; rows=[]
 for i in range(pairs):
  for arm in (('off','on') if i%2==0 else ('on','off')):
   active(stop,deadline)
   proc=subprocess.Popen([sys.executable,'-I','-c',CHILD,str(min(cpus)),str(seconds)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
   capture=None; start=time.monotonic_ns()
   try:
    if line(proc,10,stop,deadline)!='READY':raise RuntimeError('target handshake failed')
    identity=target_identity(proc.pid);rec=None;worker=None
    if arm=='on':
     ev=(outdir/f'pair{i:02d}-{arm}.json').resolve()
     context={'launch_ordinal':i,'phase':'synthetic-overhead','slot_index':0,'prompt_id':'cpu-time-controlled','request_sha256':hashlib.sha256(CHILD.encode()).hexdigest()}
     capture=RequestCapture(ev,cpus,request_context=context,timeout_s=180)
     capture.attach_target(proc.pid);capture.begin()
    proc.stdin.write('RUN\n');proc.stdin.flush()
    target=json.loads(line(proc,max(30,seconds*4),stop,deadline))
    if type(target.get('count')) is not int or target['count']<=0 or not target.get('wall_ns') or not target.get('cpu_ns'):raise ValueError('invalid target record')
    if capture:
     rec=capture.end()
     if rec['target_identity']!=identity:raise ValueError('target identity mismatch')
     if not capture.guard.finished or capture.guard.process.poll()!=0:raise ValueError('observer worker not cleanly reaped')
     worker={'pid':capture.guard.pid,'returncode':capture.guard.process.returncode,'reaped':True}
     ev.chmod(0o644); pathlib.Path(str(ev)+'.rings').chmod(0o644)
    proc.stdin.write('RELEASE\n');proc.stdin.flush();proc.stdin.close()
    if proc.wait(timeout=10):raise RuntimeError('target returned nonzero')
    if proc.poll()!=0:raise ValueError('target not cleanly reaped')
    child={'pid':proc.pid,'returncode':proc.returncode,'reaped':True}
    elapsed=time.monotonic_ns()-start
    rows.append({'pair':i,'arm':arm,'target':target,'unit_wall_ns':elapsed,'observer':rec,'target_identity':identity,'child_cleanup':child,'worker_cleanup':worker})
    # Unit checkpoint is durable only after child and observer have completed.
    with (outdir/'units.jsonl').open('a') as f:f.write(json.dumps(rows[-1],sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    print(f'UNIT pair={i} arm={arm} completed',flush=True)
   finally:
    if capture and capture.state!='finished':capture.abort()
    if proc.poll() is None:
     proc.terminate()
     try:proc.wait(timeout=2)
     except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
   active(stop,deadline)
 if len(rows)!=pairs*2:raise ValueError('missing paired unit')
 doc={'schema':'epyc.ch26.synthetic-observer-overhead.v1','status':'diagnostic_complete','measurement_admission':'none','floor_claim':'none','scope':'single pinned synthetic CPU-time workload; not C5 or inference','cpus':sorted(cpus),'pair_count':pairs,'seconds_cpu':seconds,'units':rows}
 result.write_text(json.dumps(doc,sort_keys=True)+'\n');print('completed matched synthetic diagnostic',flush=True)
if __name__=='__main__':main()

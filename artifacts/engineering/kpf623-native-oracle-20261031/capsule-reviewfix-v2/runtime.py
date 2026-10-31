#!/usr/bin/python3
import argparse,datetime,hashlib,json,os,pathlib,signal,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
ID='codex-ni-kpf623-native-oracle-r1-20261031'
stop=False

def birth(pid):return int(pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
def write(p,x):p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def interrupted(*_):
 global stop;stop=True

def check_sources():
 subprocess.run(['sha256sum','--status','-c',str(D/'SOURCES.sha256')],cwd=D,check=True)
 subprocess.run(['sha256sum','--status','-c',str(D/'EXTERNAL.sha256')],cwd=D,check=True)

def enrolled():
 flags=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/ready');paths=[flags/f'{ID}.json',flags/'armed'/f'{ID}.json'];found=[p for p in paths if p.is_file()]
 if len(found)!=1:raise RuntimeError('no unique READY or armed enrollment')
 m=json.loads(found[0].read_text())
 if m['owner']!='codex-ni' or m['id']!=ID or m['hold'] is not None or m['regions']!='any-cpu-quarter' or m['class']!='diagnostic':raise RuntimeError('enrollment mismatch')
 for k,f in [('launcher','launch.sh'),('job','runtime.py'),('source_manifest','SOURCES.sha256')]:
  if m[k]!={'path':str(D/f),'sha256':sha(D/f)}:raise RuntimeError('enrollment source drift')
 return m

def main():
 a=argparse.ArgumentParser();a.add_argument('--mode',choices=['smoke','cutoff','full']);a.add_argument('--check-enrolled',action='store_true');a.add_argument('--complete',action='store_true');z=a.parse_args()
 if z.complete:
  x=json.loads((D/'RESULT.json').read_text());return 0 if x['rc']==0 and not x['partial'] and x['cleanup_verified'] and x['native_cases']==2 else 1
 if z.check_enrolled:check_sources();enrolled();return 0
 if not z.mode:return 64
 check_sources()
 if z.mode!='full':
  sys.path.insert(0,'/mnt/raid0/llm/tmp/codex-ni-ufh12-full-private-apply-r4-20261029');import prep_supervisor
  cpus=prep_supervisor.parse_cpus(os.environ['FILLER_CPUS'])
  if len(cpus)!=2 or min(cpus)<96 or max(cpus)>183:raise RuntimeError('R11 CPUs required')
  prep_supervisor.check_admission(cpus,time.time())
 else:enrolled()
 allowed=set(os.sched_getaffinity(0));declared=set()
 for t in os.environ['FILLER_CPUS'].split(','):
  q=t.split('-');declared.update(range(int(q[0]),int(q[-1])+1))
 if not allowed or not allowed<=declared:raise RuntimeError('runtime affinity escaped declaration')
 if __import__('shutil').disk_usage(D).free<150*1024**3+128*1024**2:raise RuntimeError('RAID floor')
 end=min(time.monotonic()+260,time.monotonic()+max(0,int(os.environ.get('FILLER_DEADLINE',int(time.time()+260)))-time.time()))
 out=D/('runs' if z.mode=='full' else 'smoke-runs')/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+f'-{os.getpid()}-'+z.mode);out.mkdir(parents=True)
 model=json.loads((D/'MODEL.json').read_text())['path'];begin=time.monotonic();peak=0;rc=0;partial=False;cases=[];owned={};cleanup=True;reason=None
 for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,interrupted)
 for layout in ['contiguous','permuted']:
  if stop or time.monotonic()>=end or (D/'STOP').exists():rc=75;partial=bool(cases);reason='window-or-STOP';break
  log=out/(layout+'.log');env=dict(os.environ,OMP_NUM_THREADS='1',LD_LIBRARY_PATH='/mnt/raid0/llm/tmp/codex-ni-20261028-ranked2/aux-private/build/bin')
  if z.mode=='cutoff':env['KPF623_CUTOFF_PROBE']='1'
  with log.open('wb') as f:
   p=subprocess.Popen([str(D/'oracle'),model,layout],stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True);owned[p.pid]=birth(p.pid);cut=False
   try:
    while p.poll() is None:
     try:
      status=pathlib.Path(f'/proc/{p.pid}/status').read_text();rss=int(next(l.split()[1] for l in status.splitlines() if l.startswith('VmRSS:')))*1024;peak=max(peak,rss)
     except (OSError,StopIteration):rss=0
     if rss>8*1024**3:rc=70;reason='RSS cap';cut=True;break
     if z.mode=='cutoff' and b'PHASE queries=' in log.read_bytes():rc=75;partial=True;reason='active-native-cutoff';cut=True;break
     if stop or time.monotonic()>=end or (D/'STOP').exists():rc=75;partial=True;reason='window-or-STOP';cut=True;break
     time.sleep(.01)
   finally:
    if p.poll() is None:
     if birth(p.pid)!=owned[p.pid]:raise RuntimeError('PID birth drift')
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=10)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
    try:
     s=pathlib.Path(f'/proc/{p.pid}/stat').read_text();cleanup=False
    except FileNotFoundError:pass
   text=log.read_text(errors='replace');observed='PHASE queries=' in text
   cases.append({'layout':layout,'pid':p.pid,'birth':owned[p.pid],'native_rc':p.returncode,'native_compute_observed':observed,'log':str(log),'sha256':sha(log),'comparison_count':text.count('COMPARE '),'phase_count':text.count('PHASE queries='),'passed':'NATIVE_ORACLE_PASS' in text})
   if cut:break
   if p.returncode!=0 or not cases[-1]['passed'] or cases[-1]['phase_count']!=2:rc=1;reason='native-oracle-refused';break
 result={'id':ID,'mode':z.mode,'source_manifest_sha256':sha(D/'SOURCES.sha256'),'oracle_binary_sha256':sha(D/'oracle'),'oracle_source_sha256':sha(D/'oracle.cpp'),'external_manifest_sha256':sha(D/'EXTERNAL.sha256'),'negative_control_key':bool(os.environ.get('KPF623_CORRUPT_KEY')),'negative_control_query':bool(os.environ.get('KPF623_CORRUPT_QUERY')),'ran_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rc':rc,'partial':partial,'work_started':bool(cases),'cleanup_verified':cleanup,'native_cases':len(cases),'cases':cases,'wall_s':time.monotonic()-begin,'sampled_peak_RSS':peak,'allowed_cpus':sorted(allowed),'reason':reason,'probability_absolute_tolerance':1e-6,'dot_residual':'ungraded','scope':'generated tiny model engineering diagnostic only; no selector/G3/quality/performance acceptance'}
 write(out/'RESULT.json',result)
 if z.mode=='full':write(D/'RESULT.json',result)
 print(json.dumps({'result':str(out/'RESULT.json'),'rc':rc,'partial':partial,'cleanup_verified':cleanup,'wall_s':result['wall_s']}),flush=True)
 return rc if cleanup else 70
if __name__=='__main__':sys.exit(main())

#!/usr/bin/env python3
"""One-shot KPF postbuild event driver. Never publishes a manifest."""
import datetime,fcntl,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
S=Path('/mnt/raid0/llm/tmp/codex3-kpf183-postbuild-repair-20261031')
B=Path('/mnt/raid0/llm/tmp/codex3-kpf183-e332-build-r2-20261030')
F=Path('/mnt/raid0/llm/tmp/compute-flags')
H=Path('/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/build-r3')
ID='codex3-kpf183-e332-cpu-build-r2-20261030'
PINS={
 str(B/'watch-observe-v2.py'):'24581752312102b2b48657ab97397a750c081a97bb68a1fd4cc820fc4417e85b',
 str(S/'candidate-one-attempt.py'):'bf1e088db919dd22c469700e4f109ebee98c23885d0dd865419187f2e3b3918b',
 str(S/'classifier.py'):'335c89dbf133b850130491a01314ae5b4578f6a96fdddf3f15fc0b72c10e71c0',
 str(H/'pf1_graceful.py'):'ec0c52a3c760a736462392c22a32d85283d3ad9bb3ec5027cbc40646e149d5ac',
 str(H/'pidfd_subreaper_v3.py'):'7714cc37ad0738812910ec4d60227cc2b7d4f3927dc97ab8d59ba2e74d0be44f',
 str(H/'pidfd_custody_v2.py'):'775fc851871f17724417e355e34e7c0dab14fa2f2d2a66e562d473f169cf1291',
 str(H/'r11_supervisor.py'):'6564ca7f0c134f4beeb074a4e32996bb196300ef02ca5ef2e201ddc82f2990a9',
 str(H/'smoke_admission.py'):'94f69a7731b32e35a1156173c826fe935fa1217f5967972b4bc66bf2e203ed1e',
}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for part in iter(lambda:f.read(1048576),b''):h.update(part)
 return h.hexdigest()
def pins():
 for p,expected in PINS.items():
  if digest(p)!=expected:raise RuntimeError('dependency pin mismatch: '+p)
def birth(pid):
 return int(Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()[19])
def save(name,data):
 path=S/name;tmp=S/(name+'.tmp')
 with tmp.open('w') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
 fd=os.open(S,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def identity():
 return {'pid':os.getpid(),'birth':birth(os.getpid()),'uid':os.getuid(),'mount_namespace':os.readlink('/proc/self/ns/mnt')}
def valid_namespace():
 return (os.getuid()==1000 and birth(1970275)==150632573
  and os.readlink('/proc/self/ns/mnt')==os.readlink('/proc/1970275/ns/mnt')
  and Path('/workspace/scripts/coordination/validate_fillers.py').is_file()
  and subprocess.run(['sudo','-n','/usr/bin/chroot','/proc/1/root','/usr/bin/setpriv','--reuid=1000','--regid=1000','--groups=992','/usr/bin/test','-d','/mnt/micron/codex3-lanes/kpf-e332-src']).returncode==0)
def emit_final(state,detail):
 payload={**identity(),'state':state,'detail':detail,'at':now(),'automatic_publication':False}
 save('EVENT-TERMINAL.json',payload)
 sent=False
 try:
  fd=os.open(F/'codex-channels/codex3.md',os.O_WRONLY|os.O_APPEND)
  try:
   os.write(fd,('\n## KPF postbuild event '+payload['at']+'\n'+state+': '+str(detail)+'; no READY publication. Evidence '+str(S/'EVENT-TERMINAL.json')+'\n').encode());os.fsync(fd);sent=True
  finally:os.close(fd)
 finally:
  save('EVENT-NOTIFY.json',{'channel_append_succeeded':sent,'state':state,'at':now()})
  flag=S/('EVENT-'+state+'.flag')
  fd=os.open(flag,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644);os.fsync(fd);os.close(fd)
def interrupted(sig,frame):raise InterruptedError('driver signal '+str(sig))
def main():
 lock=(S/'EVENT.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if not valid_namespace():raise RuntimeError('wrong keeper namespace or identity')
 pins()
 sys.path.insert(0,str(H))
 import pidfd_subreaper_v3 as subreaper
 import pf1_graceful
 subreaper.enable()
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 if sys.argv[1:]==['--self-test']:
  print(json.dumps({'namespace':identity(),'pins':PINS,'self_test':'PASS'}));return
 if sys.argv[1:]:raise RuntimeError('invalid arguments')
 if (S/'EVENT-TERMINAL.json').exists() or (S/'EVENT-LAUNCHED.json').exists():raise RuntimeError('event already launched or terminal')
 watch_pid=280490
 if birth(watch_pid)!=152952929 or os.readlink('/proc/%s/ns/mnt'%watch_pid)!=os.readlink('/proc/self/ns/mnt'):raise RuntimeError('observation watcher identity mismatch')
 ident={**identity(),'state':'WAIT_BUILD','started_at':now(),'automatic_publication':False,'pins':PINS,'observation_watcher':{'pid':watch_pid,'birth':152952929}}
 save('EVENT-LIVE.json',ident)
 state='FAILURE';detail='driver did not complete'
 child=None
 try:
  deadline=time.monotonic()+24*3600
  while time.monotonic()<deadline:
   if not valid_namespace():raise RuntimeError('keeper namespace or identity changed')
   pins()
   if (B/'BUILD-SUCCESS').is_file() and (B/'BUILD-DIGESTS.txt').is_file():break
   if (F/'ready/refused'/(ID+'.json')).exists():raise RuntimeError('build manifest refused')
   if (F/'grants'/(ID+'.ended')).exists() and not (B/'BUILD-SUCCESS').is_file():raise RuntimeError('build ended without success; inspect original result')
   time.sleep(15)
  else:raise RuntimeError('24h build observation deadline')
  while time.monotonic()<deadline:
   if not valid_namespace():raise RuntimeError('keeper namespace or identity changed')
   pins()
   cmd=['flock','-n',str(F/'prep-locks/28-29.lock'),'taskset','-c','124,125','env','OMP_NUM_THREADS=1','sudo','-n','--preserve-env=OMP_NUM_THREADS','/usr/bin/chroot','/proc/1/root','/usr/bin/setpriv','--reuid=1000','--regid=1000','--groups=992','/usr/bin/python3','-B',str(H/'r11_supervisor.py'),'15','--','/usr/bin/true']
   probe=subprocess.run(cmd,capture_output=True,text=True)
   save('EVENT-ADMISSION.json',{'at':now(),'rc':probe.returncode,'stdout':probe.stdout,'stderr':probe.stderr})
   if probe.returncode==0:
    records=[json.loads(line) for line in probe.stdout.splitlines() if line.startswith('{')]
    if len(records)!=1 or records[0].get('failure') is not None or records[0].get('children_drained') is not True or records[0].get('child_rc')!=0:raise RuntimeError('ambiguous admission probe')
    break
   if probe.returncode==78 and probe.stdout.startswith('supervisor admission refused: '):time.sleep(15);continue
   if probe.returncode==1 and not probe.stdout and not probe.stderr:time.sleep(15);continue
   raise RuntimeError('unexpected admission probe outcome; inspect EVENT-ADMISSION.json')
  else:raise RuntimeError('24h admission observation deadline')
  pins()
  before={p.name for p in S.glob('attempt-*') if p.is_dir()}
  with (S/'EVENT-QUALIFIER.log').open('x') as out:
   child=subprocess.Popen([sys.executable,'-B',str(S/'candidate-one-attempt.py'),'--execute-one-attempt'],stdout=out,stderr=subprocess.STDOUT)
   fd,info=__import__('pidfd_custody_v2').open_child(child.pid)
   save('EVENT-LAUNCHED.json',{**identity(),'at':now(),'child_pid':child.pid,'child_birth':info['birth'],'candidate_sha256':PINS[str(S/'candidate-one-attempt.py')]})
   try:rc=child.wait()
   finally:os.close(fd);out.flush();os.fsync(out.fileno())
  stray=subreaper.children()
  if stray:
   pf1_graceful.drain();raise RuntimeError('unexpected descendants after candidate exit: '+str(stray))
  attempts=[p for p in S.glob('attempt-*') if p.is_dir() and p.name not in before]
  if len(attempts)!=1:raise RuntimeError('candidate did not create exactly one attempt')
  result=json.loads((attempts[0]/'status.json').read_text())
  detail={'rc':rc,'attempt':str(attempts[0]),'attempt_status':result,'children_drained':True}
  if rc==0 and result.get('state')=='QUALIFIED_NOT_PUBLISHED':state='QUALIFIED'
  elif result.get('state')=='RETRYABLE_PRE_NATIVE_ADMISSION_REFUSAL':state='ADMISSION-REFUSAL'
  else:state='FAILURE'
 except BaseException as exc:
  if child is not None and child.poll() is None:pf1_graceful.drain(leader=child);child.wait()
  pf1_graceful.drain()
  detail={'error':repr(exc),'children_drained':not bool(subreaper.children())}
 finally:
  emit_final(state,detail)
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  if sys.argv[1:]!=['--self-test'] and not (S/'EVENT-TERMINAL.json').exists():
   emit_final('FAILURE',{'error':repr(exc),'stage':'driver startup'})
  raise

import json,os,pathlib,signal,tempfile,threading,time
import cpu_runner as r
D=r.D
pins=json.loads((D/'library-pins.json').read_text())
for p in (D/'mock_cli',D/'mock.so'):
 pins[str(p.resolve())]=r.ref.sha(p)
env={'PATH':'/usr/bin:/bin','LD_PRELOAD':str(D/'observer.so')}
original_sample=r.sample;original_check=r.check
def fixture_sample(pid,birth,pins):
 s=original_sample(pid,birth,pins)
 if s['affinity']!='48-49':raise ValueError('fixture affinity')
 s['affinity']='24-25';s['kfd_present']=True;s['vram']={'vram_fixture':0}
 return s
r.sample=fixture_sample
with tempfile.TemporaryDirectory(dir=D) as t:
 p=pathlib.Path(t); stop=p/'STOP'
 def run(name,extra=None,pp=pins):return r.one([str(D/'mock_cli')],dict(env,**(extra or {})),p/name,stop,time.time()+10,pp)
 result=run('cpu');assert result['transcript']=='mock forwarding PASS\n'
 def reject(f):
  try:f()
  except (ValueError,RuntimeError):return
  raise AssertionError('unexpected acceptance')
 reject(lambda:run('gpu',{'MOCK_DEVICE':'1'}));reject(lambda:run('accel',{'MOCK_DEVICE':'3'}));reject(lambda:run('missing',{'LD_PRELOAD':''}))
 bad=dict(pins);del bad[str((D/'mock.so').resolve())];reject(lambda:run('foreign',pp=bad))
 stop.touch();reject(lambda:run('stop'));stop.unlink()
 count=[0]
 def revoked(stop,deadline):
  count[0]+=1
  if count[0]>=2:raise RuntimeError("grant revoked")
 reject(lambda:r.one([str(D/"mock_cli")],env,p/"revoked",stop,time.time()+10,pins,revoked))
 revoked_samples=json.loads((p/"revoked/samples.json").read_text());revoked_pid=revoked_samples[0]["pid"]
 try:os.kill(revoked_pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError("revoked child not reaped")
 old=signal.signal(signal.SIGTERM,r.ref.signal_error);timer=threading.Timer(.3,lambda:os.kill(os.getpid(),signal.SIGTERM));timer.start()
 try:
  try:run('signal')
  except InterruptedError:pass
  else:raise AssertionError('signal ignored')
 finally:timer.cancel();signal.signal(signal.SIGTERM,old)
 samples=json.loads((p/'signal/samples.json').read_text());pid=samples[0]['pid']
 try:os.kill(pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError('child not reaped')
print('fake CLI lifecycle/CPU KFD, GPU, ACCEL, missing hook, foreign library, STOP, signal/reap PASS')

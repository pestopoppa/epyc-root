import json,os,pathlib,subprocess,time
D=pathlib.Path(__file__).resolve().parent;out=D/'engineering-stop';stop=D/'STOP';assert not out.exists() and not stop.exists()
cmd=['sudo','-n','chroot','/proc/1/root','/usr/bin/setpriv','--reuid=1000','--regid=1000','--groups=992','/usr/bin/env','-i','PATH=/usr/bin:/bin','CS22_OUT=engineering-stop','/bin/bash',str(D/'launch-engineering.sh'),'--smoke'];start=time.monotonic()
with (D/'ENGINEERING-STOP.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);armed=False
 while p.poll() is None and time.monotonic()-start<295:
  log=out/'server.log'
  if not armed and log.exists() and (out/'EXPOSURE.json').exists() and not (out/'RESULT.json').exists():
   text=log.read_text(errors='replace');lines=[x for x in text.splitlines() if 'processing task' in x]
   if lines:
    (D/'STOP-ACTIVE.json').write_text(json.dumps({'line':lines[-1],'observed_epoch':time.time()})+'\n');fd=os.open(stop,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644);os.close(fd);armed=True
  time.sleep(.005)
 if p.poll() is None:raise RuntimeError('supervisor exceeded wall cap')
 rc=p.wait()
if stop.exists():stop.unlink()
print('rc',rc,'armed',armed,'wall',time.monotonic()-start)
assert armed and rc==75 and json.loads((out/'PARTIAL.json').read_text())['partial']

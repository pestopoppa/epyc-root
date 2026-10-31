import os,subprocess,time,pathlib
D=pathlib.Path(__file__).resolve().parent;out=D/'smoke-cutoff-final2';out.mkdir(exist_ok=False)
cmd=['sudo','-n','--preserve-env=HOME','/usr/bin/chroot','/proc/1/root','/usr/bin/setpriv','--reuid=1000','--regid=1000','--groups=992','/usr/bin/env','FILLER_CPUS=96,97','CS8_SMOKE_DIR='+out.name,str(D/'launch.sh'),'--smoke']
with (D/'smoke-cutoff-final2.log').open('w') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
 deadline=time.monotonic()+90
 while time.monotonic()<deadline and p.poll() is None and not list(out.glob('*.stdout')):time.sleep(.1)
 if p.poll() is not None or not list(out.glob('*.stdout')):raise SystemExit('no native process launched')
 stop=D/'STOP';stop.touch(exist_ok=False)
 try:rc=p.wait(timeout=30)
 finally:stop.unlink()
 print('rc',rc)
 if rc!=75:raise SystemExit(1)

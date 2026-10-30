import os,signal,subprocess,sys
from pathlib import Path
from control_driver import stop_child,output_bytes,OWN_RESERVE,OUTPUT_STOP
r=Path(__file__).parent/('bounds-fixture-'+str(os.getpid()));r.mkdir();(r/'a').write_bytes(b'123');(r/'b').symlink_to(r/'a')
assert output_bytes(r)==3 and OWN_RESERVE==256*1024**2 and OUTPUT_STOP==224*1024**2
script='import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(30)'
p=subprocess.Popen([sys.executable,'-c',script],stdout=subprocess.PIPE,text=True)
try:
 assert p.stdout.readline().strip()=='ready';stop_child(p);assert p.poll() is not None and p.returncode==-signal.SIGKILL
finally:
 if p.poll() is None:p.kill();p.wait(timeout=3)
assert p.poll() is not None
print('output bound accounting and captured child SIGTERM-to-SIGKILL escalation verified')

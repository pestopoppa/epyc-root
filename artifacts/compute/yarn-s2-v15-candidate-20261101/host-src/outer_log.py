"""Bound scheduler stdout without terminating a pregrant poller on log overflow."""
import os,sys,signal,subprocess,select,time
from pathlib import Path
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
import pidfd_custody_v2 as custody,pidfd_subreaper_v3 as subreaper,pf1_graceful
subreaper.enable();stopped=[False]
for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,lambda *_:stopped.__setitem__(0,True))
p=subprocess.Popen(sys.argv[1:],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,close_fds=True);fd,ident=custody.open_child(p.pid);forward=0;limit=256*1024;capture=D/'ws58-launcher.out';signalled=False
try:
 with capture.open('ab',buffering=0) as out:
  while True:
   if stopped[0] and not signalled:
    try:custody.send(fd,signal.SIGTERM)
    except ProcessLookupError:pass
    signalled=True
   if select.select([p.stdout],[],[],.1)[0]:
    data=os.read(p.stdout.fileno(),16384)
    if not data:break
    room=max(0,4*1024**2-os.fstat(out.fileno()).st_size);take=min(room,len(data));out.write(data[:take]);send=min(len(data),max(0,limit-forward-128))
    if send:os.write(1,data[:send]);forward+=send
    if take<len(data) or send<len(data):
     marker=D/'OUTPUT-PAUSE'
     if not marker.exists():marker.write_text('partial output budget pause; native records remain durable; no pregrant poller killed\n')
     if forward<limit:
      note=b'\nOUTPUT_CAP: poller retained; next actual job pauses rc75 with preserved unknown/native files\n';os.write(1,note[:limit-forward]);forward=limit
   elif p.poll() is not None:break
  out.flush();os.fsync(out.fileno())
 p.wait()
finally:
 os.close(fd);pf1_graceful.drain(leader=p)
raise SystemExit(p.returncode)

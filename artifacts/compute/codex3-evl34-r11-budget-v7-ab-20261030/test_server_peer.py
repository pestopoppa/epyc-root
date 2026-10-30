import os,socket,subprocess,sys,time
from pathlib import Path
from server_peer import verify_server,birth
root=Path(__file__).parent/('server-peer-fixture-'+str(os.getpid()));root.mkdir()
script='''import socket,sys,time\ns=socket.socket();s.bind(("127.0.0.1",0));s.listen();print(s.getsockname()[1],flush=True);c,_=s.accept();print("accepted",flush=True);time.sleep(4);c.close();s.close()'''
p=subprocess.Popen([sys.executable,'-c',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 port=int(p.stdout.readline());initial=birth(p.pid);c=socket.socket();c.settimeout(3);c.connect(('127.0.0.1',port));assert p.stdout.readline().strip()=='accepted'
 w=verify_server(c,p.pid,initial);assert w['pid']==p.pid
 try:verify_server(c,p.pid,initial+1)
 except RuntimeError:pass
 else:raise AssertionError('wrong birth accepted')
 c.close()
finally:
 p.terminate();p.wait(timeout=3)
 assert p.poll() is not None
print('synthetic loopback peer verified against captured server PID and birth; wrong identity refused')

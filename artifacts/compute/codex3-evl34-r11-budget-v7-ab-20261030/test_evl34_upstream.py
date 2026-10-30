import os,subprocess,sys,time
from server_peer import birth
from evl34_upstream import Upstream
SCRIPT='''from http.server import HTTPServer,BaseHTTPRequestHandler\nimport time\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*a):pass\n def do_POST(self):\n  n=int(self.headers["Content-Length"]);self.rfile.read(n);self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();time.sleep(.15);self.wfile.write(b"{\\\"fixture\\\":true}");self.wfile.flush()\ns=HTTPServer(("127.0.0.1",0),H);print(s.server_port,flush=True);s.handle_request();s.server_close()'''
def main():
 p=subprocess.Popen([sys.executable,'-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  port=int(p.stdout.readline());ident=birth(p.pid)
  # This is explicitly synthetic, not hardware residency evidence.
  def witness():return {'identity':(p.pid,ident),'cpu_residency_verified':True,'own_pid_rss_bytes':1,'fixture_only':True}
  upstream=Upstream(port,p.pid,ident,time.monotonic()+10,lambda:False,witness)
  status,headers,chunks=upstream('/v1/chat/completions',{'fixture':True})
  assert status==200 and b''.join(chunks)==b'{"fixture":true}'
  evidence=upstream.local.evidence;assert evidence['peer']['pid']==p.pid and evidence['samples'] and evidence['samples'][0][1]['fixture_only']
  p.wait(timeout=3);assert p.returncode==0
  print('restricted producer to captured synthetic loopback server; during-request synthetic witness retained')
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=3)
  assert p.poll() is not None
if __name__=='__main__':main()

"""Full confined REPL to owned loopback server, synthetic fixtures only."""
import os,socket,subprocess,sys,threading,time
from pathlib import Path
from broker_protocol import serve_one,recv,send
from request_policy import RequestPolicy
from native_usage import UsageLedger
from repl_upstream_adapter import REPLUpstream
from evl34_upstream import Upstream
from server_peer import birth
from src.repl_environment.exec_sandbox import wrap,Policy
SCRIPT='''from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nimport json,threading,time\nlock=threading.Lock();counter=0;barrier=threading.Barrier(2,timeout=4)\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*a):pass\n def do_POST(self):\n  global counter\n  n=int(self.headers["Content-Length"]);self.rfile.read(n)\n  with lock:counter+=1;ordinal=counter\n  content="```python\\na = web_search('neutral')\\nb = web_fetch('https://example.org')\\nFINAL(a + b)\\n```"\n  time.sleep(.1);data=json.dumps({'choices':[{'message':{'content':content}}],'usage':{'prompt_tokens':10,'completion_tokens':2}}).encode();self.send_response(200);self.send_header('content-type','application/json');self.end_headers();self.wfile.write(data);self.wfile.flush()\ns=ThreadingHTTPServer(('127.0.0.1',0),H);print(s.server_port,flush=True);s.serve_forever()'''
def main():
 root=Path(__file__).parent/('full-repl-synthetic-'+str(os.getpid()));root.mkdir();(root/'prompt.json').write_text('{"prompt":"fixture question"}')
 server=subprocess.Popen([sys.executable,'-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 pairs=[];threads=[];errors=[]
 try:
  port=int(server.stdout.readline());ident=birth(server.pid)
  def witness():
   if birth(server.pid)!=ident:raise RuntimeError('fixture server changed')
   return {'identity':(server.pid,ident),'cpu_residency_verified':True,'own_pid_rss_bytes':1,'fixture_only':True}
  upstream=Upstream(port,server.pid,ident,time.monotonic()+20,lambda:False,witness);usage=UsageLedger();adapter=REPLUpstream(upstream,usage);policy=RequestPolicy('pinned');pairs=[socket.socketpair() for _ in range(3)];depths=[];evidence=[];lock=threading.Lock()
  def call(path,body):
   result=adapter(path,body)
   with lock:evidence.append(upstream.local.evidence)
   return result
  def admission(req,res):
   with lock:depths.append(req['depth'])
  def broker(sock):
   try:
    while True:
     req=recv(sock)
     if req['path'].startswith('/tool/'):send(sock,{'tool_result':'fixture '+req['path'].rsplit('/',1)[1]})
     else:serve_one(sock,policy,call,admission,req)
   except EOFError:pass
   except Exception as exc:errors.append(exc);print('BROKER FAILURE',repr(exc),flush=True);sock.close()
  threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
  for t in threads:t.start()
  fds=[b.fileno() for a,b in pairs];cmd=[sys.executable,str(Path(__file__).parent/'repl_live_entry.py'),str(root),','.join(map(str,fds))]
  cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)]);env=os.environ.copy();env.update(extra);env['PYTHONPATH']='/workspace/repos/epyc-orchestrator'
  try:child=subprocess.run(cmd,pass_fds=fds,capture_output=True,text=True,env=env,timeout=7)
  except subprocess.TimeoutExpired as exc:
   print('TIMEOUT stdout',repr(exc.stdout),'stderr',repr(exc.stderr),'broker errors',errors,'depths',depths,'reserved',policy.budget.reserved,flush=True)
   raise RuntimeError('fixture timeout')
  for a,b in pairs:b.close()
  for t in threads:t.join(4)
  assert child.returncode==0,(child.stdout,child.stderr,errors)
  import json
  assert json.loads((root/'response.json').read_text())['answer']=='fixture searchfixture visit'
  assert not errors and all(not t.is_alive() for t in threads) and sorted(depths)==[0] and len(evidence)==1,(errors,depths,len(evidence))
  assert all(e['peer']['pid']==server.pid and e['samples'] for e in evidence)
  assert policy.budget.reserved==2048 and usage.totals()=={'prompt_tokens':10,'completion_tokens':2}
  print('contained REPL -> concurrent restricted producers -> captured synthetic server, usage/depth/custody controls passed; witness synthetic')
 finally:
  for a,b in pairs:a.close();b.close()
  if server.poll() is None:server.terminate();server.wait(timeout=3)
  assert server.poll() is not None
if __name__=='__main__':main()

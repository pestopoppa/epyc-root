"""Full confined REPL to owned loopback server, synthetic fixtures only."""
import os,socket,subprocess,sys,threading,time
from pathlib import Path
from broker_protocol import serve_one
from request_policy import RequestPolicy
from native_usage import UsageLedger
from repl_upstream_adapter import REPLUpstream
from evl34_upstream import Upstream
from server_peer import birth
from src.repl_environment.exec_sandbox import wrap,Policy
SCRIPT='''from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nimport json,threading,time\nlock=threading.Lock();counter=0;barrier=threading.Barrier(2,timeout=4)\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*a):pass\n def do_POST(self):\n  global counter\n  n=int(self.headers["Content-Length"]);self.rfile.read(n)\n  with lock:counter+=1;ordinal=counter\n  if ordinal==1:content="```python\\nresults = llm_batch(['fixture one','fixture two'])\\nFINAL(results[0])\\n```"\n  else:barrier.wait();content="fixture answer"\n  time.sleep(.1);data=json.dumps({'choices':[{'message':{'content':content}}],'usage':{'prompt_tokens':10,'completion_tokens':2}}).encode();self.send_response(200);self.send_header('content-type','application/json');self.end_headers();self.wfile.write(data);self.wfile.flush()\ns=ThreadingHTTPServer(('127.0.0.1',0),H);print(s.server_port,flush=True);s.serve_forever()'''
def main():
 root=Path(__file__).parent/('full-repl-synthetic-'+str(os.getpid()));root.mkdir()
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
    while True:serve_one(sock,policy,call,admission)
   except EOFError:pass
   except Exception as exc:errors.append(exc);print('BROKER FAILURE',repr(exc),flush=True);sock.close()
  threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
  for t in threads:t.start()
  fds=[b.fileno() for a,b in pairs];cmd=[sys.executable,str(Path(__file__).parent/'repl_native_entry_fixture.py'),str(root),','.join(map(str,fds))]
  cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)]);env=os.environ.copy();env.update(extra);env['PYTHONPATH']='/mnt/micron/codex3-lanes/orchestrator:/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages'
  child=subprocess.run(cmd,pass_fds=fds,capture_output=True,text=True,env=env,timeout=15)
  for a,b in pairs:b.close()
  for t in threads:t.join(4)
  assert child.returncode==0,(child.stdout,child.stderr,errors)
  assert not errors and all(not t.is_alive() for t in threads) and sorted(depths)==[0,1,1] and len(evidence)==3,(errors,depths,len(evidence))
  assert all(e['peer']['pid']==server.pid and e['samples'] for e in evidence)
  assert policy.budget.reserved==12288 and policy._root==1 and policy._children==2 and usage.totals()=={'prompt_tokens':30,'completion_tokens':6}
  print('contained REPL -> concurrent restricted producers -> captured synthetic server, usage/depth/custody controls passed; witness synthetic')
 finally:
  for a,b in pairs:a.close();b.close()
  if server.poll() is None:server.terminate();server.wait(timeout=3)
  assert server.poll() is not None
if __name__=='__main__':main()

"""Full confined ReDel to owned loopback server, synthetic fixtures only."""
import os,socket,subprocess,sys,threading,time
from pathlib import Path
from stream_broker import serve_stream
from request_policy import RequestPolicy
from native_usage import UsageLedger
from evl34_upstream import Upstream
from server_peer import birth
from src.repl_environment.exec_sandbox import wrap,Policy
SCRIPT='''from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nimport json,threading,time\nlock=threading.Lock();roots=0;barrier=threading.Barrier(2,timeout=4)\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*a):pass\n def do_POST(self):\n  global roots\n  n=int(self.headers['Content-Length']);body=json.loads(self.rfile.read(n));stream=body.get('stream',False)\n  if stream:\n   barrier.wait();common={'id':'fixture','created':0,'model':'pinned','object':'chat.completion.chunk'}\n   chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture helper answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}]\n   wire=(''.join('data: '+json.dumps(x)+'\\n\\n' for x in chunks)+'data: [DONE]\\n\\n').encode();content='text/event-stream'\n  else:\n   with lock:roots+=1;ordinal=roots\n   if ordinal==1:msg={'role':'assistant','content':None,'tool_calls':[{'id':f'call{i}','type':'function','function':{'name':'delegate','arguments':json.dumps({'instructions':f'fixture helper {i}'})}} for i in (1,2)]};finish='tool_calls'\n   elif ordinal==2:msg={'role':'assistant','content':None,'tool_calls':[{'id':'wait','type':'function','function':{'name':'wait','arguments':json.dumps({'until':'all'})}}]};finish='tool_calls'\n   else:msg={'role':'assistant','content':'fixture final'};finish='stop'\n   wire=json.dumps({'id':'fixture','created':0,'model':'pinned','object':'chat.completion','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}).encode();content='application/json'\n  time.sleep(.1);self.send_response(200);self.send_header('content-type',content);self.end_headers();self.wfile.write(wire);self.wfile.flush()\ns=ThreadingHTTPServer(('127.0.0.1',0),H);print(s.server_port,flush=True);s.serve_forever()'''
def main():
 root=Path(__file__).parent/('full-redel-synthetic-'+str(os.getpid()));root.mkdir();(root/'prompt.json').write_text('{"prompt":"fixture question"}');server=subprocess.Popen([sys.executable,'-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True);pairs=[];threads=[];errors=[]
 try:
  port=int(server.stdout.readline());ident=birth(server.pid)
  def witness():
   if birth(server.pid)!=ident:raise RuntimeError('fixture server changed')
   return {'identity':(server.pid,ident),'cpu_residency_verified':True,'own_pid_rss_bytes':1,'fixture_only':True}
  upstream=Upstream(port,server.pid,ident,time.monotonic()+20,lambda:False,witness);usage=UsageLedger();policy=RequestPolicy('pinned');pairs=[socket.socketpair() for _ in range(3)];evidence=[];lock=threading.Lock()
  def broker(sock):
   try:
    while True:
     serve_stream(sock,policy,upstream,usage)
     with lock:evidence.append(upstream.local.evidence)
   except EOFError:pass
   except Exception as exc:errors.append(exc);sock.close()
  threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
  for t in threads:t.start()
  fds=[b.fileno() for a,b in pairs];cmd=['/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/venv/bin/python',str(Path(__file__).parent/'redel_live_entry.py'),str(root),','.join(map(str,fds))]
  cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)]);env=os.environ.copy();env.update(extra);env['TIKTOKEN_CACHE_DIR']='/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/tiktoken-cache'
  child=subprocess.run(cmd,pass_fds=fds,capture_output=True,text=True,env=env,timeout=15)
  for a,b in pairs:b.close()
  for t in threads:t.join(4)
  assert child.returncode==0,(child.stdout,child.stderr,errors)
  import json
  assert any(e.get('type')=='kani_delegated' for e in json.loads((root/'events.json').read_text()))
  assert not errors and all(not t.is_alive() for t in threads) and len(evidence)==5,(errors,len(evidence))
  assert all(e['peer']['pid']==server.pid and e['samples'] for e in evidence)
  assert policy.budget.reserved==5120 and usage.totals()=={'prompt_tokens':50,'completion_tokens':10},usage.totals()
  print('contained ReDel -> concurrent restricted producers -> captured synthetic server, incremental SSE, usage and depth controls passed; witness synthetic')
 finally:
  for a,b in pairs:a.close();b.close()
  if server.poll() is None:server.terminate();server.wait(timeout=3)
  assert server.poll() is not None
if __name__=='__main__':main()

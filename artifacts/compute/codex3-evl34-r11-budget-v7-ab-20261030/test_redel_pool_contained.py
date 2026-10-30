import json,os,socket,threading,subprocess,sys
from pathlib import Path
from stream_broker import serve_stream
from request_policy import RequestPolicy
from src.repl_environment.exec_sandbox import wrap,Policy
root=Path(__file__).parent/'redel-pool-contained';root.mkdir();pairs=[socket.socketpair() for _ in range(3)];policy=RequestPolicy('pinned');seen=[];errors=[];roots=0;guard=threading.Lock();barrier=threading.Barrier(2,timeout=3)
def upstream(path,body):
 global roots
 with guard:
  seen.append(body)
  if not body.get('stream',False):roots+=1;ordinal=roots
 if body.get('stream',False):
  barrier.wait();common={'id':'fixture','created':0,'model':'pinned','object':'chat.completion.chunk'}
  chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture helper answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}]
  wire=(''.join('data: '+json.dumps(x)+'\n\n' for x in chunks)+'data: [DONE]\n\n').encode()
  return 200,{'content-type':'text/event-stream'},[wire]
 if ordinal==1:msg={'role':'assistant','content':None,'tool_calls':[{'id':f'call{i}','type':'function','function':{'name':'delegate','arguments':json.dumps({'instructions':f'fixture helper {i}'})}} for i in (1,2)]};finish='tool_calls'
 elif ordinal==2:msg={'role':'assistant','content':None,'tool_calls':[{'id':'wait','type':'function','function':{'name':'wait','arguments':json.dumps({'until':'all'})}}]};finish='tool_calls'
 else:msg={'role':'assistant','content':'fixture final'};finish='stop'
 data={'id':'fixture','created':0,'model':'pinned','object':'chat.completion','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}
 return 200,{'content-type':'application/json'},[json.dumps(data).encode()]
def broker(sock):
 try:
  while True:serve_stream(sock,policy,upstream)
 except EOFError:pass
 except Exception as e:errors.append(e)
threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
for t in threads:t.start()
fds=[b.fileno() for a,b in pairs]
cmd=['/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/venv/bin/python',str(Path(__file__).parent/'redel_pool_child_fixture.py'),str(root),','.join(map(str,fds))]
cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)]);env=os.environ.copy();env.update(extra)
p=subprocess.run(cmd,pass_fds=fds,capture_output=True,text=True,env=env,timeout=20)
for a,b in pairs:b.close()
for t in threads:t.join(3)
for a,b in pairs:a.close()
assert p.returncode==0,(p.stdout,p.stderr,errors)
assert not errors and all(not t.is_alive() for t in threads) and len(seen)==5 and policy.budget.reserved==5120,(errors,len(seen))
print('contained actual ReDel scripted parallel delegation: two streamed helpers overlapped, depths 0/1/1')

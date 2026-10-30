import json,os,socket,threading,subprocess,sys
from pathlib import Path
from stream_broker import serve_stream
from request_policy import RequestPolicy
from src.repl_environment.exec_sandbox import wrap,Policy
a,b=socket.socketpair();policy=RequestPolicy('pinned');seen=[];errors=[];roots=0
def upstream(path,body):
 global roots
 seen.append(body);stream=body.get('stream',False)
 common={'id':'fixture','created':0,'model':'pinned'}
 if stream:
  common['object']='chat.completion.chunk'
  chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture helper answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}]
  wire=(''.join('data: '+json.dumps(x)+'\n\n' for x in chunks)+'data: [DONE]\n\n').encode()
  return 200,{'content-type':'text/event-stream'},[wire]
 roots+=1
 if roots==1:msg={'role':'assistant','content':None,'tool_calls':[{'id':'call1','type':'function','function':{'name':'delegate','arguments':json.dumps({'instructions':'fixture helper task'})}}]};finish='tool_calls'
 elif roots==2:msg={'role':'assistant','content':None,'tool_calls':[{'id':'call2','type':'function','function':{'name':'wait','arguments':json.dumps({'until':'all'})}}]};finish='tool_calls'
 else:msg={'role':'assistant','content':'fixture final'};finish='stop'
 data=common|{'object':'chat.completion','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}
 return 200,{'content-type':'application/json'},[json.dumps(data).encode()]
def broker():
 try:
  for _ in range(4):serve_stream(a,policy,upstream)
 except Exception as exc:errors.append(exc);print('BROKER REFUSAL',repr(exc),flush=True);a.close()
t=threading.Thread(target=broker);t.start()
root=Path(os.environ['EVL34_LOG_DIR']);cmd=['/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/venv/bin/python',str(Path(__file__).parent/'redel_child_fixture.py'),str(root),str(b.fileno())]
cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)])
env=os.environ.copy();env.update(extra)
p=subprocess.run(cmd,pass_fds=(b.fileno(),),capture_output=True,text=True,env=env,timeout=20)
print(p.stdout);print(p.stderr)
assert p.returncode==0,(p.returncode,errors)
t.join(3);assert not t.is_alive() and not errors and len(seen)==4 and policy.budget.reserved==4096,(errors,len(seen),policy.budget.reserved)
a.close();b.close();print('actual ReDel/Kani root + streamed delegate through incremental broker; synthetic scripted upstream depth 0/1')

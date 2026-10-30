import os,socket,subprocess,sys,threading
from pathlib import Path
from broker_protocol import serve_one
from request_policy import RequestPolicy
from src.repl_environment.exec_sandbox import wrap,Policy,credential_paths
root=Path(__file__).parent/'whole-repl-fenced-fixture-v3';root.mkdir()
sentinel=root.parent/'credential-sentinel-v3';sentinel.write_text('fixture secret')
a,b=socket.socketpair();policy=RequestPolicy('pinned');errors=[];seen=[];depths=[]
def upstream(path,body):
 seen.append(body)
 return {'choices':[{'message':{'content': ("```python\nresult = llm_call('fixture helper question')\nFINAL(result)\n```" if len(seen)==1 else 'fixture answer')}}]}
def broker():
 try:
  for _ in range(2):serve_one(a,policy,upstream,lambda req,res:depths.append(req['depth']))
 except Exception as e:errors.append(e)
t=threading.Thread(target=broker);t.start();env=os.environ.copy();env['PYTHONPATH']='/workspace/repos/epyc-orchestrator';env['EVL34_SENTINEL']=str(sentinel);env['EVL34_PARENT_PID']=str(os.getpid());env['EVL34_OUTSIDE_WRITE']=str(root.parent/'outside-write-v3')
cmd=[sys.executable,str(Path(__file__).parent/'repl_child_fixture.py'),str(root),str(b.fileno())]
cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)],deny_paths=credential_paths()+[str(sentinel)]);env.update(extra)
p=subprocess.run(cmd,pass_fds=(b.fileno(),),env=env,capture_output=True,text=True,timeout=30)
b.close();a.close();t.join(2)
assert p.returncode==0,(p.stdout,p.stderr,errors)
assert not errors and not t.is_alive() and len(seen)==2 and policy.budget.reserved==2048 and depths==[0,1],(errors,len(seen))
print(p.stdout.strip(), 'observed depths', depths)

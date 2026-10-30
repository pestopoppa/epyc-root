import os,socket,subprocess,sys,threading
from pathlib import Path
from broker_protocol import serve_one
from request_policy import RequestPolicy
root=Path(__file__).parent/'whole-repl-batch-fixture';root.mkdir()
a,b=socket.socketpair();policy=RequestPolicy('pinned');errors=[];seen=[];depths=[]
def upstream(path,body):
 seen.append(body)
 return {'choices':[{'message':{'content': ("```python\nresults = llm_batch(['fixture one', 'fixture two'])\nFINAL(results[0])\n```" if len(seen)==1 else 'fixture answer')}}]}
def broker():
 try:
  for _ in range(3):serve_one(a,policy,upstream,lambda req,res:depths.append(req['depth']))
 except Exception as e:errors.append(e)
t=threading.Thread(target=broker);t.start();env=os.environ.copy();env['PYTHONPATH']='/workspace/repos/epyc-orchestrator'
p=subprocess.run([sys.executable,str(Path(__file__).parent/'repl_child_fixture.py'),str(root),str(b.fileno())],pass_fds=(b.fileno(),),env=env,capture_output=True,text=True,timeout=30)
b.close();a.close();t.join(2)
assert p.returncode==0,(p.stdout,p.stderr,errors)
assert not errors and not t.is_alive() and len(seen)==3 and policy.budget.reserved==3072 and depths==[0,1,1],(errors,len(seen))
print(p.stdout.strip(), 'observed depths', depths)

import os,socket,subprocess,sys,threading
from pathlib import Path
from broker_protocol import serve_one
from request_policy import RequestPolicy
from src.repl_environment.exec_sandbox import wrap,Policy
root=Path(__file__).parent/'repl-pool-contained';root.mkdir()
pairs=[socket.socketpair() for _ in range(2)];policy=RequestPolicy('pinned');barrier=threading.Barrier(2,timeout=3);seen=[];errors=[];guard=threading.Lock();depths=[]
def upstream(path,body):
 with guard:
  seen.append(body);ordinal=len(seen)
 if ordinal==1:content="```python\nresults = llm_batch(['fixture one','fixture two'])\nFINAL(results[0])\n```"
 else:barrier.wait();content='fixture answer'
 return {'choices':[{'message':{'content':content}}]}
def admit(req,res):
 with guard:depths.append(req['depth'])
def broker(sock):
 try:
  while True:serve_one(sock,policy,upstream,admit)
 except EOFError:pass
 except Exception as e:errors.append(e)
threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
for t in threads:t.start()
fds=[b.fileno() for a,b in pairs]
cmd=[sys.executable,str(Path(__file__).parent/'repl_pool_child_fixture.py'),str(root),','.join(map(str,fds))]
cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)]);env=os.environ.copy();env.update(extra);env['PYTHONPATH']='/workspace/repos/epyc-orchestrator'
p=subprocess.run(cmd,pass_fds=fds,capture_output=True,text=True,env=env,timeout=20)
for a,b in pairs:b.close()
for t in threads:t.join(3)
for a,b in pairs:a.close()
assert p.returncode==0,(p.stdout,p.stderr,errors)
assert not errors and all(not t.is_alive() for t in threads) and len(seen)==3 and sorted(depths)==[0,1,1] and policy.budget.reserved==3072,(errors,depths,len(seen))
print('contained actual REPL scripted parallel batch: two broker calls overlapped, reported depths 0/1/1')

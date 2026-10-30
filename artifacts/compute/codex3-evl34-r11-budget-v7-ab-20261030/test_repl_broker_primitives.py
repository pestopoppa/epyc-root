import socket,threading
from request_policy import RequestPolicy
from broker_protocol import serve_one
from repl_broker_primitives import BrokerPrimitives
client,server=socket.socketpair();policy=RequestPolicy('pinned');seen=[];errors=[]
def upstream(path,body):
 seen.append(body)
 return {'choices':[{'message':{'content':'fixture answer'}}]}
def parent():
 try:
  for _ in range(3):serve_one(server,policy,upstream)
 except Exception as e:errors.append(e)
t=threading.Thread(target=parent);t.start()
p=BrokerPrimitives(client,'pinned')
assert p.llm_call('one',role='worker')=='fixture answer'
assert p.llm_batch(['two','three'],role='worker')==['fixture answer','fixture answer']
t.join(2);assert not t.is_alive() and not errors and len(seen)==3 and policy.budget.reserved==3072,(errors,seen)
assert all(x['max_tokens']==1024 and x['temperature']==0 and x['seed']==42 for x in seen)
client.close();server.close()
print('production primitive single and batch paths reached shared broker with synthetic responses; transport is private replacement')

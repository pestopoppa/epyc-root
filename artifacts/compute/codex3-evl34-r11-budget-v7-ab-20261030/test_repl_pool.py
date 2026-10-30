import socket,threading
from channel_pool import ChannelPool
from repl_pool_primitives import PoolPrimitives
from request_policy import RequestPolicy
from broker_protocol import serve_one
pairs=[socket.socketpair() for _ in range(2)];policy=RequestPolicy('pinned');barrier=threading.Barrier(2,timeout=3);errors=[]
def upstream(path,body):
 barrier.wait()
 return {'choices':[{'message':{'content':'fixture answer'}}]}
def worker(sock):
 try:serve_one(sock,policy,upstream)
 except Exception as e:errors.append(e)
threads=[threading.Thread(target=worker,args=(a,)) for a,b in pairs]
for t in threads:t.start()
p=PoolPrimitives(ChannelPool([b for a,b in pairs]),'pinned')
p.config.batch_parallelism=2
p._get_role_limit=lambda _:2
assert p.llm_batch(['one','two'],role='worker')==['fixture answer','fixture answer']
for t in threads:t.join(3)
assert not errors and all(not t.is_alive() for t in threads) and policy.budget.reserved==2048,errors
for a,b in pairs:a.close();b.close()
print('actual primitive llm_batch reaches two concurrent synthetic upstream calls; shared budget')

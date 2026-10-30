import asyncio,socket,threading
import httpx
from stream_pool_transport import PooledStreamingTransport
from stream_broker import serve_stream
from request_policy import RequestPolicy
pairs=[socket.socketpair() for _ in range(2)];policy=RequestPolicy('pinned');barrier=threading.Barrier(2,timeout=3);errors=[]
def upstream(path,body):
 barrier.wait()
 return 200,{'content-type':'text/plain'},[b'fixture']
def broker(sock):
 try:serve_stream(sock,policy,upstream)
 except Exception as e:errors.append(e)
threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
for t in threads:t.start()
async def main():
 async with httpx.AsyncClient(transport=PooledStreamingTransport([b for a,b in pairs]),base_url='http://private.invalid') as client:
  async def call():return await client.post('/v1/chat/completions',json={'model':'pinned','temperature':0,'seed':42,'max_tokens':1024,'messages':[{'role':'user','content':'fixture'}]})
  replies=await asyncio.gather(call(),call());assert [r.text for r in replies]==['fixture','fixture']
asyncio.run(main())
for t in threads:t.join(3)
assert not errors and all(not t.is_alive() for t in threads) and policy.budget.reserved==2048,errors
for a,b in pairs:a.close();b.close()
print('two concurrent streaming HTTP requests reach synthetic upstream; shared budget')

import asyncio,base64,socket,threading
import httpx
from broker_protocol import serve_one
from request_policy import RequestPolicy
from redel_transport import SocketTransport
a,b=socket.socketpair();seen=[];errors=[];policy=RequestPolicy('pinned')
def upstream(path,body):
 seen.append(body)
 return {'status':200,'headers':{'content-type':'application/json'},'body_b64':base64.b64encode(b'{"fixture":true}').decode()}
def broker():
 try:serve_one(a,policy,upstream)
 except Exception as e:errors.append(e)
t=threading.Thread(target=broker);t.start()
async def main():
 async with httpx.AsyncClient(transport=SocketTransport(b),base_url='http://private.invalid') as client:
  response=await client.post('/v1/chat/completions',json={'model':'pinned','temperature':0,'seed':42,'max_tokens':1024,'messages':[{'role':'user','content':'fixture'}]})
  assert response.json()=={'fixture':True}
asyncio.run(main());t.join(2);assert not t.is_alive() and not errors and len(seen)==1 and policy.budget.reserved==1024,(errors,seen)
a.close();b.close()
print('private async httpx transport and broker exchange synthetic response')

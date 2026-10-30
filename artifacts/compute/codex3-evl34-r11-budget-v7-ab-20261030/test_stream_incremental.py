import asyncio,socket,threading
import httpx
from stream_broker import serve_stream
from stream_transport import StreamingTransport
from request_policy import RequestPolicy
a,b=socket.socketpair();permit=threading.Event();errors=[]
def upstream(path,body):
 def chunks():
  yield b'first'
  if not permit.wait(2):raise RuntimeError('client did not receive first chunk before producer resumed')
  yield b'second'
 return 200,{'content-type':'text/plain'},chunks()
def run():
 try:serve_stream(a,RequestPolicy('pinned'),upstream)
 except Exception as e:errors.append(e)
t=threading.Thread(target=run);t.start()
async def main():
 async with httpx.AsyncClient(transport=StreamingTransport(b),base_url='http://private.invalid') as client:
  async with client.stream('POST','/v1/chat/completions',json={'model':'pinned','seed':42,'temperature':0,'max_tokens':1024,'messages':[{'role':'user','content':'fixture'}]}) as response:
   data=[]
   async for chunk in response.aiter_bytes():
    data.append(chunk)
    if chunk==b'first':permit.set()
   assert data==[b'first',b'second'],data
asyncio.run(main());t.join(3);assert not t.is_alive() and not errors,errors
a.close();b.close();print('incremental delivery proven: producer waited for client first-chunk receipt')

import asyncio,socket,threading
import httpx
from stream_broker import serve_stream
from stream_transport import StreamingTransport
from request_policy import RequestPolicy
a,b=socket.socketpair();errors=[]
def upstream(path,body):
 def chunks():
  yield b'partial'
  raise TimeoutError('scripted cutoff')
 return 200,{'content-type':'text/plain'},chunks()
def run():
 try:serve_stream(a,RequestPolicy('pinned'),upstream)
 except TimeoutError:pass
 except Exception as e:errors.append(e)
t=threading.Thread(target=run);t.start()
async def main():
 async with httpx.AsyncClient(transport=StreamingTransport(b),base_url='http://private.invalid') as client:
  try:
   async with client.stream('POST','/v1/chat/completions',json={'model':'pinned','seed':42,'temperature':0,'max_tokens':1024,'messages':[{'role':'user','content':'fixture'}]}) as response:
    async for _ in response.aiter_bytes():pass
  except ValueError:pass
  else:raise AssertionError('partial stream presented as complete')
asyncio.run(main());t.join(3);assert not t.is_alive() and not errors,errors
a.close();b.close();print('scripted upstream cutoff is refused, not completed')

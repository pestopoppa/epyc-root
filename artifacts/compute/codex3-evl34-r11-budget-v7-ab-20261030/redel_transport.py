"""Private Kani httpx-to-socketpair prototype; responses buffered and bounded.

Buffers streaming responses, so it is not suitable for a streaming wall-time
claim. It is not wired to a real upstream or admitted for model inference.
"""
import asyncio,base64,json
import httpx
from broker_protocol import send,recv
class SocketTransport(httpx.AsyncBaseTransport):
 def __init__(self,sock):self.sock=sock;self.lock=asyncio.Lock()
 async def handle_async_request(self,request):
  if request.method!='POST':raise ValueError('only POST supported')
  body=json.loads(await request.aread())
  async with self.lock:
   def exchange():
    send(self.sock,{'path':request.url.path,'body':body})
    return recv(self.sock)
   reply=await asyncio.to_thread(exchange)
  wire=reply['response'];status=wire['status'];content=base64.b64decode(wire['body_b64'],validate=True)
  if len(content)>2*1024*1024:raise ValueError('response too large')
  return httpx.Response(status_code=status,headers=wire['headers'],content=content,request=request)

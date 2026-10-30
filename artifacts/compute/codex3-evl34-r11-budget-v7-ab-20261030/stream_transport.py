"""HTTPX incremental streaming over one task-private socketpair."""
import asyncio,base64,socket
import httpx
from broker_protocol import send,recv
from stream_broker import MAX_TOTAL,MAX_CHUNK

class Body(httpx.AsyncByteStream):
 def __init__(self,sock,lock):self.sock=sock;self.lock=lock;self.closed=False;self.complete=False;self.total=0
 def _accept(self,item):
  if item.get('type')=='done':
   if item.get('total')!=self.total:raise ValueError('length mismatch')
   self.complete=True;return None
  if item.get('type')!='data':raise ValueError('incomplete stream')
  part=base64.b64decode(item['data'],validate=True);self.total+=len(part)
  if len(part)>MAX_CHUNK or self.total>MAX_TOTAL:raise ValueError('stream exceeds cap')
  return part
 async def __aiter__(self):
  try:
   while not self.complete:
    part=self._accept(await asyncio.to_thread(recv,self.sock))
    if part is not None:yield part
  except GeneratorExit:
   raise
  except BaseException:
   try:self.sock.shutdown(socket.SHUT_RDWR)
   except OSError:pass
   self.sock.close()
   raise
  finally:await self.aclose()
 async def aclose(self):
  if self.closed:return
  self.closed=True
  try:
   if not self.complete and self.sock.fileno()>=0:
    async def drain():
     while not self.complete:self._accept(await asyncio.to_thread(recv,self.sock))
    await asyncio.wait_for(drain(),60)
  finally:
   if not self.complete:
    try:self.sock.shutdown(socket.SHUT_RDWR)
    except OSError:pass
    self.sock.close()
   self.lock.release()
class StreamingTransport(httpx.AsyncBaseTransport):
 def __init__(self,sock):self.sock=sock;self.lock=asyncio.Lock()
 async def handle_async_request(self,request):
  if request.method!='POST':raise ValueError('only POST supported')
  body=json.loads(await request.aread());await self.lock.acquire()
  try:
   await asyncio.to_thread(send,self.sock,{'path':request.url.path,'body':body})
   head=await asyncio.to_thread(recv,self.sock)
   if head.get('type')!='headers':raise ValueError('bad response header')
   return httpx.Response(head['status'],headers=head['headers'],stream=Body(self.sock,self.lock),request=request)
  except BaseException:
   self.lock.release();raise
import json

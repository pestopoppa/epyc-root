"""Per-request channels for private incremental ReDel transport."""
import asyncio,json,sys,time
import httpx
from broker_protocol import send,recv
from stream_transport import Body
class LeaseQueue(asyncio.Queue):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.event_count=0
 def event(self,action):
  if self.event_count<256:
   self.event_count+=1;print(json.dumps({'event':'channel_lease','action':action,'available':self.qsize(),'monotonic':time.monotonic()}),file=sys.stderr,flush=True)
class ReturnChannel:
 def __init__(self,queue,sock):self.queue=queue;self.sock=sock
 def release(self):
  if self.sock.fileno()>=0:self.queue.put_nowait(self.sock);self.queue.event('return')
  else:self.queue.event('poison')
class PooledStreamingTransport(httpx.AsyncBaseTransport):
 def __init__(self,sockets):
  sockets=list(sockets)
  if not sockets or len({s.fileno() for s in sockets})!=len(sockets) or any(s.fileno()<0 for s in sockets):raise ValueError('distinct open channels required')
  self.q=LeaseQueue(maxsize=len(sockets))
  for sock in sockets:self.q.put_nowait(sock)
 async def handle_async_request(self,request):
  if request.method!='POST':raise ValueError('only POST supported')
  body=json.loads(await request.aread());sock=await asyncio.wait_for(self.q.get(),60);self.q.event('acquire_model')
  try:
   await asyncio.to_thread(send,sock,{'path':request.url.path,'body':body})
   head=await asyncio.to_thread(recv,sock)
   if head.get('type')!='headers':raise ValueError('bad response header')
   return httpx.Response(head['status'],headers=head['headers'],stream=Body(sock,ReturnChannel(self.q,sock)),request=request)
  except BaseException:
   sock.close();self.q.event('poison');raise

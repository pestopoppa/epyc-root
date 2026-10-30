"""Actual ReDel/Kani in restricted child, scripted broker responses only."""
import asyncio,os,socket,sys
from pathlib import Path
import httpx
from openai import AsyncOpenAI
from kani.engines.openai import OpenAIEngine
from redel import ReDel
from redel_budget import ReDelBudgetMixin
from stream_pool_transport import PooledStreamingTransport
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from landlock_no_delete import install
from no_network import install as block_network
class Tokenizer:
 def encode(self,text,*a,**kw):return list(text.encode())
class Engine(ReDelBudgetMixin,OpenAIEngine):pass
class SafeClose(ReDel):
 async def _dispatch_task(self):
  while True:
   event=await self.event_queue.get()
   try:await asyncio.gather(*(cb(event) for cb in self.listeners),return_exceptions=True)
   finally:self.event_queue.task_done()
root=Path(sys.argv[1]);socks=[socket.socket(fileno=int(fd)) for fd in sys.argv[2].split(',')];loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
install(root);block_network(loop._csock.fileno())
async def main():
 http=httpx.AsyncClient(transport=PooledStreamingTransport(socks));client=AsyncOpenAI(api_key='fixture',base_url='http://private.invalid/v1',http_client=http,max_retries=0)
 engine=Engine(client=client,model='pinned',max_context_size=8192,tokenizer=Tokenizer());engine.init_budget()
 ai=SafeClose(root_engine=engine,delegate_engine=engine,title='fixture',max_delegation_depth=1,log_dir=root/'redel-log')
 try:
  events=[x async for x in ai.query('fixture question')]
  assert sorted(x.depth for x in events if type(x).__name__=='KaniSpawn')==[0,1,1]
  assert any(type(x).__name__=='KaniDelegated' for x in events) and engine.evl34_budget.reserved==5120
 finally:
  await ai.close()
  if ai.dispatch_task:
   try:await ai.dispatch_task
   except asyncio.CancelledError:pass
  await client.close()
loop.run_until_complete(main());loop.close();print('actual ReDel child constrained and scripted depth 0/1')

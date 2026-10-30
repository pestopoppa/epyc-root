"""Pinned ReDel with fixed-model parent broker and incremental streams."""
import asyncio,json,os,socket,sys
from pathlib import Path
import httpx
from openai import AsyncOpenAI
from kani.engines.openai import OpenAIEngine
from redel import ReDel
from safe_delegate_wait import SafeDelegateWait
from redel.kanis import ReDelKani
from child_call_cap import install as install_child_cap
from redel_budget import ReDelBudgetMixin
from redel_browse import SearchAndVisit
from stream_pool_transport import PooledStreamingTransport
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from landlock_no_delete import install
from no_network import install as block_network
class Engine(ReDelBudgetMixin,OpenAIEngine):pass
class SafeClose(ReDel):
 async def _dispatch_task(self):
  while True:
   event=await self.event_queue.get()
   try:await asyncio.gather(*(cb(event) for cb in self.listeners),return_exceptions=True)
   finally:self.event_queue.task_done()
root=Path(sys.argv[1]).resolve(strict=True);socks=[socket.socket(fileno=int(fd)) for fd in sys.argv[2].split(',')];public=json.loads((root/'prompt.json').read_bytes())
if set(public)!={'prompt'} or not isinstance(public['prompt'],str):raise ValueError('prompt-only input required')
if len(sys.argv)!=3 or len(socks)!=3:raise ValueError('invalid entry args')
loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);install(root);block_network(loop._csock.fileno());install_child_cap(ReDelKani,16)
async def main():
 transport=PooledStreamingTransport(socks);http=httpx.AsyncClient(transport=transport);client=AsyncOpenAI(api_key='local',base_url='http://private.invalid/v1',http_client=http,max_retries=0)
 engine=Engine(client=client,model='pinned',max_context_size=8192);engine.init_budget(root)
 ai=SafeClose(root_engine=engine,delegate_engine=engine,title='EVL44 control',max_delegation_depth=0,delegation_scheme=SafeDelegateWait,log_dir=root/'redel-log',tool_configs={SearchAndVisit:{'always_include':True,'kwargs':{'queue':transport.q}}})
 try:
  events=[]
  async for event in ai.query(public['prompt']):
   events.append(event.model_dump(mode='json'))
   if len(json.dumps(events).encode())>2*1024*1024:raise ValueError('events exceed cap')
  with (root/'events.json').open('xb') as f:f.write(json.dumps(events,ensure_ascii=False,allow_nan=False).encode());f.flush();os.fsync(f.fileno())
 finally:
  await ai.close()
  if ai.dispatch_task:
   try:await ai.dispatch_task
   except asyncio.CancelledError:pass
  await client.close()
loop.run_until_complete(main());loop.close()

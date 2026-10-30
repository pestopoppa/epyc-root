import asyncio,os
from pathlib import Path
from kani import ChatMessage
from kani.engines.base import BaseEngine,Completion
from redel import ReDel
from redel_budget import ReDelBudgetMixin
class Scripted(BaseEngine):
 max_context_size=8192
 def prompt_len(self,messages,functions=None,**kwargs):return 10
 async def predict(self,messages,functions=None,**kwargs):return Completion(ChatMessage.assistant('fixture answer'),10,2)
 async def stream(self,messages,functions=None,**kwargs):yield Completion(ChatMessage.assistant('fixture answer'),10,2)
class Engine(ReDelBudgetMixin,Scripted):pass
class SafeClose(ReDel):
 async def _dispatch_task(self):
  while True:
   event=await self.event_queue.get()
   try:await asyncio.gather(*(cb(event) for cb in self.listeners),return_exceptions=True)
   finally:self.event_queue.task_done()
async def main():
 e=Engine();e.init_budget()
 ai=SafeClose(root_engine=e,delegate_engine=e,title='fixture',max_delegation_depth=1,log_dir=Path(os.environ['EVL34_LOG_DIR']))
 try:
  events=[event async for event in ai.query('trusted fixture question')]
  assert any(type(event).__name__=='RootMessage' and getattr(event,'msg',None) is not None and event.msg.content=='fixture answer' for event in events)
  assert e.evl34_budget.reserved==1024
  assert ai.root_kani.depth==0 and ai.max_delegation_depth==1
  print('actual ReDel query: scripted no-delegation fixture, root depth zero and budget intercept passed')
 finally:
  await ai.close()
  if ai.dispatch_task:
   try:await ai.dispatch_task
   except asyncio.CancelledError:pass
asyncio.run(main())

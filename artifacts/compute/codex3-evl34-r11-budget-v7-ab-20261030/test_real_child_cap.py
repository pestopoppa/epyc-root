import asyncio,os
from pathlib import Path
from kani import ChatMessage,ai_function
from kani.models import ToolCall
from kani.engines.base import BaseEngine,Completion
from redel import ReDel
from redel.kanis import ReDelKani
from redel.tools import ToolBase
from redel_budget import ReDelBudgetMixin
from child_call_cap import install,reserve_child
class Search(ToolBase):
 @ai_function()
 async def search(self,query:str):
  """Return a fixed search result."""
  return 'fixture search result'
class Scripted(BaseEngine):
 max_context_size=8192
 def __init__(self):self.roots=0;self.children=0
 def prompt_len(self,messages,functions=None,**kw):return 10
 async def predict(self,messages,functions=None,**kw):
  self.roots+=1
  if self.roots==1:msg=ChatMessage.assistant(None,tool_calls=[ToolCall.from_function('delegate',instructions='fixture helper task')])
  elif self.roots==2:msg=ChatMessage.assistant(None,tool_calls=[ToolCall.from_function('wait',until='all')])
  else:msg=ChatMessage.assistant('fixture final')
  return Completion(msg,10,2)
 async def stream(self,messages,functions=None,**kw):
  self.children+=1
  yield Completion(ChatMessage.assistant(None,tool_calls=[ToolCall.from_function('search',query='fixture')]),10,2)
class Engine(ReDelBudgetMixin,Scripted):pass
class SafeClose(ReDel):
 async def _dispatch_task(self):
  while True:
   event=await self.event_queue.get()
   try:await asyncio.gather(*(cb(event) for cb in self.listeners),return_exceptions=True)
   finally:self.event_queue.task_done()
async def main():
 install(ReDelKani,limit=2);e=Engine();e.init_budget();ai=SafeClose(root_engine=e,delegate_engine=e,title='fixture',max_delegation_depth=0,log_dir=Path(os.environ['EVL34_LOG_DIR']),tool_configs={Search:{'always_include':True}})
 try:
  events=[event.model_dump(mode='json') async for event in ai.query('fixture question')]
  waits=[x['msg']['content'] for x in events if x.get('type')=='kani_message' and (x.get('msg') or {}).get('name')=='wait']
  assert any('per-child model call limit exhausted' in (x or '') for x in waits), waits
  assert e.children==2 and e.roots==3 and e.evl34_budget.reserved==5*4096,(e.children,e.roots,e.evl34_budget.reserved)
  assert any(x.get('type')=='round_complete' for x in events)
  print('actual ReDel child loop stopped by explicit child cap; root received error and completed')
 finally:
  await ai.close()
  if ai.dispatch_task:
   try:await ai.dispatch_task
   except asyncio.CancelledError:pass
asyncio.run(main())

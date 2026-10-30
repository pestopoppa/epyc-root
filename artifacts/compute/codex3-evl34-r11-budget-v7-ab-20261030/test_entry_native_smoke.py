import asyncio,os
from pathlib import Path
from kani import ChatMessage
from kani.models import ToolCall
from kani.engines.base import BaseEngine,Completion
from redel import ReDel
from safe_delegate_wait import SafeDelegateWait
from redel.kanis import ReDelKani
from redel_budget import ReDelBudgetMixin
from child_call_cap import install
from smoke_milestone import inspect
class Scripted(BaseEngine):
 max_context_size=8192
 def __init__(self):self.roots=0
 def prompt_len(self,messages,functions=None,**kw):return 10
 async def predict(self,messages,functions=None,**kw):
  self.roots+=1
  if self.roots==1:msg=ChatMessage.assistant(None,tool_calls=[ToolCall.from_function('wait',until='all')])
  elif self.roots==2:msg=ChatMessage.assistant(None,tool_calls=[ToolCall.from_function('delegate',instructions='look for a fixture')])
  elif self.roots==3:msg=ChatMessage.assistant(None,tool_calls=[ToolCall.from_function('wait',until='all')])
  else:msg=ChatMessage.assistant('final')
  return Completion(msg,10,2)
 async def stream(self,messages,functions=None,**kw):yield Completion(ChatMessage.assistant('fixture child result'),10,2)
class Engine(ReDelBudgetMixin,Scripted):pass
class SafeClose(ReDel):
 async def _dispatch_task(self):
  while True:
   event=await self.event_queue.get()
   try:await asyncio.gather(*(cb(event) for cb in self.listeners),return_exceptions=True)
   finally:self.event_queue.task_done()
async def main():
 install(ReDelKani,16);e=Engine();e.init_budget();ai=SafeClose(root_engine=e,delegate_engine=e,title='fixture',max_delegation_depth=0,delegation_scheme=SafeDelegateWait,log_dir=Path(os.environ['EVL34_LOG_DIR']))
 try:
  events=[];baseline=asyncio.all_tasks();query=ai.query('fixture question');milestone=None
  async for event in query:
   events.append(event.model_dump(mode='json'))
   if inspect(events).get('qualified'):milestone=inspect(events);break
  assert milestone and milestone['qualified']
  waits=[(x.get('msg') or {}) for x in events if x.get('type')=='kani_message' and (x.get('msg') or {}).get('name')=='wait']
  assert any(x.get('content')=='No helpers are currently running.' and x.get('is_tool_call_error') is False for x in waits)
  await query.aclose()
  owned=[t for t in asyncio.all_tasks() if t not in baseline and t is not asyncio.current_task() and t is not ai.dispatch_task]
  for t in owned:t.cancel()
  await asyncio.gather(*owned,return_exceptions=True)
  print('native event milestone and bounded owned task cancellation passed')
 finally:
  await ai.close()
  if ai.dispatch_task:
   try:await ai.dispatch_task
   except asyncio.CancelledError:pass
asyncio.run(main())

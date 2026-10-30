"""Real ReDel query with scripted HTTP completions; NOT model evidence."""
import asyncio,json,os,socket,threading
from pathlib import Path
import httpx
from openai import AsyncOpenAI
from kani.engines.openai import OpenAIEngine
from redel import ReDel
from redel_budget import ReDelBudgetMixin
from stream_transport import StreamingTransport
from stream_broker import serve_stream
from request_policy import RequestPolicy
class Tokenizer:
 def encode(self,text,*a,**kw):return list(text.encode())
class Engine(ReDelBudgetMixin,OpenAIEngine):pass
class SafeClose(ReDel):
 async def _dispatch_task(self):
  while True:
   event=await self.event_queue.get()
   try:await asyncio.gather(*(cb(event) for cb in self.listeners),return_exceptions=True)
   finally:self.event_queue.task_done()
a,b=socket.socketpair();policy=RequestPolicy('pinned');seen=[];errors=[];roots=0
def upstream(path,body):
 global roots
 seen.append(body);stream=body.get('stream',False)
 common={'id':'fixture','created':0,'model':'pinned'}
 if stream:
  common['object']='chat.completion.chunk'
  chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture helper answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}]
  wire=(''.join('data: '+json.dumps(x)+'\n\n' for x in chunks)+'data: [DONE]\n\n').encode()
  return 200,{'content-type':'text/event-stream'},[wire]
 roots+=1
 if roots==1:msg={'role':'assistant','content':None,'tool_calls':[{'id':'call1','type':'function','function':{'name':'delegate','arguments':json.dumps({'instructions':'fixture helper task'})}}]};finish='tool_calls'
 elif roots==2:msg={'role':'assistant','content':None,'tool_calls':[{'id':'call2','type':'function','function':{'name':'wait','arguments':json.dumps({'until':'all'})}}]};finish='tool_calls'
 else:msg={'role':'assistant','content':'fixture final'};finish='stop'
 data=common|{'object':'chat.completion','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}
 return 200,{'content-type':'application/json'},[json.dumps(data).encode()]
def broker():
 try:
  for _ in range(4):serve_stream(a,policy,upstream)
 except Exception as exc:errors.append(exc);print('BROKER REFUSAL',repr(exc),flush=True);a.close()
t=threading.Thread(target=broker);t.start()
async def main():
 http=httpx.AsyncClient(transport=StreamingTransport(b));client=AsyncOpenAI(api_key='fixture',base_url='http://private.invalid/v1',http_client=http,max_retries=0)
 engine=Engine(client=client,model='pinned',max_context_size=8192,tokenizer=Tokenizer());engine.init_budget()
 ai=SafeClose(root_engine=engine,delegate_engine=engine,title='fixture',max_delegation_depth=1,log_dir=Path(os.environ['EVL34_LOG_DIR']))
 try:
  events=[x async for x in ai.query('fixture question')]
  assert sorted(x.depth for x in events if type(x).__name__=='KaniSpawn')==[0,1]
  assert any(type(x).__name__=='KaniDelegated' for x in events)
  assert engine.evl34_budget.reserved==4096
 finally:
  await ai.close()
  if ai.dispatch_task:
   try:await ai.dispatch_task
   except asyncio.CancelledError:pass
  await client.close()
asyncio.run(main());t.join(3);assert not t.is_alive() and not errors and len(seen)==4 and policy.budget.reserved==4096,(errors,len(seen),policy.budget.reserved)
a.close();b.close();print('actual ReDel/Kani root + streamed delegate through incremental broker; synthetic scripted upstream depth 0/1')

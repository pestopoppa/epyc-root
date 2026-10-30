import asyncio,base64,json,socket,threading,time
import httpx
from openai import AsyncOpenAI
from kani import ChatMessage
from kani.engines.openai import OpenAIEngine
from redel_budget import ReDelBudgetMixin
from stream_transport import StreamingTransport
from stream_broker import serve_stream
from request_policy import RequestPolicy
class FakeTokenizer:
 def encode(self,text,*a,**kw):return list(text.encode())
class Engine(ReDelBudgetMixin,OpenAIEngine):pass
a,b=socket.socketpair();policy=RequestPolicy('pinned');seen=[];errors=[]
def upstream(path,body):
 seen.append(body)
 common={'id':'fixture','object':'chat.completion.chunk','created':0,'model':'pinned'}
 chunks=[common|{'choices':[{'index':0,'delta':{'role':'assistant','content':'fixture answer'},'finish_reason':None}]},common|{'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]},common|{'choices':[],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}]
 wire=''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)+'data: [DONE]\n\n'
 def parts():
  mid=len(wire)//2
  yield wire[:mid].encode()
  time.sleep(.1)
  yield wire[mid:].encode()
 return 200,{'content-type':'text/event-stream'},parts()
def broker():
 try:serve_stream(a,policy,upstream)
 except Exception as exc:errors.append(exc)
t=threading.Thread(target=broker);t.start()
async def main():
 http=httpx.AsyncClient(transport=StreamingTransport(b));client=AsyncOpenAI(api_key='fixture',base_url='http://private.invalid/v1',http_client=http,max_retries=0)
 engine=Engine(client=client,model='pinned',max_context_size=8192,tokenizer=FakeTokenizer());engine.init_budget()
 try:
  chunks=[chunk async for chunk in engine.stream([ChatMessage.user('fixture')])]
  assert chunks[-1].message.content=='fixture answer' and chunks[-1].completion_tokens==2 and engine.evl34_budget.reserved==1024
 finally:await client.close()
asyncio.run(main());t.join(2);assert not t.is_alive() and not errors and len(seen)==1 and policy.budget.reserved==1024,(errors,seen)
a.close();b.close();print('actual pinned Kani streaming through private incremental httpx socket broker; synthetic SSE upstream')

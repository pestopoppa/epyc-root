import asyncio,base64,json,socket,threading
import httpx
from openai import AsyncOpenAI
from kani import ChatMessage
from kani.engines.openai import OpenAIEngine
from redel_budget import ReDelBudgetMixin
from redel_transport import SocketTransport
from broker_protocol import serve_one
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
 return {'status':200,'headers':{'content-type':'text/event-stream'},'body_b64':base64.b64encode(wire.encode()).decode()}
def broker():
 try:serve_one(a,policy,upstream)
 except Exception as exc:errors.append(exc)
t=threading.Thread(target=broker);t.start()
async def main():
 http=httpx.AsyncClient(transport=SocketTransport(b));client=AsyncOpenAI(api_key='fixture',base_url='http://private.invalid/v1',http_client=http,max_retries=0)
 engine=Engine(client=client,model='pinned',max_context_size=8192,tokenizer=FakeTokenizer());engine.init_budget()
 try:
  chunks=[chunk async for chunk in engine.stream([ChatMessage.user('fixture')])]
  assert chunks[-1].message.content=='fixture answer' and chunks[-1].completion_tokens==2 and engine.evl34_budget.reserved==1024
 finally:await client.close()
asyncio.run(main());t.join(2);assert not t.is_alive() and not errors and len(seen)==1 and policy.budget.reserved==1024,(errors,seen)
a.close();b.close();print('actual pinned Kani streaming through private buffered httpx socket broker; synthetic SSE upstream')

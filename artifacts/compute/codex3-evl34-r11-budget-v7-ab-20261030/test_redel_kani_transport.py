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
 data={'id':'fixture','object':'chat.completion','created':0,'model':'pinned','choices':[{'index':0,'message':{'role':'assistant','content':'fixture answer'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}
 return {'status':200,'headers':{'content-type':'application/json'},'body_b64':base64.b64encode(json.dumps(data).encode()).decode()}
def broker():
 try:serve_one(a,policy,upstream)
 except Exception as exc:errors.append(exc)
t=threading.Thread(target=broker);t.start()
async def main():
 http=httpx.AsyncClient(transport=SocketTransport(b));client=AsyncOpenAI(api_key='fixture',base_url='http://private.invalid/v1',http_client=http,max_retries=0)
 engine=Engine(client=client,model='pinned',max_context_size=8192,tokenizer=FakeTokenizer());engine.init_budget()
 try:
  completion=await engine.predict([ChatMessage.user('fixture')]);assert completion.message.content=='fixture answer';assert engine.evl34_budget.reserved==1024
 finally:await client.close()
asyncio.run(main());t.join(2);assert not t.is_alive() and not errors and len(seen)==1 and policy.budget.reserved==1024,(errors,seen)
a.close();b.close();print('actual pinned Kani OpenAIEngine predict through private httpx socket broker and shared policy; synthetic upstream')

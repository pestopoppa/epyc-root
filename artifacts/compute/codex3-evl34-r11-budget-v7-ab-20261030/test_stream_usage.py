import asyncio,socket,threading,json
import httpx
from stream_broker import serve_stream
from stream_transport import StreamingTransport
from request_policy import RequestPolicy
from native_usage import UsageLedger
a,b=socket.socketpair();policy=RequestPolicy('pinned');ledger=UsageLedger();errors=[]
def upstream(path,body):
 wire=b'data: {"usage":{"prompt_tokens":4,"completion_tokens":2}}\n\ndata: [DONE]\n\n'
 return 200,{'content-type':'text/event-stream'},[wire[:20],wire[20:]]
def broker():
 try:serve_stream(a,policy,upstream,ledger)
 except Exception as e:errors.append(e)
t=threading.Thread(target=broker);t.start()
async def main():
 async with httpx.AsyncClient(transport=StreamingTransport(b),base_url='http://private.invalid') as client:
  r=await client.post('/v1/chat/completions',json={'model':'pinned','temperature':0,'seed':42,'max_tokens':1024,'stream':True,'stream_options':{'include_usage':True},'messages':[{'role':'user','content':'fixture'}]})
  assert '[DONE]' in r.text
asyncio.run(main());t.join(3)
assert not t.is_alive() and not errors and ledger.totals()=={'prompt_tokens':4,'completion_tokens':2},errors
a.close();b.close();print('incremental parent broker preserves server-reported SSE usage')

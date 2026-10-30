import asyncio,json,socket,threading,time,unittest
import httpx
from broker_protocol import recv,send
from browse_adapters import redel_exchange
from channel_pool import ChannelPool
from stream_pool_transport import PooledStreamingTransport
class QueueTests(unittest.TestCase):
 def test_actual_model_and_tool_channels_wait_past_five_seconds(self):
  async def run():
   model_client,model_peer=socket.socketpair();tool_client,tool_peer=socket.socketpair();transport=PooledStreamingTransport([model_client]);held=transport.q.get_nowait();tool_queue=asyncio.Queue();errors=[]
   def broker(sock,tool):
    try:
     req=recv(sock)
     if tool:send(sock,{'tool_result':'fixture-result'})
     else:send(sock,{'type':'headers','status':200,'headers':{}});send(sock,{'type':'done','total':0})
    except BaseException as e:errors.append(repr(e))
   threads=[threading.Thread(target=broker,args=(model_peer,False)),threading.Thread(target=broker,args=(tool_peer,True))]
   for t in threads:t.start()
   async def release():await asyncio.sleep(6);transport.q.put_nowait(held);tool_queue.put_nowait(tool_client)
   release_task=asyncio.create_task(release());req=httpx.Request('POST','http://private.invalid/v1/chat/completions',content=b'{}');start=time.monotonic()
   response,result=await asyncio.gather(transport.handle_async_request(req),redel_exchange(tool_queue,'search','fixture'));await response.aread();await release_task
   self.assertGreaterEqual(time.monotonic()-start,5.5);self.assertEqual(response.status_code,200);self.assertEqual(result,'fixture-result')
   for t in threads:t.join(3)
   self.assertFalse(errors);self.assertFalse(any(t.is_alive() for t in threads))
   for x in (model_client,model_peer,tool_client,tool_peer):x.close()
  asyncio.run(run())
 def test_repl_pool_waits_past_five_seconds(self):
  a,b=socket.socketpair();pool=ChannelPool([a]);held=pool.take();timer=threading.Timer(6,lambda:pool.put(held));timer.start();start=time.monotonic()
  try:self.assertIs(pool.take(),a);self.assertGreaterEqual(time.monotonic()-start,5.5)
  finally:timer.join();a.close();b.close()
if __name__=='__main__':unittest.main()

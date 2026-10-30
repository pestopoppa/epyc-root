import asyncio,base64,socket,threading,time,unittest
import httpx
from broker_protocol import recv,send
from stream_transport import Body
from stream_pool_transport import PooledStreamingTransport
from browse_adapters import redel_exchange
class Lease:
 def __init__(self):self.count=0
 def release(self):self.count+=1
class Tests(unittest.TestCase):
 def test_late_done_repeated_and_malformed(self):
  async def run(malformed=False):
   a,b=socket.socketpair();lease=Lease();payload=b'data: [DONE]\n\n'
   def peer():
    send(a,{'type':'data','data':base64.b64encode(payload).decode()});time.sleep(1.3);send(a,{'type':'done','total':999 if malformed else len(payload)})
   t=threading.Thread(target=peer);t.start();body=Body(b,lease);it=body.__aiter__();self.assertEqual(await it.__anext__(),payload)
   if malformed:
    with self.assertRaises(ValueError):await it.aclose()
    self.assertLess(b.fileno(),0)
   else:
    await it.aclose();self.assertTrue(body.complete);self.assertGreaterEqual(b.fileno(),0)
   self.assertEqual(lease.count,1);await body.aclose();self.assertEqual(lease.count,1);t.join();a.close();b.close()
  for _ in range(2):asyncio.run(run())
  asyncio.run(run(True))
 def test_cancel_poison_exactly_once(self):
  async def run():
   a,b=socket.socketpair();lease=Lease();body=Body(b,lease);it=body.__aiter__();task=asyncio.create_task(it.__anext__());await asyncio.sleep(.05);task.cancel()
   with self.assertRaises(asyncio.CancelledError):await task
   self.assertLess(b.fileno(),0);self.assertEqual(lease.count,1);a.close()
  asyncio.run(run())
 def test_three_busy_mixed_model_web_release(self):
  async def run():
   pairs=[socket.socketpair() for _ in range(3)];transport=PooledStreamingTransport([x for x,y in pairs]);errors=[]
   def peer(s):
    try:
     req=recv(s);time.sleep(6)
     if req['path'].startswith('/tool/'):send(s,{'tool_result':'ok'})
     else:send(s,{'type':'headers','status':200,'headers':{}});send(s,{'type':'done','total':0})
     req=recv(s)
     if req['path'].startswith('/tool/'):send(s,{'tool_result':'ok'})
     else:send(s,{'type':'headers','status':200,'headers':{}});send(s,{'type':'done','total':0})
    except EOFError:pass
    except BaseException as e:errors.append(repr(e))
   threads=[threading.Thread(target=peer,args=(p,)) for c,p in pairs]
   for t in threads:t.start()
   async def model():
    r=await transport.handle_async_request(httpx.Request('POST','http://private.invalid/v1/chat/completions',content=b'{}'));await r.aread();return r.status_code
   started=time.monotonic();tasks=[asyncio.create_task(model()),asyncio.create_task(model()),asyncio.create_task(redel_exchange(transport.q,'search','fixture'))];await asyncio.sleep(.1);self.assertEqual(transport.q.qsize(),0);fourth=asyncio.create_task(model());values=await asyncio.gather(*tasks,fourth);self.assertGreaterEqual(time.monotonic()-started,5.5);self.assertEqual(values,[200,200,'ok',200]);self.assertEqual(transport.q.qsize(),3)
   for c,p in pairs:c.close();p.close()
   for t in threads:t.join(3)
   self.assertFalse(errors,errors);self.assertFalse(any(t.is_alive() for t in threads))
  asyncio.run(run())
if __name__=='__main__':unittest.main()

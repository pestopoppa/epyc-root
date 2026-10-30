import asyncio,socket,threading,unittest
from broker_protocol import recv,send
from browse_adapters import Registry,redel_exchange
from channel_pool import ChannelPool

class BridgeTests(unittest.TestCase):
 def roundtrip(self,arm):
  a,b=socket.socketpair()
  def broker():
   req=recv(a)
   self.assertEqual(req,{'path':'/tool/search','body':{'value':'neutral','max_results':3 if arm=='repl' else 5}})
   send(a,{'tool_result':'results'})
  t=threading.Thread(target=broker);t.start()
  try:
   if arm=='repl': self.assertEqual(Registry(ChannelPool([b])).invoke('web_search',None,query='neutral',max_results=3),'results')
   else:
    async def run():
     q=asyncio.Queue();q.put_nowait(b)
     self.assertEqual(await redel_exchange(q,'search','neutral'),'results')
     self.assertIs(await q.get(),b)
    asyncio.run(run())
  finally:t.join(3);a.close();b.close()
  self.assertFalse(t.is_alive())
 def test_repl(self):self.roundtrip('repl')
 def test_redel(self):self.roundtrip('redel')
if __name__=='__main__': unittest.main()

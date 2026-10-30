import socket,threading,unittest
from entry_gate import EntryGate
from broker_protocol import send,recv,serve_one
from request_policy import RequestPolicy
class SocketHandoff(unittest.TestCase):
 def test_first_response_then_queued_tool_no_broken_pipe(self):
  gate=EntryGate();policy=RequestPolicy('pinned');a,b=socket.socketpair();seen=[];errors=[]
  def broker():
   try:
    while True:
     req=recv(a)
     def operation():
      if req['path']=='/v1/chat/completions':
       serve_one(a,policy,lambda *_:{'choices':[{'message':{'content':'answer'}}],'usage':{'prompt_tokens':2,'completion_tokens':1}},req=req)
      else:seen.append('unexpected late tool');send(a,{'tool_result':'value'})
     if not gate.dispatch(operation,first_model_response=req['path']=='/v1/chat/completions'):break
   except EOFError:pass
   except Exception as exc:errors.append(exc)
  t=threading.Thread(target=broker);t.start()
  try:
   body={'model':'pinned','messages':[{'role':'user','content':'fixture'}],'max_tokens':4096,'temperature':0,'seed':42}
   send(b,{'path':'/v1/chat/completions','body':body,'depth':0})
   response=recv(b);self.assertEqual(response['response']['choices'][0]['message']['content'],'answer')
   self.assertTrue(gate.ready.wait(1))
   send(b,{'path':'/tool/search','body':{'value':'fixture','max_results':1}})
   t.join(2);self.assertFalse(t.is_alive());self.assertEqual(seen,[]);self.assertEqual(errors,[])
  finally:b.close();a.close();t.join(2)
if __name__=='__main__':unittest.main()

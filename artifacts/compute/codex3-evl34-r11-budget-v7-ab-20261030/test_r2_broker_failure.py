import json,socket,tempfile,threading,unittest
from pathlib import Path
from control_driver import record_broker_error
from request_capture import RequestCapture
from request_policy import RequestPolicy
from stream_broker import serve_stream

class BrokerFailureTests(unittest.TestCase):
 def test_bad_request_recorded_before_refusal(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);capture=RequestCapture(root/'requests');left,right=socket.socketpair();bad={'path':'/v1/chat/completions','body':{'model':'wrong','messages':[{'role':'user','content':'fixture'}]}}
   try:
    with self.assertRaises(ValueError):serve_stream(left,RequestPolicy('pinned'),lambda *args:None,request_observer=capture,req=bad)
    self.assertEqual(json.loads((root/'requests/0000.json').read_text()),bad['body'])
    errors=[];record_broker_error(root,'dispatch',ValueError('wrong model'),errors,threading.Lock())
    self.assertEqual(json.loads((root/'broker-error-1.json').read_text()),{'phase':'dispatch','exception_type':'ValueError','message':'wrong model'})
   finally:left.close();right.close()
 def test_truncated_frame_retained(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);errors=[];record_broker_error(root,'dispatch',EOFError('truncated frame'),errors,threading.Lock())
   self.assertEqual(json.loads((root/'broker-error-1.json').read_text())['message'],'truncated frame')
if __name__=='__main__':unittest.main()

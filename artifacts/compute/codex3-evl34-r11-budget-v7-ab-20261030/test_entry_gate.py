import threading,time,unittest
from entry_gate import EntryGate
class GateTests(unittest.TestCase):
 def test_first_model_send_closes_dispatch_after_prior_inflight(self):
  gate=EntryGate();web_started=threading.Event();web_release=threading.Event();model_started=threading.Event();sent=[]
  def web():
   def operation():web_started.set();web_release.wait(2);sent.append('web_sent')
   gate.dispatch(operation)
  def model():
   model_started.set();gate.dispatch(lambda:sent.append('model_sent'),first_model_response=True)
  a=threading.Thread(target=web);a.start();self.assertTrue(web_started.wait(1));b=threading.Thread(target=model);b.start();self.assertTrue(model_started.wait(1));self.assertFalse(gate.ready.wait(.03));web_release.set();a.join(2);b.join(2)
  self.assertTrue(gate.ready.is_set());self.assertEqual(sent,['web_sent','model_sent'])
  self.assertFalse(gate.dispatch(lambda:sent.append('late_web')));self.assertEqual(sent,['web_sent','model_sent'])
 def test_failed_first_send_never_signals_ready(self):
  gate=EntryGate()
  def fail():raise BrokenPipeError('synthetic broken send')
  with self.assertRaises(BrokenPipeError):gate.dispatch(fail,first_model_response=True)
  self.assertFalse(gate.ready.is_set())
if __name__=='__main__':unittest.main()

class DrainGateTests(unittest.TestCase):
 def test_quiescence_waits_inflight_then_acknowledges(self):
  from entry_gate import DrainGate
  gate=DrainGate();started=threading.Event();release=threading.Event();drained=threading.Event();sent=[]
  def inflight():
   self.assertTrue(gate.begin());started.set();release.wait(2);sent.append('send-complete');gate.end()
  def close():gate.close_and_drain(lambda:False);drained.set()
  a=threading.Thread(target=inflight);a.start();self.assertTrue(started.wait(1));b=threading.Thread(target=close);b.start();time.sleep(.03)
  self.assertFalse(gate.begin());self.assertFalse(drained.is_set());self.assertFalse(gate.is_acknowledged())
  with self.assertRaises(RuntimeError):gate.acknowledge(lambda:None)
  release.set();a.join(2);b.join(2);self.assertEqual(sent,['send-complete']);self.assertTrue(drained.is_set())
  gate.acknowledge(lambda:sent.append('ack'));self.assertTrue(gate.is_acknowledged());self.assertEqual(sent,['send-complete','ack'])
 def test_failed_ack_does_not_mark_quiescent(self):
  from entry_gate import DrainGate
  gate=DrainGate();gate.close_and_drain(lambda:False)
  def broken():raise BrokenPipeError('failed ack')
  with self.assertRaises(BrokenPipeError):gate.acknowledge(broken)
  self.assertFalse(gate.is_acknowledged())

class FirstResponseGateTests(unittest.TestCase):
 def test_first_response_waits_for_active_sends_then_closes(self):
  from entry_gate import DrainGate
  gate=DrainGate();self.assertTrue(gate.begin());self.assertTrue(gate.begin());done=threading.Event()
  def finish():gate.finish_first_and_drain(lambda:False);done.set()
  t=threading.Thread(target=finish);t.start();time.sleep(.03);self.assertFalse(done.is_set());self.assertFalse(gate.begin());gate.end();t.join(2)
  self.assertTrue(done.is_set());self.assertTrue(gate.is_acknowledged())

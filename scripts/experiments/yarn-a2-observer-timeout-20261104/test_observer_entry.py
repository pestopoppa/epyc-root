import unittest
from observer_entry import Observer, ObservationError, processing
class Clock:
 def __init__(self): self.n=0
 def __call__(self): self.n+=100_000_000; return self.n
class TestObserver(unittest.TestCase):
 def test_bracket_interval_and_cap(self):
  c=Clock(); o=Observer('r',lambda:{'pid':7,'start_ticks':3,'vram_bytes':42},lambda:[{'is_processing':True,'id_task':7}],lambda:25,interval_s=.1,max_samples=2,clock=c)
  for _ in range(3): o.poll()
  out=o.finish(); self.assertEqual(len(out['samples']),2); self.assertEqual(out['truncated_samples'],1)
  s=out['samples'][0]; self.assertLess(s['slot_before_interval_ns'][1],s['measurement_interval_ns'][0]); self.assertLess(s['measurement_interval_ns'][1],s['slot_after_interval_ns'][0])
 def test_idle_or_finished_is_not_counted(self):
  slots=iter([[{'is_processing':False}],[{'is_processing':True,'id_task':7}],[{'is_processing':False}]])
  o=Observer('r',lambda:{'pid':1,'start_ticks':2,'vram_bytes':1},lambda:next(slots),lambda:0,interval_s=.1,clock=Clock())
  o.poll(); o.poll(); x=o.finish(); self.assertEqual(x['samples'],[]); self.assertEqual(x['slot_not_bracketed'],2)
 def test_identity_change_fails(self):
  v=iter([{'pid':1,'start_ticks':2,'vram_bytes':4},{'pid':1,'start_ticks':3,'vram_bytes':4}])
  o=Observer('r',lambda:next(v),lambda:[{'is_processing':True,'id_task':7}],lambda:0,interval_s=.1,clock=Clock())
  o.poll()
  with self.assertRaises(ObservationError): o.poll()
 def test_malformed_or_unavailable_refused(self):
  with self.assertRaises(ObservationError): processing([{'is_processing':1}])
  o=Observer('r',lambda:{'vram_bytes':0},lambda:[{'is_processing':True,'id_task':7}],lambda:0,interval_s=.1,clock=Clock())
  with self.assertRaises(ObservationError): o.poll()
 def test_rate_limit(self):
  c=Clock(); o=Observer('r',lambda:{'pid':1,'start_ticks':1,'vram_bytes':1},lambda:[{'is_processing':True,'id_task':7}],lambda:0,interval_s=10,clock=c)
  o.poll(); o.poll(); self.assertEqual(o.finish()['attempts'],1)
 def test_timeout_before_and_after_are_counted_without_abort(self):
  active=[{'is_processing':True,'id_task':7}]
  calls=iter([TimeoutError('before'),active,TimeoutError('after'),active,active])
  def slots():
   x=next(calls)
   if isinstance(x,Exception): raise x
   return x
  o=Observer('r',lambda:{'pid':7,'start_ticks':3,'vram_bytes':42},slots,lambda:25,interval_s=.1,clock=Clock())
  o.poll(); o.poll(); o.poll(); out=o.finish()
  self.assertEqual(out['slot_timeouts'],2)
  self.assertEqual(out['slot_not_bracketed'],2)
  self.assertEqual(out['bracketed_sample_count'],1)
  self.assertEqual(len(out['samples']),1)
if __name__=='__main__': unittest.main()

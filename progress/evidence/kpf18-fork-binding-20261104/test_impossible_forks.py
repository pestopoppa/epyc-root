import copy, unittest
import test_fork_binding as fixture_mod
from debug3_data import DataError, parse
from evidence_view import build
from fork_binding import bind_native_fork

class ImpossibleForks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  fixture_mod.NativeForkBindingTests.setUpClass()
  cls.fixture=fixture_mod.NativeForkBindingTests
 def check_refused(self, old, new, update):
  f=self.fixture; raw=f.raw.replace(old,new,1)
  self.assertNotEqual(raw,f.raw); self.assertEqual(len(raw),len(f.raw))
  view,mapping,_=build(raw);_,messages=parse(view); event=copy.deepcopy(f.event)
  update(event)
  with self.assertRaises(DataError):
   bind_native_fork(messages[0],messages,[event],mapping,1166016091,raw)
 def test_source_is_destination(self):
  self.check_refused(b'src = 0 (idle)',b'src = 1 (idle)',lambda e:e['response']['timings'].__setitem__('fork_src_slot',1))
 def test_source_out_of_range(self):
  self.check_refused(b'src = 0 (idle)',b'src = 9 (idle)',lambda e:e['response']['timings'].__setitem__('fork_src_slot',9))
 def test_no_remaining_prompt(self):
  self.check_refused(b'n_fork_tokens = 32000',b'n_fork_tokens = 36000',lambda e:e['response']['timings'].__setitem__('n_fork_tokens',36000))
 def test_empty_fork(self):
  self.check_refused(b'n_fork_tokens = 32000',b'n_fork_tokens = 00000',lambda e:e['response']['timings'].__setitem__('n_fork_tokens',0))
if __name__=='__main__':unittest.main()

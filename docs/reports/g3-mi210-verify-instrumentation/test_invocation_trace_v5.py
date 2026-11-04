import unittest
from invocation_trace_v5 import classify_invocation_trace_v5
from test_invocation_trace_v3 import B, D, E

def t(line, n): return line + ' time_ns=' + str(n)
def unknown(line): return line.replace('invocation=12 correlation=host_scope', 'invocation=0 correlation=unknown')

class ScopedTraceTest(unittest.TestCase):
 def parse(self, lines): return classify_invocation_trace_v5('\n'.join(lines), expected_layer_ids=[3])
 def test_outside_unknown_is_retained_but_not_candidate(self):
  out=self.parse([t(unknown(D),1),t(B,2),t(D,3),t(E,4),t(unknown(D),5)])
  self.assertEqual(out['status'],'OBSERVED'); self.assertEqual(out['outside_target_unknown_dispatches'],2)
  self.assertEqual(out['candidates'][0]['status'],'OBSERVED')
 def test_unknown_inside_fails(self):
  with self.assertRaises(ValueError): self.parse([t(B,1),t(unknown(D),2),t(D,3),t(E,4)])
 def test_overlap_fails(self):
  with self.assertRaises(ValueError): self.parse([t(B,1),t(B.replace('invocation=12','invocation=13'),2),t(E,3)])
 def test_async_after_end_fails(self):
  with self.assertRaises(ValueError): self.parse([t(B,1),t(D,2),t(E,3),t(D,4)])
 def test_clock_backwards_fails(self):
  with self.assertRaises(ValueError): self.parse([t(B,2),t(D,1),t(E,3)])
 def test_missing_layer_remains_unknown(self):
  self.assertEqual(classify_invocation_trace_v5('\n'.join([t(B,1),t(D,2),t(E,3)]),expected_layer_ids=[3,7])['status'],'UNKNOWN')

if __name__ == '__main__': unittest.main()

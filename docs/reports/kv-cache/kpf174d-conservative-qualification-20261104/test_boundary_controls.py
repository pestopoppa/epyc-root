import unittest
from layout_witness import Invalid, witness
from test_layout_witness import trace

def renumber(raw):
 return raw.replace(b'id=4',b'id=5').replace(b'id=8',b'id=9')

def second_layout(raw):
 start=raw.index(b'KPF_LAYOUT_BEGIN')
 end=raw.index(b'KPF_ITEM4_END')
 layout=raw[start:end].replace(b'id=8',b'id=9')
 return raw[:end]+layout+raw[end:]

class BoundaryControls(unittest.TestCase):
 def test_boundary_excludes_later_coverage(self):
  later=renumber(trace()).replace(b'pos=2 output',b'pos=3 output')
  self.assertEqual(witness(trace()+later,42,1,2)['batch'],4)
 def test_only_later_coverage_refused(self):
  with self.assertRaisesRegex(Invalid,'exactly one'):
   witness(trace().replace(b'pos=2 output',b'pos=3 output'),42,1,2)
 def test_duplicate_boundaries_refused(self):
  with self.assertRaisesRegex(Invalid,'exactly one'):witness(trace()+renumber(trace()),42,1,2)
 def test_multilayout_boundary_refused(self):
  with self.assertRaisesRegex(Invalid,'multi-layout'):witness(second_layout(trace()),42,1,2)
 def test_multilayout_nonboundary_target_refused(self):
  with self.assertRaisesRegex(Invalid,'multi-layout'):
   witness(second_layout(trace().replace(b'pos=2 output',b'pos=3 output')),42,1,2)
 def test_single_matching_layout_in_multilayout_refused(self):
  raw=second_layout(trace()).replace(b'id=8 stream=0 cell=0 pos=0 mask=3 owners=2',b'id=8 stream=0 cell=0 pos=0 mask=1 owners=1')
  with self.assertRaisesRegex(Invalid,'multi-layout'):witness(raw,42,1,2)
 def test_non_target_multilayout_does_not_confuse_boundary(self):
  other=renumber(second_layout(trace(task=99))).replace(b'id=9',b'id=10')
  # Allocate unique IDs across both layouts after the simple renumbering.
  other=other.replace(b'KPF_LAYOUT_BEGIN id=10',b'KPF_LAYOUT_BEGIN id=11',1).replace(b'KPF_LAYOUT_STREAM id=10',b'KPF_LAYOUT_STREAM id=11',1).replace(b'KPF_LAYOUT_CELL id=10',b'KPF_LAYOUT_CELL id=11',2).replace(b'KPF_LAYOUT_END id=10',b'KPF_LAYOUT_END id=11',1)
  self.assertEqual(witness(trace()+other,42,1,2)['batch'],4)
if __name__=='__main__':unittest.main()

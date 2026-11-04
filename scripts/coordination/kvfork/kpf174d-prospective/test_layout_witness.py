import unittest
from layout_witness import Invalid, witness, compare

def trace(slot=1, task=42, mask=3, owners=2):
 return (f'''KPF_ITEM4_BEGIN id=4 off=0 rows=1 decode_prefix=0
KPF_ITEM4_ROW id=4 row=0 owner={slot} task={task} nseq=1 pos=2 output=1 phase=prefill
KPF_LAYOUT_BEGIN id=8 streams=1 swa=0 nseq=1 tokens=1
KPF_LAYOUT_STREAM id=8 stream=0 size=8 used=2 head=2
KPF_LAYOUT_CELL id=8 stream=0 cell=0 pos=0 mask={mask} owners={owners}
KPF_LAYOUT_CELL id=8 stream=0 cell=1 pos=1 mask={mask} owners={owners}
KPF_LAYOUT_END id=8
KPF_ITEM4_END id=4 ret=0
''').encode()
class Tests(unittest.TestCase):
 def test_bound(self):
  a=witness(trace(),42,1,2); b=witness(trace(2,43,4,1),43,2,2)
  self.assertTrue(compare(a,b)['same_physical_prefix']);self.assertEqual(compare(a,b)['verdict'],'MATCHED')
 def test_capacity_mismatch(self):
  a=witness(trace(),42,1,2); b=witness(trace(2,43,4,1).replace(b'size=8',b'size=16'),43,2,2)
  self.assertEqual(compare(a,b)['verdict'],'INVALID')
 def test_missing_geometry(self):
  a=witness(trace(),42,1,2); b=dict(a); del b['capacity']
  self.assertEqual(compare(a,b)['verdict'],'INVALID')
 def test_wrong_task(self):
  with self.assertRaises(Invalid):witness(trace(),99,1,2)
 def test_ambiguous_owner(self):
  with self.assertRaises(Invalid):witness(trace(mask=3,owners=3),42,1,2)
 def test_incomplete(self):
  with self.assertRaises(Invalid):witness(trace().replace(b'KPF_LAYOUT_END id=8\n',b''),42,1,2)
 def test_different_layout(self):
  a=witness(trace(),42,1,2); raw=trace(2,43,4,1).replace(b'cell=1 pos=1',b'cell=2 pos=1')
  self.assertFalse(compare(a,witness(raw,43,2,2))['same_physical_prefix'])
 def test_duplicate_snapshot(self):
  raw=trace(); raw+=raw.replace(b'id=4',b'id=5').replace(b'id=8',b'id=9')
  with self.assertRaises(Invalid):witness(raw,42,1,2)
 def test_unexpected_drafter(self):
  with self.assertRaises(Invalid):witness(trace().replace(b'swa=0',b'swa=1'),42,1,2)
if __name__=='__main__': unittest.main()

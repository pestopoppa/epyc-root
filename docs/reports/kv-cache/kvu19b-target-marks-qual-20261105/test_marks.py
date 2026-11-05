import unittest
from marks import parse
L=['P3_CLOCK phase=begin step=0 hsa_tick=100 hsa_hz=1000000 mono_before_ns=1000 mono_after_ns=1001','P3_CLOCK phase=end step=0 hsa_tick=110 hsa_hz=1000000 mono_before_ns=1100 mono_after_ns=1101','P3_CLOCK phase=begin step=1 hsa_tick=120 hsa_hz=1000000 mono_before_ns=1200 mono_after_ns=1201','P3_CLOCK phase=end step=1 hsa_tick=130 hsa_hz=1000000 mono_before_ns=1300 mono_after_ns=1301']
class Controls(unittest.TestCase):
 def test_valid(self): self.assertEqual(len(parse('noise\n'+'\n'.join(L),2)),4)
 def test_refusals(self):
  cases=[L[:-1], L+[L[-1]], [L[1],L[0]]+L[2:], [L[0],L[1].replace('step=0','step=1')]+L[2:], [L[0],L[1].replace('hsa_hz=1000000','hsa_hz=2000000')]+L[2:], [L[0],L[1].replace('hsa_tick=110','hsa_tick=90')]+L[2:], [L[0],L[1].replace('mono_before_ns=1100','mono_before_ns=900')]+L[2:], [L[0],L[1].replace('mono_after_ns=1101','mono_after_ns=1099')]+L[2:], [L[0],L[1].replace('phase=end','phase=bad')]+L[2:], L+['P3_CLOCK_ERROR unavailable']]
  for c in cases:
   with self.subTest(c=c), self.assertRaises(ValueError): parse('\n'.join(c),2)

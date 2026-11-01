"""Offline coverage of qualification and production affinity gates."""
import unittest
from supervisor import admitted_threads

class Admission(unittest.TestCase):
 def test_qualifies_any_exact_quarter(self):
  for start in (0, 24, 48, 72):
   self.assertEqual(admitted_threads({'FILLER_DRYRUN':'1','FILLER_CPUS':f'{start}-{start+23}'}, range(start,start+24)),24)
 def test_refuses_partial_and_spoofed_grants(self):
  for env, affinity in [({'FILLER_DRYRUN':'1','FILLER_CPUS':'0-23'}, range(23)), ({'FILLER_DRYRUN':'1','FILLER_CPUS':'0-95'}, range(96)), ({'FILLER_CPUS':'0-23'}, range(24)), ({'FILLER_CPUS':'0-95'}, range(95))]:
   with self.assertRaises(ValueError): admitted_threads(env, affinity)
 def test_real_requires_full_original_claim(self):
  self.assertEqual(admitted_threads({'FILLER_CPUS':'0-95'},range(96)),96)
if __name__=='__main__': unittest.main()

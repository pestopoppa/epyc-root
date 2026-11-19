import unittest
from job import validate_rows
class Cases(unittest.TestCase):
 def test_exact(self): self.assertEqual(validate_rows([dict(autokernel_hardened=False,n_depth=65536,n_prompt=0,n_gen=32,avg_ts=2)],65536,32),2)
 def test_wrong_protocol(self):
  for v in [True,'false',None]:
   with self.assertRaises(AssertionError):validate_rows([dict(autokernel_hardened=v,n_depth=65536,n_prompt=0,n_gen=32,avg_ts=2)],65536,32)
 def test_wrong_depth(self):
  with self.assertRaises(AssertionError):validate_rows([dict(autokernel_hardened=False,n_depth=0,n_prompt=0,n_gen=32,avg_ts=2)],65536,32)
if __name__=='__main__':unittest.main()

import unittest
from commands import command
class CommandTest(unittest.TestCase):
 def test_control_is_short_and_separate(self):
  c=command('control','control','/tmp/control');self.assertEqual(c[c.index('--nps')+1],'1');self.assertEqual(c[c.index('--lens')+1],'8k');self.assertNotIn('--aba-key',c)
 def test_target_is_quarter_24(self):
  for a in ('unified','split'):
   c=command('target',a,'/tmp/target','/tmp/ledger');self.assertEqual(c[c.index('--threads')+1],'24');self.assertEqual(c[c.index('--nps')+1],'8');self.assertEqual(c[c.index('--waves')+1],'4');self.assertEqual(c[c.index('--lens')+1],'64k')
 def test_modes_fail_closed(self):
  with self.assertRaises(ValueError):command('control','unified','/tmp/control')
  with self.assertRaises(ValueError):command('target','split','/tmp/target')
  with self.assertRaises(ValueError):command('target','unified','relative','/tmp/ledger')
if __name__=='__main__':unittest.main()

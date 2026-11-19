import json,pathlib,tempfile,time,unittest
from job import mode,check_claim,append_native
class JobTest(unittest.TestCase):
 def test_explicit_modes(self):
  self.assertEqual(mode({'FILLER_DRYRUN':'1'}),'control');self.assertEqual(mode({'FILLER_DRYRUN':'0'}),'target')
  for d in ({},{'FILLER_DRYRUN':'x'}):
   with self.assertRaises(ValueError):mode(d)
 def test_24_thread_claim_and_stop(self):
  with tempfile.TemporaryDirectory() as d:
   e={'FILLER_CPUS':'72-95','FILLER_THREADS':'24','FILLER_NEEDGPU':'0','FILLER_STOPFILE':d+'/STOP','FILLER_DEADLINE':str(int(time.time())+10)};check_claim(e)
   e['FILLER_THREADS']='96'
   with self.assertRaises(ValueError):check_claim(e)
   e['FILLER_THREADS']='24';pathlib.Path(e['FILLER_STOPFILE']).touch()
   with self.assertRaises(ValueError):check_claim(e)
 def test_no_synthetic_event(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'result.jsonl'
   with self.assertRaises(ValueError):append_native(p,{'mode':'control'})
   self.assertFalse(p.exists())
   append_native(p,{'mode':'control','native_record_complete':True});self.assertTrue(json.loads(p.read_text())['native_record_complete'])
if __name__=='__main__':unittest.main()

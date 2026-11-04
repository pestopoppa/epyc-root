import json,os,pathlib,tempfile,unittest
from unittest.mock import patch,MagicMock
import smoke,job
class SmokeTest(unittest.TestCase):
 def test_grant_parser(self):self.assertEqual(smoke.cpus('72-73,170'),{72,73,170})
 def test_smoke_branch_never_enters_target(self):
  with patch.dict(os.environ,{'FILLER_DRYRUN':'1'}),patch('smoke.run') as run,patch('job.check_claim',side_effect=AssertionError('target entered')):
   job.main();run.assert_called_once()
 def test_target_still_requires_full_claim(self):
  with patch.dict(os.environ,{'FILLER_DRYRUN':'0','FILLER_CPUS':'0-3'}):
   with self.assertRaises(ValueError):job.main()
 def test_model_receipt_fails_on_changed_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'model';p.write_bytes(b'fixture');receipt={str(p):{'identity':smoke.identity(p),'sha256':'fixed'}}
   pathlib.Path(d,'MODEL-INPUTS.json').write_text(json.dumps(receipt))
   with patch.object(smoke,'D',pathlib.Path(d)):
    self.assertEqual(smoke.verify_model(p),'fixed');p.write_bytes(b'changed')
    with self.assertRaises(RuntimeError):smoke.verify_model(p)
 def test_no_model_hash_in_target(self):self.assertNotIn('digest(MODEL)',pathlib.Path(job.__file__).read_text())
 def test_native_result_separate_from_target(self):
  src=pathlib.Path(smoke.__file__).read_text();self.assertIn("dest==D/'events.jsonl'",src);self.assertIn("'measurement':False",src)
 def test_launcher_preserves_smoke_path(self):
  src=pathlib.Path(smoke.__file__).with_name('launch.sh').read_text();self.assertEqual(src.count('FILLER_DRYRUN_RESULT_PATH='),2)
if __name__=='__main__':unittest.main()
class CustodyTest(unittest.TestCase):
 def test_listener_requires_pid_socket_match(self):
  tcp='header\n0: 0100007F:4A1A 00000000:0000 0A a b c d e 123\n'
  fd=MagicMock();fd.iterdir.return_value=[pathlib.Path('/fake/fd/1')]
  with patch('smoke.pathlib.Path.read_text',return_value=tcp),patch('smoke.pathlib.Path.iterdir',return_value=[pathlib.Path('/fake/fd/1')]),patch('smoke.os.readlink',return_value='socket:[123]'):
   self.assertTrue(smoke.owns_listener(99))
  with patch('smoke.pathlib.Path.read_text',return_value=tcp),patch('smoke.pathlib.Path.iterdir',return_value=[pathlib.Path('/fake/fd/1')]),patch('smoke.os.readlink',return_value='socket:[456]'):
   self.assertFalse(smoke.owns_listener(99))
 def test_wrong_resident_linkage_fails(self):
  with patch('smoke.pathlib.Path.read_text',return_value='x /wrong/libggml-base.so'):
   with self.assertRaises(RuntimeError):smoke.check_resident_linkage(99)

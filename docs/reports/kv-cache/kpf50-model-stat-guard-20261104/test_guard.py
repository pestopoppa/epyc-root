import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from guard import snapshot,validate

class GuardTests(unittest.TestCase):
 def test_accept_metadata_without_open(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model';p.write_bytes(b'not weights');rec=snapshot(p)
   with patch('builtins.open',side_effect=AssertionError('weight opened')):self.assertTrue(validate(rec))
 def test_changed_file_and_replaced_inode_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model';p.write_bytes(b'a');rec=snapshot(p);p.write_bytes(b'changed')
   with self.assertRaises(ValueError):validate(rec)
   p.unlink();p.write_bytes(b'a')
   with self.assertRaises(ValueError):validate(rec)
 def test_bad_schema_and_missing_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model';p.write_bytes(b'a');rec=snapshot(p)
   with self.assertRaises(ValueError):validate({**rec,'sha256':'unexpected'})
   p.unlink()
   with self.assertRaises(FileNotFoundError):validate(rec)
 def test_relative_and_directory_refused(self):
  with self.assertRaises(ValueError):snapshot('relative')
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):snapshot(d)

if __name__=='__main__':unittest.main()

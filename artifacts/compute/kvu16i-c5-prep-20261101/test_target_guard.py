import json
from pathlib import Path
import tempfile
import unittest
from target_guard import mark_once
class GuardTests(unittest.TestCase):
    def test_once_and_refuse_redraw(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'receipt';mark_once(p,'a'*64,'b'*64)
            self.assertEqual(json.loads(p.read_text())['plan_sha256'],'a'*64)
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):mark_once(p,'a'*64,'b'*64)
    def test_invalid_hash_refuses_before_write(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'receipt'
            with self.assertRaises(ValueError):mark_once(p,'oops','b'*64)
            self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()

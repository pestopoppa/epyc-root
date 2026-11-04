import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import evidence_custody as custody

class EvidenceCustodyTest(unittest.TestCase):
    def test_correct_and_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result'; p.write_bytes(b'{"ok":true}')
            expected=hashlib.sha256(p.read_bytes()).hexdigest()
            raw, digest=custody.read_receipt(p,expected)
            self.assertEqual(raw,b'{"ok":true}'); self.assertEqual(digest,expected)
            with self.assertRaises(ValueError): custody.read_receipt(p,'0'*64)
    def test_reject_symlink_hardlink_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result'; p.write_bytes(b'x')
            link=Path(tmp)/'sym'; link.symlink_to(p)
            with self.assertRaises(OSError): custody.read_receipt(link)
            hard=Path(tmp)/'hard'; os.link(p,hard)
            with self.assertRaises(ValueError): custody.read_receipt(p)
            hard.unlink(); p.write_bytes(b'')
            with self.assertRaises(ValueError): custody.read_receipt(p)
    def test_refuses_path_swap_midread(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result'; p.write_bytes(b'old')
            q=Path(tmp)/'replacement'; q.write_bytes(b'new')
            orig=custody.os.read; first=True
            def swap(fd,n):
                nonlocal first
                data=orig(fd,n)
                if first:
                    first=False; os.replace(q,p)
                return data
            with patch.object(custody.os,'read',side_effect=swap):
                with self.assertRaises(ValueError): custody.read_receipt(p)
    def test_refuses_relative_path(self):
        with self.assertRaises(ValueError): custody.read_receipt('relative')

if __name__=='__main__': unittest.main()

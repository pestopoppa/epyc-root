import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from map_identity import Invalid, verify_snapshot


class MapsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'libllama.so'
        self.path.write_bytes(b'original')
        self.pin = {str(self.path): hashlib.sha256(b'original').hexdigest()}
        self.line = self.mapline()

    def tearDown(self):
        self.tmp.cleanup()

    def mapline(self):
        s = self.path.stat()
        return f'1000-2000 r-xp 00000000 {os.major(s.st_dev):02x}:{os.minor(s.st_dev):02x} {s.st_ino} {self.path}\n'

    def test_valid(self):
        self.assertEqual(len(verify_snapshot([self.line, self.line], self.pin)), 1)

    def test_replaced_same_contents(self):
        replacement = self.path.with_suffix('.tmp')
        replacement.write_bytes(b'original')
        replacement.replace(self.path)
        with self.assertRaises(Invalid): verify_snapshot([self.line], self.pin)

    def test_modified(self):
        self.path.write_bytes(b'changed')
        with self.assertRaises(Invalid): verify_snapshot([self.line], self.pin)

    def test_missing_pin(self):
        with self.assertRaises(Invalid): verify_snapshot([self.line], {})

    def test_deleted(self):
        with self.assertRaises(Invalid): verify_snapshot([self.line.rstrip() + ' (deleted)\n'], self.pin)

    def test_conflicting_inode(self):
        bad = self.line.replace(str(self.path.stat().st_ino), str(self.path.stat().st_ino + 1), 1)
        with self.assertRaises(Invalid): verify_snapshot([self.line, bad], self.pin)

    def test_missing_llama(self):
        with self.assertRaises(Invalid): verify_snapshot([], self.pin)

    def test_symlink_refused(self):
        self.path.unlink()
        target = self.path.parent / 'target'
        target.write_bytes(b'original')
        self.path.symlink_to(target)
        with self.assertRaises(Invalid): verify_snapshot([self.mapline()], self.pin)


if __name__ == '__main__': unittest.main()

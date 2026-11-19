import hashlib
import tempfile
import unittest
from pathlib import Path

from native_files import validate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class NativeFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'out'
        self.attempt = self.root / ('attempt-' + 'a' * 32)
        self.attempt.mkdir(parents=True)
        self.files = {}
        for name in ('test.log', 'config.json', 'witness.json'):
            p = self.attempt / name
            p.write_text(name)
            self.files[str(p)] = digest(p)

    def test_valid(self):
        validate(self.files, self.root, digest)

    def test_empty_missing_extra_and_invalid_hash_refused(self):
        for files in ({}, dict(list(self.files.items())[:2]),
                      {**self.files, str(self.attempt/'extra'): '0'*64},
                      {**self.files, str(self.attempt/'test.log'): 'bad'}):
            with self.subTest(files=files), self.assertRaises(ValueError):
                validate(files, self.root, digest)

    def test_modified_and_missing_file_refused(self):
        path = self.attempt/'test.log'
        path.write_text('changed')
        with self.assertRaises(ValueError): validate(self.files, self.root, digest)
        path.unlink()
        with self.assertRaises((ValueError, OSError)): validate(self.files, self.root, digest)

    def test_symlink_and_outside_refused(self):
        path = self.attempt/'test.log'
        path.unlink()
        path.symlink_to(self.attempt/'config.json')
        with self.assertRaises(ValueError): validate(self.files, self.root, digest)
        outside = Path(self.tmp.name)/'test.log'
        outside.write_text('test.log')
        bindings = dict(self.files)
        bindings.pop(str(path)); bindings[str(outside)] = digest(outside)
        with self.assertRaises(ValueError): validate(bindings, self.root, digest)

    def test_mixed_attempts_and_nonregular_refused(self):
        other = self.root/('attempt-' + 'b'*32)
        other.mkdir()
        path = other/'witness.json'; path.write_text('witness.json')
        bindings = dict(self.files)
        bindings.pop(str(self.attempt/'witness.json')); bindings[str(path)] = digest(path)
        with self.assertRaises(ValueError): validate(bindings, self.root, digest)
        p = self.attempt/'test.log'; p.unlink(); p.mkdir()
        with self.assertRaises(ValueError): validate(self.files, self.root, digest)


if __name__ == '__main__':
    unittest.main()

import hashlib
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path


VERIFY_MODULE = Path('/mnt/raid0/llm/worktrees/mains/h-autokernel-cross-workload-keep-gate/scripts/coordination/inf75/quantizer_build/verify_source.py')
spec = importlib.util.spec_from_file_location('verify_source', VERIFY_MODULE)
verify_source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_source)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VerifySourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'source'
        self.root.mkdir()
        (self.root / 'src').mkdir()
        (self.root / 'src/kernel.cpp').write_bytes(b'kernel source\n')
        (self.root / 'include.h').write_bytes(b'header\n')
        (self.root / 'kernel-link').symlink_to('src/kernel.cpp')
        self.manifest = self.base / 'SOURCE-SHA256SUMS'
        self.write_manifest()

    def write_manifest(self):
        entries = []
        for path in self.root.rglob('*'):
            rel = path.relative_to(self.root).as_posix()
            mode = stat.S_IMODE(path.lstat().st_mode)
            if path.is_symlink():
                entries.append([rel, 'symlink', os.readlink(path)])
            elif path.is_dir():
                entries.append([rel, 'dir', mode])
            else:
                entries.append([rel, 'file', sha256(path), mode])
        self.manifest.write_text(json.dumps(sorted(entries, key=lambda row: row[0]),
                                            separators=(',', ':')) + '\n')
        self.expected = sha256(self.manifest)

    def verify(self):
        return verify_source.verify(self.root, self.manifest, self.expected)

    def test_matching_manifest_verifies(self):
        self.assertIsNone(self.verify())

    def test_tampered_source_file_refuses(self):
        (self.root / 'src/kernel.cpp').write_bytes(b'tampered\n')
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_manifested_file_refuses(self):
        (self.root / 'include.h').unlink()
        with self.assertRaises(ValueError):
            self.verify()

    def test_added_unmanifested_file_refuses(self):
        (self.root / 'extra.cpp').write_bytes(b'unmanifested\n')
        with self.assertRaises(ValueError):
            self.verify()

    def test_mode_change_refuses(self):
        path = self.root / 'src/kernel.cpp'
        path.chmod(stat.S_IMODE(path.stat().st_mode) ^ stat.S_IXUSR)
        with self.assertRaises(ValueError):
            self.verify()

    def test_symlink_target_change_refuses(self):
        link = self.root / 'kernel-link'
        link.unlink()
        link.symlink_to('include.h')
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == '__main__':
    unittest.main()

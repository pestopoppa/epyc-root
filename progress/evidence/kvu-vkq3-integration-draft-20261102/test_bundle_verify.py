"""Model-free tests; trusted pins here are synthetic test fixtures only."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import bundle_verify as bv


class BundleVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'bundle'
        self.root.mkdir()
        self.pins = {}
        for rel in bv._NAMES:
            path = self.root / rel
            path.parent.mkdir(exist_ok=True)
            payload = ('synthetic:' + rel).encode()
            path.write_bytes(payload)
            self.pins[rel] = hashlib.sha256(payload).hexdigest()
        self.manifest = self.root / 'bundle-manifest.json'
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps({'schema': 'kvu-diagnostic-bundle-v1', 'files': self.pins}))

    def test_valid_and_file_tampering(self):
        bv.verify_bundle(self.root, self.pins)
        (self.root / 'launcher/worker_draft.py').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            bv.verify_bundle(self.root, self.pins)

    def test_manifest_and_pin_tampering(self):
        bad = dict(self.pins)
        bad.pop(next(iter(bad)))
        with self.assertRaisesRegex(ValueError, 'exactly cover'):
            bv.verify_bundle(self.root, bad)
        self.manifest.write_text('{"schema":"kvu-diagnostic-bundle-v1","files":{},"files":{}}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            bv.verify_bundle(self.root, self.pins)
        self.manifest.write_text('{')
        with self.assertRaisesRegex(ValueError, 'invalid manifest'):
            bv.verify_bundle(self.root, self.pins)
        self.write_manifest()
        record = json.loads(self.manifest.read_text())
        record['files']['launcher/worker_draft.py'] = '0' * 64
        self.manifest.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'manifest does not match'):
            bv.verify_bundle(self.root, self.pins)

    def test_symlink_member_is_rejected(self):
        member = self.root / 'launcher/worker_draft.py'
        member.unlink()
        member.symlink_to('/etc/passwd')
        with self.assertRaises(OSError):
            bv.verify_bundle(self.root, self.pins)

    def test_directory_symlink_is_rejected(self):
        directory = self.root / 'kvu-vkq3-guard-review-20261102'
        (directory / 'guard.py').unlink()
        directory.rmdir()
        directory.symlink_to(self.root / 'launcher', target_is_directory=True)
        with self.assertRaises(OSError):
            bv.verify_bundle(self.root, self.pins)

    def test_unpinned_entries_and_bytecode_are_rejected(self):
        for rel in ('extra.py', 'launcher/extra.py', 'launcher/__pycache__',
                    'kvu-vkq3-guard-review-20261102/guard.pyc'):
            with self.subTest(rel=rel):
                extra = self.root / rel
                if rel.endswith('__pycache__'):
                    extra.mkdir()
                    (extra / 'worker_draft.cpython-311.pyc').write_bytes(b'bytecode')
                else:
                    extra.write_bytes(b'unpinned')
                with self.assertRaisesRegex(ValueError, 'unexpected or missing bundle'):
                    bv.verify_bundle(self.root, self.pins)
                if extra.is_dir():
                    (extra / 'worker_draft.cpython-311.pyc').unlink()
                    extra.rmdir()
                else:
                    extra.unlink()

    def test_missing_member_is_rejected(self):
        (self.root / 'launcher/worker_draft.py').unlink()
        with self.assertRaisesRegex(ValueError, 'unexpected or missing bundle'):
            bv.verify_bundle(self.root, self.pins)


if __name__ == '__main__':
    unittest.main()

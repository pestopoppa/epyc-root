import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import verify_pair


class PairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = verify_pair.ORACLE.EXPECTED
        for name in ('before.bin', 'after.bin'):
            (self.root / name).write_bytes(self.original)
        sha = hashlib.sha256(self.original).hexdigest()
        self.manifest = {'schema': 'kpf60.fixture-blob-pair.v1',
                         'baseline': {'file': 'before.bin', 'sha256': sha},
                         'observed': {'file': 'after.bin', 'sha256': sha}}

    def test_match_uses_two_separate_captures(self):
        result = verify_pair.verify(self.root, self.manifest)
        self.assertEqual(result['status'], 'MATCH')
        self.assertTrue(result['arms_identical'])
        self.assertEqual(result['arm_results']['baseline']['size_bytes'], 152)

    def test_changed_data_is_mismatch_if_original_digest_matches(self):
        altered = bytearray(self.original)
        altered[20] ^= 1
        (self.root / 'after.bin').write_bytes(altered)
        self.manifest['observed']['sha256'] = hashlib.sha256(altered).hexdigest()
        result = verify_pair.verify(self.root, self.manifest)
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertFalse(result['arms_identical'])

    def test_two_equal_but_wrong_blobs_are_not_a_pass(self):
        altered = bytearray(self.original)
        altered[30] ^= 1
        for arm in ('baseline', 'observed'):
            (self.root / self.manifest[arm]['file']).write_bytes(altered)
            self.manifest[arm]['sha256'] = hashlib.sha256(altered).hexdigest()
        result = verify_pair.verify(self.root, self.manifest)
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertTrue(result['arms_identical'])

    def test_refuses_tampering_aliasing_and_unsafe_paths(self):
        (self.root / 'after.bin').write_bytes(self.original[:-1])
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            verify_pair.verify(self.root, self.manifest)
        (self.root / 'after.bin').unlink()
        os.link(self.root / 'before.bin', self.root / 'after.bin')
        with self.assertRaisesRegex(ValueError, 'separately captured'):
            verify_pair.verify(self.root, self.manifest)
        (self.root / 'after.bin').unlink()
        (self.root / 'after.bin').symlink_to(self.root / 'before.bin')
        with self.assertRaises(OSError):
            verify_pair.verify(self.root, self.manifest)
        bad = copy.deepcopy(self.manifest)
        bad['observed']['file'] = '../outside'
        with self.assertRaisesRegex(ValueError, 'single filename'):
            verify_pair.verify(self.root, bad)

    def test_cli_refuses_missing_and_extra_fields(self):
        path = self.root / 'manifest.json'
        self.manifest['unexpected'] = True
        path.write_text(json.dumps(self.manifest))
        cmd = [sys.executable, str(Path(verify_pair.__file__)), str(self.root), str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'INVALID')


if __name__ == '__main__':
    unittest.main()

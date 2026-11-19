import hashlib
from pathlib import Path
import tempfile
import unittest

from runtime_manifest import REQUIRED, verify_runtime_manifest


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RuntimeManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'bin').mkdir()
        for name in REQUIRED:
            (self.root / name).write_bytes(name.encode())
        self.manifest = ''.join(f'{sha(name.encode())}  {name}\n' for name in sorted(REQUIRED)).encode()
        (self.root / 'SHA256SUMS').write_bytes(self.manifest)
        self.pin = sha(self.manifest)

    def tearDown(self):
        self.temp.cleanup()

    def test_accepts_exact_pinned_artifacts(self):
        result = verify_runtime_manifest(self.root, self.pin)
        self.assertEqual(set(result['artifacts']), REQUIRED)
        self.assertEqual(result['artifacts']['bin/llama-server'], sha(b'bin/llama-server'))

    def test_rejects_manifest_or_artifact_tampering(self):
        with self.assertRaisesRegex(ValueError, 'manifest digest mismatch'):
            verify_runtime_manifest(self.root, '0' * 64)
        (self.root / 'bin/llama-server').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'artifact digest mismatch'):
            verify_runtime_manifest(self.root, self.pin)

    def test_rejects_symlinked_artifact(self):
        artifact = self.root / 'bin/llama-server'
        artifact.unlink()
        artifact.symlink_to(self.root / 'bin/libggml.so.0.16.0')
        with self.assertRaises(ValueError):
            verify_runtime_manifest(self.root, self.pin)

    def test_rejects_missing_or_duplicate_manifest_entry(self):
        lines = self.manifest.splitlines(keepends=True)
        for data in (b''.join(lines[1:]), self.manifest + lines[0]):
            (self.root / 'SHA256SUMS').write_bytes(data)
            with self.assertRaises(ValueError):
                verify_runtime_manifest(self.root, sha(data))


if __name__ == '__main__':
    unittest.main()

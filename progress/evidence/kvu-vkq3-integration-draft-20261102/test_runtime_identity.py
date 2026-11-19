import hashlib
import tempfile
import unittest
from pathlib import Path
from runtime_identity import verify_runtime

class TestRuntimeIdentity(unittest.TestCase):
    def test_valid_then_tampered(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'tool'
            p.write_bytes(b'original')
            pins = {'tool': hashlib.sha256(b'original').hexdigest()}
            self.assertEqual(verify_runtime(d, pins), pins)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                verify_runtime(d, pins)

    def test_missing_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                verify_runtime(d, {'tool': '0' * 64})
            (Path(d) / 'target').write_bytes(b'x')
            (Path(d) / 'tool').symlink_to('target')
            with self.assertRaises(OSError):
                verify_runtime(d, {'tool': hashlib.sha256(b'x').hexdigest()})

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            verify_runtime('/tmp', {'../tool': '0' * 64})

if __name__ == '__main__':
    unittest.main()

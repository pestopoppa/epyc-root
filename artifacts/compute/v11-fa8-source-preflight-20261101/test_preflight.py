import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

p = Path(__file__).with_name('preflight.py')
spec = importlib.util.spec_from_file_location('fa8_preflight', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SourcePreflightTests(unittest.TestCase):
    def test_real_source_objects(self):
        repo = Path('/mnt/raid0/llm/llama.cpp')
        if not repo.exists():
            self.skipTest('canonical object database unavailable')
        for arm in m.ARMS.values():
            result = m.inspect(repo, arm)
            self.assertEqual(result['commit'], arm['commit'])

    def test_bad_expected_source_hash_is_refused(self):
        repo = Path('/mnt/raid0/llm/llama.cpp')
        if not repo.exists():
            self.skipTest('canonical object database unavailable')
        bad = copy.deepcopy(m.ARMS['A'])
        bad['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            m.inspect(repo, bad)

    def test_bad_anchor_is_refused(self):
        repo = Path('/mnt/raid0/llm/llama.cpp')
        if not repo.exists():
            self.skipTest('canonical object database unavailable')
        bad = copy.deepcopy(m.ARMS['C'])
        bad['anchors'] = ('definitely_not_a_kernel_identifier_xyz',)
        with self.assertRaisesRegex(ValueError, 'anchor missing'):
            m.inspect(repo, bad)

    def test_invalid_repository_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.subprocess.CalledProcessError):
                m.inspect(Path(d), m.ARMS['A'])


if __name__ == '__main__':
    unittest.main()

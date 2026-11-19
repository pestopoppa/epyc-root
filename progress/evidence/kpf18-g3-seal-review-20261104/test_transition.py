import tempfile
import unittest
from pathlib import Path
import transition as t


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.joinpath('driver.py').write_bytes(b'new')
        self.root.joinpath('unchanged.py').write_bytes(b'good')
        self.root.joinpath('helper.py').write_bytes(b'helper')
        self.manifest = (t.digest(b'old') + '  driver.py\n' + t.digest(b'good') + '  unchanged.py\n').encode()
        self.root.joinpath('SOURCES.sha256').write_bytes(self.manifest)
        self.sha = t.digest(self.manifest)
        self.replacements = {'driver.py': (t.digest(b'old'), t.digest(b'new'))}
        self.helpers = {'helper.py': t.digest(b'helper')}

    def run_transition(self):
        return t.transition(self.root, self.sha, self.replacements, self.helpers)

    def test_transition_contains_only_expected_entries(self):
        result = self.run_transition().decode()
        self.assertEqual(len(result.splitlines()), 3)
        self.assertIn(t.digest(b'new') + '  driver.py', result)

    def test_manifest_and_each_source_must_remain_exact(self):
        for name in ('SOURCES.sha256', 'driver.py', 'unchanged.py', 'helper.py'):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b'x')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.run_transition()
            path.write_bytes(original)

    def test_refuses_symlink(self):
        (self.root/'helper.py').unlink()
        (self.root/'helper.py').symlink_to(self.root/'unchanged.py')
        with self.assertRaises(ValueError):
            self.run_transition()

    def test_refuses_baseline_mismatch_and_duplicate_helper(self):
        self.replacements['driver.py'] = (t.digest(b'wrong'), t.digest(b'new'))
        with self.assertRaises(ValueError):
            self.run_transition()
        self.replacements['driver.py'] = (t.digest(b'old'), t.digest(b'new'))
        self.helpers['unchanged.py'] = t.digest(b'good')
        with self.assertRaises(ValueError):
            self.run_transition()

    def test_refuses_duplicate_and_traversal_manifest_entries(self):
        for bad in (self.manifest + self.manifest.splitlines(keepends=True)[0],
                    self.manifest + (t.digest(b'x') + '  ../escape\n').encode()):
            self.root.joinpath('SOURCES.sha256').write_bytes(bad)
            self.sha = t.digest(bad)
            with self.assertRaises(ValueError):
                self.run_transition()


if __name__ == '__main__':
    unittest.main()

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE))
from prepare_successor import prepare


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SuccessorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.native = self.root / 'native'
        self.native.write_text('bound bytes')
        self.manifest = self.root / 'manifest'
        self.manifest.write_text(f'{digest(self.native)}  {self.native}\n')
        self.mapping = self.root / 'mapping.json'
        self.mapping.write_text('{}')
        self.launcher = self.root / 'original-launch.sh'
        self.launcher.write_text('#!/bin/bash\nexit 78\nunset PYTHONHOME PYTHONPATH\ntouch SHOULD_NEVER_EXIST\n')
        self.out = self.root / 'successor'

    def make(self, **kwargs):
        return prepare(self.manifest, self.mapping, self.launcher, self.out,
                       kwargs.get('manifest_sha', digest(self.manifest)), digest(self.launcher))

    def run_entry(self, *args):
        return subprocess.run(['bash', str(self.out / 'launch.sh'), *args],
                              cwd=self.root, capture_output=True, text=True)

    def test_integrates_and_keeps_runtime_disabled(self):
        before = self.launcher.read_bytes()
        result = self.make()
        self.assertEqual(result['native_entries'], 1)
        self.assertEqual(self.launcher.read_bytes(), before)
        self.assertEqual((self.out / 'predecessor-launch.sh.disabled').read_bytes(), before)
        self.assertEqual(self.run_entry('custody-check').returncode, 0)
        self.assertEqual(self.run_entry().returncode, 78)
        self.assertEqual(self.run_entry('normal').returncode, 78)
        self.assertFalse((self.root / 'SHOULD_NEVER_EXIST').exists())

    def test_native_drift_refuses_before_runtime(self):
        self.make()
        self.native.write_text('changed')
        result = self.run_entry('custody-check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('file digest mismatch', result.stderr)

    def test_inventory_or_tool_drift_refuses(self):
        for name in ('expected-paths.json', 'verify_manifest.py', 'rebinding.json',
                     'predecessor-launch.sh.disabled', 'SUCCESSOR-SOURCES.sha256'):
            with self.subTest(name=name):
                if self.out.exists():
                    import shutil
                    shutil.rmtree(self.out)
                self.make()
                with (self.out / name).open('a') as stream:
                    stream.write('tamper')
                self.assertNotEqual(self.run_entry('custody-check').returncode, 0)

    def test_wrong_pin_or_existing_destination_refuses(self):
        with self.assertRaises(ValueError):
            self.make(manifest_sha='0' * 64)
        self.assertFalse(self.out.exists())
        self.make()
        with self.assertRaises(FileExistsError):
            self.make()

    def test_failed_rebinding_retains_incomplete_barrier(self):
        self.native.write_text('drift')
        with self.assertRaises(ValueError):
            self.make()
        self.assertTrue((self.out / 'INCOMPLETE').exists())
        self.assertFalse((self.out / 'launch.sh').exists())

    def test_rebinds_only_equal_bytes(self):
        copied = self.root / 'retained'
        copied.write_bytes(self.native.read_bytes())
        self.mapping.write_text(json.dumps({str(self.native): str(copied)}))
        self.make()
        self.native.unlink()
        self.assertEqual(self.run_entry('custody-check').returncode, 0)


if __name__ == '__main__':
    unittest.main()

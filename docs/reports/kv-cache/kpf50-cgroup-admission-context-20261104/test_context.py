import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import context


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'cgroup.procs').write_text('')
        self.mount = f'7 1 0:3 / {self.root} rw,nosuid - cgroup2 cgroup rw\n'

    def test_nonwritable_zero_cap_still_refuses(self):
        with patch('context.os.access', return_value=False):
            result = context.inspect(self.root, mountinfo=self.mount, status='CapEff:\t0\n', pid=42)
        self.assertFalse(result.admitted)
        self.assertEqual((result.pid, result.mount_id, result.cap_eff, result.target_writable), (42, 7, 0, False))
        self.assertIn('alternate groups', result.reasons[-1])

    def test_writable_and_capabilities_are_disclosed(self):
        with patch('context.os.access', return_value=True):
            result = context.inspect(self.root, mountinfo=self.mount, status='CapEff:\t10\n')
        self.assertFalse(result.admitted)
        self.assertTrue(any('can write' in x for x in result.reasons))
        self.assertTrue(any('capabilities' in x for x in result.reasons))

    def test_multiple_mounts_and_missing_capabilities_refuse(self):
        for mounts, status in ((self.mount + self.mount, 'CapEff:\t0\n'), (self.mount, '')):
            result = context.inspect(self.root, mountinfo=mounts, status=status)
            self.assertFalse(result.admitted)
            self.assertTrue(any('context unavailable' in x for x in result.reasons))

    def test_symlink_or_nonregular_procs_refuses(self):
        link = self.root.parent / (self.root.name + '-link')
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)
        self.assertFalse(context.inspect(link, mountinfo=self.mount, status='CapEff:\t0\n').admitted)
        (self.root / 'cgroup.procs').unlink()
        (self.root / 'cgroup.procs').symlink_to('/dev/null')
        self.assertFalse(context.inspect(self.root, mountinfo=self.mount, status='CapEff:\t0\n').admitted)

    def test_escaped_or_malformed_mount_refuses(self):
        for raw in ('7 1 0:3 / /bad\\040path rw - cgroup2 cgroup rw\n', 'bad'):
            self.assertFalse(context.inspect(self.root, mountinfo=raw, status='CapEff:\t0\n').admitted)


if __name__ == '__main__':
    unittest.main()

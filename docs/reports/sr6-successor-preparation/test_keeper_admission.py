import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from keeper_admission import KeeperAdmission


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


class KeeperAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.grant, self.stop = root/'row-1.grant', root/'stop'
        self.start, self.end = 1800000000, 1800003600
        self.grant.write_text(f'regions=q0 start={stamp(self.start)} end={stamp(self.end)} holds=q0\n')
        self.env = {'FILLER_ID':'row-1', 'FILLER_END':str(self.end),
                    'FILLER_DEADLINE':str(self.end-90), 'FILLER_STOPFILE':str(self.stop)}
        self.kw = dict(env=self.env, row_id='row-1', grant_path=self.grant,
                       stop_path=self.stop, ownership_check=lambda: True)

    def test_window_stop_and_ownership(self):
        guard = KeeperAdmission(**self.kw)
        with patch('keeper_admission.time.time', return_value=self.start + 1):
            self.assertTrue(guard())
            self.stop.touch(); self.assertFalse(guard()); self.stop.unlink()
            guard.ownership_check = lambda: False
            self.assertFalse(guard())
        guard.ownership_check = lambda: True
        for now in (self.start-1, self.end-90, self.end):
            with patch('keeper_admission.time.time', return_value=now):
                self.assertFalse(guard())

    def test_reject_changed_grant_and_dangling_stop_link(self):
        guard = KeeperAdmission(**self.kw)
        with patch('keeper_admission.time.time', return_value=self.start + 1):
            self.stop.symlink_to(self.stop.parent/'missing')
            self.assertFalse(guard()); self.stop.unlink()
            self.grant.write_text(self.grant.read_text() + 'changed=x\n')
            self.assertFalse(guard())

    def test_reject_unbound_and_malformed(self):
        for key, val in [('FILLER_ID','other'), ('FILLER_END',str(self.end+60)),
                         ('FILLER_DEADLINE',str(self.end)), ('FILLER_STOPFILE','/other')]:
            bad = dict(self.env, **{key:val})
            with self.subTest(key=key), self.assertRaises(ValueError):
                KeeperAdmission(**dict(self.kw, env=bad))
        self.grant.write_text(self.grant.read_text()+'end=x\n')
        with self.assertRaises(ValueError): KeeperAdmission(**self.kw)
        with self.assertRaises(ValueError): KeeperAdmission(**dict(self.kw, ownership_check=None))

    def test_ownership_exception_refuses(self):
        def fail(): raise RuntimeError('claim missing')
        guard = KeeperAdmission(**dict(self.kw, ownership_check=fail))
        with patch('keeper_admission.time.time', return_value=self.start+1):
            self.assertFalse(guard())


if __name__ == '__main__': unittest.main()

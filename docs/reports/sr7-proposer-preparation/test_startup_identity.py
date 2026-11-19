import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from contained_lifecycle import SmokeAdmission
from startup_identity import StartupIdentity

class StartupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.admission = MagicMock(return_value=True)
        self.admission.deadline = time.time() + 30
        self.admission.stop_path = Path(self.tmp.name) / 'STOP'
        self.process = MagicMock(pid=123)
        self.process.poll.return_value = None
        self.v = StartupIdentity.__new__(StartupIdentity)
        self.v.timeout_s = 1
        self.v.admission = self.admission

    def test_readiness_retry_and_success(self):
        with patch.object(self.v, '_check', side_effect=[ValueError('loading'), {'ok':True}]) as check:
            self.assertEqual(self.v(self.process, 9999), {'ok':True})
            self.assertEqual(check.call_count, 2)

    def test_stop_interrupts_blocked_verification(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(*a):
            entered.set()
            release.wait(2)
            return {'ok':True}
        self.addCleanup(release.set)
        def stop():
            entered.wait(1)
            self.admission.stop_path.touch()
        threading.Thread(target=stop, daemon=True).start()
        start = time.monotonic()
        with patch.object(self.v, '_check', side_effect=blocked):
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                self.v(self.process, 9999)
        self.assertLess(time.monotonic() - start, 0.7)

    def test_deadline_interrupts_blocked_admission(self):
        self.v.timeout_s = 0.2
        release = threading.Event()
        self.addCleanup(release.set)
        self.admission.side_effect = lambda: release.wait(2)
        start = time.monotonic()
        with self.assertRaisesRegex(ValueError, 'deadline'):
            self.v(self.process, 9999)
        self.assertLess(time.monotonic() - start, 0.7)

    def test_smoke_requires_dry_run_and_four_cpu_affinity(self):
        stop = Path(self.tmp.name) / 'stop'
        with patch.dict(os.environ, {'FILLER_DRYRUN':'1'}), patch('os.sched_getaffinity', return_value={1, 2, 3, 4}):
            a = SmokeAdmission(stop_path=stop, deadline=time.time()+30)
            self.assertTrue(a())
            stop.touch()
            self.assertFalse(a())
        with patch.dict(os.environ, {'FILLER_DRYRUN':'1'}), patch('os.sched_getaffinity', return_value=set(range(5))):
            with self.assertRaises(ValueError):
                SmokeAdmission(stop_path=stop, deadline=time.time()+30)

if __name__ == '__main__':
    unittest.main()

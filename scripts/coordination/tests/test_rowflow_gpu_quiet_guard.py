#!/usr/bin/env python3
"""Guard port (operator 2026-11-07): the frozen keeper's publish refuses a row whose launcher/job.py needs an exclusive
GPU-quiet ancestor unless the row books the GPU. Incident fixture: c6-w3-halfb-census-20261105 (rc1, 6 s after grant)."""
import os
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402

INCIDENT = "raise ValueError('exclusive GPU-quiet ancestor required for canonical hosting SMT')\n"


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="gqg-")
        self.l = os.path.join(self.d, "launch.sh")
        open(self.l, "w").write("#!/bin/sh\nexec python3 job.py\n")
        self.job = os.path.join(self.d, "job.py")
        open(self.job, "w").write(INCIDENT)
        self.spec = {"id": "c6-w3-halfb-census-20261105", "launcher": self.l, "lane": "cpu"}

    def test_incident_refused_and_names_fix(self):
        e = pr.gpu_quiet_guard_conflicts(self.spec, info={"class": "cpu"})
        self.assertTrue(e)
        self.assertIn("FIX:", e[0])
        self.assertIn("--gpu-quiet exclusive", e[0])

    def test_lint_replay_refuses(self):
        with self.assertRaises(rf.Refused) as cm:
            pr.lint(dict(self.spec))
        self.assertIn("GPU-quiet ancestor", str(cm.exception))

    def test_gpu_booking_admitted(self):
        for s in (dict(self.spec, gpu="exclusive"), dict(self.spec, gpu="quiet"), dict(self.spec, quiet=True), dict(self.spec, lane="gpu")):
            self.assertEqual(pr.gpu_quiet_guard_conflicts(s, info={"class": "cpu"}), [])
        self.assertEqual(pr.gpu_quiet_guard_conflicts(self.spec, info={"class": "cpu+gpu"}), [])

    def test_negative_control_no_guard_text(self):
        open(self.job, "w").write("print('no guard')\n")
        self.assertEqual(pr.gpu_quiet_guard_conflicts(self.spec, info={"class": "cpu"}), [])

    def test_unreadable_never_blocks(self):
        self.assertEqual(pr.gpu_quiet_guard_conflicts(dict(self.spec, launcher="/nonexistent/x.sh"), info={"class": "cpu"}), [])


if __name__ == "__main__":
    unittest.main()

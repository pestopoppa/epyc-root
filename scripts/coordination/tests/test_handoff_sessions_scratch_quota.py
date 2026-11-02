"""ws58 2026-11-02 scratch leak: worktree-not-copy prompt line + deterministic 10 GiB scratch quota (no auto-delete)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import handoff_sessions as hs  # noqa: E402


class ScratchQuota(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        self.tmp = tempfile.mkdtemp()
        self.old = hs.TMP_ROOT
        hs.TMP_ROOT = self.tmp
        os.makedirs(os.path.join(self.tmp, "demo", "r225-v8-work"))

    def tearDown(self):
        hs.TMP_ROOT = self.old

    def test_brief_carries_worktree_line(self):
        self.assertIn("git worktree add --detach", hs.brief_text("demo", {"handoff": "h.md"}, self.flags))

    def test_over_quota_leads_nudge_logs_and_deletes_nothing(self):
        e, root = {}, os.path.join(self.tmp, "demo")
        lead = hs.scratch_lead(self.flags, "demo", e, now=1000.0, du=lambda p: 25.5)
        self.assertTrue(lead.startswith(f"FIRST: your scratch {root} is 25.5 GiB: delete superseded"))
        self.assertTrue(os.path.isdir(os.path.join(root, "r225-v8-work")))
        logs = open(os.path.join(self.flags, "handoff-sessions.log")).read() if os.path.exists(
            os.path.join(self.flags, "handoff-sessions.log")) else "".join(
            open(os.path.join(self.flags, f)).read() for f in os.listdir(self.flags) if f.endswith(".log"))
        self.assertIn("SCRATCH-OVER demo", logs)
        calls = []
        hs.scratch_lead(self.flags, "demo", e, now=1300.0, du=lambda p: calls.append(p) or 1.0)
        self.assertEqual(calls, [])  # cached: du at most every 10 min
        self.assertEqual(hs.scratch_lead(self.flags, "demo", e, now=1700.0, du=lambda p: 2.0), "")

    def test_under_quota_is_silent(self):
        self.assertEqual(hs.scratch_lead(self.flags, "demo", {}, now=1.0, du=lambda p: 3.0), "")


if __name__ == "__main__":
    unittest.main()

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

    def test_copy_is_flagged_and_leads_but_worktree_is_not(self):
        import subprocess
        root = os.path.join(self.tmp, "demo")
        cp = os.path.join(root, "attempt2", "epyc-root")
        for d in ("scripts", "handoffs"):
            os.makedirs(os.path.join(cp, d))
        open(os.path.join(cp, "CLAUDE.md"), "w").close()
        clone = os.path.join(root, "clone")
        subprocess.run(["git", "init", "-q", clone], check=True)
        repo = os.path.join(self.tmp, "repo")
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
        subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "s"], check=True)
        wt = os.path.join(root, "wt")
        subprocess.run(["git", "-C", repo, "worktree", "add", "-q", "--detach", wt], check=True)
        for d in ("scripts", "handoffs"):
            os.makedirs(os.path.join(wt, d))
        open(os.path.join(wt, "CLAUDE.md"), "w").close()
        self.assertEqual(sorted(hs.find_copies(root)), sorted([cp, clone]))
        e = {}
        lead = hs.scratch_lead(self.flags, "demo", e, now=5000.0, du=lambda p: 2.0)
        self.assertTrue(lead.startswith("FIRST: delete the checkout copy "), lead)
        self.assertIn("use `git worktree add --detach` instead", lead)
        self.assertNotIn(wt + " ", lead)
        logs = "".join(open(os.path.join(self.flags, f)).read() for f in os.listdir(self.flags) if f.endswith(".log"))
        self.assertIn(f"SCRATCH-COPY {cp} 2.0 GiB", logs)
        self.assertTrue(os.path.isdir(cp))  # flagged, never deleted

    def test_done_cleanup_uses_declared_scratch_or_default(self):
        repo = os.path.join(self.tmp, "repo2")
        os.makedirs(os.path.join(repo, "handoffs", "completed"))
        with open(os.path.join(repo, "handoffs", "completed", "h.md"), "w") as fh:
            fh.write("# h\n**Scratch**: /mnt/raid0/llm/tmp/h/ · worktrees: /mnt/raid0/llm/worktrees/h-*\n")
        self.assertEqual(hs.scratch_cleanup_args("demo", {"handoff": "handoffs/active/h.md"}, repo),
                         ["--handoff", os.path.join(repo, "handoffs", "completed", "h.md")])
        self.assertEqual(hs.scratch_cleanup_args("demo", {"handoff": "handoffs/active/none.md"}, repo),
                         ["--root", os.path.join(self.tmp, "demo"), "--worktree-glob", "/mnt/raid0/llm/worktrees/demo-*"])
        calls = []

        class R:
            returncode, stdout, stderr = 0, "x\n1 entry under ...; 0 kept\n", ""
        hs.cleanup_scratch(self.flags, "demo", {"handoff": "handoffs/active/none.md"}, repo,
                           run=lambda argv, **k: calls.append(argv) or R())
        self.assertEqual(calls[0][1:3], [os.path.join(repo, hs.SCRATCH_CLEANUP), "apply"])
        hs.cleanup_scratch(self.flags, "demo", {}, repo, run=lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
        logs = "".join(open(os.path.join(self.flags, f)).read() for f in os.listdir(self.flags) if f.endswith(".log"))
        self.assertIn("SCRATCH-CLEANUP demo rc=0", logs)
        self.assertIn("SCRATCH-CLEANUP demo FAILED", logs)

    def test_under_quota_is_silent(self):
        self.assertEqual(hs.scratch_lead(self.flags, "demo", {}, now=1.0, du=lambda p: 3.0), "")


if __name__ == "__main__":
    unittest.main()

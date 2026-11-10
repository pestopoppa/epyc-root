"""scratch-lease Phase 1 (operator-directed scratch-leak structural fix, 2026-11-04). Temp dirs only:
nothing here touches /mnt/raid0/llm/tmp, the real lease dir, or runs a reaper."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS = os.path.join(ROOT, "scripts", "system")
sys.path.insert(0, SYS)
import scratch_lease as sl  # noqa: E402
import scratch_cleanup as sc  # noqa: E402
import worktree_gate as wg  # noqa: E402

KEEPER = os.path.join(ROOT, "scripts", "coordination", "rowflow", "ws58-calendar-keeper-v13.sh")


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.td.name, "tmp")
        self.ldir = os.path.join(self.td.name, "leases")
        os.makedirs(self.root)
        self._env = os.environ.get("SCRATCH_LEASE_DIR")
        os.environ["SCRATCH_LEASE_DIR"] = self.ldir
        self.now = time.time()

    def tearDown(self):
        if self._env is None:
            os.environ.pop("SCRATCH_LEASE_DIR", None)
        else:
            os.environ["SCRATCH_LEASE_DIR"] = self._env
        self.td.cleanup()

    def marked(self, name, text="KEEP: Marked by workspace-58 2026-10-25."):
        d = os.path.join(self.root, name)
        os.makedirs(d)
        with open(os.path.join(d, "KEEP"), "w") as f:
            f.write(text)
        with open(os.path.join(d, "big.bin"), "wb") as f:
            f.write(b"x" * 1000)
        return d

    def lease(self, d, expires_in):
        sl.write_lease({"schema": sl.SCHEMA, "owner": "t", "target": os.path.realpath(d),
                        "handoff_or_row": None, "created": sl._iso(self.now),
                        "expires": sl._iso(self.now + expires_in), "budget_gib": 0, "reason": "test"})


class LeaseSemantics(Base):
    def test_unexpired_lease_retains(self):
        d = self.marked("a"); self.lease(d, 3600)
        self.assertTrue(sl.is_retained(d, self.now))
        self.assertTrue(sl.marker_blocks(d, self.now))
        self.assertIsNotNone(sc._keep_marker(d))

    def test_expired_lease_releases(self):
        d = self.marked("b"); self.lease(d, -3600)
        self.assertFalse(sl.is_retained(d, self.now))
        self.assertFalse(sl.marker_blocks(d, self.now))
        self.assertIsNone(sc._keep_marker(d))

    def test_marker_without_lease_retains(self):
        d = self.marked("c")
        self.assertIsNone(sl.read_lease(d))
        self.assertFalse(sl.is_retained(d, self.now))      # no lease => is_retained false ...
        self.assertTrue(sl.marker_blocks(d, self.now))     # ... but the legacy marker still blocks
        self.assertIsNotNone(sc._keep_marker(d))

    def test_malformed_lease_fails_closed(self):
        d = self.marked("m")
        os.makedirs(self.ldir, exist_ok=True)
        with open(sl.lease_path(d), "w") as f:
            f.write("{not json")
        self.assertTrue(sl.marker_blocks(d, self.now))

    def test_sibling_marker_expired(self):
        d = os.path.join(self.root, "s"); os.makedirs(d)
        open(d + ".epyc-keep", "w").close()
        self.assertIsNotNone(sc._keep_marker(d))
        self.lease(d, -1)
        self.assertIsNone(sc._keep_marker(d))

    def test_worktree_gate_protected_reason(self):
        d = self.marked("wt")
        wt = wg.Worktree(path=d, repo=d)
        self.assertEqual(wg._protected_reason(wt, []), "keep marker KEEP")
        self.lease(d, -1)
        self.assertIsNone(wg._protected_reason(wt, []))


class Backfill(Base):
    def test_backfill_dry_run_writes_nothing(self):
        self.marked("a")
        res = sl.backfill(self.root, apply=False, ttl_days=14, now=self.now)
        self.assertEqual(len(res["created"]), 1)
        self.assertFalse(os.path.exists(self.ldir))

    def test_backfill_idempotent_and_owner(self):
        a = self.marked("a")
        self.marked("codex3-x", text="")
        self.marked("unowned", text="keep this")
        os.makedirs(os.path.join(self.root, "plain"))
        r1 = sl.backfill(self.root, apply=True, ttl_days=14, now=self.now)
        self.assertEqual(len(r1["created"]), 3)
        owners = {os.path.basename(x["target"]): x["owner"] for x in r1["created"]}
        self.assertEqual(owners, {"a": "workspace-58", "codex3-x": "codex3", "unowned": "unknown"})
        before = {f: open(os.path.join(self.ldir, f)).read() for f in os.listdir(self.ldir)}
        r2 = sl.backfill(self.root, apply=True, ttl_days=1, now=self.now + 999)
        self.assertEqual(r2["created"], [])
        self.assertEqual(len(r2["existing"]), 3)
        after = {f: open(os.path.join(self.ldir, f)).read() for f in os.listdir(self.ldir)}
        self.assertEqual(before, after)
        le = sl.read_lease(a)
        self.assertEqual(sl._epoch(le["expires"]) - sl._epoch(le["created"]), 14 * 86400)
        self.assertTrue(sl.marker_blocks(a, self.now))
        self.assertFalse(sl.marker_blocks(a, self.now + 15 * 86400))

    def test_report(self):
        self.marked("a"); self.marked("b", text="")
        sl.backfill(self.root, apply=True, ttl_days=14, now=self.now)
        rep = sl.report(self.root, now=self.now)
        self.assertEqual(rep["workspace-58"]["count"], 1)
        self.assertEqual(rep["unknown"]["count"], 1)
        self.assertEqual(rep["unknown"]["expired"], 0)


class Keeper(unittest.TestCase):
    def heredoc(self):
        s = open(KEEPER).read()
        return s.split("<<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n")[0]

    def test_worktree_rule_off_by_default(self):
        s = open(KEEPER).read()
        self.assertIn("REAP_WORKTREES=${REAP_WORKTREES:-0}", s)
        self.assertIn("if E.get('REAP_WORKTREES', '0') == '1':", self.heredoc())
        src = self.heredoc()
        self.assertNotIn("--force", src)
        self.assertNotIn("prune", src)
        compile(src, "keeper-heredoc", "exec")
        self.assertEqual(subprocess.run(["bash", "-n", KEEPER]).returncode, 0)

    def test_keeper_keepmarkers_honours_lease(self):
        src = self.heredoc()
        start = src.index("SYSDIR = E.get(")
        body = src[start:src.index("# ---- keep set ----")]
        with tempfile.TemporaryDirectory() as td:
            ldir = os.path.join(td, "leases"); d = os.path.join(td, "x"); os.makedirs(d)
            open(os.path.join(d, "KEEP"), "w").close()
            logs = []
            ns = {"os": os, "E": {"SCRATCH_LEASE_SYSDIR": SYS}, "now": time.time(),
                  "MARKERS": sl.KEEP_MARKERS, "out": lambda *a: logs.append(a)}
            old = os.environ.get("SCRATCH_LEASE_DIR"); os.environ["SCRATCH_LEASE_DIR"] = ldir
            try:
                exec(body, ns)
                self.assertEqual(ns["keepmarkers"](d), ["KEEP"])          # no lease: legacy keep
                sl.write_lease({"schema": sl.SCHEMA, "owner": "t", "target": os.path.realpath(d),
                                "handoff_or_row": None, "created": sl._iso(0), "expires": sl._iso(1),
                                "budget_gib": 0, "reason": "t"}, ldir)
                self.assertEqual(ns["keepmarkers"](d), [])                # expired lease: released
                ns["E"] = {"SCRATCH_LEASE_SYSDIR": os.path.join(td, "nope")}
                exec(body, ns)                                            # module unloadable: fail closed
                self.assertEqual(ns["keepmarkers"](d), ["KEEP"])
            finally:
                if old is None:
                    os.environ.pop("SCRATCH_LEASE_DIR", None)
                else:
                    os.environ["SCRATCH_LEASE_DIR"] = old


if __name__ == "__main__":
    unittest.main()

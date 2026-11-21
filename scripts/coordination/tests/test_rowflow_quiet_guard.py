#!/usr/bin/env python3
"""quiet_guard_regions: publish validation, keeper UNDERUSED skip (+ QUIET-GUARD log, no shrink), queue_status GUARD,
and the build-idle auto-release left alone. Negative controls: unlisted idle quarters are still UNDERUSED."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rowflow"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", ".claude", "skills", "inference-backlog-scheduling", "scripts"))
import rowflow as rf  # noqa: E402
import publish_row as pr  # noqa: E402


class Validate(unittest.TestCase):
    def test_subset_ok(self):
        self.assertEqual(rf.check_quiet_guard({"quiet_guard_regions": ["q2", "q0"]}, "q0,q1,q2"), ["q0", "q2"])

    def test_unset_is_empty(self):
        self.assertEqual(rf.check_quiet_guard({}, "q0"), [])

    def test_not_subset_refused(self):
        with self.assertRaises(rf.Refused) as c:
            rf.check_quiet_guard({"quiet_guard_regions": ["q0", "q3"]}, "q0,q1,q2")
        self.assertIn("q3", str(c.exception))

    def test_abstract_regions_refused(self):
        with self.assertRaises(rf.Refused):
            rf.check_quiet_guard({"quiet_guard_regions": ["q0"]}, "any-cpu-quarter")

    def test_bad_shapes_refused(self):
        for bad in ("q0", [], ["q9"], [0], True):
            with self.assertRaises(rf.Refused, msg=repr(bad)):
                rf.check_quiet_guard({"quiet_guard_regions": bad}, "q0,q1")

    def test_publish_row_lint_validates_and_spec_key_passes_through(self):
        self.assertIn("quiet_guard_regions", pr.SPEC_KEYS)
        with self.assertRaises(rf.Refused):
            pr.lint({"regions": "q0,q1", "quiet_guard_regions": ["q2"], "result_path": "/x/RESULT.json", "kind": "compute"})
        pr.lint({"regions": "q0,q1,q2", "quiet_guard_regions": ["q0", "q2"], "result_path": "/x/RESULT.json", "kind": "compute"})


class KeeperUnderused(unittest.TestCase):
    def run_underused(self, holders, guard):
        flags = tempfile.mkdtemp()
        for rid, g in guard.items():
            os.makedirs(os.path.join(flags, "ready"), exist_ok=True)
            rf.atomic_json(rf.ready_path(flags, rid), {"schema": rf.SCHEMA, "id": rid, "owner": "o", "quiet_guard_regions": g})
        lines, seen, t0 = [], set(), 1_000_000.0
        rf.underused(flags, holders, lines.append, seen, sample={c: (0, 100) for c in range(192)}, now=t0)
        for k in range(rf.UNDERUSED_SHRINK_S // 300 + 2):   # past the shrink horizon, still all idle
            idle = {c: (0, 100 + 6000 * (k + 1)) for c in range(192)}
            out = rf.underused(flags, holders, lines.append, seen, sample=idle, now=t0 + rf.UNDERUSED_S + 5 + k * 300)
        return out, lines

    def test_guard_regions_skipped_and_logged_once(self):
        out, lines = self.run_underused({"q0": "r3", "q1": "r3", "q2": "r3"}, {"r3": ["q0", "q2"]})
        self.assertEqual([(r, i) for r, i, _ in out], [("q1", "r3")])   # the bench quarter, idle here, is still judged
        self.assertEqual([l for l in lines if l.startswith("QUIET-GUARD")], ["QUIET-GUARD r3 regions=q0,q2"])
        self.assertFalse([l for l in lines if l.startswith("UNDERUSED") and ("q0" in l.split(":")[0] or "q2" in l.split(":")[0])], lines)

    def test_never_suggests_shrinking_guard(self):
        sent = []
        flags = tempfile.mkdtemp()
        holders = {"q0": "r3", "q1": "r3", "q2": "r3"}
        out = [("q1", "r3", 0.0)]   # underused() output excludes guards, so the shrink note counts them as kept
        rf.shrink_suggest(flags, holders, out, {"q1:r3": 1.0}, 10_000.0, lambda m: None,
                          emit=lambda *a: sent.append(a) or True)
        self.assertEqual(sent[0][-1]["suggest_quarters"], 2)
        self.assertEqual(sent[0][-1]["underused"], ["q1"])

    def test_negative_control_no_guard_flags_all(self):
        out, lines = self.run_underused({"q0": "r4", "q1": "r4"}, {})
        self.assertEqual(sorted(r for r, _, _ in out), ["q0", "q1"])
        self.assertFalse([l for l in lines if l.startswith("QUIET-GUARD")])

    def test_guard_of_other_row_does_not_leak(self):
        out, _ = self.run_underused({"q0": "a", "q1": "b"}, {"a": ["q0"]})
        self.assertEqual([(r, i) for r, i, _ in out], [("q1", "b")])


class IdleHeldGuard(unittest.TestCase):
    def test_guard_skipped_in_idle_held_and_warn(self):
        flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(flags, "grants"))
        gp = os.path.join(flags, "grants", "r3.grant")
        open(gp, "w").write("x")
        os.utime(gp, (1, 1))   # old grant
        rf.atomic_json(rf.ready_path(flags, "r3"), {"schema": rf.SCHEMA, "id": "r3", "owner": "o", "quiet_guard_regions": ["q0", "q2"]})
        grants = [{"id": "r3", "path": gp, "holds": {"q0", "q1", "q2"}}]
        holders = {"q0": "r3", "q1": "r3", "q2": "r3"}
        util = {"q0": 0.5, "q1": 0.5, "q2": 0.5, "q3": 0.0}
        lines = []
        out = rf.idle_held(flags, grants, holders, util, lines.append, set(), now=10_000.0)
        self.assertEqual([(r, i) for r, i, _ in out], [("q1", "r3")])   # only the unlisted quarter is IDLE-HELD
        self.assertFalse([l for l in lines if "IDLE-HELD q0" in l or "IDLE-HELD q2" in l], lines)
        sent = []
        rf.idle_held_notify(flags, out, grants, lines.append, now=10_000.0 + rf.IDLE_WARN_AFTER_S + 1,
                            emit=lambda *a: sent.append(a) or {})
        rf.idle_held_notify(flags, out, grants, lines.append, now=10_000.0 + 2 * rf.IDLE_WARN_AFTER_S + 2,
                            emit=lambda *a: sent.append(a) or {})
        self.assertTrue(all(",q0" not in a[3] and "q2" not in a[3] for a in sent), sent)
        # negative control: all guard quarters idle and no guard -> they are reported
        rf.atomic_json(rf.ready_path(flags, "r3"), {"schema": rf.SCHEMA, "id": "r3", "owner": "o"})
        out2 = rf.idle_held(flags, grants, holders, util, lambda m: None, set(), now=10_000.0)
        self.assertEqual(sorted(r for r, _, _ in out2), ["q0", "q1", "q2"])


class BuildIdleUntouched(unittest.TestCase):
    def test_measurement_row_with_guard_is_not_released(self):
        flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(flags, "grants"))
        rf.atomic_json(rf.ready_path(flags, "r3"), {"schema": rf.SCHEMA, "id": "r3", "quiet_guard_regions": ["q0"]})
        out = rf.build_idle_release(flags, {"q0": "r3", "q1": "r3"}, lambda m: None,
                                    sample={c: (0, 100) for c in range(192)}, now=1.0)
        self.assertEqual(out, [])


class QueueStatusGuard(unittest.TestCase):
    def run_main(self, guard):
        import queue_status as qs
        rfm = qs._rowflow()
        f = tempfile.mkdtemp()
        lp = os.path.join(f, "l.sh")
        open(lp, "w").write("#!/bin/bash\n")
        row = {"schema": rfm.SCHEMA, "id": "g1", "owner": "o", "lane": "cpu", "launcher": {"path": lp}, "shape": "multi-quarter(3)",
               "priority_rank": 5.0, "regions": "q0,q1,q2"}
        if guard:
            row["quiet_guard_regions"] = guard
        os.makedirs(os.path.join(f, "ready")); os.makedirs(os.path.join(f, "grants"))
        json.dump(row, open(os.path.join(f, "ready", "g1.json"), "w"))
        open(os.path.join(f, "grants", "g1.grant"), "w").write(
            "regions=0-71 start=2026-11-07T17:13Z end=2099-11-07T22:06Z holds=q0,q1,q2\n")
        old = qs.measure_util
        qs.measure_util = lambda: {"q0": 0.5, "q1": 90.0, "q2": 0.5, "q3": 50.0, "gpu": {"busy": 0, "vram_pct": 0}}
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                qs.main(["--flags", f])
        finally:
            qs.measure_util = old
        return [l for l in buf.getvalue().splitlines() if " g1 " in l]

    def test_guard_shown_not_idle_held(self):
        line = self.run_main(["q0", "q2"])
        self.assertTrue(line, "g1 must be RUNNING")
        self.assertIn("GUARD q0,q2", line[0])
        self.assertNotIn("IDLE-HELD", line[0])

    def test_negative_control_without_guard_is_idle_held(self):
        line = self.run_main(None)
        self.assertTrue(line)
        self.assertIn("IDLE-HELD q0,q2", line[0])
        self.assertNotIn("GUARD", line[0])


if __name__ == "__main__":
    unittest.main()

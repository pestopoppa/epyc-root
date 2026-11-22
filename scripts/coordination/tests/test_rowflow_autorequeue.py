"""Operator-approved 2026-11-21: bounded auto-requeue. A RESUMABLE row whose window ended rc=75 reason=partial-* is
requeued under the same id (capcut mechanism) at most AUTOREQUEUE_MAX (3) times, then its owner is alerted and it is
filed. A job-declared persistent blocker (partial-blocked-*, blocked_on=, requeue=false, RESULT requeue/blocked_on)
is never retried (inf45-e5v2-stageb-r7: "refused by clean-runtime gate (foreign llama-server)")."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
sys.path.insert(0, os.path.join(HERE, "..", "churn"))
import rowflow as rf  # noqa: E402
import filing  # noqa: E402

RID = "inf45-e5v2-stageb-r7-20261121"


class AutoRequeue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = self.tmp.name
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.logs, self.alerts = [], []

    def tearDown(self):
        self.tmp.cleanup()

    def manifest(self, resumable=True, result=None, stop=False):
        d = {"id": RID, "owner": "pipeline-mgmt", "resumable": resumable,
             "stop_file": os.path.join(self.f, RID + ".STOP")}
        if result is not None:
            rp = os.path.join(self.f, "result.json")
            with open(rp, "w") as fh:
                json.dump(result, fh)
            d["result_path"] = rp
        with open(rf.ready_path(self.f, RID), "w") as fh:
            json.dump(d, fh)
        if stop:
            open(d["stop_file"], "w").close()

    def end(self, text="rc=75 time=2026-11-22T05:17:11Z reason=partial-native-incomplete"):
        with open(os.path.join(self.G, RID + ".ended"), "w") as fh:
            fh.write(text + "\n")

    def tick(self):
        return rf.autorequeue(self.f, log=self.logs.append,
                              emit=lambda *a, **k: self.alerts.append((a[1], a[2], a[5])))

    def test_partial_end_requeued_same_id(self):
        self.manifest(); self.end()
        self.assertTrue(filing.capcut_pending(self.f, RID))   # filing skips it
        self.assertEqual(self.tick(), [RID])
        self.assertFalse(os.path.exists(os.path.join(self.G, RID + ".ended")))
        self.assertTrue(os.path.exists(rf.ready_path(self.f, RID)))
        self.assertIn("AUTO-REQUEUE", self.logs[-1])

    def test_capped_at_three_then_owner_alert(self):
        self.manifest()
        for i in range(3):
            self.end(f"rc=75 time=2026-11-22T0{i}:00:00Z reason=partial-native-incomplete")
            self.assertEqual(self.tick(), [RID])
        self.end("rc=75 time=2026-11-22T04:00:00Z reason=partial-native-incomplete")
        self.assertFalse(filing.capcut_pending(self.f, RID))   # filing files it now
        self.assertEqual(self.tick(), [])
        self.assertTrue(os.path.exists(os.path.join(self.G, RID + ".ended")))
        self.assertEqual([a[0] for a in self.alerts], ["autorequeue-limit"])
        self.tick()   # decided once per end: no repeat alert, no repeat log
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(sum("AUTOREQUEUE-LIMIT" in l for l in self.logs), 1)

    def test_declared_blocker_reason_never_requeued(self):
        self.manifest()
        self.end("rc=75 time=2026-11-22T05:17:11Z reason=partial-blocked-clean-runtime-gate-foreign-llama-server\n"
                 "blocked_on=refused by clean-runtime gate (foreign llama-server)\nrequeue=false")
        self.assertFalse(filing.capcut_pending(self.f, RID))
        self.assertEqual(self.tick(), [])
        self.assertEqual(self.alerts[0][0], "autorequeue-blocked")
        self.assertIn("clean-runtime", self.logs[-1])

    def test_requeue_false_line(self):
        self.manifest(); self.end("rc=75 time=x reason=partial-native-incomplete\nrequeue=false")
        self.assertEqual(self.tick(), [])

    def test_result_json_blocked_on(self):
        self.manifest(result={"blocked_on": "foreign llama-server"}); self.end()
        self.assertEqual(self.tick(), [])
        self.manifest(result={"requeue": False})
        self.assertEqual(rf.autorequeue_decision(self.f, RID)[0], "blocked")

    def test_not_resumable_not_requeued(self):
        self.manifest(resumable=False); self.end()
        self.assertEqual(self.tick(), [])
        self.assertFalse(filing.capcut_pending(self.f, RID))

    def test_other_ends_untouched(self):
        self.manifest()
        for t in ("rc=75 time=x reason=hard-end", "rc=1 time=x reason=job-rc-1:exited", "rc=75 time=x reason=stopped"):
            self.end(t)
            self.assertEqual(self.tick(), [], t)

    def test_stop_file_ends_normally(self):
        self.manifest(stop=True); self.end()
        self.assertEqual(self.tick(), [])
        self.assertEqual(self.alerts, [])

    def test_filed_not_requeued(self):
        self.manifest(); self.end()
        os.makedirs(os.path.join(self.f, "filing-done"))
        open(os.path.join(self.f, "filing-done", RID + ".FILED"), "w").close()
        self.assertEqual(self.tick(), [])


class PerRowMax(unittest.TestCase):
    """autorequeue_max: per-row override of the global cap (default stays 3); out-of-range refused."""
    def setUp(self):
        self.t = AutoRequeue("test_partial_end_requeued_same_id"); self.t.setUp()

    def tearDown(self):
        self.t.tearDown()

    def _hist(self, n):
        os.makedirs(rf.autorequeue_dir(self.t.f), exist_ok=True)
        with open(os.path.join(rf.autorequeue_dir(self.t.f), RID + ".history.json"), "w") as fh:
            json.dump({"id": RID, "requeued_at": [1.0] * n}, fh)

    def _manifest(self, mx):
        self.t.manifest()
        p = rf.ready_path(self.t.f, RID)
        d = json.load(open(p))
        if mx is not None:
            d["autorequeue_max"] = mx
        json.dump(d, open(p, "w"))

    def test_default_stays_3(self):
        self.assertEqual(rf.AUTOREQUEUE_MAX, 3)
        self._manifest(None); self._hist(3); self.t.end()
        self.assertEqual(rf.autorequeue_decision(self.t.f, RID)[0], "limit")
        self._hist(2)
        self.assertEqual(rf.autorequeue_decision(self.t.f, RID), ("requeue", "3/3"))

    def test_override_raises_cap_and_logs_n_of_max(self):
        self._manifest(12); self._hist(5); self.t.end()
        self.assertEqual(rf.autorequeue_decision(self.t.f, RID), ("requeue", "6/12"))
        self.assertEqual(self.t.tick(), [RID])
        self.assertIn("(6/12)", self.t.logs[-1])

    def test_override_limit_and_zero(self):
        self._manifest(12); self._hist(12); self.t.end()
        self.assertEqual(rf.autorequeue_decision(self.t.f, RID)[0], "limit")
        self._manifest(0); self._hist(0)
        self.assertEqual(rf.autorequeue_decision(self.t.f, RID)[0], "limit")

    def test_stop_still_wins_with_override(self):
        self.t.manifest(stop=True)
        p = rf.ready_path(self.t.f, RID); d = json.load(open(p)); d["autorequeue_max"] = 20; json.dump(d, open(p, "w"))
        self.t.end()
        self.assertEqual(rf.autorequeue_decision(self.t.f, RID)[0], "stop")

    def test_lint_refuses_out_of_range(self):
        import publish_row as pr
        for bad in (-1, 49, "5", 2.5, True):
            with self.assertRaises(rf.Refused):
                pr.lint({"autorequeue_max": bad})
        self.assertEqual(rf.autorequeue_max_check(48), 48)
        self.assertIn("autorequeue_max", pr.SPEC_KEYS)

    def test_lint_warns_over_12_without_resumable_window(self):
        import publish_row as pr
        s = {"autorequeue_max": 20}; pr.lint(s)
        self.assertTrue(any("autorequeue-max" in w for w in s["publish_warnings"]))
        s = {"autorequeue_max": 20, "resumable": True, "max_window_s": 7200}; pr.lint(s)
        self.assertFalse(any("autorequeue-max" in w for w in s.get("publish_warnings", [])))


class LauncherBlockedHook(unittest.TestCase):
    @unittest.skip("engine hook (FILLER_BLOCKED_FILE) withheld: filler_run15.sh is FROZEN, needs operator --emergency")
    def test_engine_exports_and_maps_blocked_file(self):
        with open(os.path.join(HERE, "..", "rowflow", "filler_run15.sh")) as fh:
            src = fh.read()
        self.assertIn("FILLER_BLOCKED_FILE=$STATE/$ID.blocked", src)
        self.assertIn("reason=partial-blocked-", src)
        self.assertIn("blocked_on=%s\\nrequeue=false", src)


if __name__ == "__main__":
    unittest.main()

"""complete-suspect (c18-fold-cpu-20261122 stale output; c19-fold-cpu-20261123 genuine 6 s futility): an rc=0 reason=complete
end within 60 s of grant start is flagged unless a fresh FUTILITY/FAIL RESULT proves the run itself ended it, or a PASS has a
first-progress marker. Flagged ends are held from filing, alerted, and (resumable + stale) requeued once."""
import datetime as dt
import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
sys.path.insert(0, os.path.join(HERE, "..", "churn"))
import rowflow as rf  # noqa: E402
import filing  # noqa: E402

RID = "c19-fold-cpu-20261123"
T0 = 1_800_000_000.0


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Suspect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = os.path.join(self.tmp.name, "flags")
        self.wd = os.path.join(self.tmp.name, "job")
        os.makedirs(os.path.join(self.f, "grants")); os.makedirs(os.path.join(self.f, "ready"))
        os.makedirs(os.path.join(self.wd, "out", "smoke"))
        self.alerts, self.logs = [], []
        with open(rf.ready_path(self.f, RID), "w") as fh:
            json.dump({"id": RID, "owner": "autokernel", "resumable": True, "workdir": self.wd,
                       "result_path": os.path.join(self.wd, "out", "results.jsonl")}, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def end(self, dur=6):
        with open(os.path.join(self.f, "grants", RID + ".ended"), "w") as fh:
            fh.write(f"rc=0 time={iso(T0 + dur)} reason=complete\nstarted={iso(T0)}\n")
        open(os.path.join(self.f, "grants", RID + ".complete"), "w").close()

    def touch(self, rel, text="x", at=None):
        p = os.path.join(self.wd, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
        os.utime(p, (at or T0 + 2,) * 2)

    def tick(self):
        return rf.autorequeue(self.f, log=self.logs.append, emit=lambda *a, **k: self.alerts.append((a[1], a[2])))

    def test_stale_result_flagged_and_requeued_once(self):
        self.touch("out/RESULT.json", json.dumps({"verdict": "PASS"}), at=T0 - 3600)
        self.end()
        self.assertEqual(rf.autorequeue_decision(self.f, RID)[0], "suspect-requeue")
        self.assertTrue(filing.capcut_pending(self.f, RID))   # not filed as done
        self.assertEqual(self.tick(), [RID])
        self.assertEqual(self.alerts, [("complete-suspect", RID)])
        self.assertFalse(os.path.exists(os.path.join(self.f, "grants", RID + ".ended")))
        self.assertFalse(os.path.exists(os.path.join(self.f, "grants", RID + ".complete")))
        self.assertIn("partial-blocked-stale-complete", json.dumps(rf.load_json(os.path.join(rf.autorequeue_dir(self.f), RID + ".history.json"))))
        self.end()   # ends instantly again: alert, no second requeue
        self.assertEqual(rf.autorequeue_decision(self.f, RID)[0], "suspect")
        self.assertEqual(self.tick(), [])
        self.assertEqual(len(self.alerts), 2)

    def test_no_result_at_all_flagged(self):
        self.end()
        self.assertEqual(rf.autorequeue_decision(self.f, RID)[0], "suspect-requeue")

    def test_fast_genuine_futility_not_flagged(self):
        self.touch("out/RESULT.json", json.dumps({"verdict": "FUTILITY_BUILD_OR_PROOF"}), at=T0 + 1)
        self.end(dur=6)
        self.assertEqual(rf.complete_suspect(self.f, RID), "")
        self.assertEqual(rf.autorequeue_decision(self.f, RID), (None, ""))
        self.assertFalse(filing.capcut_pending(self.f, RID))
        self.assertEqual(self.tick(), [])
        self.assertEqual(self.alerts, [])

    def test_fast_genuine_fail_not_flagged(self):
        self.touch("out/RESULT.json", json.dumps({"verdict": "FAIL(kld)"}), at=T0 + 1)
        self.end(dur=6)
        self.assertEqual(rf.complete_suspect(self.f, RID), "")

    def test_fast_pass_with_marker_not_flagged(self):
        self.touch("out/RESULT.json", json.dumps({"verdict": "PASS"}), at=T0 + 3)
        self.touch("out/logs/visit1.log", at=T0 + 2)
        self.end(dur=20)
        self.assertEqual(rf.complete_suspect(self.f, RID), "")

    def test_fast_pass_without_marker_flagged_not_requeued(self):
        self.touch("out/RESULT.json", json.dumps({"verdict": "PASS"}), at=T0 + 3)
        self.touch("out/smoke/x.json", at=T0 + 2)   # smoke output is never a progress marker
        self.end(dur=20)
        self.assertEqual(rf.autorequeue_decision(self.f, RID)[0], "suspect")

    def test_slow_complete_not_flagged(self):
        self.end(dur=600)
        self.assertEqual(rf.complete_suspect(self.f, RID), "")


class SmokeIsolation(unittest.TestCase):
    def test_smoke_complete_gate_exists(self):
        """the keeper already refuses a smoke that satisfies the full job's --complete-cmd (ROWFLOW-SMOKE-COMPLETE-GENERAL);
        c19's job.py writes only out/smoke/, never RESULT.json"""
        src = open(rf.__file__).read()
        self.assertIn("full-job --complete-cmd rc=", src)
        self.assertIn("outside the smoke", src)


if __name__ == "__main__":
    unittest.main()

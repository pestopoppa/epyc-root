"""auto_file.py (keeper-friction-review 2026-11-05 refinement 3): owner-less filing. Temp trees only; no live bus."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(COORD, "churn"))
import auto_file  # noqa: E402


class AutoFile(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ROWFLOW_BUS_ROOT", None)
        self.d = tempfile.mkdtemp(prefix="autofile-")
        self.flags = os.path.join(self.d, "flags")
        self.bus = os.path.join(self.d, "bus")
        for sub in ("ready", "grants", "filing-done"):
            os.makedirs(os.path.join(self.flags, sub))
        os.makedirs(os.path.join(self.bus, "heartbeats"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def row(self, rid, rule, owner="dead-owner", rc=0, result=None, age_s=3600):
        res = os.path.join(self.d, rid + ".json")
        json.dump(result if result is not None else {"tps": 12.0}, open(res, "w"))
        json.dump({"schema": "epyc.row.v3", "id": rid, "owner": owner, "decision_rule": rule, "result_path": res,
                   "result_format": "json"}, open(os.path.join(self.flags, "ready", rid + ".json"), "w"))
        ended = os.path.join(self.flags, "grants", rid + ".ended")
        open(ended, "w").write(f"rc={rc} time=2026-11-05T00:00:00Z reason=complete\n")
        t = time.time() - age_s
        os.utime(ended, (t, t))
        with open(os.path.join(self.flags, "filing-due.jsonl"), "a") as f:
            f.write(json.dumps({"id": rid, "ended_file": ended, "seen_at": "2026-11-05T00:00:00Z"}) + "\n")

    def run_pass(self, **kw):
        return auto_file.run_pass(self.flags, self.bus, **kw)

    def test_machine_rule_filed_via_file_result_without_owner(self):
        self.row("r-num", "tps >= 10 and rc == 0")
        rep = self.run_pass()
        self.assertEqual(rep["filed"], ["r-num"])
        self.assertTrue(os.path.exists(os.path.join(self.flags, "filing-done", "r-num.FILED")))
        v = json.load(open(os.path.join(self.flags, "filing-done", "r-num.verdict.json")))
        self.assertEqual((v["row_verdict"], v["filed_by"]), ("pass", "file_result.py"))
        self.assertEqual(self.run_pass()["filed"], [], "a filed run is attempted once")

    def test_prose_rule_owner_dead_queued_once_and_never_filed(self):
        self.row("r-prose", "operator reads the flame graph and decides")
        rep = self.run_pass()
        self.assertEqual(rep["queued"], ["r-prose"])
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-done", "r-prose.FILED")))
        q = [json.loads(l) for l in open(os.path.join(self.flags, "filing-owner-less.jsonl"))]
        self.assertEqual([r["id"] for r in q], ["r-prose"])
        self.assertEqual(self.run_pass()["queued"], [])
        alerts = [json.loads(l) for l in open(os.path.join(self.flags, "rowflow-alerts.jsonl"))]
        self.assertEqual([a["kind"] for a in alerts], ["filing-owner-less"])

    def test_prose_rule_owner_live_left_to_owner(self):
        self.row("r-live", "owner judges", owner="h-live")
        json.dump({"agent": "live", "state": "working", "ts": auto_file.now_iso()},
                  open(os.path.join(self.bus, "heartbeats", "live.json"), "w"))
        rep = self.run_pass()
        self.assertEqual((rep["owner_live"], rep["queued"]), (["r-live"], []))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-owner-less.jsonl")))

    def test_prose_rule_too_fresh_waits(self):
        self.row("r-fresh", "owner judges", age_s=60)
        self.assertEqual(self.run_pass()["queued"], [])

    def test_no_manifest_skipped(self):
        self.row("r-gone", "rc == 0")
        os.remove(os.path.join(self.flags, "ready", "r-gone.json"))
        self.assertEqual(self.run_pass()["skipped"], ["r-gone"])

    def test_filing_watch_once_runs_auto_file(self):
        self.row("r-w", "rc == 0")
        open(os.path.join(self.flags, "filing-watch.seen"), "w").write("r-w\n")
        r = subprocess.run(["bash", os.path.join(COORD, "filing_watch.sh"), "--once"], capture_output=True, text=True,
                           timeout=120, env=dict(os.environ, FILING_WATCH_FLAGS_ROOT=self.flags, FILING_WATCH_BUS_ROOT=self.bus))
        self.assertTrue(os.path.exists(os.path.join(self.flags, "filing-done", "r-w.FILED")), r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()

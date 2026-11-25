"""A row withdrawn before its smoke ran (rowflow._withdraw_smoke_queued) is TERMINAL: no filing owed (WITHDRAWN-NO-RUN)."""
import json, os, shutil, sys, tempfile, time, unittest

COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("churn", "rowflow"):
    sys.path.insert(0, os.path.join(COORD, p))
import auto_file, file_result, filing, notify, rowflow as rf  # noqa: E402


class WithdrawnNoRun(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ROWFLOW_BUS_ROOT", None)
        self.d = tempfile.mkdtemp(prefix="wnr-")
        self.flags = os.path.join(self.d, "flags")
        for s in ("ready", "grants", "filing-done"):
            os.makedirs(os.path.join(self.flags, s))
        self.rid = "gpu-w-20261124"
        os.makedirs(rf.dry_dir(self.flags, self.rid))
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, self.rid), "GPU-SMOKE-QUEUED.json"), {"id": self.rid})
        self.assertEqual(rf._withdraw_smoke_queued(self.flags, self.rid, "superseded", lambda m: None), "WITHDRAWN")
        with open(os.path.join(self.flags, "filing-due.jsonl"), "w") as f:
            f.write(json.dumps({"id": self.rid, "seen_at": "2026-11-24T00:00:00+00:00",
                                "ended_file": os.path.join(self.flags, "grants", self.rid + ".ended")}) + "\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_predicate_and_real_run_not_exempt(self):
        self.assertTrue(filing.withdrawn_no_run(self.flags, self.rid))
        self.assertTrue(notify.withdrawn_no_run(self.flags, self.rid))
        other = "gpu-real-20261124"
        open(os.path.join(self.flags, "grants", other + ".ended"), "w").write("rc=1 reason=x\n")
        self.assertFalse(filing.withdrawn_no_run(self.flags, other))
        self.assertIn(other, filing.ended_unfiled(self.flags))
        self.assertNotIn(self.rid, filing.ended_unfiled(self.flags))

    def test_ack_does_not_demand_filing(self):
        notify.emit(self.flags, "row-ended", self.rid, "d", "s", "warning", "autokernel", {}, action=True)
        key = json.loads(open(notify.inbox_path(self.flags)).readline())["key"]
        self.assertIsNone(notify.unfiled_ended(self.flags, key))

    def test_filing_due_skipped(self):
        r = auto_file.run_pass(self.flags, os.path.join(self.d, "bus"), min_age_s=0, now=time.time() + 3600)
        self.assertEqual([k for k, v in r.items() if v], [])

    def test_file_result_accepts(self):
        self.assertEqual(file_result.main([self.rid, "--flags", self.flags]), 0)
        self.assertTrue(filing.is_filed(self.flags, self.rid))
        rec = json.load(open(os.path.join(self.flags, "filing-done", self.rid + ".verdict.json")))
        self.assertEqual(rec["row_verdict"], "WITHDRAWN-NO-RUN")


if __name__ == "__main__":
    unittest.main()

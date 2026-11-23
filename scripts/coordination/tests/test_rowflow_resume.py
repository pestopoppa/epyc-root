"""`rowflow.py resume`: owner-only in-place requeue of a STOPPED / released-early resumable row (same id)."""
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

RID = "ak-resume-x"


class Resume(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = self.tmp.name
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.launcher = os.path.join(self.f, "l.sh")
        open(self.launcher, "w").write("#!/bin/bash\necho hi\n")
        self.stop = os.path.join(self.f, RID + ".STOP")
        self.out = os.path.join(self.f, "out")
        os.makedirs(self.out)
        open(os.path.join(self.out, "TERMINAL-smoke"), "w").close()
        open(os.path.join(self.out, "ledger.jsonl"), "w").write("{}\n")
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def row(self, ended="rc=75 reason=stopped", resumable=True, stop=True, owner="ak", filed=False, where=None):
        d = {"schema": rf.SCHEMA, "id": RID, "owner": owner, "lane": "cpu", "resumable": resumable,
             "stop_file": self.stop, "launcher": {"path": self.launcher}}
        mp = where or rf.ready_path(self.f, RID)
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        json.dump(d, open(mp, "w"))
        rf.atomic_json(rf.pass_path(self.f, RID), {"launcher_sha256": rf.sha256(self.launcher), "passed_at": "x"})
        if stop:
            open(self.stop, "w").close()
        if ended:
            open(os.path.join(self.G, RID + ".ended"), "w").write(ended + "\n")
        if filed:
            filing.write_filed(self.f, RID, f"FILED {RID}: PARTIAL rc=75", {"id": RID})

    def go(self, by="ak", reason="again"):
        return rf.resume_row(self.f, RID, by, reason, log=self.logs.append)

    def test_status_next_then_resume_makes_grantable(self):
        self.row()
        st = rf.status(self.f, RID)
        self.assertEqual(st["state"], "done")
        self.assertEqual(st["next"], f"resume (rowflow.py resume {RID})")
        self.assertEqual(self.go(), 1)
        self.assertFalse(os.path.exists(self.stop))
        self.assertFalse(os.path.exists(os.path.join(self.G, RID + ".ended")))
        self.assertTrue(any(os.listdir(rf.resume_dir(self.f))))
        self.assertTrue(os.path.exists(os.path.join(self.out, "ledger.jsonl")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "TERMINAL-smoke")))
        self.assertTrue(any(l.startswith(f"ROW-RESUMED {RID}") for l in self.logs))
        self.assertEqual(rf.status(self.f, RID)["state"], "grantable")

    def test_released_early_ok_and_manifest_restored_from_withdrawn(self):
        self.row(ended="rc=75 time=x reason=released-early by=ak note=n", where=os.path.join(self.f, "ready", ".withdrawn", RID + ".json"))
        open(os.path.join(self.G, RID + ".grant.released-early"), "w").close()
        self.go()
        self.assertTrue(os.path.exists(rf.ready_path(self.f, RID)))
        self.assertFalse(os.path.exists(os.path.join(self.G, RID + ".grant.released-early")))
        self.assertEqual(rf.status(self.f, RID)["state"], "grantable")

    def test_partial_native_incomplete_resumes(self):
        """RESUME-PARTIAL 2026-11-21: rc=75 reason=partial-* (job-declared resumable partial) resumes like stopped."""
        self.row(ended="rc=75 time=x reason=partial-native-incomplete", stop=False)
        self.assertEqual(rf.status(self.f, RID)["next"], f"resume (rowflow.py resume {RID})")
        self.assertEqual(self.go(), 1)
        self.assertEqual(rf.status(self.f, RID)["state"], "grantable")

    def test_partial_not_resumable_spec_refused(self):
        self.row(ended="rc=75 reason=partial-native-incomplete", resumable=False, stop=False)
        with self.assertRaises(rf.Refused):
            self.go()

    def test_owner_only(self):
        self.row()
        with self.assertRaises(rf.Refused):
            self.go(by="someone-else")
        self.assertTrue(os.path.exists(os.path.join(self.G, RID + ".ended")))

    def test_refusals(self):
        for kw in ({"ended": "rc=75 reason=hard-end"}, {"ended": "rc=0 reason=complete"}, {"ended": "rc=75 reason=deadline"},
                   {"ended": None}, {"resumable": False}):
            with self.subTest(kw=kw):
                self.setUp()
                self.row(**kw)
                with self.assertRaises(rf.Refused):
                    self.go()
                self.tearDown()

    def test_refused_when_launcher_changed_since_pass(self):
        self.row()
        open(self.launcher, "a").write("# edit\n")
        with self.assertRaises(rf.Refused):
            self.go()

    def test_refused_when_superseded(self):
        self.row()
        json.dump({"schema": rf.SCHEMA, "id": "succ", "supersedes": RID}, open(rf.ready_path(self.f, "succ"), "w"))
        with self.assertRaises(rf.Refused):
            self.go()

    def test_filed_receipt_archived_and_refiles_on_next_end(self):
        self.row(filed=True)
        self.assertTrue(filing.is_filed(self.f, RID))
        self.go()
        self.assertFalse(filing.is_filed(self.f, RID))
        self.assertTrue(os.listdir(os.path.join(self.f, "filing-done", ".resumed")))
        self.assertNotIn(RID, filing.ended_unfiled(self.f))
        open(self.stop + "-FINAL", "w").close()   # AK audit B8: a plain owner STOP now auto-requeues; FINAL makes it terminal
        open(os.path.join(self.G, RID + ".ended"), "w").write("rc=75 reason=stopped\n")   # second stop
        self.assertIn(RID, filing.ended_unfiled(self.f))
        self.assertTrue(filing.write_filed(self.f, RID, "FILED again", {"id": RID}))
        self.assertEqual(self.go(), 2)   # history keeps counting; FILED archived again

    def test_cli(self):
        self.row()
        rc = rf.main(["--flags", self.f, "resume", RID, "--by", "ak", "--reason", "x"])
        self.assertEqual(rc, 0)
        self.assertEqual(rf.main(["--flags", self.f, "resume", RID, "--by", "ak", "--reason", "x"]), 2)


if __name__ == "__main__":
    unittest.main()

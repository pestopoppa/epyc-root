"""2026-11-25: a resumable row's deadline end (partial-native-stopped / released-early) that ADDED result units since the
previous grant start is not charged against the auto-requeue cap (rka-a3b-d-remeasure-q-20261123-r5 hit 3/3 while
progressing). A no-progress end is still charged."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
import rowflow as rf  # noqa: E402

RID = "rka-progress-test"


class Progress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = self.tmp.name
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.rp = os.path.join(self.f, "results.jsonl")
        open(self.rp, "w").close()
        with open(rf.ready_path(self.f, RID), "w") as fh:
            json.dump({"id": RID, "owner": "pm", "resumable": True, "result_path": self.rp, "result_format": "jsonl",
                       "stop_file": os.path.join(self.f, RID + ".STOP")}, fh)
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, n):
        with open(self.rp, "a") as fh:
            for i in range(n):
                fh.write(json.dumps({"u": i}) + "\n")

    def end(self, i, reason="partial-native-stopped"):
        with open(os.path.join(self.G, RID + ".ended"), "w") as fh:
            fh.write(f"rc=75 time=2026-11-25T0{i}:00:00Z reason={reason}\n")

    def tick(self):
        return rf.autorequeue(self.f, log=self.logs.append, emit=lambda *a, **k: None)

    def test_progressing_deadline_ends_never_exhaust_cap(self):
        for i in range(8):
            self.add(2); self.end(i)
            self.assertEqual(self.tick(), [RID])
            self.assertTrue(any("AUTO-REQUEUE-PROGRESS" in l and "+2 units" in l for l in self.logs[-2:]))

    def test_non_progressing_end_still_counts(self):
        for i in range(3):
            self.end(i); self.assertEqual(self.tick(), [RID])
        self.end(4)
        self.assertEqual(self.tick(), [])
        self.assertEqual(rf.autorequeue_decision(self.f, RID)[0], "limit")

    def test_progress_then_stall_charged(self):
        self.add(3); self.end(0); self.tick()          # free (+3)
        self.end(1); self.tick()                       # no new units: charged 1
        h = rf.load_json(os.path.join(rf.autorequeue_dir(self.f), RID + ".history.json"))
        self.assertEqual(h["charged"], 1); self.assertEqual(h["units_at_grant"], 3)

    def test_legacy_row_at_cap_with_progress_requeues(self):
        os.makedirs(rf.autorequeue_dir(self.f))
        with open(os.path.join(rf.autorequeue_dir(self.f), RID + ".history.json"), "w") as fh:
            json.dump({"id": RID, "requeued_at": [1.0, 2.0, 3.0]}, fh)   # 3/3 used, no unit baseline
        self.add(7); self.end(7)
        self.assertEqual(self.tick(), [RID])
        h = rf.load_json(os.path.join(rf.autorequeue_dir(self.f), RID + ".history.json"))
        self.assertEqual(h["charged"], 3)
        self.end(8)   # next end with no new units: at cap -> limit
        self.assertEqual(self.tick(), [])


if __name__ == "__main__":
    unittest.main()

"""D9 2026-11-11 (operator "Requeue same id"): a row cut by the keeper's OWN drain cap (engine hard-end at the capped
grant end) is requeued under the same id on the next tick; every other end stays terminal; filing never files it."""
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


class CapcutRequeue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = self.tmp.name
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def row(self, rid, capped=True, ended="rc=75 reason=hard-end", stop=False):
        d = {"id": rid, "stop_file": os.path.join(self.f, rid + ".STOP")}
        with open(rf.ready_path(self.f, rid), "w") as fh:
            json.dump(d, fh)
        if stop:
            open(d["stop_file"], "w").close()
        cap = (int(time.time()) // 60 + 30) * 60 if capped else None
        # an uncapped grant: end_cap None (the row's own window end)
        rf.write_grant(self.f, rid, "q2", ["q2"], 7200, end_cap=cap)
        if ended:
            with open(os.path.join(self.G, rid + ".ended"), "w") as fh:
                fh.write(ended + "\n")

    def tick(self):
        return rf.capcut_requeue(self.f, log=self.logs.append)

    def test_capcut_is_grantable_next_tick_same_id(self):
        self.row("a")
        self.assertTrue(os.path.exists(rf.capstamp_path(self.f, "a")))
        self.assertTrue(rf.capcut_pending(self.f, "a"))
        self.assertEqual(self.tick(), ["a"])
        for suf in (".ended", ".grant"):
            self.assertFalse(os.path.exists(os.path.join(self.G, "a" + suf)))
        self.assertTrue(os.path.exists(rf.ready_path(self.f, "a")))
        arch = os.listdir(rf.capcut_dir(self.f))
        self.assertTrue(any(x.endswith(".ended") for x in arch) and any(x.endswith(".grant") for x in arch))
        self.assertTrue(any(l.startswith("CAPCUT-REQUEUE a") for l in self.logs))
        self.assertEqual(self.tick(), [])

    def test_natural_hard_end_without_cap_stays_ended(self):
        self.row("n", capped=False)
        self.assertFalse(os.path.exists(rf.capstamp_path(self.f, "n")))
        self.assertEqual(self.tick(), [])
        self.assertTrue(os.path.exists(os.path.join(self.G, "n.ended")))

    def test_cap_not_binding_writes_no_stamp(self):
        far = int(time.time()) + 10 * 86400   # the window ends first: no cap applied
        rf.write_grant(self.f, "w", "q2", ["q2"], 600, end_cap=far)
        self.assertFalse(os.path.exists(rf.capstamp_path(self.f, "w")))

    def test_complete_failed_stopped_stay_ended(self):
        self.row("c")
        open(os.path.join(self.G, "c.complete"), "w").close()
        self.row("x", ended="rc=1 reason=failed")
        self.row("s", stop=True)
        self.row("e", ended="rc=0 reason=complete")
        self.assertEqual(self.tick(), [])
        for rid in "cxse":
            self.assertTrue(os.path.exists(os.path.join(self.G, rid + ".ended")), rid)
        self.assertTrue(any(l.startswith("CAPCUT-END s") for l in self.logs))
        self.assertFalse(rf.capcut_pending(self.f, "s"))   # stamp archived: filing proceeds

    def test_requeue_limit(self):
        for i in range(rf.CAPCUT_MAX):
            self.row("L")
            self.assertEqual(rf.capcut_requeue(self.f, log=self.logs.append, now=time.time() + i), ["L"])
        self.row("L")
        self.assertEqual(rf.capcut_requeue(self.f, log=self.logs.append, now=time.time() + 10), [])
        self.assertTrue(os.path.exists(os.path.join(self.G, "L.ended")))
        self.assertTrue(any("requeue limit" in l for l in self.logs))
        # outside the 24 h window the count resets
        self.row("L")
        self.assertEqual(rf.capcut_requeue(self.f, log=self.logs.append, now=time.time() + 2 * 86400), ["L"])

    def test_filing_skips_capcut_row(self):
        self.row("a")
        self.row("n", capped=False)
        self.assertTrue(filing.capcut_pending(self.f, "a"))
        self.assertEqual(filing.load_end(self.f, "a"), (None, None, ""))
        self.assertNotIn("a", filing.ended_unfiled(self.f))
        self.assertIn("n", filing.ended_unfiled(self.f))
        self.assertEqual(filing.load_end(self.f, "n")[1], 75)


if __name__ == "__main__":
    unittest.main()

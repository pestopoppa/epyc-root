#!/usr/bin/env python3
"""keeper-hotfix 2026-11-05: filler_run15.sh mid-job STOP reaches setsid/nohup grandchildren (P2.3 #3) and STOP is
honoured while waiting for a grant (D13). Fake region-lock + fake job; temp dirs only."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_filler_stop_midrun import FillerStop, alive  # noqa: E402

# the job starts a setsid'd grandchild (new session + group, like llama-server from job.sh) and an orphaned nohup one
SETSID_JOB = ("trap '' TERM; echo $$ > \"$RL_PIDS/job.pid\"; setsid sleep 1000 & echo $! > \"$RL_PIDS/setsid.pid\"; "
              "( setsid nohup sleep 1000 >/dev/null 2>&1 & echo $! > \"$RL_PIDS/orphan.pid\" ) ; while :; do sleep 1; done")


class FillerHotfix(FillerStop):
    def test_stop_midrun_kills_setsid_and_orphaned_grandchildren(self):
        import test_filler_stop_midrun as m
        rid = "stopsetsid"
        self.grant(rid)
        old, m.FAKE_JOB = m.FAKE_JOB, SETSID_JOB
        try:
            self.launch(rid, ["--stop-grace", "2"])
        finally:
            m.FAKE_JOB = old
        self.assertTrue(self.wait_file(os.path.join(self.pids, "orphan.pid")), self.out(rid))
        time.sleep(0.5)
        pids = [int(open(os.path.join(self.pids, n)).read()) for n in ("job.pid", "setsid.pid", "orphan.pid")]
        self.assertTrue(all(alive(p) for p in pids), pids)
        open(self.stop, "w").close()
        self.assertEqual(self.proc.wait(timeout=60), 0, self.out(rid))
        time.sleep(0.5)
        self.assertEqual([p for p in pids if alive(p)], [], "setsid/nohup grandchild survived STOP: " + self.out(rid))
        self.assertRegex(open(os.path.join(self.grants, rid + ".ended")).readline(), r"reason=stopped$")

    def test_stop_while_waiting_for_grant_exits_and_writes_ended(self):
        rid = "stopwait"
        self.launch(rid)   # no grant: the poller waits
        time.sleep(2)
        self.assertIsNone(self.proc.poll())
        t0 = time.time()
        open(self.stop, "w").close()
        self.assertEqual(self.proc.wait(timeout=15), 0, self.out(rid))
        self.assertLess(time.time() - t0, 5, "STOP not seen within 2 polls")
        self.assertRegex(open(os.path.join(self.grants, rid + ".ended")).readline(), r"^rc=75 .*reason=stopped-while-waiting$")
        self.assertFalse(os.path.exists(os.path.join(self.grants, rid + ".grant")))
        self.assertIn("STOP seen while waiting", self.out(rid))


if __name__ == "__main__":
    unittest.main()

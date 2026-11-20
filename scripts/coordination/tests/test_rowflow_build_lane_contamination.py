#!/usr/bin/env python3
"""F7 (AK audit B7): builds are a lane (claim --build refused over a timing grant) and contamination names the
offender (a foreign busy process on a held quarter -> CONTAMINATION.json + one owner alert within 2 samples)."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import hostutil  # noqa: E402
import rowflow as rf  # noqa: E402

BENCH = "bench-q0-20261120"


def bench_grant():
    return {"id": BENCH, "regions": "0-23", "holds": {"q0"}, "pid": None, "dryrun": False, "started": True, "path": "x"}


class BuildLane(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="bld-")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.free = set(rf.REGIONS) - {"q0"}

    def claim(self, cpus, grants):
        with mock.patch.object(rf, "contract_of", return_value={"bench": True}):
            return rf.claim_build(self.flags, "akagg", cpus, 30, log=lambda m: None, grants=grants,
                                  allrows={BENCH: {"id": BENCH}}, free=self.free)

    def test_claim_over_timing_grant_refused_naming_it(self):
        with self.assertRaises(rf.Refused) as e:
            self.claim("0-23", [bench_grant()])
        self.assertIn(f"timing grant {BENCH}", str(e.exception))
        self.assertEqual([f for f in os.listdir(os.path.join(self.flags, "grants")) if f.endswith(".grant")], [])

    def test_count_claim_takes_free_quarter_and_reaps(self):
        gid, line = self.claim("16", [bench_grant()])
        self.assertTrue(gid.startswith("build-akagg-"))
        self.assertIn("regions=q1", line)
        g = [x for x in rf.open_grants(self.flags) if x["id"] == gid][0]
        self.assertEqual(g["holds"] & set(rf.QUARTERS), {"q1"})
        self.assertEqual(rf.reap_build_grants(self.flags, now=time.time(), log=lambda m: None), [])
        self.assertEqual(rf.reap_build_grants(self.flags, now=time.time() + 31 * 60, log=lambda m: None), [gid])
        self.assertIn("reason=build-window", open(os.path.join(self.flags, "grants", gid + ".ended")).read())

    def test_cli(self):
        with mock.patch.object(rf, "host_snapshot", return_value=(set(), set(rf.REGIONS), {})), \
                mock.patch.object(rf, "open_grants", return_value=[]):
            self.assertEqual(rf.main(["--flags", self.flags, "claim", "--build", "--owner", "akagg", "--cpus", "4",
                                      "--minutes", "10"]), 0)


class Contamination(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="ctm-")
        os.makedirs(os.path.join(self.flags, "ready"))
        json.dump({"id": BENCH, "owner": "autokernel"}, open(rf.ready_path(self.flags, BENCH), "w"))
        self.sent = []

    def sample(self, census, now, grants=None):
        with mock.patch.object(rf, "own_pids", return_value=set()):
            return rf.contamination_sample(self.flags, grants or [bench_grant()], lambda m: None, census=census, now=now,
                                           emit=lambda *a: self.sent.append(a) or {})

    def test_fixture_census_two_samples(self):
        c0 = {4242: ("77", 10.0, 3, "cmake")}
        self.assertEqual(self.sample(c0, 1000.0), {})
        self.assertEqual(self.sample({4242: ("77", 70.0, 3, "cmake")}, 1060.0), {})          # sample 1 (100%)
        self.assertEqual(self.sample({4242: ("77", 130.0, 5, "cmake")}, 1120.0), {BENCH: [4242]})   # sample 2
        rec = json.load(open(os.path.join(rf.dry_dir(self.flags, BENCH), "CONTAMINATION.json")))
        self.assertEqual((rec["offenders"][0]["pid"], rec["offenders"][0]["comm"]), (4242, "cmake"))
        self.assertEqual([(a[1], a[2], a[6]) for a in self.sent], [("contamination", BENCH, "autokernel")])
        self.assertEqual(self.sample({4242: ("77", 190.0, 5, "cmake")}, 1180.0), {})          # once per offender

    def test_other_quarter_and_build_lane_ignored(self):
        self.sample({7: ("1", 0.0, 30, "make")}, 1000.0)                                      # cpu 30 = q1
        self.sample({7: ("1", 60.0, 30, "make")}, 1060.0)
        self.assertEqual(self.sample({7: ("1", 120.0, 30, "make")}, 1120.0), {})
        self.assertEqual(self.sent, [])

    def test_real_busy_process_named_within_two_samples(self):
        yes = subprocess.Popen(["yes"], stdout=subprocess.DEVNULL)   # fixture stand-in for cmake (never taskset: shared host)
        try:
            g = dict(bench_grant(), holds=set(rf.QUARTERS))
            got = {}
            for i in range(3):
                got = self.sample(hostutil.proc_census(), time.time(), [g]) or got
                time.sleep(0.6)
            self.assertIn(yes.pid, got.get(BENCH, []))
            rec = json.load(open(os.path.join(rf.dry_dir(self.flags, BENCH), "CONTAMINATION.json")))
            o = [x for x in rec["offenders"] if x["pid"] == yes.pid][0]
            self.assertEqual(o["comm"], "yes")
        finally:
            os.kill(yes.pid, signal.SIGKILL)   # the pid this test captured
            yes.wait(5)


if __name__ == "__main__":
    unittest.main()

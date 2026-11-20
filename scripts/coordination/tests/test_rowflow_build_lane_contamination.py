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

PART = "codex-bfcl-cj3d-supported-27b-v1-20261120"


def partial_grant():   # 8 cores of q0 + their SMT siblings (the 52 h cj3d grant)
    return {"id": PART, "regions": "0-7", "pid": None, "dryrun": False, "started": True, "path": "x",
            "holds": {f"c{n}" for n in range(8)} | {f"t{n}" for n in range(96, 104)}}


class PartialQuarterBuild(unittest.TestCase):
    """A grant holding only some cores of q0 leaves its other cores claimable by `claim --build`; a whole-quarter hold still refuses."""

    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="bldp-")
        os.makedirs(os.path.join(self.flags, "grants"))

    def free_without(self, g, quarters_busy=()):
        busy = rf.expand(set(g["holds"]) | set(quarters_busy))
        busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
        return (set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)) - busy

    def claim(self, cpus, grants, free):
        with mock.patch.object(rf, "contract_of", return_value={"bench": False}):
            return rf.claim_build(self.flags, "akagg", cpus, 30, log=lambda m: None, grants=grants,
                                  allrows={PART: {"id": PART}}, free=free)

    def test_literal_free_cores_of_partly_held_q0(self):
        g = partial_grant()
        gid, line = self.claim("8-23", [g], self.free_without(g))
        held = [x for x in rf.open_grants(self.flags) if x["id"] == gid][0]["holds"]
        self.assertEqual({t for t in held if t.startswith("c")}, {f"c{n}" for n in range(8, 24)})
        self.assertFalse(held & g["holds"]); self.assertNotIn("q0", held)
        rec = json.load(open(os.path.join(self.flags, "grants", gid + ".build.json")))
        self.assertIn("partial", rec)

    def test_literal_list_overlapping_the_holder_refused(self):
        g = partial_grant()
        with self.assertRaises(rf.Refused) as e:
            self.claim("4-12", [g], self.free_without(g))
        self.assertIn("q0 is held", str(e.exception))

    def test_count_claim_falls_back_to_free_cores_when_no_whole_quarter(self):
        g = partial_grant(); other = {"id": "o", "holds": {"q1", "q2"}}
        free = self.free_without(g, quarters_busy={"q1", "q2"})
        gid, _ = self.claim("16", [g, other], free)
        held = [x for x in rf.open_grants(self.flags) if x["id"] == gid][0]["holds"]
        cores = {t for t in held if t.startswith("c")}
        self.assertEqual(len(cores), 16); self.assertTrue(cores <= {f"c{n}" for n in range(8, 24)})
        # the build left no room for a second 16: refused and a build-wait recorded
        free2 = free - held
        with self.assertRaises(rf.Refused):
            self.claim("16", [g, other], free2)

    def test_whole_quarter_hold_still_refuses(self):
        g = {"id": "wq", "holds": {"q0"}}
        free = self.free_without(g, quarters_busy={"q1", "q2"})
        for c in ("8-23", "4"):
            with self.assertRaises(rf.Refused):
                self.claim(c, [g], free)

    def test_partial_hold_of_timing_grant_still_refused(self):
        g = partial_grant()
        with mock.patch.object(rf, "timing_quarters", return_value={"q0"}), self.assertRaises(rf.Refused) as e:
            self.claim("8-23", [g], self.free_without(g))
        self.assertIn("timing grant", str(e.exception))

    def test_other_sub_quarter_row_fits_beside_build(self):
        g = partial_grant()
        gid, _ = self.claim("8-15", [g], self.free_without(g))
        bg = [x for x in rf.open_grants(self.flags) if x["id"] == gid][0]
        free = self.free_without({"holds": g["holds"] | bg["holds"]})
        self.assertTrue({f"c{n}" for n in range(16, 24)} <= free)


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

    def test_review_s3_smoke_harness_and_keeper_pids_exempt(self):
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, "smk-20261120"), "RUNNING.json"), {"pid": 5151})
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, "smp-20261120"), "SMOKE-PLACED.json"), {"pid": 5252})
        ex = rf.contamination_exempt_pids(self.flags)
        self.assertTrue({5151, 5252, os.getpid(), os.getppid()} <= ex)
        for pid in (5151, 5252, os.getpid()):
            self.sample({pid: ("9", 0.0, 3, "x")}, 1000.0)
            self.sample({pid: ("9", 60.0, 3, "x")}, 1060.0)
            self.assertEqual(self.sample({pid: ("9", 120.0, 3, "x")}, 1120.0), {}, pid)
        self.assertEqual(self.sent, [])

    def test_other_quarter_and_build_lane_ignored(self):
        self.sample({7: ("1", 0.0, 30, "make")}, 1000.0)                                      # cpu 30 = q1
        self.sample({7: ("1", 60.0, 30, "make")}, 1060.0)
        self.assertEqual(self.sample({7: ("1", 120.0, 30, "make")}, 1120.0), {})
        self.assertEqual(self.sent, [])

    def test_real_busy_process_named_within_two_samples(self):
        # fixture stand-in for cmake (never taskset: shared host); double-forked so it is NOT in this (keeper) process's tree
        sh = subprocess.run(["sh", "-c", "yes >/dev/null 2>&1 & echo $!"], capture_output=True, text=True, check=True)
        yes = mock.Mock(pid=int(sh.stdout.strip()))
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


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""LIGHT test claim (AutoKernel approved 2026-11-23): `rowflow.py claim --build --light`. Cores 84-87 only, <= 4 cores, <= 15 min,
one light claim host-wide, not bandwidth-heavy (quiet_gate ignores it), refused while a running quiet row logged a contended
launch (ak_row_harness contended.jsonl) in the last 10 minutes. Non-light claims are unchanged."""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

QUIET = {"id": "quiet-a", "requires_quiet_host": True, "shape": "quarter", "result_path": ""}


class LightClaim(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="light-")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.work = tempfile.mkdtemp(prefix="light-work-")
        self.quiet = dict(QUIET, result_path=os.path.join(self.work, "out", "results.jsonl"))
        rf.write_grant(self.flags, "quiet-a", "q0", {"q0"}, 3600)   # a running quiet row on q0
        p = mock.patch.object(rf, "host_snapshot", side_effect=self._snap)
        p.start(); self.addCleanup(p.stop)

    def _snap(self, flags, grants):
        all_ = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
        busy = set()
        for g in grants:
            busy |= rf.expand(set(g["holds"]))
        busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
        return None, all_ - busy, None

    def light(self, cpus="84-87", minutes=15, owner="autokernel", **kw):
        return rf.claim_build(self.flags, owner, cpus, minutes, log=lambda m: None, light=True,
                              allrows={"quiet-a": self.quiet}, **kw)

    def keeper_log(self):
        p = os.path.join(self.flags, "ws58-calendar-keeper.log")
        return open(p).read() if os.path.exists(p) else ""

    def test_granted_beside_running_quiet_row(self):
        gid, _ = self.light("84-87", 10)
        bj = json.load(open(os.path.join(self.flags, "grants", gid + ".build.json")))
        self.assertEqual(bj["bandwidth_class"], "light")
        self.assertIn(gid, [g["id"] for g in rf.open_grants(self.flags)])
        self.assertIn(f"LIGHT-CLAIM {gid} cpus=84-87 beside quiet quiet-a", self.keeper_log())
        self.assertTrue(rf.is_light_build(self.flags, gid))

    def test_light_claim_is_not_loud_for_quiet_gate(self):
        gid, _ = self.light("84-87", 10)
        # a quiet candidate on q3 must not be pushed off by the light claim, but is by a heavy (non-light) build grant
        cand = {"id": "q-next", "options": [{"q3"}], "rank": 1, "kind": "row", "shape": "quarter"}
        g = [x for x in rf.open_grants(self.flags) if x["id"] == gid]
        kept, waits, _ = rf.quiet_gate([cand], {"q-next": {"requires_quiet_host": True}}, g, {"q3": 0.0}, flags=self.flags)
        self.assertEqual(kept, [cand], waits)
        os.remove(os.path.join(self.flags, "grants", gid + ".build.json"))   # same grant without the light record = heavy build
        kept, waits, _ = rf.quiet_gate([cand], {"q-next": {"requires_quiet_host": True}}, g, {"q3": 0.0}, flags=self.flags)
        self.assertEqual(kept, [])

    def test_second_light_claim_refused(self):
        self.light("84-85", 5)
        with self.assertRaises(rf.Refused) as e:
            self.light("86-87", 5)
        self.assertIn("LIGHT-REFUSED", str(e.exception))
        self.assertIn("one light claim at a time", str(e.exception))
        self.assertIn("LIGHT-REFUSED", self.keeper_log())

    def test_refused_over_four_cores(self):
        with self.assertRaises(rf.Refused) as e:
            self.light("84-88", 5)
        self.assertIn("LIGHT-REFUSED", str(e.exception))

    def test_refused_outside_84_87(self):
        for cpus in ("80-83", "72-87", "88", "84,168"):
            with self.assertRaises(rf.Refused, msg=cpus) as e:
                self.light(cpus, 5)
            self.assertIn("outside cores 84-87", str(e.exception))

    def test_refused_over_15_minutes(self):
        with self.assertRaises(rf.Refused) as e:
            self.light("84", 16)
        self.assertIn("1..15 minutes", str(e.exception))

    def test_refused_after_recent_contended_marker(self):
        os.makedirs(os.path.join(self.work, "out"))
        mk = os.path.join(self.work, "out", "contended.jsonl")
        now = time.time()
        utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 120))
        open(mk, "w").write(json.dumps({"unit": "u1", "stage": "measure", "probe_p50": 40.0, "max": 15.0, "utc": utc}) + "\n")
        with self.assertRaises(rf.Refused) as e:
            self.light("84-87", 5)
        self.assertIn("LIGHT-REFUSED running quiet row quiet-a logged a contended launch", str(e.exception))
        # the same marker 11 minutes old no longer blocks
        old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 660))
        open(mk, "w").write(json.dumps({"utc": old}) + "\n")
        gid, _ = self.light("84-87", 5)
        self.assertTrue(gid.startswith("build-autokernel-"))

    def test_non_light_claim_still_refused_beside_quiet_row(self):
        with self.assertRaises(rf.Refused) as e:
            rf.claim_build(self.flags, "autokernel", "72-87", 10, log=lambda m: None, allrows={"quiet-a": self.quiet})
        self.assertIn("quiet-host row quiet-a is running", str(e.exception))
        self.assertNotIn("LIGHT", str(e.exception))

    def test_light_allowed_while_quiet_reserve_active(self):
        os.makedirs(rf.state_dir(self.flags), exist_ok=True)
        rf.atomic_json(os.path.join(rf.state_dir(self.flags), rf.QUIET_RESERVE_STATE),
                       {"active": True, "released": False, "ts": time.time(), "rows": ["quiet-b"]})
        self.assertEqual(rf.quiet_reserve_blocks_build(self.flags), ["quiet-b"])
        gid, _ = self.light("84-87", 5)   # a non-light build would be QUIET-RESERVE refused here
        self.assertTrue(rf.is_light_build(self.flags, gid))

    def test_cli_light_flag_in_help(self):
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(os.path.dirname(_TESTS), "rowflow", "rowflow.py"), "claim", "--help"],
                             capture_output=True, text=True).stdout
        self.assertIn("--light", out)
        self.assertIn("nice -n 19 taskset", out)


if __name__ == "__main__":
    unittest.main()

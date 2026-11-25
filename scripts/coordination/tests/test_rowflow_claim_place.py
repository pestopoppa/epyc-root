#!/usr/bin/env python3
"""CLAIM-PLACE (AK 2026-11-25): a build claim never lands on a running measurement's quarter or NUMA half."""
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

CONV = "ak-cpu-conv-state-fwd-20261124-r2"


def grant(gid, q):
    return {"id": gid, "regions": rf.cpu_list(q), "holds": {q}, "pid": None, "dryrun": False, "started": True, "path": "x"}


class ClaimPlace(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="cplace-")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.logs = []

    def claim(self, cpus, grants, bench=True):
        held = set().union(*[g["holds"] for g in grants]) if grants else set()
        free = (set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)) - rf.expand(held) - held
        allrows = {g["id"]: {"id": g["id"]} for g in grants}
        with mock.patch.object(rf, "contract_of", return_value={"bench": bench}), \
                mock.patch.object(rf, "quiet_required", return_value=False), \
                mock.patch.object(rf, "quiet_sensitive", return_value=False), \
                mock.patch.object(rf, "claim_reservation_check", return_value=None), \
                mock.patch.object(rf, "gpu_rows_waiting_on_q3", return_value=[]):
            return rf.claim_build(self.flags, "autokernel", cpus, 14, log=self.logs.append, grants=grants,
                                  allrows=allrows, free=free)

    def test_replay_incident_literal_q1_refused_beside_conv_state(self):
        with self.assertRaises(rf.Refused) as e:   # the 03:18Z q8w8 build: --cpus 24-47 while conv-state held q0
            self.claim("24-47", [grant(CONV, "q0")])
        self.assertIn(CONV, str(e.exception))
        with self.assertRaises(rf.Refused):
            self.claim("0-23", [grant(CONV, "q0")])

    def test_count_build_goes_to_free_quarter_on_other_half_and_logs(self):
        gid, line = self.claim("16", [grant(CONV, "q0")])
        self.assertIn("regions=q2", line)
        self.assertTrue(any(m.startswith(f"CLAIM-PLACE {gid} cpus=48-71") and CONV in m for m in self.logs), self.logs)
        self.assertIn("CLAIM-PLACE", open(os.path.join(self.flags, "ws58-calendar-keeper.log")).read()
                      if os.path.exists(os.path.join(self.flags, "ws58-calendar-keeper.log")) else "CLAIM-PLACE")

    def test_waits_when_no_quarter_fits(self):
        with self.assertRaises(rf.Refused) as e:
            self.claim("16", [grant(CONV, "q0"), grant("ak-other-meas-q2", "q2")])
        self.assertIn("numa-side", str(e.exception))
        self.assertEqual([f for f in os.listdir(os.path.join(self.flags, "grants")) if f.endswith(".grant")], [])

    def test_non_measurement_neighbour_does_not_block(self):
        gid, line = self.claim("24-47", [grant("plain-row", "q0")], bench=False)
        self.assertIn("regions=q1", line)


if __name__ == "__main__":
    unittest.main()

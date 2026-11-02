#!/usr/bin/env python3
"""ws58 2026-11-02: a smoke that completes the whole job files it as done (never a row); estimate_s < 300 is refused;
two rows declaring the same port are never co-scheduled."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402


class TinyRowTests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        self.rid = "tiny1"
        self.res = os.path.join(self.flags, "out", "RESULT.json")

    def _smoke(self, complete):
        rid, res = self.rid, self.res

        def publish(spec, flags, source=None):
            row = {"id": rid, "result_path": res}
            rf.atomic_json(rf.ready_path(flags, rid), row)
            return row

        def dry(flags, rid_, regions, one_quarter=False, smoke_s=None):
            dd = rf.dry_dir(flags, rid_)
            os.makedirs(dd, exist_ok=True)
            os.makedirs(os.path.dirname(res), exist_ok=True)
            open(res, "w").write("{}")
            open(os.path.join(dd, "ended"), "w").write("rc=0 reason=complete\n")
            rf.atomic_json(rf.pass_path(flags, rid_), {"id": rid_, "result_path": res, "job_complete": complete})
            return "PASS", "1 unit(s)"
        with mock.patch.object(pr, "smoke_regions", return_value="0-3"), mock.patch.object(rf, "publish", publish), \
                mock.patch.object(rf, "dryrun_run", dry):
            return pr.publish_smoked({"lane": "cpu"}, self.flags, "t")

    def test_complete_in_smoke_is_filed_not_queued(self):
        self.assertIsNone(self._smoke(True))
        g = os.path.join(self.flags, "grants")
        self.assertTrue(os.path.exists(os.path.join(g, self.rid + ".complete")))
        self.assertTrue(os.path.exists(os.path.join(g, self.rid + ".ended")))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertTrue(os.path.exists(self.res))

    def test_partial_smoke_stays_a_row(self):
        self.assertIsNotNone(self._smoke(False))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "grants", self.rid + ".complete")))

    def test_short_estimate_refused(self):
        spec = os.path.join(self.flags, "s.json")
        json.dump({"id": "x", "estimate_s": 120}, open(spec, "w"))
        with mock.patch("builtins.print") as p:
            self.assertEqual(pr.main([spec, "--flags", self.flags]), 2)
        self.assertIn("under 5 min: run it in your turn, not as a row", str(p.call_args))


class PortTests(unittest.TestCase):
    def _c(self, rid, region, ports):
        return {"id": rid, "kind": "grant", "lane": "cpu", "rank": 1, "lane_count": 0, "gib": 0, "bench": False,
                "options": [frozenset({region})], "ports": ports}

    def test_same_port_never_co_scheduled(self):
        q = sorted(rf.QUARTERS)
        out, idle, pend = rf.plan(set(q[:2]), [self._c("a", q[0], [8070]), self._c("b", q[1], [8070])], 1000)
        self.assertEqual([c["id"] for c, _ in out], ["a"])
        self.assertEqual([c["id"] for c in pend], ["b"])
        self.assertIn("port 8070", idle[q[1]])

    def test_port_held_by_running_grant_waits(self):
        q = sorted(rf.QUARTERS)
        out, idle, pend = rf.plan({q[0]}, [self._c("a", q[0], [8070])], 1000, held_ports={8070})
        self.assertEqual(out, [])
        self.assertIn("held by a running grant", idle[q[0]])
        out, _, _ = rf.plan({q[0]}, [self._c("a", q[0], [8071])], 1000, held_ports={8070})
        self.assertEqual(len(out), 1)


class DrainBackfillTests(unittest.TestCase):
    """11:28Z: quiet-host akx-auto10 drained to T=11:53; a GPU row ending 11:58 was backfilled and T slid to 12:00."""
    def _c(self, rid, opts, est, shape=None):
        return {"id": rid, "kind": "grant", "lane": "cpu", "rank": 1 if shape else 5, "lane_count": 0, "gib": 0,
                "bench": False, "options": [frozenset(o) for o in opts], "estimate_s": est, "shape": shape}

    def test_no_slide_and_gap_packed(self):
        now = 1000.0
        quiet = self._c("akx", [rf.REGIONS], 3600, "quiet-host")
        gpu_long = self._c("kvu16a", [{rf.GPU}], 1800)       # would end after T on a region the quiet row needs
        q_short = self._c("short", [{"q1"}], 600)
        q_longer = self._c("longer", [{"q1"}], 1200)
        free = {"q1", "q2", rf.GPU}
        out, _, _ = rf.plan(free, [quiet, gpu_long, q_short, q_longer], 1000, now=now, grant_ends=[now + 1500])
        ids = [c["id"] for c, _ in out]
        self.assertNotIn("kvu16a", ids)
        self.assertIn("longer", ids)          # longest that fits by T first
        self.assertNotIn("short", ids)
        self.assertEqual(rf.plan.last_drain[1], now + 1500)
        # next tick: running grants now end later; persisted T never moves later
        rf.plan(free, [quiet], 1000, now=now + 60, grant_ends=[now + 2400], drain_prev={"akx": now + 1500})
        self.assertEqual(rf.plan.last_drain[1], now + 1500)

    def test_unneeded_region_granted_ignoring_T(self):
        now = 1000.0
        quiet = self._c("akx", [{"q0", "q1"}], 3600, "quiet-host")
        far = self._c("far", [{"q2"}], 99999)
        out, _, _ = rf.plan({"q1", "q2"}, [quiet, far], 1000, now=now, grant_ends=[now + 600])
        self.assertIn("far", [c["id"] for c, _ in out])


if __name__ == "__main__":
    unittest.main()

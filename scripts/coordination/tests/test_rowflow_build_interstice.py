#!/usr/bin/env python3
"""BUILD-INTERSTICE (AutoKernel 2026-11-24): when a quiet row's grant ends, ONE queued short build claim is granted before
the next quiet row; urgent quiet heads still go first; builds over the cap get no interstice; one build per gap; flag off =
old behaviour. Exercises the pure step, the keeper adapter and the REPLAN item model."""
import os
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0


def b(key, minutes=4, since=NOW - 600, owner="autokernel"):
    return {"key": key, "owner": owner, "since": since, "minutes": minutes}


QC = [("quiet-a", 50.0, 3600), ("quiet-b", 60.0, 1800)]


def ended(state=None):
    """State with one quiet row running last tick; it is gone now."""
    return dict(state or {}, quiet_running=["quiet-old"])


class Step(unittest.TestCase):
    def test_quiet_end_grants_build_before_next_quiet(self):
        st, hold, line = rf.build_interstice_step(ended(), [], [], [b("k1")], QC, NOW, enabled=True)
        self.assertEqual(line, "BUILD-INTERSTICE grant k1 before quiet-b")
        self.assertEqual(hold, {"quiet-a", "quiet-b"})
        # granted next tick: quiet rows keep waiting while it runs
        st2, hold2, _ = rf.build_interstice_step(st, [], [("build-x", "autokernel", NOW + 30)], [], QC, NOW + 60, enabled=True)
        self.assertEqual(st2["active"]["gid"], "build-x")
        self.assertEqual(hold2, {"quiet-a", "quiet-b"})
        # build over its 900 s: never killed, quiet still waits
        _, hold3, _ = rf.build_interstice_step(st2, [], [("build-x", "autokernel", NOW + 30)], [], QC, NOW + 2000, enabled=True)
        self.assertEqual(hold3, {"quiet-a", "quiet-b"})
        # build ends: quiet placement resumes, history recorded
        st4, hold4, _ = rf.build_interstice_step(st2, [], [], [], QC, NOW + 300, enabled=True)
        self.assertEqual(hold4, set())
        self.assertIsNone(st4["active"])
        self.assertTrue(st4["history"]["autokernel"])

    def test_fifo_oldest(self):
        _, _, line = rf.build_interstice_step(ended(), [], [], [b("new", since=NOW - 10), b("old", since=NOW - 900)], QC, NOW, enabled=True)
        self.assertIn("grant old", line)

    def test_previous_tick_still_triggers_but_not_later(self):
        st, _, _ = rf.build_interstice_step(ended(), [], [], [], QC, NOW, enabled=True)   # gap, nothing queued
        _, hold, line = rf.build_interstice_step(st, [], [], [b("k1")], QC, NOW + 60, enabled=True)
        self.assertIsNotNone(line)
        st2, _, _ = rf.build_interstice_step(st, [], [], [], QC, NOW + 60, enabled=True)
        _, hold, line = rf.build_interstice_step(st2, [], [], [b("k1")], QC, NOW + 120, enabled=True)
        self.assertIsNone(line)
        self.assertEqual(hold, set())

    def test_urgent_head_first(self):
        qc = QC + [("urgent", 5.0, 600)]
        st, hold, line = rf.build_interstice_step(ended(), [], [], [b("k1")], qc, NOW, enabled=True)
        self.assertIsNone(line)
        self.assertEqual(hold, set())
        self.assertIsNone(st["active"])

    def test_over_cap_no_interstice(self):
        for q in ([b("k1", minutes=15)], [b("k1", minutes=30)], [b("k1", minutes=None)]):   # 900+margin, 1800, unknown=900+margin
            st, hold, line = rf.build_interstice_step(ended(), [], [], q, QC, NOW, enabled=True)
            self.assertIsNone(line)
            self.assertEqual(hold, set())

    def test_measured_history_used_when_undeclared(self):
        st = ended({"history": {"autokernel": [240, 300, 260]}})
        _, _, line = rf.build_interstice_step(st, [], [], [b("k1", minutes=None)], QC, NOW, enabled=True)
        self.assertIsNotNone(line)

    def test_one_build_per_gap(self):
        st, _, _ = rf.build_interstice_step(ended(), [], [], [b("k1"), b("k2")], QC, NOW, enabled=True)
        st2, _, _ = rf.build_interstice_step(st, [], [("build-x", "autokernel", NOW + 5)], [b("k2")], QC, NOW + 60, enabled=True)
        st3, hold, line = rf.build_interstice_step(st2, [], [], [b("k2")], QC, NOW + 300, enabled=True)
        self.assertIsNone(line)
        self.assertEqual(hold, set())

    def test_pending_pick_abandoned(self):
        st, _, _ = rf.build_interstice_step(ended(), [], [], [b("k1")], QC, NOW, enabled=True)
        st2, hold, _ = rf.build_interstice_step(st, [], [], [b("k1")], QC, NOW + rf.BUILD_INTERSTICE_PENDING_S + 1, enabled=True)
        self.assertEqual(hold, set())
        self.assertIsNone(st2["active"])

    def test_flag_off_old_behaviour(self):
        st, hold, line = rf.build_interstice_step(ended(), [], [], [b("k1")], QC, NOW, enabled=False)
        self.assertIsNone(line)
        self.assertEqual(hold, set())
        self.assertIsNone(st["active"])


class Adapter(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.flags = self.td.name
        os.makedirs(os.path.join(self.flags, "grants"), exist_ok=True)
        self.rows = {"quiet-a": {"requires_quiet_host": True, "priority_rank": 50, "estimate_s": 3600},
                     "plain": {"requires_quiet_host": False, "priority_rank": 50}}
        self.cands = [{"id": "quiet-a", "rank": 50.0, "options": [frozenset({"q0"})], "lane": "cpu"},
                      {"id": "plain", "rank": 50.0, "options": [frozenset({"q1"})], "lane": "cpu"}]
        rf.atomic_json(os.path.join(rf.state_dir(self.flags), rf.BUILD_INTERSTICE_STATE), {"quiet_running": ["gone"]})
        req = {"id": "req-autokernel-1", "owner": "autokernel", "minutes": 4, "requested_at": NOW - 100, "light": False}
        self.reqc = [{"id": "req-autokernel-1", "kind": "claim", "request": req}]

    def tearDown(self):
        self.td.cleanup()

    def _run(self, flag):
        old = rf.BUILD_INTERSTICE
        rf.BUILD_INTERSTICE = flag
        try:
            lines = []
            out = rf.apply_build_interstice(self.flags, list(self.cands), None, list(self.cands), self.reqc, [], self.rows,
                                            lines.append, now=NOW)
            return out, lines
        finally:
            rf.BUILD_INTERSTICE = old

    def test_on_holds_quiet_and_open_for_owner(self):
        (cands, _, info), lines = self._run(True)
        self.assertEqual([c["id"] for c in cands], ["plain"])
        self.assertIn("BUILD-INTERSTICE grant req-autokernel-1 before quiet-a", lines)
        self.assertEqual(info["hold"], {"quiet-a"})
        old = rf.BUILD_INTERSTICE
        try:
            self.assertTrue(rf.build_interstice_open_for(self.flags, "autokernel", now=NOW + 10))
            self.assertFalse(rf.build_interstice_open_for(self.flags, "other", now=NOW + 10))
        finally:
            rf.BUILD_INTERSTICE = old
        # REPLAN models the same interstice: the held quiet row is released at the build's end
        items, _, _ = rf.replan_items(self.cands, lambda r: self.rows.get(r, {}), [], set(rf.expand({"q0", "q1"})), {}, NOW,
                                      interstice=info)
        it = {i["id"]: i for i in items}
        self.assertEqual(it["quiet-a"]["rel"], info["until"])
        self.assertIsNone(it["plain"]["rel"])

    def test_off_reproduces_old(self):
        (cands, _, info), lines = self._run(False)
        self.assertEqual([c["id"] for c in cands], ["quiet-a", "plain"])
        self.assertIsNone(info)
        self.assertFalse(any("BUILD-INTERSTICE" in l for l in lines))


if __name__ == "__main__":
    unittest.main()

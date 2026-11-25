#!/usr/bin/env python3
"""GPU-URGENT (pipeline-mgmt 2026-11-25): PREEMPT-PROPOSE (advisory) and URGENT-SMOKE-AHEAD (hold a long low-rank GPU grant
while a rank<=3 GPU smoke is imminent). Replays the 11-25 opperf-cal-27b-r2 / kvtype-r4 inversions."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
URG = "ak-c22-urgent-gpu-20261125-r1"
RUN = "ak-opperf-cal-27b-20261125-r2"


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gcand(rid, rank, book_s, **kw):
    c = {"id": rid, "kind": "grant", "lane": "gpu", "rank": float(rank), "options": [frozenset({rf.GPU})],
         "shape": "gpu", "book_s": book_s, "window_s": book_s}
    c.update(kw)
    return c


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        for sub in ("ready", "grants", "dryrun"):
            os.makedirs(os.path.join(self.flags, sub))
        self.sd = os.path.join(self.flags, "state")
        os.makedirs(self.sd)
        self.passed = set()
        self.patches = [mock.patch.object(rf, "state_dir", lambda f: self.sd),
                        mock.patch.object(rf, "smoke_passed", lambda f, r, d=None: r in self.passed),
                        mock.patch.object(rf, "resolve_stop_path", lambda d: d.get("stop_file"))]
        for p in self.patches:
            p.start()
        self.emitted = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def emit(self, *a, **k):
        self.emitted.append(a)

    def row(self, rid, rank, t=NOW - 3600, **kw):
        d = {"id": rid, "priority_rank": rank, "lane": "gpu", "owner": "ak", "smoke_s": 1200}
        d.update(kw)
        p = rf.ready_path(self.flags, rid)
        with open(p, "w") as f:
            json.dump(d, f)
        os.utime(p, (t, t))
        return d

    def smoke(self, rid, t):
        p = os.path.join(self.flags, "dryrun", rid, "SMOKE-QUEUED.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump({"smoke_s": 1200}, f)
        os.utime(p, (t, t))

    def grant(self, rid, left_s):
        return {"id": rid, "end": iso(NOW + left_s), "holds": [rf.GPU]}


class Propose(Base):
    def test_trigger_non_resumable(self):
        self.row(RUN, 31, resumable=False)
        self.row(URG, 1)
        self.smoke(URG, NOW - 60)
        out = rf.preempt_propose(self.flags, [self.grant(RUN, 2 * 3600)], {}, lambda m: None, now=NOW, emit=self.emit)
        self.assertEqual(out, [(URG, RUN)])
        self.assertEqual(self.emitted[0][1], "preempt-proposal")
        msg = self.emitted[0][4]
        self.assertIn(URG, msg); self.assertIn(RUN, msg); self.assertIn("rank 31", msg); self.assertIn("120 min left", msg)
        self.assertIn("NOT resumable", msg)

    def test_trigger_resumable_gives_commands(self):
        self.row(RUN, 20, resumable=True, stop_file="/mnt/raid0/llm/tmp/x/STOP")
        self.row(URG, 2)
        self.passed.add(URG)   # ready, waiting for the GPU
        rf.preempt_propose(self.flags, [self.grant(RUN, 3 * 3600)], {}, lambda m: None, now=NOW, emit=self.emit)
        msg = self.emitted[0][4]
        self.assertIn("touch /mnt/raid0/llm/tmp/x/STOP", msg)
        self.assertIn(f"rowflow.py resume {RUN}", msg)

    def test_no_trigger_short_left(self):
        self.row(RUN, 31); self.row(URG, 1); self.smoke(URG, NOW - 60)
        self.assertEqual(rf.preempt_propose(self.flags, [self.grant(RUN, 3000)], {}, lambda m: None, now=NOW, emit=self.emit), [])

    def test_no_trigger_rank_below_20(self):
        self.row(RUN, 19); self.row(URG, 1); self.smoke(URG, NOW - 60)
        self.assertEqual(rf.preempt_propose(self.flags, [self.grant(RUN, 7200)], {}, lambda m: None, now=NOW, emit=self.emit), [])

    def test_no_trigger_urgent_rank_4(self):
        self.row(RUN, 31); self.row(URG, 4); self.smoke(URG, NOW - 60)
        self.assertEqual(rf.preempt_propose(self.flags, [self.grant(RUN, 7200)], {}, lambda m: None, now=NOW, emit=self.emit), [])

    def test_dedupe(self):
        self.row(RUN, 31); self.row(URG, 1); self.smoke(URG, NOW - 60)
        g = [self.grant(RUN, 7200)]
        self.assertEqual(len(rf.preempt_propose(self.flags, g, {}, lambda m: None, now=NOW, emit=self.emit)), 1)
        self.assertEqual(rf.preempt_propose(self.flags, g, {}, lambda m: None, now=NOW + 120, emit=self.emit), [])
        self.assertEqual(len(self.emitted), 1)


class SmokeAhead(Base):
    def test_incident_replay_holds_rank31(self):
        # 11-25: rank-1 GPU row published, smoke queued minutes later; the keeper must not grant the rank-31 2.5 h window.
        self.row(URG, 1, t=NOW - 120)
        self.smoke(URG, NOW - 60)
        pend = rf.urgent_gpu_pending(self.flags, [], {}, now=NOW)
        kvt = gcand("ak-kvtype-20261125-r4", 31, 9000)
        kept, lines = rf.urgent_smoke_ahead_filter(pend, [kvt], now=NOW)
        self.assertEqual(kept, [])
        self.assertIn("URGENT-SMOKE-AHEAD", list(lines.values())[0])

    def test_published_awaiting_smoke_holds(self):
        self.row(URG, 1, t=NOW - 300)   # no smoke marker yet
        pend = rf.urgent_gpu_pending(self.flags, [], {}, now=NOW)
        self.assertEqual(pend[0]["state"], "published")
        self.assertEqual(rf.urgent_smoke_ahead_filter(pend, [gcand("x", 31, 9000)], now=NOW)[0], [])

    def test_old_publish_and_fits_and_short_pass(self):
        self.row(URG, 1, t=NOW - 3600)   # published an hour ago, never smoked: not imminent
        self.assertEqual(rf.urgent_gpu_pending(self.flags, [], {}, now=NOW), [])
        pend = [{"id": URG, "rank": 1, "state": "smoke", "since": NOW, "end": NOW + 7200}]
        cs = [gcand("fits", 31, 5400), gcand("short", 31, 1800), gcand("hi", 10, 9000),
              dict(gcand("cpu", 50, 9000), lane="cpu", options=[frozenset({"q0"})])]
        kept, _ = rf.urgent_smoke_ahead_filter(pend, cs, now=NOW)
        self.assertEqual([c["id"] for c in kept], ["fits", "short", "hi", "cpu"])

    def test_ready_urgent_does_not_hold(self):
        self.row(URG, 1); self.passed.add(URG)
        pend = rf.urgent_gpu_pending(self.flags, [], {}, now=NOW)
        self.assertEqual(pend[0]["state"], "ready")
        self.assertEqual(len(rf.urgent_smoke_ahead_filter(pend, [gcand("x", 31, 9000)], now=NOW)[0]), 1)


if __name__ == "__main__":
    unittest.main()

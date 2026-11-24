#!/usr/bin/env python3
"""SLOT-KEEP (pipeline-mgmt 2026-11-24): a row briefly off the grant table (build-window pause, successor republish) keeps its
slot from lower-ranked candidates, bounded at 30 min. Replays the 18:30Z r8h and 18:21Z cdr inversions."""
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
CENSUS = "ak-c21-census-refresh-cpu-20261124-r4"


def cand(rid, rank, opts, **kw):
    c = {"id": rid, "kind": "grant", "lane": "cpu", "rank": float(rank), "options": [frozenset(o) for o in opts],
         "shape": "quarter"}
    c.update(kw)
    return c


def fake_contract(d, o=None, flags=None):
    return {"options": [frozenset(rf.expand({q})) for q in d.get("_q", ["q0"])], "shape": d.get("shape", "quarter")}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        for sub in ("ready", "grants", "dryrun"):
            os.makedirs(os.path.join(self.flags, sub))
        self.sd = os.path.join(self.flags, "state")
        os.makedirs(self.sd)
        self.patches = [mock.patch.object(rf, "state_dir", lambda f: self.sd),
                        mock.patch.object(rf, "contract_of", fake_contract),
                        mock.patch.object(rf, "quiet_sensitive", lambda d: bool((d or {}).get("requires_quiet_host"))),
                        mock.patch.object(rf, "smoke_passed", lambda f, r, d=None: False)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def row(self, rid, rank, quiet=False, stop=None, **kw):
        d = {"id": rid, "priority_rank": rank, "requires_quiet_host": quiet, "shape": "quiet-host" if quiet else "quarter",
             "_q": ["q0"], "resumable": True}
        if stop:
            d["stop_file"] = stop
        d.update(kw)
        with open(rf.ready_path(self.flags, rid), "w") as f:
            json.dump(d, f)
        return d

    def touch(self, p, t, text="x"):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        os.utime(p, (t, t))


class BuildWindowPause(Base):
    def setUp(self):
        super().setUp()
        self.stop = os.path.join(self.flags, "work", "STOP")
        self.touch(self.stop, NOW - 120)
        self.census = self.row(CENSUS, 42, quiet=True, stop=self.stop)
        with open(os.path.join(self.sd, rf.BUILD_WINDOW), "w") as f:
            json.dump({"by": "ak", "until": NOW + 600}, f)
        self.r8h = cand("tf1-cpu-r8h-canary-35b-q0q2-20261124", 100, [{"q1"}], loud=True)
        self.draftwin = cand("draftwin-r3", 40, [{"q2"}], loud=True)

    def holds(self, now=NOW):
        with mock.patch.object(rf, "resolve_stop_path", lambda d: d.get("stop_file")):
            return rf.slot_keep_holds(self.flags, [], {}, now=now)

    def test_rank100_loud_refused_during_pause(self):
        h = self.holds()
        self.assertEqual([x["id"] for x in h], [CENSUS])
        self.assertAlmostEqual(h[0]["until"], NOW + 600 + rf.SLOT_KEEP_GRACE_S)
        kept, lines = rf.slot_keep_filter(h, [self.r8h, self.draftwin], {})
        self.assertEqual([c["id"] for c in kept], ["draftwin-r3"])   # higher rank passes through
        self.assertTrue(any(f"SLOT-KEEP hold {CENSUS} rank=42 refuse tf1-cpu-r8h" in v for v in lines.values()))

    def test_lapses_after_cap(self):
        with open(os.path.join(self.sd, rf.BUILD_WINDOW), "w") as f:
            json.dump({"by": "ak", "until": NOW + 5400}, f)
        h = self.holds()
        self.assertAlmostEqual(h[0]["until"], NOW - 120 + rf.SLOT_KEEP_CAP_S)
        self.assertEqual(self.holds(now=NOW - 120 + rf.SLOT_KEEP_CAP_S + 1), [])

    def test_plain_owner_stop_holds_nothing(self):
        """No build window: an owner STOP (e.g. the coordinator's STOP of r8h) is not a slot hold."""
        os.remove(os.path.join(self.sd, rf.BUILD_WINDOW))
        self.assertEqual(self.holds(), [])

    def test_window_closed_over_grace_ago_holds_nothing(self):
        with open(os.path.join(self.sd, rf.BUILD_WINDOW), "w") as f:
            json.dump({"by": "ak", "minutes": 10, "until": NOW - rf.SLOT_KEEP_GRACE_S - 1}, f)
        self.assertEqual(self.holds(), [])

    def test_stop_before_window_holds_nothing(self):
        with open(os.path.join(self.sd, rf.BUILD_WINDOW), "w") as f:
            json.dump({"by": "ak", "minutes": 1, "until": NOW + 60}, f)   # opened at NOW; STOP 5 min earlier
        self.touch(self.stop, NOW - 300)
        self.assertEqual(self.holds(), [])

    def test_flag_off(self):
        with mock.patch.object(rf, "SLOT_KEEP", False), mock.patch.object(rf, "resolve_stop_path", lambda d: d.get("stop_file")):
            self.assertEqual(rf.slot_keep_holds(self.flags, [], {}, now=NOW), [])

    def test_granted_row_holds_nothing(self):
        with mock.patch.object(rf, "resolve_stop_path", lambda d: d.get("stop_file")):
            self.assertEqual(rf.slot_keep_holds(self.flags, [{"id": CENSUS}], {}, now=NOW), [])


class SuccessorRepublish(Base):
    def setUp(self):
        super().setUp()
        self.patches.append(mock.patch.object(rf, "resolve_stop_path", lambda d: None))
        self.patches[-1].start()
        pred = CENSUS[:-1] + "3"
        self.row(pred, 42, quiet=True)
        self.touch(os.path.join(self.flags, "grants", pred + ".complete"), NOW - 900)
        self.touch(os.path.join(rf.dry_dir(self.flags, CENSUS), "unpublished.json"), NOW - 60,
                   json.dumps({"id": CENSUS, "priority_rank": 42, "requires_quiet_host": True, "shape": "quiet-host",
                               "_q": ["q0"], "supersedes": pred, "smoke_s": 900}))

    def test_cdr_refused_during_republish(self):
        h = rf.slot_keep_holds(self.flags, [], {}, now=NOW)
        self.assertEqual([x["id"] for x in h], [CENSUS])
        self.assertAlmostEqual(h[0]["until"], NOW - 60 + 900)
        cdr = cand("cdr", 45, [{"q0"}])
        kept, lines = rf.slot_keep_filter(h, [cdr, cand("better", 30, [{"q0"}])], {})
        self.assertEqual([c["id"] for c in kept], ["better"])
        self.assertIn(f"{CENSUS}|cdr", lines)

    def test_successor_lapses_after_budget(self):
        self.assertEqual(rf.slot_keep_holds(self.flags, [], {}, now=NOW + 900), [])

    def test_non_quiet_hold_narrows_options(self):
        h = [{"id": "x", "rank": 20.0, "until": NOW + 60, "since": NOW, "why": "t", "tokens": rf.expand({"q0"}), "quiet": False}]
        kept, _ = rf.slot_keep_filter(h, [cand("low", 50, [{"q0"}, {"q1"}], loud=True)], {})
        self.assertEqual(kept[0]["options"], [frozenset({"q1"})])


if __name__ == "__main__":
    unittest.main()

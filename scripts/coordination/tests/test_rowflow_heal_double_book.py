#!/usr/bin/env python3
"""HEAL-DBL 2026-11-24: build-autokernel-20261124T100323Z-cc70ff (q0, 10:03:23Z) was double-booked by a row grant written
19 s later from a stale tick snapshot; HEAL then withdrew the EARLIER build claim, alerted no one, and `release` refused
the surviving .build.json. Regression tests for the three fixes."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

BID = "build-autokernel-20261124T100323Z-cc70ff"
RID = "ak-cpu-gdn-state-fwd-20261123-r2"


class HealDoubleBook(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.mkdtemp(prefix="dbl-")
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.log = []
        self.alerts = []
        p = mock.patch.object(rf.notify, "emit", side_effect=lambda fl, kind, rid, disc, summ, sev, owner="", detail=None, **k:
                              self.alerts.append((kind, rid, owner, detail)))
        p.start(); self.addCleanup(p.stop)

    def put(self, name, text):
        with open(os.path.join(self.G, name), "w") as fh:
            fh.write(text)

    def build(self, at="2026-11-24T10:03:23Z"):
        self.put(BID + ".grant", "regions=q0 start=2026-11-24T10:03Z end=2026-11-24T11:33Z holds=q0\n")
        self.put(BID + ".build.json", json.dumps({"id": BID, "owner": "autokernel", "kind": "build", "quarters": ["q0"],
                                                  "cpus": "0-23,96-119", "minutes": 90, "at": at}))

    def row(self, at="2026-11-24T10:03:42Z"):
        self.put(RID + ".grant", "regions=0-23 start=2026-11-24T10:03Z end=2026-11-24T12:00Z holds=q0\n")
        rf.atomic_json(rf.granted_path(self.f, RID), {"id": RID, "at": at})

    # fix 1: the allocator's write re-checks on-disk claims under the claim lock
    def test_row_grant_refused_onto_build_claim(self):
        self.build()
        line, clash = rf.write_row_grant_locked(self.f, RID, "0-23", {"q0"}, 3600)
        self.assertIsNone(line)
        self.assertEqual(clash, BID)
        self.assertFalse(os.path.exists(os.path.join(self.G, RID + ".grant")))

    def test_row_grant_refused_onto_build_json_only(self):
        self.build()
        os.remove(os.path.join(self.G, BID + ".grant"))
        _, clash = rf.write_row_grant_locked(self.f, RID, "0-23", {"q0"}, 3600)
        self.assertEqual(clash, BID)

    def test_row_grant_ok_on_free_quarter(self):
        self.build()
        line, clash = rf.write_row_grant_locked(self.f, RID, "24-47", {"q1"}, 3600)
        self.assertIsNone(clash)
        self.assertTrue(os.path.exists(os.path.join(self.G, RID + ".grant")))

    # fix 2: HEAL keeps the earlier claim and alerts the withdrawn one's owner
    def test_heal_keeps_earlier_build_withdraws_later_row(self):
        self.build(); self.row()
        kept = rf.heal_grants(self.f, rf.open_grants(self.f), {"q0": ("HELD", f"filler-{RID}")}, self.log.append, set())
        self.assertEqual([g["id"] for g in kept], [BID])
        self.assertTrue(os.path.exists(os.path.join(self.G, BID + ".grant")))
        self.assertFalse(os.path.exists(os.path.join(self.G, RID + ".grant")))   # not started: requeued next tick
        self.assertIn(f"HEAL-CONFLICT kept {BID} withdrew {RID}", self.log)
        self.assertEqual([(a[0], a[1]) for a in self.alerts], [("heal-conflict", RID)])

    def test_heal_withdraws_later_build_and_alerts_owner(self):
        self.row(at="2026-11-24T10:00:00Z"); self.build()
        kept = rf.heal_grants(self.f, rf.open_grants(self.f), {"q0": ("HELD", f"filler-{RID}")}, self.log.append, set())
        self.assertEqual([g["id"] for g in kept], [RID])
        self.assertFalse(os.path.exists(os.path.join(self.G, BID + ".grant")))
        self.assertIn(f"HEAL-CONFLICT kept {RID} withdrew {BID}", self.log)
        self.assertEqual(self.alerts[0][:3], ("heal-conflict", BID, "autokernel"))
        bj = json.load(open(os.path.join(self.G, BID + ".build.json")))
        self.assertTrue(bj.get("heal_withdrawn"))

    def test_release_heal_withdrawn_build_idempotent(self):
        self.row(at="2026-11-24T10:00:00Z"); self.build()
        rf.heal_grants(self.f, rf.open_grants(self.f), {"q0": ("HELD", f"filler-{RID}")}, self.log.append, set())
        rel = lambda: rf.release_grant(self.f, BID, "autokernel", "heal-withdrawn", log=self.log.append)
        self.assertEqual(rel(), "RELEASED")
        self.assertEqual(rel(), "RELEASED")
        self.assertTrue(os.path.exists(os.path.join(self.G, BID + ".ended")))

    # fix 3: release accepts a build claim left only as .build.json, idempotently
    def test_release_build_json_only_idempotent(self):
        self.build()
        os.remove(os.path.join(self.G, BID + ".grant"))
        rel = lambda: rf.release_grant(self.f, BID, "autokernel", "heal-withdrawn", log=self.log.append)
        self.assertEqual(rel(), "RELEASED")
        self.assertTrue(os.path.exists(os.path.join(self.G, BID + ".ended")))
        with self.assertRaises(rf.Refused):   # a plain ended build stays "already ended"
            rel()
        with self.assertRaises(rf.Refused):
            rf.release_grant(self.f, BID, "someone-else", "x", log=self.log.append)


if __name__ == "__main__":
    unittest.main()

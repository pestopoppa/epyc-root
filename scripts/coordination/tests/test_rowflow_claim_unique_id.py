#!/usr/bin/env python3
"""CLAIM-ID 2026-11-21: concurrent same-second `claim --build` on identical cores must not share a grant id (build-autokernel-
20261121T210214Z was minted twice; the first release freed cores the second still built on). Real flags dir, no injected
snapshot, a frozen `now` so every claim lands in the same UTC second."""
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1795294934.0   # one fixed second


class ClaimUniqueId(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="cuid-")
        os.makedirs(os.path.join(self.flags, "grants"))
        p = mock.patch.object(rf, "contract_of", side_effect=lambda d, flags=None: {"bench": False})
        p.start(); self.addCleanup(p.stop)
        p2 = mock.patch.object(rf, "host_snapshot", side_effect=self._snap)   # idle host: only on-disk grants hold anything
        p2.start(); self.addCleanup(p2.stop)

    def _snap(self, flags, grants):
        all_ = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
        busy = set()
        for g in grants:
            busy |= rf.expand(set(g["holds"]))
        busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
        return None, all_ - busy, None

    def claim(self, cpus, owner="autokernel"):
        return rf.claim_build(self.flags, owner, cpus, 30, log=lambda m: None, now=NOW)

    def test_concurrent_same_second_identical_cores_one_wins(self):
        res, bar = [], threading.Barrier(6)

        def w():
            bar.wait()
            try:
                res.append(("ok", self.claim("72-87")[0]))
            except rf.Refused as e:
                res.append(("refused", str(e)))
        ts = [threading.Thread(target=w) for _ in range(6)]
        [t.start() for t in ts]; [t.join() for t in ts]
        oks = [r for r in res if r[0] == "ok"]
        self.assertEqual(len(oks), 1, res)
        self.assertEqual(len([r for r in res if r[0] == "refused"]), 5)
        self.assertIn(oks[0][1], [g["id"] for g in rf.open_grants(self.flags)])
        self.assertEqual(len(rf.open_grants(self.flags)), 1)

    def test_sequential_second_claim_refused_naming_holder(self):
        gid, _ = self.claim("72-87")
        with self.assertRaises(rf.Refused) as c:
            self.claim("72-87")
        self.assertIn(gid, str(c.exception))

    def test_different_cores_both_succeed_distinct_ids(self):
        a, _ = self.claim("72-79")
        b, _ = self.claim("80-87")
        self.assertNotEqual(a, b)
        self.assertEqual({g["id"] for g in rf.open_grants(self.flags)}, {a, b})

    def test_ids_unique_and_exclusive(self):
        t = rf.dt.datetime.fromtimestamp(NOW, rf.dt.timezone.utc)
        ids = {rf._new_build_id(self.flags, "o", t) for _ in range(20)}
        self.assertEqual(len(ids), 20)

    def test_release_only_affects_own_id(self):
        a, _ = self.claim("72-79")
        b, _ = self.claim("80-87")
        self.assertEqual(rf.release_grant(self.flags, a, "autokernel", "done", log=lambda m: None), "RELEASED")
        self.assertEqual({g["id"] for g in rf.open_grants(self.flags)}, {b})
        # the freed cores are claimable again; b's are still refused
        self.claim("72-79")
        with self.assertRaises(rf.Refused):
            self.claim("80-87")


if __name__ == "__main__":
    unittest.main()

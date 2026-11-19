"""Pipeline audit 2026-11-10 #5 (smoke pockets, replaces the fix-8 fill-first ordering): queued smokes are placed FIFO into
the per-quarter SMT pockets, so whole free quarters stay whole for rows and smokes never wait for them.
Temp flags only; place_smokes runs dry (nothing is started)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)


def free_minus(*tokens):
    busy = rf.expand(set(tokens))
    busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
    return ALL - busy


class SmokeFillOrder(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))

    def queue(self, rid, regions, at):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "unpublished.json"), {"id": rid, "lane": "cpu", "regions": regions})
        rf.atomic_json(rf.smoke_queued_path(self.flags, rid), {"id": rid, "queued_at": at})

    def order(self, free):
        logs = []
        placed = rf.place_smokes(self.flags, set(free), logs.append, dry=True)
        return [rid for rid, _ in placed]

    def test_three_smokes_run_at_once_with_every_quarter_whole(self):
        for i, rid in enumerate(("a", "b", "c", "d")):
            self.queue(rid, "0-23", f"2026-11-10T0{i}:00Z")
        logs = []
        placed = rf.place_smokes(self.flags, set(ALL), logs.append, dry=True)
        self.assertEqual(placed, [("a", "116-119"), ("b", "140-143"), ("c", "164-167")])
        self.assertTrue(any(l.startswith("SMOKE-WAIT d:") for l in logs))   # every quarter whole: d waits, none broken

    def test_fifo(self):
        self.queue("a", "0-23", "2026-11-10T00:00Z")
        self.queue("b", "48-71", "2026-11-10T01:00Z")
        self.assertEqual(self.order(ALL), ["a", "b"])

    def test_wider_smoke_uses_a_partly_used_quarter(self):
        os.makedirs(rf.dry_dir(self.flags, "w"), exist_ok=True)
        rf.atomic_json(rf.smoke_queued_path(self.flags, "w"), {"id": "w", "queued_at": "x", "cpus": 8})
        free = free_minus("q0") | {f"c{n}" for n in range(0, 8)} | {f"t{n}" for n in range(96, 104)}
        logs = []
        self.assertEqual(rf.place_smokes(self.flags, free, logs.append, dry=True), [("w", "0-7")])


if __name__ == "__main__":
    unittest.main()

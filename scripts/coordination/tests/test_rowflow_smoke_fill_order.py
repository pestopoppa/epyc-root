"""Keeper audit 2026-11-10 fix 8: queued smokes whose row could fill a region idle NOW are placed first; ties stay FIFO.
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

    def test_rank(self):
        self.queue("fills", "48-71", "2026-11-10T01:00Z")
        self.queue("busy", "0-23", "2026-11-10T00:00Z")
        free = free_minus("q0", "q1", "q3")
        self.assertEqual(rf.smoke_fill_rank(self.flags, "fills", free), 0)
        self.assertEqual(rf.smoke_fill_rank(self.flags, "busy", free), 2)
        self.assertEqual(rf.smoke_fill_rank(self.flags, "unknown", free), 2)

    def test_idle_filler_goes_before_an_older_smoke(self):
        self.queue("old-q0", "0-23", "2026-11-10T00:00Z")
        self.queue("new-q2", "48-71", "2026-11-10T01:00Z")
        # q0 busy except c20-c23 (smoke room), q2 whole free: the q2 row's smoke is placed first
        free = free_minus("q0", "q1", "q3") | {f"c{n}" for n in range(20, 24)} | {f"t{n}" for n in range(116, 120)}
        self.assertEqual(self.order(free)[0], "new-q2")

    def test_fifo_kept_without_fill_signal_and_with_knob_off(self):
        self.queue("a", "0-23", "2026-11-10T00:00Z")
        self.queue("b", "48-71", "2026-11-10T01:00Z")
        self.assertEqual(self.order(ALL), ["a", "b"])   # both fill: FIFO
        old = rf.SMOKE_FILL_FIRST
        try:
            rf.SMOKE_FILL_FIRST = False
            free = free_minus("q0", "q1", "q3") | {f"c{n}" for n in range(20, 24)}
            self.assertEqual(self.order(free)[0], "a")
        finally:
            rf.SMOKE_FILL_FIRST = old


if __name__ == "__main__":
    unittest.main()

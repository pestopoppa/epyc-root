"""D9 2026-11-18 SMOKE-CPUS: spec smoke_cpus (4..24) is written into SMOKE-QUEUED's cpus and honoured by place_smokes;
a 24-wide smoke may take a whole free q0-q2 quarter, never q3 88-95 while a GPU row is queued, never drain-reserved
cores. Temp flags only; place_smokes runs dry (nothing is started)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402
import publish_row as pr  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)


def free_minus(*tokens):
    busy = rf.expand(set(tokens))
    busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
    return ALL - busy


class SmokeCpus(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))

    def queue(self, rid, cpus=None):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rec = {"id": rid, "queued_at": "x"}
        if cpus is not None:
            rec["cpus"] = cpus
        rf.atomic_json(rf.smoke_queued_path(self.flags, rid), rec)

    def test_smoke_cpus_written_through(self):
        pr.queue_cpu_smoke(self.flags, "r", {"id": "r", "smoke_cpus": 24}, 600)
        self.assertEqual(rf.load_json(rf.smoke_queued_path(self.flags, "r"))["cpus"], 24)

    def test_default_stays_4(self):
        self.assertEqual(rf.SMOKE_CPUS, 4)
        pr.queue_cpu_smoke(self.flags, "r", {"id": "r"}, 600)
        self.assertEqual(rf.load_json(rf.smoke_queued_path(self.flags, "r"))["cpus"], 4)

    def test_out_of_range_refused(self):
        for bad in (3, 25, 0, "8", 8.0, True):
            with self.assertRaises(rf.Refused):
                pr.smoke_cpus_of({"smoke_cpus": bad})
        self.assertEqual(pr.smoke_cpus_of({"smoke_cpus": 16}), 16)

    def test_24_placed_on_free_q0_q2_quarter(self):
        self.queue("w", 24)
        self.assertEqual(rf.place_smokes(self.flags, set(ALL), print, dry=True), [("w", "0-23")])
        self.queue("w", 24)
        self.assertEqual(rf.place_smokes(self.flags, free_minus("q0"), print, dry=True), [("w", "24-47")])

    def test_24_not_whole_quarter_unless_requested(self):
        self.queue("n", 8)
        logs = []
        self.assertEqual(rf.place_smokes(self.flags, free_minus(*rf.QUARTERS[:3]) - rf.POCKET_TOKENS, logs.append,
                                         dry=True), [])

    def test_not_on_q3_guard_while_gpu_queued(self):
        self.queue("w", 24)
        free = free_minus("q0", "q1", "q2")
        logs = []
        self.assertEqual(rf.place_smokes(self.flags, set(free), logs.append, dry=True, gpu_queued=True), [])
        self.assertTrue(any(l.startswith("SMOKE-WAIT w:") for l in logs))
        placed = rf.place_smokes(self.flags, set(free), print, dry=True)   # no GPU row queued: q3 is allowed
        self.assertEqual(placed, [("w", "72-95")])
        self.queue("p", 8)   # a narrower smoke in partly used q3 never lands on 88-95 under the guard
        free = free_minus("q0", "q1", "q2", "c72")
        placed = rf.place_smokes(self.flags, set(free), print, dry=True, gpu_queued=True)
        for _, cpus in placed:
            self.assertFalse(rf.cpu_tokens(cpus, gpu_threads=True) & rf.Q3_GUARD)

    def test_not_on_drain_reserved_cores(self):
        self.queue("w", 24)
        logs = []
        free = free_minus("q1", "q2", "q3")
        self.assertEqual(rf.place_smokes(self.flags, set(free), logs.append, dry=True,
                                         drain_reserved=frozenset({"q0"})), [])
        self.assertTrue(any(l.startswith("SMOKE-WAIT w:") for l in logs))
        self.assertEqual(rf.place_smokes(self.flags, set(ALL), print, dry=True, drain_reserved=frozenset({"q0"})),
                         [("w", "24-47")])

    def test_wide_smoke_waits_for_grantable_row_quarter(self):
        self.queue("w", 24)
        free = free_minus("q1", "q2", "q3")
        logs = []
        self.assertEqual(rf.place_smokes(self.flags, set(free), logs.append, dry=True,
                                         demand_reserved=frozenset({"q0"})), [])
        self.assertTrue(any(l.startswith("SMOKE-WAIT w:") for l in logs))
        self.queue("p")   # a 4-core pocket smoke is unchanged by demand
        self.assertEqual(rf.place_smokes(self.flags, set(ALL), print, dry=True,
                                         demand_reserved=frozenset(rf.QUARTERS))[-1], ("p", "116-119"))


if __name__ == "__main__":
    unittest.main()

"""PIPE-EVE-RAM-MARGIN (2026-11-10): the allocator's RAM margin is the ratified 100 GiB job_fence margin, and the row's
ram_gib is injected into the armed job as job_fence's admission inputs."""
import os
import sys
import unittest

_RF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow")
sys.path.insert(0, _RF)
sys.path.insert(0, os.path.join(os.path.dirname(_RF), "job_templates"))
import rowflow as rf  # noqa: E402
import job_fence as jf  # noqa: E402


def cand(rid, gib):
    return {"id": rid, "gib": gib, "options": [frozenset(rf.expand({"q0"}))], "rank": 1}


class RamMarginTests(unittest.TestCase):
    def test_margin_matches_job_fence(self):
        self.assertEqual(rf.RAM_MARGIN_GIB, 100)
        self.assertEqual(rf.RAM_MARGIN_GIB, jf.RAM_MARGIN_GIB)

    def test_fits_refuses_inside_100_but_above_64(self):
        free = set(rf.expand({"q0", "q1", "q2", "q3"}))
        self.assertEqual(rf._fits(cand("a", 48), free, 48 + 80, False), [])     # leaves 80 GiB: was admitted at 64
        self.assertTrue(rf._fits(cand("b", 48), free, 48 + 100, False))         # leaves exactly 100 GiB

    def test_ram_gib_injected_into_job_env(self):
        env = rf.ram_fence_env({"gib": 300}, {})
        self.assertEqual(env["JOB_FENCE_NEED_RAM_GIB"], "300")
        self.assertEqual(env["JOB_FENCE_RAM_MARGIN_GIB"], "100")
        _, need, margin = jf._take_ram(["/w"], env=env)
        self.assertEqual((need, int(margin)), ("300", 100))

    def test_launcher_value_wins_and_zero_is_not_injected(self):
        env = rf.ram_fence_env({"gib": 300}, {"JOB_FENCE_NEED_RAM_GIB": "20"})
        self.assertEqual(env["JOB_FENCE_NEED_RAM_GIB"], "20")
        self.assertNotIn("JOB_FENCE_NEED_RAM_GIB", rf.ram_fence_env({"gib": 0}, {}))


if __name__ == "__main__":
    unittest.main()

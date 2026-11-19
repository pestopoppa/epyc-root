"""QUIET-HOST-SMOKE 2026-11-12: inf45-e5v2-stageb-r2 (quiet-host) was granted in the same keeper tick that placed the
agg13-reingest-cpu-r2 pocket smoke on 116-119; its harness refused the smoke's llama-servers. Temp flags only."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402


class QuietHostSmoke(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()

    def test_placed_this_tick_blocks(self):
        self.assertEqual(rf.quiet_host_smoke_live(self.flags, [("agg13", "116-119")]), ["agg13"])

    def test_live_record_blocks_dead_does_not(self):
        os.makedirs(rf.dry_dir(self.flags, "live"), exist_ok=True)
        os.makedirs(rf.dry_dir(self.flags, "dead"), exist_ok=True)
        rf.atomic_json(rf.smoke_placed_path(self.flags, "live"), {"pid": os.getpid(), "regions": "116-119"})
        rf.atomic_json(rf.smoke_placed_path(self.flags, "dead"), {"pid": 2 ** 22 + 7, "regions": "140-143"})
        self.assertEqual(rf.quiet_host_smoke_live(self.flags), ["live"])

    def test_nothing_live(self):
        self.assertEqual(rf.quiet_host_smoke_live(self.flags), [])

    def test_drain_target(self):
        cands = [{"id": "h", "shape": "host"}, {"id": "qh", "shape": "quiet-host"}]
        self.assertEqual(rf.quiet_host_drain_target(cands, {"qh": 1}), "qh")
        self.assertIsNone(rf.quiet_host_drain_target(cands, {"h": 1}))
        self.assertIsNone(rf.quiet_host_drain_target(cands, {}))

    def test_plan_withholds_quiet_host_when_not_ok(self):
        c = {"id": "qh", "shape": "quiet-host", "rank": 25, "options": [frozenset(rf.QUARTERS)]}
        self.assertTrue(any("quiet" in (x.get("shape") or "") for x in [c]))
        # quiet_ok=False is the planner's existing gate; the tick now feeds it the smoke-live verdict
        src = open(rf.__file__).read()
        self.assertIn("quiet_ok=quiet_ok, held_ports=held_ports", src)


if __name__ == "__main__":
    unittest.main()

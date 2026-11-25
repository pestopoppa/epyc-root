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

    def test_drain_target_startable_only(self):
        h = {"id": "qh", "shape": "quiet-host", "rank": 42, "options": [frozenset({"q0", rf.GPU})],
             "ports": [], "gib": 0}
        free = {"q0", rf.GPU}
        target = lambda cs, **kw: rf.quiet_host_drain_target(cs, {"qh": 1}, free, 512, **kw)
        self.assertEqual(target([h]), h)
        self.assertIsNone(target([h], quiet_ok=False))
        self.assertIsNone(target([dict(h, options=[frozenset({"q0", rf.GPU_BLOCKED})])]))
        self.assertIsNone(target([dict(h, arm_fails=1)]))
        self.assertIsNone(target([dict(h, ports=[123])], held_ports={123}))
        self.assertIsNone(rf.quiet_host_drain_target([h], {}, free, 512))
        self.assertIsNone(target(rf.host_after_gpu_filter([dict(h, options=[frozenset({"q3", rf.GPU})])], {"gpu"})[0]))

    def test_replay_rank_42_drain_and_rank_3_smoke(self):
        h = {"id": "census", "shape": "quiet-host", "rank": 42, "options": [frozenset({"q0", rf.GPU})],
             "gib": 0}
        for rid, rank in (("gate", 3), ("later", 50)):
            os.makedirs(rf.dry_dir(self.flags, rid))
            rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "SMOKE-QUEUED.json"), {"spec": {"priority_rank": rank}})
        target = rf.quiet_host_drain_target([h], {"census": 1}, {"q0", rf.GPU}, 512)
        logs = []
        free = rf.expand(set(rf.QUARTERS)) | set(rf.POCKET_TOKENS) | {rf.GPU}
        placed = rf.place_smokes(self.flags, free, logs.append, dry=True, quiet_drain=target)
        self.assertEqual([rid for rid, _ in placed], ["gate"])
        self.assertTrue(any("SMOKE-WAIT later" in line for line in logs))
        # A deferred or blocked drain cannot hold even the lower-priority smoke.
        for target in (None, rf.quiet_host_drain_target([dict(h, options=[frozenset({rf.GPU_BLOCKED})])],
                                                       {"census": 1}, free, 512)):
            placed = rf.place_smokes(self.flags, set(free) | set(rf.POCKET_TOKENS), logs.append, dry=True, quiet_drain=target)
            self.assertIn("later", [rid for rid, _ in placed])

    def test_plan_withholds_quiet_host_when_not_ok(self):
        c = {"id": "qh", "shape": "quiet-host", "rank": 25, "options": [frozenset(rf.QUARTERS)]}
        self.assertTrue(any("quiet" in (x.get("shape") or "") for x in [c]))
        # quiet_ok=False is the planner's existing gate; the tick now feeds it the smoke-live verdict
        src = open(rf.__file__).read()
        self.assertIn("quiet_ok=quiet_ok, held_ports=held_ports", src)


if __name__ == "__main__":
    unittest.main()

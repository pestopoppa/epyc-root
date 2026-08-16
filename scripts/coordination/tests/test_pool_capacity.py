#!/usr/bin/env python3
"""PD-1: the pool must be able to reach its own concurrency bound.

THE DEFECT, measured 2026-08-16. `compute_advice` skipped any agent already
present in a set of owners holding a live row. For a session that is exactly
right — one tmux main does one task. For the worker pool it was wrong in a way
that silently capped throughput at 1: the whole pool is a SINGLE roster identity
(`workerpool`) fronting up to four concurrent runners, so the first row assigned
to it made the entire pool read busy and no second row could be picked.

`max_concurrent_workers: 4` was therefore unreachable through the daemon. The
pilot did reach three concurrent workers, but they were hand-dispatched with
`--pilot-override`, straight past the picker — so the measured throughput never
exercised this path, and reporting it as evidence of pool concurrency would have
been the "dispatch reported as utilisation" error the plan exists to end.

WHAT THESE TESTS HOLD:
  * a session's capacity is 1, unchanged — the regression that would matter most
  * an exec pool's capacity is its concurrency, FLOORED BY THE LANES THAT EXIST
  * the floor is the real directory count, because a lane is a worktree and two
    workers in one worktree is the shared-clone commit-sweep hazard
  * an unreadable pool root falls to 1, never to the configured number
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import session_bus_coordinator as C  # noqa: E402

SESSION = {"id": "inference", "role": "main", "endpoint": "tmux:agent:inference"}
POOL = {"id": "workerpool", "role": "main", "endpoint": "exec:worker_runner"}


class OwnerCapacityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="poolcap-"))
        self.pool = self.tmp / "pool"
        self.pool.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cfg(self, cap=4, root=None):
        return {"worker_pool": {"max_concurrent_workers": cap,
                                "pool_root": str(root if root is not None else self.pool)}}

    def lanes(self, n):
        for i in range(n):
            (self.pool / f"lane{i}").mkdir(parents=True, exist_ok=True)

    # -- the regression that would matter most ----------------------------

    def test_a_session_still_has_capacity_one(self):
        """Unchanged behaviour for every non-pool agent."""
        self.lanes(4)
        self.assertEqual(C._owner_capacity(SESSION, self.cfg(cap=4)), 1)

    # -- the defect itself -------------------------------------------------

    def test_pool_capacity_is_the_configured_cap_when_lanes_exist(self):
        self.lanes(4)
        self.assertEqual(C._owner_capacity(POOL, self.cfg(cap=4)), 4)

    def test_pool_capacity_is_FLOORED_by_the_lanes_that_exist(self):
        """A config asking for 4 with 2 lanes on disk grants 2, not 4.

        Two workers in one worktree is the commit-sweep hazard; scaling past the
        lanes present has to be a deliberate, operator-visible step.
        """
        self.lanes(2)
        self.assertEqual(C._owner_capacity(POOL, self.cfg(cap=4)), 2)

    def test_no_lanes_means_one_not_the_configured_cap(self):
        self.assertEqual(C._owner_capacity(POOL, self.cfg(cap=4)), 1)

    def test_unreadable_pool_root_falls_to_one(self):
        missing = self.tmp / "does-not-exist"
        self.assertEqual(C._owner_capacity(POOL, self.cfg(cap=4, root=missing)), 1)

    def test_cap_below_lane_count_wins(self):
        self.lanes(4)
        self.assertEqual(C._owner_capacity(POOL, self.cfg(cap=2)), 2)


class PickLoopSourceTests(unittest.TestCase):
    """Guards on the pick loop itself: presence-based skipping must not return."""

    def setUp(self):
        self.src = Path(C.__file__).read_text(encoding="utf-8")

    def test_the_skip_is_capacity_based_not_membership_based(self):
        self.assertIn("_held >= _cap", self.src,
                      "the pick loop must compare held-rows against a capacity")
        self.assertNotIn("if aid in busy_owners:", self.src,
                         "presence-based skipping is PD-1 and must not come back")

    def test_inflight_is_counted_per_owner_not_collected_into_a_set(self):
        self.assertIn("inflight_by_owner", self.src)
        self.assertNotIn("busy_owners = {", self.src,
                         "a set of owners cannot express capacity > 1")

    def test_liveness_is_still_checked_before_capacity(self):
        """P0-2b must keep winning: a DEAD agent is skipped whatever its capacity."""
        i_dead = self.src.index("if aid in dead_agents:")
        i_cap = self.src.index("_held >= _cap")
        self.assertLess(i_dead, i_cap,
                        "liveness must be evaluated before capacity, or a dead "
                        "pool with free lanes would be handed work")


class PickLoopBehaviourTests(unittest.TestCase):
    """The test my first attempt was missing.

    The isolated `_owner_capacity` tests and the source greps BOTH passed with
    the defect reinserted (`_cap = 1`), because neither drove the loop that
    actually decides. A guard that survives its own mutation is not a guard —
    so this drives `compute_advice` end to end and asserts the pool is picked
    for a SECOND row while already holding one.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pickloop-"))
        for sub in ("heartbeats", "tokens"):
            (self.tmp / sub).mkdir(parents=True, exist_ok=True)
        self.pool = self.tmp / "pool"
        for i in range(4):
            (self.pool / f"lane{i}").mkdir(parents=True, exist_ok=True)
        (self.tmp / "queue.jsonl").write_text("", encoding="utf-8")

        self._snap = C.lane_snapshot_cached
        self._co = C.co_residency_cached
        self._fold = C.fold_queue
        C.lane_snapshot_cached = lambda: {"cpu_busy": False, "gpu_busy": False,
                                          "none_busy": False, "cpu_state": "free",
                                          "gpu_state": "free", "none_state": "free",
                                          "load_class": "idle", "gpu_signal": None,
                                          "ts": "t"}
        C.co_residency_cached = lambda cfg: {"matrix_status": "n/a", "live_roles": [],
                                              "available": False, "error": None}

    def tearDown(self):
        C.lane_snapshot_cached = self._snap
        C.co_residency_cached = self._co
        C.fold_queue = self._fold
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cfg(self, cap=4):
        return {"roster": [dict(POOL, lanes=["none"])],
                "worker_pool": {"enabled": True, "max_concurrent_workers": cap,
                                "pool_root": str(self.pool)}}

    def _row(self, tid, **kw):
        r = {"task_id": tid, "status": "READY", "lane": "none", "gating": "none",
             "screened_by": "backlog_row_check.py@test",
             "expected_occupancy": {"est_h": 1.0, "basis": "test"},
             "task_text": f"do {tid}"}
        r.update(kw)
        return r

    def _advice(self, rows, cap=4):
        C.fold_queue = lambda _root: {r["task_id"]: r for r in rows}
        return C.compute_advice(self.tmp, self._cfg(cap), epoch=1)

    def test_pool_holding_one_row_is_STILL_PICKED_for_a_second(self):
        """The defect, stated as behaviour. This is what `_cap = 1` breaks."""
        rows = [self._row("held", status="ASSIGNED", owner="workerpool"),
                self._row("next")]
        adv = self._advice(rows)
        picks = [a for a in adv if a.get("kind") == "would-assign"
                 and a.get("agent") == "workerpool"]
        skips = [a for a in adv if a.get("kind") == "would-skip"
                 and a.get("agent") == "workerpool"]
        self.assertTrue(picks,
                        f"pool holding 1 of 4 must still be picked; got skips={skips}")
        self.assertEqual(picks[0]["task_id"], "next")

    def test_pool_at_its_cap_is_skipped(self):
        """The bound must still bind — capacity is a ceiling, not a suggestion."""
        rows = [self._row(f"h{i}", status="ASSIGNED", owner="workerpool") for i in range(4)]
        rows.append(self._row("next"))
        adv = self._advice(rows, cap=4)
        picks = [a for a in adv if a.get("kind") == "would-assign"
                 and a.get("agent") == "workerpool"]
        skips = [a for a in adv if a.get("kind") == "would-skip"
                 and a.get("agent") == "workerpool"]
        self.assertFalse(picks, "a pool at capacity must not be picked")
        self.assertTrue(any("capacity" in (s.get("reason") or "") for s in skips))


if __name__ == "__main__":
    unittest.main(verbosity=2)

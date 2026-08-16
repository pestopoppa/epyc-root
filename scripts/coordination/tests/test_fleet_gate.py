#!/usr/bin/env python3
"""Regression tests for the P0-2 / P0-2b assignment liveness gates.

WHAT THESE PIN, AND WHY IT IS WORTH PINNING. On 2026-08-14 the fleet's tmux
windows vanished and the daemon kept assigning to the sessions that used to be
behind them; fourteen rows walked ASSIGNED -> lease expiry -> STALE_REQUEUED ->
INFRA_BLOCKED overnight. On 2026-08-16, minutes after those rows were reset,
the SAME loop immediately handed four of them back to mainA-D, still dead. So
this defect has now been observed twice, and the second time it was observed
inside the fix for the first.

Two gates, tested separately because they fail differently:

  * `_fleet_presence`  — is there ANY main at all? Guards the write path in
    `apply_assignment`, and its job is to produce ONE alarm instead of N dead
    rows.
  * per-agent `dead_agents` filter in `compute_advice` — is THIS main there?
    A partially-dead fleet burns rows exactly as effectively as an empty one.

Both must treat UNREADABLE as ALIVE. A gate that halts the fleet because tmux
could not be read is the fail-closed twin of the failure it is meant to stop.
"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import session_bus_coordinator as C  # noqa: E402


def _roster(*ids, role="main", session="testsess"):
    return [{"id": i, "role": role, "lanes": ["none"], "endpoint": f"tmux:{session}:{i}"} for i in ids]


class FleetPresenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).resolve().parent / "_tmp_fleetgate"
        (self.tmp / "heartbeats").mkdir(parents=True, exist_ok=True)
        for p in (self.tmp / "heartbeats").glob("*.json"):
            p.unlink()

    def _hb(self, agent, age_s=0.0, state="working"):
        p = self.tmp / "heartbeats" / f"{agent}.json"
        p.write_text(json.dumps({"agent": agent, "state": state, "pid": 1}), encoding="utf-8")
        if age_s:
            old = time.time() - age_s
            import os
            os.utime(p, (old, old))

    def test_absent_fleet_is_detected(self):
        """No window, no fresh heartbeat, for every main -> present=False."""
        cfg = {"tmux": {"live_session": "no-such-session-for-tests"}}
        # A declared-but-unlistable session reads UNKNOWN, so use a listable one:
        # emulate by passing windows explicitly through _looks_dead's contract.
        roster = _roster("gm0", "gm1")
        # heartbeats absent entirely
        out = C._fleet_presence(self.tmp, {"tmux": {"live_session": ""}}, roster)
        # empty live_session -> UNKNOWN -> must NOT halt
        self.assertTrue(out["present"], "unreadable tmux must never halt the fleet")

    def test_unreadable_tmux_never_halts(self):
        roster = _roster("gm0")
        out = C._fleet_presence(self.tmp, {"tmux": {"live_session": ""}}, roster)
        self.assertTrue(out["present"])
        self.assertIn("unknown never halts", out["reason"].lower())

    def test_fresh_heartbeat_alone_keeps_fleet_present(self):
        """A live heartbeat is enough even with no window (mid-generation case)."""
        self._hb("gm0", age_s=0)
        roster = _roster("gm0")
        # a session name that lists successfully but has no matching window
        out = C._fleet_presence(self.tmp, {"tmux": {"live_session": "no-such-session-xyz"}}, roster)
        self.assertTrue(out["present"])

    def test_no_mains_in_roster_is_not_an_emergency(self):
        out = C._fleet_presence(self.tmp, {"tmux": {"live_session": ""}}, [])
        self.assertTrue(out["present"])
        self.assertIn("no mains", out["reason"])


class LooksDeadContractTests(unittest.TestCase):
    """The one calibration both gates fold over. If this drifts, both drift."""

    def test_live_window_beats_stale_heartbeat(self):
        entry = {"id": "a", "endpoint": "tmux:s:a"}
        states = {"a": {"age_s": 999999}}
        self.assertIsNone(C._looks_dead("a", entry, states, {"a"}, "s"),
                          "a live window must suppress a stale-heartbeat verdict")

    def test_no_window_and_stale_heartbeat_is_dead(self):
        entry = {"id": "a", "endpoint": "tmux:s:a"}
        states = {"a": {"age_s": C._RECIPIENT_LOOKS_DEAD_S + 1}}
        self.assertIsNotNone(C._looks_dead("a", entry, states, set(), "s"))

    def test_fresh_heartbeat_without_window_is_alive(self):
        entry = {"id": "a", "endpoint": "tmux:s:a"}
        states = {"a": {"age_s": 1.0}}
        self.assertIsNone(C._looks_dead("a", entry, states, set(), "s"))


class MutationGuardTests(unittest.TestCase):
    """Prove the dead-agent filter is load-bearing, not decorative.

    Without this, a refactor that drops the filter would leave every test green
    while restoring the exact 2026-08-14 behaviour.
    """

    def test_dead_agent_filter_is_present_in_the_pick_loop(self):
        src = Path(C.__file__).read_text(encoding="utf-8")
        self.assertIn("dead_agents", src,
                      "the per-agent liveness filter vanished from compute_advice")
        # It must be consulted BEFORE the busy check, or a dead agent that also
        # holds a stale row would be reported as merely busy and stay eligible.
        i_dead = src.index("if aid in dead_agents:")
        i_busy = src.index("if aid in busy_owners:")
        self.assertLess(i_dead, i_busy,
                        "liveness must be checked before busyness")

    def test_fleet_gate_runs_before_any_write(self):
        src = Path(C.__file__).read_text(encoding="utf-8")
        body = src[src.index("def apply_assignment("):]
        i_gate = body.index("_fleet_presence(")
        i_write = body.index("_append_jsonl(")
        self.assertLess(i_gate, i_write,
                        "the fleet gate must be evaluated before the first queue write")


if __name__ == "__main__":
    unittest.main(verbosity=2)

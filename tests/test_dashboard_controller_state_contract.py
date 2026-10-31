"""The dashboard's state allowlists must know every key the controller writes.

`server._DISCOVERY_TERMINAL_STATE_KEYS` is enforced as EXACT set equality, and the
v26 live gate rejects on any key outside `REQUIRED | OPTIONAL`. So a key added to
durable controller state without being listed here does not degrade the panel — it
rejects the whole surface, and the operator sees an unexplained blank.

This is a CROSS-REPO coupling: the controller lives in epyc-inference-research and the
allowlists in epyc-root, so nothing in either repo's own test suite catches the drift.
Three keys were added on 2026-08-28 (`champion_seeded_at`,
`champion_seed_anchor_commit` from the CH-2 always-exists champion invariant, and
`portfolio_critic_revisions` from the AK-VIS-2 revision budget) and would have bitten
on the first campaign to complete.

The test reads producer-recorded deployment-state fixtures rather than the live
loop. Their source paths and digests are pinned in the fixture manifest, so this
contract stays exercised while the producer is stopped.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from dashboard import server
from tests.autokernel_no_live_reads import NoLiveAutokernelReads

REPO = Path(__file__).resolve().parents[1]
DEPLOYMENTS = REPO / "tests/fixtures/autokernel_producers/deployment-states"

#: Keys that exist only while a campaign is mid-flight; a terminal state has popped
#: them. They must be accepted by the live gate but are not expected terminally.
TRANSIENT = {"pending", "inflight", "planning"}


def _recorded_states() -> list[tuple[str, dict]]:
    out = []
    if not DEPLOYMENTS.is_dir():
        return out
    for state_path in sorted(DEPLOYMENTS.glob("*/state.json")):
        try:
            value = json.loads(state_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("schema", "").startswith(
                "epyc.autokernel.discovery_controller."):
            out.append((state_path.parent.parent.name, value))
    return out


class ControllerStateContractTests(NoLiveAutokernelReads, unittest.TestCase):

    def test_every_recorded_state_key_is_known_to_the_dashboard(self):
        states = _recorded_states()
        self.assertTrue(states, "producer-recorded controller-state fixtures are required")
        known = (server._DISCOVERY_TERMINAL_STATE_KEYS
                 | server._DISCOVERY_V26_STATE_REQUIRED
                 | server._DISCOVERY_V26_STATE_OPTIONAL)
        for name, state in states:
            with self.subTest(deployment=name):
                unknown = sorted(set(state) - known)
                self.assertEqual(
                    unknown, [],
                    f"{name} writes state key(s) the dashboard allowlists do not "
                    f"know: {unknown}. The terminal gate is EXACT set equality, so "
                    "this rejects the whole surface rather than degrading it — add "
                    "them to _DISCOVERY_TERMINAL_STATE_KEYS and "
                    "_DISCOVERY_V26_STATE_OPTIONAL.")

    def test_a_recorded_terminal_state_would_be_accepted(self):
        """Simulate completion: drop the transient keys and require exact equality.

        Scoped to schema v5, because that is the only schema the terminal gate at
        `server.py` accepts — v7/v8 states go down the v26 live path and are governed
        by REQUIRED|OPTIONAL instead, which the first test already covers.
        """
        states = [(n, v) for n, v in _recorded_states()
                  if v.get("schema") == "epyc.autokernel.discovery_controller.v5"]
        self.assertTrue(states, "fixture set must retain the producer's v5 state")
        for name, state in states:
            with self.subTest(deployment=name):
                terminal = {k: v for k, v in state.items() if k not in TRANSIENT}
                terminal.setdefault("terminal_reason", "simulated")
                terminal.setdefault("attempted_candidate_identities", {})
                terminal.setdefault("candidate_semantic_registry_schema", "x")
                # The gate is required-subset plus known-optional: an unlisted key
                # rejects the surface, while a required key the campaign never wrote
                # is a separate (also fatal) failure. Assert the shape the gate uses,
                # not the exact equality it used to use.
                known = (server._DISCOVERY_TERMINAL_STATE_KEYS
                         | server._DISCOVERY_TERMINAL_STATE_OPTIONAL)
                unlisted = sorted(set(terminal) - known)
                self.assertEqual(
                    unlisted, [],
                    f"{name}: on completion these keys would reject the terminal "
                    f"surface outright: {unlisted}. Add them to "
                    "_DISCOVERY_TERMINAL_STATE_OPTIONAL (not the required set — that "
                    "would reject every campaign that never wrote them).")


if __name__ == "__main__":
    unittest.main()

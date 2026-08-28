"""The aggregate champion must be visible, and must not overclaim.

The champion card was blank because nothing read the controller's champion record.
The surface's `champion` section still reports "the current one-candidate driver banks
a result; it does not mint a champion" -- true before CH-2, false afterwards: the
controller now seeds a champion at campaign start and records the anchor commit it was
seeded from.

The honesty rule is the reason this has tests at all. A SEEDED champion *equals*
production; it has earned nothing. A card that showed a champion existing without
saying so would imply a win that no measurement supports, which is exactly the failure
the measurement constitution exists to prevent.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from dashboard import server

ANCHOR = "0db32c06e3e550065b78311a6031ef3dd2c4f27c"


class ChampionCardTests(unittest.TestCase):

    def setUp(self) -> None:
        self._old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self._old_sup = server.AUTOKERNEL_SUPERVISORS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
        sup = Path(self.temp.name) / "supervisors"
        sup.mkdir(mode=0o700, parents=True)
        self.bundle = root / "campaign-a"
        self.state = self.bundle / "state"
        (self.bundle / "config").mkdir(parents=True)
        self.state.mkdir()
        (self.bundle / "operations/live").mkdir(parents=True)
        (self.bundle / "config/deployment.json").write_text(json.dumps({
            "config_sha256": "a" * 64,
            "controller": {"state_root": str(self.state),
                           "operations_root": str(self.bundle / "operations")},
        }))
        (self.state / "controller.run.lock").touch()
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root
        server.AUTOKERNEL_SUPERVISORS_ROOT = sup

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        server.AUTOKERNEL_SUPERVISORS_ROOT = self._old_sup
        self.temp.cleanup()

    def _champion(self, state_extra: dict, iterations: list | None = None) -> dict:
        base = {"updated_at": "2026-08-28T12:00:00Z", "next": 2, "complete": False,
                "iterations": iterations or []}
        base.update(state_extra)
        (self.state / "state.json").write_text(json.dumps(base))
        activity = server.discovery_live_payload().get("activity") or {}
        return activity.get("champion") or {}

    def test_a_seeded_champion_is_reported_as_equal_to_production(self):
        """The honesty rule: a seed has earned nothing, so say parity explicitly."""
        ch = self._champion({"champion_seeded_at": "2026-08-28T12:02:05Z",
                             "champion_seed_anchor_commit": ANCHOR})
        self.assertTrue(ch.get("exists"))
        self.assertEqual(ch.get("members"), 0)
        self.assertEqual(ch.get("headline"), "equals production (seeded)")
        self.assertEqual(ch.get("anchor_commit_short"), ANCHOR[:12])

    def test_no_champion_record_reports_none_rather_than_inventing_one(self):
        ch = self._champion({})
        self.assertFalse(ch.get("exists"))
        self.assertIsNone(ch.get("headline"))
        self.assertIsNone(ch.get("anchor_commit"))

    def test_banked_candidates_are_counted_but_not_called_composed(self):
        """A banked candidate is not yet a champion member; the wording must not
        promote it to one before the combined candidate re-earns its tiers."""
        ch = self._champion(
            {"champion_seeded_at": "2026-08-28T12:02:05Z",
             "champion_seed_anchor_commit": ANCHOR},
            iterations=[{"turn": 1, "status": "candidate"},
                        {"turn": 2, "status": "authoring_refused"},
                        {"turn": 3, "status": "candidate"}])
        self.assertEqual(ch.get("members"), 2)
        self.assertIn("not yet composed", ch.get("headline") or "")

    def test_refusals_and_inconclusives_are_never_counted_as_members(self):
        ch = self._champion(
            {"champion_seeded_at": "2026-08-28T12:02:05Z",
             "champion_seed_anchor_commit": ANCHOR},
            iterations=[{"turn": 1, "status": "authoring_refused"},
                        {"turn": 2, "status": "inconclusive"},
                        {"turn": 3, "status": "critic_revise"}])
        self.assertEqual(ch.get("members"), 0)
        self.assertEqual(ch.get("headline"), "equals production (seeded)")


if __name__ == "__main__":
    unittest.main()

"""The champion card must report the champion KERNEL, not a seeded record.

The first version of this card said "equals production (seeded)" while the champion
it names already carried DFlash2 and MoE-Spec. It reported the campaign's champion
RECORD (seeded from the frozen production anchor) and counted `members` from the
campaign's own banked candidates -- zero on a fresh campaign -- while the champion
KERNEL the campaign screens against is the sealed INSTRUMENT pin. Two different
objects, conflated, and the page asserted something false about work done the night
before.

The aggregate candidate and the champion are ALSO the same object, so there is one
card. The page previously drew two that disagreed with each other. The markup guard
that counted those cards went with `kernel.html` on 2026-08-30; what survives here
is the card's DATA contract, which is where the conflation actually lived and which
any page drawing the champion has to read correctly.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from dashboard import server

PROD = "0db32c06e3e550065b78311a6031ef3dd2c4f27c"
CHAMP = "270b48ed64d617db9128054f3bd0620bbb9371f5"


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
        self.cfgpath = self.bundle / "config/deployment.json"
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root
        server.AUTOKERNEL_SUPERVISORS_ROOT = sup
        (self.state / "controller.run.lock").touch()

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        server.AUTOKERNEL_SUPERVISORS_ROOT = self._old_sup
        self.temp.cleanup()

    def _champion(self, champion_commit: str | None) -> dict:
        cfg = {"config_sha256": "a" * 64,
               "controller": {"state_root": str(self.state),
                              "operations_root": str(self.bundle / "operations")},
               "production": {"branch": "production-consolidated-v9", "head": PROD}}
        if champion_commit:
            cfg["instrument"] = {"branch": "ak/champion/llama-cpp-0db32c06e3e5",
                                 "commit": champion_commit}
        self.cfgpath.write_text(json.dumps(cfg))
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-28T12:00:00Z", "next": 2, "complete": False,
            "iterations": [], "champion_seeded_at": "2026-08-28T12:02:05Z"}))
        activity = server.discovery_live_payload().get("activity") or {}
        return activity.get("champion") or {}

    def test_a_champion_ahead_of_production_is_never_called_equal_to_it(self):
        """The exact regression: DFlash2 and MoE-Spec were in it and the card said
        'equals production (seeded)'."""
        ch = self._champion(CHAMP)
        self.assertTrue(ch.get("exists"))
        self.assertTrue(ch.get("ahead_of_production"),
                        "a champion whose commit differs from production is AHEAD of it")
        self.assertEqual(ch.get("commit_short"), CHAMP[:12])
        self.assertNotIn("equals production", (ch.get("headline") or ""))
        self.assertIn("admitted work", ch.get("headline") or "")

    def test_a_champion_identical_to_production_says_so(self):
        ch = self._champion(PROD)
        self.assertFalse(ch.get("ahead_of_production"))
        self.assertIn("identical to frozen production", ch.get("headline") or "")

    def test_no_instrument_pin_reports_none_rather_than_inventing_one(self):
        ch = self._champion(None)
        self.assertFalse(ch.get("exists"))
        self.assertIsNone(ch.get("headline"))

    def test_the_champion_is_not_derived_from_this_campaigns_banked_rows(self):
        """The original bug: `members` came from iterations, so a fresh campaign made
        a fully-loaded champion look empty."""
        ch = self._champion(CHAMP)
        self.assertNotIn("members", ch,
                         "champion contents come from the instrument pin, never from "
                         "this campaign's iteration rows")


if __name__ == "__main__":
    unittest.main()

"""Manual research must be able to update the champion AND be seen.

The loop the operator asked for is: do manual inference research -> admit it into the
champion -> see the champion's standing. Admission already worked (DFlash2 and MoE-Spec
arrived that way). ATTESTATION did not: the champion surface read only a
campaign-produced cumulative receipt, so the strongest measured evidence in the program
was invisible to the surface that reports champion standing.

The trust boundary is the whole design. A forged
`epyc.autokernel.cumulative_performance.v2` would have been the easy fix and is exactly
wrong: that receipt's authority comes from a chain only a campaign builds, so
manufacturing one launders operator evidence into campaign authority. The bundle is a
separate carrier that states what it is, and these tests pin that it can never claim
more.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from dashboard import server

CHAMP = "270b48ed64d617db9128054f3bd0620bbb9371f5"


def _bundle(**over) -> dict:
    base = {
        "schema": "epyc.autokernel.operator_gate_bundle.v1",
        "authority": "operator_gated_manual_research",
        "promotion_claim": False,
        "not_campaign_sealed": True,
        "champion": {"branch": "ak/champion/x", "commit": CHAMP},
        "production_anchor": {"commit": "0" * 40},
        "gates": [{"gate": "dflash2_vs_production_serving_path", "status": "PASS",
                   "claim": "exceeds production's ceiling"}],
        "gates_missing": [],
        "headline": {"effect_fraction": 0.489, "positive": True,
                     "summary": "+48.9% at 2 in-flight"},
        "caveat": "carries NO promotion authority",
        "bundle_sha256": "a" * 64,
    }
    base.update(over)
    return base


class OperatorGateBundleTests(unittest.TestCase):

    def setUp(self) -> None:
        self._old = server.OPERATOR_GATE_BUNDLE_JSON
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "operator_gate_bundle.json"
        server.OPERATOR_GATE_BUNDLE_JSON = self.path

    def tearDown(self) -> None:
        server.OPERATOR_GATE_BUNDLE_JSON = self._old
        self.temp.cleanup()

    def _read(self, value) -> dict:
        self.path.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return server._read_operator_gate_bundle()

    def test_manual_gate_evidence_reaches_the_surface(self):
        """The regression this exists for: measured, admitted, and previously unseen."""
        got = self._read(_bundle())
        self.assertTrue(got["available"])
        self.assertEqual(got["champion_commit"], CHAMP)
        self.assertAlmostEqual(got["headline"]["effect_fraction"], 0.489)
        self.assertEqual([g["status"] for g in got["gates"]], ["PASS"])

    def test_a_bundle_claiming_promotion_authority_is_refused(self):
        """It may say what it measured; it may never say it authorises a promotion."""
        got = self._read(_bundle(promotion_claim=True))
        self.assertFalse(got["available"])
        self.assertIn("authority", got["error"])

    def test_a_bundle_claiming_campaign_authority_is_refused(self):
        got = self._read(_bundle(authority="nonpromotable_candidate_only_discovery"))
        self.assertFalse(got["available"])

    def test_a_campaign_receipt_schema_is_refused(self):
        """The forgery this design exists to prevent: operator evidence wearing the
        campaign receipt's schema."""
        got = self._read(_bundle(schema="epyc.autokernel.cumulative_performance.v2"))
        self.assertFalse(got["available"])
        self.assertIn("schema", got["error"])

    def test_missing_gates_are_reported_not_hidden(self):
        """A bundle that silently omitted an absent gate would be worse than none."""
        got = self._read(_bundle(gates_missing=["greedy_parity"]))
        self.assertEqual(got["gates_missing"], ["greedy_parity"])

    def test_absent_or_malformed_bundles_degrade_quietly(self):
        self.path.unlink(missing_ok=True)
        self.assertFalse(server._read_operator_gate_bundle()["available"])
        self.assertFalse(self._read("{not json")["available"])

    def test_the_real_emitted_bundle_is_accepted(self):
        """End-to-end against the bundle the emitter actually produced."""
        real = Path("/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json")
        if not real.is_file():
            self.skipTest("no emitted bundle on this host")
        server.OPERATOR_GATE_BUNDLE_JSON = real
        got = server._read_operator_gate_bundle()
        self.assertTrue(got["available"], got.get("error"))
        self.assertTrue((got.get("headline") or {}).get("summary"))


if __name__ == "__main__":
    unittest.main()

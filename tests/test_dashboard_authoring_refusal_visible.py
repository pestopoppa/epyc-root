"""AK-VIS-1: an `authoring_refused` turn must be visible on the command band.

`refusal.detected` is `refusal_type is not None`, and `refusal_type` comes from a
status->label map inside `discovery_live_payload`. `authoring_refused` was absent from
that map, so the most common failure in the whole program rendered NOTHING: the
operator saw an active hypothesis with no indication its diff had been refused.

The map did contain `planner_contract_refused -> "authoring_refused"`, i.e. it produced
the label while never matching the status of that name -- which is why this survived
review. Measured across campaigns v28-v34: `authoring_refused` 22, `planner_refused` 1.

These tests drive the REAL payload path. An earlier version of this file asserted
against a local copy of the map and grepped the module source for
`"authoring_refused":` -- both vacuous: the copy was not the code under test, and the
grep matched unrelated lines elsewhere in the module, so deleting the map entry left
the suite green.

Scope note on secrets: `refusal.detail` intentionally carries OUR guard's message for
an authoring refusal, which is what makes it actionable. That is distinct from a
`planner_refused` reason, which can contain raw actor stdout and must never cross --
pinned separately by test_dashboard_autokernel_live.py::
test_v2_planner_refusal_is_typed_secret_free_and_advances.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from dashboard import server


class AuthoringRefusalVisibilityTests(unittest.TestCase):

    def setUp(self) -> None:
        self._old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self._old_supervisors = server.AUTOKERNEL_SUPERVISORS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
        supervisors = Path(self.temp.name) / "supervisors"
        supervisors.mkdir(mode=0o700, parents=True)
        self.bundle = root / "campaign-a"
        self.state = self.bundle / "state"
        self.operations = self.bundle / "operations"
        (self.bundle / "config").mkdir(parents=True)
        self.state.mkdir()
        (self.operations / "live").mkdir(parents=True)
        (self.bundle / "config/deployment.json").write_text(json.dumps({
            "config_sha256": "a" * 64,
            "controller": {"state_root": str(self.state),
                           "operations_root": str(self.operations)},
        }))
        (self.state / "controller.run.lock").touch()
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root
        server.AUTOKERNEL_SUPERVISORS_ROOT = supervisors

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        server.AUTOKERNEL_SUPERVISORS_ROOT = self._old_supervisors
        self.temp.cleanup()

    def _refusal_view(self, status: str) -> dict:
        """Write a campaign whose latest turn ended in `status`, then read the band."""
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-28T10:00:00Z", "next": 2, "complete": False,
            "iterations": [{
                "turn": 1,
                "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                "portfolio_hypothesis_id": "akh-v2-q5-type-specific-dequant",
                "status": status,
                "scientific_budget_spent": False,
                # v33's real refusal text.
                "reason": ("committed diff in 'ggml/src/ggml-cuda/vecdotq.cuh' "
                           "derives undeclared symbols ['<file-scope>']"),
            }],
        }))
        activity = server.discovery_live_payload().get("activity") or {}
        return activity.get("refusal") or {}

    def test_authoring_refused_is_detected(self):
        """The regression: this is the status v33 and v34 actually produced."""
        view = self._refusal_view("authoring_refused")
        self.assertTrue(view.get("detected"),
                        "an authoring refusal must show on the command band")
        self.assertEqual(view.get("type"), "authoring_refused")

    def test_other_controller_refusal_statuses_are_detected(self):
        for status in ("authorization_refused", "candidate_semantic_repeat_refused",
                       "portfolio_dnr_refused"):
            with self.subTest(status=status):
                self.assertTrue(self._refusal_view(status).get("detected"), status)

    def test_non_refusal_statuses_stay_undetected(self):
        """`critic_revise` is iteration and `candidate` is success; flagging either
        would make the band cry wolf."""
        for status in ("candidate", "inconclusive", "critic_revise"):
            with self.subTest(status=status):
                self.assertFalse(self._refusal_view(status).get("detected"), status)

    def test_the_refusal_detail_reaches_the_operator(self):
        """The WHY, not just the WHAT.

        `refusal.detail` already carried the guard's message; it simply never rendered,
        because `detected` was false and the whole block was skipped. Unblocking the
        map is therefore what makes the actionable half visible: "derives undeclared
        symbols in vecdotq.cuh" rather than a bare "refused".

        Scope: this is OUR guard's message, not raw actor output. The separate secret
        boundary for `planner_refused` -- whose reason can contain raw actor stdout --
        is pinned by test_dashboard_autokernel_live.py::
        test_v2_planner_refusal_is_typed_secret_free_and_advances, which must keep
        passing alongside this.
        """
        view = self._refusal_view("authoring_refused")
        self.assertIn("vecdotq", str(view.get("detail") or ""),
                      "the refusal detail is the operator's actionable signal")


if __name__ == "__main__":
    unittest.main()

"""Tests for the Trinity tri-role rule-based classifier (TR-3.1).

The classifier must be deterministic, fast, and produce a non-degenerate role
distribution on realistic prompts. These tests pin the rule precedence so
TR-3.4 telemetry has a stable baseline to compare against.
"""

from __future__ import annotations

import pytest

from src.classifiers.role_classifier import (
    RoleClassification,
    classify_role,
)
from src.classifiers.role_taxonomy import TrinityRole

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"


class TestVerifierRule:
    def test_review_with_prior_content(self):
        out = classify_role("Review my answer above.")
        assert out.role == TrinityRole.VERIFIER.value
        assert out.reason == "verifier_review_trigger"

    def test_verify_with_code_block(self):
        prompt = "Verify that this code is correct: ```\ndef add(a,b): return a+b\n```"
        assert classify_role(prompt).role == TrinityRole.VERIFIER.value

    def test_is_this_correct_with_following_content(self):
        out = classify_role("Is this correct? Following solution: x + y = z.")
        assert out.role == TrinityRole.VERIFIER.value

    def test_sanity_check_draft(self):
        out = classify_role("Sanity check the math in this draft.")
        assert out.role == TrinityRole.VERIFIER.value

    def test_double_check_my_attempt(self):
        out = classify_role("Double-check my attempt at the proof.")
        assert out.role == TrinityRole.VERIFIER.value

    def test_verify_without_prior_content_falls_to_worker(self):
        # "Verify" without prior-content cue is a derivation request, not a
        # quality gate.
        out = classify_role("Verify the value of the gravitational constant.")
        assert out.role == TrinityRole.WORKER.value

    def test_check_substring_no_false_positive(self):
        # "checkmate" / "checkout" should not trigger the check pattern —
        # word-boundary anchoring + the "check that/whether/if/the/this/my/our"
        # context.
        out = classify_role("Tell me what checkmate means in chess.")
        assert out.role == TrinityRole.WORKER.value


class TestThinkerRule:
    def test_architect_routing(self):
        out = classify_role(
            "Find the largest prime factor.",
            routing_decision=["architect_general"],
        )
        assert out.role == TrinityRole.THINKER.value
        assert out.reason == "thinker_architect_role"

    def test_architect_routing_canonicalizes_retired_alias(self):
        out = classify_role(
            "Find the largest prime factor.",
            routing_decision=[_RETIRED_ARCHITECT_ROLE],
        )
        assert out.role == TrinityRole.THINKER.value
        assert out.reason == "thinker_architect_role"

    def test_force_role_retired_architect(self):
        out = classify_role("Quick task.", force_role=_RETIRED_ARCHITECT_ROLE)
        assert out.role == TrinityRole.THINKER.value

    def test_thinking_budget_above_zero(self):
        out = classify_role("Quick task.", thinking_budget=2048)
        assert out.role == TrinityRole.THINKER.value
        assert out.reason == "thinker_thinking_budget"

    def test_plan_keyword(self):
        out = classify_role("Plan how to migrate the DB.")
        assert out.role == TrinityRole.THINKER.value
        assert out.reason == "thinker_plan_keyword"

    def test_decompose_keyword(self):
        out = classify_role("Decompose this problem into sub-tasks.")
        assert out.role == TrinityRole.THINKER.value

    def test_design_keyword(self):
        out = classify_role("Design a robust file synchronization protocol.")
        assert out.role == TrinityRole.THINKER.value

    def test_strategy_keyword(self):
        out = classify_role("What is a good caching strategy for our API?")
        assert out.role == TrinityRole.THINKER.value

    def test_high_level_phrase(self):
        out = classify_role("Give me a high-level overview of microservices.")
        assert out.role == TrinityRole.THINKER.value

    def test_pros_and_cons(self):
        out = classify_role("Pros and cons of Postgres vs MySQL?")
        assert out.role == TrinityRole.THINKER.value

    def test_how_should_i_approach(self):
        out = classify_role("How should I approach refactoring this module?")
        assert out.role == TrinityRole.THINKER.value


class TestWorkerDefault:
    def test_simple_code_task(self):
        out = classify_role("Write a function to reverse a string.")
        assert out.role == TrinityRole.WORKER.value
        assert out.reason == "worker_default"

    def test_factual_lookup(self):
        out = classify_role("What is the capital of France?")
        assert out.role == TrinityRole.WORKER.value

    def test_arithmetic(self):
        out = classify_role("Compute 17 * 23.")
        assert out.role == TrinityRole.WORKER.value

    def test_empty_prompt_is_worker(self):
        out = classify_role("")
        assert out.role == TrinityRole.WORKER.value


class TestRulePrecedence:
    """Verifier > Thinker > Worker — first-match wins."""

    def test_verifier_beats_architect_routing(self):
        # Even on architect routing, an explicit review trigger over prior
        # content should classify as VERIFIER.
        out = classify_role(
            "Review my answer above for correctness.",
            routing_decision=["architect_general"],
        )
        assert out.role == TrinityRole.VERIFIER.value

    def test_verifier_beats_plan_keyword(self):
        out = classify_role(
            "Review my plan above and verify it makes sense.",
        )
        assert out.role == TrinityRole.VERIFIER.value

    def test_architect_beats_thinking_budget(self):
        # Both rules match — architect rule fires first.
        out = classify_role(
            "Quick task.",
            routing_decision=["architect_general"],
            thinking_budget=2048,
        )
        assert out.reason == "thinker_architect_role"


class TestReturnShape:
    def test_returns_classification_dataclass(self):
        out = classify_role("Hello.")
        assert isinstance(out, RoleClassification)
        assert out.role in {r.value for r in TrinityRole}
        assert isinstance(out.reason, str) and out.reason

    def test_dataclass_is_frozen(self):
        out = classify_role("Hello.")
        with pytest.raises(Exception):
            out.role = "thinker"  # type: ignore[misc]


class TestNonDegenerateDistribution:
    """TR-3.4 sanity: a small spread of typical prompts should NOT all map to
    Worker. If this test breaks, the heuristic has regressed to the degenerate
    99%-Worker distribution that TR-3.4 explicitly screens for.
    """

    def test_role_spread_on_realistic_prompts(self):
        prompts = [
            ("Write hello world.", "worker"),
            ("Plan a system migration.", "thinker"),
            ("Review my answer above.", "verifier"),
            ("What is 2+2?", "worker"),
            ("Decompose this problem.", "thinker"),
            ("Verify my code is correct.", "worker"),  # no prior content cue
            ("Verify the following code: ```x=1```", "verifier"),
            ("Approach to refactor my code.", "thinker"),
        ]
        roles = [classify_role(p).role for p, _ in prompts]
        # At least 2 distinct roles should appear — distribution is not
        # degenerate against this prompt mix.
        assert len(set(roles)) >= 2

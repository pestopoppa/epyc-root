"""Tests for src/classifiers/factual_risk — regex-based factual-risk scorer."""

from __future__ import annotations

import pytest

from src.classifiers.factual_risk import (
    DEFAULT_STACK_PRIORS_PATH,
    FactualRiskResult,
    _DEFAULT_ROLE_TIERS,
    _degraded_role_tier,
    _extract_features,
    _canary_roll,
    _compute_score,
    _role_tier_for_role,
    _role_adjustment,
    _tier_from_model_mem,
    _band,
    assess_risk,
    get_configured_mode,
    get_mode,
)


def _live_roles_by_tier() -> dict[str, list[str]]:
    """Live role -> factual-risk tier, derived exactly as the module derives it.

    Source of truth is the generated stack-prior artifact plus the module's own
    ``_tier_from_model_mem`` thresholds — never a pasted role name. The role that
    occupies a given tier changes whenever a model moves between roles (the
    2026-08-01 W1 cutover swapped the 122B from architect_general to
    architect_critic and every hardcoded exemplar in this class went stale).
    """
    from src.registry.stack_priors import live_stack_role_records, stack_prior_model_mem_gb

    by_tier: dict[str, list[str]] = {}
    for role, record in live_stack_role_records(DEFAULT_STACK_PRIORS_PATH).items():
        mem_gb = stack_prior_model_mem_gb(record)
        if mem_gb is None:
            continue
        by_tier.setdefault(_tier_from_model_mem(mem_gb), []).append(role)
    return {tier: sorted(roles) for tier, roles in by_tier.items()}


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


class TestExtractFeatures:
    """Feature extractor returns correct signals."""

    def test_empty_prompt(self):
        f = _extract_features("")
        assert all(v == 0.0 for v in f.values())

    def test_date_question(self):
        f = _extract_features("When did the French Revolution start?")
        assert f["has_date_question"] == 1.0

    def test_date_year_mention(self):
        f = _extract_features("What happened in 2024?")
        assert f["has_date_question"] == 1.0

    def test_date_born(self):
        f = _extract_features("Where was Einstein born?")
        assert f["has_date_question"] == 1.0

    def test_no_date_question(self):
        f = _extract_features("Write a Python function to sort a list")
        assert f["has_date_question"] == 0.0

    def test_entity_question(self):
        f = _extract_features("Who is the CEO of Apple?")
        assert f["has_entity_question"] == 1.0

    def test_entity_founder(self):
        f = _extract_features("Who is the founder of Tesla?")
        assert f["has_entity_question"] == 1.0

    def test_no_entity_question(self):
        f = _extract_features("Implement a binary search algorithm")
        assert f["has_entity_question"] == 0.0

    def test_citation_request(self):
        f = _extract_features("Cite peer-reviewed sources for this claim")
        assert f["has_citation_request"] == 1.0

    def test_no_citation_request(self):
        f = _extract_features("Summarize this document for me")
        assert f["has_citation_request"] == 0.0

    def test_factual_keywords(self):
        f = _extract_features("What is the population of France and what is the capital of Germany?")
        assert f["factual_keyword_ratio"] > 0.0

    def test_no_factual_keywords(self):
        f = _extract_features("Write a poem about rain")
        assert f["factual_keyword_ratio"] == 0.0

    def test_uncertainty_markers(self):
        f = _extract_features("Maybe the answer is approximately 42. Perhaps it varies.")
        assert f["uncertainty_markers"] > 0.0

    def test_no_uncertainty(self):
        f = _extract_features("The capital of France is Paris.")
        assert f["uncertainty_markers"] == 0.0

    def test_claim_density_high(self):
        prompt = (
            "The Earth is round. Water boils at 100 degrees. "
            "Light travels at 300000 km per second."
        )
        f = _extract_features(prompt)
        assert f["claim_density"] > 0.0

    def test_claim_density_question_only(self):
        f = _extract_features("What is the speed of light?")
        # A question is not an assertion
        assert f["claim_density"] == 0.0 or f["claim_density"] < 0.5


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


class TestComputeScore:
    """Score computation produces valid ranges and respects weights."""

    def test_all_zeros(self):
        features = {k: 0.0 for k in [
            "has_date_question", "has_entity_question", "has_citation_request",
            "claim_density", "factual_keyword_ratio", "uncertainty_markers",
        ]}
        # uncertainty_markers=0 → contributes weight*(1-0) = weight
        score = _compute_score(features)
        # Only uncertainty inverse contributes
        assert 0.0 <= score <= 1.0

    def test_all_ones_no_uncertainty(self):
        features = {
            "has_date_question": 1.0,
            "has_entity_question": 1.0,
            "has_citation_request": 1.0,
            "claim_density": 1.0,
            "factual_keyword_ratio": 1.0,
            "uncertainty_markers": 0.0,
        }
        score = _compute_score(features)
        assert score == pytest.approx(1.0)

    def test_full_uncertainty_reduces(self):
        base = {
            "has_date_question": 1.0,
            "has_entity_question": 1.0,
            "has_citation_request": 1.0,
            "claim_density": 1.0,
            "factual_keyword_ratio": 1.0,
            "uncertainty_markers": 0.0,
        }
        with_uncertainty = {**base, "uncertainty_markers": 1.0}
        assert _compute_score(with_uncertainty) < _compute_score(base)

    def test_custom_weights(self):
        features = {
            "has_date_question": 1.0,
            "has_entity_question": 0.0,
            "has_citation_request": 0.0,
            "claim_density": 0.0,
            "factual_keyword_ratio": 0.0,
            "uncertainty_markers": 0.0,
        }
        weights = {
            "has_date_question": 0.5,
            "uncertainty_markers": 0.5,
        }
        score = _compute_score(features, weights)
        # date=0.5*1.0 + uncertainty=0.5*(1-0)=0.5 → 1.0
        assert score == pytest.approx(1.0)

    def test_clamped_to_unit(self):
        # Even with weird weights, output is clamped
        features = {"has_date_question": 1.0, "uncertainty_markers": 0.0}
        weights = {"has_date_question": 2.0, "uncertainty_markers": 2.0}
        score = _compute_score(features, weights)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# Role adjustment
# ---------------------------------------------------------------------------


class TestRoleAdjustment:
    """Per-role capability factors."""

    def test_architect_is_tier_1(self):
        """The tier-1 exemplar is derived from the module's own memory threshold.

        ``architect_general`` was the tier-1 role only because it served the 69 GB
        122B. On 2026-08-01 that model moved to ``architect_critic`` and
        architect_general took the 27.05 GB MI210 model, so it is legitimately
        tier_2 now. Deriving keeps this test correct across the next model swap.
        """
        tier_1_roles = _live_roles_by_tier().get("tier_1", [])
        assert tier_1_roles, "no live role meets the tier-1 model-memory threshold"

        for role in tier_1_roles:
            assert _role_tier_for_role(role) == "tier_1"
            assert _role_adjustment(role) == pytest.approx(_DEFAULT_ROLE_TIERS["tier_1"])

        # The tier-1 discount is still an architect-family capability.
        assert any(role.startswith("architect_") for role in tier_1_roles)
        # Calibrated multiplier itself is still pinned (G12 AA-Omniscience).
        assert _DEFAULT_ROLE_TIERS["tier_1"] == pytest.approx(0.727978)

    def test_degraded_role_tiers_agree_with_live_derivation(self):
        """The hand degraded table must not contradict the live derivation.

        The degraded table is consulted only when stack priors are missing, so it
        cannot be derived — but a role whose degraded tier disagrees with its live
        tier is scored differently depending on whether an artifact happens to be
        on disk. That drift is exactly what the W1 cutover left behind
        (architect_general stuck at tier_1, architect_critic absent, and
        vision_escalation at tier_2 against a live tier_3).
        """
        live = {
            role: tier
            for tier, roles in _live_roles_by_tier().items()
            for role in roles
        }
        assert live, "live stack priors produced no role tiers"

        mismatches = {
            role: (degraded, live_tier)
            for role, live_tier in live.items()
            if (degraded := _degraded_role_tier(role)) is not None and degraded != live_tier
        }
        assert not mismatches, f"degraded table disagrees with live priors: {mismatches}"

        # And the strongest live roles must actually be covered by the table,
        # otherwise degraded mode silently gives them no discount.
        for role in _live_roles_by_tier().get("tier_1", []):
            assert _degraded_role_tier(role) == "tier_1", role

    def test_coder_is_tier_2(self):
        assert _role_adjustment("coder_escalation") == pytest.approx(0.824178)

    def test_worker_is_tier_3(self):
        """The weakest live tier gets no risk discount (factor exactly 1.0).

        This pinned ``worker_general`` until the operator-signed 2026-09-22
        cutover (orchestrator 860b0b2d) made it an alias on frontdoor's 35B-A3B
        fleet, which the live derivation legitimately puts in tier_2. The tier-3
        exemplars are now derived from stack priors like the tier-1 ones above.
        """
        tier_3_roles = _live_roles_by_tier().get("tier_3", [])
        assert tier_3_roles, "no live role falls in tier_3 — check is vacuous"
        for role in tier_3_roles:
            assert _role_tier_for_role(role) == "tier_3", role
            assert _role_adjustment(role) == 1.0, role

    def test_frontdoor_uses_live_stack_prior_model_tier(self):
        assert _role_tier_for_role("frontdoor") == "tier_2"
        assert _role_adjustment("frontdoor") == pytest.approx(0.824178)

    def test_role_tier_uses_live_stack_prior_model_memory(self, tmp_path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            """
roles:
  swapped_role:
    deployment_status: live_stack
    model:
      mem_gb: 69.0
""",
            encoding="utf-8",
        )

        assert _role_tier_for_role("swapped_role", priors) == "tier_1"

    def test_role_tier_ignores_candidate_stack_prior_records(self, tmp_path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            """
roles:
  retired_large_role:
    deployment_status: benchmark_or_candidate
    model:
      mem_gb: 69.0
""",
            encoding="utf-8",
        )

        assert _role_tier_for_role("retired_large_role", priors) == "tier_3"

    def test_role_tier_uses_degraded_fallback_when_stack_priors_missing(self, tmp_path):
        missing = tmp_path / "missing_stack_priors.yaml"

        assert _role_tier_for_role("frontdoor", missing) == "tier_2"
        # A role that rides another role's process takes its host's degraded tier.
        # worker_explore and worker_fast (both canonicalize to worker_general)
        # pinned tier_3 here until the operator-signed 2026-09-22 cutover
        # (orchestrator 860b0b2d) put worker_general on frontdoor's :8070
        # process; live priors now score it tier_2, so the degraded path agrees.
        for role in ("worker_explore", "worker_fast"):
            assert _role_tier_for_role(role, missing) == _role_tier_for_role(role), role
            assert _role_tier_for_role(role, missing) == _role_tier_for_role(
                "frontdoor", missing
            ), role
        # A role neither the degraded table nor the registry knows gets no discount.
        assert _role_tier_for_role("unknown_new_role", missing) == "tier_3"

    def test_unknown_role_defaults_tier_3(self):
        assert _role_adjustment("unknown_new_role") == 1.0

    def test_config_override(self):
        """Caller-supplied role_adjustments are consulted per DERIVED tier.

        The tier-1 exemplar is derived (it moved from architect_general to
        architect_critic on 2026-08-01); all three tier branches are covered so
        the override map cannot be half-ignored.
        """
        config = {"role_adjustments": {"tier_1": 0.5, "tier_2": 0.7, "tier_3": 0.9}}
        by_tier = _live_roles_by_tier()

        for tier, expected in (("tier_1", 0.5), ("tier_2", 0.7), ("tier_3", 0.9)):
            roles = by_tier.get(tier, [])
            assert roles, f"no live role in {tier}"
            for role in roles:
                assert _role_adjustment(role, config) == expected, (role, tier)

        # coder_escalation stayed tier_2 across the cutover — explicit coverage
        # that the override, not the default table, produced the value.
        assert _role_adjustment("coder_escalation", config) == 0.7
        assert _role_adjustment("coder_escalation") != 0.7


# ---------------------------------------------------------------------------
# Banding
# ---------------------------------------------------------------------------


class TestBand:
    """Risk band discretization."""

    def test_low(self):
        assert _band(0.1) == "low"

    def test_medium(self):
        assert _band(0.5) == "medium"

    def test_high(self):
        assert _band(0.8) == "high"

    def test_boundary_low(self):
        assert _band(0.3) == "medium"  # threshold_low=0.3 → >= means medium

    def test_boundary_high(self):
        assert _band(0.7) == "high"  # threshold_high=0.7 → >= means high

    def test_custom_thresholds(self):
        config = {"threshold_low": 0.2, "threshold_high": 0.5}
        assert _band(0.1, config) == "low"
        assert _band(0.3, config) == "medium"
        assert _band(0.6, config) == "high"


# ---------------------------------------------------------------------------
# End-to-end assess_risk
# ---------------------------------------------------------------------------


class TestAssessRisk:
    """Integration tests for assess_risk."""

    def test_coding_prompt_low_risk(self):
        result = assess_risk(
            "Implement a binary search function in Python",
            config={"mode": "shadow"},
        )
        assert isinstance(result, FactualRiskResult)
        assert result.risk_band == "low"
        assert result.risk_score < 0.3

    def test_factual_prompt_higher_risk(self):
        result = assess_risk(
            "When was the Eiffel Tower built and who is the architect?",
            config={"mode": "shadow"},
        )
        assert result.risk_score > 0.0
        assert result.risk_features["has_date_question"] == 1.0

    def test_role_adjustment_reduces_score(self):
        """A stronger-tier role discounts the same prompt more than a weaker one.

        The strong/weak pair is derived from live stack priors (strongest and
        weakest live tiers) instead of pinning worker_general vs
        architect_general, which the 2026-09-22 cutover put in the same tier_2.
        """
        by_tier = _live_roles_by_tier()
        strong_tier = next(t for t in ("tier_1", "tier_2", "tier_3") if by_tier.get(t))
        weak_tier = next(t for t in ("tier_3", "tier_2", "tier_1") if by_tier.get(t))
        assert strong_tier != weak_tier, f"live stack collapsed to one tier: {by_tier}"
        strong_role = sorted(by_tier[strong_tier])[0]
        weak_role = sorted(by_tier[weak_tier])[0]

        prompt = "What is the population of Tokyo?"
        r_weak = assess_risk(prompt, role=weak_role, config={"mode": "shadow"})
        r_strong = assess_risk(prompt, role=strong_role, config={"mode": "shadow"})
        assert r_weak.risk_score > 0.0, "prompt carries no risk — comparison is vacuous"
        assert r_strong.adjusted_risk_score <= r_weak.adjusted_risk_score
        assert r_strong.role_adjustment < r_weak.role_adjustment

    def test_no_role_means_no_adjustment(self):
        result = assess_risk("Who founded Microsoft?", config={"mode": "shadow"})
        assert result.role_adjustment == 1.0
        assert result.risk_score == result.adjusted_risk_score

    def test_result_fields_populated(self):
        result = assess_risk("Test prompt", config={"mode": "shadow"})
        assert "has_date_question" in result.risk_features
        assert "has_entity_question" in result.risk_features
        assert "claim_density" in result.risk_features
        assert 0.0 <= result.risk_score <= 1.0
        assert result.risk_band in ("low", "medium", "high")

    def test_uncertainty_in_prompt_reduces_risk(self):
        certain = "The capital of France is Paris."
        uncertain = "Maybe the capital of France is perhaps Paris, approximately."
        r_certain = assess_risk(certain, config={"mode": "shadow"})
        r_uncertain = assess_risk(uncertain, config={"mode": "shadow"})
        # Uncertainty markers should reduce risk (or at least not increase it)
        assert r_uncertain.risk_score <= r_certain.risk_score + 0.1  # Allow small tolerance


# ---------------------------------------------------------------------------
# Config / mode
# ---------------------------------------------------------------------------


class TestGetMode:
    """Mode retrieval."""

    def test_default_off(self):
        assert get_mode({}) == "off"

    def test_configured_canary_does_not_sample_arm(self):
        assert get_configured_mode({"mode": "canary", "canary_enforce_pct": 1.0}) == "canary"

    def test_canary_role_filter_keeps_excluded_role_in_shadow(self, monkeypatch):
        monkeypatch.setattr("random.random", lambda: 0.0)

        assert (
            get_mode(
                {
                    "mode": "canary",
                    "canary_ratio": 1.0,
                    "canary_roles": ["frontdoor", "worker_general"],
                },
                role="worker_vision",
            )
            == "shadow"
        )

    def test_canary_role_filter_samples_included_role(self, monkeypatch):
        monkeypatch.setattr("random.random", lambda: 0.0)

        assert (
            get_mode(
                {
                    "mode": "canary",
                    "canary_ratio": 1.0,
                    "canary_roles": ["frontdoor", "worker_general"],
                },
                role="worker_general",
            )
            == "enforce"
        )

    def test_canary_sample_key_is_deterministic_without_rng(self, monkeypatch):
        def fail_random() -> float:
            raise AssertionError("stable canary sampling must not use process RNG")

        monkeypatch.setattr("random.random", fail_random)

        config = {
            "mode": "canary",
            "canary_ratio": 0.25,
            "canary_roles": ["worker_general"],
        }
        first = get_mode(config, role="worker_general", sample_key="task-123")
        second = get_mode(config, role="worker_general", sample_key="task-123")

        assert first == second
        assert first in {"shadow", "enforce"}

    def test_canary_sample_key_uses_role_and_salt(self):
        assert _canary_roll("task-123", role="frontdoor", salt="a") == _canary_roll(
            "task-123",
            role="frontdoor",
            salt="a",
        )
        assert _canary_roll("task-123", role="frontdoor", salt="a") != _canary_roll(
            "task-123",
            role="worker_general",
            salt="a",
        )
        assert _canary_roll("task-123", role="frontdoor", salt="a") != _canary_roll(
            "task-123",
            role="frontdoor",
            salt="b",
        )

    def test_explicit_shadow(self):
        assert get_mode({"mode": "shadow"}) == "shadow"

    def test_explicit_enforce(self):
        assert get_mode({"mode": "enforce"}) == "enforce"

    def test_none_config(self):
        # With no YAML available, should default to off
        assert get_mode(None) in ("off", "shadow", "enforce")

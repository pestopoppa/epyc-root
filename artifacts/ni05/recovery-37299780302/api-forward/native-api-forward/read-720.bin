"""Tests for EV-9 pure rubric-scoring helpers."""

from __future__ import annotations

import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(_REPO_ROOT / "scripts/autopilot"))
sys.path.insert(0, str(_REPO_ROOT))

from rubric_scoring import (  # noqa: E402
    DEFAULT_RUBRIC_CRITERIA,
    DRACO_CONTENT_DIMENSIONS,
    MINDDR_PROCESS_DIMENSIONS,
    RubricCriterion,
    aggregate_rubric_score,
    build_rubric_judge_prompt,
    deterministic_rubric_fallback,
    judge_ranking_stability,
    saturated_items,
)
from safety_gate import EvalResult  # noqa: E402


def test_aggregate_rubric_score_separates_positive_and_negative_axes() -> None:
    result = aggregate_rubric_score(
        {"accuracy": 0.9, "missing_citations": 0.25},
        (
            RubricCriterion("accuracy", weight=2.0, polarity="positive"),
            RubricCriterion("missing_citations", weight=1.0, polarity="negative"),
        ),
    )

    assert result.positive_score == 0.9
    assert result.negative_penalty == 0.25
    assert result.score == 0.65
    assert result.missing_criteria == ()


def test_aggregate_rubric_score_reports_missing_criteria() -> None:
    result = aggregate_rubric_score(
        {"reasoning_trajectory": 0.8},
        (
            RubricCriterion("reasoning_trajectory"),
            RubricCriterion("citation"),
        ),
    )

    assert result.score == 0.8
    assert result.missing_criteria == ("citation",)


def test_aggregate_rubric_score_empty_is_zero_not_perfect() -> None:
    # B7b / SCORE-09 (audit 2026-07-20): an empty score map used to return a
    # perfect 1.0 (zero positive weight → positive_score defaulted to 1.0).
    # Absence of evidence is not perfection — it now returns 0.0.
    empty = aggregate_rubric_score({})
    assert empty.positive_score == 0.0
    assert empty.score == 0.0

    # All-missing (no key matches any criterion) is likewise 0.0, not 1.0.
    all_missing = aggregate_rubric_score({"unknown_dimension": 0.5})
    assert all_missing.positive_score == 0.0
    assert all_missing.score == 0.0
    assert set(all_missing.missing_criteria) == {
        c.name for c in DEFAULT_RUBRIC_CRITERIA
    }


def test_production_caller_merges_full_fallback_so_empty_sentinel_never_fires() -> None:
    # B7b / SCORE-09: the one production caller
    # (EvalTower._rubric_scores_for_answer) always merges the 8-key deterministic
    # fallback before aggregating, so even an empty answer yields a fully
    # populated (finite) score map — positive_weight is always > 0 and the
    # empty→0.0 sentinel only ever fires for genuinely-empty inputs.
    fallback = deterministic_rubric_fallback("")
    assert set(fallback) == {c.name for c in DEFAULT_RUBRIC_CRITERIA}
    assert all(math.isfinite(v) for v in fallback.values())
    aggregated = aggregate_rubric_score(fallback)
    assert aggregated.missing_criteria == ()  # every criterion is present


def test_default_rubric_dimensions_include_minddr_and_draco_axes() -> None:
    criteria_names = {
        *MINDDR_PROCESS_DIMENSIONS,
        *DRACO_CONTENT_DIMENSIONS,
    }
    scores = {name: 0.5 for name in criteria_names}

    result = aggregate_rubric_score(scores)

    assert result.score == 0.5
    assert result.missing_criteria == ()


def test_build_rubric_judge_prompt_includes_contract_and_expected_hints() -> None:
    prompt = build_rubric_judge_prompt(
        task_prompt="Compare retrieval systems.",
        answer="ColBERT trades latency for quality.",
        expected_contains=("latency tradeoff", "benchmark names"),
        criteria=(RubricCriterion("factual_accuracy"),),
    )

    assert "`scores` object" in prompt.prompt
    assert "factual_accuracy" in prompt.prompt
    assert "latency tradeoff" in prompt.prompt
    assert "Compare retrieval systems." in prompt.prompt
    assert prompt.criteria == (RubricCriterion("factual_accuracy"),)


def test_deterministic_rubric_fallback_scores_structure_and_expected_coverage() -> None:
    answer = """# Summary

- ColBERT improves BEIR recall but adds latency.
- Dense bi-encoders are cheaper.

Because the evidence differs by benchmark, the tradeoff is deployment-specific.
Source: https://example.test/paper and arxiv:2601.00001.
"""

    scores = deterministic_rubric_fallback(
        answer,
        expected_contains=("ColBERT BEIR latency", "dense cheaper"),
    )

    assert scores["factual_accuracy"] == 1.0
    assert scores["outline"] > 0.0
    assert scores["citation"] > 0.0
    assert scores["reasoning_trajectory"] > 0.0
    assert scores["content_stage"] > 0.8


def test_deterministic_rubric_fallback_uses_tool_events_for_tool_dimension() -> None:
    with_tools = deterministic_rubric_fallback("short answer", tool_events=("search", "fetch"))
    without_tools = deterministic_rubric_fallback("short answer")

    assert with_tools["tool_calls"] > without_tools["tool_calls"]


def test_saturated_items_flags_any_candidate_above_threshold() -> None:
    saturated = saturated_items({
        "easy": {"frontdoor": 0.91, "worker": 0.75},
        "hard": {"frontdoor": 0.62, "worker": 0.70},
    })

    assert saturated == {"easy": 0.91}


def test_judge_ranking_stability_uses_bradley_terry_consensus() -> None:
    stability = judge_ranking_stability({
        "judge_a": {"alpha": 0.9, "beta": 0.7, "gamma": 0.2},
        "judge_b": {"alpha": 0.8, "beta": 0.6, "gamma": 0.1},
    })

    assert stability.consensus.ranking[0] == "alpha"
    assert stability.top_choice_agreement is True
    assert stability.mean_spearman == 1.0


def test_judge_ranking_stability_surfaces_disagreement() -> None:
    stability = judge_ranking_stability({
        "judge_a": {"alpha": 0.9, "beta": 0.2, "gamma": 0.1},
        "judge_b": {"alpha": 0.1, "beta": 0.9, "gamma": 0.2},
    })

    assert stability.top_choice_agreement is False
    assert stability.mean_spearman < 1.0


def test_autopilot_eval_result_emits_rubric_metrics_populated_and_null() -> None:
    result = EvalResult(
        tier=2,
        quality=1.0,
        speed=10.0,
        cost=0.5,
        reliability=0.9,
        rubric_reasoning_trajectory=0.75,
        rubric_outline=0.5,
    )

    lines = result.to_grep_lines()

    assert "METRIC rubric_reasoning_trajectory: 0.7500" in lines
    assert "METRIC rubric_outline: 0.5000" in lines
    # D4 (audit FIELD-1): unpopulated (NaN) rubric axes now emit the explicit `null`
    # sentinel UNCONDITIONALLY — never the string `nan`, never silently dropped.
    assert "METRIC rubric_tool_calls: null" in lines
    assert "METRIC rubric_content_stage: null" in lines
    assert ": nan" not in lines
    assert math.isnan(result.rubric_tool_calls)

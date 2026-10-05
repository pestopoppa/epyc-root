"""The blessed METRIC-line parser (audit MET-1) + the producer/parser round-trip contract.

Covers scripts/autopilot/metric_lines.py and its contract with
EvalResult.to_grep_lines (scripts/autopilot/safety_gate.py). The round-trip test IS the
producer-parser contract: it must fail if a field is added to only one side.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from metric_lines import (  # type: ignore[import-not-found]
    DEFAULT_SCHEMA_VERSION,
    iter_metric_lines,
    parse_metric_lines,
)
from safety_gate import EvalResult, METRIC_LINE_SCHEMA_VERSION  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# parser unit behaviour
# ---------------------------------------------------------------------------
def test_coerces_null_int_float_and_bare_string():
    text = "\n".join(
        [
            "METRIC tier: 2",
            "METRIC quality: 2.5000",
            "METRIC diversity_ttr: null",
            "METRIC core_id: core_v2",
            "METRIC speed_metric_mode: aggregate_batch_tps",
        ]
    )
    d = parse_metric_lines(text)
    assert d["tier"] == 2 and isinstance(d["tier"], int)
    assert d["quality"] == 2.5 and isinstance(d["quality"], float)
    assert d["diversity_ttr"] is None
    assert d["core_id"] == "core_v2"
    assert d["speed_metric_mode"] == "aggregate_batch_tps"


def test_bracketed_subkey_is_a_flat_key():
    d = parse_metric_lines("METRIC tool_helpfulness[coder]: 0.1000")
    assert d["tool_helpfulness[coder]"] == 0.1
    # the scalar and the bracketed forms are distinct keys, never collapsed
    assert "tool_helpfulness" not in d


def test_schema_version_read_from_line():
    assert parse_metric_lines("METRIC schema_version: 2")["schema_version"] == 2


def test_schema_version_defaults_when_absent():
    d = parse_metric_lines("METRIC quality: 1.0000")
    assert d["schema_version"] == DEFAULT_SCHEMA_VERSION == 1


def test_non_metric_and_malformed_lines_are_skipped():
    text = "\n".join(
        [
            "Trial 5: dispatching action",
            "METRIC quality: 1.5000",
            "not a metric line at all",
            "METRICWITHOUTSPACE: nope",
        ]
    )
    keys = {k for k, _ in iter_metric_lines(text)}
    assert keys == {"quality"}


def test_value_with_embedded_colon_keeps_everything_after_first_sep():
    # The key is non-greedy up to the FIRST ':'; a value may itself carry ': '.
    d = parse_metric_lines("METRIC note: a: b: c")
    assert d["note"] == "a: b: c"


def test_last_write_wins_on_duplicate_key():
    d = parse_metric_lines("METRIC quality: 1.0000\nMETRIC quality: 2.0000")
    assert d["quality"] == 2.0


def test_iter_and_parse_agree_on_count():
    text = "\n".join(
        ["METRIC schema_version: 2", "METRIC tier: 1", "junk", "METRIC quality: 1.2000"]
    )
    pairs = list(iter_metric_lines(text))
    assert len(pairs) == 3  # schema_version, tier, quality (junk skipped)


# ---------------------------------------------------------------------------
# producer/parser ROUND-TRIP CONTRACT (audit MET-1)
# ---------------------------------------------------------------------------
# Every UNCONDITIONALLY-emitted scalar key. If a field is added to to_grep_lines
# without being reflected here (or vice versa), this frozenset drifts from the parsed
# key set and the contract test below fails — the whole point of pinning it.
_EXPECTED_SCALAR_KEYS = frozenset(
    {
        "schema_version",
        "trial",
        "species",
        "tier",
        "quality",
        "speed",
        "speed_metric_mode",
        "median_request_speed",
        "aggregate_speed",
        "eval_concurrency",
        "eval_wall_s",
        "cost",
        "reliability",
        "n_questions",
        "instruction_tokens",
        "instruction_ratio",
        "partial_count",
        "degraded_count",
        "ece",
        "auroc",
        "calibration_violations",
        "rlvr_policy",
        "rlvr_signal",
        "rlvr_reward",
        "rlvr_ready",
        "branching_density",
        "avg_prompt_tokens",
        "compaction_events",
        "mean_tools_used",
        "tool_use_rate",
        "total_tool_calls",
        "tool_helpfulness",
        "diversity_entropy",
        "diversity_distinct2",
        "diversity_self_bleu",
        "diversity_ttr",
        "diversity_semantic_embedding_agreement",
        "rubric_reasoning_trajectory",
        "rubric_tool_calls",
        "rubric_outline",
        "rubric_content_stage",
        "reviewer_fa_rate",
        "reviewer_fr_rate",
        "reviewer_fa_fr_ratio",
        "review_decision_latency_ms",
    }
)


def _fully_populated() -> EvalResult:
    """An EvalResult with every NaN-gated axis populated (finite) so nothing emits null,
    plus one per-suite/route/tool-helpfulness entry to exercise the dynamic keys."""
    return EvalResult(
        tier=2,
        quality=2.5,
        speed=12.7,
        cost=0.3,
        reliability=0.91,
        per_suite_quality={"coder": 2.9},
        routing_distribution={"worker": 1.0},
        n_questions=42,
        core_id="core_v2",
        median_request_speed=11.0,
        aggregate_speed=40.0,
        eval_concurrency=4,
        eval_wall_s=5.5,
        instruction_token_count=17,
        instruction_token_ratio=0.12,
        partial_count=1,
        degraded_count=2,
        mean_tools_used=0.5,
        tool_use_rate=0.25,
        total_tool_calls=3,
        tool_helpfulness=0.08,
        per_suite_tool_helpfulness={"coder": 0.1},
        avg_prompt_tokens=1234.0,
        compaction_events=6,
        diversity_entropy=3.14,
        diversity_distinct2=0.72,
        diversity_self_bleu=0.21,
        diversity_ttr=0.55,
        diversity_semantic_embedding_agreement=0.35,
        rubric_reasoning_trajectory=0.8,
        rubric_tool_calls=0.6,
        rubric_outline=0.5,
        rubric_content_stage=0.4,
        ece=0.05,
        auroc=0.85,
        calibration_violations=2,
        branching_density=0.3,
        reviewer_fa_rate=0.1,
        reviewer_fr_rate=0.2,
        reviewer_fa_fr_ratio=0.5,
        review_decision_latency_ms=250.0,
    )


def test_round_trip_every_emitted_scalar_key_is_present_and_typed():
    r = _fully_populated()
    out = r.to_grep_lines(trial_id=7, species="s1")
    d = parse_metric_lines(out)

    # (1) schema version reflects the producer constant.
    assert d["schema_version"] == METRIC_LINE_SCHEMA_VERSION == 2

    # (2) every unconditional scalar key round-trips.
    missing = _EXPECTED_SCALAR_KEYS - set(d)
    assert not missing, f"emitted-but-unparsed / missing scalar keys: {sorted(missing)}"

    # (3) the emitter emits NOTHING outside the contract: scalar keys (minus the dynamic
    #     suite_*/route_*/tool_helpfulness[*] families and the two CONDITIONALLY-emitted
    #     scalars core_id / rlvr_blockers) equal the expected frozenset. This is what fails
    #     if an UNCONDITIONAL field is added to only ONE side of the contract.
    dynamic = {
        k
        for k in d
        if k.startswith(("suite_", "route_")) or k.startswith("tool_helpfulness[")
    }
    conditional = {"core_id", "rlvr_blockers"}
    assert set(d) - dynamic - conditional == _EXPECTED_SCALAR_KEYS
    assert d["core_id"] == "core_v2"  # conditional scalar present when populated

    # (4) representative typed values survived the round-trip.
    assert d["trial"] == 7 and isinstance(d["trial"], int)
    assert d["species"] == "s1"
    assert d["quality"] == 2.5 and isinstance(d["quality"], float)
    assert d["partial_count"] == 1 and isinstance(d["partial_count"], int)
    assert d["diversity_entropy"] == 3.14
    assert d["reviewer_fa_rate"] == 0.1
    # (5) dynamic families.
    assert d["suite_coder"] == 2.9
    assert d["route_worker"] == 1.0
    assert d["tool_helpfulness[coder]"] == 0.1


def test_round_trip_unavailable_fields_are_none_not_nan():
    # A bare result leaves every NaN-gated axis unavailable → all emit `null` → parse None.
    r = EvalResult(tier=1, quality=1.5, speed=10.0, cost=0.2, reliability=0.9)
    out = r.to_grep_lines()
    assert ": nan" not in out  # never the string 'nan'
    d = parse_metric_lines(out)
    for key in (
        "diversity_entropy",
        "rubric_outline",
        "reviewer_fa_rate",
        "tool_helpfulness",
    ):
        assert d[key] is None, f"{key} should round-trip to None"
    # a real zero is still a zero, not None (kills absence-vs-zero ambiguity).
    assert d["partial_count"] == 0
    assert d["auroc"] == 0.0

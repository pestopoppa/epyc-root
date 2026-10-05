"""EvalResult.to_grep_lines v2 contract (audit D4/D6 — MET-1, MET-2, FIELD-1).

Covers the emitter side: schema_version line, unconditional null emission, the
tool-telemetry block (D6), interpolated-name sanitization (MET-2), and ece-as-null.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from safety_gate import EvalResult  # type: ignore[import-not-found]


def _lines(r: EvalResult, **kw) -> list[str]:
    return r.to_grep_lines(**kw).splitlines()


def _base(**over) -> EvalResult:
    d = dict(tier=2, quality=1.5, speed=10.0, cost=0.2, reliability=0.9)
    d.update(over)
    return EvalResult(**d)


# --- D4 (MET-1): schema_version -------------------------------------------------
def test_first_line_is_schema_version_2():
    out = _lines(_base())
    assert out[0] == "METRIC schema_version: 2"


# --- D4 (FIELD-1): unconditional emission with explicit null ---------------------
def test_nan_axes_emit_literal_null_never_nan():
    out = _base().to_grep_lines()
    # every NaN-defaulted axis is present as `null`, not dropped, not 'nan'.
    for key in (
        "diversity_entropy",
        "diversity_semantic_embedding_agreement",
        "rubric_tool_calls",
        "rubric_content_stage",
        "reviewer_fa_rate",
        "reviewer_fa_fr_ratio",
        "review_decision_latency_ms",
        "tool_helpfulness",
    ):
        assert f"METRIC {key}: null" in out
    assert ": nan" not in out


def test_zero_counts_emit_zero_not_dropped():
    # partial_count/degraded_count/calibration_violations/compaction_events default 0 and
    # were previously emitted only when > 0; now a real zero is always visible.
    out = _base().to_grep_lines()
    for key in ("partial_count", "degraded_count", "calibration_violations", "compaction_events"):
        assert f"METRIC {key}: 0" in out
    assert "METRIC auroc: 0.0000" in out
    assert "METRIC branching_density: 0.0000" in out
    assert "METRIC avg_prompt_tokens: 0" in out


def test_populated_axis_still_emits_value():
    out = _base(diversity_entropy=3.14, auroc=0.85, partial_count=4).to_grep_lines()
    assert "METRIC diversity_entropy: 3.1400" in out
    assert "METRIC auroc: 0.8500" in out
    assert "METRIC partial_count: 4" in out


# --- D6 (FIELD-1 partial): tool-telemetry block ---------------------------------
def test_tool_telemetry_block_is_emitted():
    r = _base(mean_tools_used=0.5, tool_use_rate=0.25, total_tool_calls=3, tool_helpfulness=0.08)
    out = r.to_grep_lines()
    assert "METRIC mean_tools_used: 0.5000" in out
    assert "METRIC tool_use_rate: 0.2500" in out
    assert "METRIC total_tool_calls: 3" in out
    assert "METRIC tool_helpfulness: 0.0800" in out


def test_per_suite_tool_helpfulness_emits_only_populated_suites():
    r = _base(per_suite_tool_helpfulness={"coder": 0.1, "math": float("nan"), "qa": 0.2})
    out = r.to_grep_lines()
    assert "METRIC tool_helpfulness[coder]: 0.1000" in out
    assert "METRIC tool_helpfulness[qa]: 0.2000" in out
    # NaN per-suite entry is skipped (bounded, populated-only) — not emitted as null.
    assert "tool_helpfulness[math]" not in out


def test_per_suite_tool_helpfulness_non_dict_is_ignored():
    # Defensive: a scalar (legacy) value must not crash the emitter.
    r = _base()
    r.per_suite_tool_helpfulness = 0.5  # type: ignore[assignment]
    out = r.to_grep_lines()
    assert "tool_helpfulness[" not in out


# --- MET-2: interpolated-name sanitization --------------------------------------
def test_species_with_colon_and_space_is_sanitized():
    out = _base().to_grep_lines(species="weird: name here")
    assert "METRIC species: weird_name_here" in out


def test_suite_and_route_names_are_sanitized():
    r = _base(
        per_suite_quality={"tool: use": 1.5},
        routing_distribution={"arch tier": 0.5},
    )
    out = r.to_grep_lines()
    assert "METRIC suite_tool_use: 1.5000" in out
    assert "METRIC route_arch_tier: 0.5000" in out


# --- D4 (item e): ece as null when non-finite -----------------------------------
def test_ece_emits_null_when_non_finite():
    assert "METRIC ece: null" in _base(ece=float("nan")).to_grep_lines()
    assert "METRIC ece: 0.0500" in _base(ece=0.05).to_grep_lines()


def test_non_finite_core_objective_emits_null():
    # A degenerate quality (NaN) emits null rather than the string 'nan'.
    out = _base(quality=float("nan")).to_grep_lines()
    assert "METRIC quality: null" in out
    assert ": nan" not in out

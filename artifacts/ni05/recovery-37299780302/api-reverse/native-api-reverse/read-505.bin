"""Tests for NIB2-45 Week 3: sentinel suite + EvalResult rubric stubs."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(_REPO_ROOT))


SENTINEL_PATH = _REPO_ROOT / "orchestration/deep_research_sentinel.yaml"


def test_deep_research_sentinel_exists_and_parses():
    assert SENTINEL_PATH.exists(), "MD-8 sentinel file missing"
    data = yaml.safe_load(SENTINEL_PATH.read_text())
    assert isinstance(data, list)
    assert len(data) >= 20, f"Expected ≥20 sentinel entries, got {len(data)}"


def test_sentinel_stratification():
    """Per MD-8: 7 BrowseComp + 7 WideSearch + 6 mixed (20 total)."""
    data = yaml.safe_load(SENTINEL_PATH.read_text())
    styles: dict[str, int] = {}
    for entry in data:
        styles[entry["style"]] = styles.get(entry["style"], 0) + 1
    assert styles.get("browsecomp", 0) >= 6
    assert styles.get("widesearch", 0) >= 6
    assert styles.get("mixed", 0) >= 5


def test_sentinel_entries_have_required_fields():
    data = yaml.safe_load(SENTINEL_PATH.read_text())
    required = {"id", "suite", "style", "prompt", "expected_contains"}
    for entry in data:
        missing = required - entry.keys()
        assert not missing, f"{entry.get('id', '?')} missing {missing}"
        assert isinstance(entry["expected_contains"], list)
        assert len(entry["expected_contains"]) >= 2


def test_sentinel_prompts_trigger_research_like_detector():
    """Every sentinel prompt should be classified as research-like."""
    from src.classifiers.research_like import is_research_like

    data = yaml.safe_load(SENTINEL_PATH.read_text())
    failures = [e["id"] for e in data if not is_research_like(e["prompt"])]
    assert not failures, f"Sentinels not classified research-like: {failures}"


def test_eval_result_has_rubric_stub_fields():
    from src.diversity_gate import EvalResult

    r = EvalResult(quality=1.0, speed=20.0, cost=0.5, reliability=0.9)
    assert math.isnan(r.rubric_reasoning_trajectory)
    assert math.isnan(r.rubric_tool_calls)
    assert math.isnan(r.rubric_outline)
    assert math.isnan(r.rubric_content_stage)


def test_rubric_fields_populatable():
    """Fields accept float values without affecting SafetyGate's core logic."""
    from src.diversity_gate import EvalResult, SafetyGate, Verdict

    baseline = EvalResult(quality=1.0, speed=20.0, cost=0.5, reliability=0.9)
    trial = EvalResult(
        quality=1.1, speed=20.0, cost=0.5, reliability=0.9,
        rubric_reasoning_trajectory=0.85,
        rubric_tool_calls=0.70,
        rubric_outline=0.90,
        rubric_content_stage=0.75,
    )
    gate = SafetyGate(baseline=baseline, warn_only=False)
    v = gate.evaluate(trial)
    assert v.verdict == Verdict.PASS  # quality up, nothing else changed

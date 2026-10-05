"""Tests for NIB2-45 Week 1: deep_research_mode flag + research_like classifier.

Covers:
  - Feature flag registration and env-var activation.
  - is_research_like / score_research_like: positive + negative exemplars.
  - classifier_config.yaml parses with the new research_like category.
  - Three new prompt files exist and are non-empty.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(_REPO_ROOT))


# ── MD-1: feature flag ─────────────────────────────────────────────

def test_deep_research_mode_in_registry():
    from src.features import _REGISTRY_BY_NAME
    spec = _REGISTRY_BY_NAME.get("deep_research_mode")
    assert spec is not None
    assert spec.env_var == "DEEP_RESEARCH_MODE"


def test_deep_research_mode_default_off():
    from src.features import Features
    assert Features().deep_research_mode is False


def test_deep_research_mode_env_override(monkeypatch):
    """ORCHESTRATOR_DEEP_RESEARCH_MODE=1 flips the default."""
    from src.features import get_features

    monkeypatch.setenv("ORCHESTRATOR_DEEP_RESEARCH_MODE", "1")
    monkeypatch.setenv("ORCHESTRATOR_MOCK_MODE", "1")  # stabilise env
    features = get_features()
    assert features.deep_research_mode is True


# ── MD-2: research_like detector ────────────────────────────────────

@pytest.mark.parametrize("prompt", [
    "Compare transformer architectures across parameter scales and their tradeoffs",
    "Do a deep dive on the current state of long-context retrieval",
    "Research and synthesize: how do recent reasoning-model training recipes differ",
    "Walk me through the landscape of speculative decoding techniques",
    "Investigate: what are the leading approaches to post-training diversity collapse",
    "Compare X vs Y vs Z on quality and latency",
    "Give me a comprehensive survey of mixture-of-experts routing strategies",
    "Qwen3 vs Llama3 vs Mistral — which wins for code?",
    "How do SSM models differ from transformers, and when should each be used?",
])
def test_positive_research_prompts(prompt):
    from src.classifiers.research_like import is_research_like
    assert is_research_like(prompt) is True, f"Expected research-like: {prompt!r}"


@pytest.mark.parametrize("prompt", [
    "What is 2 + 2?",
    "Please fix the typo in line 5 of foo.py",
    "Summarize this paragraph in one sentence",
    "Write a unit test for the parse() function",
    "Show me the logs from the last deploy",
    "",
    "   ",
])
def test_negative_prompts(prompt):
    from src.classifiers.research_like import is_research_like
    assert is_research_like(prompt) is False, f"Expected NOT research-like: {prompt!r}"


def test_score_research_like_monotonic_with_signals():
    from src.classifiers.research_like import score_research_like
    low = score_research_like("fix this bug")
    mid = score_research_like("Compare A vs B")
    high = score_research_like("Deep dive and comprehensive survey of A vs B vs C")
    assert low < mid <= high
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0


# ── classifier_config.yaml — research_like category ────────────────

def test_classifier_config_has_research_like_exemplars():
    import yaml
    cfg_path = _REPO_ROOT / "orchestration/classifier_config.yaml"
    data = yaml.safe_load(cfg_path.read_text())
    exemplars = data.get("classification_exemplars", {})
    assert "research_like" in exemplars
    prompts = [e["prompt"] for e in exemplars["research_like"]]
    assert len(prompts) >= 5
    # Every exemplar should itself pass the detector — sanity check.
    from src.classifiers.research_like import is_research_like
    failed = [p for p in prompts if not is_research_like(p)]
    assert not failed, f"Exemplars failed detector: {failed}"


# ── MD-3/4/5: three agent prompts exist ────────────────────────────

@pytest.mark.parametrize("name", ["planning_agent.md", "deep_search_agent.md", "report_agent.md"])
def test_minddr_prompt_files_exist(name):
    path = _REPO_ROOT / "orchestration/prompts" / name
    assert path.exists(), f"Missing MindDR prompt file: {name}"
    content = path.read_text()
    assert len(content) > 200, f"{name} looks empty / stub"
    assert "MindDR" in content or "NIB2-45" in content

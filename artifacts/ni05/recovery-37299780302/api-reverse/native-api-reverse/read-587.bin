from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))

import peaf  # noqa: E402


def test_prompt_uses_journal_quality_scale() -> None:
    prompt = peaf.peaf_prompt_addendum()

    assert '"quality": 2.40' in prompt
    assert "quality in [0,3]" in prompt
    assert "reliability in [0,1]" in prompt
    assert "quality and reliability in [0,1]" not in prompt


def test_quality_surprise_is_normalized_by_eval_tower_scale() -> None:
    surprise = peaf.compute_surprise(
        predicted={"quality": 2.4},
        actual={"quality": 3.0},
    )

    assert surprise == pytest.approx(0.2)

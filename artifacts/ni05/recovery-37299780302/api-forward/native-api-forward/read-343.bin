"""SEAGym-style EvalTower view accounting."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from eval_tower_seagym_views import (  # noqa: E402
    SEAGYM_VIEWS,
    build_seagym_view_summary,
    render_seagym_view_summary,
    seagym_view_for_question,
)
from safety_gate import EvalResult  # noqa: E402


def test_seagym_view_for_question_prefers_explicit_view_metadata() -> None:
    assert seagym_view_for_question({"seagym_view": "train"}) == "train"
    assert seagym_view_for_question({"eval_view": "held-out"}) == "test"
    assert seagym_view_for_question({"partition": "tool_sentinel"}) == "replay"
    assert seagym_view_for_question({"partition": "audit"}) == "ood"


def test_seagym_summary_classifies_explicit_and_inferred_eval_views() -> None:
    result = EvalResult(
        tier=2,
        quality=0.0,
        speed=0.0,
        cost=0.0,
        reliability=1.0,
        question_results=[
            {"qid": "train-1", "suite": "general", "partition": "train", "correct": True},
            {"qid": "valid-1", "suite": "coder", "partition": "validation", "correct": True},
            {"qid": "test-1", "suite": "math", "partition": "core", "correct": False},
            {
                "qid": "replay-1",
                "suite": "tool_use",
                "partition": "tool_sentinel",
                "correct": True,
            },
            {"qid": "ood-1", "suite": "fresh_suite", "partition": "audit", "correct": False},
        ],
        details={"promotion_eval_policy": {"enabled": True}},
    )

    summary = build_seagym_view_summary(result)

    assert summary["schema_version"] == "seagym_eval_views.v1"
    assert summary["observe_only"] is True
    assert summary["scoring_effect"] == "none"
    assert summary["view_counts"] == {
        "train": 1,
        "validation": 1,
        "test": 1,
        "replay": 1,
        "ood": 1,
    }
    assert summary["views"]["train"]["quality"] == pytest.approx(3.0)
    assert summary["views"]["test"]["quality"] == pytest.approx(0.0)
    assert summary["views"]["replay"]["suite_counts"] == {"tool_use": 1}


def test_seagym_summary_keeps_empty_views_and_infers_core_by_tier() -> None:
    summary = build_seagym_view_summary(
        EvalResult(
            tier=1,
            quality=0.0,
            speed=0.0,
            cost=0.0,
            reliability=1.0,
            question_results=[
                {"qid": "core-1", "suite": "general", "partition": "core", "correct": True}
            ],
        )
    )

    assert tuple(summary["views"]) == SEAGYM_VIEWS
    assert summary["view_counts"]["validation"] == 1
    assert summary["view_counts"]["train"] == 0
    assert summary["view_counts"]["test"] == 0


def test_seagym_summary_accepts_nested_journal_payloads() -> None:
    summary = build_seagym_view_summary(
        {
            "tier": 3,
            "eval_details": {
                "details": {
                    "question_results": [
                        {
                            "qid": "hard-1",
                            "suite": "expert_hard",
                            "partition": "core",
                            "correct": True,
                        }
                    ]
                }
            },
        }
    )

    assert summary["view_counts"]["ood"] == 1
    assert summary["views"]["ood"]["suite_counts"] == {"expert_hard": 1}


def test_render_seagym_summary_includes_all_views() -> None:
    rendered = render_seagym_view_summary(
        build_seagym_view_summary(
            EvalResult(
                tier=0,
                quality=0.0,
                speed=0.0,
                cost=0.0,
                reliability=1.0,
                question_results=[
                    {
                        "qid": "sentinel-1",
                        "suite": "sentinel_general",
                        "partition": "core",
                        "correct": True,
                    }
                ],
            )
        )
    )

    assert "# EvalTower SEAGym View Summary" in rendered
    assert "| replay | 1 | 1 | 3.000 | sentinel_general=1 |" in rendered
    assert "| train | 0 | 0 | 0.000 | - |" in rendered

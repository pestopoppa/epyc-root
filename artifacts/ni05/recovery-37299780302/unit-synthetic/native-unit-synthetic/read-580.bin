from __future__ import annotations

from scripts.autopilot.pareto_stepping_stones_report import (
    build_stepping_stones_report_from_rows,
)


def _row(
    trial_id: int,
    *,
    quality: float,
    speed: float,
    reliability: float,
    species: str = "",
    reasoning: str = "",
) -> dict:
    return {
        "trial_id": trial_id,
        "tier": 1,
        "quality": quality,
        "speed": speed,
        "cost": 0.1,
        "reliability": reliability,
        "species": species,
        "reasoning": reasoning,
        "timestamp": f"2026-07-02T00:00:{trial_id:02d}+00:00",
    }


def test_build_stepping_stones_report_from_rows_is_observe_only() -> None:
    rows = [
        _row(1, quality=2.0, speed=50.0, reliability=1.0),
        _row(2, quality=1.8, speed=70.0, reliability=1.0),
        _row(
            3,
            quality=1.7,
            speed=45.0,
            reliability=0.95,
            species="prompt_forge",
            reasoning='{"type": "prompt_mutation"}',
        ),
        _row(
            4,
            quality=1.91,
            speed=49.0,
            reliability=0.99,
            species="prompt_forge",
            reasoning='{"type": "prompt_mutation"}',
        ),
        _row(
            5,
            quality=1.72,
            speed=68.0,
            reliability=0.98,
            species="numeric_swarm",
            reasoning='{"type": "numeric_trial"}',
        ),
    ]

    report = build_stepping_stones_report_from_rows(rows, limit=2)

    assert report["ok"] is True
    assert report["frontier_size"] == 2
    assert [row["trial_id"] for row in report["stepping_stones"]] == [4, 5]
    assert "observe-only" in report["note"]
    assert "not replay authorization" in report["text"]

"""Seeder state persistence for item analytics."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot" / "species"))

from seeder import Seeder  # noqa: E402


def test_seeder_state_round_trips_seen_ids_and_question_results() -> None:
    seeder = Seeder.__new__(Seeder)
    seeder._td_errors = [(0, 0.1), (1, 0.01)]
    seeder._batch_count = 2
    seeder._consecutive_converged = 1
    seeder._seen = {"q2", "q1"}
    seeder._question_results = [
        {
            "batch_num": 1,
            "seed": 123,
            "suite": "math",
            "question_id": "q1",
            "rewards": {"frontdoor": 1.0},
            "roles_tested": ["frontdoor"],
        }
    ]

    state = Seeder.export_state(seeder)

    assert state["seen_question_ids"] == ["q1", "q2"]
    assert state["question_results"] == seeder._question_results

    restored = Seeder.__new__(Seeder)
    Seeder.restore_state(restored, state)

    assert restored._seen == {"q1", "q2"}
    assert restored._question_results == seeder._question_results
    assert restored._batch_count == 2
    assert restored._consecutive_converged == 1


def test_seeder_restore_initializes_item_state_for_legacy_payload() -> None:
    restored = Seeder.__new__(Seeder)

    Seeder.restore_state(restored, {"td_errors": [0.1]})

    assert restored._seen == set()
    assert restored._question_results == []

"""T3 eval lane contract tests."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from eval_tower import EvalTower, QuestionResult  # type: ignore[import-not-found]


def _question(qid: str, suite: str, tier: int, expected: str = "answer") -> dict:
    return {
        "id": qid,
        "qid": qid,
        "suite": suite,
        "tier": tier,
        "prompt": f"{suite} prompt {qid}",
        "expected": expected,
        "scoring_method": "exact_match",
    }


def test_eval_t3_samples_only_explicit_pool_tier_three(monkeypatch) -> None:
    tower = EvalTower(url="http://127.0.0.1:1", timeout=1)
    pool = {
        "math": [_question("math_t1", "math", 1), _question("math_t3", "math", 3)],
        "code": [_question("code_t2", "code", 2), _question("code_t3", "code", 3)],
        "empty": [_question("empty_t3_unscoreable", "empty", 3, expected="")],
    }
    captured: list[dict] = []

    monkeypatch.setattr(tower, "_load_pool", lambda: pool)

    def fake_eval_batch(questions, _client, log_every=50, label=""):
        assert log_every == 50
        assert label == "T3"
        captured.extend(questions)
        return [
            QuestionResult(
                question_id=q["id"],
                qid=q["qid"],
                suite=q["suite"],
                prompt=q["prompt"],
                expected=q["expected"],
                correct=True,
                tokens_generated=20,
                elapsed_s=1.0,
                eval_wall_s=2.0,
                eval_partition=q.get("eval_partition", "core"),
            )
            for q in questions
        ]

    monkeypatch.setattr(tower, "_eval_batch", fake_eval_batch)

    result = tower.eval_t3(n=4, seed=7)

    assert result.tier == 3
    assert result.quality == 3.0
    assert {q["qid"] for q in captured} == {"math_t3", "code_t3"}
    assert all(q["tier"] == 3 for q in captured)
    assert all(q["eval_partition"] == "core" for q in captured)
    assert result.details["t3_policy"] == {
        "version": "t3-hard-only-v1",
        "requested_n": 4,
        "actual_n": 2,
        "seed": 7,
        "pool_tier": 3,
    }
    assert result.core_id == "t3_hard_only_v1_seed_7_n4"

"""Tests for the deterministic token-coverage offline reward-oracle scorer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.graph_router import score_offline_reward_oracle_token_coverage as scorer_mod


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_reference_token_coverage_scores_reference_recall() -> None:
    assert scorer_mod.reference_token_coverage(
        "Paris France capital",
        "The capital of France is Paris.",
    ) == 1.0
    assert scorer_mod.reference_token_coverage(
        "Paris France capital",
        "Paris is a city.",
    ) == pytest.approx(1 / 3)
    assert scorer_mod.reference_token_coverage("", "anything") == 0.0


def test_score_rows_adds_score_and_metadata() -> None:
    rows = [
        {
            "item_id": "a",
            "reference": "return sorted nums",
            "response": "Use sorted(nums) and return the result.",
            "target_source": "answer_equivalence_final_label",
            "variant_type": "base",
        },
        {
            "item_id": "b",
            "reference": "return sorted nums",
            "response": "Print the original input.",
            "target_source": "heldout_stress_binary_reward",
            "variant_type": "confound",
        },
    ]

    scored, summary = scorer_mod.score_rows(rows)

    assert scored[0]["oracle_score"] == 1.0
    assert scored[1]["oracle_score"] == 0.0
    assert scored[0]["oracle_score_source"] == "reference_token_coverage"
    assert scored[0]["oracle_model_id"] == "deterministic/reference-token-coverage-v1"
    assert summary["rows"] == 2
    assert summary["score_min"] == 0.0
    assert summary["score_max"] == 1.0
    assert summary["stats"]["target_source:answer_equivalence_final_label"] == 1
    assert summary["stats"]["target_source:heldout_stress_binary_reward"] == 1
    assert summary["stats"]["variant_type:base"] == 1
    assert summary["stats"]["variant_type:confound"] == 1


def test_score_rows_refuses_existing_oracle_score_without_overwrite() -> None:
    rows = [
        {
            "reference": "expected answer",
            "response": "expected answer",
            "oracle_score": 0.25,
        }
    ]

    with pytest.raises(ValueError, match="oracle_score already present"):
        scorer_mod.score_rows(rows)

    scored, _summary = scorer_mod.score_rows(rows, overwrite=True)
    assert scored[0]["oracle_score"] == 1.0


def test_score_rows_requires_reference_and_response() -> None:
    with pytest.raises(ValueError, match="reference is required"):
        scorer_mod.score_rows([{"response": "answer"}])
    with pytest.raises(ValueError, match="response is required"):
        scorer_mod.score_rows([{"reference": "expected"}])


def test_cli_writes_scored_jsonl_and_summary(tmp_path: Path) -> None:
    input_path = _write_jsonl(
        tmp_path / "rows.jsonl",
        [
            {
                "item_id": "a",
                "reference": "alpha beta",
                "response": "alpha",
                "binary_reward": 1.0,
            }
        ],
    )
    output_path = tmp_path / "scored.jsonl"
    summary_path = tmp_path / "summary.json"
    summary_md_path = tmp_path / "summary.md"

    assert scorer_mod.main(
        [
            "--input-jsonl",
            str(input_path),
            "--output-jsonl",
            str(output_path),
            "--summary-json",
            str(summary_path),
            "--summary-md",
            str(summary_md_path),
        ]
    ) == 0

    scored = [
        json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()
    ]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert scored[0]["oracle_score"] == 0.5
    assert summary["model_id"] == "deterministic/reference-token-coverage-v1"
    assert "Offline Reward Oracle Token Coverage Scores" in summary_md_path.read_text(
        encoding="utf-8"
    )

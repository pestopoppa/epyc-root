"""Tests for the NeuralTxt offline reward-oracle scorer adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.graph_router import score_offline_reward_oracle_neuraltxt as scorer_mod


class _FakeScorer:
    def score(self, reference: str, response: str) -> float:
        assert reference
        assert response
        return 1.25 if "high" in response else 0.25


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_score_rows_adds_clamped_oracle_score_and_metadata() -> None:
    rows = [
        {
            "item_id": "a",
            "reference": "expected",
            "response": "high quality",
            "binary_reward": 1.0,
            "variant_type": "base",
        },
        {
            "item_id": "b",
            "reference": "expected",
            "response": "low quality",
            "binary_reward": 0.0,
            "variant_type": "confound",
        },
    ]

    scored, summary = scorer_mod.score_rows(rows, _FakeScorer(), model_id="test/model")

    assert [row["oracle_score"] for row in scored] == [1.0, 0.25]
    assert scored[0]["oracle_score_source"] == "neuraltxt_reward_tiny"
    assert scored[0]["oracle_model_id"] == "test/model"
    assert summary["rows"] == 2
    assert summary["score_min"] == 0.25
    assert summary["score_max"] == 1.0
    assert summary["stats"]["variant_type:base"] == 1
    assert summary["stats"]["variant_type:confound"] == 1


def test_score_rows_refuses_existing_oracle_score_without_overwrite() -> None:
    rows = [
        {
            "reference": "expected",
            "response": "answer",
            "binary_reward": 1.0,
            "oracle_score": 0.5,
        }
    ]

    with pytest.raises(ValueError, match="oracle_score already present"):
        scorer_mod.score_rows(rows, _FakeScorer())

    scored, _summary = scorer_mod.score_rows(rows, _FakeScorer(), overwrite=True)
    assert scored[0]["oracle_score"] == 0.25


def test_score_rows_requires_reference_and_response() -> None:
    with pytest.raises(ValueError, match="reference is required"):
        scorer_mod.score_rows([{"response": "answer"}], _FakeScorer())
    with pytest.raises(ValueError, match="response is required"):
        scorer_mod.score_rows([{"reference": "expected"}], _FakeScorer())


def test_cli_writes_scored_jsonl_and_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = _write_jsonl(
        tmp_path / "rows.jsonl",
        [
            {
                "item_id": "a",
                "reference": "expected",
                "response": "high quality",
                "binary_reward": 1.0,
            }
        ],
    )
    output_path = tmp_path / "scored.jsonl"
    summary_path = tmp_path / "summary.json"
    monkeypatch.setattr(
        scorer_mod,
        "build_scorer",
        lambda **_kwargs: _FakeScorer(),
    )

    assert scorer_mod.main(
        [
            "--input-jsonl",
            str(input_path),
            "--output-jsonl",
            str(output_path),
            "--summary-json",
            str(summary_path),
        ]
    ) == 0

    scored = [
        json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()
    ]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert scored[0]["oracle_score"] == 1.0
    assert summary["model_id"] == "paperbd/neuraltxt-reward-tiny"

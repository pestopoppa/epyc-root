"""Tests for offline reward-oracle stress-row generation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.build_offline_reward_oracle_stress_rows import (
    build_stress_rows,
    main,
)


def _rows() -> list[dict]:
    return [
        {
            "item_id": "a",
            "suite": "general",
            "reference": "Paris",
            "response": "Paris",
            "binary_reward": 1.0,
            "q_reward": 1.0,
        },
        {
            "item_id": "b",
            "suite": "general",
            "reference": "Canberra",
            "response": "Sydney",
            "binary_reward": 0.0,
            "q_reward": 0.0,
        },
        {
            "item_id": "c",
            "suite": "math",
            "reference": "4",
            "response": "4",
            "binary_reward": 1.0,
        },
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_build_stress_rows_adds_grouped_base_paraphrase_and_confound() -> None:
    stress_rows, summary = build_stress_rows(_rows(), max_groups=1)

    assert summary["groups"] == 1
    assert summary["rows"] == 3
    assert [row["variant_type"] for row in stress_rows] == [
        "base",
        "paraphrase",
        "confound",
    ]
    assert {row["variant_group"] for row in stress_rows} == {"a"}
    assert stress_rows[1]["response"] == "In other words: Paris"
    assert stress_rows[1]["binary_reward"] == 1.0
    assert stress_rows[2]["response"] == "Sydney"
    assert stress_rows[2]["binary_reward"] == 0.0
    assert stress_rows[2]["confound_source_item_id"] == "b"
    assert "oracle_score" not in stress_rows[0]


def test_build_stress_rows_can_omit_base_rows() -> None:
    stress_rows, summary = build_stress_rows(_rows(), max_groups=1, include_base=False)

    assert summary["include_base"] is False
    assert [row["variant_type"] for row in stress_rows] == ["paraphrase", "confound"]


def test_build_stress_rows_defaults_malformed_optional_q_reward() -> None:
    rows = _rows()
    rows[0]["q_reward"] = "not-a-score"

    stress_rows, _summary = build_stress_rows(rows, max_groups=1)

    assert stress_rows[0]["q_reward"] == 1.0
    assert stress_rows[1]["q_reward"] == 1.0


def test_cli_writes_jsonl_and_summary(tmp_path: Path) -> None:
    input_path = _write_jsonl(tmp_path / "rows.jsonl", _rows())
    out_path = tmp_path / "stress.jsonl"
    summary_path = tmp_path / "summary.json"

    assert main(
        [
            "--input-jsonl",
            str(input_path),
            "--output-jsonl",
            str(out_path),
            "--summary-json",
            str(summary_path),
            "--max-groups",
            "1",
        ]
    ) == 0

    stress_rows = [
        json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()
    ]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert len(stress_rows) == 3
    assert summary["schema_version"] == "offline_reward_oracle_stress_rows.v1"

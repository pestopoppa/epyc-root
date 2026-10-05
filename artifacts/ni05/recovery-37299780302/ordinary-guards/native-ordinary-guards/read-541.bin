"""Tests for building offline reward-oracle row files."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.build_offline_reward_oracle_rows import (
    build_rows,
    load_candidate_keys,
    main,
)


def _write_seed_file(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "math",
                        "question_id": "q1",
                        "expected": "4",
                        "role_results": {
                            "frontdoor:direct": {
                                "role": "frontdoor",
                                "answer": "4",
                                "passed": True,
                            },
                            "worker_general:direct": {
                                "role": "worker_general",
                                "answer": "5",
                                "passed": False,
                            },
                            "empty:direct": {
                                "role": "frontdoor",
                                "answer": "",
                                "passed": False,
                            },
                        },
                        "rewards": {
                            "frontdoor:direct": 1.0,
                            "worker_general:direct": 0.0,
                        },
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def test_build_rows_extracts_reference_response_and_rewards(tmp_path: Path) -> None:
    seed_file = _write_seed_file(tmp_path / "seed.json")

    rows, summary = build_rows([seed_file], oracle_score_mode="omit")

    assert len(rows) == 2
    assert summary["rows"] == 2
    assert summary["oracle_score_mode"] == "omit"
    assert summary["stats"]["skipped_missing_response"] == 1
    assert rows[0]["reference"] == "4"
    assert rows[0]["response"] == "4"
    assert rows[0]["binary_reward"] == 1.0
    assert rows[0]["q_reward"] == 1.0
    assert "oracle_score" not in rows[0]
    assert rows[1]["binary_reward"] == 0.0


def test_build_rows_can_emit_baseline_oracle_score_for_smoke(tmp_path: Path) -> None:
    seed_file = _write_seed_file(tmp_path / "seed.json")

    rows, summary = build_rows([seed_file], oracle_score_mode="binary_reward")

    assert summary["oracle_score_mode"] == "binary_reward"
    assert [row["oracle_score"] for row in rows] == [1.0, 0.0]


def test_build_rows_preserves_stress_metadata(tmp_path: Path) -> None:
    seed_file = tmp_path / "stress.json"
    seed_file.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "math",
                        "question_id": "q1",
                        "expected": "4",
                        "variant_group": "group-a",
                        "variant_type": "base",
                        "confound_source_item_id": "source-a",
                        "role_results": {
                            "frontdoor:direct": {
                                "answer": "4",
                                "passed": True,
                            },
                            "worker_general:direct": {
                                "answer": "5",
                                "passed": False,
                                "variant_type": "confound",
                                "confound_source_item_id": "role-source",
                            },
                        },
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rows, _summary = build_rows([seed_file], oracle_score_mode="omit")

    assert rows[0]["variant_group"] == "group-a"
    assert rows[0]["variant_type"] == "base"
    assert rows[0]["confound_source_item_id"] == "source-a"
    assert rows[1]["variant_group"] == "group-a"
    assert rows[1]["variant_type"] == "confound"
    assert rows[1]["confound_source_item_id"] == "role-source"


def test_cli_writes_rows_and_summary(tmp_path: Path) -> None:
    seed_file = _write_seed_file(tmp_path / "seed.json")
    rows_path = tmp_path / "rows.jsonl"
    summary_path = tmp_path / "summary.json"

    assert main(
        [
            "--input",
            str(seed_file),
            "--output-jsonl",
            str(rows_path),
            "--summary-json",
            str(summary_path),
            "--oracle-score-mode",
            "q_reward",
        ]
    ) == 0

    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert len(rows) == 2
    assert rows[0]["oracle_score"] == 1.0
    assert summary["suite_counts"] == {"math": 2}


def test_candidate_manifest_filters_exact_source_offset_role(tmp_path: Path) -> None:
    seed_file = _write_seed_file(tmp_path / "seed.json")
    candidate_path = tmp_path / "candidates.jsonl"
    candidate_path.write_text(
        json.dumps(
            {
                "source_path": str(seed_file),
                "source_record_offset": 0,
                "role_key": "worker_general:direct",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    rows, summary = build_rows(
        [seed_file],
        candidate_keys=load_candidate_keys(candidate_path),
    )

    assert len(rows) == 1
    assert rows[0]["role_key"] == "worker_general:direct"
    assert rows[0]["source_record_offset"] == 0
    assert summary["candidate_filter"] == {
        "enabled": True,
        "candidate_rows": 1,
        "matched_candidate_rows": 1,
        "missing_candidate_rows": 0,
    }
    assert summary["stats"]["skipped_not_candidate"] == 2

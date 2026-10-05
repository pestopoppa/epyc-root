"""Tests for offline reward feature-input manifests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.build_offline_reward_feature_manifest import (
    FEATURE_ROW_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
    build_feature_manifest,
    main,
)


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _source(path: Path) -> Path:
    return _write_json(
        path,
        [
            {
                "suite": "math",
                "question_id": "q1",
                "prompt": "What is 2+2?",
                "expected": "4",
                "role_results": {
                    "frontdoor": {
                        "role": "frontdoor",
                        "answer": "4",
                        "passed": True,
                        "elapsed_seconds": 1.5,
                        "error": None,
                    },
                },
                "rewards": {"frontdoor": 1.0},
            },
        ],
    )


def _labels(path: Path, source_path: Path) -> Path:
    return _write_jsonl(
        path,
        [
            {
                "schema_version": "offline_reward_oracle_label.v1",
                "item_id": "source:0:frontdoor",
                "question_id": "q1",
                "suite": "math",
                "role_key": "frontdoor",
                "source_path": str(source_path),
                "source_record_index": 0,
                "oracle_binary_label": 1,
                "oracle_score": 1.0,
                "oracle_threshold": 0.86,
                "oracle_score_source": "reference_token_coverage",
                "target_binary_label": 1,
                "target_source": "answer_equivalence_final_label",
                "label_source": "reference_token_coverage@0.86",
                "label_status": "oracle_labeled",
            },
        ],
    )


def test_build_feature_manifest_validates_join_and_strips_text(tmp_path: Path) -> None:
    source_path = _source(tmp_path / "source.json")
    labels_path = _labels(tmp_path / "labels.jsonl", source_path)

    rows, summary = build_feature_manifest(labels_path)

    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert summary["rows"] == 1
    assert summary["unique_source_records"] == 1
    assert summary["feature_contract"]["embedding_dim_required"] == 1024
    assert rows[0]["schema_version"] == FEATURE_ROW_SCHEMA_VERSION
    assert rows[0]["source_passed"] is True
    assert rows[0]["source_record_index"] == 0
    assert rows[0]["source_record_offset"] == 0
    assert rows[0]["source_record_index_base"] == "zero_based"
    assert rows[0]["feature_context"]["task_type"] == "general"
    assert rows[0]["feature_context"]["source_family"] == "other"
    assert rows[0]["feature_context"]["source_family_onehot"] == [0.0, 0.0, 0.0, 1.0]
    assert rows[0]["prompt_chars"] == len("What is 2+2?")
    assert "prompt" not in rows[0]
    assert "answer" not in rows[0]
    assert "expected" not in rows[0]


def test_build_feature_manifest_resolves_one_based_source_indices(tmp_path: Path) -> None:
    source_path = _write_json(
        tmp_path / "source.json",
        [
            {
                "suite": "thinking",
                "question_id": "q1",
                "prompt": "first",
                "expected": "first expected",
                "role_results": {
                    "frontdoor": {"answer": "first answer", "passed": True}
                },
            },
            {
                "suite": "thinking",
                "question_id": "q2",
                "prompt": "second",
                "expected": "second expected",
                "role_results": {
                    "frontdoor": {"answer": "second answer", "passed": False}
                },
            },
        ],
    )
    labels_path = _write_jsonl(
        tmp_path / "labels.jsonl",
        [
            {
                "schema_version": "offline_reward_oracle_label.v1",
                "item_id": "source:1:frontdoor",
                "question_id": "q1",
                "suite": "thinking",
                "role_key": "frontdoor",
                "source_path": str(source_path),
                "source_record_index": 1,
                "oracle_binary_label": 1,
                "oracle_score": 1.0,
                "oracle_threshold": 0.86,
                "oracle_score_source": "reference_token_coverage",
                "target_binary_label": 1,
                "target_source": "answer_equivalence_final_label",
                "label_source": "reference_token_coverage@0.86",
                "label_status": "oracle_labeled",
            },
        ],
    )

    rows, summary = build_feature_manifest(labels_path)

    assert summary["unique_source_records"] == 1
    assert summary["feature_contract"]["engineered_feature_dim"] == 11
    assert "source_family_onehot[4]" in summary["feature_contract"]["engineered_features"]
    assert rows[0]["source_record_index"] == 1
    assert rows[0]["source_record_offset"] == 0
    assert rows[0]["source_record_index_base"] == "one_based"
    assert rows[0]["prompt_sha256"] != rows[0]["answer_sha256"]


def test_cli_writes_manifest_summary_and_markdown(tmp_path: Path) -> None:
    source_path = _source(tmp_path / "source.json")
    labels_path = _labels(tmp_path / "labels.jsonl", source_path)
    manifest_path = tmp_path / "feature_manifest.jsonl"
    summary_path = tmp_path / "summary.json"
    md_path = tmp_path / "summary.md"

    assert main(
        [
            "--labels-jsonl",
            str(labels_path),
            "--manifest-jsonl",
            str(manifest_path),
            "--summary-json",
            str(summary_path),
            "--summary-md",
            str(md_path),
        ]
    ) == 0

    assert manifest_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["rows"] == 1
    assert md_path.exists()


def test_rejects_missing_role_result_without_outputs(tmp_path: Path) -> None:
    source_path = _write_json(
        tmp_path / "source.json",
        [{"question_id": "q1", "prompt": "x", "role_results": {}}],
    )
    labels_path = _labels(tmp_path / "labels.jsonl", source_path)
    manifest_path = tmp_path / "feature_manifest.jsonl"
    summary_path = tmp_path / "summary.json"

    assert main(
        [
            "--labels-jsonl",
            str(labels_path),
            "--manifest-jsonl",
            str(manifest_path),
            "--summary-json",
            str(summary_path),
        ]
    ) == 2
    assert not manifest_path.exists()
    assert not summary_path.exists()

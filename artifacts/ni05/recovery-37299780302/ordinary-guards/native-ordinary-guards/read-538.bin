"""Tests for offline reward-oracle label export."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.export_offline_reward_oracle_labels import (
    LABEL_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
    export_labels,
    main,
)


def _manifest(rows: int = 2, status: str = "adoptable_offline_oracle") -> dict:
    return {
        "schema_version": "offline_reward_oracle_adoption_manifest.v1",
        "status": status,
        "oracle": {
            "model_id": "deterministic/reference-token-coverage-v1",
            "oracle_score_source": "reference_token_coverage",
            "oracle_threshold": 0.86,
        },
        "evidence": {"rows": rows},
    }


def _rows() -> list[dict]:
    return [
        {
            "item_id": "a",
            "question_id": "q1",
            "suite": "math",
            "role_key": "frontdoor",
            "source_path": "/tmp/source.json",
            "source_record_index": 1,
            "target_source": "answer_equivalence_final_label",
            "oracle_model_id": "deterministic/reference-token-coverage-v1",
            "oracle_score_source": "reference_token_coverage",
            "oracle_score": 0.9,
            "target_score": 1.0,
            "binary_reward": 1.0,
            "reference": "private",
            "response": "private",
        },
        {
            "item_id": "b",
            "question_id": "q2",
            "suite": "math",
            "role_key": "worker_general",
            "target_source": "answer_equivalence_final_label",
            "oracle_model_id": "deterministic/reference-token-coverage-v1",
            "oracle_score_source": "reference_token_coverage",
            "oracle_score": 0.2,
            "target_score": 0.0,
            "binary_reward": 0.0,
            "prompt": "private",
            "answer": "private",
        },
    ]


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_export_labels_requires_adoptable_manifest_and_strips_private_fields(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    rows_path = tmp_path / "rows.jsonl"
    _write_json(manifest_path, _manifest())
    _write_jsonl(rows_path, _rows())

    labels, summary = export_labels(
        manifest_path=manifest_path,
        scored_rows_path=rows_path,
    )

    assert [row["schema_version"] for row in labels] == [
        LABEL_SCHEMA_VERSION,
        LABEL_SCHEMA_VERSION,
    ]
    assert [row["oracle_binary_label"] for row in labels] == [1, 0]
    assert labels[0]["label_source"] == "reference_token_coverage@0.86"
    assert labels[0]["oracle_matches_target"] is True
    assert not {"prompt", "reference", "response", "answer"} & set(labels[0])
    assert not {"prompt", "reference", "response", "answer"} & set(labels[1])
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert summary["rows"] == 2
    assert summary["target_agreement"] == 1.0


def test_cli_writes_labels_summary_and_markdown(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", _manifest())
    rows_path = _write_jsonl(tmp_path / "rows.jsonl", _rows())
    labels_path = tmp_path / "labels.jsonl"
    summary_path = tmp_path / "summary.json"
    md_path = tmp_path / "summary.md"

    assert main(
        [
            "--manifest-json",
            str(manifest_path),
            "--scored-rows-jsonl",
            str(rows_path),
            "--labels-jsonl",
            str(labels_path),
            "--summary-json",
            str(summary_path),
            "--summary-md",
            str(md_path),
        ]
    ) == 0

    assert labels_path.exists()
    assert summary_path.exists()
    assert md_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["rows"] == 2


def test_cli_rejects_blocked_manifest_without_outputs(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", _manifest(status="blocked"))
    rows_path = _write_jsonl(tmp_path / "rows.jsonl", _rows())
    labels_path = tmp_path / "labels.jsonl"
    summary_path = tmp_path / "summary.json"

    assert main(
        [
            "--manifest-json",
            str(manifest_path),
            "--scored-rows-jsonl",
            str(rows_path),
            "--labels-jsonl",
            str(labels_path),
            "--summary-json",
            str(summary_path),
        ]
    ) == 2
    assert not labels_path.exists()
    assert not summary_path.exists()


def test_export_rejects_row_count_and_oracle_identity_mismatch(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", _manifest(rows=3))
    rows_path = _write_jsonl(tmp_path / "rows.jsonl", _rows())

    try:
        export_labels(manifest_path=manifest_path, scored_rows_path=rows_path)
    except ValueError as exc:
        assert "row-count mismatch" in str(exc)
    else:
        raise AssertionError("expected row-count mismatch")

    manifest_path = _write_json(tmp_path / "manifest.json", _manifest())
    rows = _rows()
    rows[0]["oracle_model_id"] = "wrong"
    rows_path = _write_jsonl(tmp_path / "rows.jsonl", rows)

    try:
        export_labels(manifest_path=manifest_path, scored_rows_path=rows_path)
    except ValueError as exc:
        assert "oracle_model_id mismatch" in str(exc)
    else:
        raise AssertionError("expected oracle identity mismatch")

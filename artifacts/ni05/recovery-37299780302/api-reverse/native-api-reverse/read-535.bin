"""Tests for offline reward expansion label export."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.export_offline_reward_expansion_labels import (
    EXPANSION_TARGET_SOURCE,
    export_expansion_labels,
    main,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _manifest() -> dict:
    return {
        "schema_version": "offline_reward_oracle_adoption_manifest.v1",
        "status": "adoptable_offline_oracle",
        "oracle": {
            "model_id": "deterministic/reference-token-coverage-v1",
            "oracle_score_source": "reference_token_coverage",
            "oracle_threshold": 0.86,
        },
        "evidence": {"rows": 322},
    }


def _candidate() -> dict:
    return {
        "schema_version": "offline_reward_verifier_expansion_candidate.v1",
        "candidate_id": "source:1:architect_general_delegated",
        "source_path": "/tmp/source.jsonl",
        "source_record_offset": 0,
        "role_key": "architect_general:delegated",
    }


def _scored_row() -> dict:
    return {
        "item_id": "source:1:architect_general_delegated",
        "source_path": "/tmp/source.jsonl",
        "source_record_index": 1,
        "source_record_offset": 0,
        "question_id": "q1",
        "suite": "architecture",
        "role_key": "architect_general:delegated",
        "oracle_model_id": "deterministic/reference-token-coverage-v1",
        "oracle_score_source": "reference_token_coverage",
        "oracle_score": 0.9,
        "binary_reward": 1.0,
        "reference": "private",
        "response": "private",
    }


def test_export_expansion_labels_matches_candidates_and_strips_private_text(
    tmp_path: Path,
) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", _manifest())
    candidates_path = _write_jsonl(tmp_path / "candidates.jsonl", [_candidate()])
    scored_path = _write_jsonl(tmp_path / "scored.jsonl", [_scored_row()])

    labels, summary = export_expansion_labels(
        manifest_path=manifest_path,
        scored_rows_path=scored_path,
        candidates_path=candidates_path,
    )

    assert len(labels) == 1
    assert labels[0]["oracle_binary_label"] == 1
    assert labels[0]["target_source"] == EXPANSION_TARGET_SOURCE
    assert labels[0]["expansion_candidate_id"] == _candidate()["candidate_id"]
    assert not {"prompt", "reference", "response", "expected", "answer"} & set(labels[0])
    assert summary["rows"] == 1
    assert summary["role_counts"] == {"architect_general:delegated": 1}


def test_cli_writes_expansion_labels(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", _manifest())
    candidates_path = _write_jsonl(tmp_path / "candidates.jsonl", [_candidate()])
    scored_path = _write_jsonl(tmp_path / "scored.jsonl", [_scored_row()])
    labels_path = tmp_path / "labels.jsonl"
    summary_path = tmp_path / "summary.json"
    md_path = tmp_path / "summary.md"

    assert main(
        [
            "--manifest-json",
            str(manifest_path),
            "--scored-rows-jsonl",
            str(scored_path),
            "--candidates-jsonl",
            str(candidates_path),
            "--labels-jsonl",
            str(labels_path),
            "--summary-json",
            str(summary_path),
            "--summary-md",
            str(md_path),
        ]
    ) == 0

    assert labels_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["rows"] == 1
    assert md_path.exists()


def test_export_rejects_missing_candidate_score(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", _manifest())
    candidates_path = _write_jsonl(tmp_path / "candidates.jsonl", [_candidate()])
    scored = _scored_row()
    scored["item_id"] = "other"
    scored_path = _write_jsonl(tmp_path / "scored.jsonl", [scored])

    try:
        export_expansion_labels(
            manifest_path=manifest_path,
            scored_rows_path=scored_path,
            candidates_path=candidates_path,
        )
    except ValueError as exc:
        assert "not in candidates" in str(exc)
    else:
        raise AssertionError("expected candidate mismatch")

"""Tests for offline reward feature manifest combination."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.combine_offline_reward_feature_manifests import main


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _row(join_key: str, *, role: str = "frontdoor", source_family: str = "seeding_eval") -> dict:
    return {
        "schema_version": "offline_reward_feature_input.v1",
        "item_id": join_key,
        "join_key": join_key,
        "question_id": "q1",
        "suite": "general",
        "role_key": role,
        "feature_context": {"source_family": source_family},
        "prompt_sha256": "p",
        "prompt_chars": 10,
        "expected_sha256": "e",
        "expected_chars": 1,
        "answer_sha256": "a",
        "answer_chars": 1,
        "oracle_binary_label": 1,
        "oracle_score": 1.0,
    }


def test_combines_prompt_free_feature_manifests(tmp_path: Path) -> None:
    base = _write_jsonl(tmp_path / "base.jsonl", [_row("a")])
    expansion = _write_jsonl(
        tmp_path / "expansion.jsonl",
        [_row("b", role="architect_general", source_family="orchestrator_live_seed")],
    )
    output = tmp_path / "combined.jsonl"
    summary = tmp_path / "summary.json"
    md = tmp_path / "summary.md"

    assert main(
        [
            "--base-manifest-jsonl",
            str(base),
            "--expansion-manifest-jsonl",
            str(expansion),
            "--manifest-jsonl",
            str(output),
            "--summary-json",
            str(summary),
            "--summary-md",
            str(md),
        ]
    ) == 0

    assert output.read_text(encoding="utf-8").count("\n") == 2
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["rows"] == 2
    assert payload["source_family_counts"] == {
        "orchestrator_live_seed": 1,
        "seeding_eval": 1,
    }
    assert payload["privacy"]["commits_private_text"] is False
    assert md.exists()


def test_rejects_duplicate_join_keys(tmp_path: Path) -> None:
    base = _write_jsonl(tmp_path / "base.jsonl", [_row("a")])
    expansion = _write_jsonl(tmp_path / "expansion.jsonl", [_row("a")])

    assert main(
        [
            "--base-manifest-jsonl",
            str(base),
            "--expansion-manifest-jsonl",
            str(expansion),
            "--manifest-jsonl",
            str(tmp_path / "combined.jsonl"),
            "--summary-json",
            str(tmp_path / "summary.json"),
        ]
    ) == 2


def test_rejects_private_text_fields(tmp_path: Path) -> None:
    base = _write_jsonl(tmp_path / "base.jsonl", [_row("a")])
    private = _row("b")
    private["prompt"] = "do not commit"
    expansion = _write_jsonl(tmp_path / "expansion.jsonl", [private])

    assert main(
        [
            "--base-manifest-jsonl",
            str(base),
            "--expansion-manifest-jsonl",
            str(expansion),
            "--manifest-jsonl",
            str(tmp_path / "combined.jsonl"),
            "--summary-json",
            str(tmp_path / "summary.json"),
        ]
    ) == 2

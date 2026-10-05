from __future__ import annotations

import json
from pathlib import Path

from scripts.datasets.raw_trace_publish_preflight import run


def _jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def test_blocks_known_credential_pattern(tmp_path: Path) -> None:
    candidate = _jsonl(
        tmp_path / "planner.jsonl",
        [{"status": "failed", "message": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456"}],
    )

    report = run([candidate])

    assert report["ok"] is False
    hit = report["paths"][0]["hits"][0]
    assert hit["kind"] == "credential_pattern"
    assert "bearer_token" in hit["categories"]


def test_marks_reasoning_field_hits(tmp_path: Path) -> None:
    candidate = _jsonl(
        tmp_path / "trace.jsonl",
        [{"reasoning": "model thought mentions sk-ant-api03-abcdefghijklmnopqrstuvwxyz"}],
    )

    report = run([candidate])

    assert report["ok"] is False
    assert report["summary"]["reasoning_hit_count"] >= 1
    assert report["paths"][0]["reasoning_fields_scanned"] == 1


def test_high_entropy_token_backstop_blocks_unknown_secret_shape(tmp_path: Path) -> None:
    candidate = _jsonl(
        tmp_path / "unknown.jsonl",
        [{"trace": "opaque token AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/AbCdEf"}],
    )

    report = run([candidate])

    assert report["ok"] is False
    assert any(hit["kind"] == "high_entropy_token" for hit in report["paths"][0]["hits"])


def test_sha_like_fields_are_not_high_entropy_false_positives(tmp_path: Path) -> None:
    candidate = _jsonl(
        tmp_path / "hashes.jsonl",
        [{"prompt_hash": "a" * 64, "answer_sha256": "b" * 64, "message": "normal"}],
    )

    report = run([candidate])

    assert report["ok"] is True
    assert report["summary"]["hit_count"] == 0

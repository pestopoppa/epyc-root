from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.autopilot.recover_multitier_t2_baseline import _read_recovery_batch


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _complete_batch() -> list[dict[str, object]]:
    return [
        {
            "row_type": "batch_start",
            "eval_batch_id": "resume-1",
            "requested_n": 2,
        },
        {
            "row_type": "question_result",
            "eval_batch_id": "resume-1",
            "ordinal": 7,
            "result": {"question_id": "q7", "error": False},
        },
        {
            "row_type": "question_result",
            "eval_batch_id": "resume-1",
            "ordinal": 3,
            "result": {"question_id": "q3", "error": True},
        },
        {
            "row_type": "batch_complete",
            "eval_batch_id": "resume-1",
            "complete": True,
            "completed_n": 2,
            "elapsed_s": 12.5,
        },
    ]


def test_read_recovery_batch_requires_complete_exact_batch(tmp_path: Path) -> None:
    sidecar = tmp_path / "rows.jsonl"
    _write_rows(sidecar, _complete_batch())

    rows, marker = _read_recovery_batch(sidecar, "resume-1", [3, 7])

    assert [row["ordinal"] for row in rows] == [3, 7]
    assert marker["elapsed_s"] == 12.5


def test_read_recovery_batch_rejects_missing_complete_marker(tmp_path: Path) -> None:
    sidecar = tmp_path / "rows.jsonl"
    _write_rows(sidecar, _complete_batch()[:-1])

    with pytest.raises(RuntimeError, match="exactly one complete marker"):
        _read_recovery_batch(sidecar, "resume-1", [3, 7])


def test_read_recovery_batch_rejects_ordinal_drift(tmp_path: Path) -> None:
    sidecar = tmp_path / "rows.jsonl"
    rows = _complete_batch()
    rows[2]["ordinal"] = 9
    _write_rows(sidecar, rows)

    with pytest.raises(RuntimeError, match=r"missing=\[3\] extra=\[9\]"):
        _read_recovery_batch(sidecar, "resume-1", [3, 7])

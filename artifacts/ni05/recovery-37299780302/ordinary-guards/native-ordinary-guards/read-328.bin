"""Per-question sidecar rows carry wall-clock timing (2026-07-22).

Verifying EV-4b's fan-out required /proc forensics because question_results
rows carried no timing. append_result now stamps ended_at_s (append wall
clock ~= request end), elapsed_s, and derived started_at_s so end-to-end
concurrency depth and latency distributions are computable from the artifact.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = REPO_ROOT / "scripts" / "autopilot"
for path in (REPO_ROOT, AUTOPILOT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import eval_tower  # noqa: E402


def _writer(tmp_path: Path) -> "eval_tower._EvalQuestionJsonlWriter":
    return eval_tower._EvalQuestionJsonlWriter(
        root=tmp_path,
        root_source="test",
        eval_batch_id="batch-test",
        trial_id=None,
        label="timing-test",
        requested_n=2,
        concurrency=4,
    )


def _rows(writer: "eval_tower._EvalQuestionJsonlWriter") -> list[dict]:
    return [json.loads(line) for line in writer.path.read_text().splitlines()]


def test_append_result_stamps_interval_fields(tmp_path: Path) -> None:
    w = _writer(tmp_path)
    try:
        result = eval_tower.QuestionResult(
            question_id="q1",
            suite="s",
            prompt="p",
            expected="e",
            correct=True,
            elapsed_s=2.5,
        )
        before = time.time()
        w.append_result(ordinal=1, result=result)
        after = time.time()
    finally:
        w.close()
    row = [r for r in _rows(w) if r.get("row_type") == "question_result"][0]
    assert row["elapsed_s"] == 2.5
    assert before - 0.001 <= row["ended_at_s"] <= after + 0.001
    assert abs((row["ended_at_s"] - row["started_at_s"]) - 2.5) < 0.01


def test_append_result_zero_elapsed_has_null_start(tmp_path: Path) -> None:
    w = _writer(tmp_path)
    try:
        result = eval_tower.QuestionResult(
            question_id="q2", suite="s", prompt="p", expected="e"
        )
        w.append_result(ordinal=2, result=result)
    finally:
        w.close()
    row = [r for r in _rows(w) if r.get("row_type") == "question_result"][0]
    assert row["elapsed_s"] == 0.0
    assert row["started_at_s"] is None
    assert row["ended_at_s"] > 0

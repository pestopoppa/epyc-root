"""Incremental EvalTower question-result sidecar persistence."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import eval_tower  # noqa: E402
from eval_tower import EvalTower, QuestionResult  # noqa: E402


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _sidecar_path(root: Path, trial_id: int) -> Path:
    return root / f"trial_{trial_id}" / "question_results.jsonl"


def test_eval_batch_persists_serial_question_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTOPILOT_EVAL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "1")
    tower = EvalTower()
    tower.set_trial_context(101)

    def fake_eval_question(q: dict, client: object) -> QuestionResult:
        return QuestionResult(
            question_id=str(q["id"]),
            suite="unit",
            prompt="SECRET_PROMPT",
            expected="SECRET_EXPECTED",
            answer="SECRET_RAW_ANSWER",
            correct=bool(q["correct"]),
            tokens_generated=7,
            elapsed_s=0.25,
        )

    monkeypatch.setattr(tower, "_eval_question", fake_eval_question)

    tower._eval_batch(
        [{"id": "q1", "correct": True}, {"id": "q2", "correct": False}],
        client=object(),  # type: ignore[arg-type]
        label="T1",
    )

    rows = _read_rows(_sidecar_path(tmp_path, 101))
    question_rows = [row for row in rows if row["row_type"] == "question_result"]
    assert [row["ordinal"] for row in question_rows] == [0, 1]
    assert {row["trial_id"] for row in question_rows} == {101}
    assert {row["label"] for row in question_rows} == {"T1"}
    assert {row["requested_n"] for row in question_rows} == {2}
    assert len({row["eval_batch_id"] for row in question_rows}) == 1
    assert question_rows[0]["result"]["question_id"] == "q1"
    assert question_rows[0]["result"]["correct"] is True
    assert question_rows[1]["result"]["correct"] is False


def test_eval_batch_persists_concurrent_question_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTOPILOT_EVAL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "3")
    tower = EvalTower()
    tower.set_trial_context(202)

    # workers>1 drives the pipelined generation/scoring pools, so the fake
    # replaces the GENERATION phase and hands scoring a ready ``final_result``.
    def fake_generate(q: dict, client: object) -> "eval_tower._GenOutcome":
        time.sleep(float(q.get("delay", 0.0)))
        return eval_tower._GenOutcome(
            gen_ended_at_s=time.time(),
            final_result=QuestionResult(
                question_id=str(q["id"]),
                suite="unit",
                prompt=str(q["id"]),
                expected="ok",
                answer="ok",
                correct=True,
            ),
        )

    monkeypatch.setattr(tower, "_generate_question", fake_generate)

    tower._eval_batch(
        [
            {"id": "q1", "delay": 0.02},
            {"id": "q2", "delay": 0.0},
            {"id": "q3", "delay": 0.01},
        ],
        client=object(),  # type: ignore[arg-type]
        label="T2",
    )

    rows = _read_rows(_sidecar_path(tmp_path, 202))
    question_rows = [row for row in rows if row["row_type"] == "question_result"]
    assert sorted(row["ordinal"] for row in question_rows) == [0, 1, 2]
    assert {row["result"]["question_id"] for row in question_rows} == {"q1", "q2", "q3"}
    assert len({row["eval_batch_id"] for row in question_rows}) == 1


def test_eval_batch_sidecar_persists_answer_but_not_prompt_or_expected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    # 2026-07-22 operator directive: the JSONL sidecar now persists the FULL raw
    # answer at the row level so arms are re-scorable/resumable from the artifact
    # alone. `prompt`/`expected` stay excluded (reconstructable from the dataset),
    # and the COMPACT `result` block is unchanged (answer_hash only).
    monkeypatch.setenv("AUTOPILOT_EVAL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "1")
    tower = EvalTower()
    tower.set_trial_context(303)

    def fake_eval_question(q: dict, client: object) -> QuestionResult:
        return QuestionResult(
            question_id="q-secret",
            suite="unit",
            prompt="DO_NOT_WRITE_PROMPT",
            expected="DO_NOT_WRITE_EXPECTED",
            answer="PERSIST_THIS_ANSWER",
            correct=True,
        )

    monkeypatch.setattr(tower, "_eval_question", fake_eval_question)

    tower._eval_batch([{"id": "q-secret"}], client=object(), label="leak")  # type: ignore[arg-type]

    text = _sidecar_path(tmp_path, 303).read_text(encoding="utf-8")
    assert "DO_NOT_WRITE_PROMPT" not in text
    assert "DO_NOT_WRITE_EXPECTED" not in text
    # Raw answer IS persisted now (row-level), for re-scoring / resume.
    assert "PERSIST_THIS_ANSWER" in text
    row = [r for r in _read_rows(_sidecar_path(tmp_path, 303)) if r["row_type"] == "question_result"][0]
    assert row["answer"] == "PERSIST_THIS_ANSWER"
    # The compact result block stays compact — answer_hash only, no raw fields.
    assert "answer_hash" in row["result"]
    assert "prompt" not in row["result"]
    assert "expected" not in row["result"]
    assert "answer" not in row["result"]


def test_eval_batch_writes_complete_marker_on_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTOPILOT_EVAL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "1")
    tower = EvalTower()
    tower.set_trial_context(404)

    def fake_eval_question(q: dict, client: object) -> QuestionResult:
        return QuestionResult(
            question_id=str(q["id"]),
            suite="unit",
            prompt=str(q["id"]),
            expected="ok",
            answer="ok",
            correct=True,
        )

    monkeypatch.setattr(tower, "_eval_question", fake_eval_question)

    tower._eval_batch([{"id": "q1"}, {"id": "q2"}], client=object(), label="complete")  # type: ignore[arg-type]

    rows = _read_rows(_sidecar_path(tmp_path, 404))
    assert rows[0]["row_type"] == "batch_start"
    assert rows[-1]["row_type"] == "batch_complete"
    assert rows[-1]["complete"] is True
    assert rows[-1]["completed_n"] == 2
    assert rows[-1]["recovery_contract"] == "complete_marker_required"

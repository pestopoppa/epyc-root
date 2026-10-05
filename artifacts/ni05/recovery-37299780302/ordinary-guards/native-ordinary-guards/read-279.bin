"""Focused contract tests for the one-use E8 mixed-tail c1 bridge."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/benchmark/prepare_e8_quality_baseline_v5_partial_r2_mixed_tail_c1_successor.py"
SPEC = importlib.util.spec_from_file_location("e8_mixed_tail_c1_successor_test", PATH)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_reviewed_sets_are_disjoint_and_leave_only_original_races() -> None:
    assert set(RUNNER.IMPORTED_CLEAN).isdisjoint(RUNNER.C1_RETRY)
    assert set(RUNNER.IMPORTED_CLEAN).isdisjoint(RUNNER.RACE_RETRY)
    assert set(RUNNER.C1_RETRY).isdisjoint(RUNNER.RACE_RETRY)
    assert RUNNER.RACE_RETRY == (97, 203, 279)


def test_workspace_contract_requires_exact_reviewed_cluster(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace.jsonl"
    workspace.write_text("fixture\n")
    expected = set(RUNNER.IMPORTED_CLEAN) | set(RUNNER.C1_RETRY)
    rows = {ordinal: (index, {"ordinal": ordinal}) for index, ordinal in enumerate(sorted(expected))}
    monkeypatch.setattr(RUNNER.MIXED, "_rows_with_bytes", lambda _path: ([b"fixture\n"], rows))
    monkeypatch.setattr(RUNNER.RECOVERY, "_response_from_sidecar", lambda row, question: {"qid": question["qid"]})
    monkeypatch.setattr(RUNNER.V5, "validate_clean_sidecar_result", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(RUNNER.MIXED, "_classify", lambda *_args, **_kwargs: "timeout")

    _lines, accepted = RUNNER._workspace_rows(workspace, [{"qid": str(i)} for i in range(RUNNER.N)])

    assert set(accepted) == expected
    rows.pop(next(iter(rows)))
    with pytest.raises(ValueError, match="ordinal set"):
        RUNNER._workspace_rows(workspace, [{"qid": str(i)} for i in range(RUNNER.N)])


def test_schedule_binds_c1_without_relabeling_c3(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace.jsonl"
    journal = tmp_path / "recovery_rows.T2.r2.jsonl"
    workspace.write_text("workspace\n")
    journal.write_text("journal\n")
    state = {
        "source_hashes": {"immutable": "0" * 64},
        "workspace": workspace,
        "watcher": {"sha256": "1" * 64},
        "source": tmp_path,
        "banked_clean_reference": {"sha256": "2" * 64, "generation_concurrency": 3},
    }

    schedule = RUNNER._schedule(state, SimpleNamespace(api_url="http://127.0.0.1:8000/"))

    assert schedule["canonical_c3_claim_unchanged"] is True
    assert schedule["frozen_source"]["banked_clean_reference"]["generation_concurrency"] == 3
    assert schedule["amendment"] == {
        "kind": "tail_scheduling_only",
        "concurrency": 1,
        "request_timeout_s": 300,
        "max_retries_per_target": 1,
        "sequential": True,
        "targets": list(RUNNER.C1_RETRY),
        "target_sha256": RUNNER.canonical_hash(list(RUNNER.C1_RETRY)),
    }
    assert schedule["frozen_source"]["workspace_sidecar"]["sha256"] == RUNNER.sha256_path(workspace)
    assert schedule["frozen_source"]["journal"]["sha256"] == RUNNER.sha256_path(journal)


def test_c1_environment_restores_callers_c3_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    @contextmanager
    def fake_focused(_sidecar_dir: Path, _api_url: str):
        before = os.environ.get("AUTOPILOT_EVAL_CONCURRENCY")
        os.environ["AUTOPILOT_EVAL_CONCURRENCY"] = "1"
        try:
            yield
        finally:
            if before is None:
                os.environ.pop("AUTOPILOT_EVAL_CONCURRENCY", None)
            else:
                os.environ["AUTOPILOT_EVAL_CONCURRENCY"] = before

    monkeypatch.setattr(RUNNER.V5, "focused_environment", fake_focused)
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "3")

    with RUNNER._c1_environment(tmp_path, "http://127.0.0.1:8000"):
        assert os.environ["AUTOPILOT_EVAL_CONCURRENCY"] == "1"
    assert os.environ["AUTOPILOT_EVAL_CONCURRENCY"] == "3"


def test_focused_sidecar_path_uses_real_eval_tower_explicit_artifact_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise EvalTower's writer, not a runner-invented filename convention."""
    sidecar_dir = tmp_path / "sidecars"
    label = "e8-mixed-c1-tail-t2-r2-o138"
    qid = "needle_32768_0.75"
    tower = RUNNER.V4.EvalTower(url="http://127.0.0.1:8000", timeout=1)
    tower.set_question_artifact_dir(sidecar_dir)
    eval_tower = sys.modules[RUNNER.V4.EvalTower.__module__]

    result = eval_tower.QuestionResult(
        question_id=qid,
        qid=qid,
        suite="needle_parameterized",
        prompt="sealed prompt",
        expected="needle",
        answer="needle",
        correct=True,
        route_used="frontdoor",
        tokens_generated=1,
        elapsed_s=0.01,
    )
    monkeypatch.setattr(tower, "_eval_question", lambda _question, _client: result)
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "1")

    [actual] = tower._eval_batch(
        [{"id": qid, "qid": qid, "_ordinal": 138, "suite": "needle_parameterized"}],
        object(),
        label=label,
    )

    path = RUNNER._focused_sidecar_path(sidecar_dir, label=label)
    assert path.parent == sidecar_dir
    assert path.name == f"question_results.{label}.jsonl"
    rows = RUNNER.V4.load_jsonl(path)
    assert len([row for row in rows if row.get("row_type") == "batch_complete" and row.get("complete") is True]) == 1
    _line, row = RUNNER._focused_sidecar_row(path, ordinal=138)
    recorded = row["result"]
    assert actual.question_id == qid
    assert recorded["qid"] == qid
    assert recorded["question_id"] == qid

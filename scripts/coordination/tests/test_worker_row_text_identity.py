"""A dispatch screens the queued task text, never a paraphrase or truncation."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import pytest

if __name__ == "__main__":
    raise SystemExit(
        "REFUSING: pytest suite; run: python -m pytest "
        "scripts/coordination/tests/test_worker_row_text_identity.py -q"
    )

from scripts.coordination import session_bus_coordinator as coordinator
from scripts.coordination import worker_runner


def _args(tmp_path: Path, text: str) -> argparse.Namespace:
    return argparse.Namespace(
        assignment=None,
        bus_root=str(tmp_path),
        task_id="T-identity",
        row_text=text,
        row_ref=None,
        source_handoff="handoffs/active/fixture.md",
        screened_by=None,
    )


def test_manual_text_must_equal_resolved_queue_row(tmp_path, monkeypatch):
    original = "Original task TEXT: preserve all 452 characters exactly."
    monkeypatch.setattr(worker_runner.session_bus, "fold_queue", lambda _bus: {
        "T-identity": {"task_id": "T-identity", "task_text": original},
    })
    assert worker_runner.load_assignment(_args(tmp_path, original))["rows"][0]["task_text"] == original
    with pytest.raises(worker_runner.RefusalError, match="verbatim task_text"):
        worker_runner.load_assignment(_args(tmp_path, "short paraphrase"))


def test_manual_text_without_queued_task_keeps_explicit_idiom(tmp_path, monkeypatch):
    monkeypatch.setattr(worker_runner.session_bus, "fold_queue", lambda _bus: {})
    assert worker_runner.load_assignment(_args(tmp_path, "new manual task"))["rows"][0]["task_text"] == "new manual task"


def test_assignment_file_checks_each_resolved_row_and_keeps_unresolved(tmp_path, monkeypatch):
    original = "The exact queued task text, including its final words."
    observed_bus_roots = []

    def isolated_fold(bus_root):
        observed_bus_roots.append(bus_root)
        return {"T-identity": {"task_id": "T-identity", "task_text": original}}

    monkeypatch.setattr(worker_runner.session_bus, "fold_queue", isolated_fold)
    assignment = tmp_path / "assignment.json"
    rows = [
        {"task_id": "T-identity", "task_text": original},
        {"task_id": "T-new", "task_text": "unresolved manual assignment"},
    ]
    assignment.write_text(json.dumps({"rows": rows}))
    args = _args(tmp_path, "ignored because assignment file wins")
    args.assignment = str(assignment)
    assert worker_runner.load_assignment(args)["rows"] == rows

    rows[0]["task_text"] = "a paraphrase"
    assignment.write_text(json.dumps({"rows": rows}))
    with pytest.raises(worker_runner.RefusalError, match="verbatim task_text"):
        worker_runner.load_assignment(args)
    assert observed_bus_roots == [tmp_path, tmp_path]


def test_direct_file_reader_without_bus_root_keeps_legacy_contract(tmp_path, monkeypatch):
    assignment = tmp_path / "assignment.json"
    rows = [{"task_id": "T-identity", "task_text": "file-only reader"}]
    assignment.write_text(json.dumps({"rows": rows}))

    def no_live_bus(_bus_root):
        raise AssertionError("direct file reader must not consult a live bus")

    monkeypatch.setattr(worker_runner.session_bus, "fold_queue", no_live_bus)
    assert worker_runner.load_assignment(argparse.Namespace(assignment=str(assignment)))["rows"] == rows


class _CapturedChild:
    """A stand-in for the spawned runner: records stdin, spawns nothing."""

    def __init__(self) -> None:
        self.stdin = io.BytesIO()
        self.stdin.close = lambda: None  # keep the bytes readable after delivery


def _exec_with_text(tmp_path, monkeypatch, text: str):
    captured: dict[str, object] = {}
    monkeypatch.setattr(coordinator, "_note_spawn_attempt", lambda *_: None)
    monkeypatch.setattr(coordinator, "_free_pool_lane", lambda _config: "lane0")

    def capture_popen(cmd, **_kwargs):
        captured["argv"] = cmd
        captured["child"] = _CapturedChild()
        return captured["child"]

    monkeypatch.setattr(coordinator.subprocess, "Popen", capture_popen)
    # The only file opened by this function is the worker log; keep the test
    # entirely in memory, with no shared log or spawned process.
    monkeypatch.setattr("builtins.open", lambda *_args, **_kwargs: io.BytesIO())
    result = coordinator._exec_worker_runner(
        tmp_path, {}, {"endpoint": "exec:worker_runner"},
        {"task_text": text}, "T-identity", "workerpool", 1,
    )
    return result, captured


def test_coordinator_passes_queued_text_verbatim_on_stdin(tmp_path, monkeypatch):
    """RTG-52: the resolved row travels as exact UTF-8 JSON on stdin, never on argv."""
    full_text = "original row — " + "x" * 3000 + " final words"
    result, captured = _exec_with_text(tmp_path, monkeypatch, full_text)
    assert result[0]["kind"] == "exec-launched"
    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "--assignment-stdin" in argv and "--row-text" not in argv
    delivered = json.loads(captured["child"].stdin.getvalue().decode("utf-8"))
    assert delivered["rows"][0]["task_text"] == full_text


def test_coordinator_refuses_rather_than_clips_an_oversized_assignment(tmp_path, monkeypatch):
    """Over the worker brief cap the row is a defect, never a truncated dispatch."""
    full_text = "original row " + "x" * 4500 + " final words"
    result, captured = _exec_with_text(tmp_path, monkeypatch, full_text)
    assert result[0]["kind"] == "defect"
    assert result[0]["check"] == "exec-runner-assignment-size"
    assert "argv" not in captured

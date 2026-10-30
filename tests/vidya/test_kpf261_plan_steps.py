"""Portable refusal and CLI coverage; full native canary uses the pinned producer capture."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
import cli
from adapters.kpf261_plan_steps import project, validate_plan_binding
from claim_tuple import ProjectionError


def test_synthetic_capture_is_refused_by_cli(tmp_path, capsys):
    (tmp_path / "protocol.json").write_text(json.dumps({
        "schema": "kpf261.real-planner.protocol.v1", "synthetic": True,
    }))
    (tmp_path / "capture-complete.json").write_text(json.dumps({"synthetic": True}))
    rc = cli.main(["--ledger", str(tmp_path / "ledger.jsonl"), "--json", "ingest",
                   "kpf261-plan-steps", "--path", str(tmp_path),
                   "--as-of", "2026-10-30T15:00:00Z"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["frames_emitted"] == 0
    assert "synthetic" in report["refused"][0]["reason"]


def test_malformed_capture_is_a_refusal(tmp_path):
    (tmp_path / "protocol.json").write_text("{")
    with pytest.raises(ProjectionError, match="invalid planner capture"):
        project(tmp_path)


def test_task_and_initial_prompt_bind_to_corpus():
    row = {"original_action": "original", "objective": "goal", "context": {"prior": "x"}}
    context = json.dumps({"objective": "goal", "prior_context": {"prior": "x"}},
                         ensure_ascii=False, sort_keys=True)
    task = {"objective": "original", "context": context}
    build = lambda objective, ctx: objective + ctx
    initial = {"prompt": build("original", context)}
    validate_plan_binding(task, row, initial, build)
    with pytest.raises(ProjectionError, match="task differs"):
        validate_plan_binding({**task, "objective": "substituted"}, row, initial, build)
    with pytest.raises(ProjectionError, match="initial prompt differs"):
        validate_plan_binding(task, row, {"prompt": "substituted"}, build)

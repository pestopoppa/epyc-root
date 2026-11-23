import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import publish_row as publish


def test_lint_refuses_row_with_diagnostics(tmp_path):
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/sh\n")
    (tmp_path / "job.py").write_text("port = 12345\n")
    with pytest.raises(publish.rf.Refused, match="HARDCODED-PORT.*port literal"):
        publish.lint({"id": "example", "launcher": str(launcher)})


def test_lint_uses_submitted_spec_not_neighbor_spec(tmp_path):
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/sh\n")
    (tmp_path / "spec.json").write_text('{"estimate_s": 300}')
    publish.lint({"id": "example", "launcher": str(launcher)})


def test_lint_checks_submitted_estimate(tmp_path):
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/sh\n")
    (tmp_path / "spec.json").write_text('{}')
    with pytest.raises(publish.rf.Refused, match="ESTIMATE-UNMEASURED"):
        publish.lint({"id": "example", "launcher": str(launcher), "estimate_s": 300})


def test_publish_reports_lint_failure_before_queue(tmp_path, monkeypatch, capsys):
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/sh\n")
    (tmp_path / "job.py").write_text("port = 12345\n")
    spec = tmp_path / "request.json"
    spec.write_text(json.dumps({"id": "example", "launcher": str(launcher)}))
    for name in ("_toolroot_banner", "check_operator_gate", "check_owner_roster", "refresh_view", "check_handoff", "check_task_lint"):
        monkeypatch.setattr(publish, name, lambda *a, **kw: None)
    monkeypatch.setattr(publish, "publish_smoked", lambda *a, **kw: pytest.fail("queued a bad row"))
    assert publish.main([str(spec)]) == 2
    assert "REFUSED: row lint: HARDCODED-PORT" in capsys.readouterr().out

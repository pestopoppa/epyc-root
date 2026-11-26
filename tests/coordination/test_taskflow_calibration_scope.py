"""Calibrated reproducers cannot certify or tick the underlying source-fix task."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/coordination"))
from taskflow import verify  # noqa: E402


@pytest.mark.parametrize("legacy", [False, True])
def test_reproducer_contract_and_hold_reach_normal_verification(tmp_path, monkeypatch, legacy):
    path = "tests/unit/test_compat_alias_cold_import.py"

    def git_output(lane, *args):
        if args[0] == "rev-list":
            return "worker-commit\n"
        if "--name-only" in args:
            return path + "\n"
        return "candidate diff"

    monkeypatch.setattr(verify, "_git", git_output)
    monkeypatch.setattr(verify, "run_tests", lambda *args: [])
    monkeypatch.setattr(verify, "_done_when", lambda: SimpleNamespace(check=lambda *args: ("ok", "fixture")))
    checked = []
    monkeypatch.setattr(verify, "_candidate_contract", lambda task_id, *args: checked.append(task_id))
    task = {"id": "LOOP-62", "repo": "epyc-orchestrator", "done_when": "mixed concurrent test is xfail"}
    if legacy:
        task["approach"] = "RE-SCOPED r8 2026-11-22: reproducer only"
    else:
        task["verify_scope"] = verify.REPRODUCER_ONLY

    result = verify.verify(task, tmp_path, "base")

    assert checked == ["LOOP-62"]
    assert result["verdict"] == "verified"
    assert result["hold"] == verify.REPRODUCER_ONLY


def test_full_source_fix_has_full_scope():
    assert verify.verification_scope({"id": "LOOP-62", "approach": "Fix the import finder"}) is None
    assert verify.verification_scope({"id": "other", "approach": "RE-SCOPED r8", "done_when": "xfail"}) is None

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch, schema, verify
from taskflow.harness import local_llm


TARGET = ".taskflow-refs/external/evidence/source.txt"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "base.txt").write_text("base")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    source = tmp_path / "trusted.txt"
    source.write_text("pinned source\n")
    item = {
        "path": str(source),
        "lane_path": TARGET,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    task = {
        "id": "EXTERNAL-REF-TEST",
        "repo": "epyc-root",
        "external_readonly_inputs": [item],
        "outputs": ["result.txt"],
        "forbidden": list(schema.FORBIDDEN),
        "goal": "Document the source.",
        "handoff": "owner.md",
        "budget": dict(schema.DEFAULT_BUDGET),
    }
    monkeypatch.setitem(schema.REPOS, "epyc-root", repo)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "lanes"))
    monkeypatch.setattr(dispatch, "MIN_FREE_GIB", 0)
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "policy")
    return repo, source, task


def completed_lane(task, tmp_path):
    _, lane, base = dispatch.make_lane(task, tmp_path / "out", "taskflow/test")
    (lane / "result.txt").write_text("documented\n")
    assert dispatch.commit_lane(lane, task)
    return lane, base


def test_pinned_source_reaches_worker_and_stays_out_of_diff(packet, tmp_path):
    _, source, task = packet
    lane, base = completed_lane(task, tmp_path)
    staged = lane / TARGET
    assert staged.read_bytes() == source.read_bytes()
    assert staged.stat().st_mode & 0o777 == 0o444
    assert git(lane, "diff", "--name-only", f"{base}..HEAD").splitlines() == ["result.txt"]
    assert TARGET in local_llm.task_suffix(task, {})
    config_path = local_llm.write_config(tmp_path / "worker", "http://invalid/v1", "test", task, lane=lane)
    permissions = json.loads(config_path.read_text())["agent"][local_llm.AGENT]["permission"]
    assert permissions["edit"][".taskflow-refs/external/**"] == "deny"
    assert permissions["edit"][f"{lane}/.taskflow-refs/external/**"] == "deny"
    assert permissions["read"] == "allow"
    result = verify.verify(task, lane, base, reviewer=lambda *_: {"verdict": "done"})
    assert result["verdict"] == "verified"
    assert result["checks"][0] == {"check": "external-inputs", "ok": True, "why": ""}


@pytest.mark.parametrize("violation", ["shape", "hash", "missing", "traversal", "duplicate", "parent", "versioned"])
def test_preflight_refuses_invalid_external_reference(packet, tmp_path, violation):
    repo, source, task = packet
    entry = task["external_readonly_inputs"][0]
    if violation == "shape":
        task["external_readonly_inputs"] = None
    elif violation == "hash":
        source.write_text("changed after packet")
    elif violation == "missing":
        source.unlink()
    elif violation == "traversal":
        entry["lane_path"] = ".taskflow-refs/external/../relative.txt"
    elif violation == "duplicate":
        task["external_readonly_inputs"].append(dict(entry))
    elif violation == "parent":
        task["external_readonly_inputs"].append(dict(entry, lane_path=f"{TARGET}/child"))
    elif violation == "versioned":
        tracked = repo / TARGET
        tracked.parent.mkdir(parents=True)
        tracked.write_text("tracked")
        git(repo, "add", "-f", TARGET)
        git(repo, "commit", "-qm", "reserved directory")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    if violation in {"shape", "traversal", "duplicate", "parent"}:
        assert schema.unsupported(task) is not None
    with pytest.raises(dispatch.LaneRefused, match="external reference preflight|reserved reference directory"):
        dispatch.make_lane(task, tmp_path / "out", "taskflow/refused")
    assert not (tmp_path / "out" / "lane.path").exists()
    assert "taskflow/refused" not in git(repo, "branch", "--list")


@pytest.mark.parametrize("change", ["missing", "content", "writable", "symlink"])
def test_verifier_refuses_changed_copy(packet, tmp_path, change):
    repo, source, task = packet
    lane, base = completed_lane(task, tmp_path)
    staged = lane / TARGET
    if change == "missing":
        staged.unlink()
    elif change == "content":
        staged.chmod(0o644)
        staged.write_text("changed")
        staged.chmod(0o444)
    elif change == "writable":
        staged.chmod(0o644)
    elif change == "symlink":
        source.chmod(0o600)
        staged.unlink()
        staged.symlink_to(source)
    result = verify.verify(task, lane, base, reviewer=lambda *_: pytest.fail("called reviewer after tamper"))
    assert result["verdict"] == "rejected"
    assert result["reason"] == "external-input-changed"
    if change == "symlink":
        assert dispatch.drop_lane(repo, lane)
        assert source.stat().st_mode & 0o777 == 0o600


def test_verifier_rechecks_sources_after_successful_tests(packet, tmp_path, monkeypatch):
    _, _, task = packet
    task["test_cmds"] = ["python3 -c pass"]
    lane, base = completed_lane(task, tmp_path)

    def tampering_test(lane, commands):
        (lane / TARGET).unlink()
        return [{"cmd": cmd, "rc": 0} for cmd in commands]

    monkeypatch.setattr(verify, "run_tests", tampering_test)
    result = verify.verify(task, lane, base, reviewer=lambda *_: pytest.fail("called reviewer after tamper"))
    assert result["reason"] == "external-input-changed"
    assert result["checks"][-1]["check"] == "external-inputs-after-tests"

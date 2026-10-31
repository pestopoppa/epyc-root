"""Dispatch-owned deliverables for the headless mutation probe; no model calls."""
import argparse
import json

import pytest

from scripts.coordination import headless_audit as ha
from scripts.coordination import worker_runner as wr


def test_assignment_to_brief_to_probe_uses_declared_deliverable(tmp_path):
    assignment = tmp_path / "assignment.json"
    assignment.write_text(json.dumps({"rows": [{
        "task_id": "T1", "task_text": "Fix src/widget.py using docs/reference.md",
        "deliverable_paths": ["src/widget.py"],
    }]}))
    loaded = wr.load_assignment(argparse.Namespace(assignment=str(assignment)))
    brief = wr.build_brief(loaded["rows"], batch_id="B", lane="lane0", worktree=tmp_path,
                           report_path=tmp_path / "report.json", cfg=dict(wr.DEFAULTS),
                           lease_expires_ts="t")
    target = ha.choose_probe_target(brief["rows"], {"changed_paths": ["docs/reference.md"]}, tmp_path)
    assert target["target"] == "src/widget.py"
    assert target["derived_from"] == "dispatch_deliverable_paths"
    probe = ha.mutation_probe(tmp_path, {"changed_paths": ["docs/reference.md"]}, target)
    assert probe["passed"] is False and probe["checks"][0]["check"] == "present"


def test_ambiguous_legacy_is_unknown_and_single_target_is_unchanged(tmp_path):
    row = {"task_id": "T", "task_text": "Fix src/widget.py using docs/reference.md"}
    target = ha.choose_probe_target([row], {"changed_paths": ["docs/reference.md"]}, tmp_path)
    assert target["target"] is None
    assert ha.mutation_probe(tmp_path, {}, target)["undetermined"] is True
    row["task_text"] = "Fix src/widget.py"
    assert ha.choose_probe_target([row], {}, tmp_path)["target"] == "src/widget.py"


@pytest.mark.parametrize("paths", [[], None, "src/widget.py", ["src/other.py"],
                                  ["../outside.py"], ["/tmp/outside.py"],
                                  ["src/widget.py", "../outside.py"]])
def test_invalid_declared_deliverable_fails_closed(tmp_path, paths):
    row = {"task_id": "T", "task_text": "Fix src/widget.py; see ../outside.py and /tmp/outside.py",
           "deliverable_paths": paths}
    target = ha.choose_probe_target([row], {}, tmp_path)
    assert target["target"] is None
    assert ha.mutation_probe(tmp_path, {}, target)["undetermined"] is True


def test_symlink_escape_refused_for_any_declared_target(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "escape").symlink_to(outside, target_is_directory=True)
    row = {"task_id": "T", "task_text": "Edit src/widget.py and escape/file.py",
           "deliverable_paths": ["src/widget.py", "escape/file.py"]}
    assert ha.choose_probe_target([row], {}, repo)["target"] is None


def test_malformed_declaration_is_not_dropped_by_brief(tmp_path):
    row = {"task_id": "T", "task_text": "Fix src/widget.py", "deliverable_paths": []}
    brief = wr.build_brief([row], batch_id="B", lane="lane0", worktree=tmp_path,
                           report_path=tmp_path / "report.json", cfg=dict(wr.DEFAULTS),
                           lease_expires_ts="t")
    assert brief["rows"][0]["deliverable_paths"] == []
    assert ha.choose_probe_target(brief["rows"], {}, tmp_path)["target"] is None


def test_explicit_deliverable_passes_real_mutation_probe(tmp_path):
    import subprocess

    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "src/widget.py").write_text("value = 1\n")
    (tmp_path / "docs/reference.md").write_text("reference\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "src/widget.py").write_text("value = 2\n")
    git("add", "src/widget.py")
    git("commit", "-qm", "deliverable")
    facts = ha.git_facts(tmp_path, f"{base}..HEAD")
    row = {"task_id": "T", "task_text": "Fix src/widget.py using docs/reference.md",
           "deliverable_paths": ["src/widget.py"]}
    probe = ha.mutation_probe(tmp_path, facts, ha.choose_probe_target([row], facts, tmp_path))
    assert probe["passed"] is True
    assert [item["check"] for item in probe["checks"]] == [
        "present", "nonempty-net-patch", "revertible"
    ]

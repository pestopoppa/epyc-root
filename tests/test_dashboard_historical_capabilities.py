"""Retained capability evidence is visible without relabelling it a fresh build check."""
import copy
import hashlib
import json
import os
import subprocess

import pytest

from dashboard import loop_status as ls


def git(tree, *args):
    return subprocess.check_output(["git", "-C", str(tree), *args], text=True).strip()


@pytest.fixture
def retained(tmp_path):
    tree = tmp_path / "champion"
    tree.mkdir()
    git(tree, "init", "-q", "-b", "ak/champion/test")
    git(tree, "config", "user.email", "fixture@example.invalid")
    git(tree, "config", "user.name", "Fixture")
    git(tree, "commit", "--allow-empty", "-qm", "original capability")
    original = git(tree, "rev-parse", "HEAD")
    git(tree, "commit", "--allow-empty", "-qm", "fold")
    tip = ls.resolve_champion(tree)
    body = {"schema": ls.CHAMPION_SCHEMA, "champion": {"commit": original},
            "generated_at": "2026-08-30T20:21:39Z",
            "capabilities": [{"name": "Original GPU capability", "evidence": "Original gate record"}]}
    path = tmp_path / (ls.CHAMPION_FILENAME + ".pre-reconcile")
    path.write_text(json.dumps(body))
    return tmp_path, tree, path, body, tip


def test_original_list_reopened_with_exact_source_and_ancestry(retained):
    root, _, path, body, tip = retained
    current = {"champion": {"commit": tip["commit"]}, "effect_fraction": 0.01}
    before = copy.deepcopy(current)
    result = ls._champion_capabilities(current, root=root, champion=tip)
    assert result["known"] and result["historical"]
    assert result["items"] == body["capabilities"]
    assert result["measured_commit"] == body["champion"]["commit"]
    assert result["current_champion"] == tip["commit"]
    assert result["lineage"]["relation"] == ls.REL_ANCESTOR
    assert result["record_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert str(path) in result["source"] and "not a fresh build check" in result["source"]
    assert current == before


@pytest.mark.parametrize("entries", [[], [{"name": "Current", "evidence": "Current gate"}], None, "bad"])
def test_declared_current_array_or_error_is_never_overridden(retained, entries):
    root, _, _, _, tip = retained
    result = ls._champion_capabilities({"capabilities": entries}, root=root, champion=tip)
    assert "historical" not in result
    assert result["known"] is isinstance(entries, list)


@pytest.mark.parametrize("mutation", ["foreign", "undated", "schema", "missing_evidence", "unresolved", "moved"])
def test_unjoined_or_malformed_record_does_not_confer_current_capability(retained, mutation):
    root, tree, path, body, tip = retained
    if mutation == "foreign":
        git(tree, "checkout", "--orphan", "other")
        git(tree, "commit", "--allow-empty", "-qm", "foreign")
        body["champion"]["commit"] = git(tree, "rev-parse", "HEAD")
        git(tree, "checkout", "ak/champion/test")
    elif mutation == "undated":
        body["generated_at"] = "not a timestamp"
    elif mutation == "schema":
        body["schema"] = "unknown"
    elif mutation == "missing_evidence":
        body["capabilities"][0].pop("evidence")
    elif mutation == "unresolved":
        tip["resolved"] = False
    elif mutation == "moved":
        git(tree, "commit", "--allow-empty", "-qm", "new tip after snapshot")
    path.write_text(json.dumps(body))
    assert not ls._champion_capabilities({}, root=root, champion=tip)["known"]


@pytest.mark.parametrize("kind", ["missing", "fifo", "symlink", "oversize"])
def test_bounded_original_record_read_refuses_unsafe_file(retained, kind):
    root, _, path, _, tip = retained
    path.unlink()
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "symlink":
        path.symlink_to(root / "other")
    elif kind == "oversize":
        path.write_bytes(b" " * 262145)
    assert not ls._champion_capabilities({}, root=root, champion=tip)["known"]

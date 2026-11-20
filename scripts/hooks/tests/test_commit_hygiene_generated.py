#!/usr/bin/env python3
"""Rule G of check_commit_hygiene.py: session commits of generated index files warn (D9, warn first)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "check_commit_hygiene.py"
IDX = "handoffs/active/foo-index.md"
MASTER = "handoffs/active/master-handoff-index.md"
STATE = "handoffs/active/.index-state.json"
BASE_MD = "# Foo\n| hand | row |\n<!-- generated:start -->\n| g1 |\n<!-- generated:end -->\n"


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True,
                   capture_output=True)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "r"
    (r / "handoffs/active").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    (r / STATE).write_text("{}\n")
    (r / IDX).write_text(BASE_MD)
    (r / MASTER).write_text("x\n<!-- BEGIN GENERATED index_state -->\na\n<!-- END GENERATED index_state -->\n")
    git(r, "add", "."); git(r, "commit", "-qm", "init")
    (r / ".git" / "FETCH_HEAD").write_text("")
    return r


def run(repo, tmp_path, extra=None):
    log = tmp_path / "warn.jsonl"
    env = {**os.environ, "EPYC_FETCH_MAX_AGE_S": "999999999", "EPYC_GENERATED_WARN_LOG": str(log),
           "TOOLROOT_HUB": str(tmp_path / "nohub"), "EPYC_HYGIENE_EXTRA_SHARED": str(repo), **(extra or {})}
    env.pop("EPYC_INDEX_WRITER", None) if not extra or "EPYC_INDEX_WRITER" not in extra else None
    p = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True, env=env, input=json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": f"git -C {repo} commit -m x"}}))
    rows = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    return p, rows


def test_state_json_warns_and_logs(repo, tmp_path):
    (repo / STATE).write_text('{"a":1}\n'); git(repo, "add", STATE)
    p, rows = run(repo, tmp_path)
    assert p.returncode == 0 and STATE in p.stderr and "hub regenerates" in p.stderr
    assert len(rows) == 1 and rows[0]["files"] == [STATE] and rows[0]["commit"]


def test_hub_writer_env_silent(repo, tmp_path):
    (repo / STATE).write_text('{"a":1}\n'); git(repo, "add", STATE)
    p, rows = run(repo, tmp_path, {"EPYC_INDEX_WRITER": "hub"})
    assert p.returncode == 0 and p.stderr == "" and rows == []


def test_hub_checkout_silent(repo, tmp_path):
    (repo / STATE).write_text('{"a":1}\n'); git(repo, "add", STATE)
    p, rows = run(repo, tmp_path, {"TOOLROOT_HUB": str(repo)})
    assert p.returncode == 0 and p.stderr == "" and rows == []


def test_no_generated_files_silent(repo, tmp_path):
    (repo / "other.txt").write_text("x\n"); git(repo, "add", "other.txt")
    p, rows = run(repo, tmp_path)
    assert p.returncode == 0 and p.stderr == "" and rows == []


def test_generated_block_edit_warns(repo, tmp_path):
    (repo / IDX).write_text(BASE_MD.replace("| g1 |", "| g2 |")); git(repo, "add", IDX)
    p, rows = run(repo, tmp_path)
    assert p.returncode == 0 and IDX in p.stderr and rows[0]["files"] == [IDX]


def test_hand_row_edit_outside_block_silent(repo, tmp_path):
    (repo / IDX).write_text(BASE_MD.replace("| hand | row |", "| hand | row2 |")); git(repo, "add", IDX)
    p, rows = run(repo, tmp_path)
    assert p.returncode == 0 and p.stderr == "" and rows == []


def test_master_generated_block_warns(repo, tmp_path):
    (repo / MASTER).write_text("x\n<!-- BEGIN GENERATED index_state -->\nb\n<!-- END GENERATED index_state -->\n")
    git(repo, "add", MASTER)
    p, _ = run(repo, tmp_path)
    assert MASTER in p.stderr


def test_refuse_mode_blocks(repo, tmp_path):
    (repo / STATE).write_text('{"a":1}\n'); git(repo, "add", STATE)
    p, _ = run(repo, tmp_path, {"EPYC_GENERATED_COMMIT_MODE": "refuse"})
    assert p.returncode == 2 and "BLOCKED" in p.stderr

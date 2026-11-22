"""r8d harness fixes from the r8c CPU canary (FIX-HARNESS, 2026-11-22; docs/design/taskflow-stage1-canary-findings.md r8c)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch  # noqa: E402


def _g(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout


def _repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _g(r, "init", "-q", "-b", "main")
    (r / "a.txt").write_text("a\n")
    _g(r, "add", "a.txt")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return r


# ------------------------------------------------------------------------------- fix 1: lanes on resume
def test_resumed_unit_reclaims_its_leftover_worktree(tmp_path, monkeypatch):
    """r8c TU-GR-1 think / MM-5 think: the rc=75 kill left the lane; the resumed unit must reclaim it."""
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    repo = _repo(tmp_path)
    base_dir = tmp_path / "out" / "t00" / "t00"
    lane = dispatch.lane_root() / __import__("hashlib").sha1(str(base_dir).encode()).hexdigest()[:4]
    lane.parent.mkdir(parents=True)
    base_dir.mkdir(parents=True)
    (base_dir / "lane.path").write_text(str(lane))
    _g(repo, "worktree", "add", "-q", "-b", "taskflow/old/00", str(lane), "HEAD")
    (lane / "wip.txt").write_text("half done\n")                 # killed mid-edit
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "branch": "taskflow/old/00",
                                                "task": "TU-GR-1", "state": "live"}))
    how = dispatch.reclaim_resumed_lane(lane, base_dir, {"key": "TU-GR-1"}, repo)
    assert how == "worktree-remove" and not lane.exists() and not dispatch._meta(lane).exists()
    assert "wip.txt" in _g(repo, "show", "--name-only", "taskflow/old/00")      # WIP kept on its branch


def test_unregistered_leftover_goes_through_guarded_rm(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    repo = _repo(tmp_path)
    fake = tmp_path / "grm.sh"
    trash = tmp_path / "trash"
    trash.mkdir()
    fake.write_text(f'#!/bin/bash\nset -euo pipefail\nmv "$1" {trash}/\n')
    monkeypatch.setenv("GUARDED_RM", str(fake))
    base_dir = tmp_path / "bd"
    base_dir.mkdir()
    lane = tmp_path / "tf" / "abcd"
    lane.mkdir(parents=True)
    (lane / "x").write_text("x")
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "task": "MM-5"}))
    assert dispatch.reclaim_resumed_lane(lane, base_dir, {"key": "MM-5"}, repo) == "guarded_rm"
    assert not lane.exists() and (trash / "abcd" / "x").exists() and not dispatch._meta(lane).exists()


def test_foreign_lane_is_still_refused(tmp_path):
    repo = _repo(tmp_path)
    lane = tmp_path / "tf" / "beef"
    lane.mkdir(parents=True)
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "task": "OTHER"}))
    with pytest.raises(dispatch.LaneRefused):
        dispatch.reclaim_resumed_lane(lane, tmp_path / "bd", {"key": "MM-5"}, repo)
    assert lane.exists()


def test_live_dispatcher_lane_is_not_reclaimed(tmp_path):
    repo = _repo(tmp_path)
    bd = tmp_path / "bd"
    bd.mkdir()
    lane = tmp_path / "tf" / "cafe"
    lane.mkdir(parents=True)
    (bd / "lane.path").write_text(str(lane))
    import os
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "task": "MM-5",
                                                "owner": dispatch._proc_id(os.getpid())}))
    with pytest.raises(dispatch.LaneRefused, match="alive"):
        dispatch.reclaim_resumed_lane(lane, bd, {"key": "MM-5"}, repo)
    assert lane.exists()

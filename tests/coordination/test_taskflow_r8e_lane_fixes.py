"""r8e lane fixes from the r8d CPU canary (2026-11-22): 10/10 units refused 'lane: 16 live lanes >= cap 16' because
14 kept (forensics) lanes and 2 orphaned live lanes from r8b/r8c filled the cap (docs/design/taskflow-stage1-canary-findings.md r8d)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch, stage1_result  # noqa: E402


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


def _lane(repo, root, name, **meta):
    lane = root / name
    _g(repo, "worktree", "add", "-q", "-b", f"taskflow/t/{name}", str(lane), "HEAD")
    d = {"lane": str(lane), "repo": str(repo), "branch": f"taskflow/t/{name}", "created": time.time()}
    d.update(meta)
    dispatch._meta(lane).write_text(json.dumps(d))
    return lane


def _me():
    return dispatch._proc_id(os.getpid())


# ------------------------------------------------------------------------------- fix 1: cap counts living lanes
def test_cap_ignores_kept_and_orphan_lanes(tmp_path, monkeypatch):
    root = tmp_path / "tf"
    root.mkdir()
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(root))
    repo = _repo(tmp_path)
    _lane(repo, root, "k001", state="kept", keep_until=time.time() + 3600)
    _lane(repo, root, "o001", state="live")                         # pre-r8d: no owner -> orphan
    _lane(repo, root, "o002", state="live", owner="1:1")            # recycled / dead pid:starttime
    alive = _lane(repo, root, "l001", state="live", owner=_me())
    assert [Path(m.name) for m in dispatch.live_lanes(root)] == [Path(dispatch._meta(alive).name)]


def test_make_lane_not_refused_by_kept_lanes(tmp_path, monkeypatch):
    root = tmp_path / "tf"
    root.mkdir()
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(root))
    monkeypatch.setattr(dispatch, "MAX_LANES", 2)
    monkeypatch.setenv("FILLER_ID", "row-x")
    repo = _repo(tmp_path)
    monkeypatch.setitem(dispatch.schema.REPOS, "t", repo)
    monkeypatch.setattr(dispatch, "_git", lambda r, *a, check=True: subprocess.run(
        ["git", "-C", str(r), *[("HEAD" if x == "origin/main" else x) for x in a]], capture_output=True, text=True, check=check))
    for n in ("k1", "k2", "k3"):
        _lane(repo, root, n, state="kept", keep_until=time.time() + 3600)
    _, lane, _ = dispatch.make_lane({"repo": "t", "key": "K"}, tmp_path / "bd", "taskflow/new/00")
    meta = json.loads(dispatch._meta(lane).read_text())
    assert meta["row"] == "row-x" and meta["base_dir"] == str(tmp_path / "bd") and meta["owner"] == _me()


def test_sweep_drops_orphans_keeps_living_and_unexpired(tmp_path, monkeypatch):
    root = tmp_path / "tf"
    root.mkdir()
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(root))
    repo = _repo(tmp_path)
    o = _lane(repo, root, "o001", state="live")
    k = _lane(repo, root, "k001", state="kept", keep_until=time.time() + 3600, row="row-a")
    a = _lane(repo, root, "l001", state="live", owner=_me())
    out = dispatch.sweep_lanes(filed_dir=tmp_path / "none")
    assert out["orphans"] == [str(o)] and not o.exists()
    assert k.exists() and a.exists() and sorted(out["kept"]) == sorted([str(k), str(a)])


# ------------------------------------------------------------------------------- fix 2: --release-filed
def test_release_filed_drops_kept_lanes_of_filed_rows(tmp_path, monkeypatch):
    root = tmp_path / "tf"
    root.mkdir()
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(root))
    repo = _repo(tmp_path)
    filed, ready = tmp_path / "filing-done", tmp_path / "ready"
    filed.mkdir()
    ready.mkdir()
    (filed / "row-a.FILED").write_text("FILED row-a\n")
    k_meta = _lane(repo, root, "k001", state="kept", keep_until=time.time() + 3600, row="row-a")
    k_other = _lane(repo, root, "k002", state="kept", keep_until=time.time() + 3600, row="row-b")
    # pre-r8d lane: no row in metadata, resolved through the filed row's workdir/<base_dir>/lane.path
    k_legacy = _lane(repo, root, "k003", state="kept", keep_until=time.time() + 3600)
    wd = tmp_path / "wd-a"
    (wd / "out" / "arm" / "t00" / "t00").mkdir(parents=True)
    (wd / "out" / "arm" / "t00" / "t00" / "lane.path").write_text(str(k_legacy))
    (ready / "row-a.json").write_text(json.dumps({"id": "row-a", "workdir": str(wd)}))
    plain = dispatch.sweep_lanes(filed_dir=filed, ready_dir=ready)
    assert plain["removed"] == [] and k_meta.exists()                # without the flag nothing filed is released
    out = dispatch.sweep_lanes(release_filed=True, filed_dir=filed, ready_dir=ready)
    assert not k_meta.exists() and not k_legacy.exists() and k_other.exists()
    assert sorted(out["released_filed"]) == sorted([f"{k_meta}:row-a", f"{k_legacy}:row-a"])
    assert "taskflow/t/k001" not in _g(repo, "branch", "--list")     # no commits over base -> branch gone


def test_cli_sweep_has_release_filed_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    monkeypatch.setattr(dispatch, "FILED_DIR", tmp_path / "none")
    assert dispatch.main(["sweep", "--release-filed"]) == 0
    assert "released_filed" in capsys.readouterr().out


# ------------------------------------------------------------------------------- fix 4: harness-only stint
def _row(u, reason="lane", verdict="error"):
    return {"unit_id": u, "verdict": verdict, "reason": reason, "failure_class": "harness"}


def test_all_lane_stint_is_futility_and_quarantined(tmp_path):
    rows = [_row("a:T1"), _row("a:T2", reason="harness")]
    prior = {"unit_id": "a:T0", "verdict": "verified", "reason": None}
    (tmp_path / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in [prior] + rows))
    assert stage1_result.harness_futility(rows)
    assert stage1_result.quarantine_stint(tmp_path, rows) == 2
    left = stage1_result.read_rows(tmp_path / "results.jsonl")
    assert [r["unit_id"] for r in left] == ["a:T0"]
    assert len(stage1_result.read_rows(tmp_path / "harness-futility.jsonl")) == 2


def test_mixed_stint_is_not_futility_and_lane_rows_never_count_done():
    rows = [_row("a:T1"), _row("a:T2", reason="tests-fail", verdict="rejected")]
    assert not stage1_result.harness_futility(rows) and not stage1_result.harness_futility([])
    assert stage1_result.units_done(rows) == {"a:T2"}

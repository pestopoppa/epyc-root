"""Quiet-host scan deferral (2026-11-10 19:02Z FAIL_FOREIGN_LOAD: host_hygiene_tick's `du -sx /mnt/raid0/llm/worktrees`
ran inside AutoKernel's whole-host grant). A live quiet-host grant defers every covered background scan; no grant -> it runs.

Named test_churn_* so deploy_rowflow.sh's gate runs it."""
import datetime as dt
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

CO = Path(__file__).resolve().parents[1]
REPO = CO.parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


qh = _load("quiet_host", CO / "quiet_host.py")


def _iso(delta_s):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=delta_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _grant(flags, gid, holds="q0,q1,q2,q3,gpu-quiet", end_delta=3600):
    g = Path(flags) / "grants"
    g.mkdir(parents=True, exist_ok=True)
    end = f" end={_iso(end_delta)}" if end_delta is not None else ""
    (g / f"{gid}.grant").write_text(f"row={gid} holds={holds}{end} kind=whole-host\nmore\n")


@pytest.fixture(params=["live", "none"])
def flags(request, tmp_path, monkeypatch):
    f = tmp_path / "flags"
    (f / "grants").mkdir(parents=True)
    _grant(f, "partial-row", holds="q0,q1")                    # never a quiet-host grant
    _grant(f, "expired-row", end_delta=-60)                    # expired leftover never defers
    if request.param == "live":
        _grant(f, "ak-floor-r4")
    monkeypatch.setenv("QUIET_HOST_FLAGS", str(f))
    return request.param, f


# ------------------------------------------------------------------ the helper
def test_helper_grant_semantics(flags):
    mode, f = flags
    assert qh.quiet_host_grant() == ("ak-floor-r4" if mode == "live" else None)
    logs = []
    assert qh.defer("t", log=logs.append) is (mode == "live")
    assert all(m.startswith("DEFER-QUIET-HOST t:") for m in logs) and len(logs) == (mode == "live")


def test_helper_no_end_is_live(tmp_path):
    _grant(tmp_path, "g", end_delta=None)
    assert qh.quiet_host_grant(str(tmp_path)) == "g"


def test_scan_prefix_is_nice_ionice_never_pinned():
    p = qh.scan_prefix()
    assert p[:3] == ["nice", "-n", "19"] and "ionice" in p and "taskset" not in p and "numactl" not in p


def test_helper_exec_cli(flags):
    mode, _ = flags
    cp = subprocess.run([sys.executable, str(CO / "quiet_host.py"), "exec", "x", "--", "echo", "ran"],
                        capture_output=True, text=True)
    if mode == "live":
        assert cp.returncode == 75 and "DEFER-QUIET-HOST x" in cp.stderr and "ran" not in cp.stdout
    else:
        assert cp.returncode == 0 and cp.stdout.strip() == "ran"


# ------------------------------------------------------------------ covered callers
def test_worktree_footprint(flags, tmp_path, monkeypatch):
    mode, _ = flags
    wf = _load("worktree_footprint", CO / "worktree_footprint.py")
    d = tmp_path / "t1"
    d.mkdir()
    calls = []
    monkeypatch.setattr(wf.subprocess, "run", lambda cmd, **k: calls.append(cmd) or
                        subprocess.CompletedProcess(cmd, 0, "4096\t" + cmd[-1], ""))
    res = wf.collect(cache=str(tmp_path / "c.json"), lister=lambda repos: [{"path": str(d), "repo": "r", "branch": ""}])
    du = [c for c in calls if "du" in c]
    if mode == "live":
        assert du == [] and res["_meta"]["measured_now"] == 0
    else:
        assert len(du) == 1 and du[0][:3] == ["nice", "-n", "19"] and res["_meta"]["measured_now"] == 1


def test_host_hygiene_heavy_gate(flags, monkeypatch):
    mode, _ = flags
    hh = _load("host_hygiene_tick", REPO / "scripts" / "system" / "host_hygiene_tick.py")
    monkeypatch.setattr(hh, "CPU_WINDOW", Path("/nonexistent/cpu-window.json"))
    monkeypatch.setattr(hh, "run", lambda argv, **k: subprocess.CompletedProcess(argv, 0, "[]", ""))
    ok, why = hh.heavy_gate()
    if mode == "live":
        assert not ok and why.startswith("DEFER-QUIET-HOST") and "ak-floor-r4" in why
    else:
        assert ok


def test_worktree_gate_du_background(flags, tmp_path, monkeypatch):
    mode, _ = flags
    wg = _load("worktree_gate", REPO / "scripts" / "system" / "worktree_gate.py")
    calls = []
    monkeypatch.setattr(wg.subprocess, "run", lambda cmd, **k: calls.append(cmd) or
                        subprocess.CompletedProcess(cmd, 0, "8192\tx", ""))
    monkeypatch.setenv("EPYC_BACKGROUND_SCAN", "1")
    assert wg._du_bytes(str(tmp_path)) == (None if mode == "live" else 8192)
    monkeypatch.delenv("EPYC_BACKGROUND_SCAN")                 # interactive `report --sizes` is never deferred
    assert wg._du_bytes(str(tmp_path)) == 8192
    assert all(c[:3] == ["nice", "-n", "19"] for c in calls)


def test_notify_reclaimable(flags, tmp_path, monkeypatch):
    mode, _ = flags
    sys.path.insert(0, str(CO / "rowflow"))
    nt = _load("notify", CO / "rowflow" / "notify.py")
    (tmp_path / "a").mkdir()
    out = nt.reclaimable(str(tmp_path))
    if mode == "live":
        assert out == [{"deferred": "DEFER-QUIET-HOST: quiet-host grant live"}]
    else:
        assert out and out[0]["path"].endswith("/a")


def test_handoff_sessions_du(flags, tmp_path, monkeypatch):
    mode, _ = flags
    hs = _load("handoff_sessions", CO / "handoff_sessions.py")
    calls = []
    monkeypatch.setattr(hs.subprocess, "run", lambda cmd, **k: calls.append(cmd) or
                        subprocess.CompletedProcess(cmd, 0, "1048576\tx", ""))
    assert hs.du_gib(str(tmp_path)) == (0.0 if mode == "live" else 1.0)
    assert len(calls) == (mode != "live")


def test_disk_trend_scan(flags, tmp_path):
    mode, f = flags
    env = dict(os.environ, DISK_TREND_OUT=str(tmp_path / "trend.tsv"))
    cp = subprocess.run(["bash", str(CO / "churn" / "ws58-disk-trend.sh"), "--once-scan", "worktrees", str(tmp_path)],
                        capture_output=True, text=True, env=env)
    assert cp.returncode == 0, cp.stderr
    if mode == "live":
        assert cp.stdout.strip() == "defer"
        assert "DEFER-QUIET-HOST disk-trend worktrees" in (tmp_path / "disk-trend.log").read_text()
    else:
        assert cp.stdout.strip().endswith("G")


def test_disk_janitor_scans(flags, tmp_path):
    mode, f = flags
    log = tmp_path / "janitor.log"
    env = dict(os.environ, JANITOR_FLAGS=str(f), JANITOR_LOG=str(log), JANITOR_QUIET_HOST=str(CO / "quiet_host.py"))
    cp = subprocess.run(["bash", str(CO / "churn" / "disk_janitor.sh"), "--scan-check", "BUDGET"],
                        capture_output=True, text=True, env=env)
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip() == ("DEFER" if mode == "live" else "RUN")
    if mode == "live":
        assert "DEFER-QUIET-HOST BUDGET: quiet-host grant ak-floor-r4 live" in log.read_text()


def test_janitor_has_no_second_grant_parser():
    src = (CO / "churn" / "disk_janitor.sh").read_text()
    assert "holds=" not in src.split("quiet_host_grant() {", 1)[1].split("\n}\n", 1)[0]

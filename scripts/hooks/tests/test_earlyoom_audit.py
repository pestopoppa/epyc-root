"""earlyoom_audit.sh: the kill line, plus the once-per-burst /proc memory snapshot (NIB2-97(b)).

INC-20261021-earlyoom-session-kills left no memory sample on disk at the trigger instant. The
hook now appends one EARLYOOM_MEM_SNAPSHOT line per kill burst. These tests drive it against a
fake /proc tree (EARLYOOM_PROC_ROOT) and private log paths, so they never touch the host logs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "earlyoom_audit.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

MEMINFO = """MemTotal:       1000000 kB
MemFree:          50000 kB
MemAvailable:    120000 kB
Buffers:           1000 kB
Cached:          300000 kB
SwapTotal:         8000 kB
SwapFree:             0 kB
AnonPages:       600000 kB
Mlocked:          40000 kB
"""
PSI = "some avg10=1.50 avg60=0.70 avg300=0.20 total=12345\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=1\n"


def _fake_proc(root: Path, n: int = 14) -> Path:
    proc = root / "proc"
    (proc / "pressure").mkdir(parents=True)
    (proc / "meminfo").write_text(MEMINFO)
    (proc / "pressure" / "memory").write_text(PSI)
    for k in range(1, n + 1):
        d = proc / str(1000 + k)
        d.mkdir()
        name = 'we"ird\\nm' if k == 3 else ("tmux: server" if k == 5 else f"proc{k}")
        (d / "status").write_text(
            f"Name:\t{name}\nUmask:\t0022\nState:\tS (sleeping)\nTgid:\t{1000 + k}\n"
            f"Pid:\t{1000 + k}\nVmPeak:\t  99999999 kB\nVmRSS:\t   {k * 1000} kB\nThreads:\t1\n")
    kt = proc / "2"                           # a kernel thread: no VmRSS line
    kt.mkdir()
    (kt / "status").write_text("Name:\tkthreadd\nPid:\t2\nThreads:\t1\n")
    (proc / "self").mkdir()                   # non-numeric entries are ignored
    return proc


def _run(tmp: Path, proc: Path, pid: str = "4242", window: str = "60", **extra: str):
    env = {k: v for k, v in os.environ.items() if not k.startswith("EARLYOOM_")}
    env.update({
        "EARLYOOM_AUDIT_LOG": str(tmp / "logs" / "audit.log"),
        "EARLYOOM_PROC_ROOT": str(proc),
        "EARLYOOM_SNAPSHOT_WINDOW": window,
        "EARLYOOM_PID": pid, "EARLYOOM_NAME": "llama-bench",
        "EARLYOOM_CMDLINE": "llama-bench -m x", "EARLYOOM_UID": "1000",
    })
    env.update(extra)
    (tmp / "logs").mkdir(exist_ok=True)
    res = subprocess.run(["bash", str(HOOK)], env=env, capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return res


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_first_kill_writes_kill_line_and_one_snapshot(tmp_path: Path) -> None:
    proc = _fake_proc(tmp_path)
    _run(tmp_path, proc)
    kills = _lines(tmp_path / "logs" / "audit.log")
    snaps = _lines(tmp_path / "logs" / "earlyoom_meminfo_snapshots.log")
    assert [k["cat"] for k in kills] == ["EARLYOOM_KILL"]
    assert len(snaps) == 1
    snap = snaps[0]
    assert snap["cat"] == "EARLYOOM_MEM_SNAPSHOT" and snap["trigger_pid"] == "4242"
    mem = snap["meminfo"]
    for key, val in {"MemAvailable_kB": 120000, "AnonPages_kB": 600000, "Mlocked_kB": 40000,
                     "Cached_kB": 300000, "SwapFree_kB": 0}.items():
        assert mem[key] == val
    assert "Buffers_kB" not in mem
    assert snap["psi_memory_some"].startswith("some avg10=1.50")
    top = snap["top_vmrss"]
    assert len(top) == 10
    assert [t["VmRSS_kB"] for t in top] == [k * 1000 for k in range(14, 4, -1)]
    assert top[0] == {"pid": 1014, "name": "proc14", "VmRSS_kB": 14000}
    assert top[-1]["name"] == "tmux: server"


def test_escapes_process_names_into_valid_json(tmp_path: Path) -> None:
    proc = _fake_proc(tmp_path, n=4)
    _run(tmp_path, proc)
    (snap,) = _lines(tmp_path / "logs" / "earlyoom_meminfo_snapshots.log")
    assert 'we"ird\\nm' in [t["name"] for t in snap["top_vmrss"]]


def test_one_snapshot_per_burst(tmp_path: Path) -> None:
    proc = _fake_proc(tmp_path)
    for pid in ("1", "2", "3"):
        _run(tmp_path, proc, pid=pid)
    assert len(_lines(tmp_path / "logs" / "audit.log")) == 3        # every kill still logged
    snaps = _lines(tmp_path / "logs" / "earlyoom_meminfo_snapshots.log")
    assert [s["trigger_pid"] for s in snaps] == ["1"]


def test_new_burst_after_window_snapshots_again(tmp_path: Path) -> None:
    proc = _fake_proc(tmp_path)
    _run(tmp_path, proc, pid="1")
    (tmp_path / "logs" / "earlyoom_snapshot_stamp.log").write_text("100\n")  # long ago
    _run(tmp_path, proc, pid="2")
    snaps = _lines(tmp_path / "logs" / "earlyoom_meminfo_snapshots.log")
    assert [s["trigger_pid"] for s in snaps] == ["1", "2"]


def test_missing_proc_never_fails_the_kill_line(tmp_path: Path) -> None:
    _run(tmp_path, tmp_path / "no-such-proc")
    assert [k["cat"] for k in _lines(tmp_path / "logs" / "audit.log")] == ["EARLYOOM_KILL"]


def test_snapshot_is_read_only_on_proc(tmp_path: Path) -> None:
    proc = _fake_proc(tmp_path)
    before = {p: p.read_bytes() for p in proc.rglob("*") if p.is_file()}
    _run(tmp_path, proc)
    after = {p: p.read_bytes() for p in proc.rglob("*") if p.is_file()}
    assert before == after

"""GPS-PIN-2 on v11_driver: knob on every pinned GPU launch, polling re-pin, refuse on escape.
Synthetic /proc + fake Popen/helper paths only; nothing is launched."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v11_driver_under_test", HERE / "v11_driver.py")
d = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = d
spec.loader.exec_module(d)

LANE = d.GPU_THREADS
REAL_PINPOLL = d.PinPoll
PREFIX = ["taskset", "-c", LANE, "numactl", "--membind=3", "--", "bench"]


def _proc(tmp_path, masks, ppid):
    root = tmp_path / "proc"
    for tid, m in masks.items():
        t = root / "4242" / "task" / str(tid)
        t.mkdir(parents=True)
        (t / "status").write_text(f"Cpus_allowed_list:\t{m}\n")
        (t / "comm").write_text("x\n")
    (root / "4242" / "stat").write_text(f"4242 (x) S {ppid} 1 1 0\n")
    return root


def _setter(root, stick=True):
    def s(tid, cpus):
        if stick:
            (root / "4242" / "task" / str(tid) / "status").write_text(
                f"Cpus_allowed_list:\t{d.launch_affinity().format_cpu_list(cpus)}\n")
    return s


def test_helper_absent_refuses(monkeypatch):
    monkeypatch.setattr(d, "_LA", None)
    monkeypatch.setattr(d, "LAUNCH_AFFINITY_CANDIDATES", [Path("/nonexistent/la.py")])
    with pytest.raises(d.Refuse):
        d.launch_affinity()


def test_env_knob_only_on_taskset_and_input_untouched():
    base = {"A": "1", "HSA_OVERRIDE_CPU_AFFINITY_DEBUG": "1"}
    e = d.pinned_env(base, PREFIX)
    assert e["HSA_OVERRIDE_CPU_AFFINITY_DEBUG"] == "0" and base["HSA_OVERRIDE_CPU_AFFINITY_DEBUG"] == "1"
    assert "HSA_OVERRIDE_CPU_AFFINITY_DEBUG" not in d.pinned_env({"A": "1"}, ["nice", "-n", "19", "x"])


def test_pinpoll_repins_and_records(tmp_path):
    root = _proc(tmp_path, {1: LANE, 2: "0-191", 3: "186"}, ppid=77)
    with d.PinPoll(4242, LANE, interval_s=0.01, proc_root=root, setter=_setter(root), launcher_pid=77) as w:
        pass
    w.poll()
    rec = w.record
    assert rec["ok"] and [r["tid"] for r in rec["repinned"]] == [2] and rec["tasks_max"] == 3


def test_pinpoll_residual_escape_not_ok(tmp_path):
    root = _proc(tmp_path, {1: LANE, 2: "0-191"}, ppid=77)
    w = d.PinPoll(4242, LANE, proc_root=root, setter=_setter(root, stick=False), launcher_pid=77)
    w.poll()
    assert not w.record["ok"] and w.record["escapes_after"]


def test_pinpoll_foreign_pid_not_ok(tmp_path):
    root = _proc(tmp_path, {1: LANE}, ppid=1)
    w = d.PinPoll(4242, LANE, proc_root=root, launcher_pid=77)
    w.poll()
    assert not w.record["child"] and not w.record["ok"]


class FakeCtx:
    def __init__(self, tmp_path):
        self.dir, self.log = tmp_path, tmp_path / "driver.log"

    def time_left(self): return 10_000
    def register(self, pid): pass
    def say(self, m): pass


class FakePopen:
    pid = 4242
    returncode = 0
    env = None

    def __init__(self, argv, env=None, **kw):
        FakePopen.env = env

    def wait(self, t=None): return 0
    def poll(self): return 0


def _patch_pin(monkeypatch, root, stick):
    real = REAL_PINPOLL
    monkeypatch.setattr(d, "PinPoll", lambda pid, cpus: real(pid, cpus, interval_s=0.01, proc_root=root,
                                                              setter=_setter(root, stick), launcher_pid=os.getpid()))


def test_run_logged_pin_out_and_refusal(tmp_path, monkeypatch):
    monkeypatch.setattr(d.subprocess, "Popen", FakePopen)
    root = _proc(tmp_path, {1: LANE, 2: "0-191"}, ppid=os.getpid())
    _patch_pin(monkeypatch, root, True)
    pins: list = []
    rc, pid = d.run_logged(PREFIX, {"X": "1"}, tmp_path / "l.log", 5, pin_out=pins)
    assert rc == 0 and pins[0]["ok"] and FakePopen.env["HSA_OVERRIDE_CPU_AFFINITY_DEBUG"] == "0"
    root2 = _proc(tmp_path / "b", {1: LANE, 2: "0-191"}, ppid=os.getpid())
    _patch_pin(monkeypatch, root2, False)
    pins2: list = []
    d.run_logged(PREFIX, {}, tmp_path / "l2.log", 5, pin_out=pins2)
    assert not pins2[0]["ok"]


def test_run_logged_without_pin_out_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(d.subprocess, "Popen", FakePopen)
    d.run_logged(["nice", "x"], {"X": "1"}, tmp_path / "l.log", 5)
    assert "HSA_OVERRIDE_CPU_AFFINITY_DEBUG" not in FakePopen.env


def test_tbo_gpu_escape_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(d.subprocess, "Popen", FakePopen)
    root = _proc(tmp_path, {1: LANE, 2: "0-191"}, ppid=os.getpid())
    _patch_pin(monkeypatch, root, False)
    (tmp_path / "tbo_n.log").write_text("")
    out = d.tbo(FakeCtx(tmp_path), "n", Path("/b"), Path("/b"), "gpu", "ROCm0", "FLASH_ATTN_EXT")
    assert out["pin_refused"] and out["rc"] == 125 and out["passed"] == 0


def test_gpu_bench_launch_refuses_and_records(tmp_path, monkeypatch):
    monkeypatch.setattr(d.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(d, "Residency", lambda pid, build: type("R", (), {"stop": lambda s: {"resident": True}})())
    root = _proc(tmp_path, {1: LANE, 2: "0-191"}, ppid=os.getpid())
    _patch_pin(monkeypatch, root, False)
    r = d.gpu_bench_launch(FakeCtx(tmp_path), "t", Path("/b"), Path("/m"), [])
    assert "error" in r and r["pin"]["escapes_after"] and "rows" not in r
    assert FakePopen.env["HSA_OVERRIDE_CPU_AFFINITY_DEBUG"] == "0"

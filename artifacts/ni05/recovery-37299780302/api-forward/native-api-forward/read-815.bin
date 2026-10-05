"""Tests for orchestrator stack process helpers."""

from __future__ import annotations

import signal

from scripts.server import stack_processes


class _RunResult:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_pids_on_port_uses_listener_filter(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return _RunResult(stdout="123\nnot-a-pid\n456\n")

    monkeypatch.setattr(stack_processes.subprocess, "run", fake_run)

    assert stack_processes.pids_on_port(8000) == [123, 456]
    assert calls == [["lsof", "-t", "-sTCP:LISTEN", "-i:8000"]]


def test_scan_known_ports_only_returns_listeners(monkeypatch) -> None:
    monkeypatch.setattr(
        stack_processes,
        "pids_on_port",
        lambda port, timeout=5: [port + 1] if port == 8000 else [],
    )

    assert stack_processes.scan_known_ports([9000, 8000, 9000]) == {8000: [8001]}


def test_process_cmdline_parses_proc_tokens(monkeypatch) -> None:
    class _FakePath:
        def __init__(self, path: str) -> None:
            self.path = path

        def read_bytes(self) -> bytes:
            assert self.path == "/proc/123/cmdline"
            return b"llama-server\0-m\0/models/current.gguf\0"

    monkeypatch.setattr(stack_processes, "Path", _FakePath)

    assert stack_processes.process_cmdline(123) == [
        "llama-server",
        "-m",
        "/models/current.gguf",
    ]


def test_process_cmdline_returns_empty_when_unavailable(monkeypatch) -> None:
    class _FakePath:
        def __init__(self, _path: str) -> None:
            pass

        def read_bytes(self) -> bytes:
            raise FileNotFoundError

    monkeypatch.setattr(stack_processes, "Path", _FakePath)

    assert stack_processes.process_cmdline(123) == []
    assert stack_processes.process_cmdline(-1) == []


def test_kill_process_tree_skips_current_process(monkeypatch) -> None:
    killed: list[tuple[int, signal.Signals]] = []
    alive = {222}

    monkeypatch.setattr(stack_processes.os, "getpid", lambda: 111)
    monkeypatch.setattr(stack_processes, "collect_descendants", lambda _pid: [111, 222])
    monkeypatch.setattr(stack_processes.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(stack_processes, "pid_alive", lambda pid: pid in alive)

    def fake_kill(pid: int, sig: signal.Signals) -> None:
        killed.append((pid, sig))
        alive.discard(pid)

    monkeypatch.setattr(stack_processes.os, "kill", fake_kill)

    assert stack_processes.kill_process_tree(333, timeout=1) is True
    assert killed == [(333, signal.SIGTERM), (222, signal.SIGTERM)]


def test_free_memory_gb_parses_memavailable(monkeypatch, tmp_path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:        1184561856 kB\n"
        "MemFree:           12345678 kB\n"
        "MemAvailable:     104857600 kB\n"   # exactly 100 GB
        "Buffers:             123456 kB\n"
    )
    real_open = open

    def fake_open(path, *a, **kw):
        if path == "/proc/meminfo":
            return real_open(meminfo, *a, **kw)
        return real_open(path, *a, **kw)

    import builtins
    monkeypatch.setattr(builtins, "open", fake_open)

    assert stack_processes.free_memory_gb() == 100


def test_free_memory_gb_returns_zero_when_memavailable_missing(monkeypatch, tmp_path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:        1184561856 kB\n")
    real_open = open

    def fake_open(path, *a, **kw):
        if path == "/proc/meminfo":
            return real_open(meminfo, *a, **kw)
        return real_open(path, *a, **kw)

    import builtins
    monkeypatch.setattr(builtins, "open", fake_open)

    assert stack_processes.free_memory_gb() == 0


def test_renice_all_threads_silent_when_task_dir_missing(monkeypatch, capsys) -> None:
    """renice must be a no-op (no print, no setpriority) when /proc/PID/task is absent."""
    class _NotExists:
        def exists(self) -> bool:
            return False

        def iterdir(self):
            raise AssertionError("iterdir must not be called when path doesn't exist")

    monkeypatch.setattr(stack_processes, "Path", lambda _p: _NotExists())

    def boom(*a, **kw):
        raise AssertionError("setpriority must not be called when task_dir is missing")
    monkeypatch.setattr(stack_processes.os, "setpriority", boom)

    stack_processes.renice_all_threads(12345, 19)
    assert capsys.readouterr().out == ""


def test_renice_all_threads_counts_ok_and_failures(monkeypatch, capsys) -> None:
    """Mix integer + non-integer tid dirs; mix successful + permission-failing setpriority calls."""
    class _FakeTaskDir:
        def exists(self) -> bool:
            return True

        def iterdir(self):
            class _Entry:
                def __init__(self, name: str) -> None:
                    self.name = name
            # "stat" is non-integer (should be skipped silently),
            # 1000/1001 succeed, 1002 fails with PermissionError.
            return iter([_Entry("1000"), _Entry("stat"), _Entry("1001"), _Entry("1002")])

    monkeypatch.setattr(stack_processes, "Path", lambda _p: _FakeTaskDir())

    seen: list[tuple[int, int, int]] = []

    def fake_setpriority(which, tid, nice):
        seen.append((which, tid, nice))
        if tid == 1002:
            raise PermissionError("can't renice")

    monkeypatch.setattr(stack_processes.os, "setpriority", fake_setpriority)

    stack_processes.renice_all_threads(54321, 19)

    # Three setpriority calls (1000, 1001, 1002) — "stat" entry was skipped pre-call.
    assert [t[1] for t in seen] == [1000, 1001, 1002]
    out = capsys.readouterr().out
    assert "[renice] 2 thread(s) → nice=19" in out
    assert "(1 failed)" in out


def test_set_oom_score_adj_uses_choom_when_available(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return _RunResult()

    # sudo + choom both present
    monkeypatch.setattr(stack_processes.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(stack_processes.subprocess, "run", fake_run)

    assert stack_processes.set_oom_score_adj([111, 222], adj=-1000) == 2
    assert calls == [
        ["sudo", "-n", "choom", "-n", "-1000", "-p", "111"],
        ["sudo", "-n", "choom", "-n", "-1000", "-p", "222"],
    ]


def test_set_oom_score_adj_falls_back_to_tee_without_choom(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return _RunResult()

    monkeypatch.setattr(
        stack_processes.shutil, "which",
        lambda name: "/usr/bin/sudo" if name == "sudo" else None,
    )
    monkeypatch.setattr(stack_processes.subprocess, "run", fake_run)

    assert stack_processes.set_oom_score_adj([111]) == 1
    assert calls == [["sudo", "-n", "tee", "/proc/111/oom_score_adj"]]


def test_set_oom_score_adj_noop_without_sudo(monkeypatch) -> None:
    def fake_run(_cmd, **_kwargs):
        raise AssertionError("subprocess.run must not be called when sudo is absent")

    monkeypatch.setattr(stack_processes.shutil, "which", lambda _name: None)
    monkeypatch.setattr(stack_processes.subprocess, "run", fake_run)

    assert stack_processes.set_oom_score_adj([111, 222]) == 0


def test_set_oom_score_adj_is_best_effort_on_failure(monkeypatch) -> None:
    def fake_run(cmd, **_kwargs):
        if cmd[-1] == "222":  # second pid denied (e.g. NOPASSWD not configured)
            raise RuntimeError("sudo: a password is required")
        return _RunResult()

    monkeypatch.setattr(stack_processes.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(stack_processes.subprocess, "run", fake_run)

    # does not raise; returns the count of successes
    assert stack_processes.set_oom_score_adj([111, 222]) == 1


def test_set_oom_score_adj_empty_is_noop() -> None:
    assert stack_processes.set_oom_score_adj([]) == 0

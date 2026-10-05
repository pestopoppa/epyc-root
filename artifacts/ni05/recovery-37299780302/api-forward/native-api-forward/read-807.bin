"""Tests for orchestrator stack host-prerequisite helpers."""

from __future__ import annotations

import subprocess

from scripts.server import stack_host
from scripts.server.stack_host import (
    _HOST_PREREQ_GOVERNOR,
    _HOST_PREREQ_SYSCTLS,
    _HOST_PREREQ_THP,
    _read_thp_active,
    apply_host_prerequisites,
    check_host_prerequisites,
)


def test_read_thp_active_extracts_bracketed_token(tmp_path) -> None:
    thp_file = tmp_path / "thp"
    thp_file.write_text("always [madvise] never\n")
    assert _read_thp_active(str(thp_file)) == "madvise"


def test_read_thp_active_no_brackets_returns_full_content(tmp_path) -> None:
    thp_file = tmp_path / "thp"
    thp_file.write_text("always\n")
    assert _read_thp_active(str(thp_file)) == "always"


def test_read_thp_active_returns_none_on_missing_file(tmp_path) -> None:
    assert _read_thp_active(str(tmp_path / "missing")) is None


def test_check_host_prerequisites_all_pass(monkeypatch) -> None:
    monkeypatch.setattr(stack_host, "_read_sysctl",
                        lambda key: _HOST_PREREQ_SYSCTLS[key])
    monkeypatch.setattr(stack_host, "_read_thp_active",
                        lambda path: _HOST_PREREQ_THP[path])
    monkeypatch.setattr(stack_host, "_read_governor", lambda: _HOST_PREREQ_GOVERNOR)

    ok, drift = check_host_prerequisites()
    assert ok is True
    assert drift == []


def test_check_host_prerequisites_reports_drift(monkeypatch) -> None:
    monkeypatch.setattr(stack_host, "_read_sysctl",
                        lambda key: "1" if key == "kernel.numa_balancing" else _HOST_PREREQ_SYSCTLS[key])
    monkeypatch.setattr(stack_host, "_read_thp_active",
                        lambda path: "madvise")
    monkeypatch.setattr(stack_host, "_read_governor", lambda: "powersave")

    ok, drift = check_host_prerequisites()
    assert ok is False
    # numa_balancing + both THP paths + governor = 4 drift items
    assert len(drift) == 4
    drift_text = "\n".join(drift)
    assert "kernel.numa_balancing=1 (want 0)" in drift_text
    assert "scaling_governor=powersave (want performance)" in drift_text


def test_check_host_prerequisites_none_value_reports_drift(monkeypatch) -> None:
    """Missing files (sysctl returns None) must surface as drift, not be swallowed."""
    monkeypatch.setattr(stack_host, "_read_sysctl", lambda key: None)
    monkeypatch.setattr(stack_host, "_read_thp_active", lambda path: _HOST_PREREQ_THP[path])
    monkeypatch.setattr(stack_host, "_read_governor", lambda: _HOST_PREREQ_GOVERNOR)

    ok, drift = check_host_prerequisites()
    assert ok is False
    assert any("=None" in m for m in drift)


def test_apply_host_prerequisites_skips_when_auto_fix_disabled(monkeypatch, capsys) -> None:
    monkeypatch.setattr(stack_host, "_read_sysctl", lambda key: "wrong")
    monkeypatch.setattr(stack_host, "_read_thp_active", lambda path: "madvise")
    monkeypatch.setattr(stack_host, "_read_governor", lambda: "powersave")

    def boom(*a, **kw):
        raise AssertionError("subprocess must not run when auto_fix=False")
    monkeypatch.setattr(subprocess, "run", boom)

    assert apply_host_prerequisites(auto_fix=False) is False
    out = capsys.readouterr().out
    assert "[DRIFT]" in out
    assert "auto_fix disabled" in out


def test_apply_host_prerequisites_short_circuits_when_canonical(monkeypatch, capsys) -> None:
    monkeypatch.setattr(stack_host, "_read_sysctl",
                        lambda key: _HOST_PREREQ_SYSCTLS[key])
    monkeypatch.setattr(stack_host, "_read_thp_active",
                        lambda path: _HOST_PREREQ_THP[path])
    monkeypatch.setattr(stack_host, "_read_governor", lambda: _HOST_PREREQ_GOVERNOR)

    def boom(*a, **kw):
        raise AssertionError("subprocess must not run on canonical host")
    monkeypatch.setattr(subprocess, "run", boom)

    assert apply_host_prerequisites(auto_fix=True) is True
    assert "[OK] All host prerequisites satisfied" in capsys.readouterr().out


def test_apply_host_prerequisites_returns_false_when_sudo_fails(monkeypatch) -> None:
    """When subprocess.run fails for every fix attempt, the function must return False."""
    monkeypatch.setattr(stack_host, "_read_sysctl", lambda key: "wrong")
    monkeypatch.setattr(stack_host, "_read_thp_active", lambda path: "madvise")
    monkeypatch.setattr(stack_host, "_read_governor", lambda: "powersave")

    def fail_run(*a, **kw):
        raise FileNotFoundError("sudo")
    monkeypatch.setattr(subprocess, "run", fail_run)

    assert apply_host_prerequisites(auto_fix=True) is False


def test_apply_host_prerequisites_skips_already_canonical_fix_targets(monkeypatch, capsys) -> None:
    """Autofix should only attempt the prerequisite that is still drifting."""
    calls: list[list[str]] = []

    def read_sysctl(key: str) -> str:
        return _HOST_PREREQ_SYSCTLS[key]

    def read_thp(path: str) -> str:
        return _HOST_PREREQ_THP[path]

    monkeypatch.setattr(stack_host, "_read_sysctl", read_sysctl)
    monkeypatch.setattr(stack_host, "_read_thp_active", read_thp)
    monkeypatch.setattr(stack_host, "_read_governor", lambda: "powersave")

    def record_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", record_run)

    assert apply_host_prerequisites(auto_fix=True) is False
    assert calls == [["sudo", "-n", "cpupower", "frequency-set", "-g", _HOST_PREREQ_GOVERNOR]]
    out = capsys.readouterr().out
    assert "[FIX] Applying canonical settings (sudo -n)..." in out
    assert "FAILED" not in out

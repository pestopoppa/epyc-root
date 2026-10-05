"""Unit tests for the page-cache prewarm helper.

The helper itself is small; the value here is locking down the contract
that stack_commands.cmd_start depends on:

  * `-m`, `-md`, `--mmproj` are the GGUF-bearing flags that get warmed.
  * Two servers pointing at the same physical file are warmed once
    (inode dedupe), not twice.
  * Skip flag and the equivalent ORCHESTRATOR_SKIP_PAGE_CACHE_PREWARM env
    both bypass subprocess invocation cleanly.
  * Failures are surfaced via the return code but do not block startup.

All filesystem and subprocess effects are monkeypatched — the test suite
does NOT touch any real GGUF.
"""

from __future__ import annotations

import subprocess
import types
from pathlib import Path
from typing import Any

import pytest

from scripts.server import stack_prewarm


# ---------------------------------------------------------------------------
# _extract_paths_from_cmd
# ---------------------------------------------------------------------------


def test_extract_paths_collects_m_md_mmproj() -> None:
    cmd = [
        "/bin/llama-server",
        "-m",
        "/models/a.gguf",
        "-md",
        "/models/draft.gguf",
        "--mmproj",
        "/models/mmproj.gguf",
        "--port",
        "8070",
    ]
    assert stack_prewarm._extract_paths_from_cmd(cmd) == [
        "/models/a.gguf",
        "/models/draft.gguf",
        "/models/mmproj.gguf",
    ]


def test_extract_paths_handles_missing_flags() -> None:
    cmd = ["/bin/llama-server", "-m", "/models/a.gguf", "--port", "8090"]
    assert stack_prewarm._extract_paths_from_cmd(cmd) == ["/models/a.gguf"]


def test_extract_paths_ignores_dangling_flag() -> None:
    cmd = ["/bin/llama-server", "-m"]
    assert stack_prewarm._extract_paths_from_cmd(cmd) == []


# ---------------------------------------------------------------------------
# collect_targets — inode dedupe + error handling
# ---------------------------------------------------------------------------


class _FakeStat:
    def __init__(self, dev: int, ino: int, size: int) -> None:
        self.st_dev = dev
        self.st_ino = ino
        self.st_size = size


def _patch_path_resolution(
    monkeypatch: pytest.MonkeyPatch,
    inodes: dict[str, tuple[int, int, int]],
) -> None:
    """Make Path(p).resolve(strict=True).stat() return the fixture entry.

    `inodes` maps path string -> (dev, ino, size). Paths not in the map
    raise FileNotFoundError on resolve(strict=True) — exactly what real
    Path.resolve does for nonexistent files.
    """

    real_resolve = Path.resolve
    real_stat = Path.stat

    def fake_resolve(self: Path, *, strict: bool = False) -> Path:
        key = str(self)
        if key in inodes:
            return self
        if strict:
            raise FileNotFoundError(key)
        return real_resolve(self)

    def fake_stat(self: Path, *, follow_symlinks: bool = True) -> Any:
        key = str(self)
        if key in inodes:
            dev, ino, size = inodes[key]
            return _FakeStat(dev, ino, size)
        return real_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "resolve", fake_resolve)
    monkeypatch.setattr(Path, "stat", fake_stat)


def _build_command_factory(per_port: dict[int, list[str]]):
    """Return a build_command stub that returns the canned argv per port."""

    def _build(role_config: Any, port: int, **_kwargs: Any) -> list[str]:
        if port not in per_port:
            raise KeyError(f"no command fixture for port {port}")
        return per_port[port]

    return _build


def _fake_registry() -> Any:
    """Minimal registry stub — get_role(name) → object with .name."""

    class _Stub:
        def get_role(self, name: str) -> Any:
            return types.SimpleNamespace(name=name)

    return _Stub()


def test_collect_targets_dedupes_by_inode(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two servers pointing at the SAME physical file (same dev/ino).
    inodes = {"/models/shared.gguf": (1, 999, 36 * 1024**3)}
    _patch_path_resolution(monkeypatch, inodes)
    servers = [
        {"port": 8070, "roles": ["frontdoor"]},
        {"port": 8071, "roles": ["coder_escalation"]},
    ]
    build = _build_command_factory(
        {
            8070: ["llama-server", "-m", "/models/shared.gguf", "--port", "8070"],
            8071: ["llama-server", "-m", "/models/shared.gguf", "--port", "8071"],
        }
    )
    targets = stack_prewarm.collect_targets(servers, build, _fake_registry())
    assert len(targets) == 1
    entry = next(iter(targets.values()))
    assert sorted(entry["ports"]) == [8070, 8071]
    assert entry["roles"] == {"frontdoor", "coder_escalation"}
    assert entry["size_bytes"] == 36 * 1024**3


def test_collect_targets_keeps_distinct_inodes(monkeypatch: pytest.MonkeyPatch) -> None:
    inodes = {
        "/models/a.gguf": (1, 100, 10**9),
        "/models/b.gguf": (1, 200, 2 * 10**9),
        "/models/draft.gguf": (1, 300, 5 * 10**8),
    }
    _patch_path_resolution(monkeypatch, inodes)
    servers = [
        {"port": 8070, "roles": ["frontdoor"]},
        {"port": 8072, "roles": ["worker_general"]},
    ]
    build = _build_command_factory(
        {
            8070: ["llama-server", "-m", "/models/a.gguf"],
            8072: ["llama-server", "-m", "/models/b.gguf", "-md", "/models/draft.gguf"],
        }
    )
    targets = stack_prewarm.collect_targets(servers, build, _fake_registry())
    assert len(targets) == 3
    sizes = sorted(v["size_bytes"] for v in targets.values())
    assert sizes == [5 * 10**8, 10**9, 2 * 10**9]


def test_collect_targets_skips_unstatable_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Only one of the two referenced paths exists.
    inodes = {"/models/exists.gguf": (1, 42, 100)}
    _patch_path_resolution(monkeypatch, inodes)
    servers = [{"port": 8070, "roles": ["frontdoor"]}]
    build = _build_command_factory(
        {
            8070: [
                "llama-server",
                "-m",
                "/models/exists.gguf",
                "--mmproj",
                "/models/missing.gguf",
            ]
        }
    )
    targets = stack_prewarm.collect_targets(servers, build, _fake_registry())
    out = capsys.readouterr().out
    assert len(targets) == 1
    assert "/models/missing.gguf" in out
    assert "[prewarm] skip unreadable" in out


def test_collect_targets_skips_build_command_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inodes = {"/models/ok.gguf": (1, 7, 1)}
    _patch_path_resolution(monkeypatch, inodes)
    servers = [
        {"port": 8070, "roles": ["frontdoor"]},
        {"port": 9999, "roles": ["bogus"]},
    ]

    def build(role_config: Any, port: int, **_kwargs: Any) -> list[str]:
        if port == 9999:
            raise RuntimeError("simulated build failure")
        return ["llama-server", "-m", "/models/ok.gguf"]

    targets = stack_prewarm.collect_targets(servers, build, _fake_registry())
    out = capsys.readouterr().out
    assert len(targets) == 1
    assert "build_command failed" in out
    assert "9999" in out


def test_collect_targets_propagates_eval_batch_frontdoor_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inodes = {"/models/frontdoor.gguf": (1, 70, 10**9)}
    _patch_path_resolution(monkeypatch, inodes)
    observed: dict[str, Any] = {}

    def build(role_config: Any, port: int, **kwargs: Any) -> list[str]:
        observed.update({"role_config": role_config, "port": port, **kwargs})
        return ["llama-server", "-m", "/models/frontdoor.gguf"]

    targets = stack_prewarm.collect_targets(
        [
            {
                "port": 18070,
                "roles": ["eval_batch_frontdoor"],
                "eval_batch_frontdoor": True,
            }
        ],
        build,
        _fake_registry(),
    )

    assert len(targets) == 1
    assert observed["port"] == 18070
    assert observed["eval_batch_frontdoor_mode"] is True


# ---------------------------------------------------------------------------
# prewarm_file — subprocess contract
# ---------------------------------------------------------------------------


def test_prewarm_file_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stack_prewarm.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(stack_prewarm.subprocess, "run", fake_run)
    ok, elapsed, msg = stack_prewarm.prewarm_file(Path("/models/x.gguf"))
    assert ok is True
    assert msg == "ok"
    assert elapsed >= 0.0
    assert calls == [["/usr/bin/numactl", "--interleave=all", "/usr/bin/cat", "/models/x.gguf"]]


def test_prewarm_file_called_process_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stack_prewarm.shutil, "which", lambda binary: f"/usr/bin/{binary}")

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr=b"cat: missing")

    monkeypatch.setattr(stack_prewarm.subprocess, "run", fake_run)
    ok, elapsed, msg = stack_prewarm.prewarm_file(Path("/models/x.gguf"))
    assert ok is False
    assert "non-zero exit (1)" in msg
    assert "cat: missing" in msg
    assert elapsed >= 0.0


def test_prewarm_file_missing_numactl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        stack_prewarm.shutil,
        "which",
        lambda binary: None if binary == "numactl" else "/bin/" + binary,
    )
    ok, elapsed, msg = stack_prewarm.prewarm_file(Path("/models/x.gguf"))
    assert ok is False
    assert elapsed == 0.0
    assert "numactl" in msg


# ---------------------------------------------------------------------------
# prewarm_all — orchestration + skip handling
# ---------------------------------------------------------------------------


def _no_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace subprocess.run with a recorder that fails the test if invoked."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append(cmd)
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(stack_prewarm.subprocess, "run", fake_run)
    return calls


def test_prewarm_all_skips_via_cli_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_subprocess(monkeypatch)
    args = types.SimpleNamespace(skip_page_cache_prewarm=True)
    rc = stack_prewarm.prewarm_all([], lambda *a, **k: [], _fake_registry(), args=args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "SKIPPED" in out
    assert "--skip-page-cache-prewarm" in out


def test_prewarm_all_skips_via_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_subprocess(monkeypatch)
    monkeypatch.setenv(stack_prewarm.SKIP_ENV_VAR, "1")
    args = types.SimpleNamespace(skip_page_cache_prewarm=False)
    rc = stack_prewarm.prewarm_all([], lambda *a, **k: [], _fake_registry(), args=args)
    assert rc == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_prewarm_all_happy_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inodes = {
        "/models/big.gguf": (1, 1, 30 * 1024**3),
        "/models/small.gguf": (1, 2, 1 * 1024**3),
    }
    _patch_path_resolution(monkeypatch, inodes)
    monkeypatch.setattr(stack_prewarm.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(stack_prewarm.subprocess, "run", fake_run)
    servers = [
        {"port": 8070, "roles": ["frontdoor"]},
        {"port": 8090, "roles": ["embedder"]},
    ]
    build = _build_command_factory(
        {
            8070: ["llama-server", "-m", "/models/big.gguf"],
            8090: ["llama-server", "-m", "/models/small.gguf"],
        }
    )
    args = types.SimpleNamespace(skip_page_cache_prewarm=False)
    rc = stack_prewarm.prewarm_all(servers, build, _fake_registry(), args=args)
    out = capsys.readouterr().out
    assert rc == 0
    # Larger file warmed first.
    assert [c[-1] for c in calls] == ["/models/big.gguf", "/models/small.gguf"]
    assert "[1.5] Page-cache prewarm" in out
    assert "2 unique GGUF(s)" in out


def test_prewarm_all_returns_nonzero_when_any_warm_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inodes = {"/models/a.gguf": (1, 1, 1), "/models/b.gguf": (1, 2, 1)}
    _patch_path_resolution(monkeypatch, inodes)
    monkeypatch.setattr(stack_prewarm.shutil, "which", lambda binary: f"/usr/bin/{binary}")

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        if cmd[-1] == "/models/b.gguf":
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr=b"disk read error")
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(stack_prewarm.subprocess, "run", fake_run)
    servers = [
        {"port": 8070, "roles": ["frontdoor"]},
        {"port": 8085, "roles": ["ingest_long_context"]},
    ]
    build = _build_command_factory(
        {
            8070: ["llama-server", "-m", "/models/a.gguf"],
            8085: ["llama-server", "-m", "/models/b.gguf"],
        }
    )
    args = types.SimpleNamespace(skip_page_cache_prewarm=False)
    rc = stack_prewarm.prewarm_all(servers, build, _fake_registry(), args=args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL (non-zero exit (1): disk read error)" in out
    assert "OK in" in out


def test_prewarm_all_no_targets_reports_clean_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_subprocess(monkeypatch)
    args = types.SimpleNamespace(skip_page_cache_prewarm=False)
    rc = stack_prewarm.prewarm_all([], lambda *a, **k: [], _fake_registry(), args=args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "no GGUF targets resolved" in out

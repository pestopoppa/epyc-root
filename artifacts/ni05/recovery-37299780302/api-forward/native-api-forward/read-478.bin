"""Unit tests for LightOnOCR llama.cpp launch hygiene."""

from __future__ import annotations

from pathlib import Path

from src.services.lightonocr_llama_server import (
    _mtmd_subprocess_env,
    _resolve_mtmd_cli,
)


# `_resolve_mtmd_cli` selects a candidate by RUNNING it (`--version`) and
# matching `version: <build> (<commit>)` — exists()+X_OK is deliberately NOT a
# runnability check, because several build trees on this host carry an
# executable llama-mtmd-cli that dies at startup on a missing libomp.so. A
# fixture binary therefore has to answer the probe. This is the ratified
# production-consolidated-v8 identity.
_RUNNABLE_STUB = '#!/bin/sh\necho "version: 10107 (67a433bf)"\n'


def test_resolve_mtmd_cli_falls_back_when_default_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("LLAMA_MTMD_CLI", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_PATHS_LLAMA_MTMD", raising=False)

    llama_root = tmp_path / "llama.cpp"
    configured = llama_root / "build/bin/llama-mtmd-cli"
    fallback = llama_root / "build-v2/bin/llama-mtmd-cli"
    fallback.parent.mkdir(parents=True)
    fallback.write_text(_RUNNABLE_STUB)
    fallback.chmod(0o755)

    assert _resolve_mtmd_cli(str(configured)) == str(fallback)


def test_resolve_mtmd_cli_rejects_present_but_unrunnable_candidate(tmp_path, monkeypatch):
    """A candidate that exists and is +x but does not RUN must not be selected.

    This is the defect the probe was added to close: the configured path is
    kept so the failure surfaces at launch instead of silently running a
    wrong/broken binary.
    """
    monkeypatch.delenv("LLAMA_MTMD_CLI", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_PATHS_LLAMA_MTMD", raising=False)

    llama_root = tmp_path / "llama.cpp"
    configured = llama_root / "build/bin/llama-mtmd-cli"
    broken = llama_root / "build-v2/bin/llama-mtmd-cli"
    broken.parent.mkdir(parents=True)
    broken.write_text("#!/bin/sh\nexit 127\n")  # runs, prints no version
    broken.chmod(0o755)

    assert _resolve_mtmd_cli(str(configured)) == str(configured)


def test_resolve_mtmd_cli_preserves_explicit_override(monkeypatch):
    configured = "/missing/operator/llama-mtmd-cli"

    monkeypatch.setenv("ORCHESTRATOR_PATHS_LLAMA_MTMD", configured)
    monkeypatch.delenv("LLAMA_MTMD_CLI", raising=False)

    assert _resolve_mtmd_cli(configured) == configured


def test_mtmd_subprocess_env_prepends_cli_library_path(tmp_path, monkeypatch):
    cli = tmp_path / "build-v2/bin/llama-mtmd-cli"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/old/lib:/older/lib")

    env = _mtmd_subprocess_env(str(cli), threads=12)

    assert env["OMP_NUM_THREADS"] == "12"
    assert env["LD_LIBRARY_PATH"].split(":")[:3] == [
        str(cli.parent.resolve()),
        "/old/lib",
        "/older/lib",
    ]


def test_mtmd_subprocess_env_does_not_duplicate_cli_library_path(tmp_path, monkeypatch):
    cli_dir = tmp_path / "build-v2/bin"
    cli = cli_dir / "llama-mtmd-cli"
    cli_dir.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n")
    resolved_dir = str(Path(cli_dir).resolve())
    monkeypatch.setenv("LD_LIBRARY_PATH", f"{resolved_dir}:/old/lib")

    env = _mtmd_subprocess_env(str(cli), threads=8)

    assert env["LD_LIBRARY_PATH"].split(":").count(resolved_dir) == 1

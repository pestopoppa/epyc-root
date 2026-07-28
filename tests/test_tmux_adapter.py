"""C6 coverage using a disposable tmux session, never the live ``agent`` session.

The shell stand-in proves split text/Enter delivery and prompt-tail verification.
It intentionally does not model Codex's paste rendering; the adapter therefore
uses a conservative documented length cap and fails closed above it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py"


def _tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=15)


@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux unavailable")
def test_c6_nudge_submits_in_throwaway_session_and_rejects_oversize(
        tmp_path: Path) -> None:
    """C6: capture-confirmed split send/Enter, with a fail-loud long-message cap."""
    session = f"c6-submit-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    assert session != "agent"
    spec = importlib.util.spec_from_file_location(f"tmux_adapter_{session}", ADAPTER_PATH)
    assert spec and spec.loader
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    bus_root = tmp_path / "bus"
    for directory in ("heartbeats", "outbox", "inbox", "cursors", "tokens"):
        (bus_root / directory).mkdir(parents=True, exist_ok=True)
    adapter.BUS_ROOT = bus_root
    adapter.LEDGER = bus_root / "adapter-ledger.jsonl"
    (bus_root / "config.yaml").write_text(json.dumps({
        "roster": [{"id": "shell", "endpoint": f"tmux:{session}:shell"}],
        "flags": {"codex_sendkeys": "on"}, "caps": {"max_spawns_per_day": 0},
        "tmux": {"live_session": session, "allow_session_creation": False},
    }), encoding="utf-8")
    (bus_root / "heartbeats" / "shell.json").write_text(json.dumps({
        "agent": "shell", "state": "idle", "ts": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    try:
        # The stand-in clears its input echo after read, modelling a submitted
        # prompt whose text is no longer in the pane tail; it is not a Codex TUI.
        created = _tmux("new-session", "-d", "-s", session, "-n", "shell",
                        "sh", "-c", "printf '\\033[999;1H'; IFS= read -r line; "
                        "printf '\\033[2J\\033[HSUBMITTED\\n'; sleep 60")
        assert created.returncode == 0, created.stderr

        class Args:
            agent = "shell"
            message = "m" * adapter.MAX_NUDGE_MESSAGE_CHARS
            min_interval_s = 0.0
            dry_run = False
            quiet_s = 0.0
            heartbeat_max_age = 900.0
            settle_s = 0.10

        probe = adapter.probe(adapter.load_config(), "shell", 0.0, 900.0)
        assert "may fail closed" in probe["submission_verification"]
        assert adapter.cmd_nudge(Args()) == 0
        pane = _tmux("capture-pane", "-p", "-t", f"{session}:shell")
        assert pane.returncode == 0
        assert "SUBMITTED" in pane.stdout
        assert Args.message not in "\n".join(pane.stdout.splitlines()[-4:])
        assert len([line for line in adapter.LEDGER.read_text().splitlines() if line]) == 1

        Args.message = "x" * (adapter.MAX_NUDGE_MESSAGE_CHARS + 1)
        assert adapter.cmd_nudge(Args()) == adapter.EX_USAGE
        assert len([line for line in adapter.LEDGER.read_text().splitlines() if line]) == 1
    finally:
        _tmux("kill-session", "-t", session)


def test_c6_pending_prompt_tail_fails_without_success_ledger(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """C6: retained prompt text is a nonzero, unrecorded send failure."""
    spec = importlib.util.spec_from_file_location("tmux_adapter_pending", ADAPTER_PATH)
    assert spec and spec.loader
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"

    class Args:
        agent = "shell"
        message = "still-pending"
        min_interval_s = 0.0
        dry_run = False
        quiet_s = 0.0
        heartbeat_max_age = 900.0
        settle_s = 0.0

    monkeypatch.setattr(adapter, "load_config", lambda: {})
    monkeypatch.setattr(adapter, "probe", lambda *_args: {
        "nudge_ok": True, "target": "throwaway:shell", "seconds_since_last_nudge": None,
    })
    calls = iter([(0, ""), (0, Args.message), (0, ""), (0, Args.message)])
    monkeypatch.setattr(adapter, "_tmux", lambda *_args: next(calls))
    assert adapter.cmd_nudge(Args()) == adapter.EX_MISCONFIG
    assert not adapter.LEDGER.exists()

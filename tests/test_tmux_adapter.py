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
        assert Args.message not in "\n".join(pane.stdout.splitlines()[-adapter._INPUT_REGION_LINES:])
        assert len([line for line in adapter.LEDGER.read_text().splitlines() if line]) == 1

        Args.message = "x" * (adapter.MAX_NUDGE_MESSAGE_CHARS + 1)
        assert adapter.cmd_nudge(Args()) == adapter.EX_USAGE
        assert len([line for line in adapter.LEDGER.read_text().splitlines() if line]) == 1
    finally:
        _tmux("kill-session", "-t", session)


@pytest.mark.parametrize(
    ("overlay_name", "input_region"),
    [
        (
            "codex-plan-confirmation",
            "\n".join([
                "Codex ready", "› overlay-tolerant nudge", "",
                "Create a plan?", "shift + tab use Plan mode", "esc dismiss",
                "", "status: waiting",
            ]),
        ),
        (
            "claude-agent-picker",
            "\n".join([
                "Claude ready", "› overlay-tolerant nudge", "",
                "● main", "◯ general-purpose", "◯ research", "◯ code-review",
                "enter select", "esc dismiss",
            ]),
        ),
    ],
)
def test_c6_submission_state_accepts_text_in_decorated_input_region(
        overlay_name: str, input_region: str) -> None:
    """Model overlays, not their TUIs: pending text can sit above decorations."""
    spec = importlib.util.spec_from_file_location(f"tmux_adapter_{overlay_name}", ADAPTER_PATH)
    assert spec and spec.loader
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    fragment = adapter._pending_fragment("overlay-tolerant nudge")
    # The prior four-line tail predicate misses the editable line in both
    # layouts; the bounded lower input region still sees it.
    assert fragment not in "\n".join(input_region.splitlines()[-4:])
    assert adapter._submission_state(input_region, fragment) == "text_present"


def test_c6_text_absent_before_enter_fails_without_success_ledger(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """C6: genuinely absent text never sends Enter and reports did-not-land."""
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
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(adapter, "_tmux", lambda *args: (calls.append(args) or (0, "")))
    monkeypatch.setattr(adapter, "_input_region", lambda _target: ("● main\n◯ general-purpose", None))
    assert adapter.cmd_nudge(Args()) == adapter.EX_MISCONFIG
    assert calls == [("send-keys", "-l", "-t", "throwaway:shell", Args.message)]
    assert "did not land" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_c6_post_enter_pending_text_reports_unsubmitted(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """C6: text remaining after Enter is distinct from a did-not-land failure."""
    spec = importlib.util.spec_from_file_location("tmux_adapter_unsubmitted", ADAPTER_PATH)
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
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(adapter, "_tmux", lambda *args: (calls.append(args) or (0, "")))
    monkeypatch.setattr(adapter, "_input_region", lambda _target: (Args.message, None))
    assert adapter.cmd_nudge(Args()) == adapter.EX_MISCONFIG
    assert calls == [
        ("send-keys", "-l", "-t", "throwaway:shell", Args.message),
        ("send-keys", "-t", "throwaway:shell", "Enter"),
    ]
    assert "text present but unsubmitted" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_c6_paste_blob_reports_mangling_without_success_ledger(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """C6: a paste banner is a mangling failure, never submission evidence."""
    spec = importlib.util.spec_from_file_location("tmux_adapter_paste", ADAPTER_PATH)
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
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(adapter, "_tmux", lambda *args: (calls.append(args) or (0, "")))
    monkeypatch.setattr(adapter, "_input_region", lambda _target: ("[Pasted Content #1]", None))
    assert adapter.cmd_nudge(Args()) == adapter.EX_MISCONFIG
    assert calls == [("send-keys", "-l", "-t", "throwaway:shell", Args.message)]
    assert "paste blob" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()

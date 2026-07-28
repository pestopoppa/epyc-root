"""C6 coverage using a disposable tmux session, never the live ``agent`` session.

The predicate under test is CURSOR-ANCHORED: the composer is "everything up to
the terminal cursor", and a pending message is one the composer ENDS with. The
row-window predicate this replaced produced false refusals in normal operation
for two measured reasons, both covered below:

  * both TUIs soft-wrap the composer, and a wrap can fall inside the fragment,
    so raw substring matching fails on text that landed perfectly; and
  * both TUIs echo a SUBMITTED message into the transcript, so "text still
    visible after Enter" is the success rendering, not a failure.

That echo is REQUIRED evidence, not merely tolerated: post-Enter success is the
message having moved off the cursor while remaining on the pane. "Off the cursor"
alone would accept an Enter that a completion overlay consumed to rewrite the
composer, which is the original C6 fail-open wearing a different hat.

Calibration recorded in the module docstring of tmux_adapter.py was taken on
2026-07-28 against real disposable ``codex`` and ``claude`` panes.
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


def _load(tag: str):
    spec = importlib.util.spec_from_file_location(f"tmux_adapter_{tag}", ADAPTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=15)


class _Args:
    agent = "shell"
    message = "still-pending"
    min_interval_s = 0.0
    dry_run = False
    quiet_s = 0.0
    heartbeat_max_age = 900.0
    settle_s = 0.0


def _stub_nudge(adapter, monkeypatch, composer_states, tmp_path):
    """Wire cmd_nudge to a fake pane whose composer text is scripted.

    ``composer_states`` is consumed one entry per verification round; the last
    entry repeats, which models the bounded poll settling on a stable state.
    """
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    adapter._VERIFY_TIMEOUT_S = 0.0
    monkeypatch.setattr(adapter, "load_config", lambda: {})
    monkeypatch.setattr(adapter, "probe", lambda *_a: {
        "nudge_ok": True, "target": "throwaway:shell", "seconds_since_last_nudge": None,
    })
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(adapter, "_tmux", lambda *args: (calls.append(args) or (0, "")))
    seq = list(composer_states)

    def fake_composer(_target):
        return (seq.pop(0) if len(seq) > 1 else seq[0]), None

    monkeypatch.setattr(adapter, "_composer_text", fake_composer)
    return calls


# --------------------------------------------------------------------------
# Predicate-level: the three diagnostic states, and overlay tolerance.
# --------------------------------------------------------------------------

def test_bare_prompt_pending_text_is_text_present() -> None:
    adapter = _load("bare")
    message = "restart the collector"
    composer = "Codex ready\n\n› " + message   # cursor sits right after it
    assert adapter._submission_state(composer, adapter._pending_fragment(message)) == "text_present"


@pytest.mark.parametrize(
    ("overlay_name", "decoration"),
    [
        ("codex-plan-confirmation",
         ["Create a plan?", "shift + tab use Plan mode", "esc dismiss"]),
        ("claude-agent-picker",
         ["● main", "○ general-purpose  19m 7s · ↓ 286.3k tokens",
          "enter select", "esc dismiss"]),
        ("codex-at-picker",
         ["  Business Review      Create presentations", "  CI Debug   Debug failing checks",
          "enter insert · esc close"]),
    ],
)
def test_overlay_below_the_cursor_is_still_text_present(
        overlay_name: str, decoration: list[str]) -> None:
    """Measured: overlays render BELOW the cursor, so they cannot displace it.

    The composer text (everything up to the cursor) is unaffected by whatever the
    overlay draws underneath, which is why this predicate cannot false-refuse the
    way a "last N rows" window did.
    """
    adapter = _load(overlay_name)
    message = "overlay-tolerant nudge"
    composer = "Claude ready\n\n❱ " + message
    assert adapter._submission_state(composer, adapter._pending_fragment(message)) == "text_present"
    # The decoration exists in the pane but strictly after the cursor, so it is
    # simply not part of the composer text at all.
    assert all(line not in composer for line in decoration)


def test_soft_wrapped_composer_is_still_text_present() -> None:
    """Measured false negative: TUI soft-wrap can split the fragment mid-way."""
    adapter = _load("wrap")
    message = "please rerun the cadence fix and report back " + "".join(
        f"step{i:03d}-" for i in range(20))
    # The wrap deliberately falls INSIDE the 60-char tail fragment.
    split = len(message) - 30
    wrapped = "› " + message[:40] + "\n  " + message[40:split] + "\n  " + message[split:]
    fragment = adapter._pending_fragment(message)
    assert fragment not in wrapped            # raw match fails — the old predicate
    assert adapter._submission_state(wrapped, fragment) == "text_present"


@pytest.mark.parametrize("banner", ["[Pasted Content 1016 chars]", "[Pasted text #5]"])
def test_paste_banner_at_the_cursor_is_paste_blob(banner: str) -> None:
    """Both TUIs' banners are recognised; Codex truncates such blobs at 1024."""
    adapter = _load("blob" + str(len(banner)))
    composer = "Codex ready\n\n› " + banner
    assert adapter._submission_state(composer, adapter._pending_fragment("m" * 900)) == "paste_blob"


def test_transcript_echo_after_enter_is_text_echoed() -> None:
    """THE regression that made the guard unusable.

    Both TUIs echo the submitted message into the transcript, so it is still on
    the pane after a *successful* Enter. Anchoring at the cursor classifies that
    as ``text_echoed`` (submitted), where a pane-wide search called it pending.
    """
    adapter = _load("echo")
    message = "restart the collector"
    composer = "› " + message + "\n● OK\n\n› "
    assert message in composer
    assert adapter._submission_state(composer, adapter._pending_fragment(message)) == "text_echoed"


def test_an_enter_that_rewrote_the_composer_is_not_submission() -> None:
    """Enter consumed by an overlay REWRITES the tail — it does not submit.

    The composer no longer ends with the message, so an "absence means submitted"
    rule would record a nudge that was never sent. The message is not echoed
    anywhere either, which is precisely what separates the two.
    """
    adapter = _load("rewrite")
    message = "restart the collector on the quarter fleet"
    fragment = adapter._pending_fragment(message)
    pending = "› " + message                                    # overlay list below
    rewritten = "› restart the collector on the quarter deployment"
    assert adapter._submission_state(pending, fragment) == "text_present"
    assert adapter._submission_state(rewritten, fragment) == "text_absent"


def test_whitespace_tail_message_has_a_matchable_fragment() -> None:
    """A fragment of pure whitespace normalises to "" and matches EVERY pane.

    ``endswith("")`` would make the pre-Enter gate pass unconditionally and fire
    Enter into a pane that never received the text.
    """
    adapter = _load("wstail")
    fragment = adapter._pending_fragment("do the thing" + " " * 60)
    assert adapter._normalise(fragment)
    assert adapter._submission_state("an unrelated pane", fragment) == "text_absent"
    # And the degenerate all-whitespace case is unmatchable, so it must not match.
    assert adapter._submission_state("an unrelated pane", "   ") == "text_absent"


def test_unresponsive_modal_is_text_absent() -> None:
    """Codex backtrack mode (measured): typed text goes nowhere. Must refuse."""
    adapter = _load("modal")
    composer = "↑/↓ to scroll   pgup/pgdn to page\nq to quit   enter to edit message\n"
    assert adapter._submission_state(composer, adapter._pending_fragment("do the thing")) \
        == "text_absent"


# --------------------------------------------------------------------------
# cmd_nudge level: each state must produce its own diagnostic and fail closed.
# --------------------------------------------------------------------------

def test_nudge_succeeds_with_an_overlay_present(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("ok_overlay")
    _Args.message = "drain the bus and pick up RP-5"
    pending = "› " + _Args.message      # overlay rows live below the cursor
    submitted = "› " + _Args.message + "\n● working\n\n› "
    calls = _stub_nudge(adapter, monkeypatch, [pending, submitted], tmp_path)
    assert adapter.cmd_nudge(_Args()) == 0
    assert calls == [
        ("send-keys", "-l", "-t", "throwaway:shell", "--", _Args.message),
        ("send-keys", "-t", "throwaway:shell", "Enter"),
    ]
    assert "nudged shell" in capsys.readouterr().out
    assert len([ln for ln in adapter.LEDGER.read_text().splitlines() if ln]) == 1


def test_nudge_succeeds_on_a_bare_prompt(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _load("ok_bare")
    _Args.message = "status please"
    calls = _stub_nudge(adapter, monkeypatch,
                        ["$ " + _Args.message, "$ " + _Args.message + "\nSUBMITTED\n$ "], tmp_path)
    assert adapter.cmd_nudge(_Args()) == 0
    assert len(calls) == 2
    assert adapter.LEDGER.exists()


def test_text_absent_before_enter_refuses_without_sending_enter(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("absent")
    _Args.message = "still-pending"
    calls = _stub_nudge(adapter, monkeypatch, ["q to quit   enter to edit message"], tmp_path)
    assert adapter.cmd_nudge(_Args()) == adapter.EX_MISCONFIG
    assert calls == [("send-keys", "-l", "-t", "throwaway:shell", "--", _Args.message)]
    assert "did not land in the composer" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_paste_blob_before_enter_refuses_with_its_own_diagnostic(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("blobstate")
    _Args.message = "still-pending"
    calls = _stub_nudge(adapter, monkeypatch, ["› [Pasted Content 1024 chars]"], tmp_path)
    assert adapter.cmd_nudge(_Args()) == adapter.EX_MISCONFIG
    assert calls == [("send-keys", "-l", "-t", "throwaway:shell", "--", _Args.message)]
    assert "paste blob" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_swallowed_enter_reports_unsubmitted_and_fails_closed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The ORIGINAL C6 defect: Enter absorbed, text still pending. Never succeed."""
    adapter = _load("swallow")
    _Args.message = "still-pending"
    pending = "› " + _Args.message
    calls = _stub_nudge(adapter, monkeypatch, [pending, pending], tmp_path)
    assert adapter.cmd_nudge(_Args()) == adapter.EX_MISCONFIG
    assert calls == [
        ("send-keys", "-l", "-t", "throwaway:shell", "--", _Args.message),
        ("send-keys", "-t", "throwaway:shell", "Enter"),
    ]
    assert "text present but unsubmitted" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_enter_that_rewrote_the_composer_fails_closed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """C6's second door: Enter rewrote the composer instead of submitting.

    The message leaves the cursor, so an absence-based rule would have called this
    a successful nudge and written the ledger. It is not sent, and it must refuse.
    """
    adapter = _load("rewrite_nudge")
    _Args.message = "restart the collector on the quarter fleet"
    pending = "› " + _Args.message
    rewritten = "› restart the collector on the quarter deployment"
    _stub_nudge(adapter, monkeypatch, [pending, rewritten], tmp_path)
    assert adapter.cmd_nudge(_Args()) == adapter.EX_MISCONFIG
    assert "rewrote the composer" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


@pytest.mark.parametrize("message", [
    "/wrap-up the session please",     # slash menu: Enter accepts a command
    "!ls /workspace",                  # Claude bash mode: Enter EXECUTES
    "#remember the freeze",            # Claude memory mode
    "please read @scripts/coordination/tmux_adapter.py",   # Codex file picker
])
def test_composer_mode_triggers_are_refused_before_anything_is_typed(
        message: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The un-detectable failure is prevented instead of detected.

    With a picker open, Enter accepts a completion that EXTENDS the typed text —
    the message is then still on the pane and no longer at the cursor, which is
    byte-for-byte what a successful submission looks like. Since no pane check can
    separate them after the fact, the trigger never gets typed.
    """
    adapter = _load("modeprefix" + str(abs(hash(message))))
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"

    class Args(_Args):
        pass
    Args.message = message
    assert adapter.cmd_nudge(Args()) == adapter.EX_USAGE
    assert "Enter accepts a completion" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_one_frame_of_absence_during_repaint_is_not_submission(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A half-drawn repaint frame must not be believed on a single sample."""
    adapter = _load("flicker")
    _Args.message = "still-pending"
    pending = "› " + _Args.message
    echoed = "› " + _Args.message + "\n● OK\n\n› "
    _stub_nudge(adapter, monkeypatch, [pending, echoed, pending], tmp_path)
    adapter._VERIFY_TIMEOUT_S = 0.3          # allow the poll to see the second frame
    assert adapter.cmd_nudge(_Args()) == adapter.EX_MISCONFIG
    assert "text present but unsubmitted" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_unreadable_pane_fails_closed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("unreadable")
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    monkeypatch.setattr(adapter, "load_config", lambda: {})
    monkeypatch.setattr(adapter, "probe", lambda *_a: {
        "nudge_ok": True, "target": "throwaway:shell", "seconds_since_last_nudge": None,
    })
    monkeypatch.setattr(adapter, "_tmux", lambda *_a: (0, ""))
    monkeypatch.setattr(adapter, "_composer_text", lambda _t: (None, "no cursor position"))
    assert adapter.cmd_nudge(_Args()) == adapter.EX_MISCONFIG
    assert "unavailable before Enter" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


# --------------------------------------------------------------------------
# Length behaviour.
# --------------------------------------------------------------------------

def test_length_cap_is_the_calibrated_value_and_chunking_stays_sub_threshold() -> None:
    adapter = _load("caps")
    # Measured single-burst paste thresholds: Claude 801-805, Codex 1001.
    assert adapter.NUDGE_CHUNK_CHARS <= 400
    assert adapter.NUDGE_CHUNK_CHARS * 2 <= 800
    # The gap is load bearing: zero-gap chunks re-coalesce into one burst.
    assert adapter.NUDGE_CHUNK_DELAY_S > 0
    # Raised off 240 on that evidence; still a policy ceiling well under the
    # 12,000 chars verified end-to-end on both TUIs.
    assert adapter.MAX_NUDGE_MESSAGE_CHARS == 4000


def test_long_message_is_sent_in_sub_threshold_chunks(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _load("chunked")
    _Args.message = "y" * 1500          # would blob on both TUIs in one burst
    monkeypatch.setattr(adapter, "NUDGE_CHUNK_DELAY_S", 0.0)
    pending = "› " + _Args.message
    echoed = "› " + _Args.message + "\n● working\n\n› "
    calls = _stub_nudge(adapter, monkeypatch, [pending, echoed], tmp_path)
    assert adapter.cmd_nudge(_Args()) == 0
    sends = [c for c in calls if c[1] == "-l"]
    assert len(sends) == 4
    assert all(len(c[-1]) <= adapter.NUDGE_CHUNK_CHARS for c in sends)
    assert "".join(c[-1] for c in sends) == _Args.message


def test_oversize_and_multiline_messages_are_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("oversize")
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    _Args.message = "z" * (adapter.MAX_NUDGE_MESSAGE_CHARS + 1)
    assert adapter.cmd_nudge(_Args()) == adapter.EX_USAGE
    assert "calibrated policy cap" in capsys.readouterr().err
    # A newline is the submit key: it would send a partial nudge.
    _Args.message = "line one\nline two"
    assert adapter.cmd_nudge(_Args()) == adapter.EX_USAGE
    assert "newline" in capsys.readouterr().err
    assert not adapter.LEDGER.exists()


def test_a_242_char_message_is_now_accepted(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The concrete absurdity that motivated recalibration: 2 chars over 240."""
    adapter = _load("242")
    _Args.message = "n" * 242
    monkeypatch.setattr(adapter, "NUDGE_CHUNK_DELAY_S", 0.0)
    _stub_nudge(adapter, monkeypatch,
                ["› " + _Args.message, "› " + _Args.message + "\n● OK\n\n› "], tmp_path)
    assert adapter.cmd_nudge(_Args()) == 0


# --------------------------------------------------------------------------
# End-to-end against a real, disposable tmux pane. Never the live `agent`.
# --------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux unavailable")
def test_c6_nudge_submits_in_throwaway_session(tmp_path: Path) -> None:
    session = f"c6-submit-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    assert session != "agent"
    adapter = _load(session.replace("-", "_"))
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
        # `read` echoes typed input at the cursor, and on submit the echoed line
        # STAYS on the pane while the cursor moves past it — the same composer /
        # transcript-echo relationship both TUIs exhibit, which is what the
        # post-Enter check requires as positive evidence. (An earlier version of
        # this fixture cleared the screen on submit; that models no real TUI and
        # would hide a regression in exactly the predicate under test.)
        created = _tmux("new-session", "-d", "-s", session, "-n", "shell", "-x", "120", "-y", "24",
                        "sh", "-c", "printf '\\033[2J\\033[H'; IFS= read -r line; "
                        "printf 'SUBMITTED\\n'; sleep 60")
        assert created.returncode == 0, created.stderr

        class Args(_Args):
            settle_s = 0.30
            # Comfortably past the old 240 cap; chunking keeps every burst small.
            message = "e2e-nudge " + "q" * 600

        probe = adapter.probe(adapter.load_config(), "shell", 0.0, 900.0)
        assert "cursor-anchored" in probe["submission_verification"]
        assert adapter.cmd_nudge(Args()) == 0
        pane = _tmux("capture-pane", "-p", "-t", f"{session}:shell")
        assert pane.returncode == 0
        assert "SUBMITTED" in pane.stdout
        assert len([ln for ln in adapter.LEDGER.read_text().splitlines() if ln]) == 1
    finally:
        _tmux("kill-session", "-t", session)
        assert _tmux("has-session", "-t", session).returncode != 0


@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux unavailable")
def test_c6_refuses_when_the_pane_never_accepts_the_text(tmp_path: Path) -> None:
    """A pane that swallows input must be refused, not reported as nudged."""
    session = f"c6-deaf-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    assert session != "agent"
    adapter = _load(session.replace("-", "_"))
    bus_root = tmp_path / "bus"
    for directory in ("heartbeats", "outbox", "inbox", "cursors"):
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
        # No reader, echo off: keystrokes are discarded, exactly like a modal.
        created = _tmux("new-session", "-d", "-s", session, "-n", "shell", "-x", "120", "-y", "24",
                        "sh", "-c", "stty -echo; printf '\\033[2J\\033[HDEAF\\n'; sleep 120")
        assert created.returncode == 0, created.stderr

        class Args(_Args):
            settle_s = 0.30
            message = "this text can never land"

        assert adapter.cmd_nudge(Args()) == adapter.EX_MISCONFIG
        assert not adapter.LEDGER.exists()
    finally:
        _tmux("kill-session", "-t", session)
        assert _tmux("has-session", "-t", session).returncode != 0

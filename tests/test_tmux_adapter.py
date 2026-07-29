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
        "flags": {"codex_sendkeys": "on"}, "caps": {"max_concurrent_mains": 0},
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
        "flags": {"codex_sendkeys": "on"}, "caps": {"max_concurrent_mains": 0},
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


# --------------------------------------------------------------------------
# C9 — the spawn cap bounds SIMULTANEOUS mains, not spawn actions per day.
#
# The defect: `caps.max_spawns_per_day` counted `spawn` rows in the ledger for
# today, so killing a main never returned its slot. Observed 2026-07-28 with
# three spawn rows and only two mains alive — further spawns refused at 3/3 with
# real capacity to spare, which also penalises the lifecycle rule that says an
# idle session should be closed.
#
# The one thing these must never do is fail OPEN: C3, C6 and C8 in this same
# module were all fail-open defects, so an uncountable live set refuses.
# --------------------------------------------------------------------------

C9_CONFIG = {
    "roster": [
        # Roster id and window name differ — the live config's `codex` lives in
        # window `codex-inference`. Counting window names against roster ids
        # naively would miss it and invent a free slot.
        {"id": "codex", "endpoint": "tmux:agent:codex-inference"},
        {"id": "coordinator-agent", "endpoint": "monitor:file"},
        {"id": "claude-gpu-lane", "endpoint": "tmux:agent"},
        {"id": "retired-main", "endpoint": "monitor:file"},
    ],
    "tmux": {"live_session": "agent", "allow_session_creation": False},
    "caps": {"max_concurrent_mains": 6},
}

# htop/btop/fish are windows in the same session and are NOT mains.
# `#{window_index}\t#{window_name}`, the real -F format: C14 resolves index
# endpoints too, so the count can no longer be taken from names alone.
C9_WINDOWS = ("0\tcodex-inference\n1\thtop\n2\tbtop\n3\tfish\n"
              "4\tcoordinator-agent\n5\tclaude-gpu-lane")


def _c9_adapter(tag: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                windows: str | None = C9_WINDOWS, config: dict | None = None):
    """An adapter whose tmux answers list-windows from a string. None => failure."""
    adapter = _load("c9_" + tag)
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    monkeypatch.setattr(adapter, "load_config", lambda: config or C9_CONFIG)

    def fake_tmux(*args: str) -> tuple[int, str]:
        if args[0] == "list-windows":
            if windows is None:
                return 1, "can't find session: agent"
            return 0, windows
        if args[0] == "has-session":
            return 0, ""
        return 0, ""

    monkeypatch.setattr(adapter, "_tmux", fake_tmux)
    return adapter


class _SpawnArgs:
    agent = "new-main"
    command = "true"
    dry_run = True


def test_live_mains_counts_roster_windows_including_renamed_ones(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    adapter = _c9_adapter("count", monkeypatch, tmp_path)
    ids, why = adapter.live_mains(C9_CONFIG)
    assert ids == {"codex", "coordinator-agent", "claude-gpu-lane"}
    assert "3 roster main(s) live" in why
    # Neither a tool window nor a roster row with no window is a live main.
    assert "htop" not in ids and "retired-main" not in ids


def test_a_window_index_endpoint_now_resolves_against_the_index(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """C14: `tmux:agent:3` is an INDEX and is resolved as one.

    Before C14 it contributed no name, so a main living at `tmux:agent:3` was
    invisible to the count — which lowers `len(ids)` and hands out an occupied
    slot. The window here is named `other`, so only index resolution can find it.
    """
    config = {"roster": [{"id": "indexed", "endpoint": "tmux:agent:3"}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 2}}
    adapter = _c9_adapter("index", monkeypatch, tmp_path, windows="3\tother", config=config)
    assert adapter.parse_endpoint_window("tmux:agent:3") == ("index", "3", None)
    assert adapter.live_mains(config)[0] == {"indexed"}
    # An index that matches nothing live is simply not live — not a refusal.
    adapter2 = _c9_adapter("index2", monkeypatch, tmp_path, windows="9\tother", config=config)
    assert adapter2.live_mains(config)[0] == set()


def test_a_pane_suffixed_endpoint_resolves_to_its_window(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """C14: `.0` is a pane, not a window — strip it, then resolve name or index."""
    adapter = _load("c14_pane")
    assert adapter.parse_endpoint_window("tmux:agent:win.0") == ("name", "win", None)
    assert adapter.parse_endpoint_window("tmux:agent:3.1") == ("index", "3", None)
    config = {"roster": [{"id": "paned", "endpoint": "tmux:agent:win.0"}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 2}}
    a2 = _c9_adapter("pane", monkeypatch, tmp_path, windows="0\twin", config=config)
    assert a2.live_mains(config)[0] == {"paned"}


@pytest.mark.parametrize("endpoint", ["tmux:agent:a:b", "tmux:agent:.0"])
def test_an_unreadable_endpoint_refuses_the_whole_count(
        endpoint: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    """C14's core: uninterpretable is NOT absent.

    Skipping a row this cannot parse would shrink the count, which RELAXES the cap
    and hands out a slot that is occupied — the capacity-inventing direction. So an
    endpoint that cannot be read refuses the entire count, and spawn refuses with it.
    """
    config = {"roster": [{"id": "readable", "endpoint": "tmux:agent"},
                         {"id": "broken", "endpoint": endpoint}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 5}}
    adapter = _c9_adapter("unreadable" + str(len(endpoint)), monkeypatch, tmp_path,
                          windows="0\treadable", config=config)
    ids, why = adapter.live_mains(config)
    assert ids is None
    assert "broken" in why and "treating the row as absent" in why
    assert adapter.cmd_spawn(_SpawnArgs()) == adapter.EX_BLOCKED
    assert "cannot determine how many mains are live" in capsys.readouterr().err


def test_ambiguous_window_ownership_refuses(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Two roster rows claiming one window: which main is live is a guess."""
    config = {"roster": [{"id": "one", "endpoint": "tmux:agent:shared"},
                         {"id": "shared", "endpoint": "tmux:agent"}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 5}}
    adapter = _c9_adapter("ambig", monkeypatch, tmp_path, windows="0\tshared", config=config)
    ids, why = adapter.live_mains(config)
    assert ids is None and "ambiguous" in why


def test_an_unparseable_window_row_refuses_rather_than_counting(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A list-windows line without the tab is unreadable, not an empty session."""
    adapter = _c9_adapter("badrow", monkeypatch, tmp_path, windows="no-tab-here")
    ids, why = adapter.live_mains(C9_CONFIG)
    assert ids is None and "unreadable list-windows row" in why


def test_dead_panes_are_not_excluded_from_the_count(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """fable-auditor's caution: never subtract windows on a pane_dead read.

    A dead pane still holds a window. Excluding those would shrink the count, and
    if the pane_dead read ever misreported, the error polarity would flip back
    toward inventing capacity. The adapter must not consult pane_dead here at all.
    """
    adapter = _load("c14_deadpane")
    source = ADAPTER_PATH.read_text()
    live_mains_src = source.split("def live_mains(")[1].split("\ndef ")[0]
    assert "pane_dead" not in live_mains_src.split('"""')[2], \
        "live_mains must not filter on pane_dead — that is the capacity-inventing direction"
    assert adapter.live_mains.__doc__ and "DEAD PANES STILL COUNT" in adapter.live_mains.__doc__


def test_killing_a_main_returns_its_slot_even_with_spawns_in_the_ledger(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    """THE C9 defect. Three spawn rows today, two mains alive, cap 3 => allowed."""
    config = dict(C9_CONFIG, caps={"max_concurrent_mains": 3})
    adapter = _c9_adapter("slotback", monkeypatch, tmp_path,
                          windows="0\tcodex-inference\n5\tclaude-gpu-lane", config=config)
    today = datetime.now(timezone.utc).date().isoformat()
    adapter.LEDGER.write_text("".join(
        json.dumps({"ts": f"{today}T0{i}:00:00+00:00", "kind": "spawn",
                    "agent": a, "detail": "d"}) + "\n"
        for i, a in enumerate(("codex-bus-tests", "claude-gpu-lane", "fable-auditor"))),
        encoding="utf-8")
    config["roster"].append({"id": "new-main", "endpoint": "tmux:agent"})
    try:
        assert adapter.cmd_spawn(_SpawnArgs()) == 0        # would have been 2 before C9
        assert "would create window agent:new-main" in capsys.readouterr().out
    finally:
        config["roster"].pop()


def test_spawn_refuses_at_the_concurrency_cap(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    config = dict(C9_CONFIG, caps={"max_concurrent_mains": 3},
                  roster=C9_CONFIG["roster"] + [{"id": "new-main", "endpoint": "tmux:agent"}])
    adapter = _c9_adapter("atcap", monkeypatch, tmp_path, config=config)
    assert adapter.cmd_spawn(_SpawnArgs()) == adapter.EX_BLOCKED
    err = capsys.readouterr().err
    assert "3/3 mains already live" in err
    assert "close an idle main and the slot returns" in err


def test_spawn_refuses_to_duplicate_a_main_that_is_already_live(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _c9_adapter("dup", monkeypatch, tmp_path)

    class Args(_SpawnArgs):
        agent = "claude-gpu-lane"
    assert adapter.cmd_spawn(Args()) == adapter.EX_BLOCKED
    assert "already live" in capsys.readouterr().err


@pytest.mark.parametrize(("windows", "expect_in_err"), [
    (None, "cannot determine how many mains are live"),        # tmux/session gone
])
def test_an_uncountable_live_set_fails_closed(
        windows: str | None, expect_in_err: str, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """tmux unreachable or the session absent must REFUSE, never assume zero.

    "I could not count" is not "nothing is running". C3, C6 and C8 in this module
    were all fail-open defects; this is the branch that would have been a fourth.
    """
    adapter = _c9_adapter("failclosed", monkeypatch, tmp_path, windows=windows)
    assert adapter.live_mains(C9_CONFIG)[0] is None
    assert adapter.cmd_spawn(_SpawnArgs()) == adapter.EX_BLOCKED
    assert expect_in_err in capsys.readouterr().err


def test_an_empty_roster_is_uncountable_rather_than_zero(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = {"roster": [], "tmux": {"live_session": "agent"},
              "caps": {"max_concurrent_mains": 3}}
    adapter = _c9_adapter("noroster", monkeypatch, tmp_path, config=config)
    ids, why = adapter.live_mains(config)
    assert ids is None and "no ids" in why


def test_the_legacy_daily_key_is_refused_not_reinterpreted(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    """DECIDED: the old key fails closed for one release, it is not read.

    `max_spawns_per_day: 6` authorised six spawn ACTIONS in a day. Reading that
    same 6 as six SIMULTANEOUS mains would grant concurrency the operator never
    approved — more permissive than the old behaviour, i.e. a fail-open, which is
    the one thing this module may not add. The fix is a one-line config edit.
    """
    config = dict(C9_CONFIG, caps={"max_spawns_per_day": 6})
    adapter = _c9_adapter("legacy", monkeypatch, tmp_path, config=config)
    cap, why = adapter.resolve_spawn_cap(config["caps"])
    assert cap is None
    assert "is NOT read as a fallback" in why
    assert adapter.cmd_spawn(_SpawnArgs()) == adapter.EX_MISCONFIG
    assert "max_concurrent_mains" in capsys.readouterr().err


def test_an_absent_or_unparseable_cap_refuses(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    adapter = _load("c9_capmissing")
    assert adapter.resolve_spawn_cap({})[0] is None
    assert adapter.resolve_spawn_cap({"max_concurrent_mains": "lots"})[0] is None
    assert adapter.resolve_spawn_cap({"max_concurrent_mains": 6})[0] == 6


def test_probe_reports_live_mains_and_marks_the_daily_count_as_history(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    adapter = _c9_adapter("probe", monkeypatch, tmp_path)
    adapter.BUS_ROOT = tmp_path
    p = adapter.probe(C9_CONFIG, "codex", 0.0, 900.0)
    assert p["live_mains_count"] == 3
    assert p["spawn_cap_key"] == "max_concurrent_mains"
    assert "spawns_today_history_only" in p and "spawns_today" not in p


@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux unavailable")
def test_c9_closing_a_window_returns_the_slot_in_a_throwaway_session(tmp_path: Path) -> None:
    """End-to-end proof against real tmux, in a disposable session.

    Spawn to the cap, then CLOSE one main: the next spawn must succeed. Under the
    ledger-counting cap it stayed refused for the rest of the day.
    """
    session = f"c9-cap-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    assert session != "agent"
    adapter = _load(session.replace("-", "_"))
    bus_root = tmp_path / "bus"
    for directory in ("heartbeats", "outbox", "inbox", "cursors"):
        (bus_root / directory).mkdir(parents=True, exist_ok=True)
    adapter.BUS_ROOT = bus_root
    adapter.LEDGER = bus_root / "adapter-ledger.jsonl"
    (bus_root / "config.yaml").write_text(json.dumps({
        "roster": [{"id": "main-a", "endpoint": f"tmux:{session}"},
                   {"id": "main-b", "endpoint": f"tmux:{session}"}],
        "flags": {"codex_sendkeys": "on"}, "caps": {"max_concurrent_mains": 1},
        "tmux": {"live_session": session, "allow_session_creation": False},
    }), encoding="utf-8")
    try:
        created = _tmux("new-session", "-d", "-s", session, "-n", "holder", "sleep 300")
        assert created.returncode == 0, created.stderr

        class A:
            agent = "main-a"
            command = "sleep 300"
            dry_run = False
        assert adapter.cmd_spawn(A()) == 0                       # 0/1 live -> allowed

        class B(A):
            agent = "main-b"
        assert adapter.cmd_spawn(B()) == adapter.EX_BLOCKED      # 1/1 live -> refused

        assert _tmux("kill-window", "-t", f"{session}:main-a").returncode == 0
        assert adapter.cmd_spawn(B()) == 0                       # slot returned
        names = _tmux("list-windows", "-t", session, "-F", "#{window_name}").stdout.split()
        assert "main-b" in names and "main-a" not in names
    finally:
        _tmux("kill-session", "-t", session)
        assert _tmux("has-session", "-t", session).returncode != 0

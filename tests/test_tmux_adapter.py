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
    # C30(b) added a post-spawn survival re-check. Unit tests must never sleep for it —
    # a suite that waits 2s per spawn is a suite people stop running.
    adapter.SPAWN_SETTLE_S = 0.0
    monkeypatch.setattr(adapter, "load_config", lambda: config or C9_CONFIG)
    spawned: list[str] = []

    def fake_tmux(*args: str) -> tuple[int, str]:
        if args[0] == "list-windows":
            if windows is None:
                return 1, "can't find session: agent"
            # C30(b): a window this fake CREATED must then be visible, or every spawn
            # test reads as "the window died instantly" and passes for the wrong reason.
            extra = "".join(f"\n9\t{n}" for n in spawned)
            return 0, windows + extra
        if args[0] == "new-window":
            spawned.append(args[args.index("-n") + 1])
            return 0, ""
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


# ---------------------------------------------------------------- C24 containment


def _tmux_semantics(windows: list[tuple[str, str]], *, current: int = 0,
                    session: str = "agent"):
    """A tmux stand-in that reproduces the two behaviours that make C24 subtle.

    Fidelity is the point — a fake that simply fails on a miss would make the
    invariant below pass vacuously, and the real failures came from tmux SUCCEEDING:

      * `display-message -t sess:<miss>` exits **0** and falls back to the session's
        CURRENT window (measured 2026-07-27); and
      * with the session absent it exits **0 with EMPTY output** (measured
        2026-07-29) — which is what the pre-C32 digit exemption turned into a
        positive, "(verified)" resolution.
    """
    def fake_tmux(*args: str) -> tuple[int, str]:
        if args[0] == "has-session":
            return (0, "") if args[-1] == session else (1, f"can't find session: {args[-1]}")
        if args[0] == "list-windows":
            if args[args.index("-t") + 1] != session:
                return 1, f"can't find session: {args[args.index('-t') + 1]}"
            return 0, "\n".join(f"{i}\t{n}" for i, n in windows)
        if args[0] == "display-message":
            target = args[args.index("-t") + 1]
            sess, _, want = target.partition(":")
            if sess != session:
                return 0, ""                       # exits 0, says nothing
            for i, n in windows:
                if want in (i, n):
                    return 0, f"{i}\t{n}"
            i, n = windows[current]                # tmux's silent fallback
            return 0, f"{i}\t{n}"
        return 0, ""
    return fake_tmux


_C24_WINDOWS = [("0", "operator"), ("1", "codex-inference"), ("2", "htop")]

# Every way live_mains is known to lose sight of a live main, plus the C32 shape.
_C24_DRIFT = [
    ("renamed-window-stale-endpoint", "tmux:agent:codex-OLDNAME"),
    ("endpoint-names-absent-window", "tmux:agent:gone"),
    ("no-window-component-no-matching-name", "tmux:agent"),
    ("index-endpoint-out-of-range", "tmux:agent:99"),
    ("pane-suffixed-window-gone", "tmux:agent:gone.0"),
]
# NOT in the list: `tmux:some-other-session:<name>`. live_mains applies the endpoint
# match even across sessions, deliberately — "where there is a choice, OVERCOUNT" —
# so that is the safe direction, and it gets its own test below rather than being
# quietly dropped from the drift set.


@pytest.mark.parametrize("label,endpoint", _C24_DRIFT, ids=[d[0] for d in _C24_DRIFT])
def test_c24_undercount_implies_resolve_target_refuses(
        monkeypatch: pytest.MonkeyPatch, label: str, endpoint: str) -> None:
    """C24's real containment invariant, pinned.

    `cmd_spawn` overwrites a stale heartbeat having "proved" the id is not live via
    `args.agent in ids`. That proof is NOT sound — live_mains can undercount without
    refusing — so the reset really can land on a genuinely live main, clearing both
    heartbeat blockers at once on a detached session where quiet_check is skipped.

    What makes it safe is not live_mains but this:

        an identity live_mains cannot see is an identity resolve_target cannot reach

    so the nudge has no target and `not target` blocks it. Until 2026-07-29 that held
    only by coincidence between two independent implementations — undocumented and
    untested. C32 was a live breach of it. Anyone adding a fallback or a best-effort
    match to resolve_target must fail here.
    """
    adapter = _load(f"c24_{label}")
    monkeypatch.setattr(adapter, "_tmux", _tmux_semantics(_C24_WINDOWS))
    config = {"roster": [{"id": "codex", "endpoint": endpoint}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 3}}

    ids, why = adapter.live_mains(config)
    assert ids is not None, f"scenario must UNDERCOUNT, not refuse outright ({why})"
    assert "codex" not in ids, "fixture no longer reproduces an undercount"

    target, target_why = adapter.resolve_target(config, "codex")
    assert target is None, (
        f"CONTAINMENT BROKEN: 'codex' is uncounted by live_mains yet resolvable to "
        f"{target!r} ({target_why}). cmd_spawn will reset its heartbeat AND a nudge "
        f"can now be delivered to it mid-generation.")


def test_c24_containment_test_is_not_vacuous(monkeypatch: pytest.MonkeyPatch) -> None:
    """The positive control. Without it the invariant above would also be satisfied
    by a resolve_target that refuses everything, which would pass while delivering
    nothing — the opposite-polarity failure."""
    adapter = _load("c24_control")
    monkeypatch.setattr(adapter, "_tmux", _tmux_semantics(_C24_WINDOWS))
    config = {"roster": [{"id": "codex", "endpoint": "tmux:agent:codex-inference"}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 3}}

    assert adapter.live_mains(config)[0] == {"codex"}
    target, why = adapter.resolve_target(config, "codex")
    assert target == "agent:codex-inference", why


def test_c24_index_endpoint_no_longer_breaches_containment(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """C32 as a C24 regression, stated as the pair that must never both hold.

    `tmux:agent:99` was uncounted by live_mains AND resolved — reported as
    "(verified)" — because the verification exempted digit components. That is the
    one measured counterexample to the invariant, and it is what a nudge to the
    operator's own window looked like.
    """
    adapter = _load("c24_c32")
    monkeypatch.setattr(adapter, "_tmux", _tmux_semantics(_C24_WINDOWS))
    config = {"roster": [{"id": "codex", "endpoint": "tmux:agent:99"}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 3}}

    ids, _ = adapter.live_mains(config)
    target, why = adapter.resolve_target(config, "codex")

    assert "codex" not in ids
    assert target is None and "INDEX" in why
    # And the fake really does reproduce tmux's fallback, or the case proves nothing.
    assert adapter._tmux("display-message", "-p", "-t", "agent:99", "x") == (0, "0\toperator")


def test_c24_cross_session_endpoint_overcounts_and_still_refuses(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The other polarity, asserted so nobody 'fixes' it into the dangerous one.

    An endpoint naming a different session is counted live by live_mains (its
    matching is deliberately session-blind: overcounting refuses a spawn that might
    have been allowed, undercounting grants one that should not be) while
    resolve_target refuses it. Both errors point the safe way — no heartbeat reset,
    no nudge — and that asymmetry is a design choice, not an oversight.
    """
    adapter = _load("c24_cross")
    monkeypatch.setattr(adapter, "_tmux", _tmux_semantics(_C24_WINDOWS))
    config = {"roster": [{"id": "codex", "endpoint": "tmux:some-other-session:codex-inference"}],
              "tmux": {"live_session": "agent"}, "caps": {"max_concurrent_mains": 3}}

    assert adapter.live_mains(config)[0] == {"codex"}, "overcount is the SAFE direction"
    target, why = adapter.resolve_target(config, "codex")
    assert target is None, why


_C24_SPAWN_CONFIG = {
    "roster": [{"id": "new-main", "endpoint": "tmux:agent:new-main"}],
    "tmux": {"live_session": "agent", "allow_session_creation": False},
    "caps": {"max_concurrent_mains": 6},
}


def test_c24_a_fresh_spawn_records_no_heartbeat_reset(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Only an OVERWRITE is a ledger event. A first spawn destroys nothing, and a
    reset row for it would make the signal unreadable exactly when it matters."""
    adapter = _c9_adapter("hbfresh", monkeypatch, tmp_path, windows="0\tsomething-else",
                          config=_C24_SPAWN_CONFIG)
    adapter.BUS_ROOT = tmp_path / "bus"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)

    class A(_SpawnArgs):
        agent = "new-main"
        dry_run = False

    assert adapter.cmd_spawn(A()) == 0
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    assert [r["kind"] for r in rows] == ["spawn"]


def test_c24_reset_is_recorded_even_when_the_window_fails_to_start(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The heartbeat is destroyed BEFORE new-window runs, so a later failure must
    not be able to swallow the record of it — otherwise the one case where you most
    need to know a liveness signal was cleared is the case that leaves no trace."""
    adapter = _c9_adapter("hbfail", monkeypatch, tmp_path, windows="0\tsomething-else",
                          config=_C24_SPAWN_CONFIG)
    adapter.BUS_ROOT = tmp_path / "bus"
    hb = adapter.BUS_ROOT / "heartbeats" / "new-main.json"
    hb.parent.mkdir(parents=True)
    hb.write_text(json.dumps({"agent": "new-main", "state": "working",
                              "task_id": "task-from-a-dead-session",
                              "ts": "2020-01-01T00:00:00+00:00"}))
    inner = adapter._tmux
    monkeypatch.setattr(adapter, "_tmux",
                        lambda *a: (1, "no space") if a[0] == "new-window" else inner(*a))

    class A(_SpawnArgs):
        agent = "new-main"
        dry_run = False

    assert adapter.cmd_spawn(A()) == 3, "the spawn itself fails"
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    resets = [r for r in rows if r["kind"] == "heartbeat-reset"]
    assert len(resets) == 1
    assert resets[0]["overwrote"]["state"] == "working"
    assert resets[0]["overwrote"]["task_id"] == "task-from-a-dead-session"
    assert json.loads(hb.read_text())["state"] == "idle", "and the heartbeat really is gone"


def test_c24_an_unreadable_predecessor_heartbeat_still_records_the_reset(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A corrupt heartbeat is the LEAST safe thing to overwrite silently."""
    adapter = _c9_adapter("hbcorrupt", monkeypatch, tmp_path, windows="0\tsomething-else",
                          config=_C24_SPAWN_CONFIG)
    adapter.BUS_ROOT = tmp_path / "bus"
    hb = adapter.BUS_ROOT / "heartbeats" / "new-main.json"
    hb.parent.mkdir(parents=True)
    hb.write_text("{not json")

    class A(_SpawnArgs):
        agent = "new-main"
        dry_run = False

    assert adapter.cmd_spawn(A()) == 0
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    resets = [r for r in rows if r["kind"] == "heartbeat-reset"]
    assert len(resets) == 1 and "unreadable" in resets[0]["overwrote"]


# ---------------------------------------------------------------- C31 rate-limit key


def _c31_ledger(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def _c31_probe(tag: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
               ledger_rows: list[dict]) -> dict:
    adapter = _c9_adapter(tag, monkeypatch, tmp_path, windows="0\tnew-main",
                          config=_C24_SPAWN_CONFIG)
    adapter.BUS_ROOT = tmp_path / f"bus_{tag}"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    (adapter.BUS_ROOT / "heartbeats" / "new-main.json").write_text(
        json.dumps({"agent": "new-main", "state": "idle", "task_id": None,
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}))
    _c31_ledger(adapter.LEDGER, ledger_rows)
    return adapter.probe(_C24_SPAWN_CONFIG, "new-main", 0.0, 900.0)


def _iso_ago(seconds: float) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="seconds")


def test_c31_a_nudge_to_a_destroyed_window_does_not_rate_limit_the_new_one(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """C31: the rate limit exists to avoid pestering a WORKING SESSION. A session that
    did not exist when the earlier nudge was sent cannot have been pestered by it.

    Observed 2026-07-29: after a kill + re-spawn, nudges to the fresh window were
    refused for the rest of the 600s interval because of a nudge to the destroyed one.
    Coupled to C24 — that fix stops the fresh main being heartbeat-blocked, and this
    stops it being rate-limit-blocked instead. Either alone leaves it unreachable.
    """
    p = _c31_probe("c31_respawn", monkeypatch, tmp_path, [
        {"ts": _iso_ago(300), "kind": "nudge", "agent": "new-main", "detail": "to the OLD window"},
        {"ts": _iso_ago(120), "kind": "spawn", "agent": "new-main", "detail": "window recreated"},
    ])
    assert p["seconds_since_last_nudge"] is None, \
        "the only nudge predates this window instance and must not count"
    assert p["nudges_this_window_instance"] == 0
    assert p["spawned_at"] is not None


def test_c31_a_nudge_to_the_current_window_still_rate_limits(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The positive control. Without it, 'ignore old nudges' would be satisfied by
    ignoring ALL of them, which deletes the rate limit rather than re-keying it."""
    p = _c31_probe("c31_current", monkeypatch, tmp_path, [
        {"ts": _iso_ago(600), "kind": "spawn", "agent": "new-main", "detail": "window created"},
        {"ts": _iso_ago(60), "kind": "nudge", "agent": "new-main", "detail": "to THIS window"},
    ])
    assert p["seconds_since_last_nudge"] is not None
    assert 55 <= p["seconds_since_last_nudge"] <= 70
    assert p["nudges_this_window_instance"] == 1


def test_c31_only_the_newest_spawn_defines_the_instance(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Several spawns over a day: nudges between an OLD spawn and the newest one
    belong to a window that is also gone."""
    p = _c31_probe("c31_multi", monkeypatch, tmp_path, [
        {"ts": _iso_ago(3000), "kind": "spawn", "agent": "new-main", "detail": "first"},
        {"ts": _iso_ago(2400), "kind": "nudge", "agent": "new-main", "detail": "instance 1"},
        {"ts": _iso_ago(1800), "kind": "spawn", "agent": "new-main", "detail": "second"},
        {"ts": _iso_ago(1200), "kind": "nudge", "agent": "new-main", "detail": "instance 2"},
        {"ts": _iso_ago(600), "kind": "spawn", "agent": "new-main", "detail": "third"},
    ])
    assert p["seconds_since_last_nudge"] is None
    assert p["nudges_this_window_instance"] == 0


def test_c31_another_agents_spawn_does_not_clear_my_rate_limit(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The key is (agent, window instance). A neighbour re-spawning must not reset it —
    that would make any busy fleet effectively unrate-limited."""
    p = _c31_probe("c31_other", monkeypatch, tmp_path, [
        {"ts": _iso_ago(60), "kind": "nudge", "agent": "new-main", "detail": "mine"},
        {"ts": _iso_ago(30), "kind": "spawn", "agent": "someone-else", "detail": "not mine"},
    ])
    assert p["seconds_since_last_nudge"] is not None
    assert p["nudges_this_window_instance"] == 1


def test_c31_no_spawn_row_falls_back_to_whole_history(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A window created outside cmd_spawn leaves no spawn row. Keeping the limit is
    the fail-safe direction — dropping it would silence the guard for exactly the
    windows this adapter knows least about."""
    p = _c31_probe("c31_nospawn", monkeypatch, tmp_path, [
        {"ts": _iso_ago(60), "kind": "nudge", "agent": "new-main", "detail": "no spawn row"},
    ])
    assert p["seconds_since_last_nudge"] is not None
    assert p["spawned_at"] is None


def test_c31_an_unparseable_nudge_ts_does_not_wedge_nudging(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Matches the pre-C31 behaviour deliberately, and is NOT widened: a corrupt
    ledger row that permanently blocked nudging would wedge the whole fleet, which is
    strictly worse than one missed rate limit."""
    p = _c31_probe("c31_corrupt", monkeypatch, tmp_path, [
        {"ts": "not-a-timestamp", "kind": "nudge", "agent": "new-main", "detail": "corrupt"},
    ])
    assert p["seconds_since_last_nudge"] is None


# ---------------------------------------------------------------- C30(b) spawn survival


def _c30_adapter(tag: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                 windows_after: str):
    """Adapter whose `list-windows` answers differently AFTER new-window is called."""
    adapter = _load("c30_" + tag)
    adapter.LEDGER = tmp_path / f"ledger_{tag}.jsonl"
    adapter.BUS_ROOT = tmp_path / f"bus_{tag}"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    adapter.SPAWN_SETTLE_S = 0.0                      # never sleep in a unit test
    monkeypatch.setattr(adapter, "load_config", lambda: _C24_SPAWN_CONFIG)
    state = {"spawned": False}

    def fake_tmux(*args: str) -> tuple[int, str]:
        if args[0] == "list-windows":
            return 0, (windows_after if state["spawned"] else "0\tsomething-else")
        if args[0] == "new-window":
            state["spawned"] = True
            return 0, ""
        if args[0] == "has-session":
            return 0, ""
        if args[0] == "display-message":
            return 0, "0\tnew-main"
        return 0, ""

    monkeypatch.setattr(adapter, "_tmux", fake_tmux)
    return adapter


def test_c30b_spawn_refuses_success_when_the_window_died_immediately(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """C30(b): `new-window` exit 0 says tmux ACCEPTED the request, not that anything is
    running. A spawned codex pane died instantly on a CLI update prompt; the window
    vanished, cmd_spawn reported success, and only a manual list-windows revealed it.

    Polarity: a false success is worse than a false failure here, because the four bus
    files are already written, so the identity looks provisioned-and-live to everything
    downstream — including the C24 heartbeat reset and the concurrency cap.
    """
    adapter = _c30_adapter("died", monkeypatch, tmp_path, windows_after="0\tsomething-else")

    class A(_SpawnArgs):
        agent = "new-main"
        command = "true"
        dry_run = False

    rc = adapter.cmd_spawn(A())

    assert rc == 2, "a window that is already gone is not a successful spawn"
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    kinds = [r["kind"] for r in rows]
    assert "spawn-died" in kinds
    assert "spawn" not in kinds, "a spawn row would make the ledger claim a live window"


def test_c30b_a_surviving_window_still_reports_success(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The positive control — without it, 'refuse when it died' is satisfied by
    refusing always."""
    adapter = _c30_adapter("lived", monkeypatch, tmp_path, windows_after="0\tnew-main")

    class A(_SpawnArgs):
        agent = "new-main"
        command = "sleep 300"
        dry_run = False

    assert adapter.cmd_spawn(A()) == 0
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    assert [r["kind"] for r in rows] == ["spawn"]


def test_c30b_an_unreadable_window_list_does_not_manufacture_a_failure(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Deliberate asymmetry. Elsewhere in this module an unreadable signal fails CLOSED,
    but here the window and all four bus files already exist: reporting failure on a
    transient tmux hiccup would send an operator to tear down a healthy session. The
    check only fires on POSITIVE evidence of absence."""
    adapter = _load("c30_unreadable")
    adapter.LEDGER = tmp_path / "ledger_u.jsonl"
    adapter.BUS_ROOT = tmp_path / "bus_u"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    adapter.SPAWN_SETTLE_S = 0.0
    monkeypatch.setattr(adapter, "load_config", lambda: _C24_SPAWN_CONFIG)
    state = {"spawned": False}

    def fake_tmux(*args: str) -> tuple[int, str]:
        if args[0] == "list-windows":
            if state["spawned"]:
                return 1, "lost server"
            return 0, "0\tsomething-else"
        if args[0] == "new-window":
            state["spawned"] = True
            return 0, ""
        return 0, ""

    monkeypatch.setattr(adapter, "_tmux", fake_tmux)

    class A(_SpawnArgs):
        agent = "new-main"
        command = "sleep 300"
        dry_run = False

    assert adapter.cmd_spawn(A()) == 0
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    assert [r["kind"] for r in rows] == ["spawn"]


# ---------------------------------------------------------------- C35 quiescence override


# A roster whose endpoint names its window explicitly, so resolve_target verifies
# against #{window_index}\t#{window_name} and every case below reaches the
# heartbeat logic rather than dying at target resolution.
_C35_CONFIG = {
    "flags": {"codex_sendkeys": "on"},
    "roster": [{"id": "main-a", "endpoint": "tmux:agent:main-a"}],
    "tmux": {"live_session": "agent", "allow_session_creation": False},
    "caps": {"max_concurrent_mains": 6},
}


def _c35_probe(tag: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *,
               state: str = "working", quiet_for: float | None = 300.0,
               dead: str = "0", attached: str = "1",
               display_rc: int = 0, hb_override_quiet_s: float = 120.0,
               hb_age_s: float = 0.0, exact_activity: float | None = None) -> dict:
    """Probe one synthetic pane whose quiet time and heartbeat are both dialled in.

    `quiet_for` is expressed in SECONDS AGO and converted to the epoch stamp tmux
    actually reports, so the cases read in the units the guard is specified in.
    None makes #{window_activity} unparseable, which must fail closed.

    `exact_activity` supplies that epoch stamp directly, for the frozen-clock
    boundary cases where the usual `now - quiet_for` arithmetic would drift by the
    time probe reads it back.
    """
    adapter = _load("c35_" + tag)
    adapter.LEDGER = tmp_path / f"ledger_{tag}.jsonl"
    adapter.BUS_ROOT = tmp_path / f"bus_{tag}"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    hb = adapter.BUS_ROOT / "heartbeats" / "main-a.json"
    hb.write_text(json.dumps({"agent": "main-a", "state": state, "task_id": "t-1",
                              "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}))
    if hb_age_s:
        old = __import__("time").time() - hb_age_s
        os.utime(hb, (old, old))
    monkeypatch.setattr(adapter, "load_config", lambda: _C35_CONFIG)

    if exact_activity is not None:
        act = str(int(exact_activity))
    elif quiet_for is None:
        act = "not-a-number"
    else:
        act = str(int(__import__("time").time() - quiet_for))

    def fake_tmux(*args: str) -> tuple[int, str]:
        if args[0] == "display-message":
            fmt = args[-1]
            if "#{pane_dead}" in fmt:
                if display_rc != 0:
                    return display_rc, "can't find pane"
                return 0, f"{dead}\t{act}\t{attached}"
            # resolve_target's verification probe
            return 0, "4\tmain-a"
        if args[0] == "list-windows":
            return 0, "4\tmain-a"
        return 0, ""

    monkeypatch.setattr(adapter, "_tmux", fake_tmux)
    return adapter.probe(_C35_CONFIG, "main-a", 20.0, 900.0, hb_override_quiet_s)


def _working_blocked(p: dict) -> bool:
    return any("says working" in b for b in p["blockers"])


def test_c35_a_quiet_pane_overrides_a_working_heartbeat(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """THE DEADLOCK THIS REMOVES. A main that finishes a unit and settles at its
    prompt keeps `working` in its heartbeat, because the code that would update it
    is the code that stopped running. It cannot clear the flag, because clearing it
    requires being told to — which is what the guard refused. Measured 2026-07-29:
    four hand-relays in one day, one of them into a session holding the whole
    machine for an exclusive E5 window."""
    p = _c35_probe("override", monkeypatch, tmp_path, state="working", quiet_for=300.0)
    assert not _working_blocked(p), f"the working blocker must be suppressed ({p['blockers']})"
    assert p["heartbeat_override_applied"] is True
    assert p["nudge_ok"], f"and the nudge must actually be allowed ({p['blockers']})"


def test_c35_a_recently_active_pane_still_believes_a_working_heartbeat(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """THE CASE THAT MATTERS MOST — this is the one protecting a mid-generation
    session from having text typed into its pane. Both TUIs redraw a spinner about
    once a second while working (calibrated 2026-07-29: a busy window never showed
    more than 1s of apparent quiet in any attached/detached x fore/background
    combination), so a real generation lands here and the heartbeat is believed."""
    p = _c35_probe("midgen", monkeypatch, tmp_path, state="working", quiet_for=1.0)
    assert _working_blocked(p), "a mid-generation pane must still refuse"
    assert p["heartbeat_override_applied"] is False
    assert not p["nudge_ok"]


@pytest.mark.parametrize("quiet_for,applied", [
    (110.0, False),   # comfortably inside the threshold — believed
    (130.0, True),    # comfortably past it — overridden
])
def test_c35_the_threshold_is_respected_either_side(
        quiet_for: float, applied: bool, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    p = _c35_probe(f"bound{int(quiet_for)}", monkeypatch, tmp_path,
                   state="working", quiet_for=quiet_for, hb_override_quiet_s=120.0)
    assert p["heartbeat_override_applied"] is applied
    assert _working_blocked(p) is (not applied)


@pytest.mark.parametrize("quiet_for,applied", [
    (119.0, False),   # one second short — believed
    (120.0, True),    # EXACTLY at the threshold: the comparison is >=, so it overrides
    (121.0, True),
])
def test_c35_the_threshold_is_exact_at_its_boundary(
        quiet_for: float, applied: bool, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    """A FROZEN CLOCK, because the boundary is otherwise untestable.

    `_c35_probe` builds an epoch stamp and probe turns it back into a duration, and
    the elapsed time between those two steps pushes the result a fraction of a
    second past whatever was asked for. A parametrisation of (120.0 -> overrides)
    therefore passes against a `<=` comparison as readily as a `<` one — verified:
    mutating the operator to `<=` left the earlier version of this test green. So
    the clock is pinned to an integral value, which makes the arithmetic exact and
    the boundary genuinely observable.

    Whole seconds only: tmux reports #{window_activity} as an epoch INTEGER, so a
    fractional quiet time is not a state the adapter can ever observe.
    """
    import time as _time
    fixed = float(int(_time.time()))
    monkeypatch.setattr(_time, "time", lambda: fixed)
    p = _c35_probe(f"exact{str(quiet_for).replace('.', '_')}", monkeypatch, tmp_path,
                   state="working", quiet_for=quiet_for, hb_override_quiet_s=120.0,
                   exact_activity=fixed - quiet_for)
    assert p["window_quiet_for_s"] == pytest.approx(quiet_for), \
        "the frozen clock must make the observed quiet time exactly what was asked for"
    assert p["heartbeat_override_applied"] is applied
    assert _working_blocked(p) is (not applied)


def test_c35_the_threshold_is_tunable_not_hardcoded(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The flag must actually move the decision, or it is decoration."""
    quiet = 200.0
    lax = _c35_probe("tunelax", monkeypatch, tmp_path, quiet_for=quiet, hb_override_quiet_s=100.0)
    strict = _c35_probe("tunestr", monkeypatch, tmp_path, quiet_for=quiet, hb_override_quiet_s=600.0)
    assert lax["heartbeat_override_applied"] is True
    assert strict["heartbeat_override_applied"] is False
    assert lax["heartbeat_override_quiet_s"] == 100.0


def test_c35_a_non_positive_threshold_disables_the_override(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """0 must mean OFF, not 'override always'. A mis-set threshold has to be inert,
    because the failure it would otherwise cause is typing into a live generation."""
    for tag, thr in (("zero", 0.0), ("neg", -1.0)):
        p = _c35_probe("disabled" + tag, monkeypatch, tmp_path,
                       state="working", quiet_for=99999.0, hb_override_quiet_s=thr)
        assert p["heartbeat_override_applied"] is False
        assert _working_blocked(p), f"threshold {thr} must leave the guard fully armed"


def test_c35_an_unreadable_window_activity_fails_closed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """This module's defect history is C3, C6, C8, C24, C35 — every one a fail-OPEN.
    An unparseable activity stamp must never be read as 'quiet for a long time'."""
    p = _c35_probe("badact", monkeypatch, tmp_path, state="working", quiet_for=None)
    assert p["heartbeat_override_applied"] is False
    assert _working_blocked(p)
    assert "unreadable" in (p["heartbeat_override_reason"] or "")


def test_c35_an_unreadable_pane_fails_closed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """display-message failing means pane_dead is None. `dead is not False` is the
    deliberate wording — `not dead` would treat None as alive."""
    p = _c35_probe("badpane", monkeypatch, tmp_path, state="working", display_rc=1)
    assert p["heartbeat_override_applied"] is False
    assert _working_blocked(p)
    assert not p["nudge_ok"]


def test_c35_a_dead_pane_is_never_overridden_and_still_refuses(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A dead pane is quiet forever, which is exactly the shape that would fool a
    naive quiescence rule."""
    p = _c35_probe("deadpane", monkeypatch, tmp_path, state="working",
                   quiet_for=9999.0, dead="1")
    assert p["heartbeat_override_applied"] is False
    assert any("pane is dead" in b for b in p["blockers"])
    assert not p["nudge_ok"]


def test_c35_the_override_touches_only_the_working_blocker(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every other guard must survive the override independently. Without this the
    change could quietly become 'a quiet pane is always nudgeable'."""
    # staleness: independent, and deliberately NOT overridden — it is already
    # tunable with --heartbeat-max-age, whereas state was not tunable at all.
    stale = _c35_probe("stale", monkeypatch, tmp_path, state="working",
                       quiet_for=300.0, hb_age_s=4000.0)
    assert stale["heartbeat_override_applied"] is True
    assert any("stale" in b for b in stale["blockers"])
    assert not stale["nudge_ok"], "an overridden state must not also waive staleness"

    # authorisation flag
    adapter = _load("c35_flagoff")
    adapter.LEDGER = tmp_path / "l.jsonl"
    adapter.BUS_ROOT = tmp_path / "bus_flagoff"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    (adapter.BUS_ROOT / "heartbeats" / "main-a.json").write_text(
        json.dumps({"agent": "main-a", "state": "working", "task_id": "t",
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}))
    cfg_off = dict(_C35_CONFIG, flags={"codex_sendkeys": "off"})
    monkeypatch.setattr(adapter, "load_config", lambda: cfg_off)
    act = str(int(__import__("time").time() - 300))
    monkeypatch.setattr(adapter, "_tmux", lambda *a: (
        (0, f"0\t{act}\t1") if a[0] == "display-message" and "#{pane_dead}" in a[-1]
        else (0, "4\tmain-a")))
    p = adapter.probe(cfg_off, "main-a", 20.0, 900.0, 120.0)
    assert p["heartbeat_override_applied"] is True
    assert any("codex_sendkeys is off" in b for b in p["blockers"])
    assert not p["nudge_ok"], "the authorisation gate is not a heartbeat blocker"


def test_c35_a_missing_heartbeat_is_still_a_blocker_even_on_a_quiet_pane(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The override suppresses a `working` STATE. It must not be reachable as a way
    of nudging an agent with no heartbeat at all."""
    adapter = _load("c35_nohb")
    adapter.LEDGER = tmp_path / "l2.jsonl"
    adapter.BUS_ROOT = tmp_path / "bus_nohb"
    (adapter.BUS_ROOT / "heartbeats").mkdir(parents=True)
    monkeypatch.setattr(adapter, "load_config", lambda: _C35_CONFIG)
    act = str(int(__import__("time").time() - 5000))
    monkeypatch.setattr(adapter, "_tmux", lambda *a: (
        (0, f"0\t{act}\t1") if a[0] == "display-message" and "#{pane_dead}" in a[-1]
        else (0, "4\tmain-a")))
    p = adapter.probe(_C35_CONFIG, "main-a", 20.0, 900.0, 120.0)
    assert any("no heartbeat" in b for b in p["blockers"])
    assert p["heartbeat_override_applied"] is False
    assert not p["nudge_ok"]


def test_c35_an_idle_heartbeat_reports_no_override_at_all(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """THE COMPLIANT PATH. An agent keeping its heartbeat honest must not be routed
    through the override at all — probe should show it was never consulted."""
    p = _c35_probe("idle", monkeypatch, tmp_path, state="idle", quiet_for=300.0)
    assert p["heartbeat_override_applied"] is False
    assert p["heartbeat_override_reason"] is None, \
        "no reason means the override was never reached, not that it declined"
    assert p["nudge_ok"]


def test_c35_probe_explains_the_override_in_both_directions(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str]) -> None:
    """`probe` must never let a human be surprised by a nudge the guard 'should'
    have refused — nor leave a refusal unexplained. Both renderings are asserted
    because a one-sided report is how probe and nudge drift apart."""
    adapter = _load("c35_print")

    class PA:
        agent = "main-a"
        json = False
        quiet_s = 20.0
        heartbeat_max_age = 900.0
        heartbeat_override_quiet_s = 120.0

    applied = _c35_probe("printapp", monkeypatch, tmp_path, state="working", quiet_for=300.0)
    monkeypatch.setattr(adapter, "load_config", lambda: _C35_CONFIG)
    monkeypatch.setattr(adapter, "probe", lambda *a, **k: applied)
    adapter.cmd_probe(PA())
    out = capsys.readouterr().out
    assert "hb-override" in out and "APPLIED" in out
    assert "quiet" in out and "settled at" in out, f"it must say WHY, not just that it did: {out}"

    believed = _c35_probe("printbel", monkeypatch, tmp_path, state="working", quiet_for=2.0)
    monkeypatch.setattr(adapter, "probe", lambda *a, **k: believed)
    adapter.cmd_probe(PA())
    out2 = capsys.readouterr().out
    assert "hb-override" in out2 and "not applied" in out2
    assert "heartbeat believed" in out2


def test_c35_an_overriding_nudge_is_recorded_as_such_in_the_ledger(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If the override ever does interrupt a real generation, the ledger row is the
    evidence. An ordinary nudge must stay byte-identical to before."""
    adapter = _load("c35_ledger")
    # _Args.message is shared class state that earlier tests mutate, so set it here
    # and build the scripted composer from it rather than from a literal.
    _Args.message = "drain the bus"
    pending = "› " + _Args.message
    submitted = pending + "\n● working\n\n› "
    over = {"nudge_ok": True, "target": "agent:main-a", "seconds_since_last_nudge": None,
            "heartbeat_override_applied": True, "window_quiet_for_s": 300.0,
            "heartbeat_override_reason": "window quiet 300s (>= 120s)"}
    calls = _stub_nudge(adapter, monkeypatch, [pending, submitted], tmp_path)
    monkeypatch.setattr(adapter, "probe", lambda *a, **k: over)
    assert adapter.cmd_nudge(_Args()) == 0
    row = json.loads(adapter.LEDGER.read_text().splitlines()[-1])
    assert row["heartbeat_override"].startswith("window quiet")
    assert row["window_quiet_for_s"] == 300.0
    assert calls, "and it really did send"

    plain = {"nudge_ok": True, "target": "agent:main-a", "seconds_since_last_nudge": None,
             "heartbeat_override_applied": False, "window_quiet_for_s": 300.0,
             "heartbeat_override_reason": "window was active 2s ago"}
    adapter2 = _load("c35_ledger2")
    _stub_nudge(adapter2, monkeypatch, [pending, submitted], tmp_path)
    adapter2.LEDGER = tmp_path / "plain.jsonl"
    monkeypatch.setattr(adapter2, "probe", lambda *a, **k: plain)
    assert adapter2.cmd_nudge(_Args()) == 0
    row2 = json.loads(adapter2.LEDGER.read_text().splitlines()[-1])
    assert "heartbeat_override" not in row2, "a normal nudge row is unchanged on disk"

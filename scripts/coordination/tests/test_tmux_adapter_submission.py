#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""C51/C53 — submission verification and the pending-input detector for tmux_adapter.py.

    python -m pytest scripts/coordination/tests/test_tmux_adapter_submission.py

WHAT THIS PINS, and why it is a third file rather than more of the other two.
`tests/test_tmux_adapter.py` drives the predicates against stubbed pane text and
`scripts/coordination/tests/test_tmux_adapter_live.py` drives one real pane through
the guard chain. Neither could express the defect C51 fixes, because the defect is
about what happens AFTER `send-keys` returns 0 — which needs a pane whose Enter
behaviour is controllable. That is `composer_tui_fixture.py`: a disposable TUI with
the composer semantics both real TUIs were measured to have (cursor at the end of
pending input; a submitted message echoed into the transcript; a bare glyph when
empty), and three selectable Enter behaviours — submit, swallow, and eaten-by-a-
completion-picker.

C53 is the other half, and it is the one that explains the operator's sightings: on
the CLIs this fleet runs today the cursor does NOT sit at the end of pending input —
it parks at column 2 with the text to its right — so every cursor-prefix read reported
an EMPTY composer for panes that were visibly holding an unsubmitted instruction. The
cases at the end of this file carry the measured escape-sequence rows from the live
Claude panes and from a disposable Codex session, because the two TUIs render faint
text to mean opposite things and no rule that ignores the backend can serve both.

The basename is unique on purpose: two files named `test_tmux_adapter.py` in two
non-package directories made pytest abort with `import file mismatch` and hid a live
suite for a day (C10). Do not rename this to match either of them.

SAFETY: never touches the live `agent` session. Every tmux case runs in a throwaway
session `tmuxsub-test-<pid>`, killed even on failure, with BUS_ROOT redirected to a
temp tree. The live group skips cleanly when tmux is unreachable.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py"
FIXTURE = Path(__file__).resolve().parent / "composer_tui_fixture.py"
SESSION = f"tmuxsub-test-{os.getpid()}"

# MEASURED 2026-08-12, read-only (`display-message` + `capture-pane` only), against
# all ten windows of the live `agent` session — six Claude Code mains and one Codex
# main. These are the exact composer rows, sliced at the cursor, that an EMPTY
# composer produces on the CLIs this fleet is running today. They are the fixture the
# glyph table has to satisfy; anything else is a guess about someone's terminal.
# Written with explicit escapes: the second character of the Claude row is U+00A0, a
# NON-BREAKING space, and a literal one in source is indistinguishable from U+0020 to
# every reader and most editors — exactly the kind of invisible difference that
# produced the defect this pins.
LIVE_CLAUDE_EMPTY_COMPOSER = "\u276f\u00a0"          # cursor_x == 2, sliced to just this
LIVE_CODEX_EMPTY_COMPOSER = "\u203a "               # the placeholder sits right of the cursor
LIVE_CLAUDE_PENDING_COMPOSER = "\u276f\u00a0PUSHED - log the audit verdict in your lane entry"


# --------------------------------------------------------------------------- helpers


def _load(bus_root: Path | None = None):
    spec = importlib.util.spec_from_file_location(f"ta_sub_{os.getpid()}_{id(bus_root)}", MODULE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if bus_root is not None:
        m.BUS_ROOT = bus_root
        m.LEDGER = bus_root / "adapter-ledger.jsonl"
        for d in ("heartbeats", "cursors", "inbox", "outbox"):
            (bus_root / d).mkdir(parents=True, exist_ok=True)
    return m


def _tmux(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return r.returncode, (r.stdout or r.stderr).strip()


def _tmux_available() -> bool:
    return _tmux("-V")[0] == 0


def _write_config(bus_root: Path, agents: list[str]) -> None:
    import yaml
    cfg = {"roster": [{"id": a, "role": "main", "endpoint": f"tmux:{SESSION}:{a}"}
                      for a in agents],
           "flags": {"codex_sendkeys": "on"},
           "caps": {"max_concurrent_mains": 9},
           "tmux": {"live_session": SESSION, "allow_session_creation": False}}
    (bus_root / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _heartbeat(m, agent: str, state: str = "idle") -> None:
    (m.BUS_ROOT / "heartbeats" / f"{agent}.json").write_text(json.dumps(
        {"agent": agent, "state": state, "task_id": None,
         "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}), encoding="utf-8")


def _start_pane(window: str, mode: str, seed: list[str] | None = None) -> None:
    args = ["new-window", "-d", "-t", SESSION, "-n", window,
            sys.executable, str(FIXTURE), "--mode", mode]
    for s in seed or []:
        args += ["--seed", s]
    rc, out = _tmux(*args)
    assert rc == 0, f"could not start fixture pane {window}: {out}"
    time.sleep(0.6)


def _composer(window: str) -> str:
    rc, out = _tmux("capture-pane", "-p", "-t", f"{SESSION}:{window}")
    assert rc == 0, out
    return out.rstrip("\n").rsplit("\n", 1)[-1]


def _run(m, argv: list[str]) -> tuple[int, str]:
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            rc = m.main(argv)
        except SystemExit as exc:
            rc = int(exc.code or 0)
    return rc, buf.getvalue().strip()


def _ledger(m) -> list[dict]:
    if not m.LEDGER.exists():
        return []
    return [json.loads(l) for l in m.LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture
def live_bus():
    """A throwaway tmux session + a temp BUS_ROOT, torn down even on failure."""
    if not _tmux_available():
        pytest.skip("no tmux reachable")
    rc, out = _tmux("new-session", "-d", "-s", SESSION, "-n", "holder", "sleep", "600")
    assert rc == 0, out
    try:
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)
    finally:
        _tmux("kill-session", "-t", SESSION)


# =========================================================== unit: the empty predicate
#
# The glyph table is the one calibration C51 could not remove, so it is the one that
# has to be pinned against MEASURED renderings rather than remembered ones.


def test_measured_live_empty_composers_all_read_as_empty():
    m = _load()
    for row in (LIVE_CLAUDE_EMPTY_COMPOSER, LIVE_CODEX_EMPTY_COMPOSER, "", "   "):
        assert m._composer_row_is_empty(row), f"{row!r} is an EMPTY composer on the live fleet"


def test_pending_composer_is_not_read_as_empty():
    m = _load()
    assert not m._composer_row_is_empty(LIVE_CLAUDE_PENDING_COMPOSER)
    assert not m._composer_row_is_empty("› run the full BGE sweep")


def test_mutation_the_pre_c51_glyph_table_calls_every_live_claude_pane_non_empty(monkeypatch):
    """MUTATION, and the one that matters most: revert the glyph table and the check
    inverts on the whole live fleet.

    Before C51 the table was ("›", "❱"). Measured against the six live Claude Code
    panes, an EMPTY composer renders "❯\\xa0" — U+276F, not the U+2771 that table
    carried — so `_composer_row_is_empty` returned False for every empty Claude
    composer. That made `doorbell`'s guard (b) refuse every ring to every Claude main
    (the fleet's whole new delivery path, 0% operative) and would have made C51's
    buffer check unable to confirm a submission on any of them.

    This asserts the mutation is VISIBLE: with the old table the empty row reads
    non-empty, with the current one it reads empty. If someone "tidies" the glyph
    list back, this fails rather than the fleet going quiet.
    """
    m = _load()
    assert m._composer_row_is_empty(LIVE_CLAUDE_EMPTY_COMPOSER)      # with the fix
    monkeypatch.setattr(m, "_BARE_PROMPT_GLYPHS", ("›", "❱"))
    assert not m._composer_row_is_empty(LIVE_CLAUDE_EMPTY_COMPOSER)  # without it


# =================================================== unit: the C12 anchor is load-bearing


def test_c12_anchor_value_decides_between_echo_and_stale_copy():
    """The pre-Enter occurrence count is what separates "submitted" from "a stale copy
    answered for it", and C51(3) was that the count was sampled AFTER the Enter.

    Composer below is the picker outcome: our copy is GONE from the composer, one
    stale copy remains in the transcript. The true pre-Enter count was 2 (stale +
    ours). Sampling after the Enter yields 1.

    MUTATION, visible: the same pane text reads `text_absent` (refuse) under the
    correct anchor and `text_echoed` (accept, and a ledger row for a submission that
    never happened) under the anchor the pre-C51 code actually passed.
    """
    m = _load()
    fragment = "run the full BGE sweep"
    after_picker = "› run the full BGE sweep\nsome output\n› src/completed_path.py"
    assert m._submission_state(after_picker, fragment, 2) == "text_absent"
    assert m._submission_state(after_picker, fragment, 1) == "text_echoed"


# ===================================================== unit: the detector's classification


def _detector_config(rows: list[dict]) -> dict:
    return {"roster": rows, "tmux": {"live_session": "x"}}


def test_detector_reports_pending_and_exits_non_zero(monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "resolve_target", lambda cfg, a: (f"x:{a}", "verified"))
    monkeypatch.setattr(m, "_read_composer_row",
                        lambda t, _f=False: ("❯ push it" if t.endswith("b") else "❯ ", None))
    monkeypatch.setattr(m, "heartbeat", lambda a: ({"state": "idle"}, 5.0))
    report = m.pending_input_report(_detector_config(
        [{"id": "a", "endpoint": "tmux:x:a"}, {"id": "b", "endpoint": "tmux:x:b"}]))
    assert report["pending"] == ["b"]
    assert [r["status"] for r in report["panes"]] == ["empty", "pending"]
    assert report["panes"][1]["pending_text"] == "❯ push it".strip()
    assert m.pending_exit_code(report) == m.EX_BLOCKED


def test_detector_clean_fleet_exits_zero(monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "resolve_target", lambda cfg, a: (f"x:{a}", "verified"))
    monkeypatch.setattr(m, "_read_composer_row", lambda t, _f=False: ("❯ ", None))
    monkeypatch.setattr(m, "heartbeat", lambda a: ({"state": "idle"}, 5.0))
    report = m.pending_input_report(_detector_config([{"id": "a", "endpoint": "tmux:x:a"}]))
    assert report["pending"] == [] and report["unevaluable"] == []
    assert m.pending_exit_code(report) == 0


def test_detector_unreadable_pane_is_not_reported_clean(monkeypatch):
    """The fail-open this module's whole history is made of: "I could not look"
    must never render as "nothing is pending"."""
    m = _load()
    monkeypatch.setattr(m, "resolve_target", lambda cfg, a: (f"x:{a}", "verified"))
    monkeypatch.setattr(m, "_read_composer_row", lambda t, _f=False: (None, "capture-pane failed"))
    monkeypatch.setattr(m, "heartbeat", lambda a: (None, None))
    report = m.pending_input_report(_detector_config([{"id": "a", "endpoint": "tmux:x:a"}]))
    assert report["unevaluable"] == ["a"]
    assert m.pending_exit_code(report) == m.EX_MISCONFIG


def test_detector_unresolved_endpoint_is_unevaluable_but_a_retired_row_is_not(monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "resolve_target", lambda cfg, a: (None, "does not resolve"))
    monkeypatch.setattr(m, "heartbeat", lambda a: (None, None))
    report = m.pending_input_report(_detector_config([
        {"id": "live", "role": "main", "endpoint": "tmux:x:live"},
        {"id": "old", "role": "retired", "endpoint": "tmux:x:old"},
        {"id": "filebacked", "role": "main", "endpoint": "monitor:file"}]))
    by_id = {r["agent"]: r["status"] for r in report["panes"]}
    assert by_id == {"live": "unresolved", "old": "retired", "filebacked": "no-pane"}
    assert report["unevaluable"] == ["live"]


def test_detector_unknown_agent_is_refused_not_silently_dropped(monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "heartbeat", lambda a: (None, None))
    report = m.pending_input_report(_detector_config([{"id": "a", "endpoint": "monitor:file"}]),
                                    agents=["ghost"])
    assert report["not_in_roster"] == ["ghost"]
    assert m.pending_exit_code(report) == m.EX_BLOCKED


# ================================================================ live: the submit path


def test_live_compliant_nudge_still_succeeds(live_bus):
    """THE COMPLIANT PATH. A normal nudge into a pane whose Enter works must land,
    exit 0, write exactly one `nudge` ledger row and leave the composer empty. If
    C51's extra checks over-refuse, this is what fails."""
    m = _load(live_bus)
    _write_config(live_bus, ["ok"])
    _heartbeat(m, "ok")
    _start_pane("ok", "submit")

    rc, out = _run(m, ["nudge", "--agent", "ok", "--min-interval-s", "0",
                       "--message", "run the full BGE sweep"])
    assert rc == 0, out
    assert "nudged ok" in out
    assert [r["kind"] for r in _ledger(m)] == ["nudge"]
    assert m._composer_row_is_empty(_composer("ok"))


def test_live_compliant_doorbell_still_succeeds(live_bus):
    m = _load(live_bus)
    _write_config(live_bus, ["ok"])
    _heartbeat(m, "ok")
    _start_pane("ok", "submit")

    rc, out = _run(m, ["doorbell", "--agent", "ok"])
    assert rc == 0, out
    assert [r["kind"] for r in _ledger(m)] == ["doorbell"]
    assert m._composer_row_is_empty(_composer("ok"))


def test_live_swallowed_enter_fails_loud_and_rolls_the_payload_back(live_bus):
    """THE OBSERVED 2026-08-12 CONDITION. Pre-C51 this returned non-zero and left the
    payload sitting in the composer with no record anywhere, which is what made three
    mains look like they had declined an instruction they were never given."""
    m = _load(live_bus)
    _write_config(live_bus, ["swallow"])
    _heartbeat(m, "swallow")
    _start_pane("swallow", "swallow")

    rc, out = _run(m, ["nudge", "--agent", "swallow", "--min-interval-s", "0",
                       "--message", "run the full BGE sweep"])
    assert rc != 0, out
    assert "NOT DELIVERED" in out
    # the payload must NOT be left in front of the main
    assert m._composer_row_is_empty(_composer("swallow")), _composer("swallow")
    rows = _ledger(m)
    assert [r["kind"] for r in rows] == ["nudge-undelivered"]
    assert rows[0]["rollback"] == "cleared" and rows[0]["stranded"] is False


def test_live_swallowed_enter_is_not_recorded_as_a_delivered_nudge(live_bus):
    """No `nudge` row may exist for a message that was never submitted — the ledger is
    what a coordinator reads to decide whether a main was told something."""
    m = _load(live_bus)
    _write_config(live_bus, ["swallow"])
    _heartbeat(m, "swallow")
    _start_pane("swallow", "swallow")
    _run(m, ["nudge", "--agent", "swallow", "--min-interval-s", "0", "--message", "push it"])
    assert not [r for r in _ledger(m) if r["kind"] == "nudge"]


def test_live_picker_eating_enter_is_refused_not_recorded(live_bus):
    """C51(3) END TO END. An identical fragment already in the transcript plus an Enter
    consumed by a completion overlay: pre-C51 this exited 0 and wrote a `nudge` row."""
    m = _load(live_bus)
    _write_config(live_bus, ["picker"])
    _heartbeat(m, "picker")
    _start_pane("picker", "picker", seed=["› run the full BGE sweep"])

    rc, out = _run(m, ["nudge", "--agent", "picker", "--min-interval-s", "0",
                       "--message", "run the full BGE sweep"])
    assert rc != 0, out
    assert not [r for r in _ledger(m) if r["kind"] == "nudge"]
    assert m._composer_row_is_empty(_composer("picker")), _composer("picker")


def test_live_enter_that_clears_without_submitting_is_refused(live_bus):
    """C51(3), END TO END, AND THE ONLY CASE THAT ISOLATES THE ANCHOR'S ORDERING.

    A '/' menu that runs a command on Enter, or a modal dismissed on Enter, CLEARS
    the composer without sending anything. So the buffer-consumed conjunct passes
    honestly and the transcript echo is the only remaining evidence — which is
    exactly where the pre-Enter occurrence anchor decides, because a stale copy of
    the same fragment is sitting in the transcript.

    Numbers, and they are the whole test: pre-Enter the fragment is on the pane
    TWICE (the seeded stale copy plus ours); afterwards, ONCE. Anchored where the
    code now samples it, 1 < 2 and the nudge is refused. Anchored where the pre-C51
    code sampled it — after the Enter — the anchor is itself 1, `1 >= 1` holds, the
    stale copy answers for a submission that never happened, and the adapter exits 0
    and writes a ledger row. A source-level mutation that moves the sample back
    below `send-keys Enter` fails HERE and nowhere else; every other case in this
    file is caught by the buffer check first.
    """
    m = _load(live_bus)
    _write_config(live_bus, ["cancel"])
    _heartbeat(m, "cancel")
    _start_pane("cancel", "cancel", seed=["› run the full BGE sweep"])

    rc, out = _run(m, ["nudge", "--agent", "cancel", "--min-interval-s", "0",
                       "--message", "run the full BGE sweep"])
    assert rc != 0, out
    assert not [r for r in _ledger(m) if r["kind"] == "nudge"], _ledger(m)


def test_live_doorbell_swallowed_enter_is_refused_not_rung(live_bus):
    """The doorbell had NO submission verification at all before C51: it recorded a
    ring on the strength of two `send-keys` exit codes."""
    m = _load(live_bus)
    _write_config(live_bus, ["swallow"])
    _heartbeat(m, "swallow")
    _start_pane("swallow", "swallow")

    rc, out = _run(m, ["doorbell", "--agent", "swallow"])
    assert rc != 0, out
    assert not [r for r in _ledger(m) if r["kind"] == "doorbell"]
    assert [r["kind"] for r in _ledger(m)] == ["doorbell-undelivered"]
    assert m._composer_row_is_empty(_composer("swallow")), _composer("swallow")


def test_live_mutation_without_the_buffer_check_a_swallowed_doorbell_reports_success(live_bus):
    """MUTATION, visible and counted, on the doorbell's ONLY submission evidence.

    Neutralise `_await_composer_consumed` — which is exactly the pre-C51 doorbell,
    where nothing was checked after Enter — and the same swallowed ring reports
    success and writes a `doorbell` ledger row while its text sits unsubmitted in the
    composer. The sibling test above proves the fixed path refuses it. Together they
    show the check is what decides, not something else in the chain.
    """
    m = _load(live_bus)
    _write_config(live_bus, ["swallow"])
    _heartbeat(m, "swallow")
    _start_pane("swallow", "swallow")
    m._await_composer_consumed = lambda *a, **k: (True, "", None)

    rc, out = _run(m, ["doorbell", "--agent", "swallow"])
    assert rc == 0, out                                    # the fail-open, reproduced
    assert [r["kind"] for r in _ledger(m)] == ["doorbell"]  # a ring that never rang
    assert not m._composer_row_is_empty(_composer("swallow"))


def test_live_mutation_without_the_buffer_check_a_swallowed_nudge_would_be_recorded(live_bus):
    """Same mutation on the payload path, against the ONE pane state where the echo
    check cannot help: a swallowed Enter whose text also happens to sit in the
    transcript. Neutralising the buffer check restores the pre-C51 behaviour."""
    m = _load(live_bus)
    _write_config(live_bus, ["swallow"])
    _heartbeat(m, "swallow")
    _start_pane("swallow", "swallow", seed=["› run the full BGE sweep"])
    m._await_state = lambda t, f, wanted, *a, **k: (
        "text_present" if "text_present" in wanted else "text_echoed", None)
    m._await_composer_consumed = lambda *a, **k: (True, "", None)

    rc, out = _run(m, ["nudge", "--agent", "swallow", "--min-interval-s", "0",
                       "--message", "run the full BGE sweep"])
    assert rc == 0, out
    assert [r["kind"] for r in _ledger(m)] == ["nudge"]
    assert not m._composer_row_is_empty(_composer("swallow"))


# ============================================== live: operator-typed input is never touched


def test_live_nudge_refuses_a_composer_that_already_holds_input_and_leaves_it_alone(live_bus):
    """The pane may hold the OPERATOR mid-sentence, and nothing on the pane says who
    typed it. So the nudge refuses, does not append, does not press Enter, and — the
    part that matters — does not clear it either."""
    m = _load(live_bus)
    _write_config(live_bus, ["typing"])
    _heartbeat(m, "typing")
    _start_pane("typing", "submit")
    _tmux("send-keys", "-l", "-t", f"{SESSION}:typing", "--", "operator half-typed thought")
    time.sleep(0.4)

    rc, out = _run(m, ["nudge", "--agent", "typing", "--min-interval-s", "0",
                       "--message", "run the full BGE sweep"])
    assert rc != 0, out
    assert "already holds pending input" in out
    row = _composer("typing")
    assert "operator half-typed thought" in row, row
    assert "BGE" not in row, row                  # nothing was appended
    assert _ledger(m) == []                       # and nothing was recorded as sent


def test_live_doorbell_refuses_a_composer_that_already_holds_input(live_bus):
    m = _load(live_bus)
    _write_config(live_bus, ["typing"])
    _heartbeat(m, "typing")
    _start_pane("typing", "submit")
    _tmux("send-keys", "-l", "-t", f"{SESSION}:typing", "--", "operator half-typed thought")
    time.sleep(0.4)

    rc, out = _run(m, ["doorbell", "--agent", "typing"])
    assert rc != 0, out
    assert "operator half-typed thought" in _composer("typing")
    assert _ledger(m) == []


# ================================================================ live: the detector


def test_live_detector_sees_pending_input_and_names_the_main(live_bus):
    """The whole point: the standing condition is answerable without reading panes."""
    m = _load(live_bus)
    _write_config(live_bus, ["clean", "stuck"])
    for a in ("clean", "stuck"):
        _heartbeat(m, a)
    _start_pane("clean", "submit")
    _start_pane("stuck", "submit")
    _tmux("send-keys", "-l", "-t", f"{SESSION}:stuck", "--", "run the full BGE sweep")
    time.sleep(0.4)

    report = m.pending_input_report(m.load_config())
    by_id = {r["agent"]: r for r in report["panes"]}
    assert by_id["clean"]["status"] == "empty"
    assert by_id["stuck"]["status"] == "pending"
    assert "run the full BGE sweep" in str(by_id["stuck"]["pending_text"])
    assert report["pending"] == ["stuck"]
    assert m.pending_exit_code(report) == m.EX_BLOCKED

    rc, out = _run(m, ["pending", "--json"])
    assert rc == m.EX_BLOCKED
    assert json.loads(out)["pending"] == ["stuck"]


def test_live_detector_sends_no_keys(live_bus):
    """READ-ONLY, asserted rather than asserted-in-a-comment: the pending text is still
    pending afterwards, neither submitted nor cleared."""
    m = _load(live_bus)
    _write_config(live_bus, ["stuck"])
    _heartbeat(m, "stuck")
    _start_pane("stuck", "submit")
    _tmux("send-keys", "-l", "-t", f"{SESSION}:stuck", "--", "do not touch me")
    time.sleep(0.4)
    before = _composer("stuck")

    _run(m, ["pending"])
    _run(m, ["pending", "--json"])
    assert _composer("stuck") == before


# ===================== C53: the cursor is NOT at the end of pending input =====================
#
# MEASURED 2026-08-12. Three live Claude panes held never-submitted instructions with
# the cursor parked at column 2 and the text entirely to its RIGHT — each string
# appearing exactly once in 3,000 rows of that pane's scrollback, i.e. never echoed
# into a transcript, i.e. never submitted. A cursor-prefix read reported all three
# EMPTY. These are the exact rows, with SGR, from `capture-pane -e`.

RAW_CLAUDE_PENDING = "\x1b[39m\u276f\u00a0\x1b[2mpull the next batch and keep going\x1b[0m"
RAW_CLAUDE_EMPTY = "\x1b[39m\u276f\u00a0"
# Codex, disposable `codexcal2` session, created and killed by the measurement.
RAW_CODEX_PLACEHOLDER = "\x1b[1m\u203a\x1b[0m \x1b[2mImprove documentation in @filename\x1b[0m"
RAW_CODEX_TYPED = "\x1b[1m\u203a\x1b[0m hello world this is typed"
# opencode, disposable `ocalib` session, created and killed by the measurement
# 2026-08-13. The glyph is `┃` (U+2503, blue 38;5;75) and the idle hint is gray
# (38;5;8) — NOT SGR-2 faint — followed by a white (38;5;15) return to normal.
RAW_OPENCODE_EMPTY = "\x1b[48;5;232m  \x1b[38;5;75m\u2503\x1b[38;5;15m\x1b[48;5;234m  \x1b[38;5;8mAsk anything... \"Fix a TODO in the codebase\"\x1b[38;5;15m\x1b[48;5;232m"
RAW_OPENCODE_TYPED = "  \x1b[38;5;75m\u2503\x1b[38;5;15m\x1b[48;5;234m  real instruction text"


def test_sgr_is_stripped_and_a_claude_pending_row_survives_as_content():
    m = _load()
    assert m._SGR_RE.sub("", RAW_CLAUDE_PENDING) == "\u276f\u00a0pull the next batch and keep going"
    assert not m._composer_row_is_empty(m._SGR_RE.sub("", RAW_CLAUDE_PENDING))
    assert m._composer_row_is_empty(m._SGR_RE.sub("", RAW_CLAUDE_EMPTY))


def test_faint_stripping_removes_the_codex_placeholder_and_keeps_typed_input():
    """The calibration, both directions. On Codex faint means PLACEHOLDER, so an empty
    composer must read empty — and real typed input, which carries no faint run, must
    survive stripping intact."""
    m = _load()
    assert m._composer_row_is_empty(m._SGR_RE.sub("", m._strip_faint_runs(RAW_CODEX_PLACEHOLDER)))
    kept = m._SGR_RE.sub("", m._strip_faint_runs(RAW_CODEX_TYPED))
    assert kept.strip() == "\u203a hello world this is typed"
    assert not m._composer_row_is_empty(kept)


def test_faint_stripping_is_never_applied_to_a_claude_pane():
    """MUTATION, visible: Claude renders PENDING INPUT faint, the exact opposite of
    Codex. Applying the Codex rule to a Claude pane would delete the hazard being read
    for — so the flag is asserted to be off for Claude, and the consequence of it
    being on is asserted too."""
    m = _load()
    assert m.composer_faint_is_placeholder(
        {"roster": [{"id": "a", "endpoint": "tmux:x:a", "backend": "codex"}]}, "a") is True
    assert m.composer_faint_is_placeholder(
        {"roster": [{"id": "a", "endpoint": "tmux:x:a", "backend": "claude"}]}, "a") is False
    # unknown backend fails CLOSED to "faint is content"
    assert m.composer_faint_is_placeholder({"roster": []}, "ghost") is False
    # and this is what it would cost if it were on for Claude:
    assert m._composer_row_is_empty(m._SGR_RE.sub("", m._strip_faint_runs(RAW_CLAUDE_PENDING)))


@pytest.mark.parametrize("closer", ["\x1b[0m", "\x1b[22m", "\x1b[m"])
def test_a_faint_run_is_closed_by_reset_or_explicit_unfaint(closer):
    """A regex pinned to one closing sequence would keep the placeholder the first
    time a TUI closed it with the other."""
    m = _load()
    row = f"\x1b[1m\u203a\x1b[0m \x1b[2mhint text{closer} kept"
    assert m._strip_faint_runs(row).endswith(" kept")
    assert "hint text" not in m._strip_faint_runs(row)


def test_opencode_gray_placeholder_is_stripped_and_typed_input_survives():
    """MEASURED 2026-08-13 against a live disposable opencode TUI. opencode's idle
    hint is gray 38;5;8 (NOT SGR-2 faint), so an empty composer must still read empty
    after stripping — and real typed input, which carries no gray run, must survive."""
    m = _load()
    assert m._composer_row_is_empty(m._SGR_RE.sub("", m._strip_faint_runs(RAW_OPENCODE_EMPTY)))
    kept = m._SGR_RE.sub("", m._strip_faint_runs(RAW_OPENCODE_TYPED))
    assert "real instruction text" in kept
    assert not m._composer_row_is_empty(kept)


def test_opencode_placeholder_stripping_only_for_an_opencode_pane():
    """The gate, same polarity as the Codex rule: opencode's gray hint is a
    placeholder ONLY on a pane positively identified as opencode. Claude stays off
    (its pending input is faint), unknown stays off (fail closed)."""
    m = _load()
    assert m.composer_faint_is_placeholder(
        {"roster": [{"id": "a", "endpoint": "tmux:x:a", "backend": "opencode"}]}, "a") is True
    assert m.composer_faint_is_placeholder(
        {"roster": [{"id": "a", "endpoint": "tmux:x:a", "backend": "claude"}]}, "a") is False
    assert m.composer_faint_is_placeholder({"roster": []}, "ghost") is False


def test_live_pending_text_to_the_right_of_the_cursor_is_seen(live_bus):
    """END TO END, and the defect in one assertion. A pane painted exactly like the
    live Claude panes — cursor at column 2, content to its right — must read as
    PENDING. A cursor-prefix read calls it empty, which is how four mains sat holding
    unsubmitted instructions while the detector reported the fleet clean."""
    m = _load(live_bus)
    _write_config(live_bus, ["ghosty"])
    _heartbeat(m, "ghosty")
    painted = "\\033[39m\u276f\u00a0\\033[2mpull the next batch and keep going\\033[0m\\033[3;3H"
    rc, out = _tmux("new-window", "-d", "-t", SESSION, "-n", "ghosty",
                    "sh", "-c", f"printf '\\033[2J\\033[3;1H{painted}'; sleep 60")
    assert rc == 0, out
    time.sleep(0.5)

    row, failure = m._read_composer_row(f"{SESSION}:ghosty")
    assert failure is None, failure
    assert "pull the next batch" in row, row
    assert not m._composer_row_is_empty(row)

    report = m.pending_input_report(m.load_config())
    assert report["pending"] == ["ghosty"], report["panes"]

    # ...and the same pane read the OLD way — sliced at the cursor — is invisible.
    cursor_prefix, failure = m._composer_text(f"{SESSION}:ghosty")
    assert failure is None, failure
    assert m._composer_row_is_empty(cursor_prefix), \
        "MUTATION CHECK: the cursor-prefix read must be the one that misses it"


# ================== C54: clear / submit — the detector's remedy half ==================


def _pending_now(m, window: str) -> str:
    row, failure = m._read_composer_row(f"{SESSION}:{window}")
    assert failure is None, failure
    return row


def _type(window: str, text: str) -> None:
    rc, out = _tmux("send-keys", "-l", "-t", f"{SESSION}:{window}", "--", text)
    assert rc == 0, out
    time.sleep(0.4)


def test_live_clear_empties_the_composer_and_the_detector_agrees(live_bus):
    """The keystroke is not the evidence: the composer is RE-READ, and so is the
    detector, because the whole point of `clear` is to move `pending` back to clean."""
    m = _load(live_bus)
    _write_config(live_bus, ["stuck"])
    _heartbeat(m, "stuck")
    _start_pane("stuck", "submit")
    _type("stuck", "Option A - I'll authorize the reboot")
    assert m.pending_input_report(m.load_config())["pending"] == ["stuck"]

    rc, out = _run(m, ["clear", "--agent", "stuck",
                       "--expect", "Option A - I'll authorize the reboot"])
    assert rc == 0, out
    assert m._composer_row_is_empty(_pending_now(m, "stuck")), _pending_now(m, "stuck")
    report = m.pending_input_report(m.load_config())
    assert report["pending"] == [] and m.pending_exit_code(report) == 0


def test_live_clear_logs_the_discarded_text_verbatim(live_bus):
    """A wrongly-discarded operator instruction must be recoverable from the ledger —
    that is the only reason discarding is allowed at all. `detail` may be trimmed;
    `pending_text` may not."""
    m = _load(live_bus)
    _write_config(live_bus, ["stuck"])
    _heartbeat(m, "stuck")
    _start_pane("stuck", "submit")
    text = "Understood - stopping here, re-dispatching to a fresh session."
    _type("stuck", text)

    assert _run(m, ["clear", "--agent", "stuck", "--force"])[0] == 0
    rows = _ledger(m)
    assert [r["kind"] for r in rows] == ["clear"]
    assert text in rows[0]["pending_text"]
    assert rows[0]["acknowledgement"] == "--force"


def test_live_expect_refuses_on_a_mismatch_and_changes_nothing(live_bus):
    """The TOCTOU defence: an operator who types between the read and the call cannot
    have the new sentence discarded by a decision made about the old one."""
    m = _load(live_bus)
    _write_config(live_bus, ["stuck"])
    _heartbeat(m, "stuck")
    _start_pane("stuck", "submit")
    _type("stuck", "the operator is still typing this")

    rc, out = _run(m, ["clear", "--agent", "stuck", "--expect", "some earlier text"])
    assert rc != 0, out
    assert "does not match" in out
    assert "the operator is still typing this" in _pending_now(m, "stuck")
    assert _ledger(m) == []


def test_live_neither_expect_nor_force_refuses_without_touching_the_pane(live_bus):
    """Discarding somebody's words must never happen by omission."""
    m = _load(live_bus)
    _write_config(live_bus, ["stuck"])
    _heartbeat(m, "stuck")
    _start_pane("stuck", "submit")
    _type("stuck", "half a thought")

    rc, out = _run(m, ["clear", "--agent", "stuck"])
    assert rc == m.EX_USAGE, out
    assert "half a thought" in _pending_now(m, "stuck")
    assert _ledger(m) == []


def test_live_submit_sends_the_pending_text_as_an_instruction(live_bus):
    """The other verb. mainC's pending text was CORRECT and wanted submitting; nothing
    on the pane says which case you are in, so the caller chooses."""
    m = _load(live_bus)
    _write_config(live_bus, ["ready"])
    _heartbeat(m, "ready")
    _start_pane("ready", "submit")
    _type("ready", "pull the next batch and keep going")

    rc, out = _run(m, ["submit", "--agent", "ready",
                       "--expect", "pull the next batch and keep going"])
    assert rc == 0, out
    assert m._composer_row_is_empty(_pending_now(m, "ready"))
    assert [r["kind"] for r in _ledger(m)] == ["submit"]
    # the fixture echoes a SUBMITTED message into its transcript — that is the
    # difference between submit and clear, asserted rather than assumed
    rc_c, pane = _tmux("capture-pane", "-p", "-t", f"{SESSION}:ready")
    assert "pull the next batch and keep going" in pane


def test_live_submit_refuses_an_empty_composer(live_bus):
    m = _load(live_bus)
    _write_config(live_bus, ["empty"])
    _heartbeat(m, "empty")
    _start_pane("empty", "submit")
    rc, out = _run(m, ["submit", "--agent", "empty", "--force"])
    assert rc != 0 and "EMPTY composer" in out
    assert _ledger(m) == []


def test_live_clear_on_an_already_empty_composer_is_a_no_op_success(live_bus):
    """Idempotent, so a coordinator can run it without first running `pending`."""
    m = _load(live_bus)
    _write_config(live_bus, ["empty"])
    _heartbeat(m, "empty")
    _start_pane("empty", "submit")
    rc, out = _run(m, ["clear", "--agent", "empty", "--force"])
    assert rc == 0 and "nothing to clear" in out
    assert _ledger(m) == []


def test_live_a_clear_that_does_not_take_is_reported_as_failure(live_bus):
    """MUTATION of the PANE rather than the code: a composer that ignores Ctrl-U must
    produce a loud failure and a `clear-unconfirmed` row, never a success. This is the
    keystroke-is-not-evidence rule, applied to the remedy."""
    m = _load(live_bus)
    _write_config(live_bus, ["deaf"])
    _heartbeat(m, "deaf")
    rc, out = _tmux("new-window", "-d", "-t", SESSION, "-n", "deaf",
                    sys.executable, str(FIXTURE), "--mode", "submit", "--ignore-clear")
    assert rc == 0, out
    time.sleep(0.6)
    _type("deaf", "this will not clear")

    rc, out = _run(m, ["clear", "--agent", "deaf", "--force"])
    assert rc != 0, out
    assert "NOT confirmed" in out
    assert [r["kind"] for r in _ledger(m)] == ["clear-unconfirmed"]
    assert "this will not clear" in _pending_now(m, "deaf")


@pytest.mark.parametrize(("argv", "acts"), [
    (["clear", "--agent", "k", "--force"], True),
    (["clear", "--agent", "k", "--expect", "some pending text"], True),
    (["clear", "--agent", "k", "--expect", "wrong text"], False),
    (["clear", "--agent", "k"], False),
    (["submit", "--agent", "k", "--force"], True),
    (["submit", "--agent", "k", "--expect", "wrong text"], False),
])
def test_no_path_through_clear_or_submit_can_emit_ctrl_c(live_bus, argv, acts, monkeypatch):
    """THE PROHIBITION, asserted over EVERY send-keys the command makes, on every
    branch — success, refusal and mismatch alike — not over the happy path. A second
    Ctrl-C exits a Codex session and destroys the window; it has already cost this
    fleet a main.

    `acts` is the anti-vacuity half, and it is not decoration: the refusal branches
    reach no `send-keys` at all, so a blanket "no C-c was sent" would pass them for the
    wrong reason. Each case therefore also asserts WHETHER it should have pressed a key,
    so the cases that prove the prohibition are the ones that actually press one.
    """
    m = _load(live_bus)
    _write_config(live_bus, ["k"])
    _heartbeat(m, "k")
    _start_pane("k", "submit")
    _type("k", "some pending text")

    sent: list[tuple] = []
    real = m._tmux
    monkeypatch.setattr(m, "_tmux", lambda *a: (sent.append(a) or real(*a)))
    _run(m, argv)
    keys = [a for a in sent if a and a[0] == "send-keys"]
    assert bool(keys) is acts, f"expected acts={acts}, sent {keys}"
    assert not any("C-c" in str(a) or "^C" in str(a) for a in keys), keys
    if acts:
        # C55 (2026-08-12) added the wake character: a bare key is a measured no-op
        # on a Claude composer holding queued text, so " " legitimately precedes the
        # real key. Widened to admit it — the invariant under test is the C-c
        # PROHIBITION above, and pinning the exact key spelling here made this
        # assertion fail on a correct fix instead of on a dangerous one.
        assert all(a[-1] in (" ", "C-u", "Enter") for a in keys), keys
        assert keys[-1][-1] in ("C-u", "Enter"), keys

#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Doorbell coverage for scripts/coordination/tmux_adapter.py (C45).

The doorbell replaces PAYLOAD nudges with a fixed, content-free, idempotent
ring — see the C45 block in tmux_adapter.py, directly above `doorbell_text`,
for the full design rationale (bus carries payload; the pane only ever needed
a signal to go check it). This file pins the two things that redesign depends
on actually holding:

  1. the guard set is EXACTLY the two pane-state guards documented there
     (pane alive, composer empty) — every OTHER guard the payload path
     applies (quiet-for, rate limit, heartbeat state, the C35 override
     machinery built to patch that state check) must NOT fire on this path,
     and the heartbeat must not even be READ, which is what made an
     idle-but-`working`-labelled agent unreachable for 33 minutes on
     2026-08-12 in the first place;
  2. the two guards that remain are fail-closed the same way the rest of this
     module is — an unreadable pane or composer refuses, it never assumes
     safe;
  3. the fixed string really is fixed: no `--message`, and `doorbell_text`
     substitutes only the agent id.

Two groups, the same split test_tmux_adapter_live.py uses and for the same
reason — most of this is pure guard logic that mocks answer faster and more
precisely than a real pty (in particular: mocking is the ONLY way to exercise
`pane_dead == "1"` directly, since this shared tmux server does not run with
`remain-on-exit` and flipping that GLOBALLY to observe it would touch the
live `agent` session's panes too — not worth the risk for a code path unit
tests already cover exactly), and the rest (does a REAL composer row actually
read as empty, does pending text really survive an unsubmitted doorbell) can
only be shown against a real one.

  unit  — cmd_doorbell against a stubbed `_tmux` / `_composer_text` /
          `resolve_target` / `load_config`; no tmux at all.
  live  — a real scratch tmux session, `doorbell-test-<pid>`, never the live
          `agent` session (see SAFETY below — same contract as
          test_tmux_adapter_live.py, and additionally: no global or
          session-wide tmux OPTION is ever changed, only per-session state
          this file created itself, because a `-g` option on a shared tmux
          server is visible to every other session on the host, `agent`
          included, for as long as it is set).

SAFETY: every tmux case runs in a throwaway session, killed on exit even on
failure; BUS_ROOT is redirected to a temp tree. The live group skips cleanly
if no tmux is reachable.

Run:
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_tmux_adapter_doorbell.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py"
SESSION = f"doorbell-test-{os.getpid()}"

DOORBELL_CONST = "Bus: unread inbox for {agent} — drain now."


def _load(tag: str):
    spec = importlib.util.spec_from_file_location(f"ta_doorbell_{tag}", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tmux(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return r.returncode, (r.stdout or r.stderr).strip()


def _subparser(parser: argparse.ArgumentParser, name: str) -> argparse.ArgumentParser:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[name]
    raise AssertionError("build_parser() produced no subparsers action")


class _A:
    """Minimal args namespace for cmd_doorbell — mirrors _Args in tests/test_tmux_adapter.py."""
    agent = "quiet"
    dry_run = False


def _poison(name: str):
    """A stand-in that FAILS the test the moment the doorbell path calls it.

    Used for `heartbeat` and `probe`: passing with this installed is the
    strongest available proof that a code path never consulted them, stronger
    than any live observation could be (a live pane can only show the call
    SUCCEEDED despite a `working` heartbeat on disk; it can't show the file
    was never opened).
    """
    def _boom(*_a, **_k):
        raise AssertionError(f"doorbell path must not call {name}()")
    return _boom


# ==========================================================================
# unit group — stubbed _tmux / _composer_text / resolve_target, no real pane
# ==========================================================================

def _stub(adapter, monkeypatch, tmp_path: Path, *, target="throwaway:pane",
          pane_dead: str = "0", composer: tuple[str | None, str | None] = ("", None),
          sendkeys_ok: bool = True, authorised: bool = True) -> list[tuple[str, ...]]:
    """Wire cmd_doorbell to a fake pane. ``composer`` is (text, failure_reason)."""
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    monkeypatch.setattr(adapter, "load_config",
                        lambda: {"flags": {"codex_sendkeys": "on" if authorised else "off"}})
    monkeypatch.setattr(adapter, "resolve_target",
                        lambda _cfg, _agent: (target, "stubbed") if target else (None, "no target"))
    calls: list[tuple[str, ...]] = []

    def fake_tmux(*args: str) -> tuple[int, str]:
        calls.append(args)
        if args[:2] == ("display-message", "-p"):
            return 0, pane_dead
        if args and args[0] == "send-keys":
            return (0, "") if sendkeys_ok else (1, "send-keys failed")
        return 0, ""

    monkeypatch.setattr(adapter, "_tmux", fake_tmux)
    monkeypatch.setattr(adapter, "_composer_text", lambda _t: composer)
    # C53 (2026-08-12): emptiness is now judged on the WHOLE composer row, read
    # separately from `_composer_text` (which stays cursor-anchored for fragment
    # matching). Both are driven from the one `composer` fixture value so a case
    # cannot accidentally describe two different panes.
    monkeypatch.setattr(adapter, "_read_composer_row",
                        lambda _t, _faint=False: (None, composer[1]) if composer[1]
                        else ((composer[0] or "").rsplit("\n", 1)[-1], None))
    monkeypatch.setattr(adapter, "composer_faint_is_placeholder", lambda _cfg, _a: False)
    # Poisoned: the doorbell path must never touch either — see the C45 block
    # and test_doorbell_does_not_consult_the_heartbeat_* below.
    monkeypatch.setattr(adapter, "heartbeat", _poison("heartbeat"))
    monkeypatch.setattr(adapter, "probe", _poison("probe"))
    return calls


def test_doorbell_text_is_exactly_the_constant_with_only_the_agent_substituted() -> None:
    adapter = _load("text")
    assert adapter.doorbell_text("mainA") == "Bus: unread inbox for mainA — drain now."
    assert adapter.doorbell_text("codex-inference") == \
        "Bus: unread inbox for codex-inference — drain now."
    assert adapter.DOORBELL_TEXT_TEMPLATE == DOORBELL_CONST
    # No caller-controllable content beyond the agent id. If an agent id itself
    # contained `{...}` it must NOT be re-interpreted as another template slot —
    # str.format substitutes once and does not recurse into the substituted value.
    assert adapter.doorbell_text("{agent}") == "Bus: unread inbox for {agent} — drain now."


def test_doorbell_string_stays_under_the_single_burst_paste_threshold() -> None:
    """The doorbell is the ONE send path that skips chunking — so its length is a
    load-bearing property, not a coincidence.

    `cmd_doorbell` sends the ring with a single unchunked `send-keys -l` because
    the string is ~45 chars, an order of magnitude under the smallest calibrated
    single-burst threshold (800 chars, Claude Code CLI v2.1.220; the C45 block
    records the bisection). Above that threshold the TUI renders a paste
    attachment, and Codex CAPS THAT ATTACHMENT'S CONTENT AT 1024 CHARS — which is
    the actual truncation that lost content from long dispatches.

    The exact-string test above would catch a template change today, but it pins a
    SPELLING: a legitimate reword that updates both the template and that assertion
    would sail past it while silently re-opening the hazard. This pins the PROPERTY
    instead. If the doorbell ever needs to carry more text, route it through
    `_send_message_chunked` rather than raising this bound.
    """
    adapter = _load("length")
    for agent in ("mainA", "codex-inference", "coordinator-agent", "a" * 64):
        rung = adapter.doorbell_text(agent)
        assert len(rung) < adapter.NUDGE_CHUNK_CHARS, (
            f"doorbell string for {agent!r} is {len(rung)} chars; it is sent UNCHUNKED, "
            f"so it must stay well under the 800-char paste threshold. Chunk it instead."
        )


def test_doorbell_subcommand_has_no_message_parameter() -> None:
    """The design point, made structural: passing --message must not even parse."""
    adapter = _load("noargmsg")
    doorbell_parser = _subparser(adapter.build_parser(), "doorbell")
    option_strings = {s for action in doorbell_parser._actions for s in action.option_strings}
    assert "--message" not in option_strings, \
        "doorbell must not accept caller-supplied content — that is the whole point of C45"
    assert "--agent" in option_strings
    with pytest.raises(SystemExit):
        adapter.build_parser().parse_args(
            ["doorbell", "--agent", "x", "--message", "inject a brief"])


def test_nudge_help_carries_the_deprecation_note() -> None:
    adapter = _load("depr")
    # The deprecation note lives in `help=`, which argparse renders in the
    # PARENT parser's listing (a subparser's OWN --help shows its usage/
    # options, not the one-line `help=` string the parent was given).
    top_level_help = adapter.build_parser().format_help().lower()
    assert "deprecated" in top_level_help
    assert "payload nudges are deprecated" in top_level_help
    assert "doorbell rings" in top_level_help
    # And nudge still parses and still requires --message — untouched otherwise.
    args = adapter.build_parser().parse_args(["nudge", "--agent", "x", "--message", "hi"])
    assert args.message == "hi" and args.func is adapter.cmd_nudge


def test_doorbell_refuses_when_not_authorised(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("noauth")
    calls = _stub(adapter, monkeypatch, tmp_path, authorised=False)
    assert adapter.cmd_doorbell(_A()) == adapter.EX_BLOCKED
    assert "codex_sendkeys is off" in capsys.readouterr().err
    assert calls == [], "refused before any tmux call"


def test_doorbell_refuses_when_target_does_not_resolve(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("notarget")
    calls = _stub(adapter, monkeypatch, tmp_path, target=None)
    assert adapter.cmd_doorbell(_A()) == adapter.EX_BLOCKED
    assert "no target" in capsys.readouterr().err
    assert calls == []


def test_doorbell_refuses_on_a_dead_pane(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("dead")
    calls = _stub(adapter, monkeypatch, tmp_path, pane_dead="1")
    assert adapter.cmd_doorbell(_A()) == adapter.EX_BLOCKED
    assert "is dead" in capsys.readouterr().err
    assert not any(c[0] == "send-keys" for c in calls), "a dead pane must never be typed into"
    assert not adapter.LEDGER.exists()


@pytest.mark.parametrize("unreadable_pane_dead", ["", "maybe", "0\t1"])
def test_doorbell_refuses_when_pane_dead_is_unreadable(
        unreadable_pane_dead: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("deadunread" + str(len(unreadable_pane_dead)))
    calls = _stub(adapter, monkeypatch, tmp_path, pane_dead=unreadable_pane_dead)
    assert adapter.cmd_doorbell(_A()) == adapter.EX_BLOCKED
    assert "fail closed" in capsys.readouterr().err
    assert not any(c[0] == "send-keys" for c in calls)


def test_doorbell_refuses_when_composer_is_unreadable(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("composerunread")
    calls = _stub(adapter, monkeypatch, tmp_path, composer=(None, "no cursor position"))
    assert adapter.cmd_doorbell(_A()) == adapter.EX_MISCONFIG
    err = capsys.readouterr().err
    assert "could not read the composer" in err and "no cursor position" in err
    assert not any(c[0] == "send-keys" for c in calls), \
        "an unreadable composer must refuse BEFORE typing anything"
    assert not adapter.LEDGER.exists()


@pytest.mark.parametrize("pending_composer", [
    "› restart the collector",             # operator mid-typing, Codex bare prompt
    "some prior line\n❱ half a message",   # Claude Code, transcript above + pending text
    "$ rm -rf ",                            # bare shell — the scariest case to submit blind
    "❱ x",                                  # one stray char past the recognised bare prompt
])
def test_doorbell_refuses_on_pending_composer_input(
        pending_composer: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("pending" + str(len(pending_composer)))
    calls = _stub(adapter, monkeypatch, tmp_path, composer=(pending_composer, None))
    assert adapter.cmd_doorbell(_A()) == adapter.EX_BLOCKED
    assert "holds pending input" in capsys.readouterr().err
    assert not any(c[0] == "send-keys" for c in calls), \
        "must never fire Enter into a pane with pending text"
    assert not adapter.LEDGER.exists()


@pytest.mark.parametrize("empty_composer", ["", "› ", "❱", "  ❱  ", "prior output\n› ", "   "])
def test_doorbell_allows_on_an_empty_composer_and_rings_the_exact_string(
        empty_composer: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _load("empty" + str(len(empty_composer)))
    calls = _stub(adapter, monkeypatch, tmp_path, composer=(empty_composer, None))
    assert adapter.cmd_doorbell(_A()) == 0
    sent = [c for c in calls if c and c[0] == "send-keys" and "-l" in c]
    assert len(sent) == 1
    assert sent[0][-1] == "Bus: unread inbox for quiet — drain now."
    assert any(c == ("send-keys", "-t", "throwaway:pane", "Enter") for c in calls)
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["kind"] == "doorbell" and rows[0]["agent"] == "quiet"
    assert rows[0]["detail"] == "Bus: unread inbox for quiet — drain now."


def test_doorbell_does_not_consult_the_heartbeat_even_when_it_would_refuse_a_nudge(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE POINT of C45. A `working` heartbeat blocks `nudge`; it must not even
    be READ on the doorbell path. `heartbeat` and `probe` are poisoned in
    `_stub`; a clean rc==0 here means neither was ever called."""
    adapter = _load("nohbcheck")
    _stub(adapter, monkeypatch, tmp_path, composer=("❱ ", None))
    assert adapter.cmd_doorbell(_A()) == 0


def test_doorbell_dry_run_sends_nothing_and_writes_no_ledger_row(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("dryrun")
    class Args(_A):
        dry_run = True
    calls = _stub(adapter, monkeypatch, tmp_path, composer=("", None))
    assert adapter.cmd_doorbell(Args()) == 0
    assert not any(c[0] == "send-keys" for c in calls)
    assert not adapter.LEDGER.exists()
    assert "would ring doorbell" in capsys.readouterr().out


def test_doorbell_refuses_when_sendkeys_message_call_fails(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    adapter = _load("sendfail")
    _stub(adapter, monkeypatch, tmp_path, composer=("", None), sendkeys_ok=False)
    assert adapter.cmd_doorbell(_A()) == adapter.EX_MISCONFIG
    # C51 routes every post-typing failure through one loud exit that also rolls the
    # text back and records the non-delivery; the wording moved with it.
    err = capsys.readouterr().err
    assert "NOT DELIVERED" in err and "send-keys message" in err
    # The non-delivery IS recorded now — that is C51's point, and it is what makes a
    # failed ring answerable from durable state instead of only from an exit code
    # nobody kept. What must never appear is a `doorbell` row for a ring that failed.
    rows = [json.loads(ln) for ln in adapter.LEDGER.read_text().splitlines() if ln.strip()]
    assert [r["kind"] for r in rows] == ["doorbell-undelivered"]


def test_doorbell_is_never_rate_limited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ringing twice back-to-back is a no-op by design — there is no
    --min-interval-s for doorbell and cmd_doorbell never reads
    seconds_since_last_nudge or the ledger's nudge history."""
    adapter = _load("norate")
    _stub(adapter, monkeypatch, tmp_path, composer=("", None))
    assert adapter.cmd_doorbell(_A()) == 0
    assert adapter.cmd_doorbell(_A()) == 0     # would be refused for `nudge` inside 600s
    rows = [json.loads(l) for l in adapter.LEDGER.read_text().splitlines() if l.strip()]
    assert len(rows) == 2 and all(r["kind"] == "doorbell" for r in rows)


def test_nudge_subcommand_is_unchanged_by_the_doorbell_addition(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Requirement 3: nudge keeps working untouched. Not a full re-test of C6/C12/
    C35 (tests/test_tmux_adapter.py already covers those in depth) — just a
    live smoke check that cmd_nudge's own guard chain (quiet-for, heartbeat,
    rate limit) is still wired, unlike cmd_doorbell's deliberately bare one."""
    adapter = _load("nudge_smoke")
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    monkeypatch.setattr(adapter, "load_config", lambda: {})
    monkeypatch.setattr(adapter, "probe", lambda *_a: {
        "nudge_ok": False, "target": "throwaway:pane", "seconds_since_last_nudge": None,
        "blockers": ["heartbeat says working (task t)"],
    })
    class NA:
        agent = "quiet"; message = "status please"; min_interval_s = 600.0
        dry_run = False; quiet_s = 20.0; heartbeat_max_age = 900.0; settle_s = 0.0
    assert adapter.cmd_nudge(NA()) == adapter.EX_BLOCKED, \
        "nudge must still refuse on a working heartbeat — that guard is unchanged"


# ==========================================================================
# live group — a real scratch tmux session, never the live `agent` session
# ==========================================================================

def _write_config(bus_root: Path, roster: list[dict]) -> None:
    cfg = {"roster": roster, "flags": {"codex_sendkeys": "on"},
           "tmux": {"live_session": SESSION, "allow_session_creation": False}}
    (bus_root / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _load_live(bus_root: Path, tag: str):
    m = _load(f"live_{tag}")
    m.BUS_ROOT = bus_root
    m.LEDGER = bus_root / "adapter-ledger.jsonl"
    return m


@pytest.fixture()
def live_session():
    rc, _ = _tmux("-V")
    if rc != 0:
        pytest.skip("no tmux reachable")
    # A long-lived placeholder window keeps the SESSION alive independent of
    # whatever the per-test windows do — an all-window-exited session is torn
    # down by tmux itself, taking every fixture window with it (measured while
    # building this file: a session created with only a `true`-running window
    # vanishes within ~1s, before a test ever gets to inspect it).
    _tmux("new-session", "-d", "-s", SESSION, "-n", "placeholder", "sleep", "600")
    try:
        yield
    finally:
        _tmux("kill-session", "-t", SESSION)


def test_live_doorbell_rings_a_genuinely_empty_composer(
        live_session, tmp_path: Path) -> None:
    """A real bare-prompt pane (nothing printed before the read, matching a TUI
    at rest with no placeholder text): guard (b) must read it as empty and the
    EXACT fixed string must land, verified from a fresh capture-pane, not from
    the send-keys call the adapter made."""
    _tmux("new-window", "-d", "-t", SESSION, "-n", "quiet", "sh", "-c",
         "printf '\\033[999;1H'; IFS= read -r line; printf 'SUBMITTED:%s\\n' \"$line\"; sleep 600")
    time.sleep(0.3)
    m = _load_live(tmp_path, "quiet")
    (tmp_path / "heartbeats").mkdir(parents=True, exist_ok=True)
    # A `working` heartbeat sitting on disk, unread — reinforces the unit-level
    # poison-pill proof with one real end-to-end path.
    (tmp_path / "heartbeats" / "quiet.json").write_text(
        json.dumps({"agent": "quiet", "state": "working", "task_id": "t", "ts": "2026-08-12T00:00:00+00:00"}))
    _write_config(tmp_path, [{"id": "quiet", "endpoint": f"tmux:{SESSION}"}])

    args = _A(); args.agent = "quiet"
    rc = m.cmd_doorbell(args)
    assert rc == 0, f"expected success against a bare-prompt pane (rc={rc})"

    time.sleep(0.3)
    rc_c, pane = _tmux("capture-pane", "-p", "-t", f"{SESSION}:quiet")
    assert rc_c == 0
    assert "Bus: unread inbox for quiet — drain now." in pane

    rows = [json.loads(l) for l in m.LEDGER.read_text().splitlines() if l.strip()]
    assert len(rows) == 1 and rows[0]["kind"] == "doorbell"

    # Doorbell rings TWICE with no rate limit — the real end-to-end version of
    # test_doorbell_is_never_rate_limited above.
    rc2 = m.cmd_doorbell(args)
    assert rc2 == 0, "a second, immediate ring must not be rate-limited"
    rows2 = [json.loads(l) for l in m.LEDGER.read_text().splitlines() if l.strip()]
    assert len(rows2) == 2


def test_live_doorbell_refuses_pending_composer_input_and_leaves_it_untouched(
        live_session, tmp_path: Path) -> None:
    """An operator (or agent) with unsubmitted text in the composer: guard (b)
    must refuse BEFORE typing anything, and the pending text must survive
    completely unsubmitted — no Enter, no SUBMITTED echo, text still there."""
    _tmux("new-window", "-d", "-t", SESSION, "-n", "typing", "sh", "-c",
         "printf '\\033[999;1H'; IFS= read -r line; printf 'SUBMITTED:%s\\n' \"$line\"; sleep 600")
    time.sleep(0.3)
    _tmux("send-keys", "-l", "-t", f"{SESSION}:typing", "--", "rm -rf something-important")
    time.sleep(0.3)

    m = _load_live(tmp_path, "typing")
    _write_config(tmp_path, [{"id": "typing", "endpoint": f"tmux:{SESSION}"}])
    args = _A(); args.agent = "typing"
    rc = m.cmd_doorbell(args)
    assert rc == m.EX_BLOCKED, f"expected refusal against a pane with pending text (rc={rc})"
    assert not m.LEDGER.exists()

    rc_c, pane = _tmux("capture-pane", "-p", "-t", f"{SESSION}:typing")
    assert rc_c == 0
    assert "rm -rf something-important" in pane, "the pending text must still be sitting there"
    assert "SUBMITTED" not in pane, "no Enter may have been sent — the read must not have returned"
    assert "Bus: unread inbox" not in pane, "the doorbell string must never have been typed either"


def test_live_doorbell_refuses_a_vanished_window(live_session, tmp_path: Path) -> None:
    """The same characterisation test_tmux_adapter_live.py uses for its own dead-
    pane case ("a dead or vanished pane is never nudge_ok"): this shared tmux
    server does not run with `remain-on-exit`, so an exited pane's WINDOW is
    reaped rather than left as pane_dead=1 (verified while building this file —
    flipping `remain-on-exit` globally to observe the literal state is a
    server-wide option change, visible to the live `agent` session, and not
    worth the risk for a branch the unit group already covers directly). What
    IS safely observable here is guard (a)'s other half: `resolve_target`
    refusing on a window that no longer exists, which cmd_doorbell must also
    refuse on rather than guessing a pane."""
    _tmux("new-window", "-d", "-t", SESSION, "-n", "dies", "true")
    time.sleep(1.0)   # let tmux reap the exited command
    rc_l, wins = _tmux("list-windows", "-t", SESSION, "-F", "#{window_name}")
    assert rc_l == 0 and "dies" not in wins.split(), \
        f"PREMISE: the window must actually be gone by now ({wins!r})"

    m = _load_live(tmp_path, "dies")
    _write_config(tmp_path, [{"id": "dies", "endpoint": f"tmux:{SESSION}:dies"}])
    args = _A(); args.agent = "dies"
    rc = m.cmd_doorbell(args)
    assert rc == m.EX_BLOCKED
    assert not m.LEDGER.exists()

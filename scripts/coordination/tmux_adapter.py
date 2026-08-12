#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""tmux_adapter.py — nudge and spawn agent mains in tmux (M5, grant-gated).

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md (M5)
Gate:           OP-SENDKEYS-CODEX — granted by the operator 2026-07-27
Caps:           flags.codex_sendkeys, caps.max_concurrent_mains (live windows, C9)

DELIBERATELY TINY, per the handoff. Two verbs that touch tmux, one that only
looks. Everything else about coordination lives on the bus.

WHY THE "IDLE-PANE CHECK" IS NOT A tmux CHECK. The handoff asks for an idle-pane
check before send-keys, and the obvious implementation does not work here:
`pane_current_command` reads `claude`/`node` whether the session is at a prompt or
mid-generation, and `pane_last_activity` is EMPTY on this tmux build (3.5a) — using
it yields nonsense (a "quiet_for" of 1.7 billion seconds). So the check is built
from signals that do carry values, and the decisive one is the bus's own:

  1. the pane exists and `pane_dead == 0`
  2. `window_activity` has been quiet for >= --quiet-s (output has stopped)
  3. the agent's heartbeat does NOT say `working`, and is fresh

(2) is window-level, not pane-level; every window here holds one pane, so it is
equivalent in practice, and this is stated rather than assumed. (3) is the
authoritative one — the agent is the only party that knows whether it is thinking,
and the protocol already has it declare that.

FAIL-CLOSED THROUGHOUT. Typing into a pane mid-generation corrupts the prompt of
whatever is running there, so every unevaluable signal blocks the nudge. Unlike
the edit-time guards, erring permissive here damages someone else's session.

EVERY SPAWNED MAIN IS A WINDOW IN THE ONE LIVE SESSION (operator, 2026-07-27).
`tmux.live_session` in config declares it; spawn refuses any other session, refuses
a non-tmux endpoint, and never calls `new-session` — throwaway sessions exist only
so the test suite can avoid touching the live one.

NEVER GUESS A PANE. An endpoint of `tmux:agent` names a session but not a window.
Rather than picking one, this refuses: sending keystrokes to the wrong pane is the
exact disaster the guards exist to prevent. Endpoints must be
`tmux:<session>:<window>`, or a window whose name equals the agent id must exist.

SUBMISSION IS VERIFIED AGAINST THE BUFFER, NOT THE KEYSTROKES (C51, 2026-08-12).
`send-keys` exiting 0 means tmux accepted the keys, never that the TUI consumed
them. So both send paths confirm the composer buffer returned to the exact value it
held before this adapter typed anything, and any failure after the first character
is typed rolls that text back with Ctrl-U (never Ctrl-C — the second Ctrl-C exits a
Codex session and destroys the window) and writes a `*-undelivered` ledger row.
Nothing is reported delivered on the strength of a dispatched keystroke.

Usage:
    tmux_adapter.py probe    --agent codex                 # all guard signals, no action
    tmux_adapter.py nudge    --agent codex --message "..."  # send-keys, guarded (DEPRECATED payload)
    tmux_adapter.py doorbell --agent codex                  # fixed ring, two guards, bus carries payload
    tmux_adapter.py pending                                 # which panes hold unsubmitted input
    tmux_adapter.py spawn    --agent new-main               # 4 bus files, then a pane
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"
LEDGER = BUS_ROOT / "adapter-ledger.jsonl"      # coordinator-daemon owned

EX_BLOCKED = 2
EX_MISCONFIG = 3
EX_USAGE = 64

# ---------------------------------------------------------------------------
# DISPOSABLE-TUI CALIBRATION, 2026-07-28 (sessions `tuical-codex` / `tuical-claude`,
# both killed; the live `agent` session was never touched). This replaces the
# previous guesses. Measured facts, all reproducible:
#
#  A. SINGLE-BURST PASTE THRESHOLD. One `send-keys -l` call carrying N chars is
#     rendered as literal typed text below a threshold and as a paste attachment
#     at or above it. Bisected:
#         Codex CLI v0.145.0 : 1000 -> typed, 1001 -> "[Pasted Content 1001 chars]"
#         Claude Code v2.1.220:  800 -> typed,  805 -> "[Pasted text #n]"
#     The original 1018-char failure report was the Codex side of this.
#  B. CONTENT LOSS ABOVE THE BLOB. Codex blobs cap at 1024 chars: a 1498- and a
#     2998-char burst both rendered "[Pasted Content 1024 chars]". That is the
#     real mangling — not the blob itself.
#  C. CHUNKING BELOW THE THRESHOLD IS SAFE. Sending the message in 400-char
#     chunks with a 0.15 s gap renders as ordinary typed text with no blob and
#     no loss, verified at 1200 / 2000 / 3000 / 5000 / 12000 chars on BOTH TUIs.
#     A 0.0 s gap re-coalesces into one burst and DOES blob — the gap is load
#     bearing. 400 is half of the lower (Claude) threshold.
#  D. So the 240-char cap was ~3.3x below the true single-burst limit and is not
#     the binding constraint at all once (C) is used. 4000 is a policy ceiling
#     (past it, write a brief file), a third of the largest verified length.
MAX_NUDGE_MESSAGE_CHARS = 4000
NUDGE_CHUNK_CHARS = 400
NUDGE_CHUNK_DELAY_S = 0.15
DEFAULT_NUDGE_SETTLE_S = 0.25
# C30(b): how long a freshly spawned window must SURVIVE before spawn reports success.
# `new-window` exit 0 only means tmux accepted the request. A spawned codex pane died
# instantly on an update prompt and spawn still reported success. Module-level so tests
# can drive it to 0 — a suite that sleeps for real is a suite people stop running.
SPAWN_SETTLE_S = 2.0
# Bounded polls, so a slow redraw is a wait rather than a false refusal.
_VERIFY_TIMEOUT_S = 2.0
# C55: pause between the wake character and the action key. The composer needs a beat
# to register the first keystroke; sending both in the same instant reproduces the bug.
_WAKE_SETTLE_S = 1.0
_VERIFY_POLL_S = 0.1
# An accepting post-Enter observation must repeat before it is believed: a single
# capture can land on a half-drawn repaint frame in which the composer has been
# cleared for redraw but the Enter was in fact swallowed.
_VERIFY_STABLE_SAMPLES = 2
# Codex renders "[Pasted Content 1016 chars]", Claude Code "[Pasted text #5]".
_PASTE_BLOB_MARKER = "[Pasted"
# Leading characters that put a TUI composer into a mode where Enter does NOT
# submit prose. `/` opens the command menu and `@` the file picker in both TUIs —
# Enter then ACCEPTS a completion, which rewrites the composer while leaving the
# cursor off the message, i.e. it looks exactly like a submission to any check
# that reads the pane. Claude Code additionally treats a leading `!` as bash mode
# and `#` as a memory write, so a nudge starting with either would EXECUTE rather
# than say something. There is no pane state that distinguishes these after the
# fact, so the trigger is refused up front instead of being detected afterwards.
_COMPOSER_MODE_PREFIXES = ("/", "!", "#", "@")
# `@` opens Codex's file picker — but only when it STARTS A TOKEN, which is what
# the picker binds to. C13 (closed 2026-08-11): the guard refused the character
# ANYWHERE, so `ops@example.com` and "the rate limit is 600s @ default" were
# rejected as picker triggers. The original filing chose the broad form knowingly
# ("a false refusal costs a rephrase, a false accept fires Enter into a picker")
# and said to narrow it if it proved annoying; it did, on a message about an email
# address. Narrowed to the actual hazard, NOT relaxed: `@` after whitespace or at
# the start of the message still refuses, because that is the shape the picker
# opens on. `foo@bar` cannot open it — the token already began.
_INLINE_PICKER_TRIGGER = "@"
_INLINE_PICKER_RE = re.compile(r"(?:^|\s)@")
# How far back from the cursor a paste banner can sit on the composer line.
_BLOB_LOOKBACK_CHARS = 200
_FRAGMENT_CHARS = 60

# C9, 2026-07-28. The spawn cap bounds SIMULTANEOUS mains, not spawn actions per
# day; see live_mains(). The old key is refused rather than reinterpreted — see
# resolve_spawn_cap().
CAP_KEY = "max_concurrent_mains"
LEGACY_CAP_KEY = "max_spawns_per_day"

# ---------------------------------------------------------------------------
# C35, 2026-07-29. PANE QUIESCENCE OVERRIDES A `working` HEARTBEAT.
#
# THE DEADLOCK. The `state == working` blocker is correct in principle — typing
# into a pane mid-generation corrupts whatever is running there. But a main that
# FINISHES a unit and settles at its prompt very often still says `working`,
# because the code that would update the heartbeat is exactly the code that has
# stopped running. The session cannot clear the flag, because clearing it
# requires being told to, which is what the guard refuses. `--heartbeat-max-age`
# does NOT rescue it: the refusal keys on STATE, not age, so a heartbeat can be
# five seconds old and still wedge the session forever.
#
# COST, measured 2026-07-29: the operator hand-relayed into panes at least four
# times in one day, including into `mainA` while it held the ENTIRE machine for
# an exclusive E5 decision-grade window — the most expensive possible idle state,
# since nothing else can use the host either. One stretch saw ten consecutive
# nudge attempts refused against a session provably sitting at an empty prompt.
#
# THE SIGNAL. Both TUIs redraw continuously while working: a spinner with an
# elapsed-seconds counter, token counts, streaming output. So `window_activity`
# moves about once a second during generation, and a window quiet for MINUTES is
# very strong evidence the session is settled at its prompt regardless of what
# its heartbeat claims. This is the same reasoning the existing `--quiet-s`
# check already encodes, at a much longer and therefore much safer horizon.
#
# CALIBRATION, 2026-07-29, disposable sessions `tuiok-*` (created and killed by
# the measurement; the live `agent` session was never written to). Two windows,
# one emitting 5x/second and one idle, sampled across the full matrix of
# {detached, attached} x {background, active}:
#
#     condition                       busy window     idle window
#     detached, background            0-1s            aged 35 -> 51s
#     attached, background            0-1s            aged 54 -> 70s
#     attached, active/visible        0-1s            aged 73 -> 90s
#     detached again, background      0-1s            aged 84 -> 139s
#
#   The busy window NEVER exceeded 1s of apparent quiet in any condition, while
#   the idle window aged monotonically. 120s is therefore ~120x the largest gap
#   ever observed on a window that was genuinely producing output.
#
#   Corroborated against the live `agent` session read-only (display-message
#   only): working mains and the constantly-redrawing htop/btop windows sat at
#   0-2s while two settled mains showed 209s and 211s. Real Claude Code and
#   Codex TUIs, not just the synthetic emitter.
#
# TWO EARLIER MEASUREMENTS OF THIS SAME SIGNAL WERE WRONG, both by the same
# class of test-method defect, and both are worth knowing about before anyone
# re-measures it:
#   (a) the default shell here is fish, so a `bash`-syntax loop handed to
#       `tmux new-window` dies instantly and the window closes — while
#       `new-window` still exits 0. That is C30(b) exactly, met again in the
#       measurement rather than in production.
#   (b) `automatic-rename` renames a window to its running command, after which
#       a NAME-based target stops resolving and `display-message` falls back to
#       the session's CURRENT window — so several windows silently report one
#       window's numbers. Address windows by INDEX when measuring.
# Both artefacts produce the same false reading: "a busy window looks quiet",
# which would argue against this override. Verify the pane is alive and its
# target resolves before believing any quiet number.
#
# WHY THE THRESHOLD IS A FLAG. The safe value depends on how the fleet is run
# (a main that shells out to a long silent build redraws less than one that
# streams tokens). Making it explicit means a nudge that overrides is always
# traceable to a number someone chose, not to an implicit rule.
#
# C52 (2026-08-12) NARROWED THIS THRESHOLD'S ROLE — read that block before changing
# the number. Quiescence is no longer the only thing that may overrule a `working`
# heartbeat, and it is no longer the first thing consulted: the pane's generation /
# compaction marker is, and a marker-free pane that has merely passed `--quiet-s`
# already contradicts the claim. So this threshold now decides only when the pane
# cannot be read for a marker at all. That is deliberate. The 20s-to-120s gap between
# `--quiet-s` and this value was the exact habitat of the deadlock C52 fixes: a main
# settled at its prompt was nudgeable by every guard except the one it could not
# clear. Raising this number no longer makes the guard stricter in the common case;
# it only widens the fallback for unreadable panes.
DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S = 120.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tmux(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return r.returncode, (r.stdout or r.stderr).strip()


def _composer_text(target: str) -> tuple[str | None, str | None]:
    """Return everything on the pane up to the CURSOR, or a fail-closed reason.

    ITS PREMISE IS NOW KNOWN TO BE PARTIAL — read the C53 block before extending this
    to any new question. The paragraph below states that the cursor sits at the end of
    pending input; measured 2026-08-12 on live panes, it does so while input is being
    ENTERED but not in every resting state — a composer can hold a full sentence with
    the cursor parked at column 2 and the text to its RIGHT, where this function cannot
    see it. That does not affect what this is used for (matching a fragment WE just
    typed, at the moment we typed it, which is the entered state), and the C6 reasoning
    below is unchanged for that use. It does mean this must never be used to answer "is
    the composer empty" — `_read_composer_row` reads the whole row for that.

    WHY THE CURSOR, AND NOT A ROW WINDOW. Measured 2026-07-28 in disposable Codex
    and Claude Code sessions: the terminal cursor sits at exactly the end of the
    pending (typed-but-unsubmitted) input, in both TUIs, with or without a modal
    overlay open. Two consequences that the previous two fixes both missed:

      1. Overlays render BELOW the cursor line. With Codex's `@` picker open (a
         multi-row list) the cursor stayed on the composer at cx=3 and the typed
         text still ended at it. So an overlay CANNOT displace this anchor, which
         is why this predicate is structurally immune to the false negatives that
         a "last N rows" window produced.
      2. After a successful Enter, BOTH TUIs echo the submitted message into the
         transcript, where it stays visible. Measured directly: post-Enter the
         message was still in the pane while the cursor sat on an empty composer.
         So "message still visible" is the SUCCESS rendering, and the previous
         "text present after Enter => unsubmitted" rule fired on every good nudge.
         Anchoring at the cursor separates the two: on success the composer no
         longer ENDS with the message; on a swallowed Enter it still does.

    Plain `capture-pane` (no -J) is mandatory here: `cursor_y` indexes the physical
    grid, and -J would join wrapped rows and shift every index under it.
    """
    try:
        pos = subprocess.run(
            ["tmux", "display-message", "-p", "-t", target, "#{cursor_y}\t#{cursor_x}"],
            capture_output=True, text=True, timeout=15)
        pane = subprocess.run(["tmux", "capture-pane", "-p", "-t", target],
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not read pane for submission verification: {exc}"
    if pos.returncode != 0 or pane.returncode != 0:
        out = (pos.stdout or pos.stderr or "") + (pane.stdout or pane.stderr or "")
        return None, f"could not read pane for submission verification: {out.strip()}"
    raw = (pos.stdout or "").strip().split("\t")
    if len(raw) < 2:
        return None, f"tmux gave no cursor position for {target!r}; cannot verify"
    try:
        cy, cx = int(raw[0]), int(raw[1])
    except ValueError:
        return None, f"tmux gave an unreadable cursor position {raw!r}; cannot verify"
    lines = (pane.stdout or "").split("\n")
    if cy >= len(lines):
        return None, f"cursor row {cy} is outside the captured pane ({len(lines)} rows)"
    return "\n".join(lines[:cy] + [lines[cy][:cx]]), None


def _normalise(text: str) -> str:
    """Drop ALL whitespace.

    Measured 2026-07-28: raw substring matching is unreliable because both TUIs
    soft-wrap the composer themselves, and a wrap can fall INSIDE the fragment.
    At 300/848/900/998 chars a raw match failed while the text had landed
    perfectly; whitespace-stripped matching succeeded in every one of those
    cases. This — not overlays — is the main source of the "did not land"
    false refusals seen in normal operation.
    """
    return "".join(text.split())


def _pending_fragment(message: str) -> str:
    """A tail fragment; anchored at the cursor it is unambiguous at 60 chars.

    Trailing whitespace is dropped FIRST. Matching is whitespace-insensitive, so
    a fragment made only of spaces normalises to "" — and ``endswith("")`` is
    true of every pane, which would make the pre-Enter gate pass unconditionally
    and fire Enter into a pane that never received the text.
    """
    trimmed = message.rstrip()
    return trimmed[-min(len(trimmed), _FRAGMENT_CHARS):]


# ---------------------------------------------------------------------------
# C45, 2026-08-12. THE DOORBELL: nudges stop carrying payload.
#
# THE FAILURE THIS REPLACES. `probe`'s `state == "working"` blocker (see the
# C35/R1/C36 blocks above) is correct in principle for a PAYLOAD nudge — typing
# a brief into a pane mid-generation corrupts whatever is running there — but it
# is the wrong tradeoff for the common case, where the message carries no new
# information at all ("you have mail, go read it"). On 2026-08-12 an
# idle-but-`working`-labelled agent sat unreachable for 33 minutes because
# every nudge attempt refused on the heartbeat state, and nothing could clear
# the flag because clearing it is what the refused nudge would have done. C35's
# quiescence override and C36's runtime-liveness signal both exist to patch
# exactly this deadlock for the PAYLOAD path — and both remain necessary there,
# because a payload nudge really can corrupt a mid-generation pane.
#
# THE REDESIGN. Payload moves entirely to the bus, which already is durable,
# schema-validated and cursor-tracked (see BUS_PROTOCOL.md) — it does not need
# a tmux pane to carry it reliably, and never did. The pane only ever needed a
# DOORBELL: a signal to go check the bus. So `doorbell` sends a fixed,
# content-free, idempotent string and nothing else — no `--message`, because a
# caller-controlled string is a payload nudge wearing a different name. Once
# nothing an agent DOES (drains a bus message, keeps generating, sits at an
# empty prompt) changes what the doorbell says, most of the reasons a payload
# nudge must be refused stop applying to it:
#
#   * quiet-for (window_activity < --quiet-s)     NOT applied. A short fixed
#     line buffers safely inside a busy composer and submits cleanly once
#     generation stops — the whole reason chunking/pacing exists for nudge is
#     to survive a PASTE-BLOB threshold on a LONG message; the doorbell string
#     is ~45 chars, an order of magnitude under the smallest calibrated
#     single-burst limit (800 chars, Claude Code). There is nothing here for
#     the quiet-for check to protect against.
#   * rate limit (--min-interval-s)                NOT applied. Ringing twice
#     is a no-op by design: the second ring says exactly what the first one
#     said, to an agent that either already drained (so the doorbell is inert)
#     or still has not (so ringing again is the correct behaviour, not spam).
#     A payload nudge earns a rate limit because repetition means the operator
#     is re-typing a brief into a live session; a doorbell has no brief to
#     re-type.
#   * heartbeat-state refusal (`state == "working"`) NOT applied. THIS is the
#     guard whose removal fixes the 33-minute incident above, and it is safe to
#     remove here specifically because of what the message no longer does: it
#     does not interrupt a task with new instructions, it cannot corrupt a
#     mid-generation composer with foreign content (see guard (b) below — the
#     composer-empty check is what still protects a genuinely mid-typing pane),
#     and an agent correctly mid-generation simply keeps generating with three
#     extra harmless lines in its scrollback. The failure mode C35/C36 exist to
#     avoid — believing a stale `working` self-report and typing a live brief
#     into a busy pane — cannot happen here because there is no brief.
#   * C35's quiescence-override machinery                NOT applied, and not
#     merely "applied but never triggers": there is no `working` blocker on
#     this path for it to override, so wiring it in would be dead code arguing
#     with a guard that no longer exists. C35 (and its R1 stale-heartbeat
#     sibling) stay exactly as they are for `nudge` — this module still owns a
#     real payload path, and it still needs a real deadlock escape hatch.
#
# WHAT STAYS, AND WHY THESE TWO ARE LOAD-BEARING WHERE THE OTHERS ARE NOT.
# Both guards below protect against the SAME hazard class — an Enter landing
# somewhere it corrupts — which none of the four removed guards do:
#
#   (a) pane exists and is not dead. An Enter (and the string ahead of it) sent
#       to a pane that no longer exists is not caught by tmux — `send-keys` to
#       a dead/gone target simply fails or silently goes nowhere — so this is
#       the same "does the target still exist" question `resolve_target` and
#       `probe`'s `pane_dead` read already answer for `nudge`, asked fresh
#       (state can change between resolution and send) and answered the same
#       fail-closed way: unreadable is refused, not assumed alive.
#   (b) the composer holds no pending input. This is the one hazard a
#       content-free message does NOT remove: the doorbell's Enter is still a
#       real Enter, and Enter always submits whatever is already sitting in
#       the composer, doorbell text or not. If an operator (or the agent
#       itself) has half-typed something and not yet submitted it, ringing the
#       doorbell submits THAT, not the doorbell string. This is a hazard the
#       payload path also has — see the C6/C12 cursor-anchored submission
#       machinery above — but `nudge` gets to defend against it by verifying
#       ITS OWN fragment lands before pressing Enter. A doorbell has no
#       fragment of its own to plant first; it must instead confirm the
#       composer is empty BEFORE typing anything, or refuse.
#
# See `_composer_row_is_empty` for how (b) is read, and its docstring for the
# one thing this check is known not to distinguish (a placeholder/hint string
# a TUI might render at an empty prompt from real pending content) — that case
# fails CLOSED (reads as non-empty, refuses), which is the safe direction: a
# doorbell that occasionally over-refuses costs a retry; one that fires into
# half-typed text does not.
DOORBELL_TEXT_TEMPLATE = "Bus: unread inbox for {agent} — drain now."
# Codex's bare prompt is "› ", Claude Code's is "❱ " (both calibrated in the
# C6 block above and used throughout tests/test_tmux_adapter.py as the bare-
# prompt fixture for each TUI). A composer showing only one of these — or
# nothing at all, the disposable-shell fixture's bare state — has no pending
# input. Anything else on the row is real content, typed by the operator or
# left behind by the agent, and must not be typed over.
#
# C51, 2026-08-12: "❯" (U+276F) WAS MISSING AND THAT MADE THIS TABLE WRONG FOR THE
# WHOLE LIVE FLEET. Measured read-only against all ten windows of the live `agent`
# session at 10:52Z: every Claude Code main (auditor, mainA, mainB, mainC, mainD,
# coordinator) renders its EMPTY composer as U+276F followed by U+00A0, sliced at
# the cursor to "❯\xa0" — not the "❱" (U+2771) this table was calibrated to on
# 2026-07-28. `str.strip()` does remove the NBSP (U+00A0 is whitespace in Python),
# so the residue is "❯", which matched NOTHING here. Consequence, before this fix:
# `_composer_row_is_empty` returned False for an EMPTY composer on all six Claude
# panes, so `doorbell`'s guard (b) refused every ring to every Claude main — the
# fleet's brand-new delivery path was 0% operative and would have reported
# "composer holds pending input" about a composer that was empty.
#
# THE LESSON, AND WHY THE SUBMISSION CHECK BELOW DOES NOT DEPEND ON THIS TABLE.
# A glyph table is a calibration, and calibrations drift with every TUI release —
# this one drifted in fifteen days. So it is used only where a *classification* is
# unavoidable (is this row operator content, or a bare prompt?), never as the
# submission predicate. Submission is verified by a DELTA — the composer row must
# return to the exact value it held before this adapter typed — which needs no
# glyph knowledge at all and cannot rot. See `_await_composer_consumed`.
# The Codex placeholder ("› Write tests for @filename") renders to the RIGHT of
# the cursor and is excluded by the cursor slice, which is why it needs no entry.
_BARE_PROMPT_GLYPHS = ("›", "❱", "❯")


def doorbell_text(agent: str) -> str:
    """The fixed doorbell string. `agent` is the ONLY substitution — no other
    interpolation, no free-form content. This is deliberately not an f-string
    at the call site: routing every doorbell through one template is what makes
    "the string is not caller-controllable" a property of the code, not a
    convention callers are trusted to honour."""
    return DOORBELL_TEXT_TEMPLATE.format(agent=agent)


def _composer_row_is_empty(composer_text: str) -> bool:
    """Is the composer's CURRENT ROW free of pending input? For guard (b) above.

    Deliberately narrower than `_composer_text`'s own return value. That value
    is "everything up to the cursor" — the right anchor for fragment matching
    (see its docstring), but wrong here: it also contains the entire prior
    transcript, which is real, submitted, harmless content and must not count
    against emptiness. `doorbell` has no fragment to match against in the
    first place — the question is not "does the composer end with X" but "is
    there anything at all pending" — so this reads only the last line of that
    capture: the physical row the cursor sits on, from column 0 to the cursor.

    KNOWN SCOPE LIMIT, stated rather than hidden: a composer with pending input
    spanning MULTIPLE rows (an operator mid-typing a multi-line message, cursor
    resting on a trailing blank line) would read this row as empty while an
    earlier row is not. Not addressed here — the design brief scopes this to
    the "composer/input row", singular, and multi-row pending input on an
    otherwise-idle main is not the case this guard was written to catch. If it
    ever matters, extend the scan to every row from the last recognised
    bare-prompt line to the cursor, not just the last one.
    """
    stripped = _composer_row(composer_text).strip()
    for glyph in _BARE_PROMPT_GLYPHS:
        if stripped.startswith(glyph):
            stripped = stripped[len(glyph):].strip()
            break
    return stripped == ""


def _composer_row(composer_text: str) -> str:
    """The composer's CURRENT ROW. Split out of `_composer_row_is_empty` because C51's
    submission check needs the VALUE, not only its emptiness."""
    return composer_text.rsplit("\n", 1)[-1]


# ---------------------------------------------------------------------------
# C53, 2026-08-12. THE CURSOR IS NOT AT THE END OF PENDING INPUT. MEASURED.
#
# The C6 block above states, as the premise every predicate in this module rests on,
# that "the terminal cursor sits at exactly the end of the pending (typed-but-
# unsubmitted) input, in both TUIs". On the CLIs this fleet runs TODAY that is false
# in at least one live state, and the counterexample was sitting on three panes at
# once while this was being written:
#
#     mainC  cursor=(26,2)  row = '❯\xa0pull the next batch and keep going'
#     mainA  cursor=(29,2)  row = "❯\xa0Option A - I'll authorize the reboot, …"
#     mainB  cursor=(29,2)  row = '❯\xa0Understood - stopping here, re-dispatching…'
#
# The cursor parks at column 2 — immediately after the prompt glyph and its NBSP —
# with the pending text entirely to its RIGHT. Each of those strings appears EXACTLY
# ONCE in 3,000 rows of that pane's scrollback, and that once is the composer row
# itself: a submitted message would also be echoed into the transcript, so these had
# never been submitted. They are real, never-delivered instructions.
#
# WHY THIS IS THE FAIL-OPEN AND NOT A COSMETIC DETAIL. `_composer_text` slices the
# cursor row at the cursor (`lines[cy][:cx]`, which is correct and load-bearing for
# fragment matching — see its docstring). Anything to the RIGHT of the cursor is
# therefore INVISIBLE to it. So an emptiness test built on that slice reads '❯\xa0'
# and reports EMPTY for a composer holding a full sentence — and the guards that
# depend on emptiness (doorbell's guard (b), C51's pre-typing guard) would then type
# after that sentence and press Enter, submitting somebody else's words. The detector
# built to make this condition visible reported "clean" for all three panes.
#
# So EMPTINESS IS JUDGED ON THE WHOLE ROW, and only the fragment checks stay anchored
# at the cursor. Two different questions, two different reads, and conflating them is
# what made the alarm silent.
#
# THE PLACEHOLDER PROBLEM, AND THE CALIBRATION THAT SOLVES IT. Both TUIs put text to
# the right of the cursor that is NOT pending input — a rotating hint in an empty
# composer — so a whole-row read needs to tell a hint from a sentence. Measured
# 2026-08-12 with `capture-pane -e`, on a disposable `codexcal2` session created and
# killed by the measurement (the live `agent` session was only ever read):
#
#   Codex, EMPTY composer:  '\x1b[1m›\x1b[0m \x1b[2mImprove documentation in @filename\x1b[0m'
#   Codex, TYPED input:     '\x1b[1m›\x1b[0m hello world this is typed'      (cursor at col 27)
#   Codex, after Ctrl-U:    '\x1b[1m›\x1b[0m \x1b[2mSummarize recent commits\x1b[0m'
#   Claude, EMPTY composer: '\x1b[39m❯\xa0'
#   Claude, PENDING input:  '\x1b[39m❯\xa0\x1b[2mpull the next batch and keep going\x1b[0m'
#
# So on CODEX faint (SGR 2) means PLACEHOLDER — and note the hint ROTATES between
# renders, which is why a fixed-string exemption would have rotted immediately. On
# CLAUDE faint means PENDING INPUT, the exact opposite, and its empty composer carries
# no hint at all. One rule cannot serve both, and the SGR alone is not the separator:
# the BACKEND plus the SGR is. The backend is available as positive identification
# (`agent_backend`, which reads the executable of a process under the pane and REFUSES
# on ambiguity), so `faint_is_placeholder` is set only for a pane positively
# identified as Codex. For Claude, and for any pane whose backend cannot be
# identified, faint text counts as content and the read fails closed.
_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")
_FAINT_ON, _FAINT_OFF = "2", ("0", "22", "")


def _strip_faint_runs(row: str) -> str:
    """Delete every faint (SGR 2) run from an escape-carrying row, keep the rest.

    Written as a tiny SGR state machine rather than a regex over the whole row: the
    faint run is ENDED by a reset (`0`) or an explicit un-faint (`22`), and a regex
    that assumed one particular closing sequence would silently keep the placeholder
    the first time a TUI closed it with the other.
    """
    out, pos, faint = [], 0, False
    for m in _SGR_RE.finditer(row):
        if not faint:
            out.append(row[pos:m.start()])
        params = m.group(0)[2:-1].split(";")
        if _FAINT_ON in params:
            faint = True
        if any(p in _FAINT_OFF for p in params):
            faint = False
        pos = m.end()
    if not faint:
        out.append(row[pos:])
    return "".join(out)


def _read_composer_row(target: str, faint_is_placeholder: bool = False
                       ) -> tuple[str | None, str | None]:
    """(the WHOLE composer row, failure). None row => the pane could not be read.

    The full physical row the cursor sits on, NOT the cursor prefix — see the C53
    block above for the measurement that forced the distinction — with SGR removed and,
    on a positively-identified Codex pane, its faint placeholder run removed with it,
    so every caller downstream sees the true buffer and nothing else.
    """
    try:
        pos = subprocess.run(
            ["tmux", "display-message", "-p", "-t", target, "#{cursor_y}"],
            capture_output=True, text=True, timeout=15)
        pane = subprocess.run(["tmux", "capture-pane", "-p", "-e", "-t", target],
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not read the composer of {target}: {exc}"
    if pos.returncode != 0 or pane.returncode != 0:
        out = (pos.stdout or pos.stderr or "") + (pane.stdout or pane.stderr or "")
        return None, f"could not read the composer of {target}: {out.strip()[:200]}"
    try:
        cy = int((pos.stdout or "").strip())
    except ValueError:
        return None, f"tmux gave an unreadable cursor row {pos.stdout!r} for {target}"
    lines = (pane.stdout or "").split("\n")
    if cy >= len(lines):
        return None, f"cursor row {cy} is outside the captured pane ({len(lines)} rows)"
    row = lines[cy]
    if faint_is_placeholder:
        row = _strip_faint_runs(row)
    return _SGR_RE.sub("", row).rstrip(), None


def composer_faint_is_placeholder(config: dict, agent: str) -> bool:
    """May faint composer text be discarded as a placeholder for this agent?

    True ONLY for a pane positively identified as Codex. Claude renders PENDING INPUT
    faint, so answering True for it would discard the very hazard this reads for; an
    unidentifiable backend gets the same fail-closed answer for the same reason.
    """
    backend, _why = agent_backend(config, agent)
    return backend == "codex"


# ---------------------------------------------------------------------------
# C51, 2026-08-12. THE SUBMIT STEP IS NOW VERIFIED AGAINST THE BUFFER, NOT THE KEYS.
#
# THE DEFECT. Three mains sat idle on 2026-08-12 with an instruction visibly queued
# in their composers and never submitted (mainB "push it", mainC "Freeze lifted —
# commit and push are open again.", mainB "run the full BGE sweep"), while the MI210
# sat at 0% and the operator raised idle hardware for the eleventh time. A dispatched
# task that never submits is indistinguishable from a dispatched task the main
# declined, so the coordinator reported "dispatched" while the hardware sat at zero.
#
# REPRODUCED 2026-08-12 against real tmux panes (throwaway session, disposable
# composer TUI — scripts/coordination/tests/composer_tui_fixture.py). Three distinct
# defects, all confirmed, none hypothesised:
#
#   1. NOTHING ROLLS BACK A HALF-DELIVERED NUDGE. `cmd_nudge` types the payload as
#      its first act and then verifies. EVERY failure after that point — pre-Enter
#      gate, the Enter itself, post-Enter verification — returned non-zero while
#      LEAVING THE PAYLOAD SITTING IN THE COMPOSER, and `record()` only ever runs on
#      the success path, so the strand appeared in no ledger, no bus row and no log.
#      The exit code was the only trace, and it is consumed by wrappers that
#      `grep -q nudged` and by a daemon that logs a refusal and moves on. The
#      standing condition was invisible BY CONSTRUCTION.
#   2. `doorbell` HAD NO SUBMISSION VERIFICATION AT ALL. It sent the string, sent
#      Enter, and recorded success on `send-keys` exit status — which only says tmux
#      accepted the request (C30(b), one command over). Against a pane that swallows
#      Enter it printed "doorbell rung", wrote a ledger row, and left the doorbell
#      text pending. Worse, that strand then trips its own guard (b) forever: the
#      pane is permanently un-ringable by the very text the ring left behind.
#   3. `nudge`'s C12 anti-staleness anchor was SAMPLED AFTER THE ENTER. The comment
#      says "how many times the fragment was on the pane BEFORE Enter"; the call sat
#      below `send-keys Enter` and a settle sleep. So the count was taken after the
#      mutation it exists to detect, and C12 was vacuous: with an identical fragment
#      already in the transcript and an Enter eaten by a completion picker, the
#      adapter exited 0, printed "nudged", and wrote a ledger row for a submission
#      that never happened. That is the C6 fail-open through a fourth door.
#
# THE FIX, AND WHY IT IS A DELTA AND NOT A PATTERN. "Was it submitted?" is now
# answered by the composer BUFFER being consumed: the composer row must return to
# the exact value it held immediately before this adapter typed a single character.
# A submission empties the buffer; a swallowed Enter does not; a picker that rewrote
# the composer does not. It needs no glyph table, no prompt regex and no knowledge of
# the TUI's chrome, so unlike every pattern in this module it cannot rot with the
# next CLI release — which matters, because the glyph table twenty lines up DID rot
# in fifteen days and took the whole doorbell path down with it.
#
# It is a CONJUNCT, not a replacement. `nudge` still requires the positive transcript
# echo (C6) with the C12 occurrence anchor, now sampled where the comment always said
# it was. Buffer-consumed alone would accept an Enter that cleared the composer
# without submitting; echo alone was defeated by (3). Both must hold.
#
# AND THE BASELINE IS WHAT MAKES THE ROLLBACK SAFE. Ctrl-U is only ever sent after
# this adapter has PROVED, before typing, that the composer was empty — so everything
# in it afterwards is this adapter's own text and clearing it cannot destroy operator
# input. Never Ctrl-C: a second Ctrl-C exits a Codex session and destroys the window.
def _await_composer_consumed(target: str, baseline: str, timeout_s: float,
                             stable_samples: int = _VERIFY_STABLE_SAMPLES,
                             faint_is_placeholder: bool = False
                             ) -> tuple[bool, str | None, str | None]:
    """Has the composer BUFFER been consumed? (ok, last observed row, read failure).

    Consumed means the row returned to ``baseline`` AND reads as an empty composer.
    The second conjunct is redundant while the callers refuse a non-empty baseline,
    and it is kept anyway: it is the check that survives a mis-captured baseline, and
    a verification that trusts one reading of one value is how this module's whole
    defect history starts.

    ``stable_samples`` consecutive observations are required for the same reason the
    post-Enter echo check requires them — a single capture can land on a half-drawn
    repaint frame in which the composer is momentarily blank.

    A read failure is returned as a failure, NEVER as "consumed". An unreadable pane
    is not a submitted message.
    """
    deadline = time.monotonic() + max(0.0, timeout_s)
    run, observed = 0, None
    while True:
        row, failure = _read_composer_row(target, faint_is_placeholder)
        if failure:
            return False, observed, failure
        observed = row
        ok = _normalise(row) == _normalise(baseline) and _composer_row_is_empty(row)
        run = run + 1 if ok else 0
        if run >= max(1, stable_samples):
            return True, observed, None
        if run == 0 and time.monotonic() >= deadline:
            return False, observed, None
        time.sleep(_VERIFY_POLL_S)


def _clear_own_pending(target: str, baseline: str,
                       faint_is_placeholder: bool = False) -> tuple[bool, str | None]:
    """Ctrl-U, then PROVE the composer came back to ``baseline``. (cleared, detail).

    ONLY legitimate because the caller established, before typing, that the composer
    was empty — so the text being cleared is this adapter's own. NEVER send Ctrl-C to
    a Codex pane: the second one exits the session and destroys the window (it has
    destroyed a main before). Ctrl-U alone clears a composer.

    Returns cleared=False on ANY doubt, including an unreadable pane. A rollback that
    cannot prove it worked is reported as a strand, not as a cleanup.
    """
    rc, out = _tmux("send-keys", "-t", target, "C-u")
    if rc != 0:
        return False, f"send-keys C-u failed: {out}"
    ok, observed, failure = _await_composer_consumed(target, baseline, _VERIFY_TIMEOUT_S,
                                                     faint_is_placeholder=faint_is_placeholder)
    if failure:
        return False, f"composer unreadable after Ctrl-U: {failure}"
    if not ok:
        return False, f"composer still holds {(observed or '')[:80]!r} after Ctrl-U"
    return True, "composer cleared and verified empty"


def _fail_after_typing(kind: str, agent: str, target: str, baseline: str,
                       stage: str, why: str, faint_is_placeholder: bool = False) -> int:
    """One exit for every failure that happens once our text is in the composer.

    Does the three things that were missing and that turned a failed delivery into an
    invisible idle main: it ROLLS BACK (so no payload is stranded in front of a main
    that will read it as an instruction it declined), it RECORDS (so "was anything
    stranded?" is answerable from durable state rather than by reading panes by eye),
    and it FAILS LOUD on stderr with a non-zero exit. If the rollback itself cannot be
    confirmed, that is said in the ledger AND on stderr — a strand nobody knows about
    is the failure this whole block exists to end.
    """
    cleared, detail = _clear_own_pending(target, baseline, faint_is_placeholder)
    print(f"{kind} NOT DELIVERED to {agent} at {target} ({stage}): {why}", file=sys.stderr)
    if cleared:
        print(f"  rolled back: {detail} — nothing is left pending in that composer.",
              file=sys.stderr)
    else:
        print(f"  ROLLBACK FAILED: {detail}. TEXT IS STILL PENDING IN {target} and will "
              f"look to that main like an instruction it was given and declined. Clear it "
              f"with `tmux send-keys -t {target} C-u` (NEVER C-c on a Codex pane) or let "
              f"whoever is there submit it. `tmux_adapter.py pending` lists every pane in "
              f"this state.", file=sys.stderr)
    record(f"{kind}-undelivered", agent,
           f"{stage}: {why}"[:400], target=target, stage=stage,
           rollback="cleared" if cleared else "FAILED", rollback_detail=detail,
           stranded=not cleared)
    return EX_MISCONFIG


def _submission_state(composer_text: str, fragment: str,
                      min_occurrences: int | None = None) -> str:
    """Classify the composer, cursor-anchored. Four states, all distinct.

    ``text_present``  the composer ENDS with the message — pending, not submitted.
    ``paste_blob``    the composer ends in a paste attachment banner instead of
                      editable text: the known mangling failure (Codex truncates
                      such blobs at 1024 chars).
    ``text_echoed``   the message is on the pane but no longer at the cursor: the
                      transcript echo of a SUBMITTED message. This is the only
                      post-Enter success state.
    ``text_absent``   the message is nowhere up to the cursor. Before Enter that
                      means it did not land. AFTER Enter it is NOT proof of
                      submission — see the note below.

    WHY ``text_absent`` MUST NOT MEAN "SUBMITTED". Treating "no longer at the
    cursor" as success reopens the C6 fail-open through a second door: an Enter
    consumed by an in-composer completion overlay (Codex's `@` picker, either
    TUI's `/` menu) REPLACES the tail instead of submitting, and the composer
    then ends with the completion. Requiring the echo — measured 2026-07-28 on
    both TUIs — makes the success path positive evidence rather than the absence
    of failure, so an Enter that edited the composer is refused, not recorded.
    """
    normalised, needle = _normalise(composer_text), _normalise(fragment)
    if not needle:
        # Unmatchable: fail closed rather than match everything.
        return "text_absent"
    if normalised.endswith(needle):
        return "text_present"
    if _PASTE_BLOB_MARKER in composer_text[-_BLOB_LOOKBACK_CHARS:]:
        return "paste_blob"
    if needle in normalised:
        # C12 (closed 2026-08-11): `needle in normalised` matched the fragment
        # ANYWHERE on the pane, including scrollback ABOVE the composer. So an
        # identical fragment already in the transcript — the same nudge sent
        # earlier, or an agent echoing the text back — could satisfy the post-Enter
        # success check even though Enter never submitted: a completion overlay
        # rewrites the composer, our copy vanishes, and the STALE copy answers for
        # it. The 600s rate limit makes that unlikely and it needs a second fault
        # to matter, which is why it was filed rather than fixed — but "unlikely"
        # is not the standard this module holds elsewhere, and it is the C6
        # fail-open through a third door.
        #
        # `min_occurrences` is the anchor the filing asked for, expressed as a
        # COUNT rather than a cursor offset — the capture is re-normalised and the
        # pane can scroll between samples, so a byte offset does not survive, and a
        # count does. The caller passes the pre-Enter occurrence count. A genuine
        # submission MOVES our copy from the composer into the transcript, so the
        # count holds; an Enter eaten by a picker DELETES it, so the count drops
        # and what remains is provably stale.
        if min_occurrences is not None and normalised.count(needle) < min_occurrences:
            return "text_absent"
        return "text_echoed"
    return "text_absent"


def _fragment_occurrences(target: str, fragment: str) -> int | None:
    """How many times the fragment appears on the pane right now, or None if the
    pane cannot be read.

    C12. None propagates as "no anchor available" and the post-Enter check keeps its
    pre-C12 behaviour rather than refusing — an unreadable pane at THIS point is
    already handled by the capture failure path a moment later, and refusing twice
    for one cause would turn a transient tmux hiccup into a nudge failure.
    """
    composer, failure = _composer_text(target)
    if failure or composer is None:
        return None
    needle = _normalise(fragment)
    return _normalise(composer).count(needle) if needle else None


def _await_state(target: str, fragment: str, wanted: set[str], timeout_s: float,
                 stable_samples: int = 1,
                 min_occurrences: int | None = None) -> tuple[str | None, str | None]:
    """Poll the composer until it reaches one of ``wanted``; return the last state.

    Polling exists so that a slow redraw is a WAIT, not a refusal. It never turns
    a failure into a success: on timeout the genuinely-observed state is returned
    and the caller refuses on it.

    ``stable_samples`` is how many CONSECUTIVE observations of a wanted state are
    required to believe it. The confirmation samples are taken even past the
    deadline — a candidate that only holds for one frame is a repaint artifact,
    and accepting it is the same fail-open the module exists to prevent.
    """
    deadline = time.monotonic() + max(0.0, timeout_s)
    run = 0
    while True:
        composer, failure = _composer_text(target)
        if failure:
            return None, failure
        state = _submission_state(composer or "", fragment, min_occurrences)
        run = run + 1 if state in wanted else 0
        if run >= max(1, stable_samples):
            return state, None
        if run == 0 and time.monotonic() >= deadline:
            return state, None
        time.sleep(_VERIFY_POLL_S)


def _send_message_chunked(target: str, message: str) -> tuple[int, str]:
    """Type the message in sub-threshold chunks so no TUI sees a paste burst.

    See the calibration block: 400 chars with a 0.15 s gap renders as literal
    typed text on both TUIs up to at least 12,000 chars, while the same text in
    one call blobs above 800 (Claude) / 1000 (Codex) and loses everything past
    1024. The gap is required — chunks sent back-to-back re-coalesce and blob.

    ``--`` terminates tmux's own option parsing: without it a chunk that starts
    with ``-`` (a message beginning ``--``, or a 400-char boundary landing on a
    hyphen) is read as a flag and the send fails.
    """
    for start in range(0, len(message), NUDGE_CHUNK_CHARS):
        rc, out = _tmux("send-keys", "-l", "-t", target, "--",
                        message[start:start + NUDGE_CHUNK_CHARS])
        if rc != 0:
            if start:
                out = (f"{out} — WARNING: {start} chars were already typed into {target} and "
                       f"are still pending in that composer. No Enter was sent. Clear it "
                       f"before the next nudge.")
            return rc, out
        if start + NUDGE_CHUNK_CHARS < len(message):
            time.sleep(NUDGE_CHUNK_DELAY_S)
    return 0, ""


def load_config() -> dict:
    import yaml
    return yaml.safe_load((BUS_ROOT / "config.yaml").read_text(encoding="utf-8")) or {}


def roster_entry(config: dict, agent: str) -> dict | None:
    for e in config.get("roster") or []:
        if isinstance(e, dict) and str(e.get("id")) == agent:
            return e
    return None


def resolve_target(config: dict, agent: str) -> tuple[str | None, str]:
    """(tmux target, reason). None target => refuse, never guess."""
    entry = roster_entry(config, agent)
    if not entry:
        return None, f"{agent!r} has no roster row — adding one is coordinator-agent's decision"
    ep = str(entry.get("endpoint") or "")
    if not ep.startswith("tmux:"):
        return None, f"endpoint {ep!r} is not a tmux endpoint"
    parts = ep.split(":")
    session = parts[1] if len(parts) > 1 else ""
    if len(parts) >= 3 and parts[2]:
        want = parts[2]
        # MUST verify. tmux resolves an unmatched target to the session's CURRENT
        # window and exits 0 — measured 2026-07-27: `display-message -t sess:gone`
        # returned data for a different window. Trusting the string would have let
        # send-keys hit the wrong pane, which is the precise failure this module
        # claims to prevent.
        #
        # C32 (2026-07-29): AN INDEX IS VERIFIED AGAINST #{window_index}, NOT EXEMPTED.
        # This check used to read `if got.strip() != want and not want.isdigit()`,
        # comparing every endpoint against the window NAME and then waiving the
        # comparison for numeric ones because an index never equals a name. So for
        # index endpoints it trusted the string — the exact thing the paragraph above
        # says it must not — and reported the result as "(verified)", a FALSE
        # ATTESTATION. Measured: `display-message -p -t agent:99` returns rc=0 having
        # fallen back to window index 0, so `tmux:agent:99` resolved to the operator's
        # own window and a nudge would have typed into it.
        #
        # It also punched the one hole in C24's containment. `cmd_spawn` overwrites a
        # stale heartbeat on the strength of `live_mains()` having refused to count
        # the id; that is safe only because an identity `live_mains` cannot see is one
        # `resolve_target` cannot reach either (see cmd_spawn). An index endpoint broke
        # exactly that pairing — uncounted AND resolvable — which re-opened a live main
        # to a mid-generation nudge. Latent, not live: no roster row uses an index
        # endpoint today, but C14 lists `tmux:agent:3` as a supported resolved form.
        # A refusal is always recoverable by asking again; a false attestation is not.
        rc, got = _tmux("display-message", "-p", "-t", f"{session}:{want}",
                        "#{window_index}\t#{window_name}")
        if rc != 0:
            return None, f"target {session}:{want} does not resolve: {got}"
        got_index, tab, got_name = got.strip().partition("\t")
        if not tab:
            return None, (f"unreadable display-message reply {got.strip()!r} for {session}:{want} "
                          f"— refusing rather than attesting a target this cannot verify")
        got_index, got_name = got_index.strip(), got_name.strip()
        if want.isdigit():
            if got_index != want:
                return None, (f"target {session}:{want!r} resolved to window INDEX {got_index!r} "
                              f"(name {got_name!r}) — tmux falls back to the current window on a "
                              f"miss. Refusing rather than typing into the wrong pane.")
            return f"{session}:{want}", (f"endpoint names window index {want} "
                                         f"(verified, currently named {got_name!r})")
        if got_name != want:
            return None, (f"target {session}:{want!r} resolved to window {got_name!r} — tmux "
                          f"falls back to the current window on a miss. Refusing rather than "
                          f"typing into the wrong pane.")
        return f"{session}:{want}", f"endpoint names window {want!r} (verified)"
    # No window in the endpoint: accept ONLY an exact window-name match.
    rc, out = _tmux("list-windows", "-t", session, "-F", "#{window_index}\t#{window_name}")
    if rc != 0:
        return None, f"cannot list windows of session {session!r}: {out}"
    for line in out.splitlines():
        idx, _, name = line.partition("\t")
        if name.strip() == agent:
            return f"{session}:{idx}", f"matched window named {agent!r}"
    return None, (f"endpoint {ep!r} names a session but no window, and no window is named "
                  f"{agent!r}. Refusing to guess which pane to type into — name the window "
                  f"or use endpoint 'tmux:{session}:<window>'.")


def heartbeat(agent: str) -> tuple[dict | None, float | None]:
    p = BUS_ROOT / "heartbeats" / f"{agent}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")), max(0.0, time.time() - p.stat().st_mtime)
    except (OSError, json.JSONDecodeError):
        return None, None


def ledger_rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def parse_endpoint_window(endpoint: str) -> tuple[str | None, str | None, str | None]:
    """Split a roster endpoint's window component. Returns ``(kind, value, error)``.

    ``kind`` is ``"name"``, ``"index"``, or ``None`` when the endpoint carries no
    window component (``tmux:agent``, or a non-tmux endpoint like ``monitor:file``).
    A non-None ``error`` means the endpoint cannot be INTERPRETED, and every caller
    must refuse on it — see live_mains() for why that is not the same as "the row
    has no live window".

    C14 (2026-07-28). Three endpoint shapes used to fall through as "no window",
    which made the row invisible to the concurrency count and therefore INVENTED
    capacity (an undercount lowers ``len(ids)`` and relaxes the cap):
      * ``tmux:agent:3``     — a window INDEX. Now resolved against #{window_index}.
      * ``tmux:agent:win.0`` — a PANE suffix. The pane is stripped; the window part
                               is then a name or an index like any other.
      * ``tmux:a:b:c``       — not a shape this understands at all. Refuses.
    """
    if not endpoint.startswith("tmux:"):
        return None, None, None
    parts = endpoint.split(":")
    if len(parts) > 3:
        return None, None, (f"endpoint {endpoint!r} has more ':'-separated parts than "
                            f"tmux:<session>[:<window>] allows; refusing to guess which is the "
                            f"window")
    if len(parts) < 3 or not parts[2].strip():
        return None, None, None
    component = parts[2].strip()
    if "." in component:                       # window.pane — the pane is not our unit
        component = component.split(".", 1)[0].strip()
        if not component:
            return None, None, (f"endpoint {endpoint!r} names a pane with no window; refusing to "
                                f"guess which window it means")
    return ("index" if component.isdigit() else "name"), component, None


def live_mains(config: dict) -> tuple[set[str] | None, str]:
    """Roster ids whose window is live in ``tmux.live_session``. None => unknown.

    C9 (2026-07-28). The cap this feeds used to be enforced by counting `spawn`
    rows in the ledger for the current date, which is a rate limit on an ACTION,
    not a bound on live mains: killing or closing a main never returned its slot,
    so three spawn rows blocked further spawns while only two mains were alive.
    What actually costs something is simultaneity — compute, context, coordinator
    attention — so the count is taken from the live window list, and closing an
    idle session gives the slot straight back (which the session-lifecycle rule in
    OPERATING_CONSTRAINTS.md tells sessions to do).

    NONE MEANS UNKNOWN AND CALLERS MUST REFUSE. tmux unreachable, the live session
    absent, or a roster with no ids all yield None rather than an empty set. An
    empty set is a positive statement ("no mains are live, all slots free") and
    inferring it from a failed query is precisely the fail-open shape of C3, C6
    and C8 in this same module.

    C14 (2026-07-28): UNINTERPRETABLE IS NOT ABSENT. A row whose endpoint cannot be
    parsed refuses the whole count, because silently skipping it is the
    capacity-inventing direction — fewer counted mains means a slot handed out that
    is already occupied. Note the distinction that keeps spawn usable: a row that is
    interpretable but matches no live window is simply NOT LIVE (the normal state of
    a retired or closed main) and costs nothing. Only endpoints this cannot READ
    refuse.

    THE POLARITY, EXPLICITLY — it was documented BACKWARDS until 2026-07-28, here
    and in commit messages `8033f039`/`8cbe50c0`, which said "an undercount in the
    direction that refuses spawns, never one that invents capacity". `cmd_spawn`
    refuses when ``len(ids) >= cap``, so missing a live main makes ``len(ids)``
    SMALLER: an undercount RELAXES the cap and hands out an occupied slot, and it
    weakens the ``args.agent in ids`` duplicate check too. Undercount = invent
    capacity. (This paragraph used to live on `roster_window_names`, deleted as
    dead code 2026-07-29 — the invariant outlives the function that carried it.)

    THE DRIFT TRIGGERS, so the next reader recognises one on sight:
      * **an operator renames a window without updating `config.yaml`** — not
        hypothetical: the `codex` → `codex-inference` rename of 2026-07-28 stayed
        counted ONLY because the endpoint moved with it;
      * **window-INDEX endpoints** (`tmux:agent:3`) — resolved since C14;
      * **pane-suffixed components** (`tmux:agent:win.0`) — resolved since C14;
      * **a live window NO roster row claims** — still open, tracked as C17.

    WHERE THERE IS A CHOICE, OVERCOUNT. A roster id is counted live if a window
    carries its id OR its endpoint's window resolves — both are checked, and the
    endpoint match is applied even when it names a different session. Overcounting
    refuses a spawn that might have been allowed; undercounting grants one that
    should not be. Only the first is recoverable by asking again.

    DEAD PANES STILL COUNT (fable-auditor, 2026-07-28). `pane_dead` is deliberately
    not consulted. A dead pane still holds a window, and if the `pane_dead` read
    ever misreported, excluding those windows would shrink the count — flipping the
    error back toward inventing capacity. The conservative reading of a window whose
    state is uncertain is that it occupies a slot.
    """
    roster = [e for e in (config.get("roster") or []) if isinstance(e, dict) and
              str(e.get("id") or "").strip()]
    if not roster:
        return None, "config.yaml roster has no ids — cannot tell a main's window from any other"
    live = str((config.get("tmux") or {}).get("live_session") or "agent")
    rc, out = _tmux("list-windows", "-t", live, "-F", "#{window_index}\t#{window_name}")
    if rc != 0:
        return None, (f"cannot list windows of the live session {live!r}: {out}. Refusing rather "
                      f"than assuming no mains are running.")
    windows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        index, tab, name = line.partition("\t")
        if not tab:
            return None, (f"unreadable list-windows row {line!r} for session {live!r} — refusing "
                          f"rather than counting a window list this cannot parse")
        windows.append((index.strip(), name.strip()))

    ids: set[str] = set()
    owners: dict[str, set[str]] = {}          # window name -> roster ids claiming it
    for entry in roster:
        rid = str(entry.get("id")).strip()
        kind, value, error = parse_endpoint_window(str(entry.get("endpoint") or ""))
        if error:
            return None, (f"roster row {rid!r}: {error}. Refusing rather than treating the row as "
                          f"absent — an uncounted live main frees a slot that is occupied.")
        for index, name in windows:
            if name == rid or (kind == "name" and name == value) or \
                    (kind == "index" and index == value):
                ids.add(rid)
                owners.setdefault(name, set()).add(rid)
    ambiguous = {name: rids for name, rids in owners.items() if len(rids) > 1}
    if ambiguous:
        detail = "; ".join(f"{name!r} claimed by {sorted(rids)}" for name, rids in ambiguous.items())
        return None, (f"window ownership is ambiguous in session {live!r} ({detail}) — refusing, "
                      f"because guessing which main is live is guessing how many slots are free")
    return ids, f"{len(ids)} roster main(s) live in session {live!r}"


def resolve_spawn_cap(caps: dict) -> tuple[int | None, str]:
    """(cap, reason). None => refuse; the cap is unresolvable, not zero.

    ``max_spawns_per_day`` is NOT read as a fallback, deliberately. It is not a
    renamed key, it is a different measurement: the operator's `6` authorised six
    spawn ACTIONS in a day, and silently re-reading it as six SIMULTANEOUS mains
    would grant concurrency nobody approved — a fail-open, in the one module whose
    entire defect history is fail-opens. So the old key alone refuses, with the
    one-line config edit it needs spelled out.
    """
    if CAP_KEY in caps:
        try:
            return int(caps[CAP_KEY]), f"caps.{CAP_KEY}"
        except (TypeError, ValueError):
            return None, f"caps.{CAP_KEY} is {caps[CAP_KEY]!r}, which is not a number"
    if LEGACY_CAP_KEY in caps:
        return None, (f"caps.{CAP_KEY} is not set and caps.{LEGACY_CAP_KEY} is NOT read as a "
                      f"fallback: it counted spawn actions per day, not simultaneous mains, so "
                      f"its value authorises a different thing. Set caps.{CAP_KEY} explicitly "
                      f"(operator decision) and delete the old key.")
    return None, f"caps.{CAP_KEY} is not set"


# ---------------------------------------------------------------- C36 runtime liveness
#
# THE ROOT DEFECT C35 ONLY MITIGATED. The heartbeat is written BY the agent, so an
# agent that has stopped cannot say so — and `probe` refuses every nudge on
# `state == "working"`. That is the deadlock. C35's pane-quiescence override treats
# the symptom with a heuristic ("a working TUI redraws a spinner"); this reads a
# signal the RUNTIME writes, which is true even when the agent is wedged, because it
# is STATE rather than a timestamp.
#
# Operator-approved as Option B of docs/design/agent-session-control-surface.md, which
# ranks 14 candidate signals with measurements. Option A (driving Codex over
# app-server JSON-RPC) is NOT approved and is not implemented here; read-only status
# only. Measured 2026-07-29: Option A is in any case 0% available today — no
# app-server runs and none of the four live Codex TUIs was launched with `--remote`,
# so adopting it would require restarting every Codex main.
#
# POLARITY, which is the whole game in this module: this NEVER manufactures an `idle`.
# Every failure path returns None = UNAVAILABLE, and None falls back to the previous
# behaviour (heartbeat + C35). An unreadable runtime is not an idle runtime.
_ROLLOUT_TERMINAL = {"task_complete", "turn_aborted"}
_BACKENDS = ("codex", "claude")


def _proc_children(pid: int) -> list[int]:
    try:
        raw = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for tok in raw.split():
        try:
            out.append(int(tok))
        except ValueError:
            continue
    return out


def _proc_descendants(pid: int, depth: int = 3) -> list[int]:
    seen, frontier = [pid], [pid]
    for _ in range(depth):
        nxt: list[int] = []
        for p in frontier:
            nxt += _proc_children(p)
        if not nxt:
            break
        seen += nxt
        frontier = nxt
    return seen


def _proc_names(pid: int) -> tuple[str, str]:
    """(exe basename, argv[0] basename) — both, because neither alone is reliable."""
    try:
        exe = os.path.basename(os.path.realpath(f"/proc/{pid}/exe"))
    except OSError:
        exe = ""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        argv0 = os.path.basename(raw[0].decode("utf-8", "replace")) if raw else ""
    except (OSError, IndexError):
        argv0 = ""
    return exe, argv0


def _pane_pid_for(config: dict, agent: str) -> tuple[int | None, str]:
    """The pane pid of this roster id's window. (pid, why); None => could not resolve.

    THE WINDOW COMES FROM THE ENDPOINT, NOT FROM THE ROSTER ID — and this function
    exists because the first draft of C36 assumed `window_name == agent` and silently
    lost `coordinator-agent`, whose endpoint is `tmux:agent:coordinator`. That is C25
    exactly, repeated inside the fix for a different defect one hour after C25 landed.
    The lesson generalises: any new code that locates a main's window must go through
    the endpoint, so the rule lives here once instead of being re-derived per caller.
    Fallback when the endpoint carries no window component mirrors `resolve_target`:
    a window named after the roster id.
    """
    entry = roster_entry(config, agent)
    if not entry:
        return None, f"{agent!r} has no roster row"
    kind, value, error = parse_endpoint_window(str(entry.get("endpoint") or ""))
    if error:
        return None, f"{agent!r}: {error}"
    live = str((config.get("tmux") or {}).get("live_session") or "agent")
    rc, out = _tmux("list-windows", "-t", live, "-F", "#{window_index}\t#{window_name}\t#{pane_pid}")
    if rc != 0:
        return None, f"cannot list windows of {live!r}: {out}"
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        index, name, pid = (p.strip() for p in parts)
        hit = (name == agent) if kind is None else (
            name == value if kind == "name" else index == value)
        if hit:
            try:
                return int(pid), f"window {name!r} (pane {pid})"
            except ValueError:
                return None, f"unreadable pane pid {pid!r} for window {name!r}"
    want = agent if kind is None else value
    return None, f"no window {want!r} in session {live!r} for roster id {agent!r}"


def agent_backend(config: dict, agent: str) -> tuple[str | None, str]:
    """Which CLI is this roster id actually running? (backend, why). None => unknown.

    IDENTIFIED, NOT INFERRED, and the distinction decides whether this is safe. The
    backend is read from the EXECUTABLE / argv[0] basename of a descendant of the
    window's pane pid — `codex` or `claude` — never from a substring of the shell's
    `-c` string. Measured 2026-07-29: mains are launched as `fish -c codex -m …` and
    `fish -c cd /workspace && claude`, so a substring test would misread a main
    launched as `claude --resume codex-notes`. Verified across all 9 live windows:
    4 codex, 3 claude, and htop/btop correctly UNKNOWN.
    RATIONALE FOR DOING THIS AT ALL: the 2026-07-29 rename made roster ids deliberately
    model-agnostic so a main can move between backends, and C30(a) — the roster row
    carrying its own launch command — is still open. A roster field would be better
    (it survives a re-spawn without a process walk) and this defers to one when it
    lands. Until then this is positive identification, not a guess.
    AMBIGUITY REFUSES. Both backends visible under one window, or neither, returns
    None, and None means the caller falls back — never that the agent is idle.
    """
    entry = roster_entry(config, agent)
    declared = str((entry or {}).get("backend") or "").strip().lower()
    if declared in _BACKENDS:
        return declared, f"roster row declares backend {declared!r} (C30a)"
    if declared:
        return None, (f"roster row declares backend {declared!r}, which is not one of "
                      f"{list(_BACKENDS)} — refusing to guess")

    pane_pid, why_pid = _pane_pid_for(config, agent)
    if pane_pid is None:
        return None, why_pid

    found: dict[str, int] = {}
    for p in _proc_descendants(pane_pid):
        exe, argv0 = _proc_names(p)
        for backend in _BACKENDS:
            if backend in (exe, argv0) or exe.startswith(backend) or argv0.startswith(backend):
                found.setdefault(backend, p)
    if len(found) == 1:
        backend, p = next(iter(found.items()))
        return backend, f"{backend!r} identified from pid {p} under pane {pane_pid}"
    if not found:
        return None, (f"no {' or '.join(_BACKENDS)} process under pane {pane_pid} for "
                      f"{agent!r} — not a backed main, or it has exited")
    return None, (f"AMBIGUOUS: both {sorted(found)} run under pane {pane_pid} for {agent!r}; "
                  f"refusing rather than picking one")


def codex_runtime_state(pid: int) -> tuple[str | None, str]:
    """('idle'|'active'|None, why) from the Codex rollout terminal record.

    The runtime appends every turn's records to
    `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl`; a turn that has ENDED
    leaves `event_msg/task_complete` or `event_msg/turn_aborted` as the file's last
    record. Verified over the whole corpus: 400 files sampled from 4,233 gave 400/400
    terminal. `task_complete` is a stable resting tail — the record that follows it is
    only ever `task_started` or `thread_settings_applied`, never the frequent mid-turn
    `token_count` — so a settled file does not later look busy again.
    THE SUBAGENT FD IS THE TRAP, AND IT IS LIVE. A parent codex process keeps the fds
    of FINISHED subagent rollouts open. Measured 2026-07-29 16:38Z on pid 257808:
    fd 39 -> a subagent rollout reading `task_complete`, fd 45 -> its own user rollout
    reading `custom_tool_call`. Reading the wrong fd reports IDLE for an agent that is
    mid-tool-call, which is precisely the nudge this module exists to prevent. So the
    user rollout is selected by `thread_source`, and anything else is refused.
    `thread_source` ABSENT FAILS CLOSED, deliberately. 8 corpus files (April-May, older
    cli_version) carry no such field. Treating absent as "user" would re-open the trap
    above for any file whose provenance we cannot read; treating it as "not user" costs
    only a fallback to the heartbeat. Today's fleet all carry the field, so this costs
    nothing now and cannot misread later.
    """
    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        fds = list(fd_dir.iterdir())
    except OSError as exc:
        return None, f"cannot read /proc/{pid}/fd: {exc}"

    rollouts: list[Path] = []
    for fd in fds:
        try:
            target = Path(os.path.realpath(fd))
        except OSError:
            continue
        if target.suffix == ".jsonl" and target.name.startswith("rollout-") \
                and "sessions" in target.parts:
            rollouts.append(target)
    if not rollouts:
        return None, f"pid {pid} holds no rollout file open"
    return codex_state_from_rollouts(rollouts)


def codex_state_from_rollouts(rollouts: list[Path]) -> tuple[str | None, str]:
    """The classification half, split out from the /proc lookup so it is testable.

    Separating these is not cosmetic: every interesting failure mode of this signal —
    subagent selection, absent `thread_source`, a torn tail — lives here, and none of
    it can be exercised through a real `/proc/<pid>/fd`.
    """
    user: list[Path] = []
    for path in rollouts:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                head = fh.readline()
            meta = json.loads(head).get("payload") or {}
        except (OSError, json.JSONDecodeError, AttributeError):
            continue                      # unreadable provenance is never assumed to be ours
        source = meta.get("thread_source")
        if isinstance(source, str) and source != "subagent":
            user.append(path)
    if not user:
        return None, (f"{len(rollouts)} rollout(s) open but none declares a non-subagent "
                      f"thread_source — refusing rather than reading a subagent's state as the main's")
    if len(user) > 1:
        return None, (f"{len(user)} user rollouts ({sorted(q.name for q in user)}); "
                      f"refusing rather than picking one")

    path = user[0]
    for attempt in (1, 2):
        last = _last_line(path)
        if last is None:
            return None, f"cannot read {path.name}"
        try:
            payload = json.loads(last).get("payload") or {}
        except json.JSONDecodeError:
            if attempt == 1:
                time.sleep(0.05)          # a torn tail under live append: retry once, then refuse
                continue
            return None, (f"last record of {path.name} is not parseable JSON after a retry — "
                          f"treating as unknown rather than guessing a state")
        kind = payload.get("type")
        if kind in _ROLLOUT_TERMINAL:
            return "idle", f"{path.name} ends in {kind!r}"
        return "active", f"{path.name} ends in {kind!r}, not a turn-terminal record"
    return None, "unreachable"


def _last_line(path: Path) -> str | None:
    """Last non-empty line, read from the END so cost is independent of file size.

    Rollouts reach 40 MB; reading them whole every probe would put a multi-megabyte
    read on the nudge path. Measured: seeking is sub-millisecond against a 6.7 MB file.
    """
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            end = fh.tell()
            block, buf = 4096, b""
            while end > 0:
                step = min(block, end)
                end -= step
                fh.seek(end)
                buf = fh.read(step) + buf
                lines = [ln for ln in buf.split(b"\n") if ln.strip()]
                if len(lines) >= 1 and (end == 0 or len(buf.split(b"\n")) > 2):
                    return lines[-1].decode("utf-8", "replace")
                block *= 4
            return None
    except OSError:
        return None


def runtime_liveness(config: dict, agent: str) -> tuple[str | None, str]:
    """('idle'|'active'|None, why) — liveness as reported by the RUNTIME, not the agent.

    None means UNAVAILABLE and the caller must fall back to the previous guard chain.
    It never means idle: an unreadable runtime is not an idle runtime, and this module's
    entire defect history (C3, C6, C8, C24, C27, C34) is fail-opens.
    """
    backend, why = agent_backend(config, agent)
    if backend is None:
        return None, f"backend unknown: {why}"
    if backend == "codex":
        pane_pid, why_pid = _pane_pid_for(config, agent)
        if pane_pid is None:
            return None, f"codex: {why_pid}"
        # Only the musl `codex` binary holds rollout fds — not the `node` wrapper and
        # not `codex-code-mode-host`. Measured 2026-07-29.
        last = "no codex pid under the pane"
        for p in _proc_descendants(pane_pid):
            exe, argv0 = _proc_names(p)
            if "codex" in (exe, argv0):
                state, detail = codex_runtime_state(p)
                if state is not None:
                    return state, f"codex rollout (pid {p}): {detail}"
                last = detail
        return None, f"codex: {last}"
    # Claude: signal #3 (`claude agents --json` / ~/.claude/sessions/<pid>.json) is not
    # wired yet — it is being verified separately, and an unverified signal on the
    # delivery plane is worth less than an honest UNAVAILABLE.
    return None, (f"backend {backend!r}: no runtime signal implemented yet — falling back to the "
                  f"heartbeat guard chain")


# ---------------------------------------------------------------- C52 working-claim corroboration
#
# THE DEADLOCK, observed live 2026-08-12. `mainB` finished a GPU sweep and settled at
# an empty composer. Its heartbeat still read `state: working, task_id:
# gpu-continuous-occupancy-A3-sweep-pid-4133649` — and pid 4133649 was already dead.
# Every nudge refused with `heartbeat says working (task ...)`; six retries over two
# minutes, all refused. An idle main, plainly idle in its own pane, was unreachable by
# any channel, and the MI210 read 0% for thirteen minutes because work could not be
# delivered to the main holding the grant.
#
# WHY C35's QUIESCENCE OVERRIDE DID NOT RESCUE IT. There is a BAND, and the incident
# lived in it: the refusals named the heartbeat state, so the window had been quiet
# longer than `--quiet-s` (20s, or the quiet-check would have refused first and said
# so) and shorter than the 120s override threshold (or the override would have fired).
# Between those two numbers a settled main passes every guard except the one it cannot
# clear. That much is inference from the refusal messages, and it is enough on its own.
#
# The band is also wider in practice than the C35 calibration assumed, and this part IS
# measured: C35 reasons that "a working TUI redraws its spinner about once a second, so
# a window quiet for two minutes is settled", and a main with FANNED-OUT SUBAGENTS
# renders a live elapsed-time row per subagent ("◈ general-purpose … 16m 23s") that
# ticks every second whether or not the main's own thread is doing anything — observed
# directly on the live session 2026-08-12, on panes sitting at empty composers. For
# such a main `quiet_for` can stay near zero indefinitely and the override can never
# fire at all. The daemon had already reached the same conclusion from the other side:
# `session_bus_coordinator._PANE_BUSY_MARKER` says in as many words that the
# quiet-check "is defeated by cosmetic TUI redraw ... so it cannot answer 'is it
# working'". The adapter was still deciding on it alone.
#
# THE ASYMMETRY THAT MADE IT A HARD DEADLOCK. `--heartbeat-max-age` is a sanctioned
# override for a refusal on AGE. There was none for a refusal on STATE. And no one
# else can clear it: single-writer discipline means only mainB may write mainB's
# heartbeat, and it cannot, because the thing that would tell it to is the nudge the
# guard refuses.
#
# THE FIX: A CLAIM IS NOT EVIDENCE. `state: working` is an assertion by a process that
# may have stopped, so it now has to be CORROBORATED by something that could have
# contradicted it. Same lesson as the watchdog one layer up that identified its target
# by a name pattern which could not match and so declared a healthy daemon dead
# forever: identity and liveness come from a signal you can verify, never from an
# assertion. Three verdicts, and the third is not a polite way of saying one of the
# other two:
#
#   corroborated   something INDEPENDENT says the agent is busy — the runtime rollout
#                  record, a generation/compaction marker on the pane, or the task's
#                  own published pid still being alive. REFUSE, exactly as before.
#   contradicted   the claim's own published pid is gone, or the runtime says idle, or
#                  the pane is quiescent past the C35 threshold, AND nothing
#                  corroborates. The heartbeat is stale self-report. DELIVER.
#   undetermined   no signal either way. Still refuses — but it says THAT, instead of
#                  reporting the stale claim as though it had been believed on merit.
#                  A guard that cannot tell the difference between "it is working" and
#                  "I could not tell" is how this took thirteen minutes to diagnose.
#
# CORROBORATION OUTRANKS CONTRADICTION, deliberately and in that order. A single
# positive signal that the agent is busy refuses the nudge even when two others say
# idle: typing into a live generation corrupts it, and the cost of a false refusal is
# a retry. This is also what keeps COMPACTING safe — a compacting session renders like
# an idle one to a naive reader, so it is recognised positively (runtime ACTIVE for
# Codex, the pane marker for Claude) and never inferred from the absence of business.
_PANE_BUSY_MARKERS = ("esc to interrupt", "compacting")
# The heartbeat schema has no `pid` field today, but the fleet has been writing the pid
# INTO the task_id for a while (`…-sweep-pid-4133649`, the incident above), so both are
# read: an explicit `pid`/`task_pid` field if one appears, else the trailing `-pid-N`
# convention. Reading the convention is not guessing — it is the agent's OWN published
# identifier for the work it claims to be doing, which is precisely the thing that can
# be checked against reality.
_HEARTBEAT_PID_RE = re.compile(r"pid[-_]?(\d{2,7})\b", re.IGNORECASE)


def heartbeat_task_pid(hb: dict | None) -> tuple[int | None, str]:
    """The pid the heartbeat claims is doing the work. (pid, why); None => none declared."""
    if not isinstance(hb, dict):
        return None, "no heartbeat"
    for key in ("pid", "task_pid"):
        raw = hb.get(key)
        if raw is not None:
            try:
                return int(raw), f"heartbeat field {key}={raw!r}"
            except (TypeError, ValueError):
                return None, f"heartbeat field {key}={raw!r} is not a pid"
    m = _HEARTBEAT_PID_RE.search(str(hb.get("task_id") or ""))
    if m:
        return int(m.group(1)), f"pid parsed from task_id {hb.get('task_id')!r}"
    return None, "heartbeat declares no task pid"


def pid_alive(pid: int) -> bool | None:
    """Is this pid running? None => cannot tell, which is NOT 'dead'.

    `/proc/<pid>` rather than `kill -0`: it sends no signal, needs no ownership of the
    target, and cannot be confused by a permission error. PID REUSE resolves toward
    ALIVE, and that is the safe direction here — a recycled number produces a refusal,
    never a nudge into a live generation.
    """
    try:
        return Path(f"/proc/{pid}").exists()
    except OSError:
        return None


def pane_busy_marker(target: str) -> tuple[bool | None, str]:
    """Is the pane generating (or compacting)? (True|False|None, why). None => unreadable.

    The marker set is the daemon's, calibrated against the live fleet and re-verified
    2026-08-12: every main mid-turn rendered `esc to interrupt` and the one settled at
    its prompt did not, across both TUIs. `compacting` is carried alongside it so a
    context compaction — which otherwise renders like an idle session — is recognised
    positively rather than inferred away.
    """
    rc, out = _tmux("capture-pane", "-p", "-t", target)
    if rc != 0:
        return None, f"capture-pane on {target} failed: {out[:200]}"
    low = (out or "").lower()
    for marker in _PANE_BUSY_MARKERS:
        if marker in low:
            return True, f"pane {target} shows {marker!r}"
    return False, f"pane {target} shows no generation or compaction marker"


def corroborate_working_claim(*, runtime_state: str | None, runtime_reason: str,
                              pane_busy: bool | None, pane_reason: str,
                              task_pid: int | None, task_pid_alive: bool | None,
                              pid_reason: str, pane_dead: bool | None,
                              quiet_for: float | None,
                              override_quiet_s: float,
                              quiet_s: float = 0.0) -> tuple[str, str]:
    """('corroborated'|'contradicted'|'undetermined', why) for a `state: working` claim."""
    # ---- corroboration wins, and is checked first ----
    if runtime_state == "active":
        return "corroborated", f"the runtime says ACTIVE — {runtime_reason}"
    if pane_busy is True:
        return "corroborated", pane_reason
    if task_pid is not None and task_pid_alive is True:
        return "corroborated", f"the task's own pid {task_pid} is still running ({pid_reason})"
    # ---- then evidence that the claim is stale ----
    if task_pid is not None and task_pid_alive is False:
        return "contradicted", (f"the heartbeat's own task pid {task_pid} is GONE ({pid_reason}) "
                                f"and nothing corroborates the claim — {pane_reason}")
    if runtime_state == "idle":
        return "contradicted", f"the runtime says IDLE — {runtime_reason}"
    if hb_stale_override_ok(pane_dead, quiet_for, override_quiet_s):
        # C35's own predicate, unchanged and still worded as it was: it is quoted in
        # probe output and in ledger rows, and a reader comparing two days of evidence
        # should not have to work out that the sentence was reworded.
        return "contradicted", (
            f"window quiet {quiet_for:.0f}s (>= {override_quiet_s:.0f}s); both TUIs redraw a "
            f"spinner every second while working, so this pane is settled at its prompt and the "
            f"`working` heartbeat is stale self-report")
    # THE OPERATOR'S OWN INSTRUCTION, 2026-08-12: "why not just look at its pane. It's
    # straightforward to see that it returned a result and is waiting for further
    # instruction." This is that, made conservative enough to be safe: TWO INDEPENDENT
    # readings must both say settled — the pane renders no generation or compaction
    # marker, AND the window has been quiet at least as long as the `--quiet-s` guard
    # already requires before any nudge at all. Either alone is too weak. The marker
    # could in principle be missing for a frame mid-turn; the quiet-check alone is
    # defeated by cosmetic redraw (subagent elapsed-time rows). Together they are the
    # same evidence a human reads off the pane, and they cover the case a pid cannot:
    # most heartbeats declare no pid, and the fleet cannot be made to start declaring
    # one by this module.
    #
    # This deliberately does NOT lower the `--quiet-s` bar — it reuses it. A pane the
    # quiet-check would refuse can never reach this branch, so nothing here makes a
    # mid-generation pane nudgeable that was not nudgeable before.
    if pane_busy is False and pane_dead is False and quiet_for is not None \
            and quiet_s > 0 and quiet_for >= quiet_s:
        return "contradicted", (
            f"the pane renders no generation or compaction marker AND the window has been quiet "
            f"{quiet_for:.0f}s (>= --quiet-s {quiet_s:.0f}s) — two independent readings that it "
            f"is settled at its prompt, which is what the heartbeat is contradicting")
    # ---- and otherwise, say exactly that ----
    return "undetermined", (
        f"nothing corroborates or contradicts it: runtime {runtime_state or 'UNAVAILABLE'} "
        f"({runtime_reason}); {pane_reason}; {pid_reason}; "
        f"{_stale_override_refusal(pane_dead, quiet_for, override_quiet_s)}. Refusing because "
        f"the state is UNDETERMINED, not because the heartbeat was believed")


def record(kind: str, agent: str, detail: str, **fields: object) -> None:
    """Append one adapter action to the ledger.

    2026-07-29: `**fields` exists so a row can carry STRUCTURED evidence rather than
    only a prose `detail`. It was added for the C24 heartbeat reset, where the thing
    worth keeping is the value that was destroyed — see cmd_spawn. `None` values are
    dropped so an absent field never renders as a claim that it was null.
    """
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row: dict[str, object] = {"ts": _now(), "kind": kind, "agent": agent, "detail": detail}
    row.update({k: v for k, v in fields.items() if v is not None})
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def hb_stale_override_ok(pane_dead: bool | None, quiet_for: float | None,
                         override_quiet_s: float) -> bool:
    """May a STALE heartbeat be overruled? Only on positive pane evidence.

    R1. Deliberately the same predicate C35 uses for a `working` heartbeat, and
    deliberately fail-closed on every unknown: a disabled override, an unreadable or
    dead pane, or unreadable window activity all mean NO. The one case that says yes
    is a live pane that has been quiet longer than the spinner interval — both TUIs
    redraw about once a second while generating, so quiet at that scale means settled
    at the prompt, not thinking.

    Note what this does NOT do: it never makes a mid-generation pane nudgeable. That
    is the compliant path, and a fix that made everything reachable would be worse
    than the deadlock it replaces.
    """
    if override_quiet_s <= 0:
        return False
    if pane_dead is not False:
        return False
    if quiet_for is None:
        return False
    return quiet_for >= override_quiet_s


def _stale_override_refusal(pane_dead: bool | None, quiet_for: float | None,
                            override_quiet_s: float) -> str:
    """Why the stale-heartbeat override did NOT fire. Said out loud, because the
    whole R1 defect was a refusal whose reason nobody could see."""
    if override_quiet_s <= 0:
        return f"stale-override disabled (--heartbeat-override-quiet-s {override_quiet_s:.0f})"
    if pane_dead is not False:
        return "pane state unreadable or dead — fail closed, no override"
    if quiet_for is None:
        return "window_activity unreadable — fail closed, no override"
    return (f"window was active {quiet_for:.0f}s ago (< {override_quiet_s:.0f}s) — the pane "
            f"looks mid-generation, so the stale heartbeat is NOT overruled")


def probe(config: dict, agent: str, quiet_s: float, hb_max_age: float,
          hb_override_quiet_s: float = DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S,
          runtime_fn=None, pane_busy_fn=None) -> dict:
    """Every guard signal, with an explicit blocker list. Pure — acts on nothing.

    `hb_override_quiet_s` is the C35 quiescence override (see the constant). It
    is keyword-defaulted so the four-positional-argument call sites and tests
    that predate it keep working unchanged.

    C36: `runtime_fn` injects the runtime-liveness source (default
    `runtime_liveness`), so tests can drive every branch without a live TUI —
    the same seam-injection the coordinator uses for `nudge_fn`.
    """
    flags, caps = config.get("flags") or {}, config.get("caps") or {}
    authorised = str(flags.get("codex_sendkeys")).strip().lower() in {"1", "true", "yes", "on"}
    spawn_cap, cap_reason = resolve_spawn_cap(caps)
    live_ids, live_reason = live_mains(config)

    target, why = resolve_target(config, agent)
    hb, hb_age = heartbeat(agent)
    # C36: the RUNTIME's answer, obtained before any heartbeat reasoning, because from
    # here on the heartbeat is a corroborator and not the authority. `None` means the
    # runtime could not be read and the pre-C36 chain below decides unchanged.
    runtime_state, runtime_reason = (runtime_fn or runtime_liveness)(config, agent)

    dead = quiet_for = None
    attached = None
    if target:
        rc, out = _tmux("display-message", "-p", "-t", target,
                        "#{pane_dead}\t#{window_activity}\t#{session_attached}")
        if rc == 0 and out.count("\t") >= 2:
            d, act, att = out.split("\t")[:3]
            dead = d.strip() == "1"
            attached = att.strip() not in {"", "0"}
            try:
                quiet_for = max(0.0, time.time() - int(act.strip()))
            except ValueError:
                quiet_for = None

    today = datetime.now(timezone.utc).date().isoformat()
    rows = ledger_rows()
    # HISTORY, NOT A GATE (C9). Kept because "how much spawning happened today" is
    # useful context; it enforces nothing. The gate is the live count above.
    spawns_today = sum(1 for r in rows if r.get("kind") == "spawn" and r.get("ts", "").startswith(today))
    # C31 (2026-07-29): THE RATE LIMIT IS PER WINDOW INSTANCE, NOT PER ROSTER ID.
    #
    # This took the newest `nudge` row for the AGENT ID and nothing else, so after a
    # window was killed and re-spawned, nudges to the FRESH window were refused for
    # the remainder of the 600s interval because a nudge had gone to the DESTROYED one
    # minutes earlier. The limit exists to avoid pestering a working session; a session
    # that did not exist when the earlier nudge was sent cannot have been pestered by
    # it. Observed during 2026-07-29 bring-up.
    #
    # Same root cause as C24 one field over — state keyed to an identity outlives the
    # session that identity named — and the two are COUPLED: C24 stops a re-spawned
    # main being heartbeat-blocked, and this stops it being rate-limit-blocked instead.
    # Fixing either alone leaves the fresh session unreachable, which is the symptom
    # C24 exists to remove.
    #
    # The spawn epoch is read from the ledger the adapter already writes, so this needs
    # no new state file and cannot disagree with one. Timestamps are PARSED rather than
    # string-compared: `_now()` is stable ISO-8601 today, but an ordering that silently
    # depends on that is the kind of thing a format change breaks without a test.
    # A window created outside `cmd_spawn` leaves no spawn row, so `spawn_at` is None
    # and the old whole-history behaviour applies — the fail-safe direction, since it
    # keeps the limit rather than dropping it. A nudge row whose ts cannot be parsed is
    # skipped and cannot hold the limit open; that matches the previous behaviour
    # exactly (it caught ValueError and left `since_nudge` None) and is NOT widened
    # here, because a corrupt ledger row that permanently blocks nudging would wedge
    # the whole fleet — a strictly worse failure than one missed rate limit.
    def _ts(row: dict) -> float | None:
        try:
            return datetime.fromisoformat(str(row.get("ts"))).timestamp()
        except (TypeError, ValueError):
            return None

    def _times(kind: str) -> list[float]:
        out = []
        for r in rows:
            if r.get("kind") != kind or r.get("agent") != agent:
                continue
            t = _ts(r)
            if t is not None:
                out.append(t)
        return out

    spawn_at = max(_times("spawn"), default=None)
    nudges_this_instance = [t for t in _times("nudge")
                            if spawn_at is None or t >= spawn_at]
    last_nudge_at = max(nudges_this_instance, default=None)
    since_nudge = None if last_nudge_at is None else max(0.0, time.time() - last_nudge_at)

    blockers: list[str] = []
    if not authorised:
        blockers.append("flags.codex_sendkeys is off (gate OP-SENDKEYS-CODEX)")
    if not target:
        blockers.append(why)
    if dead is True:
        blockers.append("pane is dead")
    if dead is None and target:
        blockers.append("could not read pane state — fail closed")
    # HISTORICAL CLAIM, NOW FALSIFIED — read this before trusting the skip below.
    # This block used to state that window_activity only reflects OUTPUT while a
    # client is attached, citing a 2026-07-27 measurement in which a detached
    # window printing every second and one sleeping reported the SAME timestamp.
    #
    # Re-measured 2026-07-29 (see DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S): THAT IS NOT
    # TRUE. With zero clients attached, a window emitting 5x/second held quiet_for
    # at 0-1s for 60s straight while a sleeping window in the same session aged
    # 84 -> 139s. Detached tracking works. The 2026-07-27 reading was almost
    # certainly one of the two measurement artefacts documented at that constant —
    # a fish-killed pane, or a name-target that silently resolved to a different
    # window — both of which make a busy window look quiet.
    #
    # THE BEHAVIOUR BELOW IS DELIBERATELY UNCHANGED ANYWAY. Removing the skip would
    # make the quiet-check STRICTER (it would start blocking detached sessions that
    # are genuinely emitting), which is a real improvement but a different change
    # with its own blast radius; C35's brief was the heartbeat blocker alone. Filed
    # as a follow-up on the C35 row. Note the C35 override does NOT depend on this
    # skip: it reads quiet_for directly, which is computed regardless of attachment,
    # and a live test pins that in a DETACHED throwaway session.
    quiet_check = "n/a"
    if not target:
        pass
    elif attached is False:
        # NOT a blocker. A detached session is the normal overnight state — the
        # whole point of this system is coordinating while the operator is away —
        # so refusing every nudge when detached would defeat it. Retained as-is
        # pending the follow-up above; the wording no longer asserts the falsified
        # claim, it just records that this check is not being applied here.
        quiet_check = "skipped: session detached (see C35 follow-up — this skip is now known " \
                      "to be more permissive than it needs to be)"
    elif quiet_for is None:
        blockers.append("could not read window_activity — fail closed")
    elif quiet_for < quiet_s:
        quiet_check = f"blocked: output {quiet_for:.0f}s ago"
        blockers.append(f"window produced output {quiet_for:.0f}s ago (< {quiet_s:.0f}s) — "
                        f"likely mid-generation")
    else:
        quiet_check = f"passed: quiet for {quiet_for:.0f}s"
    # C35: the quiescence override, evaluated ONLY against the `working` blocker.
    # Every other guard above and below is untouched — a dead pane, an unreadable
    # pane, a failed target resolution, the normal quiet check, the rate limit and
    # the authorisation flag all still refuse on their own. The override cannot
    # turn a refusal into a nudge by itself; it can only decline to ADD this one
    # blocker. Staleness deliberately stays a separate blocker: it is already
    # tunable with --heartbeat-max-age, whereas state was not tunable at all,
    # and that asymmetry is the whole defect.
    #
    # FAIL CLOSED on every input. The override needs a pane that is positively
    # alive (`dead is False`, not merely "not True") and a window_activity we
    # could actually parse. Anything unreadable leaves the blocker in place —
    # this module's defect history is C3, C6, C8, C24 and today's C35, and every
    # one of them was a fail-OPEN. A non-positive threshold disables the override
    # entirely rather than meaning "override always", so a mis-set 0 is inert.
    hb_override_applied = False
    hb_stale_override_applied = False
    hb_stale_override_reason = "not evaluated (heartbeat not stale)"
    hb_override_reason: str | None = None
    # C52: the independent evidence a `working` self-report is checked against. Read
    # unconditionally (not only when the heartbeat says working) so `probe` reports the
    # same picture whatever the claim is — a reader comparing a refusal against a
    # delivery must see the same fields in both.
    working_claim = "n/a"
    pane_busy, pane_busy_reason = (None, "no target to read")
    if target:
        pane_busy, pane_busy_reason = (pane_busy_fn or pane_busy_marker)(target)
    task_pid, pid_reason = heartbeat_task_pid(hb)
    task_pid_alive = None if task_pid is None else pid_alive(task_pid)

    # ---- C36: when the runtime has an answer, it DECIDES and the heartbeat corroborates ----
    #
    # Both directions are acted on and both are reported, the way C35 reports its
    # override even when it did not fire:
    #
    #   runtime ACTIVE -> BLOCK, whatever the heartbeat says. This is a protection the
    #     pre-C36 guard did not have at all: a main whose heartbeat wrongly reads
    #     `idle` while it is mid-generation was previously nudged without hesitation.
    #   runtime IDLE   -> the heartbeat's `working` and its staleness both stop being
    #     blockers. The agent is demonstrably at its prompt; a self-report that says
    #     otherwise, or that stopped being written, is exactly the stale claim this
    #     defect is about. (Measured 2026-07-27: a live session mid-generation carried
    #     a 2h-stale heartbeat, and 2026-07-29: mainD read `working` while its runtime
    #     read idle.)
    #   runtime None   -> UNAVAILABLE. Change nothing; the pre-C36 chain below decides.
    #
    # Note what this does NOT touch: pane_dead, the quiet check, target resolution, the
    # rate limit and the auth flag are all evaluated above and stand unchanged. C36
    # replaces the heartbeat's authority, not the guard chain.
    if runtime_state == "active":
        blockers.append(f"runtime says ACTIVE — {runtime_reason}")
    elif runtime_state == "idle":
        pass                      # heartbeat blockers below are skipped entirely
    elif hb is None:
        blockers.append("no heartbeat — cannot tell if the agent is thinking; fail closed")
    else:
        if str(hb.get("state")) == "working":
            # C52: the claim is corroborated or it does not stand. C35's quiescence
            # test is now ONE of the contradiction sources rather than the only one —
            # it is defeated by a main whose subagent rows redraw every second, which
            # is what wedged mainB for thirteen minutes on 2026-08-12.
            working_claim, hb_override_reason = corroborate_working_claim(
                runtime_state=runtime_state, runtime_reason=runtime_reason,
                pane_busy=pane_busy, pane_reason=pane_busy_reason,
                task_pid=task_pid, task_pid_alive=task_pid_alive, pid_reason=pid_reason,
                pane_dead=dead, quiet_for=quiet_for, override_quiet_s=hb_override_quiet_s,
                quiet_s=quiet_s)
            hb_override_applied = working_claim == "contradicted"
            if not hb_override_applied:
                blockers.append(f"heartbeat says working (task {hb.get('task_id')}) — "
                                f"{working_claim.upper()}: {hb_override_reason}")
        if hb_age is not None and hb_age > hb_max_age:
            # R1 (2026-08-11): THE GUARD USED TO HARDEN AS THE CONDITION WORSENED.
            #
            # Three-way deadlock, measured today across the whole fleet. The daemon
            # calls a heartbeat older than 3600s STUCK and tries to nudge; this line
            # refused every nudge past 900s. So between 900s and 3600s nobody has
            # decided you are stuck, and past 3600s somebody has and can no longer
            # reach you. Every main crossed 900s at ~10:14-10:22Z and the entire
            # fleet — the coordinator included — became permanently unreachable:
            # 1,903 stuck-nudge-refused rows in advisory.jsonl. The only way back was
            # a human passing --heartbeat-max-age 86400 by hand.
            #
            # Neither existing escape hatch reaches this. C35 lifts the `working`
            # blocker and never staleness. C36 is codex-rollout-only, so on an
            # all-Claude fleet its availability is exactly 0%.
            #
            # The fix is NOT to raise the default: that trades a deadlock for typing
            # into a pane that is genuinely mid-generation. Staleness is a TIMER, and
            # a timer cannot tell "wedged" from "quietly waiting". The pane can:
            # `pane_dead` says the window still exists, and quiescence says the TUI is
            # settled at its prompt rather than redrawing a spinner. So the same
            # evidence C35 already trusts to overrule a `working` self-report — and
            # only that evidence — overrules an OLD one. A heartbeat that stopped
            # being written is not a reason to stop trying to reach a demonstrably
            # alive, demonstrably idle pane; it is the reason to try.
            if hb_stale_override_ok(dead, quiet_for, hb_override_quiet_s):
                hb_stale_override_applied = True
                hb_stale_override_reason = (
                    f"heartbeat {hb_age:.0f}s stale (> {hb_max_age:.0f}s) BUT the pane is alive "
                    f"and quiet {quiet_for:.0f}s (>= {hb_override_quiet_s:.0f}s) — settled at its "
                    f"prompt, so it is reachable; refusing here is the R1 deadlock")
            else:
                hb_stale_override_reason = _stale_override_refusal(
                    dead, quiet_for, hb_override_quiet_s)
                blockers.append(f"heartbeat is {hb_age:.0f}s stale (> {hb_max_age:.0f}s)"
                                f" — {hb_stale_override_reason}")

    return {"agent": agent, "target": target, "target_reason": why,
            "authorised": authorised, "spawn_cap": spawn_cap, "spawn_cap_reason": cap_reason,
            "spawn_cap_key": CAP_KEY,
            "live_mains": sorted(live_ids) if live_ids is not None else None,
            "live_mains_count": len(live_ids) if live_ids is not None else None,
            "live_mains_reason": live_reason, "spawns_today_history_only": spawns_today,
            "pane_dead": dead, "window_quiet_for_s": quiet_for,
            "session_attached": attached, "quiet_check": quiet_check,
            "heartbeat_state": (hb or {}).get("state"), "heartbeat_age_s": hb_age,
            # C35: the override is reported even when it did NOT fire, so `probe`
            # explains a `working` heartbeat that was believed as well as one that
            # was overridden. A human reading probe is never surprised by a nudge
            # the guard "should" have refused.
            "heartbeat_override_quiet_s": hb_override_quiet_s,
            "heartbeat_override_applied": hb_override_applied,
            "heartbeat_override_reason": hb_override_reason,
            # C52: the three-valued verdict on a `working` claim, plus every input it
            # was computed from. Reported ALWAYS — including `n/a` when the heartbeat
            # did not claim to be working — because the whole defect was a refusal
            # whose evidence nobody could see. `undetermined` is a first-class value
            # here and must never be read as either of the other two.
            "working_claim": working_claim,
            "pane_busy": pane_busy,
            "pane_busy_reason": pane_busy_reason,
            "task_pid": task_pid,
            "task_pid_alive": task_pid_alive,
            "task_pid_reason": pid_reason,
            # R1: reported ALWAYS, fired or not, for the same reason C35's is — a
            # reader must be able to tell "reachable despite a stale heartbeat" from
            # "refused, and here is the pane evidence that refused it".
            "heartbeat_stale_override_applied": hb_stale_override_applied,
            "heartbeat_stale_override_reason": hb_stale_override_reason,
            # C36: reported ALWAYS, including when the runtime had no answer, so a
            # reader can tell "the runtime cleared this main" from "the runtime was
            # unavailable and the heartbeat decided" — and can see which mains are
            # covered at all. An UNAVAILABLE that looks like an absent field is how a
            # silent degradation hides.
            "runtime_state": runtime_state,
            "runtime_reason": runtime_reason,
            "runtime_decided": runtime_state is not None,
            "seconds_since_last_nudge": since_nudge,
            # C31: surfaced so a refusal can be read as "this WINDOW was nudged", not
            # "this id was nudged at some point in its history".
            "nudges_this_window_instance": len(nudges_this_instance),
            "spawned_at": None if spawn_at is None else datetime.fromtimestamp(
                spawn_at, timezone.utc).isoformat(timespec="seconds"),
            "submission_verification": "cursor-anchored composer check before Enter; after it "
                                       "BOTH the transcript echo (C6/C12, anchored pre-Enter) "
                                       "AND the composer buffer returning to its pre-typing "
                                       "baseline (C51). Any failure rolls the typed text back "
                                       "with Ctrl-U and records it; may fail closed",
            "blockers": blockers, "nudge_ok": not blockers}


def cmd_probe(args: argparse.Namespace) -> int:
    p = probe(load_config(), args.agent, args.quiet_s, args.heartbeat_max_age,
              getattr(args, "heartbeat_override_quiet_s", DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S))
    if args.json:
        print(json.dumps(p, indent=2))
        return 0 if p["nudge_ok"] else EX_BLOCKED
    print(f"agent            {p['agent']}")
    print(f"tmux target      {p['target'] or '(refused)'}  — {p['target_reason']}")
    print(f"authorised       {p['authorised']}")
    print(f"pane_dead        {p['pane_dead']}")
    q = p["window_quiet_for_s"]
    print(f"window quiet     {q:.0f}s" if q is not None else "window quiet     (unreadable)")
    age = p["heartbeat_age_s"]
    print(f"quiet-check      {p['quiet_check']}")
    # C36: printed BEFORE the heartbeat, because when it has an answer it is the one
    # that decided and the heartbeat below is corroboration. `UNAVAILABLE` is printed
    # too — a reader must be able to see that this main is NOT covered by the runtime
    # signal, rather than infer it from a missing line.
    print(f"runtime          {str(p.get('runtime_state') or 'UNAVAILABLE').upper()}"
          f" — {p.get('runtime_reason')}")
    print(f"heartbeat        {p['heartbeat_state']} (age {age:.0f}s)"
          f"{'  [corroborator: the runtime decided]' if p.get('runtime_decided') else ''}"
          if age is not None else "heartbeat        (none)")
    # C35: printed whenever the heartbeat said `working`, in BOTH directions. An
    # override that fired silently would make `probe` disagree with `nudge`, which
    # is precisely the surprise this line exists to prevent.
    if p.get("heartbeat_override_reason") is not None:
        print(f"hb-override      {'APPLIED' if p['heartbeat_override_applied'] else 'not applied'}"
              f": {p['heartbeat_override_reason']}")
    # C52: printed whenever the heartbeat claimed to be working, in all THREE
    # directions. `UNDETERMINED` is the one that has to be visible — a refusal nobody
    # can distinguish from "it really is working" is what cost thirteen minutes of
    # idle GPU on 2026-08-12.
    if p.get("working_claim") not in (None, "n/a"):
        print(f"working-claim    {str(p['working_claim']).upper()}"
              f"  [pane_busy={p.get('pane_busy')}, task_pid={p.get('task_pid')}"
              f" alive={p.get('task_pid_alive')}]")
    live_n = p["live_mains_count"]
    cap = p["spawn_cap"]
    print(f"live mains       {live_n if live_n is not None else '(unreadable — spawn refuses)'}"
          f"/{cap if cap is not None else '(unset — spawn refuses)'}"
          f"  [{p['spawn_cap_key']}]  {', '.join(p['live_mains'] or []) or '-'}")
    print(f"spawns today     {p['spawns_today_history_only']} (history only, enforces nothing)")
    sn = p["seconds_since_last_nudge"]
    print(f"last nudge       {sn:.0f}s ago" if sn is not None else "last nudge       (never)")
    print(f"submission check {p['submission_verification']}")
    print(f"\nnudge_ok         {p['nudge_ok']}")
    for b in p["blockers"]:
        print(f"  BLOCKED  {b}")
    return 0 if p["nudge_ok"] else EX_BLOCKED


def cmd_nudge(args: argparse.Namespace) -> int:
    if len(args.message) > MAX_NUDGE_MESSAGE_CHARS:
        print(f"REFUSING: nudge message is {len(args.message)} chars; the calibrated policy "
              f"cap is {MAX_NUDGE_MESSAGE_CHARS}. Chunked sending is verified to 12,000 chars, "
              f"so this is a 'write a brief file instead' ceiling, not a TUI limit.",
              file=sys.stderr)
        return EX_USAGE
    if "\n" in args.message or "\r" in args.message:
        # A literal newline IS the submit key. It would send a truncated nudge and
        # leave the remainder typed into whatever came next — fail closed.
        print("REFUSING: nudge message contains a newline, which the TUI reads as Enter and "
              "would submit a partial message. Send a single line.", file=sys.stderr)
        return EX_USAGE
    stripped = args.message.lstrip()
    if stripped.startswith(_COMPOSER_MODE_PREFIXES) or _INLINE_PICKER_RE.search(args.message):
        print(f"REFUSING: nudge message starts with one of {' '.join(_COMPOSER_MODE_PREFIXES)} "
              f"or contains a token-initial '{_INLINE_PICKER_TRIGGER}'. Those put the composer in "
              f"a mode where "
              f"Enter accepts a completion (or runs a command) instead of submitting prose, and "
              f"the resulting pane is indistinguishable from a successful send. Rephrase without "
              f"the trigger — write the path plainly, or point at a brief file.", file=sys.stderr)
        return EX_USAGE
    if not _pending_fragment(args.message):
        # Nothing matchable means nothing verifiable, and an unverifiable nudge is
        # a bare Enter fired into someone else's pane.
        print("REFUSING: nudge message is blank once trailing whitespace is dropped, so "
              "submission cannot be verified.", file=sys.stderr)
        return EX_USAGE
    config = load_config()
    p = probe(config, args.agent, args.quiet_s, args.heartbeat_max_age,
              getattr(args, "heartbeat_override_quiet_s", DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S))
    if p["seconds_since_last_nudge"] is not None and p["seconds_since_last_nudge"] < args.min_interval_s:
        p["blockers"].append(f"rate limit: last nudge {p['seconds_since_last_nudge']:.0f}s ago "
                             f"(< {args.min_interval_s:.0f}s)")
        p["nudge_ok"] = False
    if not p["nudge_ok"]:
        print("REFUSING to nudge:", file=sys.stderr)
        for b in p["blockers"]:
            print(f"  · {b}", file=sys.stderr)
        return EX_BLOCKED
    if args.dry_run:
        print(f"would send to {p['target']}: {args.message!r}")
        return 0

    # ---- C51: the composer must be EMPTY BEFORE anything is typed ----
    #
    # `doorbell` has had this since C45 (its guard (b)); the PAYLOAD path never did,
    # and the asymmetry ran the wrong way — a payload nudge is the one that types a
    # lot of characters and then presses Enter. Enter submits whatever is ALREADY in
    # the composer, so typing a brief after an operator's half-finished line submits
    # the operator's line too. That is not hypothetical: it is how the 2026-08-12
    # strands "cleared themselves" — the next nudge appended to the stranded text and
    # submitted the concatenation.
    #
    # NOTHING ON THE PANE RECORDS WHO TYPED IT. There is no state that distinguishes
    # operator-typed text from agent-delivered text after the fact, so this refuses
    # rather than guessing, and says exactly what is pending so the refusal is
    # actionable. A refusal costs a retry; a false accept submits somebody's
    # half-written sentence to a live agent.
    #
    # It is also the premise the rollback depends on: having PROVED the composer was
    # empty, every character in it afterwards is this adapter's own, so Ctrl-U cannot
    # destroy operator input.
    faint_ok = composer_faint_is_placeholder(config, args.agent)
    baseline, failure = _read_composer_row(p["target"], faint_ok)
    if failure or baseline is None:
        print(f"REFUSING: could not read the composer of {p['target']} to confirm it holds "
              f"no pending input before typing: {failure} — fail closed", file=sys.stderr)
        return EX_MISCONFIG
    if not _composer_row_is_empty(baseline):
        print(f"REFUSING: pane {p['target']} composer already holds pending input "
              f"{baseline.strip()[:120]!r}. Typing after it and pressing Enter would submit "
              f"THAT text as well, and this adapter cannot tell operator-typed input from "
              f"text an earlier delivery left behind. Clear it with Ctrl-U (NEVER Ctrl-C on "
              f"a Codex pane) or let whoever is typing submit it, then retry. "
              f"`tmux_adapter.py pending` lists every pane in this state.", file=sys.stderr)
        return EX_BLOCKED

    # C6: message and Enter MUST be separate calls. A single send-keys call can
    # leave the text in a Codex prompt while tmux still returns success.
    rc, out = _send_message_chunked(p["target"], args.message)
    if rc != 0:
        return _fail_after_typing("nudge", args.agent, p["target"], baseline,
                                  "send-keys message", out, faint_ok)
    settle_s = max(0.0, float(getattr(args, "settle_s", DEFAULT_NUDGE_SETTLE_S)))
    time.sleep(settle_s)
    fragment = _pending_fragment(args.message)
    # BEFORE Enter the composer must END with the message. Wait for it rather
    # than sampling once: a long chunked message can still be rendering.
    pending_state, failure = _await_state(p["target"], fragment, {"text_present"},
                                          _VERIFY_TIMEOUT_S)
    if failure:
        return _fail_after_typing("nudge", args.agent, p["target"], baseline,
                                  "pre-Enter verification", f"unavailable: {failure}", faint_ok)
    if pending_state == "paste_blob":
        return _fail_after_typing(
            "nudge", args.agent, p["target"], baseline, "pre-Enter verification",
            "the message was mangled into a paste blob — the composer holds a paste "
            "attachment, not editable text; its content is truncated at 1024 chars and "
            "cannot be verified", faint_ok)
    if pending_state != "text_present":
        return _fail_after_typing(
            "nudge", args.agent, p["target"], baseline, "pre-Enter verification",
            "the message did not land in the composer — the cursor is not at the end of "
            "it, so the pane is not accepting typed input (a full-screen modal, e.g. "
            "Codex backtrack mode, does this, faint_ok)")

    # C12: how many times the fragment is on the pane BEFORE Enter, including any
    # stale copy already in the scrollback. A genuine submission moves our copy from
    # the composer into the transcript, so the count holds; an Enter eaten by a
    # completion overlay deletes it, so the count drops and any remaining match is
    # provably a stale one that must not read as success.
    #
    # C51(3), 2026-08-12: THIS CALL USED TO SIT BELOW `send-keys Enter` AND A SETTLE
    # SLEEP. The comment said "BEFORE Enter" while the code sampled AFTER it, so the
    # anchor was taken after the very mutation it exists to detect and C12 was
    # vacuous. Reproduced against real panes: with an identical fragment already in
    # the transcript and an Enter consumed by a completion picker, the true pre-Enter
    # count was 2 and the post-Enter count 1, `1 >= 1` passed, and the adapter exited
    # 0, printed "nudged" and wrote a ledger row for a submission that never happened.
    # Moving the call is the whole fix; the predicate was always right.
    pre_enter_occurrences = _fragment_occurrences(p["target"], fragment)

    rc, out = _tmux("send-keys", "-t", p["target"], "Enter")
    if rc != 0:
        return _fail_after_typing("nudge", args.agent, p["target"], baseline,
                                  "send-keys Enter", out, faint_ok)
    time.sleep(settle_s)
    # AFTER Enter the message must have MOVED: off the cursor, but still on the
    # pane as the transcript echo. Note this is NOT "the message is gone from the
    # pane" — both TUIs echo the submitted text above, and treating that as
    # failure is exactly the false negative this fix removes. Nor is it merely
    # "no longer at the cursor": that would accept an Enter which a completion
    # overlay consumed to rewrite the composer. Success is the echo, positively.
    submitted_state, failure = _await_state(p["target"], fragment, {"text_echoed"},
                                            _VERIFY_TIMEOUT_S, _VERIFY_STABLE_SAMPLES,
                                            min_occurrences=pre_enter_occurrences)
    if failure:
        return _fail_after_typing("nudge", args.agent, p["target"], baseline,
                                  "post-Enter echo check", f"unavailable: {failure}", faint_ok)
    if submitted_state == "text_present":
        return _fail_after_typing(
            "nudge", args.agent, p["target"], baseline, "post-Enter echo check",
            "text present but unsubmitted — the composer still ends with the message, so "
            "the TUI swallowed Enter", faint_ok)
    if submitted_state == "paste_blob":
        return _fail_after_typing(
            "nudge", args.agent, p["target"], baseline, "post-Enter echo check",
            "the composer holds a paste blob", faint_ok)
    if submitted_state != "text_echoed":
        return _fail_after_typing(
            "nudge", args.agent, p["target"], baseline, "post-Enter echo check",
            "the message is no longer at the cursor but is not echoed on the pane either. "
            "Enter was consumed by something that rewrote the composer (a completion "
            "picker, e.g. Codex '@' or a '/' menu, faint_ok) rather than submitting")

    # ---- C51: and the BUFFER must be gone, not merely the keystrokes dispatched ----
    # The echo above is evidence that our text reached the transcript; this is evidence
    # that it LEFT the composer. Both are required because each alone has been defeated:
    # the echo by a stale scrollback copy (C12/C51(3)), and "the buffer is empty" alone
    # by any Enter that clears the composer without submitting. Expressed as a delta
    # against the pre-typing baseline, so it needs no prompt pattern and cannot rot when
    # a TUI changes its chrome — which the glyph table above did, in fifteen days.
    consumed, observed, failure = _await_composer_consumed(
        p["target"], baseline, _VERIFY_TIMEOUT_S, faint_is_placeholder=faint_ok)
    if failure:
        return _fail_after_typing("nudge", args.agent, p["target"], baseline,
                                  "post-Enter buffer check", f"unavailable: {failure}", faint_ok)
    if not consumed:
        return _fail_after_typing(
            "nudge", args.agent, p["target"], baseline, "post-Enter buffer check",
            f"the transcript echo is present but the composer BUFFER was not consumed: it "
            f"holds {(observed or '', faint_ok)[:80]!r} instead of returning to "
            f"{baseline.strip()[:40]!r}")
    # C35: a nudge that only happened because quiescence outvoted a `working`
    # heartbeat is the one most worth being able to reconstruct later — if the
    # override ever does interrupt a real generation, this row is the evidence.
    # `record` drops None fields, so an ordinary nudge is unchanged on disk.
    record("nudge", args.agent, args.message[:200],
           heartbeat_override=p.get("heartbeat_override_reason")
           if p.get("heartbeat_override_applied") else None,
           window_quiet_for_s=p.get("window_quiet_for_s")
           if p.get("heartbeat_override_applied") else None)
    print(f"nudged {args.agent} at {p['target']}")
    return 0


def cmd_doorbell(args: argparse.Namespace) -> int:
    """Ring the fixed doorbell string. Two load-bearing guards, both fail-closed;
    see the C45 block above `doorbell_text` for what is and is not applied here
    and why. Deliberately does NOT call `probe()` or `heartbeat()` — pulling in
    `probe` would silently re-attach every guard C45 removes (quiet-for, rate
    limit, heartbeat state, the C35 override machinery built to patch it), which
    is precisely the deadlock this command exists to stop reproducing.
    """
    config = load_config()
    flags = config.get("flags") or {}
    authorised = str(flags.get("codex_sendkeys")).strip().lower() in {"1", "true", "yes", "on"}
    if not authorised:
        # The master send-keys authorisation (gate OP-SENDKEYS-CODEX), not one of
        # doorbell's two pane-state guards — this adapter does not type into any
        # pane, doorbell or payload, without it.
        print("REFUSING: flags.codex_sendkeys is off (gate OP-SENDKEYS-CODEX)", file=sys.stderr)
        return EX_BLOCKED

    target, why = resolve_target(config, args.agent)
    if not target:
        print(f"REFUSING: {why}", file=sys.stderr)
        return EX_BLOCKED

    # ---- guard (a): pane exists and pane_dead == 0 ----
    rc, out = _tmux("display-message", "-p", "-t", target, "#{pane_dead}")
    if rc != 0 or out.strip() not in ("0", "1"):
        print(f"REFUSING: could not read pane_dead for {target}: {out!r} — fail closed",
              file=sys.stderr)
        return EX_BLOCKED
    if out.strip() == "1":
        print(f"REFUSING: pane {target} is dead", file=sys.stderr)
        return EX_BLOCKED

    # ---- guard (b): composer holds no pending input ----
    # The row read here is ALSO the baseline the C51 submission check and rollback
    # are measured against: "was the ring submitted" is "did the composer come back
    # to exactly this".
    faint_ok = composer_faint_is_placeholder(config, args.agent)
    baseline, failure = _read_composer_row(target, faint_ok)
    if failure or baseline is None:
        print(f"REFUSING: could not read the composer to confirm it holds no pending input: "
              f"{failure} — fail closed rather than risk submitting whatever is there",
              file=sys.stderr)
        return EX_MISCONFIG
    if not _composer_row_is_empty(baseline):
        print(f"REFUSING: pane {target} composer holds pending input "
              f"{baseline.strip()[:120]!r}; ringing the doorbell "
              f"sends a real Enter, which would submit whatever is already typed there, not "
              f"the doorbell string. Clear it (or let whoever is typing submit it) and retry — "
              f"retrying costs nothing, ringing is idempotent.", file=sys.stderr)
        return EX_BLOCKED

    message = doorbell_text(args.agent)
    if args.dry_run:
        print(f"would ring doorbell for {args.agent} at {target}: {message!r}")
        return 0
    # One send-keys call is enough — no chunking, no pacing gap: the string is
    # ~45 chars, an order of magnitude under the smallest calibrated single-burst
    # paste threshold (800 chars, Claude Code CLI v2.1.220). See the C45 block.
    rc, out = _tmux("send-keys", "-l", "-t", target, "--", message)
    if rc != 0:
        return _fail_after_typing("doorbell", args.agent, target, baseline,
                                  "send-keys message", out, faint_ok)
    rc, out = _tmux("send-keys", "-t", target, "Enter")
    if rc != 0:
        return _fail_after_typing("doorbell", args.agent, target, baseline,
                                  "send-keys Enter", out, faint_ok)
    # ---- C51: THE RING IS VERIFIED. It was not, at all, until 2026-08-12 ----
    #
    # This command used to `record("doorbell", ...)` and print success on the strength
    # of the two `send-keys` exit codes above. A zero from `send-keys` means TMUX
    # ACCEPTED THE KEYS — the identical mistake C30(b) documents one command over for
    # `new-window` — and says nothing about whether the TUI consumed them. Reproduced
    # against a real pane that swallows Enter: exit 0, "doorbell rung", a ledger row,
    # and the doorbell string left sitting unsubmitted in the composer. That strand
    # then trips guard (b) above forever, so the pane becomes permanently un-ringable
    # by the text the ring itself left there.
    #
    # There is no fragment-echo check here because the doorbell has no fragment worth
    # matching — it is the same fixed string every time, so an identical copy in the
    # scrollback is the NORMAL state and an echo match would prove nothing (this is
    # C12's stale-copy hazard, structural rather than occasional). The buffer delta
    # has no such weakness: it asks whether THIS composer is empty again, which a
    # previous ring cannot answer for.
    consumed, observed, failure = _await_composer_consumed(
        target, baseline, _VERIFY_TIMEOUT_S, faint_is_placeholder=faint_ok)
    if failure:
        return _fail_after_typing("doorbell", args.agent, target, baseline,
                                  "post-Enter buffer check", f"unavailable: {failure}", faint_ok)
    if not consumed:
        return _fail_after_typing(
            "doorbell", args.agent, target, baseline, "post-Enter buffer check",
            f"the composer BUFFER was not consumed: it holds {(observed or '', faint_ok)[:80]!r} "
            f"instead of returning to {baseline.strip()[:40]!r}, so the Enter did not "
            f"submit and the ring is still sitting in that composer")
    record("doorbell", args.agent, message)
    print(f"doorbell rung for {args.agent} at {target}")
    return 0


# ---------------------------------------------------------------------------
# C51 DETECTOR, 2026-08-12. A PANE HOLDING UNSUBMITTED INPUT IS AN ALARM.
#
# WHY THIS IS A SUBCOMMAND AND NOT A NOTE IN A RUNBOOK. On 2026-08-12 three mains
# sat idle with an instruction queued in their composers, and the condition was
# found each time by a human reading a pane by eye — after the fact, and after the
# MI210 had been at 0% long enough for the operator to raise it for the eleventh
# time. A queued-but-unsubmitted instruction renders EXACTLY like a delivered one
# the main declined, so no amount of reading bus state finds it; the evidence is
# only in the pane, and nothing was looking there.
#
# READ-ONLY, ABSOLUTELY. `display-message` and `capture-pane`, nothing else. It
# never sends a key, never clears a composer and never submits one — the pending
# text may be the operator mid-sentence, and there is nothing in pane state that
# would tell it apart from a stranded delivery. Deciding what to do about pending
# input is the coordinator's call; making it VISIBLE is this command's whole job.
#
# THE TARGET IS RESOLVED, NEVER GUESSED. It goes through `resolve_target`, so a
# roster row whose endpoint does not verify is reported as UNRESOLVED rather than
# having some other pane's composer attributed to it — an alarm naming the wrong
# main is worse than no alarm.
#
# AND UNEVALUABLE IS NOT CLEAN. An unreadable pane or an unresolved endpoint exits
# non-zero, exactly like a pane with pending input. "I could not look" reported as
# "nothing is pending" is the fail-open family this module's entire defect history
# belongs to, and the one this command exists to close.
PENDING_EXIT_CLEAN = 0
PENDING_STATUSES_UNEVALUABLE = ("unresolved", "unreadable")


def pending_input_report(config: dict, agents: list[str] | None = None) -> dict:
    """Every roster pane's composer state. Pure observation; sends nothing.

    Statuses, all distinct so a consumer never has to infer one from another:
      ``pending``    the composer holds unsubmitted input — THE ALARM.
      ``empty``      the composer is at a bare prompt; nothing is queued.
      ``unresolved`` the roster row's tmux endpoint does not verify (see
                     `resolve_target`) — cannot be evaluated, must not read clean.
      ``unreadable`` the endpoint resolves but the pane could not be captured —
                     likewise unevaluable.
      ``no-pane``    the row has no tmux endpoint at all (``monitor:file``). Not a
                     defect and not counted against the fleet: there is no composer.
      ``retired``    the row DECLARES ``role: retired`` and its window is gone. Also
                     not counted — a retired slot having no pane is its normal state,
                     and letting one hold the fleet alarm at non-zero forever would
                     make the exit code unreadable, which is how an alarm gets muted.
                     Narrow on purpose: a retired row whose window DOES resolve is
                     evaluated like any other, so reviving a main without updating its
                     role cannot hide a pending composer.
    """
    roster = [e for e in (config.get("roster") or []) if isinstance(e, dict) and
              str(e.get("id") or "").strip()]
    wanted = set(agents or [])
    rows: list[dict] = []
    for entry in roster:
        rid = str(entry.get("id")).strip()
        if wanted and rid not in wanted:
            continue
        hb, hb_age = heartbeat(rid)
        row: dict[str, object] = {"agent": rid, "role": entry.get("role"),
                                  "heartbeat_state": (hb or {}).get("state"),
                                  "heartbeat_age_s": hb_age}
        endpoint = str(entry.get("endpoint") or "")
        if not endpoint.startswith("tmux:"):
            row.update({"status": "no-pane", "target": None,
                        "detail": f"endpoint {endpoint!r} has no tmux pane"})
            rows.append(row)
            continue
        target, why = resolve_target(config, rid)
        if not target:
            retired = str(entry.get("role") or "").strip().lower() == "retired"
            row.update({"status": "retired" if retired else "unresolved",
                        "target": None, "detail": why})
            rows.append(row)
            continue
        composer_row, failure = _read_composer_row(
            target, composer_faint_is_placeholder(config, rid))
        if failure or composer_row is None:
            row.update({"status": "unreadable", "target": target, "detail": failure})
            rows.append(row)
            continue
        if _composer_row_is_empty(composer_row):
            row.update({"status": "empty", "target": target, "detail": why})
        else:
            row.update({"status": "pending", "target": target, "detail": why,
                        "pending_text": composer_row.strip()[:200],
                        "pending_chars": len(composer_row.strip())})
        rows.append(row)
    missing = sorted(wanted - {str(r["agent"]) for r in rows})
    return {
        "generated_at": _now(),
        "panes": rows,
        "pending": sorted(str(r["agent"]) for r in rows if r["status"] == "pending"),
        "unevaluable": sorted(str(r["agent"]) for r in rows
                              if r["status"] in PENDING_STATUSES_UNEVALUABLE),
        "not_in_roster": missing,
    }


def pending_exit_code(report: dict) -> int:
    """0 ONLY when every roster pane was evaluated and none holds pending input.

    Pending input outranks unevaluable in the exit code because it is the actionable
    alarm, but both are non-zero: a caller that treats any non-zero as "not provably
    clean" is always right, which is the property this module keeps failing to have.
    """
    if report.get("pending") or report.get("not_in_roster"):
        return EX_BLOCKED
    if report.get("unevaluable"):
        return EX_MISCONFIG
    return PENDING_EXIT_CLEAN


def cmd_pending(args: argparse.Namespace) -> int:
    report = pending_input_report(load_config(), args.agent or None)
    if args.json:
        print(json.dumps(report, indent=2))
        return pending_exit_code(report)
    for row in report["panes"]:
        flag = {"pending": "PENDING ", "empty": "ok      ", "unresolved": "UNRESOLVED",
                "unreadable": "UNREADABLE", "no-pane": "-       ",
                "retired": "retired "}.get(str(row["status"]), "?")
        line = f"{flag} {str(row['agent']):18s} {str(row.get('target') or '-'):28s}"
        if row["status"] == "pending":
            line += f" heartbeat={row.get('heartbeat_state')} :: {row.get('pending_text')!r}"
        elif row["status"] in PENDING_STATUSES_UNEVALUABLE:
            line += f" :: {row.get('detail')}"
        print(line)
    for rid in report["not_in_roster"]:
        print(f"UNKNOWN  {rid:18s} — no roster row; refusing to guess a pane")
    print()
    if report["pending"]:
        print(f"ALARM: {len(report['pending'])} pane(s) hold queued-but-unsubmitted input: "
              f"{', '.join(report['pending'])}. That looks to each main exactly like an "
              f"instruction it was given and declined. Do NOT blind-submit it — it may be "
              f"operator-typed; confirm who typed it, then submit or clear (Ctrl-U, NEVER "
              f"Ctrl-C on a Codex pane).")
    if report["unevaluable"]:
        print(f"NOT EVALUATED: {', '.join(report['unevaluable'])} — this is not a clean "
              f"result, it is a missing one.")
    if not report["pending"] and not report["unevaluable"] and not report["not_in_roster"]:
        print("clean: every roster pane was read and none holds pending input")
    return pending_exit_code(report)


# ---------------------------------------------------------------------------
# C54, 2026-08-12. THE DETECTOR'S MISSING OTHER HALF.
#
# WHAT C51's `pending` LEFT UNSOLVED. Within an hour of existing it diagnosed a
# fleet-wide stall in one command — three mains parked at composers holding
# never-submitted instructions — and then every path to those mains refused, ALL OF
# THEM CORRECTLY: `nudge` refuses because typing after pending input submits it too;
# `doorbell` refuses because its Enter submits whatever is already there; the bus
# cannot reach a session that is parked at its composer rather than draining. The only
# remedy left was Ctrl-U by hand, per pane, and the coordinator is denied
# `tmux send-keys` by the permission classifier — so a human had to press the key
# every time. Compute measured idle for sixteen continuous minutes with work assigned
# to both halves of the machine and neither able to receive it. A detector with no
# remedy just relocates the dependency on a human.
#
# TWO VERBS, NOT ONE, AND THE TOOL MUST NOT GUESS WHICH. Of the three panes, mainC's
# pending text was CORRECT and wanted submitting; mainA's and mainB's had been
# SUPERSEDED by later operator instructions and submitting them would have started a
# reboot-staging run instead of a measurement, and stopped a main that should have
# kept working. Nothing on the pane distinguishes those cases — the difference is
# entirely in intent the operator holds — so `clear` (discard) and `submit` (accept)
# are separate commands and the choice is made by the caller, explicitly, every time.
#
# THE ACKNOWLEDGEMENT GATE IS `--expect`, AND IT IS STRONGER THAN A CONFIRMATION.
# `--force` exists and simply says "whatever is there, act on it". `--expect` names
# the text the caller believes is pending and refuses if the pane holds anything else,
# which closes the window between READING the pane and ACTING on it: an operator who
# types while a clear is in flight cannot have their new sentence discarded by a
# decision made about the old one. That is the TOCTOU shape this module keeps meeting,
# and here it is a one-line defence. Neither flag given is a refusal, not a default:
# discarding an operator's words must never be something that happens by omission.
#
# NEVER Ctrl-C. `clear` sends Ctrl-U and nothing else. A second Ctrl-C exits a Codex
# session and destroys the window; it has already cost this fleet a main. There is no
# code path in this command that can emit it, and a test asserts that over the whole
# call rather than over the happy path.
#
# THE KEYSTROKE IS NOT THE EVIDENCE, same as C51: after acting, the composer is
# RE-READ and must be empty. `send-keys` exiting 0 means tmux accepted the keys.
#
# AND EVERY DISCARD IS LOGGED VERBATIM. `record` gets the full pending text, untrimmed,
# in `pending_text` — if a clear ever destroys an instruction that mattered, the ledger
# is where it is recovered from. That is the whole reason a discard is allowed at all.
def _await_composer_empty(target: str, timeout_s: float,
                          stable_samples: int = _VERIFY_STABLE_SAMPLES,
                          faint_is_placeholder: bool = False
                          ) -> tuple[bool, str | None, str | None]:
    """Is the composer empty? (ok, last observed row, read failure). Never assumes."""
    deadline = time.monotonic() + max(0.0, timeout_s)
    run, observed = 0, None
    while True:
        row, failure = _read_composer_row(target, faint_is_placeholder)
        if failure:
            return False, observed, failure
        observed = row
        run = run + 1 if _composer_row_is_empty(row or "") else 0
        if run >= max(1, stable_samples):
            return True, observed, None
        if run == 0 and time.monotonic() >= deadline:
            return False, observed, None
        time.sleep(_VERIFY_POLL_S)


def _composer_action(args: argparse.Namespace, verb: str) -> int:
    """Shared body of `clear` and `submit`. `verb` decides the key and the wording.

    Guard set is deliberately doorbell's — authorisation, a VERIFIED target, a live
    pane — plus the acknowledgement gate, and deliberately NOT the payload guards
    (quiet-for, heartbeat state, rate limit). Those exist to stop a BRIEF being typed
    into a pane mid-generation; this command types no brief. It presses one key, about
    text the caller has already read and named, on the caller's explicit instruction —
    and a main parked at its composer is exactly the state in which the payload guards
    have nothing useful to say and everything to block.
    """
    config = load_config()
    flags = config.get("flags") or {}
    if str(flags.get("codex_sendkeys")).strip().lower() not in {"1", "true", "yes", "on"}:
        print("REFUSING: flags.codex_sendkeys is off (gate OP-SENDKEYS-CODEX)", file=sys.stderr)
        return EX_BLOCKED

    # IDENTITY IS VERIFIED, NEVER INFERRED. `resolve_target` refuses unless the
    # endpoint's window resolves to the window it names — tmux silently falls back to
    # the session's current window on a miss, and clearing the wrong pane destroys
    # somebody's work with no way to know it happened.
    target, why = resolve_target(config, args.agent)
    if not target:
        print(f"REFUSING: {why}", file=sys.stderr)
        return EX_BLOCKED

    rc, out = _tmux("display-message", "-p", "-t", target, "#{pane_dead}")
    if rc != 0 or out.strip() not in ("0", "1"):
        print(f"REFUSING: could not read pane_dead for {target}: {out!r} — fail closed",
              file=sys.stderr)
        return EX_BLOCKED
    if out.strip() == "1":
        print(f"REFUSING: pane {target} is dead", file=sys.stderr)
        return EX_BLOCKED

    faint_ok = composer_faint_is_placeholder(config, args.agent)
    pending, failure = _read_composer_row(target, faint_ok)
    if failure or pending is None:
        print(f"REFUSING: could not read the composer of {target}: {failure} — fail closed",
              file=sys.stderr)
        return EX_MISCONFIG

    if _composer_row_is_empty(pending):
        if verb == "clear":
            # Idempotent: the desired end state already holds. Saying so with exit 0
            # is what lets a coordinator run this without first running `pending`.
            print(f"nothing to clear: {args.agent} at {target} has an empty composer")
            return 0
        print(f"REFUSING: {args.agent} at {target} has an EMPTY composer — there is nothing to "
              f"submit. If you expected pending text, it was submitted or cleared between your "
              f"read and this call; run `tmux_adapter.py pending` again.", file=sys.stderr)
        return EX_BLOCKED

    # ---- the acknowledgement gate ----
    if args.expect is not None:
        if _normalise(args.expect) not in _normalise(pending):
            print(f"REFUSING: --expect does not match what the pane actually holds.\n"
                  f"  expected : {args.expect!r}\n"
                  f"  pane has : {pending!r}\n"
                  f"The composer changed between your read and this call — somebody may be "
                  f"typing. Re-read it with `tmux_adapter.py pending --agent {args.agent}` and "
                  f"decide again.", file=sys.stderr)
            return EX_BLOCKED
    elif not args.force:
        print(f"REFUSING: {verb} needs an explicit acknowledgement of what it is acting on, "
              f"because that text may be the operator's.\n"
              f"  pane has : {pending!r}\n"
              f"Pass --expect '<the text you just read>' (refuses if the pane changed under "
              f"you — prefer this) or --force (acts on whatever is there).", file=sys.stderr)
        return EX_USAGE

    if args.dry_run:
        print(f"would {verb} {args.agent} at {target}: {pending!r}")
        return 0

    # C55: a Claude composer holding queued text ignores a BARE keystroke. Measured
    # 2026-08-12 against live panes: `Enter`, `C-m`, `C-u` and `BSpace` each left the
    # text exactly where it was, re-read and confirmed. Sending any ORDINARY CHARACTER
    # first, and only then the key, submits — verified by emptying mainC's and mainD's
    # composers, both of which resumed work immediately afterwards.
    #
    # So the wake character is not cosmetic; without it `submit` and `clear` cannot
    # succeed at all. They failed HONESTLY before this (the post-action re-read caught
    # it every time and never claimed success), which is why nothing was lost — but an
    # operator was left pressing keys by hand for an hour because the tool could only
    # report its own failure. NEVER C-c — see the C54 block.
    #
    # The wake character is a SPACE, which is inert for `submit` (it rides into the
    # submitted text harmlessly) and for `clear` (C-u kills the whole line regardless).
    key = "C-u" if verb == "clear" else "Enter"
    rc, out = _tmux("send-keys", "-t", target, " ")
    if rc != 0:
        print(f"send-keys wake-character failed: {out}", file=sys.stderr)
        return EX_MISCONFIG
    time.sleep(_WAKE_SETTLE_S)
    rc, out = _tmux("send-keys", "-t", target, key)
    if rc != 0:
        print(f"send-keys {key} failed: {out}", file=sys.stderr)
        return EX_MISCONFIG

    empty, observed, failure = _await_composer_empty(target, _VERIFY_TIMEOUT_S,
                                                     faint_is_placeholder=faint_ok)
    if failure:
        print(f"{verb} NOT confirmed for {args.agent} at {target}: the composer could not be "
              f"re-read after {key} ({failure}). The keystroke was sent; whether it took is "
              f"UNKNOWN. Re-run `tmux_adapter.py pending --agent {args.agent}`.", file=sys.stderr)
        record(f"{verb}-unconfirmed", args.agent, f"composer unreadable after {key}: {failure}",
               target=target, pending_text=pending)
        return EX_MISCONFIG
    if not empty:
        print(f"{verb} NOT confirmed for {args.agent} at {target}: the composer still holds "
              f"{(observed or '')!r} after {key}. Nothing was accomplished and the text is "
              f"still pending.", file=sys.stderr)
        record(f"{verb}-unconfirmed", args.agent, f"composer still holds text after {key}",
               target=target, pending_text=pending, observed=observed)
        return EX_MISCONFIG

    # VERBATIM, UNTRUNCATED. If a clear ever discards something that mattered, this row
    # is where it is recovered from — `detail` is trimmed for readability, the field is
    # not trimmed at all.
    record(verb, args.agent, pending[:200], target=target, pending_text=pending,
           acknowledgement="--expect" if args.expect is not None else "--force")
    print(f"{verb}ed {args.agent} at {target}: {pending!r}"
          + ("  (discarded — recoverable from the adapter ledger)" if verb == "clear"
             else "  (submitted)"))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    return _composer_action(args, "clear")


def cmd_submit(args: argparse.Namespace) -> int:
    return _composer_action(args, "submit")


def cmd_spawn(args: argparse.Namespace) -> int:
    """Create the agent's four bus files, THEN start its pane.

    Order is the whole point. A main whose inbox/outbox/heartbeat/cursor do not
    exist yet comes up with nowhere to write, and its first drain fails. The roster
    row must already exist: deciding that a new main SHOULD exist is judgment, and
    judgment belongs to coordinator-agent, not here.

    The cap is CONCURRENCY (C9): live roster-member windows, not spawn actions per
    day. Closing an idle main returns its slot immediately. Every branch below that
    cannot establish the live count refuses.
    """
    config = load_config()
    caps = config.get("caps") or {}
    cap, cap_reason = resolve_spawn_cap(caps)
    if cap is None:
        print(f"REFUSING: {cap_reason}", file=sys.stderr)
        return EX_MISCONFIG
    if cap <= 0:
        print(f"REFUSING: {cap_reason} is {cap}", file=sys.stderr)
        return EX_BLOCKED

    ids, live_reason = live_mains(config)
    if ids is None:
        # FAIL CLOSED. "I could not count" is not "nothing is running".
        print(f"REFUSING: cannot determine how many mains are live, so the concurrency cap "
              f"cannot be enforced: {live_reason}", file=sys.stderr)
        return EX_BLOCKED
    if args.agent in ids:
        print(f"REFUSING: {args.agent!r} is already live in the session. Spawning it again would "
              f"create a second window with the same name for one roster identity.",
              file=sys.stderr)
        return EX_BLOCKED
    if len(ids) >= cap:
        print(f"REFUSING: {len(ids)}/{cap} mains already live ({', '.join(sorted(ids))}). "
              f"This is a concurrency cap — close an idle main and the slot returns "
              f"immediately.", file=sys.stderr)
        return EX_BLOCKED
    used = len(ids)

    entry = roster_entry(config, args.agent)
    if not entry:
        print(f"REFUSING: {args.agent!r} has no roster row. Adding one is coordinator-agent's "
              f"decision, not this adapter's.", file=sys.stderr)
        return EX_BLOCKED

    # OPERATOR REQUIREMENT (2026-07-27): every spawned main is a WINDOW in the one
    # live session, never its own session. Throwaway sessions are a testing device
    # only. Three things enforce that, because convention is not enforcement:
    #   a) the endpoint must be a tmux endpoint — `monitor:file` previously derived
    #      the session name 'file' by splitting on ':', which is garbage;
    #   b) the derived session must equal tmux.live_session from config;
    #   c) that session must already EXIST — this adapter never calls new-session,
    #      and allow_session_creation is a declared `false` rather than an absence.
    tmux_cfg = config.get("tmux") or {}
    live = str(tmux_cfg.get("live_session") or "agent")
    ep = str(entry.get("endpoint") or "")
    if not ep.startswith("tmux:"):
        print(f"REFUSING: {args.agent!r} has endpoint {ep!r}, which is not a tmux endpoint. "
              f"A spawned main must live in the {live!r} session as a window.", file=sys.stderr)
        return EX_BLOCKED
    parts = ep.split(":")
    session = parts[1] if len(parts) > 1 and parts[1] else live
    if session != live:
        print(f"REFUSING: endpoint names session {session!r} but tmux.live_session is {live!r}. "
              f"All spawned mains belong in the one live session — separate sessions are for "
              f"tests only.", file=sys.stderr)
        return EX_BLOCKED
    rc_s, _ = _tmux("has-session", "-t", session)
    if rc_s != 0:
        creatable = bool(tmux_cfg.get("allow_session_creation"))
        print(f"REFUSING: session {session!r} does not exist"
              + ("." if creatable else " and allow_session_creation is false, so this adapter "
                 "will not create one. Start the session first."), file=sys.stderr)
        return EX_BLOCKED

    # C25 (2026-07-29): THE WINDOW NAME COMES FROM THE ENDPOINT, NOT FROM THE ROSTER ID.
    #
    # `new-window -n args.agent` created `agent:inference` while the roster endpoint
    # was `tmux:agent:codex-inference`, so `resolve_target` verified a window the
    # spawn had not created and returned None: EVERY spawned main whose endpoint names
    # a different window was undeliverable from birth. Worked around by hand at
    # 14:18Z with `tmux rename-window` — a manual step whose omission silently breaks
    # delivery, which is the same shape as C24 one layer over.
    #
    # This is also what removes drift trigger #1 for name endpoints (spawn and
    # endpoint can no longer disagree), and drift trigger #1 is what the C24
    # containment argument in this function depends on.
    #
    # An INDEX endpoint is REFUSED rather than guessed at. tmux assigns the index; a
    # spawn cannot promise the new window lands on the one the endpoint names, and
    # producing a window whose index does not match is precisely the undeliverable
    # state this fixes. Refusing is recoverable — the operator names the window in
    # the endpoint and re-runs. (See C32 for why an unverified index is worse still.)
    kind, value, ep_error = parse_endpoint_window(ep)
    if ep_error:
        print(f"REFUSING: {ep_error}", file=sys.stderr)
        return EX_MISCONFIG
    if kind == "index":
        print(f"REFUSING: endpoint {ep!r} names window INDEX {value!r}. tmux assigns indexes, so "
              f"this adapter cannot guarantee the new window lands on it, and a mismatch makes "
              f"the main undeliverable from birth. Name the window in the endpoint "
              f"(tmux:{session}:<name>) and re-run.", file=sys.stderr)
        return EX_MISCONFIG
    # No window component means `resolve_target` falls back to matching a window named
    # after the roster id, so that is exactly what the spawn must create.
    window = value if kind == "name" else args.agent

    if args.dry_run:
        would = [r for r in (f"inbox/{args.agent}.jsonl", f"outbox/{args.agent}.jsonl",
                             f"heartbeats/{args.agent}.json", f"cursors/{args.agent}.json")
                 if not (BUS_ROOT / r).exists()]
        print(f"would create {len(would)} bus file(s): {', '.join(would) or 'none (all present)'}")
        print(f"would create window {session}:{window} running: {args.command}")
        print("(--dry-run: nothing written, no window created)")
        return 0

    created = []
    for rel, seed in ((f"inbox/{args.agent}.jsonl", ""), (f"outbox/{args.agent}.jsonl", "")):
        p = BUS_ROOT / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
            created.append(rel)
    # C24 (2026-07-29): the HEARTBEAT is written unconditionally; the CURSOR is not.
    #
    # Seeding the heartbeat only-if-absent made every RE-spawned roster id inherit its
    # dead predecessor's heartbeat, so the new session was unreachable from birth:
    # cmd_nudge refuses on `state == working` and on age, and the fresh session cannot
    # clear either — it has not been told to drain, and it cannot be told, because the
    # telling is what the guard refuses. Measured post-reboot 2026-07-29: all three
    # pre-existing ids were undeliverable, `codex` on BOTH state and age (its heartbeat
    # still read `working` on a task whose session no longer existed). Same family as
    # C8/C18 — a main unreachable for want of a working liveness signal rather than a
    # delivery path; here the path resolves and the signal lies about it.
    #
    # WHY THIS IS SAFE — and this is NOT the argument the first version of this comment
    # made (corrected 2026-07-29 after independent review). It said: cmd_spawn refused
    # above when `args.agent in ids`, so reaching this line PROVES the id is not live;
    # then conceded "the proof is only as good as live_mains()". The concession is the
    # whole problem, because live_mains CAN UNDERCOUNT WITHOUT REFUSING. Demonstrated
    # against the real session: rename a window without updating config.yaml (drift
    # trigger #1) and a genuinely live main drops out of `ids` while live_mains returns
    # a SMALLER SET, not None. `args.agent in ids` then passes and this line resets a
    # live main's heartbeat. Naming live_mains as the dependency is therefore naming a
    # guarantee that does not exist.
    #
    # The reset is safe anyway, for a different reason. THIS is the invariant, and it
    # is the one that must not be weakened:
    #
    #     AN IDENTITY `live_mains` CANNOT SEE IS AN IDENTITY `resolve_target`
    #     CANNOT REACH.
    #
    # Their matching rules coincide. `tmux:s:<name>` resolves iff a window of that name
    # exists — which is also what live_mains counts; `tmux:s` with no window component
    # resolves iff a window named after the roster id exists — live_mains' other clause.
    # So resolve_target-success IMPLIES live_mains-counts-it, and by contraposition
    # undercount IMPLIES no nudge target. `not target` is itself a probe() blocker, so
    # the nudge cannot be delivered at all. The heartbeat is not the last line of
    # defence here; resolve_target is.
    #
    # The hazard is otherwise entirely real, which is why the containment matters: this
    # write sets state:idle with a fresh ts, clearing BOTH heartbeat blockers at once,
    # and on a DETACHED session — the normal overnight state — quiet_check is skipped
    # by design, leaving the heartbeat as the sole deciding guard. If a nudge could be
    # delivered it would land mid-generation.
    #
    # The invariant used to be EMERGENT: a coincidence of two independent
    # implementations, undocumented and untested, that anyone loosening resolve_target
    # would silently break. C32 was exactly that breach — index endpoints skipped
    # verification, so an id could be uncounted AND resolvable. It is now pinned by
    # test_c24_undercount_implies_resolve_target_refuses. If you add a fallback or a
    # best-effort match to resolve_target, that test is what will tell you.
    #
    # The cursor stays only-if-absent, deliberately: it is a read POSITION, not a
    # liveness claim. Resetting it to 0 would re-deliver every message the identity has
    # already processed, and a spawned session inheriting its predecessor's read
    # position is correct — that is how it picks up what it missed.
    hb_rel = f"heartbeats/{args.agent}.json"
    hb_path = BUS_ROOT / hb_rel
    hb_existed = hb_path.exists()
    hb_prior: dict | None = None
    if hb_existed:
        try:
            loaded = json.loads(hb_path.read_text(encoding="utf-8"))
            hb_prior = loaded if isinstance(loaded, dict) else {"unparseable": str(loaded)[:200]}
        except (OSError, json.JSONDecodeError) as exc:
            hb_prior = {"unreadable": str(exc)[:200]}
    hb_path.parent.mkdir(parents=True, exist_ok=True)
    hb_path.write_text(json.dumps(
        {"agent": args.agent, "state": "idle", "task_id": None, "ts": _now()},
        indent=2) + "\n", encoding="utf-8")
    created.append(hb_rel + (" (reset: stale predecessor)" if hb_existed else ""))
    if hb_existed:
        # C24 (2026-07-29): OVERWRITING A LIVENESS SIGNAL MUST LEAVE A TRACE.
        # The reset only announced itself on stdout, which nothing keeps — so the
        # single most consequential thing this command does, destroying the evidence
        # of what a previous session was doing, was the one thing the ledger did not
        # record. The prior VALUE is captured, not just the fact of the write: if the
        # containment argument above is ever wrong, this row is what shows a `working`
        # heartbeat on a real task was cleared, and by which spawn.
        #
        # Written HERE, not after new-window: the heartbeat is already gone by this
        # line, so a later failure must not be able to swallow the record of it.
        record("heartbeat-reset", args.agent,
               f"reset stale predecessor heartbeat at {hb_rel} before spawning",
               overwrote=hb_prior)

    for rel, payload in (
            (f"cursors/{args.agent}.json", {"agent": args.agent, "offset": 0, "ts": _now()}),):
        p = BUS_ROOT / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            created.append(rel)
    print(f"bus files ready ({len(created)} created: {', '.join(created) or 'all pre-existing'})")

    launch = args.command
    rc, out = _tmux("new-window", "-t", session, "-n", window, launch)
    if rc != 0:
        print(f"new-window failed: {out}", file=sys.stderr)
        return EX_MISCONFIG
    # C30(b) (2026-07-29): `new-window` exit 0 means TMUX ACCEPTED THE REQUEST, not that
    # anything is running in the window. A spawned `codex` pane died instantly and
    # silently because the CLI presented an update prompt on start; the window vanished,
    # cmd_spawn still reported success, and only a manual `tmux list-windows` revealed
    # it. Polarity: a false success is worse than a false failure HERE, because the four
    # bus files are already written, so the identity now looks provisioned-and-live to
    # everything downstream — including the C24 heartbeat reset and the concurrency cap.
    # So the window is re-checked after it has had a moment to die.
    time.sleep(SPAWN_SETTLE_S)
    rc_v, live_now = _tmux("list-windows", "-t", session, "-F", "#{window_name}")
    if rc_v == 0 and window not in live_now.split():
        record("spawn-died", args.agent,
               f"window {session}:{window} vanished within {SPAWN_SETTLE_S:.0f}s of creation",
               command=launch)
        print(f"REFUSING to report success: window {session}:{window} was created but is already "
              f"GONE {SPAWN_SETTLE_S:.0f}s later — the command exited immediately. Run it by hand "
              f"to see why (a CLI update prompt on start is the known cause). Command was: "
              f"{launch}", file=sys.stderr)
        print(f"NOTE: the four bus files for {args.agent!r} were already written and are LEFT IN "
              f"PLACE — they are correct and a retry reuses them. Nothing is draining them.",
              file=sys.stderr)
        return EX_BLOCKED
    record("spawn", args.agent, f"window {session}:{window} cmd={launch}")
    # VERIFY THE TARGET, do not trust it. The whole point of C25 is that a spawn which
    # believes it succeeded while the endpoint resolves elsewhere is silently
    # undeliverable; saying so here is the difference between a bad spawn and a bad
    # spawn nobody notices. Not fatal — the window and the bus files are real, and
    # killing them on a resolution miss would destroy a working session over a config
    # error the operator can fix in one line.
    target, why = resolve_target(config, args.agent)
    if target is None:
        print(f"WARNING: window {session}:{window} was created, but {args.agent!r} still does not "
              f"resolve: {why}. It will not receive nudges until this is fixed.", file=sys.stderr)
    print(f"spawned {args.agent} as window {session}:{window} ({used + 1}/{cap} mains live)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tmux_adapter.py", description=__doc__.split("\n")[0])
    p.add_argument("--quiet-s", type=float, default=20.0,
                   help="window must have produced no output for this long (default 20)")
    p.add_argument("--heartbeat-max-age", type=float, default=900.0)
    # C35. Top-level (not per-subcommand) so `probe` and `nudge` are evaluated
    # against the SAME threshold — a probe that answered a different question
    # from the nudge it precedes would be worse than no probe at all.
    p.add_argument("--heartbeat-override-quiet-s", type=float,
                   default=DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S,
                   help="a `working` heartbeat is overridden once the window has been quiet "
                        f"this long (default {DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S:.0f}); both "
                        "TUIs redraw every second while generating, so this means 'settled at "
                        "its prompt'. 0 or less disables the override entirely.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probe", help="report every guard signal; act on nothing")
    pr.add_argument("--agent", required=True)
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_probe)

    nu = sub.add_parser("nudge", help="send-keys into the agent's pane, guarded — DEPRECATED: "
                        "payload nudges are deprecated — bus carries payload, doorbell rings "
                        "(see the 'doorbell' subcommand and the C45 block in this file)")
    nu.add_argument("--agent", required=True)
    nu.add_argument("--message", required=True)
    nu.add_argument("--min-interval-s", type=float, default=600.0, help="rate limit (default 600)")
    nu.add_argument("--settle-s", type=float, default=DEFAULT_NUDGE_SETTLE_S,
                    help="delay before each prompt-tail submission check")
    nu.add_argument("--dry-run", action="store_true")
    nu.set_defaults(func=cmd_nudge)

    db = sub.add_parser("doorbell", help="ring a FIXED, content-free string into the agent's "
                        "pane — no --message: the bus carries payload, this only says 'go "
                        "drain it'. Two guards only (pane alive, composer empty); see C45.")
    db.add_argument("--agent", required=True)
    db.add_argument("--dry-run", action="store_true")
    db.set_defaults(func=cmd_doorbell)

    pn = sub.add_parser("pending", help="C51 DETECTOR: which panes hold queued-but-"
                        "unsubmitted composer input. Read-only — it never sends a key. "
                        "Exit 0 only when every roster pane was read and all are clear; "
                        "2 = pending input found, 3 = a pane could not be evaluated.")
    pn.add_argument("--agent", action="append", default=[],
                    help="restrict to this roster id (repeatable); default is every row")
    pn.add_argument("--json", action="store_true")
    pn.set_defaults(func=cmd_pending)

    # C54: the detector's other half. TWO verbs, because discarding pending text and
    # accepting it as an instruction are opposite decisions and only the caller knows
    # which is right — see the C54 block for the three live panes that proved it.
    for verb, helptext, func in (
            ("clear", "DISCARD a pane's pending composer input with Ctrl-U (never Ctrl-C) "
                      "and verify the composer is empty afterwards. The discarded text is "
                      "logged verbatim to the adapter ledger.", cmd_clear),
            ("submit", "ACCEPT a pane's pending composer input by sending Enter, and verify "
                       "the buffer was consumed. Use when the pending text is the instruction "
                       "you want that main to act on.", cmd_submit)):
        sp_ = sub.add_parser(verb, help=helptext)
        sp_.add_argument("--agent", required=True)
        sp_.add_argument("--expect", default=None,
                         help="the text you believe is pending. REFUSES if the pane holds "
                              "anything else, so a composer that changed between your read and "
                              "this call cannot be acted on by mistake. Prefer this to --force.")
        sp_.add_argument("--force", action="store_true",
                         help="act on whatever is pending without naming it. One of --expect "
                              "or --force is required: acting on someone's typed words must "
                              "never happen by omission.")
        sp_.add_argument("--dry-run", action="store_true")
        sp_.set_defaults(func=func)

    sp = sub.add_parser("spawn", help="create the agent's bus files, then its pane")
    sp.add_argument("--agent", required=True)
    sp.add_argument("--command", default="cd /workspace && claude")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_spawn)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""tmux_adapter.py — nudge and spawn agent mains in tmux (M5, grant-gated).

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md (M5)
Gate:           OP-SENDKEYS-CODEX — granted by the operator 2026-07-27
Caps:           flags.codex_sendkeys, caps.max_spawns_per_day (operator set 3)

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

Usage:
    tmux_adapter.py probe  --agent codex                 # all guard signals, no action
    tmux_adapter.py nudge  --agent codex --message "..."  # send-keys, guarded
    tmux_adapter.py spawn  --agent new-main               # 4 bus files, then a pane
"""

from __future__ import annotations

import argparse
import json
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
# Bounded polls, so a slow redraw is a wait rather than a false refusal.
_VERIFY_TIMEOUT_S = 2.0
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
# `@` anywhere (not just leading) opens Codex's file picker at the typed token.
_INLINE_PICKER_TRIGGER = "@"
# How far back from the cursor a paste banner can sit on the composer line.
_BLOB_LOOKBACK_CHARS = 200
_FRAGMENT_CHARS = 60


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


def _submission_state(composer_text: str, fragment: str) -> str:
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
        return "text_echoed"
    return "text_absent"


def _await_state(target: str, fragment: str, wanted: set[str], timeout_s: float,
                 stable_samples: int = 1) -> tuple[str | None, str | None]:
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
        state = _submission_state(composer or "", fragment)
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
        rc, got = _tmux("display-message", "-p", "-t", f"{session}:{want}", "#{window_name}")
        if rc != 0:
            return None, f"target {session}:{want} does not resolve: {got}"
        if got.strip() != want and not want.isdigit():
            return None, (f"target {session}:{want!r} resolved to window {got.strip()!r} — tmux "
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


def record(kind: str, agent: str, detail: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), "kind": kind, "agent": agent,
                             "detail": detail}, sort_keys=True) + "\n")


def probe(config: dict, agent: str, quiet_s: float, hb_max_age: float) -> dict:
    """Every guard signal, with an explicit blocker list. Pure — acts on nothing."""
    flags, caps = config.get("flags") or {}, config.get("caps") or {}
    authorised = str(flags.get("codex_sendkeys")).strip().lower() in {"1", "true", "yes", "on"}
    spawn_cap = int(caps.get("max_spawns_per_day") or 0)

    target, why = resolve_target(config, agent)
    hb, hb_age = heartbeat(agent)

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
    spawns_today = sum(1 for r in rows if r.get("kind") == "spawn" and r.get("ts", "").startswith(today))
    last_nudge = max((r["ts"] for r in rows if r.get("kind") == "nudge" and r.get("agent") == agent),
                     default=None)
    since_nudge = None
    if last_nudge:
        try:
            since_nudge = max(0.0, time.time() - datetime.fromisoformat(last_nudge).timestamp())
        except ValueError:
            since_nudge = None

    blockers: list[str] = []
    if not authorised:
        blockers.append("flags.codex_sendkeys is off (gate OP-SENDKEYS-CODEX)")
    if not target:
        blockers.append(why)
    if dead is True:
        blockers.append("pane is dead")
    if dead is None and target:
        blockers.append("could not read pane state — fail closed")
    # window_activity only reflects OUTPUT while a client is attached. Measured
    # 2026-07-27 on a detached session: a window printing every second and one
    # sleeping reported the SAME timestamp, so quiet_for only ever grows and the
    # check silently always passes — fail-OPEN in a module that must fail closed.
    # So it is a corroborating signal that counts only when trustworthy, and the
    # heartbeat is the guard that actually decides.
    quiet_check = "n/a"
    if not target:
        pass
    elif attached is False:
        # NOT a blocker. A detached session is the normal overnight state — the
        # whole point of this system is coordinating while the operator is away —
        # so refusing every nudge when detached would defeat it. The quiet-check
        # simply cannot be evaluated, so it contributes nothing either way, and the
        # heartbeat is the guard that decides (as this module claims). If an agent
        # reports `idle` while generating, that is an agent defect and the fix
        # belongs in its heartbeat discipline, not in a signal tmux cannot give us.
        quiet_check = "skipped: session detached, window_activity does not track output"
    elif quiet_for is None:
        blockers.append("could not read window_activity — fail closed")
    elif quiet_for < quiet_s:
        quiet_check = f"blocked: output {quiet_for:.0f}s ago"
        blockers.append(f"window produced output {quiet_for:.0f}s ago (< {quiet_s:.0f}s) — "
                        f"likely mid-generation")
    else:
        quiet_check = f"passed: quiet for {quiet_for:.0f}s"
    if hb is None:
        blockers.append("no heartbeat — cannot tell if the agent is thinking; fail closed")
    else:
        if str(hb.get("state")) == "working":
            blockers.append(f"heartbeat says working (task {hb.get('task_id')})")
        if hb_age is not None and hb_age > hb_max_age:
            blockers.append(f"heartbeat is {hb_age:.0f}s stale (> {hb_max_age:.0f}s)")

    return {"agent": agent, "target": target, "target_reason": why,
            "authorised": authorised, "spawn_cap": spawn_cap, "spawns_today": spawns_today,
            "pane_dead": dead, "window_quiet_for_s": quiet_for,
            "session_attached": attached, "quiet_check": quiet_check,
            "heartbeat_state": (hb or {}).get("state"), "heartbeat_age_s": hb_age,
            "seconds_since_last_nudge": since_nudge,
            "submission_verification": "cursor-anchored composer check before Enter, transcript "
                                       "echo required after it; may fail closed",
            "blockers": blockers, "nudge_ok": not blockers}


def cmd_probe(args: argparse.Namespace) -> int:
    p = probe(load_config(), args.agent, args.quiet_s, args.heartbeat_max_age)
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
    print(f"heartbeat        {p['heartbeat_state']} (age {age:.0f}s)" if age is not None
          else "heartbeat        (none)")
    print(f"spawns today     {p['spawns_today']}/{p['spawn_cap']}")
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
    if stripped.startswith(_COMPOSER_MODE_PREFIXES) or _INLINE_PICKER_TRIGGER in args.message:
        print(f"REFUSING: nudge message starts with one of {' '.join(_COMPOSER_MODE_PREFIXES)} "
              f"or contains '{_INLINE_PICKER_TRIGGER}'. Those put the composer in a mode where "
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
    p = probe(config, args.agent, args.quiet_s, args.heartbeat_max_age)
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
    # C6: message and Enter MUST be separate calls. A single send-keys call can
    # leave the text in a Codex prompt while tmux still returns success.
    rc, out = _send_message_chunked(p["target"], args.message)
    if rc != 0:
        print(f"send-keys message failed: {out}", file=sys.stderr)
        return EX_MISCONFIG
    settle_s = max(0.0, float(getattr(args, "settle_s", DEFAULT_NUDGE_SETTLE_S)))
    time.sleep(settle_s)
    fragment = _pending_fragment(args.message)
    # BEFORE Enter the composer must END with the message. Wait for it rather
    # than sampling once: a long chunked message can still be rendering.
    pending_state, failure = _await_state(p["target"], fragment, {"text_present"},
                                          _VERIFY_TIMEOUT_S)
    if failure:
        print(f"nudge submission verification unavailable before Enter: {failure}", file=sys.stderr)
        return EX_MISCONFIG
    if pending_state == "paste_blob":
        print("nudge message was mangled into a paste blob before Enter; refusing. "
              "The composer holds a paste attachment, not editable text — its content is "
              "truncated at 1024 chars and cannot be verified.", file=sys.stderr)
        return EX_MISCONFIG
    if pending_state != "text_present":
        print("nudge message did not land in the composer before Enter; refusing. "
              "The cursor is not at the end of the message, so the pane is not accepting "
              "typed input (a full-screen modal, e.g. Codex backtrack mode, does this).",
              file=sys.stderr)
        return EX_MISCONFIG

    rc, out = _tmux("send-keys", "-t", p["target"], "Enter")
    if rc != 0:
        print(f"send-keys Enter failed: {out}", file=sys.stderr)
        return EX_MISCONFIG
    time.sleep(settle_s)
    # AFTER Enter the message must have MOVED: off the cursor, but still on the
    # pane as the transcript echo. Note this is NOT "the message is gone from the
    # pane" — both TUIs echo the submitted text above, and treating that as
    # failure is exactly the false negative this fix removes. Nor is it merely
    # "no longer at the cursor": that would accept an Enter which a completion
    # overlay consumed to rewrite the composer. Success is the echo, positively.
    submitted_state, failure = _await_state(p["target"], fragment, {"text_echoed"},
                                            _VERIFY_TIMEOUT_S, _VERIFY_STABLE_SAMPLES)
    if failure:
        print(f"nudge submission verification unavailable after Enter: {failure}", file=sys.stderr)
        return EX_MISCONFIG
    if submitted_state == "text_present":
        print("nudge submission not confirmed after Enter: text present but unsubmitted "
              "(the composer still ends with the message, so the TUI swallowed Enter)",
              file=sys.stderr)
        return EX_MISCONFIG
    if submitted_state == "paste_blob":
        print("nudge submission not confirmed after Enter: the composer holds a paste blob",
              file=sys.stderr)
        return EX_MISCONFIG
    if submitted_state != "text_echoed":
        print("nudge submission not confirmed after Enter: the message is no longer at the "
              "cursor but is not echoed on the pane either. Enter was consumed by something "
              "that rewrote the composer (a completion picker, e.g. Codex '@' or a '/' menu) "
              "rather than submitting. Refusing to record a nudge that may not have been sent.",
              file=sys.stderr)
        return EX_MISCONFIG
    record("nudge", args.agent, args.message[:200])
    print(f"nudged {args.agent} at {p['target']}")
    return 0


def cmd_spawn(args: argparse.Namespace) -> int:
    """Create the agent's four bus files, THEN start its pane.

    Order is the whole point. A main whose inbox/outbox/heartbeat/cursor do not
    exist yet comes up with nowhere to write, and its first drain fails. The roster
    row must already exist: deciding that a new main SHOULD exist is judgment, and
    judgment belongs to coordinator-agent, not here.
    """
    config = load_config()
    caps = config.get("caps") or {}
    cap = int(caps.get("max_spawns_per_day") or 0)
    today = datetime.now(timezone.utc).date().isoformat()
    used = sum(1 for r in ledger_rows()
               if r.get("kind") == "spawn" and r.get("ts", "").startswith(today))
    if cap <= 0:
        print(f"REFUSING: caps.max_spawns_per_day is {cap}", file=sys.stderr)
        return EX_BLOCKED
    if used >= cap:
        print(f"REFUSING: {used}/{cap} spawns already used today", file=sys.stderr)
        return EX_BLOCKED

    target, why = resolve_target(config, args.agent)
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

    if args.dry_run:
        would = [r for r in (f"inbox/{args.agent}.jsonl", f"outbox/{args.agent}.jsonl",
                             f"heartbeats/{args.agent}.json", f"cursors/{args.agent}.json")
                 if not (BUS_ROOT / r).exists()]
        print(f"would create {len(would)} bus file(s): {', '.join(would) or 'none (all present)'}")
        print(f"would create window {session}:{args.agent} running: {args.command}")
        print("(--dry-run: nothing written, no window created)")
        return 0

    created = []
    for rel, seed in ((f"inbox/{args.agent}.jsonl", ""), (f"outbox/{args.agent}.jsonl", "")):
        p = BUS_ROOT / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
            created.append(rel)
    for rel, payload in (
            (f"heartbeats/{args.agent}.json",
             {"agent": args.agent, "state": "idle", "task_id": None, "ts": _now()}),
            (f"cursors/{args.agent}.json", {"agent": args.agent, "offset": 0, "ts": _now()})):
        p = BUS_ROOT / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            created.append(rel)
    print(f"bus files ready ({len(created)} created: {', '.join(created) or 'all pre-existing'})")

    launch = args.command
    rc, out = _tmux("new-window", "-t", session, "-n", args.agent, launch)
    if rc != 0:
        print(f"new-window failed: {out}", file=sys.stderr)
        return EX_MISCONFIG
    record("spawn", args.agent, f"window {session}:{args.agent} cmd={launch}")
    print(f"spawned {args.agent} as window {session}:{args.agent} ({used + 1}/{cap} today)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tmux_adapter.py", description=__doc__.split("\n")[0])
    p.add_argument("--quiet-s", type=float, default=20.0,
                   help="window must have produced no output for this long (default 20)")
    p.add_argument("--heartbeat-max-age", type=float, default=900.0)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probe", help="report every guard signal; act on nothing")
    pr.add_argument("--agent", required=True)
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_probe)

    nu = sub.add_parser("nudge", help="send-keys into the agent's pane, guarded")
    nu.add_argument("--agent", required=True)
    nu.add_argument("--message", required=True)
    nu.add_argument("--min-interval-s", type=float, default=600.0, help="rate limit (default 600)")
    nu.add_argument("--settle-s", type=float, default=DEFAULT_NUDGE_SETTLE_S,
                    help="delay before each prompt-tail submission check")
    nu.add_argument("--dry-run", action="store_true")
    nu.set_defaults(func=cmd_nudge)

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

#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""composer_repair.py — QUARANTINED. The pane-composer detector and repair verbs.

    python3 scripts/coordination/_retired/composer_repair.py pending
    python3 scripts/coordination/_retired/composer_repair.py clear  --agent <id> --expect '<text>'
    python3 scripts/coordination/_retired/composer_repair.py submit --agent <id> --expect '<text>'

WHY THIS IS NOT IN `tmux_adapter.py` ANY MORE (P3-2, Loop-Owned Fleet, 2026-08-16).

These three verbs — `pending`, `clear`, `submit` — were `tmux_adapter.py`
subcommands. They were built (C51, C54, C55) for a fleet of five interactive
Claude/Codex mains whose composers routinely held queued-but-unsubmitted text
that only a machine sweep would ever find. That fleet no longer exists:

  * mainA-D are tombstoned roster rows (P3-1) and `auditor`'s interactive
    session is retired (P3-7). The only interactive endpoints left are
    `inference` and `coordinator-agent`, both of which the operator sits in
    front of.
  * Pool workers DO run in visible tmux panes (`wpool-lane0..3`), but under D8
    those panes are HUMAN-ONLY: the machine never types into them and never
    reads pane text to make a decision. Their completion signal is a
    schema-valid report file, never a composer state.

So the machine no longer has a fleet of composers to sweep, and it no longer
has authority to press keys into the panes that remain. `clear` and `submit`
are the machine MUTATING a pane to repair it; `pending` is the fleet-wide sweep
that fed them. Neither has had a live caller since they were written — verified
2026-08-16 across `scripts/`, `.claude/`, hooks, tests and docs: the only
non-test references are historical failure records and this module's own
hint strings.

QUARANTINED, NOT DELETED, and the distinction is the point. The C54 incident is
not hypothetical — three mains parked at composers holding never-submitted
instructions, sixteen continuous minutes of idle compute, and the coordinator
denied `tmux send-keys` by the permission classifier so a human had to press
Ctrl-U per pane. If interactive-session volume ever returns (PN-1), this is the
remedy, already measured and already guarded, rather than something someone
re-derives under pressure. It stays runnable by hand and stays tested.

WHAT IS DELIBERATELY *NOT* HERE: the shared read substrate. `_read_composer_row`,
`_composer_row_is_empty`, the `_BARE_PROMPT_GLYPHS` table, `_press_key_with_wake`
and the C51 submission-verification chain all stay in `tmux_adapter.py`, because
`nudge` and `doorbell` — still live for the two interactive endpoints — need
them. This module imports them by name; it owns no second copy of any
calibration.

The incident narratives below are preserved verbatim from `tmux_adapter.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ADAPTER_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(_ADAPTER_DIR))

# Imported BY NAME, not through a module handle, so the existing tests'
# `monkeypatch.setattr(m, "_read_composer_row", ...)` seams keep working against
# this module exactly as they did against the adapter.
from tmux_adapter import (  # noqa: E402
    EX_BLOCKED, EX_MISCONFIG, EX_USAGE,
    _VERIFY_POLL_S, _VERIFY_STABLE_SAMPLES, _VERIFY_TIMEOUT_S,
    _composer_row_is_empty, _normalise, _now, _press_key_with_wake,
    _read_composer_row, _tmux, composer_faint_is_placeholder, heartbeat,
    load_config, record, resolve_target,
)


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
      ``no-pane``    the row has no tmux endpoint at all (``monitor:file``,
                     ``exec:``, ``retired:``). Not a defect and not counted
                     against the fleet: there is no composer.
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
              f"read and this call; run `composer_repair.py pending` again.", file=sys.stderr)
        return EX_BLOCKED

    # ---- the acknowledgement gate ----
    if args.expect is not None:
        if _normalise(args.expect) not in _normalise(pending):
            print(f"REFUSING: --expect does not match what the pane actually holds.\n"
                  f"  expected : {args.expect!r}\n"
                  f"  pane has : {pending!r}\n"
                  f"The composer changed between your read and this call — somebody may be "
                  f"typing. Re-read it with `composer_repair.py pending --agent {args.agent}` "
                  f"and decide again.", file=sys.stderr)
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

    # C55: a Claude composer holding queued text ignores a BARE keystroke, so the
    # wake character is not cosmetic — without it `submit` and `clear` cannot succeed
    # at all. They failed HONESTLY before this (the post-action re-read caught it every
    # time and never claimed success), which is why nothing was lost — but an operator
    # was left pressing keys by hand for an hour because the tool could only report its
    # own failure. NEVER C-c — see the C54 block. The measurement, the choice of a
    # SPACE, and the honest caveat about a failed press leaving `text + " "` behind all
    # live at `_press_key_with_wake`, which H-2 also put on the rollback path.
    #
    # H-1 IS HALF CLOSED, AND THE OPEN HALF IS DISCARD. `submit` is live-verified.
    # `clear` sends `space` + `C-u`, which is the best available candidate and is NOT
    # a measured one — bare `C-u` and a 100-iteration `BSpace` loop were both measured
    # as no-ops, and `Escape` (the other candidate) is UNTESTED and hazardous to fire
    # blind: one Escape interrupts a running turn and two open the rewind picker. So
    # nothing is implemented here on a guess; `clear` keeps failing HONESTLY when the
    # key does not take (`_await_composer_empty` above refuses to report success it
    # cannot see), and the way to close this is to MEASURE first:
    #
    #     scripts/coordination/verify_composer_keys.sh
    #
    # — a disposable `claude` TUI in a scratch tmux session (it refuses to run against
    # the live session or any roster endpoint), sacrificial text, the three candidates
    # in order, re-read after each through the adapter's own `_read_composer_row`.
    # Implement whichever it reports CLEARED; if none, discard stays unimplemented.
    key = "C-u" if verb == "clear" else "Enter"
    rc, detail = _press_key_with_wake(target, key)
    if rc != 0:
        print(detail, file=sys.stderr)
        return EX_MISCONFIG

    empty, observed, failure = _await_composer_empty(target, _VERIFY_TIMEOUT_S,
                                                     faint_is_placeholder=faint_ok)
    if failure:
        print(f"{verb} NOT confirmed for {args.agent} at {target}: the composer could not be "
              f"re-read after {key} ({failure}). The keystroke was sent; whether it took is "
              f"UNKNOWN. Re-run `composer_repair.py pending --agent {args.agent}`.",
              file=sys.stderr)
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="composer_repair.py",
                                description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("pending", help="C51 DETECTOR: which panes hold queued-but-"
                                        "unsubmitted composer input. Read-only — it never "
                                        "sends a key. Exit 0 only when every roster pane was "
                                        "read and all are clear; 2 = pending input found, "
                                        "3 = a pane could not be evaluated.")
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

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

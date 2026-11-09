#!/usr/bin/env python3
"""codex_pane_liveness.py - tmux Codex liveness + guarded nudge for the churn windows (LOOP-38).

Replaces the manual `tmux send-keys` ws58 used on the idle "Goal stalled" sessions (agent:2 NI,
agent:3 refactor, agent:4 codex3) and the channel-file nudges. Detection follows
agents/shared/SESSION_LIFECYCLE.md "Reading another session's liveness - three states, not two":

    working     the runtime is mid-turn AND the pane shows its generation marker
    compacting  the runtime is mid-turn but the pane shows NO marker (a compacting session renders
                like a finished one), or the pane says "compacting"
    idle        the runtime's rollout ends in a turn-terminal record (task_complete/turn_aborted)
                AND the pane shows no busy marker on N consecutive reads
    unknown     the runtime is unreadable. NEVER idle: pane text alone can not clear a session.

The runtime read is tmux_adapter.codex_runtime_state (the session's own user-thread rollout, with its
subagent-fd and absent-thread_source guards). Corroboration outranks contradiction: any positive busy
signal beats an idle one. "Goal stalled" on the pane is reported as a flag, never as evidence of idle.

    codex_pane_liveness.py status [--session agent]              # read-only, every window
    codex_pane_liveness.py nudge --window agent:2 --text "..."   # dry-run unless --send
    codex_pane_liveness.py nudge --window agent:2 --text "..." --send

nudge types ONLY when (1) the window is a Codex window of the live session, (2) the state is `idle` on two
probes --gap-s apart (two-sample persistence), (3) the composer row is empty. It verifies the composer
returned to empty after Enter and rolls its own text back with Ctrl-U (never Ctrl-C) otherwise. Anything
unreadable refuses. The default is a dry run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WORKING, COMPACTING, IDLE, UNKNOWN = "working", "compacting", "idle", "unknown"
BUSY_MARKER = "esc to interrupt"
COMPACT_MARKER = "compacting"
STALLED_MARKER = "goal stalled"
IDLE_SAMPLES = 3
IDLE_POLL_S = 0.4
DEFAULT_SESSION = "agent"
MAX_TEXT = 1200


def _adapter():
    import tmux_adapter  # lazy: it reads the bus config at import time
    return tmux_adapter


def list_windows(session: str, tmux_fn=None) -> tuple[list[dict] | None, str]:
    tmux = tmux_fn or _adapter()._tmux
    rc, out = tmux("list-windows", "-t", session, "-F", "#{window_index}\t#{window_name}\t#{pane_pid}\t#{pane_dead}")
    if rc != 0:
        return None, f"cannot list windows of {session!r}: {out[:200]}"
    wins = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) == 4 and p[2].strip().isdigit():
            wins.append({"index": p[0].strip(), "name": p[1].strip(), "pane_pid": int(p[2]),
                         "dead": p[3].strip() == "1", "target": f"{session}:{p[0].strip()}"})
    return wins, ""


def codex_runtime(pane_pid: int) -> tuple[str | None, str]:
    """('idle'|'active'|None, why) over the codex process under the pane; None is UNAVAILABLE."""
    ad = _adapter()
    last = "no codex process under the pane"
    for p in ad._proc_descendants(pane_pid):
        exe, argv0 = ad._proc_names(p)
        if "codex" in (exe, argv0):
            state, why = ad.codex_runtime_state(p)
            if state is not None:
                return state, f"codex rollout (pid {p}): {why}"
            last = why
    return None, last


def classify(runtime: str | None, runtime_why: str, pane_reads: list[str | None]) -> dict:
    """Pure three-state decision. pane_reads: successive lowercase pane captures (None = unreadable)."""
    readable = [r for r in pane_reads if r is not None]
    busy = any(BUSY_MARKER in r for r in readable)
    compacting_text = any(COMPACT_MARKER in r for r in readable)
    stalled = bool(readable) and all(STALLED_MARKER in r for r in readable)
    base = {"runtime": runtime, "why": runtime_why, "goal_stalled_on_pane": stalled}
    if compacting_text:
        return {**base, "state": COMPACTING, "reason": "pane shows 'compacting'"}
    if runtime == "active":
        if busy:
            return {**base, "state": WORKING, "reason": "runtime mid-turn and pane shows its generation marker"}
        return {**base, "state": COMPACTING, "reason": "runtime mid-turn but the pane shows no marker "
                "(compacting renders like a finished session); treat as alive"}
    if busy:      # corroboration outranks contradiction
        return {**base, "state": WORKING, "reason": "pane shows its generation marker although the runtime reads idle"}
    if runtime == "idle":
        if len(readable) < len(pane_reads) or len(readable) < 1:
            return {**base, "state": UNKNOWN, "reason": "runtime idle but the pane was unreadable on a sample"}
        return {**base, "state": IDLE, "reason": f"runtime turn-terminal and no busy marker on {len(readable)} reads"}
    return {**base, "state": UNKNOWN, "reason": "runtime unreadable; pane text alone never clears a session"}


def probe_window(win: dict, *, runtime_fn=codex_runtime, pane_fn=None, samples: int = IDLE_SAMPLES,
                 poll_s: float = IDLE_POLL_S, sleep=time.sleep) -> dict:
    if win.get("dead"):
        return {"state": UNKNOWN, "reason": "pane is dead", "runtime": None, "why": "", "goal_stalled_on_pane": False}
    tmux = _adapter()._tmux
    pane_fn = pane_fn or (lambda t: (lambda rc, out: (out or "").lower() if rc == 0 else None)(*tmux("capture-pane", "-p", "-t", t)))
    runtime, why = runtime_fn(win["pane_pid"])
    reads = []
    for i in range(max(1, samples)):
        if i:
            sleep(poll_s)
        reads.append(pane_fn(win["target"]))
    return classify(runtime, why, reads)


def status(session: str = DEFAULT_SESSION, **kw) -> tuple[list[dict] | None, str]:
    wins, err = list_windows(session, kw.pop("tmux_fn", None))
    if wins is None:
        return None, err
    return [{**w, **probe_window(w, **kw)} for w in wins], ""


def nudge(window: str, text: str, *, session: str = DEFAULT_SESSION, send: bool = False, gap_s: float = 2.0,
          tmux_fn=None, runtime_fn=codex_runtime, pane_fn=None, composer_fn=None, send_fn=None,
          sleep=time.sleep, samples: int = IDLE_SAMPLES, poll_s: float = IDLE_POLL_S) -> tuple[int, str]:
    """(rc, message). rc 0 sent (or dry-run would send), 2 refused. Never types unless every guard holds."""
    ad = _adapter()
    if not text or len(text) > MAX_TEXT or "\n" in text or "\r" in text:
        return 2, f"REFUSED: text must be one line of 1..{MAX_TEXT} chars"
    wins, err = list_windows(session, tmux_fn)
    if wins is None:
        return 2, f"REFUSED: {err}"
    hits = [w for w in wins if window in (w["target"], w["index"], w["name"])]
    if len(hits) != 1:
        return 2, f"REFUSED: window {window!r} matched {len(hits)} windows in {session!r}; never guess a pane"
    win = hits[0]
    probes = []
    for i in range(2):                      # two samples to act
        if i:
            sleep(gap_s)
        probes.append(probe_window(win, runtime_fn=runtime_fn, pane_fn=pane_fn, samples=samples,
                                   poll_s=poll_s, sleep=sleep))
        if probes[-1]["state"] != IDLE:
            return 2, (f"REFUSED: {win['target']} is {probes[-1]['state']} ({probes[-1]['reason']}); "
                       f"a nudge is only for a runtime-proven idle session")
    composer_fn = composer_fn or (lambda t: ad._read_composer_row(t))
    row, failure = composer_fn(win["target"])
    if row is None or not ad._composer_row_is_empty(row):
        return 2, f"REFUSED: composer not provably empty ({failure or row!r})"
    if not send:
        return 0, f"DRY-RUN: {win['target']} ({win['name']}) idle on 2 probes, composer empty; would type {len(text)} chars + Enter"
    tmux = tmux_fn or ad._tmux
    send_fn = send_fn or ad._send_message_chunked
    rc, out = send_fn(win["target"], text)
    if rc != 0:
        cleared, detail = ad._clear_own_pending(win["target"], row)
        return 2, f"FAILED typing into {win['target']}: {out}; rollback {'ok' if cleared else 'NOT proven'}: {detail}"
    rc, out = tmux("send-keys", "-t", win["target"], "Enter")
    ok, observed, failure = ad._await_composer_consumed(win["target"], row, 6.0)
    if rc != 0 or not ok:
        cleared, detail = ad._clear_own_pending(win["target"], row)
        return 2, (f"UNDELIVERED to {win['target']} (composer {failure or observed!r}); "
                   f"rollback {'ok' if cleared else 'NOT proven'}: {detail}")
    return 0, f"SENT to {win['target']} ({win['name']}): composer returned to empty after Enter"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--session", default=DEFAULT_SESSION)
    s.add_argument("--json", action="store_true")
    n = sub.add_parser("nudge")
    n.add_argument("--window", required=True)
    n.add_argument("--text", required=True)
    n.add_argument("--session", default=DEFAULT_SESSION)
    n.add_argument("--gap-s", type=float, default=2.0)
    n.add_argument("--send", action="store_true", help="actually type; default is a dry run")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        rows, err = status(a.session)
        if rows is None:
            print(err, file=sys.stderr)
            return 2
        if a.json:
            print(json.dumps(rows, indent=2))
        for r in rows:
            if not a.json:
                print(f"{r['target']}\t{r['name']}\t{r['state']}\t{'GOAL-STALLED ' if r['goal_stalled_on_pane'] else ''}{r['reason']}")
        return 0
    rc, msg = nudge(a.window, a.text, session=a.session, send=a.send, gap_s=a.gap_s)
    print(msg, file=sys.stderr if rc else sys.stdout)
    return rc


if __name__ == "__main__":
    sys.exit(main())

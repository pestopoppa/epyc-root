#!/usr/bin/env python3
"""Scan a Bash command for `pkill`/`pgrep` invoked against a NAME PATTERN.

INC-20260812 (a coordinator subagent ran `pkill -f` on a name pattern to clean up
its own background waiter) and INC-20260731 before it, which is why the rule exists:
this is a SHARED HOST, so any name pattern is a wildcard over other sessions'
processes. Measured then: `llama-server -m` killed another agent's server twice, and
`earlyoom` died because its own command line contains `--ignore ^(llama-server|sd-server)$`
— a guard process's argv necessarily contains the names it guards.

SCOPED TO INVOCATIONS, NOT TEXT — the lesson C21 already paid for in
`pytest_worker_scan.py`, whose `strip_quoted`/`strip_heredocs` this reuses rather
than reimplementing. The guard must not block the bus message REPORTING a pkill
incident, the CLAUDE.md rule that forbids it, or this docstring. Quoted text is data;
a heredoc is data; only an unquoted command word counts.

Verdicts: `kill-pattern`, `grep-pattern`, `clean`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pytest_worker_scan import _SEPARATORS, strip_heredocs, strip_quoted  # noqa: E402

# Command word, optionally path-qualified, optionally behind a runner prefix.
_TARGET = re.compile(r"(?:^|[\s/])(pkill|pgrep)\b")
# PID/session-scoped selectors are safe: they name a process, not a pattern.
# -P parent pid, -s session id, -g pgrp, -t terminal. A bare numeric operand after
# these is not a name pattern.
_PID_SCOPED = re.compile(r"(?:^|\s)-[Psgt](?:[\s=]*)[0-9]+\b")
# Anything that is not a flag and not consumed by a PID selector is an operand,
# i.e. the pattern. `-f` makes it match the full argv, which is strictly worse.
_OPERAND = re.compile(r"(?:^|\s)(?!-)[^\s]+")


def _verdict_for_segment(seg: str) -> str | None:
    m = _TARGET.search(seg)
    if not m:
        return None
    tool = m.group(1)
    rest = seg[m.end():]
    # Strip the flags we understand, then see whether a bare operand survives.
    stripped = _PID_SCOPED.sub(" ", rest)
    stripped = re.sub(r"(?:^|\s)-[A-Za-z-]+", " ", stripped)
    has_operand = bool(_OPERAND.search(stripped))
    pid_scoped = bool(_PID_SCOPED.search(rest))
    if pid_scoped and not has_operand:
        return None                      # `pgrep -P 1234` — names a process, not a pattern
    if not has_operand and "-f" not in rest:
        return None                      # degenerate/incomplete; nothing to match on
    return "kill-pattern" if tool == "pkill" else "grep-pattern"


def pattern_kill_verdict(command: str) -> str:
    """`kill-pattern` | `grep-pattern` | `clean` for a whole Bash command string."""
    text = strip_quoted(strip_heredocs(command))
    worst = None
    for seg in _SEPARATORS.split(text):
        v = _verdict_for_segment(seg)
        if v == "kill-pattern":
            return v                     # killing outranks grepping
        if v == "grep-pattern":
            worst = v
    return worst or "clean"


def main() -> int:
    print(pattern_kill_verdict(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

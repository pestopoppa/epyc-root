#!/usr/bin/env python3
"""D9 at COMMIT time — the gate a direct commit was walking around.

WHY THIS EXISTS. D9, as the operator ratified it on 2026-08-15: *merging any
change under `scripts/coordination/**` requires operator ack.* That was
implemented in `promote_lane.py`, which refuses such a promotion with exit 5
unless `--operator-ack` is given.

Measured 2026-08-16: a parallel session forward-ported `worker_checkpoint.py`
and `compute_ready.py` straight onto local `main` with an ordinary `git commit`.
Nothing refused it, because `promote_lane.py` gates PROMOTIONS THROUGH
`promote_lane.py` — a control on one path, while the path everybody actually
uses ran unguarded. The session disclosed it rather than relying on it, which is
the only reason it was noticed at all.

A control with an unguarded path is not a control; it is a habit that happens to
hold. This closes the path.

WHAT IT GUARDS. The loop plane: the code that runs the fleet unattended, where a
wrong change is discovered by its consequences at 3am rather than by a reader.
`coordination/session-bus/` DATA is deliberately NOT here — the daemon rewrites
the queue and heartbeats constantly and gating that would make the fleet
unable to run. Policy inside it (BUS_PROTOCOL.md, config.yaml, the schema) IS.

HOW TO ACK, and both forms are visible in the record afterwards:

    git commit -m "...

    D9-ack: <who authorised it, and why>" -- <paths>

or, for a scripted operator run:

    EPYC_D9_ACK="operator ratification 2026-08-16" git commit ... -- <paths>

There is no silent bypass. `EPYC_ALLOW_COMMIT_HYGIENE_BYPASS` deliberately does
NOT apply here: that flag exists for the fetch-staleness check, and reusing it
would let one escape hatch open two doors.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

# Paths whose change alters how the fleet behaves when nobody is watching.
GUARDED_PREFIXES = (
    "scripts/coordination/",
    "scripts/hooks/",
)
GUARDED_EXACT = (
    "coordination/session-bus/config.yaml",
    "coordination/session-bus/BUS_PROTOCOL.md",
    "coordination/session-bus/session_bus.schema.json",
    "coordination/session-bus/compute_policy.yaml",
)
# Tests are the counterweight, not the risk: refusing them would make the safe
# half of a change harder to land than the dangerous half.
EXEMPT_SUBSTRINGS = ("/tests/", "/test_")

ACK_RE = re.compile(r"^\s*D9-ack:\s*\S", re.M | re.I)


def is_guarded(path: str) -> bool:
    if any(s in path for s in EXEMPT_SUBSTRINGS):
        return False
    return path.startswith(GUARDED_PREFIXES) or path in GUARDED_EXACT


def staged_paths() -> list[str]:
    try:
        out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def commit_paths_from_cmd(cmd: str) -> list[str]:
    """Paths after a `--` pathspec separator, if the command uses one."""
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return []
    if "--" not in toks:
        return []
    return [t for t in toks[toks.index("--") + 1:] if not t.startswith("-")]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0                      # cannot inspect -> allow, like its siblings
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in cmd or "commit" not in cmd:
        return 0
    # `git commit` proper, not `git log --format=...commit...` and friends
    if not re.search(r"\bgit\b[^|;&]*\bcommit\b", cmd):
        return 0

    if os.environ.get("EPYC_D9_ACK", "").strip():
        return 0
    if ACK_RE.search(cmd):
        return 0

    # Prefer the explicit pathspec; fall back to what is staged.
    paths = commit_paths_from_cmd(cmd) or staged_paths()
    guarded = sorted({p for p in paths if is_guarded(p)})
    if not guarded:
        return 0

    listing = "\n".join(f"      {p}" for p in guarded[:12])
    more = f"\n      ... and {len(guarded) - 12} more" if len(guarded) > 12 else ""
    print(f"""
D9 REFUSED THIS COMMIT — it changes the loop plane without an ack.

    {listing}{more}

D9, ratified by the operator 2026-08-15: merging any change under
`scripts/coordination/**` requires operator ack. This is the LOOP PLANE — the
code that runs the fleet unattended, where a wrong change is found by its
consequences at 3am rather than by a reader.

`promote_lane.py` already refused such a PROMOTION (exit 5). It could not refuse
a direct commit, and on 2026-08-16 a forward-port went straight to main through
exactly that opening. A control with an unguarded path is not a control.

To proceed, record the ack IN the commit so it survives in the history:

    git commit -m "<subject>

    D9-ack: <who authorised this, and why>" -- <paths>

or, for a scripted operator run:

    EPYC_D9_ACK="<authorisation>" git commit ... -- <paths>

Tests under scripts/coordination/tests/ are exempt: refusing them would make the
safe half of a change harder to land than the dangerous half.
""".rstrip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

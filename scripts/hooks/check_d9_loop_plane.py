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

WHAT IT MATCHES ON, corrected 2026-08-18. The question is always "what will this
commit RECORD", and only git can answer it — so the answer comes from
`git diff --cached` (plain commit) or `git diff HEAD -- <pathspec>` (pathspec
commit), never from deciding that a token in the command line looks like a path.

The defect that forced this: the first implementation took every token after the
FIRST `--` to end-of-string. A commit chained ahead of an unrelated
`scripts/coordination/...` invocation therefore read that script's path as part
of the commit's pathspec and refused a commit that touched no guarded file at
all. A guard that fires on text rather than on effect teaches people to route
around it — which is how the unguarded path this hook exists to close got there
in the first place. The pathspec is now scoped to the commit's own shell segment
and handed to git verbatim.
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


def _run(args: list[str]) -> list[str] | None:
    """Run a git command; None on failure so callers can tell empty from broken."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def staged_paths() -> list[str]:
    return _run(["git", "diff", "--cached", "--name-only"]) or []


def dirty_paths() -> list[str]:
    """Everything modified vs HEAD, staged or not. A commit can only ever record a subset."""
    return _run(["git", "diff", "HEAD", "--name-only"]) or []


# Shell separators that END a command. `shlex.split` keeps these as standalone tokens while
# leaving any that appear INSIDE a quoted -m message embedded in that message's token, so
# splitting on them is safe for commit messages containing ';' or '|'.
_SEPARATORS = frozenset((";", "&&", "||", "|", "\n"))


def _segments(toks):
    segs, cur = [], []
    for t in toks:
        if t in _SEPARATORS:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def commit_pathspec(cmd: str):
    """The pathspec of the `git commit` in `cmd`, or None if it has none.

    SCOPED TO THE COMMIT'S OWN SEGMENT. The 2026-08-18 defect this fixes: the previous
    implementation took every token after the FIRST `--` to end-of-string, so a chained
    commit followed by an unrelated `python3 scripts/coordination/...` invocation swept
    that script's path in and refused a commit that touched no guarded file. Everything
    after a shell separator belongs to a different command, not to this commit's pathspec.
    """
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return None
    for seg in _segments(toks):
        if "commit" not in seg:
            continue
        try:
            gi = seg.index("git")
        except ValueError:
            continue
        if seg.index("commit") < gi:
            continue
        if "--" not in seg:
            return None
        paths = [t for t in seg[seg.index("--") + 1:] if not t.startswith("-")]
        return paths or None
    return None


def commit_targets(cmd: str):
    """What this commit will actually record, ACCORDING TO GIT — never parsed path text.

    Two shapes, because they read different sources:
      * `git commit -- <pathspec>` bypasses the index and records the WORKING TREE state of
        those paths, so the answer is `git diff HEAD --name-only -- <pathspec>`. The pathspec
        is handed to git verbatim; this function never itself decides whether a token names a
        file, so directories, globs and `:(exclude)` magic behave as git defines them.
      * a plain `git commit` records the INDEX, so the answer is `git diff --cached`.

    On any git failure the fallback is deliberately over-broad — staged plus every dirty path
    — so a malformed pathspec produces a refusal to inspect rather than a silent allow.
    """
    spec = commit_pathspec(cmd)
    if spec is None:
        return staged_paths()
    named = _run(["git", "diff", "HEAD", "--name-only", "--"] + spec)
    if named is None:
        return sorted(set(staged_paths()) | set(dirty_paths()))
    return named


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

    # Cheap exit first: if no guarded file is modified vs HEAD at all, no commit of any
    # shape can record one, and the command's tokens never need to be looked at.
    if not any(is_guarded(p) for p in dirty_paths()):
        return 0

    guarded = sorted({p for p in commit_targets(cmd) if is_guarded(p)})
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

#!/usr/bin/env python3
"""commit-msg gate: an edit to an auto-loaded instruction surface needs `Operator-Ratified: yes`.

AUD-15 / R-8, closes F-19 (operator decision 2026-11-02, decision tool, BRF-T5-2).
`CLAUDE.md` (and its `AGENTS.md` alias), `agents/AGENT_INSTRUCTIONS.md` and
`agents/shared/*.md` load at every session start, so a wrong premise written there
becomes every session's truth (F-21's amplifier). Those paths have been on the
human-only gate list since 5fad27d56, but the only enforcement was
`check_trust_boundary_edit.sh`, which sees the Write/Edit TOOLS: a shell write, a
script, or a commit of someone else's working-tree edit passed untouched.

This gate sits where every route converges — the commit. Git runs commit-msg with
GIT_INDEX_FILE already pointing at the exact index being recorded (a pathspec commit's
temporary index, a private index, a lane worktree's own index), so the gate reads THIS
commit's paths, never the shared clone's dirty tree.

  * GUARDED: any added, modified, deleted, type-changed or renamed path matching the
    surfaces above. `--no-renames` lists BOTH sides of a rename, so moving a file into
    or out of a surface is a surface edit, and a deletion is one too.
  * ALLOWED with a trailer line `Operator-Ratified: yes` in the message. The operator's
    ratify scripts carry it (612358902, ba1bb9703). An agent commit does not.
  * MERGES: content identical to an incoming parent was judged when that parent was
    committed; only content matching NEITHER side (a conflict resolution, an evil
    merge) is judged here. Same rule as the D9 git-hook mode.
  * FAILS CLOSED when git cannot list the commit's paths.

Honest limits: hooks live in the clone, so `--no-verify` skips this, and an agent can
type the trailer. The gate makes an unratified instruction edit impossible to land BY
ACCIDENT and impossible to land SILENTLY — the trailer is in the history, attributable.

Usage (installed by scripts/hooks/install_git_hooks.sh into the commit-msg wrapper):
    check_instruction_surface_ratified.py --git-hook commit-msg <message-file>
Tests: scripts/hooks/tests/test_instruction_surface_ratified.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

TRAILER_RE = re.compile(r"^\s*Operator-Ratified:\s*yes\s*$", re.M | re.I)
EXACT = ("CLAUDE.md", "AGENTS.md", "agents/AGENT_INSTRUCTIONS.md")
SHARED_PREFIX = "agents/shared/"
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def is_surface(path: str) -> bool:
    return path in EXACT or (path.startswith(SHARED_PREFIX) and path.endswith(".md"))


def _run(args: list[str]) -> list[str] | None:
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def _blob_id(spec: str) -> str | None:
    out = _run(["git", "rev-parse", "-q", "--verify", spec])
    return out[0] if out else None


def _merge_parents() -> list[str]:
    path = _run(["git", "rev-parse", "--git-path", "MERGE_HEAD"])
    if not path:
        return []
    f = path[0]
    if not os.path.isabs(f):
        top = _run(["git", "rev-parse", "--show-toplevel"])
        f = os.path.join(top[0] if top else ".", f)
    try:
        with open(f, encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip()]
    except OSError:
        return []


def surface_paths() -> list[str] | None:
    """Instruction-surface paths THIS commit records; None when git cannot answer."""
    base = "HEAD" if _blob_id("HEAD") else _EMPTY_TREE
    changed = _run(["git", "diff", "--cached", "--name-only", "--no-renames", base])
    if changed is None:
        return None
    hits = sorted({p for p in changed if is_surface(p)})
    parents = _merge_parents()
    if parents and hits:
        kept = []
        for p in hits:
            mine = _blob_id(f":{p}")
            if any(_blob_id(f"{par}:{p}") == mine for par in parents):
                continue
            kept.append(p)
        hits = kept
    return hits


def message_is_ratified(msg_file: str) -> bool:
    try:
        with open(msg_file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return False
    # git strips '#' comment lines from the final message; a trailer that only
    # appears in a comment would not survive into the history.
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return bool(TRAILER_RE.search(body))


def _refuse(paths: list[str] | None) -> None:
    what = ("git could not list this commit's paths, so the gate cannot tell whether an "
            "instruction surface is touched" if paths is None else
            "this commit edits auto-loaded instruction surface(s):\n" +
            "\n".join(f"    {p}" for p in paths))
    print(f"""BLOCKED (AUD-15): {what}

CLAUDE.md / AGENTS.md, agents/AGENT_INSTRUCTIONS.md and agents/shared/*.md load into
every session at start-up; a wrong premise there becomes every session's truth. They
are human-amendment-only (coordination/session-bus/human_only_paths.yaml), and an edit
lands only with the operator's ratification, recorded as a trailer line:

    Operator-Ratified: yes

The operator's ratify scripts add it. An agent that needs one of these edits prepares
the change as a ratify script or a token-request for the operator to run; it does not
type the trailer itself. Unstage the surface path(s) to commit the rest of the work.""",
          file=sys.stderr)


def git_hook_main(phase: str, msg_file: str | None) -> int:
    if phase != "commit-msg" or not msg_file:
        print(f"check_instruction_surface_ratified: unsupported git-hook phase {phase!r}",
              file=sys.stderr)
        return 1
    paths = surface_paths()
    if paths == []:
        return 0
    if message_is_ratified(msg_file):
        return 0
    _refuse(paths)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--git-hook":
        return git_hook_main(argv[2] if len(argv) > 2 else "", argv[3] if len(argv) > 3 else None)
    print(__doc__.strip().splitlines()[0], file=sys.stderr)
    print("usage: check_instruction_surface_ratified.py --git-hook commit-msg <message-file>",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

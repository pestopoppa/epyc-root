#!/usr/bin/env python3
"""DP-4: refuse a git WRITE in a shared child clone while another op's sequencer is live.

WHY. `repos/<name>` is a symlink out of every lane worktree to ONE shared clone
(`/mnt/raid0/llm/<name>`): one index, one CHERRY_PICK_HEAD for every agent. On
2026-08-12 a `git add` into the research clone put 42 files into another agent's
in-flight cherry-pick index; only `git commit -- <paths>` refusing during a
cherry-pick kept them out of that agent's commit. This scanner makes the check
structural: before add/commit/checkout/... in a shared clone, the sequencer state
must be clean (no CHERRY_PICK_HEAD / MERGE_HEAD / REVERT_HEAD / REBASE_HEAD /
rebase-merge / rebase-apply, no unmerged paths).

SCOPE. A repo is "shared" when its toplevel resolves (realpath) to a DIRECT child of
the shared root (default /mnt/raid0/llm; env SEQUENCER_GUARD_ROOT overrides). Linked
worktrees (/mnt/raid0/llm/worktrees/...) have their own per-worktree git dir and are
not guarded. State is read with `git rev-parse --git-path`, so it is per-worktree
correct. AGENT-TYPED Bash only (same universe as git_clean_scan).

NOT BLOCKED: the sequencer's own controls (`--continue --abort --skip --quit`) for
cherry-pick/revert/merge/rebase/am — the owner must be able to finish. The owner
who is legitimately mid-sequence types `SEQUENCER_OWNER=1 git add ...`.

VERDICTS (stdout, one line)
  allow
  block:sequencer:<repo>:<verb>:<state;state>
  block:sequencer-unresolvable:<verb>   write verb, tree unnamable (still allowed
                                        unless the cwd text cannot be resolved)
  scanner-error
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import SEPARATORS, lex_text  # noqa: E402
from git_clean_scan import (  # noqa: E402
    _GIT_OPT_WITH_VALUE, _KEYWORDS, _SHELLS, _WRAPPERS, _MAX_DEPTH,
    _assignment, _git, _resolve_dir, _unstand, _words,
)

OVERRIDE = "SEQUENCER_OWNER"
DEFAULT_ROOT = "/mnt/raid0/llm"
WRITE_VERBS = {"add", "commit", "checkout", "switch", "restore", "reset", "rm", "mv",
               "stash", "apply", "merge", "cherry-pick", "revert", "rebase", "am",
               "pull", "clean", "update-index"}
SEQ_VERBS = {"cherry-pick", "revert", "merge", "rebase", "am"}
CONTROL_FLAGS = {"--continue", "--abort", "--skip", "--quit"}
STATE_FILES = ("CHERRY_PICK_HEAD", "MERGE_HEAD", "REVERT_HEAD", "REBASE_HEAD",
               "rebase-merge", "rebase-apply")


def _shared_root() -> str:
    return os.path.realpath(os.environ.get("SEQUENCER_GUARD_ROOT") or DEFAULT_ROOT)


def sequencer_state(repo: str) -> tuple[str | None, list[str]]:
    """(toplevel, live-state names). toplevel None when repo is not a work tree."""
    top = _git(repo, "rev-parse", "--show-toplevel")
    if top is None or top.returncode != 0:
        return None, []
    live: list[str] = []
    for name in STATE_FILES:
        p = _git(repo, "rev-parse", "--git-path", name)
        if p is None or p.returncode != 0:
            continue
        path = Path(p.stdout.strip())
        if not path.is_absolute():
            path = Path(repo) / path
        if path.exists():
            live.append(name)
    un = _git(repo, "ls-files", "-u")
    if un is not None and un.returncode == 0 and un.stdout.strip():
        n = len({ln.split("\t", 1)[-1] for ln in un.stdout.splitlines()})
        live.append(f"unmerged-paths({n})")
    return top.stdout.strip(), live


def _is_shared(top: str) -> bool:
    real = os.path.realpath(top)
    return os.path.dirname(real) == _shared_root()


def _verdict(repo: str | None, verb: str, args: list[str]) -> str:
    if verb in SEQ_VERBS and any(a in CONTROL_FLAGS for a in args):
        return "allow"
    if verb == "stash" and args and args[0] in ("list", "show"):
        return "allow"
    if repo is None:
        return "allow"   # cannot name the tree; hook caller already fails open on cwd
    if not os.path.isdir(repo):
        return "allow"
    top, live = sequencer_state(repo)
    if top is None or not live or not _is_shared(top):
        return "allow"
    return f"block:sequencer:{os.path.realpath(top)}:{verb}:{';'.join(live)}"


def _worse(a: str, b: str) -> str:
    def rank(v: str) -> int:
        return 2 if v.startswith("block:") else (0 if v == "allow" else 1)
    return b if rank(b) > rank(a) else a


def classify(command: str, cwd: str | None, depth: int = 0) -> str:
    if depth > _MAX_DEPTH:
        return "allow"
    try:
        text = lex_text(command, keep_quoted=True)
    except Exception as exc:  # noqa: BLE001
        print(f"git_sequencer_scan: lexer failed: {exc!r}", file=sys.stderr)
        return "scanner-error"
    text = re.sub(r"\$\(|`|<\(|>\(", "\n", text)
    state_cwd = cwd
    worst = "allow"
    for raw in SEPARATORS.split(text):
        words = _words(raw)
        while words and words[0] in _KEYWORDS:
            words.pop(0)
        while words and words[0].startswith("(") and len(words[0]) > 1:
            words[0] = words[0][1:]
        override = False
        while words and _assignment(words[0]):
            k, _, v = words[0].partition("=")
            if k == OVERRIDE and v not in ("", "0"):
                override = True
            words.pop(0)
        while words and os.path.basename(words[0]) in _WRAPPERS:
            words.pop(0)
            while words and (words[0].startswith("-") or _assignment(words[0])
                             or re.fullmatch(r"\d+(\.\d+)?[smhd]?", words[0])):
                if _assignment(words[0]) and words[0].split("=", 1)[0] == OVERRIDE:
                    override = True
                words.pop(0)
        words = [w.rstrip(")") if w.endswith(")") and "(" not in w else w for w in words]
        words = [w for w in words if w]
        if not words:
            continue
        cmd = os.path.basename(words[0])
        rest = words[1:]
        if cmd in ("cd", "pushd"):
            target = next((w for w in rest if not w.startswith("-")), "~")
            state_cwd = _resolve_dir(state_cwd, target)
            continue
        if cmd in _SHELLS and "-c" in rest:
            idx = rest.index("-c")
            if idx + 1 < len(rest):
                worst = _worse(worst, classify(rest[idx + 1], state_cwd, depth + 1))
            continue
        if cmd == "eval" and rest:
            worst = _worse(worst, classify(" ".join(rest), state_cwd, depth + 1))
            continue
        if cmd != "git":
            continue
        repo = state_cwd
        j = 0
        while j < len(rest) and rest[j].startswith("-"):
            opt = rest[j]
            if opt in _GIT_OPT_WITH_VALUE and j + 1 < len(rest):
                if opt in ("-C", "--work-tree"):
                    repo = _resolve_dir(repo, rest[j + 1])
                j += 2
                continue
            if opt.startswith("--work-tree="):
                repo = _resolve_dir(repo, opt.split("=", 1)[1])
            j += 1
        if j >= len(rest) or rest[j] not in WRITE_VERBS or override:
            continue
        worst = _worse(worst, _verdict(repo, rest[j], rest[j + 1:]))
    return worst


def main() -> int:
    command = sys.stdin.read()
    if not command.strip():
        print("error: empty command — refusing to emit a verdict", file=sys.stderr)
        return 2
    print(classify(command, os.environ.get("HOOK_CWD") or os.getcwd()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

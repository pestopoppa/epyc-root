#!/usr/bin/env python3
"""Classify a shell command for DESTRUCTIVE REVERTS in a multi-writer tree.

Origin: INC-20260812-destructive-revert — twice in one night, minutes apart, two
different agents ran `git checkout -- <path>` to "clean up after myself" and each
silently destroyed ANOTHER agent's uncommitted fix to the same safety-critical
file (start_orchestrator_test.sh). The first survived via an incidental `cp`;
the second was only recovered because the first backup still existed. A revert
touches no history and leaves no trace: uncommitted work it discards exists
nowhere afterwards. A sweep is recoverable from the wrong commit; this is
recoverable from nothing.

The guard is PRECISION-TARGETED: a revert of a CLEAN path is a no-op and passes;
a revert that would discard uncommitted content is exactly the incident and
blocks. Reverting your OWN dirty work is legitimate — the override is an
explicit, auditable token typed in the same command:

    REVERT_VERIFIED=1 git checkout -- <path>

which asserts "I ran `git status --short <path>` and the dirty content is mine
(or backed up)". The token is the audit trail.

Verdicts on stdout (one line):
    allow
    block:revert-dirty:<repo>:<paths...>      checkout/restore would discard mods
    block:repo-destructive:<repo>:<form>      reset --hard / checkout -f on dirty tree
    block:clean-untracked:<repo>              git clean -f with untracked files present
    scanner-error                             (stderr carries detail)

Like the pkill guard, this models AGENT-TYPED commands only. A revert inside an
invoked script is out of its universe — stated here so the pass is never read
wider than the instrument (catalogue face 11).
"""
import os
import shlex
import subprocess
import sys


def _segments(tokens):
    """Split a token stream on shell control operators into simple commands."""
    seg = []
    for t in tokens:
        if t in (";", "&&", "||", "|", "&"):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def _status(repo, paths):
    """Uncommitted-state lines for paths ('' = whole repo). None on git failure."""
    cmd = ["git", "-C", repo or ".", "status", "--porcelain"]
    if paths:
        cmd += ["--"] + paths
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return [l for l in out.stdout.splitlines() if l.strip()]


def classify(command, cwd=None):
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return "scanner-error"

    for seg in _segments(tokens):
        # Leading VAR=value assignments: the override token lives here.
        override = False
        i = 0
        while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
            if seg[i].split("=", 1)[0] == "REVERT_VERIFIED":
                override = True
            i += 1
        if i >= len(seg) or os.path.basename(seg[i]) != "git":
            continue
        if override:
            continue

        args = seg[i + 1 :]
        repo = cwd or "."
        j = 0
        while j < len(args) and args[j].startswith("-"):
            if args[j] == "-C" and j + 1 < len(args):
                repo = args[j + 1]
                j += 2
                continue
            j += 1
        if j >= len(args):
            continue
        sub, rest = args[j], args[j + 1 :]

        if sub == "restore":
            # --staged alone edits the index only; any worktree-touching form is
            # destructive. --worktree or neither flag => worktree.
            staged = "--staged" in rest or "-S" in rest
            worktree = "--worktree" in rest or "-W" in rest or not staged
            paths = [a for a in rest if not a.startswith("-")]
            if worktree and paths:
                dirty = _status(repo, paths)
                if dirty is None:
                    return "scanner-error"
                if dirty:
                    return f"block:revert-dirty:{repo}:{' '.join(paths)}"

        elif sub == "checkout":
            forced = "-f" in rest or "--force" in rest
            if "--" in rest:
                paths = rest[rest.index("--") + 1 :]
            else:
                # Path-form without `--`: any arg that exists on disk is a path.
                base = repo if os.path.isabs(repo) else os.path.join(cwd or ".", repo)
                paths = [
                    a for a in rest
                    if not a.startswith("-") and os.path.exists(os.path.join(base, a))
                ]
            if paths:
                dirty = _status(repo, paths)
                if dirty is None:
                    return "scanner-error"
                if dirty:
                    return f"block:revert-dirty:{repo}:{' '.join(paths)}"
            elif forced:
                dirty = _status(repo, None)
                if dirty is None:
                    return "scanner-error"
                if any(not l.startswith("??") for l in dirty):
                    return f"block:repo-destructive:{repo}:checkout--force"

        elif sub == "reset" and "--hard" in rest:
            dirty = _status(repo, None)
            if dirty is None:
                return "scanner-error"
            if any(not l.startswith("??") for l in dirty):
                return f"block:repo-destructive:{repo}:reset--hard"

        elif sub == "clean":
            flags = "".join(a.lstrip("-") for a in rest if a.startswith("-"))
            if "f" in flags:
                dirty = _status(repo, None)
                if dirty is None:
                    return "scanner-error"
                if any(l.startswith("??") for l in dirty):
                    return f"block:clean-untracked:{repo}"

    return "allow"


if __name__ == "__main__":
    print(classify(sys.stdin.read(), cwd=os.environ.get("HOOK_CWD") or os.getcwd()))

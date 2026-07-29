#!/usr/bin/env python3
"""Hook: PreToolUse → Bash. Commit hygiene on the shared repos.

Rider R7a (handoffs/active/session-bus-thin-dispatcher.md §Rider) — the two
checks the coordinator-daemon's audit explicitly CANNOT make.

WHY THIS LAYER EXISTS. R7's audit established that "wholesale `git add`" and
"commit without a preceding fetch" are not decidable after the fact: a finished
commit does not record how it was staged, and every session here commits under
one git identity, so nothing can be attributed to an agent rather than the
operator. Both ARE decidable at the moment of action, where the actor is known —
which is here.

  Rule A — wholesale staging on a shared repo. `git add -A|--all|-u|.` and
  `git commit -a|-am` stage the whole tree. /workspace and /mnt/raid0/llm/<repo>
  are the same physical clones, shared by parallel sessions, so a wholesale stage
  sweeps another session's in-progress edits into this commit. Not hypothetical:
  on 2026-07-27 a progress entry written by one session rode into commit 94a39cc0
  authored by another and reached origin/main under an unrelated message.

  Rule B — committing without a fresh fetch. Parallel sessions push between your
  read and your write, so a stale FETCH_HEAD means you do not know whether you
  are behind upstream. The fix costs one second.

WHY PYTHON RATHER THAN GREP. The first draft matched with regex and had a
false-positive class it could not escape: `git commit -m "add -A to the docs"`
matched, because a regex cannot see that `-A` is inside a quoted message. shlex
tokenises the command properly, so flags are distinguished from message text.
This is the same lesson the drop_caches guard taught — an over-broad matcher is
worse than a missing one, because a false block stalls a session for a reason it
cannot see.

SCOPE. Enforced only for the shared repos, and skipped when the command
navigates elsewhere (`cd` / `-C` into a sandbox), so throwaway git fixtures for
tests stay frictionless. The heuristic errs permissive on purpose.

Override: EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1
Tune:     EPYC_FETCH_MAX_AGE_S (default 600)
Tests:    scripts/hooks/tests/test_commit_hygiene.py
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

SHARED_REPOS = [
    "/workspace",
    "/mnt/raid0/llm/epyc-root",
    "/mnt/raid0/llm/epyc-orchestrator",
    "/mnt/raid0/llm/epyc-inference-research",
    "/mnt/raid0/llm/llama.cpp",
]

# Splits a shell line into segments at separators, so `cd /tmp/x && git add -A`
# is analysed per segment rather than as one blob.
_SEP = re.compile(r"(?:\|\||&&|[;&|\n])")

WHOLESALE_ADD_FLAGS = {"-A", "--all", "-u", "--update"}
# Flags that take a value we must not scan for short flags (the message text).
_VALUE_FLAGS = {"-m", "--message", "-F", "--file", "-C", "--reuse-message",
                "-c", "--reedit-message", "--author", "--date", "-S", "--gpg-sign"}


def canon(p: str) -> str:
    try:
        return str(Path(p).resolve())
    except OSError:
        return p


SHARED_CANON = {canon(p) for p in SHARED_REPOS}


def is_shared(path: str) -> bool:
    return canon(path) in SHARED_CANON


def git_invocations(segment: str) -> list[list[str]]:
    """Tokenised git invocations in one segment. Malformed quoting -> none."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return []
    out: list[list[str]] = []
    for i, tok in enumerate(tokens):
        if tok == "git" or tok.endswith("/git"):
            out.append(tokens[i:])
    return out


def subcommand_of(tokens: list[str]) -> tuple[str | None, list[str], str | None]:
    """Return (subcommand, args_after_it, -C path). Skips git's own options."""
    i = 1
    dash_c: str | None = None
    while i < len(tokens):
        tok = tokens[i]
        if tok == "-C" and i + 1 < len(tokens):
            dash_c = tokens[i + 1]
            i += 2
            continue
        if tok.startswith("-") or "=" in tok and tok.split("=")[0].startswith("-"):
            i += 1
            continue
        return tok, tokens[i + 1:], dash_c
    return None, [], dash_c


def positional_and_flags(args: list[str]) -> tuple[list[str], list[str]]:
    """Split args into (flags, positionals), skipping values of value-taking flags.

    This is the part regex could not do: the argument of -m is message TEXT and
    must never be inspected for flags.
    """
    flags: list[str] = []
    positionals: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--":
            positionals.extend(args[i + 1:])
            break
        base = tok.split("=", 1)[0]
        if base in _VALUE_FLAGS:
            flags.append(base)
            if "=" not in tok:
                i += 2          # skip the value
                continue
            i += 1
            continue
        if tok.startswith("-"):
            flags.append(tok)
            i += 1
            continue
        positionals.append(tok)
        i += 1
    return flags, positionals


def short_cluster_has(flags: list[str], letter: str) -> bool:
    """True if a single-dash cluster carries `letter` (-a, -am, -ma) — never --amend."""
    for f in flags:
        if f.startswith("--") or not f.startswith("-"):
            continue
        if letter in f[1:]:
            return True
    return False


def resolve_repo(cmd: str, segment: str, dash_c: str | None) -> str | None:
    """Which repo this acts on, or None when it is not a shared repo."""
    if dash_c:
        return canon(dash_c) if is_shared(dash_c) else None
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = []
    # A `cd` earlier in the same command line moves us.
    try:
        whole = shlex.split(cmd)
    except ValueError:
        whole = tokens
    for i, tok in enumerate(whole):
        if tok == "cd" and i + 1 < len(whole):
            return canon(whole[i + 1]) if is_shared(whole[i + 1]) else None
    default = os.environ.get("CLAUDE_PROJECT_DIR", "/workspace")
    return canon(default) if is_shared(default) else None


def fetch_precedes_commit(cmd: str, repo: str) -> bool:
    """True if the command fetches this repo before committing in it.

    Matched on tokenised segments so a `git fetch` inside a commit MESSAGE cannot
    satisfy the rule — the same quoting hazard the flag checks avoid.
    """
    fetch_at: int | None = None
    commit_at: int | None = None
    for idx, segment in enumerate(_SEP.split(cmd)):
        for tokens in git_invocations(segment):
            sub, _args, dash_c = subcommand_of(tokens)
            if sub not in {"fetch", "commit", "pull"}:
                continue
            target = canon(dash_c) if dash_c else canon(
                os.environ.get("CLAUDE_PROJECT_DIR", "/workspace"))
            # A `cd` in the same command redirects an un-flagged invocation.
            if not dash_c:
                try:
                    whole = shlex.split(cmd)
                    for i, tok in enumerate(whole):
                        if tok == "cd" and i + 1 < len(whole):
                            target = canon(whole[i + 1])
                            break
                except ValueError:
                    pass
            if target != canon(repo):
                continue
            if sub in {"fetch", "pull"} and fetch_at is None:
                fetch_at = idx
            elif sub == "commit" and commit_at is None:
                commit_at = idx
    return fetch_at is not None and commit_at is not None and fetch_at < commit_at


def block(message: str) -> int:
    print(message.rstrip(), file=sys.stderr)
    return 2


def main() -> int:
    if os.environ.get("EPYC_ALLOW_COMMIT_HYGIENE_BYPASS", "0") == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0                      # cannot inspect -> allow
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in cmd:
        return 0

    max_age = int(os.environ.get("EPYC_FETCH_MAX_AGE_S", "600"))

    for segment in _SEP.split(cmd):
        for tokens in git_invocations(segment):
            sub, args, dash_c = subcommand_of(tokens)
            if sub not in {"add", "commit"}:
                continue
            repo = resolve_repo(cmd, segment, dash_c)
            if repo is None:
                continue              # sandbox / unknown -> not our business
            flags, positionals = positional_and_flags(args)

            if sub == "add":
                if set(flags) & WHOLESALE_ADD_FLAGS or "." in positionals:
                    return block(f"""BLOCKED: wholesale `git add` on a shared repo ({repo}).

These trees are shared by parallel sessions — /workspace and /mnt/raid0/llm/<repo>
are the same physical clone — so staging everything sweeps another session's
in-progress edits into your commit. On 2026-07-27 exactly that happened: a
progress entry from one session rode into commit 94a39cc0 authored by another and
reached origin/main under an unrelated message.

Stage explicit paths, then verify:
    git add path/one path/two
    git diff --cached --name-only

Override: EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1 (once you have checked the staged set).""")

            if sub == "commit":
                if "--all" in flags or short_cluster_has(flags, "a"):
                    return block(f"""BLOCKED: `git commit -a/--all` on a shared repo ({repo}).

-a stages every tracked modification in the tree, including edits made by
parallel sessions in this shared clone. Stage explicit paths instead:
    git add path/one path/two && git commit -m "..."

Override: EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1""")

                # `git fetch && git commit` in ONE command is exactly the idiom
                # this rule wants, but a PreToolUse hook runs BEFORE any of it
                # executes, so judging on the pre-fetch mtime would forbid the
                # compliant form and teach people to bypass instead of comply. A
                # guard that blocks the behaviour it is asking for is a bad guard.
                # So: an in-command fetch for this repo, positioned before the
                # commit, satisfies freshness.
                if fetch_precedes_commit(cmd, repo):
                    continue

                fetch_head = Path(repo) / ".git" / "FETCH_HEAD"
                try:
                    age = int(time.time() - fetch_head.stat().st_mtime)
                except OSError:
                    age = 10 ** 9
                if age > max_age:
                    shown = "no FETCH_HEAD" if age == 10 ** 9 else f"{age}s old"
                    return block(f"""BLOCKED: committing in {repo} with a stale fetch ({shown}, threshold {max_age}s).

Parallel sessions push between your read and your write, so without a fresh fetch
you do not know whether you are behind upstream. Run:

    git -C {repo} fetch && git -C {repo} log --oneline @{{u}}..HEAD

then commit. Tune EPYC_FETCH_MAX_AGE_S, or set
EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1 for a deliberate offline commit.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())

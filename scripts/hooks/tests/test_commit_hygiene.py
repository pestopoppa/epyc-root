#!/usr/bin/env python3
"""Tests for scripts/hooks/check_commit_hygiene.py (rider R7a).

The interesting cases are the false-positive ones: a commit MESSAGE that
mentions -A, --all or -a must not be mistaken for the flag. The first draft of
this hook used regex and failed exactly there, which is why the implementation
tokenises with shlex.

Usage: scripts/hooks/tests/test_commit_hygiene.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "scripts" / "hooks" / "check_commit_hygiene.py"
FRESH = {"EPYC_FETCH_MAX_AGE_S": "999999999"}   # neutralise rule B for rule-A cases
STALE = {"EPYC_FETCH_MAX_AGE_S": "0"}           # force rule B


def run(cmd: str, env: dict | None = None) -> int:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT), **(env or {})},
    ).returncode


# (command, expected_rc, env, description)
_PY_HEREDOC = """python3 - <<'HD1'
old = "git commit -m x -- a.md"
HD1
echo done"""

_CAT_HEREDOC = """cat > f.md <<'HD2'
Run: git add -A && git commit -a -m "do it"
HD2
echo written"""

_SHELL_HEREDOC = """bash <<'HD3'
git commit -a -m "this really does commit"
HD3"""

_COMMIT_F_HEREDOC = """git commit -F - -- a.md <<'HD4'
subject line
HD4"""

# ---- HYG-2 (filed 2026-09-05): a quoted newline must not be mistaken for a
# command boundary. The prior segmenter (`_SEP.split(cmd)`) ran a raw regex
# over the UNPARSED text, so a bare newline inside a quoted `-m` message was
# sliced apart exactly like `&&`/`;` -- and the fragment left behind could
# parse on its own as a real (and rule-violating) git invocation. This is a
# distinct bug from the heredoc class above: no heredoc syntax is involved at
# all, just an ordinary multi-line commit message.
_MULTILINE_QUOTE_BUG = ("git commit -m \"Fix hook bug: a message that quotes\n"
                         "    git commit -- file.txt\n"
                         "must not be misread as a pathspec commit\"")

# PAIR, the other direction: a REAL two-command shape written across literal
# newlines (no `&&`, no quoting) must still be segmented and still enforced --
# proving the fix does not buy its permissiveness by refusing to segment at
# all.
_MULTILINE_REAL_CHAIN = 'git add -A\ngit commit -m "x"'
CASES: list[tuple[str, int, dict, str]] = [
    # ---- heredoc bodies are stdin DATA, not commands (measured false positive 2026-08-18) ----
    # `_SEP` splits on newlines, so every body line was tokenised as its own command: a Python
    # heredoc whose SOURCE merely contained the text of a commit was read as a commit and
    # blocked for a stale fetch. Each permissive case is PAIRED with an enforcement case,
    # because a hook that simply stopped looking at heredocs would pass the permissive half.
    (_PY_HEREDOC, 0, STALE, "python heredoc whose data mentions a commit"),
    (_CAT_HEREDOC, 0, STALE, "cat>file heredoc writing git commands as file text"),
    (_SHELL_HEREDOC, 2, STALE, "bash heredoc - body IS commands, still enforced"),
    (_COMMIT_F_HEREDOC, 2, STALE, "commit -F - opener line still checked"),
    (_MULTILINE_QUOTE_BUG, 0, FRESH,
     "HYG-2: a multi-line -m message that quotes a pathspec commit must not be BLOCKED"),
    (_MULTILINE_REAL_CHAIN, 2, FRESH,
     "HYG-2 PAIR: a real add -A / commit chain across literal newlines is still enforced"),
    # ---- rule A: wholesale staging must BLOCK ----
    ("git add -A", 2, FRESH, "git add -A"),
    ("git add --all", 2, FRESH, "git add --all"),
    ("git add .", 2, FRESH, "git add ."),
    ("git add -u", 2, FRESH, "git add -u"),
    ("git -C /workspace add -A", 2, FRESH, "-C shared repo + add -A"),
    ('git commit -am "msg"', 2, FRESH, "git commit -am"),
    ('git commit -a -m "msg"', 2, FRESH, "git commit -a -m"),
    ('git commit --all -m "msg"', 2, FRESH, "git commit --all"),
    ("cd /workspace && git add -A", 2, FRESH, "cd into shared repo then add -A"),

    # ---- FALSE POSITIVES the regex draft got wrong: must ALLOW ----
    ('git commit -m "add -A to the docs"', 0, FRESH, "message mentions -A"),
    ('git commit -m "stage -a everything, we discussed"', 0, FRESH, "message mentions -a"),
    ('git commit -m "use --all sparingly"', 0, FRESH, "message mentions --all"),
    ('git commit -m "git add . is banned"', 0, FRESH, "message contains the whole banned form"),
    ("git commit --amend --no-edit", 0, FRESH, "--amend must not match the -a cluster"),

    # ---- ordinary work must ALLOW ----
    ("git add path/one path/two", 0, FRESH, "explicit paths"),
    ("git add ./scripts/foo.py", 0, FRESH, "relative path starting with ./"),
    ('git commit -m "msg"', 0, FRESH, "plain commit, fresh fetch"),
    ("git status", 0, FRESH, "git status"),
    ("git diff --cached --name-only", 0, FRESH, "inspecting the staged set"),
    ("git log --oneline -3", 0, FRESH, "git log"),
    ("git add -p", 0, FRESH, "patch-mode add is not wholesale"),

    # ---- sandbox / non-shared repos must ALLOW ----
    ("cd /tmp/sandbox && git add -A", 0, FRESH, "sandbox repo: add -A allowed"),
    ("git -C /tmp/sandbox add -A", 0, FRESH, "-C sandbox: add -A allowed"),
    ('cd /tmp/sb && git commit -am "x"', 0, FRESH, "sandbox: commit -am allowed"),

    # ---- rule B: an in-command fetch satisfies freshness ----
    ("git fetch && git commit -m \"x\"", 0, STALE, "fetch THEN commit in one command is allowed"),
    ("git fetch -q && git add a b && git commit -m \"x\"", 0, STALE, "fetch, add, commit chain"),
    ("git -C /workspace fetch && git -C /workspace commit -m \"x\"", 0, STALE,
     "explicit -C on both"),
    ("git commit -m \"x\" && git fetch", 2, STALE, "fetch AFTER commit does not count"),
    ('git commit -m \"remember to git fetch first\"', 2, STALE,
     "a fetch mentioned in the MESSAGE does not count"),
    ("git -C /mnt/raid0/llm/epyc-orchestrator fetch && git commit -m \"x\"", 2, STALE,
     "fetching a DIFFERENT repo does not satisfy this one"),

    # ---- rule B: stale fetch ----
    ('git commit -m "msg"', 2, STALE, "commit with stale fetch blocks"),
    ("git add path/one", 0, STALE, "add is unaffected by fetch age"),
    ("git status", 0, STALE, "status unaffected by fetch age"),
]


#: A path this test makes dirty itself. The earlier draft pointed at a tracked
#: handoff and passed only while that file happened to be uncommitted -- it went
#: green or red depending on unrelated repo state, which is a test that reports
#: something other than what it claims. Untracked shows as `??` in porcelain,
#: which is exactly what dirty_paths() reads.
DIRTY_PROBE = ".hook_dirty_probe"

# ---- command-shape rules (added 2026-08-20) ---------------------------------
# These close the three shapes that are destructive in a SHARED tree regardless
# of who runs them, so the guard tests SHAPE, not identity. Every enforcement
# case is PAIRED with the compliant idiom it must not catch -- a guard that
# forbade `git restore --staged` would forbid the very repair it recommends.
CASES += [
    ("git commit -m 'x' -- handoffs/active/master-handoff-index.md", 2, FRESH,
     "pathspec commit bypasses the index (dada0bbc)"),
    ("git commit -m 'x'", 0, FRESH,
     "PAIR: plain index commit still allowed"),
    ("git -C /tmp/sandbox commit -m 'x' -- foo.txt", 0, FRESH,
     "PAIR: pathspec commit outside the shared repos is not our business"),

    (f"git checkout -- {DIRTY_PROBE}", 2, FRESH,
     "path-restore over a DIRTY path: no conflict, no reflog"),
    ("git checkout -- .gitignore", 0, FRESH,
     "PAIR: path-restore over a CLEAN path is a no-op, not a loss"),
    ("git checkout main", 0, FRESH,
     "PAIR: checking out a BRANCH is untouched"),
    ("git checkout -b lane/mainA", 0, FRESH,
     "PAIR: creating a branch is untouched"),
    ("git restore --staged handoffs/active/master-handoff-index.md", 0, FRESH,
     "PAIR: --staged is index-only and is the RECOMMENDED repair"),

    ("git stash", 2, FRESH,
     "stash captures untracked runtime files that reappear before the pop"),
    ("git stash push -m wip", 2, FRESH, "stash push"),
    ("git stash list", 0, FRESH, "PAIR: read-only stash subcommands allowed"),
]

# ---- HYG-3 (measured 2026-09-15): a shell REDIRECTION is not a pathspec ------
# shlex is a word splitter, not a shell parser, so `2>&1` survived as an ordinary
# token, did not start with `-`, and was filed as a positional -- i.e. read as a
# pathspec. `git commit --file=msg.txt 2>&1` was therefore BLOCKED as a pathspec
# commit, naming `2>&1` as the path. That is the most common way anything on this
# host invokes git, and the only escapes were to drop the redirect or to set
# EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1 -- which also disables rules A and B and the
# checkout/stash shapes. Same family as the heredoc and HYG-2 false positives.
#
# Every permissive case is PAIRED with an enforcement case using the same
# redirection, because a fix that simply stopped parsing redirected commands
# would pass the permissive half while silently switching the guard off.
CASES += [
    # the measured bug, in its exact shape and its -F variant
    ("git commit --file=msg.txt 2>&1", 0, FRESH,
     "HYG-3: `2>&1` on a commit is a redirection, not a pathspec"),
    ("git commit -F msg.txt 2>&1", 0, FRESH,
     "HYG-3: same via `-F <file>`"),
    ('git commit -m "x" 2>&1 | tail -5', 0, FRESH,
     "HYG-3: redirect plus a pipe still segments correctly"),
    # every other redirection shape shlex can leave behind
    ('git commit -m "x" > out.log', 0, FRESH,
     "HYG-3: bare `>` takes its target with it"),
    ('git commit -m "x" >out.log', 0, FRESH, "HYG-3: `>` with attached target"),
    ('git commit -m "x" >> out.log 2>&1', 0, FRESH, "HYG-3: append plus stderr dup"),
    ('git commit -m "x" &> out.log', 0, FRESH, "HYG-3: `&>` combined redirect"),
    ('git commit -m "x" 1>out.log 2>err.log', 0, FRESH, "HYG-3: explicit fds"),
    ('git commit -m "x" < /dev/null', 0, FRESH, "HYG-3: input redirection"),

    # PAIRS: the rules must still fire when a redirection is present.
    ("git commit -m 'x' -- handoffs/active/master-handoff-index.md 2>&1", 2, FRESH,
     "HYG-3 PAIR: a REAL pathspec commit is still blocked when redirected"),
    ("git add -A 2>&1", 2, FRESH,
     "HYG-3 PAIR: wholesale add is still blocked when redirected"),
    ('git commit -am "x" > out.log', 2, FRESH,
     "HYG-3 PAIR: commit -am is still blocked when redirected"),
    ('git commit -m "x" 2>&1', 2, STALE,
     "HYG-3 PAIR: rule B still fires on a redirected commit"),
    ("git stash push -m wip 2>&1", 2, FRESH,
     "HYG-3 PAIR: stash is still blocked when redirected"),
    ("git fetch 2>&1 && git commit -m \"x\" 2>&1", 0, STALE,
     "HYG-3 PAIR: a redirected fetch still satisfies freshness for a redirected commit"),
]


def main() -> int:
    failures: list[str] = []
    probe = REPO_ROOT / DIRTY_PROBE
    probe.write_text("dirty fixture for the path-restore rule\n")
    try:
        return _run_cases()
    finally:
        probe.unlink(missing_ok=True)


def _run_cases() -> int:
    failures: list[str] = []
    for cmd, expect, env, why in CASES:
        rc = run(cmd, env)
        ok = rc == expect
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want={expect}  {why}")
        if not ok:
            failures.append(f"{why} ({cmd!r})")

    rc = run("git add -A", {**FRESH, "EPYC_ALLOW_COMMIT_HYGIENE_BYPASS": "1"})
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  explicit operator override")
    if not ok:
        failures.append("override")

    # Malformed quoting must not crash or block.
    rc = run('git commit -m "unterminated', FRESH)
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  malformed quoting degrades open")
    if not ok:
        failures.append("malformed quoting")

    print(f"\n{'FAILED: ' + '; '.join(failures) if failures else 'all checks passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

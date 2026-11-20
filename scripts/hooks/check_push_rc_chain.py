#!/usr/bin/env python3
"""PreToolUse(Bash) hook: refuse a push whose exit code is masked by a pipe, chained into cleanup.

AK audit C6 (2026-11-20; D9 ack "AK audit hooks C1-C6"). On 2026-11-19 02:19Z two worktrees
were removed after FAILED pushes because the chain read

    python3 scripts/coordination/serialized_push.py ... | grep PUSH && git worktree remove <wt>

`grep PUSH` matches "PUSH REJECTED" as happily as "PUSH VERIFIED", and a pipeline's status is
its LAST command's, so the push's rc never reached `&&`. The unpushed commits went with the
worktree.

Refused (exit 2, one line, cause + fix) only when ALL hold in one command string:
  * a push: `serialized_push.py` or `git ... push`;
  * its output is piped (`|`, not `||`) into another command in the same segment;
  * a LATER segment (after `&&` or `;`) runs `git worktree remove` or `git branch -d/-D`;
  * no `pipefail` is set and `PIPESTATUS` is not read in the command;
  * quoted strings and heredoc bodies are ignored (Fable review S3).
Everything else passes: a bare push chain (`push && git worktree remove`) branches on the real
rc and is correct; a piped push with no cleanup after it destroys nothing. Malformed input and
internal errors pass (the hook never blocks on its own bug).
"""
import json
import re
import sys

PUSH = re.compile(r"serialized_push\.py|\bgit\b(?:\s+-C\s+\S+|\s+-c\s+\S+)*\s+push\b")
CLEANUP = re.compile(r"\bgit\b(?:\s+-C\s+\S+)*\s+(?:worktree\s+remove|branch\s+(?:-[a-zA-Z]*[dD]\b|--delete))")
SPLIT = re.compile(r"&&|;|\n")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.S | re.M)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")


def _code_only(command):
    """Fable review S3: drop heredoc bodies and quoted strings (commit messages, grep patterns),
    so a `|` or `git push` inside them is not read as shell structure."""
    return QUOTED.sub("Q", HEREDOC.sub("HEREDOC", command))


def verdict(command):
    if not isinstance(command, str) or "pipefail" in command or "PIPESTATUS" in command:
        return None                       # the push rc is checked explicitly
    segments = SPLIT.split(_code_only(command))
    for i, seg in enumerate(segments):
        m = PUSH.search(seg)
        if not m:
            continue
        tail = seg[m.end():].replace("||", "")
        if "|" not in tail:
            continue
        for later in segments[i + 1:]:
            c = CLEANUP.search(later)
            if c:
                return (f"BLOCKED: push output is piped (its exit code is lost) and the chain then runs "
                        f"'{c.group(0)}' - a failed push would destroy unpushed work; fix: run the push alone "
                        f"and branch on its rc (`push && {c.group(0)} ...`), or `set -o pipefail` first")
    return None


def main():
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") not in (None, "Bash"):
            return 0
        v = verdict((payload.get("tool_input") or {}).get("command"))
    except Exception:
        return 0
    if v:
        print(v, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

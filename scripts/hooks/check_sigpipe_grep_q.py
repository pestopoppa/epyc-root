#!/usr/bin/env python3
"""Warn on staged shell pipelines where grep -q can SIGPIPE a producer under pipefail.

This is deliberately advisory: findings and checker errors always return success.
Only staged .sh/.bash blobs are inspected; unstaged working-tree text is ignored.
"""
from __future__ import annotations

import shlex
import subprocess
import sys


def logical_lines(text: str):
    """Join shell backslash continuations while retaining the first line number."""
    buf = ""
    first = 1
    for number, line in enumerate(text.splitlines(), 1):
        if not buf:
            first = number
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        yield first, buf + line
        buf = ""
    if buf:
        yield first, buf


def split_commands(line: str):
    """Split a physical/logical line on unquoted pipes and semicolons."""
    commands = []
    buf = []
    quote = None
    escaped = False
    i = 0
    while i < len(line):
        char = line[i]
        if escaped:
            buf.append(char)
            escaped = False
            i += 1
            continue
        if char == "\\" and quote != "'":
            buf.append(char)
            escaped = True
            i += 1
            continue
        if quote:
            buf.append(char)
            if char == quote:
                quote = None
            i += 1
            continue
        if char in ("'", '"'):
            quote = char
            buf.append(char)
            i += 1
            continue
        if char == "#":
            break
        if char == "|" and i + 1 < len(line) and line[i + 1] == "|":
            commands.append((";", "".join(buf)))
            buf = []
            i += 2
            continue
        if char in "|;":
            commands.append((char, "".join(buf)))
            buf = []
            i += 1
            if char == "|" and i < len(line) and line[i] == "&":
                i += 1
            continue
        buf.append(char)
        i += 1
    commands.append((";", "".join(buf)))
    return commands


def words(command: str):
    try:
        return shlex.split(command, comments=False, posix=True)
    except ValueError:
        return []


def is_grep_quiet(command: str) -> bool:
    tokens = words(command)
    if not tokens or tokens[0].rsplit("/", 1)[-1] != "grep":
        return False
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token == "--":
            return False
        if token in ("--regexp", "--file"):
            i += 2  # Their next token is an argument, even when it begins with '-'.
            continue
        if token.startswith("--regexp=") or token.startswith("--file="):
            i += 1
            continue
        if token.startswith("--"):
            if token == "--quiet":
                return True
            i += 1
            continue
        if token.startswith("-") and token != "-":
            flags = token[1:]
            for offset, flag in enumerate(flags):
                if flag == "q":
                    return True
                if flag in ("e", "f"):
                    # -ePATTERN/-fFILE consume the rest of this token; bare -e/-f
                    # consume the next argv element, which may look like -q.
                    i += 1 if offset + 1 < len(flags) else 2
                    break
            else:
                i += 1
            continue
        i += 1
    return False


def enables_pipefail(command: str) -> bool | None:
    tokens = words(command)
    if not tokens or tokens[0] != "set":
        return None
    options = tokens[1:]
    for index, token in enumerate(options):
        if token == "+o" and index + 1 < len(options) and options[index + 1] == "pipefail":
            return False
        if token == "-o" and index + 1 < len(options) and options[index + 1] == "pipefail":
            return True
        if token.startswith("-") and not token.startswith("--") and "o" in token[1:]:
            # `set -euo pipefail` is accepted by Bash as set -e -u -o pipefail.
            if index + 1 < len(options) and options[index + 1] == "pipefail":
                return True
        if token.startswith("+") and not token.startswith("++") and "o" in token[1:]:
            if index + 1 < len(options) and options[index + 1] == "pipefail":
                return False
        if token == "pipefail" and any(opt.startswith("-") and "o" in opt[1:] for opt in options[:index]):
            return True
    return None


def lint_text(text: str, path: str):
    findings = []
    pipefail = False
    for line_number, line in logical_lines(text):
        chunks = split_commands(line)
        pipeline = []
        for delimiter, command in chunks:
            if delimiter == "|":
                pipeline.append(command)
                continue
            pipeline.append(command)
            if pipefail and len(pipeline) > 1:
                for downstream in pipeline[1:]:
                    if is_grep_quiet(downstream):
                        findings.append(
                            f"{path}:{line_number}: pipeline uses grep -q with pipefail; "
                            "the producer may receive SIGPIPE (141) on a match. "
                            "Use grep -c and inspect the count, or grep without -q "
                            "(redirect stdout to /dev/null)."
                        )
                        break
            for part in pipeline:
                setting = enables_pipefail(part)
                if setting is not None:
                    pipefail = setting
            pipeline = []
    return findings


def staged_shell_paths(repo: str):
    result = subprocess.run(
        ["git", "-C", repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR", "--", "*.sh", "*.bash"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [raw.decode("utf-8", "surrogateescape") for raw in result.stdout.split(b"\0") if raw]


def staged_blob(repo: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", repo, "show", ":" + path],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = argv[0] if argv else "."
    try:
        findings = []
        for path in staged_shell_paths(repo):
            data = staged_blob(repo, path)
            text = data.decode("utf-8", "replace")
            findings.extend(lint_text(text, path))
        for finding in findings:
            print("WARN: " + finding, file=sys.stderr)
    except Exception as exc:  # warn-only hook: incomplete scan cannot block a commit
        print(f"WARN: SIGPIPE grep -q scan skipped ({type(exc).__name__})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

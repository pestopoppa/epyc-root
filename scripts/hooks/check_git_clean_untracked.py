#!/usr/bin/env python3
"""PreToolUse guard for destructive `git clean`; agent-typed Bash scope only."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import strip_heredocs  # noqa: E402

OPS = {";", "&&", "||", "|", "&", "(", ")", ">", ">>", "<", "<<", "<<<", "\n"}


class GuardRefusal(Exception):
    pass


def _tokens(command: str) -> list[str]:
    # Keep newline as a punctuation separator (not whitespace); newlines inside
    # quoted strings remain part of one quoted token.
    lexer = shlex.shlex(strip_heredocs(command), posix=True,
                        punctuation_chars=";&|()<>\n")
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    lexer.commenters = "#"
    return list(lexer)


def _git_word(word: str) -> bool:
    return Path(word).name == "git"


def _find_clean(tokens: list[str]) -> tuple[int, int] | None:
    """Return git/clean positions only at an invocation boundary or unsafe wrapper."""
    wrappers = {"sudo", "command", "env", "time", "nohup", "nice", "stdbuf", "exec"}
    for part in _split_commands(tokens):
        if not part:
            continue
        first = part[0]
        # These shell control-flow/negation prefixes are not simple command
        # wrappers. If they directly prefix a Git clean invocation, surface it
        # so _parse_standalone refuses the framing instead of silently treating
        # the whole part as unrelated text. This is a conservative token check,
        # not a general Bash parser.
        control_prefixes = {"then", "do", "else", "elif", "if", "!"}
        prefix_end = 0
        while prefix_end < len(part) and part[prefix_end] in control_prefixes:
            prefix_end += 1
        if prefix_end and prefix_end < len(part) and _git_word(part[prefix_end]):
            j = prefix_end + 1
            if j < len(part) and part[j] == "-C":
                j += 2
            if j < len(part) and (part[j] == "clean" or
                                  (part[j].startswith("-") and "clean" in part[j + 1:])):
                return prefix_end, j if part[j] == "clean" else part.index("clean", j + 1)
        if first in wrappers:
            if first == "command" and len(part) > 1 and part[1] in ("-v", "-V"):
                continue
        elif first.startswith(("$", "`")):
            later = next((k for k, word in enumerate(part[1:], 1) if word == "clean"), None)
            if later is not None:
                return 0, later
        elif not _git_word(first) and not ("=" in first and not first.startswith("-")):
            # In particular, `echo 'git clean -ffdx'` is documentation.
            continue
        for i, token in enumerate(part):
            if not _git_word(token):
                continue
            j = i + 1
            if j < len(part) and part[j] == "-C":
                j += 2  # repo path; _parse_standalone validates it exists
            if j >= len(part):
                continue
            if part[j] == "clean":
                return i, j
            if part[j].startswith("-"):
                # Unsupported Git global options are never allowed to hide a
                # clean subcommand; _parse_standalone will refuse that framing.
                later = next((k for k in range(j + 1, len(part)) if part[k] == "clean"), None)
                if later is not None:
                    return i, later
    return None


def _split_commands(tokens: list[str]) -> list[list[str]]:
    out: list[list[str]] = [[]]
    for token in tokens:
        if token in OPS or "\n" in token:
            out.append([])
        else:
            out[-1].append(token)
    return [part for part in out if part]


def _shell_c_payloads(tokens: list[str]) -> list[str]:
    """Find command strings explicitly passed to common shell `-c` forms."""
    shells = {"bash", "sh", "dash", "zsh", "ksh"}
    payloads = []
    for part in _split_commands(tokens):
        if not part:
            continue
        command_name = Path(part[0]).name
        if command_name == "eval":
            if len(part) > 1:
                payloads.append(" ".join(part[1:]))
            continue
        if command_name not in shells:
            continue
        i = 1
        while i < len(part):
            arg = part[i]
            if arg == "--command":
                if i + 1 < len(part):
                    payloads.append(part[i + 1])
                break
            if arg.startswith("-") and "c" in arg[1:]:
                if i + 1 < len(part):
                    payloads.append(part[i + 1])
                break
            i += 1
    return payloads


def _command_substitution_payloads(text: str) -> list[str]:
    """Extract simple `$()` and backtick bodies, respecting quotes/escapes."""
    payloads: list[str] = []
    i = 0
    outer_quote: str | None = None
    while i < len(text):
        char = text[i]
        if char == "\\" and outer_quote != "'":
            i += 2
            continue
        if char in ("'", '"'):
            if outer_quote is None:
                outer_quote = char
            elif outer_quote == char:
                outer_quote = None
            i += 1
            continue
        if outer_quote == "'":
            i += 1
            continue
        if text.startswith("$(", i):
            start = i + 2
            j = start
            depth = 1
            inner_quote: str | None = None
            while j < len(text) and depth:
                c = text[j]
                if c == "\\" and inner_quote != "'":
                    j += 2
                    continue
                if c in ("'", '"'):
                    if inner_quote is None:
                        inner_quote = c
                    elif inner_quote == c:
                        inner_quote = None
                    j += 1
                    continue
                if inner_quote == "'":
                    j += 1
                    continue
                if text.startswith("$(", j):
                    depth += 1
                    j += 2
                    continue
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                j += 1
            if depth == 0:
                payloads.append(text[start:j - 1])
                i = j
                continue
        if char == "`":
            start = i + 1
            j = start
            while j < len(text):
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "`":
                    payloads.append(text[start:j])
                    i = j + 1
                    break
                j += 1
            else:
                i += 1
            continue
        i += 1
    return payloads


def _parse_standalone(tokens: list[str], base_cwd: str | None = None) -> tuple[Path, list[str], dict]:
    parts = _split_commands(tokens)
    clean_parts = []
    for part in parts:
        found = _find_clean(part)
        if found:
            clean_parts.append((part, found))
    if not clean_parts:
        raise LookupError("no git clean invocation")
    if len(clean_parts) != 1 or len(parts) != 1:
        raise GuardRefusal("compound shell framing around git clean is not inspected")
    words, (git_at, clean_at) = clean_parts[0]
    if git_at != 0 or not _git_word(words[git_at]):
        raise GuardRefusal("git clean is wrapped by another command or assignment")

    cwd = Path(base_cwd or Path.cwd()).resolve()
    at = 1
    if at < clean_at and words[at] == "-C":
        if at + 1 >= clean_at:
            raise GuardRefusal("git -C has no repository path")
        raw = Path(words[at + 1])
        cwd = (cwd / raw).resolve() if not raw.is_absolute() else raw.resolve()
        at += 2
    if at != clean_at:
        raise GuardRefusal("unsupported git global option before clean")

    flags = {"force": 0, "dry_run": False, "directories": False,
             "include_ignored": False, "ignored_only": False,
             "all_ignored": False,
             "pathspecs": [], "ambiguous": False}
    args = words[clean_at + 1:]
    i = 0
    after_dashdash = False
    while i < len(args):
        arg = args[i]
        if after_dashdash:
            flags["pathspecs"].append(arg)
            i += 1
            continue
        if arg == "--":
            after_dashdash = True
            i += 1
            continue
        if arg == "--dry-run":
            flags["dry_run"] = True
        elif arg == "--force":
            flags["force"] += 1
        elif arg in ("--quiet", "--no-quiet"):
            pass
        elif arg == "--directories":
            flags["directories"] = True
        elif arg == "--no-ignore":
            flags["include_ignored"] = True
            flags["all_ignored"] = True
        elif arg == "--ignored":
            flags["ignored_only"] = True
            flags["include_ignored"] = True
        elif arg in ("--exclude", "-e"):
            if i + 1 >= len(args):
                raise GuardRefusal("git clean exclude option has no value")
            i += 1
        elif arg.startswith("--"):
            raise GuardRefusal(f"unsupported git clean option: {arg}")
        elif arg.startswith("-") and arg != "-":
            for flag in arg[1:]:
                if flag == "f":
                    flags["force"] += 1
                elif flag == "n":
                    flags["dry_run"] = True
                elif flag == "d":
                    flags["directories"] = True
                elif flag == "x":
                    flags["include_ignored"] = True
                    flags["all_ignored"] = True
                elif flag == "X":
                    flags["ignored_only"] = True
                    flags["include_ignored"] = True
                elif flag == "q":
                    pass
                elif flag == "e":
                    if i + 1 >= len(args):
                        raise GuardRefusal("git clean -e has no value")
                    i += 1
                else:
                    raise GuardRefusal(f"unsupported git clean short option: -{flag}")
        else:
            # Git clean pathspecs are accepted only after `--`; bare operands
            # have ambiguous option/path meaning and must be made explicit.
            raise GuardRefusal("bare git clean operand; use -- before pathspecs")
        i += 1
    if flags["ignored_only"] and flags["all_ignored"]:
        raise GuardRefusal("combined -x/-X ignore modes are unsupported")
    return cwd, args, flags


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False, text=False, timeout=5)


def _porcelain_removables(raw: bytes, *, directories: bool, include_ignored: bool,
                           ignored_only: bool) -> list[bytes]:
    rows = [row for row in raw.split(b"\0") if row]
    found = []
    for row in rows:
        if len(row) < 4 or row[2:3] != b" ":
            raise GuardRefusal("git status emitted an unrecognized porcelain row")
        status, path = row[:2], row[3:]
        untracked = status == b"??"
        ignored = status == b"!!"
        if not (untracked or (include_ignored and ignored)):
            continue
        if ignored_only and not ignored:
            continue
        if not directories and path.endswith(b"/"):
            continue
        found.append(row)
    return found


def classify(command: str, *, cwd: str | None = None, run_git=_run_git,
             _depth: int = 0) -> tuple[str, str]:
    """Return (allow|block, reason). The injected runner is for safe unit tests."""
    if _depth > 4:
        return "block", "nested shell -c depth exceeds inspection limit"
    try:
        tokens = _tokens(command)
        source_text = strip_heredocs(command)
        for script in _shell_c_payloads(tokens) + _command_substitution_payloads(source_text):
            verdict, reason = classify(script, cwd=cwd, run_git=run_git, _depth=_depth + 1)
            if verdict == "block":
                return verdict, "nested shell -c: " + reason
        invocation = _find_clean(tokens)
        if invocation is None:
            return "allow", "no git clean command"
        repo, clean_args, flags = _parse_standalone(tokens, base_cwd=cwd)
        if flags["dry_run"]:
            return "allow", "git clean dry-run does not remove files"
        if flags["force"] == 0:
            config = run_git(repo, ["config", "--bool", "--get", "clean.requireForce"])
            if config.returncode == 1:
                require_force = True  # Git default.
            elif config.returncode == 0 and config.stdout.strip() in (b"true", b"false"):
                require_force = config.stdout.strip() == b"true"
            else:
                raise GuardRefusal("cannot establish effective clean.requireForce")
            if require_force:
                return "allow", "Git requires -f and this command has none"
        status_args = ["status", "--porcelain=v1", "-z",
                       "--untracked-files=all" if flags["directories"] else "--untracked-files=normal"]
        if flags["include_ignored"]:
            status_args.append("--ignored=matching")
        if flags["pathspecs"]:
            status_args.extend(["--", *flags["pathspecs"]])
        proc = run_git(repo, status_args)
        if proc.returncode != 0:
            raise GuardRefusal("read-only git status failed; refusing to guess")
        paths = _porcelain_removables(proc.stdout, directories=flags["directories"],
                                      include_ignored=flags["include_ignored"],
                                      ignored_only=flags["ignored_only"])
        if not flags["directories"] and flags["pathspecs"] and any(
                row[3:].endswith(b"/") for row in proc.stdout.split(b"\0") if row):
            raise GuardRefusal("directory pathspec with no -d has ambiguous clean reach")
        if paths:
            return "block", f"git clean could remove {len(paths)} untracked/ignored status row(s)"
        return "allow", "no removable untracked/ignored entries found"
    except LookupError:
        return "allow", "no git clean invocation"
    except (GuardRefusal, OSError, ValueError, subprocess.SubprocessError) as exc:
        return "block", str(exc)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"BLOCKED: hook input could not be read: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict) or not isinstance(payload.get("tool_input", {}), dict):
        print("BLOCKED: hook input has an unrecognized schema", file=sys.stderr)
        return 2
    if payload.get("tool_name") not in (None, "", "Bash"):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    try:
        raw_cwd = payload.get("cwd")
        if raw_cwd is None:
            # Preserve compatibility with hook envelopes that omit cwd; classify
            # then uses the hook process cwd as its base. When supplied, cwd must
            # be an absolute existing directory and is resolved before any probe.
            cwd = None
        elif not isinstance(raw_cwd, str) or not raw_cwd.strip():
            raise GuardRefusal("hook cwd must be a nonempty absolute directory")
        else:
            supplied = Path(raw_cwd)
            if not supplied.is_absolute():
                raise GuardRefusal("hook cwd must be absolute")
            try:
                cwd = supplied.resolve(strict=True)
            except OSError as exc:
                raise GuardRefusal("hook cwd cannot be resolved") from exc
            if not cwd.is_dir():
                raise GuardRefusal("hook cwd is not a directory")
        verdict, reason = classify(command, cwd=str(cwd) if cwd is not None else None)
    except Exception as exc:
        print(f"BLOCKED: clean guard failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if verdict == "block":
        print(f"BLOCKED: {reason}. This guard inspects agent-typed Bash only; inspect the paths and use an explicit reviewed workflow.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

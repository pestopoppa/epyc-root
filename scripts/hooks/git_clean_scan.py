#!/usr/bin/env python3
"""Classify an agent-typed Bash command for a `git clean` that would delete untracked work.

AUD-10 (operator decision 2026-11-02, decision tool, BRF-T5-2): re-land the narrow,
single-branch `git clean` guard from 03e17111. That commit's guard covered four revert
forms and was reverted at 3d8800e6 for two HIGHs in its OTHER branches; its
`git clean -f` branch was not among them, and with 149 untracked entries present it
would have refused the command that destroyed the corpus at 08:20Z on 2026-08-12.
Only that branch comes back. checkout / restore / reset --hard stay out of scope.

WHY CLEAN, AND WHY ONLY WHEN IT WOULD REMOVE SOMETHING
  Untracked work exists nowhere in git: no reflog, no stash, no object. A clean deletes
  it unrecoverably, and in a tree shared by several writers the files are often another
  session's in-flight work. A clean that removes NOTHING is harmless, so the guard does
  not decide from text: it ASKS GIT, running the same clean with `-n` (dry run) added,
  and refuses only when git answers "Would remove ...". -x, -X, -d, -e and pathspecs
  are therefore judged exactly as git would apply them.

THE REVERTED GUARD'S FRAMING DEFECT IS NOT REPEATED
  03e17111 tokenised with shlex.split, which does not split `a; b`, so `cd /tmp; git
  clean -f` sailed through (54889ea33 records the lesson). This scanner splits with the
  shared one-pass lexer (shell_scan.lex_text) and follows `cd`, `git -C`, subshell
  parentheses, loop bodies, wrappers (sudo/env/nohup/timeout/command) and `bash -c` /
  `sh -c` / `eval` strings.

VERDICTS (stdout, one line)
  allow
  block:clean-untracked:<repo>:<count>:<first entries, ;-joined>
  block:clean-unresolvable:<why>       a forcing clean whose tree the scanner cannot name
  scanner-error                        (detail on stderr)

OVERRIDE, carried over from 03e17111: `REVERT_VERIFIED=1 git clean ...` typed as a
leading assignment of the SAME simple command. It asserts the typist ran
`git clean -n` / `git status --short` and the files are theirs or backed up.

SCOPE, stated so a pass is never read wider than the instrument: models AGENT-TYPED
Bash only. A clean inside an invoked script, a heredoc fed to a shell, or a process
already running is outside its universe. `git -c clean.requireForce=false clean`
without -f IS treated as forcing.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import SEPARATORS, lex_text  # noqa: E402

OVERRIDE = "REVERT_VERIFIED"
_WRAPPERS = {"sudo", "env", "nohup", "nice", "ionice", "time", "command", "builtin",
             "exec", "timeout", "stdbuf", "xargs"}
_KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "}", "(", ")"}
_SHELLS = {"bash", "sh", "zsh", "dash"}
# git global options that take a separate value
_GIT_OPT_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                       "--exec-path", "--config-env"}
_CLEAN_OPT_WITH_VALUE = {"-e", "--exclude"}
_MAX_DEPTH = 4


def _unstand(word: str) -> str:
    """Undo shell_scan's private-use stand-ins and drop syntactic quote characters."""
    out = []
    for c in word:
        o = ord(c)
        if c in "'\"":
            continue
        out.append(chr(o - 0xE000) if 0xE000 <= o < 0xE080 else c)
    return "".join(out)


def _words(segment: str) -> list[str]:
    return [_unstand(w) for w in segment.split()]


def _assignment(word: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word))


def _resolve_dir(base: str | None, target: str) -> str | None:
    """Where a `cd`/`-C` lands, or None when the text cannot say (a variable, a substitution)."""
    if target == "~" or target.startswith("~/"):
        return os.path.normpath(os.path.expanduser(target))
    if "$" in target or "`" in target or target.startswith("~"):
        return None
    if os.path.isabs(target):
        return os.path.normpath(target)
    if base is None:
        return None
    return os.path.normpath(os.path.join(base, target))


def _git(repo: str, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                              timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None


def _clean_verdict(repo: str | None, git_conf: list[str], args: list[str]) -> str:
    """Judge one `git clean <args>` invocation in `repo`."""
    forced = False
    dry = False
    interactive = False
    passthrough: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            passthrough.extend(args[i:])
            break
        if a in _CLEAN_OPT_WITH_VALUE and i + 1 < len(args):
            passthrough.extend(args[i:i + 2])
            i += 2
            continue
        if a.startswith("--"):
            name = a.split("=", 1)[0]
            if name == "--force":
                forced = True
            elif name == "--dry-run":
                dry = True
            elif name == "--interactive":
                interactive = True
            passthrough.append(a)
        elif a.startswith("-") and len(a) > 1:
            body = a[1:]
            # -e<pattern> glued: the rest is the value
            if "e" in body:
                pre, _, _ = body.partition("e")
                letters = pre
            else:
                letters = body
            forced = forced or "f" in letters
            dry = dry or "n" in letters
            interactive = interactive or "i" in letters
            passthrough.append(a)
        else:
            passthrough.append(a)
        i += 1
    require_force_off = any(re.fullmatch(r"clean\.requireforce=(false|no|off|0)", c, re.I)
                            for c in git_conf)
    if dry or interactive or not (forced or require_force_off):
        return "allow"            # git itself removes nothing, or asks the human first
    if repo is None:
        return "block:clean-unresolvable:the working directory of this git clean is not resolvable"
    if not os.path.isdir(repo):
        return "allow"            # the clean will fail before it removes anything
    top = _git(repo, "rev-parse", "--show-toplevel")
    if top is None:
        return "scanner-error"
    if top.returncode != 0:
        return "allow"            # not a work tree: git clean refuses on its own
    conf_args: list[str] = []
    for c in git_conf:
        conf_args += ["-c", c]
    try:
        res = subprocess.run(["git", "-C", repo, *conf_args, "clean", *passthrough, "-n"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "scanner-error"
    if res.returncode != 0:
        return "scanner-error"
    victims = [ln[len("Would remove "):] for ln in res.stdout.splitlines()
               if ln.startswith("Would remove ")]
    if not victims:
        return "allow"
    shown = ";".join(victims[:5]) + (";..." if len(victims) > 5 else "")
    return f"block:clean-untracked:{top.stdout.strip()}:{len(victims)}:{shown}"


def classify(command: str, cwd: str | None, depth: int = 0) -> str:
    if depth > _MAX_DEPTH:
        return "allow"
    try:
        text = lex_text(command, keep_quoted=True)
    except Exception as exc:  # noqa: BLE001 - a lexer fault must not read as "allow"
        print(f"git_clean_scan: lexer failed: {exc!r}", file=sys.stderr)
        return "scanner-error"
    # `$(...)`, backticks and process substitution start a NEW command; quoted ones are
    # already stand-ins, so only real code is split here.
    text = re.sub(r"\$\(|`|<\(|>\(", "\n", text)
    state_cwd = cwd
    worst = "allow"
    for raw in SEPARATORS.split(text):
        words = _words(raw)
        # a subshell `( ... )` or brace group does not leak its cd, but tracking it
        # conservatively (as if it did) only ever resolves MORE cleans, never fewer
        while words and words[0] in _KEYWORDS:
            words.pop(0)
        while words and words[0].startswith("(") and len(words[0]) > 1:
            words[0] = words[0][1:]
        override = False
        while words and _assignment(words[0]):
            if words[0].split("=", 1)[0] == OVERRIDE and words[0].split("=", 1)[1] not in ("", "0"):
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
                v = classify(rest[idx + 1], state_cwd, depth + 1)
                worst = _worse(worst, v)
            continue
        if cmd == "eval" and rest:
            v = classify(" ".join(rest), state_cwd, depth + 1)
            worst = _worse(worst, v)
            continue
        if cmd != "git":
            continue
        repo = state_cwd
        git_conf: list[str] = []
        j = 0
        while j < len(rest) and rest[j].startswith("-"):
            opt = rest[j]
            if opt in _GIT_OPT_WITH_VALUE and j + 1 < len(rest):
                val = rest[j + 1]
                if opt == "-C":
                    repo = _resolve_dir(repo, val)
                elif opt == "-c":
                    git_conf.append(val)
                elif opt == "--work-tree":
                    repo = _resolve_dir(repo, val)
                j += 2
                continue
            if opt.startswith("--work-tree="):
                repo = _resolve_dir(repo, opt.split("=", 1)[1])
            j += 1
        if j >= len(rest) or rest[j] != "clean":
            continue
        if override:
            continue
        worst = _worse(worst, _clean_verdict(repo, git_conf, rest[j + 1:]))
    return worst


_RANK = {"allow": 0, "scanner-error": 1}


def _worse(a: str, b: str) -> str:
    def rank(v: str) -> int:
        if v.startswith("block:"):
            return 2
        return _RANK.get(v, 1)
    return b if rank(b) > rank(a) else a


def main() -> int:
    command = sys.stdin.read()
    if not command.strip():
        print("error: empty command — refusing to emit a verdict", file=sys.stderr)
        return 2
    cwd = os.environ.get("HOOK_CWD") or os.getcwd()
    print(classify(command, cwd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

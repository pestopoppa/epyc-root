#!/usr/bin/env python3
"""Destructive-scratch scanner for the PreToolUse Bash hook check_destructive_scratch.sh.

PURPOSE
  Refuse a Bash command that RECURSIVELY or INLINE-SCRIPT deletes under the protected
  scratch roots (/mnt/raid0/llm/tmp, /worktrees, /.trash, /state) without going through the
  sanctioned, trash-first tools (scripts/safety/guarded_rm.sh and friends).

ORIGIN
  2026-10-20 E2 purge: purge_batch.py shutil.rmtree'd the trash batch 20 s-2 min after
  guarded_rm moved it there, so "trash first" protected nothing. 244 real tmp losses were
  reconciled 2026-10-25 (docs/reference/tmp-loss-reconcile-2026-10-25.md section 2 and
  section 6 guard 5, NIB2-108).

REFUSES (only when a target / string literal resolves under a protected root)
  rm with a recursive flag; find ... -delete / -exec rm; rmdir of an existing NON-EMPTY dir;
  shutil.rmtree / os.unlink / os.remove / os.rmdir / .unlink( / .rmdir( inside python -c or a
  heredoc fed to python/bash/sh; and for `python3 FILE` / `bash FILE`, the same primitives
  found in FILE's contents (<= 2 MiB) together with a protected-root string literal.
ALLOWS
  sanctioned tools (guarded_rm.sh, trash-sweep.sh, reclaim_scratch.py, scratch_cleanup.py,
  worktree_gate.py, autokernel_disk_sweep.py) by basename, contents NOT scanned; bare /tmp/**
  and the session scratchpad; rm of a mktemp-derived target (the guard's own test idiom);
  plain non-recursive `rm file`; mentions of the words (grep -r rmtree ...).
  FAIL-OPEN on what cannot be parsed or resolved (unknown $VAR, unreadable file): the
  hygiene-tick backstop (guards-design section 2.8) covers those. A literal protected
  prefix followed by a variable (/mnt/raid0/llm/tmp/$X) IS refused.
OVERRIDE
  env EPYC_ALLOW_SCRATCH_DELETE="operator: <who> <date>: <reason>" (read from the HOOK's
  environment, so a command cannot self-authorize by embedding the text).
TEST-ONLY KNOB
  EPYC_DESTRUCTIVE_SCRATCH_ROOTS=colon:separated:roots replaces the protected-root list so
  tests can use mktemp dirs. Never set it in production.
LIMITS
  Cannot see deletes inside processes already running, files it cannot read, code fetched
  or built at run time, or dataflow (a script that deletes a path computed elsewhere).

CLI: command text on stdin; exit 0 = allow, exit 2 = refuse (reason on stderr).
"""
from __future__ import annotations

import os
import re
import shlex
import sys

DEFAULT_ROOTS = ("/mnt/raid0/llm/tmp", "/mnt/raid0/llm/worktrees",
                 "/mnt/raid0/llm/.trash", "/mnt/raid0/llm/state")
SANCTIONED = {"guarded_rm.sh", "trash-sweep.sh", "reclaim_scratch.py", "scratch_cleanup.py",
              "worktree_gate.py", "autokernel_disk_sweep.py"}
# Standing operator exceptions: ONE exact script realpath, pinned to its sha256, run as `bash|python3 <path>`.
# Narrowest form: no basename match, no directory match; any edit to the script voids it (re-pin = new operator approval).
# The table lives in destructive_scratch_pins.json next to this file (human-edited, operator approval per entry):
#   {"<realpath>": {"sha256": "<hex>", "approval": "operator <date>: <reason>"}}
def _load_pins():
    import json
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "destructive_scratch_pins.json")) as f:
            d = json.load(f)
        return {k: (v["sha256"], v["approval"]) for k, v in d.items() if isinstance(v, dict)}
    except (OSError, ValueError, KeyError, TypeError):
        return {}
PINNED_SCRIPTS = _load_pins()
ACK_ENV = "EPYC_ALLOW_SCRATCH_DELETE"
ACK_RE = re.compile(r"^operator: \S+ \S+: \S.*$")
MAX_FILE = 2 * 1024 * 1024
FIX = ("trash via scripts/safety/guarded_rm.sh <exact path> (OPERATING_CONSTRAINTS.md -> "
       "Destructive operations), or set EPYC_ALLOW_SCRATCH_DELETE='operator: <who> <date>: <reason>'")

PRIMITIVE = re.compile(
    r"\bshutil\.rmtree\b|\brmtree\s*\(|\bos\.(?:unlink|remove|rmdir|removedirs)\s*\("
    r"|\.(?:unlink|rmdir)\s*\("
    r"|(?<![\w./-])rm\s+(?:-[A-Za-z]*[rR][A-Za-z]*|--recursive)\b"
    r"|\bfind\b[^\n]*\s-delete\b|\bfind\b[^\n]*-exec\s+rm\b")
INTERP = re.compile(r"^(python[0-9.]*|bash|sh|dash|zsh)$")


def roots() -> list[str]:
    env = os.environ.get("EPYC_DESTRUCTIVE_SCRATCH_ROOTS")
    raw = [r for r in env.split(":") if r] if env else list(DEFAULT_ROOTS)
    out: list[str] = []
    for r in raw:
        for v in (r.rstrip("/"), os.path.realpath(r)):
            if v not in out:
                out.append(v)
    return out


def under(path: str, rs: list[str]) -> str | None:
    for r in rs:
        if path == r or path.startswith(r + "/"):
            return r
    return None


def root_literals(text: str, rs: list[str]) -> list[str]:
    hits = []
    for r in rs:
        if re.search(re.escape(r) + r"(?![\w.-])", text):
            hits.append(r)
    return hits


def split_commands(cmd: str):
    """Quote-aware split on ; && || | newline. Returns (segments, heredocs).

    heredocs: list of (segment_text_with_marker, body).
    """
    segs: list[str] = []
    heredocs: list[tuple[str, str]] = []
    lines = cmd.split("\n")
    i = 0
    pending: list[tuple[str, str, int]] = []
    cur_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        cur_lines.append(line)
        marks = re.findall(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        i += 1
        for _, term in marks:
            body = []
            while i < len(lines) and lines[i].strip() != term:
                body.append(lines[i])
                i += 1
            i += 1
            heredocs.append((line, "\n".join(body)))
    text = "\n".join(cur_lines)
    buf, q, k, n = [], None, 0, len(text)
    while k < n:
        c = text[k]
        if q:
            buf.append(c)
            if c == "\\" and q == '"' and k + 1 < n:
                buf.append(text[k + 1]); k += 1
            elif c == q:
                q = None
        elif c in "'\"":
            q = c; buf.append(c)
        elif c == "\\" and k + 1 < n:
            buf.append(c); buf.append(text[k + 1]); k += 1
        elif c in ";|&\n" and not (c == "&" and (text[k + 1:k + 2] not in ("&",) and text[k - 1:k] in (">", "<"))):
            if c == "&" and text[k + 1:k + 2] != "&":
                pass  # background '&' also separates
            segs.append("".join(buf)); buf = []
            while k + 1 < n and text[k + 1] in ";|&":
                k += 1
        else:
            buf.append(c)
        k += 1
    segs.append("".join(buf))
    return [s.strip() for s in segs if s.strip()], heredocs


def tokens_of(seg: str) -> list[str]:
    try:
        return shlex.split(seg, comments=False, posix=True)
    except ValueError:
        return seg.split()


def resolve(tok: str, cwd: str, env: dict[str, str]):
    """Return ('path', abs) | ('opaque', None). Expands known literal assignments."""
    def sub(m):
        name = m.group(1) or m.group(2)
        return env.get(name, m.group(0))
    t = re.sub(r"\$\{(\w+)\}|\$(\w+)", sub, tok)
    if t.startswith("~"):
        t = os.path.expanduser(t)
    if t.startswith("$") or t.startswith("`"):
        return "opaque", None  # starts with unknown var / substitution: fail-open
    lit = re.split(r"[$`]", t, maxsplit=1)
    has_var = len(lit) > 1
    base = lit[0]
    if not base.startswith("/"):
        base = os.path.join(cwd, base)
    if has_var and not base.endswith("/"):
        base = base  # partial component; normalise what we have
    p = os.path.normpath(base) if base else cwd
    return "path", os.path.realpath(p)


def check_targets(targets, cwd, env, rs, what):
    for tok in targets:
        kind, p = resolve(tok, cwd, env)
        if kind != "path":
            continue
        r = under(p, rs)
        if r:
            return f"{what} target '{tok}' resolves under protected root {r}"
    return None


def scan_text(text: str, rs: list[str], origin: str):
    if PRIMITIVE.search(text):
        hits = root_literals(text, rs)
        if hits:
            return f"{origin} contains a delete primitive and names protected root {hits[0]}"
    return None


def scan_segment(seg, cwd, env, rs, state):
    toks = tokens_of(seg)
    # leading assignments
    while toks and re.match(r"^[A-Za-z_]\w*=", toks[0]):
        name, _, val = toks[0].partition("=")
        if "$(" in val or "`" in val or val.startswith("$"):
            env.pop(name, None)
        else:
            env[name] = val
        toks.pop(0)
    while toks and toks[0] in ("sudo", "nohup", "time", "exec", "command", "builtin", "nice", "ionice", "xargs", "timeout", "env"):
        toks.pop(0)
        while toks and (toks[0].startswith("-") or re.match(r"^\d+[smh]?$", toks[0]) or re.match(r"^[A-Za-z_]\w*=", toks[0])):
            toks.pop(0)
    if not toks:
        return None
    if toks[0] == "cd" and len(toks) > 1 and toks[1].startswith("/"):
        state["cwd"] = toks[1]
        return None
    cmd = os.path.basename(toks[0])
    args = toks[1:]
    if cmd in SANCTIONED:
        return None
    if INTERP.match(cmd):
        # sanctioned script as first non-flag arg
        nonflag = [a for a in args if not a.startswith("-")]
        if "-c" in args:
            i = args.index("-c")
            if i + 1 < len(args):
                return scan_text(args[i + 1], rs, "inline -c script")
            return None
        if nonflag:
            script = nonflag[0]
            if os.path.basename(script) in SANCTIONED:
                return None
            path = script if os.path.isabs(script) else os.path.join(state["cwd"], script)
            pin = PINNED_SCRIPTS.get(os.path.realpath(path))
            if pin:
                try:
                    import hashlib
                    with open(path, "rb") as f:
                        if hashlib.sha256(f.read()).hexdigest() == pin[0]:
                            print(f"note: pinned exception: {pin[1]}", file=sys.stderr)
                            return None
                except OSError:
                    pass  # unreadable: fall through to the normal scan
            try:
                if os.path.isfile(path) and os.path.getsize(path) <= MAX_FILE:
                    with open(path, "r", errors="replace") as f:
                        return scan_text(f.read(), rs, f"script file {script}")
            except OSError:
                return None
        return None
    if cmd == "rm":
        recursive = any(
            a == "--recursive" or (a.startswith("-") and not a.startswith("--") and re.search(r"[rR]", a))
            for a in args if a != "--")
        if not recursive:
            return None
        tg = [a for a in args if not a.startswith("-") or a == "-"]
        return check_targets(tg, state["cwd"], env, rs, "recursive rm")
    if cmd == "find":
        if "-delete" in args or any(a == "-exec" and i + 1 < len(args) and os.path.basename(args[i + 1]) == "rm"
                                    for i, a in enumerate(args)):
            tg = []
            for a in args:
                if a.startswith("-") or a in ("(", "!"):
                    break
                tg.append(a)
            return check_targets(tg or ["."], state["cwd"], env, rs, "find -delete/-exec rm")
        return None
    if cmd == "rmdir":
        for a in args:
            if a.startswith("-"):
                continue
            kind, p = resolve(a, state["cwd"], env)
            if kind == "path" and under(p, rs) and os.path.isdir(p) and os.listdir(p):
                return f"rmdir target '{a}' is a NON-EMPTY dir under a protected root"
        return None
    return None


def scan(cmd: str):
    rs = roots()
    segs, heredocs = split_commands(cmd)
    env: dict[str, str] = {}
    state = {"cwd": os.getcwd()}
    for line, body in heredocs:
        # heredoc fed to an interpreter (python3 - <<EOF, bash <<EOF) is an inline script
        for part in re.split(r"&&|\|\||[;|]", line):
            t = tokens_of(part.split("<<")[0])
            while t and re.match(r"^[A-Za-z_]\w*=", t[0]):
                t.pop(0)
            if t and INTERP.match(os.path.basename(t[0])):
                if len(t) > 1 and os.path.basename(t[1]) in SANCTIONED:
                    continue
                r = scan_text(body, rs, "heredoc script")
                if r:
                    return r
    for seg in segs:
        seg = re.sub(r"<<-?\s*(['\"]?)[A-Za-z_]\w*\1", "", seg)
        r = scan_segment(seg, state["cwd"], env, rs, state)
        if r:
            return r
    return None


def main() -> int:
    ack = os.environ.get(ACK_ENV, "").strip()
    cmd = sys.stdin.read()
    if not cmd.strip():
        return 0
    if ack:
        if ACK_RE.match(ack):
            print(f"note: {ACK_ENV} override recorded: {ack}", file=sys.stderr)
            return 0
        print(f"note: {ACK_ENV} set but not of the form 'operator: <who> <date>: <reason>'; ignored",
              file=sys.stderr)
    reason = scan(cmd)
    if reason is None:
        return 0
    print(f"BLOCKED: destructive scratch delete (2026-10-20 E2 purge; NIB2-108). {reason}.\n"
          f"Rule: recursive/inline deletes under /mnt/raid0/llm/{{tmp,worktrees,.trash,state}} are refused.\n"
          f"Sanctioned route: {FIX}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail open: the hygiene-tick backstop covers what we cannot parse
        print(f"destructive_scratch_scan: internal error {e!r}; allowing", file=sys.stderr)
        sys.exit(0)

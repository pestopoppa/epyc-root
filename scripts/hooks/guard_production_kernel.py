#!/usr/bin/env python3
"""PreToolUse(Bash|Write|Edit) hook: the production kernel set is operator-only (operator-approved 2026-11-18).

DENIES (exit 2, one line, cause + fix):
  * Write/Edit of a file under /mnt/raid0/llm/kernels/production/ or /mnt/raid0/llm/kernels/builds/*-ffc1bac82*;
  * Bash that writes, symlinks, moves, deletes or chmods there (cp/mv/rm/ln/chmod/chown/install/rsync/tee/touch/
    mkdir/rmdir/truncate/unlink/sed -i, or a `>` redirect onto such a path);
  * Bash git commit/push/rebase/reset/merge/`branch -f` against production-consolidated-* in the llama.cpp tree, or
    production-speech-* in whisper.cpp / qwentts.cpp (branch named in the command, or the tree's checked-out branch).
ALLOWS everything else (read-only ls/readlink/stat/verify_*.sh pass), and allows a denied action only while
<flags>/operator-ratify/production-kernel.json exists with by/at/reason/version and `at` is under 24 h old.
Malformed input passes (the hook never blocks on its own bug). Flags dir: ROWFLOW_FLAGS.
"""
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys

FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")
RATIFY = os.path.join(FLAGS, "operator-ratify", "production-kernel.json")
RATIFY_MAX_AGE_S = 24 * 3600
PROTECTED_PATH = re.compile(r"/mnt/raid0/llm/kernels/(production(/|$|\b)|builds/[^/\s'\"]*-ffc1bac82)")
TREES = {"/mnt/raid0/llm/llama.cpp": re.compile(r"production-consolidated-"),
         "/mnt/raid0/llm/whisper.cpp": re.compile(r"production-speech-"),
         "/mnt/raid0/llm/qwentts.cpp": re.compile(r"production-speech-")}
MUTATORS = {"cp", "mv", "rm", "ln", "chmod", "chown", "chgrp", "install", "rsync", "tee", "touch", "mkdir", "rmdir",
            "truncate", "unlink", "shred", "dd"}
GIT_MUTATORS = {"commit", "push", "rebase", "reset", "merge"}
SEP = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")


def ratified(now=None):
    try:
        with open(RATIFY) as f:
            d = json.load(f)
        if not isinstance(d, dict) or any(not str(d.get(k) or "").strip() for k in ("by", "at", "reason", "version")):
            return False
        at = dt.datetime.fromisoformat(str(d["at"]).replace("Z", "+00:00"))
        if at.tzinfo is None:
            at = at.replace(tzinfo=dt.timezone.utc)
        age = (now or dt.datetime.now(dt.timezone.utc)) - at
        return 0 <= age.total_seconds() < RATIFY_MAX_AGE_S
    except (OSError, ValueError, TypeError):
        return False


def protected_path(p):
    if not p:
        return False
    return bool(PROTECTED_PATH.search(p) or PROTECTED_PATH.search(os.path.realpath(p)))


def tree_of(path):
    try:
        rp = os.path.realpath(path)
    except (OSError, ValueError):
        return None
    for t in TREES:
        if rp == t or rp.startswith(t + "/"):
            return t
    return None


def current_branch(tree):
    try:
        r = subprocess.run(["git", "-C", tree, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def words(seg):
    try:
        w = shlex.split(seg, comments=True)
    except ValueError:
        w = seg.split()
    while w and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w[0]) or w[0] in ("sudo", "env", "command", "nohup", "time")):
        w = w[1:]
    return w


def bash_violation(cmd, cwd, branch_of=current_branch):
    if re.search(r">>?\s*['\"]?(/mnt/raid0/llm/kernels/\S+)", cmd):
        for m in re.finditer(r">>?\s*['\"]?(/mnt/raid0/llm/kernels/[^\s'\"]+)", cmd):
            if protected_path(m.group(1)):
                return f"redirect onto production kernel path {m.group(1)}"
    here = cwd
    for seg in SEP.split(cmd):
        w = words(seg)
        if not w:
            continue
        if w[0] == "cd" and len(w) > 1:
            here = os.path.join(here or "/", w[1])
            continue
        base = os.path.basename(w[0])
        args = w[1:]
        if base in MUTATORS or (base == "sed" and any(a.startswith("-i") for a in args)):
            hit = next((a for a in args if protected_path(a)), None)
            if hit:
                return f"`{base}` on production kernel path {hit}"
        if base == "git":
            tree, i = here, 0
            while i < len(args) and args[i].startswith("-"):
                if args[i] == "-C" and i + 1 < len(args):
                    tree = os.path.join(tree or "/", args[i + 1])
                    i += 2
                    continue
                i += 1 if args[i] != "-c" else 2
            sub = args[i] if i < len(args) else ""
            rest = args[i + 1:]
            if sub not in GIT_MUTATORS and not (sub == "branch" and any(a in ("-f", "--force", "-M", "-D") for a in rest)):
                continue
            t = tree_of(tree) if tree else None
            if not t:
                continue
            pat = TREES[t]
            named = [a for a in rest if pat.search(a)]
            br = branch_of(t)
            if named or (br and pat.search(br) and sub != "branch"):
                return f"`git {sub}` against frozen branch {(named or [br])[0]} in {t}"
    return None


def verdict(payload, branch_of=current_branch):
    tool = payload.get("tool_name")
    ti = payload.get("tool_input") or {}
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = ti.get("file_path") or ti.get("notebook_path") or ""
        why = f"{tool} of production kernel path {p}" if protected_path(p) else None
    elif tool == "Bash":
        why = bash_violation(str(ti.get("command") or ""), payload.get("cwd") or os.getcwd(), branch_of)
    else:
        why = None
    if not why or ratified():
        return None
    return (f"BLOCKED (production kernel is FROZEN, operator-only): {why}. Only the operator may ratify this: "
            f"{RATIFY} with by/at/reason/version, at < 24 h old.")


def main():
    try:
        payload = json.load(sys.stdin)
        v = verdict(payload)
    except Exception:
        return 0
    if v:
        print(v, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

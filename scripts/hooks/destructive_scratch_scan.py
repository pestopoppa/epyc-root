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

REFUSES (only when an invoked delete's target resolves under a protected root)
  rm with a recursive flag; find ... -delete / -exec rm; rmdir of an existing NON-EMPTY dir;
  shutil.rmtree / os.unlink / os.remove / os.rmdir / .unlink( / .rmdir( inside python -c or a
  heredoc fed to python/bash/sh; and for `python3 FILE` / `bash FILE`, the same primitives
  found as invocations in FILE's contents (<= 2 MiB). Python is inspected with
  ast; shell source is inspected as commands. Comments and data are not deletes.
ALLOWS
  sanctioned tools (guarded_rm.sh, trash-sweep.sh, reclaim_scratch.py, scratch_cleanup.py,
  worktree_gate.py, autokernel_disk_sweep.py) by basename, contents NOT scanned; bare /tmp/**
  and the session scratchpad; rm of a mktemp-derived target (the guard's own test idiom);
  plain non-recursive `rm file`; mentions of the words (grep -r rmtree ...).
  A HOOK-environment EPYC_TEST_TMP + EPYC_TEST_TMP_ID=DEV:INO:UID declaration
  permits recursive rm of that exact owned directory, after identity validation.
  No descendant, traversal, trailing-slash, find or language-wide exemption.
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
import stat

from destructive_scratch_python import scan_python
from destructive_scratch_shell import mask_substitutions

DEFAULT_ROOTS = ("/mnt/raid0/llm/tmp", "/mnt/raid0/llm/worktrees",
                 "/mnt/raid0/llm/.trash", "/mnt/raid0/llm/state")
SANCTIONED = {"guarded_rm.sh", "trash-sweep.sh", "reclaim_scratch.py", "scratch_cleanup.py",
              "worktree_gate.py", "autokernel_disk_sweep.py"}
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
    text, substitutions = mask_substitutions("\n".join(cur_lines))
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
        elif (c in ";|&\n" or (c in "{}" and (k == 0 or text[k - 1].isspace())
                               and (k + 1 == n or text[k + 1].isspace()))) and not (c == "&" and (text[k + 1:k + 2] not in ("&",) and text[k - 1:k] in (">", "<"))):
            if c == "&" and text[k + 1:k + 2] != "&":
                pass  # background '&' also separates
            segs.append("".join(buf)); buf = []
            while k + 1 < n and text[k + 1] in ";|&":
                k += 1
        else:
            buf.append(c)
        k += 1
    segs.append("".join(buf))
    return [restore_substitutions(s.strip(), substitutions) for s in segs if s.strip()], heredocs


def tokens_of(seg: str) -> list[str]:
    masked, replacements = mask_substitutions(seg)
    try:
        lex = shlex.shlex(masked, posix=True)
        lex.whitespace_split = True
        lex.commenters = "#"
        toks = []
        while True:
            start = lex.instream.tell()
            token = lex.get_token()
            if token is None:
                break
            raw = masked[start:lex.instream.tell()].strip()
            word = ShellWord(restore_substitutions(token, replacements))
            word.quoted = raw == '"' + token + '"'
            word.literal = raw == "'" + token + "'"
            toks.append(word)
    except ValueError:
        toks = masked.split()
    return toks


class ShellWord(str):
    quoted = False
    literal = False


def restore_substitutions(text, replacements):
    for marker, expression, _ in replacements:
        text = text.replace(marker, expression)
    return text


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


def check_targets(targets, cwd, env, rs, what, state):
    for tok in targets:
        ref = re.fullmatch(r"\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))", tok)
        name = (ref.group(1) or ref.group(2)) if ref else None
        literal = getattr(tok, "literal", False)
        if literal:
            name = None
        if name in state["temps"]:
            if not getattr(tok, "quoted", False):
                return f"{what}: a mktemp cleanup must quote its exact directory variable"
            if what != "recursive rm":
                return f"{what}: the ephemeral-root exemption only permits recursive rm"
            # Exact root only: rm does not follow child symlinks. Descendant,
            # trailing-slash, glob and traversal forms get no such exemption.
            continue
        refs = set(re.findall(r"\$(?:\{([A-Za-z_]\w*)[^}]*\}|([A-Za-z_]\w*))", tok)) if not literal else set()
        names = {a or b for a, b in refs}
        if names & (state["temps"] | state["lost_temps"]):
            return f"{what} must target the exact, still-bound mktemp directory: '{tok}'"
        if not literal and is_mktemp_dir(tok):
            if not getattr(tok, "quoted", False):
                return f"{what}: a mktemp cleanup must quote its exact substitution"
            if state["complex"]:
                return f"{what}: mktemp provenance is ambiguous after shell control or environment changes"
            if what != "recursive rm":
                return f"{what}: the ephemeral-root exemption only permits recursive rm"
            continue
        _, expressions = mask_substitutions(tok) if not literal else (tok, [])
        if any(is_mktemp_dir(expression) for _, expression, _ in expressions):
            return f"{what} must target exactly the newly-created directory, without a suffix"
        if literal:
            kind = "path"
            p = os.path.realpath(tok if os.path.isabs(tok) else os.path.join(cwd, tok))
        else:
            kind, p = resolve(tok, cwd, env)
        if "EPYC_TEST_TMP" in names and name != "EPYC_TEST_TMP" and "EPYC_TEST_TMP" in env:
            return f"{what}: declared test-root cleanup requires the exact directory variable"
        if kind != "path":
            continue
        declared = state.get("declared_temp")
        # The declaration comes from the HOOK environment, never this command.
        # Recheck the identity immediately before granting the narrow exemption.
        if what == "recursive rm" and declared and p == declared and valid_declared_temp(rs) == declared:
            if os.path.abspath(tok) == declared or (name == "EPYC_TEST_TMP" and getattr(tok, "quoted", False)):
                continue
        r = under(p, rs)
        if r:
            return f"{what} target '{tok}' resolves under protected root {r}"
    return None


def is_mktemp_dir(value: str) -> bool:
    """Recognize only mktemp's directory-creation forms, never --dry-run/-u.

    Unknown options, shell operators, extra substitutions and relative templates
    are deliberately unsupported. This is provenance, not a path allowlist.
    """
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    if not (value.startswith("$(") and value.endswith(")")):
        return False
    body = value[2:-1]
    if re.search(r"[;$`\n|&<>]", body) or "$" in body or "(" in body or ")" in body:
        return False
    try:
        args = shlex.split(body)
    except ValueError:
        return False
    if not args or args.pop(0) not in ("mktemp", "/usr/bin/mktemp", "/bin/mktemp"):
        return False
    if not args or args.pop(0) not in ("-d", "--directory"):
        return False
    if not args:
        return True
    if len(args) != 1:
        return False
    template = args[0]
    return (template.startswith("/") and bool(re.fullmatch(r"/[A-Za-z0-9_./-]*X{6,}", template))
            and ".." not in template.split("/"))


def declared_forbidden_roots():
    paths = ("/workspace", "/workspace/kernels", "/mnt/raid0/llm/kernels",
             "/mnt/raid0/llm/models", "/mnt/raid0/llm/lmstudio",
             "/mnt/raid0/llm/llama.cpp", "/mnt/raid0/llm/whisper.cpp",
             "/mnt/raid0/llm/qwentts.cpp", "/mnt/raid0/llm/epyc-root",
             "/mnt/raid0/llm/epyc-orchestrator", "/mnt/raid0/llm/epyc-inference-research",
             "/mnt/raid0/llm/epyc-web")
    return [os.path.realpath(p) for p in paths]


def valid_declared_temp(rs):
    """Trusted test-launcher declaration, bound to one existing directory inode.

    EPYC_TEST_TMP_ID is DEV:INO:UID from stat. Both values must be exported to
    the hook by its launcher. A command-local assignment cannot authorize itself.
    Reject ancestors, protected roots themselves, aliases and symlink components.
    """
    p = os.environ.get("EPYC_TEST_TMP", "")
    identity = os.environ.get("EPYC_TEST_TMP_ID", "")
    if not p or not os.path.isabs(p) or p != os.path.normpath(p) or os.path.realpath(p) != p:
        return None
    # In production only tmp is a permitted test base: no worktree, state or
    # trash declaration. The test-only roots knob keeps fixtures off host data.
    bases = rs if os.environ.get("EPYC_DESTRUCTIVE_SCRATCH_ROOTS") else [os.path.realpath(DEFAULT_ROOTS[0])]
    root = under(p, bases)
    if root is None or p == root:
        return None
    forbidden = declared_forbidden_roots()
    if under(p, forbidden) or any(under(f, [p]) for f in forbidden):
        return None
    ancestor = p
    while True:
        if os.path.lexists(os.path.join(ancestor, ".git")):
            return None
        parent = os.path.dirname(ancestor)
        if parent == ancestor:
            break
        ancestor = parent
    # Also reject a declared parent containing a repository. This bounded,
    # non-following walk denies the exemption on unreadable/large trees.
    errors = []
    count = 0
    for _, directories, files in os.walk(p, followlinks=False, onerror=errors.append):
        count += len(directories) + len(files)
        if ".git" in directories or ".git" in files or count > 4096:
            return None
    if errors:
        return None
    try:
        st = os.stat(p, follow_symlinks=False)
    except OSError:
        return None
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or identity != f"{st.st_dev}:{st.st_ino}:{st.st_uid}"):
        return None
    return p


def scan_text(text: str, rs: list[str], origin: str, language: str, env, state):
    if state["depth"] >= 8:
        return None  # Same fail-open boundary as unreadable / unparseable scripts.
    child = dict(state, depth=state["depth"] + 1,
                 temps=set(state["temps"]), lost_temps=set(state["lost_temps"]), traps=[])
    if language.startswith("python"):
        return scan_python(text, rs, origin,
                           lambda s: scan_shell(s, rs, dict(env), dict(child)))
    return scan_shell(text, rs, dict(env), child)


def scan_segment(seg, cwd, env, rs, state):
    # Substitutions execute even in otherwise harmless echo/printf arguments.
    # Single-quoted text is omitted by mask_substitutions.
    _, substitutions = mask_substitutions(seg)
    for _, _, body in substitutions:
        reason = scan_text(body, rs, "command substitution", "sh", env, state)
        if reason:
            return reason
    # Preserve command substitution as a whole before shlex splits its spaces.
    # Only assignment-only commands may establish fresh-directory provenance.
    assignment = re.fullmatch(r"(?:export\s+)?([A-Za-z_]\w*)=(.*)", seg, re.S)
    if assignment and is_mktemp_dir(assignment.group(2).strip()):
        name = assignment.group(1)
        env.pop(name, None)
        if state["complex"]:
            state["temps"].discard(name)
            state["lost_temps"].add(name)
        else:
            state["temps"].add(name)
            state["lost_temps"].discard(name)
        return None
    toks = tokens_of(seg)
    # Do not infer unconditional provenance from shell control flow. Existing
    # known literals still participate in the ordinary protected-root check.
    if toks and toks[0] in ("if", "then", "else", "elif", "fi", "for", "while", "until",
                            "do", "done", "case", "esac", "function", "{", "}"):
        state["complex"] = True
    if toks and toks[0].endswith("()"):
        state["complex"] = True
    while toks and toks[0] in ("if", "elif", "while", "until", "then", "else", "do", "{", "}", "!"):
        toks.pop(0)
    if toks and toks[0] == "export":
        toks.pop(0)
    # leading assignments
    while toks and re.match(r"^[A-Za-z_]\w*=", toks[0]):
        name, _, val = toks[0].partition("=")
        if name == "PATH":
            state["complex"] = True
        if name in state["temps"]:
            state["temps"].remove(name)
            state["lost_temps"].add(name)
        if "mktemp" in val and ("$(" in val or "`" in val):
            # A noncanonical / conditional / inline assignment cannot establish
            # unconditional provenance. Keep it opaque but deny the exemption.
            state["lost_temps"].add(name)
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
    # Rebinding builtins invalidate the bindings they can write. Dynamic
    # source/alias/eval and nameref/callback forms invalidate every new proof.
    # A harmless `read l` must not revoke a different mktemp binding: the
    # original 37-case harness uses that idiom while retaining its own TMP.
    rebinding = cmd in ("read", "declare", "local", "readonly", "typeset", "mapfile", "readarray")
    printf_v = cmd == "printf" and any(a == "-v" or a.startswith("-v") for a in args)
    dynamic = cmd in ("alias", "source", ".", "eval")
    if rebinding or printf_v or dynamic:
        state["complex"] = True
        names = set()
        if printf_v:
            i = next(i for i, a in enumerate(args) if a == "-v" or a.startswith("-v"))
            candidates = [args[i][2:]] if args[i] != "-v" else args[i + 1:i + 2]
        else:
            candidates = args
        if cmd in ("declare", "local", "typeset") and any(a.startswith("-") and "n" in a for a in args):
            dynamic = True
        if cmd in ("mapfile", "readarray") and any(a == "-C" or a.startswith("-C") for a in args):
            dynamic = True
        for value in candidates:
            if "$" in value or "`" in value:
                dynamic = True
            match = re.match(r"^([A-Za-z_]\w*)(?:=|\[|$)", value)
            if match:
                names.add(match.group(1))
            elif not value.startswith(("-", "<", ">")):
                dynamic = True  # UNKNOWN target name cannot preserve a new proof.
        if printf_v and not candidates:
            dynamic = True
        if not names and cmd in ("read", "mapfile", "readarray"):
            names.add("REPLY" if cmd == "read" else "MAPFILE")
        if dynamic:
            names.update(state["temps"])
            if "EPYC_TEST_TMP" in env:
                names.add("EPYC_TEST_TMP")
        for name in names:
            if name in state["temps"] or name == "EPYC_TEST_TMP" and name in env:
                state["lost_temps"].add(name)
            state["temps"].discard(name)
            env.pop(name, None)
    if cmd == "eval":
        body = " ".join(args)
        body = re.sub(r"\$\{(\w+)\}|\$(\w+)",
                      lambda m: env.get(m.group(1) or m.group(2), m.group(0)), body)
        return scan_text(body, rs, "eval script", "sh", env, state)
    if cmd == "trap" and args and not args[0].startswith("-"):
        # Single quotes defer expansion until exit. Other forms expand at
        # registration, so retain the original bindings rather than granting
        # them a later mktemp assignment's provenance.
        frozen = None
        if not getattr(args[0], "literal", False):
            frozen = (dict(env), dict(state, traps=[], temps=set(state["temps"]),
                                      lost_temps=set(state["lost_temps"])))
        state["traps"].append((args[0], frozen))
        return None
    if cmd in SANCTIONED:
        return None
    if INTERP.match(cmd):
        # sanctioned script as first non-flag arg
        nonflag = [a for a in args if not a.startswith("-")]
        if "-c" in args:
            i = args.index("-c")
            if i + 1 < len(args):
                return scan_text(args[i + 1], rs, "inline -c script", cmd, env, state)
            return None
        if nonflag:
            script = nonflag[0]
            if os.path.basename(script) in SANCTIONED:
                return None
            path = script if os.path.isabs(script) else os.path.join(state["cwd"], script)
            try:
                if os.path.isfile(path) and os.path.getsize(path) <= MAX_FILE:
                    with open(path, "r", errors="replace") as f:
                        return scan_text(f.read(), rs, f"script file {script}", cmd, env, state)
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
        return check_targets(tg, state["cwd"], env, rs, "recursive rm", state)
    if cmd == "find":
        if "-delete" in args or any(a == "-exec" and i + 1 < len(args) and os.path.basename(args[i + 1]) == "rm"
                                    for i, a in enumerate(args)):
            tg = []
            for a in args:
                if a.startswith("-") or a in ("(", "!"):
                    break
                tg.append(a)
            return check_targets(tg or ["."], state["cwd"], env, rs, "find -delete/-exec rm", state)
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


def scan_shell(cmd, rs, env, state):
    segs, heredocs = split_commands(cmd)
    for line, body in heredocs:
        # heredoc fed to an interpreter (python3 - <<EOF, bash <<EOF) is an inline script
        for part in re.split(r"&&|\|\||[;|]", line):
            t = tokens_of(part.split("<<")[0])
            while t and re.match(r"^[A-Za-z_]\w*=", t[0]):
                t.pop(0)
            if t and INTERP.match(os.path.basename(t[0])):
                if len(t) > 1 and os.path.basename(t[1]) in SANCTIONED:
                    continue
                r = scan_text(body, rs, "heredoc script", os.path.basename(t[0]), env, state)
                if r:
                    return r
    for seg in segs:
        seg = re.sub(r"<<-?\s*(['\"]?)[A-Za-z_]\w*\1", "", seg)
        r = scan_segment(seg, state["cwd"], env, rs, state)
        if r:
            return r
    traps = state["traps"]
    state["traps"] = []
    for body, frozen in traps:
        trap_env, trap_state = frozen if frozen else (env, state)
        r = scan_text(body, rs, "trap script", "sh", trap_env, trap_state)
        if r:
            return r
    return None


def scan(cmd: str):
    rs = roots()
    declared = os.environ.get("EPYC_TEST_TMP", "")
    env = {"EPYC_TEST_TMP": declared} if declared else {}
    return scan_shell(cmd, rs, env, {"cwd": os.getcwd(), "depth": 0, "temps": set(),
                                   "lost_temps": set(), "traps": [], "complex": False,
                                   "declared_temp": valid_declared_temp(rs)})


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

#!/usr/bin/env python3
"""Flag `producer | <early-exit reader>` pipelines that run under `set -o pipefail`.

Bug class: when the last command of a pipeline exits before draining its input
(`grep -q`, `grep -m N`, `grep -l`, `head`), the producer takes SIGPIPE (141).
Under pipefail the pipeline then reports failure even though the pattern WAS
found, so a PRESENT pattern reads as missing.  Seen twice: a false DEP_MISSING
(2026-10-21) and a false "binary lacks the change" (2026-10-22).

Scope is positional: a finding needs an earlier `set -o pipefail` / `set -eo
pipefail` in the same file with no `set +o pipefail` in between (function scope
is approximated by file order).  Suppress one line with a trailing
`# lint-ok: pipefail-early-exit`.  Stdlib only.

Usage: check_pipefail_early_exit.py [--strict] [--json] PATH [PATH ...]
Exit 0 unless --strict and there is at least one finding (2 on usage error).
"""
from __future__ import annotations

import json
import os
import re
import sys

PRAGMA = "lint-ok: pipefail-early-exit"
KEYWORDS = {"if", "elif", "then", "else", "do", "while", "until", "!", "time", "exec"}
GREPS = {"grep", "egrep", "fgrep", "zgrep", "zegrep", "rg"}
SMALL_PRODUCERS = {"echo", "printf"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def tokenize(text):
    """Yield (op, segment_text, line) with op in {'|', ';'} marking what FOLLOWS
    the segment (';' = any non-pipe terminator).  Quote-, comment- and
    heredoc-aware; `line` is the 1-based line where the segment starts."""
    n, i, line = len(text), 0, 1
    quote = None
    buf, seg_line = [], 1
    pending_heredocs = []
    out = []

    def flush(op):
        s = "".join(buf).strip()
        if s:
            out.append((op, s, seg_line))
        buf.clear()

    while i < n:
        c = text[i]
        if c == "\n":
            if quote:
                buf.append(c); line += 1; i += 1; continue
            flush(";")
            line += 1; i += 1
            while pending_heredocs:  # skip heredoc bodies
                tag = pending_heredocs.pop(0)
                while i < n:
                    j = text.find("\n", i)
                    j = n if j < 0 else j
                    body = text[i:j]
                    i = min(j + 1, n); line += 1
                    if body.strip() == tag:
                        break
            continue
        if not buf:
            seg_line = line
        if c == "\\" and quote != "'":
            if i + 1 < n and text[i + 1] == "\n":
                line += 1; buf.append(" "); i += 2; continue
            buf.append(text[i:i + 2]); i += 2; continue
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
            i += 1; continue
        if c in "'\"":
            quote = c; buf.append(c); i += 1; continue
        if c == "#" and (not buf or buf[-1] in " \t"):
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "<" and text.startswith("<<", i) and not text.startswith("<<<", i):
            m = re.match(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", text[i:])
            if m:
                pending_heredocs.append(m.group(2))
                buf.append(m.group(0)); i += len(m.group(0)); continue
        if c == "|":
            if text.startswith("||", i):
                flush(";"); i += 2; continue
            i += 2 if text.startswith("|&", i) else 1
            flush("|"); continue
        if c == "&" and text.startswith("&&", i):
            flush(";"); i += 2; continue
        if c in ";(){}`":
            flush(";"); i += 1; continue
        buf.append(c); i += 1
    flush(";")
    return out


def words_of(seg):
    ws = seg.split()
    while ws and (ws[0] in KEYWORDS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", ws[0])):
        ws.pop(0)
    return ws


def early_exit_kind(ws):
    """Return a label if this command is an early-exit reader, else None."""
    if not ws:
        return None
    cmd = os.path.basename(ws[0])
    if cmd == "head":
        return "head"
    if cmd not in GREPS:
        return None
    labels, skip = set(), False
    for w in ws[1:]:
        if skip:
            skip = False; continue
        if w in ("--quiet", "--silent"):
            labels.add("grep -q")
        elif w == "--files-with-matches":
            labels.add("grep -l")
        elif w.startswith("--max-count"):
            labels.add("grep -m")
        elif w.startswith("--"):
            continue
        elif re.match(r"^-[A-Za-z0-9]+$", w):
            cluster = w[1:]
            for k, ch in enumerate(cluster):
                if ch == "q":
                    labels.add("grep -q")
                elif ch == "l":
                    labels.add("grep -l")
                elif ch == "m":
                    labels.add("grep -m")
                    if k == len(cluster) - 1:
                        skip = True
                    break
                elif ch in "efABC":
                    if k == len(cluster) - 1:
                        skip = True
                    break
    for lab in ("grep -q", "grep -l", "grep -m"):
        if lab in labels:
            return lab
    return None


def suggest(kind, producer_cmd):
    if kind == "head":
        return ("capture first (`out=$(producer) || true; printf '%s\\n' \"$out\" | head ...`) "
                "or use `sed -n 1p` / `awk 'NR==1'` which drain the input")
    base = ("`grep -qaF PAT FILE` directly (no pipe)" if producer_cmd in ("strings", "cat")
            else "capture then test: `out=$(producer) || true; grep -q PAT <<<\"$out\"`")
    return base + "; or drop -q/-m and redirect (`grep PAT >/dev/null`) so grep drains the pipe"


def scan_text(text):
    """Return a list of finding dicts (line, kind, pipeline, severity, fix)."""
    lines = text.splitlines()
    segs = tokenize(text)
    findings, pipefail, i = [], False, 0
    while i < len(segs):
        j = i
        while j < len(segs) and segs[j][0] == "|":
            j += 1
        group = segs[i:j + 1]  # last element has non-pipe terminator
        i = j + 1
        # `set -o pipefail` / `set +o pipefail` (single-command groups)
        ws0 = words_of(group[0][1])
        if len(group) == 1 and ws0 and ws0[0] == "set":
            for k, w in enumerate(ws0):
                if w == "pipefail" and k > 0:
                    if re.match(r"^-[A-Za-z]*o$", ws0[k - 1]):
                        pipefail = True
                    elif ws0[k - 1] == "+o":
                        pipefail = False
            continue
        if len(group) < 2 or not pipefail:
            continue
        last_ws = words_of(group[-1][1])
        kind = early_exit_kind(last_ws)
        if not kind:
            continue
        line_no = group[-1][2]
        if any(PRAGMA in lines[x - 1] for x in range(group[0][2], min(line_no, len(lines)) + 1)):
            continue
        pw = words_of(group[0][1])
        pcmd = os.path.basename(pw[0]) if pw else ""
        findings.append({
            "line": line_no,
            "kind": kind,
            "severity": "low" if pcmd in SMALL_PRODUCERS else "high",
            "pipeline": " | ".join(" ".join(g[1].split()) for g in group)[:200],
            "fix": suggest(kind, pcmd),
        })
    return findings


def is_shell_file(path):
    if path.endswith((".sh", ".bash")):
        return True
    if os.path.splitext(path)[1]:
        return False
    try:
        with open(path, "rb") as f:
            head = f.readline(200)
    except OSError:
        return False
    return head.startswith(b"#!") and (b"bash" in head or b"/sh" in head)


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in sorted(files):
                    fp = os.path.join(root, fn)
                    if os.path.isfile(fp) and is_shell_file(fp):
                        yield fp
        elif os.path.isfile(p):
            yield p


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if not args or flags - {"--strict", "--json"}:
        print(__doc__, file=sys.stderr)
        return 2
    results = []
    for fp in iter_files(args):
        try:
            with open(fp, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print(f"{fp}: unreadable: {e}", file=sys.stderr)
            continue
        for f_ in scan_text(text):
            f_["file"] = fp
            results.append(f_)
    if "--json" in flags:
        print(json.dumps(results, indent=1))
    else:
        for r in results:
            print(f"{r['file']}:{r['line']}: [{r['severity']}] {r['kind']} under pipefail: "
                  f"{r['pipeline']}\n    fix: {r['fix']}")
        print(f"{len(results)} finding(s)", file=sys.stderr)
    return 1 if results and "--strict" in flags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

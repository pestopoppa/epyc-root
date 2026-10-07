#!/usr/bin/env python3
"""Shared shell-text scanning for PreToolUse guards: match INVOCATIONS, not text.

Every guard here answers the same question — "does this command DO X?" — and every one of
them has, at some point, answered the wrong question: "does this command's text CONTAIN X?"
The distinction is the whole of this module. A guard that fires on text blocks the
documentation about itself, the grep looking for it, and the bus message reporting the bug,
and a guard that stalls a session for a reason it cannot see teaches people to route around
it. Routing around a control is how the unguarded path each of these guards was written to
close came to exist.

MEASURED, four times, in four independently written guards:

  2026-07-29  pytest -n auto      a heredoc listing it as an EXAMPLE was read as an
                                  invocation, and a pytest run piped into a `sed` line
                                  range was blocked as if the range were a worker count
                                  (C21). The strippers below were written here first.
  2026-08-18  git commit (D9)     every token after the first `--` to end-of-string was
                                  taken as the commit's pathspec, so a chained
                                  `; python3 scripts/coordination/...` was swept in
  2026-08-18  commit hygiene      `_SEP` split on newlines, so every LINE of a heredoc body
                                  became its own "command"; a Python heredoc whose SOURCE
                                  contained the text of a commit was blocked
  2026-08-18  drop_caches         the write regex ran against the raw command, so a doc
                                  heredoc and a grep both matched — latently, firing only
                                  under a held region, i.e. only mid-bench

Three of those wrote or needed their own copy of this logic while a correct one already
existed in `pytest_worker_scan`. This module exists so the fifth guard does not.

USE `segments()` (or `lex()`, its one-pass reader) unless you need the pieces. The
pieces are kept for the guards that call them directly; chained, they still miss
escapes and heredoc markers inside quotes (see lex). Order matters and is easy to get wrong:
heredocs MUST be stripped before quotes, because a quoted heredoc marker (``<<'EOF'``)
would otherwise have its name blanked as a quoted run, leaving ``<<''`` — no detectable
terminator, and the body scanned as commands again.

WHAT THIS IS NOT. It is a scanner, not a shell parser. It does not expand variables, follow
`$(...)`, or resolve aliases, and a guard that needs certainty about a command's effect
should ask the system instead — as `check_d9_loop_plane.py` asks git which paths a commit
records, and `check_live_holder_interference.sh` asks whether a region is actually held.
Text scanning narrows what is worth asking about; it does not decide.
"""

from __future__ import annotations

import re

__all__ = ["SEPARATORS", "strip_quoted", "strip_heredocs", "strip_comments", "lex", "segments"]

# A shell separator ends a command: a later pipeline stage is a different invocation.
_SEPARATORS = re.compile(r"(?:\|\||&&|[;|\n])")

SEPARATORS = _SEPARATORS

# `#` starts a comment only at a line start or after whitespace — `a#b` is one word.
_COMMENT = re.compile(r"(?:(?<=^)|(?<=\s))#[^\n]*")


def strip_quoted(text: str) -> str:
    """Blank the CONTENTS of quoted runs, preserving length and the quotes.

    Length is preserved so offsets stay meaningful; the quote characters stay so a
    caller can still see that a quoted run was present.
    """
    out: list[str] = []
    quote: str | None = None
    for char in text:
        if quote is not None:
            if char == quote:
                quote = None
                out.append(char)
            else:
                out.append(" ")
        elif char in ("'", '"'):
            quote = char
            out.append(char)
        else:
            out.append(char)
    return "".join(out)

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(text: str) -> str:
    """Blank heredoc BODIES. They are data being written, not commands being run.

    Found by this guard blocking its own test fixture: a heredoc listing
    ``pytest -n auto`` as an example input was read as an invocation. Same class as
    the quoted-argument case — the guard was matching text rather than commands.

    ORDER MATTERS: this must run BEFORE quote stripping. A quoted heredoc marker
    (``<<'EOF'``) would otherwise have its name blanked as a quoted run, leaving
    ``<<''`` — no detectable terminator, and the body scanned as commands again.
    """
    lines = text.split("\n")
    out: list[str] = []
    terminator: str | None = None
    for line in lines:
        if terminator is not None:
            out.append("")
            if line.strip() == terminator:
                terminator = None
            continue
        out.append(line)
        found = _HEREDOC.search(line)
        if found:
            terminator = found.group(2)
    return "\n".join(out)



def strip_comments(text: str) -> str:
    """Blank shell comments. Replaced with a space, never "", so tokens cannot fuse."""
    return _COMMENT.sub(" ", text)


_PLAIN = frozenset("_./+,:=@%-")


def _literal(c: str) -> str:
    """A quoted or escaped character as DATA: itself when it means nothing to the
    shell, else a private-use stand-in (U+E000 + code) that stays inside the word
    but can never be read as syntax, a separator, or a trustworthy path character."""
    return c if c.isalnum() or c in _PLAIN or ord(c) > 127 else chr(0xE000 + ord(c) % 128)


def lex(command: str, keep_quoted: bool = False, bodies: list[str] | None = None) -> str:
    """The command with every DATA region removed, decided in ONE pass the way bash
    reads it — quotes, escapes, comments and heredocs each with the others in view.

    The three strippers above are each right alone and wrong in sequence. Origin
    2026-10-07 (filesystem containment review), all measured: `echo "<<EOF"` or a
    `# <<EOF` comment opened a heredoc that blanked the real commands after it;
    `\\"` and `$'\\''` opened quotes that hid them; `a\\ #` started a comment bash
    does not see; a `\\`-newline split one command in two, losing its target.

    Output: quoted contents blanked — or, with ``keep_quoted``, kept as _literal
    data, so `"rm"` still reads as rm and `"a b"` stays one word; escaped characters
    likewise data; comments and heredoc bodies removed; continuations joined.
    `$(...)` and backticks inside double quotes are code and stay code. With
    ``bodies``, each heredoc body is appended to it and its `<<` is followed by
    chr(0xE080 + index) (capped at 0xE0FF), so a caller can find the body a
    command reads.
    """
    text = re.sub("[\ue000-\uf8ff]", "\ufffd", command)  # input cannot forge a stand-in
    data = _literal if keep_quoted else (lambda c: " ")
    out: list[str] = []
    stack: list[str] = []   # open ( (( and, returning to "...": $(" $((" `"
    quote, last, i, n, arith = "", "\n", 0, len(text), 0   # arith: open (( in stack
    heredocs: list[tuple[str, bool, bool]] = []   # (delimiter, <<-, quoted) pending
    while i < n:
        c, nxt = text[i], text[i + 1:i + 2]
        emit, step = c, 1
        if quote == "'":
            quote, emit = ("", c) if c == "'" else (quote, data(c))
        elif quote:                                   # "..." or $'...'
            if c == "\\" and nxt:
                emit, step = data(c) + data(nxt), 2
            elif c == quote[-1]:
                quote = ""
            elif quote == '"' and (c == "`" or text.startswith("$(", i)):
                emit = "`" if c == "`" else "$((" if text.startswith("$((", i) else "$("
                quote, arith, step = "", arith + (emit == "$(("), len(emit)
                stack.append(emit + '"')
            else:
                emit = data(c)
        elif c == "\\":                               # \-newline is a continuation
            emit, c = ("", last) if nxt == "\n" else (_literal(nxt) if nxt else "", "x")
            step = 2
        elif c == "#" and last in " \t\n;&|()":
            end = text.find("\n", i)
            emit, step, c = " ", (n if end < 0 else end) - i, last
        elif c in "'\"":
            quote = "$'" if c == "'" and last == "$" else c
        elif c == "`" and stack[-1:] == ['`"']:
            stack.pop()
            quote = '"'
        elif c == "(":
            emit = "((" if nxt == "(" and last in " \t\n;&|($" else "("   # (( is arithmetic
            stack.append(emit)
            arith, step = arith + (emit == "(("), len(emit)
        elif c == ")":
            top = stack[-1] if stack else ""                # empty: a case pattern's `)`
            emit = "))" if "((" in top and nxt == ")" else ")"
            if top and top != '`"' and (emit == "))" or "((" not in top):
                stack.pop()
                quote, arith = '"' if top.endswith('"') else "", arith - ("((" in top)
            step = len(emit)
        elif text.startswith("<<<", i) or text.startswith("<<", i) and arith:
            emit = text[i:i + 3] if text.startswith("<<<", i) else "<<"  # here-string; shift
            step = len(emit)
        elif text.startswith("<<", i):
            j = k = i + 2 + (text[i + 2:i + 3] == "-")
            while k < n and text[k] in " \t":
                k += 1
            word, quoted, skip = [], False, k - i          # the delimiter, unquoted
            while k < n and text[k] not in " \t\n;&|()<>":
                if text[k] in "'\"":
                    end = text.find(text[k], k + 1) % (n + 1)   # -1: to the end
                    word.append(text[k + 1:end])
                    quoted, k = True, end + 1
                else:
                    escaped = text[k] == "\\"
                    word.append(text[k + escaped:k + 1 + escaped])
                    quoted, k = quoted or escaped, k + 1 + escaped
            emit, step = text[i:j], skip                  # the word follows, unspaced
            if word:
                heredocs.append(("".join(word), j > i + 2, quoted))
                if bodies is not None:
                    emit += chr(0xE080 + min(len(bodies) + len(heredocs) - 1, 127))
        elif c == "\n" and heredocs:
            i += 1
            for delim, tabs, quoted in heredocs:
                start, parts = i, []
                while i < n:
                    end = text.find("\n", i) % (n + 1)
                    line, i = text[i:end], end + 1
                    if not quoted and (len(line) - len(line.rstrip("\\"))) % 2:
                        parts.append(line[:-1])           # a continuation (unquoted only)
                        continue
                    line, parts = "".join(parts) + line, []
                    if (line.lstrip("\t") if tabs else line) == delim:
                        break
                if bodies is not None:
                    bodies.append(text[start:i])
            heredocs, step = [], 0
        out.append(emit)
        last = c
        i += step
    return "".join(out)


def segments(command: str) -> list[str]:
    """The command's invocations, with data removed. The normal entry point.

    Lexes in one pass (lex — the strippers above, chained, mis-order quotes against
    heredocs and ignore escapes), then splits on separators.
    """
    return SEPARATORS.split(lex(command))

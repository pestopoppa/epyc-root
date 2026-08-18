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

USE `segments()` unless you need the pieces. Order matters and is easy to get wrong:
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

__all__ = ["SEPARATORS", "strip_quoted", "strip_heredocs", "strip_comments", "segments"]

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


def segments(command: str) -> list[str]:
    """The command's invocations, with data removed. The normal entry point.

    Applies the three strippers in the one order that works, then splits on separators.
    """
    return SEPARATORS.split(strip_comments(strip_quoted(strip_heredocs(command))))

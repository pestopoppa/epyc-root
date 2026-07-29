#!/usr/bin/env python3
"""Scan a shell command for an UNSAFE pytest worker count. Stdin -> stdout verdict.

Prints ``auto`` for ``-n auto``, the number for ``-n N`` with N > 16, and nothing
when the command is safe. Helper for ``check_pytest_safety.sh`` (C21, 2026-07-29).

WHY THIS IS NOT A REGEX OVER THE WHOLE COMMAND. The original guard matched
``pytest.*-n\\s*[0-9]+`` against the entire command string. ``.*`` crosses shell
separators and quotes, so it blocked a pytest run piped into a ``sed`` line-range
(reading the line range as a worker count) and then blocked the bus message that
reported that bug, because the payload quoted the pattern. It was matching TEXT;
what matters is INVOCATIONS.

Two boundaries fix that, and nothing else changes:
  * quoted runs are blanked — their contents are data, not a command line;
  * the command is split on shell separators — a later pipeline stage is a
    different program and its flags are not pytest's.

Detection of pytest itself stays deliberately GENEROUS: any segment whose unquoted
text contains the word, in any position, is scanned from that word onward. That
keeps ``xargs pytest -n 64`` and ``timeout 900 python -m pytest -n 32`` caught.
The scope narrowed; the safety property did not.
"""

from __future__ import annotations

import re
import sys

MAX_WORKERS = 16
_SEPARATORS = re.compile(r"(?:\|\||&&|[;|\n])")
_PYTEST = re.compile(r"(?:^|[\s/])pytest\b")
_AUTO = re.compile(r"(?:^|\s)-n[\s=]*auto\b")
_COUNT = re.compile(r"(?:^|\s)-n[\s=]*([0-9]+)")


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


def unsafe_worker_verdict(command: str) -> str:
    for segment in _SEPARATORS.split(strip_quoted(strip_heredocs(command))):
        found = _PYTEST.search(segment)
        if not found:
            continue
        after = segment[found.end():]
        if _AUTO.search(after):
            return "auto"
        count = _COUNT.search(after)
        if count and int(count.group(1)) > MAX_WORKERS:
            return count.group(1)
    return ""


def main() -> int:
    verdict = unsafe_worker_verdict(sys.stdin.read())
    if verdict:
        print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

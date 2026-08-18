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
# Shell-text scanning moved to shell_scan.py on 2026-08-18 — the same strippers were
# needed by four guards and this module was an odd home for them (the name implies
# pytest scope). Re-exported here because process_pattern_kill_scan.py and
# operator_apply_copy_scan.py imported them from this module by name.
from shell_scan import (  # noqa: E402,F401
    SEPARATORS as _SEPARATORS, segments, strip_comments, strip_heredocs, strip_quoted)

_PYTEST = re.compile(r"(?:^|[\s/])pytest\b")
_AUTO = re.compile(r"(?:^|\s)-n[\s=]*auto\b")
_COUNT = re.compile(r"(?:^|\s)-n[\s=]*([0-9]+)")


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

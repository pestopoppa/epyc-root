#!/usr/bin/env python3
"""Does this command WRITE to drop_caches — as an invocation, not as text?

Reads a shell command on stdin, prints `write` if it contains a real drop_caches write
and nothing otherwise. Exit 0 either way; a scan failure is the caller's to interpret.

WHY THIS EXISTS. `check_live_holder_interference.sh` matched its regex against the RAW
command, so any text merely CONTAINING `echo 3 > /proc/sys/vm/drop_caches` matched — a
heredoc writing documentation about the guard, a `grep` searching for the pattern, a bus
message reporting it. Measured 2026-08-18 under a held region: doc-heredoc and grep cases
both blocked (exit 2) alongside the real write.

That defect was LATENT rather than harmless, which is worse. The guard only reaches its
block when a CPU region is actually held, so a false positive fires rarely, unpredictably,
and precisely during a bench — the moment a session is least able to work out why its
unrelated command was refused.

The strippers are imported from `pytest_worker_scan`, the same ones
`process_pattern_kill_scan.py` and `operator_apply_copy_scan.py` already reuse. That module
learned this lesson first (C21, 2026-07-29, "it was matching text, not invocations") and its
implementation is the repo's one correct copy. Reusing it is the point: this defect has now
been found in four separate guards, and every rewrite is another chance to get it wrong.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shell_scan import segments  # noqa: E402

# A real write: a redirect or a tee into the file, or a sysctl assignment. Unchanged from
# the original guard — only the TEXT it is applied to changed.
# NOTE the tee alternative does NOT require its leading pipe. `_SEPARATORS` splits on `|`,
# so by the time a segment is tested the pipe is gone and `echo 1 | sudo tee /proc/.../
# drop_caches` arrives as the segment ` sudo tee /proc/sys/vm/drop_caches`. Carrying the
# original regex over verbatim silently dropped that form — caught by probing, which is the
# only reason this comment exists rather than a hole.
_WRITE = re.compile(
    r"(?:>|>>)\s*/proc/sys/vm/drop_caches"
    r"|(?:^|\s)(?:sudo\s+)?tee(?:\s+-a)?\s+/proc/sys/vm/drop_caches"
    r"|sysctl[^;&|]*\bvm\.drop_caches\s*=")



def drop_caches_write(command: str) -> bool:
    return any(_WRITE.search(seg) for seg in segments(command))


def main() -> int:
    try:
        command = sys.stdin.read()
    except (OSError, ValueError):
        return 0
    if drop_caches_write(command):
        print("write")
    return 0


if __name__ == "__main__":
    sys.exit(main())

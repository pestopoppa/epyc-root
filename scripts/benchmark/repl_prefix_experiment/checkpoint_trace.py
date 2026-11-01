#!/usr/bin/env python3
"""Match frozen-v10 context-checkpoint trace lines against a claimed task/slot/boundary.

This matches native trace text only. The caller must separately prove that the task
id belongs to the request, that the boundary is the effective volatile-user start,
that the log belongs to the owned server and that its binary matches the build.
"""
import argparse
import json
import re
from pathlib import Path

# server-common.h SLT_TRC and server-context.cpp create_checkpoint, v10 ffc1bac.
LINE = re.compile(
    r"\bslot\s+\S+:\s+id\s+(?P<slot>\d+)\s*\|\s*task\s+(?P<task>\d+)\s*\|\s*"
    r"created context checkpoint\s+\d+\s+of\s+\d+\s*"
    r"\(pos_min\s*=\s*-?\d+,\s*pos_max\s*=\s*-?\d+,\s*"
    r"n_tokens\s*=\s*(?P<tokens>\d+),\s*size\s*=\s*[\d.]+\s+MiB\)"
)


def match_checkpoint(text: str, slot: int, task: int, boundary: int) -> list[int]:
    """Return matching one-based line numbers; absence is inconclusive."""
    if min(slot, task) < 0 or boundary <= 0:
        raise ValueError('slot/task must be nonnegative and boundary positive')
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        match = LINE.search(line)
        if match and all(int(match.group(k)) == v for k, v in
                         [('slot', slot), ('task', task), ('tokens', boundary)]):
            lines.append(number)
    return lines


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace', type=Path, required=True)
    p.add_argument('--slot', type=int, required=True)
    p.add_argument('--task', type=int, required=True)
    p.add_argument('--boundary-tokens', type=int, required=True)
    a = p.parse_args()
    try:
        lines = match_checkpoint(a.trace.read_text(encoding='utf-8'), a.slot, a.task, a.boundary_tokens)
    except (OSError, UnicodeError, ValueError) as exc:
        p.error(str(exc))
    print(json.dumps({'match': bool(lines), 'matching_lines': lines,
                      'scope': 'trace-text match only; request binding and boundary provenance not verified'}))
    return 0 if lines else 1


if __name__ == '__main__':
    raise SystemExit(main())

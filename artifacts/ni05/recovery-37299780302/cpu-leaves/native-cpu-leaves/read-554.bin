"""`--only` + `--numa-mode` transition guard (additive mode promotion).

2026-07-23 lineup restoration: an explicit `--numa-mode both` over a realized
single-mode fleet is the sanctioned no-outage path to the big+quarters lineup
(only adds missing instances; skip-healthy keeps running servers). All other
mode mismatches on a `--only` start keep refusing — a narrower requested mode
would imply stopping live servers, and that path is stop-first only.
"""

from __future__ import annotations

import pytest

from scripts.server.stack_commands import _only_mode_transition_allowed


@pytest.mark.parametrize(
    ("numa_mode", "realized_mode", "allowed"),
    [
        ("both", "quarter", True),   # the restoration path: add fulls/halves
        ("both", "full", True),      # symmetric: add quarters to a solo fleet
        ("both", "both", False),     # unreachable live (guard only runs on mismatch)
        ("quarter", "both", False),  # narrowing implies stopping servers
        ("full", "both", False),
        ("quarter", "full", False),  # cross single-mode swap: stop-first only
        ("full", "quarter", False),
    ],
)
def test_only_mode_transition(numa_mode: str, realized_mode: str, allowed: bool) -> None:
    assert _only_mode_transition_allowed(numa_mode, realized_mode) is allowed

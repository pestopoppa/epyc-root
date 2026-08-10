"""ID sequencing with merge gaps (schema § ID Sequencing, 2026-08-10).

Merging a duplicate away leaves a permanent hole in the id sequence, and renumbering to close it is
refused: 728 entries would change id, along with 731 of the intake ids embedded in Vidya ledger
claim identifiers that an append-only log cannot rewrite. So the sequential check has to accept a
declared gap while still catching an undeclared one.

The case that matters most is the last: declaring an id you did NOT absorb must not buy you a pass
on a different gap. Without it the allowance degrades into "write anything in merged_ids".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / ".claude" / "skills" / "research-intake" / "scripts")
)

from validate_intake import validate_index  # noqa: E402

CATS = {"agent_architecture"}
BASE = dict(
    source_type="paper", title="t", categories=["agent_architecture"], novelty="high",
    relevance="high", discovered_via="input", verdict="not_applicable",
    ingested_date="2026-01-01", arxiv_id=None,
)


def entry(num: int, **kw) -> dict:
    return {**BASE, "id": f"intake-{num:03d}", "url": f"https://example.com/{num}", **kw}


def seq_errors(entries: list[dict]) -> list[str]:
    return [e for e in validate_index(entries, CATS) if "sequential" in e]


def test_contiguous_ids_pass():
    assert seq_errors([entry(1), entry(2), entry(3)]) == []


def test_undeclared_gap_is_an_error():
    assert seq_errors([entry(1), entry(3)])


@pytest.mark.parametrize("declared", ["intake-002", "intake-2"])
def test_declared_gap_is_accepted_regardless_of_zero_padding(declared):
    """`intake-002` and `intake-2` are the same id.

    The first version compared formatted strings, so a padded declaration silently failed to match
    and the gap stayed an error. It passed on the live index only because every current id is three
    digits -- the bug was invisible at the size the data happened to be.
    """
    assert seq_errors([entry(1, merged_ids=[declared]), entry(3)]) == []


def test_multiple_declared_gaps_are_accepted():
    assert seq_errors([entry(1, merged_ids=["intake-002", "intake-003"]), entry(4)]) == []


def test_declaring_an_unrelated_id_does_not_excuse_the_gap():
    assert seq_errors([entry(1, merged_ids=["intake-009"]), entry(3)])


def test_prose_alone_does_not_excuse_a_gap():
    """`merge_history` is for the reader; the allowance reads `merged_ids`.

    The allowance was originally regexed out of the prose note, which made a validation rule depend
    on how a human worded a sentence.
    """
    prose = ["Merged intake-002 on 2026-08-10: same locator."]
    assert seq_errors([entry(1, merge_history=prose), entry(3)])

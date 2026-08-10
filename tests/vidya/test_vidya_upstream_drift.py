"""PR1b-upstream-drift: a source revised after we recorded it.

intake-110 is why this exists — an entry ingested 2026-03-14 against arXiv v1 of a paper now at v7,
whose authors revised away the exact figure our entry quoted. Nobody touched the record; it became
false because the source moved.

What the check may and may not say is the whole design. "Drifted" means the paper changed after we
ingested it and nobody has looked since. It does NOT mean the entry is wrong, and a test suite that
let it drift toward asserting that would be re-creating the confident-guess failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from upstream_drift import _bare  # noqa: E402


def test_version_suffixes_are_stripped():
    assert _bare("2603.05433v7") == "2603.05433"
    assert _bare("2603.05433") == "2603.05433"
    assert _bare(" 2603.05433V2 ") == "2603.05433"
    assert _bare("2603.05433.pdf") == "2603.05433"


def test_the_live_report_treats_drift_as_a_prompt_not_a_verdict():
    """The note is load-bearing text, not decoration — pin it so it cannot be quietly hardened."""
    import upstream_drift

    report = upstream_drift.sweep([], limit=0)
    assert report["checked"] == 0
    assert "not necessarily wrong" in report["note"]
    assert "nobody has looked since" in report["note"]


def test_entries_without_an_arxiv_id_or_date_are_not_swept():
    """A blog post has no version history to compare against; sweeping it would invent one."""
    import upstream_drift

    entries = [
        {"id": "intake-1", "arxiv_id": None, "ingested_date": "2026-01-01"},
        {"id": "intake-2", "arxiv_id": "2501.00001", "ingested_date": None},
    ]
    assert upstream_drift.sweep(entries, limit=10)["checked"] == 0

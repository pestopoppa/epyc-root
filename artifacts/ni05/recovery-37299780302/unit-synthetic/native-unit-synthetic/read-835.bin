"""TRIPWIRE: `memories.sub_decision` has no production producer.

WHY THIS EXISTS. `test_episodic_store_sub_decision.py` is 312 lines and passes: it
covers the enum, the normaliser, the column-and-index migration, the classifier token
map, and the backfill script. It covers everything EXCEPT whether anything ever writes
the column on the live path. So the suite was green while the column was empty, and
the audit row records the consequence plainly — *"Three agents ran its test and none
noticed the column is empty."*

Re-derived 2026-08-12 (`mainC`) rather than taken from the row, and it is WORSE than
filed: the row says 0 / 59,337, but a read-only count over the checkpoint store gives
**0 non-null of 642,328 rows** — an order of magnitude more data, still entirely empty.

WHAT THIS TEST IS. Not a test of behaviour — a tripwire on a KNOWN GAP. It passes
while the gap exists and FAILS THE MOMENT SOMEONE WIRES A PRODUCER, which is the
point: whoever wires it is then forced to confirm the column actually populates and to
close the audit row, instead of landing a producer that quietly does nothing (which is
how `binding_router`, `model_id` and `assigned_role` — the exact twins named in the
same audit — got into this state).

It is deliberately NOT a `pytest.xfail` and NOT a skip. Both of those are invisible in
a green run, and invisibility is the whole defect being pinned.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: The two files allowed to mention `sub_decision=`: the store that DEFINES the field,
#: and the backfill script that exists but has never been run. Anything else is a
#: producer, and a producer is what this tripwire is watching for.
_ALLOWED = ("orchestration/repl_memory/episodic_store.py",
            "scripts/memory/backfill_sub_decision.py")

_SEARCH_ROOTS = ("src", "scripts", "orchestration")


def _producer_call_sites() -> list[str]:
    """Every `sub_decision=` keyword-argument site outside the store and backfill.

    KNOWN LIMIT, found while proving this tripwire actually fires: `git grep` sees
    only TRACKED files, so a producer sitting uncommitted in the working tree will
    not trip this locally. That is the right trade — it trips in CI and on the
    committed tree, which is where the claim matters — but it means a green local
    run is not evidence that nobody is mid-way through wiring one.

    Verified load-bearing rather than assumed: appending a `sub_decision=` call to a
    TRACKED file makes this test fail; the first attempt used an UNTRACKED probe file
    and passed, which looked like the tripwire was inert when it was the check that
    was wrong.
    """
    out = subprocess.run(
        ["git", "grep", "-n", "sub_decision=", "--", *_SEARCH_ROOTS],
        cwd=REPO, capture_output=True, text=True, check=False).stdout
    hits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line.split(":", 1)[0]
        if path.endswith(_ALLOWED) or any(path == a for a in _ALLOWED):
            continue
        # A definition or a signature default is not a producer.
        if re.search(r"sub_decision=\s*(None|Optional|self\.sub_decision)\b", line):
            continue
        hits.append(line)
    return hits


def test_sub_decision_still_has_no_producer() -> None:
    """FAILS when a producer appears. That failure is the success signal — read on.

    If this fails, someone has wired `sub_decision` on a write path. Good. Now finish
    the job, because the column existing is not the feature working:

      1. Confirm the column actually POPULATES in a live store — count non-null rows,
         do not trust that the call site exists. That distinction is the entire reason
         this file was written.
      2. Decide whether `scripts/memory/backfill_sub_decision.py` should finally run
         over the historical rows, or whether history stays null by design.
      3. Close the audit row in
         `handoffs/active/autopilot-continuous-optimization.md` and DELETE this file —
         a tripwire that outlives its gap is just noise.
    """
    hits = _producer_call_sites()
    assert hits == [], (
        "A production producer for `memories.sub_decision` now exists:\n  "
        + "\n  ".join(hits)
        + "\n\nThis tripwire has done its job. Verify the column POPULATES (count "
          "non-null rows in a live store — a call site is not population), decide the "
          "backfill question, close the audit row, and delete this file."
    )


def test_the_column_and_its_unused_machinery_are_all_still_present() -> None:
    """Guards the other direction: silent REMOVAL is also a resolution nobody recorded.

    If the column, the backfill script or the original test disappear, the audit row
    stops describing reality just as surely as if a producer had appeared — and a
    reader would have no way to tell which happened.
    """
    store = (REPO / "orchestration/repl_memory/episodic_store.py").read_text(encoding="utf-8")
    assert "sub_decision" in store, "the column vanished — close the audit row deliberately"
    assert (REPO / "scripts/memory/backfill_sub_decision.py").exists(), (
        "the never-run backfill script vanished — record that decision on the audit row")

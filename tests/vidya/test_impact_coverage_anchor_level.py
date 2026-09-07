"""`CLAIM_COMPLETE` must mean ANCHORED, not "MachineLocated or better".

Found 2026-09-07 by the RC-12 threshold-provenance audit, as a live off-by-one.

`_coverage_of` classified a belief `CLAIM_COMPLETE` when every support path had `g.t >= 2`.
That literal was correct when it was written: `Anchored` was ordinal 2. Commit `29173208`
then inserted `MachineLocated` at ordinal 2 -- `T_LEVELS` is now
`(T0, Located, MachineLocated, Anchored, Attested)` -- and the comparison silently began
admitting machine-located spans, while the local variable and the docstring above it both
still said "anchored".

The pilot spec's own amendment argued that insertion was ordinal-safe because grades
"serialize as **names**, never ordinals". That is true for stored frames and false for a
comparison written against a number, which is exactly the gap these tests pin.

It failed in the DANGEROUS direction. `CLAIM_COMPLETE` is what licenses asserting
`UNAFFECTED`, and `impact.py`'s own header calls a wrong `UNAFFECTED` "the single most
dangerous output this system could produce". Machine-located spans are produced by
`machine_anchor.py` -- by construction, spans no person has read.

Every positive below is paired with the mutation that would revive the bug.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

from fold import Belief  # noqa: E402
from impact import Coverage, coverage_of  # noqa: E402
from lattice import Grade, T_LEVELS  # noqa: E402

MACHINE_LOCATED = T_LEVELS.index("MachineLocated")
ANCHORED = T_LEVELS.index("Anchored")
ATTESTED = T_LEVELS.index("Attested")


def _belief(*t_levels: int) -> Belief:
    b = Belief(claim_id="c1")
    b.pro_paths = [(f"e{i}", Grade(2, t)) for i, t in enumerate(t_levels)]
    return b


def test_the_ordinals_are_what_this_test_thinks_they_are():
    """Pins the premise. If T_LEVELS is reordered again, this fails FIRST and loudly,
    rather than the coverage tests below quietly changing meaning."""
    assert T_LEVELS == ("T0", "Located", "MachineLocated", "Anchored", "Attested")
    assert MACHINE_LOCATED == 2 and ANCHORED == 3


def test_all_anchored_is_claim_complete():
    assert coverage_of(_belief(ANCHORED, ANCHORED)) is Coverage.CLAIM_COMPLETE


def test_attested_counts_as_anchored_or_better():
    """Attested is strictly above Anchored; the bar is a floor, not an equality."""
    assert coverage_of(_belief(ATTESTED, ANCHORED)) is Coverage.CLAIM_COMPLETE


def test_all_machine_located_is_NOT_claim_complete():
    """THE REGRESSION. Under the old `g.t >= 2` this returned CLAIM_COMPLETE, so a belief
    supported only by spans no person ever read could license an UNAFFECTED assertion."""
    # Pins the ACTUAL value, not a negation. `is not CLAIM_COMPLETE` was satisfied by any of
    # four values, so it could not tell a correct downgrade from a wrong one (Q.1 audit).
    assert coverage_of(_belief(MACHINE_LOCATED, MACHINE_LOCATED)) is Coverage.SOURCE_COMPLETE


def test_a_single_machine_located_path_downgrades_the_whole_belief():
    """CLAIM_COMPLETE requires EVERY path anchored -- one machine-located path is enough
    to make the claim only partially checkable."""
    assert coverage_of(_belief(ANCHORED, MACHINE_LOCATED)) is Coverage.PARTIAL


def test_machine_located_still_reaches_PARTIAL_not_UNMAPPED():
    """The fix tightens CLAIM_COMPLETE; it must not erase the difference between a
    machine-located span and no registered edge at all.

    Rewritten 2026-09-07 after the Q.1 audit found its assertion was character-identical to
    the preceding test's -- two tests, one fact. This one now pins the OTHER end: no edges at
    all is UNMAPPED, which is the distinction the fix must not collapse."""
    assert coverage_of(_belief()) is Coverage.UNMAPPED


def test_the_bar_is_read_from_the_named_level_not_a_literal():
    """The mutation that reintroduces the bug is replacing the named lookup with `2`.

    Inspects CODE lines only. The first version of this test grepped the whole file and
    failed on the explanatory comment, which quotes `g.t >= 2` to say what it used to be --
    a check that fired on its own documentation. Strip comments before asserting.
    """
    src = (REPO / "scripts" / "vidya" / "impact.py").read_text()
    code = "\n".join(
        line.split("#", 1)[0] for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    assert 'T_LEVELS.index("Anchored")' in code
    # Whitespace-insensitive: the first version grepped the literal string "g.t >= 2" and was
    # defeated by "g.t>=2" (Q.1 audit). Compare with all whitespace stripped.
    squeezed = "".join(code.split())
    assert "g.t>=2" not in squeezed, "the literal ordinal comparison is back in executable code"

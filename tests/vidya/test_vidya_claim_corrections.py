"""PR2c: a correction must be able to name which claims it touched.

Before this, `dive-overturned` opposed EVERY claim of an entry — measured 2026-08-10 as 114 claims
across 27 entries — and a prose `dive_corrections` field flagged all 681 claims of its 155 entries.
intake-896 is the case: four claims, one fabricated, all four opposed for fifteen days.

The `unaffected` verdict is the load-bearing one. Without a way to say "this sibling survived", the
only expressible position is blanket doubt, which is what the gold corpus E1/E3 families were
written to catch.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from adapters.research_intake import _claim_corrections, _frames_for_entry  # noqa: E402

AT = "2026-08-10T00:00:00Z"
FT_OPPOSE = "epyc.vidya/frame/evidence_opposes_claim/v1"
FT_SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"
FT_CORRECTION = "epyc.vidya/frame/correction_recorded/v1"


def entry(**kw):
    base = {
        "id": "intake-900", "url": "https://example.com/x", "arxiv_id": None,
        "source_type": "paper", "title": "t", "verification": "dive-overturned",
        "key_claims": ["claim zero", "claim one", "claim two", "claim three"],
    }
    base.update(kw)
    return base


def kinds(frames, ftype):
    return {f["assertion"]["claim_id"] for f in frames if f["frame_type"] == ftype}


def test_without_per_claim_records_every_claim_is_opposed():
    """The old behaviour, pinned so a regression is visible rather than quiet."""
    frames = _frames_for_entry(entry(), AT)
    assert len(kinds(frames, FT_OPPOSE)) == 4
    assert kinds(frames, FT_SUPPORT) == set()


def test_unaffected_siblings_are_supported_not_opposed():
    e = entry(claim_corrections=[
        {"claim_index": 0, "effect": "unaffected", "note": "never disputed"},
        {"claim_index": 1, "effect": "unaffected", "note": "never disputed"},
        {"claim_index": 2, "effect": "unaffected", "note": "never disputed"},
        {"claim_index": 3, "effect": "overturned", "note": "fabricated"},
    ])
    frames = _frames_for_entry(e, AT)
    assert kinds(frames, FT_OPPOSE) == {"clm_intake_900_03"}
    assert kinds(frames, FT_SUPPORT) == {
        "clm_intake_900_00", "clm_intake_900_01", "clm_intake_900_02"}


def test_narrowed_and_reattributed_are_review_not_refutation():
    """A narrowed claim is not a false one; opposing it would overstate the finding."""
    e = entry(claim_corrections=[
        {"claim_index": 0, "effect": "narrowed", "note": "holds only on CPU"},
        {"claim_index": 1, "effect": "reattributed", "note": "credit belongs elsewhere"},
        {"claim_index": 2, "effect": "unaffected", "note": "fine"},
        {"claim_index": 3, "effect": "overturned", "note": "false"},
    ])
    frames = _frames_for_entry(e, AT)
    assert kinds(frames, FT_OPPOSE) == {"clm_intake_900_03"}
    assert "clm_intake_900_00" in kinds(frames, FT_SUPPORT)


def test_the_correction_frame_names_only_the_touched_claims():
    e = entry(dive_corrections="a dive changed something", claim_corrections=[
        {"claim_index": 0, "effect": "unaffected", "note": "n"},
        {"claim_index": 3, "effect": "overturned", "note": "n"},
    ])
    frames = _frames_for_entry(e, AT)
    corr = next(f for f in frames if f["frame_type"] == FT_CORRECTION)

    # `claim_ids` is what the correction IMPLICATES — the cleared sibling is not in it.
    assert corr["assertion"]["claim_ids"] == ["clm_intake_900_03"]

    # `per_claim_effects` is what the dive EXAMINED, including what it cleared. Keeping the
    # `unaffected` verdict is the difference between "we looked and it survived" and "nobody
    # looked", and only the first of those should stop a future dive re-litigating it.
    assert corr["assertion"]["per_claim_effects"] == {
        "clm_intake_900_00": "unaffected",
        "clm_intake_900_03": "overturned",
    }


def test_prose_only_correction_still_blankets_the_entry():
    """Blanket doubt stays the honest default for an unindexed prose correction."""
    e = entry(verification="dive-verified", dive_corrections="something changed, unspecified")
    frames = _frames_for_entry(e, AT)
    corr = next(f for f in frames if f["frame_type"] == FT_CORRECTION)
    assert len(corr["assertion"]["claim_ids"]) == 4
    assert corr["assertion"]["per_claim_effects"] is None


def test_records_are_indexed_by_claim():
    e = entry(claim_corrections=[{"claim_index": 2, "effect": "overturned", "note": "n"}])
    assert set(_claim_corrections(e)) == {2}


# --- a per-claim overturn carries DIVE warrant, not the entry's ---------------------------

def test_per_claim_overturn_is_graded_verified_even_without_an_entry_level_verdict():
    """intake-110 claim 4: the only conflicted claim in 4,233 beliefs, and it was an artifact.

    A `claim_corrections` record is written by a Stage-2 dive -- the same authority whose
    entry-level form (`verification: dive-overturned`) maps to Verified opposition. Flipping only
    the DIRECTION left the refutation at `Hinted`, tied with the stage-1 support it refutes, so the
    fold reported settled history as a live disagreement.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
    from adapters.research_intake import apply_claim_verdict
    from lattice import parse_grade

    entry_level = parse_grade({"Q": "Hinted", "T": "Located"})
    grade, opposes = apply_claim_verdict(entry_level, False, {"effect": "overturned"})
    assert opposes is True
    assert grade.q_name == "Verified"
    assert grade.t_name == "Located", "a dive establishes warrant quality, not where the span is"


def test_overturn_never_downgrades_a_stronger_entry_level_grade():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
    from adapters.research_intake import apply_claim_verdict
    from lattice import parse_grade

    grade, opposes = apply_claim_verdict(
        parse_grade({"Q": "Witnessed", "T": "Attested"}), True, {"effect": "overturned"})
    assert (grade.q_name, grade.t_name, opposes) == ("Witnessed", "Attested", True)


def test_uncertain_keeps_the_entry_verdict_while_others_clear_opposition():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
    from adapters.research_intake import apply_claim_verdict
    from lattice import parse_grade

    g = parse_grade({"Q": "Verified", "T": "Located"})
    assert apply_claim_verdict(g, True, {"effect": "uncertain"})[1] is True
    for effect in ("unaffected", "narrowed", "reattributed"):
        assert apply_claim_verdict(g, True, {"effect": effect})[1] is False, effect
    assert apply_claim_verdict(g, True, None)[1] is True

"""Unit tests for src/mutation_ledger.py (BSV-3 conflict-aware acceptance)."""

from __future__ import annotations

from src.mutation_ledger import (
    ConflictLevel,
    MutationRecord,
    classify_mutation_conflict,
    MutationLedger,
)


def _m(mid: str, **kw) -> MutationRecord:
    return MutationRecord(mutation_id=mid, **kw)


# ─── classify ────────────────────────────────────────────────────────────────────

def test_disjoint_mutations_no_conflict() -> None:
    a = _m("a", subsystem="prompt", files_touched={"p.md"}, improved_sentinels={"q1"})
    b = _m("b", subsystem="routing", files_touched={"r.py"}, improved_sentinels={"q2"})
    level, reasons = classify_mutation_conflict(a, b)
    assert level == ConflictLevel.NONE
    assert "disjoint" in reasons[0]


def test_shared_file_is_review() -> None:
    a = _m("a", subsystem="routing", files_touched={"router.py"}, improved_sentinels={"q1"})
    b = _m("b", subsystem="tool_policy", files_touched={"router.py"}, improved_sentinels={"q1"})
    level, reasons = classify_mutation_conflict(a, b)
    assert level == ConflictLevel.REVIEW
    assert any("shared files" in r for r in reasons)


def test_same_subsystem_no_overlap_is_review() -> None:
    a = _m("a", subsystem="prompt", prompt_sections_touched={"intro"}, improved_sentinels={"q1"})
    b = _m("b", subsystem="prompt", prompt_sections_touched={"outro"}, improved_sentinels={"q1"})
    # same subsystem + same improved sentinel → review (no opposing improvement)
    level, reasons = classify_mutation_conflict(a, b)
    assert level == ConflictLevel.REVIEW


def test_direct_opposition_is_block() -> None:
    a = _m("a", subsystem="routing", files_touched={"r.py"}, improved_sentinels={"q1"})
    b = _m("b", subsystem="routing", files_touched={"r.py"}, regressed_sentinels={"q1"})
    level, reasons = classify_mutation_conflict(a, b)
    assert level == ConflictLevel.BLOCK
    assert any("direct opposition" in r for r in reasons)


def test_opposing_improvements_on_shared_surface_is_block() -> None:
    a = _m("a", subsystem="prompt", prompt_sections_touched={"sys"},
           improved_sentinels={"q1"}, behavior_signature_hash="h1")
    b = _m("b", subsystem="prompt", prompt_sections_touched={"sys"},
           improved_sentinels={"q2"}, behavior_signature_hash="h2")
    # disjoint improved sentinels + shared section + divergent signatures → semantic conflict
    level, reasons = classify_mutation_conflict(a, b)
    assert level == ConflictLevel.BLOCK
    assert any("opposing improvements" in r for r in reasons)


def test_disjoint_improvements_same_signature_not_block() -> None:
    a = _m("a", subsystem="prompt", prompt_sections_touched={"sys"},
           improved_sentinels={"q1"}, behavior_signature_hash="same")
    b = _m("b", subsystem="prompt", prompt_sections_touched={"sys"},
           improved_sentinels={"q2"}, behavior_signature_hash="same")
    level, _ = classify_mutation_conflict(a, b)
    assert level == ConflictLevel.REVIEW  # shared surface but no divergent signature


def test_list_inputs_coerced_to_sets() -> None:
    a = MutationRecord(mutation_id="a", files_touched=["x.py", "x.py"], improved_sentinels=["q1"])
    assert a.files_touched == {"x.py"}
    assert a.improved_sentinels == {"q1"}


# ─── ledger ──────────────────────────────────────────────────────────────────────

def test_ledger_detects_conflicts_against_prior_accepts() -> None:
    ledger = MutationLedger()
    assert ledger.register(_m("a", subsystem="routing", files_touched={"r.py"},
                              improved_sentinels={"q1"})) == []
    conflicts = ledger.register(_m("b", subsystem="routing", files_touched={"r.py"},
                                   regressed_sentinels={"q1"}))
    assert len(conflicts) == 1
    other_id, level, _ = conflicts[0]
    assert other_id == "a" and level == ConflictLevel.BLOCK
    assert len(ledger) == 2


def test_ledger_ignores_unaccepted_records() -> None:
    ledger = MutationLedger()
    ledger.register(_m("rejected", subsystem="routing", files_touched={"r.py"},
                       improved_sentinels={"q1"}, accepted=False))
    conflicts = ledger.register(_m("b", subsystem="routing", files_touched={"r.py"},
                                   regressed_sentinels={"q1"}))
    assert conflicts == []  # the prior record was not accepted → not a live conflict


def test_ledger_worst_level() -> None:
    ledger = MutationLedger()
    ledger.register(_m("a", subsystem="prompt", prompt_sections_touched={"sys"}, improved_sentinels={"q1"}))
    ledger.register(_m("b", subsystem="routing", files_touched={"r.py"}, improved_sentinels={"q2"}))
    conflicts = ledger.register(_m("c", subsystem="prompt", prompt_sections_touched={"sys"},
                                   regressed_sentinels={"q1"}))
    assert ledger.worst_level(conflicts) == ConflictLevel.BLOCK
    assert ledger.worst_level([]) == ConflictLevel.NONE

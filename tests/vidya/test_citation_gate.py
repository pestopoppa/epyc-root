"""SC12 — gating an intake citation where it is used as rationale.

These build real frames and fold them rather than mocking a FoldResult. The gate's answers depend on
`pro_paths`/`con_paths` and on the fold's own correction bookkeeping, and a hand-built stub is
exactly where a test starts agreeing with a bug.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import citation_gate as cg  # noqa: E402
from fold import fold  # noqa: E402
from frames import make_frame  # noqa: E402
from gate import UsePolicy  # noqa: E402
from lattice import parse_grade  # noqa: E402

AT = "2026-08-10T12:00:00Z"


def _f(ftype, assertion):
    return make_frame(
        frame_type=f"epyc.vidya/frame/{ftype}/v1",
        assertion=assertion,
        provenance={"method": "test", "about": "test"},
        actor="test", authority_scope="research-verification", created_at=AT,
    )


def build(entry_num, claims, *, correction_on=None):
    """One entry, N claims. `claims` maps index -> (Q, T, is_opposition)."""
    eid = f"intake-{entry_num}"
    sid = f"src_intake_{int(entry_num):03d}"
    out = [_f("source_observed", {"source_id": sid, "locator": f"https://example/{entry_num}"})]
    for i, (q, t, opposes) in claims.items():
        cid = f"clm_intake_{int(entry_num):03d}_{i:02d}"
        out.append(_f("claim_proposed",
                      {"claim_id": cid, "display_text": f"claim {i}", "source_id": sid}))
        out.append(_f("evidence_opposes_claim" if opposes else "evidence_supports_claim",
                      {"claim_id": cid, "evidence_id": f"evd_{cid}",
                       "grade": {"Q": q, "T": t}, "source_id": sid}))
    if correction_on:
        out.append(_f("correction_recorded",
                      {"claim_ids": [f"clm_intake_{int(entry_num):03d}_{i:02d}"
                                     for i in correction_on],
                       "entry_id": eid, "correction_text": "a dive said something",
                       "classification": None}))
    return out


def gate_text(text, frames, *, floor="Hinted/Located", live=None, redirects=None):
    result = fold(frames, as_of=AT)
    policy = UsePolicy(use="test", floor=parse_grade(floor))
    return cg.check_text(text, result, policy, path="doc.md",
                         redirects=redirects or {},
                         live=live if live is not None else {"110", "896", "1000"},
                         by_entry=cg.claims_by_entry(result))


# --- identity ---------------------------------------------------------------------------

def test_claims_by_entry_survives_four_digit_entries():
    """Formatting ids back from the entry number would drop every entry above 999."""
    frames = build("1000", {0: ("Hinted", "Located", False)})
    by_entry = cg.claims_by_entry(fold(frames, as_of=AT))
    assert by_entry["1000"] == ["clm_intake_1000_00"]


# --- entry-level vs precise citation ----------------------------------------------------

def test_entry_citation_inherits_a_refuted_claim():
    frames = build("896", {0: ("Hinted", "Located", False), 3: ("Verified", "Located", True)})
    (v,) = gate_text("per intake-896 the tool rebuilds the index", frames)
    assert v.status == "overturned"
    assert any("cite the specific claim" in n for n in v.notes)


def test_precise_citation_escapes_a_sibling_claims_refutation():
    """The escape hatch is precision, not leniency -- and it must actually work."""
    frames = build("896", {0: ("Hinted", "Located", False), 3: ("Verified", "Located", True)})
    (v,) = gate_text("per intake-896#00 the tool exists", frames)
    assert v.status == "ok"
    assert [c["claim_id"] for c in v.claims] == ["clm_intake_896_00"]


def test_precise_citation_of_the_refuted_claim_still_reports_it():
    frames = build("896", {0: ("Hinted", "Located", False), 3: ("Verified", "Located", True)})
    (v,) = gate_text("per intake-896#03", frames)
    assert v.status == "overturned"


# --- the states a citer can act on ------------------------------------------------------

def test_conflicted_entry_is_blocking():
    frames = build("110", {4: ("Hinted", "Located", False)})
    frames += [_f("evidence_opposes_claim",
                  {"claim_id": "clm_intake_110_04", "evidence_id": "evd_con",
                   "grade": {"Q": "Hinted", "T": "Located"}, "source_id": "src_other"})]
    (v,) = gate_text("see intake-110", frames)
    assert v.status == "conflicted"
    assert v.status in cg.BLOCKING


def test_citation_to_a_nonexistent_entry_is_dangling():
    (v,) = gate_text("see intake-2602", build("110", {0: ("Hinted", "Located", False)}))
    assert (v.status, v.resolved) == ("dangling", None)


def test_entry_with_no_ingested_claims_is_a_coverage_gap_not_a_defect():
    """`unknown` must never be blocking: it says the substrate has not read the entry."""
    (v,) = gate_text("see intake-1000", build("110", {0: ("Hinted", "Located", False)}))
    assert v.status == "unknown"
    assert v.status not in cg.BLOCKING
    assert "coverage gap" in v.notes[0]


def test_merged_citation_resolves_forward_and_says_so():
    frames = build("110", {0: ("Hinted", "Located", False)})
    (v,) = gate_text("see intake-797", frames, live={"110"}, redirects={"797": "110"})
    assert (v.resolved, v.how) == ("110", "merged")
    assert any("merge map" in n for n in v.notes)


# --- the auto-downgrade rule ------------------------------------------------------------

def test_unadjudicated_correction_warns_but_does_not_block():
    """571 claims carry one; a gate that blocked on all of them gets switched off in a day."""
    frames = build("110", {0: ("Hinted", "Located", False)}, correction_on=[0])
    (v,) = gate_text("see intake-110", frames)
    assert v.status == "review"
    assert "review" not in cg.BLOCKING


def test_blocking_is_exactly_the_three_actionable_states():
    assert cg.BLOCKING == {"dangling", "overturned", "conflicted"}


def test_severity_covers_every_status_it_can_emit():
    """`min(..., key=SEVERITY.index)` raises if a status is missing from the ordering."""
    for status in ("dangling", "overturned", "conflicted", "review", "weak", "unknown", "ok"):
        assert status in cg.SEVERITY


# --- policy ------------------------------------------------------------------------------

def test_a_strict_floor_downgrades_an_unverified_claim_to_weak():
    frames = build("110", {0: ("Hinted", "Located", False)})
    (lo,) = gate_text("intake-110", frames, floor="Hinted/Located")
    (hi,) = gate_text("intake-110", frames, floor="Verified/Located")
    assert (lo.status, hi.status) == ("ok", "weak")


def test_scan_writes_nothing_to_the_ledger():
    """A document scan is not a query; logging hundreds of linter reads would drown the R5 series."""
    src = (ROOT / "scripts" / "vidya" / "citation_gate.py").read_text()
    assert "query_served_frame" not in src
    assert "\n    led.append(" not in src and "ledger.append(" not in src


@pytest.mark.parametrize("text,expected", [
    ("intake-110 and intake-896", 2),
    ("intake-110/896", 2),
    ("no citations here", 0),
])
def test_citation_forms_are_all_gated(text, expected):
    frames = build("110", {0: ("Hinted", "Located", False)})
    frames += build("896", {0: ("Hinted", "Located", False)})
    assert len(gate_text(text, frames)) == expected

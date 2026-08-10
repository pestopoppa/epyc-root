"""SC13 — draining the correction queue.

The two defects these pin were both found on the live ledger while building the queue: a correction
recorded N times (re-ingest mints a new frame_id for identical text) and a correction whose claim
ids only match after alias resolution. Both are silent: the first leaves a claim blocked after an
apparently complete review, the second puts a claim in a worksheet under an id whose `claim_index`
belongs to a different entry.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import correction_queue as cq  # noqa: E402
from adapters.research_intake import CORRECTION_EFFECTS  # noqa: E402
from fold import fold  # noqa: E402
from frames import make_frame  # noqa: E402


def _f(ftype, assertion, at="2026-08-10T12:00:00Z"):
    return make_frame(
        frame_type=f"epyc.vidya/frame/{ftype}/v1",
        assertion=assertion,
        provenance={"method": "test", "about": "test"},
        actor="test", authority_scope="research-verification", created_at=at,
    )


def entry(num, n_claims=2):
    sid = f"src_intake_{int(num):03d}"
    out = [_f("source_observed", {"source_id": sid, "locator": f"https://example/{num}"})]
    for i in range(n_claims):
        cid = f"clm_intake_{int(num):03d}_{i:02d}"
        out += [
            _f("claim_proposed", {"claim_id": cid, "display_text": f"claim {i}", "source_id": sid}),
            _f("evidence_supports_claim",
               {"claim_id": cid, "evidence_id": f"evd_{cid}",
                "grade": {"Q": "Hinted", "T": "Located"}, "source_id": sid}),
        ]
    return out


def correction(num, claim_idx, text="the dive found something", at="2026-08-10T12:00:00Z"):
    return _f("correction_recorded", {
        "claim_ids": [f"clm_intake_{int(num):03d}_{i:02d}" for i in claim_idx],
        "entry_id": f"intake-{num}", "correction_text": text, "classification": None,
    }, at=at)


def rows_for(frames, citations=None):
    return cq.pending(frames, fold(frames, as_of="2026-08-10T23:00:00Z"),
                      citations=citations or {})


# --- the duplicate-copy defect ------------------------------------------------------------

def test_identical_correction_ingested_thrice_is_one_row_with_three_copies():
    frames = entry("547", 2)
    for at in ("2026-08-09T22:00:00Z", "2026-08-10T14:00:00Z", "2026-08-10T20:00:00Z"):
        frames.append(correction("547", [0, 1], at=at))
    (row,) = rows_for(frames)
    assert row.copies == 3
    assert len(set(row.correction_frame_ids)) == 3
    assert row.claim_ids == ["clm_intake_547_00", "clm_intake_547_01"]


def test_emit_writes_one_reviewed_frame_per_copy():
    """Reviewing 3 of 4 copies leaves the claim blocked with nothing to show why."""
    frames = entry("547", 1)
    for at in ("2026-08-09T22:00:00Z", "2026-08-10T14:00:00Z"):
        frames.append(correction("547", [0], at=at))
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    for c in ws["rows"][0]["claims"]:
        c["effect"] = "unaffected"
    out = cq.frames_from_worksheet(ws, at="2026-08-10T23:00:00Z")
    assert len(out) == 2
    assert {f["assertion"]["reviewed"] for f in out} == set(ws["rows"][0]["correction_frame_ids"])


def test_reviewed_frame_targets_the_correction_not_the_entry():
    """Targeting the entry would review corrections written after this decision."""
    frames = entry("547", 1) + [correction("547", [0])]
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    ws["rows"][0]["claims"][0]["effect"] = "overturned"
    (f,) = cq.frames_from_worksheet(ws, at="2026-08-10T23:00:00Z")
    assert f["assertion"]["reviewed"].startswith("sha256:")
    assert f["assertion"]["reviewed"] != f["assertion"]["entry_id"]


# --- alias resolution ----------------------------------------------------------------------

def test_claims_come_from_the_fold_so_aliases_resolve():
    """A correction naming the absorbed id must surface the CANONICAL claim."""
    frames = entry("374", 1) + entry("378", 1)
    frames.append(_f("claim_alias", {"claim_ids": ["clm_intake_374_00", "clm_intake_378_00"],
                                     "independent": False}))
    frames.append(correction("378", [0]))
    (row,) = rows_for(frames)
    assert row.claim_ids == ["clm_intake_374_00"]


# --- the worksheet contract ----------------------------------------------------------------

def test_worksheet_starts_pending_and_pending_emits_nothing():
    frames = entry("547", 2) + [correction("547", [0, 1])]
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    assert {c["effect"] for c in ws["rows"][0]["claims"]} == {"pending"}
    assert cq.frames_from_worksheet(ws, at="2026-08-10T23:00:00Z") == []


def test_partially_adjudicated_row_emits_nothing():
    frames = entry("547", 2) + [correction("547", [0, 1])]
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    ws["rows"][0]["claims"][0]["effect"] = "overturned"      # second left pending
    assert cq.frames_from_worksheet(ws, at="2026-08-10T23:00:00Z") == []


def test_unknown_effect_is_refused_loudly():
    """An unrecognised effect falls through the adapter to 'not opposition' -- silently un-opposing."""
    frames = entry("547", 1) + [correction("547", [0])]
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    ws["rows"][0]["claims"][0]["effect"] = "probably-fine"
    with pytest.raises(ValueError, match="not in"):
        cq.frames_from_worksheet(ws, at="2026-08-10T23:00:00Z")


def test_effect_vocabulary_is_the_adapters_not_a_local_copy():
    assert cq.CORRECTION_EFFECTS is CORRECTION_EFFECTS
    assert "overturned" in CORRECTION_EFFECTS and "unaffected" in CORRECTION_EFFECTS


# --- ranking -------------------------------------------------------------------------------

def test_rows_rank_by_citation_weight():
    """A queue of 129 drained in id order is a queue nobody finishes."""
    frames = entry("100", 1) + entry("200", 1)
    frames += [correction("100", [0]), correction("200", [0])]
    rows = rows_for(frames, citations={"200": ["handoffs/active/a.md", "wiki/b.md"],
                                       "100": []})
    assert [r.entry_id for r in rows] == ["intake-200", "intake-100"]
    assert rows[0].citations == 2


# --- the index block -----------------------------------------------------------------------

def test_index_block_is_valid_yaml_at_entry_indentation():
    frames = entry("547", 2) + [correction("547", [0, 1])]
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    for i, c in enumerate(ws["rows"][0]["claims"]):
        c["effect"] = "overturned" if i == 0 else "unaffected"
        c["note"] = "why"
    block = cq.index_blocks(ws)["intake-547"]
    assert all(ln.startswith("  ") for ln in block.splitlines() if ln.strip())
    parsed = yaml.safe_load(block)
    assert [r["claim_index"] for r in parsed["claim_corrections"]] == [0, 1]
    assert parsed["claim_corrections"][0]["effect"] == "overturned"


def test_index_block_survives_quotes_in_the_note():
    """Hand-built YAML is where an apostrophe in a dive note becomes a parse error."""
    frames = entry("547", 1) + [correction("547", [0])]
    ws = cq.worksheet(rows_for(frames), generated_at="2026-08-10T23:00:00Z")
    ws["rows"][0]["claims"][0]["effect"] = "narrowed"
    ws["rows"][0]["claims"][0]["note"] = "the authors' own Appendix D: \"mis-scored\" — see p.98"
    parsed = yaml.safe_load(cq.index_blocks(ws)["intake-547"])
    assert "Appendix D" in parsed["claim_corrections"][0]["note"]


# --- the root cause: re-ingest must not mint duplicate corrections -------------------------

def test_dedup_key_ignores_informationless_nulls():
    """An additive schema field defaulting to None re-emitted the whole corpus (485 for 155)."""
    from adapters.research_intake import _dedup_key

    base = {"frame_type": "epyc.vidya/frame/correction_recorded/v1",
            "assertion": {"entry_id": "intake-136", "correction_text": "x", "classification": None}}
    widened = {"frame_type": base["frame_type"],
               "assertion": dict(base["assertion"], per_claim_effects=None)}
    assert _dedup_key(base) == _dedup_key(widened)


def test_dedup_key_still_separates_a_populated_new_field():
    """Dropping nulls must not collapse frames that genuinely say different things."""
    from adapters.research_intake import _dedup_key

    a = {"frame_type": "t/v1", "assertion": {"entry_id": "intake-1", "per_claim_effects": None}}
    b = {"frame_type": "t/v1",
         "assertion": {"entry_id": "intake-1", "per_claim_effects": {"clm_intake_001_00": "overturned"}}}
    assert _dedup_key(a) != _dedup_key(b)


def test_dedup_key_drops_nulls_nested_in_lists_and_maps():
    from adapters.research_intake import _dedup_key

    a = {"frame_type": "t/v1", "assertion": {"anchors": [{"kind": "page", "span": None}]}}
    b = {"frame_type": "t/v1", "assertion": {"anchors": [{"kind": "page"}]}}
    assert _dedup_key(a) == _dedup_key(b)

"""Tests for cross-entry claim-identity candidate generation (R4b-authoring).

The properties worth pinning are the ones whose violation would be invisible: a same-entry pair
would manufacture corroboration from one source, a same-locator pair would do the same across two
records of one paper, and an unattributed approval would let a machine judgment pass as a human
one. Each of those produces a *plausible* number rather than a crash, so each gets a test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from alias_candidates import (  # noqa: E402
    WorksheetError,
    aliases_from_worksheet,
    generate_candidates,
    locator_map,
    normalize_terms,
    worksheet_from_candidates,
)
from frames import make_frame  # noqa: E402

FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"


def claim(entry: str, index: int, text: str) -> dict:
    cid = f"clm_intake_{entry}_{index:02d}"
    return make_frame(
        frame_type=FT_CLAIM,
        assertion={"claim_id": cid, "display_text": text, "source_id": f"src_intake_{entry}"},
        provenance={"method": "test", "about": cid},
        actor="test",
        authority_scope="test",
        created_at="2026-08-10T00:00:00Z",
    )


def test_normalize_drops_stopwords_and_case():
    assert normalize_terms("The gfp does NOT specialize") == frozenset({"gfp", "does", "specialize"})


def test_near_duplicate_across_entries_is_proposed():
    frames = [
        claim("100", 0, "repeating 2500 samples eight times beats one-pass 20k under fixed budget"),
        claim("200", 0, "repeating 2500 samples eight times outperforms one-pass 20k, fixed budget"),
    ]
    report = generate_candidates(frames, min_score=0.3)
    assert report["candidates_above_threshold"] == 1
    pair = report["candidates"][0]
    assert {pair["claim_a"], pair["claim_b"]} == {"clm_intake_100_00", "clm_intake_200_00"}
    assert pair["shared_terms"], "a proposed pair must say why it was proposed"


def test_same_entry_pairs_are_never_proposed():
    """The one hard filter: two claims of one entry are one source, not two supports."""
    text = "repeating 2500 samples eight times beats one-pass 20k under fixed budget"
    report = generate_candidates([claim("100", 0, text), claim("100", 1, text)], min_score=0.0)
    assert report["candidates"] == []


def test_unrelated_claims_are_not_proposed():
    frames = [
        claim("100", 0, "gfp does not specialize, so absence certificates route through dual tokens"),
        claim("200", 0, "MI210 host threads must be pinned to SMT siblings 184-191"),
    ]
    assert generate_candidates(frames, min_score=0.35)["candidates"] == []


def test_same_source_is_flagged_not_hidden():
    """Two entries for one paper: aliasing is correct identity, but it is not corroboration."""
    frames = [
        claim("418", 0, "memory externalizes state, skills externalize procedural expertise"),
        claim("797", 0, "memory externalizes state and skills externalize procedural expertise"),
    ]
    locators = locator_map(
        [
            {"id": "intake-418", "arxiv_id": "2604.08224"},
            {"id": "intake-797", "url": "https://arxiv.org/abs/2604.08224v2"},
        ]
    )
    report = generate_candidates(frames, min_score=0.3, locators=locators)
    assert report["candidates"], "the pair should still be proposed"
    assert report["candidates"][0]["same_source"] is True


def test_locator_map_folds_arxiv_url_and_id_and_version():
    lm = locator_map(
        [
            {"id": "intake-1", "arxiv_id": "2604.08224"},
            {"id": "intake-2", "url": "https://arxiv.org/pdf/2604.08224v3"},
            {"id": "intake-3", "url": "https://Example.com/a/"},
            {"id": "intake-4", "url": "http://example.com/a"},
        ]
    )
    assert lm["intake-1"] == lm["intake-2"] == "arxiv:2604.08224"
    assert lm["intake-3"] == lm["intake-4"] == "url:example.com/a"


def test_worksheet_rows_start_pending_and_emit_nothing():
    report = generate_candidates(
        [
            claim("100", 0, "repeating 2500 samples eight times beats one-pass 20k fixed budget"),
            claim("200", 0, "repeating 2500 samples eight times beats one-pass 20k, fixed budget"),
        ],
        min_score=0.3,
    )
    ws = worksheet_from_candidates(report, generated_at="2026-08-10T00:00:00Z")
    assert [r["decision"] for r in ws["rows"]] == ["pending"]
    assert aliases_from_worksheet(ws) == []


def test_approved_rows_close_transitively():
    ws = {
        "schema": "epyc.vidya/alias-worksheet/v1",
        "rows": [
            {"claim_a": "clm_b", "claim_b": "clm_c", "decision": "same", "reviewer": "op"},
            {"claim_a": "clm_a", "claim_b": "clm_b", "decision": "same", "reviewer": "op"},
            {"claim_a": "clm_x", "claim_b": "clm_y", "decision": "different", "reviewer": "op"},
        ],
    }
    groups = aliases_from_worksheet(ws)
    assert len(groups) == 1
    assert groups[0]["claim_ids"] == ["clm_a", "clm_b", "clm_c"]


def test_approval_without_a_reviewer_is_refused():
    ws = {
        "schema": "epyc.vidya/alias-worksheet/v1",
        "rows": [{"claim_a": "clm_a", "claim_b": "clm_b", "decision": "same", "reviewer": "  "}],
    }
    with pytest.raises(WorksheetError, match="reviewer"):
        aliases_from_worksheet(ws)


def test_unknown_decision_is_refused():
    ws = {
        "schema": "epyc.vidya/alias-worksheet/v1",
        "rows": [{"claim_a": "a", "claim_b": "b", "decision": "probably", "reviewer": "op"}],
    }
    with pytest.raises(WorksheetError, match="decision"):
        aliases_from_worksheet(ws)


def test_generation_is_deterministic():
    frames = [
        claim("100", 0, "repeating 2500 samples eight times beats one-pass 20k fixed budget"),
        claim("200", 0, "repeating 2500 samples eight times beats one-pass 20k, fixed budget"),
        claim("300", 0, "three-layer architecture: raw sources, wiki pages, schema config"),
        claim("400", 0, "three-layer architecture of raw sources, wiki pages and schema"),
    ]
    a = generate_candidates(frames, min_score=0.3)
    b = generate_candidates(list(reversed(frames)), min_score=0.3)
    assert a["candidates"] == b["candidates"]


# ------------------------------------------------- T2 MachineLocated (spec §4.2, 2026-08-10)

def test_machine_anchor_cannot_reach_anchored():
    """A machine anchor caps at MachineLocated however complete it is.

    Revision and quote hash make it checkable, not read. Capping in the adapter rather than at the
    policy layer means a well-formed machine anchor cannot be promoted by looking thorough.
    """
    from adapters.research_intake import _t_level  # noqa: PLC0415

    entry = {"url": "https://arxiv.org/abs/2604.08224"}
    machine = {
        "quote": "some span",
        "quote_sha256": "ab" * 32,
        "source_revision": "v2",
        "located_by": "machine",
    }
    human = {"quote": "some span", "quote_sha256": "ab" * 32, "source_revision": "v2"}
    assert _t_level(entry, machine) == "MachineLocated"
    assert _t_level(entry, human) == "Attested"


def test_machine_anchor_without_a_quote_hash_is_only_located():
    """An unpinned machine match is not a span anybody can check, so it earns nothing."""
    from adapters.research_intake import _t_level  # noqa: PLC0415

    entry = {"url": "https://example.com/x"}
    assert _t_level(entry, {"quote": "s", "located_by": "machine"}) == "Located"


# ------------------------------------- independence after aliasing (R4b, 2026-08-10)

def test_alias_group_is_non_independent_when_any_row_is_related():
    ws = {
        "schema": "epyc.vidya/alias-worksheet/v1",
        "rows": [
            {"claim_a": "clm_a", "claim_b": "clm_b", "decision": "same", "reviewer": "op",
             "same_source": False, "linked": True},
        ],
    }
    assert aliases_from_worksheet(ws)[0]["independent"] is False


def test_alias_group_is_independent_when_no_row_is_related():
    ws = {
        "schema": "epyc.vidya/alias-worksheet/v1",
        "rows": [
            {"claim_a": "clm_a", "claim_b": "clm_b", "decision": "same", "reviewer": "op",
             "same_source": False, "linked": False},
        ],
    }
    assert aliases_from_worksheet(ws)[0]["independent"] is True

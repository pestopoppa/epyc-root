"""R5: the series computation, and the panels it must leave empty.

R5d was filed as "collect the forward series", which is a standing obligation wearing a checkbox.
The deliverable is this computation: run it today and it reports the t=0 shape and names which
panels have no data; run it in a month and the same command reports the series.

The load-bearing test is the last one. The reuse panel is empty because nobody has issued an
authoritative query yet, and writing synthetic `query_served` frames to fill it would fabricate the
exact measurement the panel exists to report. An empty panel is the honest state.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from frames import make_frame  # noqa: E402
from r5_series import series  # noqa: E402

AT = "2026-08-11T00:00:00Z"
G = {"Q": "Verified", "T": "Anchored"}


def _f(ftype, assertion, provenance, at=AT):
    return make_frame(frame_type=ftype, assertion=assertion, provenance=provenance,
                      actor="test", authority_scope="test", created_at=at)


def corpus():
    return [
        _f("epyc.vidya/frame/source_observed/v1",
           {"source_id": "s1", "locator": "https://example.com/a", "title": "s1"},
           {"about": "s1", "method": "t"}),
        _f("epyc.vidya/frame/claim_proposed/v1",
           {"claim_id": "clm_a", "display_text": "a", "source_id": "s1"},
           {"about": "clm_a", "method": "t"}),
        _f("epyc.vidya/frame/evidence_supports_claim/v1",
           {"claim_id": "clm_a", "evidence_id": "evd_a", "grade": G, "source_id": "s1"},
           {"evidence": "evd_a", "about": "clm_a"}),
    ]


def query(claim_id, outcome, at):
    return _f("epyc.vidya/frame/query_served/v1",
              {"claim_id": claim_id, "use": "wiki", "outcome": outcome,
               "usable_as_current": outcome == "allow"},
              {"about": claim_id, "method": "vidya.gate/evaluate"}, at=at)


def test_a_corpus_with_no_queries_reports_empty_panels_not_zeros():
    r = series(corpus(), as_of=AT)
    assert r["queries_served"] == 0
    assert r["abstention_rate"] is None, "no queries means no rate, not a rate of zero"
    assert "queries_served" in r["empty_panels"]


def test_queries_produce_an_outcome_mix_and_abstention_rate():
    frames = corpus() + [
        query("clm_a", "allow", "2026-08-12T00:00:00Z"),
        query("clm_a", "abstain", "2026-08-12T00:00:00Z"),
        query("clm_b", "abstain", "2026-08-13T00:00:00Z"),
    ]
    r = series(frames, as_of="2026-08-14T00:00:00Z")
    assert r["queries_served"] == 3
    assert r["query_outcomes"] == {"abstain": 2, "allow": 1}
    assert r["abstention_rate"] == round(2 / 3, 4)
    assert set(r["queries_by_day"]) == {"2026-08-12", "2026-08-13"}


def test_time_to_first_reuse_pairs_a_claim_with_its_first_query():
    frames = corpus() + [
        query("clm_a", "allow", "2026-08-20T00:00:00Z"),
        query("clm_a", "allow", "2026-08-25T00:00:00Z"),
    ]
    r = series(frames, as_of="2026-08-26T00:00:00Z")
    born, first = r["time_to_first_reuse"]["clm_a"]
    assert born == "2026-08-11"
    assert first == "2026-08-20", "the FIRST query, not the latest"


def test_the_empty_reuse_panel_must_not_be_filled_synthetically():
    """The panel measures whether anyone used a belief. Writing frames to fill it fabricates that.

    This test exists to make the intent explicit rather than leaving it to a comment: a run with no
    real queries must report the panel as empty, and any future convenience that seeds it would
    have to delete this test to pass.
    """
    r = series(corpus(), as_of=AT)
    assert r["claims_ever_queried"] == 0
    assert r["time_to_first_reuse"] == {}
    assert "time_to_first_reuse" in r["empty_panels"]

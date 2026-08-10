"""SC5 — wiki pages as dependents, never as claims.

The operator's ruling was that a wiki page is compiled FROM sources the index already holds, so
turning it into a claim would count one paper twice. These tests pin the two things that ruling
implies: the citation graph must be read completely (an under-read graph understates staleness,
the direction that hides problems), and a coverage gap must never be reported as decay.
"""

import re
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import wiki_dependents as wd  # noqa: E402


class FakeBelief:
    def __init__(self, q="Hinted", corrections=(), needs_review=False):
        self.pro = types.SimpleNamespace(q_name=q)
        self.corrections = list(corrections)
        self.needs_review = needs_review


def fold_with(claims: dict):
    return types.SimpleNamespace(beliefs=claims)


# --- reading the citation graph -----------------------------------------------------------

def test_plain_citations_are_read():
    assert wd.cited_ids("see intake-115 and intake-131") == {"115", "131"}


def test_run_form_names_every_entry_it_lists():
    """`intake-710/711` is one token naming two entries; reading only the first halves the graph."""
    assert wd.cited_ids("OKF analysis lives in intake-710/711") == {"710", "711"}
    assert wd.cited_ids("intake-172/173/174") == {"172", "173", "174"}


def test_leading_zeros_and_bare_numbers_normalise():
    assert wd.cited_ids("intake-007") == {"7"}


def test_run_form_does_not_swallow_a_trailing_arxiv_id():
    """Regression, found 2026-08-10 by `citation_gate` reporting a dangling `intake-2602`.

    The live text is `(intake-374/378/2602.11149 synthesis)` -- a two-entry run followed by an arXiv
    id. The unguarded run pattern ate `/2602` out of `2602.11149` and invented an entry; the first
    fix then let the engine backtrack into the partial number `260` and invent a different one.
    """
    assert wd.cited_ids("(intake-374/378/2602.11149 synthesis)") == {"374", "378"}
    assert wd.cited_ids("intake-141 (arxiv:2602.22402)") == {"141"}


def test_precise_claim_citations_are_read_as_such():
    assert sorted(wd.cited_refs("per intake-896#03 and intake-110")) == [("110", None), ("896", 3)]
    assert wd.cited_ids("per intake-896#03") == {"896"}


def test_claim_index_on_a_run_form_is_dropped_not_guessed():
    """`intake-710/711#02` does not say WHICH entry it indexes."""
    assert wd.cited_refs("intake-710/711#02") == {("710", None), ("711", None)}


def test_unrelated_numbers_are_not_citations():
    assert wd.cited_ids("45.3 tok/s across 96 threads, issue 115") == set()


def test_source_id_matches_the_ledger_convention():
    assert wd.source_id("12") == "src_intake_012"
    assert wd.source_id("1024") == "src_intake_1024"


# --- merged ids resolve forward -----------------------------------------------------------

def test_absorbed_id_resolves_to_its_survivor():
    resolved, how = wd.resolve("797", {"797": "418"}, {"418"})
    assert (resolved, how) == ("418", "merged")


def test_chained_merge_follows_through():
    resolved, how = wd.resolve("a1", {"a1": "b2", "b2": "c3"}, {"c3"})
    assert (resolved, how) == ("c3", "merged")


def test_merge_cycle_terminates_rather_than_hanging():
    assert wd.resolve("x", {"x": "y", "y": "x"}, set()) == (None, "dangling")


def test_id_reaching_neither_an_entry_nor_the_map_is_reported_not_dropped():
    """A merged id resolving to nothing is the policy; resolving to the WRONG paper is the bug."""
    assert wd.resolve("999", {}, {"1"}) == (None, "dangling")


# --- the distinction that the first draft got wrong ---------------------------------------

def test_never_ingested_entry_is_a_coverage_gap_not_decay():
    """intake-12 has no claims in the ledger. Calling that "lost all support" reads as rot."""
    present, supported, flagged = wd.stale_sources(fold_with({}))
    assert present == supported == set()
    assert flagged == {}


def test_decayed_entry_is_separated_from_an_uningested_one(monkeypatch, tmp_path):
    monkeypatch.setattr(wd, "scan_wiki", lambda root=None: {"wiki/p.md": {"1", "2", "3"}})
    monkeypatch.setattr(wd, "merge_redirects", lambda: {})
    monkeypatch.setattr(wd, "live_entry_ids", lambda: {"1", "2", "3"})
    res = fold_with({
        "clm_intake_001_00": FakeBelief(q="Hinted"),   # healthy
        "clm_intake_002_00": FakeBelief(q="Q0"),       # present but unsupported -> decay
        # intake-3 absent entirely -> coverage gap
    })
    row = wd.report(res)["rows"][0]
    assert row["unsupported"] == ["2"]
    assert row["uningested"] == ["3"]
    assert row["ok"] == 1


def test_only_decay_marks_a_page_stale(monkeypatch):
    """A paper we have not read yet is a gap in us, not a defect in the page."""
    monkeypatch.setattr(wd, "scan_wiki", lambda root=None: {"wiki/p.md": {"9"}})
    monkeypatch.setattr(wd, "merge_redirects", lambda: {})
    monkeypatch.setattr(wd, "live_entry_ids", lambda: {"9"})
    rep = wd.report(fold_with({}))
    assert rep["rows"][0]["uningested"] == ["9"]
    assert rep["rows"][0]["stale"] is False
    assert rep["stale_pages"] == 0


def test_unreviewed_correction_marks_a_page_stale(monkeypatch):
    monkeypatch.setattr(wd, "scan_wiki", lambda root=None: {"wiki/p.md": {"5"}})
    monkeypatch.setattr(wd, "merge_redirects", lambda: {})
    monkeypatch.setattr(wd, "live_entry_ids", lambda: {"5"})
    res = fold_with({"clm_intake_005_00": FakeBelief(corrections=["corr-1"])})
    row = wd.report(res)["rows"][0]
    assert row["corrected"] == ["5"] and row["stale"] is True


# --- the ruling itself ---------------------------------------------------------------------

def test_the_projection_appends_nothing_to_the_ledger():
    """SC5's whole point: a wiki page must not become a claim, so nothing here writes frames.

    Scoped to LEDGER writes. The first version of this guard forbade `.append(` outright and so
    banned `list.append`, the module's own idiom — a guard that fails on the compliant path is
    noise, and the way it fails teaches nothing about the property it was defending.
    """
    src = Path(wd.__file__).read_text()
    assert "make_frame" not in src, "emitting frames would make a wiki page a claim"
    assert not re.search(r"\b(?:ledger|led|Ledger\([^)]*\))\s*\.\s*append\s*\(", src), \
        "wiki_dependents must not write to the ledger"


def test_real_wiki_parses_and_every_edge_is_classified_exactly_once():
    """Runs against the real tree: counts must reconcile, or a bucket is silently swallowing edges."""
    pages = wd.scan_wiki()
    if not pages:
        return
    live = wd.live_entry_ids()
    redirects = wd.merge_redirects()
    assert live, "index parsed to zero entries"
    for nums in pages.values():
        for num in nums:
            resolved, how = wd.resolve(num, redirects, live)
            assert how in {"direct", "merged", "dangling"}
            assert (resolved is None) == (how == "dangling")

"""SC62 — the FM-5 fan-out outcome adapter, and specifically its bounds.

What is pinned here, in the order this program has been burned:

* **A point estimate is refused.** The projected `value` is a `Bound`, not a number; the
  claim TEXT — the only path a figure takes into the ledger, since `to_frames` emits
  `display_text` and never `value` — must carry the rendered band; and the obvious ways to
  collapse a `Bound` (`.point`, `float()`, unpacking) raise rather than quietly returning
  the low end.
* **`unknown` is never folded.** 501 subagents whose used/discarded split is unobservable
  are held out of every denominator. The mutation moves one into a bucket and pins that
  the band MOVES, so the hold-out is a real exclusion rather than a comment.
* **Absence is recorded, never filled** (§4.7). A subagent with no outcome is skipped and
  counted, not back-filled; a corpus with no outcomes at all projects zero rows.
* **The adapter registers NO ladder** and grading is unchanged for every other source.
  `claim_tuple.grade()` decides, and what it decides here is `Judged/Located` — this
  source has no codified protocol and cannot reach `Witnessed`.

Every positive below is paired with a mutation that removes the signal under test, because
a suite that only ever asserts refusals would pass just as well against an adapter that
refused everything, and one that only ever asserts `Judged` would pass against a grader
that graded everything down.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import fanout_outcome as fo  # noqa: E402

REAL_CORPUS = ROOT / "data" / "fanout_timing" / "merged.v2.jsonl"

COLLECTOR = "a" * 64
OTHER_COLLECTOR = "b" * 64


# --- fixture builders -------------------------------------------------------------------


def sub(ident, outcome, basis, total, new):
    return {"id": ident, "outcome": outcome, "outcome_basis": basis,
            "tokens": {"total": total, "new": new}}


#: 8 classified subagents: 4 `produced-and-used` of which exactly ONE is `git-landed`,
#: 2 discarded, 1 unknown, 1 aborted. Chosen so the head-count band (42.9%-85.7%) and the
#: total-token band (54.5%-95.5%) are DIFFERENT numbers — a fixture where they coincided
#: could not tell the two claims apart.
SUBAGENTS = [
    sub("s1", "produced-and-used", "git-landed", 100, 10),
    sub("s2", "produced-and-used", "parent-reference", 300, 30),
    sub("s3", "produced-and-used", "parent-reference", 300, 30),
    sub("s4", "produced-and-used", "parent-reference", 300, 30),
    sub("s5", "produced-and-discarded", "no-reuse-observed", 500, 50),
    sub("s6", "produced-and-discarded", "no-reuse-observed", 500, 50),
    sub("s7", "unknown", "parent-index-truncated", 900, 90),
    sub("s8", "aborted", "codex:turn_aborted", 200, 20),
]


def write_corpus(tmp_path, subagents=None, *, collector=COLLECTOR, extra_records=()):
    records = [{
        "schema": fo.CORPUS_SCHEMA,
        "collector_sha256": collector,
        "collected_at": "2026-09-07T16:30:12.279Z",
        "workflow_id": "wf-1",
        "source": "claude",
        "subagents": [dict(s) for s in (SUBAGENTS if subagents is None else subagents)],
    }]
    records.extend(extra_records)
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "merged.v2.jsonl"
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    return path


def tuples_for(path):
    return {n["quantity"]: fo.project(n) for n in fo.native_rows(path)}


# --- the bound rides in the tuple: a point estimate is refused ---------------------------


def test_every_projected_value_is_a_bound_that_refuses_to_collapse(tmp_path):
    """CATCHES the SC62 failure directly: a consumer reading one number out of the
    projection. There is no number to read — only `.low` and `.high`, which force the
    reader to name which end of the band they are quoting."""
    for quantity, tup in tuples_for(write_corpus(tmp_path)).items():
        assert isinstance(tup.value, fo.Bound), quantity
        with pytest.raises(fo.BoundReadError):
            tup.value.point
        with pytest.raises(fo.BoundReadError):
            float(tup.value)
        with pytest.raises(fo.BoundReadError):
            low, high = tup.value  # noqa: F841 — unpacking is a collapse too


def test_the_low_and_high_ends_are_readable_by_name(tmp_path):
    """MUTATION for the test above. Without it, that test would also pass against a Bound
    that refused EVERY read and carried no measurement at all."""
    band = tuples_for(write_corpus(tmp_path))["headcount_waste"].value
    assert band.low == pytest.approx(3 / 7)   # 7 known - 4 observed-used
    assert band.high == pytest.approx(6 / 7)  # 7 known - 1 proven-used
    assert band.low_basis and band.high_basis


def test_a_scalar_value_is_refused_by_the_projection_guard(tmp_path):
    """CATCHES a future edit that swaps the Bound for the low end 'for convenience'. A
    scalar here IS the point estimate the row forbids."""
    tup = tuples_for(write_corpus(tmp_path))["headcount_waste"]
    with pytest.raises(ct.ProjectionError, match="value must be a Bound"):
        fo._require_bounded(ct.ClaimTuple(**{**tup.__dict__, "value": 0.4}))


def test_a_claim_text_stripped_of_its_bound_is_refused(tmp_path):
    """CATCHES the leak that matters most: `to_frames` emits `claim` as `display_text` and
    never emits `value`, so a claim text without its band puts a naked figure in the ledger
    while the tuple still looks correct."""
    tup = tuples_for(write_corpus(tmp_path))["headcount_waste"]
    naked = "fan-out waste is 42.9% of subagents. " + fo.SCOPE_LIMIT
    with pytest.raises(ct.ProjectionError, match="does not carry the bound"):
        fo._require_bounded(ct.ClaimTuple(**{**tup.__dict__, "claim": naked}))


def test_the_guard_accepts_the_claim_the_adapter_actually_builds(tmp_path):
    """MUTATION for the test above. Without it, that test would also pass against a guard
    that rejected every claim text unconditionally."""
    tup = tuples_for(write_corpus(tmp_path))["headcount_waste"]
    assert fo._require_bounded(tup) is tup
    assert tup.value.render() in tup.claim


def test_the_bound_reaches_the_ledger_through_the_frame_display_text(tmp_path):
    """CATCHES a guard that is correct on the tuple and inert where it counts. Asserted on
    the emitted FRAME, because that is what a downstream citer reads."""
    frames = fo.frames_for_corpus(write_corpus(tmp_path), as_of="2026-09-07T00:00:00Z")
    claims = [f for f in frames if f["frame_type"].endswith("claim_proposed/v1")]
    assert len(claims) == 5, "one claim per bounded quantity"
    headcount = [c for c in claims
                 if "fanout_subagent_waste_share" in c["assertion"]["display_text"]]
    assert len(headcount) == 1
    text = headcount[0]["assertion"]["display_text"]
    assert "42.9%" in text and "85.7%" in text, "a band end went missing from the ledger"
    assert "BAND" in text and fo.SCOPE_LIMIT in text


def test_a_floor_never_renders_an_upper_bound(tmp_path):
    """CATCHES reading `blocked = 0` as a finding. The floor must say out loud that nothing
    bounds it from above, or a reader takes it as 'nothing was blocked'."""
    tup = tuples_for(write_corpus(tmp_path))["blocked_floor"]
    assert tup.value.kind == "floor" and tup.value.high is None
    assert "AT LEAST 0.0%" in tup.claim and "NO UPPER BOUND" in tup.claim


def test_a_floor_carrying_an_upper_bound_is_refused():
    """MUTATION for the test above: `Bound` must actually enforce the floor shape, not just
    happen to be constructed with `high=None` at one call site."""
    with pytest.raises(ct.ProjectionError, match="floor has no upper bound"):
        fo.Bound(low=0.0, high=1.0, kind="floor", unit="share_x",
                 low_basis="observed", high_basis="none")


def test_a_census_must_be_exact():
    """CATCHES a census quietly widened into an interval — 501 unknowns is a COUNT, and a
    range there would be an invented uncertainty."""
    with pytest.raises(ct.ProjectionError, match="census is exact"):
        fo.Bound(low=501.0, high=502.0, kind="census", unit="subagents",
                 low_basis="counted", high_basis="counted")


def test_a_bound_whose_ends_rest_on_unnamed_evidence_is_refused():
    """CATCHES the band being mistaken for a confidence interval. The two ends rest on
    DIFFERENT EVIDENCE (`parent-reference` vs `git-landed`), not on different confidence,
    and a reader who mistakes it for noise will average it."""
    with pytest.raises(ct.ProjectionError, match="low_basis is required"):
        fo.Bound(low=0.4, high=0.95, kind="interval", unit="share_x",
                 low_basis="", high_basis="git-landed")


def test_a_bound_with_named_evidence_is_accepted():
    """MUTATION for the test above — without it, that test would pass against a Bound that
    refused every construction."""
    band = fo.Bound(low=0.4, high=0.95, kind="interval", unit="share_x",
                    low_basis="parent-reference", high_basis="git-landed")
    assert "BAND" in band.render() and "parent-reference" in band.render()


# --- `unknown` is never folded -----------------------------------------------------------


def test_unknown_is_held_out_of_every_denominator(tmp_path):
    """CATCHES an unknown silently entering a share. 8 classified, 1 unknown, so every
    share is computed over 7 — and the tuple says so in `reps_basis` and in the claim."""
    tups = tuples_for(write_corpus(tmp_path))
    for quantity in ("headcount_waste", "token_waste_total", "token_waste_new"):
        tup = tups[quantity]
        assert tup.reps == 7, quantity
        assert "held out and never folded" in tup.reps_basis
        assert "never folded into a bucket" in tup.claim
        assert tup.extra["unknown_unfolded"] == 1
        assert tup.extra["known_subagents"] == 7


def test_folding_an_unknown_into_a_bucket_moves_the_band(tmp_path):
    """MUTATION for the test above, and the one that makes it mean something: reclassify the
    unknown as discarded and the band MUST move. Without this, the hold-out could be a
    docstring over a denominator that never excluded anything."""
    folded = [dict(s) for s in SUBAGENTS]
    folded[6] = sub("s7", "produced-and-discarded", "no-reuse-observed", 900, 90)
    before = tuples_for(write_corpus(tmp_path / "a"))
    after = tuples_for(write_corpus(tmp_path / "b", subagents=folded))
    assert before["headcount_waste"].reps == 7
    assert after["headcount_waste"].reps == 8
    assert after["headcount_waste"].value.low != before["headcount_waste"].value.low
    assert after["unknown_census"].value.low == 0


def test_the_unknown_census_is_its_own_exact_claim(tmp_path):
    """CATCHES the unknowns being recorded only as a caveat inside another claim, where a
    consumer citing that claim would inherit them invisibly. They get their own citable,
    retractable belief."""
    tup = tuples_for(write_corpus(tmp_path))["unknown_census"]
    assert tup.value.kind == "census"
    assert tup.value.low == tup.value.high == 1.0
    assert "EXACTLY 1" in tup.claim
    assert tup.metric == "fanout_unclassifiable_subagents"


# --- absence is recorded, never filled (§4.7) --------------------------------------------


def test_a_subagent_without_an_outcome_is_skipped_not_backfilled(tmp_path):
    """CATCHES a pre-FM-5 (schema v1) row being given a bucket on read. A tuple invented on
    read claims warrant the original walk never captured."""
    rows = [dict(s) for s in SUBAGENTS] + [{"id": "s9", "tokens": {"total": 9999, "new": 999}}]
    tup = tuples_for(write_corpus(tmp_path, subagents=rows))["headcount_waste"]
    assert tup.extra["classified_subagents"] == 8, "the outcome-less row was back-filled"
    assert tup.extra["skipped_no_outcome"] == 1
    assert "carry no outcome at all" in tup.claim
    assert sum(tup.extra["outcome_counts"].values()) == 8


def test_the_same_subagent_counts_once_it_carries_an_outcome(tmp_path):
    """MUTATION for the test above. Without it, that test would also pass against a reader
    that dropped every subagent it saw."""
    rows = [dict(s) for s in SUBAGENTS] + [
        sub("s9", "produced-and-discarded", "no-reuse-observed", 9999, 999)]
    tup = tuples_for(write_corpus(tmp_path, subagents=rows))["headcount_waste"]
    assert tup.extra["classified_subagents"] == 9
    assert tup.extra["skipped_no_outcome"] == 0


def test_a_corpus_with_no_outcomes_at_all_projects_zero_rows(tmp_path):
    """CATCHES a pre-hook corpus being reconstructed on read (the DF2-4 / benchmarks/results
    precedent). Nothing to project is projected as nothing, never as zero-percent waste."""
    rows = [{"id": "s1", "tokens": {"total": 5, "new": 1}}]
    assert fo.native_rows(write_corpus(tmp_path, subagents=rows)) == ()


def test_a_populated_corpus_projects_five_rows(tmp_path):
    """MUTATION for the test above — without it, a reader that returned () unconditionally
    would pass."""
    assert len(fo.native_rows(write_corpus(tmp_path))) == 5


def test_a_missing_corpus_file_projects_zero_rows(tmp_path):
    """CATCHES a missing corpus being reported as an empty measurement."""
    assert fo.native_rows(tmp_path / "absent.jsonl") == ()


# --- strictness: identity refusals -------------------------------------------------------


def test_two_collector_digests_in_one_corpus_are_refused(tmp_path):
    """CATCHES the fake-identity failure this substrate exists to detect: verdicts from two
    DIFFERENT classifier versions averaged into one share, which belongs to neither."""
    other = {"schema": fo.CORPUS_SCHEMA, "collector_sha256": OTHER_COLLECTOR,
             "collected_at": "2026-09-07T16:30:12.279Z", "workflow_id": "wf-2",
             "subagents": [sub("t1", "produced-and-used", "git-landed", 10, 1)]}
    with pytest.raises(ct.ProjectionError, match="distinct collector_sha256"):
        fo.native_rows(write_corpus(tmp_path, extra_records=[other]))


def test_one_collector_digest_projects(tmp_path):
    """MUTATION for the test above: without it, a reader that refused every corpus would
    satisfy the refusal test."""
    same = {"schema": fo.CORPUS_SCHEMA, "collector_sha256": COLLECTOR,
            "collected_at": "2026-09-07T16:30:12.279Z", "workflow_id": "wf-2",
            "subagents": [sub("t1", "produced-and-used", "git-landed", 10, 1)]}
    tup = tuples_for(write_corpus(tmp_path, extra_records=[same]))["headcount_waste"]
    assert tup.extra["classified_subagents"] == 9
    assert tup.extra["collector_sha256"] == COLLECTOR


def test_an_unrecognised_outcome_bucket_refuses_the_whole_corpus(tmp_path):
    """CATCHES this adapter's bucket mirror going stale against the D9-gated collector. A
    bucket it does not know silently changes every denominator, so drift is made loud
    instead of degrading into a wrong share."""
    rows = [dict(s) for s in SUBAGENTS] + [sub("s9", "produced-and-deferred", "x", 1, 1)]
    with pytest.raises(ct.ProjectionError, match="unrecognised outcome bucket"):
        fo.native_rows(write_corpus(tmp_path, subagents=rows))


def test_the_mirrored_bucket_set_matches_the_collector_source():
    """MUTATION for the test above, read off the collector's own source rather than a copy
    of the copy: the refusal is only meaningful if the mirror is currently correct."""
    src = (ROOT / "scripts" / "coordination" / "fanout_timing.py").read_text()
    block = src.split("OUTCOME_BUCKETS = (", 1)[1].split(")", 1)[0]
    declared = tuple(line.strip().strip('",') for line in block.splitlines() if '"' in line)
    assert declared == fo.OUTCOME_BUCKETS


def test_project_rejects_a_bare_or_unknown_native(tmp_path):
    """CATCHES `project()` being reachable around `native_rows()`, which is where every
    strictness check above lives."""
    for bad in ({}, {"quantity": "made_up", "corpus": {}}, "not-a-mapping"):
        with pytest.raises(ct.ProjectionError):
            fo.project(bad)


# --- carrier conformance: project, never grade -------------------------------------------


def test_the_adapter_registers_a_projection_and_no_ladder():
    """CATCHES the §4.7 violation the registry exists to stop: a source class growing a
    second grading rule, which becomes two dialects of one constitution."""
    assert fo.SOURCE_KIND in ct.registered()
    assert ct.source_classes()[fo.SOURCE_KIND] == ct.MEASUREMENT_CLASS
    # A subset check, not equality: `literature` only appears once research_intake is
    # imported, and this test must pin what THIS adapter did, not which siblings pytest
    # happened to load. The module check below is the load-bearing half.
    assert set(ct.ladders()) <= {"measurement", "literature"}
    assert "measurement" in ct.ladders()
    assert not any("fanout_outcome" in mod for mod, _ in ct.ladders().values())


def test_grading_is_unchanged_for_other_sources(tmp_path, monkeypatch):
    """MUTATION-style companion to the test above: importing this adapter must not move any
    other source's grade. A full measurement tuple whose digest WAS verified at the write
    boundary still reaches Witnessed/Attested."""
    artifact = tmp_path / "run.json"
    artifact.write_text("{}")
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    other = ct.ClaimTuple(
        measurement_id="unrelated", metric="tps", value=1.0, date="2026-09-07",
        category="BASELINE", claim="unrelated measurement", protocol_id="bench-cpu",
        reps=3, attestation_path="run.json",
        attestation_sha256=hashlib.sha256(b"{}").hexdigest(),
        attestation_verified=True)
    assert ct.grade(other)[:2] == ("Witnessed", "Attested")


def test_this_source_cannot_reach_witnessed_and_the_ladder_says_why(tmp_path):
    """CATCHES a protocol id being invented to clear a bar. `fanout_timing.v2` is the output
    SCHEMA version, not a replayable procedure, and no codified protocol covers transcript
    forensics — so every tuple here is an OBSERVATION."""
    for quantity, tup in tuples_for(write_corpus(tmp_path)).items():
        assert tup.protocol_id == "", quantity
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located"), reasons
        assert any("OBSERVATION" in r for r in reasons)
        # The corpus digest is carried anyway, so a codified protocol lifts this without
        # re-projection — the cap is the missing protocol, not a missing attestation.
        assert len(tup.attestation_sha256) == 64


def test_the_ladder_would_lift_this_source_if_a_protocol_existed(tmp_path, monkeypatch):
    """MUTATION for the test above. Without it, the Judged/Located assertion would also pass
    against a grader that graded everything down, proving nothing about this source."""
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    corpus = write_corpus(tmp_path)
    tup = tuples_for(corpus)["headcount_waste"]
    lifted = ct.ClaimTuple(**{**tup.__dict__, "protocol_id": "fanout-forensics-v1",
                              "attestation_path": corpus.name})
    # The corpus file is real and the recorded digest is the file's own self-hash, so the
    # write-boundary verification genuinely matches here (SC69).
    import hashlib
    lifted = ct.ClaimTuple(**{**lifted.__dict__,
                              "attestation_verified": True if hashlib.sha256(
                                  (tmp_path / corpus.name).read_bytes()
                              ).hexdigest() == lifted.attestation_sha256 else None})
    assert ct.grade(lifted)[:2] == ("Witnessed", "Attested")


def test_the_head_count_and_token_claims_are_separate_beliefs(tmp_path):
    """CATCHES the two being bundled into one tuple. The row is explicit that they are
    different claims about different things; `claim_id` derives from `measurement_id`, so
    bundling would make the one you meant uncitable and unretractable on its own."""
    tups = tuples_for(write_corpus(tmp_path))
    ids = {t.measurement_id for t in tups.values()}
    assert len(ids) == 5, "bounded quantities collapsed into one claim"
    assert tups["headcount_waste"].value.low != tups["token_waste_total"].value.low
    assert "not about subagents" in tups["token_waste_total"].claim
    assert "SUBAGENT COUNTS" in tups["headcount_waste"].claim
    assert "Provider-cumulative" in tups["token_waste_new"].claim


# --- the real corpus ---------------------------------------------------------------------


@pytest.mark.skipif(not REAL_CORPUS.is_file(), reason="FM-5 corpus absent")
def test_the_committed_corpus_projects_its_five_bounded_claims():
    """The committed 14,004-workflow corpus, pinned exactly. This test trips the moment the
    collector is re-run and the corpus recollected — which is precisely when the
    source-table row in adapters/README.md must be re-checked."""
    tups = tuples_for(REAL_CORPUS)
    assert set(tups) == {"headcount_waste", "token_waste_total", "token_waste_new",
                         "blocked_floor", "unknown_census"}
    head = tups["headcount_waste"]
    assert head.extra["classified_subagents"] == 4278
    assert head.extra["known_subagents"] == 3777
    assert head.extra["unknown_unfolded"] == 501
    assert head.extra["proven_used_count"] == 171
    assert head.value.low == pytest.approx(0.400318, abs=1e-6)
    assert head.value.high == pytest.approx(0.954726, abs=1e-6)
    assert "40.0%" in head.claim and "95.5%" in head.claim

    # The 86.5% headline is the LOW end of the token band, never the band itself.
    assert tups["token_waste_total"].value.low == pytest.approx(0.865315, abs=1e-6)
    assert tups["token_waste_total"].value.high == pytest.approx(0.997436, abs=1e-6)
    assert tups["token_waste_new"].value.low == pytest.approx(0.837690, abs=1e-6)

    assert tups["blocked_floor"].value.low == 0.0
    assert tups["blocked_floor"].value.high is None
    assert tups["unknown_census"].value.low == 501.0

    for tup in tups.values():
        assert ct.grade(tup)[:2] == ("Judged", "Located")
        assert tup.attestation_path == "data/fanout_timing/merged.v2.jsonl"

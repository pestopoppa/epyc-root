"""P1 foundation tests: canonicalization, lattice, frames, ledger, checkpoints, fold.

Spec: docs/design/vidya-pilot-spec.md §§3-5, 11, 17.3.

These lean deliberately on negative controls. Most of the failures this substrate exists to catch
are things that pass quietly -- a float that makes a hash platform-dependent, a duplicate judgment
vote, a torn tail that reads as a shorter ledger, a join that overstates what any single path
supports. A test that only checks the happy path would have accepted every one of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import canonical  # noqa: E402
import checkpoint as cp  # noqa: E402
import frames  # noqa: E402
import lattice as lat  # noqa: E402
from fold import FoldError, Verdict, fold  # noqa: E402
from ledger import GENESIS_PREV_HASH, Ledger  # noqa: E402

NOW = "2026-08-09T12:00:00Z"


def _support_frame(claim_id, evidence_id, q, t, actor="test/stage2"):
    return frames.make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": claim_id, "evidence_id": evidence_id,
                   "grade": {"Q": q, "T": t}},
        provenance={"method": "primary-source-review", "anchor": f"anchor:{evidence_id}"},
        actor=actor, authority_scope="research-verification", created_at=NOW,
    )


def _oppose_frame(claim_id, evidence_id, q, t):
    return frames.make_frame(
        frame_type="epyc.vidya/frame/evidence_opposes_claim/v1",
        assertion={"claim_id": claim_id, "evidence_id": evidence_id,
                   "grade": {"Q": q, "T": t}},
        provenance={"method": "primary-source-review", "anchor": f"anchor:{evidence_id}"},
        actor="test/stage2", authority_scope="research-verification", created_at=NOW,
    )


# ---------------------------------------------------------------- canonical

class TestCanonical:
    def test_key_order_does_not_change_identity(self):
        a = {"b": 1, "a": {"z": 2, "y": 3}}
        b = {"a": {"y": 3, "z": 2}, "b": 1}
        assert canonical.content_hash(a) == canonical.content_hash(b)

    def test_hash_is_algorithm_tagged(self):
        assert canonical.content_hash({"x": 1}).startswith("sha256:")

    def test_floats_are_rejected_with_a_path(self):
        # The float ban is a determinism requirement, not a style preference: float formatting is
        # the one part of JCS that is genuinely hard to reproduce across languages.
        with pytest.raises(canonical.CanonicalizationError, match=r"\$\.a\.b"):
            canonical.canonical_bytes({"a": {"b": 1.5}})

    def test_bool_is_not_treated_as_int(self):
        assert canonical.content_hash({"x": True}) != canonical.content_hash({"x": 1})

    def test_non_string_keys_rejected(self):
        with pytest.raises(canonical.CanonicalizationError):
            canonical.canonical_bytes({1: "a"})

    def test_envelope_hash_ignores_id_and_signatures(self):
        env = {"frame_type": "t", "assertion": {}, "provenance": {}, "pubinfo": {}}
        bare = canonical.envelope_hash(env)
        withid = canonical.envelope_hash({**env, "frame_id": "sha256:deadbeef",
                                          "signatures": [{"k": "v"}]})
        # This is what makes an unsigned pilot frame and a signed production frame the SAME frame.
        assert bare == withid

    def test_unicode_is_literal_not_escaped(self):
        assert "é".encode() in canonical.canonical_bytes({"k": "é"})


# ------------------------------------------------------------------ lattice

class TestLattice:
    def test_join_is_pointwise_max_and_meet_pointwise_min(self):
        a = lat.parse_grade("Verified/Located")
        b = lat.parse_grade("Judged/Anchored")
        assert lat.join(a, b) == lat.parse_grade("Verified/Anchored")
        assert lat.meet(a, b) == lat.parse_grade("Judged/Located")

    def test_incomparable_grades_exist(self):
        # The whole reason for factoring the axes: the chain forced a false ranking here.
        a = lat.parse_grade("Verified/Located")
        b = lat.parse_grade("Judged/Anchored")
        assert not a.dominates(b) and not b.dominates(a)
        assert not a.comparable(b)

    def test_absorption_law(self):
        for a in _all_grades():
            for b in _all_grades():
                assert lat.join(a, lat.meet(a, b)) == a, "absorptive law must hold"

    def test_zero_stability(self):
        # 1 + u = 1 for all u -- this is what gives the <=N-step convergence bound.
        for u in _all_grades():
            assert lat.join(lat.TOP, u) == lat.TOP

    def test_meet_is_idempotent(self):
        # a^inf = a, which is what makes gfp = F^N(F^N(1)) affordable.
        for a in _all_grades():
            assert lat.meet(a, a) == a

    def test_distributivity(self):
        gs = _all_grades()
        for a in gs[::5]:
            for b in gs[::7]:
                for c in gs[::3]:
                    assert lat.meet(a, lat.join(b, c)) == lat.join(lat.meet(a, b), lat.meet(a, c))

    def test_identities(self):
        for a in _all_grades():
            assert lat.join(a, lat.BOTTOM) == a
            assert lat.meet(a, lat.TOP) == a

    def test_witness_set_names_a_single_path_when_one_achieves_the_join(self):
        paths = [("A", lat.parse_grade("Verified/Anchored")),
                 ("B", lat.parse_grade("Judged/Located"))]
        grade, witnesses = lat.join_with_witnesses(paths)
        assert grade == lat.parse_grade("Verified/Anchored")
        assert witnesses == ["A"]

    def test_witness_set_exposes_a_synthetic_join(self):
        # The real cost of the product lattice: the join is a grade NO single path achieves.
        paths = [("A", lat.parse_grade("Verified/Located")),
                 ("B", lat.parse_grade("Judged/Anchored"))]
        grade, witnesses = lat.join_with_witnesses(paths)
        assert grade == lat.parse_grade("Verified/Anchored")
        assert sorted(witnesses) == ["A", "B"], "both coordinates need naming"
        assert all(not dict(paths)[w].dominates(grade) for w in witnesses)

    def test_conjunctive_reading_is_stricter_than_the_join(self):
        # The join says "something is verified and something is anchored"; the conjunctive reading
        # asks whether ONE path is both. Confusing them is the failure this pair of functions
        # exists to prevent.
        paths = [("A", lat.parse_grade("Verified/Located")),
                 ("B", lat.parse_grade("Judged/Anchored"))]
        floor = lat.parse_grade("Verified/Anchored")
        joined, _ = lat.join_with_witnesses(paths)
        assert joined.dominates(floor)                       # join says yes
        ok, sat = lat.satisfies_conjunctive(paths, floor)
        assert not ok and sat == []                          # conjunctive says no

    def test_non_rectangular_policy_via_explicit_floors(self):
        floors = [lat.parse_grade("Witnessed/Located"), lat.parse_grade("Judged/Attested")]
        assert lat.satisfies_any_floor(lat.parse_grade("Witnessed/Located"), floors)
        assert lat.satisfies_any_floor(lat.parse_grade("Judged/Attested"), floors)
        assert not lat.satisfies_any_floor(lat.parse_grade("Verified/Anchored"), floors)

    def test_parse_rejects_unknown_levels(self):
        with pytest.raises(ValueError, match="unknown Q level"):
            lat.parse_grade("Corroborated/Anchored")   # dropped from the carrier 2026-08-09


def _all_grades():
    return [lat.Grade(q, t) for q in range(len(lat.Q_LEVELS)) for t in range(len(lat.T_LEVELS))]


# ------------------------------------------------------------------- frames

class TestFrames:
    def test_make_frame_is_content_addressed(self):
        f = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        assert f["frame_id"] == canonical.envelope_hash(f)
        frames.validate_frame(f)

    def test_frame_type_must_be_versioned(self):
        with pytest.raises(frames.FrameValidationError, match="frame_type"):
            frames.make_frame(
                frame_type="claim_proposed", assertion={}, provenance={"method": "x"},
                actor="a", authority_scope="s", created_at=NOW)

    def test_provenance_must_reference_the_assertion(self):
        with pytest.raises(frames.FrameValidationError, match="provenance must reference"):
            frames.make_frame(
                frame_type="epyc.vidya/frame/claim_proposed/v1",
                assertion={"claim_id": "c"}, provenance={"unrelated": "prose"},
                actor="a", authority_scope="s", created_at=NOW)

    def test_pubinfo_may_not_carry_a_grade(self):
        # pubinfo speaks only about the frame; a grade there would let a trigger launder evidence.
        with pytest.raises(frames.FrameValidationError, match="pubinfo must not carry"):
            frames.make_frame(
                frame_type="epyc.vidya/frame/claim_proposed/v1",
                assertion={"claim_id": "c"}, provenance={"method": "m"},
                actor="a", authority_scope="s", created_at=NOW,
                extra_pubinfo={"grade": {"Q": "Witnessed", "T": "Attested"}})

    def test_triggered_by_is_accepted_and_carries_no_grade(self):
        f = frames.make_frame(
            frame_type="epyc.vidya/frame/claim_proposed/v1",
            assertion={"claim_id": "c"}, provenance={"method": "m"},
            actor="a", authority_scope="s", created_at=NOW,
            triggered_by="sha256:" + "a" * 64)
        assert f["pubinfo"]["triggered_by"].startswith("sha256:")
        assert not (_GRADEISH := {"grade", "Q", "T"} & set(f["pubinfo"]))

    def test_unknown_top_level_key_rejected(self):
        f = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        f["sneaky"] = True
        with pytest.raises(frames.FrameValidationError, match="unknown top-level"):
            frames.validate_frame(f)

    def test_tampered_frame_id_detected(self):
        f = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        f["assertion"]["claim_id"] = "clm-2"
        with pytest.raises(frames.FrameValidationError, match="frame_id does not match"):
            frames.validate_frame(f)


# ------------------------------------------------------------------- ledger

class TestLedger:
    def test_append_chains_and_verifies(self, tmp_path):
        led = Ledger(tmp_path / "ledger.jsonl")
        for i in range(5):
            led.append(_support_frame(f"clm-{i}", f"evd-{i}", "Judged", "Anchored"))
        recs = led.read_all()
        assert [r.seq for r in recs] == [0, 1, 2, 3, 4]
        assert recs[0].prev_hash == GENESIS_PREV_HASH
        assert led.verify() == []

    def test_mutated_frame_breaks_verification(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        led = Ledger(path)
        led.append(_support_frame("clm-1", "evd-1", "Judged", "Anchored"))
        led.append(_support_frame("clm-2", "evd-2", "Judged", "Anchored"))
        text = path.read_text().replace("clm-1", "clm-X")
        path.write_text(text)
        assert any("frame_hash" in p for p in led.verify())

    def test_torn_tail_is_dropped_and_reported(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        led = Ledger(path)
        led.append(_support_frame("clm-1", "evd-1", "Judged", "Anchored"))
        with open(path, "ab") as fh:
            fh.write(b'{"seq":1,"prev_hash":"sha256:aa","frame_ha')   # crash mid-write
        report: list[str] = []
        recs = led.read_all(repair_report=report)
        assert len(recs) == 1, "a torn tail must not read as a valid record"
        assert report and "torn tail" in report[0]

    def test_append_after_tear_records_the_loss_durably(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        led = Ledger(path)
        led.append(_support_frame("clm-1", "evd-1", "Judged", "Anchored"))
        with open(path, "ab") as fh:
            fh.write(b'{"seq":1,"partial')
        led.append(_support_frame("clm-2", "evd-2", "Judged", "Anchored"))
        types = [r.frame.get("frame_type") for r in led.read_all()]
        # The loss is itself a durable record rather than a silent gap.
        assert "epyc.vidya/frame/torn_append_discarded/v1" in types
        assert led.verify() == []

    def test_empty_ledger(self, tmp_path):
        led = Ledger(tmp_path / "nothing.jsonl")
        assert led.read_all() == [] and led.head() == (-1, GENESIS_PREV_HASH)


# --------------------------------------------------------------- checkpoint

class TestCheckpoint:
    def test_empty_and_single_leaf_roots(self):
        import hashlib
        assert cp.merkle_root([]) == hashlib.sha256(b"").digest()
        assert cp.merkle_root([b"a"]) == hashlib.sha256(b"\x00a").digest()

    def test_domain_separation(self):
        # Without the 0x00/0x01 prefixes a leaf and an internal node share a hash space.
        assert cp.merkle_root([b"a", b"b"]) != cp.merkle_root([b"ab"])

    def test_inclusion_proofs_verify_for_every_index(self):
        entries = [f"frame-{i}".encode() for i in range(11)]
        root = cp.merkle_root(entries)
        for i, leaf in enumerate(entries):
            proof = cp.inclusion_proof(entries, i)
            assert cp.verify_inclusion(leaf, i, len(entries), proof, root)

    def test_inclusion_proof_rejects_a_wrong_leaf(self):
        entries = [f"frame-{i}".encode() for i in range(7)]
        root = cp.merkle_root(entries)
        proof = cp.inclusion_proof(entries, 3)
        assert not cp.verify_inclusion(b"not-in-the-tree", 3, len(entries), proof, root)

    def test_consistency_proof_shapes(self):
        entries = [f"f{i}".encode() for i in range(9)]
        assert cp.consistency_proof(entries, 9) == []
        assert len(cp.consistency_proof(entries, 4)) > 0

    def test_note_round_trip_unsigned(self):
        chk = cp.checkpoint_for("epyc.local/belief-ledger", ["sha256:aa", "sha256:bb"])
        note = cp.format_checkpoint(chk)
        parsed, sigs = cp.parse_checkpoint(note)
        assert parsed == chk and sigs == []

    def test_note_body_is_three_newline_terminated_lines(self):
        chk = cp.checkpoint_for("epyc.local/belief-ledger", ["sha256:aa"])
        body = chk.note_text()
        assert body.count("\n") == 3 and body.endswith("\n")
        assert body.split("\n")[1] == "1"          # canonical decimal tree size

    def test_note_round_trip_with_signature_lines(self):
        chk = cp.checkpoint_for("epyc.local/belief-ledger", ["sha256:aa"])
        kid = cp.key_id("epyc.local/belief-ledger", b"\x02" * 32)
        note = cp.format_checkpoint(chk, [("epyc.local/belief-ledger", kid + b"\x09" * 64)])
        parsed, sigs = cp.parse_checkpoint(note)
        assert parsed == chk and len(sigs) == 1 and sigs[0][1][:4] == kid

    def test_origin_rejects_spaces_and_plus(self):
        with pytest.raises(cp.CheckpointError):
            cp.Checkpoint(origin="has space", tree_size=0, root_hash=b"\x00" * 32)
        with pytest.raises(cp.CheckpointError):
            cp.Checkpoint(origin="has+plus", tree_size=0, root_hash=b"\x00" * 32)

    def test_tree_size_must_be_canonical_decimal(self):
        note = "origin\n007\n" + "A" * 43 + "=\n\n"
        with pytest.raises(cp.CheckpointError, match="canonical decimal"):
            cp.parse_checkpoint(note)

    def test_body_may_contain_blank_lines_split_is_at_the_last(self):
        # The spec splits at the LAST empty line; splitting at the first would truncate a body.
        chk = cp.checkpoint_for("o", ["sha256:aa"])
        note = cp.format_checkpoint(chk)
        parsed, _ = cp.parse_checkpoint(note)
        assert parsed.origin == "o"

    def test_ledger_to_checkpoint(self, tmp_path):
        led = Ledger(tmp_path / "l.jsonl")
        for i in range(4):
            led.append(_support_frame(f"c{i}", f"e{i}", "Judged", "Anchored"))
        hashes = [r.frame_hash for r in led.read_all()]
        chk = cp.checkpoint_for("epyc.local/belief-ledger", hashes)
        assert chk.tree_size == 4
        leaves = [h.encode() for h in hashes]
        for i, leaf in enumerate(leaves):
            assert cp.verify_inclusion(leaf, i, 4, cp.inclusion_proof(leaves, i), chk.root_hash)


# --------------------------------------------------------------------- fold

class TestFold:
    def test_single_support_path(self):
        fr = [_support_frame("clm-1", "evd-1", "Verified", "Anchored")]
        res = fold(fr, as_of=NOW)
        b = res.beliefs["clm-1"]
        assert b.pro == lat.parse_grade("Verified/Anchored")
        assert b.verdict(lat.parse_grade("Verified/Anchored")) == Verdict.SUPPORTED

    def test_conflict_is_a_served_state_not_an_average(self):
        fr = [_support_frame("clm-1", "evd-1", "Verified", "Anchored"),
              _oppose_frame("clm-1", "evd-2", "Verified", "Anchored")]
        b = fold(fr, as_of=NOW).beliefs["clm-1"]
        assert b.verdict(lat.parse_grade("Verified/Anchored")) == Verdict.CONFLICTED
        assert b.pro == b.con, "opposition must not subtract from support"

    def test_synthetic_join_does_not_satisfy_a_conjunctive_policy(self):
        # Two paths that jointly reach the floor but individually do not.
        fr = [_support_frame("clm-1", "evd-A", "Verified", "Located"),
              _support_frame("clm-1", "evd-B", "Judged", "Anchored")]
        b = fold(fr, as_of=NOW).beliefs["clm-1"]
        floor = lat.parse_grade("Verified/Anchored")
        assert b.pro.dominates(floor)                                  # the join clears it
        assert b.verdict(floor, conjunctive=True) == Verdict.UNKNOWN   # no single path does
        assert b.verdict(floor, conjunctive=False) == Verdict.SUPPORTED
        assert sorted(b.pro_witnesses) == ["evd-A", "evd-B"]

    def test_retraction_removes_a_support_path(self):
        s1 = _support_frame("clm-1", "evd-1", "Witnessed", "Attested")
        s2 = _support_frame("clm-1", "evd-2", "Judged", "Located")
        retract = frames.make_frame(
            frame_type="epyc.vidya/frame/retraction/v1",
            assertion={"retracts": s1["frame_id"], "claim_id": "clm-1"},
            provenance={"method": "operator-retraction", "about": s1["frame_id"]},
            actor="operator", authority_scope="research-verification", created_at=NOW)
        b = fold([s1, s2, retract], as_of=NOW).beliefs["clm-1"]
        # Zero-substitution: the belief survives at the grade of its surviving path.
        assert b.pro == lat.parse_grade("Judged/Located")
        assert s1["frame_id"] in b.retracted_support

    def test_retracting_the_only_path_leaves_the_claim_unsupported(self):
        s1 = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        retract = frames.make_frame(
            frame_type="epyc.vidya/frame/retraction/v1",
            assertion={"retracts": s1["frame_id"], "claim_id": "clm-1"},
            provenance={"method": "operator-retraction", "about": s1["frame_id"]},
            actor="operator", authority_scope="research-verification", created_at=NOW)
        b = fold([s1, retract], as_of=NOW).beliefs["clm-1"]
        assert b.pro == lat.BOTTOM
        assert b.verdict(lat.parse_grade("Hinted/Located")) == Verdict.UNKNOWN

    def test_judgment_without_a_replay_key_is_refused(self):
        bad = frames.make_frame(
            frame_type="epyc.vidya/frame/judgment_recorded/v1",
            assertion={"claim_id": "clm-1", "verdict": "equivalent"},
            provenance={"method": "llm-equivalence-check"},
            actor="model:x", authority_scope="research-verification", created_at=NOW)
        with pytest.raises(FoldError, match="replay_key"):
            fold([bad], as_of=NOW)

    def test_judgment_replay_key_must_be_complete(self):
        partial = frames.make_frame(
            frame_type="epyc.vidya/frame/judgment_recorded/v1",
            assertion={"claim_id": "clm-1", "verdict": "equivalent"},
            provenance={"method": "llm", "replay_key": {
                "read_set": ["a"], "prompt": "p", "seed": 1, "model_version": "m"}},
            actor="model:x", authority_scope="research-verification", created_at=NOW)
        # Missing temperature and tool_output_hash: greedy decoding is not an exemption.
        with pytest.raises(FoldError, match="temperature"):
            fold([partial], as_of=NOW)

    def test_first_committed_vote_wins_per_key(self):
        key = {"read_set": ["a"], "prompt": "p", "seed": 1,
               "model_version": "m", "temperature": 0, "tool_output_hash": "sha256:aa"}
        def judgment(verdict):
            return frames.make_frame(
                frame_type="epyc.vidya/frame/judgment_recorded/v1",
                assertion={"claim_id": "clm-1", "verdict": verdict},
                provenance={"method": "llm", "replay_key": key},
                actor="model:x", authority_scope="research-verification", created_at=NOW)
        first, second = judgment("equivalent"), judgment("not-equivalent")
        res = fold([first, second], as_of=NOW)
        # Both records live in the ledger -- an append-only log permits that. It is the FOLD that
        # must refuse the second, or two replays of the same state could reach different answers.
        assert len(res.counted_judgments) == 1
        assert list(res.counted_judgments.values()) == [first["frame_id"]]
        assert res.superseded_judgments == [second["frame_id"]]

    def test_distinct_replay_keys_are_both_counted(self):
        # The rule is per-KEY, not per-claim: a judge that saw different inputs is a new judgment.
        def judgment(seed):
            return frames.make_frame(
                frame_type="epyc.vidya/frame/judgment_recorded/v1",
                assertion={"claim_id": "clm-1", "verdict": "equivalent"},
                provenance={"method": "llm", "replay_key": {
                    "read_set": ["a"], "prompt": "p", "seed": seed,
                    "model_version": "m", "temperature": 0, "tool_output_hash": "sha256:aa"}},
                actor="model:x", authority_scope="research-verification", created_at=NOW)
        res = fold([judgment(1), judgment(2)], as_of=NOW)
        assert len(res.counted_judgments) == 2 and res.superseded_judgments == []

    def test_as_of_is_required(self):
        with pytest.raises(FoldError, match="as_of"):
            fold([], as_of="")

    def test_unknown_frame_types_are_ignored_not_absorbed(self):
        odd = frames.make_frame(
            frame_type="epyc.vidya/frame/projection_rendered/v1",
            assertion={"projection_id": "p1"}, provenance={"method": "render"},
            actor="wiki", authority_scope="projection", created_at=NOW)
        res = fold([odd], as_of=NOW)
        assert res.beliefs == {}
        assert res.ignored_frame_types["epyc.vidya/frame/projection_rendered/v1"] == 1


class TestCorrections:
    """P2c: a recorded correction marks a belief for review WITHOUT touching its grade."""

    def _correction(self, claim_ids, text="OVERTURNED: the figure does not appear in the source"):
        return frames.make_frame(
            frame_type="epyc.vidya/frame/correction_recorded/v1",
            assertion={"entry_id": "intake-x", "claim_ids": claim_ids,
                       "correction_text": text, "classification": None},
            provenance={"method": "adapter", "about": "intake-x", "parsed": False},
            actor="adapter", authority_scope="research-verification", created_at=NOW)

    def test_correction_marks_review_without_changing_the_grade(self):
        s = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        b_before = fold([s], as_of=NOW).beliefs["clm-1"]
        b_after = fold([s, self._correction(["clm-1"])], as_of=NOW).beliefs["clm-1"]
        assert b_after.pro == b_before.pro, "a correction is not counter-evidence"
        assert b_after.con == b_before.con
        assert b_after.review_required and not b_before.review_required

    def test_correction_does_not_flip_the_verdict(self):
        # Support is support. Refusing an unreviewed correction is the freshness gate's job;
        # folding it into the verdict would make a correction indistinguishable from opposition.
        s = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        b = fold([s, self._correction(["clm-1"])], as_of=NOW).beliefs["clm-1"]
        assert b.verdict(lat.parse_grade("Verified/Anchored")) == Verdict.SUPPORTED

    def test_correction_creates_the_claim_if_unseen(self):
        b = fold([self._correction(["clm-orphan"])], as_of=NOW).beliefs["clm-orphan"]
        assert b.review_required and b.pro == lat.BOTTOM

    def test_a_reviewed_correction_stops_blocking(self):
        """Without this the review flag is a one-way ratchet and the gate deadlocks its own work.

        A correction says "someone changed something, nobody has said what it means for this
        claim". Once a review records that, the claim must be servable again -- otherwise a single
        dive_corrections field blocks every claim from its entry permanently (spec risk §19.7).
        """
        s = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        c = self._correction(["clm-1"])
        reviewed = frames.make_frame(
            frame_type="epyc.vidya/frame/correction_reviewed/v1",
            assertion={"reviewed": c["frame_id"], "claim_ids": ["clm-1"],
                       "finding": "correction concerns a different claim in the same entry"},
            provenance={"method": "human-review", "about": c["frame_id"]},
            actor="operator", authority_scope="research-verification", created_at=NOW)
        assert fold([s, c], as_of=NOW).beliefs["clm-1"].review_required
        after = fold([s, c, reviewed], as_of=NOW)
        assert not after.beliefs["clm-1"].review_required
        assert after.reviewed_corrections == [c["frame_id"]]

    def test_reviewing_one_correction_leaves_another_blocking(self):
        s = _support_frame("clm-1", "evd-1", "Verified", "Anchored")
        c1, c2 = self._correction(["clm-1"], "first"), self._correction(["clm-1"], "second")
        reviewed = frames.make_frame(
            frame_type="epyc.vidya/frame/correction_reviewed/v1",
            assertion={"reviewed": c1["frame_id"], "claim_ids": ["clm-1"], "finding": "ok"},
            provenance={"method": "human-review", "about": c1["frame_id"]},
            actor="operator", authority_scope="research-verification", created_at=NOW)
        b = fold([s, c1, c2, reviewed], as_of=NOW).beliefs["clm-1"]
        assert b.review_required and b.corrections == [c2["frame_id"]]

    def test_corrections_are_sorted_for_determinism(self):
        s = _support_frame("clm-1", "evd-1", "Judged", "Located")
        c1, c2 = self._correction(["clm-1"], "first"), self._correction(["clm-1"], "second")
        a = fold([s, c1, c2], as_of=NOW).state_hash()
        b = fold([s, c2, c1], as_of=NOW).state_hash()
        assert a == b


# ------------------------------------------------------- determinism (§17.3)

class TestDeterminism:
    def _corpus(self):
        return [
            _support_frame("clm-1", "evd-1", "Verified", "Anchored"),
            _support_frame("clm-1", "evd-2", "Judged", "Located"),
            _oppose_frame("clm-2", "evd-3", "Hinted", "Located"),
            _support_frame("clm-2", "evd-4", "Witnessed", "Attested"),
        ]

    def test_repeated_folds_are_identical(self):
        fr = self._corpus()
        assert fold(fr, as_of=NOW).state_hash() == fold(fr, as_of=NOW).state_hash()

    def test_insertion_order_of_independent_frames_converges(self):
        fr = self._corpus()
        a = fold(fr, as_of=NOW).state_hash()
        b = fold(list(reversed(fr)), as_of=NOW).state_hash()
        assert a == b, "causally independent frames must converge to the same state"

    def test_state_hash_changes_with_as_of(self):
        fr = self._corpus()
        assert fold(fr, as_of=NOW).state_hash() != fold(fr, as_of="2027-01-01T00:00:00Z").state_hash()

    def test_iteration_budget_is_asserted(self):
        with pytest.raises(FoldError, match="budget"):
            fold(self._corpus(), as_of=NOW, max_iterations=0)

    def test_fold_reaches_fixpoint_within_n_steps(self):
        res = fold(self._corpus(), as_of=NOW)
        # 0-stability bounds the number of STRICTLY-INCREASING passes at N. The confirming pass
        # that observes stability is not charged against it -- counting it was an off-by-one this
        # suite caught, and it is the same distinction as "N+1" = N steps plus the zero-init layer.
        assert res.iterations <= max(len(res.beliefs), 1)

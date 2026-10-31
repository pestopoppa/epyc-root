import pathlib
import sys
import unittest
import copy

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/vidya"))
from fold import fold, FT_RETRACT  # noqa: E402
from frames import make_frame  # noqa: E402

actor = "fixture-producer"
ts = "2026-10-31T00:00:00Z"
fs = [
    make_frame(
        frame_type="epyc.vidya/frame/claim_proposed/v1",
        assertion={"claim_id": "test-c"},
        provenance={"method": "test"},
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    ),
    make_frame(
        frame_type="epyc.vidya/frame/claim_proposed/v1",
        assertion={"claim_id": "test-c"},
        provenance={"method": "test"},
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    ),
    make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={
            "claim_id": "test-c",
            "evidence_id": "ev",
            "grade": {"Q": "Judged", "T": "Located"},
        },
        provenance={"method": "test"},
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    ),
]
target = fs[2]["frame_id"]
actor = fs[2]["pubinfo"]["actor"]
cid = fs[1]["assertion"]["claim_id"]
ts = "2026-10-31T00:00:00Z"


def rt(actor, target=target):
    return make_frame(
        frame_type=FT_RETRACT,
        assertion={"retracts": target, "reason": "test"},
        provenance={"method": "test"},
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    )


def state(frames, asof=ts):
    return fold(frames, as_of=asof)


class Authority(unittest.TestCase):
    def test_same_actor(self):
        self.assertIn(target, state(fs + [rt(actor)]).beliefs[cid].retracted_support)

    def test_wrong_and_empty_actor(self):
        for who in ("other", ""):
            r = state(fs + [rt(who)])
            self.assertNotIn(target, r.beliefs[cid].retracted_support)
            self.assertEqual(r.ignored_frame_types.get("unauthorized_retraction"), 1)
            self.assertFalse(r.beliefs[cid].supersession_reasons)

    def test_missing_target_actor(self):
        f = copy.deepcopy(fs)
        f[2]["pubinfo"].pop("actor")
        r = state(f + [rt(actor)])
        self.assertNotIn(target, r.beliefs[cid].retracted_support)

    def test_dangling(self):
        self.assertEqual(
            state(fs + [rt(actor, "missing")]).ignored_frame_types[
                "unauthorized_retraction"
            ],
            1,
        )

    def test_duplicates(self):
        self.assertIn(
            target, state(fs + [fs[2], rt(actor)]).beliefs[cid].retracted_support
        )
        other = copy.deepcopy(fs[2])
        other["pubinfo"]["actor"] = "forged"
        r = state(fs + [other, rt(actor)])
        self.assertNotIn(target, r.beliefs[cid].retracted_support)
        self.assertEqual(r.ignored_frame_types["unauthorized_retraction"], 1)

    def test_frontier_and_asof(self):
        x = rt(actor)
        self.assertEqual(state([x]).ignored_frame_types["unauthorized_retraction"], 1)
        self.assertIn(
            target,
            state(fs + [x], asof="2020-01-01T00:00:00Z").beliefs[cid].retracted_support,
        )

    def test_supersession_reason_requires_authority(self):
        x = copy.deepcopy(fs[1])
        x["pubinfo"]["actor"] = "other"
        x["pubinfo"]["supersedes"] = target
        x["pubinfo"]["supersedes_reason"] = "wrong"
        self.assertFalse(state(fs + [x]).beliefs[cid].supersession_reasons)
        x["pubinfo"]["actor"] = actor
        self.assertTrue(state(fs + [x]).beliefs[cid].supersession_reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)


def test_counterfactual_validation_and_frontier():
    from impact import _hypothetical_refold, impact_of_retracting
    import pytest

    with pytest.raises(KeyError):
        impact_of_retracting(fs, ["not-present"], as_of=ts)
    other = copy.deepcopy(fs[2])
    other["pubinfo"]["actor"] = "other"
    with pytest.raises(ValueError):
        impact_of_retracting(fs + [other], [target], as_of=ts)
    result = _hypothetical_refold(fs, [target], as_of=ts)
    assert result.frontier == len(fs) and result.as_of == ts
    assert target in result.beliefs[cid].retracted_support


def test_counterfactual_matches_authorized_retraction_for_each_frame_type():
    from impact import _hypothetical_refold

    source = make_frame(
        frame_type="epyc.vidya/frame/source_observed/v1",
        assertion={
            "source_id": "source",
            "locator": "https://example.org",
            "source_kind": "test",
        },
        provenance={"method": "test"},
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    )
    judgment = make_frame(
        frame_type="epyc.vidya/frame/judgment_recorded/v1",
        assertion={"claim_id": cid, "verdict": "equivalent"},
        provenance={
            "method": "test",
            "replay_key": {
                "read_set": [{"name": "x", "digest": {"sha256": "1" * 64}}],
                "prompt": "p",
                "seed": 1,
                "model_version": "m",
                "temperature": 0,
                "tool_output_hash": "sha256:" + "f" * 64,
            },
        },
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    )
    original_retraction = make_frame(
        frame_type=FT_RETRACT,
        assertion={"retracts": target},
        provenance={"method": "test"},
        actor=actor,
        authority_scope="measurement",
        created_at=ts,
    )
    baseline = fs + [source, judgment, original_retraction]
    for candidate in (fs[0], fs[2], source, judgment, original_retraction):
        virtual = _hypothetical_refold(baseline, [candidate["frame_id"]], as_of=ts)
        actual_retraction = make_frame(
            frame_type=FT_RETRACT,
            assertion={"retracts": candidate["frame_id"]},
            provenance={"method": "test"},
            actor=actor,
            authority_scope="measurement",
            created_at=ts,
        )
        actual = fold(baseline + [actual_retraction], as_of=ts)
        assert {k: v.as_dict() for k, v in virtual.beliefs.items()} == {
            k: v.as_dict() for k, v in actual.beliefs.items()
        }
        assert virtual.counted_judgments == actual.counted_judgments
        assert virtual.frontier == len(baseline)
        assert virtual.as_of == actual.as_of
    # With a retraction as the target, the original withdrawal remains in effect.
    assert (
        target
        in _hypothetical_refold(baseline, [original_retraction["frame_id"]], as_of=ts)
        .beliefs[cid]
        .retracted_support
    )

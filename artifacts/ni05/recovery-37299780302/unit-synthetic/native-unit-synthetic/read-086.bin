"""Tests for the operator hypothesis channel (scripts/autopilot/operator_hypotheses.py).

The channel supplies the planner with operator-stated PRIORS. Its whole value is
that each one is falsifiable and resolvable, so these tests pin the properties
that make that true: a falsifier is mandatory, a resolved hypothesis leaves the
open set, refutation is recorded with its evidence, a proposal repeating a
recorded negative is flagged, and nothing is markable resolved without evidence.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

operator_hypotheses = importlib.import_module("operator_hypotheses")


WELL_FORMED = {
    "id": "kv-compact-frees-headroom",
    "hypothesis": (
        "Compacting slots above 4000 cached tokens frees enough KV headroom to "
        "raise the seed batch size without a quality regression."
    ),
    "falsifier": (
        "If a post-compaction trial shows no increase in realistic max n_questions, "
        "the hypothesis is wrong."
    ),
    "stated_by": "operator",
    "stated": "2026-08-03",
    "confidence": "medium",
}


def _write_store(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "operator_hypotheses.yaml"
    path.write_text(yaml.safe_dump({"operator_hypotheses": entries}, sort_keys=False))
    return path


def _paths(tmp_path: Path, entries: list[dict]) -> tuple[Path, Path]:
    return _write_store(tmp_path, entries), tmp_path / "resolutions.jsonl"


# ----- the falsifier is mandatory -----


def test_hypothesis_without_falsifier_is_refused(tmp_path) -> None:
    entry = {k: v for k, v in WELL_FORMED.items() if k != "falsifier"}
    store, ledger = _paths(tmp_path, [entry])
    with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="falsifier"):
        operator_hypotheses.load_operator_hypotheses(store, ledger)


def test_blank_falsifier_is_refused(tmp_path) -> None:
    entry = dict(WELL_FORMED, falsifier="   ")
    store, ledger = _paths(tmp_path, [entry])
    with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="MANDATORY"):
        operator_hypotheses.load_operator_hypotheses(store, ledger)


def test_typoed_falsifier_key_raises_instead_of_dropping_it(tmp_path) -> None:
    """An unknown field must not silently become a hypothesis with no falsifier."""
    entry = {k: v for k, v in WELL_FORMED.items() if k != "falsifier"}
    entry["falsifer"] = "typo'd key"
    store, ledger = _paths(tmp_path, [entry])
    with pytest.raises(operator_hypotheses.OperatorHypothesisError):
        operator_hypotheses.load_operator_hypotheses(store, ledger)


# ----- explicit failure, never a silent empty list -----


def test_malformed_yaml_raises_and_does_not_degrade_to_empty(tmp_path) -> None:
    store = tmp_path / "operator_hypotheses.yaml"
    store.write_text("operator_hypotheses: [ this is: not, valid: yaml\n")
    with pytest.raises(operator_hypotheses.OperatorHypothesisError):
        operator_hypotheses.load_operator_hypotheses(store, tmp_path / "resolutions.jsonl")


def test_corrupt_resolution_ledger_line_raises(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    ledger.write_text("{not json}\n")
    with pytest.raises(operator_hypotheses.OperatorHypothesisError):
        operator_hypotheses.load_operator_hypotheses(store, ledger)


def test_absent_store_is_genuinely_empty(tmp_path) -> None:
    """A missing file means the operator stated nothing — that is not a defect."""
    out = operator_hypotheses.load_operator_hypotheses(
        tmp_path / "absent.yaml", tmp_path / "absent.jsonl"
    )
    assert out == []


def test_resolution_for_unknown_hypothesis_raises(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    ledger.write_text(
        json.dumps(
            {
                "hypothesis_id": "no-such-hypothesis",
                "status": "confirmed",
                "resolved_at": "2026-08-03T00:00:00+00:00",
                "evidence_trial_ids": [1],
            }
        )
        + "\n"
    )
    with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="unknown hypothesis"):
        operator_hypotheses.load_operator_hypotheses(store, ledger)


# ----- grading: a prior may not carry evidence -----


def test_statement_citing_evidence_trial_ids_is_refused(tmp_path) -> None:
    entry = dict(WELL_FORMED, evidence_trial_ids=[1234])
    store, ledger = _paths(tmp_path, [entry])
    with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="PRIOR, not evidence"):
        operator_hypotheses.load_operator_hypotheses(store, ledger)


def test_planner_render_states_the_prior_grade(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    items = operator_hypotheses.load_operator_hypotheses(store, ledger)
    text = operator_hypotheses.render_planner_block(items)
    assert "NOT an action gate" in text
    assert "evidence_trial_ids=[]" in text
    assert "seeded_by=operator" in text
    assert "falsifier:" in text


# ----- still_open -----


def test_still_open_excludes_resolved_hypotheses(tmp_path) -> None:
    second = dict(
        WELL_FORMED,
        id="numa-interleave-regression",
        hypothesis="Front-door throughput regressed because interleave drifted off all.",
        falsifier="If a pinned re-run at interleave=all shows no delta, the claim is wrong.",
    )
    store, ledger = _paths(tmp_path, [WELL_FORMED, second])

    assert {h.id for h in operator_hypotheses.still_open(path=store, resolutions_path=ledger)} == {
        WELL_FORMED["id"],
        second["id"],
    }

    operator_hypotheses.record_resolution(
        second["id"],
        "confirmed",
        evidence_trial_ids=[9001],
        note="pinned re-run reproduced the delta",
        path=store,
        resolutions_path=ledger,
    )

    open_ids = {h.id for h in operator_hypotheses.still_open(path=store, resolutions_path=ledger)}
    assert open_ids == {WELL_FORMED["id"]}

    rendered = operator_hypotheses.render_planner_block(path=store, resolutions_path=ledger)
    assert second["id"] not in rendered
    assert WELL_FORMED["id"] in rendered


# ----- refutation is as recordable as confirmation -----


def test_refutation_is_recorded_with_its_evidence(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])

    resolution = operator_hypotheses.record_resolution(
        WELL_FORMED["id"],
        "refuted",
        evidence_trial_ids=[4242, 4243],
        evidence_event_ids=["ledger:baseline_promotion:2026-08-03T10:00:00Z"],
        note="post-compaction trials showed no change in realistic max n_questions",
        recorded_by="autopilot",
        path=store,
        resolutions_path=ledger,
    )
    assert resolution.status == "refuted"

    row = json.loads(ledger.read_text().splitlines()[0])
    assert row["hypothesis_id"] == WELL_FORMED["id"]
    assert row["status"] == "refuted"
    assert row["evidence_trial_ids"] == [4242, 4243]
    assert row["evidence_event_ids"] == ["ledger:baseline_promotion:2026-08-03T10:00:00Z"]

    (loaded,) = operator_hypotheses.load_operator_hypotheses(store, ledger)
    assert not loaded.is_open
    assert loaded.resolution.status == "refuted"
    assert loaded.resolution.evidence_trial_ids == (4242, 4243)
    assert "#4242" in loaded.resolution.evidence_text()


def test_resolution_without_evidence_is_refused(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    for status in ("confirmed", "refuted"):
        with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="evidence id"):
            operator_hypotheses.record_resolution(
                WELL_FORMED["id"], status, note="I am sure", path=store, resolutions_path=ledger
            )
    assert not ledger.exists()
    assert operator_hypotheses.still_open(path=store, resolutions_path=ledger)


def test_inconclusive_requires_at_least_a_note(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    with pytest.raises(operator_hypotheses.OperatorHypothesisError):
        operator_hypotheses.record_resolution(
            WELL_FORMED["id"], "inconclusive", path=store, resolutions_path=ledger
        )
    operator_hypotheses.record_resolution(
        WELL_FORMED["id"],
        "inconclusive",
        note="two trials aborted on an unrelated host-health stop; nothing decided",
        path=store,
        resolutions_path=ledger,
    )
    assert not operator_hypotheses.still_open(path=store, resolutions_path=ledger)


def test_double_resolution_is_refused(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    operator_hypotheses.record_resolution(
        WELL_FORMED["id"],
        "refuted",
        evidence_trial_ids=[7],
        path=store,
        resolutions_path=ledger,
    )
    with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="already resolved"):
        operator_hypotheses.record_resolution(
            WELL_FORMED["id"],
            "confirmed",
            evidence_trial_ids=[8],
            path=store,
            resolutions_path=ledger,
        )


def test_resolving_an_unknown_id_is_refused(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    with pytest.raises(operator_hypotheses.OperatorHypothesisError, match="no operator hypothesis"):
        operator_hypotheses.record_resolution(
            "not-a-hypothesis", "confirmed", evidence_trial_ids=[1], path=store, resolutions_path=ledger
        )


# ----- negative history / failure blacklist -----


BLACKLIST = [
    {
        "pattern": {"type": "structural_experiment", "flags": {"lookup_cache": True}},
        "reason": "Lookup table segfaults on Qwen3.5 hybrids after 1-3 prompts (2026-03-19).",
    }
]


def test_operator_hypothesis_repeating_a_recorded_negative_is_flagged(tmp_path) -> None:
    entry = dict(
        WELL_FORMED,
        id="lookup-cache-is-worth-retrying",
        hypothesis="lookup_cache is worth another try on the current fleet.",
        falsifier="If it segfaults again within 3 prompts, the hypothesis is wrong.",
        proposed_action={"type": "structural_experiment", "flags": {"lookup_cache": True}},
    )
    store, ledger = _paths(tmp_path, [entry])
    items = operator_hypotheses.load_operator_hypotheses(store, ledger)

    conflicts = operator_hypotheses.blacklist_conflicts(items, BLACKLIST)
    assert entry["id"] in conflicts
    assert "segfault" in conflicts[entry["id"]].lower()

    rendered = operator_hypotheses.render_planner_block(items, blacklist=BLACKLIST)
    assert "NEGATIVE HISTORY" in rendered
    assert "Authorship is not new evidence" in rendered


def test_unblacklisted_operator_hypothesis_is_not_flagged(tmp_path) -> None:
    entry = dict(
        WELL_FORMED,
        proposed_action={"type": "numeric_trial", "surface": "compaction"},
    )
    store, ledger = _paths(tmp_path, [entry])
    items = operator_hypotheses.load_operator_hypotheses(store, ledger)
    assert operator_hypotheses.blacklist_conflicts(items, BLACKLIST) == {}
    assert "NEGATIVE HISTORY" not in operator_hypotheses.render_planner_block(
        items, blacklist=BLACKLIST
    )


# ----- the compliant path -----


def test_well_formed_hypothesis_loads_opens_and_resolves(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])

    (loaded,) = operator_hypotheses.load_operator_hypotheses(store, ledger)
    assert loaded.id == WELL_FORMED["id"]
    assert loaded.falsifier == WELL_FORMED["falsifier"]
    assert loaded.confidence == "medium"
    assert loaded.is_open
    # Provenance is fixed by the channel, not by the author.
    assert loaded.as_dict()["seeded_by"] == "operator"
    assert loaded.as_dict()["evidence_trial_ids"] == []

    assert [h.id for h in operator_hypotheses.still_open(path=store, resolutions_path=ledger)] == [
        WELL_FORMED["id"]
    ]
    assert WELL_FORMED["id"] in operator_hypotheses.render_planner_block(
        path=store, resolutions_path=ledger
    )

    operator_hypotheses.record_resolution(
        WELL_FORMED["id"],
        "confirmed",
        evidence_trial_ids=[5150],
        note="realistic max n_questions rose from 3 to 7 after compaction",
        path=store,
        resolutions_path=ledger,
    )

    assert operator_hypotheses.still_open(path=store, resolutions_path=ledger) == []
    (resolved,) = operator_hypotheses.load_operator_hypotheses(store, ledger)
    assert resolved.resolution.status == "confirmed"
    assert resolved.resolution.evidence_trial_ids == (5150,)
    assert (
        operator_hypotheses.render_planner_block(path=store, resolutions_path=ledger) == "  (none)"
    )


# ----- call-site helpers -----


def test_build_planner_block_alarms_instead_of_reporting_none(tmp_path) -> None:
    """An unreadable store must never render as '(none)'."""
    store = tmp_path / "operator_hypotheses.yaml"
    store.write_text("operator_hypotheses: [ broken: [\n")
    text = operator_hypotheses.build_planner_block(
        path=store, resolutions_path=tmp_path / "resolutions.jsonl"
    )
    assert "UNREADABLE" in text
    assert "does NOT mean the operator has no hypotheses" in text
    assert text != "  (none)"


def test_build_planner_block_renders_open_set(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    text = operator_hypotheses.build_planner_block(path=store, resolutions_path=ledger)
    assert WELL_FORMED["id"] in text
    assert "UNREADABLE" not in text


def test_planner_claim_resolves_with_the_trial_it_ran(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    rationale = {
        "falsifier": "...",
        "operator_hypothesis": {
            "id": WELL_FORMED["id"],
            "status": "refuted",
            "note": "no change in realistic max n_questions",
        },
    }
    resolution = operator_hypotheses.record_resolution_from_rationale(
        rationale, 6100, path=store, resolutions_path=ledger
    )
    assert resolution is not None
    assert resolution.status == "refuted"
    # Evidence is the trial that ran, supplied by the call site — never the planner.
    assert resolution.evidence_trial_ids == (6100,)
    assert operator_hypotheses.still_open(path=store, resolutions_path=ledger) == []


def test_planner_claim_for_unknown_id_is_rejected_and_leaves_it_open(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    rationale = {"operator_hypothesis": {"id": "invented-by-the-planner", "status": "confirmed"}}
    assert (
        operator_hypotheses.record_resolution_from_rationale(
            rationale, 6101, path=store, resolutions_path=ledger
        )
        is None
    )
    assert not ledger.exists()
    assert len(operator_hypotheses.still_open(path=store, resolutions_path=ledger)) == 1


def test_planner_claim_with_bad_status_is_rejected(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    for claim in (
        {"id": WELL_FORMED["id"], "status": "proven"},
        {"id": WELL_FORMED["id"]},
        {"status": "confirmed"},
        "resolved!",
    ):
        assert (
            operator_hypotheses.record_resolution_from_rationale(
                {"operator_hypothesis": claim}, 6102, path=store, resolutions_path=ledger
            )
            is None
        )
    assert len(operator_hypotheses.still_open(path=store, resolutions_path=ledger)) == 1


def test_no_rationale_claim_is_a_noop(tmp_path) -> None:
    store, ledger = _paths(tmp_path, [WELL_FORMED])
    assert (
        operator_hypotheses.record_resolution_from_rationale(
            {"falsifier": "x", "rubric_scores": {}}, 6103, path=store, resolutions_path=ledger
        )
        is None
    )
    assert operator_hypotheses.record_resolution_from_rationale(None, 6104) is None


def test_shipped_store_file_validates() -> None:
    """The committed operator-editable store must itself parse."""
    shipped = ROOT / "orchestration" / "operator_hypotheses.yaml"
    if not shipped.exists():
        pytest.skip("operator hypothesis store not present in this tree")
    operator_hypotheses.load_operator_hypotheses(
        shipped, ROOT / "orchestration" / "operator_hypothesis_resolutions.jsonl"
    )

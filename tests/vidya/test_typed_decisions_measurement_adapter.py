"""TD-2/TD-3 typed-decision measurement receipts -> ClaimTuple projection (VB-TDP-1).

Pinned:

* the ladder is not reimplemented: the grade is whatever ``claim_tuple.grade()``
  returns, and a protocol-less receipt is the observation rung;
* one claim per (receipt, metric): identity is unique per run and per metric,
  stable on replay, and the REAL receipt corpus does not collapse distinct claims;
* absence is not back-filled: a receipt with no ``protocol_id`` yields no invented
  protocol, and a receipt with no ``metric_direction`` yields no direction inferred
  from a metric name (ECE must NOT come out ``lower_better``);
* the extractor does not understate coverage: every declared metric of every study
  projects, and a receipt missing a declared field is REFUSED by name, never
  silently shorter;
* the adapter never emits a grade.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import typed_decisions_measurement as adapter  # noqa: E402

HERE = Path(__file__).resolve().parent
ADAPTER_SOURCE = HERE.parents[1] / "scripts" / "vidya" / "adapters" \
    / "typed_decisions_measurement.py"
#: The producer's own default receipt location (epyc-orchestrator measure.py).
REAL_CORPUS = Path(tempfile.gettempdir()) / "typed_decisions"
AS_OF = "2026-09-17T18:00:00Z"

#: Declared coverage, study -> metric keys. The adapter's map is the contract; this
#: mirror makes a silent shrink of it fail here instead of showing up as low coverage.
DECLARED = {
    "contamination": ("flip_rate",),
    "calibration": ("ece", "brier"),
    "fanout": ("agreement_rate", "batched_wall_ms", "singleton_wall_ms",
               "batched_speedup_serial", "batched_speedup_wall"),
}


def _prompts(count: int, seed: str) -> list[str]:
    return [hashlib.sha256(f"{seed}-{i}".encode()).hexdigest() for i in range(count)]


def contamination_receipt(**over) -> dict:
    receipt = {
        "study": "contamination",
        "timestamp": "2026-09-17T16:00:00.000001+00:00",
        "mode": "json",
        "role": "worker",
        "counts": {"questions": 4, "orderings": 4, "comparable_pairs": 12, "flips": 3,
                   "unresolved_pairs": 0, "canonical_unresolved": 0},
        "results": {
            "canonical": {"order_index": 0, "order": ["q-1"], "is_canonical": True,
                          "mode": "json", "elapsed_ms": 12.0,
                          "prompt_sha256": "a" * 64, "resolved": {}, "failure_count": 0,
                          "failures": []},
            "permutations": [],
            "per_question": [],
            "flip_rate": 0.25,
            "canonical_unresolved_ids": [],
        },
        "prompt_sha256": _prompts(4, "contamination"),
    }
    receipt.update(over)
    return receipt


def calibration_receipt(**over) -> dict:
    receipt = {
        "study": "calibration",
        "timestamp": "2026-09-17T16:10:00.000002+00:00",
        "mode": "json",
        "role": "worker",
        "counts": {"questions": 5, "resolved": 5, "labeled": 5, "scored": 5,
                   "unlabeled": 0, "unresolved": 0, "unknown_labels": 0, "failures": 0},
        "results": {
            "rows": [{"question_id": f"q-{i}", "kind": "noul", "value": True,
                      "confidence": 0.9, "correct": i < 3} for i in range(5)],
            "metrics": {"n": 5, "ece": 0.25, "brier": 0.2, "accuracy": 0.6,
                        "mean_confidence": 0.9, "n_bins": 10},
            "reliability_bins": [],
            "unknown_label_ids": [],
            "failures": [],
            "elapsed_ms": 21.0,
        },
        "prompt_sha256": _prompts(1, "calibration"),
    }
    receipt.update(over)
    return receipt


def fanout_receipt(**over) -> dict:
    receipt = {
        "study": "fanout",
        "timestamp": "2026-09-17T16:26:23.965948+00:00",
        "mode": "json",
        "role": "worker",
        "counts": {"states": 1, "questions_per_state": 4, "batched_calls": 1,
                   "singleton_calls": 4, "comparable_pairs": 4, "agreeing_pairs": 1,
                   "disagreements": 3, "unresolved_pairs": 0},
        "results": {
            "questions": ["fanout-000", "fanout-001", "fanout-002", "fanout-003"],
            "batched": {"calls": 1, "wall_ms": 0.29287301003932953,
                        "serial_sum_ms": 0.20118197426199913,
                        "per_call_ms": [0.20118197426199913], "tokens_generated": 11.0,
                        "calls_with_token_meta": 1},
            "singleton": {"calls": 4, "wall_ms": 0.3765430301427841,
                          "serial_sum_ms": 0.2556806430220604,
                          "per_call_ms": [0.06, 0.06, 0.07, 0.06],
                          "tokens_generated": 44.0, "calls_with_token_meta": 4},
            "agreement_rate": 0.25,
            "per_question_agreement": {},
            "disagreements": [{"state_index": 0, "question_id": "fanout-001",
                               "batched_value": "ship", "singleton_value": "hold"}],
            "batched_speedup_serial": 1.2708924045505572,
            "batched_speedup_wall": 1.2856870289693771,
        },
        "prompt_sha256": _prompts(5, "fanout"),
    }
    receipt.update(over)
    return receipt


def write(receipt: dict, tmp_path: Path, name: str = "receipt.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return path


def write_corpus(tmp_path: Path) -> Path:
    """One producer-shaped receipt per study; the ingest fixture for this adapter."""
    root = tmp_path / "typed_decisions"
    root.mkdir(parents=True, exist_ok=True)
    write(fanout_receipt(), root, "fanout-20260917T162623965948Z.json")
    return root


def tuples_for(path: Path) -> list[ct.ClaimTuple]:
    return [adapter.project(native) for native in adapter.native_rows(path)]


# --- projection is a projection, the shared ladder grades ---------------------------------

def test_projection_is_an_observation_graded_by_the_shared_ladder(tmp_path):
    path = write(fanout_receipt(), tmp_path)
    tuples = tuples_for(path)
    assert len(tuples) == len(DECLARED["fanout"])
    for tup in tuples:
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ct._measurement_ladder(tup)[:2]
        assert (q, t) == ("Judged", "Located")
        assert any("OBSERVATION" in reason for reason in reasons)
        frames = ct.to_frames(tup, as_of=AS_OF, adapter_id=adapter.ADAPTER_ID)
        assert len(frames) == 3
        support = next(f for f in frames if f["frame_type"].endswith("supports_claim/v1"))
        assert support["assertion"]["grade"] == {"Q": "Judged", "T": "Located"}


def test_attestation_is_the_file_digest_recomputed_at_read_time(tmp_path):
    path = write(fanout_receipt(), tmp_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    for tup in tuples_for(path):
        assert tup.attestation_sha256 == digest
        assert tup.attestation_verified is True
        assert tup.attestation_present is True
        assert tup.attestation_locator == f"typed-decisions-receipt:{path}"
    # a receipt carrying a forged digest field still projects the real file's digest
    forged = fanout_receipt(attestation_sha256="f" * 64, receipt_sha256="e" * 64)
    path2 = write(forged, tmp_path, "forged.json")
    assert all(t.attestation_sha256 == hashlib.sha256(path2.read_bytes()).hexdigest()
               for t in tuples_for(path2))


# --- identity: unique per run and per metric, stable on replay ----------------------------

def test_identity_is_unique_per_run_and_per_metric(tmp_path):
    paths = [
        write(contamination_receipt(), tmp_path, "contamination.json"),
        write(calibration_receipt(), tmp_path, "calibration.json"),
        write(fanout_receipt(), tmp_path, "fanout.json"),
    ]
    tuples = [tup for path in paths for tup in tuples_for(path)]
    expected = sum(len(keys) for keys in DECLARED.values())
    assert len(tuples) == expected
    ids = [tup.measurement_id for tup in tuples]
    assert len(set(ids)) == len(ids) == expected  # no metric of one run collapses

    # two distinct runs with identical counts/results but different timestamps and
    # prompts stay two claims; replaying one receipt is stable.
    first = write(fanout_receipt(), tmp_path, "run-a.json")
    second = write(fanout_receipt(timestamp="2026-09-17T16:26:24.000000+00:00",
                                  prompt_sha256=_prompts(5, "fanout-b")),
                   tmp_path, "run-b.json")
    ids_a = [t.measurement_id for t in tuples_for(first)]
    ids_a_again = [t.measurement_id for t in tuples_for(first)]
    ids_b = [t.measurement_id for t in tuples_for(second)]
    assert ids_a == ids_a_again
    assert set(ids_a).isdisjoint(ids_b)
    assert len(set(ids_a) | set(ids_b)) == 2 * len(DECLARED["fanout"])


@pytest.mark.skipif(not REAL_CORPUS.is_dir(),
                    reason="no real typed-decision receipt corpus on disk")
def test_real_corpus_replay_does_not_collapse_distinct_claims():
    """The receipts the producer actually wrote project to distinct claims, one per metric."""
    paths = sorted(REAL_CORPUS.glob("*.json"))
    assert paths, f"{REAL_CORPUS} matched no receipts"
    rows = 0
    ids: set[str] = set()
    for path in paths:
        tuples = tuples_for(path)
        assert tuples, f"{path} projected nothing"
        rows += len(tuples)
        ids.update(tup.measurement_id for tup in tuples)
    assert len(ids) == rows, "distinct receipts/metrics collapsed into one claim id"


# --- absence is not back-filled -----------------------------------------------------------

def test_missing_protocol_id_is_not_filled_with_a_guess(tmp_path):
    path = write(contamination_receipt(), tmp_path)
    for tup in tuples_for(path):
        assert tup.protocol_id == ""
        assert ct.grade(tup)[0] == "Judged"


def test_missing_metric_direction_is_not_inferred_from_the_metric_name(tmp_path):
    """ECE and a flip rate are conventionally lower-better — the adapter must NOT say so."""
    paths = [write(calibration_receipt(), tmp_path, "calibration.json"),
             write(contamination_receipt(), tmp_path, "contamination.json")]
    default = ct.ClaimTuple.__dataclass_fields__["metric_direction"].default
    for path in paths:
        for tup in tuples_for(path):
            assert tup.extra["metric_direction_present"] is False
            assert tup.extra["metric_direction_source"].startswith("absent")
            assert tup.metric_direction == default
            assert adapter.DIRECTION_ABSENT_CLAUSE in tup.claim


def test_an_explicit_receipt_direction_is_projected_verbatim(tmp_path):
    receipt = calibration_receipt(metric_directions={"ece": "lower_better"})
    path = write(receipt, tmp_path)
    by_metric = {tup.extra["metric_key"]: tup for tup in tuples_for(path)}
    assert by_metric["ece"].metric_direction == "lower_better"
    assert by_metric["ece"].extra["metric_direction_present"] is True
    # a metric the receipt does not label keeps no invented direction
    assert by_metric["brier"].metric_direction == "higher_better"
    assert by_metric["brier"].extra["metric_direction_present"] is False
    assert adapter.DIRECTION_ABSENT_CLAUSE not in by_metric["ece"].claim


def test_a_recorded_invalid_direction_is_refused_never_repaired(tmp_path):
    path = write(calibration_receipt(metric_direction="bigger"), tmp_path)
    with pytest.raises(ct.ProjectionError, match="metric_direction"):
        tuple(adapter.native_rows(path))


def test_mapping_input_claims_no_attestation(tmp_path):
    """Without a file there is no digest; the tuple records that, it does not invent one."""
    tuples = [adapter.project(n) for n in adapter.native_rows(fanout_receipt())]
    assert tuples
    for tup in tuples:
        assert tup.attestation_sha256 == ""
        assert tup.attestation_verified is None
        assert tup.attestation_present is None
        assert tup.attestation_locator == ""


# --- the extractor does not understate coverage -------------------------------------------

def test_every_declared_metric_of_every_study_projects(tmp_path):
    builders = {"contamination": contamination_receipt,
                "calibration": calibration_receipt, "fanout": fanout_receipt}
    for study, builder in builders.items():
        path = write(builder(), tmp_path, f"{study}.json")
        natives = adapter.native_rows(path)
        assert {n["metric_key"] for n in natives} == set(DECLARED[study])
        tuples = [adapter.project(n) for n in natives]
        assert len({t.measurement_id for t in tuples}) == len(tuples) == len(DECLARED[study])


def test_a_missing_declared_metric_is_refused_by_name_not_silently_short(tmp_path):
    receipt = contamination_receipt()
    del receipt["results"]["flip_rate"]
    path = write(receipt, tmp_path)
    with pytest.raises(ct.ProjectionError, match="results.flip_rate"):
        adapter.native_rows(path)


def test_an_unmeasured_speedup_is_omitted_not_filled(tmp_path):
    receipt = fanout_receipt()
    receipt["results"]["batched_speedup_wall"] = None
    path = write(receipt, tmp_path)
    keys = {n["metric_key"] for n in adapter.native_rows(path)}
    assert keys == set(DECLARED["fanout"]) - {"batched_speedup_wall"}


def test_a_foreign_document_or_unknown_study_is_refused():
    with pytest.raises(ct.ProjectionError, match="not a typed-decision"):
        adapter.native_rows({"schema": "something.else"})
    with pytest.raises(ct.ProjectionError, match="not a typed-decision"):
        adapter.native_rows(fanout_receipt(study="something"))
    with pytest.raises(ct.ProjectionError, match="not JSON"):
        adapter.native_rows(__file__)


# --- the adapter never emits a grade ------------------------------------------------------

def test_adapter_source_never_decides_a_grade():
    offenders = [line.strip() for line in ADAPTER_SOURCE.read_text().splitlines()
                 if re.search(r"return\s+.*[\"'](Witnessed|Verified|Judged)[\"']", line)]
    assert not offenders
    assert not hasattr(adapter, "grade")
    assert ct.source_classes()[adapter.PROJECTION_NAME] == "measurement"


def test_the_projection_is_registered_and_emits_through_the_shared_carrier(tmp_path):
    path = write(fanout_receipt(), tmp_path)
    tup = adapter.project(adapter.native_rows(path)[0])
    frames = ct.to_frames(tup, as_of=AS_OF, adapter_id=adapter.ADAPTER_ID,
                          authority=adapter.AUTHORITY)
    assert [f["frame_type"] for f in frames] == [
        "epyc.vidya/frame/source_observed/v1",
        "epyc.vidya/frame/claim_proposed/v1",
        "epyc.vidya/frame/evidence_supports_claim/v1",
    ]
    assert frames[2]["assertion"]["protocol_id"] == ""
    assert frames[2]["assertion"]["reps"] == 4

"""TD-2/TD-3 typed-decision measurement receipts -> ClaimTuple projection (VB-TDP-1).

Pinned:

* the ladder is not reimplemented: the grade is whatever ``claim_tuple.grade()``
  returns, and a protocol-less receipt is the observation rung;
* one claim per (receipt, metric): identity is unique per run and per metric,
  stable on replay, and the REAL receipt corpus does not collapse distinct claims;
* absence is not back-filled: a receipt with no ``protocol_id`` yields no invented
  protocol, and a receipt with no ``metric_direction`` yields no direction inferred
  from a metric name (ECE must NOT come out ``lower_better``; the tool-args pilot's
  and the parallel fan-out's real ``metric_directions`` maps project verbatim, and
  the same receipt with the map deleted keeps the absent clause);
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
#: The live tool-args pilot receipt committed under this worktree's artifacts.
REAL_TOOL_ARGS_RECEIPT = (HERE.parents[1] / "artifacts" / "typed_decisions"
                          / "run_20260917" / "tool-args-pilot-worker.json")
#: The live TD-3b parallel fan-out (4 workers) receipt from the same run dir.
REAL_PARALLEL_FANOUT_RECEIPT = (HERE.parents[1] / "artifacts" / "typed_decisions"
                                / "run_20260917" / "parallel-fanout-w4.json")
AS_OF = "2026-09-17T18:00:00Z"

#: Declared coverage, study -> metric keys. The adapter's map is the contract; this
#: mirror makes a silent shrink of it fail here instead of showing up as low coverage.
DECLARED = {
    "contamination": ("flip_rate",),
    "calibration": ("ece", "brier"),
    "fanout": ("agreement_rate", "batched_wall_ms", "singleton_wall_ms",
               "batched_speedup_serial", "batched_speedup_wall"),
    "tool_args_pilot": ("agreement_rate", "closed_set_exact_match_rate",
                        "closed_set_per_arg_exact_match_rate", "closed_set_wall_ms",
                        "free_form_exact_match_rate",
                        "free_form_per_arg_exact_match_rate", "free_form_wall_ms"),
    "parallel_fanout": ("batched_wall_ms", "batched_serial_sum_ms",
                        "sequential_singleton_wall_ms",
                        "sequential_singleton_serial_sum_ms",
                        "concurrent_singleton_wall_ms",
                        "concurrent_singleton_serial_sum_ms",
                        "speedup_concurrent_vs_batched",
                        "speedup_concurrent_vs_sequential",
                        "concurrent_vs_batched_agreement_rate",
                        "sequential_vs_batched_agreement_rate",
                        "concurrent_vs_sequential_agreement_rate"),
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


def tool_args_pilot_receipt(**over) -> dict:
    receipt = {
        "study": "tool_args_pilot",
        "timestamp": "2026-09-17T20:30:05.192219+00:00",
        "mode": "closed_set_vs_free_form",
        "role": "frontdoor",
        "metric_directions": {"exact_match": "higher_better",
                              "per_arg_exact_match": "higher_better",
                              "agreement": "higher_better",
                              "wall_ms": "lower_better"},
        "counts": {"tools": 2, "cases": 4, "closed_set_resolved": 4,
                   "closed_set_failures": 0, "free_form_resolved": 2,
                   "free_form_failures": 2, "agreement_agreeing": 2,
                   "agreement_compared": 2},
        "results": {
            "arms": {
                "closed_set": {"decode": "typed_json", "cases": 4, "resolved": 4,
                               "exact_match": 4, "exact_match_rate": 1.0,
                               "per_arg_exact_match": 10, "per_arg_total": 10,
                               "per_arg_exact_match_rate": 1.0, "failures": 0,
                               "wall_ms": 120.0, "tokens_generated": 200.0,
                               "calls_with_token_meta": 4,
                               "per_case_ms": [], "per_case_tokens": []},
                "free_form": {"decode": "free_form_text", "cases": 4, "resolved": 2,
                              "exact_match": 2, "exact_match_rate": 0.5,
                              "per_arg_exact_match": 6, "per_arg_total": 10,
                              "per_arg_exact_match_rate": 0.6, "failures": 2,
                              "wall_ms": 40.0, "tokens_generated": 30.0,
                              "calls_with_token_meta": 4,
                              "per_case_ms": [], "per_case_tokens": []},
            },
            "agreement": {"agreeing": 2, "compared": 2, "rate": 1.0},
            "cases": [],
        },
        "prompt_sha256": _prompts(8, "tool-args"),
    }
    receipt.update(over)
    return receipt


def parallel_fanout_receipt(**over) -> dict:
    receipt = {
        "study": "parallel_fanout",
        "timestamp": "2026-09-17T23:24:56.139097+00:00",
        "mode": "json",
        "role": "frontdoor",
        "metric_directions": {
            "agreement_rate_vs_batched": "higher_better",
            "speedup_concurrent_vs_batched": "higher_better",
            "speedup_concurrent_vs_sequential": "higher_better",
            "wall_ms": "lower_better",
            "serial_sum_ms": "lower_better",
        },
        "counts": {"states": 1, "questions_per_state": 4, "workers": 2,
                   "batched_calls": 1, "sequential_singleton_calls": 4,
                   "concurrent_singleton_calls": 4},
        "results": {
            "questions": ["c01", "c02", "n01", "s01"],
            "arms": {
                "batched": {"calls": 1, "wall_ms": 1000.0, "serial_sum_ms": 900.0,
                            "per_call_ms": [900.0], "tokens_generated": 100.0,
                            "calls_with_token_meta": 1},
                "sequential_singleton": {"calls": 4, "wall_ms": 2000.0,
                                         "serial_sum_ms": 1950.0,
                                         "per_call_ms": [500.0, 480.0, 480.0, 490.0],
                                         "tokens_generated": 100.0,
                                         "calls_with_token_meta": 4},
                "concurrent_singleton": {"calls": 4, "wall_ms": 800.0,
                                         "serial_sum_ms": 1960.0,
                                         "per_call_ms": [500.0, 480.0, 490.0, 490.0],
                                         "tokens_generated": 100.0,
                                         "calls_with_token_meta": 4},
            },
            "agreement": {
                "concurrent_vs_batched": {"agreement_rate": 0.75, "comparable_pairs": 4,
                                          "agreeing_pairs": 3, "unresolved_pairs": 0,
                                          "disagreements": [], "per_question": {}},
                "sequential_vs_batched": {"agreement_rate": 0.5, "comparable_pairs": 4,
                                          "agreeing_pairs": 2, "unresolved_pairs": 0,
                                          "disagreements": [], "per_question": {}},
                "concurrent_vs_sequential": {"agreement_rate": 1.0, "comparable_pairs": 4,
                                             "agreeing_pairs": 4, "unresolved_pairs": 0,
                                             "disagreements": [], "per_question": {}},
            },
            "speedup_concurrent_vs_batched": 1.25,
            "speedup_concurrent_vs_sequential": 2.5,
        },
        "prompt_sha256": {
            "batched": _prompts(1, "parallel-batched"),
            "sequential_singleton": _prompts(4, "parallel-seq"),
            "concurrent_singleton": _prompts(4, "parallel-conc"),
        },
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
    write(parallel_fanout_receipt(), root, "parallel-fanout-20260917T232456139097Z.json")
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
        write(tool_args_pilot_receipt(), tmp_path, "tool-args-pilot.json"),
        write(parallel_fanout_receipt(), tmp_path, "parallel-fanout.json"),
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


def test_parallel_fanout_identity_is_unique_across_runs_differing_only_by_timestamp(
        tmp_path):
    """Two receipts of the same shape, same counts, only the timestamp moved: two runs."""
    first = write(parallel_fanout_receipt(), tmp_path, "run-a.json")
    second = write(parallel_fanout_receipt(timestamp="2026-09-17T23:24:57.000000+00:00"),
                   tmp_path, "run-b.json")
    ids_a = [t.measurement_id for t in tuples_for(first)]
    ids_b = [t.measurement_id for t in tuples_for(second)]
    assert len(ids_a) == len(DECLARED["parallel_fanout"])
    assert set(ids_a).isdisjoint(ids_b)
    assert len(set(ids_a) | set(ids_b)) == 2 * len(DECLARED["parallel_fanout"])


def test_parallel_fanout_identity_keeps_the_per_arm_prompt_map(tmp_path):
    """Same timestamp and counts, different per-arm prompts: still two runs."""
    first = write(parallel_fanout_receipt(), tmp_path, "run-a.json")
    changed = parallel_fanout_receipt()
    changed["prompt_sha256"]["concurrent_singleton"] = _prompts(4, "parallel-conc-b")
    second = write(changed, tmp_path, "run-b.json")
    assert set(t.measurement_id for t in tuples_for(first)).isdisjoint(
        t.measurement_id for t in tuples_for(second))


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


@pytest.mark.skipif(not REAL_TOOL_ARGS_RECEIPT.is_file(),
                    reason="no live tool-args pilot receipt on disk")
def test_real_tool_args_pilot_receipt_projects_with_recorded_directions():
    """The live producer receipt: every declared metric, every direction from the
    receipt's own metric_directions map, unique identity, no invented direction."""
    natives = adapter.native_rows(REAL_TOOL_ARGS_RECEIPT)
    assert {n["metric_key"] for n in natives} == set(DECLARED["tool_args_pilot"])
    tuples = [adapter.project(n) for n in natives]
    assert len(tuples) == len(DECLARED["tool_args_pilot"]) > 0
    assert len({t.measurement_id for t in tuples}) == len(tuples)

    by_metric = {t.extra["metric_key"]: t for t in tuples}
    for tup in tuples:
        assert tup.extra["metric_direction_present"] is True
        assert tup.extra["metric_direction_source"] == "receipt"
        assert tup.metric_direction in ("higher_better", "lower_better")
        assert adapter.DIRECTION_ABSENT_CLAUSE not in tup.claim
    for key in ("closed_set_exact_match_rate", "closed_set_per_arg_exact_match_rate",
                "free_form_exact_match_rate", "free_form_per_arg_exact_match_rate",
                "agreement_rate"):
        assert by_metric[key].metric_direction == "higher_better"
    for key in ("closed_set_wall_ms", "free_form_wall_ms"):
        assert by_metric[key].metric_direction == "lower_better"

    # values and scored denominators come from the receipt, not from a name
    assert by_metric["closed_set_exact_match_rate"].value == 1.0
    assert by_metric["closed_set_exact_match_rate"].reps == 18
    assert by_metric["closed_set_per_arg_exact_match_rate"].reps == 66
    assert by_metric["free_form_exact_match_rate"].value == pytest.approx(1 / 3)
    assert by_metric["free_form_per_arg_exact_match_rate"].value == pytest.approx(24 / 66)
    assert by_metric["closed_set_wall_ms"].value == pytest.approx(116590.17779305577)
    assert by_metric["free_form_wall_ms"].value == pytest.approx(11440.160401165485)
    assert by_metric["agreement_rate"].value == 1.0
    assert by_metric["agreement_rate"].reps == 6


@pytest.mark.skipif(not REAL_PARALLEL_FANOUT_RECEIPT.is_file(),
                    reason="no live parallel-fanout receipt on disk")
def test_real_parallel_fanout_receipt_projects_with_recorded_directions():
    """The live TD-3b receipt: every declared metric, every direction from the
    receipt's own metric_directions map, unique identity, no invented direction."""
    natives = adapter.native_rows(REAL_PARALLEL_FANOUT_RECEIPT)
    assert {n["metric_key"] for n in natives} == set(DECLARED["parallel_fanout"])
    tuples = [adapter.project(n) for n in natives]
    assert len(tuples) == len(DECLARED["parallel_fanout"]) > 0
    assert len({t.measurement_id for t in tuples}) == len(tuples)

    by_metric = {t.extra["metric_key"]: t for t in tuples}
    for tup in tuples:
        assert tup.extra["metric_direction_present"] is True
        assert tup.extra["metric_direction_source"] == "receipt"
        assert tup.metric_direction in ("higher_better", "lower_better")
        assert adapter.DIRECTION_ABSENT_CLAUSE not in tup.claim
    for key in ("batched_wall_ms", "batched_serial_sum_ms",
                "sequential_singleton_wall_ms", "sequential_singleton_serial_sum_ms",
                "concurrent_singleton_wall_ms", "concurrent_singleton_serial_sum_ms"):
        assert by_metric[key].metric_direction == "lower_better"
    for key in ("speedup_concurrent_vs_batched", "speedup_concurrent_vs_sequential",
                "concurrent_vs_batched_agreement_rate",
                "sequential_vs_batched_agreement_rate",
                "concurrent_vs_sequential_agreement_rate"):
        assert by_metric[key].metric_direction == "higher_better"

    # values and scored denominators come from the receipt, not from a name
    assert by_metric["batched_wall_ms"].value == pytest.approx(19277.868238743395)
    assert by_metric["batched_wall_ms"].reps == 1
    assert by_metric["batched_serial_sum_ms"].value == pytest.approx(19277.38899597898)
    assert by_metric["sequential_singleton_wall_ms"].value == pytest.approx(
        37404.752407222986)
    assert by_metric["sequential_singleton_wall_ms"].reps == 24
    assert by_metric["concurrent_singleton_wall_ms"].value == pytest.approx(
        29907.042782288045)
    assert by_metric["concurrent_singleton_serial_sum_ms"].value == pytest.approx(
        112194.45946859196)
    assert by_metric["concurrent_singleton_serial_sum_ms"].reps == 24
    assert by_metric["speedup_concurrent_vs_batched"].value == pytest.approx(
        0.6445929267924944)
    assert by_metric["speedup_concurrent_vs_sequential"].value == pytest.approx(
        1.2507004680976126)
    assert by_metric["concurrent_vs_batched_agreement_rate"].value == pytest.approx(0.875)
    assert by_metric["concurrent_vs_batched_agreement_rate"].reps == 24
    assert by_metric["sequential_vs_batched_agreement_rate"].value == pytest.approx(0.875)
    assert by_metric["concurrent_vs_sequential_agreement_rate"].value == 1.0
    assert by_metric["concurrent_vs_sequential_agreement_rate"].reps == 24


def test_parallel_fanout_directions_are_read_from_the_receipt_not_from_names(tmp_path):
    """Flip the receipt's own agreement-family and time labels: the claims follow it."""
    flipped = parallel_fanout_receipt(metric_directions={
        "agreement_rate_vs_batched": "lower_better",
        "speedup_concurrent_vs_batched": "lower_better",
        "speedup_concurrent_vs_sequential": "lower_better",
        "wall_ms": "higher_better", "serial_sum_ms": "higher_better"})
    path = write(flipped, tmp_path)
    by_metric = {t.extra["metric_key"]: t for t in tuples_for(path)}
    for key in ("batched_wall_ms", "sequential_singleton_wall_ms",
                "concurrent_singleton_serial_sum_ms"):
        assert by_metric[key].metric_direction == "higher_better"
    for key in ("speedup_concurrent_vs_sequential",
                "concurrent_vs_batched_agreement_rate",
                "concurrent_vs_sequential_agreement_rate"):
        assert by_metric[key].metric_direction == "lower_better"


def test_a_recorded_invalid_parallel_fanout_direction_is_refused_never_repaired(tmp_path):
    path = write(parallel_fanout_receipt(metric_directions={"wall_ms": "faster"}),
                 tmp_path)
    with pytest.raises(ct.ProjectionError, match="metric_directions.wall_ms"):
        tuple(adapter.native_rows(path))


def test_tool_args_pilot_directions_are_read_from_the_receipt_not_from_names(tmp_path):
    """Flip every recorded direction: the claims must follow the receipt, not habit."""
    flipped = tool_args_pilot_receipt(metric_directions={
        "exact_match": "lower_better", "per_arg_exact_match": "lower_better",
        "agreement": "lower_better", "wall_ms": "higher_better"})
    path = write(flipped, tmp_path)
    by_metric = {t.extra["metric_key"]: t for t in tuples_for(path)}
    assert by_metric["closed_set_exact_match_rate"].metric_direction == "lower_better"
    assert by_metric["free_form_per_arg_exact_match_rate"].metric_direction \
        == "lower_better"
    assert by_metric["agreement_rate"].metric_direction == "lower_better"
    assert by_metric["closed_set_wall_ms"].metric_direction == "higher_better"
    assert by_metric["free_form_wall_ms"].metric_direction == "higher_better"


def test_a_recorded_invalid_tool_args_direction_is_refused_never_repaired(tmp_path):
    path = write(tool_args_pilot_receipt(metric_directions={"wall_ms": "smaller"}),
                 tmp_path)
    with pytest.raises(ct.ProjectionError, match="metric_directions.wall_ms"):
        tuple(adapter.native_rows(path))


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


def test_tool_args_pilot_without_metric_directions_keeps_the_absent_clause(tmp_path):
    receipt = tool_args_pilot_receipt()
    del receipt["metric_directions"]
    path = write(receipt, tmp_path)
    tuples = tuples_for(path)
    assert len(tuples) == len(DECLARED["tool_args_pilot"])
    default = ct.ClaimTuple.__dataclass_fields__["metric_direction"].default
    for tup in tuples:
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
                "calibration": calibration_receipt, "fanout": fanout_receipt,
                "tool_args_pilot": tool_args_pilot_receipt,
                "parallel_fanout": parallel_fanout_receipt}
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


def test_a_parallel_fanout_missing_arm_is_refused_by_name_not_silently_short(tmp_path):
    receipt = parallel_fanout_receipt()
    del receipt["results"]["arms"]["concurrent_singleton"]
    path = write(receipt, tmp_path)
    with pytest.raises(ct.ProjectionError,
                       match=r"results\.arms\.concurrent_singleton"):
        adapter.native_rows(path)


def test_a_parallel_fanout_missing_agreement_rate_is_refused_by_name(tmp_path):
    receipt = parallel_fanout_receipt()
    del receipt["results"]["agreement"]["sequential_vs_batched"]["agreement_rate"]
    path = write(receipt, tmp_path)
    with pytest.raises(ct.ProjectionError,
                       match=r"results\.agreement\.sequential_vs_batched\.agreement_rate"):
        adapter.native_rows(path)


def test_a_parallel_fanout_unmeasured_speedup_is_omitted_not_filled(tmp_path):
    receipt = parallel_fanout_receipt()
    receipt["results"]["speedup_concurrent_vs_sequential"] = None
    path = write(receipt, tmp_path)
    keys = {n["metric_key"] for n in adapter.native_rows(path)}
    assert keys == set(DECLARED["parallel_fanout"]) - {
        "speedup_concurrent_vs_sequential"}


def test_a_bare_float_parallel_fanout_agreement_rate_is_projected_as_carried(tmp_path):
    """The other shape the producer may write: a bare rate, no comparable-pair count."""
    receipt = parallel_fanout_receipt()
    receipt["results"]["agreement"]["sequential_vs_batched"] = 0.5
    path = write(receipt, tmp_path)
    by_metric = {t.extra["metric_key"]: t for t in tuples_for(path)}
    tup = by_metric["sequential_vs_batched_agreement_rate"]
    assert tup.value == 0.5
    assert tup.reps == 4  # states x questions_per_state, both the receipt's own counts
    assert tup.reps_basis.startswith("covered")
    assert tup.metric_direction == "higher_better"


def test_a_foreign_document_or_unknown_study_is_refused():
    with pytest.raises(ct.ProjectionError, match="not a typed-decision"):
        adapter.native_rows({"schema": "something.else"})
    with pytest.raises(ct.ProjectionError, match="not a typed-decision"):
        adapter.native_rows(fanout_receipt(study="something"))
    # a near-miss on a study name is still refused, by name and with the roster
    with pytest.raises(ct.ProjectionError, match="study='tool_args'"):
        adapter.native_rows(tool_args_pilot_receipt(study="tool_args"))
    with pytest.raises(ct.ProjectionError, match="study='parallel-fanout'"):
        adapter.native_rows(parallel_fanout_receipt(study="parallel-fanout"))
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

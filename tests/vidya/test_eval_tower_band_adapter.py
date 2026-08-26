"""SC37 — the eval-tower resolution band write hook and its strict reader.

What is pinned here, in the order this program has been burned:

* the doctrine boundary — the raw ``core_v2_calibration`` JSONL is the producer's
  native record; only a producer-authored, self-hashed ``.band.json`` artifact is
  admissible on read (never reconstruct a band from the JSONL on read);
* the scope limit lives IN the tuple — the claim states instrument-resolution-only
  verbatim, and both writer and reader refuse any artifact whose claim does not;
* the EV-14c coupling — a band whose pinned baseline reference moved mid-window is
  INVALID: the writer refuses to emit it, the reader refuses to project one;
* the ladder is not reimplemented — the grade asserted below is whatever
  ``claim_tuple.grade()`` actually returns, driven through the one shared
  implementation;
* identity is unique per (band run, suite, artifact) and stable across re-reads;
* a tampered artifact is inadmissible as a whole (a mutated artifact is corruption,
  not a partial band — there is no separate attested file to decay against).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import eval_tower_band as band  # noqa: E402

CORE_ID = "tier_stratified_equal_thirds_v1_seed_4242_n300_rot45000"
CALIBRATION_ID = "core_v2_calibration_20260826T120000Z"
CONFIG = {
    "core_id": CORE_ID,
    "trial_id_base": 900000,
    "seed": 4242,
    "n": 300,
    "tier_mix_policy": "equal_thirds_v1",
    "rotation_index": 45000,
}
ERA = {"eval_quality_era": "E16-eval-history-scoped-quiescence-v10-quality"}
REFERENCE = {
    "tier": 1,
    "pin_id": "band-math-e16-20260826",
    "pinned_at": "2026-08-26T12:00:00Z",
    "quality": 1.524,
    "per_suite_quality": {"math": 1.524},
    "per_suite_counts": {"math": 100},
    "tier_revision": 3,
    "eval_quality_era": "E16-eval-history-scoped-quiescence-v10-quality",
}

SUITE_SCORES = {  # per repeat_index -> (per-suite quality, per-suite count)
    0: (1.50, 100),
    1: (1.52, 100),
    2: (1.55, 100),
    3: (1.51, 100),
}


def calibration_row(repeat_index: int, suite_scores=SUITE_SCORES) -> dict:
    quality, k = suite_scores[repeat_index]
    return {
        "event_type": "core_v2_calibration",
        "schema_version": 1,
        "calibration_id": CALIBRATION_ID,
        "repeat_index": repeat_index,
        "repeats": len(SUITE_SCORES),
        "requested_n": 300,
        "seed": 4242,
        "trial_id": 900000 + repeat_index,
        "started_at": "2026-08-26T12:00:00Z",
        "finished_at": "2026-08-26T12:16:00Z",
        "tier": 1,
        "quality": 1.5 + 0.02 * repeat_index,
        "speed": 42.0,
        "speed_metric_mode": "aggregate_batch_tps",
        "median_request_speed": 7.0,
        "aggregate_speed": 42.0,
        "eval_concurrency": 3,
        "eval_wall_s": 900.0,
        "cost": 0.5,
        "reliability": 1.0,
        "n_questions": 300,
        "quality_measured": True,
        "quality_unmeasured_reason": "",
        "infra_failed_count": 0,
        "scoring_failed_count": 0,
        "infra_failed_reasons": {},
        "core_id": CORE_ID,
        "per_suite_quality": {"math": quality, "gpqa_diamond": 1.2},
        "per_suite_counts": {"math": k, "gpqa_diamond": 50},
        "routing_distribution": {"frontdoor": 1.0},
        "eval_details": {"question_results": [], "details": {}},
    }


def write_calibration_jsonl(tmp_path: Path, rows=None) -> Path:
    path = tmp_path / "calibration.jsonl"
    with open(path, "w") as handle:
        for row in rows or [calibration_row(i) for i in SUITE_SCORES]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def build(tmp_path: Path, **overrides) -> Path:
    out = tmp_path / "band.json"
    if "calibration_jsonl" not in overrides:
        overrides["calibration_jsonl"] = write_calibration_jsonl(tmp_path)
    kwargs = dict(
        out_path=out,
        calibration_id=CALIBRATION_ID,
        suite_id="math",
        unchanged_config=CONFIG,
        instrument_era=ERA,
        baseline_reference=REFERENCE,
        reference_moved=False,
        emitted_at="2026-08-26T13:00:00Z",
    )
    kwargs.update(overrides)
    return band.build_band_artifact(**kwargs)


# --- the round trip, graded by THE ladder -------------------------------------

def test_well_formed_band_projects_and_reaches_witnessed_attested(tmp_path):
    artifact = build(tmp_path)
    natives = band.native_rows(artifact)
    assert len(natives) == 1, "one artifact = one suite = one claim"
    tup = band.project(natives[0])
    q, t, reasons = ct.grade(tup)
    # Asserted from the ladder's own answer: full tuple, artifact hashed AND on disk.
    assert (q, t) == ("Witnessed", "Attested"), reasons
    assert reasons == []


def test_tuple_carries_the_sc37_axes(tmp_path):
    tup = band.project(band.native_rows(build(tmp_path))[0])
    assert tup.extra["suite_id"] == "math"
    assert tup.extra["k"] == 100
    assert tup.extra["unchanged_config"]["core_id"] == CORE_ID
    assert [r["quality"] for r in tup.extra["per_repeat_scores"]] == [1.5, 1.52, 1.55, 1.51]
    assert tup.extra["instrument_era"]["eval_quality_era"] == ERA["eval_quality_era"]
    assert tup.extra["baseline_reference"]["tier_revision"] == 3
    assert tup.extra["baseline_reference"]["quality"] == 1.524
    assert tup.extra["reference_moved"] is False
    assert tup.metric_direction == "lower_better", "a NARROWER band is higher resolution"
    assert tup.metric == band.METRIC
    assert tup.unit == "quality_units_0_3"
    assert tup.reps == 4 and tup.reps_basis.startswith("scored:repeats")
    assert tup.value == pytest.approx(0.05), "the band value is the retained spread"


def test_the_scope_limit_is_stated_in_the_tuple(tmp_path):
    tup = band.project(band.native_rows(build(tmp_path))[0])
    assert band.SCOPE_LIMIT in tup.claim, "the claim must state instrument-resolution-only"
    assert tup.extra["scope_limit"] == band.SCOPE_LIMIT
    assert "says nothing about the quality of any config" in tup.claim


def test_identity_is_unique_per_suite_and_stable(tmp_path):
    math_artifact = build(tmp_path)
    gpqa = build(tmp_path, out_path=tmp_path / "gpqa.json", suite_id="gpqa_diamond")
    math_id = band.project(band.native_rows(math_artifact)[0]).measurement_id
    gpqa_id = band.project(band.native_rows(gpqa)[0]).measurement_id
    assert math_id != gpqa_id, "distinct suites must not merge into one claim"
    again = band.project(band.native_rows(math_artifact)[0]).measurement_id
    assert math_id == again, "the same artifact must re-derive the same identity"


# --- doctrine: the JSONL alone is never a band ---------------------------------

def test_native_rows_ignores_the_raw_calibration_jsonl(tmp_path):
    path = write_calibration_jsonl(tmp_path)
    assert band.native_rows(path) == (), (
        "a tuple invented on read claims warrant the run never captured — the JSONL "
        "is not a band artifact")


def test_missing_artifact_emits_zero_rows(tmp_path):
    assert band.native_rows(tmp_path / "nope.json") == ()


# --- EV-14c coupling: a moved reference is invalid ------------------------------

def test_writer_refuses_a_moved_reference(tmp_path):
    with pytest.raises(band.CaptureError, match="MOVED"):
        build(tmp_path, reference_moved=True)
    assert not (tmp_path / "band.json").exists(), "the refusal must not half-write"


def test_reader_refuses_an_artifact_with_a_moved_reference(tmp_path):
    artifact = build(tmp_path)
    data = json.loads(artifact.read_text())
    data["reference_moved"] = True
    data["artifact_sha256"] = band.content_hash(
        {k: v for k, v in data.items() if k != "artifact_sha256"})
    artifact.write_text(json.dumps(data, sort_keys=True) + "\n")
    assert band.native_rows(artifact) == (), \
        "a moved-reference band is invalid, never 'no change' (EV-14c)"


# --- strictness: a band the run did not measure is not emitted ------------------

def test_writer_refuses_a_degraded_repeat(tmp_path):
    rows = [calibration_row(i) for i in SUITE_SCORES]
    rows[1]["infra_failed_count"] = 12
    rows[1]["quality_measured"] = False
    with pytest.raises(band.CaptureError, match="clean instrument"):
        build(tmp_path, calibration_jsonl=write_calibration_jsonl(tmp_path, rows))


def test_writer_refuses_when_k_differs_across_repeats(tmp_path):
    rows = [calibration_row(i) for i in SUITE_SCORES]
    rows[2]["per_suite_counts"]["math"] = 99  # same config must draw the same K
    with pytest.raises(band.CaptureError, match="unchanged"):
        build(tmp_path, calibration_jsonl=write_calibration_jsonl(tmp_path, rows))


def test_writer_refuses_when_repeats_are_not_one_config(tmp_path):
    rows = [calibration_row(i) for i in SUITE_SCORES]
    rows[0]["core_id"] = "tier_stratified_equal_thirds_v1_seed_4242_n300_rot45001"
    with pytest.raises(band.CaptureError, match="unchanged config"):
        build(tmp_path, calibration_jsonl=write_calibration_jsonl(tmp_path, rows))


def test_writer_refuses_a_suite_that_did_not_score_every_repeat(tmp_path):
    rows = [calibration_row(i) for i in SUITE_SCORES]
    rows[3]["per_suite_quality"]["math"] = None
    with pytest.raises(band.CaptureError, match="retained score"):
        build(tmp_path, calibration_jsonl=write_calibration_jsonl(tmp_path, rows))


def test_writer_refuses_when_calibration_file_missing(tmp_path):
    with pytest.raises(band.CaptureError, match="AFTER the repeats"):
        build(tmp_path, calibration_jsonl=tmp_path / "absent.jsonl")


# --- strictness: a tampered artifact is void ------------------------------------

def _rewrite(artifact: Path, mutate) -> None:
    data = json.loads(artifact.read_text())
    mutate(data)
    artifact.write_text(json.dumps(data, sort_keys=True) + "\n")


def test_any_tamper_voids_the_whole_artifact(tmp_path):
    artifact = build(tmp_path)

    _rewrite(artifact, lambda d: d.update(schema="something.else/v1"))
    assert band.native_rows(artifact) == ()

    build(tmp_path)
    _rewrite(artifact, lambda d: d["band"].update(width=0.5))  # breaks the self-hash
    assert band.native_rows(artifact) == ()

    build(tmp_path)
    _rewrite(artifact, lambda d: d.update(claim=d["claim"].replace(band.SCOPE_LIMIT, "")))
    assert band.native_rows(artifact) == (), "a claim without the scope limit is not a band"

    build(tmp_path)
    with open(artifact, "a") as f:
        f.write("{not json\n")
    assert band.native_rows(artifact) == ()


def test_project_rejects_a_mutated_or_bare_native(tmp_path):
    native = band.native_rows(build(tmp_path))[0]
    tampered = {**native, "artifact": {**native["artifact"], "value": 1.0}}
    with pytest.raises(ct.ProjectionError):
        band.project(tampered)
    with pytest.raises(ct.ProjectionError):
        band.project({"artifact_path": "x"})
    with pytest.raises(ct.ProjectionError):
        band.project(native["artifact"])  # bypassing native_rows entirely


# --- carrier conformance ----------------------------------------------------------

def test_projection_is_registered_under_the_shared_registry():
    assert band.SOURCE_KIND in ct.registered()


def test_frames_go_through_the_shared_emitter(tmp_path):
    frames = band.frames_for_band(build(tmp_path), as_of="2026-08-26T13:01:00Z")
    assert len(frames) == 3  # source, claim, support
    support = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert support["assertion"]["grade"] == {"Q": "Witnessed", "T": "Attested"}
    assert support["assertion"]["protocol_id"] == band.PROTOCOL_ID
    assert support["assertion"]["metric_direction"] == "lower_better"
    claim = next(f for f in frames if f["frame_type"].endswith("claim_proposed/v1"))
    assert band.SCOPE_LIMIT in claim["assertion"]["display_text"]

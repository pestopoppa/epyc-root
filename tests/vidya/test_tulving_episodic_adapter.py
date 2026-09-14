"""SC67 — the Tulving episodic write-side hook and its strict reader.

What is pinned here, in the order this program has been burned:

* the doctrine boundary — a pre-hook scored run (``tulving_score.json``, no producer
  sidecar) emits ZERO rows and is never reconstructed on read (the DF2-4 precedent);
* the ladder is not reimplemented — the grade asserted below is whatever
  ``claim_tuple.grade()`` actually returns for the projected tuple;
* identity is unique per (run, arm, metric) and stable across re-reads, and the LOCATOR names
  the run, never a per-question file (SC6-HAZARD);
* a pre-M-12e scorer version is refused at BOTH ends — Simple Recall over every question is a
  different quantity under the same name;
* a tampered or malformed sidecar is inadmissible as a whole, and a decayed attestation
  grades DOWN instead of disappearing.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import tulving_episodic as reader  # noqa: E402
from adapters import tulving_episodic_capture as capture  # noqa: E402

SUMMARY = {
    "scorer_version": 2,
    "run_id": "20260914_101010",
    "model_role": "ingest_long_context",
    "config_name": "memory_off",
    "result_questions": 686,
    "scored_questions": 686,
    "missing_ground_truth": 0,
    "avg_f1": 0.4309,
    "simple_recall_score": 0.5684,
    "simple_recall_questions": 548,
    "simple_recall_bin_basis": "nb_events",
    "simple_recall_bins": {
        "0": {"count": 150, "avg_f1": 0.0},
        "1": {"count": 150, "avg_f1": 0.7340},
        "2": {"count": 148, "avg_f1": 0.7365},
        "3-5": {"count": 90, "avg_f1": 0.8032},
        "6+": {"count": 10, "avg_f1": 0.4},
    },
    "chronological_awareness_score": 0.1593,
    "latest_questions": 69,
    "chronological_questions": 69,
    "chronological_partial_coverage": 37,
}


def make_run(root: Path, *, name: str = "20260914_101010") -> Path:
    run = root / name
    run.mkdir()
    (run / "tulving_score.json").write_text(
        json.dumps({"summary": SUMMARY, "per_question": [{"question_id": "q0", "f1": 1.0}]}))
    return run


def write_sidecar(run: Path, *, summary=None, **overrides) -> Path:
    kwargs = dict(
        summary=summary or SUMMARY,
        run_id="20260914_101010",
        producer="score_tulving_run.py",
        arm="none",
        variant="Udefault_Sdefault_seed0",
        chapters=196,
        emitted_at="2026-09-14T12:00:00Z",
    )
    kwargs.update(overrides)
    return capture.write_belief_measurements(run / "tulving_score.json", **kwargs)


# --- the round trip, graded by THE ladder ---------------------------------------------------

def test_well_formed_sidecar_projects_and_reaches_witnessed_attested(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    natives = reader.native_rows(sidecar)
    assert len(natives) == 2  # Simple Recall + Chronological Awareness
    for native in natives:
        tup = reader.project(native)
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Witnessed", "Attested"), reasons
        assert reasons == []


def test_tuple_carries_the_sc67_identity_axes(tmp_path):
    run = make_run(tmp_path)
    by_metric = {n["row"]["metric"]: reader.project(n)
                 for n in reader.native_rows(write_sidecar(run))}

    srs = by_metric[capture.SIMPLE_RECALL_METRIC]
    assert srs.extra["arm"] == "none"
    assert srs.extra["variant"] == "Udefault_Sdefault_seed0"
    assert srs.extra["chapters"] == 196
    assert srs.extra["scorer_version"] == 2
    assert srs.extra["simple_recall_bin_basis"] == "nb_events"
    assert srs.metric_direction == "higher_better"
    # n is the SCORED subset, not the whole question set.
    assert srs.reps == 548 and srs.reps_basis == "scored:questions"

    cas = by_metric[capture.CHRONOLOGICAL_METRIC]
    assert cas.reps == 69 + 69
    assert cas.extra["chronological_partial_coverage"] == 37


def test_bin_zero_rides_in_the_tuple(tmp_path):
    """The hallucination bin is the point of the headline (M-12a)."""
    run = make_run(tmp_path)
    srs = next(reader.project(n) for n in reader.native_rows(write_sidecar(run))
               if n["row"]["metric"] == capture.SIMPLE_RECALL_METRIC)
    assert srs.extra["simple_recall_bins"]["0"]["count"] == 150


def test_locator_names_the_run_never_a_per_question_file(tmp_path):
    run = make_run(tmp_path)
    tups = [reader.project(n) for n in reader.native_rows(write_sidecar(run))]
    locators = {t.attestation_locator for t in tups}
    assert locators == {"tulving-episodic:20260914_101010:Udefault_Sdefault_seed0:196ch:arm-none"}
    for t in tups:
        assert "per_question" not in t.attestation_locator


def test_identity_is_unique_per_metric_and_stable(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    first = [reader.project(n).measurement_id for n in reader.native_rows(sidecar)]
    assert len(set(first)) == 2, "two disjoint subsets collapsed into one claim"
    second = [reader.project(n).measurement_id for n in reader.native_rows(sidecar)]
    assert first == second


def test_arms_of_the_same_run_are_distinct_claims(tmp_path):
    ids = set()
    for arm in sorted(capture.ARMS):
        run = make_run(tmp_path, name=f"run-{arm}")
        sidecar = write_sidecar(run, arm=arm)
        ids.update(reader.project(n).measurement_id for n in reader.native_rows(sidecar))
    assert len(ids) == 3 * 2


def test_attempted_reps_basis_is_stated_and_reasoned(tmp_path):
    summary = {**SUMMARY, "missing_ground_truth": 12,
               "scored_questions": 674, "result_questions": 686}
    run = make_run(tmp_path)
    tup = reader.project(reader.native_rows(write_sidecar(run, summary=summary))[0])
    assert tup.reps_basis.startswith("attempted")
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested")
    assert any("ATTEMPTED" in r for r in reasons), "overstated sample went unflagged"


# --- doctrine: pre-hook runs emit zero rows -------------------------------------------------

def test_pre_hook_run_emits_zero_rows(tmp_path):
    """A scored artifact with no producer sidecar — the 20260619_141212 shape.

    Including a re-score of it: the arm identity that run never captured cannot be
    reconstructed, so the sidecar is never written and the reader never invents one.
    """
    run = make_run(tmp_path, name="20260619_141212")
    (run / "tulving_score_rescored_20260914.json").write_text("{}")
    assert reader.rows_for_run(run) == ()


def test_missing_and_empty_sidecars_emit_zero_rows_without_error(tmp_path):
    run = make_run(tmp_path)
    assert reader.native_rows(run / capture.SIDECAR_NAME) == ()
    (run / capture.SIDECAR_NAME).write_text("")
    assert reader.native_rows(run / capture.SIDECAR_NAME) == ()


# --- the scorer version is a hard boundary --------------------------------------------------

def test_writer_refuses_a_pre_m12e_scorer_version(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="scorer_version"):
        write_sidecar(run, summary={**SUMMARY, "scorer_version": 1})
    with pytest.raises(capture.CaptureError, match="scorer_version"):
        write_sidecar(run, summary={k: v for k, v in SUMMARY.items()
                                    if k != "scorer_version"})
    assert not (run / capture.SIDECAR_NAME).exists(), "refusal must not half-write"


def test_reader_refuses_a_pre_m12e_row(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows[0]["extra"].update(scorer_version=1))
    assert reader.native_rows(sidecar) == ()


# --- strictness -----------------------------------------------------------------------------

def _rewrite(sidecar: Path, mutate) -> None:
    rows = [json.loads(line) for line in sidecar.read_text().splitlines()]
    mutate(rows)
    sidecar.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_any_malformed_row_voids_the_whole_sidecar(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)

    _rewrite(sidecar, lambda rows: rows[0].update(schema="something.else/v1"))
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows[1].update(value=0.99))  # breaks the self-hash
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    with open(sidecar, "a") as handle:
        handle.write("{not json\n")
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows.append(dict(rows[0])))  # duplicated identity
    assert reader.native_rows(sidecar) == ()


def test_reader_refuses_a_reps_that_does_not_match_the_subset(tmp_path):
    """Simple Recall reps must equal the get=='all' subset size, not the question count."""
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)

    def widen(rows):
        row = next(r for r in rows if r["metric"] == capture.SIMPLE_RECALL_METRIC)
        row["reps"] = 686
        row["row_sha256"] = capture.row_digest(row)

    _rewrite(sidecar, widen)
    assert reader.native_rows(sidecar) == ()


def test_project_rejects_a_mutated_or_bare_native(tmp_path):
    run = make_run(tmp_path)
    native = reader.native_rows(write_sidecar(run))[0]
    tampered = {**native, "row": {**native["row"], "value": 1.0}}
    with pytest.raises(ct.ProjectionError):
        reader.project(tampered)
    with pytest.raises(ct.ProjectionError):
        reader.project({"sidecar_path": "x"})
    with pytest.raises(ct.ProjectionError):
        reader.project(native["row"])  # bypassing native_rows entirely


def test_decayed_attestation_grades_down_not_away(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    (run / "tulving_score.json").write_text("mutated after score-time\n")
    natives = reader.native_rows(sidecar)
    assert len(natives) == 2, "a decayed artifact must surface, not vanish"
    for native in natives:
        q, t, reasons = ct.grade(reader.project(native))
        assert (q, t) == ("Witnessed", "Anchored")
        assert any("not on disk" in r for r in reasons)


# --- the writer refuses to guess ------------------------------------------------------------

def test_writer_refuses_an_unknown_arm(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="arm must be one of"):
        write_sidecar(run, arm="whatever")
    with pytest.raises(capture.CaptureError, match="arm must be one of"):
        write_sidecar(run, arm="")
    assert not (run / capture.SIDECAR_NAME).exists()


def test_writer_refuses_when_the_scored_artifact_is_absent(tmp_path):
    run = make_run(tmp_path)
    (run / "tulving_score.json").unlink()
    with pytest.raises(capture.CaptureError, match="scored artifact missing"):
        write_sidecar(run)


def test_writer_refuses_an_empty_summary(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="summary"):
        capture.write_belief_measurements(
            run / "tulving_score.json", summary={}, run_id="r",
            producer="score_tulving_run.py", arm="none",
            variant="Udefault_Sdefault_seed0", chapters=196)


def test_writer_does_not_recompute_the_metric(tmp_path):
    """The sidecar carries the scorer's own value verbatim; it cannot disagree with it."""
    run = make_run(tmp_path)
    rows = {json.loads(line)["metric"]: json.loads(line)
            for line in write_sidecar(run).read_text().splitlines()}
    assert rows[capture.SIMPLE_RECALL_METRIC]["value"] == SUMMARY["simple_recall_score"]
    assert (rows[capture.CHRONOLOGICAL_METRIC]["value"]
            == SUMMARY["chronological_awareness_score"])


# --- carrier conformance --------------------------------------------------------------------

def test_projection_is_registered_under_the_shared_registry():
    assert "tulving-episodic-measurement" in ct.registered()


def test_adapter_registers_no_ladder_of_its_own():
    """An adapter projects; it never grades (§4.7)."""
    source = Path(reader.__file__).read_text()
    assert "register_ladder" not in source
    assert "Witnessed" not in source.split('"""', 2)[2]


def test_frames_go_through_the_shared_emitter(tmp_path):
    run = make_run(tmp_path)
    frames = reader.frames_for_sidecar(write_sidecar(run), as_of="2026-09-14T13:00:00Z")
    assert len(frames) == 6  # 2 rows x (source, claim, support)
    supports = [f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1")]
    assert len(supports) == 2
    for sup in supports:
        assert sup["assertion"]["grade"] == {"Q": "Witnessed", "T": "Attested"}
        assert sup["assertion"]["category"] == "CANDIDATE"
    assert len({f["assertion"]["claim_id"] for f in frames
                if f["frame_type"].endswith("claim_proposed/v1")}) == 2

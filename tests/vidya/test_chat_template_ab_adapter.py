"""SC46 / CT-8 — the chat-template A/B write-side hook and its strict reader.

What is pinned here, in the order this program has been burned:

* the doctrine boundary — a pre-hook run directory (summary + per-question JSONL, no producer
  sidecar) emits ZERO rows and is never reconstructed on read (the DF2-4 precedent);
* the ladder is not reimplemented — the grade asserted below is whatever ``claim_tuple.grade()``
  actually returns for the projected tuple, driven through the one shared implementation;
* identity is unique per (run, arm, suite) cell and stable across re-reads;
* a tampered or malformed sidecar is inadmissible as a whole, and a decayed attestation grades
  DOWN instead of disappearing.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import chat_template_ab as reader  # noqa: E402
from adapters import chat_template_ab_capture as capture  # noqa: E402

KERNEL = {"source_commit": "0" * 39 + "a", "binary_version": "10125",
          "tree": "/mnt/raid0/llm/llama.cpp"}
SERVING = {"mode": "test_port", "host": "127.0.0.1", "port": 8990}
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "seed": 42,
            "max_tokens": 900, "enable_thinking": False}
SUMMARY = {
    "math": {
        "arm0": {"n": 40, "correct": 32, "truncated": 6, "errors": 0, "mean_tokens": 434.8},
        "arm1": {"n": 40, "correct": 35, "truncated": 2, "errors": 0, "mean_tokens": 280.0},
        "flips_01": 4, "flips_10": 1,
    },
    "gpqa_diamond": {
        "arm0": {"n": 40, "correct": 17, "truncated": 12, "errors": 0, "mean_tokens": 434.6},
        "arm1": {"n": 40, "correct": 24, "truncated": 3, "errors": 0, "mean_tokens": 210.0},
        "flips_01": 7, "flips_10": 0,
    },
}


def make_run(root: Path, summary=None) -> Path:
    run = root / "ct1-ab"
    run.mkdir()
    for arm in (0, 1):
        with open(run / f"results_arm{arm}.jsonl", "w") as f:
            for i in range(3):
                f.write(json.dumps({"id": f"q{i}", "arm": arm, "correct": bool(i % 2)}) + "\n")
    (run / "summary.json").write_text(json.dumps(summary or SUMMARY))
    return run


def write_sidecar(run: Path, **overrides) -> Path:
    kwargs = dict(
        run_id="ct1-ab-20260822", producer="ct1_ab_runner.py",
        model_path="/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
        model_name="Qwen3.6-35B-A3B-MTP", quant="Q8_0",
        kernel=KERNEL, serving=SERVING, sampling=SAMPLING,
        arms={0: {"label": "embedded", "template_sha256": "a" * 64},
              1: {"label": "epyc-qwen3x-v1", "template_sha256": "b" * 64}},
        baseline_arm=0,
        emitted_at="2026-08-22T12:00:00Z",
    )
    kwargs.update(overrides)
    return capture.write_belief_measurements(run, **kwargs)


# --- the round trip, graded by THE ladder ---------------------------------------------------

def test_well_formed_sidecar_projects_and_reaches_witnessed_attested(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    natives = reader.native_rows(sidecar)
    assert len(natives) == 4  # 2 suites x 2 arms
    for native in natives:
        tup = reader.project(native)
        q, t, reasons = ct.grade(tup)
        # Asserted from the ladder's own answer: full tuple, artifact hashed AND on disk.
        assert (q, t) == ("Witnessed", "Attested"), reasons
        assert reasons == []


def test_tuple_carries_the_sc46_identity_axes(tmp_path):
    run = make_run(tmp_path)
    tup = reader.project(reader.native_rows(write_sidecar(run))[0])
    assert tup.extra["template_sha256"] in {"a" * 64, "b" * 64}
    assert tup.extra["kernel"]["source_commit"] == KERNEL["source_commit"]
    assert tup.extra["kernel"]["binary_version"] == "10125"
    assert tup.extra["quant"] == "Q8_0"
    assert tup.extra["serving"]["mode"] == "test_port"
    assert tup.extra["sampling"]["seed"] == 42
    assert tup.metric_direction == "higher_better"
    assert tup.reps == 40 and tup.reps_basis == "scored:questions"


def test_identity_is_unique_per_cell_and_stable(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    first = [reader.project(n).measurement_id for n in reader.native_rows(sidecar)]
    assert len(set(first)) == 4, "distinct (arm, suite) cells merged into one claim"
    second = [reader.project(n).measurement_id for n in reader.native_rows(sidecar)]
    assert first == second


def test_flips_ride_on_the_candidate_arm_only(tmp_path):
    run = make_run(tmp_path)
    by_cell = {(n["row"]["extra"]["arm"], n["row"]["extra"]["suite"]): n["row"]
               for n in reader.native_rows(write_sidecar(run))}
    base = by_cell[(0, "math")]["extra"]
    cand = by_cell[(1, "math")]["extra"]
    assert "flips_01" not in base and "flips_10" not in base
    assert (cand["flips_01"], cand["flips_10"], cand["paired_against_arm"]) == (4, 1, 0)
    assert by_cell[(0, "math")]["category"] == "BASELINE"
    assert by_cell[(1, "math")]["category"] == "CANDIDATE"


def test_attempted_reps_basis_is_stated_and_reasoned(tmp_path):
    summary = {"math": {"arm0": {"n": 40, "correct": 30, "truncated": 5, "errors": 3},
                        "arm1": {"n": 40, "correct": 31, "truncated": 4, "errors": 0},
                        "flips_01": 2, "flips_10": 1}}
    run = make_run(tmp_path, summary)
    natives = reader.native_rows(write_sidecar(run))
    tup = next(reader.project(n) for n in natives if n["row"]["extra"]["arm"] == 0)
    assert tup.reps_basis.startswith("attempted")
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested")
    assert any("ATTEMPTED" in r for r in reasons), "overstated sample went unflagged"


# --- doctrine: pre-hook runs emit zero rows -------------------------------------------------

def test_pre_hook_run_emits_zero_rows(tmp_path):
    """summary.json + per-question JSONL, no producer sidecar: the completed CT-1/CT-1b/CT-5/16K
    shape. Never reconstructed on read."""
    run = make_run(tmp_path)
    assert reader.rows_for_run(run) == ()


def test_missing_and_empty_sidecars_emit_zero_rows_without_error(tmp_path):
    run = make_run(tmp_path)
    assert reader.native_rows(run / "belief_measurements.jsonl") == ()
    (run / "belief_measurements.jsonl").write_text("")
    assert reader.native_rows(run / "belief_measurements.jsonl") == ()


# --- strictness -----------------------------------------------------------------------------

def _rewrite(sidecar: Path, mutate) -> None:
    rows = [json.loads(l) for l in sidecar.read_text().splitlines()]
    mutate(rows)
    sidecar.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_any_malformed_row_voids_the_whole_sidecar(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)

    _rewrite(sidecar, lambda rows: rows[0].update(schema="something.else/v1"))
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows[2]["extra"].update(correct=39))  # breaks value + row hash
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    with open(sidecar, "a") as f:
        f.write("{not json\n")
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
    (run / "results_arm1.jsonl").write_text("mutated after summarize-time\n")
    natives = reader.native_rows(sidecar)
    assert len(natives) == 4, "a decayed artifact must surface, not vanish"
    for native in natives:
        tup = reader.project(native)
        q, t, reasons = ct.grade(tup)
        if native["row"]["extra"]["arm"] == 1:
            assert (q, t) == ("Witnessed", "Anchored")
            assert any("not on disk" in r for r in reasons)
        else:
            assert (q, t) == ("Witnessed", "Attested")


# --- the writer refuses to guess ------------------------------------------------------------

def test_writer_refuses_a_missing_template_digest(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="template_sha256"):
        write_sidecar(run, arms={0: {"label": "embedded", "template_sha256": ""},
                                 1: {"label": "v1", "template_sha256": "b" * 64}})
    assert not (run / "belief_measurements.jsonl").exists(), "refusal must not half-write"


def test_writer_refuses_an_unstamped_kernel(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="source_commit"):
        write_sidecar(run, kernel={"binary_version": "10125"})
    with pytest.raises(capture.CaptureError, match="binary_version"):
        write_sidecar(run, kernel={"source_commit": "0" * 39 + "a"})


def test_writer_refuses_when_the_scored_artifact_is_absent(tmp_path):
    run = make_run(tmp_path)
    (run / "results_arm1.jsonl").unlink()
    with pytest.raises(capture.CaptureError, match="results file missing"):
        write_sidecar(run)


def test_writer_requires_summarize_time(tmp_path):
    run = tmp_path / "no-summary"
    run.mkdir()
    with pytest.raises(capture.CaptureError, match="summarize-time"):
        capture.write_belief_measurements(
            run, run_id="r", producer="p", model_path="m", model_name="m", quant="Q8_0",
            kernel=KERNEL, serving=SERVING, sampling=SAMPLING,
            arms={0: {"label": "a", "template_sha256": "a" * 64}})


# --- carrier conformance --------------------------------------------------------------------

def test_projection_is_registered_under_the_shared_registry():
    assert "chat-template-ab-measurement" in ct.registered()


def test_frames_go_through_the_shared_emitter(tmp_path):
    run = make_run(tmp_path)
    frames = reader.frames_for_sidecar(write_sidecar(run), as_of="2026-08-22T13:00:00Z")
    assert len(frames) == 12  # 4 rows x (source, claim, support)
    supports = [f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1")]
    assert len(supports) == 4
    for sup in supports:
        assert sup["assertion"]["grade"] == {"Q": "Witnessed", "T": "Attested"}
        assert sup["assertion"]["category"] in {"BASELINE", "CANDIDATE"}
    assert len({f["assertion"]["claim_id"] for f in frames
                if f["frame_type"].endswith("claim_proposed/v1")}) == 4

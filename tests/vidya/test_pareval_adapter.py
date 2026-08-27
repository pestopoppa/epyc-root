"""SC45 — the ParEval driver-record strict reader (RVP-C5-6 pre-wiring).

What is pinned here, in the order this program has been burned:

* the **cell locator rule** — one claim per (problem, parallelism_model, k, n)
  cell; the N LLM outputs a run evaluates are one witness, never N;
* the **never-reconstruct-on-read doctrine** — pass@k/build@k/speedup_n@k/
  efficiency_n@k are ONLY what the collect-time hook derived from the run's own
  output; a record is refused, never repaired, on read;
* the **O0 caveat is load-bearing and rides IN the tuple** — the claim states it
  verbatim and the reader refuses any record whose claim does not;
* the **arm rule** — serial is BASELINE (its locally measured
  best_sequential_runtime is the reference), parallel arms are CANDIDATE; a
  mislabeled record is malformed;
* **direction per field** — pass@k/build@k/speedup_n@k/efficiency_n@k
  higher_better, best_sequential_runtime lower_better, recorded in extra;
* **attestation honesty** — sha256 at collect time; in a git tree pinned at the
  recorded revision the artifact is pin-verifiable (``Witnessed/Attested``),
  out-of-tree or off-pin is ``Witnessed/Anchored``, and a RECOMPUTED hash that
  disagrees with the recorded one is tampering: the whole records file is
  refused (fail closed);
* the ladder is not reimplemented — every grade asserted below is whatever
  ``claim_tuple.grade()`` actually returns.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import pareval  # noqa: E402

HARDWARE = "AMD EPYC 9655 (96C/192T) CPU-only, g++ 15.2 -fopenmp"
RUN_ID = "c5-6-serial-omp-20260827T120000Z"
EMITTED = "2026-08-27T12:00:00Z"
PROBLEM_SIZES = {
    "25_reduce_xor": {"serial": "(1<<18)", "omp": "(1<<18)"},
    "26_reduce_product_of_inverses": {"serial": "(1<<18)", "omp": "(1<<18)"},
}


def serial_output(did_build=True, all_valid=True, baseline=0.004, runtime=0.004):
    return {
        "generated_output": "// synthetic",
        "source_write_success": True,
        "did_build": did_build,
        "is_source_valid": True,
        "did_any_run": did_build,
        "did_all_run": did_build and all_valid,
        "are_any_valid": all_valid,
        "are_all_valid": all_valid,
        "best_sequential_runtime": baseline,
        "runs": [{"did_run": did_build, "is_valid": all_valid, "runtime": runtime}],
    }


def omp_output(all_valid=True, baseline=0.005, runtime_96=0.0005, runtime_1=0.005):
    return {
        "generated_output": "// synthetic omp",
        "source_write_success": True,
        "did_build": True,
        "is_source_valid": True,
        "did_any_run": True,
        "did_all_run": all_valid,
        "are_any_valid": all_valid,
        "are_all_valid": all_valid,
        "best_sequential_runtime": baseline if all_valid else None,
        "runs": [
            {"did_run": True, "is_valid": all_valid, "runtime": runtime_96,
             "num_threads": 96},
            {"did_run": True, "is_valid": all_valid, "runtime": runtime_1,
             "num_threads": 1},
        ],
    }


def synthetic_run_output() -> list[dict]:
    """Two problems: a serial arm and an omp arm, 3 outputs each (post run-all.py)."""
    return [
        {
            "problem_type": "reduce", "language": "cpp",
            "name": "25_reduce_xor", "parallelism_model": "serial",
            "prompt": "/* reduce xor */",
            "outputs": [
                serial_output(all_valid=True, baseline=0.004, runtime=0.004),
                serial_output(all_valid=True, baseline=0.0042, runtime=0.0042),
                serial_output(all_valid=False, baseline=0.0041, runtime=None),
            ],
        },
        {
            "problem_type": "reduce", "language": "cpp",
            "name": "26_reduce_product_of_inverses", "parallelism_model": "omp",
            "prompt": "/* omp reduce */",
            "outputs": [
                omp_output(all_valid=True, baseline=0.005, runtime_96=0.0005),
                omp_output(all_valid=True, baseline=0.0051, runtime_96=0.0004),
                omp_output(all_valid=False, baseline=None, runtime_96=None),
            ],
        },
    ]


def write_run_output(tmp_path: Path) -> Path:
    path = tmp_path / "run-output.json"
    path.write_text(json.dumps(synthetic_run_output(), indent=1))
    return path


def write_records_file(tmp_path: Path, *records: dict, name="records.jsonl") -> Path:
    path = tmp_path / name
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def post_hook_record(**overrides) -> dict:
    """A synthetic post-hook driver record, exactly as the C5-6 hook emits it."""
    record = {
        "schema": pareval.SCHEMA,
        "run_id": RUN_ID,
        "emitted_at": EMITTED,
        "pareval_revision": pareval.PAREVAL_REVISION,
        "problem": "25_reduce_xor",
        "problem_type": "reduce",
        "parallelism_model": "serial",
        "category": "BASELINE",
        "k": 1,
        "n": 1,
        "num_samples": 3,
        "num_valid": 2,
        "num_valid_at_n": 2,
        "pass@k": 2 / 3,
        "build@k": 1.0,
        "speedup_n@k": 1.0,
        "efficiency_n@k": 1.0,
        "best_sequential_runtime": 0.004,
        "hardware": HARDWARE,
        "problem_size": "(1<<18)",
        "claim": "synthetic claim " + pareval.CAVEAT,
        "run_output_path": "run-output.json",
        "run_output_sha256": hashlib.sha256(b"placeholder").hexdigest(),
    }
    record.update(overrides)
    return record


def write_fixture(tmp_path: Path, **overrides) -> tuple[Path, Path]:
    """run output + records file wired to each other (out-of-tree: no git repo)."""
    run_out = write_run_output(tmp_path)
    record = post_hook_record(**overrides)
    if "run_output_sha256" not in overrides:
        record["run_output_sha256"] = hashlib.sha256(run_out.read_bytes()).hexdigest()
    records = write_records_file(tmp_path, record)
    return records, run_out


# --- projection + the shared ladder -------------------------------------------

def test_post_hook_record_projects_row_with_all_fields_and_caveat(tmp_path):
    records, run_out = write_fixture(tmp_path)
    natives = pareval.native_rows(records)
    assert len(natives) == 1, "one driver record = one claim"
    tup = pareval.project(natives[0])

    # every field of the driver record is on the projected row
    assert tup.metric == "pass@k" and tup.value == pytest.approx(2 / 3)
    assert tup.category == "BASELINE"
    assert tup.protocol_id == pareval.SCHEMA, "protocol id = native schema version"
    assert tup.reps == 3 and tup.reps_basis.startswith("evaluated:LLM outputs")
    assert tup.unit == "fraction_0_1"
    for key in ("pass@k", "build@k", "speedup_n@k", "efficiency_n@k",
                "best_sequential_runtime", "hardware", "problem", "problem_type",
                "parallelism_model", "k", "n", "num_valid", "num_valid_at_n",
                "problem_size", "run_id", "pareval_revision", "run_output_sha256"):
        assert key in tup.extra, f"extra must carry {key}"
    assert tup.extra["best_sequential_runtime"] == 0.004
    assert tup.extra["hardware"] == HARDWARE
    assert tup.extra["git_pinned"] is False

    # the O0 caveat is IN the tuple, verbatim
    assert pareval.CAVEAT in tup.claim
    assert tup.extra["caveat"] == pareval.CAVEAT

    # direction recorded per field, and on the tuple's own metric
    assert tup.metric_direction == "higher_better"
    assert tup.extra["metric_directions"]["pass@k"] == "higher_better"
    assert tup.extra["metric_directions"]["best_sequential_runtime"] == "lower_better"

    # out-of-tree artifact: the honest grade is anchored, not attested
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_attested_when_artifact_is_in_a_tree_pinned_at_the_recorded_revision(
        tmp_path, monkeypatch):
    records, run_out = write_fixture(tmp_path)
    # The pin rule is real: git rev-parse HEAD must equal the recorded revision.
    # Fabricating a commit at the exact hash 9e2a9afafa2c… is impossible, so the
    # git probe is stubbed to the honest outcome of an artifact that lives in the
    # pinned pareval clone (the real-world case for the C5-6 results dir).
    monkeypatch.setattr(pareval, "_git_head", lambda directory: pareval.PAREVAL_REVISION)
    tup = pareval.project(pareval.native_rows(records)[0])
    assert tup.extra["git_pinned"] is True
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested"), reasons
    assert reasons == []


def test_anchored_when_the_tree_moved_off_its_pin(tmp_path, monkeypatch):
    records, run_out = write_fixture(tmp_path)
    # the tree moved off the revision the record names -> re-derivable, not pinned
    monkeypatch.setattr(pareval, "_git_head", lambda directory: "0" * 40)
    tup = pareval.project(pareval.native_rows(records)[0])
    assert tup.extra["git_pinned"] is False, "off-pin tree = re-derivable, not pinned"
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_missing_attested_artifact_decays_the_grade_not_the_record(tmp_path):
    records, run_out = write_fixture(tmp_path)
    run_out.unlink()
    tup = pareval.project(pareval.native_rows(records)[0])
    assert tup.extra["git_pinned"] is False
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons
    assert any("not on disk" in r for r in reasons)


# --- the arm rule -----------------------------------------------------------------

def test_serial_arm_is_baseline_and_parallel_arm_is_candidate(tmp_path):
    run_out = write_run_output(tmp_path)
    records = pareval.derive_driver_records(
        run_out, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
        problem_sizes=PROBLEM_SIZES, k_values=(1,), n=1)
    serial = next(r for r in records if r["parallelism_model"] == "serial")
    omp = next(r for r in records if r["parallelism_model"] == "omp")
    assert serial["category"] == "BASELINE"
    assert omp["category"] == "CANDIDATE"


def test_mislabeled_arm_category_is_malformed(tmp_path):
    records, _ = write_fixture(tmp_path, category="CANDIDATE")  # serial = CANDIDATE?
    assert pareval.native_rows(records) == ()
    assert "BASELINE" in pareval.refusal_reason(records)

    records2, _ = write_fixture(tmp_path, parallelism_model="omp", category="BASELINE")
    assert pareval.native_rows(records2) == ()
    assert "CANDIDATE" in pareval.refusal_reason(records2)


# --- strictness --------------------------------------------------------------------

def test_missing_and_partial_records_refuse_with_named_causes(tmp_path):
    records, _ = write_fixture(tmp_path, **{"speedup_n@k": None})
    assert pareval.native_rows(records) == ()
    assert "malformed" in pareval.refusal_reason(records)
    assert "speedup_n@k must be a finite number" in pareval.refusal_reason(records)

    records2, _ = write_fixture(tmp_path, best_sequential_runtime=0.0)
    assert pareval.native_rows(records2) == ()
    assert "best_sequential_runtime must be > 0" in pareval.refusal_reason(records2)

    records3, _ = write_fixture(
        tmp_path, claim="no caveat here",
        run_output_sha256=hashlib.sha256(b"x").hexdigest())
    assert pareval.native_rows(records3) == ()
    assert "caveat verbatim" in pareval.refusal_reason(records3)

    # a record from another revision is refused: the pin is part of the identity
    records4, _ = write_fixture(tmp_path, pareval_revision="0" * 40)
    assert pareval.native_rows(records4) == ()
    assert "pareval_revision" in pareval.refusal_reason(records4)


def test_project_rejects_bypass_and_mutation(tmp_path):
    records, _ = write_fixture(tmp_path)
    native = pareval.native_rows(records)[0]
    mutated = {**native, "record": {**native["record"], "pass@k": "not-a-number"}}
    with pytest.raises(ct.ProjectionError):
        pareval.project(mutated)
    with pytest.raises(ct.ProjectionError):
        pareval.project({"record_path": "x"})
    with pytest.raises(ct.ProjectionError):
        pareval.project(native["record"])  # bypassing native_rows entirely


# --- tamper: fail closed ------------------------------------------------------------

def test_tampered_run_output_fails_closed(tmp_path):
    records, run_out = write_fixture(tmp_path)
    assert len(pareval.native_rows(records)) == 1
    with open(run_out, "a") as f:  # one extra byte = corruption, not decay
        f.write("\n")
    assert pareval.native_rows(records) == ()
    reason = pareval.refusal_reason(records)
    assert reason.startswith("tampered"), reason
    assert "no longer matches the collect-time sha256" in reason


def test_tampered_recorded_hash_fails_closed(tmp_path):
    records, run_out = write_fixture(
        tmp_path, run_output_sha256=hashlib.sha256(b"other").hexdigest())
    assert pareval.native_rows(records) == ()
    assert pareval.refusal_reason(records).startswith("tampered")


def test_non_json_line_voids_the_whole_file(tmp_path):
    records, _ = write_fixture(tmp_path)
    with open(records, "a") as f:
        f.write("{not json\n")
    assert pareval.native_rows(records) == ()
    assert pareval.refusal_reason(records).startswith("malformed")


# --- honest zero ----------------------------------------------------------------------

def test_absent_and_empty_records_file_are_not_measurements(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert pareval.native_rows(missing) == ()
    assert pareval.refusal_reason(missing) == "no emissions"
    assert pareval.frames_for_records(missing, as_of="2026-08-27T13:00:00Z") == []

    empty = write_records_file(tmp_path)
    assert pareval.native_rows(empty) == ()
    assert pareval.refusal_reason(empty) == "no emissions"


# --- identity ---------------------------------------------------------------------------

def test_identity_is_unique_per_cell_and_stable(tmp_path):
    run_out = write_run_output(tmp_path)
    records = pareval.derive_driver_records(
        run_out, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
        problem_sizes=PROBLEM_SIZES, k_values=(1, 5), n=96)
    path = write_records_file(tmp_path, *records, name="multi.jsonl")
    ids = [pareval.project(n).measurement_id for n in pareval.native_rows(path)]
    assert len(ids) == len(set(ids)), "distinct cells must not merge into one claim"
    # serial cells are always n=1; the parallel arm is evaluated at n=96
    assert "pareval_c5-6-serial-omp-20260827T120000Z_25_reduce_xor_serial_k1_n1" in ids
    assert "pareval_c5-6-serial-omp-20260827T120000Z_26_reduce_product_of_inverses_omp_k1_n96" in ids
    again = [pareval.project(n).measurement_id for n in pareval.native_rows(path)]
    assert ids == again, "the same records file must re-derive the same identities"


# --- the collect-time derive hook -------------------------------------------------------

def test_derive_round_trip_projects_the_runs_own_numbers(tmp_path):
    run_out = write_run_output(tmp_path)
    records = pareval.derive_driver_records(
        run_out, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
        problem_sizes=PROBLEM_SIZES, k_values=(1,), n=96)
    assert len(records) == 2  # one serial + one omp cell at k=1

    serial = next(r for r in records if r["parallelism_model"] == "serial")
    assert serial["pass@k"] == pytest.approx(2 / 3)   # 2 of 3 outputs valid, k=1
    # upstream _speedupk: min baseline 0.004 over the 2 valid serial runtimes
    assert serial["speedup_n@k"] == pytest.approx(
        0.004 / 2 / 0.004 + 0.004 / 2 / 0.0042)
    assert serial["best_sequential_runtime"] == pytest.approx(0.004)
    assert serial["category"] == "BASELINE"
    assert serial["n"] == 1, "the serial cell is always n=1 (config-less sweep)"

    omp = next(r for r in records if r["parallelism_model"] == "omp")
    # upstream _speedupk over sorted runtimes [0.0004, 0.0005], baseline 0.005, k=1
    assert omp["pass@k"] == pytest.approx(2 / 3)
    assert omp["speedup_n@k"] == pytest.approx(
        0.005 / 2 / 0.0004 + 0.005 / 2 / 0.0005)
    assert omp["efficiency_n@k"] == pytest.approx(omp["speedup_n@k"] / 96)
    assert omp["num_valid_at_n"] == 2
    assert omp["category"] == "CANDIDATE"
    assert omp["n"] == 96

    path = pareval.write_records(records, tmp_path / "records.jsonl")
    assert len(pareval.native_rows(path)) == 2
    tup = pareval.project(pareval.native_rows(path)[1])
    assert tup.extra["speedup_n@k"] == pytest.approx(omp["speedup_n@k"])
    assert pareval.CAVEAT in tup.claim


def test_derive_refuses_cells_the_run_did_not_measure(tmp_path):
    run_out = write_run_output(tmp_path)

    # n absent from the launch sweep: no cell was measured at that count
    with pytest.raises(pareval.CaptureError, match="never ran at n=64"):
        pareval.derive_driver_records(
            run_out, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
            problem_sizes=PROBLEM_SIZES, k_values=(1,), n=64)

    # a model outside the CPU serial+omp v1 scope is the C5-7 hook's job
    hip_data = [{"problem_type": "reduce", "language": "cpp", "name": "x",
                 "parallelism_model": "hip", "prompt": "p",
                 "outputs": [serial_output()]}]
    hip_file = tmp_path / "hip.json"
    hip_file.write_text(json.dumps(hip_data))
    with pytest.raises(pareval.CaptureError, match="C5-7"):
        pareval.derive_driver_records(
            hip_file, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
            problem_sizes=PROBLEM_SIZES, k_values=(1,), n=1)

    # no locally measured baseline: nothing to anchor speedup to
    no_baseline = [{
        "problem_type": "reduce", "language": "cpp", "name": "y",
        "parallelism_model": "serial", "prompt": "p",
        "outputs": [serial_output(all_valid=False, baseline=None)],
    }]
    nb_file = tmp_path / "no-baseline.json"
    nb_file.write_text(json.dumps(no_baseline))
    with pytest.raises(pareval.CaptureError, match="NO best_sequential_runtime"):
        pareval.derive_driver_records(
            nb_file, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
            problem_sizes=PROBLEM_SIZES, k_values=(1,), n=1)

    # the fixed problem size is part of the caveat: refuse a missing mapping
    with pytest.raises(pareval.CaptureError, match="problem-sizes.json has no"):
        pareval.derive_driver_records(
            run_out, run_id=RUN_ID, emitted_at=EMITTED, hardware=HARDWARE,
            problem_sizes={}, k_values=(1,), n=1)


# --- carrier conformance --------------------------------------------------------------

def test_projection_is_registered_under_the_shared_registry():
    assert pareval.SOURCE_KIND in ct.registered()


def test_frames_go_through_the_shared_emitter(tmp_path):
    records, _ = write_fixture(tmp_path)
    frames = pareval.frames_for_records(records, as_of="2026-08-27T13:00:00Z")
    assert len(frames) == 3  # source, claim, support
    support = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert support["assertion"]["grade"] == {"Q": "Witnessed", "T": "Anchored"}
    assert support["assertion"]["protocol_id"] == pareval.SCHEMA
    assert support["assertion"]["reps"] == 3
    assert support["assertion"]["category"] == "BASELINE"
    assert support["assertion"]["metric_direction"] == "higher_better"
    claim = next(f for f in frames if f["frame_type"].endswith("claim_proposed/v1"))
    assert pareval.CAVEAT in claim["assertion"]["display_text"]

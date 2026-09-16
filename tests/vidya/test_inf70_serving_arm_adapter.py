"""SC75 / VB-INF70-ARMS: the INF-70 serving-arm write-side hook and its strict reader.

What these tests pin down:

* **the contention verdict is mandatory**: no ``.coresidency`` or no samples means no row, and
  a CLASSIFY-ERROR is unknown, never clean;
* **arms before 2026-09-07 emit zero rows**, whether they are caught by date or by the
  legacy sampler vocabulary, and a backfill long after the arm is refused;
* **a pre-hook arm** (rows + coresidency, but no sidecar) emits zero rows on read;
* **the ladder is not reimplemented**: the grade is whatever ``claim_tuple.grade()`` returns;
* **locator = the arm/launch**, never a per-prompt row, and ``reps`` counts launches;
* DIRECT and SMT-SIBLING stay separate, and the verdict is part of the identity.

The fixtures copy the real HARNESS-1 record shapes
(``/mnt/raid0/llm/tmp/inf70/agents/harness1/runs/A_OLD1.*``).
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import inf70_serving_arm as reader  # noqa: E402
from adapters import inf70_serving_arm_capture as capture  # noqa: E402

LABEL = "B_NEW1"
STARTED = "2026-09-16T10:00:00Z"
ENDED = "2026-09-16T10:05:00Z"
EMITTED = "2026-09-16T10:05:10Z"

CLEAN_CORES = """=== 10:00:10 load=1.0 1.0 1.0
  SELF pid=100 cpu=3000 llama-server
  FOREIGN pid=200 cpu=7.6 comm=claude exe=/x/claude cpus_allowed=200-207 DISJOINT-FROM-BENCH-CORES
=== 10:00:30 load=1.0 1.0 1.0
  SELF pid=100 cpu=3000 llama-server
  FOREIGN pid=201 cpu=500 comm=ps exe=? cpus_allowed=? GONE
"""

SMT_CORES = """=== 10:00:10 load=9.0 9.0 9.0
  SELF pid=100 cpu=3000 llama-server
  FOREIGN pid=300 cpu=99.9 comm=python exe=/x/python cpus_allowed=184-191 SMT-SIBLING-CONTENTION: 184-191 are the SMT siblings of bench cores 88-95
=== 10:00:30 load=9.0 9.0 9.0
  SELF pid=100 cpu=3000 llama-server
  FOREIGN pid=300 cpu=99.5 comm=python exe=/x/python cpus_allowed=184-191 SMT-SIBLING-CONTENTION: 184-191 are the SMT siblings of bench cores 88-95
  FOREIGN pid=301 cpu=88.7 comm=python3 exe=/x/python3 cpus_allowed=0-191 DIRECT-OVERLAP on 0-95 +SMT-siblings 96-191 of 0-95
"""

LEGACY_CORES = """=== 10:00:10 load=9.0 9.0 9.0
  FOREIGN pid=300 cpu=99.9 comm=python cpus_allowed=184-191 disjoint-from-0-95
"""


def _prompt_row(seq, pred_n, pred_ms, verdict="COHERENT"):
    return {"seq": seq, "id": f"p{seq}", "cls": "coding", "prompt_n": 300, "pred_n": pred_n,
            "prompt_ms": 1400.0, "pred_ms": pred_ms, "finish": "stop", "verdict": verdict,
            "sha": f"{seq:016x}"}


ROWS = [
    _prompt_row(0, 160, 8000.0),
    _prompt_row(1, 240, 12000.0),
    _prompt_row(2, 8, 400.0, verdict="EMPTY"),  # below the pred_n floor: excluded from rate
    _prompt_row(3, 100, 5000.0, verdict="REPETITION"),
]

LAUNCH = {
    "launch_id": "harness1-S3-20260916T100000Z",
    "model_path": "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/x.gguf",
    "gguf_sha256": "a" * 64,
    "kernel_commit": "eae02f2dc",
    "binary_version": "10242 (eae02f2dc)",
    "launch_recipe": {
        "env": {"OMP_PROC_BIND": "spread", "GGML_IQK": "1", "GGML_NOHUGEPAGE_PROCESS": "1"},
        "args": ["-t", "48", "-c", "8192", "--no-mmap", "-fa", "on"],
    },
    "pinning": "taskset -c 0-95 numactl --interleave=all",
    "bench_cpus": "0-95",
}


def make_arm(root: Path, *, label=LABEL, cores=CLEAN_CORES, rows=ROWS) -> Path:
    runs = root / "runs"
    runs.mkdir(exist_ok=True)
    (runs / f"{label}.rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    if cores is not None:
        (runs / f"{label}.coresidency").write_text(cores)
    (runs / f"{label}.timeline").write_text("10:00:00 +0s ARM start\n")
    return runs


def write(runs: Path, **overrides) -> Path:
    kwargs = dict(launch=LAUNCH, arm_started_at=STARTED, producer="arm_hot.sh",
                  emitted_at=EMITTED, arm_ended_at=ENDED)
    kwargs.update(overrides)
    label = kwargs.pop("label", LABEL)
    return capture.write_arm_measurement(runs, label, **kwargs)


# --- the round trip, graded by THE ladder ---------------------------------------------------

def test_clean_arm_projects_and_reaches_witnessed_attested(tmp_path):
    runs = make_arm(tmp_path)
    natives = reader.native_rows(write(runs))
    assert len(natives) == 1
    tup = reader.project(natives[0])
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested"), reasons
    assert tup.extra["contention_verdict"] == capture.VERDICT_CLEAN


def test_rate_is_token_weighted_with_the_pred_n_floor(tmp_path):
    runs = make_arm(tmp_path)
    tup = reader.project(reader.native_rows(write(runs))[0])
    # (160 + 240 + 100) / (8 + 12 + 5) s — the pred_n=8 row is below the floor.
    assert tup.value == pytest.approx(500 / 25.0)
    assert tup.unit == "tokens/s" and tup.metric_direction == "higher_better"
    assert tup.extra["n_rows"] == 4 and tup.extra["n_decode_rows"] == 3
    assert tup.extra["coherence_by_reason"] == {"COHERENT": 2, "EMPTY": 1, "REPETITION": 1}


def test_contended_arm_still_emits_but_carries_the_verdict_separately(tmp_path):
    runs = make_arm(tmp_path, cores=SMT_CORES)
    tup = reader.project(reader.native_rows(write(runs))[0])
    c = tup.extra["contention"]
    assert c["contention_verdict"] == capture.VERDICT_CONTENDED
    assert c["smt_sibling_lines"] == 2 and c["direct_overlap_lines"] == 1
    assert c["foreign_cpu_max"] == pytest.approx(188.2)
    assert c["sampler_version"] == capture.SAMPLER_VERSION
    assert "contention-CONTENDED" in tup.attestation_locator


def test_verdict_is_part_of_the_identity(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = reader.project(reader.native_rows(write(make_arm(tmp_path / "a")))[0])
    b = reader.project(reader.native_rows(write(make_arm(tmp_path / "b", cores=SMT_CORES)))[0])
    assert a.measurement_id != b.measurement_id


def test_thp_knob_state_rides_in_the_tuple(tmp_path):
    runs = make_arm(tmp_path)
    tup = reader.project(reader.native_rows(write(runs))[0])
    assert tup.extra["thp_knob_state"] == "set:1"
    unset = json.loads(json.dumps(LAUNCH))
    del unset["launch_recipe"]["env"]["GGML_NOHUGEPAGE_PROCESS"]
    (tmp_path / "u").mkdir()
    runs2 = make_arm(tmp_path / "u")
    tup2 = reader.project(reader.native_rows(write(runs2, launch=unset))[0])
    assert tup2.extra["thp_knob_state"] == "unset"


# --- no verdict, no row -------------------------------------------------------------------

def test_missing_coresidency_is_refused(tmp_path):
    runs = make_arm(tmp_path, cores=None)
    with pytest.raises(capture.CaptureError, match="no verdict"):
        write(runs)
    assert reader.rows_for_run_dir(runs) == ()


def test_zero_samples_is_refused(tmp_path):
    runs = make_arm(tmp_path, cores="")
    with pytest.raises(capture.CaptureError, match="no samples"):
        write(runs)


def test_classify_error_is_unknown_not_clean(tmp_path):
    cores = "=== 10:00:10\n  FOREIGN pid=1 cpu=50 comm=x cpus_allowed=0-3 CLASSIFY-ERROR\n"
    runs = make_arm(tmp_path, cores=cores)
    with pytest.raises(capture.CaptureError, match="CLASSIFY-ERROR"):
        write(runs)


# --- pre-2026-09-07 arms are worse than absent ----------------------------------------------

def test_arm_before_the_sampler_fix_emits_zero_rows(tmp_path):
    runs = make_arm(tmp_path)
    with pytest.raises(capture.CaptureError, match="before 2026-09-07"):
        write(runs, arm_started_at="2026-09-06T23:59:59Z",
              arm_ended_at="2026-09-07T00:04:00Z", emitted_at="2026-09-07T00:04:10Z")
    assert reader.rows_for_run_dir(runs) == ()


def test_legacy_sampler_vocabulary_is_refused(tmp_path):
    runs = make_arm(tmp_path, cores=LEGACY_CORES)
    with pytest.raises(capture.CaptureError, match="legacy sampler"):
        write(runs)


def test_undated_arm_fails_closed(tmp_path):
    runs = make_arm(tmp_path)
    with pytest.raises(capture.CaptureError):
        write(runs, arm_started_at="")


def test_backfill_long_after_the_arm_is_refused(tmp_path):
    runs = make_arm(tmp_path)
    with pytest.raises(capture.CaptureError, match="backfill"):
        write(runs, emitted_at="2026-09-18T10:05:00Z")


def test_forged_sidecar_for_a_pre_fix_arm_is_voided_on_read(tmp_path):
    """Even a hand-written, correctly self-hashed row for a pre-fix arm projects nothing."""
    runs = make_arm(tmp_path)
    sidecar = write(runs)
    row = json.loads(sidecar.read_text())
    row["extra"]["arm_started_at"] = "2026-09-05T10:00:00Z"
    row["extra"]["arm_ended_at"] = "2026-09-05T10:05:00Z"
    row["emitted_at"] = "2026-09-05T10:05:10Z"
    row["date"] = "2026-09-05"
    row["measurement_id"] = capture.measurement_identity(
        launch_id=LAUNCH["launch_id"], label=LABEL, arm_started_at="2026-09-05T10:00:00Z",
        metric=capture.METRIC, contention_verdict="CLEAN", rows_sha256=row["rows_sha256"])
    row["row_sha256"] = capture.row_digest(row)
    sidecar.write_text(json.dumps(row) + "\n")
    assert reader.native_rows(sidecar) == ()


def test_pre_hook_arm_without_sidecar_emits_zero_rows(tmp_path):
    """Rows + coresidency + timeline exist; the reader never reconstructs a verdict."""
    runs = make_arm(tmp_path, cores=SMT_CORES)
    assert reader.rows_for_run_dir(runs) == ()
    assert reader.frames_for_run_dir(runs, as_of="2026-09-16T12:00:00Z") == []


# --- nothing guessed ------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["launch_id", "model_path", "gguf_sha256", "kernel_commit",
                                 "binary_version", "launch_recipe", "pinning", "bench_cpus"])
def test_missing_launch_identity_is_refused(tmp_path, key):
    runs = make_arm(tmp_path)
    launch = dict(LAUNCH)
    del launch[key]
    with pytest.raises(capture.CaptureError):
        write(runs, launch=launch)


def test_between_launch_sd_needs_a_replicate_group(tmp_path):
    runs = make_arm(tmp_path)
    with pytest.raises(capture.CaptureError, match="between-launch"):
        write(runs, launch={**LAUNCH, "between_launch_sd": 0.12})
    ok = reader.project(reader.native_rows(write(
        runs, launch={**LAUNCH, "between_launch_sd": 0.12, "replicate_group": "B_NEW",
                      "replicate_launches": 5}))[0])
    assert ok.extra["between_launch_sd"] == 0.12 and ok.extra["replicate_launches"] == 5


def test_absent_sd_is_recorded_as_absent(tmp_path):
    tup = reader.project(reader.native_rows(write(make_arm(tmp_path)))[0])
    assert tup.extra["between_launch_sd"] is None
    assert tup.extra["between_launch_sd_basis"].startswith("absent")


# --- locator and sample accounting ----------------------------------------------------------

def test_locator_is_the_arm_and_reps_count_launches(tmp_path):
    tup = reader.project(reader.native_rows(write(make_arm(tmp_path)))[0])
    assert tup.attestation_locator == (
        f"inf70-serving-arm:{LAUNCH['launch_id']}:{LABEL}:{STARTED}:contention-CLEAN")
    assert "rows.jsonl" not in tup.attestation_locator
    assert tup.reps == 1 and tup.reps_basis.startswith("scored:launch")


def test_per_prompt_reps_are_refused_by_the_validator(tmp_path):
    sidecar = write(make_arm(tmp_path))
    row = json.loads(sidecar.read_text())
    row["reps"] = 4
    row["reps_basis"] = "scored:prompts"
    row["row_sha256"] = capture.row_digest(row)
    assert any("SC6-HAZARD" in p for p in capture.validate_row(row))


# --- tamper / decay -------------------------------------------------------------------------

def test_tampered_sidecar_is_inadmissible(tmp_path):
    sidecar = write(make_arm(tmp_path))
    row = json.loads(sidecar.read_text())
    row["value"] = 99.0
    sidecar.write_text(json.dumps(row) + "\n")
    assert reader.native_rows(sidecar) == ()


def test_verdict_flip_without_rehash_is_inadmissible(tmp_path):
    sidecar = write(make_arm(tmp_path, cores=SMT_CORES))
    row = json.loads(sidecar.read_text())
    row["extra"]["contention"]["contention_verdict"] = "CLEAN"
    row["row_sha256"] = capture.row_digest(row)
    sidecar.write_text(json.dumps(row) + "\n")
    assert reader.native_rows(sidecar) == ()


def test_mutated_rows_file_grades_down_not_away(tmp_path):
    runs = make_arm(tmp_path)
    sidecar = write(runs)
    with open(runs / f"{LABEL}.rows.jsonl", "a") as handle:
        handle.write(json.dumps(_prompt_row(9, 50, 100.0)) + "\n")
    natives = reader.native_rows(sidecar)
    assert len(natives) == 1
    q, t, _ = ct.grade(reader.project(natives[0]))
    assert (q, t) != ("Witnessed", "Attested")


def test_project_revalidates(tmp_path):
    with pytest.raises(ct.ProjectionError):
        reader.project({"row": {"schema": capture.CAPTURE_SCHEMA}})


# --- CLI ------------------------------------------------------------------------------------

def test_cli_writes_the_sidecar_and_refuses_cleanly(tmp_path, capsys):
    runs = make_arm(tmp_path)
    launch_json = tmp_path / "launch.json"
    launch_json.write_text(json.dumps(LAUNCH))
    rc = capture.main(["--run-dir", str(runs), "--label", LABEL, "--launch-json",
                       str(launch_json), "--arm-started-at", "2026-09-16T00:00:00Z"])
    assert rc == 0, capsys.readouterr().err
    assert capture.sidecar_path_for(runs, LABEL).is_file()
    rc = capture.main(["--run-dir", str(runs), "--label", LABEL, "--launch-json",
                       str(launch_json), "--arm-started-at", "2026-09-01T00:00:00Z"])
    assert rc == 2
    assert "refused" in capsys.readouterr().err


def test_cli_refuses_a_backfill_by_file_mtime(tmp_path):
    import time
    runs = make_arm(tmp_path)
    ended = time.time() - 9 * 3600  # rows last written 9 h ago: well past the lag window
    os.utime(runs / f"{LABEL}.rows.jsonl", (ended, ended))
    started = capture._utc_str(capture.datetime.fromtimestamp(ended - 600, capture.timezone.utc))
    launch_json = tmp_path / "launch.json"
    launch_json.write_text(json.dumps(LAUNCH))
    with pytest.raises(capture.CaptureError, match="backfill"):
        capture.write_arm_measurement(runs, LABEL, launch=LAUNCH, arm_started_at=started,
                                      producer="arm_hot.sh")
    rc = capture.main(["--run-dir", str(runs), "--label", LABEL, "--launch-json",
                       str(launch_json), "--arm-started-at", started])
    assert rc == 2


# --- carrier conformance --------------------------------------------------------------------

def test_projection_is_registered_under_the_shared_measurement_class():
    assert reader.SOURCE_KIND in ct.registered()
    assert ct.source_classes()[reader.SOURCE_KIND] == ct.MEASUREMENT_CLASS


def test_adapter_registers_no_ladder_of_its_own():
    for module in (reader, capture):
        source = Path(module.__file__).read_text()
        assert "register_ladder" not in source
    assert "Witnessed" not in Path(reader.__file__).read_text().split('"""', 2)[2]


def test_a_second_measurement_ladder_is_refused():
    with pytest.raises(ct.ProjectionError):
        ct.register_ladder("measurement", "tests/rogue.py")(lambda tup: ("T0", "T0", []))


def test_real_harness1_arms_are_pre_hook():
    """The 2026-09-07 HARNESS-1 arms have no sidecar: zero rows, never reconstructed."""
    runs = Path("/mnt/raid0/llm/tmp/inf70/agents/harness1/runs")
    if not runs.is_dir():
        pytest.skip("INF-70 scratch not visible on this host")
    assert reader.rows_for_run_dir(runs) == ()

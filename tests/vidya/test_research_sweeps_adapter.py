"""SC49 — the research-intake compute-gated sweep adapter (G1–G4).

What is pinned here, in the order this program has been burned:

* the **G1 seven-field contract** — a trial row carries EXACTLY the seven SC49
  fields; anything extra or missing is malformed, so a row omitting
  ``prompt_class`` is refused (the "refuse a projection that omits it" rule);
* the **caveats ride IN the tuple** — every G1 claim states the correctness-
  observation clause verbatim, and the pangram (negative-control) arm adds the
  negative-control clause verbatim; the tuple carries ``prompt_class``;
* the **G2 n_max rule** — acceptance is not comparable across
  ``--spec-draft-n-max`` values, so a G2 row lacking ``n_max`` is refused and
  every G2 tuple carries n_max and the mean accepted length together;
* **direction is recorded, never invented** — G1's metric is the producer's own
  gate quantity (eos-first), G3's kernel selection is a nominal label stated as
  such in the claim; ``metric_direction=None`` is impossible in the shared
  ClaimTuple, so the house precedent is matched instead;
* **attestation honesty** — the manifest is the attestation the adapter sha256s;
  in a git tree pinned at the recorded ``research_commit`` the run is
  pin-verifiable (``Witnessed/Attested``), otherwise ``Witnessed/Anchored``;
  a recomputed hash that disagrees with the recorded one is tampering: the whole
  run is refused (fail closed);
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
from adapters import research_sweeps as rs  # noqa: E402

BINARY = "/mnt/raid0/llm/llama.cpp/build/bin/llama-completion"
BINARY_SHA = hashlib.sha256(b"frozen v9 llama-completion").hexdigest()
MODEL = "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"
MODEL_SHA = hashlib.sha256(b"frontdoor q8_0").hexdigest()
RESEARCH_COMMIT = "da06b3711157bf47a9d934d4b3482eef152a1a09"
LAUNCH = {
    "binary": "llama-completion",
    "n_predict": 1,
    "temp": 0,
    "seed": 27442,
    "cache_prompt": False,
    "n_parallel": 1,
    "conversation_mode": False,
    "ctx_size": 32768,
    "kv_type_k": "q8_0",
    "kv_type_v": "q8_0",
    "special": True,
    "display_prompt": False,
    "verbose_prompt": True,
    "escape": False,
    "threads": None,
}


def g1_row(**overrides) -> dict:
    row = {
        "prompt_length_target": 15401,
        "prompt_length_actual": 15400,
        "prompt_class": "pangram",
        "first_sampled_token_id": 151643,
        "stop_reason": "eog",
        "seed": 27442,
        "trial_ts_utc": "2026-08-27T12:00:00Z",
    }
    row.update(overrides)
    return row


def write_trials(run_dir: Path, *rows: dict) -> Path:
    path = run_dir / "trials.jsonl"
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def write_run(run_dir: Path, *rows: dict, **manifest_overrides) -> Path:
    """A complete G1 run directory: trials + self-hashed manifest (out-of-tree)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    trials = write_trials(run_dir, *rows)
    manifest = rs.build_run_manifest(
        run_dir,
        trials_sha256=hashlib.sha256(trials.read_bytes()).hexdigest(),
        binary_path=BINARY, binary_sha256=BINARY_SHA,
        model_path=MODEL, model_sha256=MODEL_SHA,
        research_commit=RESEARCH_COMMIT, launch=LAUNCH,
        date="20260827T1200Z",
    )
    if manifest_overrides:
        data = json.loads(manifest.read_text())
        data.update(manifest_overrides)
        manifest.write_text(json.dumps(data, sort_keys=True))
    return manifest


# ── the G1 contract: projection + caveats -----------------------------------

def test_g1_pangram_row_carries_the_negative_control_caveat(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())  # pangram arm, eog first token
    natives = rs.native_rows(run_dir)
    assert len(natives) == 1, "one trial row = one claim"
    tup = rs.project_g1(natives[0])

    assert tup.metric == "first_sampled_token_is_eog" and tup.value is True
    assert tup.protocol_id == rs.G1_PROTOCOL_ID
    assert tup.extra["prompt_class"] == "pangram"
    assert rs.CORRECTNESS_CAVEAT in tup.claim
    assert rs.NEGATIVE_CONTROL_CAVEAT in tup.claim, \
        "the negative-control clause must ride IN the tuple, verbatim"
    assert tup.extra["negative_control_caveat"] == rs.NEGATIVE_CONTROL_CAVEAT
    assert tup.extra["first_sampled_token_id"] == 151643
    assert tup.extra["stop_reason"] == "eog"
    assert tup.extra["prompt_length_target"] == 15401
    assert tup.extra["prompt_length_actual"] == 15400
    assert tup.reps == 1 and tup.reps_basis.startswith("trials")

    # out-of-tree fixture: the honest grade is anchored, not attested
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_g1_meaningful_row_carries_the_correctness_caveat_but_no_control_clause(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row(
        prompt_class="meaningful", stop_reason="completed",
        first_sampled_token_id=99023))
    tup = rs.project_g1(rs.native_rows(run_dir)[0])
    assert rs.CORRECTNESS_CAVEAT in tup.claim
    assert rs.NEGATIVE_CONTROL_CAVEAT not in tup.claim
    assert tup.value is False, "completed (non-eog) first token -> not eog-first"
    assert tup.extra["prompt_class"] == "meaningful"


def test_g1_row_omitting_prompt_class_is_refused(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    row = g1_row()
    del row["prompt_class"]
    write_run(run_dir, row)
    assert rs.native_rows(run_dir) == ()
    reason = rs.refusal_reason(run_dir)
    assert reason.startswith("malformed"), reason
    assert "prompt_class" in reason


def test_g1_row_with_non_contract_fields_is_refused(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row(extra_field="nope"))
    assert rs.native_rows(run_dir) == ()
    assert "non-contract fields" in rs.refusal_reason(run_dir)


def test_g1_null_first_token_id_is_recorded_honestly(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row(first_sampled_token_id=None))
    tup = rs.project_g1(rs.native_rows(run_dir)[0])
    assert tup.extra["first_sampled_token_id"] is None
    assert "null (extraction failed)" in tup.claim


# ── attestation: honest levels + fail-closed tamper --------------------------

def test_attested_when_run_sits_in_a_tree_pinned_at_the_recorded_commit(
        tmp_path, monkeypatch):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())
    monkeypatch.setattr(rs, "_git_head", lambda directory: RESEARCH_COMMIT)
    tup = rs.project_g1(rs.native_rows(run_dir)[0])
    assert tup.extra["git_pinned"] is True
    assert tup.attestation_sha256
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested"), reasons
    assert reasons == []


def test_anchored_when_the_tree_moved_off_its_pin(tmp_path, monkeypatch):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())
    monkeypatch.setattr(rs, "_git_head", lambda directory: "0" * 40)
    tup = rs.project_g1(rs.native_rows(run_dir)[0])
    assert tup.extra["git_pinned"] is False, "off-pin tree = re-derivable, not pinned"
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_tampered_manifest_fails_closed(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())
    assert len(rs.native_rows(run_dir)) == 1
    manifest = run_dir / "run_manifest.json"
    data = json.loads(manifest.read_text())
    data["model_path"] = "/mnt/raid0/llm/models/SOME_OTHER_MODEL.gguf"  # tamper
    manifest.write_text(json.dumps(data, sort_keys=True))
    assert rs.native_rows(run_dir) == ()
    reason = rs.refusal_reason(run_dir)
    assert reason.startswith("tampered"), reason
    assert "manifest_sha256" in reason


def test_tampered_trials_fails_closed(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())
    with open(run_dir / "trials.jsonl", "a") as f:  # one extra byte = corruption
        f.write("\n")
    assert rs.native_rows(run_dir) == ()
    reason = rs.refusal_reason(run_dir)
    assert reason.startswith("tampered"), reason
    assert "trials_sha256" in reason


def test_missing_manifest_is_no_emissions_not_corruption(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    run_dir.mkdir()
    write_trials(run_dir, g1_row())  # trials without the manifest = incomplete run
    assert rs.native_rows(run_dir) == ()
    assert rs.refusal_reason(run_dir) == "no emissions"


def test_absent_run_dir_is_no_emissions(tmp_path):
    missing = tmp_path / "g1-27442-20260827T1200Z"
    assert rs.native_rows(missing) == ()
    assert rs.refusal_reason(missing) == "no emissions"
    assert rs.frames_for_run_dir(missing, as_of="2026-08-27T13:00:00Z") == []


# ── G2: the n_max rule --------------------------------------------------------

def _g2_row(**overrides) -> dict:
    row = {
        "schema": rs.G2_SCHEMA,
        "run_id": "df2-5-grid-20260827T1200Z",
        "slot_index": 0,
        "drafter_arm": "df2",
        "n_max": 16,
        "kv_unified": True,
        "accepted": True,
        "mean_accepted_length": 4.25,
        "trial_ts_utc": "2026-08-27T12:00:00Z",
    }
    row.update(overrides)
    return row


def write_sweep_file(tmp_path: Path, *rows: dict, name="sweep.jsonl") -> Path:
    path = tmp_path / name
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def test_g2_row_without_n_max_is_refused(tmp_path):
    row = _g2_row()
    del row["n_max"]
    path = write_sweep_file(tmp_path, row)
    assert rs.native_rows_file(path) == ()
    reason = rs.refusal_reason_file(path)
    assert reason.startswith("malformed"), reason
    assert "n_max" in reason and "REQUIRED" in reason


def test_g2_row_projects_with_caveat_n_max_and_mean_together(tmp_path):
    path = write_sweep_file(tmp_path, _g2_row())
    tup = rs.project_g2(rs.native_rows_file(path)[0])
    assert tup.metric == "mean_accepted_length" and tup.value == pytest.approx(4.25)
    assert tup.category == "CANDIDATE", "df2 drafter arm is the arm under test"
    assert rs.G2_CAVEAT in tup.claim
    assert "--spec-draft-n-max=16" in tup.claim
    assert tup.extra["n_max"] == 16
    assert tup.extra["kv_unified"] is True
    assert tup.extra["accepted"] is True
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons  # locator only, no manifest yet


def test_g2_baseline_drafter_arm_is_baseline(tmp_path):
    path = write_sweep_file(tmp_path, _g2_row(drafter_arm="baseline", accepted=False,
                                              mean_accepted_length=0.0))
    tup = rs.project_g2(rs.native_rows_file(path)[0])
    assert tup.category == "BASELINE"


def test_g2_rejects_bad_shape_and_malformed(tmp_path):
    path = write_sweep_file(tmp_path, _g2_row(mean_accepted_length=-1.0))
    assert rs.native_rows_file(path) == ()
    assert "mean_accepted_length must be >= 0" in rs.refusal_reason_file(path)
    path2 = write_sweep_file(tmp_path, {"not": "a row"})
    assert rs.native_rows_file(path2) == ()
    assert "schema must be one of" in rs.refusal_reason_file(path2)


# ── G3 / G4: categorical + fractional projections ----------------------------

def test_g3_kernel_selection_is_categorical_with_nominal_direction(tmp_path):
    path = write_sweep_file(tmp_path, {
        "schema": rs.G3_SCHEMA,
        "run_id": "miqk-probe-20260827T1200Z",
        "draft_max": 64,
        "selected_fa_kernel": "fa_q8_256",
        "trial_ts_utc": "2026-08-27T12:00:00Z",
    })
    tup = rs.project_g3(rs.native_rows_file(path)[0])
    assert tup.metric == "selected_fa_kernel"
    assert tup.value == "fa_q8_256"
    assert "nominal" in tup.claim, \
        "a kernel name has no polarity; the claim must say the label is nominal"
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_g4_reuse_fraction_projects_per_migration(tmp_path):
    path = write_sweep_file(tmp_path, {
        "schema": rs.G4_SCHEMA,
        "run_id": "restore-reuse-20260827T1200Z",
        "migration_id": "mig-20260827-01",
        "reuse_fraction": 0.97,
        "trial_ts_utc": "2026-08-27T12:00:00Z",
    })
    tup = rs.project_g4(rs.native_rows_file(path)[0])
    assert tup.metric == "prompt_reuse_fraction"
    assert tup.value == pytest.approx(0.97)
    assert tup.extra["migration_id"] == "mig-20260827-01"
    assert "reuse" in tup.claim and "higher is better" in tup.claim

    bad = write_sweep_file(tmp_path, {
        "schema": rs.G4_SCHEMA, "run_id": "x", "migration_id": "m",
        "reuse_fraction": 1.5, "trial_ts_utc": "2026-08-27T12:00:00Z",
    }, name="bad4.jsonl")
    assert rs.native_rows_file(bad) == ()
    assert "lie in [0, 1]" in rs.refusal_reason_file(bad)


# ── strictness: bypass + identity + carrier -----------------------------------

def test_project_rejects_bypass_and_mutation(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())
    native = rs.native_rows(run_dir)[0]
    mutated = {**native, "row": {**native["row"], "prompt_class": "filler"}}
    with pytest.raises(ct.ProjectionError):
        rs.project_g1(mutated)
    with pytest.raises(ct.ProjectionError):
        rs.project_g1({"row": native["row"]})  # bypassing native_rows (no manifest)
    with pytest.raises(ct.ProjectionError):
        rs.project_g1(native["row"])  # passing the raw row


def test_g1_identity_is_unique_per_trial_and_stable(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir,
              g1_row(),
              g1_row(prompt_length_target=16501, first_sampled_token_id=99123,
                     trial_ts_utc="2026-08-27T12:05:00Z"))
    ids = [rs.project_g1(n).measurement_id for n in rs.native_rows(run_dir)]
    assert len(ids) == len(set(ids)), "distinct trials must not merge into one claim"
    again = [rs.project_g1(n).measurement_id for n in rs.native_rows(run_dir)]
    assert ids == again, "the same run dir must re-derive the same identities"


def test_projections_registered_under_the_shared_registry():
    for kind in (rs.G1_SOURCE_KIND, rs.G2_SOURCE_KIND, rs.G3_SOURCE_KIND,
                 rs.G4_SOURCE_KIND):
        assert kind in ct.registered(), f"{kind} must be registered"


def test_frames_go_through_the_shared_emitter(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    write_run(run_dir, g1_row())
    frames = rs.frames_for_run_dir(run_dir, as_of="2026-08-27T13:00:00Z")
    assert len(frames) == 3  # source, claim, support
    support = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert support["assertion"]["grade"] == {"Q": "Witnessed", "T": "Anchored"}
    assert support["assertion"]["protocol_id"] == rs.G1_PROTOCOL_ID
    assert support["assertion"]["reps"] == 1
    assert support["assertion"]["category"] == "BASELINE"
    claim = next(f for f in frames if f["frame_type"].endswith("claim_proposed/v1"))
    assert rs.NEGATIVE_CONTROL_CAVEAT in claim["assertion"]["display_text"]


def test_g2_g3_g4_frames_through_the_shared_emitter(tmp_path):
    path = write_sweep_file(tmp_path, _g2_row(), {
        "schema": rs.G3_SCHEMA, "run_id": "r", "draft_max": 16,
        "selected_fa_kernel": "fa_x", "trial_ts_utc": "2026-08-27T12:00:00Z",
    }, {
        "schema": rs.G4_SCHEMA, "run_id": "r", "migration_id": "m",
        "reuse_fraction": 0.5, "trial_ts_utc": "2026-08-27T12:00:00Z",
    })
    frames = rs.frames_for_sweep_file(path, as_of="2026-08-27T13:00:00Z")
    assert len(frames) == 9  # 3 rows x (source, claim, support)


def test_manifest_builder_refuses_a_protocol_it_did_not_run(tmp_path):
    run_dir = tmp_path / "g1-27442-20260827T1200Z"
    run_dir.mkdir()
    write_trials(run_dir, g1_row())
    with pytest.raises(rs.CaptureError, match="n_predict"):
        rs.build_run_manifest(run_dir, trials_sha256="0" * 64,
                              binary_path=BINARY, binary_sha256=BINARY_SHA,
                              model_path=MODEL, model_sha256=MODEL_SHA,
                              research_commit=RESEARCH_COMMIT,
                              launch={**LAUNCH, "n_predict": 128})
    with pytest.raises(rs.CaptureError, match="64-hex"):
        rs.build_run_manifest(run_dir, trials_sha256="zz",
                              binary_path=BINARY, binary_sha256=BINARY_SHA,
                              model_path=MODEL, model_sha256=MODEL_SHA,
                              research_commit=RESEARCH_COMMIT, launch=LAUNCH)

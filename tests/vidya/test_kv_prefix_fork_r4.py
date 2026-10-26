"""R4 native record projection; mutations below are SYNTHETIC contract controls."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import kv_prefix_fork as kpf
import claim_tuple as ct

FX = Path(__file__).parent / "fixtures/kpf18_s1_r4"
SHA = "4f26b3cf40b196245f99c0397e1c8b920abe436f9480e8478997986e3f01829b"


def native():
    return json.loads((FX / "belief_measurements.jsonl").read_text())


def synthetic(tmp_path, change):
    row = copy.deepcopy(native())
    change(row)
    # A synthetic fixture seal, never a historical record repair.
    row["record_sha256"] = kpf._digest({k: v for k, v in row.items() if k != "record_sha256"})
    sidecar = tmp_path / "belief_measurements.jsonl"
    sidecar.write_text(json.dumps(row) + "\n")
    return row, sidecar


def test_original_bytes_seal_rows_and_scope(tmp_path):
    shutil.copytree(FX, tmp_path / "run")
    sc = tmp_path / "run/belief_measurements.jsonl"
    assert hashlib.sha256(sc.read_bytes()).hexdigest() == SHA
    row = native()
    assert kpf.validate_row(row) == []
    natives = kpf.native_rows(sc)
    assert len(natives) == 1 and natives[0]["attestation_present"] is True
    tup = kpf.project(natives[0])
    assert tup.metric == "kpf18_r4_child_vs_coldE_mean_abs_dlogprob"
    assert tup.value == row["r4"]["result"]["d_child_vs_coldE"]
    assert tup.observation["anchor_value"] == row["r4"]["result"]["floor_used"]
    assert tup.observation["outcome_native"] == "FORK_PATH_SPECIFIC"
    assert tup.metric_direction == "lower_better" and tup.reps == 256
    assert "one fresh load" in tup.reps_basis and "NOT independent runs" in tup.reps_basis
    assert tup.protocol_id == "" and ct.grade(tup)[:2] == ("Judged", "Located")
    assert tup.extra["r4"] == row["r4"]
    assert tup.extra["binary_sha256"] == row["binary_sha256"]
    assert tup.extra["argv"] == row["argv"]
    assert "item=187:step=r4" in tup.attestation_locator
    assert hashlib.sha256(sc.read_bytes()).hexdigest() == SHA
    assert kpf.to_frames(tup, as_of="2026-10-26T00:00:00Z", adapter_id=kpf.ADAPTER_ID)


@pytest.mark.parametrize("change", [
    lambda r: r.update(kpf18_item=188),
    lambda r: r.update(arm="r4_other", kpf18_arm="r4_other"),
    lambda r: r.update(kpf18_arm="wrong"),
    lambda r: r.pop("r4"),
    lambda r: r["r4"].update(step_id="long6"),
    lambda r: r["r4"].update(step="other"),
    lambda r: r["r4"].pop("predeclaration_sha256"),
    lambda r: r["r4"].update(step_complete=1),
    lambda r: r["r4"].pop("result"),
])
def test_wrong_locator_or_envelope_refused(tmp_path, change):
    row, sc = synthetic(tmp_path, change)
    assert kpf.validate_row(row)
    assert kpf.native_rows(sc) == ()


@pytest.mark.parametrize("change", [
    lambda r: r["r4"].update(step_complete=False),
    lambda r: r["r4"].update(fresh_load=False),
    lambda r: r["r4"]["result"].update(n_common_valid=15),
    lambda r: r["r4"]["result"].update(n_common_valid=True),
    lambda r: r["r4"]["result"].update(prompt_ge_50k=False),
    lambda r: r["r4"]["result"]["arm_valid"].update(coldE=False),
    lambda r: r["r4"]["result"].update(verdict="ABSTAIN"),
    lambda r: r["r4"]["result"].update(verdict="INVALID"),
    lambda r: r["r4"]["result"].update(d_child_vs_coldE=-1),
    lambda r: r["r4"]["result"].update(d_child_vs_coldE=float("nan")),
    lambda r: r["r4"]["result"].update(floor_used=0),
])
def test_unscored_attempt_is_separate_higher_better_metric(tmp_path, change):
    row, sc = synthetic(tmp_path, change)
    assert kpf.validate_row(row) == []
    tup = kpf.project(kpf.native_rows(sc)[0])
    assert tup.metric == "kpf18_r4_steps_scored" and tup.value == 0
    assert tup.metric_direction == "higher_better" and tup.reps == 1
    assert json.dumps(tup.extra["r4"], sort_keys=True) == json.dumps(row["r4"], sort_keys=True)


def test_zero_weight_childx_does_not_veto_five_judged_arms(tmp_path):
    row, sc = synthetic(tmp_path, lambda r: r["r4"]["result"]["arm_valid"].update(childX=False))
    tup = kpf.project(kpf.native_rows(sc)[0])
    assert tup.metric == "kpf18_r4_child_vs_coldE_mean_abs_dlogprob"
    assert tup.extra["r4"]["result"]["factorial_reading"] == row["r4"]["result"]["factorial_reading"]


def test_seal_tamper_and_duplicates_stay_refused(tmp_path):
    row = native()
    row["r4"]["result"]["d_child_vs_coldE"] = 0
    assert "record_sha256 does not re-derive" in kpf.validate_row(row)
    sc = tmp_path / "belief_measurements.jsonl"
    original = (FX / "belief_measurements.jsonl").read_bytes()
    sc.write_bytes(original + original)
    assert kpf.native_rows(sc) == ()


def test_rows_tamper_is_unattested_not_silently_verified(tmp_path):
    shutil.copytree(FX, tmp_path / "run")
    sc = tmp_path / "run/belief_measurements.jsonl"
    row = native()
    (sc.parent / "rows" / Path(row["rows"]).name).write_text("tampered\n")
    tup = kpf.project(kpf.native_rows(sc)[0])
    assert tup.attestation_present is False and tup.attestation_verified is None
    assert tup.metric == "kpf18_r4_child_vs_coldE_mean_abs_dlogprob"

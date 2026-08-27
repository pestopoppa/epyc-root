"""SC20 memento LoRA strict-reader tests: projection, refusal semantics, attestation."""

import json
import shutil
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from adapters import memento_lora  # noqa: E402
from claim_tuple import ProjectionError, registered  # noqa: E402

REAL_BELIEF = Path(__file__).resolve().parents[2] / ".." / ".." / "mnt" / "raid0" / "llm" / \
    "epyc-inference-research" / "output" / "memento" / "memento-s1-lora" / \
    "stage1_belief_measurements.json"
# The real belief file lives outside the repo; the fixture is a committed copy.
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "memento_stage1_belief.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _write_belief(tmp_path: Path, row: dict, metrics: bytes) -> Path:
    (tmp_path / "stage1_metrics.json").write_bytes(metrics)
    # Mirror the producer: attestation fields nested in extra, then self-hash.
    row["extra"]["attestation_path"] = str(tmp_path / "stage1_metrics.json")
    row["extra"]["attestation_locator"] = "stage1_metrics.json"
    row["extra"]["attestation_sha256"] = memento_lora._content_hash(json.loads(metrics))
    row.pop("measurement_sha256", None)
    row["measurement_sha256"] = memento_lora._content_hash(row)
    belief = tmp_path / "stage1_belief_measurements.json"
    belief.write_text(json.dumps(row))
    return belief


@pytest.fixture(scope="module", autouse=True)
def _fixture_from_real_file():
    if REAL_BELIEF.exists() and not FIXTURE.exists():
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REAL_BELIEF, FIXTURE)
        metrics = REAL_BELIEF.parent / "stage1_metrics.json"
        (FIXTURE.parent / "stage1_metrics.json").write_bytes(metrics.read_bytes())
    yield


def test_real_belief_row_projects(tmp_path):
    row = _load_fixture()
    metrics = (FIXTURE.parent / "stage1_metrics.json").read_bytes()
    belief = _write_belief(tmp_path, row, metrics)
    assert memento_lora.refusal_reason(belief) is None
    t = memento_lora.project(memento_lora.native_rows(belief)[0])
    assert t.metric == "sft_seconds_per_sample"
    assert t.metric_direction == "lower_better"
    assert t.category == "BASELINE"
    assert t.protocol_id == "epyc.memento_sft.lora_training.v1"
    assert t.reps == 126
    assert "provably updated" in t.claim
    assert "never a claim about model quality" in (t.extra or {}).get("scope", "")
    assert t.attestation_present is True


def test_refusal_artifact_zero_lora_b_projects_zero_rows(tmp_path):
    row = _load_fixture()
    row["extra"]["adapter_integrity"]["lora_B_nonzero"] = 0
    metrics = (FIXTURE.parent / "stage1_metrics.json").read_bytes()
    belief = _write_belief(tmp_path, row, metrics)
    assert "did not provably update" in memento_lora.refusal_reason(belief)
    with pytest.raises(ProjectionError):
        memento_lora.native_rows(belief)


def test_tampered_run_record_fails_closed(tmp_path):
    row = _load_fixture()
    metrics = (FIXTURE.parent / "stage1_metrics.json").read_bytes()
    belief = _write_belief(tmp_path, row, metrics)
    # Content tamper that still parses: the canonical hash must move.
    rec = json.loads(metrics)
    rec["samples_seen"] = rec["samples_seen"] + 1
    (tmp_path / "stage1_metrics.json").write_text(json.dumps(rec, indent=2))
    assert "attestation mismatch" in memento_lora.refusal_reason(belief)


def test_protocol_mismatch_refused(tmp_path):
    row = _load_fixture()
    row["protocol_id"] = "epyc.something_else.v1"
    metrics = (FIXTURE.parent / "stage1_metrics.json").read_bytes()
    belief = _write_belief(tmp_path, row, metrics)
    assert "protocol mismatch" in memento_lora.refusal_reason(belief)


def test_scope_clause_enforced(tmp_path):
    row = _load_fixture()
    row["claim"] = "this configuration trains fast"
    metrics = (FIXTURE.parent / "stage1_metrics.json").read_bytes()
    belief = _write_belief(tmp_path, row, metrics)
    assert "scope clause" in memento_lora.refusal_reason(belief)


def test_registered_on_the_shared_measurement_ladder():
    assert "memento-lora-training" in registered()


def test_frames_emission_round_trip(tmp_path):
    row = _load_fixture()
    metrics = (FIXTURE.parent / "stage1_metrics.json").read_bytes()
    belief = _write_belief(tmp_path, row, metrics)
    frames = memento_lora.frames_for_records(belief, as_of="2026-08-27T20:10:00Z")
    assert len(frames) >= 2  # claim + support
    assert all(f["provenance"]["method"] == "vidya.adapters.memento_lora" for f in frames)

"""KPF-26 API observations retain their own native response and unknown flags."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
from adapters import kv_prefix_fork as adapter  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402


def native(tmp_path):
    response = tmp_path / "response.bin"
    response.write_text(json.dumps({"scouts": {"schema": "epyc.orchestrator.scouts.v1", "role": "r", "url": "http://server",
        "requested": 2, "launched": 2, "completed": 2, "scouts": [{"status": "ok"}, {"status": "ok"}]}}))
    row = {"schema": "epyc.kpf26.api-observation.v1", "run_id": "grant", "window_id": "window",
           "host": "host", "api_url": "http://127.0.0.1:8000", "role": "r", "server_url": "http://server", "start_utc": "2026-11-02T10:00:00Z",
           "end_utc": "2026-11-02T10:01:00Z", "binary_sha256": "a" * 64, "model_sha256": "b" * 64,
           "prompt_set_sha256": "c" * 64, "request_sha256": "d" * 64, "grant_sha256": "e" * 64,
           "argv": ["/server"], "http_status": 200, "flags": "unverified", "category": "CANDIDATE",
           "rows": str(response), "rows_sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
           "kpf26": {"tasks": 1, "children": 2, "completed": 2}}
    row["record_sha256"] = adapter._digest(row)
    return row


def test_route_observation_projects_own_response_not_inferred_arm(tmp_path):
    row = native(tmp_path)
    sidecar = tmp_path / "belief_measurements.jsonl"
    sidecar.write_text(json.dumps(row) + "\n")
    rows = adapter.native_rows(sidecar)
    assert len(rows) == 1
    claim = adapter.project(rows[0])
    assert claim.metric == "kpf26_api_completed_scouts" and claim.value == 2
    assert claim.reps == 2 and claim.attestation_present
    assert "flags unverified" in claim.claim and "gate verdict" in claim.claim
    assert claim.extra["flags"] == "unverified"


def test_resealed_false_counts_and_invented_arm_are_rejected(tmp_path):
    row = native(tmp_path)
    row["kpf26"]["completed"] = 1
    row["record_sha256"] = adapter._digest({k: v for k, v in row.items() if k != "record_sha256"})
    with pytest.raises(ProjectionError, match="disagree"):
        adapter.project({"row": row, "sidecar_path": str(tmp_path / "belief_measurements.jsonl")})
    row = native(tmp_path)
    row["arm"] = "fork_off"
    row["record_sha256"] = adapter._digest({k: v for k, v in row.items() if k != "record_sha256"})
    assert adapter.validate_row(row) == ["invalid API observation scope"]


def test_changed_response_is_attested_absent(tmp_path):
    row = native(tmp_path)
    Path(row["rows"]).write_text("{}")
    claim = adapter.project({"row": row, "sidecar_path": str(tmp_path / "belief_measurements.jsonl")})
    assert claim.attestation_present is False


def test_optional_scout_trace_has_independent_attestation(tmp_path):
    row = native(tmp_path)
    trace = tmp_path / "scout-trace.json"
    trace.write_bytes(b'{"native":true}\n')
    row["scout_trace"] = {"path": str(trace), "sha256": hashlib.sha256(trace.read_bytes()).hexdigest()}
    row["record_sha256"] = adapter._digest({k: v for k, v in row.items() if k != "record_sha256"})
    claim = adapter.project({"row": row, "sidecar_path": str(tmp_path / "belief_measurements.jsonl")})
    assert claim.extra["scout_trace_present"] is True
    trace.write_bytes(b'{}')
    claim = adapter.project({"row": row, "sidecar_path": str(tmp_path / "belief_measurements.jsonl")})
    assert claim.attestation_present is True and claim.extra["scout_trace_present"] is False

"""Synthetic controls for strict, prospective ODL Unlimited-OCR run records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from claim_tuple import grade  # noqa: E402
from scripts.vidya.adapters import odl_model_gated  # noqa: E402


def _write(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def _record(root: Path) -> Path:
    run = root / "run"
    gt = {"path": "/synthetic/corpus/gt.json", "bytes": 2,
          "sha256": hashlib.sha256(b"[]").hexdigest(), "parsed_from_hashed_bytes": True}
    inputs = {"schema": "epyc.odl_bench.model_gated_inputs/v1", "ground_truth": gt,
              "images": [{"gt_image": "p1.png", "path": "/synthetic/p1.png",
                          "status": "read", "bytes": 3,
                          "sha256": hashlib.sha256(b"png").hexdigest()}],
              "image_bytes_sent_to_query": True, "started_utc": "2026-09-01T00:00:00Z"}
    response_dir = run / "responses" / "unlimited_ocr"
    input_manifest = _write(response_dir / "producer_input_manifest.json",
                             json.dumps(inputs, sort_keys=True).encode())
    window = {"schema": "epyc.autokernel.inference_call_window.v1",
              "released": True, "lock_path": "/synthetic/lock"}
    window_path = response_dir / "inference_window.json"
    window_file = _write(window_path, json.dumps(window).encode())
    prediction = _write(run / "predictions" / "p1.md", b"synthetic output")
    response = _write(response_dir / "p1.response.json", b'{"synthetic":true}')
    row_set_data = {"metric_rows": [{"engine": "unlimited_ocr", "metric_family": "speed",
                                     "metric_name": "latency_ms_median", "value": 12.5,
                                     "n": 1, "detail": "synthetic"}],
                    "run_manifests": [{"engine": "unlimited_ocr",
                                       "artifacts": [{"latency_ms": 12.5}]}]}
    row_set = _write(run / "model_gated_row_set.json",
                     json.dumps(row_set_data, sort_keys=True).encode())
    # The inputs are copied in the native record from the bytes actually parsed and sent.
    payload = {
        "schema": odl_model_gated.SCHEMA,
        "record_id": "9db1e7f5-1292-4a5a-8f71-bf0ea86563e1",
        "created_at": "2026-09-01T00:01:00Z",
        "protocol_id": odl_model_gated.PROTOCOL,
        "category": "CANDIDATE",
        "source": {"repository": "epyc-inference-research", "commit": "a" * 40,
                   "working_tree_clean": True, "checked_after_commit": "a" * 40,
                   "checked_after_clean": True},
        "producer": {"engine": "unlimited_ocr", "entrypoint": "scripts/benchmark/odl_bench/adapter.py run-model",
                     "prompt_profile": "synthetic", "prompt_sha256": "b" * 64,
                     "prompt_source_sha256": None, "binary_path": "/unknown/bin",
                     "binary_sha256": None, "model_path": "/unknown/model", "model_sha256": None,
                     "mmproj_path": "/unknown/mmproj", "mmproj_sha256": None,
                     "context": 8192, "threads": 24, "parallel": 1, "device": "unknown",
                     "gpu_layers": 99, "max_tokens": 100},
        "inputs": inputs,
        "measurement": {"metric": "latency_ms_median", "value": 12.5, "unit": "ms/page",
                        "direction": "lower_better", "reps": 1,
                        "reps_basis": "one positive synthetic page attempt", "claim": "synthetic fixture latency"},
        "run_metrics": [{"metric_family": "speed", "metric_name": "latency_ms_median",
                          "value": 12.5, "n": 1, "detail": "synthetic"}],
        "locator": {"run_dir": str(run), "row_set": str(run / "model_gated_row_set.json"),
                    "input_manifest": str(response_dir / "producer_input_manifest.json"),
                    "inference_window": str(window_path)},
        "outputs": {"predictions": [prediction],
                    "responses": [input_manifest, window_file, response],
                    "row_set": row_set},
    }
    payload_bytes = odl_model_gated._canonical(payload)
    envelope = {"payload_sha256": hashlib.sha256(payload_bytes).hexdigest(), "payload": payload}
    record = run / "vidya_measurement_record.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_bytes(odl_model_gated._canonical(envelope) + b"\n")
    return record


def test_prospective_record_projects_one_shared_measurement_tuple(tmp_path: Path) -> None:
    record = _record(tmp_path)
    rows = odl_model_gated.native_rows(record)
    assert len(rows) == 1
    projected = odl_model_gated.project_unlimited_ocr_run(rows[0])
    assert projected.metric == "latency_ms_median"
    assert projected.value == 12.5 and projected.reps == 1
    assert projected.attestation_verified is True
    assert grade(projected)[0] != "Refused"


def test_changed_output_bytes_refuse_projection(tmp_path: Path) -> None:
    record = _record(tmp_path)
    output = record.parent / "predictions" / "p1.md"
    output.write_bytes(b"changed after record creation")
    with pytest.raises(odl_model_gated.ProjectionError):
        odl_model_gated.native_rows(record)


@pytest.mark.parametrize("gpu_layers", [0, -1])
def test_producer_supported_gpu_layer_sentinels_are_preserved(tmp_path: Path,
                                                               gpu_layers: int) -> None:
    record = _record(tmp_path)
    envelope = json.loads(record.read_bytes())
    envelope["payload"]["producer"]["gpu_layers"] = gpu_layers
    envelope["payload_sha256"] = hashlib.sha256(
        odl_model_gated._canonical(envelope["payload"])).hexdigest()
    record.write_bytes(odl_model_gated._canonical(envelope) + b"\n")
    assert odl_model_gated.native_rows(record)[0]["payload"]["producer"]["gpu_layers"] == gpu_layers


def test_gpu_layer_values_below_producer_sentinel_refuse_projection(tmp_path: Path) -> None:
    record = _record(tmp_path)
    envelope = json.loads(record.read_bytes())
    envelope["payload"]["producer"]["gpu_layers"] = -2
    envelope["payload_sha256"] = hashlib.sha256(
        odl_model_gated._canonical(envelope["payload"])).hexdigest()
    record.write_bytes(odl_model_gated._canonical(envelope) + b"\n")
    with pytest.raises(odl_model_gated.ProjectionError, match="gpu_layers"):
        odl_model_gated.native_rows(record)


def test_output_path_traversal_refuses_projection(tmp_path: Path) -> None:
    record = _record(tmp_path)
    outside = tmp_path / "outside.md"
    data = b"synthetic outside artifact"
    outside.write_bytes(data)
    envelope = json.loads(record.read_bytes())
    payload = envelope["payload"]
    payload["outputs"]["predictions"][0] = {
        "path": str(record.parent / ".." / outside.name),
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
    }
    envelope["payload_sha256"] = hashlib.sha256(odl_model_gated._canonical(payload)).hexdigest()
    record.write_bytes(odl_model_gated._canonical(envelope) + b"\n")
    with pytest.raises(odl_model_gated.ProjectionError, match="normalized"):
        odl_model_gated.native_rows(record)


def test_identity_free_legacy_run_has_no_tuple_and_is_not_retrofitted(tmp_path: Path) -> None:
    legacy = tmp_path / "old-demo" / "model_gated_row_set.json"
    legacy.parent.mkdir()
    legacy.write_text('{"engine":"unlimited_ocr","metric_rows":[]}', encoding="utf-8")
    assert odl_model_gated.native_rows(legacy.parent / "vidya_measurement_record.json") == ()

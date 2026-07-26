"""The E8 quality reseed preparation is intentionally non-writing."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/prepare_e8_quality_baseline_reseed_20260726.sh"


def test_plan_documents_full_pool_evidence_and_no_numeric_derivation() -> None:
    result = subprocess.run(["bash", str(SCRIPT), "--plan"], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "dedicated full-pool tier evidence" in result.stdout
    assert "never derive quality baseline values from numeric trials" in result.stdout


def test_script_exposes_no_writing_or_attestation_mode() -> None:
    result = subprocess.run(["bash", str(SCRIPT), "--attest"], capture_output=True, text=True)

    assert result.returncode != 0
    assert "usage: --plan|--validate-only|--validate-evidence PATH" in result.stderr


def _evidence(tmp_path: Path) -> Path:
    records = []
    for tier in (1, 2):
        observations = []
        quality = float(tier)
        for index, q in enumerate((quality - 0.1, quality, quality + 0.1)):
            raw = tmp_path / f"tier{tier}-observation-{index}.json"
            raw_payload = {
                "q": q,
                "ts": "2026-07-26T00:00:00Z",
                "core_id": f"core-{tier}",
                "protocol_id": f"E8-full-pool-tier-{tier}",
                "n": 4,
                "era": "E8",
                "per_suite_quality": {"suite": quality},
                "per_suite_counts": {"suite": 4},
            }
            raw.write_text(json.dumps(raw_payload) + "\n")
            observations.append(
                {
                    key: raw_payload[key]
                    for key in ("q", "ts", "core_id", "protocol_id", "n", "era")
                }
                | {"path": str(raw), "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
            )
        source = tmp_path / f"tier{tier}.json"
        source.write_text(
            json.dumps(
                {
                    "tier": tier,
                    "core_id": f"core-{tier}",
                    "n": 4,
                    "quality": quality,
                    "per_suite_quality": {"suite": quality},
                    "per_suite_counts": {"suite": 4},
                    "era": "E8",
                    "decision_grade": True,
                    "observations": observations,
                }
            )
            + "\n"
        )
        records.append(
            {
                "tier": tier,
                "path": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "protocol_id": f"E8-full-pool-tier-{tier}",
                "core_id": f"core-{tier}",
                "n": 4,
                "timestamp": "2026-07-26T00:00:00Z",
                "era": "E8",
                "instrument": "dedicated_full_pool_tier_baseline",
                "quality": quality,
            }
        )
    evidence = {
        "schema": "epyc.e8_quality_baseline_evidence.v1",
        "eval_quality_era": "E8",
        "source_records": records,
        "replacement": {
            "baseline_state": {
                "eval_quality_era": "E8",
                "baselines_by_tier": {"1": 1.0, "2": 2.0},
                "per_suite_quality_by_tier": {"1": {"suite": 1.0}, "2": {"suite": 2.0}},
                "per_suite_counts_by_tier": {"1": {"suite": 4}, "2": {"suite": 4}},
            },
            "quality_history_by_tier": {"1": [0.9, 1.0, 1.1], "2": [1.9, 2.0, 2.1]},
            "quality_history_provenance_by_tier": {
                "1": [
                    {"q": 0.9, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-1"},
                    {"q": 1.0, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-1"},
                    {"q": 1.1, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-1"},
                ],
                "2": [
                    {"q": 1.9, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-2"},
                    {"q": 2.0, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-2"},
                    {"q": 2.1, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-2"},
                ],
            },
        },
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence) + "\n")
    return path


def _validate(evidence: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "--validate-evidence", str(evidence)],
        env={**os.environ, "EPYC_PYTHON": "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python"},
        capture_output=True,
        text=True,
    )


def test_evidence_contract_accepts_two_hash_verified_full_pool_tier_records(tmp_path: Path) -> None:
    result = _validate(_evidence(tmp_path))

    assert result.returncode == 0, result.stderr


def test_evidence_contract_rejects_source_hash_mismatch(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    payload["source_records"][0]["sha256"] = "0" * 64
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "hash mismatch" in result.stderr


def test_evidence_contract_rejects_numeric_derived_source(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    payload["source_records"][0]["instrument"] = "autopilot_numeric_trial"
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "numeric-derived" in result.stderr


def test_evidence_contract_rejects_unrelated_baseline_key(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    payload["replacement"]["baseline_state"]["speed"] = 99.0
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "non-quality fields" in result.stderr


def test_evidence_contract_rejects_insufficient_mad_history(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    payload["replacement"]["quality_history_by_tier"]["1"] = [1.0]
    payload["replacement"]["quality_history_provenance_by_tier"]["1"] = [
        {"q": 1.0, "ts": "2026-07-26T00:00:00Z", "era": "E8", "core_id": "core-1"}
    ]
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "derived from raw" in result.stderr


def test_evidence_contract_rejects_non_decision_grade_source(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    source = Path(payload["source_records"][0]["path"])
    summary = json.loads(source.read_text())
    summary["decision_grade"] = False
    source.write_text(json.dumps(summary) + "\n")
    payload["source_records"][0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "not decision-grade" in result.stderr


def test_evidence_contract_rejects_tampered_raw_observation(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    raw = Path(payload["source_records"][0]["path"])
    summary = json.loads(raw.read_text())
    observation = Path(summary["observations"][0]["path"])
    observation.write_text("{}\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "raw observation artifact hash mismatch" in result.stderr


def test_evidence_contract_rejects_aggregate_mismatch(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    payload["replacement"]["baseline_state"]["baselines_by_tier"]["1"] = 9.0
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "baseline does not match source quality" in result.stderr


def test_evidence_contract_rejects_mismatched_observation_protocol_or_n(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    source = Path(payload["source_records"][0]["path"])
    summary = json.loads(source.read_text())
    summary["observations"][0]["protocol_id"] = "wrong-protocol"
    source.write_text(json.dumps(summary) + "\n")
    payload["source_records"][0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "protocol or n differs" in result.stderr


def test_evidence_contract_rejects_copied_raw_observation(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads(evidence.read_text())
    source = Path(payload["source_records"][0]["path"])
    summary = json.loads(source.read_text())
    original = Path(summary["observations"][0]["path"])
    copied = tmp_path / "copied-observation.json"
    copied.write_bytes(original.read_bytes())
    summary["observations"][1]["path"] = str(copied)
    summary["observations"][1]["sha256"] = hashlib.sha256(copied.read_bytes()).hexdigest()
    source.write_text(json.dumps(summary) + "\n")
    payload["source_records"][0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence.write_text(json.dumps(payload) + "\n")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "repeats a raw observation path or content hash" in result.stderr

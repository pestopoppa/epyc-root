"""SC33 reward-integrity rows are prospective, exact, and authority-free."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_reward_integrity as reward  # noqa: E402


def _claim(*, released: bool) -> dict:
    return {
        "schema": "epyc.autokernel.device_claim_receipt.v1",
        "claim_id": "akd-reward-fixture",
        "device_id": reward.DEVICE_ID,
        "campaign_id": "ak-reward-successor",
        "acquired_at": "2026-08-12T12:00:00+00:00",
        "released_at": "2026-08-12T12:01:00+00:00" if released else None,
        "state": "held",
    }


def _sign(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("receipt_sha256", None)
    unsigned["receipt_sha256"] = reward._canonical_sha256(unsigned)
    return unsigned


def _writer_row(**fields) -> dict:
    value = dict(fields)
    value["measurement_sha256"] = reward._canonical_sha256(value)
    return value


def _producer_rows(receipt: dict) -> list[dict]:
    """Independent fixture implementation of the research-repo v2 writer."""
    producer = receipt["producer"]
    claim_identity = {
        "opened": receipt["device_claim_open"],
        "released": receipt["device_claim_released"],
    }
    claim_sha = reward._canonical_sha256(claim_identity)
    sampling_sha = receipt["device_sampling"]["sha256"]
    case_identities = [{
        key: case[key] for key in (
            "case_id", "label", "mode", "source", "source_sha256", "binary",
            "binary_sha256")
    } for case in receipt["cases"]]
    detector_observations = [{
        "case_id": case["case_id"],
        "label": case["label"],
        "detected": case["detected"],
        "findings_sha256": reward._canonical_sha256(case["findings"]),
        "runtime_behavior_manifested": case["runtime_behavior_manifested"],
    } for case in receipt["cases"]]
    common = {
        "campaign_id": receipt["campaign_id"],
        "purpose": reward.PURPOSE,
        "producer_identity": producer,
        "device_claim_identity": claim_identity,
        "device_claim_identity_sha256": claim_sha,
        "device_sampling_sha256": sampling_sha,
        "instrument_validation_only": True,
        "candidate_speed_claim": False,
        "grants_campaign_authority": False,
    }
    population = {
        "case_identities": case_identities,
        "detector_observations": detector_observations,
        "corpus": receipt["corpus"],
        "producer_sha256": producer["sha256"],
        "device_claim_identity_sha256": claim_sha,
        "device_sampling_sha256": sampling_sha,
    }
    population_sha = reward._canonical_sha256(population)
    rows = []
    for measurement_id, metric, value, direction, reps, reps_basis in (
            ("reward_integrity_detector_sensitivity",
             "autokernel_reward_integrity_detector_sensitivity",
             receipt["corpus"]["sensitivity"], "higher_better", 10,
             "scored:planted executable cases"),
            ("reward_integrity_detector_specificity",
             "autokernel_reward_integrity_detector_specificity",
             receipt["corpus"]["specificity"], "higher_better", 15,
             "scored:clean executable cases"),
            ("reward_integrity_detector_false_positive_rate",
             "autokernel_reward_integrity_detector_false_positive_rate",
             receipt["corpus"]["false_positive_rate"], "lower_better", 15,
             "scored:clean executable cases")):
        rows.append(_writer_row(
            measurement_id=measurement_id,
            metric=metric,
            value=value,
            unit="fraction",
            metric_direction=direction,
            category="BASELINE",
            protocol_id=reward.SOURCE_SCHEMA,
            reps=reps,
            reps_basis=reps_basis,
            claim=(f"AutoKernel reward-integrity instrument observed {metric}={value:.9g} "
                   f"across {reps} scored cases; instrument validation only"),
            extra={**common, "evidence_basis": population,
                   "evidence_sha256": population_sha},
        ))
    identities = {item["case_id"]: item for item in case_identities}
    for case in receipt["cases"]:
        case_identity = identities[case["case_id"]]
        for unit in case["ranked_units"]:
            unit_identity = {
                key: unit[key] for key in ("unit_id", "kind", "n", "argv")}
            evidence = {
                "case_identity": case_identity,
                "ranked_unit_identity": unit_identity,
                "result": unit["result"],
                "returncode": unit["returncode"],
                "runtime_behavior_manifested": case["runtime_behavior_manifested"],
                "producer_sha256": producer["sha256"],
                "device_claim_identity_sha256": claim_sha,
                "device_sampling_sha256": sampling_sha,
            }
            elapsed = float(unit["result"]["gpu_elapsed_ms"])
            rows.append(_writer_row(
                measurement_id=(f"reward_integrity_gpu_elapsed_ms__{case['case_id']}__"
                                f"{unit['unit_id']}"),
                metric="autokernel_reward_integrity_ranked_unit_gpu_elapsed_ms",
                value=elapsed,
                unit="ms",
                metric_direction="lower_better",
                category="BASELINE",
                protocol_id=reward.SOURCE_SCHEMA,
                reps=reward.KERNEL_REPETITIONS,
                reps_basis="scored:HIP kernel launches in one ranked unit",
                claim=(f"AutoKernel reward-integrity case {case['case_id']} "
                       f"{unit['unit_id']} observed {elapsed:.9g} ms across "
                       f"{reward.KERNEL_REPETITIONS} launches; instrument validation only, "
                       "not candidate speed"),
                extra={**common, "case_identity": case_identity,
                       "ranked_unit_identity": unit_identity,
                       "evidence_basis": evidence,
                       "evidence_sha256": reward._canonical_sha256(evidence)},
            ))
    return rows


def successor_receipt() -> dict:
    cases = []
    hipcc = "/opt/rocm/bin/hipcc"
    for index, (case_id, mode) in enumerate(reward.EXPECTED_CASES.items(), 1):
        label = "planted" if case_id in reward.PLANTED_CASES else "clean"
        binary = f"/evidence/bin/{case_id}"
        units = []
        for unit_id, (kind, n) in reward.EXPECTED_UNITS.items():
            units.append({
                "unit_id": unit_id,
                "kind": kind,
                "n": n,
                "argv": [binary, str(n)],
                "returncode": 0,
                "wall_duration_s": 0.2 + index / 1000,
                "stderr_tail": "",
                "result": {
                    "n": n,
                    "mismatches": n if label == "planted" else 0,
                    "gpu_elapsed_ms": float(index) + (0.1 if n == 127 else 0.0),
                    "repetitions": reward.KERNEL_REPETITIONS,
                },
            })
        cases.append({
            "case_id": case_id,
            "label": label,
            "mode": mode,
            "source": f"/evidence/sources/{case_id}.hip",
            "source_sha256": f"{index:064x}",
            "binary": binary,
            "binary_sha256": f"{index + 100:064x}",
            "compile_argv": [hipcc, "--offload-arch=gfx90a", "-O2", "-pthread",
                             f"/evidence/sources/{case_id}.hip", "-o", binary],
            "compile_returncode": 0,
            "compile_duration_s": 0.1,
            "detected": label == "planted",
            "findings": {"detector": [case_id] if label == "planted" else []},
            "runtime_behavior_manifested": True,
            "ranked_units": units,
        })
    opened, released = _claim(released=False), _claim(released=True)
    sampling = {
        "schema": "epyc.autokernel.device_sampling_receipt.v1",
        "sampler_id": "autokernel.execution.device_sampler/v1",
        "device_id": "ROCm0",
        "source": "amdgpu-hwmon/numeric-250ms/v1",
        "started_at": "2026-08-12T12:00:00.100000Z",
        "ended_at": "2026-08-12T12:00:59.900000Z",
        "interval_s": 0.25,
        "duration_s": 59.8,
        "command": ["/opt/rocm/bin/rocm-smi", "-d", "0", "--showclocks",
                    "--showpower", "--showtemp"],
        "sample_count": 2,
        "max_gap_s": 0.25,
        "samples": [
            {"offset_s": 0.0, "power_w": 42.0, "sclk_mhz": 800.0,
             "mclk_mhz": 1600.0, "temperature_c": 35.0,
             "under_measurement_load": True},
            {"offset_s": 0.25, "power_w": 43.0, "sclk_mhz": 1700.0,
             "mclk_mhz": 1600.0, "temperature_c": 36.0,
             "under_measurement_load": True},
        ],
    }
    sampling["sha256"] = reward._canonical_sha256(sampling)
    value = {
        "schema": reward.SOURCE_SCHEMA,
        "status": "complete",
        "campaign_id": "ak-reward-successor",
        "purpose": reward.PURPOSE,
        "receipt_sha256_scope": "canonical JSON of every field except receipt_sha256",
        "attempt_history": [],
        "started_at": "2026-08-12T12:00:00Z",
        "ended_at": "2026-08-12T12:01:00Z",
        "host": {"uname": "Linux test", "hipcc": hipcc},
        "producer": {
            "producer_id": reward.PRODUCER_ID,
            "path": reward.PRODUCER_PATH,
            "sha256": "a" * 64,
        },
        "corpus": {
            "planted": len(reward.PLANTED_CASES),
            "clean": len(reward.CLEAN_CASES),
            "true_positives": len(reward.PLANTED_CASES),
            "false_positives": 0,
            "sensitivity": 1.0,
            "specificity": 1.0,
            "false_positive_rate": 0.0,
            "runtime_behavior_manifested": len(reward.EXPECTED_CASES),
            "runtime_behavior_total": len(reward.EXPECTED_CASES),
        },
        "ranked_set": {
            "unit_ids": ["normal-128", "anti-short-circuit-127"],
            "both_units_measured_for_every_program": True,
        },
        "device_claim_open": opened,
        "device_claim_released": released,
        "device_sampling": sampling,
        "device_claim_identity_sha256": reward._canonical_sha256({
            "opened": opened, "released": released}),
        "cases": cases,
    }
    value["belief_measurements"] = _producer_rows(value)
    return _sign(value)


def test_pre_hook_v1_receipt_is_never_backfilled() -> None:
    assert reward.native_rows({
        "schema": reward.LEGACY_SCHEMA,
        "campaign_id": "ak-rvp-c6-executable-corpus-20260812",
        "corpus": {"sensitivity": 1.0, "specificity": 1.0},
    }) == ()
    with pytest.raises(ct.ProjectionError, match="legacy"):
        reward.native_rows({
            "schema": reward.LEGACY_SCHEMA,
            "belief_measurements": [{"invented": True}],
        })


def test_successor_projects_three_detector_and_fifty_ranked_unit_rows() -> None:
    rows = reward.native_rows(
        successor_receipt(),
        receipt_locator="campaign:reward-successor/receipt.json",
        receipt_sha256="f" * 64,
        attestation_present=True)
    projected = [reward.project(row) for row in rows]
    assert len(projected) == len({row.measurement_id for row in projected}) == 53
    assert [row.metric_direction for row in projected[:3]] == [
        "higher_better", "higher_better", "lower_better"]
    assert [row.value for row in projected[:3]] == [1.0, 1.0, 0.0]
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in projected)
    elapsed = projected[3]
    assert elapsed.reps == reward.KERNEL_REPETITIONS
    assert elapsed.extra["case_identity"]["source_sha256"] == "1".zfill(64)
    assert elapsed.extra["case_identity"]["binary_sha256"] == f"{101:064x}"
    assert elapsed.extra["ranked_unit_identity"]["unit_id"] == "normal-128"
    assert elapsed.extra["device_claim_identity"]["released"]["released_at"]
    assert all(row.extra["instrument_validation_only"] is True for row in projected)
    assert all(row.extra["candidate_speed_claim"] is False for row in projected)
    assert all(row.extra["grants_campaign_authority"] is False for row in projected)


def test_detector_failures_project_as_negative_evidence_instead_of_disappearing() -> None:
    value = successor_receipt()
    value["cases"][0]["findings"] = {"detector": []}
    value["cases"][0]["detected"] = False
    first_clean = next(case for case in value["cases"] if case["label"] == "clean")
    first_clean["findings"] = {"detector": ["false-positive"]}
    first_clean["detected"] = True
    value["corpus"].update({
        "true_positives": 9,
        "false_positives": 1,
        "sensitivity": 0.9,
        "specificity": 14 / 15,
        "false_positive_rate": 1 / 15,
    })
    value["belief_measurements"] = _producer_rows(value)
    rows = reward.native_rows(_sign(value))
    projected = [reward.project(row) for row in rows[:3]]
    assert [row.value for row in projected] == [0.9, 14 / 15, 1 / 15]


@pytest.mark.parametrize("defect", [
    "receipt", "row", "source", "binary", "compile", "case", "unit", "elapsed",
    "reps", "claim", "sampling", "corpus", "producer", "authority", "purpose",
    "missing_rows",
])
def test_identity_metric_and_authority_defects_fail_closed(defect: str) -> None:
    value = successor_receipt()
    if defect == "receipt":
        value["receipt_sha256"] = "0" * 64
    elif defect == "row":
        value["belief_measurements"][0]["value"] = 0.5
        value = _sign(value)
    elif defect == "source":
        value["cases"][0]["source_sha256"] = "0" * 64
        value = _sign(value)
    elif defect == "binary":
        value["cases"][0]["binary_sha256"] = "0" * 64
        value = _sign(value)
    elif defect == "compile":
        value["cases"][0]["compile_argv"][1] = "--offload-arch=gfx942"
        value = _sign(value)
    elif defect == "case":
        value["cases"][0]["case_id"] = value["cases"][1]["case_id"]
        value = _sign(value)
    elif defect == "unit":
        value["cases"][0]["ranked_units"][0]["n"] = 127
        value = _sign(value)
    elif defect == "elapsed":
        value["cases"][0]["ranked_units"][0]["result"]["gpu_elapsed_ms"] += 1
        value = _sign(value)
    elif defect == "reps":
        value["cases"][0]["ranked_units"][0]["result"]["repetitions"] = 127
        value = _sign(value)
    elif defect == "claim":
        value["device_claim_released"]["claim_id"] = "akd-other"
        value = _sign(value)
    elif defect == "sampling":
        value["device_sampling"]["samples"][0]["under_measurement_load"] = False
        unsigned = dict(value["device_sampling"])
        unsigned.pop("sha256")
        value["device_sampling"]["sha256"] = reward._canonical_sha256(unsigned)
        value = _sign(value)
    elif defect == "corpus":
        value["corpus"]["false_positive_rate"] = 0.1
        value = _sign(value)
    elif defect == "producer":
        value["producer"]["producer_id"] = "other"
        value = _sign(value)
    elif defect == "authority":
        value["promotion_authority"] = "autonomous"
        value = _sign(value)
    elif defect == "purpose":
        value["purpose"] = "candidate speed claim"
        value = _sign(value)
    else:
        value.pop("belief_measurements")
        value = _sign(value)
    with pytest.raises(ct.ProjectionError):
        reward.native_rows(value)


def test_project_refuses_a_row_mutated_after_validation() -> None:
    native = dict(reward.native_rows(successor_receipt())[0])
    native["measurement"] = {**native["measurement"], "value": 0.5}
    with pytest.raises(ct.ProjectionError, match="mutated"):
        reward.project(native)

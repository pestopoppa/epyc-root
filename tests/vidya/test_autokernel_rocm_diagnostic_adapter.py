"""SC28 ROCm diagnostics are re-derived, identity-bound, and authority-free."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_rocm_diagnostic as diagnostic  # noqa: E402


def _claim(*, released: bool) -> dict:
    return {
        "schema": "epyc.autokernel.device_claim_receipt.v1",
        "claim_id": "akd-fixture", "device_id": "mi210_0",
        "campaign_id": "ak-fixture", "acquired_at": "2026-08-12T06:00:00Z",
        "state": "released" if released else "held",
        "released_at": "2026-08-12T06:01:00Z" if released else None,
    }


def _sampling() -> dict:
    rows = [
        {"offset_s": 0.0, "power_w": 190.0, "sclk_mhz": 1700.0},
        {"offset_s": 0.25, "power_w": 196.0, "sclk_mhz": 1700.0},
        {"offset_s": 0.50, "power_w": 194.0, "sclk_mhz": 1600.0},
    ]
    value = {"schema": "epyc.autokernel.device_sampling_receipt.v1",
             "sample_count": len(rows), "samples": rows}
    value["sha256"] = diagnostic._canonical_sha256(value)
    return value


def _producer(receipt: dict, *, producer_id: str, path: str) -> dict:
    receipt["producer"] = {"producer_id": producer_id, "path": path, "sha256": "e" * 64}
    claim = {"opened": receipt["device_claim_open"],
             "released": receipt["device_claim_released"]}
    receipt["device_claim_identity_sha256"] = diagnostic._canonical_sha256(claim)
    return receipt


def _sign(receipt: dict) -> dict:
    unsigned = copy.deepcopy(receipt)
    unsigned.pop("receipt_sha256", None)
    unsigned["receipt_sha256"] = diagnostic._canonical_sha256(unsigned)
    return unsigned


def _row(**fields) -> dict:
    value = dict(fields)
    value["measurement_sha256"] = diagnostic._canonical_sha256(value)
    return value


def saturation_receipt(*, prospective: bool = True) -> dict:
    value = {
        "schema": diagnostic.SATURATION_SCHEMA, "campaign_id": "ak-fixture",
        "started_at": "2026-08-12T06:00:00Z", "ended_at": "2026-08-12T06:01:00Z",
        "workload": {"schema": "epyc.rocm_gemm_saturation.v1",
                     "arch": "gfx90a:sramecc+", "m": 8192, "n": 8192, "k": 8192,
                     "iterations": 64, "throughput_tflops": 41.75},
        "workload_source": "/source/rocm_gemm_saturation.cpp",
        "workload_source_sha256": "a" * 64,
        "workload_binary": "/bin/rocm_gemm_saturation",
        "workload_binary_sha256": "b" * 64,
        "device_claim_open": _claim(released=False),
        "device_claim_released": _claim(released=True),
        "device_sampling": _sampling(), "power_cap_w": 300.0,
        "max_power_w": 196.0, "nominal_sclk_mhz": 1700.0,
        "nominal_sclk_sample_fraction": 2 / 3,
    }
    if not prospective:
        return value
    value["status"] = "complete"
    value["source_identity"] = {"path": value["workload_source"],
                                "sha256": value["workload_source_sha256"]}
    value["binary_identity"] = {"path": value["workload_binary"],
                                "sha256": value["workload_binary_sha256"]}
    _producer(
        value, producer_id=diagnostic.SATURATION_PRODUCER_ID,
        path=diagnostic.SATURATION_PRODUCER_PATH)
    claim_identity = {"opened": value["device_claim_open"],
                      "released": value["device_claim_released"]}
    claim_sha = value["device_claim_identity_sha256"]
    evidence = {
        "workload": value["workload"],
        "device_sampling_sha256": value["device_sampling"]["sha256"],
        "source_identity": value["source_identity"],
        "binary_identity": value["binary_identity"],
        "device_claim_identity_sha256": claim_sha, "power_cap_w": 300.0,
        "nominal_sclk_mhz": 1700.0, "producer_sha256": "e" * 64,
    }
    common = {
        "campaign_id": "ak-fixture", "source_identity": value["source_identity"],
        "binary_identity": value["binary_identity"],
        "device_claim_identity": claim_identity,
        "device_claim_identity_sha256": claim_sha,
        "producer_id": diagnostic.SATURATION_PRODUCER_ID,
        "producer_sha256": "e" * 64, "evidence_basis": evidence,
        "evidence_sha256": diagnostic._canonical_sha256(evidence),
        "diagnostic_only": True, "grants_campaign_authority": False,
    }
    specs = (
        ("rvp_t0_1_sustained_gemm_throughput_tflops",
         "gfx90a_sustained_gemm_throughput_tflops", 41.75, "TFLOP/s",
         "higher_better", 64, "scored:completed GEMM iterations",
         "RVP-T0-1 observed sustained GEMM throughput 41.75 TFLOP/s"),
        ("rvp_t0_1_nominal_sclk_hold_fraction", "gfx90a_nominal_sclk_hold_fraction",
         2 / 3, "fraction", "higher_better", 3,
         "scored:in-window device-state samples",
         f"RVP-T0-1 observed nominal-clock hold fraction {2 / 3:.9g}"),
        ("rvp_t0_1_peak_power_w", "gfx90a_peak_power_w", 196.0, "W",
         "lower_better", 3, "scored:in-window device-state samples",
         "RVP-T0-1 observed peak board power 196 W"),
        ("rvp_t0_1_power_headroom_w", "gfx90a_power_cap_headroom_w", 104.0, "W",
         "higher_better", 3, "scored:in-window device-state samples",
         "RVP-T0-1 observed 104 W headroom to the declared cap"),
    )
    value["belief_measurements"] = [_row(
        measurement_id=mid, metric=metric, value=number, unit=unit,
        metric_direction=direction, category="BASELINE",
        protocol_id=diagnostic.SATURATION_SCHEMA, reps=reps,
        reps_basis=basis, claim=claim, extra=common)
        for mid, metric, number, unit, direction, reps, basis, claim in specs]
    return _sign(value)


def vendor_receipt(*, prospective: bool = True) -> dict:
    raw, comparisons = [], []
    for m, n, k, roc, hip in (
            (896, 128, 896, 10.0, 12.0), (4864, 128, 896, 20.0, 18.0)):
        raw.extend((
            {"schema": "epyc.rocm.gemm_baseline.v1", "library": "rocblas",
             "dtype": "fp16_compute_fp32", "m": m, "n": n, "k": k,
             "repetitions": 30, "tflops": roc},
            {"schema": "epyc.rocm.gemm_baseline.v1", "library": "hipblaslt",
             "dtype": "fp16_compute_fp32", "m": m, "n": n, "k": k,
             "repetitions": 30, "tflops": hip}))
        comparisons.append({"m": m, "n": n, "k": k,
                            "rocblas_tflops": roc, "hipblaslt_tflops": hip,
                            "hipblaslt_over_rocblas": hip / roc})
    value = {
        "schema": diagnostic.VENDOR_SCHEMA, "campaign_id": "ak-fixture",
        "started_at": "2026-08-12T06:00:00Z", "ended_at": "2026-08-12T06:01:00Z",
        "comparator_source": "/source/rocm_gemm_baseline_compare.cpp",
        "comparator_source_sha256": "c" * 64,
        "comparator_binary": "/bin/rocm_gemm_baseline_compare",
        "comparator_binary_sha256": "d" * 64,
        "device_claim_open": _claim(released=False),
        "device_claim_released": _claim(released=True),
        "device_sampling": _sampling(),
        "metadata": {"schema": "epyc.rocm.gemm_baseline.meta.v1", "shape_count": 2},
        "raw_results": raw, "comparisons": comparisons,
    }
    if not prospective:
        return value
    value["status"] = "complete"
    value["source_identity"] = {"path": value["comparator_source"],
                                "sha256": value["comparator_source_sha256"]}
    value["binary_identity"] = {"path": value["comparator_binary"],
                                "sha256": value["comparator_binary_sha256"]}
    _producer(
        value, producer_id=diagnostic.VENDOR_PRODUCER_ID,
        path=diagnostic.VENDOR_PRODUCER_PATH)
    claim_identity = {"opened": value["device_claim_open"],
                      "released": value["device_claim_released"]}
    rows = []
    for item in sorted(comparisons, key=lambda row: (row["m"], row["n"], row["k"])):
        m, n, k = item["m"], item["n"], item["k"]
        pair = {row["library"]: row for row in raw
                if (row["m"], row["n"], row["k"]) == (m, n, k)}
        ratio = item["hipblaslt_tflops"] / item["rocblas_tflops"]
        best = "hipblaslt" if ratio > 1 else "rocblas"
        evidence = {
            "shape": {"m": m, "n": n, "k": k, "dtype": "fp16_compute_fp32"},
            "provider_rows": pair, "source_identity": value["source_identity"],
            "binary_identity": value["binary_identity"],
            "device_claim_identity_sha256": value["device_claim_identity_sha256"],
            "producer_sha256": "e" * 64,
        }
        rows.append(_row(
            measurement_id=f"ak_bh_1_m{m}_n{n}_k{k}_hipblaslt_over_rocblas",
            metric="hipblaslt_over_rocblas_exact_shape_throughput_ratio",
            value=ratio, unit="ratio", metric_direction="higher_better",
            category="BASELINE", protocol_id=diagnostic.VENDOR_SCHEMA, reps=30,
            reps_basis="scored:timed repetitions per provider at exact shape",
            claim=(f"AK-BH-1 shape m={m},n={n},k={k} observed hipBLASLt/rocBLAS "
                   f"throughput ratio {ratio:.9g}; stronger provider {best}"),
            extra={
                "campaign_id": "ak-fixture", "shape": evidence["shape"],
                "rocblas_tflops": item["rocblas_tflops"],
                "hipblaslt_tflops": item["hipblaslt_tflops"],
                "stronger_provider": best, "source_identity": value["source_identity"],
                "binary_identity": value["binary_identity"],
                "device_claim_identity": claim_identity,
                "device_claim_identity_sha256": value["device_claim_identity_sha256"],
                "producer_id": diagnostic.VENDOR_PRODUCER_ID,
                "producer_sha256": "e" * 64, "evidence_basis": evidence,
                "evidence_sha256": diagnostic._canonical_sha256(evidence),
                "exact_shape_only": True, "global_provider_selection": False,
                "grants_campaign_authority": False,
            }))
    value["belief_measurements"] = rows
    return _sign(value)


def test_pre_hook_receipts_are_not_backfilled() -> None:
    assert diagnostic.native_rows(saturation_receipt(prospective=False)) == ()
    assert diagnostic.native_rows(vendor_receipt(prospective=False)) == ()


def test_saturation_projects_four_attested_directional_claims() -> None:
    rows = diagnostic.native_rows(
        saturation_receipt(), receipt_locator="campaign:rvp/receipt.json",
        receipt_sha256="f" * 64, attestation_present=True)
    projected = [diagnostic.project(row) for row in rows]
    assert len(projected) == 4
    assert [row.metric_direction for row in projected] == [
        "higher_better", "higher_better", "lower_better", "higher_better"]
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in projected)
    assert all(row.extra["grants_campaign_authority"] is False for row in projected)


def test_vendor_projects_one_unique_exact_shape_claim_per_comparison() -> None:
    rows = diagnostic.native_rows(
        vendor_receipt(), receipt_locator="campaign:bh/receipt.json",
        receipt_sha256="f" * 64, attestation_present=True)
    projected = [diagnostic.project(row) for row in rows]
    assert len(projected) == len({row.measurement_id for row in projected}) == 2
    assert {row.value for row in projected} == {1.2, 0.9}
    assert all(row.extra["exact_shape_only"] is True for row in projected)
    assert all(row.extra["global_provider_selection"] is False for row in projected)


@pytest.mark.parametrize("kind,defect", [
    ("saturation", "receipt"), ("saturation", "row"),
    ("saturation", "source"), ("saturation", "sampling"),
    ("saturation", "authority"), ("vendor", "ratio"),
    ("vendor", "claim"), ("vendor", "provider"),
])
def test_tampering_and_authority_fail_closed(kind: str, defect: str) -> None:
    value = saturation_receipt() if kind == "saturation" else vendor_receipt()
    if defect == "receipt":
        value["receipt_sha256"] = "0" * 64
    elif defect == "row":
        value["belief_measurements"][0]["value"] += 1
        value = _sign(value)
    elif defect == "source":
        value["source_identity"]["sha256"] = "0" * 64
        value = _sign(value)
    elif defect == "sampling":
        value["device_sampling"]["samples"][0]["power_w"] += 1
        value = _sign(value)
    elif defect == "authority":
        value["autonomous_promotion_authority"] = True
        value = _sign(value)
    elif defect == "ratio":
        value["comparisons"][0]["hipblaslt_over_rocblas"] = 99.0
        value = _sign(value)
    elif defect == "claim":
        value["device_claim_released"]["claim_id"] = "other"
        value = _sign(value)
    else:
        value["raw_results"][0]["library"] = "other"
        value = _sign(value)
    with pytest.raises(ct.ProjectionError):
        diagnostic.native_rows(value)

"""Project prospective AutoKernel ROCm diagnostic receipts into ClaimTuples.

Only producer-written ``belief_measurements`` are eligible.  The admitted
2026-08-12 RVP-T0-1 and AK-BH-1 receipts predate the hook, so their absence is
an empty projection rather than permission to reconstruct claims.  For future
receipts this reader independently derives every metric, exact-shape identity,
row digest, source/binary/device-claim binding, and logical receipt digest.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_rocm_diagnostic/v1"
SATURATION_SCHEMA = "epyc.rvp_t0_1_saturation_probe.v1"
VENDOR_SCHEMA = "epyc.ak_bh_1_gemm_baseline_compare.v1"
SOURCE_SCHEMAS = frozenset({SATURATION_SCHEMA, VENDOR_SCHEMA})
SATURATION_PRODUCER_ID = "scripts.benchmark.run_rocm_saturation_probe/v2"
VENDOR_PRODUCER_ID = "scripts.benchmark.run_rocm_gemm_baseline_compare/v2"
SATURATION_PRODUCER_PATH = "scripts/benchmark/run_rocm_saturation_probe.py"
VENDOR_PRODUCER_PATH = "scripts/benchmark/run_rocm_gemm_baseline_compare.py"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY = re.compile(
    r"(?:auto|autonomous|unattended|unsupervised|authori[sz]e[ds]?|approv(?:e[ds]?|al)|"
    r"permit(?:ted)?|grant(?:ed)?|override).*(?:promot|ratif|deploy|release|freeze|cutover)|"
    r"(?:promot|ratif|deploy|release|freeze|cutover).*(?:authority|authori[sz]|approv|auto)",
    re.IGNORECASE,
)


def _canonical_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"diagnostic source is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{label} must be non-empty text")
    return value.strip()


def _mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{label} must be an object")
    return value


def _finite(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or (positive and value <= 0):
        qualifier = "positive " if positive else ""
        raise ProjectionError(f"{label} must be a {qualifier}finite number")
    return float(value)


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProjectionError(f"{label} must be a positive integer")
    return value


def _contains_authority(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_AUTHORITY.search(str(key).replace("_", " "))
                   or _contains_authority(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_authority(child) for child in value)
    return False


def _claim_identity(receipt: dict) -> tuple[dict, str]:
    opened = _mapping(receipt.get("device_claim_open"), "device_claim_open")
    released = _mapping(receipt.get("device_claim_released"), "device_claim_released")
    for key in ("claim_id", "device_id", "campaign_id", "acquired_at"):
        _text(opened.get(key), f"device_claim_open.{key}")
        if released.get(key) != opened[key]:
            raise ProjectionError(f"device claim {key} changed across release")
    # ClaimReceipt retains the state immediately before Claim.release() drops
    # the lock.  The durable release proof is released_at; there is no
    # synthetic ``released`` state in the canonical claim implementation.
    if released.get("state") not in {"held", "draining"} \
            or not released.get("released_at"):
        raise ProjectionError("device claim must be durably released")
    identity = {"opened": opened, "released": released}
    return identity, _canonical_sha256(identity)


def _common(receipt: dict, *, producer_id: str, producer_path: str,
            source_prefix: str, binary_prefix: str) -> tuple[dict, dict, dict, dict, str]:
    producer = _mapping(receipt.get("producer"), "producer")
    if producer.get("producer_id") != producer_id or producer.get("path") != producer_path:
        raise ProjectionError("diagnostic receipt names a different producer")
    _sha(producer.get("sha256"), "producer.sha256")
    source = {
        "path": _text(receipt.get(f"{source_prefix}_source"), f"{source_prefix}_source"),
        "sha256": _sha(
            receipt.get(f"{source_prefix}_source_sha256"),
            f"{source_prefix}_source_sha256"),
    }
    binary = {
        "path": _text(receipt.get(f"{binary_prefix}_binary"), f"{binary_prefix}_binary"),
        "sha256": _sha(
            receipt.get(f"{binary_prefix}_binary_sha256"),
            f"{binary_prefix}_binary_sha256"),
    }
    if receipt.get("source_identity") != source or receipt.get("binary_identity") != binary:
        raise ProjectionError("diagnostic top-level identities do not re-derive")
    claim, claim_sha = _claim_identity(receipt)
    if receipt.get("device_claim_identity_sha256") != claim_sha:
        raise ProjectionError("device_claim_identity_sha256 does not bind claim receipts")
    return producer, source, binary, claim, claim_sha


def _measurement(*, measurement_id: str, metric: str, value: float, unit: str,
                 direction: str, protocol: str, reps: int, reps_basis: str,
                 claim: str, extra: Mapping[str, Any]) -> dict:
    row = {
        "measurement_id": measurement_id, "metric": metric, "value": value,
        "unit": unit, "metric_direction": direction, "category": "BASELINE",
        "protocol_id": protocol, "reps": reps, "reps_basis": reps_basis,
        "claim": claim, "extra": dict(extra),
    }
    row["measurement_sha256"] = _canonical_sha256(row)
    return row


def _expected_saturation(receipt: dict) -> list[dict]:
    producer, source, binary, claim_identity, claim_sha = _common(
        receipt, producer_id=SATURATION_PRODUCER_ID,
        producer_path=SATURATION_PRODUCER_PATH,
        source_prefix="workload", binary_prefix="workload")
    workload = _mapping(receipt.get("workload"), "workload")
    sampling = _mapping(receipt.get("device_sampling"), "device_sampling")
    if workload.get("schema") != "epyc.rocm_gemm_saturation.v1" \
            or sampling.get("schema") != "epyc.autokernel.device_sampling_receipt.v1":
        raise ProjectionError("saturation native schemas differ")
    sampling_unsigned = dict(sampling)
    sampling_sha = sampling_unsigned.pop("sha256", None)
    if _sha(sampling_sha, "device_sampling.sha256") != _canonical_sha256(sampling_unsigned):
        raise ProjectionError("device sampling digest does not bind its trace")
    iterations = _positive_int(workload.get("iterations"), "workload.iterations")
    sample_count = _positive_int(sampling.get("sample_count"), "device_sampling.sample_count")
    if not isinstance(sampling.get("samples"), list) \
            or len(sampling["samples"]) != sample_count:
        raise ProjectionError("device sampling count does not bind its trace")
    throughput = _finite(workload.get("throughput_tflops"), "throughput", positive=True)
    nominal_sclk = _finite(receipt.get("nominal_sclk_mhz"), "nominal sclk", positive=True)
    sample_sclks = [_finite(
        item.get("sclk_mhz") if isinstance(item, dict) else None,
        f"device_sampling.samples[{index}].sclk_mhz", positive=True)
        for index, item in enumerate(sampling["samples"])]
    sample_powers = [_finite(
        item.get("power_w") if isinstance(item, dict) else None,
        f"device_sampling.samples[{index}].power_w", positive=True)
        for index, item in enumerate(sampling["samples"])]
    nominal_fraction = sum(value >= nominal_sclk for value in sample_sclks) / sample_count
    if not math.isclose(
            nominal_fraction, _finite(
                receipt.get("nominal_sclk_sample_fraction"), "nominal fraction"),
            rel_tol=1e-12, abs_tol=1e-15):
        raise ProjectionError("nominal clock fraction does not re-derive from device samples")
    if not 0 <= nominal_fraction <= 1:
        raise ProjectionError("nominal clock fraction must be in [0, 1]")
    max_power = max(sample_powers)
    if max_power != _finite(receipt.get("max_power_w"), "peak power", positive=True):
        raise ProjectionError("peak power does not re-derive from device samples")
    power_cap = _finite(receipt.get("power_cap_w"), "power cap", positive=True)
    headroom = power_cap - max_power
    evidence = {
        "workload": workload, "device_sampling_sha256": sampling_sha,
        "source_identity": source, "binary_identity": binary,
        "device_claim_identity_sha256": claim_sha,
        "power_cap_w": power_cap, "nominal_sclk_mhz": nominal_sclk,
        "producer_sha256": producer["sha256"],
    }
    common = {
        "campaign_id": receipt.get("campaign_id"), "source_identity": source,
        "binary_identity": binary, "device_claim_identity": claim_identity,
        "device_claim_identity_sha256": claim_sha,
        "producer_id": producer["producer_id"], "producer_sha256": producer["sha256"],
        "evidence_basis": evidence, "evidence_sha256": _canonical_sha256(evidence),
        "diagnostic_only": True, "grants_campaign_authority": False,
    }
    return [
        _measurement(
            measurement_id="rvp_t0_1_sustained_gemm_throughput_tflops",
            metric="gfx90a_sustained_gemm_throughput_tflops", value=throughput,
            unit="TFLOP/s", direction="higher_better", protocol=SATURATION_SCHEMA,
            reps=iterations, reps_basis="scored:completed GEMM iterations",
            claim=f"RVP-T0-1 observed sustained GEMM throughput {throughput:.9g} TFLOP/s",
            extra=common),
        _measurement(
            measurement_id="rvp_t0_1_nominal_sclk_hold_fraction",
            metric="gfx90a_nominal_sclk_hold_fraction", value=nominal_fraction,
            unit="fraction", direction="higher_better", protocol=SATURATION_SCHEMA,
            reps=sample_count, reps_basis="scored:in-window device-state samples",
            claim=f"RVP-T0-1 observed nominal-clock hold fraction {nominal_fraction:.9g}",
            extra=common),
        _measurement(
            measurement_id="rvp_t0_1_peak_power_w", metric="gfx90a_peak_power_w",
            value=max_power, unit="W", direction="lower_better", protocol=SATURATION_SCHEMA,
            reps=sample_count, reps_basis="scored:in-window device-state samples",
            claim=f"RVP-T0-1 observed peak board power {max_power:.9g} W", extra=common),
        _measurement(
            measurement_id="rvp_t0_1_power_headroom_w",
            metric="gfx90a_power_cap_headroom_w", value=headroom, unit="W",
            direction="higher_better", protocol=SATURATION_SCHEMA,
            reps=sample_count, reps_basis="scored:in-window device-state samples",
            claim=f"RVP-T0-1 observed {headroom:.9g} W headroom to the declared cap",
            extra=common),
    ]


def _expected_vendor(receipt: dict) -> list[dict]:
    producer, source, binary, claim_identity, claim_sha = _common(
        receipt, producer_id=VENDOR_PRODUCER_ID, producer_path=VENDOR_PRODUCER_PATH,
        source_prefix="comparator", binary_prefix="comparator")
    metadata = _mapping(receipt.get("metadata"), "metadata")
    comparisons, raw = receipt.get("comparisons"), receipt.get("raw_results")
    if metadata.get("schema") != "epyc.rocm.gemm_baseline.meta.v1" \
            or not isinstance(comparisons, list) or not comparisons \
            or not isinstance(raw, list) or len(raw) != 2 * len(comparisons):
        raise ProjectionError("vendor receipt lacks exact paired shape evidence")
    if metadata.get("shape_count") != len(comparisons):
        raise ProjectionError("vendor metadata shape_count does not bind comparisons")
    raw_by_shape: dict[tuple[int, int, int], dict[str, dict]] = {}
    for item in raw:
        item = _mapping(item, "raw result")
        key = (item.get("m"), item.get("n"), item.get("k"))
        raw_by_shape.setdefault(key, {})[item.get("library")] = item
    expected = []
    for item in sorted(comparisons, key=lambda row: (row["m"], row["n"], row["k"])):
        item = _mapping(item, "comparison")
        m, n, k = (_positive_int(item.get(axis), f"comparison.{axis}")
                   for axis in ("m", "n", "k"))
        pair = raw_by_shape.get((m, n, k))
        if not isinstance(pair, dict) or set(pair) != {"rocblas", "hipblaslt"}:
            raise ProjectionError("vendor comparison does not bind both providers")
        reps = _positive_int(pair["rocblas"].get("repetitions"), "repetitions")
        if pair["hipblaslt"].get("repetitions") != reps:
            raise ProjectionError("provider repetitions differ within exact shape")
        rocblas = _finite(pair["rocblas"].get("tflops"), "rocblas.tflops", positive=True)
        hipblaslt = _finite(pair["hipblaslt"].get("tflops"), "hipblaslt.tflops", positive=True)
        if (rocblas != _finite(item.get("rocblas_tflops"), "rocblas_tflops", positive=True)
                or hipblaslt != _finite(
                    item.get("hipblaslt_tflops"), "hipblaslt_tflops", positive=True)):
            raise ProjectionError(
                "provider comparison throughput does not re-derive from raw rows")
        ratio = hipblaslt / rocblas
        if not math.isclose(
                ratio, _finite(item.get("hipblaslt_over_rocblas"), "provider ratio"),
                rel_tol=1e-12, abs_tol=1e-15):
            raise ProjectionError("provider ratio does not re-derive")
        best = "hipblaslt" if ratio > 1 else "rocblas"
        evidence = {
            "shape": {"m": m, "n": n, "k": k, "dtype": pair["rocblas"].get("dtype")},
            "provider_rows": pair, "source_identity": source, "binary_identity": binary,
            "device_claim_identity_sha256": claim_sha,
            "producer_sha256": producer["sha256"],
        }
        expected.append(_measurement(
            measurement_id=f"ak_bh_1_m{m}_n{n}_k{k}_hipblaslt_over_rocblas",
            metric="hipblaslt_over_rocblas_exact_shape_throughput_ratio",
            value=ratio, unit="ratio", direction="higher_better", protocol=VENDOR_SCHEMA,
            reps=reps, reps_basis="scored:timed repetitions per provider at exact shape",
            claim=(f"AK-BH-1 shape m={m},n={n},k={k} observed hipBLASLt/rocBLAS "
                   f"throughput ratio {ratio:.9g}; stronger provider {best}"),
            extra={
                "campaign_id": receipt.get("campaign_id"), "shape": evidence["shape"],
                "rocblas_tflops": rocblas, "hipblaslt_tflops": hipblaslt,
                "stronger_provider": best, "source_identity": source,
                "binary_identity": binary, "device_claim_identity": claim_identity,
                "device_claim_identity_sha256": claim_sha,
                "producer_id": producer["producer_id"],
                "producer_sha256": producer["sha256"],
                "evidence_basis": evidence, "evidence_sha256": _canonical_sha256(evidence),
                "exact_shape_only": True, "global_provider_selection": False,
                "grants_campaign_authority": False,
            }))
    return expected


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return only prospective rows; pre-hook receipts yield no claims."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel ROCm diagnostic schema")
    if receipt_sha256:
        _sha(receipt_sha256, "receipt_sha256")
    rows = receipt.get("belief_measurements")
    if rows is None:
        return ()
    if receipt.get("status") != "complete" or not isinstance(rows, list) or not rows:
        raise ProjectionError("only a complete diagnostic may carry belief rows")
    if _contains_authority(receipt):
        raise ProjectionError("diagnostic receipt may not carry promotion or release authority")
    unsigned = dict(receipt)
    stored = unsigned.pop("receipt_sha256", None)
    if _sha(stored, "receipt.receipt_sha256") != _canonical_sha256(unsigned):
        raise ProjectionError("receipt_sha256 does not bind the logical receipt")
    expected = (_expected_saturation(receipt) if receipt["schema"] == SATURATION_SCHEMA
                else _expected_vendor(receipt))
    if rows != expected:
        raise ProjectionError("producer rows do not re-derive from native diagnostic evidence")
    return tuple({
        "receipt": receipt, "measurement": row, "measurement_index": index,
        "receipt_locator": receipt_locator, "receipt_sha256": receipt_sha256,
        "attestation_present": attestation_present,
    } for index, row in enumerate(rows))


@register("autokernel-rocm-diagnostic-measurement")
def project(native: Any) -> ClaimTuple:
    """Project one revalidated native row; the shared measurement ladder grades it."""
    if not isinstance(native, dict):
        raise ProjectionError("AutoKernel ROCm diagnostic native row must be an object")
    receipt = _mapping(native.get("receipt"), "native.receipt")
    rows = native_rows(
        receipt, receipt_locator=str(native.get("receipt_locator") or ""),
        receipt_sha256=str(native.get("receipt_sha256") or ""),
        attestation_present=native.get("attestation_present"))
    index = native.get("measurement_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(rows):
        raise ProjectionError("native measurement_index is invalid")
    expected = rows[index]
    if native.get("measurement") != expected["measurement"]:
        raise ProjectionError("native diagnostic row was mutated after validation")
    row = expected["measurement"]
    campaign = _text(receipt.get("campaign_id"), "receipt.campaign_id")
    local_id = _text(row.get("measurement_id"), "measurement.measurement_id")
    identity = hashlib.sha256(json.dumps(
        [receipt["schema"], campaign, local_id], separators=(",", ":"),
        ensure_ascii=True).encode()).hexdigest()[:24]
    return ClaimTuple(
        measurement_id=f"akrocm_{identity}", metric=row["metric"], value=row["value"],
        date=str(receipt.get("ended_at") or "")[:10], category=row["category"],
        claim=row["claim"], metric_direction=row["metric_direction"],
        protocol_id=row["protocol_id"], reps=row["reps"],
        reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=str(native.get("receipt_sha256") or ""),
        attestation_locator=str(native.get("receipt_locator") or ""),
        attestation_present=native.get("attestation_present"),
        source_kind="autokernel-rocm-diagnostic-measurement",
        extra={
            "source_schema": receipt["schema"], "campaign_id": campaign,
            "native_measurement_id": local_id,
            "native_measurement_sha256": row["measurement_sha256"],
            "receipt_self_sha256": receipt["receipt_sha256"], **row["extra"],
        },
    )


__all__ = [
    "ADAPTER_ID", "SATURATION_SCHEMA", "VENDOR_SCHEMA", "native_rows", "project",
]

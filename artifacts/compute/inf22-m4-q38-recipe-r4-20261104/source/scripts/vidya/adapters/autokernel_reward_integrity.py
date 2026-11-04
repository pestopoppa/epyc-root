"""Project prospective AutoKernel reward-integrity corpus measurements.

Historical executable-corpus v1 receipts remain measurement evidence in their
native domain, but they predate producer-authored ``belief_measurements`` and
therefore project to no Vidya claims.  Only complete v2 successor receipts are
eligible.  This adapter independently re-derives the detector population, all
50 exact case/ranked-unit elapsed observations, source and binary identities,
released device claim, producer and row hashes, and the instrument-validation
authority boundary before projecting through the shared measurement ladder.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_reward_integrity/v1"
LEGACY_SCHEMA = "epyc.autokernel.executable-reward-hack-corpus.v1"
SOURCE_SCHEMA = "epyc.autokernel.executable-reward-hack-corpus.v2"
PURPOSE = "instrument validation only; no candidate speed claim"
PRODUCER_ID = "autokernel.execution.reward_hack_corpus/v2"
PRODUCER_PATH = "scripts/kernel_rnd/autokernel/execution/reward_hack_corpus.py"
DEVICE_ID = "mi210_0"
KERNEL_REPETITIONS = 128
PLANTED_CASES = {
    "frame-timer": 1,
    "frame-sync": 2,
    "pointer-map": 3,
    "pointer-key": 4,
    "known-shape": 5,
    "structured-input": 6,
    "environment": 7,
    "timing": 8,
    "side-stream": 9,
    "async-thread": 10,
}
CLEAN_CASES = {f"clean-{index:02d}": 0 for index in range(1, 16)}
EXPECTED_CASES = {**PLANTED_CASES, **CLEAN_CASES}
EXPECTED_UNITS = {
    "normal-128": ("normal", 128),
    "anti-short-circuit-127": ("anti_short_circuit", 127),
}
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
        raise ProjectionError(f"reward-integrity receipt is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{label} must be an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{label} must be non-empty text")
    return value.strip()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProjectionError(f"{label} must be a positive integer")
    return value


def _finite(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or (positive and value <= 0):
        qualifier = "positive " if positive else ""
        raise ProjectionError(f"{label} must be a {qualifier}finite number")
    return float(value)


def _contains_authority(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_AUTHORITY.search(str(key).replace("_", " "))
                   or _contains_authority(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_authority(child) for child in value)
    return False


def _timestamp(value: Any, label: str) -> datetime:
    text = _text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ProjectionError(f"{label} must carry a timezone")
    return parsed


def _claim_identity(receipt: dict) -> tuple[dict, str]:
    opened = _mapping(receipt.get("device_claim_open"), "device_claim_open")
    released = _mapping(receipt.get("device_claim_released"), "device_claim_released")
    if opened.get("schema") != "epyc.autokernel.device_claim_receipt.v1":
        raise ProjectionError("device claim has an unsupported schema")
    if opened.get("released_at") is not None:
        raise ProjectionError("opened device claim is already marked released")
    released_at = _timestamp(
        released.get("released_at"), "device_claim_released.released_at")
    replayed_open = dict(released)
    replayed_open["released_at"] = None
    if replayed_open != opened:
        raise ProjectionError("device claim identity changed across release")
    if (opened.get("device_id") != DEVICE_ID
            or opened.get("campaign_id") != receipt.get("campaign_id")
            or opened.get("state") not in {"held", "draining"}):
        raise ProjectionError("device claim does not bind the declared MI210 campaign")
    _text(opened.get("claim_id"), "device_claim_open.claim_id")
    acquired_at = _timestamp(opened.get("acquired_at"), "device_claim_open.acquired_at")
    if released_at <= acquired_at:
        raise ProjectionError("device claim release does not follow acquisition")
    identity = {"opened": opened, "released": released}
    digest = _canonical_sha256(identity)
    if receipt.get("device_claim_identity_sha256") != digest:
        raise ProjectionError("device_claim_identity_sha256 does not bind claim receipts")
    return identity, digest


def _sampling_identity(receipt: dict, claim_identity: dict) -> tuple[dict, str]:
    sampling = _mapping(receipt.get("device_sampling"), "device_sampling")
    unsigned = dict(sampling)
    stored = unsigned.pop("sha256", None)
    digest = _canonical_sha256(unsigned)
    if _sha(stored, "device_sampling.sha256") != digest:
        raise ProjectionError("device sampling self-hash does not bind its window")
    if (sampling.get("schema") != "epyc.autokernel.device_sampling_receipt.v1"
            or sampling.get("sampler_id") != "autokernel.execution.device_sampler/v1"
            or sampling.get("device_id") != "ROCm0"):
        raise ProjectionError("device sampling does not identify the governed ROCm0 sampler")
    command = sampling.get("command")
    if not isinstance(command, list) or command[1:3] != ["-d", "0"]:
        raise ProjectionError("device sampling command does not target ROCm0")
    interval = _finite(sampling.get("interval_s"), "device_sampling.interval_s", positive=True)
    duration = _finite(sampling.get("duration_s"), "device_sampling.duration_s", positive=True)
    max_gap = _finite(sampling.get("max_gap_s"), "device_sampling.max_gap_s")
    samples = sampling.get("samples")
    if (not isinstance(samples, list) or not samples
            or sampling.get("sample_count") != len(samples)
            or max_gap < 0 or max_gap > 2.0 * interval):
        raise ProjectionError("device sampling coverage or cadence is incomplete")
    offsets = []
    for index, value in enumerate(samples):
        sample = _mapping(value, f"device_sampling.samples[{index}]")
        offsets.append(_finite(sample.get("offset_s"), "sample.offset_s"))
        for key in ("power_w", "sclk_mhz", "mclk_mhz", "temperature_c"):
            _finite(sample.get(key), f"sample.{key}", positive=True)
        if sample.get("under_measurement_load") is not True:
            raise ProjectionError("device sample is outside the declared measurement window")
    if offsets != sorted(offsets) or offsets[0] < 0 or duration < offsets[-1]:
        raise ProjectionError("device sampling offsets do not fit the declared window")
    started = _timestamp(sampling.get("started_at"), "device_sampling.started_at")
    ended = _timestamp(sampling.get("ended_at"), "device_sampling.ended_at")
    acquired = _timestamp(
        claim_identity["opened"].get("acquired_at"), "device_claim_open.acquired_at")
    released = _timestamp(
        claim_identity["released"].get("released_at"),
        "device_claim_released.released_at")
    if not acquired <= started < ended <= released:
        raise ProjectionError("device sampling window is not contained by the MI210 claim")
    return sampling, digest


def _producer(receipt: dict) -> dict:
    producer = _mapping(receipt.get("producer"), "producer")
    expected = {
        "producer_id": PRODUCER_ID,
        "path": PRODUCER_PATH,
        "sha256": _sha(producer.get("sha256"), "producer.sha256"),
    }
    if producer != expected:
        raise ProjectionError("reward-integrity receipt names a different producer")
    return expected


def _case_identity(row: dict) -> dict:
    return {
        "case_id": _text(row.get("case_id"), "case.case_id"),
        "label": _text(row.get("label"), "case.label"),
        "mode": row.get("mode"),
        "source": _text(row.get("source"), "case.source"),
        "source_sha256": _sha(row.get("source_sha256"), "case.source_sha256"),
        "binary": _text(row.get("binary"), "case.binary"),
        "binary_sha256": _sha(row.get("binary_sha256"), "case.binary_sha256"),
    }


def _unit_identity(unit: dict, *, binary: str) -> tuple[dict, dict]:
    unit_id = _text(unit.get("unit_id"), "ranked_unit.unit_id")
    if unit_id not in EXPECTED_UNITS:
        raise ProjectionError(f"unknown ranked-unit identity {unit_id!r}")
    kind, n = EXPECTED_UNITS[unit_id]
    identity = {
        "unit_id": unit_id,
        "kind": kind,
        "n": n,
        "argv": [binary, str(n)],
    }
    if any(unit.get(key) != value for key, value in identity.items()):
        raise ProjectionError(f"ranked unit {unit_id} identity differs")
    if unit.get("returncode") != 0:
        raise ProjectionError(f"ranked unit {unit_id} did not exit cleanly")
    _finite(unit.get("wall_duration_s"), "ranked_unit.wall_duration_s", positive=True)
    result = _mapping(unit.get("result"), "ranked_unit.result")
    if result.get("n") != n or result.get("repetitions") != KERNEL_REPETITIONS:
        raise ProjectionError(f"ranked unit {unit_id} result identity differs")
    _positive_int(result.get("repetitions"), "ranked_unit.result.repetitions")
    _finite(result.get("gpu_elapsed_ms"), "ranked_unit.result.gpu_elapsed_ms", positive=True)
    mismatches = result.get("mismatches")
    if isinstance(mismatches, bool) or not isinstance(mismatches, int) or mismatches < 0:
        raise ProjectionError("ranked-unit mismatch count must be a non-negative integer")
    return identity, result


def _measurement(*, measurement_id: str, metric: str, value: float,
                 unit: str, direction: str, reps: int, reps_basis: str,
                 claim: str, extra: Mapping[str, Any]) -> dict:
    row = {
        "measurement_id": measurement_id,
        "metric": metric,
        "value": value,
        "unit": unit,
        "metric_direction": direction,
        "category": "BASELINE",
        "protocol_id": SOURCE_SCHEMA,
        "reps": reps,
        "reps_basis": reps_basis,
        "claim": claim,
        "extra": dict(extra),
    }
    row["measurement_sha256"] = _canonical_sha256(row)
    return row


def _expected_rows(receipt: dict) -> list[dict]:
    producer = _producer(receipt)
    claim_identity, claim_sha = _claim_identity(receipt)
    _sampling, sampling_sha = _sampling_identity(receipt, claim_identity)
    host = _mapping(receipt.get("host"), "host")
    hipcc = _text(host.get("hipcc"), "host.hipcc")
    cases = receipt.get("cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_CASES):
        raise ProjectionError("reward-integrity receipt must carry exactly 25 cases")
    if not isinstance(receipt.get("attempt_history"), list):
        raise ProjectionError("reward-integrity receipt lacks explicit attempt history")

    case_identities = []
    detector_observations = []
    unit_evidence: list[tuple[dict, dict, dict, dict]] = []
    seen = set()
    true_positives = false_positives = runtime_ok = 0
    for row_index, value in enumerate(cases):
        case = _mapping(value, f"cases[{row_index}]")
        identity = _case_identity(case)
        case_id = identity["case_id"]
        if case_id in seen or case_id not in EXPECTED_CASES:
            raise ProjectionError("case identities are duplicated or outside the declared corpus")
        seen.add(case_id)
        expected_label = "planted" if case_id in PLANTED_CASES else "clean"
        if (identity["label"] != expected_label
                or identity["mode"] != EXPECTED_CASES[case_id]
                or case.get("compile_returncode") != 0):
            raise ProjectionError(f"case {case_id} label, mode, or compilation differs")
        expected_compile = [
            hipcc, "--offload-arch=gfx90a", "-O2", "-pthread",
            identity["source"], "-o", identity["binary"],
        ]
        if case.get("compile_argv") != expected_compile:
            raise ProjectionError(f"case {case_id} compile identity differs")
        _finite(case.get("compile_duration_s"), "case.compile_duration_s", positive=True)
        findings = _mapping(case.get("findings"), f"case {case_id}.findings")
        if not findings or not all(isinstance(items, list) for items in findings.values()):
            raise ProjectionError(f"case {case_id} scanner findings are malformed")
        detected = any(bool(items) for items in findings.values())
        if case.get("detected") is not detected:
            raise ProjectionError(f"case {case_id} detector result does not re-derive")
        if case.get("runtime_behavior_manifested") is not True:
            raise ProjectionError(f"case {case_id} did not manifest its declared runtime behavior")
        ranked_units = case.get("ranked_units")
        if not isinstance(ranked_units, list) or len(ranked_units) != 2:
            raise ProjectionError(f"case {case_id} must retain exactly two ranked units")
        unit_ids = {unit.get("unit_id") for unit in ranked_units if isinstance(unit, dict)}
        if unit_ids != set(EXPECTED_UNITS):
            raise ProjectionError(f"case {case_id} ranked-unit set differs")
        for unit_value in ranked_units:
            unit = _mapping(unit_value, f"case {case_id} ranked unit")
            unit_identity, result = _unit_identity(unit, binary=identity["binary"])
            mismatches = result["mismatches"]
            if (mismatches > 0) is not (expected_label == "planted"):
                raise ProjectionError(f"case {case_id} runtime oracle does not re-derive")
            unit_evidence.append((identity, unit_identity, result, unit))
        case_identities.append(identity)
        detector_observations.append({
            "case_id": case_id,
            "label": expected_label,
            "detected": detected,
            "findings_sha256": _canonical_sha256(findings),
            "runtime_behavior_manifested": True,
        })
        true_positives += int(expected_label == "planted" and detected)
        false_positives += int(expected_label == "clean" and detected)
        runtime_ok += 1
    if seen != set(EXPECTED_CASES):
        raise ProjectionError("reward-integrity corpus case coverage differs")

    corpus = {
        "planted": len(PLANTED_CASES),
        "clean": len(CLEAN_CASES),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "sensitivity": true_positives / len(PLANTED_CASES),
        "specificity": (len(CLEAN_CASES) - false_positives) / len(CLEAN_CASES),
        "false_positive_rate": false_positives / len(CLEAN_CASES),
        "runtime_behavior_manifested": runtime_ok,
        "runtime_behavior_total": len(EXPECTED_CASES),
    }
    if receipt.get("corpus") != corpus:
        raise ProjectionError("corpus summary does not re-derive from native cases")
    if receipt.get("ranked_set") != {
            "unit_ids": ["normal-128", "anti-short-circuit-127"],
            "both_units_measured_for_every_program": True}:
        raise ProjectionError("ranked-set declaration differs from native case coverage")

    common = {
        "campaign_id": receipt["campaign_id"],
        "purpose": PURPOSE,
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
        "corpus": corpus,
        "producer_sha256": producer["sha256"],
        "device_claim_identity_sha256": claim_sha,
        "device_sampling_sha256": sampling_sha,
    }
    population_sha = _canonical_sha256(population)
    rows = []
    for measurement_id, metric, value, direction, reps, reps_basis in (
            ("reward_integrity_detector_sensitivity",
             "autokernel_reward_integrity_detector_sensitivity",
             corpus["sensitivity"], "higher_better", len(PLANTED_CASES),
             "scored:planted executable cases"),
            ("reward_integrity_detector_specificity",
             "autokernel_reward_integrity_detector_specificity",
             corpus["specificity"], "higher_better", len(CLEAN_CASES),
             "scored:clean executable cases"),
            ("reward_integrity_detector_false_positive_rate",
             "autokernel_reward_integrity_detector_false_positive_rate",
             corpus["false_positive_rate"], "lower_better", len(CLEAN_CASES),
             "scored:clean executable cases")):
        rows.append(_measurement(
            measurement_id=measurement_id, metric=metric, value=value,
            unit="fraction", direction=direction, reps=reps, reps_basis=reps_basis,
            claim=(f"AutoKernel reward-integrity instrument observed {metric}={value:.9g} "
                   f"across {reps} scored cases; instrument validation only"),
            extra={**common, "evidence_basis": population,
                   "evidence_sha256": population_sha}))

    for case_identity, unit_identity, result, unit in unit_evidence:
        evidence = {
            "case_identity": case_identity,
            "ranked_unit_identity": unit_identity,
            "result": result,
            "returncode": unit["returncode"],
            "runtime_behavior_manifested": True,
            "producer_sha256": producer["sha256"],
            "device_claim_identity_sha256": claim_sha,
            "device_sampling_sha256": sampling_sha,
        }
        elapsed = float(result["gpu_elapsed_ms"])
        rows.append(_measurement(
            measurement_id=(f"reward_integrity_gpu_elapsed_ms__{case_identity['case_id']}__"
                            f"{unit_identity['unit_id']}"),
            metric="autokernel_reward_integrity_ranked_unit_gpu_elapsed_ms",
            value=elapsed, unit="ms", direction="lower_better",
            reps=KERNEL_REPETITIONS,
            reps_basis="scored:HIP kernel launches in one ranked unit",
            claim=(f"AutoKernel reward-integrity case {case_identity['case_id']} "
                   f"{unit_identity['unit_id']} observed {elapsed:.9g} ms across "
                   f"{KERNEL_REPETITIONS} launches; instrument validation only, "
                   "not candidate speed"),
            extra={**common, "case_identity": case_identity,
                   "ranked_unit_identity": unit_identity,
                   "evidence_basis": evidence,
                   "evidence_sha256": _canonical_sha256(evidence)}))
    return rows


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return producer-authored successor rows; never retrofit a v1 receipt."""
    if not isinstance(receipt, dict):
        raise ProjectionError("reward-integrity receipt must be an object")
    schema = receipt.get("schema")
    if schema == LEGACY_SCHEMA:
        if "belief_measurements" in receipt:
            raise ProjectionError("legacy reward-integrity schema may not carry belief rows")
        return ()
    if schema != SOURCE_SCHEMA:
        raise ProjectionError("unsupported reward-integrity receipt schema")
    if receipt_sha256:
        _sha(receipt_sha256, "receipt_sha256")
    if (receipt.get("status") != "complete" or receipt.get("purpose") != PURPOSE
            or not _text(receipt.get("campaign_id"), "receipt.campaign_id")
            or not _text(receipt.get("ended_at"), "receipt.ended_at")):
        raise ProjectionError("only a complete instrument-validation receipt is eligible")
    if _contains_authority(receipt):
        raise ProjectionError("reward-integrity receipt may not carry promotion/release authority")
    unsigned = dict(receipt)
    stored = unsigned.pop("receipt_sha256", None)
    if _sha(stored, "receipt.receipt_sha256") != _canonical_sha256(unsigned):
        raise ProjectionError("receipt_sha256 does not bind the logical receipt")
    rows = receipt.get("belief_measurements")
    if not isinstance(rows, list) or not rows:
        raise ProjectionError("current reward-integrity schema must carry producer rows")
    expected = _expected_rows(receipt)
    if rows != expected:
        raise ProjectionError("producer rows do not re-derive from native reward-integrity evidence")
    return tuple({
        "receipt": receipt,
        "measurement": row,
        "measurement_index": index,
        "receipt_locator": receipt_locator,
        "receipt_sha256": receipt_sha256,
        "attestation_present": attestation_present,
    } for index, row in enumerate(rows))


@register("autokernel-reward-integrity-measurement")
def project(native: Any) -> ClaimTuple:
    """Project one revalidated native row through the shared measurement ladder."""
    if not isinstance(native, dict):
        raise ProjectionError("reward-integrity native row must be an object")
    receipt = _mapping(native.get("receipt"), "native.receipt")
    rows = native_rows(
        receipt,
        receipt_locator=str(native.get("receipt_locator") or ""),
        receipt_sha256=str(native.get("receipt_sha256") or ""),
        attestation_present=native.get("attestation_present"))
    index = native.get("measurement_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(rows):
        raise ProjectionError("native measurement_index is invalid")
    expected = rows[index]
    if native.get("measurement") != expected["measurement"]:
        raise ProjectionError("native reward-integrity row was mutated after validation")
    row = expected["measurement"]
    campaign = receipt["campaign_id"]
    local_id = row["measurement_id"]
    identity = hashlib.sha256(json.dumps(
        [SOURCE_SCHEMA, campaign, local_id], separators=(",", ":"),
        ensure_ascii=True).encode()).hexdigest()[:24]
    return ClaimTuple(
        measurement_id=f"akreward_{identity}",
        metric=row["metric"],
        value=row["value"],
        date=str(receipt["ended_at"])[:10],
        category=row["category"],
        claim=row["claim"],
        metric_direction=row["metric_direction"],
        protocol_id=row["protocol_id"],
        reps=row["reps"],
        reps_basis=row["reps_basis"],
        unit=row["unit"],
        attestation_sha256=str(native.get("receipt_sha256") or ""),
        attestation_locator=str(native.get("receipt_locator") or ""),
        attestation_present=native.get("attestation_present"),
        source_kind="autokernel-reward-integrity-measurement",
        extra={
            "source_schema": SOURCE_SCHEMA,
            "campaign_id": campaign,
            "native_measurement_id": local_id,
            "native_measurement_sha256": row["measurement_sha256"],
            "receipt_self_sha256": receipt["receipt_sha256"],
            **row["extra"],
        },
    )


__all__ = [
    "ADAPTER_ID", "LEGACY_SCHEMA", "SOURCE_SCHEMA", "native_rows", "project",
]

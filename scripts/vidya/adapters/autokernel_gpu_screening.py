"""Project prospective AutoKernel GPU discovery baseline/candidate screens.

The 2026-08-13 MMQ-MFMA s2 screen predates the producer hook and therefore
emits zero rows; it is never reconstructed on read.  Successor screens
(``epyc.autokernel.gpu_screening_baseline.v2`` and
``epyc.autokernel.gpu_candidate_only_screen.v2``) carry producer-authored
``belief_measurements`` sealed by ``baseline_sha256``/``result_sha256``.  This
reader independently re-derives every binding — source/build/binary/linkage/
model/device identity, sole-factor identity, scored invocation basis, KFD/VRAM
residency, baseline/result hashes, authority boundary — and projects only the
exactly-rederiving producer rows through the shared measurement ladder.  It
never grades: ``claim_tuple.grade()`` decides, and no second ladder exists.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_gpu_screening/v1"
PROJECTION_SCHEMA = "epyc.vidya.autokernel_gpu_screening_measurements.v1"
SOURCE_SCHEMAS = frozenset({
    "epyc.autokernel.gpu_screening_baseline.v2",
    "epyc.autokernel.gpu_candidate_only_screen.v2",
})
BANK_SCHEMA = "epyc.autokernel.gpu_screening_baseline.v2"
RESULT_SCHEMA = "epyc.autokernel.gpu_candidate_only_screen.v2"
# The v1 screens (2026-08-13 s1/s2 and successors until the hook landed)
# predate the producer-authored belief rows.  They are never reconstructed on
# read: they emit zero rows, always.
PRE_HOOK_SCHEMAS = frozenset({
    "epyc.autokernel.gpu_screening_baseline.v1",
    "epyc.autokernel.gpu_candidate_only_screen.v1",
})
PRODUCER_ID = "scripts.benchmark.run_autokernel_gpu_discovery/v4"
PRODUCER_PATH = "scripts/benchmark/run_autokernel_gpu_discovery.py"
AUTHORITY = "nonpromotable_candidate_only_discovery"
NOMINATION = "top_k_candidate_only_not_a_keep"
ALLOWED_REPS = frozenset({3, 5, 9})
NATIVE_CONTRACT = "epyc.autokernel.native_llama_bench_metric.v1"
SERIALIZED_CONTRACT = "epyc.autokernel.serialized_pair_max_metric.v1"
CONTRACTS = frozenset({NATIVE_CONTRACT, SERIALIZED_CONTRACT})
RECIPES = {
    "pp512-ngl99": "prefill_tokens_per_s",
    "tg128-ngl99": "decode_tokens_per_s",
}
LABELS = {"pp512-ngl99": "pp512", "tg128-ngl99": "tg128"}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

# Sole-factor families the v4 producer's factor_spec can emit:
# name -> (anchor, candidate).  Tuple/string membership is type-exact.
_FACTOR_PAIRS = {
    "GGML_HIP_MMQ_MFMA": ("ON", "OFF"),
    "flash_attention": ("OFF", "ON"),
    "GGML_HIP_ROCWMMA_FATTN": ("OFF", "ON"),
    "GGML_HIP_GRAPHS": ("ON", "OFF"),
    "mmap": ("ON", "OFF"),
    "op_offload": ("ON", "OFF"),
    "split_mode": ("layer", "row"),
    "kv_offload": ("ON", "OFF"),
}
_FACTOR_SETS = {
    "gpu_helper_threads": (8, {4, 12, 16, 24}),
    "batch_size": (512, {256, 1024}),
    "ubatch_size": (512, {256, 1024}),
    "gpu_poll": (50, {0}),
}
# These factors run one identical sealed build on both arms.
_IDENTICAL_BUILD_FACTORS = frozenset({
    "flash_attention", "gpu_helper_threads", "batch_size", "ubatch_size",
    "mmap", "op_offload", "split_mode", "kv_offload", "gpu_poll",
})


def _canonical_sha(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectionError(
            f"GPU screening receipt is not canonical JSON: {exc}") from exc
    return hashlib.sha256(raw).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{label} must be an object")
    return value


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value <= 0:
        raise ProjectionError(f"{label} must be a positive finite number")
    return float(value)


def _samples(value: Any, label: str, *, expected: int) -> list[float]:
    if not isinstance(value, list) or len(value) != expected:
        raise ProjectionError(f"{label} must contain exactly {expected} samples")
    result = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)) \
                or not math.isfinite(item) or item <= 0:
            raise ProjectionError(f"{label}[{index}] must be positive and finite")
        result.append(float(item))
    return result


def _validate_identity(identity: Any, label: str) -> dict:
    identity = _mapping(identity, label)
    commit = _COMMIT.fullmatch(str(identity.get("source_commit", "")))
    if not commit:
        raise ProjectionError(f"{label}.source_commit must be a 40-hex commit")
    for key in ("hip_graphs", "rocwmma_fattn", "mmq_mfma"):
        if not isinstance(identity.get(key), bool):
            raise ProjectionError(f"{label}.{key} must be a boolean build setting")
    artifacts = _mapping(identity.get("artifacts"), f"{label}.artifacts")
    if not isinstance(artifacts.get("binary"), str) or not artifacts["binary"]:
        raise ProjectionError(f"{label}.artifacts.binary is required")
    _sha(artifacts.get("binary_sha256"), f"{label}.artifacts.binary_sha256")
    libraries = artifacts.get("libraries")
    if not isinstance(libraries, dict) or not libraries:
        raise ProjectionError(f"{label}.artifacts.libraries must name at least one DSO")
    for name, digest in libraries.items():
        if not isinstance(name, str) or not name:
            raise ProjectionError(f"{label}.artifacts.libraries key is invalid")
        _sha(digest, f"{label}.artifacts.libraries[{name!r}]")
    return identity


def _validate_frame(frame: Any) -> dict:
    frame = _mapping(frame, "frame")
    if frame.get("backend") != "llama_gpu":
        raise ProjectionError("GPU screening frame is not a llama_gpu frame")
    recipe = frame.get("recipe")
    if recipe not in RECIPES or frame.get("metric") != RECIPES[recipe]:
        raise ProjectionError("GPU screening frame recipe/metric do not match")
    if frame.get("metric_direction") != "higher_better":
        raise ProjectionError("GPU screening frame metric direction is not higher_better")
    if frame.get("device") != "AMD Instinct MI210" \
            or frame.get("architecture") != "gfx90a":
        raise ProjectionError("GPU screening frame is not the sealed MI210/gfx90a device")
    if not _COMMIT.fullmatch(str(frame.get("source_commit", ""))):
        raise ProjectionError("GPU screening frame lacks its exact source commit")
    if not isinstance(frame.get("model"), str) or not frame["model"]:
        raise ProjectionError("GPU screening frame lacks its model identity")
    _sha(frame.get("model_sha256"), "frame.model_sha256")
    if not isinstance(frame.get("cpu_list"), str) or not frame["cpu_list"]:
        raise ProjectionError("GPU screening frame lacks its cpu_list")
    for key in ("n_prompt", "n_gen"):
        if isinstance(frame.get(key), bool) or not isinstance(frame.get(key), int) \
                or frame.get(key) <= 0:
            raise ProjectionError(f"GPU screening frame.{key} must be a positive integer")
    contract = _mapping(frame.get("metric_contract"), "frame.metric_contract")
    if contract.get("schema") not in CONTRACTS:
        raise ProjectionError("GPU screening frame names an unknown metric contract")
    return frame


def _validate_sole_factor(factor: Any, *, anchor: dict | None = None,
                          candidate: dict | None = None) -> dict:
    """Validate the admitted transition and, per available arm, its identity.

    The bank carries both arm identities; the candidate result carries only
    ``candidate_identity`` (the anchor lives in the sealed bank its
    ``baseline_sha256`` binds).  Identity-dependent checks run only for the
    arms actually present in the receipt.
    """
    factor = _mapping(factor, "sole_factor")
    if set(factor) != {"name", "anchor", "candidate"}:
        raise ProjectionError("sole_factor must have exact name/anchor/candidate identity")
    name, anchor_value, candidate_value = (
        factor["name"], factor["anchor"], factor["candidate"])
    if name in _FACTOR_PAIRS:
        pair = _FACTOR_PAIRS[name]
        if (anchor_value, candidate_value) != pair:
            raise ProjectionError(
                f"sole factor {name} is not its admitted {pair[0]}->{pair[1]} transition")
    elif name in _FACTOR_SETS:
        anchor_expected, candidates = _FACTOR_SETS[name]
        if anchor_value != anchor_expected or candidate_value not in candidates:
            raise ProjectionError(
                f"sole factor {name} is not an admitted anchor/candidate configuration")
    elif name == "source_patch":
        if (not isinstance(anchor_value, str) or len(anchor_value) != 12
                or not isinstance(candidate_value, str) or len(candidate_value) != 12
                or anchor_value == candidate_value):
            raise ProjectionError("source_patch factor must carry two distinct 12-hex commits")
        if candidate is not None and candidate["source_commit"][:12] != candidate_value:
            raise ProjectionError("source_patch factor does not bind the candidate source commit")
        if anchor is not None:
            if anchor["source_commit"][:12] != anchor_value:
                raise ProjectionError("source_patch factor does not bind the anchor source commit")
            for key in ("hip_graphs", "rocwmma_fattn", "mmq_mfma"):
                if anchor[key] != candidate[key]:
                    raise ProjectionError(
                        "source_patch arms must keep build settings identical")
        return factor
    else:
        raise ProjectionError(f"sole factor {name!r} is not an admitted factor transition")
    if name == "GGML_HIP_MMQ_MFMA":
        if candidate["rocwmma_fattn"] is not True or candidate["mmq_mfma"] is not False:
            raise ProjectionError("MMQ candidate identity does not bind r1m0")
        if anchor is not None and (
                anchor["rocwmma_fattn"] is not True or anchor["mmq_mfma"] is not True):
            raise ProjectionError("MMQ anchor identity does not bind r1m1")
    elif name == "flash_attention":
        if anchor is not None and anchor != candidate:
            raise ProjectionError("flash-attention screen must use one identical build")
        if anchor is not None and (
                anchor["rocwmma_fattn"] is not True or anchor["mmq_mfma"] is not False):
            raise ProjectionError("flash-attention screen requires the r1m0 build")
        if candidate["rocwmma_fattn"] is not True or candidate["mmq_mfma"] is not False:
            raise ProjectionError("flash-attention candidate identity does not bind r1m0")
    elif name == "GGML_HIP_ROCWMMA_FATTN":
        if candidate["mmq_mfma"] is not False or candidate["rocwmma_fattn"] is not True:
            raise ProjectionError("ROCWMMA candidate identity does not bind r0m1")
        if anchor is not None and (
                anchor["mmq_mfma"] is not False or anchor["rocwmma_fattn"] is not False):
            raise ProjectionError("ROCWMMA anchor identity does not bind r0m0")
    elif name == "GGML_HIP_GRAPHS":
        if candidate["hip_graphs"] is not False:
            raise ProjectionError("HIP graphs candidate identity does not bind graphs off")
        if anchor is not None:
            if anchor["hip_graphs"] is not True:
                raise ProjectionError("HIP graphs anchor identity does not bind graphs on")
            if anchor["rocwmma_fattn"] != candidate["rocwmma_fattn"] \
                    or anchor["mmq_mfma"] != candidate["mmq_mfma"]:
                raise ProjectionError(
                    "HIP graphs arms must keep ROCWMMA/MMQ settings identical")
    elif name in _IDENTICAL_BUILD_FACTORS and anchor is not None and anchor != candidate:
        raise ProjectionError(f"{name} screen requires one identical sealed build")
    return factor


def _validate_run(run: Any, *, samples: list[float], reps: int, arm: str) -> dict:
    run = _mapping(run, f"{arm}_run")
    if run.get("samples") != samples or run.get("sample_count") != reps:
        raise ProjectionError(f"{arm} run does not bind the native raw sample vector")
    if run.get("hip_residency_proved") is not True:
        raise ProjectionError(f"{arm} run does not prove HIP residency")
    residency = run.get("residency")
    if not isinstance(residency, list) or not residency:
        raise ProjectionError(f"{arm} run lacks its KFD/VRAM residency sample vector")
    owned_kfd = False
    vram_resident = False
    for index, sample in enumerate(residency):
        sample = _mapping(sample, f"{arm}_run.residency[{index}]")
        pids = sample.get("owned_kfd_pids")
        if not isinstance(pids, list) or not all(
                isinstance(pid, int) and not isinstance(pid, bool) and pid > 0
                for pid in pids):
            raise ProjectionError(
                f"{arm}_run.residency[{index}].owned_kfd_pids must list positive PIDs")
        if pids:
            owned_kfd = True
        vram = sample.get("vram_used_bytes")
        if isinstance(vram, bool) or not isinstance(vram, int) or vram < 0:
            raise ProjectionError(
                f"{arm}_run.residency[{index}].vram_used_bytes must be a byte count")
        if vram > 0:
            vram_resident = True
    if not owned_kfd:
        raise ProjectionError(f"{arm} run has no owned KFD residency sample")
    if not vram_resident:
        raise ProjectionError(f"{arm} run has no positive VRAM residency delta")
    return run


def _common(receipt: dict, *, samples: list[float],
            producer: dict, frame: dict, factor: dict) -> dict:
    evidence = {
        "campaign_id": receipt.get("campaign_id"), "authority": AUTHORITY,
        "frame": frame, "sole_factor": factor, "samples": samples,
        "producer_sha256": producer["sha256"],
    }
    return {
        "authority": AUTHORITY, "non_promotable": True,
        "top_k_discovery_only": True, "promotion_authority": False,
        "production_tree_touched": False, "frame": frame, "sole_factor": factor,
        "producer_id": producer["producer_id"],
        "producer_sha256": producer["sha256"], "evidence_basis": evidence,
        "evidence_sha256": _canonical_sha(evidence),
    }


def _row(*, measurement_id: str, metric: str, value: float, unit: str,
         category: str, claim: str, reps_basis: str, extra: dict,
         protocol_id: str, reps: int) -> dict:
    row = {
        "measurement_id": measurement_id, "metric": metric, "value": value,
        "unit": unit, "metric_direction": "higher_better", "category": category,
        "protocol_id": protocol_id, "reps": reps, "reps_basis": reps_basis,
        "claim": claim, "extra": dict(extra),
    }
    row["measurement_sha256"] = _canonical_sha(row)
    return row


def _baseline_center(frame: dict, *, samples: list[float], run: dict) -> float:
    if frame["metric_contract"]["schema"] == SERIALIZED_CONTRACT:
        return _positive(run.get("metric"),
                         "serialized pair-max run metric (mean protected latency)")
    return sum(samples) / len(samples)


def _expected_rows(receipt: dict, *, samples: list[float], reps: int,
                   runs: list[dict], producer: dict, frame: dict,
                   factor: dict) -> list[dict]:
    common = _common(receipt, samples=samples, producer=producer,
                     frame=frame, factor=factor)
    label = LABELS[frame["recipe"]]
    metric = frame["metric"]
    if receipt["schema"] == BANK_SCHEMA:
        common.update({"arm": "anchor",
                       "build_identity": receipt["anchor_identity"]})
        center = _baseline_center(frame, samples=samples, run=runs[0])
        return [_row(
            measurement_id=f"gpu_discovery_anchor_{label}_median_tokens_per_s",
            metric=f"gpu_{metric}", value=statistics.median(samples),
            unit="tokens/s", category="BASELINE",
            claim=(f"Non-promotable GPU discovery anchor observed median {label} throughput "
                   f"{statistics.median(samples):.9g} tokens/s"),
            reps_basis=f"scored:{reps} anchor-bank MI210 llama-bench native repetitions",
            extra={**common, "sealed_baseline_center": center,
                   "baseline_center_method": (
                       "tokens_per_mean_protected_latency"
                       if frame["metric_contract"]["schema"] == SERIALIZED_CONTRACT
                       else "arithmetic_mean_native_samples")},
            protocol_id=BANK_SCHEMA, reps=reps)]
    center = _positive(receipt.get("baseline_center"), "baseline_center")
    effects = [(value - center) / center for value in samples]
    common.update({
        "arm": "candidate", "build_identity": receipt["candidate_identity"],
        "baseline_sha256": receipt["baseline_sha256"],
        "baseline_anchor_samples": receipt["baseline_anchor_samples"],
        "baseline_center": center, "hip_residency_proved": True,
    })
    basis = f"scored:{reps} candidate-only MI210 llama-bench invocations"
    return [
        _row(
            measurement_id=f"gpu_discovery_candidate_{label}_median_tokens_per_s",
            metric=f"gpu_{metric}", value=statistics.median(samples),
            unit="tokens/s", category="CANDIDATE",
            claim=(f"Non-promotable GPU candidate discovery observed median {label} throughput "
                   f"{statistics.median(samples):.9g} tokens/s"),
            reps_basis=basis, extra=common, protocol_id=RESULT_SCHEMA, reps=reps),
        _row(
            measurement_id=f"gpu_discovery_candidate_{label}_median_relative_effect",
            metric=f"gpu_{metric.removesuffix('_tokens_per_s')}_relative_effect_vs_sealed_anchor",
            value=statistics.median(effects), unit="fraction", category="CANDIDATE",
            claim=("Non-promotable GPU candidate discovery observed median relative effect "
                   f"{statistics.median(effects):.9g} versus its sealed anchor bank"),
            reps_basis=basis, extra={**common, "relative_effects": effects},
            protocol_id=RESULT_SCHEMA, reps=reps),
    ]


def _validate_receipt(receipt: dict) -> list[dict]:
    if receipt.get("authority") != AUTHORITY:
        raise ProjectionError("GPU screening receipt upgrades its non-promotable authority")
    if not isinstance(receipt.get("campaign_id"), str) or not receipt["campaign_id"]:
        raise ProjectionError("GPU screening receipt lacks its campaign identity")
    producer = _mapping(receipt.get("producer"), "producer")
    if (producer.get("producer_id") != PRODUCER_ID
            or producer.get("path") != PRODUCER_PATH):
        raise ProjectionError("GPU screening receipt names another producer")
    _sha(producer.get("sha256"), "producer.sha256")
    frame = _validate_frame(receipt.get("frame"))
    factor = _validate_sole_factor(receipt.get("sole_factor"),
                                   anchor=receipt.get("anchor_identity"),
                                   candidate=receipt.get("candidate_identity"))
    schema = receipt["schema"]
    self_field = "baseline_sha256" if schema == BANK_SCHEMA else "result_sha256"
    claimed = _sha(receipt.get(self_field), f"receipt.{self_field}")
    unsigned = {key: value for key, value in receipt.items() if key != self_field}
    if _canonical_sha(unsigned) != claimed:
        raise ProjectionError(f"GPU screening {self_field} does not bind its receipt")
    samples_key = "anchor_samples" if schema == BANK_SCHEMA else "candidate_samples"
    runs_key = "anchor_runs" if schema == BANK_SCHEMA else "candidate_runs"
    reps = receipt.get("anchor_invocations" if schema == BANK_SCHEMA
                       else "candidate_invocations")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps not in ALLOWED_REPS:
        raise ProjectionError("invocation count must be one of 3, 5, or 9")
    samples = _samples(receipt.get(samples_key), samples_key, expected=reps)
    runs = receipt.get(runs_key)
    if not isinstance(runs, list) or len(runs) != 1:
        raise ProjectionError(f"{runs_key} must contain exactly the one arm process")
    _validate_run(runs[0], samples=samples, reps=reps,
                  arm="anchor" if schema == BANK_SCHEMA else "candidate")
    candidate = _validate_identity(receipt.get("candidate_identity"),
                                   "candidate_identity")
    anchor = None
    if receipt.get("anchor_identity") is not None:
        anchor = _validate_identity(receipt.get("anchor_identity"), "anchor_identity")
    if schema == BANK_SCHEMA and anchor is None:
        raise ProjectionError("GPU baseline bank lacks its anchor identity")
    if schema == RESULT_SCHEMA:
        if (receipt.get("state") != "decided" or receipt.get("ok") is not True
                or receipt.get("non_promotable") is not True
                or receipt.get("promotion_claim") is not False
                or receipt.get("nomination") != NOMINATION
                or receipt.get("hip_residency_proved") is not True):
            raise ProjectionError("GPU candidate result upgrades or lacks its discovery boundary")
        if receipt.get("candidate_invocations") != receipt.get("anchor_invocations"):
            raise ProjectionError("candidate invocation count differs from the sealed bank")
        _sha(receipt.get("baseline_sha256"), "baseline_sha256")
        bank_samples = _samples(receipt.get("baseline_anchor_samples"),
                                "baseline_anchor_samples", expected=reps)
        center = receipt.get("baseline_center")
        if (isinstance(center, bool) or not isinstance(center, (int, float))
                or not math.isfinite(center) or center <= 0):
            raise ProjectionError("baseline_center must be positive and finite")
        if frame["metric_contract"]["schema"] == NATIVE_CONTRACT and not math.isclose(
                float(center), sum(bank_samples) / reps, rel_tol=1e-12, abs_tol=1e-12):
            raise ProjectionError("baseline_center does not rederive from anchor samples")
        effects = [(value - float(center)) / float(center) for value in samples]
        declared = receipt.get("relative_effects")
        if (not isinstance(declared, list) or len(declared) != reps
                or any(isinstance(item, bool) or not isinstance(item, (int, float))
                       or not math.isclose(float(item), expected,
                                           rel_tol=1e-12, abs_tol=1e-12)
                       for item, expected in zip(declared, effects))):
            raise ProjectionError("relative effects do not rederive from candidate and bank samples")
        if not math.isclose(float(receipt.get("median_relative")),
                            statistics.median(effects),
                            rel_tol=1e-12, abs_tol=1e-12):
            raise ProjectionError("median_relative does not rederive from the effect vector")
        opened = receipt.get("device_claim_open")
        if opened is not None:
            opened = _mapping(opened, "device_claim_open")
            if not isinstance(opened.get("claim_id"), str) or not opened["claim_id"] \
                    or not isinstance(opened.get("device_id"), str) \
                    or not opened["device_id"]:
                raise ProjectionError("device_claim_open lacks its claim identity")
        phase = receipt.get("device_claim_borrowed_phase_end")
        if phase is not None:
            phase = _mapping(phase, "device_claim_borrowed_phase_end")
            if (phase.get("schema") != "epyc.autokernel.borrowed_device_claim_phase.v1"
                    or phase.get("mode") != "borrowed_outer_reservation"
                    or phase.get("physical_release") is not False
                    or "released_at" in phase):
                raise ProjectionError("borrowed phase end claims a physical release")
    _validate_sole_factor(receipt.get("sole_factor"), anchor=anchor, candidate=candidate)
    return _expected_rows(receipt, samples=samples, reps=reps, runs=runs,
                          producer=producer, frame=frame, factor=factor)


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return only producer-written rows of a sealed GPU discovery screen.

    A pre-hook screen carries no ``belief_measurements`` and therefore emits
    zero rows; a post-hook screen must exactly re-derive or it is refused.
    """
    if not isinstance(receipt, dict) or receipt.get("schema") not in SOURCE_SCHEMAS:
        if isinstance(receipt, dict) and receipt.get("schema") in PRE_HOOK_SCHEMAS:
            return ()
        raise ProjectionError("unsupported GPU screening receipt schema")
    if receipt_sha256 and not _SHA.fullmatch(receipt_sha256):
        raise ProjectionError("receipt_sha256 must be a lowercase SHA-256 digest")
    if receipt.get("belief_measurements") is None:
        return ()
    if receipt.get("status") != "complete":
        raise ProjectionError("an incomplete GPU screen cannot carry belief rows")
    measurements = receipt["belief_measurements"]
    if not isinstance(measurements, list) or not measurements:
        raise ProjectionError("GPU screening v2 requires producer-written belief rows")
    expected = _validate_receipt(receipt)
    if measurements != expected:
        raise ProjectionError("GPU screening belief rows do not exactly rederive")
    return tuple({
        "receipt": receipt,
        "measurement": measurement,
        "measurement_index": index,
        "receipt_locator": receipt_locator,
        "receipt_sha256": receipt_sha256,
        "attestation_present": attestation_present,
    } for index, measurement in enumerate(measurements))


@register("autokernel-gpu-screening-measurement")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one producer-written GPU screen row; the shared ladder grades it."""
    if not isinstance(native, dict):
        raise ProjectionError("GPU screening native row must be an object")
    receipt = native.get("receipt")
    measurement = native.get("measurement")
    if not isinstance(receipt, dict) or not isinstance(measurement, dict):
        raise ProjectionError("GPU screening native row needs receipt and measurement dicts")
    schema = receipt.get("schema")
    if schema not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported GPU screening receipt schema")
    campaign_id = receipt.get("campaign_id")
    local_id = measurement.get("measurement_id")
    if not isinstance(campaign_id, str) or not isinstance(local_id, str):
        raise ProjectionError("GPU screening receipt or row lacks its identity")
    metric = measurement.get("metric")
    value = measurement.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise ProjectionError("GPU screening measurement value must be finite")
    reps = measurement.get("reps")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
        raise ProjectionError("GPU screening measurement reps must be a positive integer")
    index = native.get("measurement_index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ProjectionError("GPU screening measurement_index must be a non-negative integer")
    identity_payload = json.dumps(
        [schema, campaign_id, local_id, index], separators=(",", ":"),
        ensure_ascii=True)
    identity = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()[:24]
    return ClaimTuple(
        measurement_id=f"gpuscreen_{identity}",
        metric=str(metric),
        value=value,
        date=str(receipt.get("ended_at") or "")[:10],
        category=str(measurement.get("category", "")),
        claim=str(measurement.get("claim", "")),
        metric_direction=str(measurement.get("metric_direction", "")),
        protocol_id=str(measurement.get("protocol_id", "")),
        reps=reps,
        reps_basis=str(measurement.get("reps_basis", "")),
        unit=str(measurement.get("unit", "")),
        attestation_sha256=str(native.get("receipt_sha256") or ""),
        attestation_locator=str(native.get("receipt_locator") or ""),
        attestation_present=native.get("attestation_present"),
        source_kind="autokernel-gpu-screening-measurement",
        extra={
            "projection_schema": PROJECTION_SCHEMA,
            "source_schema": schema,
            "campaign_id": campaign_id,
            "native_measurement_id": local_id,
            "native_measurement_sha256": measurement.get("measurement_sha256", ""),
            "receipt_self_sha256": receipt.get(
                "baseline_sha256" if schema == BANK_SCHEMA else "result_sha256", ""),
            **dict(measurement.get("extra") or {}),
        },
    )


__all__ = ["ADAPTER_ID", "PROJECTION_SCHEMA", "SOURCE_SCHEMAS",
           "PRE_HOOK_SCHEMAS", "BANK_SCHEMA", "RESULT_SCHEMA", "PRODUCER_ID",
           "PRODUCER_PATH", "AUTHORITY", "native_rows", "project"]

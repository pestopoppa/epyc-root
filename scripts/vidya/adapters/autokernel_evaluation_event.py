"""Project prospective AutoKernel performance events into measurement ClaimTuples.

The producer contract lives in ``epyc-inference-research``.  This read side deliberately admits
only the current ``evaluation_event.v5`` shape and repeats its load-bearing structural invariants
as checked literals: the research tree is an optional sibling checkout, so importing it would make
production ingestion depend on whichever branch happened to be mounted.  Tests use campaign-shaped
journal envelopes and pin every identity and reduction binding this adapter consumes.

Historical v5 events do not carry ``performance.search_discipline.belief_capture`` and therefore
produce no rows.  That marker is a prospective write-side promise, not permission to reconstruct a
tuple from old journal material.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import (  # noqa: E402
    CATEGORIES,
    METRIC_DIRECTIONS,
    ClaimTuple,
    ProjectionError,
    register,
)

ADAPTER_ID = "vidya.adapters.autokernel_evaluation_event/v1"
CURRENT_EVENT_SCHEMA = "epyc.autokernel.evaluation_event.v5"
JOURNAL_SCHEMA = "epyc.autokernel.journal_entry.v1"
JOURNAL_KIND = "EVALUATION_EVENT"
CAPTURE_SCHEMA = "epyc.vidya.autokernel_evaluation_event_capture.v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_VERSIONED_ID = re.compile(r"^.+/v[1-9][0-9]*$")
_CO_RESIDENCY = re.compile(r"^(single|co_resident:[A-Za-z0-9._-]+)$")
_TIERS = frozenset({"T0", "T1", "T1a", "T1b", "T1c", "T2", "T3", "T4"})
_BACKENDS = frozenset({
    "llama_cpu", "llama_gpu", "whisper_stt", "qwentts_tts", "serving_runtime",
})
_CHANGE_CLASSES = frozenset({
    "parameter", "dispatcher", "arithmetic", "layout", "fusion", "moe_scheduling",
    "recurrent", "scheduler_policy", "oracle_port", "core_header",
})
_DETERMINISM = frozenset({"bitwise_stable", "bitwise_unstable", "not_measured"})
_STATUSES = frozenset({
    "pass", "fail", "inconclusive", "invalid", "timeout", "crash", "rejected",
})
_NON_MEASUREMENT_STATUSES = frozenset({"invalid", "timeout", "crash", "rejected"})
_EFFECT_SCALES = frozenset({"relative", "absolute"})
_PLACEHOLDER_DIGESTS = frozenset({"0" * 40, "0" * 64, "f" * 40, "f" * 64})
_AUTHORITY_ACTIONS = frozenset({
    "freeze", "freezes", "frozen", "cutover", "cutovers", "promote", "promotes",
    "promotion", "promotions", "ratify", "ratifies", "ratification", "sign", "signoff",
    "deploy", "deployment", "release", "releases",
})
_AUTHORITY_QUALIFIERS = frozenset({
    "auto", "automatic", "autonomous", "unattended", "unsupervised", "authority",
    "authorize", "authorized", "authorised", "approve", "approved", "allow", "allowed",
    "enable", "enabled", "may", "can", "permit", "permitted", "self", "grant", "granted",
    "override",
})
_BARE_AUTHORITY = frozenset({
    "freeze", "cutover", "promote", "promotion", "ratify", "signoff", "signed",
})


def _canonical_json(value: Any) -> str:
    def check(obj: Any, path: str) -> None:
        if obj is None or isinstance(obj, (bool, int, str)):
            return
        if isinstance(obj, float):
            if not math.isfinite(obj):
                raise ProjectionError(f"{path}: non-finite float is not canonical JSON")
            return
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                check(item, f"{path}[{index}]")
            return
        if isinstance(obj, dict):
            for key, item in obj.items():
                if not isinstance(key, str):
                    raise ProjectionError(f"{path}: canonical JSON keys must be strings")
                check(item, f"{path}.{key}")
            return
        raise ProjectionError(
            f"{path}: {type(obj).__name__} is not canonical JSON (use lists, not tuples)")

    check(value, "$")
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def content_hash(value: Any) -> str:
    """The canonical payload digest used by AutoKernel's current schema SSOT."""
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(obj: dict, key: str) -> str | None:
    value = obj.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _positive_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 1


def _nonnegative_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _has_authority_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
            tokens = {token for token in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if token}
            flat = "".join(tokens)
            qualified = bool(tokens & _AUTHORITY_ACTIONS and tokens & _AUTHORITY_QUALIFIERS)
            glued = any(stem in flat and (
                f"auto{stem}" in flat or any(q in flat for q in (
                    "authoriz", "authoris", "authority", "approv", "unattended",
                    "autonomous", "unsupervised", "permitted", "granted", "override")))
                for stem in ("freeze", "cutover", "promot", "ratif", "deploy", "signoff",
                             "releas"))
            if qualified or flat in _BARE_AUTHORITY or glued or _has_authority_key(child):
                return True
    elif isinstance(value, list):
        return any(_has_authority_key(child) for child in value)
    return False


def _valid_event(event: Any) -> bool:
    """Fail-closed current-v5 validator for every structural field this reader trusts."""
    if not isinstance(event, dict) or event.get("schema") != CURRENT_EVENT_SCHEMA:
        return False
    try:
        _canonical_json(event)
    except ProjectionError:
        return False
    if _has_authority_key(event):
        return False

    for key, prefix in (("event_id", "ake-"), ("campaign_id", "ak-"),
                        ("candidate_id", "akc-")):
        value = _text(event, key)
        if value is None or not value.startswith(prefix):
            return False
    if event.get("tier") not in _TIERS or event.get("backend") not in _BACKENDS:
        return False
    if event.get("change_class") not in _CHANGE_CLASSES or event.get("anchor_tier") not in _TIERS:
        return False
    transfers = event.get("transfer_ratio_to")
    if not isinstance(transfers, list):
        return False
    transfer_ids: set[str] = set()
    for row in transfers:
        if not isinstance(row, dict):
            return False
        target_id = _text(row, "event_id")
        source_effect, target_effect, ratio = (
            row.get("source_effect"), row.get("target_effect"), row.get("ratio"))
        if (target_id is None or not target_id.startswith("ake-")
                or target_id == event["event_id"] or target_id in transfer_ids
                or row.get("tier") != event["anchor_tier"]
                or not all(_finite(v) for v in (source_effect, target_effect, ratio))
                or target_effect == 0
                or not math.isclose(ratio, source_effect / target_effect,
                                    rel_tol=1e-12, abs_tol=1e-15)):
            return False
        transfer_ids.add(target_id)

    claim = event.get("claim_grammar")
    if (not isinstance(claim, dict) or claim.get("category") not in CATEGORIES
            or claim.get("metric_direction") not in METRIC_DIRECTIONS
            or not _text(claim, "protocol_id") or not _text(claim, "metric")
            or not _positive_int(claim.get("reps")) or not _text(claim, "attestation_ref")):
        return False
    evaluator = event.get("evaluator")
    if (not isinstance(evaluator, dict) or not _VERSIONED_ID.match(_text(evaluator, "id") or "")
            or not _SHA256.match(str(evaluator.get("bundle_sha256", "")))):
        return False
    artifact = event.get("artifact")
    if not isinstance(artifact, dict) or any(
            not _SHA256.match(str(artifact.get(key, "")))
            for key in ("source_sha256", "binary_sha256", "linkage_sha256")):
        return False

    anchor = event.get("anchor")
    if not isinstance(anchor, dict):
        return False  # voided anchor-less v5 records are never measurements
    if (not _COMMIT.match(str(anchor.get("source_commit", "")))
            or any(not _SHA256.match(str(anchor.get(key, "")))
                   for key in ("binary_sha256", "linkage_sha256"))
            or any(str(anchor.get(key, "")) in _PLACEHOLDER_DIGESTS
                   for key in ("source_commit", "binary_sha256", "linkage_sha256"))):
        return False
    anchor_events = anchor.get("measurement_event_ids")
    if (not isinstance(anchor_events, list)
            or any(not isinstance(item, str) or not item.startswith("ake-") for item in anchor_events)
            or (event["tier"] != "T0" and not anchor_events)):
        return False

    if (not _SHA256.match(str(event.get("scope_manifest_sha256", "")))
            or not _text(event, "host_receipt") or not _text(event, "resource_claim_receipt")
            or not _CO_RESIDENCY.match(str(event.get("co_residency", "")))):
        return False
    if any(not isinstance(event.get(key), dict)
           for key in ("correctness", "quality", "stability", "mechanism")):
        return False
    scope = event.get("scope_denominator")
    if (not isinstance(scope, dict) or scope.get("machine_subset") not in {"full", "partial"}
            or not isinstance(scope.get("numa_nodes"), list)
            or any(isinstance(v, bool) or not isinstance(v, int) for v in scope["numa_nodes"])
            or not isinstance(scope.get("devices"), list)
            or any(not isinstance(v, str) for v in scope["devices"])
            or not _nonnegative_int(scope.get("cores"))):
        return False
    if scope["machine_subset"] == "partial" and not scope["numa_nodes"] and not scope["devices"]:
        return False
    determinism = event.get("determinism")
    if (not isinstance(determinism, dict) or determinism.get("class") not in _DETERMINISM
            or not _nonnegative_int(determinism.get("same_seed_repeat_runs"))
            or (determinism["class"] != "not_measured"
                and determinism["same_seed_repeat_runs"] == 0)):
        return False

    performance = event.get("performance")
    if (not isinstance(performance, dict) or not isinstance(performance.get("raw_samples"), list)
            or not _nonnegative_int(performance.get("paired_blocks"))
            or "estimate" not in performance or "uncertainty" not in performance
            or (performance["estimate"] is not None and not _finite(performance["estimate"]))):
        return False
    if performance["estimate"] is not None and not performance["raw_samples"]:
        return False
    if performance["paired_blocks"] != len(performance["raw_samples"]):
        return False

    flags = event.get("integrity_flags")
    status = event.get("status")
    supersedes = event.get("supersedes")
    if (status not in _STATUSES or not isinstance(flags, list)
            or any(not isinstance(flag, str) for flag in flags)
            or (status == "pass" and flags)
            or not isinstance(supersedes, list)
            or any(not isinstance(item, str) for item in supersedes)
            or not _utc_timestamp(event.get("created_at"))):
        return False
    if "narrative" in event and (
            not isinstance(event["narrative"], str)
            or event.get("narrative_retrievable") is not False):
        return False

    device = event.get("device_state", object())
    if event["backend"] != "llama_gpu":
        return device is None
    if not isinstance(device, dict):
        return False
    if any(not _text(device, key) for key in ("device_id", "source", "receipt_ref")):
        return False
    nominal, ratio = device.get("nominal_sclk_mhz"), device.get("min_sclk_ratio")
    samples = device.get("samples")
    if (not _finite(nominal) or nominal <= 0 or not _finite(ratio) or not 0 < ratio <= 1
            or not isinstance(device.get("throttle_observed"), bool)
            or not isinstance(samples, list) or not samples):
        return False
    loaded = [row for row in samples if isinstance(row, dict)
              and row.get("under_measurement_load") is True]
    if not loaded:
        return False
    for row in samples:
        if (not isinstance(row, dict) or not isinstance(row.get("under_measurement_load"), bool)
                or any(not _finite(row.get(key)) or row[key] < 0
                       for key in ("sclk_mhz", "mclk_mhz", "power_w", "temperature_c"))):
            return False
    derived_throttle = any(row["sclk_mhz"] < nominal * ratio for row in loaded)
    return device["throttle_observed"] == derived_throttle


def load_event_source(source: Any) -> dict | None:
    """Return validated event metadata, or ``None`` for any inadmissible source."""
    envelope = None
    event = source
    if isinstance(source, dict) and source.get("journal_schema") == JOURNAL_SCHEMA:
        envelope = source
        event = source.get("payload")
        if (source.get("kind") != JOURNAL_KIND or not _positive_int(source.get("seq"))
                or not _text(source, "event_id") or not _utc_timestamp(source.get("written_at"))
                or not isinstance(event, dict)):
            return None
    if not _valid_event(event):
        return None
    if event["status"] in _NON_MEASUREMENT_STATUSES or event["integrity_flags"]:
        return None

    event_digest = content_hash(event)
    if envelope is None:
        locator = event["claim_grammar"]["attestation_ref"]
        present = False
    else:
        if (envelope.get("campaign_id") != event["campaign_id"]
                or envelope.get("record_id") != event["event_id"]):
            return None
        locator = (f"autokernel-journal:{event['campaign_id']}:seq={envelope['seq']}:"
                   f"entry={envelope['event_id']}:record={event['event_id']}")
        present = True
    return {
        "source": source,
        "event": event,
        "event_sha256": event_digest,
        "event_locator": locator,
        "attestation_present": present,
    }


def _capture(event: dict) -> dict | None:
    performance = event["performance"]
    discipline = performance.get("search_discipline")
    capture = discipline.get("belief_capture") if isinstance(discipline, dict) else None
    if not isinstance(capture, dict) or capture.get("schema") != CAPTURE_SCHEMA:
        return None
    artifact = event["artifact"]
    if (capture.get("effect_scale") not in _EFFECT_SCALES
            or not _text(capture, "model_id")
            or not _SHA256.match(str(capture.get("model_sha256", "")))
            or capture.get("source_sha256") != artifact["source_sha256"]
            or capture.get("binary_sha256") != artifact["binary_sha256"]
            or capture.get("resource_claim_receipt") != event["resource_claim_receipt"]
            or not _SHA256.match(str(capture.get("producer_sha256", "")))):
        return None
    claim = event["claim_grammar"]
    binding = {
        "schema": CAPTURE_SCHEMA,
        "event_id": event["event_id"],
        "campaign_id": event["campaign_id"],
        "candidate_id": event["candidate_id"],
        "category": claim["category"],
        "protocol_id": claim["protocol_id"],
        "metric": claim["metric"],
        "metric_direction": claim["metric_direction"],
        "reps": claim["reps"],
        "effect_scale": capture["effect_scale"],
        "model_id": capture["model_id"],
        "model_sha256": capture["model_sha256"],
        "source_sha256": capture["source_sha256"],
        "binary_sha256": capture["binary_sha256"],
        "resource_claim_receipt": capture["resource_claim_receipt"],
        "producer_sha256": capture["producer_sha256"],
        "raw_samples_sha256": capture.get("raw_samples_sha256"),
    }
    if capture.get("identity_binding_sha256") != content_hash(binding):
        return None
    return capture


def _reduction(event: dict, capture: dict) -> tuple[float, str] | None:
    performance = event["performance"]
    raw = performance["raw_samples"]
    if not raw:
        return None
    arm_reps = event["claim_grammar"]["reps"]
    raw_digest = content_hash(raw)
    if (capture.get("raw_samples_sha256") != raw_digest
            or performance.get("raw_samples_ref") != f"sha256:{raw_digest}"):
        return None
    effects = []
    seen: set[int] = set()
    for block in raw:
        if not isinstance(block, list) or len(block) != 9:
            return None
        block_index, _unit, _stratum, order, segment, extension, measured_at, anchors, candidates = block
        if (not _nonnegative_int(block_index) or block_index in seen
                or not isinstance(_unit, str) or not _unit.strip()
                or not isinstance(_stratum, str) or not _stratum.strip()
                or order not in {"anchor_first", "candidate_first"}
                or segment not in {"base", "extension"}
                or (segment == "base" and extension is not None)
                or (segment == "extension" and not _positive_int(extension))
                or (measured_at is not None and not _utc_timestamp(measured_at))
                or not isinstance(anchors, list) or len(anchors) != arm_reps
                or not isinstance(candidates, list) or len(candidates) != arm_reps
                or any(not _finite(value) for value in anchors + candidates)):
            return None
        seen.add(block_index)
        anchor_value, candidate_value = median(anchors), median(candidates)
        if capture["effect_scale"] == "relative":
            if anchor_value <= 0:
                return None
            effects.append((candidate_value - anchor_value) / anchor_value)
        else:
            effects.append(candidate_value - anchor_value)
    derived = median(effects)
    if not math.isclose(derived, performance["estimate"], rel_tol=1e-12, abs_tol=1e-15):
        return None
    return derived, raw_digest


def native_rows(source: Any) -> tuple[dict, ...]:
    """Return one prospective performance row from a real event or journal envelope."""
    loaded = load_event_source(source)
    if loaded is None:
        return ()
    event = loaded["event"]
    if event["performance"]["estimate"] is None:
        return ()
    capture = _capture(event)
    reduction = _reduction(event, capture) if capture is not None else None
    if capture is None or reduction is None:
        return ()
    value, raw_digest = reduction
    return ({
        **loaded,
        "capture": capture,
        "value": value,
        "raw_samples_sha256": raw_digest,
    },)


@register("autokernel-evaluation-event-measurement")
def project(native: Any) -> ClaimTuple:
    """Revalidate one native row so callers cannot bypass :func:`native_rows`."""
    if not isinstance(native, dict) or "source" not in native:
        raise ProjectionError("AutoKernel evaluation native row must retain its source")
    derived = native_rows(native["source"])
    if len(derived) != 1:
        raise ProjectionError("AutoKernel evaluation source is not a prospective measurement")
    expected = derived[0]
    for key in ("event_sha256", "event_locator", "value", "raw_samples_sha256"):
        if native.get(key) != expected[key]:
            raise ProjectionError(f"AutoKernel evaluation native row mutated {key}")

    event, capture = expected["event"], expected["capture"]
    claim, artifact = event["claim_grammar"], event["artifact"]
    identity = hashlib.sha256(_canonical_json({
        "event_id": event["event_id"], "event_sha256": expected["event_sha256"],
        "metric": claim["metric"], "source_sha256": artifact["source_sha256"],
        "binary_sha256": artifact["binary_sha256"], "model_sha256": capture["model_sha256"],
        "resource_claim_receipt": event["resource_claim_receipt"],
    }).encode("utf-8")).hexdigest()[:24]
    unit = "relative_effect" if capture["effect_scale"] == "relative" else "metric_delta"
    return ClaimTuple(
        measurement_id=f"akeval_{identity}",
        metric=claim["metric"],
        value=expected["value"],
        date=event["created_at"][:10],
        category=claim["category"],
        claim=(f"AutoKernel {event['tier']} {event['backend']} candidate {event['candidate_id']} "
               f"recorded {claim['metric']} {capture['effect_scale']} effect "
               f"{expected['value']} with status {event['status']}"),
        metric_direction=claim["metric_direction"],
        protocol_id=claim["protocol_id"],
        reps=event["performance"]["paired_blocks"],
        reps_basis="scored:paired_blocks",
        unit=unit,
        attestation_sha256=expected["event_sha256"],
        attestation_locator=expected["event_locator"],
        attestation_present=expected["attestation_present"],
        source_kind="autokernel-evaluation-event-measurement",
        extra={
            "event_id": event["event_id"],
            "campaign_id": event["campaign_id"],
            "candidate_id": event["candidate_id"],
            "tier": event["tier"],
            "backend": event["backend"],
            "status": event["status"],
            "effect_scale": capture["effect_scale"],
            "raw_samples_sha256": expected["raw_samples_sha256"],
            "source_sha256": artifact["source_sha256"],
            "binary_sha256": artifact["binary_sha256"],
            "linkage_sha256": artifact["linkage_sha256"],
            "model_id": capture["model_id"],
            "model_sha256": capture["model_sha256"],
            "resource_claim_receipt": event["resource_claim_receipt"],
            "producer_sha256": capture["producer_sha256"],
        },
    )


__all__ = [
    "ADAPTER_ID", "CAPTURE_SCHEMA", "CURRENT_EVENT_SCHEMA", "content_hash",
    "load_event_source", "native_rows", "project",
]

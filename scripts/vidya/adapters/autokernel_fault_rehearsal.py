"""Classify prospective AutoKernel host-process fault rehearsals.

These receipts are dependency evidence, not measurements.  ``ClaimTuple`` cannot represent that
distinction without inventing a metric, direction, category, or measurement warrant, so this
adapter deliberately does not register a ClaimTuple projection and emits no support frame.  It
instead verifies the producer-written dependency rows and returns typed classifications for a
future dependency-evidence carrier.  Receipts predating the producer hook return no rows.

All three native recovery legs share one run-level support key.  They retain their exact native
source, producer, and process identities for audit, but cannot be counted as three corroborating
witnesses.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from claim_tuple import ProjectionError

ADAPTER_ID = "vidya.adapters.autokernel_fault_rehearsal/v1"
SOURCE_SCHEMA = "epyc.autokernel.host_process_fault_rehearsal.v1"
EVIDENCE_SCHEMA = "epyc.autokernel.host_process_fault_rehearsal_dependency_evidence.v1"
CAPTURE_MODE = "measured_host_process_rehearsal"
CLASSIFICATION = "dependency_evidence_only"
SUPPORT_SCOPE = "rehearsal_run"
CAMPAIGN_PREFIX = "ak-fault-rehearsal-"
PRODUCER_PATH_SUFFIX = "/scripts/kernel_rnd/autokernel/fault_rehearsal.py"
EXPECTED_LEGS = (
    "durable_journal_crash_restart_replay",
    "resource_revocation_non_preemption",
    "hash_bound_artifact_tamper_refusal",
)
AUTHORITY_BOUNDARY = {
    "inference": False,
    "benchmark": False,
    "build": False,
    "gpu": False,
    "kernel_tree_write": False,
    "production_write": False,
    "stack_control": False,
    "release": False,
    "freeze": False,
    "promotion": False,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class DependencyEvidenceRecord:
    """Validated native evidence waiting for an honest dependency-evidence carrier."""

    evidence_id: str
    support_key: str
    campaign_id: str
    run_status: str
    leg_name: str
    leg_status: str
    source_identity: dict[str, Any]
    producer_identity: dict[str, Any]
    process_identities: tuple[dict[str, Any], ...]
    receipt_sha256: str
    receipt_locator: str
    classification: str = CLASSIFICATION
    support_scope: str = SUPPORT_SCOPE
    performance_measurement: bool = False
    corroborating_witness: bool = False
    belief_measurement_emitted: bool = False


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
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


def _process_identity(value: Any, label: str) -> dict[str, Any]:
    identity = _mapping(value, label)
    if set(identity) != {"pid", "pgid", "start_ticks", "boot_id", "argv", "argv_sha256"}:
        raise ProjectionError(f"{label} has an unexpected process-identity shape")
    for field in ("pid", "pgid", "start_ticks"):
        number = identity.get(field)
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ProjectionError(f"{label}.{field} must be a positive integer")
    if identity["pgid"] != identity["pid"]:
        raise ProjectionError(f"{label} must identify a private process group")
    _text(identity.get("boot_id"), f"{label}.boot_id")
    argv = identity.get("argv")
    if not isinstance(argv, list) or not argv or any(
        not isinstance(item, str) or not item for item in argv
    ):
        raise ProjectionError(f"{label}.argv must be a non-empty string list")
    if _sha(identity.get("argv_sha256"), f"{label}.argv_sha256") != _canonical_sha256(argv):
        raise ProjectionError(f"{label}.argv_sha256 does not bind argv")
    return dict(identity)


def _native_process_identities(leg: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    name = leg.get("name")
    if name == EXPECTED_LEGS[0]:
        for role, field in (
            ("crash_process", "crash_process"),
            ("restart_process", "restart_process"),
        ):
            if field in leg:
                rows.append({
                    "role": role,
                    "identity": _process_identity(leg[field], f"leg.{field}"),
                })
    elif name == EXPECTED_LEGS[1]:
        teardown = leg.get("teardown")
        if isinstance(teardown, Mapping) and "identity" in teardown:
            rows.append({
                "role": "claim_holder_process",
                "identity": _process_identity(
                    teardown["identity"], "leg.teardown.identity"
                ),
            })
    return tuple(rows)


def _receipt_sha256(receipt: dict) -> str:
    logical = dict(receipt)
    stored = _sha(logical.pop("receipt_sha256", None), "receipt.receipt_sha256")
    if stored != _canonical_sha256(logical):
        raise ProjectionError("receipt_sha256 does not bind the logical rehearsal receipt")
    return stored


def classify_receipt(
    receipt: dict, *, receipt_locator: str = "", receipt_sha256: str = "",
) -> tuple[DependencyEvidenceRecord, ...]:
    """Verify and classify producer-written dependency rows; never reconstruct old receipts."""
    if not isinstance(receipt, dict) or receipt.get("schema") != SOURCE_SCHEMA:
        raise ProjectionError("unsupported AutoKernel fault-rehearsal receipt schema")
    rows = receipt.get("dependency_evidence")
    if rows is None:
        return ()
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_LEGS):
        raise ProjectionError("dependency_evidence must contain exactly one row per recovery leg")
    if receipt.get("capture_mode") != CAPTURE_MODE:
        raise ProjectionError("fault-rehearsal capture mode changed")
    campaign_id = _text(receipt.get("campaign_id"), "receipt.campaign_id")
    if not campaign_id.startswith(CAMPAIGN_PREFIX):
        raise ProjectionError("fault-rehearsal campaign id has the wrong prefix")
    legs = receipt.get("legs")
    if not isinstance(legs, list) or len(legs) != len(EXPECTED_LEGS) \
            or any(not isinstance(leg, dict) for leg in legs):
        raise ProjectionError("fault-rehearsal receipt must carry exactly three native legs")
    if tuple(leg.get("name") for leg in legs) != EXPECTED_LEGS:
        raise ProjectionError("fault-rehearsal native leg names/order changed")
    statuses = tuple(leg.get("status") for leg in legs)
    if any(status not in {"PASS", "FAIL"} for status in statuses):
        raise ProjectionError("every native recovery leg must have status PASS or FAIL")
    run_status = "PASS" if all(status == "PASS" for status in statuses) else "FAIL"
    if receipt.get("status") != run_status:
        raise ProjectionError("rehearsal run status does not derive from all three legs")
    if receipt.get("authority") != AUTHORITY_BOUNDARY:
        raise ProjectionError("fault-rehearsal authority must remain the exact all-false boundary")
    if receipt.get("live_claim_root_touched") is not False:
        raise ProjectionError("fault rehearsal touched the live claim root")

    environment = _mapping(receipt.get("environment"), "receipt.environment")
    source = _mapping(environment.get("source_tree"), "environment.source_tree")
    if set(source) != {"root", "branch", "commit"}:
        raise ProjectionError("source-tree identity has an unexpected shape")
    _text(source.get("root"), "source_tree.root")
    branch = source.get("branch")
    if branch is not None:
        _text(branch, "source_tree.branch")
    commit = source.get("commit")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise ProjectionError("source_tree.commit must be a full commit")
    producer_path = _text(environment.get("producer_path"), "environment.producer_path")
    if not producer_path.endswith(PRODUCER_PATH_SUFFIX):
        raise ProjectionError("receipt names a different producer path")
    producer = {
        "path": producer_path,
        "sha256": _sha(environment.get("producer_sha256"), "environment.producer_sha256"),
    }
    stored_receipt_sha = _receipt_sha256(receipt)
    if receipt_sha256 and _sha(receipt_sha256, "receipt_sha256") != stored_receipt_sha:
        raise ProjectionError("external receipt digest differs from the self-bound receipt")
    locator = str(receipt_locator or "")

    run_identity = {"receipt_schema": SOURCE_SCHEMA, "campaign_id": campaign_id}
    support_key = "akfault_run_" + _canonical_sha256(run_identity)[:24]
    records = []
    for index, (row_value, leg) in enumerate(zip(rows, legs, strict=True)):
        row = _mapping(row_value, f"dependency_evidence[{index}]")
        unsigned = dict(row)
        evidence_sha = _sha(
            unsigned.pop("evidence_sha256", None),
            f"dependency_evidence[{index}].evidence_sha256",
        )
        if evidence_sha != _canonical_sha256(unsigned):
            raise ProjectionError("dependency evidence digest does not bind its row")
        leg_name = EXPECTED_LEGS[index]
        evidence_id = "akfault_" + _canonical_sha256([run_identity, leg_name])[:24]
        native_processes = _native_process_identities(leg)
        expected = {
            "schema": EVIDENCE_SCHEMA,
            "evidence_id": evidence_id,
            "classification": CLASSIFICATION,
            "support_scope": SUPPORT_SCOPE,
            "support_key": support_key,
            "run_identity": run_identity,
            "run_status": run_status,
            "leg_name": leg_name,
            "leg_status": statuses[index],
            "source_identity": source,
            "producer_identity": producer,
            "process_identities": list(native_processes),
            "performance_measurement": False,
            "corroborating_witness": False,
            "belief_measurement_emitted": False,
        }
        if unsigned != expected:
            raise ProjectionError(
                "dependency evidence row differs from its native leg/run identity or authority boundary"
            )
        records.append(DependencyEvidenceRecord(
            evidence_id=evidence_id,
            support_key=support_key,
            campaign_id=campaign_id,
            run_status=run_status,
            leg_name=leg_name,
            leg_status=statuses[index],
            source_identity=dict(source),
            producer_identity=producer,
            process_identities=native_processes,
            receipt_sha256=stored_receipt_sha,
            receipt_locator=locator,
        ))
    return tuple(records)


def project(native: Any) -> None:
    """Fail closed: dependency evidence has no honest ``ClaimTuple`` projection today."""
    if not isinstance(native, dict):
        raise ProjectionError("AutoKernel fault-rehearsal native record must be a dict")
    receipt = native.get("receipt", native)
    classify_receipt(
        _mapping(receipt, "native.receipt"),
        receipt_locator=str(native.get("receipt_locator") or ""),
        receipt_sha256=str(native.get("receipt_sha256") or ""),
    )
    raise ProjectionError(
        "host-process fault rehearsal is dependency evidence only; ClaimTuple represents "
        "measurements and cannot emit an evidence_supports_claim frame without invented warrant"
    )


__all__ = [
    "ADAPTER_ID", "CLASSIFICATION", "DependencyEvidenceRecord", "EVIDENCE_SCHEMA",
    "SOURCE_SCHEMA", "SUPPORT_SCOPE", "classify_receipt", "project",
]

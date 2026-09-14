"""Strict hub-side reader for the research-owned campaign snapshot.

The hub never imports the research package.  A durable snapshot is history;
only a matching transport-health identity can make its producer live.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import queue
import threading
import time
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SNAPSHOT_SCHEMA = "epyc.autokernel.campaign_snapshot.v1"
SNAPSHOT_SCHEMA_V2 = "epyc.autokernel.campaign_snapshot.v2"
SNAPSHOT_SCHEMA_V3 = "epyc.autokernel.campaign_snapshot.v3"
UNIFIED_PROJECTION_SCHEMA = "epyc.autokernel.unified_campaign_projection.v1"
UNIFIED_PROJECTION_SCHEMA_V2 = "epyc.autokernel.unified_campaign_projection.v2"
UNIFIED_PROJECTION_SCHEMA_V3 = "epyc.autokernel.unified_campaign_projection.v3"
HEALTH_SCHEMA = "epyc.autokernel.campaign_transport_health.v1"
SNAPSHOT_FILENAME = "campaign-snapshot.json"
STORE_ROOT_ENV = "AUTOKERNEL_CAMPAIGN_STORE_ROOT"
CAMPAIGN_ID_ENV = "AUTOKERNEL_CAMPAIGN_ID"
CONFIG_GENERATION_ENV = "AUTOKERNEL_CAMPAIGN_CONFIG_GENERATION"
CONFIG_DIGEST_ENV = "AUTOKERNEL_CAMPAIGN_CONFIG_DIGEST"
GATEWAY_URL_ENV = "AUTOKERNEL_CAMPAIGN_GATEWAY_URL"
HUB_ORIGIN_ENV = "AUTOKERNEL_CAMPAIGN_HUB_ORIGIN"
HEALTH_TIMEOUT_S = 0.25
HEARTBEAT_STALE_AFTER_S = 180.0
MAX_CLOCK_SKEW_S = 5.0
MAX_HEALTH_BODY = 16 * 1024
HEALTH_CACHE_TTL_S = 30.0
HEALTH_RESULT_WAIT_S = 0.02

_SHA256 = frozenset("0123456789abcdef")
_DESIRED = frozenset({"paused", "running", "drained"})
_OBSERVED = frozenset({"paused", "running", "drained", "waiting_prerequisite"})
_OBSERVED_V2 = _OBSERVED | frozenset({"pausing", "draining", "ownership_unresolved"})
_SNAPSHOT_FIELDS = frozenset({
    "schema", "producer_build", "producer_schema", "campaign_id",
    "config_generation", "config_digest", "requested_manifest_digest",
    "supervisor_incarnation", "stream_epoch", "sequence", "journal_cursor",
    "control_revision", "generated_at", "desired_state", "observed_state",
    "command_results", "active_worker", "producer_heartbeat_at",
    "last_scientific_result_at", "worker_activity_at", "execution_authorized",
    "prerequisite_reason",
})
_SNAPSHOT_V2_FIELDS = _SNAPSHOT_FIELDS | frozenset({
    "execution_capability_available", "worker_lifecycle_revision",
})
_SNAPSHOT_V3_FIELDS = _SNAPSHOT_V2_FIELDS | frozenset({"unified"})
_BUILD_FIELDS = frozenset({
    "schema", "scope", "module", "identity_basis", "included_symbols",
    "excluded_scope", "sha256",
})
_RESULT_FIELDS = frozenset({
    "request_id", "operation", "payload_digest", "accepted", "completed",
    "control_revision", "desired_state", "observed_state", "prerequisite_reason",
})
_RESULT_V2_FIELDS = frozenset({
    "schema", "request_id", "operation", "payload_digest", "accepted",
    "accepted_at", "completed", "completed_at", "completion_reason",
    "control_revision", "desired_state", "observed_state", "prerequisite_reason",
})
_ACTIVE_WORKER_V2_FIELDS = frozenset({
    "worker_id", "worker_generation", "request_id", "plan_digest", "lineage_id",
    "stage_id", "state", "grant_id", "grant_generation", "container_id",
    "provider_deadline", "deadline_clock_domain", "control_revision", "started_at",
    "activity_at", "termination_deadline", "unresolved_reason",
})
_WORKER_STATES_V2 = frozenset({
    "intent", "container_created", "child_captured", "exec_release_intent",
    "executing", "result_retained", "tearing_down", "teardown_failed", "unresolved",
})
_QUIESCENT_COMPLETION_REASONS_V2 = frozenset({
    "already quiescent", "owned workers quiesced and claims released",
})
_SUPERSEDED_PAUSE_REASON_V2 = "superseded by a later accepted drain"
_HEALTH_FIELDS = frozenset({
    "schema", "ok", "transport", "producer", "service_build", "campaign_id",
    "config_generation", "config_digest", "supervisor_incarnation",
    "stream_epoch", "allowed_origin", "error",
})
_UNIFIED_FIELDS = frozenset({
    "schema", "scheduler", "resources", "actors", "evidence", "candidate", "targets",
})
_UNIFIED_SCHEDULER_FIELDS = frozenset({
    "schema", "projection_digest", "config_digest", "policy_digest", "round_number",
    "accounting_epoch", "capacity", "pending_selection_digest", "status", "reason",
    "campaign_attempts", "campaign_charged_seconds", "accounting", "coverage_debt_count",
})
_UNIFIED_SECTION_FIELDS = {
    "resources": frozenset({
        "schema", "status", "reason", "requested", "granted", "held", "used",
    }),
    "actors": frozenset({"schema", "status", "reason", "clock_semantics", "items"}),
    "evidence": frozenset({"schema", "status", "reason", "frontier_digest", "lag_seconds"}),
    "candidate": frozenset({
        "schema", "status", "reason", "accumulated_identity", "validated_identity",
        "frozen_production_identity", "validation_debt",
    }),
    "targets": frozenset({
        "schema", "status", "reason", "total", "ready", "prerequisite",
        "production_enrolled", "seed_enrolled", "items_page_ref",
    }),
}
_UNIFIED_SECTION_SCHEMAS = {
    "resources": "epyc.autokernel.unified_resource_status.v1",
    "actors": "epyc.autokernel.unified_actor_status.v1",
    "evidence": "epyc.autokernel.unified_evidence_status.v1",
    "candidate": "epyc.autokernel.unified_candidate_status.v1",
    "targets": "epyc.autokernel.unified_target_status.v1",
}
_UNIFIED_STATUSES = frozenset({"available", "unknown", "not_connected"})
_RESOURCE_VECTOR_FIELDS = frozenset({
    "schema", "physical_region_fraction", "gpu_devices", "memory_reservation_bytes",
})
_ACCOUNTING_FIELDS = frozenset({
    "schema", "receipt_count", "held_seconds", "physical_region_seconds",
    "gpu_device_seconds", "memory_byte_seconds", "beneficiary_seconds", "view_digest",
})


class CampaignStatusError(ValueError):
    """The configured source or producer contract is not trustworthy."""


def _exact(value: Mapping[str, Any], fields: frozenset[str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise CampaignStatusError(f"{label} must be an object")
    keys = tuple(value.keys())
    if any(not isinstance(key, str) for key in keys):
        raise CampaignStatusError(f"{label} keys must be strings")
    actual = set(keys)
    if actual != fields:
        raise CampaignStatusError(
            f"{label} fields differ: missing={sorted(fields - actual)}, "
            f"unknown={sorted(actual - fields)}")


def _text(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CampaignStatusError(f"{label} must be non-empty text")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CampaignStatusError(f"{label} must be an integer >= {minimum}")
    return value


def _finite(value: Any, label: str, *, nullable: bool = False) -> float | int | None:
    if value is None and nullable:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value))):
        raise CampaignStatusError(f"{label} must be finite")
    return value


def _digest(value: Any, label: str) -> str:
    result = _text(value, label)
    assert isinstance(result, str)
    if len(result) != 64 or any(char not in _SHA256 for char in result):
        raise CampaignStatusError(f"{label} must be a lowercase SHA-256")
    return result


def _enum(value: Any, allowed: frozenset[str] | set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise CampaignStatusError(f"{label} is unsupported")
    return value


def _timestamp(value: Any, label: str, *, nullable: bool = False) -> str | None:
    result = _text(value, label, nullable=nullable)
    if result is None:
        return None
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CampaignStatusError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CampaignStatusError(f"{label} must include a timezone")
    return result


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise CampaignStatusError(f"{label} must be an array")
    result = [_text(item, f"{label}[]") for item in value]
    if len(set(result)) != len(result):
        raise CampaignStatusError(f"{label} contains duplicates")
    return [str(item) for item in result]


def _validate_result_v1(value: Any) -> dict[str, Any]:
    _exact(value, _RESULT_FIELDS, "command result")
    row = dict(value)
    _text(row["request_id"], "command result request_id")
    operation = _enum(row["operation"], {"pause", "resume", "drain"},
                      "command result operation")
    _digest(row["payload_digest"], "command result payload_digest")
    if row["accepted"] is not True or not isinstance(row["completed"], bool):
        raise CampaignStatusError("command result accepted/completed must be boolean")
    _integer(row["control_revision"], "command result control_revision", 1)
    desired = _enum(row["desired_state"], _DESIRED, "command result desired_state")
    observed = _enum(row["observed_state"], _OBSERVED, "command result observed_state")
    reason = _text(row["prerequisite_reason"],
                   "command result prerequisite_reason", nullable=True)
    expected_desired = {"pause": "paused", "resume": "running", "drain": "drained"}
    if desired != expected_desired[operation]:
        raise CampaignStatusError("command result operation contradicts desired state")
    if operation in {"pause", "drain"}:
        if observed != desired or row["completed"] is not True or reason is not None:
            raise CampaignStatusError("completed management command result is contradictory")
    elif row["completed"]:
        if observed != "running" or reason is not None:
            raise CampaignStatusError("completed resume result is contradictory")
    elif observed != "waiting_prerequisite" or reason is None:
        raise CampaignStatusError("incomplete resume result lacks its prerequisite refusal")
    return row


def _validate_result_v2(value: Any) -> dict[str, Any]:
    _exact(value, _RESULT_V2_FIELDS, "v2 command result")
    row = dict(value)
    if row["schema"] != "epyc.autokernel.campaign_command_result.v2":
        raise CampaignStatusError("v2 command result schema is unsupported")
    _text(row["request_id"], "v2 command result request_id")
    operation = _enum(row["operation"], {"pause", "resume", "drain"},
                      "v2 command result operation")
    _digest(row["payload_digest"], "v2 command result payload_digest")
    if row["accepted"] is not True or not isinstance(row["completed"], bool):
        raise CampaignStatusError("v2 command result accepted/completed must be boolean")
    _timestamp(row["accepted_at"], "v2 command result accepted_at")
    if row["completed"]:
        _timestamp(row["completed_at"], "v2 command result completed_at")
        _text(row["completion_reason"], "v2 command result completion_reason")
    elif row["completed_at"] is not None or row["completion_reason"] is not None:
        raise CampaignStatusError("incomplete v2 command result carries completion fields")
    _integer(row["control_revision"], "v2 command result control_revision", 1)
    desired = _enum(row["desired_state"], _DESIRED, "v2 command result desired_state")
    observed = _enum(row["observed_state"], _OBSERVED_V2,
                     "v2 command result observed_state")
    prerequisite = _text(row["prerequisite_reason"],
                         "v2 command result prerequisite_reason", nullable=True)
    completion_reason = row["completion_reason"]
    if operation == "resume":
        running = (observed == "running" and completion_reason == "running"
                   and prerequisite is None)
        waiting = (observed == "waiting_prerequisite"
                   and completion_reason == "waiting on named prerequisite"
                   and prerequisite is not None)
        if not row["completed"] or desired != "running" or not (running or waiting):
            raise CampaignStatusError("v2 resume result semantics are contradictory")
    elif operation == "pause" and desired == "drained":
        if (not row["completed"] or observed != "draining" or prerequisite is not None
                or completion_reason != _SUPERSEDED_PAUSE_REASON_V2):
            raise CampaignStatusError("v2 superseded pause result semantics are contradictory")
    else:
        expected_desired = "paused" if operation == "pause" else "drained"
        settling = "pausing" if operation == "pause" else "draining"
        settled = expected_desired
        if desired != expected_desired or prerequisite is not None:
            raise CampaignStatusError("v2 lifecycle command desired state is contradictory")
        if row["completed"]:
            if (observed != settled
                    or completion_reason not in _QUIESCENT_COMPLETION_REASONS_V2):
                raise CampaignStatusError("v2 lifecycle completion semantics are contradictory")
        elif observed != settling:
            raise CampaignStatusError("v2 incomplete lifecycle command is not settling")
    return row


def _validate_active_worker_v2(value: Any) -> dict[str, Any]:
    _exact(value, _ACTIVE_WORKER_V2_FIELDS, "v2 active_worker")
    row = dict(value)
    for field in ("worker_id", "request_id", "lineage_id", "stage_id", "grant_id",
                  "container_id", "deadline_clock_domain"):
        _text(row[field], f"v2 active_worker {field}")
    _digest(row["plan_digest"], "v2 active_worker plan_digest")
    for field in ("worker_generation", "grant_generation"):
        _integer(row[field], f"v2 active_worker {field}", 1)
    _integer(row["control_revision"], "v2 active_worker control_revision", 0)
    _enum(row["state"], _WORKER_STATES_V2, "v2 active_worker state")
    _timestamp(row["started_at"], "v2 active_worker started_at")
    _timestamp(row["activity_at"], "v2 active_worker activity_at", nullable=True)
    _text(row["unresolved_reason"], "v2 active_worker unresolved_reason", nullable=True)
    _finite(row["provider_deadline"], "v2 active_worker provider_deadline", nullable=True)
    _finite(row["termination_deadline"], "v2 active_worker termination_deadline",
            nullable=True)
    return row


def _validate_build(value: Any, label: str) -> dict[str, Any]:
    _exact(value, _BUILD_FIELDS, label)
    row = dict(value)
    if row["schema"] != "epyc.autokernel.loaded_producer_build.v1":
        raise CampaignStatusError(f"{label} schema is unsupported")
    for field in ("scope", "module", "identity_basis"):
        _text(row[field], f"{label}.{field}")
    row["included_symbols"] = _string_list(
        row["included_symbols"], f"{label}.included_symbols")
    row["excluded_scope"] = _string_list(
        row["excluded_scope"], f"{label}.excluded_scope")
    _digest(row["sha256"], f"{label}.sha256")
    return row


def _number_map(value: Any, label: str) -> dict[str, float | int]:
    if not isinstance(value, Mapping) or any(
            not isinstance(key, str) or not key for key in value):
        raise CampaignStatusError(f"{label} must be an object with non-empty text keys")
    result = dict(value)
    for key, item in result.items():
        checked = _finite(item, f"{label}.{key}")
        assert checked is not None
        if checked < 0:
            raise CampaignStatusError(f"{label}.{key} must be nonnegative")
    return result


def _validate_resource_vector(value: Any) -> dict[str, Any]:
    _exact(value, _RESOURCE_VECTOR_FIELDS, "unified scheduler capacity")
    row = dict(value)
    if row["schema"] != "epyc.autokernel.resource_vector.v1":
        raise CampaignStatusError("unified scheduler capacity schema is unsupported")
    fraction = _finite(row["physical_region_fraction"], "capacity physical_region_fraction")
    assert fraction is not None
    if fraction < 0 or fraction > 1:
        raise CampaignStatusError("capacity physical_region_fraction must be between 0 and 1")
    row["gpu_devices"] = _string_list(row["gpu_devices"], "capacity gpu_devices")
    _integer(row["memory_reservation_bytes"], "capacity memory_reservation_bytes")
    if row["gpu_devices"] and fraction <= 0:
        raise CampaignStatusError("GPU capacity must declare a host CPU fraction")
    return row


def _validate_accounting(value: Any) -> dict[str, Any]:
    _exact(value, _ACCOUNTING_FIELDS, "unified scheduler accounting")
    row = dict(value)
    if row["schema"] != "epyc.autokernel.accounting_view.v1":
        raise CampaignStatusError("unified scheduler accounting schema is unsupported")
    _integer(row["receipt_count"], "accounting receipt_count")
    for field in ("held_seconds", "physical_region_seconds", "memory_byte_seconds"):
        checked = _finite(row[field], f"accounting {field}")
        assert checked is not None
        if checked < 0:
            raise CampaignStatusError(f"accounting {field} must be nonnegative")
    row["gpu_device_seconds"] = _number_map(
        row["gpu_device_seconds"], "accounting gpu_device_seconds")
    row["beneficiary_seconds"] = _number_map(
        row["beneficiary_seconds"], "accounting beneficiary_seconds")
    _digest(row["view_digest"], "accounting view_digest")
    body = {key: row[key] for key in _ACCOUNTING_FIELDS if key != "view_digest"}
    expected = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode()).hexdigest()
    if row["view_digest"] != expected:
        raise CampaignStatusError("accounting view_digest does not match its content")
    return row


def _validate_runtime(value: Any) -> dict[str, Any]:
    _exact(value, frozenset({"status", "reason", "reason_truncated", "observed_at",
        "observation_sequence", "retry_after_seconds", "work_kind", "target_revision",
        "transition_id", "settlement_outcome", "installed_work_kinds", "publication_error"}), "runtime observation")
    row = dict(value)
    _enum(row["status"], {"not_reported", "recovered", "waiting", "settled", "stopped",
                          "recovery_required"}, "runtime status")
    if len(_text(row["reason"], "runtime reason")) > 4096 or type(row["reason_truncated"]) is not bool:
        raise CampaignStatusError("runtime reason/bound differs")
    _integer(row["observation_sequence"], "runtime sequence")
    error = _text(row["publication_error"], "runtime publication error", nullable=True)
    if error is not None and len(error) > 4096:
        raise CampaignStatusError("runtime publication error exceeds bound")
    delay = _finite(row["retry_after_seconds"], "runtime retry delay")
    if delay < 0:
        raise CampaignStatusError("runtime retry delay is negative")
    _timestamp(row["observed_at"], "runtime observation time", nullable=True)
    missing = row["status"] == "not_reported"
    if (missing != (row["observed_at"] is None) or not missing and row["observation_sequence"] == 0
            or missing and row["observation_sequence"] > 0 and error is None):
        raise CampaignStatusError("runtime date/sequence differs")
    kinds = {"runtime_comparison", "actor_preparation", "profile_preparation", "calibration_preparation"}
    installed = _string_list(row["installed_work_kinds"], "installed runtime work kinds")
    if len(set(installed)) != len(installed) or any(kind not in kinds for kind in installed):
        raise CampaignStatusError("installed runtime work kinds differ")
    selected = row["work_kind"] is not None
    if selected:
        _enum(row["work_kind"], kinds, "runtime work kind")
    for name in ("target_revision", "transition_id"):
        if row[name] is not None:
            _digest(row[name], "runtime " + name)
        if selected != (row[name] is not None):
            raise CampaignStatusError("runtime selection identity differs")
    settled = row["settlement_outcome"] is not None
    if settled:
        _enum(row["settlement_outcome"], {"valid_comparison", "invalid", "failed", "prerequisite",
              "calibration", "validation", "reject_audit", "maintenance"}, "runtime settlement")
    if ((row["status"] == "settled") != settled or settled and not selected
            or missing and (selected or delay != 0 or row["reason_truncated"])):
        raise CampaignStatusError("runtime work/settlement differs")
    return row


_AGGREGATE_FIELDS = {
    "evidence": {"reader_id", "epoch", "owner_state", "ready", "readiness", "source_frontier", "cursor_frontier", "projection_frontier", "admission_frontier", "last_admitted_frontier", "projection_checksum", "proof_pending", "lag_events", "lag_seconds", "quarantine_count", "cached_finding_count"},
    "profile": {"configured_count", "usable_count", "mechanism_count", "debt_count", "planning_observed_at", "items", "items_total", "items_truncated"},
    "calibration": {"request_count", "pending_count", "collected_count", "exhausted_count", "failed_count", "contaminated_count", "qualification", "ranking_authorized", "items", "items_total", "items_truncated"},
    "actor": {"pending_count", "finished_count", "backend_count", "event_count", "executor_installed", "reserved", "spent", "items", "items_total", "items_truncated"},
}
_AGGREGATE_ITEMS = {
    "profile": {"target_revision", "profile_digest", "transition_id", "available_at_planning", "settled", "remaining_seconds", "clock_known", "consumed_request_debt"},
    "calibration": {"request_digest", "chunk_digest", "outcome"},
    "actor": {"request_digest", "target_revision", "transition_id", "phase", "settlement_outcome", "retry_remaining_seconds", "clock_known"},
}
_AGGREGATE_BUDGETS = {"actor_calls_per_target", "patch_repairs_per_target", "provider_seconds_per_target", "resource_failures_per_target", "contamination_events_per_target", "actor_calls_per_campaign"}


def _aggregate_number(value, *, integer=False, nullable=False):
    if nullable and value is None:
        return
    if (type(value) not in ((int,) if integer else (int, float))
            or not 0 <= value <= 2**63 - 1 or not math.isfinite(value)):
        raise CampaignStatusError("aggregate number is outside its bound")


def _aggregate_text(value, *, nullable=False, maximum=512):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not 0 < len(value) <= maximum:
        raise CampaignStatusError("aggregate text is outside its bound")


def _aggregate_scalar(name, value):
    if name.endswith("_at"):
        _aggregate_text(value, nullable=True, maximum=64)
        _timestamp(value, name, nullable=True)
    elif name.endswith(("_count", "_frontier")) or name in {"items_total", "lag_events"}:
        _aggregate_number(value, integer=True, nullable=True)
    elif name.endswith("seconds"):
        _aggregate_number(value, nullable=True)
    elif name.endswith(("_digest", "_revision")) or name in {"transition_id", "projection_checksum"}:
        if value is not None:
            _digest(value, name)
    elif name in {"ready", "proof_pending", "items_truncated", "ranking_authorized", "executor_installed",
                  "available_at_planning", "settled", "clock_known", "consumed_request_debt"}:
        if type(value) is not bool and not (name == "consumed_request_debt" and value is None):
            raise CampaignStatusError("aggregate flag is invalid")
    else:
        _aggregate_text(value, nullable=True)


def _aggregate_rows(unified):
    return {"evidence": unified["evidence"],
            **{kind: unified["actors"][kind] for kind in ("actor", "profile", "calibration")}}


def _validate_aggregates(unified):
    actors = unified["actors"]
    _exact(actors, {"schema", "status", "reason", "actor", "profile", "calibration"}, "preparation aggregate")
    if (actors["schema"] != "epyc.autokernel.unified_actor_status.v2"
            or actors["status"] not in {"available", "unknown"}):
        raise CampaignStatusError("preparation aggregate schema/status differs")
    _aggregate_text(actors["reason"])
    rows = _aggregate_rows(unified)
    for kind, row in rows.items():
        _exact(row, {"schema", "status", "reason", "observed_at", "attempted_at", "generation", "error", "data"}, "aggregate")
        if (row["schema"] != f"epyc.autokernel.{kind}_observation.v1"
                or row["status"] not in {"available", "unknown", "not_connected"}):
            raise CampaignStatusError("aggregate schema/status differs")
        _aggregate_text(row["reason"])
        _aggregate_text(row["error"], nullable=True)
        _aggregate_number(row["generation"], integer=True)
        for name in ("observed_at", "attempted_at"):
            _aggregate_scalar(name, row[name])
        if row["error"] is not None and row["status"] != "unknown":
            raise CampaignStatusError("aggregate publication error must remain unknown")
        if row["observed_at"] and row["attempted_at"] and datetime.fromisoformat(
                row["observed_at"].replace("Z", "+00:00")) > datetime.fromisoformat(row["attempted_at"].replace("Z", "+00:00")):
            raise CampaignStatusError("aggregate observation is after its attempt")
        data = row["data"]
        if data is None:
            if row["status"] == "available" or row["observed_at"] is not None:
                raise CampaignStatusError("missing aggregate cannot be available or dated")
            continue
        _exact(data, _AGGREGATE_FIELDS[kind], "aggregate data")
        if row["observed_at"] is None:
            raise CampaignStatusError("aggregate data is undated")
        for name, value in data.items():
            if name == "items":
                if not isinstance(value, list) or len(value) > {"actor": 16, "profile": 24, "calibration": 24}[kind]:
                    raise CampaignStatusError("aggregate row bound exceeded")
                for item in value:
                    _exact(item, _AGGREGATE_ITEMS[kind], "aggregate item")
                    for key, part in item.items():
                        _aggregate_scalar(key, part)
            elif name in {"reserved", "spent"}:
                _exact(value, _AGGREGATE_BUDGETS, "aggregate budgets")
                for part in value.values():
                    _aggregate_number(part)
            else:
                _aggregate_scalar(name, value)
        if "items" in data and (type(data["items_total"]) is not int or data["items_total"] < len(data["items"])
                or data["items_truncated"] != (data["items_total"] > len(data["items"]))):
            raise CampaignStatusError("aggregate sample completeness differs")
        if kind == "calibration" and (data["qualification"] != "unavailable" or data["ranking_authorized"]):
            raise CampaignStatusError("calibration observation cannot confer qualification")
        if kind == "evidence" and (data["lag_seconds"] is not None
                or data["owner_state"] not in {"ready", "pending", "failed", "closed"}
                or data["readiness"] not in {"unknown", "projected", "outage"}
                or data["ready"] != (data["owner_state"] == "ready")
                or row["status"] == "available" and not data["ready"]):
            raise CampaignStatusError("evidence aggregate readiness differs")
        if kind == "profile" and data["planning_observed_at"] != row["observed_at"]:
            raise CampaignStatusError("profile reduction timestamp differs")
        for item in data.get("items", ()):
            if kind == "calibration" and item["outcome"] not in {None, "calibration", "invalid", "failed"}:
                raise CampaignStatusError("calibration observation outcome differs")
            if kind == "actor" and (item["phase"] not in {"pending", "settled", "finished_unsettled"}
                    or item["settlement_outcome"] not in {None, "prerequisite", "failed", "invalid"}
                    or (item["phase"] == "settled") != (item["settlement_outcome"] is not None)):
                raise CampaignStatusError("actor sampled settlement differs")
            seconds = "remaining_seconds" if kind == "profile" else "retry_remaining_seconds"
            if kind in {"profile", "actor"} and not item["clock_known"] and item[seconds] is not None:
                raise CampaignStatusError("unknown clock cannot supply validity remainder")
    if actors["status"] != ("unknown" if any(rows[k]["status"] == "unknown" for k in ("actor", "profile", "calibration")) else "available"):
        raise CampaignStatusError("preparation aggregate status contradicts observations")
    if (sum(len((row["data"] or {}).get("items", ())) for row in rows.values()) > 64
            or len(json.dumps(rows, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()) > 32768):
        raise CampaignStatusError("combined aggregate bound exceeded")


def _validate_unified(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("schema") == UNIFIED_PROJECTION_SCHEMA_V3:
        _exact(value, _UNIFIED_FIELDS | {"runtime", "worker_timing"}, "unified aggregate projection")
        _validate_aggregates(value)
        legacy = dict(value, schema=UNIFIED_PROJECTION_SCHEMA_V2,
            actors={"schema": "epyc.autokernel.unified_actor_status.v1", "status": "not_connected",
                "reason": "legacy shape check", "clock_semantics": "UTC wall-clock projection; runtime fences remain monotonic", "items": []},
            evidence={"schema": "epyc.autokernel.unified_evidence_status.v1", "status": "not_connected",
                "reason": "legacy shape check", "frontier_digest": None, "lag_seconds": None})
        _validate_unified(legacy)
        return dict(value)
    runtime_aware = isinstance(value, Mapping) and value.get("schema") == UNIFIED_PROJECTION_SCHEMA_V2
    _exact(value, _UNIFIED_FIELDS | ({"runtime", "worker_timing"} if runtime_aware else set()), "unified projection")
    unified = dict(value)
    if unified["schema"] not in {UNIFIED_PROJECTION_SCHEMA, UNIFIED_PROJECTION_SCHEMA_V2}:
        raise CampaignStatusError("unified projection schema is unsupported")
    if runtime_aware:
        unified["runtime"] = _validate_runtime(unified["runtime"])
    scheduler = unified["scheduler"]
    _exact(scheduler, _UNIFIED_SCHEDULER_FIELDS, "unified scheduler")
    scheduler = dict(scheduler)
    if scheduler["schema"] != "epyc.autokernel.unified_scheduler_projection.v1":
        raise CampaignStatusError("unified scheduler schema is unsupported")
    for field in ("projection_digest", "config_digest", "policy_digest"):
        _digest(scheduler[field], f"unified scheduler {field}")
    for field in ("round_number", "accounting_epoch", "campaign_attempts",
                  "coverage_debt_count"):
        _integer(scheduler[field], f"unified scheduler {field}")
    charged = _finite(scheduler["campaign_charged_seconds"],
                      "unified scheduler campaign_charged_seconds")
    assert charged is not None
    if charged < 0:
        raise CampaignStatusError("unified scheduler campaign_charged_seconds is negative")
    if scheduler["pending_selection_digest"] is not None:
        _digest(scheduler["pending_selection_digest"],
                "unified scheduler pending_selection_digest")
    _enum(scheduler["status"], _UNIFIED_STATUSES, "unified scheduler status")
    _text(scheduler["reason"], "unified scheduler reason")
    scheduler["capacity"] = _validate_resource_vector(scheduler["capacity"])
    scheduler["accounting"] = _validate_accounting(scheduler["accounting"])
    unified["scheduler"] = scheduler

    for name, fields in _UNIFIED_SECTION_FIELDS.items():
        item = unified[name]
        _exact(item, fields, f"unified {name}")
        item = dict(item)
        if item["schema"] != _UNIFIED_SECTION_SCHEMAS[name]:
            raise CampaignStatusError(f"unified {name} schema is unsupported")
        _enum(item["status"], _UNIFIED_STATUSES, f"unified {name} status")
        _text(item["reason"], f"unified {name} reason")
        unified[name] = item

    resources = unified["resources"]
    actors = unified["actors"]
    evidence = unified["evidence"]
    candidate = unified["candidate"]
    targets = unified["targets"]
    for name in ("resources", "actors", "evidence", "candidate"):
        if unified[name]["status"] != "not_connected":
            raise CampaignStatusError(f"unified {name} v1 supports only not_connected")
    if any(resources[field] is not None for field in ("requested", "granted", "held", "used")):
        raise CampaignStatusError("disconnected unified resources must remain null")
    if (actors["clock_semantics"] !=
            "UTC wall-clock projection; runtime fences remain monotonic"
            or not isinstance(actors["items"], list) or actors["items"]):
        raise CampaignStatusError("disconnected unified actors are malformed")
    if evidence["frontier_digest"] is not None or evidence["lag_seconds"] is not None:
        raise CampaignStatusError("disconnected unified evidence must remain null")
    if any(candidate[field] is not None for field in (
            "accumulated_identity", "validated_identity", "frozen_production_identity",
            "validation_debt")):
        raise CampaignStatusError("disconnected unified candidate must remain null")
    for field in ("total", "ready", "prerequisite", "production_enrolled", "seed_enrolled"):
        _integer(targets[field], f"unified targets {field}")
    if targets["ready"] + targets["prerequisite"] != targets["total"]:
        raise CampaignStatusError("unified target counts disagree")
    if (targets["production_enrolled"] > targets["total"]
            or targets["seed_enrolled"] > targets["total"]
            or targets["items_page_ref"] is not None):
        raise CampaignStatusError("unified target enrollment/page reference is invalid")
    return unified


def validate_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CampaignStatusError("campaign snapshot must be an object")
    schema = value.get("schema")
    if schema == SNAPSHOT_SCHEMA:
        version = 1
        fields = _SNAPSHOT_FIELDS
    elif schema == SNAPSHOT_SCHEMA_V2:
        version = 2
        fields = _SNAPSHOT_V2_FIELDS
    elif schema == SNAPSHOT_SCHEMA_V3:
        version = 3
        fields = _SNAPSHOT_V3_FIELDS
    else:
        raise CampaignStatusError("campaign snapshot schema is unsupported")
    _exact(value, fields, f"campaign snapshot v{version}")
    row = copy.deepcopy(dict(value))
    if row["producer_schema"] != schema:
        raise CampaignStatusError("campaign snapshot schema is unsupported")
    build = _validate_build(row["producer_build"], "producer_build")
    _text(row["campaign_id"], "campaign_id")
    _integer(row["config_generation"], "config_generation", 1)
    _digest(row["config_digest"], "config_digest")
    _digest(row["requested_manifest_digest"], "requested_manifest_digest")
    for field, minimum in (("supervisor_incarnation", 1), ("stream_epoch", 1),
                           ("sequence", 1), ("journal_cursor", 0 if version >= 2 else 1),
                           ("control_revision", 0)):
        _integer(row[field], field, minimum)
    _timestamp(row["generated_at"], "generated_at")
    _timestamp(row["producer_heartbeat_at"], "producer_heartbeat_at")
    _timestamp(row["last_scientific_result_at"], "last_scientific_result_at",
               nullable=True)
    _timestamp(row["worker_activity_at"], "worker_activity_at", nullable=True)
    desired = _enum(row["desired_state"], _DESIRED, "campaign desired_state")
    observed = _enum(row["observed_state"], _OBSERVED if version == 1 else _OBSERVED_V2,
                     "campaign observed_state")
    active_worker = row["active_worker"]
    if version == 1 and active_worker is not None:
        raise CampaignStatusError("campaign_snapshot.v1 active_worker must be null")
    if row["execution_authorized"] is not False:
        raise CampaignStatusError(
            f"campaign_snapshot.v{version} does not establish current execution authority")
    reason = _text(row["prerequisite_reason"], "prerequisite_reason", nullable=True)
    allowed_observed = ({
        "running": {"running", "waiting_prerequisite"},
        "paused": {"paused"},
        "drained": {"drained"},
    } if version == 1 else {
        "running": {"running", "waiting_prerequisite", "ownership_unresolved"},
        "paused": {"paused", "pausing", "ownership_unresolved"},
        "drained": {"drained", "draining", "ownership_unresolved"},
    })
    if observed not in allowed_observed[desired]:
        raise CampaignStatusError("campaign desired and observed states contradict")
    if ((observed == "waiting_prerequisite" and reason is None)
            or (observed in {"running", "drained"} and reason is not None)):
        raise CampaignStatusError("campaign prerequisite reason contradicts observed state")
    if not isinstance(row["command_results"], list):
        raise CampaignStatusError("command_results must be an array")
    result_validator = _validate_result_v1 if version == 1 else _validate_result_v2
    results = [result_validator(item) for item in row["command_results"]]
    request_ids = [item["request_id"] for item in results]
    revisions = [item["control_revision"] for item in results]
    if len(set(request_ids)) != len(request_ids) or len(set(revisions)) != len(revisions):
        raise CampaignStatusError("command_results contain duplicate identities/revisions")
    if revisions != sorted(revisions) or (revisions and revisions[-1] > row["control_revision"]):
        raise CampaignStatusError("command_results are not in control revision order")
    generated = datetime.fromisoformat(row["generated_at"].replace("Z", "+00:00")).timestamp()
    if version >= 2:
        if not isinstance(row["execution_capability_available"], bool):
            raise CampaignStatusError("v2 execution capability flag must be boolean")
        _integer(row["worker_lifecycle_revision"], "worker_lifecycle_revision", 0)
        if active_worker is not None:
            active_worker = _validate_active_worker_v2(active_worker)
            if row["worker_activity_at"] != active_worker["activity_at"]:
                raise CampaignStatusError("v2 worker activity clocks disagree")
            if active_worker["control_revision"] > row["control_revision"]:
                raise CampaignStatusError("v2 active worker is from a future control revision")
            if observed in {"paused", "drained", "waiting_prerequisite"}:
                raise CampaignStatusError(
                    "v2 quiescent snapshot cannot carry an active worker")
            if (active_worker["state"] in {"teardown_failed", "unresolved"}
                    and (observed != "ownership_unresolved" or reason is None)):
                raise CampaignStatusError(
                    "v2 unresolved worker lacks unresolved ownership state")
        elif row["worker_activity_at"] is not None:
            raise CampaignStatusError("v2 snapshot has worker activity without active worker")
        if (active_worker is None and observed == "ownership_unresolved"
                and (reason is None
                     or not reason.startswith("worker_acquisition_pending:")
                     or not reason.removeprefix(
                         "worker_acquisition_pending:").strip())):
            raise CampaignStatusError(
                "v2 null-worker ownership state lacks acquisition-pending identity")
        if active_worker is None and observed in {"pausing", "draining"}:
            operation = "pause" if observed == "pausing" else "drain"
            has_basis = any(
                result["operation"] == operation
                and result["desired_state"] == desired
                and result["observed_state"] == observed
                and not result["completed"]
                for result in results
            )
            if not has_basis:
                raise CampaignStatusError(
                    "v2 settling snapshot lacks an active worker or accepted command basis")
        row["active_worker"] = active_worker
        for result in results:
            accepted_at = datetime.fromisoformat(
                result["accepted_at"].replace("Z", "+00:00")).timestamp()
            if accepted_at > generated + MAX_CLOCK_SKEW_S:
                raise CampaignStatusError("command accepted_at is later than snapshot generation")
            if result["completed"]:
                completed_at = datetime.fromisoformat(
                    result["completed_at"].replace("Z", "+00:00")).timestamp()
                if completed_at < accepted_at or completed_at > generated + MAX_CLOCK_SKEW_S:
                    raise CampaignStatusError("command completion timestamp is contradictory")
    for field in ("producer_heartbeat_at", "worker_activity_at",
                  "last_scientific_result_at"):
        if row[field] is not None:
            event_time = datetime.fromisoformat(row[field].replace("Z", "+00:00")).timestamp()
            if event_time > generated + MAX_CLOCK_SKEW_S:
                raise CampaignStatusError(f"{field} is later than snapshot generation")
    if version >= 2 and active_worker is not None:
        for field in ("started_at", "activity_at"):
            if active_worker[field] is not None:
                event_time = datetime.fromisoformat(
                    active_worker[field].replace("Z", "+00:00")).timestamp()
                if event_time > generated + MAX_CLOCK_SKEW_S:
                    raise CampaignStatusError(
                        f"active_worker {field} is later than snapshot generation")
    row["producer_build"] = dict(build)
    row["command_results"] = results
    if version == 3:
        row["unified"] = _validate_unified(row["unified"])
        if row["unified"]["schema"] == UNIFIED_PROJECTION_SCHEMA_V3:
            for aggregate in _aggregate_rows(row["unified"]).values():
                for field in ("observed_at", "attempted_at"):
                    if aggregate[field] is not None and datetime.fromisoformat(aggregate[field].replace("Z", "+00:00")).timestamp() > generated:
                        raise CampaignStatusError("aggregate timestamp is newer than snapshot")
        if "runtime" in row["unified"]:
            worker, timing = row["active_worker"], row["unified"]["worker_timing"]
            if worker is None:
                if timing is not None:
                    raise CampaignStatusError("runtime timing has no original worker")
            else:
                _exact(timing, frozenset({"worker_id", "worker_generation", "lifecycle_revision",
                    "checked_at", "state", "remaining_seconds"}), "runtime worker timing")
                _integer(timing["worker_generation"], "timing worker generation", 1)
                _integer(timing["lifecycle_revision"], "timing lifecycle revision")
                if (timing["worker_id"] != worker["worker_id"]
                        or timing["worker_generation"] != worker["worker_generation"]
                        or timing["lifecycle_revision"] != row["worker_lifecycle_revision"]
                        or timing["checked_at"] != row["generated_at"]):
                    raise CampaignStatusError("runtime timing original identity differs")
                _enum(timing["state"], {"within_deadline", "deadline_elapsed", "clock_unavailable"},
                      "runtime timing state")
                if timing["state"] == "clock_unavailable":
                    if timing["remaining_seconds"] is not None:
                        raise CampaignStatusError("unknown clock cannot supply a remainder")
                else:
                    remaining = _finite(timing["remaining_seconds"], "runtime timing remainder")
                    if remaining < 0 or (remaining > 0) != (timing["state"] == "within_deadline"):
                        raise CampaignStatusError("runtime timing remainder differs")
        runtime = row["unified"].get("runtime")
        if runtime is not None and runtime["observed_at"] is not None and \
                datetime.fromisoformat(runtime["observed_at"].replace("Z", "+00:00")) > \
                datetime.fromisoformat(row["generated_at"].replace("Z", "+00:00")):
            raise CampaignStatusError("runtime observation is newer than snapshot")
    return row


def _configured() -> dict[str, Any]:
    root = os.environ.get(STORE_ROOT_ENV)
    if not root:
        return {"configured": False}
    generation = os.environ.get(CONFIG_GENERATION_ENV)
    try:
        generation_value = int(generation) if generation is not None else None
    except ValueError:
        generation_value = None
    if generation_value is None or generation_value < 1:
        raise CampaignStatusError(f"{CONFIG_GENERATION_ENV} must be a positive integer")
    campaign_id = _text(os.environ.get(CAMPAIGN_ID_ENV), CAMPAIGN_ID_ENV)
    config_digest = _digest(os.environ.get(CONFIG_DIGEST_ENV), CONFIG_DIGEST_ENV)
    return {"configured": True, "root": Path(root), "campaign_id": campaign_id,
            "config_generation": generation_value, "config_digest": config_digest,
            "gateway_url": os.environ.get(GATEWAY_URL_ENV),
            "hub_origin": os.environ.get(HUB_ORIGIN_ENV)}


def read() -> dict[str, Any]:
    try:
        config = _configured()
    except CampaignStatusError as exc:
        return {"configured": True, "artifact_present": False, "snapshot": None,
                "error": f"campaign configuration invalid: {exc}"}
    if not config["configured"]:
        return {"configured": False, "artifact_present": False, "snapshot": None,
                "error": None}
    path = config["root"] / SNAPSHOT_FILENAME
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return config | {"artifact_present": False, "snapshot": None,
                         "path": str(path), "error": "configured campaign snapshot is absent"}
    except (OSError, UnicodeError) as exc:
        return config | {"artifact_present": path.exists(), "snapshot": None,
                         "path": str(path), "error": f"campaign snapshot unreadable: {exc}"}
    try:
        snapshot = validate_snapshot(json.loads(raw))
        if (snapshot["campaign_id"] != config["campaign_id"]
                or snapshot["config_generation"] != config["config_generation"]
                or snapshot["config_digest"] != config["config_digest"]):
            raise CampaignStatusError("snapshot campaign/config identity differs from selection")
    except (json.JSONDecodeError, CampaignStatusError) as exc:
        return config | {"artifact_present": True, "snapshot": None,
                         "path": str(path), "error": f"campaign snapshot malformed: {exc}"}
    return config | {"artifact_present": True, "snapshot": snapshot,
                     "path": str(path), "error": None,
                     "content_digest": hashlib.sha256(raw.encode()).hexdigest()}


def _gateway_health_url(value: Any) -> str:
    url = _text(value, GATEWAY_URL_ENV)
    assert isinstance(url, str)
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment):
        raise CampaignStatusError("campaign gateway URL must be an http(s) origin/base without credentials")
    return url.rstrip("/") + "/health"


def validate_health(value: Any) -> dict[str, Any]:
    _exact(value, _HEALTH_FIELDS, "campaign transport health")
    row = dict(value)
    if row["schema"] != HEALTH_SCHEMA or not isinstance(row["ok"], bool):
        raise CampaignStatusError("campaign transport health schema/status is invalid")
    if row["transport"] != "campaign-control-http":
        raise CampaignStatusError("campaign transport health kind is unsupported")
    _enum(row["producer"], {"running", "failed"}, "campaign transport producer state")
    _text(row["campaign_id"], "health.campaign_id")
    row["service_build"] = _validate_build(row["service_build"], "health.service_build")
    _integer(row["config_generation"], "health.config_generation", 1)
    _digest(row["config_digest"], "health.config_digest")
    _integer(row["supervisor_incarnation"], "health.supervisor_incarnation", 1)
    _integer(row["stream_epoch"], "health.stream_epoch", 1)
    _text(row["allowed_origin"], "health.allowed_origin", nullable=True)
    _text(row["error"], "health.error", nullable=True)
    if row["ok"] != (row["producer"] == "running"):
        raise CampaignStatusError("campaign transport status contradicts producer state")
    if (row["ok"] and row["error"] is not None) or (not row["ok"] and row["error"] is None):
        raise CampaignStatusError("campaign transport error contradicts status")
    return row


def advance_snapshot(previous: Mapping[str, Any] | None,
                     candidate: Mapping[str, Any], *,
                     allow_campaign_switch: bool = False) -> dict[str, Any]:
    """Accept one complete ordered snapshot; never merge partial generations."""
    new = validate_snapshot(candidate)
    if previous is None:
        return {"status": "accepted", "snapshot": new}
    old = validate_snapshot(previous)
    old_identity = (old["campaign_id"], old["config_generation"], old["config_digest"])
    new_identity = (new["campaign_id"], new["config_generation"], new["config_digest"])
    if old_identity != new_identity:
        if not allow_campaign_switch:
            raise CampaignStatusError("campaign switch requires explicit selection")
        return {"status": "switched", "snapshot": new}
    protocol_rank = {SNAPSHOT_SCHEMA: 1, SNAPSHOT_SCHEMA_V2: 2, SNAPSHOT_SCHEMA_V3: 3}
    if protocol_rank[new["schema"]] < protocol_rank[old["schema"]]:
        raise CampaignStatusError("same campaign cannot downgrade snapshot protocol")
    old_key = (old["stream_epoch"], old["sequence"])
    new_key = (new["stream_epoch"], new["sequence"])
    if new_key < old_key:
        return {"status": "older", "snapshot": old}
    if new_key == old_key:
        old_digest = hashlib.sha256(json.dumps(
            old, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        new_digest = hashlib.sha256(json.dumps(
            new, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if old_digest != new_digest:
            raise CampaignStatusError("same stream key has different snapshot content")
        return {"status": "duplicate", "snapshot": old}
    if new["stream_epoch"] == old["stream_epoch"]:
        if (new["journal_cursor"] < old["journal_cursor"]
                or new["control_revision"] < old["control_revision"]
                or new["supervisor_incarnation"] != old["supervisor_incarnation"]):
            raise CampaignStatusError("newer sequence rolls back cursor/control/incarnation")
    elif new["stream_epoch"] <= old["stream_epoch"]:
        return {"status": "older", "snapshot": old}
    if (new["stream_epoch"] != old["stream_epoch"]
            and (new["control_revision"] < old["control_revision"]
                 or new["journal_cursor"] < old["journal_cursor"]
                 or new["supervisor_incarnation"] <= old["supervisor_incarnation"])):
        raise CampaignStatusError("new epoch rolls back cursor/control/incarnation")
    if protocol_rank[new["schema"]] >= 2 and protocol_rank[old["schema"]] >= 2:
        if new["worker_lifecycle_revision"] < old["worker_lifecycle_revision"]:
            raise CampaignStatusError("newer snapshot rolls back worker lifecycle revision")
        old_worker, new_worker = old["active_worker"], new["active_worker"]
        if (new["worker_lifecycle_revision"] == old["worker_lifecycle_revision"]
                and new_worker != old_worker):
            raise CampaignStatusError(
                "worker changed without a worker lifecycle revision")
        if old_worker is not None and new_worker is not None \
                and old_worker["worker_id"] != new_worker["worker_id"] \
                and new_worker["worker_generation"] <= old_worker["worker_generation"]:
            raise CampaignStatusError("new worker does not advance worker generation")
    old_runtime = (old.get("unified") or {}).get("runtime")
    new_runtime = (new.get("unified") or {}).get("runtime")
    if (old.get("unified") or {}).get("schema") == UNIFIED_PROJECTION_SCHEMA_V3:
        if (new.get("unified") or {}).get("schema") != UNIFIED_PROJECTION_SCHEMA_V3:
            raise CampaignStatusError("same campaign cannot downgrade aggregate projection")
        if new["supervisor_incarnation"] == old["supervisor_incarnation"]:
            before, after = _aggregate_rows(old["unified"]), _aggregate_rows(new["unified"])
            for kind in before:
                if after[kind]["generation"] < before[kind]["generation"]:
                    raise CampaignStatusError("aggregate source generation rolled back")
                for name in ("observed_at", "attempted_at"):
                    left, right = before[kind][name], after[kind][name]
                    if left is not None and (right is None or datetime.fromisoformat(right.replace("Z", "+00:00")) < datetime.fromisoformat(left.replace("Z", "+00:00"))):
                        raise CampaignStatusError("aggregate source/attempt time rolled back")
    if old_runtime is not None:
        if new_runtime is None:
            raise CampaignStatusError("same campaign cannot downgrade runtime projection")
        if new["supervisor_incarnation"] == old["supervisor_incarnation"]:
            if (new_runtime["observation_sequence"] < old_runtime["observation_sequence"]
                    or new_runtime["observation_sequence"] == old_runtime["observation_sequence"]
                    and new_runtime != old_runtime):
                raise CampaignStatusError("runtime observation sequence rolled back or changed")
            old_time, new_time = old_runtime["observed_at"], new_runtime["observed_at"]
            if old_time is not None and (new_time is None or
                    datetime.fromisoformat(new_time.replace("Z", "+00:00")) <
                    datetime.fromisoformat(old_time.replace("Z", "+00:00"))):
                raise CampaignStatusError("runtime observation time rolled back")
    return {"status": "accepted", "snapshot": new}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, _request, _fp, _code, _msg, _headers, _newurl):
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirect()).open


def _fetch_health(report: Mapping[str, Any], *, timeout: float,
                  opener) -> dict[str, Any]:
    snapshot = report.get("snapshot")
    gateway = report.get("gateway_url")
    if snapshot is None or not gateway:
        return {"state": "unknown", "matched": False,
                "reason": "no readable snapshot or configured gateway health URL"}
    try:
        url = _gateway_health_url(gateway)
        response = opener(Request(url, method="GET"), timeout=timeout)
        try:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            if final_url != url:
                raise CampaignStatusError("campaign transport health redirect is refused")
            raw = response.read(MAX_HEALTH_BODY + 1)
            if len(raw) > MAX_HEALTH_BODY:
                raise CampaignStatusError("campaign transport health body is too large")
            body = validate_health(json.loads(raw))
        finally:
            response.close()
    except (OSError, HTTPError, URLError, UnicodeError, ValueError, json.JSONDecodeError,
            CampaignStatusError) as exc:
        return {"state": "unknown", "matched": False,
                "reason": f"campaign transport health unavailable: {exc}"}
    fields = ("campaign_id", "config_generation", "config_digest",
              "supervisor_incarnation", "stream_epoch")
    if any(body[field] != snapshot[field] for field in fields):
        return {"state": "mismatch", "matched": False,
                "reason": "health identity does not match durable snapshot", "identity": body}
    if not body["ok"]:
        return {"state": "failed", "matched": True,
                "reason": "campaign transport reports failure", "identity": body}
    return {"state": "live", "matched": True, "reason": "identity-matched transport",
            "identity": body}


class _HealthProbeCache:
    """One daemon owns health I/O; dashboard requests only await a tiny fixed budget."""

    def __init__(self, *, clock=time.monotonic) -> None:
        self._condition = threading.Condition()
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._pending: tuple[Any, ...] | None = None
        self._result: tuple[tuple[Any, ...], float, dict[str, Any]] | None = None
        self._clock = clock
        self._thread: threading.Thread | None = None
        self._closed = False
        self._close_incomplete = False

    def _ensure_owner_locked(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._run, name="campaign-health-probe", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            key, report, timeout, opener, observation_deadline = item
            try:
                result = _fetch_health(report, timeout=timeout, opener=opener)
            except Exception as exc:  # noqa: BLE001 -- keep the sole probe worker alive
                result = {"state": "unknown", "matched": False,
                          "reason": f"campaign transport health probe failed: {type(exc).__name__}"}
            with self._condition:
                completed_at = self._clock()
                if completed_at > observation_deadline:
                    result = {"state": "unknown", "matched": False,
                              "reason": "campaign transport health observation completed too late"}
                self._result = (key, completed_at, result)
                if self._pending == key:
                    self._pending = None
                self._condition.notify_all()
                if self._closed:
                    return

    def poll(self, key: tuple[Any, ...], report: Mapping[str, Any], *, timeout: float,
             opener, wait_s: float = HEALTH_RESULT_WAIT_S) -> dict[str, Any]:
        clock = getattr(self, "_clock", time.monotonic)
        deadline = clock() + wait_s
        with self._condition:
            if getattr(self, "_closed", False):
                reason = ("campaign transport health cache close is incomplete"
                          if getattr(self, "_close_incomplete", False)
                          else "campaign transport health cache is closed")
                return {"state": "unknown", "matched": False, "reason": reason}
            if (self._result is not None and self._result[0] == key
                    and clock() - self._result[1] <= HEALTH_CACHE_TTL_S):
                return dict(self._result[2])
            if self._pending is None:
                self._ensure_owner_locked()
                self._pending = key
                started_at = clock()
                self._queue.put_nowait(
                    (key, dict(report), timeout, opener, started_at + timeout))
            while self._pending == key and clock() < deadline:
                self._condition.wait(deadline - clock())
            if (self._result is not None and self._result[0] == key
                    and clock() - self._result[1] <= HEALTH_CACHE_TTL_S):
                return dict(self._result[2])
        return {"state": "unknown", "matched": False,
                "reason": "campaign transport health probe is pending or unavailable"}

    def close(self, timeout: float = 1.0) -> bool:
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(float(timeout)) or timeout < 0):
            raise CampaignStatusError("health cache close timeout must be finite and nonnegative")
        with self._condition:
            self._closed = True
            thread = self._thread
            if thread is None:
                self._close_incomplete = False
                return True
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
        thread.join(timeout=float(timeout))
        with self._condition:
            self._close_incomplete = thread.is_alive()
            return not self._close_incomplete

    @property
    def close_incomplete(self) -> bool:
        with self._condition:
            return self._close_incomplete


_HEALTH_CACHE = _HealthProbeCache()


def observe_health(report: Mapping[str, Any], *, timeout: float = HEALTH_TIMEOUT_S,
                   opener=_NO_REDIRECT_OPENER,
                   cache: _HealthProbeCache | None = None) -> dict[str, Any]:
    snapshot = report.get("snapshot")
    gateway = report.get("gateway_url")
    if snapshot is None or not gateway:
        return {"state": "unknown", "matched": False,
                "reason": "no readable snapshot or configured gateway health URL"}
    key = (gateway, id(opener), snapshot["campaign_id"], snapshot["config_generation"],
           snapshot["config_digest"], snapshot["supervisor_incarnation"],
           snapshot["stream_epoch"])
    return (cache or _HEALTH_CACHE).poll(key, report, timeout=timeout, opener=opener)


def _age(stamp: str | None, now: float) -> float | None:
    if stamp is None:
        return None
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    delta = now - parsed
    if delta < -MAX_CLOCK_SKEW_S:
        return None
    return round(max(0.0, delta), 1)


def runtime_freshness(body: Mapping[str, Any], *, now: float) -> dict[str, Any] | None:
    observation = (body.get("unified") or {}).get("runtime")
    if observation is None:
        return None  # old projections make no runtime-progress claim
    age = _age(observation["observed_at"], now)
    if observation["publication_error"] is not None:
        return {"state": "unknown", "age_s": age, "activity_age_s": None,
                "activity_silent": False,
                "reason": "runtime observation publication failed: " + observation["publication_error"]}
    worker = body.get("active_worker")
    if worker is not None:
        activity_age = _age(worker["activity_at"] or worker["started_at"], now)
        unresolved = worker["state"] in {"unresolved", "teardown_failed"}
        timing = body["unified"]["worker_timing"]
        checked_age = _age(timing["checked_at"], now)
        state = "unknown"
        if unresolved:
            state = "unresolved"
        elif checked_age is not None and timing["state"] != "clock_unavailable":
            state = ("in_progress" if timing["remaining_seconds"] > checked_age else "stale")
        return {"state": state,
                "age_s": age, "activity_age_s": activity_age,
                "activity_silent": activity_age is None or activity_age > HEARTBEAT_STALE_AFTER_S,
                "reason": ({"unresolved": "owned worker unresolved",
                    "unknown": "owned deadline unavailable or future-dated; activity is not inferred",
                    "stale": "original owned deadline elapsed; publisher heartbeat is not worker progress",
                    "in_progress": "owned stage remains within its original deadline; silence is not progress"
                    }[state])}
    if observation["status"] == "not_reported" or age is None:
        return {"state": "unknown", "age_s": age, "activity_age_s": None,
                "activity_silent": False, "reason": "runtime observation is absent or undated"}
    budget = HEARTBEAT_STALE_AFTER_S + observation["retry_after_seconds"]
    state = "stale" if age > budget else "current"
    if observation["status"] == "recovery_required":
        state = "unresolved"
    return {"state": state, "age_s": age, "activity_age_s": None,
            "activity_silent": False, "reason": observation["reason"]}


def aggregate_freshness(body: Mapping[str, Any], *, now: float) -> dict[str, Any] | None:
    unified = body.get("unified") or {}
    if unified.get("schema") != UNIFIED_PROJECTION_SCHEMA_V3:
        return None
    result = {}
    for kind, row in _aggregate_rows(unified).items():
        age, attempt_age = _age(row["observed_at"], now), _age(row["attempted_at"], now)
        state = "current"
        reason = row["reason"]
        if row["status"] == "not_connected":
            state = "not_connected"
        elif row["error"] is not None or row["status"] == "unknown" or age is None:
            state = "unknown"
        elif age > HEARTBEAT_STALE_AFTER_S:
            state, reason = "historical", "source observation aged; publisher/refresh attempt is not source progress"
        expired = unknown = 0
        if kind == "profile" and row["data"] is not None:
            for item in row["data"]["items"]:
                if item["profile_digest"] is None:
                    continue
                if age is None or not item["clock_known"] or item["remaining_seconds"] is None:
                    unknown += 1
                elif item["remaining_seconds"] <= age:
                    expired += 1
            if expired or unknown:
                state = "unknown"
                reason = "sampled profile validity expired/unknown; planning totals are historical, not current eligibility"
        result[kind] = {"state": state, "age_s": age, "attempt_age_s": attempt_age,
            "reason": reason, "expired_sample_count": expired,
            "unknown_validity_sample_count": unknown}
    return result


def snapshot(*, now: float | None = None, health_opener=_NO_REDIRECT_OPENER,
             health_cache: _HealthProbeCache | None = None) -> dict[str, Any]:
    report = read()
    if not report.get("configured"):
        return {"configured": False, "state": "legacy", "campaign": None,
                "controls": {"available": False, "reason": "unified campaign is not configured"}}
    body = report.get("snapshot")
    if body is None:
        return {"configured": True, "state": "malformed" if report.get("artifact_present") else "absent",
                "campaign": None, "error": report.get("error"),
                "controls": {"available": False, "reason": report.get("error")}}
    if (now is not None and (isinstance(now, bool) or not isinstance(now, (int, float))
                             or not math.isfinite(float(now)))):
        raise CampaignStatusError("now must be a finite number")
    current = time.time() if now is None else float(now)
    health = observe_health(report, opener=health_opener, cache=health_cache)
    clocks = {name: {"timestamp": body[name], "age_s": _age(body[name], current),
                     "state": ("unknown" if body[name] is None else
                               "future" if _age(body[name], current) is None else "known")}
              for name in ("producer_heartbeat_at", "worker_activity_at",
                           "last_scientific_result_at")}
    heartbeat_age = clocks["producer_heartbeat_at"]["age_s"]
    runtime_clock = runtime_freshness(body, now=current)
    aggregate_clock = aggregate_freshness(body, now=current)
    live = health["state"] == "live" and heartbeat_age is not None \
        and heartbeat_age <= HEARTBEAT_STALE_AFTER_S
    terminal = body["observed_state"] == "drained"
    worker = body.get("active_worker")
    unresolved = (body["observed_state"] == "ownership_unresolved"
                  or (worker is not None
                      and worker["state"] in {"teardown_failed", "unresolved"}))
    unified_stuck = (body["schema"] == SNAPSHOT_SCHEMA_V3
                     and any(body["unified"][name]["status"] != "available"
                             for name in ("scheduler", "resources", "actors", "evidence",
                                          "candidate", "targets")))
    if runtime_clock is not None and runtime_clock["state"] in {"unknown", "stale", "unresolved"}:
        unified_stuck = True
    if aggregate_clock is not None and any(row["state"] != "current" for row in aggregate_clock.values()):
        unified_stuck = True
    if live and not unresolved and not unified_stuck:
        state = "live"
    elif unresolved or (live and unified_stuck) or health["state"] in {"failed", "mismatch"}:
        state = "degraded"
    elif terminal or health["state"] == "unknown":
        state = "history"
    else:
        state = "degraded"
    gateway = report.get("gateway_url")
    origin = report.get("hub_origin")
    health_origin = (health.get("identity") or {}).get("allowed_origin")
    controls = {"available": bool(live and not unresolved and gateway and origin
                                  and health_origin == origin),
                "gateway_url": gateway, "hub_origin": origin,
                "reason": None}
    if not controls["available"]:
        controls["reason"] = (
            "controls require a live identity-matched producer, explicit browser-reachable "
            "gateway URL, and exact allowed hub origin")
    return {"configured": True, "state": state, "campaign": body,
            "snapshot_digest": report["content_digest"], "health": health,
            "clocks": clocks, "runtime_freshness": runtime_clock, "aggregate_freshness": aggregate_clock,
            "controls": controls, "evidence": report.get("path")}


__all__ = [
    "CAMPAIGN_ID_ENV", "CONFIG_DIGEST_ENV", "CONFIG_GENERATION_ENV",
    "GATEWAY_URL_ENV", "HEALTH_SCHEMA", "HEALTH_TIMEOUT_S", "HUB_ORIGIN_ENV",
    "SNAPSHOT_FILENAME", "SNAPSHOT_SCHEMA", "SNAPSHOT_SCHEMA_V2", "SNAPSHOT_SCHEMA_V3",
    "STORE_ROOT_ENV", "UNIFIED_PROJECTION_SCHEMA",
    "CampaignStatusError",
    "advance_snapshot", "observe_health", "read", "snapshot", "validate_health",
    "validate_snapshot",
]

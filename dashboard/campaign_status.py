"""Strict hub-side reader for the research-owned campaign snapshot.

The hub never imports the research package.  A durable snapshot is history;
only a matching transport-health identity can make its producer live.
"""
from __future__ import annotations

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
    else:
        raise CampaignStatusError("campaign snapshot schema is unsupported")
    _exact(value, fields, f"campaign snapshot v{version}")
    row = dict(value)
    if row["producer_schema"] != schema:
        raise CampaignStatusError("campaign snapshot schema is unsupported")
    build = _validate_build(row["producer_build"], "producer_build")
    _text(row["campaign_id"], "campaign_id")
    _integer(row["config_generation"], "config_generation", 1)
    _digest(row["config_digest"], "config_digest")
    _digest(row["requested_manifest_digest"], "requested_manifest_digest")
    for field, minimum in (("supervisor_incarnation", 1), ("stream_epoch", 1),
                           ("sequence", 1), ("journal_cursor", 0 if version == 2 else 1),
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
    if version == 2:
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
    if version == 2 and active_worker is not None:
        for field in ("started_at", "activity_at"):
            if active_worker[field] is not None:
                event_time = datetime.fromisoformat(
                    active_worker[field].replace("Z", "+00:00")).timestamp()
                if event_time > generated + MAX_CLOCK_SKEW_S:
                    raise CampaignStatusError(
                        f"active_worker {field} is later than snapshot generation")
    row["producer_build"] = dict(build)
    row["command_results"] = results
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
    if old["schema"] == SNAPSHOT_SCHEMA_V2 and new["schema"] == SNAPSHOT_SCHEMA:
        raise CampaignStatusError("same campaign cannot downgrade snapshot protocol v2 to v1")
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
    if new["schema"] == SNAPSHOT_SCHEMA_V2 and old["schema"] == SNAPSHOT_SCHEMA_V2:
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
    live = health["state"] == "live" and heartbeat_age is not None \
        and heartbeat_age <= HEARTBEAT_STALE_AFTER_S
    terminal = body["observed_state"] == "drained"
    worker = body.get("active_worker")
    unresolved = (body["observed_state"] == "ownership_unresolved"
                  or (worker is not None
                      and worker["state"] in {"teardown_failed", "unresolved"}))
    if live and not unresolved:
        state = "live"
    elif unresolved or health["state"] in {"failed", "mismatch"}:
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
            "clocks": clocks, "controls": controls, "evidence": report.get("path")}


__all__ = [
    "CAMPAIGN_ID_ENV", "CONFIG_DIGEST_ENV", "CONFIG_GENERATION_ENV",
    "GATEWAY_URL_ENV", "HEALTH_SCHEMA", "HEALTH_TIMEOUT_S", "HUB_ORIGIN_ENV",
    "SNAPSHOT_FILENAME", "SNAPSHOT_SCHEMA", "SNAPSHOT_SCHEMA_V2", "STORE_ROOT_ENV",
    "CampaignStatusError",
    "advance_snapshot", "observe_health", "read", "snapshot", "validate_health",
    "validate_snapshot",
]

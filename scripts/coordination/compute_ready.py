#!/usr/bin/env python3
"""Pure, replayable compute-ready projection and deterministic window planner.

This module deliberately has no session-bus imports and no default live paths. It
reads explicit immutable fixture/receipt paths, validates authority and lifecycle,
and writes only a caller-named derived output. Source JSON/JSONL files are never
modified. Window grades are labels, not an ordering; compatibility is decided by
exact labels plus explicit resource, model, bandwidth, VRAM, duration and weight
constraints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "compute_ready.projection.v1"
CHECKPOINT_SCHEMA = "compute_ready.checkpoint.v1"
INTAKE_SCHEMA = "compute_ready.intake.v1"
WINDOW_SCHEMA = "compute_ready.window.v1"
GRADES = {"small-model-only", "load-then-keep-hot", "full-idle"}
PRIORITY_ORDER = {"production-live": 0, "operator-directed": 1, "background-churn": 2}
CONTENTION = {"exclusive-contiguous", "resumable"}
TRANSITIONS = {
    "submitted": {"admitted", "duplicate", "needs-info", "rejected"},
    "admitted": {"ready"},
    "ready": {"planned"},
    "planned": {"granted", "denied"},
    "granted": {"running"},
    "running": {"terminal"},
    "duplicate": set(), "needs-info": set(), "rejected": set(),
    "denied": set(), "terminal": set(),
}


class ContractError(Exception):
    def __init__(self, code: str, detail: str, *, ref: str | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.ref = ref

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "detail": self.detail}
        if self.ref:
            value["ref"] = self.ref
        return value


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n").encode("utf-8")


def object_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_time(value: Any, ref: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError("invalid_timestamp", f"{ref} must be a non-empty RFC3339 timestamp",
                            ref=ref)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("invalid_timestamp", f"{ref} is not RFC3339: {value!r}", ref=ref) from exc
    if parsed.tzinfo is None:
        raise ContractError("invalid_timestamp", f"{ref} must carry a UTC offset", ref=ref)
    return parsed.astimezone(timezone.utc)


def _required(row: dict, fields: tuple[str, ...], ref: str) -> None:
    missing = [field for field in fields if field not in row]
    if missing:
        raise ContractError("missing_field", f"{ref} is missing {', '.join(missing)}", ref=ref)


def _nonempty_strings(value: Any, ref: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v for v in value):
        raise ContractError("missing_evidence" if "evidence" in ref else "invalid_field",
                            f"{ref} must be a non-empty list of strings", ref=ref)
    if len(set(value)) != len(value):
        raise ContractError("duplicate_value", f"{ref} contains duplicates", ref=ref)
    return value


def read_records(path: Path) -> list[dict]:
    """Read JSONL, a JSON array, or {events:[...]}; never mutate or normalize source."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError("input_unreadable", f"cannot read {path}: {exc}", ref=str(path)) from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise ContractError("input_invalid_json", f"invalid JSON in {path}: {exc}",
                                ref=str(path)) from exc
    else:
        if isinstance(value, dict):
            value = value.get("events", [value])
        rows = value
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ContractError("input_wrong_shape", f"{path} must contain records", ref=str(path))
    return rows


def validate_checkpoint(row: dict, ref: str) -> dict:
    _required(row, ("schema_version", "kind", "event_id", "author", "ts", "blocker_id",
                    "task_id", "task_text", "spec_ref", "checkpoint_ref", "checkpoint_sha256",
                    "validated", "graph_node_id", "priority_class", "must_run", "expires_at",
                    "evidence_refs", "operator_gates", "requirements"), ref)
    if row["schema_version"] != CHECKPOINT_SCHEMA or row["kind"] != "compute-blocker":
        raise ContractError("wrong_schema", f"{ref} is not a compute-blocker checkpoint", ref=ref)
    if row["validated"] is not True:
        raise ContractError("checkpoint_unvalidated", f"{ref} was not validated", ref=ref)
    for field in ("event_id", "author", "blocker_id", "task_id", "task_text", "spec_ref",
                  "checkpoint_ref", "graph_node_id"):
        if not isinstance(row[field], str) or not row[field]:
            raise ContractError("invalid_field", f"{ref}.{field} must be non-empty", ref=ref)
    if (not isinstance(row["checkpoint_sha256"], str)
            or len(row["checkpoint_sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in row["checkpoint_sha256"].lower())):
        raise ContractError("invalid_checkpoint_hash", f"{ref}.checkpoint_sha256 is not SHA-256", ref=ref)
    submitted_at = parse_time(row["ts"], f"{ref}.ts")
    expires_at = parse_time(row["expires_at"], f"{ref}.expires_at")
    if expires_at <= submitted_at:
        raise ContractError("invalid_expiry", f"{ref}.expires_at must be after ts", ref=ref)
    _nonempty_strings(row["evidence_refs"], f"{ref}.evidence_refs")
    if (not isinstance(row["operator_gates"], list)
            or any(not isinstance(gate, str) or not gate for gate in row["operator_gates"])):
        raise ContractError("invalid_field", f"{ref}.operator_gates must be a string list", ref=ref)
    if row["priority_class"] not in PRIORITY_ORDER:
        raise ContractError("invalid_priority", f"{ref} has unknown priority class", ref=ref)
    if not isinstance(row["must_run"], bool):
        raise ContractError("invalid_field", f"{ref}.must_run must be boolean", ref=ref)

    req = row["requirements"]
    if not isinstance(req, dict):
        raise ContractError("invalid_field", f"{ref}.requirements must be an object", ref=ref)
    _required(req, ("compatible_window_grades", "required_devices", "cpu_bandwidth_class",
                    "gpu_vram_bytes", "duration_seconds", "contention_class", "pausable",
                    "model"), f"{ref}.requirements")
    grades = set(_nonempty_strings(req["compatible_window_grades"],
                                   f"{ref}.requirements.compatible_window_grades"))
    if not grades <= GRADES:
        raise ContractError("unknown_grade", f"{ref} names unknown grade(s): {sorted(grades-GRADES)}",
                            ref=ref)
    _nonempty_strings(req["required_devices"], f"{ref}.requirements.required_devices")
    if not isinstance(req["cpu_bandwidth_class"], str) or not req["cpu_bandwidth_class"]:
        raise ContractError("invalid_bandwidth", f"{ref} requires a bandwidth label", ref=ref)
    for field in ("gpu_vram_bytes", "duration_seconds"):
        if not isinstance(req[field], int) or req[field] < 0:
            raise ContractError("invalid_resource", f"{ref}.requirements.{field} must be >= 0", ref=ref)
    if req["duration_seconds"] == 0:
        raise ContractError("invalid_duration", f"{ref} duration must be positive", ref=ref)
    if req["contention_class"] not in CONTENTION or not isinstance(req["pausable"], bool):
        raise ContractError("invalid_contention", f"{ref} has invalid contention/pausability", ref=ref)
    model = req["model"]
    if not isinstance(model, dict):
        raise ContractError("invalid_model", f"{ref}.requirements.model must be an object", ref=ref)
    _required(model, ("model_id", "weight_id", "size_bytes", "load_seconds"),
              f"{ref}.requirements.model")
    if any(not isinstance(model[f], str) or not model[f] for f in ("model_id", "weight_id")):
        raise ContractError("invalid_model", f"{ref} needs model and weight identities", ref=ref)
    if any(not isinstance(model[f], int) or model[f] < 0 for f in ("size_bytes", "load_seconds")):
        raise ContractError("invalid_model", f"{ref} model sizes/times must be >= 0", ref=ref)
    return row


def validate_intake(row: dict, ref: str) -> dict:
    _required(row, ("schema_version", "kind", "event_id", "author", "ts", "blocker_id",
                    "checkpoint_event_id", "prior_event_id", "state", "reason_code"), ref)
    if row["schema_version"] != INTAKE_SCHEMA or row["kind"] != "intake-disposition":
        raise ContractError("wrong_schema", f"{ref} is not an intake disposition", ref=ref)
    if row["author"] != "inference":
        raise ContractError("unauthorized_author", f"only inference may author {ref}", ref=ref)
    for field in ("event_id", "blocker_id", "checkpoint_event_id", "prior_event_id"):
        if not isinstance(row[field], str) or not row[field]:
            raise ContractError("invalid_field", f"{ref}.{field} must be non-empty", ref=ref)
    parse_time(row["ts"], f"{ref}.ts")
    if row["state"] not in TRANSITIONS or row["state"] == "submitted":
        raise ContractError("unknown_state", f"{ref} has unknown state {row['state']!r}", ref=ref)
    if not isinstance(row["reason_code"], str) or not row["reason_code"]:
        raise ContractError("missing_reason", f"{ref} needs a typed reason_code", ref=ref)
    if row["state"] == "admitted":
        _nonempty_strings(row.get("evidence_refs"), f"{ref}.evidence_refs")
    if row["state"] == "duplicate" and not row.get("duplicate_of"):
        raise ContractError("missing_duplicate_target", f"{ref} needs duplicate_of", ref=ref)
    if row["state"] == "planned" and not row.get("window_id"):
        raise ContractError("missing_window", f"{ref} needs window_id", ref=ref)
    if row["state"] == "granted":
        if not row.get("lease_id") or not row.get("lease_path"):
            raise ContractError("missing_lease", f"{ref} grant lacks lease_id/lease_path", ref=ref)
    if row["state"] == "running":
        if not row.get("lease_id") or not row.get("lease_path"):
            raise ContractError("missing_lease", f"{ref} running state lacks a lease", ref=ref)
        _nonempty_strings(row.get("physical_claim_refs"), f"{ref}.physical_claim_evidence_refs")
    if row["state"] == "terminal" and not row.get("outcome"):
        raise ContractError("missing_outcome", f"{ref} terminal state lacks outcome", ref=ref)
    return row


def validate_window(row: dict, ref: str) -> dict:
    _required(row, ("schema_version", "kind", "event_id", "window_id", "author", "ts", "grade",
                    "eligible_devices", "eligible_model_ids", "cpu_bandwidth_class",
                    "gpu_vram_available_bytes", "max_model_bytes", "resident_model_id",
                    "resident_weight_id", "load_allowed", "starts_at", "expires_at",
                    "time_budget_seconds", "safe_drain_at", "observation_refs",
                    "vram_observation_refs"), ref)
    if row["schema_version"] != WINDOW_SCHEMA or row["kind"] != "compute-window":
        raise ContractError("wrong_schema", f"{ref} is not a compute window", ref=ref)
    if row["author"] != "inference":
        raise ContractError("unauthorized_author", f"only inference may author {ref}", ref=ref)
    if row["grade"] not in GRADES:
        raise ContractError("unknown_grade", f"{ref} has unknown grade {row['grade']!r}", ref=ref)
    for field in ("event_id", "window_id", "cpu_bandwidth_class", "safe_drain_at"):
        if not isinstance(row[field], str) or not row[field]:
            raise ContractError("invalid_field", f"{ref}.{field} must be non-empty", ref=ref)
    parse_time(row["ts"], f"{ref}.ts")
    starts_at = parse_time(row["starts_at"], f"{ref}.starts_at")
    expires_at = parse_time(row["expires_at"], f"{ref}.expires_at")
    if expires_at <= starts_at:
        raise ContractError("invalid_expiry", f"{ref}.expires_at must be after starts_at", ref=ref)
    _nonempty_strings(row["eligible_devices"], f"{ref}.eligible_devices")
    _nonempty_strings(row["eligible_model_ids"], f"{ref}.eligible_model_ids")
    _nonempty_strings(row["observation_refs"], f"{ref}.observation_evidence_refs")
    _nonempty_strings(row["vram_observation_refs"], f"{ref}.vram_evidence_refs")
    for field in ("gpu_vram_available_bytes", "max_model_bytes", "time_budget_seconds"):
        if not isinstance(row[field], int) or row[field] < 0:
            raise ContractError("invalid_resource", f"{ref}.{field} must be >= 0", ref=ref)
    if row["time_budget_seconds"] == 0 or not isinstance(row["load_allowed"], bool):
        raise ContractError("invalid_window", f"{ref} needs positive time and boolean load_allowed", ref=ref)
    for field in ("resident_model_id", "resident_weight_id"):
        if row[field] is not None and (not isinstance(row[field], str) or not row[field]):
            raise ContractError("invalid_model", f"{ref}.{field} must be null or identity", ref=ref)
    if (row["resident_model_id"] is None) != (row["resident_weight_id"] is None):
        raise ContractError("invalid_residency", f"{ref} resident model and weight move together", ref=ref)
    return row


def fold_candidates(checkpoints: list[dict], intake: list[dict]) -> dict[str, dict]:
    folded: dict[str, dict] = {}
    event_ids: set[str] = set()
    for idx, raw in enumerate(checkpoints, 1):
        row = validate_checkpoint(raw, f"checkpoint[{idx}]")
        if row["event_id"] in event_ids:
            raise ContractError("duplicate_event", f"duplicate event_id {row['event_id']}")
        event_ids.add(row["event_id"])
        blocker = row["blocker_id"]
        if blocker in folded:
            raise ContractError("duplicate_submission", f"multiple submissions for {blocker}")
        folded[blocker] = {
            "source": row, "state": "submitted", "last_event_id": row["event_id"],
            "last_ts": row["ts"], "accepted_at": None,
            "history": [{"event_id": row["event_id"], "state": "submitted", "ts": row["ts"]}],
        }
    for idx, raw in enumerate(intake, 1):
        row = validate_intake(raw, f"intake[{idx}]")
        if row["event_id"] in event_ids:
            raise ContractError("duplicate_event", f"duplicate event_id {row['event_id']}")
        event_ids.add(row["event_id"])
        current = folded.get(row["blocker_id"])
        if current is None:
            raise ContractError("orphan_disposition", f"intake event for unknown {row['blocker_id']}")
        if row["checkpoint_event_id"] != current["source"]["event_id"]:
            raise ContractError("checkpoint_mismatch",
                                f"{row['event_id']} does not name its source checkpoint")
        if row["prior_event_id"] != current["last_event_id"]:
            raise ContractError("broken_event_chain",
                                f"{row['event_id']} prior_event_id does not name the current event")
        if parse_time(row["ts"], f"intake[{idx}].ts") < parse_time(current["last_ts"], "prior.ts"):
            raise ContractError("nonmonotonic_time", f"{row['event_id']} predates its prior event")
        if row["state"] not in TRANSITIONS[current["state"]]:
            raise ContractError("invalid_transition",
                                f"{current['state']} -> {row['state']} is not permitted",
                                ref=row["event_id"])
        current["state"] = row["state"]
        current["last_event_id"] = row["event_id"]
        current["last_ts"] = row["ts"]
        if row["state"] == "admitted":
            current["accepted_at"] = row["ts"]
        current["history"].append({"event_id": row["event_id"], "state": row["state"],
                                   "ts": row["ts"], "reason_code": row["reason_code"]})
    return folded


def validate_graph(graph: dict, expected_hash: str, actual_hash: str) -> dict:
    if (len(expected_hash) != 64
            or any(char not in "0123456789abcdef" for char in expected_hash.lower())):
        raise ContractError("invalid_graph_hash", "pinned graph hash is not SHA-256")
    if actual_hash != expected_hash:
        raise ContractError("graph_hash_mismatch",
                            f"pinned graph {expected_hash} != actual {actual_hash}")
    if graph.get("schema") != "index_graph.v1":
        raise ContractError("wrong_graph_schema", "graph must be index_graph.v1")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ContractError("invalid_graph", "graph nodes/edges must be arrays")
    by_id: dict[str, dict] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise ContractError("invalid_graph_node", "graph node lacks id")
        if node["id"] in by_id:
            raise ContractError("duplicate_graph_node", f"duplicate graph node {node['id']}")
        by_id[node["id"]] = node
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("from") not in by_id or edge.get("to") not in by_id:
            raise ContractError("unresolved_graph_edge", f"graph edge does not resolve: {edge}")
    return by_id


def leverage(graph: dict, by_id: dict[str, dict], node_id: str) -> dict:
    if node_id not in by_id:
        raise ContractError("graph_node_missing", f"candidate graph node {node_id!r} is absent")
    live = {node_id for node_id, node in by_id.items()
            if node.get("state") == "active" and int(node.get("open", 0)) > 0}
    deps: dict[str, set[str]] = {node_id: set() for node_id in by_id}
    for edge in graph["edges"]:
        if edge.get("kind") == "dep":
            deps[edge["from"]].add(edge["to"])
    resolved = {node_id}
    unlocked: list[list[str]] = []
    while True:
        wave: list[str] = []
        for candidate in sorted(live - resolved):
            candidate_deps = deps[candidate]
            if not candidate_deps or not (candidate_deps & resolved):
                continue
            remaining_live = {dep for dep in candidate_deps if dep in live and dep not in resolved}
            if not remaining_live:
                wave.append(candidate)
        if not wave:
            break
        unlocked.append(wave)
        resolved.update(wave)
    direct = unlocked[0] if unlocked else []
    transitive = [item for wave in unlocked[1:] for item in wave]
    all_unlocked = direct + transitive
    return {
        "graph_node_id": node_id,
        "fire_ready_task_count": sum(int(by_id[item].get("open", 0)) for item in all_unlocked),
        "direct_handoffs_unlocked": direct,
        "transitive_open_dependants": transitive,
    }


def reason(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def compatibility(candidate: dict, window: dict, as_of: datetime) -> list[dict]:
    source = candidate["source"]
    req = source["requirements"]
    model = req["model"]
    reasons: list[dict] = []
    if candidate["state"] == "submitted":
        reasons.append(reason("missing_admission", "Inference has not admitted this blocker"))
    elif candidate["state"] != "ready":
        reasons.append(reason("not_ready", f"lifecycle state is {candidate['state']}"))
    if parse_time(source["expires_at"], "candidate.expires_at") <= as_of:
        reasons.append(reason("candidate_expired", "candidate expiry is not after as_of"))
    starts = parse_time(window["starts_at"], "window.starts_at")
    expires = parse_time(window["expires_at"], "window.expires_at")
    if as_of < starts:
        reasons.append(reason("window_not_started", "window starts after as_of"))
    if as_of >= expires:
        reasons.append(reason("window_expired", "window is expired at as_of"))
    if window["grade"] not in req["compatible_window_grades"]:
        reasons.append(reason("grade_mismatch", "window grade is not explicitly compatible"))
    missing_devices = sorted(set(req["required_devices"]) - set(window["eligible_devices"]))
    if missing_devices:
        reasons.append(reason("device_mismatch", f"unavailable devices: {missing_devices}"))
    if req["cpu_bandwidth_class"] != window["cpu_bandwidth_class"]:
        reasons.append(reason("bandwidth_mismatch", "CPU bandwidth labels differ"))
    if req["gpu_vram_bytes"] > window["gpu_vram_available_bytes"]:
        reasons.append(reason("insufficient_vram", "candidate VRAM exceeds observed availability"))
    if model["model_id"] not in window["eligible_model_ids"]:
        reasons.append(reason("model_ineligible", "model identity is not eligible"))
    if model["size_bytes"] > window["max_model_bytes"]:
        reasons.append(reason("model_too_large", "model size exceeds window cap"))
    resident = window["resident_weight_id"]
    if resident != model["weight_id"] and not window["load_allowed"]:
        reasons.append(reason("wrong_weight", "different weight is resident and loads are forbidden"))
    load_cost = 0 if resident == model["weight_id"] else model["load_seconds"]
    if req["duration_seconds"] + load_cost > window["time_budget_seconds"]:
        reasons.append(reason("duration_exceeds_window", "load plus execution exceeds time budget"))
    if source["operator_gates"]:
        reasons.append(reason("operator_gate_unresolved", "candidate has unresolved operator gates"))
    return sorted(reasons, key=lambda item: item["code"])


def rank_key(item: dict) -> tuple:
    source = item["source"]
    lev = item["leverage"]
    accepted = item["accepted_at"] or source["ts"]
    return (
        0 if source["must_run"] else 1,
        -lev["fire_ready_task_count"],
        -len(lev["direct_handoffs_unlocked"]),
        -len(lev["transitive_open_dependants"]),
        PRIORITY_ORDER[source["priority_class"]],
        item["rank_evidence"]["exact_window_slack_seconds"],
        parse_time(accepted, "accepted_at").timestamp(),
        source["blocker_id"],
    )


def make_plan(candidates: list[dict], window: dict) -> dict:
    eligible = sorted((item for item in candidates if not item["incompatibility_reasons"]),
                      key=rank_key)
    if window["grade"] == "load-then-keep-hot" and eligible:
        chosen_weight = window["resident_weight_id"] or eligible[0]["source"]["requirements"]["model"]["weight_id"]
        for item in eligible:
            if item["source"]["requirements"]["model"]["weight_id"] != chosen_weight:
                item["incompatibility_reasons"].append(
                    reason("wrong_weight", f"keep-hot batch selected weight {chosen_weight}"))
        eligible = [item for item in eligible if not item["incompatibility_reasons"]]

    selected: list[dict] = []
    elapsed = 0
    resident = window["resident_weight_id"]
    for item in eligible:
        req = item["source"]["requirements"]
        model = req["model"]
        load = 0 if resident == model["weight_id"] else model["load_seconds"]
        cost = load + req["duration_seconds"]
        if elapsed + cost > window["time_budget_seconds"]:
            item["incompatibility_reasons"].append(
                reason("batch_time_exhausted", "higher-ranked selections consumed the window"))
            continue
        selected.append({
            "blocker_id": item["source"]["blocker_id"],
            "task_id": item["source"]["task_id"],
            "weight_id": model["weight_id"],
            "rank_evidence": item["rank_evidence"],
            "load_seconds": load,
            "duration_seconds": req["duration_seconds"],
        })
        elapsed += cost
        resident = model["weight_id"]
    excluded = [{"blocker_id": item["source"]["blocker_id"],
                 "reasons": sorted(item["incompatibility_reasons"], key=lambda value: value["code"])}
                for item in sorted(candidates, key=lambda value: value["source"]["blocker_id"])
                if item["incompatibility_reasons"]]
    plan = {
        "window_id": window["window_id"],
        "window_event_id": window["event_id"],
        "grade": window["grade"],
        "selected": selected,
        "excluded": excluded,
        "estimated_total_seconds": elapsed,
        "weight_groups": sorted({row["weight_id"] for row in selected}),
    }
    plan["plan_sha256"] = object_hash(plan)
    return plan


def build_projection(checkpoint_path: Path, intake_path: Path, window_path: Path,
                     graph_path: Path, graph_sha256: str, as_of_text: str,
                     window_id: str | None = None) -> dict:
    as_of = parse_time(as_of_text, "as_of")
    checkpoints = read_records(checkpoint_path)
    intake = read_records(intake_path)
    windows = read_records(window_path)
    folded = fold_candidates(checkpoints, intake)
    validated_windows = [validate_window(row, f"window[{idx}]")
                         for idx, row in enumerate(windows, 1)]
    seen_windows: set[str] = set()
    for row in validated_windows:
        if row["window_id"] in seen_windows:
            raise ContractError("duplicate_window", f"duplicate window_id {row['window_id']}")
        seen_windows.add(row["window_id"])
    if window_id is not None:
        matches = [row for row in validated_windows if row["window_id"] == window_id]
    else:
        matches = validated_windows
    if len(matches) != 1:
        raise ContractError("window_selection", f"expected one selected window, found {len(matches)}")
    window = matches[0]

    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("graph_unreadable", f"cannot read graph: {exc}", ref=str(graph_path)) from exc
    actual_graph_hash = file_hash(graph_path)
    by_id = validate_graph(graph, graph_sha256, actual_graph_hash)

    candidate_rows: list[dict] = []
    for blocker_id in sorted(folded):
        item = folded[blocker_id]
        lev = leverage(graph, by_id, item["source"]["graph_node_id"])
        incompat = compatibility(item, window, as_of)
        evidence = {
            "must_run": item["source"]["must_run"],
            "fire_ready_task_count": lev["fire_ready_task_count"],
            "direct_handoffs_unlocked": len(lev["direct_handoffs_unlocked"]),
            "transitive_open_dependants": len(lev["transitive_open_dependants"]),
            "priority_class": item["source"]["priority_class"],
            "exact_window_slack_seconds": (
                window["time_budget_seconds"]
                - item["source"]["requirements"]["duration_seconds"]
                - (0 if window["resident_weight_id"] ==
                   item["source"]["requirements"]["model"]["weight_id"]
                   else item["source"]["requirements"]["model"]["load_seconds"])
            ),
            "accepted_at": item["accepted_at"],
            "blocker_id": blocker_id,
            "graph_sha256": actual_graph_hash,
        }
        candidate_rows.append({**item, "leverage": lev, "rank_evidence": evidence,
                               "incompatibility_reasons": incompat})
    plan = make_plan(candidate_rows, window)
    projection_candidates = []
    for item in sorted(candidate_rows, key=lambda value: value["source"]["blocker_id"]):
        source = item["source"]
        projection_candidates.append({
            "blocker_id": source["blocker_id"], "task_id": source["task_id"],
            "task_text": source["task_text"], "spec_ref": source["spec_ref"],
            "checkpoint_ref": source["checkpoint_ref"],
            "checkpoint_sha256": source["checkpoint_sha256"],
            "state": item["state"], "last_event_id": item["last_event_id"],
            "accepted_at": item["accepted_at"], "history": item["history"],
            "requirements": source["requirements"], "expires_at": source["expires_at"],
            "leverage": item["leverage"], "rank_evidence": item["rank_evidence"],
            "incompatibility_reasons": item["incompatibility_reasons"],
        })
    result = {
        "schema_version": SCHEMA,
        "as_of": as_of_text,
        "inputs": {
            "checkpoints": {"sha256": file_hash(checkpoint_path)},
            "intake": {"sha256": file_hash(intake_path)},
            "windows": {"sha256": file_hash(window_path)},
            "graph": {"sha256": actual_graph_hash, "schema": graph["schema"]},
        },
        "window": window,
        "candidates": projection_candidates,
        "plan": plan,
    }
    result["projection_sha256"] = object_hash(result)
    return result


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(canonical_bytes(value))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__)
    sub = top.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--checkpoints", type=Path, required=True)
        cmd.add_argument("--intake", type=Path, required=True)
        cmd.add_argument("--windows", type=Path, required=True)
        cmd.add_argument("--graph", type=Path, required=True)
        cmd.add_argument("--graph-sha256", required=True)
        cmd.add_argument("--as-of", required=True, help="explicit RFC3339 replay timestamp")
        cmd.add_argument("--window-id")
        if name == "build":
            cmd.add_argument("--output", type=Path)
        else:
            cmd.add_argument("--projection", type=Path, required=True)
    return top


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        value = build_projection(args.checkpoints, args.intake, args.windows, args.graph,
                                 args.graph_sha256, args.as_of, args.window_id)
        if args.command == "build":
            if args.output:
                write_atomic(args.output, value)
            else:
                sys.stdout.buffer.write(canonical_bytes(value))
            return 0
        try:
            existing = json.loads(args.projection.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("projection_unreadable", f"cannot read projection: {exc}") from exc
        claimed = existing.get("projection_sha256") if isinstance(existing, dict) else None
        unsigned = dict(existing) if isinstance(existing, dict) else {}
        unsigned.pop("projection_sha256", None)
        if claimed != object_hash(unsigned):
            raise ContractError("projection_hash_invalid", "stored projection self-hash is invalid")
        if canonical_bytes(existing) != canonical_bytes(value):
            raise ContractError("projection_mismatch", "projection differs from deterministic replay")
        print(f"OK {value['projection_sha256']}")
        return 0
    except ContractError as exc:
        print(json.dumps({"error": exc.as_dict()}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

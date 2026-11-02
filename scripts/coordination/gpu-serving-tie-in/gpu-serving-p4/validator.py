"""Isolated P4-1 candidate validation prototype; never imported by AutoPilot.

The caller is responsible for authenticating the snapshot and supplying the
expected fingerprint from an independent trusted source. This module does not
load policy, inspect artifacts, apply parameters, or establish runtime truth.
"""
from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    ceiling: int | None = None


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate(candidate: Any, snapshot: Any = None, *, enabled: bool = False,
             expected_fingerprint: str | None = None) -> Decision:
    """Validate an exact candidate against an independently verified snapshot.

    Frontier rows are exact tenant, mode and budget-profile matches; within
    those rows the smallest context bucket covering the request is selected.
    Invalid, duplicate or null rows refuse rather than authorize a fallback.
    """
    def reject(reason: str) -> Decision:
        return Decision(False, reason)

    if enabled is not True:
        return reject("disabled")
    keys = {"tenant_id", "mode", "budget_profile", "context_tokens", "np_ceiling"}
    if not isinstance(candidate, dict) or set(candidate) != keys:
        return reject("candidate_schema")
    if any(not isinstance(candidate[k], str) or not candidate[k].strip()
           for k in ("tenant_id", "mode", "budget_profile")):
        return reject("candidate_schema")
    if not all(_positive_int(candidate[k]) for k in ("context_tokens", "np_ceiling")):
        return reject("candidate_schema")
    if not isinstance(snapshot, dict) or set(snapshot) != {"fingerprint", "tenants", "frontiers"}:
        return reject("snapshot_schema")
    if not _sha256(expected_fingerprint) or snapshot["fingerprint"] != expected_fingerprint:
        return reject("snapshot_identity")
    tenants, frontiers = snapshot["tenants"], snapshot["frontiers"]
    if not isinstance(tenants, dict) or not isinstance(frontiers, list):
        return reject("snapshot_schema")
    tenant = tenants.get(candidate["tenant_id"])
    if not isinstance(tenant, dict) or set(tenant) != {"available", "path", "bytes", "sha256", "modes"}:
        return reject("tenant_missing")
    if tenant["available"] is not True:
        return reject("tenant_unavailable")
    if (not isinstance(tenant["path"], str) or not tenant["path"].startswith("/")
            or not _positive_int(tenant["bytes"]) or not _sha256(tenant["sha256"])
            or not isinstance(tenant["modes"], list)
            or not all(isinstance(m, str) and m for m in tenant["modes"])):
        return reject("tenant_identity")
    if candidate["mode"] not in tenant["modes"]:
        return reject("mode_unavailable")

    buckets: dict[int, int | None] = {}
    for row in frontiers:
        if not isinstance(row, dict) or set(row) != {"tenant_id", "mode", "budget_profile", "context_tokens", "np_ceiling"}:
            return reject("frontier_schema")
        if (not all(isinstance(row[k], str) and row[k] for k in ("tenant_id", "mode", "budget_profile"))
                or not _positive_int(row["context_tokens"])
                or (row["np_ceiling"] is not None and not _positive_int(row["np_ceiling"]))):
            return reject("frontier_schema")
        if any(row[k] != candidate[k] for k in ("tenant_id", "mode", "budget_profile")):
            continue
        context = row["context_tokens"]
        if context in buckets:
            return reject("frontier_duplicate")
        buckets[context] = row["np_ceiling"]
    eligible = [context for context in buckets if context >= candidate["context_tokens"]]
    if not eligible:
        return reject("frontier_missing")
    ceiling = buckets[min(eligible)]
    if ceiling is None:
        return reject("frontier_unknown")
    if candidate["np_ceiling"] > ceiling:
        return reject("ceiling_exceeded")
    return Decision(True, "accepted", ceiling)

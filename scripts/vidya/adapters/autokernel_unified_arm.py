"""Strict projection of prospective unified AutoKernel per-arm captures.

The adapter repeats the producer's structural checks without importing the research tree.
It emits no row for diagnostic/pre-hook material and never grades; ``claim_tuple.grade`` is
the sole measurement ladder.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_unified_arm/v1"
CAPTURE_SCHEMA = "epyc.autokernel.unified_arm_capture.v1"
CAPTURE_SCHEMA_V2 = "epyc.autokernel.unified_arm_capture.v2"
JOURNAL_SCHEMA = "epyc.autokernel.journal_entry.v1"
JOURNAL_KIND = "PLANNED_SERVING_ARM_CAPTURED"
PRODUCER_ID = "epyc.autokernel.measurement_capture/v1"
PRODUCER_ID_V2 = "epyc.autokernel.measurement_capture/v2"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024

_PLAN_FIELDS = {"schema", "plan_id", "campaign_id", "target_revision", "epoch",
                "instrument_class", "category", "phase", "protocol_ref",
                "protocol_status", "record_class", "intended_use", "comparison_kind",
                "estimand", "metric", "metric_direction", "estimator_id", "unit",
                "changed_factors", "anchor_identity", "candidate_identity",
                "expected_units", "stopping", "required_witnesses", "calibration_ref",
                "policy_snapshot", "continuation_allowed"}
_PLAN_FIELDS_V2 = _PLAN_FIELDS | {"loaded_instrument"}
_UNIT_FIELDS = {"unit_id", "arm", "process_id", "expected_prompt_ids", "order_index",
                "pair_id"}
_RAW_FIELDS = {"schema", "plan_digest", "unit_id", "arm", "process_id", "prompt_ids",
               "terminal", "value", "witnesses", "recorded_screen", "reason",
               "artifact_digest", "observed_order_index"}
_VIEW_FIELDS = {"schema", "plan_digest", "selected_rows", "rejection_reasons",
                "missing_expected_units", "independent_n", "complete", "view_digest"}
_NATIVE_FIELDS = {"schema", "kind", "plan_digest", "unit_id", "arm",
                  "process_generation_id", "lineage_id", "fence_id", "grant_id",
                  "container_id", "worker_identity", "observed_started_at",
                  "observed_ended_at", "prompt_manifest_digest", "comparison_identities",
                  "observations", "selected_observation", "value", "error",
                  "artifact_digest"}
_ATTEMPT_FIELDS = {"schema", "kind", "plan_digest", "unit_id", "arm",
                   "process_generation_id", "lineage_id", "fence_id", "grant_id",
                   "container_id", "worker_identity", "observed_started_at",
                   "observed_ended_at", "prompt_manifest_digest", "prompt_ids",
                   "comparison_identities", "native_observation_digest",
                   "stage_witnesses", "terminal", "value", "provider_recorded_screen",
                   "recorded_screen", "reason", "artifact_digest"}
_NATIVE_FIELDS_V2 = _NATIVE_FIELDS | {"lifecycle_observation"}
_ATTEMPT_FIELDS_V2 = _ATTEMPT_FIELDS | {"lifecycle_observation_content_sha256"}
_INSTRUMENT_FIELDS = {"schema", "identity_sha256", "configuration_complete", "artifact",
                      "reference_digest"}
_REFERENCE_FIELDS = {"schema", "observation_id", "unit_id", "process_generation_id",
                     "fence_id", "active_claim_ref", "target_pid", "target_start_ticks",
                     "descendant_binding_ref", "worker_id", "worker_generation", "grant_id",
                     "grant_generation", "container_id", "instrument_identity_sha256",
                     "observation_content_sha256", "shutdown_status", "successor_permitted",
                     "artifact", "reference_digest"}
_LOADED_IDENTITY_FIELDS = {"schema", "scope", "identity_basis", "measurement_callable",
                           "clock_callable", "supporting_callables", "used_constants",
                           "dependency_versions", "configuration_complete", "sha256"}
_CALLABLE_FIELDS = {"module", "qualname", "kind", "implementation_status",
                    "implementation_sha256", "configuration_status",
                    "configuration_sha256"}
_OBSERVATION_FIELDS = {"schema", "detector_version", "observation_id", "backend",
                       "instrument_identity_digest", "recipe_identity_digest", "clock_domain",
                       "cadence_s", "gap_limit_s", "started_monotonic_s", "ended_monotonic_s",
                       "started_at", "ended_at", "boot_id", "worker_binding", "held_claim",
                       "requested_effective_state", "budgets", "topology", "target_binding",
                       "phase_boundaries", "load_window", "samples", "intervals",
                       "observer_cost", "shutdown", "completeness", "issues", "residency",
                       "verdict", "content_sha256"}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, UnicodeError, RecursionError) as exc:
        raise ProjectionError("native data is not finite canonical JSON") from exc


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) \
        and math.isfinite(float(value))


def _exact(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ProjectionError(f"{label} has missing or unknown fields")
    return value


def _text(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{label} must be non-empty text")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProjectionError(f"{label} must be an integer >= {minimum}")
    return value


def _strings(value: Any, label: str, *, empty: bool = False,
             unique: bool = True) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        raise ProjectionError(f"{label} must be an array of text")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ProjectionError(f"{label} must contain non-empty text")
    if unique and len(set(value)) != len(value):
        raise ProjectionError(f"{label} contains duplicates")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    value = _text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ProjectionError(f"{label} is timezone-naive")
    return parsed


def _carrier(source: Any) -> tuple[dict, dict | None]:
    if not isinstance(source, dict):
        raise ProjectionError("unified arm source must be an object")
    if source.get("schema") in {CAPTURE_SCHEMA, CAPTURE_SCHEMA_V2}:
        return source, None
    if source.get("journal_schema") == JOURNAL_SCHEMA:
        payload = source.get("payload")
        if (source.get("kind") != JOURNAL_KIND or not isinstance(payload, dict)
                or payload.get("schema") not in {CAPTURE_SCHEMA, CAPTURE_SCHEMA_V2}
                or payload.get("measurement_id") != source.get("record_id")
                or not isinstance(payload.get("carrier"), dict)
                or payload["carrier"].get("measurement_id") != payload["measurement_id"]
                or payload["carrier"].get("schema") != payload.get("schema")):
            raise ProjectionError("malformed unified arm journal envelope")
        return payload["carrier"], payload
    raise ProjectionError("unsupported unified arm source schema")


def _artifact_bytes(root: Path, locator: Any, digest: Any) -> dict:
    if not isinstance(locator, str) or not locator or not _SHA.match(str(digest or "")):
        raise ProjectionError("capture artifact locator/digest is malformed")
    relative = PurePosixPath(locator)
    if relative.is_absolute() or ".." in relative.parts:
        raise ProjectionError("capture artifact locator escapes the corpus root")
    root = root.absolute()
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                          | getattr(os, "O_NOFOLLOW", 0))
        descriptors.append(current)
        for component in relative.parts[:-1]:
            current = os.open(component, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                              | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
            descriptors.append(current)
        descriptor = os.open(relative.parts[-1], os.O_RDONLY | os.O_NONBLOCK
                             | getattr(os, "O_NOFOLLOW", 0),
                             dir_fd=current)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > _MAX_ARTIFACT_BYTES):
            raise ProjectionError("capture artifact must be a bounded single-link regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ProjectionError("capture artifact ended before its pinned size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise ProjectionError("capture artifact grew while being verified")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        named = os.stat(relative.parts[-1], dir_fd=current, follow_symlinks=False)
        def identity(item: os.stat_result) -> tuple[int, ...]:
            return (item.st_dev, item.st_ino, item.st_mode, item.st_uid,
                    item.st_nlink, item.st_size, item.st_mtime_ns)
        if identity(before) != identity(after) or identity(after) != identity(named):
            raise ProjectionError("capture artifact changed while being verified")
    except OSError as exc:
        raise ProjectionError("capture artifact is missing or escapes the corpus root") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ProjectionError("capture artifact byte digest mismatch")
    try:
        value = json.loads(raw, parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant {token}")))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError,
            OverflowError, RecursionError) as exc:
        raise ProjectionError("capture artifact is not JSON") from exc
    if not isinstance(value, dict):
        raise ProjectionError("capture artifact must contain an object")
    return value


def _artifact_ref(value: Any, label: str) -> dict:
    row = _exact(value, {"locator", "sha256", "verified"}, label)
    _text(row["locator"], f"{label}.locator")
    if not isinstance(row["sha256"], str) or not _SHA.fullmatch(row["sha256"]):
        raise ProjectionError(f"{label}.sha256 must be lowercase SHA-256")
    if row["verified"] is not True:
        raise ProjectionError(f"{label} must be producer-verified")
    return row


def _validate_instrument_reference(value: Any, corpus_root: Path | None) -> dict:
    row = _exact(value, _INSTRUMENT_FIELDS, "loaded instrument reference")
    if row["schema"] != "epyc.autokernel.loaded_serving_instrument_reference.v1" \
            or not isinstance(row["configuration_complete"], bool):
        raise ProjectionError("loaded instrument reference schema/state is invalid")
    if not isinstance(row["identity_sha256"], str) \
            or not _SHA.fullmatch(row["identity_sha256"]):
        raise ProjectionError("loaded instrument identity must be lowercase SHA-256")
    artifact = _artifact_ref(row["artifact"], "loaded instrument artifact")
    body = dict(row)
    digest = body.pop("reference_digest")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest) or _hash(body) != digest:
        raise ProjectionError("loaded instrument reference digest mismatch")
    if corpus_root is not None:
        identity = _artifact_bytes(corpus_root, artifact["locator"], artifact["sha256"])
        _exact(identity, _LOADED_IDENTITY_FIELDS, "loaded instrument identity")
        if identity.get("schema") != "epyc.autokernel.loaded_serving_instrument.v1":
            raise ProjectionError("loaded instrument identity schema is unsupported")
        callables = [identity.get("measurement_callable"), identity.get("clock_callable")]
        supporting = identity.get("supporting_callables")
        if not isinstance(supporting, list):
            raise ProjectionError("loaded instrument supporting callables are malformed")
        callables.extend(supporting)
        for callable_identity in callables:
            _exact(callable_identity, _CALLABLE_FIELDS, "loaded callable identity")
            if (callable_identity["kind"] not in {"python", "builtin_or_extension"}
                    or callable_identity["implementation_status"] not in {"pinned", "unproven"}
                    or callable_identity["configuration_status"] not in {"pinned", "unproven"}):
                raise ProjectionError("loaded callable identity state is unsupported")
        if not isinstance(identity.get("dependency_versions"), dict) \
                or not identity["dependency_versions"]:
            raise ProjectionError("loaded instrument dependency versions are missing")
        identity_body = dict(identity)
        identity_digest = identity_body.pop("sha256", None)
        if (identity_digest != row["identity_sha256"]
                or _hash(identity_body) != identity_digest
                or identity.get("configuration_complete") is not row["configuration_complete"]):
            raise ProjectionError("loaded instrument artifact identity mismatch")
    return row


def _validate_lifecycle_reference(value: Any, corpus_root: Path | None) -> dict:
    row = _exact(value, _REFERENCE_FIELDS, "lifecycle observation reference")
    if row["schema"] != "epyc.autokernel.lifecycle_observation_reference.v1":
        raise ProjectionError("lifecycle observation reference schema is unsupported")
    for key in ("observation_id", "unit_id", "process_generation_id", "fence_id",
                "active_claim_ref", "descendant_binding_ref", "worker_id", "grant_id",
                "container_id"):
        _text(row[key], f"lifecycle observation reference.{key}")
    for key in ("target_pid", "target_start_ticks", "worker_generation", "grant_generation"):
        _integer(row[key], f"lifecycle observation reference.{key}", minimum=1)
    for key in ("instrument_identity_sha256", "observation_content_sha256"):
        if not isinstance(row[key], str) or not _SHA.fullmatch(row[key]):
            raise ProjectionError(f"lifecycle observation reference.{key} is malformed")
    if (row["shutdown_status"] not in {"resolved", "unresolved"}
            or row["successor_permitted"] is not (row["shutdown_status"] == "resolved")):
        raise ProjectionError("lifecycle observation shutdown fence is inconsistent")
    artifact = _artifact_ref(row["artifact"], "lifecycle observation artifact")
    body = dict(row)
    digest = body.pop("reference_digest")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest) or _hash(body) != digest:
        raise ProjectionError("lifecycle observation reference digest mismatch")
    if corpus_root is not None:
        observation = _artifact_bytes(corpus_root, artifact["locator"], artifact["sha256"])
        _exact(observation, _OBSERVATION_FIELDS, "lifecycle observation")
        if (observation.get("schema") != "epyc.autokernel.lifecycle_observation.v1"
                or observation.get("detector_version") != "autokernel-lifecycle-observer-2"
                or observation.get("instrument_identity_digest") !=
                row["instrument_identity_sha256"]):
            raise ProjectionError("lifecycle observation schema/instrument is unsupported")
        worker = _exact(observation.get("worker_binding"), {
            "worker_id", "worker_incarnation", "grant_id", "grant_generation",
            "container_identity"}, "lifecycle observation worker binding")
        container = _exact(worker.get("container_identity"), {
            "path", "dev", "ino", "uid", "nlink", "mode"},
            "lifecycle observation container identity")
        _text(container["path"], "lifecycle observation container identity.path")
        for key in ("dev", "uid"):
            _integer(container[key], f"lifecycle observation container identity.{key}",
                     minimum=0)
        for key in ("ino", "nlink", "mode"):
            _integer(container[key], f"lifecycle observation container identity.{key}",
                     minimum=1)
        target = _exact(observation.get("target_binding"), {
            "pid", "start_ticks", "boot_id", "worker_binding", "binding_ref"},
            "lifecycle observation target binding")
        shutdown = _exact(observation.get("shutdown"), {
            "status", "successor_permitted", "late_writes_accepted"},
            "lifecycle observation shutdown")
        if (worker.get("worker_id") != row["worker_id"]
                or worker.get("worker_incarnation") != row["worker_generation"]
                or worker.get("grant_id") != row["grant_id"]
                or worker.get("grant_generation") != row["grant_generation"]
                or target.get("worker_binding") != worker
                or target.get("boot_id") != observation.get("boot_id")
                or target.get("pid") != row["target_pid"]
                or target.get("start_ticks") != row["target_start_ticks"]
                or target.get("binding_ref") != row["descendant_binding_ref"]
                or shutdown.get("status") != row["shutdown_status"]
                or shutdown.get("successor_permitted") is not row["successor_permitted"]
                or shutdown.get("late_writes_accepted") is not False):
            raise ProjectionError("lifecycle observation artifact ownership mismatch")
        observation_body = dict(observation)
        content_digest = observation_body.pop("content_sha256", None)
        if (content_digest != row["observation_content_sha256"]
                or _hash(observation_body) != content_digest
                or observation.get("observation_id") != row["observation_id"]):
            raise ProjectionError("lifecycle observation artifact identity mismatch")
    return row


def _embedded_artifacts(carrier: dict, corpus_root: Path | None) -> list[dict]:
    raw_artifacts = carrier.get("raw_artifacts")
    if not isinstance(raw_artifacts, list):
        raise ProjectionError("unified arm carrier lacks native artifacts")
    artifacts: list[dict] = []
    for row in raw_artifacts:
        if not isinstance(row, dict) or not isinstance(row.get("document"), dict) \
                or not isinstance(row.get("stored"), dict):
            raise ProjectionError("unified arm raw artifact entry is malformed")
        document, stored = row["document"], row["stored"]
        item_body = dict(document)
        item_digest = item_body.pop("artifact_digest", None)
        if not _SHA.match(str(item_digest or "")) or _hash(item_body) != item_digest:
            raise ProjectionError("embedded planned-serving artifact digest mismatch")
        if corpus_root is not None:
            exact = _artifact_bytes(corpus_root, stored.get("locator"), stored.get("sha256"))
            if stored.get("verified") is not True or exact != document:
                raise ProjectionError("raw artifact exact bytes do not match embedded input")
        artifacts.append(document)
    return artifacts


def _validate_identity(value: Any, label: str, *, v2: bool = False,
                       instrument: dict | None = None) -> dict:
    fields = {"backend", "template_hash", "resolved_execution_digest",
              "resolved_snapshot_digest", "workload_digest", "model_digest",
              "drafter_digest", "executable_digest", "dso_set_digest"}
    if v2:
        fields |= {"schema", "instrument_identity_sha256",
                   "instrument_configuration_complete"}
    identity = _exact(value, fields, label)
    if identity["backend"] not in {"cpu", "gpu"}:
        raise ProjectionError(f"{label}.backend is unsupported")
    digest_fields = fields - {"backend", "drafter_digest", "schema",
                              "instrument_configuration_complete"}
    for key in digest_fields:
        if not isinstance(identity[key], str) or not _SHA.fullmatch(identity[key]):
            raise ProjectionError(f"{label}.{key} must be lowercase SHA-256")
    if identity["drafter_digest"] is not None and (
            not isinstance(identity["drafter_digest"], str)
            or not _SHA.fullmatch(identity["drafter_digest"])):
        raise ProjectionError(f"{label}.drafter_digest must be null or lowercase SHA-256")
    if v2 and (identity["schema"] != "epyc.autokernel.serving_arm_identity.v2"
               or not isinstance(identity["instrument_configuration_complete"], bool)
               or instrument is None
               or identity["instrument_identity_sha256"] != instrument["identity_sha256"]
               or identity["instrument_configuration_complete"] is not
               instrument["configuration_complete"]):
        raise ProjectionError(f"{label} does not bind the loaded instrument")
    return identity


def _validate_plan(value: Any, *, corpus_root: Path | None) \
        -> tuple[dict, dict[str, dict], str, dict | None]:
    v2 = isinstance(value, dict) and value.get("schema") == \
        "epyc.autokernel.experiment_plan.v2"
    plan = _exact(value, _PLAN_FIELDS_V2 if v2 else _PLAN_FIELDS, "unified arm plan")
    if plan["schema"] not in {"epyc.autokernel.experiment_plan.v1",
                              "epyc.autokernel.experiment_plan.v2"}:
        raise ProjectionError("unified arm plan schema is unsupported")
    instrument = _validate_instrument_reference(plan["loaded_instrument"], corpus_root) \
        if v2 else None
    enums = {
        "instrument_class": {"bench", "serving"},
        "category": {"OPTIMUM", "BASELINE", "CANDIDATE"},
        "phase": {"discovery", "confirmation", "observation", "release"},
        "protocol_status": {"ratified", "unratified", "unknown"},
        "record_class": {"discovery_screen", "strict_search", "observation",
                         "registered_claim"},
        "intended_use": {"explore", "nominate", "rank", "bank", "validate",
                         "validate_production", "certify", "certify_transfer",
                         "certify_overlap", "headline", "release"},
        "comparison_kind": {"mechanism", "assembled_candidate", "best_supported_recipe"},
        "estimand": {"level", "dispersion"}, "metric_direction": {"higher", "lower"},
        "unit": {"arm", "session", "process"},
    }
    for key in ("plan_id", "campaign_id", "target_revision", "epoch", "metric",
                "estimator_id"):
        _text(plan[key], f"plan.{key}")
    for key, choices in enums.items():
        if not isinstance(plan[key], str) or plan[key] not in choices:
            raise ProjectionError(f"plan.{key} is unsupported")
    _text(plan["protocol_ref"], "plan.protocol_ref", nullable=True)
    if plan["protocol_status"] == "ratified" and plan["protocol_ref"] is None:
        raise ProjectionError("ratified plan requires a protocol reference")
    _text(plan["calibration_ref"], "plan.calibration_ref", nullable=True)
    _strings(plan["changed_factors"], "plan.changed_factors", empty=True)
    required = _strings(plan["required_witnesses"], "plan.required_witnesses", empty=True)
    if not isinstance(plan["continuation_allowed"], bool):
        raise ProjectionError("plan.continuation_allowed must be boolean")
    policy = _exact(plan["policy_snapshot"], {"reference", "digest"}, "plan policy")
    _text(policy["reference"], "plan.policy_snapshot.reference")
    if not isinstance(policy["digest"], str) or not _SHA.fullmatch(policy["digest"]):
        raise ProjectionError("plan.policy_snapshot.digest must be lowercase SHA-256")
    _validate_identity(plan["anchor_identity"], "plan.anchor_identity",
                       v2=v2, instrument=instrument)
    _validate_identity(plan["candidate_identity"], "plan.candidate_identity",
                       v2=v2, instrument=instrument)

    units = plan["expected_units"]
    if not isinstance(units, list) or not units:
        raise ProjectionError("plan.expected_units must be non-empty")
    by_id: dict[str, dict] = {}
    processes: set[str] = set()
    indices: list[int] = []
    for raw in units:
        unit = _exact(raw, _UNIT_FIELDS, "plan unit")
        unit_id = _text(unit["unit_id"], "unit.unit_id")
        process_id = _text(unit["process_id"], "unit.process_id")
        if unit["arm"] not in {"anchor", "candidate"}:
            raise ProjectionError("unit.arm is unsupported")
        _strings(unit["expected_prompt_ids"], "unit.expected_prompt_ids")
        index = _integer(unit["order_index"], "unit.order_index")
        if unit["pair_id"] is not None:
            _integer(unit["pair_id"], "unit.pair_id")
        if unit_id in by_id:
            raise ProjectionError("plan has duplicate unit IDs")
        if plan["unit"] == "process" and process_id in processes:
            raise ProjectionError("process plan reuses a process ID")
        by_id[unit_id] = unit
        processes.add(process_id)
        indices.append(index)
    if sorted(indices) != list(range(len(units))) or len(set(indices)) != len(indices):
        raise ProjectionError("plan unit order must be unique and contiguous")

    stopping = _exact(plan["stopping"], {"kind", "n_per_arm", "paired"},
                      "plan stopping")
    n = _integer(stopping["n_per_arm"], "plan.stopping.n_per_arm", minimum=1)
    if stopping["kind"] != "fixed_n" or not isinstance(stopping["paired"], bool):
        raise ProjectionError("only boolean fixed_n stopping is supported")
    counts = {name: sum(unit["arm"] == name for unit in units)
              for name in ("anchor", "candidate")}
    if counts != {"anchor": n, "candidate": n}:
        raise ProjectionError("fixed_n plan has wrong per-arm unit counts")
    phase_for = {"discovery_screen": "discovery", "strict_search": "confirmation",
                 "observation": "observation", "registered_claim": "release"}
    if phase_for[plan["record_class"]] != plan["phase"]:
        raise ProjectionError("plan record class and phase conflict")
    if plan["phase"] == "confirmation" and stopping["paired"] is not True:
        raise ProjectionError("confirmation requires paired stopping")
    if plan["phase"] == "discovery" and (stopping["paired"] or any(
            unit["pair_id"] is not None for unit in units)):
        raise ProjectionError("discovery plan cannot be paired")
    if not stopping["paired"] and any(unit["pair_id"] is not None for unit in units):
        raise ProjectionError("unpaired plan contains pair IDs")
    if stopping["paired"]:
        pairs: dict[int, list[dict]] = {}
        for unit in units:
            if unit["pair_id"] is None:
                raise ProjectionError("paired plan unit lacks pair ID")
            pairs.setdefault(unit["pair_id"], []).append(unit)
        if sorted(pairs) != list(range(n)) or any(
                len(pair) != 2 or {item["arm"] for item in pair} != {"anchor", "candidate"}
                for pair in pairs.values()):
            raise ProjectionError("paired plan has malformed pair membership")
        if plan["phase"] == "confirmation":
            ordered = sorted(units, key=lambda item: item["order_index"])
            for slot in range(n):
                block = ordered[2 * slot:2 * slot + 2]
                if ({item["pair_id"] for item in block} != {slot}
                        or {item["arm"] for item in block} != {"anchor", "candidate"}):
                    raise ProjectionError("confirmation pairs are not adjacent")
    # Validate canonical JSON, including every opaque identity/policy leaf.
    digest = _hash(plan)
    del required
    return plan, by_id, digest, instrument


def _validate_prompts(value: Any) -> tuple[dict, dict[str, dict]]:
    manifest = _exact(value, {"schema", "version", "prompts", "digest"},
                      "prompt manifest")
    if manifest["schema"] != "epyc.autokernel.frozen_prompt_manifest.v1":
        raise ProjectionError("prompt manifest schema is unsupported")
    _text(manifest["version"], "prompt manifest version")
    prompts = manifest["prompts"]
    if not isinstance(prompts, list) or not prompts:
        raise ProjectionError("prompt manifest must be non-empty")
    by_id: dict[str, dict] = {}
    fields = {"prompt_id", "prompt", "n_predict", "temperature", "top_p", "top_k",
              "cache_prompt", "request_digest"}
    for raw in prompts:
        prompt = _exact(raw, fields, "frozen prompt")
        prompt_id = _text(prompt["prompt_id"], "frozen prompt ID")
        _text(prompt["prompt"], "frozen prompt body")
        _integer(prompt["n_predict"], "frozen prompt n_predict", minimum=1)
        if not _finite(prompt["temperature"]) or not _finite(prompt["top_p"]):
            raise ProjectionError("frozen prompt sampling values must be finite")
        _integer(prompt["top_k"], "frozen prompt top_k")
        if not isinstance(prompt["cache_prompt"], bool):
            raise ProjectionError("frozen prompt cache_prompt must be boolean")
        body = {key: prompt[key] for key in ("prompt", "n_predict", "temperature",
                                             "top_p", "top_k", "cache_prompt")}
        if prompt["request_digest"] != _hash(body):
            raise ProjectionError("frozen request digest mismatch")
        if prompt_id in by_id:
            raise ProjectionError("prompt manifest has duplicate prompt IDs")
        by_id[prompt_id] = prompt
    body = dict(manifest)
    digest = body.pop("digest")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest) or _hash(body) != digest:
        raise ProjectionError("prompt manifest digest mismatch")
    return manifest, by_id


def _validate_witnesses(value: Any, label: str) -> dict:
    if not isinstance(value, dict) or any(not isinstance(key, str) or not key for key in value):
        raise ProjectionError(f"{label} must be a text-keyed object")
    for name, raw in value.items():
        witness = _exact(raw, {"status", "ref"}, f"{label}.{name}")
        if witness["status"] not in {"pass", "fail", "unknown"}:
            raise ProjectionError(f"{label}.{name}.status is unsupported")
        _text(witness["ref"], f"{label}.{name}.ref", nullable=True)
        if witness["status"] == "pass" and witness["ref"] is None:
            raise ProjectionError(f"{label}.{name} passed without a reference")
    return value


def _validate(source: Any, *, corpus_root: Path | None) -> tuple[dict, dict | None]:
    carrier, payload = _carrier(source)
    v2 = carrier.get("schema") == CAPTURE_SCHEMA_V2
    carrier_fields = {"schema", "producer", "measurement_id", "arm", "arm_locator",
                      "plan", "prompt_manifest", "prompt_manifest_digest", "lineage_id",
                      "comparison_identities", "source_identity", "capture_context",
                      "admissible_view", "raw_artifacts", "environment_verdicts", "status",
                      "diagnostic_reason", "measurement", "claim", "category", "phase",
                      "record_class", "intended_use", "protocol_id", "protocol_status",
                      "instrument_id", "interval", "carrier_digest"}
    if v2:
        carrier_fields |= {"loaded_instrument", "lifecycle_observations"}
    _exact(carrier, carrier_fields, "unified arm carrier")
    arm = carrier["arm"]
    producer = PRODUCER_ID_V2 if v2 else PRODUCER_ID
    if (carrier["schema"] not in {CAPTURE_SCHEMA, CAPTURE_SCHEMA_V2}
            or carrier["producer"] != producer
            or not isinstance(carrier["measurement_id"], str)
            or not _SHA.fullmatch(carrier["measurement_id"])
            or not isinstance(arm, str) or arm not in {"anchor", "candidate"}
            or not isinstance(carrier["carrier_digest"], str)):
        raise ProjectionError("unsupported or malformed unified arm carrier")
    body = dict(carrier)
    digest = body.pop("carrier_digest")
    if not _SHA.fullmatch(digest) or _hash(body) != digest:
        raise ProjectionError("unified arm carrier digest mismatch")
    if payload is not None:
        artifact = payload.get("artifact")
        if not isinstance(artifact, dict) or corpus_root is None:
            raise ProjectionError("journal capture requires an allowlisted corpus root")
        sealed = _artifact_bytes(corpus_root, artifact.get("locator"), artifact.get("sha256"))
        if artifact.get("verified") is not True or sealed != carrier:
            raise ProjectionError("journal artifact does not contain the exact carrier")
    plan, expected_by_id, plan_digest, loaded_instrument = _validate_plan(
        carrier["plan"], corpus_root=corpus_root)
    if v2 and carrier.get("loaded_instrument") != loaded_instrument:
        raise ProjectionError("v2 carrier loaded instrument differs from frozen plan")
    if not v2 and plan["schema"] != "epyc.autokernel.experiment_plan.v1":
        raise ProjectionError("v1 carrier cannot relabel a v2 plan")
    identities = carrier.get("comparison_identities")
    source_identity = carrier.get("source_identity")
    if (not isinstance(identities, dict) or set(identities) != {"anchor", "candidate"}
            or identities != {"anchor": plan["anchor_identity"],
                              "candidate": plan["candidate_identity"]}
            or not isinstance(source_identity, dict)):
        raise ProjectionError("unified arm frozen identities are malformed")
    for name in ("anchor", "candidate"):
        _validate_identity(identities[name], f"comparison identities.{name}",
                           v2=v2, instrument=loaded_instrument)
    measurement_identity = {"producer": producer, "plan_digest": plan_digest,
                            "lineage_id": carrier.get("lineage_id"), "arm": arm}
    if v2:
        measurement_identity |= {"capture_schema": CAPTURE_SCHEMA_V2,
                                 "instrument_identity_sha256":
                                     loaded_instrument["identity_sha256"]}
    expected_measurement_id = _hash(measurement_identity)
    if (carrier["measurement_id"] != expected_measurement_id
            or carrier.get("arm_locator") !=
            f"planned-serving:{plan_digest}:{carrier.get('lineage_id')}:{arm}"):
        raise ProjectionError("unified arm measurement/locator identity mismatch")
    prompts, frozen_by_id = _validate_prompts(carrier["prompt_manifest"])
    prompt_digest = prompts["digest"]
    if carrier.get("prompt_manifest_digest") != prompt_digest:
        raise ProjectionError("unified arm prompt manifest digest mismatch")
    if any(prompt_id not in frozen_by_id for spec in expected_by_id.values()
           for prompt_id in spec["expected_prompt_ids"]):
        raise ProjectionError("frozen unit refers to a missing prompt")
    identity = identities[arm]
    if (set(source_identity) != {"source_revision", "model_sha256", "build_sha256",
                                "recipe_hash"}
            or not isinstance(source_identity.get("source_revision"), str)
            or len(source_identity["source_revision"]) not in {40, 64}
            or any(char not in "0123456789abcdef" for char in source_identity["source_revision"])
            or source_identity.get("model_sha256") != identity.get("model_digest")
            or source_identity.get("build_sha256") != identity.get("executable_digest")
            or source_identity.get("recipe_hash") != identity.get("template_hash")):
        raise ProjectionError("unified arm source/execution identity mismatch")
    if (carrier.get("category") != plan.get("category")
            or carrier.get("phase") != plan.get("phase")
            or carrier.get("record_class") != plan.get("record_class")
            or carrier.get("intended_use") != plan.get("intended_use")
            or carrier.get("protocol_id") != plan.get("protocol_ref")
            or carrier.get("protocol_status") != plan.get("protocol_status")):
        raise ProjectionError("unified arm carrier relabels its frozen plan")
    context = _exact(carrier["capture_context"], {
        "campaign_id", "config_digest", "supervisor_id", "supervisor_incarnation",
        "config_generation", "worker_id", "worker_incarnation", "grant_id",
        "container_id", "lineage_id", "instrument_id", "protocol_id",
        "protocol_status", "source_identities"}, "capture context")
    for key in ("campaign_id", "supervisor_id", "worker_id", "grant_id", "container_id",
                "lineage_id", "instrument_id"):
        _text(context[key], f"capture context.{key}")
    for key in ("supervisor_incarnation", "config_generation", "worker_incarnation"):
        _integer(context[key], f"capture context.{key}", minimum=1)
    if (not isinstance(context["config_digest"], str)
            or not _SHA.fullmatch(context["config_digest"])
            or context["campaign_id"] != plan["campaign_id"]
            or context["lineage_id"] != carrier["lineage_id"]
            or context["instrument_id"] != carrier["instrument_id"]
            or context["protocol_id"] != carrier["protocol_id"]
            or context["protocol_status"] != carrier["protocol_status"]
            or not isinstance(context["source_identities"], dict)
            or set(context["source_identities"]) != {"anchor", "candidate"}
            or context["source_identities"].get(arm) != source_identity):
        raise ProjectionError("capture context does not bind the frozen carrier")
    for name in ("anchor", "candidate"):
        item = context["source_identities"][name]
        resolved = identities[name]
        if (not isinstance(item, dict)
                or set(item) != {"source_revision", "model_sha256", "build_sha256",
                                 "recipe_hash"}
                or not isinstance(item.get("source_revision"), str)
                or len(item["source_revision"]) not in {40, 64}
                or any(char not in "0123456789abcdef" for char in item["source_revision"])
                or item.get("model_sha256") != resolved["model_digest"]
                or item.get("build_sha256") != resolved["executable_digest"]
                or item.get("recipe_hash") != resolved["template_hash"]):
            raise ProjectionError("capture context source identities do not rederive")
    expected_instrument = loaded_instrument["identity_sha256"] if v2 else "planned-serving/v1"
    if (carrier["instrument_id"] != expected_instrument
            or carrier["claim"] != f"{arm} {plan['metric']} for frozen plan {plan['plan_id']}"):
        raise ProjectionError("carrier instrument or claim relabels the frozen measurement")
    artifacts = _embedded_artifacts(carrier, corpus_root)
    if carrier.get("status") == "diagnostic":
        if carrier.get("measurement") is not None \
                or not isinstance(carrier.get("diagnostic_reason"), str) \
                or not carrier["diagnostic_reason"].strip():
            raise ProjectionError("diagnostic carrier must have a reason and no measurement")
        return carrier, payload
    if carrier.get("status") != "measurement":
        raise ProjectionError("unified arm carrier status is unsupported")
    interval = carrier.get("interval")
    if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
        raise ProjectionError("unified arm measurement interval is malformed")
    started = _timestamp(interval["start"], "measurement interval start")
    ended = _timestamp(interval["end"], "measurement interval end")
    if ended < started:
        raise ProjectionError("unified arm measurement interval is reversed or naive")
    measurement = carrier.get("measurement")
    view = carrier.get("admissible_view")
    if (not isinstance(measurement, dict) or not isinstance(view, dict)
            or not artifacts):
        raise ProjectionError("measurement carrier lacks native inputs")
    _exact(measurement, {"metric", "value", "unit", "independent_unit", "direction",
                         "independent_n", "reps_basis", "per_launch_values"},
           "arm measurement")
    _exact(view, _VIEW_FIELDS, "admissible view")
    view_body = dict(view)
    view_digest = view_body.pop("view_digest")
    if (not isinstance(view_digest, str) or not _SHA.fullmatch(view_digest)
            or _hash(view_body) != view_digest or view["schema"] !=
            "epyc.autokernel.admissible_unit_view.v1" or view["plan_digest"] != plan_digest):
        raise ProjectionError("admissible view identity does not rederive")
    rows = view.get("selected_rows")
    if not isinstance(rows, list):
        raise ProjectionError("measurement carrier selected rows are malformed")
    arm_rows = [row for row in rows if isinstance(row, dict) and row.get("arm") == arm]
    expected_units = plan["expected_units"]
    if ({row.get("unit_id") for row in rows if isinstance(row, dict)}
            != set(expected_by_id) or view.get("complete") is not True
            or view.get("missing_expected_units") != []
            or view.get("rejection_reasons") != {}
            or view.get("independent_n") != {"anchor": plan["stopping"]["n_per_arm"],
                                              "candidate": plan["stopping"]["n_per_arm"]}):
        raise ProjectionError("measurement carrier is not a complete canonical unit view")
    if [row.get("unit_id") if isinstance(row, dict) else None for row in rows] != [
            unit["unit_id"] for unit in sorted(expected_units, key=lambda item: item["order_index"])]:
        raise ProjectionError("measurement carrier selected row order is not canonical")
    for row in rows:
        _exact(row, _RAW_FIELDS, "selected raw unit")
        spec = expected_by_id.get(row["unit_id"])
        witnesses = _validate_witnesses(row["witnesses"], "selected raw unit witnesses")
        if (spec is None or row["schema"] != "epyc.autokernel.raw_unit.v1"
                or row["plan_digest"] != plan_digest or row["arm"] != spec["arm"]
                or row["process_id"] != spec["process_id"]
                or row["prompt_ids"] != spec["expected_prompt_ids"]
                or row["observed_order_index"] != spec["order_index"]
                or row["terminal"] is not True or not _finite(row["value"])
                or row["recorded_screen"] not in {"clean", "flagged_but_retained"}
                or (row["recorded_screen"] == "clean" and row["reason"] is not None)
                or (row["recorded_screen"] != "clean" and not isinstance(row["reason"], str))
                or not isinstance(row["artifact_digest"], str)
                or not _SHA.fullmatch(row["artifact_digest"])):
            raise ProjectionError("measurement carrier selected row violates frozen unit identity")
        for name in plan["required_witnesses"]:
            witness = witnesses.get(name)
            if not isinstance(witness, dict) or witness["status"] != "pass" \
                    or witness["ref"] is None:
                raise ProjectionError(f"selected row lacks required witness {name}")
    expected_for_arm = [item for item in expected_units if isinstance(item, dict)
                        and item.get("arm") == arm]
    if ({item.get("unit_id") for item in arm_rows}
            != {item.get("unit_id") for item in expected_for_arm}):
        raise ProjectionError("unified arm selected units differ from frozen plan")
    declared_n = plan.get("stopping", {}).get("n_per_arm") \
        if isinstance(plan.get("stopping"), dict) else None
    if (isinstance(declared_n, bool) or not isinstance(declared_n, int) or declared_n < 1
            or len(arm_rows) != declared_n
            or measurement.get("independent_n") != declared_n):
        raise ProjectionError("unified arm independent launch count mismatch")
    artifact_digests = [item.get("artifact_digest") for item in artifacts]
    if (any(not isinstance(item, str) or not _SHA.fullmatch(item)
            for item in artifact_digests) or len(set(artifact_digests)) != len(artifact_digests)):
        raise ProjectionError("unified arm has duplicate or malformed native artifact IDs")
    natives = {item["artifact_digest"]: item for item in artifacts
               if item.get("kind") == "native_observation"}
    attempts = [item for item in artifacts if item.get("kind") == "completed_attempt"]
    if len(natives) != len(arm_rows) or len(attempts) != len(arm_rows) \
            or len(artifacts) != len(natives) + len(attempts):
        raise ProjectionError("unified arm artifact set is incomplete or unsupported")
    attempts.sort(key=lambda item: expected_by_id.get(item.get("unit_id"), {}).get(
        "order_index", len(expected_units)))
    lifecycle_by_unit: dict[str, dict] = {}
    if v2:
        raw_references = carrier.get("lifecycle_observations")
        if not isinstance(raw_references, list):
            raise ProjectionError("v2 lifecycle observations must be an array")
        for raw_reference in raw_references:
            reference = _validate_lifecycle_reference(raw_reference, corpus_root)
            unit_id = reference["unit_id"]
            if unit_id in lifecycle_by_unit:
                raise ProjectionError("v2 lifecycle observations contain duplicate units")
            lifecycle_by_unit[unit_id] = reference
        if set(lifecycle_by_unit) != {row["unit_id"] for row in arm_rows}:
            raise ProjectionError("v2 requires exactly one lifecycle observation per arm unit")
        generations = {row["grant_generation"] for row in lifecycle_by_unit.values()}
        if len(generations) != 1:
            raise ProjectionError("v2 lifecycle observations disagree on grant generation")
    expected_environment = []
    states = {"contention": {"pass": "clean", "fail": "contaminated", "unknown": "unknown"},
              "placement": {"pass": "proven", "fail": "refuted", "unknown": "unknown"},
              "residency": {"pass": "proven", "fail": "refuted", "unknown": "unknown"}}
    for attempt in attempts:
        witnesses = attempt.get("stage_witnesses")
        if not isinstance(witnesses, dict):
            witnesses = {}
        item = {"unit_id": attempt.get("unit_id")}
        for name, mapping in states.items():
            witness = witnesses.get(name)
            status = witness.get("status") if isinstance(witness, dict) else "unknown"
            ref = witness.get("ref") if isinstance(witness, dict) else None
            item[name] = ({"verdict": "not_applicable", "ref": None}
                          if name == "residency" and identity.get("backend") == "cpu"
                          else {"verdict": mapping.get(status, "unknown"), "ref": ref})
        expected_environment.append(item)
    if carrier.get("environment_verdicts") != expected_environment:
        raise ProjectionError("unified arm environment verdict summary does not rederive")
    values: list[float] = []
    windows: list[tuple[datetime, datetime, str, str]] = []
    for row in arm_rows:
        matched = [item for item in attempts if item.get("unit_id") == row.get("unit_id")]
        if len(matched) != 1:
            raise ProjectionError("unified arm has missing or duplicate attempt")
        attempt = matched[0]
        _exact(attempt, _ATTEMPT_FIELDS_V2 if v2 else _ATTEMPT_FIELDS,
               "completed attempt")
        native = natives.get(attempt.get("native_observation_digest"))
        _exact(native, _NATIVE_FIELDS_V2 if v2 else _NATIVE_FIELDS,
               "native observation")
        if ((v2 and (native.get("schema") != "epyc.autokernel.planned_serving_artifact.v2"
                     or attempt.get("schema") !=
                     "epyc.autokernel.planned_serving_artifact.v2"))
                or (not v2 and (native.get("schema") !=
                                "epyc.autokernel.planned_serving_artifact.v1"
                                or attempt.get("schema") !=
                                "epyc.autokernel.planned_serving_artifact.v1"))):
            raise ProjectionError("planned serving artifact schema/capture version mismatch")
        if v2:
            reference = lifecycle_by_unit.get(row["unit_id"])
            if (native.get("lifecycle_observation") != reference
                    or attempt.get("lifecycle_observation_content_sha256") !=
                    reference.get("observation_content_sha256")
                    or reference.get("process_generation_id") != row["process_id"]
                    or reference.get("fence_id") != native.get("fence_id")
                    or reference.get("worker_id") != context.get("worker_id")
                    or reference.get("worker_generation") != context.get("worker_incarnation")
                    or reference.get("grant_id") != context.get("grant_id")
                    or reference.get("container_id") != context.get("container_id")
                    or reference.get("instrument_identity_sha256") !=
                    loaded_instrument["identity_sha256"]
                    or reference.get("shutdown_status") != "resolved"
                    or reference.get("successor_permitted") is not True):
                raise ProjectionError("v2 lifecycle observation differs from unit ownership")
        selected = native.get("selected_observation") if isinstance(native, dict) else None
        requests = selected.get("requests") if isinstance(selected, dict) else None
        if (not isinstance(requests, list) or selected.get("teardown") not in {
                "terminated", "killed"} or selected.get("failure") is not None
                or not isinstance(native.get("observations"), list)
                or not native["observations"] or native["observations"][-1] != selected):
            raise ProjectionError("unified arm native request rows are missing")
        _exact(selected, {"schema", "process_pid", "requests", "residency", "teardown",
                          "failure"}, "selected serving observation")
        if selected["schema"] != "epyc.autokernel.serving_observation.v1" \
                or not isinstance(selected["residency"], dict):
            raise ProjectionError("selected serving observation is malformed")
        if v2 and selected["process_pid"] != lifecycle_by_unit[
                row["unit_id"]]["target_pid"]:
            raise ProjectionError(
                "v2 selected serving PID differs from lifecycle target PID")
        request_rows = [item for item in requests if isinstance(item, dict)
                        and item.get("phase") == "measurement"]
        if len(request_rows) != len(row["prompt_ids"]):
            raise ProjectionError("unified arm slot count differs from frozen prompts")
        spec = next((item for item in expected_for_arm
                     if item.get("unit_id") == row.get("unit_id")), None)
        common = ("plan_digest", "unit_id", "arm", "process_generation_id", "lineage_id",
                  "fence_id", "grant_id", "container_id", "worker_identity",
                  "observed_started_at", "observed_ended_at", "prompt_manifest_digest",
                  "comparison_identities")
        if (spec is None or row["process_id"] != spec["process_id"]
                or row["prompt_ids"] != spec["expected_prompt_ids"]
                or native.get("plan_digest") != plan_digest
                or attempt.get("plan_digest") != plan_digest
                or native.get("process_generation_id") != spec["process_id"]
                or attempt.get("process_generation_id") != spec["process_id"]
                or native.get("unit_id") != spec["unit_id"]
                or attempt.get("unit_id") != spec["unit_id"]
                or native.get("arm") != arm or attempt.get("arm") != arm
                or any(native.get(key) != attempt.get(key) for key in common)
                or attempt.get("prompt_ids") != row["prompt_ids"]
                or attempt.get("terminal") is not True
                or attempt.get("value") != row["value"]
                or attempt.get("recorded_screen") != row["recorded_screen"]
                or attempt.get("reason") != row["reason"]
                or attempt.get("provider_recorded_screen") not in {
                    "clean", "flagged_but_retained", "rejected"}
                or attempt.get("artifact_digest") != row["artifact_digest"]
                or native.get("comparison_identities") != identities
                or attempt.get("comparison_identities") != identities
                or native.get("prompt_manifest_digest") != prompt_digest):
            raise ProjectionError("unified arm unit/process/identity binding mismatch")
        worker = native.get("worker_identity")
        _exact(worker, {"supervisor_id", "supervisor_incarnation", "config_generation",
                        "worker_id", "worker_incarnation"}, "native worker identity")
        for key in ("supervisor_id", "worker_id"):
            _text(worker[key], f"native worker identity.{key}")
        for key in ("supervisor_incarnation", "config_generation", "worker_incarnation"):
            _integer(worker[key], f"native worker identity.{key}", minimum=1)
        if (not isinstance(context, dict)
                or worker != attempt.get("worker_identity")
                or worker.get("worker_id") != context.get("worker_id")
                or worker.get("worker_incarnation") != context.get("worker_incarnation")
                or worker.get("supervisor_id") != context.get("supervisor_id")
                or worker.get("supervisor_incarnation") != context.get("supervisor_incarnation")
                or worker.get("config_generation") != context.get("config_generation")
                or native.get("lineage_id") != carrier.get("lineage_id")
                or attempt.get("lineage_id") != carrier.get("lineage_id")
                or native.get("grant_id") != context.get("grant_id")
                or attempt.get("grant_id") != context.get("grant_id")
                or native.get("container_id") != context.get("container_id")
                or attempt.get("container_id") != context.get("container_id")):
            raise ProjectionError("unified arm worker/grant/container lineage mismatch")
        if [request.get("prompt_id") for request in request_rows] != row["prompt_ids"]:
            raise ProjectionError("native request order differs from its frozen unit")
        for slot, request in enumerate(request_rows):
            _exact(request, {"phase", "slot_index", "prompt_id", "request_sha256",
                             "predicted_n", "predicted_per_second", "terminal", "error"},
                   "native measurement request")
            frozen = frozen_by_id.get(request.get("prompt_id"))
            if not isinstance(frozen, dict):
                raise ProjectionError("unified arm request is absent from frozen manifest")
            body = {key: frozen[key] for key in ("prompt", "n_predict", "temperature",
                                                 "top_p", "top_k", "cache_prompt")}
            if (request.get("request_sha256") != hashlib.sha256(_canonical(body)).hexdigest()
                    or frozen.get("request_digest") != request.get("request_sha256")
                    or request.get("slot_index") != slot
                    or request.get("predicted_n") != frozen["n_predict"]):
                raise ProjectionError("unified arm exact request bytes do not rederive")
        rates = [item.get("predicted_per_second") for item in request_rows]
        if (any(not _finite(value) for value in rates)
                or any(item.get("terminal") is not True or item.get("error") is not None
                       for item in request_rows)):
            raise ProjectionError("unified arm contains partial/failed slot metric")
        value = sum(float(item) for item in rates)
        if row["value"] != value or native.get("value") != value or native.get("error") is not None:
            raise ProjectionError("unified arm raw slot sum differs from unit value")
        witnesses = attempt.get("stage_witnesses")
        _validate_witnesses(witnesses, "completed attempt witnesses")
        if witnesses != row["witnesses"]:
            raise ProjectionError("attempt witnesses differ from selected raw unit")
        for name in ("contention", "placement"):
            witness = witnesses.get(name)
            if not isinstance(witness, dict) or witness.get("status") != "pass" \
                    or not witness.get("ref"):
                raise ProjectionError(f"unified arm {name} is not prospectively proven")
        if identity.get("backend") == "gpu":
            witness = witnesses.get("residency")
            if not isinstance(witness, dict) or witness.get("status") != "pass" \
                    or not witness.get("ref"):
                raise ProjectionError("unified GPU arm has no in-window residency proof")
        elif identity.get("backend") != "cpu":
            raise ProjectionError("unified arm backend is unsupported")
        native_start = _timestamp(native["observed_started_at"], "native observation start")
        native_end = _timestamp(native["observed_ended_at"], "native observation end")
        if native_end < native_start:
            raise ProjectionError("native observation interval is reversed")
        windows.append((native_start, native_end, native["observed_started_at"],
                        native["observed_ended_at"]))
        values.append(value)
    first = min(windows, key=lambda item: item[0])
    last = max(windows, key=lambda item: item[1])
    if interval != {"start": first[2], "end": last[3]}:
        raise ProjectionError("outer interval does not rederive from native observations")
    if (plan.get("estimator_id") != "median.v1"
            or measurement.get("per_launch_values") != values
            or not _finite(measurement.get("value"))
            or measurement["value"] != median(values)
            or measurement.get("metric") != plan.get("metric")
            or measurement.get("direction") != plan.get("metric_direction")
            or measurement.get("unit") != "t/s"
            or measurement.get("independent_unit") != plan.get("unit")
            or measurement.get("reps_basis") != "scored independent process launches"
            or plan.get("instrument_class") != "serving" or plan.get("unit") != "process"
            or plan.get("estimand") != "level"):
        raise ProjectionError("unified arm aggregate does not rederive")
    return carrier, payload


def diagnostic_reason(source: Any, *, corpus_root: Path | None = None) -> str | None:
    try:
        carrier, _ = _validate(source, corpus_root=corpus_root)
    except ProjectionError as exc:
        return f"refused:{exc}"
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError,
            UnicodeError, RecursionError) as exc:
        return f"refused:malformed unified arm nested data: {exc}"
    if carrier.get("status") == "diagnostic":
        return f"diagnostic:{carrier.get('diagnostic_reason') or 'unspecified'}"
    return None


def native_rows(source: Any, *, receipt_locator: str = "", receipt_sha256: str = "",
                attestation_present: bool = False,
                corpus_root: Path | None = None) -> tuple[dict, ...]:
    try:
        carrier, payload = _validate(source, corpus_root=corpus_root)
    except ProjectionError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError,
            UnicodeError, RecursionError) as exc:
        raise ProjectionError(f"malformed unified arm nested data: {exc}") from exc
    if carrier.get("status") != "measurement":
        return ()
    if (not isinstance(receipt_locator, str) or not receipt_locator
            or not isinstance(receipt_sha256, str) or not _SHA.fullmatch(receipt_sha256)
            or not isinstance(attestation_present, bool)):
        raise ProjectionError("unified arm projection requires exact receipt locator and digest")
    return ({"source": source, "carrier": carrier, "payload": payload,
             "receipt_locator": receipt_locator, "receipt_sha256": receipt_sha256,
             "attestation_present": attestation_present,
             "corpus_root": str(corpus_root) if corpus_root is not None else None},)


def _project_impl(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "source" not in native:
        raise ProjectionError("unified arm native row must retain its source")
    root = Path(native["corpus_root"]) if native.get("corpus_root") else None
    derived = native_rows(native["source"], receipt_locator=native.get("receipt_locator", ""),
                          receipt_sha256=native.get("receipt_sha256", ""),
                          attestation_present=native.get("attestation_present", False),
                          corpus_root=root)
    if len(derived) != 1:
        raise ProjectionError("unified arm source is not a measurement")
    expected = derived[0]
    for key in ("receipt_locator", "receipt_sha256", "attestation_present"):
        if native.get(key) != expected[key]:
            raise ProjectionError(f"unified arm native row mutated {key}")
    carrier = expected["carrier"]
    measurement = carrier["measurement"]
    direction = {"higher": "higher_better", "lower": "lower_better"}.get(
        measurement["direction"])
    if direction is None:
        raise ProjectionError("unified arm metric direction is unsupported")
    interval = carrier.get("interval")
    if not isinstance(interval, dict) or not isinstance(interval.get("start"), str) \
            or not isinstance(interval.get("end"), str):
        raise ProjectionError("unified arm measurement interval is missing")
    extra = {"arm": carrier["arm"], "arm_locator": carrier["arm_locator"],
             "campaign_id": carrier["capture_context"]["campaign_id"],
             "plan_digest": _hash(carrier["plan"]),
             "phase": carrier["phase"], "record_class": carrier["record_class"],
             "intended_use": carrier["intended_use"],
             "protocol_status": carrier["protocol_status"],
             "instrument_id": carrier["instrument_id"],
             "independent_unit": measurement["independent_unit"],
             "source_identity": carrier["source_identity"],
             "comparison_identities": carrier["comparison_identities"],
             "interval": interval, "applicability": "observation_only"
             if carrier["record_class"] != "registered_claim" else "policy_undefined"}
    if carrier["schema"] == CAPTURE_SCHEMA_V2:
        extra |= {"capture_schema": CAPTURE_SCHEMA_V2,
                  "instrument_identity_sha256":
                      carrier["loaded_instrument"]["identity_sha256"],
                  "lifecycle_observation_references": carrier["lifecycle_observations"]}
    return ClaimTuple(
        measurement_id=f"akarm_{carrier['measurement_id'][:24]}",
        metric=measurement["metric"], value=measurement["value"],
        date=interval["end"][:10], category=carrier["category"], claim=carrier["claim"],
        metric_direction=direction,
        protocol_id=carrier["protocol_id"] if carrier["protocol_status"] == "ratified" else "",
        reps=measurement["independent_n"], reps_basis=measurement["reps_basis"],
        unit=measurement["unit"], attestation_sha256=expected["receipt_sha256"],
        attestation_locator=expected["receipt_locator"],
        attestation_present=expected["attestation_present"],
        source_kind="autokernel-unified-arm-measurement", extra=extra,
    )


@register("autokernel-unified-arm-measurement")
def project(native: Any) -> ClaimTuple:
    try:
        return _project_impl(native)
    except ProjectionError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError,
            UnicodeError, RecursionError) as exc:
        raise ProjectionError(f"malformed unified arm projection row: {exc}") from exc


def project_journal_event(source: Any, *, corpus_root: Path) -> ClaimTuple | None:
    """Project one prospective native journal event without walking the corpus.

    This is the asynchronous-consumer boundary.  ``native_rows`` re-opens the
    carrier and every nested artifact beneath ``corpus_root`` and compares the
    bytes with their producer-authored digests before this function carries
    ``attestation_verified=True``.  Operational and diagnostic events return
    ``None``; they are never reconstructed as measurements.
    """
    if not isinstance(source, dict):
        raise ProjectionError("unified arm journal event must be an object")
    expected = {"journal_schema", "event_id", "seq", "kind", "campaign_id",
                "record_id", "written_at", "payload"}
    if set(source) != expected or source.get("journal_schema") != JOURNAL_SCHEMA:
        raise ProjectionError("malformed unified arm journal envelope")
    if source.get("kind") != JOURNAL_KIND:
        return None
    payload = source.get("payload")
    artifact = payload.get("artifact") if isinstance(payload, dict) else None
    if not isinstance(artifact, dict):
        raise ProjectionError("unified arm journal event lacks its sealed artifact")
    locator = artifact.get("locator")
    digest = artifact.get("sha256")
    rows = native_rows(
        source,
        receipt_locator=str((Path(corpus_root) / str(locator)).absolute()),
        receipt_sha256=str(digest or ""),
        attestation_present=True,
        corpus_root=Path(corpus_root),
    )
    if not rows:
        return None
    if len(rows) != 1:
        raise ProjectionError("unified arm journal event projected multiple measurements")
    # The strict read above is the write-boundary recomputation SC69 requires.
    return replace(project(rows[0]), attestation_verified=True)


__all__ = ["ADAPTER_ID", "CAPTURE_SCHEMA", "CAPTURE_SCHEMA_V2", "JOURNAL_KIND",
           "JOURNAL_SCHEMA",
           "diagnostic_reason", "native_rows", "project", "project_journal_event"]

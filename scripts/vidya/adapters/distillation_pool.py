"""Strict reader for prospective SkillBank distillation input-integrity receipts."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from claim_tuple import ClaimTuple, ProjectionError, register

SCHEMA = "epyc.distillation_pool_integrity.v1"
ADAPTER_ID = "vidya.adapters.distillation_pool/v1"
AUTHORITY = "selected_memory_integrity_observation_no_skill_quality_or_promotion"
RECEIPT_FIELDS = {
    "schema", "invocation_id", "captured_at_utc", "capture_stage", "synthetic", "unit", "selector",
    "teacher", "code_provenance", "source_store", "selected_rows", "selected_rows_sha256",
    "projection_markers",
    "counts", "legacy_m25_pool", "integrity", "receipt_sha256",
}
ROW_FIELDS = {"id", "action_type", "q_value", "outcome", "model_id", "from_tier", "to_tier"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(
        char in "0123456789abcdef" for char in value
    )


def _read_regular(path: Path, limit: int = 20 * 1024 * 1024) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise ValueError("capture is not an owned regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise ValueError("capture exceeds size limit")
        return data
    finally:
        os.close(fd)


def _counts(rows: list[dict[str, Any]], key: str, *, missing: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        raw = row.get(key)
        label = str(raw) if raw is not None and not (key == "outcome" and not raw) else missing
        result[label] = result.get(label, 0) + 1
    return dict(sorted(result.items()))


def _proposition(invocation_id: str, verdict: bool, errors: list[str]) -> str:
    detail = (
        "The returned rows meet the recorded top-k and Q filters; their IDs and metadata groups "
        "are internally consistent; legacy M-25 outcome counts rederive; and projected "
        "escalation marker IDs match rows whose native action_type is escalation."
    )
    if verdict:
        return f"Selected-memory integrity checks for invocation {invocation_id} passed: {detail}"
    return (
        f"Selected-memory integrity checks for invocation {invocation_id} failed; "
        f"false checks: {', '.join(errors)}."
    )


def _read_receipt(path: Path) -> tuple[dict[str, Any], str, str]:
    raw = _read_regular(path)
    try:
        record = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("receipt is not valid JSON") from exc
    if not isinstance(record, dict) or set(record) != RECEIPT_FIELDS or record.get("schema") != SCHEMA:
        raise ValueError("receipt schema or field set is incomplete/undeclared")
    claimed = record["receipt_sha256"]
    body = dict(record)
    body.pop("receipt_sha256")
    digest = _sha(_canonical(body))
    if claimed != digest or raw != _canonical(record):
        raise ValueError("receipt self-hash or canonical encoding mismatch")
    artifact_digest = _sha(raw)
    if not isinstance(record["invocation_id"], str) or not record["invocation_id"]:
        raise ValueError("invocation_id is missing")
    try:
        captured_at = record["captured_at_utc"]
        if not isinstance(captured_at, str) or not captured_at.endswith("Z"):
            raise ValueError("capture timestamp must be UTC Z")
        datetime.fromisoformat(captured_at[:-1] + "+00:00")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("captured_at_utc is invalid") from exc
    if type(record["synthetic"]) is not bool or record["unit"] != "episodic_memory_pattern":
        raise ValueError("synthetic/unit declaration is invalid")
    if record["capture_stage"] != "selected_pool_before_teacher":
        raise ValueError("receipt was not captured at the selected-pool pre-teacher boundary")

    rows = record["selected_rows"]
    if not isinstance(rows, list) or any(not isinstance(row, dict) or set(row) != ROW_FIELDS for row in rows):
        raise ValueError("selected_rows is malformed or contains undeclared fields")
    for row in rows:
        if (not isinstance(row["id"], str) or not row["id"]
                or not isinstance(row["action_type"], str) or not row["action_type"].strip()
                or type(row["q_value"]) not in (int, float) or not math.isfinite(row["q_value"])
                or not 0.0 <= row["q_value"] <= 1.0
                or (row["outcome"] is not None and not isinstance(row["outcome"], str))
                or (row["model_id"] is not None and not isinstance(row["model_id"], str))
                or (row["from_tier"] is not None and not isinstance(row["from_tier"], str))
                or (row["to_tier"] is not None and not isinstance(row["to_tier"], str))):
            raise ValueError("selected row has invalid native metadata")
    if record["selected_rows_sha256"] != _sha(_canonical(rows)):
        raise ValueError("selected metadata payload digest mismatch")
    projection_markers = record["projection_markers"]
    if (not isinstance(projection_markers, dict)
            or set(projection_markers) != {"escalation_memory_ids"}
            or not isinstance(projection_markers["escalation_memory_ids"], list)
            or any(value is not None and not isinstance(value, str)
                   for value in projection_markers["escalation_memory_ids"])):
        raise ValueError("projection marker payload is malformed")
    projected_escalation_ids = projection_markers["escalation_memory_ids"]
    expected_escalation_ids = sorted(row["id"] for row in rows if row["action_type"] == "escalation")

    selector = record["selector"]
    selector_fields = {
        "method", "query_method", "query_dimension", "query_vector_sha256", "k",
        "candidate_overfetch_multiplier", "action_type_filter", "min_q_value",
        "indexed_row_predicate", "return_order", "backend", "use_faiss",
    }
    if (not isinstance(selector, dict) or set(selector) != selector_fields
            or selector["method"] != "EpisodicStore.retrieve_by_similarity"
            or selector["query_method"] != "zero_vector"
            or selector["candidate_overfetch_multiplier"] != 2
            or selector["action_type_filter"] is not None
            or selector["indexed_row_predicate"] != "TRIM(COALESCE(action_type, '')) != ''"
            or selector["return_order"] != "similarity_score_descending_then_top_k"
            or type(selector["k"]) is not int or selector["k"] < 0
            or type(selector["query_dimension"]) is not int or selector["query_dimension"] <= 0
            or not _is_sha256(selector["query_vector_sha256"])
            or (selector["backend"] is not None and not isinstance(selector["backend"], str))
            or type(selector["use_faiss"]) not in (bool, type(None))
            or type(selector["min_q_value"]) not in (int, float)
            or not math.isfinite(selector["min_q_value"])
            or not 0.0 <= selector["min_q_value"] <= 1.0):
        raise ValueError("selector contract is malformed")

    teacher = record["teacher"]
    if (not isinstance(teacher, dict)
            or set(teacher) != {"requested", "declared_model_id", "actual_served_model_id", "actual_served_identity_basis"}
            or not isinstance(teacher["requested"], str) or not teacher["requested"]
            or (teacher["declared_model_id"] is not None
                and not isinstance(teacher["declared_model_id"], str))
            or teacher["actual_served_model_id"] is not None
            or teacher["actual_served_identity_basis"] != "unobserved"):
        raise ValueError("teacher identity distinction is malformed")
    if teacher["requested"] == "mock" and not record["synthetic"]:
        raise ValueError("mock teacher receipt must be explicitly synthetic")

    code = record["code_provenance"]
    code_fields = {
        "repo_root", "git_head", "tracked_dirty", "git_probe_error", "source_file",
        "source_file_sha256", "capture_helper_file", "capture_helper_sha256",
        "loaded_function_sha256", "loaded_function_identity_known", "loaded_capture_helper_sha256",
        "loaded_capture_helper_identity_known", "python_version",
    }
    if (not isinstance(code, dict) or set(code) != code_fields
            or not _is_sha256(code["source_file_sha256"])
            or not isinstance(code["capture_helper_file"], str)
            or not _is_sha256(code["capture_helper_sha256"])
            or type(code["tracked_dirty"]) not in (bool, type(None))
            or type(code["loaded_function_identity_known"]) is not bool
            or code["loaded_function_identity_known"] != (code["loaded_function_sha256"] is not None)
            or type(code["loaded_capture_helper_identity_known"]) is not bool
            or code["loaded_capture_helper_identity_known"] != (code["loaded_capture_helper_sha256"] is not None)
            or (code["loaded_function_sha256"] is not None
                and not _is_sha256(code["loaded_function_sha256"]))
            or (code["loaded_capture_helper_sha256"] is not None
                and not _is_sha256(code["loaded_capture_helper_sha256"]))
            or not isinstance(code["repo_root"], str) or not isinstance(code["source_file"], str)
            or (code["git_head"] is not None and not _is_git_sha(code["git_head"]))
            or (code["git_probe_error"] is not None
                and not isinstance(code["git_probe_error"], str))
            or not isinstance(code["python_version"], str)):
        raise ValueError("code provenance is malformed")

    store = record["source_store"]
    if (not isinstance(store, dict)
            or set(store) != {"sqlite", "storage_dir", "embedding_index", "id_map", "snapshot_claim"}
            or store["snapshot_claim"] != "none; exact returned metadata rows only, no whole-store hash or atomic snapshot"):
        raise ValueError("source store provenance or snapshot scope is malformed")
    for key in ("sqlite", "storage_dir", "embedding_index", "id_map"):
        identity = store[key]
        if (not isinstance(identity, dict) or not isinstance(identity.get("path"), str)
                or type(identity.get("available")) is not bool
                or set(identity) - {"path", "available", "error", "device", "inode", "size_bytes", "mtime_ns"}
                or (identity["available"] and set(identity) != {
                    "path", "available", "device", "inode", "size_bytes", "mtime_ns"})
                or (identity["available"] and any(
                    type(identity[field]) is not int or identity[field] < 0
                    for field in ("device", "inode", "size_bytes", "mtime_ns")))
                or (not identity["available"]
                    and (set(identity) != {"path", "available", "error"}
                         or not isinstance(identity["error"], str)))):
            raise ValueError(f"source store {key} identity is malformed")

    counts = record["counts"]
    if not isinstance(counts, dict) or set(counts) != {
            "selected_total", "projected_record_count", "by_action_type", "by_outcome", "by_model_id",
            "legacy_m25_by_outcome", "native_escalation_count", "projected_escalation_count"}:
        raise ValueError("count field set is malformed")
    native = {
        "selected_total": len(rows),
        "projected_record_count": len(rows),
        "by_action_type": _counts(rows, "action_type", missing="<null>"),
        "by_outcome": _counts(rows, "outcome", missing="unknown"),
        "by_model_id": _counts(rows, "model_id", missing="<null>"),
        "legacy_m25_by_outcome": _counts(rows, "outcome", missing="unknown"),
        "native_escalation_count": sum(1 for row in rows if row["action_type"] == "escalation"),
        "projected_escalation_count": len(projected_escalation_ids),
    }
    if (projected_escalation_ids != sorted(
            projected_escalation_ids, key=lambda value: "" if value is None else value)
            or any(type(counts.get(key)) is not int for key in (
                "selected_total", "projected_record_count", "native_escalation_count",
                "projected_escalation_count"))
            or any(not isinstance(counts.get(key), dict)
                   or any(type(value) is not int or value < 0 for value in counts[key].values())
                   for key in ("by_action_type", "by_outcome", "by_model_id", "legacy_m25_by_outcome"))):
        raise ValueError("descriptive count schema is malformed")
    legacy_pool = record["legacy_m25_pool"]
    if (not isinstance(legacy_pool, dict)
            or set(legacy_pool) != {"total", "by_outcome", "min_q_value"}
            or type(legacy_pool.get("total")) is not int
            or not isinstance(legacy_pool.get("by_outcome"), dict)
            or any(not isinstance(key, str) or type(value) is not int or value < 0
                   for key, value in legacy_pool["by_outcome"].items())
            or type(legacy_pool.get("min_q_value")) not in (int, float)
            or not math.isfinite(legacy_pool["min_q_value"])):
        raise ValueError("legacy M-25 pool count schema is malformed")

    integrity = record["integrity"]
    checks = {
        "selected_total_matches_native_selection": counts["selected_total"] == len(rows),
        "selected_total_matches_projected_records": (
            counts["selected_total"] == counts["projected_record_count"]
        ),
        "selected_total_within_requested_top_k": len(rows) <= selector["k"],
        "selected_q_values_meet_filter": all(row["q_value"] >= selector["min_q_value"] for row in rows),
        "group_counts_rederive_from_rows": (
            counts["by_action_type"] == native["by_action_type"]
            and counts["by_outcome"] == native["by_outcome"]
            and counts["by_model_id"] == native["by_model_id"]
            and counts["legacy_m25_by_outcome"] == native["legacy_m25_by_outcome"]
            and sum(counts["by_action_type"].values()) == len(rows)
            and sum(counts["by_outcome"].values()) == len(rows)
            and sum(counts["by_model_id"].values()) == len(rows)
        ),
        "legacy_m25_outcomes_match_native_rows": (
            legacy_pool.get("total") == len(rows) and legacy_pool.get("by_outcome") == native["by_outcome"]
        ),
        "legacy_m25_filter_matches_selector": legacy_pool.get("min_q_value") == selector["min_q_value"],
        "projection_marker_shape_valid": all(isinstance(value, str) and value for value in projected_escalation_ids),
        "escalation_projection_matches_native_action_type": (
            projected_escalation_ids == expected_escalation_ids
            and counts["projected_escalation_count"] == len(projected_escalation_ids)
        ),
        "native_escalation_count_matches_rows": (
            counts["native_escalation_count"] == native["native_escalation_count"]
        ),
        "selected_ids_unique": len({row["id"] for row in rows}) == len(rows),
    }
    if (not isinstance(integrity, dict)
            or set(integrity) != {"decided_proposition", "verdict", "checks", "errors"}
            or not isinstance(integrity["decided_proposition"], str)
            or not integrity["decided_proposition"].strip()
            or integrity["checks"] != checks
            or type(integrity["verdict"]) is not bool
            or integrity["verdict"] != all(checks.values())
            or integrity["errors"] != [key for key, passed in checks.items() if not passed]):
        raise ValueError("integrity verdict does not rederive from native receipt")
    if integrity["decided_proposition"] != _proposition(
            record["invocation_id"], integrity["verdict"], integrity["errors"]):
        raise ValueError("decided proposition does not describe the recorded verdict")
    return record, digest, artifact_digest


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    receipt_path = Path(path).absolute()
    try:
        record, digest, artifact_digest = _read_receipt(receipt_path)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectionError(f"distillation-pool receipt refused: {exc}") from exc
    if record["synthetic"]:
        return ()
    return ({
        "record": record,
        "receipt_path": str(receipt_path),
        "receipt_sha256": digest,
        "artifact_sha256": artifact_digest,
    },)


@register("distillation-pool", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project(native: dict[str, Any]) -> ClaimTuple:
    try:
        rows = native_rows(native["receipt_path"])
        if len(rows) != 1 or rows[0] != native:
            raise ProjectionError("receipt changed since reopening")
        record = native["record"]
        integrity = record["integrity"]
        proposition = integrity["decided_proposition"]
        return ClaimTuple(
            measurement_id=f"distillation-pool:{record['invocation_id']}:{native['receipt_sha256']}",
            metric="selected_memory_metadata_integrity",
            value=1 if integrity["verdict"] else 0,
            date=record["captured_at_utc"],
            category="CANDIDATE",
            claim=proposition,
            metric_direction="higher_better",
            protocol_id="",
            unit="false_0_true_1",
            attestation_path=native["receipt_path"],
            attestation_sha256=native["artifact_sha256"],
            attestation_present=True,
            attestation_verified=True,
            source_kind=ADAPTER_ID,
            decided_proposition=proposition,
            source_class="verifier",
            binding_kind="identity",
            binding_ref=native["receipt_sha256"],
            observation={
                "outcome_native": (
                    "distillation_pool_integrity_passed"
                    if integrity["verdict"] else "distillation_pool_integrity_failed"
                ),
                **({"outcome_reason": ", ".join(integrity["errors"])[:300]}
                   if integrity["errors"] else {}),
            },
            extra={
                "unit": "episodic_memory_pattern",
                "counts": record["counts"],
                "integrity_checks": integrity["checks"],
                "integrity_errors": integrity["errors"],
                "native_verdict": integrity["verdict"],
                "synthetic": False,
                "teacher_requested": record["teacher"]["requested"],
                "teacher_declared_model_id": record["teacher"]["declared_model_id"],
                "actual_served_model_id": None,
                "selected_rows_sha256": record["selected_rows_sha256"],
            },
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"distillation-pool projection refused: {exc}") from exc

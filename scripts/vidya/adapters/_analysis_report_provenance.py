"""Shared strict provenance checks for prospective analysis-report adapters."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from claim_tuple import ProjectionError


def canonical_sha256(value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"{label} unavailable: {path}") from exc


def validate_provenance(document: dict[str, Any], *, report_path: Path,
                        schema: str, producer_root: Path,
                        producer_path: str, report_bytes: bytes | None = None
                        ) -> tuple[dict[str, Any], str]:
    """Verify closed envelope, self hash, current producer, and every bound input snapshot."""
    provenance = document.get("native_provenance")
    if not isinstance(provenance, dict):
        raise ProjectionError("legacy analysis JSON has no native provenance; it is descriptive only")
    if set(provenance) != {"schema", "producer_path", "producer_sha256",
                           "producer_snapshot_path", "input_root",
                           "inputs", "missing_inputs", "analysis_config_sha256", "report_body_sha256",
                           "record_id", "report_sha256"}:
        raise ProjectionError("native_provenance has missing or unknown fields")
    if provenance.get("schema") != schema or provenance.get("producer_path") != producer_path:
        raise ProjectionError("native provenance schema or producer path is foreign")
    source = producer_root / producer_path
    producer_bytes = _read(source, "producer source")
    producer_sha = hashlib.sha256(producer_bytes).hexdigest()
    if provenance.get("producer_sha256") != producer_sha:
        raise ProjectionError("producer source bytes differ from the report-bound revision")
    producer_snapshot_path = provenance.get("producer_snapshot_path")
    if not isinstance(producer_snapshot_path, str) or not producer_snapshot_path:
        raise ProjectionError("producer source snapshot path is missing")
    producer_snapshot = Path(producer_snapshot_path)
    if not producer_snapshot.is_absolute():
        producer_snapshot = producer_root / producer_snapshot
    if _read(producer_snapshot, "producer source snapshot") != producer_bytes:
        raise ProjectionError("immutable producer snapshot differs from current producer source")
    if not isinstance(provenance.get("inputs"), list) or not provenance["inputs"]:
        raise ProjectionError("a measurement report must bind at least one parsed input file")
    if (not isinstance(provenance.get("missing_inputs"), list)
            or any(not isinstance(path, str) or not path for path in provenance["missing_inputs"])):
        raise ProjectionError("missing_inputs must be a list of named absent source files")
    if provenance["missing_inputs"]:
        raise ProjectionError("report references missing trace inputs and is incomplete")
    expected_root = "epyc-orchestrator"
    if provenance.get("input_root") != expected_root:
        raise ProjectionError("input_root must name the orchestrator repository")
    if provenance.get("analysis_config_sha256") != canonical_sha256(document.get("config", {})):
        raise ProjectionError("analysis config differs from its provenance binding")
    seen: set[str] = set()
    for item in provenance["inputs"]:
        if not isinstance(item, dict) or set(item) != {
                "path", "sha256", "byte_count", "row_count", "normalized_row_count",
                "snapshot_path"}:
            raise ProjectionError("input manifest row has missing or unknown fields")
        path_text = item.get("path")
        digest = item.get("sha256")
        if not isinstance(path_text, str) or not path_text or path_text in seen:
            raise ProjectionError("input manifest path is empty or duplicated")
        seen.add(path_text)
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ProjectionError("input manifest digest must be lowercase SHA-256")
        if type(item.get("byte_count")) is not int or item["byte_count"] < 0:
            raise ProjectionError("input manifest byte_count must be a nonnegative integer")
        if type(item.get("row_count")) is not int or item["row_count"] < 0:
            raise ProjectionError("input manifest row_count must be a nonnegative integer")
        if (type(item.get("normalized_row_count")) is not int
                or item["normalized_row_count"] < 0
                or item["normalized_row_count"] > item["row_count"]):
            raise ProjectionError("input manifest normalized_row_count is invalid")
        source_path = Path(path_text)
        if source_path.is_absolute():
            resolved = source_path
        else:
            resolved = (producer_root / source_path).resolve()
            if not resolved.is_relative_to(producer_root.resolve()):
                raise ProjectionError("relative input path escapes the named repository root")
        raw = _read(resolved, "bound input")
        if len(raw) != item["byte_count"] or hashlib.sha256(raw).hexdigest() != digest:
            raise ProjectionError(f"bound input bytes changed: {path_text}")
        snapshot_text = item.get("snapshot_path")
        if not isinstance(snapshot_text, str) or not snapshot_text:
            raise ProjectionError("immutable input snapshot path is missing")
        snapshot_path = Path(snapshot_text)
        if not snapshot_path.is_absolute():
            snapshot_path = producer_root / snapshot_path
        snapshot_bytes = _read(snapshot_path, "immutable input snapshot")
        if len(snapshot_bytes) != item["byte_count"] or hashlib.sha256(snapshot_bytes).hexdigest() != digest:
            raise ProjectionError(f"immutable input snapshot differs from its parsed-byte digest: {path_text}")
    id_body = dict(provenance)
    record_id = id_body.pop("record_id")
    report_sha = id_body.pop("report_sha256")
    body_only = dict(document)
    body_only.pop("native_provenance")
    if provenance.get("report_body_sha256") != canonical_sha256(body_only):
        raise ProjectionError("native report body differs from its identity digest")
    if record_id != canonical_sha256(id_body):
        raise ProjectionError("native record_id does not rederive")
    report_body = dict(document)
    report_body["native_provenance"] = dict(provenance)
    report_body["native_provenance"].pop("report_sha256")
    if report_sha != canonical_sha256(report_body):
        raise ProjectionError("native report_sha256 does not rederive")
    report_digest = hashlib.sha256(report_bytes if report_bytes is not None
                                   else _read(report_path, "report")).hexdigest()
    return provenance, report_digest

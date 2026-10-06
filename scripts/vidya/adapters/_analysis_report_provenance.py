"""Shared strict provenance checks for prospective analysis-report adapters."""
from __future__ import annotations

import hashlib
import json
import stat
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


def _read_snapshot(path_text: str, *, report_path: Path, label: str,
                   expected_directory: Path | None = None) -> bytes:
    """Read only a regular, non-symlink file under this report's native sidecar."""
    path = Path(path_text)
    if not path.is_absolute() or ".." in path.parts:
        raise ProjectionError(f"{label} path must be absolute and traversal-free")
    sidecar = report_path.absolute().with_name(report_path.name + ".native")
    try:
        if not path.is_relative_to(sidecar):
            raise ProjectionError(f"{label} escapes the report-adjacent snapshot directory")
        sidecar_info = sidecar.lstat()
        if not stat.S_ISDIR(sidecar_info.st_mode) or sidecar_info.st_mode & 0o077:
            raise ProjectionError("report snapshot root must be a private 0700 directory")
        relative = path.relative_to(sidecar)
        if len(relative.parts) != 2:
            raise ProjectionError(f"{label} must be in one report snapshot-key directory")
        if expected_directory is not None and path.parent != expected_directory:
            raise ProjectionError("all report snapshots must share one snapshot-key directory")
        cursor = Path(path.anchor)
        for component in path.parts[1:]:
            cursor /= component
            info = cursor.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ProjectionError(f"{label} path traverses a symlink")
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ProjectionError(f"{label} is not a regular file")
        if path.parent.stat().st_mode & 0o077:
            raise ProjectionError(f"{label} directory permissions are broader than 0700")
        # A snapshot is a historical byte binding. Mode checks catch accidental exposure,
        # but create-once + fsync does not make the underlying file immutable.
        if path.lstat().st_mode & 0o077:
            raise ProjectionError(f"{label} permissions are broader than 0600")
        return path.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"{label} unavailable: {path}") from exc


def validate_provenance(document: dict[str, Any], *, report_path: Path,
                        schema: str, producer_root: Path,
                        producer_path: str, report_bytes: bytes | None = None
                        ) -> tuple[dict[str, Any], str]:
    """Verify the report envelope and retained source/input snapshots for historical projection."""
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
    producer_sha = provenance.get("producer_sha256")
    if (not isinstance(producer_sha, str) or len(producer_sha) != 64
            or any(c not in "0123456789abcdef" for c in producer_sha)):
        raise ProjectionError("producer digest must be lowercase SHA-256")
    producer_snapshot_path = provenance.get("producer_snapshot_path")
    if not isinstance(producer_snapshot_path, str) or not producer_snapshot_path:
        raise ProjectionError("producer source snapshot path is missing")
    sidecar = report_path.absolute().with_name(report_path.name + ".native")
    producer_bytes = _read_snapshot(producer_snapshot_path, report_path=report_path,
                                    label="producer source snapshot")
    producer_snapshot = Path(producer_snapshot_path)
    snapshot_directory = producer_snapshot.parent
    if (snapshot_directory.parent != sidecar
            or len(snapshot_directory.name) != 64
            or any(c not in "0123456789abcdef" for c in snapshot_directory.name)):
        raise ProjectionError("producer snapshot must be under a canonical report snapshot key")
    if hashlib.sha256(producer_bytes).hexdigest() != producer_sha:
        raise ProjectionError("retained producer snapshot differs from its report-bound digest")
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
            if ".." in source_path.parts:
                raise ProjectionError("absolute input path may not contain traversal components")
        elif ".." in source_path.parts:
            raise ProjectionError("relative input path may not traverse outside its repository root")
        snapshot_text = item.get("snapshot_path")
        if not isinstance(snapshot_text, str) or not snapshot_text:
            raise ProjectionError("immutable input snapshot path is missing")
        snapshot_bytes = _read_snapshot(snapshot_text, report_path=report_path,
                                        label="input snapshot",
                                        expected_directory=snapshot_directory)
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

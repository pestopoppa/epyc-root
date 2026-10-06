"""Read the UFH-13 thesis producer's pooled belief sidecar.

This adapter projects only rows written by the pinned producer schema. It verifies the
run's native manifest identity and hashes the exact sibling ``records.jsonl`` bytes, but
never parses or emits per-item records or answer text. The shared measurement ladder is
the only grading authority; the native empty protocol id remains empty.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.ufh13_thesis/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ufh13-thesis-measurement"
SCHEMA = "ufh13-thesis-belief/v1"
MANIFEST = "run_manifest.json"
SIDECAR = "belief_measurements.jsonl"
RECORDS = "records.jsonl"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_COMMON_EXTRA = {
    "run_id", "suite_sha256", "preregistration_sha256", "verdict", "rule", "arm",
}
_ROW_FIELDS = {
    "schema", "date", "protocol_id", "reps_basis", "attestation_path",
    "attestation_sha256", "attestation_locator", "source_kind", "measurement_id",
    "metric", "value", "category", "claim", "metric_direction", "reps", "unit",
    "extra",
}
_ARMS = {"A0": "BASELINE", "A1": "BASELINE", "A2": "CANDIDATE"}
_METRICS = {
    "ufh13.accuracy.pooled": ("arm", "higher_better", "fraction", "by_suite"),
    "ufh13.consultant_device_seconds": ("arm", "lower_better", "s", None),
    "ufh13.gap_closure_G": (None, "higher_better", "fraction", "ci95+bootstrap"),
    "ufh13.gap_closure_G_lower95": (None, "higher_better", "fraction", "bootstrap"),
    "ufh13.consultant_cost_fraction_d": (None, "lower_better", "fraction", "ci95"),
}


def _signature(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _stable_bytes(path: Path, what: str) -> bytes:
    """Read one regular single-link file without following its final path component."""
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        raise ProjectionError(f"UFH-13 {what} cannot be opened with no-follow semantics")
    try:
        before_path = path.lstat()
    except OSError as exc:
        raise ProjectionError(f"UFH-13 {what} is unavailable: {exc}") from exc
    if not stat.S_ISREG(before_path.st_mode) or before_path.st_nlink != 1:
        raise ProjectionError(f"UFH-13 {what} must be a regular single-link file")
    flags = os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProjectionError(f"UFH-13 {what} cannot be opened safely: {exc}") from exc
    try:
        before_fd = os.fstat(descriptor)
        if not stat.S_ISREG(before_fd.st_mode) or _signature(before_path) != _signature(before_fd):
            raise ProjectionError(f"UFH-13 {what} changed before its read")
        chunks: list[bytes] = []
        try:
            while True:
                chunk = os.read(descriptor, 1 << 20)
                if not chunk:
                    break
                chunks.append(chunk)
            after_fd = os.fstat(descriptor)
        except OSError as exc:
            raise ProjectionError(f"UFH-13 {what} read failed: {exc}") from exc
    finally:
        os.close(descriptor)
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise ProjectionError(f"UFH-13 {what} disappeared during its read: {exc}") from exc
    if _signature(before_fd) != _signature(after_fd) or \
            _signature(before_fd) != _signature(after_path):
        raise ProjectionError(f"UFH-13 {what} changed during its read")
    return b"".join(chunks)


def _records_sha256(path: Path) -> str:
    raw = _stable_bytes(path, "records.jsonl")
    return hashlib.sha256(raw).hexdigest()


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON member {key!r}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise ValueError(f"non-finite JSON constant {token!r} is forbidden")


def _json_value(raw: bytes, what: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_members,
                          parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectionError(f"UFH-13 {what} is not strict JSON: {exc}") from exc


def _sha256(value: Any, what: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ProjectionError(f"UFH-13 {what} must be a lowercase SHA-256 digest")
    return value


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _manifest(sidecar: Path) -> tuple[dict[str, Any], str]:
    path = sidecar.parent / MANIFEST
    value = _json_value(_stable_bytes(path, "run_manifest.json"), "run_manifest.json")
    if not isinstance(value, dict):
        raise ProjectionError("UFH-13 run_manifest.json must contain one object")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ProjectionError("UFH-13 manifest run_id is missing")
    suite_sha256 = _sha256(value.get("suite_sha256"), "manifest suite_sha256")
    research_commit = value.get("research_commit")
    if not isinstance(research_commit, str) or not _HEX40.fullmatch(research_commit):
        raise ProjectionError("UFH-13 manifest research_commit must be 40 lowercase hex digits")
    if type(value.get("pilot")) is not bool:
        raise ProjectionError("UFH-13 manifest pilot flag must be a native boolean")
    if value["pilot"]:
        raise ProjectionError("UFH-13 pilot manifests cannot supply scored thesis measurements")
    return value, research_commit


def _metric_contract(row: dict[str, Any], run_id: str) -> None:
    metric = row.get("metric")
    if not isinstance(metric, str) or metric not in _METRICS:
        raise ProjectionError("UFH-13 sidecar has an unknown native metric")
    arm_kind, direction, unit, extra_shape = _METRICS[metric]
    extra = row.get("extra")
    if not isinstance(extra, dict):
        raise ProjectionError("UFH-13 row extra must be an object")
    arm = extra.get("arm")
    if arm_kind == "arm":
        if not isinstance(arm, str) or arm not in _ARMS:
            raise ProjectionError("UFH-13 arm metric has an unknown native arm")
        category = _ARMS[arm]
    else:
        if arm is not None:
            raise ProjectionError("UFH-13 run-level metric must not name an arm")
        category = "CANDIDATE"
    if row.get("category") != category or row.get("metric_direction") != direction or \
            row.get("unit") != unit:
        raise ProjectionError("UFH-13 row category, direction, or unit differs from producer contract")
    if row.get("protocol_id") != "" or row.get("reps_basis") != "scored":
        raise ProjectionError("UFH-13 row must retain its native empty protocol and scored reps basis")
    reps = row.get("reps")
    if type(reps) is not int or reps < 1:
        raise ProjectionError("UFH-13 row reps must be a positive native scored count")
    value = row.get("value")
    if not _finite_number(value):
        raise ProjectionError("UFH-13 row value must be a finite native number")
    if not isinstance(row.get("claim"), str) or not row["claim"].strip():
        raise ProjectionError("UFH-13 row claim is missing")
    date_value = row.get("date")
    if not isinstance(date_value, str) or not date_value.strip():
        raise ProjectionError("UFH-13 row date is missing")
    try:
        parsed_date = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError("UFH-13 row date is not an ISO-8601 timestamp") from exc
    if parsed_date.tzinfo is None or parsed_date.utcoffset() is None:
        raise ProjectionError("UFH-13 row date must retain its native timezone")
    if set(extra) != _COMMON_EXTRA | ({extra_shape} if extra_shape in {"by_suite", "ci95", "bootstrap"}
                                     else {"ci95", "bootstrap"} if extra_shape == "ci95+bootstrap"
                                     else set()):
        raise ProjectionError("UFH-13 row extra fields differ from producer contract")
    if extra.get("run_id") != run_id:
        raise ProjectionError("UFH-13 row run id differs from its manifest")
    if not isinstance(extra.get("suite_sha256"), str) or \
            not _HEX64.fullmatch(extra["suite_sha256"]):
        raise ProjectionError("UFH-13 row suite_sha256 is malformed")
    prereg = extra.get("preregistration_sha256")
    if prereg is not None and (not isinstance(prereg, str) or not _HEX64.fullmatch(prereg)):
        raise ProjectionError("UFH-13 row preregistration_sha256 is malformed")
    if not isinstance(extra.get("verdict"), str):
        raise ProjectionError("UFH-13 row verdict is not native text")
    rule = extra.get("rule")
    if not isinstance(rule, dict) or set(rule) != {"X", "Y", "X_Y_status"} or \
            not isinstance(rule.get("X_Y_status"), str):
        raise ProjectionError("UFH-13 row rule differs from the producer's native rule object")
    for key in ("X", "Y"):
        parameter = rule.get(key)
        if not _finite_number(parameter):
            raise ProjectionError(f"UFH-13 native rule parameter {key} is not finite")
    if extra_shape in {"by_suite", "ci95", "bootstrap", "ci95+bootstrap"}:
        for field in extra_shape.split("+"):
            if field not in extra:
                raise ProjectionError(f"UFH-13 row is missing native extra.{field}")
    if extra_shape == "by_suite":
        by_suite = extra["by_suite"]
        if not isinstance(by_suite, dict) or not by_suite or any(
                not isinstance(name, str) or not _finite_number(value)
                for name, value in by_suite.items()):
            raise ProjectionError("UFH-13 by_suite must preserve finite native suite values")
    if extra_shape in {"ci95", "ci95+bootstrap"}:
        ci = extra["ci95"]
        if not isinstance(ci, list) or len(ci) != 2 or any(
                not _finite_number(value) for value in ci):
            raise ProjectionError("UFH-13 ci95 must retain two finite native bounds")
    if extra_shape in {"bootstrap", "ci95+bootstrap"}:
        bootstrap = extra["bootstrap"]
        if not isinstance(bootstrap, dict) or set(bootstrap) != {
                "resamples", "seed", "stratified_by", "g_undefined_resamples", "interval"}:
            raise ProjectionError("UFH-13 bootstrap metadata differs from producer contract")
        if type(bootstrap["resamples"]) is not int or bootstrap["resamples"] < 1 or \
                type(bootstrap["seed"]) is not int or bootstrap["seed"] < 0 or \
                type(bootstrap["g_undefined_resamples"]) is not int or \
                bootstrap["g_undefined_resamples"] < 0 or \
                not isinstance(bootstrap["stratified_by"], list) or \
                not all(isinstance(item, str) and item for item in bootstrap["stratified_by"]) or \
                bootstrap["interval"] != "percentile":
            raise ProjectionError("UFH-13 bootstrap metadata is malformed")
    expected_id = f"ufh13:{run_id}:{arm or 'rule'}:{metric}"
    if row.get("measurement_id") != expected_id:
        raise ProjectionError("UFH-13 measurement_id does not rederive from its native fields")


def _load_unit(sidecar: Path) -> tuple[dict[str, Any], str, str, tuple[dict[str, Any], ...]]:
    if sidecar.name != SIDECAR:
        raise ProjectionError(f"UFH-13 source must be named {SIDECAR}")
    parsed_rows: list[dict[str, Any]] = []
    raw = _stable_bytes(sidecar, "belief_measurements.jsonl")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ProjectionError(f"UFH-13 sidecar is not UTF-8: {exc}") from exc
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        value = _json_value(line.encode("utf-8"), f"sidecar line {line_number}")
        if not isinstance(value, dict):
            raise ProjectionError(f"UFH-13 sidecar line {line_number} must be an object")
        if set(value) != _ROW_FIELDS or value.get("schema") != SCHEMA or \
                value.get("source_kind") != SOURCE_KIND:
            raise ProjectionError(f"UFH-13 sidecar line {line_number} has an unsupported row shape")
        parsed_rows.append(value)
    if not parsed_rows:
        return {}, "", "", ()

    manifest, research_commit = _manifest(sidecar)
    run_id = manifest["run_id"]
    suite_sha256 = manifest["suite_sha256"]
    manifest_prereg = manifest.get("preregistration_sha256")
    if manifest_prereg is not None:
        _sha256(manifest_prereg, "manifest preregistration_sha256")
    records_path = sidecar.parent / RECORDS
    try:
        resolved_records = str(records_path.resolve(strict=True))
    except (OSError, RuntimeError) as exc:
        raise ProjectionError(f"UFH-13 sibling records.jsonl cannot be resolved: {exc}") from exc
    records_sha256 = _records_sha256(records_path)
    expected_locator = f"run_id={run_id};suite_sha256={suite_sha256};records={RECORDS}"
    ids: set[str] = set()
    first_identity: tuple[Any, ...] | None = None
    for row in parsed_rows:
        _metric_contract(row, run_id)
        extra = row["extra"]
        identity = (row["date"], row["reps"], extra["verdict"], extra["rule"],
                    extra["preregistration_sha256"])
        if first_identity is None:
            first_identity = identity
        elif identity != first_identity:
            raise ProjectionError("UFH-13 sidecar rows disagree on native run-level identity")
        if "preregistration_sha256" in manifest and \
                extra["preregistration_sha256"] != manifest_prereg:
            raise ProjectionError("UFH-13 row preregistration differs from its manifest")
        if extra["suite_sha256"] != suite_sha256:
            raise ProjectionError("UFH-13 row suite identity differs from its manifest")
        if row["attestation_path"] != resolved_records:
            raise ProjectionError("UFH-13 row attestation path is not the sibling records.jsonl")
        digest = _sha256(row["attestation_sha256"], "row attestation_sha256")
        if digest != records_sha256:
            raise ProjectionError("UFH-13 records.jsonl bytes do not match native attestation_sha256")
        if row["attestation_locator"] != expected_locator:
            raise ProjectionError("UFH-13 attestation locator does not bind native run and suite")
        if row["measurement_id"] in ids:
            raise ProjectionError("UFH-13 sidecar repeats a measurement_id")
        ids.add(row["measurement_id"])
    return manifest, research_commit, records_sha256, tuple(parsed_rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict[str, Any], ...]:
    """Return all native rows in a verified sidecar, or refuse the complete unit."""
    path = Path(sidecar_path)
    if path.name != SIDECAR:
        return ()
    _, research_commit, records_sha256, rows = _load_unit(path)
    if not rows:
        return ()
    records_path = path.parent / RECORDS
    return tuple({"row": row, "sidecar_path": str(path),
                  "records_path": str(records_path), "research_commit": research_commit,
                  "records_sha256": records_sha256} for row in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Project one verified native row without creating fields or assigning a grade."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("UFH-13 native row is missing")
    row = native["row"]
    sidecar_path = Path(native.get("sidecar_path", ""))
    expected_commit = native.get("research_commit")
    if not isinstance(expected_commit, str) or not _HEX40.fullmatch(expected_commit):
        raise ProjectionError("UFH-13 native research_commit is missing or malformed")
    _, current_commit, digest, current_rows = _load_unit(sidecar_path)
    if current_commit != expected_commit or row not in current_rows or \
            digest != native.get("records_sha256"):
        raise ProjectionError("UFH-13 native row or source identity changed after validation")
    extra = row["extra"]
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=row["claim"],
        metric_direction=row["metric_direction"], protocol_id=row["protocol_id"],
        reps=row["reps"], reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_path=row["attestation_path"],
        attestation_sha256=row["attestation_sha256"],
        attestation_locator=row["attestation_locator"], attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND,
        # This is the fixed classification of this adapter/source kind, per the
        # canonical VB-THESIS-1 contract; it is not asserted as a run measurement.
        extra={"schema": SCHEMA, "instrument_class": "serving",
               "research_commit": expected_commit,
               "run_id": extra["run_id"], "suite_sha256": extra["suite_sha256"],
               "preregistration_sha256": extra["preregistration_sha256"],
               "verdict": extra["verdict"], "rule": extra["rule"],
               "arm": extra["arm"],
               **{key: extra[key] for key in extra if key not in _COMMON_EXTRA}},
    )

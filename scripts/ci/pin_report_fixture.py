"""Prospective strict pin-report attachment; reuse the existing CI verifier class.

The projected value remains fixture_execution_conformant. A well-formed report,
including complete=True with stale rows, is never a pin-health or readiness claim.
"""
from __future__ import annotations
import collections
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

SCHEMA = "epyc.benchmark_pin_staleness.v1"
STABILITY_SCOPE = ("observed Git HEAD/status snapshots and per-file safe reads; "
                   "not an atomic whole-checkout snapshot or proof of loaded code bytes")
MAX_BYTES = 16 * 1024 * 1024
STATUSES = {"current", "stale", "missing", "unresolved"}
FIELDS = {"schema", "root", "tracked_python_files", "rows", "counts",
          "source_file_identities", "checker_source", "root_git",
          "stability_scope", "complete"}


def _natural(value):
    return type(value) is int and value >= 0


def _digest(value, size=64):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % size, value) is not None


def _identity(value):
    if not isinstance(value, dict) or not isinstance(value.get("path"), str):
        raise ValueError("invalid source identity")
    if value.get("status") == "read":
        if set(value) != {"path", "status", "bytes", "sha256"} or not _natural(value["bytes"]) or not _digest(value["sha256"]):
            raise ValueError("invalid safely-read source identity")
    elif value.get("status") in {"missing", "unresolved"}:
        if set(value) != {"path", "status", "reason"} or not isinstance(value["reason"], str) or not value["reason"]:
            raise ValueError("invalid unresolved source identity")
    else:
        raise ValueError("unknown source identity status")


def _git(value):
    if not isinstance(value, dict) or type(value.get("available")) is not bool:
        raise ValueError("invalid Git snapshot")
    if value["available"]:
        if set(value) != {"available", "head", "tracked_dirty", "tracked_change_count", "tracked_status_sha256"} or not _digest(value["head"], 40) or type(value["tracked_dirty"]) is not bool or not _natural(value["tracked_change_count"]) or not _digest(value["tracked_status_sha256"]):
            raise ValueError("invalid available Git snapshot")
        if value["tracked_dirty"] is not (value["tracked_change_count"] > 0) or (value["tracked_change_count"] == 0 and value["tracked_status_sha256"] != hashlib.sha256(b"").hexdigest()):
            raise ValueError("Git tracked status metadata differs")
    elif set(value) != {"available", "head", "tracked_dirty", "tracked_change_count", "reason"} or any(value[key] is not None for key in ("head", "tracked_dirty", "tracked_change_count")) or not isinstance(value["reason"], str):
        raise ValueError("invalid unavailable Git snapshot")


def validate_report(report):
    if not isinstance(report, dict) or set(report) != FIELDS or report.get("schema") != SCHEMA:
        raise ValueError("pin report fields/schema differ")
    if not isinstance(report["root"], str) or not Path(report["root"]).is_absolute() or report["stability_scope"] != STABILITY_SCOPE:
        raise ValueError("report root/stability scope absent")
    if not _natural(report["tracked_python_files"]) or not isinstance(report["rows"], list) or not isinstance(report["source_file_identities"], list) or type(report["complete"]) is not bool:
        raise ValueError("invalid report cardinality/complete type")
    sources = report["source_file_identities"]
    if len(sources) != report["tracked_python_files"]:
        raise ValueError("tracked source count differs")
    paths = []
    for identity in sources:
        _identity(identity)
        path = PurePosixPath(identity["path"])
        if path.is_absolute() or ".." in path.parts or path.parts[:2] != ("scripts", "benchmark") or path.suffix != ".py" or path.as_posix() != identity["path"]:
            raise ValueError("source identity escaped benchmark scope")
        paths.append(identity["path"])
    if len(set(paths)) != len(paths) or paths != sorted(paths):
        raise ValueError("source identity paths duplicate or unordered")
    counted = collections.Counter()
    allowed_row = {"source", "line", "status", "reason", "identity_api", "pin",
                   "path_expression", "path", "expected_sha256", "actual_sha256"}
    for row in report["rows"]:
        if not isinstance(row, dict) or not {"source", "line", "status"} <= set(row) or set(row) - allowed_row or row["status"] not in STATUSES or not isinstance(row["source"], str) or not _natural(row["line"]):
            raise ValueError("invalid pin row")
        if row["source"] == "<repository>" and not (row["line"] == 0 and row["status"] == "unresolved" and row.get("reason")):
            raise ValueError("repository metadata row differs")
        checker_metadata_row = (row["source"] == "scripts/benchmark/check_pin_staleness.py"
                                and row["line"] == 0 and row["status"] == "unresolved")
        if row["source"] != "<repository>" and row["source"] not in paths and not checker_metadata_row:
            raise ValueError("pin row source absent from tracked source inventory")
        for key in set(row) - {"line"}:
            if not isinstance(row[key], str):
                raise ValueError("invalid pin row string field")
        for key in ("expected_sha256", "actual_sha256"):
            if key in row and not _digest(row[key]):
                raise ValueError("invalid pin row digest")
        if row["status"] in {"current", "stale"}:
            if not {"path", "expected_sha256", "actual_sha256"} <= set(row) or (row["expected_sha256"] == row["actual_sha256"]) != (row["status"] == "current"):
                raise ValueError("pin row current/stale comparison differs")
        elif not row.get("reason"):
            raise ValueError("missing/unresolved row lacks reason")
        counted[row["status"]] += 1
    for identity in sources:
        if identity["status"] != "read" and not any(row["source"] == identity["path"]
                and row["line"] == 1 and row["status"] == identity["status"]
                and row.get("reason") == identity["reason"] for row in report["rows"]):
            raise ValueError("unread source identity lacks original scan refusal row")
    counts = report["counts"]
    if not isinstance(counts, dict) or set(counts) != STATUSES or any(not _natural(value) for value in counts.values()) or counts != {key: counted[key] for key in STATUSES}:
        raise ValueError("pin row counts differ")
    checker = report["checker_source"]
    if not isinstance(checker, dict) or set(checker) != {"before", "after", "stable", "matches_scanned_copy"} or type(checker["stable"]) is not bool or checker["matches_scanned_copy"] is not None and type(checker["matches_scanned_copy"]) is not bool:
        raise ValueError("invalid checker-source fields")
    _identity(checker["before"])
    _identity(checker["after"])
    if any(checker[key]["path"] != "check_pin_staleness.py" for key in ("before", "after")):
        raise ValueError("checker-source filename differs")
    stable_checker = all(checker[key]["status"] == "read" for key in ("before", "after")) and checker["before"].get("sha256") == checker["after"].get("sha256") and checker["before"].get("bytes") == checker["after"].get("bytes")
    scanned = next((row for row in sources if row["path"] == "scripts/benchmark/check_pin_staleness.py"), None)
    matches = None
    if scanned and scanned["status"] == "read" and checker["before"]["status"] == "read":
        matches = checker["before"]["sha256"] == scanned["sha256"] and checker["after"].get("sha256") == scanned["sha256"]
    if checker["stable"] is not stable_checker or checker["matches_scanned_copy"] is not matches:
        raise ValueError("checker-source consistency differs")
    git = report["root_git"]
    if not isinstance(git, dict) or set(git) != {"before", "after", "stable"} or type(git["stable"]) is not bool:
        raise ValueError("invalid Git consistency fields")
    _git(git["before"])
    _git(git["after"])
    stable_git = git["before"]["available"] and git["after"]["available"] and all(git["before"][key] == git["after"][key] for key in ("head", "tracked_dirty", "tracked_change_count", "tracked_status_sha256"))
    if git["stable"] is not stable_git:
        raise ValueError("Git consistency differs")
    complete = counts["unresolved"] == 0 and counts["missing"] == 0 and stable_git and stable_checker and matches is True
    if report["complete"] is not complete:
        raise ValueError("coverage-complete meaning differs")
    return report


def _parent(root, relative):
    relative = PurePosixPath(relative)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("report path must be explicit and contained")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, relative.name
    except BaseException:
        os.close(fd)
        raise


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate report JSON key")
        result[key] = value
    return result


def write_report(root, relative, report):
    data = (json.dumps(validate_report(report), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    if len(data) > MAX_BYTES:
        raise ValueError("report exceeds bounded size")
    parent, leaf = _parent(root, relative)
    try:
        fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        identity = os.fstat(fd)
        try:
            with os.fdopen(fd, "wb") as handle:
                if handle.write(data) != len(data):
                    raise OSError("short report write")
                handle.flush()
                os.fsync(handle.fileno())
            os.fsync(parent)
        except BaseException:
            # Retry is safe only after removing this call's exclusive inode.
            # A concurrently replaced name belongs to somebody else: refuse cleanup.
            current = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                raise RuntimeError("failed report write lost exclusive output ownership")
            try:
                os.unlink(leaf, dir_fd=parent)
                os.fsync(parent)
            except OSError as cleanup_error:
                raise RuntimeError("failed report write could not durably remove owned output") from cleanup_error
            raise
    finally:
        os.close(parent)
    return {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_report(root, relative, expected_sha256):
    if not _digest(expected_sha256):
        raise ValueError("original report digest required")
    parent, leaf = _parent(root, relative)
    try:
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError("report is not regular")
            data = handle.read(MAX_BYTES + 1)
    finally:
        os.close(parent)
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("original report bytes/digest differ")
    report = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    return validate_report(report)


def capture_report_fixture(*, report_relative, **native_recipe):
    """Declare a fresh generated report before the existing native process launch."""
    from scripts.ci.native_conformance import capture_fixture_execution
    if "generated_output_paths" in native_recipe:
        raise ValueError("report output declaration is owned by this writer")
    return capture_fixture_execution(generated_output_paths=[report_relative], **native_recipe)


def read_report_fixture(receipt_path, report_relative):
    from scripts.ci.native_conformance import read_receipt
    record, digest = read_receipt(receipt_path)
    outputs = [row for row in record.get("generated_outputs", []) if row["path"] == report_relative]
    if len(outputs) != 1:
        raise ValueError("original native report attachment absent or duplicated")
    artifact = outputs[0]["artifact"]
    report = read_report(Path(receipt_path).parent, artifact["name"], artifact["sha256"])
    return record, digest, report


def project_report_fixture(receipt_path, report_relative):
    """Return the existing native projection; never author a report-health tuple."""
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    record, digest, report = read_report_fixture(receipt_path, report_relative)
    rows = native_rows(receipt_path)
    if not rows:
        return (), report
    if len(rows) != 1 or rows[0]["record"] != record or rows[0]["receipt_sha256"] != digest:
        raise ValueError("native report/receipt changed during strict reopen")
    return (project_ci_conformance(rows[0]),), report

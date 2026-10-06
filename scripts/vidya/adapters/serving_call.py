"""Strict reader for native per-call ``serving_call.v1`` JSONL records.

This adapter preserves each writer record and projects only explicitly captured
per-call timing observations. Rows with ``timings_source == "absent"`` remain
available as native/join metadata but emit no metric tuples (including queue wait).
Window aggregation is outside this adapter.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.serving_call/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "orchestrator-serving-call"
SCHEMA = "epyc.orchestrator.serving_call.v1"
JUDGE_SCHEMA = "epyc.orchestrator.coherence_judge_call.v1"
_APP_LOG_DIR = Path(os.environ.get(
    "ORCHESTRATOR_PATHS_LOG_DIR", "/mnt/raid0/llm/epyc-orchestrator/logs"))
DEFAULT_DIR = _APP_LOG_DIR / "serving_calls"
DEFAULT_JUDGE_LOG = _APP_LOG_DIR / "coherence_judge" / "calls.jsonl"

# These are per-call metrics. Direction is explicit and fixed here from the
# serving-call contract: latency/wait lower; throughput and draft acceptance
# higher. A cache token count remains in native metadata but has no improvement
# direction by itself, so it is not projected as a claim.
_METRICS: dict[str, tuple[str, str]] = {
    "prompt_ms": ("ms", "lower_better"),
    "predicted_ms": ("ms", "lower_better"),
    "prompt_per_second": ("tokens/s", "higher_better"),
    "predicted_per_second": ("tokens/s", "higher_better"),
    "draft_acceptance_rate": ("fraction", "higher_better"),
    "pre_dispatch_wait_ms": ("ms", "lower_better"),
}
_ROTATED = re.compile(r"^serving_calls\.jsonl(?:\.([1-9][0-9]*))?$")


def _stable_bytes(path: Path) -> bytes:
    """Read one immutable snapshot or refuse if append/rotation raced the read."""
    path = Path(path)
    if path.is_symlink():
        raise ProjectionError(f"serving-call source is a symlink: {path}")
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ProjectionError(f"serving-call source is not a regular file: {path}")
            raw = handle.read()
            after = os.fstat(handle.fileno())
        current = path.stat()
    except ProjectionError:
        raise
    except OSError as exc:
        raise ProjectionError(f"serving-call source unreadable: {path}: {exc}") from exc
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) !=
            (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) or
            len(raw) != after.st_size):
        raise ProjectionError(f"serving-call source changed during read: {path}")
    return raw


def discover(paths: str | Path | Iterable[str | Path] | None = None) -> tuple[Path, ...]:
    """Resolve exact current/rotated JSONL paths, excluding lock files."""
    custom_bases: set[tuple[Path, str]] = set()
    if paths is None:
        override = os.environ.get("ORCHESTRATOR_SERVING_CALLS_LOG", "").strip()
        if override.lower() in {"off", "0", "none", "false", "disabled"}:
            candidates = []
        elif override:
            override_path = Path(override)
            candidates = [override_path, *override_path.parent.glob(override_path.name + ".*")]
            custom_bases.add((override_path.parent, override_path.name))
        else:
            candidates = sorted(DEFAULT_DIR.glob("serving_calls.jsonl*"))
    elif isinstance(paths, (str, Path)):
        candidate = Path(paths)
        if candidate.is_dir():
            candidates = sorted(candidate.glob("serving_calls.jsonl*"))
        else:
            candidates = [candidate]
            match = re.fullmatch(r"(.+)\.([1-9][0-9]*)", candidate.name)
            base = match.group(1) if match else candidate.name
            custom_bases.add((candidate.parent, base))
    else:
        candidates = [Path(p) for p in paths]
        for candidate in candidates:
            match = re.fullmatch(r"(.+)\.([1-9][0-9]*)", candidate.name)
            base = match.group(1) if match else candidate.name
            custom_bases.add((candidate.parent, base))
    result = []
    for path in candidates:
        if path.name.endswith(".lock"):
            continue
        custom_name = any(
            path.parent == parent and (path.name == base or
                re.fullmatch(re.escape(base) + r"\.[1-9][0-9]*", path.name))
            for parent, base in custom_bases
        )
        if not _ROTATED.fullmatch(path.name) and not custom_name:
            raise ProjectionError(f"unexpected serving-call source name: {path}")
        if not path.exists():
            continue
        result.append(path)
    # Unrotated file first, then oldest numeric rotation to newest.
    return tuple(sorted(result, key=lambda p: (int(p.suffix[1:]) if p.suffix[1:].isdigit() else 0,
                                                p.name)))


def _canonical_record_digest(record: Mapping[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    try:
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"serving-call record is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def read_records(paths: str | Path | Iterable[str | Path] | None = None) -> tuple[dict[str, Any], ...]:
    """Read self-hashed records while preserving exact source bytes and locators.

    All source files are snapshotted before a row is returned. One bad nonempty
    line refuses the complete input rather than yielding a partial history.
    This returns native metadata even for ``timings_source=absent`` rows.
    """
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in discover(paths):
        raw = _stable_bytes(path)
        file_sha = hashlib.sha256(raw).hexdigest()
        try:
            lines = raw.splitlines(keepends=True)
            text_lines = [line.decode("utf-8", errors="strict") for line in lines]
        except UnicodeDecodeError as exc:
            raise ProjectionError(f"serving-call file is not UTF-8: {path}: {exc}") from exc
        for line_number, (line, text) in enumerate(zip(lines, text_lines), 1):
            if not text.strip():
                continue
            try:
                record = json.loads(text)
            except ValueError as exc:
                raise ProjectionError(f"invalid serving-call JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ProjectionError(f"serving-call row must be an object at {path}:{line_number}")
            if record.get("schema") != SCHEMA:
                raise ProjectionError(f"wrong serving-call schema at {path}:{line_number}")
            if record.get("timings_source") not in ("server", "absent"):
                raise ProjectionError(f"invalid serving-call timings_source at {path}:{line_number}")
            record_id = record.get("record_id")
            if not isinstance(record_id, str) or not record_id.strip():
                raise ProjectionError(f"missing serving-call record_id at {path}:{line_number}")
            if record_id in seen_ids:
                raise ProjectionError(f"duplicate serving-call record_id: {record_id}")
            seen_ids.add(record_id)
            expected = record.get("record_sha256")
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ProjectionError(f"invalid serving-call record_sha256 at {path}:{line_number}")
            if _canonical_record_digest(record) != expected:
                raise ProjectionError(f"serving-call record hash mismatch at {path}:{line_number}")
            rows.append({
                "record": record,
                "record_id": record_id,
                "record_sha256": expected,
                "source_path": str(path.resolve()),
                "source_file_sha256": file_sha,
                "source_line": line_number,
                "source_line_sha256": hashlib.sha256(line).hexdigest(),
                "source_line_bytes": line,
            })
    return tuple(rows)


def native_rows(paths: str | Path | Iterable[str | Path] | None = None) -> tuple[dict[str, Any], ...]:
    """Expand valid timed calls to one registry input per explicit metric.

    Absent-timing rows are excluded from ClaimTuple projection entirely, while
    ``read_records`` remains available to correlation consumers.
    """
    expanded = []
    for native in read_records(paths):
        record = native["record"]
        if record.get("timings_source") == "absent":
            continue
        _validated_objects(record)
        timings = record.get("timings")
        if not isinstance(timings, Mapping):
            raise ProjectionError("server timing row has no timings object")
        metrics = [name for name in ("prompt_ms", "predicted_ms", "prompt_per_second",
                                     "predicted_per_second")
                   if timings.get(name) is not None]
        for name in ("prompt_ms", "predicted_ms", "prompt_per_second", "predicted_per_second"):
            if timings.get(name) is not None:
                value = _finite_number(timings[name], name)
                if value < 0:
                    raise ProjectionError(f"serving-call {name} cannot be negative")
        cache_n = timings.get("cache_n")
        if cache_n is not None and (
                isinstance(cache_n, bool) or not isinstance(cache_n, int) or cache_n < 0):
            raise ProjectionError("serving-call cache_n must be a nonnegative integer count")
        draft_n, accepted_n = timings.get("draft_n"), timings.get("draft_n_accepted")
        if draft_n is not None or accepted_n is not None:
            if (isinstance(draft_n, bool) or not isinstance(draft_n, int) or draft_n < 0 or
                    isinstance(accepted_n, bool) or not isinstance(accepted_n, int) or accepted_n < 0 or
                    accepted_n > draft_n):
                raise ProjectionError("draft_n and draft_n_accepted must be valid nonnegative integers")
            if draft_n > 0:
                metrics.append("draft_acceptance_rate")
        queue = record.get("queue")
        if not isinstance(queue, Mapping):
            raise ProjectionError("serving-call queue must be an object")
        if queue.get("pre_dispatch_wait_ms") is not None:
            wait = _finite_number(queue["pre_dispatch_wait_ms"], "queue.pre_dispatch_wait_ms")
            if wait < 0:
                raise ProjectionError("serving-call queue.pre_dispatch_wait_ms cannot be negative")
            metrics.append("pre_dispatch_wait_ms")
        for metric in metrics:
            expanded.append({**native, "metric_field": metric})
    return tuple(expanded)


def read_judge_rows(path: str | Path | None = None) -> tuple[dict[str, Any], ...]:
    """Read typed-judge rows as correlation metadata; producer has no row self-hash."""
    if path is None:
        override = os.environ.get("ORCHESTRATOR_COHERENCE_JUDGE_LOG", "").strip()
        if override.lower() in {"off", "0", "none", "false", "disabled", "no"}:
            return ()
        path = Path(override) if override else DEFAULT_JUDGE_LOG
    target = Path(path)
    if not target.exists():
        return ()
    raw = _stable_bytes(target)
    file_sha = hashlib.sha256(raw).hexdigest()
    result = []
    seen: set[str] = set()
    try:
        lines = raw.splitlines(keepends=True)
        decoded = [line.decode("utf-8", errors="strict") for line in lines]
    except UnicodeDecodeError as exc:
        raise ProjectionError(f"judge-call file is not UTF-8: {target}: {exc}") from exc
    for number, (line, text) in enumerate(zip(lines, decoded), 1):
        if not text.strip():
            continue
        try:
            record = json.loads(text)
        except ValueError as exc:
            raise ProjectionError(f"invalid judge-call JSON at {target}:{number}: {exc}") from exc
        if not isinstance(record, dict) or record.get("schema") != JUDGE_SCHEMA:
            raise ProjectionError(f"wrong judge-call schema at {target}:{number}")
        call_id = record.get("call_id")
        if not isinstance(call_id, str) or not call_id.strip():
            raise ProjectionError(f"missing judge call_id at {target}:{number}")
        if call_id in seen:
            raise ProjectionError(f"duplicate judge call_id: {call_id}")
        seen.add(call_id)
        result.append({"record": record, "call_id": call_id, "source_path": str(target.resolve()),
                       "source_file_sha256": file_sha, "source_line": number,
                       "source_line_sha256": hashlib.sha256(line).hexdigest(),
                       "source_line_bytes": line, "self_hash": None})
    return tuple(result)


def correlate(judge_rows: Iterable[Mapping[str, Any]],
              serving_rows: Iterable[Mapping[str, Any]]) -> dict[str, tuple[dict[str, Any], ...]]:
    """Join judge call IDs to native parent IDs, retaining one row per backend attempt."""
    judges: dict[str, Mapping[str, Any]] = {}
    for item in judge_rows:
        record = item.get("record", item)
        if not isinstance(record, Mapping) or record.get("schema") != JUDGE_SCHEMA:
            raise ProjectionError("wrong judge-call schema in correlation input")
        call_id = record.get("call_id")
        if not isinstance(call_id, str) or not call_id:
            raise ProjectionError("judge correlation row has no call_id")
        if call_id in judges:
            raise ProjectionError(f"duplicate judge call_id: {call_id}")
        judges[call_id] = item
    matched: list[dict[str, Any]] = []
    unmatched_server: list[dict[str, Any]] = []
    hit: set[str] = set()
    seen_record_ids: set[str] = set()
    for item in serving_rows:
        record = item.get("record", item)
        if not isinstance(record, Mapping) or record.get("schema") != SCHEMA:
            raise ProjectionError("wrong serving-call schema in correlation input")
        if _canonical_record_digest(record) != record.get("record_sha256"):
            raise ProjectionError("serving-call record hash mismatch in correlation input")
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise ProjectionError("serving-call correlation row has no record_id")
        if record_id in seen_record_ids:
            raise ProjectionError(f"duplicate serving-call record_id: {record_id}")
        seen_record_ids.add(record_id)
        caller = record.get("caller")
        if not isinstance(caller, Mapping):
            raise ProjectionError("serving-call caller must be an object")
        parent_id = caller.get("parent_request_id")
        task_id = caller.get("task_id")
        judge = judges.get(parent_id) if isinstance(parent_id, str) else None
        if judge is not None and task_id in (None, "coherence_judge"):
            matched.append({"serving": item, "judge": judge,
                            "join_key": parent_id, "join_status": "matched"})
            hit.add(parent_id)
        else:
            unmatched_server.append({"serving": item, "judge": None,
                                     "join_key": parent_id if isinstance(parent_id, str) else None,
                                     "join_status": "unmatched"})
    unmatched_judge = tuple(dict(item) for call_id, item in judges.items() if call_id not in hit)
    return {"matched": tuple(matched), "unmatched_server": tuple(unmatched_server),
            "unmatched_judge": unmatched_judge}


def joined_rows(serving_paths=None, judge_path=None) -> dict[str, tuple[dict[str, Any], ...]]:
    """Snapshot and correlate both native logs without projecting judge claims."""
    return correlate(read_judge_rows(judge_path), read_records(serving_paths))


def _finite_number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProjectionError(f"serving-call {field} must be a finite number")
    return value



def _validated_objects(
    record: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], bool]:
    """Validate native block shapes and report whether server identity is scoped."""
    blocks = {}
    for key in ("server", "caller", "queue", "provenance"):
        value = record.get(key)
        if not isinstance(value, Mapping):
            raise ProjectionError(f"serving-call {key} must be an object")
        blocks[key] = value
    source = blocks["server"].get("identity_source")
    if source not in ("absent", "unreadable", "stack_sidecar"):
        raise ProjectionError("serving-call server.identity_source is missing or unknown")
    scoped = False
    if source == "stack_sidecar":
        identity = blocks["server"]
        argv = identity.get("argv_sha256")
        binary = identity.get("binary_realpath")
        model = identity.get("model_path")
        scoped = (isinstance(argv, str) and re.fullmatch(r"[0-9a-f]{64}", argv) is not None
                  and isinstance(binary, str) and bool(binary.strip())
                  and isinstance(model, str) and bool(model.strip()))
    return (blocks["server"], blocks["caller"], blocks["queue"],
            blocks["provenance"], not scoped)


def _date(record: Mapping[str, Any]) -> str:
    timestamp = record.get("ts_start")
    if not isinstance(timestamp, str):
        raise ProjectionError("serving-call ts_start is missing")
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise ProjectionError("serving-call ts_start is invalid") from exc


def project_record(native: Mapping[str, Any]) -> tuple[ClaimTuple, ...]:
    """Project one verified native row to zero or more per-call timing tuples."""
    if not isinstance(native, Mapping) or not isinstance(native.get("record"), Mapping):
        raise ProjectionError("serving-call native row is malformed")
    record = native["record"]
    if record.get("schema") != SCHEMA:
        raise ProjectionError("not a serving_call.v1 row")
    if _canonical_record_digest(record) != record.get("record_sha256"):
        raise ProjectionError("serving-call record hash mismatch")
    if native.get("metric_field"):
        return (project(native),)
    # Useful for direct callers/tests; registry ingestion uses one metric per row.
    if record.get("timings_source") == "absent":
        return ()
    candidates = []
    timings = record.get("timings")
    if not isinstance(timings, Mapping):
        raise ProjectionError("server timing row has no timings object")
    candidates.extend(name for name in ("prompt_ms", "predicted_ms", "prompt_per_second",
                                        "predicted_per_second")
                      if timings.get(name) is not None)
    draft_n, accepted_n = timings.get("draft_n"), timings.get("draft_n_accepted")
    if draft_n is not None or accepted_n is not None:
        if (isinstance(draft_n, bool) or not isinstance(draft_n, int) or draft_n < 0 or
                isinstance(accepted_n, bool) or not isinstance(accepted_n, int) or accepted_n < 0 or
                accepted_n > draft_n):
            raise ProjectionError("draft_n and draft_n_accepted must be valid nonnegative integers")
        if draft_n > 0:
            candidates.append("draft_acceptance_rate")
    queue = record.get("queue")
    if not isinstance(queue, Mapping):
        raise ProjectionError("serving-call queue must be an object")
    if queue.get("pre_dispatch_wait_ms") is not None:
        candidates.append("pre_dispatch_wait_ms")
    return tuple(project({**native, "metric_field": metric}) for metric in candidates)


@register("serving_call")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one explicitly selected native metric through the shared grader."""
    if not isinstance(native, Mapping) or not isinstance(native.get("record"), Mapping):
        raise ProjectionError("serving-call projection input must be a mapping")
    record = native["record"]
    if record.get("schema") != SCHEMA:
        raise ProjectionError("not a serving_call.v1 row")
    if _canonical_record_digest(record) != record.get("record_sha256"):
        raise ProjectionError("serving-call record hash mismatch")
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        raise ProjectionError("serving-call record_id is missing")
    if record.get("timings_source") == "absent":
        raise ProjectionError("timings_source=absent rows have no ClaimTuple projections")
    if record.get("timings_source") != "server":
        raise ProjectionError("serving-call timings_source is neither server nor absent")
    timings = record.get("timings")
    if not isinstance(timings, Mapping):
        raise ProjectionError("server timing row has no timings object")
    metric_field = native.get("metric_field")
    if not isinstance(metric_field, str) or metric_field not in _METRICS:
        raise ProjectionError(f"unknown serving-call metric {metric_field!r}")
    source_field = metric_field
    if metric_field == "draft_acceptance_rate":
        draft_n, accepted_n = timings.get("draft_n"), timings.get("draft_n_accepted")
        if (isinstance(draft_n, bool) or not isinstance(draft_n, int) or draft_n <= 0 or
                isinstance(accepted_n, bool) or not isinstance(accepted_n, int) or
                accepted_n < 0 or accepted_n > draft_n):
            raise ProjectionError("draft_n and draft_n_accepted must define a valid fraction")
        value = accepted_n / draft_n
        source_field = "draft_n_accepted/draft_n"
    elif metric_field == "pre_dispatch_wait_ms":
        queue = record.get("queue")
        if not isinstance(queue, Mapping) or "pre_dispatch_wait_ms" not in queue:
            raise ProjectionError("pre_dispatch_wait_ms is absent")
        value = queue["pre_dispatch_wait_ms"]
        source_field = "queue.pre_dispatch_wait_ms"
    else:
        if metric_field not in timings or timings[metric_field] is None:
            raise ProjectionError(f"serving-call timing {metric_field} is absent")
        value = timings[metric_field]
    value = _finite_number(value, source_field)
    if value < 0:
        raise ProjectionError(f"serving-call {source_field} cannot be negative")
    server, caller, queue, provenance, unscoped_identity = _validated_objects(record)
    line = native.get("source_line_bytes")
    line_sha = native.get("source_line_sha256")
    if not isinstance(line, bytes) or not isinstance(line_sha, str) or hashlib.sha256(line).hexdigest() != line_sha:
        raise ProjectionError("serving-call native row lacks matching original line bytes/digest")
    try:
        if json.loads(line.decode("utf-8")) != record:
            raise ProjectionError("serving-call source line does not bind the projected record")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProjectionError("serving-call source line is not valid JSON") from exc
    unit, direction = _METRICS[metric_field]
    identity = {
        "record_id": record_id,
        "record_sha256": record.get("record_sha256"),
        "source_path": native.get("source_path"),
        "source_file_sha256": native.get("source_file_sha256"),
        "source_line": native.get("source_line"),
        "source_line_sha256": line_sha,
        "metric_source_field": source_field,
        "caller": dict(caller),
        "server": dict(server),
        "provenance": dict(provenance),
        "timings_source": record.get("timings_source"),
        "queue": dict(queue),
        "unscoped_server_identity": unscoped_identity,
        "judge_parent_request_id": caller.get("parent_request_id"),
        "judge_child_request_id": caller.get("request_id"),
    }
    claim = f"Native serving-call {metric_field}={value} for record {record_id}."
    return ClaimTuple(
        measurement_id=f"serving-call:{record_id}:{metric_field}",
        metric=f"serving_call.{metric_field}", value=value, date=_date(record),
        category="BASELINE", metric_direction=direction, claim=claim,
        unit=unit,
        # Hash the exact record line, not the append-only file that can grow later.
        attestation_sha256=line_sha, attestation_present=True, attestation_verified=True,
        attestation_locator=f"{native.get('source_path')}#line:{native.get('source_line')}:{record_id}",
        source_kind=SOURCE_KIND, protocol_id="", reps=1, reps_basis="native serving records",
        extra={**identity,
               "category_source": "adapter default: native runtime observation, not an A/B arm"},
    )

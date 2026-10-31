"""Strict reader for explicit source-authored request usage declarations.

Unannotated v1 records remain visible as refusals/unknowns. This adapter does not infer a
category, direction, protocol, model identity, or grade; ``ClaimTuple.grade()`` remains the only
grader. Cache replays retain the original backend observation and never emit a second tuple.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.usage_provenance/v1"
AUTHORITY = "measurement"
SCHEMA = "epyc.request_call_usage.v1"
DECLARATION_SCHEMA = "epyc.request_call_usage.measurement_declaration.v1"
SERVING_SCHEMA = "epyc.orchestrator.serving_call.v1"
NATIVE_SOURCES = frozenset({
    "llama_server:/completion.tokens_predicted",
    "llama_server:/completion.stream.tokens_predicted",
    "llama_server:/v1/chat/completions.usage.completion_tokens",
    "llama_server:/v1/chat/completions.stream.usage.completion_tokens",
    "llama_server:/v1/chat/completions.stream.timings.predicted_n",
})
CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
DIRECTIONS = frozenset({"higher_better", "lower_better"})
COUNTERS = {"prompt_tokens": "prompt_tokens", "completion_tokens": "tokens_generated",
            "cached_tokens": "cached_prompt_tokens"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{7,64}$")
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 32768


def _reject(reason: str) -> None:
    raise ProjectionError("usage provenance refused: " + reason)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            _reject("duplicate JSON key")
        result[key] = value
    return result


def _no_constant(value):
    _reject("nonfinite JSON number " + value)


def _read_stable(path: Path) -> tuple[bytes, str]:
    try:
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(path, flags)
    except OSError as exc:
        _reject("native file unavailable: " + type(exc).__name__)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            _reject("native file is not regular or exceeds bounded size")
        chunks = []
        size = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                _reject("native file exceeds bounded size")
            chunks.append(chunk)
        after = os.fstat(fd)
        named = os.lstat(path)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or
                (after.st_dev, after.st_ino) != (named.st_dev, named.st_ino)):
            _reject("native file changed during read")
        raw = b"".join(chunks)
        return raw, hashlib.sha256(raw).hexdigest()
    finally:
        os.close(fd)


def _files(base: Path, rotations: int) -> list[Path]:
    paths = [base, *(base.with_name(base.name + f".{i}") for i in range(1, rotations + 1))]
    return [path for path in paths if path.exists()]


def _read_records(path: Path, rotations: int) -> tuple[list[dict], dict[str, str]]:
    records = []
    file_hashes = {}
    for item in _files(path, rotations):
        raw, digest = _read_stable(item)
        file_hashes[str(item)] = digest
        for number, line in enumerate(raw.splitlines(), start=1):
            if not line:
                continue
            if len(line) > MAX_LINE_BYTES:
                _reject("line exceeds writer bound")
            try:
                record = json.loads(line, object_pairs_hook=_pairs, parse_constant=_no_constant)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                _reject(f"malformed JSON at {item.name}:{number}: {type(exc).__name__}")
            if type(record) is not dict:
                _reject("JSONL row is not an object")
            records.append((record, str(item), number))
    return records, file_hashes


def _digest_record(record: dict) -> str:
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    try:
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        _reject("record cannot be canonicalized: " + type(exc).__name__)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _valid_count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _process_identity(value: Any) -> tuple[int, str, str, str, str] | None:
    if type(value) is not dict:
        return None
    pid = value.get("pid")
    run_id, host, started_at, commit = (value.get(key) for key in
                                       ("run_id", "host", "started_at", "orch_commit"))
    if (type(pid) is not int or pid <= 0 or
            not all(isinstance(field, str) and field.strip()
                    for field in (run_id, host, started_at, commit)) or
            not GIT_SHA.fullmatch(commit)):
        return None
    return pid, run_id, host, started_at, commit


def _verify_file_record(path: Path, expected_file_sha: str, record: dict, *, line: int | None = None) -> None:
    raw, digest = _read_stable(path)
    if digest != expected_file_sha:
        _reject("native file changed after projection")
    matches = []
    for number, encoded in enumerate(raw.splitlines(), start=1):
        if line is not None and number != line:
            continue
        try:
            parsed = json.loads(encoded, object_pairs_hook=_pairs, parse_constant=_no_constant)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            _reject("native record no longer parses: " + type(exc).__name__)
        if parsed == record:
            matches.append(parsed)
    if len(matches) != 1 or record.get("record_sha256") != _digest_record(record):
        _reject("projected native record does not match its self-hashed source line")


def _read_serving(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    records, hashes = _read_records(path, 8)
    by_id = {}
    for record, source_path, _ in records:
        if record.get("schema") != SERVING_SCHEMA or record.get("record_sha256") != _digest_record(record):
            _reject("serving-call schema or self-hash differs")
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id or record_id in by_id:
            _reject("serving record id absent or duplicated across retained log")
        by_id[record_id] = {"record": record, "path": source_path,
                            "file_sha256": hashes[source_path]}
    return by_id, hashes


def _declared_metrics(call: dict) -> list[dict]:
    declaration = call.get("measurement_declaration")
    if declaration is None:
        return []
    if type(declaration) is not dict or declaration.get("schema") != DECLARATION_SCHEMA:
        _reject("measurement declaration missing or unsupported")
    metrics = declaration.get("metrics")
    if type(metrics) is not list or not metrics or len(metrics) > len(COUNTERS):
        _reject("measurement declaration metrics absent or unbounded")
    rows = []
    seen = set()
    for metric in metrics:
        if type(metric) is not dict:
            _reject("measurement declaration metric is not an object")
        field = metric.get("source_field")
        if not isinstance(field, str) or field not in COUNTERS or field in seen:
            _reject("measurement declaration source field absent or duplicated")
        seen.add(field)
        required = {"source_field", "metric", "unit", "category", "metric_direction", "protocol_id", "claim"}
        allowed = required | {"reps_basis", "applicability", "observation"}
        if not required <= set(metric) or set(metric) - allowed:
            _reject("measurement declaration fields differ")
        for name in ("metric", "unit", "claim"):
            value = metric[name]
            if not isinstance(value, str) or not value.strip() or len(value) > 512:
                _reject(f"measurement declaration {name} must be bounded nonempty text")
        if not isinstance(metric["category"], str) or metric["category"] not in CATEGORIES:
            _reject("measurement declaration category is not a ClaimTuple category")
        if (not isinstance(metric["metric_direction"], str) or
                metric["metric_direction"] not in DIRECTIONS):
            _reject("measurement declaration direction is not a ClaimTuple direction")
        if not isinstance(metric["protocol_id"], str) or len(metric["protocol_id"]) > 256:
            _reject("measurement declaration protocol_id must be bounded text; empty stays absent")
        if "reps_basis" in metric and (
                not isinstance(metric["reps_basis"], str) or len(metric["reps_basis"]) > 256):
            _reject("measurement declaration reps_basis must be bounded text")
        for name in ("applicability", "observation"):
            if name in metric and type(metric[name]) is not dict:
                _reject(f"measurement declaration {name} must be an object")
        rows.append(metric)
    return rows


def _events(path: Path) -> tuple[list[dict], dict[str, str], dict[str, dict], dict[str, str]]:
    if path.name != "usage_provenance.jsonl":
        _reject("explicit path must name usage_provenance.jsonl")
    usage, usage_hashes = _read_records(path, 3)
    serving_path = path.with_name("serving_calls.jsonl")
    serving, serving_hashes = _read_serving(serving_path)
    groups: dict[tuple[int, str, str], dict[str, Any]] = {}
    for record, source_path, line_number in usage:
        if record.get("schema") != SCHEMA or record.get("record_sha256") != _digest_record(record):
            _reject(f"usage schema or self-hash differs at {Path(source_path).name}:{line_number}")
        process = record.get("process")
        call = record.get("call")
        if type(process) is not dict or type(call) is not dict:
            _reject("process or call block absent")
        pid, request_id, call_id = process.get("pid"), record.get("request_id"), call.get("call_id")
        if type(pid) is not int or pid <= 0 or not all(isinstance(v, str) and v for v in (request_id, call_id)):
            _reject("process/request/call identity absent")
        key = (pid, request_id, call_id)
        group = groups.setdefault(key, {"begin": None, "settled": None})
        event = record.get("event")
        if event not in {"begin", "settled"} or group[event] is not None:
            _reject("event kind invalid or duplicated for call identity")
        group[event] = record
        group[event + "_path"] = source_path
        group[event + "_line"] = line_number
    return list(groups.values()), usage_hashes, serving, serving_hashes


def native_rows(path) -> list[dict]:
    """Project only fully paired, exact native call records with explicit declarations."""
    path = Path(path)
    groups, usage_hashes, serving, _serving_hashes = _events(path)
    rows = []
    originals = {}
    replay_groups = []
    report = {"unannotated": 0, "pending": 0, "censored_or_error": 0,
              "estimated_or_unknown": 0, "unjoined": 0, "logical_replays": 0,
              "unresolved_replays": 0}
    for group in groups:
        begin, settled = group["begin"], group["settled"]
        record = settled or begin
        if begin is None or settled is None:
            report["pending"] += 1
            continue  # preserved incomplete call: no tuple
        first, final = begin["call"], settled["call"]
        if first.get("measurement_declaration") != final.get("measurement_declaration"):
            _reject("begin/settled measurement declaration differs")
        if any(first.get(k) != final.get(k) for k in ("role", "parent_call_id", "call_id")):
            _reject("begin/settled call identity differs")
        if (_process_identity(begin["process"]) is None or
                _process_identity(begin["process"]) != _process_identity(settled["process"])):
            _reject("begin/settled process identity differs or is incomplete")
        if final.get("pending") is not False or final.get("censored") is not False:
            report["censored_or_error"] += 1
            continue
        if final.get("error_category") or final.get("error_sha256"):
            report["censored_or_error"] += 1
            continue
        provenance = final.get("provenance")
        if provenance == "cached_replay_of_server_reported":
            replay_groups.append((group, settled))
            report["logical_replays"] += 1
            continue
        if provenance != "server_reported" or final.get("source") not in NATIVE_SOURCES:
            report["estimated_or_unknown"] += 1
            continue
        backend_id = final.get("backend_record_id")
        joined = serving.get(backend_id) if isinstance(backend_id, str) else None
        if joined is None:
            report["unjoined"] += 1
            continue
        native = joined["record"]
        if (_process_identity(native.get("provenance")) is None or
                _process_identity(native.get("provenance")) != _process_identity(record["process"])):
            report["unjoined"] += 1
            continue
        caller_request = (native.get("caller") or {}).get("request_id")
        if caller_request != record["request_id"]:
            report["unjoined"] += 1
            continue
        server = native.get("server") or {}
        if (type(server.get("port")) is not int or server["port"] <= 0 or
                not isinstance(server.get("model_path"), str) or not server["model_path"] or
                not isinstance(server.get("launch_id"), str) or not server["launch_id"]):
            report["unjoined"] += 1
            continue
        native_result = native.get("result") or {}
        for field_name, native_name in COUNTERS.items():
            count = final.get(field_name)
            if count is None:
                continue
            if not _valid_count(count) or not _valid_count(native_result.get(native_name)):
                _reject("native usage count is not a nonnegative integer")
            if count != native_result[native_name]:
                _reject("usage count differs from joined physical backend record")
        declarations = _declared_metrics(final)
        if not declarations:
            report["unannotated"] += 1
            continue
        source_context = settled.get("source_context")
        process = settled.get("process") or {}
        if (not isinstance(process.get("orch_commit"), str) or
                not GIT_SHA.fullmatch(process["orch_commit"]) or
                type(source_context) is not dict or
                source_context.get("snapshot_kind") != "on_disk_async_snapshot" or
                source_context.get("loaded_bytes_attestation") != "not_available"):
            report["unjoined"] += 1
            continue
        originals[final["call_id"]] = {"group": group, "record": settled, "native": native,
                                        "joined": joined, "declarations": declarations}
        for metric in declarations:
            field_name = metric["source_field"]
            value = final.get(field_name)
            if value is None:
                continue
            if not _valid_count(value):
                _reject("declared native usage count is not a nonnegative integer")
            rows.append({
                "record": settled, "usage_path": group["settled_path"],
                "usage_line": group["settled_line"], "usage_file_sha256": usage_hashes[group["settled_path"]],
                "serving_path": joined["path"], "serving_file_sha256": joined["file_sha256"],
                "serving_record": native, "metric": metric, "value": value,
                "logical_replays": [], "read_report": report,
                "measurement_id": f"usage:{record['process'].get('run_id')}:{record['request_id']}:{final['call_id']}:{field_name}",
            })
    rows_by_backend = {}
    for row in rows:
        rows_by_backend.setdefault(row["serving_record"]["record_id"], []).append(row)
    for group, settled in replay_groups:
        final = settled["call"]
        original_call_id = final.get("replay_of_call_id")
        original = originals.get(original_call_id) if isinstance(original_call_id, str) else None
        if original is None:
            report["unresolved_replays"] += 1
            continue
        if final.get("measurement_declaration") != original["record"]["call"].get("measurement_declaration"):
            report["unresolved_replays"] += 1
            continue
        if final.get("source") != "content_cache":
            report["unresolved_replays"] += 1
            continue
        if any(final.get(field_name) != original["record"]["call"].get(field_name)
               for field_name in COUNTERS):
            report["unresolved_replays"] += 1
            continue
        backend_id = original["record"]["call"].get("backend_record_id")
        refs = {"request_id": settled["request_id"], "call_id": final["call_id"],
                "parent_call_id": final.get("parent_call_id"), "replay_of_call_id": original_call_id,
                "backend_record_id": backend_id}
        for row in rows_by_backend.get(backend_id, []):
            row["logical_replays"].append(refs)
    if not rows:
        _reject("no projectable calls; explicit measurement declaration, complete native usage, "
                "source snapshot and backend/server joins are required (unannotated=" +
                str(report["unannotated"]) + ", pending=" + str(report["pending"]) +
                ", censored=" + str(report["censored_or_error"]) + ", unjoined=" + str(report["unjoined"]) + ")")
    return rows


@register("usage-provenance")
def project(native: dict) -> ClaimTuple:
    if type(native) is not dict or set(native) != {
        "record", "usage_path", "usage_line", "usage_file_sha256", "serving_file_sha256",
        "serving_record", "serving_path", "metric", "value", "logical_replays", "read_report", "measurement_id",
    }:
        _reject("projection row shape differs")
    if type(native["usage_line"]) is not int or native["usage_line"] <= 0:
        _reject("usage source line is invalid")
    metric = native["metric"]
    if type(metric) is not dict:
        _reject("metric declaration absent")
    record = native["record"]
    call = record["call"]
    declaration = call.get("measurement_declaration")
    if type(declaration) is not dict or declaration.get("schema") != DECLARATION_SCHEMA:
        _reject("source-authored measurement declaration absent")
    if metric not in _declared_metrics(call):
        _reject("metric is not in the native declaration")
    value = native["value"]
    if not _valid_count(value):
        _reject("native value is not a nonnegative integer")
    source_field = metric["source_field"]
    if not _valid_count(call.get(source_field)) or value != call[source_field]:
        _reject("projected value differs from the exact declared call counter")
    serving_record = native["serving_record"]
    if (serving_record.get("record_id") != call.get("backend_record_id") or
            serving_record.get("schema") != SERVING_SCHEMA or
            serving_record.get("record_sha256") != _digest_record(serving_record) or
            _process_identity(serving_record.get("provenance")) !=
            _process_identity(record.get("process"))):
        _reject("projected physical serving record does not bind to this process and call")
    physical_count = (serving_record.get("result") or {}).get(COUNTERS[source_field])
    if not _valid_count(physical_count) or value != physical_count:
        _reject("projected value differs from the joined physical counter")
    _verify_file_record(Path(native["usage_path"]), native["usage_file_sha256"], record,
                        line=native["usage_line"])
    _verify_file_record(Path(native["serving_path"]), native["serving_file_sha256"], serving_record)
    if not HEX64.fullmatch(native["usage_file_sha256"]) or not HEX64.fullmatch(native["serving_file_sha256"]):
        _reject("native log digest absent")
    if not GIT_SHA.fullmatch(str(record["process"].get("orch_commit") or "")):
        _reject("producer commit is unknown")
    stamp = datetime.fromtimestamp(record["ts_epoch"], tz=timezone.utc).date().isoformat()
    server = native["serving_record"].get("server", {})
    extra = {
        "usage_record_sha256": record["record_sha256"],
        "usage_log_sha256": native["usage_file_sha256"],
        "usage_log_line": native["usage_line"],
        "serving_record_id": native["serving_record"]["record_id"],
        "serving_log_sha256": native["serving_file_sha256"],
        "serving_log_path": native["serving_path"],
        "process": record["process"], "source_context": record.get("source_context"),
        "server": server, "provenance": call.get("provenance"),
        "native_source": call.get("source"), "finish_reason": call.get("finish_reason"),
        "logical_replays": native["logical_replays"], "read_report": native["read_report"],
        "persistence": record.get("persistence"),
    }
    return ClaimTuple(
        measurement_id=native["measurement_id"], metric=metric["metric"], value=value, date=stamp,
        category=metric["category"], metric_direction=metric["metric_direction"],
        protocol_id=metric["protocol_id"], claim=metric["claim"], reps=1,
        reps_basis=metric.get("reps_basis", "one native call"), unit=metric["unit"],
        attestation_path=native["usage_path"], attestation_sha256=native["usage_file_sha256"],
        attestation_locator=f"{native['usage_path']}:{native['usage_line']}",
        attestation_present=True, attestation_verified=True, source_kind="usage-provenance",
        extra=extra, applicability=metric.get("applicability", {}),
        observation=metric.get("observation", {}),
    )

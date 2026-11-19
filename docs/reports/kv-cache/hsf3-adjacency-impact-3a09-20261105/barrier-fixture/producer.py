#!/usr/bin/env python3
"""Passive session-gap extraction with prospective, self-hashed pair receipts.

No inference. Old dispatch/staging times are labelled proxies, never enqueue
observations. A gap has no better direction; only timestamp-pair integrity is a
verifier observation. Windows and client classes remain separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

SCHEMA = "epyc.session_gap_pair.v1"
METHOD = {
    "serving_call_schema": "epyc.orchestrator.serving_call.v1",
    "session": "caller.trace_keys.x_session_id or caller.session_id",
    "client_class": "caller.client_class when explicit; otherwise unknown",
    "role": "role",
    "completion": "ts_end sampled by serving decorator immediately after backend return; outcome=ok dispatched=true",
    "exact_enqueue": "queue.enqueue_ts_epoch (backend-admission entry, not frontend arrival)",
    "proxy_enqueue": "ts_start minus queue.pre_dispatch_wait_ms; staging after admission",
    "timestamp_precision": "completion/dispatch ISO: milliseconds; enqueue Unix seconds: native precision",
    "pairing": "adjacent calls in same session, role and explicit client class, sorted by enqueue or ts_start when unavailable; non-overlap only",
    "percentiles": "linear interpolation at (n-1)*p; at least 50 distinct sessions per window/class/role/basis",
}


class NativeIdentityConflict(ValueError):
    """A source snapshot cannot assign two native records the same identity."""


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def snapshot_source(path: Path, snapshot: Path, frontier: int) -> str:
    """Copy an initial byte frontier without loading the log into memory."""
    checksum = hashlib.sha256()
    remaining = frontier
    with path.open("rb") as source, snapshot.open("wb") as target:
        while remaining:
            chunk = source.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("native source truncated during snapshot")
            target.write(chunk)
            checksum.update(chunk)
            remaining -= len(chunk)
    return checksum.hexdigest()


def snapshot_lines(path: Path):
    with path.open("rb") as handle:
        yield from handle


def epoch(text: str) -> Decimal:
    stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp must declare a timezone")
    return Decimal(str(stamp.timestamp()))


def statement(row: dict) -> str:
    return (f"Timestamp pair {row['pair_id']} has nonnegative elapsed gap {row['gap_s']} s "
            f"inside declared window {row['window']['id']} from {row['timestamp_basis']} "
            f"at declared precision; client class {row['client_class']}, role {row['role']}.")


def capture_pair(first: dict, next_call: dict, window: dict, *, manifest_sha256: str,
                 extractor_sha256: str) -> dict:
    for key in ("session_hash", "role", "client_class"):
        if first[key] != next_call[key]:
            raise ValueError("pair crosses its declared session/role/client group")
    if not first["complete"] or next_call["enqueue"] is None:
        raise ValueError("pair has no successful completion or next enqueue")
    done, enqueue = epoch(first["ts_end"]), Decimal(next_call["enqueue"])
    start, end = epoch(window["start"]), epoch(window["end"])
    if not start <= done <= enqueue < end:
        raise ValueError("pair is outside its window or overlaps")
    ident = {"session_hash": first["session_hash"], "role": first["role"],
             "client_class": first["client_class"], "window": window,
             "first_record": first["record_id"], "next_record": next_call["record_id"],
             "timestamp_basis": next_call["basis"], "manifest_sha256": manifest_sha256}
    row = {"schema": SCHEMA, **ident, "pair_id": digest(ident),
           "extracted_at": datetime.now(timezone.utc).isoformat(),
           "t_done": str(done), "t_next": str(enqueue), "gap_s": str(enqueue - done),
           "source": next_call["source"], "extractor_sha256": extractor_sha256,
           "method_sha256": digest(METHOD), "precision": METHOD["timestamp_precision"],
           "integrity_result": True}
    row["claim"] = statement(row)
    row["row_sha256"] = digest(row)
    return row


def validate_row(row: dict) -> None:
    if row.get("schema") != SCHEMA or row.get("integrity_result") is not True:
        raise ValueError("not a prospective timestamp-pair integrity receipt")
    if row.get("row_sha256") != digest({k: v for k, v in row.items() if k != "row_sha256"}):
        raise ValueError("pair receipt hash differs")
    if row.get("precision") != METHOD["timestamp_precision"]:
        raise ValueError("pair timestamp precision differs")
    if row.get("method_sha256") != digest(METHOD):
        raise ValueError("pair extraction method differs")
    epoch(row["extracted_at"])
    ident_keys = ("session_hash", "role", "client_class", "window", "first_record",
                  "next_record", "timestamp_basis", "manifest_sha256")
    if row["pair_id"] != digest({key: row[key] for key in ident_keys}):
        raise ValueError("pair identity does not rederive")
    done, enqueue, gap = (Decimal(row[key]) for key in ("t_done", "t_next", "gap_s"))
    if not all(value.is_finite() for value in (done, enqueue, gap)):
        raise ValueError("nonfinite timestamp pair")
    if not epoch(row["window"]["start"]) <= done <= enqueue < epoch(row["window"]["end"]):
        raise ValueError("pair is outside its window or overlaps")
    if gap != enqueue - done or row["claim"] != statement(row):
        raise ValueError("pair result does not rederive")
    if row["timestamp_basis"] not in {"exact_backend_enqueue", "staging_proxy"}:
        raise ValueError("unknown timestamp basis")


def percentile(values: list[Decimal], fraction: Decimal) -> str:
    ordered = sorted(values)
    index = Decimal(len(ordered) - 1) * fraction
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return str(ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo))


def summarize(rows: list[dict], windows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        key = (row["window"]["id"], row["client_class"], row["role"], row["timestamp_basis"])
        groups[key].append(row)
    results = []
    for (window, client, role, basis), group in sorted(groups.items()):
        sessions = len({row["session_hash"] for row in group})
        result = {"window": window, "client_class": client, "role": role,
                  "timestamp_basis": basis, "n_gaps": len(group), "n_sessions": sessions,
                  "status": "coverage_gap" if sessions < 50 else "available",
                  "approximate": basis != "exact_backend_enqueue"}
        if sessions >= 50:
            values = [Decimal(row["gap_s"]) for row in group]
            result.update({name: percentile(values, Decimal(p))
                           for name, p in (("p50", ".5"), ("p90", ".9"), ("p99", ".99"))})
        results.append(result)
    return {"windows": windows, "groups": results, "empty_windows": [w["id"] for w in windows
            if not any(r["window"]["id"] == w["id"] for r in rows)],
            "exact_acceptance": "not established; requires >=50 exact sessions per requested class "
                                "in both independent windows; unknown client class proves no brand"}


def native_call(record: dict, source: dict) -> dict | None:
    """Normalize recorded native fields; missing enqueue calls remain adjacency barriers."""
    caller = record.get("caller") or {}
    keys = caller.get("trace_keys") or {}
    session = keys.get("x_session_id") or caller.get("session_id")
    role, client = record.get("role"), caller.get("client_class") or "unknown"
    if not isinstance(session, str) or not session or not isinstance(role, str) or not role:
        return None
    if not isinstance(client, str):
        return None
    queue = record.get("queue") or {}
    enqueue, basis = None, "unavailable"
    if "enqueue_ts_epoch" in queue:
        enqueue, basis = Decimal(str(queue["enqueue_ts_epoch"])), "exact_backend_enqueue"
    elif queue.get("pre_dispatch_wait_ms") is not None:
        enqueue = epoch(record["ts_start"]) - Decimal(str(queue["pre_dispatch_wait_ms"])) / 1000
        basis = "staging_proxy"
    done = epoch(record["ts_end"])
    if enqueue is not None and (not enqueue.is_finite() or enqueue > done):
        enqueue, basis = None, "unavailable"
    return {"session_hash": hashlib.sha256(session.encode()).hexdigest(), "role": role,
            "client_class": client, "record_id": record["record_id"], "ts_end": record["ts_end"],
            "enqueue": str(enqueue) if enqueue is not None else None,
            "sort_at": str(enqueue if enqueue is not None else epoch(record["ts_start"])),
            "complete": record.get("outcome") == "ok" and record.get("dispatched") is True,
            "basis": basis, "source": source}


def coverage_census(calls: list[dict], windows: list[dict]) -> list[dict]:
    """Count recorded coverage before filtering to usable gap pairs."""
    groups = defaultdict(list)
    for call in calls:
        stamp = Decimal(call["sort_at"])
        for window in windows:
            if epoch(window["start"]) <= stamp < epoch(window["end"]):
                groups[(window["id"], call["client_class"], call["role"])].append(call)
    result = []
    for (window, client, role), group in sorted(groups.items()):
        sessions = {call["session_hash"] for call in group}
        exact = {call["session_hash"] for call in group
                 if call["basis"] == "exact_backend_enqueue"}
        result.append({"window": window, "client_class": client, "role": role,
                       "n_keyed_calls": len(group), "n_keyed_sessions": len(sessions),
                       "n_completed_calls": sum(call["complete"] for call in group),
                       "n_exact_enqueue_calls": sum(call["basis"] == "exact_backend_enqueue" for call in group),
                       "n_exact_enqueue_sessions": len(exact),
                       "n_proxy_enqueue_calls": sum(call["basis"] == "staging_proxy" for call in group),
                       "n_unavailable_enqueue_calls": sum(call["enqueue"] is None for call in group),
                       "exact_session_coverage": "coverage_gap" if len(exact) < 50 else "available"})
    return result


def extract(paths: list[Path], windows: list[dict], out: Path) -> dict:
    """Author native receipts as the extraction runs; never backfill old claim tuples."""
    if len(windows) != 2 or windows[0]["id"] == windows[1]["id"]:
        raise ValueError("declare two independent named windows")
    ranges = sorted((epoch(w["start"]), epoch(w["end"])) for w in windows)
    if any(a >= b for a, b in ranges) or ranges[0][1] > ranges[1][0]:
        raise ValueError("windows must be nonempty and disjoint")
    out.mkdir(parents=True, exist_ok=False)
    snapshots, counts, calls = [], Counter(), []
    native_identities = {}
    keyed_sessions = set()
    for index, path in enumerate(paths):
        # The bounded initial byte frontier is the snapshot. Appends after it
        # belong to another extraction; torn tails remain explicitly counted.
        frontier = path.stat().st_size
        snapshot = out / f"source-{index}.jsonl"
        sha = snapshot_source(path, snapshot, frontier)
        snapshots.append({"path": str(snapshot), "source": str(path), "bytes": frontier, "sha256": sha})
        for line in snapshot_lines(snapshot):
            counts["records_seen"] += 1
            if not line.endswith(b"\n"):
                counts["torn_tail"] += 1
                continue
            try:
                record = json.loads(line)
                if record.get("schema") != METHOD["serving_call_schema"]:
                    counts["not_serving_call_schema"] += 1
                    keys = record.get("request_keys") or {}
                    sid = keys.get("x_session_id") if isinstance(keys, dict) else None
                    if isinstance(sid, str) and sid:
                        counts["tap_keyed_records_without_native_enqueue"] += 1
                        keyed_sessions.add(hashlib.sha256(sid.encode()).hexdigest())
                    continue
                rid = record.get("record_id")
                if not isinstance(rid, str) or not rid:
                    counts["malformed_records"] += 1
                    continue
                if rid in native_identities:
                    if native_identities[rid] != record:
                        raise NativeIdentityConflict(f"conflicting native record identity: {rid}")
                    counts["duplicate_record_id"] += 1
                    continue
                native_identities[rid] = record
                caller = record.get("caller") or {}
                keys = caller.get("trace_keys") or {}
                session = keys.get("x_session_id") or caller.get("session_id")
                if not isinstance(session, str) or not session:
                    counts["missing_session_key"] += 1
                    continue
                counts["keyed_records"] += 1
                session_hash = hashlib.sha256(session.encode()).hexdigest()
                keyed_sessions.add(session_hash)
                complete = record.get("outcome") == "ok" and record.get("dispatched") is True
                if not complete:
                    counts["incomplete_or_failed_call"] += 1
                normalized = native_call(record, {"path": str(snapshot), "sha256": sha})
                if normalized is None:
                    counts["missing_role_or_invalid_class"] += 1
                    continue
                if normalized["enqueue"] is None:
                    counts["missing_or_invalid_enqueue"] += 1
                normalized["native_record"] = record
                calls.append(normalized)
            except NativeIdentityConflict:
                raise
            except (ValueError, TypeError, KeyError, ArithmeticError, AttributeError):
                counts["malformed_records"] += 1
    extractor_bytes = Path(__file__).read_bytes()
    (out / "extractor.py").write_bytes(extractor_bytes)
    extractor_sha = hashlib.sha256(extractor_bytes).hexdigest()
    manifest = {"schema": "epyc.session_gap_manifest.v1", "sources": snapshots,
                "extractor_sha256": extractor_sha, "method": METHOD, "method_sha256": digest(METHOD),
                "windows": windows, "timestamp_precision": METHOD["timestamp_precision"]}
    manifest_path = out / "manifest.json"
    manifest_path.write_bytes(canonical(manifest))
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    grouped = defaultdict(list)
    for call in calls:
        grouped[(call["session_hash"], call["role"], call["client_class"])].append(call)
    rows = []
    receipt_path = out / "session-gap-pairs.jsonl"
    with receipt_path.open("wb") as receipts:
        for group in grouped.values():
            group.sort(key=lambda c: Decimal(c["sort_at"]))
            for first, next_call in zip(group, group[1:]):
                if not first["complete"] or next_call["enqueue"] is None:
                    counts["pair_missing_completion_or_enqueue"] += 1
                    continue
                for window in windows:
                    try:
                        row = capture_pair(first, next_call, window,
                                           manifest_sha256=manifest_sha, extractor_sha256=extractor_sha)
                    except ValueError:
                        continue
                    validate_row(row)
                    receipts.write(canonical(row) + b"\n")
                    rows.append(row)
    report = {"schema": "epyc.session_gap_report.v1", "counts": dict(counts),
              "manifest_sha256": manifest_sha, "keyed_sessions": len(keyed_sessions),
              "coverage": coverage_census(calls, windows),
              **summarize(rows, windows)}
    (out / "report.json").write_bytes(canonical(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, type=Path)
    parser.add_argument("--window", action="append", required=True,
                        help="ID,START_ISO,END_ISO (repeat twice)")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    windows = [dict(zip(("id", "start", "end"), spec.split(","))) for spec in args.window]
    report = extract(args.source, windows, args.out)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

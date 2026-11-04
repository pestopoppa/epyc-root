#!/usr/bin/env python3
"""Bounded aggregate-only HSF-3 source-coverage census; never emits identifiers."""
import argparse
import glob
import hashlib
import json
import os
import sqlite3
from pathlib import Path

EVENTS = {"session_created", "session_resumed", "session_checkpointed"}
MAX_RECORD = 1024 * 1024


def progress(paths):
    total = {"files": 0, "bytes": 0, "json_records": 0, "invalid_json": 0,
             "oversize_records": 0, "target_events": 0, "session_created": 0,
             "session_resumed": 0, "session_checkpointed": 0,
             "target_with_session_id": 0, "target_with_timestamp": 0,
             "target_with_both": 0}
    custody = []
    for name in sorted(paths):
        h = hashlib.sha256()
        with open(name, "rb") as f:
            before = os.fstat(f.fileno())
            limit, consumed = before.st_size, 0
            total["files"] += 1
            while consumed < limit:
                # Bound memory even for malformed records without newlines.
                chunk = f.readline(min(limit - consumed, MAX_RECORD + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                h.update(chunk)
                total["bytes"] += len(chunk)
                if len(chunk) > MAX_RECORD:
                    total["oversize_records"] += 1
                    if not chunk.endswith(b"\n"):
                        while consumed < limit:
                            tail = f.readline(min(limit - consumed, 64 * 1024))
                            if not tail:
                                break
                            consumed += len(tail)
                            h.update(tail)
                            total["bytes"] += len(tail)
                            if tail.endswith(b"\n"):
                                break
                    continue
                if not chunk.endswith(b"\n"):
                    continue  # incomplete tail at the captured frontier
                try:
                    row = json.loads(chunk)
                except (UnicodeDecodeError, ValueError):
                    total["invalid_json"] += 1
                    continue
                if not isinstance(row, dict):
                    total["invalid_json"] += 1
                    continue
                et = row.get("event_type") or row.get("event")
                if not isinstance(et, str) or et not in EVENTS:
                    continue
                total["target_events"] += 1
                total[et] += 1
                data = row.get("data") if isinstance(row.get("data"), dict) else {}
                has_sid = bool(data.get("session_id"))
                has_ts = any(bool(row.get(k)) for k in ("timestamp", "ts", "created_at"))
                total["target_with_session_id"] += int(has_sid)
                total["target_with_timestamp"] += int(has_ts)
                total["target_with_both"] += int(has_sid and has_ts)
            after = os.fstat(f.fileno())
            stable = (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino)
        if consumed != limit:
            raise RuntimeError("progress source read was incomplete; refusing partial result")
        if not stable:
            raise RuntimeError("progress source changed during bounded read; refusing result")
        custody.append({"source_class": "progress_jsonl", "bytes_hashed_and_scanned": consumed,
                        "sha256_hashed_and_scanned_bytes": h.hexdigest(), "stable_during_read": stable})
    return total, custody


def checkpoint(db):
    path = Path(db).resolve()
    uri = path.as_uri() + "?mode=ro"
    before = {}
    for suffix in ("", "-wal"):
        p = Path(str(path) + suffix)
        try:
            st = p.stat()
            before[suffix or "main"] = (st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)
        except FileNotFoundError:
            before[suffix or "main"] = None
    conn = sqlite3.connect(uri, uri=True, timeout=1)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = {"database_present": True, "tables_seen": len(tables),
                  "sessions_table_present": "sessions" in tables,
                  "checkpoints_table_present": "checkpoints" in tables,
                  "sessions_rows": None, "checkpoints_rows": None,
                  "sessions_created_at_present": False, "sessions_last_checkpoint_at_present": False,
                  "checkpoints_session_id_present": False, "checkpoints_created_at_present": False}
        for table in ("sessions", "checkpoints"):
            if table not in tables:
                continue
            cols = {r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")}
            result[table + "_rows"] = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            if table == "sessions":
                result["sessions_created_at_present"] = "created_at" in cols
                result["sessions_last_checkpoint_at_present"] = "last_checkpoint_at" in cols
            else:
                result["checkpoints_session_id_present"] = "session_id" in cols
                result["checkpoints_created_at_present"] = "created_at" in cols
        conn.commit()
    finally:
        conn.close()
    after = {}
    for suffix in ("", "-wal"):
        p = Path(str(path) + suffix)
        try:
            st = p.stat()
            after[suffix or "main"] = (st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)
        except FileNotFoundError:
            after[suffix or "main"] = None
    if before != after:
        raise RuntimeError("checkpoint DB or WAL changed during read; refusing result")
    custody = {"source_class": "sqlite_checkpoint_db", "sqlite_mode": "read_only_transaction_including_wal",
               "source_frontier_stable_during_query": True,
               "note": "main/WAL stat stability only; no logical-snapshot content hash claimed"}
    return result, custody


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--progress", default="/mnt/raid0/llm/epyc-orchestrator/logs/progress/*.jsonl")
    p.add_argument("--checkpoint-db", default="/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/sessions.db")
    p.add_argument("--out", help="new output directory")
    p.add_argument("--out-file", help="new aggregate JSON file, for rowflow result accounting")
    a = p.parse_args()
    if bool(a.out) == bool(a.out_file):
        p.error("provide exactly one of --out or --out-file")
    paths = glob.glob(a.progress)
    if not paths:
        raise RuntimeError("progress input glob matched no files; refusing zero-file census")
    pc, custody = progress(paths)
    db, dbcustody = checkpoint(a.checkpoint_db)
    result = {"schema": "hsf3_source_coverage_census.v1", "mode": "read_only_aggregate_only",
              "source_frontiers": custody + [dbcustody], "progress": pc, "checkpoint_db": db,
              "interpretation": "coverage only; no joins, gap pairs, client class, distribution, or HSF-3 completion inferred"}
    if a.out_file:
        outfile = Path(a.out_file)
        with outfile.open("x") as f:
            f.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    else:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=False)
        outfile = out / "aggregate.json"
        outfile.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"output": str(outfile), "progress_files": pc["files"],
                      "progress_target_events": pc["target_events"], "checkpoint_rows": db["checkpoints_rows"]}, sort_keys=True))


if __name__ == "__main__":
    main()

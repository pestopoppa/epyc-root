"""Synthetic source-shaped boundaries; no live records or inferred joins.

App contract: 300cf5817edccc4f82089f0faa477828496068b6, specifically
TapWriter._emit_event, ProgressEntry.to_json and Checkpoint.to_dict. These
fixtures copy their serialized shapes without importing runtime providers.
The prospective CI recipe must bind those source files independently.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(ROOT / "scripts" / "harness"))
import session_gap_measure as producer
from adapters import session_intercall_gap as reader
import claim_tuple as ct
from ingest_sources import ingest
from ledger import Ledger

WINDOWS = [
    {"id": "W1", "start": "2026-10-03T00:00:00Z", "end": "2026-10-04T00:00:00Z"},
    {"id": "W2", "start": "2026-10-04T00:00:00Z", "end": "2026-10-05T00:00:00Z"},
]
SESSION = "synthetic-shared-session"


def source_rows(kind, *, keyed=True):
    rows = []
    for i, second in enumerate((1, 5)):
        stamp = f"2026-10-03T01:00:{second:02d}+00:00"
        if kind == "tap":
            row = {"event": "start" if i else "end", "ts": stamp,
                   "ts_epoch": float(producer.epoch(stamp)),
                   "request_id": f"tap-{i}", "pid": 123,
                   "topology_hash": "synthetic-topology", "role": "frontdoor"}
            if keyed:
                row["request_keys"] = {"x_session_id": SESSION}
        elif kind == "progress":
            row = {"event_type": "task_completed", "task_id": f"task-{i}",
                   "timestamp": stamp, "agent_tier": "A", "agent_role": "frontdoor",
                   "data": {}, "memory_id": None, "outcome": "success",
                   "outcome_details": None}
        else:
            assert kind == "checkpoint"
            row = {"id": f"checkpoint-{i}", "session_id": SESSION,
                   "created_at": stamp, "context_hash": "synthetic-context",
                   "artifacts": [], "execution_count": i, "exploration_calls": 0,
                   "message_count": i, "trigger": "turns", "user_globals": {},
                   "variable_lineage": {}, "skipped_user_globals": [],
                   "pickled_globals": {}, "protocol_version": 1}
        rows.append(row)
    return rows


def native_rows(*, proxy=False, known_class=True):
    rows = []
    for i, second in enumerate((0, 5)):
        start = f"2026-10-03T01:00:{second:02d}Z"
        caller = {"trace_keys": {"x_session_id": SESSION}}
        if known_class:
            caller["client_class"] = "chat_repl"
        rows.append({"schema": producer.METHOD["serving_call_schema"],
                     "record_id": f"native-{i}", "ts_start": start,
                     "ts_end": f"2026-10-03T01:00:{second + 1:02d}Z",
                     "role": "frontdoor", "outcome": "ok", "dispatched": True,
                     "caller": caller,
                     "queue": ({"pre_dispatch_wait_ms": 0} if proxy else
                               {"enqueue_ts_epoch": str(producer.epoch(start))})})
    return rows


def capture(tmp_path, records):
    source = tmp_path / "synthetic-source.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in records))
    report = producer.extract([source], WINDOWS, tmp_path / "capture")
    return report, tmp_path / "capture" / "session-gap-pairs.jsonl"


@pytest.mark.parametrize("kind", ["tap", "progress", "checkpoint", "mixed"])
def test_non_native_source_shapes_never_supply_gap_pairs(tmp_path, kind):
    records = (sum((source_rows(k) for k in ("tap", "progress", "checkpoint")), [])
               if kind == "mixed" else source_rows(kind))
    assert all("schema" not in row and "queue" not in row for row in records)
    report, sidecar = capture(tmp_path, records)
    assert report["counts"]["records_seen"] == len(records)
    assert report["counts"]["not_serving_call_schema"] == len(records)
    assert report["counts"].get("tap_keyed_records_without_native_enqueue", 0) == (
        2 if kind in ("tap", "mixed") else 0)
    assert report["keyed_sessions"] == (1 if kind in ("tap", "mixed") else 0)
    assert report["coverage"] == report["groups"] == []
    assert sidecar.read_bytes() == b"" and reader.native_rows(sidecar) == []
    ledger = Ledger(tmp_path / "ledger.jsonl")
    result = ingest(ledger, "session-intercall-gap", [sidecar],
                    as_of="2026-10-05T00:00:00Z")
    assert result["frames_emitted"] == 0 and ledger.verify() == []


def test_unkeyed_tap_events_do_not_become_keyed_coverage(tmp_path):
    report, sidecar = capture(tmp_path, source_rows("tap", keyed=False))
    assert report["counts"]["not_serving_call_schema"] == 2
    assert report["counts"].get("tap_keyed_records_without_native_enqueue", 0) == 0
    assert report["keyed_sessions"] == 0 and reader.native_rows(sidecar) == []


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("known_class", [False, True])
def test_native_controls_keep_exact_proxy_and_unknown_class_distinct(
        tmp_path, proxy, known_class):
    report, sidecar = capture(tmp_path, native_rows(proxy=proxy, known_class=known_class))
    native = reader.native_rows(sidecar)
    assert len(native) == 1
    tup = reader.project(native[0])
    basis = "staging_proxy" if proxy else "exact_backend_enqueue"
    assert tup.extra["timestamp_basis"] == basis and tup.extra["gap_s"] == "4.0"
    assert ct.grade(tup)[:2] == ("Judged", "Located")
    group = report["groups"][0]
    assert group["client_class"] == ("chat_repl" if known_class else "unknown")
    assert group["timestamp_basis"] == basis and group["approximate"] is proxy
    assert group["status"] == "coverage_gap" and group["n_sessions"] == 1
    assert not any(key in group for key in ("p50", "p90", "p99"))
    assert report["empty_windows"] == ["W2"]


@pytest.mark.parametrize("kind", ["tap", "progress", "checkpoint"])
def test_source_identifiers_cannot_replace_native_adjacency_even_after_reseal(tmp_path, kind):
    records = native_rows() + source_rows(kind)
    report, sidecar = capture(tmp_path, records)
    assert len(reader.native_rows(sidecar)) == 1
    assert report["coverage"][0]["n_keyed_calls"] == 2
    row = json.loads(sidecar.read_text())
    row["next_record"] = records[-1][{"tap": "request_id", "progress": "task_id",
                                     "checkpoint": "id"}[kind]]
    keys = ("session_hash", "role", "client_class", "window", "first_record",
            "next_record", "timestamp_basis", "manifest_sha256")
    row["pair_id"] = producer.digest({key: row[key] for key in keys})
    row["claim"] = producer.statement(row)
    row["row_sha256"] = producer.digest({key: value for key, value in row.items()
                                         if key != "row_sha256"})
    sidecar.write_text(json.dumps(row) + "\n")
    with pytest.raises(ct.ProjectionError, match="not adjacent"):
        reader.native_rows(sidecar)

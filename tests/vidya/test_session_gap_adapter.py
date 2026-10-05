"""Gap extraction: honest coverage and prospective native-pair integrity only."""
from __future__ import annotations
import json
import sys
from decimal import Decimal
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

WINDOWS = [{"id": "W1", "start": "2026-10-03T00:00:00Z", "end": "2026-10-04T00:00:00Z"},
           {"id": "W2", "start": "2026-10-04T00:00:00Z", "end": "2026-10-05T00:00:00Z"}]


def call(rid="1", start="2026-10-03T01:00:00Z", end="2026-10-03T01:00:01Z", *, exact=True):
    return {"schema": producer.METHOD["serving_call_schema"], "record_id": rid,
            "ts_start": start, "ts_end": end, "outcome": "ok", "dispatched": True,
            "role": "frontdoor", "caller": {"session_id": "native-session", "client_class": "chat_repl"},
            "queue": ({"enqueue_ts_epoch": str(producer.epoch(start))} if exact
                      else {"pre_dispatch_wait_ms": 0})}


def write_fixture(tmp: Path, *, proxy=False) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    source = tmp / "native.jsonl"
    source.write_text("\n".join(json.dumps(row) for row in [call(exact=not proxy),
        call("2", "2026-10-03T01:00:05Z", "2026-10-03T01:00:06Z", exact=not proxy)]) + "\n")
    producer.extract([source], WINDOWS, tmp / "capture")
    return tmp / "capture" / "session-gap-pairs.jsonl"


def test_native_gap_integrity_roundtrips_without_grading_the_gap(tmp_path):
    sidecar = write_fixture(tmp_path)
    native = reader.native_rows(sidecar)
    assert len(native) == 1
    tup = reader.project(native[0])
    assert tup.value == 1 and tup.metric_direction == "higher_better"
    assert tup.extra["gap_s"] == "4.0"
    assert tup.claim == tup.decided_proposition and tup.binding_kind == "identity"
    assert ct.grade(tup)[0] == "Judged" and tup.protocol_id == ""
    assert tup.reps is None and str(sidecar) in tup.attestation_locator
    assert "manifest.json" in tup.attestation_locator
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest(ledger, "session-intercall-gap", [sidecar], as_of="2026-10-05T00:00:00Z")
    assert report["frames_emitted"] == 3 and ledger.verify() == []


def test_proxy_and_under_50_sessions_are_explicit_coverage_gaps(tmp_path):
    path = write_fixture(tmp_path, proxy=True)
    report = json.loads((path.parent / "report.json").read_text())
    group = report["groups"][0]
    assert group["timestamp_basis"] == "staging_proxy" and group["approximate"]
    assert group["n_sessions"] == group["n_gaps"] == 1
    assert group["status"] == "coverage_gap" and "p99" not in group
    assert report["empty_windows"] == ["W2"]
    tup = reader.project(reader.native_rows(path)[0])
    assert tup.extra["timestamp_basis"] == "staging_proxy"
    assert ct.grade(tup)[0] == "Judged"


def test_fifty_sessions_and_two_windows_never_pool():
    rows = []
    for window in WINDOWS:
        for i in range(50):
            rows.append({"window": window, "session_hash": str(i), "role": "r",
                         "client_class": "native", "timestamp_basis": "exact_backend_enqueue", "gap_s": str(i)})
    groups = producer.summarize(rows, WINDOWS)["groups"]
    assert len(groups) == 2
    assert all(g["n_sessions"] == 50 and g["p50"] == "24.5" and g["p99"] == "48.51" for g in groups)


def test_an_intervening_missing_enqueue_is_not_skipped(tmp_path):
    rows = [call(), call("2", "2026-10-03T01:00:05Z", "2026-10-03T01:00:06Z"),
            call("3", "2026-10-03T01:00:10Z", "2026-10-03T01:00:11Z")]
    rows[1]["queue"] = {}
    rows[1]["outcome"] = "error"
    source = tmp_path / "calls.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = producer.extract([source], WINDOWS, tmp_path / "capture")
    assert report["groups"] == []
    assert report["counts"]["pair_missing_completion_or_enqueue"] == 2
    coverage = report["coverage"][0]
    assert coverage["n_keyed_calls"] == 3 and coverage["n_completed_calls"] == 2
    assert coverage["n_exact_enqueue_calls"] == 2
    assert coverage["n_unavailable_enqueue_calls"] == 1
    assert coverage["exact_session_coverage"] == "coverage_gap"


def test_unknown_client_class_is_not_invented(tmp_path):
    rows = [call(), call("2", "2026-10-03T01:00:05Z", "2026-10-03T01:00:06Z")]
    for row in rows:
        row["caller"].pop("client_class")
    source = tmp_path / "calls.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = producer.extract([source], WINDOWS, tmp_path / "capture")
    assert report["groups"][0]["client_class"] == "unknown"


@pytest.mark.parametrize("mutation", ["gap", "snapshot", "manifest", "extractor"])
def test_capture_refuses_tampered_native_evidence(tmp_path, mutation):
    sidecar = write_fixture(tmp_path)
    if mutation == "gap":
        row = json.loads(sidecar.read_text())
        row["gap_s"] = "99"
        row["row_sha256"] = producer.digest({k: v for k, v in row.items() if k != "row_sha256"})
        sidecar.write_text(json.dumps(row) + "\n")
    else:
        artifact = {"snapshot": "source-0.jsonl", "manifest": "manifest.json", "extractor": "extractor.py"}[mutation]
        with (sidecar.parent / artifact).open("ab") as handle:
            handle.write(b" ")
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(sidecar)


def rewrite_identity(row):
    keys = ("session_hash", "role", "client_class", "window", "first_record",
            "next_record", "timestamp_basis", "manifest_sha256")
    row["pair_id"] = producer.digest({key: row[key] for key in keys})
    row["claim"] = producer.statement(row)
    row["row_sha256"] = producer.digest({key: value for key, value in row.items()
                                         if key != "row_sha256"})


def test_project_reverifies_receipt_and_refuses_caller_altered_row(tmp_path):
    sidecar = write_fixture(tmp_path)
    native = reader.native_rows(sidecar)[0]
    native["row"]["window"]["id"] = "invented"
    rewrite_identity(native["row"])
    native["manifest_verified"] = True
    with pytest.raises(ct.ProjectionError, match="custody"):
        reader.project(native)


def test_project_reverifies_source_after_native_read(tmp_path):
    sidecar = write_fixture(tmp_path)
    native = reader.native_rows(sidecar)[0]
    with (sidecar.parent / "source-0.jsonl").open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ct.ProjectionError, match="artifact hash"):
        reader.project(native)


def test_recomputed_hash_cannot_invent_manifest_window(tmp_path):
    sidecar = write_fixture(tmp_path)
    row = json.loads(sidecar.read_text())
    row["window"] = {**row["window"], "id": "invented"}
    rewrite_identity(row)
    sidecar.write_text(json.dumps(row) + "\n")
    with pytest.raises(ct.ProjectionError, match="window is not declared"):
        reader.native_rows(sidecar)


def test_recomputed_hash_cannot_skip_an_adjacent_native_call(tmp_path):
    records = [call(), call("2", "2026-10-03T01:00:05Z", "2026-10-03T01:00:06Z"),
               call("3", "2026-10-03T01:00:10Z", "2026-10-03T01:00:11Z")]
    source = tmp_path / "native.jsonl"
    source.write_text("".join(json.dumps(record) + "\n" for record in records))
    producer.extract([source], WINDOWS, tmp_path / "capture")
    sidecar = tmp_path / "capture" / "session-gap-pairs.jsonl"
    row = json.loads(sidecar.read_text().splitlines()[0])
    row["next_record"] = "3"
    row["t_next"] = str(producer.epoch(records[2]["ts_start"]))
    row["gap_s"] = str(Decimal(row["t_next"]) - Decimal(row["t_done"]))
    rewrite_identity(row)
    sidecar.write_text(json.dumps(row) + "\n")
    with pytest.raises(ct.ProjectionError, match="not adjacent"):
        reader.native_rows(sidecar)


def test_conflicting_duplicate_native_identity_refuses_before_receipts(tmp_path):
    source = tmp_path / "native.jsonl"
    source.write_text("".join(json.dumps(record) + "\n" for record in
                             [call(), call(end="2026-10-03T01:00:02Z")]))
    with pytest.raises(ValueError, match="conflicting native record identity"):
        producer.extract([source], WINDOWS, tmp_path / "capture")
    assert not (tmp_path / "capture" / "session-gap-pairs.jsonl").exists()


def test_identical_duplicate_native_identity_dedupes(tmp_path):
    source = tmp_path / "native.jsonl"
    source.write_text("".join(json.dumps(record) + "\n" for record in
                             [call(), call(), call("2", "2026-10-03T01:00:05Z", "2026-10-03T01:00:06Z")]))
    report = producer.extract([source], WINDOWS, tmp_path / "capture")
    assert report["counts"]["duplicate_record_id"] == 1
    assert len(reader.native_rows(tmp_path / "capture" / "session-gap-pairs.jsonl")) == 1


@pytest.mark.parametrize("key", ["session_hash", "role", "client_class"])
def test_capture_pair_cannot_cross_native_group(tmp_path, key):
    first = producer.native_call(call(), {})
    next_call = producer.native_call(call("2", "2026-10-03T01:00:05Z", "2026-10-03T01:00:06Z"), {})
    next_call[key] = "different"
    with pytest.raises(ValueError, match="crosses"):
        producer.capture_pair(first, next_call, WINDOWS[0], manifest_sha256="m", extractor_sha256="e")

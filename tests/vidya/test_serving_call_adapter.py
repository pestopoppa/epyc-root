"""Temporary-file contracts for the native per-call serving reader (no live logs)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import serving_call as reader  # noqa: E402


def _sealed(record: dict) -> dict:
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = hashlib.sha256(json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()
    return record


def _serving(**over) -> dict:
    row = {
        "schema": reader.SCHEMA,
        "record_id": "native-001",
        "ts_start": "2026-10-06T12:00:00.000Z",
        "ts_end": "2026-10-06T12:00:01.000Z",
        "wall_ms": 1000.0,
        "dispatched": True,
        "method": "infer",
        "role": "worker_general",
        "caller": {"request_id": "cj-001:try-01", "parent_request_id": "cj-001",
                   "task_id": "coherence_judge", "session_id": "session-fixture"},
        "queue": {"pre_dispatch_wait_ms": 2.5},
        "timings": {"prompt_ms": 10.0, "predicted_ms": 20.0,
                    "prompt_per_second": 100.0, "predicted_per_second": 50.0,
                    "cache_n": 12, "draft_n": 4, "draft_n_accepted": 3},
        "timings_source": "server",
        "server": {"identity_source": "absent", "argv_sha256": None,
                   "binary_realpath": None, "model_path": None},
        "provenance": {"orch_commit": "fixture-commit", "run_id": "fixture-run"},
    }
    row.update(over)
    return _sealed(row)


def _write_lines(path: Path, *rows: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False).encode() + b"\n" for row in rows))
    return path


def write_fixture(tmp_path: Path) -> Path:
    """One valid native serving record for the registry-wide offline CLI fixture."""
    return _write_lines(tmp_path / "serving_calls.jsonl", _serving())


def _judge(call_id="cj-001", **over):
    row = {"schema": reader.JUDGE_SCHEMA, "call_id": call_id,
           "task_id": "coherence_judge", "outcome": "scored"}
    row.update(over)
    return {"record": row}


def test_projects_only_native_explicit_metrics_with_exact_source_custody(tmp_path):
    path = _write_lines(tmp_path / "serving_calls.jsonl", _serving())
    rows = reader.native_rows(path)
    assert len(rows) == 7
    tuples = [reader.project(row) for row in rows]
    by_metric = {item.metric: item for item in tuples}
    assert set(by_metric) == {
        "serving_call.prompt_ms", "serving_call.predicted_ms",
        "serving_call.prompt_per_second", "serving_call.predicted_per_second",
        "serving_call.cache_n", "serving_call.draft_acceptance_rate",
        "serving_call.pre_dispatch_wait_ms",
    }
    assert by_metric["serving_call.draft_acceptance_rate"].value == 0.75
    assert by_metric["serving_call.prompt_ms"].metric_direction == "lower_better"
    assert by_metric["serving_call.predicted_per_second"].metric_direction == "higher_better"
    for item in tuples:
        assert item.attestation_locator.endswith(":native-001")
        assert item.attestation_sha256 == hashlib.sha256(
            rows[0]["source_line_bytes"]).hexdigest()
        assert item.attestation_verified is True
        assert item.extra["source_line_sha256"] == item.attestation_sha256
        assert item.extra["source_file_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert item.extra["unscoped_server_identity"] is True
        assert item.extra["server"]["binary_realpath"] is None
        assert item.extra["provenance"]["orch_commit"] == "fixture-commit"


def test_absent_timing_row_is_native_metadata_only_even_when_queue_exists(tmp_path):
    row = _serving(timings_source="absent", timings=None,
                   queue={"pre_dispatch_wait_ms": 8.0})
    path = _write_lines(tmp_path / "serving_calls.jsonl", row)
    assert len(reader.read_records(path)) == 1
    assert reader.native_rows(path) == ()
    assert reader.project_record(reader.read_records(path)[0]) == ()


@pytest.mark.parametrize("mutation, message", [
    (lambda r: r.update(record_sha256="0" * 64), "hash mismatch"),
    (lambda r: r.update(schema="other.schema.v1"), "wrong serving-call schema"),
])
def test_refuses_bad_hash_or_schema_without_partial_rows(tmp_path, mutation, message):
    good = _serving()
    bad = dict(good)
    mutation(bad)
    path = _write_lines(tmp_path / "serving_calls.jsonl", good, bad)
    with pytest.raises(ct.ProjectionError, match=message):
        reader.read_records(path)


def test_refuses_malformed_json_and_duplicate_native_record_ids(tmp_path):
    path = tmp_path / "serving_calls.jsonl"
    path.write_bytes(b"{broken}\n")
    with pytest.raises(ct.ProjectionError, match="invalid serving-call JSON"):
        reader.read_records(path)
    _write_lines(path, _serving(), _serving())
    with pytest.raises(ct.ProjectionError, match="duplicate serving-call record_id"):
        reader.read_records(path)


def test_discovery_includes_only_current_and_numbered_rotations(tmp_path):
    old = _write_lines(tmp_path / "serving_calls.jsonl.2", _serving(record_id="old"))
    current = _write_lines(tmp_path / "serving_calls.jsonl", _serving(record_id="new"))
    (tmp_path / "serving_calls.jsonl.lock").write_text("", encoding="utf-8")
    assert reader.discover(tmp_path) == (current, old)
    assert [row["record_id"] for row in reader.read_records(tmp_path)] == ["new", "old"]


def test_judge_join_uses_parent_id_and_preserves_distinct_attempts_once():
    judge = _judge()
    first = {"record": _serving(record_id="native-1")}
    second = {"record": _serving(record_id="native-2", caller={
        "request_id": "cj-001:try-02", "parent_request_id": "cj-001",
        "task_id": "coherence_judge"})}
    decoy = {"record": _serving(record_id="native-decoy", caller={
        "request_id": "cj-001", "parent_request_id": "another-parent",
        "task_id": "coherence_judge"})}
    result = reader.correlate((judge,), (first, second, decoy))
    assert len(result["matched"]) == 2
    assert len(result["unmatched_server"]) == 1
    assert len(result["unmatched_judge"]) == 0
    assert {item["serving"]["record"]["caller"]["request_id"]
            for item in result["matched"]} == {"cj-001:try-01", "cj-001:try-02"}
    assert all(item["judge"]["record"]["call_id"] == "cj-001"
               for item in result["matched"])


def test_unmatched_judge_and_server_records_remain_separate():
    judge_only = _judge("cj-refused")
    server_only = {"record": _serving(record_id="native-unmatched", caller={
        "request_id": "attempt-orphan", "parent_request_id": "cj-unknown",
        "task_id": "coherence_judge"})}
    result = reader.correlate((judge_only,), (server_only,))
    assert result["matched"] == ()
    assert len(result["unmatched_judge"]) == 1
    assert len(result["unmatched_server"]) == 1
    assert result["unmatched_judge"][0]["record"]["call_id"] == "cj-refused"
    assert result["unmatched_server"][0]["serving"]["record"]["record_id"] == "native-unmatched"


def test_absent_task_id_does_not_block_parent_join_and_other_task_does():
    judge = _judge()
    no_task = {"record": _serving(caller={"request_id": "attempt-1",
                                        "parent_request_id": "cj-001"})}
    other = {"record": _serving(record_id="other", caller={
        "request_id": "attempt-2", "parent_request_id": "cj-001", "task_id": "other"})}
    result = reader.correlate((judge,), (no_task, other))
    assert len(result["matched"]) == 1
    assert result["matched"][0]["serving"]["record"]["caller"].get("task_id") is None
    assert len(result["unmatched_server"]) == 1


def test_correlator_refuses_duplicate_judge_ids_and_wrong_schemas():
    with pytest.raises(ct.ProjectionError, match="duplicate judge call_id"):
        reader.correlate((_judge(), _judge()), ())
    with pytest.raises(ct.ProjectionError, match="wrong judge-call schema"):
        reader.correlate(({"record": {"schema": "wrong", "call_id": "cj"}},), ())
    with pytest.raises(ct.ProjectionError, match="wrong serving-call schema"):
        reader.correlate((), ({"record": {"schema": "wrong"}},))
    row = _serving()
    row["record_sha256"] = "0" * 64
    with pytest.raises(ct.ProjectionError, match="record hash mismatch"):
        reader.correlate((), ({"record": row},))
    good = _serving()
    with pytest.raises(ct.ProjectionError, match="duplicate serving-call record_id"):
        reader.correlate((), ({"record": good}, {"record": good}))


def test_judge_reader_marks_absent_producer_self_hash(tmp_path):
    path = _write_lines(tmp_path / "calls.jsonl", _judge()["record"])
    rows = reader.read_judge_rows(path)
    assert rows[0]["self_hash"] is None
    assert rows[0]["call_id"] == "cj-001"
    assert rows[0]["source_line_sha256"] == hashlib.sha256(rows[0]["source_line_bytes"]).hexdigest()

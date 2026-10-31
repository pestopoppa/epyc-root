"""The native usage writer projects only explicit declarations into planning context."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple
import ingest_sources
import loop_beliefs
from adapters import usage_provenance as reader
from ledger import Ledger

SYNTHETIC_MODEL = "usage-provenance-synthetic.gguf"
TEST_ONLY_DECLARATION = {
    "schema": "epyc.request_call_usage.measurement_declaration.v1",
    "metrics": [{
        "source_field": "completion_tokens",
        "metric": "test_only_completion_tokens",
        "unit": "tokens",
        "category": "CANDIDATE",
        "metric_direction": "higher_better",
        "protocol_id": "",
        "claim": "TEST ONLY synthetic writer fixture; not a runtime measurement or warrant.",
        "reps_basis": "one synthetic writer invocation",
        "applicability": {"model_file": SYNTHETIC_MODEL, "backend": "cpu"},
    }],
}


def _orchestrator_root() -> Path:
    configured = os.environ.get("EPYC_ORCHESTRATOR_ROOT")
    return Path(configured or "/workspace/repos/epyc-orchestrator").resolve()


def _writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
            declaration: dict | None = TEST_ONLY_DECLARATION):
    orchestrator = _orchestrator_root()
    if not (orchestrator / "src/llm_primitives/usage.py").is_file():
        pytest.skip("orchestrator source tree is not available for cross-repo writer canary")
    sys.path.insert(0, str(orchestrator))
    # Load the two actual writer modules without importing the orchestrator's unrelated API
    # dependency graph (the package __init__ eagerly imports every backend).
    for name, package_path in (
        ("src.backends", orchestrator / "src/backends"),
        ("src.llm_primitives", orchestrator / "src/llm_primitives"),
    ):
        package = types.ModuleType(name)
        package.__path__ = [str(package_path)]
        monkeypatch.setitem(sys.modules, name, package)
    serving_calls = importlib.import_module("src.backends.serving_calls")
    usage_module = importlib.import_module("src.llm_primitives.usage")
    usage_log = importlib.import_module("src.llm_primitives.usage_log")

    serving_path = tmp_path / "serving_calls.jsonl"
    monkeypatch.setenv(serving_calls.LOG_ENV, str(serving_path))
    monkeypatch.setattr(usage_log, "source_context", lambda: {
        "snapshot_kind": "on_disk_async_snapshot",
        "loaded_bytes_attestation": "not_available",
        "process_commit_semantics": "synthetic fixture; not loaded-byte proof",
        "head_commit_at_capture": serving_calls.process_provenance().get("orch_commit"),
        "worktree_state_at_capture": "clean",
        "relevant_source_complete": True,
    })
    usage_path = serving_path.with_name("usage_provenance.jsonl")

    def physical_call(request_id: str, completion_tokens: int = 0) -> str:
        record_id = uuid.uuid4().hex
        record = {
            "schema": serving_calls.SCHEMA,
            "record_id": record_id,
            "ts_start": datetime.now(timezone.utc).isoformat(),
            "ts_end": datetime.now(timezone.utc).isoformat(),
            "caller": {"request_id": request_id},
            "provenance": serving_calls.process_provenance(),
            "server": {"port": 12345, "model_path": SYNTHETIC_MODEL,
                       "launch_id": "synthetic-test-only"},
            "result": {"prompt_tokens": 2, "tokens_generated": completion_tokens,
                       "cached_prompt_tokens": 0},
        }
        assert serving_calls.write_record(record)
        return record_id

    request_id = "usage-provenance-test-" + uuid.uuid4().hex
    backend_id = physical_call(request_id)
    ledger = usage_module.UsageLedger(request_id)
    call_id = ledger.begin("test_only", measurement_declaration=declaration)
    ledger.finish(call_id, prompt_tokens=2, completion_tokens=0, cached_tokens=0,
                  provenance="server_reported",
                  source="llama_server:/completion.tokens_predicted",
                  backend_record_id=backend_id, finish_reason="stop")
    return usage_path, call_id, backend_id, usage_module, physical_call


class _Sync:
    def status(self, *args, **kwargs):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1,
                "synced_max_id": 1, "last_sync": datetime.now(timezone.utc).isoformat()}

    def sync(self, *args, **kwargs):
        raise AssertionError("planning canary unexpectedly requested a source sync")


def test_writer_reader_and_planning_canary_preserve_declaration_and_scope(tmp_path, monkeypatch):
    usage_path, original_call_id, backend_id, usage_module, _ = _writer(tmp_path, monkeypatch)
    replay_ledger = usage_module.UsageLedger("usage-provenance-replay-" + uuid.uuid4().hex)
    replay_id = replay_ledger.begin("test_only", measurement_declaration=TEST_ONLY_DECLARATION)
    replay_ledger.finish(replay_id, prompt_tokens=2, completion_tokens=0, cached_tokens=0,
                         provenance="cached_replay_of_server_reported", source="content_cache",
                         replay_of_call_id=original_call_id, finish_reason="stop")

    rows = reader.native_rows(usage_path)
    assert len(rows) == 1  # the replay links to, but does not count, the physical call again
    row = rows[0]
    assert row["value"] == 0
    assert row["serving_record"]["record_id"] == backend_id
    assert row["logical_replays"] == [{
        "request_id": replay_ledger.request_id,
        "call_id": replay_id,
        "parent_call_id": None,
        "replay_of_call_id": original_call_id,
        "backend_record_id": backend_id,
    }]
    claim = reader.project(row)
    assert claim_tuple.grade(claim)[:2] == ("Judged", "Located")
    assert claim.metric == "test_only_completion_tokens"
    assert claim.value == 0
    assert claim.applicability == TEST_ONLY_DECLARATION["metrics"][0]["applicability"]
    assert claim.extra["logical_replays"][0]["replay_of_call_id"] == original_call_id

    ledger_path = tmp_path / "planning-ledger.jsonl"
    as_of = datetime.now(timezone.utc).isoformat()
    result = ingest_sources.ingest(Ledger(ledger_path), "usage-provenance", [usage_path], as_of=as_of)
    assert result["rows_projected"] == 1
    cfg = tmp_path / "alarm.yaml"
    cfg.write_text("backend: file\nfile:\n  path: " + str(tmp_path / "alarm.jsonl") + "\n")
    common = {
        "ledger": ledger_path, "index_path": tmp_path / "index.yaml", "as_of": as_of,
        "sync_module": _Sync(), "alarm_config": cfg,
    }
    synthetic = loop_beliefs.prepare(
        "test.usage_provenance.synthetic", {"backend": "cpu", "model_file": SYNTHETIC_MODEL},
        known_good=tmp_path / "known-synthetic.json", alarm_state=tmp_path / "alarm-synthetic.json",
        read_log=tmp_path / "reads-synthetic.jsonl", **common)
    real = loop_beliefs.prepare(
        "test.usage_provenance.real", {"backend": "cpu", "model_file": "real-model.gguf"},
        known_good=tmp_path / "known-real.json", alarm_state=tmp_path / "alarm-real.json",
        read_log=tmp_path / "reads-real.jsonl", **common)
    synthetic_claims = [c for c in synthetic.get("evidence", {}).get("claims", [])
                        if c.get("source_kind") == "usage-provenance"]
    real_claims = [c for c in real.get("evidence", {}).get("claims", [])
                   if c.get("source_kind") == "usage-provenance"]
    assert len(synthetic_claims) == 1
    assert synthetic_claims[0]["model_file"] == SYNTHETIC_MODEL
    assert not real_claims
    assert (tmp_path / "reads-synthetic.jsonl").is_file()
    assert (tmp_path / "reads-real.jsonl").is_file()


def test_unannotated_real_shape_remains_refused(tmp_path, monkeypatch):
    usage_path, _, _, _, _ = _writer(tmp_path, monkeypatch, declaration=None)
    # Existing v1 writer shape with an absent declaration is intentionally not projectable.
    with pytest.raises(claim_tuple.ProjectionError, match="explicit measurement declaration"):
        reader.native_rows(usage_path)


@pytest.mark.parametrize("field,value", [
    ("metric_direction", "neutral"),
    ("category", {"unexpected": "object"}),
    ("protocol_id", None),
])
def test_reader_rejects_invalid_source_declaration(tmp_path, monkeypatch, field, value):
    usage_path, _, _, _, _ = _writer(tmp_path, monkeypatch)
    records = [json.loads(line) for line in usage_path.read_text().splitlines()]
    for record in records:
        declaration = record["call"]["measurement_declaration"]
        declaration["metrics"][0][field] = value
        record["record_sha256"] = hashlib.sha256(json.dumps(
            {k: v for k, v in record.items() if k != "record_sha256"},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()).hexdigest()
    usage_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                                     for row in records))
    with pytest.raises(claim_tuple.ProjectionError, match="measurement declaration"):
        reader.native_rows(usage_path)

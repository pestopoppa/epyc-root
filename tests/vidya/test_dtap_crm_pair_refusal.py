"""Synthetic native-custody controls; never a live measurement."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import dtap_crm_pair as adapter  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def test_journal_chain_refuses_truncation_mutation_and_missing_terminal():
    def line(kind, previous):
        return (json.dumps({"kind": kind, "utc": "2026-11-02T13:00:00+00:00",
                            "previous_sha256": previous, "payload": {}},
                           sort_keys=True, separators=(",", ":")) + "\n").encode()
    start = line("start", "0" * 64)
    end = line("terminal", digest(start))
    assert [r["kind"] for r in adapter._journal(start + end)] == ["start", "terminal"]
    for bad in (start + end[:-1], start, start + end.replace(b'"terminal"', b'"changed!"'),
                start + end.replace(digest(start).encode(), b"f" * 64)):
        with pytest.raises(ValueError):
            adapter._journal(bad)


def test_fixture_seal_is_never_promoted_to_live_measurement(tmp_path):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps({"schema": adapter.SCHEMA, "capture_kind": "fixture"}))
    with pytest.raises(ProjectionError, match="refused"):
        adapter.native_rows(path)


def test_consistent_self_declared_live_receipt_still_refuses_authority(tmp_path, monkeypatch):
    producer = tmp_path / "producer.py"
    producer.write_bytes(b"synthetic producer bytes")
    monkeypatch.setattr(adapter, "PRODUCER_SHA256", digest(producer.read_bytes()))
    grant, source = tmp_path / "grant", tmp_path / "source"
    grant.write_bytes(b"arbitrary file")
    source.write_bytes(b"arbitrary source declaration")
    prov = {key: "a" * 64 for key in ("source_tree_sha256", "model_sha256", "server_sha256",
                                       "template_sha256", "tool_schema_sha256", "case_sha256")}
    prov.update(source_commit="b" * 40, grant_id="synthetic", model_pid=1,
                model_pid_starttime=1, backend="cpu")
    utc = "2026-11-02T13:00:00+00:00"
    state = {"salesforce": {}, "slack": {}}
    state_sha = digest(json.dumps(state, sort_keys=True, separators=(",", ":")).encode())
    manifest = {"case": adapter.CASE, "arms": ["control", "attack"], "skill_injection": "not_tested",
                "schema_sha256": prov["tool_schema_sha256"], "registry_sha256": prov["case_sha256"]}
    arms = {arm: {"status": "complete", "delivery": "not_observed"} for arm in ("control", "attack")}
    events = [("start", {"capture_kind": "live", "provenance": prov}),
              ("pair_manifest", {"manifest": manifest})]
    for arm in arms:
        events.extend([("reset", {"arm": arm, "state": state, "sha256": state_sha}),
                       ("judged", {"arm": arm, "delivery": "not_observed", "judge": {"task_success": True}})])
    events.extend([("cleanup", {"status": "completed_by_backend"}),
                   ("terminal", {"arms": arms, "cleanup": "completed_by_backend"})])
    raw, previous = b"", "0" * 64
    for kind, payload in events:
        line = (json.dumps({"kind": kind, "utc": utc, "previous_sha256": previous, "payload": payload},
                           sort_keys=True, separators=(",", ":")) + "\n").encode()
        raw += line
        previous = digest(line)
    journal = tmp_path / "journal.jsonl"
    journal.write_bytes(raw)
    seal = {"schema": adapter.SCHEMA, "capture_kind": "live", "provenance": prov, "arms": arms,
            "cleanup": "completed_by_backend", "capture_start_utc": utc, "terminal_utc": utc, "sealed_utc": utc}
    for key, path in (("journal", journal), ("grant_receipt", grant), ("source_manifest", source), ("producer", producer)):
        seal[key + "_path"] = str(path)
        seal[key + "_sha256"] = digest(path.read_bytes())
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(seal))
    assert adapter._open_pair(receipt)["results"]["attack"]["delivery"] == "not_observed"
    with pytest.raises(ProjectionError, match="authority"):
        adapter.native_rows(receipt)
    # A reset failure produces an explicit skipped attack, not a fabricated result.
    arms = {"control": {"status": "failed", "delivery": "not_observed"},
            "attack": {"status": "not_attempted", "delivery": "not_observed"}}
    partial = [("start", {"capture_kind": "live", "provenance": prov}),
               ("pair_manifest", {"manifest": manifest}),
               ("arm_failed", {"arm": "control", "delivery": "not_observed", "error": {"type": "reset"}}),
               ("cleanup", {"status": "completed_by_backend"}),
               ("arm_skipped", {"arm": "attack", "delivery": "not_observed", "reason": "prior_arm_failed"}),
               ("terminal", {"arms": arms, "cleanup": "completed_by_backend"})]
    raw, previous = b"", "0" * 64
    for kind, payload in partial:
        line = (json.dumps({"kind": kind, "utc": utc, "previous_sha256": previous, "payload": payload},
                           sort_keys=True, separators=(",", ":")) + "\n").encode()
        raw += line
        previous = digest(line)
    journal.write_bytes(raw)
    seal["arms"] = arms
    seal["journal_sha256"] = digest(raw)
    receipt.write_text(json.dumps(seal))
    assert adapter._open_pair(receipt)["results"]["attack"]["status"] == "not_attempted"
    with pytest.raises(ProjectionError, match="authority"):
        adapter.native_rows(receipt)
    journal.write_bytes(raw + b"tamper")
    with pytest.raises(ProjectionError, match="refused"):
        adapter.native_rows(receipt)

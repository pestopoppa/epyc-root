"""Synthetic native-custody controls; never a live measurement."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import dtap_crm_pair as adapter  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def test_reviewed_source_pins_are_full_sha256():
    for value in (adapter.PRODUCER_SHA256, adapter.PROVIDER_SHA256,
                  adapter.LOCK_SHA256, adapter.RECEIPT_SHA256):
        assert adapter.SHA256.fullmatch(value)


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
    with pytest.raises(ProjectionError, match="refused"):
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
    with pytest.raises(ProjectionError, match="refused"):
        adapter.native_rows(receipt)
    journal.write_bytes(raw + b"tamper")
    with pytest.raises(ProjectionError, match="refused"):
        adapter.native_rows(receipt)


def test_provider_claim_requires_pins_grant_window_and_production_root(tmp_path, monkeypatch):
    lock_root, grant_root = tmp_path / "locks", tmp_path / "grants"
    lock_root.mkdir()
    grant_root.mkdir()
    monkeypatch.setattr(adapter, "LOCK_ROOT", lock_root)
    monkeypatch.setattr(adapter, "GRANT_ROOT", grant_root)
    pins = {}
    sources = {}
    for key, constant in (("provider", "PROVIDER_SHA256"), ("lock", "LOCK_SHA256"),
                          ("receipt", "RECEIPT_SHA256")):
        source = tmp_path / (key + ".py")
        source.write_text(key)
        sources[key] = source
        pins[key + "_sha256"] = digest(source.read_bytes())
        monkeypatch.setattr(adapter, constant, pins[key + "_sha256"])
    pins["expected_lock_root"] = str(lock_root)
    grant_raw = b"regions=0-23 start=2026-11-02T13:00Z end=2026-11-02T14:00Z holds=q0\n"
    grant_copy = tmp_path / "copy.grant"
    grant_copy.write_bytes(grant_raw)
    opened = {"schema": "region-lock-claim.v1", "phase": "open", "provider": "region-lock",
              "claim_id": "a" * 32, "provider_pid": 123, "provider_pid_starttime": 99,
              "lock_root": str(lock_root), "grant_id": "row1", "grant_path": str(grant_root / "row1.grant"),
              "grant_copy_path": str(grant_copy), "grant_sha256": digest(grant_raw),
              "grant_start": "2026-11-02T13:00Z", "grant_end": "2026-11-02T14:00Z",
              "opened_utc": "2026-11-02T13:01:00Z", "cpu_list": "0-23", "regions": ["q0"],
              "flock_proof": [{"region": "q0", "path": str(lock_root / "cpu_region.GLOBAL.q0.lock"),
                               "device_major": 1, "device_minor": 2, "inode": 3,
                               "proc_locks_row": "1: FLOCK ADVISORY WRITE 123 01:02:3 0 EOF"}]}
    for key, path in sources.items():
        opened[key + "_source_path"] = str(path)
        opened[key + "_source_sha256"] = pins[key + "_sha256"]
    open_path, close_path = tmp_path / "claim.open.json", tmp_path / "claim.close.json"
    open_path.write_text(json.dumps(opened))
    closed = {"schema": "region-lock-claim.v1", "phase": "close", "claim_id": opened["claim_id"],
              "provider_pid": 123, "provider_pid_starttime": 99, "open_path": str(open_path),
              "open_sha256": digest(open_path.read_bytes()), "child_rc": 0,
              "closed_utc": "2026-11-02T13:05:00Z"}
    close_path.write_text(json.dumps(closed))
    seal = {"claim_pins": pins, "claim_open_path": str(open_path), "claim_open_sha256": digest(open_path.read_bytes()),
            "claim_close_path": str(close_path), "claim_close_sha256": digest(close_path.read_bytes()),
            "grant_receipt_path": str(grant_copy), "capture_start_utc": "2026-11-02T13:02:00Z",
            "terminal_utc": "2026-11-02T13:04:00Z", "sealed_utc": "2026-11-02T13:06:00Z"}
    assert adapter._claim(seal, grant_raw, {"grant_id": "row1"})["regions"] == ["q0"]
    with pytest.raises(ValueError, match="captured bytes"):
        adapter._claim(seal, b"different", {"grant_id": "row1"})
    seal["capture_start_utc"] = "2026-11-02T12:59:00Z"
    with pytest.raises(ValueError, match="outside"):
        adapter._claim(seal, grant_raw, {"grant_id": "row1"})
    seal["capture_start_utc"] = "2026-11-02T13:02:00Z"
    close_path.write_text("tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        adapter._claim(seal, grant_raw, {"grant_id": "row1"})


def test_source_manifest_reopens_exact_files_and_git_blobs(tmp_path, monkeypatch):
    name = adapter.DTAP + "harness/crm_pair_capture.py"
    other = adapter.DTAP + "cases.json"
    monkeypatch.setattr(adapter, "SOURCE_FILES", (name, other))
    for path, contents in ((name, b"producer"), (other, b"registry")):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
    monkeypatch.setattr(adapter, "PRODUCER_SHA256", digest(b"producer"))
    files = {name: digest(b"producer"), other: digest(b"registry")}
    tree = digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())
    manifest = {"schema": "dtap.crm_source_manifest.v1", "repo_path": str(tmp_path),
                "source_commit": "a" * 40, "source_tree_sha256": tree, "files": files}
    def git_show(argv, **kwargs):
        target = argv[-1].split(":", 1)[1]
        return SimpleNamespace(stdout=(tmp_path / target).read_bytes())
    monkeypatch.setattr(adapter.subprocess, "run", git_show)
    prov = {"source_commit": "a" * 40, "source_tree_sha256": tree}
    seal = {"producer_path": str(tmp_path / name)}
    assert adapter._source(json.dumps(manifest).encode(), prov, seal)["source_commit"] == "a" * 40
    (tmp_path / other).write_bytes(b"changed")
    with pytest.raises(ValueError, match="differs"):
        adapter._source(json.dumps(manifest).encode(), prov, seal)

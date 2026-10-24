"""Strict-reader contract tests; fixtures are never projected or graded."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from adapters import distillation_pool as adapter
from claim_tuple import ProjectionError, grade, to_frames


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _write_fixture(path: Path, *, projection_count=1, legacy_total=1,
                   legacy_by_outcome=None):
    if legacy_by_outcome is None:
        legacy_by_outcome = {"unknown": 1}
    rows = [{"id": "fixture-memory", "action_type": "escalation", "q_value": 0.8,
             "outcome": None, "model_id": None, "from_tier": "worker", "to_tier": None}]
    counts = {
        "selected_total": 1,
        "projected_record_count": 1,
        "by_action_type": {"escalation": 1},
        "by_outcome": {"unknown": 1},
        "by_model_id": {"<null>": 1},
        "legacy_m25_by_outcome": {"unknown": 1},
        "native_escalation_count": 1,
        "projected_escalation_count": projection_count,
    }
    checks = {
        "selected_total_matches_native_selection": True,
        "selected_total_matches_projected_records": True,
        "selected_total_within_requested_top_k": True,
        "selected_q_values_meet_filter": True,
        "group_counts_rederive_from_rows": True,
        "legacy_m25_outcomes_match_native_rows": (
            legacy_total == 1 and legacy_by_outcome == {"unknown": 1}
        ),
        "legacy_m25_filter_matches_selector": True,
        "escalation_projection_matches_native_action_type": projection_count == 1,
        "native_escalation_count_matches_rows": True,
        "projection_marker_shape_valid": True,
        "selected_ids_unique": True,
    }
    errors = [key for key, passed in checks.items() if not passed]
    record = {
        "schema": adapter.SCHEMA,
        "invocation_id": "synthetic-fixture-invocation",
        "captured_at_utc": "2026-10-24T00:00:00Z",
        "capture_stage": "selected_pool_before_teacher",
        "synthetic": True,
        "unit": "episodic_memory_pattern",
        "selector": {
            "method": "EpisodicStore.retrieve_by_similarity", "query_method": "zero_vector",
            "query_dimension": 1024, "query_vector_sha256": "a" * 64, "k": 20,
            "candidate_overfetch_multiplier": 2, "action_type_filter": None,
            "min_q_value": 0.7,
            "indexed_row_predicate": "TRIM(COALESCE(action_type, '')) != ''",
            "return_order": "similarity_score_descending_then_top_k",
            "backend": "FixtureEmbeddingStore", "use_faiss": True,
        },
        "teacher": {
            "requested": "mock", "declared_model_id": "mock-fixture",
            "actual_served_model_id": None, "actual_served_identity_basis": "unobserved",
        },
        "code_provenance": {
            "repo_root": "/fixture", "git_head": None, "tracked_dirty": None,
            "git_probe_error": "FileNotFoundError", "source_file": "/fixture/structural_lab.py",
            "source_file_sha256": "b" * 64, "capture_helper_file": "/fixture/capture.py",
            "capture_helper_sha256": "c" * 64, "loaded_capture_helper_sha256": None,
            "loaded_capture_helper_identity_known": False, "loaded_function_sha256": None,
            "loaded_function_identity_known": False, "python_version": "3.12.0",
        },
        "source_store": {
            "sqlite": {"path": "/fixture/episodic.db", "available": False, "error": "FileNotFoundError"},
            "storage_dir": {"path": "/fixture/store", "available": False, "error": "FileNotFoundError"},
            "embedding_index": {"path": "/fixture/embeddings.faiss", "available": False, "error": "FileNotFoundError"},
            "id_map": {"path": "/fixture/id_map.npy", "available": False, "error": "FileNotFoundError"},
            "snapshot_claim": "none; exact returned metadata rows only, no whole-store hash or atomic snapshot",
        },
        "selected_rows": rows,
        "selected_rows_sha256": hashlib.sha256(_canonical(rows)).hexdigest(),
        "projection_markers": {"escalation_memory_ids": ["fixture-memory"] if projection_count else []},
        "counts": counts,
        "legacy_m25_pool": {
            "total": legacy_total, "by_outcome": legacy_by_outcome, "min_q_value": 0.7,
        },
        "integrity": {
            "decided_proposition": adapter._proposition(
                "synthetic-fixture-invocation", all(checks.values()), errors
            ),
            "verdict": all(checks.values()), "checks": checks, "errors": errors,
        },
    }
    record["receipt_sha256"] = hashlib.sha256(_canonical(record)).hexdigest()
    path.write_bytes(_canonical(record))
    return record


def test_synthetic_fixture_is_validated_then_declined(tmp_path):
    receipt = tmp_path / "fixture.json"
    record = _write_fixture(receipt)
    parsed, digest, artifact_digest = adapter._read_receipt(receipt)
    assert parsed["integrity"]["verdict"] is True
    assert digest == record["receipt_sha256"]
    assert artifact_digest == hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert adapter.native_rows(receipt) == ()


def test_false_integrity_is_preserved_but_fixture_is_not_ingested(tmp_path):
    receipt = tmp_path / "fixture.json"
    record = _write_fixture(receipt, projection_count=0, legacy_total=0,
                             legacy_by_outcome={})
    parsed, _, _ = adapter._read_receipt(receipt)
    assert parsed["integrity"]["verdict"] is False
    assert "escalation_projection_matches_native_action_type" in parsed["integrity"]["errors"]
    assert "legacy_m25_outcomes_match_native_rows" in parsed["integrity"]["errors"]
    assert adapter.native_rows(receipt) == ()


def test_selected_metadata_tamper_is_refused(tmp_path):
    receipt = tmp_path / "fixture.json"
    _write_fixture(receipt)
    record = json.loads(receipt.read_bytes())
    record["selected_rows"][0]["action_type"] = "routing"
    receipt.write_bytes(_canonical(record))
    with pytest.raises(ProjectionError, match="self-hash or canonical encoding mismatch"):
        adapter.native_rows(receipt)


@pytest.mark.parametrize("m25_counts_match", [True, False])
def test_actual_writer_reader_verifier_and_temp_ledger_round_trip(
    tmp_path, m25_counts_match
):
    configured = os.environ.get("EPYC_ORCHESTRATOR_SOURCE_ROOT")
    if not configured:
        pytest.skip("focused cross-repo test requires EPYC_ORCHESTRATOR_SOURCE_ROOT")
    orch_root = Path(configured).resolve()
    writer_path = orch_root / "scripts/autopilot/species/distillation_pool_capture.py"
    spec = importlib.util.spec_from_file_location("m26_distillation_pool_writer", writer_path)
    assert spec is not None and spec.loader is not None
    writer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = writer
    spec.loader.exec_module(writer)

    store_dir = tmp_path / "episodic-store"
    store_dir.mkdir()
    sqlite_path = store_dir / "episodic.db"
    sqlite_path.write_bytes(b"fixture-native-store-identity")
    store = SimpleNamespace(
        sqlite_path=sqlite_path,
        storage_dir=store_dir,
        _embedding_store=SimpleNamespace(
            index_path=store_dir / "embeddings.faiss",
            id_map_path=store_dir / "id_map.npy",
        ),
        use_faiss=True,
    )
    memory = SimpleNamespace(
        id="roundtrip-memory",
        action_type="escalation",
        q_value=0.9,
        outcome="success",
        model_id="fixture-model",
        context={"extra": {"from_tier": "worker", "to_tier": "architect"}},
    )

    def loaded_entrypoint():
        return None

    legacy_pool = (
        {"total": 1, "by_outcome": {"success": 1}, "min_q_value": 0.7}
        if m25_counts_match else
        {"total": 0, "by_outcome": {}, "min_q_value": 0.7}
    )
    result = writer.write_capture(
        repo_root=orch_root,
        output_dir=tmp_path,
        source_path=orch_root / "scripts/autopilot/species/structural_lab.py",
        loaded_function=loaded_entrypoint,
        store=store,
        memories=[memory],
        teacher_requested="claude",
        teacher_declared_model_id="requested-fixture-pin",
        max_trajectories=10,
        min_q_value=0.7,
        query_vector=SimpleNamespace(size=1024, tobytes=lambda: b"zero-vector-fixture"),
        projected_records=[{"escalations": [{"memory_id": "roundtrip-memory"}]}],
        legacy_m25_pool=legacy_pool,
        synthetic=False,
    )
    receipt = Path(result["path"])
    native = adapter.native_rows(receipt)[0]
    assert native["record"]["integrity"]["verdict"] is m25_counts_match
    claim = adapter.project(native)
    q, t, _reasons = grade(claim)
    as_of = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    frames = to_frames(
        claim, as_of=as_of, adapter_id=adapter.ADAPTER_ID, authority=adapter.AUTHORITY
    )
    evidence = next(
        frame["assertion"] for frame in frames
        if frame["frame_type"].endswith("evidence_supports_claim/v1")
    )
    assert type(claim.value) is int
    assert claim.value == (1 if m25_counts_match else 0)
    assert claim.unit == "false_0_true_1"
    assert claim.extra["native_verdict"] is m25_counts_match
    assert claim.attestation_sha256 == hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert claim.attestation_sha256 != native["receipt_sha256"]
    assert evidence["metric"] == claim.metric
    assert evidence["value"] == (1 if m25_counts_match else 0)
    assert evidence["unit"] == "false_0_true_1"
    assert evidence["observation"]["outcome_native"] == (
        "distillation_pool_integrity_passed"
        if m25_counts_match else "distillation_pool_integrity_failed"
    )
    assert evidence["grade"] == {"Q": q, "T": t}
    assert (" passed:" if m25_counts_match else " failed;") in claim.claim
    if not m25_counts_match:
        assert claim.extra["native_verdict"] is False
        assert "returned rows meet" not in claim.claim
        assert (q, t) == ("Judged", "Located")

    from ledger import Ledger

    isolated_ledger = Ledger(tmp_path / "isolated-ledger.jsonl")
    for frame in frames:
        isolated_ledger.append(frame)
    stored_frames = [item.frame for item in isolated_ledger.read_all()]
    stored_claim = next(
        frame for frame in stored_frames if frame["frame_type"].endswith("claim_proposed/v1")
    )
    stored_evidence = next(
        frame for frame in stored_frames
        if frame["frame_type"].endswith("evidence_supports_claim/v1")
    )
    assert stored_claim["assertion"]["display_text"] == claim.claim
    assert stored_evidence["assertion"]["value"] == (1 if m25_counts_match else 0)
    assert stored_evidence["assertion"]["unit"] == "false_0_true_1"
    assert isolated_ledger.path == tmp_path / "isolated-ledger.jsonl"

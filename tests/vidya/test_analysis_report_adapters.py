"""Strict source/input provenance and shared-grade projection for analysis reports."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from ledger import Ledger  # noqa: E402
from adapters import eval_suite_discriminability as eval_adapter  # noqa: E402
from adapters import verify_before_stop as vbs_adapter  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return _sha(raw)


def _seal(tmp_path: Path, body: dict, *, schema: str, producer: str) -> Path:
    root = tmp_path / "repo"
    src = root / producer
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"fixture producer source identity\n")
    inp = root / "data" / "source.jsonl"
    inp.parent.mkdir(parents=True, exist_ok=True)
    input_bytes = b'{"qid":"q1","correct":true,"error":false}\n'
    inp.write_bytes(input_bytes)
    provenance = {
        "schema": schema,
        "producer_path": producer,
        "producer_sha256": _sha(src.read_bytes()),
        "input_root": "epyc-orchestrator",
        "missing_inputs": [],
        "missing_inputs": [],
        "inputs": [{"path": "data/source.jsonl", "sha256": _sha(input_bytes),
                    "byte_count": len(input_bytes), "row_count": 1,
                    "normalized_row_count": 1}],
        "analysis_config_sha256": _canonical_sha(body.get("config", {})),
        "report_body_sha256": _canonical_sha(body),
    }
    provenance["record_id"] = _canonical_sha(provenance)
    body["native_provenance"] = provenance
    provenance["report_sha256"] = _canonical_sha(body)
    report = tmp_path / "report.json"
    report.write_text(json.dumps(body, sort_keys=True))
    return report


def _vbs_report(tmp_path: Path) -> Path:
    body = {
        "prior_reference": {},
        "corpus": {"n_total_real_trajectories": 3,
                   "date_range": None, "role_model": None},
        "classification": {},
        "rates": {
            "failure_over_all_voluntary_stops": {
                "numerator": 1, "denominator": 2, "point": 0.5,
                "wilson_95ci_lo": 0.0945, "wilson_95ci_hi": 0.9055},
            "failure_over_edited_voluntary_stops": {
                "numerator": 1, "denominator": 2, "point": 0.5,
                "wilson_95ci_lo": 0.0945, "wilson_95ci_hi": 0.9055},
            "no_execution_after_edit_corpuswide_forced_and_voluntary": {
                "numerator": 2, "denominator": 3, "point": 2 / 3,
                "wilson_95ci_lo_of_never_executed": 0.2077,
                "wilson_95ci_hi_of_never_executed": 0.9385,
                "call_bearing_edited_trajectories": 1},
        },
        "delegates_to_user_variant": {}, "execution_tool_availability": {},
        "auto_finalize_caveat": {}, "breakdown_by_arm": {}, "breakdown_by_task": {},
        "breakdown_by_source_dir": {}, "breakdown_by_role": {}, "examples_class_c": [],
        "examples_class_d": [], "prior_comparison": {},
    }
    return _seal(tmp_path, body, schema=vbs_adapter.REPORT_SCHEMA,
                 producer=vbs_adapter.PRODUCER)


def _eval_report(tmp_path: Path) -> Path:
    body = {
        "schema_version": eval_adapter.REPORT_SCHEMA,
        "generated_at": "2026-10-06T12:00:00+00:00",
        "measurement_class": "OBSERVATION",
        "config": {"alpha": 0.05, "power": 0.8, "target_effect": 0.15,
                   "saturation_high": 0.95, "saturation_low": 0.05, "min_n": 5,
                   "quantum_gate": 0.15, "run_spread_gate": 0.3,
                   "error_dominated_gate": 0.5},
        "inputs": ["data/source.jsonl"], "warnings": [],
        "summary": {"n_rows": 1, "n_suites": 1, "n_task_classes": 0,
                    "n_saturated_suites": 0, "n_floored_suites": 0,
                    "n_underpowered_suites": 1, "n_run_unstable_suites": 0,
                    "n_underpowered_task_classes": 0}, "task_classes": [],
        "suites": [{
            "group": "fixture", "n": 1, "n_unique_qids": 1, "n_runs": 1,
            "correct": 1, "errors": 0, "error_rate": 0.0, "pass_rate": 1.0,
            "pass_rate_excl_errors": 1.0, "wilson_ci": [0.2, 1.0], "wilson_width": 0.8,
            "effective_quantum": 1.0, "mde": 0.2, "mde_target_effect": 0.15,
            "n_per_arm": 1, "run_spread": 0.1, "error_dominated_runs": [],
            "run_stability_unmeasurable": False,
            "brittleness": {"measured": True, "n_multirun_qids": 1, "flip_rate": 0.25,
                            "mean_qid_variance": 0.25, "max_qid_variance": 0.25,
                            "n_error_excluded": 0},
            "per_run": {}, "saturated": False, "floored": False, "tiny_n": True,
            "underpowered": True, "run_unstable": False, "discriminability_index": 0.2,
            "flags": [],
        }],
    }
    return _seal(tmp_path, body, schema=eval_adapter.REPORT_SCHEMA,
                 producer=eval_adapter.PRODUCER)


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
])
def test_report_bytes_and_original_inputs_are_reverified_at_projection(tmp_path, monkeypatch,
                                                                       adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    path = factory(tmp_path)
    native = adapter.native_rows(path)
    assert native
    tuples = [adapter.project(row) for row in native]
    assert all(t.protocol_id == "" and t.attestation_verified is True for t in tuples)
    assert all(ct.grade(t)[0] == "Judged" for t in tuples)

    input_path = root / "data" / "source.jsonl"
    input_path.write_bytes(input_path.read_bytes() + b"\n")
    with pytest.raises(ProjectionError, match="bound input bytes changed"):
        adapter.project(native[0])


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
])
def test_identity_free_legacy_report_is_refused(tmp_path, monkeypatch, adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    current = factory(tmp_path)
    old = json.loads(current.read_text())
    old.pop("native_provenance")
    current.write_text(json.dumps(old))
    with pytest.raises(ProjectionError):
        adapter.native_rows(current)


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
])
def test_unknown_native_fields_are_refused(tmp_path, monkeypatch, adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    path = factory(tmp_path)
    doc = json.loads(path.read_text())
    doc["unexpected"] = "must not be silently ignored"
    path.write_text(json.dumps(doc))
    with pytest.raises(ProjectionError, match="unknown top-level fields"):
        adapter.native_rows(path)


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
])
def test_producer_source_changes_refuse_previously_discovered_rows(tmp_path, monkeypatch,
                                                                  adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    path = factory(tmp_path)
    native = adapter.native_rows(path)
    assert native
    producer = root / adapter.PRODUCER
    producer.write_bytes(producer.read_bytes() + b"# source changed after capture\n")
    with pytest.raises(ProjectionError, match="producer source bytes differ"):
        adapter.project(native[0])


@pytest.mark.parametrize(("source", "adapter", "factory"), [
    ("verify-before-stop-measurement", vbs_adapter, _vbs_report),
    ("eval-suite-discriminability", eval_adapter, _eval_report),
])
def test_cli_dispatch_uses_shared_grade_only(tmp_path, monkeypatch, capsys,
                                             source, adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    report_path = factory(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", source,
                   "--path", str(report_path), "--as-of", "2026-10-06T12:00:00Z"])
    assert rc == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["refused"] == []
    assert receipt["rows_projected"] > 0
    for record in Ledger(ledger).read_all():
        if record.frame["frame_type"].endswith("evidence_supports_claim/v1"):
            claim_id = record.frame["assertion"]["claim_id"]
            native = next(n for n in adapter.native_rows(report_path)
                          if f"clm_{adapter.project(n).measurement_id}" == claim_id)
            assert record.frame["assertion"]["grade"] == {
                "Q": ct.grade(adapter.project(native))[0],
                "T": ct.grade(adapter.project(native))[1],
            }

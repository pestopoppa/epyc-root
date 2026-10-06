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


def _rewrite_report(path: Path, mutate) -> None:
    report = json.loads(path.read_text())
    mutate(report)
    provenance = report["native_provenance"]
    provenance.pop("record_id", None)
    provenance.pop("report_sha256", None)
    provenance["report_body_sha256"] = _canonical_sha(
        {key: value for key, value in report.items() if key != "native_provenance"})
    provenance["record_id"] = _canonical_sha(provenance)
    provenance["report_sha256"] = _canonical_sha(report)
    path.write_text(json.dumps(report))


def _seal(tmp_path: Path, body: dict, *, schema: str, producer: str) -> Path:
    root = tmp_path / "repo"
    src = root / producer
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"fixture producer source identity\n")
    inp = root / "data" / "source.jsonl"
    inp.parent.mkdir(parents=True, exist_ok=True)
    input_bytes = b'{"qid":"q1","correct":true,"error":false}\n'
    inp.write_bytes(input_bytes)
    report = tmp_path / "report.json"
    snapshot_dir = tmp_path / "report.json.native" / ("a" * 64)
    snapshot_dir.mkdir(parents=True, mode=0o700)
    (snapshot_dir.parent).chmod(0o700)
    snapshot_dir.chmod(0o700)
    input_snapshot = snapshot_dir / "input-0000.raw"
    input_snapshot.write_bytes(input_bytes)
    input_snapshot.chmod(0o600)
    producer_snapshot = snapshot_dir / "producer.snapshot.py"
    producer_snapshot.write_bytes(src.read_bytes())
    producer_snapshot.chmod(0o600)
    provenance = {
        "schema": schema,
        "producer_path": producer,
        "producer_sha256": _sha(src.read_bytes()),
        "producer_snapshot_path": str(producer_snapshot),
        "input_root": "epyc-orchestrator",
        "missing_inputs": [],
        "inputs": [{"path": "data/source.jsonl", "sha256": _sha(input_bytes),
                    "byte_count": len(input_bytes), "row_count": 1,
                    "normalized_row_count": 1,
                    "snapshot_path": str(input_snapshot)}],
        "analysis_config_sha256": _canonical_sha(body.get("config", {})),
        "report_body_sha256": _canonical_sha(body),
    }
    provenance["record_id"] = _canonical_sha(provenance)
    body["native_provenance"] = provenance
    provenance["report_sha256"] = _canonical_sha(body)
    report.write_text(json.dumps(body, sort_keys=True))
    return report


def _vbs_report(tmp_path: Path) -> Path:
    body = {
        "category": "BASELINE",
        "prior_reference": {},
        "corpus": {"sources_scanned": ["fixture"], "n_total_real_trajectories": 3,
                   "n_forced_max_turns": 0, "n_forced_error": 0, "n_voluntary": 3,
                   "date_range": None, "role_model": None,
                   "scope_note": "fixture scope is not native time/role evidence"},
        "classification": {"a_no_edit": 1, "b_edit_then_executed": 1,
                           "c_edit_then_unverified": 1, "d_edit_then_delegated_to_user": 0,
                           "n_edited_total_b_c_d": 2, "n_failure_c_plus_d": 1},
        "rates": {
            "failure_over_all_voluntary_stops": {
                "numerator": 1, "denominator": 2, "point": 0.5,
                "wilson_95ci_lo": 0.0945, "wilson_95ci_hi": 0.9055},
            "failure_over_edited_voluntary_stops": {
                "numerator": 1, "denominator": 2, "point": 0.5,
                "wilson_95ci_lo": 0.0945, "wilson_95ci_hi": 0.9055},
            "no_execution_after_edit_corpuswide_forced_and_voluntary": {
                "description": "Fixture call-bearing heuristic",
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
        "category": "BASELINE",
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
            "per_run": {"run-1": {"n": 1, "correct": 1, "errors": 0,
                                    "n_scored": 1, "error_rate": 0.0,
                                    "pass_rate": 1.0, "pass_rate_excl_errors": 1.0,
                                    "error_dominated": False}},
            "saturated": False, "floored": False, "tiny_n": True,
            "underpowered": True, "run_unstable": False, "discriminability_index": 0.2,
            "flags": [],
        }],
    }
    return _seal(tmp_path, body, schema=eval_adapter.REPORT_SCHEMA,
                 producer=eval_adapter.PRODUCER)


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
], ids=("vbs", "eval"))
def test_report_bytes_and_retained_inputs_are_reverified_at_projection(tmp_path, monkeypatch,
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
    assert adapter.project(native[0]).attestation_verified is True


def test_immutable_input_snapshot_is_required_and_rechecked(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(vbs_adapter, "ORCHESTRATOR", root)
    path = _vbs_report(tmp_path)
    native = vbs_adapter.native_rows(path)
    assert native
    snapshot = tmp_path / "report.json.native" / ("a" * 64) / "input-0000.raw"
    snapshot.write_bytes(snapshot.read_bytes() + b"tamper")
    with pytest.raises(ProjectionError, match="immutable input snapshot differs"):
        vbs_adapter.project(native[0])


def test_mf_cached_metric_key_must_match_native_selection(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(vbs_adapter, "ORCHESTRATOR", root)
    path = _vbs_report(tmp_path)
    native = vbs_adapter.native_rows(path)
    changed = dict(native[0], metric_key="failure_over_edited_voluntary_stops")
    with pytest.raises(ProjectionError, match="metric selection"):
        vbs_adapter.project(changed)


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
], ids=("vbs", "eval"))
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
], ids=("vbs", "eval"))
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
], ids=("vbs", "eval"))
def test_category_must_be_producer_authored_diagnostic_baseline(tmp_path, monkeypatch,
                                                                adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    path = factory(tmp_path)
    _rewrite_report(path, lambda doc: doc.update(category="CANDIDATE"))
    with pytest.raises(ProjectionError, match="category must be producer-authored BASELINE"):
        adapter.native_rows(path)


@pytest.mark.parametrize(("adapter", "factory"), [
    (vbs_adapter, _vbs_report), (eval_adapter, _eval_report),
], ids=("vbs", "eval"))
def test_producer_source_changes_preserve_snapshot_bound_historical_rows(tmp_path, monkeypatch,
                                                                        adapter, factory):
    root = tmp_path / "repo"
    monkeypatch.setattr(adapter, "ORCHESTRATOR", root)
    path = factory(tmp_path)
    native = adapter.native_rows(path)
    assert native
    producer = root / adapter.PRODUCER
    producer.write_bytes(producer.read_bytes() + b"# source changed after capture\n")
    assert adapter.project(native[0]).attestation_verified is True


def test_snapshot_path_escape_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(vbs_adapter, "ORCHESTRATOR", root)
    path = _vbs_report(tmp_path)
    report = json.loads(path.read_text())
    report["native_provenance"]["inputs"][0]["snapshot_path"] = str(tmp_path / "outside.raw")
    report["native_provenance"]["record_id"] = _canonical_sha({k: v for k, v in
        report["native_provenance"].items() if k not in {"record_id", "report_sha256"}})
    report["native_provenance"].pop("report_sha256")
    report["native_provenance"]["report_sha256"] = _canonical_sha(report)
    path.write_text(json.dumps(report))
    with pytest.raises(ProjectionError, match="escapes the report-adjacent"):
        vbs_adapter.native_rows(path)


def test_external_input_original_locator_is_metadata_only(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(eval_adapter, "ORCHESTRATOR", root)
    path = _eval_report(tmp_path)
    external = tmp_path / "outside" / "question_ledger.jsonl"
    _rewrite_report(path, lambda doc: doc["native_provenance"]["inputs"][0].update(
        path=str(external)))
    rows = eval_adapter.native_rows(path)
    assert rows
    assert all(eval_adapter.project(row).attestation_verified for row in rows)


def test_zero_denominator_rate_is_omitted_while_defined_rates_remain(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(vbs_adapter, "ORCHESTRATOR", root)
    path = _vbs_report(tmp_path)
    def zero_rate(report):
        report["rates"]["failure_over_edited_voluntary_stops"].update(
            numerator=0, denominator=0, point=None,
            wilson_95ci_lo=None, wilson_95ci_hi=None)
    _rewrite_report(path, zero_rate)
    rows = vbs_adapter.native_rows(path)
    assert rows
    assert "failure_over_edited_voluntary_stops" not in {row["metric_key"] for row in rows}


@pytest.mark.parametrize("field", ["date_range", "role_model"], ids=("date_range", "role_model"))
def test_unbound_mf_scope_fields_cannot_be_supplied_by_report_envelope(tmp_path, monkeypatch, field):
    root = tmp_path / "repo"
    monkeypatch.setattr(vbs_adapter, "ORCHESTRATOR", root)
    path = _vbs_report(tmp_path)
    _rewrite_report(path, lambda doc: doc["corpus"].update({field: "claimed-scope"}))
    with pytest.raises(ProjectionError, match="does not bind native date or role/model"):
        vbs_adapter.native_rows(path)


def test_eval_run_spread_with_one_eligible_run_is_omitted_even_if_cached_flag_is_false(
        tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(eval_adapter, "ORCHESTRATOR", root)
    path = _eval_report(tmp_path)
    rows = eval_adapter.native_rows(path)
    assert rows
    assert "run_spread" not in {row["metric"] for row in rows}
    assert "pass_rate" in {row["metric"] for row in rows}


def test_eval_metric_reps_use_each_native_denominator(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(eval_adapter, "ORCHESTRATOR", root)
    path = _eval_report(tmp_path)
    rows = eval_adapter.native_rows(path)
    tuples = {row["metric"]: eval_adapter.project(row) for row in rows}
    assert tuples["pass_rate"].reps == 1  # producer's all-row n
    assert tuples["pass_rate"].reps_basis.startswith("native denominator")
    assert tuples["mde"].reps == 1  # producer's n_per_arm
    assert tuples["flip_rate"].reps == 1  # n_multirun_qids
    assert "run_spread" not in tuples  # only one eligible run, even if the cached flag is false


def test_eval_cached_suite_and_metric_must_match_bound_report(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(eval_adapter, "ORCHESTRATOR", root)
    path = _eval_report(tmp_path)
    rows = eval_adapter.native_rows(path)
    selected = next(row for row in rows if row["metric"] == "pass_rate")
    changed_value = dict(selected, value=0.0)
    with pytest.raises(ProjectionError, match="cached metric value"):
        eval_adapter.project(changed_value)
    changed_suite = dict(selected, suite=dict(selected["suite"]))
    changed_suite["suite"]["brittleness"] = dict(selected["suite"]["brittleness"],
                                                    measured=False)
    with pytest.raises(ProjectionError, match="cached suite"):
        eval_adapter.project(changed_suite)


@pytest.mark.parametrize(("source", "adapter", "factory"), [
    ("verify-before-stop-measurement", vbs_adapter, _vbs_report),
    ("eval-suite-discriminability", eval_adapter, _eval_report),
], ids=("vbs", "eval"))
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

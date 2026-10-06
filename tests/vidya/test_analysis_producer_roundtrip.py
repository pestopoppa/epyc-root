"""Hosted-only, synthetic APP-writer -> ROOT-adapter source-bound round trips.

The capture recipe sets EPYC_ORCHESTRATOR_SOURCE_ROOT to the separately pinned APP source
checkout. This fixture copies and hash-checks the exact producer/dependency bytes into a temporary
project tree, then uses the actual producer normalization/summarization/sealing functions over
synthetic bytes. It never reads the live BEP corpus or a real evaluation run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import eval_suite_discriminability as eval_adapter  # noqa: E402
from adapters import verify_before_stop as mf_adapter  # noqa: E402


_APP_SHA256 = {
    "scripts/analysis/mf_vbs1_verify_before_stop.py":
        "7463afeab66a20c274314e5f0a85472e271dc7e12e10f052b874039d4c0b44da",
    "scripts/analysis/eval_suite_discriminability.py":
        "6e3e8e688b74b857d7023e10361ca5c13334f8facbb69cae6a37c3df1648de35",
    "src/llm_primitives/stat_tests.py":
        "d0886ef1b32498475d804b9597347d2934b3dc0553224c0443a98654436af2dc",
}


def _copy_exact(app_root: Path, temp_root: Path, relative: str) -> Path:
    raw = (app_root / relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _APP_SHA256[relative], relative
    target = temp_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return target


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _app_tree(tmp_path: Path) -> tuple[Path, object, object]:
    configured = os.environ.get("EPYC_ORCHESTRATOR_SOURCE_ROOT")
    if not configured:
        pytest.skip("hosted source-bound integration recipe must provide APP source root")
    app_root = Path(configured).resolve()
    temp_root = tmp_path / "synthetic-orchestrator"
    mf_path = _copy_exact(app_root, temp_root, "scripts/analysis/mf_vbs1_verify_before_stop.py")
    eval_path = _copy_exact(app_root, temp_root, "scripts/analysis/eval_suite_discriminability.py")
    _copy_exact(app_root, temp_root, "src/llm_primitives/stat_tests.py")
    package_init = app_root / "src/llm_primitives/__init__.py"
    package_target = temp_root / "src/llm_primitives/__init__.py"
    package_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(package_init, package_target)
    sys.path.insert(0, str(temp_root))
    return temp_root, _load_module(mf_path, "captured_mf_vbs1_producer"), \
        _load_module(eval_path, "captured_eval_discriminability_producer")


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in rows))


def test_actual_mf_producer_snapshot_round_trips_through_root_adapter(tmp_path, monkeypatch):
    app_root, producer, _ = _app_tree(tmp_path)
    results = app_root / "data/bep_sandbox/synthetic/results.jsonl"
    trace_a = app_root / "data/bep_sandbox/synthetic/traces/a.jsonl"
    trace_b = app_root / "data/bep_sandbox/synthetic/traces/b.jsonl"
    _jsonl(results, [
        {"mode": "real", "task": "a", "arm": "base", "block": 0, "turns": 2,
         "touched_files": ["a.py"], "answer_preview": "done", "trace": {"path": "traces/a.jsonl"}},
        {"mode": "real", "task": "b", "arm": "base", "block": 0, "turns": 2,
         "touched_files": ["b.py"], "answer_preview": "done", "trace": {"path": "traces/b.jsonl"}},
    ])
    _jsonl(trace_a, [{"raw_output": "finished"}])
    _jsonl(trace_b, [{"raw_output": "please run the test yourself"}])
    inputs: list[dict] = []
    missing: list[str] = []
    trajectories = producer.load_trajectories(str(app_root), input_manifest=inputs,
                                              missing_inputs=missing)
    report = producer.summarize(trajectories)
    report_path = app_root / "data/analysis/synthetic-mf.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = producer._seal_report(report, str(app_root), inputs, str(report_path), missing)
    report_path.write_text(json.dumps(report, sort_keys=True))

    monkeypatch.setattr(mf_adapter, "ORCHESTRATOR", app_root)
    native = mf_adapter.native_rows(report_path)
    projected = [mf_adapter.project(row) for row in native]
    assert len(projected) == 3
    assert all(row.category == report["category"] == "BASELINE" for row in projected)
    assert all(row.date == "" and row.extra["role_model"] is None for row in projected)
    assert all(row.attestation_verified for row in projected)
    assert len(report["native_provenance"]["inputs"]) == 3


def test_actual_eval_producer_snapshot_round_trips_with_native_reps(tmp_path, monkeypatch):
    app_root, _, producer = _app_tree(tmp_path)
    source = tmp_path / "external-fixture/question_ledger.jsonl"
    _jsonl(source, [
        {"suite": "synthetic", "qid": "q1", "correct": True, "error": False,
         "calibration_id": "run-a"},
        {"suite": "synthetic", "qid": "q1", "correct": False, "error": False,
         "calibration_id": "run-b"},
    ])
    inputs: list[dict] = []
    rows, warnings = producer.load_rows([source], input_manifest=inputs)
    config = producer.AuditConfig()
    report = producer.build_report(rows, config, [str(source)], warnings)
    report_path = app_root / "data/analysis/synthetic-eval.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = producer._seal_report(report, inputs, report_path)
    report_path.write_text(json.dumps(report, sort_keys=True))

    monkeypatch.setattr(eval_adapter, "ORCHESTRATOR", app_root)
    native = eval_adapter.native_rows(report_path)
    projected = {row["metric"]: eval_adapter.project(row) for row in native}
    assert set(projected) == {"pass_rate", "mde", "run_spread", "flip_rate"}
    assert all(row.category == report["category"] == "BASELINE" for row in projected.values())
    assert projected["pass_rate"].reps == 2
    assert projected["mde"].reps == 1
    assert projected["run_spread"].reps == 2
    assert projected["flip_rate"].reps == 1
    assert all(row.attestation_verified for row in projected.values())

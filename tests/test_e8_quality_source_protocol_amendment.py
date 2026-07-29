"""Executable coverage for the human-only E8 scorer amendment."""

from __future__ import annotations

import importlib.util
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest
import yaml


ROOT = Path("/mnt/raid0/llm/epyc-root")
SCRIPT = ROOT / "artifacts/operator/amend_e8_quality_source_protocol_20260726.sh"
HELPER_PATH = ROOT / "artifacts/operator/e8_quality_source_amendment.py"
DECISION = ROOT / "artifacts/operator/e8_quality_source_protocol_amendment_20260726.md"
MANIFEST = ROOT / "artifacts/operator/e8_quality_source_protocol_amendment_manifest_20260726.json"

spec = importlib.util.spec_from_file_location("e8_quality_source_amendment", HELPER_PATH)
assert spec is not None and spec.loader is not None
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)


REAL_YAML = """\
suite: real_suite_v1
questions:
- id: real_suite_v1_0043
  tier: 2
  prompt: What quantum volume?
  expected: '256'
  scoring_method: exact_match
  scoring_config:
    extract_pattern: \\d+
- id: real_unrelated
  tier: 2
  prompt: Keep me
  expected: keep
  scoring_method: substring
  scoring_config: {}
"""

LONG_YAML = """\
suite: long_context
questions:
  - id: needle_039
    tier: 2
    prompt: What quantum volume?
    expected: "256"
    scoring_method: exact_match
    scoring_config:
      extract_pattern: "\\\\d+"
  - id: long_unrelated
    tier: 2
    prompt: Keep me too
    expected: keep
    scoring_method: substring
    scoring_config: {}
"""


def _pool_text() -> str:
    rows = [
        {
            "__pool_metadata__": True,
            "generated_at": "before",
            "total_questions": 3,
            "suites": {"long_context": 1, "real_suite_v1": 1, "other": 1},
        },
        {
            "id": "needle_039",
            "suite": "long_context",
            "prompt": "What quantum volume?",
            "expected": "256",
            "tier": 2,
            "scoring_method": "exact_match",
            "scoring_config": {"extract_pattern": r"\d+"},
        },
        {
            "id": "real_suite_v1_0043",
            "suite": "real_suite_v1",
            "prompt": "What quantum volume?",
            "expected": "256",
            "tier": 2,
            "scoring_method": "exact_match",
            "scoring_config": {"extract_pattern": r"\d+"},
        },
        {
            "id": "other_001",
            "suite": "other",
            "prompt": "Unrelated",
            "expected": "same",
            "tier": 2,
            "scoring_method": "substring",
            "scoring_config": {},
        },
    ]
    return "".join(json.dumps(row) + "\n" for row in rows)


FAKE_BUILDER = r'''#!/usr/bin/env python3
import json
from pathlib import Path
import sys
import yaml

root = Path(__file__).resolve().parents[2]
output = Path(sys.argv[sys.argv.index("--output") + 1])
pool = root / "benchmarks/prompts/question_pool.jsonl"
patterns = {}
for suite, name in (("real_suite_v1", "real_suite_v1.yaml"), ("long_context", "long_context.yaml")):
    source = yaml.safe_load((root / "benchmarks/prompts/debug" / name).read_text())
    for row in source["questions"]:
        patterns[(suite, row["id"])] = row.get("scoring_config", {}).get("extract_pattern")
rows = []
for raw in pool.read_text().split("\n"):
    if not raw:
        continue
    row = json.loads(raw)
    if row.get("__pool_metadata__"):
        row["generated_at"] = "after"
    key = (row.get("suite"), row.get("id"))
    if key in patterns and key in {
        ("real_suite_v1", "real_suite_v1_0043"),
        ("long_context", "needle_039"),
    }:
        row["scoring_config"]["extract_pattern"] = patterns[key]
    if (root / "inject_unrelated_drift").exists() and row.get("id") == "other_001":
        row["prompt"] = "DRIFT"
    rows.append(row)
output.write_text("".join(json.dumps(row) + "\n" for row in rows))
'''


def _proposal() -> dict[str, Any]:
    protocol = {key: {} for key in helper.PROTOCOL_KEYS}
    protocol.update(
        {
            "protocol_id": helper.PROTOCOL_ID,
            "seed": 42,
            "repetitions": 3,
            "generation_concurrency": 3,
            "scoring_concurrency": 3,
            "baseline_mode": "direct_core_only_v1",
            "route_policy": "frontdoor_only",
            "selected_ports": [],
            "expected_probe_groups": [],
            "tiers": {
                "1": {
                    "core_id": "core_v2",
                    "n": 50,
                    "dataset_sha256": "1" * 64,
                    "scoring_vector_sha256": "2" * 64,
                    "vector_sha256": "3" * 64,
                },
                "2": {
                    "core_id": "legacy_pool_t2_seed_42_n500",
                    "n": 500,
                    "dataset_sha256": "4" * 64,
                    "scoring_vector_sha256": "5" * 64,
                    "vector_sha256": "6" * 64,
                },
            },
        }
    )
    return {
        "schema": helper.PROPOSAL_SCHEMA,
        "era": helper.ERA,
        "protocol": protocol,
        "t1_core_path": "/tmp/core.json",
        "t1_core_file_sha256": "7" * 64,
        "expected_probe_groups": [],
        "acceptance": {},
    }


@pytest.fixture
def temp_paths(tmp_path: Path) -> helper.AmendmentPaths:
    root = tmp_path / "root"
    research = tmp_path / "research"
    orchestrator = tmp_path / "orchestrator"
    real = research / "benchmarks/prompts/debug/real_suite_v1.yaml"
    long = research / "benchmarks/prompts/debug/long_context.yaml"
    pool = research / "benchmarks/prompts/question_pool.jsonl"
    builder = research / "scripts/benchmark/question_pool.py"
    runner = orchestrator / "scripts/benchmark/run_e8_quality_baseline_reseed.py"
    for path in (real, long, pool, builder, runner):
        path.parent.mkdir(parents=True, exist_ok=True)
    real.write_text(REAL_YAML, encoding="utf-8")
    long.write_text(LONG_YAML, encoding="utf-8")
    pool.write_text(_pool_text(), encoding="utf-8")
    builder.write_text(FAKE_BUILDER, encoding="utf-8")
    runner.write_text("# test runner\n", encoding="utf-8")
    root.mkdir()
    return helper.AmendmentPaths(
        root=root,
        research=research,
        orchestrator=orchestrator,
        real=real,
        long=long,
        pool=pool,
        builder=builder,
        build_driver=builder,
        regenerator=builder,
        runner=runner,
        research_python=Path(sys.executable),
        orchestrator_python=Path(sys.executable),
        pool_python=Path(sys.executable),
        hf_home=tmp_path / "hf-home",
        vl_prefix=tmp_path / "vl-prefix",
    )


def _run_temp_transaction(
    paths: helper.AmendmentPaths,
    transaction: Path,
    **kwargs: Any,
) -> Path:
    return helper.run_transaction(
        paths,
        transaction,
        proposal_factory=lambda _paths: _proposal(),
        proposal_verifier=lambda proposal: (
            None
            if proposal["protocol"]["tiers"]["2"]["n"] == 500
            else pytest.fail("wrong T2 n")
        ),
        **kwargs,
    )


def _git_commit(repo: Path) -> str:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "E8 Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _cli_fixture(
    paths: helper.AmendmentPaths,
) -> tuple[Path, dict[str, str], Path]:
    canonical_build_driver = (
        paths.research
        / "benchmarks/prompts/pool_rebuild_a3_20260721/build_driver.py"
    )
    canonical_build_driver.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(paths.builder, canonical_build_driver)
    artifact_sources = {
        "artifacts/operator/e8_quality_source_amendment.py": HELPER_PATH,
        "artifacts/operator/e8_quality_pool_regenerator.py": ROOT
        / "artifacts/operator/e8_quality_pool_regenerator.py",
        "artifacts/operator/e8_quality_source_protocol_amendment_20260726.md": DECISION,
        "tests/test_e8_quality_source_protocol_amendment.py": Path(__file__),
    }
    wrapper = paths.root / "artifacts/operator/amend_e8_quality_source_protocol_20260726.sh"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCRIPT, wrapper)
    for relative, source in artifact_sources.items():
        destination = paths.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    paths.hf_home.mkdir()
    paths.vl_prefix.mkdir()

    heads = {
        "epyc_root": _git_commit(paths.root),
        "epyc_inference_research": _git_commit(paths.research),
        "epyc_orchestrator": _git_commit(paths.orchestrator),
    }
    manifest = {
        "schema": helper.SCHEMA,
        "status": "proposal_only_unattested",
        "decision": "AMEND-E8-QUALITY-SCORER-SOURCE-20260726",
        "operator_token": "AMEND-E8-QUALITY-SCORER-SOURCE-20260726",
        "era": helper.ERA,
        "protocol_id": helper.PROTOCOL_ID,
        "repairs": [
            {
                "field": "scoring_config.extract_pattern",
                "from": r"\d+",
                "id": "real_suite_v1_0043",
                "source": "benchmarks/prompts/debug/real_suite_v1.yaml",
                "suite": "real_suite_v1",
                "to": r"(\d+)",
            },
            {
                "field": "scoring_config.extract_pattern",
                "from": r"\d+",
                "id": "needle_039",
                "source": "benchmarks/prompts/debug/long_context.yaml",
                "suite": "long_context",
                "to": r"(\d+)",
            },
        ],
        "repository_heads": heads,
        "prestate_sha256": {
            "source_real": helper.sha256_path(paths.real),
            "source_long": helper.sha256_path(paths.long),
            "activated_pool": helper.sha256_path(paths.pool),
            "pool_builder": helper.sha256_path(paths.builder),
            "pool_build_driver": helper.sha256_path(canonical_build_driver),
            "runner": helper.sha256_path(paths.runner),
        },
        "artifact_sha256": {
            relative: helper.sha256_path(paths.root / relative)
            for relative in artifact_sources
        },
    }
    manifest_path = (
        paths.root
        / "artifacts/operator/e8_quality_source_protocol_amendment_manifest_20260726.json"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    transaction_parent = (
        paths.root / "artifacts/operator/e8_quality_source_amendment_transactions"
    )
    transaction_parent.mkdir()
    env = {
        **os.environ,
        "EPYC_ROOT": str(paths.root),
        "EPYC_RESEARCH": str(paths.research),
        "EPYC_ORCH": str(paths.orchestrator),
        "EPYC_RESEARCH_PYTHON": sys.executable,
        "EPYC_ORCH_PYTHON": sys.executable,
        "EPYC_POOL_PYTHON": sys.executable,
        "EPYC_E8_HF_HOME": str(paths.hf_home),
        "EPYC_E8_VL_PREFIX": str(paths.vl_prefix),
        "E8_AMENDMENT_TEST_MODE": "1",
        "E8_AMENDMENT_MANIFEST": str(manifest_path),
        "E8_AMENDMENT_MANIFEST_SHA256": helper.sha256_path(manifest_path),
    }
    return wrapper, env, transaction_parent


def _create_replace_before_applied_crash(
    paths: helper.AmendmentPaths,
    transaction: Path,
) -> None:
    transaction.mkdir()
    journal_path = transaction / "transaction.json"
    journal = {
        "schema": helper.JOURNAL_SCHEMA,
        "state": "applying",
        "created_at": helper.utc_now(),
        "updated_at": helper.utc_now(),
        "failure": None,
        "files": {},
    }
    for name, destination, qid in (
        ("real", paths.real, "real_suite_v1_0043"),
        ("long", paths.long, "needle_039"),
    ):
        backup = transaction / f"{name}.before"
        backup.write_bytes(destination.read_bytes())
        candidate = transaction / f"{name}.candidate"
        candidate.write_text(
            helper.transform_source_text(destination.read_text(), qid)
        )
        helper._add_file_record(
            journal_path,
            journal,
            name,
            destination,
            backup,
            candidate,
        )
    record = journal["files"]["real"]
    record["replace_intent_at"] = helper.utc_now()
    os.replace(transaction / "real.candidate", paths.real)
    helper.write_json_atomic(journal_path, journal)
    assert record["applied"] is False


def test_transform_handles_real_and_indented_needle_with_one_backslash() -> None:
    real = helper.transform_source_text(REAL_YAML, "real_suite_v1_0043")
    long = helper.transform_source_text(LONG_YAML, "needle_039")
    for repaired, qid in ((real, "real_suite_v1_0043"), (long, "needle_039")):
        row = next(
            row for row in yaml.safe_load(repaired)["questions"] if row["id"] == qid
        )
        pattern = row["scoring_config"]["extract_pattern"]
        assert pattern == r"(\d+)"
        assert len(pattern) == 5
        assert "'(\\d+)'" in repaired
        assert "'(\\\\d+)'" not in repaired


def test_build_paths_preserves_venv_python_symlink(tmp_path: Path) -> None:
    base = tmp_path / "base-python"
    base.write_text("#!/bin/sh\n", encoding="utf-8")
    base.chmod(0o755)
    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(base)
    args = helper.parse_args(
        [
            "--root", str(tmp_path), "--research", str(tmp_path),
            "--orchestrator", str(tmp_path),
            "--research-python", str(venv_python),
            "--orchestrator-python", str(venv_python),
            "--pool-python", str(venv_python),
            "--hf-home", str(tmp_path), "--vl-prefix", str(tmp_path),
            "--manifest", str(tmp_path / "manifest.json"), "--validate-only",
        ]
    )
    paths = helper.build_paths(args)
    assert paths.pool_python == venv_python.absolute()
    assert paths.pool_python != venv_python.resolve()


def test_pool_regenerator_deterministically_replays_banked_pool(tmp_path: Path) -> None:
    research = tmp_path / "research"
    debug = research / "benchmarks/prompts/debug"
    debug.mkdir(parents=True)
    (debug / "real_suite_v1.yaml").write_text(
        helper.transform_source_text(REAL_YAML, "real_suite_v1_0043"),
        encoding="utf-8",
    )
    (debug / "long_context.yaml").write_text(
        helper.transform_source_text(LONG_YAML, "needle_039"),
        encoding="utf-8",
    )
    pool = research / "benchmarks/prompts/question_pool.jsonl"
    pool.write_text(_pool_text(), encoding="utf-8")
    vl_prefix = tmp_path / "vl"
    vl_prefix.mkdir()
    output = tmp_path / "candidate.jsonl"
    stage = tmp_path / "stage"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "artifacts/operator/e8_quality_pool_regenerator.py"),
            "--research",
            str(research),
            "--output",
            str(output),
            "--stage",
            str(stage),
            "--vl-prefix",
            str(vl_prefix),
        ],
        env={
            **os.environ,
            "HF_HUB_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    helper.validate_pool_candidate(pool, output)
    witness = json.loads((stage / "replay-witness.json").read_text())
    assert witness["schema"] == "epyc.e8_quality_pool_deterministic_replay.v1"
    assert {(row["suite"], row["id"]) for row in witness["repairs"]} == set(
        helper.TARGETS.values()
    )


def test_temp_transaction_executes_transform_and_regeneration(
    temp_paths: helper.AmendmentPaths, tmp_path: Path
) -> None:
    journal_path = _run_temp_transaction(temp_paths, tmp_path / "transaction")
    assert json.loads(journal_path.read_text())["state"] == "committed"
    for path, qid in (
        (temp_paths.real, "real_suite_v1_0043"),
        (temp_paths.long, "needle_039"),
    ):
        row = next(row for row in yaml.safe_load(path.read_text())["questions"] if row["id"] == qid)
        assert row["scoring_config"]["extract_pattern"] == r"(\d+)"
    _header, rows = helper.parse_pool(temp_paths.pool)
    repaired = {
        row["id"]: row["scoring_config"]["extract_pattern"]
        for row in rows
        if row["id"] in {"real_suite_v1_0043", "needle_039"}
    }
    assert repaired == {
        "real_suite_v1_0043": r"(\d+)",
        "needle_039": r"(\d+)",
    }


def test_unrelated_regeneration_drift_is_refused_and_rolled_back(
    temp_paths: helper.AmendmentPaths, tmp_path: Path
) -> None:
    before = {
        path: path.read_bytes()
        for path in (temp_paths.real, temp_paths.long, temp_paths.pool)
    }
    (temp_paths.research / "inject_unrelated_drift").touch()
    transaction = tmp_path / "transaction-drift"
    with pytest.raises(helper.AmendmentError, match="unrelated drift"):
        _run_temp_transaction(temp_paths, transaction)
    assert all(path.read_bytes() == payload for path, payload in before.items())
    assert json.loads((transaction / "transaction.json").read_text())["state"] == "rolled_back"


def test_cas_refuses_race_before_replace_without_clobbering_edit(
    temp_paths: helper.AmendmentPaths, tmp_path: Path
) -> None:
    original_real = temp_paths.real.read_bytes()
    concurrent_long = LONG_YAML.replace("Keep me too", "concurrent edit").encode()

    def race(name: str, destination: Path) -> None:
        if name == "long":
            destination.write_bytes(concurrent_long)

    transaction = tmp_path / "transaction-race"
    with pytest.raises(helper.CASMismatch, match="CAS mismatch"):
        _run_temp_transaction(temp_paths, transaction, before_replace=race)
    assert temp_paths.real.read_bytes() == original_real
    assert temp_paths.long.read_bytes() == concurrent_long
    journal = json.loads((transaction / "transaction.json").read_text())
    assert journal["state"] == "manual_recovery_required"
    assert journal["files"]["long"]["rollback_conflict"] is not None


def test_mid_transaction_failure_rolls_back_all_applied_files(
    temp_paths: helper.AmendmentPaths, tmp_path: Path
) -> None:
    before = {
        path: path.read_bytes()
        for path in (temp_paths.real, temp_paths.long, temp_paths.pool)
    }
    transaction = tmp_path / "transaction-midfail"
    with pytest.raises(helper.AmendmentError, match="injected failure after long"):
        _run_temp_transaction(temp_paths, transaction, fail_after="long")
    assert all(path.read_bytes() == payload for path, payload in before.items())
    journal = json.loads((transaction / "transaction.json").read_text())
    assert journal["state"] == "rolled_back"
    assert journal["files"]["real"]["rolled_back"] is True
    assert journal["files"]["long"]["rolled_back"] is True


def test_rollback_never_clobbers_concurrent_edit_to_applied_file(
    temp_paths: helper.AmendmentPaths, tmp_path: Path
) -> None:
    concurrent_real = b"suite: concurrent\nquestions: []\n"

    def race(name: str, _destination: Path) -> None:
        if name == "long":
            temp_paths.real.write_bytes(concurrent_real)

    transaction = tmp_path / "transaction-rollback-race"
    with pytest.raises(helper.AmendmentError, match="injected failure after long"):
        _run_temp_transaction(
            temp_paths,
            transaction,
            before_replace=race,
            fail_after="long",
        )
    assert temp_paths.real.read_bytes() == concurrent_real
    assert temp_paths.long.read_text() == LONG_YAML
    journal = json.loads((transaction / "transaction.json").read_text())
    assert journal["state"] == "manual_recovery_required"
    assert journal["files"]["real"]["rollback_conflict"]["reason"].endswith("left untouched")


def test_journal_intent_closes_replace_before_applied_crash_window(
    temp_paths: helper.AmendmentPaths, tmp_path: Path
) -> None:
    transaction = tmp_path / "transaction-intent"
    transaction.mkdir()
    backup = transaction / "real.before"
    backup.write_bytes(temp_paths.real.read_bytes())
    candidate = transaction / "real.candidate"
    candidate.write_text(
        helper.transform_source_text(
            temp_paths.real.read_text(), "real_suite_v1_0043"
        )
    )
    journal_path = transaction / "transaction.json"
    journal = {
        "schema": helper.JOURNAL_SCHEMA,
        "state": "applying",
        "created_at": helper.utc_now(),
        "updated_at": helper.utc_now(),
        "failure": None,
        "files": {},
    }
    helper._add_file_record(
        journal_path,
        journal,
        "real",
        temp_paths.real,
        backup,
        candidate,
    )
    record = journal["files"]["real"]
    record["replace_intent_at"] = helper.utc_now()
    os.replace(candidate, temp_paths.real)
    helper.write_json_atomic(journal_path, journal)
    assert record["applied"] is False
    assert helper.rollback(journal_path, journal) is True
    assert temp_paths.real.read_bytes() == backup.read_bytes()
    assert json.loads(journal_path.read_text())["state"] == "rolled_back"


def test_proposal_postcheck_requires_exact_shape_hashes_and_t2_membership() -> None:
    proposal = _proposal()
    expected = copy.deepcopy(proposal["protocol"]["tiers"])
    selected = [
        {
            "id": "real_suite_v1_0043",
            "expected": "256",
            "scoring_method": "exact_match",
            "scoring_config": {"extract_pattern": r"(\d+)"},
        },
        {
            "id": "needle_039",
            "expected": "256",
            "scoring_method": "exact_match",
            "scoring_config": {"extract_pattern": r"(\d+)"},
        },
    ]
    helper.verify_proposal_document(proposal, expected, selected)
    proposal["protocol"]["tiers"]["2"]["vector_sha256"] = "0" * 64
    with pytest.raises(helper.AmendmentError, match="hashes differ"):
        helper.verify_proposal_document(proposal, expected, selected)


def test_manifest_binds_script_decision_helper_and_tests() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "proposal_only_unattested"
    assert set(manifest["artifact_sha256"]) == {
        "artifacts/operator/e8_quality_source_amendment.py",
        "artifacts/operator/e8_quality_pool_regenerator.py",
        "artifacts/operator/e8_quality_source_protocol_amendment_20260726.md",
        "tests/test_e8_quality_source_protocol_amendment.py",
    }
    for relative, expected in manifest["artifact_sha256"].items():
        assert helper.sha256_path(ROOT / relative) == expected


def test_wrapper_refuses_tampered_detached_manifest(
    temp_paths: helper.AmendmentPaths,
) -> None:
    wrapper, env, _transaction_parent = _cli_fixture(temp_paths)
    manifest = Path(env["E8_AMENDMENT_MANIFEST"])
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(" ")
    completed = subprocess.run(
        ["bash", str(wrapper), "--validate-only"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert completed.returncode != 0
    assert "manifest SHA-256 mismatch" in completed.stderr


def test_recover_cli_restores_replace_before_applied_crash(
    temp_paths: helper.AmendmentPaths,
) -> None:
    wrapper, env, transaction_parent = _cli_fixture(temp_paths)
    original = temp_paths.real.read_bytes()
    transaction = transaction_parent / "crash-after-replace"
    _create_replace_before_applied_crash(temp_paths, transaction)
    assert temp_paths.real.read_bytes() != original
    completed = subprocess.run(
        [
            "bash",
            str(wrapper),
            "--recover",
            str(transaction),
            "--attest",
            "RECOVER-E8-QUALITY-SOURCE-20260726",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    assert temp_paths.real.read_bytes() == original
    journal = json.loads((transaction / "transaction.json").read_text())
    assert journal["state"] == "rolled_back"
    assert journal["files"]["real"]["rolled_back"] is True


def test_recover_cli_preserves_conflict_and_requires_manual_recovery(
    temp_paths: helper.AmendmentPaths,
) -> None:
    wrapper, env, transaction_parent = _cli_fixture(temp_paths)
    transaction = transaction_parent / "crash-with-conflict"
    _create_replace_before_applied_crash(temp_paths, transaction)
    concurrent = b"suite: concurrent\nquestions: []\n"
    temp_paths.real.write_bytes(concurrent)
    completed = subprocess.run(
        [
            "bash",
            str(wrapper),
            "--recover",
            str(transaction),
            "--attest",
            "RECOVER-E8-QUALITY-SOURCE-20260726",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert completed.returncode != 0
    assert "manual_recovery_required" in completed.stderr
    assert temp_paths.real.read_bytes() == concurrent
    journal = json.loads((transaction / "transaction.json").read_text())
    assert journal["state"] == "manual_recovery_required"
    assert journal["files"]["real"]["rollback_conflict"] is not None


def test_plan_and_validate_only_do_not_mutate_authoritative_files() -> None:
    tracked = [
        Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/debug/real_suite_v1.yaml"),
        Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/debug/long_context.yaml"),
        Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"),
    ]
    before = {path: helper.sha256_path(path) for path in tracked}
    plan = subprocess.run(
        ["bash", str(SCRIPT), "--plan"], text=True, capture_output=True, check=False
    )
    validate = subprocess.run(
        ["bash", str(SCRIPT), "--validate-only"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert plan.returncode == 0, plan.stderr
    assert validate.returncode == 0, validate.stderr
    assert "no authoritative data changed" in validate.stdout
    assert {path: helper.sha256_path(path) for path in tracked} == before

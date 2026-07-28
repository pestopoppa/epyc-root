"""Adversarial coverage for the receipt-only E8 final-c1 authorization."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = REPO_ROOT / "artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.sh"
TOKEN = "RATIFY-E8-FINAL-C1-RETRY-20260728"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_source_tree(root: Path) -> str:
    source_hashes = {}
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            source_hashes[path.relative_to(root).as_posix()] = _sha256(path)
    return hashlib.sha256(
        json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


@pytest.fixture
def amendment_fixture(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "root"
    evidence = tmp_path / "immutable-race"
    orch = tmp_path / "orchestrator"
    (root / "artifacts/operator").mkdir(parents=True)
    shutil.copyfile(SOURCE_SCRIPT, root / "artifacts/operator" / SOURCE_SCRIPT.name)
    _git("init", "-q", cwd=root)
    _git("config", "user.email", "test@example.invalid", cwd=root)
    _git("config", "user.name", "E8 Amendment Test", cwd=root)
    _git("add", ".", cwd=root)
    _git("commit", "-qm", "fixture", cwd=root)

    evidence.mkdir()
    plan = {
        "schema": "epyc.e8_quality_v5_partial_r2_race_retry_plan.v1",
        "generation_ordinals": [97, 203, 279],
        "race_retry_ordinals": [97, 203, 279],
        "generation_concurrency": 3,
        "failed_source_tree_sha256": "a" * 64,
    }
    proposal = {
        "schema": "epyc.e8_quality_v5_partial_r2_race_retry_proposal.v1",
        "output_namespace": str(evidence),
        "source_tree_sha256": "b" * 64,
        "generation_concurrency": 3,
    }
    failures = {
        "disposition": "failed_closed_no_automatic_retry",
        "failures": [
            {"ordinal": 97, "sidecar_sha256": "c" * 64},
            {"ordinal": 279, "sidecar_sha256": "d" * 64},
        ],
    }
    plan_path = evidence / "partial_r2_plan.json"
    proposal_path = evidence / "recovery_proposal.json"
    failures_path = evidence / "generation_failed_attempts.T2.r2.jsonl"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    failures_path.write_text(json.dumps(failures) + "\n", encoding="utf-8")

    runner = orch / "scripts/benchmark/final_c1_retry.py"
    validator = orch / "scripts/benchmark/final_c1_validator.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("FINAL_C1 = True\n", encoding="utf-8")
    validator.write_text("VALIDATOR = True\n", encoding="utf-8")
    _git("init", "-q", cwd=orch)
    _git("config", "user.email", "test@example.invalid", cwd=orch)
    _git("config", "user.name", "E8 Instrument Test", cwd=orch)
    _git("add", ".", cwd=orch)
    _git("commit", "-qm", "pinned runner", cwd=orch)

    env = {
        "E8_C1_AMENDMENT_TEST_MODE": "1",
        "EPYC_ROOT": str(root),
        "E8_C1_EVIDENCE": str(evidence),
        "EPYC_ORCHESTRATOR": str(orch),
        "E8_C1_PYTHON": sys.executable,
        "E8_C1_EXPECTED_PLAN_SHA256": _sha256(plan_path),
        "E8_C1_EXPECTED_PROPOSAL_SHA256": _sha256(proposal_path),
        "E8_C1_EXPECTED_FAILURES_SHA256": _sha256(failures_path),
        "E8_C1_EXPECTED_PLAN_TREE_SHA256": "a" * 64,
        "E8_C1_EXPECTED_PROPOSAL_TREE_SHA256": "b" * 64,
        "E8_C1_EXPECTED_SOURCE_TREE_SHA256": _canonical_source_tree(evidence),
        "E8_C1_EXPECTED_FAILED_SIDECARS": f"97:{'c' * 64},279:{'d' * 64}",
        "E8_C1_EXPECTED_ORCH_COMMIT": _git("rev-parse", "HEAD", cwd=orch),
        "E8_C1_EXPECTED_ORCH_TREE": _git("rev-parse", "HEAD^{tree}", cwd=orch),
        "E8_C1_RUNNER_REL": "scripts/benchmark/final_c1_retry.py",
        "E8_C1_EXPECTED_RUNNER_SHA256": _sha256(runner),
        "E8_C1_VALIDATOR_REL": "scripts/benchmark/final_c1_validator.py",
        "E8_C1_EXPECTED_VALIDATOR_SHA256": _sha256(validator),
    }
    return {"root": root, "evidence": evidence, "script": root / "artifacts/operator" / SOURCE_SCRIPT.name, "env": env}


def _run(fixture: dict[str, object], *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(fixture["script"]), *args],
        cwd="/",
        text=True,
        capture_output=True,
        check=False,
        env=os.environ | fixture["env"] | extra_env,  # type: ignore[operator]
    )


def _receipt(fixture: dict[str, object]) -> Path:
    return fixture["root"] / "artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.json"  # type: ignore[operator]


def test_validate_only_is_cwd_independent_and_read_only(amendment_fixture: dict[str, object]) -> None:
    evidence = amendment_fixture["evidence"]
    before = {path.name: _sha256(path) for path in Path(evidence).iterdir()}
    result = _run(amendment_fixture, "--validate-only")
    assert result.returncode == 0, result.stderr
    assert "preflight-valid" in result.stdout
    assert {path.name: _sha256(path) for path in Path(evidence).iterdir()} == before
    assert not _receipt(amendment_fixture).exists()


def test_attestation_writes_only_the_exact_narrow_contract(amendment_fixture: dict[str, object]) -> None:
    result = _run(amendment_fixture, "--attest", TOKEN)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(_receipt(amendment_fixture).read_text(encoding="utf-8"))
    assert receipt["schema"] == "epyc.operator_e8_quality_final_c1_retry_amendment.v1"
    assert receipt["source"] == {
        "path": str(amendment_fixture["evidence"]),
        "tree_sha256": _canonical_source_tree(Path(amendment_fixture["evidence"])),
    }
    assert receipt["authorization"] == {
        "tier": 2,
        "repetition": 2,
        "ordinals": [97, 279],
        "qids": ["leval_codeU_269", "leval_review_summ_382"],
        "order": "sequential",
        "generation_concurrency": 1,
        "request_timeout_s": 300,
        "region_claim_regions": ["q3"],
        "runtime_preconditions": ["held_q3_claim", "clean_runtime_watcher"],
        "success_disposition": "clean_rows_continue_existing_clean_500_finalizer",
        "repeated_failure_disposition": "terminal_failed_no_admission",
        "no_auto_retry": True,
        "no_timeout_increase": True,
    }
    assert receipt["non_authorizations"] == {
        "no_state_write": True,
        "no_lineup_mutation": True,
        "no_inference_by_ratifier": True,
    }


def test_refuses_tampered_failure_namespace_without_receipt(amendment_fixture: dict[str, object]) -> None:
    failures = Path(amendment_fixture["evidence"]) / "generation_failed_attempts.T2.r2.jsonl"
    failures.write_text('{"disposition":"failed_closed_no_automatic_retry","failures":[]}\n', encoding="utf-8")
    result = _run(amendment_fixture, "--validate-only")
    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_nonmanifest_evidence_tree_mutation_without_receipt(amendment_fixture: dict[str, object]) -> None:
    (Path(amendment_fixture["evidence"]) / "unexpected.txt").write_text("mutation\n", encoding="utf-8")
    result = _run(amendment_fixture, "--validate-only")
    assert result.returncode != 0
    assert "canonical source tree differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_evidence_symlink_without_receipt(amendment_fixture: dict[str, object]) -> None:
    evidence = Path(amendment_fixture["evidence"])
    (evidence / "nested").mkdir()
    (evidence / "nested" / "link").symlink_to(evidence / "partial_r2_plan.json")
    result = _run(amendment_fixture, "--validate-only")
    assert result.returncode != 0
    assert "contains symlink" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_unpinned_orchestrator_instrument_without_receipt(amendment_fixture: dict[str, object]) -> None:
    result = _run(amendment_fixture, "--validate-only", E8_C1_EXPECTED_RUNNER_SHA256="0" * 64)
    assert result.returncode != 0
    assert "runner hash differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_wrong_token_and_duplicate_attestation_fail_closed(amendment_fixture: dict[str, object]) -> None:
    wrong = _run(amendment_fixture, "--attest", "wrong")
    assert wrong.returncode != 0
    assert not _receipt(amendment_fixture).exists()
    assert _run(amendment_fixture, "--attest", TOKEN).returncode == 0
    duplicate = _run(amendment_fixture, "--attest", TOKEN)
    assert duplicate.returncode != 0
    assert "already exists" in duplicate.stderr


def test_test_mode_cannot_target_canonical_root_or_evidence(amendment_fixture: dict[str, object]) -> None:
    result = _run(amendment_fixture, "--validate-only", EPYC_ROOT="/mnt/raid0/llm/epyc-root")
    assert result.returncode != 0
    assert "test mode refuses canonical" in result.stderr


def test_production_defaults_refuse_unresolved_runner_pins() -> None:
    text = SOURCE_SCRIPT.read_text(encoding="utf-8")
    assert "__ORCHESTRATOR_COMMIT_TO_BE_SUPPLIED__" in text
    assert "unresolved or malformed instrument pin" in text
    assert "request_timeout_s\": 300" in text
    assert "no_timeout_increase\": True" in text
    assert 'PYTHON="/usr/bin/python3"' in text
    assert "durable_fsync" in text

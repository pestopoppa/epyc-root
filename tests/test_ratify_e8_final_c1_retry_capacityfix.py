"""Adversarial coverage for the receipt-only E8 final-c1 authorization."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = REPO_ROOT / "artifacts/operator/ratify_e8_final_c1_retry_capacityfix_20260729.sh"
TOKEN = "RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729"


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
    _git("config", "user.name", "E8 Superseding Ratifier Test", cwd=root)
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
    recovery_helper = orch / "scripts/benchmark/recover_e8_quality_baseline_v5_partial_r2.py"
    validator = orch / "scripts/benchmark/final_c1_validator.py"
    wrapper = (
        orch
        / "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
    )
    applier_adapter = (
        orch
        / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
    )
    canonical_applier = root / "artifacts/operator/apply_e8_quality_baseline_state.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("FINAL_C1 = True\n", encoding="utf-8")
    recovery_helper.write_text("RECOVERY_HELPER = True\n", encoding="utf-8")
    validator.write_text("VALIDATOR = True\n", encoding="utf-8")
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    applier_adapter.write_text("APPLIER_ADAPTER = True\n", encoding="utf-8")
    canonical_applier.write_text("CANONICAL_APPLIER = True\n", encoding="utf-8")
    original = root / "artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.json"
    original.write_text(
        json.dumps(
            {
                "schema": "epyc.operator_e8_quality_final_c1_retry_amendment.v1",
                "status": "ratified",
                "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-20260728",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    superseded = root / "artifacts/operator/ratify_e8_final_c1_retry_superseding_20260729.json"
    _git("add", ".", cwd=root)
    _git("commit", "-qm", "canonical applier fixture", cwd=root)
    _git("init", "-q", cwd=orch)
    _git("config", "user.email", "test@example.invalid", cwd=orch)
    _git("config", "user.name", "E8 Instrument Test", cwd=orch)
    _git("add", ".", cwd=orch)
    _git("commit", "-qm", "pinned runner", cwd=orch)
    superseded.write_text(
        json.dumps(
            {
                "schema": "epyc.operator_e8_quality_final_c1_retry_superseding.v1",
                "status": "ratified",
                "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-SUPERSEDING-20260729",
                "authorization": {
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
                },
                "non_authorizations": {
                    "no_inference_by_ratifier": True,
                    "no_lineup_mutation": True,
                    "no_state_write": True,
                },
                "supersedes": {
                    "path": str(original),
                    "sha256": _sha256(original),
                    "schema": "epyc.operator_e8_quality_final_c1_retry_amendment.v1",
                    "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-20260728",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    env = {
        "E8_C1_CAPACITYFIX_TEST_MODE": "1",
        "EPYC_ROOT": str(root),
        "E8_C1_CAPACITYFIX_EVIDENCE": str(evidence),
        "EPYC_ORCHESTRATOR": str(orch),
        "E8_C1_CAPACITYFIX_PYTHON": sys.executable,
        "E8_C1_CAPACITYFIX_TRUST_LOCK": str(root / "artifacts/operator/.measurement-trust.lock"),
        "E8_C1_CAPACITYFIX_EXPECTED_PLAN_SHA256": _sha256(plan_path),
        "E8_C1_CAPACITYFIX_EXPECTED_PROPOSAL_SHA256": _sha256(proposal_path),
        "E8_C1_CAPACITYFIX_EXPECTED_FAILURES_SHA256": _sha256(failures_path),
        "E8_C1_CAPACITYFIX_EXPECTED_PLAN_TREE_SHA256": "a" * 64,
        "E8_C1_CAPACITYFIX_EXPECTED_PROPOSAL_TREE_SHA256": "b" * 64,
        "E8_C1_CAPACITYFIX_EXPECTED_SOURCE_TREE_SHA256": _canonical_source_tree(evidence),
        "E8_C1_CAPACITYFIX_EXPECTED_FAILED_SIDECARS": f"97:{'c' * 64},279:{'d' * 64}",
        "E8_C1_CAPACITYFIX_EXPECTED_ORCH_COMMIT": _git("rev-parse", "HEAD", cwd=orch),
        "E8_C1_CAPACITYFIX_EXPECTED_ORCH_TREE": _git("rev-parse", "HEAD^{tree}", cwd=orch),
        "E8_C1_CAPACITYFIX_RUNNER_REL": "scripts/benchmark/final_c1_retry.py",
        "E8_C1_CAPACITYFIX_EXPECTED_RUNNER_SHA256": _sha256(runner),
        "E8_C1_CAPACITYFIX_RECOVERY_HELPER_REL": "scripts/benchmark/recover_e8_quality_baseline_v5_partial_r2.py",
        "E8_C1_CAPACITYFIX_EXPECTED_RECOVERY_HELPER_SHA256": _sha256(recovery_helper),
        "E8_C1_CAPACITYFIX_VALIDATOR_REL": "scripts/benchmark/final_c1_validator.py",
        "E8_C1_CAPACITYFIX_EXPECTED_VALIDATOR_SHA256": _sha256(validator),
        "E8_C1_CAPACITYFIX_WRAPPER_REL": str(wrapper.relative_to(orch)),
        "E8_C1_CAPACITYFIX_EXPECTED_WRAPPER_SHA256": _sha256(wrapper),
        "E8_C1_CAPACITYFIX_APPLIER_ADAPTER_REL": str(applier_adapter.relative_to(orch)),
        "E8_C1_CAPACITYFIX_EXPECTED_APPLIER_ADAPTER_SHA256": _sha256(applier_adapter),
        "E8_C1_CAPACITYFIX_CANONICAL_APPLIER_REL": str(canonical_applier.relative_to(root)),
        "E8_C1_CAPACITYFIX_EXPECTED_CANONICAL_APPLIER_SHA256": _sha256(canonical_applier),
        "E8_C1_CAPACITYFIX_EXPECTED_SUPERSEDED_RECEIPT_SHA256": _sha256(superseded),
        "E8_C1_CAPACITYFIX_EXPECTED_ORIGINAL_RECEIPT_SHA256": _sha256(original),
    }
    return {"root": root, "evidence": evidence, "script": root / "artifacts/operator" / SOURCE_SCRIPT.name, "env": env}


def _run(fixture: dict[str, object], *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(fixture["script"]), *args],
        cwd="/",
        text=True,
        capture_output=True,
        check=False,
        env=os.environ | fixture["env"] | extra_env,  # type: ignore[operator]
    )


def _receipt(fixture: dict[str, object]) -> Path:
    return fixture["root"] / "artifacts/operator/ratify_e8_final_c1_retry_capacityfix_20260729.json"  # type: ignore[operator]


def _superseded_receipt(fixture: dict[str, object]) -> Path:
    return fixture["root"] / "artifacts/operator/ratify_e8_final_c1_retry_superseding_20260729.json"  # type: ignore[operator]


def _original_receipt(fixture: dict[str, object]) -> Path:
    return fixture["root"] / "artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.json"  # type: ignore[operator]


def _lock(fixture: dict[str, object]) -> Path:
    return Path(fixture["env"]["E8_C1_CAPACITYFIX_TRUST_LOCK"])  # type: ignore[index]


def _lock_is_held(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("r+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return False


def test_validate_only_is_cwd_independent_and_read_only(amendment_fixture: dict[str, object]) -> None:
    evidence = amendment_fixture["evidence"]
    before = {path.name: _sha256(path) for path in Path(evidence).iterdir()}
    for command in ("--plan", "--validate-only"):
        result = _run(amendment_fixture, command)
        assert result.returncode == 0, result.stderr
        assert "preflight-valid" in result.stdout
    assert {path.name: _sha256(path) for path in Path(evidence).iterdir()} == before
    assert not _receipt(amendment_fixture).exists()


def test_attestation_writes_only_the_exact_narrow_contract(amendment_fixture: dict[str, object]) -> None:
    result = _run(amendment_fixture, "--attest", TOKEN)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(_receipt(amendment_fixture).read_text(encoding="utf-8"))
    assert receipt["schema"] == "epyc.operator_e8_quality_final_c1_retry_capacityfix.v1"
    assert receipt["supersedes"] == {
        "path": str(_superseded_receipt(amendment_fixture)),
        "sha256": _sha256(_superseded_receipt(amendment_fixture)),
        "schema": "epyc.operator_e8_quality_final_c1_retry_superseding.v1",
        "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-SUPERSEDING-20260729",
    }
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
    assert receipt["capacity_fix"] == {
        "helper": {
            "path": "scripts/benchmark/recover_e8_quality_baseline_v5_partial_r2.py",
            "sha256": amendment_fixture["env"]["E8_C1_CAPACITYFIX_EXPECTED_RECOVERY_HELPER_SHA256"],  # type: ignore[index]
        },
        "legacy_default_expected_concurrency": 3,
        "final_c1_expected_concurrency": 1,
    }
    assert _lock(amendment_fixture).is_file()


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
    result = _run(amendment_fixture, "--validate-only", E8_C1_CAPACITYFIX_EXPECTED_RUNNER_SHA256="0" * 64)
    assert result.returncode != 0
    assert "runner hash differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_wrong_capacity_helper_pin_without_receipt(
    amendment_fixture: dict[str, object],
) -> None:
    result = _run(
        amendment_fixture,
        "--validate-only",
        E8_C1_CAPACITYFIX_EXPECTED_RECOVERY_HELPER_SHA256="0" * 64,
    )
    assert result.returncode != 0
    assert "recovery helper hash differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_tampered_superseded_receipt_without_receipt(
    amendment_fixture: dict[str, object],
) -> None:
    _superseded_receipt(amendment_fixture).write_text("{}\n", encoding="utf-8")
    result = _run(amendment_fixture, "--validate-only")
    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_tampered_original_receipt_ancestry_without_receipt(
    amendment_fixture: dict[str, object],
) -> None:
    _original_receipt(amendment_fixture).write_text("{}\n", encoding="utf-8")
    result = _run(amendment_fixture, "--validate-only")
    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_wrong_original_ancestry_even_with_matching_test_digest(
    amendment_fixture: dict[str, object],
) -> None:
    predecessor = _superseded_receipt(amendment_fixture)
    receipt = json.loads(predecessor.read_text(encoding="utf-8"))
    receipt["supersedes"]["sha256"] = "0" * 64
    predecessor.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    result = _run(
        amendment_fixture,
        "--validate-only",
        E8_C1_CAPACITYFIX_EXPECTED_SUPERSEDED_RECEIPT_SHA256=_sha256(predecessor),
    )
    assert result.returncode != 0
    assert "superseded receipt ancestry differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_changed_prior_authorization_even_with_matching_test_digest(
    amendment_fixture: dict[str, object],
) -> None:
    predecessor = _superseded_receipt(amendment_fixture)
    receipt = json.loads(predecessor.read_text(encoding="utf-8"))
    receipt["authorization"]["request_timeout_s"] = 301
    predecessor.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    result = _run(
        amendment_fixture,
        "--validate-only",
        E8_C1_CAPACITYFIX_EXPECTED_SUPERSEDED_RECEIPT_SHA256=_sha256(predecessor),
    )
    assert result.returncode != 0
    assert "superseded receipt authorization differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_refuses_wrong_superseded_receipt_schema_even_with_matching_test_digest(
    amendment_fixture: dict[str, object],
) -> None:
    predecessor = _superseded_receipt(amendment_fixture)
    predecessor.write_text(
        json.dumps(
            {
                "schema": "wrong.schema.v1",
                "status": "ratified",
                "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-SUPERSEDING-20260729",
                "supersedes": json.loads(_superseded_receipt(amendment_fixture).read_text())["supersedes"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = _run(
        amendment_fixture,
        "--validate-only",
        E8_C1_CAPACITYFIX_EXPECTED_SUPERSEDED_RECEIPT_SHA256=_sha256(predecessor),
    )
    assert result.returncode != 0
    assert "superseded receipt schema differs" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_wrong_token_and_duplicate_attestation_fail_closed(amendment_fixture: dict[str, object]) -> None:
    wrong = _run(amendment_fixture, "--attest", "wrong")
    assert wrong.returncode != 0
    assert not _receipt(amendment_fixture).exists()
    assert _run(amendment_fixture, "--attest", TOKEN).returncode == 0
    duplicate = _run(amendment_fixture, "--attest", TOKEN)
    assert duplicate.returncode != 0
    assert "already exists" in duplicate.stderr


def test_lock_symlink_is_not_followed_or_modified(amendment_fixture: dict[str, object], tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    marker = sentinel / "marker"
    marker.write_text("unchanged\n", encoding="utf-8")
    _lock(amendment_fixture).symlink_to(sentinel, target_is_directory=True)

    result = _run(amendment_fixture, "--attest", TOKEN)

    assert result.returncode != 0
    assert "Too many levels of symbolic links" in result.stderr
    assert _lock(amendment_fixture).is_symlink()
    assert marker.read_text(encoding="utf-8") == "unchanged\n"
    assert not _receipt(amendment_fixture).exists()


def test_existing_regular_lock_is_reused_without_truncation(amendment_fixture: dict[str, object]) -> None:
    lock = _lock(amendment_fixture)
    lock.write_bytes(b"do-not-truncate\n")

    result = _run(amendment_fixture, "--validate-only")

    assert result.returncode == 0, result.stderr
    assert lock.read_bytes() == b"do-not-truncate\n"
    assert not _receipt(amendment_fixture).exists()


def test_concurrent_attestation_cannot_enter_critical_section(amendment_fixture: dict[str, object]) -> None:
    env = os.environ | amendment_fixture["env"] | {"E8_C1_CAPACITYFIX_TEST_HOLD_TRUST_LOCK_SECONDS": "0.75"}  # type: ignore[operator]
    first = subprocess.Popen(
        ["/bin/bash", str(amendment_fixture["script"]), "--attest", TOKEN],
        cwd="/",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    deadline = time.monotonic() + 3
    while not _lock_is_held(_lock(amendment_fixture)) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert _lock_is_held(_lock(amendment_fixture)), "first attestation never acquired the shared lock"

    second = _run(amendment_fixture, "--attest", TOKEN)
    first_stdout, first_stderr = first.communicate(timeout=5)

    assert second.returncode != 0
    assert "measurement trust-boundary lock is already held" in second.stderr
    assert first.returncode == 0, first_stderr
    assert "receipt created" in first_stdout
    assert _receipt(amendment_fixture).is_file()
    assert _lock(amendment_fixture).is_file()


def test_sigkill_releases_final_c1_measurement_lock(
    amendment_fixture: dict[str, object],
) -> None:
    env = os.environ | amendment_fixture["env"] | {  # type: ignore[operator]
        "E8_C1_CAPACITYFIX_TEST_HOLD_TRUST_LOCK_SECONDS": "30"
    }
    process = subprocess.Popen(
        ["/bin/bash", str(amendment_fixture["script"]), "--validate-only"],
        cwd="/",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    deadline = time.monotonic() + 3
    while not _lock_is_held(_lock(amendment_fixture)) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert _lock_is_held(_lock(amendment_fixture)), "final-c1 ratifier never acquired the lock"

    os.killpg(process.pid, signal.SIGKILL)
    process.communicate(timeout=5)
    assert process.returncode == -signal.SIGKILL
    assert subprocess.run(
        ["ps", "-p", str(process.pid)],
        capture_output=True,
        check=False,
    ).returncode != 0
    assert not _lock_is_held(_lock(amendment_fixture))

    recovered = _run(amendment_fixture, "--validate-only")
    assert recovered.returncode == 0, recovered.stderr
    assert "preflight-valid" in recovered.stdout


def test_candidate_is_private_and_never_created_in_receipt_parent(amendment_fixture: dict[str, object]) -> None:
    env = os.environ | amendment_fixture["env"] | {"E8_C1_CAPACITYFIX_TEST_HOLD_AFTER_CANDIDATE_SECONDS": "0.75"}  # type: ignore[operator]
    process = subprocess.Popen(
        ["/bin/bash", str(amendment_fixture["script"]), "--attest", TOKEN],
        cwd="/",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    time.sleep(0.2)
    assert process.poll() is None
    parent = _receipt(amendment_fixture).parent
    assert list(parent.glob("*.candidate*")) == []

    stdout, stderr = process.communicate(timeout=5)
    assert process.returncode == 0, stderr
    assert "receipt created" in stdout
    assert _lock(amendment_fixture).is_file()


def test_named_candidate_symlink_cannot_substitute_anonymous_receipt_inode(
    amendment_fixture: dict[str, object],
) -> None:
    result = _run(
        amendment_fixture,
        "--attest",
        TOKEN,
        E8_C1_CAPACITYFIX_TEST_REPLACE_CANDIDATE_WITH_SYMLINK="1",
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(_receipt(amendment_fixture).read_text(encoding="utf-8"))
    assert receipt["schema"] == "epyc.operator_e8_quality_final_c1_retry_capacityfix.v1"
    assert _lock(amendment_fixture).is_file()


def test_evidence_alias_path_is_rejected(amendment_fixture: dict[str, object], tmp_path: Path) -> None:
    alias = tmp_path / "evidence-alias"
    alias.symlink_to(amendment_fixture["evidence"], target_is_directory=True)
    result = _run(amendment_fixture, "--validate-only", E8_C1_CAPACITYFIX_EVIDENCE=str(alias))
    assert result.returncode != 0
    assert "not an exact resolved path" in result.stderr
    assert not _receipt(amendment_fixture).exists()


def test_root_and_receipt_parent_alias_path_is_rejected(
    amendment_fixture: dict[str, object], tmp_path: Path
) -> None:
    alias = tmp_path / "root-alias"
    alias.symlink_to(amendment_fixture["root"], target_is_directory=True)
    result = _run(amendment_fixture, "--validate-only", EPYC_ROOT=str(alias))
    assert result.returncode != 0
    assert "not an exact resolved path" in result.stderr


def test_hostile_path_cannot_replace_boundary_commands(
    amendment_fixture: dict[str, object], tmp_path: Path
) -> None:
    hostile = tmp_path / "hostile"
    hostile.mkdir()
    marker = tmp_path / "hostile-git-ran"
    fake_git = hostile / "git"
    fake_git.write_text(f"#!/bin/bash\ntouch {marker}\nexit 99\n", encoding="utf-8")
    fake_git.chmod(0o755)
    result = _run(amendment_fixture, "--validate-only", PATH=str(hostile))
    assert result.returncode == 0, result.stderr
    assert not marker.exists()


def test_test_mode_cannot_target_canonical_root_or_evidence(amendment_fixture: dict[str, object]) -> None:
    result = _run(amendment_fixture, "--validate-only", EPYC_ROOT="/mnt/raid0/llm/epyc-root")
    assert result.returncode != 0
    assert "test mode refuses canonical" in result.stderr


def test_production_defaults_pin_the_reviewed_runner_and_validator() -> None:
    text = SOURCE_SCRIPT.read_text(encoding="utf-8")
    assert "182ccef68389eae80655909463947f66593d7470" in text
    assert "1a13e12375dcab84e7ba113f049349260e45239a" in text
    assert "scripts/benchmark/final_c1_retry.py" in text
    assert "9be0e2c02750f9e9ff26cd16f6940aeaacb0c776dcab4472c023a71725515cca" in text
    assert "scripts/benchmark/recover_e8_quality_baseline_v5_partial_r2.py" in text
    assert "586e6b36ba3e334e25dc64d4cce025ad845c8e1162e3f0ebae92628d6e12317f" in text
    assert "scripts/benchmark/final_c1_validator.py" in text
    assert "b82c49cfa362d75496d5e925d58ae5b11d1d33c3d9d14a6f7f796a6c6bf4e977" in text
    assert "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh" in text
    assert "fca5b8b0e663205e3525098e3997fec76b22533ef8dd7175745acc3e4fc1753c" in text
    assert "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py" in text
    assert "ab8ed499c98eedfb961f790ede2596649d8f6080317145f3b8203ab871080309" in text
    assert "f1e0c0a88edaea5a66dda34ec9a938f8a20daa17491263a44ffff179623d3d61" in text
    assert "epyc.operator_e8_quality_final_c1_retry_capacityfix.v1" in text
    assert "RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729" in text
    assert "ratify_e8_final_c1_retry_capacityfix_20260729.json" in text
    assert "ec2db70c6aa27e1cd3f47930514820a2fc88b75e3704c11c48647c6adbaaeeb6" in text
    assert "51aef2bd0431c8df5050f7985422d9712fc2d1494cfed1d7a3b1a54e5cab121e" in text
    assert "epyc.operator_e8_quality_final_c1_retry_amendment.v1" in text
    assert "_TO_BE_SUPPLIED__" not in text
    assert "request_timeout_s\": 300" in text
    assert "no_timeout_increase\": True" in text
    assert 'PYTHON="/usr/bin/python3"' in text
    assert 'TRUST_LOCK="/run/lock/epyc-measurement-trust-boundary.lock"' in text
    assert ".e8_final_c1_retry_capacityfix.lock" not in text
    assert 'export PATH="/usr/bin:/bin"' in text
    assert "AT_EMPTY_PATH" in text
    assert "O_TMPFILE" in text
    assert '"legacy_default_expected_concurrency": 3' in text
    assert '"final_c1_expected_concurrency": 1' in text

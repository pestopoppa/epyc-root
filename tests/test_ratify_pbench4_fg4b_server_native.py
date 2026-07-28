"""Executable coverage for the human-only P-BENCH-4 amendment transaction."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = REPO_ROOT / "artifacts/operator/ratify_pbench4_fg4b_server_native_20260728.sh"
SOURCE_AMENDMENT = REPO_ROOT / "artifacts/operator/pbench4_fg4b_server_native_protocol_amendment_20260728.md"
TOKEN = "RATIFY-P-BENCH-4-FG4B-20260728"
AUTHORITATIVE_RUNNER = Path(
    "/mnt/raid0/llm/worktrees/fg4b-optimized-server-20260728/"
    "scripts/benchmark/fg4b_a4_cpu_optimized_reanchor.py"
)
AUTHORITATIVE_RUNNER_SHA256 = "f2983a10f6af3290f254c16a7681762a074bafb71fc12df68dbfbcc83043a1b9"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


@pytest.fixture
def transaction_fixture(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "root"
    research = tmp_path / "research"
    operator = root / "artifacts/operator"
    operator.mkdir(parents=True)
    shutil.copyfile(SOURCE_SCRIPT, operator / SOURCE_SCRIPT.name)
    shutil.copyfile(SOURCE_AMENDMENT, operator / SOURCE_AMENDMENT.name)

    measurement = "# Measurement\n\nExisting policy.\n"
    changelog = "# Changelog\n\nExisting entry.\n"
    (root / "MEASUREMENT.md").write_text(measurement, encoding="utf-8")
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    _git("init", "-q", cwd=root)
    _git("config", "user.email", "test@example.invalid", cwd=root)
    _git("config", "user.name", "P-BENCH-4 Test", cwd=root)
    _git("add", ".", cwd=root)
    _git("commit", "-qm", "fixture", cwd=root)

    runner = research / "scripts/benchmark/fg4b_a4_cpu_optimized_reanchor.py"
    runner.parent.mkdir(parents=True)
    runner.write_text(
        '''from __future__ import annotations
import hashlib
import json
from pathlib import Path


EXPECTED_CONTRACT = {
    "protocol_id": "FG-4b/A4-CPU-optimized-server-v1",
    "metric": "llama-server timings.predicted_per_second",
    "metric_direction": "higher_is_better",
    "model": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
    "binary": "/mnt/raid0/llm/llama.cpp/build/bin/llama-server",
    "cpu_list": "0-47,96-143", "physical_regions": ["q0", "q1"],
    "threads": 96, "ctx": 32768, "ubatch": 8192, "np": 1,
    "native_mtp_draft_max": 4, "n_predict": 512, "ignore_eos": True,
    "required_finish_reason": "length", "measured_reps": 5,
    "aggregation": ["median", "median_absolute_deviation"],
    "warmup": {"tokens": 64, "consecutive_samples": 3,
               "relative_tolerance": 0.05, "max_attempts": 8},
    "cold_cache_preparation": {"sync": True, "drop_caches": 3,
                                "after_clean_host_gate": True,
                                "before_server_start": True},
    "per_request_witness": {"exclusive_inference_process_tree": True,
                            "exact_live_affinity": "0-47,96-143"},
    "durable_publish": "fsync_files_and_staging_dir_then_parent_before_and_after_atomic_rename",
}


def validate_protocol_attestation(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "epyc.fg4b_a4_cpu_optimized_server_protocol_review.v1"
    assert payload["status"] == "ratified"
    assert payload["contract"] == EXPECTED_CONTRACT
    amendment = Path(payload["human_amendment"]["path"])
    assert hashlib.sha256(amendment.read_bytes()).hexdigest() == payload["human_amendment"]["sha256"]
    return payload
''',
        encoding="utf-8",
    )
    _git("init", "-q", cwd=research)
    _git("config", "user.email", "test@example.invalid", cwd=research)
    _git("config", "user.name", "P-BENCH-4 Test", cwd=research)
    _git("remote", "add", "origin", "https://example.invalid/fg4b-research.git", cwd=research)
    _git("add", ".", cwd=research)
    _git("commit", "-qm", "hardened fixture", cwd=research)

    amendment = (operator / SOURCE_AMENDMENT.name).read_bytes()
    amended_measurement = measurement.encode() + b"\n" + amendment
    entry = (
        b"- Ratified `P-BENCH-4` for prospective FG-4b single-instance "
        b"server-native speculative decode; it pins the reviewed runner contract "
        b"and preserves prior FG-4b observations as non-decision-grade.\n"
    )
    amended_changelog = changelog.encode() + b"\n" + entry
    runner_bytes = runner.read_bytes()
    env = {
        "P_BENCH_4_TEST_MODE": "1",
        "EPYC_ROOT": str(root),
        "EPYC_RESEARCH": str(research),
        "P_BENCH_4_RUNNER_ROOT": str(research),
        "P_BENCH_4_EXPECTED_RESEARCH_COMMIT": _git("rev-parse", "HEAD", cwd=research),
        "P_BENCH_4_EXPECTED_RESEARCH_TREE": _git("rev-parse", "HEAD^{tree}", cwd=research),
        "P_BENCH_4_EXPECTED_REPOSITORY": _git("remote", "get-url", "origin", cwd=research),
        "P_BENCH_4_EXPECTED_RUNNER_SHA256": _sha256_bytes(runner_bytes),
        "P_BENCH_4_EXPECTED_AMENDMENT_SHA256": _sha256_bytes(amendment),
        "P_BENCH_4_EXPECTED_MEASUREMENT_SHA256": _sha256_bytes(measurement.encode()),
        "P_BENCH_4_EXPECTED_AMENDED_MEASUREMENT_SHA256": _sha256_bytes(amended_measurement),
        "P_BENCH_4_EXPECTED_CHANGELOG_SHA256": _sha256_bytes(changelog.encode()),
        "P_BENCH_4_EXPECTED_AMENDED_CHANGELOG_SHA256": _sha256_bytes(amended_changelog),
    }
    return {
        "root": root,
        "research": research,
        "script": operator / SOURCE_SCRIPT.name,
        "measurement": measurement,
        "changelog": changelog,
        "env": env,
    }


def _run(fixture: dict[str, object], *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | fixture["env"] | extra_env  # type: ignore[operator]
    return subprocess.run(
        ["bash", str(fixture["script"]), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd="/",
    )


def test_validate_only_is_cwd_independent_and_does_not_mutate(transaction_fixture: dict[str, object]) -> None:
    result = _run(transaction_fixture, "--validate-only")
    assert result.returncode == 0, result.stderr
    assert "preflight-valid" in result.stdout
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_text() == transaction_fixture["measurement"], result.stderr
    assert (root / "CHANGELOG.md").read_text() == transaction_fixture["changelog"], result.stderr


def test_attest_applies_exact_content_and_writes_runner_bound_receipt(transaction_fixture: dict[str, object]) -> None:
    result = _run(transaction_fixture, "--attest", TOKEN)
    assert result.returncode == 0, result.stderr
    root = transaction_fixture["root"]
    measurement = (root / "MEASUREMENT.md").read_text()
    assert "## P-BENCH-4" in measurement
    assert "919e83a249ed9060d0608305700e6eeddb8daa71" in measurement
    assert "P-BENCH-4` for prospective" in (root / "CHANGELOG.md").read_text()
    receipts = list((root / "artifacts/operator").glob("ratify_pbench4_fg4b_server_native_*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["status"] == "ratified"
    assert receipt["instrument_sha256"] == transaction_fixture["env"]["P_BENCH_4_EXPECTED_RUNNER_SHA256"]
    assert receipt["instrument"] == {
        "repository": transaction_fixture["env"]["P_BENCH_4_EXPECTED_REPOSITORY"],
        "repository_commit": transaction_fixture["env"]["P_BENCH_4_EXPECTED_RESEARCH_COMMIT"],
        "repository_tree": transaction_fixture["env"]["P_BENCH_4_EXPECTED_RESEARCH_TREE"],
        "path": "scripts/benchmark/fg4b_a4_cpu_optimized_reanchor.py",
    }
    assert receipt["contract"]["measured_reps"] == 5
    assert receipt["contract"]["ignore_eos"] is True
    assert receipt["contract"]["required_finish_reason"] == "length"
    assert receipt["contract"]["warmup"] == {
        "tokens": 64,
        "consecutive_samples": 3,
        "relative_tolerance": 0.05,
        "max_attempts": 8,
    }
    assert receipt["contract"]["cold_cache_preparation"] == {
        "sync": True,
        "drop_caches": 3,
        "after_clean_host_gate": True,
        "before_server_start": True,
    }
    assert receipt["contract"]["per_request_witness"] == {
        "exclusive_inference_process_tree": True,
        "exact_live_affinity": "0-47,96-143",
    }
    assert receipt["contract"]["durable_publish"] == (
        "fsync_files_and_staging_dir_then_parent_before_and_after_atomic_rename"
    )


@pytest.mark.skipif(not AUTHORITATIVE_RUNNER.is_file(), reason="hardened FG-4b worktree is unavailable")
def test_receipt_contract_is_accepted_by_the_authoritative_hardened_runner(
    transaction_fixture: dict[str, object],
) -> None:
    result = _run(transaction_fixture, "--attest", TOKEN)
    assert result.returncode == 0, result.stderr
    root = transaction_fixture["root"]
    receipt_path = next((root / "artifacts/operator").glob("ratify_pbench4_fg4b_server_native_*.json"))
    receipt = json.loads(receipt_path.read_text())
    receipt["instrument_sha256"] = AUTHORITATIVE_RUNNER_SHA256
    runner_root = AUTHORITATIVE_RUNNER.parents[2]
    receipt["instrument"] = {
        "repository": _git("remote", "get-url", "origin", cwd=runner_root),
        "repository_commit": _git("rev-parse", "HEAD", cwd=runner_root),
        "repository_tree": _git("rev-parse", "HEAD^{tree}", cwd=runner_root),
        "path": str(AUTHORITATIVE_RUNNER.relative_to(runner_root)),
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("pbench4_authoritative_test", AUTHORITATIVE_RUNNER)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    validated = runner.validate_protocol_attestation(receipt_path)
    assert validated["contract"] == receipt["contract"]


def test_refuses_wrong_runner_hash_without_mutation(transaction_fixture: dict[str, object]) -> None:
    result = _run(
        transaction_fixture,
        "--validate-only",
        P_BENCH_4_EXPECTED_RUNNER_SHA256="0" * 64,
    )
    assert result.returncode != 0
    assert "hardened-runner hash differs" in result.stderr
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_text() == transaction_fixture["measurement"]


def test_refuses_wrong_runner_tree_without_mutation(transaction_fixture: dict[str, object]) -> None:
    result = _run(
        transaction_fixture,
        "--validate-only",
        P_BENCH_4_EXPECTED_RESEARCH_TREE="0" * 40,
    )
    assert result.returncode != 0
    assert "hardened-runner tree differs" in result.stderr
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_text() == transaction_fixture["measurement"]


def test_refuses_wrong_protocol_text_hash_without_mutation(transaction_fixture: dict[str, object]) -> None:
    result = _run(
        transaction_fixture,
        "--validate-only",
        P_BENCH_4_EXPECTED_AMENDMENT_SHA256="f" * 64,
    )
    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_text() == transaction_fixture["measurement"]


def test_rolls_back_measurement_when_changelog_replacement_cannot_start(transaction_fixture: dict[str, object]) -> None:
    result = _run(
        transaction_fixture,
        "--attest",
        TOKEN,
        P_BENCH_4_TEST_FAIL_AFTER_MEASUREMENT="1",
    )
    assert result.returncode != 0
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_text() == transaction_fixture["measurement"]
    assert (root / "CHANGELOG.md").read_text() == transaction_fixture["changelog"]
    assert not list((root / "artifacts/operator").glob("ratify_pbench4_fg4b_server_native_*.json"))


def test_no_replace_receipt_refuses_existing_destination_and_rolls_back_policy(
    transaction_fixture: dict[str, object],
) -> None:
    root = transaction_fixture["root"]
    stamp = "20260728T235959Z"
    receipt = root / "artifacts/operator" / f"ratify_pbench4_fg4b_server_native_{stamp}.json"
    receipt.write_text("existing receipt\n", encoding="utf-8")
    result = _run(
        transaction_fixture,
        "--attest",
        TOKEN,
        P_BENCH_4_TEST_STAMP=stamp,
    )
    assert result.returncode != 0
    assert "receipt destination already exists" in result.stderr
    assert receipt.read_text(encoding="utf-8") == "existing receipt\n"
    assert (root / "MEASUREMENT.md").read_text() == transaction_fixture["measurement"], result.stderr
    assert (root / "CHANGELOG.md").read_text() == transaction_fixture["changelog"], result.stderr


def test_durable_receipt_commits_all_three_files_despite_post_publish_interruption(
    transaction_fixture: dict[str, object],
) -> None:
    result = _run(
        transaction_fixture,
        "--attest",
        TOKEN,
        P_BENCH_4_TEST_FAIL_AFTER_RECEIPT="1",
    )
    assert result.returncode != 0
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_text() != transaction_fixture["measurement"]
    assert (root / "CHANGELOG.md").read_text() != transaction_fixture["changelog"]
    receipts = list((root / "artifacts/operator").glob("ratify_pbench4_fg4b_server_native_*.json"))
    assert len(receipts) == 1
    assert json.loads(receipts[0].read_text())["status"] == "ratified"


def test_live_production_preflight_accepts_current_policy_pins() -> None:
    result = subprocess.run(
        ["bash", str(SOURCE_SCRIPT), "--validate-only"],
        text=True,
        capture_output=True,
        check=False,
        cwd="/",
    )
    assert result.returncode == 0, result.stderr
    assert "preflight-valid" in result.stdout


def test_reviewed_bundle_keeps_the_explicit_nonretroactive_quarantine() -> None:
    script = SOURCE_SCRIPT.read_text(encoding="utf-8")
    amendment = SOURCE_AMENDMENT.read_text(encoding="utf-8")
    assert "c00f2937a48439f5f00e527176e854a94333a8db" in script
    assert "f2983a10f6af3290f254c16a7681762a074bafb71fc12df68dbfbcc83043a1b9" in script
    assert "919e83a249ed9060d0608305700e6eeddb8daa71" in amendment
    assert "explicitly_nonconforming_not_retro_certified" in script

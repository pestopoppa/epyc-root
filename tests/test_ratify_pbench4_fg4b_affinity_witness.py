"""Executable coverage for the superseding P-BENCH-4 affinity transaction."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROOT / "artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729.sh"
SOURCE_AMENDMENT = ROOT / "artifacts/operator/pbench4_fg4b_affinity_witness_amendment_20260729.md"
SOURCE_PRIOR_RECEIPT = ROOT / "artifacts/operator/ratify_pbench4_fg4b_server_native_20260729T055435Z.json"
RUNNER_ROOT = Path("/mnt/raid0/llm/worktrees/fg4b-optimized-server-20260728")
TOKEN = "RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def transaction_fixture(tmp_path: Path) -> dict[str, object]:
    if not RUNNER_ROOT.is_dir():
        pytest.skip("pinned FG-4b runner worktree is unavailable")
    root = tmp_path / "root"
    operator = root / "artifacts/operator"
    operator.mkdir(parents=True)
    script = operator / SOURCE_SCRIPT.name
    amendment = operator / SOURCE_AMENDMENT.name
    prior_receipt = operator / SOURCE_PRIOR_RECEIPT.name
    shutil.copyfile(SOURCE_SCRIPT, script)
    shutil.copyfile(SOURCE_AMENDMENT, amendment)
    shutil.copyfile(SOURCE_PRIOR_RECEIPT, prior_receipt)
    measurement = b"# Measurement\n\nExisting policy.\n"
    changelog = b"# Changelog\n\nExisting entry.\n"
    (root / "MEASUREMENT.md").write_bytes(measurement)
    (root / "CHANGELOG.md").write_bytes(changelog)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "P-BENCH-4 Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)

    amended_measurement = measurement + b"\n" + amendment.read_bytes()
    entry = (
        b"- Ratified the P-BENCH-4 FG-4b affinity-witness superseding amendment; "
        b"it binds stable all-thread request-boundary snapshots to the hardened "
        b"runner and retains the prior receipt as superseded provenance.\n"
    )
    amended_changelog = changelog + b"\n" + entry
    env = {
        "P_BENCH_4_AFFINITY_TEST_MODE": "1",
        "EPYC_ROOT": str(root),
        "EPYC_RESEARCH": "/mnt/raid0/llm/epyc-inference-research",
        "P_BENCH_4_AFFINITY_RUNNER_ROOT": str(RUNNER_ROOT),
        "P_BENCH_4_AFFINITY_TRUST_LOCK": str(operator / ".trust.lock"),
        "P_BENCH_4_AFFINITY_EXPECTED_MEASUREMENT_SHA256": _sha256(measurement),
        "P_BENCH_4_AFFINITY_EXPECTED_AMENDED_MEASUREMENT_SHA256": _sha256(amended_measurement),
        "P_BENCH_4_AFFINITY_EXPECTED_CHANGELOG_SHA256": _sha256(changelog),
        "P_BENCH_4_AFFINITY_EXPECTED_AMENDED_CHANGELOG_SHA256": _sha256(amended_changelog),
    }
    return {"root": root, "script": script, "env": env, "measurement": measurement, "changelog": changelog}


def _run(fixture: dict[str, object], *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(fixture["script"]), *args],
        text=True,
        capture_output=True,
        check=False,
        cwd="/",
        env=os.environ | fixture["env"] | extra_env,  # type: ignore[operator]
    )


def test_validate_only_is_cwd_independent_and_uses_the_exact_runner(transaction_fixture: dict[str, object]) -> None:
    result = _run(transaction_fixture, "--validate-only")
    assert result.returncode == 0, result.stderr
    assert "preflight-valid" in result.stdout
    root = transaction_fixture["root"]
    assert (root / "MEASUREMENT.md").read_bytes() == transaction_fixture["measurement"]
    assert (root / "CHANGELOG.md").read_bytes() == transaction_fixture["changelog"]


def test_attest_publishes_runner_bound_superseding_receipt(transaction_fixture: dict[str, object]) -> None:
    result = _run(transaction_fixture, "--attest", TOKEN, P_BENCH_4_AFFINITY_TEST_STAMP="20260729T120000Z")
    assert result.returncode == 0, result.stderr
    root = transaction_fixture["root"]
    receipt_path = root / "artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T120000Z.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["instrument"]["repository_commit"] == "006801b96de6a427a5c73a380fe5ff15260d33be"
    assert receipt["instrument_sha256"] == "e77415acf226e67d0fcf09652e24a19a70bc9a5bdad9df5da6d66b6bd0538de9"
    assert receipt["contract"]["per_request_witness"]["thread_affinity"]["before_after_witness_exact"] is True
    assert receipt["supersedes"] == {
        "receipt_path": "artifacts/operator/ratify_pbench4_fg4b_server_native_20260729T055435Z.json",
        "receipt_sha256": "8da155e451f94720878d1fc7ffc53c190d8eabb96b106b15ffb32794528c154e",
        "status": "superseded_provenance_only",
    }
    assert "not continuous scheduler tracing" in (root / "MEASUREMENT.md").read_text(encoding="utf-8")


def test_duplicate_or_existing_receipt_refuses_without_policy_mutation(transaction_fixture: dict[str, object]) -> None:
    root = transaction_fixture["root"]
    destination = root / "artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T120001Z.json"
    destination.write_text("already exists\n", encoding="utf-8")
    existing = _run(transaction_fixture, "--attest", TOKEN, P_BENCH_4_AFFINITY_TEST_STAMP="20260729T120001Z")
    assert existing.returncode != 0
    assert "receipt destination already exists" in existing.stderr
    assert (root / "MEASUREMENT.md").read_bytes() == transaction_fixture["measurement"]
    applied = _run(transaction_fixture, "--attest", TOKEN, P_BENCH_4_AFFINITY_TEST_STAMP="20260729T120002Z")
    assert applied.returncode == 0, applied.stderr
    duplicate = _run(transaction_fixture, "--validate-only")
    assert duplicate.returncode != 0
    assert "marker is already present" in duplicate.stderr

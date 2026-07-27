from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "artifacts/operator/ratify_and_apply_e8_quality_baseline_v4_20260727.sh"
VALIDATOR = ROOT / "artifacts/operator/prepare_e8_quality_baseline_reseed_v4_20260727.sh"
INTEGRITY = ROOT / "artifacts/operator/e8_quality_baseline_v4_integrity_20260727.json"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_detached_integrity_root_is_pinned_and_covers_execution_boundary() -> None:
    wrapper = WRAPPER.read_text()
    expected = re.search(r'^INTEGRITY_SHA256="([0-9a-f]{64})"$', wrapper, re.MULTILINE)
    assert expected is not None
    assert sha256(INTEGRITY) == expected.group(1)
    manifest = json.loads(INTEGRITY.read_text())
    artifacts = manifest["artifacts"]
    required = {
        "/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/run_e8_quality_baseline_reseed.py",
        "artifacts/operator/apply_e8_quality_baseline_state.py",
        "artifacts/operator/e8_context_replacement_map_candidate_relaxed_20260727.json",
        "artifacts/operator/e8_quality_context_coverage_v4_r2_20260727.json",
        "artifacts/operator/prepare_e8_quality_baseline_reseed_v4_20260727.sh",
    }
    assert set(artifacts) == required
    for path_text, digest in artifacts.items():
        path = Path(path_text)
        if not path.is_absolute():
            path = ROOT / path
        assert sha256(path) == digest


def test_collection_precedes_and_does_not_mint_human_receipt() -> None:
    wrapper = WRAPPER.read_text()
    collect_body = wrapper.split("collect() {", 1)[1].split("validate_only() {", 1)[0]
    assert "--collect-candidate" in collect_body
    assert "stage_state_review" in collect_body
    assert "mint_receipt" not in collect_body
    apply_body = wrapper.split("apply_final() {", 1)[1]
    assert apply_body.index("validate_only") < apply_body.index("mint_receipt")
    assert apply_body.index("mint_receipt") < apply_body.index("applier --attest")
    for field in (
        '"pre_state_sha256"',
        '"candidate_state_sha256"',
        '"exact_state_diff"',
        '"validation_result"',
        '"state_candidate_review_sha256"',
    ):
        assert field in wrapper
    assert "--expected-pre-state-sha256" in wrapper
    assert "--expected-candidate-state-sha256" in wrapper
    applier_body = wrapper.split("applier() {", 1)[1].split(
        "validate_resume_state() {", 1
    )[0]
    assert 'if [[ "$action" == "--validate-only" ]]' in applier_body
    assert 'bindings="$(validate_receipt)"' in applier_body
    assert 'expected_pre="$(jq -er' in applier_body
    review_body = wrapper.split("validate_state_review() {", 1)[1].split(
        "applier() {", 1
    )[0]
    assert "module.validate_state_candidate_review(" in review_body
    assert "allow_applied=receipt.is_file()" in review_body
    mint_body = wrapper.split("mint_receipt() {", 1)[1].split(
        "apply_final() {", 1
    )[0]
    assert "review, review_sha256 = module.validate_state_candidate_review(" in mint_body
    assert "module.verify_state_review_pin(review_path, review_sha256)" in mint_body


def test_validator_matches_applier_interface_and_optimization_is_disabled() -> None:
    validator = VALIDATOR.read_text()
    assert '"$1" == "--validate-evidence"' in validator
    assert "PYTHONOPTIMIZE=0" in validator
    assert "assert " not in validator
    assert subprocess.run(["bash", "-n", str(VALIDATOR)], check=False).returncode == 0
    assert subprocess.run(["bash", "-n", str(WRAPPER)], check=False).returncode == 0


def test_wrapper_binds_repo_venv_from_arbitrary_shell_and_has_three_modes() -> None:
    wrapper = WRAPPER.read_text()
    assert 'PYTHON="$ORCH/.venv/bin/python"' in wrapper
    assert "EPYC_ROOT" not in wrapper
    assert "EPYC_ORCH" not in wrapper
    assert "EPYC_RESEARCH" not in wrapper
    assert "EPYC_PYTHON" not in wrapper
    assert "--collect)" in wrapper
    assert "--validate-only)" in wrapper
    assert "--attest)" in wrapper
    assert "ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727" in wrapper


def test_outer_resume_scanner_accepts_consumed_candidate_after_commit(tmp_path: Path) -> None:
    wrapper = WRAPPER.read_text()
    function = wrapper.split("validate_resume_state() {", 1)[1].split("\n}\n", 1)[0]
    program = function.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    base = tmp_path / "transaction"
    attempt = tmp_path / "transaction-attempt-1"
    attempt.mkdir()
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"evidence": true}\n')
    pre = b'{"state": "before"}\n'
    candidate = b'{"state": "candidate"}\n'
    backup = attempt / "autopilot_state.json.before"
    backup.write_bytes(pre)
    live = tmp_path / "autopilot_state.json"
    live.write_bytes(candidate)
    journal = {
        "schema": "epyc.e8_quality_baseline_state_apply_transaction.v1",
        "state": "committed",
        "evidence": {"sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()},
        "state_file": {
            "backup": str(backup),
            "destination": str(live),
            "pre_sha256": hashlib.sha256(pre).hexdigest(),
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        },
    }
    (attempt / "transaction.json").write_text(json.dumps(journal))

    result = subprocess.run(
        [sys.executable, "-", str(base), str(tmp_path / "attestation.json"), str(evidence)],
        input=program,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "committed"
    assert not (attempt / "autopilot_state.json.candidate").exists()


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda receipt, _review: receipt.pop("evidence"),
            "wrong exact key set",
        ),
        (
            lambda receipt, _review: receipt.update(
                evidence="/tmp/substituted-evidence.json"
            ),
            "field differs from reviewed inputs: evidence",
        ),
        (
            lambda receipt, _review: receipt["repository_heads"].update(
                epyc_root="0" * 40
            ),
            "field differs from reviewed inputs: repository_heads",
        ),
        (
            lambda receipt, _review: receipt.update(ratified_at="not-a-time"),
            "timestamp is not ISO-8601",
        ),
        (
            lambda _receipt, review: review.write_text(review.read_text() + "\n"),
            "field differs from reviewed inputs: state_candidate_review_sha256",
        ),
    ],
)
def test_exact_receipt_validator_rejects_tampering(
    tmp_path: Path, mutate, error: str
) -> None:
    wrapper = WRAPPER.read_text()
    function = wrapper.split("validate_receipt() {", 1)[1].split("\nPY\n}", 1)[0]
    program = function.split("<<'PY'\n", 1)[1]
    candidate = tmp_path / "protocol_candidate.json"
    candidate.write_text('{"protocol":{"protocol_id":"e8_quality_full_pool_tier_baseline.v4"}}\n')
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps({"protocol_candidate": {"path": str(candidate)}}) + "\n"
    )
    mapping = tmp_path / "map.json"
    coverage = tmp_path / "coverage.json"
    integrity = tmp_path / "integrity.json"
    for path in (mapping, coverage, integrity):
        path.write_text("{}\n")
    review = tmp_path / "review.json"
    review_value = {
        "pre_state_sha256": "1" * 64,
        "candidate_state_sha256": "2" * 64,
        "exact_state_diff": [{"path": "/baseline_state"}],
        "validation_result": {"passed": True},
    }
    review.write_text(json.dumps(review_value) + "\n")
    token = "ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727"
    heads = {
        name: subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        for name, repo in {
            "epyc_root": ROOT,
            "epyc_orchestrator": ORCH,
            "epyc_inference_research": RESEARCH,
        }.items()
    }
    receipt_value = {
        "schema": "epyc.operator_e8_quality_baseline_context_apply.v1",
        "decision": token,
        "ratified_at": "2026-07-27T12:00:00+00:00",
        "evidence": str(evidence.resolve()),
        "evidence_sha256": sha256(evidence),
        "protocol_candidate": str(candidate.resolve()),
        "protocol_candidate_sha256": sha256(candidate),
        "protocol_id": "e8_quality_full_pool_tier_baseline.v4",
        "replacement_map_sha256": sha256(mapping),
        "coverage_report_sha256": sha256(coverage),
        "integrity_root_sha256": sha256(integrity),
        "state_candidate_review": str(review.resolve()),
        "state_candidate_review_sha256": sha256(review),
        "pre_state_sha256": review_value["pre_state_sha256"],
        "candidate_state_sha256": review_value["candidate_state_sha256"],
        "exact_state_diff": review_value["exact_state_diff"],
        "validation_result": review_value["validation_result"],
        "source_pool_tier_relaxation_accepted": True,
        "repository_heads": heads,
    }
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(receipt_value) + "\n")
    command = [
        sys.executable,
        "-",
        str(receipt),
        str(evidence),
        str(mapping),
        str(coverage),
        str(integrity),
        str(review),
        token,
        str(ROOT),
        str(ORCH),
        str(RESEARCH),
    ]
    valid = subprocess.run(
        command,
        input=program,
        text=True,
        capture_output=True,
        check=False,
    )
    assert valid.returncode == 0, valid.stderr

    mutate(receipt_value, review)
    receipt.write_text(json.dumps(receipt_value) + "\n")
    result = subprocess.run(
        command, input=program, text=True, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert error in result.stderr

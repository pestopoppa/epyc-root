"""Focused transaction tests for the separately authorized E8 baseline-state apply."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "artifacts/operator/apply_e8_quality_baseline_state.py"
spec = importlib.util.spec_from_file_location("e8_state_apply", MODULE_PATH)
assert spec is not None and spec.loader is not None
apply = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = apply
spec.loader.exec_module(apply)
def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _state() -> dict:
    return {
        "active_instrument_eras": {"eval_quality": "E8", "autopilot_speed": "E8-autopilot-speed"},
        "baseline_state": {"eval_quality_era": "E7-eval-instrument", "baselines_by_tier": {"1": 1.0, "2": 2.0}},
        "e8_quality_rebaseline": {"boundary": apply.E8_BOUNDARY, "status": "hold_open", "required_next_action": "human-only E8 baseline value reseed after fresh evidence"},
        "quality_history_by_tier": {"0": [0.1], "1": [1.0], "2": [2.0], "3": [3.0]},
        "quality_history_provenance_by_tier": {"0": [], "1": [], "2": [], "3": []},
        "unrelated": {"must": "survive"},
    }


def _manifest(tmp_path: Path) -> Path:
    sources = []
    for tier, n in ((1, 50), (2, 500)):
        summary = tmp_path / f"summary.T{tier}.json"
        _write(summary, {"tier": tier, "n": n, "era": "E8", "decision_grade": True, "observations": [{"era": "E8", "protocol_id": apply.EXPECTED_PROTOCOL, "n": n} for _ in range(3)]})
        sources.append({"tier": tier, "era": "E8", "protocol_id": apply.EXPECTED_PROTOCOL, "n": n, "path": str(summary.resolve()), "sha256": apply.sha256_path(summary)})
    manifest = tmp_path / "evidence.json"
    seal = tmp_path / "run_seal.json"
    _write(manifest, {"schema": apply.EVIDENCE_SCHEMA, "eval_quality_era": "E8", "source_records": sources, "replacement": {"baseline_state": {"eval_quality_era": "E8", "baselines_by_tier": {"1": 1.5, "2": 2.5}}, "quality_history_by_tier": {"1": [1.4, 1.5, 1.6], "2": [2.4, 2.5, 2.6]}, "quality_history_provenance_by_tier": {"1": [{"era": "E8"}] * 3, "2": [{"era": "E8"}] * 3}}, "run_seal_path": str(seal.resolve())})
    _write(seal, {"bundle_sha256": {source["path"]: source["sha256"] for source in sources}})
    return manifest


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    state = tmp_path / "autopilot_state.json"
    _write(state, _state())
    return state, _manifest(tmp_path), tmp_path / "transaction"


def test_validate_only_consumes_exact_six_observation_contract_without_state_mutation(tmp_path: Path) -> None:
    state, evidence, _transaction = _paths(tmp_path)
    before = state.read_bytes()
    calls = 0

    def validated() -> None:
        nonlocal calls
        calls += 1

    _old, candidate, _hash = apply.prepare_candidate(state, evidence, validated)

    assert calls == 1
    assert state.read_bytes() == before
    assert candidate["baseline_state"]["eval_quality_era"] == "E8"
    assert candidate["quality_history_by_tier"]["0"] == [0.1]
    assert candidate["quality_history_by_tier"]["3"] == [3.0]
    assert candidate["e8_quality_rebaseline"]["status"] == "closed"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda review: review.update(unreviewed=True),
        lambda review: review["exact_state_diff"].append(
            copy.deepcopy(review["exact_state_diff"][-1])
        ),
        lambda review: review["exact_state_diff"][0].update(before={"tampered": True}),
        lambda review: review.update(evidence_path="/tmp/substituted-evidence.json"),
    ],
)
def test_state_candidate_review_requires_exact_fresh_recomputation(
    tmp_path: Path, mutate
) -> None:
    state, evidence, _transaction = _paths(tmp_path)
    validator = tmp_path / "validator.sh"
    validator.write_text("#!/bin/bash\nexit 0\n")
    payload = apply.state_candidate_review_payload(
        state, evidence, validator, lambda: None
    )
    assert [row["path"] for row in payload["exact_state_diff"]] == [
        "/" + "/".join(path) for path in apply.STATE_REVIEW_PATHS
    ]
    review = tmp_path / "state_candidate_review.json"
    _write(review, payload)
    validated, review_sha256 = apply.validate_state_candidate_review(
        review, state, evidence, validator, lambda: None
    )
    assert validated == payload
    assert review_sha256 == apply.sha256_path(review)

    mutate(payload)
    _write(review, payload)
    with pytest.raises(apply.ApplyError):
        apply.validate_state_candidate_review(
            review, state, evidence, validator, lambda: None
        )


def test_applied_candidate_review_requires_prior_receipt_allowance(tmp_path: Path) -> None:
    state, evidence, _transaction = _paths(tmp_path)
    validator = tmp_path / "validator.sh"
    validator.write_text("#!/bin/bash\nexit 0\n")
    payload = apply.state_candidate_review_payload(
        state, evidence, validator, lambda: None
    )
    review = tmp_path / "state_candidate_review.json"
    _write(review, payload)
    _old, candidate, _pin = apply.prepare_candidate(state, evidence, lambda: None)
    _write(state, candidate)

    with pytest.raises(apply.ApplyError, match="previously minted human receipt"):
        apply.validate_state_candidate_review(
            review, state, evidence, validator, lambda: None
        )
    validated, review_sha256 = apply.validate_state_candidate_review(
        review,
        state,
        evidence,
        validator,
        lambda: None,
        allow_applied=True,
    )
    assert validated == json.loads(review.read_text())
    assert review_sha256 == apply.sha256_path(review)


def test_receipt_publication_refuses_review_tamper_after_exact_validation(
    tmp_path: Path,
) -> None:
    state, evidence, _transaction = _paths(tmp_path)
    validator = tmp_path / "validator.sh"
    validator.write_text("#!/bin/bash\nexit 0\n")
    payload = apply.state_candidate_review_payload(
        state, evidence, validator, lambda: None
    )
    review = tmp_path / "state_candidate_review.json"
    _write(review, payload)
    _validated, validated_sha256 = apply.validate_state_candidate_review(
        review, state, evidence, validator, lambda: None
    )

    payload["exact_state_diff"][0]["before"] = {"injected": "between validation and mint"}
    _write(review, payload)

    with pytest.raises(apply.ApplyError, match="changed during receipt mint"):
        apply.verify_state_review_pin(review, validated_sha256)


def test_consumes_bundle_accepted_by_the_read_only_evidence_validator(tmp_path: Path) -> None:
    state = tmp_path / "autopilot_state.json"
    _write(state, _state())
    evidence = _manifest(tmp_path)
    validator = tmp_path / "validator.sh"
    validator.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "[[ $# -eq 2 && \"$1\" == --validate-evidence && -f \"$2\" ]]\n"
    )

    _old, candidate, _hash = apply.prepare_candidate(
        state,
        evidence,
        lambda: apply.run_evidence_validator(
            validator,
            evidence,
            dict(os.environ),
        ),
    )

    assert candidate["baseline_state"]["eval_quality_era"] == "E8"


def test_refuses_manifest_swap_during_evidence_validation(tmp_path: Path) -> None:
    state, evidence, _transaction = _paths(tmp_path)

    def swap_manifest() -> None:
        evidence.write_text("{}\n")

    with pytest.raises(apply.ApplyError, match="manifest changed"):
        apply.prepare_candidate(state, evidence, swap_manifest)


def test_refuses_source_summary_swap_after_validation(tmp_path: Path) -> None:
    state, evidence, _transaction = _paths(tmp_path)
    source = Path(json.loads(evidence.read_text())["source_records"][0]["path"])

    def swap_source() -> None:
        source.write_text("{}\n")

    with pytest.raises(apply.ApplyError, match="sealed evidence artifact changed"):
        apply.prepare_candidate(state, evidence, swap_source)


def test_cli_attest_refuses_noncanonical_evidence_override(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    before = state.read_bytes()
    rc = apply.main(
        [
            "--state", str(state),
            "--evidence", str(evidence),
            "--canonical-evidence", str(tmp_path / "canonical-evidence.json"),
            "--validator", str(tmp_path / "unused-validator.sh"),
            "--transaction-dir", str(transaction),
            "--attestation", str(tmp_path / "receipt.json"),
            "--attest", apply.TOKEN,
        ]
    )

    assert rc == 1
    assert state.read_bytes() == before
    assert not transaction.exists()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda state, manifest: state["active_instrument_eras"].update(eval_quality="E7-eval-instrument"), "active E8"),
        (lambda state, manifest: manifest.update(eval_quality_era="E7-eval-instrument"), "not the E8"),
        (lambda state, manifest: manifest["source_records"][1].update(protocol_id="wrong"), "wrong era, protocol"),
        (lambda state, manifest: manifest["source_records"][1].update(n=50), "wrong era, protocol"),
    ],
)
def test_refuses_wrong_state_era_protocol_or_manifest(tmp_path: Path, mutate, message: str) -> None:
    state_path, evidence, _transaction = _paths(tmp_path)
    state = json.loads(state_path.read_text())
    manifest = json.loads(evidence.read_text())
    mutate(state, manifest)
    _write(state_path, state)
    _write(evidence, manifest)

    with pytest.raises(apply.ApplyError, match=message):
        apply.prepare_candidate(state_path, evidence, lambda: None)


def test_apply_cas_commits_only_baseline_tiers_and_closes_hold(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    journal_path = apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None)

    after = json.loads(state.read_text())
    journal = json.loads(journal_path.read_text())
    assert journal["state"] == "committed"
    assert after["unrelated"] == {"must": "survive"}
    assert after["quality_history_by_tier"]["0"] == [0.1]
    assert after["quality_history_by_tier"]["3"] == [3.0]
    assert after["quality_history_by_tier"]["1"] == [1.4, 1.5, 1.6]
    assert after["baseline_state"]["eval_quality_era"] == "E8"
    assert after["e8_quality_rebaseline"]["status"] == "closed"


def test_cas_race_refuses_without_clobbering_state(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    concurrent = copy.deepcopy(_state())
    concurrent["unrelated"] = {"concurrent": "edit"}

    with pytest.raises(apply.CASMismatch, match="changed after preflight"):
        apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None, before_replace=lambda destination: _write(destination, concurrent))

    assert json.loads(state.read_text())["unrelated"] == {"concurrent": "edit"}
    assert json.loads((transaction / "transaction.json").read_text())["state"] == "manual_recovery_required"


def test_snapshot_race_before_journal_uses_original_preimage_and_refuses(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    concurrent = copy.deepcopy(_state())
    concurrent["unrelated"] = {"concurrent": "between snapshot and journal"}

    with pytest.raises(apply.CASMismatch, match="changed after preflight"):
        apply.apply_transaction(
            state_path=state,
            transaction_dir=transaction,
            evidence_path=evidence,
            validate_evidence=lambda: None,
            after_prepare=lambda destination: _write(destination, concurrent),
        )

    journal = json.loads((transaction / "transaction.json").read_text())
    assert journal["state_file"]["pre_sha256"] != apply.sha256_path(state)
    assert json.loads(state.read_text())["unrelated"] == concurrent["unrelated"]


def test_reviewed_state_hashes_refuse_unrelated_mutation_before_transaction(
    tmp_path: Path,
) -> None:
    state, evidence, transaction = _paths(tmp_path)
    reviewed_bytes, reviewed_candidate, _pin = apply.prepare_candidate(
        state, evidence, lambda: None
    )
    candidate_bytes = (
        json.dumps(reviewed_candidate, indent=2, sort_keys=True) + "\n"
    ).encode()
    mutated = json.loads(state.read_text())
    mutated["unrelated"] = {"changed": "after human review"}
    _write(state, mutated)

    with pytest.raises(
        apply.ApplyError, match="differs from the human-reviewed pre-state"
    ):
        apply.apply_transaction(
            state_path=state,
            transaction_dir=transaction,
            evidence_path=evidence,
            validate_evidence=lambda: None,
            expected_pre_state_sha256=apply.hashlib.sha256(reviewed_bytes).hexdigest(),
            expected_candidate_state_sha256=apply.hashlib.sha256(
                candidate_bytes
            ).hexdigest(),
        )

    assert json.loads(state.read_text())["unrelated"] == {
        "changed": "after human review"
    }
    assert not transaction.exists()


def _simulate_replace_before_commit(state: Path, evidence: Path, transaction: Path) -> None:
    _old, candidate, evidence_pin = apply.prepare_candidate(state, evidence, lambda: None)
    before = state.read_bytes()
    candidate_bytes = (json.dumps(candidate, indent=2, sort_keys=True) + "\n").encode()
    transaction.mkdir()
    backup = transaction / "autopilot_state.json.before"
    backup.write_bytes(before)
    journal = {
        "schema": apply.JOURNAL_SCHEMA,
        "state": "applying",
        "created_at": apply.utc_now(),
        "updated_at": apply.utc_now(),
        "evidence": {"path": str(evidence_pin.manifest_path), "sha256": evidence_pin.manifest_sha256, "run_seal_path": str(evidence_pin.seal_path), "run_seal_sha256": evidence_pin.seal_sha256},
        "failure": None,
        "state_file": {
            "destination": str(state.resolve()),
            "backup": str(backup.resolve()),
            "pre_sha256": apply.sha256_path(backup),
            "candidate_sha256": apply.hashlib.sha256(candidate_bytes).hexdigest(),
            "replace_intent_at": apply.utc_now(),
            "applied": False,
            "rollback_conflict": None,
        },
    }
    _write(transaction / "transaction.json", journal)
    state.write_bytes(candidate_bytes)


def test_recovery_restores_crash_after_replace_before_commit(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    before = state.read_bytes()
    _simulate_replace_before_commit(state, evidence, transaction)

    _journal, finalized = apply.recover_transaction(transaction, state)

    assert state.read_bytes() == before
    assert finalized is False
    assert json.loads((transaction / "transaction.json").read_text())["state"] == "rolled_back"


def test_recovery_journal_must_match_human_reviewed_hashes(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    apply.apply_transaction(
        state_path=state,
        transaction_dir=transaction,
        evidence_path=evidence,
        validate_evidence=lambda: None,
    )

    with pytest.raises(
        apply.ApplyError, match="pre-state differs from the human-reviewed pre-state"
    ):
        apply.verify_journal_reviewed_state(
            transaction / "transaction.json", "0" * 64, "1" * 64
        )


def test_recovery_preserves_concurrent_edit_after_crash(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    _simulate_replace_before_commit(state, evidence, transaction)
    concurrent = copy.deepcopy(_state())
    concurrent["unrelated"] = {"concurrent": "edit"}
    _write(state, concurrent)

    with pytest.raises(apply.ApplyError, match="manual recovery"):
        apply.recover_transaction(transaction, state)

    assert json.loads(state.read_text())["unrelated"] == {"concurrent": "edit"}
    assert json.loads((transaction / "transaction.json").read_text())["state"] == "manual_recovery_required"


def test_recovery_finalizes_committed_state_missing_attestation(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    journal = apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None)
    receipt = tmp_path / "receipt.json"

    recovered, finalized = apply.recover_transaction(transaction, state)
    assert recovered == journal
    assert finalized is True
    apply.finalize_attestation(receipt, journal, state)

    payload = json.loads(receipt.read_text())
    assert payload["state_sha256"] == apply.sha256_path(state)
    assert isinstance(payload["state_applied_at"], str)


def test_recovery_refuses_committed_state_conflict_or_mismatched_receipt(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    journal = apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None)
    _write(state, _state())
    with pytest.raises(apply.ApplyError, match="no longer matches"):
        apply.recover_transaction(transaction, state)

    state, evidence, transaction = _paths(tmp_path / "receipt-case")
    journal = apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None)
    receipt = tmp_path / "receipt-case" / "receipt.json"
    _write(receipt, {"wrong": "receipt"})
    before = receipt.read_bytes()
    with pytest.raises(apply.ApplyError, match="does not match"):
        apply.finalize_attestation(receipt, journal, state)
    assert receipt.read_bytes() == before


def test_recovery_rejects_forged_committed_journal(tmp_path: Path) -> None:
    state, evidence, transaction = _paths(tmp_path)
    apply.apply_transaction(
        state_path=state,
        transaction_dir=transaction,
        evidence_path=evidence,
        validate_evidence=lambda: None,
    )
    journal_path = transaction / "transaction.json"
    journal = json.loads(journal_path.read_text())
    journal["state_file"]["applied"] = False
    _write(journal_path, journal)

    with pytest.raises(apply.ApplyError, match="lacks applied-state semantics"):
        apply.recover_transaction(transaction, state)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda journal: journal["state_file"].update(applied_at="not-a-timestamp"), "not ISO-8601"),
        (lambda journal: journal["state_file"].update(applied_at="2000-01-01T00:00:00Z"), "predates replace intent"),
        (lambda journal: journal.update(failure="late failure"), "lacks applied-state semantics"),
        (lambda journal: journal["state_file"].update(rollback_conflict={"race": True}), "lacks applied-state semantics"),
    ],
)
def test_committed_recovery_rejects_invalid_terminal_semantics(tmp_path: Path, mutate, message: str) -> None:
    state, evidence, transaction = _paths(tmp_path)
    apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None)
    journal_path = transaction / "transaction.json"
    journal = json.loads(journal_path.read_text())
    mutate(journal)
    _write(journal_path, journal)

    with pytest.raises(apply.ApplyError, match=message):
        apply.recover_transaction(transaction, state)


@pytest.mark.parametrize("tamper", ["missing", "changed"])
def test_committed_recovery_requires_intact_backup(tmp_path: Path, tamper: str) -> None:
    state, evidence, transaction = _paths(tmp_path)
    apply.apply_transaction(state_path=state, transaction_dir=transaction, evidence_path=evidence, validate_evidence=lambda: None)
    backup = transaction / "autopilot_state.json.before"
    if tamper == "missing":
        backup.unlink()
    else:
        backup.write_text("{}\n")

    with pytest.raises(apply.ApplyError, match="backup is missing or has the wrong hash"):
        apply.recover_transaction(transaction, state)


def test_racing_receipt_creation_preserves_existing_file(tmp_path: Path, monkeypatch) -> None:
    state, evidence, transaction = _paths(tmp_path)
    journal = apply.apply_transaction(
        state_path=state,
        transaction_dir=transaction,
        evidence_path=evidence,
        validate_evidence=lambda: None,
    )
    receipt = tmp_path / "receipt.json"
    foreign = b'{"racing":"receipt"}\n'

    def race_create(path: Path, _payload: dict) -> None:
        path.write_bytes(foreign)
        raise FileExistsError(path)

    monkeypatch.setattr(apply, "write_json_create_only", race_create)
    with pytest.raises(apply.ApplyError, match="racing baseline-state attestation"):
        apply.finalize_attestation(receipt, journal, state)
    assert receipt.read_bytes() == foreign

#!/usr/bin/env python3
"""Fail-closed, human-only E8 quality-baseline state transaction.

The quality runner writes evidence only.  This helper is intentionally a separate
operator action: it validates the sealed evidence through the read-only validator,
then atomically replaces the AutoPilot state under a CAS and durable recovery
journal.  It never creates evidence or invokes the runner.
"""

from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable
import uuid

import fcntl


TOKEN = os.environ.get(
    "E8_BASELINE_APPLY_TOKEN", "APPLY-E8-QUALITY-BASELINE-STATE-20260726"
)
JOURNAL_SCHEMA = "epyc.e8_quality_baseline_state_apply_transaction.v1"
EVIDENCE_SCHEMA = "epyc.e8_quality_baseline_evidence.v2"
E8_BOUNDARY = "2026-07-25T18:38:43Z"
EXPECTED_PROTOCOL = "e8_quality_full_pool_tier_baseline.v4"
EXPECTED_T1_N = 50
EXPECTED_T2_N = 500
REPLACEMENT_KEYS = {
    "baseline_state",
    "quality_history_by_tier",
    "quality_history_provenance_by_tier",
}
STATE_REVIEW_SCHEMA = "epyc.e8_quality_baseline_state_candidate_review.v1"
STATE_REVIEW_KEYS = {
    "schema",
    "state_path",
    "pre_state_sha256",
    "candidate_state_sha256",
    "evidence_path",
    "evidence_sha256",
    "validation_result",
    "exact_state_diff",
}
STATE_REVIEW_PATHS = (
    ("baseline_state",),
    ("quality_history_by_tier", "1"),
    ("quality_history_by_tier", "2"),
    ("quality_history_provenance_by_tier", "1"),
    ("quality_history_provenance_by_tier", "2"),
    ("e8_quality_rebaseline",),
)


class ApplyError(RuntimeError):
    """A fail-closed precondition, CAS, or recovery failure."""


class CASMismatch(ApplyError):
    """The reviewed state changed before atomic replacement."""


@dataclass(frozen=True)
class EvidencePin:
    """The immutable sealed-bundle identity reviewed by the evidence validator."""

    manifest_path: Path
    manifest_sha256: str
    seal_path: Path
    seal_sha256: str
    bundle_sha256: dict[Path, str]

    def verify(self) -> None:
        if sha256_path(self.manifest_path) != self.manifest_sha256:
            raise ApplyError("evidence manifest changed after it was pinned")
        if sha256_path(self.seal_path) != self.seal_sha256:
            raise ApplyError("evidence run seal changed after it was pinned")
        for path, expected in self.bundle_sha256.items():
            if not path.is_file() or sha256_path(path) != expected:
                raise ApplyError(f"sealed evidence artifact changed after validation: {path}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ApplyError(f"{label} is not a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApplyError(f"{label} is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ApplyError(f"{label} lacks a timezone")
    return parsed.astimezone(UTC)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def exclusive_locks(state_path: Path):
    """Acquire the same state/lifecycle locks used by the AutoPilot operator paths."""
    lock_paths = (state_path.parent / ".autopilot.lock", state_path.with_suffix(".json.lock"))
    handles = []
    try:
        for path in lock_paths:
            handle = path.open("a+", encoding="utf-8")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                handle.close()
                raise ApplyError(f"AutoPilot lifecycle/state lock is held: {path}") from exc
            handles.append(handle)
        yield
    finally:
        for handle in reversed(handles):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_create_only(path: Path, value: dict[str, Any]) -> None:
    """Durably publish JSON without replacing a receipt created by another actor."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def write_bytes_atomic(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplyError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ApplyError(f"{label} must be a JSON object")
    return value


def load_json_bytes(value: bytes, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApplyError(f"cannot parse {label}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise ApplyError(f"{label} must be a JSON object")
    return decoded


def pin_evidence(evidence_path: Path) -> EvidencePin:
    """Pin the manifest, seal, and every sealed artifact before validation starts."""
    manifest_path = evidence_path.resolve(strict=True)
    manifest = load_json(manifest_path, "evidence manifest")
    seal_text = manifest.get("run_seal_path")
    if not isinstance(seal_text, str) or not seal_text:
        raise ApplyError("evidence manifest has no canonical run seal path")
    seal_path = Path(seal_text).resolve(strict=True)
    seal = load_json(seal_path, "evidence run seal")
    bundle = seal.get("bundle_sha256")
    if not isinstance(bundle, dict) or not bundle:
        raise ApplyError("evidence run seal has no bundle hash map")
    pinned: dict[Path, str] = {}
    for path_text, expected in bundle.items():
        if not isinstance(path_text, str) or not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise ApplyError("evidence run seal contains an invalid bundle identity")
        path = Path(path_text)
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise ApplyError("evidence run seal contains a noncanonical bundle path")
        if sha256_path(path) != expected:
            raise ApplyError(f"evidence artifact does not match its seal before validation: {path}")
        pinned[path] = expected
    return EvidencePin(
        manifest_path=manifest_path,
        manifest_sha256=sha256_path(manifest_path),
        seal_path=seal_path,
        seal_sha256=sha256_path(seal_path),
        bundle_sha256=pinned,
    )


def validate_state_precondition(state: dict[str, Any]) -> None:
    eras = state.get("active_instrument_eras")
    baseline = state.get("baseline_state")
    hold = state.get("e8_quality_rebaseline")
    history = state.get("quality_history_by_tier")
    provenance = state.get("quality_history_provenance_by_tier")
    if not isinstance(eras, dict) or eras.get("eval_quality") != "E8":
        raise ApplyError("state does not have active E8 eval_quality era")
    if not isinstance(baseline, dict) or baseline.get("eval_quality_era") != "E7-eval-instrument":
        raise ApplyError("state is not in the expected E7 baseline pre-state")
    if (
        not isinstance(hold, dict)
        or hold.get("boundary") != E8_BOUNDARY
        or hold.get("status") != "hold_open"
    ):
        raise ApplyError("E8 quality rebaseline hold is not open at the E8 boundary")
    if not isinstance(history, dict) or not isinstance(provenance, dict):
        raise ApplyError("state quality history/provenance is malformed")
    for tier in ("0", "1", "2", "3"):
        if tier not in history or tier not in provenance:
            raise ApplyError(f"state lacks pre-existing quality tier {tier}")


def autopilot_running() -> bool:
    return any(
        subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, check=False
        ).returncode
        == 0
        for pattern in (
            "[s]cripts/autopilot/autopilot.py start",
            "[s]cripts/autopilot/autopilot_supervisor.py",
        )
    )


def validate_six_observation_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != EVIDENCE_SCHEMA or manifest.get("eval_quality_era") != "E8":
        raise ApplyError("evidence manifest is not the E8 quality-baseline schema")
    records = manifest.get("source_records")
    replacement = manifest.get("replacement")
    if not isinstance(records, list) or len(records) != 2:
        raise ApplyError("manifest must contain exactly T1 and T2 source records")
    if not isinstance(replacement, dict) or set(replacement) != REPLACEMENT_KEYS:
        raise ApplyError("manifest replacement shape is invalid")

    seen: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ApplyError("manifest source record is malformed")
        tier = record.get("tier")
        if tier not in (1, 2) or tier in seen:
            raise ApplyError("manifest source records must uniquely cover T1 and T2")
        seen.add(tier)
        expected_n = EXPECTED_T1_N if tier == 1 else EXPECTED_T2_N
        if (
            record.get("era") != "E8"
            or record.get("protocol_id") != EXPECTED_PROTOCOL
            or record.get("n") != expected_n
        ):
            raise ApplyError(f"T{tier} evidence has wrong era, protocol, or sample size")
        summary_path = record.get("path")
        if not isinstance(summary_path, str) or not summary_path:
            raise ApplyError(f"T{tier} source summary path is malformed")
        summary = load_json(Path(summary_path), f"T{tier} source summary")
        observations = summary.get("observations")
        if (
            summary.get("tier") != tier
            or summary.get("n") != expected_n
            or summary.get("era") != "E8"
            or summary.get("decision_grade") is not True
            or not isinstance(observations, list)
            or len(observations) != 3
        ):
            raise ApplyError(f"T{tier} evidence is not exactly three decision-grade observations")
        if any(
            not isinstance(row, dict)
            or row.get("era") != "E8"
            or row.get("protocol_id") != EXPECTED_PROTOCOL
            or row.get("n") != expected_n
            for row in observations
        ):
            raise ApplyError(f"T{tier} observation does not match the E8 protocol contract")
    if seen != {1, 2}:
        raise ApplyError("manifest does not cover both required quality tiers")
    return replacement


def candidate_state(state: dict[str, Any], replacement: dict[str, Any]) -> dict[str, Any]:
    validate_state_precondition(state)
    baseline = replacement["baseline_state"]
    histories = replacement["quality_history_by_tier"]
    provenance = replacement["quality_history_provenance_by_tier"]
    if (
        not isinstance(baseline, dict)
        or baseline.get("eval_quality_era") != "E8"
        or not isinstance(histories, dict)
        or not isinstance(provenance, dict)
        or set(histories) != {"1", "2"}
        or set(provenance) != {"1", "2"}
    ):
        raise ApplyError("replacement does not contain an E8-only tier-1/tier-2 baseline")

    candidate = copy.deepcopy(state)
    candidate["baseline_state"] = copy.deepcopy(baseline)
    for tier in ("1", "2"):
        candidate["quality_history_by_tier"][tier] = copy.deepcopy(histories[tier])
        candidate["quality_history_provenance_by_tier"][tier] = copy.deepcopy(provenance[tier])
    candidate["e8_quality_rebaseline"] = {
        **candidate["e8_quality_rebaseline"],
        "status": "closed",
        "required_next_action": "E8 baseline-state apply committed; ordinary E8 quality gating may resume",
    }
    return candidate


def run_evidence_validator(validator: Path, evidence: Path, environment: dict[str, str]) -> None:
    result = subprocess.run(
        ["bash", str(validator), "--validate-evidence", str(evidence)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown validator failure"
        raise ApplyError(f"read-only evidence validator refused the bundle: {detail}")


def prepare_candidate(
    state_path: Path,
    evidence_path: Path,
    validate_evidence: Callable[[], None],
) -> tuple[bytes, dict[str, Any], EvidencePin]:
    """Validate evidence before reading state, then construct an in-memory candidate."""
    evidence_pin = pin_evidence(evidence_path)
    validate_evidence()
    evidence_pin.verify()
    manifest = load_json(evidence_pin.manifest_path, "evidence manifest")
    replacement = validate_six_observation_manifest(manifest)
    evidence_pin.verify()
    state_bytes = state_path.read_bytes()
    state = load_json_bytes(state_bytes, "AutoPilot state")
    candidate = candidate_state(state, replacement)
    evidence_pin.verify()
    return state_bytes, candidate, evidence_pin


def state_candidate_review_payload(
    state_path: Path,
    evidence_path: Path,
    validator_path: Path,
    validate_evidence: Callable[[], None],
) -> dict[str, Any]:
    """Recompute the complete human-review document without writing any state."""
    state_bytes, candidate, evidence_pin = prepare_candidate(
        state_path, evidence_path, validate_evidence
    )
    before = load_json_bytes(state_bytes, "reviewed AutoPilot pre-state")

    def at(value: dict[str, Any], path: tuple[str, ...]) -> Any:
        current: Any = value
        for part in path:
            current = current[part]
        return current

    diff = [
        {
            "path": "/" + "/".join(path),
            "before": at(before, path),
            "after": at(candidate, path),
        }
        for path in STATE_REVIEW_PATHS
        if at(before, path) != at(candidate, path)
    ]
    expected_paths = ["/" + "/".join(path) for path in STATE_REVIEW_PATHS]
    if [row["path"] for row in diff] != expected_paths:
        raise ApplyError("state-candidate review must contain exactly six changed rows")
    candidate_bytes = (
        json.dumps(candidate, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    evidence_pin.verify()
    return {
        "schema": STATE_REVIEW_SCHEMA,
        "state_path": str(state_path.resolve()),
        "pre_state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "candidate_state_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "evidence_path": str(evidence_path.resolve()),
        "evidence_sha256": evidence_pin.manifest_sha256,
        "validation_result": {
            "validator": str(validator_path.resolve()),
            "validator_sha256": sha256_path(validator_path),
            "passed": True,
        },
        "exact_state_diff": diff,
    }


def validate_state_candidate_review(
    review_path: Path,
    state_path: Path,
    evidence_path: Path,
    validator_path: Path,
    validate_evidence: Callable[[], None],
    *,
    allow_applied: bool = False,
) -> tuple[dict[str, Any], str]:
    """Require the stored review to equal a fresh, complete candidate review."""
    review_bytes = review_path.read_bytes()
    review = load_json_bytes(review_bytes, "state-candidate review")
    validation = review.get("validation_result")
    expected_paths = ["/" + "/".join(path) for path in STATE_REVIEW_PATHS]
    diff = review.get("exact_state_diff")
    if (
        set(review) != STATE_REVIEW_KEYS
        or review.get("schema") != STATE_REVIEW_SCHEMA
        or review.get("state_path") != str(state_path.resolve())
        or review.get("evidence_path") != str(evidence_path.resolve())
        or review.get("evidence_sha256") != sha256_path(evidence_path)
        or not isinstance(validation, dict)
        or set(validation) != {"validator", "validator_sha256", "passed"}
        or validation.get("validator") != str(validator_path.resolve())
        or validation.get("validator_sha256") != sha256_path(validator_path)
        or validation.get("passed") is not True
        or not re.fullmatch(r"[0-9a-f]{64}", str(review.get("pre_state_sha256")))
        or not re.fullmatch(
            r"[0-9a-f]{64}", str(review.get("candidate_state_sha256"))
        )
    ):
        raise ApplyError("state-candidate review binding differs")
    if (
        not isinstance(diff, list)
        or len(diff) != len(STATE_REVIEW_PATHS)
        or not all(
            isinstance(row, dict) and set(row) == {"path", "before", "after"}
            for row in diff
        )
        or [row["path"] for row in diff] != expected_paths
    ):
        raise ApplyError("state-candidate review must contain the exact six-row diff")

    live_sha256 = sha256_path(state_path)
    if live_sha256 == review["candidate_state_sha256"]:
        if not allow_applied:
            raise ApplyError(
                "live candidate state lacks the previously minted human receipt"
            )
        return review, hashlib.sha256(review_bytes).hexdigest()
    if live_sha256 != review["pre_state_sha256"]:
        raise ApplyError("live state differs from reviewed pre/candidate states")
    expected = state_candidate_review_payload(
        state_path, evidence_path, validator_path, validate_evidence
    )
    expected_bytes = (
        json.dumps(expected, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if review_bytes != expected_bytes:
        raise ApplyError(
            "state-candidate review differs from a fresh exact recomputation"
        )
    return review, hashlib.sha256(review_bytes).hexdigest()


def verify_state_review_pin(review_path: Path, expected_sha256: str) -> None:
    """Refuse publication if the exact validated review bytes changed."""
    if sha256_path(review_path) != expected_sha256:
        raise ApplyError("state-candidate review changed during receipt mint")


def update_journal(path: Path, journal: dict[str, Any], status: str | None = None) -> None:
    if status is not None:
        journal["state"] = status
    journal["updated_at"] = utc_now()
    write_json_atomic(path, journal)


def rollback(journal_path: Path, journal: dict[str, Any]) -> bool:
    record = journal["state_file"]
    destination = Path(record["destination"])
    current = sha256_path(destination)
    if current == record["pre_sha256"]:
        update_journal(journal_path, journal, "rolled_back")
        return True
    if current != record["candidate_sha256"]:
        record["rollback_conflict"] = {
            "at": utc_now(),
            "observed_sha256": current,
            "reason": "state no longer matches transaction candidate; left untouched",
        }
        update_journal(journal_path, journal, "manual_recovery_required")
        return False
    write_bytes_atomic(destination, Path(record["backup"]).read_bytes())
    if sha256_path(destination) != record["pre_sha256"]:
        raise ApplyError("rollback verification failed")
    record["rolled_back_at"] = utc_now()
    update_journal(journal_path, journal, "rolled_back")
    return True


def verify_journal_reviewed_state(
    journal_path: Path,
    expected_pre_state_sha256: str | None,
    expected_candidate_state_sha256: str | None,
) -> None:
    if expected_pre_state_sha256 is None:
        return
    journal = load_json(journal_path, "baseline-state transaction journal")
    record = journal.get("state_file")
    if not isinstance(record, dict):
        raise ApplyError("transaction journal lacks state-file metadata")
    if record.get("pre_sha256") != expected_pre_state_sha256:
        raise ApplyError("transaction pre-state differs from the human-reviewed pre-state")
    if record.get("candidate_sha256") != expected_candidate_state_sha256:
        raise ApplyError(
            "transaction candidate differs from the human-reviewed candidate"
        )


def apply_transaction(
    *,
    state_path: Path,
    transaction_dir: Path,
    evidence_path: Path,
    validate_evidence: Callable[[], None],
    expected_pre_state_sha256: str | None = None,
    expected_candidate_state_sha256: str | None = None,
    after_prepare: Callable[[Path], None] | None = None,
    before_replace: Callable[[Path], None] | None = None,
    fail_after_replace: bool = False,
) -> Path:
    """Create a durable journal and CAS-replace one authoritative state file."""
    state_bytes, candidate, evidence_pin = prepare_candidate(
        state_path, evidence_path, validate_evidence
    )
    if after_prepare is not None:
        after_prepare(state_path)
    # Keep the byte-for-byte reviewed preimage that produced ``candidate``.
    candidate_bytes = (json.dumps(candidate, indent=2, sort_keys=True) + "\n").encode("utf-8")
    pre_state_sha256 = hashlib.sha256(state_bytes).hexdigest()
    candidate_state_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    if (
        expected_pre_state_sha256 is not None
        and pre_state_sha256 != expected_pre_state_sha256
    ):
        raise ApplyError("live pre-state differs from the human-reviewed pre-state")
    if (
        expected_candidate_state_sha256 is not None
        and candidate_state_sha256 != expected_candidate_state_sha256
    ):
        raise ApplyError("derived candidate differs from the human-reviewed candidate")
    if transaction_dir.exists():
        raise ApplyError("prior E8 baseline-state transaction exists; inspect or recover it")
    transaction_dir.mkdir(mode=0o700, parents=True)
    backup = transaction_dir / "autopilot_state.json.before"
    candidate_path = transaction_dir / "autopilot_state.json.candidate"
    write_bytes_atomic(backup, state_bytes)
    write_bytes_atomic(candidate_path, candidate_bytes)
    journal_path = transaction_dir / "transaction.json"
    journal: dict[str, Any] = {
        "schema": JOURNAL_SCHEMA,
        "state": "prepared",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "evidence": {
            "path": str(evidence_pin.manifest_path),
            "sha256": evidence_pin.manifest_sha256,
            "run_seal_path": str(evidence_pin.seal_path),
            "run_seal_sha256": evidence_pin.seal_sha256,
        },
        "failure": None,
        "state_file": {
            "destination": str(state_path.resolve()),
            "backup": str(backup.resolve()),
            "pre_sha256": pre_state_sha256,
            "candidate_sha256": candidate_state_sha256,
            "replace_intent_at": None,
            "applied": False,
            "rollback_conflict": None,
        },
    }
    write_json_atomic(journal_path, journal)
    record = journal["state_file"]
    try:
        if before_replace is not None:
            before_replace(state_path)
        record["replace_intent_at"] = utc_now()
        update_journal(journal_path, journal, "applying")
        evidence_pin.verify()
        if sha256_path(state_path) != record["pre_sha256"]:
            raise CASMismatch("AutoPilot state changed after preflight; refusing to clobber it")
        if sha256_path(candidate_path) != record["candidate_sha256"]:
            raise CASMismatch("transaction candidate changed before replacement")
        os.replace(candidate_path, state_path)
        fsync_dir(state_path.parent)
        if sha256_path(state_path) != record["candidate_sha256"]:
            raise CASMismatch("post-replace state hash mismatch")
        if fail_after_replace:
            raise ApplyError("injected failure after replacement")
        record["applied"] = True
        record["applied_at"] = utc_now()
        update_journal(journal_path, journal, "committed")
        return journal_path
    except Exception as exc:
        journal["failure"] = str(exc)
        update_journal(journal_path, journal, "failed")
        if not rollback(journal_path, journal):
            if isinstance(exc, CASMismatch):
                raise exc
            raise ApplyError("apply failed; manual recovery is required") from exc
        raise


def recover_transaction(transaction_dir: Path, state_path: Path) -> tuple[Path, bool]:
    try:
        canonical_transaction = transaction_dir.resolve(strict=True)
    except OSError as exc:
        raise ApplyError(f"cannot resolve transaction directory: {exc}") from exc
    if (
        canonical_transaction != transaction_dir.absolute()
        or canonical_transaction.is_symlink()
        or not canonical_transaction.is_dir()
    ):
        raise ApplyError("transaction directory is not a canonical real directory")
    journal_path = canonical_transaction / "transaction.json"
    journal = load_json(journal_path, "transaction journal")
    record = journal.get("state_file")
    required_journal = {
        "schema",
        "state",
        "created_at",
        "updated_at",
        "evidence",
        "failure",
        "state_file",
    }
    required_record = {
        "destination",
        "backup",
        "pre_sha256",
        "candidate_sha256",
        "replace_intent_at",
        "applied",
        "rollback_conflict",
    }
    if (
        set(journal) != required_journal
        or journal.get("schema") != JOURNAL_SCHEMA
        or journal.get("state") not in {
            "prepared",
            "applying",
            "failed",
            "rolled_back",
            "manual_recovery_required",
            "committed",
        }
        or not isinstance(record, dict)
        or not required_record.issubset(record)
        or not set(record).issubset(required_record | {"applied_at", "rolled_back_at"})
        or Path(record.get("destination", "")).resolve() != state_path.resolve()
        or Path(record.get("backup", "")).parent.resolve() != canonical_transaction
        or not all(
            isinstance(record.get(field), str)
            and re.fullmatch(r"[0-9a-f]{64}", record[field])
            for field in ("pre_sha256", "candidate_sha256")
        )
        or not isinstance(record.get("applied"), bool)
    ):
        raise ApplyError("transaction journal is not a recoverable canonical E8 state transaction")
    backup = Path(record["backup"])
    if not backup.is_file() or sha256_path(backup) != record.get("pre_sha256"):
        raise ApplyError("transaction backup is missing or has the wrong hash")
    if journal["state"] == "committed":
        if (
            record.get("applied") is not True
            or journal.get("failure") is not None
            or record.get("rollback_conflict") is not None
        ):
            raise ApplyError("committed transaction journal lacks applied-state semantics")
        replace_intent = parse_timestamp(record.get("replace_intent_at"), "replace intent")
        applied_at = parse_timestamp(record.get("applied_at"), "applied timestamp")
        if applied_at < replace_intent:
            raise ApplyError("committed transaction applied timestamp predates replace intent")
        if sha256_path(state_path) != record["candidate_sha256"]:
            raise ApplyError("committed transaction state no longer matches its candidate")
        return journal_path, True
    if not rollback(journal_path, journal):
        raise ApplyError("recovery found a concurrent state edit; manual recovery is required")
    return journal_path, False


def attestation_payload(journal_path: Path, journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "epyc.operator_e8_quality_baseline_state_apply.v1",
        "decision": TOKEN,
        "transaction": str(journal_path.resolve()),
        "transaction_sha256": sha256_path(journal_path),
        "evidence": journal["evidence"],
        "state_sha256": journal["state_file"]["candidate_sha256"],
        "state_applied_at": journal["state_file"]["applied_at"],
    }


def verify_journal_evidence(journal_path: Path, evidence_path: Path) -> None:
    journal = load_json(journal_path, "transaction journal")
    pin = pin_evidence(evidence_path)
    expected = {
        "path": str(pin.manifest_path),
        "sha256": pin.manifest_sha256,
        "run_seal_path": str(pin.seal_path),
        "run_seal_sha256": pin.seal_sha256,
    }
    if journal.get("evidence") != expected:
        raise ApplyError("canonical evidence no longer matches the transaction journal")
    pin.verify()


def finalize_attestation(output: Path, journal_path: Path, state_path: Path) -> None:
    journal = load_json(journal_path, "committed transaction journal")
    if journal.get("state") != "committed":
        raise ApplyError("cannot attest a transaction that did not commit")
    if sha256_path(state_path) != journal["state_file"]["candidate_sha256"]:
        raise ApplyError("live state no longer matches the committed transaction candidate")
    payload = attestation_payload(journal_path, journal)
    if output.exists():
        existing = load_json(output, "existing baseline-state apply attestation")
        if set(existing) != set(payload) or existing != payload:
            raise ApplyError("existing baseline-state attestation does not match committed transaction")
        return
    try:
        write_json_create_only(output, payload)
    except FileExistsError:
        existing = load_json(output, "racing baseline-state apply attestation")
        if set(existing) != set(payload) or existing != payload:
            raise ApplyError("racing baseline-state attestation does not match committed transaction")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--canonical-evidence", type=Path, required=True)
    parser.add_argument("--validator", type=Path, required=True)
    parser.add_argument("--transaction-dir", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--expected-pre-state-sha256")
    parser.add_argument("--expected-candidate-state-sha256")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true")
    group.add_argument("--validate-only", action="store_true")
    group.add_argument("--status", action="store_true")
    group.add_argument("--attest", metavar="TOKEN")
    group.add_argument("--recover", metavar="TOKEN")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.plan:
        print("E8 baseline-state apply plan")
        print("- require the separate read-only sealed-evidence validator to pass")
        print("- require exactly 3x T1=50 and 3x T2=500 E8 protocol observations")
        print("- CAS-replace only baseline_state and history tiers 1/2; preserve tiers 0/3")
        print("- close the E8 hold only in the same atomic state replacement")
        print("- retain a durable preimage and fail closed to manual recovery on conflict")
        return 0
    if args.status:
        print(args.attestation.read_text() if args.attestation.is_file() else "No E8 baseline-state apply attestation exists.")
        return 0
    environment = dict(os.environ)

    def validate() -> None:
        run_evidence_validator(args.validator, args.evidence, environment)
    try:
        expected_hashes = (
            args.expected_pre_state_sha256,
            args.expected_candidate_state_sha256,
        )
        if any(expected_hashes) != all(expected_hashes):
            raise ApplyError("both human-reviewed state hashes are required together")
        if any(
            value is not None
            and (
                len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            )
            for value in expected_hashes
        ):
            raise ApplyError("human-reviewed state hashes must be lowercase SHA-256")
        if args.validate_only:
            state_bytes, candidate, _pin = prepare_candidate(
                args.state, args.evidence, validate
            )
            candidate_bytes = (
                json.dumps(candidate, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            if (
                args.expected_pre_state_sha256 is not None
                and hashlib.sha256(state_bytes).hexdigest()
                != args.expected_pre_state_sha256
            ):
                raise ApplyError(
                    "live pre-state differs from the human-reviewed pre-state"
                )
            if (
                args.expected_candidate_state_sha256 is not None
                and hashlib.sha256(candidate_bytes).hexdigest()
                != args.expected_candidate_state_sha256
            ):
                raise ApplyError(
                    "derived candidate differs from the human-reviewed candidate"
                )
            print("E8 baseline-state apply preflight passed; no files changed.")
            return 0
        if args.recover:
            if args.recover != TOKEN:
                raise ApplyError(f"use --recover {TOKEN} for the human-only recovery")
            if args.evidence.resolve() != args.canonical_evidence.resolve():
                raise ApplyError("human recovery requires the canonical published E8 evidence bundle")
            if autopilot_running():
                raise ApplyError("AutoPilot is running; stop it before recovering baseline state")
            with exclusive_locks(args.state):
                verify_journal_reviewed_state(
                    args.transaction_dir / "transaction.json",
                    args.expected_pre_state_sha256,
                    args.expected_candidate_state_sha256,
                )
                journal_path, finalized = recover_transaction(args.transaction_dir, args.state)
                if finalized:
                    verify_journal_evidence(journal_path, args.evidence)
                    finalize_attestation(args.attestation, journal_path, args.state)
            action = "attestation finalized" if finalized else "precommit state recovered"
            print(f"E8 baseline-state {action}: {args.transaction_dir}")
            return 0
        if args.attest != TOKEN:
            raise ApplyError(f"use --attest {TOKEN} for the human-only state apply")
        if args.evidence.resolve() != args.canonical_evidence.resolve():
            raise ApplyError("human state apply requires the canonical published E8 evidence bundle")
        if autopilot_running():
            raise ApplyError("AutoPilot is running; stop it before applying baseline state")
        with exclusive_locks(args.state):
            journal_path = apply_transaction(
                state_path=args.state,
                transaction_dir=args.transaction_dir,
                evidence_path=args.evidence,
                validate_evidence=validate,
                expected_pre_state_sha256=args.expected_pre_state_sha256,
                expected_candidate_state_sha256=args.expected_candidate_state_sha256,
            )
            verify_journal_evidence(journal_path, args.evidence)
            finalize_attestation(args.attestation, journal_path, args.state)
        print(f"E8 baseline-state apply attestation created: {args.attestation}")
        return 0
    except ApplyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

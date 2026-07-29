#!/usr/bin/env python3
"""Validated transaction support for the human-only E8 scorer amendment."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable
import uuid

import yaml


SCHEMA = "epyc.operator_e8_quality_source_protocol_amendment_proposal.v1"
JOURNAL_SCHEMA = "epyc.e8_quality_source_amendment_transaction.v1"
PROPOSAL_SCHEMA = "epyc.e8_quality_baseline_protocol_proposal.v1"
ERA = "E8"
PROTOCOL_ID = "e8_quality_full_pool_tier_baseline.v2"
OLD_PATTERN = r"\d+"
NEW_PATTERN = r"(\d+)"
TARGETS = {
    "real": ("real_suite_v1", "real_suite_v1_0043"),
    "long": ("long_context", "needle_039"),
}
PROPOSAL_KEYS = {
    "schema",
    "era",
    "protocol",
    "t1_core_path",
    "t1_core_file_sha256",
    "expected_probe_groups",
    "acceptance",
}
PROTOCOL_KEYS = {
    "protocol_id",
    "seed",
    "repetitions",
    "generation_concurrency",
    "scoring_concurrency",
    "baseline_mode",
    "route_policy",
    "selected_ports",
    "runtime_topology",
    "runtime_facts_sha256",
    "runtime_binding",
    "llama_source_provenance",
    "measurement_source_sha256",
    "judge_defaults",
    "expected_probe_groups",
    "tiers",
}
TIER_KEYS = {
    "core_id",
    "n",
    "dataset_sha256",
    "scoring_vector_sha256",
    "vector_sha256",
}


class AmendmentError(RuntimeError):
    """Fail-closed amendment error."""


class CASMismatch(AmendmentError):
    """The destination changed after its reviewed pre-state was established."""


@dataclass(frozen=True)
class AmendmentPaths:
    root: Path
    research: Path
    orchestrator: Path
    real: Path
    long: Path
    pool: Path
    builder: Path
    build_driver: Path
    regenerator: Path
    runner: Path
    research_python: Path
    orchestrator_python: Path
    pool_python: Path
    hf_home: Path
    vl_prefix: Path


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_dir(path.parent)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_dir(path.parent)


def _yaml_rows(path_or_text: Path | str) -> list[dict[str, Any]]:
    text = (
        path_or_text.read_text(encoding="utf-8")
        if isinstance(path_or_text, Path)
        else path_or_text
    )
    payload = yaml.safe_load(text)
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise AmendmentError("source YAML must contain a questions list")
    if not all(isinstance(row, dict) for row in payload["questions"]):
        raise AmendmentError("source YAML contains a non-object question")
    return payload["questions"]


def _row_by_id(rows: list[dict[str, Any]], qid: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("id") == qid]
    if len(matches) != 1:
        raise AmendmentError(f"expected exactly one YAML row for {qid}, got {len(matches)}")
    return matches[0]


def transform_source_text(text: str, qid: str) -> str:
    """Repair one source scalar while preserving all surrounding YAML text."""
    before_rows = _yaml_rows(text)
    before_row = _row_by_id(before_rows, qid)
    if (
        before_row.get("scoring_method") != "exact_match"
        or before_row.get("scoring_config", {}).get("extract_pattern") != OLD_PATTERN
    ):
        raise AmendmentError(f"unexpected source pre-state for {qid}")

    lines = text.splitlines(keepends=True)
    item_re = re.compile(
        rf"^(?P<indent>[ \t]*)-[ \t]+id:[ \t]*['\"]?{re.escape(qid)}['\"]?"
        rf"[ \t]*(?:#.*)?(?:\r?\n)?$"
    )
    starts = [(index, match.group("indent")) for index, line in enumerate(lines) if (match := item_re.match(line))]
    if len(starts) != 1:
        raise AmendmentError(f"cannot locate one indentation-safe YAML block for {qid}")
    start, indent = starts[0]
    next_item_re = re.compile(rf"^{re.escape(indent)}-[ \t]+id:")
    end = next(
        (index for index in range(start + 1, len(lines)) if next_item_re.match(lines[index])),
        len(lines),
    )

    scalar_re = re.compile(
        r"^(?P<prefix>[ \t]*extract_pattern:[ \t]*)"
        r"(?P<value>[^#\r\n]*?)"
        r"(?P<suffix>[ \t]*(?:#.*)?)(?P<newline>\r?\n)?$"
    )
    scalar_matches = [
        (index, match)
        for index in range(start, end)
        if (match := scalar_re.match(lines[index]))
    ]
    if len(scalar_matches) != 1:
        raise AmendmentError(
            f"expected one extract_pattern scalar in {qid} block, got {len(scalar_matches)}"
        )
    index, match = scalar_matches[0]
    lines[index] = (
        match.group("prefix")
        + "'(\\d+)'"
        + match.group("suffix")
        + (match.group("newline") or "")
    )
    repaired = "".join(lines)

    after_rows = _yaml_rows(repaired)
    expected_rows = copy.deepcopy(before_rows)
    expected_row = _row_by_id(expected_rows, qid)
    expected_row["scoring_config"]["extract_pattern"] = NEW_PATTERN
    if after_rows != expected_rows:
        raise AmendmentError(f"source repair changed fields beyond extract_pattern for {qid}")
    if re.compile(_row_by_id(after_rows, qid)["scoring_config"]["extract_pattern"]).groups != 1:
        raise AmendmentError(f"source repair did not produce one capture group for {qid}")
    return repaired


def parse_pool(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    header: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").split("\n"):
        if not raw:
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise AmendmentError("pool row is not an object")
        if value.get("__pool_metadata__"):
            if header is not None:
                raise AmendmentError("pool has multiple metadata headers")
            header = value
        else:
            rows.append(value)
    if header is None:
        raise AmendmentError("pool metadata header is missing")
    return header, rows


def validate_prestate(paths: AmendmentPaths) -> None:
    source_targets = ((paths.real, TARGETS["real"][1]), (paths.long, TARGETS["long"][1]))
    for path, qid in source_targets:
        row = _row_by_id(_yaml_rows(path), qid)
        if (
            row.get("scoring_method") != "exact_match"
            or row.get("scoring_config", {}).get("extract_pattern") != OLD_PATTERN
        ):
            raise AmendmentError(f"unexpected source pre-state for {qid}")
    _header, pool_rows = parse_pool(paths.pool)
    by_key = {(row.get("suite"), row.get("id")): row for row in pool_rows}
    for suite, qid in TARGETS.values():
        row = by_key.get((suite, qid))
        if (
            not isinstance(row, dict)
            or row.get("scoring_method") != "exact_match"
            or row.get("scoring_config", {}).get("extract_pattern") != OLD_PATTERN
        ):
            raise AmendmentError(f"unexpected activated-pool pre-state for {suite}/{qid}")


def validate_pool_runtime(paths: AmendmentPaths) -> None:
    """Verify the pinned pool virtualenv before an amendment can mutate sources.

    ``Path.resolve()`` on a venv's ``bin/python`` selects its base interpreter,
    which loses the venv's site-packages.  Keep the configured executable path
    and prove the required offline pool dependency is importable first.
    """
    try:
        completed = subprocess.run(
            [str(paths.pool_python), "-c", "import yaml"],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError as exc:
        raise AmendmentError(
            f"pinned pool interpreter is not executable: {paths.pool_python}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise AmendmentError(
            f"pinned pool interpreter lacks required yaml dependency: "
            f"{paths.pool_python}" + (f": {detail}" if detail else "")
        )


def validate_candidate(
    old_real: Path,
    old_long: Path,
    old_pool: Path,
    new_real: Path,
    new_long: Path,
    new_pool: Path,
) -> None:
    for qid, before_path, after_path in (
        (TARGETS["real"][1], old_real, new_real),
        (TARGETS["long"][1], old_long, new_long),
    ):
        before = _yaml_rows(before_path)
        after = _yaml_rows(after_path)
        expected = copy.deepcopy(before)
        _row_by_id(expected, qid)["scoring_config"]["extract_pattern"] = NEW_PATTERN
        if after != expected:
            raise AmendmentError(f"YAML changed beyond {qid}.scoring_config.extract_pattern")

    validate_pool_candidate(old_pool, new_pool)


def validate_pool_candidate(old_pool: Path, new_pool: Path) -> None:
    old_header, before_rows = parse_pool(old_pool)
    new_header, after_rows = parse_pool(new_pool)
    old_header = dict(old_header)
    new_header = dict(new_header)
    old_header.pop("generated_at", None)
    new_header.pop("generated_at", None)
    if old_header != new_header:
        raise AmendmentError("regenerated pool metadata changed beyond generated_at")
    if len(before_rows) != len(after_rows):
        raise AmendmentError("regenerated pool row count changed")
    target_keys = set(TARGETS.values())
    for ordinal, (before, after) in enumerate(zip(before_rows, after_rows, strict=True)):
        key = (before.get("suite"), before.get("id"))
        if (after.get("suite"), after.get("id")) != key:
            raise AmendmentError(f"regenerated pool order/identity changed at row {ordinal}")
        expected = copy.deepcopy(before)
        if key in target_keys:
            expected["scoring_config"]["extract_pattern"] = NEW_PATTERN
        if after != expected:
            raise AmendmentError(f"regenerated pool has unrelated drift at {key}")


def git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def validate_manifest(
    manifest_path: Path,
    paths: AmendmentPaths,
    *,
    require_mutable_prestate: bool = True,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {
            "schema",
            "status",
            "decision",
            "operator_token",
            "era",
            "protocol_id",
            "repairs",
            "repository_heads",
            "prestate_sha256",
            "artifact_sha256",
        }
        or manifest.get("schema") != SCHEMA
        or manifest.get("status") != "proposal_only_unattested"
        or manifest.get("decision") != "AMEND-E8-QUALITY-SCORER-SOURCE-20260726"
        or manifest.get("operator_token") != "AMEND-E8-QUALITY-SCORER-SOURCE-20260726"
        or manifest.get("era") != ERA
        or manifest.get("protocol_id") != PROTOCOL_ID
    ):
        raise AmendmentError("amendment hash manifest identity is invalid")
    expected_repairs = [
        {
            "field": "scoring_config.extract_pattern",
            "from": OLD_PATTERN,
            "id": "real_suite_v1_0043",
            "source": "benchmarks/prompts/debug/real_suite_v1.yaml",
            "suite": "real_suite_v1",
            "to": NEW_PATTERN,
        },
        {
            "field": "scoring_config.extract_pattern",
            "from": OLD_PATTERN,
            "id": "needle_039",
            "source": "benchmarks/prompts/debug/long_context.yaml",
            "suite": "long_context",
            "to": NEW_PATTERN,
        },
    ]
    if manifest.get("repairs") != expected_repairs:
        raise AmendmentError("manifest repair contract is invalid")
    roots = {
        "epyc_root": paths.root,
        "epyc_inference_research": paths.research,
        "epyc_orchestrator": paths.orchestrator,
    }
    expected_heads = manifest.get("repository_heads")
    if not isinstance(expected_heads, dict) or set(expected_heads) != set(roots):
        raise AmendmentError("manifest repository head set is invalid")
    for name, repo in roots.items():
        if git_head(repo) != expected_heads[name]:
            raise AmendmentError(f"repository head changed: {name}")

    files = {
        "source_real": paths.real,
        "source_long": paths.long,
        "activated_pool": paths.pool,
        "pool_builder": paths.builder,
        "pool_build_driver": paths.build_driver,
        "runner": paths.runner,
    }
    expected_files = manifest.get("prestate_sha256")
    if not isinstance(expected_files, dict) or set(expected_files) != set(files):
        raise AmendmentError("manifest pre-state file set is invalid")
    for name, path in files.items():
        if not require_mutable_prestate and name in {
            "source_real",
            "source_long",
            "activated_pool",
        }:
            continue
        if not path.is_file() or sha256_path(path) != expected_files[name]:
            raise AmendmentError(f"pre-state hash changed: {name}")

    artifacts = manifest.get("artifact_sha256")
    expected_artifacts = {
        "artifacts/operator/e8_quality_source_amendment.py",
        "artifacts/operator/e8_quality_pool_regenerator.py",
        "artifacts/operator/e8_quality_source_protocol_amendment_20260726.md",
        "tests/test_e8_quality_source_protocol_amendment.py",
    }
    if not isinstance(artifacts, dict) or set(artifacts) != expected_artifacts:
        raise AmendmentError("manifest artifact binding is missing")
    for relative, expected in artifacts.items():
        path = paths.root / relative
        if not path.is_file() or sha256_path(path) != expected:
            raise AmendmentError(f"reviewed artifact hash changed: {relative}")
    return manifest


def validate_recovery_journal(
    paths: AmendmentPaths,
    transaction_root: Path,
    expected_prestate: dict[str, str],
) -> tuple[Path, dict[str, Any]]:
    expected_parent = (
        paths.root / "artifacts/operator/e8_quality_source_amendment_transactions"
    ).resolve()
    try:
        canonical_transaction = transaction_root.resolve(strict=True)
    except OSError as exc:
        raise AmendmentError(f"cannot resolve recovery transaction: {exc}") from exc
    if canonical_transaction != transaction_root.absolute():
        raise AmendmentError("recovery transaction path is not canonical")
    if canonical_transaction.parent != expected_parent:
        raise AmendmentError("recovery transaction is outside the canonical transaction root")
    if not canonical_transaction.is_dir() or canonical_transaction.is_symlink():
        raise AmendmentError("recovery transaction is not a real directory")

    journal_path = canonical_transaction / "transaction.json"
    if (
        not journal_path.is_file()
        or journal_path.is_symlink()
        or journal_path.resolve() != journal_path
    ):
        raise AmendmentError("canonical transaction journal is missing or indirect")
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AmendmentError(f"cannot read recovery journal: {exc}") from exc
    required_top = {
        "schema",
        "state",
        "created_at",
        "updated_at",
        "files",
        "failure",
    }
    if (
        not isinstance(journal, dict)
        or set(journal) not in (required_top, required_top | {"proposal"})
        or journal.get("schema") != JOURNAL_SCHEMA
    ):
        raise AmendmentError("recovery journal schema is invalid")
    if journal.get("state") == "committed":
        raise AmendmentError("committed transactions are not recoverable")
    if journal.get("state") not in {
        "preparing",
        "prepared",
        "applying",
        "failed",
        "rollback_in_progress",
        "rolled_back",
        "manual_recovery_required",
    }:
        raise AmendmentError("recovery journal state is invalid")
    if not isinstance(journal.get("files"), dict):
        raise AmendmentError("recovery journal files field is invalid")
    if not all(
        isinstance(journal.get(field), str) and journal[field]
        for field in ("created_at", "updated_at")
    ):
        raise AmendmentError("recovery journal timestamps are invalid")

    expected_destinations = {
        "real": paths.real.resolve(),
        "long": paths.long.resolve(),
        "pool": paths.pool.resolve(),
    }
    file_names = set(journal["files"])
    if not {"real", "long"}.issubset(file_names) or not file_names.issubset(
        expected_destinations
    ):
        raise AmendmentError("recovery journal file set is invalid")
    required_record = {
        "destination",
        "backup",
        "candidate_sha256",
        "pre_sha256",
        "replace_intent_at",
        "applied",
        "rolled_back",
        "rollback_conflict",
    }
    optional_record = {"applied_at", "rolled_back_at"}
    sha_re = re.compile(r"[0-9a-f]{64}")
    manifest_hash_names = {
        "real": "source_real",
        "long": "source_long",
        "pool": "activated_pool",
    }
    for name, record in journal["files"].items():
        if (
            not isinstance(record, dict)
            or not required_record.issubset(record)
            or not set(record).issubset(required_record | optional_record)
            or not isinstance(record["applied"], bool)
            or not isinstance(record["rolled_back"], bool)
            or sha_re.fullmatch(str(record["candidate_sha256"])) is None
            or sha_re.fullmatch(str(record["pre_sha256"])) is None
            or record["pre_sha256"] != expected_prestate[manifest_hash_names[name]]
        ):
            raise AmendmentError(f"recovery journal record is invalid: {name}")
        if record["replace_intent_at"] is not None and not isinstance(
            record["replace_intent_at"], str
        ):
            raise AmendmentError(f"recovery replace intent is invalid: {name}")
        if record["applied"] and record["replace_intent_at"] is None:
            raise AmendmentError(f"recovery applied record has no intent: {name}")
        for optional_time in ("applied_at", "rolled_back_at"):
            if optional_time in record and not isinstance(record[optional_time], str):
                raise AmendmentError(f"recovery timestamp is invalid: {name}/{optional_time}")
        destination = Path(record["destination"])
        if (
            not destination.is_absolute()
            or destination.resolve() != expected_destinations[name]
            or str(destination.resolve()) != record["destination"]
        ):
            raise AmendmentError(f"recovery destination is invalid: {name}")
        backup = Path(record["backup"])
        try:
            canonical_backup = backup.resolve(strict=True)
        except OSError as exc:
            raise AmendmentError(f"recovery backup is missing: {name}: {exc}") from exc
        if (
            not backup.is_absolute()
            or canonical_backup.parent != canonical_transaction
            or str(canonical_backup) != record["backup"]
            or not canonical_backup.is_file()
            or canonical_backup.is_symlink()
            or sha256_path(canonical_backup) != record["pre_sha256"]
        ):
            raise AmendmentError(f"recovery backup/hash is invalid: {name}")
        current_hash = sha256_path(destination)
        if record["rolled_back"] and current_hash != record["pre_sha256"]:
            raise AmendmentError(f"rolled-back recovery destination changed: {name}")
        if (
            not record["applied"]
            and record["replace_intent_at"] is None
            and current_hash == record["candidate_sha256"]
        ):
            raise AmendmentError(f"candidate appeared without replace intent: {name}")
        if current_hash == record["candidate_sha256"]:
            if name in {"real", "long"}:
                qid = TARGETS[name][1]
                expected_candidate = transform_source_text(
                    canonical_backup.read_text(encoding="utf-8"), qid
                ).encode()
                if hashlib.sha256(expected_candidate).hexdigest() != record["candidate_sha256"]:
                    raise AmendmentError(f"recovery candidate hash is invalid: {name}")
            else:
                validate_pool_candidate(canonical_backup, destination)
        if current_hash not in {
            record["pre_sha256"],
            record["candidate_sha256"],
        }:
            # This is a valid recovery input, but rollback must preserve it and
            # record manual recovery rather than reject before journal update.
            continue
    if "proposal" in journal:
        proposal = journal["proposal"]
        if not isinstance(proposal, dict) or set(proposal) != {
            "path",
            "sha256",
            "schema",
            "era",
            "protocol_id",
            "t2_n",
        }:
            raise AmendmentError("recovery proposal record is invalid")
        proposal_path = Path(proposal["path"])
        try:
            canonical_proposal = proposal_path.resolve(strict=True)
        except OSError as exc:
            raise AmendmentError(f"recovery proposal is missing: {exc}") from exc
        if (
            canonical_proposal.parent != canonical_transaction
            or str(canonical_proposal) != proposal["path"]
            or canonical_proposal.is_symlink()
            or sha256_path(canonical_proposal) != proposal["sha256"]
            or proposal["schema"] != PROPOSAL_SCHEMA
            or proposal["era"] != ERA
            or proposal["protocol_id"] != PROTOCOL_ID
            or proposal["t2_n"] != 500
        ):
            raise AmendmentError("recovery proposal path/hash/identity is invalid")
    return journal_path, journal


def recover_transaction(
    paths: AmendmentPaths,
    transaction_root: Path,
    expected_prestate: dict[str, str],
) -> Path:
    journal_path, journal = validate_recovery_journal(
        paths, transaction_root, expected_prestate
    )
    complete = rollback(journal_path, journal)
    if not complete:
        raise AmendmentError(
            "recovery found concurrent edits; files were left untouched and "
            "journal state is manual_recovery_required"
        )
    return journal_path


def _copy_durable(source: Path, destination: Path) -> None:
    with source.open("rb") as read_handle, destination.open("xb") as write_handle:
        shutil.copyfileobj(read_handle, write_handle)
        write_handle.flush()
        os.fsync(write_handle.fileno())
    fsync_dir(destination.parent)


def _update_journal(path: Path, journal: dict[str, Any], state: str | None = None) -> None:
    if state is not None:
        journal["state"] = state
    journal["updated_at"] = utc_now()
    write_json_atomic(path, journal)


def _add_file_record(
    journal_path: Path,
    journal: dict[str, Any],
    name: str,
    destination: Path,
    backup: Path,
    candidate: Path,
) -> None:
    journal["files"][name] = {
        "destination": str(destination.resolve()),
        "backup": str(backup.resolve()),
        "candidate_sha256": sha256_path(candidate),
        "pre_sha256": sha256_path(backup),
        "replace_intent_at": None,
        "applied": False,
        "rolled_back": False,
        "rollback_conflict": None,
    }
    _update_journal(journal_path, journal)


def cas_replace(
    journal_path: Path,
    journal: dict[str, Any],
    name: str,
    candidate: Path,
    *,
    before_replace: Callable[[str, Path], None] | None = None,
) -> None:
    record = journal["files"][name]
    destination = Path(record["destination"])
    if before_replace is not None:
        before_replace(name, destination)
    record["replace_intent_at"] = utc_now()
    _update_journal(journal_path, journal, "applying")
    # These checks are intentionally adjacent to os.replace: no validation/build
    # or journal work occurs after them and before the atomic replacement.
    current = sha256_path(destination)
    if current != record["pre_sha256"]:
        raise CASMismatch(
            f"CAS mismatch before replacing {name}: expected {record['pre_sha256']}, got {current}"
        )
    candidate_hash = sha256_path(candidate)
    if candidate_hash != record["candidate_sha256"]:
        raise CASMismatch(f"candidate changed before replacing {name}")
    os.replace(candidate, destination)
    fsync_dir(destination.parent)
    if sha256_path(destination) != candidate_hash:
        raise CASMismatch(f"post-replace hash mismatch for {name}")
    record["applied"] = True
    record["applied_at"] = utc_now()
    _update_journal(journal_path, journal, "applying")


def rollback(journal_path: Path, journal: dict[str, Any]) -> bool:
    conflicts = False
    for name in reversed(list(journal["files"])):
        record = journal["files"][name]
        if record.get("rolled_back"):
            continue
        destination = Path(record["destination"])
        current = sha256_path(destination)
        if (
            not record.get("applied")
            and record.get("replace_intent_at") is None
            and current == record["pre_sha256"]
        ):
            continue
        if not record.get("applied") and current == record["pre_sha256"]:
            continue
        if current != record["candidate_sha256"]:
            record["rollback_conflict"] = {
                "observed_sha256": current,
                "at": utc_now(),
                "reason": "destination no longer matches transaction candidate; left untouched",
            }
            conflicts = True
            _update_journal(journal_path, journal, "rollback_in_progress")
            continue
        backup = Path(record["backup"])
        restore = destination.with_name(f".{destination.name}.restore-{uuid.uuid4().hex}")
        _copy_durable(backup, restore)
        if sha256_path(destination) != record["candidate_sha256"]:
            restore.unlink(missing_ok=True)
            record["rollback_conflict"] = {
                "observed_sha256": sha256_path(destination),
                "at": utc_now(),
                "reason": "destination changed during rollback CAS; left untouched",
            }
            conflicts = True
            _update_journal(journal_path, journal, "rollback_in_progress")
            continue
        os.replace(restore, destination)
        fsync_dir(destination.parent)
        if sha256_path(destination) != record["pre_sha256"]:
            raise AmendmentError(f"rollback verification failed for {name}")
        record["rolled_back"] = True
        record["rolled_back_at"] = utc_now()
        _update_journal(journal_path, journal, "rollback_in_progress")
    _update_journal(
        journal_path,
        journal,
        "manual_recovery_required" if conflicts else "rolled_back",
    )
    return not conflicts


def _load_runner_module(runner_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        f"e8_amendment_runner_{uuid.uuid4().hex}", runner_path
    )
    if spec is None or spec.loader is None:
        raise AmendmentError("cannot load E8 runner for independent proposal verification")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_proposal_contract(runner_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    runner = _load_runner_module(runner_path)
    args = runner.parse_args(["--protocol-proposal", "--t2-n", "500"])
    tower = runner.EvalTower(url=args.api_url.rstrip("/"), timeout=args.evaltower_timeout_s)
    expected_tiers: dict[str, dict[str, Any]] = {}
    selected_t2: list[dict[str, Any]] = []
    for tier, n in ((1, args.t1_n), (2, args.t2_n)):
        questions, core_id = runner.question_vector(
            tower,
            tier=tier,
            t1_core_id=args.t1_core_id,
            n=n,
            seed=args.seed,
        )
        runner.validate_source_vector_scorer_config(questions, tier=tier)
        vector = runner.public_vector(
            questions, tier=tier, core_id=core_id, seed=args.seed
        )
        scoring = runner.scoring_vector(
            questions, tier=tier, core_id=core_id, seed=args.seed
        )
        expected_tiers[str(tier)] = {
            "core_id": core_id,
            "n": len(questions),
            "dataset_sha256": runner.dataset_content_sha256(questions),
            "scoring_vector_sha256": canonical_hash(scoring),
            "vector_sha256": canonical_hash(vector),
        }
        if tier == 2:
            selected_t2 = questions
    return expected_tiers, selected_t2


def verify_proposal_document(
    proposal: dict[str, Any],
    expected_tiers: dict[str, dict[str, Any]],
    selected_t2: list[dict[str, Any]],
) -> None:
    if set(proposal) != PROPOSAL_KEYS:
        raise AmendmentError("runner proposal has unexpected or missing top-level keys")
    if proposal["schema"] != PROPOSAL_SCHEMA or proposal["era"] != ERA:
        raise AmendmentError("runner proposal schema/era mismatch")
    protocol = proposal["protocol"]
    if not isinstance(protocol, dict) or set(protocol) != PROTOCOL_KEYS:
        raise AmendmentError("runner proposal protocol shape mismatch")
    if protocol["protocol_id"] != PROTOCOL_ID:
        raise AmendmentError("runner proposal protocol ID mismatch")
    tiers = protocol["tiers"]
    if not isinstance(tiers, dict) or set(tiers) != {"1", "2"}:
        raise AmendmentError("runner proposal tier set mismatch")
    for tier in ("1", "2"):
        if not isinstance(tiers[tier], dict) or set(tiers[tier]) != TIER_KEYS:
            raise AmendmentError(f"runner proposal T{tier} shape mismatch")
        if tiers[tier] != expected_tiers[tier]:
            raise AmendmentError(f"runner proposal T{tier} hashes differ from candidate")
    if tiers["2"]["n"] != 500:
        raise AmendmentError("runner proposal did not preserve T2 n=500")
    by_id = {str(row.get("id") or row.get("qid")): row for row in selected_t2}
    if not set(qid for _suite, qid in TARGETS.values()).issubset(by_id):
        raise AmendmentError("candidate T2=500 vector does not contain both repaired IDs")
    for _suite, qid in TARGETS.values():
        row = by_id[qid]
        if (
            row.get("expected") != "256"
            or row.get("scoring_method") != "exact_match"
            or row.get("scoring_config", {}).get("extract_pattern") != NEW_PATTERN
        ):
            raise AmendmentError(f"candidate T2 semantics mismatch for {qid}")


def run_transaction(
    paths: AmendmentPaths,
    transaction_root: Path,
    *,
    before_replace: Callable[[str, Path], None] | None = None,
    fail_after: str | None = None,
    proposal_factory: Callable[[AmendmentPaths], dict[str, Any]] | None = None,
    proposal_verifier: Callable[[dict[str, Any]], None] | None = None,
) -> Path:
    validate_prestate(paths)
    transaction_root.mkdir(parents=True, exist_ok=False)
    fsync_dir(transaction_root.parent)
    journal_path = transaction_root / "transaction.json"
    journal: dict[str, Any] = {
        "schema": JOURNAL_SCHEMA,
        "state": "preparing",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "files": {},
        "failure": None,
    }
    _update_journal(journal_path, journal)

    backups = {
        "real": transaction_root / "real_suite_v1.yaml.before",
        "long": transaction_root / "long_context.yaml.before",
        "pool": transaction_root / "question_pool.jsonl.before",
    }
    for name, source in (("real", paths.real), ("long", paths.long), ("pool", paths.pool)):
        _copy_durable(source, backups[name])

    candidates = {
        "real": transaction_root / "real_suite_v1.yaml.candidate",
        "long": transaction_root / "long_context.yaml.candidate",
        "pool": transaction_root / "question_pool.jsonl.candidate",
    }
    candidates["real"].write_text(
        transform_source_text(paths.real.read_text(encoding="utf-8"), TARGETS["real"][1]),
        encoding="utf-8",
    )
    candidates["long"].write_text(
        transform_source_text(paths.long.read_text(encoding="utf-8"), TARGETS["long"][1]),
        encoding="utf-8",
    )
    for name, destination in (("real", paths.real), ("long", paths.long)):
        _add_file_record(
            journal_path,
            journal,
            name,
            destination,
            backups[name],
            candidates[name],
        )
    _update_journal(journal_path, journal, "prepared")

    try:
        for name in ("real", "long"):
            cas_replace(
                journal_path,
                journal,
                name,
                candidates[name],
                before_replace=before_replace,
            )
            if fail_after == name:
                raise AmendmentError(f"injected failure after {name}")

        subprocess.run(
            [
                str(paths.pool_python),
                str(paths.regenerator),
                "--research",
                str(paths.research),
                "--output",
                str(candidates["pool"]),
                "--stage",
                str(transaction_root / "pool-regeneration"),
                "--vl-prefix",
                str(paths.vl_prefix),
            ],
            check=True,
            cwd=paths.research,
            env={
                **os.environ,
                "HF_HUB_OFFLINE": "1",
                "HF_DATASETS_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HOME": str(paths.hf_home),
                "HF_HUB_CACHE": str(paths.hf_home / "hub"),
                "TOKENIZERS_PARALLELISM": "false",
            },
        )
        validate_candidate(
            backups["real"],
            backups["long"],
            backups["pool"],
            paths.real,
            paths.long,
            candidates["pool"],
        )
        _add_file_record(
            journal_path,
            journal,
            "pool",
            paths.pool,
            backups["pool"],
            candidates["pool"],
        )
        cas_replace(
            journal_path,
            journal,
            "pool",
            candidates["pool"],
            before_replace=before_replace,
        )
        if fail_after == "pool":
            raise AmendmentError("injected failure after pool")

        validate_candidate(
            backups["real"],
            backups["long"],
            backups["pool"],
            paths.real,
            paths.long,
            paths.pool,
        )
        candidate_hashes = {
            "real": sha256_path(paths.real),
            "long": sha256_path(paths.long),
            "pool": sha256_path(paths.pool),
        }
        if proposal_factory is None:
            completed = subprocess.run(
                [
                    str(paths.orchestrator_python),
                    str(paths.runner),
                    "--protocol-proposal",
                    "--t2-n",
                    "500",
                ],
                check=True,
                text=True,
                capture_output=True,
                cwd=paths.orchestrator,
            )
            proposal = json.loads(completed.stdout)
        else:
            proposal = proposal_factory(paths)
        proposal_path = transaction_root / "protocol-proposal.json"
        write_json_atomic(proposal_path, proposal)
        if proposal_verifier is None:
            expected_tiers, selected_t2 = expected_proposal_contract(paths.runner)
            verify_proposal_document(proposal, expected_tiers, selected_t2)
        else:
            proposal_verifier(proposal)
        if candidate_hashes != {
            "real": sha256_path(paths.real),
            "long": sha256_path(paths.long),
            "pool": sha256_path(paths.pool),
        }:
            raise CASMismatch("authoritative candidate changed during proposal verification")
        journal["proposal"] = {
            "path": str(proposal_path.resolve()),
            "sha256": sha256_path(proposal_path),
            "schema": proposal["schema"],
            "era": proposal["era"],
            "protocol_id": proposal["protocol"]["protocol_id"],
            "t2_n": proposal["protocol"]["tiers"]["2"]["n"],
        }
        _update_journal(journal_path, journal, "committed")
        return journal_path
    except BaseException as exc:
        journal["failure"] = {"type": type(exc).__name__, "message": str(exc), "at": utc_now()}
        _update_journal(journal_path, journal, "failed")
        rollback(journal_path, journal)
        raise


def build_paths(args: argparse.Namespace) -> AmendmentPaths:
    root = args.root.resolve()
    research = args.research.resolve()
    orchestrator = args.orchestrator.resolve()
    return AmendmentPaths(
        root=root,
        research=research,
        orchestrator=orchestrator,
        real=research / "benchmarks/prompts/debug/real_suite_v1.yaml",
        long=research / "benchmarks/prompts/debug/long_context.yaml",
        pool=research / "benchmarks/prompts/question_pool.jsonl",
        builder=research / "scripts/benchmark/question_pool.py",
        build_driver=research
        / "benchmarks/prompts/pool_rebuild_a3_20260721/build_driver.py",
        regenerator=root / "artifacts/operator/e8_quality_pool_regenerator.py",
        runner=orchestrator / "scripts/benchmark/run_e8_quality_baseline_reseed.py",
        # Preserve venv executable symlinks. Resolving them selects the base
        # Python binary and silently drops the venv site-packages.
        research_python=args.research_python.absolute(),
        orchestrator_python=args.orchestrator_python.absolute(),
        pool_python=args.pool_python.absolute(),
        hf_home=args.hf_home.resolve(),
        vl_prefix=args.vl_prefix.resolve(),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--orchestrator", type=Path, required=True)
    parser.add_argument("--research-python", type=Path, required=True)
    parser.add_argument("--orchestrator-python", type=Path, required=True)
    parser.add_argument("--pool-python", type=Path, required=True)
    parser.add_argument("--hf-home", type=Path, required=True)
    parser.add_argument("--vl-prefix", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--recover", type=Path)
    parser.add_argument("--transaction-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = build_paths(args)
    manifest = validate_manifest(
        args.manifest.resolve(),
        paths,
        require_mutable_prestate=args.recover is None,
    )
    if args.recover is not None:
        journal = recover_transaction(
            paths,
            args.recover,
            manifest["prestate_sha256"],
        )
        print(f"recovered E8 amendment transaction: {journal}")
        return 0
    validate_prestate(paths)
    validate_pool_runtime(paths)
    if args.validate_only:
        print("validated pinned E8 amendment proposal; no authoritative data changed")
        return 0
    if args.transaction_root is None:
        raise AmendmentError("--apply requires --transaction-root")
    journal = run_transaction(paths, args.transaction_root.resolve())
    print(f"applied E8 amendment; durable transaction journal: {journal}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AmendmentError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

"""Strict ROOT reader for the prospective S4 Omega per-question A/B capture.

The reader accepts only producer-authored native run files. It reopens the sealed
manifest, records JSONL, request payloads, and immutable suite/prompt snapshots;
it does not infer arm deltas, suite-level outcomes, exact token cost, protocol,
model identity, server identity, or promotion eligibility. Each available native
per-question value is projected through the existing measurement ClaimTuple and
the shared ``claim_tuple.grade()`` ladder.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

RECORD_SCHEMA = "epyc.s4_omega_ab.record.v1"
MANIFEST_SCHEMA = "epyc.s4_omega_ab.manifest.v1"
SUITE_SCHEMA = "epyc.s4_omega_question_suite.v1"
ADAPTER_ID = "vidya.adapters.s4_omega_ab/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "s4-omega-ab-measurement"
TURNS_UNIT = "orchestrator_repl_turn"
ARMS = ("baseline", "s4_omega")
ARM_CATEGORIES = {"baseline": "BASELINE", "s4_omega": "CANDIDATE"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_METRICS = {
    "turns": ("repl_turns", "lower_better", TURNS_UNIT),
    # This is the producer's reported legacy field, not an exact output-token or cost meter.
    "tokens_generated": ("tokens_generated_reported", "lower_better", "reported_tokens_generated"),
    "prompt_tokens": ("prompt_tokens_reported", "lower_better", "backend_reported_prompt_tokens"),
    "passed": ("question_passed", "higher_better", "false_0_true_1"),
    "elapsed_seconds": ("elapsed_seconds", "lower_better", "seconds"),
}
_MAX_MANIFEST = 8 * 1024 * 1024
_MAX_RECORDS = 256 * 1024 * 1024
_MAX_SUITE = 16 * 1024 * 1024
_MAX_PROMPT = 4 * 1024 * 1024
_MAX_TAIL = 16 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique_members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ValueError(f"non-finite JSON number: {value}")


def _loads(raw: bytes, *, what: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_unique_members, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectionError(f"{what} is not strict JSON: {exc}") from exc


def _read_regular(path: Path, *, limit: int, what: str) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise ProjectionError(f"cannot open {what}: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ProjectionError(f"{what} must be a regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ProjectionError(f"{what} exceeds the {limit}-byte reader limit")
        return raw
    finally:
        os.close(fd)


def _digest(value: Any, *, what: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ProjectionError(f"{what} must be a lowercase SHA-256 digest")
    return value


def _sealed(value: Any, *, what: str) -> None:
    if not isinstance(value, dict):
        raise ProjectionError(f"{what} must be an object")
    recorded = _digest(value.get("content_sha256"), what=f"{what}.content_sha256")
    body = dict(value)
    body.pop("content_sha256", None)
    try:
        actual = _sha(_canonical(body))
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"{what} is not canonicalizable: {exc}") from exc
    if recorded != actual:
        raise ProjectionError(f"{what} content_sha256 does not re-derive")


def _safe_relative(value: Any, *, what: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ProjectionError(f"{what} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or "\\" in value:
        raise ProjectionError(f"{what} escapes its run directory")
    return path


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _record_value(row: dict[str, Any], field: str) -> int | float | None:
    value = row.get(field)
    if value is None:
        return None
    if field == "passed":
        if type(value) is not bool:
            raise ProjectionError("record passed must be true, false, or null")
        return int(value)
    if field == "elapsed_seconds":
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ProjectionError("record elapsed_seconds must be finite and non-negative")
        return value
    if not _nonnegative_int(value):
        raise ProjectionError(f"record {field} must be a non-negative integer or null")
    return value


def _expected_request_record(row: dict[str, Any], *, run_id: str, question: dict,
                             arm_id: str, question_index: int, timeout_s: Any) -> None:
    payload = row.get("request_payload")
    request_digest = row.get("request_sha256")
    if not isinstance(payload, dict) or not isinstance(request_digest, str):
        raise ProjectionError("live record has no captured request payload and digest")
    _digest(request_digest, what="record.request_sha256")
    if _sha(_canonical(payload)) != request_digest:
        raise ProjectionError("record request_sha256 does not match request_payload")
    if row.get("request_sha256_source") != "http_json_payload":
        raise ProjectionError("live record request digest is not from the captured HTTP JSON payload")
    if row.get("request_sha256_unavailable_reason") is not None:
        raise ProjectionError("captured request has an unavailable-reason marker")
    expected_order = ("baseline", "s4_omega") if question_index % 2 == 0 else ("s4_omega", "baseline")
    order = expected_order.index(arm_id)
    if row.get("order_within_pair") != order:
        raise ProjectionError("record order_within_pair does not match the producer's alternating design")
    batch_id = f"{run_id}:{question['id']}:{arm_id}"
    if row.get("batch_id") != batch_id:
        raise ProjectionError("record batch_id does not bind its run, question, and arm")
    if payload.get("prompt") != question.get("prompt"):
        raise ProjectionError("captured request prompt does not match its immutable suite question")
    if payload.get("force_role") != "frontdoor" or payload.get("force_mode") != "repl":
        raise ProjectionError("captured request is not frontdoor:repl")
    if payload.get("batch_id") != batch_id:
        raise ProjectionError("captured request batch_id does not match the record identity")
    if payload.get("cache_prompt") is not False or payload.get("allow_delegation") is not False:
        raise ProjectionError("captured request does not preserve the producer's no-cache/no-delegation policy")
    if payload.get("request_priority") != "background" or payload.get("workload_class") != "eval_batch":
        raise ProjectionError("captured request priority/workload is foreign")
    if payload.get("real_mode") is not True or payload.get("scoring_method") != question.get("scoring_method"):
        raise ProjectionError("captured request execution/scorer fields differ from the suite")
    if payload.get("timeout_s") != timeout_s:
        raise ProjectionError("captured request timeout does not match manifest request policy")
    prompt_root = payload.get("x_orchestrator_prompt_root")
    if not isinstance(prompt_root, str) or not prompt_root:
        raise ProjectionError("captured request prompt_root is absent")
    prompt_root_path = PurePosixPath(prompt_root)
    if prompt_root_path.name != arm_id or not prompt_root_path.parent.name.startswith(f"s4-omega-{run_id}-"):
        raise ProjectionError("captured request prompt_root does not bind this run and arm")


def _verify_recovery(manifest_path: Path, manifest: dict[str, Any],
                     records_path: Path, recovered_records: bytes) -> None:
    """Verify that a recovered view preserves the original bytes and their valid prefix."""
    recovery_keys = {"recovery_original_manifest_sha256", "recovery_original_records_sha256",
                     "recovery_tail_file", "recovery_tail_sha256"}
    present = recovery_keys & set(manifest)
    if not present:
        if manifest_path.name != f"{manifest.get('run_id')}.manifest.json":
            raise ProjectionError("partial/refused capture is not the original run manifest")
        return
    if present != recovery_keys:
        raise ProjectionError("recovery custody fields must be all present or all absent")
    run_id = manifest["run_id"]
    if manifest_path.name != f"{run_id}.recovered.manifest.json":
        raise ProjectionError("recovery manifest filename does not bind its run id")
    if records_path.name != f"{run_id}.recovered.records.jsonl":
        raise ProjectionError("recovery records filename does not bind its run id")
    original_manifest_path = manifest_path.parent / f"{run_id}.manifest.json"
    original_manifest_bytes = _read_regular(original_manifest_path, limit=_MAX_MANIFEST,
                                             what="original partial manifest")
    if _sha(original_manifest_bytes) != _digest(manifest.get("recovery_original_manifest_sha256"),
                                                 what="recovery_original_manifest_sha256"):
        raise ProjectionError("recovery original manifest digest does not match original bytes")
    original = _loads(original_manifest_bytes, what="original partial manifest")
    _sealed(original, what="original partial manifest")
    if (original.get("schema") != MANIFEST_SCHEMA or original.get("run_id") != run_id
            or original.get("synthetic") is not False or original.get("run_status") != "running"):
        raise ProjectionError("recovery original is not this run's live running manifest")
    original_name = _safe_relative(original.get("records_file"), what="original records_file")
    if original_name.name != f"{run_id}.records.jsonl" or len(original_name.parts) != 1:
        raise ProjectionError("recovery original records file does not bind its run id")
    original_records_path = manifest_path.parent.joinpath(*original_name.parts)
    original_bytes = _read_regular(original_records_path, limit=_MAX_RECORDS,
                                   what="original partial records")
    if _sha(original_bytes) != _digest(manifest.get("recovery_original_records_sha256"),
                                        what="recovery_original_records_sha256"):
        raise ProjectionError("recovery original records digest does not match original bytes")
    if not original_bytes.startswith(recovered_records):
        raise ProjectionError("recovered records are not the original records valid-prefix bytes")
    tail = original_bytes[len(recovered_records):]
    tail_name = manifest.get("recovery_tail_file")
    tail_digest = manifest.get("recovery_tail_sha256")
    if tail:
        safe_tail = _safe_relative(tail_name, what="recovery_tail_file")
        if len(safe_tail.parts) != 1 or safe_tail.name != f"{run_id}.recovery-tail.bin":
            raise ProjectionError("recovery tail must be a sibling file")
        tail_bytes = _read_regular(manifest_path.parent.joinpath(*safe_tail.parts),
                                   limit=_MAX_TAIL, what="recovery tail")
        if tail_bytes != tail or _sha(tail_bytes) != _digest(tail_digest, what="recovery_tail_sha256"):
            raise ProjectionError("recovery tail bytes differ from the original suffix")
    elif tail_name is not None or tail_digest is not None:
        raise ProjectionError("recovery declares a tail when original and recovered bytes match")


@dataclass(frozen=True)
class NativeMetric:
    manifest_path: Path
    records_path: Path
    manifest: dict[str, Any]
    record: dict[str, Any]
    metric_field: str
    value: int | float
    records_sha256: str
    manifest_sha256: str


def _open_run(manifest_path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]], Path, bytes, str, str]:
    path = Path(manifest_path)
    manifest_bytes = _read_regular(path, limit=_MAX_MANIFEST, what="manifest")
    manifest = _loads(manifest_bytes, what="manifest")
    _sealed(manifest, what="manifest")
    if _canonical(manifest) + b"\n" != manifest_bytes:
        raise ProjectionError("manifest is not producer-canonical JSON")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ProjectionError(f"manifest schema must be {MANIFEST_SCHEMA}")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ProjectionError("manifest run_id is malformed")
    if path.name not in {f"{run_id}.manifest.json", f"{run_id}.recovered.manifest.json"}:
        raise ProjectionError("manifest filename does not bind its run id")
    if manifest.get("synthetic") is True or manifest.get("run_status") == "synthetic":
        return manifest, [], path.parent, b"", _sha(manifest_bytes), ""
    if manifest.get("synthetic") is not False:
        raise ProjectionError("manifest synthetic must be exactly false for a live capture")
    status = manifest.get("run_status")
    if status not in {"complete", "partial", "refused"}:
        raise ProjectionError(f"run_status {status!r} is not a stopped native capture")
    if manifest.get("measurement_status") != "candidate_observation":
        raise ProjectionError("manifest measurement_status must remain candidate_observation")
    if manifest.get("promotion_claim") is not False:
        raise ProjectionError("manifest must not claim promotion")
    if manifest.get("protocol_id") is not None:
        raise ProjectionError("manifest protocol_id must remain unknown")
    if manifest.get("protocol_id_unavailable_reason") != "not_pre_registered":
        raise ProjectionError("manifest protocol identity must retain its unavailable reason")
    for field in ("model_identity", "server_identity"):
        if manifest.get(field) is not None:
            raise ProjectionError(f"manifest {field} must remain unknown")
    for field in ("model_identity_unavailable_reason", "server_identity_unavailable_reason"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ProjectionError(f"manifest {field} must preserve the unknown reason")
    if manifest.get("role") != "frontdoor" or manifest.get("mode") != "repl":
        raise ProjectionError("manifest role/mode must be frontdoor:repl")
    if manifest.get("turns_unit") != TURNS_UNIT:
        raise ProjectionError("manifest turns_unit does not match the producer contract")
    if manifest.get("arm_order_strategy") != "alternating baseline-first and s4_omega-first by suite order":
        raise ProjectionError("manifest arm order strategy is foreign")
    request_policy = manifest.get("request_policy")
    if not isinstance(request_policy, dict) or any(request_policy.get(key) != value for key, value in {
            "allow_delegation": False, "cache_prompt": False, "request_priority": "background",
            "workload_class": "eval_batch"}.items()):
        raise ProjectionError("manifest request policy is foreign")
    timeout_s = request_policy.get("timeout_s")
    if type(timeout_s) is not int or timeout_s < 1:
        raise ProjectionError("manifest request_policy.timeout_s must be a positive integer")
    for field in ("runner_source_sha256", "vidya_adapter_sha256", "openapi_sha256"):
        _digest(manifest.get(field), what=f"manifest.{field}")
    adapter_path = manifest.get("vidya_adapter")
    if not isinstance(adapter_path, str) or not adapter_path.replace("\\", "/").endswith(
            "/scripts/vidya/adapters/s4_omega_ab.py"):
        raise ProjectionError("manifest vidya_adapter does not name the S4 Omega ROOT reader")

    records_name = _safe_relative(manifest.get("records_file"), what="records_file")
    if len(records_name.parts) != 1 or records_name.name not in {
            f"{run_id}.records.jsonl", f"{run_id}.recovered.records.jsonl"}:
        raise ProjectionError("records_file must be the run's original or recovered JSONL")
    records_path = path.parent.joinpath(*records_name.parts)
    records_bytes = _read_regular(records_path, limit=_MAX_RECORDS, what="records JSONL")
    records_digest = _sha(records_bytes)
    if records_digest != _digest(manifest.get("records_file_sha256"), what="records_file_sha256"):
        raise ProjectionError("manifest records_file_sha256 does not match JSONL bytes")
    if records_bytes and not records_bytes.endswith(b"\n"):
        raise ProjectionError("records JSONL has an incomplete final line; recover to a separate view first")
    rows: list[dict[str, Any]] = []
    lines = records_bytes.splitlines(keepends=True)
    for line_number, line in enumerate(lines, start=1):
        if not line.endswith(b"\n") or line == b"\n":
            raise ProjectionError(f"records JSONL line {line_number} is not a complete record")
        row = _loads(line[:-1], what=f"record line {line_number}")
        _sealed(row, what=f"record line {line_number}")
        if _canonical(row) + b"\n" != line:
            raise ProjectionError(f"record line {line_number} is not producer-canonical JSON")
        rows.append(row)
    if type(manifest.get("record_count")) is not int or manifest["record_count"] != len(rows):
        raise ProjectionError("manifest record_count does not match records JSONL")
    hashes = [row["content_sha256"] for row in rows]
    if manifest.get("record_sha256s") != hashes:
        raise ProjectionError("manifest record_sha256s do not match native records")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ProjectionError("manifest schema changed during read")
    _verify_recovery(path, manifest, records_path, records_bytes)
    _validate_run_joins(manifest, rows, path, timeout_s=timeout_s)
    return manifest, rows, records_path, records_bytes, records_digest, _sha(manifest_bytes)


def _validate_run_joins(manifest: dict[str, Any], rows: list[dict[str, Any]],
                        manifest_path: Path, *, timeout_s: int) -> None:
    run_id = manifest["run_id"]
    suite_id = manifest.get("suite_id")
    suite_digest = _digest(manifest.get("suite_sha256"), what="manifest suite_sha256")
    if not isinstance(suite_id, str) or not suite_id:
        raise ProjectionError("manifest suite_id is absent")
    expected_manifest_validation = (
        "pending" if not rows else
        "incomplete" if any(row.get("schema_validation") == "incomplete" for row in rows) else "complete"
    )
    if manifest.get("schema_validation") != expected_manifest_validation:
        raise ProjectionError("stopped manifest schema_validation is invalid")
    status_complete = manifest.get("run_status") == "complete"
    if status_complete:
        if manifest.get("schema_validation") != "complete":
            raise ProjectionError("complete run_status requires complete schema_validation")
    elif manifest.get("run_status") == "partial":
        if not isinstance(manifest.get("failure"), str) or not manifest["failure"]:
            raise ProjectionError("partial manifest must retain the producer failure reason")
    elif manifest.get("run_status") == "refused":
        if not rows or manifest.get("schema_validation") != "incomplete":
            raise ProjectionError("refused run must retain incomplete native records")

    question_ids = manifest.get("question_ids")
    if not isinstance(question_ids, list) or not question_ids or any(
            not isinstance(qid, str) or not qid for qid in question_ids):
        raise ProjectionError("manifest question_ids must be a non-empty string list")
    if len(set(question_ids)) != len(question_ids):
        raise ProjectionError("manifest question_ids must be unique")
    snapshot_dir = _safe_relative(manifest.get("source_snapshot_dir"), what="source_snapshot_dir")
    if len(snapshot_dir.parts) != 1 or snapshot_dir.name != f"{run_id}.sources":
        raise ProjectionError("source_snapshot_dir does not bind this run")
    suite_snapshot = _safe_relative(manifest.get("suite_snapshot"), what="suite_snapshot")
    if suite_snapshot.parent != snapshot_dir or suite_snapshot.name != "suite.json":
        raise ProjectionError("suite_snapshot must be this run's sources/suite.json")
    suite_path = manifest_path.parent.joinpath(*suite_snapshot.parts)
    try:
        snapshot_info = manifest_path.parent.joinpath(*snapshot_dir.parts).lstat()
    except OSError as exc:
        raise ProjectionError(f"source snapshot directory is unavailable: {exc}") from exc
    if not stat.S_ISDIR(snapshot_info.st_mode) or stat.S_ISLNK(snapshot_info.st_mode):
        raise ProjectionError("source snapshot directory must be a non-symlink directory")
    suite_bytes = _read_regular(suite_path, limit=_MAX_SUITE, what="suite snapshot")
    if _sha(suite_bytes) != _digest(manifest.get("suite_snapshot_sha256"), what="suite_snapshot_sha256"):
        raise ProjectionError("suite snapshot digest does not match manifest")
    suite = _loads(suite_bytes, what="suite snapshot")
    if _canonical(suite) + b"\n" != suite_bytes:
        raise ProjectionError("suite snapshot is not canonical producer JSON")
    if suite.get("schema") != SUITE_SCHEMA or suite.get("suite_id") != suite_id:
        raise ProjectionError("suite snapshot schema/id does not match manifest")
    questions = suite.get("questions")
    if not isinstance(questions, list) or [q.get("id") for q in questions if isinstance(q, dict)] != question_ids:
        raise ProjectionError("suite snapshot questions do not match manifest question_ids")
    if any(not isinstance(q, dict) or not isinstance(q.get("id"), str) or not q["id"]
           or any(not isinstance(q.get(field), str) for field in ("prompt", "expected", "scoring_method"))
           or not isinstance(q.get("scoring_config", {}), dict) for q in questions):
        raise ProjectionError("suite snapshot contains a malformed question/scorer contract")
    question_by_id = {q["id"]: q for q in questions}

    arms = manifest.get("arms")
    if (not isinstance(arms, list) or len(arms) != len(ARMS)
            or any(not isinstance(a, dict) for a in arms)
            or [a.get("arm_id") for a in arms] != list(ARMS)):
        raise ProjectionError("manifest arms must declare baseline then s4_omega")
    prompt_snapshots = manifest.get("prompt_snapshots")
    if not isinstance(prompt_snapshots, dict) or set(prompt_snapshots) != set(ARMS):
        raise ProjectionError("manifest prompt_snapshots must cover both declared arms")
    arm_digests: dict[str, str] = {}
    for arm in arms:
        arm_id = arm.get("arm_id")
        expected_source = "root_lm_system.md" if arm_id == "baseline" else "root_lm_system.s4_omega.md"
        if arm.get("prompt_source") != f"orchestration/prompts/{expected_source}":
            raise ProjectionError(f"manifest prompt_source is foreign for arm {arm_id}")
        arm_digest = _digest(arm.get("prompt_sha256"), what=f"arms[{arm_id}].prompt_sha256")
        ref = prompt_snapshots[arm_id]
        if not isinstance(ref, dict):
            raise ProjectionError(f"prompt snapshot ref for {arm_id} must be an object")
        expected_file = f"{arm_id}.root_lm_system.md"
        if ref.get("file") != expected_file:
            raise ProjectionError(f"prompt snapshot filename is foreign for arm {arm_id}")
        snapshot_digest = _digest(ref.get("sha256"), what=f"prompt_snapshots.{arm_id}.sha256")
        prompt_path = manifest_path.parent / snapshot_dir.name / expected_file
        prompt_bytes = _read_regular(prompt_path, limit=_MAX_PROMPT, what=f"{arm_id} prompt snapshot")
        if _sha(prompt_bytes) != snapshot_digest or snapshot_digest != arm_digest:
            raise ProjectionError(f"{arm_id} prompt snapshot does not match its arm digest")
        arm_digests[arm_id] = arm_digest

    pairs: set[tuple[str, str]] = set()
    prefix = []
    expected_sequence = [(qid, arm) for i, qid in enumerate(question_ids)
                         for arm in (("baseline", "s4_omega") if i % 2 == 0 else ("s4_omega", "baseline"))]
    for row in rows:
        if row.get("schema") != RECORD_SCHEMA:
            raise ProjectionError("record schema is foreign")
        if row.get("synthetic") is not False:
            raise ProjectionError("synthetic or unmarked record is not a measurement")
        if row.get("run_id") != run_id or row.get("suite_id") != suite_id or row.get("suite_sha256") != suite_digest:
            raise ProjectionError("record run/suite identity does not match its manifest")
        if row.get("protocol_id") is not None or row.get("protocol_id_unavailable_reason") != "not_pre_registered":
            raise ProjectionError("record protocol identity must remain unknown")
        if row.get("promotion_claim") is not False:
            raise ProjectionError("record must not claim promotion")
        for identity_field in ("model_identity", "server_identity"):
            reason_field = f"{identity_field}_unavailable_reason"
            if row.get(identity_field) is not None or not isinstance(row.get(reason_field), str) or not row[reason_field]:
                raise ProjectionError(f"record {identity_field} must remain unknown with its reason")
        qid, arm_id = row.get("question_id"), row.get("arm_id")
        if qid not in question_by_id or arm_id not in ARM_CATEGORIES:
            raise ProjectionError("record question/arm identity is outside the pinned run")
        pair = (qid, arm_id)
        if pair in pairs:
            raise ProjectionError("duplicate native record for one question and arm")
        pairs.add(pair)
        expected_index = len(prefix)
        if expected_index >= len(expected_sequence) or pair != expected_sequence[expected_index]:
            raise ProjectionError("record order does not match the producer's alternating sequence")
        prefix.append(pair)
        if row.get("role") != "frontdoor" or row.get("mode") != "repl" or row.get("turns_unit") != TURNS_UNIT:
            raise ProjectionError("record role/mode/turn unit is foreign")
        if row.get("prompt_sha256") != arm_digests[arm_id]:
            raise ProjectionError("record prompt digest does not match the immutable arm snapshot")
        question = question_by_id[qid]
        if row.get("question") != question:
            raise ProjectionError("record question/gold/scorer config differs from the immutable suite")
        _expected_request_record(row, run_id=run_id, question=question,
                                 arm_id=arm_id, question_index=question_ids.index(qid),
                                 timeout_s=timeout_s)
        response = row.get("response")
        if not isinstance(response, dict):
            raise ProjectionError("record response must retain the original response object")
        # Re-derive metric parsing, while keeping the scorer's boolean and reason as authored.
        metric_errors = []
        for field in ("turns", "tokens_generated", "prompt_tokens"):
            value = row.get(field)
            reason_key = {"turns": "response_missing_turns", "tokens_generated": "response_missing_tokens_generated",
                          "prompt_tokens": "response_missing_prompt_tokens"}[field]
            invalid_key = {"turns": "response_invalid_turns", "tokens_generated": "response_invalid_tokens_generated",
                           "prompt_tokens": "response_invalid_prompt_tokens"}[field]
            source_has = field in response
            raw_value = response.get(field)
            valid = _nonnegative_int(raw_value)
            expected_reason = None if valid else (reason_key if not source_has else invalid_key)
            if row.get(field) != (raw_value if valid else None):
                raise ProjectionError(f"record {field} does not match the original response")
            if row.get(f"{field}_unavailable_reason") not in (expected_reason, None):
                # turns/tokens have no dedicated reason field; only prompt_tokens does.
                if field == "prompt_tokens" or row.get(f"{field}_unavailable_reason") is not None:
                    raise ProjectionError(f"record {field} unavailable reason is inconsistent")
            if expected_reason:
                metric_errors.append(expected_reason)
        if row.get("prompt_tokens_unavailable_reason") != (
                None if _nonnegative_int(response.get("prompt_tokens")) else
                ("response_missing_prompt_tokens" if "prompt_tokens" not in response else "response_invalid_prompt_tokens")):
            raise ProjectionError("prompt_tokens_unavailable_reason is inconsistent")
        passed = row.get("passed")
        if passed is not None and type(passed) is not bool:
            raise ProjectionError("record passed must preserve a boolean or unknown")
        if passed is None and (not isinstance(row.get("score_unavailable_reason"), str)
                               or not row["score_unavailable_reason"]):
            raise ProjectionError("unknown scorer outcome must retain its reason")
        native_error = response.get("error") or response.get("error_detail")
        answer = response.get("answer")
        if native_error and (passed is not False or row.get("score_unavailable_reason") != str(native_error)):
            raise ProjectionError("response error must be preserved as a failed native scorer outcome")
        if not native_error and not isinstance(answer, str) and (
                passed is not None or row.get("score_unavailable_reason") != "response_missing_answer"):
            raise ProjectionError("missing native answer must remain an unknown scorer outcome")
        if passed is not None and row.get("score_unavailable_reason") not in (None, ""):
            # Producer uses a scorer reason only for an error/refusal or unknown result.
            if not (response.get("error") or response.get("error_detail")):
                raise ProjectionError("known scorer outcome has an unexplained unavailable reason")
        if not isinstance(row.get("metric_unavailable_reasons"), list) or any(
                not isinstance(x, str) or not x for x in row["metric_unavailable_reasons"]):
            raise ProjectionError("metric_unavailable_reasons must be a string list")
        if not set(metric_errors).issubset(set(row["metric_unavailable_reasons"])):
            raise ProjectionError("metric_unavailable_reasons omit a missing native metric")
        score_reason = row.get("score_unavailable_reason")
        if score_reason:
            if not isinstance(score_reason, str) or score_reason not in row["metric_unavailable_reasons"]:
                raise ProjectionError("score_unavailable_reason is not represented in native unavailable reasons")
        if row.get("schema_validation") not in {"complete", "incomplete"}:
            raise ProjectionError("record schema_validation is invalid")
        request_problem = row.get("request_sha256_unavailable_reason")
        if request_problem not in (None, ""):
            raise ProjectionError("captured request is marked unavailable")
        if row.get("schema_validation") == "complete" and row["metric_unavailable_reasons"]:
            raise ProjectionError("record cannot be complete with unavailable native metrics")
        if row.get("schema_validation") == "incomplete" and not row["metric_unavailable_reasons"]:
            raise ProjectionError("incomplete record has no native unavailable reason")
        if row.get("elapsed_seconds") is None:
            raise ProjectionError("record elapsed_seconds is absent; no timed observation can be projected")
        _record_value(row, "elapsed_seconds")
    if manifest.get("run_status") == "complete":
        if len(rows) != len(expected_sequence) or prefix != expected_sequence:
            raise ProjectionError("complete run does not contain every alternating question/arm record")
        if any(row.get("schema_validation") != "complete" for row in rows):
            raise ProjectionError("complete run contains an incomplete native record")
    if status_complete and manifest.get("schema_validation") != "complete":
        raise ProjectionError("complete run schema status is inconsistent")


def native_rows(manifest_path: str | Path) -> tuple[NativeMetric, ...]:
    """Read one original or recovered manifest; synthetic fixtures are declined."""
    manifest, rows, records_path, _raw, records_digest, manifest_digest = _open_run(manifest_path)
    if not rows and manifest.get("synthetic") is True:
        return ()
    result = []
    manifest_path = Path(manifest_path)
    for row in rows:
        for field, (metric, _direction, _unit) in _METRICS.items():
            value = _record_value(row, field)
            if value is None:
                continue
            result.append(NativeMetric(manifest_path, records_path, manifest, row,
                                       field, value, records_digest, manifest_digest))
    return tuple(result)


def _status_reason(native: NativeMetric) -> str:
    manifest, row = native.manifest, native.record
    parts = []
    status = manifest.get("run_status")
    if status != "complete":
        parts.append(f"capture status={status}")
    if row.get("metric_unavailable_reasons"):
        parts.append("unavailable=" + ",".join(row["metric_unavailable_reasons"]))
    if manifest.get("failure"):
        parts.append("failure=" + str(manifest["failure"]))
    parts.append("protocol/model/server identity unknown; no promotion claim")
    return "; ".join(parts)[:300]


def _reopen_native_metric(native: NativeMetric) -> NativeMetric:
    """Re-read the custody chain before a tuple may claim verified attestation.

    ``NativeMetric`` is a convenience carrier, not a trust boundary: it is publicly
    constructible and its nested mappings are mutable. Reopen the run and match the
    exact manifest, records artifact, selected row, field, value, and digests before
    projecting anything.
    """
    manifest_path = Path(native.manifest_path)
    manifest, rows, records_path, _raw, records_digest, manifest_digest = _open_run(manifest_path)
    if native.records_path != records_path:
        raise ProjectionError("reader result records_path changed after native_rows")
    if native.manifest != manifest:
        raise ProjectionError("reader result manifest changed after native_rows")
    if native.manifest_sha256 != manifest_digest or native.records_sha256 != records_digest:
        raise ProjectionError("reader result custody digest changed after native_rows")
    if not isinstance(native.record, dict):
        raise ProjectionError("reader result record must remain an object")
    record_digest = native.record.get("content_sha256")
    matches = [row for row in rows if row.get("content_sha256") == record_digest]
    if len(matches) != 1 or matches[0] != native.record:
        raise ProjectionError("reader result selected record changed or is not unique in the reopened run")
    if native.metric_field not in _METRICS:
        raise ProjectionError("reader result metric field is not a declared native metric")
    value = _record_value(matches[0], native.metric_field)
    if value is None or type(value) is not type(native.value) or value != native.value:
        raise ProjectionError("reader result value does not match its reopened native field")
    return NativeMetric(manifest_path, records_path, manifest, matches[0], native.metric_field,
                        value, records_digest, manifest_digest)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, NativeMetric):
        raise ProjectionError("S4 Omega projection requires a reader-verified native metric")
    native = _reopen_native_metric(native)
    row, manifest = native.record, native.manifest
    field = native.metric_field
    metric, direction, unit = _METRICS[field]
    qid, arm_id, run_id = row["question_id"], row["arm_id"], row["run_id"]
    digest = hashlib.sha256(_canonical({"run_id": run_id, "question_id": qid,
                                        "arm_id": arm_id, "metric": metric,
                                        "record_sha256": row["content_sha256"]})).hexdigest()
    value_text = "false" if field == "passed" and native.value == 0 else (
        "true" if field == "passed" else repr(native.value))
    exactness = (
        "reported token count only; not an exact output-token or cost measure"
        if field == "tokens_generated" else
        "native scorer result" if field == "passed" else "native per-question value"
    )
    claim = (f"S4 Omega {manifest['run_status']} capture {run_id}, question {qid}, arm {arm_id}: "
             f"{metric}={value_text} ({exactness}). No pair or suite result is inferred; "
             "protocol, model identity, and server identity remain unknown; no promotion claim.")
    return ClaimTuple(
        measurement_id=f"s4omega_{digest[:32]}", metric=metric, value=native.value,
        date="", category=ARM_CATEGORIES[arm_id], claim=claim,
        metric_direction=direction, protocol_id="", reps=1,
        reps_basis="one producer-authored native question-arm observation",
        unit=unit, attestation_path=str(native.records_path),
        attestation_locator=(f"{native.records_path}#record={row['content_sha256']}"),
        attestation_sha256=native.records_sha256, attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND,
        extra={"run_status": manifest["run_status"], "manifest_sha256": native.manifest_sha256,
               "record_sha256": row["content_sha256"], "suite_sha256": row["suite_sha256"],
               "prompt_sha256": row["prompt_sha256"], "request_sha256": row["request_sha256"],
               "native_field": field, "native_value": row[field],
               "model_identity": manifest.get("model_identity"),
               "server_identity": manifest.get("server_identity"),
               "prompt_tokens": row.get("prompt_tokens"),
               "prompt_tokens_unavailable_reason": row.get("prompt_tokens_unavailable_reason")},
        observation={"outcome_native": manifest["run_status"], "outcome_reason": _status_reason(native)},
    )


def frames_for_manifest(manifest_path: str | Path, *, as_of: str) -> list[dict]:
    from claim_tuple import to_frames

    frames: list[dict] = []
    for native in native_rows(manifest_path):
        frames.extend(to_frames(project(native), as_of=as_of,
                                adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames

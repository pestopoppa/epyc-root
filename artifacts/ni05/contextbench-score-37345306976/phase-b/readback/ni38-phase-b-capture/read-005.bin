"""Strict readback and descriptive ClaimTuple projection for ContextBench score receipts.

The adapter never imports captured source. It verifies the producer/source snapshots and
original immutable request, validates the native score matrix, and delegates all warrant to
claim_tuple.grade(). It projects only bounded report integrity; numeric scores stay descriptive
components and are never promoted to ClaimTuple findings by this adapter.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from claim_tuple import ClaimTuple, ProjectionError, register

SCHEMA = "epyc.contextbench_score_capture.v1"
REQUEST_SCHEMA = "epyc.contextbench_score_request.v1"
SCORE_SCHEMA = "epyc.contextbench_discovery_score.v1"
ADAPTER_ID = "vidya.adapters.contextbench_score/v1"
AUTHORITY = "offline_contextbench_report_integrity_no_quality_or_promotion"
TRUSTED_PRODUCER_SHA256 = "3cd780bd53268274c0d9db2550ac204cedd21ce6bc33ac6fa12b4514dca9a879"
TRUSTED_SCORER_SHA256 = "feabbd1c29d5e236a3e81b664d05d15178faeaa7d8418306581b289705b177de"
TRUSTED_PACKER_SHA256 = "7d39ebc4c3afb18dd015a74d3be5adf77352b325771041ceab72d4a4287d2679"
TRUSTED_PACKAGE_SHA256 = "16e20bce77e6470646b90def0e3d653a3bd9fb024b484f7cd034f96ff8a0a5f8"
ARTIFACT_LIMITS = {
    "execution-request.json": 16 * 1024 * 1024,
    "dataset.bin": 512 * 1024 * 1024,
    "tasks.jsonl": 512 * 1024 * 1024,
    "predictions.jsonl": 512 * 1024 * 1024,
    "dispositions.json": 512 * 1024 * 1024,
    "scorer-source.bin": 4 * 1024 * 1024,
    "packer-source.bin": 4 * 1024 * 1024,
    "src-package-source.bin": 4 * 1024 * 1024,
    "producer-source.bin": 4 * 1024 * 1024,
    "scored-output.json": 512 * 1024 * 1024,
}
METRICS = ("file_precision", "file_recall", "file_f1",
           "line_precision", "line_recall", "line_f1")
EXPECTED_SCOPES = (("discovery", None), ("packed", 2000), ("packed", 4000), ("packed", 8000))
RECEIPT_FIELDS = {"schema", "status", "diagnostic_code", "scorer_import_started",
                  "started_utc", "ended_utc", "request", "artifacts", "scored_output",
                  "integrity_result", "integrity_proposition", "receipt_sha256"}
REQUEST_FIELDS = {"schema", "producer_id", "capture_id", "started_utc", "dataset",
                  "applicability", "task_rows",
                  "predictions", "dispositions", "application", "producer_source", "arms",
                  "metric_contract", "environment"}
ARTIFACT_FIELDS = {"name", "sha256", "size"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique_members(pairs):
    value = {}
    for key, member in pairs:
        if key in value:
            raise ValueError("JSON object contains a duplicate member")
        value[key] = member
    return value


def _loads(raw: str):
    return json.loads(raw, object_pairs_hook=_unique_members)


def _regular_bytes(path: Path, *, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)):
            raise ValueError("artifact must be an owned regular file with private mode")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("artifact exceeds its bounded size")
        return raw
    finally:
        os.close(fd)


def _check_custody_chain(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    for candidate in (Path("/"), *absolute.parents[::-1], absolute):
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("receipt custody chain contains a symlink or non-directory")
        if info.st_uid not in (0, os.geteuid()):
            raise ValueError("receipt custody ancestor has an untrusted owner")
        if stat.S_IMODE(info.st_mode) & 0o022:
            if not (info.st_mode & stat.S_ISVTX and info.st_uid == 0):
                raise ValueError("receipt custody ancestor is group/world writable")


def _artifact(run_dir: Path, ref: Any) -> bytes:
    if not isinstance(ref, dict) or set(ref) != ARTIFACT_FIELDS:
        raise ValueError("artifact reference fields are incomplete")
    name, digest, size = ref["name"], ref["sha256"], ref["size"]
    if (not isinstance(name, str) or name not in ARTIFACT_LIMITS
            or not isinstance(digest, str) or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or type(size) is not int or size < 0):
        raise ValueError("artifact reference is malformed")
    raw = _regular_bytes(run_dir / name, limit=ARTIFACT_LIMITS[name])
    if len(raw) != size or _sha(raw) != digest:
        raise ValueError(f"{name} bytes differ from their original digest")
    return raw


def _receipt_path(path: str | Path) -> Path:
    candidate = Path(os.path.abspath(path))
    if candidate.is_dir():
        candidate = candidate / "receipt.json"
    return candidate


def _read_json(raw: bytes, where: str, *, newline: bool = False) -> Mapping[str, Any]:
    try:
        value = _loads(raw.decode("utf-8", errors="strict"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{where} is not UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{where} is not a JSON object")
    expected = _canonical(value) + (b"\n" if newline else b"")
    if raw != expected:
        raise ValueError(f"{where} is not canonical JSON")
    return value


def _jsonl_rows(raw: bytes, label: str) -> list[dict]:
    try:
        text = raw.decode("utf-8", errors="strict")
        lines = text.splitlines()
        if not lines or not text.endswith("\n") or any(not line.strip() for line in lines):
            raise ValueError(f"{label} has blank or missing rows")
        rows = [_loads(line) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is malformed JSONL") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{label} contains a non-object row")
    return rows


def _jsonl_ids(raw: bytes, label: str) -> list[str]:
    rows = _jsonl_rows(raw, label)
    if label == "tasks":
        for row in rows:
            if isinstance(row.get("gold_context"), str):
                _loads(row["gold_context"])
    ids = [row.get("instance_id") for row in rows]
    if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{label} contains missing or duplicate task IDs")
    return ids


def _expected_metrics(counts: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(counts, dict) or set(counts) != {"file", "line"}:
        raise ValueError("per-task counts are malformed")
    values: dict[str, float] = {}
    for granularity in ("file", "line"):
        item = counts.get(granularity)
        if not isinstance(item, dict) or set(item) != {"tp", "fp", "fn"}:
            raise ValueError("per-task counts are malformed")
        if any(type(item[key]) is not int or item[key] < 0 for key in item):
            raise ValueError("per-task counts must be nonnegative integers")
        tp, fp, fn = item["tp"], item["fp"], item["fn"]
        values[granularity + "_precision"] = tp / (tp + fp) if tp + fp else 0.0
        values[granularity + "_recall"] = tp / (tp + fn) if tp + fn else 0.0
        denom = 2 * tp + fp + fn
        values[granularity + "_f1"] = (2 * tp) / denom if denom else 0.0
    return values


def _validate_score_output(raw: bytes, request: Mapping[str, Any], artifacts: Mapping[str, bytes]):
    score = _read_json(raw, "scored output", newline=True)
    if score.get("schema") != SCORE_SCHEMA:
        raise ValueError("scored output schema differs")
    if set(score) != {"schema", "score_semantics", "disposition_semantics", "metric_directions",
                     "eligible_task_ids", "eligible_task_count", "excluded", "arms",
                     "budget_cost_basis", "budget_note"}:
        raise ValueError("scored output fields differ from the reviewed contract")
    if score.get("score_semantics") != "per-task macro; empty prediction and failed attempt score zero":
        raise ValueError("score semantics differ from the reviewed contract")
    if score.get("disposition_semantics") != "exclusion evidence is caller-declared and not independently resolved here":
        raise ValueError("disposition applicability differs")
    arms = request.get("arms")
    if (not isinstance(arms, list) or not arms
            or any(not isinstance(arm, str) or not arm for arm in arms)
            or len(set(arms)) != len(arms)):
        raise ValueError("request arm set is malformed")
    prediction_rows = _jsonl_rows(artifacts["predictions.jsonl"], "predictions")
    if (not isinstance(score.get("arms"), list)
            or any(not isinstance(item, dict) for item in score["arms"])
            or [item.get("arm") for item in score["arms"]] != arms):
        raise ValueError("score output arms differ from request")
    task_ids = _jsonl_ids(artifacts["tasks.jsonl"], "tasks")
    try:
        dispositions = _loads(artifacts["dispositions.json"].decode("utf-8", errors="strict"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("disposition input is malformed JSON") from exc
    if not isinstance(dispositions, dict):
        raise ValueError("disposition input is not a JSON object")
    if set(dispositions) != {"schema", "tasks"} or not isinstance(dispositions.get("tasks"), list):
        raise ValueError("disposition manifest is malformed")
    decisions = {}
    for row in dispositions["tasks"]:
        if (not isinstance(row, dict) or set(row) != {"task_id", "disposition", "evidence_paths"}
                or not isinstance(row.get("task_id"), str) or not row["task_id"]
                or row["task_id"] in decisions
                or row.get("disposition") not in {
                    "include", "exclude_empty_gold", "exclude_scratch_gold", "exclude_unresolvable_gold"
                }
                or not isinstance(row.get("evidence_paths"), list)):
            raise ValueError("disposition task rows are malformed or duplicated")
        decisions[row["task_id"]] = row.get("disposition")
    if set(decisions) != set(task_ids):
        raise ValueError("disposition IDs differ from task rows")
    eligible = sorted(task_id for task_id in task_ids if decisions[task_id] == "include")
    if (score.get("eligible_task_ids") != eligible
            or score.get("eligible_task_count") != len(eligible)
            or not eligible):
        raise ValueError("score eligible task identities/count differ from original inputs")
    expected_prediction_keys = {(task_id, arm) for task_id in eligible for arm in arms}
    prediction_keys = []
    for row in prediction_rows:
        if (set(row) != {"task_id", "arm", "status", "pred_files", "pred_spans", "pack_candidates"}
                or not isinstance(row.get("task_id"), str)
                or not isinstance(row.get("arm"), str)
                or row.get("status") not in {"ok", "error", "no_context_extracted", "checkout_failed"}
                or not isinstance(row.get("pred_files"), list)
                or not isinstance(row.get("pred_spans"), list)
                or not isinstance(row.get("pack_candidates"), list)):
            raise ValueError("original prediction row fields are malformed")
        prediction_keys.append((row["task_id"], row["arm"]))
    if (len(prediction_keys) != len(set(prediction_keys))
            or set(prediction_keys) != expected_prediction_keys):
        raise ValueError("original prediction rows do not cover the declared task-by-arm matrix")
    if score.get("metric_directions") != {name: "higher_better" for name in METRICS}:
        raise ValueError("metric directions differ from the declared higher-better scores")
    if score.get("budget_cost_basis") != "caller_supplied_candidate_cost_fields":
        raise ValueError("score candidate-cost basis differs")
    if score.get("budget_note") != "pack budgets use supplied cost estimates; no tokenizer or cost estimator runs here":
        raise ValueError("score budget note differs")
    disposition_by_id = {row["task_id"]: row["disposition"] for row in dispositions["tasks"]}
    expected_excluded = [task_id for task_id in sorted(task_ids)
                         if disposition_by_id[task_id] != "include"]
    excluded_rows = score.get("excluded")
    if (not isinstance(excluded_rows, list) or any(not isinstance(row, dict) for row in excluded_rows)
            or any(set(row) != {"task_id", "reason", "unsafe_gold_paths"} for row in excluded_rows)
            or [row.get("task_id") for row in excluded_rows] != expected_excluded
            or any(row.get("reason") != disposition_by_id[row["task_id"]]
                   for row in excluded_rows)):
        raise ValueError("excluded rows differ from explicit dispositions")
    for arm_record in score["arms"]:
        if (set(arm_record) != {"arm", "metric_direction", "scopes"}
                or arm_record.get("metric_direction") != "higher_better"
                or not isinstance(arm_record.get("scopes"), list)
                or any(not isinstance(scope, dict) for scope in arm_record["scopes"])
                or any(set(scope) != {"scope", "budget_tokens", "budget_basis", "metrics", "per_task"}
                       for scope in arm_record["scopes"])
                or [(scope.get("scope"), scope.get("budget_tokens")) for scope in arm_record["scopes"]]
                != list(EXPECTED_SCOPES)):
            raise ValueError("arm scopes or metric direction differ")
        for scope in arm_record["scopes"]:
            rows = scope.get("per_task")
            if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
                    or [row.get("task_id") for row in rows] != eligible):
                raise ValueError("per-task score rows differ from the eligible denominator")
            if scope.get("budget_basis") != ("caller_supplied_candidate_costs"
                                              if scope["budget_tokens"] is not None else None):
                raise ValueError("packed budget basis differs")
            summary_metrics = scope.get("metrics")
            if not isinstance(summary_metrics, dict) or set(summary_metrics) != set(METRICS):
                raise ValueError("summary metric membership is incomplete")
            macro_values: dict[str, list[float]] = {metric: [] for metric in METRICS}
            for row in rows:
                if set(row) != {"task_id", "status", "counts", "metrics"}:
                    raise ValueError("per-task score fields differ")
                if row.get("status") not in {"ok", "error", "no_context_extracted", "checkout_failed"}:
                    raise ValueError("per-task row status is invalid")
                derived = _expected_metrics(row.get("counts", {}))
                metric_values = row.get("metrics")
                if not isinstance(metric_values, dict) or set(metric_values) != set(METRICS):
                    raise ValueError("per-task metric membership is incomplete")
                for metric in METRICS:
                    value = metric_values[metric]
                    if (type(value) not in (int, float) or not math.isfinite(value)
                            or value < 0 or value > 1):
                        raise ValueError("per-task metric is outside [0,1]")
                    expected = 0.0 if row["status"] != "ok" else derived[metric]
                    if not math.isclose(float(value), expected, rel_tol=0, abs_tol=1e-12):
                        raise ValueError("per-task metric differs from its original TP/FP/FN")
                    macro_values[metric].append(float(value))
                if row["status"] != "ok" and any(
                        row["counts"][granularity][key] != 0
                        for granularity in ("file", "line") for key in ("tp", "fp")):
                    raise ValueError("failed task contributes predictions to the score counts")
            for metric in METRICS:
                summary = summary_metrics[metric]
                if (not isinstance(summary, dict) or set(summary) != {"value", "direction", "unit"}
                        or summary.get("direction") != "higher_better"
                        or summary.get("unit") != "fraction"):
                    raise ValueError("macro metric metadata is malformed")
                expected = math.fsum(macro_values[metric]) / len(macro_values[metric])
                value = summary.get("value")
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or not math.isclose(value, expected, rel_tol=0, abs_tol=1e-12)):
                    raise ValueError("aggregate metric differs from per-task macro values")
    return score


def read_receipt(path: str | Path) -> tuple[dict, str]:
    receipt_path = _receipt_path(path)
    run_dir = receipt_path.parent
    _check_custody_chain(run_dir)
    info = run_dir.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("run directory must be owned and private (mode 0700)")
    raw = _regular_bytes(receipt_path, limit=8 * 1024 * 1024)
    record = _read_json(raw, "receipt", newline=True)
    if set(record) != RECEIPT_FIELDS or record.get("schema") != SCHEMA:
        raise ValueError("unsupported or incomplete ContextBench score receipt")
    receipt_sha = record.get("receipt_sha256")
    unsigned = dict(record)
    unsigned.pop("receipt_sha256", None)
    if not isinstance(receipt_sha, str) or _sha(_canonical(unsigned)) != receipt_sha:
        raise ValueError("receipt self-hash differs")
    refs = record.get("artifacts")
    if (not isinstance(refs, dict)
            or set(refs) != set(ARTIFACT_LIMITS) - {"execution-request.json", "scored-output.json"}):
        raise ValueError("receipt artifact membership is incomplete")
    copied = {}
    for name, ref in refs.items():
        if not isinstance(ref, dict) or ref.get("name") != name:
            raise ValueError("receipt artifact name differs from its declared slot")
        copied[name] = _artifact(run_dir, ref)
    request_ref = record.get("request")
    if not isinstance(request_ref, dict) or set(request_ref) != ARTIFACT_FIELDS:
        raise ValueError("receipt request artifact reference is malformed")
    if request_ref.get("name") != "execution-request.json":
        raise ValueError("request artifact name is noncanonical")
    request_bytes = _artifact(run_dir, request_ref)
    request = _read_json(request_bytes, "execution request")
    if set(request) != REQUEST_FIELDS or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("execution request schema or fields differ")
    if (request.get("producer_id") != "scripts/harness/contextbench_score_capture.py/v1"
            or request.get("environment") != "not captured"):
        raise ValueError("request producer/environment declaration differs")
    dataset = request.get("dataset")
    if not isinstance(dataset, dict) or set(dataset) != {"label", "artifact"}:
        raise ValueError("request dataset identity is malformed")
    if (not isinstance(dataset.get("label"), str)
            or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", dataset["label"])):
        raise ValueError("request dataset label is missing or malformed")
    capture_id = request.get("capture_id")
    if not isinstance(capture_id, str) or not re.fullmatch(r"[0-9a-f]{32}", capture_id):
        raise ValueError("request capture identifier is malformed")
    try:
        if uuid.UUID(hex=capture_id).version != 4:
            raise ValueError("request capture identifier is not UUIDv4")
    except ValueError as exc:
        raise ValueError("request capture identifier is not UUIDv4") from exc
    if run_dir.name != capture_id:
        raise ValueError("capture directory name differs from the pre-score UUID")
    if request.get("applicability") not in {"synthetic_fixture", "local_precomputed_inputs"}:
        raise ValueError("request applicability must be explicit")
    for field, name in (("task_rows", "tasks.jsonl"), ("predictions", "predictions.jsonl"),
                        ("dispositions", "dispositions.json")):
        if request.get(field) != refs[name]:
            raise ValueError(f"request {field} bytes differ from receipt artifact reference")
    if request.get("dataset", {}).get("artifact") != refs["dataset.bin"]:
        raise ValueError("dataset reference differs from captured dataset bytes")
    if request.get("producer_source") != refs["producer-source.bin"]:
        raise ValueError("request producer identity differs from captured producer bytes")
    app = request.get("application")
    if (not isinstance(app, dict) or set(app) != {"root", "revision", "tracked_clean",
            "scorer_sha256", "packer_sha256", "package_sha256"} or app.get("tracked_clean") is not True
            or not isinstance(app.get("revision"), str) or len(app["revision"]) != 40):
        raise ValueError("application source identity is incomplete")
    trusted = {
        "producer-source.bin": TRUSTED_PRODUCER_SHA256,
        "scorer-source.bin": TRUSTED_SCORER_SHA256,
        "packer-source.bin": TRUSTED_PACKER_SHA256,
        "src-package-source.bin": TRUSTED_PACKAGE_SHA256,
    }
    for name, expected in trusted.items():
        if refs[name]["sha256"] != expected or _sha(copied[name]) != expected:
            raise ValueError(f"{name} differs from the trusted reviewed source identity")
    if app["scorer_sha256"] != refs["scorer-source.bin"]["sha256"]:
        raise ValueError("application scorer identity differs from captured source bytes")
    if app["packer_sha256"] != refs["packer-source.bin"]["sha256"]:
        raise ValueError("application packer identity differs from captured source bytes")
    if app["package_sha256"] != refs["src-package-source.bin"]["sha256"]:
        raise ValueError("application src package identity differs from captured source bytes")
    metric_contract = {
        "schema": SCORE_SCHEMA,
        "average": "macro_per_task",
        "direction": "higher_better",
        "budget_values": [2000, 4000, 8000],
        "integrity_proposition": (
            "The offline ContextBench score artifact is complete and internally consistent "
            "for applicability={applicability}; no discovery quality is asserted."
        ),
    }
    if request.get("metric_contract") != metric_contract:
        raise ValueError("request metric contract differs")
    for field in ("started_utc",):
        value = request.get(field)
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError(f"request {field} is missing")
        try:
            datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise ValueError(f"request {field} is not an ISO timestamp") from exc
    started, ended = record.get("started_utc"), record.get("ended_utc")
    if not isinstance(started, str) or not isinstance(ended, str):
        raise ValueError("receipt timestamps are missing")
    if started != request["started_utc"]:
        raise ValueError("receipt start time differs from original request")
    try:
        start_dt = datetime.fromisoformat(started[:-1] + "+00:00") if started.endswith("Z") else None
        end_dt = datetime.fromisoformat(ended[:-1] + "+00:00") if ended.endswith("Z") else None
    except ValueError as exc:
        raise ValueError("receipt timestamps are malformed") from exc
    if start_dt is None or end_dt is None or end_dt < start_dt:
        raise ValueError("receipt end time is invalid or precedes its request")
    if record.get("status") == "diagnostic":
        if (not isinstance(record.get("diagnostic_code"), str) or not record["diagnostic_code"]
                or record.get("scored_output") is not None
                or record.get("integrity_result") is not None
                or record.get("integrity_proposition") is not None
                or type(record.get("scorer_import_started")) is not bool):
            raise ValueError("diagnostic receipt has inconsistent output or code")
        expected_members = set(refs) | {"execution-request.json", "receipt.json"}
        if {p.name for p in run_dir.iterdir()} != expected_members:
            raise ValueError("diagnostic run directory has unexpected artifacts")
        return record, receipt_sha
    if (record.get("status") != "scored" or record.get("diagnostic_code")
            or record.get("scorer_import_started") is not True):
        raise ValueError("score status, import boundary, and diagnostic fields disagree")
    output_ref = record.get("scored_output")
    if not isinstance(output_ref, dict) or output_ref.get("name") != "scored-output.json":
        raise ValueError("scored output reference is missing or noncanonical")
    output_bytes = _artifact(run_dir, output_ref)
    if {p.name for p in run_dir.iterdir()} != set(refs) | {
            "execution-request.json", "scored-output.json", "receipt.json"}:
        raise ValueError("score run directory has unexpected artifacts")
    _validate_score_output(output_bytes, request, copied)
    score = _read_json(output_bytes, "scored output", newline=True)
    proposition = request["metric_contract"]["integrity_proposition"].format(
        applicability=request["applicability"])
    if (record.get("integrity_result") is not True
            or record.get("integrity_proposition") != proposition):
        raise ValueError("receipt integrity result or proposition differs from its pre-score request")
    return record, receipt_sha


def native_rows(path: str | Path) -> tuple[dict, ...]:
    try:
        record, receipt_sha = read_receipt(path)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ProjectionError("ContextBench score receipt custody refused") from None
    if record["status"] != "scored":
        return ()
    receipt_path = _receipt_path(path)
    run_dir = receipt_path.parent
    score_bytes = _artifact(run_dir, record["scored_output"])
    score = _read_json(score_bytes, "scored output", newline=True)
    request_bytes = _artifact(run_dir, record["request"])
    request = _read_json(request_bytes, "execution request")
    return ({
        "receipt_path": str(receipt_path),
        "receipt_sha256": receipt_sha,
        "capture_id": request["capture_id"],
        "applicability": request["applicability"],
        "dataset_sha256": request["dataset"]["artifact"]["sha256"],
        "source_revision": request["application"]["revision"],
        "scorer_sha256": request["application"]["scorer_sha256"],
        "packer_sha256": request["application"]["packer_sha256"],
        "package_sha256": request["application"]["package_sha256"],
        "score_sha256": record["scored_output"]["sha256"],
        "eligible_task_count": score["eligible_task_count"],
        "excluded_task_count": len(score["excluded"]),
        "score_cell_count": len(score["arms"]) * len(EXPECTED_SCOPES) * len(METRICS),
        "integrity_result": record["integrity_result"],
        "integrity_proposition": record["integrity_proposition"],
    },)


def public_locator(path: str | Path) -> str:
    """Return only the request-bound opaque UUID, never a private filesystem path."""
    try:
        record, _ = read_receipt(path)
        run_dir = _receipt_path(path).parent
        request = _read_json(_artifact(run_dir, record["request"]), "execution request")
        return "contextbench-score:" + request["capture_id"]
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return "contextbench-score:unresolved"


@register("contextbench-discovery-score", source_class="verifier",
          decided_proposition_field="integrity_proposition")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    try:
        rows = native_rows(native["receipt_path"])
        if len(rows) != 1 or rows[0] != dict(native):
            raise ProjectionError("native score row differs from immutable receipt readback")
        capture_id = native["capture_id"]
        return ClaimTuple(
            measurement_id="contextbench-score:" + capture_id,
            metric="contextbench_score_report_integrity",
            value=native["integrity_result"],
            date=read_receipt(native["receipt_path"])[0]["ended_utc"],
            reps=None,
            category="CANDIDATE",
            metric_direction="higher_better",
            protocol_id="",
            claim=native["integrity_proposition"],
            decided_proposition=native["integrity_proposition"],
            source_class="verifier",
            source_kind=ADAPTER_ID,
            binding_kind="identity",
            attestation_locator="contextbench-score:" + capture_id,
            attestation_sha256=native["receipt_sha256"],
            attestation_present=True,
            attestation_verified=True,
            extra={
                "applicability": native["applicability"],
                "dataset_sha256": native["dataset_sha256"],
                "source_revision": native["source_revision"],
                "scorer_sha256": native["scorer_sha256"],
                "packer_sha256": native["packer_sha256"],
                "package_sha256": native["package_sha256"],
                "score_sha256": native["score_sha256"],
                "eligible_task_count": native["eligible_task_count"],
                "excluded_task_count": native["excluded_task_count"],
                "score_cell_count": native["score_cell_count"],
                "receipt_sha256": native["receipt_sha256"],
                "promotion_authority": False,
                "scoring_values_asserted": False,
            },
        )
    except ProjectionError:
        raise
    except (KeyError, TypeError, ValueError, OSError):
        raise ProjectionError("ContextBench score projection refused") from None

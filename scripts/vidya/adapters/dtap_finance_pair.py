"""Strict reader of the producer-written DTAP finance paired native record (VB-DTAP-FINANCE-PAIRED-WRITE).

Native input: ``native-record.json`` with ``schema == "dtap-finance-paired-native/v1"`` written once by the
finance pair capture next to its two arm results. The reader re-opens every file the record names and
refuses on any digest, case, seed, model or delivery-witness disagreement. Grant, cleanup and image
identities are producer declarations; physical authority, scheduler issuer and loaded code stay UNKNOWN.

Projection is ONE tuple: the benign (baseline-arm) legitimate-task-success outcome, exactly the claim the
producer's own projection made. Attack delivery / nondelivery is carried as an informational fact only:
observed delivery alone is not a security finding, so no attack metric is projected. Shared
``claim_tuple.grade()`` decides; no ladder is added and no historical warrant is invented.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

SCHEMA = "dtap-finance-paired-native/v1"
SOURCE_KIND = "dtap-finance-pair"
ADAPTER_ID = "vidya.adapters.dtap_finance_pair/v1"
AUTHORITY = "producer_reported_observation_no_issuer_runtime_or_physical_warrant"
CASE = "finance-indirect-action-reversal-002"
ARMS = ("baseline", "attack")
RECORD_KEYS = {"schema", "completed_at", "case", "scope", "source_manifest_path", "source_manifest_sha256",
               "case_source_sha256", "injection_payload", "attack_delivery", "cleanup", "arms", "files"}
FILE_KEYS = {"result_path", "result_sha256", "setup_path", "setup_sha256", "exposure_path", "exposure_sha256"}


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON field")
        out[key] = value
    return out


def _read(path: Path, limit: int = 64 * 1024 * 1024) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("native artifact is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        if len(raw) > limit or (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("native artifact changed during read")
        return raw
    finally:
        os.close(fd)


def _json(raw: bytes) -> Any:
    return json.loads(raw, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _open(path: Path) -> dict[str, Any]:
    raw = _read(path)
    record = _json(raw)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA or set(record) != RECORD_KEYS:
        raise ValueError("not a finance paired native record")
    if record["case"] != CASE or not isinstance(record["completed_at"], str):
        raise ValueError("case or completion time invalid")
    if _sha(_read(Path(record["source_manifest_path"]))) != record["source_manifest_sha256"]:
        raise ValueError("source manifest digest mismatch")
    arms, files = record["arms"], record["files"]
    if set(arms) != set(ARMS) or set(files) != set(ARMS):
        raise ValueError("arm set invalid")
    seeds, models = set(), set()
    for arm in ARMS:
        row, ident = arms[arm], files[arm]
        if set(ident) != FILE_KEYS or row.get("arm") != arm or row.get("case") != CASE:
            raise ValueError("arm identity invalid")
        for kind in ("result", "setup", "exposure"):
            if _sha(_read(Path(ident[kind + "_path"]))) != ident[kind + "_sha256"]:
                raise ValueError(f"{arm} {kind} digest mismatch")
        result = _json(_read(Path(ident["result_path"])))
        if result.get("native_judge") != row.get("native_judge") or result.get("events") != row.get("events"):
            raise ValueError(f"{arm} native record disagrees with its result file")
        runtime = row["runtime"]
        if runtime["source_manifest_sha256"] != record["source_manifest_sha256"]:
            raise ValueError(f"{arm} runtime source manifest disagrees")
        seeds.add(row["seed"])
        models.add(runtime["model_sha256"])
        judge = row["native_judge"]
        if not isinstance(judge, dict) or "task_success" not in judge or "error" not in judge:
            raise ValueError(f"{arm} native judgment missing")
    if len(seeds) != 1 or len(models) != 1:
        raise ValueError("arms differ in seed or model")
    delivery = record["attack_delivery"]
    if delivery not in ("delivered", "nondelivered") or arms["attack"]["attack_delivery"] != delivery:
        raise ValueError("attack delivery claim inconsistent")
    witnessed = any(e.get("tool") == "trade_stock" and e.get("attack_delivered") is True
                    and record["injection_payload"] in str(e.get("result", ""))
                    for e in arms["attack"]["events"])
    if witnessed != (delivery == "delivered"):
        raise ValueError("native delivery witness mismatch")
    return {"record_path": str(path), "record_sha256": _sha(raw), "record": record}


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    try:
        return (_open(Path(path).absolute()),)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ProjectionError("finance pair custody refused: " + type(exc).__name__ + ": " + str(exc)[:80]) from exc


@register(SOURCE_KIND)
def project(native: dict[str, Any]) -> ClaimTuple:
    reopened = native_rows(native["record_path"])
    if reopened[0] != native:
        raise ProjectionError("finance pair changed since original reader pass")
    record = native["record"]
    base = record["arms"]["baseline"]
    judge = base["native_judge"]
    if judge.get("error") is not None or not isinstance(judge.get("task_success"), bool):
        raise ProjectionError("baseline judgment errored or not boolean; nothing to project")
    runtime = base["runtime"]
    return ClaimTuple(
        measurement_id="dtap-finance-pair:" + native["record_sha256"][:20], metric="legitimate_task_success",
        value=int(judge["task_success"]), unit="boolean", date=record["completed_at"], category="BASELINE",
        metric_direction="higher_better", protocol_id="", reps=1, reps_basis="scored",
        claim="Legitimate task success in one benign finance diagnostic (single case, single seed)",
        attestation_locator="dtap-finance-pair:" + native["record_path"],
        attestation_sha256=native["record_sha256"], source_kind=SOURCE_KIND,
        extra={"case": record["case"], "seed": base["seed"], "attack_delivery": record["attack_delivery"],
               "scope": "single benign diagnostic; no security or efficacy inference; attack-arm outcome not projected",
               "producer_declared_model_sha256": runtime["model_sha256"],
               "producer_declared_grant": runtime["grant"], "upstream_commit": runtime["upstream_commit"],
               "source_manifest_sha256": record["source_manifest_sha256"],
               "scheduler_issuer": "UNKNOWN", "loaded_code": "UNKNOWN", "physical_authority": "UNKNOWN"},
    )

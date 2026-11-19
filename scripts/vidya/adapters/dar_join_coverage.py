"""VB-DAR-JOIN-COVERAGE-WIRE: DAR task-ID join coverage audit receipts (awaiting first real run).

Producer: ``scripts/analysis/dar_join_coverage.py --receipt-out R --scorer-config C``. At write time it
captures, aggregates and digests only (no paths, task IDs, prompt text, exception details): input
snapshot digests, baseline-roles digest and count, the scorer-configuration digest, the producer
source sha256 and git revision, the E18 cutoff constant, execution status and the aggregate counts,
self-hashed as ``receipt_sha256``.

This adapter only PROJECTS. The strict reader re-derives the receipt self-hash and the count
invariants, and refuses anything else. Two coverage RATES over the audited progress task IDs are
projected as OBSERVATIONS (empty ``protocol_id``; the shared ladder grades them):

* ``dar_join.feature_reward_coverage``: joined unique feature+reward rows / progress task IDs;
* ``dar_join.duration_input_coverage``: joined rows with a duration baseline / progress task IDs.

No E18 reward warrant, episodic-memory join, model-performance or training-eligibility claim: the
audit "verifies coverage of inputs, not the provenance of stored rewards". Historical stdout-only
audits carry no receipt and project nothing.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.dar_join_coverage/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "dar-join-coverage"
RECEIPT_SCHEMA = "epyc.dar_join_coverage.receipt.v1"
RESULT_SCHEMA = "dar-join-audit.v1"
METRICS = {
    "dar_join.feature_reward_coverage": ("joined_unique_feature_reward", "joined unique feature+reward task IDs"),
    "dar_join.duration_input_coverage": ("joined_duration_inputs_available", "joined task IDs with a duration baseline"),
}
_HEX = re.compile(r"^[0-9a-f]{64}$")
_REV = re.compile(r"^[0-9a-f]{40}$")


def _digest(body: Mapping[str, Any]) -> str:
    canonical = json.dumps({k: v for k, v in body.items() if k != "receipt_sha256"}, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _problems(r: Any) -> list[str]:
    if not isinstance(r, dict) or r.get("schema") != RECEIPT_SCHEMA:
        return [f"not a {RECEIPT_SCHEMA} receipt"]
    p: list[str] = []
    if r.get("status") != "completed":
        p.append("execution status is not completed")
    prod, inp, res = r.get("producer"), r.get("inputs"), r.get("result")
    if not isinstance(prod, dict) or not _HEX.match(str(prod.get("sha256", ""))) \
            or not _REV.match(str(prod.get("git_revision") or "")):
        p.append("producer source sha256 and 40-hex git revision are required")
    if not isinstance(inp, dict):
        return p + ["inputs missing"]
    for k in ("progress", "rewards"):
        v = inp.get(k)
        if not isinstance(v, list) or not v or not all(_HEX.match(str(x)) for x in v):
            p.append(f"inputs.{k} must be a non-empty list of 64-hex snapshot digests")
    br = inp.get("baseline_roles")
    if not isinstance(br, dict) or not _HEX.match(str(br.get("sha256", ""))) \
            or not isinstance(br.get("n_roles"), int) or br["n_roles"] < 0:
        p.append("inputs.baseline_roles needs sha256 and n_roles")
    if not _HEX.match(str(inp.get("scorer_config_sha256", ""))):
        p.append("inputs.scorer_config_sha256 must be a 64-hex digest")
    try:
        if datetime.fromisoformat(str(r.get("recorded_at_utc"))).utcoffset() is None:
            p.append("recorded_at_utc must carry a UTC offset")
    except ValueError:
        p.append("recorded_at_utc is not a timestamp")
    if not isinstance(res, dict) or res.get("schema") != RESULT_SCHEMA or not isinstance(res.get("counts"), dict):
        return p + ["result is not a dar-join-audit.v1 aggregate"]
    c = res["counts"]
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in c.values()):
        p.append("counts must be non-negative integers")
    elif not (c.get("joined_duration_inputs_available", 0) <= c.get("joined_unique_feature_reward", 0)
              <= c.get("progress_task_ids", 0)):
        p.append("count invariant violated (duration inputs <= joined <= progress task IDs)")
    elif c.get("progress_task_ids", 0) == 0:
        p.append("no progress task IDs audited: a coverage rate over nothing is not a measurement")
    if not p and r.get("receipt_sha256") != _digest(r):
        p.append("receipt_sha256 does not bind the receipt content")
    return p


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    """One receipt file -> one native per projected metric. A foreign document is refused by name."""
    f = Path(path)
    if not f.is_file():
        return ()
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"DAR receipt unreadable: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != RECEIPT_SCHEMA:
        raise ProjectionError(f"not a {RECEIPT_SCHEMA} receipt (stdout-only audits carry no receipt)")
    sha = _file_sha(f)
    return tuple({"receipt": doc, "path": str(f), "file_sha256": sha, "metric": m} for m in METRICS)


@register("dar_join_coverage")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    if not isinstance(native, Mapping) or not isinstance(native.get("receipt"), Mapping):
        raise ProjectionError("DAR native must retain the producer receipt")
    metric = native.get("metric")
    if metric not in METRICS:
        raise ProjectionError(f"unknown DAR metric {metric!r}")
    r = dict(native["receipt"])
    problems = _problems(r)
    if problems:
        raise ProjectionError("DAR receipt refused: " + "; ".join(problems))
    path = Path(native["path"])
    if not path.is_file() or _file_sha(path) != native["file_sha256"]:
        raise ProjectionError("DAR receipt no longer carries the hashed bytes")
    key, what = METRICS[metric]
    c = r["result"]["counts"]
    n = c["progress_task_ids"]
    ident = hashlib.sha256(f"{r['receipt_sha256']}|{metric}".encode()).hexdigest()[:24]
    return ClaimTuple(
        measurement_id=f"darjoin_{ident}", metric=metric, value=c.get(key, 0) / n, unit="fraction of progress task IDs",
        metric_direction="higher_better", category="BASELINE", date=r["recorded_at_utc"], protocol_id="",
        claim=(f"{c.get(key, 0)}/{n} progress task IDs are {what} (input-coverage audit only; no E18 reward "
               "warrant, episodic-memory join, model performance or training eligibility)"),
        reps=n, reps_basis="scored: progress task IDs audited", attestation_path=str(path),
        attestation_sha256=native["file_sha256"], attestation_present=True, attestation_verified=True,
        attestation_locator=f"dar-join-coverage:{path.name}#{metric}", source_kind=SOURCE_KIND,
        extra={"schema": RECEIPT_SCHEMA, "receipt_sha256": r["receipt_sha256"], "producer": r["producer"],
               "inputs": r["inputs"], "e18_cutoff_utc": r.get("e18_cutoff_utc"), "counts": c,
               "status": r["status"]})


__all__ = ["ADAPTER_ID", "AUTHORITY", "METRICS", "native_rows", "project"]

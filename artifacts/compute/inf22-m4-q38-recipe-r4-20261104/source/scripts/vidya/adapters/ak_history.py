"""VB-AK-HISTORY: AK-HR-3 prospective history fields as a measurement source (write side + strict read).

AK-HR-1 (census) and AK-HR-2 (diversity diagnostic) read closed stores with no producer hook; they
stay RETROSPECTIVE and emit zero tuples (the VB-TD-21-CENSUS stance). This module is only for the
fields AK-HR-3 adds on rows produced inside ``loop.iterate`` (research ``loop/history_fields.py``,
``fef9b11ae``): ``trial_id`` (the attempt-to-call join key), ``failure_class``, ``stage_seconds``
(planner / critic / author / gate / measure; build and correctness nested inside gate, null when absent), ``trial_tokens``,
``trial_ordinal`` and ``cumulative_tokens`` (monotone per store + epoch), ``mechanism_family_bucket``
and ``knob_descriptor``. Nullable fields stay null and are never filled.

One self-hashed row per trial. The row attests a per-trial RECEIPT file (the canonical bytes of the
authored fields) written beside the sidecar, re-hashed on read. The projected metric is the sum of
the outer stage seconds that were recorded (``ak_trial_stage_seconds_total``, lower is better), refused
when no stage was timed. No backfill from ``experiments.db`` rows: a store without this sidecar emits
zero tuples. ``claim_tuple.grade()`` decides; no ladder.

The producer-side call (``write_belief_measurements`` from the research loop's archive boundary)
is NOT wired in epyc-inference-research by this change; that repo is owned by the INF-73 loop
owner. This carrier is the contract that call must satisfy.
"""

from __future__ import annotations

import hashlib
import fcntl
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.ak_history_capture.v1"
SIDECAR_NAME = "ak_history.beliefs.jsonl"
RECEIPT_DIR = "ak_history_receipts"
METRIC = "ak_trial_stage_seconds_total"
UNIT = "seconds"
ADAPTER_ID = "vidya.adapters.ak_history/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ak-history-measurement"
OUTER_STAGES = ("planner", "critic", "author", "gate", "measure")
STAGES = ("planner", "critic", "author", "gate", "build", "correctness", "measure")
FIELDS = ("trial_id", "trial_ordinal", "cumulative_tokens", "trial_tokens", "failure_class",
          "stage_seconds", "mechanism_family_bucket", "knob_descriptor")


def _receipt_leaf(trial_id: Any) -> str:
    """Restrict new receipt names; legacy rows are validated on read unchanged."""
    if not isinstance(trial_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", trial_id) is None:
        raise CaptureError("trial_id is not a safe receipt filename stem")
    return trial_id + ".json"


def _write_receipts_no_replace(root: Path, receipts: Sequence[tuple[Path, bytes]]) -> None:
    """Preflight all targets, then create missing receipts without following links."""
    directory = root / RECEIPT_DIR
    if directory.is_symlink():
        raise CaptureError("AK history receipt directory is a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    try:
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise CaptureError("AK history receipt directory is not an owned directory") from exc
    try:
        missing: list[tuple[str, bytes]] = []
        for receipt, body in receipts:
            leaf = _receipt_leaf(receipt.stem)
            try:
                fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
            except FileNotFoundError:
                missing.append((leaf, body))
                continue
            except OSError as exc:
                raise CaptureError("AK history receipt is a symlink or unreadable") from exc
            with os.fdopen(fd, "rb") as handle:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode) or handle.read() != body:
                    raise CaptureError("AK history receipt exists with conflicting bytes")
        for leaf, body in missing:
            try:
                fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=dir_fd)
            except OSError as exc:
                raise CaptureError("AK history receipt create refused; target changed") from exc
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _existing_receipt_is_regular(row: Mapping[str, Any]) -> bool:
    path = Path(row["results_path"])
    return not path.is_symlink() and not path.parent.is_symlink() and path.is_file()


def _field_problems(f: Any) -> list[str]:
    if not isinstance(f, dict):
        return ["extra.fields must be an object"]
    p = []
    if sorted(f) != sorted(FIELDS):
        p.append(f"extra.fields must carry exactly {list(FIELDS)} (null where not recorded)")
        return p
    if not ns.text(f["trial_id"]):
        p.append("fields.trial_id must be a non-empty string")
    for k in ("trial_ordinal", "cumulative_tokens", "trial_tokens"):
        if f[k] is not None and not ns.nonneg_int(f[k]):
            p.append(f"fields.{k} must be a non-negative integer or null")
    if f["trial_ordinal"] is None:
        p.append("fields.trial_ordinal is required; cumulative_tokens may be unknown")
    for k in ("failure_class", "mechanism_family_bucket"):
        if f[k] is not None and not ns.text(f[k]):
            p.append(f"fields.{k} must be a non-empty string or null")
    if f["knob_descriptor"] is not None and not isinstance(f["knob_descriptor"], dict):
        p.append("fields.knob_descriptor must be an object or null")
    ss = f["stage_seconds"]
    if not isinstance(ss, dict) or sorted(ss) not in (sorted(OUTER_STAGES), sorted(STAGES)):
        p.append(f"fields.stage_seconds must have the legacy or current stages {list(STAGES)}")
    else:
        for k, v in ss.items():
            if v is not None and (not ns.finite(v) or v < 0):
                p.append(f"fields.stage_seconds.{k} must be a non-negative number or null")
        if not any(ss[k] is not None for k in OUTER_STAGES):
            p.append("fields.stage_seconds has no timed stage; nothing to project")
        if (ss.get("build") is not None or ss.get("correctness") is not None) and ss["gate"] is None:
            p.append("fields.stage_seconds build/correctness require a timed gate")
    return p


def _total(fields: Mapping[str, Any]) -> float:
    # build and correctness are components of gate, not additional wall time.
    stages = fields["stage_seconds"]
    return float(sum(stages[k] for k in OUTER_STAGES if stages[k] is not None))


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("metric") != METRIC:
        p.append(f"metric must be {METRIC!r}")
    if row.get("category") != "CANDIDATE":
        p.append("category must be CANDIDATE")
    if row.get("metric_direction") != "lower_better":
        p.append("metric_direction must be lower_better")
    for k in ("campaign_id", "store_id", "epoch"):
        if not ns.text(e.get(k)):
            p.append(f"extra.{k} must be a non-empty string")
    fp = _field_problems(e.get("fields"))
    p += fp
    if not fp:
        if abs(row["value"] - _total(e["fields"])) > 1e-9:
            p.append("value must equal the sum of the recorded stage seconds")
        if row.get("reps") != 1 or row.get("reps_basis") != "scored:trial":
            p.append("reps must be 1 with reps_basis 'scored:trial'")
        p += ns.check_identity(row, {
            "campaign": e["campaign_id"], "store": e["store_id"], "epoch": e["epoch"],
            "trial": e["fields"]["trial_id"], "results": row["results_sha256"]}, "akhist")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, campaign_id: str, store_id: str, epoch: str, producer: str,
    trials: Sequence[Mapping[str, Any]], emitted_at: str | None = None,
    _existing_rows: Sequence[dict[str, Any]] = (),
) -> Path:
    """Emit ``ak_history.beliefs.jsonl`` plus one receipt file per trial.

    ``trials`` carry exactly :data:`FIELDS` as the loop wrote them (null where not recorded).
    Raises :class:`CaptureError`; nothing is written on any invalid trial.
    """
    root = Path(out_dir)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not trials:
        raise CaptureError("at least one trial is required")
    rows, receipts = [], []
    for t in trials:
        fields = {k: t.get(k) for k in FIELDS}
        if set(t) - set(FIELDS):
            raise CaptureError(f"unknown trial fields {sorted(set(t) - set(FIELDS))}: refusing to "
                               "widen the closed carrier")
        bad = _field_problems(fields)
        if bad:
            raise CaptureError("; ".join(bad))
        body = ns.canonical_json(fields).encode("utf-8")
        receipt = root / RECEIPT_DIR / _receipt_leaf(fields["trial_id"])
        digest = hashlib.sha256(body).hexdigest()
        total = _total(fields)
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": campaign_id, "producer": producer,
            "emitted_at": when, "date": when[:10],
            "measurement_id": "akhist_" + ns.content_hash({
                "campaign": campaign_id, "store": store_id, "epoch": epoch,
                "trial": fields["trial_id"], "results": digest})[:24],
            "metric": METRIC, "value": total, "unit": UNIT, "metric_direction": "lower_better",
            "category": "CANDIDATE",
            "claim": f"AK trial {fields['trial_id']} recorded {total:.3f}s of timed stages",
            "protocol_id": "", "reps": 1, "reps_basis": "scored:trial",
            "results_path": str(receipt), "results_sha256": digest,
            "extra": {"campaign_id": campaign_id, "store_id": store_id, "epoch": epoch,
                      "fields": fields},
        }
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
        receipts.append((receipt, body))
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate trial_id in one sidecar")
    for old in _existing_rows:
        if validate_row(old) or not _existing_receipt_is_regular(old) or not ns.results_present(old):
            raise CaptureError("existing AK history row lost custody")
    rows = [*_existing_rows, *rows]
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate AK history measurement in append")
    _write_receipts_no_replace(root, receipts)
    return ns.write_rows_atomic(root / SIDECAR_NAME, rows)


def append_belief_measurement(
    out_dir: str | Path, *, campaign_id: str, store_id: str, epoch: str,
    producer: str, trial: Mapping[str, Any], emitted_at: str | None = None,
) -> Path:
    """Append one committed trial without replacing older receipts or rows."""
    if set(trial) - set(FIELDS):
        raise CaptureError("unknown trial fields: refusing to widen the closed carrier")
    normalized = {key: trial.get(key) for key in FIELDS}
    problems = _field_problems(normalized)
    if problems:
        raise CaptureError("; ".join(problems))
    _receipt_leaf(normalized["trial_id"])
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "ak_history.append.lock"
    sidecar = root / SIDECAR_NAME
    with open(lock_path, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if sidecar.exists():
            old = ns.load_rows(sidecar, validate_row)
            if old is None:
                raise CaptureError("existing AK history sidecar is invalid")
        else:
            old = []
        if any(not _existing_receipt_is_regular(row) for row in old):
            raise CaptureError("existing AK history receipt is a symlink or nonregular file")
        for row in old:
            fields = row["extra"]["fields"]
            if fields["trial_id"] == normalized["trial_id"]:
                if (fields != normalized or row["run_id"] != campaign_id
                        or row["producer"] != producer
                        or row["extra"]["store_id"] != store_id
                        or row["extra"]["epoch"] != epoch
                        or not ns.results_present(row)):
                    raise CaptureError("trial_id already captured with different identity or bytes")
                return sidecar
        result = write_belief_measurements(
            root, campaign_id=campaign_id, store_id=store_id,
            epoch=epoch, producer=producer, trials=[normalized],
            emitted_at=emitted_at, _existing_rows=old,
        )
        with open(result, "rb") as handle:
            os.fsync(handle.fileno())
        captured = native_rows(result)
        if len(captured) != len(old) + 1 or not all(
            row["attestation_present"] for row in captured
        ):
            raise CaptureError("AK history append readback lost a row or receipt")
        dir_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return result


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("AK history native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("AK history row is not a producer-authored capture: "
                              + "; ".join(problems))
    x = row["extra"]
    locator = (f"ak-history:{x['campaign_id']}:{x['store_id']}:{x['epoch']}:"
               f"{x['fields']['trial_id']}:{row['results_path']}")
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""),
                             no_protocol_ids=("observation:none",), legacy_schema_protocol=True)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames

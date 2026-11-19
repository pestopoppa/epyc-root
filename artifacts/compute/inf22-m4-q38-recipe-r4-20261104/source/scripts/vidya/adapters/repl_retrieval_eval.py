"""Read producer-authored UFH-12 retrieval-eval and embedder-speed sidecars.

Tasks VB-UFH12-RETR (REPL-EMB-2.2/2.4) and VB-UFH12-EMBSPEED (REPL-EMB-2.7 speed block). The
producer is the eval harness in ``epyc-orchestrator`` ``scripts/benchmark``; its write side,
``scripts/benchmark/repl_retrieval_capture.py`` (``RetrievalRun`` / ``SpeedRun``), emits
``<run_id>.belief_measurements.jsonl`` (offline recall) and ``<run_id>.speed.belief_measurements.jsonl``
(speed) beside the immutable record each ``finalize()`` writes. This reader loads that capture module
pinned by sha256 and uses ITS ``validate_row`` / ``validate_rows``, so writer and reader share one
definition of a well-formed row.

Two source kinds, one module, ONE ladder: ``repl-retrieval-eval`` (instrument ``offline_recall``)
and ``repl-embedder-speed`` (instrument ``offline_speed``) both register a projection into the
shared ``measurement`` class and are graded by ``claim_tuple.grade()`` alone. The two instruments
never pool: each source accepts only its own, and a sidecar holding anything else -- an online
``spill_pointer_follows`` row, the other offline instrument, a mix -- is refused whole. One malformed
row voids the whole sidecar. ``protocol_id`` is empty (no protocol is codified), so every row is an
observation until the constitution gains one.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.repl_retrieval_eval/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "repl-retrieval-eval"
SPEED_SOURCE_KIND = "repl-embedder-speed"
ORCHESTRATOR_ROOT = Path("/workspace/repos/epyc-orchestrator")
PRODUCER_PATH = ORCHESTRATOR_ROOT / "scripts/benchmark/repl_retrieval_capture.py"
PRODUCER_SHA256 = "be6a0499a1e53307ee6cb6ff1200d6e5d7e29a46e4bfe859c7652c3513dd800e"
DEFAULT_ROOT = Path("/mnt/raid0/llm/epyc-orchestrator/data/repl_retrieval_eval")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _producer() -> ModuleType:
    try:
        metadata = PRODUCER_PATH.lstat()
    except OSError as exc:
        raise ProjectionError(
            f"retrieval-eval capture module unavailable: {exc}"
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ProjectionError(
            "retrieval-eval capture module must be a regular single-link file"
        )
    if _sha256(PRODUCER_PATH) != PRODUCER_SHA256:
        raise ProjectionError(
            "retrieval-eval capture module bytes differ from reviewed sha256"
        )
    name = "_epyc_repl_retrieval_capture"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PRODUCER_PATH)
    if spec is None or spec.loader is None:
        raise ProjectionError("retrieval-eval capture module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(
            f"retrieval-eval capture module cannot be loaded: {exc}"
        ) from exc
    return module


def _check_row(row: Any, producer: ModuleType, source_kind: str) -> None:
    try:
        problems = producer.validate_row(row)
    except Exception as exc:
        raise ProjectionError(f"retrieval-eval row validator failed: {exc}") from exc
    if problems:
        raise ProjectionError("retrieval-eval row refused: " + "; ".join(problems))
    if row["source_kind"] != source_kind:
        raise ProjectionError(
            f"{source_kind} was offered a {row['source_kind']} row "
            f"(instrument {row['instrument']}): the offline instruments never pool"
        )


def _record_path(sidecar: Path, row: dict, producer: ModuleType) -> Path:
    record = sidecar.parent / row["record_file"]
    if producer.sidecar_path(record).name != sidecar.name:
        raise ProjectionError(
            "retrieval-eval sidecar is not the sidecar of its named record"
        )
    return record


def _native(sidecar_path: str | Path, source_kind: str) -> tuple[dict, ...]:
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    producer = _producer()
    try:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"retrieval-eval sidecar unreadable: {exc}") from exc
    if not rows:
        return ()
    for row in rows:
        _check_row(row, producer, source_kind)
    try:
        set_problems = producer.validate_rows(rows)
    except Exception as exc:
        raise ProjectionError(
            f"retrieval-eval sidecar validator failed: {exc}"
        ) from exc
    if set_problems:
        raise ProjectionError(
            "retrieval-eval sidecar refused: " + "; ".join(set_problems)
        )
    _record_path(path, rows[0], producer)
    return tuple({"row": row, "sidecar_path": str(path)} for row in rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Recall, paired-diff and cost rows of one ``offline_recall`` sidecar (all or nothing)."""
    return _native(sidecar_path, SOURCE_KIND)


def speed_native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Speed rows of one ``offline_speed`` sidecar (all or nothing)."""
    return _native(sidecar_path, SPEED_SOURCE_KIND)


def _project(native: Any, source_kind: str) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("retrieval-eval native capture row missing")
    row = native["row"]
    producer = _producer()
    _check_row(row, producer, source_kind)
    sidecar = Path(native.get("sidecar_path") or "")
    record = _record_path(sidecar, row, producer)
    present = record.is_file()
    verified = present and _sha256(record) == row["record_sha256"]
    extra = row["extra"]
    prov = extra["provenance"]
    detail: dict[str, Any] = {
        "schema": row["schema"],
        "producer": row["producer"],
        "emitted_at": row["emitted_at"],
        "row_sha256": row["row_sha256"],
        "sidecar_path": str(sidecar),
        "instrument": row["instrument"],
        "run_id": row["run_id"],
        "kind": row["kind"],
        "arm_id": row["arm_id"],
        "arm": extra["arm"],
        "mode": row["mode"],
        "query_category": row["query_category"],
        "k": row["k"],
        "locator": extra["locator"],
        "config_echo": extra["config_echo"],
        "samples": row["samples"],
        "digests": prov["digests"],
        "host_context": prov["host_context"],
        "provenance_sha256": extra["provenance_sha256"],
        "provenance": prov,
    }
    if row["kind"] == "paired_diff":
        detail["against"] = extra["against"]
    if source_kind == SOURCE_KIND:
        detail["rule"] = prov["rule"]
        detail["rule_amended"] = prov["rule"].get("amendment") is not None
    else:
        detail["noise_floor"] = row["samples"]["noise_floor"]
    return ClaimTuple(
        measurement_id=row["measurement_id"],
        metric=row["metric"],
        value=row["value"],
        date=row["date"],
        category=row["category"],
        claim=row["claim"],
        metric_direction=row["metric_direction"],
        protocol_id=row["protocol_id"],
        reps=row["reps"],
        reps_basis=row["reps_basis"],
        unit=row["unit"],
        attestation_path=str(record),
        attestation_sha256=row["record_sha256"],
        attestation_locator=f"{extra['locator']}|{record}#sha256={row['record_sha256']}",
        attestation_present=present,
        attestation_verified=True if verified else None,
        source_kind=source_kind,
        extra=detail,
    )


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    return _project(native, SOURCE_KIND)


@register(SPEED_SOURCE_KIND)
def project_speed(native: Any) -> ClaimTuple:
    return _project(native, SPEED_SOURCE_KIND)

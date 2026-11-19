"""Read producer-authored CPU speech capture rows (VB-SPEECH-CPU-1 / VB-SPEECH-CPU-1a).

Producer: epyc-inference-research `artifacts/speech_cpu_realtime_20260924/speech_cpu_capture.py`
(schema `epyc.vidya.speech_cpu_capture.v1`), written by `speech_cpu_bench.py` and
`live_llm_contention_capture.py` when SPEECH_CPU_CAPTURE_DIR is set. The 2026-09-24 rows in that
artifact's `raw/` carry no schema, row hash or binary digest: they yield ZERO tuples and are never
backfilled — a field invented on read would claim a warrant the run never captured.

The adapter projects; the shared measurement ladder (`claim_tuple.grade()`) alone grades. Every
row is re-validated with the producer's own `validate_row()`, loaded by pinned sha256.

Three cautions from the source row, carried on every tuple (`extra.cautions`) and enforced by
the producer's validator as required fields:
  1. the core layout is part of the measurand (whisper collapses on some layouts at the same
     thread count) — the exact core list and thread count are in the applicability scope;
  2. the TTS thread count exists only via the `get_nprocs` preload shim — TTS rows carry
     `shim_nprocs`;
  3. co-tenant state decides the result — at least one co-tenant sample inside the row's window
     and an explicit `generating` verdict with its basis.

A capped, timed-out or guard-aborted request is never projected as a measurement (its value is
null by contract). It is not dropped either: `native_rows()` counts it, and every projected tuple
of the run carries `n_censored_in_run`, so the censoring stays visible in the denominator.
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
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.speech_cpu_measurement/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "speech-cpu-measurement"
RESEARCH_ROOT = Path("/workspace/repos/epyc-inference-research")
PRODUCER_PATH = RESEARCH_ROOT / "artifacts/speech_cpu_realtime_20260924/speech_cpu_capture.py"
PRODUCER_SHA256 = "1f63ee2ef9b6ec6958d27565987f0f8f5b61e03876c3eac786904ed371010fca"
CAUTIONS = (
    "core layout is part of the measurand (whisper collapses on some layouts at equal thread count)",
    "TTS thread count exists only via the get_nprocs preload shim (shim_nprocs)",
    "co-tenant state (frontdoor generating, its -t/cores) decides the result; sampled during the row",
)


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
        raise ProjectionError(f"speech CPU capture producer unavailable: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise ProjectionError("speech CPU capture producer must be a regular file")
    if _sha256(PRODUCER_PATH) != PRODUCER_SHA256:
        raise ProjectionError("speech CPU capture producer bytes differ from reviewed sha256")
    name = "_epyc_speech_cpu_capture_producer"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PRODUCER_PATH)
    if spec is None or spec.loader is None:
        raise ProjectionError("speech CPU capture producer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(f"speech CPU capture producer cannot be loaded: {exc}") from exc
    return module


def _check_row(row: Any, producer: ModuleType) -> None:
    try:
        problems = producer.validate_row(row)
    except Exception as exc:
        raise ProjectionError(f"speech CPU row validator failed: {exc}") from exc
    if problems:
        raise ProjectionError("speech CPU row refused: " + "; ".join(problems))


def native_rows(capture_path: str | Path) -> tuple[dict, ...]:
    """Every completed row of one capture file; censored rows are counted, never projected.

    One invalid row refuses the whole file (a partially valid file is not a run we can attest).
    Legacy rows (no capture schema) refuse it too: the retrospective raw/ is never read as a run.
    """
    path = Path(capture_path)
    if not path.is_file():
        return ()
    producer = _producer()
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"speech CPU capture unreadable: {exc}") from exc
    seen: set[str] = set()
    for row in rows:
        _check_row(row, producer)
        if row["measurement_id"] in seen:
            raise ProjectionError("speech CPU capture duplicates a measurement")
        seen.add(row["measurement_id"])
    file_sha = _sha256(path)
    censored: dict[str, int] = {}
    for row in rows:
        if not row["request"]["completed"]:
            censored[row["run_id"]] = censored.get(row["run_id"], 0) + 1
    return tuple({"row": row, "capture_path": str(path), "capture_sha256": file_sha,
                  "n_censored_in_run": censored.get(row["run_id"], 0)}
                 for row in rows if row["request"]["completed"])


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("speech CPU native capture row missing")
    row = native["row"]
    _check_row(row, _producer())
    if not row["request"]["completed"] or row["value"] is None:
        raise ProjectionError("a capped, timed-out or guard-aborted request is not a measurement")
    path = Path(native.get("capture_path", ""))
    present = path.is_file()
    recorded = native.get("capture_sha256", "")
    verified = present and bool(recorded) and _sha256(path) == recorded
    placement, cot = row["placement"], row["cotenant"]
    # Layout and co-tenant state are part of the measurand (cautions 1-3), so they are the fixed
    # knob set of the scope, never prose.
    scope = {"run_id": row["run_id"], "backend": "cpu", "device": "cpu", "surface": row["harness"],
             "kernel": {k: v["sha256"] for k, v in row["binaries"].items()},
             "knobs": {k: v for k, v in (
                 ("cores", placement["cores"]), ("threads", placement["threads"]),
                 ("shim_nprocs", placement.get("shim_nprocs")), ("mode", placement.get("mode")),
                 ("cotenant_generating", bool(cot["generating"])))
                 if v is not None and v != ""}}  # an absent knob is omitted, never invented
    claim = (f"{row['metric']} {row['value']} {row['unit']} ({row['metric_direction']}) on "
             f"{placement['threads']} threads, cores {placement['cores']}"
             + (f", SHIM_NPROCS={placement['shim_nprocs']}" if placement.get("shim_nprocs") else "")
             + f", co-tenant generating={cot['generating']} [{row['harness']}, n=1, {row['date']}, "
               f"observation: no ratified protocol route]")
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=claim,
        metric_direction=row["metric_direction"], protocol_id=row["protocol_id"],
        reps=row["reps"], reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_path=str(path) if present else "",
        attestation_sha256=recorded if verified else "",
        attestation_locator=f"{row['run_id']}:{row['row_index']}:{row['metric']}|{path}",
        attestation_present=present, attestation_verified=True if verified else None,
        source_kind=SOURCE_KIND, applicability=scope,
        extra={"schema": row["schema"], "row_sha256": row["row_sha256"],
               "cautions": list(CAUTIONS), "request": row["request"],
               "generating_basis": cot.get("generating_basis", {}),
               "n_censored_in_run": native.get("n_censored_in_run", 0),
               "adapter": ADAPTER_ID},
    )

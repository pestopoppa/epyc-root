"""VB-AK-SEAT read side: project AutoKernel actor-seat records into measurement ClaimTuples.

Strict by construction. The admissible inputs are the two producer-authored records defined in
``autokernel_actor_seat_capture.py``:

* ``actor-calls.jsonl`` lines of schema ``epyc.autokernel.actor_call.v1`` -> one tuple per call
  (``actor_call_wall_s``);
* ``result-<arm>.json`` documents of schema ``epyc.autokernel.seat_ab_arm.v1`` -> five tuples per
  arm (wall, steps, tool calls, decoded tokens, compactions; totals over root + scouts).

The adapter PROJECTS, and ``claim_tuple.grade()`` decides. It registers no ladder: this is the
``measurement`` class, whose one ladder lives in ``claim_tuple.py`` (spec §4.7).

Doctrine (§4.7: "absence is recorded, never filled"):

* **Pre-hook emits zero rows.** A call-log line or result file without the v1 schema (every
  record on disk when the hook was filed, e.g. the stopped 2026-09-24 bounded-v1 arm) is skipped.
  The reader never rebuilds a tuple from ``ts/backend/wall_s/prompt_chars`` or from a driver
  result, because a tuple invented on read claims warrant the run never captured.
* **A record claiming v1 that fails validation is REFUSED** (``ProjectionError`` naming the
  line), and the whole unit with it: a call log whose v1 lines do not re-derive is corruption.
* **Censored sessions emit zero rows** (timeout / signal death): their wall is a lower bound.
* **Every tuple is an OBSERVATION** while ``protocol_id`` is empty, which it is: no actor-seat
  protocol is codified. n = 1 per call and per arm; the producer's ``scope`` text rides in every
  arm claim, verbatim, so a comparison between arms can never read as a seat effect.

Attestation. A call tuple attests its own log line: the line bytes are sha256-ed at read time and
the locator is ``<log>#L<n>``. An arm tuple attests the ROOT session's ``opencode export`` file,
re-hashed on every read; a moved or mutated export grades DOWN through the shared ladder, it is
not skipped. The result file's own digest (computed here) rides in ``extra``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.autokernel_actor_seat_capture import (  # noqa: E402
    ARM_METRICS,
    ARM_SCHEMA,
    CALL_LOG_NAME,
    CALL_METRICS,
    CALL_SCHEMA,
    METRIC_CALL_WALL,
    arm_values,
    censored,
    measurement_identity,
    seat_digest,
    validate_arm_record,
    validate_call_record,
)

ADAPTER_ID = "vidya.adapters.autokernel_actor_seat/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-actor-seat"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _call_natives(path: Path) -> tuple[dict, ...]:
    try:
        lines = path.read_bytes().splitlines()
    except OSError:
        return ()
    natives: list[dict] = []
    seen: set[str] = set()
    for number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"{path}#L{number}: not JSON ({exc})") from exc
        if not isinstance(record, dict) or record.get("schema") != CALL_SCHEMA:
            continue  # pre-hook (or foreign) line: absence is recorded, never filled
        problems = validate_call_record(record)
        if problems:
            raise ProjectionError(f"{path}#L{number}: actor call record does not re-derive: "
                                  + "; ".join(problems))
        if record["call_id"] in seen:
            raise ProjectionError(f"{path}#L{number}: duplicate call_id {record['call_id']!r}")
        seen.add(record["call_id"])
        if censored(record):
            continue
        for metric in CALL_METRICS:
            natives.append({"kind": "call", "metric": metric, "record": record,
                            "path": str(path), "line": number,
                            "line_sha256": hashlib.sha256(raw.strip()).hexdigest()})
    return tuple(natives)


def _arm_natives(path: Path) -> tuple[dict, ...]:
    try:
        raw = path.read_bytes()
        record = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(record, dict) or record.get("schema") != ARM_SCHEMA:
        return ()  # pre-hook driver result: zero rows, never retrofitted
    problems = validate_arm_record(record)
    if problems:
        raise ProjectionError(f"{path}: seat A/B arm record does not re-derive: "
                              + "; ".join(problems))
    if censored(record):
        return ()
    file_sha = hashlib.sha256(raw).hexdigest()
    return tuple({"kind": "arm", "metric": metric, "record": record, "path": str(path),
                  "file_sha256": file_sha} for metric in ARM_METRICS)


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Admissible (record, metric) natives from a call log or an arm result file.

    Pre-hook, censored, absent or foreign input gives zero rows; a v1 record that fails
    validation raises ``ProjectionError``.
    """
    p = Path(path)
    if not p.is_file():
        return ()
    if p.suffix == ".jsonl":
        return _call_natives(p)
    if p.suffix == ".json":
        return _arm_natives(p)
    return ()


def _resolve(ref_path: str, record_path: str) -> Path:
    candidate = Path(ref_path)
    return candidate if candidate.is_absolute() else Path(record_path).parent / candidate


def _export_present(record: dict, record_path: str) -> tuple[bool, dict]:
    root = next(s for s in record["sessions"] if s["root"])
    checks = {}
    for session in record["sessions"]:
        export = _resolve(session["export"]["path"], record_path)
        checks[session["session_id"]] = (export.is_file()
                                         and _sha256_file(export) == session["export"]["sha256"])
    return checks[root["session_id"]], {"root_session": root["session_id"],
                                        "exports_verified": checks}


def _common_extra(record: dict) -> dict:
    seat = record["seat"]
    return {
        "schema": record["schema"],
        "record_sha256": record["record_sha256"],
        "producer": record["producer"],
        "seat": seat,
        "seat_digest": seat_digest(seat),
        "backend": record["backend"],
        "server": record["server"],
        "prompt": record["prompt"],
        "started_at": record["started_at"],
        "finished_at": record["finished_at"],
        "recorded_at": record["recorded_at"],
    }


def _seat_label(record: dict) -> str:
    seat = record["seat"]
    cfg = seat["config"]["sha256"][:12] if seat["config"] else "none"
    b = record["backend"]
    return (f"seat {seat['arm']} (cfg {cfg}), {b['kind']}:{b['model']}@{b['effort']}, "
            f"prompt {record['prompt']['sha256'][:12]}/{record['prompt']['chars']} chars")


def _project_call(native: dict) -> ClaimTuple:
    record = native["record"]
    metric = native["metric"]
    unit, direction, basis = CALL_METRICS[metric]
    value = record["wall_s"]
    claim = (f"AutoKernel actor {record['role']} call {record['call_id']} "
             f"({_seat_label(record)}, rc {record['returncode']}): {metric} = {value} {unit}; "
             "n=1 call, no repeat, no noise floor -- an observation, not a seat comparison")
    return ClaimTuple(
        measurement_id=measurement_identity(kind="call", record_id=record["call_id"],
                                            metric=metric,
                                            record_sha256=record["record_sha256"]),
        metric=metric, value=value, date=record["started_at"][:10],
        category="BASELINE", claim=claim, metric_direction=direction,
        protocol_id=record["protocol_id"], reps=1, reps_basis=basis, unit=unit,
        attestation_sha256=native["line_sha256"],
        attestation_locator=f"ak-actor-call:{native['path']}#L{native['line']}",
        attestation_present=True,
        # SC69: the line bytes were re-read and hashed at this boundary.
        attestation_verified=True,
        source_kind=SOURCE_KIND,
        extra={**_common_extra(record), "kind": "call", "call_id": record["call_id"],
               "role": record["role"], "run_id": record["run_id"],
               "workspace": record["workspace"], "returncode": record["returncode"],
               "reply": record["reply"],
               "category_source": "adapter default: a single call is not an A/B arm"},
    )


def _project_arm(native: dict) -> ClaimTuple:
    record = native["record"]
    metric = native["metric"]
    unit, direction, basis = ARM_METRICS[metric]
    value = arm_values(record)[metric]
    present, exports = _export_present(record, native["path"])
    root = next(s for s in record["sessions"] if s["root"])
    claim = (f"AutoKernel seat A/B {record['ab_id']} arm {record['arm_id']} "
             f"({record['category']}, {_seat_label(record)}, verdict {record['verdict']}, "
             f"{len(record['sessions'])} session(s)): {metric} = {value} {unit}; "
             f"n=1 arm run, no repeat, no noise floor; scope: {record['scope'].strip()}")
    return ClaimTuple(
        measurement_id=measurement_identity(kind="arm", record_id=record["arm_id"],
                                            metric=metric,
                                            record_sha256=record["record_sha256"]),
        metric=metric, value=value, date=record["started_at"][:10],
        category=record["category"], claim=claim, metric_direction=direction,
        protocol_id=record["protocol_id"], reps=1, reps_basis=basis, unit=unit,
        attestation_sha256=root["export"]["sha256"],
        attestation_locator=(f"ak-seat-arm:{record['ab_id']}:{record['arm_id']}:"
                             f"{_resolve(root['export']['path'], native['path'])}"),
        attestation_present=present,
        # SC69: `present` re-read the root export and recomputed its digest.
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={**_common_extra(record), "kind": "arm", "ab_id": record["ab_id"],
               "arm_id": record["arm_id"], "arm": record["arm"], "role": record["role"],
               "scope": record["scope"], "verdict": record["verdict"],
               "driver": record["driver"], "lane": record["lane"], "call": record["call"],
               "totals": record["totals"], "totals_basis": "root + scouts",
               "sessions": record["sessions"], "result_path": native["path"],
               "result_sha256": native["file_sha256"], **exports},
    )


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Re-validates so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("record"), dict):
        raise ProjectionError("actor-seat native row must retain the producer record")
    record = native["record"]
    if native.get("kind") == "call":
        problems = validate_call_record(record)
        metrics = CALL_METRICS
    elif native.get("kind") == "arm":
        problems = validate_arm_record(record)
        metrics = ARM_METRICS
    else:
        raise ProjectionError("actor-seat native row kind must be 'call' or 'arm'")
    if problems:
        raise ProjectionError("actor-seat record is not a producer-authored capture: "
                              + "; ".join(problems))
    if native.get("metric") not in metrics:
        raise ProjectionError(f"metric must be one of {sorted(metrics)}")
    if censored(record):
        raise ProjectionError("a censored session (timeout / signal) projects no tuple")
    return _project_call(native) if native["kind"] == "call" else _project_arm(native)


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    """Emit frames through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "CALL_LOG_NAME", "METRIC_CALL_WALL", "SOURCE_KIND",
           "frames_for_path", "native_rows", "project"]

"""Compute-calendar granted-job estimate-vs-actual -> measurement ClaimTuples (VB-CAL-OVERRUN-WIRE).

Native record: the grant's ``<id>.ended`` file (``/mnt/raid0/llm/tmp/compute-flags/grants/``). Its
first line is the launcher's historical ``rc=N time=ISO reason=...`` and stays untouched (grant
writers read ``head -1``). The calendar owner's job-end check APPENDS ``key=value`` lines:

    job_id= owner= step= estimated_wall_s= actual_wall_s= [started=ISO] [ratio=] regions= co_residents=
    [np=] [ctx=] [estimator=]

STRICT: ``estimated_wall_s`` must be a positive number, ``actual_wall_s`` (or ``started`` + ``time``)
a non-negative one, a stated ``ratio`` must re-derive from the two walls, and ``actual_wall_s`` must
agree with ``started``..``time`` when both are given. A legacy ``.ended`` (first line only) or one with
no ``estimated_wall_s`` is UNCHECKED: it projects nothing, and no estimate is ever invented. A present
but zero/negative/non-numeric estimate refuses.

The ratio is per (np, context length): ``np`` and ``ctx`` are carried in applicability when the
record has them, never as a global factor. A hard-end rc (124/125/143) censors the actual wall, so the
ratio is a lower bound and the claim says so.

PROJECTION ONLY: metric ``wall_actual_over_estimated`` (ratio, lower better), reps 1, empty
``protocol_id`` (no codified protocol), attestation = the ``.ended`` file with its sha256.
``claim_tuple.grade()`` decides. No ladder here.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.calendar_overrun/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "calendar-overrun"
METRIC = "wall_actual_over_estimated"
MAX_BYTES = 1 << 20
CENSORING_RC = frozenset({124, 125, 143})
_FIRST = re.compile(r"^rc=(-?\d+) time=(\S+) reason=(.*)$")
_KV = re.compile(r"^([a-z_]+)=(.*)$")
_KEYS = frozenset({"job_id", "owner", "step", "estimated_wall_s", "actual_wall_s", "started", "ratio",
                   "regions", "co_residents", "np", "ctx", "estimator"})
_TS = "%Y-%m-%dT%H:%M:%SZ"


def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"calendar-overrun input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"calendar-overrun input exceeds bound: {path}")
    return raw


def _num(value: str, key: str, where: str) -> float:
    try:
        x = float(value)
    except ValueError as exc:
        raise ProjectionError(f"calendar-overrun {where}: {key}={value!r} is not a number") from exc
    if x != x or x in (float("inf"), float("-inf")):
        raise ProjectionError(f"calendar-overrun {where}: {key} is not finite")
    return x


def _ts(value: str, key: str, where: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(value, _TS).replace(tzinfo=datetime.timezone.utc)
    except ValueError as exc:
        raise ProjectionError(f"calendar-overrun {where}: {key}={value!r} is not a UTC timestamp") from exc


def _posint(fields: dict, key: str, where: str) -> int | None:
    if key not in fields:
        return None
    if not re.fullmatch(r"[1-9][0-9]*", fields[key]):
        raise ProjectionError(f"calendar-overrun {where}: {key}={fields[key]!r} is not a positive integer")
    return int(fields[key])


def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path)
    if p.suffix != ".ended":
        return ()
    raw = _read(p)
    lines = raw.decode("utf-8").splitlines()
    where = p.name
    first = _FIRST.match(lines[0]) if lines else None
    if not first:
        raise ProjectionError(f"calendar-overrun {where}: first line is not 'rc= time= reason='")
    rc, ended_at = int(first.group(1)), first.group(2)
    end = _ts(ended_at, "time", where)
    fields: dict[str, str] = {}
    for ln in lines[1:]:
        if not ln.strip():
            continue
        m = _KV.match(ln)
        if not m or m.group(1) not in _KEYS or m.group(1) in fields:
            raise ProjectionError(f"calendar-overrun {where}: unknown, duplicate or malformed line {ln[:60]!r}")
        fields[m.group(1)] = m.group(2).strip()
    if "estimated_wall_s" not in fields:
        return ()                                     # legacy record: no estimate -> UNCHECKED, nothing invented
    est = _num(fields["estimated_wall_s"], "estimated_wall_s", where)
    if est <= 0:
        raise ProjectionError(f"calendar-overrun {where}: estimated_wall_s must be > 0 (got {est})")
    walls = []
    if "actual_wall_s" in fields:
        walls.append(_num(fields["actual_wall_s"], "actual_wall_s", where))
    if "started" in fields:
        walls.append((end - _ts(fields["started"], "started", where)).total_seconds())
        if len(walls) == 2 and abs(walls[0] - walls[1]) > 2.0:
            raise ProjectionError(f"calendar-overrun {where}: actual_wall_s disagrees with started..time")
    if not walls:
        raise ProjectionError(f"calendar-overrun {where}: estimate present but no actual_wall_s or started")
    actual = walls[0]
    if actual < 0:
        raise ProjectionError(f"calendar-overrun {where}: negative actual wall")
    ratio = actual / est
    if "ratio" in fields and abs(_num(fields["ratio"], "ratio", where) - ratio) > 0.005 * max(ratio, 1e-9) + 1e-6:
        raise ProjectionError(f"calendar-overrun {where}: stated ratio does not re-derive from the walls")
    for need in ("job_id", "owner", "step"):
        if not fields.get(need):
            raise ProjectionError(f"calendar-overrun {where}: {need} missing")
    return ({"path": str(p), "sha256": hashlib.sha256(raw).hexdigest(), "rc": rc, "reason": first.group(3),
             "ended_at": ended_at, "estimated_s": est, "actual_s": actual, "ratio": ratio,
             "job_id": fields["job_id"], "owner": fields["owner"], "step": fields["step"],
             "regions": fields.get("regions", ""), "co_residents": fields.get("co_residents", ""),
             "np": _posint(fields, "np", where), "ctx": _posint(fields, "ctx", where),
             "estimator": fields.get("estimator", "")},)


def units(path: Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    return sorted(p for p in path.glob("*.ended") if p.is_file()) if path.is_dir() else []


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "ratio" not in native or "job_id" not in native:
        raise ProjectionError("calendar-overrun native record missing")
    censored = native["rc"] in CENSORING_RC
    r = native["ratio"]
    shape = ", ".join(f"{k}={native[k]}" for k in ("np", "ctx") if native[k])
    claim = (f"Granted job {native['job_id']} (owner {native['owner']}, step {native['step']}"
             + (f"; {shape}" if shape else "") + f") ran {native['actual_s']:.0f} s against an estimated "
             f"{native['estimated_s']:.0f} s: ratio {'>= ' if censored else ''}{r:.3f}, rc={native['rc']}"
             + (" (hard end: the wall is censored, the ratio is a lower bound)" if censored else "")
             + (f"; regions {native['regions']}" if native["regions"] else "")
             + (f"; co-residents {native['co_residents']}" if native["co_residents"] else "")
             + ". Applies to this job's shape only, not a global factor.")
    applicability: dict[str, Any] = {}
    if native["np"]:
        applicability["np"] = native["np"]
    if native["ctx"]:
        applicability["context_tokens"] = native["ctx"]
    if applicability:
        applicability["scope_basis"] = "native"
    observation: dict[str, Any] = {
        "outcome_native": f"rc={native['rc']} actual {native['actual_s']:.0f}s / est {native['estimated_s']:.0f}s"[:120]}
    return ClaimTuple(
        measurement_id=f"calendar-overrun:{native['job_id']}:{native['sha256'][:16]}",
        metric=METRIC, value=round(r, 6), date=native["ended_at"][:10], category="BASELINE", claim=claim,
        metric_direction="lower_better", protocol_id="", reps=1,
        reps_basis="scored: one granted job, one actual wall", unit="ratio",
        attestation_path=native["path"], attestation_sha256=native["sha256"],
        attestation_locator=f"calendar-overrun:{Path(native['path']).name}", attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND, applicability=applicability,
        observation=observation,
        extra={"adapter": ADAPTER_ID, "rc": native["rc"], "reason": native["reason"],
               "estimated_wall_s": native["estimated_s"], "actual_wall_s": native["actual_s"],
               "co_residents": native["co_residents"], "regions": native["regions"], "owner": native["owner"], "step": native["step"],
               "estimator": native["estimator"], "censored": censored})


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "units", "frames_for_path"]

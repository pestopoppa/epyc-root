"""Read the research-owned progression.v1 projection; never infer promotion.

The semantic horizon is observed_through. Re-exporting historical receipts does
not make their observations current. This optional historical card has its own
probe and never changes the loop/operator-gate health verdict.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import stat
import time

from dashboard import panels

SCHEMA = "epyc.autokernel.progression.v1"
PATH = Path(os.environ.get("KERNEL_PROGRESSION_JSON",
                          "/mnt/raid0/llm/autokernel/surface/kernel_progression.json"))
MAX_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 64
STAGES = frozenset({"candidate", "inconclusive", "strict_keep", "rejected", "screened_out"})


def _timestamp(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.timestamp()
    except (ValueError, OverflowError):
        return None


def _validate(body: object) -> dict:
    # A parsed document is returned inside an HTTP envelope. Bound depth well
    # below Python's encoder recursion limit as well as catching parser failure.
    pending = [(body, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise ValueError("progression exceeds nesting bound")
        if isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
    if not isinstance(body, dict) or body.get("schema") != SCHEMA:
        raise ValueError("unknown progression schema")
    if (body.get("authority") != "presentation_projection_only"
            or body.get("promotion_claim") is not False):
        raise ValueError("progression must declare presentation-only authority and promotion_claim=false")
    rows, unexplored = body.get("candidates"), body.get("unexplored")
    if not isinstance(rows, list) or not isinstance(unexplored, list):
        raise ValueError("candidates and unexplored must be lists")
    for row in rows:
        if (not isinstance(row, dict) or row.get("lane") not in {"CPU", "GPU"}
                or not isinstance(row.get("candidate"), str)
                or row.get("stage") not in STAGES
                or row.get("metric_direction") != "higher_better"
                or type(row.get("effect_fraction")) not in {int, float}
                or not math.isfinite(row["effect_fraction"])
                or type(row.get("champion")) is not bool
                or type(row.get("promotable")) is not bool
                or not isinstance(row.get("workload"), str)
                or not isinstance(row.get("evidence"), list)
                or any(not isinstance(item, dict) or not isinstance(item.get("path"), str)
                       for item in row["evidence"])):
            raise ValueError("malformed candidate observation")
    if any(not isinstance(row, dict) or row.get("lane") not in {"CPU", "GPU"}
           for row in unexplored):
        raise ValueError("malformed unexplored hypothesis")
    counts = {
        "candidate": sum(row["stage"] in {"candidate", "inconclusive"} for row in rows),
        "strict_keep": sum(row["stage"] == "strict_keep" for row in rows),
        "champion": sum(row["champion"] for row in rows),
        "promotable": sum(row["promotable"] for row in rows),
    }
    declared = body.get("funnel")
    if (not isinstance(declared, dict) or set(declared) != set(counts)
            or any(type(declared[key]) is not int or declared[key] != value
                   for key, value in counts.items())):
        raise ValueError("funnel does not match its candidate observations")
    return body


def snapshot(*, path: Path | None = None, now: float | None = None) -> tuple[dict, panels.Observation]:
    path = PATH if path is None else path
    now = time.time() if now is None else now
    body = None
    state, error, present = "absent", "not exported", False
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
                raise ValueError("progression is not a bounded nonempty regular file")
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        present = True
        if (len(raw) != before.st_size
                or (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)
                != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)):
            raise ValueError("progression changed while read")
        body = _validate(json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError("non-finite JSON number"))))
        state, error = "observed", None
    except FileNotFoundError:
        pass
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        state, error = "malformed", str(exc)
        # Permission/I/O failure is unobservable, rather than proof of absence.
        present = True
    stamped = _timestamp(body.get("observed_through")) if body else None
    if body is not None and stamped is None:
        state, error = "unknown", "no usable observed_through horizon"
    observation = panels.Observation(
        artifact_present=present, timestamp=stamped, source="observed_through",
        populated=bool(body["candidates"] or body["unexplored"]) if body else None,
        evidence=str(path), detail=error,
        unreported=("progression",) if state in {"unknown", "malformed"} else ())
    envelope = panels.envelope(panels.source("kernel_progression"), observation, now=now)
    if state == "observed":
        state = envelope["staleness_class"]
        if state == panels.CLASS_MISSING:
            state, error = "unknown", envelope["watchdog"]["reason"]
    return {"schema": SCHEMA, "state": state, "available": body is not None,
            "artifact_present": present, "error": error, "data": body,
            "promotion_claim": False, "_freshness": envelope}, observation


def health() -> tuple[int, dict]:
    payload, _ = snapshot()
    state = payload["state"]
    status = (panels.STATUS_OK if state in {"fresh", "aging"} else
              panels.STATUS_ABSENT if state == "absent" else panels.STATUS_DEGRADED)
    return (200 if status == panels.STATUS_OK else 503), {
        "status": status, "panel": "kernel_progression", "state": state,
        "freshness": payload["_freshness"], "error": payload["error"]}

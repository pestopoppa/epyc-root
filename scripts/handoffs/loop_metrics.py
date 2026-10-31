#!/usr/bin/env python3
"""Read-only daily loop report. Unknown coverage is never a measured zero.

First produce a native verdict snapshot with verdict_count.py --json PATH;
pass it with --verdict-snapshot PATH. No conversation or bus message contents
are read. Keeper alerts are point observations, not idle intervals. Filing due
records are deduplicated terminals, not a complete admission-attempt ledger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
from pathlib import Path

FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")


def unknown(reason: str, **observations) -> dict:
    return {"value": None, "status": "unknown", "reason": reason, **observations}


def read_source(path: Path | None) -> tuple[bytes | None, dict]:
    if path is None:
        return None, {"status": "missing", "reason": "no source supplied"}
    try:
        before = path.stat()
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("source is not regular metadata")
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("source exceeds metadata bound")
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("source changed during read")
    except (OSError, ValueError) as exc:
        return None, {"status": "unknown", "reason": type(exc).__name__}
    return raw, {
        "status": "read",
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "mtime_ns": after.st_mtime_ns,
    }


def records(raw: bytes | None) -> tuple[list[dict], int]:
    if raw is None:
        return [], 1
    out, bad = [], 0
    for line in raw.splitlines(keepends=True):
        if not line.strip():
            continue
        try:
            if not line.endswith(b"\n"):
                raise ValueError("partial append")
            record = json.loads(line)
            if not isinstance(record, dict):
                raise TypeError("record must be object")
            out.append(record)
        except (ValueError, TypeError, UnicodeError):
            bad += 1
    return out, bad


def utc_date(value: str) -> str:
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return stamp.astimezone(dt.timezone.utc).date().isoformat()


def decisions(raw: bytes | None, day: str) -> dict:
    try:
        snapshot = json.loads(raw) if raw is not None else None
        row = snapshot["series"][day]
        if any(
            type(row[k]) is not int or row[k] < 0
            for k in ("rows", "handoff_ticks", "progress_lines")
        ):
            raise ValueError("invalid native counts")
        return {
            "value": row["rows"],
            "status": "observed",
            "unit": "distinct inference row-days",
            "basis": "unchanged verdict_count.py native series.rows",
            "handoff_ticks": row["handoff_ticks"],
            "progress_lines": row["progress_lines"],
            "caveat": "producer counts dated verdict records; not native scientific grades",
        }
    except (ValueError, TypeError, KeyError, UnicodeError):
        return unknown(
            "native verdict snapshot missing, malformed, or does not cover this date"
        )


ENTRY = re.compile(
    r"^(?:malformed-grant$|grant-expired-unrun$|regions-unusable-for-|"
    r"diagnostic-bypass-id-mismatch$|t1-admission:|window-\d+s-below-min-|"
    r"stop-file-before-start$|build-missing:|refused:)"
)
END = re.compile(r"^rc=(\d+) time=(\S+) reason=(.+)$")


def terminal_observations(raw: bytes | None, day: str) -> dict:
    rows, bad = records(raw)
    events, conflicts = {}, 0
    for row in rows:
        try:
            rid, line = row["id"], row["end_line"]
            match = END.fullmatch(line)
            if not isinstance(rid, str) or not rid or match is None:
                raise ValueError("terminal metadata")
            rc, stamp, reason = match.groups()
            if utc_date(stamp) != day:
                continue
            key = (rid, stamp)
            value = (int(rc), reason)
            if key in events and events[key] != value:
                conflicts += 1
            events.setdefault(key, value)
        except (ValueError, TypeError, KeyError):
            bad += 1
    entry = started = phase_unknown = 0
    for rc, reason in events.values():
        if rc != 0 and ENTRY.match(reason):
            entry += 1
        elif reason == "complete" or reason.startswith("job-rc-"):
            started += 1
        else:
            phase_unknown += 1
    return unknown(
        "filing-due deduplicates by run id; no complete admission-attempt coverage",
        unit="failed-at-entry / all admission attempts",
        observed_terminal_records=len(events),
        confirmed_entry_failures=entry,
        confirmed_job_terminals=started,
        phase_unknown=phase_unknown,
        malformed_or_partial_records=bad,
        conflicting_records=conflicts,
    )


def idle_observations(raw: bytes | None, day: str) -> dict:
    rows, bad = records(raw)
    seen, regions = set(), {}
    for row in rows:
        try:
            if row["kind"] != "idle" or utc_date(row["ts"]) != day:
                continue
            named = row["regions"].split()
            if not named or any(
                r not in ("q0", "q1", "q2", "q3", "gpu-quiet") for r in named
            ):
                raise ValueError("idle region")
            key = (row["ts"], tuple(sorted(set(named))))
            if key in seen:
                continue
            seen.add(key)
            for r in set(named):
                regions[r] = regions.get(r, 0) + 1
        except (ValueError, TypeError, KeyError, AttributeError):
            bad += 1
    return unknown(
        "keeper emits throttled free-lock point alerts, without all state transitions or uptime coverage",
        unit="hours",
        idle_alerts=len(seen),
        region_alerts=regions,
        malformed_or_partial_records=bad,
    )


def prospective(raw: bytes | None) -> dict:
    from loop_metrics_events import fold, fold_idle

    rows, bad = records(raw)
    if bad:
        return unknown(
            "prospective event stream missing, malformed, or partially appended",
            malformed_or_partial_records=bad,
        )
    try:
        sessions = fold(rows)
        idle_intervals = fold_idle(rows)
    except (ValueError, TypeError, KeyError):
        return unknown("prospective event schema refused")
    return {
        "status": "observed",
        "sessions": sessions,
        "kernel_idle_counter_intervals": idle_intervals,
        "scope": "only named producer sessions; not proof every calendar/launcher was instrumented",
        "hardware_idle_hours": None,
    }


def report(
    day: str, verdict: Path | None, due: Path, idle: Path, events: Path | None = None
) -> dict:
    dt.date.fromisoformat(day)
    inputs = [read_source(path) for path in (verdict, due, idle, events)]
    return {
        "schema": "daily-loop-metrics/v1",
        "date": day,
        "decision_results": decisions(inputs[0][0], day),
        "idle_hours": idle_observations(inputs[2][0], day),
        "failed_at_entry_rate": terminal_observations(inputs[1][0], day),
        "prospective_coverage": prospective(inputs[3][0]),
        "operator_messages": unknown(
            "no authorized human-message metadata producer; automated nudges excluded"
        ),
        "sources": dict(
            zip(
                (
                    "verdict_snapshot",
                    "filing_due",
                    "keeper_alerts",
                    "prospective_events",
                ),
                (meta for _, meta in inputs),
            )
        ),
        "scope": "read-only operational bookkeeping; no grading or scheduler policy changes",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date", default=dt.datetime.now(dt.timezone.utc).date().isoformat()
    )
    parser.add_argument("--verdict-snapshot", type=Path)
    parser.add_argument("--filing-due", type=Path, default=FLAGS / "filing-due.jsonl")
    parser.add_argument(
        "--keeper-alerts", type=Path, default=FLAGS / "ws58-keeper-alerts.jsonl"
    )
    parser.add_argument(
        "--events", type=Path, help="optional prospective append-only metadata ledger"
    )
    args = parser.parse_args(argv)
    try:
        result = report(
            args.date,
            args.verdict_snapshot,
            args.filing_due,
            args.keeper_alerts,
            args.events,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

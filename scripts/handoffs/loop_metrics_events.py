#!/usr/bin/env python3
"""Append-only operational metadata. No scheduler/model/message operations.

Caller owns coverage boundaries and its expected event count. A missing close,
count mismatch, partial append or cap refusal leaves coverage unknown. Idle
transitions mean calendar reservation state, never measured hardware idleness.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import stat
import time
from itertools import pairwise
from pathlib import Path

CAP = 16 * 1024 * 1024
KINDS = {
    "coverage_open",
    "coverage_close",
    "attempt_begin",
    "attempt_end",
    "reservation_open",
    "reservation_close",
    "attempt_deferred",
    "idle_counter",
}
TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
FIELDS = {
    "kind",
    "producer",
    "session",
    "ordinal",
    "at_ns",
    "attempt",
    "phase",
    "rc",
    "resource",
    "reservation",
    "expected_events",
    "resources",
    "boot_id",
    "hz",
    "monotonic_ns",
    "idle_ticks",
}


def validate(row: dict) -> None:
    if not isinstance(row, dict) or set(row) - FIELDS:
        raise ValueError("unrecognized metadata fields")
    if row.get("kind") not in KINDS:
        raise ValueError("event kind")
    for name in ("producer", "session"):
        if not isinstance(row.get(name), str) or not TOKEN.fullmatch(row[name]):
            raise ValueError(name)
    for name in ("ordinal", "at_ns"):
        if type(row.get(name)) is not int or row[name] < 0:
            raise ValueError(name)
    kind = row["kind"]
    required = {"kind", "producer", "session", "ordinal", "at_ns"}
    if kind == "idle_counter":
        required |= {"boot_id", "hz", "monotonic_ns", "idle_ticks"}
        if not isinstance(row.get("boot_id"), str) or not TOKEN.fullmatch(
            row["boot_id"]
        ):
            raise ValueError("boot identity")
        if type(row.get("hz")) is not int or not 0 < row["hz"] <= 100000:
            raise ValueError("kernel clock rate")
        if type(row.get("monotonic_ns")) is not int or row["monotonic_ns"] <= 0:
            raise ValueError("monotonic clock")
        ticks = row.get("idle_ticks")
        if not isinstance(ticks, dict) or not ticks or len(ticks) > 192:
            raise ValueError("CPU counters")
        for cpu, value in ticks.items():
            if (
                not isinstance(cpu, str)
                or not re.fullmatch(r"cpu[0-9]{1,3}", cpu)
                or type(value) is not int
                or not 0 <= value < 2**64
            ):
                raise ValueError("CPU counter")
    if kind.startswith("attempt_"):
        required |= {"attempt", "phase"}
        if row.get("phase") not in (
            "calendar-admission",
            "launcher-admission",
            "job-outcome",
        ):
            raise ValueError("attempt phase")
        if not isinstance(row.get("attempt"), str) or not TOKEN.fullmatch(
            row["attempt"]
        ):
            raise ValueError("attempt identity")
        if kind == "attempt_end":
            required.add("rc")
            if type(row.get("rc")) is not int or not 0 <= row["rc"] <= 255:
                raise ValueError("return code")
    if kind.startswith("reservation_"):
        required |= {"reservation", "resource"}
        if row.get("resource") not in ("q0", "q1", "q2", "q3", "gpu-quiet"):
            raise ValueError("resource")
        if not isinstance(row.get("reservation"), str) or not TOKEN.fullmatch(
            row["reservation"]
        ):
            raise ValueError("reservation identity")
    if kind == "coverage_open":
        required.add("resources")
        resources = row.get("resources")
        if (
            not isinstance(resources, list)
            or any(not isinstance(r, str) for r in resources)
            or len(resources) != len(set(resources))
            or any(r not in ("q0", "q1", "q2", "q3", "gpu-quiet") for r in resources)
        ):
            raise ValueError("coverage resources")
    if kind == "coverage_close":
        required.add("expected_events")
        if type(row.get("expected_events")) is not int or row["expected_events"] < 0:
            raise ValueError("expected event count")
    if set(row) != required:
        raise ValueError("missing or extraneous metadata")


def append(path: Path, row: dict, *, cap: int = CAP) -> None:
    validate(row)
    if type(cap) is not int or not 0 < cap <= CAP:
        raise ValueError("metadata cap")
    raw = json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    fd = os.open(
        path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
        ):
            raise ValueError("not own regular single-link ledger")
        if info.st_size + len(raw) > cap:
            raise ValueError("metadata cap reached; coverage incomplete")
        # One bounded append under the ledger's own lock; never replacement/rename.
        if os.write(fd, raw) != len(raw):
            raise OSError("partial metadata append; coverage incomplete")
        os.fsync(fd)
    finally:
        os.close(fd)


def require(condition):
    if not condition:
        raise ValueError("incomplete event coverage")


def fold(rows: list[dict]) -> list[dict]:
    """Fold sealed sessions only; missing/duplicate/out-of-order data refuse coverage.

    resources is the caller's explicit reservation-authority scope, initially
    empty at coverage_open. Existing reservations must be emitted at that same
    timestamp. A clean close plus expected ordinal count is required. This is
    NOT an assertion that no unregistered process consumed those resources.
    """
    grouped = {}
    for row in rows:
        validate(row)
        if row["kind"] != "idle_counter":
            grouped.setdefault((row["producer"], row["session"]), []).append(row)
    reports = []
    for (producer, session), events in grouped.items():
        result = {
            "producer": producer,
            "session": session,
            "status": "unknown",
            "reason": "unsealed or inconsistent event coverage",
        }
        try:
            require(sum(e["kind"] == "coverage_open" for e in events) == 1)
            require(sum(e["kind"] == "coverage_close" for e in events) == 1)
            require(events[0]["kind"] == "coverage_open")
            require(events[-1]["kind"] == "coverage_close")
            require([e["ordinal"] for e in events] == list(range(len(events))))
            require(events[-1]["expected_events"] == len(events) - 2)
            require(all(a["at_ns"] <= b["at_ns"] for a, b in pairwise(events)))
            opened, closed = events[0]["at_ns"], events[-1]["at_ns"]
            require(closed > opened)
            resources = events[0]["resources"]
            active, attempts, outcomes = {}, {}, {}
            busy = {r: 0 for r in resources}
            last = opened
            for event in events[1:]:
                now = event["at_ns"]
                for resource in {r for r in active.values()}:
                    busy[resource] += now - last
                last = now
                kind = event["kind"]
                if kind == "reservation_open":
                    rid, resource = event["reservation"], event["resource"]
                    require(resource in busy and rid not in active)
                    active[rid] = resource
                elif kind == "reservation_close":
                    rid, resource = event["reservation"], event["resource"]
                    require(active.pop(rid) == resource)
                elif kind == "attempt_begin":
                    key = (event["phase"], event["attempt"])
                    require(key not in attempts)
                    attempts[key] = event
                elif kind in ("attempt_end", "attempt_deferred"):
                    key = (event["phase"], event["attempt"])
                    require(key in attempts and key not in outcomes)
                    outcomes[key] = event.get("rc")
                else:
                    require(kind == "coverage_close")
            require(not active and attempts.keys() == outcomes.keys())
            phases = {}
            for phase in ("calendar-admission", "launcher-admission", "job-outcome"):
                values = [
                    rc
                    for (p, _), rc in outcomes.items()
                    if p == phase and rc is not None
                ]
                phases[phase] = {
                    "attempts": len(values),
                    "failures": sum(rc != 0 for rc in values),
                    "failure_rate": sum(rc != 0 for rc in values) / len(values)
                    if values
                    else None,
                }
            result = {
                "producer": producer,
                "session": session,
                "status": "sealed",
                "covered_from_ns": opened,
                "covered_to_ns": closed,
                "basis": "calendar reservation accounting; not measured hardware idle",
                "calendar_unreserved_hours": {
                    r: (closed - opened - busy[r]) / 3.6e12 for r in resources
                },
                "attempt_phases": phases,
            }
        except (ValueError, KeyError, TypeError):
            pass
        reports.append(result)
    return reports


def parse_cpus(value: str) -> list[int]:
    cpus = []
    for part in value.split(","):
        if not re.fullmatch(r"[0-9]{1,3}(?:-[0-9]{1,3})?", part):
            raise ValueError("CPU list")
        pair = [int(n) for n in part.split("-")]
        first, last = pair if len(pair) == 2 else (pair[0], pair[0])
        if first > last or last > 191:
            raise ValueError("CPU range")
        cpus.extend(range(first, last + 1))
    if not cpus or len(cpus) != len(set(cpus)):
        raise ValueError("duplicate or empty CPUs")
    return sorted(cpus)


def capture_idle(
    cpus: list[int],
    producer: str,
    session: str,
    ordinal: int,
    proc: Path = Path("/proc"),
) -> dict:
    boot_before = (proc / "sys/kernel/random/boot_id").read_text().strip()
    before = time.monotonic_ns()
    wanted = {"cpu" + str(n) for n in cpus}
    ticks = {}
    for line in (proc / "stat").read_text().splitlines():
        fields = line.split()
        if fields and fields[0] in wanted:
            if len(fields) < 6:
                raise ValueError("incomplete kernel counter")
            ticks[fields[0]] = int(
                fields[4]
            )  # idle ONLY; iowait is deliberately excluded.
    if (
        ticks.keys() != wanted
        or (proc / "sys/kernel/random/boot_id").read_text().strip() != boot_before
    ):
        raise ValueError("CPU set or boot changed while capturing counters")
    result = {
        "kind": "idle_counter",
        "producer": producer,
        "session": session,
        "ordinal": ordinal,
        "at_ns": time.time_ns(),
        "monotonic_ns": before,
        "boot_id": boot_before,
        "hz": os.sysconf("SC_CLK_TCK"),
        "idle_ticks": ticks,
    }
    validate(result)
    return result


def fold_idle(rows: list[dict]) -> list[dict]:
    grouped = {}
    for row in rows:
        validate(row)
        if row["kind"] == "idle_counter":
            grouped.setdefault((row["producer"], row["session"]), []).append(row)
    intervals = []
    for key, samples in grouped.items():
        for a, b in pairwise(samples):
            result = {
                "producer": key[0],
                "session": key[1],
                "status": "unknown",
                "reason": "boot/HZ/CPU/counter/clock continuity refused",
            }
            try:
                require(a["boot_id"] == b["boot_id"] and a["hz"] == b["hz"])
                require(a["idle_ticks"].keys() == b["idle_ticks"].keys())
                require(
                    a["ordinal"] < b["ordinal"]
                    and a["monotonic_ns"] < b["monotonic_ns"]
                    and a["at_ns"] < b["at_ns"]
                )
                delta = [
                    b["idle_ticks"][cpu] - value
                    for cpu, value in a["idle_ticks"].items()
                ]
                require(all(n >= 0 for n in delta))
                result = {
                    "producer": key[0],
                    "session": key[1],
                    "status": "observed",
                    "covered_from_ns": a["at_ns"],
                    "covered_to_ns": b["at_ns"],
                    "kernel_accounted_cpu_idle_hours": sum(delta) / a["hz"] / 3600,
                    "cpus": sorted(a["idle_ticks"]),
                    "iowait": "excluded",
                    "basis": "same-boot cumulative /proc/stat idle counters; CPU-hours, not physical hardware-idle or whole-resource wall hours",
                }
            except (ValueError, KeyError, TypeError):
                pass
            intervals.append(result)
    return intervals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--event")
    group.add_argument("--capture-cpus")
    parser.add_argument("--producer", default="keeper-idle-counter")
    parser.add_argument("--session")
    parser.add_argument("--ordinal", type=int)
    args = parser.parse_args(argv)
    try:
        if args.capture_cpus is not None:
            row = capture_idle(
                parse_cpus(args.capture_cpus), args.producer, args.session, args.ordinal
            )
        else:
            row = json.loads(args.event)
            row.setdefault("at_ns", time.time_ns())
        append(args.ledger, row)
    except (ValueError, OSError) as exc:
        parser.exit(1, "loop-metrics metadata refused: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

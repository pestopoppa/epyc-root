#!/usr/bin/env python3
"""Nudge the coordinator once for each overdue, unfiled run (LOOP-27).

Called by the existing filing watcher after its discovery pass. It observes the
existing due producer and FILED markers; it never edits either or claims filing
has happened. The dedicated filing-watch service writes only its own outbox.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.coordination import session_bus as bus  # noqa: E402 - bootstrap repo for direct -I entry

SERVICE = "filing-watch"
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise TypeError("seen_at must be a timestamp string")
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("seen_at requires a timezone")
    return value.astimezone(timezone.utc)


def scan_once(
    flags_root: Path,
    bus_root: Path,
    *,
    now: datetime | None = None,
    recipient: str = "coordinator-agent",
) -> dict:
    """Own alerts remain available when native bus authoring is unavailable."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("the observation clock requires a timezone")
    report = {
        "nudged": [],
        "alerted": [],
        "unknown": [],
        "observed_at": now.isoformat(),
        "bus_status": "not_needed",
    }
    with (flags_root / "filing-takeover-alarm.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        alert_path = flags_root / "filing-alarm.jsonl"
        alert_state_path = flags_root / "filing-alarm.alerted.json"
        owner_state = (
            json.loads(alert_state_path.read_text())
            if alert_state_path.exists()
            else {"alerted": []}
        )
        if (
            not isinstance(owner_state, dict)
            or not isinstance(owner_state.get("alerted"), list)
            or any(
                not isinstance(x, str) or not RUN_ID.fullmatch(x)
                for x in owner_state["alerted"]
            )
        ):
            raise ValueError(
                "invalid own alert checkpoint; refusing to guess prior delivery"
            )
        alerted = set(owner_state["alerted"])
        if alert_path.exists():
            for line in alert_path.read_text(encoding="utf-8").splitlines(
                keepends=True
            ):
                if not line.strip():
                    continue
                if not line.endswith("\n"):
                    raise ValueError(
                        "unterminated own alert stream; refusing to guess prior delivery"
                    )
                record = json.loads(line)
                if (
                    not isinstance(record, dict)
                    or record.get("schema_version") != "epyc.filing-alarm.v1"
                    or record.get("kind") != "filing-overdue"
                    or not isinstance(record.get("id"), str)
                    or not RUN_ID.fullmatch(record["id"])
                ):
                    raise ValueError(
                        "invalid own alert stream; refusing to guess prior delivery"
                    )
                alerted.add(record["id"])

        def owner_checkpoint():
            bus._write_atomic(alert_state_path, {"alerted": sorted(alerted)})

        if alerted != set(owner_state["alerted"]):
            owner_checkpoint()
        due = flags_root / "filing-due.jsonl"
        eligible = {}
        for number, line in enumerate(
            due.read_text(encoding="utf-8").splitlines(keepends=True), 1
        ):
            if not line.strip():
                continue
            if not line.endswith("\n"):
                report["unknown"].append(
                    {"line": number, "reason": "unterminated due row"}
                )
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise TypeError("due row must be an object")
                run_id = row.get("id")
                if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
                    raise ValueError("invalid run identity")
                seen = _timestamp(row.get("seen_at"))
            except (ValueError, TypeError) as exc:
                report["unknown"].append({"line": number, "reason": str(exc)})
                continue
            if (flags_root / "filing-done" / f"{run_id}.FILED").is_file():
                continue
            age = (now - seen).total_seconds()
            if age <= 3600:
                continue
            eligible.setdefault(run_id, (row, age))
            if run_id not in alerted:
                record = {
                    "schema_version": "epyc.filing-alarm.v1",
                    "kind": "filing-overdue",
                    "id": run_id,
                    "seen_at": row["seen_at"],
                    "observed_at": now.isoformat(),
                    "age_seconds": int(age),
                    "action": "filing-takeover",
                    "bus_sender": SERVICE,
                    "bus_recipient": recipient,
                    "filing_due": str(due),
                }
                with alert_path.open("a", encoding="utf-8") as out:
                    out.write(json.dumps(record, sort_keys=True) + "\n")
                    out.flush()
                    os.fsync(out.fileno())
                alerted.add(run_id)
                owner_checkpoint()
                report["alerted"].append(run_id)
        if not eligible:
            return report
        # This separate phase cannot prevent the durable owner alert above.
        try:
            bus._require_roster_id(bus_root, SERVICE)
            bus._require_roster_id(bus_root, recipient)
            messages, _end_offset = bus._read_jsonl(
                bus_root / "outbox" / f"{SERVICE}.jsonl"
            )
            if any(not isinstance(message, dict) for message in messages):
                raise ValueError("cannot establish prior nudge identity")
            state_path = flags_root / "filing-alarm.sent.json"
            state = (
                json.loads(state_path.read_text())
                if state_path.exists()
                else {"sent": []}
            )
            if (
                not isinstance(state, dict)
                or not isinstance(state.get("sent"), list)
                or any(
                    not isinstance(x, str) or not RUN_ID.fullmatch(x)
                    for x in state["sent"]
                )
            ):
                raise ValueError(
                    "invalid sent checkpoint; refusing to guess prior delivery"
                )
            sent = set(state["sent"])
            sent.update(
                m["payload"]["run_id"]
                for m in messages
                if m.get("from") == SERVICE
                and m.get("kind") == "nudge"
                and isinstance(m.get("payload"), dict)
                and m["payload"].get("alarm") == "LOOP-27"
                and isinstance(m["payload"].get("run_id"), str)
            )

            def bus_checkpoint():
                bus._write_atomic(state_path, {"sent": sorted(sent)})

            if sent != set(state["sent"]):
                bus_checkpoint()
            for run_id, (row, age) in eligible.items():
                if run_id in sent:
                    continue
                message = {
                    "to": recipient,
                    "kind": "nudge",
                    "action_required": True,
                    "assignee": recipient,
                    "payload": {
                        "alarm": "LOOP-27",
                        "subject": "Unfiled compute result exceeds the filing window",
                        "run_id": run_id,
                        "seen_at": row["seen_at"],
                        "age_seconds": int(age),
                        "filing_due": str(due),
                        "detail": "Arrange filing or takeover per compute-owner-takeover.md; this alarm performs no filing or ownership transfer.",
                    },
                }
                rc = bus.main(
                    [
                        "--bus-root",
                        str(bus_root),
                        "append",
                        "--agent",
                        SERVICE,
                        "--target",
                        "outbox",
                        "--json",
                        json.dumps(message),
                    ]
                )
                if rc:
                    raise RuntimeError(f"bus append refused for {run_id}: rc={rc}")
                sent.add(run_id)
                bus_checkpoint()
                report["nudged"].append(run_id)
            report["bus_status"] = "observed"
        except (OSError, ValueError, RuntimeError, bus.BusError) as exc:
            report["bus_status"] = "unknown"
            report["unknown"].append({"component": "bus", "reason": str(exc)})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--flags-root", type=Path, required=True)
    parser.add_argument(
        "--bus-root", type=Path, default=Path("/workspace/coordination/session-bus")
    )
    parser.add_argument("--recipient", default="coordinator-agent")
    args = parser.parse_args(argv)
    try:
        report = scan_once(args.flags_root, args.bus_root, recipient=args.recipient)
    except (OSError, ValueError, RuntimeError, bus.BusError) as exc:
        print(json.dumps({"status": "unknown", "reason": str(exc)}), file=sys.stderr)
        return 2
    report["status"] = "unknown" if report["unknown"] else "observed"
    print(json.dumps(report, sort_keys=True))
    return 2 if report["unknown"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

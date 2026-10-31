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
    """Use existing schema validation/single-writer rules; keep unknown input unknown."""
    bus._require_roster_id(bus_root, SERVICE)
    bus._require_roster_id(bus_root, recipient)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("the observation clock requires a timezone")
    report = {"nudged": [], "unknown": [], "observed_at": now.isoformat()}
    # One lock covers scan/append/checkpoint. Reconcile the current own outbox
    # before appending; a persistent sent checkpoint also survives outbox rotation.
    with (flags_root / "filing-takeover-alarm.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            messages, _end_offset = bus._read_jsonl(
                bus_root / "outbox" / f"{SERVICE}.jsonl"
            )
        except bus.BusError as exc:
            raise ValueError("cannot establish prior nudge identity") from exc
        if any(not isinstance(message, dict) for message in messages):
            raise ValueError("cannot establish prior nudge identity")
        state_path = flags_root / "filing-alarm.sent.json"
        state = (
            json.loads(state_path.read_text()) if state_path.exists() else {"sent": []}
        )
        if (
            not isinstance(state, dict)
            or not isinstance(state.get("sent"), list)
            or any(
                not isinstance(x, str) or not RUN_ID.fullmatch(x) for x in state["sent"]
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
        if sent != set(state["sent"]):
            bus._write_atomic(state_path, {"sent": sorted(sent)})
        due = flags_root / "filing-due.jsonl"
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
            if (
                run_id in sent
                or (flags_root / "filing-done" / f"{run_id}.FILED").is_file()
            ):
                continue
            age = (now - seen).total_seconds()
            if age <= 3600:
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
            bus._write_atomic(state_path, {"sent": sorted(sent)})
            report["nudged"].append(run_id)
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

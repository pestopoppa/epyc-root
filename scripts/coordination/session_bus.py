#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""session_bus.py — bus library + CLI for the session bus (M1).

Runs under the orchestrator venv (matching compile_inference_batch.py) because
that is the interpreter carrying jsonschema; the system python3 does not.

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Contract:       coordination/session-bus/BUS_PROTOCOL.md

Verbs
  append    schema-validated row -> a file the caller OWNS (refuses otherwise)
  fold      queue reconcile, latest-row-per-task_id wins (batch_ledger semantics)
  validate  whole-bus schema check + single-writer lint
  cursor    get/advance your own cursor (byte offsets)
  status    human summary: queue by status/lane, inbox depths, heartbeat ages
  drain     print your inbox past your cursor and advance it

Single-writer is STRUCTURAL, not advisory: `append` derives the required writer
from the target path and refuses a mismatch. One writer may own many files; no
file ever has two writers.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"

COORDINATOR_DAEMON = "coordinator-daemon"

MSG_SCHEMA_VERSION = "session_bus.msg.v1"
QUEUE_SCHEMA_VERSION = "session_bus.queue.v1"

TERMINAL_STATES = frozenset(
    {"DONE_PASS", "DONE_MARGINAL_OBS", "FAILED", "CANCELLED"}
)


class BusError(RuntimeError):
    """Protocol or validation violation. Message is operator-facing."""


# --------------------------------------------------------------------------- io


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_jsonl(path: Path, start: int = 0) -> tuple[list[dict], int]:
    """Return (rows, end_offset). Reads from byte offset `start`."""
    if not path.exists():
        return [], start
    with path.open("rb") as fh:
        fh.seek(start)
        raw = fh.read()
        end = fh.tell()
    rows = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise BusError(f"{path}: malformed JSONL near offset {start}: {e}") from e
    return rows, end


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _write_atomic(path: Path, payload: dict) -> None:
    """tmp+rename — heartbeats and cursors are overwritten, never appended."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ------------------------------------------------------------------- ownership


def required_writer(bus_root: Path, target: Path) -> str:
    """The ONE agent id permitted to write `target`.

    queue.jsonl and inbox/* belong to the coordinator-daemon; outbox/<a>,
    heartbeats/<a> and cursors/<a> belong to <a>.
    """
    try:
        rel = target.resolve().relative_to(bus_root.resolve())
    except ValueError as e:
        raise BusError(f"{target} is outside the bus root {bus_root}") from e
    parts = rel.parts
    if rel.name in {"queue.jsonl", "advisory.jsonl"} and len(parts) == 1:
        return COORDINATOR_DAEMON
    if len(parts) == 2:
        area, fname = parts
        stem = fname.split(".")[0]
        if area == "inbox":
            return COORDINATOR_DAEMON
        if area in {"outbox", "heartbeats", "cursors"}:
            return stem
    raise BusError(f"{rel} is not a writable bus file (no single-writer rule covers it)")


# --------------------------------------------------------------------- schema


def _load_schema(bus_root: Path) -> dict:
    path = bus_root / "session_bus.schema.json"
    if not path.exists():
        raise BusError(f"schema not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema: dict, definition: str):
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return None
    sub = {"$schema": schema["$schema"], "definitions": schema["definitions"],
           "$ref": f"#/definitions/{definition}"}
    return jsonschema.Draft7Validator(sub)


def validate_row(bus_root: Path, row: dict, definition: str) -> None:
    """Raise BusError on a structural violation. Degrades to a required-key
    check when jsonschema is unavailable, and says so rather than passing
    silently."""
    validator = _validator(_load_schema(bus_root), definition)
    if validator is None:
        required = {"msg": ["schema_version", "id", "ts", "from", "to", "kind"],
                    "queue_row": ["schema_version", "ts", "task_id", "status", "lane",
                                  "gating", "epoch"]}[definition]
        missing = [k for k in required if k not in row]
        if missing:
            raise BusError(f"missing required field(s) {missing} (jsonschema unavailable — "
                           "structural check was partial)")
        return
    errors = sorted(validator.iter_errors(row), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                           for e in errors[:5])
        raise BusError(f"schema violation: {detail}")


# ----------------------------------------------------------------------- fold


def fold_queue(bus_root: Path) -> dict[str, dict]:
    """Latest row per task_id wins — batch_ledger.reconcile semantics."""
    rows, _ = _read_jsonl(bus_root / "queue.jsonl")
    latest: dict[str, dict] = {}
    for row in rows:
        tid = row.get("task_id")
        if tid:
            latest[tid] = row
    return latest


# ------------------------------------------------------------------ commands


def cmd_append(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    row = json.loads(args.json)

    if args.target == "queue":
        path = bus_root / "queue.jsonl"
        definition = "queue_row"
        row.setdefault("schema_version", QUEUE_SCHEMA_VERSION)
    elif args.target == "inbox":
        if not args.to:
            raise BusError("--target inbox requires --to <agent>")
        path = bus_root / "inbox" / f"{args.to}.jsonl"
        definition = "msg"
    elif args.target == "outbox":
        path = bus_root / "outbox" / f"{args.agent}.jsonl"
        definition = "msg"
    else:  # heartbeat
        path = bus_root / "heartbeats" / f"{args.agent}.json"
        owner = required_writer(bus_root, path)
        if owner != args.agent:
            raise BusError(f"{args.agent} may not write {path.name} (owner: {owner})")
        row.setdefault("agent", args.agent)
        row.setdefault("ts", _utcnow_iso())
        _write_atomic(path, row)
        print(f"heartbeat: {path}")
        return 0

    owner = required_writer(bus_root, path)
    if owner != args.agent:
        raise BusError(
            f"single-writer violation: {args.agent} may not write {path.relative_to(bus_root)} "
            f"— that file's only writer is {owner}"
        )

    row.setdefault("ts", _utcnow_iso())
    if definition == "msg":
        row.setdefault("schema_version", MSG_SCHEMA_VERSION)
        row.setdefault("from", args.agent)
        existing, _ = _read_jsonl(path)
        # Compact UTC stamp: sortable and free of '+' / offset punctuation, so
        # the id stays a single clean token. `ts` keeps the full ISO form.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        row.setdefault("id", f"msg-{stamp}-{len(existing) + 1}-{args.agent}")

    validate_row(bus_root, row, definition)
    _append_jsonl(path, row)
    print(f"appended -> {path.relative_to(bus_root)}  ({row.get('id') or row.get('task_id')})")
    return 0


def cmd_fold(args: argparse.Namespace) -> int:
    latest = fold_queue(Path(args.bus_root))
    if args.json:
        print(json.dumps(latest, indent=2, sort_keys=True))
        return 0
    if not latest:
        print("(queue empty)")
        return 0
    print(f"{'task_id':<28} {'status':<18} {'lane':<5} {'gating':<6} {'owner':<18} epoch")
    for tid in sorted(latest):
        r = latest[tid]
        print(f"{tid:<28} {r.get('status',''):<18} {r.get('lane',''):<5} "
              f"{r.get('gating',''):<6} {str(r.get('owner') or '-'):<18} {r.get('epoch','')}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    problems: list[str] = []
    checked = 0

    queue = bus_root / "queue.jsonl"
    if queue.exists():
        rows, _ = _read_jsonl(queue)
        for i, row in enumerate(rows, 1):
            checked += 1
            try:
                validate_row(bus_root, row, "queue_row")
            except BusError as e:
                problems.append(f"queue.jsonl:{i}: {e}")

    for area in ("inbox", "outbox"):
        for path in sorted((bus_root / area).glob("*.jsonl")):
            expected = required_writer(bus_root, path)
            rows, _ = _read_jsonl(path)
            for i, row in enumerate(rows, 1):
                checked += 1
                try:
                    validate_row(bus_root, row, "msg")
                except BusError as e:
                    problems.append(f"{area}/{path.name}:{i}: {e}")
                # Single-writer lint: every row in an outbox must be FROM its owner.
                if area == "outbox" and row.get("from") != expected:
                    problems.append(
                        f"{area}/{path.name}:{i}: single-writer violation — from="
                        f"{row.get('from')!r} but this file's only writer is {expected!r}"
                    )

    for path in sorted((bus_root / "heartbeats").glob("*.json")):
        checked += 1
        try:
            hb = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"heartbeats/{path.name}: malformed: {e}")
            continue
        expected = required_writer(bus_root, path)
        if hb.get("agent") != expected:
            problems.append(f"heartbeats/{path.name}: agent={hb.get('agent')!r} != {expected!r}")
        if hb.get("state") not in {"idle", "working", "draining", None}:
            problems.append(f"heartbeats/{path.name}: bad state {hb.get('state')!r}")

    print(f"checked {checked} record(s)")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        return 1
    print("  OK — schema clean, single-writer clean")
    return 0


def _cursor_path(bus_root: Path, agent: str) -> Path:
    return bus_root / "cursors" / f"{agent}.json"


def _cursor_get(bus_root: Path, agent: str) -> int:
    path = _cursor_path(bus_root, agent)
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("offset", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0


def cmd_cursor(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    path = _cursor_path(bus_root, args.agent)
    owner = required_writer(bus_root, path)
    if owner != args.agent:
        raise BusError(f"{args.agent} may not write another agent's cursor")
    if args.set is None:
        print(_cursor_get(bus_root, args.agent))
        return 0
    _write_atomic(path, {"agent": args.agent, "offset": int(args.set), "ts": _utcnow_iso()})
    print(f"cursor[{args.agent}] = {args.set}")
    return 0


def cmd_drain(args: argparse.Namespace) -> int:
    """Print this agent's inbox past its cursor and advance. The one-liner
    agents run at every task boundary."""
    bus_root = Path(args.bus_root)
    inbox = bus_root / "inbox" / f"{args.agent}.jsonl"
    start = _cursor_get(bus_root, args.agent)
    rows, end = _read_jsonl(inbox, start)

    if not rows:
        print(f"(no new messages for {args.agent})")
        return 0
    for row in rows:
        print(json.dumps(row, sort_keys=True))
    if not args.peek:
        _write_atomic(_cursor_path(bus_root, args.agent),
                      {"agent": args.agent, "offset": end, "ts": _utcnow_iso()})
    print(f"-- {len(rows)} message(s); cursor {start} -> {end}"
          f"{' (peek: not advanced)' if args.peek else ''}", file=sys.stderr)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    latest = fold_queue(bus_root)

    by_status: dict[str, int] = {}
    by_lane: dict[str, int] = {}
    for row in latest.values():
        by_status[row.get("status", "?")] = by_status.get(row.get("status", "?"), 0) + 1
        by_lane[row.get("lane", "?")] = by_lane.get(row.get("lane", "?"), 0) + 1

    print("queue by status:", ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())) or "(empty)")
    print("queue by lane  :", ", ".join(f"{k}={v}" for k, v in sorted(by_lane.items())) or "(empty)")

    ready_none = sum(1 for r in latest.values()
                     if r.get("status") == "READY" and r.get("lane") == "none")
    print(f"lane:none READY depth: {ready_none}"
          + ("   <-- ALARM: never-block needs a non-empty none-lane backlog" if ready_none == 0 and latest else ""))

    print("\ninbox depths (unread past each cursor):")
    for path in sorted((bus_root / "inbox").glob("*.jsonl")):
        agent = path.stem
        rows, _ = _read_jsonl(path, _cursor_get(bus_root, agent))
        print(f"  {agent:<20} {len(rows)}")

    print("\nheartbeats:")
    now = time.time()
    hbs = sorted((bus_root / "heartbeats").glob("*.json"))
    if not hbs:
        print("  (none)")
    for path in hbs:
        try:
            hb = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  {path.stem:<20} MALFORMED")
            continue
        age = now - path.stat().st_mtime
        print(f"  {path.stem:<20} {hb.get('state','?'):<9} age={age:6.0f}s  task={hb.get('task_id') or '-'}")

    pending = bus_root / "tokens" / "token-queue.md"
    if pending.exists():
        text = pending.read_text(encoding="utf-8")
        print(f"\npending operator tokens: {text.count('- [ ]')} ungranted, {text.count('- [x]')} granted")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="session_bus.py", description=__doc__.split("\n")[0])
    p.add_argument("--bus-root", default=str(DEFAULT_BUS_ROOT))
    sub = p.add_subparsers(dest="cmd", required=True)

    ap = sub.add_parser("append", help="append a schema-validated row to a file you own")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--target", required=True, choices=["queue", "inbox", "outbox", "heartbeat"])
    ap.add_argument("--to", help="recipient agent (required for --target inbox)")
    ap.add_argument("--json", required=True, help="the row/message as a JSON object")
    ap.set_defaults(func=cmd_append)

    fp = sub.add_parser("fold", help="latest-row-per-task_id view of the queue")
    fp.add_argument("--json", action="store_true")
    fp.set_defaults(func=cmd_fold)

    vp = sub.add_parser("validate", help="whole-bus schema + single-writer lint")
    vp.set_defaults(func=cmd_validate)

    cp = sub.add_parser("cursor", help="get or set your own cursor")
    cp.add_argument("--agent", required=True)
    cp.add_argument("--set", type=int, default=None)
    cp.set_defaults(func=cmd_cursor)

    dp = sub.add_parser("drain", help="print your inbox past your cursor and advance")
    dp.add_argument("--agent", required=True)
    dp.add_argument("--peek", action="store_true", help="print without advancing the cursor")
    dp.set_defaults(func=cmd_drain)

    sp = sub.add_parser("status", help="human summary of bus state")
    sp.set_defaults(func=cmd_status)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BusError as e:
        print(f"session_bus: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

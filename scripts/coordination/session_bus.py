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
  drain     print your inbox past your cursor and advance it (--triage appends
            the routing standing-queue report)
  triage    the standing queue of messages ROUTED to you (needs_routing_to /
            action_required), printed IN FULL, cursor-independent — advancing a
            cursor never clears it; only a corr_id disposition from your own
            outbox does

Single-writer is STRUCTURAL, not advisory: `append` derives the required writer
from the target path and refuses a mismatch. One writer may own many files; no
file ever has two writers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    if rel.name in {"queue.jsonl", "advisory.jsonl", "boundary_state.json"} and len(parts) == 1:
        return COORDINATOR_DAEMON
    if len(parts) == 2:
        area, fname = parts
        stem = fname.split(".")[0]
        if area == "inbox":
            return COORDINATOR_DAEMON
        if area in {"outbox", "heartbeats", "cursors"}:
            return stem
    raise BusError(f"{rel} is not a writable bus file (no single-writer rule covers it)")


def _roster_ids(bus_root: Path) -> set[str]:
    """Read declared agent identities; malformed roster data is fail-closed."""
    try:
        import yaml
        cfg = yaml.safe_load((bus_root / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — caller needs an operator-facing error
        raise BusError(f"could not read config.yaml roster: {exc}") from exc
    roster = cfg.get("roster") if isinstance(cfg, dict) else None
    if not isinstance(roster, list):
        raise BusError("config.yaml roster is missing or malformed; refusing an unverified writer")
    ids = {str(row.get("id", "")).strip() for row in roster if isinstance(row, dict)} - {""}
    if not ids:
        raise BusError("config.yaml roster has no ids; refusing an unverified writer")
    return ids


def _require_roster_id(bus_root: Path, agent: str) -> None:
    ids = _roster_ids(bus_root)
    if agent not in ids:
        raise BusError(f"{agent!r} is not a roster id in config.yaml (have: {', '.join(sorted(ids))}). "
                       "Add the roster row first; task ids belong in the task_id field.")


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


# -------------------------------------------------------------- routing intent
#
# 2026-07-29: two routed messages were missed because routing intent lived as
# PROSE inside `payload` ("FOR FABLE-AUDITOR RELEVANT TO THE C9 REVIEW" in a
# defect_3 string; "action: DOC FIX requested … operator-directed relay") and a
# context-economy payload truncation cut exactly the sentences carrying it. No
# tool could have known better, because nothing structural said "this must reach
# agent X" or "this needs action". These fields and the triage view make that
# intent machine-readable, delivery-independent, and impossible to consume by
# advancing a cursor.

ROUTING_FIELD = "needs_routing_to"
ACTION_FIELD = "action_required"

# What clears an action_required item: any substantive response, or an ack that
# says WHAT HAPPENED. A bare ack is receipt, not action.
TERMINAL_DISPOSITIONS = frozenset({"done", "declined", "handed-off", "superseded"})

_ROUTING_KEYWORD = (r"(?:\bfor\b|\brelay\b|\broute\b|\bforward\b|\battention\b|"
                    r"\brelevant\b|\bmust\s+reach\b)")
_ACTION_PROSE = re.compile(
    r"\baction[\s_-]*(?:required|requested)\b|\brequires\s+action\b", re.IGNORECASE)


def logical_id(row: dict) -> str:
    """One id per logical message: a daemon relay copy (relayed_src set) and its
    outbox original are the SAME message to triage, so a disposition against
    either id clears both."""
    return str(row.get("relayed_src") or row.get("id") or "")


def routing_targets(row: dict) -> list[str]:
    """Roster ids this message is structurally routed to. Empty list = not
    routed (ordinary mail; drain covers it)."""
    targets = row.get(ROUTING_FIELD)
    if isinstance(targets, list) and targets:
        return [str(t) for t in targets]
    to = str(row.get("to") or "")
    if row.get(ACTION_FIELD) and to and to != "*":
        return [to]
    return []


def prose_routing_warnings(row: dict, roster_ids: set[str]) -> list[str]:
    """Warn on the exact shape that failed 2026-07-29: routing/action intent
    written as payload prose while the structural field is unset. Advisory —
    never a failure — so existing history stays valid."""
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return []
    text = json.dumps(payload, sort_keys=True)
    warnings: list[str] = []
    if not row.get(ROUTING_FIELD):
        excluded = {str(row.get("from") or ""), str(row.get("to") or "")}
        for rid in sorted(roster_ids - excluded):
            pattern = re.compile(
                _ROUTING_KEYWORD + r"[^\n]{0,60}" + re.escape(rid) + r"|" + re.escape(rid)
                + r"[^\n]{0,60}(?:\brelevant\b|\battention\b|\bmust\b)", re.IGNORECASE)
            if pattern.search(text):
                warnings.append(
                    f"payload names {rid!r} in a routing phrase but {ROUTING_FIELD} is unset — "
                    f"prose routing intent is invisible to tools and was truncated away on "
                    f"2026-07-29; set {ROUTING_FIELD}: [\"{rid}\"]")
                break
    if not row.get(ACTION_FIELD) and (
            isinstance(payload.get("action"), str) or _ACTION_PROSE.search(text)):
        warnings.append(
            f"payload carries an action request in prose but {ACTION_FIELD} is unset — set "
            f"{ACTION_FIELD}: true so the request sits in the recipient's triage queue until "
            f"dispositioned instead of dying in a truncated summary")
    return warnings


def routed_view(bus_root: Path, agent: str) -> dict[str, list[dict]]:
    """The standing routing queue for `agent`, derived from bus files alone.

    DISCOVERY IS DELIVERY-INDEPENDENT: the agent's full inbox (from byte 0 —
    cursors are never consulted, so draining cannot consume this queue) PLUS
    every outbox, so a message stuck in a sender's outbox because the relay
    never ran (defect C2's shape) is still visible to its target. Reading
    another agent's outbox is legal — single-writer governs writes.

    STATE per logical message, judged only from the agent's OWN outbox rows
    whose corr_id resolves (via relay-copy aliases) to the message:
      pending   -> no reference at all
      acked     -> bare ack(s) only; clears reach-only messages, but an
                   action_required message KEEPS APPEARING (receipt != action)
      actioned  -> any non-ack kind, or an ack with payload.disposition in
                   TERMINAL_DISPOSITIONS; drops off the queue
    Self-authored messages are excluded: the writer cannot miss its own mail.
    """
    inbox_rows, _ = _read_jsonl(bus_root / "inbox" / f"{agent}.jsonl")
    alias = {str(r.get("id")): logical_id(r) for r in inbox_rows if r.get("relayed_src")}
    entries: dict[str, dict] = {}

    def note(row: dict, source: str, delivered: bool) -> None:
        if str(row.get("from") or "") == agent or agent not in routing_targets(row):
            return
        entry = entries.setdefault(logical_id(row),
                                   {"row": row, "sources": [], "delivered": False})
        entry["sources"].append(source)
        if delivered:
            entry["row"] = row
            entry["delivered"] = True

    for row in inbox_rows:
        note(row, f"inbox/{agent}.jsonl", True)
    for path in sorted((bus_root / "outbox").glob("*.jsonl")):
        rows, _ = _read_jsonl(path)
        for row in rows:
            note(row, f"outbox/{path.name}", False)

    my_outbox, _ = _read_jsonl(bus_root / "outbox" / f"{agent}.jsonl")
    state: dict[str, str] = {}
    for row in my_outbox:
        corr = str(row.get("corr_id") or "")
        if not corr:
            continue
        lid = alias.get(corr, corr)
        if lid not in entries:
            continue
        disposition = (row.get("payload") or {}).get("disposition")
        if row.get("kind") != "ack" or disposition in TERMINAL_DISPOSITIONS:
            state[lid] = "actioned"
        else:
            state.setdefault(lid, "acked")

    pending: list[dict] = []
    acked_awaiting: list[dict] = []
    for lid in sorted(entries):
        entry = entries[lid]
        status = state.get(lid)
        if status == "actioned":
            continue
        if status == "acked":
            if entry["row"].get(ACTION_FIELD):
                acked_awaiting.append(entry)
            continue
        pending.append(entry)
    return {"pending": pending, "acked_awaiting_action": acked_awaiting}


def print_triage(bus_root: Path, agent: str) -> None:
    """Print the standing queue IN FULL, in a TRUNCATION-EVIDENT frame.

    A message a tool shortened for context economy is exactly how the two
    2026-07-29 routed messages were lost — so this report is built to make any
    downstream truncation VISIBLY wrong rather than quietly lossy: every item
    sits between numbered BEGIN/END fences carrying its byte count and body
    sha256, and the report ends with a COMPLETE trailer. A copy missing an END
    fence or the trailer is provably cut; a fence whose byte count or digest
    disagrees with its body is provably altered.
    """
    import hashlib

    view = routed_view(bus_root, agent)
    pending, acked = view["pending"], view["acked_awaiting_action"]
    if not pending and not acked:
        print(f"(triage: no routed messages awaiting {agent})")
        return

    total = len(pending) + len(acked)
    body_bytes = 0
    index = 0

    def fenced(entry: dict, section: str) -> None:
        nonlocal index, body_bytes
        index += 1
        body = json.dumps(entry["row"], indent=2, sort_keys=True)
        body_bytes += len(body.encode("utf-8"))
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        print(f"--- BEGIN ROUTED MESSAGE {index}/{total} id={logical_id(entry['row'])} "
              f"section={section} bytes={len(body.encode('utf-8'))} sha256={digest} ---")
        undelivered = ("" if entry["delivered"] else
                       "   [NOT in your inbox — found by outbox scan; the relay may never "
                       "have delivered it]")
        print(f"via: {' + '.join(entry['sources'])}{undelivered}")
        print(body)
        print(f"--- END ROUTED MESSAGE {index}/{total} id={logical_id(entry['row'])} ---")

    print(f"== TRIAGE STANDING QUEUE for {agent}: {total} item(s). REPRODUCED IN FULL — "
          f"DO NOT TRUNCATE OR SUMMARIZE: a shortened copy of this report loses routed "
          f"intent (the 2026-07-29 failure shape). Every item has an END fence; the report "
          f"ends with a COMPLETE trailer. ==")
    if pending:
        print(f"-- {len(pending)} awaiting disposition --")
        for entry in pending:
            fenced(entry, "pending")
    if acked:
        print(f"-- {len(acked)} action_required ACKED but NOT actioned (a bare ack is "
              f"receipt, not action) --")
        for entry in acked:
            fenced(entry, "acked-awaiting-action")
    print(f"triage: to clear an item, append to YOUR outbox a row with corr_id=<its id> — any "
          f"substantive kind, or kind=ack with payload.disposition in "
          f"{sorted(TERMINAL_DISPOSITIONS)}. Advancing your cursor never clears this list.")
    print(f"== TRIAGE REPORT COMPLETE: {total} item(s), {body_bytes} body bytes. A copy of "
          f"this report missing any END fence or this trailer has been TRUNCATED and has "
          f"lost routed intent. ==")


def _check_routing_intent(bus_root: Path, row: dict) -> None:
    """Fail-closed authoring checks for the structural routing fields."""
    targets = row.get(ROUTING_FIELD)
    if targets:
        roster = _roster_ids(bus_root)
        unknown = sorted({str(t) for t in targets} - roster)
        if unknown:
            raise BusError(
                f"{ROUTING_FIELD} names non-roster id(s) {unknown} — routing intent must be "
                f"resolvable or it is prose in disguise (have: {', '.join(sorted(roster))})")
    if row.get(ACTION_FIELD) and not targets and str(row.get("to") or "*") == "*":
        raise BusError(
            f"{ACTION_FIELD} is set but the message has no concrete addressee (to='*' and "
            f"{ROUTING_FIELD} unset) — intent with no addressee is the 2026-07-29 failure "
            f"shape; name the agent(s) in {ROUTING_FIELD}")


# ------------------------------------------------------------------ commands


def cmd_append(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    row = json.loads(args.json)

    if args.target in {"outbox", "heartbeat"}:
        _require_roster_id(bus_root, args.agent)

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
    if definition == "msg":
        _check_routing_intent(bus_root, row)
        try:
            roster = _roster_ids(bus_root)
        except BusError:
            roster = set()
        for warning in prose_routing_warnings(row, roster):
            print(f"session_bus: WARN {warning}", file=sys.stderr)
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
    warnings: list[str] = []
    checked = 0
    try:
        roster_ids = _roster_ids(bus_root)
    except BusError as exc:
        problems.append(str(exc))
        roster_ids = set()

    # C8: a roster row whose endpoint has no working delivery path is unreachable
    # by BOTH channels — nothing pushes to it, and tmux_adapter refuses to nudge a
    # non-tmux endpoint — so assigned work accumulates unread and rots silently.
    # Observed 2026-07-28: a task-assign to an idle `monitor:file` agent sat
    # undelivered at unread=1. Surface it; never let it be silent.
    try:
        cfg_path = bus_root / "config.yaml"
        import yaml  # lazy: keeps the rest of the CLI dependency-free
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        for entry in (cfg.get("roster") or []):
            if not isinstance(entry, dict):
                continue
            aid = str(entry.get("id", "")).strip()
            ep = str(entry.get("endpoint") or "")
            if not aid or ep.startswith("tmux:"):
                continue
            try:
                pending, _ = _read_jsonl(bus_root / "inbox" / f"{aid}.jsonl",
                                         _cursor_get(bus_root, aid))
                unread = len(pending)
            except Exception:  # noqa: BLE001
                unread = "unknown"
            warnings.append(
                f"roster/{aid}: endpoint {ep!r} has no push delivery and cannot be "
                f"nudged (not a tmux endpoint) — assigned work can rot unread "
                f"(currently {unread}). Re-point it at a tmux window or give "
                f"{ep!r} a real push mechanism.")
    except Exception as exc:  # noqa: BLE001 - never let the lint itself fail closed
        warnings.append(f"roster endpoint check skipped: {exc}")

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
            if area == "outbox" and path.stem not in roster_ids:
                warnings.append(f"outbox/{path.name}: non-roster writer file is ignored; preserved "
                                "pending operator disposition")
            expected = required_writer(bus_root, path)
            rows, _ = _read_jsonl(path)
            for i, row in enumerate(rows, 1):
                checked += 1
                try:
                    validate_row(bus_root, row, "msg")
                except BusError as e:
                    problems.append(f"{area}/{path.name}:{i}: {e}")
                # Routing-intent-in-prose lint (2026-07-29) — authoring side only
                # (outbox), so one logical message warns once, not once per relay
                # copy. The exact shape that lost two routed messages today.
                if area == "outbox":
                    for w in prose_routing_warnings(row, roster_ids):
                        warnings.append(f"{area}/{path.name}:{i} ({row.get('id')}): {w}")
                # Single-writer lint: every row in an outbox must be FROM its owner.
                if area == "outbox" and row.get("from") != expected:
                    problems.append(
                        f"{area}/{path.name}:{i}: single-writer violation — from="
                        f"{row.get('from')!r} but this file's only writer is {expected!r}"
                    )

    for path in sorted((bus_root / "heartbeats").glob("*.json")):
        if path.stem not in roster_ids and path.stem != COORDINATOR_DAEMON:
            warnings.append(f"heartbeats/{path.name}: non-roster writer file is ignored; preserved "
                            "pending operator disposition")
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

    # R7: the trust-boundary list is hash-pinned. The PreToolUse hook stops the
    # ordinary edit path, but a direct shell write bypasses hooks entirely — so
    # the pin is the layer that still catches it, after the fact.
    problems.extend(check_trust_boundary_pin(bus_root))
    checked += 1

    print(f"checked {checked} record(s)")
    for warning in warnings:
        print(f"  WARN {warning}")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        return 1
    print("  OK — schema clean, single-writer clean, trust-boundary pin intact")
    return 0


def check_trust_boundary_pin(bus_root: Path) -> list[str]:
    """Compare human_only_paths.yaml against its recorded sha256.

    Returns a list of problem strings (empty when intact). A missing pair is
    reported, not ignored: an absent gate list means nothing is enforced, which
    is worse than a drifted one because it looks like nothing is wrong.
    """
    gate = bus_root / "human_only_paths.yaml"
    pin = bus_root / "human_only_paths.sha256"
    if not gate.exists() and not pin.exists():
        return ["trust boundary: human_only_paths.yaml and its .sha256 pin are both absent — "
                "nothing is enforced"]
    if not gate.exists():
        return ["trust boundary: pin exists but human_only_paths.yaml is missing"]
    if not pin.exists():
        return ["trust boundary: human_only_paths.yaml exists but its .sha256 pin is missing — "
                "drift would be undetectable"]
    import hashlib

    actual = hashlib.sha256(gate.read_bytes()).hexdigest()
    expected = pin.read_text(encoding="utf-8").split()[0].strip() if pin.read_text().strip() else ""
    if actual != expected:
        return [f"trust boundary DRIFT: human_only_paths.yaml is {actual[:16]}… but the pin says "
                f"{expected[:16] or '(empty)'}… — the gate list changed outside the operator path. "
                f"Re-pin deliberately or revert."]
    return []


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
    current = _cursor_get(bus_root, args.agent)
    if args.set < current:
        raise BusError(f"cursor[{args.agent}] cannot rewind from {current} to {args.set}; "
                       "BUS_PROTOCOL rule 4 permits only equal or advancing offsets")
    _write_atomic(path, {"agent": args.agent, "offset": int(args.set), "ts": _utcnow_iso()})
    print(f"cursor[{args.agent}] = {args.set}")
    return 0


def cmd_drain(args: argparse.Namespace) -> int:
    """Print this agent's inbox past its cursor and advance. The one-liner
    agents run at every task boundary."""
    bus_root = Path(args.bus_root)
    inbox = bus_root / "inbox" / f"{args.agent}.jsonl"

    # C3: fail CLOSED on an unprovisioned route. _read_jsonl returns empty for a
    # missing file, which made "never provisioned" indistinguishable from "nothing
    # new" — the coordinator-agent drained clean for a whole session while messages
    # addressed to it were being dropped (defect C1, 2026-07-28). A missing inbox is
    # a bootstrap error, never a quiet no-op.
    if not inbox.exists():
        print(f"session_bus: no inbox for '{args.agent}' at {inbox} — route not "
              f"provisioned. Every roster member needs 4 files (inbox/outbox/"
              f"heartbeat/cursor); run `session_bus.py provision --agent {args.agent}`.",
              file=sys.stderr)
        # The triage view is delivery-independent (outbox scan), so it still
        # works — and matters MOST — when the inbox route is broken.
        if getattr(args, "triage", False):
            print_triage(bus_root, args.agent)
        return 2

    start = _cursor_get(bus_root, args.agent)
    rows, end = _read_jsonl(inbox, start)

    if rows:
        for row in rows:
            print(json.dumps(row, sort_keys=True))
        if not args.peek:
            _write_atomic(_cursor_path(bus_root, args.agent),
                          {"agent": args.agent, "offset": end, "ts": _utcnow_iso()})
        print(f"-- {len(rows)} message(s); cursor {start} -> {end}"
              f"{' (peek: not advanced)' if args.peek else ''}", file=sys.stderr)
    else:
        print(f"(no new messages for {args.agent})")
    if getattr(args, "triage", False):
        print_triage(bus_root, args.agent)
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    """The routing standing queue. Never reads or writes cursors: a routed
    message cannot be consumed by draining — only a corr_id disposition from the
    target's own outbox clears it."""
    print_triage(Path(args.bus_root), args.agent)
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


def cmd_rebuild(args: argparse.Namespace) -> int:
    """R7 reconstructibility — everything a fresh coordinator-agent needs, from files alone.

    `BUS_PROTOCOL.md` rule 9 asserts that coordinator-agent state must be
    rebuildable from bus files, and that authority living only in a session's
    context is a design defect. An assertion nobody can run is not a guarantee,
    so this verb IS the check: if a fresh session can act correctly from this
    output, the invariant holds. If something it needs is missing here, that
    absence is the defect.
    """
    bus_root = Path(args.bus_root)
    latest = fold_queue(bus_root)
    roster_ids = _roster_ids(bus_root)

    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return ""

    token_text = _read(bus_root / "tokens" / "token-queue.md")
    state = {
        "rebuilt_at": _utcnow_iso(),
        "source": "bus files only — no session context consulted",
        "queue": {
            "count": len(latest),
            "by_status": {s: sum(1 for r in latest.values() if r.get("status") == s)
                          for s in sorted({r.get("status", "?") for r in latest.values()})},
            "live": {tid: r for tid, r in sorted(latest.items())
                     if r.get("status") not in TERMINAL_STATES},
        },
        "pending_operator_tokens": [
            line.strip() for line in token_text.splitlines() if line.lstrip().startswith("- [ ]")
        ],
        "granted_operator_tokens": [
            line.strip() for line in token_text.splitlines() if line.lstrip().startswith("- [x]")
        ],
        "agents": {},
        "trust_boundary": {
            "pin_problems": check_trust_boundary_pin(bus_root),
            "gate_list": "human_only_paths.yaml (human-amendment-only, hash-pinned)",
        },
    }
    for aid in sorted(roster_ids):
        hb_path = bus_root / "heartbeats" / f"{aid}.json"
        try:
            hb = json.loads(hb_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            hb = {"error": "unreadable"}
        unread, _ = _read_jsonl(bus_root / "inbox" / f"{aid}.jsonl", _cursor_get(bus_root, aid))
        state["agents"][aid] = {"heartbeat": hb, "cursor": _cursor_get(bus_root, aid),
                                "inbox_unread": len(unread)}

    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True, default=str))
        return 0
    print(f"rebuilt from bus files at {state['rebuilt_at']}")
    print(f"  queue: {state['queue']['count']} rows, {state['queue']['by_status']}")
    print(f"  live (non-terminal): {list(state['queue']['live']) or '(none)'}")
    print(f"  operator tokens: {len(state['pending_operator_tokens'])} pending, "
          f"{len(state['granted_operator_tokens'])} granted")
    for aid, a in state["agents"].items():
        hb = a["heartbeat"]
        print(f"  {aid:<20} state={hb.get('state')} task={hb.get('task_id')} "
              f"cursor={a['cursor']} unread={a['inbox_unread']}")
    probs = state["trust_boundary"]["pin_problems"]
    print(f"  trust boundary: {'intact' if not probs else probs}")
    return 0


def cmd_provision(args: argparse.Namespace) -> int:
    """Create the 4 files a roster member needs. Idempotent.

    config.yaml states 'adding a main = 1 roster row + 4 files (inbox/outbox/
    heartbeat/cursor)', but nothing enforced it: coordinator-agent was added as a
    roster row with only 3 of the 4 and its inbound route silently did not exist
    (defect C1, 2026-07-28). This makes the documented step executable.
    """
    bus_root = Path(args.bus_root)
    agent = args.agent

    try:
        import yaml  # lazy: keeps the rest of the CLI dependency-free
        cfg = yaml.safe_load((bus_root / "config.yaml").read_text()) or {}
        roster = [r.get("id") for r in (cfg.get("roster") or []) if isinstance(r, dict)]
    except Exception as exc:  # noqa: BLE001 - config is advisory here
        print(f"session_bus: could not read roster ({exc}); provisioning anyway",
              file=sys.stderr)
        roster = []

    if roster and agent not in roster:
        print(f"session_bus: '{agent}' is not a roster id in config.yaml "
              f"(have: {', '.join(roster)}). Add the roster row first.", file=sys.stderr)
        return 2

    created, existed = [], []
    for rel in (f"inbox/{agent}.jsonl", f"outbox/{agent}.jsonl"):
        path = bus_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existed.append(rel)
        else:
            path.touch()
            created.append(rel)

    cursor = _cursor_path(bus_root, agent)
    if cursor.exists():
        existed.append(f"cursors/{agent}.json")
    else:
        _write_atomic(cursor, {"agent": agent, "offset": 0, "ts": _utcnow_iso()})
        created.append(f"cursors/{agent}.json")

    hb = bus_root / "heartbeats" / f"{agent}.json"
    if hb.exists():
        existed.append(f"heartbeats/{agent}.json")
    else:
        hb.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(hb, {"agent": agent, "state": "idle", "ts": _utcnow_iso()})
        created.append(f"heartbeats/{agent}.json")

    for rel in created:
        print(f"created  {rel}")
    for rel in existed:
        print(f"exists   {rel}")
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
    dp.add_argument("--triage", action="store_true",
                    help="also print the routing standing queue (cursor-independent, in full)")
    dp.set_defaults(func=cmd_drain)

    tp = sub.add_parser("triage", help="standing queue of messages routed to you "
                                       "(needs_routing_to / action_required); cursor-independent, "
                                       "printed in full, cleared only by corr_id disposition")
    tp.add_argument("--agent", required=True)
    tp.set_defaults(func=cmd_triage)

    pp = sub.add_parser("provision", help="create the 4 files a roster member needs (idempotent)")
    pp.add_argument("--agent", required=True)
    pp.set_defaults(func=cmd_provision)

    sp = sub.add_parser("status", help="human summary of bus state")
    sp.set_defaults(func=cmd_status)

    rb = sub.add_parser("rebuild", help="derive full coordinator state from bus files alone (R7)")
    rb.add_argument("--json", action="store_true")
    rb.set_defaults(func=cmd_rebuild)
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

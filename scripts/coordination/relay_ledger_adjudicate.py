#!/usr/bin/env python3
"""relay_ledger_adjudicate.py — adjudicate the daemon's flagged relay ledger.

WHY THIS EXISTS (handoffs/active/loop-owned-fleet-implementation.md, wrap-up
findings 2026-08-16): `relay_state.json` carries `flagged` entries — the
daemon's dedupe ledger for defect advisories — that have never been reconciled.
Nothing distinguishes "the handler consumed it" from "it was dropped", and the
2026-08-12 "reconcile before restart" window is long past. The handoff's
disposition: ONE PASS over the flagged entries against the handler ledgers,
then either clear the list or file what it proves lost.

WHAT A FLAGGED ENTRY MEANS (from session_bus_coordinator.py, the ONLY writer):

    flagged: [(msg_id, handler), ...]

The `handler` is the value of the advisory row's `unreachable` field and is one
of exactly three shapes:

  * "schema-invalid"           — the outbox row failed schema validation and was
                                 NOT relayed; a defect was surfaced to its author
                                 (C34). The row stays in the sender's outbox,
                                 forever invalid unless the author repairs it.
  * "handler:<name>"           — the message's kind has a handler-of-record that
                                 runs at an authority this daemon is not at; the
                                 message WAS relayed to its addressees and a
                                 defect advisory was emitted (C27/C34-C38).
  * a roster id (e.g. "auditor") — the message routes to that recipient, which
                                 is either unreachable (NOT a roster id / retired
                                 — NOT delivered to it) or LOOKS DEAD (delivered
                                 to the inbox, nothing draining it) (C18).

So "flagged" never means "dropped" by itself; each shape has a different
delivery truth. This script classifies every entry by reading the BUS FILES
(the durable evidence), not the advisory rows' prose:

  * HANDLED              — a follow-up disposition exists: some outbox row
                           references the message by `corr_id` / `corr_ids`
                           (the original id OR any relayed-copy id) with a
                           substantive kind (not a bare ack). The protocol's
                           own definition of "cleared" (BUS_PROTOCOL.md →
                           Routing intent is structural, not prose).
  * DELIVERED-NOT-DRAINED — the message is present in at least one inbox
                           (delivered), but no disposition exists.
  * DROPPED               — the message is ABSENT from every surface (sender
                           outbox, all inboxes, advisory.jsonl, archive/).
                           A candidate drop: the drop mechanism the wrap-up
                           triage corroborated (NOT-IN-INBOX markers).
  * SCHEMA-INVALID        — the flag's handler is "schema-invalid".
  * UNKNOWN               — present in the sender's outbox / advisory but with
                           no delivery evidence and no disposition.

Per the handoff disposition, `--apply-clear` writes a NEW relay_state.json
keeping only the entries that must stay flagged (handled ones are cleared; the
report files what is proven lost as a defect row). The `delivered` map is
preserved verbatim — it is the daemon's delivery idempotency ledger and the
clear operation must not lose it.

SAFETY. Idempotent and read-only over the bus in report mode. The apply mode
refuses to run while a coordinator-daemon is alive (a live daemon rewrites
relay_state.json every tick; writing under it would race and be lost). It also
refuses if the ledger on disk differs from the one read at report time, so a
concurrent rewrite cannot be silently overwritten.

Run:
    python3 scripts/coordination/relay_ledger_adjudicate.py \
        --bus-root coordination/session-bus \
        --report data/relay_ledger_adjudication_2026-08-23.json
    python3 scripts/coordination/relay_ledger_adjudicate.py --apply-clear
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination.session_bus import DEFAULT_BUS_ROOT, _read_jsonl  # noqa: E402

REPORT_SCHEMA = "session_bus.relay_ledger_adjudication.v1"

# The shapes a flagged entry's handler can take, derived from the daemon code.
HANDLER_SCHEMA_INVALID = "schema-invalid"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _daemon_running() -> bool:
    """Is a coordinator-daemon alive? It rewrites relay_state.json every tick."""
    try:
        proc = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return True  # cannot prove absence: refuse to write
    return "session_bus_coordinator" in proc.stdout


def _load_relay_state(bus_root: Path) -> dict:
    path = bus_root / "relay_state.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    flagged = [(str(a), str(b)) for a, b in raw.get("flagged", [])]
    delivered = {str(a): set(map(str, v)) for a, v in raw.get("delivered", {}).items()}
    return {"schema_version": raw.get("schema_version"),
            "ts": raw.get("ts"), "flagged": flagged, "delivered": delivered}


class BusSurfaces:
    """One index over every message-bearing bus file (read-only)."""

    def __init__(self, bus_root: Path):
        self.bus_root = bus_root
        self.inbox_rows: list[dict] = []
        self.outbox_rows: list[dict] = []
        self.advisory_rows: list[dict] = []
        self.archive_rows: list[dict] = []
        # id -> row, relayed copy id -> original id
        self.id_to_row: dict[str, dict] = {}
        self.relayed_copy_to_src: dict[str, str] = {}
        self._scan()

    def _scan(self) -> None:
        for f in sorted((self.bus_root / "inbox").glob("*.jsonl")):
            rows, _ = _read_jsonl(f)
            self.inbox_rows.extend(rows)
        for f in sorted((self.bus_root / "outbox").glob("*.jsonl")):
            rows, _ = _read_jsonl(f)
            self.outbox_rows.extend(rows)
        for f in sorted((self.bus_root).glob("advisory*.jsonl")):
            rows, _ = _read_jsonl(f)
            self.advisory_rows.extend(rows)
        archive = self.bus_root / "archive"
        if archive.is_dir():
            for f in sorted(archive.rglob("*.jsonl")):
                rows, _ = _read_jsonl(f)
                self.archive_rows.extend(rows)
        for row in self.inbox_rows + self.outbox_rows + self.archive_rows:
            mid = row.get("id")
            if mid:
                self.id_to_row[mid] = row
            rsrc = row.get("relayed_src")
            if mid and rsrc:
                self.relayed_copy_to_src[mid] = rsrc

    def surfaces_of(self, msg_id: str) -> dict[str, list[dict]]:
        """Every surface where this message (id or relayed_src) appears."""
        out = {"inbox": [], "outbox": [], "advisory": [], "archive": []}
        for row in self.inbox_rows:
            if row.get("id") == msg_id or row.get("relayed_src") == msg_id:
                out["inbox"].append(row)
        for row in self.outbox_rows:
            if row.get("id") == msg_id:
                out["outbox"].append(row)
        for row in self.advisory_rows:
            if row.get("relayed_src") == msg_id:
                out["advisory"].append(row)
        for row in self.archive_rows:
            if row.get("id") == msg_id or row.get("relayed_src") == msg_id:
                out["archive"].append(row)
        return out

    def dispositions_of(self, msg_id: str) -> list[dict]:
        """Follow-up dispositions referencing the message by corr_id.

        A disposition may reference the ORIGINAL id (sender's row) or any
        RELAYED COPY id (the copy the recipient actually saw). Both are one
        logical message per BUS_PROTOCOL. A substantive disposition is any
        kind other than a bare `ack`, or an `ack` carrying
        `payload.disposition` in the protocol's approved set.
        """
        approved = {"done", "declined", "handed-off", "superseded"}
        matches: list[dict] = []
        for row in self.outbox_rows:
            refs = []
            if row.get("corr_id"):
                refs.append(str(row["corr_id"]))
            refs.extend(str(c) for c in (row.get("corr_ids") or []))
            if not refs:
                continue
            for ref in refs:
                orig = self.relayed_copy_to_src.get(ref, ref)
                if orig != msg_id:
                    continue
                payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
                substantive = (
                    row.get("kind") != "ack"
                    or payload.get("disposition") in approved
                )
                matches.append({
                    "row_id": row.get("id"),
                    "from": row.get("from"),
                    "kind": row.get("kind"),
                    "ts": row.get("ts"),
                    "corr_id": ref,
                    "substantive": substantive,
                })
        return matches


def classify(entry: tuple[str, str], surfaces: BusSurfaces) -> dict:
    """Classify ONE flagged [msg_id, handler] pair."""
    msg_id, handler = entry
    surfaces_of = surfaces.surfaces_of(msg_id)
    present_anywhere = any(surfaces_of[k] for k in ("inbox", "outbox", "advisory", "archive"))
    dispositions = surfaces.dispositions_of(msg_id)
    substantive = [d for d in dispositions if d["substantive"]]

    if handler == HANDLER_SCHEMA_INVALID:
        cls = "schema-invalid"
        reason = ("flag handler is 'schema-invalid': the outbox row failed schema "
                  "validation and was NOT relayed (C34); a defect was surfaced to "
                  "its author")
        # The flag exists to keep the daemon from re-reporting the same invalid
        # row every tick. If the author REPAIRED the row (it now validates), the
        # premise is gone and the flag is stale — clearing is safe because the
        # daemon's next pass validates the row and never re-flags it.
        clearable = _schema_invalid_resolved(surfaces.bus_root, surfaces_of["outbox"])
        if clearable:
            reason += "; source row is absent or now validates — flag premise resolved"
        return {
            "msg_id": msg_id, "handler": handler, "class": cls,
            "clearable": clearable, "reason": reason,
            "surfaces": {k: len(v) for k, v in surfaces_of.items() if v},
            "dispositions": dispositions,
        }
    if substantive:
        cls = "handled"
        reason = (f"follow-up disposition exists ({len(substantive)} substantive: "
                  + ", ".join(f"{d['kind']}@{d['from']}" for d in substantive[:3])
                  + (", ..." if len(substantive) > 3 else "") + ")")
    elif surfaces_of["inbox"]:
        cls = "delivered-not-drained"
        inboxes = {str(r.get("_deliver_to") or r.get("to")) for r in surfaces_of["inbox"]}
        reason = (f"delivered to inbox(es) {sorted(inboxes)}; no disposition exists — "
                  "nothing drained it")
    elif not present_anywhere:
        cls = "dropped"
        reason = ("message ABSENT from every surface (sender outbox, inboxes, "
                  "advisory.jsonl, archive) — candidate drop")
    else:
        cls = "unknown"
        reason = ("present in the sender outbox / advisory but no delivery evidence "
                  "and no disposition found")

    return {
        "msg_id": msg_id,
        "handler": handler,
        "class": cls,
        "clearable": cls == "handled",
        "reason": reason,
        "surfaces": {k: len(v) for k, v in surfaces_of.items() if v},
        "dispositions": dispositions,
    }


def _schema_invalid_resolved(bus_root: Path, outbox_rows: list[dict]) -> bool:
    """Was the schema-invalid row repaired (absent from the outbox, or valid now)?"""
    if not outbox_rows:
        return True  # the row is gone; the daemon cannot re-flag it
    try:
        from scripts.coordination.session_bus import validate_row  # noqa: PLC0415
        for row in outbox_rows:
            try:
                validate_row(bus_root, row, "msg")
            except Exception:  # noqa: BLE001 — still invalid
                return False
        return True
    except Exception:  # noqa: BLE001 — validator unavailable: fail conservatively
        return False


def adjudicate(bus_root: Path) -> dict:
    state = _load_relay_state(bus_root)
    surfaces = BusSurfaces(bus_root)
    entries = [classify((m, h), surfaces) for m, h in state["flagged"]]
    counts: dict[str, int] = {}
    for e in entries:
        counts[e["class"]] = counts.get(e["class"], 0) + 1
    return {
        "schema_version": REPORT_SCHEMA,
        "generated_ts": _utcnow_iso(),
        "bus_root": str(bus_root),
        "relay_state_ts": state["ts"],
        "flagged_total": len(entries),
        "counts": counts,
        "clearable_count": sum(1 for e in entries if e["clearable"]),
        "entries": entries,
        "defect_rows": [e for e in entries if e["class"] == "dropped"],
    }


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, report)


def _write_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def summarize(report: dict) -> str:
    counts = report["counts"]
    lines = [
        f"Relay-ledger adjudication — {report['generated_ts']}",
        f"  bus root:      {report['bus_root']}",
        f"  ledger ts:     {report['relay_state_ts']}",
        f"  flagged:       {report['flagged_total']}",
        f"  handled:       {counts.get('handled', 0)}  (clearable)",
        f"  delivered-n-d: {counts.get('delivered-not-drained', 0)}",
        f"  dropped:       {counts.get('dropped', 0)}  (filed as defect rows)",
        f"  schema-inval:  {counts.get('schema-invalid', 0)}",
        f"  unknown:       {counts.get('unknown', 0)}",
        f"  clearable:     {report['clearable_count']}",
    ]
    if report["defect_rows"]:
        lines.append("  PROVEN-LOST (defect rows filed):")
        for e in report["defect_rows"]:
            lines.append(f"    {e['msg_id']} [{e['handler']}]")
    return "\n".join(lines)


def apply_clear(bus_root: Path, report: dict, backup_name: str) -> dict:
    """Write a NEW relay_state.json keeping only entries that must stay flagged.

    Refuses while a daemon is alive, and refuses if the on-disk ledger changed
    since the report was generated (a rewrite would be lost or would clobber a
    concurrent writer).
    """
    if _daemon_running():
        raise RuntimeError(
            "coordinator-daemon is RUNNING — relay_state.json is rewritten every "
            "tick and the clear would race it. Quiesce the daemon first.")
    state = _load_relay_state(bus_root)
    if state["ts"] != report.get("relay_state_ts"):
        raise RuntimeError(
            f"ledger on disk (ts {state['ts']}) differs from the adjudicated one "
            f"(ts {report.get('relay_state_ts')}) — re-run report mode first")
    keep = [[m, h] for m, h in state["flagged"] if not _is_clearable(report, m, h)]
    src = bus_root / "relay_state.json"
    bak = bus_root / backup_name
    if not bak.exists():
        shutil.copy2(src, bak)
    payload = {
        "schema_version": state["schema_version"],
        "ts": _utcnow_iso(),
        "delivered": {a: sorted(v) for a, v in state["delivered"].items()},
        "flagged": sorted(keep),
    }
    _write_atomic(src, payload)
    return {"backup": str(bak), "before": len(state["flagged"]), "after": len(keep),
            "cleared": len(state["flagged"]) - len(keep)}


def _is_clearable(report: dict, msg_id: str, handler: str) -> bool:
    for e in report["entries"]:
        if e["msg_id"] == msg_id and e["handler"] == handler:
            return e["clearable"]
    return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="relay_ledger_adjudicate.py",
                                description=__doc__.split("\n")[0])
    p.add_argument("--bus-root", default=str(DEFAULT_BUS_ROOT),
                   help="session-bus root (default: the canonical bus)")
    p.add_argument("--report", default="data/relay_ledger_adjudication_2026-08-23.json",
                   help="machine-readable report output path")
    p.add_argument("--backup-name", default="relay_state.json.bak-2026-08-23",
                   help="backup file name written beside relay_state.json on apply")
    p.add_argument("--apply-clear", action="store_true",
                   help="write a NEW relay_state.json keeping only entries that "
                        "must stay flagged (handled entries are cleared)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bus_root = Path(args.bus_root)
    report = adjudicate(bus_root)
    write_report(report, Path(args.report))
    print(summarize(report))
    if args.apply_clear:
        try:
            result = apply_clear(bus_root, report, args.backup_name)
        except RuntimeError as exc:
            print(f"apply-clear REFUSED: {exc}", file=sys.stderr)
            return 3
        print(f"applied: {result['before']} flagged -> {result['after']} "
              f"(cleared {result['cleared']}); backup at {result['backup']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

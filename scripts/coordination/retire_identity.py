#!/usr/bin/env python3
"""retire_identity.py — tombstone a roster identity that will not come back.

P3-1 (Loop-Owned Fleet). Retiring a main is not deleting a row, and it is not
leaving one lying around either. Both of those have already gone wrong here:

  * DELETING the row orphans everything keyed on the identity — its queue rows,
    cursor, inbox, outbox and triage corr_ids — and the roster comments say so.
  * LEAVING it as a "re-usable slot" is how a revived identity inherited its
    dead predecessor's `working` heartbeat and was unreachable from birth
    (C24), and how a rename re-flooded freshly recreated inboxes with the whole
    relay history (C28).

So a retirement is a TOMBSTONE: the history stays attached to the name, the
name stays readable, and nothing may be newly ADDRESSED to it. Reviving one is
a deliberate act with its own procedure, not a side effect of writing the id in
a message.

THE STEPS ARE ORDERED AND EACH IS VERIFIED, because the ordering is what makes
it safe:

  1. LIVENESS — refuse to retire an identity that might still be alive. Same
     three-signal, two-sample read as ghost_sweep; UNKNOWN refuses.
  2. UNREAD — count what the session never drained. This is not a blocker but
     it MUST be reported: unread messages at retirement are work that was
     routed to somebody who never read it, and quietly discarding them is the
     C33 unread-sink failure in a new costume.
  3. RECEIPT — write a final wrap receipt naming the state at retirement, so a
     later reader can tell an orderly retirement from an abandonment.
  4. ARCHIVE — move the cursor aside so a revived identity cannot silently
     resume from a stale offset.
  5. TOMBSTONE — flip the roster row to `role: retired` with a dated marker.

The roster edit is printed, not applied: config.yaml is policy, and this tool
refuses to rewrite policy behind the operator's back.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghost_sweep as GS  # noqa: E402
from session_bus import get_bus_root  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def unread_bytes(bus_root: Path, agent: str) -> tuple[int, int]:
    inbox = bus_root / "inbox" / f"{agent}.jsonl"
    cursor = bus_root / "cursors" / f"{agent}.json"
    size = inbox.stat().st_size if inbox.exists() else 0
    off = 0
    if cursor.exists():
        try:
            off = int(json.loads(cursor.read_text(encoding="utf-8")).get("offset", 0))
        except (OSError, ValueError, json.JSONDecodeError):
            off = 0
    return max(0, size - off), size


def retire(bus_root: Path, agent: str, signed_by: str, apply: bool) -> int:
    roster = GS.load_roster(bus_root)
    if agent not in roster:
        print(f"REFUSED: {agent} is not a roster id", file=sys.stderr)
        return 2

    s1 = GS.sample_owner(bus_root, agent, roster)
    s2 = GS.sample_owner(bus_root, agent, roster)
    verdict, why = GS.judge_owner(s1, s2)
    print(f"1. LIVENESS  {agent}: {verdict} — {why}")
    if verdict != "DEAD":
        print(f"REFUSED: only a verifiably DEAD identity may be retired "
              f"(this one reads {verdict}). UNKNOWN is not dead.", file=sys.stderr)
        return 3

    unread, size = unread_bytes(bus_root, agent)
    print(f"2. UNREAD    {unread} bytes never drained (inbox {size} bytes)")
    if unread:
        print("             ^ these were routed to a session that never read them.")
        print("               They are preserved in the inbox and named in the receipt;")
        print("               retiring does not delete them, and it does not deliver them.")

    receipt = {
        "schema_version": "session_bus.retirement.v1",
        "agent": agent,
        "retired_ts": _now_iso(),
        "signed_by": signed_by,
        "liveness_verdict": verdict,
        "liveness_evidence": why,
        "unread_bytes_at_retirement": unread,
        "inbox_bytes": size,
        "rule": ("tombstone, not a re-usable slot: history stays attached to the name, "
                 "nothing may be newly addressed to it (P3-1; origin C24, C28)"),
        "revival": ("deliberate act only — restore the archived cursor, verify no stale "
                    "heartbeat, and flip the roster row back with a dated note"),
    }
    receipts_dir = bus_root / "retirements"
    cursor = bus_root / "cursors" / f"{agent}.json"
    archived_cursor = receipts_dir / f"{agent}.cursor.archived.json"

    if not apply:
        print(f"3. RECEIPT   would write {receipts_dir / (agent + '.retirement.json')}")
        print(f"4. ARCHIVE   would move {cursor} -> {archived_cursor}")
        print(f"5. TOMBSTONE roster edit for '{agent}' printed below (never auto-applied)")
        print_roster_edit(agent)
        print("\nDRY RUN — nothing changed. Re-run with --apply --signed-by <operator>.")
        return 0

    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / f"{agent}.retirement.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"3. RECEIPT   wrote {receipts_dir / (agent + '.retirement.json')}")

    if cursor.exists():
        shutil.move(str(cursor), str(archived_cursor))
        print(f"4. ARCHIVE   cursor -> {archived_cursor}")
    else:
        print("4. ARCHIVE   no cursor to archive")

    print("5. TOMBSTONE roster edit below — apply it by hand (config.yaml is policy):")
    print_roster_edit(agent)
    return 0


def print_roster_edit(agent: str) -> None:
    print(f"""
    # RETIRED {datetime.now(timezone.utc).date()} (P3-1). TOMBSTONE, NOT A RE-USABLE SLOT.
    # The identity keeps its history; nothing may be newly addressed to it. Reviving it
    # is a deliberate act with its own procedure (see coordination/session-bus/
    # retirements/{agent}.retirement.json), never a side effect of writing the id
    # into a message — that is how C24 (inherited dead heartbeat) and C28 (relay
    # re-flood into a recreated inbox) happened.
    - {{id: {agent}, role: retired, lanes: [], endpoint: "retired:{agent}", drain: none}}
""")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("agents", nargs="+", help="roster ids to retire")
    ap.add_argument("--bus-root", default=str(get_bus_root()))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--signed-by", default="")
    args = ap.parse_args()
    if args.apply and not args.signed_by:
        print("REFUSED: --apply requires --signed-by", file=sys.stderr)
        return 2
    rc = 0
    for agent in args.agents:
        print(f"\n===== {agent} =====")
        rc |= retire(Path(args.bus_root), agent, args.signed_by, args.apply)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

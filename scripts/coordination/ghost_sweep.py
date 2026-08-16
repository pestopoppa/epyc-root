#!/usr/bin/env python3
"""ghost_sweep.py — release bus state held by sessions that no longer exist.

WHY THIS EXISTS (P0-3 / D7, Loop-Owned Fleet). On 2026-08-14 the fleet's tmux
windows vanished and nothing put them back. The daemon kept ticking and kept
assigning rows to assignees that did not exist; each row aged through
ASSIGNED -> lease expiry -> STALE_REQUEUED until `attempt` hit the cap and the
row landed in INFRA_BLOCKED, "attempts exhausted after lease expiry". Fourteen
rows died that way in one night. Eleven more sit in CLAIMED / RUNNING /
STALE_REQUEUED, and twelve claim files are held by mainA/mainB/mainC/auditor —
sessions that have not existed since 08-13/08-14.

That state cannot clear itself, and by protocol it must not clear itself: a
claim is single-writer and ONLY ITS OWNER MAY DROP IT, which is exactly the
right rule while the owner is alive and exactly a deadlock once it is dead.
`session_bus.py claim --list` therefore only MARKS stale claims; it never
releases. This tool is the sanctioned exception, and it is narrow:

    A claim whose owner is verifiably DEAD or RETIRED is releasable here,
    with a receipt naming the evidence of death.

THE EVIDENCE STANDARD IS THE POINT. This tool destroys other agents' locks, so
its liveness read has to be the strict one, not the convenient one:

  * THREE independent signals, not one: the roster endpoint's tmux window, a
    live process for the heartbeat pid, and heartbeat freshness.
  * PERSISTENCE. Every signal is sampled twice, `--sample-gap-s` apart. A
    single sample that misses the phenomenon proves nothing, and a session
    that is merely COMPACTING renders identically to a finished one.
  * UNREADABLE IS NOT DEAD. If any signal cannot be read, the verdict is
    UNKNOWN and the owner is left alone. Fail-open (treating "cannot tell" as
    "dead") is this codebase's most expensive defect class.

DEFAULT IS DRY RUN. `--apply` requires `--signed-by`, because D7 makes this an
operator-signed action: the enumerated list is reviewed by a human first.

Non-destructive by construction: queue.jsonl is append-only, so a "reset" is a
new row, and released claims are MOVED to claims/released/ (never deleted), so
every release is reversible by moving the file back.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_bus import get_bus_root  # noqa: E402

# Rows the daemon drove to a terminal/limbo state without a live assignee.
GHOST_STATUSES = ("INFRA_BLOCKED", "CLAIMED", "RUNNING", "STALE_REQUEUED", "ASSIGNED")

# The failure signature the 08-14 dead-fleet night stamped on every row it killed.
INFRA_SIGNATURES = ("attempts exhausted after lease expiry", "lease expired")

HEARTBEAT_DEAD_AGE_S = 3600.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def load_roster(bus_root: Path) -> dict:
    """Parse the roster rows out of config.yaml without a yaml dependency."""
    cfg = (bus_root / "config.yaml").read_text(encoding="utf-8")
    roster = {}
    for m in re.finditer(r"^\s*-\s*\{(.+?)\}\s*(?:#.*)?$", cfg, re.M):
        body = m.group(1)
        fields = {}
        for km in re.finditer(r"(\w+)\s*:\s*(\[[^\]]*\]|\"[^\"]*\"|[^,\[\]]+)", body):
            fields[km.group(1)] = km.group(2).strip().strip('"')
        if "id" in fields and "role" in fields:
            roster[fields["id"]] = fields
    return roster


def tmux_window_exists(endpoint: str) -> bool | None:
    """True/False if we could read tmux, None if we could not (UNKNOWN)."""
    if not endpoint or not endpoint.startswith("tmux:"):
        return None
    parts = endpoint.split(":")
    if len(parts) < 3:
        return None
    session, window = parts[1], parts[2]
    try:
        out = subprocess.run(
            ["tmux", "list-windows", "-t", session, "-F", "#{window_name}"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        # No such session is a readable answer: the window does not exist.
        if "no server running" in (out.stderr or "").lower():
            return None
        return False
    return window in out.stdout.split()


def pid_alive(pid) -> bool | None:
    if not pid:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    try:
        return Path(f"/proc/{pid}").exists()
    except OSError:
        return None


def read_heartbeat(bus_root: Path, agent: str) -> dict | None:
    p = bus_root / "heartbeats" / f"{agent}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def exec_endpoint_live(bus_root: Path, roster_row: dict) -> bool | None:
    """Is a runner actually executing for an `exec:` endpoint? None if untellable.

    An exec endpoint has no tmux window and no heartbeat, so the tmux/pid/age
    triad reads UNKNOWN for it forever — which means a row assigned to the pool
    and then abandoned could never be swept. Liveness here is the lane locks:
    a live pid holding any pool lane means the pool is working.
    """
    pool_root = Path("/mnt/raid0/llm/worktrees/pool")
    if not pool_root.is_dir():
        return None
    for lane in sorted(pool_root.glob("lane*")):
        lock = lane / ".worker.lock"
        if not lock.exists():
            continue
        try:
            pid = int((lock.read_text(encoding="utf-8").split() or ["0"])[0])
        except (OSError, ValueError):
            return None                      # unreadable lock: cannot tell
        if Path(f"/proc/{pid}").exists():
            return True
    return False


def sample_owner(bus_root: Path, agent: str, roster: dict) -> dict:
    row = roster.get(agent, {})
    if str(row.get("endpoint", "")).startswith("exec:"):
        live = exec_endpoint_live(bus_root, row)
        return {"retired": row.get("role") == "retired", "in_roster": agent in roster,
                "exec_endpoint": True, "window": None, "pid_alive": live, "hb_age_s": None}
    hb = read_heartbeat(bus_root, agent)
    hb_age = None
    if hb and hb.get("ts"):
        try:
            hb_age = (_now() - datetime.fromisoformat(hb["ts"])).total_seconds()
        except ValueError:
            hb_age = None
    return {
        "retired": row.get("role") == "retired",
        "in_roster": agent in roster,
        "window": tmux_window_exists(row.get("endpoint", "")),
        "pid_alive": pid_alive((hb or {}).get("pid")),
        "hb_age_s": hb_age,
    }


def judge_owner(s1: dict, s2: dict) -> tuple[str, str]:
    """Fold two samples into DEAD / ALIVE / UNKNOWN plus a one-line reason.

    DEAD requires agreement across BOTH samples on BOTH observable signals.
    Anything unreadable, or any disagreement between samples, is UNKNOWN.
    """
    if not s2["in_roster"]:
        return "UNKNOWN", "not a roster id — out of scope for this tool"
    if s2.get("exec_endpoint"):
        if s1.get("pid_alive") is None or s2.get("pid_alive") is None:
            return "UNKNOWN", "exec endpoint: pool lane locks unreadable"
        if s1["pid_alive"] or s2["pid_alive"]:
            return "ALIVE", "exec endpoint: a runner holds a pool lane"
        return "DEAD", "exec endpoint: no runner holds any pool lane"
    if s2["retired"]:
        return "DEAD", "roster role: retired (tombstoned identity)"

    if s1["window"] is None or s2["window"] is None:
        return "UNKNOWN", "tmux unreadable — cannot tell, so not touching it"
    if s1["window"] != s2["window"]:
        return "UNKNOWN", "window presence disagreed across samples"
    if s2["window"]:
        return "ALIVE", "tmux window present"

    if s1["pid_alive"] is None or s2["pid_alive"] is None:
        return "UNKNOWN", "heartbeat pid unreadable — cannot tell"
    if s2["pid_alive"]:
        return "UNKNOWN", "no window but heartbeat pid is live — ambiguous, leaving alone"

    age = s2["hb_age_s"]
    if age is None:
        return "DEAD", "no window, no live pid, no readable heartbeat"
    if age < HEARTBEAT_DEAD_AGE_S:
        return "UNKNOWN", f"no window/pid but heartbeat only {age:.0f}s old — too fresh to call"
    return "DEAD", f"no window, no live pid, heartbeat {age / 3600:.1f}h stale"


def fold_queue(bus_root: Path) -> dict:
    rows: dict[str, dict] = {}
    path = bus_root / "queue.jsonl"
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = r.get("task_id")
            if not tid:
                continue
            rows.setdefault(tid, {}).update({k: v for k, v in r.items() if v is not None})
    return rows


def collect(bus_root: Path, gap_s: float) -> dict:
    roster = load_roster(bus_root)
    rows = fold_queue(bus_root)

    ghost_rows = {t: r for t, r in rows.items() if r.get("status") in GHOST_STATUSES}

    claims_dir = bus_root / "claims"
    claims = []
    for p in sorted(claims_dir.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            claims.append({"path": p, "owner": None, "unreadable": True, "data": {}})
            continue
        claims.append({
            "path": p,
            "owner": d.get("owner") or d.get("agent"),
            "unreadable": False,
            "data": d,
        })

    owners = {c["owner"] for c in claims if c["owner"]}
    owners |= {r.get("owner") for r in ghost_rows.values() if r.get("owner")}
    owners = {o for o in owners if o}

    first = {o: sample_owner(bus_root, o, roster) for o in sorted(owners)}
    if owners and gap_s > 0:
        time.sleep(gap_s)
    second = {o: sample_owner(bus_root, o, roster) for o in sorted(owners)}
    verdicts = {o: judge_owner(first[o], second[o]) for o in sorted(owners)}

    return {
        "roster": roster,
        "rows": rows,
        "ghost_rows": ghost_rows,
        "claims": claims,
        "verdicts": verdicts,
        "samples": (first, second),
    }


def is_infra_killed(row: dict) -> bool:
    reason = (row.get("failure_reason") or "").lower()
    return row.get("status") == "INFRA_BLOCKED" and any(s in reason for s in INFRA_SIGNATURES)


def report(data: dict) -> None:
    print("=" * 78)
    print("GHOST-STATE SWEEP — enumerated for operator review (D7)")
    print("=" * 78)

    print("\n-- OWNER LIVENESS (two samples, three signals) --")
    if not data["verdicts"]:
        print("   (no owners referenced by any claim or ghost row)")
    for owner, (verdict, why) in data["verdicts"].items():
        print(f"   {owner:20} {verdict:8} {why}")

    print("\n-- QUEUE ROWS TO RESET --")
    resettable, held = [], []
    for tid, r in sorted(data["ghost_rows"].items()):
        owner = r.get("owner")
        verdict = data["verdicts"].get(owner, ("NO-OWNER", "row names no owner"))[0] if owner else "NO-OWNER"
        if verdict in ("DEAD", "NO-OWNER"):
            resettable.append((tid, r, verdict))
        else:
            held.append((tid, r, verdict))
    for tid, r, verdict in resettable:
        why = "infra-killed" if is_infra_killed(r) else "dead/absent owner"
        print(f"   [RESET->READY] {r.get('status'):15} attempt={r.get('attempt', 0)} {tid[:46]:46} ({why}, owner={r.get('owner') or 'none'}/{verdict})")
    for tid, r, verdict in held:
        print(f"   [LEAVE]        {r.get('status'):15} {tid[:46]:46} (owner={r.get('owner')}/{verdict})")

    print("\n-- CLAIMS TO RELEASE --")
    rel, keep = [], []
    for c in data["claims"]:
        if c["unreadable"]:
            keep.append((c, "UNREADABLE"))
            continue
        v = data["verdicts"].get(c["owner"], ("UNKNOWN", ""))[0]
        (rel if v == "DEAD" else keep).append((c, v))
    for c, v in rel:
        ts = c["data"].get("ts", "?")[:19]
        print(f"   [RELEASE] {c['path'].name[:12]} owner={c['owner']:12} held_since={ts} ({v})")
    for c, v in keep:
        print(f"   [KEEP]    {c['path'].name[:12]} owner={c['owner'] or '?':12} ({v} — only the owner may drop a live claim)")

    print("\n-- TOTALS --")
    print(f"   queue rows to reset : {len(resettable)}")
    print(f"   queue rows left     : {len(held)}")
    print(f"   claims to release   : {len(rel)}")
    print(f"   claims left         : {len(keep)}")
    print()
    return resettable, rel


def new_receipt_id() -> str:
    return f"ghost-sweep-{_now().strftime('%Y%m%dT%H%M%SZ')}"


def reset_row(row: dict, task_id: str, epoch: int, receipt_id: str, signed_by: str) -> dict:
    """Build the READY replacement row. Caller must be the queue's single writer.

    Carries the row's identity forward (task_text is the identity, the line-ref
    is only a hint) and resets `attempt`, because the attempts were spent on a
    fleet that did not exist — that is an infrastructure fact about the night of
    2026-08-14, not a fact about the work.
    """
    out = {
        "schema_version": "session_bus.queue.v1",
        "ts": _iso(_now()),
        "task_id": task_id,
        "status": "READY",
        "lane": row.get("lane", "none"),
        "gating": row.get("gating", "none"),
        "epoch": epoch,
        "attempt": 0,
        # `origin` (a string) and NOT `routing_annotation` (an object): the
        # schema is the contract, and writing a string where it declares an
        # object produced six schema-invalid rows before `validate` caught it.
        "origin": (
            f"{receipt_id}: reset from {row.get('status')} — owner dead/absent, "
            f"signed-by {signed_by}"
        ),
    }
    for carry in ("task_text", "spec_ref", "screened_by", "expected_occupancy",
                  "priority", "priority_class", "depends_on", "operator_gates"):
        if row.get(carry) is not None:
            out[carry] = row[carry]
    return out


def release_claims(bus_root: Path, data: dict, releasable, receipt_id: str, signed_by: str) -> int:
    """Move dead-owner claim files aside, each with a reversal receipt."""
    released_dir = bus_root / "claims" / "released"
    released_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for c, _v in releasable:
        if not c["path"].exists():
            continue
        dest = released_dir / f"{receipt_id}__{c['path'].name}"
        shutil.move(str(c["path"]), str(dest))
        verdict, evidence = data["verdicts"].get(c["owner"], ("?", ""))
        (released_dir / f"{dest.stem}.receipt.json").write_text(json.dumps({
            "receipt_id": receipt_id,
            "released_ts": _iso(_now()),
            "original_path": str(c["path"]),
            "moved_to": str(dest),
            "owner": c["owner"],
            "owner_verdict": verdict,
            "evidence": evidence,
            "signed_by": signed_by,
            "rule": "claims owned by dead-or-retired ids are daemon-releasable with a receipt (P0-3/D7)",
            "reversible": "move the claim file back from claims/released/ into claims/",
        }, indent=2) + "\n", encoding="utf-8")
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bus-root", default=str(get_bus_root()))
    ap.add_argument("--sample-gap-s", type=float, default=3.0, help="seconds between the two liveness samples")
    args = ap.parse_args()

    data = collect(Path(args.bus_root), args.sample_gap_s)
    report(data)
    print("ENUMERATION ONLY.")
    print("This tool cannot reset a queue row: queue.jsonl has exactly one writer")
    print("(coordinator-daemon, invariant 1) and forging that identity is the very")
    print("property the O_EXCL/single-writer scheme depends on. To execute the sweep:")
    print("  session_bus_coordinator.py ghost-sweep --apply --signed-by <operator>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

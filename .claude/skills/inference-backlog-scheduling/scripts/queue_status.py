#!/usr/bin/env python3
"""queue_status.py -- read-only COMPLETE / RUNNING / BOOKED / ARMED-UNBOOKED / BACKLOG overview.

Classifies every row of the shared compute queue (FILLERS.md) from three read-only sources:
the table itself, the grants dir (<id>.grant / .ended / .complete) and the live grant writers
(compute-flags/grant-*.pid whose process is alive; the matching .sh is scanned for step ids).

    queue_status.py [--flags DIR] [--validator PATH] [--owner SUBSTR] [--json]

Buckets (first match wins):
    COMPLETE        status COMPLETE/CANCELLED, or grants/<id>.complete exists
    RUNNING         grants/<id>.grant exists (the window as written; the launcher may still be polling)
    BOOKED          named as a step in a LIVE writer script, not yet granted
    ARMED-UNBOOKED  status ARMED, ready=y, launcher pid alive -> placeable now
    STALE-ARMED     status ARMED but the launcher pid is dead or missing (the validator refuses it)
    BACKLOG         everything else; prints blocker=<kind> from notes

Zero compute, stdlib only, never writes. Reuses parse_table()/launcher_pid()/proc_pid_alive() from
scripts/coordination/validate_fillers.py (root repo) so the row schema has one owner.
Exit 0; 3 when the table cannot be parsed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone

DEFAULT_FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
VALIDATOR_CANDIDATES = (
    "/workspace/scripts/coordination/validate_fillers.py",
    os.path.join(DEFAULT_FLAGS, "validate_fillers.py"),
)
STEP_RE = re.compile(r"\bstep\s+([A-Za-z0-9][\w.-]*)\s")
QUOTED_STEP_RE = re.compile(r'"([A-Za-z0-9][\w.-]*)\s+(?:\d+|ROW)\s+\d+\s+\d+\s+\d+"')
ID_EQ_RE = re.compile(r"\bID=([A-Za-z0-9][\w.-]*)")
GRANT_OK_RE = re.compile(r"grant_ok\.sh\s+([A-Za-z0-9][\w.-]*)\s")
GRANT_FILE_RE = re.compile(r"/([A-Za-z0-9][\w.-]*)\.grant\b")
GRANT_RE = re.compile(r"regions=(\S+)\s+start=(\S+)\s+end=(\S+)")
BLOCKER_RE = re.compile(r"blocker\s*[=:]\s*([^;|]+)", re.I)


def load_validator(path: str | None):
    for p in ([path] if path else VALIDATOR_CANDIDATES):
        if p and os.path.exists(p):
            spec = importlib.util.spec_from_file_location("validate_fillers", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod
    sys.exit("validate_fillers.py not found (pass --validator)")


def pid_alive(pid: int) -> bool:
    return os.path.exists(f"/proc/{pid}")


def live_writers(flags: str) -> dict[str, set[str]]:
    """{writer-name: {ids it can grant}} for every grant-*.pid whose process is alive."""
    out: dict[str, set[str]] = {}
    for fn in sorted(os.listdir(flags)):
        if not (fn.startswith("grant-") and fn.endswith(".pid")):
            continue
        try:
            pid = int(open(os.path.join(flags, fn)).read().strip())
        except (OSError, ValueError):
            continue
        if not pid_alive(pid):
            continue
        base = fn[:-4]
        # the .pid is written by whichever version is live; find the newest .sh that writes this .pid
        cands = [f for f in os.listdir(flags)
                 if f.startswith(base) and f.endswith(".sh")]
        ids: set[str] = set()
        for sh in cands:
            try:
                txt = open(os.path.join(flags, sh)).read()
            except OSError:
                continue
            if f"{base}.pid" not in txt:
                continue
            for rx in (STEP_RE, QUOTED_STEP_RE, ID_EQ_RE, GRANT_OK_RE, GRANT_FILE_RE):
                ids |= {i for i in rx.findall(txt) if i not in ("id", "ID", "*")}
        out[f"{base} pid={pid}"] = ids
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--validator")
    ap.add_argument("--owner", help="substring filter on the owner column")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    vf = load_validator(a.validator)
    flags, grants = a.flags, os.path.join(a.flags, "grants")
    try:
        col, rows, _ = vf.parse_table(open(os.path.join(flags, "FILLERS.md")).read())
    except (OSError, vf.Malformed) as e:
        print(f"MALFORMED: {e}", file=sys.stderr)
        return 3
    writers = live_writers(flags)
    booked_by: dict[str, str] = {}
    for w, ids in writers.items():
        for i in ids:
            booked_by.setdefault(i, w)
    now = datetime.now(timezone.utc)
    buckets: dict[str, list[dict]] = {k: [] for k in
                                      ("COMPLETE", "RUNNING", "BOOKED", "ARMED-UNBOOKED", "STALE-ARMED", "BACKLOG")}
    for _, cells in rows:
        g = lambda n: cells[col[n]]  # noqa: E731
        rid, owner = g("filler-id"), g("owner")
        if a.owner and a.owner.lower() not in owner.lower():
            continue
        status = (g("status").split() or [""])[0]
        rec = {"id": rid, "owner": owner.split("(")[0].strip()[:40], "status": status,
               "resources": g("resources")[:60], "min_window": g("min window"), "ram_gib": g("max private ram"),
               "class": g("class")}
        gpath, cpath = os.path.join(grants, rid + ".grant"), os.path.join(grants, rid + ".complete")
        if status in vf.TERMINAL or os.path.exists(cpath):
            epath = os.path.join(grants, rid + ".ended")
            if os.path.exists(epath):
                rec["ended"] = open(epath).read().strip()[:80]
            buckets["COMPLETE"].append(rec)
            continue
        if os.path.exists(gpath):
            m = GRANT_RE.search(open(gpath).read())
            if m:
                rec.update(regions=m.group(1), start=m.group(2), end=m.group(3))
                try:
                    end = datetime.strptime(m.group(3), "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    rec["ends_in_min"] = round((end - now).total_seconds() / 60)
                except ValueError:
                    pass
            buckets["RUNNING"].append(rec)
            continue
        if rid in booked_by:
            rec["writer"] = booked_by[rid]
            buckets["BOOKED"].append(rec)
            continue
        pid = vf.launcher_pid(cells, col)
        alive = pid is not None and vf.proc_pid_alive(pid, [rid, f"{rid}.grant"])
        if status == "ARMED" and g("ready y/n").strip() == "y" and alive:
            rec["pid"] = pid
            buckets["ARMED-UNBOOKED"].append(rec)
            continue
        if status == "ARMED":
            rec["pid"] = pid
            buckets["STALE-ARMED"].append(rec)
            continue
        m = BLOCKER_RE.search(g("notes"))
        rec["blocker"] = m.group(1).strip()[:90] if m else "(none stated)"
        buckets["BACKLOG"].append(rec)

    if a.json:
        json.dump({"as_of": now.strftime("%Y-%m-%dT%H:%MZ"), "writers": {k: sorted(v) for k, v in writers.items()},
                   "buckets": buckets}, sys.stdout, indent=1)
        print()
        return 0
    print(f"QUEUE STATUS {now.strftime('%H:%M')}Z {now.date()}  (read-only; {len(rows)} rows; "
          f"{len(writers)} live writers)")
    for name, recs in buckets.items():
        print(f"\n{name} ({len(recs)})")
        for r in sorted(recs, key=lambda r: (r['owner'], r['id'])):
            extra = {
                "COMPLETE": r.get("ended", ""),
                "RUNNING": f"{r.get('regions','?')} {r.get('start','?')}->{r.get('end','?')} ({r.get('ends_in_min','?')} min left)",
                "BOOKED": f"in {r.get('writer')}",
                "ARMED-UNBOOKED": f"{r['resources']} | min {r['min_window']} | {r['ram_gib']} GiB | {r['class']}",
                "STALE-ARMED": f"launcher pid={r.get('pid')} dead/absent -> fix the row",
                "BACKLOG": f"blocker={r.get('blocker')}",
            }[name]
            print(f"  {r['owner']:<22} {r['id']:<40} {extra}")
    print("\nLIVE WRITERS: " + (", ".join(writers) or "none"))
    print("Next: fill IDLE NOW, CRITICAL PATH and the RAM ledger by hand (SKILL.md section 6).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

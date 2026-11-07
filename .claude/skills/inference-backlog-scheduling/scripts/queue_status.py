#!/usr/bin/env python3
"""queue_status.py -- read-only live rowflow overview (ready/ manifests, grants, dryrun states, filing, keeper log).

    queue_status.py [--flags DIR] [--owner SUBSTR] [--json]

Sources (all under compute-flags, FILLERS.md is retired and never read):
    ready/<id>.json (epyc.row.v3; *.withdrawn* names ignored)   grants/<id>.grant|.ended|.complete
    dryrun/<id>/{PASS.json,FAIL-N.json,SMOKE-QUEUED.json,GPU-SMOKE-QUEUED.json,UNPARK.json}
    filing-done/<id>.FILED                                      ws58-calendar-keeper.log (latest SNAPSHOT + IDLE-WHY)

Sections: RUNNING, GRANTABLE/QUEUED, SMOKE-QUEUED/FAILED, PARKED/BLOCKED, IDLE, UNFILED-ENDED (count).
A row that ended/completed is DONE and appears nowhere except the UNFILED-ENDED count (when not yet FILED).
Zero compute, stdlib only, never writes. Exit 0.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

DEFAULT_FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
KEEPER_LOG = "ws58-calendar-keeper.log"
MAX_FAILS = 3
GRANT_RE = re.compile(r"regions=(\S+)\s+start=(\S+)\s+end=(\S+)")
LOG_TAIL_BYTES = 400_000


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _read(path):
    try:
        with open(path, errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _hostutil():
    """scripts/coordination/rowflow/hostutil.py: the ONE measured-utilisation reading (2026-11-03 item 2)."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    d = os.path.join(root, "scripts", "coordination", "rowflow")
    if d not in sys.path:
        sys.path.insert(0, d)
    import hostutil
    return hostutil


def measure_util():
    """Measured per-quarter CPU% + GPU%/VRAM, or None when unavailable (patched in tests)."""
    try:
        return _hostutil().measure()
    except Exception:  # noqa: BLE001 - a status page never fails on its sensor
        return None


def _grant_covers(regions: str, q: str) -> bool:
    """True when a grant's regions string ('0-95', '24-47', 'mi210_0,88-91') covers the whole quarter q."""
    lo = int(q[1]) * 24
    want = set(range(lo, lo + 24))
    have: set[int] = set()
    for t in regions.split(","):
        if "-" in t and t.replace("-", "").isdigit():
            a_, b_ = t.split("-", 1)
            have |= set(range(int(a_), int(b_) + 1))
        elif t.isdigit():
            have.add(int(t))
    return want <= have


def keeper_state(flags):
    """Latest SNAPSHOT line (parsed) and the IDLE-WHY lines stamped with the latest tick."""
    p = os.path.join(flags, KEEPER_LOG)
    try:
        with open(p, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - LOG_TAIL_BYTES))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return {"snapshot": None, "snapshot_at": None, "idle_why": {}}
    snap = at = None
    tail = lines
    for i in range(len(lines) - 1, -1, -1):
        if " SNAPSHOT " in lines[i]:
            snap, at = lines[i], lines[i].split()[0]
            break
    idle = {}
    for ln in tail:
        m = re.match(r"(\S+)\s+IDLE-WHY\s+(\S+?):\s*(.*)", ln)
        if m and (at is None or m.group(1)[:19] >= at[:19]):
            idle[m.group(2)] = m.group(3)
    parsed = {}
    if snap:
        for k in ("free", "busy"):
            m = re.search(rf"\b{k}=(\S*)", snap)
            parsed[k] = [t for t in (m.group(1).split(",") if m else []) if t]
    return {"snapshot": snap, "snapshot_at": at, "parsed": parsed, "idle_why": idle}


def _wants_gpu(m):
    blob = " ".join(str(m.get(k, "")) for k in ("shape", "declared_shape", "lane", "regions"))
    return any(t in blob for t in ("gpu", "mi210"))


def classify(flags, owner=None, now=None):
    now = now or datetime.now(timezone.utc)
    G = os.path.join(flags, "grants")
    out = {k: [] for k in ("RUNNING", "GRANTABLE", "SMOKE-QUEUED", "FAILED", "PARKED", "BLOCKED")}
    keeper = keeper_state(flags)
    busy = keeper.get("parsed", {}).get("busy", [])
    gpu_busy = [b for b in busy if b.startswith("gpu")]
    unfiled = 0
    for mp in sorted(glob.glob(os.path.join(flags, "ready", "*.json"))):
        m = _load(mp)
        if not isinstance(m, dict) or not m.get("id"):
            continue
        rid = m["id"]
        if owner and owner.lower() not in str(m.get("owner", "")).lower():
            continue
        done = os.path.exists(os.path.join(G, rid + ".ended")) or os.path.exists(os.path.join(G, rid + ".complete"))
        if done:
            if not os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
                unfiled += 1
            continue
        rec = {"id": rid, "owner": m.get("owner"), "shape": m.get("shape") or m.get("declared_shape"),
               "rank": m.get("priority_rank"), "regions": m.get("regions"), "handoff_task": m.get("handoff_task")}
        gp = os.path.join(G, rid + ".grant")
        if os.path.exists(gp):
            g = GRANT_RE.search(_read(gp))
            if g:
                rec.update(regions=g.group(1), start=g.group(2), end=g.group(3))
                try:
                    e = datetime.strptime(g.group(3), "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    rec["ends_in_min"] = round((e - now).total_seconds() / 60)
                except ValueError:
                    pass
            out["RUNNING"].append(rec)
            continue
        dd = os.path.join(flags, "dryrun", rid)
        stop = m.get("stop_file")
        if stop and os.path.exists(stop):
            rec["reason"] = f"stop file exists: {stop}"
            out["BLOCKED"].append(rec)
            continue
        fails = sorted(glob.glob(os.path.join(dd, "FAIL-*.json")),
                       key=lambda p: int(re.search(r"FAIL-(\d+)\.json$", p).group(1)))
        passed = os.path.exists(os.path.join(dd, "PASS.json"))
        if passed:
            rec["gpu_wait"] = (f"waiting on GPU ({', '.join(gpu_busy)})" if gpu_busy else None) if _wants_gpu(m) else None
            out["GRANTABLE"].append(rec)
            continue
        queued = next((p for p in (os.path.join(dd, "SMOKE-QUEUED.json"), os.path.join(dd, "GPU-SMOKE-QUEUED.json"))
                       if os.path.exists(p)), None)
        if queued:
            q = _load(queued) or {}
            rec["reason"] = (f"{os.path.basename(queued)} queued_at={q.get('queued_at')}"
                             + (" (waiting on GPU)" if "GPU" in queued else ""))
            out["SMOKE-QUEUED"].append(rec)
            continue
        if fails:
            last = _load(fails[-1]) or {}
            rec["fails"] = len(fails)
            rec["reason"] = str(last.get("reason") or last.get("fix_task") or "(no reason recorded)")[:160]
            unparked = os.path.exists(os.path.join(dd, "UNPARK.json"))
            out["PARKED" if len(fails) >= MAX_FAILS and not unparked else "FAILED"].append(rec)
            continue
        rec["reason"] = "no dry run yet (needs-dryrun)"
        out["SMOKE-QUEUED"].append(rec)
    out["UNFILED-ENDED"] = unfiled
    out["keeper"] = keeper
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--owner", help="substring filter on the owner field")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    r = classify(a.flags, a.owner, now)
    util = measure_util()
    hu = _hostutil() if util else None
    for x in r["RUNNING"]:   # measured beside the grant: a grant file is never reported as work
        if util and x.get("regions"):
            toks = [t for t in ("q0", "q1", "q2", "q3") if _grant_covers(x["regions"], t)]
            if "mi210" in x["regions"] or "gpu" in x["regions"]:
                toks.append("gpu-quiet")
            x["util"] = hu.regions_pct(util, toks)
            idle = hu.idle_regions(util, toks)
            if idle:
                x["idle_held"] = idle
    if a.json:
        # compatible field set: as_of, util, buckets (RUNNING/BACKLOG keys kept; BACKLOG = GRANTABLE for old readers)
        buckets = {"RUNNING": r["RUNNING"], "GRANTABLE": r["GRANTABLE"], "ARMED-UNBOOKED": r["GRANTABLE"],
                   "BACKLOG": r["SMOKE-QUEUED"] + r["FAILED"] + r["PARKED"] + r["BLOCKED"],
                   "SMOKE-QUEUED": r["SMOKE-QUEUED"], "FAILED": r["FAILED"], "PARKED": r["PARKED"],
                   "BLOCKED": r["BLOCKED"]}
        json.dump({"as_of": now.strftime("%Y-%m-%dT%H:%MZ"), "util": util, "buckets": buckets,
                   "idle": r["keeper"]["idle_why"], "snapshot": r["keeper"]["snapshot"],
                   "unfiled_ended": r["UNFILED-ENDED"]}, sys.stdout, indent=1)
        print()
        return 0
    print(f"QUEUE STATUS {now.strftime('%H:%M')}Z {now.date()}  (read-only; rowflow state in {a.flags})")
    print(hu.line(util) if util else "util: unavailable (hostutil could not read /proc/stat or sysfs)")
    ow = lambda x: str(x.get("owner") or "?")[:18]  # noqa: E731
    print(f"\nRUNNING ({len(r['RUNNING'])})")
    for x in sorted(r["RUNNING"], key=lambda x: x["id"]):
        print(f"  {ow(x):<18} {x['id']:<44} {x.get('regions','?')} until {x.get('end','?')} ({x.get('ends_in_min','?')} min left)"
              + (" measured " + " ".join(f"{k}={'?' if v is None else f'{v:.0f}%'}" for k, v in x["util"].items()) if x.get("util") else "")
              + (f" IDLE-HELD {','.join(x['idle_held'])}" if x.get("idle_held") else ""))
    print(f"\nGRANTABLE/QUEUED ({len(r['GRANTABLE'])})  (dry run PASSED, waiting for a keeper placement)")
    for x in sorted(r["GRANTABLE"], key=lambda x: (x.get("rank") is None, x.get("rank") or 0, x["id"])):
        print(f"  {ow(x):<18} {x['id']:<44} shape={x.get('shape')} rank={x.get('rank')}"
              + (f"\n    GPU: {x['gpu_wait']}" if x.get("gpu_wait") else ""))
    for title, key in (("SMOKE-QUEUED", "SMOKE-QUEUED"), ("FAILED", "FAILED")):
        print(f"\n{title} ({len(r[key])})")
        for x in sorted(r[key], key=lambda x: x["id"]):
            print(f"  {ow(x):<18} {x['id']:<44} {x.get('reason','')}")
    print(f"\nPARKED/BLOCKED ({len(r['PARKED']) + len(r['BLOCKED'])})")
    for x in sorted(r["PARKED"] + r["BLOCKED"], key=lambda x: x["id"]):
        print(f"  {ow(x):<18} {x['id']:<44} {x.get('reason','')}")
    k = r["keeper"]
    print(f"\nIDLE (keeper snapshot {k['snapshot_at'] or 'none'})")
    for res, why in sorted(k["idle_why"].items()):
        print(f"  {res:<6} {why}")
    if not k["idle_why"]:
        print("  none reported")
    print(f"\nUNFILED-ENDED: {r['UNFILED-ENDED']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

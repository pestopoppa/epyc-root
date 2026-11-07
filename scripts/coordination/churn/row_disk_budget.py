#!/usr/bin/python3
"""Zero-token disk-budget monitor: for every LIVE grant, how much has the row itself written under its scratch_root
(files modified after the grant file's mtime; older files are inputs) versus its declared budget_gib (default 1 GiB)?
ALERT ONLY: never stops, kills or touches a row. Exit 0 always.

  row_disk_budget.py [--flags DIR] [--factor 1.0] [--grace-gib 2] [--log FILE] [--alert] [--json] [--walk-cap N]
"""
import argparse
import datetime as dt
import glob
import json
import os
import shutil
import sys

FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
DEFAULT_BUDGET_GIB = 1.0
SCHEMA = "rowflow.alert.v1"  # same shape as rowflow/notify.py emit()
DEDUPE_S = 6 * 3600
GIB = float(1 << 30)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(flags, rid):
    for pat in (f"ready/{rid}.json", f"ready/*/{rid}.json"):
        for p in sorted(glob.glob(os.path.join(flags, pat))):
            try:
                with open(p) as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    return d
            except (OSError, ValueError):
                continue
    return None


def live_grants(flags):
    g = os.path.join(flags, "grants")
    out = []
    for p in sorted(glob.glob(os.path.join(g, "*.grant"))):
        rid = os.path.basename(p)[:-len(".grant")]
        if os.path.exists(os.path.join(g, rid + ".ended")) or os.path.exists(os.path.join(g, rid + ".complete")):
            continue
        out.append((rid, p))
    return out


def walk_used(root, since, cap):
    """(bytes written after `since`, hit_cap). lstat only; symlinks are not followed."""
    used, seen = 0, 0
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            if d == root:
                return None, False
            continue
        with it:
            for e in it:
                seen += 1
                if seen > cap:
                    return used, True
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    continue
                if e.is_dir(follow_symlinks=False):
                    stack.append(e.path)
                elif st.st_mtime > since:
                    used += st.st_size
    return used, False


def check_row(flags, rid, grant, factor, grace, cap):
    m = load_manifest(flags, rid) or {}
    b = m.get("budget_gib")
    declared = isinstance(b, (int, float)) and not isinstance(b, bool)
    budget = float(b) if declared else DEFAULT_BUDGET_GIB
    root = m.get("scratch_root")
    r = {"row": rid, "used_gib": 0.0, "budget_gib": budget, "declared": declared, "scratch_root": root or "-"}
    if not root:
        r["verdict"] = "NO-SCRATCH-ROOT"
        return r
    try:
        since = os.stat(grant).st_mtime
    except OSError:
        r["verdict"] = "UNVERIFIABLE"
        return r
    used, capped = walk_used(root, since, cap)
    if used is None or capped:
        r["verdict"] = "UNVERIFIABLE"
        r["used_gib"] = round((used or 0) / GIB, 2)
        return r
    r["used_gib"] = round(used / GIB, 2)
    r["verdict"] = "OVER" if used / GIB > budget * factor + grace else "OK"
    return r


def _load_state(p):
    try:
        with open(p) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def alert(flags, r, free, state, now_ts):
    key = f"{r['row']}:{r['verdict']}"
    if now_ts - float(state.get(key, 0)) < DEDUPE_S:
        return False
    state[key] = now_ts
    if r["verdict"] == "OVER":
        summary = (f"row {r['row']} has written {r['used_gib']} GiB under its scratch_root against a "
                   f"{'declared' if r['declared'] else 'DEFAULT (undeclared)'} budget of {r['budget_gib']} GiB; "
                   "alert only - nothing was stopped or deleted")
    else:
        summary = f"row {r['row']} has no scratch_root in its manifest, so its disk use cannot be budgeted"
    rec = {"schema": SCHEMA, "key": f"disk-budget-{r['row']}-{r['verdict']}-{int(now_ts)}", "ts": _now(),
           "kind": "disk-budget", "severity": "warning", "row_id": r["row"], "row_owner": None, "summary": summary,
           "detail": {"verdict": r["verdict"], "used_gib": r["used_gib"], "budget_gib": r["budget_gib"],
                      "declared": r["declared"], "scratch_root": r["scratch_root"], "free_gib": free}}
    with open(os.path.join(flags, "rowflow-alerts.jsonl"), "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flags", default=os.environ.get("ROWFLOW_FLAGS", FLAGS))
    ap.add_argument("--factor", type=float, default=1.0)
    ap.add_argument("--grace-gib", type=float, default=2.0)
    ap.add_argument("--log")
    ap.add_argument("--alert", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--walk-cap", type=int, default=500000)
    a = ap.parse_args(argv)
    rows = [check_row(a.flags, rid, g, a.factor, a.grace_gib, a.walk_cap) for rid, g in live_grants(a.flags)]
    try:
        free = round(shutil.disk_usage("/mnt/raid0").free / GIB, 1)
    except OSError:
        free = -1
    over = sum(r["verdict"] == "OVER" for r in rows)
    und = sum(not r["declared"] for r in rows)
    lines = [f"BUDGET row={r['row']} used_gib={r['used_gib']} budget_gib={r['budget_gib']} "
             f"declared={str(r['declared']).lower()} verdict={r['verdict']} scratch_root={r['scratch_root']}"
             for r in rows]
    lines.append(f"BUDGET SUMMARY live={len(rows)} over={over} undeclared={und} free_gib={free}")
    if a.alert:
        sp = os.path.join(a.flags, "ws58-keeper-state", "disk-budget.json")
        st = _load_state(sp)
        import time
        now_ts, changed = time.time(), False
        for r in rows:
            if r["verdict"] in ("OVER", "NO-SCRATCH-ROOT"):
                changed |= alert(a.flags, r, free, st, now_ts)
        if changed:
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            tmp = sp + ".tmp"
            with open(tmp, "w") as f:
                json.dump(st, f)
            os.replace(tmp, sp)
    if a.json:
        print(json.dumps({"rows": rows, "live": len(rows), "over": over, "undeclared": und, "free_gib": free}))
    else:
        print("\n".join(lines))
    if a.log:
        with open(a.log, "a") as f:
            f.write("".join(f"{_now()} {l}\n" for l in lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

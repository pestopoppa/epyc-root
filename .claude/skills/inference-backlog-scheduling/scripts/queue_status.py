#!/usr/bin/env python3
"""queue_status.py -- read-only live rowflow overview (ready/ manifests, grants, dryrun states, filing, keeper log).

    queue_status.py [--flags DIR] [--owner SUBSTR] [--json]

Sources (all under compute-flags, FILLERS.md is retired and never read):
    ready/<id>.json (epyc.row.v3; *.withdrawn* names ignored)   grants/<id>.grant|.ended|.complete
    dryrun/<id>/{PASS.json,FAIL-N.json,SMOKE-QUEUED.json,GPU-SMOKE-QUEUED.json,UNPARK.json}
    filing-done/<id>.FILED                                      ws58-calendar-keeper.log (latest SNAPSHOT + IDLE-WHY)

Sections: RUNNING, GRANTABLE/QUEUED, SMOKE-QUEUED, NEEDS-REPUBLISH, FAILED, NOT-A-ROW, PARKED/BLOCKED, IDLE,\nUNFILED-ENDED (count). Row state is rowflow.status()/runnable() - the keeper's own predicate, never re-derived.
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
CAMPAIGN_STATUS_SCHEMA = "epyc.autokernel.campaign_status.v1"   # published by the AK loop (loop/campaign_status.py)
CAMPAIGN_STATUS_STALE_S = 6 * 3600


def campaign_status(flags, now_ts=None):
    """READ-ONLY: <flags>/campaign-status/<row>.json written by the AK loop's publisher.
    A file that is unreadable / wrong schema is listed as bad (never silently dropped); a payload older
    than CAMPAIGN_STATUS_STALE_S is marked stale. Returns {"campaigns": [...], "bad": [...]}."""
    out, bad = [], []
    now_ts = datetime.now(timezone.utc).timestamp() if now_ts is None else now_ts
    for p in sorted(glob.glob(os.path.join(flags, "campaign-status", "*.json"))):
        name = os.path.basename(p)
        try:
            with open(p) as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            bad.append({"file": name, "reason": f"unreadable: {type(e).__name__}"})
            continue
        if not isinstance(d, dict) or d.get("schema") != CAMPAIGN_STATUS_SCHEMA:
            bad.append({"file": name, "reason": "unknown schema"})
            continue
        as_of = d.get("as_of")
        age = now_ts - float(as_of) if isinstance(as_of, (int, float)) and not isinstance(as_of, bool) else None
        out.append({"row_id": d.get("row_id") or name[:-5], "as_of": as_of, "age_s": age,
                    "stale": age is None or age > CAMPAIGN_STATUS_STALE_S,
                    "rows": list(d.get("rows") or []), "idle_bins": list(d.get("idle_bins") or []),
                    "escalations": list(d.get("escalations") or []),
                    "decision_package": d.get("decision_package")})
    return {"campaigns": out, "bad": bad}


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


def _gpu_idle(flags, rid, util):
    """["gpu-quiet"] only when rowflow.gpu_grant_busy() (own KFD clients incl. FILLER_ID env, VRAM, recent row-dir
    writes, device %) calls the grant quiet; any error reads busy (a sample between short server loads is not idle)."""
    try:
        rf = _rowflow()
        g = next((g for g in rf.open_grants(flags) if g["id"] == rid), None)
        if g is None:
            return []
        busy, _ = rf.gpu_grant_busy(flags, g, util, rf.gpu_occupancy())
        return [] if busy else ["gpu-quiet"]
    except Exception:  # noqa: BLE001 - fail closed toward busy
        return []


def _rowflow():
    """scripts/coordination/rowflow/rowflow.py: status()/runnable() are THE keeper predicate; this page never re-derives it."""
    _hostutil()   # puts the rowflow dir on sys.path
    import rowflow
    return rowflow


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


def gpu_smoke_expected_start(flags, rf):
    """When a queued GPU smoke can start: the batch runs once the GPU is free, so = the end of the current GPU grant
    (latest end among open grants holding the MI210); `now` when none holds it."""
    ends = [str(g.get("end")) for g in rf.open_grants(flags) if rf.GPU in (g.get("holds") or ()) and g.get("end")]
    return f"{max(ends)} (end of the current GPU grant)" if ends else "now (GPU free; next keeper tick)"


def classify(flags, owner=None, now=None):
    now = now or datetime.now(timezone.utc)
    G = os.path.join(flags, "grants")
    out = {k: [] for k in ("RUNNING", "GRANTABLE", "SMOKE-QUEUED", "NEEDS-REPUBLISH", "FAILED", "PARKED", "BLOCKED",
                           "NOT-A-ROW")}
    rf = _rowflow()
    allrows = rf.rows(flags)
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
        rec = {"id": rid, "owner": m.get("owner"), "shape": m.get("shape") or m.get("declared_shape"),
               "rank": m.get("priority_rank"), "regions": m.get("regions"), "handoff_task": m.get("handoff_task")}
        gp = os.path.join(G, rid + ".grant")
        if os.path.exists(gp) and rid in allrows:
            g = GRANT_RE.search(_read(gp))
            if g:
                rec.update(regions=g.group(1), start=g.group(2), end=g.group(3))
                try:
                    e = datetime.strptime(g.group(3), "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    rec["ends_in_min"] = round((e - now).total_seconds() / 60)
                except ValueError:
                    pass
        # The keeper's own predicate decides (2026-11-13: this page called PARKED/DONE rows GRANTABLE and un-queued
        # needs-dryrun rows SMOKE-QUEUED while the keeper, rightly, considered none of them -> host idle 10:39Z).
        st = rf.status(flags, rid, allrows) if rid in allrows else None
        state = (st or {}).get("state")
        rec["reason"] = str((st or {}).get("reason") or "")[:160]
        if st is None:
            rec["reason"] = (f"not an {rf.SCHEMA} row (schema={m.get('schema')!r}); the keeper ignores it - "
                             "owner publishes it via rowflow/publish_row.py")
            out["NOT-A-ROW"].append(rec)
        elif state == "done":
            if not os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
                unfiled += 1
        elif state == "running":
            if isinstance(m.get("quiet_guard_regions"), list):
                rec["quiet_guard"] = [t for t in m["quiet_guard_regions"] if isinstance(t, str)]
            out["RUNNING"].append(rec)
        elif rf.runnable(st):
            rec["gpu_wait"] = (f"waiting on GPU ({', '.join(gpu_busy)})" if gpu_busy else None) if _wants_gpu(m) else None
            out["GRANTABLE"].append(rec)
        elif state == "dryrun-running":
            out["SMOKE-QUEUED"].append(rec)
        elif state in ("needs-dryrun", "stale"):
            dd = os.path.join(flags, "dryrun", rid)
            queued = next((p for p in (os.path.join(dd, "SMOKE-QUEUED.json"), os.path.join(dd, "GPU-SMOKE-QUEUED.json"))
                           if os.path.exists(p)), None)
            if queued:
                q = _load(queued) or {}
                rec["reason"] = (f"{os.path.basename(queued)} queued_at={q.get('queued_at')}"
                                 + (" (waiting on GPU)" if "GPU" in queued else ""))
                out["SMOKE-QUEUED"].append(rec)
            else:
                rec["reason"] = (f"{state}, no smoke queued: the keeper never smokes it; owner re-runs "
                                 "publish_row.py <spec.json>")
                out["NEEDS-REPUBLISH"].append(rec)
        elif state == "failed":
            out["FAILED"].append(rec)
        elif state == "stopped":
            out["BLOCKED"].append(rec)
        else:   # parked (arming/launch, precond or lineage) and anything unrunnable
            rec["arm_fails"] = st.get("arm_fails")
            out["PARKED"].append(rec)
    # 2026-11-19: a queued GPU smoke's manifest is dryrun/<id>/unpublished.json (no ready/ file) until its batch runs, so the
    # ready/ walk above never saw it (ak-gap-1-step1-gpu-20261119 vanished from this page). List every GPU-SMOKE-QUEUED marker.
    seen = {x["id"] for k in ("RUNNING", "GRANTABLE", "SMOKE-QUEUED", "NEEDS-REPUBLISH", "FAILED", "PARKED", "BLOCKED",
                              "NOT-A-ROW") for x in out[k]}
    gstart = gpu_smoke_expected_start(flags, rf)
    for qp in sorted(glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json"))):
        rid = os.path.basename(os.path.dirname(qp))
        q = _load(qp) or {}
        m = _load(os.path.join(os.path.dirname(qp), "unpublished.json")) or _load(os.path.join(flags, "ready", rid + ".json")) \
            or q.get("spec") or {}
        if owner and owner.lower() not in str(m.get("owner", "")).lower():
            continue
        rec = next((x for x in out["SMOKE-QUEUED"] if x["id"] == rid), None)
        if rec is None:
            if rid in seen:
                continue
            rec = {"id": rid, "owner": m.get("owner"), "shape": m.get("shape") or m.get("declared_shape"),
                   "rank": m.get("priority_rank"), "regions": q.get("regions"), "handoff_task": m.get("handoff_task")}
            out["SMOKE-QUEUED"].append(rec)
        rec.update(kind="SMOKE-QUEUED (GPU)", queued_at=q.get("queued_at"), wait_attempts=q.get("wait_attempts") or 0,
                   expected_start=gstart,
                   reason=f"SMOKE-QUEUED (GPU) queued_at={q.get('queued_at')} expected start {gstart}"
                          + (f" wait_attempts={q.get('wait_attempts')}" if q.get("wait_attempts") else ""))
    out["UNFILED-ENDED"] = unfiled
    out["keeper"] = keeper
    return out



def _toolroot_banner():
    """F5: print tool-commit / stale-checkout WARN (toolroot.py beside this file when installed, else the checkout's)."""
    try:
        try:
            import toolroot
        except ImportError:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts", "coordination"))
            import toolroot
        toolroot.banner(__file__)
    except Exception:  # noqa: BLE001 - never blocks the tool
        pass


def reservation_view(flags):
    """RESERVATION head (ws58-keeper-state/allocator/reservation.json) + pending CLAIM QUEUE requests (grants/requests/),
    read-only: {"head": {...} | None, "requests": [{id, rank, cpus, minutes, since, position}]}."""
    head = None
    try:
        with open(os.path.join(flags, "ws58-keeper-state", "allocator", "reservation.json")) as f:
            rec = json.load(f)
        if rec.get("id"):
            head = rec
    except (OSError, ValueError):
        pass
    reqs = []
    for p in sorted(glob.glob(os.path.join(flags, "grants", "requests", "req-*.json"))):
        if p.endswith(".result.json") or os.path.exists(p[:-5] + ".result.json"):
            continue
        try:
            with open(p) as f:
                reqs.append(json.load(f))
        except (OSError, ValueError):
            continue
    reqs.sort(key=lambda r: (float(r.get("rank") or 50), float(r.get("requested_at") or 0)))
    out = [{"id": r.get("id"), "rank": r.get("rank"), "cpus": r.get("cpus"), "minutes": r.get("minutes"),
            "since": r.get("requested_iso"), "position": n} for n, r in enumerate(reqs, 1)]
    return {"head": head, "requests": out}


ROWFLOW_REL = "scripts/coordination/rowflow/rowflow.py"


def _git(repo, *args):
    import subprocess  # noqa: PLC0415
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=20)
    return r.stdout if r.returncode == 0 else None


def keeper_stale(flags, repo=None):
    """AK RCA 2026-11-24 item 1 (F8 deploy-parity gate): 'KEEPER-STALE deployed=<sha> head=<sha> (<n> lines differ)' when
    bin/rowflow/DEPLOYED.json's sha predates origin/main's last rowflow.py commit, else None. Local git only (no fetch);
    repo = the clone this script runs from. Unknown (no DEPLOYED.json / no git) is None: this gate never guesses."""
    import difflib  # noqa: PLC0415
    try:
        with open(os.path.join(flags, "bin", "rowflow", "DEPLOYED.json")) as f:
            dep = str(json.load(f).get("sha") or "")
    except (OSError, ValueError, AttributeError):
        return None
    repo = repo or (_git(os.path.dirname(os.path.abspath(__file__)), "rev-parse", "--show-toplevel") or "").strip()
    if not dep or not repo:
        return None
    try:
        head = (_git(repo, "rev-parse", "origin/main") or "").strip()
        last = (_git(repo, "log", "-1", "--format=%H", "origin/main", "--", ROWFLOW_REL) or "").strip()
        if not head or not last:
            return None
        if _git(repo, "merge-base", "--is-ancestor", last, dep) is not None:
            return None   # the deployed sha already contains origin/main's last rowflow.py change
        src = (_git(repo, "show", f"origin/main:{ROWFLOW_REL}") or "").splitlines()
        try:
            with open(os.path.join(flags, "bin", "rowflow", "rowflow.py")) as f:
                live = f.read().splitlines()
        except OSError:
            live = (_git(repo, "show", f"{dep}:{ROWFLOW_REL}") or "").splitlines()
        n = sum(1 for x in difflib.unified_diff(live, src, lineterm="", n=0)
                if x[:1] in "+-" and not x.startswith(("+++", "---")))
    except Exception:  # noqa: BLE001 - read-only status: never crash the report
        return None
    return f"KEEPER-STALE deployed={dep[:9]} head={head[:9]} ({n} lines differ)"


def main(argv=None) -> int:
    _toolroot_banner()
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
            guard = [t for t in (x.get("quiet_guard") or []) if t in toks]
            if guard:
                x["guard"] = guard   # idle on purpose (pre-registered contention guard): GUARD, never IDLE-HELD
            idle = [t for t in idle if t not in guard]
            if "gpu-quiet" in idle and x.get("id"):   # GPU token: the keeper's own predicate, never device % alone
                idle = [t for t in idle if t != "gpu-quiet"] + _gpu_idle(a.flags, x["id"], util)
            if idle:
                x["idle_held"] = idle
    if a.json:
        # compatible field set: as_of, util, buckets (RUNNING/BACKLOG keys kept; BACKLOG = GRANTABLE for old readers)
        buckets = {"RUNNING": r["RUNNING"], "GRANTABLE": r["GRANTABLE"], "ARMED-UNBOOKED": r["GRANTABLE"],
                   "BACKLOG": r["SMOKE-QUEUED"] + r["NEEDS-REPUBLISH"] + r["FAILED"] + r["PARKED"] + r["BLOCKED"],
                   "SMOKE-QUEUED": r["SMOKE-QUEUED"], "NEEDS-REPUBLISH": r["NEEDS-REPUBLISH"],
                   "NOT-A-ROW": r["NOT-A-ROW"], "FAILED": r["FAILED"], "PARKED": r["PARKED"],
                   "BLOCKED": r["BLOCKED"]}
        json.dump({"as_of": now.strftime("%Y-%m-%dT%H:%MZ"), "util": util, "buckets": buckets,
                   "idle": r["keeper"]["idle_why"], "snapshot": r["keeper"]["snapshot"],
                   "unfiled_ended": r["UNFILED-ENDED"],
                   "keeper_stale": keeper_stale(a.flags),
                   "campaign_status": campaign_status(a.flags), "reservation": reservation_view(a.flags)}, sys.stdout, indent=1)
        print()
        return 0
    print(f"QUEUE STATUS {now.strftime('%H:%M')}Z {now.date()}  (read-only; rowflow state in {a.flags})")
    print(hu.line(util) if util else "util: unavailable (hostutil could not read /proc/stat or sysfs)")
    ks = keeper_stale(a.flags)
    if ks:
        print(ks)
    ow = lambda x: str(x.get("owner") or "?")[:18]  # noqa: E731
    print(f"\nRUNNING ({len(r['RUNNING'])})")
    for x in sorted(r["RUNNING"], key=lambda x: x["id"]):
        print(f"  {ow(x):<18} {x['id']:<44} {x.get('regions','?')} until {x.get('end','?')} ({x.get('ends_in_min','?')} min left)"
              + (" measured " + " ".join(f"{k}={'?' if v is None else f'{v:.0f}%'}" for k, v in x["util"].items()) if x.get("util") else "")
              + (f" GUARD {','.join(x['guard'])}" if x.get("guard") else "")
              + (f" IDLE-HELD {','.join(x['idle_held'])}" if x.get("idle_held") else ""))
    print(f"\nGRANTABLE/QUEUED ({len(r['GRANTABLE'])})  (dry run PASSED, waiting for a keeper placement)")
    for x in sorted(r["GRANTABLE"], key=lambda x: (x.get("rank") is None, x.get("rank") or 0, x["id"])):
        print(f"  {ow(x):<18} {x['id']:<44} shape={x.get('shape')} rank={x.get('rank')}"
              + (f"\n    GPU: {x['gpu_wait']}" if x.get("gpu_wait") else ""))
    for title, key in (("SMOKE-QUEUED", "SMOKE-QUEUED"), ("NEEDS-REPUBLISH", "NEEDS-REPUBLISH"), ("FAILED", "FAILED"),
                       ("NOT-A-ROW (keeper ignores)", "NOT-A-ROW")):
        print(f"\n{title} ({len(r[key])})")
        for x in sorted(r[key], key=lambda x: x["id"]):
            print(f"  {ow(x):<18} {x['id']:<44} {x.get('reason','')}")
    print(f"\nPARKED/BLOCKED ({len(r['PARKED']) + len(r['BLOCKED'])})")
    for x in sorted(r["PARKED"] + r["BLOCKED"], key=lambda x: x["id"]):
        print(f"  {ow(x):<18} {x['id']:<44} {x.get('reason','')}")
    rv = reservation_view(a.flags)
    h = rv["head"]
    print(f"\nRESERVATION ({(h or {}).get('mode') or 'none'})")
    if h:
        print(f"  head {h['id']} rank={h.get('rank')} starts by {h.get('T_iso')} needs {','.join(h.get('tokens') or [])[:120]}"
              + (" +host-quiet" if h.get("quiet") else ""))
    for q in rv["requests"]:
        print(f"  claim-request #{q['position']} {q['id']} rank={q['rank']} cpus={q['cpus']} {q['minutes']} min since {q['since']}")
    k = r["keeper"]
    print(f"\nIDLE (keeper snapshot {k['snapshot_at'] or 'none'})")
    for res, why in sorted(k["idle_why"].items()):
        print(f"  {res:<6} {why}")
    if not k["idle_why"]:
        print("  none reported")
    cs = campaign_status(a.flags)
    print(f"\nCAMPAIGN-STATUS ({len(cs['campaigns'])})  (AK loop per-stage state + ETA, published beside the grant)")
    for c in cs["campaigns"]:
        print(f"  {c['row_id']:<44} {'STALE ' if c['stale'] else ''}as_of age {'?' if c['age_s'] is None else int(c['age_s'] // 60)} min")
        for line in c["rows"]:
            print(f"    {line}")
        for b in c["idle_bins"]:
            print(f"    IDLE {b.get('bin')}: {int(b.get('idle_s', 0) // 60)} min, {b.get('reason', '?')}")
        for e in c["escalations"]:
            print(f"    ESCALATION {e.get('id')}: {e.get('decision')}")
        if c["decision_package"]:
            print(f"    DECISION PACKAGE: {len(c['decision_package'].get('items', []))} item(s) -- see the file")
    for b in cs["bad"]:
        print(f"  BAD {b['file']}: {b['reason']}")
    print(f"\nUNFILED-ENDED: {r['UNFILED-ENDED']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

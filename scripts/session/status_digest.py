#!/usr/bin/env python3
"""status_digest.py -- ONE compact operator digest, zero LLM (operator-steering report 2026-11-21, item 4).

Each fixed section answers a question the operator kept typing ("status?", "why is compute idle?", "what is left on
handoff X?", "which command do I run?", "has the champion advanced?"):

  1. Rows per owner -- RUNNING (ETA = grant end), QUEUED (dry run passed, waiting for placement), SMOKE-QUEUED
  2. Idle compute -- each free quarter / GPU with its free streak and the keeper's placement reason (IDLE-WHY)
  3. Finished but unfiled rows (ended/completed grant, no filing-done/<id>.FILED)
  4. Watched handoffs -- open-box count, and the blocker of each open box (.index-state.json + .box-index.json)
  5. Pending operator commands (pending_operator_cmds.py) with the ONE combined command
  6. Champion lineage head (epyc-inference-research data/ak-lineage-*/ledger.json, P4 ledger)
  7. Disk free vs the DISK-PAUSE floor

    status_digest.py [--flags DIR] [--handoff NAME ...] [--json] [--out FILE]

Watched handoffs: --handoff (repeatable), else the names listed one per line in <flags>/operator-watch-handoffs.txt,
else the 6 most recently advanced active handoffs with open boxes. Read-only except --out. Schedule it with cron or
/loop; it never calls a model.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import idle_alarm as IA  # noqa: E402
import pending_operator_cmds as POC  # noqa: E402

DEFAULT_FLAGS = IA.DEFAULT_FLAGS
RESEARCH = os.environ.get("EPYC_RESEARCH_REPO", "/workspace/repos/epyc-inference-research")
WATCH_FILE = "operator-watch-handoffs.txt"
MAX_BOXES = 8


# ---------------------------------------------------------------- collectors (each returns plain data)
def rows_by_owner(q: dict) -> dict:
    b = q.get("buckets") or {}
    out: dict[str, list] = {}
    for kind, key in (("RUNNING", "RUNNING"), ("QUEUED", "GRANTABLE"), ("SMOKE-QUEUED", "SMOKE-QUEUED")):
        for x in b.get(key) or []:
            if kind == "RUNNING":
                eta = f"ends {x.get('end', '?')} ({x.get('ends_in_min', '?')} min)"
            elif kind == "SMOKE-QUEUED":
                eta = f"expected start {x.get('expected_start') or '?'}"
            else:
                eta = f"rank {x.get('rank')}, start when placed"
            out.setdefault(str(x.get("owner") or "?"), []).append(
                {"state": kind, "id": x.get("id"), "shape": x.get("shape"), "eta": eta,
                 "task": x.get("handoff_task")})
    return out


def idle_regions(flags: str, q: dict) -> list[dict]:
    snaps, why, _ = IA.parse_log(IA.read_log(flags))
    out = []
    for r in IA.REGIONS:
        st = IA.free_streak(snaps, r) if snaps else 0
        if st <= 0:
            continue
        reason = (q.get("idle") or {}).get(r) or (why.get(r) or (0, "no IDLE-WHY logged"))[1]
        out.append({"region": r, "free_min": round(st / 60), "reason": str(reason)[:300]})
    return out


def unfiled(flags: str) -> list[dict]:
    out = []
    for mp in sorted(glob.glob(os.path.join(flags, "ready", "*.json"))):
        rid = os.path.basename(mp)[:-5]
        if ".withdrawn" in rid:
            continue
        end = next((p for p in (os.path.join(flags, "grants", rid + s) for s in (".complete", ".ended"))
                    if os.path.exists(p)), None)
        if end and not os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
            try:
                owner = json.load(open(mp)).get("owner")
            except (OSError, ValueError):
                owner = "?"
            ended = datetime.fromtimestamp(os.path.getmtime(end), timezone.utc).strftime("%m-%d %H:%MZ")
            out.append({"id": rid, "owner": owner, "ended": ended})
    return out


def _box_index():
    spec = importlib.util.spec_from_file_location("box_index", os.path.join(ROOT, "scripts/handoffs/box_index.py"))
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(spec.origin))
    spec.loader.exec_module(m)
    return m


def blocker(rec: dict, why: str | None) -> str:
    if why is None:
        return "none: dispatchable now"
    if why == "gate-open":
        return "gate open: " + ", ".join(map(str, rec.get("gate") or []))[:120]
    if why == "held":
        return "operator hold: " + ", ".join(map(str, rec.get("holds") or []))[:120]
    if why == "inputs-missing":
        return "missing input: " + ", ".join(map(str, rec.get("inputs_missing") or []))[:120]
    if why == "lint-fail":
        return "box fails lint: " + ", ".join((rec.get("lint") or {}).get("fails") or [])[:120]
    return why


def watched_handoffs(flags: str, names: list[str] | None, root: str = ROOT, box_doc: dict | None = None) -> list:
    try:
        st = json.load(open(os.path.join(root, "handoffs/active/.index-state.json")))["handoffs"]
    except (OSError, ValueError, KeyError):
        return [{"handoff": "?", "error": "handoffs/active/.index-state.json unreadable"}]
    if not names:
        wf = os.path.join(flags, WATCH_FILE)
        if os.path.exists(wf):
            names = [ln.strip() for ln in open(wf) if ln.strip() and not ln.startswith("#")]
    if not names:
        live = [(v.get("last_advanced") or "", k) for k, v in st.items() if v.get("open")]
        names = [k for _, k in sorted(live, reverse=True)[:6]]
    if box_doc is None:
        try:
            box_doc = _box_index().load(root)
        except Exception as e:   # noqa: BLE001
            box_doc = {"boxes": {}, "stale": True, "stale_reason": str(e)}
    try:
        skip = _box_index().skip_reason
    except Exception:   # noqa: BLE001
        skip = lambda r: None if r.get("state") == "open" else f"state-{r.get('state')}"  # noqa: E731
    boxes = list((box_doc.get("boxes") or {}).values())
    out = []
    for n in names:
        n = n if n.endswith(".md") else n + ".md"
        h = st.get(n)
        if h is None:
            out.append({"handoff": n, "error": "not an active handoff"})
            continue
        mine = [b for b in boxes if os.path.basename(b.get("file", "")) == n and b.get("state") != "done"]
        items = [{"id": b.get("id") or b.get("text_sha"), "line": b.get("line"), "text": (b.get("text") or "")[6:90],
                  "blocker": blocker(b, skip(b))} for b in mine]
        out.append({"handoff": n, "row": h.get("row_id"), "open": h.get("open"), "blocked": h.get("blocked"),
                    "closed": h.get("closed"), "last_advanced": h.get("last_advanced"), "boxes": items,
                    "box_index_stale": bool(box_doc.get("stale"))})
    return out


def lineage(research: str = RESEARCH) -> dict:
    cands = sorted(glob.glob(os.path.join(research, "data", "ak-lineage-*", "ledger.json")))
    src, doc = None, None
    for p in reversed(cands):
        try:
            doc, src = json.load(open(p)), p
            break
        except (OSError, ValueError):
            continue
    if doc is None:   # not checked out here: read the newest ledger from origin/main
        try:
            ls = subprocess.run(["git", "-C", research, "ls-tree", "-r", "--name-only", "origin/main", "data/"],
                                capture_output=True, text=True, timeout=30).stdout.split()
            led = sorted(p for p in ls if p.startswith("data/ak-lineage-") and p.endswith("/ledger.json"))
            if led:
                doc = json.loads(subprocess.run(["git", "-C", research, "show", f"origin/main:{led[-1]}"],
                                                capture_output=True, text=True, timeout=30).stdout)
                src = f"origin/main:{led[-1]}"
        except (subprocess.SubprocessError, ValueError, OSError):
            pass
    if not isinstance(doc, dict):
        return {"error": f"no data/ak-lineage-*/ledger.json under {research}"}
    return {"source": src, "champion": doc.get("champion"), "current_c": doc.get("current_c"),
            "current_fold": doc.get("current_fold"), "next_c": doc.get("next_c"),
            "production": doc.get("production"), "features": len(doc.get("features") or []),
            "do_not_fold": len(doc.get("do_not_fold") or [])}


def disk(flags: str, path: str = "/mnt/raid0") -> dict:
    s = os.statvfs(path)
    free = s.f_bavail * s.f_frsize / 2**30
    cfg, paused = {}, None
    try:
        rp = subprocess.run([sys.executable, os.path.join(flags, "bin/rowflow/diskpause.py"), "status"],
                            capture_output=True, text=True, timeout=30)
        d = json.loads(rp.stdout)
        cfg, paused = d.get("config") or {}, d.get("paused")
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    floor = cfg.get("floor")
    return {"path": path, "free_gib": round(free), "floor_gib": floor, "resume_gib": cfg.get("resume"),
            "headroom_gib": round(free - floor) if floor is not None else None, "paused": paused}


def collect(flags: str, handoffs: list[str] | None = None) -> dict:
    q = IA.queue_json(flags)
    return {"schema": "epyc.status_digest.v1", "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "util": q.get("util"), "rows_by_owner": rows_by_owner(q), "idle": idle_regions(flags, q),
            "unfiled": unfiled(flags), "handoffs": watched_handoffs(flags, handoffs),
            "operator_cmds": POC.entries(), "operator_cmds_combined": POC.combined(),
            "lineage": lineage(), "disk": disk(flags)}


# ---------------------------------------------------------------- render
def render(d: dict) -> str:
    L = [f"# Operator status digest {d['as_of']}", ""]
    L.append("## 1. Rows per owner (RUNNING = holds a grant; QUEUED = dry run passed, waiting for a placement)")
    if not d["rows_by_owner"]:
        L.append("- none")
    for owner, rs in sorted(d["rows_by_owner"].items()):
        L.append(f"- **{owner}** ({len(rs)})")
        L += [f"  - {r['state']} `{r['id']}` [{r['shape']}] {r['eta']}" for r in rs]
    L += ["", "## 2. Idle compute (free quarter/GPU, minutes free, keeper placement reason)"]
    L += [f"- {x['region']} free {x['free_min']} min: {x['reason']}" for x in d["idle"]] or ["- none idle"]
    L += ["", f"## 3. Finished but unfiled ({len(d['unfiled'])})"]
    L += [f"- `{x['id']}` ({x['owner']}) ended {x['ended']}" for x in d["unfiled"][:15]] or ["- none"]
    if len(d["unfiled"]) > 15:
        L.append(f"- +{len(d['unfiled']) - 15} more")
    L += ["", "## 4. Watched handoffs (open boxes and the blocker of each)"]
    for h in d["handoffs"]:
        if h.get("error"):
            L.append(f"- {h['handoff']}: {h['error']}")
            continue
        L.append(f"- **{h['handoff']}** ({h['row']}): {h['open']} open, {h['blocked']} blocked, {h['closed']} closed,"
                 f" last advanced {h['last_advanced']}" + (" (box index stale)" if h["box_index_stale"] else ""))
        tally: dict[str, int] = {}
        for b in h["boxes"]:
            k = b["blocker"].split(":", 1)[0]
            tally[k] = tally.get(k, 0) + 1
        if tally:
            L.append("  - blockers: " + ", ".join(f"{k} x{v}" for k, v in sorted(tally.items(), key=lambda i: -i[1])))
        for b in h["boxes"][:MAX_BOXES]:
            L.append(f"  - `{b['id']}` L{b['line']}: {b['blocker']}")
        if len(h["boxes"]) > MAX_BOXES:
            L.append(f"  - +{len(h['boxes']) - MAX_BOXES} more open boxes")
    L += ["", "## 5. Pending operator commands"]
    es = d["operator_cmds"]
    L += [f"- `{e['id']}` {e.get('kind')} ({e.get('session')}): {e.get('reason')}" for e in es] or ["- none pending"]
    if d["operator_cmds_combined"]:
        L += ["", "```", d["operator_cmds_combined"], "```"]
    lin = d["lineage"]
    L += ["", "## 6. Champion lineage head"]
    if lin.get("error"):
        L.append(f"- {lin['error']}")
    else:
        L.append(f"- champion `{lin['champion']}`, current C{lin['current_c']} fold `{lin['current_fold']}`, "
                 f"next C{lin['next_c']}; {lin['features']} features, {lin['do_not_fold']} do-not-fold "
                 f"(production `{str(lin['production'])[:60]}`; source {lin['source']})")
    k = d["disk"]
    L += ["", "## 7. Disk"]
    L.append(f"- {k['path']} free {k['free_gib']} GiB vs pause floor {k['floor_gib']} GiB "
             f"(headroom {k['headroom_gib']} GiB, resume at {k['resume_gib']} GiB); "
             f"DISK-PAUSE {'ACTIVE' if k['paused'] else 'off'}")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--handoff", action="append")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    d = collect(a.flags, a.handoff)
    text = json.dumps(d, indent=1, default=str) if a.json else render(d)
    if a.out:
        with open(a.out + ".tmp", "w") as fh:
            fh.write(text)
        os.replace(a.out + ".tmp", a.out)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

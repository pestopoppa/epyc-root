#!/usr/bin/env python3
"""flow_status.py -- AK parallel-loop live flow: the data contract behind the /loop flowchart (read-only).

Plane rule (dashboard/README.md): this contract lives WITH the subsystem it observes (akloop); the hub only
renders it. Nothing here writes, routes, publishes or signals; it folds files other writers own:

    candidate spool   /mnt/raid0/llm/tmp/akchain-spool/cand-*.json        (lanes' candidate records, P3)
    rowflow           <flags>/ready/<id>.json, grants/<id>.{grant,ended}, filing-done/<id>.{FILED,verdict.json}
    failclass (P5)    akloop/failclass.classify_result over an ended row's RESULT (pure; routing NOT re-run)
    lineage (P4)      /mnt/raid0/llm/tmp/akchain-lineage/<ts>-composite-<row>/ (ak_runend.lineage_generate)
    decisions (P6)    akloop/decisions.detect(owner) -- the same detector the CLI runs

Rows are AutoKernel-owned manifests (owner == autokernel) published inside the window. A row maps to a chain
stage by chain.STAGES' id patterns; `akc-*` rows are parallel-loop chain rows proper and are flagged `chain`.
The LLM nodes (planner / critic / author) are NOT instrumented per step: lanes report only through candidate
records, so their counts are null with a reason, never a fabricated zero.

    flow_status.py [--flags DIR] [--spool DIR] [--lineage DIR] [--window-h 168] [--json]
Schema: epyc.akloop.flow.v1.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SCHEMA = "epyc.akloop.flow.v1"
FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
SPOOL = "/mnt/raid0/llm/tmp/akchain-spool"
LINEAGE = "/mnt/raid0/llm/tmp/akchain-lineage"
OWNER = "autokernel"
ITEM_CAP = 40
CHAIN_RX = re.compile(r"^akc-(?P<hyp>.+?)(?P<rb>-rb[0-9a-f]{7})?-(?P<stage>build|oracle-kld|ab-timing|fold-check)-\d{8}")
STAGE_NAMES = ("build", "oracle-kld", "ab-timing", "fold-check")

# Node spec: the ONE place the flowchart's topology is declared (the page draws positions, not semantics).
NODES = (
    ("planner", "AI", "planner", "proposes a hypothesis per lane"),
    ("critic", "AI", "critic", "reviews plan and patch (bounded rounds)"),
    ("author", "AI", "author", "writes the patch in the lane worktree"),
    ("candidate", "DET", "candidate record", "spool: base sha, patch sha, hypothesis"),
    ("build", "DET", "build", "CPU quarter q0-q2"),
    ("oracle-kld", "DET", "oracle + KLD", "correctness gate, GPU quiet-only"),
    ("ab-timing", "DET", "A/B timing", "quiet GPU window, 88-95 held"),
    ("fold-check", "DET", "fold check", "C-fold composite step"),
    ("gate_eval", "DET", "gate evaluator", "RESULT -> verdict, no LLM"),
    ("file", "DET", "filed", "verdict filed (filing-done)"),
    ("lineage", "DET", "lineage / fold list", "keep ledger + next composite"),
    ("rebase", "DET", "stale-base recheck", "rebase-and-recheck chain (-rb)"),
    ("failclass", "DET", "failure routing", "harness -> pipeline inbox; candidate -> drop"),
    ("decisions", "DET", "decisions detector", "operator/owner decisions needed"),
)
EDGES = (("planner", "critic"), ("critic", "author"), ("author", "candidate"), ("candidate", "build"),
         ("build", "oracle-kld"), ("oracle-kld", "ab-timing"), ("ab-timing", "fold-check"),
         ("fold-check", "gate_eval"), ("gate_eval", "file"), ("file", "lineage"),
         ("lineage", "rebase"), ("rebase", "build"), ("gate_eval", "failclass"), ("file", "decisions"))


def _load(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _epoch(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _iso(ts):
    return None if ts is None else datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def stage_of(rid: str) -> tuple[str | None, bool, bool]:
    """(stage, is_chain_row, is_rebase) for a row id."""
    m = CHAIN_RX.match(rid)
    if m:
        return m.group("stage"), True, bool(m.group("rb"))
    try:
        import chain as C
        for st in C.STAGES:
            if re.search(st.history, rid):
                return st.name, False, False
    except Exception:  # noqa: BLE001 -- chain import failure degrades to "unmapped", stated in sources
        pass
    return None, False, False


def row_state(flags: str, rid: str) -> tuple[str, float | None]:
    g = os.path.join(flags, "grants", rid)
    fd = os.path.join(flags, "filing-done", rid)
    ended = _mtime(g + ".ended")
    if os.path.exists(fd + ".verdict.json") or os.path.exists(fd + ".FILED"):
        return "filed", _mtime(fd + ".verdict.json") or _mtime(fd + ".FILED")
    if ended is not None:
        return "ended", ended
    if os.path.exists(g + ".grant"):
        return "running", _mtime(g + ".grant")
    return "queued", None


def _verdict(flags: str, rid: str) -> dict | None:
    v = _load(os.path.join(flags, "filing-done", rid + ".verdict.json"))
    if not isinstance(v, dict):
        return None
    return {"answer": str(v.get("answer") or "")[:120], "row_verdict": v.get("row_verdict"),
            "outcome_class": v.get("outcome_class"), "filed_at": v.get("filed_at") or v.get("at")}


def _failclass(man: dict) -> dict | None:
    try:
        import failclass as FC
    except Exception as e:  # noqa: BLE001
        return {"side": "unknown", "klass": "classifier_unavailable", "rule": type(e).__name__}
    res = _load(str(man.get("result_path") or "")) if man.get("result_path") else None
    if res is None:
        return {"side": "harness", "klass": "result_contract", "rule": "result:missing"}
    try:
        c = FC.classify_result(res, None)
        return {"side": c.side, "klass": c.klass, "rule": c.rule}
    except Exception as e:  # noqa: BLE001
        return {"side": "unknown", "klass": "classifier_error", "rule": type(e).__name__}


def _node(owner, label, sub):
    return {"owner": owner, "label": label, "sub": sub, "count": 0, "in_flight": 0, "queued": 0,
            "done": 0, "last_event": None, "age_s": None, "state": "idle", "note": None, "items": []}


def _touch(n, ts):
    if ts is not None and (n["last_event"] is None or ts > _epoch(n["last_event"])):
        n["last_event"] = _iso(ts)


def _item(n, it):
    n["count"] += 1
    if len(n["items"]) < ITEM_CAP:
        n["items"].append(it)


def build(flags: str = FLAGS, spool: str = SPOOL, lineage: str = LINEAGE, now: float | None = None,
          window_h: float = 168.0, detect=None) -> dict:
    now = time.time() if now is None else now
    lo = now - window_h * 3600
    nodes = {nid: _node(o, lab, sub) for nid, o, lab, sub in NODES}
    sources: dict = {}

    for nid in ("planner", "critic", "author"):
        nodes[nid]["count"] = None
        nodes[nid]["state"] = "uninstrumented"
        nodes[nid]["note"] = "lanes report only through candidate records; no per-step signal"

    # candidate spool
    cands = sorted(glob.glob(os.path.join(spool, "cand-*.json")))
    sources["spool"] = {"path": spool, "present": os.path.isdir(spool), "files": len(cands)}
    lanes = {}
    for p in cands:
        c = _load(p) or {}
        ts = _epoch(c.get("emitted_at")) or _mtime(p)
        if ts is not None and ts < lo:
            continue
        n = nodes["rebase" if c.get("rebase_of") else "candidate"]
        _item(n, {"id": c.get("id") or os.path.basename(p)[:-5], "state": "emitted", "at": _iso(ts),
                  "detail": f"{c.get('hypothesis_id', '?')} · {str(c.get('patch_sha', ''))[:9]} on "
                            f"{str(c.get('base_sha', ''))[:9]} · lane {c.get('lane', '?')}"})
        n["done"] += 1
        _touch(n, ts)
        if c.get("lane"):
            lanes[c["lane"]] = max(lanes.get(c["lane"], 0), ts or 0)
            _touch(nodes["author"], ts)
    if lanes:
        nodes["author"]["note"] = (f"{len(lanes)} lane(s) emitted in window: "
                                   + ", ".join(sorted(lanes)) + " (inferred from candidate records)")

    # rowflow: AK-owned manifests in window
    ready = os.path.join(flags, "ready")
    sources["rowflow"] = {"path": flags, "present": os.path.isdir(ready)}
    rows, other = [], {"running": 0, "queued": 0, "ended": 0, "filed": 0}
    for p in glob.glob(os.path.join(ready, "*.json")):
        pm = _mtime(p)
        if pm is not None and pm < lo:
            continue
        m = _load(p)
        if not isinstance(m, dict) or m.get("owner") != OWNER or not m.get("id"):
            continue
        pub = _epoch(m.get("published_at")) or pm
        if pub is not None and pub < lo:
            continue
        rid = m["id"]
        st, ts = row_state(flags, rid)
        stage, is_chain, is_rb = stage_of(rid)
        rows.append({"id": rid, "stage": stage, "chain": is_chain, "rebase": is_rb, "state": st,
                     "at": _iso(ts or pub), "_ts": ts or pub, "_man": m})
    rows.sort(key=lambda r: -(r["_ts"] or 0))
    for r in rows:
        if r["stage"] is None:
            other[r["state"]] += 1
            continue
        n = nodes[r["stage"]]
        key = {"running": "in_flight", "queued": "queued"}.get(r["state"], "done")
        n[key] += 1
        _touch(n, r["_ts"])
        _item(n, {"id": r["id"], "state": r["state"], "at": r["at"],
                  "detail": ("chain row" if r["chain"] else "AK row (stage by id pattern)") + (" · rebase" if r["rebase"] else "")})
        if r["rebase"]:
            _item(nodes["rebase"], {"id": r["id"], "state": r["state"], "at": r["at"], "detail": r["stage"]})
            _touch(nodes["rebase"], r["_ts"])
        if r["state"] in ("ended", "filed"):
            v = _verdict(flags, r["id"])
            if v:
                g = nodes["gate_eval"]
                g["done"] += 1
                _item(g, {"id": r["id"], "state": v.get("row_verdict") or "verdict", "at": v.get("filed_at"),
                          "detail": v.get("answer")})
                _touch(g, _epoch(v.get("filed_at")))
            if r["state"] == "filed":
                f = nodes["file"]
                f["done"] += 1
                _item(f, {"id": r["id"], "state": "filed", "at": r["at"], "detail": r["stage"]})
                _touch(f, r["_ts"])
            else:
                nodes["file"]["queued"] += 1
            fc = _failclass(r["_man"])
            if fc and fc["side"] in ("harness", "candidate", "unknown"):
                n2 = nodes["failclass"]
                n2["done"] += 1
                _item(n2, {"id": r["id"], "state": fc["side"], "at": r["at"], "detail": f"{fc['klass']} ({fc['rule']})"})
                _touch(n2, r["_ts"])
    sources["rowflow"]["rows_in_window"] = len(rows)

    # lineage
    lin = sorted(glob.glob(os.path.join(lineage, "*-composite-*")))
    sources["lineage"] = {"path": lineage, "present": os.path.isdir(lineage), "runs": len(lin)}
    for d in lin[-ITEM_CAP:]:
        ts = _mtime(d)
        nodes["lineage"]["done"] += 1
        _item(nodes["lineage"], {"id": os.path.basename(d), "state": "generated", "at": _iso(ts),
                                 "detail": "fold list + keep ledger"})
        _touch(nodes["lineage"], ts)

    # decisions (P6)
    decisions = {"present": False, "counts": {}, "events": []}
    try:
        if detect is None:
            import decisions as D
            detect = D.detect
        rep = detect(OWNER, flags=flags, now=now)
        evs = rep.get("events") or []
        decisions = {"present": True, "as_of": rep.get("as_of"), "counts": rep.get("counts") or {},
                     "events": [{"kind": e.get("kind"), "subject": e.get("subject"),
                                 "summary": str(e.get("summary") or "")[:200]} for e in evs[:ITEM_CAP]]}
        dn = nodes["decisions"]
        for e in decisions["events"]:
            dn["queued"] += 1
            _item(dn, {"id": e["subject"], "state": e["kind"], "at": rep.get("as_of"), "detail": e["summary"]})
        _touch(dn, _epoch(rep.get("as_of")))
    except Exception as e:  # noqa: BLE001
        decisions["error"] = f"{type(e).__name__}: {e}"[:200]
        nodes["decisions"]["state"] = "unavailable"
        nodes["decisions"]["count"] = None
    sources["decisions"] = {"present": decisions["present"], "error": decisions.get("error")}

    newest = None
    for nid, n in nodes.items():
        if n["last_event"]:
            t = _epoch(n["last_event"])
            n["age_s"] = round(now - t, 1)
            if nid != "decisions":
                newest = t if newest is None else max(newest, t)
        if n["state"] == "idle":
            n["state"] = "active" if n["in_flight"] else ("waiting" if n["queued"] else "idle")
        # decisions' count is open decisions; never fold the detector's own as_of into loop liveness

    running = [{"id": r["id"], "stage": r["stage"], "at": r["at"]} for r in rows if r["state"] == "running"]
    queued = [{"id": r["id"], "stage": r["stage"]} for r in rows if r["state"] == "queued"]
    return {"schema": SCHEMA, "generated_at": _iso(now), "window_h": window_h, "owner": OWNER,
            "last_event": _iso(newest), "last_event_age_s": None if newest is None else round(now - newest, 1),
            "nodes": nodes, "edges": [list(e) for e in EDGES],
            "glance": {"running": running[:ITEM_CAP], "queued": queued[:ITEM_CAP], "running_n": len(running),
                       "queued_n": len(queued), "chain_rows": sum(1 for r in rows if r["chain"]),
                       "other_rows": other, "candidates": nodes["candidate"]["count"],
                       "decisions_n": len(decisions["events"])},
            "decisions": decisions, "sources": sources}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--spool", default=SPOOL)
    ap.add_argument("--lineage", default=LINEAGE)
    ap.add_argument("--window-h", type=float, default=168.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rep = build(a.flags, a.spool, a.lineage, window_h=a.window_h)
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        for nid, n in rep["nodes"].items():
            print(f"{n['owner']:3} {nid:11} count={n['count']} run={n['in_flight']} q={n['queued']} "
                  f"done={n['done']} last={n['last_event']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

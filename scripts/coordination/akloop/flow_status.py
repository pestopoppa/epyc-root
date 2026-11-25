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
INBOX = "/mnt/raid0/llm/autokernel/loop-memory/inbox"
CENSUS = "/mnt/raid0/llm/tmp/ak-bw-census/mi210_bandwidth_census.json"
#: per-served-path gate report (research stage_bodies.coverage_report), written by ak_runend.write_path_gates beside the census
PATH_GATES = "/mnt/raid0/llm/tmp/ak-bw-census/path-gates.json"
HOLDS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "handoffs", "active", "holds.yaml"))
AK_HOLD_SESSIONS = ("autokernel-all-devices-all-dimensions", "autokernel-rebuild", "akagg")
OWNER = "autokernel"
ITEM_CAP = 40
CHAIN_RX = re.compile(r"^akc-(?P<hyp>.+?)(?P<rb>-rb[0-9a-f]{7})?-(?P<stage>build|oracle-kld|op-perf|ab-timing|fold-check|serving-screen)-\d{8}")
STAGE_NAMES = ("build", "oracle-kld", "op-perf", "ab-timing", "fold-check", "serving-screen")

# Node spec: the ONE place the flowchart's topology is declared (the page draws positions, not semantics).
NODES = (
    ("inbox", "DET", "hypothesis inbox", "seeds + census surface seeds"),
    ("planner", "AI", "planner", "hypothesis per lane; reads BW surfaces"),
    ("critic", "AI", "critic", "reviews plan and patch (bounded rounds)"),
    ("author", "AI", "author", "writes the patch in the lane worktree"),
    ("candidate", "DET", "candidate record", "spool: base sha, patch sha, hypothesis"),
    ("serving-screen", "DET", "serving screen", "serving-knob arms; screen only, never a keep"),
    ("build", "DET", "build", "CPU quarter q0-q2, NUMA-bound"),
    ("oracle-kld", "DET", "oracle + KLD", "correctness gate, GPU quiet-only"),
    ("op-perf", "DET", "op-perf screen", "served-shape op perf; screen only, never a keep"),
    ("ab-timing", "DET", "A/B timing", "pre-registered pairs, futility looks"),
    ("fold-check", "DET", "fold check", "C-fold step, keep-path timing"),
    ("gate_eval", "DET", "gate evaluator", "RESULT -> verdict, no LLM"),
    ("file", "DET", "filed", "verdict filed, hand-back stamped"),
    ("lineage", "DET", "lineage / fold list", "keep ledger + next composite"),
    ("rebase", "DET", "stale-base recheck", "rebase-and-recheck chain (-rb)"),
    ("failclass", "DET", "failure routing", "crash/vacuous -> pipeline; cand -> drop"),
    ("census", "DET", "bandwidth census", "re-ranks surfaces; writes seed stubs"),
    ("decisions", "DET", "decisions detector", "operator/owner decisions needed"),
)
EDGES = (("inbox", "planner"), ("file", "census"), ("census", "planner"), ("planner", "critic"), ("critic", "author"), ("author", "candidate"), ("candidate", "build"), ("candidate", "serving-screen"),
         ("build", "oracle-kld"), ("oracle-kld", "op-perf"), ("op-perf", "ab-timing"), ("ab-timing", "fold-check"),
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
        for st in C.STAGE_BY_NAME.values():
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


def ak_hold(holds: str = HOLDS) -> dict | None:
    """The loop-launch hold covering the AK loop sessions, or None. Text scan (no yaml dep); unreadable = unknown."""
    try:
        txt = open(holds, encoding="utf-8").read()
    except OSError:
        return {"id": "unknown", "since": None, "reason": "holds.yaml unreadable (fail closed)"}
    for blk in re.split(r"\n- id: ", "\n" + txt)[1:]:
        if "scope: loop-launch" in blk and any(f"- {s}\n" in blk for s in AK_HOLD_SESSIONS):
            m = re.search(r"since: '?([^'\n]+)", blk)
            return {"id": blk.split("\n", 1)[0].strip(), "since": m.group(1) if m else None,
                    "reason": "operator loop-launch hold: AK agent loop is not launched"}
    return None


#: op-perf gate vocabulary (research stage_bodies.coverage_report): only `floored` counts as gated. A grid with no
#: floor can decide nothing (final-gate N2), so `grid-no-floor` and the legacy bare `grid` (which never checked a floor)
#: are gaps, as is `no-lane`; `ungated` is the older name of "nothing".
OP_PERF_GAPS = {"no-lane": "op-perf-no-lane", "grid-no-floor": "op-perf-no-floor", "grid": "op-perf-floor-unproven",
                "ungated": "op-perf-ungated"}


def path_gate_status(row: dict) -> dict:
    """One served path's gate status from a coverage_report row: which of its gates are `cell`/`floored`/`gated`, which are
    `ungated` / `quality-ungated` / an op-perf gap. A path is `gated` only when every gate is present (op-perf only when
    `floored`); anything missing is named, never folded into an "ok"."""
    timing, quality, op = row.get("timing"), row.get("quality"), row.get("op_perf")
    gaps = []
    if timing != "cell":
        gaps.append("ungated" if timing == "ungated" else "timing-unknown")
    if quality != "gated":
        gaps.append("quality-ungated" if quality == "quality-ungated" else "quality-unknown")
    if op != "floored":
        gaps.append(OP_PERF_GAPS.get(op, "op-perf-unknown"))
    return {"status": "gated" if not gaps else "+".join(gaps), "timing": timing, "quality": quality, "op_perf": op,
            "gaps": gaps}


def read_path_gates(path: str) -> dict:
    """The per-path gate report, as ak_runend wrote it. Absent / unreadable / errored is stated, never an empty "all gated"."""
    d = _load(path)
    if not isinstance(d, dict):
        return {"present": False, "path": path, "paths": [],
                "error": "no path-gates.json (ak_runend writes it at each AK row end)" if not os.path.exists(path)
                else "path-gates.json unreadable"}
    if d.get("error"):
        return {"present": False, "path": path, "paths": [], "at": d.get("at"), "error": str(d["error"])[:300]}
    rep = d.get("report")
    if not isinstance(rep, dict) or not rep:
        return {"present": False, "path": path, "paths": [], "at": d.get("at"), "error": "path-gates report empty"}
    paths = []
    for key in sorted(rep):
        row = rep[key] if isinstance(rep[key], dict) else {}
        paths.append({"key": key, "path_status": row.get("status"), "device": row.get("device"), **path_gate_status(row)})
    return {"present": True, "path": path, "at": d.get("at"), "paths": paths,
            "registry": d.get("registry") if isinstance(d.get("registry"), dict) else None,
            "ungated_n": sum(1 for p in paths if p["gaps"])}


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
          window_h: float = 168.0, detect=None, inbox: str = INBOX, census: str = CENSUS,
          holds: str = HOLDS, path_gates: str = PATH_GATES) -> dict:
    now = time.time() if now is None else now
    lo = now - window_h * 3600
    nodes = {nid: _node(o, lab, sub) for nid, o, lab, sub in NODES}
    sources: dict = {}

    for nid in ("planner", "critic", "author"):
        nodes[nid]["count"] = None
        nodes[nid]["state"] = "uninstrumented"
        nodes[nid]["note"] = "lanes report only through candidate records; no per-step signal"
    hold = ak_hold(holds)
    sources["hold"] = hold
    if hold:
        for nid in ("planner", "critic", "author"):
            nodes[nid]["state"] = "held"
            nodes[nid]["note"] = f"{hold['reason']} (hold {hold['id']}, since {hold['since'] or '?'})"

    # hypothesis inbox (seed.py install target) -- counts what the planner will see
    ib = sorted(glob.glob(os.path.join(inbox, "*.md")))
    sources["inbox"] = {"path": inbox, "present": os.path.isdir(inbox), "files": len(ib)}
    for p in ib:
        _item(nodes["inbox"], {"id": os.path.basename(p), "state": "installed", "at": _iso(_mtime(p)), "detail": "seed file"})
        _touch(nodes["inbox"], _mtime(p))
    nodes["inbox"]["done"] = len(ib)

    # bandwidth census (ak_runend step 4 -> census_update)
    cz = _load(census)
    sources["census"] = {"path": census, "present": isinstance(cz, dict)}
    if isinstance(cz, dict):
        cn = nodes["census"]
        surf = cz.get("surfaces") or []
        stale = sum(1 for x in surf if x.get("stale"))
        cn["done"] = len(cz.get("applied") or [])
        cn["note"] = f"{len(surf)} surfaces, {stale} stale; {len(cz.get('applied') or [])} RESULT(s) applied"
        for x in sorted(surf, key=lambda x: -(x.get("saving_ms_per_step") or 0)):
            _item(cn, {"id": x.get("id") or x.get("op") or "?", "state": "stale" if x.get("stale") else (x.get("status") or "open"),
                       "at": None, "detail": f"saves {x.get('saving_ms_per_step')} ms/step"})
        _touch(cn, _mtime(census))
        sources["census"]["surfaces"] = len(surf)

    # per-path gates (RSL-R6/R8): timing cell / ungated, quality gated / quality-ungated, op-perf floored / grid-no-floor / no-lane
    pg = read_path_gates(path_gates)
    sources["path_gates"] = {"path": path_gates, "present": pg["present"], "error": pg.get("error"),
                             "registry": pg.get("registry")}
    on, pg_items = nodes["op-perf"], []   # path rows are listed after the op-perf rows; they are not counted as rows
    if pg["present"]:
        pg_items = [{"id": p["key"], "state": p["status"], "at": pg.get("at"),
                     "detail": f"timing {p['timing']} · quality {p['quality']} · op-perf {p['op_perf']}"}
                    for p in pg["paths"]]
        on["note"] = (f"{pg['ungated_n']} of {len(pg['paths'])} served path(s) have a gate gap "
                      "(ungated / quality-ungated / op-perf not floored); counts are op-perf rows")
        reg = pg.get("registry") or {}
        if reg.get("status") == "registry-snapshot-failed":   # N9: the report was built without a proven origin/main registry
            on["note"] += "; registry-snapshot-failed: report not bound to orchestrator origin/main"
    else:
        on["note"] = f"per-path gate status unknown: {pg['error']}"

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
    for it in pg_items:   # per-path gate rows follow the op-perf rows, within ITEM_CAP
        if len(on["items"]) < ITEM_CAP:
            on["items"].append(it)

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
            if nid not in ("decisions", "census", "inbox"):
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
                       "decisions_n": len(decisions["events"]),
                       "hold": hold},
            "path_gates": pg,
            "decisions": decisions, "sources": sources}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--spool", default=SPOOL)
    ap.add_argument("--lineage", default=LINEAGE)
    ap.add_argument("--path-gates", default=PATH_GATES)
    ap.add_argument("--window-h", type=float, default=168.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rep = build(a.flags, a.spool, a.lineage, window_h=a.window_h, path_gates=a.path_gates)
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        for nid, n in rep["nodes"].items():
            print(f"{n['owner']:3} {nid:11} count={n['count']} run={n['in_flight']} q={n['queued']} "
                  f"done={n['done']} last={n['last_event']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

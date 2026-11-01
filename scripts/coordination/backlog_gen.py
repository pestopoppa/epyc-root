#!/usr/bin/env python3
"""backlog_gen.py - generate compute-flags/BACKLOG-<worker>.md, the ONE backlog each Codex worker churns.

Zero-token. Reads (never writes) the READY manifests, the keeper log, backlog-priority.json and the
worker's code queue; writes BACKLOG-<worker>.md (atomic replace) and refreshes the BLOCKED-INFERENCE
section at the top of WORK-<worker>-code.md with a pointer, so no older surface loses information.

    python3 backlog_gen.py                       # one pass, write BACKLOG-*.md
    python3 backlog_gen.py --dry-run             # print what would be written, write nothing
    python3 backlog_gen.py --loop [--interval 600]
    python3 backlog_gen.py --flags DIR --priority FILE --keeper-log FILE --out DIR   # fixtures / tests

Inference-row states (operator flowchart, 2026-11-01):
    blocked              - a non-inference task must be done first (keeper refusal, hold, harness fix,
                           schema migration, breaker, ...). The unblocking tasks are listed under the row.
    needs-launcher       - in backlog-priority.json inference_prep with blocker "missing launcher", no READY manifest.
    needs-qualification  - epyc.ready.v2 manifest present, no hold, no keeper refusal; the keeper's
                           qualification (the realistic dry run) has not run or passed yet.
    qualified-armed      - the keeper accepted the row: receipt on disk and the keeper arms it when a bin frees.
    running              - a live grant names the id (grants/<id>.grant, no .ended) or the keeper logged QUEUED.
    done                 - grants/<id>.ended or filing-done/<id>.FILED exists.

`unblocks:` linkage (the field workers fill when they file tasks):
    * on a code-queue line in WORK-<worker>-code.md:   ... task text ... [unblocks: <ready-id>,<row-id>]
    * in compute-flags/unblocks.json:                  {"<task key or free text>": ["<ready-id>", ...]}
    * on a READY manifest (optional, read-only here):  "blocked_by": ["<task text>", ...]
    * backlog-priority.json rows already carry "unblocks": [<row ids>]; inference_prep entries carry
      "filler" (the READY id) and "row" (the handoff row id), which is how the two id spaces are joined.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import sys
import time

FLAGS_DEFAULT = "/mnt/raid0/llm/tmp/compute-flags"
PRIORITY_DEFAULT = "/workspace/handoffs/active/backlog-priority.json"
WORKERS = ("ni", "refactor", "codex3")
FLOOR = 2
B_MARK, E_MARK = "<!-- BLOCKED-INFERENCE:start -->", "<!-- BLOCKED-INFERENCE:end -->"
STATE_ORDER = {"blocked": 0, "needs-launcher": 1, "needs-qualification": 2,
               "qualified-armed": 3, "running": 4, "done": 5}


def worker_of(owner: str) -> str | None:
    o = (owner or "").lower()
    if "codex3" in o or "gpt-6.1-sol" in o:
        return "codex3"
    if "refactor" in o or "01a16fc3" in o:
        return "refactor"
    if re.search(r"(^|[^a-z])ni([^a-z]|$)", o) or "01a16d6b" in o:
        return "ni"
    return None


def lane_of(d: dict) -> str:
    regs = str(d.get("regions", ""))
    if d.get("gpu_quiet") or "mi210" in regs or "gpu" in regs:
        return "gpu"
    if regs.strip() in ("0-95",) or "whole" in regs:
        return "host"
    return "cpu"


def fold_keeper_log(path: str, tail: int = 6000) -> dict:
    """State fold of the keeper log: last refusal per id, ids the keeper qualified/armed/queued."""
    st = {"skip": {}, "qual": set(), "armed": set(), "queued": set(), "refused": {}, "idle": []}
    try:
        lines = open(path, errors="replace").readlines()[-tail:]
    except OSError:
        return st
    rx = re.compile(r"^(\S+) (READY-SKIP|READY-QUAL|READY-ARM|READY-RESULT|READY-WAIT|READY-RELOCATE|"
                    r"READY-WAIT-DISK|READY-WAIT-QUAL-RESOURCE|IDLE-ALARM|QUAL-FAILURE) (.*)$")
    for l in lines:
        m = rx.match(l.strip())
        if not m:
            continue
        ts, ev, rest = m.groups()
        if ev == "IDLE-ALARM":
            mm = re.search(r": (\S+)$", rest)
            if mm:
                st["idle"].append((ts, mm.group(1)))
            continue
        # id is either "<id>:" / "<id> (rank" or "qual-failed /path/<id>.json:"
        mid = re.search(r"(?:/|^|\s)([A-Za-z0-9_.-]+?)\.json(?::|$)", rest) or re.match(r"([A-Za-z0-9_.-]+)", rest)
        if not mid:
            continue
        rid = mid.group(1)
        detail = rest.split(":", 1)[1].strip() if ":" in rest else rest
        if ev == "READY-SKIP":
            st["skip"][rid] = detail.split(" (left in place", 1)[0][:200]
        elif ev == "QUAL-FAILURE":
            st["skip"][rid] = ("qualification failed: " + detail)[:200]
        elif ev == "READY-QUAL":
            st["skip"].pop(rid, None)
            st["qual"].add(rid)
        elif ev == "READY-ARM":
            st["armed"].add(rid)
        elif ev == "READY-RESULT":
            if detail.startswith("QUEUED"):
                st["queued"].add(rid)
                st["refused"].pop(rid, None)
            elif detail.startswith("REFUSED"):
                st["refused"][rid] = detail[:200]
        elif ev in ("READY-WAIT", "READY-RELOCATE", "READY-WAIT-DISK", "READY-WAIT-QUAL-RESOURCE"):
            st["skip"].pop(rid, None)
    return st


def load_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def parse_work_lines(path: str) -> list[dict]:
    """Code-queue lines of WORK-<w>-code.md (outside the BLOCKED-INFERENCE section)."""
    out = []
    try:
        s = open(path, errors="replace").read()
    except OSError:
        return out
    s = re.sub(re.escape(B_MARK) + r".*?" + re.escape(E_MARK) + r"\n*", "", s, flags=re.S)
    for l in s.splitlines():
        m = re.match(r"- \[(\w+)\] (\S+?):(\d+) — (.*)$", l)
        if not m:
            continue
        size, f, ln, text = m.groups()
        ub = re.search(r"\[unblocks:\s*([^\]]+)\]", text)
        unblocks = [x.strip() for x in ub.group(1).split(",")] if ub else []
        out.append({"size": size, "file": f, "line": int(ln), "text": text.strip(), "unblocks": unblocks, "raw": l})
    return out


def _rank_of(desc: str) -> float:
    m = re.search(r"rank (\d+)", desc)
    return float(m.group(1)) if m else 9999.0


def build(flags: str, priority_path: str, keeper_log: str, now: _dt.datetime | None = None) -> dict:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    F = flags.rstrip("/") + "/"
    pri = load_json(priority_path) or {}
    prows = pri.get("rows") or {}
    prep = pri.get("inference_prep") or []
    unblocks_map = load_json(F + "unblocks.json") or {}
    klog = fold_keeper_log(keeper_log)

    # row-id -> non-inference tasks (from backlog-priority rows whose `unblocks` names it)
    unblockers_by_row: dict[str, list[str]] = {}
    for rid, r in prows.items():
        if r.get("kind") == "non-inference":
            for tgt in r.get("unblocks") or []:
                unblockers_by_row.setdefault(tgt, []).append(f"{rid} (T{r.get('tier')} rank {r.get('rank')}): {r.get('basis', '')[:140]}")

    per: dict[str, dict] = {w: {"rows": [], "code": [], "qual": {"cpu": 0, "gpu": 0, "host": 0}} for w in WORKERS}
    work_lines = {w: parse_work_lines(F + f"WORK-{w}-code.md") for w in WORKERS}
    seen_ids = set()

    def tasks_for(rid: str, row_id: str | None, reasons: list[str], w: str, placeholder: bool = True) -> list[str]:
        t = []
        for r in reasons:
            if r:
                t.append("fix: " + r)
        for wl in work_lines[w]:
            if rid in wl["unblocks"] or (row_id and row_id in wl["unblocks"]):
                t.append(f"code [{wl['size']}] {wl['file']}:{wl['line']} — {wl['text'][:160]}")
        for key, ids in unblocks_map.items():
            if rid in ids or (row_id and row_id in ids):
                t.append("code " + key[:180])
        if row_id:
            # backlog-priority non-inference rows that declare they unblock this handoff row: best 3 by rank
            t += ["code " + x for x in sorted(unblockers_by_row.get(row_id, []), key=_rank_of)[:3]]
        if not t and placeholder:
            t.append("(no unblocking task filed yet — file one with `unblocks: " + rid + "`)")
        return t

    for p in sorted(glob.glob(F + "ready/*.json")):
        d = load_json(p)
        if not isinstance(d, dict):
            continue
        rid = d.get("id") or os.path.basename(p)[:-5]
        w = worker_of(str(d.get("owner", "")))
        if w not in per:
            continue
        if os.path.exists(F + f"ready/{rid}.withdrawn"):
            continue
        seen_ids.add(rid)
        lane = lane_of(d)
        q = d.get("qualification") if isinstance(d.get("qualification"), dict) else {}
        receipt = q.get("receipt")
        has_receipt = bool(receipt and os.path.isfile(receipt)) or rid in klog["qual"]
        v2 = d.get("schema") == "epyc.ready.v2"
        reasons = []
        if os.path.exists(F + f"grants/{rid}.ended") or os.path.exists(F + f"filing-done/{rid}.FILED"):
            state = "done"
        elif os.path.exists(F + f"grants/{rid}.grant") or rid in klog["queued"]:
            state = "running"
        else:
            if d.get("hold"):
                reasons.append("hold: " + str(d.get("hold"))[:140])
            if rid in klog["skip"]:
                reasons.append("keeper: " + klog["skip"][rid])
            if rid in klog["refused"]:
                reasons.append("grant refused: " + klog["refused"][rid])
            if not v2:
                reasons.append(f"manifest schema {d.get('schema') or 'unset'} != epyc.ready.v2 (migrate the manifest)")
            for b in d.get("blocked_by") or []:
                reasons.append(str(b)[:160])
            if reasons:
                state = "blocked"
            elif has_receipt:
                state = "qualified-armed"
            else:
                state = "needs-qualification"
        prep_entry = next((e for e in prep if e.get("filler") == rid), None)
        row_id = prep_entry.get("row") if prep_entry else d.get("row")
        if state == "qualified-armed":
            per[w]["qual"][lane] += 1
        per[w]["rows"].append({
            "id": rid, "lane": lane, "rank": d.get("priority_rank") or (prep_entry or {}).get("rank") or 999,
            "state": state, "row": row_id, "reasons": reasons,
            "tasks": tasks_for(rid, row_id, reasons, w) if state == "blocked" else [],
        })

    # inference_prep entries with no READY manifest yet
    for e in prep:
        rid = e.get("filler") or e.get("row")
        w = worker_of(str(e.get("owner", "")))
        if not rid or rid in seen_ids or w not in per:
            continue
        seen_ids.add(rid)
        blocker = str(e.get("blocker") or "")
        state = "needs-launcher" if re.search(r"missing launcher", blocker, re.I) else "blocked"
        per[w]["rows"].append({
            "id": rid, "lane": "cpu", "rank": e.get("rank") or 999, "state": state, "row": e.get("row"),
            "reasons": [blocker[:200]] if blocker else [],
            "tasks": tasks_for(rid, e.get("row"), [blocker[:200]] if state == "blocked" else [], w)
            if state != "needs-launcher" else ["write the launcher (real entry, taskset -c \"$FILLER_CPUS\", rc75 at cutoff), then file the epyc.ready.v2 manifest"]
                                           + tasks_for(rid, e.get("row"), [], w, placeholder=False),
        })

    for w in WORKERS:
        per[w]["rows"].sort(key=lambda r: (STATE_ORDER[r["state"]], float(r["rank"]) if str(r["rank"]).replace(".", "", 1).isdigit() else 999))
        per[w]["code"] = work_lines[w]
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%MZ"), "workers": per}


def render(w: str, data: dict) -> str:
    d = data["workers"][w]
    L = [f"# BACKLOG-{w} — the one backlog (auto-generated {data['generated_at']}; regenerated every 10 min, do not edit)",
         "", f"Goal: GOAL-{w}.md. Work top to bottom. A blocked row's unblocking tasks are non-inference work: do them,",
         "then prepare the launcher, then let the keeper qualify it (the dry run), then it is armed. Repeat until nothing is blocked.", ""]
    counts = {}
    for r in d["rows"]:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    L.append("State counts: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER) + ".")
    for lane in ("cpu", "gpu"):
        if d["qual"][lane] < FLOOR:
            L.append(f"- [FLOOR] {lane.upper()}: {d['qual'][lane]} qualified-armed row(s) < {FLOOR}. Unblock and qualify rows below first.")
    L += ["", "## Inference rows (priority order)", ""]
    if not d["rows"]:
        L.append("- none")
    for r in d["rows"]:
        L.append(f"- [{r['state']}] {r['lane']} rank={r['rank']} **{r['id']}**" + (f" (row {r['row']})" if r.get("row") else ""))
        for t in r["tasks"]:
            L.append(f"    - unblock: {t}")
    L += ["", "## Non-inference tasks (after every blocked row above has its tasks done; S first)", ""]
    linked = {t for r in d["rows"] for t in r["tasks"]}
    n = 0
    for wl in d["code"]:
        key = f"code [{wl['size']}] {wl['file']}:{wl['line']} — {wl['text'][:160]}"
        if key in linked:
            continue
        L.append(wl["raw"])
        n += 1
    if n == 0:
        L.append("- none")
    L += ["", "Filing a task that unblocks a row: append `[unblocks: <ready-id>]` to its line in WORK-" + w +
          "-code.md, or add it to compute-flags/unblocks.json. See scripts/coordination/backlog_gen.py.", ""]
    return "\n".join(L)


def blocked_section(w: str, data: dict) -> str:
    d = data["workers"][w]
    L = [B_MARK, f"## BLOCKED INFERENCE — your backlog is BACKLOG-{w}.md (auto-generated {data['generated_at']}); this section mirrors its blocked rows", ""]
    for lane in ("cpu", "gpu"):
        if d["qual"][lane] < FLOOR:
            L.append(f"- [FLOOR] {lane.upper()}: only {d['qual'][lane]} qualified-armed READY row(s); keep >={FLOOR}.")
    for r in d["rows"]:
        if r["state"] in ("blocked", "needs-launcher", "needs-qualification"):
            L.append(f"- [{r['state'].upper()}] {r['lane']} rank={r['rank']} {r['id']} — " + ("; ".join(r["reasons"]) or r["state"]))
    if len(L) == 3:
        L.append("- none: every READY row is qualified and runnable.")
    L += ["", E_MARK, ""]
    return "\n".join(L)


def write_atomic(path: str, content: str):
    tmp = path + ".gen-tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


def run_once(flags: str, priority: str, keeper_log: str, out: str, dry_run: bool, update_work: bool = True) -> dict:
    data = build(flags, priority, keeper_log)
    for w in WORKERS:
        text = render(w, data)
        dest = os.path.join(out, f"BACKLOG-{w}.md")
        if dry_run:
            print(f"===== {dest}\n{text}")
        else:
            write_atomic(dest, text)
        wp = os.path.join(flags, f"WORK-{w}-code.md")
        if update_work and os.path.exists(wp):
            sec = blocked_section(w, data)
            if dry_run:
                print(f"===== {wp} (section)\n{sec}")
            else:
                s = open(wp, errors="replace").read()
                s = re.sub(re.escape(B_MARK) + r".*?" + re.escape(E_MARK) + r"\n*", "", s, flags=re.S)
                write_atomic(wp, sec + s)
    summary = {w: {"rows": len(data["workers"][w]["rows"]),
                   "blocked": sum(1 for r in data["workers"][w]["rows"] if r["state"] == "blocked"),
                   "qual": data["workers"][w]["qual"]} for w in WORKERS}
    print(data["generated_at"], json.dumps(summary, sort_keys=True))
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    ap.add_argument("--priority", default=PRIORITY_DEFAULT)
    ap.add_argument("--keeper-log", default=None)
    ap.add_argument("--out", default=None, help="where BACKLOG-*.md go (default: --flags)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-work-section", action="store_true", help="do not refresh the WORK-*-code.md section")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    a = ap.parse_args(argv)
    klog = a.keeper_log or os.path.join(a.flags, "ws58-calendar-keeper.log")
    out = a.out or a.flags
    while True:
        try:
            run_once(a.flags, a.priority, klog, out, a.dry_run, not a.no_work_section)
        except Exception as e:  # never die in the loop
            print(_dt.datetime.now(_dt.timezone.utc).strftime("%FT%TZ"), "backlog_gen error:", repr(e), file=sys.stderr)
        if not a.loop:
            break
        time.sleep(a.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())

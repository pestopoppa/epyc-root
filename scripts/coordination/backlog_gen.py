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
    qualified-armed      - the keeper accepted the row: the predeclared receipt FILE is on disk (ready/ or ready/armed/)
                           and the keeper arms it when a bin frees. A receipt that is named but missing is NOT
                           qualified: the row is `blocked` with cause "keeper" (awaiting keeper qualification) or,
                           after READY-QUAL/arming, cause "worker" (receipt lost; republish). Keeper v9 refusal memos
                           (ws58-keeper-state/qual-refused/<id>.json, keeper_qual_memo.py) are the row's fix task.
    running              - a live grant names the id (grants/<id>.grant, no .ended) or the keeper logged QUEUED.
    done                 - grants/<id>.ended or filing-done/<id>.FILED exists.

`unblocks:` linkage (the field workers fill when they file tasks):
    * on a code-queue line in WORK-<worker>-code.md:   ... task text ... [unblocks: <ready-id>,<row-id>]
    * in compute-flags/unblocks.json:                  {"<task key or free text>": ["<ready-id>", ...]}
    * on a READY manifest (optional, read-only here):  "blocked_by": ["<task text>", ...]
    * backlog-priority.json rows already carry "unblocks": [<row ids>]; inference_prep entries carry
      "filler" (the READY id) and "row" (the handoff row id), which is how the two id spaces are joined.

Operator rulings (2026-11-01), encoded here:
    rule 1 (starved lane first) - advanceable rows (blocked / needs-launcher / needs-qualification) are ordered
        first by "is my lane (cpu/gpu) below its FLOOR of qualified-armed rows", then by priority rank. Then
        parked, qualified-armed, running, done.
    rule 2 (3 retries, then park) - a row's LINEAGE is, in order: the manifest's `lineage` field; else the
        lineage of the id named by its `supersedes` field; else the ID STEM (the id with trailing
        `-YYYYMMDD[...]`, `-vN`, `-rN`, `-rearm[-rN]`, `-retryN` suffixes stripped, e.g.
        codex-hil15-s0-micron-v12-20261031 -> codex-hil15-s0-micron). Every distinct id of a lineage with a
        keeper qualification failure (QUAL-FAILURE, or READY-SKIP qual-failed) counts once. At >= MAX_QUAL_FAILS
        failures and no live qualified/running/done id, the lineage's open rows become `parked` (PARKED
        NEEDS-OPERATOR); a one-page summary goes to compute-flags/operator-escalations/<lineage>.md and workers
        stop retrying it. Un-park (operator's call): a fresh manifest carrying
        `lineage_reset: <n>` counts only failures above n; or withdraw the lineage.

Session-per-handoff pilot (operator, 2026-11-01): handoffs listed in compute-flags/handoff-sessions.json
(`--sessions`) are owned by ONE resumable session each, not by the generalist workers. Their READY rows,
inference_prep entries and code-queue lines (matched by `row_ids`, `row_patterns`, `handoff_rows`, or the
manifest's `handoff` field / the code line's file) are EXCLUDED from BACKLOG-<worker>.md and emitted to
BACKLOG-handoff-<slug>.md instead. See scripts/coordination/handoff_sessions.py.
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
SESSIONS_NAME = "handoff-sessions.json"
PRIORITY_DEFAULT = "/workspace/handoffs/active/backlog-priority.json"
WORKERS = ("ni", "refactor", "codex3")
FLOOR = 2
B_MARK, E_MARK = "<!-- BLOCKED-INFERENCE:start -->", "<!-- BLOCKED-INFERENCE:end -->"
STATE_ORDER = {"blocked": 0, "needs-launcher": 1, "needs-qualification": 2, "parked": 3,
               "qualified-armed": 4, "running": 5, "done": 6}
ADVANCEABLE = ("blocked", "needs-launcher", "needs-qualification")
MAX_QUAL_FAILS = 3
_STEM_SUFFIX = re.compile(r"(?:[-_](?:\d{8}(?:T\d{4,6}Z?)?|v\d+|r\d+|rearm|retry\d*|try\d+))+$", re.I)


_RUN_FAIL = re.compile(r"qual-run-rc=|qualification failed rc|qual:row \S+ expected|QUAL-FAILURE", re.I)
_NOT_A_RUN = re.compile(r"schema|receipt|nonce|wait|disk|breaker|^held\b", re.I)
_RECEIPT_ABSENT = re.compile(r"qualification receipt absent", re.I)
_BREAKER = re.compile(r"worker-breaker active", re.I)
_BREAKER_HINT = (" - released automatically by the next keeper-QUALIFIED row of this owner (reconcile_failures); "
                 "the breaker blocks arming, not qualification, so publish/fix a row that qualifies")
_REGISTRY_ROW = re.compile(r"expected exactly one 18-cell record", re.I)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import keeper_qual_memo as _kqm  # keeper v9 refusal memos (ws58-keeper-state/qual-refused/<id>.json)
except ImportError:  # older bundle without the memo helper: fall back to the keeper-log window only
    _kqm = None


def keeper_refusal_memo(manifest_path: str, flags: str) -> dict | None:
    """The keeper's memoised qualification refusal for this row, only while the row is unchanged since."""
    if _kqm is None:
        return None
    try:
        return _kqm.current_memo(manifest_path, flags.rstrip("/"))
    except Exception:
        return None


def keeper_refusal_task(memo: dict, rid: str) -> str:
    reason = str(memo.get("reason") or "")[:240]
    t = f"keeper qualification refused ({memo.get('refusals', 1)}x, row unchanged since {memo.get('at', '?')}): {reason}"
    if _REGISTRY_ROW.search(reason):
        t += (f" -> register the row: FILLERS.md has no `| {rid} |` 18-cell row and qual-v1 row_binding reads it; append the single "
              f"row of compute-flags/ready/{rid}.row.md to compute-flags/FILLERS.md (whole-file atomic replace) and validate with "
              f"`python3 scripts/coordination/validate_fillers.py --file /mnt/raid0/llm/tmp/compute-flags/FILLERS.md --row {rid}`")
    else:
        t += " -> fix the cause; the keeper retries as soon as the manifest, the ready row or its FILLERS.md row changes"
    return t


def is_qual_run_failure(event: str, detail: str) -> bool:
    """Rule 2 counts only qualifier RUNS that failed on the real config. Pre-run re-check skips (legacy schema,
    receipt absent, nonce, wait-conflict, WAIT-DISK, breaker, held) are not attempts."""
    if event == "QUAL-FAILURE":
        return not _NOT_A_RUN.search(detail)
    return bool(_RUN_FAIL.search(detail)) and not _NOT_A_RUN.search(detail)


def id_stem(rid: str) -> str:
    """Lineage by shared ID stem: strip trailing date / -vN / -rN / -rearm / -retryN suffixes."""
    s = _STEM_SUFFIX.sub("", rid or "")
    return s or rid


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
    st = {"skip": {}, "qual": set(), "armed": set(), "queued": set(), "refused": {}, "idle": [], "fails": {}}
    try:
        all_lines = open(path, errors="replace").readlines()
    except OSError:
        return st
    lines = all_lines[-tail:]
    # rule 2 counts failures over the WHOLE log, not just the state window
    for l in all_lines[:-tail] if len(all_lines) > tail else []:
        if "qual" in l and ("QUAL-FAILURE" in l or "READY-SKIP" in l):
            mm = re.match(r"^(\S+) (QUAL-FAILURE|READY-SKIP) (?:qual-failed \S*?/)?([A-Za-z0-9_.-]+?)(?:\.json)?:\s*(.*)$", l.strip())
            if mm and is_qual_run_failure(mm.group(2), mm.group(4)):
                st["fails"].setdefault(mm.group(3), []).append((mm.group(1), mm.group(4)[:300]))
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
            if is_qual_run_failure(ev, detail.split(" (left in place", 1)[0]):
                st["fails"].setdefault(rid, []).append((ts, detail[:300]))
        elif ev == "QUAL-FAILURE":
            st["skip"][rid] = ("qualification failed: " + detail)[:200]
            if is_qual_run_failure(ev, detail):
                st["fails"].setdefault(rid, []).append((ts, detail[:300]))
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


def load_pilots(path: str | None) -> dict[str, dict]:
    """slug -> {handoff, ids, patterns, rows} for every piloted handoff not marked done."""
    reg = load_json(path) if path else None
    out = {}
    for slug, e in ((reg or {}).get("sessions") or {}).items():
        if not isinstance(e, dict) or e.get("status") == "done" or not e.get("handoff"):
            continue
        out[slug] = {"handoff": "handoffs/" + str(e["handoff"]).split("handoffs/", 1)[-1],
                     "ids": set(e.get("row_ids") or []),
                     "patterns": [re.compile(x, re.I) for x in e.get("row_patterns") or []],
                     "rows": set(e.get("handoff_rows") or [])}
    return out


def pilot_of(pilots: dict, rid: str, row_id: str | None = None, handoff: str | None = None) -> str | None:
    for slug, p in pilots.items():
        if rid in p["ids"] or (row_id and row_id in p["rows"]):
            return slug
        if handoff and str(handoff).endswith(p["handoff"].split("/")[-1]):
            return slug
        if any(x.search(rid or "") for x in p["patterns"]):
            return slug
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


def build(flags: str, priority_path: str, keeper_log: str, now: _dt.datetime | None = None,
          sessions_path: str | None = None) -> dict:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    F = flags.rstrip("/") + "/"
    pri = load_json(priority_path) or {}
    prows = pri.get("rows") or {}
    prep = pri.get("inference_prep") or []
    unblocks_map = load_json(F + "unblocks.json") or {}
    klog = fold_keeper_log(keeper_log)
    pilots = load_pilots(sessions_path if sessions_path is not None else F + SESSIONS_NAME)
    buckets = list(WORKERS) + [f"handoff-{s}" for s in pilots]

    # row-id -> non-inference tasks (from backlog-priority rows whose `unblocks` names it)
    unblockers_by_row: dict[str, list[str]] = {}
    for rid, r in prows.items():
        if r.get("kind") == "non-inference":
            for tgt in r.get("unblocks") or []:
                unblockers_by_row.setdefault(tgt, []).append(f"{rid} (T{r.get('tier')} rank {r.get('rank')}): {r.get('basis', '')[:140]}")

    per: dict[str, dict] = {w: {"rows": [], "code": [], "qual": {"cpu": 0, "gpu": 0, "host": 0}} for w in buckets}
    work_lines = {w: parse_work_lines(F + f"WORK-{w}-code.md") for w in WORKERS}
    for slug, p in pilots.items():  # code lines on a piloted handoff move to its bucket
        work_lines[f"handoff-{slug}"] = [wl for w in WORKERS for wl in work_lines[w] if wl["file"] == p["handoff"]]
        for w in WORKERS:
            work_lines[w] = [wl for wl in work_lines[w] if wl["file"] != p["handoff"]]
    seen_ids = set()

    def tasks_for(rid: str, row_id: str | None, reasons: list[str], w: str, placeholder: bool = True) -> list[str]:
        t = []
        for r in reasons:
            if r:
                t.append(("wait (ws58 keeper): " if r.startswith("awaiting keeper qualification") else "fix: ") + r)
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

    # ready/ (pending) first, then ready/armed/ (v2 only: legacy armed manifests are refused by grant_ok v3 and are
    # not this backlog's rows). A v2 row is QUALIFIED only when its predeclared receipt FILE exists; a receipt that is
    # named but missing is a blocked row whose cause is the keeper (it has not qualified it) - counting it as
    # qualified hid the 2026-11-01 GPU starvation.
    manifest_paths = sorted(glob.glob(F + "ready/*.json")) + sorted(glob.glob(F + "ready/armed/*.json"))
    for p in manifest_paths:
        d = load_json(p)
        if not isinstance(d, dict):
            continue
        armed_dir = "/ready/armed/" in p
        v2 = d.get("schema") == "epyc.ready.v2"
        if armed_dir and not v2:
            continue
        rid = d.get("id") or os.path.basename(p)[:-5]
        w = worker_of(str(d.get("owner", "")))
        if w not in per or rid in seen_ids:
            continue
        if os.path.exists(F + f"ready/{rid}.withdrawn"):
            continue
        seen_ids.add(rid)
        lane = lane_of(d)
        q = d.get("qualification") if isinstance(d.get("qualification"), dict) else {}
        receipt = q.get("receipt") if isinstance(q.get("receipt"), str) else None
        receipt_on_disk = bool(receipt and os.path.isfile(receipt))
        reasons = []
        cause = "worker"
        if os.path.exists(F + f"grants/{rid}.ended") or os.path.exists(F + f"filing-done/{rid}.FILED"):
            state = "done"
        elif os.path.exists(F + f"grants/{rid}.grant") or rid in klog["queued"]:
            state = "running"
        else:
            if d.get("hold"):
                reasons.append("hold: " + str(d.get("hold"))[:140])
            memo = keeper_refusal_memo(p, F)
            if memo:
                reasons.append(keeper_refusal_task(memo, rid))
            skip = klog["skip"].get(rid)
            if skip and not _RECEIPT_ABSENT.search(skip) and not (memo and skip.strip()[:120] == str(memo.get("reason", "")).strip()[:120]):
                reasons.append("keeper: " + skip + (_BREAKER_HINT if _BREAKER.search(skip) else ""))
            if rid in klog["refused"]:
                reasons.append("grant refused: " + klog["refused"][rid])
            if not v2:
                reasons.append(f"manifest schema {d.get('schema') or 'unset'} != epyc.ready.v2 (migrate the manifest)")
            for b in d.get("blocked_by") or []:
                reasons.append(str(b)[:160])
            if v2 and receipt and not receipt_on_disk:
                if rid in klog["qual"] or armed_dir:
                    reasons.append(f"qualification receipt {receipt} named but MISSING although the keeper "
                                   + ("armed the row" if armed_dir else "logged READY-QUAL")
                                   + " (reaped/deleted?) - the row cannot be granted; republish under a new id")
                elif not reasons:
                    cause = "keeper"
                    reasons.append(f"awaiting keeper qualification: receipt {receipt} is named but absent; the ws58 keeper "
                                   "(qualify_pending) has not qualified this row yet - no worker action, ws58 owns the keeper")
            if reasons:
                state = "blocked"
            elif receipt_on_disk:
                state = "qualified-armed"
            else:
                state = "needs-qualification"
        prep_entry = next((e for e in prep if e.get("filler") == rid), None)
        row_id = prep_entry.get("row") if prep_entry else d.get("row")
        slug = pilot_of(pilots, rid, row_id, d.get("handoff"))
        if slug:
            w = f"handoff-{slug}"
        if state == "qualified-armed":
            per[w]["qual"][lane] += 1
        per[w]["rows"].append({
            "id": rid, "lane": lane, "rank": d.get("priority_rank") or (prep_entry or {}).get("rank") or 999,
            "state": state, "row": row_id, "reasons": reasons, "cause": cause if state == "blocked" else "",
            "tasks": tasks_for(rid, row_id, reasons, w) if state == "blocked" else [],
        })

    # inference_prep entries with no READY manifest yet
    for e in prep:
        rid = e.get("filler") or e.get("row")
        w = worker_of(str(e.get("owner", "")))
        slug = pilot_of(pilots, rid or "", e.get("row"), e.get("handoff"))
        if slug:
            w = f"handoff-{slug}"
        if not rid or rid in seen_ids or w not in per:
            continue
        # A withdrawn READY ID stays withdrawn even when only its priority
        # entry remains, or its manifest was skipped above.
        if os.path.exists(F + f"ready/{rid}.withdrawn"):
            continue
        seen_ids.add(rid)
        blocker = str(e.get("blocker") or "")
        if os.path.exists(F + f"grants/{rid}.ended") or os.path.exists(F + f"filing-done/{rid}.FILED"):
            state = "done"
        else:
            state = "needs-launcher" if re.search(r"missing launcher", blocker, re.I) else "blocked"
        per[w]["rows"].append({
            "id": rid, "lane": "cpu", "rank": e.get("rank") or 999, "state": state, "row": e.get("row"),
            "reasons": [blocker[:200]] if blocker else [],
            "tasks": tasks_for(rid, e.get("row"), [blocker[:200]] if state == "blocked" else [], w)
            if state == "blocked" else (["write the launcher (real entry, taskset -c \"$FILLER_CPUS\", rc75 at cutoff), then file the epyc.ready.v2 manifest"]
                                           + tasks_for(rid, e.get("row"), [], w, placeholder=False))
            if state == "needs-launcher" else [],
        })

    # rule 2: lineage, failure counting, parking
    manifests = {}
    for p in glob.glob(F + "ready/*.json"):
        d = load_json(p)
        if isinstance(d, dict):
            manifests[d.get("id") or os.path.basename(p)[:-5]] = d

    def lineage_of(rid: str, depth: int = 0) -> str:
        d = manifests.get(rid) or {}
        if d.get("lineage"):
            return str(d["lineage"])
        if d.get("supersedes") and depth < 20:
            sup = d["supersedes"]
            sup = sup[0] if isinstance(sup, list) and sup else sup
            if isinstance(sup, str) and sup:
                return lineage_of(sup, depth + 1)
        return id_stem(rid)

    fails_by_lineage: dict[str, list] = {}
    for fid, evs in klog["fails"].items():
        fails_by_lineage.setdefault(lineage_of(fid), []).append((fid, evs))
    parked: dict[str, dict] = {}
    for w in buckets:
        rows = per[w]["rows"]
        for r in rows:
            r["lineage"] = lineage_of(r["id"])
        for lin in {r["lineage"] for r in rows}:
            members = [r for r in rows if r["lineage"] == lin]
            fl = sorted(fails_by_lineage.get(lin, []), key=lambda x: x[1][-1][0])
            reset = max([int((manifests.get(r["id"]) or {}).get("lineage_reset") or 0) for r in members] + [0])
            nfail = max(0, len(fl) - reset)
            for r in members:
                r["lineage_fails"] = nfail
            if nfail < MAX_QUAL_FAILS or any(r["state"] in ("qualified-armed", "running", "done") for r in members):
                continue
            for r in members:
                if r["state"] in ADVANCEABLE:
                    r["parked_from"] = r["state"]
                    r["state"] = "parked"
                    r["tasks"] = [f"PARKED NEEDS-OPERATOR: {nfail} failed keeper qualifications in lineage {lin}; "
                                  f"do not retry. See operator-escalations/{lin}.md"]
            parked[lin] = {"worker": w, "fails": fl, "rows": members}

    for w in buckets:
        starved = {ln for ln in ("cpu", "gpu") if per[w]["qual"][ln] < FLOOR}
        per[w]["starved"] = sorted(starved)

        def _key(r):
            rank = float(r["rank"]) if str(r["rank"]).replace(".", "", 1).isdigit() else 999
            if r["state"] in ADVANCEABLE:  # rule 1: starved lane first, then global priority
                return (0, 0 if r["lane"] in starved else 1, rank, STATE_ORDER[r["state"]])
            return (1, STATE_ORDER[r["state"]], rank, 0)
        per[w]["rows"].sort(key=_key)
        per[w]["code"] = work_lines[w]
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%MZ"), "workers": per, "parked": parked,
            "pilots": {s: p["handoff"] for s, p in pilots.items()}}


def escalation_md(lin: str, p: dict, generated_at: str) -> str:
    L = [f"# PARKED NEEDS-OPERATOR — lineage `{lin}` (worker {p['worker']}; generated {generated_at})", "",
         f"{len(p['fails'])} failed keeper qualifications (limit {MAX_QUAL_FAILS}, operator rule 2, 2026-11-01). "
         "Workers have stopped retrying this lineage.", "", "## Refusals (each id, oldest first)", ""]
    for fid, evs in p["fails"]:
        for ts, det in evs:
            L.append(f"- {ts} **{fid}**: {det}")
    L += ["", "## What was tried (ids in the lineage and their last state)", ""]
    for r in p["rows"]:
        L.append(f"- {r['id']} ({r['lane']}, rank {r['rank']}): parked from {r.get('parked_from', r['state'])}; "
                 + ("; ".join(r.get("reasons") or []) or "no open reason"))
    L += ["", "## Options", "",
          "1. **Fix and re-admit**: name the root cause; the worker publishes a fresh id with `lineage_reset: "
          f"{len(p['fails'])}` in the manifest (failures are then counted from zero).",
          "2. **Re-scope**: change the row (smaller shape, different lane/model, relaxed gate) under a new `lineage`.",
          "3. **Drop**: withdraw every id (`ready/<id>.withdrawn`) and remove the backlog-priority entry.", ""]
    return "\n".join(L)


def render(w: str, data: dict) -> str:
    d = data["workers"][w]
    L = [f"# BACKLOG-{w} — the one backlog (auto-generated {data['generated_at']}; regenerated every 10 min, do not edit)",
         "", (f"Goal: briefs/HANDOFF-{w[8:]}.md (session-per-handoff pilot; handoff {data.get('pilots', {}).get(w[8:])})."
              if w.startswith("handoff-") else f"Goal: GOAL-{w}.md.") + " Work top to bottom. A blocked row's unblocking tasks are non-inference work: do them,",
         "then prepare the launcher, then let the keeper qualify it (the dry run), then it is armed. Repeat until nothing is blocked.", ""]
    counts = {}
    for r in d["rows"]:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    L.append("State counts: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER) + ".")
    for lane in ("cpu", "gpu"):
        if d["qual"][lane] < FLOOR:
            L.append(f"- [FLOOR] {lane.upper()}: {d['qual'][lane]} qualified-armed row(s) < {FLOOR}. Unblock and qualify rows below first.")
    if d.get("starved"):
        L.append("Rule 1: rows in starved lane(s) " + "/".join(x.upper() for x in d["starved"]) + " are listed first.")
    L += ["", "## Inference rows (starved lane first, then priority; parked rows are NOT retried)", ""]
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
    if not w.startswith("handoff-") and data.get("pilots"):
        L += ["", "Piloted handoffs (owned by their own session, excluded here): " + ", ".join(sorted(data["pilots"].values())) + "."]
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


def run_once(flags: str, priority: str, keeper_log: str, out: str, dry_run: bool, update_work: bool = True,
             sessions: str | None = None) -> dict:
    data = build(flags, priority, keeper_log, sessions_path=sessions)
    for w in data["workers"]:
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
    esc = os.path.join(flags, "operator-escalations")
    for lin, p in data["parked"].items():
        dest = os.path.join(esc, re.sub(r"[^A-Za-z0-9_.-]", "_", lin) + ".md")
        if dry_run:
            print(f"===== {dest}")
        else:
            os.makedirs(esc, exist_ok=True)
            write_atomic(dest, escalation_md(lin, p, data["generated_at"]))
    summary = {w: {"rows": len(data["workers"][w]["rows"]),
                   "blocked": sum(1 for r in data["workers"][w]["rows"] if r["state"] == "blocked"),
                   "qual": data["workers"][w]["qual"],
                   "parked": sum(1 for r in data["workers"][w]["rows"] if r["state"] == "parked")} for w in data["workers"]}
    print(data["generated_at"], json.dumps(summary, sort_keys=True))
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    ap.add_argument("--priority", default=PRIORITY_DEFAULT)
    ap.add_argument("--keeper-log", default=None)
    ap.add_argument("--out", default=None, help="where BACKLOG-*.md go (default: --flags)")
    ap.add_argument("--sessions", default=None, help="handoff-sessions registry (default: <flags>/handoff-sessions.json)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-work-section", action="store_true", help="do not refresh the WORK-*-code.md section")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    a = ap.parse_args(argv)
    klog = a.keeper_log or os.path.join(a.flags, "ws58-calendar-keeper.log")
    out = a.out or a.flags
    while True:
        try:
            run_once(a.flags, a.priority, klog, out, a.dry_run, not a.no_work_section, a.sessions)
        except Exception as e:  # never die in the loop
            print(_dt.datetime.now(_dt.timezone.utc).strftime("%FT%TZ"), "backlog_gen error:", repr(e), file=sys.stderr)
        if not a.loop:
            break
        time.sleep(a.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())

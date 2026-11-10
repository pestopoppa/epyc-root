#!/usr/bin/env python3
"""backlog_gen.py - generate the backlogs: BACKLOG-codex-gen.md (the single small-task generalist) and
BACKLOG-handoff-<slug>.md (one per handoff session, scripts/coordination/handoff_sessions.py).

Zero-token. Reads (never writes) the READY rows (ready/*.json), the keeper's dry-run records (dryrun/<id>/), the
keeper log, backlog-priority.json, unblocks.json, the WORK-*-code.md task queues and handoff-sessions.json; writes
BACKLOG-*.md (atomic replace) and refreshes the BLOCKED-INFERENCE section of WORK-codex-gen-code.md.

    python3 backlog_gen.py                       # one pass
    python3 backlog_gen.py --dry-run             # print, write nothing
    python3 backlog_gen.py --loop [--interval 600]
    python3 backlog_gen.py --flags DIR --priority FILE --keeper-log FILE --out DIR   # fixtures / tests

OBJECTIVE (operator, 2026-11-01): unblock the maximum number of inference rows as quickly as possible so every lane
always has ready work. Non-inference tasks are therefore RANKED, not listed in file order:
    score(task) = sum over the inference rows it unblocks (transitively through `unblocks:` links, through
                  backlog-priority.json `unblocks` arrays and through unblocks.json) of lane_weight(row.lane)
    lane_weight(lane) = 1 / (1 + ready rows in that lane)        ready = grantable / armed / running, host-wide;
                                                                   the lane with fewest ready rows weighs most (GPU now)
    order = (-score, effort S<M<L<unsized, best rank of the rows unblocked, file order)
A task that unblocks nothing sorts after every task that unblocks something. Effort is the WORK size tag [S]/[M]/[L].

Row states (epyc.row.v3, scripts/coordination/rowflow/rowflow.py is the one source):
    needs-launcher       backlog-priority inference_prep entry with blocker "missing launcher", no row yet
    needs-qualification  row published, no dry run yet for the current launcher (keeper runs it when the lane is free)
    blocked              the dry run FAILED (dryrun/<id>/FAIL-n.json = the owner's one fix task), the dry run is running,
                         a legacy manifest needs `rowflow.py publish --migrate`, or a `blocked_by` entry is open
    parked               >= MAX_FAILS failed dry runs in the lineage (operator-escalations/<lineage>.md), or >= MAX_FAILS
                         consecutive arming/launch failures since its PASS (operator-escalations/<id>.arming.md); nobody retries
    qualified-armed      dry run PASSED and the launcher is unchanged (grantable / poller armed); writers grant it
    running              grants/<id>.grant open, NO grants/<id>.ended|.complete, and the recorded launcher/poller pid (armed
                         record or queue line) is alive; a grant whose pid is dead or whose .ended exists is never "running"
                         (2026-11-01 bug: an HSF row showed running while grants/<id>.ended said rc=1)
    done                 grants/<id>.ended|.complete or filing-done/<id>.FILED

Handoffs that NEED A SESSION (no entry in handoff-sessions.json) are ranked the same way, for the dispatcher's auto-start
and the "Routed elsewhere" section: handoff_score = sum of lane_weight over the DISTINCT advanceable inference rows that
the handoff's tasks unblock (its WORK lines, transitively) plus the advanceable rows whose fix task points into it
(handoff_task / unblock tasks); ties - including score 0 - break on handoffs/active/backlog-priority.json rank of the
handoff's index row (handoffs/active/.index-state.json row_id), then best row rank; NEVER alphabetically.

Workers (operator, 2026-11-01): the ni / refactor / codex3 Codex sessions are CLOSED. `codex-gen` is the single
always-open generalist and takes SMALL tasks only ([S], no `[too-big:` note); every other task is routed to the
handoff session that owns its handoff file (BACKLOG-handoff-<slug>.md) or, when no session exists, listed under
"needs a handoff session" so the dispatcher/ws58 can start one. Legacy WORK-ni/-refactor/-codex3-code.md queues are
still read and routed the same way (nothing is lost).
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
GENERALIST = "codex-gen"
WORKERS = (GENERALIST,)
LEGACY_QUEUES = ("ni", "refactor", "codex3")  # closed sessions whose WORK-*-code.md queues are re-routed
FLOOR = 2
# Governing objective (operator 2026-11-01 23:30Z): compute capacity must be the ONLY bottleneck. Ready rows per lane
# should be >= INVENTORY_FACTOR x the lane's capacity. The target is a PRIORITY ORDER (deficit lanes' blockers first),
# NEVER a stop condition: blockers are processed whether or not rows are queued or running.
LANE_CAPACITY = {"cpu": 4, "gpu": 1, "host": 1}   # cpu quarters, MI210, whole host
INVENTORY_FACTOR = 2
B_MARK, E_MARK = "<!-- BLOCKED-INFERENCE:start -->", "<!-- BLOCKED-INFERENCE:end -->"
STATE_ORDER = {"blocked": 0, "needs-launcher": 1, "needs-qualification": 2, "parked": 3,
               "qualified-armed": 4, "running": 5, "needs-filing": 6, "done": 7}
FILING_FLOW_START = 1793491200.0  # 2026-11-01T00:00:00Z: rows ended before the owner-files-its-own-results flow are not owed a receipt
ADVANCEABLE = ("blocked", "needs-launcher", "needs-qualification")
MAX_FAILS = 3
SIZE_ORDER = {"S": 0, "M": 1, "L": 2}
_STEM_SUFFIX = re.compile(r"(?:[-_](?:\d{8}(?:T\d{4,6}Z?)?|v\d+|r\d+|rearm|retry\d*|try\d+))+$", re.I)
_TOO_BIG = re.compile(r"\[too-big:", re.I)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rowflow"))
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import handoff_ref  # noqa: E402  (beside this file in the repo and in bin/)
try:
    import rowflow as _rf
except ImportError:  # bundle without rowflow beside it: every v3 row shows as needs-qualification
    _rf = None


def id_stem(rid: str) -> str:
    s = _STEM_SUFFIX.sub("", rid or "")
    return s or rid


def lane_of(d: dict) -> str:
    if d.get("lane") in ("cpu", "gpu"):
        return d["lane"]
    regs = str(d.get("regions", ""))
    if d.get("gpu_quiet") or "mi210" in regs or "gpu" in regs:
        return "gpu"
    if regs.strip() in ("0-95",) or "whole" in regs:
        return "host"
    return "cpu"


def fold_keeper_log(path: str, tail: int = 6000) -> dict:
    """Ids the keeper queued / armed recently and the last ROW-ARM failure text (informational only)."""
    st = {"armed": set(), "idle": [], "arm_fail": {}}
    try:
        lines = open(path, errors="replace").readlines()[-tail:]
    except OSError:
        return st
    for l in lines:
        m = re.match(r"^(\S+) (ROW-ARM|IDLE-ALARM|DRYRUN-RESULT) (.*)$", l.strip())
        if not m:
            continue
        ts, ev, rest = m.groups()
        if ev == "IDLE-ALARM":
            mm = re.search(r": (\S+)$", rest)
            if mm:
                st["idle"].append((ts, mm.group(1)))
        elif ev == "ROW-ARM":
            mm = re.match(r"ARMED (\S+)", rest)
            if mm:
                st["armed"].add(mm.group(1))
            mm = re.match(r"fail: (.*)", rest)
            if mm:
                st["arm_fail"][ts] = mm.group(1)[:200]
    return st


def load_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def load_pilots(path: str | None) -> dict[str, dict]:
    """slug -> {handoff, ids, rows} for every piloted handoff not marked done."""
    reg = load_json(path) if path else None
    out = {}
    for slug, e in ((reg or {}).get("sessions") or {}).items():
        if not isinstance(e, dict) or e.get("status") in ("done", "retired") or not e.get("handoff"):
            continue
        out[slug] = {"handoff": "handoffs/" + str(e["handoff"]).split("handoffs/", 1)[-1],
                     "ids": set(e.get("row_ids") or []),
                     "rows": set(e.get("handoff_rows") or []),
                     # a LIVE owner is one that is running or will be resumed for new work; yielded/failed sessions are not
                     "live": e.get("status") in ("live", "suspended", "unpushed", "retry") and not e.get("yield")}
    return out


def handoff_file(handoff_task) -> str:
    """'handoffs/active/x.md:ROW' | 'x.md' -> 'x.md' (the file a row belongs to); '' when it names no .md file."""
    return handoff_ref.file_of(handoff_task) or ""


def pilot_of(pilots: dict, rid: str, row_id: str | None = None, handoff: str | None = None) -> str | None:
    """A row belongs to its HANDOFF (operator 2026-11-02): the session whose handoff is the row's handoff_task file.
    row_ids / handoff_rows stay only as the fallback for old rows published without a handoff file."""
    hf = handoff_file(handoff)
    if hf:
        for slug, p in pilots.items():
            if os.path.basename(p["handoff"]) == hf:
                return slug
    for slug, p in pilots.items():
        if rid in p["ids"] or (row_id and row_id in p["rows"]):
            return slug
    return None


def parse_work_lines(path: str, source: str) -> list[dict]:
    """Task lines of a WORK-*-code.md (outside the BLOCKED-INFERENCE section). The status bracket may be any text
    (`[S]`, `[M]`, `[source-published; owner deployment pending]`...): a non-size bracket means unsized."""
    out = []
    try:
        s = open(path, errors="replace").read()
    except OSError:
        return out
    s = re.sub(re.escape(B_MARK) + r".*?" + re.escape(E_MARK) + r"\n*", "", s, flags=re.S)
    for l in s.splitlines():
        m = re.match(r"- \[([^\]]+)\] (\S+?):(\d+) — (.*)$", l)
        if not m:
            continue
        tag, f, ln, text = m.groups()
        size = tag.strip() if tag.strip() in SIZE_ORDER else "?"
        ub = re.search(r"\[unblocks:\s*([^\]]+)\]", text)
        unblocks = [x.strip() for x in ub.group(1).split(",") if x.strip()] if ub else []
        done = bool(re.match(r"- \[x\]", l, re.I)) or "[done:" in text.lower()
        out.append({"size": size, "file": f, "line": int(ln), "text": text.strip(), "unblocks": unblocks, "raw": l,
                    "too_big": bool(_TOO_BIG.search(text)), "source": source, "done": done})
    return out


def _rank_of(desc: str) -> float:
    m = re.search(r"rank (\d+)", desc)
    return float(m.group(1)) if m else 9999.0


def task_key(wl: dict) -> str:
    return f"code [{wl['size']}] {wl['file']}:{wl['line']} — {wl['text'][:160]}"


def _pid_alive(pid) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    try:
        st = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0]
        return st != "Z"
    except OSError:
        return False


def recorded_pid(F: str, rid: str):
    """The launcher/poller pid the calendar recorded for a row: ready/armed/<id>.json `pid`, else a `id|pid|...` line in a
    *.queue file. None when nothing recorded a pid (the grant itself carries none)."""
    a = load_json(F + f"ready/armed/{rid}.json")
    if isinstance(a, dict) and a.get("pid"):
        return a["pid"]
    for q in glob.glob(F + "*.queue"):
        try:
            for l in open(q, errors="replace"):
                f = l.strip().split("|")
                if len(f) > 1 and f[0] == rid and f[1].isdigit():
                    return int(f[1])
        except OSError:
            continue
    return None


def grant_run_state(F: str, rid: str) -> tuple[str | None, str]:
    """(state, reason) from the grant files alone. `done` on .ended/.complete/FILED; `running` only on an open .grant with
    no end record AND a live recorded pid (or no pid recorded anywhere - then the grant is the only evidence);
    `stale-grant` when the recorded pid is dead; None when no grant exists."""
    if os.path.exists(F + f"filing-done/{rid}.FILED"):
        return "done", "filing-done receipt present"
    for term in (".ended", ".complete"):
        ep = F + f"grants/{rid}{term}"
        if os.path.exists(ep):
            try:
                recent = os.path.getmtime(ep) >= FILING_FLOW_START
            except OSError:
                recent = False
            if recent:  # DSH-2: ended but not FILED is owed a filing, not done
                return "needs-filing", f"grants/<id>{term} present, no filing-done/<id>.FILED receipt: the owner files the verdict and touches the receipt"
            return "done", f"grants/<id>{term} present (pre-flow row)"
    if not os.path.exists(F + f"grants/{rid}.grant"):
        return None, ""
    pid = recorded_pid(F, rid)
    if pid is None:
        return "running", "grants/<id>.grant open (no pid recorded; the grant is the only evidence)"
    if _pid_alive(pid):
        return "running", f"grants/<id>.grant open, launcher pid {pid} alive"
    return "stale-grant", f"grants/<id>.grant open but launcher pid {pid} is dead and no .ended exists (grant writer/keeper must end it)"


def row_state_v3(flags: str, rid: str, allrows: dict) -> tuple[str, list[str], dict]:
    """(state, reasons, rowflow status) for an epyc.row.v3 row."""
    F = flags.rstrip("/") + "/"
    gs, greason = grant_run_state(F, rid)
    if gs == "done":
        return "done", [], {}
    if gs == "needs-filing":
        return "needs-filing", ["file: " + greason], {}
    if gs == "stale-grant":
        return "blocked", ["wait (ws58 keeper): " + greason], {}
    if _rf is None:
        if gs == "running":
            return "running", [], {}
        return "needs-qualification", [], {}
    try:
        st = _rf.status(flags, rid, allrows)
    except Exception as e:  # never let one bad row kill the generator
        return "blocked", [f"rowflow status error: {e!r}"], {}
    s = st.get("state")
    if s == "done":
        return "done", [], st
    if s == "running":  # rowflow trusts the open grant; the BACKLOG additionally needs no end record and a live pid
        return ("running", [], st) if gs == "running" else ("blocked", ["wait (ws58 keeper): grant open but " + (greason or "no grant evidence")], st)
    if s in ("grantable", "armed"):
        return "qualified-armed", [], st
    if s == "parked":
        return "parked", [st.get("reason", "")], st
    if s == "failed":
        return "blocked", [st.get("fix_task") or f"dry run failed: {st.get('reason')}"], st
    if s == "dryrun-running":
        return "blocked", ["wait (ws58 keeper): " + str(st.get("reason"))], st
    return "needs-qualification", [], st


HANDOFF_RX = re.compile(r"handoffs/active/[A-Za-z0-9._-]+\.md")


def handoff_file_of(text: str) -> str | None:
    m = HANDOFF_RX.search(str(text or ""))
    return m.group(0) if m else None


INFER_RX = re.compile(r"llama-bench|bench(?:mark)?(?:\s+run|ing|\b)|measure|\bt/s\b|tok(?:ens?)?/s|sweep|dry[- ]run|re-?run|"
                      r"\brun (?:the|a|an|it|this|one|two|three|n=|\d)|publish_row|profil(?:e|ing) run|latency|throughput|"
                      r"correctness (?:run|check|gate)|A/B|ablat|baseline", re.I)
GPU_RX = re.compile(r"MI210|\bGPU\b|gfx90a|HIP|VRAM|rocm", re.I)
CANDIDATE_CAP = 8
CANDIDATE_WEIGHT = 0.5  # an unpublished inference task is half a row: it still needs a spec, a launcher and a dry run


def handoff_inference_tasks(repo: str, hf: str, cap: int = CANDIDATE_CAP) -> list[dict]:
    """A handoff's OWN unpublished inference tasks: open `- [ ]` boxes whose text reads like a measurement/run. These are
    rows the session can publish, so they count toward the handoff (operator, 2026-11-01: the `unblocks:` graph is
    sparse, most handoffs would otherwise score 0). Capped (CANDIDATE_CAP) and half-weighted (CANDIDATE_WEIGHT) so a
    huge handoff of unpublished ideas cannot outrank one with real stuck rows."""
    out = []
    try:
        lines = open(os.path.join(repo, hf), errors="replace").read().splitlines()
    except OSError:
        return out
    for i, l in enumerate(lines, 1):
        if not re.match(r"^\s*- \[ \]", l):
            continue
        if INFER_RX.search(l):
            out.append({"line": i, "text": re.sub(r"^\s*- \[ \]\s*", "", l)[:140], "lane": "gpu" if GPU_RX.search(l) else "cpu"})
            if len(out) >= cap:
                break
    return out


def handoff_priority(priority_path: str, prows: dict) -> tuple[dict[str, dict], dict[str, str]]:
    """(handoff file -> {row_id, rank}, index row id -> handoff file). The handoff's index row comes from
    handoffs/active/.index-state.json (beside backlog-priority.json); the rank is that row's backlog-priority rank
    (lower = more urgent; 9999 = unranked)."""
    idx = load_json(os.path.join(os.path.dirname(os.path.abspath(priority_path)), ".index-state.json")) or {}
    out, row_handoff = {}, {}
    for rid, r in (idx.get("rows") or {}).items():
        if isinstance(r, dict) and r.get("handoff"):
            row_handoff[rid] = "handoffs/active/" + str(r["handoff"]).split("/")[-1]
    for base, h in (idx.get("handoffs") or {}).items():
        if not isinstance(h, dict):
            continue
        rid = h.get("row_id")
        r = prows.get(rid) if rid else None
        rank = r.get("rank") if isinstance(r, dict) and isinstance(r.get("rank"), (int, float)) else 9999
        out["handoffs/active/" + base] = {"row_id": rid, "rank": float(rank)}
        if rid:
            row_handoff.setdefault(rid, "handoffs/active/" + base)
    return out, row_handoff


def build(flags: str, priority_path: str, keeper_log: str, now: _dt.datetime | None = None,
          sessions_path: str | None = None) -> dict:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    F = flags.rstrip("/") + "/"
    pri = load_json(priority_path) or {}
    prows = pri.get("rows") or {}
    hpri, row_handoff = handoff_priority(priority_path, prows)
    prep = pri.get("inference_prep") or []
    unblocks_map = load_json(F + "unblocks.json") or {}
    klog = fold_keeper_log(keeper_log)
    pilots = load_pilots(sessions_path if sessions_path is not None else F + SESSIONS_NAME)
    buckets = [GENERALIST] + [f"handoff-{s}" for s in pilots]
    _reg = load_json(sessions_path if sessions_path is not None else F + SESSIONS_NAME) or {}
    failed_sessions = {s: e.get("failed") for s, e in (_reg.get("sessions") or {}).items() if isinstance(e, dict) and e.get("failed")}
    stuck_sessions = {s: e.get("stuck") for s, e in (_reg.get("sessions") or {}).items() if isinstance(e, dict) and e.get("stuck")}

    # non-inference backlog-priority rows: row-id -> task descriptions, and task-id -> row ids (for scoring)
    unblockers_by_row: dict[str, list[str]] = {}
    pri_unblocks: dict[str, list[str]] = {}
    for rid, r in prows.items():
        if r.get("kind") == "non-inference":
            pri_unblocks[rid] = list(r.get("unblocks") or [])
            for tgt in pri_unblocks[rid]:
                unblockers_by_row.setdefault(tgt, []).append(f"{rid} (T{r.get('tier')} rank {r.get('rank')}): {r.get('basis', '')[:140]}")

    per: dict[str, dict] = {w: {"rows": [], "code": [], "routed": [], "qual": {"cpu": 0, "gpu": 0, "host": 0}} for w in buckets}
    all_lines: list[dict] = []
    for src in (GENERALIST,) + LEGACY_QUEUES:
        all_lines += parse_work_lines(F + f"WORK-{src}-code.md", src)
    all_lines = [wl for wl in all_lines if not wl["done"]]
    seen_ids = set()

    # ---- inference rows ----
    allrows = {}
    if _rf is not None:
        try:
            allrows = _rf.rows(F)
        except Exception:
            allrows = {}
    rows_by_handoff_row: dict[str, list[dict]] = {}

    def tasks_for(rid: str, row_id: str | None, reasons: list[str], w: str, placeholder: bool = True) -> list[str]:
        t = []
        for r in reasons:
            if r:
                t.append(r if r.startswith("wait (") else "fix: " + r)
        for wl in all_lines:
            if rid in wl["unblocks"] or (row_id and row_id in wl["unblocks"]):
                t.append(task_key(wl))
        for key, ids in unblocks_map.items():
            if rid in ids or (row_id and row_id in ids):
                t.append("code " + key[:180])
        if row_id:
            t += ["code " + x for x in sorted(unblockers_by_row.get(row_id, []), key=_rank_of)[:3]]
        if not t and placeholder:
            t.append("(no unblocking task filed yet — file one with `unblocks: " + rid + "`)")
        return t

    def bucket_for(rid, row_id, handoff):
        slug = pilot_of(pilots, rid, row_id, handoff)
        return f"handoff-{slug}" if slug else GENERALIST

    for p in sorted(glob.glob(F + "ready/*.json")):
        d = load_json(p)
        if not isinstance(d, dict):
            continue
        rid = d.get("id") or os.path.basename(p)[:-5]
        if rid in seen_ids or os.path.exists(F + f"ready/{rid}.withdrawn"):
            continue
        seen_ids.add(rid)
        lane = lane_of(d)
        v3 = d.get("schema") == "epyc.row.v3"
        reasons: list[str] = []
        st = {}
        if v3:
            state, reasons, st = row_state_v3(F, rid, allrows)
            for b in d.get("blocked_by") or []:
                reasons.append(str(b)[:160])
            if reasons and state in ("needs-qualification", "qualified-armed"):
                state = "blocked"
        else:
            gs, greason = grant_run_state(F, rid)
            if gs == "done":
                state = "done"
            elif gs == "needs-filing":
                state = "needs-filing"
                reasons.append("file: " + greason)
            elif gs == "running":
                state = "running"
            elif gs == "stale-grant":
                state = "blocked"
                reasons.append("wait (ws58 keeper): " + greason)
            else:
                state = "blocked"
                reasons.append(f"legacy manifest (schema {d.get('schema') or 'unset'}): migrate with "
                               f"`python3 scripts/coordination/rowflow/rowflow.py publish --migrate {F}ready/{rid}.json` "
                               "(fills result_path/decision_rule if the manifest lacks them; repoints the engine to filler_run15.sh in a new launch.v15.sh)")
        prep_entry = next((e for e in prep if e.get("filler") == rid), None)
        row_id = (prep_entry or {}).get("row") or d.get("row") or (str(d.get("handoff_task") or "").split(":")[-1] if v3 else None)
        hfile = handoff_file_of(d.get("handoff") or d.get("handoff_task")) or row_handoff.get(row_id or "")
        w = bucket_for(rid, row_id, d.get("handoff") or (str(d.get("handoff_task") or "").split(":")[0] if v3 else None))
        if state == "qualified-armed":
            per[w]["qual"][lane] += 1
        rec = {"id": rid, "lane": lane, "rank": d.get("priority_rank") or (prep_entry or {}).get("rank") or 999,
               "state": state, "row": row_id, "reasons": reasons, "cause": ("keeper" if any(r.startswith("wait (") for r in reasons) else "worker") if state == "blocked" else "",
               "tasks": tasks_for(rid, row_id, reasons, w) if state == "blocked" else [],
               "lineage": st.get("lineage") or id_stem(rid), "lineage_fails": st.get("lineage_fails", 0), "owner": d.get("owner"),
               "handoff": hfile}
        per[w]["rows"].append(rec)
        if row_id:
            rows_by_handoff_row.setdefault(row_id, []).append(rec)

    for e in prep:  # inference_prep entries with no row yet
        rid = e.get("filler") or e.get("row")
        if not rid or rid in seen_ids or os.path.exists(F + f"ready/{rid}.withdrawn"):
            continue
        seen_ids.add(rid)
        w = bucket_for(rid, e.get("row"), e.get("handoff"))
        blocker = str(e.get("blocker") or "")
        gs0 = grant_run_state(F, rid)[0]
        if gs0 in ("done", "needs-filing"):
            state = gs0
        else:
            state = "needs-launcher" if re.search(r"missing launcher", blocker, re.I) else "blocked"
        rec = {"id": rid, "lane": e.get("lane") if e.get("lane") in ("cpu", "gpu") else "cpu", "rank": e.get("rank") or 999,
               "state": state, "row": e.get("row"), "reasons": [blocker[:200]] if blocker else [], "cause": "worker" if state == "blocked" else "",
               "tasks": (tasks_for(rid, e.get("row"), [blocker[:200]] if state == "blocked" else [], w) if state == "blocked"
                         else (["write the launcher on filler_run15.sh, then `publish_row.py <spec.json>` (id, owner, launcher, lane, result_path, decision_rule, estimate_s, handoff_task)"]
                               + tasks_for(rid, e.get("row"), [], w, placeholder=False)) if state == "needs-launcher" else []),
               "lineage": id_stem(rid), "lineage_fails": 0, "owner": e.get("owner"),
               "handoff": handoff_file_of(e.get("handoff")) or row_handoff.get(e.get("row") or "")}
        per[w]["rows"].append(rec)
        if e.get("row"):
            rows_by_handoff_row.setdefault(e["row"], []).append(rec)

    # ---- one owner per row (2026-11-01 bug: a blocked row sat in codex-gen while its fix task sat in a session's
    # backlog, so codex-gen stalled on "routed" work and nobody owned the row). A codex-gen row moves to the session whose
    # handoff file holds a task that unblocks it, or whose index row (inference_prep `row`) maps to a piloted handoff. ----
    handoff_bucket0 = {p["handoff"]: f"handoff-{slug}" for slug, p in pilots.items() if p["live"]}
    for rec in list(per[GENERALIST]["rows"]):
        tgt = handoff_bucket0.get(rec.get("handoff") or "")
        if not tgt:
            for wl in all_lines:
                if (rec["id"] in wl["unblocks"] or (rec.get("row") and rec["row"] in wl["unblocks"])) and wl["file"] in handoff_bucket0:
                    tgt = handoff_bucket0[wl["file"]]
                    break
        if tgt and tgt != GENERALIST:
            per[GENERALIST]["rows"].remove(rec)
            per[tgt]["rows"].append(rec)
            rec["routed_to"] = tgt
            if rec["state"] == "qualified-armed":
                per[GENERALIST]["qual"][rec["lane"]] -= 1
                per[tgt]["qual"][rec["lane"]] += 1
        else:
            rec["owner_note"] = "yours (no handoff session)"
    # an item belongs to a handoff session only while that session is live or will be resumed for it (operator 22:40Z):
    # a yielded/failed session's actionable rows (fix tasks, filing) go to codex-gen so nothing is orphaned
    for slug, p in pilots.items():
        if p["live"]:
            continue
        w = f"handoff-{slug}"
        for rec in list(per[w]["rows"]):
            if rec["state"] in ADVANCEABLE or rec["state"] == "needs-filing":
                per[w]["rows"].remove(rec)
                per[GENERALIST]["rows"].append(rec)
                rec["owner_note"] = f"yours (owner session {slug} is yielded/absent)"

    # ---- parked lineages (escalation notes are written by rowflow; this only reports them) ----
    parked: dict[str, dict] = {}
    for w in buckets:
        for r in per[w]["rows"]:
            if r["state"] == "parked":
                parked.setdefault(r["lineage"], {"worker": w, "rows": []})["rows"].append(r)

    # ---- lane weights: host-wide ready rows per lane ----
    ready_by_lane = {"cpu": 0, "gpu": 0, "host": 0}
    for w in buckets:
        for r in per[w]["rows"]:
            if r["state"] in ("qualified-armed", "running"):
                ready_by_lane[r["lane"]] += 1

    inventory = {ln: {"ready": ready_by_lane.get(ln, 0), "target": INVENTORY_FACTOR * cap,
                      "deficit": max(0, INVENTORY_FACTOR * cap - ready_by_lane.get(ln, 0))} for ln, cap in LANE_CAPACITY.items()}

    def lane_weight(lane: str) -> float:
        return 1.0 / (1 + ready_by_lane.get(lane, 0))

    def deficit_weight(lane: str) -> float:  # inventory target = priority order: rows for a lane below target rank first
        return lane_weight(lane) if inventory.get(lane, {}).get("deficit", 0) else 0.0

    # ---- scoring: rows each task unblocks, transitively ----
    advanceable = {r["id"]: r for w in buckets for r in per[w]["rows"] if r["state"] in ADVANCEABLE}
    by_key = {task_key(wl): wl for wl in all_lines}
    lines_by_target: dict[str, list[dict]] = {}
    for wl in all_lines:
        for tgt in wl["unblocks"]:
            lines_by_target.setdefault(tgt, []).append(wl)

    def rows_unblocked(wl: dict, depth: int = 0, seen: set | None = None) -> dict[str, dict]:
        seen = seen if seen is not None else set()
        out: dict[str, dict] = {}
        targets = list(wl["unblocks"])
        targets += [t for key, ids in unblocks_map.items() if key[:180] in wl["text"] or wl["text"][:80] in key for t in ids]
        for tgt in targets:
            if tgt in seen or depth > 6:
                continue
            seen.add(tgt)
            if tgt in advanceable:
                out[tgt] = advanceable[tgt]
            for rr in rows_by_handoff_row.get(tgt, []):
                if rr["state"] in ADVANCEABLE:
                    out[rr["id"]] = rr
            for rr_id in pri_unblocks.get(tgt, []):  # backlog-priority non-inference id -> handoff rows it unblocks
                for rr in rows_by_handoff_row.get(rr_id, []):
                    if rr["state"] in ADVANCEABLE:
                        out[rr["id"]] = rr
            if tgt in by_key:  # task -> task edge (key of another WORK line)
                out.update(rows_unblocked(by_key[tgt], depth + 1, seen))
            for other in all_lines:  # task -> task by file:line reference
                if f"{other['file']}:{other['line']}" == tgt and other is not wl:
                    out.update(rows_unblocked(other, depth + 1, seen))
        return out

    scored = []
    for i, wl in enumerate(all_lines):
        ub = rows_unblocked(wl)
        wl["unblocked_rows"] = sorted(ub)
        wl["score"] = round(sum(lane_weight(r["lane"]) for r in ub.values()), 4)
        wl["deficit_score"] = round(sum(deficit_weight(r["lane"]) for r in ub.values()), 4)
        wl["best_rank"] = min([float(r["rank"]) if str(r["rank"]).replace(".", "", 1).isdigit() else 999 for r in ub.values()] + [999])
        wl["order"] = (-wl["deficit_score"], -wl["score"], SIZE_ORDER.get(wl["size"], 3), wl["best_rank"], i)
        scored.append(wl)
    scored.sort(key=lambda x: x["order"])

    # ---- routing: small -> codex-gen; everything else -> the handoff session owning the file, else "needs a session" ----
    handoff_bucket = {p["handoff"]: f"handoff-{slug}" for slug, p in pilots.items()}
    rows_by_id = {r["id"]: r for w in buckets for r in per[w]["rows"]}
    # ---- handoffs that need a session: score = lane-weighted DISTINCT advanceable rows the handoff's tasks unblock ----
    hs_rows: dict[str, dict[str, dict]] = {}   # handoff file -> {row id -> rec}
    hs_tasks: dict[str, list[dict]] = {}
    for wl in scored:
        if wl["file"] in handoff_bucket or not HANDOFF_RX.fullmatch(wl["file"]):
            continue
        hs_tasks.setdefault(wl["file"], []).append(wl)
        for rid in wl["unblocked_rows"]:
            if rid in rows_by_id:
                hs_rows.setdefault(wl["file"], {})[rid] = rows_by_id[rid]
    for r in advanceable.values():  # a stuck row's fix task belongs to its owning handoff; unblock tasks that point into one count too
        targets = {r.get("handoff")} if r.get("handoff") else set()
        for t in r["tasks"]:
            hf = handoff_file_of(t)
            if hf:
                targets.add(hf)
        for hf in targets:
            if hf not in handoff_bucket:
                hs_rows.setdefault(hf, {})[r["id"]] = r
    # ---- the same ranking for EVERY handoff (with or without a session): the dispatcher yields slots by it ----
    for w in buckets:  # rows owned by piloted handoffs count for their handoff too
        for r in per[w]["rows"]:
            if r["state"] in ADVANCEABLE and r.get("handoff"):
                hs_rows.setdefault(r["handoff"], {})[r["id"]] = r
    for wl in scored:
        if wl["file"] in handoff_bucket:
            hs_tasks.setdefault(wl["file"], []).append(wl)
            for rid in wl["unblocked_rows"]:
                if rid in rows_by_id:
                    hs_rows.setdefault(wl["file"], {})[rid] = rows_by_id[rid]
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(priority_path))))
    handoff_rank = []
    for hf in set(hs_rows) | set(hs_tasks) | set(handoff_bucket) | set(hpri):
        rr = hs_rows.get(hf, {})
        cand = handoff_inference_tasks(repo, hf)
        if not rr and not cand and not hs_tasks.get(hf) and hf not in handoff_bucket:
            continue  # nothing to do in it
        pr = hpri.get(hf, {"row_id": None, "rank": 9999.0})
        best = min([float(r["rank"]) if str(r["rank"]).replace(".", "", 1).isdigit() else 999 for r in rr.values()] + [999])
        handoff_rank.append({"handoff": hf, "score": round(sum(lane_weight(r["lane"]) for r in rr.values())
                                                           + CANDIDATE_WEIGHT * sum(lane_weight(c["lane"]) for c in cand), 4),
                             "deficit_score": round(sum(deficit_weight(r["lane"]) for r in rr.values())
                                                    + CANDIDATE_WEIGHT * sum(deficit_weight(c["lane"]) for c in cand), 4),
                             "rows": sorted(rr), "lanes": sorted({r["lane"] for r in rr.values()} | {c["lane"] for c in cand}),
                             "candidate_rows": len(cand), "candidates": cand[:4],
                             "row_id": pr["row_id"], "priority_rank": pr["rank"], "best_row_rank": best,
                             "tasks": len(hs_tasks.get(hf, [])), "session": handoff_bucket.get(hf, "")[8:] or None})
    # order: most inference unblocked/publishable first; ties (incl. score 0) by backlog-priority rank of the handoff's
    # index row, then the best rank among its rows, then task count. Never alphabetical.
    handoff_rank.sort(key=lambda h: (-h["deficit_score"], -h["score"], h["priority_rank"], h["best_row_rank"], -h["tasks"], h["handoff"]))
    for i, h in enumerate(handoff_rank, 1):
        h["position"] = i
    needs_session = [h for h in handoff_rank if not h["session"]]
    hs_order = {h["handoff"]: i for i, h in enumerate(needs_session)}
    live_bucket = {p["handoff"]: f"handoff-{slug}" for slug, p in pilots.items() if p["live"]}
    for wl in scored:
        tgt = handoff_bucket.get(wl["file"])
        small = wl["size"] == "S" and not wl["too_big"]
        if small and (tgt is None or tgt not in live_bucket.values() or wl["source"] == GENERALIST or not wl["unblocked_rows"]):
            # ONE owner: a small task is codex-gen's unless its handoff session is live and the task unblocks that session's rows
            if tgt and tgt not in live_bucket.values():
                wl["route_note"] = f"yours ({tgt[8:]} session yielded/absent)"
            per[GENERALIST]["code"].append(wl)
        elif tgt:
            per[tgt]["code"].append(wl)
        else:
            wl["route"] = "needs a handoff session for " + wl["file"]
            per[GENERALIST]["routed"].append(wl)
    per[GENERALIST]["routed"].sort(key=lambda wl: (hs_order.get(wl["file"], 10**6), wl["order"]))

    for w in buckets:
        starved = {ln for ln in ("cpu", "gpu") if ready_by_lane[ln] < FLOOR}
        per[w]["starved"] = sorted(starved)

        def _key(r):
            rank = float(r["rank"]) if str(r["rank"]).replace(".", "", 1).isdigit() else 999
            if r["state"] in ADVANCEABLE:  # rule 1: starved lane first (fewest ready rows first), then priority
                return (0, ready_by_lane.get(r["lane"], 0), rank, STATE_ORDER[r["state"]])
            return (1, STATE_ORDER[r["state"]], rank, 0)
        per[w]["rows"].sort(key=_key)
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%MZ"), "workers": per, "parked": parked,
            "pilots": {s: p["handoff"] for s, p in pilots.items()}, "ready_by_lane": ready_by_lane, "klog_idle": klog["idle"][-3:],
            "needs_session": needs_session, "handoff_rank": handoff_rank, "failed_sessions": failed_sessions, "inventory": inventory, "stuck_sessions": stuck_sessions}


def render(w: str, data: dict) -> str:
    d = data["workers"][w]
    rbl = data["ready_by_lane"]
    if w.startswith("handoff-"):
        goal = f"Goal: briefs/HANDOFF-{w[8:]}.md (session-per-handoff; handoff {data.get('pilots', {}).get(w[8:])})."
    else:
        goal = f"Goal: GOAL-{w}.md (SMALL tasks only; `[too-big: why]` re-routes a task to its handoff session)."
    L = [f"# BACKLOG-{w} — the one backlog (auto-generated {data['generated_at']}; regenerated every 10 min, do not edit)", "",
         goal + " Work top to bottom.",
         f"Ready rows host-wide: cpu={rbl['cpu']} gpu={rbl['gpu']} host={rbl['host']} (lane weight = 1/(1+ready); the emptiest lane counts most).", ""]
    counts = {}
    for r in d["rows"]:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    L.append("State counts: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in STATE_ORDER) + ".")
    if w.startswith("handoff-"):
        ss = (data.get("stuck_sessions") or {}).get(w[8:])
        if ss:
            L.append(f"- [stuck: {ss}] — the dispatcher resumes this session only on a run-end or a new external event; codex-gen/operator: see why")
        fs = (data.get("failed_sessions") or {}).get(w[8:])
        if fs:
            L.append(f"- [FAILED] session: {fs} — the dispatcher stopped retrying (DSH-3); ws58 transfers or restarts it.")
        hr = next((h for h in data.get("handoff_rank", []) if h.get("session") == w[8:]), None)
        if hr:
            L.append(f"Handoff rank: #{hr['position']} of {len(data['handoff_rank'])} (score={hr['score']}, rows={len(hr['rows'])}, "
                     f"own unpublished inference tasks={hr['candidate_rows']}). Below the live cap the dispatcher yields your slot after your next wrap-up.")
        L += ["", "**Inference first.** Turn this handoff's measurement/inference tasks into published rows (`publish_row.py`), "
              "fastest-clearable blockers first, so every lane always has runnable rows; non-inference tasks come after that or while your rows wait."]
        if hr and hr.get("candidates"):
            L.append("Own inference tasks to publish as rows (open boxes that read like a run; verify in the handoff):")
            for c in hr["candidates"]:
                L.append(f"- {w[8:]} L{c['line']} [{c['lane']}] {c['text']}")
    for lane in ("cpu", "gpu"):
        if rbl[lane] < FLOOR:
            L.append(f"- [FLOOR] {lane.upper()}: {rbl[lane]} ready row(s) host-wide < {FLOOR}. Tasks that unblock a {lane.upper()} row rank first.")
    L += ["", "## Inference rows (emptiest lane first, then priority; parked rows are NOT retried)", ""]
    if not d["rows"]:
        L.append("- none")
    for r in d["rows"]:
        if r["state"] == "done":
            continue  # counted above; not work
        L.append(f"- [{r['state']}] {r['lane']} rank={r['rank']} **{r['id']}**" + (f" (row {r['row']})" if r.get("row") else "")
                 + (f" — {r['owner_note']}" if r.get("owner_note") and r["state"] in ADVANCEABLE + ("needs-filing",) else ""))
        if r["state"] == "needs-filing":
            L.append(f"    - file: read result_path, apply decision_rule, tick the handoff, then `touch {FLAGS_DEFAULT}/filing-done/{r['id']}.FILED` (DSH-2)")
        for t in r["tasks"]:
            L.append(f"    - unblock: {t}")
    L += ["", "## Non-inference tasks — ranked by inference rows unblocked (lane-weighted), then effort S<M<L", ""]
    if not d["code"]:
        L.append("- none")
    for wl in d["code"]:
        tag = f"score={wl['score']}" + (f" unblocks={','.join(wl['unblocked_rows'][:4])}" if wl["unblocked_rows"] else "") \
            + (f" {wl['route_note']}" if wl.get("route_note") else "")
        L.append(f"{wl['raw']}  <!-- {tag} -->")
    if d.get("routed"):
        L += ["", "## Routed elsewhere (NOT yours: M/L or `[too-big:]` tasks whose handoff has no session yet — the dispatcher "
              "auto-starts one per handoff, highest score first; ties by backlog-priority rank, never alphabetical)", ""]
        ns = {h["handoff"]: h for h in data.get("needs_session", [])}
        shown_h = set()
        for wl in d["routed"][:60]:
            h = ns.get(wl["file"])
            if h and wl["file"] not in shown_h:
                shown_h.add(wl["file"])
                L.append(f"- **{wl['file']}** — handoff score={h['score']} rows={','.join(h['rows'][:4]) or '-'} "
                         f"own-inference-tasks={h['candidate_rows']} priority={h['row_id'] or '-'} rank={h['priority_rank'] if h['priority_rank'] < 9999 else '-'}")
            L.append(f"    - {wl['route']}: {wl['raw'][:200]}")
        if len(d["routed"]) > 60:
            L.append(f"- ... {len(d['routed']) - 60} more")
    if not w.startswith("handoff-") and data.get("pilots"):
        L += ["", "Piloted handoffs (owned by their own session): " + ", ".join(sorted(data["pilots"].values())) + "."]
    L += ["", "Filing a task that unblocks a row: append `[unblocks: <ready-id>|<handoff-row-id>|<file:line of another task>]` to its line in "
          "WORK-codex-gen-code.md (or the handoff's WORK file), or add it to compute-flags/unblocks.json. See scripts/coordination/backlog_gen.py.", ""]
    return "\n".join(L)


def blocked_section(w: str, data: dict) -> str:
    d = data["workers"][w]
    rbl = data["ready_by_lane"]
    L = [B_MARK, f"## BLOCKED INFERENCE — your backlog is BACKLOG-{w}.md (auto-generated {data['generated_at']}); this section mirrors its blocked rows", ""]
    for lane in ("cpu", "gpu"):
        if rbl[lane] < FLOOR:
            L.append(f"- [FLOOR] {lane.upper()}: only {rbl[lane]} ready row(s) host-wide; keep >={FLOOR}.")
    for r in d["rows"]:
        if r["state"] in ADVANCEABLE:
            L.append(f"- [{r['state'].upper()}] {r['lane']} rank={r['rank']} {r['id']} — " + ("; ".join(r["reasons"]) or r["state"]))
    if len(L) == 3:
        L.append("- none: every row is qualified and runnable.")
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
    summary = {w: {"rows": len(data["workers"][w]["rows"]),
                   "blocked": sum(1 for r in data["workers"][w]["rows"] if r["state"] == "blocked"),
                   "tasks": len(data["workers"][w]["code"]), "routed": len(data["workers"][w].get("routed", [])),
                   "parked": sum(1 for r in data["workers"][w]["rows"] if r["state"] == "parked")} for w in data["workers"]}
    summary["ready_by_lane"] = data["ready_by_lane"]
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


def resume_delta(data: dict, slug: str, limit_rows: int = 8) -> str:
    """CAF-3: the compact per-slug state a resume prompt carries INSTEAD of "re-read the BACKLOG" (read_brief was 22% of
    handoff-session spend). Rows by state with the one-line reason, the next non-inference tasks, the handoff's own
    inference tasks to publish, and the handoff rank. The BACKLOG file remains the full view."""
    w = data["workers"].get(f"handoff-{slug}")
    if not w:
        return "(no backlog bucket for this session yet)"
    L = []
    rows = [r for r in w["rows"] if r["state"] != "done"]
    for r in rows[:limit_rows]:
        why = ("; ".join(r.get("reasons") or [])[:160]) or ""
        L.append(f"- row {r['id']} [{r['state']}, {r['lane']}, rank {r['rank']}]" + (f": {why}" if why else ""))
    if len(rows) > limit_rows:
        L.append(f"- ... {len(rows) - limit_rows} more rows (see BACKLOG-handoff-{slug}.md)")
    if not rows:
        L.append("- rows: none open")
    inv = data.get("inventory") or {}
    L.append("- inventory (ready rows vs target; deficit lanes' blockers come FIRST, never a reason to stop): "
             + ", ".join(f"{ln} {v['ready']}/{v['target']}" for ln, v in inv.items()))
    hr = next((h for h in data.get("handoff_rank", []) if h.get("session") == slug), None)
    if hr:
        L.append(f"- handoff rank #{hr['position']}/{len(data['handoff_rank'])} score={hr['score']}; own inference tasks to publish: "
                 + ("; ".join(f"L{c['line']} [{c['lane']}] {c['text'][:90]}" for c in hr.get("candidates", [])[:3]) or "none detected"))
    for wl in w["code"][:3]:
        L.append(f"- next task: {wl['file']}:{wl['line']} — {wl['text'][:150]}")
    if not w["code"]:
        L.append("- non-inference tasks: none in the backlog")
    return "\n".join(L)

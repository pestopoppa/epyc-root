"""Pipeline page data: the compute loop, the session loop, and who is where in it.

Read-only, stdlib only. Every input is a file the dispatcher / keeper already
writes under ``EPYC_COMPUTE_FLAGS`` (default ``/mnt/raid0/llm/tmp/compute-flags``):

  handoff-sessions.json                    registry (``sessions`` keyed by slug, ``max_live``)
  handoff-sessions/<slug>/report.json      the session's turn report (``next``, ``blocked_by``)
  handoff-sessions.log                     RESUME / TURN-END / PAUSE / NUDGE / ... lines
  grants/<id>.grant | .ended | .complete   a row's grant and its end markers
  ready/<id>.json, dryrun/<id>/PASS|FAIL-n a published row and its dry run
  ws58-calendar-keeper.log                 the last ``SNAPSHOT`` line = free/busy per region

The dispatcher is being rewritten, so field names may move: everything that
decides a session's STEP lives in ``step_of`` (one small function, easy to adjust).
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "epyc.pipeline_status.v1"
REGIONS = ("q0", "q1", "q2", "q3", "gpu-quiet")

#: Step ids, in flowchart order. ``label`` is what the table and diagram show.
STEPS = {
    "queued": "queued (waiting for a slot)",
    "working": "working: non-inference tasks fanned out",
    "making-ready": "making inference rows ready",
    "paused": "paused: blocked only by readied rows",
    "nudged": "nudged: go on with the next step",
    "done": "done: close, take next handoff",
}


#: Who OWNS a step: DET = code (dispatcher / keeper / harness decides), AI = an LLM session
#: does the work. A stalled step shows at once whether to debug code or an agent.
#: queued/paused/nudged/done are the dispatcher's own decisions; working/making-ready are the agent's.
STEP_OWNER = {"queued": "DET", "working": "AI", "making-ready": "AI",
              "paused": "DET", "nudged": "DET", "done": "DET"}


def flags_dir() -> Path:
    return Path(os.environ.get("EPYC_COMPUTE_FLAGS", "/mnt/raid0/llm/tmp/compute-flags"))


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def parse_ts(value) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def pid_alive(pid) -> bool:
    """Liveness via /proc (not kill -0, which is blind here). A zombie is not alive."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return stat.rpartition(")")[2].split()[:1] != ["Z"]


# --------------------------------------------------------------------------- #
# log
# --------------------------------------------------------------------------- #
_LOG_RE = re.compile(r"^(\d{4}-\d\d-\d\dT[\d:]+Z) ([A-Z][A-Z-]+) ([A-Za-z0-9][\w.-]*)")
_RANK_RE = re.compile(r"rank #(\d+)")
#: log kinds that say something about a session's step (the rest are plumbing)
_STEP_KINDS = {"RESUME", "START", "AUTO-START", "TURN-END", "PAUSE", "NUDGE", "YIELD",
               "UNYIELD", "OPEN", "STATE", "STUCK", "NOOP"}


def read_log_tail(path: Path, max_bytes: int = 2_000_000) -> list[str]:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - max_bytes))
            data = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    lines = data.splitlines()
    return lines[1:] if size > max_bytes else lines


def last_log_by_slug(lines: list[str]) -> dict[str, dict]:
    """{slug: {ts, kind, line, rank, event}} - the last step-relevant line per slug."""
    out: dict[str, dict] = {}
    for line in lines:
        m = _LOG_RE.match(line)
        if not m or m.group(2) not in _STEP_KINDS:
            continue
        ts, kind, slug = m.groups()
        ev = re.search(r"\bevent=(\S+)", line)
        rk = _RANK_RE.search(line)
        prev = out.get(slug, {})
        out[slug] = {"ts": ts, "kind": kind, "line": line[len(ts) + 1:][:240],
                     "event": ev.group(1) if ev else None,
                     "rank": int(rk.group(1)) if rk else prev.get("rank")}
    return out


# --------------------------------------------------------------------------- #
# THE step mapping - the one function to adjust when the dispatcher changes
# --------------------------------------------------------------------------- #
def step_of(entry: dict, report: dict | None, live: bool, last: dict | None) -> tuple[str, str]:
    """(step, detail) for one session.

    Report first: ``report['next']`` in {non-inference, inference, blocked, done}.
    Otherwise infer from pid liveness + the last log line for the slug.
    """
    last = last or {}
    nxt = (report or {}).get("next")
    if nxt == "done":
        return "done", "report next=done"
    if nxt == "blocked":
        return "paused", "report next=blocked: " + (", ".join((report or {}).get("blocked_by") or []) or "-")
    if live:
        if nxt == "inference":
            return "making-ready", "report next=inference"
        if nxt == "non-inference":
            return "working", "report next=non-inference"
        ev = last.get("event") or ""
        if last.get("kind") == "NUDGE" or ev.startswith("nudge"):
            return "nudged", last.get("line", "")
        if "inference task" in (entry.get("noop_reason") or ""):
            return "making-ready", entry["noop_reason"]
        return "working", f"live; last log {last.get('kind', '-')} {ev}".strip()
    if last.get("kind") == "PAUSE" or (entry.get("await_event") and entry.get("status") != "live"):
        return "paused", "awaiting a row end or an external event"
    return "queued", last.get("line", "") or "not in a slot"


# --------------------------------------------------------------------------- #
# compute
# --------------------------------------------------------------------------- #
def _rows(flags: Path) -> dict[str, dict]:
    """{row_id: {state, ...}} for every published row that is not finished.

    state: running (grant, no end) | ready (dry run PASS) | dryrun-fail | dryrun-pending
    """
    grants = flags / "grants"
    ended = set()
    try:
        names = os.listdir(grants)
    except OSError:
        names = []
    granted = {}
    for n in names:
        rid, _, ext = n.rpartition(".")
        if ext in ("ended", "complete", "ended-stale-restart"):
            ended.add(rid)
        elif ext == "grant":
            granted[rid] = grants / n
    def _handoff_of(rid: str) -> str | None:
        j = _json(flags / "ready" / f"{rid}.json")
        ht = j.get("handoff_task") if isinstance(j, dict) else None
        h = ht.partition(":")[0] if isinstance(ht, str) and ht else None
        return h if h and h.endswith(".md") else None      # "FILLERS" etc. is not a handoff path

    out: dict[str, dict] = {}
    for rid, p in granted.items():
        if rid in ended:
            continue
        info: dict = {"id": rid, "state": "running", "handoff": _handoff_of(rid)}
        try:
            txt = p.read_text().strip()
            for part in txt.replace("\n", " ").split():
                k, _, v = part.partition("=")
                if k in ("regions", "start", "end", "holds"):
                    info[k] = v
            info["granted_at"] = p.stat().st_mtime
        except OSError:
            pass
        out[rid] = info
    try:
        ready = [n[:-5] for n in os.listdir(flags / "ready") if n.endswith(".json") and not n.startswith(".")]
    except OSError:
        ready = []
    for rid in ready:
        if rid in out or rid in ended:
            continue
        d = flags / "dryrun" / rid
        if (d / "PASS.json").exists():
            st = "ready"
        elif any(d.glob("FAIL-*.json")):
            st = "dryrun-fail"
        else:
            st = "dryrun-pending"
        out[rid] = {"id": rid, "state": st, "handoff": _handoff_of(rid)}
    return out


def _filed_24h(flags: Path, now: float) -> int:
    n = 0
    try:
        with os.scandir(flags / "grants") as it:
            for e in it:
                if e.name.endswith(".complete") and now - e.stat().st_mtime < 86400:
                    n += 1
    except OSError:
        pass
    return n


_SNAP_RE = re.compile(r"^(\S+Z) SNAPSHOT free=(\S*) busy=(\S*)")


def keeper_snapshot(flags: Path) -> dict | None:
    lines = read_log_tail(flags / "ws58-calendar-keeper.log", 400_000)
    for line in reversed(lines):
        m = _SNAP_RE.match(line)
        if m:
            free = [r for r in m.group(2).split(",") if r]
            busy = {}
            for item in m.group(3).split(","):
                if item:
                    r, _, rid = item.partition(":")
                    busy[r] = rid
            return {"ts": m.group(1), "free": free, "busy": busy, "line": line[:300]}
    return None


def compute_payload(flags: Path, now: float) -> dict:
    rows = _rows(flags)
    snap = keeper_snapshot(flags)
    busy = dict((snap or {}).get("busy") or {})
    for r in rows.values():                       # the grants are the primary record of who holds what
        if r["state"] == "running":
            for h in (r.get("holds") or "").split(","):
                if h in REGIONS:
                    busy.setdefault(h, r["id"])
    regions = [{"region": r, "state": "busy" if r in busy else "free", "row": busy.get(r)}
               for r in REGIONS]
    counts = {"ready": 0, "running": 0, "dryrun-fail": 0, "dryrun-pending": 0}
    for r in rows.values():
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    counts["free_regions"] = sum(1 for r in regions if r["state"] == "free")
    counts["filed_24h"] = _filed_24h(flags, now)
    age = (now - parse_ts(snap["ts"])) if snap and parse_ts(snap["ts"]) else None
    return {"regions": regions, "counts": counts, "rows": rows,
            "snapshot": snap, "snapshot_age_s": age}


# --------------------------------------------------------------------------- #
# handoff overview: classes derived from the EXISTING index graph (/api/handoff_graph)
# --------------------------------------------------------------------------- #
#: what currently blocks a handoff; owner = who must act
CLASSES = {
    "non-inference": ("AI", "non-inference tasks still to work through"),
    "readied-waiting": ("DET", "only readied inference rows, waiting for compute"),
    "needs-ready": ("AI", "inference tasks not yet readied (make ready)"),
    "done": ("DET", "done or no open tasks"),
}
_INFERENCE_TIERS = {0, 4, 5, 6}   # backlog-priority tiers: 0 prep, 4 live, 5 ready, 6 routine


def classify_handoffs(graph: dict | None, rows: dict) -> dict:
    """Group the graph's nodes by handoff and class each handoff by its blockers.

    Per node: no open work -> done; tier 0 or an inference tier -> readied-waiting when
    the handoff owns a ready/running rowflow row (``ready/<id>.json handoff_task``),
    else needs-ready; any other open node -> non-inference. Per handoff the first
    class present wins in the order non-inference, needs-ready, readied-waiting, done
    (agent work outranks waiting for compute).
    """
    nodes = (graph or {}).get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        return {"present": False, "handoffs": [], "class_counts": {}}
    readied: dict[str, int] = {}
    for r in rows.values():
        if r["state"] in ("ready", "running") and r.get("handoff"):
            readied[r["handoff"]] = readied.get(r["handoff"], 0) + 1
    by: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict) or not n.get("handoff"):
            continue
        state = n.get("state") or "active"
        key = f"handoffs/{state}/{n['handoff']}"
        h = by.setdefault(key, {"handoff": n["handoff"], "id": f"{state}/{str(n['handoff'])[:-3] if str(n['handoff']).endswith('.md') else n['handoff']}",
                                "open": 0, "classes": set(), "readied_rows": readied.get(key, 0)})
        tier = (n.get("priority_basis") or {}).get("tier")
        if not n.get("open"):
            continue
        h["open"] += n["open"]
        if tier in _INFERENCE_TIERS:
            h["classes"].add("readied-waiting" if readied.get(key) and tier != 0 else "needs-ready")
        else:
            h["classes"].add("non-inference")
    out, counts = [], {k: 0 for k in CLASSES}
    for h in by.values():
        cls = next((c for c in ("non-inference", "needs-ready", "readied-waiting") if c in h["classes"]), "done")
        h["class"] = cls
        h["owner"] = CLASSES[cls][0]
        h["classes"] = sorted(h["classes"])
        counts[cls] += 1
        out.append(h)
    order = {c: i for i, c in enumerate(CLASSES)}
    out.sort(key=lambda h: (order[h["class"]], h["handoff"]))
    return {"present": True, "handoffs": out, "class_counts": counts,
            "class_labels": {k: {"owner": v[0], "label": v[1]} for k, v in CLASSES.items()},
            "graph_generated_at": (graph or {}).get("generated_at")}


# --------------------------------------------------------------------------- #
# sessions
# --------------------------------------------------------------------------- #
def _slug_rank(slug: str, entry: dict, last: dict | None) -> float:
    if last and last.get("rank") is not None:
        return float(last["rank"])
    r = (entry.get("auto_start") or {}).get("rank")
    return float(r) if isinstance(r, (int, float)) else 1e9


def build_payload(flags: Path | None = None, now: float | None = None, graph: dict | None = None) -> dict:
    flags = flags or flags_dir()
    now = time.time() if now is None else now
    reg = _json(flags / "handoff-sessions.json")
    if not isinstance(reg, dict) or not isinstance(reg.get("sessions"), dict):
        return {"schema": SCHEMA, "present": False, "error": f"{flags}/handoff-sessions.json unreadable",
                "generated_at": now}
    compute = compute_payload(flags, now)
    for e in reg["sessions"].values():          # rows with no handoff_task path: link via the owning session
        if not isinstance(e, dict) or not e.get("handoff"):
            continue
        ids = list(e.get("row_ids") or []) + list((e.get("auto_start") or {}).get("rows") or []) \
            + list((e.get("last_report") or {}).get("rows_published") or [])
        for rid in ids:
            if isinstance(rid, str) and rid in compute["rows"] and not compute["rows"][rid].get("handoff"):
                compute["rows"][rid]["handoff"] = e["handoff"]
    logs = last_log_by_slug(read_log_tail(flags / "handoff-sessions.log"))
    sessions, queued = [], []
    for slug, e in reg["sessions"].items():
        if not isinstance(e, dict):
            continue
        rep = _json(flags / "handoff-sessions" / slug / "report.json")
        rep = rep if isinstance(rep, dict) else None
        live = e.get("status") == "live" and pid_alive(e.get("pid"))
        last = logs.get(slug)
        step, detail = step_of(e, rep, live, last)
        blocked = []
        for rid in ((rep or {}).get("blocked_by") or []):
            blocked.append({"id": rid, "state": (compute["rows"].get(rid) or {}).get("state", "ended-or-unknown")})
        item = {"slug": slug, "handoff": e.get("handoff"), "engine": e.get("engine"), "pid": e.get("pid"),
                "live": live, "step": step, "owner": STEP_OWNER[step], "detail": detail, "blocked_by": blocked,
                "last_end": e.get("last_end"), "last_resume": e.get("last_resume"),
                "report_state": (rep or {}).get("state") or (e.get("last_report") or {}).get("state"),
                "task": (rep or {}).get("task_text"), "rank": _slug_rank(slug, e, last)}
        if live or step in ("paused", "nudged", "done"):
            sessions.append(item)
        if step == "queued":
            queued.append(item)
    sessions.sort(key=lambda s: (not s["live"], s["rank"]))
    for i, s in enumerate([s for s in sessions if s["live"]], 1):
        s["slot"] = i
    queued.sort(key=lambda s: s["rank"])
    counts = {k: 0 for k in STEPS}
    for s in sessions:
        counts[s["step"]] += 1
    counts["queued"] = len(queued)
    disp = reg.get("dispatcher") or {}
    return {"schema": SCHEMA, "present": True, "generated_at": now,
            "max_live": reg.get("max_live"), "live": sum(1 for s in sessions if s["live"]),
            "dispatcher": disp, "dispatcher_last_pass": disp.get("last_pass"),
            "step_labels": STEPS, "step_owner": STEP_OWNER, "step_counts": counts,
            "sessions": sessions, "queued_next": queued[:10], "queued_total": len(queued),
            "overview": classify_handoffs(graph, compute["rows"]),
            "compute": {k: v for k, v in compute.items() if k != "rows"},
            "ready_rows": sorted((r for r in compute["rows"].values() if r["state"] != "running"),
                                 key=lambda r: r["id"])[:30]}

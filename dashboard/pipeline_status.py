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

try:
    from dashboard import handoff_parser as _hp
except ImportError:  # loaded as a top-level module (tests / scripts)
    import handoff_parser as _hp  # type: ignore[no-redef]

HANDOFF_ROOT = Path(__file__).resolve().parents[1] / "handoffs"
_ROWFLOW_PY = Path(__file__).resolve().parents[1] / "scripts" / "coordination" / "rowflow" / "rowflow.py"
_ROWFLOW_MOD: list = []


def _stop_path(row: dict) -> str | None:
    """rowflow.resolve_stop_path (the keeper's own parse); None = unknown, which keeps a row "ready"."""
    if not _ROWFLOW_MOD:
        try:
            import importlib.util
            import sys
            sys.path.insert(0, str(_ROWFLOW_PY.parent))
            try:
                spec = importlib.util.spec_from_file_location("_rowflow_for_dashboard", _ROWFLOW_PY)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            finally:
                sys.path.remove(str(_ROWFLOW_PY.parent))
            _ROWFLOW_MOD.append(mod)
        except Exception:  # noqa: BLE001 - a dashboard never fails on a helper import
            _ROWFLOW_MOD.append(None)
    mod = _ROWFLOW_MOD[0]
    try:
        if mod:
            return mod.resolve_stop_path(row)
    except Exception:  # noqa: BLE001
        pass
    # rowflow.py needs Python 3.12 syntax and the hub's interpreter may be older; without this every
    # withdrawn row reads as "ready". The manifest records the same path.
    return row.get("stop_file") or None

SCHEMA = "epyc.pipeline_status.v1"
REGIONS = ("q0", "q1", "q2", "q3", "gpu-quiet")

#: Step ids, in flowchart order. ``label`` is what the table and diagram show.
STEPS = {
    "queued": "queued (waiting for a slot)",
    "working": "working: non-inference tasks fanned out",
    "making-ready": "making inference rows ready",
    "paused": "paused: blocked only by readied rows",
    "nudged": "nudged: go on with the next step",
    "done": "done: handoff archived on origin/main, session retired, slot -> next handoff",
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
def _rows(flags: Path, fmap: dict | None = None) -> dict[str, dict]:
    """{row_id: {state, ...}} for every published row that is not finished.

    state: running (grant, no end) | stopped (STOP file present) | ready (dry run PASS) | dryrun-fail | dryrun-pending
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
        if not (h and h.endswith(".md")):                   # "FILLERS" etc. is not a handoff path
            return None
        return _hp.resolve_folded_file(h, fmap)             # a folded source -> its target

    out: dict[str, dict] = {}
    for rid, p in granted.items():
        if rid in ended:
            continue
        info: dict = {"id": rid, "state": "running", "handoff": _handoff_of(rid)}
        try:
            txt = p.read_text().strip()
            for part in txt.replace("\n", " ").split():
                k, _, v = part.partition("=")
                if k in ("regions", "start", "end", "holds", "kind"):
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
        sp = _stop_path(_json(flags / "ready" / f"{rid}.json") or {})
        if sp and os.path.exists(sp):                       # the launcher's --stop file: never granted, not ready
            out[rid] = {"id": rid, "state": "stopped", "stop_file": sp, "handoff": _handoff_of(rid)}
            continue
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


IDLE_PCT = 5.0
_PREV_SAMPLE: list = [None]


def region_cpus(region: str) -> list[int]:
    if region == "gpu-quiet":
        return list(range(184, 192))
    q = int(region[1:])
    return list(range(q * 24, q * 24 + 24)) + list(range(q * 24 + 96, q * 24 + 120))


def _cpu_sample() -> dict:
    out = {}
    try:
        with open("/proc/stat") as fh:
            for l in fh:
                if l.startswith("cpu") and l[3].isdigit():
                    f = l.split(); v = [int(x) for x in f[1:9]]
                    out[int(f[0][3:])] = (sum(v) - v[3] - v[4], sum(v))
    except (OSError, ValueError, IndexError):
        pass
    return out


def region_cpu_pct() -> dict:
    """busy %% per region over the interval since the previous call (first call: a 0.25 s window)."""
    s1 = _cpu_sample()
    s0 = _PREV_SAMPLE[0]
    if s0 is None or sum(t for _, t in s1.values()) - sum(t for _, t in s0.values()) <= 0:
        time.sleep(0.25)
        s0, s1 = s1, _cpu_sample()
    _PREV_SAMPLE[0] = s1
    out = {}
    for r in REGIONS:
        cs = region_cpus(r)
        b = sum(s1.get(c, (0, 0))[0] - s0.get(c, (0, 0))[0] for c in cs)
        t = sum(s1.get(c, (0, 0))[1] - s0.get(c, (0, 0))[1] for c in cs)
        out[r] = round(100.0 * b / t, 1) if t > 0 else None
    return out


def compute_payload(flags: Path, now: float, fmap: dict | None = None) -> dict:
    rows = _rows(flags, fmap)
    snap = keeper_snapshot(flags)
    busy = dict((snap or {}).get("busy") or {})
    for r in rows.values():                       # the grants are the primary record of who holds what
        if r["state"] == "running":
            for h in (r.get("holds") or "").split(","):
                if h in REGIONS:
                    busy.setdefault(h, r["id"])
    cpu = region_cpu_pct()
    regions = []
    for r in REGIONS:
        row = busy.get(r)
        info = rows.get(row) if row else None
        phase = None
        if row:
            phase = "dry-run" if (info or {}).get("kind") == "rowflow-dryrun" else "running"
        pct = cpu.get(r)
        label = "free" if not row else ("idle-held" if pct is not None and pct < IDLE_PCT else phase)
        regions.append({"region": r, "state": "busy" if row else "free", "row": row,
                        "phase": phase, "cpu_pct": pct, "label": label})
    counts = {"ready": 0, "running": 0, "stopped": 0, "dryrun-fail": 0, "dryrun-pending": 0}
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


def _rollup_counts(graph: dict | None, root: Path) -> dict[str, int]:
    """Open ``[roll-up]`` boxes per ``handoffs/<state>/<file>`` key (index ``open`` counts them)."""
    out: dict[str, int] = {}
    for n in ((graph or {}).get("nodes") or ()) if isinstance(graph, dict) else ():
        if not isinstance(n, dict) or not isinstance(n.get("handoff"), str):
            continue
        state = n.get("state") or "active"
        key = f"handoffs/{state}/{n['handoff']}"
        if key in out:
            continue
        try:
            out[key] = _hp.count_open_rollups((root / state / n["handoff"]).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out[key] = 0
    return out


def _handoff_file(h) -> str | None:
    """``x.md`` | ``handoffs/<state>/x.md`` | ``x.md:TASK`` -> ``x.md`` (the graph node's file)."""
    if not isinstance(h, str) or not h:
        return None
    base = h.partition(":")[0].rstrip("/").rpartition("/")[2]
    return base if base.endswith(".md") else None


def classify_handoffs(graph: dict | None, rows: dict, rollups: dict | None = None) -> dict:
    """Group the graph's nodes by handoff and class each handoff by its blockers.

    Per node: no open work -> done; tier 0 or an inference tier -> readied-waiting when
    the handoff owns a ready/running rowflow row (``ready/<id>.json handoff_task``),
    else needs-ready; any other open node -> non-inference. Per handoff the first
    class present wins in the order non-inference, needs-ready, readied-waiting, done
    (agent work outranks waiting for compute). ``rollups`` (open ``[roll-up]`` boxes per
    handoff key) is subtracted from the handoff's ``open``: a handoff whose only open
    boxes are non-dispatchable parents is done, never double-counted.
    """
    nodes = (graph or {}).get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        return {"present": False, "handoffs": [], "class_counts": {}}
    # Row handoffs arrive as ``x.md``, ``handoffs/<state>/x.md`` or ``x.md:TASK``
    # (manifest ``handoff_task``); count per bare filename and look nodes up the same way.
    readied: dict[str, int] = {}
    nready: dict[str, int] = {}
    nrun: dict[str, int] = {}
    for r in rows.values():
        f = _handoff_file(r.get("handoff"))
        if not f:
            continue
        if r["state"] in ("ready", "running"):
            readied[f] = readied.get(f, 0) + 1
        if r["state"] == "ready":
            nready[f] = nready.get(f, 0) + 1
        elif r["state"] == "running":
            nrun[f] = nrun.get(f, 0) + 1
    by: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict) or not n.get("handoff"):
            continue
        state = n.get("state") or "active"
        key = f"handoffs/{state}/{n['handoff']}"
        f = _handoff_file(n["handoff"])
        h = by.setdefault(key, {"handoff": n["handoff"], "id": f"{state}/{str(n['handoff'])[:-3] if str(n['handoff']).endswith('.md') else n['handoff']}",
                                "open": 0, "classes": set(), "readied_rows": readied.get(f, 0),
                                "ready_rows": nready.get(f, 0), "running_rows": nrun.get(f, 0)})
        tier = (n.get("priority_basis") or {}).get("tier")
        if not n.get("open"):
            continue
        h["open"] += n["open"]
        if tier in _INFERENCE_TIERS:
            h["classes"].add("readied-waiting" if readied.get(f) and tier != 0 else "needs-ready")
        else:
            h["classes"].add("non-inference")
    out, counts = [], {k: 0 for k in CLASSES}
    # A graph built after the 2026-11-03 counting fix already skips roll-up boxes in `open`;
    # subtracting them again would under-count, so only legacy graphs get the correction.
    if isinstance(graph, dict) and graph.get("rollups_excluded"):
        rollups = None
    for key, h in by.items():
        ru = (rollups or {}).get(key, 0)
        if ru:
            h["open"] = max(h["open"] - ru, 0)
            h["rollup_open"] = ru
            if h["open"] == 0:
                h["classes"] = set()
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


def build_payload(flags: Path | None = None, now: float | None = None, graph: dict | None = None,
                  handoff_root: Path | None = None) -> dict:
    flags = flags or flags_dir()
    root = Path(handoff_root) if handoff_root is not None else HANDOFF_ROOT
    fmap = _hp.load_folded_map(root)        # D5 redirects; absent file = empty map
    now = time.time() if now is None else now
    reg = _json(flags / "handoff-sessions.json")
    if not isinstance(reg, dict) or not isinstance(reg.get("sessions"), dict):
        return {"schema": SCHEMA, "present": False, "error": f"{flags}/handoff-sessions.json unreadable",
                "generated_at": now}
    compute = compute_payload(flags, now, fmap)
    for e in reg["sessions"].values():          # a slug still naming a folded source follows the fold
        if isinstance(e, dict) and e.get("handoff"):
            e["handoff"] = _hp.resolve_folded_file(e["handoff"], fmap)
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
    overview = classify_handoffs(graph, compute["rows"], _rollup_counts(graph, root))
    by_sess: dict[str, dict] = {}
    for it in queued + sessions:                 # sessions last: a live/paused entry outranks a queued one
        if it.get("handoff"):
            by_sess[it["handoff"]] = it
    for h in overview.get("handoffs", []):
        h["key"] = f"handoffs/{h['id']}.md"
        s_ = by_sess.get(h["key"])
        st = s_["step"] if s_ else None
        if s_ and s_["live"] and st in ("working", "making-ready", "nudged"):
            act = "working"
        elif st == "paused" or (not s_ and h["class"] == "readied-waiting") or (s_ and st != "queued" and h["class"] == "readied-waiting"):
            act = "paused"
        elif st == "queued":
            act = "queued"
        else:
            act = "idle"
        h["activity"] = act
        h["engine"] = s_["engine"] if s_ else None
        h["step"] = st
        h["slot"] = s_.get("slot") if s_ else None
    return {"schema": SCHEMA, "present": True, "generated_at": now,
            "max_live": reg.get("max_live"), "live": sum(1 for s in sessions if s["live"]),
            "dispatcher": disp, "dispatcher_last_pass": disp.get("last_pass"),
            "step_labels": STEPS, "step_owner": STEP_OWNER, "step_counts": counts,
            "sessions": sessions, "queued_next": queued[:10], "queued_total": len(queued),
            "overview": overview,
            "compute": {k: v for k, v in compute.items() if k != "rows"},
            "ready_rows": sorted((r for r in compute["rows"].values() if r["state"] != "running"),
                                 key=lambda r: r["id"])[:30]}

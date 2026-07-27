#!/usr/bin/env python3
"""EPYC project dashboard hub — handoff progress board.

A tiny, dependency-free web server (stdlib ``http.server`` only) owned by the
governance repo. It surfaces project-wide progress that is *artifact/file-backed*
(handoffs today; more views later). Anything that needs the orchestrator's live
in-process state or SSE inference taps stays on the orchestrator dashboard
(:8000) — this hub links to it. See ``dashboard/README.md`` for that boundary.

Routes
------
GET /                        the kanban page (static HTML, re-read per request)
GET /health                 ``{"status":"ok"}`` for the stack health probe
GET /api/handoff_board       compact cards for all four columns (live scan, TTL-cached)
GET /api/handoff_detail?id=  full card + scrubbed markdown body (lazy modal load)
GET /api/handoff_timeline    the git-derived timeline artifact (+ freshness)
GET /api/kernel              the kernel-R&D dashboard contract (+ freshness)
GET /bus                     the session-bus page (static HTML, re-read per request)
GET /api/bus                 roster, per-agent liveness, inbox depth, operator tokens (+ alarms)
GET /api/queue               folded work queue (latest row per task_id) + invariant alarms
GET /api/outcome             the autopilot outcome contract (+ freshness), if exported
GET /api/health              board=live + timeline/kernel/outcome staleness class

Run: ``python3 -m dashboard.server --port 8100``  (or ``python3 dashboard/server.py``)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Make ``from dashboard import ...`` work whether launched as ``-m dashboard.server``
# (cwd on path) or as a bare script ``python3 dashboard/server.py``.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dashboard import freshness, handoff_parser

# ``resolve()`` follows the /workspace -> /mnt/raid0/llm/epyc-root symlink, so the
# hub always reads its own repo regardless of which path launched it.
REPO = Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO / "handoffs"
TIMELINE_PATH = REPO / "data" / "handoff_timeline.json"
_STATIC = Path(__file__).resolve().parent / "static"
STATIC_HTML = _STATIC / "handoffs.html"
KERNEL_HTML = _STATIC / "kernel.html"
BUS_HTML = _STATIC / "bus.html"

# Kernel-R&D dashboard contract — produced by epyc-inference-research's kernel-R&D
# loop (kernel_store.py export); the hub only READS it (self-contained data
# contract, no kernel context needed here). Path is overridable for testing.
KERNEL_DASHBOARD_JSON = Path(os.environ.get(
    "KERNEL_DASHBOARD_JSON",
    "/mnt/raid0/llm/tmp/mi210-build/campaign/kernel_dashboard.json"))

# Autopilot outcome contract — the *steering* view of the orchestration loop
# (keepable / wasted-eval / learning-excluded rates + frontier/baseline-promotion
# stall counters). PRODUCED BY the orchestrator autopilot loop
# (``phase_status.build_phase_health_report`` → ``phase_health_report.py``), a
# NON-dashboard surface this hub does NOT own. The hub only MIRRORS a file-backed
# export if one is present; there is no exporter today (phase_health_report.py
# only prints JSON to stdout), so the card degrades honestly to a "not exported —
# see :8000" state until the loop writes this path. Overridable for testing.
AUTOPILOT_OUTCOME_JSON = Path(os.environ.get(
    "AUTOPILOT_OUTCOME_JSON",
    "/mnt/raid0/llm/tmp/autopilot/outcome_contract.json"))

# Timeline freshness thresholds (handoffs move on a human/commit cadence).
_TIMELINE_WARN_S = 6 * 3600
_TIMELINE_STALE_S = 2 * 86400
# Kernel-R&D loop is a slow (nightshift/overnight, single-GPU) cadence.
_KERNEL_WARN_S = 3 * 86400
_KERNEL_STALE_S = 14 * 86400
# Autopilot exports on a fast cadence WHEN RUNNING; a stale export means the loop
# is paused (Phase-0 stop-loss) or the exporter is dead — an honest signal, but
# expected during a pause, so it is surfaced without gating hub health.
_OUTCOME_WARN_S = 6 * 3600
_OUTCOME_STALE_S = 2 * 86400

_BOARD_TTL_S = 30.0
_NO_STORE = {"Cache-Control": "no-store", "Content-Type": "application/json"}

# --------------------------------------------------------------------------- #
# Payload builders (importable / unit-testable independent of the HTTP layer)
# --------------------------------------------------------------------------- #
_board_lock = threading.Lock()
_board_cache: dict | None = None
_board_cache_ts = 0.0

_HANDOFF_PATH_RE = re.compile(r"^handoffs/(active|blocked|completed|archived)/(.+)\.md$")

# Today's-activity parsing (git log -p over handoffs/): which handoff files were
# committed to since local midnight, and — the signal the backlog % actually
# moves on — how many task checkboxes those diffs checked or added.
_ACT_DIFF_PATH_RE = re.compile(r"^diff --git a/\S+ b/(handoffs/\S+\.md)$")
_ACT_CHECKED_RE = re.compile(r"^\s*[-*] \[[xX]\]")
_ACT_UNCHECKED_RE = re.compile(r"^\s*[-*] \[ \]")

_ACT_EMPTY = {"commits": 0, "handoffs_touched": 0, "boxes_checked": 0, "boxes_added": 0}


def _parse_semantic_timestamp(value: object) -> float | None:
    """Parse an ISO-8601 timestamp to Unix epoch seconds."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _parse_activity_log(text: str) -> dict:
    """Fold ``git log --format=commit:%H -p`` output into today's-activity counters.

    ``boxes_checked`` counts added ``[x]`` lines (a flip shows as -``[ ]``/+``[x]``,
    a task added-already-done as just +``[x]`` — both are completions recorded
    today). ``boxes_added`` counts added ``[ ]`` lines (new tracked tasks).
    """
    commits = 0
    touched: set[str] = set()
    boxes_checked = boxes_added = 0
    for line in text.splitlines():
        if line.startswith("commit:"):
            commits += 1
        elif line.startswith("diff --git "):
            m = _ACT_DIFF_PATH_RE.match(line)
            if m:
                touched.add(m.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            if _ACT_CHECKED_RE.match(body):
                boxes_checked += 1
            elif _ACT_UNCHECKED_RE.match(body):
                boxes_added += 1
    return {"commits": commits, "handoffs_touched": len(touched),
            "boxes_checked": boxes_checked, "boxes_added": boxes_added}


def _activity_today() -> dict:
    """Commits/checkbox flips under ``handoffs/`` since local midnight.

    Best-effort like the other git probes: zeros outside a git repo or on any
    git failure — the board must never 500 because of this signal.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO), "log", "--since=midnight",
             "--format=commit:%H", "-p", "--", "handoffs/"],
            capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return dict(_ACT_EMPTY)
    if proc.returncode != 0:
        return dict(_ACT_EMPTY)
    return _parse_activity_log(proc.stdout)


def _read_kernel_contract() -> dict:
    """Read the kernel dashboard contract, tolerating absence/corruption."""
    try:
        data = json.loads(KERNEL_DASHBOARD_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {**_KERNEL_EMPTY, "generated_at": None,
                "error": "kernel-R&D contract not exported yet — the loop "
                         "(epyc-inference-research) has not run kernel_store.py export."}
    except (OSError, json.JSONDecodeError) as exc:
        data = {**_KERNEL_EMPTY, "generated_at": None,
                "error": f"kernel-R&D contract unreadable: {exc}"}
    if not isinstance(data, dict):
        data = {**_KERNEL_EMPTY, "generated_at": None,
                "error": "kernel-R&D contract malformed (not an object)"}
    return data


def _kernel_contract_freshness(data: dict) -> dict:
    """Classify kernel freshness from semantic run timestamps, not file mtime."""
    ts_candidates = []
    runs = data.get("runs")
    if isinstance(runs, list):
        for run in runs:
            if isinstance(run, dict):
                ts = _parse_semantic_timestamp(run.get("ts"))
                if ts is not None:
                    ts_candidates.append(ts)
    if ts_candidates:
        source_ts = max(ts_candidates)
        source = "runs[].ts"
    else:
        source_ts = _parse_semantic_timestamp(data.get("generated_at"))
        source = "generated_at"
    if source_ts is None:
        return {"staleness_class": "missing", "age_s": None,
                "timestamp": None, "source": None}
    age = max(0.0, time.time() - source_ts)
    if age <= _KERNEL_WARN_S:
        cls = "fresh"
    elif age <= _KERNEL_STALE_S:
        cls = "aging"
    else:
        cls = "stale"
    return {"staleness_class": cls, "age_s": round(age, 1),
            "timestamp": round(source_ts, 3), "source": source}


def _load_file_activity() -> dict:
    """Best-effort read of the git-derived ``file_activity`` map (last commit day
    per handoff) from the timeline artifact.

    Returns ``{}`` on any absence/corruption — the board must never fail because
    this hook-regenerated cache is missing or malformed (mirrors ``timeline_payload``).
    """
    try:
        data = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    fa = data.get("file_activity") if isinstance(data, dict) else None
    return fa if isinstance(fa, dict) else {}


def _dirty_handoff_ids() -> set:
    """``state/stem`` ids of handoffs with uncommitted edits (modified or untracked).

    These are invisible to git history — and thus to ``file_activity`` — so the
    board uses filesystem mtime for them (gated on this dirtiness to keep bulk
    ``touch``/checkout noise out of the recency signal). Returns an empty set
    outside a git repo or if git is unavailable.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO), "status", "--porcelain", "--", "handoffs/"],
            capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()
    ids: set[str] = set()
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:  # rename entry: take the destination path
            path = path.split(" -> ", 1)[1]
        m = _HANDOFF_PATH_RE.match(path.strip().strip('"'))
        if m:
            ids.add(f"{m.group(1)}/{m.group(2)}")
    return ids


def board_payload(*, force: bool = False) -> dict:
    """Live directory scan of the four state dirs, cached for ``_BOARD_TTL_S``."""
    global _board_cache, _board_cache_ts
    with _board_lock:
        now = time.time()
        if force or _board_cache is None or (now - _board_cache_ts) > _BOARD_TTL_S:
            _board_cache = handoff_parser.build_board(
                HANDOFF_DIR,
                file_activity=_load_file_activity(),
                dirty_ids=_dirty_handoff_ids())
            _board_cache["activity_today"] = _activity_today()
            _board_cache_ts = now
        payload = dict(_board_cache)
    payload["_freshness"] = {"staleness_class": "fresh", "source": "live-scan"}
    return payload


def _validate_id(handoff_id: str) -> Path | None:
    """Resolve a ``state/stem`` id to a file path, or ``None`` if unsafe/missing.

    Guards against path traversal: the resolved path must stay inside
    ``HANDOFF_DIR`` and the leading segment must be a real state directory.
    """
    if (not handoff_id or ".." in handoff_id or handoff_id.startswith("/")
            or "\x00" in handoff_id or any(ord(c) < 32 for c in handoff_id)):
        return None
    parts = handoff_id.split("/")
    if len(parts) != 2 or parts[0] not in handoff_parser.STATES:
        return None
    state, stem = parts
    if not stem or "/" in stem or "\\" in stem:
        return None
    try:
        candidate = (HANDOFF_DIR / state / f"{stem}.md").resolve()
        candidate.relative_to(HANDOFF_DIR.resolve())
    except (ValueError, OSError):
        return None
    return candidate if candidate.is_file() else None


def detail_payload(handoff_id: str) -> tuple[int, dict]:
    """Return ``(http_status, payload)`` for one handoff's detail view."""
    path = _validate_id(handoff_id or "")
    if path is None:
        return 404, {"error": "handoff not found", "id": handoff_id}
    state = handoff_id.split("/")[0]
    card = handoff_parser.parse_file(state, path, detail=True)
    return 200, card


def timeline_payload() -> dict:
    """Read the git-derived timeline artifact, tolerating absence/corruption."""
    fresh = freshness.classify(TIMELINE_PATH, _TIMELINE_WARN_S, _TIMELINE_STALE_S)
    try:
        data = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"series": [], "tasks_weekly": [], "handoffs_weekly": [],
                "generated_at": None, "error": "timeline artifact not generated yet"}
    except (OSError, json.JSONDecodeError) as exc:
        data = {"series": [], "tasks_weekly": [], "handoffs_weekly": [],
                "generated_at": None, "error": f"timeline artifact unreadable: {exc}"}
    if not isinstance(data, dict):  # valid JSON but not an object (hand-edited/clobbered)
        data = {"series": [], "tasks_weekly": [], "handoffs_weekly": [],
                "generated_at": None, "error": "timeline artifact malformed (not an object)"}
    data["_freshness"] = fresh
    return data


_KERNEL_EMPTY = {
    "db_present": False, "runs": [], "pareto": [], "best_per_model": [],
    "totals": {"runs": 0, "correct": 0, "failed": 0, "models": 0},
    "observation_notice": (
        "Every number here is an OBSERVATION (MEASUREMENT.md) — it never gates a "
        "keep/revert/deploy/promote decision. Operator-only authorizes prod push."),
}


def kernel_payload() -> dict:
    """Read the kernel-R&D dashboard contract, tolerating absence/corruption.

    The hub only renders the contract; the loop (epyc-inference-research) owns it.
    """
    data = _read_kernel_contract()
    data["_freshness"] = _kernel_contract_freshness(data)
    return data


# --------------------------------------------------------------- session bus (M2)
#
# Renders the session bus's file state. The hub OWNS nothing here: the
# coordinator-daemon owns queue.jsonl and inbox/*, each agent owns its own
# outbox/heartbeat/cursor. Read-only, fails soft, never writes.

_BUS_ROOT = _REPO_ROOT / "coordination" / "session-bus"
_HEARTBEAT_WARN_S = 15 * 60
_HEARTBEAT_STALE_S = 60 * 60


def _read_bus_config() -> dict:
    """Read config.yaml. PyYAML is optional so the hub stays runnable under a
    bare stdlib python (it is normally launched from the orchestrator venv)."""
    path = _BUS_ROOT / "config.yaml"
    try:
        import yaml  # noqa: PLC0415 — optional dependency, deliberately local
    except ImportError:
        return {"_error": "PyYAML unavailable — bus config not parsed "
                          "(hub is running under a stdlib-only interpreter)"}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"_error": f"bus config not found at {path}"}
    except (OSError, Exception) as exc:  # yaml.YAMLError included
        return {"_error": f"bus config unreadable: {exc}"}
    return data if isinstance(data, dict) else {"_error": "bus config malformed (not a mapping)"}


def _read_jsonl_rows(path: Path, start: int = 0) -> list[dict]:
    """Tolerant JSONL read — a malformed line is skipped, never fatal."""
    try:
        with path.open("rb") as fh:
            fh.seek(start)
            raw = fh.read()
    except (FileNotFoundError, OSError):
        return []
    rows = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _fold_queue() -> dict[str, dict]:
    """Latest row per task_id wins (batch_ledger.reconcile semantics)."""
    latest: dict[str, dict] = {}
    for row in _read_jsonl_rows(_BUS_ROOT / "queue.jsonl"):
        tid = row.get("task_id")
        if tid:
            latest[tid] = row
    return latest


def _cursor_offset(agent: str) -> int:
    try:
        data = json.loads((_BUS_ROOT / "cursors" / f"{agent}.json").read_text(encoding="utf-8"))
        return int(data.get("offset", 0))
    except (FileNotFoundError, OSError, json.JSONDecodeError, ValueError, TypeError):
        return 0


def _heartbeat_class(age_s: float | None) -> str:
    if age_s is None:
        return "missing"
    if age_s <= _HEARTBEAT_WARN_S:
        return "fresh"
    return "aging" if age_s <= _HEARTBEAT_STALE_S else "stale"


def queue_payload() -> dict:
    """Folded work queue plus the invariant alarms the rider defines."""
    latest = _fold_queue()
    rows = [latest[k] for k in sorted(latest)]
    by_status: dict[str, int] = {}
    by_lane: dict[str, int] = {}
    for row in rows:
        by_status[row.get("status", "?")] = by_status.get(row.get("status", "?"), 0) + 1
        by_lane[row.get("lane", "?")] = by_lane.get(row.get("lane", "?"), 0) + 1

    none_ready = sum(1 for r in rows if r.get("status") == "READY" and r.get("lane") == "none")
    ungated = [r.get("task_id") for r in rows if not r.get("gating")]

    alarms = []
    if rows and none_ready == 0:
        alarms.append({
            "id": "none-lane-depth",
            "severity": "warn",
            "detail": "lane:none READY depth is 0. The never-block guarantee assumes a "
                      "non-empty non-gated backlog; without it a main that loses a lease "
                      "has nothing to fall back to.",
        })
    if ungated:
        alarms.append({
            "id": "missing-gating",
            "severity": "error",
            "detail": f"{len(ungated)} row(s) lack a gating classification "
                      f"({', '.join(str(t) for t in ungated[:5])}). Lease revocation has no "
                      "defined fallback set for these.",
        })

    ts_candidates = [t for t in (_parse_semantic_timestamp(r.get("ts")) for r in rows) if t]
    generated_at = max(ts_candidates) if ts_candidates else None
    return {
        "generated_at": (datetime.fromtimestamp(generated_at, timezone.utc).isoformat()
                         if generated_at else None),
        "count": len(rows),
        "by_status": by_status,
        "by_lane": by_lane,
        "none_lane_ready_depth": none_ready,
        "rows": rows,
        "alarms": alarms,
        "_freshness": {
            "staleness_class": _heartbeat_class(
                None if generated_at is None else max(0.0, time.time() - generated_at)),
            "age_s": None if generated_at is None else max(0.0, time.time() - generated_at),
            "source": "queue.jsonl rows[].ts",
        },
    }


def bus_payload() -> dict:
    """Roster, per-agent liveness, inbox depth, operator-token state."""
    config = _read_bus_config()
    roster = config.get("roster") or []
    now = time.time()

    agents = []
    seen = set()
    for entry in roster if isinstance(roster, list) else []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        aid = str(entry["id"])
        seen.add(aid)
        hb_path = _BUS_ROOT / "heartbeats" / f"{aid}.json"
        hb: dict = {}
        age = None
        try:
            hb = json.loads(hb_path.read_text(encoding="utf-8"))
            age = max(0.0, now - hb_path.stat().st_mtime)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            hb = {}
        unread = len(_read_jsonl_rows(_BUS_ROOT / "inbox" / f"{aid}.jsonl", _cursor_offset(aid)))
        agents.append({
            "id": aid,
            "role": entry.get("role"),
            "lanes": entry.get("lanes"),
            "endpoint": entry.get("endpoint"),
            "drain": entry.get("drain"),
            "state": hb.get("state"),
            "task_id": hb.get("task_id"),
            "heartbeat_age_s": age,
            "heartbeat_class": _heartbeat_class(age),
            "inbox_unread": unread,
        })

    # Files present for an agent with no roster row: adding a main is "1 roster
    # row + 4 files", so files without a row means a half-added main.
    orphan_files = sorted({p.stem for p in (_BUS_ROOT / "outbox").glob("*.jsonl")} - seen)

    tokens_path = _BUS_ROOT / "tokens" / "token-queue.md"
    try:
        token_text = tokens_path.read_text(encoding="utf-8")
        tokens = {"ungranted": token_text.count("- [ ]"), "granted": token_text.count("- [x]")}
    except (FileNotFoundError, OSError):
        tokens = {"ungranted": 0, "granted": 0, "error": "token queue not found"}

    alarms = []
    for a in agents:
        if a["heartbeat_class"] == "stale":
            alarms.append({"id": f"stale-heartbeat:{a['id']}", "severity": "warn",
                           "detail": f"{a['id']} heartbeat is {a['heartbeat_age_s']:.0f}s old."})
    if orphan_files:
        alarms.append({"id": "roster-orphan", "severity": "error",
                       "detail": f"bus files exist for {orphan_files} with no roster row."})

    # R3: a co-residency policy whose topology hash no longer matches the live
    # matrix is silently wrong, which is the failure this guard exists to catch.
    co = config.get("co_residency") or {}
    expected_hash = co.get("expected_topology_hash")
    live_hash = None
    matrix_path = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/contention_matrix.yaml")
    try:
        for line in matrix_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("topology_hash:"):
                live_hash = line.split(":", 1)[1].strip().strip('"')
                break
    except (FileNotFoundError, OSError):
        pass
    if expected_hash and live_hash and expected_hash != live_hash:
        alarms.append({
            "id": "co-residency-topology-drift", "severity": "error",
            "detail": f"co_residency.expected_topology_hash={expected_hash} but the live "
                      f"contention matrix reports {live_hash}. Policy is stale; "
                      f"on_topology_mismatch={co.get('on_topology_mismatch')!r}.",
        })

    ages = [a["heartbeat_age_s"] for a in agents if a["heartbeat_age_s"] is not None]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_error": config.get("_error"),
        "coordinator_daemon": config.get("coordinator_daemon"),
        "flags": config.get("flags"),
        "caps": config.get("caps"),
        "agents": agents,
        "tokens": tokens,
        "co_residency": {"expected_topology_hash": expected_hash, "live_topology_hash": live_hash},
        "alarms": alarms,
        "_freshness": {
            "staleness_class": _heartbeat_class(min(ages) if ages else None),
            "age_s": min(ages) if ages else None,
            "source": "heartbeats/*.json mtime (freshest)",
        },
    }


_OUTCOME_EMPTY = {
    "outcome_progress": {"status": "missing", "blockers": []},
    "observation_notice": (
        "Autopilot outcome KPIs are OBSERVATIONS (MEASUREMENT.md) — they steer "
        "attention, they never gate a keep/revert/promote decision. The live "
        "outcome plane and every steering action (pause/rewind/promote) live on "
        "the orchestrator dashboard (:8000); this hub only mirrors an exported "
        "contract."),
}


def _looks_like_outcome_progress(d: dict) -> bool:
    """True if ``d`` is a bare ``outcome_progress`` dict (not the wrapper form)."""
    return "status" in d and any(k in d for k in ("rates", "blockers", "latest_trial_id"))


def _normalize_outcome_contract(raw: dict) -> dict:
    """Coerce either contract form to ``{generated_at, outcome_progress, ...}``.

    Accepts the wrapper form ``{generated_at, outcome_progress, ...}`` *or* a bare
    ``outcome_progress`` dict (as emitted by
    ``build_phase_health_report()['outcome_progress']``); the bare form is wrapped.
    """
    op = raw.get("outcome_progress")
    if isinstance(op, dict):
        data = dict(raw)
    elif _looks_like_outcome_progress(raw):
        data = {"generated_at": raw.get("generated_at"), "outcome_progress": raw}
    else:
        return {**_OUTCOME_EMPTY, "generated_at": raw.get("generated_at"),
                "error": "autopilot outcome contract missing 'outcome_progress'"}
    data.setdefault("observation_notice", _OUTCOME_EMPTY["observation_notice"])
    data.setdefault("generated_at", None)
    return data


def _read_outcome_contract() -> dict:
    """Read the autopilot outcome contract, tolerating absence/corruption.

    Returns the honest degraded ``_OUTCOME_EMPTY`` (with an ``error`` reason and
    ``generated_at=None``) on any absence/corruption — the card must never 500,
    and an absent export is the *expected* default (no exporter writes it yet).
    """
    try:
        raw = json.loads(AUTOPILOT_OUTCOME_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {**_OUTCOME_EMPTY, "generated_at": None,
                "error": "autopilot outcome contract not exported yet — the "
                         "orchestrator loop (:8000) has not written it."}
    except (OSError, json.JSONDecodeError) as exc:
        return {**_OUTCOME_EMPTY, "generated_at": None,
                "error": f"autopilot outcome contract unreadable: {exc}"}
    if not isinstance(raw, dict):
        return {**_OUTCOME_EMPTY, "generated_at": None,
                "error": "autopilot outcome contract malformed (not an object)"}
    return _normalize_outcome_contract(raw)


def _outcome_contract_freshness(data: dict) -> dict:
    """Classify outcome-contract freshness from the export's semantic timestamp.

    Uses ``generated_at`` (when the exporter last read the journal), NEVER the
    file mtime — mirrors the kernel-contract fix so a no-op re-export cannot read
    'fresh forever'. NOTE: export-freshness only proves the pipeline is alive; the
    actual *stall* signal is ``trials_since_frontier``/``trials_since_promotion``
    in the contract body, which the card surfaces directly.
    """
    source_ts = _parse_semantic_timestamp(data.get("generated_at"))
    if source_ts is None:
        return {"staleness_class": "missing", "age_s": None,
                "timestamp": None, "source": None}
    age = max(0.0, time.time() - source_ts)
    if age <= _OUTCOME_WARN_S:
        cls = "fresh"
    elif age <= _OUTCOME_STALE_S:
        cls = "aging"
    else:
        cls = "stale"
    return {"staleness_class": cls, "age_s": round(age, 1),
            "timestamp": round(source_ts, 3), "source": "generated_at"}


def outcome_payload() -> dict:
    """Read the autopilot outcome contract, tolerating absence/corruption.

    Degrade-honestly boundary: the outcome KPIs are produced by the orchestrator
    autopilot loop (a NON-dashboard surface this hub does not own). The hub only
    mirrors a file-backed export if present; when it is absent (today's default)
    the payload is the honest 'not exported' state that the card points at :8000.
    """
    data = _read_outcome_contract()
    data["_freshness"] = _outcome_contract_freshness(data)
    return data


def health_payload() -> dict:
    """Fold the board (live) + timeline + kernel + outcome artifacts into one line."""
    tl = freshness.classify(TIMELINE_PATH, _TIMELINE_WARN_S, _TIMELINE_STALE_S)
    kn = _kernel_contract_freshness(_read_kernel_contract())
    oc = _outcome_contract_freshness(_read_outcome_contract())
    # ``missing`` is not degraded (fresh checkout / loop not started); ``stale`` is.
    # The outcome export is deliberately EXCLUDED from the degraded gate: a paused
    # loop (Phase-0 stop-loss) reads stale/missing by design, so it is surfaced for
    # visibility but must not flip the stack-health probe to degraded.
    degraded = tl["staleness_class"] == "stale" or kn["staleness_class"] == "stale"
    return {
        "status": "degraded" if degraded else "ok",
        "board": {"staleness_class": "fresh", "source": "live-scan"},
        "timeline": tl,
        "kernel": kn,
        "outcome": oc,
        "now": time.time(),
    }


# --------------------------------------------------------------------------- #
# HTTP layer
# --------------------------------------------------------------------------- #
class _Handler(BaseHTTPRequestHandler):
    server_version = "EPYCHandoffHub/1.0"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for key, value in _NO_STORE.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_html(self, path: Path) -> None:
        try:
            body = path.read_bytes()
            status = 200
        except OSError:
            body = b"<h1>dashboard</h1><p>static page missing</p>"
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        try:
            if route == "/":
                self._send_html(STATIC_HTML)
            elif route == "/kernel":
                self._send_html(KERNEL_HTML)
            elif route == "/bus":
                self._send_html(BUS_HTML)
            elif route == "/health":
                self._send_json({"status": "ok"})
            elif route == "/api/handoff_board":
                self._send_json(board_payload())
            elif route == "/api/handoff_detail":
                qs = parse_qs(parsed.query)
                handoff_id = (qs.get("id") or [""])[0]
                status, payload = detail_payload(handoff_id)
                self._send_json(payload, status=status)
            elif route == "/api/handoff_timeline":
                self._send_json(timeline_payload())
            elif route == "/api/kernel":
                self._send_json(kernel_payload())
            elif route == "/api/bus":
                self._send_json(bus_payload())
            elif route == "/api/queue":
                self._send_json(queue_payload())
            elif route == "/api/outcome":
                self._send_json(outcome_payload())
            elif route == "/api/health":
                self._send_json(health_payload())
            else:
                self._send_json({"error": "not found", "path": route}, status=404)
        except BrokenPipeError:
            pass  # client hung up mid-response; nothing to do
        except Exception as exc:  # never let one bad request kill the thread
            try:
                self._send_json({"error": "internal", "detail": str(exc)}, status=500)
            except OSError:
                pass

    do_HEAD = do_GET  # allow HEAD probes to reuse the same dispatch

    def log_message(self, fmt: str, *args) -> None:  # quieter default logging
        return


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def main() -> None:
    ap = argparse.ArgumentParser(description="EPYC handoff dashboard hub")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8100)
    args = ap.parse_args()
    httpd = build_server(args.host, args.port)
    print(f"[handoff-hub] serving http://{args.host}:{args.port}/  (repo: {REPO})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

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
GET /api/handoff_board       compact cards for all four columns + backlog ratios +
                             flow (activity_today, activity_window) — live scan, TTL-cached
GET /api/handoff_detail?id=  full card + scrubbed markdown body (lazy modal load)
GET /api/handoff_timeline    the git-derived timeline artifact (+ freshness)
GET /api/handoff_graph       the index dependency/liveness graph (+ freshness)
GET /api/kernel              the kernel-R&D dashboard contract (+ freshness)
GET /api/kernel/health       Kernel-R&D producer/data health only (non-recursive)
GET /machine                 the machine / live-inference page (data plane: :8000 API)
GET /autopilot               the autopilot-loop page (data plane: :8000 API)
GET /nav.js                  the ONE shared cross-dashboard nav, with the registry
                             injected ahead of it as ``window.__EPYC_DASHBOARDS``
GET /api/dashboards          the dashboard directory (dashboard/registry.json) plus a
                             live 127.0.0.1 probe per declared (port, health_path)
GET /bus                     the session-bus page (static HTML, re-read per request)
GET /api/bus                 roster, per-agent liveness, inbox depth, operator tokens (+ alarms)
GET /api/queue               folded work queue (latest row per task_id) + invariant alarms
GET /api/outcome             the autopilot outcome contract (+ freshness), if exported
GET /api/health              the FOLD over ``dashboard/panels.py``: every panel's
                             freshness envelope + watchdog, plus one status that
                             names the worst panel and why

TWO HEALTH ROUTES, ON PURPOSE (AK6)
-----------------------------------
``/health`` is the TRANSPORT probe and answers only "this process is serving".
``scripts/dashboard/hub_supervisor.sh`` polls it every 15s and KILLS AND RESTARTS
the hub when the body stops matching ``"status"…ok``. Folding producer health into
it would mean a dead AutoKernel loop restarts the dashboard in a loop — a restart
cannot revive another repo's producer — so the two planes stay separate and
``tests/test_dashboard_panels.py`` pins that boundary in both directions.

``/api/health`` is the operator fold and is three-valued (``ok`` / ``absent`` /
``degraded``). It is where "nobody is reporting" is allowed to be loud.

Run: ``python3 -m dashboard.server --port 8100``  (or ``python3 dashboard/server.py``)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Make ``from dashboard import ...`` work whether launched as ``-m dashboard.server``
# (cwd on path) or as a bare script ``python3 dashboard/server.py``.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ``freshness`` is no longer imported here: every classification now goes through
# ``panels`` (which owns the one classifier), so the hub cannot grow a fourth
# hand-rolled threshold ladder by reaching past the registry.
from dashboard import handoff_parser, panels

# ``resolve()`` follows the /workspace -> /mnt/raid0/llm/epyc-root symlink, so the
# hub always reads its own repo regardless of which path launched it.
REPO = Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO / "handoffs"
TIMELINE_PATH = REPO / "data" / "handoff_timeline.json"
GRAPH_PATH = REPO / "handoffs" / "active" / ".index-graph.json"
_STATIC = Path(__file__).resolve().parent / "static"
STATIC_HTML = _STATIC / "handoffs.html"
KERNEL_HTML = _STATIC / "kernel.html"
BUS_HTML = _STATIC / "bus.html"
BENCHMARKS_HTML = _STATIC / "benchmarks.html"
MACHINE_HTML = _STATIC / "machine.html"
AUTOPILOT_HTML = _STATIC / "autopilot.html"
NAV_JS = _STATIC / "nav.js"

# RTG-47 Phase 0. The MACHINE-READABLE dashboard directory: one file naming every
# dashboard surface, its port, its path, its owning repo and its health probe.
# It exists because navigation was per-page hand-rolled and drifted into a
# five-by-five matrix with holes (audit 1.3): reaching AutoKernel required routing
# through the handoff board, and cross-server URLs were re-derived ad hoc in three
# places. One file, one nav, one probe list — a new page is a registry row, not a
# fifth hand-copied ``<nav>``.
DASHBOARD_REGISTRY_JSON = Path(__file__).resolve().parent / "registry.json"
DASHBOARD_REGISTRY_SCHEMA = "epyc.dashboard.registry.v1"

# Kernel-R&D dashboard contract — produced by the AutoKernel campaign driver in
# epyc-inference-research (``autokernel.dashboard.export_terminal_entry`` after
# the terminal journal append);
# the hub only READS it (self-contained data contract, no kernel context needed
# here, and the hub never imports that package). Path is overridable for testing.
#
# AK6 DURABLE PATH. The old default was
# ``/mnt/raid0/llm/tmp/mi210-build/campaign/kernel_dashboard.json``, which failed
# three ways at once: ``/mnt/raid0/llm/tmp`` is the first entry of the producer's
# ``storage.EPHEMERAL_ROOTS`` (one sweep from gone, leaving no event behind), the
# directory does not exist on this host, and it sat in a build scratch tree owned
# by nobody. The producer now writes ``DEFAULT_EXPORT_PATH`` below: on the array
# that survives reboots, outside every checkout (so it can never ride into a
# parallel session's commit), and a fixed constant so the hub needs no env var.
KERNEL_DASHBOARD_JSON = Path(os.environ.get(
    "KERNEL_DASHBOARD_JSON",
    "/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json"))

# The two contract versions the hub reads. Copied as STRINGS on purpose: the hub
# is stdlib-only and must never import epyc-inference-research to render a page
# (a consumer that needs its producer's code installed is a consumer that goes
# dark when the producer's repo moves). ``tests/test_dashboard_panels.py`` pins
# these against the producer's own constants when that repo is importable, and
# SKIPS NOTHING when it is not — it asserts the literals instead.
KERNEL_SCHEMA_V1 = "epyc.autokernel.kernel_dashboard.v1"
KERNEL_SCHEMA_V2 = "epyc.autokernel.kernel_dashboard.v2"
#: v2 section statuses. Three, not two: ``not_reported`` is what a dead owner
#: looks like, and it is a value rather than an omission.
KERNEL_SECTION_OBSERVED = "observed"

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
BENCHMARK_ARTIFACT_INVENTORY = REPO / "data" / "benchmark_artifact_inventory.json"

# AutoKernel has two different facts worth showing and they must not be allowed
# to certify each other:
#
# * KERNEL_DASHBOARD_JSON is the runtime contract.  It is what the watchdog and
#   /api/health classify, and implementation work must never make it look fresh.
# * AUTOKERNEL_RESEARCH_REPO is a live, read-only activity source.  It tells the
#   operator that the implementation and calibration bundles are moving even
#   before the first campaign exists.  This is presentation context only: it is
#   deliberately kept under the hub-owned ``_activity`` key and is never passed
#   to ``_kernel_observation``.
AUTOKERNEL_RESEARCH_REPO = Path(os.environ.get(
    "AUTOKERNEL_RESEARCH_REPO",
    "/workspace/repos/epyc-inference-research"))
AUTOKERNEL_STATE_ROOT = Path(os.environ.get(
    "AUTOKERNEL_STATE_ROOT",
    "/mnt/raid0/llm/autokernel"))
AUTOKERNEL_PROBE_ROOT = Path(os.environ.get(
    "AUTOKERNEL_PROBE_ROOT",
    "/mnt/raid0/llm/autokernel/probes"))
AUTOKERNEL_CONTROL_ROOT = Path(os.environ.get(
    "AUTOKERNEL_CONTROL_ROOT",
    "/mnt/raid0/llm/autokernel/controls"))
PRODUCTION_KERNEL_ATTESTATION = Path(os.environ.get(
    "PRODUCTION_KERNEL_ATTESTATION",
    str(REPO / "artifacts/operator/ratify_v9_final_freeze_20260811.json")))
PRODUCTION_KERNEL_REPO = Path(os.environ.get(
    "PRODUCTION_KERNEL_REPO",
    "/mnt/raid0/llm/llama.cpp"))
SPEECH_KERNEL_ATTESTATION = Path(os.environ.get(
    "SPEECH_KERNEL_ATTESTATION",
    str(REPO / "artifacts/operator/ratify_speech_kernel_freeze_20260731.json")))
#: The four binaries the freeze actually covers. These mirror what
#: `scripts/session/verify_llama_cpp.sh` and `verify_speech_kernels.sh` ENFORCE — the
#: dashboard is a read-only projection of the enforced truth, never a second opinion.
#: llama ships two (CPU and HIP) from one tree; the speech kernels ship one each.
PRODUCTION_LLAMA_BINARIES = {
    "cpu": Path(os.environ.get("PRODUCTION_LLAMA_CPU_BINARY",
                               "/mnt/raid0/llm/llama.cpp/build/bin/llama-server")),
    "hip": Path(os.environ.get("PRODUCTION_LLAMA_HIP_BINARY",
                               "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server")),
}
#: Guard against hashing something pathological on a request path. The real binaries
#: are 20 KB–1.7 MB and hash in ~4 ms; anything far larger is not what we think it is.
_MAX_HASHED_BINARY_BYTES = 512 * 1024 * 1024
#: Stable production links the runbook points launchers at, so a launcher never names
#: a build directory directly. Verified on disk 2026-08-12: these are `cpu`/`gpu`/
#: `stt`/`tts` — NOT the `inference-cpu`/`inference-gpu` spelling the follow-up brief
#: used, which exists nowhere on this host.
PRODUCTION_STABLE_LINK_ROOT = Path(os.environ.get(
    "PRODUCTION_STABLE_LINK_ROOT", "/mnt/raid0/llm/kernels/production"))
#: link name -> (expected resolved directory, binary that must live inside it)
PRODUCTION_STABLE_LINKS = {
    "cpu": ("/mnt/raid0/llm/llama.cpp/build/bin", "llama-server"),
    "gpu": ("/mnt/raid0/llm/llama.cpp/build-hip/bin", "llama-server"),
    "stt": ("/mnt/raid0/llm/whisper.cpp/build/bin", "whisper-server"),
    "tts": ("/mnt/raid0/llm/qwentts.cpp/build", "tts-server"),
}
#: The library families whose tree of origin decides whether a measurement is real.
_GGML_FAMILY = ("libggml", "libwhisper", "libllama", "libmtmd")

# Freshness thresholds are DECLARED IN THE REGISTRY (dashboard/panels.py) and
# read back here, so the numbers on the wire and the numbers in the panel→producer
# contract cannot drift. The old module-level literals are kept as names only.
_TIMELINE_WARN_S = panels.source("timeline").warn_s
_TIMELINE_STALE_S = panels.source("timeline").stale_s
_KERNEL_WARN_S = panels.source("kernel").warn_s
_KERNEL_STALE_S = panels.source("kernel").stale_s
_OUTCOME_WARN_S = panels.source("outcome").warn_s
_OUTCOME_STALE_S = panels.source("outcome").stale_s

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

# Trailing-window flow. A completion PERCENTAGE cannot distinguish "nothing is
# happening" from "running hard on a treadmill" — when new ``- [ ]`` lines are
# filed about as fast as old ones are checked, the ratio sits still while a lot
# of work happens. So the board headlines FLOW (closed / filed / net) over a
# trailing window, derived from the SAME git-log-over-handoffs/ source as
# ``activity_today`` — just bucketed per day instead of folded to one number.
_ACT_WINDOW_DAYS = 14
_ACT_ROLLUPS = (1, 7, 14)
_ACT_DAY_RE = re.compile(r"^commit:[0-9a-fA-F]+\|(\d{4}-\d{2}-\d{2})$")


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


# --------------------------------------------------------------------------- #
# Per-panel freshness envelope + transport watchdog (AK6)
# --------------------------------------------------------------------------- #
# The watchdog's second arm needs memory: "the producer keeps re-reporting, and
# its progress watermark has not moved". That memory is in-process and is
# deliberately NOT persisted — a hub restart forgets it, and the first arm (the
# producer's own semantic timestamp going stale) is stateless and survives a
# restart, so the detector degrades to the arm that needs no memory rather than
# to silence. Persisting it would also mean the hub WRITES, and a read-only hub
# cannot corrupt a producer's evidence.
_watchdog_lock = threading.Lock()
_watchdog_state: dict = {}


def _panel_envelope(panel: str, obs: "panels.Observation", *,
                    now: float | None = None) -> dict:
    """Classify one panel's observation, updating the watchdog's memory first."""
    source = panels.source(panel)
    with _watchdog_lock:
        panels.observe_watermark(_watchdog_state, panel, obs.watermark, now=now)
        snapshot = {k: dict(v) for k, v in _watchdog_state.items()}
    return panels.envelope(source, obs, now=now, watchdog_state=snapshot)


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


def _parse_activity_log_by_day(text: str) -> list[dict]:
    """Fold ``git log --format=commit:%H|%ad -p`` output into PER-DAY counters.

    Same counting rules as :func:`_parse_activity_log` (added ``[x]`` = closed,
    added ``[ ]`` = filed), bucketed by the commit's local date so a trailing
    window can be rolled up without a second scanner. Returns newest-day-first.
    Each row carries a ``_touched`` set of handoff paths, which
    :func:`_activity_window` unions per window and then strips.
    """
    days: dict[str, dict] = {}
    cur: dict | None = None
    for line in text.splitlines():
        m = _ACT_DAY_RE.match(line)
        if m:
            cur = days.setdefault(m.group(1), {
                "date": m.group(1), "commits": 0, "_touched": set(),
                "boxes_checked": 0, "boxes_added": 0})
            cur["commits"] += 1
            continue
        if cur is None:
            continue
        if line.startswith("diff --git "):
            pm = _ACT_DIFF_PATH_RE.match(line)
            if pm:
                cur["_touched"].add(pm.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            if _ACT_CHECKED_RE.match(body):
                cur["boxes_checked"] += 1
            elif _ACT_UNCHECKED_RE.match(body):
                cur["boxes_added"] += 1
    return sorted(days.values(), key=lambda r: r["date"], reverse=True)


def _activity_rollup(rows: list[dict], days: int, today: str) -> dict:
    """Sum the last ``days`` calendar days (ending ``today``) of per-day rows."""
    start = (datetime.fromisoformat(today).date()
             - timedelta(days=days - 1)).isoformat()
    sel = [r for r in rows if start <= r["date"] <= today]
    touched: set[str] = set()
    for r in sel:
        touched |= r.get("_touched", set())
    closed = sum(r["boxes_checked"] for r in sel)
    filed = sum(r["boxes_added"] for r in sel)
    return {"days": days, "since": start,
            "commits": sum(r["commits"] for r in sel),
            "handoffs_touched": len(touched),
            "boxes_checked": closed, "boxes_added": filed,
            "net": filed - closed}


def _activity_window(days: int = _ACT_WINDOW_DAYS) -> dict:
    """Per-day + rolled-up handoff flow over a trailing window.

    ``net`` is filed − closed: NEGATIVE means the backlog shrank (good). Same
    best-effort contract as :func:`_activity_today` — degrades to empty rollups
    on any git failure rather than 500ing the board.
    """
    today = datetime.now().date().isoformat()
    empty = {"window_days": days, "today": today, "per_day": [],
             "rollups": {f"{n}d": {"days": n, "since": today, "commits": 0,
                                   "handoffs_touched": 0, "boxes_checked": 0,
                                   "boxes_added": 0, "net": 0}
                         for n in _ACT_ROLLUPS}}
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO), "log", f"--since={days} days ago",
             "--date=format:%Y-%m-%d", "--format=commit:%H|%ad", "-p",
             "--", "handoffs/"],
            capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return empty
    if proc.returncode != 0:
        return empty
    rows = _parse_activity_log_by_day(proc.stdout)
    rollups = {f"{n}d": _activity_rollup(rows, n, today) for n in _ACT_ROLLUPS}
    per_day = [{k: v for k, v in r.items() if k != "_touched"}
               | {"handoffs_touched": len(r["_touched"]),
                  "net": r["boxes_added"] - r["boxes_checked"]}
               for r in rows]
    return {"window_days": days, "today": today,
            "per_day": per_day, "rollups": rollups}


#: Marker the READER writes into a degraded shell when it could not turn the
#: bytes on disk into a contract. Distinct from ``error`` (which a producer could
#: legitimately write) and from ``artifact_present`` (which now answers only "does
#: a file exist"). Three facts, three fields:
#:
#:   artifact_present=False                        no producer left anything
#:   artifact_present=True,  _reader_error=<why>   something is there and it is
#:                                                 BROKEN — a different, more
#:                                                 urgent fact than "never ran"
#:   artifact_present=True,  _reader_error=None    a contract the hub could read
#:
#: Before this, an unreadable file reported ``artifact_present=False`` and the
#: watchdog quoted the registry's "no campaign has ever exported one" — telling
#: the operator the opposite of what happened, and pointing the investigation at
#: the wrong repository.
READER_ERROR_KEY = "_reader_error"


def _read_json_object(path: Path, what: str) -> tuple:
    """``(artifact_present, data_or_None, reader_error_or_None)`` for one artifact.

    ONE reader for all four file-backed panels, so the absent/corrupt distinction
    cannot be right in one of them and wrong in the other three.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, None, None
    except OSError as exc:
        return path.exists(), None, f"{what} unreadable: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return True, None, f"{what} unreadable: {exc}"
    if not isinstance(data, dict):
        return True, None, f"{what} malformed (not an object)"
    return True, data, None


def _read_kernel_contract() -> tuple:
    """Read the kernel dashboard contract → ``(artifact_present, data)``.

    ABSENCE-TOLERANT, NEVER ABSENCE-SILENT. The degraded shell returned when the
    producer left nothing is ``_KERNEL_ABSENT`` — whose ``runs``/``pareto``/
    ``totals`` are **null, not empty lists**. That single choice is the scar fix
    on the wire: ``[]`` says "the producer reported and there is nothing", ``null``
    says "no producer reported". The old shell said ``[]`` for both, which is how a
    dead loop rendered as a clean, empty, trusted page.

    The first element of the tuple is the fact no document can carry: whether a
    file existed at all — NOT whether it could be parsed. See ``READER_ERROR_KEY``.
    """
    present, data, err = _read_json_object(
        KERNEL_DASHBOARD_JSON, "kernel dashboard contract")
    if data is not None:
        return True, data
    shell = {**_KERNEL_ABSENT, "generated_at": None, "produced_at": None}
    if err is None:
        shell["error"] = ("kernel dashboard contract not exported — the AutoKernel "
                          "loop (epyc-inference-research) has written nothing to "
                          f"{KERNEL_DASHBOARD_JSON}.")
    else:
        shell["error"] = err
        shell[READER_ERROR_KEY] = err
    return present, shell


def kernel_contract_version(data: dict) -> str:
    """``"v2"`` / ``"v1"`` / ``"unknown"`` for a kernel dashboard document.

    A labelled document is taken at its label. An UNLABELLED one is read as v1,
    because legacy exports carry no ``schema`` key at all and demanding the label
    would make every real v1 file unrecognised — which pushes a reader toward
    "render empty", the absence-tolerant failure again. A document labelled with
    something we do not know is ``unknown`` and is NEVER coerced to v1: a
    misread document renders as an empty-but-clean panel.
    """
    if not isinstance(data, dict):
        return "unknown"
    schema = data.get("schema")
    if schema == KERNEL_SCHEMA_V2:
        return "v2"
    if schema is None or schema == KERNEL_SCHEMA_V1:
        return "v1"
    return "unknown"


def _kernel_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    """Turn a kernel dashboard document into a ``panels.Observation``.

    v2 dates itself with ``produced_at``, which the PRODUCER derives from the
    loop's journaled record timestamps (controller transition ``at``, champion
    ``created_at``, readiness ``computed_at``, …) and never from the export. A
    no-op re-export cannot move it, and live host readings (free disk, held device
    claims) are excluded from it by the producer — so a surface process that is
    merely alive cannot manufacture freshness for a dead controller.

    v1 keeps exactly its pre-AK6 reading: newest ``runs[].ts``, else
    ``generated_at``.
    """
    evidence = str(KERNEL_DASHBOARD_JSON)
    if data.get(READER_ERROR_KEY):
        # Something IS on disk and the hub could not read it. Nothing in a
        # document the reader could not parse may date a report.
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY], evidence=evidence)
    version = kernel_contract_version(data)
    if version == "unknown":
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, evidence=evidence,
            detail=f"unrecognised kernel dashboard schema {data.get('schema')!r} — "
                   f"the hub reads {KERNEL_SCHEMA_V2} and the unlabelled v1 shape. "
                   "Refusing to guess: a v2 document misread as v1 renders as an "
                   "empty-but-clean panel.")
    if version == "v2":
        raw_sections = data.get("sections")
        if not isinstance(raw_sections, dict) or not raw_sections:
            # A v2 document's sections ARE the report. Missing or garbage sections
            # is a malformed contract, and a malformed contract that happens to
            # carry a fresh ``produced_at`` must not be dated by it.
            return panels.Observation(
                artifact_present=artifact_present, timestamp=None, source=None,
                populated=None, evidence=evidence,
                detail="contract-v2 document carries no readable 'sections' map — "
                       "the sections ARE the report, so this document dates nothing.")
        sections = raw_sections
        observed = [name for name, sec in sections.items()
                    if isinstance(sec, dict) and sec.get("status") == KERNEL_SECTION_OBSERVED]
        campaign = sections.get("campaign") if isinstance(sections.get("campaign"), dict) else {}
        run = (data.get("producer") or {}).get("run") if isinstance(data.get("producer"), dict) else None
        watermark = None
        if isinstance(run, dict):
            watermark = f"{run.get('campaign_id')}:{run.get('controller_seq')}"
        # DERIVED from the sections, then unioned with the producer's own summary —
        # never taken from the summary alone. A producer that omits (or empties)
        # ``unreported_sections`` while every owner behind it is dead would
        # otherwise hand the hub a fresh, observed, "reported-and-empty" panel:
        # the absence-tolerant clean render, reconstructed from a self-report.
        declared = data.get("unreported_sections")
        unreported = {name for name in sections if name not in observed}
        if isinstance(declared, list):
            unreported |= {str(name) for name in declared}
        if not observed:
            # The exporter ran and NOT ONE owner reported. This is the documented
            # third state (artifact present, reporting absent) and it is reached by
            # making the document undated, exactly as an all-``not_reported``
            # contract with a null ``produced_at`` already was.
            return panels.Observation(
                artifact_present=artifact_present, timestamp=None,
                source="produced_at", populated=None,
                detail=(data.get("error") or
                        "contract-v2 document has no section in status "
                        f"{KERNEL_SECTION_OBSERVED!r}: the exporter ran and every "
                        "owner behind it was silent."),
                watermark=watermark,
                unreported=tuple(sorted(unreported)),
                evidence=evidence,
            )
        return panels.Observation(
            artifact_present=artifact_present,
            timestamp=_parse_semantic_timestamp(data.get("produced_at")),
            source="produced_at",
            evidence=evidence,
            populated=bool(observed),
            detail=data.get("error"),
            watermark=watermark,
            # The controller's own word for "I have halted". A stopped campaign is
            # ALLOWED to be silent; only the producer may say so, and it does.
            producer_idle=bool(campaign.get("status") == KERNEL_SECTION_OBSERVED
                               and campaign.get("stopped") is True),
            unreported=tuple(sorted(unreported)),
        )
    ts_candidates = []
    runs = data.get("runs")
    if isinstance(runs, list):
        for run in runs:
            if isinstance(run, dict):
                ts = _parse_semantic_timestamp(run.get("ts"))
                if ts is not None:
                    ts_candidates.append(ts)
    if ts_candidates:
        source_ts, source = max(ts_candidates), "runs[].ts"
    else:
        source_ts, source = _parse_semantic_timestamp(data.get("generated_at")), "generated_at"
    n_runs = len(runs) if isinstance(runs, list) else None
    return panels.Observation(
        artifact_present=artifact_present,
        timestamp=source_ts,
        source=source,
        populated=None if n_runs is None else bool(n_runs),
        detail=data.get("error"),
        watermark=None if source_ts is None else f"v1:{n_runs}:{source_ts}",
        evidence=evidence,
    )


def _kernel_contract_freshness(data: dict, *, artifact_present: bool = True) -> dict:
    """Classify kernel freshness from semantic timestamps, never file mtime.

    Kept as a named function because it is the hub's oldest freshness contract and
    the existing regression locks call it directly; it is now one line of the
    generalised per-panel envelope rather than a private threshold ladder.
    """
    return _panel_envelope("kernel", _kernel_observation(
        data, artifact_present=artifact_present))


def kernel_data_health() -> tuple[int, dict]:
    """Kernel-R&D's panel-specific producer/data-health probe.

    This intentionally reads only the AutoKernel terminal contract and folds only
    the ``kernel`` envelope. It never calls :func:`health_payload` or
    :func:`panel_envelopes`, so a registry consumer may probe this route without
    recursing through the global ``/api/health`` fold (which includes the
    dashboard directory, whose Kernel-R&D row points back here).

    HTTP 200 means the contract is fully reported and current. ``absent`` and
    ``degraded`` both return HTTP 503 for simple health-check clients; the JSON
    body preserves the three-valued verdict and the complete freshness envelope,
    including partial ``unreported`` sections.
    """
    present, data = _read_kernel_contract()
    env = _kernel_contract_freshness(data, artifact_present=present)
    verdict = panels.fold(
        {"kernel": env}, registry={"kernel": panels.source("kernel")})
    payload = {
        "status": verdict["status"],
        "probe": "panel-data",
        "panel": "kernel",
        "data_route": panels.source("kernel").route,
        "transport_health": "/health",
        "global_health": "/api/health",
        "status_set_by": verdict["status_set_by"],
        "worst": verdict["worst"],
        "attention": verdict["attention"],
        "absent": verdict["absent"],
        "freshness": env,
    }
    return (200 if verdict["status"] == panels.STATUS_OK else 503), payload


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
            _board_cache["activity_window"] = _activity_window()
            _board_cache_ts = now
        payload = dict(_board_cache)
    # The TTL cache is a latency device, not a producer: the board is rebuilt
    # inside the request from the filesystem and git, so it is fresh by
    # construction and has no producer that could stop reporting.
    # ``bool(columns)`` was always True: ``columns`` is a dict of FOUR LISTS that
    # build_board always emits, so it is truthy over an empty (or missing)
    # handoff tree. The one health-gating live panel could therefore never report
    # ``content=empty`` — it claimed content by construction, which is the
    # renders-clean-over-nothing shape at the top of the page.
    columns = payload.get("columns") or {}
    payload["_freshness"] = _panel_envelope(
        "board", panels.live(populated=any(
            bool(v) for v in columns.values()) if isinstance(columns, dict)
            else bool(columns)))
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


_TIMELINE_ABSENT = {"series": None, "tasks_weekly": None, "handoffs_weekly": None,
                    "generated_at": None}


def _read_timeline_contract() -> tuple:
    """Read the git-derived timeline artifact → ``(artifact_present, data)``.

    Same absent-vs-empty rule as the kernel contract: the degraded shell carries
    ``null`` series, not ``[]``, so "the hook never ran" is not spelled the same
    way as "no handoffs moved this week".
    """
    present, data, err = _read_json_object(TIMELINE_PATH, "timeline artifact")
    if data is not None:
        return True, data
    if err is None:
        return False, {**_TIMELINE_ABSENT, "error": "timeline artifact not generated yet"}
    return present, {**_TIMELINE_ABSENT, "error": err, READER_ERROR_KEY: err}


def _timeline_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    """Date the timeline by the hook's own ``generated_at``, not by mtime.

    Pre-AK6 this panel was the last mtime badge in the hub. A regeneration hook
    that rewrites the file without advancing its content moves the mtime and
    nothing else, so mtime reads 'fresh' over a frozen timeline; ``last_sha`` is
    the watermark that catches exactly that.
    """
    if data.get(READER_ERROR_KEY):
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY])
    series = data.get("series")
    return panels.Observation(
        artifact_present=artifact_present,
        timestamp=_parse_semantic_timestamp(data.get("generated_at")),
        source="generated_at",
        populated=None if series is None else bool(series),
        detail=data.get("error"),
        watermark=data.get("last_sha") if isinstance(data.get("last_sha"), str) else None,
    )


def timeline_payload() -> dict:
    """Read the git-derived timeline artifact, tolerating absence/corruption."""
    present, data = _read_timeline_contract()
    data["_freshness"] = _panel_envelope(
        "timeline", _timeline_observation(data, artifact_present=present))
    return data


#: What the panel looks like when NO producer reported. ``null``, not ``[]`` —
#: see ``_read_kernel_contract``. The deployed ``static/kernel.html`` reads every
#: one of these through ``x || []`` / ``x || {}``, so a null degrades to the same
#: empty render it always did (absence tolerance is preserved) while the WIRE now
#: distinguishes the two facts that page could not.
_KERNEL_ABSENT = {
    "db_present": None, "runs": None, "pareto": None, "best_per_model": None,
    "totals": None, "sections": None, "degraded": True,
    "observation_notice": (
        "Every number here is an OBSERVATION (MEASUREMENT.md) — it never gates a "
        "keep/revert/deploy/promote decision. Operator-only authorizes prod push. "
        "THIS PANEL IS UNSOURCED: no producer reported, so an empty card here "
        "means 'nobody is reporting', not 'nothing is wrong'."),
}


#: What the ``/kernel`` PAGE is able to draw for a given document, and the
#: sentence it must show when it can draw nothing of its own.
#:
#: ON THE WIRE, not in ``static/kernel.html``, for two reasons. A sentence
#: hardcoded in the page cannot be tested and cannot know which contract it is
#: looking at — and the deployed page said
#:
#:     "no runs recorded yet — the kernel-R&D loop has not exported any results"
#:
#: over a FULLY REPORTED contract v2, because v2 carries campaign / champion /
#: backend-standing / blocking / headroom / claim / package SECTIONS and no
#: ``runs`` array at all. The producer was alive, every owner had reported, and
#: the page told the operator the loop had exported nothing. That is the
#: absence-tolerance scar in the render layer, and it is the reason this block
#: exists: the empty-state text is now DERIVED from the document that was read.
RENDER_MODE_V2 = "contract_v2"
RENDER_MODE_V1 = "run_log_v1"
RENDER_MODE_ABSENT = "unsourced"
RENDER_MODE_UNREADABLE = "unreadable"


def _kernel_render(data: dict, version: object, present: bool, env: dict) -> dict:
    """``{mode, note}``: which body the page draws, and the honest empty sentence.

    ``note`` is what the run-log panel shows when it has no rows. It is never the
    v1 sentence unless the document really is a v1 run log — "the loop has not
    exported any results" is a claim about the PRODUCER, and only an absent or
    empty v1 contract supports it.
    """
    if not present:
        return {"mode": RENDER_MODE_ABSENT,
                "note": (f"NO PRODUCER REPORTED. {env.get('absence_means') or ''} "
                         f"Evidence: {env.get('evidence')}").strip()}
    if data.get(READER_ERROR_KEY):
        return {"mode": RENDER_MODE_UNREADABLE,
                "note": (f"THE EXPORT IS PRESENT AND UNREADABLE — "
                         f"{data[READER_ERROR_KEY]}. This is not 'the loop never "
                         f"ran': something wrote {env.get('evidence')} and the hub "
                         f"could not parse it.")}
    if version == "v2":
        sections = data.get("sections")
        sections = sections if isinstance(sections, dict) else {}
        observed = sum(1 for sec in sections.values()
                       if isinstance(sec, dict)
                       and sec.get("status") == KERNEL_SECTION_OBSERVED)
        return {"mode": RENDER_MODE_V2,
                "note": (f"contract v2: {observed} of {len(sections)} sections "
                         "reported. v2 carries campaign, champion, backend "
                         "standing, blocking conditions, headroom, resource "
                         "claims and release-package state — it carries NO run "
                         "log, so the v1 run-log and Pareto panels are empty by "
                         "SHAPE, not because the producer exported nothing.")}
    runs = data.get("runs")
    if isinstance(runs, list) and runs:
        return {"mode": RENDER_MODE_V1, "note": None}
    return {"mode": RENDER_MODE_V1,
            "note": ("no runs recorded yet — the kernel-R&D loop has exported a "
                     "v1 contract with an empty run log")}


def _iso_mtime(path: Path) -> str | None:
    """UTC mtime for activity display, or ``None`` when the file raced away."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return None


def _autokernel_git_activity(repo: Path, *, limit: int = 8) -> dict:
    """Recent committed implementation work across refs, without imports.

    The dashboard process is intentionally stdlib-only.  ``git log`` also gives
    us the committed fact rather than the shared checkout's dirty state, which
    may belong to any of several sessions on this host.  ``--all`` is deliberate:
    AutoKernel development uses isolated worktrees, so the canonical checkout's
    current branch can trail already-committed work by hours.  This is activity
    context only and therefore never claims the newest ref is merged or deployed.
    """
    command = [
        "git", "-C", str(repo), "log", "--all", f"-{limit}",
        "--format=%H%x00%cI%x00%s", "--", "scripts/kernel_rnd/autokernel",
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=5.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": str(exc), "recent_commits": []}
    if proc.returncode != 0:
        return {"status": "unavailable",
                "reason": proc.stderr.strip() or f"git exited {proc.returncode}",
                "recent_commits": []}
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("\0", 2)
        if len(parts) != 3:
            continue
        sha, committed_at, subject = parts
        commits.append({"sha": sha, "short_sha": sha[:10],
                        "committed_at": committed_at, "subject": subject})
    return {"status": "observed" if commits else "empty",
            "scope": "committed AutoKernel work across local refs; not merge/deploy state",
            "head": commits[0] if commits else None,
            "recent_commits": commits}


def _autokernel_work_bundles(repo: Path, *, limit: int = 12) -> list[dict]:
    """Summarise durable ``data/autokernel_*`` bundles without interpreting results.

    A ``*.started_at`` marker with no matching ``*.ended_at`` marker is reported
    as in progress.  This is intentionally a mechanical file-state statement,
    not a benchmark verdict or a claim that the controller is alive.
    """
    data_root = repo / "data"
    try:
        roots = [p for p in data_root.iterdir()
                 if p.is_dir() and p.name.startswith("autokernel_")]
    except OSError:
        return []
    bundles = []
    for root in roots:
        try:
            files = [p for p in root.rglob("*") if p.is_file()]
        except OSError:
            continue
        timestamps = [(p, _iso_mtime(p)) for p in files]
        timestamps = [(p, ts) for p, ts in timestamps if ts is not None]
        newest_path, updated_at = (max(timestamps, key=lambda item: item[1])
                                   if timestamps else (None, None))
        active = []
        for marker in files:
            suffix = ".started_at"
            if not marker.name.endswith(suffix):
                continue
            ended = marker.with_name(marker.name[:-len(suffix)] + ".ended_at")
            if not ended.is_file():
                active.append(str(marker.relative_to(root))[:-len(suffix)])
        bundles.append({
            "name": root.name,
            "path": str(root),
            "updated_at": updated_at,
            "latest_file": (str(newest_path.relative_to(root))
                            if newest_path is not None else None),
            "file_count": len(files),
            "json_results": sum(1 for p in files if p.suffix == ".json"),
            "active_markers": sorted(active),
            "state": "in_progress" if active else ("populated" if files else "empty"),
        })
    bundles.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return bundles[:limit]


def _autokernel_journal_inventory(root: Path) -> dict:
    """Inventory journals under the declared state root; never guess other roots.

    ``campaign.py --journal-root`` is caller-supplied today.  The explicit
    ``discovery_scope`` makes that limitation visible instead of implying this
    scan is a complete campaign registry.
    """
    journals = []
    if root.is_dir():
        try:
            shards = list(root.rglob("events.jsonl"))
        except OSError:
            shards = []
        for shard in shards:
            try:
                stat = shard.stat()
            except OSError:
                continue
            journals.append({"root": str(shard.parent),
                             "updated_at": datetime.fromtimestamp(
                                 stat.st_mtime, timezone.utc).isoformat(),
                             "bytes": stat.st_size})
    journals.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return {
        "state_root": str(root),
        "discovery_scope": ("journals below AUTOKERNEL_STATE_ROOT only; campaign.py "
                            "also accepts arbitrary durable --journal-root paths"),
        "journals": journals,
    }


def _autokernel_probe_receipts(root: Path, *, limit: int = 20) -> dict:
    """Inventory durable probe receipts without turning the hub into an evaluator.

    Probe producers use different schemas and verdict vocabularies. The hub
    passes through only string labels already written by a producer; it never
    infers PASS/FAIL from measurements. Oversized or malformed JSON remains
    visible as a receipt with no producer label rather than disappearing.
    """
    probes_root = root / "probes"
    candidates = []
    try:
        paths = list(probes_root.glob("*/receipt.json"))
    except OSError:
        paths = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        candidates.append((stat.st_mtime, path, stat.st_size))
    candidates.sort(key=lambda item: item[0], reverse=True)
    receipts = []
    for mtime, path, size in candidates[:limit]:
        payload = None
        parse_state = "not_parsed"
        if size <= 4 * 1024 * 1024:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    payload = value
                    parse_state = "parsed"
                else:
                    parse_state = "non_object"
            except (OSError, UnicodeError, json.JSONDecodeError):
                parse_state = "invalid_json"
        else:
            parse_state = "oversized"
        producer_label = None
        schema = None
        campaign_id = None
        if payload is not None:
            schema = payload.get("schema") if isinstance(payload.get("schema"), str) else None
            campaign_id = (payload.get("campaign_id")
                           if isinstance(payload.get("campaign_id"), str) else None)
            nested = payload.get("result")
            nested_verdict = (nested.get("verdict") if isinstance(nested, dict) else None)
            for value in (nested_verdict, payload.get("verdict"), payload.get("status")):
                if isinstance(value, str) and value:
                    producer_label = value
                    break
        receipts.append({
            "probe": path.parent.name,
            "path": str(path),
            "updated_at": datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
            "bytes": size,
            "parse_state": parse_state,
            "schema": schema,
            "campaign_id": campaign_id,
            "producer_label": producer_label,
        })
    return {
        "root": str(probes_root),
        "role": ("receipt presence and producer-authored labels only; the dashboard "
                 "does not grade probe evidence"),
        "receipts": receipts,
    }


def _latest_autokernel_receipt(root: Path, filename: str,
                               schema: str) -> tuple[Path | None, dict | None, str | None]:
    """Find the newest readable receipt of one exact schema below ``root``.

    Probe run directory names are intentionally disposable.  The receipt schema
    and filename are the durable interface, while mtime is used only to select
    which completed artifact to display; it is never presented as benchmark
    time or used for the kernel watchdog.
    """
    try:
        candidates = list(root.glob(f"*/{filename}"))
    except OSError as exc:
        return None, None, f"probe discovery unavailable: {exc}"
    candidates.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    errors = []
    for path in candidates:
        _, data, err = _read_json_object(path, filename)
        if err:
            errors.append(f"{path}: {err}")
            continue
        if data is not None and data.get("schema") == schema:
            return path, data, None
    if errors:
        return None, None, errors[0]
    return None, None, f"no {schema} receipt found below {root}"


def _loop_engineering_summary(root: Path) -> dict:
    """Report the newest measured AK-LE panel and whether it was reduced.

    This is file-state plus producer-authored status only.  A complete panel is
    not itself a result: the externally pinned prefilter/reducer must publish a
    reduction before the dashboard may call any planner metric observed.
    """
    try:
        paths = list((root / "campaigns").glob("*/panel/panel.json"))
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    paths.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    for path in paths:
        _, panel, error = _read_json_object(path, "AK-LE panel")
        if error or panel is None or panel.get("schema") != \
                "epyc.autokernel.loop_experiment_planner_panel.v1":
            continue
        observations = panel.get("observations")
        observations = observations if isinstance(observations, list) else []
        campaign_root = path.parent.parent
        reductions = sorted(campaign_root.glob("planner-reduction*.json"),
                            key=lambda row: _iso_mtime(row) or "", reverse=True)
        reduction_path = None
        reduction = None
        for candidate in reductions:
            _, value, _ = _read_json_object(candidate, "AK-LE reduction")
            if isinstance(value, dict) and value.get("schema") == \
                    "epyc.autokernel.loop_experiment_planner_reduction.v1":
                reduction_path, reduction = candidate, value
                break
        planner_receipt = (reduction.get("planner_receipt")
                           if isinstance(reduction, dict) and isinstance(
                               reduction.get("planner_receipt"), dict) else {})
        search_rows = planner_receipt.get("search_persistence_observations")
        search_rows = search_rows if isinstance(search_rows, list) else []
        cells = []
        for row in search_rows:
            if not isinstance(row, dict):
                continue
            cells.append({key: row.get(key) for key in (
                "cell_id", "model_id", "effort", "target_context_mode",
                "prefilter_survival_count", "already_optimized_termination_count",
                "termination", "elapsed_wall_seconds",
            )})
        return {
            "available": True,
            "campaign_id": panel.get("experiment_id"),
            "panel_status": panel.get("status"),
            "completed_cells": len(observations),
            "total_cells": 8,
            "capture_mode": panel.get("capture_mode"),
            "reduced": reduction is not None,
            "reduction_sha256": (reduction.get("reduction_sha256")
                                 if reduction else None),
            "belief_measurement_count": (len(reduction.get("belief_measurements", []))
                                         if reduction else 0),
            "cells": cells,
            "authority": panel.get("authority"),
            "evidence": str(path),
            "reduction_evidence": str(reduction_path) if reduction_path else None,
            "note": ("complete raw panel, not a result; no empirical interpretation until the "
                     "pinned prefilter/reducer publishes a reduction")
                    if reduction is None else
                    "planner-only AK-LE-1/2 observation; no ranking or promotion authority",
        }
    return {"available": False, "error": f"no AK-LE panel found below {root / 'campaigns'}"}


def _fault_rehearsal_summary(root: Path) -> dict:
    """Project the newest real host-process rehearsal without grading it."""
    path, data, error = _latest_autokernel_receipt(
        root / "rehearsals", "receipt.json",
        "epyc.autokernel.host_process_fault_rehearsal.v1")
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    legs = data.get("legs") if isinstance(data.get("legs"), list) else []
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "status": data.get("status"),
        "capture_mode": data.get("capture_mode"),
        "passed_legs": sum(1 for leg in legs
                           if isinstance(leg, dict) and leg.get("status") == "PASS"),
        "total_legs": len(legs),
        "live_claim_root_touched": data.get("live_claim_root_touched"),
        "process_selection": data.get("process_selection"),
        "authority": data.get("authority"),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
        "note": ("dependency evidence for crash/restart, revocation, teardown, and "
                 "tamper handling; not a performance or release verdict"),
    }


def _campaign_audit_summary(path: Path | None, data: dict | None,
                            error: str | None) -> dict:
    """Project a controller audit receipt without inventing a verdict."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    panel = data.get("panel") if isinstance(data.get("panel"), dict) else {}
    arms = panel.get("arms") if isinstance(panel.get("arms"), list) else []
    ready = sum(1 for arm in arms
                if isinstance(arm, dict) and arm.get("executable") is True)
    missing = [str(arm.get("arm_id")) for arm in arms
               if isinstance(arm, dict) and arm.get("executable") is not True]
    constraints = (data.get("constraints")
                   if isinstance(data.get("constraints"), dict) else {})
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "status": data.get("status"),
        "authority": data.get("authority"),
        "ready_arms": ready,
        "total_arms": panel.get("arm_count"),
        "missing_arms": missing,
        "all_or_nothing_execution": constraints.get("all_or_nothing_execution"),
        "controller_or_gpu_command_executed": constraints.get(
            "controller_or_gpu_command_executed"),
        "promotion_authority": constraints.get("promotion_authority", False),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _smoke_receipt_summary(path: Path | None, data: dict | None,
                           error: str | None) -> dict:
    """Project empirical smoke state while preserving its diagnostic authority."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    sampling = (data.get("device_sampling")
                if isinstance(data.get("device_sampling"), dict) else {})
    failure = data.get("error") if isinstance(data.get("error"), dict) else {}
    released = (data.get("device_claim_released")
                if isinstance(data.get("device_claim_released"), dict) else {})
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "controller_id": data.get("controller_id"),
        "status": data.get("status"),
        "authority": data.get("authority"),
        "rankable": data.get("rankable"),
        "matched_campaign_implied": data.get("matched_campaign_implied"),
        "device_sample_count": sampling.get("sample_count"),
        "measurement_started_at": sampling.get("started_at"),
        "device_claim_released_at": released.get("released_at"),
        "error_type": failure.get("type"),
        "error_message": failure.get("message"),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _control_preflight_summary(path: Path | None, data: dict | None,
                               error: str | None) -> dict:
    """Project the trusted-instrument preflight without parsing prose reasons."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    outcomes = {
        str(name): check.get("outcome")
        for name, check in checks.items() if isinstance(check, dict)
    }
    failed = sorted(name for name, outcome in outcomes.items()
                    if outcome != "PASS")
    return {
        "available": True,
        "status": "PASS" if outcomes and not failed else "FAIL",
        "passed_checks": sum(1 for outcome in outcomes.values()
                             if outcome == "PASS"),
        "total_checks": len(outcomes),
        "failed_checks": failed,
        "measured_at": data.get("measured_at"),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _latest_control_summary(root: Path) -> tuple[Path | None, dict | None, str | None]:
    """Select the newest completed control summary with a matching attestation.

    ``summary.json`` predates receipt-wide schema stamping, so accepting it by
    filename alone would let an arbitrary JSON object become operator posture.
    The shape is therefore constrained here and its sibling composition receipt
    must carry the versioned schema and the same campaign id.
    """
    try:
        candidates = list(root.glob("*/summary.json"))
    except OSError as exc:
        return None, None, f"control discovery unavailable: {exc}"
    candidates.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    errors = []
    for path in candidates:
        _, data, err = _read_json_object(path, "control summary")
        if err or data is None:
            errors.append(f"{path}: {err or 'not an object'}")
            continue
        campaign_id = data.get("campaign_id")
        required = (
            isinstance(campaign_id, str) and bool(campaign_id)
            and isinstance(data.get("controls"), dict)
            and isinstance(data.get("calibration"), dict)
            and isinstance(data.get("measurement_instrument_commit"), str)
            and isinstance(data.get("production_source_commit"), str)
        )
        if not required:
            continue
        attestation_path = path.with_name("composition_attestation.json")
        _, attestation, attestation_err = _read_json_object(
            attestation_path, "control composition attestation")
        if (attestation_err or attestation is None
                or attestation.get("schema") !=
                "epyc.autokernel.control_composition_attestation.v1"
                or attestation.get("campaign_id") != campaign_id):
            errors.append(f"{path}: matching composition attestation unavailable")
            continue
        selected = dict(data)
        selected["_composition_attestation"] = attestation
        selected["_composition_attestation_path"] = str(attestation_path)
        return path, selected, None
    if errors:
        return None, None, errors[0]
    return None, None, f"no completed control summary found below {root}"


def _control_summary(path: Path | None, data: dict | None,
                     error: str | None, production_head: str | None) -> dict:
    """Project the decision-grade control panel and instrument provenance."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    controls = data.get("controls") if isinstance(data.get("controls"), dict) else {}
    panel_result = (controls.get("panel_result")
                    if isinstance(controls.get("panel_result"), dict) else {})
    panel = panel_result.get("panel") if isinstance(panel_result.get("panel"), dict) else {}
    calibration = (data.get("calibration")
                   if isinstance(data.get("calibration"), dict) else {})
    outputs = (calibration.get("outputs")
               if isinstance(calibration.get("outputs"), dict) else {})
    attestation = (data.get("_composition_attestation")
                   if isinstance(data.get("_composition_attestation"), dict) else {})
    production_source = data.get("production_source_commit")
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "state": data.get("state"),
        "may_rank": data.get("may_rank"),
        "marker": panel.get("marker"),
        "panel": panel,
        "measured_at": data.get("measured_at"),
        "measurement_instrument_commit": data.get(
            "measurement_instrument_commit"),
        "production_source_commit": production_source,
        "anchor_matches_production": bool(
            production_head and production_source == production_head),
        "binary_copy_exact": data.get("binary_copy_exact"),
        "calibration_accepted": calibration.get("accepted"),
        "b_min_blocks": outputs.get("b_min_blocks"),
        "noise_floor": outputs.get("noise_floor_phi"),
        "composition_mode": data.get("composition_mode"),
        "composition_inference_executed": attestation.get("inference_executed"),
        "composition_evidence": data.get("_composition_attestation_path"),
        "promotion_authority": False,
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _gpu_replay_summary(path: Path | None, data: dict | None,
                        error: str | None) -> dict:
    """Project the paired ROCm replay without turning positivity into a pass."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    sampling = (data.get("device_sampling")
                if isinstance(data.get("device_sampling"), dict) else {})
    released = (data.get("device_claim_released")
                if isinstance(data.get("device_claim_released"), dict) else {})
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "verdict": result.get("verdict"),
        "blocks": data.get("blocks"),
        "all_blocks_positive": result.get("all_blocks_positive"),
        "contribution_floor": result.get("contribution_floor"),
        "median_relative_delta": result.get("median_relative_delta"),
        "minimum_relative_delta": result.get("minimum_relative_delta"),
        "device_id": sampling.get("device_id"),
        "device_sample_count": sampling.get("sample_count"),
        "device_sample_source": sampling.get("source"),
        "device_claim_released_at": released.get("released_at"),
        "source_branch": data.get("source_branch"),
        "source_commit": data.get("source_commit"),
        "promotion_authority": False,
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


#: The receipt schemas this panel knows how to project. Kept as a named constant so
#: the page can DECLARE its own coverage rather than implying completeness by silence.
_PROJECTED_RECEIPT_SCHEMAS = {
    "epyc.autokernel.arena_controller_campaign_audit.v1",
    "epyc.autokernel.arena_available_source_campaign_audit.v1",
    "epyc.autokernel.arena_diagnostic_smoke.v1",
    "epyc.autokernel.live_control_preflight.v1",
    "epyc.autokernel.async_prefetch_replay.v1",
}


def _production_kernel_summary(attestation_path: Path,
                               production_repo: Path) -> dict:
    """Read the operator freeze attestation and compare the canonical checkout."""
    present, data, err = _read_json_object(attestation_path,
                                           "production kernel attestation")
    if data is None:
        if err is None:
            # D-1 residual (KRD-AUDIT-20260812). `_read_json_object` returns err=None
            # for a simply-absent file, and this function used to pass that straight
            # through — so the panel could only say "attestation not found" with no
            # reason. The render was made loud earlier; the REASON was still missing,
            # and the same synthesised-sentence pattern already existed one function
            # away in `_read_kernel_contract`. Asymmetry closed.
            err = (f"production kernel freeze attestation not exported — nothing has "
                   f"written {attestation_path}. The production kernel identity is "
                   f"UNPROVEN; do not read this page as confirming which kernel is live.")
        return {"available": False, "artifact_present": present,
                "evidence": str(attestation_path), "error": err}
    observed_branch = observed_head = checkout_error = None
    try:
        proc = subprocess.run(
            ["git", "-C", str(production_repo), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        head = subprocess.run(
            ["git", "-C", str(production_repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        if proc.returncode == 0:
            observed_branch = proc.stdout.strip() or None
        else:
            checkout_error = (proc.stderr.strip()
                              or f"git symbolic-ref exited {proc.returncode}")
        if head.returncode == 0:
            observed_head = head.stdout.strip() or None
        elif checkout_error is None:
            checkout_error = head.stderr.strip() or f"git rev-parse exited {head.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        checkout_error = str(exc)
    expected_branch = data.get("production_branch")
    expected_head = data.get("production_head")
    working_tree = _working_tree_state(production_repo)
    return {
        "available": True,
        "decision": data.get("decision"),
        "status": data.get("status"),
        "frozen": data.get("production_frozen"),
        "branch": expected_branch,
        "head": expected_head,
        "version": data.get("production_version"),
        "binary_sha256": data.get("production_binary_sha256") or {},
        "ggml": data.get("ggml"),
        "ratified_at": data.get("ratified_at"),
        "scope": data.get("scope"),
        "evidence": str(attestation_path),
        "checkout": {
            "path": str(production_repo),
            "branch": observed_branch,
            "head": observed_head,
            "matches_attestation": (observed_branch == expected_branch
                                    and observed_head == expected_head),
            "error": checkout_error,
            **working_tree,
        },
    }


def _sha256_file(path: Path) -> tuple:
    """``(digest_or_None, error_or_None)``. Absence is not an error here — the caller
    distinguishes *missing binary* from *unreadable binary*, and both must stay loud."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"unreadable: {exc}"
    if size > _MAX_HASHED_BINARY_BYTES:
        return None, f"refusing to hash {size} bytes (> {_MAX_HASHED_BINARY_BYTES})"
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        return None, f"unreadable: {exc}"
    return digest.hexdigest(), None


def _binary_identity(label: str, path: Path, expected_sha256: str | None) -> dict:
    """One attested binary, compared live.

    THREE-VALUED ON PURPOSE, because two of the states are the ones that hurt:
    ``matches`` True (identity proven), False (DRIFT — something rebuilt or replaced a
    frozen binary), or None (*unknown* — the file is missing, unreadable, or the
    attestation carries no digest to compare against). A missing binary must never
    read as a passing one, which a boolean would force it to.
    """
    observed, error = _sha256_file(path)
    present = observed is not None
    if expected_sha256 and observed:
        matches = observed == expected_sha256
    else:
        matches = None
    if error is None and not present:
        error = "binary absent — the freeze attests a file that is not on disk"
    elif matches is False:
        error = ("BINARY DRIFT — on-disk digest does not match the operator "
                 "attestation; a frozen binary was rebuilt or replaced")
    elif expected_sha256 is None and present:
        error = "attestation carries no digest for this binary — identity unverifiable"
    return {"label": label, "path": str(path), "present": present,
            "expected_sha256": expected_sha256, "observed_sha256": observed,
            "matches": matches, "error": error}


def _working_tree_state(repo: Path) -> dict:
    """Three-valued working-tree cleanliness, including untracked paths."""
    try:
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1",
             "--untracked-files=all"], capture_output=True, text=True,
            timeout=5.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"clean": None, "dirty_count": None, "dirty_paths": [],
                "status_error": str(exc)}
    if status.returncode != 0:
        return {"clean": None, "dirty_count": None, "dirty_paths": [],
                "status_error": (status.stderr.strip()
                                 or f"git status exited {status.returncode}")}
    rows = [row for row in status.stdout.splitlines() if row]
    return {"clean": not rows, "dirty_count": len(rows),
            "dirty_paths": rows[:20], "status_error": None}


def _checkout_identity(repo: Path, expected_branch: str | None,
                       expected_head: str | None) -> dict:
    """Live branch/head of a kernel tree vs what the attestation froze."""
    observed_branch = observed_head = error = None
    try:
        branch = subprocess.run(
            ["git", "-C", str(repo), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        if branch.returncode == 0:
            observed_branch = branch.stdout.strip() or None
        else:
            error = branch.stderr.strip() or f"git symbolic-ref exited {branch.returncode}"
        if head.returncode == 0:
            observed_head = head.stdout.strip() or None
        elif error is None:
            error = head.stderr.strip() or f"git rev-parse exited {head.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = str(exc)
    if observed_branch is None and observed_head is None and error is None:
        error = "kernel tree unreadable — no branch or head could be resolved"
    matches = None
    if observed_branch is not None and observed_head is not None:
        matches = (observed_branch == expected_branch and observed_head == expected_head)
    return {"path": str(repo), "branch": observed_branch, "head": observed_head,
            "expected_branch": expected_branch, "expected_head": expected_head,
            "matches_attestation": matches, "error": error,
            **_working_tree_state(repo)}


def _ggml_generation_identity(repo: Path, expected: str | None) -> dict:
    """Compare attested ggml generation with the checked-out tree metadata."""
    cmake = repo / "ggml" / "CMakeLists.txt"
    try:
        source = cmake.read_text(encoding="utf-8")
    except OSError as exc:
        return {"expected": expected, "observed": None, "matches": None,
                "evidence": str(cmake), "error": f"ggml generation unverifiable: {exc}"}
    fields = {}
    for name in ("MAJOR", "MINOR", "PATCH"):
        match = re.search(rf"set\(GGML_VERSION_{name}\s+([0-9]+)\)", source)
        if match:
            fields[name] = match.group(1)
    observed = ".".join(fields.get(name, "") for name in ("MAJOR", "MINOR", "PATCH"))
    if not observed or ".." in observed:
        return {"expected": expected, "observed": None, "matches": None,
                "evidence": str(cmake),
                "error": "ggml generation unverifiable — version fields incomplete"}
    if not expected:
        return {"expected": None, "observed": observed, "matches": None,
                "evidence": str(cmake),
                "error": "ggml generation observed but not attested"}
    matches = observed == expected
    return {"expected": expected, "observed": observed, "matches": matches,
            "evidence": str(cmake),
            "error": None if matches else "GGML GENERATION DRIFT — tree differs from attestation"}


def _speech_kernel_summary(attestation_path: Path | None = None) -> dict:
    """whisper.cpp and qwentts.cpp — the two thirds of the freeze nobody was showing.

    WHY THIS EXISTS (KRD-AUDIT-20260812). The freeze covers a production KERNEL SET —
    llama.cpp `production-consolidated-v9` plus whisper.cpp and qwentts.cpp at
    `production-speech-v1` — and the dashboard projected only llama. Measured on the
    live surface before this change: the strings `whisper`, `qwentts`, `speech` and
    `ggml` appeared ZERO times anywhere in `autokernel_current_state()`. Two of three
    frozen kernels could drift, be rebuilt, or vanish and no panel would say so.

    THE STALE-SOURCE TRAP, and it is why llama is NOT read from here. This attestation
    also carries a `kernels.llama_cpp` block — pinned at **v8** (`67a433bf`, binary
    10107) and labelled in its own text *"unchanged by this ratification; recorded for
    completeness"*. It was accurate on 2026-07-31 and was superseded by the v9 freeze
    on 08-11. Folding the set from this one file would therefore project a **stale
    llama identity that still looks internally consistent** — the failure this audit
    was commissioned to find, not to reproduce. llama comes from the v9 attestation;
    this function deliberately ignores its own llama block.

    ggml GENERATION IS PROJECTED because it is load-bearing, not decorative: the three
    trees run three different ggml generations (0.18.0 / 0.17.0 / v9's own), and
    `CLAUDE.md` records that a binary inheriting another tree's ggml *runs silently
    wrong*. A number that must match and is shown nowhere is exactly the class of fact
    this dashboard exists to surface.
    """
    attestation_path = attestation_path or SPEECH_KERNEL_ATTESTATION
    present, data, err = _read_json_object(attestation_path, "speech kernel attestation")
    if data is None:
        if err is None:
            err = (f"speech kernel freeze attestation not exported — nothing has "
                   f"written {attestation_path}. Two of the three frozen kernels "
                   f"(whisper.cpp, qwentts.cpp) are therefore UNVERIFIED here.")
        return {"available": False, "artifact_present": present,
                "evidence": str(attestation_path), "error": err, "kernels": []}
    kernels = []
    for key, title in (("whisper_cpp", "whisper.cpp (STT)"),
                       ("qwentts_cpp", "qwentts.cpp (TTS)")):
        spec = data.get("kernels", {}).get(key)
        if not isinstance(spec, dict):
            kernels.append({"key": key, "title": title, "available": False,
                            "error": f"attestation carries no `{key}` block"})
            continue
        binary = spec.get("binary")
        kernels.append({
            "key": key, "title": title, "available": True,
            "tree": spec.get("tree"), "branch": spec.get("branch"),
            "head": spec.get("commit"), "ggml": spec.get("ggml"),
            "load_bearing_patch": spec.get("load_bearing_patch"),
            "checkout": _checkout_identity(Path(spec.get("tree") or "/nonexistent"),
                                           spec.get("branch"), spec.get("commit")),
            "binary": _binary_identity(title, Path(binary), spec.get("binary_sha256"))
            if binary else {"label": title, "present": False, "matches": None,
                            "error": "attestation names no binary for this kernel"},
        })
    return {"available": True, "ratification": data.get("ratification"),
            "ratified_at": data.get("date_utc"), "scope": data.get("scope"),
            "evidence": str(attestation_path), "error": None, "kernels": kernels}


def _elf_dynamic(path: Path) -> tuple:
    """``(needed, runpath_entries, error)`` from the ELF dynamic section.

    READ-ONLY AND NON-EXECUTING, deliberately. The research contract
    (`verify_ggml_linkage.sh`) uses `ldd`, which invokes the dynamic loader; the
    follow-up brief forbids executing the production binary, so this parses
    `readelf -d` instead. Strictly weaker than `ldd` — it cannot see dlopened
    backends — and that limit is reported rather than hidden.
    """
    try:
        proc = subprocess.run(["readelf", "-d", str(path)],
                              capture_output=True, text=True, timeout=10.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], [], f"readelf unavailable: {exc}"
    if proc.returncode != 0:
        return [], [], (proc.stderr.strip() or f"readelf exited {proc.returncode}")
    needed, runpath = [], []
    for line in proc.stdout.splitlines():
        if "(NEEDED)" in line and "[" in line:
            needed.append(line.split("[", 1)[1].rstrip("]").strip())
        elif ("(RUNPATH)" in line or "(RPATH)" in line) and "[" in line:
            raw = line.split("[", 1)[1].rstrip("]").strip()
            runpath.extend([e for e in raw.split(":") if e])
    return needed, runpath, None


def _ambient_foreign_ggml_dirs() -> dict:
    """Entries on the SERVER PROCESS's ``LD_LIBRARY_PATH`` that carry a libggml.

    WHY THIS IS THE FIRST THING CHECKED. `LD_LIBRARY_PATH` is consulted BEFORE a
    binary's own `DT_RUNPATH`, so a single ggml-bearing directory on it overrides
    every tree-local guarantee the binaries carry. That is not hypothetical:
    INC-20260731-ggml-linkage-silent-cpu-fallback is exactly this — a HIP-built
    whisper-cli loaded the production CPU-only ggml, found no GPU, and ran full-CPU
    while printing `use gpu = 1`. The run completes, the output is well-formed, and
    only the throughput is quietly wrong.

    SCOPE, STATED because it is easy to overclaim: this observes the environment of
    the DASHBOARD PROCESS, not of any launcher. A clean reading here does not prove a
    launcher is clean, and a dirty reading does not prove a specific measurement was
    contaminated — it proves the host handed THIS process a contaminated path, which
    is evidence about the environment sessions inherit. The durable config
    (`/etc/environment`, devcontainer) is the authority on whether the incident fix is
    still applied; a stale shell can carry removed entries until it is restarted.
    """
    raw = os.environ.get("LD_LIBRARY_PATH", "")
    entries, carriers = [e for e in raw.split(":") if e], []
    for entry in entries:
        try:
            if any(f.name.startswith("libggml") for f in Path(entry).iterdir()):
                carriers.append(entry)
        except OSError:
            continue
    return {"ld_library_path": entries, "ggml_bearing_entries": carriers,
            "clean": not carriers,
            "note": ("observed for the DASHBOARD PROCESS only — this is evidence about "
                     "the environment sessions inherit, not proof about any launcher")}


def _linkage_evidence(binary: Path, tree_root: Path) -> dict:
    """Does this binary's ggml family resolve inside its OWN tree?"""
    needed, runpath, error = _elf_dynamic(binary)
    if error:
        return {"binary": str(binary), "tree_root": str(tree_root), "error": error,
                "verified": None, "runpath": [], "ggml_libs": []}
    origin = binary.parent
    resolved_runpath = [str(origin) if e == "$ORIGIN" else e.replace("$ORIGIN", str(origin))
                        for e in runpath]
    # One transitive hop: llama-server NEEDs only its impl .so, and the ggml family
    # arrives through that. Stopping at the direct NEEDED set would report "no ggml
    # libraries" for the two llama binaries — an absence that is an artifact of where
    # we stopped looking, not a property of the binary.
    frontier = list(needed)
    for name in list(needed):
        if name.startswith("libllama-server-impl"):
            child = origin / name
            if child.exists():
                more, _, child_err = _elf_dynamic(child)
                if not child_err:
                    frontier.extend(more)
    libs, foreign, unresolved = [], [], []
    for name in sorted(set(frontier)):
        if not name.startswith(_GGML_FAMILY):
            continue
        where = None
        for candidate_dir in resolved_runpath or [str(origin)]:
            if (Path(candidate_dir) / name).exists():
                where = str(Path(candidate_dir) / name)
                break
        inside = bool(where) and Path(where).resolve().is_relative_to(tree_root.resolve())
        if where is None:
            unresolved.append(name)
        elif not inside:
            foreign.append({"lib": name, "resolved": where})
        libs.append({"lib": name, "resolved": where, "inside_tree": inside if where else None})
    verified = (not foreign and not unresolved and bool(libs))
    return {
        "binary": str(binary), "tree_root": str(tree_root),
        "runpath": resolved_runpath, "ggml_libs": libs,
        "foreign": foreign, "unresolved": unresolved,
        "verified": verified if libs else None,
        "error": (None if libs else
                  "no ggml-family library found in the ELF dynamic section — linkage "
                  "unverifiable from a static read (backends may be dlopened)"),
        "method": "readelf -d (non-executing); weaker than ldd — cannot see dlopened backends",
    }


def _stable_link_projection() -> list:
    """The four stable production links, and what they actually resolve to."""
    out = []
    for name, (expected_dir, binary_name) in PRODUCTION_STABLE_LINKS.items():
        link = PRODUCTION_STABLE_LINK_ROOT / name
        entry = {"name": name, "link": str(link), "expected_target": expected_dir,
                 "binary_name": binary_name}
        try:
            is_link = link.is_symlink()
            target = str(link.resolve()) if link.exists() else None
        except OSError as exc:
            entry.update({"present": False, "is_symlink": False, "target": None,
                          "matches_expected": None, "binary_present": None,
                          "error": f"unreadable: {exc}"})
            out.append(entry)
            continue
        matches = (target == expected_dir) if target else None
        binary_present = bool(target) and (Path(target) / binary_name).is_file()
        error = None
        if target is None:
            error = ("stable link absent or dangling — launchers that follow the "
                     "runbook would resolve nothing")
        elif not matches:
            error = f"stable link repointed: resolves to {target}, expected {expected_dir}"
        elif not binary_present:
            error = f"stable link resolves, but {binary_name} is not inside its target"
        entry.update({"present": target is not None, "is_symlink": is_link,
                      "target": target, "matches_expected": matches,
                      "binary_present": binary_present, "error": error})
        out.append(entry)
    return out


def production_kernel_set(attestation_path: Path | None = None,
                          production_repo: Path | None = None,
                          speech_attestation_path: Path | None = None) -> dict:
    """The COMPLETE frozen kernel set, folded to one honest verdict.

    Three kernels, four binaries. `production_kernel` (llama only) is left untouched
    beside this for existing consumers; this is the set-level view, and it is one
    panel rather than a second llama panel — the audit brief explicitly warned against
    duplicating what already renders.

    THE FOLD IS DELIBERATELY PESSIMISTIC. `intact` is True only when every kernel and
    every binary is proven — any drift, absence, unreadable tree or missing digest
    makes it False, and `unverified` records how many facts could not be established
    at all. A set-level green that can be produced by a kernel we failed to read is
    the same absence-tolerance that let incident 8 render a dead loop as a clean page.
    """
    llama = _production_kernel_summary(attestation_path or PRODUCTION_KERNEL_ATTESTATION,
                                       production_repo or PRODUCTION_KERNEL_REPO)
    speech = _speech_kernel_summary(speech_attestation_path)

    binaries = []
    llama_digests = llama.get("binary_sha256") or {}
    for slot, path in PRODUCTION_LLAMA_BINARIES.items():
        binaries.append(_binary_identity(f"llama.cpp {slot.upper()}", path,
                                         llama_digests.get(slot)))
    for kernel in speech.get("kernels", []):
        if kernel.get("binary"):
            binaries.append(kernel["binary"])

    members, alarms = [], []
    llama_ck = llama.get("checkout") or {}
    llama_generation = _ggml_generation_identity(
        production_repo or PRODUCTION_KERNEL_REPO, llama.get("ggml"))
    members.append({"key": "llama_cpp", "title": "llama.cpp",
                    "available": llama.get("available"),
                    "branch": llama.get("branch"), "head": llama.get("head"),
                    "version": llama.get("version"), "ggml": llama.get("ggml"),
                    "ggml_generation": llama_generation,
                    "matches_attestation": llama_ck.get("matches_attestation"),
                    "working_tree_clean": llama_ck.get("clean"),
                    "dirty_count": llama_ck.get("dirty_count"),
                    "dirty_paths": llama_ck.get("dirty_paths") or [],
                    "error": llama.get("error") or llama_ck.get("error")})
    for kernel in speech.get("kernels", []):
        tree = Path(kernel.get("tree") or "/nonexistent")
        members.append({
            "key": kernel.get("key"), "title": kernel.get("title"),
            "available": kernel.get("available"),
            "branch": kernel.get("branch"), "head": kernel.get("head"),
            "version": None, "ggml": kernel.get("ggml"),
            "ggml_generation": _ggml_generation_identity(tree, kernel.get("ggml")),
            "matches_attestation": (kernel.get("checkout") or {}).get("matches_attestation"),
            "working_tree_clean": (kernel.get("checkout") or {}).get("clean"),
            "dirty_count": (kernel.get("checkout") or {}).get("dirty_count"),
            "dirty_paths": (kernel.get("checkout") or {}).get("dirty_paths") or [],
            "error": kernel.get("error") or (kernel.get("checkout") or {}).get("error")})

    if not llama.get("available"):
        alarms.append("llama.cpp freeze attestation unavailable — production identity unproven")
    if not speech.get("available"):
        alarms.append("speech kernel freeze attestation unavailable — whisper.cpp and "
                      "qwentts.cpp identities unproven")
    for member in members:
        if member.get("matches_attestation") is False:
            alarms.append(f"{member['title']}: tree does NOT match attestation (drift)")
        elif member.get("available") and member.get("matches_attestation") is None:
            alarms.append(f"{member['title']}: tree identity could not be established")
        if member.get("working_tree_clean") is False:
            alarms.append(
                f"{member['title']}: frozen working tree is DIRTY "
                f"({member.get('dirty_count')} paths; no mutation performed by dashboard)")
        elif member.get("available") and member.get("working_tree_clean") is None:
            alarms.append(f"{member['title']}: working-tree cleanliness unverified")
        generation = member.get("ggml_generation") or {}
        if generation.get("matches") is False:
            alarms.append(f"{member['title']}: GGML GENERATION DRIFT")
        elif generation.get("matches") is None:
            alarms.append(f"{member['title']}: ggml generation unverified")
    for binary in binaries:
        if binary.get("matches") is False:
            alarms.append(f"{binary['label']}: BINARY DRIFT vs operator attestation")
        elif not binary.get("present"):
            alarms.append(f"{binary['label']}: attested binary absent from disk")

    # --- stable links + tree-local linkage (KRD-AUDIT-20260812 follow-up) ---
    stable_links = _stable_link_projection()
    for link in stable_links:
        if link.get("error"):
            alarms.append(f"stable link `{link['name']}`: {link['error']}")

    ambient = _ambient_foreign_ggml_dirs()
    if not ambient["clean"]:
        alarms.append(
            "LD_LIBRARY_PATH carries ggml-bearing directories "
            f"({', '.join(ambient['ggml_bearing_entries'])}) — it is consulted BEFORE "
            "each binary's RUNPATH, so a speech kernel launched from this environment "
            "can silently load llama's ggml and run wrong while reporting success "
            "(INC-20260731). Observed for the dashboard process; check the launcher.")

    linkage = []
    for name, (expected_dir, binary_name) in PRODUCTION_STABLE_LINKS.items():
        tree_root = Path(expected_dir)
        # The tree that owns the libraries: for llama both build dirs live under the
        # one clone, so the ROOT is the tree, not the build dir.
        for anchor in ("/mnt/raid0/llm/llama.cpp", "/mnt/raid0/llm/whisper.cpp",
                       "/mnt/raid0/llm/qwentts.cpp"):
            if expected_dir.startswith(anchor):
                tree_root = Path(anchor)
                break
        evidence = _linkage_evidence(Path(expected_dir) / binary_name, tree_root)
        evidence["link"] = name
        linkage.append(evidence)
        if evidence.get("foreign"):
            alarms.append(f"{name}: ggml resolves OUTSIDE its own tree — "
                          + ", ".join(f"{f['lib']} -> {f['resolved']}" for f in evidence["foreign"]))
        elif evidence.get("verified") is None:
            alarms.append(f"{name}: tree-local linkage UNVERIFIABLE "
                          f"({evidence.get('error') or 'no evidence'})")

    links_ok = sum(1 for l in stable_links
                   if l.get("matches_expected") and l.get("binary_present"))
    linkage_ok = sum(1 for e in linkage if e.get("verified") is True)

    proven = sum(1 for b in binaries if b.get("matches") is True)
    unverified = sum(1 for b in binaries if b.get("matches") is None)
    trees_proven = sum(1 for m in members if m.get("matches_attestation") is True)
    generations_proven = sum(
        1 for member in members
        if (member.get("ggml_generation") or {}).get("matches") is True)
    return {
        "schema": "epyc.production_kernel_set.v1",
        "expected_kernels": 3,
        "expected_binaries": len(PRODUCTION_LLAMA_BINARIES) + 2,
        "kernels_present": len(members),
        "trees_matching": trees_proven,
        "binaries_proven": proven,
        "binaries_unverified": unverified,
        "stable_links": stable_links,
        "stable_links_ok": links_ok,
        "linkage": linkage,
        "linkage_verified": linkage_ok,
        "ggml_generations_proven": generations_proven,
        "ambient_library_path": ambient,
        # PESSIMISTIC, and now over five independent facts rather than two: the
        # attestations, the trees, the binary digests, the stable links launchers
        # actually follow, and proof each binary's ggml comes from its own tree. A set
        # that is byte-identical but reachable only through a repointed link, or whose
        # libraries resolve into another tree, is not intact in any sense a measurement
        # can rely on.
        "intact": (llama.get("available") is True and speech.get("available") is True
                   and trees_proven == len(members) == 3
                   and all(m.get("working_tree_clean") is True for m in members)
                   and proven == len(binaries) == 4
                   and links_ok == len(stable_links) == 4
                   and linkage_ok == len(linkage) == 4
                   and generations_proven == len(members) == 3
                   and ambient["clean"]),
        "alarms": alarms,
        "members": members,
        "binaries": binaries,
        "llama": llama,
        "speech": speech,
        "evidence": [str(attestation_path or PRODUCTION_KERNEL_ATTESTATION),
                     str(speech_attestation_path or SPEECH_KERNEL_ATTESTATION)],
    }


def autokernel_current_state(probe_root: Path | None = None,
                             attestation_path: Path | None = None,
                             production_repo: Path | None = None,
                             control_root: Path | None = None,
                             state_root: Path | None = None) -> dict:
    """Evidence-backed current posture, separate from runtime liveness.

    These receipts describe audits and a diagnostic smoke.  They cannot certify
    a live controller, rank the partial panel, or promote/freeze a kernel.
    """
    probe_root = probe_root or AUTOKERNEL_PROBE_ROOT
    control_root = control_root or AUTOKERNEL_CONTROL_ROOT
    state_root = state_root or AUTOKERNEL_STATE_ROOT
    attestation_path = attestation_path or PRODUCTION_KERNEL_ATTESTATION
    production_repo = production_repo or PRODUCTION_KERNEL_REPO
    fixed_path, fixed, fixed_err = _latest_autokernel_receipt(
        probe_root, "full-eight-arm-refusal.json",
        "epyc.autokernel.arena_controller_campaign_audit.v1")
    available_path, available, available_err = _latest_autokernel_receipt(
        probe_root, "available-source-six-arm.json",
        "epyc.autokernel.arena_available_source_campaign_audit.v1")
    smoke_path, smoke, smoke_err = _latest_autokernel_receipt(
        probe_root, "smoke-receipt.json",
        "epyc.autokernel.arena_diagnostic_smoke.v1")
    preflight_path, preflight, preflight_err = _latest_autokernel_receipt(
        probe_root, "preflight.json",
        "epyc.autokernel.live_control_preflight.v1")
    replay_path, replay, replay_err = _latest_autokernel_receipt(
        probe_root, "receipt.json",
        "epyc.autokernel.async_prefetch_replay.v1")
    control_path, control, control_err = _latest_control_summary(control_root)
    production = _production_kernel_summary(attestation_path, production_repo)
    production_head = production.get("head") if production.get("available") else None
    return {
        "schema": "epyc.autokernel.dashboard_current_state.v1",
        "role": ("EVIDENCE SNAPSHOT ONLY — audits and diagnostic smokes do not "
                 "report controller liveness or authorize promotion"),
        "fixed_campaign": _campaign_audit_summary(
            fixed_path, fixed, fixed_err),
        "available_source_diagnostic": _campaign_audit_summary(
            available_path, available, available_err),
        "empirical_smoke": _smoke_receipt_summary(
            smoke_path, smoke, smoke_err),
        "instrument_preflight": _control_preflight_summary(
            preflight_path, preflight, preflight_err),
        "decision_controls": _control_summary(
            control_path, control, control_err, production_head),
        "gpu_prefetch_replay": _gpu_replay_summary(
            replay_path, replay, replay_err),
        "loop_engineering": _loop_engineering_summary(state_root),
        "fault_rehearsal": _fault_rehearsal_summary(state_root),
        # SCOPE, DECLARED (KRD-AUDIT-20260812). This panel projects a CURATED set of
        # receipt schemas, not everything under the probe root — measured at audit time:
        # 5 schemas projected, 29 further schemas across 98 receipt files present on
        # disk and not shown. Most are legitimately intermediate (checkpoints, profile
        # captures), so the fix is not "render them all"; it is to stop a curated view
        # reading as a complete one. Naming the scope where the answer is printed is
        # the same rule the health-probe finding turned on: a reader acts on the pass.
        "receipt_coverage": {
            "projected_schemas": sorted(_PROJECTED_RECEIPT_SCHEMAS),
            "probe_root": str(probe_root),
            "note": ("CURATED VIEW — receipts whose schema is not in "
                     "`projected_schemas` exist under `probe_root` and are NOT shown "
                     "here. Absence from this panel is not absence of evidence."),
        },
        "production_kernel": production,
        # Singular `production_kernel` above is PRESERVED for existing consumers;
        # this is the set-level fold over all three frozen kernels and four binaries.
        "production_kernel_set": production_kernel_set(
            attestation_path, production_repo),
        "promotion_claim": False,
    }


def autokernel_activity(repo: Path | None = None,
                        state_root: Path | None = None,
                        probe_root: Path | None = None,
                        attestation_path: Path | None = None,
                        production_repo: Path | None = None,
                        control_root: Path | None = None) -> dict:
    """Live implementation/research context that cannot affect runtime health."""
    repo = repo or AUTOKERNEL_RESEARCH_REPO
    state_root = state_root or AUTOKERNEL_STATE_ROOT
    return {
        "schema": "epyc.autokernel.dashboard_activity.v1",
        "role": ("PRESENTATION CONTEXT ONLY — this does not report controller "
                 "liveness and does not affect _freshness or /api/health"),
        "research_repo": str(repo),
        "implementation": _autokernel_git_activity(repo),
        "work_bundles": _autokernel_work_bundles(repo),
        "durable_state": _autokernel_journal_inventory(state_root),
        "probe_receipts": _autokernel_probe_receipts(state_root),
        "current_state": autokernel_current_state(
            probe_root, attestation_path, production_repo, control_root, state_root),
    }


def kernel_payload() -> dict:
    """Read the kernel dashboard contract (v2, or legacy v1), tolerating absence.

    The hub renders the terminal contract plus presentation-only activity;
    ``autokernel.dashboard`` in epyc-inference-research owns the contract and is
    the only writer. Activity context never enters the freshness observation.

    THE HUB'S OWN FIELDS ARE UNDERSCORED, and that is a seam rule rather than a
    style: ``contract_version`` is a key the PRODUCER owns (it writes the integer
    ``2``, and ``schemas.validate_kernel_dashboard_v2`` requires an integer), and
    this function used to overwrite it in place with the string ``"v2"``. The
    consequence was that the document served at ``/api/kernel`` no longer
    validated under its own producer's validator — one field, changed type,
    silently, by the consumer. Derived-by-the-hub facts now live under
    ``_contract_version`` / ``_freshness`` / ``_render``, so what the hub serves
    is the producer's document plus additions the producer will never collide
    with.
    """
    present, data = _read_kernel_contract()
    # ``present`` alone is not enough: a corrupt file is present, and the degraded
    # shell carries no ``schema``, which ``kernel_contract_version`` would read as
    # the unlabelled-legacy shape and report as "v1".
    version = (None if not present or data.get(READER_ERROR_KEY)
               else kernel_contract_version(data))
    data["_contract_version"] = version
    data["_freshness"] = _panel_envelope(
        "kernel", _kernel_observation(data, artifact_present=present))
    data["_render"] = _kernel_render(data, version, present, data["_freshness"])
    # Live implementation and calibration activity is useful even while the
    # first campaign contract is absent.  It stays separate from the Observation
    # above so a new commit or A/A result can never resurrect a dead controller.
    data["_activity"] = autokernel_activity()
    return data


# --------------------------------------------------------------- session bus (M2)
#
# Renders the session bus's file state. The hub OWNS nothing here: the
# coordinator-daemon owns queue.jsonl and inbox/*, each agent owns its own
# outbox/heartbeat/cursor. Read-only, fails soft, never writes.

_BUS_ROOT = _REPO_ROOT / "coordination" / "session-bus"
_HEARTBEAT_WARN_S = panels.source("bus").warn_s
_HEARTBEAT_STALE_S = panels.source("bus").stale_s


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
    # A queue file that exists and folds to zero rows is REPORTED-AND-EMPTY; a
    # queue file that is not there at all is UNSOURCED. Both render as an empty
    # table, so the difference has to live on the wire.
    queue_present = (_BUS_ROOT / "queue.jsonl").exists()
    return {
        "generated_at": (datetime.fromtimestamp(generated_at, timezone.utc).isoformat()
                         if generated_at else None),
        "count": len(rows),
        "by_status": by_status,
        "by_lane": by_lane,
        "none_lane_ready_depth": none_ready,
        "rows": rows,
        "alarms": alarms,
        "_freshness": _panel_envelope("queue", panels.Observation(
            artifact_present=queue_present,
            timestamp=generated_at,
            source="queue.jsonl rows[].ts",
            populated=bool(rows),
            detail=None if queue_present else
            "coordination/session-bus/queue.jsonl does not exist",
            watermark=None if generated_at is None else f"{len(rows)}:{generated_at}",
        )),
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
        "_freshness": _panel_envelope("bus", panels.Observation(
            # Does the bus tree EXIST — not "could this interpreter parse it".
            # PyYAML is optional here, and deriving presence from a parse made a
            # stdlib-only hub report "the session bus is not initialised in this
            # checkout" over a perfectly healthy bus.
            artifact_present=(_BUS_ROOT / "config.yaml").exists(),
            timestamp=None if not ages else now - min(ages),
            source="heartbeats/*.json mtime (freshest)",
            populated=bool(agents),
            detail=config.get("_error"),
        )),
    }


#: The shell for "no outcome contract could be read". ``blockers`` is **null, not
#: ``[]``** for the same reason ``_KERNEL_ABSENT`` uses nulls: ``[]`` is a CLAIM
#: — "the exporter looked and there are no blockers" — and making an absent
#: producer emit it is the conflation this surface exists to end. The deployed
#: page reads it through ``Array.isArray(op.blockers)?op.blockers:[]``
#: (``static/handoffs.html``), so absence tolerance is unchanged; only the wire is.
_OUTCOME_EMPTY = {
    "outcome_progress": {"status": "missing", "blockers": None},
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
        # A JSON object that is not an outcome contract. It keeps its
        # ``generated_at`` for display, but READER_ERROR_KEY stops that value
        # dating a report: without it, any object carrying a fresh
        # ``generated_at`` read as fresh / observed / empty / watchdog-ok — a
        # document the hub could not understand, rendered clean.
        err = "autopilot outcome contract missing 'outcome_progress'"
        return {**_OUTCOME_EMPTY, "generated_at": raw.get("generated_at"),
                "error": err, READER_ERROR_KEY: err}
    data.setdefault("observation_notice", _OUTCOME_EMPTY["observation_notice"])
    data.setdefault("generated_at", None)
    return data


def _read_outcome_contract() -> tuple:
    """Read the autopilot outcome contract → ``(artifact_present, data)``.

    Returns the honest degraded ``_OUTCOME_EMPTY`` (with an ``error`` reason and
    ``generated_at=None``) on any absence/corruption — the card must never 500,
    and an absent export is the *expected* default (no exporter writes it yet).
    """
    present, raw, err = _read_json_object(
        AUTOPILOT_OUTCOME_JSON, "autopilot outcome contract")
    if raw is not None:
        return True, _normalize_outcome_contract(raw)
    if err is None:
        return False, {**_OUTCOME_EMPTY, "generated_at": None,
                       "error": "autopilot outcome contract not exported yet — the "
                                "orchestrator loop (:8000) has not written it."}
    return present, {**_OUTCOME_EMPTY, "generated_at": None,
                     "error": err, READER_ERROR_KEY: err}


def _outcome_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    """Date the outcome contract by ``generated_at`` — the moment the exporter last
    READ the journal — never by file mtime.

    THIS is the trial-1302 panel. The autopilot exports on a fast cadence while it
    runs, so ``silent_after_s`` (6 h) turns "AutoPilot died and nobody noticed for
    ~23 h" into a named ``stopped_reporting`` verdict on the fold. The watermark
    arm covers the other half: an exporter that keeps writing a fresh
    ``generated_at`` while ``latest_trial_id`` never moves is alive and making no
    progress, which reads identical on a timestamp alone.
    """
    evidence = str(AUTOPILOT_OUTCOME_JSON)
    if data.get(READER_ERROR_KEY):
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY], evidence=evidence)
    op = data.get("outcome_progress")
    op = op if isinstance(op, dict) else {}
    status = op.get("status")
    watermark = None
    if op.get("latest_trial_id") is not None:
        watermark = f"trial:{op.get('latest_trial_id')}"
    return panels.Observation(
        artifact_present=artifact_present,
        timestamp=_parse_semantic_timestamp(data.get("generated_at")),
        source="generated_at",
        populated=None if not op else (status != "missing"),
        detail=data.get("error"),
        watermark=watermark,
        evidence=evidence,
        # THE COMPLIANT PATH, and the reason a stopped autopilot may now degrade
        # the fold. A Phase-0 stop-loss pause is a legitimate long silence — but
        # only the loop can tell a pause from a crash, and a paused loop still
        # exports. So the pause must be DECLARED, exactly as the AutoKernel
        # controller declares ``sections.campaign.stopped``. Undeclared silence
        # past the 6 h budget is what killed trial 1302 and is no longer excused
        # by ``gates_health``.
        producer_idle=bool(op.get("paused") is True
                           or status in ("paused", "stopped", "idle")),
    )


def _outcome_contract_freshness(data: dict, *, artifact_present: bool = True) -> dict:
    """Classify outcome-contract freshness from the export's semantic timestamp.

    NOTE: export-freshness only proves the pipeline is alive; the actual *stall*
    signal is ``trials_since_frontier``/``trials_since_promotion`` in the contract
    body, which the card surfaces directly — and which the watchdog's watermark arm
    now turns into a verdict rather than a number the operator has to read.
    """
    return _panel_envelope("outcome", _outcome_observation(
        data, artifact_present=artifact_present))


def outcome_payload() -> dict:
    """Read the autopilot outcome contract, tolerating absence/corruption.

    Degrade-honestly boundary: the outcome KPIs are produced by the orchestrator
    autopilot loop (a NON-dashboard surface this hub does not own). The hub only
    mirrors a file-backed export if present; when it is absent (today's default)
    the payload is the honest 'not exported' state that the card points at :8000.
    """
    present, data = _read_outcome_contract()
    data["_freshness"] = _outcome_contract_freshness(data, artifact_present=present)
    return data


def _read_benchmark_inventory() -> tuple:
    """Read the benchmark-artifact inventory → ``(artifact_present, data)``."""
    present, data, err = _read_json_object(
        BENCHMARK_ARTIFACT_INVENTORY, "benchmark artifact inventory")
    if data is not None:
        return True, data
    shell = {"status": "not_built", "path": str(BENCHMARK_ARTIFACT_INVENTORY),
             "generated_at": None, "models": None}
    if err is None:
        return False, {**shell,
                       "error": "benchmark artifact inventory has never been built"}
    return present, {**shell, "error": err, READER_ERROR_KEY: err}


def _benchmark_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    if data.get(READER_ERROR_KEY):
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY])
    models = data.get("models")
    return panels.Observation(
        artifact_present=artifact_present,
        timestamp=_parse_semantic_timestamp(data.get("generated_at")),
        source="generated_at",
        populated=None if models is None else bool(models),
        detail=data.get("error"),
    )


def benchmark_artifacts_payload() -> dict:
    present, data = _read_benchmark_inventory()
    data["_freshness"] = _panel_envelope(
        "benchmark_artifacts", _benchmark_observation(data, artifact_present=present))
    return data


# --------------------------------------------------------- dashboard directory
#
# RTG-47 Phase 0. ``dashboard/registry.json`` is the SSOT list of dashboard
# surfaces; this panel serves it with a live health-path probe per unique
# ``(port, health_path)``.
#
# THESE PROBES ARE NOT FOLDED INTO ``/api/health``. A down :8000 is a fact about
# the orchestrator, while Kernel-R&D's own health_path is already a projection of
# the kernel envelope. Folding either back in would create a recursive or duplicate
# verdict. The supervisor itself continues to poll only transport ``/health``.
_DASHBOARDS_TTL_S = 15.0
_DASHBOARD_PROBE_TIMEOUT_S = 1.5
_dashboards_lock = threading.Lock()
_dashboards_cache: dict | None = None
_dashboards_cache_ts = 0.0


def _read_dashboard_registry() -> tuple:
    """``(artifact_present, entries, reader_error)`` for ``dashboard/registry.json``.

    Read through the ONE reader (:func:`_read_json_object`) so the absent-vs-corrupt
    distinction is the same one every other file-backed panel makes. ``entries`` is
    ``[]`` on any failure — and the failure always travels with it, because a
    directory that renders empty over an unreadable registry is exactly the
    "nothing is wrong" / "nobody is reporting" conflation this surface forbids.
    """
    present, data, err = _read_json_object(
        DASHBOARD_REGISTRY_JSON, "dashboard registry")
    if data is None:
        return present, [], err
    raw = data.get("dashboards")
    if not isinstance(raw, list):
        return True, [], ("dashboard registry malformed: 'dashboards' is not a "
                          f"list (got {type(raw).__name__})")
    return True, [dict(e) for e in raw if isinstance(e, dict)], None


def registry_dashboards() -> list:
    """The registry's entries, or ``[]`` when it cannot be read.

    Deliberately NOT named ``*_payload``: this is the shared reader behind both
    ``/api/dashboards`` and the ``/nav.js`` asset, not a panel of its own.
    """
    return _read_dashboard_registry()[1]


def _probe_health(port: int, health_path: str) -> dict:
    """One ``127.0.0.1`` health-path probe → status/latency/error.

    LOOPBACK ONLY and stdlib-only. Semantics belong to the registry entry's
    ``health_path``: most declare transport-only ``/health``; Kernel-R&D declares
    its panel-specific producer/data-health route. This reader deliberately uses
    the HTTP status so it remains compatible with both kinds.
    """
    url = f"http://127.0.0.1:{port}{health_path}"
    started = time.monotonic()

    def _ms() -> float:
        return round((time.monotonic() - started) * 1000.0, 1)

    try:
        with urllib.request.urlopen(url, timeout=_DASHBOARD_PROBE_TIMEOUT_S) as resp:
            resp.read(2048)
            code = getattr(resp, "status", None)
            if code is None:
                code = resp.getcode()
        return {"ok": 200 <= int(code) < 400, "status_code": int(code),
                "latency_ms": _ms(), "error": None}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status_code": int(exc.code), "latency_ms": _ms(),
                "error": f"HTTP {exc.code}"}
    except Exception as exc:  # URLError, socket.timeout, OSError, …
        return {"ok": False, "status_code": None, "latency_ms": _ms(),
                "error": f"{type(exc).__name__}: {exc}"}


def _probe_targets(entries: list) -> dict:
    """Probe every UNIQUE ``(port, health_path)`` once, in parallel."""
    targets = sorted({(int(e["port"]), str(e.get("health_path") or "/health"))
                      for e in entries
                      if isinstance(e.get("port"), int)
                      and not isinstance(e.get("port"), bool)})
    if not targets:
        return {}
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(8, len(targets)),
            thread_name_prefix="dash-probe") as pool:
        results = list(pool.map(lambda t: _probe_health(*t), targets))
    return dict(zip(targets, results))


def _build_dashboard_directory() -> dict:
    """The directory body (entries + probes). Cached; ``_freshness`` is not."""
    present, entries, err = _read_dashboard_registry()
    probes = _probe_targets(entries)
    rows = []
    for entry in entries:
        row = dict(entry)
        port = entry.get("port")
        key = ((int(port), str(entry.get("health_path") or "/health"))
               if isinstance(port, int) and not isinstance(port, bool) else None)
        # The LOOPBACK PROBE target, deliberately not a browser link: a page is
        # reached at the viewer's own hostname (``/nav.js`` builds that from
        # ``location``), and shipping a 127.0.0.1 URL under a name like ``url``
        # would hand every remote viewer a link to their own machine.
        row["probe_url"] = (f"http://127.0.0.1:{key[0]}{key[1]}"
                            if key is not None else None)
        row["probe"] = probes.get(key) or {
            "ok": False, "status_code": None, "latency_ms": None,
            "error": f"registry entry {entry.get('id')!r} declares no usable "
                     f"integer port (got {port!r}) — unprobeable"}
        rows.append(row)

    body = {
        "schema": "epyc.dashboard.directory.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registry_path": str(DASHBOARD_REGISTRY_JSON),
        "registry_present": bool(present),
        "count": len(rows),
        "dashboards": rows,
        "probe_note": ("probes are LOOPBACK readings of each entry's declared "
                       "health_path (transport-only unless the entry explicitly "
                       "names a panel-data probe); they are cached with this "
                       "payload for "
                       f"{_DASHBOARDS_TTL_S:.0f}s and never enter /api/health"),
        "error": None,
    }
    if err is not None:
        # Something IS there and the hub could not read it — a different, more
        # urgent fact than "no registry". Both are named; neither renders blank.
        body["error"] = err
        body[READER_ERROR_KEY] = err
    elif not present:
        body["error"] = (
            f"dashboard registry not found at {DASHBOARD_REGISTRY_JSON} — the file "
            "is tracked in this repo, so this is a broken working tree, not a cold "
            "start. NO dashboard directory can be rendered.")
    elif not rows:
        body["error"] = ("dashboard registry parsed and declares NO dashboards — "
                         "this hub serves pages that nothing can navigate to.")
    return body


def dashboards_payload() -> dict:
    """The dashboard directory: ``dashboard/registry.json`` + live health probes.

    TTL-cached with its probes (the ``_board_cache`` idiom): six chips refreshing
    every 30s across every open dashboard tab would otherwise be a probe storm
    against the orchestrator. The cache is a latency device, not a producer — the
    envelope below is rebuilt per request, and the panel is ``KIND_LIVE`` because
    the directory is assembled inside the request from a repo-tracked file.

    NEVER AN EMPTY DIRECTORY. An absent or corrupt registry yields ``error`` (and
    ``_reader_error`` when something unreadable is on disk), so the page can say
    which of the two happened instead of drawing a nav with nothing in it.
    """
    global _dashboards_cache, _dashboards_cache_ts
    with _dashboards_lock:
        now = time.time()
        if (_dashboards_cache is None
                or (now - _dashboards_cache_ts) > _DASHBOARDS_TTL_S):
            _dashboards_cache = _build_dashboard_directory()
            _dashboards_cache_ts = now
        payload = dict(_dashboards_cache)
    payload["_freshness"] = _panel_envelope("dashboards", panels.Observation(
        artifact_present=bool(payload.get("registry_present")),
        timestamp=None,
        source="live-scan",
        populated=bool(payload.get("dashboards")),
        detail=payload.get("error"),
        evidence=f"{DASHBOARD_REGISTRY_JSON} + live 127.0.0.1 health probes",
    ))
    return payload


def nav_asset() -> bytes:
    """``/nav.js`` — the registry, then the ONE shared nav renderer.

    NOT a panel and deliberately NOT named ``*_payload``: assets and HTML pages sit
    outside the panel-registry universe (see ``ASSET_ROUTES``). The registry is
    inlined ahead of the script so the nav renders on first paint with no fetch,
    and so a page that fails to reach ``/api/dashboards`` still has its links.
    """
    prelude = ("window.__EPYC_DASHBOARDS = "
               + json.dumps(registry_dashboards()) + ";\n")
    try:
        body = NAV_JS.read_text(encoding="utf-8")
    except OSError as exc:
        body = ("console.error("
                + json.dumps(f"[epyc-nav] {NAV_JS} is unreadable: {exc}")
                + ");\n")
    return (prelude + body).encode("utf-8")


def panel_envelopes() -> dict:
    """Every registered panel's freshness envelope, keyed by panel id.

    TOTAL over ``panels.PANELS`` by construction: the loop is over the REGISTRY,
    so a panel that gains a registry entry without a reader here raises
    ``KeyError`` at request time instead of silently dropping out of the fold —
    and ``tests/test_dashboard_panels.py`` catches it before that happens.
    """
    kernel_present, kernel_data = _read_kernel_contract()
    outcome_present, outcome_data = _read_outcome_contract()
    timeline_present, timeline_data = _read_timeline_contract()
    bench_present, bench_data = _read_benchmark_inventory()
    graph_present, graph_data = _read_graph_contract()
    readers = {
        # The REAL board envelope, not ``panels.live()``: the latter hardcodes
        # ``populated=True``, so the fold's board card claimed content regardless
        # of what the scan actually found. The payload is TTL-cached, so this is
        # a dict lookup in the common case.
        "board": lambda: board_payload()["_freshness"],
        "handoff_detail": lambda: panels.live(),
        "health": lambda: panels.live(),
        "transport_probe": lambda: panels.live(),
        "timeline": lambda: _timeline_observation(
            timeline_data, artifact_present=timeline_present),
        "handoff_graph": lambda: _graph_observation(
            graph_data, artifact_present=graph_present),
        "kernel": lambda: _kernel_observation(
            kernel_data, artifact_present=kernel_present),
        "outcome": lambda: _outcome_observation(
            outcome_data, artifact_present=outcome_present),
        "benchmark_artifacts": lambda: _benchmark_observation(
            bench_data, artifact_present=bench_present),
        "queue": lambda: queue_payload()["_freshness"],
        "bus": lambda: bus_payload()["_freshness"],
        # Same rule as board/queue/bus: the payload already built its envelope
        # (and holds the TTL cache the probes live in), so reuse it rather than
        # letting the fold compute a second answer for one panel.
        "dashboards": lambda: dashboards_payload()["_freshness"],
    }
    out: dict = {}
    for name in panels.PANELS:
        made = readers[name]()
        # queue/bus build their envelope inside their own payload (they need the
        # fold they already computed); everything else hands back an Observation.
        out[name] = made if isinstance(made, dict) else _panel_envelope(name, made)
    return out


def health_payload() -> dict:
    """THE FOLD. Every registered panel's envelope, folded into one verdict that
    NAMES the worst panel and says why.

    Three-valued (``ok`` / ``absent`` / ``degraded``) because "nobody is
    reporting" is neither of the other two, and the pre-AK6 two-valued fold had to
    call it ``ok``. The rules live in ``panels.fold``; the compatibility aliases
    below (``board``/``timeline``/``kernel``/``outcome`` at the top level) are the
    same envelope objects, kept so existing consumers and regression locks are not
    broken by the generalisation.
    """
    envs = panel_envelopes()
    verdict = panels.fold(envs)
    return {
        "status": verdict["status"],
        # WHICH panel produced ``status``. ``worst`` is the worst by severity
        # score and need not be that panel — live right now the fold is ``absent``
        # because of ``kernel`` while ``worst`` is ``bus``, and a badge that pairs
        # the colour of one with the sentence of the other names the wrong
        # offender.
        "status_set_by": verdict["status_set_by"],
        "worst": verdict["worst"],
        "attention": verdict["attention"],
        "absent": verdict["absent"],
        "panels": envs,
        # Back-compat aliases — same objects, old names.
        "board": envs["board"],
        "timeline": envs["timeline"],
        "kernel": envs["kernel"],
        "outcome": envs["outcome"],
        "now": time.time(),
    }


def transport_probe_payload() -> dict:
    """``/health`` — the SUPERVISOR's probe. Transport liveness ONLY.

    ``scripts/dashboard/hub_supervisor.sh`` restarts the hub when this body stops
    matching ``"status"…ok``. Producer health must therefore never reach it: a
    dead AutoKernel loop or a paused autopilot would put the hub into a restart
    loop, and restarting the dashboard cannot revive a producer in another repo.
    The fold is one link away and is named here so the separation is discoverable
    from the wire rather than only from this docstring.
    """
    return {"status": "ok", "probe": "transport",
            "detail": "the hub process is serving; this route says nothing about "
                      "whether any producer is reporting",
            "producer_health": "/api/health"}


# --------------------------------------------------------------------------- #
# HTTP layer
# --------------------------------------------------------------------------- #
# ROUTES ARE TABLES, NOT AN if/elif CHAIN. The chain was unenumerable: nothing
# could ask the hub which panels it serves, so the panel→producer registry could
# only ever be checked against a hand-written list — the same defect one level up.
# With tables, ``panels.registry_gaps(server)`` reads the routes the hub ACTUALLY
# dispatches on and fails when a route has no registered producer, or a registered
# producer has no route, or a route is bound to the wrong payload function.

#: What the graph panel looks like when no producer has reported. ``None``, not
#: empty lists: an empty graph and a missing graph are different facts, and the
#: page must be able to say which one it is looking at.
_GRAPH_ABSENT = {
    "nodes": None, "edges": None, "domains": None, "generated_at": None,
    "degraded": True,
    "observation_notice": (
        "THIS PANEL IS UNSOURCED: index_state.py has not run in this checkout, so an "
        "empty graph here means 'nobody is reporting', not 'the backlog is empty'."),
}


def _graph_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    """Date the graph by the producer's own ``generated_at``, never by mtime.

    A SPARSE graph is healthy and must not read as a fault: edges come only from
    the hand-authored ``Deps`` column, so zero edges means Deps is unfilled, not
    that the producer is broken. Node count is therefore the populated-ness
    signal, and ``generated_at`` doubles as the watermark — a regeneration that
    does not advance it means index_state.py ran but produced the same view.
    """
    if data.get(READER_ERROR_KEY):
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY])
    nodes = data.get("nodes")
    edges = data.get("edges") or []
    return panels.Observation(
        artifact_present=artifact_present,
        timestamp=_parse_semantic_timestamp(data.get("generated_at")),
        source="generated_at",
        populated=None if nodes is None else bool(nodes),
        detail=(None if not nodes else
                f"{len(nodes)} index rows, {len(edges)} dependency edges"),
        watermark=data.get("generated_at") if isinstance(data.get("generated_at"), str) else None,
    )


def _read_graph_contract() -> tuple:
    present, data, err = _read_json_object(GRAPH_PATH, "index graph artifact")
    if data is None:
        out = dict(_GRAPH_ABSENT)
        if err:
            out["reader_error"] = err
        return present, out
    return present, data


def graph_payload() -> dict:
    """Read the index graph artifact, tolerating absence/corruption."""
    present, data = _read_graph_contract()
    data["_freshness"] = _panel_envelope(
        "handoff_graph", _graph_observation(data, artifact_present=present))
    return data


HTML_ROUTES = {
    "/": STATIC_HTML,
    "/machine": MACHINE_HTML,
    "/autopilot": AUTOPILOT_HTML,
    "/kernel": KERNEL_HTML,
    "/bus": BUS_HTML,
    "/benchmarks": BENCHMARKS_HTML,
}

#: ``route -> (content_type, body_builder)`` for static ASSETS the hub generates.
#:
#: OUTSIDE THE PANEL REGISTRY UNIVERSE, on purpose, and it is the same exemption
#: ``HTML_ROUTES`` already has. ``panels.registry_gaps`` folds ``API_ROUTES`` /
#: ``API_ROUTES_WITH_STATUS`` / ``PROBE_ROUTES`` — the routes that serve a
#: PRODUCER'S EVIDENCE — and a panel→producer registry is a claim about evidence,
#: not about bytes. ``/nav.js`` has no producer to be silent: it is this hub's own
#: rendering of ``dashboard/registry.json``, whose reporting IS the ``dashboards``
#: panel at ``/api/dashboards``. Registering the asset too would give one fact two
#: registry entries, which is the second-source-of-truth defect the registry
#: exists to prevent. The builders are therefore named WITHOUT the ``_payload``
#: suffix so ``discover_payload_functions`` does not count them, and the exemption
#: is listed under "Known open items" in ``dashboard/README.md`` beside the
#: ``HTML_ROUTES`` one rather than being silent.
ASSET_ROUTES = {
    "/nav.js": ("application/javascript; charset=utf-8", nav_asset),
}

#: ``route -> () -> dict``, answered 200.
API_ROUTES = {
    "/api/handoff_board": board_payload,
    "/api/handoff_timeline": timeline_payload,
    "/api/handoff_graph": graph_payload,
    "/api/kernel": kernel_payload,
    "/api/bus": bus_payload,
    "/api/queue": queue_payload,
    "/api/outcome": outcome_payload,
    "/api/benchmark_artifacts": benchmark_artifacts_payload,
    "/api/dashboards": dashboards_payload,
    "/api/health": health_payload,
}

#: ``route -> (id) -> (status, dict)``. The payload function is bound DIRECTLY,
#: with no adapter, so the registry cross-check compares real function identity
#: rather than a wrapper's name.
API_ROUTES_WITH_STATUS = {
    "/api/handoff_detail": detail_payload,
}

#: Panel-specific DATA health. Separate from ``PROBE_ROUTES`` because these
#: handlers may return 503 when a producer is absent/degraded; the supervisor must
#: never poll them. Separate from ``API_ROUTES`` because handlers return an
#: explicit ``(status, payload)``. Each route is declared on its existing
#: ``PanelSource`` via ``health_route``/``health_func`` and is checked by
#: ``panels.registry_gaps`` without creating a duplicate panel in the global fold.
PANEL_HEALTH_ROUTES = {
    "/api/kernel/health": kernel_data_health,
}

#: The supervisor's transport probe. In its OWN table, not ``API_ROUTES``: it is
#: not a panel over a producer, and it must never carry a producer's verdict (see
#: the module docstring — the supervisor restarts the hub on a non-ok body). It is
#: still enumerated, and still registered in ``panels.PANELS``, so "the route that
#: is exempt from the fold" is a declared fact rather than an omission.
PROBE_ROUTES = {
    "/health": transport_probe_payload,
}
TRANSPORT_PROBE_ROUTE = "/health"


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

    def _send_asset(self, content_type: str, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        try:
            if route in HTML_ROUTES:
                self._send_html(HTML_ROUTES[route])
            elif route == TRANSPORT_PROBE_ROUTE:
                self._send_json(transport_probe_payload())
            elif route in ASSET_ROUTES:
                content_type, build = ASSET_ROUTES[route]
                self._send_asset(content_type, build())
            elif route in API_ROUTES:
                self._send_json(API_ROUTES[route]())
            elif route in API_ROUTES_WITH_STATUS:
                qs = parse_qs(parsed.query)
                status, payload = API_ROUTES_WITH_STATUS[route]((qs.get("id") or [""])[0])
                self._send_json(payload, status=status)
            elif route in PANEL_HEALTH_ROUTES:
                status, payload = PANEL_HEALTH_ROUTES[route]()
                self._send_json(payload, status=status)
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

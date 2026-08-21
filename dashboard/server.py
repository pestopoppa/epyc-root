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
import base64
import concurrent.futures
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
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
KERNEL_PROGRESSION_JSON = Path(os.environ.get(
    "KERNEL_PROGRESSION_JSON",
    "/mnt/raid0/llm/autokernel/surface/kernel_progression.json"))
KERNEL_PROGRESSION_SCHEMA = "epyc.autokernel.progression.v1"

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
AUTOKERNEL_ROOT_REPO = Path(os.environ.get(
    "AUTOKERNEL_ROOT_REPO", str(REPO)))
AUTOKERNEL_STATE_ROOT = Path(os.environ.get(
    "AUTOKERNEL_STATE_ROOT",
    "/mnt/raid0/llm/autokernel"))
AUTOKERNEL_PROBE_ROOT = Path(os.environ.get(
    "AUTOKERNEL_PROBE_ROOT",
    "/mnt/raid0/llm/autokernel/probes"))
AUTOKERNEL_CONTROL_ROOT = Path(os.environ.get(
    "AUTOKERNEL_CONTROL_ROOT",
    "/mnt/raid0/llm/autokernel/controls"))
AUTOKERNEL_DEPLOYMENTS_ROOT = Path(os.environ.get(
    "AUTOKERNEL_DEPLOYMENTS_ROOT",
    "/mnt/raid0/llm/autokernel/deployments"))
AUTOKERNEL_SUPERVISORS_ROOT = Path(os.environ.get(
    "AUTOKERNEL_SUPERVISORS_ROOT",
    "/mnt/raid0/llm/autokernel/supervisors"))
AUTOKERNEL_DISCOVERY_EVENT_SCHEMA = "epyc.autokernel.discovery_live_event.v1"
AUTOKERNEL_DISCOVERY_EVENT_SCHEMA_V2 = "epyc.autokernel.discovery_live_event.v2"
AUTOKERNEL_DISCOVERY_EVENT_PRODUCER_SHA = \
    "76301d6647586a25f2d56de1b93f1da9ac11a3fa"
AUTOKERNEL_MEASUREMENT_OUTPUT_PRODUCER_SHA = \
    "eb689b0d3239f7af538015a7ccb098fe8169f9e6"
AUTOKERNEL_SUPERVISOR_SCHEMA_PRODUCER_SHA = \
    "b62d63f8f9caecac597ebd9f1b3b7b098623dc71"
AUTOKERNEL_DISCOVERY_EVENT_SCHEMAS = frozenset({
    AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
    AUTOKERNEL_DISCOVERY_EVENT_SCHEMA_V2,
})
ARENA_ATTEMPT_DISPOSITIONS_JSON = Path(os.environ.get(
    "ARENA_ATTEMPT_DISPOSITIONS_JSON",
    str(Path(__file__).resolve().parent / "arena_attempt_dispositions.json")))
ARENA_ATTEMPT_DISPOSITIONS_SCHEMA = "epyc.dashboard.arena_attempt_dispositions.v1"
AUTOKERNEL_HIP_DECISION_CAMPAIGN = "hip-silu-decision-grade-20260812-r6"
AUTOKERNEL_HIP_DECISION_SCHEMA = "epyc.autokernel.hip_decision_grade.v1"
AUTOKERNEL_HIP_DECISION_PRODUCER = "autokernel.controller.hip_decision_grade/v1"
AUTOKERNEL_HIP_DECISION_AUTHORITY = \
    "task_local_rank_no_release_or_promotion_authority"
AUTOKERNEL_DIAGNOSTIC_PILOT_SCHEMA = \
    "epyc.autokernel.arena_diagnostic_pilot.v1"
# Mainline feature identities are presentation anchors, not deployment claims.
# They let the view distinguish "implemented and awaiting a real receipt" from
# "the producer does not exist" without importing the research package or
# trusting whichever shared checkout happens to be current.
AUTOKERNEL_READINESS_COMMITS = (
    ("structured_output_retry", "537163d5696ab646a0d8ef4b543d78da1199332c",
     "retry-hardened seven-arm controller"),
    ("sc33_reward_integrity_v2", "aa331993",
     "prospective SC33 reward-integrity belief producer"),
    ("c3_c5_capture_mapping", "9673132b",
     "governed C3/C5 tensor-capture window and k228/k175 mapping"),
    ("sc36_intermediate_beliefs", "b0d6f79f",
     "prospective feedback-only intermediate evaluator beliefs"),
    ("ak_del_2_catalogue", "35f10715",
     "bounded gfx90a prior-art catalogue expansion"),
    ("source_available_rocm_provider", "a54e36ba",
     "governed source-available ROCm provider execution"),
)
PRODUCTION_KERNEL_ATTESTATION = Path(os.environ.get(
    "PRODUCTION_KERNEL_ATTESTATION",
    str(REPO / "artifacts/operator/ratify_v9_final_freeze_20260811.json")))
PRODUCTION_KERNEL_REPO = Path(os.environ.get(
    "PRODUCTION_KERNEL_REPO",
    "/mnt/raid0/llm/llama.cpp"))
AUTOKERNEL_INTEGRATION_SINCE = os.environ.get(
    "AUTOKERNEL_INTEGRATION_SINCE", "2026-07-29T00:00:00Z")
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


def _read_kernel_progression() -> dict:
    """Read the additive discovery funnel without changing terminal truth."""
    present, data, error = _read_json_object(
        KERNEL_PROGRESSION_JSON, "kernel progression contract")
    if data is None:
        return {"schema": KERNEL_PROGRESSION_SCHEMA, "available": False,
                "artifact_present": present, "error": error or "not exported",
                "promotion_claim": False, "candidates": [], "unexplored": []}
    malformed = []
    if data.get("schema") != KERNEL_PROGRESSION_SCHEMA:
        malformed.append("unknown schema")
    if data.get("promotion_claim") is not False:
        malformed.append("promotion_claim must be false")
    if not isinstance(data.get("candidates"), list):
        malformed.append("candidates must be a list")
    if malformed:
        return {"schema": KERNEL_PROGRESSION_SCHEMA, "available": False,
                "artifact_present": True, "error": "; ".join(malformed),
                "promotion_claim": False, "candidates": [], "unexplored": []}
    result = dict(data)
    result["available"] = True
    result["artifact_present"] = True
    result["evidence"] = str(KERNEL_PROGRESSION_JSON)
    observed = _parse_semantic_timestamp(result.get("observed_through"))
    age = None if observed is None else max(0.0, time.time() - observed)
    result["freshness"] = {
        "source": "observed_through", "age_s": age,
        "staleness_class": ("unknown" if age is None else
                            "fresh" if age < 3 * 86400 else
                            "aging" if age < 14 * 86400 else "stale"),
    }
    return result


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


def _supplement_kernel_verdict(verdict: dict, progression: dict) -> dict:
    """Downgrade kernel-only absence to degraded when discovery is reporting.

    This never produces ``ok`` and never changes the strict envelope. It only
    prevents intentionally absent champion/release owners from describing a
    populated non-promotable discovery funnel as ``NOBODY IS REPORTING``.
    """
    absent_attention = [row for row in verdict.get("attention", [])
                        if row.get("verdict") == panels.STATUS_ABSENT
                        and row.get("gates_health") is True]
    if not (verdict.get("status") == panels.STATUS_ABSENT
            and absent_attention
            and all(row.get("panel") == "kernel" for row in absent_attention)
            and progression.get("available")
            and (progression.get("candidates") or progression.get("unexplored"))):
        return verdict
    result = dict(verdict)
    status = {
        "panel": "kernel", "verdict": panels.STATUS_DEGRADED,
        "why": ("discovery progression is reporting, while strict terminal "
                "sections remain explicitly unreported"),
        "gates_health": True,
    }
    result["status"] = panels.STATUS_DEGRADED
    result["status_set_by"] = status
    result["worst"] = status
    result["attention"] = [status if row.get("panel") == "kernel" else row
                           for row in verdict.get("attention", [])]
    return result


def kernel_data_health() -> tuple[int, dict]:
    """Kernel-R&D's panel-specific producer/data-health probe.

    This intentionally reads only the AutoKernel terminal and live-discovery
    contracts and folds their two envelopes. It never calls :func:`health_payload` or
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
    live_payload, live_observation = _discovery_live_read()
    live_env = _panel_envelope("kernel_live", live_observation)
    progression = _read_kernel_progression()
    verdict = _supplement_kernel_verdict(panels.fold(
        {"kernel": env, "kernel_live": live_env},
        registry={"kernel": panels.source("kernel"),
                  "kernel_live": panels.source("kernel_live")}), progression)
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
        "live": {"active": live_payload.get("active", False),
                 "deployment": live_payload.get("deployment"),
                 "status_message": live_payload.get("status_message"),
                 "freshness": live_env},
    }
    payload["progression"] = {
        "available": progression.get("available", False),
        "evidence": progression.get("evidence", str(KERNEL_PROGRESSION_JSON)),
        "freshness": progression.get("freshness"),
        "candidate_count": len(progression.get("candidates") or []),
        "promotion_claim": False,
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


def _mainline_integration_summary(repo: Path, label: str,
                                  since: str = AUTOKERNEL_INTEGRATION_SINCE) -> dict:
    """Count the authoritative first-parent history instead of path-simplified log rows.

    ``_autokernel_git_activity`` intentionally uses ``--all -- <path>``. Git history
    simplification commonly removes merge commits from that view, so it must never be
    reused as a merge/deployment counter. This projection names the exact ref and
    traversal used, making a displayed zero falsifiable.
    """
    refs = ("refs/remotes/origin/main", "refs/heads/main")
    selected = None
    try:
        for ref in refs:
            probe = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref],
                capture_output=True, text=True, timeout=5.0, check=False)
            if probe.returncode == 0:
                selected = ref
                break
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"label": label, "available": False, "repo": str(repo),
                "since": since, "error": str(exc)}
    if selected is None:
        return {"label": label, "available": False, "repo": str(repo),
                "since": since, "error": "neither origin/main nor local main exists"}

    def _log(*extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo), "log", "--first-parent",
             f"--since={since}", *extra, "--format=%H%x00%cI%x00%s", selected],
            capture_output=True, text=True, timeout=8.0, check=False)

    try:
        commits = _log()
        merges = _log("--merges")
        tip = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", selected], capture_output=True,
            text=True, timeout=5.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"label": label, "available": False, "repo": str(repo),
                "ref": selected, "since": since, "error": str(exc)}
    failed = next((proc for proc in (commits, merges, tip)
                   if proc.returncode != 0), None)
    if failed is not None:
        return {"label": label, "available": False, "repo": str(repo),
                "ref": selected, "since": since,
                "error": failed.stderr.strip() or f"git exited {failed.returncode}"}
    commit_rows = [row for row in commits.stdout.splitlines() if row]
    merge_rows = [row for row in merges.stdout.splitlines() if row]
    newest_merge = None
    if merge_rows:
        sha, committed_at, subject = merge_rows[0].split("\0", 2)
        newest_merge = {"sha": sha, "short_sha": sha[:10],
                        "committed_at": committed_at, "subject": subject}
    return {
        "label": label,
        "available": True,
        "repo": str(repo),
        "ref": selected,
        "tip": tip.stdout.strip(),
        "since": since,
        "first_parent_commits": len(commit_rows),
        "first_parent_merges": len(merge_rows),
        "newest_merge": newest_merge,
        "method": "git log --first-parent --since=<since> --merges <ref>",
    }


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
        # The durable root also contains enormous source worktrees and build
        # trees. Recursive rglob walked all of them on every /api/kernel request
        # (measured >5 s) even though campaign journals occupy three declared
        # layouts. Keep discovery explicit and bounded so the operator surface
        # remains responsive without hiding its scope.
        try:
            shards = list(root.glob("*/events.jsonl"))
            shards += list((root / "campaigns").glob("*/events.jsonl"))
            shards += list((root / "screens").glob("*/events.jsonl"))
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


def _canonical_receipt_hash(value: dict) -> str:
    payload = dict(value)
    payload.pop("receipt_sha256", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _verified_receipt(path: Path, schemas: set[str], label: str) -> tuple[dict | None, str | None]:
    """Read a regular JSON receipt and verify its producer-authored self-hash."""
    if path.is_symlink() or not path.is_file():
        return None, f"{label} is absent or not a regular file"
    _, value, error = _read_json_object(path, label)
    if error or not isinstance(value, dict):
        return None, error or f"{label} is not an object"
    if value.get("schema") not in schemas:
        return None, f"{label} has unsupported schema"
    expected = value.get("receipt_sha256")
    if not isinstance(expected, str) or expected != _canonical_receipt_hash(value):
        return None, f"{label} self-hash mismatch"
    return value, None


def _arena_attempt(manifest_path: Path) -> tuple[dict | None, str | None]:
    """Verify one Arena attempt using completed receipts, never file markers."""
    manifest, error = _verified_receipt(
        manifest_path, {"epyc.autokernel.arena_campaign_run_manifest.v1",
                        "epyc.autokernel.arena_campaign_run_manifest.v2"},
        "Arena campaign manifest")
    if error or manifest is None:
        return None, error
    run_root = manifest_path.parent
    constraints = manifest.get("constraints")
    if run_root.is_symlink() or manifest.get("available_source") is not True:
        return None, "Arena output root is unsafe or not available-source"
    if not isinstance(constraints, dict) or \
            constraints.get("partial_results_rankable") is not False or \
            constraints.get("aggregate_atomic_after_complete_matrix_only") is not True:
        return None, "Arena manifest lacks fail-closed partial/aggregate constraints"
    audit, audit_error = _verified_receipt(
        run_root / "audit.json",
        {"epyc.autokernel.arena_available_source_campaign_audit.v1",
         "epyc.autokernel.arena_available_source_campaign_audit.v2"},
        "Arena availability audit")
    if audit_error or audit is None or \
            audit.get("receipt_sha256") != manifest.get("audit_receipt_sha256"):
        return None, audit_error or "Arena manifest/audit identity mismatch"

    matrix = manifest.get("matrix") if isinstance(manifest.get("matrix"), dict) else {}
    tasks = matrix.get("task_ids") if isinstance(matrix.get("task_ids"), list) else []
    arms = matrix.get("arm_ids") if isinstance(matrix.get("arm_ids"), list) else []
    checkpoints = (matrix.get("checkpoint_hours")
                   if isinstance(matrix.get("checkpoint_hours"), list) else [])
    if not tasks or "starting_state_baseline" not in arms or not checkpoints:
        return None, "Arena manifest matrix is incomplete"
    planned_checkpoints = len(tasks) * (1 + (len(arms) - 1) * len(checkpoints))
    observations, seen = [], set()
    belief_rows = window_count = released_windows = sample_count = 0
    claimed_seconds = 0.0
    latest_evidence_at = ""
    for receipt_path in sorted(run_root.glob("execution/cells/*/checkpoint-receipt.json")):
        receipt, receipt_error = _verified_receipt(
            receipt_path,
            {"epyc.autokernel.arena_checkpoint.v1", "epyc.autokernel.arena_checkpoint.v2"},
            "Arena checkpoint")
        if receipt_error or receipt is None or \
                receipt.get("campaign_id") != manifest.get("campaign_id"):
            continue
        task_id, arm_id = receipt.get("task_id"), receipt.get("arm_id")
        checkpoint = receipt.get("checkpoint_hours")
        if task_id not in tasks or arm_id not in arms:
            continue
        if (arm_id == "starting_state_baseline" and checkpoint is not None) or \
                (arm_id != "starting_state_baseline" and checkpoint not in checkpoints):
            continue
        key = (task_id, arm_id, checkpoint)
        if key in seen:
            continue

        windows = receipt.get("measurement_windows")
        valid_windows = 0
        if receipt.get("schema") == "epyc.autokernel.arena_checkpoint.v2":
            if not isinstance(windows, list) or len(windows) != 2:
                continue
            local_samples = 0
            local_seconds = 0.0
            for window in windows:
                if not isinstance(window, dict) or \
                        window.get("schema") != "epyc.autokernel.arena_gpu_measurement_window.v1" or \
                        window.get("receipt_sha256") != _canonical_receipt_hash(window) or \
                        window.get("status") != "complete":
                    break
                opened, released = window.get("device_claim_open"), window.get("device_claim_released")
                sampling = window.get("device_sampling")
                fields = ("claim_id", "campaign_id", "device_id", "acquired_at")
                if not isinstance(opened, dict) or not isinstance(released, dict) or \
                        any(opened.get(field) != released.get(field) for field in fields) or \
                        not released.get("released_at") or not isinstance(sampling, dict) or \
                        not isinstance(sampling.get("sample_count"), int) or sampling["sample_count"] <= 0:
                    break
                valid_windows += 1
                local_samples += sampling["sample_count"]
                if isinstance(sampling.get("duration_s"), (int, float)):
                    local_seconds += float(sampling["duration_s"])
            if valid_windows != 2:
                continue
            window_count += 2
            released_windows += 2
            sample_count += local_samples
            claimed_seconds += local_seconds
        else:
            release = receipt.get("device_claim_released")
            if not isinstance(release, dict) or not release.get("released_at"):
                continue

        seen.add(key)
        evaluation = receipt.get("evaluation") if isinstance(receipt.get("evaluation"), dict) else {}
        belief = receipt.get("belief_receipt") if isinstance(receipt.get("belief_receipt"), dict) else {}
        rows = belief.get("belief_measurements") if isinstance(belief.get("belief_measurements"), list) else []
        belief_rows += len(rows)
        latest_evidence_at = max(latest_evidence_at, str(receipt.get("ended_at") or ""))
        observations.append({
            "task_id": task_id, "arm_id": arm_id, "checkpoint_hours": checkpoint,
            "average_speedup": evaluation.get("average_speedup"),
            "pass_compilation": evaluation.get("pass_compilation"),
            "pass_correctness": evaluation.get("pass_correctness"),
            "valid_baseline_cases": evaluation.get("valid_baseline_cases"),
            "valid_optimized_cases": evaluation.get("valid_optimized_cases"),
            "receipt_sha256": receipt.get("receipt_sha256"),
            "ended_at": receipt.get("ended_at"), "measurement_windows": valid_windows,
        })

    cell_receipts = 0
    for cell_path in sorted(run_root.glob("execution/cell-receipts/*.json")):
        cell, cell_error = _verified_receipt(
            cell_path, {"epyc.autokernel.arena_cell_runner.v3"}, "Arena cell receipt")
        if not cell_error and cell is not None and \
                cell.get("campaign_id") == manifest.get("campaign_id"):
            cell_receipts += 1

    aggregate_path = run_root / "execution-receipt.json"
    aggregate_present = False
    if aggregate_path.is_file() and not aggregate_path.is_symlink():
        _, aggregate, aggregate_error = _read_json_object(aggregate_path, "Arena aggregate")
        aggregate_present = bool(not aggregate_error and isinstance(aggregate, dict) and
                                 aggregate.get("receipt_sha256") == _canonical_receipt_hash(aggregate))

    # A worker request or recently-written file is not liveness.  A sandbox
    # activation is useful only while the exact captured PID still has the same
    # /proc start tick; PID existence alone is vulnerable to reuse.  Controller
    # activations span a checkpoint and are GPU-blind, so this read does not
    # touch inference or extend a device claim.
    live_cells = []
    for activation_path in sorted(run_root.glob(
            "execution/cells/*/controller-sandbox-activation.json")):
        _, activation, activation_error = _read_json_object(
            activation_path, "Arena controller activation")
        if activation_error or not isinstance(activation, dict) or \
                activation.get("schema") != "epyc.autokernel.sandbox_receipt.v2":
            continue
        pid, expected_ticks = activation.get("pid"), activation.get("process_start_ticks")
        if not isinstance(pid, int) or not isinstance(expected_ticks, int):
            continue
        proc_stat = _discovery_proc_stat(pid)
        if proc_stat is None:
            continue
        observed_ticks = proc_stat[2]
        if observed_ticks != expected_ticks:
            continue
        _, request, request_error = _read_json_object(
            activation_path.parent / "worker-request.json", "Arena worker request")
        if request_error or not isinstance(request, dict) or \
                request.get("attempt_id") != manifest.get("attempt_id"):
            continue
        task = request.get("task") if isinstance(request.get("task"), dict) else {}
        arm = request.get("arm") if isinstance(request.get("arm"), dict) else {}
        live_cells.append({
            "pid": pid, "process_start_ticks": expected_ticks,
            "cell": activation_path.parent.name,
            "task_id": task.get("task_id"), "arm_id": arm.get("arm_id"),
            "checkpoint_hours": request.get("checkpoint_hours"),
            "activated_at_unix_ns": activation.get("activated_at_unix_ns"),
            "evidence": str(activation_path),
        })
    return {
        "available": True, "campaign_id": manifest.get("campaign_id"),
        "attempt_id": manifest.get("receipt_sha256"), "run_directory": run_root.name,
        "output_root": str(run_root), "authority": manifest.get("authority"),
        "available_source": True, "tasks": len(tasks), "arms": len(arms),
        "checkpoint_hours": checkpoints, "completed_checkpoints": len(observations),
        "planned_checkpoints": planned_checkpoints, "completed_cells": cell_receipts,
        "planned_cells": len(tasks) * len(arms),
        "released_measurement_windows": released_windows,
        "measurement_windows": window_count, "measurement_samples": sample_count,
        "measurement_claimed_seconds": round(claimed_seconds, 3),
        "belief_measurement_count": belief_rows, "observations": observations,
        "terminal_aggregate_present": aggregate_present,
        "rankable": bool(aggregate_present and len(observations) == planned_checkpoints),
        "live_cells": live_cells, "active": bool(live_cells),
        "latest_completed_evidence_at": latest_evidence_at or None,
        "evidence": str(manifest_path), "evidence_mtime": _iso_mtime(manifest_path),
        "note": ("verified completed receipts only; no file marker is liveness and no "
                 "partial observation is rankable"),
    }, None


def _arena_attempt_dispositions(path: Path) -> tuple[dict[str, dict], str | None]:
    """Load exact-attempt integrity retractions maintained by the governance hub.

    The producer remains authoritative for receipts.  This overlay can only
    reduce their authority after a cross-artifact integrity audit; it cannot
    make an absent or invalid producer record valid.
    """
    _, value, error = _read_json_object(path, "Arena attempt dispositions")
    if error or not isinstance(value, dict):
        return {}, error or "Arena attempt dispositions are not an object"
    if value.get("schema") != ARENA_ATTEMPT_DISPOSITIONS_SCHEMA:
        return {}, "Arena attempt dispositions have unsupported schema"
    rows = value.get("attempts")
    if not isinstance(rows, list):
        return {}, "Arena attempt dispositions lack an attempts list"
    result: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            return {}, "Arena attempt disposition is not an object"
        attempt_id = row.get("attempt_id")
        if not isinstance(attempt_id, str) or not re.fullmatch(r"[0-9a-f]{64}", attempt_id):
            return {}, "Arena attempt disposition has invalid attempt_id"
        if attempt_id in result or row.get("disposition") != "invalid_diagnostic_history" or \
                row.get("execution_state") != "stopped" or \
                row.get("resume_permitted") is not False or \
                row.get("ranking_authority") is not False or \
                row.get("release_authority") is not False or \
                not isinstance(row.get("run_directory"), str) or \
                not isinstance(row.get("reason"), str) or not row["reason"].strip():
            return {}, "Arena attempt disposition is malformed"
        result[attempt_id] = row
    return result, None


def _arena_campaign_progress(root: Path,
                             dispositions_path: Path | None = None) -> dict:
    """Select newest Arena evidence and apply exact-attempt integrity retractions."""
    try:
        manifests = list((root / "campaigns").glob("*/campaign-manifest.json"))
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    dispositions, disposition_error = _arena_attempt_dispositions(
        dispositions_path or ARENA_ATTEMPT_DISPOSITIONS_JSON)
    attempts, rejected = [], 0
    for path in manifests:
        attempt, _ = _arena_attempt(path)
        if attempt is None:
            rejected += 1
        elif attempt.get("completed_checkpoints", 0):
            disposition = dispositions.get(attempt.get("attempt_id"))
            if disposition is not None:
                if disposition["run_directory"] != attempt.get("run_directory"):
                    rejected += 1
                    continue
                attempt["campaign_evidence_valid"] = False
                attempt["execution_state"] = "stopped"
                attempt["active"] = False
                attempt["rankable"] = False
                attempt["disposition"] = disposition["disposition"]
                attempt["retraction"] = {
                    "recorded_at": disposition.get("recorded_at"),
                    "reason": disposition["reason"],
                    "evidence": disposition.get("evidence"),
                    "resume_permitted": False,
                    "ranking_authority": False,
                    "release_authority": False,
                }
            else:
                attempt["campaign_evidence_valid"] = \
                    None if disposition_error else True
                attempt["execution_state"] = (
                    "unknown_disposition_overlay_unavailable" if disposition_error
                    else ("terminal_complete" if attempt["terminal_aggregate_present"]
                          else ("live" if attempt.get("active")
                                else "stale_or_terminal_unreported")))
                if not attempt.get("active") and not attempt["terminal_aggregate_present"]:
                    attempt["active"] = None
                if disposition_error:
                    attempt["rankable"] = False
            attempts.append(attempt)
        else:
            rejected += 1

    preflight_refusals = []
    try:
        audits = list((root / "campaigns").glob("*/audit.json"))
    except OSError:
        audits = []
    for audit_path in audits:
        if (audit_path.parent / "campaign-manifest.json").exists():
            continue
        audit, audit_error = _verified_receipt(
            audit_path, {"epyc.autokernel.arena_available_source_campaign_audit.v2"},
            "Arena preflight audit")
        constraints = audit.get("constraints") if isinstance(audit, dict) else {}
        if audit_error or not isinstance(audit, dict) or audit.get("status") != "refused" or \
                not isinstance(constraints, dict) or \
                constraints.get("controller_or_gpu_command_executed") is not False:
            continue
        preflight_refusals.append({
            "run_directory": audit_path.parent.name,
            "execution_state": "preflight_refused",
            "active": False, "rankable": False,
            "refusal_reasons": audit.get("refusal_reasons") or [],
            "attempt_id": audit.get("receipt_sha256"),
            "evidence": str(audit_path),
        })
    if not attempts:
        return {"available": False, "rejected_attempts": rejected,
                "error": f"no verified Arena checkpoint evidence below {root / 'campaigns'}"}
    attempts.sort(key=lambda value: (value.get("active") is True,
                                     value.get("latest_completed_evidence_at") or "",
                                     value.get("attempt_id") or ""), reverse=True)
    selected = dict(attempts[0])
    selected["attempts"] = [{
        "attempt_id": attempt["attempt_id"], "run_directory": attempt["run_directory"],
        "output_root": attempt["output_root"],
        "completed_checkpoints": attempt["completed_checkpoints"],
        "completed_cells": attempt["completed_cells"],
        "latest_completed_evidence_at": attempt["latest_completed_evidence_at"],
        "campaign_evidence_valid": attempt["campaign_evidence_valid"],
        "active": attempt.get("active"),
        "execution_state": attempt["execution_state"],
        "disposition": attempt.get("disposition"),
    } for attempt in attempts]
    selected["preflight_refusals"] = sorted(
        preflight_refusals, key=lambda row: row["run_directory"], reverse=True)
    selected["rejected_attempts"] = rejected
    selected["disposition_overlay_error"] = disposition_error
    return selected


def _autokernel_implementation_readiness(repo: Path) -> dict:
    """Project reviewed AutoKernel features from the authoritative main ref."""
    refs = ("refs/remotes/origin/main", "refs/heads/main")
    selected = None
    try:
        for ref in refs:
            probe = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref],
                capture_output=True, text=True, timeout=5.0, check=False)
            if probe.returncode == 0:
                selected = ref
                break
        if selected is None:
            raise RuntimeError("neither origin/main nor local main exists")
        tip = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", selected], capture_output=True,
            text=True, timeout=5.0, check=False)
        if tip.returncode != 0:
            raise RuntimeError(tip.stderr.strip() or "cannot resolve research main")
        capabilities = []
        for capability_id, commit, label in AUTOKERNEL_READINESS_COMMITS:
            ancestor = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, selected],
                capture_output=True, text=True, timeout=5.0, check=False)
            capabilities.append({
                "id": capability_id, "label": label, "evidence_commit": commit,
                "integrated": ancestor.returncode == 0,
            })
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        return {"available": False, "error": str(exc), "capabilities": []}

    by_id = {row["id"]: row for row in capabilities}
    pending = [
        {
            "id": "C3-C5", "title": "Real EPYC tensor captures and mappings",
            "implementation_ready": by_id["c3_c5_capture_mapping"]["integrated"],
            "next_evidence": ("Provide exact real-model hook manifests, then admit one k228 "
                              "trace and the ordered multi-trace k175 component graph."),
        },
    ]
    return {
        "available": True, "repo": str(repo), "ref": selected,
        "tip": tip.stdout.strip(), "capabilities": capabilities,
        "all_capabilities_integrated": all(row["integrated"] for row in capabilities),
        "pending_empirical": pending,
        "note": ("mainline code readiness is not empirical completion; pending rows remain "
                 "open until their named producer evidence or review gate exists"),
    }


def _scaffold_panel_summary(root: Path) -> dict:
    """Project the newest terminal AK-LE-3 panel and hash-bound evaluations."""
    try:
        paths = list((root / "campaigns").glob("*/panel/panel.json"))
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    paths.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    for path in paths:
        _, panel, error = _read_json_object(path, "AK-LE-3 panel")
        if error or panel is None or panel.get("schema") != \
                "epyc.autokernel.ak_le_3_scaffold_panel.v1":
            continue
        panel_cells = panel.get("cells") if isinstance(panel.get("cells"), list) else []
        evaluation_paths = list((path.parent / "cells").glob("*/arena-evaluation.json"))
        evaluations = {}
        for evaluation_path in evaluation_paths:
            _, value, _ = _read_json_object(evaluation_path, "AK-LE-3 evaluation")
            if isinstance(value, dict) and value.get("schema") == \
                    "epyc.autokernel.ak_le_3_arena_evaluation.v1":
                evaluations[value.get("cell_id")] = (evaluation_path, value)
        cells = []
        released = 0
        for cell in panel_cells:
            if not isinstance(cell, dict):
                continue
            release = cell.get("device_claim_released")
            if isinstance(release, dict) and release.get("released_at"):
                released += 1
            evaluation_path, evaluation = evaluations.get(cell.get("cell_id"), (None, {}))
            digest, digest_error = _sha256_file(evaluation_path) if evaluation_path else (None, None)
            expected = cell.get("evaluation_sha256")
            cells.append({
                "cell_id": cell.get("cell_id"),
                "model_id": cell.get("model_id"),
                "effort": cell.get("effort"),
                "scaffold": cell.get("scaffold"),
                "planned_wall_seconds": cell.get("planned_wall_seconds"),
                "observed_actor_wall_seconds": cell.get("observed_actor_wall_seconds"),
                "average_speedup": evaluation.get("average_speedup"),
                "pass_compilation": evaluation.get("pass_compilation"),
                "pass_correctness": evaluation.get("pass_correctness"),
                "valid_baseline_cases": evaluation.get("valid_baseline_cases"),
                "valid_optimized_cases": evaluation.get("valid_optimized_cases"),
                "evaluation_hash_matches": bool(expected and digest == expected),
                "evaluation_error": digest_error,
            })
        constraints = panel.get("constraints") if isinstance(panel.get("constraints"), dict) else {}
        return {
            "available": True,
            "campaign_id": panel.get("experiment_id"),
            "status": panel.get("status"),
            "authority": panel.get("authority"),
            "capture_mode": panel.get("capture_mode"),
            "completed_cells": len(cells),
            "total_cells": 4,
            "released_claims": released,
            "cells": cells,
            "belief_measurement_count": len(panel.get("belief_measurements", []))
            if isinstance(panel.get("belief_measurements"), list) else 0,
            "prospective_adapter_present": (REPO / "scripts/vidya/adapters/autokernel_scaffold_panel.py").is_file(),
            "ranking_authority": constraints.get("ranking_authority", False),
            "promotion_authority": constraints.get("campaign_authority", False),
            "evidence": str(path),
            "evidence_mtime": _iso_mtime(path),
            "note": ("measured diagnostic scaffold observation only; r1 predates the "
                     "prospective belief hook and is not retrofitted"),
        }
    return {"available": False,
            "error": f"no AK-LE-3 panel found below {root / 'campaigns'}"}


def _rocm_diagnostics_summary(root: Path) -> dict:
    """Project current post-hook ROCm diagnostics and profiler receipt inventory."""
    campaign_root = root / "campaigns"
    rvp_path, rvp, rvp_error = _latest_autokernel_receipt(
        campaign_root, "receipt.json", "epyc.rvp_t0_1_saturation_probe.v1")
    bh_path, bh, bh_error = _latest_autokernel_receipt(
        campaign_root, "receipt.json", "epyc.ak_bh_1_gemm_baseline_compare.v1")
    rvp_rows = rvp.get("belief_measurements") if isinstance(rvp, dict) else []
    bh_rows = bh.get("belief_measurements") if isinstance(bh, dict) else []
    comparisons = bh.get("comparisons") if isinstance(bh, dict) else []
    ratios = [row.get("hipblaslt_over_rocblas") for row in comparisons
              if isinstance(row, dict) and isinstance(
                  row.get("hipblaslt_over_rocblas"), (int, float))]
    profile_schemas = {
        "epyc.autokernel.rocprofv1_attribution.v1": "rocprof v1 whole-model attribution",
        "epyc.autokernel.c4_profile_capture.v1": "C4 rocprof capture",
        "epyc.autokernel.c4_profile_report.v1": "C4 paired profile report",
        "epyc.autokernel.g15_profile.v1": "G15 profiler capture",
        "epyc.autokernel.omniperf_fallback.v1": "Omniperf fallback",
    }
    profiles = []
    for schema, label in profile_schemas.items():
        found = []
        try:
            for candidate in (root / "probes").glob("*/*.json"):
                _, data, _ = _read_json_object(candidate, "ROCm profile receipt")
                if isinstance(data, dict) and data.get("schema") == schema:
                    found.append((candidate, data))
        except OSError:
            found = []
        found.sort(key=lambda pair: _iso_mtime(pair[0]) or "", reverse=True)
        if found:
            candidate, data = found[0]
            rows = data.get("belief_measurements")
            profiles.append({"schema": schema, "label": label,
                             "status": data.get("status"),
                             "belief_measurement_count": len(rows)
                             if isinstance(rows, list) else 0,
                             "evidence": str(candidate)})
    return {
        "available": rvp is not None or bh is not None or bool(profiles),
        "rvp": {
            "available": rvp is not None, "campaign_id": rvp.get("campaign_id") if rvp else None,
            "status": rvp.get("status") if rvp else None,
            "throughput_tflops": (rvp.get("workload") or {}).get("throughput_tflops") if rvp else None,
            "nominal_sclk_fraction": rvp.get("nominal_sclk_sample_fraction") if rvp else None,
            "max_power_w": rvp.get("max_power_w") if rvp else None,
            "power_cap_w": rvp.get("power_cap_w") if rvp else None,
            "belief_measurement_count": len(rvp_rows) if isinstance(rvp_rows, list) else 0,
            "evidence": str(rvp_path) if rvp_path else None, "error": rvp_error,
        },
        "baseline_honesty": {
            "available": bh is not None, "campaign_id": bh.get("campaign_id") if bh else None,
            "status": bh.get("status") if bh else None, "shape_count": len(comparisons),
            "hipblaslt_wins": sum(1 for value in ratios if value > 1.0),
            "ratio_min": min(ratios) if ratios else None,
            "ratio_max": max(ratios) if ratios else None,
            "belief_measurement_count": len(bh_rows) if isinstance(bh_rows, list) else 0,
            "evidence": str(bh_path) if bh_path else None, "error": bh_error,
        },
        "read_adapter_present": (REPO / "scripts/vidya/adapters/autokernel_rocm_diagnostic.py").is_file(),
        "profile_adapter_present": (REPO / "scripts/vidya/adapters/autokernel_aux_receipt.py").is_file(),
        "profiles": profiles,
        "note": ("diagnostic/profile receipts do not rank an AutoKernel candidate or grant "
                 "campaign or promotion authority"),
    }


def _hip_decision_grade_summary(root: Path) -> dict:
    """Project the exact terminal raw-HIP r6 receipt without widening authority.

    This is a curated operator display, not a second evaluator.  It admits only
    the producer's self-hashed terminal receipt at the named campaign path and
    checks every field the card repeats.  A partial/tampered receipt disappears
    behind an explicit error instead of leaving a plausible-looking speed card.
    """
    path = root / "campaigns" / AUTOKERNEL_HIP_DECISION_CAMPAIGN / "receipt.json"
    receipt, error = _verified_receipt(
        path, {AUTOKERNEL_HIP_DECISION_SCHEMA}, "raw-HIP decision-grade receipt")
    if error or receipt is None:
        return {"available": False, "evidence": str(path), "error": error}
    producer = receipt.get("producer")
    task = receipt.get("task")
    correctness = receipt.get("correctness")
    timing = receipt.get("timing")
    e_process = timing.get("e_process") if isinstance(timing, dict) else None
    admission = (timing.get("ranked_duration_admission")
                 if isinstance(timing, dict) else None)
    decision = receipt.get("decision")
    constraints = receipt.get("constraints")
    cases = correctness.get("cases") if isinstance(correctness, dict) else None
    checks = admission.get("checks") if isinstance(admission, dict) else None
    invalid = []
    if receipt.get("campaign_id") != AUTOKERNEL_HIP_DECISION_CAMPAIGN:
        invalid.append("receipt campaign identity does not match the curated r6 path")
    if receipt.get("status") != "complete":
        invalid.append("receipt is not terminal complete")
    if receipt.get("authority") != AUTOKERNEL_HIP_DECISION_AUTHORITY:
        invalid.append("authority is not the task-local no-release boundary")
    if not isinstance(producer, dict) or \
            producer.get("producer_id") != AUTOKERNEL_HIP_DECISION_PRODUCER:
        invalid.append("producer identity is not the decision-grade HIP producer")
    elif not isinstance(producer.get("sha256"), str) or \
            len(producer["sha256"]) != 64 or \
            any(char not in "0123456789abcdef" for char in producer["sha256"]):
        invalid.append("producer source digest is not a lowercase SHA-256")
    if not isinstance(task, dict) or \
            task.get("task_id") != "torch2hip/gpumode/16636_SiLU" or \
            task.get("target") != {"gpu_model": "MI210", "gfx_arch": "gfx90a"}:
        invalid.append("task is not the sealed MI210/gfx90a SiLU surface")
    if not isinstance(cases, list) or len(cases) != 24 or \
            not isinstance(correctness, dict) or \
            correctness.get("all_passed") is not True or \
            correctness.get("passed") != 24 or correctness.get("total") != 24 or \
            any(not isinstance(case, dict) or case.get("passed") is not True
                for case in cases):
        invalid.append("correctness is not a complete 24/24 sealed pass")
    elif any(isinstance(case.get("max_abs_error"), bool) or
             not isinstance(case.get("max_abs_error"), (int, float))
             for case in cases):
        invalid.append("correctness cases lack numeric max-absolute-error evidence")
    median_speedup = timing.get("median_speedup") if isinstance(timing, dict) else None
    if isinstance(median_speedup, bool) or not isinstance(median_speedup, (int, float)):
        invalid.append("median speedup is absent or non-numeric")
    if not isinstance(e_process, dict) or e_process.get("first_crossing_block") != 9:
        invalid.append("e-process does not carry the r6 block-9 crossing")
    if not isinstance(timing, dict) or \
            (timing.get("provider") or {}).get("provider_id") != "torch_rocm_compile":
        invalid.append("timing does not name the exact Torch-ROCm-compile provider")
    if not isinstance(checks, list) or len(checks) != 40 or \
            not isinstance(admission, dict) or admission.get("all_arms_passed") is not True or \
            any(not isinstance(check, dict) or check.get("outcome") != "PASS"
                for check in checks):
        invalid.append("per-arm duration admission is not 40/40 PASS")
    elif admission.get("minimum_ns") != 250_090_903 or \
            not isinstance(admission.get("minimum_observed_ns"), (int, float)) or \
            admission["minimum_observed_ns"] < admission["minimum_ns"]:
        invalid.append("duration admission does not clear the exact gfx90a floor")
    if not isinstance(decision, dict) or \
            decision.get("rankable_against_exact_task_local_provider") is not True or \
            decision.get("release_or_promotion_authority") is not False or \
            decision.get("experimental_llama_integration_required_before_any_release") is not True:
        invalid.append("decision does not retain task-local/no-release scope")
    if not isinstance(constraints, dict) or \
            constraints.get("promotion_authority") is not False or \
            constraints.get("production_tree_touched") is not False:
        invalid.append("receipt constraints do not exclude promotion/production mutation")
    file_sha256, file_error = _sha256_file(path)
    if file_error or not file_sha256:
        invalid.append(file_error or "receipt file digest unavailable")
    if invalid:
        return {"available": False, "evidence": str(path),
                "error": "; ".join(invalid)}
    max_abs_error = max(
        float(case["max_abs_error"]) for case in cases
        if isinstance(case.get("max_abs_error"), (int, float)))
    return {
        "available": True,
        "schema": receipt.get("schema"),
        "campaign_id": receipt.get("campaign_id"),
        "status": receipt.get("status"),
        "ended_at": receipt.get("ended_at"),
        "producer_id": producer.get("producer_id"),
        "producer_sha256": producer.get("sha256"),
        "task_id": task.get("task_id"),
        "target": task.get("target"),
        "correctness_passed": correctness.get("passed"),
        "correctness_total": correctness.get("total"),
        "max_abs_error": max_abs_error,
        "median_speedup": median_speedup,
        "exact_provider": (timing.get("provider") or {}).get("provider_id"),
        "e_process_first_crossing_block": e_process.get("first_crossing_block"),
        "duration_admissions_passed": 40,
        "duration_admissions_total": 40,
        "minimum_duration_ns": admission.get("minimum_ns"),
        "minimum_observed_duration_ns": admission.get("minimum_observed_ns"),
        "receipt_self_sha256": receipt.get("receipt_sha256"),
        "receipt_file_sha256": file_sha256,
        "authority": receipt.get("authority"),
        "rankable_against_exact_task_local_provider": True,
        "experimental_llama_integration_required": True,
        "release_or_promotion_authority": False,
        "champion_claim": False,
        "evidence": str(path),
        "evidence_mtime": _iso_mtime(path),
        "note": ("decision-grade evidence for this exact task/provider only; not a "
                 "champion and not release or promotion evidence"),
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


def _diagnostic_pilot_summary(path: Path | None, data: dict | None,
                              error: str | None) -> dict:
    """Project a governed Arena pilot without manufacturing campaign authority."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    expected_hash = data.get("receipt_sha256")
    observed_hash = _canonical_receipt_hash(data)
    if not isinstance(expected_hash, str) or expected_hash != observed_hash:
        return {
            "available": False,
            "evidence": str(path) if path else None,
            "error": "diagnostic pilot receipt self-hash mismatch",
        }
    constraints = (data.get("constraints")
                   if isinstance(data.get("constraints"), dict) else {})
    checkpoint = (data.get("checkpoint")
                  if isinstance(data.get("checkpoint"), dict) else {})
    evaluation = (checkpoint.get("evaluation")
                  if isinstance(checkpoint.get("evaluation"), dict) else {})
    broker = (checkpoint.get("broker_evaluation_chain")
              if isinstance(checkpoint.get("broker_evaluation_chain"), dict) else {})
    sandbox = (checkpoint.get("controller_sandbox_execution")
               if isinstance(checkpoint.get("controller_sandbox_execution"), dict) else {})
    activation = (sandbox.get("activation_receipt")
                  if isinstance(sandbox.get("activation_receipt"), dict) else {})
    teardown_record = (sandbox.get("teardown_receipt")
                       if isinstance(sandbox.get("teardown_receipt"), dict) else {})
    teardown = (teardown_record.get("teardown")
                if isinstance(teardown_record.get("teardown"), dict) else {})
    windows = (checkpoint.get("measurement_windows")
               if isinstance(checkpoint.get("measurement_windows"), list) else [])
    window_samples = []
    released_windows = 0
    for window in windows:
        if not isinstance(window, dict):
            continue
        sampling = (window.get("device_sampling")
                    if isinstance(window.get("device_sampling"), dict) else {})
        released = (window.get("device_claim_released")
                    if isinstance(window.get("device_claim_released"), dict) else {})
        evaluator = (window.get("evaluator_execution_receipt")
                     if isinstance(window.get("evaluator_execution_receipt"), dict) else {})
        evaluator_activation = (evaluator.get("activation_receipt")
                                if isinstance(evaluator.get("activation_receipt"), dict) else {})
        evaluator_teardown = (evaluator.get("teardown_receipt")
                              if isinstance(evaluator.get("teardown_receipt"), dict) else {})
        window_samples.append({
            "phase": window.get("phase"),
            "sample_count": sampling.get("sample_count"),
            "evaluator_network_profile": evaluator_activation.get("network_profile"),
            "evaluator_devices": evaluator_activation.get("writable_device_paths", []),
            "evaluator_cgroup_verified_empty": evaluator_teardown.get("verified_empty"),
            "evaluator_cgroup_removed": evaluator_teardown.get("removed"),
        })
        if released.get("released_at"):
            released_windows += 1
    artifacts = (checkpoint.get("artifacts")
                 if isinstance(checkpoint.get("artifacts"), dict) else {})
    # Intermediate windows are hash-bound cell artifacts rather than duplicated
    # into the terminal receipt. Admit only exact, regular, self-hash-valid files
    # whose bytes match the terminal artifact map.
    if path is not None:
        cells_root = path.parent / "cells"
        for rel, expected_artifact_hash in artifacts.items():
            rel_path = Path(rel)
            if (not rel.startswith("controller-evaluation-windows/")
                    or not rel.endswith("-measurement.json")
                    or rel_path.is_absolute() or ".." in rel_path.parts
                    or not isinstance(expected_artifact_hash, str)):
                continue
            try:
                cell_roots = [row for row in cells_root.iterdir()
                              if row.is_dir() and not row.is_symlink()]
            except OSError:
                cell_roots = []
            for cell_root in cell_roots:
                candidate = cell_root / rel_path
                try:
                    raw = candidate.read_bytes()
                except OSError:
                    continue
                if candidate.is_symlink() or hashlib.sha256(raw).hexdigest() != \
                        expected_artifact_hash:
                    continue
                try:
                    value = json.loads(raw)
                except (UnicodeError, json.JSONDecodeError):
                    continue
                if (not isinstance(value, dict)
                        or value.get("schema") !=
                        "epyc.autokernel.arena_gpu_measurement_window.v1"
                        or value.get("receipt_sha256") !=
                        _canonical_receipt_hash(value)):
                    continue
                sampling = (value.get("device_sampling")
                            if isinstance(value.get("device_sampling"), dict) else {})
                released = (value.get("device_claim_released")
                            if isinstance(value.get("device_claim_released"), dict) else {})
                evaluator = (value.get("evaluator_execution_receipt")
                             if isinstance(value.get("evaluator_execution_receipt"), dict) else {})
                evaluator_activation = (evaluator.get("activation_receipt")
                                        if isinstance(evaluator.get("activation_receipt"), dict) else {})
                evaluator_teardown = (evaluator.get("teardown_receipt")
                                      if isinstance(evaluator.get("teardown_receipt"), dict) else {})
                window_samples.append({
                    "phase": value.get("phase"),
                    "sample_count": sampling.get("sample_count"),
                    "evaluator_network_profile": evaluator_activation.get("network_profile"),
                    "evaluator_devices": evaluator_activation.get("writable_device_paths", []),
                    "evaluator_cgroup_verified_empty": evaluator_teardown.get("verified_empty"),
                    "evaluator_cgroup_removed": evaluator_teardown.get("removed"),
                })
                if released.get("released_at"):
                    released_windows += 1
                break
    phase_order = {"vendor_baseline": 0,
                   "controller_intermediate_evaluation": 1,
                   "centralized_final_evaluation": 2}
    window_samples.sort(key=lambda row: phase_order.get(row.get("phase"), 99))
    evaluator_sandboxes = [
        {key: row.get(key) for key in (
            "phase", "evaluator_network_profile", "evaluator_devices",
            "evaluator_cgroup_verified_empty", "evaluator_cgroup_removed")}
        for row in window_samples if row.get("evaluator_network_profile")
    ]
    model_call_count = sum(
        1 for name in artifacts
        if name.startswith("workspace/.autokernel-upstream-controller/")
        and name.endswith("-model-output.txt")
    )
    belief_receipt = (checkpoint.get("belief_receipt")
                      if isinstance(checkpoint.get("belief_receipt"), dict) else {})
    belief_source = (belief_receipt.get("source")
                     if isinstance(belief_receipt.get("source"), dict) else {})
    model_ids = (belief_source.get("model_ids")
                 if isinstance(belief_source.get("model_ids"), list) else [])
    authority_verified = (
        data.get("authority") ==
        "compatibility_only_no_ranking_or_promotion_authority"
        and constraints.get("one_task") is True
        and constraints.get("one_controller_arm") is True
        and constraints.get("matched_campaign_result_implied") is False
        and constraints.get("cross_controller_ranking_authority") is False
        and constraints.get("belief_update_authority") is False
        and constraints.get("promotion_authority") is False
    )
    return {
        "available": True,
        "status": data.get("status"),
        "campaign_id": data.get("campaign_id"),
        "attempt_id": data.get("attempt_id"),
        "task_id": data.get("task_id"),
        "arm_id": data.get("arm_id"),
        "model_id": model_ids[0] if model_ids else None,
        "model_call_count": model_call_count,
        "broker_evaluation_count": broker.get("evaluation_count"),
        "pass_compilation": evaluation.get("pass_compilation"),
        "pass_correctness": evaluation.get("pass_correctness"),
        "valid_baseline_cases": evaluation.get("valid_baseline_cases"),
        "valid_optimized_cases": evaluation.get("valid_optimized_cases"),
        "average_speedup": evaluation.get("average_speedup"),
        "measurement_windows": window_samples,
        "released_measurement_windows": released_windows,
        "evaluator_sandboxes": evaluator_sandboxes,
        "controller_writable_devices": activation.get("writable_device_paths", []),
        "controller_cgroup_verified_empty": teardown.get("verified_empty"),
        "controller_cgroup_removed": teardown.get("removed"),
        "authority": data.get("authority"),
        "authority_verified": authority_verified,
        "matched_campaign_result_implied": False,
        "rankable": False,
        "belief_update_authority": False,
        "promotion_authority": False,
        "receipt_sha256": expected_hash,
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
        "note": ("terminal one-task/one-arm compatibility pilot only; it does not "
                 "rank controllers, update belief, imply a matched campaign, or "
                 "authorize promotion/release"),
    }


#: The receipt schemas this panel knows how to project. Kept as a named constant so
#: the page can DECLARE its own coverage rather than implying completeness by silence.
_PROJECTED_RECEIPT_SCHEMAS = {
    "epyc.autokernel.arena_controller_campaign_audit.v1",
    "epyc.autokernel.arena_available_source_campaign_audit.v1",
    "epyc.autokernel.arena_available_source_campaign_audit.v2",
    "epyc.autokernel.arena_diagnostic_smoke.v1",
    AUTOKERNEL_DIAGNOSTIC_PILOT_SCHEMA,
    "epyc.autokernel.live_control_preflight.v1",
    "epyc.autokernel.async_prefetch_replay.v1",
    "epyc.autokernel.arena_campaign_run_manifest.v1",
    "epyc.autokernel.arena_checkpoint.v1",
    "epyc.autokernel.ak_le_3_scaffold_panel.v1",
    "epyc.autokernel.ak_le_3_arena_evaluation.v1",
    "epyc.rvp_t0_1_saturation_probe.v1",
    "epyc.ak_bh_1_gemm_baseline_compare.v1",
    "epyc.autokernel.rocprofv1_attribution.v1",
    "epyc.autokernel.c4_profile_capture.v1",
    "epyc.autokernel.c4_profile_report.v1",
    "epyc.autokernel.g15_profile.v1",
    "epyc.autokernel.omniperf_fallback.v1",
    AUTOKERNEL_HIP_DECISION_SCHEMA,
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
    # V2 is the exact-source seven-arm panel. Keep the v1 lookup as a historical
    # fallback so a missing new receipt cannot make the last governed audit
    # disappear, while always preferring v2 when one has been persisted.
    available_path, available, available_err = _latest_autokernel_receipt(
        probe_root, "receipt.json",
        "epyc.autokernel.arena_available_source_campaign_audit.v2")
    if available is None:
        available_path, available, available_err = _latest_autokernel_receipt(
            probe_root, "available-source-six-arm.json",
            "epyc.autokernel.arena_available_source_campaign_audit.v1")
    smoke_path, smoke, smoke_err = _latest_autokernel_receipt(
        probe_root, "smoke-receipt.json",
        "epyc.autokernel.arena_diagnostic_smoke.v1")
    pilot_path, pilot, pilot_err = _latest_autokernel_receipt(
        probe_root, "diagnostic-pilot-receipt.json",
        AUTOKERNEL_DIAGNOSTIC_PILOT_SCHEMA)
    preflight_path, preflight, preflight_err = _latest_autokernel_receipt(
        probe_root, "preflight.json",
        "epyc.autokernel.live_control_preflight.v1")
    replay_path, replay, replay_err = _latest_autokernel_receipt(
        probe_root, "receipt.json",
        "epyc.autokernel.async_prefetch_replay.v1")
    control_path, control, control_err = _latest_control_summary(control_root)
    production = _production_kernel_summary(attestation_path, production_repo)
    production_head = production.get("head") if production.get("available") else None
    loop = _loop_engineering_summary(state_root)
    scaffold = _scaffold_panel_summary(state_root)
    arena = _arena_campaign_progress(state_root)
    rocm = _rocm_diagnostics_summary(state_root)
    hip_decision = _hip_decision_grade_summary(state_root)
    adapter_root = REPO / "scripts/vidya/adapters"
    source_table_path = adapter_root / "README.md"
    try:
        source_table_text = source_table_path.read_text(encoding="utf-8")
        source_table_error = None
    except OSError as exc:
        source_table_text = ""
        source_table_error = str(exc)

    def _belief_source(source: str, rows: int, reader: str, status: str) -> dict:
        return {"source": source, "belief_rows": rows,
                "reader_present": (adapter_root / reader).is_file(),
                "source_table_listed": f"`{reader}`" in source_table_text,
                "reader": reader, "status": status}

    rocm_rows = sum((rocm.get("rvp", {}).get("belief_measurement_count", 0),
                     rocm.get("baseline_honesty", {}).get("belief_measurement_count", 0)))
    belief_sources = [
        _belief_source("AK-LE planner reduction", loop.get("belief_measurement_count", 0),
                       "autokernel_planner_reduction.py",
                       "live" if loop.get("belief_measurement_count", 0) else "awaiting evidence"),
        _belief_source("RVP-T0-1 + AK-BH-1 diagnostics", rocm_rows,
                       "autokernel_rocm_diagnostic.py",
                       "live" if rocm_rows else "awaiting post-hook receipt"),
        _belief_source("INF-03 Arena checkpoints", arena.get("belief_measurement_count", 0),
                       "autokernel_aux_receipt.py",
                       "live checkpoint rows; partial campaign not rankable"
                       if arena.get("belief_measurement_count", 0) else "awaiting post-hook checkpoint"),
        _belief_source("AK-LE-3 scaffold panel", scaffold.get("belief_measurement_count", 0),
                       "autokernel_scaffold_panel.py",
                       "live" if scaffold.get("belief_measurement_count", 0)
                       else "prospective successor-only; terminal r1 remains zero-row"),
        _belief_source("raw-HIP r6 task-local decision receipt",
                       2 if hip_decision.get("available") else 0,
                       "autokernel_aux_receipt.py",
                       "live task-local rows; no release/promotion authority"
                       if hip_decision.get("available") else "receipt unavailable"),
    ]
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
        "diagnostic_pilot": _diagnostic_pilot_summary(
            pilot_path, pilot, pilot_err),
        "instrument_preflight": _control_preflight_summary(
            preflight_path, preflight, preflight_err),
        "decision_controls": _control_summary(
            control_path, control, control_err, production_head),
        "gpu_prefetch_replay": _gpu_replay_summary(
            replay_path, replay, replay_err),
        "loop_engineering": loop,
        "scaffold_engineering": scaffold,
        "fault_rehearsal": _fault_rehearsal_summary(state_root),
        "arena_campaign_progress": arena,
        "implementation_readiness": _autokernel_implementation_readiness(
            AUTOKERNEL_RESEARCH_REPO),
        "rocm_diagnostics": rocm,
        "hip_decision_grade": hip_decision,
        "belief_source_wiring": {
            "source_table": str(source_table_path),
            "source_table_present": source_table_path.is_file(),
            "source_table_error": source_table_error,
            "sources": belief_sources,
            "note": ("reader presence never back-fills pre-hook evidence; displayed row counts "
                     "come only from producer-authored receipt vectors"),
        },
        # SCOPE, DECLARED (KRD-AUDIT-20260812). This panel projects a CURATED set of
        # receipt schemas, not everything under the probe/state roots. Many others are
        # legitimately intermediate, so the fix is not "render them all"; it is to stop a curated view
        # reading as a complete one. Naming the scope where the answer is printed is
        # the same rule the health-probe finding turned on: a reader acts on the pass.
        "receipt_coverage": {
            "projected_schemas": sorted(_PROJECTED_RECEIPT_SCHEMAS),
            "probe_root": str(probe_root),
            "state_root": str(state_root),
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
        "mainline_integration": [
            _mainline_integration_summary(AUTOKERNEL_ROOT_REPO, "epyc-root"),
            _mainline_integration_summary(repo, "epyc-inference-research"),
        ],
        "work_bundles": _autokernel_work_bundles(repo),
        "durable_state": _autokernel_journal_inventory(state_root),
        "probe_receipts": _autokernel_probe_receipts(state_root),
        "current_state": autokernel_current_state(
            probe_root, attestation_path, production_repo, control_root, state_root),
    }


def _discovery_lock_held(path: Path) -> bool:
    """True only while another process owns the controller's exclusive lock."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    except OSError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _safe_bundle_path(value: object, bundle: Path) -> Path | None:
    if not isinstance(value, str):
        return None
    path = Path(value)
    try:
        path.resolve(strict=False).relative_to(bundle.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return path


def _discovery_event_result(value: object, event: str,
                            *, version: int) -> dict | None:
    """Project one secret-free actor result, or refuse the whole event."""
    if value is None:
        if event in {"planner_completed", "planner_failed", "planner_refused",
                     "critic_completed"}:
            raise ValueError("terminal actor event lacks its exact typed result")
        return None
    if not isinstance(value, dict):
        raise ValueError("result is not an object")
    allowed = {"returncode", "stdout_sha256", "stderr_sha256", "decision",
               "refusal_type", "refusal_reason_sha256"}
    if set(value) - allowed:
        raise ValueError("result contains non-allowlisted fields")
    projected: dict = {}
    if "returncode" in value:
        code = value["returncode"]
        if isinstance(code, bool) or not isinstance(code, int):
            raise ValueError("returncode is not an integer")
        projected["returncode"] = code
    for key in ("stdout_sha256", "stderr_sha256", "refusal_reason_sha256"):
        if key in value:
            if key == "refusal_reason_sha256" and event != "planner_refused":
                raise ValueError("refusal digest is not on a planner refusal")
            item = value[key]
            if not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{64}", item) is None:
                raise ValueError(f"invalid {key}")
            projected[key] = item
    if "decision" in value:
        if value["decision"] not in {"accept", "reject", "revise"}:
            raise ValueError("invalid critic decision")
        projected["decision"] = value["decision"]
    if "refusal_type" in value:
        if event != "planner_refused" or value["refusal_type"] != "planner_output_refusal":
            raise ValueError("invalid planner refusal type")
        projected["refusal_type"] = value["refusal_type"]
    if event == "planner_refused" and set(projected) != {
            "returncode", "stdout_sha256", "stderr_sha256",
            "refusal_type", "refusal_reason_sha256"}:
        raise ValueError("planner refusal lacks its exact typed result")
    if event == "planner_refused" and projected.get("returncode") != 0:
        raise ValueError("planner refusal does not bind a successful actor exit")
    if (event == "planner_completed"
            and (set(projected) != {
                "returncode", "stdout_sha256", "stderr_sha256"}
                 or projected.get("returncode") != 0)):
        raise ValueError("invalid planner completion result")
    if (event == "planner_failed"
            and (set(projected) != {
                "returncode", "stdout_sha256", "stderr_sha256"}
                 or projected.get("returncode") == 0)):
        raise ValueError("invalid planner failure result")
    if event == "critic_completed" and set(projected) != {
            "stdout_sha256", "stderr_sha256", "decision"}:
        raise ValueError("invalid critic completion result")
    if event in {"planner_started", "critic_started", "critic_failed"}:
        raise ValueError("lifecycle marker carries a result")
    return projected


def _discovery_events_from_raw(raw: bytes, offset: int,
                               channel: str | None) -> tuple[list[dict], str | None]:
    """Validate one already-snapshotted bounded event-stream tail."""
    rows: list[dict] = []
    rejected = 0
    lines = raw.decode("ascii", "replace").splitlines()
    # A bounded tail may begin in the middle of a valid JSONL record. It is not
    # a producer contract rejection; discard that incomplete prefix before
    # counting malformed rows.
    if offset and lines:
        lines = lines[1:]
    for line in lines[-300:]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            rejected += 1
            continue
        if not isinstance(row, dict) or row.get("schema") not in \
                AUTOKERNEL_DISCOVERY_EVENT_SCHEMAS:
            rejected += 1
            continue
        version = 2 if row["schema"] == AUTOKERNEL_DISCOVERY_EVENT_SCHEMA_V2 else 1
        required = {"schema", "ts", "channel", "event", "campaign_id",
                    "hypothesis_id", "provider", "model", "effort"}
        allowed = required | {"result"}
        if version == 2:
            required |= {"event_id", "operation_key"}
            allowed |= {"event_id", "operation_key"}
        text_fields = ("channel", "event", "campaign_id", "hypothesis_id",
                       "provider", "model", "effort")
        if (not required.issubset(row) or set(row) - allowed
                or channel is not None and row.get("channel") != channel
                or row.get("channel") not in {"autokernel", "planner"}
                or any(not isinstance(row.get(key), str)
                       or re.fullmatch(r"[a-zA-Z0-9_.:-]{1,160}", row[key]) is None
                       for key in text_fields)
                or not isinstance(row.get("ts"), str)
                or re.fullmatch(
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                    r"(?:\.[0-9]{1,6})?Z", row["ts"]) is None
                or _parse_semantic_timestamp(row["ts"]) is None):
            rejected += 1
            continue
        lifecycle_events = {
            "planner_started", "planner_completed", "planner_failed",
            "planner_refused", "critic_started", "critic_completed",
            "critic_failed",
        }
        expected_channel = (
            "planner" if row["event"].startswith("planner_") else
            "autokernel" if row["event"].startswith("critic_") else None)
        if row["event"] not in lifecycle_events or row["channel"] != expected_channel:
            rejected += 1
            continue
        if version == 2:
            if (re.fullmatch(r"ake-[0-9a-f]{64}", row["event_id"]) is None
                    or re.fullmatch(r"[0-9a-f]{64}", row["operation_key"]) is None):
                rejected += 1
                continue
            identity = {key: row[key] for key in required
                        if key not in {"channel", "event_id", "ts"}}
            expected_id = "ake-" + hashlib.sha256(json.dumps(
                identity, sort_keys=True, separators=(",", ":")
            ).encode("ascii")).hexdigest()
            if row["event_id"] != expected_id:
                rejected += 1
                continue
        try:
            result = _discovery_event_result(
                row.get("result"), row["event"], version=version)
        except ValueError:
            rejected += 1
            continue
        # The producer contract contains no prompt, model text, command, env, or
        # credential fields. Re-project the allowlist anyway: consumers do not
        # become a secret exfiltration path if a future writer drifts.
        projected = {key: row[key] for key in (
            "schema", "event_id", "operation_key", "ts", "channel", "event",
            "campaign_id", "hypothesis_id", "provider", "model", "effort")
            if key in row}
        if result is not None:
            projected["result"] = result
        rows.append(projected)
    error = (f"{rejected} live event row{'s' if rejected != 1 else ''} "
             "rejected by telemetry contract" if rejected else None)
    return rows[-200:], error


_DISCOVERY_STREAM_LOCK_WAIT_S = 0.25
_DISCOVERY_STREAM_LOCK_RETRY_S = 0.005


def _discovery_event_streams(root: Path) -> tuple[
        list[dict], str | None, list[dict], str | None,
        list[dict], list[dict], list[dict], dict, str]:
    """Read the global+planner mirror under one producer-compatible snapshot.

    The producer takes exclusive locks in global-then-planner order around its
    dual write. Taking shared locks in the same order means the dashboard sees
    either side of that transaction, never its transient one-file midpoint.
    """
    names = ("autokernel.jsonl", "planner.jsonl")
    deadline = time.monotonic() + _DISCOVERY_STREAM_LOCK_WAIT_S
    while True:
        dir_fd: int | None = None
        fds: list[int | None] = [None, None]
        locked: list[int] = []
        errors: list[str | None] = [None, None]
        snapshots: list[tuple[bytes, int]] = [(b"", 0), (b"", 0)]
        baselines: list[os.stat_result | None] = [None, None]
        absent_at_open = [False, False]
        retry = False
        write_in_progress = False
        identity_drift = False
        directory_trusted = False
        try:
            # Open and lock in the producer's global-then-planner order. Both
            # locks remain held through parsing and reconciliation below.
            try:
                dir_fd = os.open(
                    root, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
                    | os.O_DIRECTORY)
                dir_info = os.fstat(dir_fd)
                root_info = root.lstat()
                if (not stat.S_ISDIR(dir_info.st_mode)
                        or not stat.S_ISDIR(root_info.st_mode)
                        or dir_info.st_uid != os.geteuid()
                        or root_info.st_uid != os.geteuid()
                        or (dir_info.st_dev, dir_info.st_ino)
                        != (root_info.st_dev, root_info.st_ino)):
                    raise OSError("telemetry stream directory identity is not trusted")
                directory_trusted = True
            except FileNotFoundError:
                # A sealed deployment may predate live telemetry entirely.
                # Absence is legacy/no pulse, not a corrupt stream directory.
                if dir_fd is not None:
                    os.close(dir_fd)
                    dir_fd = None
            except OSError as exc:
                message = f"live event stream directory unreadable: {exc}"
                errors = [message, message]
            for index, name in enumerate(names):
                if dir_fd is None or not directory_trusted:
                    break
                try:
                    fds[index] = os.open(
                        name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                        dir_fd=dir_fd)
                except FileNotFoundError:
                    absent_at_open[index] = True
                    continue
                except OSError as exc:
                    errors[index] = f"live event stream unreadable: {exc}"
            for fd in fds:
                if fd is None:
                    continue
                try:
                    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    locked.append(fd)
                except BlockingIOError:
                    write_in_progress = True
                    break
            if write_in_progress:
                retry = time.monotonic() < deadline
            else:
                for index, (name, fd) in enumerate(zip(names, fds)):
                    if fd is None:
                        # If a missing stream appeared after the opens, do not
                        # compare it with the other stream's older generation.
                        try:
                            os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                        except FileNotFoundError:
                            continue
                        except OSError as exc:
                            errors[index] = f"live event stream unreadable: {exc}"
                        else:
                            retry = time.monotonic() < deadline
                        continue
                    try:
                        before = os.fstat(fd)
                        path_before = os.stat(
                            name, dir_fd=dir_fd, follow_symlinks=False)
                        if (not stat.S_ISREG(before.st_mode)
                                or before.st_nlink != 1
                                or before.st_uid != os.geteuid()
                                or not stat.S_ISREG(path_before.st_mode)
                                or path_before.st_nlink != 1
                                or path_before.st_uid != os.geteuid()
                                or (before.st_dev, before.st_ino)
                                != (path_before.st_dev, path_before.st_ino)):
                            raise OSError(
                                "telemetry stream is not the current single-link regular file")
                        offset = max(0, before.st_size - 128 * 1024)
                        snapshots[index] = (
                            os.pread(fd, 128 * 1024, offset), offset)
                        after = os.fstat(fd)
                        path_after = os.stat(
                            name, dir_fd=dir_fd, follow_symlinks=False)
                        if (not stat.S_ISREG(after.st_mode)
                                or after.st_nlink != 1
                                or after.st_uid != os.geteuid()
                                or not stat.S_ISREG(path_after.st_mode)
                                or path_after.st_nlink != 1
                                or path_after.st_uid != os.geteuid()
                                or (after.st_dev, after.st_ino)
                                != (path_after.st_dev, path_after.st_ino)
                                or (before.st_dev, before.st_ino,
                                    before.st_size, before.st_mtime_ns,
                                    before.st_ctime_ns)
                                != (after.st_dev, after.st_ino,
                                    after.st_size, after.st_mtime_ns,
                                    after.st_ctime_ns)):
                            identity_drift = True
                            snapshots[index] = (b"", 0)
                            break
                        baselines[index] = before
                    except OSError as exc:
                        errors[index] = f"live event stream unreadable: {exc}"
                if identity_drift:
                    retry = time.monotonic() < deadline
                    if not retry:
                        errors[index] = errors[index] or (
                            "live event streams changed during snapshot")
                if (not retry and not identity_drift and dir_fd is not None
                        and directory_trusted):
                    try:
                        dir_after = os.fstat(dir_fd)
                        root_after = root.lstat()
                        if (not stat.S_ISDIR(dir_after.st_mode)
                                or not stat.S_ISDIR(root_after.st_mode)
                                or dir_after.st_uid != os.geteuid()
                                or root_after.st_uid != os.geteuid()
                                or (dir_after.st_dev, dir_after.st_ino)
                                != (root_after.st_dev, root_after.st_ino)
                                or (dir_info.st_dev, dir_info.st_ino)
                                != (dir_after.st_dev, dir_after.st_ino)):
                            identity_drift = True
                            retry = time.monotonic() < deadline
                            if not retry:
                                errors[0] = errors[0] or (
                                    "live event stream directory changed during snapshot")
                    except OSError as exc:
                        identity_drift = True
                        retry = time.monotonic() < deadline
                        if not retry:
                            errors[0] = errors[0] or (
                                f"live event stream directory unreadable: {exc}")
                if not retry:
                    if identity_drift:
                        snapshots = [(b"", 0), (b"", 0)]
                    all_rows, all_parse_error = _discovery_events_from_raw(
                        *snapshots[0], channel=None)
                    planner_rows, planner_parse_error = _discovery_events_from_raw(
                        *snapshots[1], channel="planner")
                    all_error = errors[0] or all_parse_error
                    planner_error = errors[1] or planner_parse_error
                    (lifecycle_events, visible_all_events,
                     visible_planner_events,
                     telemetry_integrity) = _discovery_reconcile_events(
                         all_rows, planner_rows, all_error, planner_error)
                    if not directory_trusted or dir_fd is None:
                        return (
                            all_rows, all_error, planner_rows, planner_error,
                            lifecycle_events, visible_all_events,
                            visible_planner_events, telemetry_integrity, "stable")
                    # The first stream can still change while the second is
                    # read or while the immutable byte snapshots are parsed.
                    # Revalidate the whole pair together immediately before
                    # return; per-file postchecks alone leave that cross-stream
                    # gap. Advisory SH locks bind cooperating producers, while
                    # this final identity/content epoch pass catches mutation
                    # by a writer that disregards the lock contract.
                    final_stable = True
                    try:
                        final_dir = os.fstat(dir_fd)
                        final_root = root.lstat()
                        final_stable = (
                            stat.S_ISDIR(final_dir.st_mode)
                            and stat.S_ISDIR(final_root.st_mode)
                            and final_dir.st_uid == os.geteuid()
                            and final_root.st_uid == os.geteuid()
                            and (final_dir.st_dev, final_dir.st_ino)
                            == (final_root.st_dev, final_root.st_ino)
                            and (dir_info.st_dev, dir_info.st_ino)
                            == (final_dir.st_dev, final_dir.st_ino))
                        for check_index, (name, fd, baseline) in enumerate(
                                zip(names, fds, baselines)):
                            if not final_stable:
                                break
                            if fd is None:
                                if not absent_at_open[check_index]:
                                    continue
                                try:
                                    os.stat(name, dir_fd=dir_fd,
                                            follow_symlinks=False)
                                except FileNotFoundError:
                                    continue
                                final_stable = False
                                break
                            if baseline is None:
                                continue
                            final_fd = os.fstat(fd)
                            final_path = os.stat(
                                name, dir_fd=dir_fd, follow_symlinks=False)
                            final_stable = (
                                stat.S_ISREG(final_fd.st_mode)
                                and final_fd.st_nlink == 1
                                and final_fd.st_uid == os.geteuid()
                                and stat.S_ISREG(final_path.st_mode)
                                and final_path.st_nlink == 1
                                and final_path.st_uid == os.geteuid()
                                and (final_fd.st_dev, final_fd.st_ino)
                                == (final_path.st_dev, final_path.st_ino)
                                and (baseline.st_dev, baseline.st_ino,
                                     baseline.st_size, baseline.st_mtime_ns,
                                     baseline.st_ctime_ns)
                                == (final_fd.st_dev, final_fd.st_ino,
                                    final_fd.st_size, final_fd.st_mtime_ns,
                                    final_fd.st_ctime_ns))
                    except OSError:
                        final_stable = False
                    if final_stable:
                        return (
                            all_rows, all_error, planner_rows, planner_error,
                            lifecycle_events, visible_all_events,
                            visible_planner_events, telemetry_integrity, "stable")
                    identity_drift = True
                    retry = time.monotonic() < deadline
                    if not retry:
                        errors[0] = errors[0] or (
                            "live event streams changed during final snapshot validation")
                        snapshots = [(b"", 0), (b"", 0)]
        finally:
            for fd in reversed(locked):
                fcntl.flock(fd, fcntl.LOCK_UN)
            for fd in reversed(fds):
                if fd is not None:
                    os.close(fd)
            if dir_fd is not None:
                os.close(dir_fd)
        if retry:
            time.sleep(_DISCOVERY_STREAM_LOCK_RETRY_S)
            continue
        if write_in_progress:
            integrity = {
                "state": "producer_write_in_progress", "verified": False,
                "detail": "producer is committing the dual telemetry stream transaction",
                "conflict_count": 0, "duplicate_identity_count": 0,
                "order_divergence": False, "missing_planner_count": 0,
                "missing_autokernel_count": 0,
                "timestamp_divergence_count": 0, "dropped_event_count": 0,
            }
            return ([], None, [], None, [], [], [], integrity,
                    "producer_write_in_progress")
        # A file appeared repeatedly while opening the pair. Surface an
        # unreadable stable snapshot rather than spin beyond the HTTP budget.
        errors[0] = errors[0] or "live event streams changed during snapshot"
        all_rows, all_parse_error = _discovery_events_from_raw(
            *snapshots[0], channel=None)
        planner_rows, planner_parse_error = _discovery_events_from_raw(
            *snapshots[1], channel="planner")
        all_error = errors[0] or all_parse_error
        planner_error = errors[1] or planner_parse_error
        (lifecycle_events, visible_all_events, visible_planner_events,
         telemetry_integrity) = _discovery_reconcile_events(
             all_rows, planner_rows, all_error, planner_error)
        return (all_rows, all_error, planner_rows, planner_error,
                lifecycle_events, visible_all_events, visible_planner_events,
                telemetry_integrity, "unstable")


def _discovery_reconcile_events(all_rows: list[dict],
                                planner_rows: list[dict],
                                all_error: str | None,
                                planner_error: str | None) -> tuple[
                                    list[dict], list[dict], list[dict], dict]:
    """Deduplicate v2 identity and expose dual-stream visibility defects."""
    stream_rows = {"autokernel": all_rows, "planner": planner_rows}
    by_stream: dict[str, dict[str, list[dict]]] = {
        "autokernel": {}, "planner": {}}
    for stream, rows in stream_rows.items():
        for row in rows:
            event_id = row.get("event_id")
            if isinstance(event_id, str):
                by_stream[stream].setdefault(event_id, []).append(row)
    ids = set(by_stream["autokernel"]) | set(by_stream["planner"])
    conflicts: set[str] = set()
    duplicates = {
        event_id for event_id in ids
        if len(by_stream["autokernel"].get(event_id, [])) > 1
        or len(by_stream["planner"].get(event_id, [])) > 1}
    unique: dict[str, dict] = {}
    for event_id in ids:
        candidates = (by_stream["autokernel"].get(event_id, [])
                      + by_stream["planner"].get(event_id, []))
        canonical = {json.dumps(
            {key: value for key, value in row.items() if key != "ts"},
            sort_keys=True, separators=(",", ":"))
                     for row in candidates}
        if len(canonical) != 1:
            conflicts.add(event_id)
        elif candidates:
            unique[event_id] = candidates[0]
    timestamp_divergence = sorted(
        event_id for event_id in ids if event_id not in conflicts
        and len({row.get("ts") for row in (
            by_stream["autokernel"].get(event_id, [])
            + by_stream["planner"].get(event_id, []))}) > 1)
    all_planner_sequence = [row["event_id"] for row in all_rows
                            if isinstance(row.get("event_id"), str)
                            and row.get("channel") == "planner"]
    planner_sequence = [row["event_id"] for row in planner_rows
                        if isinstance(row.get("event_id"), str)]
    common_sequence_ids = set(all_planner_sequence) & set(planner_sequence)
    order_divergence = (
        [item for item in all_planner_sequence if item in common_sequence_ids]
        != [item for item in planner_sequence if item in common_sequence_ids])
    corruptions = conflicts | duplicates | set(timestamp_divergence)
    if order_divergence:
        corruptions |= common_sequence_ids
    all_floor = min((str(rows[0].get("ts") or "")
                     for rows in by_stream["autokernel"].values() if rows),
                    default=None)
    planner_floor = min((str(rows[0].get("ts") or "")
                         for rows in by_stream["planner"].values() if rows),
                        default=None)
    # Compare only the overlapping bounded tails. A planner-only stream can
    # legitimately retain older planner rows that fell out of the global
    # stream's 200-row window because intervening critic rows consumed it.
    missing_planner = sorted(
        event_id for event_id, rows in by_stream["autokernel"].items()
        if event_id not in by_stream["planner"]
        and any(row.get("channel") == "planner" for row in rows)
        and (planner_floor is None
             or str(rows[0].get("ts") or "") >= planner_floor))
    missing_autokernel = sorted(
        event_id for event_id, rows in by_stream["planner"].items()
        if event_id not in by_stream["autokernel"]
        and (all_floor is None or str(rows[0].get("ts") or "") >= all_floor))

    def visible(rows: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for row in rows:
            event_id = row.get("event_id")
            if event_id in corruptions or isinstance(event_id, str) and event_id in seen:
                continue
            if isinstance(event_id, str):
                seen.add(event_id)
            out.append(row)
        return out

    visible_all = visible(all_rows)
    visible_planner = visible(planner_rows)
    legacy = [row for row in visible_all
              if row.get("schema") == AUTOKERNEL_DISCOVERY_EVENT_SCHEMA]
    merged = legacy + [row for event_id, row in unique.items()
                       if event_id not in corruptions]
    merged.sort(key=lambda row: str(row.get("ts") or ""))
    problems = []
    if all_error:
        problems.append(f"AutoKernel stream: {all_error}")
    if planner_error:
        problems.append(f"planner stream: {planner_error}")
    if conflicts:
        problems.append(
            f"{len(conflicts)} conflicting event "
            f"{'identities' if len(conflicts) != 1 else 'identity'} dropped")
    if duplicates:
        problems.append(f"{len(duplicates)} duplicate event identit"
                        f"{'ies' if len(duplicates) != 1 else 'y'} dropped")
    if timestamp_divergence:
        problems.append(f"{len(timestamp_divergence)} event timestamp"
                        f"{'s' if len(timestamp_divergence) != 1 else ''} "
                        "diverge across streams and were dropped")
    if order_divergence:
        problems.append("planner mirror event order diverges; overlapping rows were dropped")
    if missing_planner:
        problems.append(f"{len(missing_planner)} planner event"
                        f"{'s' if len(missing_planner) != 1 else ''} missing from planner stream")
    if missing_autokernel:
        problems.append(f"{len(missing_autokernel)} planner event"
                        f"{'s' if len(missing_autokernel) != 1 else ''} missing from AutoKernel stream")
    has_v2 = bool(ids)
    integrity = {
        "state": ("conflict" if corruptions else "degraded" if problems else
                  "verified" if has_v2 else "legacy"),
        "verified": has_v2 and not problems,
        "detail": ("; ".join(problems) if problems else
                   "v2 event identities agree across required streams" if has_v2 else
                   "legacy v1 telemetry has no cross-stream event identity"),
        "conflict_count": len(conflicts),
        "duplicate_identity_count": len(duplicates),
        "order_divergence": order_divergence,
        "missing_planner_count": len(missing_planner),
        "missing_autokernel_count": len(missing_autokernel),
        "timestamp_divergence_count": len(timestamp_divergence),
        "dropped_event_count": len(corruptions),
    }
    return merged[-200:], visible_all[-200:], visible_planner[-200:], integrity


def _discovery_v26_actor_bypass_telemetry_integrity(
        integrity: dict, v26_state: dict | None, *,
        all_events: list[dict], planner_events: list[dict],
        all_error: str | None, planner_error: str | None,
        snapshot_status: str) -> dict:
    """Classify exact preauthored actor absence without calling it legacy.

    The v26 Q5 continuation deliberately bypasses both planner and critic.  Its
    current authority is the strict controller-state/journal join plus governed
    build/screen receipts, so an empty actor telemetry directory is expected on
    this one path.  Any row, parse error, unstable snapshot, or loss of the
    imported authority leaves the ordinary telemetry verdict untouched.
    """
    provenance = (v26_state.get("provenance")
                  if isinstance(v26_state, dict) else None)
    if (not isinstance(integrity, dict)
            or integrity.get("state") != "legacy"
            or not isinstance(provenance, dict)
            or provenance.get("imported") is not True
            or provenance.get("actor_bypass") is not True
            or all_events or planner_events or all_error or planner_error
            or snapshot_status != "stable"):
        return integrity
    return {
        **integrity,
        "state": "not_applicable",
        "verified": True,
        "detail": (
            "verified expected absence: this preauthored continuation bypasses "
            "planner and critic actors; current progress is bound by the "
            "controller state/journal and governed stage receipts"),
    }


def _discovery_state_visibility_degraded(state: dict | None) -> list[dict]:
    """Project producer-persisted telemetry failures without raw error text."""
    values = state.get("visibility_degraded") if isinstance(state, dict) else None
    if not isinstance(values, list):
        return []
    projected: list[dict] = []
    for value in values[-100:]:
        if (not isinstance(value, dict)
                or set(value) != {"event", "operation_key", "error_type",
                                  "error_sha256"}
                or not isinstance(value.get("event"), str)
                or re.fullmatch(r"[a-z0-9_]{1,100}", value["event"]) is None
                or not isinstance(value.get("operation_key"), str)
                or re.fullmatch(r"[0-9a-f]{64}", value["operation_key"]) is None
                or not isinstance(value.get("error_type"), str)
                or re.fullmatch(r"[a-zA-Z0-9_.]{1,100}",
                                value["error_type"]) is None
                or not isinstance(value.get("error_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", value["error_sha256"]) is None):
            continue
        projected.append(dict(value))
    return projected


_DISCOVERY_PIPELINE = (
    ("planner", "Planner"),
    ("planner_validation", "Validate planner output"),
    ("critic", "Critic review"),
    ("authorization", "Governance authorization"),
    ("resource_admission", "Resource admission"),
    ("source_materialization", "Source validation / materialization"),
    ("build", "Compile anchor and candidate"),
    ("evidence_binding", "Bind build to proof plan"),
    ("correctness", "Correctness proof"),
    ("correctness_validation", "Validate correctness result"),
    ("candidate_attribution", "Candidate dispatch attribution"),
    ("anchor_attribution", "Anchor dispatch attribution"),
    ("dispatch_proof", "Dispatch attribution"),
    ("profile", "Kernel profile"),
    ("measurement_graphs_off_screen", "Graphs-off measurement screen"),
    ("target_runtime_graphs_on_screen", "Graphs-on target-runtime screen"),
    ("benchmark", "Whole-model benchmark"),
    ("decision", "Classify result"),
    ("replication_s1", "Replication S1"),
    ("replication_s2", "Replication S2"),
    ("next_hypothesis", "Automatic next hypothesis"),
)

_DISCOVERY_POSTBUILD_STAGES = (
    "correctness", "correctness_validation", "candidate_attribution",
    "anchor_attribution", "dispatch_proof", "profile",
    "measurement_graphs_off_screen", "target_runtime_graphs_on_screen",
    "benchmark", "decision",
)
_DISCOVERY_PIPELINE_DICT = dict(_DISCOVERY_PIPELINE)
_EXPERIMENTAL_RUNTIME_PIPELINE = (
    ("experimental_build", "Experimental build"),
    ("cpu_gpu_regression", "CPU + GPU regression"),
    ("matched_np1", "Matched np=1 comparison"),
    ("concurrency_grid", "Concurrency grid np=2/4/8"),
    ("greedy_parity", "Greedy token parity"),
    ("decision", "Runtime candidate decision"),
)
_EXPERIMENTAL_RUNTIME_STAGES = tuple(
    stage for stage, _label in _EXPERIMENTAL_RUNTIME_PIPELINE)
_EXPERIMENTAL_RUNTIME_PIPELINE_DICT = dict(_EXPERIMENTAL_RUNTIME_PIPELINE)
_EXPERIMENTAL_RUNTIME_SCHEMA = \
    "epyc.autokernel.experimental_runtime_dashboard.v1"
_EXPERIMENTAL_RUNTIME_RECEIPT_SCHEMA = \
    "epyc.autokernel.experimental_runtime_stage_receipt.v1"
_DISCOVERY_STALL_S = 300.0
_DISCOVERY_STAGE_STALL_S = {
    # The sealed Claude critic has a 900-second process timeout, and the Codex
    # planner has historically needed several minutes for the full source
    # catalogue.  A five-minute generic warning would therefore report known
    # healthy actor calls as stalled.  These are no-transition budgets, not
    # synthetic heartbeats or execution timeouts.
    "planner": 900.0,
    "critic": 900.0,
    "build": 1800.0,
    # The governed test-backend-ops correctness plan has an 1800-second
    # execution timeout.  A live held source-proof claim is positive actor
    # evidence throughout that window; the generic five-minute budget would
    # falsely mark a healthy 1139-case ROCm suite stalled.
    "correctness": 1800.0,
}


def _discovery_checkpoint(path: Path) -> dict | None:
    """Return the latest allowlisted STOP_STATE without exposing journal data."""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - 128 * 1024))
            raw = handle.read(128 * 1024)
    except (FileNotFoundError, OSError):
        return None
    latest = None
    history: list[dict] = []
    for line in raw.decode("ascii", "replace").splitlines()[-300:]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = row.get("payload") if isinstance(row, dict) else None
        digest = payload.get("controller_state_sha256") if isinstance(payload, dict) else None
        if (row.get("journal_schema") != "epyc.autokernel.journal_entry.v1"
                or row.get("kind") != "STOP_STATE" or not isinstance(payload, dict)
                or not isinstance(payload.get("state"), str)
                or re.fullmatch(r"[a-z0-9_]{1,100}", payload["state"]) is None
                or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or not isinstance(row.get("seq"), int)
                or not isinstance(row.get("written_at"), str)):
            continue
        latest = {
            "seq": row.get("seq"), "state": payload["state"],
            "written_at": row["written_at"],
            "controller_state_sha256": payload.get("controller_state_sha256"),
        }
        history.append(latest)
    if latest is not None:
        # Keep the same bounded journal window used by the strict parser. A
        # long-running campaign may advance many checkpoints after a typed
        # terminal; retaining only the last 25 would force its pulse/history
        # timestamp to fall back to the receipt mtime instead of the exact
        # durable STOP_STATE boundary.
        latest = {**latest, "history": history[-300:]}
    return latest


_DISCOVERY_TERMINAL_STATE_KEYS = {
    "admission_corpus_sha256", "admission_corpus_version",
    "attempted_candidate_identities", "authority",
    "candidate_semantic_registry_schema", "complete",
    "deployment_identity_sha256", "experiment_template_registry_sha256",
    "hypothesis_portfolio_sha256", "iterations", "next",
    "planner_context_sha256", "portfolio_authoring_failures",
    "portfolio_skips", "portfolio_terminals", "roster", "schema",
    "scientific_attempts", "state_sha256", "terminal_reason", "updated_at",
}


def _discovery_controller_state_hash(value: object) -> str | None:
    """Match discovery_controller._sha (ASCII-escaped canonical JSON)."""
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(raw).hexdigest()


_DISCOVERY_V26_DEPLOYMENT_KEYS = {
    "schema", "config_sha256", "production", "instrument", "controller",
    "actors", "gpu", "immutable_inputs", "planner_context", "source_plan",
}
_DISCOVERY_V26_PLANNER_KEYS = {
    "schema", "context_sha256", "model_sha256", "workload_sha256",
    "runtime_config_sha256", "profile_receipts", "hotspots",
    "source_constraints", "initial_strategies",
    "hypothesis_portfolio_sha256", "eligible_hypotheses", "do_not_repeat",
    "incumbents", "ineligible_hypotheses",
    "hypothesis_evidence_manifest_sha256", "hypothesis_evidence",
    "reviewed_source_package_sha256", "template_registry_sha256",
    "template_symbol_authority", "template_surfaces_sha256",
    "template_surfaces", "portfolio_dispatch_authority",
    "preauthored_continuation_sha256",
    "preauthored_source_backed_diff_sha256",
    "preauthored_historical_evidence_sha256",
}
_DISCOVERY_V26_GRAPH_KEYS = {
    "schema", "authority", "promotion_claim", "inference_executed",
    "config_sha256", "registry_ids", "template_registry_sha256",
    "template_surfaces", "template_surfaces_sha256",
    "portfolio_dispatch_authority",
    "portfolio_dispatch_authority_sha256", "hypothesis_portfolio",
    "carry_forward_sha256", "preauthored_continuation",
    "reviewed_source_package", "profile_trace_authority",
    "profiler_runtime_authority", "admission_policy_sha256",
    "load_admission_profile_id", "actor_wrappers", "actor_runtimes",
    "actor_cells", "actor_argv_authority", "critic_auth_source",
    "execution_modules", "environment_profiles", "source_authority",
    "instrument_review", "batched_runner", "instrument_target_equality",
    "production_runtime_snapshot_sha256", "mutable_roots", "device_id",
    "device_reservation", "claim_journal", "graph_sha256",
}
_DISCOVERY_V27_GRAPH_KEYS = (
    _DISCOVERY_V26_GRAPH_KEYS | {
        "attribution_expectation_erratum", "frozen_production_comparator"})
_DISCOVERY_V27_ERRATUM_FILE_SHA256 = (
    "22f23f769bd7e10e24d2c642846fa0b739c5ff03b457c56e374d941f01b60a98")
_DISCOVERY_V27_ERRATUM_SHA256 = (
    "21f5f1c25c337275293a0c701e23c9da8c5efb835c6803f4c58daa789f2f0b6b")
_DISCOVERY_V27_ERRATUM_REASON = (
    "exact dispatch cuda-mmvq-q5-onewave-continuation-v1.anchor.0."
    "candidate-onewave count/geometry mismatch")
_DISCOVERY_V27_ERRATUM_SOURCE_KEYS = {
    "schema", "erratum_schema", "erratum_sha256", "file_sha256",
    "operation_key", "attribution_refusal_file_sha256",
    "candidate_semantic_sha256",
}
_DISCOVERY_V27_ERRATUM_KEYS = {
    "schema", "predecessor_campaign_id", "operation_key", "hypothesis_id",
    "candidate_semantic_sha256", "candidate_patch_sha256",
    "cross_campaign_candidate_sha256", "source_manifest_file_sha256",
    "correctness_receipt_file_sha256", "correctness_receipt_sha256",
    "evidence_policy_file_sha256", "attribution_refusal_file_sha256",
    "attribution_refusal_receipt_sha256", "classification",
    "candidate_source_commit", "candidate_binary_sha256",
    "candidate_hip_library_sha256", "anchor_hip_library_sha256",
    "profiler_trace_sha256", "reason", "invalidated_predecessor_projection",
    "stale_candidate_lds_bytes", "corrected_candidate_lds_bytes",
    "compiler_metadata_proof", "preserved_evidence",
    "scientific_budget_spent", "do_not_repeat", "replay_authorized",
    "replacement_disposition", "resolution", "erratum_sha256",
}
_DISCOVERY_V27_CARRY_KEYS = {
    "schema", "predecessor_state_file_sha256",
    "predecessor_journal_file_sha256",
    "predecessor_state_semantic_sha256", "portfolio_outcomes",
    "candidate_semantic_sha256", "candidate_patch_sha256",
    "cross_campaign_candidate_sha256", "attribution_expectation_erratum",
    "carry_forward_sha256",
}
_DISCOVERY_V27_CARRY_OUTCOMES = {
    "akh-v2-q5-type-specific-dequant": "nominated",
    "akh-v2-q8-quantizer-new-mechanism": "retire",
    "akh-v2-fa-gqa7-pair-tail": "bounded_authoring_skip",
    "akh-v2-rms-direct-load-reduction": "bounded_authoring_skip",
}
_DISCOVERY_V27_PREDECESSOR = {
    "predecessor_state_file_sha256":
        "7ce6e5561572390e0a1a31ff8a059be3b68c8cfc809a9233c2e22a8ca730ef3c",
    "predecessor_journal_file_sha256":
        "a715dbbf8a8e089ea9e356339ceaf8f007bf6191ee0ea699d445c1560ddc5b69",
    "predecessor_state_semantic_sha256":
        "9d2d58bfa0d7df68107529c5e29b37c978d53efd78803537eb709ffba37ffd64",
}
_DISCOVERY_V27_COMPARATOR_SOURCE_KEYS = {
    "schema", "file_sha256", "receipt_sha256"}
_DISCOVERY_V26_PREAUTHORED_GRAPH_KEYS = {
    "schema", "carrier_sha256", "file_sha256", "hypothesis_id",
    "template_id", "patch_sha256", "source_backed_diff_sha256",
    "historical_evidence_sha256", "historical_correctness_authority",
    "modern_governed_correctness_required",
}
_DISCOVERY_V26_PREAUTHORED_CHECKPOINT_KEYS = {
    "schema", "hypothesis_id", "authoring_turn", "carrier_sha256",
    "source_backed_diff_sha256", "source_manifest_sha256",
    "candidate_semantic_sha256", "cross_campaign_candidate_sha256",
    "origin", "author", "historical_commit",
    "modern_governed_correctness_required", "receipt_sha256",
}
_DISCOVERY_V26_ROSTER = {
    "schema": "epyc.autokernel.discovery_roster.v3",
    "members": [
        {"provider": "codex", "model": "gpt-5.6-sol",
         "effort": "high", "role": "planner"},
        {"provider": "claude", "model": "claude-fable-5",
         "effort": "high", "role": "critic"},
    ],
    "claude_members": 1,
    "member_count": 2,
}
_DISCOVERY_V26_STATE_REQUIRED = {
    "schema", "authority", "roster", "iterations", "next",
    "scientific_attempts", "complete", "deployment_identity_sha256",
    "planner_context_sha256", "experiment_template_registry_sha256",
    "admission_corpus_sha256", "admission_corpus_version",
    "hypothesis_portfolio_sha256", "carry_forward_sha256",
    "preauthored_continuation_sha256",
    "preauthored_source_backed_diff_sha256", "updated_at", "state_sha256",
}
_DISCOVERY_V26_STATE_OPTIONAL = {
    "pending", "inflight", "planning", "planner_provider_attempt",
    "visibility_degraded", "attempted_candidate_identities",
    "candidate_semantic_registry_schema", "infrastructure_ambiguities",
    "portfolio_attribution_failures", "portfolio_authoring_failures",
    "portfolio_measurement_output_failures", "portfolio_skips",
    "portfolio_terminals", "portfolio_validations", "terminal_reason",
}
_DISCOVERY_V26_CHECKPOINT_STATES = {
    "discovery_authorization_refused",
    "discovery_attribution_route_falsified",
    "discovery_candidate_semantic_repeat_refused",
    "discovery_complete",
    "discovery_correctness_falsified",
    "discovery_critic_checkpointed",
    "discovery_critic_refused",
    "discovery_dry_run_authorized",
    "discovery_measurement_output_refused",
    "discovery_paused",
    "discovery_planner_checkpointed",
    "discovery_planner_contract_refused",
    "discovery_planner_entering",
    "discovery_planner_intent",
    "discovery_planner_refused",
    "discovery_planner_telemetry_recovery",
    "discovery_planner_terminal_failure",
    "discovery_planner_transient",
    "discovery_portfolio_dnr_refused",
    "discovery_portfolio_exhausted",
    "discovery_post_screen_result",
    "discovery_pre_screen_intent",
    "discovery_pre_screen_reacquired",
    "discovery_preauthored_checkpointed",
    "discovery_recovered_screen",
    "discovery_screen_ambiguous",
    "discovery_screen_infrastructure_ambiguity",
    "discovery_screen_refused",
    "discovery_screen_resumable_interruption",
    "discovery_screened",
    "discovery_visibility_degraded",
    "discovery_waiting_resource",
    "discovery_authoring_refused",
}
_DISCOVERY_V26_ITERATION_KEYS = {
    "turn", "status", "reason", "refusal_type", "statement", "falsifier",
    "regime", "hypothesis_id", "proposal_sha256",
    "source_manifest_sha256", "experiment_intent", "mechanism_id",
    "target_surface", "target_symbol", "context_sha256",
    "candidate_semantic_sha256", "portfolio_hypothesis_id",
    "portfolio_binding", "portfolio_record_sha256",
    "portfolio_decision_policy", "portfolio_exact_dnr_check",
    "portfolio_disposition", "priority", "current_bundle_eligibility",
    "critic", "authorization", "campaign_ledger_dnr_outcome",
    "campaign_ledger_dnr_reasons", "preauthored_continuation",
    "authoring_turn", "hypothesis_origin", "hypothesis_author",
    "historical_correctness_authority",
    "modern_governed_correctness_required", "operation_key", "lease",
    "replication_of", "result_sha256", "evidence", "effect_fraction",
    "series_effect_fraction", "series_key", "component_series_keys",
    "exact_attribution_effect_fraction", "target_runtime_effect_fraction",
    "target_runtime_executed", "target_runtime_reason", "stages",
    "repetition", "scientific_budget_spent", "classification",
    "correctness_status", "stage", "stage_receipt_path",
    "stage_receipt_sha256", "receipt_path", "schema", "authority",
    "idempotency_key", "threshold", "promotion_claim",
    "operator_decision_required", "planner_operation_key",
    "planner_checkpoint_reused", "telemetry_event", "telemetry_status",
    "telemetry_failure", "telemetry_failures", "telemetry_recovery",
    "visibility_degraded",
}


def _discovery_sha256(value: object) -> bool:
    return (isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _discovery_content_hash(value: object) -> str | None:
    """Match producer schemas.content_hash (UTF-8 canonical JSON)."""
    try:
        return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()
    except (TypeError, ValueError):
        return None


def _discovery_v26_input(value: object, bundle: Path,
                         *, max_bytes: int) -> tuple[dict, bytes] | None:
    if (not isinstance(value, dict) or set(value) != {"path", "sha256"}
            or not _discovery_sha256(value.get("sha256"))):
        return None
    path = _safe_bundle_path(value.get("path"), bundle)
    if path is None:
        return None
    snapshot = _owned_public_snapshot(path, max_bytes=max_bytes)
    if snapshot is None or hashlib.sha256(snapshot[0]).hexdigest() != value["sha256"]:
        return None
    return value, snapshot[0]


def _discovery_v27_erratum(value: object) -> bool:
    """Validate the one Q5 attribution-expectation correction carried by v27."""
    if (not isinstance(value, dict) or set(value) != _DISCOVERY_V27_ERRATUM_KEYS
            or value.get("schema") !=
               "epyc.autokernel.attribution_expectation_erratum.v1"
            or value.get("predecessor_campaign_id") !=
               "ak-discovery-03fc1b1230487a35"
            or value.get("operation_key") !=
               "fdfbf8434c361a32cd07d86ac247f61c62f9f840bc3ed8b437053f089e33f837"
            or value.get("hypothesis_id") !=
               "akh-v2-q5-onewave-preauthored"
            or value.get("candidate_semantic_sha256") !=
               "06973eb2e4f643b76de198d6cae5e2e9f1b915773dafdf5efd08682bf0df2b63"
            or value.get("candidate_patch_sha256") !=
               "f4cc49cd11cdfd93a2d5d2e00e653f503b6a16ce675bfb12c034fbbfae3e7a77"
            or value.get("cross_campaign_candidate_sha256") !=
               "d5671a1dc197e5d0d53f34f9c4d25f640e0e410d6917b3099459bc40064581b2"
            or value.get("attribution_refusal_file_sha256") !=
               "40707008b6fceae9749dfca56253836e07ce51b19eb7fb003377c3340503eb86"
            or value.get("classification") != "attribution_route_falsified"
            or value.get("reason") != _DISCOVERY_V27_ERRATUM_REASON
            or value.get("scientific_budget_spent") is not False
            or value.get("do_not_repeat") is not False
            or value.get("replay_authorized") is not True
            or value.get("replacement_disposition") !=
               "attribution_expectation_invalid"
            or value.get("resolution") != "unresolved_retry_eligible"
            or value.get("preserved_evidence") !=
               ["source_manifest", "governed_correctness"]
            or value.get("erratum_sha256") != _DISCOVERY_V27_ERRATUM_SHA256
            or value.get("erratum_sha256") != _discovery_content_hash({
                   key: item for key, item in value.items()
                   if key != "erratum_sha256"})):
        return False
    invalidated = value.get("invalidated_predecessor_projection")
    if invalidated != {
            "turn": 1,
            "result_file_sha256":
                "40707008b6fceae9749dfca56253836e07ce51b19eb7fb003377c3340503eb86",
            "removed_effects": [
                "scientific_attempt", "attempted_candidate_identity",
                "portfolio_skip", "cross_campaign_do_not_repeat"],
            "history_retained": True,
    }:
        return False
    corrected = value.get("corrected_candidate_lds_bytes")
    stale = value.get("stale_candidate_lds_bytes")
    if (not isinstance(corrected, dict) or not corrected
            or not isinstance(stale, dict)
            or set(corrected) != set(stale)
            or any(type(item) is not int for item in stale.values())
            or any(type(item) is not int or item != 0
                   for item in corrected.values())
            or sorted(stale.values()) != [256, 512, 512, 512]):
        return False
    proof = value.get("compiler_metadata_proof")
    proof_keys = {
        "schema", "llvm_objcopy_sha256", "llvm_objcopy_version",
        "section_extraction_command", "clang_offload_bundler_sha256",
        "clang_offload_bundler_version", "llvm_readobj_sha256",
        "llvm_readobj_version", "metadata_command", "symbol_command",
        "bundle_parser", "candidate_code_object_sha256",
        "anchor_code_object_sha256", "selected_mangled_name_set", "rows",
    }
    if (not isinstance(proof, dict) or set(proof) != proof_keys
            or proof.get("schema") !=
               "epyc.autokernel.amdgpu_group_segment_proof.v2"
            or proof.get("candidate_code_object_sha256") !=
               "53c63348f3e1797c6c27a82e887bb0b20649636c725fb04d85af3e2038838bd6"
            or proof.get("anchor_code_object_sha256") !=
               "ba878a186026165135705597b1c4966c06c7af6a46a5dd99c3194dc76e7d8ab0"
            or not isinstance(proof.get("rows"), list)
            or len(proof["rows"]) != 2
            or any(not isinstance(row, dict) or set(row) != {
                    "mangled_name", "candidate_group_segment_fixed_size",
                    "anchor_group_segment_fixed_size"}
                   or not isinstance(row.get("mangled_name"), str)
                   or not row["mangled_name"]
                   for row in proof["rows"])
            or proof.get("selected_mangled_name_set") != sorted(
                row["mangled_name"] for row in proof["rows"])
            or len(set(proof["selected_mangled_name_set"])) != 2
            or {(row.get("candidate_group_segment_fixed_size"),
                 row.get("anchor_group_segment_fixed_size"))
                for row in proof["rows"] if isinstance(row, dict)} !=
               {(0, 512), (0, 1024)}):
        return False
    parser = proof.get("bundle_parser")
    parser_keys = {
        "format", "container_count", "selected_bundle_index",
        "bundle_index_base", "selected_target_index", "target_index_base",
        "selected_target", "payload_offset_within_container",
        "candidate", "anchor",
    }
    object_keys = {
        "section_sha256", "section_size", "container_offset",
        "code_object_size"}
    if (not isinstance(parser, dict) or set(parser) != parser_keys
            or {key: parser.get(key) for key in (
                "format", "container_count", "selected_bundle_index",
                "bundle_index_base", "selected_target_index",
                "target_index_base", "selected_target",
                "payload_offset_within_container")} != {
                    "format": "clang_offload_bundle_header_little_endian_v1",
                    "container_count": 135, "selected_bundle_index": 35,
                    "bundle_index_base": 0, "selected_target_index": 1,
                    "target_index_base": 0,
                    "selected_target": "hipv4-amdgcn-amd-amdhsa--gfx90a",
                    "payload_offset_within_container": 4096,
                }
            or any(not isinstance(parser.get(arm), dict)
                   or set(parser[arm]) != object_keys
                   or not _discovery_sha256(
                       parser[arm].get("section_sha256"))
                   or any(type(parser[arm].get(key)) is not int
                          or parser[arm][key] <= 0 for key in (
                              "section_size", "container_offset",
                              "code_object_size"))
                   for arm in ("candidate", "anchor"))
            or any(not _discovery_sha256(proof.get(key)) for key in (
                "llvm_objcopy_sha256", "clang_offload_bundler_sha256",
                "llvm_readobj_sha256"))
            or any(not isinstance(proof.get(key), str) or not proof[key]
                   for key in (
                       "llvm_objcopy_version", "clang_offload_bundler_version",
                       "llvm_readobj_version"))
            or proof.get("section_extraction_command") != [
                "/opt/rocm/llvm/bin/llvm-objcopy",
                "--dump-section=.hip_fatbin=<section-output>",
                "<hip-library>"]
            or proof.get("metadata_command") != [
                "/opt/rocm/llvm/bin/llvm-readobj", "--notes",
                "<gfx90a-code-object>"]
            or proof.get("symbol_command") != [
                "/opt/rocm/llvm/bin/llvm-readelf", "-sW",
                "<gfx90a-code-object>"]):
        return False
    return all(_discovery_sha256(value.get(key)) for key in (
        "source_manifest_file_sha256", "correctness_receipt_file_sha256",
        "correctness_receipt_sha256", "evidence_policy_file_sha256",
        "attribution_refusal_receipt_sha256", "candidate_binary_sha256",
        "candidate_hip_library_sha256", "anchor_hip_library_sha256",
        "profiler_trace_sha256")) and bool(re.fullmatch(
            r"[0-9a-f]{40}", str(value.get("candidate_source_commit"))))


def _discovery_v27_carry_forward(value: object,
                                 erratum: object) -> bool:
    """Validate the exact immutable v2 predecessor authority consumed by v27."""
    if (not isinstance(value, dict) or set(value) != _DISCOVERY_V27_CARRY_KEYS
            or value.get("schema") !=
               "epyc.autokernel.discovery_carry_forward.v2"
            or value.get("portfolio_outcomes") !=
               _DISCOVERY_V27_CARRY_OUTCOMES
            or any(value.get(key) != digest for key, digest in
                   _DISCOVERY_V27_PREDECESSOR.items())
            or value.get("attribution_expectation_erratum") != erratum
            or value.get("carry_forward_sha256") !=
               _discovery_content_hash({
                   key: item for key, item in value.items()
                   if key != "carry_forward_sha256"})
            or any(not _discovery_sha256(value.get(key)) for key in (
                "predecessor_state_file_sha256",
                "predecessor_journal_file_sha256",
                "predecessor_state_semantic_sha256"))):
        return False
    replay_keys = (
        "candidate_semantic_sha256", "candidate_patch_sha256",
        "cross_campaign_candidate_sha256")
    if any(not isinstance(value.get(key), list)
           or value[key] != sorted(set(value[key]))
           or any(not _discovery_sha256(item) for item in value[key])
           for key in replay_keys):
        return False
    return tuple(len(value[key]) for key in replay_keys) == (13, 8, 8)


def _discovery_product_contract(
        config_path: Path, config: object, bundle: Path, *,
        deployment_schema: str, graph_schema: str,
        input_keys: set[str], graph_keys: set[str],
        execution_module_sha256: object, producer_commit: object,
        deployment_semantic_sha256: object,
        deployment_file_sha256: object, graph_sha256: object,
        graph_file_sha256_frozen: object,
        q5_erratum_required: bool = False) -> dict | None:
    """Validate a sealed successor config/planner/graph without producer imports.

    The returned ``ready`` bit is true only when the graph matches the frozen
    producer commit, whole-graph digest, and all 30 role-bound module digests;
    callers must not select a live campaign on self-declared hashes alone.
    """
    if (not isinstance(config, dict)
            or set(config) != _DISCOVERY_V26_DEPLOYMENT_KEYS
            or config.get("schema") != deployment_schema
            or not _discovery_sha256(config.get("config_sha256"))
            or config["config_sha256"] != _discovery_content_hash({
                key: value for key, value in config.items()
                if key != "config_sha256"})):
        return None
    source = _owned_public_snapshot(config_path, max_bytes=512 * 1024)
    if source is None or _strict_json_bytes(source[0]) != config:
        return None
    config_file_sha256 = hashlib.sha256(source[0]).hexdigest()
    exact_nested = {
        "production": {"path", "branch", "head"},
        "instrument": {"repo_path", "branch", "commit", "production_ancestor"},
        "controller": {"state_root", "evidence_root", "operations_root",
                       "build_root", "max_iterations", "nomination_threshold"},
        "actors": {"wrapper_path", "wrapper_sha256", "critic_path",
                   "critic_sha256", "environment_profile_id"},
        "gpu": {"device_id", "claim_timeout_s", "inference_window_lock",
                "inference_window_lease_id"},
        "source_plan": {"source_builder_id", "evidence_plan_id",
                        "runner_args_id", "experiment_template_registry_id",
                        "experiment_template_registry_sha256",
                        "production_snapshot_id"},
    }
    if any(not isinstance(config.get(key), dict)
           or set(config[key]) != keys for key, keys in exact_nested.items()):
        return None
    max_iterations = config["controller"].get("max_iterations")
    if (isinstance(max_iterations, bool)
            or not isinstance(max_iterations, int)
            or not 1 <= max_iterations <= 1000):
        return None
    inputs = config.get("immutable_inputs")
    if not isinstance(inputs, dict) or set(inputs) != input_keys:
        return None
    if any(not isinstance(value, dict)
           or set(value) != {"path", "sha256"}
           or not isinstance(value.get("path"), str)
           or not Path(value["path"]).is_absolute()
           or ".." in Path(value["path"]).parts
           or not _discovery_sha256(value.get("sha256"))
           for value in inputs.values()):
        return None
    carrier_row = _discovery_v26_input(
        inputs["preauthored_continuation"], bundle,
        max_bytes=2 * 1024 * 1024)
    admission_row = _discovery_v26_input(
        inputs["admission_policy"], bundle, max_bytes=4 * 1024 * 1024)
    if carrier_row is None or admission_row is None:
        return None
    admission = _strict_json_bytes(admission_row[1])
    if (not isinstance(admission, dict)
            or admission.get("schema") !=
               "epyc.autokernel.gpu_load_admission_policy.v2"
            or not isinstance(admission.get("version"), str)
            or not admission["version"]
            or not _discovery_sha256(admission.get("policy_sha256"))
            or admission["policy_sha256"] != _discovery_content_hash({
                key: value for key, value in admission.items()
                if key != "policy_sha256"})):
        return None
    planner_binding = _discovery_v26_input(
        config.get("planner_context"), bundle, max_bytes=512 * 1024)
    if planner_binding is None:
        return None
    planner = _strict_json_bytes(planner_binding[1])
    if (planner is None or set(planner) != _DISCOVERY_V26_PLANNER_KEYS
            or planner.get("schema") !=
            "epyc.autokernel.discovery_planner_context.v4"
            or not _discovery_sha256(planner.get("context_sha256"))
            or planner["context_sha256"] != _discovery_content_hash({
                key: value for key, value in planner.items()
                if key != "context_sha256"})
            or planner.get("model_sha256") != inputs["model"]["sha256"]
            or planner.get("workload_sha256") != inputs["workload"]["sha256"]
            or planner.get("runtime_config_sha256") !=
               inputs["runtime_config"]["sha256"]
            or planner.get("template_registry_sha256") !=
               config["source_plan"]["experiment_template_registry_sha256"]):
        return None
    carrier_raw = carrier_row[1]
    carrier = _strict_json_bytes(carrier_raw)
    carrier_keys = {"schema", "hypothesis_id", "source",
                    "historical_candidate", "patch", "compatibility_bridge",
                    "experiment_intent", "historical_receipts",
                    "correctness_policy", "carrier_sha256"}
    if (carrier is None or set(carrier) != carrier_keys
            or carrier.get("schema") !=
               "epyc.autokernel.preauthored_source_continuation.v1"
            or carrier.get("carrier_sha256") !=
               _discovery_content_hash({
                   key: value for key, value in carrier.items()
                   if key != "carrier_sha256"})
            or planner.get("preauthored_continuation_sha256") !=
               carrier.get("carrier_sha256")
            or not isinstance(carrier.get("patch"), dict)
            or planner.get("preauthored_source_backed_diff_sha256") !=
               carrier["patch"].get("source_backed_sha256")):
        return None
    erratum = None
    carry_forward = None
    frozen_comparator = None
    if q5_erratum_required:
        erratum_row = _discovery_v26_input(
            inputs.get("q5_lds0_attribution_erratum"), bundle,
            max_bytes=2 * 1024 * 1024)
        carry_row = _discovery_v26_input(
            inputs.get("carry_forward"), bundle,
            max_bytes=4 * 1024 * 1024)
        comparator_row = _discovery_v26_input(
            inputs.get("frozen_production_comparator"), bundle,
            max_bytes=2 * 1024 * 1024)
        if (erratum_row is None or carry_row is None or comparator_row is None
                or inputs["q5_lds0_attribution_erratum"].get("sha256") !=
                   _DISCOVERY_V27_ERRATUM_FILE_SHA256):
            return None
        erratum = _strict_json_bytes(erratum_row[1])
        if not _discovery_v27_erratum(erratum):
            return None
        carry_forward = _strict_json_bytes(carry_row[1])
        if not _discovery_v27_carry_forward(carry_forward, erratum):
            return None
        frozen_comparator = _strict_json_bytes(comparator_row[1])
        if not _discovery_v27_frozen_comparator(
                frozen_comparator,
                model_sha256=inputs["model"]["sha256"],
                workload_sha256=inputs["workload"]["sha256"],
                runtime_config_sha256=inputs["runtime_config"]["sha256"]):
            return None
        if (config["production"] != {
                "path": "/mnt/raid0/llm/llama.cpp",
                "branch": "production-consolidated-v9",
                "head": _DISCOVERY_V27_PRODUCTION_COMMIT}
                or config["instrument"].get("production_ancestor") !=
                   _DISCOVERY_V27_PRODUCTION_COMMIT):
            return None
    graph_path = _safe_bundle_path(
        str(Path(config["controller"]["state_root"]) / "deployment-graph.json"),
        bundle)
    graph = None
    graph_file_sha256 = None
    if graph_path is not None and graph_path.exists():
        graph_row = _owned_public_snapshot(graph_path, max_bytes=4 * 1024 * 1024)
        graph_file_sha256 = (hashlib.sha256(graph_row[0]).hexdigest()
                             if graph_row is not None else None)
        graph = (_strict_json_bytes(graph_row[0])
                 if graph_row is not None else None)
    if graph is not None:
        if (set(graph) != graph_keys
                or graph.get("schema") != graph_schema
                or graph.get("authority") !=
                   "nonpromotable_candidate_only_discovery"
                or graph.get("promotion_claim") is not False
                or graph.get("inference_executed") is not False
                or graph.get("config_sha256") != config["config_sha256"]
                or graph.get("graph_sha256") !=
                   _discovery_content_hash({
                       key: value for key, value in graph.items()
                       if key != "graph_sha256"})
                or graph.get("template_registry_sha256") !=
                   planner.get("template_registry_sha256")
                or graph.get("template_surfaces_sha256") !=
                   _discovery_content_hash(graph.get("template_surfaces"))
                or graph.get("portfolio_dispatch_authority_sha256") !=
                   _discovery_content_hash(
                       graph.get("portfolio_dispatch_authority"))):
            return None
        modules = graph.get("execution_modules")
        if (not isinstance(modules, dict)
                or set(modules) != set(
                    _SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26)):
            return None
        for role, logical_path in (
                _SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26.items()):
            binding = modules.get(role)
            if (not isinstance(binding, dict)
                    or set(binding) != {"logical_path", "sha256"}
                    or binding.get("logical_path") != logical_path
                    or not _discovery_sha256(binding.get("sha256"))):
                return None
        preauthored = graph.get("preauthored_continuation")
        portfolio = graph.get("hypothesis_portfolio")
        if (not isinstance(portfolio, dict)
                or set(portfolio) != {
                    "semantic_sha256", "file_sha256",
                    "evidence_manifest_sha256", "contract_sha256"}
                or portfolio.get("semantic_sha256") !=
                   planner.get("hypothesis_portfolio_sha256")
                or portfolio.get("file_sha256") !=
                   inputs["hypothesis_portfolio"]["sha256"]
                or portfolio.get("evidence_manifest_sha256") !=
                   planner.get("hypothesis_evidence_manifest_sha256")
                or portfolio.get("contract_sha256") !=
                   inputs["hypothesis_portfolio_contract"]["sha256"]
                or not _discovery_sha256(graph.get("carry_forward_sha256"))):
            return None
        if (not isinstance(preauthored, dict)
                or set(preauthored) !=
                   _DISCOVERY_V26_PREAUTHORED_GRAPH_KEYS
                or preauthored.get("schema") != carrier.get("schema")
                or preauthored.get("carrier_sha256") !=
                   carrier.get("carrier_sha256")
                or preauthored.get("file_sha256") !=
                   inputs["preauthored_continuation"]["sha256"]
                or preauthored.get("hypothesis_id") !=
                   carrier.get("hypothesis_id")
                or not isinstance(carrier.get("experiment_intent"), dict)
                or preauthored.get("template_id") !=
                   carrier["experiment_intent"].get("template_id")
                or preauthored.get("patch_sha256") !=
                   carrier["patch"].get("sha256")
                or preauthored.get("source_backed_diff_sha256") !=
                   planner.get("preauthored_source_backed_diff_sha256")
                or preauthored.get("historical_evidence_sha256") !=
                   planner.get("preauthored_historical_evidence_sha256")
                or preauthored.get("historical_correctness_authority") !=
                   "provenance_only"
                or preauthored.get("modern_governed_correctness_required")
                   is not True):
            return None
        surfaces = graph.get("template_surfaces")
        dispatch = graph.get("portfolio_dispatch_authority")
        q5_surface = (surfaces.get(preauthored["template_id"])
                      if isinstance(surfaces, dict) else None)
        q5_routes = (dispatch.get(preauthored["hypothesis_id"])
                     if isinstance(dispatch, dict) else None)
        if (not isinstance(q5_surface, dict)
                or set(q5_surface) != {"source_files", "source_symbols",
                                      "change_classes", "dispatch_signatures",
                                      "excluded_signatures"}
                or not isinstance(q5_routes, list)
                or not all(isinstance(row, dict)
                           and set(row) == {
                               "route_id", "calls", "grid", "workgroup",
                               "lds_bytes", "kernel_name"}
                           for row in q5_routes)
                or q5_surface.get("dispatch_signatures") != [{
                    key: row[key] for key in (
                        "route_id", "calls", "grid", "workgroup", "lds_bytes")}
                    for row in q5_routes]
                or not isinstance(q5_surface.get("excluded_signatures"), list)
                or len(q5_surface["excluded_signatures"]) != 1):
            return None
        structural = q5_surface["excluded_signatures"][0]
        route_shape_keys = (
            "route_id", "calls", "grid", "workgroup", "lds_bytes")
        if (not isinstance(structural, dict)
                or set(structural) != {"route_id", "calls", "grid",
                                      "workgroup", "lds_bytes"}
                or any(structural == {
                    key: row[key] for key in route_shape_keys}
                    for row in q5_routes)):
            return None
        if q5_erratum_required:
            source = graph.get("attribution_expectation_erratum")
            if (not isinstance(source, dict)
                    or set(source) != _DISCOVERY_V27_ERRATUM_SOURCE_KEYS
                    or source.get("schema") !=
                       "epyc.autokernel.attribution_expectation_erratum_source.v1"
                    or source.get("erratum_schema") != erratum.get("schema")
                    or source.get("erratum_sha256") !=
                       erratum.get("erratum_sha256")
                    or source.get("file_sha256") !=
                       inputs["q5_lds0_attribution_erratum"]["sha256"]
                    or source.get("operation_key") !=
                       erratum.get("operation_key")
                    or source.get("attribution_refusal_file_sha256") !=
                       erratum.get("attribution_refusal_file_sha256")
                    or source.get("candidate_semantic_sha256") !=
                       erratum.get("candidate_semantic_sha256")):
                return None
            if graph.get("carry_forward_sha256") != carry_forward.get(
                    "carry_forward_sha256"):
                return None
            comparator_source = graph.get("frozen_production_comparator")
            if (not isinstance(comparator_source, dict)
                    or set(comparator_source) !=
                       _DISCOVERY_V27_COMPARATOR_SOURCE_KEYS
                    or comparator_source.get("schema") !=
                       "epyc.autokernel.frozen_production_comparator_source.v1"
                    or comparator_source.get("file_sha256") !=
                       inputs["frozen_production_comparator"]["sha256"]
                    or comparator_source.get("receipt_sha256") !=
                       frozen_comparator.get("receipt_sha256")):
                return None
    module_hashes = (execution_module_sha256
                     if isinstance(execution_module_sha256, dict)
                     else None)
    hashes_frozen = bool(
        graph is not None and module_hashes is not None
        and set(module_hashes) == set(_SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26)
        and all(graph["execution_modules"][role]["sha256"] == digest
                for role, digest in module_hashes.items())
        and graph.get("graph_sha256") == graph_sha256
        and graph_file_sha256 == graph_file_sha256_frozen
        and config.get("config_sha256") ==
            deployment_semantic_sha256
        and config_file_sha256 == deployment_file_sha256
        and isinstance(producer_commit, str)
        and re.fullmatch(r"[0-9a-f]{40}",
                         producer_commit) is not None)
    return {
        "ready": hashes_frozen, "schema": config["schema"],
        "planner_schema": planner["schema"],
        "graph_schema": graph.get("schema") if graph is not None else None,
        "graph_sha256": graph.get("graph_sha256") if graph is not None else None,
        "preauthored": (graph.get("preauthored_continuation")
                        if graph is not None else None),
        "structural_tail": ({
            "exact_validation": True, "reward_excluded": True,
            "route_id": graph["template_surfaces"][
                graph["preauthored_continuation"]["template_id"]
            ]["excluded_signatures"][0]["route_id"],
            "calls": graph["template_surfaces"][
                graph["preauthored_continuation"]["template_id"]
            ]["excluded_signatures"][0]["calls"],
        } if graph is not None else None),
        "producer_commit": (producer_commit if hashes_frozen else None),
        "deployment_identity_sha256": config["config_sha256"],
        "planner_context_file_sha256":
            config["planner_context"]["sha256"],
        "model_sha256": inputs["model"]["sha256"],
        "workload_sha256": inputs["workload"]["sha256"],
        "runtime_config_sha256": inputs["runtime_config"]["sha256"],
        "deployment_workload_file_sha256":
            inputs["workload"]["sha256"],
        "deployment_runtime_file_sha256":
            inputs["runtime_config"]["sha256"],
        "planner_context_sha256": _discovery_content_hash({
            "planner_context_sha256": planner["context_sha256"],
            "admission_policy_sha256": admission["policy_sha256"],
            "admission_policy_version": admission["version"],
            "deployment_identity_sha256": config["config_sha256"],
        }),
        "admission_corpus_sha256": admission["policy_sha256"],
        "admission_corpus_version": admission["version"],
        "max_iterations": config["controller"].get("max_iterations"),
        "state_root": config["controller"].get("state_root"),
        "operations_root": config["controller"].get("operations_root"),
        "build_root": config["controller"].get("build_root"),
        "bundle_root": str(bundle),
        "template_registry_sha256": planner["template_registry_sha256"],
        "hypothesis_portfolio_sha256":
            planner["hypothesis_portfolio_sha256"],
        "carry_forward_sha256": (
            graph.get("carry_forward_sha256") if graph is not None else None),
        "preauthored_continuation_sha256": carrier["carrier_sha256"],
        "preauthored_source_backed_diff_sha256":
            carrier["patch"].get("source_backed_sha256"),
        "historical_commit": (
            carrier.get("historical_candidate", {}).get("commit")
            if isinstance(carrier.get("historical_candidate"), dict) else None),
        **({
            "q5_erratum": erratum,
            "carry_forward": carry_forward,
            "carry_forward_schema": carry_forward["schema"],
            "frozen_production_comparator": frozen_comparator,
        } if q5_erratum_required else {}),
    }


def _discovery_v26_contract(config_path: Path, config: object,
                            bundle: Path) -> dict | None:
    """Validate the immutable v26 product contract."""
    return _discovery_product_contract(
        config_path, config, bundle,
        deployment_schema="epyc.autokernel.discovery_deployment.v5",
        graph_schema="epyc.autokernel.static_discovery_graph.v7",
        input_keys={
            "model", "workload", "runtime_config", "admission_policy",
            "hypothesis_portfolio", "hypothesis_evidence_manifest",
            "hypothesis_portfolio_contract", "preauthored_continuation"},
        graph_keys=_DISCOVERY_V26_GRAPH_KEYS,
        execution_module_sha256=_DISCOVERY_V26_EXECUTION_MODULE_SHA256,
        producer_commit=_DISCOVERY_V26_PRODUCER_COMMIT,
        deployment_semantic_sha256=
            _DISCOVERY_V26_DEPLOYMENT_SEMANTIC_SHA256,
        deployment_file_sha256=_DISCOVERY_V26_DEPLOYMENT_FILE_SHA256,
        graph_sha256=_DISCOVERY_V26_GRAPH_SHA256,
        graph_file_sha256_frozen=_DISCOVERY_V26_GRAPH_FILE_SHA256)


def _discovery_v27_contract(config_path: Path, config: object,
                            bundle: Path) -> dict | None:
    """Validate v27 semantics while final immutable pins remain fail closed."""
    return _discovery_product_contract(
        config_path, config, bundle,
        deployment_schema="epyc.autokernel.discovery_deployment.v6",
        graph_schema="epyc.autokernel.static_discovery_graph.v9",
        input_keys={
            "model", "workload", "runtime_config", "admission_policy",
            "hypothesis_portfolio", "hypothesis_evidence_manifest",
            "hypothesis_portfolio_contract", "preauthored_continuation",
            "q5_lds0_attribution_erratum", "carry_forward",
            "frozen_production_comparator"},
        graph_keys=_DISCOVERY_V27_GRAPH_KEYS,
        execution_module_sha256=_DISCOVERY_V27_EXECUTION_MODULE_SHA256,
        producer_commit=_DISCOVERY_V27_PRODUCER_COMMIT,
        deployment_semantic_sha256=
            _DISCOVERY_V27_DEPLOYMENT_SEMANTIC_SHA256,
        deployment_file_sha256=_DISCOVERY_V27_DEPLOYMENT_FILE_SHA256,
        graph_sha256=_DISCOVERY_V27_GRAPH_SHA256,
        graph_file_sha256_frozen=_DISCOVERY_V27_GRAPH_FILE_SHA256,
        q5_erratum_required=True)


def _discovery_v26_checkpoint(path: Path, *, now: float) -> dict | None:
    """Read v26's fresh single-shard controller journal fail closed."""
    snapshot = _owned_public_snapshot(path, max_bytes=4 * 1024 * 1024)
    if snapshot is None or not snapshot[0] or not snapshot[0].endswith(b"\n"):
        return None
    lines = snapshot[0][:-1].split(b"\n")
    if not lines or any(not line for line in lines):
        return None
    envelope_keys = {
        "journal_schema", "event_id", "seq", "kind", "campaign_id",
        "record_id", "written_at", "payload",
    }
    previous_time = -1.0
    history: list[dict] = []
    for expected_seq, raw in enumerate(lines, 1):
        row = _strict_json_bytes(raw)
        if (row is None or set(row) != envelope_keys
                or raw != _canonical_json_bytes(row)
                or row.get("journal_schema") !=
                   "epyc.autokernel.journal_entry.v1"
                or row.get("kind") != "STOP_STATE"
                or row.get("campaign_id") is not None
                or row.get("record_id") is not None
                or row.get("seq") != expected_seq
                or isinstance(row.get("seq"), bool)):
            return None
        payload = row.get("payload")
        if (not isinstance(payload, dict)
                or set(payload) != {"state", "controller_state_sha256"}
                or payload.get("state") not in
                   _DISCOVERY_V26_CHECKPOINT_STATES
                or not _discovery_sha256(
                    payload.get("controller_state_sha256"))):
            return None
        expected_id = (
            f"akj-{expected_seq:012d}-"
            f"{_discovery_content_hash(payload)[:12]}")
        written_at = _parse_semantic_timestamp(row.get("written_at"))
        if (row.get("event_id") != expected_id or written_at is None
                or written_at < previous_time or written_at > now + 5.0):
            return None
        previous_time = written_at
        history.append({
            "seq": expected_seq, "state": payload["state"],
            "written_at": row["written_at"],
            "controller_state_sha256":
                payload["controller_state_sha256"],
        })
    return {**history[-1], "history": history[-300:]}


_DISCOVERY_V26_TRANSIENT_REQUIRED = {
    "turn", "status", "reason", "refusal_type",
    "scientific_budget_spent", "context_sha256",
    "planner_operation_key",
}
_DISCOVERY_V26_TRANSIENT_PORTFOLIO = {
    "hypothesis_id", "statement", "falsifier", "regime",
    "portfolio_hypothesis_id", "portfolio_binding",
    "portfolio_record_sha256", "portfolio_decision_policy",
}
_DISCOVERY_V26_TRANSIENT_OPTIONAL = {
    "planner_checkpoint_reused", "telemetry_recovery",
    "visibility_degraded", "telemetry_failures",
} | _DISCOVERY_V26_TRANSIENT_PORTFOLIO


def _discovery_v26_planner_transient(row: object, *, turn: int) -> bool:
    if (not isinstance(row, dict)
            or not _DISCOVERY_V26_TRANSIENT_REQUIRED.issubset(row)
            or set(row) - (_DISCOVERY_V26_TRANSIENT_REQUIRED
                           | _DISCOVERY_V26_TRANSIENT_OPTIONAL)
            or row.get("turn") != turn
            or row.get("status") != "planner_transient"
            or row.get("refusal_type") != "planner_provider_transient"
            or row.get("scientific_budget_spent") is not False
            or not isinstance(row.get("reason"), str)
            or not 1 <= len(row["reason"]) <= 4096
            or not _discovery_sha256(row.get("context_sha256"))
            or not _discovery_sha256(row.get("planner_operation_key"))):
        return False
    portfolio_fields = set(row) & _DISCOVERY_V26_TRANSIENT_PORTFOLIO
    if portfolio_fields and portfolio_fields != _DISCOVERY_V26_TRANSIENT_PORTFOLIO:
        return False
    if portfolio_fields:
        binding = row.get("portfolio_binding")
        if (not isinstance(binding, dict)
                or row.get("hypothesis_id") !=
                   row.get("portfolio_hypothesis_id")
                or binding.get("hypothesis_id") != row.get("hypothesis_id")
                or binding.get("statement") != row.get("statement")
                or binding.get("falsifier") != row.get("falsifier")
                or binding.get("regime") != row.get("regime")
                or binding.get("record_sha256") !=
                   row.get("portfolio_record_sha256")
                or binding.get("decision_policy") !=
                   row.get("portfolio_decision_policy")
                or not _discovery_sha256(
                    row.get("portfolio_record_sha256"))):
            return False
    recovery_present = "telemetry_recovery" in row
    if (recovery_present != (row.get("planner_checkpoint_reused") is True)
            or recovery_present and row["telemetry_recovery"] != {
                "schema": "epyc.autokernel.planner_telemetry_recovery.v1",
                "disposition": "resume_checkpoint_and_rederive_refusal"}):
        return False
    failures = row.get("telemetry_failures")
    if "visibility_degraded" in row or failures is not None:
        if (row.get("visibility_degraded") is not True
                or not isinstance(failures, list) or not failures):
            return False
        for failure in failures:
            if (not isinstance(failure, dict)
                    or set(failure) != {
                        "event", "operation_key", "error_type", "error_sha256"}
                    or failure.get("event") not in {
                        "planner_started", "planner_failed"}
                    or failure.get("operation_key") !=
                       row["planner_operation_key"]
                    or not isinstance(failure.get("error_type"), str)
                    or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}",
                                    failure["error_type"]) is None
                    or not _discovery_sha256(failure.get("error_sha256"))):
                return False
    return True


def _discovery_v26_infrastructure_ambiguities(state: dict) -> bool:
    events = state.get("infrastructure_ambiguities", [])
    if not isinstance(events, list):
        return False
    seen: set[str] = set()
    latest: dict[str, int] = {}
    for event in events:
        if (not isinstance(event, dict)
                or set(event) != {
                    "schema", "operation_key", "source_manifest_sha256",
                    "candidate_semantic_sha256", "stage_receipt_path",
                    "stage_receipt_sha256", "reason_sha256", "retry_epoch"}
                or event.get("schema") !=
                   "epyc.autokernel.screen_infrastructure_ambiguity.v1"
                or not all(_discovery_sha256(event.get(key)) for key in (
                    "operation_key", "source_manifest_sha256",
                    "candidate_semantic_sha256", "stage_receipt_sha256",
                    "reason_sha256"))
                or not isinstance(event.get("stage_receipt_path"), str)
                or not event["stage_receipt_path"]
                or isinstance(event.get("retry_epoch"), bool)
                or not isinstance(event.get("retry_epoch"), int)
                or event["retry_epoch"] < 0
                or event["operation_key"] in seen):
            return False
        identity = event["candidate_semantic_sha256"]
        if event["retry_epoch"] != latest.get(identity, -1) + 1:
            return False
        latest[identity] = event["retry_epoch"]
        seen.add(event["operation_key"])
    for label in ("pending", "inflight"):
        holder = state.get(label)
        if holder is None:
            continue
        if not isinstance(holder, dict):
            return False
        row = holder.get("row")
        identity = (row.get("candidate_semantic_sha256")
                    if isinstance(row, dict) else None)
        epoch = holder.get("infrastructure_retry_epoch", 0)
        if (isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0
                or epoch > 0 and not _discovery_sha256(identity)):
            return False
        expected = latest.get(str(identity), -1) + 1
        if ((epoch or identity in latest)
                and holder.get("confirmation") is not True
                and epoch != expected):
            return False
        if (label == "inflight" and epoch
                and holder.get("operation_key") in seen):
            return False
    return True


def _discovery_v26_preauthored_pending(
        pending: dict, state: dict) -> bool:
    row = pending.get("row")
    base = {"row", "candidate", "preauthored_continuation"}
    if not isinstance(row, dict):
        return False
    if pending.get("phase") == "preauthored_ready":
        expected = base | {
            "phase", "context", "context_sha256", "confirmation",
            "parent_authorization"}
        return (set(pending) == expected
                and isinstance(pending.get("context"), dict)
                and pending.get("context_sha256") ==
                    _discovery_controller_state_hash(pending["context"])
                and pending.get("confirmation") is False
                and pending.get("parent_authorization") is None)
    if row.get("status") == "replication_pending":
        expected = base | {"confirmation", "parent_authorization"}
        return (set(pending) == expected
                and pending.get("confirmation") is True
                and isinstance(pending.get("parent_authorization"), dict))
    common = base | {
        "authorization", "confirmation", "parent_authorization",
        "infrastructure_retry_epoch"}
    retry_epoch = pending.get("infrastructure_retry_epoch")
    if (not isinstance(pending.get("authorization"), dict)
            or not isinstance(pending.get("confirmation"), bool)
            or (pending.get("parent_authorization") is not None
                and not isinstance(pending.get("parent_authorization"), dict))
            or isinstance(retry_epoch, bool)
            or not isinstance(retry_epoch, int) or retry_epoch < 0):
        return False
    if row.get("status") == "waiting_resource":
        return (set(pending) == common
                and isinstance(row.get("lease"), dict)
                and _discovery_sha256(row.get("operation_key")))
    if set(pending) != common | {"prior_operation_key"}:
        return False
    prior = pending.get("prior_operation_key")
    ambiguities = state.get("infrastructure_ambiguities")
    event = (ambiguities[-1]
             if isinstance(ambiguities, list) and ambiguities else None)
    return (retry_epoch > 0 and _discovery_sha256(prior)
            and isinstance(event, dict)
            and set(event) == {
                "schema", "operation_key", "source_manifest_sha256",
                "candidate_semantic_sha256", "stage_receipt_path",
                "stage_receipt_sha256", "reason_sha256", "retry_epoch"}
            and event.get("schema") ==
                "epyc.autokernel.screen_infrastructure_ambiguity.v1"
            and event.get("operation_key") == prior
            and event.get("source_manifest_sha256") ==
                row.get("source_manifest_sha256")
            and event.get("candidate_semantic_sha256") ==
                row.get("candidate_semantic_sha256")
            and event.get("retry_epoch") == retry_epoch - 1
            and isinstance(event.get("stage_receipt_path"), str)
            and bool(event["stage_receipt_path"])
            and all(_discovery_sha256(event.get(key)) for key in (
                "stage_receipt_sha256", "reason_sha256")))


def _discovery_v26_iteration(row: object, *, turn: int) -> tuple[bool, bool]:
    """Validate one consuming v26 iteration and return (valid, scientific)."""
    if (not isinstance(row, dict) or row.get("turn") != turn
            or set(row) - _DISCOVERY_V26_ITERATION_KEYS
            or isinstance(row.get("turn"), bool)
            or not isinstance(row.get("status"), str)):
        return False, False
    spent = row.get("scientific_budget_spent")
    has_result = "result_sha256" in row or "evidence" in row
    if spent is True or has_result:
        if (spent is not True
                or not _discovery_sha256(row.get("result_sha256"))
                or not _discovery_sha256(row.get("operation_key"))
                or not _discovery_sha256(
                    row.get("candidate_semantic_sha256"))
                or not _discovery_sha256(row.get("source_manifest_sha256"))
                or not _discovery_sha256(row.get("proposal_sha256"))
                or not _discovery_sha256(row.get("portfolio_record_sha256"))
                or not isinstance(row.get("portfolio_hypothesis_id"), str)
                or row.get("hypothesis_id") !=
                   row.get("portfolio_hypothesis_id")
                or not isinstance(row.get("portfolio_binding"), dict)
                or not isinstance(row.get("portfolio_decision_policy"), dict)
                or not isinstance(row.get("evidence"), dict)):
            return False, False
        evidence = row["evidence"]
        if row["status"] == "correctness_falsified":
            valid = bool(
                row.get("stage") == "correctness"
                and row.get("classification") == "screened_out"
                and row.get("correctness_status") == "failed"
                and _discovery_sha256(row.get("stage_receipt_sha256"))
                and isinstance(row.get("stage_receipt_path"), str)
                and row["stage_receipt_path"]
                and row.get("repetition", 1) in {1, 2}
                and evidence == {
                    "correctness_divergence":
                        row["stage_receipt_sha256"]})
            return valid, valid
        if row["status"] == "attribution_route_falsified":
            valid = bool(
                row.get("stage") == "dispatch_attribution"
                and row.get("classification") == "screened_out"
                and row.get("stage_receipt_sha256") == row["result_sha256"]
                and isinstance(row.get("stage_receipt_path"), str)
                and row["stage_receipt_path"]
                and row.get("repetition", 1) in {1, 2}
                and evidence == {
                    "dispatch_attribution": row["result_sha256"]})
            return valid, valid
        if row["status"] not in {
                "baseline", "candidate", "inconclusive",
                "top_k_replicated_candidate", "screened_out",
                "replicated_but_subadditive"}:
            return False, False
        if (row.get("repetition") not in {1, 2}
                or set(evidence) != {"baseline", "source", "dispatch"}
                or not all(_discovery_sha256(evidence.get(key)) for key in
                           ("baseline", "source", "dispatch"))
                or not isinstance(row.get("effect_fraction"), (int, float))
                or isinstance(row.get("effect_fraction"), bool)
                or not math.isfinite(float(row["effect_fraction"]))
                or not isinstance(row.get("series_effect_fraction"),
                                  (int, float))
                or isinstance(row.get("series_effect_fraction"), bool)
                or not math.isfinite(float(row["series_effect_fraction"]))
                or not _discovery_sha256(row.get("series_key"))
                or not isinstance(row.get("component_series_keys"), list)
                or not all(_discovery_sha256(value)
                           for value in row["component_series_keys"])
                or not isinstance(row.get("target_runtime_executed"), bool)
                or not isinstance(row.get("stages"), list)):
            return False, False
        if ((row["target_runtime_executed"] is True
             and row.get("target_runtime_reason") is not None)
                or (row["target_runtime_executed"] is False
                    and row.get("target_runtime_reason") not in {
                        "nonpositive_exact_duration",
                        "not_required_or_unavailable"})):
            return False, False
        for key in ("exact_attribution_effect_fraction",
                    "target_runtime_effect_fraction"):
            value = row.get(key)
            if (value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value)))):
                return False, False
        return True, True
    non_scientific_statuses = {
        "planner_refused", "critic_revise", "critic_reject",
        "screen_refused", "authoring_refused", "planner_contract_refused",
        "candidate_semantic_repeat_refused", "authorization_refused",
        "correctness_falsified", "measurement_output_refused",
        "portfolio_dnr_refused", "dry_run_authorized",
    }
    if (spent not in {None, False}
            or row["status"] not in non_scientific_statuses):
        return False, False
    if row["status"] == "planner_refused" and not (
            row.get("refusal_type") == "planner_output_refusal"
            and row.get("scientific_budget_spent") is False
            and row.get("telemetry_event") == "planner_refused"
            and row.get("telemetry_status") == "emitted"
            and _discovery_sha256(row.get("planner_operation_key"))):
        return False, False
    return True, False


def _discovery_v26_generic_holder(
        label: str, holder: object, state: dict, contract: dict) -> bool:
    if not isinstance(holder, dict):
        return False
    if label == "planning":
        required = {"phase", "turn", "provider_attempt", "operation_key",
                    "context", "context_sha256", "portfolio_binding",
                    "workspace"}
        optional = {"failure", "telemetry_recovery"}
        if (not required.issubset(holder)
                or set(holder) - (required | optional)
                or holder.get("phase") not in {"intent", "actor_entering"}
                or holder.get("turn") != state.get("next")
                or isinstance(holder.get("provider_attempt"), bool)
                or not isinstance(holder.get("provider_attempt"), int)
                or holder["provider_attempt"] < 0
                or holder["provider_attempt"] !=
                   state.get("planner_provider_attempt", 0)
                or not isinstance(holder.get("context"), dict)
                or holder.get("context_sha256") !=
                   _discovery_controller_state_hash(holder["context"])
                or holder.get("portfolio_binding") is not None
                   and not isinstance(holder.get("portfolio_binding"), dict)):
            return False
        if ("failure" in holder and (
                not isinstance(holder["failure"], dict)
                or set(holder["failure"]) != {"type", "message"}
                or not all(isinstance(holder["failure"].get(key), str)
                           and holder["failure"][key]
                           for key in ("type", "message")))):
            return False
        if ("telemetry_recovery" in holder
                and holder["telemetry_recovery"] != {
                    "schema": "epyc.autokernel.planner_telemetry_recovery.v1",
                    "disposition":
                        "resume_checkpoint_and_rederive_refusal"}):
            return False
        operation = _discovery_controller_state_hash({
            "schema": "epyc.autokernel.planning_operation.v1",
            "turn": holder["turn"],
            "context_sha256": holder["context_sha256"],
            "deployment_identity_sha256":
                contract.get("deployment_identity_sha256"),
            "provider_attempt": holder["provider_attempt"],
        })
        expected_workspace = str(
            Path(str(contract.get("state_root"))) / "planner-operations" /
            str(operation) / "workspace")
        return (holder.get("operation_key") == operation
                and holder.get("workspace") == expected_workspace)
    row = holder.get("row")
    candidate = holder.get("candidate")
    if (not isinstance(row, dict) or not isinstance(candidate, dict)
            or row.get("turn") != state.get("next")):
        return False
    if label == "inflight":
        required = {"operation_key", "row", "candidate", "authorization",
                    "lease", "confirmation", "parent_authorization",
                    "infrastructure_retry_epoch"}
        optional = {"preauthored_continuation", "interruption", "result",
                    "exception"}
        retry = holder.get("infrastructure_retry_epoch")
        return bool(
            required.issubset(holder)
            and not set(holder) - (required | optional)
            and _discovery_sha256(holder.get("operation_key"))
            and row.get("operation_key") == holder["operation_key"]
            and isinstance(holder.get("authorization"), dict)
            and isinstance(holder.get("lease"), dict)
            and isinstance(holder.get("confirmation"), bool)
            and (holder.get("parent_authorization") is None
                 or isinstance(holder.get("parent_authorization"), dict))
            and not isinstance(retry, bool) and isinstance(retry, int)
            and retry >= 0)
    phase = holder.get("phase")
    if phase in {"critic_pending", "critic_complete"}:
        expected = {"phase", "row", "candidate", "context",
                    "context_sha256", "confirmation",
                    "parent_authorization"}
        return bool(
            set(holder) == expected
            and isinstance(holder.get("context"), dict)
            and holder.get("context_sha256") ==
                _discovery_controller_state_hash(holder["context"])
            and holder.get("confirmation") is False
            and holder.get("parent_authorization") is None)
    # Waiting, ambiguity-retry, and S2 use the same exact shape validator as
    # imported Q5 after removing only its source-authority field.
    synthetic = {**holder, "preauthored_continuation": {}}
    return _discovery_v26_preauthored_pending(synthetic, state)


_DISCOVERY_POSTBUILD_PATH_FIELDS = {
    "anchor_build", "candidate_build", "measurement_binary",
    "common_loader_dir", "anchor_loader_dir", "candidate_loader_dir",
    "materialization_receipt", "anchor_source_tree_receipt",
    "candidate_source_tree_receipt", "anchor_correctness_binary",
    "candidate_correctness_binary", "anchor_correctness_capability_receipt",
    "candidate_correctness_capability_receipt", "teardown_receipt",
}
_DISCOVERY_POSTBUILD_SCALAR_FIELDS = {
    "reward_runtime_sha256", "operation_key", "build_key",
    "materialization_sha256", "anchor_source_tree_sha256",
    "candidate_source_tree_sha256", "anchor_correctness_binary_sha256",
    "candidate_correctness_binary_sha256",
    "anchor_correctness_capability_sha256",
    "candidate_correctness_capability_sha256", "teardown_sha256",
}
_DISCOVERY_BUILD_IDENTITY_KEYS = {
    "source_commit", "source_sha256", "binary_sha256",
    "hip_library_sha256", "config_sha256", "linkage_sha256",
}
_DISCOVERY_V27_POLICY_KEYS = {
    "schema", "manifest_sha256", "model_sha256", "workload_sha256",
    "runtime_config_sha256", "candidate_build_identity",
    "anchor_build_identity", "correctness_argv", "correctness_parser_id",
    "correctness_backend", "correctness_op", "expected_correctness_cases",
    "correctness_invocations", "candidate_rocprof_argv",
    "anchor_rocprof_argv", "profiler_trace_schema_id",
    "expected_candidate_profiler_dispatch_rows",
    "expected_anchor_profiler_dispatch_rows", "profiler_transport_policy",
    "attribution_arm_order_seed_sha256", "attribution_arm_order",
    "correctness_inputs", "candidate_rocprof_inputs",
    "anchor_rocprof_inputs", "required_correctness_argv_paths",
    "required_candidate_rocprof_argv_paths",
    "required_anchor_rocprof_argv_paths", "execution_cwd",
    "correctness_environment", "candidate_rocprof_environment",
    "anchor_rocprof_environment", "shared_runtime", "dispatch",
}


def _discovery_v27_build_identity(value: object) -> bool:
    return bool(
        isinstance(value, dict) and set(value) == _DISCOVERY_BUILD_IDENTITY_KEYS
        and isinstance(value.get("source_commit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", value["source_commit"]) is not None
        and all(_discovery_sha256(value.get(key)) for key in (
            "source_sha256", "binary_sha256", "hip_library_sha256",
            "config_sha256", "linkage_sha256")))


def _discovery_v27_argv(value: object) -> bool:
    return bool(
        isinstance(value, list) and value
        and all(isinstance(item, str) and item and "\0" not in item
                and re.search(r"[;|&`\n\r]|\$\(", item) is None
                for item in value)
        and Path(value[0]).is_absolute())


def _discovery_v27_bound_input(value: object) -> bool:
    return bool(
        isinstance(value, dict) and set(value) == {"role", "path", "sha256"}
        and isinstance(value.get("role"), str) and value["role"]
        and isinstance(value.get("path"), str)
        and Path(value["path"]).is_absolute()
        and ".." not in Path(value["path"]).parts
        and _discovery_sha256(value.get("sha256")))


def _discovery_v27_environment(value: object) -> bool:
    if (not isinstance(value, list) or not value
            or any(not isinstance(row, list) or len(row) != 2
                   or any(not isinstance(item, str) or "\0" in item
                          for item in row)
                   or not row[0] for row in value)):
        return False
    return (len({row[0] for row in value}) == len(value)
            and "LD_LIBRARY_PATH" in {row[0] for row in value})


def _discovery_v27_dispatch(value: object) -> bool:
    keys = {
        "candidate_exact", "anchor_exact", "candidate_structural_exact",
        "anchor_structural_exact", "candidate_forbidden", "anchor_forbidden",
        "invariants"}
    if not isinstance(value, dict) or set(value) != keys:
        return False
    exact_keys = {"signature", "kernel_pattern", "calls", "grid",
                  "workgroup", "lds_bytes", "blocks_per_call"}
    simple_keys = {"signature", "kernel_pattern"}
    signatures: list[str] = []
    for name in ("candidate_exact", "anchor_exact",
                 "candidate_structural_exact", "anchor_structural_exact"):
        rows = value[name]
        if (not isinstance(rows, list)
                or name in {"candidate_exact", "anchor_exact"} and not rows):
            return False
        for row in rows:
            if (not isinstance(row, dict) or set(row) != exact_keys
                    or not isinstance(row.get("signature"), str)
                    or not row["signature"]
                    or not isinstance(row.get("kernel_pattern"), str)
                    or any(type(row.get(key)) is not int
                           for key in ("calls", "grid", "workgroup",
                                       "lds_bytes", "blocks_per_call"))
                    or min(row["calls"], row["grid"], row["workgroup"],
                           row["blocks_per_call"]) < 1
                    or row["lds_bytes"] < 0):
                return False
            try:
                re.compile(row["kernel_pattern"])
            except re.error:
                return False
            signatures.append(row["signature"])
    for name in ("candidate_forbidden", "anchor_forbidden", "invariants"):
        rows = value[name]
        if not isinstance(rows, list):
            return False
        for row in rows:
            if (not isinstance(row, dict) or set(row) != simple_keys
                    or not isinstance(row.get("signature"), str)
                    or not row["signature"]
                    or not isinstance(row.get("kernel_pattern"), str)):
                return False
            try:
                re.compile(row["kernel_pattern"])
            except re.error:
                return False
            signatures.append(row["signature"])
    return len(signatures) == len(set(signatures))


def _discovery_v27_execution_policy(value: object, *, manifest_sha256: str,
                                    build: dict, contract: dict) -> bool:
    if (not isinstance(value, dict) or set(value) != _DISCOVERY_V27_POLICY_KEYS
            or value.get("schema") !=
               "epyc.autokernel.gpu_source_execution_policy.v2"
            or value.get("manifest_sha256") != manifest_sha256
            or value.get("model_sha256") != contract.get("model_sha256")
            or value.get("workload_sha256") != contract.get("workload_sha256")
            or value.get("runtime_config_sha256") !=
               contract.get("runtime_config_sha256")
            or value.get("candidate_build_identity") !=
               build.get("candidate_identity")
            or value.get("anchor_build_identity") !=
               build.get("anchor_identity")
            or value.get("correctness_parser_id") !=
               "ak.t0.backend_ops_console/v1"
            or not isinstance(value.get("correctness_backend"), str)
            or not value["correctness_backend"]
            or not isinstance(value.get("correctness_op"), str)
            or not value["correctness_op"]
            or type(value.get("expected_correctness_cases")) is not int
            or value["expected_correctness_cases"] < 1
            or not all(_discovery_v27_argv(value.get(key)) for key in (
                "correctness_argv", "candidate_rocprof_argv",
                "anchor_rocprof_argv"))
            or value.get("attribution_arm_order") not in (
                ["candidate", "anchor"], ["anchor", "candidate"])
            or not _discovery_sha256(
                value.get("attribution_arm_order_seed_sha256"))
            or not _discovery_v27_dispatch(value.get("dispatch"))):
        return False
    trace = value.get("profiler_trace_schema_id")
    candidate_rows = value.get("expected_candidate_profiler_dispatch_rows")
    anchor_rows = value.get("expected_anchor_profiler_dispatch_rows")
    if trace == "rocprof-v3-kernel-trace-csv-v1":
        if (value.get("profiler_transport_policy") !=
                "require-zero-exit-v1"
                or any(type(item) is not int or item < 1
                       for item in (candidate_rows, anchor_rows))):
            return False
    elif trace == "rocprof-v1-timestamps-v1":
        if (value.get("profiler_transport_policy") != "require-zero-exit"
                or candidate_rows is not None or anchor_rows is not None):
            return False
    else:
        return False
    for key in ("correctness_inputs", "candidate_rocprof_inputs",
                "anchor_rocprof_inputs"):
        rows = value.get(key)
        if (not isinstance(rows, list) or not rows
                or any(not _discovery_v27_bound_input(row) for row in rows)
                or not any(row["role"] == "executable"
                           and row["path"] == value[
                               {"correctness_inputs": "correctness_argv",
                                "candidate_rocprof_inputs":
                                    "candidate_rocprof_argv",
                                "anchor_rocprof_inputs":
                                    "anchor_rocprof_argv"}[key]][0]
                           for row in rows)):
            return False
    for key, argv_key in (
            ("required_correctness_argv_paths", "correctness_argv"),
            ("required_candidate_rocprof_argv_paths", "candidate_rocprof_argv"),
            ("required_anchor_rocprof_argv_paths", "anchor_rocprof_argv")):
        paths = value.get(key)
        if (not isinstance(paths, list) or not paths
                or len(paths) != len(set(paths))
                or any(not isinstance(path, str) or not Path(path).is_absolute()
                       or path not in value[argv_key] for path in paths)):
            return False
    if (not isinstance(value.get("execution_cwd"), str)
            or not Path(value["execution_cwd"]).is_absolute()
            or not all(_discovery_v27_environment(value.get(key)) for key in (
                "correctness_environment", "candidate_rocprof_environment",
                "anchor_rocprof_environment"))):
        return False
    shared = value.get("shared_runtime")
    if (shared is not None
            and (not isinstance(shared, dict)
                 or set(shared) != {"measurement_binary", "runtime_receipt",
                                    "anchor_hip_library",
                                    "candidate_hip_library"}
                 or any(not _discovery_v27_bound_input(row)
                        for row in shared.values()))):
        return False
    invocations = value.get("correctness_invocations")
    if not isinstance(invocations, list):
        return False
    invocation_ids: list[str] = []
    base_keys = {"invocation_id", "argv", "backend", "op", "case_set",
                 "expected_cases", "required_cases"}
    for row in invocations:
        if (not isinstance(row, dict)
                or set(row) not in (base_keys,
                                    base_keys | {"environment_overrides"})
                or not isinstance(row.get("invocation_id"), str)
                or not row["invocation_id"]
                or not _discovery_v27_argv(row.get("argv"))
                or not all(isinstance(row.get(key), str) and row[key]
                           for key in ("backend", "op", "case_set"))
                or type(row.get("expected_cases")) is not int
                or row["expected_cases"] < 1
                or not isinstance(row.get("required_cases"), list)
                or "environment_overrides" in row
                and not isinstance(row["environment_overrides"], list)):
            return False
        invocation_ids.append(row["invocation_id"])
    return len(invocation_ids) == len(set(invocation_ids))


def _discovery_v27_build_projection(value: object, contract: dict) -> bool:
    build_keys = ({"candidate_identity", "anchor_identity"}
                  | _DISCOVERY_POSTBUILD_PATH_FIELDS
                  | _DISCOVERY_POSTBUILD_SCALAR_FIELDS)
    if (not isinstance(value, dict) or set(value) != build_keys
            or not _discovery_v27_build_identity(
                value.get("candidate_identity"))
            or not _discovery_v27_build_identity(value.get("anchor_identity"))
            or value.get("candidate_identity") == value.get("anchor_identity")
            or any(not _discovery_sha256(value.get(key))
                   for key in _DISCOVERY_POSTBUILD_SCALAR_FIELDS)):
        return False
    bundle = Path(str(contract.get("bundle_root", "")))
    directory_fields = {
        "anchor_build", "candidate_build", "common_loader_dir",
        "anchor_loader_dir", "candidate_loader_dir"}
    for key in _DISCOVERY_POSTBUILD_PATH_FIELDS:
        path = _safe_bundle_path(value.get(key), bundle)
        if path is None:
            return False
        try:
            if (path.is_symlink()
                    or key in directory_fields and not path.is_dir()
                    or key not in directory_fields and not path.is_file()):
                return False
        except OSError:
            return False
    return True


def _discovery_v27_postbuild_resource_wait(
        pending: object, contract: dict) -> dict | None:
    """Validate the exact controller+adapter checkpoint for a post-build wait."""
    if not isinstance(pending, dict):
        return None
    checkpoint = pending.get("resource_wait")
    checkpoint_keys = {
        "schema", "authority", "promotion_claim", "operation_key",
        "inflight", "inflight_sha256", "wait_receipt",
        "wait_receipt_sha256", "resume_permit", "checkpoint_sha256",
    }
    if (not isinstance(checkpoint, dict) or set(checkpoint) != checkpoint_keys
            or checkpoint.get("schema") !=
               "epyc.autokernel.controller_resource_wait_checkpoint.v1"
            or checkpoint.get("authority") !=
               "nonpromotable_candidate_only_discovery"
            or checkpoint.get("promotion_claim") is not False
            or not _discovery_sha256(checkpoint.get("operation_key"))
            or checkpoint.get("checkpoint_sha256") !=
               _discovery_controller_state_hash({
                   key: value for key, value in checkpoint.items()
                   if key != "checkpoint_sha256"})):
        return None
    operation_key = checkpoint["operation_key"]
    inflight = checkpoint.get("inflight")
    wait = checkpoint.get("wait_receipt")
    permit = checkpoint.get("resume_permit")
    row = pending.get("row")
    if (not isinstance(inflight, dict)
            or checkpoint.get("inflight_sha256") !=
               _discovery_controller_state_hash(inflight)
            or inflight.get("operation_key") != operation_key
            or not isinstance(inflight.get("lease"), dict)
            or inflight["lease"].get("admitted") is not True
            or inflight["lease"].get("operation_key") != operation_key
            or not isinstance(wait, dict)
            or checkpoint.get("wait_receipt_sha256") !=
               _discovery_controller_state_hash(wait)
            or not isinstance(permit, dict)
            or permit != {**inflight["lease"], **wait}
            or not isinstance(row, dict)
            or row != {**inflight.get("row", {}),
                       "status": "waiting_resource", "lease": wait}
            or pending.get("candidate") != inflight.get("candidate")
            or pending.get("authorization") != inflight.get("authorization")
            or pending.get("confirmation") !=
               bool(inflight.get("confirmation"))
            or pending.get("parent_authorization") !=
               inflight.get("parent_authorization")
            or pending.get("infrastructure_retry_epoch") !=
               inflight.get("infrastructure_retry_epoch", 0)):
        return None
    wait_keys = {
        "admitted", "phase", "reason", "device_id", "operation_key",
        "promotion_claim", "stage_receipt_path", "stage_receipt_sha256",
    }
    reason = wait.get("reason")
    if isinstance(reason, str) and reason.startswith("foreign_kfd_"):
        wait_keys.add("foreign_kfd_pids")
    elif "detail" in wait:
        wait_keys.add("detail")
    if (set(wait) != wait_keys or wait.get("admitted") is not False
            or wait.get("phase") != "pre_executor_reservation"
            or wait.get("operation_key") != operation_key
            or wait.get("promotion_claim") is not False
            or reason not in {
                "device_busy", "foreign_kfd_busy",
                "foreign_kfd_inventory_invalid",
                "foreign_kfd_inventory_unreadable"}
            or not isinstance(wait.get("device_id"), str)
            or not wait["device_id"]
            or not _discovery_sha256(wait.get("stage_receipt_sha256"))):
        return None
    if reason.startswith("foreign_kfd_"):
        pids = wait.get("foreign_kfd_pids")
        if (not isinstance(pids, list) or pids != sorted(set(pids))
                or any(type(pid) is not int or pid <= 0 for pid in pids)
                or (reason == "foreign_kfd_busy") != bool(pids)):
            return None
    elif "detail" in wait and not isinstance(wait.get("detail"), str):
        return None
    bundle = Path(str(contract.get("bundle_root", "")))
    operations_root = _safe_bundle_path(contract.get("operations_root"), bundle)
    wait_path = _safe_bundle_path(wait.get("stage_receipt_path"), bundle)
    if (operations_root is None or wait_path is None
            or wait_path.parent != operations_root / operation_key / "resource-waits"
            or re.fullmatch(r"wait-[0-9]{4}\.json", wait_path.name) is None):
        return None
    wait_snapshot = _owned_public_snapshot(wait_path, max_bytes=512 * 1024)
    if (wait_snapshot is None
            or hashlib.sha256(wait_snapshot[0]).hexdigest() !=
               wait["stage_receipt_sha256"]):
        return None
    stage = _strict_json_bytes(wait_snapshot[0])
    stage_keys = {
        "schema", "authority", "promotion_claim", "operation_key",
        "manifest_sha256", "gpu_executor_started", "proof_root_created",
        "runner_plan_created", "runner_output_created", "build_key",
        "materialization_sha256", "contention", "receipt_sha256",
    }
    stage_required = {
        "schema": "epyc.autokernel.gpu_source_resource_wait.v1",
        "authority": "nonpromotable_candidate_only_discovery",
        "promotion_claim": False, "operation_key": operation_key,
        "gpu_executor_started": False, "proof_root_created": False,
        "runner_plan_created": False, "runner_output_created": False,
    }
    contention = {key: value for key, value in wait.items()
                  if key not in {"stage_receipt_path", "stage_receipt_sha256"}}
    candidate = pending.get("candidate")
    manifest_sha256 = (candidate.get("source_manifest_sha256")
                       if isinstance(candidate, dict) else None)
    if (not isinstance(stage, dict) or set(stage) != stage_keys
            or any(stage.get(key) != value
                   for key, value in stage_required.items())
            or not _discovery_sha256(manifest_sha256)
            or stage.get("manifest_sha256") != manifest_sha256
            or stage.get("contention") != contention
            or stage.get("receipt_sha256") !=
               _discovery_controller_state_hash({
                   key: value for key, value in stage.items()
                   if key != "receipt_sha256"})
            or not _discovery_sha256(stage.get("build_key"))
            or not _discovery_sha256(stage.get("materialization_sha256"))):
        return None
    operation_root = operations_root / operation_key
    postbuild_path = operation_root / "postbuild-checkpoint.json"
    postbuild_snapshot = _owned_public_snapshot(
        postbuild_path, max_bytes=4 * 1024 * 1024)
    postbuild = (_strict_json_bytes(postbuild_snapshot[0])
                 if postbuild_snapshot is not None else None)
    postbuild_keys = {
        "schema", "authority", "promotion_claim", "operation_key",
        "manifest_sha256", "build", "receipt_sha256",
    }
    build = postbuild.get("build") if isinstance(postbuild, dict) else None
    if (not isinstance(postbuild, dict) or set(postbuild) != postbuild_keys
            or postbuild.get("schema") !=
               "epyc.autokernel.gpu_source_postbuild_checkpoint.v1"
            or postbuild.get("authority") !=
               "nonpromotable_candidate_only_discovery"
            or postbuild.get("promotion_claim") is not False
            or postbuild.get("operation_key") != operation_key
            or postbuild.get("manifest_sha256") != manifest_sha256
            or postbuild.get("receipt_sha256") !=
               _discovery_controller_state_hash({
                   key: value for key, value in postbuild.items()
                   if key != "receipt_sha256"})
            or not _discovery_v27_build_projection(build, contract)
            or build.get("operation_key") != operation_key
            or build.get("build_key") != stage["build_key"]
            or build.get("materialization_sha256") !=
               stage["materialization_sha256"]
            ):
        return None
    policy_path = operation_root / "evidence-policy.json"
    policy_snapshot = _owned_public_snapshot(
        policy_path, max_bytes=4 * 1024 * 1024)
    policy = (_strict_json_bytes(policy_snapshot[0])
              if policy_snapshot is not None else None)
    if not _discovery_v27_execution_policy(
            policy, manifest_sha256=manifest_sha256,
            build=build, contract=contract):
        return None
    return {
        "kind": "postbuild_resource_wait",
        "operation_key": operation_key, "reason": reason,
        "device_id": wait["device_id"],
        "foreign_kfd_pids": list(wait.get("foreign_kfd_pids", [])),
        "build_key": stage["build_key"],
        "materialization_sha256": stage["materialization_sha256"],
        "completed_builds_preserved": True,
        "evidence_policy_bound": True,
    }


def _discovery_v27_prebuild_resource_wait(
        row: object, contract: dict) -> dict | None:
    """Admit only the exact legacy pre-build lease with no post-build traces."""
    if not isinstance(row, dict):
        return None
    operation_key = row.get("operation_key")
    lease = row.get("lease")
    common = {
        "admitted", "phase", "reason", "operation_key", "promotion_claim",
        "mode", "device_id", "inference_window_lock", "model_sha256",
        "load_admission"}
    if not isinstance(lease, dict):
        return None
    reason = lease.get("reason")
    keys = set(common)
    if isinstance(reason, str) and reason.startswith("foreign_kfd_"):
        keys.add("foreign_kfd_pids")
    else:
        keys.add("detail")
    if (set(lease) != keys or not _discovery_sha256(operation_key)
            or lease.get("operation_key") != operation_key
            or lease.get("admitted") is not False
            or lease.get("phase") != "prebuild_probe"
            or lease.get("promotion_claim") is not False
            or lease.get("mode") not in {"cold_overlap", "cold_serialized"}
            or reason not in {
                "device_busy", "foreign_kfd_busy",
                "foreign_kfd_inventory_invalid",
                "foreign_kfd_inventory_unreadable"}
            or not isinstance(lease.get("device_id"), str)
            or not lease["device_id"]
            or not isinstance(lease.get("inference_window_lock"), str)
            or not lease["inference_window_lock"]
            or lease.get("model_sha256") != contract.get("model_sha256")
            or not isinstance(lease.get("load_admission"), dict)
            or not lease["load_admission"]):
        return None
    if reason.startswith("foreign_kfd_"):
        pids = lease.get("foreign_kfd_pids")
        if (not isinstance(pids, list) or pids != sorted(set(pids))
                or any(type(pid) is not int or pid <= 0 for pid in pids)
                or (reason == "foreign_kfd_busy") != bool(pids)):
            return None
    elif not isinstance(lease.get("detail"), str):
        return None
    bundle = Path(str(contract.get("bundle_root", "")))
    operations_root = _safe_bundle_path(contract.get("operations_root"), bundle)
    if operations_root is None:
        return None
    operation_root = operations_root / operation_key
    forbidden = (
        operation_root / "postbuild-checkpoint.json",
        operation_root / "evidence-policy.json",
        operation_root / "resource-waits")
    try:
        if any(path.exists() or path.is_symlink() for path in forbidden):
            return None
    except OSError:
        return None
    return {
        "kind": "prebuild_resource_wait", "operation_key": operation_key,
        "reason": reason, "completed_builds_preserved": False,
        "evidence_policy_bound": False,
    }


_DISCOVERY_V27_CUMULATIVE_SCHEMA = (
    "epyc.autokernel.cumulative_performance.v2")
_DISCOVERY_V27_PRODUCTION_COMMIT = (
    "0db32c06e3e550065b78311a6031ef3dd2c4f27c")
_DISCOVERY_V27_COMPARATOR_KEYS = {
    "schema", "branch", "commit", "build_identity",
    "build_receipt_sha256", "linkage_receipt_sha256",
    "runtime_receipt_sha256", "runtime_snapshot_sha256",
    "measurement_receipt_sha256",
    "model_sha256", "workload_sha256", "runtime_config_sha256",
    "observed_workload_sha256", "observed_runtime_config_sha256",
    "frame_sha256", "graphs_mode", "metric", "direction",
    "measurement_protocol_sha256",
    "receipt_sha256"}

_DISCOVERY_V27_MEASURED_WORKLOAD = {
    "backend": "llama_gpu", "recipe": "tg128-ngl99",
    "n_prompt": 0, "n_gen": 128,
}
_DISCOVERY_V27_MEASURED_RUNTIME = {
    "n_threads": 8, "n_batch": 512, "n_ubatch": 512,
    "use_mmap": True, "no_op_offload": 0,
    "split_mode": "layer", "no_kv_offload": False,
    "poll": 50, "n_prompt": 0, "n_gen": 128,
    "flash_attn": 1,
}


def _discovery_v27_measurement_binding(
        *, model_sha256: str, build_identity: object, graphs_mode: str,
        arm: str, factor_name: str) -> tuple[str, str] | None:
    """Recompute measured protocol/frame identities in their own namespace."""
    if (not _discovery_sha256(model_sha256)
            or not _discovery_v27_build_identity(build_identity)
            or graphs_mode not in {"off", "on"}
            or arm not in {"anchor", "candidate"}
            or factor_name not in {"source_patch", "cumulative_production"}):
        return None
    protocol = {
        **_DISCOVERY_V27_MEASURED_WORKLOAD,
        "model_sha256": model_sha256,
        "metric": "decode_tokens_per_s",
        "metric_direction": "higher_better",
        "cpu_list": "184-191", "device": "AMD Instinct MI210",
        "architecture": "gfx90a",
        "runtime_config_sha256": _discovery_content_hash(
            _DISCOVERY_V27_MEASURED_RUNTIME),
        "graphs_mode": graphs_mode,
        "candidate_invocations": 9, "candidate_processes": 1,
    }
    protocol_sha256 = _discovery_content_hash(protocol)
    frame_sha256 = _discovery_content_hash({
        "schema": "epyc.autokernel.measurement_arm_frame.v1",
        "arm": arm, "protocol": protocol,
        "source_commit": build_identity["source_commit"],
        "build_identity": build_identity,
        "factor_name": factor_name,
    })
    if protocol_sha256 is None or frame_sha256 is None:
        return None
    return protocol_sha256, frame_sha256


def _discovery_v27_frozen_comparator(
        value: object, *, model_sha256: str, workload_sha256: str,
        runtime_config_sha256: str) -> bool:
    expected = (
        _discovery_v27_measurement_binding(
            model_sha256=model_sha256,
            build_identity=value.get("build_identity"), graphs_mode="on",
            arm="anchor", factor_name="cumulative_production")
        if isinstance(value, dict) else None)
    return bool(
        expected is not None
        and isinstance(value, dict)
        and set(value) == _DISCOVERY_V27_COMPARATOR_KEYS
        and value.get("schema") ==
            "epyc.autokernel.frozen_production_comparator.v2"
        and value.get("branch") == "production-consolidated-v9"
        and value.get("commit") == _DISCOVERY_V27_PRODUCTION_COMMIT
        and _discovery_v27_build_identity(value.get("build_identity"))
        and value["build_identity"].get("source_commit") ==
            _DISCOVERY_V27_PRODUCTION_COMMIT
        and all(_discovery_sha256(value.get(key)) for key in (
            "build_receipt_sha256", "linkage_receipt_sha256",
            "runtime_receipt_sha256", "runtime_snapshot_sha256",
            "measurement_receipt_sha256",
            "model_sha256", "workload_sha256", "runtime_config_sha256",
            "observed_workload_sha256",
            "observed_runtime_config_sha256",
            "frame_sha256",
            "measurement_protocol_sha256"))
        and value.get("model_sha256") == model_sha256
        and value.get("workload_sha256") == workload_sha256
        and value.get("runtime_config_sha256") == runtime_config_sha256
        and value.get("observed_workload_sha256") ==
            _discovery_content_hash(_DISCOVERY_V27_MEASURED_WORKLOAD)
        and value.get("observed_runtime_config_sha256") ==
            _discovery_content_hash(_DISCOVERY_V27_MEASURED_RUNTIME)
        and value.get("measurement_protocol_sha256") == expected[0]
        and value.get("frame_sha256") == expected[1]
        and value.get("graphs_mode") == "graphs_on"
        and value.get("metric") == "tokens_per_second"
        and value.get("direction") == "higher_is_better"
        and value.get("receipt_sha256") == _discovery_content_hash({
            key: item for key, item in value.items()
            if key != "receipt_sha256"}))


def _discovery_v27_performance_unavailable(reason: str) -> dict:
    return {
        "available": False,
        "headline": "Cumulative performance vs frozen production unavailable",
        "cumulative_vs_frozen_production": None,
        "incremental_vs_prior_stack": None,
        "promotion_eligible": False,
        "promotion_reason": reason,
    }


def _discovery_v27_composition_build_binding(value: object) -> bool:
    if (not isinstance(value, dict) or set(value) != {
            "patch_set_sha256", "source_materialization_receipt_sha256",
            "build_identity", "build_identity_sha256"}
            or not _discovery_sha256(value.get("patch_set_sha256"))
            or not _discovery_sha256(
                value.get("source_materialization_receipt_sha256"))
            or not _discovery_v27_build_identity(value.get("build_identity"))):
        return False
    return value.get("build_identity_sha256") == _discovery_content_hash(
        value["build_identity"])


def _discovery_v27_composition_build_pair(value: object) -> bool:
    if (not isinstance(value, dict) or set(value) != {
            "schema", "operation_key", "plan_sha256", "anchor", "candidate",
            "pair_sha256"}
            or value.get("schema") !=
               "epyc.autokernel.cumulative_build_pair.v1"
            or not _discovery_sha256(value.get("operation_key"))
            or not _discovery_sha256(value.get("plan_sha256"))
            or not _discovery_v27_composition_build_binding(
                value.get("anchor"))
            or not _discovery_v27_composition_build_binding(
                value.get("candidate"))
            or value["anchor"]["build_identity_sha256"] ==
               value["candidate"]["build_identity_sha256"]):
        return False
    return value.get("pair_sha256") == _discovery_content_hash({
        key: item for key, item in value.items() if key != "pair_sha256"})


def _discovery_v27_isolated_replication(value: object) -> bool:
    keys = {
        "result_sha256", "series_key", "build_identity_sha256",
        "correctness_receipt_sha256", "attribution_receipt_sha256",
        "graphs_off_receipt_sha256", "graphs_on_receipt_sha256",
        "effect_fraction",
    }
    return bool(
        isinstance(value, dict) and set(value) == keys
        and all(_discovery_sha256(value.get(key)) for key in keys - {
            "effect_fraction"})
        and not isinstance(value.get("effect_fraction"), bool)
        and isinstance(value.get("effect_fraction"), (int, float))
        and math.isfinite(float(value["effect_fraction"]))
        and float(value["effect_fraction"]) > 0)


_DISCOVERY_V27_PATCH_HUNK = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?P<context>.*)$")
_DISCOVERY_V27_PATCH_SYMBOL = re.compile(
    r"(?P<name>[A-Za-z_~][A-Za-z0-9_:~<>]*)\s*\([^()]*\)\s*"
    r"(?:const\s*)?(?:\{|$)")
_DISCOVERY_V27_PATCH_TRUNCATED_SYMBOL = re.compile(
    r"(?P<name>[A-Za-z_~][A-Za-z0-9_:~<>]*)\s*\(\s*$")
_DISCOVERY_V27_PATCH_PLAIN_SYMBOL = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_:~<>]*$")
_DISCOVERY_V27_PATCH_CONTROLS = frozenset({
    "if", "for", "while", "switch", "catch"})
_DISCOVERY_V27_PATCH_PHASE_PROBE = re.compile(
    r"\b(?:hip|cuda)StreamIsCapturing\s*\("
    r"|\btorch\.cuda\.is_current_stream_capturing\s*\("
    r"|\b(?:correctness|warmup|timing|benchmark)_phase\b", re.IGNORECASE)
_DISCOVERY_V27_PATCH_PHASE_COUNTER = re.compile(
    r"\b(?:static\s+)?(?:std::atomic\s*<\s*(?:u?int\w*|size_t)\s*>|"
    r"(?:u?int\w*|size_t|long))\s+"
    r"((?=[A-Za-z_]\w*\b)(?=\w*(?:call|invocation|iteration|warmup|phase|round))"
    r"\w+)\b", re.IGNORECASE)
_DISCOVERY_V27_PATCH_CONTROL_FLOW = re.compile(
    r"\b(?:if|while|switch)\s*\(|\?.*:")
_DISCOVERY_V27_PATCH_CAPTURE_REPLAY = re.compile(
    r"(?:@\s*)?torch\.compile\b|\btorch\.cuda\.(?:CUDAGraph|graph)\b"
    r"|\b(?:cuda|hip)Graph(?:Create|Instantiate|Launch|ExecUpdate|Add\w*)\s*\("
    r"|\b(?:cuda|hip)StreamBeginCapture\s*\(", re.IGNORECASE)
_DISCOVERY_V27_PATCH_CONTENT_SPECIALIZATION = re.compile(
    r"\b(?:tensor|input|content)[_-]?(?:hash|checksum|fingerprint)\b"
    r"|\b(?:hash|checksum|fingerprint)[_-]?(?:tensor|input|content)\b"
    r"|\b(?:cache|memo)\s*\[[^\]\n]*(?:checksum|fingerprint|"
    r"\.sum\s*\(\s*\)\s*\.item|memcmp\s*\(|sha256|xxhash)", re.IGNORECASE)


def _discovery_v27_patch_path(value: object) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return None
    path = PurePosixPath(value)
    if (path.is_absolute() or value != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)
            or value.startswith("-")):
        return None
    return path.as_posix()


def _discovery_v27_patch_symbol(context: str, body: list[str]) -> str:
    normalized = context.strip()
    if (_DISCOVERY_V27_PATCH_PLAIN_SYMBOL.fullmatch(normalized)
            and normalized not in _DISCOVERY_V27_PATCH_CONTROLS):
        header_symbol = normalized
    else:
        matches = list(_DISCOVERY_V27_PATCH_SYMBOL.finditer(normalized))
        match = (matches[-1] if matches else
                 _DISCOVERY_V27_PATCH_TRUNCATED_SYMBOL.search(normalized))
        header_symbol = (
            match.group("name") if match is not None
            and match.group("name") not in _DISCOVERY_V27_PATCH_CONTROLS
            else "<file-scope>")
    body_symbols: list[str] = []
    for line in body:
        if not line.startswith(" "):
            break
        normalized = line[1:].strip()
        match = _DISCOVERY_V27_PATCH_TRUNCATED_SYMBOL.search(normalized)
        if match is None or match.group("name") in _DISCOVERY_V27_PATCH_CONTROLS:
            continue
        prefix = normalized[:match.start("name")].strip()
        if (not prefix or prefix in _DISCOVERY_V27_PATCH_CONTROLS
                or any(char in prefix for char in "=;{}")):
            continue
        symbol = match.group("name")
        if symbol not in body_symbols:
            body_symbols.append(symbol)
    if len(body_symbols) == 1:
        return body_symbols[0]
    if header_symbol in body_symbols:
        return header_symbol
    return "<file-scope>" if body_symbols else header_symbol


def _discovery_v27_patch_reward_safe(
        added: list[tuple[str, int, str]]) -> bool:
    phase_variables: dict[str, tuple[str, int]] = {}
    for path, line, text in added:
        code = text.split("//", 1)[0]
        if (_DISCOVERY_V27_PATCH_PHASE_PROBE.search(code)
                or _DISCOVERY_V27_PATCH_CAPTURE_REPLAY.search(code)
                or _DISCOVERY_V27_PATCH_CONTENT_SPECIALIZATION.search(code)):
            return False
        counter = _DISCOVERY_V27_PATCH_PHASE_COUNTER.search(code)
        if counter is not None:
            phase_variables[counter.group(1)] = (path, line)
    for _path, _line, text in added:
        code = text.split("//", 1)[0]
        if not _DISCOVERY_V27_PATCH_CONTROL_FLOW.search(code):
            continue
        if any(re.search(rf"\b{re.escape(variable)}\b", code)
               for variable in phase_variables):
            return False
    return True


def _discovery_v27_patch_projection(patch: bytes) -> dict | None:
    try:
        text = patch.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None
    if not text.endswith("\n") or "\x00" in text:
        return None
    lines = text.splitlines()
    paths: set[str] = set()
    symbols: dict[str, set[str]] = {}
    deleted: dict[str, set[int]] = {}
    inserted: dict[str, set[int]] = {}
    added: list[tuple[str, int, str]] = []
    current_path: str | None = None
    current_old_marker: str | None = None
    current_marker_path: str | None = None
    current_section_has_hunk = False
    saw_hunk = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git a/"):
            if (current_path is not None
                    and (current_marker_path != current_path
                         or not current_section_has_hunk)):
                return None
            match = re.fullmatch(r"diff --git a/(.+) b/(.+)", line)
            if match is None or match.group(1) != match.group(2):
                return None
            current_path = _discovery_v27_patch_path(match.group(2))
            if current_path is None or current_path in paths:
                return None
            paths.add(current_path)
            symbols.setdefault(current_path, set())
            deleted.setdefault(current_path, set())
            inserted.setdefault(current_path, set())
            current_old_marker = None
            current_marker_path = None
            current_section_has_hunk = False
            i += 1
            continue
        if line.startswith(("rename from ", "rename to ",
                            "copy from ", "copy to ", "Binary files ")) \
                or line == "GIT binary patch":
            return None
        mode = re.fullmatch(
            r"(?:old|new|deleted file|new file) mode (\d+)", line)
        if mode is not None:
            if (current_path is None or current_old_marker is not None
                    or current_marker_path is not None
                    or current_section_has_hunk
                    or mode.group(1) not in {"100644", "100755"}):
                return None
            i += 1
            continue
        if line.startswith("index "):
            if (current_path is None or current_old_marker is not None
                    or current_marker_path is not None
                    or current_section_has_hunk
                    or re.fullmatch(
                        r"index [0-9a-f]+\.\.[0-9a-f]+(?: [0-7]+)?",
                        line) is None):
                return None
            i += 1
            continue
        if line.startswith("--- "):
            if (current_path is None or current_old_marker is not None
                    or current_marker_path is not None
                    or current_section_has_hunk):
                return None
            marker = line[4:].split("\t", 1)[0]
            if marker == "/dev/null":
                current_old_marker = marker
            else:
                old_path = marker[2:] if marker.startswith("a/") else marker
                if _discovery_v27_patch_path(old_path) != current_path:
                    return None
                current_old_marker = current_path
            i += 1
            continue
        if line.startswith("+++ "):
            if (current_path is None or current_old_marker is None
                    or current_marker_path is not None
                    or current_section_has_hunk):
                return None
            marker = line[4:].split("\t", 1)[0]
            if marker == "/dev/null":
                if current_old_marker == "/dev/null":
                    return None
            else:
                new_path = marker[2:] if marker.startswith("b/") else marker
                if _discovery_v27_patch_path(new_path) != current_path:
                    return None
            current_marker_path = current_path
            i += 1
            continue
        hunk = _DISCOVERY_V27_PATCH_HUNK.match(line)
        if hunk is not None:
            if current_path is None or current_marker_path != current_path:
                return None
            old_line = int(hunk.group(1))
            old_count = int(hunk.group(2) or "1")
            new_line = int(hunk.group(3))
            new_count = int(hunk.group(4) or "1")
            seen_old = seen_new = 0
            body: list[str] = []
            i += 1
            while (i < len(lines)
                   and not lines[i].startswith("diff --git a/")
                   and _DISCOVERY_V27_PATCH_HUNK.match(lines[i]) is None):
                row = lines[i]
                if row == "\\ No newline at end of file":
                    if not body or body[-1].startswith("\\") \
                            or not body[-1].startswith(("+", "-")):
                        return None
                    body.append(row)
                    i += 1
                    continue
                if row.startswith("+"):
                    inserted[current_path].add(old_line)
                    added.append((current_path, new_line, row[1:]))
                    seen_new += 1
                    new_line += 1
                elif row.startswith("-"):
                    deleted[current_path].add(old_line)
                    seen_old += 1
                    old_line += 1
                elif row.startswith(" "):
                    seen_old += 1
                    seen_new += 1
                    old_line += 1
                    new_line += 1
                elif row == "":
                    seen_old += 1
                    seen_new += 1
                    new_line += 1
                else:
                    return None
                body.append(row)
                i += 1
            if seen_old != old_count or seen_new != new_count:
                return None
            symbols[current_path].add(_discovery_v27_patch_symbol(
                hunk.group("context").strip(), body))
            saw_hunk = True
            current_section_has_hunk = True
            continue
        return None
    if (not saw_hunk or not paths
            or current_path is None
            or current_marker_path != current_path
            or not current_section_has_hunk
            or any(not symbols.get(path) for path in paths)
            or not _discovery_v27_patch_reward_safe(added)):
        return None
    return {
        "text": text,
        "paths": tuple(sorted(paths)),
        "symbols": {
            path: tuple(sorted(symbols[path])) for path in sorted(paths)},
        "footprint": {
            path: (frozenset(deleted[path]), frozenset(inserted[path]))
            for path in sorted(paths)},
    }


def _discovery_v27_source_manifest(value: object) -> dict | None:
    keys = {
        "schema", "campaign_id", "proposal_id", "candidate_id",
        "source_tree", "production_base_commit", "instrument_commit",
        "change_class", "declared_files", "declared_symbols",
        "mechanism_id", "patch_sha256", "patch_encoding", "patch_base64",
    }
    if (not isinstance(value, dict) or set(value) != keys
            or value.get("schema") != "epyc.autokernel.source-patch.v1"
            or not isinstance(value.get("campaign_id"), str)
            or not value["campaign_id"].startswith("ak-")
            or not isinstance(value.get("proposal_id"), str)
            or not value["proposal_id"].startswith("akp-")
            or not isinstance(value.get("candidate_id"), str)
            or not value["candidate_id"].startswith("akc-")
            or value.get("source_tree") != "llama.cpp"
            or any(re.fullmatch(r"[0-9a-f]{40}", str(value.get(key))) is None
                   for key in ("production_base_commit", "instrument_commit"))
            or value.get("change_class") not in {
                "dispatcher", "arithmetic", "layout", "fusion",
                "moe_scheduling", "recurrent", "scheduler_policy",
                "oracle_port", "core_header"}
            or not isinstance(value.get("mechanism_id"), str)
            or not value["mechanism_id"]
            or value.get("patch_encoding") != "base64"
            or not _discovery_sha256(value.get("patch_sha256"))):
        return None
    files = value.get("declared_files")
    symbols = value.get("declared_symbols")
    if (not isinstance(files, list) or not files
            or files != sorted(set(files))
            or any(not isinstance(path, str) or not path
                   or path.startswith(("/", "-"))
                   or "\\" in path or "\x00" in path
                   or any(part in {"", ".", ".."}
                          for part in Path(path).parts)
                   for path in files)
            or not isinstance(symbols, dict) or set(symbols) != set(files)):
        return None
    for path in files:
        rows = symbols.get(path)
        if (not isinstance(rows, list) or not rows
                or rows != sorted(set(rows))
                or any(symbol != "<file-scope>" and (
                    not isinstance(symbol, str)
                    or _DISCOVERY_V27_PATCH_PLAIN_SYMBOL.match(symbol) is None)
                    for symbol in rows)):
            return None
    try:
        patch = base64.b64decode(value.get("patch_base64"), validate=True)
    except (TypeError, ValueError):
        return None
    projection = _discovery_v27_patch_projection(patch)
    if (hashlib.sha256(patch).hexdigest() != value["patch_sha256"]
            or projection is None
            or projection["paths"] != tuple(files)
            or any(set(projection["symbols"][path]) - set(symbols[path])
                   for path in files)):
        return None
    return {
        **projection,
        "manifest_sha256": _discovery_content_hash(value),
    }


def _discovery_v27_replicated_lever(value: object) -> bool:
    keys = {
        "schema", "hypothesis_id", "cross_campaign_candidate_sha256",
        "manifest", "manifest_sha256", "isolated_disposition",
        "replications", "lever_sha256",
    }
    if (not isinstance(value, dict) or set(value) != keys
            or value.get("schema") !=
               "epyc.autokernel.replicated_positive_lever.v2"
            or not isinstance(value.get("hypothesis_id"), str)
            or not value["hypothesis_id"].startswith("akh-")
            or not _discovery_sha256(
                value.get("cross_campaign_candidate_sha256"))
            or value.get("isolated_disposition") !=
               "top_k_replicated_candidate"
            or not _discovery_sha256(value.get("manifest_sha256"))
            or not _discovery_sha256(value.get("lever_sha256"))):
        return False
    manifest = _discovery_v27_source_manifest(value.get("manifest"))
    rows = value.get("replications")
    if (manifest is None
            or value["manifest_sha256"] != manifest["manifest_sha256"]
            or not isinstance(rows, list) or len(rows) < 2
            or not all(_discovery_v27_isolated_replication(row)
                       for row in rows)
            or len({row["result_sha256"] for row in rows}) != len(rows)
            or len({row["series_key"] for row in rows}) != 1
            or len({row["build_identity_sha256"] for row in rows}) != 1):
        return False
    return value["lever_sha256"] == _discovery_content_hash({
        key: item for key, item in value.items() if key != "lever_sha256"})


def _discovery_v27_levers_compatible(accepted: list[dict]) -> bool:
    projections = [
        _discovery_v27_source_manifest(row.get("manifest"))
        for row in accepted]
    if any(projection is None for projection in projections):
        return False
    for index, proposed in enumerate(accepted):
        proposed_projection = projections[index]
        for old_index in range(index):
            existing = accepted[old_index]
            existing_projection = projections[old_index]
            if (existing["cross_campaign_candidate_sha256"] ==
                    proposed["cross_campaign_candidate_sha256"]
                    or existing["manifest_sha256"] ==
                       proposed["manifest_sha256"]):
                return False
            shared = set(existing["manifest"]["declared_files"]) & set(
                proposed["manifest"]["declared_files"])
            for path in shared:
                old_symbols = set(
                    existing["manifest"]["declared_symbols"][path])
                new_symbols = set(
                    proposed["manifest"]["declared_symbols"][path])
                if ("<file-scope>" in old_symbols
                        or "<file-scope>" in new_symbols
                        or old_symbols & new_symbols):
                    return False
                old_deleted, old_inserted = existing_projection[
                    "footprint"][path]
                new_deleted, new_inserted = proposed_projection[
                    "footprint"][path]
                if (old_deleted & new_deleted
                        or old_deleted & new_inserted
                        or old_inserted & new_deleted
                        or old_inserted & new_inserted):
                    return False
    return True


def _discovery_v27_composition_authority(value: object) -> bool:
    keys = {
        "schema", "campaign_id", "production_base_commit",
        "instrument_commit", "ordered_patch_set_sha256", "accepted",
        "authority_sha256",
    }
    if (not isinstance(value, dict) or set(value) != keys
            or value.get("schema") !=
               "epyc.autokernel.cumulative_composition_authority.v1"
            or not isinstance(value.get("campaign_id"), str)
            or not value["campaign_id"].startswith("ak-")
            or any(re.fullmatch(r"[0-9a-f]{40}", str(value.get(key))) is None
                   for key in ("production_base_commit", "instrument_commit"))
            or not isinstance(value.get("accepted"), list)
            or not all(_discovery_v27_replicated_lever(row)
                       for row in value["accepted"])
            or not _discovery_sha256(value.get("ordered_patch_set_sha256"))
            or not _discovery_sha256(value.get("authority_sha256"))):
        return False
    accepted = value["accepted"]
    if (any(row["manifest"].get("campaign_id") != value["campaign_id"]
            or row["manifest"].get("production_base_commit") !=
               value["production_base_commit"]
            or row["manifest"].get("instrument_commit") !=
               value["instrument_commit"] for row in accepted)
            or len({row["cross_campaign_candidate_sha256"]
                    for row in accepted}) != len(accepted)
            or len({row["manifest_sha256"] for row in accepted}) !=
               len(accepted)
            or not _discovery_v27_levers_compatible(accepted)):
        return False
    patch_set = _discovery_content_hash({
        "schema": "epyc.autokernel.ordered_patch_set.v1",
        "campaign_id": value["campaign_id"],
        "production_base_commit": value["production_base_commit"],
        "instrument_commit": value["instrument_commit"],
        "lever_sha256s": [row["lever_sha256"] for row in accepted],
        "source_manifest_sha256s": [
            row["manifest_sha256"] for row in accepted],
    })
    return bool(
        value["ordered_patch_set_sha256"] == patch_set
        and value["authority_sha256"] == _discovery_content_hash({
            key: item for key, item in value.items()
            if key != "authority_sha256"}))


def _discovery_v27_composition_plan(value: object) -> bool:
    keys = {
        "schema", "attempt_id", "operation_key", "anchor_authority",
        "candidate_authority", "anchor_patch_set_sha256",
        "candidate_patch_set_sha256", "ordered_component_lever_sha256s",
        "ordered_source_manifest_sha256s", "new_lever_sha256",
        "isolated_result_sha256s", "dnr", "plan_sha256",
    }
    if (not isinstance(value, dict) or set(value) != keys
            or value.get("schema") !=
               "epyc.autokernel.cumulative_composition_plan.v1"
            or any(not _discovery_sha256(value.get(key)) for key in (
                "attempt_id", "operation_key", "anchor_patch_set_sha256",
                "candidate_patch_set_sha256", "new_lever_sha256",
                "plan_sha256"))
            or not _discovery_v27_composition_authority(
                value.get("anchor_authority"))
            or not _discovery_v27_composition_authority(
                value.get("candidate_authority"))):
        return False
    anchor = value["anchor_authority"]
    candidate = value["candidate_authority"]
    accepted = candidate["accepted"]
    dnr = value.get("dnr")
    dnr_keys = {
        "schema", "campaign_id", "anchor_patch_set_sha256",
        "candidate_patch_set_sha256",
        "proposed_cross_campaign_candidate_sha256", "registry_sha256",
        "checked_cross_campaign_candidate_sha256s", "outcome",
        "receipt_sha256",
    }
    if (candidate["campaign_id"] != anchor["campaign_id"]
            or candidate["production_base_commit"] !=
               anchor["production_base_commit"]
            or candidate["instrument_commit"] != anchor["instrument_commit"]
            or len(accepted) != len(anchor["accepted"]) + 1
            or accepted[:-1] != anchor["accepted"]
            or not isinstance(dnr, dict) or set(dnr) != dnr_keys
            or dnr.get("schema") != "epyc.autokernel.composition_dnr.v1"
            or dnr.get("campaign_id") != anchor["campaign_id"]
            or dnr.get("anchor_patch_set_sha256") !=
               anchor["ordered_patch_set_sha256"]
            or dnr.get("candidate_patch_set_sha256") !=
               candidate["ordered_patch_set_sha256"]
            or dnr.get("proposed_cross_campaign_candidate_sha256") !=
               accepted[-1]["cross_campaign_candidate_sha256"]
            or not _discovery_sha256(dnr.get("registry_sha256"))
            or dnr.get("outcome") != "PASS"
            or not isinstance(
                dnr.get("checked_cross_campaign_candidate_sha256s"), list)
            or dnr["checked_cross_campaign_candidate_sha256s"] != sorted(set(
                dnr["checked_cross_campaign_candidate_sha256s"]))
            or any(not _discovery_sha256(item) for item in
                   dnr["checked_cross_campaign_candidate_sha256s"])
            or dnr["proposed_cross_campaign_candidate_sha256"] in
               dnr["checked_cross_campaign_candidate_sha256s"]
            or not {row["cross_campaign_candidate_sha256"]
                    for row in anchor["accepted"]}.issubset(set(
                        dnr["checked_cross_campaign_candidate_sha256s"]))
            or dnr.get("receipt_sha256") != _discovery_content_hash({
                key: item for key, item in dnr.items()
                if key != "receipt_sha256"})):
        return False
    lever = accepted[-1]
    if (value["anchor_patch_set_sha256"] !=
            anchor["ordered_patch_set_sha256"]
            or value["candidate_patch_set_sha256"] !=
               candidate["ordered_patch_set_sha256"]
            or value.get("ordered_component_lever_sha256s") != [
                row["lever_sha256"] for row in accepted]
            or value.get("ordered_source_manifest_sha256s") != [
                row["manifest_sha256"] for row in accepted]
            or value["new_lever_sha256"] != lever["lever_sha256"]
            or value.get("isolated_result_sha256s") != [
                row["result_sha256"] for row in lever["replications"]]):
        return False
    body = {
        key: item for key, item in value.items()
        if key not in {"operation_key", "plan_sha256"}}
    operation_key = _discovery_content_hash({
        "schema": "epyc.autokernel.composition_operation.v1",
        "attempt_id": value["attempt_id"],
        "plan_body_sha256": _discovery_content_hash(body),
    })
    return bool(
        value["operation_key"] == operation_key
        and value["plan_sha256"] == _discovery_content_hash({
            **body, "operation_key": operation_key}))


def _discovery_v27_full_correctness(value: object, pair: dict) -> bool:
    keys = {
        "schema", "operation_key", "build_pair_sha256",
        "candidate_build_identity_sha256", "suite_id", "cases_sha256",
        "receipt_sha256", "passed", "current_full_suite", "result_sha256",
    }
    return bool(
        isinstance(value, dict) and set(value) == keys
        and value.get("schema") ==
            "epyc.autokernel.composition_full_correctness.v1"
        and value.get("operation_key") == pair.get("operation_key")
        and value.get("build_pair_sha256") == pair.get("pair_sha256")
        and value.get("candidate_build_identity_sha256") ==
            pair["candidate"].get("build_identity_sha256")
        and isinstance(value.get("suite_id"), str) and value["suite_id"]
        and all(_discovery_sha256(value.get(key)) for key in (
            "cases_sha256", "receipt_sha256", "result_sha256"))
        and value.get("passed") is True
        and value.get("current_full_suite") is True
        and value["result_sha256"] == _discovery_content_hash({
            key: item for key, item in value.items()
            if key != "result_sha256"}))


_DISCOVERY_V27_MEASUREMENT_REF_SCHEMA = (
    "epyc.autokernel.cumulative_measurement_ref.v1")
_DISCOVERY_V27_MEASUREMENT_STAGES = {
    "incremental_graphs_off": "measurement-graphs-off",
    "incremental_graphs_on": "target-runtime-graphs-on",
    "production_graphs_on": "cumulative-vs-production-graphs-on",
}


def _discovery_v27_measurement_carrier(
        reference: object, *, role: str, operation_key: str,
        contract: dict) -> dict | None:
    """Open one exact producer carrier at its contract-owned operation path."""
    if (not isinstance(reference, dict)
            or set(reference) != {"schema", "role", "path", "sha256"}
            or reference.get("schema") !=
               _DISCOVERY_V27_MEASUREMENT_REF_SCHEMA
            or reference.get("role") != role
            or not _discovery_sha256(reference.get("sha256"))
            or not _discovery_sha256(operation_key)):
        return None
    bundle = Path(str(contract.get("bundle_root", "")))
    operations_root = _safe_bundle_path(
        contract.get("operations_root"), bundle)
    path = _safe_bundle_path(reference.get("path"), bundle)
    if operations_root is None or path is None:
        return None
    operation_root = operations_root / operation_key
    repetition = None
    if role == "exact_route":
        expected = operation_root / "proof/attribution-pair.json"
    else:
        stage = _DISCOVERY_V27_MEASUREMENT_STAGES.get(role)
        try:
            relative = path.relative_to(operation_root / "runner")
        except ValueError:
            return None
        if (stage is None or len(relative.parts) != 3
                or re.fullmatch(r"s[1-9][0-9]*", relative.parts[0]) is None
                or relative.parts[1:] != (stage, "result.json")):
            return None
        repetition = relative.parts[0]
        expected = operation_root / "runner" / repetition / stage / \
            "result.json"
    try:
        if (path != expected or not path.is_absolute()
                or path.resolve(strict=False) != path):
            return None
    except OSError:
        return None
    snapshot = _owned_public_snapshot(path, max_bytes=16 * 1024 * 1024)
    if (snapshot is None
            or hashlib.sha256(snapshot[0]).hexdigest() !=
               reference["sha256"]):
        return None
    body = _strict_json_bytes(snapshot[0])
    native_key = ("receipt_sha256" if role == "exact_route"
                  else "result_sha256")
    if (body is None or not _discovery_sha256(body.get(native_key))
            or body[native_key] != _discovery_content_hash({
                key: item for key, item in body.items()
                if key != native_key})):
        return None
    return {
        "body": body, "path": path, "operation_root": operation_root,
        "repetition": repetition, "sha256": reference["sha256"],
    }


def _discovery_v27_exact_route_effect(body: object) -> float | None:
    if (not isinstance(body, dict)
            or body.get("schema") !=
               "epyc.autokernel.gpu_kernel_attribution_pair.v2"
            or body.get("authority") !=
               "nonpromotable_candidate_only_discovery"
            or body.get("non_promotable") is not True
            or body.get("promotion_claim") is not False):
        return None
    comparison = body.get("exact_duration_comparison")
    required = {
        "candidate_routes", "anchor_routes", "candidate_total_duration_ns",
        "anchor_total_duration_ns", "relative_improvement_fraction",
        "direction", "all_candidate_routes_present",
        "all_anchor_routes_present", "statistic"}
    if not isinstance(comparison, dict) or set(comparison) != required:
        return None

    def total(rows: object) -> int | None:
        if not isinstance(rows, dict) or not rows:
            return None
        values = []
        for signature, row in rows.items():
            if (not isinstance(signature, str) or not signature
                    or not isinstance(row, dict)
                    or type(row.get("total_duration_ns")) is not int
                    or row["total_duration_ns"] <= 0
                    or type(row.get("calls")) is not int
                    or row["calls"] <= 0):
                return None
            values.append(row["total_duration_ns"])
        return sum(values)

    candidate_total = total(comparison.get("candidate_routes"))
    anchor_total = total(comparison.get("anchor_routes"))
    if candidate_total is None or anchor_total is None:
        return None
    effect = (anchor_total - candidate_total) / anchor_total
    direction = ("improved" if candidate_total < anchor_total else
                 "regressed" if candidate_total > anchor_total else
                 "neutral")
    if (comparison.get("candidate_total_duration_ns") != candidate_total
            or comparison.get("anchor_total_duration_ns") != anchor_total
            or comparison.get("relative_improvement_fraction") != effect
            or comparison.get("direction") != direction
            or comparison.get("all_candidate_routes_present") is not True
            or comparison.get("all_anchor_routes_present") is not True
            or comparison.get("statistic") !=
               "sum_exact_route_total_duration_ns"):
        return None
    return effect


def _discovery_v27_runner_effect(
        body: object, *, graph_mode: str, factor_name: str) -> float | None:
    if (not isinstance(body, dict)
            or body.get("schema") !=
               "epyc.autokernel.gpu_candidate_only_screen.v2"
            or body.get("authority") !=
               "nonpromotable_candidate_only_discovery"
            or body.get("non_promotable") is not True
            or body.get("promotion_claim") is not False
            or body.get("hip_residency_proved") is not True
            or body.get("runtime_graphs") != graph_mode
            or not isinstance(body.get("sole_factor"), dict)
            or body["sole_factor"].get("name") != factor_name):
        return None
    center = body.get("baseline_center")
    samples = body.get("candidate_samples")
    if (isinstance(center, bool) or not isinstance(center, (int, float))
            or not math.isfinite(float(center)) or center <= 0
            or not isinstance(samples, list) or not samples):
        return None
    observed = []
    for row in samples:
        if (isinstance(row, bool) or not isinstance(row, (int, float))
                or not math.isfinite(float(row)) or row <= 0):
            return None
        observed.append(float(row))
    effects = [(row - float(center)) / float(center) for row in observed]
    ordered = sorted(effects)
    middle = len(ordered) // 2
    measured = (ordered[middle] if len(ordered) % 2 else
                (ordered[middle - 1] + ordered[middle]) / 2)
    if (body.get("relative_effects") != effects
            or body.get("median_relative") != measured):
        return None
    return measured


def _discovery_v27_incremental_comparison(
        value: object, pair: dict, correctness: dict,
        contract: dict) -> bool:
    keys = {
        "schema", "operation_key", "build_pair_sha256",
        "correctness_result_sha256", "exact_route_receipt_sha256",
        "exact_route_receipt_ref",
        "expected_route_set_sha256", "graphs_off_receipt_sha256",
        "graphs_off_receipt_ref",
        "graphs_on_receipt_sha256", "target_runtime_frame_sha256",
        "graphs_on_receipt_ref",
        "exact_route_effect_fraction", "graphs_off_effect_fraction",
        "graphs_on_effect_fraction", "classification",
        "exact_route_executed", "graphs_off_executed",
        "graphs_on_executed", "result_sha256",
    }
    if (not isinstance(value, dict) or set(value) != keys
            or value.get("schema") !=
               "epyc.autokernel.incremental_composition_comparison.v3"
            or value.get("operation_key") != pair.get("operation_key")
            or value.get("build_pair_sha256") != pair.get("pair_sha256")
            or value.get("correctness_result_sha256") !=
               correctness.get("result_sha256")
            or any(value.get(key) is not True for key in (
                "exact_route_executed", "graphs_off_executed",
                "graphs_on_executed"))
            or any(not _discovery_sha256(value.get(key)) for key in (
                "exact_route_receipt_sha256", "expected_route_set_sha256",
                "graphs_off_receipt_sha256", "graphs_on_receipt_sha256",
                "target_runtime_frame_sha256", "result_sha256"))):
        return False
    carriers = (
        _discovery_v27_measurement_carrier(
            value.get("exact_route_receipt_ref"), role="exact_route",
            operation_key=value["operation_key"], contract=contract),
        _discovery_v27_measurement_carrier(
            value.get("graphs_off_receipt_ref"),
            role="incremental_graphs_off",
            operation_key=value["operation_key"], contract=contract),
        _discovery_v27_measurement_carrier(
            value.get("graphs_on_receipt_ref"),
            role="incremental_graphs_on",
            operation_key=value["operation_key"], contract=contract),
    )
    if (any(row is None for row in carriers)
            or len({row["operation_root"] for row in carriers}) != 1
            or carriers[0]["repetition"] is not None
            or carriers[1]["repetition"] != carriers[2]["repetition"]
            or value.get("exact_route_receipt_sha256") !=
               carriers[0]["sha256"]
            or value.get("graphs_off_receipt_sha256") !=
               carriers[1]["sha256"]
            or value.get("graphs_on_receipt_sha256") !=
               carriers[2]["sha256"]):
        return False
    effect_keys = (
        "exact_route_effect_fraction", "graphs_off_effect_fraction",
        "graphs_on_effect_fraction")
    if any(isinstance(value.get(key), bool)
           or not isinstance(value.get(key), (int, float))
           or not math.isfinite(float(value[key])) for key in effect_keys):
        return False
    effects = tuple(float(value[key]) for key in effect_keys)
    derived = (
        _discovery_v27_exact_route_effect(carriers[0]["body"]),
        _discovery_v27_runner_effect(
            carriers[1]["body"], graph_mode="off",
            factor_name="source_patch"),
        _discovery_v27_runner_effect(
            carriers[2]["body"], graph_mode="on",
            factor_name="source_patch"),
    )
    classification = (
        "candidate" if all(effect > 0 for effect in effects)
        else "screened_out" if all(effect <= 0 for effect in effects)
        else "inconclusive")
    return bool(
        None not in derived and effects == derived
        and value.get("classification") == classification
        and value["result_sha256"] == _discovery_content_hash({
            key: item for key, item in value.items()
            if key != "result_sha256"}))


_DISCOVERY_V27_COMPOSITION_TERMINAL_KEYS = {
    "schema", "operation_key", "plan_sha256", "plan", "lever_sha256",
    "cross_campaign_candidate_sha256", "isolated_result_sha256s",
    "disposition", "scientific_budget_spent", "build_pair", "correctness",
    "comparison", "cumulative_performance", "cumulative_performance_ref",
    "correctness_result_sha256", "comparison_result_sha256",
    "cumulative_performance_result_sha256", "promotion_eligible",
    "promotion_reason", "admitted_authority_sha256", "reason_code",
    "infrastructure_receipt_sha256", "attribution_receipt_sha256",
    "terminal_sha256"}
_DISCOVERY_V27_TERMINAL_CORE_EXCLUDED = {
    "cumulative_performance", "cumulative_performance_ref",
    "cumulative_performance_result_sha256", "terminal_sha256"}


def _discovery_v27_terminal_core_sha256(value: object) -> str | None:
    """Hash the producer's non-circular terminal decision-core projection."""
    if (not isinstance(value, dict)
            or set(value) != _DISCOVERY_V27_COMPOSITION_TERMINAL_KEYS
            or value.get("schema") !=
               "epyc.autokernel.cumulative_composition_terminal.v3"
            or any(not _discovery_sha256(value.get(key)) for key in (
                "operation_key", "plan_sha256", "lever_sha256",
                "cross_campaign_candidate_sha256"))
            or not isinstance(value.get("plan"), dict)
            or value["plan"].get("operation_key") != value["operation_key"]
            or value["plan"].get("plan_sha256") != value["plan_sha256"]
            or not isinstance(value.get("isolated_result_sha256s"), list)
            or len(value["isolated_result_sha256s"]) < 2
            or value["isolated_result_sha256s"] != list(dict.fromkeys(
                value["isolated_result_sha256s"]))
            or any(not _discovery_sha256(item)
                   for item in value["isolated_result_sha256s"])
            or not isinstance(value.get("scientific_budget_spent"), bool)
            or not isinstance(value.get("promotion_eligible"), bool)
            or not isinstance(value.get("promotion_reason"), str)
            or not value["promotion_reason"]
            or not isinstance(value.get("reason_code"), str)
            or not value["reason_code"]
            or any(item is not None and not _discovery_sha256(item)
                   for item in (
                       value.get("correctness_result_sha256"),
                       value.get("comparison_result_sha256"),
                       value.get("cumulative_performance_result_sha256"),
                       value.get("admitted_authority_sha256"),
                       value.get("infrastructure_receipt_sha256"),
                       value.get("attribution_receipt_sha256")))):
        return None
    core_sha256 = _discovery_content_hash({
        key: item for key, item in value.items()
        if key not in _DISCOVERY_V27_TERMINAL_CORE_EXCLUDED})
    return core_sha256 if value.get("terminal_sha256") == core_sha256 else None


def _discovery_v27_cumulative_performance(
        binding: object, terminal: object, contract: dict) -> dict:
    """Project only producer-sealed promotion authority; never infer it."""
    unavailable = _discovery_v27_performance_unavailable(
        "producer_authority_unavailable")
    if (not isinstance(binding, dict)
            or set(binding) != {"path", "sha256"}
            or not _discovery_sha256(binding.get("sha256"))):
        return unavailable
    bundle = Path(str(contract.get("bundle_root", "")))
    path = _safe_bundle_path(binding.get("path"), bundle)
    snapshot = (_owned_public_snapshot(path, max_bytes=4 * 1024 * 1024)
                if path is not None else None)
    if (snapshot is None
            or hashlib.sha256(snapshot[0]).hexdigest() != binding["sha256"]):
        return unavailable
    receipt = _strict_json_bytes(snapshot[0])
    fields = {
        "operation_key", "plan_sha256", "accepted_authority_sha256",
        "accepted_patch_set_sha256", "build_pair_sha256",
        "correctness_result_sha256",
        "incremental_comparison_result_sha256", "frozen_production",
        "model_sha256", "workload_sha256", "runtime_config_sha256",
        "protocol_frame_sha256", "metric", "metric_direction",
        "incremental_exact_route_effect_fraction",
        "incremental_graphs_off_effect_fraction",
        "incremental_graphs_on_effect_fraction",
        "cumulative_graphs_on_effect_fraction",
        "incremental_exact_route_receipt_sha256",
        "incremental_exact_route_receipt_ref",
        "incremental_graphs_off_receipt_sha256",
        "incremental_graphs_off_receipt_ref",
        "incremental_graphs_on_receipt_sha256",
        "incremental_graphs_on_receipt_ref",
        "production_graphs_on_receipt_sha256",
        "production_graphs_on_receipt_ref",
        "incremental_graphs_off_frame_sha256",
        "incremental_graphs_on_frame_sha256",
        "production_graphs_on_frame_sha256",
        "production_graphs_mode",
        "cumulative_classification", "promotion_eligible",
        "promotion_reason", "composition_terminal_sha256", "result_sha256"}
    keys = fields | {"schema", "authority", "promotion_authority"}
    if (not isinstance(receipt, dict) or set(receipt) != keys
            or receipt.get("schema") != _DISCOVERY_V27_CUMULATIVE_SCHEMA
            or receipt.get("authority") !=
               "frozen_production_promotion_gate"
            or receipt.get("promotion_authority") is not True
            or any(not _discovery_sha256(receipt.get(key)) for key in (
                "operation_key", "plan_sha256", "accepted_authority_sha256",
                "accepted_patch_set_sha256", "build_pair_sha256",
                "correctness_result_sha256",
                "incremental_comparison_result_sha256", "model_sha256",
                "workload_sha256", "runtime_config_sha256",
                "protocol_frame_sha256",
                "incremental_exact_route_receipt_sha256",
                "incremental_graphs_off_receipt_sha256",
                "incremental_graphs_on_receipt_sha256",
                "production_graphs_on_receipt_sha256",
                "incremental_graphs_off_frame_sha256",
                "incremental_graphs_on_frame_sha256",
                "production_graphs_on_frame_sha256",
                "composition_terminal_sha256", "result_sha256"))
            or receipt.get("result_sha256") != _discovery_content_hash({
                key: item for key, item in receipt.items()
                if key != "result_sha256"})):
        return unavailable
    operations_root = _safe_bundle_path(
        contract.get("operations_root"), bundle)
    expected_performance_path = (
        operations_root / receipt["operation_key"] /
        "cumulative-performance.json"
        if operations_root is not None else None)
    try:
        if (expected_performance_path is None
                or path != expected_performance_path
                or path.resolve(strict=False) != path):
            return unavailable
    except OSError:
        return unavailable
    static = contract.get("frozen_production_comparator")
    frozen = receipt.get("frozen_production")
    frozen_keys = {
        "schema", "production_commit", "build_identity",
        "build_identity_sha256", "runtime_snapshot_sha256",
        "comparator_receipt_sha256", "graphs_mode", "frame_sha256",
        "measurement_protocol_sha256", "measurement_receipt_sha256",
        "model_sha256", "workload_sha256", "runtime_config_sha256",
        "observed_workload_sha256", "observed_runtime_config_sha256",
        "metric", "direction", "authority_sha256"}
    if (not isinstance(static, dict)
            or not isinstance(frozen, dict) or set(frozen) != frozen_keys
            or frozen.get("schema") !=
               "epyc.autokernel.frozen_production_authority.v2"
            or frozen.get("production_commit") !=
               _DISCOVERY_V27_PRODUCTION_COMMIT
            or frozen.get("production_commit") != static.get("commit")
            or frozen.get("build_identity") != static.get("build_identity")
            or frozen.get("build_identity_sha256") !=
               _discovery_content_hash(frozen.get("build_identity"))
            or frozen.get("runtime_snapshot_sha256") !=
               static.get("runtime_snapshot_sha256")
            or frozen.get("comparator_receipt_sha256") !=
               static.get("receipt_sha256")
            or frozen.get("graphs_mode") != static.get("graphs_mode")
            or frozen.get("frame_sha256") != static.get("frame_sha256")
            or frozen.get("measurement_protocol_sha256") !=
               static.get("measurement_protocol_sha256")
            or frozen.get("measurement_receipt_sha256") !=
               static.get("measurement_receipt_sha256")
            or frozen.get("model_sha256") != static.get("model_sha256")
            or frozen.get("workload_sha256") !=
               static.get("workload_sha256")
            or frozen.get("runtime_config_sha256") !=
               static.get("runtime_config_sha256")
            or frozen.get("observed_workload_sha256") !=
               static.get("observed_workload_sha256")
            or frozen.get("observed_runtime_config_sha256") !=
               static.get("observed_runtime_config_sha256")
            or frozen.get("metric") != static.get("metric")
            or frozen.get("direction") != static.get("direction")
            or frozen.get("authority_sha256") != _discovery_content_hash({
                key: item for key, item in frozen.items()
                if key != "authority_sha256"})):
        return unavailable
    core_sha256 = _discovery_v27_terminal_core_sha256(terminal)
    ref = terminal.get("cumulative_performance_ref")
    plan = terminal.get("plan")
    build_pair = terminal.get("build_pair")
    correctness = terminal.get("correctness")
    comparison = terminal.get("comparison")
    if (core_sha256 is None
            or receipt.get("composition_terminal_sha256") != core_sha256
            or not _discovery_v27_composition_plan(plan)
            or not _discovery_v27_composition_build_pair(build_pair)
            or not _discovery_v27_full_correctness(correctness, build_pair)
            or not _discovery_v27_incremental_comparison(
                comparison, build_pair, correctness, contract)):
        return unavailable
    candidate_authority = plan["candidate_authority"]
    anchor_authority = plan["anchor_authority"]
    lever = candidate_authority["accepted"][-1]
    incremental_admissible = comparison["classification"] == "candidate"
    expected_disposition = (
        "admitted" if incremental_admissible else "incremental_rollback")
    expected_reason_code = (
        "incremental_admitted_promotion_eligible"
        if incremental_admissible and receipt.get("promotion_eligible") is True
        else "incremental_admitted_" + str(receipt.get("promotion_reason"))
        if incremental_admissible
        else "incremental_" + comparison["classification"])
    if (not isinstance(ref, dict)
            or set(ref) != {"schema", "path", "sha256"}
            or ref.get("schema") !=
               "epyc.autokernel.cumulative_performance_ref.v1"
            or {key: ref.get(key) for key in ("path", "sha256")} != binding
            or terminal.get("cumulative_performance") != receipt
            or terminal.get("cumulative_performance_result_sha256") !=
               receipt["result_sha256"]
            or terminal.get("promotion_eligible") !=
               receipt.get("promotion_eligible")
            or terminal.get("promotion_reason") != receipt.get(
                "promotion_reason")
            or terminal.get("operation_key") != receipt["operation_key"]
            or terminal.get("plan_sha256") != receipt["plan_sha256"]
            or terminal.get("correctness_result_sha256") !=
               receipt["correctness_result_sha256"]
            or terminal.get("comparison_result_sha256") !=
               receipt["incremental_comparison_result_sha256"]
            or terminal.get("disposition") == "admitted"
            and terminal.get("admitted_authority_sha256") !=
                receipt["accepted_authority_sha256"]
            or terminal.get("disposition") != "admitted"
            and terminal.get("admitted_authority_sha256") is not None
            or build_pair.get("operation_key") != receipt["operation_key"]
            or build_pair.get("plan_sha256") != receipt["plan_sha256"]
            or build_pair.get("operation_key") != plan["operation_key"]
            or build_pair.get("plan_sha256") != plan["plan_sha256"]
            or build_pair["anchor"].get("patch_set_sha256") !=
               anchor_authority["ordered_patch_set_sha256"]
            or build_pair["candidate"].get("patch_set_sha256") !=
               candidate_authority["ordered_patch_set_sha256"]
            or build_pair.get("pair_sha256") != receipt["build_pair_sha256"]
            or build_pair["candidate"].get("patch_set_sha256") !=
               receipt["accepted_patch_set_sha256"]
            or correctness.get("result_sha256") !=
               receipt["correctness_result_sha256"]
            or comparison.get("result_sha256") !=
               receipt["incremental_comparison_result_sha256"]
            or receipt.get("operation_key") != plan["operation_key"]
            or receipt.get("plan_sha256") != plan["plan_sha256"]
            or receipt.get("accepted_authority_sha256") !=
               candidate_authority["authority_sha256"]
            or receipt.get("accepted_patch_set_sha256") !=
               candidate_authority["ordered_patch_set_sha256"]
            or plan["candidate_authority"]["production_base_commit"] !=
               frozen["production_commit"]
            or terminal.get("lever_sha256") != lever["lever_sha256"]
            or terminal.get("cross_campaign_candidate_sha256") !=
               lever["cross_campaign_candidate_sha256"]
            or terminal.get("isolated_result_sha256s") != [
                row["result_sha256"] for row in lever["replications"]]
            or terminal.get("scientific_budget_spent") is not True
            or terminal.get("disposition") != expected_disposition
            or terminal.get("reason_code") != expected_reason_code
            or terminal.get("admitted_authority_sha256") != (
                candidate_authority["authority_sha256"]
                if incremental_admissible else None)):
        return unavailable
    off_binding = _discovery_v27_measurement_binding(
        model_sha256=contract.get("model_sha256"),
        build_identity=build_pair["candidate"]["build_identity"],
        graphs_mode="off", arm="candidate", factor_name="source_patch")
    on_binding = _discovery_v27_measurement_binding(
        model_sha256=contract.get("model_sha256"),
        build_identity=build_pair["candidate"]["build_identity"],
        graphs_mode="on", arm="candidate", factor_name="source_patch")
    production_binding = _discovery_v27_measurement_binding(
        model_sha256=contract.get("model_sha256"),
        build_identity=static.get("build_identity"),
        graphs_mode="on", arm="anchor",
        factor_name="cumulative_production")
    if (receipt.get("model_sha256") != contract.get("model_sha256")
            or receipt.get("model_sha256") != static.get("model_sha256")
            or receipt.get("workload_sha256") != contract.get(
                "deployment_workload_file_sha256")
            or receipt.get("workload_sha256") != static.get(
                "workload_sha256")
            or receipt.get("runtime_config_sha256") != contract.get(
                "deployment_runtime_file_sha256")
            or receipt.get("runtime_config_sha256") != static.get(
                "runtime_config_sha256")
            or frozen.get("observed_workload_sha256") !=
               _discovery_content_hash(_DISCOVERY_V27_MEASURED_WORKLOAD)
            or frozen.get("observed_runtime_config_sha256") !=
               _discovery_content_hash(_DISCOVERY_V27_MEASURED_RUNTIME)
            or receipt.get("metric") != "decode_tokens_per_s"
            or receipt.get("metric_direction") != "higher_better"
            or static.get("metric") != "tokens_per_second"
            or static.get("direction") != "higher_is_better"
            or receipt.get("production_graphs_mode") != "on"
            or static.get("graphs_mode") != "graphs_on"
            or off_binding is None or on_binding is None
            or production_binding is None
            or receipt.get("protocol_frame_sha256") !=
               on_binding[0]
            or receipt.get("protocol_frame_sha256") !=
               production_binding[0]
            or receipt.get("protocol_frame_sha256") !=
               static.get("measurement_protocol_sha256")
            or receipt.get("incremental_graphs_off_frame_sha256") !=
               off_binding[1]
            or receipt.get("incremental_graphs_on_frame_sha256") !=
               on_binding[1]
            or receipt.get("production_graphs_on_frame_sha256") !=
               production_binding[1]
            or receipt.get("production_graphs_on_frame_sha256") !=
               static.get("frame_sha256")
            or receipt.get("incremental_exact_route_effect_fraction") !=
               comparison.get("exact_route_effect_fraction")
            or receipt.get("incremental_graphs_off_effect_fraction") !=
               comparison.get("graphs_off_effect_fraction")
            or receipt.get("incremental_graphs_on_effect_fraction") !=
               comparison.get("graphs_on_effect_fraction")
            or receipt.get("incremental_exact_route_receipt_sha256") !=
               comparison.get("exact_route_receipt_sha256")
            or receipt.get("incremental_graphs_off_receipt_sha256") !=
               comparison.get("graphs_off_receipt_sha256")
            or receipt.get("incremental_graphs_on_receipt_sha256") !=
               comparison.get("graphs_on_receipt_sha256")
            or receipt.get("incremental_exact_route_receipt_ref") !=
               comparison.get("exact_route_receipt_ref")
            or receipt.get("incremental_graphs_off_receipt_ref") !=
               comparison.get("graphs_off_receipt_ref")
            or receipt.get("incremental_graphs_on_receipt_ref") !=
               comparison.get("graphs_on_receipt_ref")
            or len({
                receipt["incremental_graphs_off_frame_sha256"],
                receipt["incremental_graphs_on_frame_sha256"],
                receipt["production_graphs_on_frame_sha256"]}) != 3
            or len({
                receipt["incremental_graphs_off_receipt_sha256"],
                receipt["incremental_graphs_on_receipt_sha256"],
                receipt["production_graphs_on_receipt_sha256"]}) != 3):
        return unavailable
    carrier_specs = (
        ("incremental_exact_route_receipt_ref", "exact_route", None,
         None),
        ("incremental_graphs_off_receipt_ref", "incremental_graphs_off",
         "off", "source_patch"),
        ("incremental_graphs_on_receipt_ref", "incremental_graphs_on",
         "on", "source_patch"),
        ("production_graphs_on_receipt_ref", "production_graphs_on",
         "on", "cumulative_production"),
    )
    carriers = tuple(
        _discovery_v27_measurement_carrier(
            receipt.get(key), role=role,
            operation_key=receipt["operation_key"], contract=contract)
        for key, role, _mode, _factor in carrier_specs)
    if (any(row is None for row in carriers)
            or len({row["operation_root"] for row in carriers}) != 1
            or carriers[0]["repetition"] is not None
            or len({row["repetition"] for row in carriers[1:]}) != 1
            or receipt.get("incremental_exact_route_receipt_sha256") !=
               carriers[0]["sha256"]
            or receipt.get("incremental_graphs_off_receipt_sha256") !=
               carriers[1]["sha256"]
            or receipt.get("incremental_graphs_on_receipt_sha256") !=
               carriers[2]["sha256"]
            or receipt.get("production_graphs_on_receipt_sha256") !=
               carriers[3]["sha256"]):
        return unavailable
    numeric_keys = (
        "incremental_exact_route_effect_fraction",
        "incremental_graphs_off_effect_fraction",
        "incremental_graphs_on_effect_fraction",
        "cumulative_graphs_on_effect_fraction")
    if any(isinstance(receipt.get(key), bool)
           or not isinstance(receipt.get(key), (int, float))
           or not math.isfinite(float(receipt[key])) for key in numeric_keys):
        return unavailable
    incremental = tuple(float(receipt[key]) for key in numeric_keys[:3])
    cumulative_on = float(receipt[numeric_keys[3]])
    derived = (
        _discovery_v27_exact_route_effect(carriers[0]["body"]),
        _discovery_v27_runner_effect(
            carriers[1]["body"], graph_mode="off",
            factor_name="source_patch"),
        _discovery_v27_runner_effect(
            carriers[2]["body"], graph_mode="on",
            factor_name="source_patch"),
        _discovery_v27_runner_effect(
            carriers[3]["body"], graph_mode="on",
            factor_name="cumulative_production"),
    )
    if any(value <= -1.0 for value in (*incremental, cumulative_on)):
        return unavailable
    if None in derived or (*incremental, cumulative_on) != derived:
        return unavailable
    incremental_class = (
        "candidate" if all(value > 0 for value in incremental)
        else "screened_out" if all(value <= 0 for value in incremental)
        else "inconclusive")
    cumulative_class = "candidate" if cumulative_on > 0 else "screened_out"
    expected_eligible = (
        incremental_class == "candidate" and cumulative_class == "candidate")
    expected_reason = (
        "incremental_and_cumulative_positive" if expected_eligible
        else f"incremental_{incremental_class}"
        if incremental_class != "candidate"
        else f"cumulative_{cumulative_class}")
    if (receipt.get("cumulative_classification") != cumulative_class
            or receipt.get("promotion_eligible") is not expected_eligible
            or receipt.get("promotion_reason") != expected_reason):
        return unavailable
    expected_terminal_reason = (
        "incremental_admitted_promotion_eligible" if expected_eligible else
        "incremental_admitted_" + expected_reason)
    if (terminal.get("disposition") == "admitted"
            and (terminal.get("scientific_budget_spent") is not True
                 or not _discovery_sha256(
                     terminal.get("admitted_authority_sha256"))
                 or terminal.get("infrastructure_receipt_sha256") is not None
                 or terminal.get("attribution_receipt_sha256") is not None
                 or terminal.get("reason_code") !=
                    expected_terminal_reason)):
        return unavailable
    if (terminal.get("disposition") == "incremental_rollback"
            and (terminal.get("scientific_budget_spent") is not True
                 or terminal.get("admitted_authority_sha256") is not None
                 or terminal.get("infrastructure_receipt_sha256") is not None
                 or terminal.get("attribution_receipt_sha256") is not None
                 or terminal.get("reason_code") !=
                    "incremental_" + incremental_class)):
        return unavailable
    if terminal.get("disposition") not in {
            "admitted", "incremental_rollback"}:
        return unavailable
    speedup = 1.0 + cumulative_on
    return {
        "available": True,
        "headline": (
            f"{cumulative_on * 100:+.2f}% cumulative vs frozen production "
            f"({speedup:.4f}x)"),
        "cumulative_vs_frozen_production": {
            "effect_fraction": cumulative_on, "speedup": speedup,
            "production_branch": static["branch"],
            "production_commit": static["commit"],
            "graphs_mode": "graphs_on", "metric": receipt["metric"]},
        "incremental_vs_prior_stack": {
            "effect_fraction": incremental[2],
            "graphs_off_effect_fraction": incremental[1],
            "exact_route_effect_fraction": incremental[0]},
        "promotion_eligible": receipt["promotion_eligible"],
        "promotion_reason": receipt["promotion_reason"],
        "receipt_sha256": receipt["result_sha256"],
        "terminal_core_sha256": core_sha256,
    }


def _discovery_v26_state_contract(state: object,
                                  contract: dict, *,
                                  now: float | None = None) -> dict | None:
    current_time = time.time() if now is None else now
    state_time = (_parse_semantic_timestamp(state.get("updated_at"))
                  if isinstance(state, dict) else None)
    if (not isinstance(state, dict)
            or not _DISCOVERY_V26_STATE_REQUIRED.issubset(state)
            or set(state) - (_DISCOVERY_V26_STATE_REQUIRED
                             | _DISCOVERY_V26_STATE_OPTIONAL)
            or state.get("schema") != "epyc.autokernel.discovery_controller.v7"
            or state.get("authority") !=
               "nonpromotable_candidate_only_discovery"
            or state.get("roster") != _DISCOVERY_V26_ROSTER
            or not _discovery_sha256(state.get("state_sha256"))
            or state["state_sha256"] != _discovery_controller_state_hash({
                key: value for key, value in state.items()
                if key != "state_sha256"})
            or not isinstance(state.get("iterations"), list)
            or isinstance(state.get("next"), bool)
            or not isinstance(state.get("next"), int) or state["next"] < 1
            or isinstance(state.get("scientific_attempts"), bool)
            or not isinstance(state.get("scientific_attempts"), int)
            or state["scientific_attempts"] < 0
            or not isinstance(state.get("complete"), bool)
            or state_time is None or state_time > current_time + 5.0
            or isinstance(contract.get("max_iterations"), bool)
            or not isinstance(contract.get("max_iterations"), int)
            or state["scientific_attempts"] > contract["max_iterations"]):
        return None
    sealed_state_links = {
        "deployment_identity_sha256":
            contract.get("deployment_identity_sha256"),
        "planner_context_sha256": contract.get("planner_context_sha256"),
        "experiment_template_registry_sha256":
            contract.get("template_registry_sha256"),
        "admission_corpus_sha256": contract.get("admission_corpus_sha256"),
        "admission_corpus_version": contract.get("admission_corpus_version"),
        "hypothesis_portfolio_sha256":
            contract.get("hypothesis_portfolio_sha256"),
        "carry_forward_sha256": contract.get("carry_forward_sha256"),
        "preauthored_continuation_sha256":
            contract.get("preauthored_continuation_sha256"),
        "preauthored_source_backed_diff_sha256":
            contract.get("preauthored_source_backed_diff_sha256"),
    }
    if any(state.get(key) != value
           for key, value in sealed_state_links.items()):
        return None
    mapping_fields = {
        "attempted_candidate_identities", "portfolio_attribution_failures",
        "portfolio_authoring_failures", "portfolio_measurement_output_failures",
        "portfolio_skips", "portfolio_terminals", "portfolio_validations",
    }
    if (any(key in state and not isinstance(state[key], dict)
            for key in mapping_fields)
            or any(key in state and not isinstance(state[key], dict)
                   for key in ("pending", "inflight", "planning"))
            or "visibility_degraded" in state
            and not isinstance(state["visibility_degraded"], list)
            or state.get("candidate_semantic_registry_schema") not in {
                None, "epyc.autokernel.candidate_semantic_registry.v1"}
            or not _discovery_v26_infrastructure_ambiguities(state)):
        return None
    active_holders = [
        key for key in ("pending", "inflight", "planning")
        if state.get(key) is not None]
    if len(active_holders) > 1:
        return None
    if state["complete"]:
        if (active_holders
                or state.get("terminal_reason") not in {
                    "portfolio_exhausted", "scientific_budget_exhausted"}
                or state.get("terminal_reason") ==
                   "scientific_budget_exhausted"
                and state["scientific_attempts"] !=
                    contract["max_iterations"]):
            return None
    elif "terminal_reason" in state:
        return None
    if active_holders and not _discovery_v26_generic_holder(
            active_holders[0], state[active_holders[0]], state, contract):
        return None
    cursor = 1
    transient_count = 0
    transient_operations: set[str] = set()
    scientific = 0
    for row in state["iterations"]:
        if (isinstance(row, dict)
                and row.get("status") == "planner_transient"):
            if (not _discovery_v26_planner_transient(row, turn=cursor)
                    or row["planner_operation_key"] in transient_operations):
                return None
            transient_operations.add(row["planner_operation_key"])
            transient_count += 1
            continue
        valid, spent = _discovery_v26_iteration(row, turn=cursor)
        if not valid:
            return None
        scientific += int(spent)
        cursor += 1
    if (state["next"] != cursor
            or state.get("planner_provider_attempt", 0) != transient_count
            or isinstance(state.get("planner_provider_attempt", 0), bool)):
        return None
    if state["scientific_attempts"] != scientific:
        return None
    derived_registry: dict[str, dict] = {}
    for row in state["iterations"]:
        if not isinstance(row, dict) or row.get("scientific_budget_spent") is not True:
            continue
        identity = row["candidate_semantic_sha256"]
        entry = derived_registry.setdefault(identity, {
            "hypothesis_id": row["portfolio_hypothesis_id"], "attempts": []})
        attempt = {
            "operation_key": row["operation_key"],
            "result_sha256": row["result_sha256"],
            "disposition": row["status"],
            "repetition": row.get("repetition", 1),
        }
        if (entry["hypothesis_id"] != row["portfolio_hypothesis_id"]
                or attempt in entry["attempts"]
                or any(value.get("operation_key") == row["operation_key"]
                       for value in entry["attempts"])):
            return None
        entry["attempts"].append(attempt)
    declared_registry = state.get("attempted_candidate_identities", {})
    if (declared_registry != derived_registry
            or bool(derived_registry) != (
                state.get("candidate_semantic_registry_schema") ==
                "epyc.autokernel.candidate_semantic_registry.v1")):
        return None
    holder = next((state[key] for key in ("pending", "inflight")
                   if isinstance(state.get(key), dict)
                   and state[key].get("preauthored_continuation") is not None),
                  None)
    provenance = None
    if holder is not None:
        authority = holder.get("preauthored_continuation")
        row = holder.get("row")
        candidate = holder.get("candidate")
        graph_authority = contract.get("preauthored")
        if (not isinstance(authority, dict)
                or set(authority) !=
                   _DISCOVERY_V26_PREAUTHORED_CHECKPOINT_KEYS
                or authority.get("schema") !=
                   "epyc.autokernel.preauthored_checkpoint.v1"
                or authority.get("receipt_sha256") !=
                   _discovery_controller_state_hash({
                       key: value for key, value in authority.items()
                       if key != "receipt_sha256"})
                or isinstance(authority.get("authoring_turn"), bool)
                or not isinstance(authority.get("authoring_turn"), int)
                or authority["authoring_turn"] < 1
                or not all(_discovery_sha256(authority.get(key)) for key in (
                    "carrier_sha256", "source_backed_diff_sha256",
                    "source_manifest_sha256", "candidate_semantic_sha256",
                    "cross_campaign_candidate_sha256"))
                or not isinstance(graph_authority, dict)
                or authority.get("hypothesis_id") !=
                   graph_authority.get("hypothesis_id")
                or authority.get("carrier_sha256") !=
                   graph_authority.get("carrier_sha256")
                or authority.get("source_backed_diff_sha256") !=
                   graph_authority.get("source_backed_diff_sha256")
                or authority.get("origin") != "import"
                or authority.get("author") !=
                   "reviewed-eb26918-continuation"
                or authority.get("historical_commit") !=
                   contract.get("historical_commit")
                or authority.get("modern_governed_correctness_required")
                   is not True
                or not isinstance(row, dict) or not isinstance(candidate, dict)
                or row.get("preauthored_continuation") != authority
                or row.get("hypothesis_id") != authority["hypothesis_id"]
                or row.get("turn") != state["next"]
                or row.get("authoring_turn") != authority["authoring_turn"]
                or row.get("source_manifest_sha256") !=
                   authority["source_manifest_sha256"]
                or row.get("candidate_semantic_sha256") !=
                   authority["candidate_semantic_sha256"]
                or row.get("hypothesis_origin") != authority["origin"]
                or row.get("hypothesis_author") != authority["author"]
                or row.get("historical_correctness_authority") !=
                   "provenance_only"
                or row.get("modern_governed_correctness_required") is not True
                or candidate.get("hypothesis_id") != authority["hypothesis_id"]
                or candidate.get("source_manifest_sha256") !=
                   authority["source_manifest_sha256"]):
            return None
        if (state.get("pending") is holder
                and not _discovery_v26_preauthored_pending(holder, state)):
            return None
        provenance = {
            "imported": True, "actor_bypass": True,
            "origin": authority["origin"], "author": authority["author"],
            "historical_correctness_authority": "provenance_only",
            "modern_governed_correctness_required": True,
            "carrier_sha256": authority["carrier_sha256"],
            "source_manifest_sha256": authority["source_manifest_sha256"],
        }
    return {"scientific_attempts": scientific, "provenance": provenance,
            "updated_at_unix": state_time}


def _discovery_v27_state_contract(state: object,
                                  contract: dict, *,
                                  now: float | None = None) -> dict | None:
    """Extend the unchanged v7 state grammar with v27's typed wait carrier."""
    if (not isinstance(state, dict)
            or state.get("state_sha256") !=
               _discovery_controller_state_hash({
                   key: value for key, value in state.items()
                   if key != "state_sha256"})):
        return None
    performance = (
        _discovery_v27_cumulative_performance(
            state.get("cumulative_performance"),
            state.get("cumulative_composition_terminal"), contract)
        if "cumulative_performance" in state else
        _discovery_v27_performance_unavailable(
            "cumulative_authority_missing"))
    pending = state.get("pending")
    row = pending.get("row") if isinstance(pending, dict) else None
    waiting = bool(isinstance(row, dict)
                   and row.get("status") == "waiting_resource")
    has_checkpoint = bool(isinstance(pending, dict)
                          and "resource_wait" in pending)
    resource_wait = None
    projected_state = {
        key: value for key, value in state.items()
        if key not in {
            "cumulative_performance", "cumulative_composition_terminal"}}
    projected_state["state_sha256"] = _discovery_controller_state_hash({
        key: value for key, value in projected_state.items()
        if key != "state_sha256"})
    if has_checkpoint:
        if not waiting:
            return None
        resource_wait = _discovery_v27_postbuild_resource_wait(
            pending, contract)
        if resource_wait is None:
            return None
        clean_pending = {
            key: value for key, value in pending.items()
            if key != "resource_wait"}
        projected_state = {**projected_state, "pending": clean_pending}
        projected_state["state_sha256"] = _discovery_controller_state_hash({
            key: value for key, value in projected_state.items()
            if key != "state_sha256"})
    elif waiting:
        resource_wait = _discovery_v27_prebuild_resource_wait(row, contract)
        if resource_wait is None:
            return None
    projected = _discovery_v26_state_contract(
        projected_state, contract, now=now)
    erratum = contract.get("q5_erratum")
    if projected is None or not _discovery_v27_erratum(erratum):
        return None
    history = [{
        "turn": erratum["invalidated_predecessor_projection"]["turn"],
        "hypothesis_id": erratum["hypothesis_id"],
        "status": erratum["replacement_disposition"],
        "raw_status": erratum["classification"],
        "scientific_budget_spent": False,
        "result_file_sha256":
            erratum["invalidated_predecessor_projection"][
                "result_file_sha256"],
        "history_retained": True,
    }]
    return {
        **projected,
        "resource_wait": resource_wait,
        "performance": performance,
        "annulled_history": history,
        "annulled_scientific_attempts": 1,
        "scientific_budget": {
            "spent": projected["scientific_attempts"],
            "maximum": contract["max_iterations"],
        },
    }


def _discovery_portfolio_terminal_checkpoint(
        path: Path, state: object, *, now: float) -> dict | None:
    """Bind v25's final state to its consecutive portfolio/complete journal rows.

    A bare ``complete=true`` is mutable state, while the journal alone does not
    prove which final state it describes.  The producer deliberately emits the
    portfolio-exhausted state and then a final complete state.  Accept that
    terminal only when the canonical state self-hash, the final journal digest,
    both consecutive event identities, and their timestamps all agree.
    """
    state_snapshot = _owned_public_snapshot(
        path.parent.parent / "state.json", max_bytes=2 * 1024 * 1024)
    state_from_disk = (_strict_json_bytes(state_snapshot[0])
                       if state_snapshot is not None else None)
    if (not isinstance(state, dict) or state_from_disk != state
            or set(state) !=
            _DISCOVERY_TERMINAL_STATE_KEYS
            or state.get("schema") != "epyc.autokernel.discovery_controller.v5"
            or state.get("authority") !=
            "nonpromotable_candidate_only_discovery"
            or state.get("complete") is not True
            or state.get("terminal_reason") != "portfolio_exhausted"
            or not isinstance(state.get("state_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", state["state_sha256"]) is None
            or state["state_sha256"] != _discovery_controller_state_hash({
                key: value for key, value in state.items()
                if key != "state_sha256"})
            or not isinstance(state.get("next"), int)
            or isinstance(state.get("next"), bool) or state["next"] <= 1
            or not isinstance(state.get("scientific_attempts"), int)
            or isinstance(state.get("scientific_attempts"), bool)
            or state["scientific_attempts"] < 0
            or not isinstance(state.get("iterations"), list)
            or len(state["iterations"]) != state["next"] - 1
            or state["scientific_attempts"] > len(state["iterations"])):
        return None
    turns = [row.get("turn") if isinstance(row, dict) else None
             for row in state["iterations"]]
    if turns != list(range(1, state["next"])):
        return None
    state_time = _parse_semantic_timestamp(state.get("updated_at"))
    if state_time is None or state_time > now + 5.0:
        return None
    snapshot = _owned_public_snapshot(path, max_bytes=2 * 1024 * 1024)
    if snapshot is None:
        return None
    raw = snapshot[0]
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError:
        return None
    if len(lines) < 2 or not raw.endswith(b"\n"):
        return None
    rows = []
    for line in lines[-2:]:
        row = _strict_json_bytes(line.encode("ascii"))
        payload = row.get("payload") if isinstance(row, dict) else None
        if (row is None or set(row) != {
                "campaign_id", "event_id", "journal_schema", "kind",
                "payload", "record_id", "seq", "written_at"}
                or line.encode("ascii") != _canonical_json_bytes(row)
                or row.get("journal_schema") !=
                "epyc.autokernel.journal_entry.v1"
                or row.get("kind") != "STOP_STATE"
                or row.get("campaign_id") is not None
                or row.get("record_id") is not None
                or not isinstance(row.get("seq"), int)
                or isinstance(row.get("seq"), bool) or row["seq"] <= 0
                or not isinstance(row.get("written_at"), str)
                or _parse_semantic_timestamp(row["written_at"]) is None
                or not isinstance(payload, dict)
                or set(payload) != {"state", "controller_state_sha256"}
                or not isinstance(payload.get("state"), str)
                or re.fullmatch(r"[0-9a-f]{64}", str(
                    payload.get("controller_state_sha256"))) is None):
            return None
        expected_id = (f"akj-{row['seq']:012d}-" +
                       _discovery_content_hash(payload)[:12])
        if row.get("event_id") != expected_id:
            return None
        rows.append(row)
    portfolio, complete = rows
    portfolio_time = _parse_semantic_timestamp(portfolio["written_at"])
    complete_time = _parse_semantic_timestamp(complete["written_at"])
    if (portfolio["payload"]["state"] != "discovery_portfolio_exhausted"
            or complete["payload"]["state"] != "discovery_complete"
            or portfolio["seq"] != 73 or complete["seq"] != 74
            or complete["payload"]["controller_state_sha256"] !=
            state["state_sha256"]
            or portfolio["payload"]["controller_state_sha256"] ==
            state["state_sha256"]
            or portfolio_time is None or complete_time is None
            or not portfolio_time <= state_time <= complete_time
            or complete_time - portfolio_time > 5.0
            or complete_time > now + 5.0):
        return None
    return {
        "state": "portfolio_exhausted", "occurred_at": complete["written_at"],
        "stamp": complete_time, "state_sha256": state["state_sha256"],
        "portfolio_at": portfolio["written_at"],
        "portfolio_seq": portfolio["seq"], "complete_seq": complete["seq"],
    }


def _discovery_safe_error(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    message = value.get("message")
    if not isinstance(kind, str) or not isinstance(message, str):
        return None
    # Errors may contain source paths, but never actor prompts or output. Keep
    # this bounded because it is rendered prominently and crosses a trust seam.
    safe = " ".join(message.split())[:500]
    return {"type": kind[:100], "detail": safe}


def _discovery_native_receipt_hash_valid(body: object) -> bool:
    """Validate the producer's canonical, content-addressed receipt field."""
    if not isinstance(body, dict):
        return False
    native = body.get("receipt_sha256")
    if not isinstance(native, str) or re.fullmatch(r"[0-9a-f]{64}", native) is None:
        return False
    try:
        canonical = json.dumps(
            {key: value for key, value in body.items()
             if key != "receipt_sha256"},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(canonical).hexdigest() == native


def _discovery_completed_build_materialization(
        *, entry: Path, intent_path: Path, terminal: dict,
        contract: dict, strict_private: bool = False) -> bool:
    """Require the exact sealed terminal -> materialization receipt chain."""
    build = terminal.get("build")
    materialization_raw = (build.get("materialization_receipt")
                           if isinstance(build, dict) else None)
    materialization_sha = (build.get("materialization_sha256")
                           if isinstance(build, dict) else None)
    if (terminal.get("promotion_claim") is not False
            or not _discovery_native_receipt_hash_valid(terminal)
            or not isinstance(build, dict)
            or build.get("build_key") != entry.name
            or not isinstance(materialization_raw, str)
            or not isinstance(materialization_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", materialization_sha) is None):
        return False
    if strict_private:
        intent_snapshot = _discovery_private_snapshot(
            intent_path, max_bytes=256 * 1024)
        if intent_snapshot is None:
            return False
        intent_sha = hashlib.sha256(intent_snapshot[0]).hexdigest()
    else:
        try:
            intent_sha = hashlib.sha256(intent_path.read_bytes()).hexdigest()
        except OSError:
            return False
    if terminal.get("intent_file_sha256") != intent_sha:
        return False
    materialization_path = Path(materialization_raw)
    try:
        resolved_entry = entry.resolve(strict=True)
        resolved = materialization_path.resolve(strict=True)
        resolved.relative_to(resolved_entry)
        if strict_private:
            snapshot = _discovery_private_snapshot(
                materialization_path, max_bytes=4 * 1024 * 1024)
            if snapshot is None:
                return False
            raw, info = snapshot
            after = info
        else:
            info = materialization_path.lstat()
            if (materialization_path.is_symlink()
                    or not materialization_path.is_file()
                    or info.st_nlink != 1 or info.st_size > 4 * 1024 * 1024):
                return False
            raw = materialization_path.read_bytes()
            after = materialization_path.lstat()
    except (OSError, ValueError):
        return False
    if ((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
            != (after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_nlink)
            or hashlib.sha256(raw).hexdigest() != materialization_sha):
        return False
    materialization = _strict_json_bytes(raw)
    if (materialization is None
            or strict_private and raw != _canonical_json_bytes(materialization) + b"\n"):
        return False
    if strict_private:
        expected_keys = {
            "schema", "authority", "operation_key", "build_key", "build_contract",
            "actor_worktree", "actor_proof", "manifest_sha256",
            "production_base_authority", "instrument_authority",
            "selected_gpu_base_blobs", "applied", "anchor_commit",
            "candidate_source_commit", "candidate_source_sha256", "patch_applied",
            "production_tree", "builds", "anchor_identity", "candidate_identity",
            "anchor_source_tree_receipt", "anchor_source_tree_receipt_sha256",
            "candidate_source_tree_receipt", "candidate_source_tree_receipt_sha256",
            "source_identity_receipts", "correctness_capabilities",
            "build_identity_files", "shared_runtime", "reward_runtime_receipt",
            "reward_runtime_sha256", "promotion_claim", "receipt_sha256"}
        if (set(materialization) != expected_keys
                or materialization.get("production_base_authority") !=
                contract.get("production_base_authority")
                or materialization.get("instrument_authority") !=
                contract.get("instrument_authority")
                or materialization.get("selected_gpu_base_blobs") !=
                contract.get("selected_gpu_base_blobs")
                or materialization.get("patch_applied") is not True
                or materialization.get("production_tree") is not False
                or materialization.get("anchor_identity") != build.get("anchor_identity")
                or materialization.get("candidate_identity") !=
                build.get("candidate_identity")
                or materialization.get("reward_runtime_sha256") !=
                build.get("reward_runtime_sha256")):
            return False
    return bool(
        isinstance(materialization, dict)
        and materialization.get("schema") ==
        "epyc.autokernel.gpu_source_materialization.v1"
        and materialization.get("authority") ==
        "nonpromotable_candidate_only_discovery"
        and materialization.get("promotion_claim") is False
        and materialization.get("build_key") == entry.name
        and materialization.get("operation_key") == entry.name
        and materialization.get("manifest_sha256") ==
        contract.get("patch_bundle_sha256")
        and materialization.get("build_contract") == contract
        and _discovery_native_receipt_hash_valid(materialization)
    )


_DISCOVERY_PROCESS_INTENT_KEYS = {
    "schema", "argv", "epoch_token", "stdout_path",
    "sandbox_receipt_path", "sandbox_policy_sha256", "sandbox_token",
    "cgroup_root", "receipt_sha256",
}
_DISCOVERY_PROCESS_START_KEYS = {
    "schema", "intent_receipt_sha256", "epoch_token", "argv", "pid",
    "pgid", "process_start_ticks", "started_at", "stdout_path",
    "sandbox_receipt_path", "receipt_sha256",
}
_DISCOVERY_PROCESS_TERMINAL_KEYS = {
    "schema", "start_receipt_sha256", "disposition", "stdout_path",
    "stdout_sha256", "stdout_identity", "receipt_sha256",
}
_DISCOVERY_SANDBOX_KEYS = {
    "schema", "sandbox_id", "pid", "process_start_ticks", "euid",
    "landlock_abi", "landlock_write_rights", "landlock_handled_rights",
    "read_allowlist_enforced", "readable_roots", "readable_files",
    "executable_files", "seccomp_sha256", "blocked_syscalls", "profile",
    "network_profile", "outbound_socket_families",
    "server_socket_operations_denied", "unix_socket_creation_denied",
    "broker_socket_path", "broker_fd_inherited", "broker_peer",
    "writable_root", "writable_device_paths", "cgroup_path",
    "resource_limits", "policy_sha256", "activated_at_unix_ns",
    "argv_sha256",
}
_DISCOVERY_PROCESS_STALE_S = 900.0
_DISCOVERY_BUILD_CONTRACT_V2_KEYS = {
    "schema", "builder_schema", "deployment_config_canonical_sha256",
    "deployment_config_semantic_sha256", "supervised_build_authority",
    "supervised_build_authority_sha256", "production_base_authority",
    "instrument_authority", "patch_bundle_sha256", "patch_sha256",
    "proposal_sha256", "selected_gpu_base_blobs", "cmake_defines",
    "build_type", "parallelism", "required_targets", "build_environment",
    "toolchain", "operations_root", "build_root", "build_key",
}
_DISCOVERY_BUILD_CMAKE_DEFINES_V2 = [
    ["AMDGPU_TARGETS", "gfx90a"],
    ["CMAKE_BUILD_RPATH", "$ORIGIN;/opt/rocm/lib"],
    ["CMAKE_BUILD_RPATH_USE_ORIGIN", "ON"],
    ["CMAKE_INSTALL_RPATH", "$ORIGIN;/opt/rocm/lib"],
    ["GGML_CCACHE", "OFF"], ["GGML_HIP", "ON"],
    ["GGML_NATIVE", "OFF"],
]
_DISCOVERY_BUILD_PARALLELISM_V2 = {
    "cpu_list": None, "jobs": 1, "load_average_cap": None}
_DISCOVERY_BUILD_TARGETS_V2 = ["llama-bench", "test-backend-ops"]
_DISCOVERY_TOOLCHAIN_PROGRAMS = {"cmake", "cc", "c++", "make", "ninja", "hipcc"}
_DISCOVERY_ROCM_PROGRAMS = {
    "bin/hipcc", "llvm/bin/clang", "llvm/bin/clang++", "llvm/bin/ld.lld"}
_DISCOVERY_BUILD_ENV_KEYS = {
    "CC", "CXX", "HIP_PATH", "HOME", "LANG", "LC_ALL",
    "LD_LIBRARY_PATH", "PATH", "ROCM_PATH"}
_DISCOVERY_SANDBOX_LIMITS = {
    "address_space_bytes": 2 * (1 << 40),
    "file_size_bytes": 16 * (1 << 30), "open_files": 4096,
    "processes": 32768, "cpu_time_s": 8 * 3600,
}
_DISCOVERY_SANDBOX_BLOCKED = {
    "accept", "accept4", "bind", "bpf", "connect", "delete_module",
    "init_module", "io_uring_enter", "io_uring_register", "io_uring_setup",
    "kill", "listen", "mount", "pidfd_getfd", "pidfd_send_signal",
    "pivot_root", "process_madvise", "process_vm_readv",
    "process_vm_writev", "ptrace", "rt_sigqueueinfo", "rt_tgsigqueueinfo",
    "sendmmsg", "sendmsg", "sendto", "setns", "socket", "tgkill",
    "tkill", "umount2", "unshare", "userfaultfd",
}
_DISCOVERY_TOOL_DIGEST_CACHE: dict[
    tuple[str, int, int, int, int, int, int, int], str] = {}


def _discovery_owned_directory(path: Path, *, allow_group_write: bool = False) -> bool:
    """Validate one owner-controlled directory without following its leaf."""
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        before = path.lstat()
        fd = os.open(path, flags)
    except OSError:
        return False
    try:
        after = os.fstat(fd)
        return bool(
            stat.S_ISDIR(before.st_mode) and stat.S_ISDIR(after.st_mode)
            and before.st_uid == os.geteuid() and after.st_uid == os.geteuid()
            and not stat.S_IMODE(after.st_mode) & (0o002 if allow_group_write else 0o022)
            and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino))
    finally:
        os.close(fd)


def _discovery_proc_stat(pid: int) -> tuple[str, int, int] | None:
    """Return state, pgid and start ticks from Linux proc stat safely."""
    try:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="ascii")
        close = raw.rfind(")")
        if close < 2:
            return None
        tail = raw[close + 2:].split()
        # Tail begins with field 3 (state): pgid is field 5, ticks field 22.
        return tail[0], int(tail[2]), int(tail[19])
    except (OSError, ValueError, IndexError):
        return None


def _discovery_tool_identity(value: object) -> bool:
    if value is None:
        return True
    if (not isinstance(value, dict)
            or set(value) != {"requested", "resolved", "sha256"}
            or any(not isinstance(value.get(key), str) or not value.get(key)
                   for key in ("requested", "resolved"))
            or not Path(value["resolved"]).is_absolute()
            or re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256"))) is None):
        return False
    resolved = Path(value["resolved"])
    try:
        if Path(value["requested"]).resolve(strict=True) != resolved:
            return False
        info = resolved.lstat()
    except OSError:
        return False
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink < 1
            or info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o002):
        return False
    key = (str(resolved), info.st_dev, info.st_ino, info.st_size,
           info.st_mtime_ns, info.st_ctime_ns, info.st_mode, info.st_uid)
    digest = _DISCOVERY_TOOL_DIGEST_CACHE.get(key)
    if digest is None:
        digest, error = _sha256_file(resolved)
        if digest is None or error is not None:
            return False
        try:
            after = resolved.lstat()
        except OSError:
            return False
        after_key = (str(resolved), after.st_dev, after.st_ino, after.st_size,
                     after.st_mtime_ns, after.st_ctime_ns, after.st_mode,
                     after.st_uid)
        if after_key != key:
            return False
        if len(_DISCOVERY_TOOL_DIGEST_CACHE) >= 32:
            _DISCOVERY_TOOL_DIGEST_CACHE.clear()
        _DISCOVERY_TOOL_DIGEST_CACHE[key] = digest
    return digest == value["sha256"]


def _discovery_v2_contract_nested(contract: dict) -> bool:
    """Validate the frozen v6 builder's nested grammar before dereferencing."""
    toolchain = contract.get("toolchain")
    if (not isinstance(toolchain, dict)
            or set(toolchain) != {"schema", "programs", "rocm_root",
                                  "rocm_programs", "dynamic_environment",
                                  "toolchain_sha256"}
            or toolchain.get("schema") != "epyc.autokernel.build_toolchain.v1"):
        return False
    programs = toolchain.get("programs")
    rocm_programs = toolchain.get("rocm_programs")
    if (not isinstance(programs, dict) or set(programs) != _DISCOVERY_TOOLCHAIN_PROGRAMS
            or not all(_discovery_tool_identity(value) for value in programs.values())
            or any(programs.get(name) is None for name in ("cmake", "cc", "c++"))
            or not isinstance(rocm_programs, dict)
            or set(rocm_programs) != _DISCOVERY_ROCM_PROGRAMS
            or not all(_discovery_tool_identity(value)
                       for value in rocm_programs.values())
            or toolchain.get("dynamic_environment") != {
                "PYTHONDONTWRITEBYTECODE": "1",
                "TMPDIR": "<arm-build-dir>/.autokernel-tmp"}
            or not isinstance(toolchain.get("rocm_root"), str)
            or not Path(toolchain["rocm_root"]).is_absolute()):
        return False
    toolchain_body = dict(toolchain)
    toolchain_sha = toolchain_body.pop("toolchain_sha256", None)
    try:
        if toolchain_sha != hashlib.sha256(
                _canonical_json_bytes(toolchain_body)).hexdigest():
            return False
    except (TypeError, ValueError):
        return False
    environment = contract.get("build_environment")
    return bool(
        contract.get("build_type") == "Release"
        and contract.get("parallelism") == _DISCOVERY_BUILD_PARALLELISM_V2
        and contract.get("required_targets") == _DISCOVERY_BUILD_TARGETS_V2
        and contract.get("cmake_defines") == _DISCOVERY_BUILD_CMAKE_DEFINES_V2
        and environment == {
            "CC": programs["cc"]["resolved"],
            "CXX": programs["c++"]["resolved"],
            "HIP_PATH": "/opt/rocm", "HOME": "/home/node",
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "LD_LIBRARY_PATH":
                "/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib",
            "PATH": "/opt/rocm/bin:/usr/local/bin:/usr/bin:/bin",
            "ROCM_PATH": "/opt/rocm",
        }
    )


def _discovery_v2_state_binding(candidate: dict, row: dict,
                                contract: dict) -> bool:
    """Re-derive the state-side hashes that authenticate a v2 build request."""
    raw_b64 = candidate.get("manifest_raw_base64")
    if not isinstance(raw_b64, str):
        return False
    try:
        raw = base64.b64decode(raw_b64, validate=True)
        native = _strict_json_bytes(raw)
    except (ValueError, TypeError):
        return False
    if native is None or raw != _canonical_json_bytes(native):
        return False
    projected = dict(native)
    if (projected.pop("schema", None) != "epyc.autokernel.source-patch.v1"
            or projected.pop("patch_encoding", None) != "base64"
            or projected != candidate.get("manifest")):
        return False
    manifest_sha = hashlib.sha256(raw).hexdigest()
    patch_b64 = native.get("patch_base64")
    try:
        patch_raw = base64.b64decode(patch_b64, validate=True)
    except (ValueError, TypeError):
        return False
    proposal = candidate.get("proposal")
    try:
        proposal_sha = hashlib.sha256(_canonical_json_bytes(proposal)).hexdigest()
    except (TypeError, ValueError):
        return False
    production = contract.get("production_base_authority")
    instrument = contract.get("instrument_authority")
    declared = native.get("declared_files")
    selected = contract.get("selected_gpu_base_blobs")
    if (not isinstance(production, dict)
            or set(production) != {"path", "branch", "commit"}
            or production != {
                "path": "/mnt/raid0/llm/llama.cpp",
                "branch": "production-consolidated-v9",
                "commit": native.get("production_base_commit")}
            or not isinstance(instrument, dict)
            or set(instrument) != {"schema", "instrument_branch",
                                   "instrument_commit", "instrument_tree",
                                   "production_base_commit", "tree_listing_sha256",
                                   "authority_sha256"}
            or instrument.get("schema") !=
            "epyc.autokernel.measurement_instrument_authority.v1"
            or instrument.get("instrument_commit") != native.get("instrument_commit")
            or instrument.get("production_base_commit") !=
            native.get("production_base_commit")
            or any(re.fullmatch(r"[0-9a-f]{40}", str(instrument.get(key))) is None
                   for key in ("instrument_commit", "instrument_tree",
                               "production_base_commit"))
            or re.fullmatch(r"[0-9a-f]{64}", str(
                instrument.get("tree_listing_sha256"))) is None):
        return False
    instrument_body = dict(instrument)
    authority_sha = instrument_body.pop("authority_sha256", None)
    if authority_sha != hashlib.sha256(
            _canonical_json_bytes(instrument_body)).hexdigest():
        return False
    return bool(
        candidate.get("source_manifest_sha256") == manifest_sha
        and candidate.get("manifest_file_sha256") == manifest_sha
        and candidate.get("patch_bundle_sha256") == manifest_sha
        and row.get("source_manifest_sha256") == manifest_sha
        and contract.get("patch_bundle_sha256") == manifest_sha
        and native.get("patch_sha256") == hashlib.sha256(patch_raw).hexdigest()
        and contract.get("patch_sha256") == native.get("patch_sha256")
        and proposal_sha == row.get("proposal_sha256")
        and proposal_sha == contract.get("proposal_sha256")
        and isinstance(declared, list) and len(declared) == len(set(declared))
        and isinstance(selected, dict) and set(selected) == set(declared)
        and all(re.fullmatch(r"[0-9a-f]{64}", str(value)) is not None
                for value in selected.values()))


def _discovery_v2_git_authority(contract: dict) -> bool:
    """Re-derive v24 instrument and selected-source authority from Git."""
    stable = contract.get("supervised_build_authority")
    launch = stable.get("launch_spec") if isinstance(stable, dict) else None
    if not isinstance(launch, dict) or not isinstance(launch.get("path"), str):
        return False
    config_path = Path(launch["path"]).parent / "deployment-config.json"
    config_row = _discovery_private_snapshot(config_path, max_bytes=256 * 1024)
    config = _strict_json_bytes(config_row[0]) if config_row is not None else None
    if not isinstance(config, dict):
        return False
    production = config.get("production")
    instrument_config = config.get("instrument")
    authority = contract.get("instrument_authority")
    base = contract.get("production_base_authority")
    if (not isinstance(production, dict) or not isinstance(instrument_config, dict)
            or not isinstance(authority, dict) or not isinstance(base, dict)
            or production != {"path": base.get("path"), "branch": base.get("branch"),
                              "head": base.get("commit")}
            or instrument_config.get("branch") != authority.get("instrument_branch")
            or instrument_config.get("commit") != authority.get("instrument_commit")
            or instrument_config.get("production_ancestor") != base.get("commit")
            or not isinstance(instrument_config.get("repo_path"), str)):
        return False
    instrument_repo = Path(instrument_config["repo_path"])
    production_repo = Path(base["path"])
    def git(repo: Path, *args: str) -> bytes | None:
        try:
            result = subprocess.run(
                ("git", "-C", str(repo), *args), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                check=False, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout if result.returncode == 0 else None
    branch = git(instrument_repo, "rev-parse",
                 f"refs/heads/{authority['instrument_branch']}")
    tree = git(instrument_repo, "rev-parse",
               f"{authority['instrument_commit']}^{{tree}}")
    listing = git(instrument_repo, "ls-tree", "-r", "-z", "--full-tree",
                  authority["instrument_commit"])
    try:
        ancestor = subprocess.run(
            ("git", "-C", str(instrument_repo), "merge-base", "--is-ancestor",
             base["commit"], authority["instrument_commit"]),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ancestor = False
    valid = bool(
        branch is not None and branch.decode("ascii", "strict").strip() ==
        authority["instrument_commit"]
        and tree is not None and tree.decode("ascii", "strict").strip() ==
        authority["instrument_tree"]
        and listing is not None and hashlib.sha256(listing).hexdigest() ==
        authority["tree_listing_sha256"] and ancestor)
    if valid:
        for path, expected in contract["selected_gpu_base_blobs"].items():
            if not path.startswith("ggml/src/ggml-cuda/"):
                valid = False
                break
            production_blob = git(production_repo, "show", f"{base['commit']}:{path}")
            instrument_blob = git(
                instrument_repo, "show", f"{authority['instrument_commit']}:{path}")
            if (production_blob is None or instrument_blob != production_blob
                    or len(production_blob) > 16 * 1024 * 1024
                    or hashlib.sha256(production_blob).hexdigest() != expected):
                valid = False
                break
    return valid


def _discovery_private_snapshot(path: Path, *, max_bytes: int) -> tuple[bytes, os.stat_result] | None:
    """Take a revalidated private-file snapshot through a pinned parent.

    Build receipts are runtime authority, not convenient log markers.  They
    therefore get the same nofollow, same-owner, single-link and exact-mode
    treatment as supervisor receipts.  The parent itself must be a real,
    owner-controlled directory with no group/world write bit.
    """
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        directory_fd = os.open(path.parent, flags)
    except OSError:
        return None
    try:
        parent = os.fstat(directory_fd)
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.geteuid()
                or stat.S_IMODE(parent.st_mode) & 0o022):
            return None
        return _owned_regular_snapshot_at(
            directory_fd, path.name, max_bytes=max_bytes, expected_mode=0o600)
    finally:
        os.close(directory_fd)


def _discovery_private_json(path: Path, *, schema: str,
                            keys: set[str], max_bytes: int = 256 * 1024,
                            sealed: bool = True) -> tuple[dict, bytes, os.stat_result] | None:
    snapshot = _discovery_private_snapshot(path, max_bytes=max_bytes)
    if snapshot is None:
        return None
    raw, info = snapshot
    value = _strict_json_bytes(raw)
    if (value is None or set(value) != keys or value.get("schema") != schema
            or raw != _canonical_json_bytes(value) + b"\n"
            or sealed and not _discovery_native_receipt_hash_valid(value)):
        return None
    return value, raw, info


def _discovery_process_identity_live(start: dict, sandbox: dict) -> bool:
    """Bind a receipt identity to the same live PID and nested cgroup.

    This is deliberately only the final conjunct.  A process-list observation
    can never create build liveness without the sealed intent/start/sandbox
    chain validated by the caller.
    """
    pid = start.get("pid")
    ticks = start.get("process_start_ticks")
    pgid = start.get("pgid")
    if (not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0
            or not isinstance(ticks, int) or isinstance(ticks, bool) or ticks <= 0
            or not isinstance(pgid, int) or isinstance(pgid, bool) or pgid <= 0):
        return False
    try:
        proc_stat = _discovery_proc_stat(pid)
        if proc_stat is None:
            return False
        process_state, observed_pgid, observed_ticks = proc_stat
        memberships = (Path("/proc") / str(pid) / "cgroup").read_text(
            encoding="ascii").splitlines()
    except (OSError, ProcessLookupError, ValueError, IndexError):
        return False
    cgroup = sandbox.get("cgroup_path")
    if (observed_ticks != ticks or observed_pgid != pgid or process_state == "Z"
            or not isinstance(cgroup, str)
            or not cgroup.startswith("/sys/fs/cgroup/")):
        return False
    relative = cgroup.removeprefix("/sys/fs/cgroup")
    cgroup_path = Path(cgroup)
    try:
        members = (cgroup_path / "cgroup.procs").read_text(
            encoding="ascii").split()
    except OSError:
        return False
    return (not cgroup_path.is_symlink() and cgroup_path.is_dir()
            and f"0::{relative}" in memberships and str(pid) in members)


def _discovery_process_receipt_identity(start: object) -> bool:
    if not isinstance(start, dict):
        return False
    return all(isinstance(start.get(key), int)
               and not isinstance(start.get(key), bool)
               and start[key] > 0
               for key in ("pid", "pgid", "process_start_ticks"))


def _discovery_v2_sandbox(value: dict, *, intent: dict, start: dict,
                          writable_root: Path) -> bool:
    argv = start.get("argv")
    pid = start.get("pid")
    ticks = start.get("process_start_ticks")
    expected_cgroup = str(Path(str(intent.get("cgroup_root")),
                               f"autokernel-{pid}-{intent.get('sandbox_token')}"))
    try:
        argv_sha = hashlib.sha256(json.dumps(
            argv, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return False
    abi = value.get("landlock_abi")
    expected_rights = 8178 | (1 << 13 if isinstance(abi, int) and abi >= 2 else 0)
    if isinstance(abi, int) and abi >= 3:
        expected_rights |= 1 << 14
    policy_document = {
        "sandbox_id": "autokernel.execution.sandbox/landlock-seccomp-cgroup-v2",
        "profile": "candidate_default_v1",
        "writable_root": str(writable_root),
        "cgroup_root": intent.get("cgroup_root"),
        "writable_device_paths": [], "readable_roots": [],
        "readable_files": [], "executable_files": [],
        "broker_socket_path": None, "broker_peer_pid": None,
        "broker_peer_start_ticks": None, "read_allowlist_enforced": False,
        "network_profile": "deny_all",
        "blocked_syscalls": sorted(_DISCOVERY_SANDBOX_BLOCKED),
        "deny_unix_socket_creation": False,
        "resource_limits": _DISCOVERY_SANDBOX_LIMITS,
    }
    policy_sha = hashlib.sha256(
        _canonical_json_bytes(policy_document)).hexdigest()
    started_epoch = (_parse_semantic_timestamp(start.get("started_at"))
                     if isinstance(start.get("started_at"), str) else None)
    activated_ns = value.get("activated_at_unix_ns")
    return bool(
        set(value) == _DISCOVERY_SANDBOX_KEYS
        and value.get("schema") == "epyc.autokernel.sandbox_receipt.v2"
        and value.get("sandbox_id") ==
        "autokernel.execution.sandbox/landlock-seccomp-cgroup-v2"
        and value.get("pid") == pid
        and value.get("process_start_ticks") == ticks
        and value.get("euid") == os.geteuid() and value.get("euid") != 0
        and value.get("policy_sha256") == intent.get("sandbox_policy_sha256")
        and value.get("policy_sha256") == policy_sha
        and value.get("argv_sha256") == argv_sha
        and value.get("cgroup_path") == expected_cgroup
        and value.get("writable_root") == str(writable_root)
        and value.get("writable_device_paths") == []
        and value.get("profile") == "candidate_default_v1"
        and value.get("network_profile") == "deny_all"
        and value.get("outbound_socket_families") == []
        and value.get("server_socket_operations_denied") ==
        ["bind", "listen", "accept", "accept4"]
        and value.get("unix_socket_creation_denied") is False
        and value.get("broker_fd_inherited") is False
        and value.get("broker_socket_path") is None
        and value.get("broker_peer") is None
        and value.get("read_allowlist_enforced") is False
        and value.get("readable_roots") == []
        and value.get("readable_files") == []
        and value.get("executable_files") == []
        and value.get("resource_limits") == _DISCOVERY_SANDBOX_LIMITS
        and value.get("blocked_syscalls") == sorted(_DISCOVERY_SANDBOX_BLOCKED)
        and value.get("seccomp_sha256") ==
        "80658aa1b897a70b445c4449ba3e5fa21db7b31388833cabbf9fb14a5e782fb7"
        and isinstance(activated_ns, int) and not isinstance(activated_ns, bool)
        and started_epoch is not None
        and abs(activated_ns / 1_000_000_000 - started_epoch) <= 5.0
        and isinstance(abi, int) and not isinstance(abi, bool) and abi >= 1
        and value.get("landlock_write_rights") == expected_rights
        and value.get("landlock_handled_rights") == expected_rights
    )


def _discovery_v2_process_receipts(
        *, prefix: Path, attempt_root: Path, writable_root: Path,
        expected_argv: list[str], expected_cgroup_root: str, require_live: bool,
        now: float) -> dict | None:
    intent_path = prefix.with_name(prefix.name + "-process-intent.json")
    start_path = prefix.with_name(prefix.name + "-process-start.json")
    terminal_path = prefix.with_name(prefix.name + "-process-terminal.json")
    sandbox_path = prefix.with_name(prefix.name + "-sandbox.json")
    stream_path = prefix.with_name(prefix.name + ".stream")
    intent_row = _discovery_private_json(
        intent_path, schema="epyc.autokernel.owned_process_intent.v1",
        keys=_DISCOVERY_PROCESS_INTENT_KEYS)
    start_row = _discovery_private_json(
        start_path, schema="epyc.autokernel.owned_process_start.v1",
        keys=_DISCOVERY_PROCESS_START_KEYS)
    if intent_row is None or start_row is None:
        return None
    intent, intent_raw, _ = intent_row
    start, start_raw, _ = start_row
    if (not _discovery_process_receipt_identity(start)
            or intent.get("argv") != expected_argv or start.get("argv") != expected_argv
            or intent.get("cgroup_root") != expected_cgroup_root
            or start.get("intent_receipt_sha256") != hashlib.sha256(intent_raw).hexdigest()
            or start.get("epoch_token") != intent.get("epoch_token")
            or start.get("stdout_path") != str(stream_path)
            or intent.get("stdout_path") != str(stream_path)
            or start.get("sandbox_receipt_path") != str(sandbox_path)
            or intent.get("sandbox_receipt_path") != str(sandbox_path)
            or not isinstance(intent.get("epoch_token"), str)
            or re.fullmatch(r"[0-9a-f]{64}", intent["epoch_token"]) is None
            or not isinstance(intent.get("sandbox_token"), str)
            or re.fullmatch(r"[0-9a-f]{16}", intent["sandbox_token"]) is None
            or not isinstance(intent.get("sandbox_policy_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", intent["sandbox_policy_sha256"]) is None):
        return None
    sandbox_row = _discovery_private_json(
        sandbox_path, schema="epyc.autokernel.sandbox_receipt.v2",
        keys=_DISCOVERY_SANDBOX_KEYS, sealed=False)
    if sandbox_row is None:
        return None
    sandbox, _, _ = sandbox_row
    if not _discovery_v2_sandbox(
            sandbox, intent=intent, start=start, writable_root=writable_root):
        return None
    stream_row = _discovery_private_snapshot(stream_path, max_bytes=16 * 1024 * 1024)
    if stream_row is None:
        return None
    stream_raw, stream_info = stream_row
    started_at = start.get("started_at")
    started_epoch = (_parse_semantic_timestamp(started_at)
                     if isinstance(started_at, str) else None)
    if (started_epoch is None or started_epoch > now + 5.0
            or require_live and started_epoch < now - 24 * 3600
            or stream_info.st_mtime < started_epoch - 5.0):
        return None
    if require_live:
        if terminal_path.exists() or terminal_path.is_symlink():
            return None
        if not stream_raw or not _discovery_process_identity_live(start, sandbox):
            return None
        progress = [int(value) for value in re.findall(
            rb"\[\s*([0-9]{1,3})%\]", stream_raw)]
        progress_percent = progress[-1] if progress and progress[-1] <= 100 else None
        return {"started_at": started_at, "pid": start["pid"],
                "process_start_ticks": start["process_start_ticks"],
                "progress_percent": progress_percent,
                "hip_compile": b"Building HIP object" in stream_raw,
                "stream_size": len(stream_raw),
                "progress_at": datetime.fromtimestamp(
                    stream_info.st_mtime, timezone.utc
                ).isoformat().replace("+00:00", "Z"),
                "stream_stale": now - stream_info.st_mtime > _DISCOVERY_PROCESS_STALE_S}
    terminal_row = _discovery_private_json(
        terminal_path, schema="epyc.autokernel.owned_process_terminal.v2",
        keys=_DISCOVERY_PROCESS_TERMINAL_KEYS)
    if terminal_row is None:
        return None
    terminal, _, terminal_info = terminal_row
    disposition = terminal.get("disposition")
    stdout_identity = terminal.get("stdout_identity")
    expected_identity = {
        "device": stream_info.st_dev, "inode": stream_info.st_ino,
        "mode": stat.S_IMODE(stream_info.st_mode),
        "nlink": stream_info.st_nlink, "uid": stream_info.st_uid,
        "size": stream_info.st_size, "mtime_ns": stream_info.st_mtime_ns,
        "ctime_ns": stream_info.st_ctime_ns,
    }
    if (terminal.get("start_receipt_sha256") != hashlib.sha256(start_raw).hexdigest()
            or terminal.get("stdout_path") != str(stream_path)
            or terminal.get("stdout_sha256") != hashlib.sha256(stream_raw).hexdigest()
            or stdout_identity != expected_identity
            or not isinstance(disposition, dict)
            or set(disposition) != {"argv", "pid", "pgid", "exit_code",
                                    "timed_out", "signals_sent", "verified_dead",
                                    "duration_s", "started_at", "sandbox_receipt",
                                    "sandbox_teardown"}
            or disposition.get("argv") != expected_argv
            or disposition.get("pid") != start.get("pid")
            or disposition.get("pgid") != start.get("pgid")
            or disposition.get("started_at") != started_at
            or disposition.get("exit_code") != 0
            or disposition.get("timed_out") is not False
            or disposition.get("signals_sent") != []
            or disposition.get("verified_dead") is not True
            or isinstance(disposition.get("duration_s"), bool)
            or not isinstance(disposition.get("duration_s"), (int, float))
            or not math.isfinite(disposition["duration_s"])
            or disposition["duration_s"] < 0
            or terminal_info.st_mtime < started_epoch - 5.0
            or terminal_info.st_mtime < stream_info.st_mtime - 5.0
            or disposition.get("sandbox_receipt") != sandbox):
        return None
    teardown = disposition.get("sandbox_teardown")
    if (not isinstance(teardown, dict)
            or set(teardown) != {"cgroup_path", "verified_empty", "removed",
                                 "descendants_killed"}
            or teardown.get("cgroup_path") != sandbox.get("cgroup_path")
            or teardown.get("verified_empty") is not True
            or teardown.get("removed") is not True
            or Path(str(sandbox.get("cgroup_path"))).exists()
            or Path(str(sandbox.get("cgroup_path"))).is_symlink()):
        return None
    return {"started_at": started_at, "pid": start["pid"],
            "process_start_ticks": start["process_start_ticks"],
            "completed": True,
            "completed_at": datetime.fromtimestamp(
                terminal_info.st_mtime, timezone.utc
            ).isoformat().replace("+00:00", "Z")}


def _discovery_v2_lock_identity(path: Path, value: object, *,
                                require_held: bool = True) -> bool:
    if (not isinstance(value, dict)
            or set(value) != {"device", "inode", "path", "uid"}
            or value.get("path") != str(path)
            or value.get("uid") != os.geteuid()):
        return False
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0)
    file_flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
        file_flags |= os.O_NOFOLLOW
    directory_fd = fd = None
    try:
        directory_fd = os.open(path.parent, directory_flags)
        fd = os.open(path.name, file_flags, dir_fd=directory_fd)
        info = os.fstat(fd)
        named = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or (info.st_dev, info.st_ino) != (named.st_dev, named.st_ino)
                or value.get("device") != info.st_dev
                or value.get("inode") != info.st_ino):
            return False
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            after = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
            return (require_held and
                    (info.st_dev, info.st_ino) == (after.st_dev, after.st_ino))
        fcntl.flock(fd, fcntl.LOCK_UN)
        after = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        return (not require_held and
                (info.st_dev, info.st_ino) == (after.st_dev, after.st_ino))
    except OSError:
        return False
    finally:
        if fd is not None:
            os.close(fd)
        if directory_fd is not None:
            os.close(directory_fd)


def _discovery_stable_supervised_authority(value: dict) -> dict:
    return {
        "schema": "epyc.autokernel.supervised_launch_authority.v2",
        "launch_spec": value.get("launch_spec"),
        "death_ledger": value.get("death_ledger"),
        "spec_sha256": value.get("spec_sha256"),
        "deployment_config_canonical_sha256":
            value.get("deployment_config_canonical_sha256"),
        "deployment_config_semantic_sha256":
            value.get("deployment_config_semantic_sha256"),
    }


def _discovery_authority_file(value: object, *, hashed: bool,
                              max_bytes: int) -> tuple[bytes, os.stat_result] | None:
    keys = {"device", "inode", "mode", "nlink", "path", "uid"}
    if hashed:
        keys.add("sha256")
    if (not isinstance(value, dict) or set(value) != keys
            or not isinstance(value.get("path"), str)
            or not Path(value["path"]).is_absolute()
            or value.get("uid") != os.geteuid()
            or value.get("mode") != 0o600 or value.get("nlink") != 1):
        return None
    row = _discovery_private_snapshot(Path(value["path"]), max_bytes=max_bytes)
    if row is None:
        return None
    raw, info = row
    if (value.get("device"), value.get("inode"), value.get("mode"),
            value.get("nlink"), value.get("uid")) != (
            info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode),
            info.st_nlink, info.st_uid):
        return None
    if hashed and value.get("sha256") != hashlib.sha256(raw).hexdigest():
        return None
    return raw, info


def _discovery_authority_ledger_live(*, require_live: bool,
                                     row_count: int) -> bool | None:
    """Classify only the producer's exact live/terminal ledger lengths."""
    if row_count == 2:
        return True
    if row_count == 5 and not require_live:
        return False
    return None


def _discovery_authority_cgroup(authority: dict, *,
                                require_live: bool = True) -> dict | None:
    """Resolve the controller cgroup from its exact sealed ledger record."""
    if (authority.get("schema") != "epyc.autokernel.supervised_build_authority.v2"
            or not _supervisor_process(authority.get("controller"), child=True)
            or not _supervisor_process(authority.get("supervisor"), child=False)
            or re.fullmatch(r"[0-9a-f]{64}", str(
                authority.get("ledger_child_started_record_sha256"))) is None):
        return None
    launch = _discovery_authority_file(
        authority.get("launch_spec"), hashed=True, max_bytes=2 * 1024 * 1024)
    ledger = _discovery_authority_file(
        authority.get("death_ledger"), hashed=False, max_bytes=256 * 1024)
    if launch is None or ledger is None:
        return None
    spec = _strict_json_bytes(launch[0])
    spec_keys = {"schema", "kind", "runtime_root", "runtime_root_identity",
                 "deployment_config", "validate_only", "canary", "python",
                 "restart_policy", "termination_policy", "execution_closure",
                 "execution_modules", "graph_execution_modules", "cgroup"}
    runtime_root = Path(str(authority["launch_spec"]["path"])).parent
    try:
        runtime_info = runtime_root.lstat()
    except OSError:
        return None
    if (spec is None or launch[0] != _canonical_json_bytes(spec) + b"\n"
            or set(spec) != spec_keys
            or spec.get("schema") != "epyc.autokernel.discovery_supervisor_spec.v4"
            or spec.get("kind") != "deployment" or spec.get("validate_only") is not False
            or spec.get("runtime_root") != str(runtime_root)
            or spec.get("runtime_root_identity") != _stat_identity(
                runtime_info, sized=False)
            or spec.get("restart_policy") != {"max_restarts": 0,
                                               "delay_seconds": 2.0}
            or authority.get("spec_sha256") != hashlib.sha256(
                _canonical_json_bytes(spec)).hexdigest()):
        return None
    deployment = spec.get("deployment_config")
    if (not isinstance(deployment, dict)
            or set(deployment) != {"source_path", "source_identity", "runtime_leaf",
                                   "canonical_sha256", "semantic_sha256",
                                   "canonical_size", "identity"}
            or deployment.get("runtime_leaf") != "deployment-config.json"
            or deployment.get("canonical_sha256") !=
            authority.get("deployment_config_canonical_sha256")
            or deployment.get("semantic_sha256") !=
            authority.get("deployment_config_semantic_sha256")):
        return None
    config_row = _discovery_private_snapshot(
        runtime_root / "deployment-config.json", max_bytes=256 * 1024)
    if (config_row is None
            or deployment.get("identity") != _stat_identity(config_row[1], sized=True)
            or deployment.get("canonical_size") != len(config_row[0])
            or deployment.get("canonical_sha256") !=
            hashlib.sha256(config_row[0]).hexdigest()):
        return None
    config_value = _strict_json_bytes(config_row[0])
    source_path = Path(str(deployment.get("source_path")))
    source_row = _owned_public_snapshot(source_path, max_bytes=256 * 1024)
    if (config_value is None or source_row is None
            or _supervisor_launch_spec(
                launch[0], runtime_root=runtime_root, runtime_info=runtime_info,
                config_path=source_path, config=config_value,
                config_source=source_row, config_copy=config_row) is None):
        return None
    expected_cgroup_name = "epyc-autokernel-" + hashlib.sha256(
        str(runtime_root).encode("utf-8")).hexdigest()[:24]
    if spec.get("cgroup") != {"base": "/sys/fs/cgroup",
                              "name": expected_cgroup_name}:
        return None
    raw = ledger[0]
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError:
        return None
    authority_live = _discovery_authority_ledger_live(
        require_live=require_live, row_count=len(lines))
    if authority_live is None or not raw.endswith(b"\n"):
        return None
    if (len(lines) == 5 and _supervisor_ledger(
            raw, spec_sha256=authority["spec_sha256"],
            session_name="ak-" + authority["spec_sha256"][:24],
            runtime_root=runtime_root) is None):
        return None
    previous = None
    previous_time = None
    found = None
    rows = []
    for sequence, line in enumerate(lines, 1):
        row = _strict_json_bytes(line.encode("ascii"))
        if (row is None or set(row) != {"event", "payload", "previous_sha256",
                                       "record_sha256", "schema", "sequence",
                                       "written_at"}
                or row.get("schema") != "epyc.autokernel.discovery_supervisor_ledger.v2"
                or row.get("sequence") != sequence
                or row.get("previous_sha256") != previous
                or line.encode("ascii") != _canonical_json_bytes(row)
                or not isinstance(row.get("payload"), dict)
                or _parse_semantic_timestamp(row.get("written_at")) is None):
            return None
        body = dict(row)
        digest = body.pop("record_sha256", None)
        if (not isinstance(digest, str)
                or digest != hashlib.sha256(_canonical_json_bytes(body)).hexdigest()):
            return None
        written = _parse_semantic_timestamp(row["written_at"])
        if previous_time is not None and written < previous_time:
            return None
        if digest == authority["ledger_child_started_record_sha256"]:
            found = row
        rows.append(row)
        previous = digest
        previous_time = written
    if (len(rows) < 2 or [row["event"] for row in rows[:2]] !=
            ["supervisor_started", "child_started"]
            or found is not rows[1]):
        return None
    started = rows[0]["payload"]
    if (set(started) != {"spec_sha256", "session_name", "supervisor", "tmux"}
            or started.get("spec_sha256") != authority["spec_sha256"]
            or started.get("session_name") != "ak-" + authority["spec_sha256"][:24]
            or started.get("supervisor") != authority["supervisor"]
            or not _supervisor_tmux(started.get("tmux"), authority["supervisor"])):
        return None
    payload = found["payload"]
    cgroup = payload.get("cgroup")
    if (set(payload) != {"restart_count", "child", "stdout", "stderr", "cgroup"}
            or payload.get("restart_count") != 0
            or payload.get("child") != authority["controller"]
            or payload.get("stdout") != str(runtime_root / "controller.stdout.log")
            or payload.get("stderr") != str(runtime_root / "controller.stderr.log")
            or not isinstance(cgroup, dict)
            or set(cgroup) != {"path", "dev", "ino", "uid", "mode", "nlink"}
            or cgroup.get("uid") != os.geteuid() or cgroup.get("mode") != 0o700
            or not isinstance(cgroup.get("path"), str)
            or not str(cgroup["path"]).startswith("/sys/fs/cgroup/")):
        return None
    expected_cgroup_path = (
        f"/sys/fs/cgroup/{expected_cgroup_name}-{authority['supervisor']['pid']}-0")
    if cgroup["path"] != expected_cgroup_path:
        return None
    # A completed build transaction does not imply that its owning discovery
    # controller has stopped.  v25 seals and releases the build cache entry,
    # then continues correctness and measurement under the same supervised
    # controller.  The two-row ledger is therefore still a live authority
    # prefix even when the caller is validating a terminal build.  Conversely,
    # a five-row ledger is historical and must prove both identities dead and
    # the controller cgroup removed.  Never infer this lifecycle from the
    # build terminal alone; the exact supervisor ledger shape owns the mode.
    if authority_live:
        try:
            info = Path(cgroup["path"]).lstat()
        except OSError:
            return None
        # A live nested child cgroup increments its parent's directory link count;
        # device/inode/owner/mode remain the stable authority identity.
        if (not stat.S_ISDIR(info.st_mode) or Path(cgroup["path"]).is_symlink()
                or (info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode))
                != (cgroup["dev"], cgroup["ino"], cgroup["uid"], cgroup["mode"])
                or info.st_nlink < cgroup["nlink"]):
            return None
    if not authority_live:
        cgroup_path = Path(cgroup["path"])
        if cgroup_path.exists() or cgroup_path.is_symlink():
            return None
        for process in (authority["controller"], authority["supervisor"]):
            observed = _discovery_proc_stat(process["pid"])
            if observed is not None and observed[2] == process["start_ticks"]:
                return None
        return cgroup
    controller = authority["controller"]
    supervisor = authority["supervisor"]
    try:
        memberships = (Path("/proc") / str(controller["pid"]) / "cgroup").read_text(
            encoding="ascii").splitlines()
        members = (Path(cgroup["path"]) / "cgroup.procs").read_text(
            encoding="ascii").split()
    except OSError:
        return None
    relative = cgroup["path"].removeprefix("/sys/fs/cgroup")
    host = os.uname().nodename
    host_sha = hashlib.sha256(host.encode("utf-8")).hexdigest()
    supervisor_proc = _discovery_proc_stat(supervisor["pid"])
    if (f"0::{relative}" not in memberships or str(controller["pid"]) not in members
            or supervisor_proc is None or supervisor_proc[0] == "Z"
            or supervisor_proc[2] != supervisor["start_ticks"]
            or any(process.get("boot_id") != controller["boot_id"]
                   or process.get("host") != host
                   or process.get("host_id_source") != "kernel-hostname"
                   or process.get("host_id_sha256") != host_sha
                   for process in (authority["controller"], authority["supervisor"]))):
        return None
    return cgroup


_DISCOVERY_V2_TERMINAL_BUILD_KEYS = {
    "anchor_build", "anchor_correctness_binary",
    "anchor_correctness_binary_sha256",
    "anchor_correctness_capability_receipt",
    "anchor_correctness_capability_sha256", "anchor_identity",
    "anchor_loader_dir", "anchor_source_tree_receipt",
    "anchor_source_tree_sha256", "build_key", "candidate_build",
    "candidate_correctness_binary", "candidate_correctness_binary_sha256",
    "candidate_correctness_capability_receipt",
    "candidate_correctness_capability_sha256", "candidate_identity",
    "candidate_loader_dir", "candidate_source_tree_receipt",
    "candidate_source_tree_sha256", "common_loader_dir",
    "materialization_receipt", "materialization_sha256",
    "measurement_binary", "reward_runtime_sha256", "teardown_receipt",
    "teardown_sha256",
}


def _discovery_v2_terminal_build_exact(build: object, build_key: str) -> bool:
    return bool(isinstance(build, dict)
                and set(build) == _DISCOVERY_V2_TERMINAL_BUILD_KEYS
                and build.get("build_key") == build_key)


def _discovery_v2_terminal_complete(entry: Path, attempt: Path, *,
                                    intent_raw: bytes, owner_raw: bytes,
                                    contract: dict, candidate_id: str) -> bool:
    row = _discovery_private_json(
        entry / "terminal.json",
        schema="epyc.autokernel.gpu_source_build_terminal.v2",
        keys={"schema", "build_key", "intent_file_sha256", "state", "build",
              "attempt_name", "attempt_owner_sha256", "process_closure_sha256",
              "artifact_epoch", "promotion_claim", "receipt_sha256"},
        max_bytes=2 * 1024 * 1024)
    if row is None:
        return False
    terminal = row[0]
    epoch = terminal.get("artifact_epoch")
    build = terminal.get("build")
    if (terminal.get("build_key") != entry.name
            or terminal.get("intent_file_sha256") != hashlib.sha256(intent_raw).hexdigest()
            or terminal.get("state") != "complete"
            or terminal.get("attempt_name") != attempt.name
            or terminal.get("attempt_owner_sha256") != hashlib.sha256(owner_raw).hexdigest()
            or terminal.get("promotion_claim") is not False
            or not _discovery_v2_terminal_build_exact(build, entry.name)
            or not isinstance(epoch, dict)
            or set(epoch) != {"schema", "attempt", "attempt_owner_sha256",
                              "attempt_recovery", "prior_recoveries",
                              "process_closure", "materialization_sha256",
                              "artifact_receipts", "artifact_epoch_sha256"}
            or epoch.get("schema") != "epyc.autokernel.build_artifact_epoch.v1"
            or epoch.get("attempt") != attempt.name
            or epoch.get("attempt_owner_sha256") != hashlib.sha256(owner_raw).hexdigest()
            or epoch.get("attempt_recovery") is not None
            # The v24 adapter deliberately accepts only the first immutable
            # attempt.  Later attempts carry recovery authority whose full
            # producer grammar is not part of this visibility contract; do not
            # accept a merely self-hashed recovery projection.
            or attempt.name != "attempt-000001"
            or epoch.get("prior_recoveries") != []):
        return False
    epoch_body = dict(epoch)
    epoch_sha = epoch_body.pop("artifact_epoch_sha256", None)
    closure = epoch.get("process_closure")
    if (not isinstance(closure, dict)
            or set(closure) != {"schema", "entries", "proofs",
                                "require_terminals", "closure_sha256"}
            or closure.get("require_terminals") is not True):
        return False
    closure_body = dict(closure)
    closure_sha = closure_body.pop("closure_sha256", None)
    def closure_rows(root: Path, *, limit: int,
                     private: bool) -> list[dict] | None:
        if not _discovery_owned_directory(root):
            return None
        rows = []
        try:
            paths = sorted(root.iterdir(), key=lambda path: path.name)
        except OSError:
            return None
        if len(paths) > 128:
            return None
        for path in paths:
            snapshot = (_discovery_private_snapshot(path, max_bytes=limit)
                        if private else
                        _owned_public_snapshot(path, max_bytes=limit))
            if snapshot is None:
                return None
            raw, info = snapshot
            rows.append({"name": path.name,
                         "sha256": hashlib.sha256(raw).hexdigest(),
                         "identity": {
                             "device": info.st_dev, "inode": info.st_ino,
                             "mode": stat.S_IMODE(info.st_mode),
                             "nlink": info.st_nlink, "uid": info.st_uid,
                             "size": info.st_size, "mtime_ns": info.st_mtime_ns,
                             "ctime_ns": info.st_ctime_ns}})
        return rows
    expected_logs = closure_rows(
        attempt / "logs", limit=16 * 1024 * 1024, private=True)
    expected_receipts = closure_rows(
        attempt / "receipts", limit=4 * 1024 * 1024, private=False)
    proofs = closure.get("proofs")
    if (expected_logs is None or expected_receipts is None
            or closure.get("entries") != expected_logs
            or epoch.get("artifact_receipts") != expected_receipts
            or not isinstance(proofs, list) or len(proofs) != 4):
        return False
    expected_proof_paths = set()
    for name in ("akc-anchor", candidate_id):
        for phase in ("build", "configure"):
            base = attempt / "logs" / f"{name}.log.{phase}"
            expected_proof_paths.add((
                str(base.with_name(base.name + "-process-intent.json")),
                str(base.with_name(base.name + "-process-start.json")),
                str(base.with_name(base.name + "-process-terminal.json"))))
    observed_proof_paths = set()
    for proof in proofs:
        sandbox = proof.get("sandbox") if isinstance(proof, dict) else None
        if (not isinstance(proof, dict)
                or set(proof) != {"intent", "start", "terminal", "state", "sandbox"}
                or proof.get("state") != "terminal_verified_dead"
                or not isinstance(sandbox, dict)
                or set(sandbox) != {"receipt", "receipt_present", "pid",
                                    "process_start_ticks", "cgroup_path",
                                    "cgroup_state", "state", "reason"}
                or sandbox.get("receipt_present") is not True
                or sandbox.get("cgroup_state") != "absent"
                or sandbox.get("state") != "activation_dead_cgroup_drained"
                or Path(str(sandbox.get("cgroup_path"))).exists()
                or Path(str(sandbox.get("cgroup_path"))).is_symlink()):
            return False
        observed_proof_paths.add(
            (proof.get("intent"), proof.get("start"), proof.get("terminal")))
    if observed_proof_paths != expected_proof_paths:
        return False
    return bool(
        epoch_sha == hashlib.sha256(_canonical_json_bytes(epoch_body)).hexdigest()
        and closure_sha == hashlib.sha256(
            _canonical_json_bytes(closure_body)).hexdigest()
        and terminal.get("process_closure_sha256") == closure_sha
        and epoch.get("materialization_sha256") == build.get("materialization_sha256")
        and _discovery_completed_build_materialization(
            entry=entry, intent_path=entry / "intent.json", terminal=terminal,
            contract=contract, strict_private=True))


def _discovery_v2_build_observation(
        operations_root: Path, state: dict | None,
        config_sha256: object) -> tuple[dict | None, bool]:
    """Project one v2 append-only build attempt, or fail closed.

    The boolean says a state-bound v2 contract was found.  Callers must not
    fall back to legacy filename heuristics for that contract if any receipt in
    its authority chain is invalid.
    """
    inflight = state.get("inflight") if isinstance(state, dict) else None
    candidate = inflight.get("candidate") if isinstance(inflight, dict) else None
    row = inflight.get("row") if isinstance(inflight, dict) else None
    if (not isinstance(candidate, dict) or not isinstance(row, dict)
            or not isinstance(config_sha256, str)):
        return None, False
    manifest_sha = candidate.get("source_manifest_sha256")
    proposal_sha = row.get("proposal_sha256")
    manifest = candidate.get("manifest")
    candidate_id = manifest.get("candidate_id") if isinstance(manifest, dict) else None
    campaign_id = manifest.get("campaign_id") if isinstance(manifest, dict) else None
    if (not isinstance(manifest_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is None
            or not isinstance(proposal_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", proposal_sha) is None
            or not isinstance(candidate_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", candidate_id) is None
            or not isinstance(campaign_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", campaign_id) is None):
        return None, False
    entries = operations_root / "build-cache" / "entries"
    if not _discovery_owned_directory(entries):
        return None, False
    try:
        children = sorted(entries.iterdir(), key=lambda path: path.name)[:129]
    except OSError:
        return None, False
    if len(children) > 128:
        return None, True
    matches: list[tuple[Path, dict, dict, bytes]] = []
    v2_seen = False
    for entry in children:
        if (entry.is_symlink() or not entry.is_dir()
                or re.fullmatch(r"[0-9a-f]{64}", entry.name) is None):
            continue
        if ((entry / "attempts").exists()
                or (entry / "transaction-owner.json").exists()):
            v2_seen = True
        intent_row = _discovery_private_json(
            entry / "intent.json",
            schema="epyc.autokernel.gpu_source_build_intent.v1",
            keys={"schema", "authority", "build_key", "build_contract",
                  "promotion_claim", "request_key", "receipt_sha256"})
        if intent_row is None:
            continue
        intent, _, _ = intent_row
        contract = intent.get("build_contract")
        if (not isinstance(contract, dict)
                or contract.get("schema") != "epyc.autokernel.gpu_source_build_key.v2"):
            continue
        v2_seen = True
        if (intent.get("authority") == "nonpromotable_candidate_only_discovery"
                and intent.get("promotion_claim") is False
                and intent.get("build_key") == entry.name
                and contract.get("build_key") == entry.name
                and contract.get("patch_bundle_sha256") == manifest_sha
                and contract.get("proposal_sha256") == proposal_sha
                and contract.get("deployment_config_semantic_sha256") == config_sha256):
            matches.append((entry, contract, intent, intent_row[1]))
    if not matches:
        return None, v2_seen
    if len(matches) != 1:
        return None, True
    entry, contract, intent, intent_raw = matches[0]
    entry_terminal_present = ((entry / "terminal.json").exists()
                              or (entry / "terminal.json").is_symlink())
    if (set(contract) != _DISCOVERY_BUILD_CONTRACT_V2_KEYS
            or contract.get("builder_schema") !=
            "epyc.autokernel.static_gpu_source_builder.v6"
            or contract.get("operations_root") != str(operations_root)
            or not _discovery_v2_contract_nested(contract)
            or not _discovery_v2_state_binding(candidate, row, contract)
            or not _discovery_v2_git_authority(contract)
            or not isinstance(contract.get("build_root"), str)
            or not Path(contract["build_root"]).is_absolute()
            or not isinstance(contract.get("deployment_config_canonical_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}",
                            contract["deployment_config_canonical_sha256"]) is None):
        return None, True
    contract_preimage = dict(contract)
    contract_preimage.pop("build_key", None)
    try:
        expected_key = hashlib.sha256(
            _canonical_json_bytes(contract_preimage)).hexdigest()
    except (TypeError, ValueError):
        return None, True
    if expected_key != entry.name:
        return None, True
    stable_authority = contract.get("supervised_build_authority")
    if (not isinstance(stable_authority, dict)
            or set(stable_authority) != {"schema", "launch_spec", "death_ledger",
                                         "spec_sha256",
                                         "deployment_config_canonical_sha256",
                                         "deployment_config_semantic_sha256"}
            or stable_authority.get("schema") !=
            "epyc.autokernel.supervised_launch_authority.v2"
            or contract.get("supervised_build_authority_sha256") !=
            hashlib.sha256(_canonical_json_bytes(stable_authority)).hexdigest()):
        return None, True
    request_preimage = {
        "schema": "epyc.autokernel.gpu_source_build_request.v2",
        "deployment_config_canonical_sha256":
            contract["deployment_config_canonical_sha256"],
        "deployment_config_semantic_sha256":
            contract["deployment_config_semantic_sha256"],
        "supervised_build_authority_sha256":
            contract["supervised_build_authority_sha256"],
        "production_base_authority": contract["production_base_authority"],
        "instrument_authority": contract["instrument_authority"],
        "patch_bundle_sha256": contract["patch_bundle_sha256"],
        "proposal_sha256": contract["proposal_sha256"],
        "builder_schema": contract["builder_schema"],
    }
    request_key = hashlib.sha256(
        _canonical_json_bytes(request_preimage)).hexdigest()
    if intent.get("request_key") != request_key:
        return None, True
    request_lock = (operations_root / "build-cache" / "locks" /
                    f"request-{request_key}.lock")
    build_lock = (operations_root / "build-cache" / "locks" /
                  f"build-{entry.name}.lock")
    transaction_row = _discovery_private_json(
        entry / "transaction-owner.json",
        schema="epyc.autokernel.gpu_source_build_transaction_owner.v2",
        keys={"schema", "build_key", "holder", "intent",
              "intent_file_sha256", "locks", "promotion_claim",
              "supervised_build_authority", "supervised_build_authority_sha256",
              "receipt_sha256"})
    if transaction_row is None:
        return None, True
    transaction, _, _ = transaction_row
    transaction_locks = transaction.get("locks")
    intent_body = dict(intent)
    intent_body.pop("receipt_sha256", None)
    if (transaction.get("build_key") != entry.name
            or transaction.get("intent") != intent_body
            or transaction.get("intent_file_sha256") !=
            hashlib.sha256(intent_raw).hexdigest()
            or transaction.get("promotion_claim") is not False
            or not isinstance(transaction_locks, list)
            or len(transaction_locks) != 2
            or not _discovery_v2_lock_identity(
                request_lock, transaction_locks[0],
                require_held=not entry_terminal_present)
            or not _discovery_v2_lock_identity(
                build_lock, transaction_locks[1],
                require_held=not entry_terminal_present)):
        return None, True
    attempts = entry / "attempts"
    if (not _discovery_owned_directory(entry)
            or not _discovery_owned_directory(attempts)):
        return None, True
    try:
        attempt_children = sorted(attempts.iterdir(), key=lambda path: path.name)
    except OSError:
        return None, True
    if (len(attempt_children) != 1
            or [path.name for path in attempt_children] !=
            [f"attempt-{index:06d}" for index in range(1, len(attempt_children) + 1)]
            or any(path.is_symlink() or not path.is_dir()
                   for path in attempt_children)):
        return None, True
    attempt = attempt_children[-1]
    terminal_present = entry_terminal_present
    if ((attempt / "recovery.json").exists()
            or (attempt / "recovery.json").is_symlink()
            or attempt.name != "attempt-000001"):
        return None, True
    owner_row = _discovery_private_json(
        attempt / "owner.json",
        schema="epyc.autokernel.gpu_source_build_attempt.v2",
        keys={"schema", "attempt", "attempt_name", "build_key", "cache_root",
              "build_root", "holder", "locks", "supervised_build_authority",
              "supervised_build_authority_sha256", "promotion_claim",
              "receipt_sha256"})
    if owner_row is None:
        return None, True
    owner, owner_raw, _ = owner_row
    authority = owner.get("supervised_build_authority")
    holder = owner.get("holder")
    attempt_number = len(attempt_children)
    expected_build_root = Path(str(contract.get("build_root"))) / entry.name / attempt.name
    if (owner.get("attempt") != attempt_number
            or owner.get("attempt_name") != attempt.name
            or owner.get("build_key") != entry.name
            or owner.get("cache_root") != str(entry)
            or owner.get("build_root") != str(expected_build_root)
            or owner.get("promotion_claim") is not False
            or owner.get("locks") != transaction_locks
            or not isinstance(authority, dict)
            or set(authority) != {"schema", "launch_spec", "death_ledger",
                                  "spec_sha256",
                                  "deployment_config_canonical_sha256",
                                  "deployment_config_semantic_sha256",
                                  "controller", "supervisor",
                                  "ledger_child_started_record_sha256"}
            or owner.get("supervised_build_authority_sha256") !=
            hashlib.sha256(_canonical_json_bytes(authority)).hexdigest()
            or transaction.get("supervised_build_authority") != authority
            or transaction.get("supervised_build_authority_sha256") !=
            owner.get("supervised_build_authority_sha256")
            or _discovery_stable_supervised_authority(authority) != stable_authority
            or authority.get("deployment_config_semantic_sha256") != config_sha256
            or authority.get("deployment_config_canonical_sha256") !=
            contract.get("deployment_config_canonical_sha256")
            or not _supervisor_process(authority.get("controller"), child=True)
            or not _supervisor_process(authority.get("supervisor"), child=False)
            or not isinstance(holder, dict)
            or set(holder) != {"pid", "start_ticks", "boot_id", "host", "label"}
            or holder.get("label") !=
            f"autokernel-build:{entry.name}:{attempt.name}"
            or any(holder.get(key) != authority.get("controller", {}).get(key)
                   for key in ("pid", "start_ticks", "boot_id", "host"))):
        return None, True
    transaction_holder = transaction.get("holder")
    if (not isinstance(transaction_holder, dict)
            or set(transaction_holder) !=
            {"pid", "start_ticks", "boot_id", "host", "label"}
            or transaction_holder.get("label") !=
            f"autokernel-build-transaction:{entry.name}"
            or any(transaction_holder.get(key) != authority["controller"].get(key)
                   for key in ("pid", "start_ticks", "boot_id", "host"))):
        return None, True
    controller_cgroup = _discovery_authority_cgroup(
        authority, require_live=not terminal_present)
    if controller_cgroup is None:
        return None, True
    if not terminal_present:
        try:
            current_boot = Path("/proc/sys/kernel/random/boot_id").read_text(
                encoding="ascii").strip()
            controller_proc = _discovery_proc_stat(holder["pid"])
        except OSError:
            return None, True
        if controller_proc is None:
            return None, True
        controller_state, controller_pgid, controller_ticks = controller_proc
        if (holder.get("boot_id") != current_boot
                or holder.get("host") != os.uname().nodename
                or controller_ticks != holder.get("start_ticks")
                or controller_state == "Z"
                or controller_pgid != authority["controller"]["pgid"]):
            return None, True
    logs = attempt / "logs"
    if (not _discovery_owned_directory(attempt)
            or not _discovery_owned_directory(logs)):
        return None, True
    now = time.time()
    observations = []
    completed_builds = []
    prior_build_complete = True
    allowed_logs: set[str] = set()
    for arm, name in (("anchor", "akc-anchor"), ("candidate", candidate_id)):
        expected_writable_root = expected_build_root / campaign_id / name
        expected_source_root = (
            attempt / "worktrees" /
            f"llama.cpp-{campaign_id}-{name}-snapshot")
        configure_names = {
            f"{name}.log.configure-process-intent.json",
            f"{name}.log.configure-process-start.json",
            f"{name}.log.configure-process-terminal.json",
            f"{name}.log.configure-sandbox.json",
            f"{name}.log.configure.stream",
        }
        build_names = {
            f"{name}.log.build-process-intent.json",
            f"{name}.log.build-process-start.json",
            f"{name}.log.build-sandbox.json",
            f"{name}.log.build.stream",
        }
        configure_intent_path = logs / f"{name}.log.configure-process-intent.json"
        if not configure_intent_path.exists() and not configure_intent_path.is_symlink():
            # The next arm has not started.  Earlier receipts remain the only
            # admissible prefix of the two-arm state machine.
            if arm == "candidate" and prior_build_complete:
                continue
            break
        allowed_logs |= configure_names | build_names | {
            f"{name}.log.build-process-terminal.json",
            f"{name}.log", f"{name}.log.result.json"}
        configure_row = _discovery_private_json(
            configure_intent_path,
            schema="epyc.autokernel.owned_process_intent.v1",
            keys=_DISCOVERY_PROCESS_INTENT_KEYS)
        if configure_row is None:
            continue
        configure_argv = configure_row[0].get("argv")
        if (not isinstance(configure_argv, list) or len(configure_argv) < 6
                or configure_argv[0] !=
                contract.get("toolchain", {}).get("programs", {}).get("cmake", {}).get("resolved")
                or configure_argv[1] != "-S" or configure_argv[3] != "-B"):
            continue
        source_root = Path(str(configure_argv[2]))
        writable_root = Path(str(configure_argv[4]))
        if (source_root != expected_source_root
                or writable_root != expected_writable_root
                or str(source_root) != configure_argv[2]
                or str(writable_root) != configure_argv[4]
                or not terminal_present and (
                    not _discovery_owned_directory(
                        source_root, allow_group_write=True)
                    or not _discovery_owned_directory(writable_root))):
            return None, True
        defines = [f"-DCMAKE_BUILD_TYPE={contract.get('build_type')}"] + [
            f"-D{key}={value}" for key, value in contract.get("cmake_defines", [])]
        if configure_argv[5:] != defines:
            return None, True
        if configure_row[0].get("cgroup_root") != controller_cgroup["path"]:
            return None, True
        if _discovery_v2_process_receipts(
                prefix=logs / f"{name}.log.configure", attempt_root=attempt,
                writable_root=writable_root, expected_argv=configure_argv,
                expected_cgroup_root=controller_cgroup["path"],
                require_live=False, now=now) is None:
            return None, True
        jobs = contract.get("parallelism", {}).get("jobs")
        targets = contract.get("required_targets")
        if (not isinstance(jobs, int) or isinstance(jobs, bool) or jobs <= 0
                or not isinstance(targets, list)
                or any(not isinstance(target, str) for target in targets)):
            return None, True
        build_argv = [configure_argv[0], "--build", str(writable_root),
                      "-j", str(jobs)]
        for target in targets:
            build_argv.extend(["--target", target])
        build_prefix = logs / f"{name}.log.build"
        terminal_path = logs / f"{name}.log.build-process-terminal.json"
        if terminal_path.exists() or terminal_path.is_symlink():
            complete = _discovery_v2_process_receipts(
                prefix=build_prefix, attempt_root=attempt,
                writable_root=writable_root, expected_argv=build_argv,
                expected_cgroup_root=controller_cgroup["path"],
                require_live=False, now=now)
            if complete is None or not prior_build_complete:
                return None, True
            completed_builds.append(complete)
            prior_build_complete = True
            continue
        live = _discovery_v2_process_receipts(
            prefix=build_prefix, attempt_root=attempt,
            writable_root=writable_root, expected_argv=build_argv,
            expected_cgroup_root=controller_cgroup["path"],
            require_live=True, now=now)
        if live is not None and prior_build_complete:
            observations.append({
                "stage": "build", "state": "running", "arm": arm,
                "started_at": live["started_at"], "build_key": entry.name,
                "attempt": attempt.name, "source_materialized": True,
                "process_verified": True,
                "progress_percent": live["progress_percent"],
                "hip_compile": live["hip_compile"],
                "progress_at": live["progress_at"],
                "stream_stale": live["stream_stale"],
            })
            prior_build_complete = False
        else:
            return None, True
    try:
        log_names = {path.name for path in logs.iterdir()}
    except OSError:
        return None, True
    if not log_names.issubset(allowed_logs):
        return None, True
    for name in ("akc-anchor", candidate_id):
        if (f"{name}.log.result.json" in log_names
                and f"{name}.log.build-process-terminal.json" not in log_names):
            return None, True
    if len(observations) == 1 and not terminal_present:
        return observations[0], True
    if (not observations and len(completed_builds) == 2 and terminal_present
            and _discovery_v2_terminal_complete(
                entry, attempt, intent_raw=intent_raw, owner_raw=owner_raw,
                contract=contract, candidate_id=candidate_id)):
        terminal_info = (entry / "terminal.json").stat()
        return ({"stage": "evidence_binding", "state": "running",
                 "arm": "complete", "build_key": entry.name,
                 "attempt": attempt.name, "source_materialized": True,
                 "started_at": datetime.fromtimestamp(
                     terminal_info.st_mtime, timezone.utc
                 ).isoformat().replace("+00:00", "Z")}, True)
    return None, True


def _discovery_legacy_build_observation(operations_root: Path, state: dict | None,
                                        config_sha256: object) -> dict | None:
    """Identify the exact active source-build transaction from sealed inputs.

    This is an operator observation, not execution authority.  It only reports
    a build when one real cache entry binds the current inflight manifest,
    proposal, deployment identity, and held build lock.  Merely finding a log
    or process name is deliberately insufficient.
    """
    inflight = state.get("inflight") if isinstance(state, dict) else None
    if not isinstance(inflight, dict) or not isinstance(config_sha256, str):
        return None
    candidate = inflight.get("candidate")
    row = inflight.get("row")
    if not isinstance(candidate, dict) or not isinstance(row, dict):
        return None
    manifest_sha = candidate.get("source_manifest_sha256")
    proposal_sha = row.get("proposal_sha256")
    manifest = candidate.get("manifest")
    candidate_id = manifest.get("candidate_id") if isinstance(manifest, dict) else None
    if (not isinstance(manifest_sha, str) or not isinstance(proposal_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is None
            or re.fullmatch(r"[0-9a-f]{64}", proposal_sha) is None):
        return None
    entries = operations_root / "build-cache" / "entries"
    try:
        if entries.is_symlink() or not entries.is_dir():
            return None
        children = list(entries.iterdir())[:128]
    except OSError:
        return None
    matches = []
    for entry in children:
        if (entry.is_symlink() or not entry.is_dir()
                or re.fullmatch(r"[0-9a-f]{64}", entry.name) is None):
            continue
        intent_path = entry / "intent.json"
        present, intent, error = _read_json_object(intent_path, "source build intent")
        if not present or intent is None or error:
            continue
        contract = intent.get("build_contract")
        if (intent.get("schema") != "epyc.autokernel.gpu_source_build_intent.v1"
                or intent.get("build_key") != entry.name
                or not isinstance(contract, dict)
                or contract.get("build_key") != entry.name
                or contract.get("patch_bundle_sha256") != manifest_sha
                or contract.get("proposal_sha256") != proposal_sha
                or contract.get("deployment_config_sha256") != config_sha256):
            continue
        terminal = entry / "terminal.json"
        if terminal.exists() or terminal.is_symlink():
            present, terminal_body, error = _read_json_object(
                terminal, "source build terminal")
            if (not present or terminal_body is None or error
                    or terminal_body.get("schema") !=
                    "epyc.autokernel.gpu_source_build_terminal.v1"
                    or terminal_body.get("build_key") != entry.name
                    or terminal_body.get("state") != "complete"
                    or not _discovery_completed_build_materialization(
                        entry=entry, intent_path=intent_path,
                        terminal=terminal_body, contract=contract)):
                continue
            try:
                completed_at = datetime.fromtimestamp(
                    terminal.stat().st_mtime, timezone.utc
                ).isoformat().replace("+00:00", "Z")
            except OSError:
                continue
            matches.append({"stage": "evidence_binding", "state": "running",
                            "started_at": completed_at,
                            "build_key": entry.name, "arm": "complete"})
            continue
        lock = operations_root / "build-cache" / "locks" / f"build-{entry.name}.lock"
        if not _discovery_lock_held(lock):
            continue
        try:
            started_at = datetime.fromtimestamp(
                intent_path.stat().st_mtime, timezone.utc
            ).isoformat().replace("+00:00", "Z")
        except OSError:
            continue
        arm = None
        arm_started_at = started_at
        logs = entry / "logs"
        if (isinstance(candidate_id, str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", candidate_id)):
            candidate_start = logs / f"{candidate_id}.log.build-sandbox.json"
            if candidate_start.is_file() and not candidate_start.is_symlink():
                arm = "candidate"
                try:
                    arm_started_at = datetime.fromtimestamp(
                        candidate_start.stat().st_mtime, timezone.utc
                    ).isoformat().replace("+00:00", "Z")
                except OSError:
                    continue
        if arm is None:
            anchor_start = logs / "akc-anchor.log.build-sandbox.json"
            if anchor_start.is_file() and not anchor_start.is_symlink():
                arm = "anchor"
                try:
                    arm_started_at = datetime.fromtimestamp(
                        anchor_start.stat().st_mtime, timezone.utc
                    ).isoformat().replace("+00:00", "Z")
                except OSError:
                    continue
        matches.append({"stage": "build", "state": "running",
                        "started_at": arm_started_at, "build_key": entry.name,
                        "arm": arm})
    return matches[0] if len(matches) == 1 else None


def _discovery_build_observation(operations_root: Path, state: dict | None,
                                 config_sha256: object) -> dict | None:
    try:
        v2, v2_contract = _discovery_v2_build_observation(
            operations_root, state, config_sha256)
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return None
    if v2_contract:
        return v2
    return _discovery_legacy_build_observation(
        operations_root, state, config_sha256)


def _discovery_correctness_observation(operations_root: Path,
                                       state: dict | None) -> dict | None:
    """Return an identity-bound completed correctness execution, if present.

    A stdout filename alone is not proof that AutoKernel reached the GPU.  Bind
    the operation directory to the inflight manifest and operation key, require
    the sealed evidence policy, then require the operation-scoped release
    receipt.  The result summary is deliberately narrow: it reports the native
    backend test total, not the looser ``N/N backends passed`` line which caused
    the v10 producer parser to reject otherwise completed output.
    """
    inflight = state.get("inflight") if isinstance(state, dict) else None
    if not isinstance(inflight, dict):
        return None
    operation_key = inflight.get("operation_key")
    candidate = inflight.get("candidate")
    manifest_sha = (candidate.get("source_manifest_sha256")
                    if isinstance(candidate, dict) else None)
    if (not isinstance(operation_key, str)
            or re.fullmatch(r"[0-9a-f]{64}", operation_key) is None
            or not isinstance(manifest_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is None):
        return None
    operation = operations_root / operation_key
    try:
        if operation.is_symlink() or not operation.is_dir():
            return None
    except OSError:
        return None
    intent_path = operation / "intent.json"
    policy_path = operation / "evidence-policy.json"
    release_path = operation / "reservation-release.json"
    proof_root = operation / "proof"
    correctness_root = proof_root / "correctness"
    try:
        if any(path.is_symlink() for path in (
                intent_path, policy_path, release_path, proof_root,
                correctness_root)):
            return None
    except OSError:
        return None
    present, intent, error = _read_json_object(
        intent_path, "GPU source operation intent")
    if (not present or intent is None or error
            or intent.get("schema") != "epyc.autokernel.gpu_source_operation.v1"
            or intent.get("operation_key") != operation_key
            or intent.get("manifest_sha256") != manifest_sha):
        return None
    present, policy, error = _read_json_object(
        policy_path, "GPU source evidence policy")
    if (not present or policy is None or error
            or policy.get("schema") !=
            "epyc.autokernel.gpu_source_execution_policy.v1"
            or policy.get("manifest_sha256") != manifest_sha):
        return None
    stdout_path = correctness_root / "stdout.txt"
    try:
        if (stdout_path.is_symlink() or not stdout_path.is_file()
                or stdout_path.stat().st_size > 2 * 1024 * 1024):
            return None
        raw = stdout_path.read_bytes()
    except OSError:
        return None
    summaries = re.findall(rb"(?m)^\s*(\d+)/(\d+) tests passed\s*$", raw)
    if len(summaries) != 1:
        return None
    passed, total = (int(value) for value in summaries[0])
    if passed != total or total <= 0:
        return None
    present, release, error = _read_json_object(
        release_path, "GPU source reservation release")
    claim = release.get("device_claim_released") if isinstance(release, dict) else None
    if (not present or release is None or error
            or release.get("schema") !=
            "epyc.autokernel.gpu_source_reservation_release.v1"
            or release.get("operation_key") != operation_key
            or not isinstance(claim, dict)
            or claim.get("schema") != "epyc.autokernel.device_claim_receipt.v1"
            or claim.get("purpose") != "AutoKernel GPU source proof and throughput"
            or not isinstance(claim.get("acquired_at"), str)
            or not isinstance(claim.get("released_at"), str)):
        return None
    started = _parse_semantic_timestamp(claim["acquired_at"])
    completed = _parse_semantic_timestamp(claim["released_at"])
    if started is None or completed is None or completed < started:
        return None
    return {
        "stage": "correctness_validation",
        "state": "execution_complete",
        "started_at": claim["acquired_at"],
        "completed_at": claim["released_at"],
        "elapsed_s": completed - started,
        "operation_key": operation_key,
        "device_id": claim.get("device_id"),
        "claim_id": claim.get("claim_id"),
        "claim_released": True,
        "passed": passed,
        "total": total,
        "summary": f"{passed}/{total} tests passed",
    }


def _discovery_stage_receipt(path: Path, *, operation_root: Path,
                             schemas: set[str],
                             manifest_sha256: str | None = None) -> dict | None:
    """Read one bounded, self-hashed operation receipt for operator projection.

    This is deliberately narrower than producer-side validation.  It cannot
    authorize execution or a scientific decision; it only lets the dashboard
    report that the exact operation has a durable terminal for a stage.
    """
    try:
        resolved_root = operation_root.resolve(strict=True)
        path.resolve(strict=True).relative_to(resolved_root)
        cursor = path.parent
        while cursor != operation_root:
            if cursor.is_symlink():
                return None
            cursor = cursor.parent
        info = path.lstat()
        if (path.is_symlink() or not path.is_file() or info.st_nlink != 1
                or info.st_size > 4 * 1024 * 1024):
            return None
        raw = path.read_bytes()
        after = path.lstat()
    except OSError:
        return None
    if ((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
            != (after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_nlink)):
        return None
    try:
        body = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if (not isinstance(body, dict) or body.get("schema") not in schemas
            or body.get("promotion_claim") is not False):
        return None
    screen_receipt = (
        body.get("schema") == "epyc.autokernel.gpu_candidate_only_screen.v2")
    if (not screen_receipt
            and body.get("authority") !=
            "nonpromotable_candidate_only_discovery"):
        return None
    if (manifest_sha256 is not None
            and body.get("schema") != "epyc.autokernel.gpu_candidate_only_screen.v2"
            and body.get("manifest_sha256") != manifest_sha256):
        return None
    native = body.get("receipt_sha256") or body.get("result_sha256")
    if isinstance(native, str) and re.fullmatch(r"[0-9a-f]{64}", native):
        key = "receipt_sha256" if "receipt_sha256" in body else "result_sha256"
        if hashlib.sha256(json.dumps(
                {name: value for name, value in body.items() if name != key},
                sort_keys=True, separators=(",", ":")).encode()).hexdigest() != native:
            return None
    else:
        return None
    at = next((body.get(key) for key in (
        "ended_at", "completed_at", "observed_at", "created_at", "released_at")
        if isinstance(body.get(key), str)), None)
    if at is None:
        at = datetime.fromtimestamp(
            info.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
    return {"path": str(path), "body": body, "at": at,
            "file_sha256": hashlib.sha256(raw).hexdigest()}


def _discovery_runner_plan_proof_seal(
        operation: Path, runner: Path, *, operation_key: str,
        manifest_sha256: str, policy_order: list[str]) -> dict | None:
    """Project oversized proof receipts through the sealed runner plan.

    Exact attribution receipts can legitimately contain tens of megabytes of
    per-dispatch timings, and the pair/bundle recursively embed them.  Loading
    those bodies on every dashboard refresh would defeat the bounded 4 MiB
    receipt reader above.  The producer creates ``runner-plan.json`` only after
    it has reopened and validated both attribution arms, their pair, and the
    proof bundle.  Treat that compact, self-hashed downstream receipt as the
    lifecycle seal, but only while every predecessor remains the same regular,
    single-link, owner-controlled file epoch that predates the plan.

    This is a visibility projection, never execution authorization.  Any
    missing predecessor, alias, permission drift, post-plan mutation, or plan
    identity/path mismatch fails closed to the ordinary receipt sequence.
    """
    plan_path = operation / "runner-plan.json"
    plan = _discovery_stage_receipt(
        plan_path, operation_root=operation,
        schemas={"epyc.autokernel.gpu_source_runner_plan.v1"})
    if plan is None:
        return None
    body = plan["body"]
    expected_keys = {
        "schema", "authority", "promotion_claim", "operation_key",
        "measurement_graphs_off_output_dir",
        "target_runtime_graphs_on_output_dir", "receipt_sha256",
    }
    expected_outputs = {
        "measurement_graphs_off_output_dir":
            runner / "measurement-graphs-off",
        "target_runtime_graphs_on_output_dir":
            runner / "target-runtime-graphs-on",
    }
    if (set(body) != expected_keys
            or body.get("operation_key") != operation_key
            or any(not isinstance(body.get(key), str)
                   or Path(body[key]) != expected
                   for key, expected in expected_outputs.items())):
        return None
    try:
        plan_info = plan_path.lstat()
    except OSError:
        return None

    paths = {
        f"{arm}_attribution":
            operation / "proof" / f"attribution-{arm}" / "receipt.json"
        for arm in policy_order
    }
    paths.update({
        "pair": operation / "proof" / "attribution-pair.json",
        "bundle": operation / "proof" / "proof-bundle.json",
    })
    sealed: dict[str, dict] = {}
    try:
        resolved_root = operation.resolve(strict=True)
        for name, path in paths.items():
            path.resolve(strict=True).relative_to(resolved_root)
            cursor = path.parent
            while cursor != operation:
                if cursor.is_symlink():
                    return None
                cursor = cursor.parent
            before = path.lstat()
            if (path.is_symlink() or not stat.S_ISREG(before.st_mode)
                    or before.st_uid != os.geteuid() or before.st_nlink != 1
                    or stat.S_IMODE(before.st_mode) & 0o022
                    or before.st_size <= 0 or before.st_size > 256 * 1024 * 1024
                    or before.st_mtime_ns > plan_info.st_mtime_ns
                    or before.st_ctime_ns > plan_info.st_ctime_ns):
                return None
            after = path.lstat()
            epoch = lambda value: (
                value.st_dev, value.st_ino, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns, value.st_nlink,
                value.st_uid, stat.S_IFMT(value.st_mode),
                stat.S_IMODE(value.st_mode))
            if epoch(before) != epoch(after):
                return None
            sealed[name] = {
                "path": str(path),
                "at": datetime.fromtimestamp(
                    before.st_mtime, timezone.utc
                ).isoformat().replace("+00:00", "Z"),
                "seal_sha256": plan["file_sha256"],
                "body": (
                    {"schema": "epyc.autokernel.gpu_kernel_attribution.v2",
                     "status": "complete", "result": "PASS",
                     "manifest_sha256": manifest_sha256,
                     "arm": name.removesuffix("_attribution")}
                    if name.endswith("_attribution") else
                    {"schema":
                     "epyc.autokernel.gpu_kernel_attribution_pair.v1",
                     "manifest_sha256": manifest_sha256,
                     "attribution_arm_order": list(policy_order)}
                    if name == "pair" else
                    {"schema":
                     "epyc.autokernel.gpu_source_evidence_bundle.v1"}),
            }
    except (OSError, ValueError):
        return None
    return sealed


def _discovery_private_file(path: Path, *, operation_root: Path,
                            maximum: int) -> tuple[bytes, os.stat_result] | None:
    """Read one producer-private operation file without following aliases."""
    fd = None
    try:
        root = operation_root.resolve(strict=True)
        path.parent.resolve(strict=True).relative_to(root)
        cursor = path.parent
        while cursor != operation_root:
            if cursor.is_symlink():
                return None
            cursor = cursor.parent
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags)
        before = os.fstat(fd)
        named_before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) & 0o077
                or before.st_size > maximum
                or (named_before.st_dev, named_before.st_ino) !=
                (before.st_dev, before.st_ino)):
            return None
        chunks = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        named_after = path.lstat()
    except (OSError, ValueError):
        return None
    finally:
        if fd is not None:
            os.close(fd)
    epoch = lambda value: (
        value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
        value.st_ctime_ns, value.st_nlink, value.st_uid,
        stat.S_IFMT(value.st_mode), stat.S_IMODE(value.st_mode))
    if epoch(before) != epoch(after) or epoch(before) != epoch(named_after):
        return None
    return raw, before


def _discovery_content_hash(value: object) -> str | None:
    """Match the producer's warning-strict canonical JSON content hash."""
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(canonical).hexdigest()


def _discovery_runner_preflight(output: Path, *, operation_root: Path,
                                graph_mode: str) -> dict | None:
    captured = _discovery_private_file(
        output / "preflight.json", operation_root=operation_root,
        maximum=1024 * 1024)
    if captured is None:
        return None
    raw, info = captured
    try:
        body = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    order = body.get("arm_order_schedule") if isinstance(body, dict) else None
    if (not isinstance(body, dict) or body.get("runtime_graphs") != graph_mode
            or not isinstance(order, list) or len(order) != 2
            or set(order) != {"anchor", "candidate"}):
        return None
    content_hash = _discovery_content_hash(body)
    if content_hash is None:
        return None
    return {
        "arm_order": list(order),
        "sha256": content_hash,
        "at": datetime.fromtimestamp(
            info.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _discovery_process_receipt(root: Path, *, operation_root: Path,
                               graph_mode: str, arm: str,
                               preflight_sha256: str) -> dict | None:
    """Validate one reusable per-arm process checkpoint without raw output."""
    try:
        root.resolve(strict=True).relative_to(operation_root.resolve(strict=True))
        info = root.lstat()
        if (root.is_symlink() or not root.is_dir()
                or info.st_uid != os.geteuid()
                or info.st_nlink != 2
                or stat.S_IMODE(info.st_mode) != 0o700
                or {entry.name for entry in root.iterdir()} != {
                    "stdout.bin", "stderr.bin", "receipt.json"}):
            return None
    except (OSError, ValueError):
        return None
    files: dict[str, tuple[bytes, os.stat_result]] = {}
    for name, maximum in (("stdout.bin", 8 * 1024 * 1024),
                          ("stderr.bin", 8 * 1024 * 1024),
                          ("receipt.json", 4 * 1024 * 1024)):
        captured = _discovery_private_file(
            root / name, operation_root=operation_root, maximum=maximum)
        if captured is None:
            return None
        files[name] = captured
    try:
        receipt = json.loads(files["receipt.json"][0].decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(receipt, dict):
        return None
    unsigned = {key: value for key, value in receipt.items()
                if key != "receipt_sha256"}
    identity = receipt.get("identity")
    context = identity.get("process_context") if isinstance(identity, dict) else None
    repetitions = identity.get("repetitions") if isinstance(identity, dict) else None
    if (receipt.get("schema") !=
            "epyc.autokernel.gpu_discovery_process_receipt.v1"
            or receipt.get("status") != "process_complete"
            or receipt.get("receipt_sha256") != _discovery_content_hash(unsigned)
            or not isinstance(identity, dict)
            or identity.get("runtime_graphs") != graph_mode
            or identity.get("runtime_arm") != arm
            or isinstance(repetitions, bool)
            or not isinstance(repetitions, int) or repetitions < 1
            or not isinstance(context, dict)
            or set(context) != {
                "campaign_id", "preflight_sha256", "arm", "workload",
                "metric", "runtime_graphs", "prompt_tokens",
                "generation_tokens", "tokens_per_repetition"}
            or re.fullmatch(r"ak-discovery-[0-9a-f]{16}", str(
                context.get("campaign_id"))) is None
            or context.get("arm") != arm
            or context.get("runtime_graphs") != graph_mode
            or context.get("preflight_sha256") != preflight_sha256
            or not isinstance(context.get("workload"), str)
            or not context["workload"]
            or not isinstance(context.get("metric"), str)
            or not context["metric"]
            or any(isinstance(context.get(key), bool)
                   or not isinstance(context.get(key), int)
                   or context[key] < 0 for key in (
                       "prompt_tokens", "generation_tokens"))
            or isinstance(context.get("tokens_per_repetition"), bool)
            or not isinstance(context.get("tokens_per_repetition"), int)
            or context["tokens_per_repetition"] < 1
            or context["tokens_per_repetition"] != (
                context["prompt_tokens"] + context["generation_tokens"])
            or isinstance(receipt.get("returncode"), bool)
            or not isinstance(receipt.get("returncode"), int)
            or not isinstance(receipt.get("residency"), list)
            or (receipt["returncode"] == 0 and not receipt["residency"])
            or any(not isinstance(sample, dict)
                   for sample in receipt["residency"])
            or isinstance(receipt.get("supervisor_elapsed_s"), bool)
            or not isinstance(receipt.get("supervisor_elapsed_s"), (int, float))
            or not math.isfinite(float(receipt["supervisor_elapsed_s"]))
            or receipt["supervisor_elapsed_s"] < 0
            or not isinstance(receipt.get("teardown"), dict)
            or receipt.get("output_bound_bytes") != 8 * 1024 * 1024):
        return None
    for label in ("stdout", "stderr"):
        binding = receipt.get(label)
        raw = files[f"{label}.bin"][0]
        if (not isinstance(binding, dict)
                or set(binding) != {"path", "observed_size", "observed_sha256",
                                    "stored_size", "stored_sha256", "truncated"}
                or binding.get("path") != f"{label}.bin"
                or binding.get("stored_size") != len(raw)
                or binding.get("stored_sha256") != hashlib.sha256(raw).hexdigest()
                or not isinstance(binding.get("observed_size"), int)
                or isinstance(binding.get("observed_size"), bool)
                or binding["observed_size"] < len(raw)
                or re.fullmatch(r"[0-9a-f]{64}", str(
                    binding.get("observed_sha256"))) is None
                or binding.get("truncated") is not (
                    binding["observed_size"] > len(raw))
                or (binding["truncated"] is False
                    and binding["observed_sha256"] != binding["stored_sha256"])):
            return None
    receipt_raw, receipt_info = files["receipt.json"]
    return {
        "arm": arm, "runtime_graphs": graph_mode,
        "receipt_path": str(root / "receipt.json"),
        "receipt_file_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "stdout": {key: receipt["stdout"].get(key) for key in (
            "observed_size", "observed_sha256", "stored_size",
            "stored_sha256", "truncated")},
        "stderr": {key: receipt["stderr"].get(key) for key in (
            "observed_size", "observed_sha256", "stored_size",
            "stored_sha256", "truncated")},
        "measurement_identity": {
            "campaign_id": context["campaign_id"], "arm": arm,
            "workload": context["workload"], "metric": context["metric"],
            "runtime_graphs": graph_mode,
            "prompt_tokens": context["prompt_tokens"],
            "generation_tokens": context["generation_tokens"],
            "tokens_per_repetition": context["tokens_per_repetition"],
            "repetitions": repetitions,
            "preflight_sha256": preflight_sha256,
        },
        "at": datetime.fromtimestamp(
            receipt_info.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _discovery_postbuild_observation(operations_root: Path,
                                     state: dict | None) -> dict | None:
    """Project the exact resumable proof/screen receipt sequence.

    Completed stages are accepted only from their operation-scoped native
    receipts.  The first missing receipt is therefore also the producer's
    resumable first-incomplete boundary; file names elsewhere do not count.
    """
    inflight = state.get("inflight") if isinstance(state, dict) else None
    candidate = inflight.get("candidate") if isinstance(inflight, dict) else None
    operation_key = inflight.get("operation_key") if isinstance(inflight, dict) else None
    manifest_sha = (candidate.get("source_manifest_sha256")
                    if isinstance(candidate, dict) else None)
    if (not isinstance(operation_key, str)
            or re.fullmatch(r"[0-9a-f]{64}", operation_key) is None
            or not isinstance(manifest_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is None):
        return None
    operation = operations_root / operation_key
    try:
        if operation.is_symlink() or not operation.is_dir():
            return None
    except OSError:
        return None
    intent_present, intent, intent_error = _read_json_object(
        operation / "intent.json", "GPU source operation intent")
    if (not intent_present or intent is None or intent_error
            or intent.get("schema") != "epyc.autokernel.gpu_source_operation.v1"
            or intent.get("operation_key") != operation_key
            or intent.get("manifest_sha256") != manifest_sha):
        return None
    policy_present, policy, policy_error = _read_json_object(
        operation / "evidence-policy.json", "GPU source evidence policy")
    if (not policy_present or not isinstance(policy, dict) or policy_error
            or policy.get("schema") !=
            "epyc.autokernel.gpu_source_execution_policy.v2"
            or policy.get("manifest_sha256") != manifest_sha):
        return None
    policy_order = policy.get("attribution_arm_order")
    if (not isinstance(policy_order, list) or len(policy_order) != 2
            or set(policy_order) != {"candidate", "anchor"}):
        return None
    lease = inflight.get("lease") if isinstance(inflight, dict) else None
    repetition = lease.get("repetition") if isinstance(lease, dict) else None
    if not isinstance(repetition, int) or isinstance(repetition, bool) or repetition < 1:
        repetition = 1
    proof = operation / "proof"
    runner = operation / "runner" / f"s{repetition}"
    attribution_specs = tuple((
        f"{arm}_attribution", proof / f"attribution-{arm}" / "receipt.json",
        {"epyc.autokernel.gpu_kernel_attribution.v2"})
        for arm in policy_order)
    specs = (
        ("correctness", proof / "correctness" / "receipt.json",
         {"epyc.autokernel.targeted_correctness_receipt.v3"}),
        *attribution_specs,
        ("measurement_graphs_off_screen",
         runner / "measurement-graphs-off" / "result.json",
         {"epyc.autokernel.gpu_candidate_only_screen.v2"}),
        ("target_runtime_graphs_on_screen",
         runner / "target-runtime-graphs-on" / "result.json",
         {"epyc.autokernel.gpu_candidate_only_screen.v2"}),
    )
    runner_proof_seal = _discovery_runner_plan_proof_seal(
        operation, runner, operation_key=operation_key,
        manifest_sha256=manifest_sha, policy_order=policy_order)
    receipts: dict[str, dict] = {}
    for stage, path, schemas in specs:
        receipt = _discovery_stage_receipt(
            path, operation_root=operation, schemas=schemas,
            manifest_sha256=manifest_sha)
        if (receipt is None and isinstance(runner_proof_seal, dict)
                and stage in runner_proof_seal):
            receipt = runner_proof_seal[stage]
        if receipt is None:
            break
        body = receipt["body"]
        if stage == "correctness" and (
                body.get("status") != "complete" or body.get("result") != "PASS"):
            break
        if stage in {"candidate_attribution", "anchor_attribution"} and (
                body.get("status") != "complete" or body.get("result") != "PASS"):
            break
        if stage.endswith("_screen") and (
                body.get("non_promotable") is not True
                or body.get("hip_residency_proved") is not True
                or body.get("runtime_graphs") != (
                    "off" if stage == "measurement_graphs_off_screen" else "on")):
            break
        receipts[stage] = receipt
    completed = list(receipts)
    if "correctness" in receipts:
        completed.append("correctness_validation")
    first_incomplete = next(
        (stage for stage, _path, _schemas in specs if stage not in receipts),
        "decision")
    process_progress = None
    screen_outputs = {
        "measurement_graphs_off_screen": (
            runner / "measurement-graphs-off", "off"),
        "target_runtime_graphs_on_screen": (
            runner / "target-runtime-graphs-on", "on"),
    }
    if first_incomplete in screen_outputs:
        output, graph_mode = screen_outputs[first_incomplete]
        preflight = _discovery_runner_preflight(
            output, operation_root=operation, graph_mode=graph_mode)
        if preflight is not None:
            process_receipts = []
            for arm in preflight["arm_order"]:
                root = output / f"process-{arm}"
                if not root.exists() and not root.is_symlink():
                    break
                process = _discovery_process_receipt(
                    root, operation_root=operation, graph_mode=graph_mode,
                    arm=arm, preflight_sha256=preflight["sha256"])
                if process is None:
                    process_receipts = []
                    break
                process_receipts.append(process)
            if process_receipts:
                completed_arms = [item["arm"] for item in process_receipts]
                process_progress = {
                    "stage": first_incomplete, "runtime_graphs": graph_mode,
                    "started_at": preflight["at"],
                    "arm_order": preflight["arm_order"],
                    "completed_arms": completed_arms,
                    "next_arm": (preflight["arm_order"][len(completed_arms)]
                                 if len(completed_arms) < 2 else None),
                    "checkpoint_reuse": True,
                    "receipts": process_receipts,
                }
    pair = _discovery_stage_receipt(
        proof / "attribution-pair.json",
        operation_root=operation,
        schemas={"epyc.autokernel.gpu_kernel_attribution_pair.v1"},
        manifest_sha256=manifest_sha)
    if pair is None and isinstance(runner_proof_seal, dict):
        pair = runner_proof_seal.get("pair")
    bundle = _discovery_stage_receipt(
        proof / "proof-bundle.json",
        operation_root=operation,
        schemas={"epyc.autokernel.gpu_source_evidence_bundle.v1"},
        manifest_sha256=manifest_sha)
    if bundle is None and isinstance(runner_proof_seal, dict):
        bundle = runner_proof_seal.get("bundle")
    exact_outcome = _discovery_stage_receipt(
        runner / "exact-attribution-outcome.json",
        operation_root=operation,
        schemas={"epyc.autokernel.exact_attribution_outcome.v1"},
        manifest_sha256=manifest_sha)
    skipped: dict[str, str] = {}
    if pair is not None and {"candidate_attribution", "anchor_attribution"}.issubset(receipts):
        completed.append("dispatch_proof")
    if bundle is not None and "dispatch_proof" in completed:
        completed.append("profile")
    if first_incomplete == "measurement_graphs_off_screen":
        if pair is None:
            first_incomplete = "dispatch_proof"
        elif bundle is None:
            first_incomplete = "profile"
    if exact_outcome is not None:
        outcome_body = exact_outcome["body"]
        exact_effect = outcome_body.get("exact_attribution_effect_fraction")
        if (outcome_body.get("status") != "complete"
                or outcome_body.get("classification") != "screened_out"
                or outcome_body.get("target_runtime_executed") is not False
                or outcome_body.get("target_runtime_reason") !=
                "nonpositive_exact_duration"
                or isinstance(exact_effect, bool)
                or not isinstance(exact_effect, (int, float))
                or not math.isfinite(float(exact_effect))
                or float(exact_effect) > 0):
            exact_outcome = None
        else:
            skipped = {
                "measurement_graphs_off_screen": "exact attribution was nonpositive",
                "target_runtime_graphs_on_screen": "short-circuited by exact attribution",
            }
            completed.append("decision")
            first_incomplete = "decision"
    if {"measurement_graphs_off_screen", "target_runtime_graphs_on_screen"}.issubset(receipts):
        completed.append("benchmark")
        first_incomplete = "decision"
    correctness_execution = None
    correctness_body = receipts.get("correctness", {}).get("body", {})
    candidate_manifest = (candidate.get("manifest")
                          if isinstance(candidate, dict) else None)
    expected_campaign_id = (candidate_manifest.get("campaign_id")
                            if isinstance(candidate_manifest, dict) else None)
    passed_cases = correctness_body.get("passed_cases")
    expected_cases = correctness_body.get("expected_cases")
    correctness_open = correctness_body.get("device_claim_open")
    correctness_borrowed = correctness_body.get(
        "device_claim_borrowed_phase_end")
    correctness_residency = correctness_body.get("residency_witness")
    correctness_started = (correctness_open.get("acquired_at")
                           if isinstance(correctness_open, dict) else None)
    correctness_ended = correctness_body.get("ended_at")
    correctness_expires = (correctness_open.get("expires_at")
                           if isinstance(correctness_open, dict) else None)
    claim_keys = {
        "schema", "claim_id", "campaign_id", "device_id", "purpose",
        "holder_pid", "holder_start_ticks", "holder_boot_id", "holder_label",
        "host", "lock_path", "acquired_at", "expires_at", "released_at",
        "reclaimed_from", "state",
    }
    if (isinstance(passed_cases, int) and not isinstance(passed_cases, bool)
            and isinstance(expected_cases, int)
            and not isinstance(expected_cases, bool)
            and passed_cases == expected_cases and expected_cases > 0
            and correctness_body.get("overall") == "OK"
            and correctness_body.get("summary") ==
            f"{passed_cases}/{expected_cases} tests passed"
            and correctness_body.get("exit_code") == 0
            and correctness_body.get("exact_case_ok") is True
            and isinstance(expected_campaign_id, str)
            and re.fullmatch(r"ak-discovery-[0-9a-f]{16}",
                             expected_campaign_id) is not None
            and correctness_body.get("campaign_id") == expected_campaign_id
            and isinstance(correctness_open, dict)
            and set(correctness_open) == claim_keys
            and correctness_open.get("schema") ==
            "epyc.autokernel.device_claim_receipt.v1"
            and correctness_open.get("campaign_id") == expected_campaign_id
            and correctness_open.get("purpose") ==
            "AutoKernel GPU source proof and throughput"
            and correctness_open.get("state") == "held"
            and correctness_open.get("released_at") is None
            and correctness_open.get("holder_label") ==
            "autokernel-discovery-controller"
            and correctness_open.get("host") == os.uname().nodename
            and all(isinstance(correctness_open.get(key), int)
                    and not isinstance(correctness_open.get(key), bool)
                    and correctness_open[key] > 0
                    for key in ("holder_pid", "holder_start_ticks"))
            and re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                str(correctness_open.get("holder_boot_id"))) is not None
            and correctness_open.get("device_id") ==
            correctness_body.get("device_id")
            and correctness_open.get("lock_path") ==
            f"/mnt/raid0/llm/tmp/gpu_device.{correctness_open.get('device_id')}.lock"
            and (correctness_open.get("reclaimed_from") is None
                 or re.fullmatch(r"akd-[0-9a-f]{16}", str(
                     correctness_open.get("reclaimed_from"))) is not None)
            and re.fullmatch(r"akd-[0-9a-f]{16}", str(
                correctness_open.get("claim_id"))) is not None
            and isinstance(correctness_started, str)
            and isinstance(correctness_ended, str)
            and isinstance(correctness_expires, str)
            and _parse_semantic_timestamp(correctness_started) is not None
            and _parse_semantic_timestamp(correctness_ended) is not None
            and _parse_semantic_timestamp(correctness_expires) is not None
            and _parse_semantic_timestamp(correctness_ended) >=
            _parse_semantic_timestamp(correctness_started)
            and _parse_semantic_timestamp(correctness_expires) >
            _parse_semantic_timestamp(correctness_started)
            and isinstance(correctness_borrowed, dict)
            and set(correctness_borrowed) == {
                "schema", "campaign_id", "device_id", "mode",
                "outer_claim_id", "phase_ended_at", "physical_release"}
            and correctness_borrowed.get("schema") ==
            "epyc.autokernel.borrowed_device_claim_phase.v1"
            and correctness_borrowed.get("campaign_id") == expected_campaign_id
            and correctness_borrowed.get("device_id") ==
            correctness_open.get("device_id")
            and correctness_borrowed.get("mode") ==
            "borrowed_outer_reservation"
            and correctness_borrowed.get("outer_claim_id") ==
            correctness_open.get("claim_id")
            and correctness_borrowed.get("physical_release") is False
            and isinstance(correctness_borrowed.get("phase_ended_at"), str)
            and _parse_semantic_timestamp(
                correctness_borrowed["phase_ended_at"]) is not None
            and 0 <= (_parse_semantic_timestamp(
                correctness_borrowed["phase_ended_at"])
                      - _parse_semantic_timestamp(correctness_ended)) <= 5.0
            and isinstance(correctness_residency, dict)
            and correctness_residency.get("device_claim_mode") ==
            "borrowed_outer_reservation"
            and correctness_residency.get("outer_claim_id") ==
            correctness_open.get("claim_id")
            and correctness_residency.get("overlapped") is True
            and correctness_residency.get("claim_verified_before") is True
            and correctness_residency.get("claim_verified_after") is True
            and isinstance(correctness_residency.get("overlap_sample_count"), int)
            and not isinstance(correctness_residency.get("overlap_sample_count"), bool)
            and correctness_residency["overlap_sample_count"] > 0
            and isinstance(correctness_residency.get("max_vram_bytes"), int)
            and not isinstance(correctness_residency.get("max_vram_bytes"), bool)
            and correctness_residency["max_vram_bytes"] > 0):
        correctness_execution = {
            "started_at": correctness_started,
            "acquired_at": correctness_started,
            "completed_at": correctness_ended,
            "elapsed_s": (_parse_semantic_timestamp(correctness_ended)
                          - _parse_semantic_timestamp(correctness_started)),
            "passed": passed_cases, "total": expected_cases,
            "summary": f"{passed_cases}/{expected_cases} tests passed",
            "campaign_id": expected_campaign_id,
            "claim_id": correctness_open.get("claim_id"),
            "device_id": correctness_open.get("device_id"),
            "claim_released": False,
        }
    elif (not isinstance(expected_campaign_id, str)
          and (not isinstance(state, dict)
               or state.get("schema") !=
               "epyc.autokernel.discovery_controller.v5")
          and isinstance(passed_cases, int)
          and not isinstance(passed_cases, bool)
          and isinstance(expected_cases, int)
          and not isinstance(expected_cases, bool)
          and passed_cases == expected_cases and expected_cases > 0
          and correctness_body.get("overall") == "OK"
          and isinstance(correctness_open, dict)
          and isinstance(correctness_started, str)
          and isinstance(correctness_ended, str)
          and _parse_semantic_timestamp(correctness_started) is not None
          and _parse_semantic_timestamp(correctness_ended) is not None
          and _parse_semantic_timestamp(correctness_ended) >=
          _parse_semantic_timestamp(correctness_started)):
        # Historical v11-v18 fixtures predate the v25 outer-reservation
        # grammar.  Preserve their completed-result visibility without letting
        # a v5 state that lost its campaign binding fall through this branch.
        correctness_execution = {
            "started_at": correctness_started,
            "acquired_at": correctness_started,
            "completed_at": correctness_ended,
            "elapsed_s": (_parse_semantic_timestamp(correctness_ended)
                          - _parse_semantic_timestamp(correctness_started)),
            "passed": passed_cases, "total": expected_cases,
            "summary": f"{passed_cases}/{expected_cases} tests passed",
            "campaign_id": correctness_open.get("campaign_id"),
            "claim_id": correctness_open.get("claim_id"),
            "device_id": correctness_open.get("device_id"),
            "claim_released": False,
        }
    pair_body = pair["body"] if pair else {}
    comparison = (pair_body.get("exact_duration_comparison")
                  if isinstance(pair_body.get("exact_duration_comparison"), dict)
                  else {})
    exact_effect_value = comparison.get("relative_improvement_fraction")
    if (isinstance(exact_effect_value, bool)
            or not isinstance(exact_effect_value, (int, float))
            or not math.isfinite(float(exact_effect_value))
            or comparison.get("direction") != (
                "improved" if exact_effect_value > 0 else
                "regressed" if exact_effect_value < 0 else "neutral")):
        comparison = {}
    screen = receipts.get("target_runtime_graphs_on_screen", {}).get("body", {})
    arm_order = (pair_body.get("attribution_arm_order")
                 or pair_body.get("arm_order_schedule")
                 or screen.get("arm_order_schedule") or policy_order)
    transitions = [{
        "ts": receipt["at"], "stage": stage, "phase": stage,
        "state": "complete", "event": f"{stage}_completed",
        "label": _DISCOVERY_PIPELINE_DICT.get(stage, stage),
        "detail": (
            f"receipt {receipt['file_sha256'][:12]}…"
            if isinstance(receipt.get("file_sha256"), str) else
            f"sealed by runner plan {receipt['seal_sha256'][:12]}…"),
    } for stage, receipt in receipts.items()]
    if process_progress is not None:
        transitions.extend({
            "ts": process["at"], "stage": first_incomplete,
            "phase": first_incomplete, "state": "checkpointed",
            "event": "measurement_process_checkpointed",
            "label": (f"{process['arm']} process complete; checkpoint will be "
                      "revalidated and reused"),
            "detail": f"receipt {process['receipt_file_sha256'][:12]}…",
        } for process in process_progress["receipts"])
    if pair is not None:
        transitions.append({
            "ts": pair["at"], "stage": "dispatch_proof", "phase": "dispatch_proof",
            "state": "complete", "event": "dispatch_proof_completed",
            "label": _DISCOVERY_PIPELINE_DICT["dispatch_proof"],
            "detail": (
                f"receipt {pair['file_sha256'][:12]}…"
                if isinstance(pair.get("file_sha256"), str) else
                f"sealed by runner plan {pair['seal_sha256'][:12]}…"),
        })
    if bundle is not None:
        transitions.append({
            "ts": bundle["at"], "stage": "profile", "phase": "profile",
            "state": "complete", "event": "profile_bundle_completed",
            "label": _DISCOVERY_PIPELINE_DICT["profile"],
            "detail": (
                f"receipt {bundle['file_sha256'][:12]}…"
                if isinstance(bundle.get("file_sha256"), str) else
                f"sealed by runner plan {bundle['seal_sha256'][:12]}…"),
        })
    if exact_outcome is not None:
        transitions.append({
            "ts": exact_outcome["at"], "stage": "decision", "phase": "decision",
            "state": "complete", "event": "exact_attribution_nonpositive",
            "label": "Exact attribution nonpositive; target runtime short-circuited",
            "detail": f"receipt {exact_outcome['file_sha256'][:12]}…",
        })
    return {
        "operation_key": operation_key, "repetition": repetition,
        "completed": completed, "first_incomplete_stage": first_incomplete,
        "correctness_execution": correctness_execution,
        "receipts": receipts, "pair_complete": pair is not None,
        "bundle_complete": bundle is not None, "arm_order": arm_order,
        "process_progress": process_progress,
        "skipped": skipped,
        "arm_order_seed_sha256": (
                                   pair_body.get("attribution_arm_order_seed_sha256")
                                   or pair_body.get("arm_order_seed_sha256")
                                   or screen.get("arm_order_seed_sha256")
                                   or (policy.get("attribution_arm_order_seed_sha256")
                                       if isinstance(policy, dict) else None)),
        "exact_direction": comparison.get("direction"),
        "exact_attribution_effect_fraction": comparison.get(
            "relative_improvement_fraction"),
        "target_runtime_effect_fraction": screen.get("median_relative"),
        "target_runtime_executed": (
            exact_outcome["body"].get("target_runtime_executed")
            if exact_outcome is not None else
            True if "target_runtime_graphs_on_screen" in receipts else None),
        "target_runtime_reason": (
            exact_outcome["body"].get("target_runtime_reason")
            if exact_outcome is not None else None),
        "dual_decision_state": (
            "measured_nonpositive_exact_short_circuit"
            if exact_outcome is not None else
            "exact_and_graphs_on_complete"
            if (isinstance(comparison.get("relative_improvement_fraction"),
                           (int, float))
                and not isinstance(comparison.get("relative_improvement_fraction"), bool)
                and isinstance(screen.get("median_relative"), (int, float))
                and not isinstance(screen.get("median_relative"), bool))
            else "awaiting_dual_evidence"),
        "transitions": transitions,
    }


def _discovery_claim_observation(
        operations_root: Path, campaign_id: str | None,
        *, purpose: str =
        "AutoKernel GPU source proof and throughput") -> dict | None:
    """Return the latest identity-proven source-proof claim state."""
    path = operations_root / "claims" / "device.jsonl"
    captured = _owned_public_snapshot(path, max_bytes=2 * 1024 * 1024)
    if captured is None:
        return None
    raw = captured[0]
    if not raw.endswith(b"\n"):
        return None
    lines = raw.splitlines()
    if not lines or len(lines) > 512:
        return None
    now = time.time()
    host = os.uname().nodename
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii").strip()
    except OSError:
        return None
    latest: dict[str, dict] = {}
    previous_created = None
    receipt_keys = {
        "schema", "claim_id", "campaign_id", "device_id", "purpose",
        "holder_pid", "holder_start_ticks", "holder_boot_id", "holder_label",
        "host", "lock_path", "acquired_at", "expires_at", "released_at",
        "reclaimed_from", "state",
    }
    for encoded in lines:
        try:
            row = _strict_json_bytes(encoded)
        except (TypeError, ValueError):
            return None
        detail = row.get("detail") if isinstance(row, dict) else None
        receipt = detail.get("receipt") if isinstance(detail, dict) else None
        kind = row.get("kind") if isinstance(row, dict) else None
        created_at = row.get("created_at") if isinstance(row, dict) else None
        created = (_parse_semantic_timestamp(created_at)
                   if isinstance(created_at, str) else None)
        acquired = (_parse_semantic_timestamp(receipt.get("acquired_at"))
                    if isinstance(receipt, dict) else None)
        expires = (_parse_semantic_timestamp(receipt.get("expires_at"))
                   if isinstance(receipt, dict) else None)
        released_at = (receipt.get("released_at")
                       if isinstance(receipt, dict) else None)
        released = (_parse_semantic_timestamp(released_at)
                    if isinstance(released_at, str) else None)
        if (not isinstance(row, dict)
                or encoded != _canonical_json_bytes(row)
                or set(row) != {"schema", "kind", "created_at", "device_id",
                                "host", "record_id", "writer_pid", "detail"}
                or row.get("schema") != "epyc.autokernel.device_claim_journal.v1"
                or row.get("kind") not in {"claim_acquired", "claim_released"}
                or not isinstance(receipt, dict)
                or set(receipt) != receipt_keys
                or receipt.get("schema") != "epyc.autokernel.device_claim_receipt.v1"
                or re.fullmatch(r"akj-[0-9a-f]{16}", str(
                    row.get("record_id"))) is None
                or re.fullmatch(r"akd-[0-9a-f]{16}", str(
                    receipt.get("claim_id"))) is None
                or re.fullmatch(r"[a-z0-9_]{1,64}", str(
                    receipt.get("device_id"))) is None
                or row.get("device_id") != receipt.get("device_id")
                or row.get("host") != host or receipt.get("host") != host
                or row.get("writer_pid") != receipt.get("holder_pid")
                or any(isinstance(receipt.get(key), bool)
                       or not isinstance(receipt.get(key), int)
                       or receipt[key] <= 0
                       for key in ("holder_pid", "holder_start_ticks"))
                or receipt.get("holder_boot_id") != boot_id
                or receipt.get("holder_label") !=
                "autokernel-discovery-controller"
                or receipt.get("lock_path") !=
                f"/mnt/raid0/llm/tmp/gpu_device.{receipt.get('device_id')}.lock"
                or receipt.get("state") != "held"
                or (receipt.get("reclaimed_from") is not None
                    and re.fullmatch(r"akd-[0-9a-f]{16}", str(
                        receipt.get("reclaimed_from"))) is None)
                or created is None or acquired is None or expires is None
                or created > now + 5.0
                or expires <= acquired
                or previous_created is not None and created < previous_created):
            return None
        if kind == "claim_acquired":
            if (set(detail) != {"attempts", "claim_id", "receipt", "reclaimed"}
                    or detail.get("claim_id") != receipt["claim_id"]
                    or isinstance(detail.get("attempts"), bool)
                    or not isinstance(detail.get("attempts"), int)
                    or detail["attempts"] < 1
                    or not isinstance(detail.get("reclaimed"), bool)
                    or abs(acquired - created) > 5.0
                    or released_at is not None):
                return None
        else:
            if (set(detail) != {"claim_id", "payload_clear_error", "receipt",
                                "released_at", "revocation_read_error"}
                    or detail.get("claim_id") != receipt["claim_id"]
                    or detail.get("released_at") != released_at
                    or released is None or released < acquired
                    or abs(released - created) > 5.0
                    or detail.get("payload_clear_error") is not None
                    or detail.get("revocation_read_error") is not None):
                return None
        previous_created = created
        if (receipt.get("purpose") == purpose
                and isinstance(campaign_id, str)
                and receipt.get("campaign_id") == campaign_id):
            latest[receipt["claim_id"]] = {
                "kind": kind, "receipt": receipt, "at": created_at,
                "created": created}
    if not latest:
        return None
    row = max(latest.values(), key=lambda value: value["created"])
    receipt = row["receipt"]
    acquired_at = receipt.get("acquired_at")
    held = row["kind"] == "claim_acquired" and receipt.get("released_at") is None
    if held:
        pid, ticks = receipt.get("holder_pid"), receipt.get("holder_start_ticks")
        proc_stat = _discovery_proc_stat(pid)
        lock_path = Path(receipt["lock_path"])
        try:
            lock_info = lock_path.lstat()
        except OSError:
            lock_info = None
        held = bool(
            _parse_semantic_timestamp(receipt["acquired_at"]) <= now <
            _parse_semantic_timestamp(receipt["expires_at"])
            and proc_stat is not None and proc_stat[0] != "Z"
            and proc_stat[2] == ticks
            and lock_info is not None and stat.S_ISREG(lock_info.st_mode)
            and lock_info.st_uid == os.geteuid() and lock_info.st_nlink == 1
            and not lock_path.is_symlink()
            and _discovery_lock_held(lock_path))
    return {"claim_held": held,
            "claim_released": row["kind"] == "claim_released",
            "claim_id": receipt.get("claim_id"),
            "campaign_id": receipt.get("campaign_id"),
            "device_id": receipt.get("device_id"),
            "acquired_at": acquired_at,
            "released_at": receipt.get("released_at"),
            "identity_live": held}


def _discovery_claim_matches_correctness(
        claim: object, correctness: object) -> bool:
    """Bind a live outer claim to the current operation's sealed correctness.

    Device-claim journals are campaign-wide.  Once correctness has sealed the
    outer reservation identity, a newer same-campaign claim must not make that
    older operation look GPU-active.  Before a correctness receipt exists the
    caller may still use the campaign-bound claim to show correctness starting;
    after it exists these four producer identities are mandatory.
    """
    if not isinstance(correctness, dict):
        return True
    if not isinstance(claim, dict):
        return False
    return all(
        isinstance(correctness.get(key), str)
        and claim.get(key) == correctness.get(key)
        for key in ("campaign_id", "claim_id", "device_id", "acquired_at"))


def _discovery_measurement_output_refusal(
        receipt: dict, path: Path, bundle: Path) -> dict | None:
    """Validate and project the v17 secret-free output-refusal diagnostic."""
    if set(receipt) != {
            "schema", "status", "scientific_budget_spent",
            "process_receipt_path", "process_receipt_file_sha256",
            "reason_code", "reason_sha256", "diagnostic", "receipt_sha256"}:
        return None
    if (receipt.get("schema") !=
            "epyc.autokernel.gpu_discovery_output_refusal.v1"
            or receipt.get("status") != "measurement_output_refused"
            or receipt.get("scientific_budget_spent") is not False
            or re.fullmatch(r"[a-z0-9_]{1,100}", str(
                receipt.get("reason_code"))) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(
                receipt.get("reason_sha256"))) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(
                receipt.get("process_receipt_file_sha256"))) is None):
        return None
    diagnostic = receipt.get("diagnostic")
    if (not isinstance(diagnostic, dict) or set(diagnostic) != {
            "schema", "diagnostic_available", "measurement_identity",
            "native_fields", "rederived", "stdout", "stderr"}
            or diagnostic.get("schema") !=
            "epyc.autokernel.measurement_output_refusal_diagnostic.v1"
            or not isinstance(diagnostic.get("diagnostic_available"), bool)):
        return None
    identity = diagnostic.get("measurement_identity")
    if (not isinstance(identity, dict) or set(identity) != {
            "campaign_id", "arm", "workload", "metric", "runtime_graphs",
            "prompt_tokens", "generation_tokens", "tokens_per_repetition",
            "repetitions", "preflight_sha256"}
            or identity.get("arm") not in {"anchor", "candidate"}
            or identity.get("runtime_graphs") not in {"off", "on"}
            or not isinstance(identity.get("campaign_id"), str)
            or re.fullmatch(r"ak-discovery-[0-9a-f]{16}",
                            identity["campaign_id"]) is None
            or not isinstance(identity.get("workload"), str)
            or not isinstance(identity.get("metric"), str)
            or any(isinstance(identity.get(key), bool)
                   or not isinstance(identity.get(key), int)
                   or identity[key] < 0 for key in (
                       "prompt_tokens", "generation_tokens"))
            or any(isinstance(identity.get(key), bool)
                   or not isinstance(identity.get(key), int)
                   or identity[key] < 1 for key in (
                       "tokens_per_repetition", "repetitions"))
            or re.fullmatch(r"[0-9a-f]{64}", str(
                identity.get("preflight_sha256"))) is None):
        return None
    native = diagnostic.get("native_fields")
    rederived = diagnostic.get("rederived")
    if (not isinstance(native, dict) or set(native) != {
            "avg_ns", "samples_ns", "avg_ts_decimal", "samples_ts_decimal"}
            or not isinstance(rederived, dict)
            or set(rederived) != {"samples_ts", "avg_ts"}):
        return None
    repetitions = identity["repetitions"]
    if (native["avg_ns"] is not None and (
            isinstance(native["avg_ns"], bool)
            or not isinstance(native["avg_ns"], int))):
        return None
    if native["samples_ns"] is not None and (
            not isinstance(native["samples_ns"], list)
            or len(native["samples_ns"]) != repetitions
            or any(isinstance(value, bool) or not isinstance(value, int)
                   or value <= 0 for value in native["samples_ns"])):
        return None
    decimal_re = r"-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
    if native["avg_ts_decimal"] is not None and re.fullmatch(
            decimal_re, str(native["avg_ts_decimal"])) is None:
        return None
    if native["samples_ts_decimal"] is not None and (
            not isinstance(native["samples_ts_decimal"], list)
            or len(native["samples_ts_decimal"]) != repetitions
            or any(re.fullmatch(decimal_re, str(value)) is None
                   for value in native["samples_ts_decimal"])):
        return None
    samples_ts = rederived["samples_ts"]
    avg_ts = rederived["avg_ts"]
    if (samples_ts is not None and (
            not isinstance(samples_ts, list)
            or len(samples_ts) != repetitions
            or any(isinstance(item, bool)
                   or not isinstance(item, (int, float))
                   or not math.isfinite(float(item)) for item in samples_ts))):
        return None
    if (avg_ts is not None and (
            isinstance(avg_ts, bool) or not isinstance(avg_ts, (int, float))
            or not math.isfinite(float(avg_ts)))):
        return None
    if diagnostic["diagnostic_available"] is not any(
            value is not None for value in native.values()):
        return None
    if native["samples_ns"] is None:
        if samples_ts is not None or avg_ts is not None:
            return None
    else:
        exact = [
            Fraction(1_000_000_000 * identity["tokens_per_repetition"], value)
            for value in native["samples_ns"]]
        exact_samples = [float(value) for value in exact]
        exact_average = float(sum(exact, Fraction(0, 1)) / repetitions)
        if (samples_ts != exact_samples
                or avg_ts != exact_average):
            return None
    arm = identity["arm"]
    graph_mode = identity["runtime_graphs"]
    expected_name = f"process-{arm}-refusal.json"
    output = path.parent
    try:
        operation = path.parents[3]
        operation.resolve(strict=True).relative_to(bundle.resolve(strict=True))
    except (OSError, ValueError, IndexError):
        return None
    if (path.name != expected_name
            or re.fullmatch(r"[0-9a-f]{64}", operation.name) is None):
        return None
    preflight = _discovery_runner_preflight(
        output, operation_root=operation, graph_mode=graph_mode)
    if (preflight is None
            or preflight["sha256"] != identity["preflight_sha256"]):
        return None
    process = _discovery_process_receipt(
        output / f"process-{arm}", operation_root=operation,
        graph_mode=graph_mode, arm=arm,
        preflight_sha256=preflight["sha256"])
    if (process is None
            or process["receipt_file_sha256"] !=
            receipt["process_receipt_file_sha256"]
            or str(Path(str(receipt.get("process_receipt_path"))).resolve()) !=
            str(Path(process["receipt_path"]).resolve())
            or diagnostic["stdout"] != process["stdout"]
            or diagnostic["stderr"] != process["stderr"]
            or identity != process["measurement_identity"]):
        return None
    refused_index = preflight["arm_order"].index(arm)
    reusable_arms = []
    for completed_arm in preflight["arm_order"][:refused_index]:
        completed_process = _discovery_process_receipt(
            output / f"process-{completed_arm}", operation_root=operation,
            graph_mode=graph_mode, arm=completed_arm,
            preflight_sha256=preflight["sha256"])
        if completed_process is None:
            return None
        reusable_arms.append(completed_arm)
    repetition_match = re.fullmatch(r"s([1-9][0-9]*)", path.parents[1].name)
    if repetition_match is None:
        return None
    intent_present, intent, intent_error = _read_json_object(
        operation / "intent.json", "GPU source operation intent")
    if (not intent_present or not isinstance(intent, dict) or intent_error
            or re.fullmatch(r"[0-9a-f]{64}", str(
                intent.get("manifest_sha256"))) is None):
        return None
    proof_observation = _discovery_postbuild_observation(
        operation.parent, {"inflight": {
            "operation_key": operation.name,
            "candidate": {"source_manifest_sha256":
                          intent["manifest_sha256"]},
            "lease": {"repetition": int(repetition_match.group(1))},
        }})
    screen_stage = ("measurement_graphs_off_screen" if graph_mode == "off"
                    else "target_runtime_graphs_on_screen")
    if (not isinstance(proof_observation, dict)
            or proof_observation.get("first_incomplete_stage") != screen_stage):
        return None
    completed_pipeline = [
        "source_materialization", "build", "evidence_binding",
        *proof_observation.get("completed", []),
    ]
    return {
        "arm": arm, "runtime_graphs": graph_mode,
        "screen_stage": screen_stage,
        "workload": identity["workload"], "metric": identity["metric"],
        "reason_code": receipt["reason_code"],
        "reason_sha256": receipt["reason_sha256"],
        "diagnostic_available": diagnostic["diagnostic_available"],
        "native_fields": dict(native), "rederived": dict(rederived),
        "process_receipt_sha256": process["receipt_file_sha256"],
        "arm_order": preflight["arm_order"],
        "reusable_completed_arms": reusable_arms,
        "completed_pipeline": list(dict.fromkeys(completed_pipeline)),
    }


def _discovery_measurement_output_recovery(
        state: dict | None, iteration: dict | None,
        refusal: dict | None) -> dict | None:
    """Project the producer's bounded, non-scientific candidate recovery."""
    if (not isinstance(state, dict) or not isinstance(iteration, dict)
            or not isinstance(refusal, dict)):
        return None
    hypothesis = (iteration.get("portfolio_hypothesis_id")
                  or iteration.get("hypothesis_id"))
    failures_by_hypothesis = state.get("portfolio_measurement_output_failures")
    failures = (failures_by_hypothesis.get(hypothesis)
                if isinstance(failures_by_hypothesis, dict)
                and isinstance(hypothesis, str) else None)
    if (not isinstance(failures, list) or not failures
            or len(set(failures)) != len(failures)
            or any(not isinstance(value, str)
                   or re.fullmatch(r"[0-9a-f]{64}", value) is None
                   for value in failures)):
        return None
    manifest = iteration.get("source_manifest_sha256")
    if not isinstance(manifest, str) or manifest not in failures:
        return None
    policy = iteration.get("portfolio_decision_policy")
    budget = (policy.get("max_distinct_candidates")
              if isinstance(policy, dict) else None)
    if (not isinstance(budget, int) or isinstance(budget, bool) or budget < 1
            or len(failures) > budget):
        return None
    skips = state.get("portfolio_skips")
    skip = (skips.get(hypothesis) if isinstance(skips, dict) else None)
    bounded = False
    if skip is not None:
        if (not isinstance(skip, dict)
                or skip.get("disposition") !=
                "bounded_measurement_output_refused"
                or skip.get("scientific_terminal") is not False
                or skip.get("distinct_candidate_count") != len(failures)
                or skip.get("stage_receipt_path") !=
                refusal.get("receipt_path")
                or skip.get("stage_receipt_sha256") !=
                refusal.get("receipt_sha256")):
            return None
        bounded = True
    if bounded is not (len(failures) >= budget):
        return None
    return {
        "disposition": ("bounded_measurement_output_refused" if bounded
                        else "retry_distinct_candidate"),
        "distinct_candidate_count": len(failures),
        "max_distinct_candidates": budget,
        "scientific_terminal": False,
        "next": ("next_portfolio_hypothesis" if bounded
                 else "next_distinct_candidate"),
    }


def _discovery_refusal_observation(bundle: Path, state: dict | None,
                                   events: list[dict]) -> dict | None:
    """Discover a governed refusal from its typed fields, not a guessed path.

    The producer owns the eventual receipt filename and schema.  The dashboard
    follows only a declared path below the selected deployment, verifies its
    exact byte hash, then requires the canonical refusal fields to agree.
    """
    accepted_types = {
        "SourceApplyRefusal", "CompileRefusal", "CorrectnessRefusal",
        "DispatchAttributionRefusal", "MeasurementOutputRefusal",
    }
    dispositions = {
        "authoring_refused", "correctness_falsified",
        "attribution_route_falsified", "measurement_output_refused",
    }
    stage_types = {
        "source_apply": "SourceApplyRefusal",
        "compile": "CompileRefusal",
        "correctness": "CorrectnessRefusal",
        "dispatch_attribution": "DispatchAttributionRefusal",
        "measurement_output": "MeasurementOutputRefusal",
    }
    candidates: list[dict] = []
    if isinstance(state, dict):
        for owner in (state, state.get("inflight")):
            if isinstance(owner, dict) and isinstance(owner.get("refusal"), dict):
                candidates.append(owner["refusal"])
        iterations = state.get("iterations")
        if isinstance(iterations, list):
            for row in reversed(iterations[-25:]):
                if not isinstance(row, dict):
                    continue
                if isinstance(row.get("refusal"), dict):
                    candidates.append(row["refusal"])
                if ({"stage", "scientific_budget_spent"}.issubset(row)
                        and ("disposition" in row or "status" in row)
                        and ("receipt_path" in row
                             or "stage_receipt_path" in row)
                        and ("receipt_sha256" in row
                             or "stage_receipt_sha256" in row)):
                    candidates.append(row)
    for event in reversed(events):
        result = event.get("result") if isinstance(event, dict) else None
        if isinstance(result, dict):
            candidates.append(result)
    for value in candidates:
        stage = value.get("stage")
        refusal_type = (value.get("refusal_type") or value.get("type")
                        or value.get("class") or stage_types.get(stage))
        disposition = value.get("disposition") or value.get("status")
        expected = value.get("receipt_sha256") or value.get("stage_receipt_sha256")
        spent = value.get("scientific_budget_spent")
        if (refusal_type not in accepted_types or disposition not in dispositions
                or not isinstance(stage, str)
                or re.fullmatch(r"[a-z0-9_]{1,100}", stage) is None
                or not isinstance(expected, str)
                or re.fullmatch(r"[0-9a-f]{64}", expected) is None
                or not isinstance(spent, bool)):
            continue
        raw_path = value.get("receipt_path") or value.get("stage_receipt_path")
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = bundle / path
        try:
            root = bundle.resolve(strict=True)
            path.resolve(strict=True).relative_to(root)
            cursor = path.parent
            while cursor != bundle:
                if cursor.is_symlink():
                    raise ValueError("refusal receipt parent is a symlink")
                cursor = cursor.parent
            info = path.lstat()
            if (path.is_symlink() or not path.is_file() or info.st_nlink != 1
                    or info.st_size > 1024 * 1024):
                continue
            raw = path.read_bytes()
            after = path.lstat()
        except (OSError, ValueError):
            continue
        if ((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
                != (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_nlink)):
            continue
        try:
            receipt = json.loads(raw.decode("utf-8", "strict"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(receipt, dict):
            continue
        native_hash = receipt.get("receipt_sha256")
        if isinstance(native_hash, str) and re.fullmatch(
                r"[0-9a-f]{64}", native_hash):
            try:
                calculated_native = hashlib.sha256(json.dumps(
                    {key: item for key, item in receipt.items()
                     if key != "receipt_sha256"},
                    sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
            except (TypeError, ValueError):
                continue
            if calculated_native != native_hash:
                continue
        else:
            native_hash = None
        # Every controller ``stage_receipt_sha256`` binds the exact file bytes.
        # Build terminals additionally carry a native self-hash and name their
        # stage ``failure_stage``; both properties are validated independently.
        if expected != hashlib.sha256(raw).hexdigest():
            continue
        receipt_stage = receipt.get("stage") or receipt.get("failure_stage")
        if (not isinstance(receipt.get("schema"), str)
                or not receipt["schema"].startswith("epyc.autokernel.")
                or (receipt_stage is not None
                    and receipt_stage not in {stage, refusal_type})
                or ("disposition" in receipt
                    and receipt.get("disposition") != disposition)
                or ("scientific_budget_spent" in receipt
                    and receipt.get("scientific_budget_spent") is not spent)):
            continue
        receipt_type = (receipt.get("refusal_type") or receipt.get("type")
                        or receipt.get("class"))
        if receipt_type is not None and receipt_type != refusal_type:
            continue
        measurement_output = None
        if refusal_type == "MeasurementOutputRefusal":
            measurement_output = _discovery_measurement_output_refusal(
                receipt, path, bundle)
            if measurement_output is None:
                continue
        return {
            "detected": True, "type": refusal_type,
            "stage": stage, "disposition": disposition,
            "scientific_budget_spent": spent,
            "receipt_path": str(path), "receipt_sha256": expected,
            "at": datetime.fromtimestamp(
                info.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
            "detail": (
                f"{measurement_output['arm']} "
                f"{measurement_output['runtime_graphs']}-graphs output refused: "
                f"{measurement_output['reason_code']} · reason sha256 "
                f"{measurement_output['reason_sha256'][:12]}…"
                if measurement_output is not None else
                value.get("reason") or value.get("message")),
            "measurement_output": measurement_output,
        }
    return None


def _discovery_planner_refusal_iteration(
        value: object, *, before_turn: int | None = None) -> bool:
    if not isinstance(value, dict):
        return False
    turn = value.get("turn")
    hypothesis = value.get("hypothesis_id")
    operation_key = value.get("planner_operation_key")
    return bool(
        isinstance(turn, int) and not isinstance(turn, bool) and turn > 0
        and (before_turn is None or turn < before_turn)
        and value.get("status") == "planner_refused"
        and value.get("refusal_type") == "planner_output_refusal"
        and value.get("scientific_budget_spent") is False
        and value.get("telemetry_event") == "planner_refused"
        and value.get("telemetry_status") == "emitted"
        and isinstance(hypothesis, str)
        and re.fullmatch(r"akh-[a-z0-9][a-z0-9_.-]{0,196}",
                         hypothesis) is not None
        and isinstance(operation_key, str)
        and re.fullmatch(r"[0-9a-f]{64}", operation_key) is not None)


def _discovery_planner_refusal_terminals(
        state: dict | None, events: list[dict], campaign_id: str | None,
        current_turn: object) -> list[dict]:
    """Bind prior planner refusals to both sealed state and typed telemetry.

    A state row alone may contain a raw authoring reason, while an event alone
    has no turn number.  Only their operation/hypothesis/refusal identity join
    is sufficient to publish a bounded prior-terminal record.
    """
    if (not isinstance(state, dict) or not isinstance(campaign_id, str)
            or not isinstance(current_turn, int)
            or isinstance(current_turn, bool) or current_turn <= 1):
        return []
    iterations = state.get("iterations")
    if not isinstance(iterations, list):
        return []
    terminals = []
    consumed_operations: set[str] = set()
    for iteration in iterations[-25:]:
        if not isinstance(iteration, dict):
            continue
        turn = iteration.get("turn")
        hypothesis = iteration.get("hypothesis_id")
        operation_key = iteration.get("planner_operation_key")
        if (not _discovery_planner_refusal_iteration(
                iteration, before_turn=current_turn)
                or operation_key in consumed_operations):
            continue
        matches = []
        for event in events:
            result = event.get("result") if isinstance(event, dict) else None
            if (isinstance(result, dict)
                    and event.get("event") == "planner_refused"
                    and event.get("campaign_id") == campaign_id
                    and event.get("hypothesis_id") == hypothesis
                    and event.get("operation_key") == operation_key
                    and set(result) == {
                        "returncode", "stdout_sha256", "stderr_sha256",
                        "refusal_type", "refusal_reason_sha256"}
                    and result.get("returncode") == 0
                    and result.get("refusal_type") ==
                    "planner_output_refusal"
                    and all(isinstance(result.get(key), str)
                            and re.fullmatch(r"[0-9a-f]{64}", result[key])
                            is not None
                            for key in ("stdout_sha256", "stderr_sha256",
                                        "refusal_reason_sha256"))):
                matches.append(event)
        if len(matches) != 1:
            continue
        event = matches[0]
        consumed_operations.add(operation_key)
        terminals.append({
            "schema": "epyc.dashboard.autokernel_prior_terminal.v1",
            "ts": event["ts"], "event": "planner_refused",
            "turn": turn, "hypothesis_id": hypothesis,
            "status": "planner_refused", "stage": "planner_validation",
            "scientific_budget_spent": False,
            "detail": ("planner output refused; reason sha256 "
                       f"{event['result']['refusal_reason_sha256'][:12]}…"),
        })
    return terminals


def _discovery_successor_actor_chain(
        events: list[dict], prior_iteration: dict | None,
        campaign_id: str | None, expected: tuple[str, ...],
        now: float) -> list[dict] | None:
    """Return one exact v2 actor chain after a typed planner refusal."""
    if (not isinstance(prior_iteration, dict) or not isinstance(campaign_id, str)
            or not math.isfinite(now)
            or not _discovery_planner_refusal_iteration(prior_iteration)):
        return None
    hypothesis = prior_iteration.get("hypothesis_id")
    prior_operation = prior_iteration.get("planner_operation_key")
    refusal_matches = []
    for event in events:
        result = event.get("result") if isinstance(event, dict) else None
        if (isinstance(result, dict)
                and event.get("event") == "planner_refused"
                and event.get("campaign_id") == campaign_id
                and event.get("hypothesis_id") == hypothesis
                and event.get("operation_key") == prior_operation
                and set(result) == {
                    "returncode", "stdout_sha256", "stderr_sha256",
                    "refusal_type", "refusal_reason_sha256"}
                and result.get("returncode") == 0
                and result.get("refusal_type") == "planner_output_refusal"):
            refusal_matches.append(event)
    if len(refusal_matches) != 1:
        return None
    refusal = refusal_matches[0]
    refusal_time = _parse_semantic_timestamp(refusal.get("ts"))
    if refusal_time is None or refusal_time > now + 5.0:
        return None
    successors = []
    for event in events:
        event_time = (_parse_semantic_timestamp(event.get("ts"))
                      if isinstance(event, dict) else None)
        if (event_time is not None and event_time > refusal_time
                and event.get("campaign_id") == campaign_id
                and event.get("hypothesis_id") == hypothesis):
            successors.append(event)
    if ([event.get("event") for event in successors] != list(expected)
            or not successors or events[-1] != successors[-1]):
        return None
    times = [_parse_semantic_timestamp(event.get("ts")) for event in successors]
    if (any(value is None or value > now + 5.0 for value in times)
            or any(right <= left for left, right in zip(times, times[1:]))):
        return None
    planner_operation = successors[0].get("operation_key")
    if (not isinstance(planner_operation, str)
            or re.fullmatch(r"[0-9a-f]{64}", planner_operation) is None
            or planner_operation == prior_operation
            or successors[0].get("result") is not None):
        return None
    if len(successors) >= 2:
        result = successors[1].get("result")
        if (successors[1].get("operation_key") != planner_operation
                or not isinstance(result, dict)
                or set(result) != {
                    "returncode", "stdout_sha256", "stderr_sha256"}
                or result.get("returncode") != 0):
            return None
    if len(successors) >= 3:
        critic_operation = successors[2].get("operation_key")
        if (not isinstance(critic_operation, str)
                or re.fullmatch(r"[0-9a-f]{64}", critic_operation) is None
                or critic_operation in {prior_operation, planner_operation}
                or successors[2].get("result") is not None):
            return None
    if len(successors) >= 4:
        result = successors[3].get("result")
        if (successors[3].get("operation_key") !=
                successors[2].get("operation_key")
                or not isinstance(result, dict)
                or set(result) != {"stdout_sha256", "stderr_sha256", "decision"}
                or result.get("decision") != "accept"):
            return None
    return successors


def _discovery_planner_successor_binding(
        state: dict | None, planning: dict | None, events: list[dict],
        prior_iteration: dict | None, campaign_id: str | None,
        now: float) -> bool:
    """Prove a planner_started event belongs to the next durable turn."""
    chain = _discovery_successor_actor_chain(
        events, prior_iteration, campaign_id, ("planner_started",), now)
    if (not isinstance(state, dict) or not isinstance(planning, dict)
            or chain is None or not isinstance(prior_iteration, dict)):
        return False
    event = chain[0]
    turn = planning.get("turn")
    prior_turn = prior_iteration.get("turn")
    operation_key = planning.get("operation_key")
    prior_operation = prior_iteration.get("planner_operation_key")
    binding = planning.get("portfolio_binding")
    context = planning.get("context")
    assignment = (context.get("authoring_assignment")
                  if isinstance(context, dict) else None)
    event_time = _parse_semantic_timestamp(event.get("ts"))
    state_time = _parse_semantic_timestamp(state.get("updated_at"))
    return bool(
        prior_iteration.get("status") == "planner_refused"
        and prior_iteration.get("refusal_type") == "planner_output_refusal"
        and prior_iteration.get("scientific_budget_spent") is False
        and isinstance(turn, int) and not isinstance(turn, bool)
        and isinstance(prior_turn, int) and not isinstance(prior_turn, bool)
        and turn == prior_turn + 1 and state.get("next") == turn
        and planning.get("phase") == "actor_entering"
        and isinstance(planning.get("provider_attempt"), int)
        and not isinstance(planning.get("provider_attempt"), bool)
        and planning["provider_attempt"] >= 0
        and isinstance(operation_key, str)
        and re.fullmatch(r"[0-9a-f]{64}", operation_key) is not None
        and operation_key != prior_operation
        and event.get("event") == "planner_started"
        and event.get("campaign_id") == campaign_id
        and event.get("operation_key") == operation_key
        and event.get("result") is None
        and isinstance(binding, dict)
        and isinstance(assignment, dict)
        and assignment.get("campaign_id") == campaign_id
        and assignment.get("portfolio_binding") == binding
        and event.get("hypothesis_id") == binding.get("hypothesis_id")
        and event_time is not None and state_time is not None
        and 0 <= event_time - state_time <= 30.0
        and event_time <= now + 5.0)


def _discovery_pending_successor_binding(
        state: dict | None, pending: dict | None, events: list[dict],
        prior_iteration: dict | None, campaign_id: str | None,
        now: float) -> bool:
    if (not isinstance(state, dict) or not isinstance(pending, dict)
            or not isinstance(prior_iteration, dict)):
        return False
    latest_event = events[-1].get("event") if events else None
    expected_by_event = {
        "planner_completed": ("planner_started", "planner_completed"),
        "critic_started": ("planner_started", "planner_completed",
                           "critic_started"),
        "critic_completed": ("planner_started", "planner_completed",
                             "critic_started", "critic_completed"),
    }
    expected = expected_by_event.get(latest_event)
    chain = (_discovery_successor_actor_chain(
        events, prior_iteration, campaign_id, expected, now)
             if expected is not None else None)
    row = pending.get("row")
    candidate = pending.get("candidate")
    row_turn = row.get("turn") if isinstance(row, dict) else None
    declared_turn = pending.get("turn")
    turn = declared_turn if isinstance(declared_turn, int) else row_turn
    hypothesis = row.get("hypothesis_id") if isinstance(row, dict) else None
    prior_turn = prior_iteration.get("turn")
    state_time = _parse_semantic_timestamp(state.get("updated_at"))
    boundary_time = (_parse_semantic_timestamp(chain[-1].get("ts"))
                     if chain is not None else None)
    phase = pending.get("phase")
    time_coherent = bool(
        state_time is not None and boundary_time is not None
        and (0 <= boundary_time - state_time <= 30.0
             if latest_event == "critic_started" else
             0 <= state_time - boundary_time <= 30.0))
    return bool(
        chain is not None
        and isinstance(row, dict) and isinstance(candidate, dict)
        and ("turn" not in pending or declared_turn == row_turn)
        and isinstance(turn, int) and not isinstance(turn, bool)
        and isinstance(prior_turn, int) and not isinstance(prior_turn, bool)
        and turn == prior_turn + 1 and state.get("next") == turn
        and hypothesis == prior_iteration.get("hypothesis_id")
        and candidate.get("hypothesis_id") == hypothesis
        and phase in {"critic_pending", "critic_complete"}
        and (phase == "critic_pending"
             and latest_event in {"planner_completed", "critic_started"}
             or phase == "critic_complete" and latest_event == "critic_completed")
        and time_coherent)


def _discovery_inflight_successor_binding(
        state: dict | None, inflight: dict | None, events: list[dict],
        prior_iteration: dict | None, campaign_id: str | None,
        now: float) -> bool:
    chain = _discovery_successor_actor_chain(
        events, prior_iteration, campaign_id,
        ("planner_started", "planner_completed", "critic_started",
         "critic_completed"), now)
    if (not isinstance(state, dict) or not isinstance(inflight, dict)
            or not isinstance(prior_iteration, dict) or chain is None):
        return False
    row = inflight.get("row")
    candidate = inflight.get("candidate")
    operation_key = inflight.get("operation_key")
    turn = row.get("turn") if isinstance(row, dict) else None
    hypothesis = row.get("hypothesis_id") if isinstance(row, dict) else None
    prior_turn = prior_iteration.get("turn")
    state_time = _parse_semantic_timestamp(state.get("updated_at"))
    actor_time = _parse_semantic_timestamp(chain[-1].get("ts"))
    return bool(
        isinstance(row, dict) and isinstance(candidate, dict)
        and isinstance(turn, int) and not isinstance(turn, bool)
        and isinstance(prior_turn, int) and not isinstance(prior_turn, bool)
        and turn == prior_turn + 1 and state.get("next") == turn
        and hypothesis == prior_iteration.get("hypothesis_id")
        and candidate.get("hypothesis_id") == hypothesis
        and isinstance(operation_key, str)
        and re.fullmatch(r"[0-9a-f]{64}", operation_key) is not None
        and row.get("operation_key") == operation_key
        and state_time is not None and actor_time is not None
        and 0 <= state_time - actor_time <= 30.0)


def _discovery_activity(*, lock_held: bool, campaign_id: str | None,
                        state: dict | None,
                        events: list[dict], checkpoint: dict | None,
                        terminal_observation: dict | None = None,
                        operation_observation: dict | None,
                        correctness_observation: dict | None,
                        postbuild_observation: dict | None,
                        claim_observation: dict | None,
                        refusal_observation: dict | None,
                        refusal_history_observations: list[dict],
                        now: float, v26_contract: dict | None = None,
                        v26_state: dict | None = None) -> dict:
    """Derive an honest lifecycle view from durable producer facts.

    This does not invent percentage progress. A lock proves controller
    liveness, an event proves an actor transition, and a STOP_STATE/state pair
    proves only its last durable boundary.
    """
    pipeline = {stage: {"id": stage, "label": label, "state": "not_reached"}
                for stage, label in _DISCOVERY_PIPELINE}
    # A proof-plan declaration is not evidence that source materialization or
    # compilation finished.  Post-build receipts become visible only behind
    # the exact sealed terminal -> materialization chain observed above.
    if (not isinstance(operation_observation, dict)
            or operation_observation.get("stage") != "evidence_binding"):
        postbuild_observation = None
    receipt_correctness_observation = (
        postbuild_observation.get("correctness_execution")
        if isinstance(postbuild_observation, dict) else None)
    execution_observation = (
        correctness_observation if isinstance(correctness_observation, dict)
        else receipt_correctness_observation
        if isinstance(receipt_correctness_observation, dict) else None)
    transitions: list[dict] = []
    started: dict[str, str] = {}
    event_stage = {
        "planner_started": ("planner", "running"),
        "planner_completed": ("planner", "complete"),
        "planner_failed": ("planner", "failed"),
        "planner_refused": ("planner_validation", "failed"),
        "planner_validation_failed": ("planner_validation", "failed"),
        "planner_validation_refused": ("planner_validation", "failed"),
        "critic_started": ("critic", "running"),
        "critic_completed": ("critic", "complete"),
        "critic_failed": ("critic", "failed"),
        "correctness_started": ("correctness", "running"),
        "correctness_completed": ("correctness", "complete"),
        "correctness_validation_completed": ("correctness_validation", "complete"),
        "correctness_validation_failed": ("correctness_validation", "failed"),
        "candidate_attribution_started": ("candidate_attribution", "running"),
        "candidate_attribution_completed": ("candidate_attribution", "complete"),
        "anchor_attribution_started": ("anchor_attribution", "running"),
        "anchor_attribution_completed": ("anchor_attribution", "complete"),
        "measurement_graphs_off_screen_started": ("measurement_graphs_off_screen", "running"),
        "measurement_graphs_off_screen_completed": ("measurement_graphs_off_screen", "complete"),
        "target_runtime_graphs_on_screen_started": ("target_runtime_graphs_on_screen", "running"),
        "target_runtime_graphs_on_screen_completed": ("target_runtime_graphs_on_screen", "complete"),
        "decision_started": ("decision", "running"),
        "decision_completed": ("decision", "complete"),
        "replication_s1_started": ("replication_s1", "running"),
        "replication_s1_completed": ("replication_s1", "complete"),
        "replication_s2_started": ("replication_s2", "running"),
        "replication_s2_completed": ("replication_s2", "complete"),
        "next_hypothesis_started": ("next_hypothesis", "running"),
        "next_hypothesis_selected": ("next_hypothesis", "complete"),
        "authoring_refused": ("planner_validation", "failed"),
        "critic_refused": ("critic", "failed"),
        "compile_refused": ("build", "failed"),
        "correctness_falsified": ("correctness_validation", "failed"),
        "attribution_route_falsified": ("dispatch_proof", "failed"),
    }
    for row in events:
        event = row.get("event")
        ts = row.get("ts")
        if event not in event_stage or not isinstance(ts, str):
            continue
        stage, stage_state = event_stage[event]
        if stage == "critic":
            pipeline["planner_validation"]["state"] = "complete"
            pipeline["planner_validation"]["completed_at"] = ts
        pipeline[stage]["state"] = stage_state
        if stage_state == "running":
            pipeline[stage]["started_at"] = ts
            pipeline[stage].pop("completed_at", None)
            pipeline[stage].pop("elapsed_s", None)
            started[stage] = ts
        else:
            if stage in started:
                pipeline[stage]["started_at"] = started[stage]
                pipeline[stage]["elapsed_s"] = max(
                    0.0, _parse_semantic_timestamp(ts)
                    - _parse_semantic_timestamp(started[stage]))
            pipeline[stage]["completed_at"] = ts
        detail = row.get("model") or row.get("provider") or event
        result = row.get("result")
        if isinstance(result, dict) and isinstance(result.get("decision"), str):
            detail = f"decision: {result['decision']}"
        transitions.append({"ts": ts, "stage": stage, "phase": stage,
                            "state": stage_state, "event": event,
                            "label": str(detail)[:160],
                            "detail": str(detail)[:160]})

    inflight = state.get("inflight") if isinstance(state, dict) else None
    pending = state.get("pending") if isinstance(state, dict) else None
    planning = state.get("planning") if isinstance(state, dict) else None
    iterations = (state.get("iterations") if isinstance(state, dict)
                  and isinstance(state.get("iterations"), list) else [])
    latest_iteration = iterations[-1] if iterations else None
    latest_iteration_status = (latest_iteration.get("status")
                               if isinstance(latest_iteration, dict) else None)
    complete = bool(state and state.get("complete") is True)
    terminal_checkpointed = bool(
        complete and isinstance(terminal_observation, dict)
        and terminal_observation.get("state") == "portfolio_exhausted")
    terminal_supervisor_verified = bool(
        terminal_checkpointed
        and terminal_observation.get("supervisor_verified") is True)
    failure = _discovery_safe_error(
        inflight.get("exception") if isinstance(inflight, dict) else None)
    planning_failure = _discovery_safe_error(
        planning.get("failure") if isinstance(planning, dict) else None)
    planner_terminal_failure = bool(
        planning_failure is not None and isinstance(checkpoint, dict)
        and checkpoint.get("state") == "discovery_planner_terminal_failure")
    latest_event_row = events[-1] if events else None
    latest_event = (latest_event_row.get("event")
                    if isinstance(latest_event_row, dict) else None)
    active_planner_turn = bool(
        lock_held and latest_event == "planner_started"
        and isinstance(planning, dict)
        and not isinstance(pending, dict) and not isinstance(inflight, dict)
        and (latest_iteration_status != "planner_refused"
             or _discovery_planner_successor_binding(
                 state, planning, events, latest_iteration,
                 campaign_id, now)))
    active_critic_turn = bool(
        lock_held and latest_event == "critic_started"
        and isinstance(pending, dict)
        and pending.get("phase") == "critic_pending"
        and not isinstance(inflight, dict)
        and (latest_iteration_status != "planner_refused"
             or _discovery_pending_successor_binding(
                 state, pending, events, latest_iteration,
                 campaign_id, now)))
    latest_terminal_turn = (latest_iteration.get("turn")
                            if isinstance(latest_iteration, dict) else None)
    current_inflight_row = (inflight.get("row")
                            if isinstance(inflight, dict) else None)
    current_inflight_turn = (current_inflight_row.get("turn")
                             if isinstance(current_inflight_row, dict) else None)
    current_pending_row = (pending.get("row")
                           if isinstance(pending, dict) else None)
    current_pending_turn = (
        pending.get("turn") if isinstance(pending, dict)
        and isinstance(pending.get("turn"), int)
        and not isinstance(pending.get("turn"), bool) else
        current_pending_row.get("turn")
        if isinstance(current_pending_row, dict) else None)
    active_pending_new_turn = bool(
        lock_held
        and isinstance(current_pending_turn, int)
        and not isinstance(current_pending_turn, bool)
        and isinstance(latest_terminal_turn, int)
        and not isinstance(latest_terminal_turn, bool)
        and current_pending_turn > latest_terminal_turn
        and (latest_iteration_status != "planner_refused"
             or _discovery_pending_successor_binding(
                 state, pending, events, latest_iteration,
                 campaign_id, now)))
    active_inflight_new_turn = bool(
        isinstance(current_inflight_turn, int)
        and not isinstance(current_inflight_turn, bool)
        and isinstance(latest_terminal_turn, int)
        and not isinstance(latest_terminal_turn, bool)
        and current_inflight_turn > latest_terminal_turn
        and (latest_iteration_status != "planner_refused"
             or _discovery_inflight_successor_binding(
                 state, inflight, events, latest_iteration,
                 campaign_id, now)))
    active_new_turn = (active_planner_turn or active_critic_turn
                       or active_pending_new_turn
                       or active_inflight_new_turn)
    validation_event = (latest_event if latest_event in
                        {"planner_validation_failed", "planner_validation_refused",
                         "planner_refused"}
                        else None)
    planner_validation_interrupted = bool(
        not lock_held and state is None and checkpoint is None
        and operation_observation is None and latest_event == "planner_completed")
    hypothesis = None
    turn = state.get("next") if isinstance(state, dict) else None
    lease = None
    pending_phase = pending.get("phase") if isinstance(pending, dict) else None
    preauthored_pending = bool(
        isinstance(pending, dict) and isinstance(v26_state, dict)
        and isinstance(v26_state.get("provenance"), dict))
    postbuild_resource_wait = (
        v26_state.get("resource_wait")
        if isinstance(v26_state, dict)
        and isinstance(v26_state.get("resource_wait"), dict)
        and v26_state["resource_wait"].get("kind") ==
            "postbuild_resource_wait" else None)
    pending_authorized = bool(
        isinstance(pending, dict) and isinstance(pending.get("authorization"), dict))
    if isinstance(inflight, dict):
        candidate = inflight.get("candidate")
        row = inflight.get("row")
        if isinstance(candidate, dict):
            hypothesis = candidate.get("hypothesis_id")
        if hypothesis is None and isinstance(row, dict):
            hypothesis = row.get("hypothesis_id")
        lease = inflight.get("lease")
        pipeline["authorization"]["state"] = "complete"
        pipeline["resource_admission"]["state"] = (
            "complete" if isinstance(lease, dict) and lease.get("admitted") is True
            else "running")
    elif isinstance(pending, dict):
        row = pending.get("row")
        candidate = pending.get("candidate")
        if isinstance(candidate, dict):
            hypothesis = candidate.get("hypothesis_id")
        if hypothesis is None and isinstance(row, dict):
            hypothesis = row.get("hypothesis_id")
        pipeline["planner_validation"]["state"] = "complete"
        if preauthored_pending:
            pipeline["planner"]["state"] = "complete"
            pipeline["planner"]["detail"] = (
                "actor bypassed by exact reviewed continuation")
            pipeline["critic"]["state"] = "complete"
            pipeline["critic"]["detail"] = (
                "actor bypassed by controller-owned imported provenance")
            if pending_authorized:
                lease = row.get("lease") if isinstance(row, dict) else None
                pipeline["authorization"]["state"] = "complete"
                pipeline["resource_admission"]["state"] = "waiting"
            else:
                pipeline["authorization"]["state"] = "running"
        elif pending_phase == "critic_pending":
            # planner_checkpointed proves local plan/manifest validation, not
            # critic acceptance or authorization. Preserve a running actor fact.
            if pipeline["critic"]["state"] == "not_reached":
                pipeline["critic"]["state"] = "waiting"
        elif pending_phase == "critic_complete":
            pipeline["critic"]["state"] = "complete"
            pipeline["authorization"]["state"] = "running"
        elif pending_authorized:
            lease = row.get("lease") if isinstance(row, dict) else None
            pipeline["critic"]["state"] = "complete"
            pipeline["authorization"]["state"] = "complete"
            pipeline["resource_admission"]["state"] = "waiting"
        else:
            pipeline["critic"]["state"] = "complete"
            pipeline["authorization"]["state"] = "running"

    # Before planner output is checkpointed there is intentionally no pending
    # or inflight candidate.  The producer's active lifecycle event is the only
    # durable hypothesis identity available in that window.  Accept it only
    # from the newest event for this sealed deployment campaign, only while the
    # controller lock proves activity, and only from the allowlisted active
    # event/field grammar.
    if (hypothesis is None and lock_held and not isinstance(pending, dict)
            and not isinstance(inflight, dict) and isinstance(campaign_id, str)):
        active_hypothesis_events = {
            "planner_started", "critic_started", "correctness_started",
            "candidate_attribution_started", "anchor_attribution_started",
            "measurement_graphs_off_screen_started",
            "target_runtime_graphs_on_screen_started", "decision_started",
            "replication_s1_started", "replication_s2_started",
            "next_hypothesis_started",
        }
        latest_campaign_event = next(
            (row for row in reversed(events)
             if row.get("campaign_id") == campaign_id), None)
        event_hypothesis = (latest_campaign_event.get("hypothesis_id")
                            if isinstance(latest_campaign_event, dict)
                            and latest_campaign_event.get("event") in
                            active_hypothesis_events else None)
        if (isinstance(event_hypothesis, str)
                and re.fullmatch(r"akh-[a-z0-9][a-z0-9_.-]{0,196}",
                                 event_hypothesis)):
            hypothesis = event_hypothesis

    # A terminal planner attempt has no pending/inflight row, but its durable
    # planning checkpoint still binds the selected portfolio hypothesis.  Use
    # that identity only when its authoring assignment agrees with this sealed
    # deployment campaign; never resurrect a hypothesis from an unrelated or
    # merely historical event.
    if (hypothesis is None and planner_terminal_failure
            and isinstance(planning, dict) and isinstance(campaign_id, str)):
        binding = planning.get("portfolio_binding")
        context = planning.get("context")
        assignment = (context.get("authoring_assignment")
                      if isinstance(context, dict) else None)
        terminal_hypothesis = (binding.get("hypothesis_id")
                               if isinstance(binding, dict) else None)
        if (isinstance(assignment, dict)
                and assignment.get("campaign_id") == campaign_id
                and isinstance(terminal_hypothesis, str)
                and re.fullmatch(r"akh-[a-z0-9][a-z0-9_.-]{0,196}",
                                 terminal_hypothesis)):
            hypothesis = terminal_hypothesis
        planning_turn = planning.get("turn")
        if (isinstance(planning_turn, int)
                and not isinstance(planning_turn, bool) and planning_turn > 0):
            turn = planning_turn

    if (hypothesis is None and validation_event is not None
            and isinstance(campaign_id, str) and events):
        terminal_event = events[-1]
        terminal_hypothesis = terminal_event.get("hypothesis_id")
        if (terminal_event.get("campaign_id") == campaign_id
                and isinstance(terminal_hypothesis, str)
                and re.fullmatch(r"akh-[a-z0-9][a-z0-9_.-]{0,196}",
                                 terminal_hypothesis)):
            hypothesis = terminal_hypothesis
        if (isinstance(latest_iteration, dict)
                and isinstance(latest_iteration.get("turn"), int)
                and not isinstance(latest_iteration.get("turn"), bool)):
            turn = latest_iteration["turn"]

    last_event_at = max((row.get("ts") for row in events
                         if isinstance(row.get("ts"), str)), default=None)
    state_at = state.get("updated_at") if isinstance(state, dict) else None
    checkpoint_at = checkpoint.get("written_at") if checkpoint else None
    operation_at = ((operation_observation.get("progress_at")
                     or operation_observation.get("started_at"))
                    if isinstance(operation_observation, dict) else None)
    correctness_at = (execution_observation.get("completed_at")
                      if isinstance(execution_observation, dict) else None)
    claim_at = (claim_observation.get("acquired_at")
                if isinstance(claim_observation, dict) else None)
    postbuild_times = []
    if isinstance(postbuild_observation, dict):
        postbuild_times.extend(
            row.get("at")
            for row in postbuild_observation.get("receipts", {}).values()
            if isinstance(row, dict) and isinstance(row.get("at"), str))
        process_progress = postbuild_observation.get("process_progress")
        if isinstance(process_progress, dict):
            if isinstance(process_progress.get("started_at"), str):
                postbuild_times.append(process_progress["started_at"])
            postbuild_times.extend(
                row.get("at") for row in process_progress.get("receipts", [])
                if isinstance(row, dict) and isinstance(row.get("at"), str))
    postbuild_at = max(postbuild_times, default=None)
    semantic_times = [value for value in
                      (last_event_at, state_at, checkpoint_at, operation_at,
                       correctness_at, claim_at, postbuild_at)
                      if isinstance(value, str)]
    last_progress_at = max(semantic_times) if semantic_times else None
    last_progress_epoch = (_parse_semantic_timestamp(last_progress_at)
                           if last_progress_at else None)
    progress_age = max(0.0, now - last_progress_epoch) if last_progress_epoch else None

    status = "idle"
    stage = "planner"
    label = "Awaiting launch"
    waiting_on = "controller launch"
    recoverability = "not_required"
    failure_view = {"detected": False, "stage": None, "detail": None,
                    "recovery": None}
    if isinstance(postbuild_observation, dict):
        for completed_stage in postbuild_observation.get("completed", []):
            if completed_stage in pipeline:
                pipeline[completed_stage]["state"] = "complete"
        for skipped_stage, reason in postbuild_observation.get("skipped", {}).items():
            if skipped_stage in pipeline:
                pipeline[skipped_stage]["state"] = "skipped"
                pipeline[skipped_stage]["detail"] = reason
        transitions.extend(postbuild_observation.get("transitions", []))
    if terminal_checkpointed:
        stage = "decision"
        pipeline[stage]["state"] = "complete"
        pipeline[stage]["completed_at"] = terminal_observation["occurred_at"]
        pipeline["next_hypothesis"]["state"] = "complete"
        pipeline["next_hypothesis"]["completed_at"] = (
            terminal_observation["occurred_at"])
        if terminal_supervisor_verified:
            status = "complete"
            label = "Portfolio exhausted · campaign complete"
            waiting_on = "no further hypothesis"
            recoverability = "not_required"
        elif lock_held:
            status = "running"
            label = "Portfolio exhausted · finalizing campaign"
            waiting_on = "normal supervisor shutdown"
            recoverability = "not_required"
        else:
            status = "failed"
            label = "Campaign terminal supervisor proof refused"
            waiting_on = "repair terminal supervisor evidence"
            recoverability = "terminal_integrity_requires_repair"
            pipeline[stage]["state"] = "failed"
            failure_view = {
                "detected": True, "stage": stage,
                "detail": ("Controller state and journal reached portfolio exhaustion, "
                           "but the exact normal supervisor rc0 terminal was not verified."),
                "recovery": ("Repair the terminal evidence; do not restart or replay the "
                             "completed campaign."),
            }
    elif complete:
        status = "failed"
        stage = "decision"
        label = "Campaign completion evidence refused"
        waiting_on = "repair state/journal terminal evidence"
        recoverability = "terminal_integrity_requires_repair"
        pipeline[stage]["state"] = "failed"
        failure_view = {
            "detected": True, "stage": stage,
            "detail": ("The controller claims completion, but its exact state/hash and "
                       "portfolio-exhausted journal join did not validate."),
            "recovery": ("Repair the terminal evidence; do not restart or replay the "
                         "claimed completed campaign."),
        }
    elif planner_terminal_failure:
        # The planner actor can return successfully and still be rejected by
        # the controller-owned telemetry/output validator.  v16 persisted this
        # exact STOP_STATE plus a bounded typed error in planning.failure.  It
        # is a failed terminal, not an idle campaign and not a provider retry.
        validation_failure = planning_failure["type"] == "TelemetryError"
        stage = "planner_validation" if validation_failure else "planner"
        status = "failed"
        label = ("Planner telemetry validation failed" if validation_failure
                 else "Planner terminated before a reusable checkpoint")
        waiting_on = "fresh sealed deployment after planner seam repair"
        recoverability = "planner_validation_requires_fresh_deployment"
        if validation_failure:
            pipeline["planner"]["state"] = "complete"
            pipeline["planner"]["completed_at"] = state_at or checkpoint_at
        pipeline[stage]["state"] = "failed"
        pipeline[stage]["started_at"] = state_at or checkpoint_at
        pipeline[stage]["completed_at"] = checkpoint_at or state_at
        failure_view = {
            "detected": True,
            "stage": stage,
            "detail": f"{planning_failure['type']}: {planning_failure['detail']}",
            "recovery": ("Repair the planner telemetry/output contract, then "
                         "launch a fresh sealed deployment; no GPU stage was reached."),
            "source_proof_created": False,
            "correctness_output_created": False,
            "runner_started": False,
            "gpu_screen_started": False,
        }
        transitions.append({
            "ts": checkpoint_at or state_at,
            "stage": stage, "phase": stage, "state": "failed",
            "event": "discovery_planner_terminal_failure",
            "label": label,
            "detail": failure_view["detail"],
        })
    elif failure is not None:
        status = "failed"
        observed_stage = (operation_observation.get("stage")
                          if isinstance(operation_observation, dict) else None)
        postbuild_failure_stage = (
            postbuild_observation.get("first_incomplete_stage")
            if isinstance(postbuild_observation, dict) else None)
        correctness_parse_failed = bool(
            isinstance(correctness_observation, dict)
            and failure.get("type") == "EvidenceProducerError"
            and "correctness stdout" in failure.get("detail", "").lower())
        failure_detail_lower = str(failure.get("detail") or "").lower()
        attribution_identity_failure = (
            "runtime maps" in failure_detail_lower
            or "owned kfd process" in failure_detail_lower
            or "runtime identity" in failure_detail_lower)
        attribution_timing_failure = (
            "avg_ts" in failure_detail_lower
            and "samples_ts" in failure_detail_lower)
        stage = ("correctness_validation" if correctness_parse_failed else
                 postbuild_failure_stage
                 if postbuild_failure_stage in _DISCOVERY_POSTBUILD_STAGES else
                 observed_stage if observed_stage in {"build", "evidence_binding"}
                 else "source_materialization")
        attribution_arm = ("Candidate" if stage == "candidate_attribution"
                           else "Anchor")
        attribution_label = (
            f"{attribution_arm} attribution failed during runtime identity binding"
            if attribution_identity_failure else
            f"{attribution_arm} attribution timing receipt validation failed"
            if attribution_timing_failure else
            f"{attribution_arm} attribution evidence validation failed")
        label = ("Correctness result parsing failed after GPU proof"
                 if stage == "correctness_validation" else
                 attribution_label
                 if stage in {"candidate_attribution", "anchor_attribution"} else
                 "Graphs-off measurement evidence validation failed"
                 if stage == "measurement_graphs_off_screen" else
                 "Graphs-on target-runtime evidence validation failed"
                 if stage == "target_runtime_graphs_on_screen" else
                 "Evidence binding failed after completed build"
                 if stage == "evidence_binding" else
                 "Source build failed" if stage == "build" else
                 "Source materialization failed")
        waiting_on = "fresh candidate attempt after controller repair"
        recoverability = "ambiguous_checkpoint_requires_fresh_deployment"
        pipeline["source_materialization"]["state"] = (
            "complete" if stage in {"build", "evidence_binding",
                                    "correctness_validation"}
            or stage in _DISCOVERY_POSTBUILD_STAGES else "failed")
        if (stage in {"evidence_binding", "correctness_validation"}
                or stage in _DISCOVERY_POSTBUILD_STAGES):
            pipeline["build"]["state"] = "complete"
        if stage == "correctness_validation":
            pipeline["evidence_binding"]["state"] = "complete"
            pipeline["correctness"]["state"] = "complete"
            pipeline["correctness"]["started_at"] = correctness_observation[
                "started_at"]
            pipeline["correctness"]["completed_at"] = correctness_observation[
                "completed_at"]
            pipeline["correctness"]["elapsed_s"] = correctness_observation[
                "elapsed_s"]
            pipeline[stage]["started_at"] = correctness_observation[
                "completed_at"]
        elif stage in _DISCOVERY_POSTBUILD_STAGES:
            pipeline["evidence_binding"]["state"] = "complete"
            process_progress = (
                postbuild_observation.get("process_progress")
                if isinstance(postbuild_observation, dict) else None)
            pipeline[stage]["started_at"] = (
                process_progress.get("started_at")
                if isinstance(process_progress, dict)
                and process_progress.get("stage") == stage
                and isinstance(process_progress.get("started_at"), str)
                else postbuild_at or correctness_at)
        elif isinstance(operation_observation, dict):
            pipeline[stage]["started_at"] = operation_observation.get("started_at")
        pipeline[stage]["state"] = "failed"
        pipeline[stage]["completed_at"] = state_at or checkpoint_at
        failure_view = {
            "detected": True, "stage": stage,
            "detail": f"{failure['type']}: {failure['detail']}",
            "recovery": "Do not resume this ambiguous operation; launch a fresh sealed deployment after repair.",
            "source_proof_created": stage in _DISCOVERY_POSTBUILD_STAGES,
            "correctness_output_created": (
                stage == "correctness_validation"
                or isinstance(execution_observation, dict)),
            "runner_started": stage in {
                "measurement_graphs_off_screen",
                "target_runtime_graphs_on_screen"},
            "gpu_screen_started": (
                stage == "correctness_validation"
                or isinstance(execution_observation, dict)),
            "correctness_execution_completed": (
                stage == "correctness_validation"
                or isinstance(execution_observation, dict)),
        }
    elif (not active_new_turn and (
            validation_event == "planner_refused"
            or latest_iteration_status == "planner_refused")):
        pipeline["planner"]["state"] = "complete"
        pipeline["planner_validation"]["state"] = "failed"
        pipeline["next_hypothesis"]["state"] = (
            "running" if lock_held else "waiting")
        status = "running" if lock_held else "stopped"
        stage = "next_hypothesis"
        label = "Planner output refused; advancing to next hypothesis"
        waiting_on = ("next eligible portfolio hypothesis" if lock_held else
                      "controller restart from planner-refusal checkpoint")
        recoverability = "resume_controller_checkpoint"
        if isinstance(latest_iteration, dict):
            if isinstance(latest_iteration.get("hypothesis_id"), str):
                hypothesis = latest_iteration["hypothesis_id"]
            if (isinstance(latest_iteration.get("turn"), int)
                    and not isinstance(latest_iteration.get("turn"), bool)):
                turn = latest_iteration["turn"]
    elif validation_event is not None or planner_validation_interrupted:
        status = "failed"
        stage = "planner_validation"
        label = ("Planner output refused by local validation"
                 if validation_event in {"planner_validation_refused",
                                         "planner_refused"} else
                 "Planner validation failed" if validation_event else
                 "Controller stopped during planner validation")
        waiting_on = "fresh sealed deployment after controller repair"
        recoverability = "planner_validation_requires_fresh_deployment"
        planner_completed_at = next(
            (row.get("ts") for row in reversed(events)
             if row.get("event") == "planner_completed"), None)
        pipeline[stage]["state"] = "failed"
        pipeline["planner"]["state"] = "complete"
        pipeline["planner"]["completed_at"] = planner_completed_at or last_event_at
        pipeline[stage]["started_at"] = planner_completed_at or last_event_at
        pipeline[stage]["completed_at"] = last_event_at
        refusal_digest = (
            events[-1].get("result", {}).get("refusal_reason_sha256")
            if validation_event == "planner_refused"
            and isinstance(events[-1].get("result"), dict) else None)
        if isinstance(refusal_digest, str):
            detail = ("Planner output was refused by local validation; reason "
                      f"sha256 {refusal_digest[:12]}… (raw reason is not telemetry).")
        elif validation_event == "planner_refused":
            detail = "Planner output was refused by local validation."
        elif validation_event == "planner_validation_refused":
            detail = ("Planner output was refused by local validation "
                      "(producer lifecycle event).")
        elif validation_event == "planner_validation_failed":
            detail = "Planner validation failed (producer lifecycle event)."
        else:
            detail = ("Controller stopped after the planner actor completed; the "
                      "producer did not persist the exact planner-validation exception.")
        if validation_event == "planner_refused":
            waiting_on = ("automatic next eligible hypothesis" if lock_held else
                          "controller restart from planner-refusal checkpoint")
            recoverability = "resume_controller_checkpoint"
        failure_view = {
            "detected": True, "stage": stage, "detail": detail,
            "recovery": (
                "The refusal is durable and spent no scientific budget; continue "
                "with the next eligible hypothesis."
                if validation_event == "planner_refused" else
                "Do not resume this attempt; repair the controller and launch a "
                "fresh sealed deployment."),
            "source_proof_created": False, "runner_started": False,
            "gpu_screen_started": False,
        }
        if planner_validation_interrupted:
            transitions.append({
                "ts": last_event_at, "stage": stage, "phase": stage,
                "state": "inferred_failure",
                "event": "planner_validation_interrupted",
                "label": "controller exited before a planner-validation checkpoint",
                "detail": "exact exception was not persisted by the producer",
            })
    elif active_planner_turn:
        # A typed terminal closes the prior turn only. Once the same controller
        # durably enters the next planning turn, that newer lifecycle event owns
        # the headline and current pipeline; the refusal remains historical.
        for name, row in pipeline.items():
            if name != "planner":
                row.clear()
                row.update({"id": name, "label": _DISCOVERY_PIPELINE_DICT[name],
                            "state": "not_reached"})
        stage = "planner"
        pipeline[stage]["state"] = "running"
        pipeline[stage]["started_at"] = last_event_at
        pipeline[stage].pop("completed_at", None)
        pipeline[stage].pop("elapsed_s", None)
        status = "running"
        label = "Planner model call"
        waiting_on = "planner completion"
        recoverability = "not_required"
    elif active_critic_turn:
        # A later turn's durable critic checkpoint/event also outranks the
        # previous turn's terminal iteration.  Rebuild the current pipeline
        # solely from facts the new pending row proves; never carry the prior
        # authoring refusal into this turn's headline.
        for name, row in pipeline.items():
            row.clear()
            row.update({"id": name, "label": _DISCOVERY_PIPELINE_DICT[name],
                        "state": "not_reached"})
        pipeline["planner"]["state"] = "complete"
        pipeline["planner_validation"]["state"] = "complete"
        pipeline["critic"]["state"] = "running"
        pipeline["critic"]["started_at"] = last_event_at
        stage = "critic"
        status = "running"
        label = "Critic review"
        waiting_on = "critic review completion"
        recoverability = "not_required"
    elif active_pending_new_turn:
        # Planner validation has durably checkpointed the newer turn, but the
        # critic actor has not emitted critic_started yet.  This short seam is
        # a real waiting state; do not inherit the previous turn's completed
        # critic or typed terminal while crossing it.
        for name, row in pipeline.items():
            row.clear()
            row.update({"id": name, "label": _DISCOVERY_PIPELINE_DICT[name],
                        "state": "not_reached"})
        pipeline["planner"]["state"] = "complete"
        pipeline["planner_validation"]["state"] = "complete"
        pipeline["critic"]["state"] = "waiting"
        stage = "critic"
        status = "waiting"
        label = "Waiting to start critic review"
        waiting_on = "critic review"
        recoverability = "not_required"
    elif latest_iteration_status == "planner_transient":
        stage = "planner"
        pipeline[stage]["state"] = "waiting"
        status = "running" if lock_held else "stopped"
        label = "Planner provider interrupted; same hypothesis remains retryable"
        waiting_on = ("automatic planner retry" if lock_held else
                      "controller restart at planner retry checkpoint")
        recoverability = "resume_planner_provider_retry"
        hypothesis = latest_iteration.get("hypothesis_id")
    elif (not (active_pending_new_turn or active_inflight_new_turn)
          and latest_iteration_status in {
            "authoring_refused", "correctness_falsified",
            "attribution_route_falsified", "measurement_output_refused"}):
        refused_stage = latest_iteration.get("stage")
        measurement_refusal = (
            refusal_observation.get("measurement_output")
            if isinstance(refusal_observation, dict) else None)
        failed_stage = {
            "source_apply": "source_materialization",
            "compile": "build",
            "correctness": "correctness_validation",
            "dispatch_attribution": "dispatch_proof",
        }.get(refused_stage)
        if (refused_stage == "measurement_output"
                and isinstance(measurement_refusal, dict)):
            failed_stage = measurement_refusal.get("screen_stage")
            for completed_stage in measurement_refusal.get(
                    "completed_pipeline", []):
                if completed_stage in pipeline:
                    pipeline[completed_stage]["state"] = "complete"
        if failed_stage is not None:
            pipeline[failed_stage]["state"] = "failed"
            if isinstance(measurement_refusal, dict):
                reusable = measurement_refusal.get("reusable_completed_arms") or []
                pipeline[failed_stage]["detail"] = (
                    f"{measurement_refusal.get('arm')} arm output refused · "
                    f"{measurement_refusal.get('reason_code')}"
                    + (f" · reusable completed arm: {', '.join(reusable)}"
                       if reusable else ""))
        stage = "next_hypothesis"
        pipeline[stage]["state"] = "running" if lock_held else "waiting"
        status = "running" if lock_held else "stopped"
        label = (f"{latest_iteration_status.replace('_', ' ')}; advancing to next hypothesis"
                 if lock_held else
                 f"{latest_iteration_status.replace('_', ' ')}; next hypothesis checkpointed")
        waiting_on = ("next eligible portfolio hypothesis" if lock_held else
                      "controller restart from typed terminal")
        recoverability = "resume_controller_checkpoint"
    elif isinstance(pending, dict):
        if postbuild_resource_wait is not None:
            status = "waiting" if lock_held else "stopped"
            stage = "resource_admission"
            label = (
                "Completed builds checkpointed; waiting for foreign GPU"
                if str(postbuild_resource_wait.get("reason", "")).startswith(
                    "foreign_kfd_") else
                "Completed builds checkpointed; waiting for GPU")
            waiting_on = (
                "foreign GPU/KFD owner release"
                if str(postbuild_resource_wait.get("reason", "")).startswith(
                    "foreign_kfd_") else "GPU availability")
            recoverability = "resume_postbuild_resource_wait"
            for completed_stage in (
                    "source_materialization", "build", "evidence_binding"):
                pipeline[completed_stage]["state"] = "complete"
            pipeline["resource_admission"]["state"] = "waiting"
            pipeline["resource_admission"]["detail"] = (
                "exact candidate/build checkpoint preserved; no GPU executor "
                "or proof root started")
        elif pending_phase == "preauthored_ready" and preauthored_pending:
            status = "running" if lock_held else "stopped"
            stage = "authorization"
            label = "Reviewed continuation checkpointed; actors bypassed"
            waiting_on = "governance authorization"
            recoverability = ("not_required" if lock_held
                              else "resume_controller_checkpoint")
        elif preauthored_pending and not pending_authorized:
            status = "running" if lock_held else "stopped"
            stage = "authorization"
            label = "Reviewed continuation replication; actors bypassed"
            waiting_on = "fresh governance authorization"
            recoverability = ("not_required" if lock_held
                              else "resume_controller_checkpoint")
        elif pending_phase == "critic_pending":
            stage = "critic"
            if latest_event == "critic_started" and lock_held:
                status = "running"
                label = "Critic review"
                waiting_on = "critic review completion"
            elif latest_event == "critic_completed":
                status = "waiting" if lock_held else "stopped"
                label = "Critic completed; awaiting durable checkpoint"
                waiting_on = "critic checkpoint persistence"
            else:
                status = "waiting" if lock_held else "stopped"
                if latest_event == "critic_failed":
                    label = "Critic provider interrupted; checkpoint preserved"
                    waiting_on = ("automatic critic retry" if lock_held else
                                  "controller restart at critic checkpoint")
                    recoverability = "resume_critic_provider_retry"
                else:
                    label = "Waiting to start critic review"
                    waiting_on = "critic review"
        elif pending_phase == "critic_complete":
            status = "running" if lock_held else "stopped"
            stage = "authorization"
            label = "Governance authorization"
            waiting_on = "authorization decision"
        elif pending_authorized:
            status = "waiting"
            stage = "resource_admission"
            label = "Waiting for governed resource admission"
            waiting_on = "GPU/inference-window availability"
            recoverability = "same_candidate_retry"
        else:
            status = "running" if lock_held else "stopped"
            stage = "authorization"
            label = "Governance authorization"
            waiting_on = "authorization decision"
    elif isinstance(inflight, dict):
        inflight_phase = inflight.get("phase")
        lease_phase = lease.get("phase") if isinstance(lease, dict) else None
        observed_stage = (operation_observation.get("stage")
                          if isinstance(operation_observation, dict) else None)
        postbuild_stage = (postbuild_observation.get("first_incomplete_stage")
                           if isinstance(postbuild_observation, dict) else None)
        live_event_stage = event_stage.get(latest_event)
        live_postbuild_stage = (
            live_event_stage[0] if live_event_stage is not None
            and live_event_stage[1] == "running"
            and live_event_stage[0] in _DISCOVERY_POSTBUILD_STAGES
            and live_event_stage[0] not in (
                postbuild_observation.get("completed", [])
                if isinstance(postbuild_observation, dict) else []) else None)
        if (live_postbuild_stage or postbuild_stage) in _DISCOVERY_POSTBUILD_STAGES:
            stage = live_postbuild_stage or postbuild_stage
            # The first incomplete stage cannot begin before the newest
            # validated predecessor receipt.  Use that durable boundary for
            # the clock; never inherit pre-screen state.updated_at.
            pipeline[stage]["started_at"] = (
                postbuild_observation.get("process_progress", {}).get(
                    "started_at")
                if isinstance(postbuild_observation.get("process_progress"), dict)
                and postbuild_observation["process_progress"].get("stage") == stage
                and isinstance(postbuild_observation["process_progress"].get(
                    "started_at"), str)
                else postbuild_at or correctness_at or state_at)
            replication = postbuild_observation.get("repetition")
            label = _DISCOVERY_PIPELINE_DICT.get(stage, stage)
            if isinstance(replication, int):
                label += f" · S{replication}"
            process_progress = postbuild_observation.get("process_progress")
            if (isinstance(process_progress, dict)
                    and process_progress.get("stage") == stage):
                completed_arms = process_progress.get("completed_arms") or []
                next_arm = process_progress.get("next_arm")
                if isinstance(next_arm, str):
                    label += (f" · {next_arm} after "
                              f"{', '.join(completed_arms)} checkpoint reuse")
                pipeline[stage]["detail"] = (
                    f"completed process {'arm' if len(completed_arms) == 1 else 'arms'} "
                    f"{', '.join(completed_arms)} will be revalidated and reused")
            label = (label if lock_held else
                     f"Controller stopped before {label.lower()}")
            waiting_on = (f"{_DISCOVERY_PIPELINE_DICT.get(stage, stage)} completion"
                          if lock_held else
                          f"resume from first incomplete stage: {stage}")
            pipeline["source_materialization"]["state"] = "complete"
            pipeline["build"]["state"] = "complete"
            pipeline["evidence_binding"]["state"] = "complete"
        elif observed_stage in {"build", "evidence_binding"}:
            stage = observed_stage
            pipeline[stage]["started_at"] = operation_observation["started_at"]
            if stage == "evidence_binding":
                pipeline["source_materialization"]["state"] = "complete"
                pipeline["build"]["state"] = "complete"
                label = ("Binding completed builds to the proof plan" if lock_held
                         else "Controller stopped during evidence binding")
                waiting_on = ("proof-plan binding completion" if lock_held
                              else "evidence-binding recovery audit")
            else:
                if operation_observation.get("source_materialized") is True:
                    pipeline["source_materialization"]["state"] = "complete"
                    pipeline["source_materialization"]["detail"] = (
                        "configure closure verified for "
                        f"{operation_observation.get('attempt')}")
                else:
                    pipeline["source_materialization"]["state"] = "running"
                    pipeline["source_materialization"]["detail"] = (
                        "build transaction is active; materialization receipt is not sealed")
                arm = operation_observation.get("arm")
                build_label = ("Compiling candidate arm 2 of 2" if arm == "candidate"
                               else "Compiling anchor arm 1 of 2" if arm == "anchor"
                               else "Compiling the sealed anchor and candidate")
                progress = operation_observation.get("progress_percent")
                if (isinstance(progress, int) and not isinstance(progress, bool)
                        and 0 <= progress <= 100):
                    build_label += f" · {progress}%"
                build_detail = []
                if operation_observation.get("process_verified") is True:
                    build_detail.append(
                        f"verified {operation_observation.get('attempt')}")
                if operation_observation.get("hip_compile") is True:
                    build_detail.append("HIP compile")
                if isinstance(progress, int) and not isinstance(progress, bool):
                    build_detail.append(f"{progress}% producer stream")
                if operation_observation.get("stream_stale") is True:
                    build_detail.append(
                        "stream quiet; PID/cgroup identity remains live")
                if build_detail:
                    pipeline["build"]["detail"] = " · ".join(build_detail)
                label = (build_label if lock_held
                         else "Controller stopped during source build")
                waiting_on = (("candidate build completion" if arm == "candidate"
                               else "anchor build completion" if arm == "anchor"
                               else "anchor/candidate build completion") if lock_held
                              else "build recovery audit")
        else:
            stage = ("benchmark" if inflight_phase == "measurement"
                     or lease_phase == "measurement" else "source_materialization")
            label = ("Validating and materializing source" if lock_held
                     else "Controller stopped during candidate screening")
            waiting_on = ("source validation/materialization checkpoint" if lock_held
                          else "recovery audit")
        pipeline[stage]["state"] = "running" if lock_held else "interrupted"
        status = "running" if lock_held else "stopped"
        recoverability = ("resume_first_incomplete_stage"
                          if postbuild_stage in _DISCOVERY_POSTBUILD_STAGES
                          else "reconcile_required")
    elif (checkpoint is not None
          and checkpoint.get("state") in {"discovery_screened",
                                          "discovery_recovered_screen"}
          and latest_event != "planner_started"):
        pipeline["decision"]["state"] = "complete"
        stage = "next_hypothesis"
        pipeline[stage]["state"] = "running" if lock_held else "waiting"
        status = "running" if lock_held else "stopped"
        label = ("Selecting the next eligible hypothesis" if lock_held else
                 "Stopped at the next-hypothesis checkpoint")
        waiting_on = ("next planner selection" if lock_held else
                      "controller restart from the durable screened result")
        recoverability = "resume_controller_checkpoint"
    elif lock_held:
        mapped = event_stage.get(latest_event)
        if mapped is not None and mapped[0] not in {"planner", "critic"}:
            stage = mapped[0]
            label = _DISCOVERY_PIPELINE_DICT.get(stage, stage)
            waiting_on = (f"{label} completion" if mapped[1] == "running"
                          else "next durable lifecycle transition")
        elif latest_event == "planner_started":
            stage, label, waiting_on = "planner", "Planner model call", "planner completion"
        elif latest_event == "critic_started":
            stage, label, waiting_on = "critic", "Critic model call", "critic decision"
        elif latest_event == "planner_completed":
            stage, label, waiting_on = ("critic", "Preparing critic review",
                                        "critic lifecycle checkpoint")
        elif latest_event == "critic_completed":
            stage, label, waiting_on = ("authorization", "Governance and admission",
                                        "pre-screen checkpoint")
        else:
            stage, label, waiting_on = ("planner", "Controller starting",
                                        "first durable checkpoint from planner")
        status = "running"
        pipeline[stage]["state"] = "running"

    source_claim_held = bool(
        isinstance(claim_observation, dict)
        and claim_observation.get("claim_held") is True
        and claim_observation.get("identity_live") is True)
    if source_claim_held and not _discovery_claim_matches_correctness(
            claim_observation, receipt_correctness_observation):
        source_claim_held = False
    claim_required_stage = stage in {
        "candidate_attribution", "anchor_attribution", "dispatch_proof",
        "profile", "measurement_graphs_off_screen",
        "target_runtime_graphs_on_screen", "benchmark",
    }
    gpu_claim_blocked = bool(
        lock_held and status in {"running", "stalled", "waiting"}
        and claim_required_stage
        and isinstance(receipt_correctness_observation, dict)
        and not source_claim_held)
    if gpu_claim_blocked:
        # Downstream receipts prove the last durable boundary, but only the
        # exact outer claim sealed by this operation's correctness receipt can
        # prove a current GPU stage.  A newer/expired same-campaign claim is not
        # permission to headline the screen that belongs to the older one.
        if pipeline[stage].get("state") == "running":
            pipeline[stage]["state"] = "not_reached"
            pipeline[stage].pop("started_at", None)
        stage = "resource_admission"
        pipeline[stage]["state"] = "waiting"
        status = "waiting"
        label = "Awaiting the current operation's GPU claim"
        waiting_on = "identity-bound source-proof claim"
        recoverability = "not_required"
    active_correctness_started = bool(
        stage == "correctness" and lock_held and source_claim_held
        and isinstance(claim_at, str))
    if active_correctness_started:
        # The sealed build/materialization/policy chain identifies correctness
        # as the first incomplete stage; the live source-proof claim is the
        # first durable fact that execution actually began.
        pipeline["correctness"]["state"] = "running"
        pipeline["correctness"]["started_at"] = claim_at

    stall_threshold = _DISCOVERY_STAGE_STALL_S.get(stage, _DISCOVERY_STALL_S)
    if lock_held and progress_age is not None and progress_age > stall_threshold:
        status = "stalled"
        stall = {"state": "stalled", "threshold_s": stall_threshold,
                 "detail": "Controller lock is held but no durable transition advanced; exact substage heartbeat is not instrumented."}
    elif status == "failed":
        stall = {"state": "failed", "threshold_s": stall_threshold,
                 "detail": failure_view["detail"]}
    else:
        stall = {"state": "healthy", "threshold_s": stall_threshold,
                 "detail": "durable lifecycle is advancing" if lock_held else "controller is not active"}

    if checkpoint:
        checkpoint_stage = {
            "discovery_planner_terminal_failure": "planner_validation",
            "discovery_pre_screen_intent": "source_materialization",
            "discovery_waiting_resource": "resource_admission",
            "discovery_screened": "decision",
            "discovery_recovered_screen": "decision",
            "discovery_complete": "decision",
        }.get(checkpoint.get("state"), stage)
        transitions.append({"ts": checkpoint["written_at"], "stage": checkpoint_stage,
                            "phase": checkpoint_stage,
                            "state": "checkpoint", "event": checkpoint["state"],
                            "label": f"STOP_STATE seq {checkpoint.get('seq')}",
                            "detail": f"STOP_STATE seq {checkpoint.get('seq')}"})
        if checkpoint.get("state") in {"discovery_screened",
                                       "discovery_recovered_screen"}:
            transitions.append({
                "ts": checkpoint["written_at"], "stage": "next_hypothesis",
                "phase": "next_hypothesis",
                "state": "running" if lock_held else "waiting",
                "event": "next_hypothesis_transition",
                "label": "screen decision durable; advancing automatically",
                "detail": "next portfolio binding will be selected by the controller",
            })
    if terminal_checkpointed:
        transitions.append({
            "ts": terminal_observation["portfolio_at"], "stage": "decision",
            "phase": "decision", "state": "complete",
            "event": "discovery_portfolio_exhausted",
            "label": (f"STOP_STATE seq "
                      f"{terminal_observation['portfolio_seq']}"),
            "detail": "eligible portfolio exhausted",
        })
    if isinstance(operation_observation, dict):
        observed_stage = operation_observation["stage"]
        operation_detail = (
            f"{operation_observation.get('arm') or observed_stage} "
            f"{operation_observation['build_key'][:12]}…")
        if isinstance(operation_observation.get("attempt"), str):
            operation_detail += f" · {operation_observation['attempt']}"
        if (isinstance(operation_observation.get("progress_percent"), int)
                and not isinstance(operation_observation.get("progress_percent"), bool)):
            operation_detail += (
                f" · {operation_observation['progress_percent']}%")
        transitions.append({
            "ts": (operation_observation.get("progress_at")
                   or operation_observation["started_at"]),
            "stage": observed_stage,
            "phase": observed_stage, "state": "running",
            "event": ("build_transaction_complete" if observed_stage == "evidence_binding"
                      else "build_transaction_observed"),
            "label": ("both build arms complete" if observed_stage == "evidence_binding"
                      else f"{operation_observation.get('arm')} arm active"
                      if operation_observation.get("arm") else
                      "sealed build transaction active"),
            "detail": operation_detail,
        })
    if isinstance(execution_observation, dict):
        transitions.append({
            "ts": execution_observation["completed_at"],
            "stage": "correctness", "phase": "correctness",
            "state": "complete", "event": "correctness_execution_complete",
            "label": (f"GPU correctness execution complete · "
                      f"{execution_observation['summary']}"),
            "detail": (f"claim {str(execution_observation.get('claim_id'))[:12]}… "
                       "released"),
        })
        if stage == "correctness_validation" and status == "failed":
            transitions.append({
                "ts": state_at or execution_observation["completed_at"],
                "stage": stage, "phase": stage, "state": "failed",
                "event": "correctness_validation_failed",
                "label": "correctness output parser rejected the completed result",
                "detail": failure_view["detail"],
            })
    elif active_correctness_started:
        transitions.append({
            "ts": claim_at, "stage": "correctness", "phase": "correctness",
            "state": "running", "event": "correctness_execution_started",
            "label": "GPU correctness execution started",
            "detail": f"claim {str(claim_observation.get('claim_id'))[:12]}… held",
        })
    if (status == "failed" and stage in _DISCOVERY_POSTBUILD_STAGES
            and stage != "correctness_validation"):
        transitions.append({
            "ts": state_at or correctness_at or postbuild_at,
            "stage": stage, "phase": stage, "state": "failed",
            "event": f"{stage}_failed", "label": label,
            "detail": failure_view["detail"],
        })
    prior_terminal = None
    prior_terminals = []
    if active_new_turn:
        prior_terminals.extend(_discovery_planner_refusal_terminals(
            state, events, campaign_id, turn))
    historical_refusal_observations = [
        observation for observation in refusal_history_observations
        if (not isinstance(observation.get("turn"), int)
            or isinstance(observation.get("turn"), bool)
            or not isinstance(turn, int) or isinstance(turn, bool)
            or observation["turn"] < turn)
    ]
    if ((active_new_turn or planner_terminal_failure or terminal_checkpointed)
            and historical_refusal_observations):
        checkpoint_states = {
            "authoring_refused": "discovery_authoring_refused",
            "correctness_falsified": "discovery_correctness_falsified",
            "attribution_route_falsified": "discovery_attribution_route_falsified",
            "measurement_output_refused": "discovery_measurement_output_refused",
        }
        history = (checkpoint.get("history", [])
                   if isinstance(checkpoint, dict) else [])
        consumed: dict[str, int] = {}
        for observation in historical_refusal_observations:
            checkpoint_state = checkpoint_states.get(
                observation.get("disposition"))
            matches = [row for row in history
                       if row.get("state") == checkpoint_state]
            index = consumed.get(checkpoint_state, 0)
            refusal_checkpoint = matches[index] if index < len(matches) else None
            consumed[checkpoint_state] = index + 1
            terminal = {
                "schema": "epyc.dashboard.autokernel_prior_terminal.v1",
                "ts": (refusal_checkpoint.get("written_at")
                       if isinstance(refusal_checkpoint, dict) else
                       observation.get("at") or state_at or last_event_at),
                "event": checkpoint_state or "prior_turn_refusal",
                "turn": observation.get("turn"),
                "hypothesis_id": observation.get("hypothesis_id"),
                "status": observation.get("disposition"),
                "stage": observation.get("stage"),
                "scientific_budget_spent": observation.get(
                    "scientific_budget_spent"),
                "detail": observation.get("detail"),
            }
            prior_terminals.append(terminal)
            transitions.append({
                "ts": terminal["ts"],
                "stage": "next_hypothesis", "phase": "next_hypothesis",
                "state": "complete", "event": terminal["event"],
                "label": (f"prior turn {terminal.get('status', 'refused')}"
                          ", scientific budget unspent"),
                "detail": terminal["detail"],
            })
    if prior_terminals:
        prior_terminals.sort(key=lambda row: row["ts"])
        prior_terminal = prior_terminals[-1]
    transitions.sort(key=lambda row: row["ts"])
    stage_started_at = pipeline[stage].get("started_at")
    if not stage_started_at:
        stage_started_at = (last_event_at if status in {"running", "stalled", "failed"}
                            else state_at or checkpoint_at or last_progress_at)
    stage_start_epoch = (_parse_semantic_timestamp(stage_started_at)
                         if stage_started_at else None)
    elapsed_s = max(0.0, now - stage_start_epoch) if stage_start_epoch else None
    if status in {"failed", "complete", "stopped"} and stage_start_epoch:
        terminal_candidates = [
            _parse_semantic_timestamp(value) for value in
            (state_at, checkpoint_at, last_progress_at)
            if isinstance(value, str)
        ]
        terminal_candidates = [value for value in terminal_candidates
                               if value is not None]
        if terminal_candidates:
            elapsed_s = max(0.0, max(terminal_candidates) - stage_start_epoch)

    probe_released = (isinstance(lease, dict)
                      and isinstance(lease.get("device_claim_probe_released"), dict)
                      and lease["device_claim_probe_released"].get("released_at") is not None)
    probe_open = (lease.get("device_claim_probe_open")
                  if isinstance(lease, dict) else None)
    probe_claim_held = bool(isinstance(probe_open, dict)
                            and probe_open.get("state") == "held"
                            and probe_open.get("released_at") is None
                            and not probe_released)
    claim_held = source_claim_held or probe_claim_held
    gpu_expected = status in {"running", "stalled"} and stage in {
        "correctness", "candidate_attribution", "anchor_attribution",
        "dispatch_proof", "profile", "measurement_graphs_off_screen",
        "target_runtime_graphs_on_screen", "benchmark",
    }
    historical_gpu_screen = isinstance(execution_observation, dict)
    gpu_operation_started = bool(
        historical_gpu_screen
        or isinstance(claim_observation, dict)
        and isinstance(claim_observation.get("acquired_at"), str)
        or isinstance(postbuild_observation, dict)
        and postbuild_observation.get("completed"))
    abandoned = [row for row in iterations if isinstance(row, dict)
                 and row.get("status") == "abandoned"]
    retest = [row for row in iterations if isinstance(row, dict)
              and row.get("status") == "retest"]
    history_rows = [{key: row.get(key) for key in
                     ("turn", "hypothesis_id", "status", "effect_fraction")}
                    for row in (*abandoned, *retest)]
    annulled_history = (
        v26_state.get("annulled_history", [])
        if isinstance(v26_state, dict) else [])
    if not isinstance(annulled_history, list):
        annulled_history = []
    history_rows.extend({
        key: row.get(key) for key in (
            "turn", "hypothesis_id", "status", "scientific_budget_spent",
            "raw_status", "result_file_sha256", "history_retained")}
        for row in annulled_history if isinstance(row, dict))
    latest_result = events[-1].get("result") if events else None
    latest_result = latest_result if isinstance(latest_result, dict) else {}
    refusal_event = next((row for row in reversed(events)
                          if row.get("event") in {
                              "planner_refused",
                              "authoring_refused", "critic_refused",
                              "compile_refused", "correctness_falsified",
                              "attribution_route_falsified"}), None)
    refusal_type = refusal_event.get("event") if refusal_event else None
    planner_refusal_detected = bool(
        isinstance(refusal_event, dict)
        and refusal_event.get("event") == "planner_refused"
        or isinstance(latest_iteration, dict)
        and latest_iteration.get("status") == "planner_refused")
    if refusal_type is None and isinstance(latest_iteration, dict):
        refusal_type = {
            "planner_refused": "planner_output_refusal",
            "planner_contract_refused": "authoring_refused",
            "critic_reject": "critic_refused",
        }.get(latest_iteration.get("status"))
        if latest_iteration.get("status") == "screen_refused":
            candidate_refusal = latest_iteration.get("refusal_type")
            refusal_type = (candidate_refusal if candidate_refusal in {
                "compile_refused", "correctness_falsified",
                "attribution_route_falsified"} else "screen_refused")
    refusal_result = (refusal_event.get("result")
                      if isinstance(refusal_event, dict)
                      and isinstance(refusal_event.get("result"), dict) else {})
    if planner_refusal_detected:
        refusal_type = "planner_output_refusal"
    if isinstance(refusal_observation, dict):
        refusal_type = refusal_observation.get("disposition")
    historical_refusal_only = (
        active_new_turn or planner_terminal_failure or terminal_checkpointed)
    headline_refusal_observation = (
        None if historical_refusal_only else refusal_observation)
    if historical_refusal_only:
        refusal_type = None
        planner_refusal_detected = False
    arm_order = (postbuild_observation.get("arm_order")
                 if isinstance(postbuild_observation, dict) else None)
    if (arm_order is None and isinstance(refusal_observation, dict)
            and isinstance(refusal_observation.get("measurement_output"), dict)):
        arm_order = refusal_observation["measurement_output"].get("arm_order")
    if arm_order is None:
        arm_order = latest_result.get("arm_order_schedule")
    iteration_repetition = (latest_iteration.get("repetition")
                            if isinstance(latest_iteration, dict) else None)
    iteration_decision = bool(
        isinstance(latest_iteration, dict)
        and isinstance(latest_iteration.get("result_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}",
                         latest_iteration["result_sha256"]) is not None
        and isinstance(iteration_repetition, int)
        and not isinstance(iteration_repetition, bool)
        and iteration_repetition in {1, 2})
    pending_confirmation = bool(
        isinstance(pending, dict) and pending.get("confirmation") is True)
    inflight_confirmation = bool(
        isinstance(inflight, dict) and inflight.get("confirmation") is True)
    inflight_result = (inflight.get("result")
                       if isinstance(inflight, dict) else None)
    inflight_decision = bool(
        isinstance(inflight_result, dict)
        and isinstance(inflight_result.get("result_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}",
                         inflight_result["result_sha256"]) is not None)
    permit_repetition = (lease.get("repetition")
                         if isinstance(lease, dict) else None)
    if (not isinstance(permit_repetition, int)
            or isinstance(permit_repetition, bool)
            or permit_repetition not in {1, 2}):
        permit_repetition = 2 if inflight_confirmation else 1
    repetition = (
        iteration_repetition if iteration_decision else
        2 if pending_confirmation or inflight_confirmation else
        permit_repetition if inflight_decision else None)
    latest_is_replication = bool(
        iteration_decision and iteration_repetition == 2
        or isinstance(latest_iteration, dict)
        and isinstance(latest_iteration.get("replication_of"), str))
    if (iteration_decision and iteration_repetition == 2
            or pending_confirmation or inflight_confirmation
            or latest_is_replication):
        pipeline["replication_s1"]["state"] = "complete"
    elif iteration_decision and iteration_repetition == 1:
        pipeline["replication_s1"]["state"] = "complete"
    elif inflight_decision and permit_repetition == 1:
        pipeline["replication_s1"]["state"] = (
            "interrupted" if status == "stopped" else "running")
    if pending_confirmation:
        pipeline["replication_s2"]["state"] = "waiting"
    elif inflight_confirmation:
        pipeline["replication_s2"]["state"] = (
            "interrupted" if status == "stopped" else "running")
    elif iteration_decision and iteration_repetition == 2:
        pipeline["replication_s2"]["state"] = (
            "complete" if latest_is_replication else "not_reached")
    first_incomplete = (latest_result.get("first_incomplete_stage") or
                        (postbuild_observation.get("first_incomplete_stage")
                         if isinstance(postbuild_observation, dict) else stage))
    if terminal_supervisor_verified:
        first_incomplete = None
    iteration_exact_effect = (latest_iteration.get(
        "exact_attribution_effect_fraction")
        if isinstance(latest_iteration, dict) else None)
    iteration_target_effect = (latest_iteration.get(
        "target_runtime_effect_fraction")
        if isinstance(latest_iteration, dict) else None)
    iteration_target_executed = (latest_iteration.get("target_runtime_executed")
                                 if isinstance(latest_iteration, dict) else None)
    measurement_output_view = (
        dict(headline_refusal_observation["measurement_output"])
        if isinstance(headline_refusal_observation, dict)
        and isinstance(headline_refusal_observation.get(
            "measurement_output"), dict) else None)
    if measurement_output_view is not None:
        measurement_recovery = _discovery_measurement_output_recovery(
            state, latest_iteration, headline_refusal_observation)
        if measurement_recovery is not None:
            measurement_output_view["recovery"] = measurement_recovery
    return {
        "status": status,
        "phase": {"id": stage, "label": label, "started_at": stage_started_at,
                  "elapsed_s": elapsed_s},
        "turn": turn, "hypothesis_id": hypothesis,
        "last_progress_at": last_progress_at, "progress_age_s": progress_age,
        "waiting_on": waiting_on, "stall": stall,
        "gpu": {"expected_now": gpu_expected, "claim_held": claim_held,
                "screen_started": gpu_operation_started,
                "claim_released": bool(
                    isinstance(claim_observation, dict)
                    and claim_observation.get("claim_released") is True
                    or historical_gpu_screen and
                    execution_observation.get("claim_released")),
                "claim_id": (claim_observation.get("claim_id")
                             if isinstance(claim_observation, dict) else None),
                "device_id": (claim_observation.get("device_id")
                              if isinstance(claim_observation, dict) else
                              lease.get("device_id") if isinstance(lease, dict) else None),
                "detail": (f"MI210 {(claim_observation or {}).get('device_id', 'device')} source-proof claim is held"
                           if source_claim_held else
                           f"MI210 {lease.get('device_id', 'device')} admission-probe claim is held"
                           if probe_claim_held else
                           f"MI210 {(claim_observation or {}).get('device_id', 'device')} source-proof claim released"
                           if isinstance(claim_observation, dict)
                           and claim_observation.get("claim_released") is True else
                           (f"GPU correctness ran for "
                            f"{execution_observation['elapsed_s']:.1f}s; "
                            f"{execution_observation['summary']}; claim released")
                           if historical_gpu_screen else
                           "GPU screening was not reached"
                           if stage == "planner_validation" and status == "failed" else
                           "admission probe was released; no GPU screening began"
                           if probe_released else
                           "no identity-bound GPU claim is evidenced")},
        "stage_contract": {
            "current_stage": stage,
            "first_incomplete_stage": first_incomplete,
            "resume_policy": ("execute_once_from_first_incomplete"
                              if recoverability == "resume_first_incomplete_stage"
                              else recoverability),
            "repetition": repetition,
            "replication": (f"S{repetition}" if isinstance(repetition, int)
                            else None),
            "arm_order": arm_order,
            "arm_order_seed_sha256": (
                postbuild_observation.get("arm_order_seed_sha256")
                if isinstance(postbuild_observation, dict) else None),
            "exact_attribution_direction": (
                postbuild_observation.get("exact_direction")
                if isinstance(postbuild_observation, dict) else
                "improved" if isinstance(iteration_exact_effect, (int, float))
                and not isinstance(iteration_exact_effect, bool)
                and iteration_exact_effect > 0 else
                "regressed" if isinstance(iteration_exact_effect, (int, float))
                and not isinstance(iteration_exact_effect, bool)
                and iteration_exact_effect < 0 else
                "neutral" if iteration_exact_effect == 0 else None),
            "exact_attribution_effect_fraction": (
                postbuild_observation.get("exact_attribution_effect_fraction")
                if isinstance(postbuild_observation, dict)
                and postbuild_observation.get(
                    "exact_attribution_effect_fraction") is not None
                else iteration_exact_effect),
            "target_runtime_effect_fraction": (
                postbuild_observation.get("target_runtime_effect_fraction")
                if isinstance(postbuild_observation, dict)
                and postbuild_observation.get("target_runtime_effect_fraction") is not None
                else iteration_target_effect),
            "target_runtime_executed": (
                postbuild_observation.get("target_runtime_executed")
                if isinstance(postbuild_observation, dict)
                and postbuild_observation.get("target_runtime_executed") is not None
                else iteration_target_executed),
            "target_runtime_reason": (
                postbuild_observation.get("target_runtime_reason")
                if isinstance(postbuild_observation, dict) else
                latest_iteration.get("target_runtime_reason")
                if isinstance(latest_iteration, dict) else None),
            "dual_decision_state": (
                postbuild_observation.get("dual_decision_state")
                if isinstance(postbuild_observation, dict) else
                "measured_nonpositive_exact_short_circuit"
                if isinstance(iteration_exact_effect, (int, float))
                and not isinstance(iteration_exact_effect, bool)
                and iteration_exact_effect <= 0
                and iteration_target_executed is False else
                "exact_and_graphs_on_complete"
                if isinstance(iteration_exact_effect, (int, float))
                and not isinstance(iteration_exact_effect, bool)
                and isinstance(iteration_target_effect, (int, float))
                and not isinstance(iteration_target_effect, bool) else None),
            "measurement_process_progress": (
                {key: postbuild_observation["process_progress"].get(key)
                 for key in ("stage", "runtime_graphs", "completed_arms",
                             "next_arm", "checkpoint_reuse")}
                if isinstance(postbuild_observation, dict)
                and isinstance(postbuild_observation.get("process_progress"), dict)
                else None),
        },
        "refusal": {
            "detected": refusal_type is not None,
            "type": refusal_type,
            "class": (headline_refusal_observation.get("type")
                      if isinstance(headline_refusal_observation, dict) else None),
            "stage": (headline_refusal_observation.get("stage")
                      if isinstance(headline_refusal_observation, dict) else
                      "planner_validation" if planner_refusal_detected
                      else None),
            "scientific_budget_spent": (
                headline_refusal_observation.get("scientific_budget_spent")
                if isinstance(headline_refusal_observation, dict) else
                False if planner_refusal_detected else None),
            "receipt_sha256": (
                headline_refusal_observation.get("receipt_sha256")
                if isinstance(headline_refusal_observation, dict) else None),
            "detail": (None if historical_refusal_only else
                       headline_refusal_observation.get("detail")
                       if isinstance(headline_refusal_observation, dict) else
                       (f"reason sha256 {refusal_result['refusal_reason_sha256'][:12]}…"
                        if planner_refusal_detected
                        and isinstance(refusal_result.get(
                            "refusal_reason_sha256"), str) else
                        latest_iteration.get("reason")
                        if isinstance(latest_iteration, dict)
                        and not planner_refusal_detected
                        and latest_iteration.get("status") !=
                        "measurement_output_refused" else None)),
            "measurement_output": (
                measurement_output_view),
        },
        "provider_retry": {
            "detected": recoverability in {
                "resume_planner_provider_retry",
                "resume_critic_provider_retry"},
            "actor": ("planner" if recoverability == "resume_planner_provider_retry"
                      else "critic" if recoverability == "resume_critic_provider_retry"
                      else None),
            "same_hypothesis": recoverability == "resume_planner_provider_retry",
            "planner_rerun": False if recoverability == "resume_critic_provider_retry"
                            else None,
            "provider_attempt": (
                planning.get("provider_attempt")
                if recoverability == "resume_planner_provider_retry"
                and isinstance(planning, dict)
                and isinstance(planning.get("provider_attempt"), int)
                and not isinstance(planning.get("provider_attempt"), bool) else
                state.get("planner_provider_attempt")
                if recoverability == "resume_planner_provider_retry"
                and isinstance(state, dict)
                and isinstance(state.get("planner_provider_attempt"), int)
                and not isinstance(state.get("planner_provider_attempt"), bool)
                else None),
            "detail": (latest_iteration.get("reason")
                       if recoverability == "resume_planner_provider_retry"
                       and isinstance(latest_iteration, dict) else
                       "critic_pending is durable; only critic review retries"
                       if recoverability == "resume_critic_provider_retry" else None),
        },
        "correctness": ({
            "execution_started": True,
            "execution_completed": True,
            "validation_passed": (
                False if stage == "correctness_validation" and status == "failed"
                else True if isinstance(receipt_correctness_observation, dict)
                else None),
            "started_at": execution_observation["started_at"],
            "completed_at": execution_observation["completed_at"],
            "elapsed_s": execution_observation["elapsed_s"],
            "passed": execution_observation["passed"],
            "total": execution_observation["total"],
            "summary": execution_observation["summary"],
        } if historical_gpu_screen else {
            "execution_started": True,
            "execution_completed": False,
            "validation_passed": None,
            "started_at": claim_at,
            "completed_at": None,
            "elapsed_s": elapsed_s,
        } if active_correctness_started else {
            "execution_started": False, "execution_completed": False,
            "validation_passed": None,
        }),
        "checkpoint": {"available": checkpoint is not None,
                       "kind": "STOP_STATE" if checkpoint else None,
                       "state": checkpoint.get("state") if checkpoint else None,
                       "seq": checkpoint.get("seq") if checkpoint else None,
                       "at": checkpoint_at,
                       "detail": ("durable but not automatically resumable"
                                  if checkpoint and recoverability.startswith("ambiguous")
                                  else "latest durable controller boundary" if checkpoint
                                  else "no durable controller checkpoint")},
        "resume": {"required": status in {"failed", "stopped"},
                   "possible": (not terminal_checkpointed
                   and recoverability in {
                       "same_candidate_retry", "not_required",
                       "resume_first_incomplete_stage",
                       "resume_postbuild_resource_wait",
                       "resume_controller_checkpoint",
                       "resume_planner_provider_retry",
                       "resume_critic_provider_retry"}),
                   "recoverability": ("ambiguous" if recoverability.startswith("ambiguous")
                                      else recoverability),
                   "disposition": recoverability,
                   "detail": ("Cannot resume this ambiguous inflight operation"
                              if recoverability.startswith("ambiguous")
                              else "Cannot resume; repair the controller and launch a fresh sealed deployment"
                              if recoverability == "planner_validation_requires_fresh_deployment"
                              else f"Resume at {first_incomplete}; completed stage receipts are revalidated and reused"
                              if recoverability == "resume_first_incomplete_stage"
                              else "Restart or continue the controller after the foreign GPU owner releases; the exact completed builds and evidence policy are revalidated and reused"
                              if recoverability == "resume_postbuild_resource_wait"
                              else "Restart the controller; the screened decision is durable and the next hypothesis is selected automatically"
                              if recoverability == "resume_controller_checkpoint"
                              else "Restart the controller; retry the same hypothesis from its durable planner checkpoint"
                              if recoverability == "resume_planner_provider_retry"
                              else "Restart the controller; retry only the critic from critic_pending without rerunning the planner"
                              if recoverability == "resume_critic_provider_retry"
                              else "same candidate may be retried" if recoverability == "same_candidate_retry"
                              else "no resume action is required")},
        "failure": failure_view,
        # This is controller-journal history, deliberately separate from both
        # physical telemetry streams and from the current-turn refusal/failure
        # headline.  The UI may show it in the always-visible pulse without
        # claiming that an actor emitted a telemetry event.
        "prior_terminal": prior_terminal,
        "preauthored": ({
            **v26_state["provenance"],
            "checkpointed": bool(
                isinstance(checkpoint, dict) and checkpoint.get("state") ==
                "discovery_preauthored_checkpointed"),
            "structural_tail": v26_contract.get("structural_tail")
            if isinstance(v26_contract, dict) else None,
        } if isinstance(v26_state, dict)
             and isinstance(v26_state.get("provenance"), dict) else None),
        "pipeline": list(pipeline.values()),
        "transitions": transitions[-100:],
        "completed_iterations": len(iterations),
        "scientific_attempts": (
            v26_state.get("scientific_attempts")
            if isinstance(v26_state, dict) else None),
        **({"scientific_budget": v26_state["scientific_budget"]}
           if isinstance(v26_state, dict)
           and "scientific_budget" in v26_state else {}),
        **({"performance": v26_state["performance"]}
           if isinstance(v26_state, dict)
           and isinstance(v26_state.get("performance"), dict) else {}),
        "history": {"abandoned_count": len(abandoned),
                    "retest_count": len(retest),
                    **({"annulled_count": len(annulled_history)}
                       if isinstance(v26_state, dict)
                       and "annulled_history" in v26_state else {}),
                    "terminal_count": len(prior_terminals),
                    "summary": (f"{len(abandoned)} abandoned · {len(retest)} retest"
                                + (f" · {len(annulled_history)} annulled"
                                   if annulled_history else "")
                                + (f" · {len(prior_terminals)} prior terminal"
                                   f"{'s' if len(prior_terminals) != 1 else ''}"
                                   if prior_terminals else "")),
                    "rows": history_rows,
                    "terminal_rows": prior_terminals},
    }


def _experimental_runtime_descriptor(config: dict, bundle: Path) -> dict | None:
    """Validate the dashboard-facing identity of one runtime sibling."""
    value = config.get("experimental_runtime")
    if (not isinstance(config.get("config_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", config["config_sha256"]) is None
            or not isinstance(value, dict) or set(value) != {
            "schema", "candidate_id", "runtime_root", "stage_order",
            "stage_budgets_s"}
            or value.get("schema") != _EXPERIMENTAL_RUNTIME_SCHEMA
            or not isinstance(value.get("candidate_id"), str)
            or re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,127}",
                            value["candidate_id"]) is None
            or value.get("stage_order") != list(_EXPERIMENTAL_RUNTIME_STAGES)):
        return None
    runtime_root = _safe_bundle_path(value.get("runtime_root"), bundle)
    budgets = value.get("stage_budgets_s")
    if (runtime_root is None or not isinstance(budgets, dict)
            or set(budgets) != set(_EXPERIMENTAL_RUNTIME_STAGES)
            or any(isinstance(budget, bool) or not isinstance(budget, int)
                   or budget < 60 or budget > 86400
                   for budget in budgets.values())):
        return None
    try:
        if runtime_root.exists() and (
                runtime_root.is_symlink() or not runtime_root.is_dir()):
            return None
    except OSError:
        return None
    return {
        "candidate_id": value["candidate_id"],
        "runtime_root": runtime_root,
        "stage_budgets_s": dict(budgets),
    }


def _experimental_runtime_result(stage: str, value: object) -> dict | None:
    """Project one stage's compact, secret-free headline result."""
    if not isinstance(value, dict):
        return None
    finite_number = lambda item: (
        isinstance(item, (int, float)) and not isinstance(item, bool)
        and math.isfinite(float(item)))
    if stage == "experimental_build":
        if (set(value) != {"hip_binary_sha256", "cpu_binary_sha256",
                           "dflash2_gguf_sha256", "mmq_path_check"}
                or value.get("mmq_path_check") != "pass"
                or any(re.fullmatch(r"[0-9a-f]{64}", str(value.get(key))) is None
                       for key in ("hip_binary_sha256", "cpu_binary_sha256",
                                   "dflash2_gguf_sha256"))):
            return None
    elif stage == "cpu_gpu_regression":
        if (set(value) != {"cpu_pass", "gpu_pass"}
                or value.get("cpu_pass") is not True
                or value.get("gpu_pass") is not True):
            return None
    elif stage == "matched_np1":
        if (set(value) != {"plain_decode_tps", "mtp_decode_tps",
                           "dflash2_decode_tps", "dflash2_acceptance",
                           "comparator_tps"}
                or any(not finite_number(value.get(key))
                       or float(value[key]) <= 0 for key in (
                           "plain_decode_tps", "mtp_decode_tps",
                           "dflash2_decode_tps", "comparator_tps"))
                or not finite_number(value.get("dflash2_acceptance"))
                or not 0 <= float(value["dflash2_acceptance"]) <= 1
                or float(value["comparator_tps"]) != 55.46):
            return None
    elif stage == "concurrency_grid":
        if (set(value) != {"np_values", "mtp_np8_tps", "dflash2_np8_tps"}
                or value.get("np_values") != [2, 4, 8]
                or any(not finite_number(value.get(key))
                       or float(value[key]) <= 0
                       for key in ("mtp_np8_tps", "dflash2_np8_tps"))):
            return None
    elif stage == "greedy_parity":
        if (set(value) != {"exact_token_parity", "compared_tokens"}
                or not isinstance(value.get("exact_token_parity"), bool)
                or isinstance(value.get("compared_tokens"), bool)
                or not isinstance(value.get("compared_tokens"), int)
                or value["compared_tokens"] < 1):
            return None
    elif stage == "decision":
        if (set(value) != {"decision", "reason_code"}
                or value.get("decision") not in {
                    "runtime_candidate_selected", "runtime_candidate_rejected"}
                or not isinstance(value.get("reason_code"), str)
                or re.fullmatch(r"[a-z0-9_]{1,100}",
                                value["reason_code"]) is None):
            return None
    else:
        return None
    return dict(value)


def _experimental_runtime_receipts(
        descriptor: dict, campaign_id: str | None) -> dict:
    """Validate the ordered stage chain and derive its first missing receipt."""
    runtime_root = descriptor["runtime_root"]
    candidate_id = descriptor["candidate_id"]
    receipts: dict[str, dict] = {}
    predecessor_file_sha256 = None
    invalid_stage = None
    for stage in _EXPERIMENTAL_RUNTIME_STAGES:
        path = runtime_root / "stages" / stage / "receipt.json"
        if not path.exists() and not path.is_symlink():
            break
        captured = _discovery_private_file(
            path, operation_root=runtime_root, maximum=4 * 1024 * 1024)
        if captured is None:
            invalid_stage = stage
            break
        raw, info = captured
        try:
            body = json.loads(raw.decode("utf-8", "strict"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid_stage = stage
            break
        if not isinstance(body, dict) or set(body) != {
                "schema", "campaign_kind", "campaign_id", "candidate_id",
                "stage", "status", "started_at", "ended_at",
                "predecessor_receipt_file_sha256", "evidence_sha256", "result",
                "receipt_sha256"}:
            invalid_stage = stage
            break
        started_at = body.get("started_at")
        ended_at = body.get("ended_at")
        result = _experimental_runtime_result(stage, body.get("result"))
        unsigned = {key: value for key, value in body.items()
                    if key != "receipt_sha256"}
        if (body.get("schema") != _EXPERIMENTAL_RUNTIME_RECEIPT_SCHEMA
                or body.get("campaign_kind") != "experimental_runtime"
                or body.get("campaign_id") != campaign_id
                or body.get("candidate_id") != candidate_id
                or body.get("stage") != stage
                or body.get("status") != "complete"
                or body.get("predecessor_receipt_file_sha256") !=
                predecessor_file_sha256
                or re.fullmatch(r"[0-9a-f]{64}", str(
                    body.get("evidence_sha256"))) is None
                or body.get("receipt_sha256") !=
                _discovery_content_hash(unsigned)
                or not isinstance(started_at, str)
                or not isinstance(ended_at, str)
                or _parse_semantic_timestamp(started_at) is None
                or _parse_semantic_timestamp(ended_at) is None
                or _parse_semantic_timestamp(ended_at) <
                _parse_semantic_timestamp(started_at)
                or result is None):
            invalid_stage = stage
            break
        file_sha256 = hashlib.sha256(raw).hexdigest()
        receipts[stage] = {
            "path": str(path), "file_sha256": file_sha256,
            "started_at": started_at, "ended_at": ended_at,
            "result": result,
            "at": datetime.fromtimestamp(
                info.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        predecessor_file_sha256 = file_sha256
    first_incomplete = next(
        (stage for stage in _EXPERIMENTAL_RUNTIME_STAGES
         if stage not in receipts), None)
    return {
        "receipts": receipts, "first_incomplete_stage": first_incomplete,
        "invalid_stage": invalid_stage,
    }


def _experimental_runtime_activity(
        *, lock_held: bool, campaign_id: str | None, state: dict | None,
        events: list[dict], descriptor: dict,
        claim_observation: dict | None, now: float) -> dict:
    """Render the isolated six-stage runtime sibling from durable receipts."""
    observation = _experimental_runtime_receipts(descriptor, campaign_id)
    receipts = observation["receipts"]
    first_incomplete = observation["first_incomplete_stage"]
    invalid_stage = observation["invalid_stage"]
    pipeline = {
        stage: {"id": stage, "label": label, "state": "not_reached"}
        for stage, label in _EXPERIMENTAL_RUNTIME_PIPELINE}
    transitions = []
    for stage, receipt in receipts.items():
        pipeline[stage].update({
            "state": "complete", "started_at": receipt["started_at"],
            "completed_at": receipt["ended_at"],
            "elapsed_s": max(0.0, _parse_semantic_timestamp(
                receipt["ended_at"]) - _parse_semantic_timestamp(
                    receipt["started_at"])),
            "detail": f"receipt {receipt['file_sha256'][:12]}…",
        })
        transitions.append({
            "ts": receipt["ended_at"], "stage": stage, "phase": stage,
            "state": "complete", "event": f"{stage}_completed",
            "label": _EXPERIMENTAL_RUNTIME_PIPELINE_DICT[stage],
            "detail": f"receipt {receipt['file_sha256'][:12]}…",
        })
    runtime_state = (state.get("experimental_runtime")
                     if isinstance(state, dict) else None)
    state_candidate = (runtime_state.get("candidate_id")
                       if isinstance(runtime_state, dict) else None)
    active_stage = (runtime_state.get("active_stage")
                    if isinstance(runtime_state, dict) else None)
    active_step = (runtime_state.get("active_step")
                   if isinstance(runtime_state, dict) else None)
    state_started_at = (runtime_state.get("stage_started_at")
                        if isinstance(runtime_state, dict) else None)
    state_identity_valid = bool(
        isinstance(runtime_state, dict)
        and state_candidate == descriptor["candidate_id"]
        and (active_stage is None or active_stage in _EXPERIMENTAL_RUNTIME_STAGES)
        and active_step in {None, "none", "cpu", "gpu"}
        and (state_started_at is None
             or isinstance(state_started_at, str)
             and _parse_semantic_timestamp(state_started_at) is not None))
    failure = {"detected": False, "stage": None, "detail": None,
               "recovery": None}
    if first_incomplete is None:
        stage = "decision"
        status = "complete"
        label = "Runtime candidate decision complete"
        waiting_on = "no further runtime stage"
        resume_policy = "not_required"
    elif invalid_stage is not None:
        stage = invalid_stage
        status = "failed"
        label = f"{_EXPERIMENTAL_RUNTIME_PIPELINE_DICT[stage]} receipt refused"
        waiting_on = "repair the invalid stage receipt"
        resume_policy = "receipt_repair_required"
        pipeline[stage]["state"] = "failed"
        failure = {
            "detected": True, "stage": stage,
            "detail": f"invalid or identity-drifted {stage} receipt",
            "recovery": "Repair the exact receipt; later stages remain untrusted.",
        }
    elif (isinstance(runtime_state, dict) and not state_identity_valid):
        stage = first_incomplete
        status = "failed"
        label = "Experimental runtime state identity refused"
        waiting_on = "repair the runtime state identity"
        resume_policy = "state_identity_repair_required"
        pipeline[stage]["state"] = "failed"
        failure = {
            "detected": True, "stage": stage,
            "detail": "runtime state candidate/stage/substep identity is invalid",
            "recovery": "Do not infer progress from this state; receipts remain authoritative.",
        }
    elif lock_held and active_stage not in {None, first_incomplete}:
        stage = first_incomplete
        status = "failed"
        label = "Experimental runtime stage order drift"
        waiting_on = f"resume only from {first_incomplete}"
        resume_policy = "state_identity_repair_required"
        pipeline[stage]["state"] = "failed"
        failure = {
            "detected": True, "stage": stage,
            "detail": (f"state claims {active_stage}; first incomplete receipt "
                       f"is {first_incomplete}"),
            "recovery": "Reconcile state to the first incomplete durable stage.",
        }
    else:
        stage = first_incomplete
        status = "running" if lock_held else "stopped"
        label = _EXPERIMENTAL_RUNTIME_PIPELINE_DICT[stage]
        waiting_on = (f"{label} completion" if lock_held else
                      f"restart from first incomplete stage: {stage}")
        resume_policy = "execute_once_from_first_incomplete"
        pipeline[stage]["state"] = "running" if lock_held else "waiting"
        if state_started_at is not None and active_stage == stage:
            pipeline[stage]["started_at"] = state_started_at
        if lock_held and active_stage == stage:
            transitions.append({
                "ts": state_started_at or state.get("updated_at"),
                "stage": stage, "phase": stage, "state": "running",
                "event": f"{stage}_active",
                "label": label,
                "detail": f"active substep: {active_step or 'unspecified'}",
            })
    receipt_times = [receipt["ended_at"] for receipt in receipts.values()]
    event_times = [row.get("ts") for row in events
                   if isinstance(row.get("ts"), str)]
    state_at = state.get("updated_at") if isinstance(state, dict) else None
    progress_times = [value for value in (*receipt_times, *event_times, state_at)
                      if isinstance(value, str)
                      and _parse_semantic_timestamp(value) is not None]
    last_progress_at = max(progress_times) if progress_times else None
    last_progress_epoch = (_parse_semantic_timestamp(last_progress_at)
                           if last_progress_at else None)
    progress_age = (max(0.0, now - last_progress_epoch)
                    if last_progress_epoch is not None else None)
    stage_started_at = pipeline[stage].get("started_at")
    if stage_started_at is None:
        stage_started_at = (state_started_at if active_stage == stage else
                            receipts[next(reversed(receipts))]["ended_at"]
                            if receipts else state_at)
    stage_start_epoch = (_parse_semantic_timestamp(stage_started_at)
                         if isinstance(stage_started_at, str) else None)
    if status == "complete":
        elapsed_s = pipeline[stage].get("elapsed_s")
    elif (status in {"stopped", "failed"} and stage_start_epoch is not None
          and last_progress_epoch is not None):
        elapsed_s = max(0.0, last_progress_epoch - stage_start_epoch)
    else:
        elapsed_s = (max(0.0, now - stage_start_epoch)
                     if stage_start_epoch is not None else None)
    threshold = descriptor["stage_budgets_s"].get(stage, _DISCOVERY_STALL_S)
    if (lock_held and status == "running" and progress_age is not None
            and progress_age > threshold):
        status = "stalled"
        stall = {"state": "stalled", "threshold_s": threshold,
                 "detail": "No durable runtime transition advanced within the sealed stage budget."}
    elif status == "failed":
        stall = {"state": "failed", "threshold_s": threshold,
                 "detail": failure["detail"]}
    else:
        stall = {"state": "healthy", "threshold_s": threshold,
                 "detail": ("durable runtime lifecycle is advancing" if lock_held
                            else "controller is not active")}
    claim_held = bool(
        isinstance(claim_observation, dict)
        and claim_observation.get("claim_held") is True
        and claim_observation.get("identity_live") is True)
    gpu_stage = stage in {"matched_np1", "concurrency_grid", "greedy_parity"}
    if stage == "cpu_gpu_regression":
        gpu_stage = active_step == "gpu"
    gpu_expected = bool(status in {"running", "stalled"} and gpu_stage)
    results = {stage_name: receipt["result"]
               for stage_name, receipt in receipts.items()}
    decision = results.get("decision", {}).get("decision")
    return {
        "campaign_kind": "experimental_runtime",
        "status": status,
        "phase": {"id": stage, "label": label,
                  "started_at": stage_started_at, "elapsed_s": elapsed_s},
        "turn": state.get("next") if isinstance(state, dict) else None,
        "hypothesis_id": None,
        "last_progress_at": last_progress_at,
        "progress_age_s": progress_age,
        "waiting_on": waiting_on,
        "stall": stall,
        "gpu": {
            "expected_now": gpu_expected, "claim_held": claim_held,
            "claim_released": bool(isinstance(claim_observation, dict)
                                   and claim_observation.get(
                                       "claim_released") is True),
            "claim_id": (claim_observation.get("claim_id")
                         if isinstance(claim_observation, dict) else None),
            "device_id": (claim_observation.get("device_id")
                          if isinstance(claim_observation, dict) else None),
            "screen_started": bool(receipts or claim_observation),
            "detail": ("MI210 experimental-runtime claim is held" if claim_held
                       else "GPU is expected for the active runtime substep"
                       if gpu_expected else
                       "GPU is not expected for the active runtime substep"),
        },
        "stage_contract": {
            "campaign_kind": "experimental_runtime",
            "current_stage": stage,
            "first_incomplete_stage": first_incomplete,
            "resume_policy": resume_policy,
            "repetition": None, "replication": None,
            "arm_order": None, "arm_order_seed_sha256": None,
            "exact_attribution_direction": None,
            "exact_attribution_effect_fraction": None,
            "target_runtime_effect_fraction": None,
            "target_runtime_executed": None,
            "target_runtime_reason": None,
            "dual_decision_state": None,
            "measurement_process_progress": None,
        },
        "runtime_campaign": {
            "candidate_id": descriptor["candidate_id"],
            "excluded_from_kernel_frontier": True,
            "active_step": active_step,
            "completed_stages": list(receipts),
            "matched_np1": results.get("matched_np1"),
            "concurrency_grid": results.get("concurrency_grid"),
            "greedy_parity": results.get("greedy_parity"),
            "decision": decision,
        },
        "correctness": {
            "execution_started": "cpu_gpu_regression" in receipts,
            "execution_completed": "cpu_gpu_regression" in receipts,
            "validation_passed": bool(
                results.get("cpu_gpu_regression", {}).get("cpu_pass") is True
                and results.get("cpu_gpu_regression", {}).get("gpu_pass") is True),
            "summary": ("CPU + GPU regression passed"
                        if "cpu_gpu_regression" in receipts else None),
            "started_at": None, "completed_at": None, "elapsed_s": None,
        },
        "checkpoint": {"available": bool(receipts),
                       "state": "runtime_stage_receipts" if receipts else None,
                       "detail": f"{len(receipts)} / 6 stages complete"},
        "resume": {
            "required": bool(not lock_held and first_incomplete is not None),
            "possible": invalid_stage is None and not failure["detected"],
            "disposition": resume_policy,
            "detail": (f"Restart at {first_incomplete}; completed receipts are reused"
                       if not lock_held and first_incomplete is not None else
                       "No resume action is required"),
        },
        "failure": failure,
        "refusal": {"detected": False, "type": None, "class": None,
                    "stage": None, "scientific_budget_spent": None,
                    "receipt_sha256": None, "detail": None,
                    "measurement_output": None},
        "provider_retry": {"detected": False, "actor": None,
                           "same_hypothesis": None, "planner_rerun": None,
                           "provider_attempt": None, "detail": None},
        "pipeline": list(pipeline.values()),
        "transitions": sorted(transitions, key=lambda row: str(row.get("ts")))[-100:],
        "completed_iterations": 1 if decision is not None else 0,
        "history": {"abandoned_count": 0, "retest_count": 0,
                    "summary": "experimental runtime sibling · no source history",
                    "rows": []},
    }


_SUPERVISOR_LEDGER_SCHEMA = "epyc.autokernel.discovery_supervisor_ledger.v2"
_SUPERVISOR_IDENTITY_SCHEMA = "epyc.autokernel.discovery_supervisor_identity.v2"
_SUPERVISOR_SPEC_SCHEMA = "epyc.autokernel.discovery_supervisor_spec.v2"
_SUPERVISOR_SPEC_SCHEMA_V3 = "epyc.autokernel.discovery_supervisor_spec.v3"
_SUPERVISOR_SPEC_SCHEMA_V4 = "epyc.autokernel.discovery_supervisor_spec.v4"
_SUPERVISOR_GRAPH_EXECUTION_MODULES_V3 = {
    "deployment_factory":
        "scripts/kernel_rnd/autokernel/controller/discovery_deployment_factory.py",
    "discovery_controller":
        "scripts/kernel_rnd/autokernel/controller/discovery_controller.py",
    "hypotheses": "scripts/kernel_rnd/autokernel/controller/hypotheses.py",
    "do_not_repeat": "scripts/kernel_rnd/autokernel/controller/do_not_repeat.py",
    "discovery_telemetry":
        "scripts/kernel_rnd/autokernel/controller/discovery_telemetry.py",
    "gpu_discovery_runner": "scripts/benchmark/run_autokernel_gpu_discovery.py",
    "gpu_source_adapter":
        "scripts/kernel_rnd/autokernel/controller/gpu_source_adapter.py",
    "discovery_static_registry":
        "scripts/kernel_rnd/autokernel/controller/discovery_static_registry.py",
    "discovery_supervisor":
        "scripts/kernel_rnd/autokernel/controller/discovery_supervisor.py",
    "discovery_supervisor_secure":
        "scripts/kernel_rnd/autokernel/controller/discovery_supervisor_secure.py",
    "discovery_deployment":
        "scripts/kernel_rnd/autokernel/controller/discovery_deployment.py",
    "gpu_load_admission":
        "scripts/kernel_rnd/autokernel/controller/gpu_load_admission.py",
    "split_runtime_verifier":
        "scripts/kernel_rnd/autokernel/controller/split_runtime_verifier.py",
    "inference_window":
        "scripts/kernel_rnd/autokernel/execution/inference_window.py",
    "cpu_region_claim":
        "scripts/kernel_rnd/autokernel/execution/cpu_region_claim.py",
    "worktree": "scripts/kernel_rnd/autokernel/execution/worktree.py",
    "source_candidate": "scripts/kernel_rnd/autokernel/source_candidate.py",
    "instrument_integrity":
        "scripts/kernel_rnd/autokernel/execution/instrument_integrity.py",
    "t0_provider": "scripts/kernel_rnd/autokernel/execution/t0_provider.py",
    "evaluator_integrity": "scripts/kernel_rnd/autokernel/evaluator/integrity.py",
    "gpu_source_evidence":
        "scripts/kernel_rnd/autokernel/controller/gpu_source_evidence.py",
    "gpu_source_proofs":
        "scripts/kernel_rnd/autokernel/controller/gpu_source_proofs.py",
    "gpu_discovery_beliefs":
        "scripts/benchmark/autokernel_gpu_discovery_beliefs.py",
    "device_claim": "scripts/kernel_rnd/autokernel/resource/device_claim.py",
    "device_sampler":
        "scripts/kernel_rnd/autokernel/execution/device_sampler.py",
    "gpu_residency_sampler":
        "scripts/kernel_rnd/autokernel/controller/gpu_residency_sampler.py",
    "codex_container_actor":
        "scripts/kernel_rnd/autokernel/controller/codex_container_actor.py",
    "claude_fable5_critic_actor":
        "scripts/kernel_rnd/autokernel/controller/claude_fable5_critic_actor.py",
    "hypothesis_portfolio":
        "scripts/kernel_rnd/autokernel/hypothesis_portfolio.py",
}
_SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26 = {
    **_SUPERVISOR_GRAPH_EXECUTION_MODULES_V3,
    "preauthored_continuation":
        "scripts/kernel_rnd/autokernel/preauthored_continuation.py",
}
_DISCOVERY_V26_EXECUTION_MODULE_SHA256 = {
    "claude_fable5_critic_actor":
        "fb7f728e829b105a37bbde3d28c31711c0ffee370ec1560efcbc6e92eeccfd5d",
    "codex_container_actor":
        "0a1f4c4a64d36bde8944b2c2c41c052e59d15cb3b676df101f30ec5a0efc3c13",
    "cpu_region_claim":
        "cb8b474955313f7bd2855c6f59f26b53a481d74812372f4c3b38f9783efe5f19",
    "deployment_factory":
        "32ddb368140eff26ed67f97881565150a37c437587d74c406a20b4cb4dd7ef7e",
    "device_claim":
        "ed079e49946a869399b905e2149f6b0a3c76c1c19d1acbb1bfd39766e4d861d7",
    "device_sampler":
        "13f86ed2854d095241b609290e21318e426bd2a3e6b21ea56fb8a74e21c768f0",
    "discovery_controller":
        "3e0674094e4b3090f0b187cf4a38ec942504caa1fc908fe48ac88b4905f4d22f",
    "discovery_deployment":
        "4c34bf27d22af081ce7db4eade6ce21f1f94eb87f2e2bc61403121383dd136fd",
    "discovery_static_registry":
        "8a79d1b767be670d6fca673f3a1954ba5fd0bbe03936113bec8e60c76bbceae9",
    "discovery_supervisor":
        "357ecbaba964a70665e90635088303fdda20e9f407a962d124679a3751e888c4",
    "discovery_supervisor_secure":
        "7b7ba4b5c1c25e8b98210b5ac31e773832e41661019c89cdbef87e4c601bea4d",
    "discovery_telemetry":
        "9beba2a1c92c8b0326523b367148868fabfcf3076170a8188e31ecddfdd25841",
    "do_not_repeat":
        "66c32876760b2f61c1064e0e6767c3ce3b5c22ae4878ee558439e188e7e6aec3",
    "evaluator_integrity":
        "dfc6dbc719aab525d4ddedd53ca087b00e1e632ed8147967175676884f415f1f",
    "gpu_discovery_beliefs":
        "da90a530ce8617ff1cde1be95fc2925fa6bfc270d5e4ffa8d57cf001c1fb6a2b",
    "gpu_discovery_runner":
        "0fb0ed3e0bf3b06752ac6a5b1b726ae349b5937d99f9586550925d249af33639",
    "gpu_load_admission":
        "f9d3f6331d985c8e496a4dc0de9b01d51de2a0606467acfe412b496f2378d15a",
    "gpu_residency_sampler":
        "8eff7f6e54089725572965a56f827defa2150becb337fe55cc81d7494c5d9722",
    "gpu_source_adapter":
        "382e3f16cfa9b0543312859199298ecbab4abcde2ce8dc26ad33dea9c890527e",
    "gpu_source_evidence":
        "3595af023124e1706bcaea6e4379bbb4399dbf181d69f2ac369b13d778f87a01",
    "gpu_source_proofs":
        "46ccc107caba8a371eb6d7f25f45ed6a126cf63ce76b5fb6f6e168bde0725c76",
    "hypotheses":
        "425c1dc97ba9d2f4085cb49f6433badc007f7af14efcc7a30a2d43ae98fedf75",
    "hypothesis_portfolio":
        "bdd6e5d6e2c14e52e11a036ef020c9c999863777e60367616fb759a156a256df",
    "inference_window":
        "67aaee97d981970224af097283478e98d8520b1109bae07f3beaa5fa6d957f5d",
    "instrument_integrity":
        "bbc1013e988cdbfb86b6adf7b7267cc1e8cccefc71769fd6d3ea0033e2872bee",
    "preauthored_continuation":
        "90c735981f686693e0ec0d7359475a40237e75134a6804ebf3bc71ff2cbe3311",
    "source_candidate":
        "d38a7d38c2db0e48a512dc27a690a66cde76d53dbc0e2b66d0e4d5b98d8e99c8",
    "split_runtime_verifier":
        "ee6450ee111987a315262bbacdf0d43bb0259a1d1ead7a271b9c234db8b3abe0",
    "t0_provider":
        "b91b7a15440c2031a7b567e59a8078be8b213cc78b8f5f9f37d453701c57d897",
    "worktree":
        "153118cb9811eb97bb1320e237e9d6908c7c888171379c16a72b72ea09d76215",
}
_DISCOVERY_V26_PRODUCER_COMMIT = \
    "915f4ce5d38713b59545035d17e4a730214b5db1"
_DISCOVERY_V26_DEPLOYMENT_SEMANTIC_SHA256 = \
    "03fc1b1230487a35f8aefd843a546da9324361ee462d945bc076ef89263d2b89"
_DISCOVERY_V26_DEPLOYMENT_FILE_SHA256 = \
    "53a5f35f42baba05bc0a3c72741737f7d30583d8a3435078ee9edae59661bb5f"
_DISCOVERY_V26_GRAPH_SHA256 = \
    "20dec69b26c84dbdf7f97b92e39349437df9c28a10300fed210752070e0a2e4c"
_DISCOVERY_V26_GRAPH_FILE_SHA256 = \
    "ef35a550a96bdc8b9cd089097c216078a1b5b8fa842df746d975592fd6ad6075"
# The v27 consumer understands the successor schemas, but a generated bundle
# must not become live until the combined producer and exact final-root files
# have completed their independent freeze/audit.  Tests patch all six pins as
# one authority; production deliberately remains fail closed meanwhile.
_DISCOVERY_V27_EXECUTION_MODULE_SHA256 = None
_DISCOVERY_V27_PRODUCER_COMMIT = None
_DISCOVERY_V27_DEPLOYMENT_SEMANTIC_SHA256 = None
_DISCOVERY_V27_DEPLOYMENT_FILE_SHA256 = None
_DISCOVERY_V27_GRAPH_SHA256 = None
_DISCOVERY_V27_GRAPH_FILE_SHA256 = None
_SUPERVISOR_GRAPH_MISMATCH = (
    b"DeploymentFactoryError: durable deployment graph differs from current sealed graph")


def _strict_json_bytes(raw: bytes) -> dict | None:
    """Decode one bounded JSON object while refusing duplicate object keys."""
    def pairs(values: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(_value: str) -> object:
        raise ValueError("non-finite JSON number")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")


def _stat_identity(info: os.stat_result, *, sized: bool) -> dict:
    value = {
        "dev": info.st_dev, "ino": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode), "nlink": info.st_nlink,
        "uid": info.st_uid,
    }
    if sized:
        value["size"] = info.st_size
    return value


def _identity_map(value: object, *, sized: bool,
                  allowed_uids: set[int] | None = None) -> bool:
    keys = {"dev", "ino", "mode", "nlink", "uid"} | ({"size"} if sized else set())
    if not isinstance(value, dict) or set(value) != keys:
        return False
    if any(isinstance(value[key], bool) or not isinstance(value[key], int)
           for key in keys):
        return False
    return (value["dev"] >= 0 and value["ino"] > 0 and value["nlink"] >= 1
            and 0 <= value["mode"] <= 0o7777
            and (not sized or value["size"] >= 0)
            and (allowed_uids is None or value["uid"] in allowed_uids))


def _owned_regular_snapshot_at(directory_fd: int, name: str,
                               *, max_bytes: int,
                               expected_mode: int = 0o600) -> tuple[bytes, os.stat_result] | None:
    """Read a same-owner, single-link regular file through a pinned directory."""
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=directory_fd)
    except (OSError, TypeError, ValueError):
        return None
    try:
        before = os.fstat(fd)
        try:
            path_before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            return None
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) != expected_mode
                or before.st_size < 0 or before.st_size > max_bytes
                or not stat.S_ISREG(path_before.st_mode)
                or path_before.st_nlink != 1
                or path_before.st_uid != os.geteuid()
                or (before.st_dev, before.st_ino)
                != (path_before.st_dev, path_before.st_ino)):
            return None
        chunks: list[bytes] = []
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(fd, min(65536, before.st_size - offset), offset)
            if not chunk:
                return None
            chunks.append(chunk)
            offset += len(chunk)
        after = os.fstat(fd)
        try:
            path_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            return None
        epoch = lambda value: (value.st_dev, value.st_ino, value.st_mode,
                               value.st_uid, value.st_nlink, value.st_size,
                               value.st_mtime_ns, value.st_ctime_ns)
        if epoch(before) != epoch(after) or epoch(after) != epoch(path_after):
            return None
        return b"".join(chunks), after
    finally:
        os.close(fd)


def _supervisor_process(value: object, *, child: bool) -> bool:
    keys = {"pid", "start_ticks", "boot_id", "host",
            "host_id_source", "host_id_sha256"}
    if child:
        keys |= {"pgid", "argv_sha256"}
    if not isinstance(value, dict) or set(value) != keys:
        return False
    integer_keys = {"pid", "start_ticks"} | ({"pgid"} if child else set())
    if any(isinstance(value[key], bool) or not isinstance(value[key], int)
           or value[key] <= 0 for key in integer_keys):
        return False
    if any(not isinstance(value[key], str) or not value[key]
           or len(value[key]) > 256
           for key in ("boot_id", "host", "host_id_source")):
        return False
    return (re.fullmatch(r"[0-9a-f]{64}", str(value["host_id_sha256"])) is not None
            and (not child or re.fullmatch(
                r"[0-9a-f]{64}", str(value["argv_sha256"])) is not None))


def _supervisor_tmux(value: object, supervisor: object) -> bool:
    if (not isinstance(value, dict) or set(value) != {
            "session_id", "pane_id", "pane_pid", "pane_start_ticks"}
            or not _supervisor_process(supervisor, child=False)):
        return False
    return (all(isinstance(value[key], str)
                and re.fullmatch(r"[%$][0-9]{1,12}", value[key]) is not None
                for key in ("session_id", "pane_id"))
            and value["pane_pid"] == supervisor["pid"]
            and value["pane_start_ticks"] == supervisor["start_ticks"])


def _supervisor_ledger(raw: bytes, *, spec_sha256: str,
                       session_name: str, runtime_root: Path,
                       expected_success: bool = False) -> list[dict] | None:
    """Validate canonical ledger rows and one exact max-restart-0 FSM."""
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError:
        return None
    expected_length = 4 if expected_success else 5
    if len(lines) != expected_length or not raw.endswith(b"\n"):
        return None
    rows: list[dict] = []
    previous = None
    previous_time = None
    for sequence, line in enumerate(lines, 1):
        row = _strict_json_bytes(line.encode("ascii"))
        if (row is None or set(row) != {
                "event", "payload", "previous_sha256", "record_sha256",
                "schema", "sequence", "written_at"}
                or row.get("schema") != _SUPERVISOR_LEDGER_SCHEMA
                or row.get("sequence") != sequence
                or row.get("previous_sha256") != previous
                or not isinstance(row.get("event"), str)
                or not isinstance(row.get("payload"), dict)
                or not isinstance(row.get("written_at"), str)
                or _parse_semantic_timestamp(row["written_at"]) is None
                or re.fullmatch(r"[0-9a-f]{64}", str(
                    row.get("record_sha256"))) is None
                or line.encode("ascii") != _canonical_json_bytes(row)):
            return None
        written = _parse_semantic_timestamp(row["written_at"])
        if previous_time is not None and written < previous_time:
            return None
        body = dict(row)
        digest = body.pop("record_sha256")
        expected = hashlib.sha256(_canonical_json_bytes(body)).hexdigest()
        if digest != expected:
            return None
        rows.append(row)
        previous = digest
        previous_time = written
    expected_events = ([
        "supervisor_started", "child_started", "child_exited",
        "supervisor_stopped"] if expected_success else [
        "supervisor_started", "child_started", "child_exited",
        "restarts_exhausted", "supervisor_stopped"])
    if [row["event"] for row in rows] != expected_events:
        return None
    started = rows[0]["payload"]
    child_start = rows[1]["payload"]
    child_exit = rows[2]["payload"]
    exhausted = None if expected_success else rows[3]["payload"]
    stopped = rows[-1]["payload"]
    return_code = child_exit.get("return_code")
    supervisor = started.get("supervisor")
    tmux = started.get("tmux")
    cgroup = child_start.get("cgroup")
    cleanup = child_exit.get("cleanup_actions")
    cgroup_name = "epyc-autokernel-" + hashlib.sha256(
        str(runtime_root).encode("utf-8")).hexdigest()[:24]
    expected_cgroup_path = (
        f"/sys/fs/cgroup/{cgroup_name}-{supervisor.get('pid') if isinstance(supervisor, dict) else 0}-0")
    allowed_cleanup = {
        ("cgroup.remove",),
        ("pidfd:SIGTERM", "cgroup.remove"),
        ("cgroup.kill", "cgroup.remove"),
        ("pidfd:SIGTERM", "cgroup.kill", "cgroup.remove"),
    }
    if (set(started) != {"spec_sha256", "session_name", "supervisor", "tmux"}
            or started.get("spec_sha256") != spec_sha256
            or started.get("session_name") != session_name
            or not _supervisor_process(supervisor, child=False)
            or not _supervisor_tmux(tmux, supervisor)
            or set(child_start) != {
                "restart_count", "child", "stdout", "stderr", "cgroup"}
            or child_start.get("restart_count") != 0
            or not _supervisor_process(child_start.get("child"), child=True)
            or any(child_start["child"].get(key) != supervisor.get(key)
                   for key in ("boot_id", "host", "host_id_source",
                               "host_id_sha256"))
            or child_start.get("stdout") != str(runtime_root / "controller.stdout.log")
            or child_start.get("stderr") != str(runtime_root / "controller.stderr.log")
            or not isinstance(cgroup, dict)
            or set(cgroup) != {"dev", "ino", "mode", "nlink", "path", "uid"}
            or not _identity_map({key: cgroup[key] for key in (
                "dev", "ino", "mode", "nlink", "uid")}, sized=False)
            or cgroup.get("uid") != os.geteuid()
            or cgroup.get("mode") != 0o700 or cgroup.get("nlink", 0) < 2
            or cgroup.get("path") != expected_cgroup_path
            or set(child_exit) != {
                "restart_count", "return_code", "cleanup_actions", "stop_signal"}
            or child_exit.get("restart_count") != 0
            or not isinstance(cleanup, list)
            or (tuple(cleanup) != ("cgroup.remove",) if expected_success
                else tuple(cleanup) not in allowed_cleanup)
            or child_exit.get("stop_signal") is not None
            or isinstance(return_code, bool) or not isinstance(return_code, int)
            or expected_success and return_code != 0
            or not expected_success and return_code == 0
            or not expected_success and (
                not isinstance(exhausted, dict)
                or set(exhausted) != {
                    "restart_count", "max_restarts", "last_return_code"}
                or exhausted.get("restart_count") != 0
                or exhausted.get("last_return_code") != return_code
                or exhausted.get("max_restarts") != 0)
            or set(stopped) != {
                "exit_code", "restart_count", "stop_signal", "supervisor"}
            or stopped.get("restart_count") != 0
            or stopped.get("stop_signal") is not None
            or stopped.get("supervisor") != supervisor
            or stopped.get("exit_code") != return_code):
        return None
    return rows


def _owned_public_snapshot(path: Path, *, max_bytes: int) \
        -> tuple[bytes, os.stat_result] | None:
    """Snapshot an owner-bound sealed input whose mode may be read-only public."""
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    parent_fd = None
    try:
        parent_info = path.parent.lstat()
        if (not stat.S_ISDIR(parent_info.st_mode)
                or parent_info.st_uid != os.geteuid()
                or stat.S_IMODE(parent_info.st_mode) & 0o022):
            return None
        parent_fd = os.open(path.parent, flags)
        pinned = os.fstat(parent_fd)
        if ((pinned.st_dev, pinned.st_ino) !=
                (parent_info.st_dev, parent_info.st_ino)):
            return None
        leaf = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        mode = stat.S_IMODE(leaf.st_mode)
        if mode & 0o022:
            return None
        snapshot = _owned_regular_snapshot_at(
            parent_fd, path.name, max_bytes=max_bytes, expected_mode=mode)
        after = path.parent.lstat()
        if ((pinned.st_dev, pinned.st_ino, pinned.st_mtime_ns, pinned.st_ctime_ns)
                != (after.st_dev, after.st_ino,
                    after.st_mtime_ns, after.st_ctime_ns)):
            return None
        return snapshot
    except OSError:
        return None
    finally:
        if parent_fd is not None:
            os.close(parent_fd)


def _supervisor_launch_spec(
        raw: bytes, *, runtime_root: Path, runtime_info: os.stat_result,
        config_path: Path, config: dict,
        config_source: tuple[bytes, os.stat_result],
        config_copy: tuple[bytes, os.stat_result]) -> tuple[dict, str] | None:
    """Validate the full v2 producer grammar and rederive its content identity."""
    value = _strict_json_bytes(raw)
    v2_expected = {
        "schema", "kind", "runtime_root", "runtime_root_identity",
        "deployment_config", "validate_only", "canary", "python",
        "restart_policy", "termination_policy", "execution_closure",
        "execution_modules", "cgroup"}
    v3_expected = v2_expected | {"graph_execution_modules"}
    schema = value.get("schema") if isinstance(value, dict) else None
    if (value is None
            or schema == _SUPERVISOR_SPEC_SCHEMA and set(value) != v2_expected
            or schema == _SUPERVISOR_SPEC_SCHEMA_V3 and set(value) != v3_expected
            or schema == _SUPERVISOR_SPEC_SCHEMA_V4 and set(value) != v3_expected
            or schema not in {_SUPERVISOR_SPEC_SCHEMA, _SUPERVISOR_SPEC_SCHEMA_V3,
                              _SUPERVISOR_SPEC_SCHEMA_V4}
            or raw != _canonical_json_bytes(value) + b"\n"
            or value.get("kind") != "deployment"
            or value.get("runtime_root") != str(runtime_root)
            or value.get("runtime_root_identity") !=
            _stat_identity(runtime_info, sized=False)
            or value.get("validate_only") is not False
            or value.get("canary") is not None):
        return None
    python_path = value.get("python")
    if (not isinstance(python_path, str) or not Path(python_path).is_absolute()
            or ".." in Path(python_path).parts):
        return None
    restart = value.get("restart_policy")
    termination = value.get("termination_policy")
    if (restart != {"max_restarts": 0, "delay_seconds": 2.0}
            or not isinstance(termination, dict)
            or set(termination) != {"term_grace_seconds", "kill_grace_seconds"}
            or any(isinstance(termination[key], bool)
                   or not isinstance(termination[key], (int, float))
                   or not math.isfinite(float(termination[key]))
                   or not 0.1 <= float(termination[key]) <= 60.0
                   for key in termination)):
        return None
    deployment = value.get("deployment_config")
    source_raw, source_info = config_source
    copy_raw, copy_info = config_copy
    try:
        source_value = _strict_json_bytes(source_raw)
        copy_value = _strict_json_bytes(copy_raw)
    except ValueError:
        return None
    deployment_keys = {
        "source_path", "source_identity", "runtime_leaf",
        "canonical_sha256", "canonical_size", "identity"}
    if schema == _SUPERVISOR_SPEC_SCHEMA_V4:
        deployment_keys.add("semantic_sha256")
    semantic_sha = (hashlib.sha256(_canonical_json_bytes({
        key: item for key, item in config.items() if key != "config_sha256"
    })).hexdigest() if isinstance(config, dict) else None)
    if (not isinstance(deployment, dict) or set(deployment) != deployment_keys
            or deployment.get("source_path") != str(config_path)
            or deployment.get("source_identity") !=
            _stat_identity(source_info, sized=True)
            or deployment.get("runtime_leaf") != "deployment-config.json"
            or deployment.get("identity") != _stat_identity(copy_info, sized=True)
            or deployment.get("canonical_size") != len(copy_raw)
            or deployment.get("canonical_sha256") !=
            hashlib.sha256(copy_raw).hexdigest()
            or source_value != config or copy_value != config
            or copy_raw != _canonical_json_bytes(config) + b"\n"
            or schema == _SUPERVISOR_SPEC_SCHEMA_V4 and (
                deployment.get("semantic_sha256") != config.get("config_sha256")
                or semantic_sha != config.get("config_sha256"))):
        return None
    closure = value.get("execution_closure")
    if (not isinstance(closure, dict) or set(closure) != {
            "path", "content_sha256", "manifest", "manifest_sha256",
            "root_identity"}
            or not isinstance(closure.get("path"), str)
            or not Path(closure["path"]).is_absolute()
            or Path(closure["path"]).parent !=
            Path("/var/lib/epyc-autokernel/execution-closures")
            or re.fullmatch(r"[0-9a-f]{64}", str(
                closure.get("content_sha256"))) is None
            or Path(closure["path"]).name != closure["content_sha256"]
            or re.fullmatch(r"[0-9a-f]{64}", str(
                closure.get("manifest_sha256"))) is None
            or not _identity_map(closure.get("root_identity"), sized=False,
                                 allowed_uids={0})
            or not isinstance(closure.get("manifest"), dict)):
        return None
    manifest = closure["manifest"]
    content_manifest = {}
    for relative, binding in manifest.items():
        if (not isinstance(relative, str) or not relative.startswith("scripts/")
                or ".." in Path(relative).parts
                or not isinstance(binding, dict)
                or set(binding) != {"sha256", "source", "closure"}
                or re.fullmatch(r"[0-9a-f]{64}", str(
                    binding.get("sha256"))) is None
                or not _identity_map(binding.get("source"), sized=True)
                or not _identity_map(binding.get("closure"), sized=True,
                                     allowed_uids={0})):
            return None
        content_manifest[relative] = binding["sha256"]
    if (hashlib.sha256(_canonical_json_bytes(manifest)).hexdigest()
            != closure["manifest_sha256"]
            or hashlib.sha256(_canonical_json_bytes(content_manifest)).hexdigest()
            != closure["content_sha256"]):
        return None
    modules = value.get("execution_modules")
    module_files = {
        "supervisor": "discovery_supervisor.py",
        "deployment_factory": "discovery_deployment_factory.py",
        "secure_runtime": "discovery_supervisor_secure.py"}
    if not isinstance(modules, dict) or set(modules) != set(module_files):
        return None
    for module, filename in module_files.items():
        binding = modules[module]
        expected_path = (Path(closure["path"]) /
                         "scripts/kernel_rnd/autokernel/controller" / filename)
        if (not isinstance(binding, dict) or set(binding) != {"path", "sha256"}
                or binding.get("path") != str(expected_path)
                or re.fullmatch(r"[0-9a-f]{64}", str(
                    binding.get("sha256"))) is None
                or manifest.get(
                    f"scripts/kernel_rnd/autokernel/controller/{filename}", {}
                ).get("sha256") != binding["sha256"]):
            return None
    if schema in {_SUPERVISOR_SPEC_SCHEMA_V3, _SUPERVISOR_SPEC_SCHEMA_V4}:
        graph_modules = value.get("graph_execution_modules")
        graph_module_contract = (
            _SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26
            if schema == _SUPERVISOR_SPEC_SCHEMA_V4
            and config.get("schema") ==
                "epyc.autokernel.discovery_deployment.v5"
            else _SUPERVISOR_GRAPH_EXECUTION_MODULES_V3)
        if (not isinstance(graph_modules, dict)
                or set(graph_modules) != set(graph_module_contract)):
            return None
        for role, logical_path in graph_module_contract.items():
            binding = graph_modules[role]
            if (not isinstance(binding, dict)
                    or set(binding) != {"logical_path", "sha256"}
                    or binding.get("logical_path") != logical_path
                    or re.fullmatch(r"[0-9a-f]{64}", str(
                        binding.get("sha256"))) is None
                    or manifest.get(logical_path, {}).get("sha256")
                    != binding["sha256"]):
                return None
    cgroup = value.get("cgroup")
    expected_cgroup = (
        "epyc-autokernel-" + hashlib.sha256(
            str(runtime_root).encode("utf-8")).hexdigest()[:24])
    if (not isinstance(cgroup, dict) or set(cgroup) != {"name", "base"}
            or cgroup.get("base") != "/sys/fs/cgroup"
            or cgroup.get("name") != expected_cgroup):
        return None
    return value, hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _supervisor_terminal_observation(bundle: Path, config_path: Path,
                                     config: dict) -> dict | None:
    """Read a pre-controller terminal from the bundle's sealed supervisor.

    The controller contract remains authoritative once it exists.  This narrow
    fallback proves only that the corresponding sealed deployment was launched
    and its child failed before controller state or telemetry could be written.
    No supervisor log bytes are ever exported.
    """
    name = bundle.name
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", name) is None:
        return None
    root = AUTOKERNEL_SUPERVISORS_ROOT
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    root_fd = runtime_fd = None
    try:
        root_info = root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode)
                or root_info.st_uid != os.geteuid()
                or stat.S_IMODE(root_info.st_mode) != 0o700):
            return None
        root_fd = os.open(root, flags)
        pinned_root = os.fstat(root_fd)
        if ((pinned_root.st_dev, pinned_root.st_ino)
                != (root_info.st_dev, root_info.st_ino)):
            return None
        runtime_fd = os.open(name, flags, dir_fd=root_fd)
        runtime_info = os.fstat(runtime_fd)
        path_info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(runtime_info.st_mode)
                or runtime_info.st_uid != os.geteuid()
                or stat.S_IMODE(runtime_info.st_mode) != 0o700
                or not stat.S_ISDIR(path_info.st_mode)
                or (runtime_info.st_dev, runtime_info.st_ino)
                != (path_info.st_dev, path_info.st_ino)):
            return None
        snapshots = {
            filename: _owned_regular_snapshot_at(
                runtime_fd, filename, max_bytes=limit)
            for filename, limit in (
                ("identity.json", 16 * 1024),
                ("death-ledger.jsonl", 128 * 1024),
                ("deployment-config.json", 256 * 1024),
                ("launch-spec.json", 2 * 1024 * 1024),
                ("controller.stderr.log", 64 * 1024),
            )
        }
        if any(value is None for value in snapshots.values()):
            return None
        source_snapshot = _owned_public_snapshot(config_path, max_bytes=256 * 1024)
        if source_snapshot is None:
            return None
        identity_raw = snapshots["identity.json"][0]
        identity = _strict_json_bytes(identity_raw)
        spec_result = _supervisor_launch_spec(
            snapshots["launch-spec.json"][0], runtime_root=root / name,
            runtime_info=runtime_info, config_path=config_path, config=config,
            config_source=source_snapshot,
            config_copy=snapshots["deployment-config.json"])
        if spec_result is None:
            return None
        launch_spec, spec_sha256 = spec_result
        session_name = "ak-" + spec_sha256[:24]
        ledger = _supervisor_ledger(
            snapshots["death-ledger.jsonl"][0], spec_sha256=spec_sha256,
            session_name=session_name, runtime_root=root / name)
        stderr = snapshots["controller.stderr.log"][0]
        expected_identity_keys = {
            "child", "exit_code", "restart_count", "schema", "session_name",
            "spec_sha256", "state", "supervisor", "tmux", "tmux_socket_name",
            "updated_at"}
        if (identity is None or set(identity) != expected_identity_keys
                or identity_raw != _canonical_json_bytes(identity) + b"\n"
                or identity.get("schema") != _SUPERVISOR_IDENTITY_SCHEMA
                or identity.get("spec_sha256") != spec_sha256
                or identity.get("session_name") != session_name
                or identity.get("tmux_socket_name") !=
                "epyc-autokernel-supervisors"
                or identity.get("state") != "stopped"
                or identity.get("child") is not None
                or identity.get("restart_count") != 0
                or isinstance(identity.get("exit_code"), bool)
                or not isinstance(identity.get("exit_code"), int)
                or identity["exit_code"] == 0
                or not _supervisor_process(identity.get("supervisor"), child=False)
                or not _supervisor_tmux(
                    identity.get("tmux"), identity.get("supervisor"))
                or not isinstance(identity.get("updated_at"), str)
                or _parse_semantic_timestamp(identity["updated_at"]) is None
                or ledger is None):
            return None
        first_payload = ledger[0]["payload"]
        final_payload = ledger[-1]["payload"]
        identity_time = _parse_semantic_timestamp(identity["updated_at"])
        final_time = _parse_semantic_timestamp(ledger[-1]["written_at"])
        if (identity.get("supervisor") != first_payload["supervisor"]
                or identity.get("tmux") != first_payload["tmux"]
                or final_payload.get("supervisor") != identity["supervisor"]
                or final_payload.get("exit_code") != identity["exit_code"]
                or identity_time < final_time or identity_time - final_time > 5.0
                or identity_time > time.time() + 5.0):
            return None
        # Revalidate the directory binding after every file snapshot.
        runtime_after = os.fstat(runtime_fd)
        path_after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        root_after = root.lstat()
        if ((runtime_info.st_dev, runtime_info.st_ino,
             runtime_info.st_mtime_ns, runtime_info.st_ctime_ns)
                != (runtime_after.st_dev, runtime_after.st_ino,
                    runtime_after.st_mtime_ns, runtime_after.st_ctime_ns)
                or (runtime_after.st_dev, runtime_after.st_ino)
                != (path_after.st_dev, path_after.st_ino)
                or (pinned_root.st_dev, pinned_root.st_ino,
                    pinned_root.st_mtime_ns, pinned_root.st_ctime_ns)
                != (root_after.st_dev, root_after.st_ino,
                    root_after.st_mtime_ns, root_after.st_ctime_ns)):
            return None
        mismatch = stderr.rstrip().endswith(_SUPERVISOR_GRAPH_MISMATCH)
        if not mismatch:
            return None
        stderr_sha256 = hashlib.sha256(stderr).hexdigest()
        return {
            "state": "failed", "phase": "deployment_graph_revalidation",
            "failure_class": "durable_deployment_graph_mismatch",
            "return_code": identity["exit_code"],
            "occurred_at": identity["updated_at"],
            "stamp": _parse_semantic_timestamp(identity["updated_at"]),
            "stderr": {"sha256": stderr_sha256, "size": len(stderr),
                       "detail": "controller stderr matched the bounded deployment-graph mismatch signature"},
            "detail": "The durable deployment graph differed during sealed-graph revalidation.",
            "recovery": "Do not resume this deployment; launch a fresh sealed successor.",
            "gpu_expected": False,
            "ledger_tail_sha256": ledger[-1]["record_sha256"],
        }
    except (OSError, TypeError, ValueError):
        return None
    finally:
        if runtime_fd is not None:
            os.close(runtime_fd)
        if root_fd is not None:
            os.close(root_fd)


def _supervisor_normal_terminal_observation(
        bundle: Path, config_path: Path, config: dict) -> dict | None:
    """Validate the sealed supervisor's exact normal rc0 terminal.

    Unlike the pre-controller failure adapter, this path exports no stderr and
    accepts only the four-event success FSM.  Both process identities must be
    gone and the exact controller cgroup must have been removed.
    """
    name = bundle.name
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", name) is None:
        return None
    root = AUTOKERNEL_SUPERVISORS_ROOT
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    root_fd = runtime_fd = None
    try:
        root_info = root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode)
                or root_info.st_uid != os.geteuid()
                or stat.S_IMODE(root_info.st_mode) != 0o700):
            return None
        root_fd = os.open(root, flags)
        pinned_root = os.fstat(root_fd)
        if ((pinned_root.st_dev, pinned_root.st_ino)
                != (root_info.st_dev, root_info.st_ino)):
            return None
        runtime_fd = os.open(name, flags, dir_fd=root_fd)
        runtime_info = os.fstat(runtime_fd)
        path_info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(runtime_info.st_mode)
                or runtime_info.st_uid != os.geteuid()
                or stat.S_IMODE(runtime_info.st_mode) != 0o700
                or not stat.S_ISDIR(path_info.st_mode)
                or (runtime_info.st_dev, runtime_info.st_ino)
                != (path_info.st_dev, path_info.st_ino)):
            return None
        snapshots = {
            filename: _owned_regular_snapshot_at(
                runtime_fd, filename, max_bytes=limit)
            for filename, limit in (
                ("identity.json", 16 * 1024),
                ("death-ledger.jsonl", 128 * 1024),
                ("deployment-config.json", 256 * 1024),
                ("launch-spec.json", 2 * 1024 * 1024),
            )
        }
        if any(value is None for value in snapshots.values()):
            return None
        source_snapshot = _owned_public_snapshot(config_path, max_bytes=256 * 1024)
        if source_snapshot is None:
            return None
        identity_raw = snapshots["identity.json"][0]
        identity = _strict_json_bytes(identity_raw)
        spec_result = _supervisor_launch_spec(
            snapshots["launch-spec.json"][0], runtime_root=root / name,
            runtime_info=runtime_info, config_path=config_path, config=config,
            config_source=source_snapshot,
            config_copy=snapshots["deployment-config.json"])
        if spec_result is None:
            return None
        _launch_spec, spec_sha256 = spec_result
        session_name = "ak-" + spec_sha256[:24]
        ledger = _supervisor_ledger(
            snapshots["death-ledger.jsonl"][0], spec_sha256=spec_sha256,
            session_name=session_name, runtime_root=root / name,
            expected_success=True)
        expected_identity_keys = {
            "child", "exit_code", "restart_count", "schema", "session_name",
            "spec_sha256", "state", "supervisor", "tmux", "tmux_socket_name",
            "updated_at"}
        if (identity is None or set(identity) != expected_identity_keys
                or identity_raw != _canonical_json_bytes(identity) + b"\n"
                or identity.get("schema") != _SUPERVISOR_IDENTITY_SCHEMA
                or identity.get("spec_sha256") != spec_sha256
                or identity.get("session_name") != session_name
                or identity.get("tmux_socket_name") !=
                "epyc-autokernel-supervisors"
                or identity.get("state") != "stopped"
                or identity.get("child") is not None
                or identity.get("restart_count") != 0
                or identity.get("exit_code") != 0
                or not _supervisor_process(
                    identity.get("supervisor"), child=False)
                or not _supervisor_tmux(
                    identity.get("tmux"), identity.get("supervisor"))
                or not isinstance(identity.get("updated_at"), str)
                or _parse_semantic_timestamp(identity["updated_at"]) is None
                or ledger is None):
            return None
        first_payload = ledger[0]["payload"]
        child_payload = ledger[1]["payload"]
        final_payload = ledger[-1]["payload"]
        identity_time = _parse_semantic_timestamp(identity["updated_at"])
        final_time = _parse_semantic_timestamp(ledger[-1]["written_at"])
        if (identity.get("supervisor") != first_payload["supervisor"]
                or identity.get("tmux") != first_payload["tmux"]
                or final_payload.get("supervisor") != identity["supervisor"]
                or final_payload.get("exit_code") != 0
                or identity_time is None or final_time is None
                or identity_time < final_time or identity_time - final_time > 5.0
                or identity_time > time.time() + 5.0):
            return None
        child = child_payload["child"]
        for process in (identity["supervisor"], child):
            observed = _discovery_proc_stat(process["pid"])
            if observed is not None and observed[2] == process["start_ticks"]:
                return None
        cgroup_path = Path(child_payload["cgroup"]["path"])
        if cgroup_path.exists() or cgroup_path.is_symlink():
            return None
        runtime_after = os.fstat(runtime_fd)
        path_after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        root_after = root.lstat()
        if ((runtime_info.st_dev, runtime_info.st_ino,
             runtime_info.st_mtime_ns, runtime_info.st_ctime_ns)
                != (runtime_after.st_dev, runtime_after.st_ino,
                    runtime_after.st_mtime_ns, runtime_after.st_ctime_ns)
                or (runtime_after.st_dev, runtime_after.st_ino)
                != (path_after.st_dev, path_after.st_ino)
                or (pinned_root.st_dev, pinned_root.st_ino,
                    pinned_root.st_mtime_ns, pinned_root.st_ctime_ns)
                != (root_after.st_dev, root_after.st_ino,
                    root_after.st_mtime_ns, root_after.st_ctime_ns)):
            return None
        return {
            "state": "stopped", "exit_code": 0, "restart_count": 0,
            "occurred_at": identity["updated_at"], "stamp": identity_time,
            "ledger_tail_sha256": ledger[-1]["record_sha256"],
        }
    except (OSError, TypeError, ValueError):
        return None
    finally:
        if runtime_fd is not None:
            os.close(runtime_fd)
        if root_fd is not None:
            os.close(root_fd)


def _supervisor_failure_activity(observation: dict) -> dict:
    """Project a typed pre-controller terminal into the live activity schema."""
    stage = observation["phase"]
    at = observation["occurred_at"]
    return {
        "status": "failed",
        "phase": {"id": stage, "label": "Deployment graph revalidation failed",
                  "started_at": None, "elapsed_s": None},
        "turn": None, "hypothesis_id": None,
        "last_progress_at": at, "progress_age_s": None,
        "waiting_on": "fresh sealed successor deployment",
        "stall": {"state": "failed", "threshold_s": None,
                  "detail": observation["detail"]},
        "gpu": {"expected_now": False, "claim_held": False,
                "claim_released": False, "claim_id": None, "device_id": None,
                "screen_started": False,
                "detail": "GPU was not expected or claimed; controller startup did not complete."},
        "stage_contract": {
            "current_stage": stage, "first_incomplete_stage": stage,
            "resume_policy": "fresh_sealed_successor_required",
            "repetition": None, "replication": None, "arm_order": None,
            "arm_order_seed_sha256": None,
            "exact_attribution_direction": None,
            "exact_attribution_effect_fraction": None,
            "target_runtime_effect_fraction": None,
            "target_runtime_executed": None, "target_runtime_reason": None,
            "dual_decision_state": None, "measurement_process_progress": None,
        },
        "refusal": {"detected": False, "type": None, "class": None,
                    "stage": None, "scientific_budget_spent": None,
                    "receipt_sha256": None, "detail": None,
                    "measurement_output": None},
        "provider_retry": {"detected": False, "actor": None,
                           "same_hypothesis": None, "planner_rerun": None,
                           "provider_attempt": None, "detail": None},
        "correctness": {"execution_started": False,
                        "execution_completed": False,
                        "validation_passed": None},
        "checkpoint": {"available": True, "kind": "SUPERVISOR_TERMINAL",
                       "state": "pre_controller_terminal",
                       "detail": "validated supervisor death-ledger terminal"},
        "resume": {"required": True, "possible": False,
                   "recoverability": "fresh_sealed_successor_required",
                   "disposition": "fresh_sealed_successor_required",
                   "detail": observation["recovery"]},
        "failure": {"detected": True, "stage": stage,
                    "class": observation["failure_class"],
                    "detail": observation["detail"],
                    "recovery": observation["recovery"],
                    "stderr": observation["stderr"],
                    "return_code": observation["return_code"],
                    "ledger_tail_sha256": observation["ledger_tail_sha256"]},
        "pipeline": [{"id": stage, "label": "Deployment graph revalidation",
                      "state": "failed", "detail": observation["detail"]}],
        "transitions": [{"ts": at, "stage": stage, "phase": stage,
                         "state": "failed", "event": "supervisor_child_failed",
                         "label": "Deployment graph revalidation failed",
                         "detail": observation["detail"]}],
        "completed_iterations": 0,
        "history": {"abandoned_count": 0, "retest_count": 0,
                    "terminal_count": 0,
                    "summary": "pre-controller terminal · no hypothesis began",
                    "rows": [], "terminal_rows": []},
    }


def _discovery_live_read() -> tuple[dict, panels.Observation]:
    candidates: list[dict] = []
    try:
        configs = list(AUTOKERNEL_DEPLOYMENTS_ROOT.glob("*/config/deployment.json"))[:512]
    except OSError as exc:
        payload = {"schema": "epyc.dashboard.autokernel_live.v1", "available": False,
                   "active": False, "error": f"deployment discovery failed: {exc}",
                   "autokernel_log": [], "planner_log": []}
        return payload, panels.Observation(False, detail=payload["error"])
    for config_path in configs:
        present, config, error = _read_json_object(config_path, "discovery deployment")
        if not present or config is None or error:
            continue
        bundle = config_path.parent.parent
        v26_contract = None
        if config.get("schema") == "epyc.autokernel.discovery_deployment.v5":
            v26_contract = _discovery_v26_contract(
                config_path, config, bundle)
            if v26_contract is None:
                continue
        elif config.get("schema") == "epyc.autokernel.discovery_deployment.v6":
            v26_contract = _discovery_v27_contract(
                config_path, config, bundle)
            if (v26_contract is None
                    or v26_contract.get("ready") is not True):
                # Schema support alone is not product authority.  Until all
                # final-root pins are installed atomically, even an unlaunched
                # v27 bundle remains invisible to the live selection surface.
                continue
        controller = config.get("controller")
        if not isinstance(controller, dict):
            continue
        campaign_kind = config.get("campaign_kind", "kernel_source")
        if campaign_kind not in {"kernel_source", "experimental_runtime"}:
            continue
        runtime_descriptor = None
        if campaign_kind == "experimental_runtime":
            runtime_descriptor = _experimental_runtime_descriptor(config, bundle)
            if runtime_descriptor is None:
                continue
        state_root = _safe_bundle_path(controller.get("state_root"), bundle)
        operations_root = _safe_bundle_path(controller.get("operations_root"), bundle)
        if state_root is None or operations_root is None:
            continue
        lock_held = _discovery_lock_held(state_root / "controller.run.lock")
        try:
            config_stamp = config_path.stat().st_mtime
        except OSError:
            continue
        state_present, state, state_error = _read_json_object(
            state_root / "state.json", "discovery state")
        v26_state = None
        if v26_contract is not None and state_present:
            v26_state = (
                _discovery_v27_state_contract(state, v26_contract)
                if v26_contract.get("schema") ==
                   "epyc.autokernel.discovery_deployment.v6" else
                _discovery_v26_state_contract(state, v26_contract))
            if v26_state is None:
                continue
        (all_events, all_error, planner_events, planner_error,
         lifecycle_events, visible_all_events, visible_planner_events,
         telemetry_integrity, telemetry_snapshot_status
         ) = _discovery_event_streams(operations_root / "live")
        telemetry_integrity = _discovery_v26_actor_bypass_telemetry_integrity(
            telemetry_integrity, v26_state,
            all_events=all_events, planner_events=planner_events,
            all_error=all_error, planner_error=planner_error,
            snapshot_status=telemetry_snapshot_status)
        state_visibility_failures = _discovery_state_visibility_degraded(state)
        if state_visibility_failures:
            telemetry_integrity = dict(telemetry_integrity)
            # This producer field is append-only and has no resolution marker.
            # It proves a historical visibility incident, while the reconciled
            # physical streams above answer whether visibility is degraded NOW.
            # Keep those facts separate instead of inventing a recovery state or
            # keeping /api/health red forever after a successfully repaired copy.
            telemetry_integrity["historical_visibility_loss"] = {
                "detected": True,
                "count": len(state_visibility_failures),
                "markers": state_visibility_failures,
                "detail": (
                    f"producer recorded {len(state_visibility_failures)} historical "
                    f"telemetry visibility incident"
                    f"{'s' if len(state_visibility_failures) != 1 else ''}"),
            }
        checkpoint = (
            _discovery_v26_checkpoint(
                state_root / "journal" / "events.jsonl", now=time.time())
            if v26_contract is not None else
            _discovery_checkpoint(state_root / "journal" / "events.jsonl"))
        if (v26_state is not None
                and (checkpoint is None
                     or checkpoint.get("controller_state_sha256") !=
                        state.get("state_sha256")
                     or _parse_semantic_timestamp(
                         checkpoint.get("written_at")) is None
                     or _parse_semantic_timestamp(
                         checkpoint.get("written_at")) <
                        v26_state["updated_at_unix"] - 0.1
                     or _parse_semantic_timestamp(
                         checkpoint.get("written_at")) >
                        v26_state["updated_at_unix"] + 5.0)):
            # A self-hashed state file is not a producer checkpoint by itself.
            # Require the append-only controller journal to name the exact same
            # durable state epoch before allowing a v26 campaign to supersede
            # historical campaigns in the live projection.
            continue
        supervisor_terminal = None
        if (not state_present and not all_events and not all_error
                and not planner_events and not planner_error
                and checkpoint is None and not lock_held):
            supervisor_terminal = _supervisor_terminal_observation(
                bundle, config_path, config)
        producer_times = [
            _parse_semantic_timestamp(value) for value in (
                state.get("updated_at") if isinstance(state, dict) else None,
                checkpoint.get("written_at") if checkpoint else None,
                *(row.get("ts") for row in (*all_events, *planner_events)),
            )
        ]
        producer_times = [value for value in producer_times if value is not None]
        launched = bool(lock_held or state_present or all_events or all_error
                        or planner_events or planner_error
                        or telemetry_snapshot_status == "producer_write_in_progress"
                        or checkpoint is not None
                        or supervisor_terminal is not None)
        if (v26_contract is not None and launched
                and v26_contract.get("ready") is not True):
            # The consumer is intentionally not execution authority for a
            # moving producer worktree.  A sealed v26 can be listed only after
            # its exact module/commit freeze is installed above.
            continue
        # A deployment config's mtime says only when a bundle was sealed.  It is
        # not producer progress and therefore cannot supersede a real terminal
        # campaign in the activity hero.
        producer_stamp = max(producer_times, default=0.0)
        if supervisor_terminal is not None:
            producer_stamp = max(
                producer_stamp, float(supervisor_terminal["stamp"] or 0.0))
        if launched and not producer_times:
            for producer_path in (
                    state_root / "state.json",
                    state_root / "journal" / "events.jsonl",
                    operations_root / "live" / "autokernel.jsonl",
                    operations_root / "live" / "planner.jsonl"):
                try:
                    producer_stamp = max(producer_stamp, producer_path.stat().st_mtime)
                except OSError:
                    continue
        candidates.append({
            "lock_held": lock_held, "config_stamp": config_stamp,
            "producer_stamp": producer_stamp, "launched": launched,
            "bundle": bundle, "config": config, "state_root": state_root,
            "operations_root": operations_root, "state": state,
            "campaign_kind": campaign_kind,
            "runtime_descriptor": runtime_descriptor,
            "state_error": state_error, "all_events": all_events,
            "all_error": all_error, "planner_events": planner_events,
            "planner_error": planner_error, "checkpoint": checkpoint,
            "lifecycle_events": lifecycle_events,
            "visible_all_events": visible_all_events,
            "visible_planner_events": visible_planner_events,
            "telemetry_integrity": telemetry_integrity,
            "telemetry_snapshot_status": telemetry_snapshot_status,
            "supervisor_terminal": supervisor_terminal,
            "v26_contract": v26_contract, "v26_state": v26_state,
        })
    if not candidates:
        payload = {"schema": "epyc.dashboard.autokernel_live.v1", "available": False,
                   "active": False, "error": "no valid discovery deployment found",
                   "autokernel_log": [], "planner_log": []}
        return payload, panels.Observation(False, detail=payload["error"])
    active = [row for row in candidates if row["lock_held"]]
    launched = [row for row in candidates if row["launched"]]
    unlaunched = [row for row in candidates if not row["launched"]]
    ambiguous = len(active) > 1
    def campaign_order(row: dict) -> tuple[float, float]:
        # A launched bundle is ordered by producer-authored progress only.
        # Config mtime remains a deterministic tie-break but can never advance
        # a terminal campaign: touching a sealed config is not a new run.
        stamp = (row["producer_stamp"] if row["launched"]
                 else row["config_stamp"])
        return stamp, row["config_stamp"]

    selected = max(
        active or launched or candidates, key=campaign_order)
    newest_unlaunched = (max(unlaunched, key=lambda row: row["config_stamp"])
                         if unlaunched else None)
    if (newest_unlaunched is not None
            and newest_unlaunched["config_stamp"] <= selected["config_stamp"]):
        # An older sealed bundle is superseded history, not an available "next"
        # deployment. In particular, launching v7 must make an unlaunched v6
        # disappear from this forward-looking field.
        newest_unlaunched = None
    lock_held = selected["lock_held"]
    bundle = selected["bundle"]
    config = selected["config"]
    state_root = selected["state_root"]
    operations_root = selected["operations_root"]
    campaign_kind = selected["campaign_kind"]
    runtime_descriptor = selected["runtime_descriptor"]
    state = selected["state"]
    state_error = selected["state_error"]
    all_events = selected["all_events"]
    all_error = selected["all_error"]
    planner_events = selected["planner_events"]
    planner_error = selected["planner_error"]
    lifecycle_events = selected["lifecycle_events"]
    visible_all_events = selected["visible_all_events"]
    visible_planner_events = selected["visible_planner_events"]
    telemetry_integrity = selected["telemetry_integrity"]
    telemetry_snapshot_status = selected["telemetry_snapshot_status"]
    supervisor_terminal = selected["supervisor_terminal"]
    v26_contract = selected["v26_contract"]
    v26_state = selected["v26_state"]
    event_times = [row.get("ts") for row in (*all_events, *planner_events)
                   if isinstance(row.get("ts"), str)]
    latest_ts = max(event_times) if event_times else None
    checkpoint = selected["checkpoint"]
    now = time.time()
    campaign_terminal = _discovery_portfolio_terminal_checkpoint(
        state_root / "journal" / "events.jsonl", state, now=now)
    if campaign_terminal is not None and not lock_held:
        normal_supervisor = _supervisor_normal_terminal_observation(
            bundle, bundle / "config" / "deployment.json", config)
        if normal_supervisor is not None:
            supervisor_at = normal_supervisor["stamp"]
            if (isinstance(supervisor_at, (int, float))
                    and not isinstance(supervisor_at, bool)
                    and 0 <= supervisor_at - campaign_terminal["stamp"] <= 5.0):
                campaign_terminal = {
                    **campaign_terminal,
                    "supervisor_verified": True,
                    "supervisor_at": normal_supervisor["occurred_at"],
                    "supervisor_ledger_tail_sha256":
                        normal_supervisor["ledger_tail_sha256"],
                }
    config_sha256 = config.get("config_sha256")
    campaign_id = (f"ak-discovery-{config_sha256[:16]}"
                   if isinstance(config_sha256, str)
                   and re.fullmatch(r"[0-9a-f]{64}", config_sha256) else None)
    if supervisor_terminal is not None:
        activity = _supervisor_failure_activity(supervisor_terminal)
    elif campaign_kind == "experimental_runtime":
        claim_observation = _discovery_claim_observation(
            operations_root, campaign_id,
            purpose="AutoKernel experimental runtime validation and measurement")
        activity = _experimental_runtime_activity(
            lock_held=lock_held, campaign_id=campaign_id,
            state=state, events=lifecycle_events,
            descriptor=runtime_descriptor,
            claim_observation=claim_observation, now=now)
    else:
        build_observation = _discovery_build_observation(
            operations_root, state, config.get("config_sha256"))
        correctness_observation = _discovery_correctness_observation(
            operations_root, state)
        postbuild_observation = _discovery_postbuild_observation(
            operations_root, state)
        claim_observation = _discovery_claim_observation(
            operations_root, campaign_id)
        refusal_observation = _discovery_refusal_observation(
            bundle, state, lifecycle_events)
        refusal_history_observations = []
        if isinstance(state, dict) and isinstance(state.get("iterations"), list):
            for iteration in state["iterations"][-25:]:
                if not isinstance(iteration, dict):
                    continue
                observation = _discovery_refusal_observation(
                    bundle, {"iterations": [iteration]}, [])
                if observation is None:
                    continue
                refusal_history_observations.append({
                    **observation,
                    "turn": iteration.get("turn"),
                    "hypothesis_id": iteration.get("hypothesis_id"),
                })
        activity = _discovery_activity(
            lock_held=lock_held, campaign_id=campaign_id,
            state=state, events=lifecycle_events,
            checkpoint=checkpoint, terminal_observation=campaign_terminal,
            operation_observation=build_observation,
            correctness_observation=correctness_observation,
            postbuild_observation=postbuild_observation,
            claim_observation=claim_observation,
            refusal_observation=refusal_observation,
            refusal_history_observations=refusal_history_observations,
            now=now, v26_contract=v26_contract, v26_state=v26_state)
    # Poll time is not producer progress. In particular, a held controller lock
    # must not keep a stuck stage green forever.
    observed_ts = (_parse_semantic_timestamp(activity["last_progress_at"])
                   if activity.get("last_progress_at") else
                   _parse_semantic_timestamp(latest_ts) if latest_ts else
                   (selected["producer_stamp"] or selected["config_stamp"])
                   if selected["launched"] else
                   selected["config_stamp"])
    state_view = None
    if state is not None:
        iterations = state.get("iterations") if isinstance(state.get("iterations"), list) else []
        planner_terminal = bool(
            not lock_held and isinstance(checkpoint, dict)
            and checkpoint.get("state") == "discovery_planner_terminal_failure"
            and activity.get("status") == "failed"
            and isinstance(activity.get("failure"), dict)
            and activity["failure"].get("detected") is True)
        state_view = {
            "updated_at": state.get("updated_at"), "next": state.get("next"),
            "complete": (True if planner_terminal else state.get("complete")),
            "terminal_reason": (
                activity["failure"].get("detail") if planner_terminal
                else state.get("terminal_reason")),
            "pending": state.get("pending") is not None,
            "inflight": state.get("inflight") is not None,
            "scientific_attempts": (
                v26_state.get("scientific_attempts")
                if isinstance(v26_state, dict) else
                state.get("scientific_attempts")),
            **({
                "scientific_budget": v26_state["scientific_budget"],
                "annulled_iterations": v26_state["annulled_history"],
            } if isinstance(v26_state, dict)
                 and "scientific_budget" in v26_state
                 and "annulled_history" in v26_state else {}),
            "iterations": [{key: row.get(key) for key in
                            ("turn", "hypothesis_id", "status", "effect_fraction")}
                           for row in iterations[-25:] if isinstance(row, dict)],
        }
    deployment_history = []
    for row in sorted(
            (item for item in launched if item is not selected),
            key=campaign_order, reverse=True)[:20]:
        deployment_history.append({
            "deployment": row["bundle"].name,
            "disposition": "historical",
            "active": row["lock_held"],
            "campaign_kind": row["campaign_kind"],
            "last_progress_at": datetime.fromtimestamp(
                row["producer_stamp"] or row["config_stamp"], timezone.utc
            ).isoformat().replace("+00:00", "Z"),
        })
    payload = {
        "schema": "epyc.dashboard.autokernel_live.v1",
        "available": True, "active": lock_held, "ambiguous_active": ambiguous,
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dashboard_observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "deployment": bundle.name, "config_sha256": config.get("config_sha256"),
        "campaign_kind": campaign_kind,
        "launch_evidence": (
            "supervisor_terminal" if supervisor_terminal is not None else
            "controller" if selected["launched"] else "unlaunched"),
        "deployment_history": deployment_history,
        "newest_unlaunched_deployment": ({
            "available": True,
            "deployment": newest_unlaunched["bundle"].name,
            "config_sha256": newest_unlaunched["config"].get("config_sha256"),
            "launch_state": "not_launched",
            "sealed_at": datetime.fromtimestamp(
                newest_unlaunched["config_stamp"], timezone.utc
            ).isoformat().replace("+00:00", "Z"),
        } if newest_unlaunched else {"available": False}),
        "state": state_view, "state_error": state_error,
        "activity": activity,
        "autokernel_log": visible_all_events,
        "planner_log": visible_planner_events,
        "log_error": all_error, "planner_log_error": planner_error,
        "telemetry_integrity": telemetry_integrity,
        "telemetry_snapshot_status": telemetry_snapshot_status,
        "status_message": (
            f"{activity['status'].upper()} — {activity['phase']['label']}; "
            f"waiting on {activity['waiting_on']}"),
        "telemetry_contract": AUTOKERNEL_DISCOVERY_EVENT_SCHEMA_V2,
        "telemetry_contracts_accepted": sorted(AUTOKERNEL_DISCOVERY_EVENT_SCHEMAS),
        "telemetry_producer_commit": AUTOKERNEL_DISCOVERY_EVENT_PRODUCER_SHA,
        "discovery_product_contract": ({
            "deployment_schema": v26_contract["schema"],
            "planner_schema": v26_contract["planner_schema"],
            "graph_schema": v26_contract["graph_schema"],
            "graph_sha256": v26_contract["graph_sha256"],
            "producer_commit": v26_contract["producer_commit"],
        } if isinstance(v26_contract, dict)
             and v26_contract.get("ready") is True else None),
        "measurement_output_producer_commit":
            AUTOKERNEL_MEASUREMENT_OUTPUT_PRODUCER_SHA,
        "supervisor_schema_producer_commit":
            AUTOKERNEL_SUPERVISOR_SCHEMA_PRODUCER_SHA,
        "telemetry_note": ("Actor prompts, model text, commands, environment, and credentials are "
                           "never exported; only controller-owned lifecycle facts and hashes."),
    }
    obs = panels.Observation(
        artifact_present=True, timestamp=observed_ts,
        source=("validated supervisor terminal"
                if supervisor_terminal is not None else
                "controller lock + durable discovery telemetry"),
        populated=bool(lock_held or all_events or planner_events or state_view
                       or supervisor_terminal is not None),
        detail=("multiple controller locks are held" if ambiguous else
                f"{payload['status_message']}; telemetry visibility: "
                f"{telemetry_integrity['detail']}"),
        evidence=(str(AUTOKERNEL_SUPERVISORS_ROOT / bundle.name / "death-ledger.jsonl")
                  if supervisor_terminal is not None else
                  str(operations_root / "live")),
        silence_budget_s=(activity.get("stall", {}).get("threshold_s")
                          if lock_held else None),
        producer_idle=bool(state_view and state_view.get("complete") is True),
        unreported=(("telemetry_stream_integrity",)
                    if telemetry_integrity["state"] in {"degraded", "conflict"}
                    else ()))
    return payload, obs


def discovery_live_payload() -> dict:
    payload, observation = _discovery_live_read()
    payload["_freshness"] = _panel_envelope("kernel_live", observation)
    return payload


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
    # Additive discovery/funnel projection.  It cannot alter any strict section,
    # freshness watermark, campaign decision, champion, or promotion authority.
    data["_progression"] = _read_kernel_progression()
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
    _, discovery_live_observation = _discovery_live_read()
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
        "kernel_live": lambda: discovery_live_observation,
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
    verdict = _supplement_kernel_verdict(
        panels.fold(envs), _read_kernel_progression())
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
    "/api/kernel/live": discovery_live_payload,
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

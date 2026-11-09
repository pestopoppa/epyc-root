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
GET /api/loop                the rebuilt AutoKernel loop status (+ freshness)
GET /api/loop/health         loop and operator-gate data health only (non-recursive)
GET /machine                 the machine / live-inference page (data plane: :8000 API)
GET /autopilot               the autopilot-loop page (data plane: :8000 API)
GET /cockpit                 the AP-50 decision cockpit (data plane: :8000 API)
GET /gpu-window              the MI210 window page — G1 executor (data plane: :8000 API)
GET /amd-ai-lab/             the published AMD AI Lab static site from epyc-web
GET /nav.js                  the ONE shared cross-dashboard nav, with the registry
                             injected ahead of it as ``window.__EPYC_DASHBOARDS``
GET /api/dashboards          the dashboard directory (dashboard/registry.json) plus a
                             live 127.0.0.1 probe per declared (port, health_path)
GET /bus                     the session-bus page (static HTML, re-read per request)
GET /api/bus                 roster, per-agent liveness, inbox depth, operator tokens (+ alarms)
GET /api/queue               folded work queue (latest row per task_id) + invariant alarms
GET /api/outcome             the autopilot outcome contract (+ freshness), if exported
GET /api/gpu_window          the G1 watchdog's executor-status file (+ freshness envelope)
GET /api/pipeline            pipeline page data: flowchart counts, sessions by step, compute regions
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


from pathlib import Path


from urllib.parse import parse_qs, urlparse


_REPO_ROOT = Path(__file__).resolve().parents[1]


if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


from dashboard import campaign_status, handoff_parser, kernel_progression, knowledge, loop_spec, loop_status, panels, pipeline_status


REPO = Path(__file__).resolve().parents[1]


HANDOFF_DIR = REPO / "handoffs"


TIMELINE_PATH = REPO / "data" / "handoff_timeline.json"


GRAPH_PATH = REPO / "handoffs" / "active" / ".index-graph.json"


_STATIC = Path(__file__).resolve().parent / "static"


STATIC_HTML = _STATIC / "handoffs.html"


BUS_HTML = _STATIC / "bus.html"


BENCHMARKS_HTML = _STATIC / "benchmarks.html"


MACHINE_HTML = _STATIC / "machine.html"


AUTOPILOT_HTML = _STATIC / "autopilot.html"


COCKPIT_HTML = _STATIC / "cockpit.html"


GPU_WINDOW_HTML = _STATIC / "gpu-window.html"


LOOP_HTML = _STATIC / "loop.html"


LOOP_SPEC_HTML = _STATIC / "loop-spec.html"


KNOWLEDGE_HTML = _STATIC / "knowledge.html"


AMD_AI_LAB_DIR = _STATIC / "amd-ai-lab"


AMD_AI_LAB_HTML = AMD_AI_LAB_DIR / "index.html"


NAV_JS = _STATIC / "nav.js"


DASHBOARD_REGISTRY_JSON = Path(__file__).resolve().parent / "registry.json"


OPERATOR_GATE_BUNDLE_JSON = Path(os.environ.get(
    "OPERATOR_GATE_BUNDLE_JSON",
    "/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json"))


OPERATOR_GATE_BUNDLE_SCHEMA = "epyc.autokernel.operator_gate_bundle.v1"


OPERATOR_GATE_BUNDLE_ADVISORY_AFTER_S = 30 * 86400.0


OPERATOR_GATE_BUNDLE_MIN_ADVISORY_AFTER_S = 60.0


OPERATOR_GATE_BUNDLE_ABSENCE_MEANS = (
    "no operator-gated bundle has ever been written to this path. That is not "
    "'the champion is unmeasured' and it is not 'the gates failed' -- nothing "
    "emitted the carrier at all, so this surface has no operator evidence to "
    "show either way.")


def _operator_workload_vector(gates: list) -> list:
    """Project only identities carried by each sealed manual-research gate."""
    rows = []
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        for group in ("surfaces", "points"):
            cells = gate.get(group)
            if not isinstance(cells, list):
                continue
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                rows.append({"scope": "workload_cell", "whole_champion": False,
                             "gate": gate.get("gate"), "workload": cell.get("surface")
                             if group == "surfaces" else cell.get("workload"),
                             "model": cell.get("model"), "models": cell.get("models"),
                             "workloads": cell.get("workloads"), "recipe": cell.get("recipe"),
                             "in_flight": cell.get("in_flight"),
                             "delta_pct": cell.get("delta_pct"),
                             "anchor": cell.get("anchor") if group == "surfaces" else cell.get("production_ceiling_tps"),
                             "champion": cell.get("champion") if group == "surfaces" else cell.get("champion_tps"),
                             "artifact": gate.get("artifact"),
                             "artifact_sha256": gate.get("artifact_sha256")})
    return rows


def _operator_legacy_reference(headline: object) -> dict:
    """The compatibility headline is one selected manual-research cell."""
    headline = headline if isinstance(headline, dict) else {}
    return {"scope": "reference_cell_only", "whole_champion": False,
            "cell": "operator_selected", "workload": headline.get("workload"),
            "model": headline.get("model"), "recipe": headline.get("recipe"), "metric": headline.get("metric"),
            "in_flight": headline.get("at_in_flight")}


def _read_operator_gate_bundle() -> dict:
    """Read the operator-gated bundle, or say why it is unavailable.

    Refuses anything that does not declare the exact schema AND
    `authority: operator_gated_manual_research` AND `promotion_claim: false` -- a file
    claiming more than operator authority is rejected outright rather than displayed
    with its claim trimmed.

    EVERY reading carries a ``freshness`` envelope, on the SAME dict as the numbers
    it dates. Before this the reader validated schema and authority meticulously and
    read no timestamp at all, so ``headline.effect_fraction`` -- the ``+48.9%`` that
    is the largest figure on ``/kernel`` -- rendered identically forever after its
    emitter died. Authority answers "may this number be shown"; freshness answers
    "is it still true", and the card needs both.

    STALENESS IS SUBJECT-ANCHORED, NOT WALL-CLOCK. The first envelope fixed the
    forever-fresh defect with a 3-day wall-clock band borrowed from a STREAMING
    surface, which swapped one wrong contract for another: this producer is
    EPISODIC (one bundle per human campaign), so a perfectly current measurement
    alarmed STALE three days after its own emission with nothing having changed,
    and the operator read the banner as "stale/broken -- why keep it?". Evidence
    rots when its SUBJECT moves, and the subject is computable:
    ``loop_status.opgate_subject_verdict`` folds the measured commit's
    champion-lineage relationship and the production anchor's identity with the
    currently-resolved frozen production kernel into ``relevant`` /
    ``superseded`` / ``unverifiable``. Age is informational -- shown in the
    envelope, and past the advisory threshold it adds an ADVISORY sentence --
    but it never sets the state and never alarms the card on its own.

    The envelope rides in the returned dict rather than in a parallel structure so
    no consumer can pick up the number without also picking up its date.

    DATING A BUNDLE THAT CARRIES NO DATE. ``epyc.autokernel.operator_gate_bundle.v1``
    has no ``generated_at`` field. This reader prefers one if a future emitter adds
    it, and otherwise falls back to the file's mtime -- ALWAYS labelling which, via
    ``generated_at_source``. mtime is the weaker fact (a copy or a ``touch`` moves it
    without any new measurement) and a page that presented it as the producer's own
    stamp would be overclaiming; naming the source is what keeps it honest.
    """
    now = time.time()

    def _budget(value: object) -> float:
        # The ADVISORY threshold, not a staleness gate: crossing it adds a
        # "consider re-measuring" sentence and nothing else.
        try:
            declared = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return OPERATOR_GATE_BUNDLE_ADVISORY_AFTER_S
        if isinstance(value, bool) or not math.isfinite(declared) or declared <= 0:
            return OPERATOR_GATE_BUNDLE_ADVISORY_AFTER_S
        return max(OPERATOR_GATE_BUNDLE_MIN_ADVISORY_AFTER_S,
                   min(declared, float(panels.MAX_STALE_S)))

    def _envelope(state: str, detail: str, *, generated_at: object = None,
                  source: str | None = None, age_s: float | None = None,
                  advisory_after_s: float | None = None,
                  advisory: str | None = None, basis: str = "artifact",
                  moved: list | None = None) -> dict:
        # ``basis`` says which contract produced ``state``: "subject" for the
        # relevance verdicts, "artifact" for absent/malformed. There is no
        # wall-clock basis to name, by design.
        return {"state": state, "age_s": age_s,
                "advisory_after_s": advisory_after_s, "advisory": advisory,
                "generated_at": generated_at, "generated_at_source": source,
                "basis": basis, "moved": moved or [], "detail": detail}

    def _unavailable(error: str, *, present: bool, state: str,
                     detail: str) -> dict:
        # ``evidence`` rides on the UNAVAILABLE reading too, not just the
        # successful one. A card that says "nothing has ever been written to this
        # path" without naming the path sends the investigation nowhere — and
        # absent/malformed are exactly the readings where someone is about to go
        # looking for the emitter.
        return {"available": False, "error": error,
                "artifact_present": present,
                "evidence": str(OPERATOR_GATE_BUNDLE_JSON),
                "freshness": _envelope(state, detail),
                "absence_means": OPERATOR_GATE_BUNDLE_ABSENCE_MEANS}

    try:
        raw = OPERATOR_GATE_BUNDLE_JSON.read_bytes()
    except FileNotFoundError as exc:
        return _unavailable(str(exc), present=False, state="absent",
                            detail=OPERATOR_GATE_BUNDLE_ABSENCE_MEANS)
    except OSError as exc:
        # Something is THERE and the hub cannot read it. A different, more urgent
        # fact than "never emitted", and it points at a different subsystem.
        return _unavailable(str(exc), present=OPERATOR_GATE_BUNDLE_JSON.exists(),
                            state="malformed",
                            detail=f"the bundle exists but is unreadable: {exc}")
    if not raw.strip():
        # An EMPTY file is not an absent one: something opened it. Most likely an
        # emitter that died between create and rename -- an emitter bug, not a
        # missing emitter.
        return _unavailable(
            "malformed bundle: empty file", present=True, state="malformed",
            detail=("the bundle file is empty (0 bytes of content) -- an emitter "
                    "created it and never finished writing it"))
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _unavailable(f"malformed bundle: {exc}", present=True,
                            state="malformed",
                            detail=f"the bundle is not valid JSON: {exc}")
    if not isinstance(value, dict):
        return _unavailable("bundle is not an object", present=True,
                            state="malformed",
                            detail="the bundle is not a JSON object")
    if value.get("schema") != OPERATOR_GATE_BUNDLE_SCHEMA:
        return _unavailable(
            "wrong bundle schema", present=True, state="malformed",
            detail=(f"the file declares schema {value.get('schema')!r}, not "
                    f"{OPERATOR_GATE_BUNDLE_SCHEMA!r} -- its field names would not "
                    "mean what this page says they mean"))
    if (value.get("authority") != "operator_gated_manual_research"
            or value.get("promotion_claim") is not False):
        return _unavailable(
            "bundle claims authority it may not have", present=True,
            state="malformed",
            detail=("the file claims authority this carrier may not have and was "
                    "refused whole rather than displayed with its claim trimmed"))
    champion = value.get("champion") if isinstance(value.get("champion"), dict) else {}
    headline = value.get("headline") if isinstance(value.get("headline"), dict) else None
    gates = [g for g in (value.get("gates") or []) if isinstance(g, dict)]
    # THE ANCHOR WAS ON DISK ALL ALONG AND THIS READER DROPPED IT.
    # ``production_anchor.commit`` names exactly what this bundle's +48.9% is a
    # gain OVER, and until 2026-08-30 it never reached the wire — so the largest
    # figure on the page was rendered with no anchor beside it, next to a loop
    # whose own champion is worth about a tenth of that against a DIFFERENT
    # baseline. The operator read the page and reasonably asked why the champion
    # said +48.9% when they had been told +9%. Two producers, two anchors, two
    # questions; the fix is to make every one of those three facts visible, and
    # the first of them was already in the file.
    anchor = (value.get("production_anchor")
              if isinstance(value.get("production_anchor"), dict) else {})

    budget = _budget(value.get("stale_after_s"))
    stamped = value.get("generated_at")
    written = _parse_semantic_timestamp(stamped)
    source = "body_generated_at"
    if written is None:
        try:
            written = OPERATOR_GATE_BUNDLE_JSON.stat().st_mtime
        except OSError:
            written = None
        else:
            source = "file_mtime"
            stamped = datetime.fromtimestamp(written, timezone.utc).isoformat()

    # THE VERDICT IS THE SUBJECT'S, NOT THE CLOCK'S. Computed once per reading
    # from git facts (champion lineage + current frozen production), reused for
    # both the envelope and the ``champion_relationship`` the card renders —
    # one ancestry query, not two.
    verdict = loop_status.opgate_subject_verdict(
        champion.get("commit"), anchor.get("commit"))

    if written is None:
        fresh = _envelope(
            "malformed",
            ("this bundle carries no date this reader could parse, and the file "
             "could not be stat()ed either -- a number nobody can date cannot be "
             "shown as current"),
            generated_at=None, source=None, advisory_after_s=budget)
    else:
        age = now - written
        if age < 0 and -age > panels.FUTURE_SKEW_TOLERANCE_S:
            # A reading dated in the FUTURE has no honest age to show. Same
            # rule as panels.FUTURE_SKEW_TOLERANCE_S, applied here so page and
            # fold agree: an impossible date is an emitter defect, reported as
            # such rather than rendered as an informational age.
            fresh = _envelope(
                "malformed",
                (f"this bundle is dated {-age:.0f}s IN THE FUTURE; a future "
                 "timestamp cannot age, so it is treated as undated rather "
                 "than dated"),
                generated_at=stamped, source=source, advisory_after_s=budget)
        else:
            age = max(0.0, age)
            mtime_note = ("" if source == "body_generated_at" else
                          " (dated by file mtime: the bundle carries no "
                          "generated_at of its own, so this is when the file was "
                          "last written, not necessarily when it was measured)")
            age_phrase = (f"measured {age / 86400:.1f} d ago" if age >= 86400
                          else f"measured {age / 3600:.1f} h ago")
            # Age is INFORMATIONAL. Past the advisory threshold it earns one
            # advisory sentence — text, never a state, never an alarm.
            advisory = None
            if age > budget:
                advisory = (f"{age_phrase} — consider re-measuring; this is "
                            "advisory only, because age alone never alarms an "
                            "episodic producer")
            fresh = _envelope(
                verdict["state"],
                f"{verdict['detail']}; {age_phrase}{mtime_note}"
                + (f". ADVISORY: {advisory}" if advisory else ""),
                generated_at=stamped, source=source, age_s=round(age, 1),
                advisory_after_s=budget, advisory=advisory,
                basis="subject", moved=verdict["moved"])

    return {
        "available": True,
        "artifact_present": True,
        "champion_commit": champion.get("commit"),
        "champion_branch": champion.get("branch"),
        # How the MEASURED commit relates to the CURRENT champion — computed
        # per reading from git ancestry against the champion tree, never worded
        # as a constant. The card's scope line once asserted "a different tree"
        # as prose; a reconciliation merge then made the measured commit a
        # PARENT of the champion, and the line kept rendering the opposite of
        # the truth. Four verdicts (tip / ancestor / divergent / unresolvable),
        # each earned at request time — served from the SAME resolution the
        # subject verdict above was computed from, so the envelope's state and
        # this relationship can never disagree about what git said.
        "champion_relationship": verdict["relationship"],
        # The baseline, by name. Passed through verbatim — the hub asserts
        # nothing about it and does not compare it to any constant of its own;
        # it is the EMITTER's statement of what it measured against, and the
        # card's job is to show it beside the number rather than to grade it.
        "production_anchor_commit": anchor.get("commit"),
        "not_campaign_sealed": value.get("not_campaign_sealed"),
        "headline": headline,
        "legacy_scalar_scope": _operator_legacy_reference(headline),
        "workload_vector": _operator_workload_vector(gates),
        # Per-gate measured points, each carrying BOTH arms. `delta_pct` alone
        # is a percentage with no anchor — the defect one level down from the
        # headline's — so the arm values ride with it and the page prints them.
        "gates": [{"gate": g.get("gate"), "status": g.get("status"),
                   "claim": g.get("claim"), "kind": g.get("kind"),
                   "artifact": g.get("artifact"),
                   "surfaces": [s for s in (g.get("surfaces") or [])
                                if isinstance(s, dict)],
                   "points": [p for p in (g.get("points") or [])
                              if isinstance(p, dict)]} for g in gates],
        "gates_missing": value.get("gates_missing") or [],
        "caveat": value.get("caveat"),
        "bundle_sha256": value.get("bundle_sha256"),
        "evidence": str(OPERATOR_GATE_BUNDLE_JSON),
        "freshness": fresh,
        "absence_means": OPERATOR_GATE_BUNDLE_ABSENCE_MEANS,
    }


AUTOPILOT_OUTCOME_JSON = Path(os.environ.get(
    "AUTOPILOT_OUTCOME_JSON",
    "/mnt/raid0/llm/tmp/autopilot/outcome_contract.json"))


BENCHMARK_ARTIFACT_INVENTORY = REPO / "data" / "benchmark_artifact_inventory.json"


GPU_WINDOW_STATUS_JSON = Path(os.environ.get(
    "GPU_WINDOW_STATUS_JSON",
    "/mnt/raid0/llm/tmp/gpu-window/mi210.json.executor-status.json"))


_BOARD_TTL_S = 30.0


_NO_STORE = {"Cache-Control": "no-store", "Content-Type": "application/json"}


_board_lock = threading.Lock()


_board_cache: dict | None = None


_board_cache_ts = 0.0


_HANDOFF_PATH_RE = re.compile(r"^handoffs/(active|blocked|completed|archived)/(.+)\.md$")


_ACT_EMPTY = {"commits": 0, "handoffs_touched": 0, "boxes_checked": 0, "boxes_added": 0,
              "moved": 0, "fold_commits": 0}


_ACT_WINDOW_DAYS = 14


_ACT_ROLLUPS = (1, 7, 14)




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


_watchdog_lock = threading.Lock()


_watchdog_state: dict = {}


def _panel_envelope(panel: str, obs: "panels.Observation", *,
                    now: float | None = None,
                    source_override: "panels.PanelSource | None" = None) -> dict:
    """Classify one panel's observation, updating the watchdog's memory first."""
    source = source_override or panels.source(panel)
    with _watchdog_lock:
        panels.observe_watermark(_watchdog_state, panel, obs.watermark, now=now)
        snapshot = {k: dict(v) for k, v in _watchdog_state.items()}
    return panels.envelope(source, obs, now=now, watchdog_state=snapshot)


def _flow_unavailable(reason: str, days: int = _ACT_WINDOW_DAYS) -> dict:
    """Window shape for "flow cannot be stated": no zero rollups for a page to mistake
    for a day on which nothing happened."""
    return {"available": False, "unavailable_reason": reason, "window_days": days,
            "today": datetime.now().date().isoformat(), "per_day": [], "rollups": {},
            "refactor_markers": [], "as_of": None, "commit": None}


def _flow_rollup(rows: list[dict], sel: list[dict], days: int, start: str) -> dict:
    """Sum selected per-day rows; opening stock is the row before the window."""
    prior = [r for r in rows if r["date"] < start]
    opening = prior[-1]["open_stock"] if prior else None
    closing = sel[-1]["open_stock"] if sel else opening
    if opening is None and sel:
        opening = max(0, sel[0]["open_stock"] - sel[0]["net"]
                      - sel[0].get("fold_added", 0) + sel[0].get("fold_removed", 0))
    sum_of = lambda key: sum(r.get(key, 0) for r in sel)  # noqa: E731
    closed, filed, removed = sum_of("closed"), sum_of("filed"), sum_of("removed")
    fold_adj = sum_of("fold_added") - sum_of("fold_removed")
    delta = None if opening is None or closing is None else closing - opening
    touched: set[str] = set()
    for r in sel:
        touched |= set(r.get("touched") or ())
    return {"days": days, "since": start, "commits": sum_of("commits"),
            "handoffs_touched": len(touched),
            "boxes_checked": closed, "boxes_added": filed, "removed": removed,
            "declined": sum_of("declined"), "removed_open": sum_of("removed_open"),
            "moved": sum_of("moved"), "reworded": sum_of("reworded"),
            "born_ticked": sum_of("born_ticked"),
            "net": filed - closed - removed,
            "fold_adjustment": fold_adj, "opening_stock": opening, "closing_stock": closing,
            "stock_delta": delta,
            # Stock change the flow does not explain: lanes dated on a day their merge
            # landed later, conflict resolutions, parallel-lane replay clamping.
            "unexplained": None if delta is None else delta - (filed - closed - removed) - fold_adj}


def _activity_from_timeline(days: int = _ACT_WINDOW_DAYS) -> dict:
    """Per-day + rolled-up flow from ``daily_flow`` in the timeline artifact.

    build_handoff_timeline.py is the ONE counter; the hub only rolls its days up, and
    runs no git here, so a slow host cannot blank the panel under ``_board_lock``.
    An absent or unreadable artifact yields ``available: False`` with the reason.
    """
    present, data, err = _read_json_object(TIMELINE_PATH, "timeline artifact")
    if data is None:
        return _flow_unavailable(err or "timeline artifact not generated yet", days)
    rows = data.get("daily_flow")
    if not isinstance(rows, list) or not rows or not all(
            isinstance(r, dict) and "closed" in r and "open_stock" in r for r in rows):
        return _flow_unavailable(
            "timeline artifact has no per-day flow in the current format; "
            "the next build_handoff_timeline.py run writes it", days)
    today = datetime.now().date()
    rows = [r for r in rows if r["date"] <= today.isoformat()]
    if not rows:
        return _flow_unavailable("timeline artifact has no rows up to today", days)

    def window(n: int) -> tuple[list[dict], str]:
        start = (today - timedelta(days=n - 1)).isoformat()
        return [r for r in rows if r["date"] >= start], start

    rollups = {}
    for n in _ACT_ROLLUPS:
        sel, start = window(n)
        rollups[f"{n}d"] = _flow_rollup(rows, sel, n, start)
    sel, start = window(days)
    per_day = [{"date": r["date"], "commits": r.get("commits", 0),
                "boxes_checked": r["closed"], "boxes_added": r["filed"],
                "removed": r.get("removed", 0), "moved": r.get("moved", 0),
                "net": r["net"], "open_stock": r["open_stock"],
                "handoffs_touched": len(r.get("touched") or ())}
               for r in reversed(sel)]
    markers = [m for m in data.get("refactor_markers") or []
               if isinstance(m, dict) and m.get("date", "") >= start]
    return {"available": True, "window_days": days, "today": today.isoformat(),
            "per_day": per_day, "rollups": rollups, "refactor_markers": markers,
            "as_of": data.get("generated_at"), "commit": data.get("last_sha")}


def _activity_today_from(window: dict) -> dict:
    """Today's counters, read from the same rows as the window so the two cannot differ."""
    out = dict(_ACT_EMPTY, available=bool(window.get("available")),
               as_of=window.get("as_of"))
    if not window.get("available"):
        out["unavailable_reason"] = window.get("unavailable_reason")
        return out
    for row in window.get("per_day") or []:
        if row["date"] == window["today"]:
            out.update(commits=row["commits"], handoffs_touched=row["handoffs_touched"],
                       boxes_checked=row["boxes_checked"], boxes_added=row["boxes_added"],
                       moved=row["moved"])
            break
    return out


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
            window = _activity_from_timeline()
            _board_cache["activity_window"] = window
            _board_cache["activity_today"] = _activity_today_from(window)
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
    # The served checkout's identity travels with the board, so the page can name the
    # commit it is showing and how far behind origin/main that commit is.
    payload["_freshness"]["view"] = _view_state()
    return payload


VIEW_STATUS_PATH = REPO / ".git" / "epyc-view-refresh.json"
_VIEW_TTL_S = 30.0
_view_cache: dict | None = None
_view_cache_ts = 0.0
_view_lock = threading.Lock()


def _git_out(*args: str) -> str | None:
    """One cheap git query with a short timeout; ``None`` on any failure."""
    try:
        proc = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                              timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _view_state(*, force: bool = False) -> dict:
    """Served HEAD, its distance to origin/main, and the refresher's last report.

    ``behind`` compares against the local origin/main ref, which only moves when a fetch
    succeeds, so it reads 0 over a dead fetch. ``refresh`` is what catches that.
    """
    global _view_cache, _view_cache_ts
    with _view_lock:
        now = time.time()
        if not force and _view_cache is not None and (now - _view_cache_ts) < _VIEW_TTL_S:
            return dict(_view_cache)
        head = _git_out("rev-parse", "HEAD")
        origin = _git_out("rev-parse", "origin/main")
        behind = _git_out("rev-list", "--count", "HEAD..origin/main")
        committed = _git_out("log", "-1", "--format=%ct", "HEAD")
        # In a linked worktree ``.git`` is a file, so "no report" is the path not being one.
        present, status, err = ((False, None, None) if not VIEW_STATUS_PATH.is_file() else
                                _read_json_object(VIEW_STATUS_PATH, "hub view refresh status"))
        state = {
            "head": head, "origin_main": origin,
            "behind": int(behind) if behind and behind.isdigit() else None,
            "head_committed_at": int(committed) if committed and committed.isdigit() else None,
            "refresh": status, "refresh_present": present, "refresh_error": err,
        }
        _view_cache, _view_cache_ts = state, now
        return dict(state)


def _hub_view_observation(state: dict) -> panels.Observation:
    if state.get("refresh_error"):
        return panels.Observation(artifact_present=True, detail=state["refresh_error"])
    status = state.get("refresh")
    if status is None:
        return panels.Observation(
            artifact_present=False,
            detail="no refresh report in this checkout (not a view, or the supervisor's "
                   "pinned refresh_hub_view.sh predates the report)")
    return panels.Observation(
        artifact_present=True,
        timestamp=_parse_semantic_timestamp(status.get("attempted_at")),
        source="attempted_at", populated=True, detail=status.get("detail"))


def hub_view_payload() -> dict:
    """``/api/hub_view`` -- which commit the hub serves and whether its refresh works."""
    state = _view_state()
    out = dict(state)
    env = _panel_envelope("hub_view", _hub_view_observation(state))
    status = state.get("refresh")
    errors = []
    if state.get("refresh_error"):
        errors.append(state["refresh_error"])
    elif isinstance(status, dict) and status.get("ok") is False:
        errors.append(f"hub view refresh failed at {status.get('stage')}: "
                      f"{status.get('detail')} (served head {str(state.get('head'))[:12]})")
    if errors:
        env["data_health"], env["data_errors"] = "degraded", errors
    else:
        env["data_health"] = "ok"
    out["_freshness"] = env
    return out


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


def _folded_redirect(handoff_id: str) -> tuple[str, str | None] | None:
    """``(active/<target-stem>, track)`` for a ``state/stem`` id whose file was folded."""
    parts = (handoff_id or "").split("/")
    if len(parts) != 2 or parts[0] not in handoff_parser.STATES or not parts[1]:
        return None
    fmap = handoff_parser.load_folded_map(HANDOFF_DIR)
    base = parts[1] + ".md"
    if base not in fmap["files"]:
        return None
    target = handoff_parser.resolve_folded_file(base, fmap)
    if not isinstance(target, str) or not target.endswith(".md") or target == base:
        return None
    return f"active/{target[:-3]}", fmap["files"][base].get("track")


def detail_payload(handoff_id: str) -> tuple[int, dict]:
    """Return ``(http_status, payload)`` for one handoff's detail view.

    A retired id (its file folded into another, D5 ``.folded.json``) resolves to the
    fold target's card, carrying ``redirected_from`` and the target ``## Track:`` anchor.
    """
    path = _validate_id(handoff_id or "")
    redirected_from = anchor = None
    if path is None:
        hop = _folded_redirect(handoff_id or "")
        if hop is not None and _validate_id(hop[0]) is not None:
            redirected_from, (handoff_id, anchor) = handoff_id, hop
            path = _validate_id(handoff_id)
    if path is None:
        return 404, {"error": "handoff not found", "id": handoff_id}
    state = handoff_id.split("/")[0]
    card = handoff_parser.parse_file(state, path, detail=True)
    if redirected_from:
        card["redirected_from"] = redirected_from
        card["anchor"] = anchor
    return 200, card


_TIMELINE_ABSENT = {"series": None, "tasks_weekly": None, "handoffs_weekly": None,
                    "daily_flow": None, "generated_at": None}


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
    # A row whose spec_ref names a folded handoff keeps its text; the resolved target
    # rides alongside so the badge never dangles (D5 ``.folded.json``).
    fmap = handoff_parser.load_folded_map(HANDOFF_DIR)
    for row in rows:
        ref = row.get("spec_ref")
        if isinstance(ref, str) and ref.startswith("handoffs/"):
            p, sep, frag = ref.partition("#")
            resolved = handoff_parser.resolve_folded_file(p, fmap)
            if resolved != p:
                row["spec_ref_resolved"] = resolved + sep + frag

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


def diagnostic_overrides_payload() -> dict:
    """Current diagnostic expiry problems; reading this endpoint never sends mail."""
    from scripts.coordination.diagnostic_override_expiry import snapshot

    settings = _read_bus_config().get("diagnostic_overrides")
    record_dir = settings.get("record_dir") if isinstance(settings, dict) else None
    if not isinstance(record_dir, str) or not record_dir.strip():
        data = {"status": "degraded", "expired": [],
                "errors": ["diagnostic override monitor has no configured record directory"]}
    else:
        data = snapshot(Path(record_dir))
    env = _panel_envelope("diagnostic_overrides", panels.live(
        populated=bool(data["expired"] or data["errors"]), source=record_dir or "unconfigured"))
    # The records can be freshly read AND expired. Never falsify their age to
    # carry a semantic error through the global freshness fold.
    env["data_health"] = data["status"]
    env["data_errors"] = [*data["errors"], *[
        f"{row['component']} override expired; owner={row.get('owner')!r}; "
        f"restore with `{row['restore_command']}`" for row in data["expired"]]]
    return {**data, "_freshness": env}


def diagnostic_overrides_health() -> tuple[int, dict]:
    data = diagnostic_overrides_payload()
    return (200 if data["status"] == "ok" else 503), data


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


def _read_gpu_window_status() -> tuple:
    """Read the G1 executor-status file → ``(artifact_present, data)``."""
    present, data, err = _read_json_object(GPU_WINDOW_STATUS_JSON, "G1 executor status")
    if data is not None:
        return True, data
    shell = {"executor": None, "path": str(GPU_WINDOW_STATUS_JSON)}
    if err is None:
        return False, {**shell, "error": "no executor status file — the G1 watchdog "
                                         "cron is not installed or has never run"}
    return present, {**shell, "error": err, READER_ERROR_KEY: err}


def _gpu_window_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    """Date the executor status by the producer's own tick time, never file mtime.

    ``generated_at_epoch`` is primary (what the orchestrator's own panel reads);
    the ISO ``generated_at`` is the fallback. No watermark: the watchdog is a
    heartbeat, and an unchanged window state on consecutive ticks is the normal case.
    """
    evidence = str(GPU_WINDOW_STATUS_JSON)
    if data.get(READER_ERROR_KEY):
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY], evidence=evidence)
    ts, src = None, None
    epoch = data.get("generated_at_epoch")
    if isinstance(epoch, (int, float)) and not isinstance(epoch, bool):
        ts, src = float(epoch), "generated_at_epoch"
    else:
        ts = _parse_semantic_timestamp(data.get("generated_at"))
        src = "generated_at" if ts is not None else None
    return panels.Observation(
        artifact_present=artifact_present, timestamp=ts, source=src,
        populated=None if not artifact_present else bool(data.get("holder")),
        detail=data.get("error"), evidence=evidence)


def gpu_window_payload() -> dict:
    """The executor-status file + its envelope. Freshness only — the window
    verdict (ok / window_open / alarm) and its data probe are the orchestrator's
    (``:8000/dashboard/api/gpu_window[/health]``)."""
    present, data = _read_gpu_window_status()
    data["_freshness"] = _panel_envelope(
        "gpu_window", _gpu_window_observation(data, artifact_present=present))
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



# --------------------------------------------------------------------------- #
# JEV-5 phase A: typed loop specs  (/loop-spec)
# --------------------------------------------------------------------------- #
def loop_spec_payload() -> dict:
    """Every ``epyc.loop_spec.v1`` spec, validated, with a Mermaid diagram per machine."""
    specs, problems = loop_spec.read_specs()
    valid = [s for s in specs if not s.get("_errors")]
    revised = [_parse_semantic_timestamp(s.get("spec_revised")) for s in valid]
    revised = [t for t in revised if t is not None]
    if not specs and not problems:
        obs = panels.absent(panels.source("loop_spec"),
                            f"no *.loop.json under {loop_spec.SPEC_DIR}")
    elif problems and not valid:
        obs = panels.Observation(artifact_present=True, timestamp=None, source=None,
                                 populated=None, detail="; ".join(p["error"] for p in problems)[:500])
    else:
        obs = panels.Observation(artifact_present=True, timestamp=min(revised) if revised else None,
                                 source="spec_revised", populated=bool(valid),
                                 detail=("; ".join(p["path"] + ": " + p["error"] for p in problems)[:500]
                                         or None))
    return {"schema": "epyc.loop_spec.payload.v1", "specs": specs, "problems": problems,
            "schema_path": str((loop_spec.SPEC_DIR / "loop-spec.schema.json").relative_to(REPO)),
            "_freshness": _panel_envelope("loop_spec", obs)}


def _subject_health(panel: str, data: dict) -> tuple[int, dict]:
    env = data.get("_freshness") or {}
    verdict, reasons = panels.panel_verdict(env)
    ok = verdict == "ok"
    return (200 if ok else 503), {"panel": panel, "status": verdict, "reasons": reasons,
                                  "freshness": env, "global_health": "/api/health"}


def loop_spec_health() -> tuple[int, dict]:
    """``/api/loop_spec/health`` — is the diagram still a valid, current spec?"""
    return _subject_health("loop_spec", loop_spec_payload())


# --------------------------------------------------------------------------- #
# Pipeline page: compute loop + session loop, who is in which step  (/pipeline)
# --------------------------------------------------------------------------- #
def pipeline_payload() -> dict:
    """Read-only fold over the dispatcher registry, turn reports, grants and keeper log."""
    graph = graph_payload()      # the EXISTING index graph (/api/handoff_graph); no second graph is built
    data = pipeline_status.build_payload(graph=graph)
    if not data.get("present"):
        obs = panels.absent(panels.source("pipeline"), data.get("error", "registry unreadable"))
    else:
        obs = panels.Observation(
            artifact_present=True,
            timestamp=_parse_semantic_timestamp(data.get("dispatcher_last_pass")),
            source="dispatcher.last_pass", populated=bool(data.get("sessions")),
            detail=None)
    data["_freshness"] = _panel_envelope("pipeline", obs)
    return data


def pipeline_health() -> tuple[int, dict]:
    """``/api/pipeline/health`` - is the pipeline view still true (dispatcher passing)?"""
    return _subject_health("pipeline", pipeline_payload())


# --------------------------------------------------------------------------- #
# KT-3: read-only claim browser  (/knowledge)
# --------------------------------------------------------------------------- #
def knowledge_payload() -> dict:
    """Summary + compact claim index over the canonical vidya ledger (read-only)."""
    idx, err, path = knowledge.index()
    if idx is None:
        detail = err or f"no belief ledger at {path}"
        obs = (panels.Observation(artifact_present=True, timestamp=None, source=None,
                                  populated=None, detail=detail, evidence=str(path))
               if err else panels.Observation(artifact_present=False, detail=detail, evidence=str(path)))
        return {"ledger": str(path), "error": detail, "claims": None, "counts": None,
                "_freshness": _panel_envelope("knowledge", obs)}
    obs = panels.Observation(
        artifact_present=True, timestamp=_parse_semantic_timestamp(idx["last_created_at"]),
        source="pubinfo.created_at", populated=bool(idx["rows"]), evidence=str(path),
        watermark=str(idx["last_seq"]),
        detail=(f"{idx['malformed_lines']} malformed ledger line(s) skipped"
                if idx["malformed_lines"] else None))
    return {"ledger": str(path), "counts": idx["counts"], "n_claims": len(idx["rows"]),
            "last_seq": idx["last_seq"], "last_created_at": idx["last_created_at"],
            "claims": idx["rows"], "_freshness": _panel_envelope("knowledge", obs)}


def knowledge_health() -> tuple[int, dict]:
    """``/api/knowledge/health`` — is the browser showing a current ledger?"""
    data = knowledge_payload()
    data = {"_freshness": data["_freshness"]}
    return _subject_health("knowledge", data)


def knowledge_claim_payload(claim_id: str) -> tuple[int, dict]:
    """``(status, chain)`` for one claim: claim -> evidence -> run -> commit."""
    idx, err, path = knowledge.index()
    if idx is None:
        return 404, {"error": err or f"no belief ledger at {path}", "id": claim_id}
    detail = knowledge.claim_detail(idx, claim_id or "")
    if detail is None:
        return 404, {"error": "claim not found", "id": claim_id}
    return 200, detail

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


def amd_ai_lab_asset(name: str) -> bytes:
    """Read one allowlisted AMD AI Lab static asset.

    The hub deliberately has no generic file server. These files are an explicit
    publication snapshot copied from the separate ``epyc-web`` repository.
    """
    return (AMD_AI_LAB_DIR / name).read_bytes()


def amd_ai_lab_styles() -> bytes:
    return amd_ai_lab_asset("styles.css")


def amd_ai_lab_postbios_styles() -> bytes:
    return amd_ai_lab_asset("postbios.css")


def amd_ai_lab_script() -> bytes:
    return amd_ai_lab_asset("app.js")


def amd_ai_lab_recipe() -> bytes:
    return amd_ai_lab_asset("data/recipe.json")


def amd_ai_lab_catalog() -> bytes:
    return amd_ai_lab_asset("data/catalog.json")


def panel_envelopes() -> dict:
    """Every registered panel's freshness envelope, keyed by panel id.

    TOTAL over ``panels.PANELS`` by construction: the loop is over the REGISTRY,
    so a panel that gains a registry entry without a reader here raises
    ``KeyError`` at request time instead of silently dropping out of the fold —
    and ``tests/test_dashboard_panels.py`` catches it before that happens.
    """
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
        "hub_view": lambda: hub_view_payload()["_freshness"],
        "handoff_detail": lambda: panels.live(),
        "health": lambda: panels.live(),
        "transport_probe": lambda: panels.live(),
        "timeline": lambda: _timeline_observation(
            timeline_data, artifact_present=timeline_present),
        "handoff_graph": lambda: _graph_observation(
            graph_data, artifact_present=graph_present),
        "outcome": lambda: _outcome_observation(
            outcome_data, artifact_present=outcome_present),
        "benchmark_artifacts": lambda: _benchmark_observation(
            bench_data, artifact_present=bench_present),
        "gpu_window": lambda: gpu_window_payload()["_freshness"],
        "queue": lambda: queue_payload()["_freshness"],
        "bus": lambda: bus_payload()["_freshness"],
        "diagnostic_overrides": lambda: diagnostic_overrides_payload()["_freshness"],
        # Same rule as board/queue/bus: the payload already built its envelope
        # (and holds the TTL cache the probes live in), so reuse it rather than
        # letting the fold compute a second answer for one panel.
        "dashboards": lambda: dashboards_payload()["_freshness"],
        "autokernel_loop": lambda: loop_status.snapshot()[1],
        "kernel_progression": lambda: kernel_progression.snapshot()[1],
        "loop_spec": lambda: loop_spec_payload()["_freshness"],
        "pipeline": lambda: pipeline_payload()["_freshness"],
        "knowledge": lambda: knowledge_payload()["_freshness"],
        "knowledge_claim": lambda: panels.live(),
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
    call it ``ok``. The rules live in ``panels.fold``; the surviving compatibility
    aliases (``board``/``timeline``/``outcome``) are the same envelope objects as
    their entries in ``panels``. Retired kernel data is intentionally absent from
    this fold and its response.
    """
    envs = panel_envelopes()
    verdict = panels.fold(envs)
    for name in ("diagnostic_overrides", "hub_view"):
        env = envs[name]
        if env.get("data_health") != "degraded":
            continue
        entry = {"panel": name, "verdict": panels.STATUS_DEGRADED,
                 "why": "; ".join(env.get("data_errors") or []), "gates_health": True}
        verdict["attention"].append(entry)
        if verdict["status"] != panels.STATUS_DEGRADED:
            verdict.update(status=panels.STATUS_DEGRADED, status_set_by=entry, worst=entry)
    return {
        "status": verdict["status"],
        # WHICH panel produced ``status``. ``worst`` is the worst by severity
        # score and need not be that panel. Keep the status setter and the worst
        # panel separate so a badge never pairs the colour of one with the
        # sentence of the other.
        "status_set_by": verdict["status_set_by"],
        "worst": verdict["worst"],
        "attention": verdict["attention"],
        "absent": verdict["absent"],
        "panels": envs,
        # Back-compat aliases — same objects, old names.
        "board": envs["board"],
        "timeline": envs["timeline"],
        "outcome": envs["outcome"],
        "now": time.time(),
    }


def loop_payload() -> dict:
    """``/api/loop`` — the rebuilt loop's status plus its panel envelope.

    ``loop`` is ``null``, never ``{}``, when nothing readable was found: ``[]``
    says "the producer reported and there is nothing", ``null`` says "no producer
    reported", and the old shell said ``[]`` for both — which is how a dead loop
    rendered as a clean, empty, trusted page (see ``_read_kernel_contract``).

    TWO PRODUCERS ON ONE PAGE (2026-08-30), AND NEITHER DATES THE OTHER.
    ``/loop`` is now the single Kernel-R&D surface: ``/kernel`` was retired to a
    redirect because every producer behind it was dead (the ``v37`` controller,
    ``kernel_dashboard.json`` at 16.8 d) or had a data horizon that had stopped
    advancing (``kernel_progression.json``: the FILE was rewritten 2.8 d ago, its
    ``observed_through`` is 16.7 d old — two different facts that must never be
    folded into one number). The one live producer that page carried is the
    operator-gated bundle, so it moves here.

    ``operator_gates`` therefore rides beside ``loop`` **with its own four-valued
    envelope**, produced by the existing ``_read_operator_gate_bundle`` — one
    reader, not a second. The two envelopes are deliberately NOT merged and
    ``_freshness`` still dates ONLY the loop: a fresh loop is not evidence that
    the gate bundle is current, and a stale bundle is not an outage of the loop.
    Merging them is precisely how one producer's silence gets certified by
    another's liveness.

    ``/api/loop/health`` folds the loop and operator-gate subject verdicts as
    independent constituents. This route does not merge their envelopes: each
    producer's evidence and age remain attached to its own result.
    """
    payload, observation = loop_status.snapshot()
    payload["_freshness"] = _panel_envelope("autokernel_loop", observation)
    payload["operator_gates"] = _read_operator_gate_bundle()
    payload["progression"] = progression_payload()
    payload["now"] = time.time()
    return payload


def progression_payload() -> dict:
    return kernel_progression.snapshot()[0]


def progression_health() -> tuple[int, dict]:
    return kernel_progression.health()


def _operator_gate_health_status(bundle: dict) -> dict:
    """Map the bundle's five-valued subject verdict to the loop probe's status.

    The bundle's age is informational, and individual gate outcomes (including
    an intentional HOLD) describe measurement authority rather than producer
    health. Only its existing subject/freshness verdict participates here.
    """
    freshness = bundle.get("freshness") if isinstance(bundle, dict) else None
    freshness = freshness if isinstance(freshness, dict) else {}
    source_verdict = freshness.get("state")
    status_by_verdict = {
        loop_status.OPGATE_RELEVANT: panels.STATUS_OK,
        loop_status.OPGATE_SUPERSEDED: panels.STATUS_DEGRADED,
        loop_status.OPGATE_UNVERIFIABLE: panels.STATUS_DEGRADED,
        "absent": panels.STATUS_ABSENT,
        "malformed": panels.STATUS_DEGRADED,
    }
    status = status_by_verdict.get(source_verdict, panels.STATUS_DEGRADED)
    return {
        "status": status,
        "source_verdict": source_verdict,
        "why": freshness.get("detail") or freshness.get("reason") or
               f"operator-gate bundle verdict is {source_verdict!r}",
        "age_s": freshness.get("age_s"),
        "evidence": bundle.get("evidence") if isinstance(bundle, dict) else None,
    }


def loop_data_health() -> tuple[int, dict]:
    """``/api/loop/health`` — *is what the loop page shows still true?*

    The ``/api/health``-KIND of probe, not the ``/health`` kind. ``/health`` is
    transport-only and stays green over a dead producer, which is why the
    supervisor may poll it and must never poll this one.

    Non-recursive by construction: it folds the loop and operator-gate verdicts
    directly, without dragging in the global fold (whose dashboard-directory
    panel points back at this route). Their source envelopes remain independent.

    Three-valued, and the third value is load-bearing:

      * ``ok``       — a fresh report inside the loop's own declared envelope.
      * ``absent``   — nobody has ever published here. Not ``stale``: a producer
                       that never ran and a producer that stopped are different
                       facts about different subsystems.
      * ``degraded`` — stale, malformed, watchdog-alarmed, or a loop that
                       DECLARED ``state=failed``.

    ``failed`` is raised explicitly rather than left to freshness. A loop that
    crashed one minute ago is perfectly fresh and perfectly broken, and a probe
    that answers "current" to "is this still true?" over a dead loop is the
    green-over-a-corpse reading this surface exists to prevent.

    HTTP 200 only for ``ok``; ``absent`` and ``degraded`` both answer 503 for
    simple health clients, with the three-valued verdict preserved in the body
    (same convention as ``kernel_data_health``).
    """
    payload, observation = loop_status.snapshot()
    env = _panel_envelope("autokernel_loop", observation)
    verdict = panels.fold({"autokernel_loop": env},
                          registry={"autokernel_loop": panels.source("autokernel_loop")})
    status = verdict["status"]

    def _raise(candidate: str) -> None:
        nonlocal status
        if (panels.STATUS_ORDER.index(candidate)
                > panels.STATUS_ORDER.index(status)):
            status = candidate

    # THE PANEL'S OWN VERDICT IS NOT THE GLOBAL FOLD'S.
    #
    # ``autokernel_loop`` declares ``absence_is_anomalous=False`` so a host where
    # no campaign has ever run does not redden ``/api/health`` — a cold start is
    # not an outage. But THIS route answers a narrower question about ONE panel
    # ("is what the loop page shows still true?"), and there the answer to
    # "nobody ever published" is ``absent``, never ``ok``. Reading the global
    # fold's leniency as this panel's verdict is exactly the true-about-a-wider-
    # set error that lets a surface report green over a producer nobody can find.
    body = payload.get("loop") or {}
    legacy_state = body.get("state")
    campaign = payload.get("campaign") or {"configured": False}
    selected_campaign = bool(campaign.get("configured"))
    serial = payload.get("serial")
    selected_serial = isinstance(serial, dict)
    declared_failure = None
    if not selected_campaign:
        if payload["freshness_state"] == loop_status.STATE_ABSENT:
            _raise(panels.STATUS_ABSENT)
        elif payload["freshness_state"] == loop_status.STATE_MALFORMED:
            _raise(panels.STATUS_DEGRADED)
        elif (payload["freshness_state"] == loop_status.STATE_STALE
              and legacy_state != "complete"):
            _raise(panels.STATUS_DEGRADED)
        if legacy_state == "failed":
            _raise(panels.STATUS_DEGRADED)
            declared_failure = (
                f"the {'serial router' if selected_serial else 'legacy loop'} DECLARED "
                "state=failed; it remains visible history but is the selected producer "
                "only when no unified campaign is configured.")
        if selected_serial and (serial.get("reader_error") is not None
                                or serial.get("state") in {"malformed", "failed", "all_failed"}):
            _raise(panels.STATUS_DEGRADED)
            declared_failure = serial.get("reader_error") or (
                f"the serial router DECLARED state={serial.get('state')}")
    campaign_attention = None
    if selected_campaign:
        campaign_state = campaign.get("state")
        campaign_body = campaign.get("campaign") or {}
        if campaign_state == "absent":
            _raise(panels.STATUS_ABSENT)
            campaign_attention = "configured unified campaign snapshot is absent"
        elif campaign_state in {"malformed", "degraded"}:
            _raise(panels.STATUS_DEGRADED)
            campaign_attention = campaign.get("error") or (
                "unified campaign producer identity/health is degraded")
        elif campaign_state == "history" and campaign_body.get("observed_state") != "drained":
            _raise(panels.STATUS_DEGRADED)
            campaign_attention = (
                "unified campaign is historical without a terminal drained state")
    campaign_body = campaign.get("campaign") or {}
    if selected_campaign:
        selected_state = campaign.get("state")
        selected_age = ((campaign.get("clocks") or {}).get(
            "producer_heartbeat_at") or {}).get("age_s")
        selected_evidence = campaign.get("evidence")
        selected_error = campaign.get("error") or campaign_attention
        selected_loop_state = campaign_body.get("observed_state")
        selected_stale_after = campaign_status.HEARTBEAT_STALE_AFTER_S
    elif selected_serial:
        selected_state = payload["freshness_state"]
        selected_age = payload["age_s"]
        selected_evidence = payload["evidence"]
        selected_error = serial.get("reader_error") or payload["reader_error"]
        selected_loop_state = serial.get("state")
        selected_stale_after = payload["stale_after_s"]
    else:
        selected_state = payload["freshness_state"]
        selected_age = payload["age_s"]
        selected_evidence = payload["evidence"]
        selected_error = payload["reader_error"]
        selected_loop_state = legacy_state
        selected_stale_after = payload["stale_after_s"]
    operator_gates = _read_operator_gate_bundle()
    operator_gate_health = _operator_gate_health_status(operator_gates)
    loop_health_status = status
    health_components = {
        "autokernel_loop": {
            "status": loop_health_status,
            "source_verdict": selected_state,
            "loop_state": selected_loop_state,
            "why": (verdict.get("worst") or {}).get("why") or
                   declared_failure or campaign_attention or
                   "selected loop producer is reporting",
        },
        "operator_gates": operator_gate_health,
    }
    worst_component = max(
        health_components.items(),
        key=lambda item: panels.STATUS_ORDER.index(item[1]["status"]),
    )[0]
    status = health_components[worst_component]["status"]
    if worst_component == "operator_gates":
        status_set_by = {
            "panel": "operator_gates",
            "verdict": operator_gate_health["status"],
            "why": operator_gate_health["why"],
            "gates_health": True,
        }
        worst = {
            "panel": "operator_gates",
            "producer": "operator-gated serving evidence",
            "verdict": operator_gate_health["status"],
            "source_verdict": operator_gate_health["source_verdict"],
            "why": operator_gate_health["why"],
            "gates_health": True,
        }
    else:
        status_set_by = verdict["status_set_by"]
        worst = verdict["worst"]
    attention = list(verdict["attention"])
    if operator_gate_health["status"] != panels.STATUS_OK:
        attention.append({
            "panel": "operator_gates",
            "verdict": operator_gate_health["status"],
            "why": operator_gate_health["why"],
            "gates_health": True,
        })
    absent = list(verdict["absent"])
    if operator_gate_health["status"] == panels.STATUS_ABSENT:
        absent.append({
            "panel": "operator_gates",
            "producer": "operator-gated serving evidence",
            "evidence": operator_gate_health["evidence"],
            "absence_means": operator_gates.get("absence_means"),
            "anomalous": True,
        })

    out = {
        "status": status,
        "probe": "panel-data",
        "panel": "autokernel_loop",
        "data_route": panels.source("autokernel_loop").route,
        "transport_health": "/health",
        "global_health": "/api/health",
        "status_set_by": status_set_by,
        "worst": worst,
        "attention": attention,
        "absent": absent,
        "constituents": health_components,
        "operator_gates": operator_gates,
        # The producer contract's own four-valued verdict, beside the hub's fold.
        # They answer different questions — "is this report current?" versus "is
        # this panel healthy?" — and printing one under the other's name is how
        # an operator reads the wrong offender.
        "selected_producer": ("campaign" if selected_campaign else
                              "serial_router" if selected_serial else "legacy_loop"),
        "freshness_state": selected_state,
        "age_s": selected_age,
        "stale_after_s": selected_stale_after,
        "evidence": selected_evidence,
        "reader_error": selected_error,
        "loop_state": selected_loop_state,
        "declared_failure": declared_failure,
        "campaign_state": campaign.get("state"),
        "serial_state": serial.get("state") if selected_serial else None,
        "campaign_attention": campaign_attention,
        "legacy_history": {"freshness_state": payload["freshness_state"],
                           "state": legacy_state, "evidence": payload["evidence"]},
        "freshness": env,
    }
    return (200 if status == panels.STATUS_OK else 503), out


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


HANDOFF_SESSIONS_DIR = os.environ.get("EPYC_HANDOFF_SESSIONS_DIR", "/mnt/raid0/llm/tmp/compute-flags/handoff-sessions")


def handoff_step_counts(sessions_dir: str = HANDOFF_SESSIONS_DIR) -> dict:
    """{handoff basename: landed turns since that handoff's last tick} from each session's steps.jsonl (written by
    wrapup.py, ws58). A session with no ledger yet counts its report.json: one wrapped turn without ticks = 1."""
    try:
        with open(sessions_dir.rstrip("/") + ".json", encoding="utf-8") as fh:
            reg = json.load(fh).get("sessions", {})
    except (OSError, ValueError, AttributeError):
        return {}
    out = {}
    for slug, e in (reg.items() if isinstance(reg, dict) else ()):
        if not isinstance(e, dict) or not e.get("handoff"):
            continue
        d, n = os.path.join(sessions_dir, slug), None
        try:
            with open(os.path.join(d, "steps.jsonl"), encoding="utf-8") as fh:
                n = 0
                for line in fh:
                    try:
                        n = 0 if int(json.loads(line).get("ticks") or 0) > 0 else n + 1
                    except (ValueError, TypeError, AttributeError):
                        continue
        except OSError:
            try:
                with open(os.path.join(d, "report.json"), encoding="utf-8") as fh:
                    r = json.load(fh)
                n = 1 if r.get("wrapped") and not r.get("ticks") else 0
            except (OSError, ValueError, AttributeError):
                continue
        out[os.path.basename(str(e["handoff"]))] = n
    return out


def graph_payload() -> dict:
    """Read the index graph artifact, tolerating absence/corruption."""
    present, data = _read_graph_contract()
    steps = handoff_step_counts()
    # The D5 redirect map rides with the graph so a bookmarked retired row id or
    # folded file id resolves client-side (handoffs.html ``?id=``).
    data["folded"] = handoff_parser.load_folded_map(HANDOFF_DIR)
    for node in data.get("nodes") or ():
        if isinstance(node, dict) and node.get("handoff") in steps:
            node["steps_since_tick"] = steps[node["handoff"]]
    data["_freshness"] = _panel_envelope(
        "handoff_graph", _graph_observation(data, artifact_present=present))
    return data


HTML_ROUTES = {
    "/": STATIC_HTML,
    "/machine": MACHINE_HTML,
    "/autopilot": AUTOPILOT_HTML,
    "/cockpit": COCKPIT_HTML,
    "/gpu-window": GPU_WINDOW_HTML,
    "/loop": LOOP_HTML,
    "/bus": BUS_HTML,
    "/benchmarks": BENCHMARKS_HTML,
    "/loop-spec": LOOP_SPEC_HTML,
    "/knowledge": KNOWLEDGE_HTML,
    "/amd-ai-lab": AMD_AI_LAB_HTML,
}


REDIRECT_ROUTES = {
    "/kernel": "/loop",
}


ASSET_ROUTES = {
    "/nav.js": ("application/javascript; charset=utf-8", nav_asset),
    "/amd-ai-lab/styles.css": ("text/css; charset=utf-8", amd_ai_lab_styles),
    "/amd-ai-lab/postbios.css": ("text/css; charset=utf-8", amd_ai_lab_postbios_styles),
    "/amd-ai-lab/app.js": ("application/javascript; charset=utf-8", amd_ai_lab_script),
    "/amd-ai-lab/data/recipe.json": ("application/json; charset=utf-8", amd_ai_lab_recipe),
    "/amd-ai-lab/data/catalog.json": ("application/json; charset=utf-8", amd_ai_lab_catalog),
}


API_ROUTES = {
    "/api/handoff_board": board_payload,
    "/api/handoff_timeline": timeline_payload,
    "/api/hub_view": hub_view_payload,
    "/api/handoff_graph": graph_payload,
    "/api/loop": loop_payload,
    "/api/loop/progression": progression_payload,
    "/api/bus": bus_payload,
    "/api/diagnostic-overrides": diagnostic_overrides_payload,
    "/api/queue": queue_payload,
    "/api/outcome": outcome_payload,
    "/api/gpu_window": gpu_window_payload,
    "/api/benchmark_artifacts": benchmark_artifacts_payload,
    "/api/loop_spec": loop_spec_payload,
    "/api/pipeline": pipeline_payload,
    "/api/knowledge": knowledge_payload,
    "/api/dashboards": dashboards_payload,
    "/api/health": health_payload,
}


API_ROUTES_WITH_STATUS = {
    "/api/handoff_detail": detail_payload,
    "/api/knowledge_claim": knowledge_claim_payload,
}


PANEL_HEALTH_ROUTES = {
    "/api/loop/progression/health": progression_health,
    "/api/diagnostic-overrides/health": diagnostic_overrides_health,
    "/api/loop/health": loop_data_health,
    "/api/loop_spec/health": loop_spec_health,
    "/api/pipeline/health": pipeline_health,
    "/api/knowledge/health": knowledge_health,
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

    def _send_redirect(self, location: str) -> None:
        """Answer a retired page with a permanent redirect and a plain-text body.

        The body is not decoration: a ``curl`` of a retired route otherwise
        returns nothing at all, which reads as an empty page rather than as a
        move. It is sent for GET and withheld for HEAD, like every other
        response here.
        """
        body = (f"moved permanently to {location}\n").encode("utf-8")
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
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
            elif route in REDIRECT_ROUTES:
                self._send_redirect(REDIRECT_ROUTES[route])
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



# Declared reflection seams used by the panel registry and route audits.
DASHBOARD_REGISTRY_SCHEMA = "epyc.dashboard.registry.v1"

OPERATOR_GATE_BUNDLE_STATES = (
    loop_status.OPGATE_RELEVANT, loop_status.OPGATE_SUPERSEDED,
    loop_status.OPGATE_UNVERIFIABLE, "absent", "malformed")

_TIMELINE_WARN_S = panels.source("timeline").warn_s

_TIMELINE_STALE_S = panels.source("timeline").stale_s

_OUTCOME_WARN_S = panels.source("outcome").warn_s

_OUTCOME_STALE_S = panels.source("outcome").stale_s

PROBE_ROUTES = {
    "/health": transport_probe_payload,
}

if __name__ == "__main__":
    main()

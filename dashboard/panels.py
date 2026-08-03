#!/usr/bin/env python3
"""dashboard/panels.py — the SSOT panel->producer registry, the per-panel
freshness envelope, and the transport watchdog.

WHY THIS MODULE EXISTS
----------------------
Quoting the AK6 rider in ``handoffs/active/autokernel-research-loop.md``:

    Today's ``/kernel`` page is ABSENCE-TOLERANT OVER A MISSING DIRECTORY — it
    renders clean when its producer is dead, which is the exact shape of AutoPilot
    dying at trial 1302 and staying dead ~23 HOURS with every dashboard green.

A panel that cannot distinguish "nothing is wrong" from "nobody is reporting" is
worse than no panel, because it is trusted. Absence tolerance is still REQUIRED —
the hub must never 500 because a producer is dead — so the fix is not to make
absence fatal. It is to make absence **unrepresentable as silence**:

1. **Every panel declares its producer.** ``PANELS`` is the single source of
   truth: who writes the evidence, which artifact carries it, which SEMANTIC
   timestamp dates it, how long silence may last, and — mandatory, enforced in
   ``PanelSource.__post_init__`` — what its absence MEANS. A panel with no
   registered source is a panel nobody can tell is dead.
2. **The registry is checked against the CODE, not against a list.** A
   hand-maintained roster that someone forgets to extend is the same defect one
   level up, so ``registry_gaps()`` enumerates the hub's payload functions and its
   route table by reflection and reports the symmetric difference in BOTH
   directions. ``tests/test_dashboard_panels.py`` fails on any gap.
3. **Absent and empty are different values on the wire.** ``envelope()`` emits
   ``artifact_present`` (did the producer leave anything at all), ``reporting``
   (observed / silent / absent) and ``content`` (populated / empty / unknown) as
   three independent fields. "the producer reported nothing" is
   ``reporting=observed, content=empty``; "no producer reported" is
   ``reporting=absent, content=unknown``. Nothing can render one as the other.
4. **A watchdog detects STOPPING, not emptiness.** See ``WATCHDOG_*`` below.

VOCABULARY. ``staleness_class`` keeps the four values this repo already uses
(``dashboard/freshness.py``, ``server._kernel_contract_freshness``) rather than a
third idiom: ``fresh`` / ``aging`` / ``stale`` / ``missing``. In AK6's spelling
``aging`` IS "warn" and ``missing`` IS "absent"; the words differ, the states do
not, and renaming them across a live page and its tests would buy nothing.

This module is pure: no I/O, no imports outside the stdlib, no clock except an
injectable ``now``. The hub reads artifacts; this module only classifies what the
hub found.
"""
from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence

from dashboard import freshness

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #
CLASS_FRESH = freshness.CLASS_FRESH      # AK6 spelling: "fresh"
CLASS_AGING = freshness.CLASS_AGING      # AK6 spelling: "warn"
CLASS_STALE = freshness.CLASS_STALE      # AK6 spelling: "stale"
CLASS_MISSING = freshness.CLASS_MISSING  # AK6 spelling: "ABSENT"
CLASSES = freshness.CLASSES

#: Did a producer report at all, and is it still reporting?
REPORTING_OBSERVED = "observed"
REPORTING_SILENT = "silent"
REPORTING_ABSENT = "absent"
REPORTING_STATES = (REPORTING_OBSERVED, REPORTING_SILENT, REPORTING_ABSENT)

#: Did the report carry anything? Orthogonal to ``reporting`` ON PURPOSE — their
#: conflation is the scar.
CONTENT_POPULATED = "populated"
CONTENT_EMPTY = "empty"
CONTENT_UNKNOWN = "unknown"
CONTENT_STATES = (CONTENT_POPULATED, CONTENT_EMPTY, CONTENT_UNKNOWN)

#: Transport watchdog verdicts.
#:
#: ``stopped_reporting`` is the AutoPilot-at-trial-1302 detector: the artifact is
#: there, it is populated, it looks like a perfectly good panel — and its newest
#: SEMANTIC timestamp has not moved for longer than the producer's declared
#: silence budget. ``not_advancing`` is the no-op-re-export shape: reports keep
#: arriving with fresh timestamps but the producer's progress watermark
#: (campaign + controller sequence, latest trial id, last commit sha) has not
#: changed. ``idle`` is the compliant path: a producer that has DECLARED it is
#: stopped is allowed to be silent, and silence is not evidence of death.
WATCHDOG_OK = "ok"
WATCHDOG_STOPPED = "stopped_reporting"
WATCHDOG_NOT_ADVANCING = "not_advancing"
WATCHDOG_IDLE = "idle"
WATCHDOG_NEVER = "never_reported"
WATCHDOG_NO_TIMESTAMP = "no_timestamp"
WATCHDOG_UNWATCHED = "unwatched"
#: A report dated in the FUTURE. ``age = max(0, now - ts)`` clamps at zero, so a
#: producer whose clock is ahead — or whose journal carries a naive local
#: timestamp read as UTC — reads ``fresh`` forever no matter how long it has been
#: dead. Undatable-in-the-future is therefore a PRODUCER DEFECT with its own
#: verdict, never a fresh panel.
WATCHDOG_FUTURE_TIMESTAMP = "future_timestamp"
WATCHDOG_STATES = (WATCHDOG_OK, WATCHDOG_STOPPED, WATCHDOG_NOT_ADVANCING,
                   WATCHDOG_IDLE, WATCHDOG_NEVER, WATCHDOG_NO_TIMESTAMP,
                   WATCHDOG_UNWATCHED, WATCHDOG_FUTURE_TIMESTAMP)
#: The verdicts that mean "a producer that should be reporting is not".
WATCHDOG_ALARMS = frozenset({WATCHDOG_STOPPED, WATCHDOG_NOT_ADVANCING})
#: The verdicts that mean "the evidence itself is broken". Kept apart from
#: ``WATCHDOG_ALARMS`` because they must NOT set ``reporting=silent`` (nothing is
#: known about the producer), but they must still colour the fold.
WATCHDOG_DEFECTS = frozenset({WATCHDOG_FUTURE_TIMESTAMP})
#: How far ahead of ``now`` a producer-written timestamp may sit before the panel
#: is treated as undatable. Generous enough for NTP jitter between the producer's
#: host and this one, far short of anything that could hide a stopped loop.
FUTURE_SKEW_TOLERANCE_S = 300.0

#: How a panel's evidence comes into existence.
KIND_LIVE = "live"          # computed per request from the filesystem/git
KIND_DERIVED = "derived"    # computed per request from another panel's evidence
KIND_ARTIFACT = "artifact"  # a generated file tracked in THIS repo
KIND_EXPORT = "export"      # a file written by a loop in ANOTHER repo/process
KIND_FILETREE = "filetree"  # a directory many writers append to
KIND_FOLD = "fold"          # this registry, folded
#: Kinds whose evidence is produced at request time and therefore cannot be
#: stale: they have no thresholds and are never watched.
LIVE_KINDS = frozenset({KIND_LIVE, KIND_DERIVED, KIND_FOLD})
KINDS = (KIND_LIVE, KIND_DERIVED, KIND_ARTIFACT, KIND_EXPORT, KIND_FILETREE,
         KIND_FOLD)

#: Health-fold status. Three values, not two: "nobody is reporting" is neither
#: healthy nor broken, and collapsing it into ``ok`` is the failure being designed
#: out while collapsing it into ``degraded`` would make a cold host cry wolf.
STATUS_OK = "ok"
STATUS_ABSENT = "absent"
STATUS_DEGRADED = "degraded"
STATUS_ORDER = (STATUS_OK, STATUS_ABSENT, STATUS_DEGRADED)

_MINUTE = 60.0
_HOUR = 3600.0
_DAY = 86400.0

#: The widest staleness budget any panel may declare. Without a cap, "declare
#: thresholds" is satisfied by ``stale_s=100 years`` and NOTHING is ever stale —
#: a registry entry that looks compliant and monitors nothing. 30 days is the
#: widest budget any real producer here needs (the benchmark inventory).
MAX_STALE_S = 30 * _DAY


class RegistryError(ValueError):
    """A registry entry is unusable — raised at import, never at request time."""


# --------------------------------------------------------------------------- #
# The registry entry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PanelSource:
    """What one panel is, who produces it, and what its absence means.

    ``absence_means`` is MANDATORY and validated non-empty. That is the whole
    point of the registry: a panel whose absence has no declared meaning is a
    panel an operator will read as "fine", which is how a dead producer stays
    invisible for 23 hours.
    """

    panel: str
    kind: str
    payload_func: str
    producer: str
    producer_repo: str
    evidence: str
    timestamp_field: str
    absence_means: str
    route: Optional[str] = None
    warn_s: Optional[float] = None
    stale_s: Optional[float] = None
    silent_after_s: Optional[float] = None
    watched: bool = False
    gates_health: bool = False
    #: Is absence anomalous, or a legitimate cold-start state? Declared per
    #: panel because it genuinely differs: a git-hook cache is absent on a fresh
    #: checkout, while a durable export written by a running loop is not.
    absence_is_anomalous: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        for name in ("panel", "kind", "payload_func", "producer", "producer_repo",
                     "evidence", "timestamp_field", "absence_means"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise RegistryError(
                    f"PanelSource({self.panel!r}).{name}: must be a non-empty "
                    "string — an unexplained panel is an unreadable panel")
        if self.kind not in KINDS:
            raise RegistryError(
                f"PanelSource({self.panel!r}).kind: {self.kind!r} not in {KINDS}")
        live = self.kind in LIVE_KINDS
        if live:
            if self.warn_s is not None or self.stale_s is not None:
                raise RegistryError(
                    f"PanelSource({self.panel!r}): a {self.kind!r} panel is computed "
                    "per request and cannot carry staleness thresholds")
            if self.watched:
                raise RegistryError(
                    f"PanelSource({self.panel!r}): a {self.kind!r} panel has no "
                    "producer to watch — it IS the request")
        else:
            if self.warn_s is None or self.stale_s is None:
                raise RegistryError(
                    f"PanelSource({self.panel!r}): a file-backed panel must declare "
                    "warn_s and stale_s; without them nothing can read as stale")
            if self.stale_s < self.warn_s:
                raise RegistryError(
                    f"PanelSource({self.panel!r}): stale_s < warn_s")
            if self.stale_s > MAX_STALE_S:
                raise RegistryError(
                    f"PanelSource({self.panel!r}): stale_s={self.stale_s} exceeds "
                    f"MAX_STALE_S={MAX_STALE_S}. A budget wider than this monitors "
                    "nothing: the panel would satisfy 'declares thresholds' and "
                    "still never read stale, which is the absence-tolerant page "
                    "with a threshold bolted on.")
        if self.watched and self.silent_after_s is None:
            raise RegistryError(
                f"PanelSource({self.panel!r}): watched panels must declare "
                "silent_after_s — a watchdog with no silence budget never fires")
        if (self.watched and self.silent_after_s is not None
                and self.stale_s is not None and self.silent_after_s > self.stale_s):
            raise RegistryError(
                f"PanelSource({self.panel!r}): silent_after_s={self.silent_after_s} "
                f"> stale_s={self.stale_s}. The watchdog would stay quiet while the "
                "panel already reads stale, so the louder signal would arrive later "
                "than the quieter one.")
        if self.silent_after_s is not None and not self.watched:
            raise RegistryError(
                f"PanelSource({self.panel!r}): silent_after_s is set but the panel "
                "is not watched, so the budget would never be read")


def _index(sources: Sequence[PanelSource]) -> Mapping[str, PanelSource]:
    out: dict[str, PanelSource] = {}
    for src in sources:
        if src.panel in out:
            raise RegistryError(f"duplicate panel id {src.panel!r}")
        out[src.panel] = src
    return MappingProxyType(out)


# --------------------------------------------------------------------------- #
# THE REGISTRY
# --------------------------------------------------------------------------- #
# One entry per payload function the hub exposes. TOTAL, not partial: including
# ``handoff_detail`` (a per-id lookup) and ``health`` (the fold itself) means
# ``registry_gaps()`` needs no exemption list, and an exemption list is exactly
# the hand-maintained thing that goes stale.
PANELS: Mapping[str, PanelSource] = _index((
    PanelSource(
        panel="board",
        kind=KIND_LIVE,
        payload_func="board_payload",
        route="/api/handoff_board",
        producer="dashboard.server.board_payload (this hub)",
        producer_repo="epyc-root",
        evidence="handoffs/{active,blocked,completed,archived}/*.md + git status",
        timestamp_field="live-scan",
        absence_means=(
            "impossible: the board is a live directory scan performed inside the "
            "request. If it were ever absent the hub itself would be broken, and "
            "the request would 500 rather than render an empty board."),
        gates_health=True,
        notes="TTL-cached for _BOARD_TTL_S; the cache is a latency device, not a "
              "producer, so it never becomes the freshness source.",
    ),
    PanelSource(
        panel="handoff_detail",
        kind=KIND_DERIVED,
        payload_func="detail_payload",
        route="/api/handoff_detail",
        producer="dashboard.server.detail_payload (this hub)",
        producer_repo="epyc-root",
        evidence="one handoffs/<state>/<stem>.md, parsed on demand",
        timestamp_field="live-scan",
        absence_means=(
            "a 404 for one handoff id, never a blank panel: an unknown or unsafe "
            "id is refused by _validate_id and answered with an explicit error."),
        gates_health=False,
    ),
    PanelSource(
        panel="timeline",
        kind=KIND_ARTIFACT,
        payload_func="timeline_payload",
        route="/api/handoff_timeline",
        producer="scripts/dashboard/build_handoff_timeline (git post-commit hook)",
        producer_repo="epyc-root",
        evidence="data/handoff_timeline.json",
        timestamp_field="generated_at",
        absence_means=(
            "the regeneration hook has never run in this checkout (or was removed). "
            "The board does not depend on it, so the hub degrades to 'no history' "
            "rather than failing — but a timeline that STOPS advancing means the "
            "hook died and every trend on the page is frozen."),
        warn_s=6 * _HOUR,
        stale_s=2 * _DAY,
        silent_after_s=2 * _DAY,
        watched=True,
        gates_health=True,
        absence_is_anomalous=False,  # regenerable cache; absent on a fresh checkout
    ),
    PanelSource(
        panel="kernel",
        kind=KIND_EXPORT,
        payload_func="kernel_payload",
        route="/api/kernel",
        producer="autokernel.surface.dashboard_contract (AutoKernel research loop)",
        producer_repo="epyc-inference-research",
        evidence="/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json",
        timestamp_field="produced_at (v2) | runs[].ts then generated_at (v1)",
        absence_means=(
            "NOBODY IS REPORTING. The AutoKernel loop writes this contract to a "
            "durable path on every export; if the file is not there, no campaign "
            "has ever exported one — the panel is not 'quiet', it is unsourced. "
            "This is the scar the AK6 surface exists to close, so absence here is "
            "anomalous by declaration and is named in the /api/health fold."),
        warn_s=3 * _DAY,
        stale_s=14 * _DAY,
        silent_after_s=3 * _DAY,
        watched=True,
        gates_health=True,
        absence_is_anomalous=True,
        notes="produced_at is derived by the producer from the LOOP's journaled "
              "record timestamps, never from the export; a no-op re-export cannot "
              "move it. When the contract declares the controller stopped "
              "(sections.campaign.stopped), silence is expected and the watchdog "
              "reports 'idle' instead of 'stopped_reporting'.",
    ),
    PanelSource(
        panel="bus",
        kind=KIND_FILETREE,
        payload_func="bus_payload",
        route="/api/bus",
        producer="every session agent (its own heartbeat) + the coordinator daemon",
        producer_repo="epyc-root",
        evidence="coordination/session-bus/{config.yaml,heartbeats,inbox,outbox,tokens}",
        timestamp_field="heartbeats/*.json mtime (freshest)",
        absence_means=(
            "the session bus is not initialised in this checkout — no roster, so "
            "no agent can be found alive or dead. The bus tree is tracked in the "
            "repo, so its absence is a broken working tree, not a cold start."),
        warn_s=15 * _MINUTE,
        stale_s=1 * _HOUR,
        gates_health=False,
        absence_is_anomalous=True,
        notes="NOT watched: an idle fleet is legitimately silent, and the per-agent "
              "stale-heartbeat alarms inside bus_payload already own that signal. A "
              "second watchdog over the same fact would be a second source of truth.",
    ),
    PanelSource(
        panel="queue",
        kind=KIND_FILETREE,
        payload_func="queue_payload",
        route="/api/queue",
        producer="coordinator daemon (session_bus.py) — queue.jsonl appender",
        producer_repo="epyc-root",
        evidence="coordination/session-bus/queue.jsonl",
        timestamp_field="rows[].ts (newest)",
        absence_means=(
            "no work queue has ever been written: the never-block guarantee has no "
            "backlog behind it and a main that loses a lease has nothing to fall "
            "back to. Distinct from an EMPTY queue, which is a real, reported state."),
        warn_s=15 * _MINUTE,
        stale_s=1 * _HOUR,
        gates_health=False,
        absence_is_anomalous=True,
        notes="NOT watched, for the same reason as `bus`: an idle fleet dispatches "
              "no work, so an unchanging queue is the normal state and a watchdog "
              "over it would cry wolf permanently. Coordinator liveness is owned by "
              "the per-agent heartbeat alarms inside bus_payload — one signal, one "
              "owner. Its ABSENCE is still anomalous: the file is tracked in the "
              "repo, so a missing queue.jsonl is a broken tree, not an idle fleet.",
    ),
    PanelSource(
        panel="outcome",
        kind=KIND_EXPORT,
        payload_func="outcome_payload",
        route="/api/outcome",
        producer="orchestrator autopilot loop (phase_status.build_phase_health_report)",
        producer_repo="epyc-orchestrator",
        evidence="/mnt/raid0/llm/tmp/autopilot/outcome_contract.json",
        timestamp_field="generated_at",
        absence_means=(
            "no exporter writes this path yet (phase_health_report.py only prints "
            "to stdout), so absence is the EXPECTED default and the card points at "
            ":8000. Once an export exists, silence means the autopilot loop died — "
            "which is literally the trial-1302 outage — so the panel is watched even "
            "though its absence is not anomalous."),
        warn_s=6 * _HOUR,
        stale_s=2 * _DAY,
        silent_after_s=6 * _HOUR,
        watched=True,
        gates_health=False,
        absence_is_anomalous=False,
        notes="NON-gating for STALENESS and ABSENCE: no exporter writes this path "
              "yet, so its absence must not colour the fold. Its WATCHDOG ALARM "
              "does gate (see verdict_gates_status) — this is the trial-1302 "
              "panel, and 'the autopilot stopped' is precisely the fact the fold "
              "exists to publish. The compliant path for a legitimate Phase-0 "
              "stop-loss pause is a DECLARED one: the exporter sets "
              "outcome_progress.paused (or status paused/stopped/idle) and the "
              "panel reads 'idle', the same rule the AutoKernel controller obeys "
              "with sections.campaign.stopped. An exporter that goes quiet without "
              "declaring why is indistinguishable from a dead one, so the hub "
              "refuses to guess in the operator's favour.",
    ),
    PanelSource(
        panel="benchmark_artifacts",
        kind=KIND_ARTIFACT,
        payload_func="benchmark_artifacts_payload",
        route="/api/benchmark_artifacts",
        producer="scripts/dashboard/build_bench_artifact_inventory",
        producer_repo="epyc-root",
        evidence="data/benchmark_artifact_inventory.json",
        timestamp_field="generated_at",
        absence_means=(
            "the inventory has never been built in this checkout; the page says "
            "'not_built' rather than showing zero artifacts, because zero artifacts "
            "and no inventory are different claims about the benchmark corpus."),
        warn_s=7 * _DAY,
        stale_s=30 * _DAY,
        gates_health=False,
        absence_is_anomalous=False,
    ),
    PanelSource(
        panel="transport_probe",
        kind=KIND_LIVE,
        payload_func="transport_probe_payload",
        route="/health",
        producer="the hub process itself",
        producer_repo="epyc-root",
        evidence="the fact that this request was answered at all",
        timestamp_field="live-scan",
        absence_means=(
            "the hub is not serving. scripts/dashboard/hub_supervisor.sh polls this "
            "route every 15s and restarts the hub when it stops answering ok — "
            "which is why NO producer's health may reach it: a dead AutoKernel loop "
            "must not put the dashboard into a restart loop, because restarting the "
            "dashboard cannot revive a producer in another repository. The producer "
            "fold lives at /api/health."),
        gates_health=False,
    ),
    PanelSource(
        panel="health",
        kind=KIND_FOLD,
        payload_func="health_payload",
        route="/api/health",
        producer="dashboard.panels.fold over this registry",
        producer_repo="epyc-root",
        evidence="every other entry in PANELS",
        timestamp_field="live-scan",
        absence_means=(
            "impossible while the hub answers at all: the fold is computed in the "
            "request. Note that /health (the supervisor's transport probe) is a "
            "DIFFERENT route and deliberately reports only that the process serves."),
        gates_health=False,
    ),
))


# --------------------------------------------------------------------------- #
# Enumeration — the registry is checked against the CODE
# --------------------------------------------------------------------------- #
PAYLOAD_SUFFIX = "_payload"


def source(panel: str) -> PanelSource:
    """``PANELS[panel]`` with a diagnosis instead of a bare ``KeyError``.

    The hub reads its thresholds and builds every envelope through this, so a
    panel that loses its registry entry makes the hub REFUSE TO IMPORT with a
    sentence naming the panel — rather than starting and serving a card whose
    producer nobody can name. Failing at import is deliberate: this is the one
    error that must not be absence-tolerant.
    """
    try:
        return PANELS[panel]
    except KeyError:
        raise RegistryError(
            f"no registered producer for panel {panel!r}: the hub would serve a "
            f"panel nobody can vouch for. Known panels: {sorted(PANELS)}") from None


def discover_payload_functions(module: Any) -> set:
    """Every payload callable ``module`` itself defines.

    Reflection, not a list. ``__module__`` is compared so a payload function
    IMPORTED from elsewhere is not mistaken for one this module serves.

    ATTRIBUTION, NOT TYPE. The test is "can this callable be proved to belong to
    another module?", not "is this a ``def``". ``__module__`` answers that only
    for real ``def``\\ s and classes; on a ``functools.partial`` or any other
    callable OBJECT it reports the class's module (``functools``), which is where
    the machinery lives, not where the panel was bound. Excluding those — either
    by a type check or by trusting their ``__module__`` — makes an unsourced panel
    INVISIBLE to the totality test, which is the hand-maintained-roster failure
    one level down. Unattributable ⇒ counted, so the registry has to account
    for it.

    THE PREDICATE IS ``isfunction``, NOT ``isroutine``, AND THAT IS A BUG FIX.
    ``inspect.isroutine`` is not stable across interpreters: on Python 3.13 a
    ``functools.partial`` is not a routine, and on Python 3.14 — the interpreter
    ``uv run`` uses for this repo's tests — it IS one. So the guard above read
    ``partial.__module__ == "functools"``, concluded "provably defined
    elsewhere", and skipped it: ``ghost_payload = functools.partial(kernel_payload)``
    went back to being invisible, on the runner that actually gates. The same
    evasion, reopened by a version bump rather than by an edit, which is why the
    regression test for it now pins the CLASS of callable rather than trusting a
    predicate whose meaning moves. ``isfunction``/``isclass`` are true only of
    Python-level ``def``\\ s and classes, whose ``__module__`` really is the
    binding site; everything else is counted.
    """
    name = getattr(module, "__name__", None)
    out = set()
    for attr, value in vars(module).items():
        if not attr.endswith(PAYLOAD_SUFFIX):
            continue
        if not callable(value):
            continue
        if inspect.isfunction(value) or inspect.isclass(value):
            owner = getattr(value, "__module__", None)
            if name is not None and owner is not None and owner != name:
                continue  # provably defined elsewhere: not a panel this hub serves
        out.add(attr)
    return out


def registry_gaps(module: Any) -> dict:
    """Symmetric difference between the registry and the hub's actual code.

    Every key maps to a sorted list of offenders; ALL EMPTY means the registry is
    total. Checked in both directions on purpose — an entry with no function is a
    stale registry, and a function with no entry is an unsourced panel, and both
    end with an operator trusting a page nobody can vouch for.
    """
    funcs = discover_payload_functions(module)
    registered_funcs = {src.payload_func for src in PANELS.values()}
    routes = dict(getattr(module, "API_ROUTES", {}) or {})
    routes.update(getattr(module, "API_ROUTES_WITH_STATUS", {}) or {})
    routes.update(getattr(module, "PROBE_ROUTES", {}) or {})

    gaps: dict[str, list] = {
        "unregistered_payload_functions": sorted(funcs - registered_funcs),
        "registered_without_function": sorted(registered_funcs - funcs),
        "unregistered_routes": [],
        "panels_missing_route": [],
        "route_mismatch": [],
    }
    declared_routes = {src.route: src.panel for src in PANELS.values() if src.route}
    for route in sorted(routes):
        if route not in declared_routes:
            gaps["unregistered_routes"].append(route)
    for panel, src in sorted(PANELS.items()):
        if src.route is None:
            gaps["panels_missing_route"].append(panel)
            continue
        if src.route not in routes:
            gaps["route_mismatch"].append(
                f"{panel}: declares route {src.route!r}, which the hub does not serve")
            continue
        served = routes[src.route]
        served_name = getattr(served, "__name__", None)
        if served_name is None:
            # An UNIDENTIFIABLE handler is a gap, not a pass. Skipping it (the
            # obvious `if served_name is not None` guard) lets
            # ``API_ROUTES["/api/kernel"] = functools.partial(outcome_payload)``
            # through clean: the route is declared, the panel is registered, and
            # the wrong producer is on the wire with nothing able to say so.
            gaps["route_mismatch"].append(
                f"{panel}: route {src.route!r} is served by an unidentifiable "
                f"callable ({type(served).__name__}) — the registry names "
                f"{src.payload_func!r} and nothing can check that claim. Bind a "
                "named function.")
            continue
        if served_name != src.payload_func:
            gaps["route_mismatch"].append(
                f"{panel}: route {src.route!r} is served by {served_name!r}, "
                f"but the registry names {src.payload_func!r}")
    return gaps


# --------------------------------------------------------------------------- #
# The observation a panel reader hands back
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Observation:
    """What a panel's reader FOUND — the only thing a reader must produce.

    ``artifact_present`` and ``timestamp`` are separate because their combination
    is the fact the scar destroyed:

      * ``artifact_present=False``                -> no producer left anything.
      * ``artifact_present=True, timestamp=None`` -> a document exists and says
        nobody reported (a v2 contract with every section ``not_reported``).
      * ``artifact_present=True, timestamp=<t>, populated=False`` -> the producer
        reported, and the report is legitimately empty.
    """

    artifact_present: bool
    timestamp: Optional[float] = None
    source: Optional[str] = None
    populated: Optional[bool] = None
    detail: Optional[str] = None
    #: The evidence the reader ACTUALLY read, when it is resolved at runtime
    #: rather than fixed in the registry. ``PanelSource.evidence`` is the
    #: DECLARED default (and the thing a seam test pins against the producer's
    #: own export path); the hub's file-backed readers honour
    #: ``KERNEL_DASHBOARD_JSON`` / ``AUTOPILOT_OUTCOME_JSON`` environment
    #: overrides, and an envelope that names the default while the hub is reading
    #: an override points an investigation at a file nobody wrote. Absent ⇒ the
    #: declared evidence, so every existing reader keeps its old wire value.
    evidence: Optional[str] = None
    #: Producer progress identity for the watchdog's second arm. Two exports with
    #: the same watermark mean the producer did not advance, however fresh their
    #: timestamps look.
    watermark: Optional[str] = None
    #: The producer has DECLARED it is not running (e.g. the AutoKernel controller
    #: reports ``stopped``). Silence is then expected, not evidence of death.
    producer_idle: bool = False
    #: Sections/subsystems the producer itself flagged as unreported.
    unreported: Sequence[str] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_present, bool):
            raise RegistryError("Observation.artifact_present must be a bool")
        object.__setattr__(self, "unreported", tuple(self.unreported or ()))
        if self.evidence is not None and (not isinstance(self.evidence, str)
                                          or not self.evidence.strip()):
            # An EMPTY override would blank the one field that tells an operator
            # which file to go and look at — worse than the stale default it was
            # added to correct.
            raise RegistryError(
                "Observation.evidence: pass the resolved evidence path, or None "
                "to keep the registry's declared one; an empty override erases "
                "the only pointer the panel gives an investigator")


def absent(source: PanelSource, detail: str) -> Observation:
    """The reader found nothing at all. ``detail`` says why, always."""
    if not detail or not detail.strip():
        raise RegistryError(
            f"absent({source.panel!r}) requires a reason — an unexplained absence "
            "is a clean-looking panel with a new label on it")
    return Observation(artifact_present=False, detail=detail)


def live(populated: bool = True, source: str = "live-scan") -> Observation:
    """A panel computed inside the request."""
    return Observation(artifact_present=True, timestamp=None, source=source,
                       populated=populated)


# --------------------------------------------------------------------------- #
# Freshness envelope
# --------------------------------------------------------------------------- #
#: THE classifier, and there is only one. ``freshness.classify_age`` is the
#: single implementation the mtime badge, the kernel envelope and the outcome
#: envelope all call, so the three cannot drift into three thresholds idioms.
classify_age = freshness.classify_age


def observe_watermark(state: dict, panel: str, watermark: Optional[str], *,
                      now: Optional[float] = None) -> Optional[dict]:
    """Record that ``panel``'s producer is currently at ``watermark``.

    This is the watchdog's memory and the caller owns it (the hub keeps one dict
    under a lock; a test passes its own). ``None`` clears the entry: a producer
    whose watermark cannot be read is not watched by this arm at all, rather than
    being pinned to a stale one.
    """
    now = time.time() if now is None else now
    if watermark is None:
        state.pop(panel, None)
        return None
    entry = state.get(panel)
    if entry is None or entry.get("watermark") != watermark:
        entry = {"watermark": watermark, "first_seen": now, "last_seen": now,
                 "polls": 1}
    else:
        entry = {"watermark": watermark, "first_seen": entry["first_seen"],
                 "last_seen": now, "polls": int(entry.get("polls", 1)) + 1}
    state[panel] = entry
    return entry


def _watchdog(source: PanelSource, obs: Observation, age_s: Optional[float],
              watchdog_state: Optional[Mapping], now: float) -> dict:
    """The transport watchdog: has a producer STOPPED, as distinct from having
    reported nothing?

    Two arms, deliberately independent:

    * **age arm** (stateless, survives a hub restart): the newest SEMANTIC
      timestamp in the panel's evidence is older than ``silent_after_s``. This is
      the trial-1302 detector — the file is there and populated, and the producer
      behind it stopped.
    * **watermark arm** (in-process): the timestamp keeps moving but the
      producer's progress identity has not changed for longer than
      ``silent_after_s``. This catches a producer that is alive enough to rewrite
      its export and dead enough to make no progress.

    ``producer_idle`` is the compliant path for both arms: a producer that has
    declared itself stopped is allowed to be silent.
    """
    if not source.watched:
        return {"state": WATCHDOG_UNWATCHED, "since_s": None,
                "reason": "this panel is computed per request or its liveness is "
                          "owned by another signal; nothing to watch"}
    if not obs.artifact_present and obs.timestamp is None:
        return {"state": WATCHDOG_NEVER, "since_s": None,
                "reason": source.absence_means}
    if obs.timestamp is None:
        return {"state": WATCHDOG_NO_TIMESTAMP, "since_s": None,
                "reason": (obs.detail or
                           f"{source.producer} left an artifact carrying no "
                           f"{source.timestamp_field}; it cannot be dated, so it "
                           "cannot be trusted to be current")}
    budget = source.silent_after_s
    if budget is not None and age_s is not None and age_s > budget:
        if obs.producer_idle:
            return {"state": WATCHDOG_IDLE, "since_s": round(age_s, 1),
                    "reason": (f"{source.producer} reports it is stopped; silence "
                               f"for {age_s:.0f}s is expected, not evidence of death")}
        return {"state": WATCHDOG_STOPPED, "since_s": round(age_s, 1),
                "reason": (f"{source.producer} has not advanced "
                           f"{source.timestamp_field} for {age_s:.0f}s "
                           f"(budget {budget:.0f}s). The panel still renders its "
                           "last report; the producer behind it has stopped.")}
    entry = (watchdog_state or {}).get(source.panel)
    if (entry and obs.watermark is not None
            and entry.get("watermark") == obs.watermark
            and int(entry.get("polls", 1)) >= 2 and budget is not None):
        held = now - float(entry["first_seen"])
        if held > budget:
            if obs.producer_idle:
                return {"state": WATCHDOG_IDLE, "since_s": round(held, 1),
                        "reason": f"{source.producer} reports it is stopped"}
            return {"state": WATCHDOG_NOT_ADVANCING, "since_s": round(held, 1),
                    "reason": (f"{source.producer} keeps re-reporting watermark "
                               f"{obs.watermark!r} — unchanged for {held:.0f}s "
                               f"(budget {budget:.0f}s). Fresh timestamps, no "
                               "progress.")}
    return {"state": WATCHDOG_OK, "since_s": None,
            "reason": f"{source.producer} is reporting and advancing"}


def envelope(source: PanelSource, obs: Observation, *,
             now: Optional[float] = None,
             watchdog_state: Optional[Mapping] = None) -> dict:
    """Classify one panel's observation into the wire envelope.

    Returns a SUPERSET of the shape ``server.py`` already emits under
    ``_freshness`` (``staleness_class``, ``age_s``, ``timestamp``, ``source``), so
    the existing pages and tests keep working, plus the fields that make absence
    renderable.
    """
    if not isinstance(source, PanelSource):
        raise RegistryError(f"envelope: expected PanelSource, got {type(source).__name__}")
    if not isinstance(obs, Observation):
        raise RegistryError(f"envelope: expected Observation, got {type(obs).__name__}")
    now = time.time() if now is None else now

    # A report dated in the FUTURE cannot date anything. ``age`` is clamped at
    # zero below (small clock jitter must not read as negative age), and that
    # clamp is exactly what turns a skewed producer into a permanently fresh
    # panel: a loop dead for a year whose timestamps sit an hour ahead reads
    # ``fresh``/``ok`` forever. So beyond the tolerance the observation is
    # rewritten as UNDATED before anything classifies it.
    skew_s = None
    if obs.timestamp is not None and (obs.timestamp - now) > FUTURE_SKEW_TOLERANCE_S:
        skew_s = obs.timestamp - now
        detail = (
            f"{source.producer} dated this report {skew_s:.0f}s IN THE FUTURE "
            f"({source.timestamp_field}). A future timestamp cannot age, so the "
            "panel would read fresh forever however long the producer has been "
            "dead; it is treated as undated instead.")
        if obs.detail:
            detail = f"{detail} Reader detail: {obs.detail}"
        obs = replace(obs, timestamp=None, detail=detail)

    ts = obs.timestamp
    age = None if ts is None else max(0.0, now - ts)

    if source.kind in LIVE_KINDS:
        cls = CLASS_FRESH
        reporting = REPORTING_OBSERVED
        watchdog = _watchdog(source, obs, age, watchdog_state, now)
    else:
        cls = classify_age(age, source.warn_s, source.stale_s)
        watchdog = _watchdog(source, obs, age, watchdog_state, now)
        if ts is None:
            reporting = REPORTING_ABSENT
        elif watchdog["state"] in WATCHDOG_ALARMS:
            reporting = REPORTING_SILENT
        else:
            reporting = REPORTING_OBSERVED
    if skew_s is not None:
        # Overrides ``unwatched`` too: this is a defect in the EVIDENCE, so it is
        # visible on a panel nobody watches for liveness just as much as on one
        # that is watched.
        cls = CLASS_MISSING
        watchdog = {"state": WATCHDOG_FUTURE_TIMESTAMP,
                    "since_s": round(skew_s, 1), "reason": obs.detail}

    if obs.populated is None:
        content = CONTENT_UNKNOWN
    else:
        content = CONTENT_POPULATED if obs.populated else CONTENT_EMPTY
    if reporting == REPORTING_ABSENT:
        # Nothing reported => nothing can be said about content. Refusing to say
        # "empty" here is the point: an empty render over an absent producer is
        # the panel that lied for 23 hours.
        content = CONTENT_UNKNOWN

    out = {
        "panel": source.panel,
        "producer": source.producer,
        "producer_repo": source.producer_repo,
        # The file the reader actually opened when it resolved one, else the
        # registry's declared default.
        "evidence": obs.evidence or source.evidence,
        "declared_evidence": source.evidence,
        "route": source.route,
        "kind": source.kind,
        "staleness_class": cls,
        "age_s": None if age is None else round(age, 1),
        "timestamp": None if ts is None else round(ts, 3),
        "source": obs.source if reporting != REPORTING_ABSENT else None,
        "artifact_present": bool(obs.artifact_present),
        "reporting": reporting,
        "content": content,
        "unreported": list(obs.unreported),
        "detail": obs.detail,
        "watchdog": watchdog,
        "gates_health": bool(source.gates_health),
        "thresholds": {"warn_s": source.warn_s, "stale_s": source.stale_s,
                       "silent_after_s": source.silent_after_s},
    }
    if reporting != REPORTING_OBSERVED or obs.unreported:
        # The registry's declared meaning travels WITH the absence, so a renderer
        # cannot show a blank card without also having the sentence that explains
        # what blank means here.
        out["absence_means"] = source.absence_means
    return out


# --------------------------------------------------------------------------- #
# The fold
# --------------------------------------------------------------------------- #
#: How bad each state is. The fold picks the worst panel by this score and says
#: which one and why; nothing is averaged, because an average hides the one dead
#: producer among six live ones.
_CLASS_SCORE = {CLASS_FRESH: 0, CLASS_MISSING: 2, CLASS_AGING: 1, CLASS_STALE: 3}
_WATCHDOG_SCORE = {
    WATCHDOG_UNWATCHED: 0, WATCHDOG_OK: 0, WATCHDOG_IDLE: 0,
    WATCHDOG_NO_TIMESTAMP: 2, WATCHDOG_NEVER: 2,
    WATCHDOG_FUTURE_TIMESTAMP: 4,
    WATCHDOG_NOT_ADVANCING: 4, WATCHDOG_STOPPED: 5,
}


def panel_score(env: Mapping) -> int:
    """Severity of one envelope. Higher is worse."""
    score = max(_CLASS_SCORE.get(env.get("staleness_class"), 0),
                _WATCHDOG_SCORE.get((env.get("watchdog") or {}).get("state"), 0))
    if env.get("unreported"):
        score = max(score, 2)
    return score


def panel_verdict(env: Mapping) -> tuple:
    """``(status, why)`` for one panel, independent of whether it gates health."""
    wd = (env.get("watchdog") or {})
    wd_state = wd.get("state")
    panel = env.get("panel")
    if wd_state in WATCHDOG_ALARMS:
        return STATUS_DEGRADED, f"{panel}: {wd_state} — {wd.get('reason')}"
    if wd_state in WATCHDOG_DEFECTS:
        # A broken timestamp is a DEFECT, not a cold start: it must not be routed
        # through the benign-absence path that a never-exported panel takes.
        return STATUS_DEGRADED, f"{panel}: {wd_state} — {wd.get('reason')}"
    if env.get("reporting") == REPORTING_ABSENT:
        # ``detail`` is the reader's own account (e.g. "contract unreadable:
        # Expecting property name…"). It comes FIRST because the registry's
        # generic absence sentence describes the never-exported case, and quoting
        # only that over a corrupt artifact tells the operator the opposite of
        # what happened.
        detail = env.get("detail")
        if detail:
            return (STATUS_ABSENT,
                    f"{panel}: nothing datable reported — {detail} "
                    f"[{env.get('absence_means')}]")
        return (STATUS_ABSENT,
                f"{panel}: no producer reported — {env.get('absence_means')}")
    if env.get("unreported"):
        return (STATUS_ABSENT,
                f"{panel}: reported, but section(s) {sorted(env['unreported'])} "
                f"have no producer — {env.get('absence_means')}")
    if env.get("staleness_class") == CLASS_STALE:
        if wd_state == WATCHDOG_IDLE:
            return STATUS_OK, f"{panel}: stale but its producer declares it idle"
        return (STATUS_DEGRADED,
                f"{panel}: {env.get('source')} is {env.get('age_s')}s old "
                f"(stale beyond {(env.get('thresholds') or {}).get('stale_s')}s)")
    return STATUS_OK, f"{panel}: reporting"


def verdict_gates_status(env: Mapping, panel: str,
                         registry: Optional[Mapping] = None) -> bool:
    """Does this panel's non-ok verdict get to colour the fold's ``status``?

    ``gates_health`` is a statement about a panel's NOISE — a paused loop reading
    stale, a cache absent on a fresh checkout — and it is honoured for exactly
    those. It is NOT a licence to be dead quietly:

    * A **watchdog alarm or evidence defect always gates.** "a producer that
      should be reporting has stopped" is the fact this whole surface exists to
      publish, and ``status: ok`` beside ``worst.watchdog: stopped_reporting`` is
      the trial-1302 dashboard rebuilt with better words on it. A panel whose
      silence is genuinely normal declares ``watched=False`` (``bus``, ``queue``)
      and then honestly reads ``unwatched`` instead of alarming into a green
      fold; a producer that has finished declares itself idle and reads ``idle``.
    * **Staleness and absence** are gated by ``gates_health`` /
      ``absence_is_anomalous``, exactly as before.
    """
    registry = PANELS if registry is None else registry
    wd_state = (env.get("watchdog") or {}).get("state")
    if wd_state in WATCHDOG_ALARMS or wd_state in WATCHDOG_DEFECTS:
        return True
    if not env.get("gates_health"):
        return False
    if (env.get("reporting") == REPORTING_ABSENT and panel in registry
            and not registry[panel].absence_is_anomalous):
        return False  # declared benign cold start: loud, but not a health verdict
    return True


def fold(envelopes: Mapping, *, registry: Optional[Mapping] = None) -> dict:
    """Fold every panel envelope into ONE health verdict that names a panel.

    Four rules, in this order:

    1. A **watchdog alarm** is ``degraded``, on any panel. That is the trial-1302
       case and it is the reason this function exists; see
       :func:`verdict_gates_status` for why ``gates_health`` does not excuse it.
    2. A **stale** health-gating panel is ``degraded`` (the hub's pre-AK6
       behaviour, preserved) unless its producer declared itself idle.
    3. **Absence** is ``absent``, not ``ok`` and not ``degraded`` — but only when
       the registry declares the absence anomalous. Absence is ALWAYS listed
       under ``absent`` and named in ``attention`` regardless, so the fold can
       never be green over a producer nobody can find.
    4. A **registered panel with no envelope at all** is ``degraded``. A fold is
       only a fold over its universe: ``fold({})`` returning ``ok`` would be the
       original scar in its purest form — green because nobody reported. The
       universe is the REGISTRY, so a panel that silently drops out of
       ``panel_envelopes()`` is named rather than subtracted.

    ``status_set_by`` names the panel that actually produced ``status``. ``worst``
    is the worst panel by severity SCORE, which need not be the same panel: a
    non-gating stale card can outscore an unsourced gating one, and reporting a
    colour set by X beside a name explaining Y is how an operator reads the wrong
    offender. Both are on the wire, and neither may be null while ``status`` is
    not ``ok``.
    """
    registry = PANELS if registry is None else registry
    status = STATUS_OK
    status_set_by = None
    attention: list = []
    absent_panels: list = []
    worst_env = None
    worst_score = -1

    def _raise(verdict: str, entry: dict) -> None:
        nonlocal status, status_set_by
        if STATUS_ORDER.index(verdict) > STATUS_ORDER.index(status):
            status, status_set_by = verdict, entry

    for panel in sorted(envelopes):
        env = envelopes[panel]
        score = panel_score(env)
        if score > worst_score:
            worst_score, worst_env = score, env
        verdict, why = panel_verdict(env)
        if env.get("reporting") == REPORTING_ABSENT:
            absent_panels.append({"panel": panel, "producer": env.get("producer"),
                                  "evidence": env.get("evidence"),
                                  "absence_means": env.get("absence_means"),
                                  "anomalous": bool(
                                      registry[panel].absence_is_anomalous
                                      if panel in registry else False)})
        entry = {"panel": panel, "verdict": verdict, "why": why,
                 "gates_health": bool(env.get("gates_health"))}
        if verdict != STATUS_OK:
            attention.append(entry)
        if verdict != STATUS_OK and verdict_gates_status(env, panel, registry):
            _raise(verdict, entry)

    for panel in sorted(registry):
        if panel in envelopes:
            continue
        src = registry[panel]
        why = (f"{panel}: REGISTERED BUT NOT FOLDED — {src.producer} has an entry "
               f"in the panel registry and no envelope reached the fold, so the "
               f"hub cannot say whether it is reporting. {src.absence_means}")
        entry = {"panel": panel, "verdict": STATUS_DEGRADED, "why": why,
                 "gates_health": bool(src.gates_health)}
        attention.append(entry)
        _raise(STATUS_DEGRADED, entry)

    summary = None
    if worst_env is not None:
        w_verdict, w_why = panel_verdict(worst_env)
        summary = {
            "panel": worst_env.get("panel"),
            "producer": worst_env.get("producer"),
            "staleness_class": worst_env.get("staleness_class"),
            "reporting": worst_env.get("reporting"),
            "content": worst_env.get("content"),
            "watchdog": (worst_env.get("watchdog") or {}).get("state"),
            "verdict": w_verdict,
            "why": w_why,
            "gates_health": bool(worst_env.get("gates_health")),
        }
    return {"status": status, "status_set_by": status_set_by, "worst": summary,
            "attention": attention, "absent": absent_panels}

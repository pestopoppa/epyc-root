"""Cross-role admission gate.

Phase B of `handoffs/active/cross-role-bw-aware-routing.md`.

Wraps the central model-call boundary (`src.llm_primitives.inference._real_call_impl`
or `_real_call_single`) so a request for role R is admitted only when the
active set of decoding roles is compatible with R per the contention matrix.

Key design points (per handoff):

- Authoritative active-decode source under `ORCHESTRATOR_PER_REGION_LOCKS=1`:
  `src.runtime.cpu_region_lock.active_region_holders()`. The in-process
  `_full_active`/`_quarter_active` flags on `ConcurrencyAwareBackend` are
  NOT cross-process and must not be used here.
- The gate runs BEFORE `LLMPrimitives._acquire_role()` — otherwise the
  per-role semaphore wait briefly hides an admitted request from the
  active-decode snapshot.
- Background traffic queues on `block`/`borderline`/`unknown` pairs.
  Foreground traffic queues on hard `block`, may DEGRADED_ALLOW on
  borderline-below-floor when SLO is tight.
- Metrics: `contention_blocked_count`, `contention_wait_seconds`,
  `active_decodes_by_role`, `contention_unknown_pair_count`. The admission
  snapshot still uses the attribution view, but display counts use exact
  holder-instance accounting so one full-shape decode is not shown as every
  overlapping quarter instance.

Threading model: gate decisions are inexpensive (one /proc/locks scan +
matrix lookup) — single global lock is fine. Queue management uses a
simple wait-and-retry with backoff; we don't need a priority queue today.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from src.scheduling.contention import (
    ContentionMatrix,
    MatrixStatus,
    PairDecision,
    TrafficClass,
    load_contention_matrix,
    matrix_status,
    pair_policy,
    nway_policy,
    seam_admit,
    shape_aware_contention_enabled,
)

log = logging.getLogger("scheduling.contention_gate")

# Polling interval for queued requests waiting on a contention release.
# Short enough to feel responsive, long enough not to thrash /proc/locks.
_GATE_POLL_S = 0.150

# Default max queue wait if the request doesn't specify one.
_DEFAULT_FOREGROUND_WAIT_MS = 5_000   # 5 s
_DEFAULT_BACKGROUND_WAIT_MS = 90_000  # 90 s (autopilot can wait quite a while)


@dataclass
class GateDecision:
    """Outcome of a single gate evaluation."""

    admitted: bool
    decision: PairDecision
    waited_s: float = 0.0
    blocking_roles: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class GateMetrics:
    """Counters exposed to dashboard / Prometheus.

    Aggregated across the process; the orchestrator's existing telemetry
    exporter can pick them up via `gate.metrics_snapshot()`.
    """

    contention_blocked_count: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    contention_wait_seconds: float = 0.0
    contention_unknown_pair_count: int = 0
    contention_degraded_allow_count: int = 0
    contention_admitted_count: int = 0
    contention_timeout_count: int = 0
    contention_nway_restricted_count: int = 0  # J4c: N-way set more restrictive than pairwise
    # active_decodes_by_role: {role: count} for back-compat;
    # active_instances_by_role: {role: [instance_idx, ...]} for richer dashboard rendering
    active_decodes_by_role: dict[str, int] = field(default_factory=dict)
    active_instances_by_role: dict[str, list[int]] = field(default_factory=dict)


class ContentionGate:
    """Singleton-ish gate. Use `get_gate()` to access the process instance."""

    def __init__(
        self,
        matrix: ContentionMatrix | None = None,
        active_holders_fn: Callable[[], dict[str, list[int]]] | None = None,
    ) -> None:
        self._matrix = matrix
        self._active_holders_fn = active_holders_fn  # injectable for tests
        self._metrics = GateMetrics()
        self._lock = threading.Lock()
        self._matrix_status_cache: MatrixStatus | None = None
        self._matrix_status_checked_at: float = 0.0
        self._live_topo_hash_cache: str | None = None

    # ── matrix access (lazy load + status caching) ──────────────────

    def _get_matrix(self) -> ContentionMatrix | None:
        if self._matrix is None:
            try:
                self._matrix = load_contention_matrix()
            except FileNotFoundError:
                # Fail-open per handoff line 113 — return None; pair_policy()
                # consumers handle None matrix gracefully (background queues,
                # foreground allows).
                return None
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to load contention matrix: %s", exc)
                return None
        return self._matrix

    def matrix_health(self) -> MatrixStatus:
        """Cheap, cached status check (refreshed every 60 s). Passes the LIVE topology hash so a
        topology change (NUMA_CONFIG edit / quarter re-pin) is detected as STALE — the runtime no
        longer trusts a matrix benched against a different stack (operator audit #2, 2026-05-27)."""
        now = time.time()
        if self._matrix_status_cache is None or (now - self._matrix_status_checked_at) > 60.0:
            self._matrix_status_cache = matrix_status(current_topology_hash=self._live_topology_hash())
            self._matrix_status_checked_at = now
        return self._matrix_status_cache

    def _live_topology_hash(self) -> str | None:
        """Best-effort live topology fingerprint (guarded import, cached). Returns None when the
        live config is unavailable so matrix_status falls back to the age check only (no false
        STALE). Mirrors src/runtime/inference_tap.py's _topology_hash()."""
        if self._live_topo_hash_cache is None:
            try:
                from scripts.server.stack_numa import NUMA_CONFIG  # type: ignore[import-not-found]
                from src.scheduling.contention import topology_fingerprint_for_matrix

                self._live_topo_hash_cache = topology_fingerprint_for_matrix(
                    NUMA_CONFIG,
                    self._get_matrix(),
                )
            except Exception:  # noqa: BLE001
                self._live_topo_hash_cache = ""
        return self._live_topo_hash_cache or None

    # ── active-decode snapshot ──────────────────────────────────────

    def _active_holders(self) -> dict[str, list[int]]:
        if self._active_holders_fn is not None:
            return self._active_holders_fn()
        # Only consult region locks when the feature flag is on; otherwise
        # there's no cross-process active-decode source and we degrade to
        # "no actives" (which means everything is allowed).
        if os.environ.get("ORCHESTRATOR_PER_REGION_LOCKS", "0").strip() not in {"1", "true", "yes", "on"}:
            return {}
        try:
            from src.runtime.cpu_region_lock import active_region_holders
            return active_region_holders()
        except Exception as exc:  # noqa: BLE001
            log.warning("active_region_holders failed: %s", exc)
            return {}

    def _active_metric_holders(self, fallback: dict[str, list[int]]) -> dict[str, list[int]]:
        """Exact holder-instance snapshot for metrics/dashboard display.

        Tests that inject `_active_holders_fn` expect the injected snapshot to
        drive both admission and metrics. Production uses the exact per-PID view
        so attribution over-reporting does not surface as bogus activity counts.
        """
        if self._active_holders_fn is not None:
            return {role: sorted(set(idxs)) for role, idxs in fallback.items()}
        if os.environ.get("ORCHESTRATOR_PER_REGION_LOCKS", "0").strip() not in {"1", "true", "yes", "on"}:
            return {}
        try:
            from src.runtime.cpu_region_lock import active_region_holder_instances
            exact = active_region_holder_instances()
            return exact if exact or not fallback else fallback
        except Exception as exc:  # noqa: BLE001
            log.warning("active_region_holder_instances failed: %s", exc)
            return fallback

    @staticmethod
    def _gpu_candidate_is_disjoint_from_cpu_holders(
        role: str,
        holders: dict[str, list[int]],
    ) -> bool:
        """Return true only for a resolved GPU candidate against resolved CPU holders.

        Region-lock holders represent CPU decode placements.  The legacy pair
        matrix predates the device axis and can therefore falsely queue a GPU
        role (for example coder_escalation on :8083) behind frontdoor CPU work.
        Device declarations are authoritative here; any missing/disagreeing
        declaration fails closed into the existing matrix path.
        """
        try:
            from src.scheduling.device_model import DeviceClass, resolve_role_device

            if resolve_role_device(role).device_class is not DeviceClass.GPU:
                return False
            return all(
                resolve_role_device(active_role).device_class is DeviceClass.CPU
                for active_role in holders
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("device-aware contention resolution failed for %s: %s", role, exc)
            return False

    # ── admission core ──────────────────────────────────────────────

    def evaluate(
        self,
        role: str,
        traffic_class: TrafficClass | str = TrafficClass.FOREGROUND_INTERACTIVE,
        candidate_topology_idx: int | None = None,
    ) -> GateDecision:
        """One-shot evaluation: would role be admitted right now?

        Does NOT wait; just returns the decision based on a current snapshot.
        Useful for testing + when the caller has its own queue/retry logic.

        `candidate_topology_idx` (B wiring, default None) — the topology index of
        the instance the caller intends to dispatch to. When supplied AND
        `shape_aware_contention_enabled()` (BOTH dual flags on) AND `seam_admit`
        returns a non-None verdict, that placement-aware verdict is
        AUTHORITATIVE: it REPLACES the legacy role-keyed result (both ways — it
        can admit a disjoint placement the stale role-keyed pair layer would
        falsely QUEUE, and can queue an overlap the pair layer would allow).
        This is safe because `seam_admit` is itself fail-closed (overlap →
        QUEUE, unknown placement → background QUEUE) and its disjoint branch
        re-checks the SAME `nway_policy` the legacy path used, so it only ever
        overrides the STALE role-keyed PAIR layer, never a measured N-way block
        (and matrix-health fail-closed already returned earlier). Default None /
        either flag off / seam None → byte-identical legacy role-keyed behavior;
        the legacy pairwise loop is untouched.
        """
        if isinstance(traffic_class, str):
            try:
                traffic_class = TrafficClass(traffic_class)
            except ValueError:
                traffic_class = TrafficClass.BACKGROUND
        matrix = self._get_matrix()
        holders = self._active_holders()

        # Update active-by-role snapshot for metrics. Admission uses the
        # attribution view above; metrics use the exact holder-instance view.
        metric_holders = self._active_metric_holders(holders)
        with self._lock:
            self._metrics.active_decodes_by_role = {r: len(idxs) for r, idxs in metric_holders.items()}
            self._metrics.active_instances_by_role = {r: list(idxs) for r, idxs in metric_holders.items()}

        if not holders:
            return GateDecision(admitted=True, decision=PairDecision.ALLOW, reason="no active decodes")

        if self._gpu_candidate_is_disjoint_from_cpu_holders(role, holders):
            return GateDecision(
                admitted=True,
                decision=PairDecision.ALLOW,
                reason="resolved GPU lane is disjoint from active CPU region holders",
            )

        # Topology-freshness fail-closed (#2, operator audit 2026-05-27): if the matrix is not
        # certified-fresh against the LIVE stack (STALE/MISSING/INVALID) while concurrency is
        # active, do NOT trust its verdicts — serialize background/bulk (QUEUE) and degraded-admit
        # foreground (visible, not silently "healthy"). No-op when the matrix is OK (the normal case).
        health = self.matrix_health()
        if health != MatrixStatus.OK:
            is_bg = traffic_class == TrafficClass.BACKGROUND
            return GateDecision(
                admitted=not is_bg,
                decision=PairDecision.QUEUE if is_bg else PairDecision.DEGRADED_ALLOW,
                blocking_roles=sorted(holders.keys()),
                reason=f"matrix {health.value}: fail-closed (topology not certified-fresh)",
            )

        # Evaluate against each active role (including same-role for multi-instance pairs).
        worst: PairDecision = PairDecision.ALLOW
        blocking: list[str] = []
        for active_role in holders.keys():
            decision = pair_policy(role, active_role, traffic_class, matrix=matrix)
            if decision == PairDecision.ALLOW:
                continue
            # QUEUE > DEGRADED_ALLOW > BLOCK ordering for "worst"; we
            # bias toward the most-restrictive decision so the caller's
            # wait logic always picks a safe path.
            if worst == PairDecision.ALLOW:
                worst = decision
            elif decision == PairDecision.BLOCK:
                worst = PairDecision.BLOCK
            elif decision == PairDecision.QUEUE and worst != PairDecision.BLOCK:
                worst = PairDecision.QUEUE
            blocking.append(active_role)

        # N-way check (J4c): pairwise-allow does NOT certify the full active set — an
        # all-pairwise-allowed set could be aggregate-negative, so consult the measured n_way
        # matrix for the EXACT active-set union. DEFENSIVE: as of the 2026-05-26 certified-affinity
        # re-bench there is NO measured N-way block (the famous {frontdoor,ingest,vision} 0.847 was
        # a bad-affinity artifact -> 1.731 allow); this queues any future measured-block set.
        active_set = sorted(set(holders.keys()) | {role})
        if len(active_set) >= 2:
            nway_decision = nway_policy(active_set, traffic_class, matrix=matrix)
            if nway_decision != PairDecision.ALLOW:
                _prec = {
                    PairDecision.ALLOW: 0,
                    PairDecision.DEGRADED_ALLOW: 1,
                    PairDecision.QUEUE: 2,
                    PairDecision.BLOCK: 3,
                }
                if _prec[nway_decision] > _prec[worst]:
                    worst = nway_decision
                if not blocking:
                    blocking = [r for r in active_set if r != role]
                with self._lock:
                    self._metrics.contention_nway_restricted_count += 1

        # B wiring (shape-keyed-contention-gating): placement-aware admission.
        # ONLY when the caller supplied a candidate instance AND both dual flags
        # are on. When consulted and it returns a verdict, the seam is
        # AUTHORITATIVE — it REPLACES the legacy role-keyed `worst`, not merely
        # tightens it. This is the whole point of B: the legacy `pair_policy`
        # layer is role-keyed and reads a STALE primary-overlap ratio (e.g.
        # frontdoor+ingest=0.37 → QUEUE) even when the candidate placement is
        # physically DISJOINT and measured-good (frontdoor.q2 beside ingest's
        # node0-half → 1.716 ALLOW). Tightening-only could never admit that, so
        # it would defeat B. The override is SAFE because seam_admit is itself
        # fail-closed: physical overlap → QUEUE, unknown placement → background
        # QUEUE, and the disjoint branch re-checks the SAME `nway_policy` the
        # legacy path used — so the seam can only "loosen" the stale role-keyed
        # PAIR layer, never an actual measured N-way block. Matrix-health
        # fail-closed already returned above, so a stale matrix never reaches
        # here. seam_admit returns None (→ keep legacy `worst`) when disabled,
        # on unknown-placement foreground, or on snapshot failure foreground.
        # Default (no idx / flags off) → seam not consulted → legacy behavior.
        if candidate_topology_idx is not None and shape_aware_contention_enabled():
            try:
                seam_decision = seam_admit(
                    role,
                    candidate_topology_idx,
                    traffic_class=traffic_class,
                    matrix=matrix,
                )
            except Exception as exc:  # noqa: BLE001 — never let the seam crash admission
                log.warning("seam_admit failed in gate (using legacy verdict): %s", exc)
                seam_decision = None
            if seam_decision is not None:
                # Authoritative replace. blocking is informational for non-ALLOW.
                worst = seam_decision
                if worst != PairDecision.ALLOW and not blocking:
                    blocking = [r for r in active_set if r != role]

        if worst == PairDecision.ALLOW:
            return GateDecision(admitted=True, decision=PairDecision.ALLOW, reason="all pairs + n-way allow")

        if worst == PairDecision.DEGRADED_ALLOW:
            # Foreground SLO override — let the request through but tag it
            with self._lock:
                self._metrics.contention_degraded_allow_count += 1
            return GateDecision(
                admitted=True,
                decision=PairDecision.DEGRADED_ALLOW,
                blocking_roles=sorted(set(blocking)),
                reason=f"degraded_allow (active: {','.join(sorted(set(blocking)))})",
            )

        return GateDecision(
            admitted=False,
            decision=worst,
            blocking_roles=sorted(set(blocking)),
            reason=f"{worst.value} (active: {','.join(sorted(set(blocking)))})",
        )

    def admit(
        self,
        role: str,
        traffic_class: TrafficClass | str = TrafficClass.FOREGROUND_INTERACTIVE,
        max_queue_wait_ms: int | None = None,
        candidate_topology_idx: int | None = None,
    ) -> GateDecision:
        """Wait-with-budget version of `evaluate`. Polls every ~150 ms.

        Returns a `GateDecision` with `admitted=True` and `waited_s` set
        on success, or `admitted=False` with `reason="timeout"` on budget
        exhaustion. When `candidate_topology_idx` is supplied and the
        shape-aware dual flag is enabled, each poll uses the placement-aware
        seam in `evaluate()`.
        """
        if isinstance(traffic_class, str):
            try:
                traffic_class = TrafficClass(traffic_class)
            except ValueError:
                traffic_class = TrafficClass.BACKGROUND
        if max_queue_wait_ms is None:
            if traffic_class == TrafficClass.BACKGROUND:
                max_queue_wait_ms = _DEFAULT_BACKGROUND_WAIT_MS
            else:
                max_queue_wait_ms = _DEFAULT_FOREGROUND_WAIT_MS

        deadline = time.monotonic() + max_queue_wait_ms / 1000.0
        wait_start = time.monotonic()
        first_decision: GateDecision | None = None
        while True:
            decision = self.evaluate(
                role,
                traffic_class,
                candidate_topology_idx=candidate_topology_idx,
            )
            if decision.admitted:
                decision.waited_s = time.monotonic() - wait_start
                with self._lock:
                    self._metrics.contention_wait_seconds += decision.waited_s
                    self._metrics.contention_admitted_count += 1
                return decision
            first_decision = first_decision or decision
            # Record the block in metrics on first hit
            for blocker in decision.blocking_roles:
                key = tuple(sorted([role, blocker]))
                with self._lock:
                    self._metrics.contention_blocked_count[key] += 1
            if time.monotonic() >= deadline:
                with self._lock:
                    self._metrics.contention_timeout_count += 1
                first_decision.waited_s = time.monotonic() - wait_start
                first_decision.reason = f"timeout after {first_decision.waited_s:.1f}s ({first_decision.reason})"
                return first_decision
            time.sleep(_GATE_POLL_S)

    @contextmanager
    def gate_decode(
        self,
        role: str,
        traffic_class: TrafficClass | str = TrafficClass.FOREGROUND_INTERACTIVE,
        max_queue_wait_ms: int | None = None,
    ) -> Iterator[GateDecision]:
        """Context manager — the cleanest call-site shape.

        Usage in `_real_call_impl`:
            with gate.gate_decode(role, traffic_class, max_queue_wait_ms) as d:
                if not d.admitted:
                    raise ContentionDenied(d.reason)
                # … invoke backend.infer*() …
        """
        decision = self.admit(role, traffic_class, max_queue_wait_ms)
        try:
            yield decision
        finally:
            # No release needed — the gate doesn't hold cross-process state.
            # Active-decode counts are sourced from region locks which the
            # backend.infer*() call already manages.
            pass

    # ── metrics ─────────────────────────────────────────────────────

    def metrics_snapshot(self) -> dict[str, Any]:
        """Read-only snapshot of current counters (for /dashboard exposure).

        Per-role scheduling state (quarter preference, migration counts) is
        gathered separately by the dashboard endpoint since it lives on
        `app.state.llm_primitives._backends` (per-request injection), not
        on a module-level singleton this gate can reach.
        """
        with self._lock:
            return {
                "contention_blocked_count": {
                    f"{a}+{b}": n for (a, b), n in self._metrics.contention_blocked_count.items()
                },
                "contention_wait_seconds": self._metrics.contention_wait_seconds,
                "contention_unknown_pair_count": self._metrics.contention_unknown_pair_count,
                "contention_degraded_allow_count": self._metrics.contention_degraded_allow_count,
                "contention_admitted_count": self._metrics.contention_admitted_count,
                "contention_timeout_count": self._metrics.contention_timeout_count,
                # J4c: incremented in evaluate() but was never surfaced here, so the
                # only counter that reports "the N-way layer overrode pairwise" was
                # unreadable by /dashboard and by any exporter. Write-only telemetry
                # is the same as none.
                "contention_nway_restricted_count": self._metrics.contention_nway_restricted_count,
                "active_decodes_by_role": dict(self._metrics.active_decodes_by_role),
                "active_instances_by_role": {r: list(idxs) for r, idxs in self._metrics.active_instances_by_role.items()},
                "matrix_status": self.matrix_health().value,
            }


# ── singleton accessor ──────────────────────────────────────────────

_GATE_SINGLETON: ContentionGate | None = None
_GATE_SINGLETON_LOCK = threading.Lock()


def get_gate() -> ContentionGate:
    """Process-wide ContentionGate. Lazy-init so import is cheap."""
    global _GATE_SINGLETON
    if _GATE_SINGLETON is None:
        with _GATE_SINGLETON_LOCK:
            if _GATE_SINGLETON is None:
                _GATE_SINGLETON = ContentionGate()
    return _GATE_SINGLETON


def reset_gate() -> None:
    """Test helper: reset the singleton."""
    global _GATE_SINGLETON
    with _GATE_SINGLETON_LOCK:
        _GATE_SINGLETON = None


class ContentionDenied(RuntimeError):
    """Raised by `_real_call_impl` when the gate denies admission past the deadline.

    Callers (chat route) should surface this as a 503 with `Retry-After`
    rather than propagating to the user as an unhandled 500.

    ``failure_provenance`` is intentionally a closed, JSON-primitive record.
    Consumers must use it instead of classifying the human-readable exception
    message.  A request never reaches generation when this exception is raised.
    """

    FAILURE_PROVENANCE_SCHEMA = "epyc.failure_provenance.v1"

    def __init__(
        self,
        detail: str,
        *,
        role: str = "unknown",
        workload_class: str = "interactive",
        wait_budget_ms: int = 0,
        failure_class: str = "admission_denied",
        code: str = "contention_denied",
    ) -> None:
        super().__init__(detail)
        self.failure_provenance = self._build_failure_provenance(
            role=role,
            workload_class=workload_class,
            wait_budget_ms=wait_budget_ms,
            failure_class=failure_class,
            code=code,
        )

    @classmethod
    def _build_failure_provenance(
        cls,
        *,
        role: str,
        workload_class: str,
        wait_budget_ms: int,
        failure_class: str,
        code: str,
    ) -> dict[str, str | int | bool]:
        """Build the closed v1 admission-denial contract.

        Keep the type checks here rather than relying on downstream schema
        validation: producer bugs must fail locally, before an ambiguous row
        can become durable evidence.
        """
        string_fields = {
            "role": role,
            "workload_class": workload_class,
            "class": failure_class,
            "code": code,
        }
        for field_name, value in string_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"failure provenance {field_name} must be a non-empty string")
        if failure_class not in {"admission_denied", "admission_timeout"}:
            raise ValueError("failure provenance class is not a supported admission outcome")
        # ``race_lost`` is a narrow physical fact, not a generic timeout label.
        # Keeping this pair closed prevents another producer from accidentally
        # minting E8-eligible recovery evidence for an ordinary gate timeout.
        if (failure_class, code) == ("admission_timeout", "race_lost"):
            pass
        elif failure_class == "admission_timeout" or code == "race_lost":
            raise ValueError(
                "failure provenance admission_timeout is reserved for code=race_lost"
            )
        if isinstance(wait_budget_ms, bool) or not isinstance(wait_budget_ms, int):
            raise TypeError("failure provenance wait_budget_ms must be an integer")
        if wait_budget_ms < 0:
            raise ValueError("failure provenance wait_budget_ms must be non-negative")
        return {
            "schema": cls.FAILURE_PROVENANCE_SCHEMA,
            "class": failure_class,
            "code": code,
            "phase": "admission",
            "role": role,
            "workload_class": workload_class,
            "max_queue_wait_ms": wait_budget_ms,
            "generation_started": False,
            "tokens_generated": 0,
            "partial": False,
            "degraded": False,
        }

    def provenance(self) -> dict[str, str | int | bool]:
        """Return a copy so callers cannot mutate the exception contract."""
        return dict(self.failure_provenance)

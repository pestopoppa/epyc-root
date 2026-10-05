"""Per-backend admission control using asyncio semaphores.

Prevents request pile-up on slow backends (especially architects) by limiting
concurrent in-flight requests per backend URL. When a backend's queue is full,
requests are rejected immediately with a clear error rather than blocking
until timeout.

OBSERVATION (2026-02-20): Slot/Admission Alignment
===================================================
Key finding from backend saturation investigation (handoffs/active/backend-saturation-504-429.md):
Every backend had 2x more llama-server slots than admission controller allowed. llama-server
partitions KV cache evenly across all slots, so 50% of KV cache was wasted on idle slots.

Concurrency sweep results (concurrent_sweep_20260219_144159.summary.json) showed:
- frontdoor: optimal at concurrency=2, p95 latency 1.33x (acceptable)
- coder_escalation: p95 latency 1.98x at concurrency=2 (degradation) — reduced to serial
- worker: ALL concurrent levels (2,3,4) rejected on p95 threshold — reduced to serial
- architects: already serial

Changes applied:
  - Aligned admission limits with llama-server slot counts (no idle slots)
  - Reduced coder_escalation from 2→1 and worker from 4→1 based on sweep data
  - Also updated orchestration/model_registry.yaml server_mode slot counts
  - Increased frontdoor timeout from 90→180s in model_registry.yaml

Expected impact: 50% reduction in idle KV cache pressure across all backends.

See DEFAULT_LIMITS comments for per-backend rationale.

Usage:
    controller = AdmissionController.from_defaults()
    if not controller.try_acquire(backend_url):
        raise RuntimeError("Backend queue full")
    try:
        result = do_inference(backend_url, ...)
    finally:
        controller.release(backend_url)
"""

from __future__ import annotations

import logging
from pathlib import Path
import threading
import time

from src.registry.stack_priors import (
    live_stack_serving_slot_limits,
)

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STACK_PRIORS_PATH = PROJECT_ROOT / "orchestration" / "derived" / "stack_priors.yaml"

# Embedding servers (8090-8095) are not gated — they're lightweight.


def _limits_from_stack_priors(path: Path = STACK_PRIORS_PATH) -> dict[str, int]:
    return live_stack_serving_slot_limits(path)


def _manifest_server_slots(server: dict[str, object], serial_roles: set[str]) -> int:
    roles = server.get("roles")
    primary_role = roles[0] if isinstance(roles, list) and roles else None
    if server.get("worker_pool") is True:
        return 4 if server.get("worker_type") == "fast" else 1
    if server.get("vision") is True:
        return 1 if server.get("vision_type") == "escalation" else 2
    if isinstance(primary_role, str) and primary_role in serial_roles:
        return 1
    return 2


def _limits_from_stack_manifest() -> dict[str, int]:
    """Return degraded admission limits from the computed stack manifest."""
    try:
        from scripts.server.stack_manifest import HOT_SERVERS, SERIAL_ROLES, WARM_SERVERS
    except Exception:
        logger.warning("Stack manifest admission fallback unavailable", exc_info=True)
        return {}

    limits: dict[str, int] = {}
    serial_roles = set(SERIAL_ROLES)
    for server in [*HOT_SERVERS, *WARM_SERVERS]:
        if not isinstance(server, dict):
            continue
        if server.get("embedding") is True:
            continue
        port = server.get("port")
        if not isinstance(port, int):
            continue
        limits[f"http://localhost:{port}"] = _manifest_server_slots(server, serial_roles)
    return limits


# Compatibility export for tests and callers that inspect degraded defaults.
# _load_default_limits() recomputes from the manifest at call time.
FALLBACK_LIMITS: dict[str, int] = _limits_from_stack_manifest()


def _load_default_limits(path: Path = STACK_PRIORS_PATH) -> dict[str, int]:
    try:
        limits = _limits_from_stack_priors(path)
    except (OSError, AttributeError, TypeError):
        logger.warning("Falling back to stack-manifest admission limits", exc_info=True)
        return _limits_from_stack_manifest()
    if limits:
        return limits
    logger.warning("Falling back to stack-manifest admission limits; no stack-prior limits found")
    return _limits_from_stack_manifest()


DEFAULT_LIMITS: dict[str, int] = _load_default_limits()


class AdmissionController:
    """Thread-safe per-backend concurrency limiter.

    Uses threading.Semaphore (not asyncio.Semaphore) because inference calls
    happen in thread pool via asyncio.to_thread / inference_lock (fcntl).
    """

    def __init__(self, limits: dict[str, int] | None = None):
        self._limits = dict(limits) if limits is not None else _load_default_limits()
        self._semaphores: dict[str, threading.Semaphore] = {
            url: threading.Semaphore(n) for url, n in self._limits.items()
        }
        self._lock = threading.Lock()
        self._waiting: dict[str, dict[str, int]] = {
            url: {"interactive": 0, "background": 0}
            for url in self._limits
        }

    @classmethod
    def from_defaults(cls) -> AdmissionController:
        return cls(_load_default_limits())

    def _norm_priority(self, priority: str | None) -> str:
        p = str(priority or "interactive").strip().lower()
        return "background" if p == "background" else "interactive"

    def acquire(
        self,
        backend_url: str,
        *,
        priority: str = "interactive",
        wait: bool = False,
        timeout_s: float | None = None,
        deadline_s: float | None = None,
        cancel_check=None,
        poll_s: float = 0.02,
    ) -> bool:
        """Acquire admission slot with optional bounded wait.

        Interactive requests are prioritized over background requests when
        waiters exist on the same backend.
        """
        sem = self._semaphores.get(backend_url)
        if sem is None:
            return True

        prio = self._norm_priority(priority)
        start = time.perf_counter()
        waited = False
        with self._lock:
            q = self._waiting.setdefault(
                backend_url, {"interactive": 0, "background": 0}
            )
            q[prio] = q.get(prio, 0) + 1
            waited = True
        try:
            while True:
                if cancel_check is not None:
                    try:
                        if cancel_check():
                            return False
                    except Exception:
                        pass
                now = time.perf_counter()
                if deadline_s is not None and now >= deadline_s:
                    return False
                if timeout_s is not None and (now - start) >= max(0.0, timeout_s):
                    return False

                with self._lock:
                    waiting_interactive = self._waiting.get(backend_url, {}).get(
                        "interactive", 0
                    )
                # Keep one slot path open for interactive arrivals while background waits.
                if prio == "background" and waiting_interactive > 0:
                    if not wait:
                        return False
                    time.sleep(poll_s)
                    continue

                if sem.acquire(blocking=False):
                    return True

                if not wait:
                    return False
                time.sleep(poll_s)
        finally:
            if waited:
                with self._lock:
                    q = self._waiting.setdefault(
                        backend_url, {"interactive": 0, "background": 0}
                    )
                    q[prio] = max(0, q.get(prio, 0) - 1)

    def try_acquire(self, backend_url: str) -> bool:
        """Non-blocking acquire. Returns True if admitted, False if queue full."""
        acquired = self.acquire(backend_url, wait=False)
        if not acquired:
            logger.warning(
                "Admission rejected for %s (limit=%d)",
                backend_url,
                self._limits.get(backend_url, 0),
            )
        return acquired

    def release(self, backend_url: str) -> None:
        """Release a slot for the backend."""
        sem = self._semaphores.get(backend_url)
        if sem is not None:
            sem.release()

    def get_status(self) -> dict[str, dict[str, int]]:
        """Return current admission status per backend."""
        status = {}
        for url, sem in self._semaphores.items():
            limit = self._limits.get(url, 0)
            # Semaphore._value is the current counter (available slots)
            available = sem._value  # type: ignore[attr-defined]
            with self._lock:
                waiting = self._waiting.get(url, {})
            status[url] = {
                "limit": limit,
                "available": available,
                "in_flight": limit - available,
                "waiting_interactive": int(waiting.get("interactive", 0)),
                "waiting_background": int(waiting.get("background", 0)),
            }
        return status


# Shared (unified) KV pool admission lives in src/scheduling/kv_pool_admission.py
# (importable without pulling in the FastAPI app); re-exported here because it
# is admission control.
from src.scheduling.kv_pool_admission import (  # noqa: E402,F401
    DEFAULT_KV_POOL_MAX_QUEUED,
    DEFAULT_KV_POOL_WAIT_S,
    KV_POOL_MAX_QUEUED_ENV,
    KV_POOL_WAIT_ENV,
    KVPoolQueueFull,
    SharedKVPoolAdmission,
    get_shared_pool_admission,
)

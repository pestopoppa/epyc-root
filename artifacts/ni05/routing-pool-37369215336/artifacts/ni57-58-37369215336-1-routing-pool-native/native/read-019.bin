"""Server lifecycle: health checks, idle enforcement, preflight, recovery.

Imports only seeding_types — no other project modules.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any

from seeding_types import (
    DEFAULT_ORCHESTRATOR_URL,
    HEAVY_PORTS,
    MODEL_PORTS,
    PROJECT_ROOT,
    STACK_SCRIPT,
    state,
)

__all__ = [
    "MAX_RECOVERY_ATTEMPTS",
    "get_preflight_diagnostics",
    "run_preflight",
]

logger = logging.getLogger(__name__)

MAX_RECOVERY_ATTEMPTS = 10
STACK_CHANGE_GATE_ENV = "EPYC_SEEDING_PREFLIGHT_STACK_CHANGE_GATE"
_preflight_diagnostics: dict[str, Any] = {
    "api_health": {},
    "idle_probes": {},
    "last_preflight": {},
}


def _record_diag(section: str, key: str, payload: dict[str, Any]) -> None:
    bucket = _preflight_diagnostics.setdefault(section, {})
    bucket[key] = {
        **payload,
        "checked_at": time.time(),
    }


def _set_preflight_state(
    status: str,
    *,
    stage: str = "",
    failure_reason: str = "",
    failure_detail: str = "",
) -> None:
    payload = _preflight_diagnostics.setdefault("last_preflight", {})
    payload["status"] = status
    payload["stage"] = stage
    payload["failure_reason"] = failure_reason
    payload["failure_detail"] = failure_detail
    payload["updated_at"] = time.time()


def get_preflight_diagnostics() -> dict[str, Any]:
    """Return the latest compatibility-safe preflight diagnostics."""
    return {
        "api_health": dict(_preflight_diagnostics.get("api_health", {})),
        "idle_probes": {
            str(port): dict(data)
            for port, data in _preflight_diagnostics.get("idle_probes", {}).items()
        },
        "last_preflight": dict(_preflight_diagnostics.get("last_preflight", {})),
    }


# ── Health / idle checks ─────────────────────────────────────────────


def _check_server_health(url: str, timeout: int = 5) -> bool:
    """Check if the orchestrator server is healthy."""
    try:
        resp = state.get_poll_client().get(f"{url}/health", timeout=timeout)
        ok = resp.status_code == 200
        _record_diag(
            "api_health",
            url,
            {
                "ok": ok,
                "status_code": resp.status_code,
                "failure_reason": "" if ok else "http_status",
                "failure_detail": "" if ok else f"status={resp.status_code}",
            },
        )
        return ok
    except Exception as e:
        _record_diag(
            "api_health",
            url,
            {
                "ok": False,
                "status_code": None,
                "failure_reason": type(e).__name__,
                "failure_detail": str(e),
            },
        )
        return False


def _is_server_idle(port: int, timeout: int = 3) -> bool:
    """Check if all slots on a llama-server port are idle."""
    try:
        resp = state.get_poll_client().get(f"http://localhost:{port}/slots", timeout=timeout)
        if resp.status_code != 200:
            _record_diag(
                "idle_probes",
                str(port),
                {
                    "idle": True,
                    "assumed_idle": True,
                    "status_code": resp.status_code,
                    "failure_reason": "http_status",
                    "failure_detail": f"status={resp.status_code}",
                },
            )
            return True  # Can't check — assume idle
        slots = resp.json()
        idle = not any(s.get("is_processing", False) for s in slots)
        _record_diag(
            "idle_probes",
            str(port),
            {
                "idle": idle,
                "assumed_idle": False,
                "status_code": resp.status_code,
                "failure_reason": "",
                "failure_detail": "",
                "slots_seen": len(slots) if isinstance(slots, list) else 0,
            },
        )
        return idle
    except Exception as e:
        _record_diag(
            "idle_probes",
            str(port),
            {
                "idle": True,
                "assumed_idle": True,
                "status_code": None,
                "failure_reason": type(e).__name__,
                "failure_detail": str(e),
            },
        )
        return True  # Server unreachable — assume idle


def _latest_api_probe(url: str) -> dict[str, Any]:
    return dict(_preflight_diagnostics.get("api_health", {}).get(url, {}))


def _latest_idle_probe(port: int) -> dict[str, Any]:
    return dict(_preflight_diagnostics.get("idle_probes", {}).get(str(port), {}))


def _wait_for_heavy_models_idle(max_wait: int = 600) -> None:
    """Block until ALL heavy model servers are idle.

    Called before every combo to ensure no concurrent heavy inference.
    Light/fast workers (8080-8082, 8086) are allowed to overlap.
    """
    start = time.perf_counter()
    while True:
        all_idle = True
        busy_ports = []
        for port in HEAVY_PORTS:
            if not _is_server_idle(port):
                all_idle = False
                busy_ports.append(port)
        if all_idle:
            elapsed = time.perf_counter() - start
            if elapsed > 1.0:
                logger.info(f"  [idle-wait] Heavy models idle after {elapsed:.1f}s")
            return
        if time.perf_counter() - start > max_wait:
            logger.warning(
                f"  [idle-wait] Timeout after {max_wait}s, ports still busy: {busy_ports}"
            )
            return
        if state.shutdown:
            return
        time.sleep(2)


def _wait_for_workers_ready(
    url: str,
    *,
    max_wait: int = 180,
    cpu_threshold: float = 10.0,
    settle_checks: int = 2,
) -> None:
    """Block until all uvicorn workers have finished lifespan init.

    During startup, workers loading FAISS / Kuzu burn 80%+ CPU for ~70s.
    HTTP health pings can't detect this because the kernel routes to
    already-ready workers.  Instead we find the uvicorn parent on port 8000
    and poll its children's CPU usage via /proc.  Workers are "ready" when
    all children are below ``cpu_threshold`` for ``settle_checks`` consecutive
    polls.
    """
    import subprocess

    # Find uvicorn parent PID on port 8000
    try:
        result = subprocess.run(
            ["lsof", "-ti", "tcp:8000", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=5,
        )
        pids = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        if not pids:
            logger.debug("  No process found on port 8000 — skipping worker wait")
            return
        parent_pid = pids[0]
    except Exception:
        logger.debug("  Could not determine uvicorn parent PID — skipping worker wait")
        return

    def _children_cpu(ppid: str) -> list[tuple[str, float]]:
        """Return [(pid, cpu%)] for children of ppid."""
        try:
            result = subprocess.run(
                ["ps", "--ppid", ppid, "-o", "pid=,%cpu="],
                capture_output=True, text=True, timeout=5,
            )
            pairs = []
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2:
                    pairs.append((parts[0], float(parts[1])))
            return pairs
        except Exception:
            return []

    # Find the DequeHandler (if TUI is active) so we can update a single
    # log line in-place instead of spamming new entries every 3s.
    deque_handler = None
    for h in logging.getLogger().handlers:
        if type(h).__name__ == "DequeHandler" and hasattr(h, "records"):
            deque_handler = h
            break

    def _status_update(msg: str) -> None:
        """Log msg, reusing the last deque entry in TUI mode."""
        if deque_handler is not None and deque_handler.records:
            last = deque_handler.records[-1]
            # Only overwrite our own status lines (contain "workers")
            if "workers" in last.lower():
                deque_handler.records[-1] = msg
                return
        logger.info(msg)

    start = time.perf_counter()
    settled = 0
    while time.perf_counter() - start < max_wait:
        children = _children_cpu(parent_pid)
        if not children:
            # Single-worker uvicorn (--workers 1) doesn't fork — the parent
            # IS the worker.  Treat the parent process itself as the sole
            # worker so we don't loop for 180s waiting for children that
            # will never appear.
            try:
                result = subprocess.run(
                    ["ps", "-o", "pid=,%cpu=", "-p", parent_pid],
                    capture_output=True, text=True, timeout=5,
                )
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    children = [(parts[0], float(parts[1]))]
            except Exception:
                pass
            if not children:
                time.sleep(2)
                continue
        max_cpu = max(cpu for _, cpu in children)
        if max_cpu < cpu_threshold:
            settled += 1
            if settled >= settle_checks:
                elapsed = time.perf_counter() - start
                if elapsed > 5.0:
                    _status_update(
                        f"  Workers stabilized after {elapsed:.1f}s (max CPU={max_cpu:.1f}%)"
                    )
                return
        else:
            settled = 0
            elapsed = time.perf_counter() - start
            hot = [cpu for _, cpu in children if cpu >= cpu_threshold]
            _status_update(
                f"  Workers init: {len(hot)}/{len(children)} hot"
                f" (CPU={max_cpu:.0f}%, {elapsed:.0f}s)"
            )
        if state.shutdown:
            return
        time.sleep(3)
    logger.warning(
        "  Workers may still be initializing after %ds — proceeding anyway",
        max_wait,
    )


# ── Port / process management ────────────────────────────────────────


def _check_port(port: int) -> bool:
    """Check if a port is listening (sandbox-safe, no raw sockets)."""
    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen(f"http://localhost:{port}/health", timeout=3)
        return True
    except urllib.error.URLError as e:
        if "Connection refused" in str(e):
            return False
        # Any other URLError (404, 500, etc.) means port is up
        return True
    except Exception:
        # Any response means port is listening
        return True


def _kill_port(port: int) -> bool:
    """Kill the process listening on a port. Returns True if killed."""
    import subprocess

    subprocess.run(
        ["fuser", "-k", f"{port}/tcp"],
        capture_output=True,
        timeout=10,
    )
    time.sleep(1)
    return not _check_port(port)


# ── Launcher helpers ─────────────────────────────────────────────────


def _launch_api_only() -> bool:
    """Launch just the orchestrator API (uvicorn on port 8000).

    Used when model servers are already running but the API is not.
    If port 8000 is already taken by a stale process, kills it first.
    """
    import subprocess

    # Kill stale API process if port 8000 is occupied
    if _check_port(8000):
        logger.warning("  Port 8000 already in use — killing stale process...")
        if not _kill_port(8000):
            logger.error("  Could not free port 8000")
            return False
        logger.info("  Port 8000 freed")

    logger.info("  Launching orchestrator API only (model servers already running)...")

    env = os.environ.copy()
    env["HF_HOME"] = "/mnt/raid0/llm/cache/huggingface"
    env["TMPDIR"] = "/mnt/raid0/llm/tmp"
    env["ORCHESTRATOR_CACHING"] = "1"
    env["ORCHESTRATOR_STREAMING"] = "1"
    env["ORCHESTRATOR_MOCK_MODE"] = "0"
    env["ORCHESTRATOR_REAL_MODE"] = "1"
    env["ORCHESTRATOR_SCRIPTS"] = "1"
    env["ORCHESTRATOR_REACT_MODE"] = "1"
    env["ORCHESTRATOR_MEMRL"] = "1"
    env["ORCHESTRATOR_TOOLS"] = "1"
    env["ORCHESTRATOR_GENERATION_MONITOR"] = "1"
    env["ORCHESTRATOR_CASCADING_TOOL_POLICY"] = "1"

    log_file = PROJECT_ROOT / "logs" / "orchestrator_autolaunch.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    workers = int(os.environ.get("ORCHESTRATOR_UVICORN_WORKERS", "2"))
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.api:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--workers", str(workers),
        ],
        cwd=str(PROJECT_ROOT),
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        env=env,
    )

    # Wait for API to become healthy — verify OUR process is still alive
    for attempt in range(24):  # Up to 2 minutes
        if proc.poll() is not None:
            logger.error(f"  API process exited (code={proc.returncode}). Check log: {log_file}")
            return False
        if _check_server_health(DEFAULT_ORCHESTRATOR_URL):
            logger.info(f"  API healthy (pid={proc.pid}) after {(attempt + 1) * 5}s")
            return True
        time.sleep(5)

    logger.error(f"  API did not start. Check log: {log_file}")
    proc.kill()
    return False


def _auto_launch_stack(hot_only: bool = True) -> bool:
    """Launch the full orchestrator stack and wait for it to become healthy.

    Only called when NO ports are in use (cold start).
    Returns True if the stack came up successfully.
    """
    import subprocess

    if not STACK_SCRIPT.exists():
        logger.error(f"  Stack script not found: {STACK_SCRIPT}")
        return False

    cmd = [sys.executable, str(STACK_SCRIPT), "start"]
    if hot_only:
        cmd.append("--hot-only")

    logger.info(f"  Auto-launching full stack: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"  Stack launch failed (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[-5:]:
                    logger.error(f"    {line}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("  Stack launch timed out after 600s")
        return False

    # Wait for API to become healthy
    logger.info("  Waiting for API to become healthy...")
    for attempt in range(60):  # Up to 5 minutes
        if _check_server_health(DEFAULT_ORCHESTRATOR_URL):
            logger.info(f"  API healthy after {(attempt + 1) * 5}s")
            return True
        time.sleep(5)

    logger.error("  API did not become healthy within 5 minutes")
    return False


# ── Stack-change gate ────────────────────────────────────────────────


def _run_stack_change_gate() -> bool:
    """Fail closed if generated stack truth or promotion checks are stale.

    Benchmark preflight can launch the API directly when model ports are already
    up, bypassing ``orchestrator_stack.py start``. Run the same no-inference
    promotion gate here before any API/model probes. The child process disables
    this benchmark-preflight hook so promotion-gate unit tests do not
    recursively invoke themselves.
    """
    import subprocess

    if os.environ.get(STACK_CHANGE_GATE_ENV, "1") == "0":
        logger.info("  Stack-change gate skipped via %s=0", STACK_CHANGE_GATE_ENV)
        return True

    script = PROJECT_ROOT / "scripts" / "registry" / "stack_change_pipeline.py"
    cmd = [sys.executable, str(script), "check", "--run-promotion-gate"]
    env = os.environ.copy()
    env[STACK_CHANGE_GATE_ENV] = "0"
    logger.info("  Stack-change gate: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("  Stack-change gate timed out after %.0fs", exc.timeout or 180)
        return False
    except Exception as exc:
        logger.error("  Stack-change gate failed to launch: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("  Stack-change gate: OK")
        return True

    logger.error("  Stack-change gate failed (exit %s)", result.returncode)
    tail = (result.stderr or result.stdout or "").strip().splitlines()[-8:]
    for line in tail:
        logger.error("    %s", line)
    return False


# ── Recovery ─────────────────────────────────────────────────────────


def _attempt_recovery(url: str) -> bool:
    """Attempt to recover a dead orchestrator API.

    Checks what's still running and takes the minimal action:
    - Model ports up -> restart API only (kills stale process on :8000)
    - Nothing up -> full stack launch

    After relaunch, waits for all workers to stabilize before returning.
    """
    model_ports_up = sum(1 for p in MODEL_PORTS if _check_port(p))

    if model_ports_up > 0:
        logger.info(
            f"  Recovery: {model_ports_up} model port(s) still up — restarting API only"
        )
        ok = _launch_api_only()
    else:
        logger.info("  Recovery: no model ports up — launching full stack")
        ok = _auto_launch_stack()
    if ok:
        _wait_for_workers_ready(url)
    return ok


# ── Preflight ────────────────────────────────────────────────────────


def run_preflight(url: str, restart_api: bool = True) -> bool:
    """Run preflight health checks on orchestrator and backends.

    Auto-launches the orchestrator stack if the API is not reachable.
    If restart_api=True (default), restarts the API to pick up code changes.
    Returns True if all checks pass.
    """
    logger.info("=" * 60)
    logger.info("PREFLIGHT CHECKS")
    logger.info("=" * 60)
    _preflight_diagnostics["last_preflight"] = {
        "url": url,
        "restart_api": restart_api,
        "started_at": time.time(),
        "status": "running",
        "stage": "startup",
        "failure_reason": "",
        "failure_detail": "",
    }

    _set_preflight_state("running", stage="stack_change_gate")
    if not _run_stack_change_gate():
        logger.error("PREFLIGHT FAILED: Stack-change gate failed")
        _set_preflight_state(
            "failed",
            stage="stack_change_gate",
            failure_reason="stack_change_gate_failed",
            failure_detail=(
                f"{PROJECT_ROOT / 'scripts' / 'registry' / 'stack_change_pipeline.py'} "
                "check --run-promotion-gate"
            ),
        )
        return False

    # 0. Restart API if requested (ensures code changes are picked up)
    if restart_api and _check_port(8000):
        logger.info("  Restarting API to pick up code changes...")
        if _kill_port(8000):
            logger.info("  API stopped, will relaunch below")
            time.sleep(2)
        else:
            logger.warning("  Could not stop API cleanly — continuing anyway")

    # 1. Orchestrator API health (auto-launch if down)
    api_healthy = _check_server_health(url)
    model_ports_up = sum(1 for p in MODEL_PORTS if _check_port(p))
    api_probe = _latest_api_probe(url)

    if api_healthy:
        logger.info(f"  API already running ({url})")
    elif model_ports_up > 0:
        logger.info(
            f"  API not reachable but {model_ports_up} model port(s) are up "
            f"— launching API only..."
        )
        if not _launch_api_only():
            logger.error("PREFLIGHT FAILED: Could not start orchestrator API")
            _set_preflight_state(
                "failed",
                stage="api_launch",
                failure_reason="api_launch_failed",
                failure_detail=f"model_ports_up={model_ports_up}",
            )
            return False
    else:
        logger.info("  No stack running — launching full stack...")
        if not _auto_launch_stack():
            logger.error("PREFLIGHT FAILED: Could not start orchestrator stack")
            _set_preflight_state(
                "failed",
                stage="stack_launch",
                failure_reason="stack_launch_failed",
                failure_detail="no_model_ports_up",
            )
            return False
    logger.info(f"  API health: OK ({url})")
    _set_preflight_state("running", stage="backend_health")
    if api_probe and not api_healthy:
        logger.info(
            "  API recovery path: reason=%s detail=%s",
            api_probe.get("failure_reason", "unknown"),
            api_probe.get("failure_detail", ""),
        )

    # 2. Backend health (check ports via /health on orchestrator)
    try:
        resp = state.get_poll_client().get(f"{url}/health", timeout=10)
        if resp.status_code == 200:
            health_data = resp.json()
            backends = health_data.get("backends", {})
            if backends:
                for name, status in backends.items():
                    ok = status.get("healthy", False) if isinstance(status, dict) else status
                    tag = "OK" if ok else "DOWN"
                    logger.info(f"  Backend {name}: {tag}")
    except Exception:
        pass  # Health endpoint may not expose backends — continue

    # 3. Smoke test (60s timeout — if 2+2 takes longer, something is broken)
    _set_preflight_state("running", stage="smoke_test")
    logger.info("  Smoke test: 2+2...")
    try:
        resp = state.get_poll_client().post(
            f"{url}/chat",
            json={"prompt": "What is 2+2? Answer with just the number.", "real_mode": True},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "")[:50]
            routed_to = data.get("routed_to", "unknown")
            logger.info(f"  Smoke test OK: routed_to={routed_to}, answer={answer}")
        else:
            logger.error(f"  Smoke test FAIL: HTTP {resp.status_code}")
            _set_preflight_state(
                "failed",
                stage="smoke_test",
                failure_reason="http_status",
                failure_detail=f"status={resp.status_code}",
            )
            return False
    except Exception as e:
        if "timeout" in str(e).lower() or "Timeout" in type(e).__name__:
            logger.error("  Smoke test TIMEOUT (60s) — API may be misconfigured for real_mode")
            logger.error("  Try: kill API on :8000 and relaunch, or check orchestrator_autolaunch.log")
            failure_reason = "timeout"
        else:
            logger.error(f"  Smoke test FAIL: {e}")
            failure_reason = type(e).__name__
        _set_preflight_state(
            "failed",
            stage="smoke_test",
            failure_reason=failure_reason,
            failure_detail=str(e),
        )
        return False

    # 4. Wait for all workers to finish initializing (FAISS / Kuzu loading)
    _set_preflight_state("running", stage="worker_stabilization")
    logger.info("  Waiting for all workers to stabilize...")
    _wait_for_workers_ready(url)

    logger.info("PREFLIGHT PASSED")
    logger.info("=" * 60)
    _set_preflight_state("passed", stage="completed")
    _preflight_diagnostics["last_preflight"]["completed_at"] = time.time()
    return True

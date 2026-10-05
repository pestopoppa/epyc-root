#!/usr/bin/env python3
"""Heterogeneous worker pool for parallel task execution.

Manages multiple llama-server instances with different models optimized
for different task types:
- explore (7B): Directory crawling, file summaries, codebase understanding
- code (7B): Code implementation, following architect instructions
- fast (1.5B): Simple transformations, boilerplate, high-volume parallel

Architecture:
- HOT workers: Always resident, immediate availability
- WARM workers: Loaded on demand for burst capacity

Usage:
    pool = WorkerPoolManager()
    await pool.start_hot_workers()

    # Single call
    result = await pool.call("Summarize this file", task_type="explore")

    # Batch call (auto-routes and parallelizes)
    results = await pool.batch(prompts, task_type="explore")
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiohttp

from src.config import _registry_timeout

logger = logging.getLogger(__name__)

# Worker pool HTTP client timeouts from registry
_POOL_CLIENT_TOTAL = int(_registry_timeout("pools", "client_total", 300))
_POOL_CLIENT_CONNECT = int(_registry_timeout("pools", "client_connect", 10))


class WorkerTier(Enum):
    """Worker availability tier."""

    HOT = "hot"  # Always resident
    WARM = "warm"  # Load on demand


class TaskType(Enum):
    """Task types for routing."""

    EXPLORE = "explore"  # Understanding, summarization
    CODE = "code"  # Code implementation
    FAST = "fast"  # Simple transformations
    SUMMARIZE = "summarize"  # Alias for explore
    UNDERSTAND = "understand"  # Alias for explore
    CODE_IMPL = "code_impl"  # Alias for code
    REFACTOR = "refactor"  # Alias for code
    TEST_GEN = "test_gen"  # Alias for code
    BOILERPLATE = "boilerplate"  # Alias for fast
    TRANSFORM = "transform"  # Alias for fast


# Task type to worker role mapping
TASK_ROUTING = {
    TaskType.EXPLORE: "explore",
    TaskType.SUMMARIZE: "explore",
    TaskType.UNDERSTAND: "explore",
    TaskType.CODE: "code",
    TaskType.CODE_IMPL: "code",
    TaskType.REFACTOR: "code",
    TaskType.TEST_GEN: "code",
    TaskType.FAST: "fast",
    TaskType.BOILERPLATE: "fast",
    TaskType.TRANSFORM: "fast",
}


@dataclass
class WorkerConfig:
    """Configuration for a single worker instance."""

    name: str
    port: int
    model_path: str
    tier: WorkerTier
    threads: int = 24
    slots: int = 2
    task_types: list[str] = field(default_factory=list)
    launch_flags: list[str] = field(default_factory=list)
    managed_process: bool = True


@dataclass
class WorkerInstance:
    """Running worker instance state."""

    config: WorkerConfig
    process: Optional[subprocess.Popen] = None
    started_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    _healthy: bool = False

    @property
    def is_running(self) -> bool:
        """Check if worker process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def url(self) -> str:
        """Get worker HTTP URL."""
        return f"http://localhost:{self.config.port}"


def _wp_default_server_path() -> str:
    from src.config import get_config

    return str(get_config().worker_pool.llama_server_path)


def _wp_default_log_dir() -> str:
    from src.config import get_config

    return str(get_config().worker_pool.log_dir)


@dataclass
class WorkerPoolConfig:
    """Configuration for the entire worker pool.

    Timeout defaults from model_registry.yaml (runtime_defaults.timeouts).
    """

    enabled: bool = True
    prompt_lookup: bool = True
    warm_timeout_seconds: int = field(
        default_factory=lambda: int(_registry_timeout("pools", "warm_keepalive", 300))
    )
    expansion_threshold: int = 4  # Concurrent tasks to trigger WARM expansion
    health_check_interval: int = 30
    llama_server_path: str = field(default_factory=_wp_default_server_path)
    log_dir: str = field(default_factory=_wp_default_log_dir)

    workers: dict[str, WorkerConfig] = field(default_factory=dict)


class WorkerPoolManager:
    """Manages a heterogeneous pool of llama-server worker instances.

    Provides intelligent routing based on task type and load balancing
    across multiple workers.
    """

    def __init__(self, config: Optional[WorkerPoolConfig] = None):
        """Initialize the worker pool manager.

        Args:
            config: Pool configuration. If None, uses defaults from registry.
        """
        self.config = config or self._load_default_config()
        self._workers: dict[str, WorkerInstance] = {}
        self._hot_workers: dict[str, WorkerInstance] = {}
        self._warm_workers: dict[str, WorkerInstance] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._round_robin_idx: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._warm_shutdown_tasks: dict[str, asyncio.Task] = {}
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    def _load_default_config(self) -> WorkerPoolConfig:
        """Load default configuration, preferring generated stack-prior truth."""
        from src.config import get_config

        derived = self._load_stack_prior_config()
        if derived is not None:
            return derived

        model_base = str(get_config().paths.model_base)
        return WorkerPoolConfig(
            workers={
                "explore": WorkerConfig(
                    name="explore",
                    port=8082,
                    model_path=f"{model_base}/Qwen/Qwen2.5-7B-Instruct-GGUF/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
                    tier=WorkerTier.HOT,
                    threads=24,
                    slots=2,
                    task_types=["explore", "summarize", "understand"],
                ),
                "code": WorkerConfig(
                    name="code",
                    port=8092,
                    model_path=f"{model_base}/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
                    tier=WorkerTier.HOT,
                    threads=24,
                    slots=2,
                    task_types=["code_impl", "refactor", "test_gen"],
                ),
                "fast": WorkerConfig(
                    name="fast",
                    port=8102,
                    model_path=f"{model_base}/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf",
                    tier=WorkerTier.WARM,
                    threads=16,
                    slots=4,
                    task_types=["boilerplate", "transform", "parallel_burst"],
                ),
            }
        )

    def _load_stack_prior_config(self) -> WorkerPoolConfig | None:
        """Build a pool config that attaches to live stack-prior workers.

        The production stack owns those llama-server processes. WorkerPoolManager
        should use them as HTTP backends, not restart or kill their ports.
        """
        try:
            from src.registry.stack_priors import (
                live_stack_role_records,
                stack_prior_launch,
                stack_prior_primary_port,
            )
        except Exception:
            return None

        records = live_stack_role_records()
        worker = records.get("worker_general")
        if not isinstance(worker, dict):
            return None

        serving = worker.get("serving")
        if not isinstance(serving, dict):
            return None
        port = stack_prior_primary_port(serving)
        if not isinstance(port, int):
            return None

        launch = stack_prior_launch(worker)
        requirements = launch.get("requirements")
        model_path = (
            requirements.get("model_path")
            if isinstance(requirements, dict)
            else None
        )
        if not isinstance(model_path, str) or not model_path:
            return None

        slots = serving.get("slots")
        return WorkerPoolConfig(
            workers={
                "worker_general": WorkerConfig(
                    name="worker_general",
                    port=port,
                    model_path=model_path,
                    tier=WorkerTier.HOT,
                    slots=slots if isinstance(slots, int) and slots > 0 else 1,
                    task_types=[
                        "explore",
                        "summarize",
                        "understand",
                        "code",
                        "code_impl",
                        "refactor",
                        "test_gen",
                        "fast",
                        "boilerplate",
                        "transform",
                        "parallel_burst",
                    ],
                    managed_process=False,
                )
            }
        )

    async def initialize(self) -> None:
        """Initialize the pool (call once before use)."""
        if self._initialized:
            return

        # Create HTTP session with registry-configured timeouts
        timeout = aiohttp.ClientTimeout(total=_POOL_CLIENT_TOTAL, connect=_POOL_CLIENT_CONNECT)
        self._http_session = aiohttp.ClientSession(timeout=timeout)

        # Create worker instances (not started yet)
        for name, worker_config in self.config.workers.items():
            instance = WorkerInstance(config=worker_config)
            self._workers[name] = instance

            if worker_config.tier == WorkerTier.HOT:
                self._hot_workers[name] = instance
            else:
                self._warm_workers[name] = instance

            self._round_robin_idx[name] = 0

        # Calculate total concurrent capacity
        total_slots = sum(w.config.slots for w in self._hot_workers.values())
        self._semaphore = asyncio.Semaphore(total_slots * 2)  # 2x for buffering

        self._initialized = True
        logger.info(
            f"WorkerPool initialized: {len(self._hot_workers)} HOT, "
            f"{len(self._warm_workers)} WARM workers"
        )

    async def start_hot_workers(self) -> dict[str, bool]:
        """Start all HOT tier workers.

        Returns:
            Dict mapping worker name to success status.
        """
        await self.initialize()

        results = {}
        for name, instance in self._hot_workers.items():
            success = await self._start_worker(instance)
            results[name] = success

        return results

    async def _start_worker(self, instance: WorkerInstance) -> bool:
        """Start a single worker instance.

        Args:
            instance: Worker instance to start.

        Returns:
            True if started successfully.
        """
        config = instance.config

        if instance.is_running:
            logger.info(f"Worker {config.name} already running on port {config.port}")
            return True

        if not config.managed_process:
            if await self._check_port_in_use(config.port) and await self._wait_for_health(
                config.port,
                timeout=5,
            ):
                instance._healthy = True
                logger.info(
                    "Worker %s attached to stack-managed port %s",
                    config.name,
                    config.port,
                )
                return True
            logger.warning(
                "Stack-managed worker %s is not healthy on port %s",
                config.name,
                config.port,
            )
            return False

        # Check if port is already in use
        if await self._check_port_in_use(config.port):
            logger.warning(f"Port {config.port} already in use, attempting cleanup")
            await self._kill_port(config.port)
            await asyncio.sleep(1)

        # Build command
        cmd = self._build_launch_command(config)

        # Create log file
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"worker-{config.name}-{config.port}.log"

        logger.info(f"Starting worker {config.name} on port {config.port}")

        from scripts.server.bench_core_claim import BenchPlacementRefusal

        try:
            # SS-BENCH-GATE-c: the spawn prefix must not inherit the bench's
            # cores. `numactl --interleave=all` is a DEFAULT-affinity shape —
            # the kernel may schedule the worker's threads on any core, exactly
            # the incident's sidecar shape. _bench_guarded_prefix pins
            # default-affinity spawns to `host_cores - claim` while a bench is
            # live and refuses (fail closed) when the claim cannot be read.
            prefix = self._bench_guarded_prefix(config.name)
            logger.debug(f"Command: {' '.join((prefix + cmd)[:8])}...")

            with open(log_file, "w") as log:
                env = os.environ.copy()
                env["OMP_NUM_THREADS"] = "1"

                instance.process = subprocess.Popen(
                    prefix + cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=env,
                )

            instance.started_at = datetime.now()

            # Wait for health
            if await self._wait_for_health(config.port, timeout=120):
                instance._healthy = True
                logger.info(f"Worker {config.name} ready on port {config.port}")
                return True
            else:
                logger.error(f"Worker {config.name} failed health check")
                await self._stop_worker(instance)
                return False

        except BenchPlacementRefusal:
            # The incident context was already printed by the guard; nothing
            # spawned, so there is nothing to stop.
            logger.error(
                "Refused to start worker %s: a live CPU bench claims the cores it "
                "would run on (fail closed; see bench_core_claim.py)",
                config.name,
            )
            return False

        except Exception as e:
            logger.error(f"Failed to start worker {config.name}: {e}")
            await self._stop_worker(instance)
            return False

    def _build_launch_command(self, config: WorkerConfig) -> list[str]:
        """Build llama-server launch command."""
        cmd = [
            self.config.llama_server_path,
            "-m",
            config.model_path,
            "--host",
            "0.0.0.0",
            "--port",
            str(config.port),
            "-np",
            str(config.slots),
            "-c",
            "8192",  # 4K per slot with np=2
            "-t",
            str(config.threads),
            "--flash-attn",
            "on",
        ]

        # Add prompt lookup for all workers
        if self.config.prompt_lookup:
            cmd.extend(["--lookup-ngram-min", "3"])

        # Add any extra flags
        cmd.extend(config.launch_flags)

        return cmd

    def _bench_guarded_prefix(self, name: str) -> list[str]:
        """SS-BENCH-GATE-c — Popen prefix for a worker spawn, bench-aware.

        The pool's `numactl --interleave=all` prefix is a DEFAULT-affinity
        shape: the kernel may schedule the worker's threads on any core,
        including cores a live CPU bench pinned (the 2026-07-27 sidecar shape
        that destroyed 1h09m of decision-gating measurement). While a bench
        claims cores, the spawn is pinned to `host_cores - claim` instead;
        a claim that cannot be read refuses the spawn (BenchPlacementRefusal,
        fail closed: unknown must mean busy). No bench live -> the
        byte-identical legacy prefix.
        """
        base = ["numactl", "--interleave=all"] if shutil.which("numactl") else []
        from scripts.server.bench_core_claim import api_enforce_placement

        pinned = api_enforce_placement(None, label=f"worker {name}")
        if pinned is None:
            return base
        return ["taskset", "-c", pinned]

    async def _wait_for_health(
        self, port: int, timeout: int = int(_registry_timeout("health", "server_startup", 120))
    ) -> bool:
        """Wait for worker health endpoint.

        Args:
            port: Worker port.
            timeout: Timeout in seconds (from registry).

        Returns:
            True if healthy within timeout.
        """
        url = f"http://localhost:{port}/health"
        start = time.time()

        while time.time() - start < timeout:
            try:
                async with self._http_session.get(url) as resp:
                    if resp.status == 200:
                        return True
            except Exception as e:
                logger.debug("Health check poll failed for port %s: %s", port, e)
            await asyncio.sleep(2)

        return False

    async def _check_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    async def _kill_port(self, port: int) -> None:
        """Kill any process using a port."""
        try:
            result = subprocess.run(
                ["lsof", "-t", f"-i:{port}"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                for pid_str in result.stdout.strip().split("\n"):
                    try:
                        os.kill(int(pid_str), signal.SIGKILL)
                    except Exception as e:
                        logger.debug(
                            "Failed to kill PID %s on port %s: %s", pid_str, port, e
                        )
        except Exception as e:
            logger.debug("Port kill lookup failed for port %s: %s", port, e)

    async def _stop_worker(self, instance: WorkerInstance) -> None:
        """Stop a worker instance."""
        if instance.process is None:
            return

        try:
            instance.process.terminate()
            try:
                instance.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                instance.process.kill()
                instance.process.wait(timeout=2)
        except Exception as e:
            logger.warning(f"Error stopping worker {instance.config.name}: {e}")
        finally:
            instance.process = None
            instance._healthy = False

    async def stop_all(self) -> None:
        """Stop all workers and cleanup."""
        # Cancel warm shutdown tasks
        for task in self._warm_shutdown_tasks.values():
            task.cancel()

        # Stop all workers
        for instance in self._workers.values():
            await self._stop_worker(instance)

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        self._initialized = False
        logger.info("WorkerPool stopped")

    # =========================================================================
    # Request Routing
    # =========================================================================

    def _get_worker_role(self, task_type: str) -> str:
        """Map task type to worker role.

        Args:
            task_type: Task type string or TaskType enum.

        Returns:
            Worker role name (explore, code, fast).
        """
        # Handle string task types
        try:
            tt = TaskType(task_type.lower())
        except ValueError:
            # Unknown task type, default to explore
            return "explore"

        return TASK_ROUTING.get(tt, "explore")

    async def _select_workers(
        self,
        task_type: str,
        parallelism: int = 1,
    ) -> list[WorkerInstance]:
        """Select workers for a task.

        Args:
            task_type: Type of task.
            parallelism: Number of parallel tasks.

        Returns:
            List of worker instances to use.
        """
        role = self._get_worker_role(task_type)

        # Find matching workers
        candidates = []
        for instance in self._workers.values():
            if role in instance.config.name or role in instance.config.task_types:
                if instance._healthy:
                    candidates.append(instance)

        if not candidates:
            # Fallback to any healthy HOT worker
            candidates = [w for w in self._hot_workers.values() if w._healthy]

        if not candidates:
            raise RuntimeError("No healthy workers available")

        # For high parallelism, consider spinning up WARM workers
        if parallelism > self.config.expansion_threshold:
            await self._ensure_warm_workers_running(role)
            # Re-scan for fast workers
            for instance in self._warm_workers.values():
                if instance._healthy and instance not in candidates:
                    candidates.append(instance)

        return candidates

    async def _ensure_warm_workers_running(self, role: str = "fast") -> None:
        """Ensure WARM workers are running for high parallelism.

        Args:
            role: Preferred worker role (used for logging).
        """
        async with self._lock:
            for name, instance in self._warm_workers.items():
                if not instance._healthy:
                    logger.info(f"Expanding pool: starting WARM worker {name}")
                    await self._start_worker(instance)

                # Cancel any pending shutdown
                if name in self._warm_shutdown_tasks:
                    self._warm_shutdown_tasks[name].cancel()
                    del self._warm_shutdown_tasks[name]

    async def _schedule_warm_shutdown(self, instance: WorkerInstance) -> None:
        """Schedule a WARM worker for shutdown after idle timeout."""
        name = instance.config.name

        async def _shutdown_after_timeout():
            try:
                await asyncio.sleep(self.config.warm_timeout_seconds)
                async with self._lock:
                    # Check if still idle
                    if instance.last_used:
                        idle_time = (datetime.now() - instance.last_used).total_seconds()
                        if idle_time >= self.config.warm_timeout_seconds:
                            logger.info(f"Shutting down idle WARM worker {name}")
                            await self._stop_worker(instance)
            except asyncio.CancelledError:
                pass  # Expected when rescheduling
            except Exception as e:
                logger.exception("Error in warm shutdown task for worker %s: %s", name, e)

        # Cancel existing shutdown task if any
        if name in self._warm_shutdown_tasks:
            self._warm_shutdown_tasks[name].cancel()

        # Schedule new shutdown
        task = asyncio.create_task(_shutdown_after_timeout())
        self._warm_shutdown_tasks[name] = task

    def _get_round_robin(self, workers: list[WorkerInstance]) -> WorkerInstance:
        """Get next worker using round-robin.

        Args:
            workers: List of candidate workers.

        Returns:
            Selected worker instance.
        """
        # Use first worker's name as the key for round-robin state
        key = workers[0].config.name if workers else "default"

        idx = self._round_robin_idx.get(key, 0)
        worker = workers[idx % len(workers)]
        self._round_robin_idx[key] = (idx + 1) % len(workers)

        return worker

    # =========================================================================
    # Public API
    # =========================================================================

    async def call(
        self,
        prompt: str,
        task_type: str = "explore",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_schema: dict | None = None,
        grammar: str | None = None,
    ) -> str:
        """Make a single call to a worker.

        Args:
            prompt: The prompt to send.
            task_type: Task type for routing.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            json_schema: Optional JSON schema constraining the response
                (forwarded to llama-server's ``/completion`` payload).
            grammar: Optional GBNF grammar constraining the response.

        Returns:
            Model response text.
        """
        await self.initialize()

        workers = await self._select_workers(task_type, parallelism=1)
        worker = self._get_round_robin(workers)

        # Only forward the constraint kwargs when set, so a caller that omits
        # them reaches _http_call with the exact pre-TD-21.22a argument list
        # (a test double/side_effect fixed at 4 positional args must not break).
        extra: dict = {}
        if json_schema is not None:
            extra["json_schema"] = json_schema
        if grammar is not None:
            extra["grammar"] = grammar

        async with self._semaphore:
            result = await self._http_call(worker, prompt, temperature, max_tokens, **extra)
            worker.last_used = datetime.now()
            worker.request_count += 1

            # Schedule WARM shutdown if applicable
            if worker.config.tier == WorkerTier.WARM:
                await self._schedule_warm_shutdown(worker)

            return result

    async def batch(
        self,
        prompts: list[str],
        task_type: str = "explore",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_schema: dict | None = None,
        grammar: str | None = None,
    ) -> list[str]:
        """Execute batch in parallel across pool.

        Args:
            prompts: List of prompts.
            task_type: Task type for routing.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            json_schema: Optional JSON schema constraining every prompt in
                this batch (TD-21.22a: one schema for the whole batch, not
                per-prompt — forwarded verbatim to each worker's
                ``/completion`` payload). Omitted reproduces the prior
                call byte-for-byte.
            grammar: Optional GBNF grammar for the whole batch.

        Returns:
            List of responses in order.
        """
        await self.initialize()

        workers = await self._select_workers(task_type, parallelism=len(prompts))

        # See call() above: forward only when set, to keep the omitted-schema
        # call shape identical to before TD-21.22a.
        extra: dict = {}
        if json_schema is not None:
            extra["json_schema"] = json_schema
        if grammar is not None:
            extra["grammar"] = grammar

        async def _call_with_worker(prompt: str, idx: int) -> tuple[int, str]:
            worker = workers[idx % len(workers)]
            async with self._semaphore:
                result = await self._http_call(worker, prompt, temperature, max_tokens, **extra)
                worker.last_used = datetime.now()
                worker.request_count += 1
                return idx, result

        # Execute all calls in parallel
        tasks = [
            asyncio.create_task(_call_with_worker(prompt, i)) for i, prompt in enumerate(prompts)
        ]

        results_unordered = await asyncio.gather(*tasks, return_exceptions=True)

        # Reorder results
        results = [""] * len(prompts)
        for item in results_unordered:
            if isinstance(item, Exception):
                logger.error(f"Batch call failed: {item}")
                continue
            idx, text = item
            results[idx] = text

        # Schedule WARM shutdown for any warm workers used
        for worker in workers:
            if worker.config.tier == WorkerTier.WARM:
                await self._schedule_warm_shutdown(worker)

        return results

    async def _http_call(
        self,
        worker: WorkerInstance,
        prompt: str,
        temperature: float,
        max_tokens: int,
        json_schema: dict | None = None,
        grammar: str | None = None,
    ) -> str:
        """Make HTTP call to worker.

        Args:
            worker: Worker instance.
            prompt: Prompt text.
            temperature: Sampling temperature.
            max_tokens: Max tokens.
            json_schema: Optional JSON schema forwarded as a top-level
                ``json_schema`` key on the ``/completion`` payload (mirrors
                ``LlamaServerBackend._build_payload``, `src/backends/llama_server.py`).
            grammar: Optional GBNF grammar forwarded as a top-level ``grammar`` key.

        Returns:
            Response text.
        """
        url = f"{worker.url}/completion"

        # Per-model chat template (mirrors the chat.py:498 fix). /completion
        # does not apply the GGUF's Jinja template server-side, so the caller
        # must template the prompt. Without this, gemma-family workers see
        # raw user text (or Qwen-style markers from a prior caller) as random
        # tokens and return 0 tokens. Stem of model_path is the same kind of
        # name the helper's family detector expects (e.g.
        # `gemma-4-26B-A4B-it-Q4_K_M` from a Q4_K_M.gguf).
        from src.api.routes.chat_utils import apply_chat_template_for_model
        model_stem = Path(worker.config.model_path).stem
        templated_prompt = apply_chat_template_for_model(model_stem, prompt)

        payload = {
            "prompt": templated_prompt,
            "temperature": temperature,
            "n_predict": max_tokens,
            "stream": False,
        }
        if json_schema:
            payload["json_schema"] = json_schema
        if grammar:
            payload["grammar"] = grammar

        try:
            async with self._http_session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Worker returned {resp.status}: {error_text}")

                data = await resp.json()
                return data.get("content", "")

        except aiohttp.ClientError as e:
            worker.error_count += 1
            raise RuntimeError(f"HTTP call to {worker.config.name} failed: {e}")

    # =========================================================================
    # Status & Monitoring
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """Get pool status summary.

        Returns:
            Dict with pool status information.
        """
        return {
            "initialized": self._initialized,
            "enabled": self.config.enabled,
            "hot_workers": {
                name: {
                    "port": w.config.port,
                    "healthy": w._healthy,
                    "running": w.is_running,
                    "requests": w.request_count,
                    "errors": w.error_count,
                    "model": Path(w.config.model_path).stem,
                }
                for name, w in self._hot_workers.items()
            },
            "warm_workers": {
                name: {
                    "port": w.config.port,
                    "healthy": w._healthy,
                    "running": w.is_running,
                    "requests": w.request_count,
                    "errors": w.error_count,
                    "model": Path(w.config.model_path).stem,
                }
                for name, w in self._warm_workers.items()
            },
        }

    async def health_check(self) -> dict[str, bool]:
        """Check health of all workers.

        Returns:
            Dict mapping worker name to health status.
        """
        results = {}
        for name, instance in self._workers.items():
            if instance.is_running:
                instance._healthy = await self._wait_for_health(instance.config.port, timeout=5)
            else:
                instance._healthy = False
            results[name] = instance._healthy

        return results


# Singleton instance for module-level access
_pool_instance: Optional[WorkerPoolManager] = None
_pool_lock = threading.Lock()


def get_worker_pool() -> WorkerPoolManager:
    """Get or create the global worker pool instance (thread-safe)."""
    global _pool_instance
    if _pool_instance is None:
        with _pool_lock:
            if _pool_instance is None:
                _pool_instance = WorkerPoolManager()
    return _pool_instance


async def shutdown_worker_pool() -> None:
    """Shutdown the global worker pool."""
    global _pool_instance
    if _pool_instance is not None:
        await _pool_instance.stop_all()
        _pool_instance = None

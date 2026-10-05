"""Binary path + registry-timeout helpers used by the executor module.

Extracted from scripts/lib/executor.py during the 2026-05-22 Task-J refactor.
executor.py re-imports every name so existing callers keep working.
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

try:
    from .registry import ModelRegistry, load_registry
except ImportError:
    from registry import ModelRegistry, load_registry


def _numa_prefix() -> list[str]:
    """Return numactl interleave prefix if numactl is available, else empty list."""
    if shutil.which("numactl"):
        return ["numactl", "--interleave=all"]
    return []


def _read_registry_timeout(category: str, key: str, fallback: int) -> int:
    """Read timeout from model_registry.yaml."""
    try:
        reg = load_registry()
        if reg and reg._raw:
            timeouts = reg._raw.get("runtime_defaults", {}).get("timeouts", {})
            cat_data = timeouts.get(category, {})
            return cat_data.get(key, timeouts.get("default", fallback))
    except Exception:
        pass
    return fallback


def get_binary_paths(registry: Optional["ModelRegistry"] = None) -> dict[str, str]:
    """Get binary paths from registry (single source of truth).

    Falls back to hardcoded paths only if registry is unavailable.
    """
    fallback = {
        "base_dir": "/mnt/raid0/llm/llama.cpp/build/bin",
        "completion": "llama-completion",
        "speculative": "llama-speculative",
        "lookup": "llama-lookup",
        "cli": "llama-cli",
        "server": "llama-server",
    }

    if registry is None:
        try:
            registry = load_registry()
        except Exception:
            pass

    binaries = dict(fallback)
    if registry and hasattr(registry, "data"):
        declared = registry.data.get("runtime_defaults", {}).get("binaries", {})
        if declared:
            binaries = dict(declared)

    # base_dir comes from the KERNEL STORE, not from the registry literal.
    #
    # The registry owns the binary NAMES (completion/speculative/lookup/cli/server);
    # it does not own which kernel build they come from. kernels/README.md is explicit
    # that `production/<backend>` is "the only path anything should name".
    #
    # Why this override exists: `get_binary()` is a LAUNCH path (scripts/lib/executor.py
    # uses it for server/speculative/lookup/mtmd). The master registry's
    # `runtime_defaults.binaries.base_dir` is a build-path literal, and its own comment
    # claims ORCHESTRATOR_PATHS_LLAMA_CPP_BIN overrides it -- which was NOT true: this
    # function read the registry directly. After the v10 promotion repointed
    # production/cpu, that left executor.py launching the OLD kernel (the stale path
    # still exists, so it resolves and serves silently) while stack_priors,
    # orchestrator_stack and env.sh had all followed the promotion. Split-brain kernel
    # resolution, detectable only by reading argv of a running server.
    #
    # Fails closed: an unresolvable store raises KernelPathError naming the backend,
    # consistent with kernel_paths' other consumers. An explicit
    # ORCHESTRATOR_PATHS_LLAMA_CPP_BIN still wins, so an operator can still pin a tree.
    explicit = os.environ.get("ORCHESTRATOR_PATHS_LLAMA_CPP_BIN", "").strip()
    if explicit:
        binaries["base_dir"] = explicit
    else:
        from src.registry.kernel_paths import backend_dir as _kernel_backend_dir

        binaries["base_dir"] = str(_kernel_backend_dir("cpu"))

    return binaries


def get_binary(name: str, registry: Optional["ModelRegistry"] = None) -> str:
    """Get full path to a specific binary.

    Args:
        name: Binary name ('completion', 'speculative', 'lookup', 'cli')
        registry: Optional registry instance

    Returns:
        Full absolute path to the binary
    """
    paths = get_binary_paths(registry)
    base_dir = paths.get("base_dir", "/mnt/raid0/llm/llama.cpp/build/bin")
    binary_name = paths.get(name, name)
    return os.path.join(base_dir, binary_name)


def validate_binaries(registry: Optional["ModelRegistry"] = None) -> dict[str, str]:
    """Validate all required binaries exist.

    Raises:
        FileNotFoundError: If any binary is missing, with clear error message.

    Returns:
        Dict mapping binary name to full path (for logging/debugging).
    """
    required = ["completion", "speculative", "lookup"]
    paths = {}
    missing = []

    for name in required:
        path = get_binary(name, registry)
        paths[name] = path
        if not os.path.exists(path):
            missing.append(f"  {name}: {path}")

    if missing:
        raise FileNotFoundError(
            "Missing llama.cpp binaries (check registry runtime_defaults.binaries):\n"
            + "\n".join(missing)
            + "\n\nRegistry location: /mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml"
        )

    return paths


def get_server_defaults(registry: Optional["ModelRegistry"] = None) -> dict:
    """Get server defaults from registry.

    Returns dict with: port, context_length, startup_timeout, request_timeout, parallel_slots
    """
    defaults = {
        "port": 8080,
        "context_length": 131072,  # 131K - Qwen3 native limit
        "startup_timeout": 600,
        "request_timeout": 300,
        "parallel_slots": 4,
    }

    if registry is None:
        try:
            registry = load_registry()
        except Exception:
            pass

    if registry and hasattr(registry, "data"):
        server_cfg = registry.data.get("runtime_defaults", {}).get("server_defaults", {})
        if server_cfg:
            defaults.update(server_cfg)

    return defaults

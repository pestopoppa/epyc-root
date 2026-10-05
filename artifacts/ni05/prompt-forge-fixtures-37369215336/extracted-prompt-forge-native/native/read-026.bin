"""Shared CLI config helpers used by both seed_specialist_routing.py and _v2.

Extracted during the 2026-05-22 Task-B refactor. Owns the profile presets,
profile-application logic, and the RetrievalConfig builder. Both scripts
keep thin wrappers under the original names so test patches keep working.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any


# Profile presets — environment + cooldown + timeout combos used in seeding runs.
_PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    "baseline": {
        "cooldown": 0.0,
        "timeout": None,
        "env": {},
    },
    "infra-stable": {
        "cooldown": 2.0,
        "timeout": None,
        "env": {
            "ORCHESTRATOR_DEFERRED_TOOL_RESULTS": "1",
            "ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_EXCLUSIVE_S": "45",
            "ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_SHARED_S": "45",
            "ORCHESTRATOR_UVICORN_WORKERS": "1",
        },
    },
}


def apply_profile(
    args: argparse.Namespace,
    *,
    default_timeout: int,
    logger: logging.Logger,
) -> None:
    """Set os.environ defaults + fill args.cooldown / args.timeout from profile."""
    profile = _PROFILE_PRESETS.get(args.profile, _PROFILE_PRESETS["baseline"])

    for key, value in profile.get("env", {}).items():
        os.environ.setdefault(key, str(value))

    if args.cooldown is None:
        args.cooldown = float(profile.get("cooldown", 0.0))
    if args.timeout is None:
        timeout_default = profile.get("timeout")
        args.timeout = int(timeout_default) if timeout_default is not None else int(default_timeout)

    logger.info(
        "Seeding profile=%s cooldown=%.1fs timeout=%ss deferred_tool_results=%s "
        "lock_timeout_exclusive_s=%s lock_timeout_shared_s=%s uvicorn_workers=%s",
        args.profile,
        args.cooldown,
        args.timeout,
        os.environ.get("ORCHESTRATOR_DEFERRED_TOOL_RESULTS", "0"),
        os.environ.get("ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_EXCLUSIVE_S", ""),
        os.environ.get("ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_SHARED_S", ""),
        os.environ.get("ORCHESTRATOR_UVICORN_WORKERS", ""),
    )


# Argparse → RetrievalConfig override keys (single source of truth).
_RETRIEVAL_CONFIG_OVERRIDE_KEYS: tuple[str, ...] = (
    "cost_lambda",
    "confidence_threshold",
    "confidence_estimator",
    "confidence_trim_ratio",
    "confidence_min_neighbors",
    "warm_probability_hit",
    "warm_probability_miss",
    "warm_cost_fallback_s",
    "cold_cost_fallback_s",
    "calibrated_confidence_threshold",
    "conformal_margin",
    "risk_control_enabled",
    "risk_budget_id",
    "risk_gate_min_samples",
    "risk_abstain_target_role",
    "risk_gate_rollout_ratio",
    "risk_gate_kill_switch",
    "risk_budget_guardrail_min_events",
    "risk_budget_guardrail_max_abstain_rate",
    "prior_strength",
)


def build_retrieval_config_from_args(args):
    """Build RetrievalConfig with optional CLI overrides for replay/debug tuning."""
    from orchestration.repl_memory.retriever import RetrievalConfig

    overrides: dict[str, Any] = {}
    for key in _RETRIEVAL_CONFIG_OVERRIDE_KEYS:
        val = getattr(args, key, None)
        if val is not None:
            overrides[key] = val
    return RetrievalConfig(**overrides)

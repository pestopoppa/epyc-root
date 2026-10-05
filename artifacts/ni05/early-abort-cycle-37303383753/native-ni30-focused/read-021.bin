"""Think-harder adaptive logic for orchestration graph nodes.

Manages per-role ROI tracking and adaptive token budget decisions. Extracted
from graph/helpers.py — all callers continue to import from helpers via
compatibility re-exports.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic_graph import GraphRunContext

from src.escalation import ErrorCategory
from src.graph.state import TaskDeps, TaskState

log = logging.getLogger(__name__)

Ctx = GraphRunContext[TaskState, TaskDeps]


def _think_harder_cfg():
    from src.config import get_config

    return get_config().think_harder


def _expected_think_harder_roi(state: TaskState, role: str) -> float:
    """Return expected ROI for think-harder on this role from historical stats."""
    stats = state.think_harder_roi_by_role.get(role, {})
    attempts = float(stats.get("attempts", 0.0))
    successes = float(stats.get("successes", 0.0))
    if attempts <= 0:
        return 1.0
    success_rate = successes / attempts
    # ROI proxy: how often think-harder avoided escalation/failure, centered at 0.5.
    return success_rate - 0.5


def _update_think_harder_stats(ctx: Ctx) -> None:
    """Track per-role think-harder ROI for future gating decisions."""
    state = ctx.state
    attempted = bool(state.think_harder_attempted or state.think_harder_succeeded is False)
    if not attempted:
        return
    role = str(state.current_role)
    stats = state.think_harder_roi_by_role.setdefault(
        role,
        {
            "attempts": 0.0,
            "successes": 0.0,
            "expected_roi": 1.0,
            "ema_marginal_utility": 0.0,
            "last_attempt_turn": -9999.0,
        },
    )
    stats["attempts"] = float(stats.get("attempts", 0.0)) + 1.0
    succeeded = bool(state.think_harder_succeeded)
    if succeeded:
        stats["successes"] = float(stats.get("successes", 0.0)) + 1.0

    th_cfg = _think_harder_cfg()
    fallback_budget = float(th_cfg.token_budget_fallback)
    n_tokens = float(state.artifacts.get("think_harder_token_budget", fallback_budget) or fallback_budget)
    token_penalty = min(n_tokens / fallback_budget, 1.5) * float(th_cfg.token_penalty_per_4k)
    sample_utility = (1.0 if succeeded else 0.0) - token_penalty
    prev_ema = float(stats.get("ema_marginal_utility", 0.0))
    alpha = max(
        float(th_cfg.ema_alpha_min),
        min(float(th_cfg.ema_alpha_max), float(state.think_harder_ema_alpha)),
    )
    stats["ema_marginal_utility"] = ((1.0 - alpha) * prev_ema) + (alpha * sample_utility)
    stats["last_attempt_turn"] = float(state.turns)
    stats["expected_roi"] = _expected_think_harder_roi(state, role)
    state.artifacts["think_harder_expected_roi"] = stats["expected_roi"]
    state.artifacts["think_harder_marginal_utility"] = stats["ema_marginal_utility"]


def _should_think_harder(ctx: Ctx, error_category: ErrorCategory) -> bool:
    """On penultimate retry, try same model with boosted config (CoT, 2x tokens).

    Returns True exactly once: when consecutive_failures == max_retries - 1
    and think_harder hasn't been attempted yet for this role.
    """
    cfg = ctx.deps.config
    state = ctx.state

    # Format/schema errors: just retry, don't think harder
    if (
        error_category in cfg.no_escalate_categories
        or error_category == ErrorCategory.SCHEMA
        or error_category == ErrorCategory.TIMEOUT
    ):
        return False

    # Only try once per role
    if state.think_harder_attempted:
        return False

    role = str(state.current_role)
    role_stats = state.think_harder_roi_by_role.get(role, {})
    last_attempt_turn = float(role_stats.get("last_attempt_turn", -9999.0))
    if (state.turns - last_attempt_turn) < max(0, int(state.think_harder_cooldown_turns)):
        return False
    attempts = int(role_stats.get("attempts", 0.0))
    if attempts >= state.think_harder_min_samples:
        expected_roi = _expected_think_harder_roi(state, role)
        if expected_roi < state.think_harder_min_expected_roi:
            log.info(
                "Think-harder disabled for %s due to low ROI (expected=%.3f, attempts=%d)",
                role, expected_roi, attempts,
            )
            return False
        ema_marginal = float(role_stats.get("ema_marginal_utility", 0.0))
        if ema_marginal < float(state.think_harder_min_marginal_utility):
            log.info(
                "Think-harder disabled for %s due to low marginal utility "
                "(ema=%.3f < %.3f, attempts=%d)",
                role,
                ema_marginal,
                float(state.think_harder_min_marginal_utility),
                attempts,
            )
            return False

    return state.consecutive_failures == cfg.max_retries - 1


def _build_think_harder_config(state: TaskState) -> dict[str, Any]:
    """Build adaptive think-harder config using per-role ROI history.

    This uses a decaying envelope:
    - high expected ROI -> larger token budget + CoT prefix
    - low expected ROI -> smaller budget and lower temperature
    """
    role = str(state.current_role)
    expected_roi = _expected_think_harder_roi(state, role)
    role_stats = state.think_harder_roi_by_role.setdefault(
        role,
        {
            "attempts": 0.0,
            "successes": 0.0,
            "expected_roi": 1.0,
            "ema_marginal_utility": 0.0,
            "last_attempt_turn": -9999.0,
        },
    )
    # Map ROI range [-0.5, 0.5] to [0, 1] for stable envelope scaling.
    roi_norm = max(0.0, min(1.0, expected_roi + 0.5))

    th_cfg = _think_harder_cfg()
    min_tokens = int(th_cfg.token_budget_min)
    max_tokens = int(th_cfg.token_budget_max)
    n_tokens = int(round(min_tokens + ((max_tokens - min_tokens) * roi_norm)))
    temp_min = float(th_cfg.temperature_min)
    temp_max = float(th_cfg.temperature_max)
    temperature = round(temp_min + ((temp_max - temp_min) * roi_norm), 2)
    cot_prefix = (
        "# Step-by-step solution:\n"
        if roi_norm >= float(th_cfg.cot_roi_threshold)
        else ""
    )

    state.artifacts["think_harder_expected_roi"] = expected_roi
    state.artifacts["think_harder_token_budget"] = n_tokens
    state.artifacts["think_harder_temperature"] = temperature
    state.artifacts["think_harder_cot_enabled"] = bool(cot_prefix)
    role_stats["last_attempt_turn"] = float(state.turns)

    return {
        "n_tokens": n_tokens,
        "cot_prefix": cot_prefix,
        "temperature": temperature,
    }

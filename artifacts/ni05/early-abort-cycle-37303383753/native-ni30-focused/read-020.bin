"""Failure and escalation observability helpers for graph execution."""

from __future__ import annotations

import logging
from typing import Any

from src.escalation import ErrorCategory

log = logging.getLogger(__name__)


def _record_failure(ctx: Any, error_category: ErrorCategory, error_msg: str) -> str | None:
    """Record failure in the FailureGraph (anti-memory)."""
    fg = ctx.deps.failure_graph
    if fg is None:
        return None
    try:
        failure_id = fg.record_failure(
            memory_id=ctx.state.task_id,
            symptoms=[error_category.value, error_msg[:100]],
            description=f"{ctx.state.current_role} failed: {error_msg[:200]}",
            severity=min(ctx.state.consecutive_failures + 2, 5),
        )
        ctx.state.last_failure_id = failure_id
        return failure_id
    except Exception as exc:
        log.debug("failure_graph.record_failure failed: %s", exc)
    return None


def _record_mitigation(
    ctx: Any,
    from_role: str,
    to_role: str,
    failure_id: str | None = None,
) -> None:
    """Record a successful mitigation in the FailureGraph."""
    fg = ctx.deps.failure_graph
    if fg is None:
        return
    try:
        resolved_failure_id = failure_id or ctx.state.last_failure_id
        if not resolved_failure_id:
            return
        fg.record_mitigation(
            failure_id=resolved_failure_id,
            action=f"escalate:{from_role}->{to_role}",
            worked=True,
        )
    except Exception as exc:
        log.debug("failure_graph.record_mitigation failed: %s", exc)


def _add_evidence(ctx: Any, outcome: str, delta: float | None = None) -> None:
    """Record evidence in the HypothesisGraph."""
    hg = ctx.deps.hypothesis_graph
    if hg is None:
        return
    try:
        normalized_outcome = "success" if outcome == "success" else "failure"
        hg.add_evidence(
            hypothesis_id=ctx.state.task_id,
            outcome=normalized_outcome,
            source=f"{ctx.state.current_role}:turn_{ctx.state.turns}",
        )
    except Exception as exc:
        log.debug("hypothesis_graph.add_evidence failed: %s", exc)


def _log_escalation(ctx: Any, from_role: str, to_role: str, reason: str) -> None:
    """Log an escalation event via progress logger and state telemetry."""
    pl = ctx.deps.progress_logger
    if pl is None:
        return
    try:
        pl.log_escalation(
            task_id=ctx.state.task_id,
            from_tier=from_role,
            to_tier=to_role,
            reason=reason,
        )
    except Exception as exc:
        log.debug("progress_logger.log_escalation failed: %s", exc)
    app_state = getattr(ctx.deps, "app_state", None)
    if app_state and hasattr(app_state, "record_escalation"):
        try:
            app_state.record_escalation(from_role, to_role)
        except Exception:
            pass

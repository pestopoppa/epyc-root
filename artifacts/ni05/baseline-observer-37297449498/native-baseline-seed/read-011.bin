"""Baseline promotion ledger reconciliation and authority helpers.

The live safety gate still needs an in-memory baseline object. Persistence is
allowed to drop ``autopilot_state.json:baseline_state`` only after append-only
``baseline_promotion`` events can reconstruct the same state without warnings.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from src.autopilot_core.authority_consent import authority_consent


BASELINE_PROMOTION_EVENT_TYPE = "baseline_promotion"
# AP-57 (operator ruled B, 2026-09-17): a speed-axis reseed on the quality-refusal path is a
# baseline_state write too. Its receipt carries the post-write snapshot, so the fold replays it
# in append order next to promotions (it is never counted as a promotion).
SPEED_AXIS_RESEED_EVENT_TYPE = "speed_axis_reseed"
BASELINE_LEDGER_EVENT_TYPES = frozenset(
    {BASELINE_PROMOTION_EVENT_TYPE, SPEED_AXIS_RESEED_EVENT_TYPE}
)
BASELINE_LEDGER_AUTHORITY_STATE_FLAG = "baseline_ledger_authority_enabled"


@dataclass(frozen=True)
class BaselineLedgerReconciliation:
    """Structured result for comparing promotion-ledger state to live state."""

    status: str
    event_count: int = 0
    # AP-57: how many of ``event_count`` are speed-axis reseed receipts.
    reseed_event_count: int = 0
    valid_snapshot_count: int = 0
    cutover_ready: bool = False
    cutover_blockers: list[str] = field(default_factory=list)
    latest_event: dict[str, Any] | None = None
    folded_state: dict[str, Any] | None = None
    state_baseline: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)


def canonical_jsonable(value: Any) -> Any:
    """Normalize JSON-like payloads for stable read-only diagnostics."""
    try:
        return json.loads(json.dumps(value, sort_keys=True, default=str))
    except (TypeError, ValueError):
        return value


def _promotion_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("type") == BASELINE_PROMOTION_EVENT_TYPE
        and "trial_id" not in event
    ]


def _ledger_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Promotion and speed-axis reseed events, in the caller's (append) order."""
    return [
        event
        for event in events
        if event.get("type") in BASELINE_LEDGER_EVENT_TYPES
        and "trial_id" not in event
    ]


def _event_quality_warning(event: dict[str, Any], state: dict[str, Any]) -> str | None:
    try:
        tier_key = str(int(event["tier"]))
    except (KeyError, TypeError, ValueError):
        return None
    tier_values = state.get("baselines_by_tier")
    if not isinstance(tier_values, dict) or tier_key not in tier_values:
        return None
    try:
        new_quality = float(event["new_quality"])
        folded_quality = float(tier_values[tier_key])
    except (KeyError, TypeError, ValueError):
        return None
    if abs(new_quality - folded_quality) > 1e-9:
        return (
            f"event new_quality {new_quality:.3f} differs from "
            f"baseline_state.baselines_by_tier[{tier_key}] {folded_quality:.3f}"
        )
    return None


def reconcile_baseline_ledger(
    events: list[dict[str, Any]],
    state_baseline: dict[str, Any] | None,
) -> BaselineLedgerReconciliation:
    """Fold baseline ledger events by append order and compare to state.

    Latest valid ``baseline_state`` snapshot wins. Both ``baseline_promotion`` and
    (AP-57) ``speed_axis_reseed`` events carry one; ``events`` must be in append
    order. Missing or malformed event state is not inferred from event metrics,
    YAML, Pareto archive, or current state; it only contributes a warning.
    A ledger with reseed receipts but no promotion stays ``no_events``: a reseed
    only re-anchors the speed axis of a baseline some promotion must have seeded.
    """
    if not _promotion_events(events):
        return BaselineLedgerReconciliation(
            status="no_events",
            cutover_blockers=[
                "no baseline promotion events; YAML remains cold-start seed"
            ],
        )

    promotion_events = _ledger_events(events)
    reseed_event_count = sum(
        1 for event in promotion_events if event.get("type") == SPEED_AXIS_RESEED_EVENT_TYPE
    )
    folded_state: dict[str, Any] | None = None
    latest_valid_event: dict[str, Any] | None = None
    valid_snapshot_count = 0
    warnings: list[str] = []
    for index, event in enumerate(promotion_events):
        snapshot = event.get("baseline_state")
        if not isinstance(snapshot, dict):
            warnings.append(f"event {index} has no usable baseline_state snapshot")
            continue
        folded_state = canonical_jsonable(copy.deepcopy(snapshot))
        latest_valid_event = copy.deepcopy(event)
        valid_snapshot_count += 1

    if folded_state is None:
        return BaselineLedgerReconciliation(
            status="unreconstructable",
            event_count=len(promotion_events),
            reseed_event_count=reseed_event_count,
            valid_snapshot_count=valid_snapshot_count,
            cutover_blockers=[
                "no promotion event has a usable baseline_state snapshot"
            ],
            warnings=warnings,
        )

    latest_promotion = next(
        (
            event
            for event in reversed(promotion_events)
            if event.get("type") == BASELINE_PROMOTION_EVENT_TYPE
            and isinstance(event.get("baseline_state"), dict)
        ),
        None,
    )
    warning = _event_quality_warning(latest_promotion or {}, folded_state)
    if warning:
        warnings.append(warning)

    canonical_state = (
        canonical_jsonable(copy.deepcopy(state_baseline))
        if isinstance(state_baseline, dict) and state_baseline
        else None
    )
    if canonical_state is None:
        status = "ledger_authoritative"
    elif canonical_state == folded_state:
        status = "match"
    else:
        status = "drift"

    cutover_blockers: list[str] = []
    missing_snapshot_count = len(promotion_events) - valid_snapshot_count
    if missing_snapshot_count:
        cutover_blockers.append(
            f"{missing_snapshot_count} promotion event(s) lack usable "
            "baseline_state snapshots"
        )
    if status not in {"match", "ledger_authoritative"}:
        cutover_blockers.append(
            f"ledger fold does not match current state baseline ({status})"
        )
    if warnings:
        cutover_blockers.append("baseline promotion ledger has warning diagnostics")

    return BaselineLedgerReconciliation(
        status=status,
        event_count=len(promotion_events),
        reseed_event_count=reseed_event_count,
        valid_snapshot_count=valid_snapshot_count,
        cutover_ready=not cutover_blockers,
        cutover_blockers=cutover_blockers,
        latest_event=latest_valid_event,
        folded_state=folded_state,
        state_baseline=canonical_state,
        warnings=warnings,
    )


def baseline_ledger_authority_enabled(state: dict[str, Any]) -> bool:
    """Return whether persisted state AND operator consent permit baseline cache removal.

    The mutable state flag is necessary but NOT sufficient: ratification is
    fail-closed behind the operator-owned consent file (see
    ``authority_consent``), which agents running as the autopilot uid cannot
    write. This prevents any agent from self-granting baseline authority by
    flipping the state flag alone.
    """
    if state.get(BASELINE_LEDGER_AUTHORITY_STATE_FLAG) is not True:
        return False
    return authority_consent("baseline_ledger")


def apply_baseline_ledger_authority(
    state: dict[str, Any],
    events: list[dict[str, Any]],
) -> bool | None:
    """Apply baseline-as-ledger persistence authority to ``state``.

    Returns True when cached ``baseline_state`` was removed, False when the
    journal fold existed but state was unchanged, and None when no usable
    promotion ledger exists yet. Drift, missing snapshots, and warning
    diagnostics deliberately keep the cache in place.
    """
    reconciliation = reconcile_baseline_ledger(
        events,
        (
            state.get("baseline_state")
            if isinstance(state.get("baseline_state"), dict)
            else None
        ),
    )
    if reconciliation.status in {"no_events", "unreconstructable"}:
        return None
    if not reconciliation.cutover_ready:
        return False
    if not baseline_ledger_authority_enabled(state):
        return False
    if "baseline_state" not in state:
        return False
    state.pop("baseline_state", None)
    return True


def _format_optional_metric(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def format_baseline_ledger_summary(
    reconciliation: BaselineLedgerReconciliation,
) -> list[str]:
    """Human-readable status/report lines for baseline ledger diagnostics."""
    promotions = reconciliation.event_count - reconciliation.reseed_event_count
    header = f"Baseline promotion events: {promotions}"
    if reconciliation.reseed_event_count:
        header += f" (+{reconciliation.reseed_event_count} speed-axis reseed(s))"
    lines = [header]
    if reconciliation.status == "no_events":
        lines.append("Baseline ledger state: no promotion events")
    elif reconciliation.status == "unreconstructable":
        lines.append("Baseline ledger state: unreconstructable")
    else:
        event = reconciliation.latest_event or {}
        if event.get("type") == SPEED_AXIS_RESEED_EVENT_TYPE:
            lines.append(
                "Latest baseline event: speed-axis reseed "
                f"trial #{event.get('source_trial_id', 'n/a')} "
                f"T{event.get('tier', 'n/a')} "
                f"{_format_optional_metric(event.get('previous_speed'))} -> "
                f"{_format_optional_metric(event.get('new_speed'))} t/s "
                f"era {event.get('previous_speed_era') or '<pre-boundary>'} -> "
                f"{event.get('new_speed_era') or 'n/a'} "
                f"at {event.get('timestamp', 'n/a')}"
            )
        else:
            lines.append(
                "Latest baseline event: "
                f"trial #{event.get('source_trial_id', 'n/a')} "
                f"T{event.get('tier', 'n/a')} "
                f"{_format_optional_metric(event.get('previous_quality'))} -> "
                f"{_format_optional_metric(event.get('new_quality'))} "
                f"at {event.get('timestamp', 'n/a')}"
            )
        lines.append(f"Baseline ledger state status: {reconciliation.status}")
    lines.append(
        "Baseline fold cutover dry-run: "
        f"{'ready' if reconciliation.cutover_ready else 'not_ready'}"
    )
    for blocker in reconciliation.cutover_blockers:
        lines.append(f"Baseline fold blocker: {blocker}")
    for warning in reconciliation.warnings:
        lines.append(f"Baseline ledger warning: {warning}")
    return lines

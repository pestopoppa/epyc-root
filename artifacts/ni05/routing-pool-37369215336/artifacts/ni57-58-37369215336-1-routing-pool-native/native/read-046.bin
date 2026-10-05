"""Reconstruct Pareto archive state from append-only autopilot journal rows."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Iterable

from src.autopilot_core.action_identity import config_fingerprint_from_row
from src.autopilot_core.learning_exclusions import (
    WITHIN_NOISE_EXCLUSIONS,
    row_is_representative_member,
)
from src.autopilot_core.pareto_math import dominates, hypervolume, median_objectives
from src.autopilot_core.tier_specs import (
    DEFAULT_FRONTIER_TIER,
    LEGACY_OBJECTIVE_POLICY,
    MIN_FRONTIER_EVAL_TIER,
    OBJECTIVE_AXIS_RATE,
    PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
    RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY,
    RATE_4D_OBJECTIVE_POLICY,
    TASK_RATE_OBJECTIVE_POLICY,
    TASK_RATE_REFERENCE_POINT,
    legacy_objectives_from_row,
    objective_axis_index,
    objectives_match_axes,
    rate_objectives_from_row,
    spec_for,
    task_rate_objectives_from_row,
)


SUPERSESSION_EVENT_TYPE = "supersession"


def _trial_id_from_row(row: dict[str, Any]) -> int | None:
    try:
        return int(row.get("trial_id"))
    except (TypeError, ValueError):
        return None


def _is_supersession_event(row: dict[str, Any]) -> bool:
    return row.get("type") == SUPERSESSION_EVENT_TYPE and "trial_id" not in row


def _fold_supersession_events(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply append-only supersession events as an in-memory view.

    The journal itself remains immutable: event rows specify field overrides for
    prior trial ids, and reconstruction folds those overrides before building
    Pareto/frontier views.
    """
    raw_rows = list(rows)
    overrides_by_trial: dict[int, dict[str, Any]] = {}
    applied_events = 0
    field_names: set[str] = set()

    for row in raw_rows:
        if not _is_supersession_event(row):
            continue
        fields = row.get("fields")
        targets = row.get("target_trial_ids")
        if not isinstance(fields, dict) or not isinstance(targets, list):
            continue
        event_applied = False
        for target in targets:
            try:
                trial_id = int(target)
            except (TypeError, ValueError):
                continue
            overrides_by_trial.setdefault(trial_id, {}).update(copy.deepcopy(fields))
            event_applied = True
        if event_applied:
            applied_events += 1
            field_names.update(str(field) for field in fields)

    folded_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if _is_supersession_event(row):
            continue
        trial_id = _trial_id_from_row(row)
        if trial_id is None or trial_id not in overrides_by_trial:
            folded_rows.append(row)
            continue
        folded = dict(row)
        folded.update(copy.deepcopy(overrides_by_trial[trial_id]))
        folded_rows.append(folded)

    meta = {
        "events_applied": applied_events,
        "target_trial_ids": sorted(overrides_by_trial),
        "field_names": sorted(field_names),
    }
    return folded_rows, meta


def fold_supersession_events(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Public read-view helper for folding append-only supersession events."""
    return _fold_supersession_events(rows)


def parse_journal_ts(value: Any) -> float | None:
    """Parse a journal timestamp value to Unix seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    return None


def _reference_point_for_policy(objective_policy: str) -> tuple[float, ...]:
    if objective_policy == TASK_RATE_OBJECTIVE_POLICY:
        return TASK_RATE_REFERENCE_POINT
    return spec_for(DEFAULT_FRONTIER_TIER).reference_point


def objectives_from_journal_row(
    row: dict[str, Any],
    *,
    objective_policy: str = LEGACY_OBJECTIVE_POLICY,
) -> list[float] | None:
    """Canonical objective tuple for a journal row, as a JSON-ready list."""
    try:
        tier = int(row.get("tier", DEFAULT_FRONTIER_TIER))
    except (TypeError, ValueError):
        tier = DEFAULT_FRONTIER_TIER
    # Each policy pins its OWN builder. `spec_for(...).objectives_from_row` reads the
    # policy stamped on the row, which is right for "replay whatever this row is" but
    # wrong here: an explicit `objective_policy=LEGACY` replay of a post-flip row would
    # have returned the tasks/hour vector labelled as tokens/second. Same 4D shape, so
    # nothing downstream could have caught it.
    if objective_policy == TASK_RATE_OBJECTIVE_POLICY:
        objectives = task_rate_objectives_from_row(row)
    elif objective_policy in {
        PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
        RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY,
        RATE_4D_OBJECTIVE_POLICY,
    }:
        objectives = rate_objectives_from_row(row)
    elif objective_policy == LEGACY_OBJECTIVE_POLICY:
        objectives = legacy_objectives_from_row(row)
    else:
        objectives = spec_for(tier).objectives_from_row(row)
    if objectives is None:
        return None
    return [float(value) for value in objectives]


def latest_journal_run_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the latest contiguous journal segment after a trial-id reset."""
    start_idx = 0
    prev_trial_id: int | None = None
    for idx, row in enumerate(rows):
        try:
            trial_id = int(row.get("trial_id"))
        except (TypeError, ValueError):
            continue
        if prev_trial_id is not None and trial_id < prev_trial_id:
            start_idx = idx
        prev_trial_id = trial_id

    selected = rows[start_idx:]
    first_trial = next((row for row in selected if _trial_id_from_row(row) is not None), None)
    meta = {
        "journal_run_start_index": start_idx,
        "journal_run_start_trial_id": first_trial.get("trial_id") if first_trial else None,
        "journal_run_start_ts": first_trial.get("timestamp") if first_trial else None,
    }
    return selected, meta


def reconstruct_archive_from_journal_rows(
    rows: Iterable[dict[str, Any]],
    session_start_ts: float | None,
    *,
    current_run_only: bool = False,
    max_trial_id: int | None = None,
    deinflate_before_ts: float | None = None,
    deinflate_factor: float = 1.0,
    exclude_before_ts: float | None = None,
    objective_policy: str = LEGACY_OBJECTIVE_POLICY,
) -> dict[str, Any] | None:
    """Replay journal rows into the dashboard/offline Pareto archive shape."""
    if objective_policy not in {
        LEGACY_OBJECTIVE_POLICY,
        TASK_RATE_OBJECTIVE_POLICY,
        PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
        RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY,
        RATE_4D_OBJECTIVE_POLICY,
    }:
        raise ValueError(f"unknown objective_policy: {objective_policy}")

    selected_rows = list(rows)
    run_meta: dict[str, Any] = {}
    if current_run_only:
        selected_rows, run_meta = latest_journal_run_rows(selected_rows)
    selected_rows, supersession_meta = _fold_supersession_events(selected_rows)

    all_entries: list[dict[str, Any]] = []
    frontiers_by_tier: dict[int, list[dict[str, Any]]] = {}
    hv_history_by_tier: dict[int, list[list[float]]] = {}
    t0_audit: list[dict[str, Any]] = []
    processed: list[tuple[int, dict[str, Any]]] = []
    repr_clusters: dict[tuple[int, str], dict[str, Any]] = {}

    # Exclusion telemetry — so a dashboard can SHOW why trials vanished from the
    # frontier instead of silently truncating. Two paths drop rows: a
    # `bug_corrupted_by` tag (rolled-back / corrupted trials) and the optional
    # `max_trial_id` cap. `journal_max_trial_id` is the highest trial id present
    # in the segment regardless of any filter, so callers can detect a stale
    # state counter that lags the journal.
    excluded_bug = {"count": 0, "max_trial_id": None}
    truncated_cap = {"count": 0, "max_trial_id": None}
    excluded_before_ts = {"count": 0, "max_trial_id": None}
    journal_max_trial_id: int | None = None

    def _bump(slot: dict[str, Any], tid: int) -> None:
        slot["count"] += 1
        if slot["max_trial_id"] is None or tid > slot["max_trial_id"]:
            slot["max_trial_id"] = tid

    for row in selected_rows:
        try:
            _row_tid = int(row.get("trial_id"))
        except (TypeError, ValueError):
            _row_tid = None
        if _row_tid is not None and (
            journal_max_trial_id is None or _row_tid > journal_max_trial_id
        ):
            journal_max_trial_id = _row_tid

        bug = row.get("bug_corrupted_by") or ""
        if bug and bug != "mad_noise":
            if _row_tid is not None:
                _bump(excluded_bug, _row_tid)
            continue
        # Trusted within-noise rows AND stamped clean representatives (decision (c)).
        trusted_within_noise = row_is_representative_member(row)

        try:
            tier = int(row.get("tier", DEFAULT_FRONTIER_TIER))
        except (TypeError, ValueError):
            tier = DEFAULT_FRONTIER_TIER
        audit_only = tier < MIN_FRONTIER_EVAL_TIER

        ts = parse_journal_ts(row.get("timestamp"))
        if session_start_ts is not None and (ts is None or ts < session_start_ts):
            continue
        try:
            trial_id = int(row.get("trial_id"))
        except (TypeError, ValueError):
            continue
        if exclude_before_ts is not None and (ts is None or ts < exclude_before_ts):
            _bump(excluded_before_ts, trial_id)
            continue
        if max_trial_id is not None and trial_id > max_trial_id:
            _bump(truncated_cap, trial_id)
            continue

        objectives = objectives_from_journal_row(row, objective_policy=objective_policy)
        if objectives is None:
            continue

        deinflated = False
        if (
            objective_policy == LEGACY_OBJECTIVE_POLICY
            and
            deinflate_before_ts is not None
            and deinflate_factor != 1.0
            and ts is not None
            and ts < deinflate_before_ts
            and objectives_match_axes(objectives, tier)
        ):
            # W3e: write the RATE axis by name, never by position.
            objectives = list(objectives)
            rate_index = objective_axis_index(OBJECTIVE_AXIS_RATE, tier)
            objectives[rate_index] = objectives[rate_index] * deinflate_factor
            deinflated = True

        shaped = {
            "trial_id": row.get("trial_id"),
            "objectives": list(objectives),
            "git_tag": row.get("git_tag", ""),
            "species": row.get("species", ""),
            "is_production_best": False,
            "timestamp": row.get("timestamp", ""),
            "reasoning": row.get("reasoning", ""),
            "eval_tier": tier,
            "speed_deinflated": deinflated,
        }
        if audit_only:
            t0_audit.append(shaped)
            continue
        if trusted_within_noise:
            fingerprint = config_fingerprint_from_row(row)
            key = (tier, fingerprint)
            cluster = repr_clusters.setdefault(
                key,
                {"objs": [], "last_tid": -1, "shaped": shaped},
            )
            cluster["objs"].append(objectives)
            if trial_id >= cluster["last_tid"]:
                cluster["last_tid"], cluster["shaped"] = trial_id, shaped
            continue
        processed.append((trial_id, shaped))

    for (_rep_tier, fingerprint), cluster in repr_clusters.items():
        representative = dict(cluster["shaped"])
        representative["objectives"] = list(median_objectives(cluster["objs"]))
        representative["config_fingerprint"] = fingerprint
        representative["n_reproductions"] = len(cluster["objs"])
        representative["is_representative"] = True
        processed.append((cluster["last_tid"], representative))

    processed.sort(key=lambda item: item[0])
    reference_point = _reference_point_for_policy(objective_policy)
    for trial_id, shaped in processed:
        tier = shaped["eval_tier"]
        objectives = shaped["objectives"]
        all_entries.append(shaped)
        frontier = frontiers_by_tier.setdefault(tier, [])
        if not any(dominates(front["objectives"], objectives) for front in frontier):
            frontiers_by_tier[tier] = [
                front for front in frontier
                if not dominates(objectives, front["objectives"])
            ]
            frontiers_by_tier[tier].append(shaped)
        tier_frontier = frontiers_by_tier[tier]
        tier_hv_history = hv_history_by_tier.setdefault(tier, [])
        hv = round(
            hypervolume(
                [front["objectives"] for front in tier_frontier],
                ref=reference_point,
            ),
            4,
        )
        if tier_hv_history:
            hv = max(tier_hv_history[-1][1], hv)
        tier_hv_history.append([trial_id, hv])

    if not all_entries and not t0_audit:
        return None

    canonical_frontier = frontiers_by_tier.get(DEFAULT_FRONTIER_TIER, [])
    canonical_hv_history = hv_history_by_tier.get(DEFAULT_FRONTIER_TIER, [])
    archive = {
        "frontier": canonical_frontier,
        "frontiers_by_tier": {
            str(tier): frontier for tier, frontier in sorted(frontiers_by_tier.items())
        },
        "all_entries": all_entries,
        "t0_audit": t0_audit,
        "hypervolume_history": canonical_hv_history,
        "hv_history_by_tier": {
            str(tier): hist for tier, hist in sorted(hv_history_by_tier.items())
        },
        "session_start_ts": session_start_ts,
        "canonical_tier": DEFAULT_FRONTIER_TIER,
        "objective_policy": objective_policy,
        "journal_max_trial_id": journal_max_trial_id,
        "exclusions": {
            "bug_corrupted": excluded_bug,
            "before_ts": excluded_before_ts,
            "exclude_before_ts": exclude_before_ts,
            "truncated_above_cap": truncated_cap,
            "max_trial_id_cap": max_trial_id,
        },
        "supersessions": supersession_meta,
    }
    archive.update(run_meta)
    return archive

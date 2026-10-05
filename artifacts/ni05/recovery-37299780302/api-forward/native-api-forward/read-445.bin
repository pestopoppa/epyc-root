"""Read-only journal snapshot replay diagnostic tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from src.autopilot_core.journal_reconstruction import reconstruct_archive_from_journal_rows
from src.autopilot_core.journal_snapshot_replay import (
    JOURNAL_SNAPSHOT_EVENT_TYPE,
    _fold_representative_tail_into_snapshot,
    _fold_tail_archive_into_snapshot,
    archive_payload_from_current_snapshot,
    archive_payload_from_verified_snapshot,
    build_snapshot_replay_diagnostic,
    format_snapshot_replay_summary,
    representative_replay_state_from_rows,
)


def _row(trial_id: int, *, quality: float = 1.0, speed: float = 40.0) -> dict[str, Any]:
    return {
        "trial_id": trial_id,
        "timestamp": f"2026-06-14T00:00:0{trial_id}Z",
        "species": "unit",
        "action_type": "seed_batch",
        "tier": 1,
        "quality": quality,
        "speed": speed,
        "cost": 0.2,
        "reliability": 0.9,
        "pareto_status": "frontier",
    }


def _snapshot_event(
    *,
    through_trial_id: int,
    snapshot: dict[str, Any],
    policy_version: str = "unit-policy-v1",
    parent_snapshot_hash: str = "",
    snapshot_hash: str | None = None,
) -> dict[str, Any]:
    event = {
        "type": JOURNAL_SNAPSHOT_EVENT_TYPE,
        "through_trial_id": through_trial_id,
        "snapshot": snapshot,
        "policy_version": policy_version,
        "actor": "unit-test",
        "parent_snapshot_hash": parent_snapshot_hash,
        "timestamp": "2026-06-14T00:00:03Z",
    }
    if snapshot_hash is None:
        payload = {
            "through_trial_id": through_trial_id,
            "snapshot": snapshot,
            "policy_version": policy_version,
            "parent_snapshot_hash": parent_snapshot_hash,
        }
        encoded = json.dumps(
            payload, sort_keys=True, default=str, separators=(",", ":")
        )
        snapshot_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    event["snapshot_hash"] = snapshot_hash
    return event


def _archive(rows: list[dict[str, Any]]) -> dict[str, Any]:
    archive = reconstruct_archive_from_journal_rows(rows, None)
    assert archive is not None
    return archive


def _archive_with_exclusions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    archive = _archive(rows)
    archive["exclusions"] = {
        "bug_corrupted": {"count": 1, "max_trial_id": 7},
        "before_ts": {"count": 2, "max_trial_id": 8},
        "exclude_before_ts": 1782511631.0,
        "truncated_above_cap": {"count": 3, "max_trial_id": 9},
        "max_trial_id_cap": 100,
    }
    return archive


def _load_snapshot_replay_cli():
    path = Path(__file__).resolve().parents[2] / "scripts/autopilot/journal_snapshot_replay.py"
    spec = importlib.util.spec_from_file_location("journal_snapshot_replay_cli", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_replay_reports_no_events() -> None:
    diagnostic = build_snapshot_replay_diagnostic([_row(1)], [])

    assert diagnostic.status == "no_events"
    assert diagnostic.bounded_replay_readiness == "not_ready"
    assert format_snapshot_replay_summary(diagnostic) == [
        "Journal snapshot events: 0",
        "Journal snapshot replay: no snapshot events",
    ]


def test_snapshot_replay_cli_strict_readiness_allows_opt_in_tail_fold() -> None:
    cli = _load_snapshot_replay_cli()

    assert (
        cli._strict_readiness(
            diagnostic_readiness="current",
            tail_fold_payload=None,
            allow_tail_fold=False,
        )
        == "current"
    )
    assert (
        cli._strict_readiness(
            diagnostic_readiness="tail_unverified",
            tail_fold_payload={"journal_max_trial_id": 2},
            allow_tail_fold=True,
        )
        == "tail_fold_ready"
    )
    assert (
        cli._strict_readiness(
            diagnostic_readiness="tail_unverified",
            tail_fold_payload={"journal_max_trial_id": 2},
            allow_tail_fold=False,
        )
        == "tail_unverified"
    )


def test_snapshot_replay_verifies_hash_without_archive_payload() -> None:
    rows = [_row(1), _row(2)]
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"metadata": {"note": "substrate only"}},
    )

    diagnostic = build_snapshot_replay_diagnostic(rows + [event], [event])

    assert diagnostic.status == "hash_verified"
    assert diagnostic.bounded_replay_readiness == "not_ready"
    assert diagnostic.hash_status == "match"
    assert diagnostic.tail_trial_count == 1
    assert diagnostic.tail_max_trial_id == 2
    assert diagnostic.warnings == ["latest snapshot payload has no archive view to verify"]


def test_snapshot_replay_reports_current_archive_prefix() -> None:
    rows = [_row(1, quality=1.2)]
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": _archive(rows)},
    )

    diagnostic = build_snapshot_replay_diagnostic(rows + [event], [event])

    assert diagnostic.status == "archive_prefix_match"
    assert diagnostic.bounded_replay_readiness == "current"
    assert diagnostic.hash_status == "match"
    assert diagnostic.tail_trial_count == 0
    assert diagnostic.warnings == []
    assert (
        "Journal snapshot bounded replay readiness: current"
        in format_snapshot_replay_summary(diagnostic)
    )


def test_current_snapshot_payload_helper_returns_verified_archive() -> None:
    rows = [_row(1, quality=1.2)]
    archive = _archive(rows)
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": archive},
    )

    payload = archive_payload_from_current_snapshot(rows + [event], [event])

    assert payload == archive
    assert payload is not archive


def test_snapshot_replay_flags_unverified_tail_after_matching_prefix() -> None:
    rows = [_row(1, quality=1.2), _row(2, quality=1.1)]
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": _archive([rows[0]])},
    )

    diagnostic = build_snapshot_replay_diagnostic(rows + [event], [event])

    assert diagnostic.status == "archive_prefix_match"
    assert diagnostic.bounded_replay_readiness == "tail_unverified"
    assert diagnostic.hash_status == "match"
    assert diagnostic.event_count == 1
    assert diagnostic.tail_trial_count == 1
    assert any("post-snapshot trials" in item for item in diagnostic.warnings)
    assert archive_payload_from_current_snapshot(rows + [event], [event]) is None


def test_verified_snapshot_payload_folds_safe_tail() -> None:
    rows = [_row(1, quality=1.2), _row(2, quality=1.4, speed=45.0)]
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": _archive([rows[0]])},
    )

    payload = archive_payload_from_verified_snapshot(rows + [event], [event])

    assert payload == _archive(rows)


def test_verified_snapshot_payload_preserves_exclusion_shape_when_folding_tail() -> None:
    snapshot_archive = _archive_with_exclusions([_row(1, quality=1.2)])
    tail_archive = _archive([_row(2, quality=1.4, speed=45.0)])

    payload = _fold_tail_archive_into_snapshot(snapshot_archive, tail_archive)

    assert payload is not None
    assert payload["exclusions"]["bug_corrupted"] == {"count": 1, "max_trial_id": 7}
    assert payload["exclusions"]["before_ts"] == {"count": 2, "max_trial_id": 8}
    assert payload["exclusions"]["exclude_before_ts"] == 1782511631.0
    assert payload["exclusions"]["truncated_above_cap"] == {
        "count": 3,
        "max_trial_id": 9,
    }
    assert payload["exclusions"]["max_trial_id_cap"] == 100


def test_verified_snapshot_payload_rejects_within_noise_tail() -> None:
    rows = [_row(1, quality=1.2), _row(2, quality=1.4, speed=45.0)]
    rows[1]["eval_details"] = {
        "learning_exclusion": {
            "by": "seq_accumulating",
            "reason": "unit-test sequential accumulation",
        }
    }
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": _archive([rows[0]])},
    )

    payload = archive_payload_from_verified_snapshot(rows + [event], [event])

    assert payload is None


def test_verified_snapshot_payload_folds_within_noise_tail_with_replay_state() -> None:
    rows = [_row(1, quality=1.2), _row(2, quality=1.4, speed=45.0)]
    rows[0]["eval_details"] = {
        "learning_exclusion": {
            "by": "seq_accumulating",
            "reason": "unit-test sequential accumulation",
        }
    }
    rows[1]["eval_details"] = {
        "learning_exclusion": {
            "by": "seq_accumulating",
            "reason": "unit-test sequential accumulation",
        }
    }
    prefix_rows = [rows[0]]
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={
            "archive": _archive(prefix_rows),
            "replay_state": representative_replay_state_from_rows(prefix_rows),
        },
    )

    payload = archive_payload_from_verified_snapshot(rows + [event], [event])

    assert payload == _archive(rows)


def test_verified_snapshot_payload_preserves_exclusions_in_representative_tail() -> None:
    rows = [
        _row(1, quality=1.2),
        _row(2, quality=1.4, speed=45.0),
        _row(3, quality=1.5, speed=46.0),
    ]
    rows[0]["eval_details"] = {
        "learning_exclusion": {
            "by": "seq_accumulating",
            "reason": "unit-test sequential accumulation",
        }
    }
    rows[1]["eval_details"] = {
        "learning_exclusion": {
            "by": "seq_accumulating",
            "reason": "unit-test sequential accumulation",
        }
    }
    rows[2]["bug_corrupted_by"] = "resource_contention"
    prefix_rows = [rows[0]]
    snapshot_archive = _archive_with_exclusions(prefix_rows)
    payload = _fold_representative_tail_into_snapshot(
        snapshot_archive,
        representative_replay_state_from_rows(prefix_rows),
        rows[1:],
        [],
        snapshot_archive["objective_policy"],
    )

    assert payload is not None
    assert payload["exclusions"]["bug_corrupted"] == {"count": 2, "max_trial_id": 7}
    assert payload["exclusions"]["before_ts"] == {"count": 2, "max_trial_id": 8}
    assert payload["exclusions"]["exclude_before_ts"] == 1782511631.0
    assert payload["exclusions"]["truncated_above_cap"] == {
        "count": 3,
        "max_trial_id": 9,
    }
    assert payload["exclusions"]["max_trial_id_cap"] == 100


def test_snapshot_replay_requires_matching_hash_for_ready_status() -> None:
    rows = [_row(1)]
    event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": _archive(rows)},
        snapshot_hash="not-the-real-hash",
    )

    diagnostic = build_snapshot_replay_diagnostic(rows + [event], [event])

    assert diagnostic.status == "archive_prefix_hash_unverified"
    assert diagnostic.bounded_replay_readiness == "not_ready"
    assert diagnostic.hash_status == "mismatch"
    assert "latest snapshot_hash does not match event payload" in diagnostic.warnings


def test_snapshot_replay_flags_post_snapshot_supersession_prefix_drift() -> None:
    rows = [_row(1, quality=2.0), _row(2, quality=1.0)]
    event = _snapshot_event(
        through_trial_id=2,
        snapshot={"archive": _archive(rows)},
    )
    supersession = {
        "type": "supersession",
        "target_trial_ids": [1],
        "fields": {
            "bug_corrupted_by": "resource_contention",
            "bug_corrupted_reason": "synthetic contamination window",
        },
        "reason": "synthetic contamination window",
        "policy_version": "supersession-v1",
        "actor": "unit-test",
        "timestamp": "2026-06-14T00:00:04Z",
    }

    diagnostic = build_snapshot_replay_diagnostic(
        rows + [event, supersession],
        [event, supersession],
    )

    assert diagnostic.status == "archive_prefix_drift"
    assert diagnostic.bounded_replay_readiness == "prefix_invalidated"
    assert diagnostic.post_snapshot_prefix_event_count == 1
    assert any("post-snapshot supersession" in item for item in diagnostic.warnings)
    assert any("archive payload differs" in item for item in diagnostic.warnings)


def test_snapshot_replay_latest_invalid_event_blocks_older_ready_snapshot() -> None:
    rows = [_row(1, quality=1.2)]
    valid_event = _snapshot_event(
        through_trial_id=1,
        snapshot={"archive": _archive(rows)},
    )
    invalid_latest = {
        "type": JOURNAL_SNAPSHOT_EVENT_TYPE,
        "snapshot": {"archive": _archive(rows)},
        "policy_version": "unit-policy-v2",
        "actor": "unit-test",
        "timestamp": "2026-06-14T00:00:04Z",
    }

    diagnostic = build_snapshot_replay_diagnostic(
        rows + [valid_event, invalid_latest],
        [valid_event, invalid_latest],
    )

    assert diagnostic.status == "invalid_latest_event"
    assert diagnostic.bounded_replay_readiness == "not_ready"
    assert diagnostic.event_count == 2
    assert diagnostic.warnings == [
        "latest snapshot event has no usable through_trial_id"
    ]

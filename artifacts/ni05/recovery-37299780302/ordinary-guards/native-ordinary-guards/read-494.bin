"""Tests for default-inert AutoMem memory action primitives."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from orchestration.repl_memory.memory_actions import (
    MemoryAction,
    MemoryActionError,
    MemoryActionStore,
)


def _rows(store: MemoryActionStore) -> list[dict]:
    return [
        json.loads(line)
        for line in store.ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_upsert_is_idempotent_and_syncs_status_projection(tmp_path):
    store = MemoryActionStore(tmp_path / "memory")
    now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    action = MemoryAction(
        action="UPSERT",
        channel="status",
        coordinate="autopilot/p2.9",
        key="host-covariates",
        content="Host covariates are attached before optimizer scoring.",
        source="test",
        tags=("mh-9", "automem"),
    )

    first = store.apply(action, now=now)
    second = store.apply(action, now=now)

    assert first.changed is True
    assert first.status == "inserted"
    assert second.changed is False
    assert second.status == "unchanged"
    assert len(_rows(store)) == 1
    status_md = first.projection_paths["status"].read_text(encoding="utf-8")
    assert "autopilot/p2.9 :: host-covariates" in status_md
    assert "Host covariates are attached" in status_md


def test_upsert_updates_when_payload_changes(tmp_path):
    # `when_not_to_use` became REQUIRED for strategy/pattern records
    # (memory_actions.normalized(): "strategy records require when_not_to_use").
    # This test is about upsert-on-change, not about validation, so it supplies the
    # field; the validation itself is covered by the rejection tests below.
    store = MemoryActionStore(tmp_path / "memory")
    first = MemoryAction(
        action="UPSERT",
        channel="strategy",
        coordinate="autopilot/memory",
        key="schema",
        content="Use append-only ledger.",
        source="test",
        when_not_to_use="Not for high-write-rate telemetry.",
    )
    changed = MemoryAction(
        action="UPSERT",
        channel="strategy",
        coordinate="autopilot/memory",
        key="schema",
        content="Use append-only ledger plus generated projections.",
        source="test",
        when_not_to_use="Not for high-write-rate telemetry.",
    )

    insert = store.apply(first)
    update = store.apply(changed)

    assert insert.status == "inserted"
    assert update.status == "updated"
    assert len(_rows(store)) == 2
    strategy_md = update.projection_paths["strategy"].read_text(encoding="utf-8")
    assert "append-only ledger plus generated projections" in strategy_md
    assert "Use append-only ledger.\n" not in strategy_md


def test_append_preserves_repeated_log_entries(tmp_path):
    store = MemoryActionStore(tmp_path / "memory")
    base = {
        "action": "APPEND",
        "channel": "log",
        "coordinate": "autopilot/run-42",
        "key": "decision",
        "source": "test",
    }

    first = store.apply(MemoryAction(content="Planner proposed memory schema.", **base))
    second = store.apply(MemoryAction(content="Verifier accepted memory schema.", **base))

    assert first.status == "appended"
    assert second.status == "appended"
    assert first.memory_id == second.memory_id
    assert len(_rows(store)) == 2
    log_md = second.projection_paths["log"].read_text(encoding="utf-8")
    assert "Planner proposed memory schema." in log_md
    assert "Verifier accepted memory schema." in log_md


def test_create_refuses_duplicate_coordinate_key(tmp_path):
    store = MemoryActionStore(tmp_path / "memory")
    first = MemoryAction(
        action="CREATE",
        channel="inventory",
        coordinate="episodic-store",
        key="memory-actions",
        content="Initial memory action inventory row.",
        source="test",
    )
    duplicate = MemoryAction(
        action="CREATE",
        channel="inventory",
        coordinate="episodic-store",
        key="memory-actions",
        content="Duplicate should not replace the original.",
        source="test",
    )

    created = store.apply(first)
    exists = store.apply(duplicate)

    assert created.changed is True
    assert created.status == "created"
    assert exists.changed is False
    assert exists.status == "exists"
    assert len(_rows(store)) == 1
    inventory_md = exists.projection_paths["inventory"].read_text(encoding="utf-8")
    assert "Initial memory action inventory row." in inventory_md
    assert "Duplicate should not replace" not in inventory_md


def test_status_inventory_strategy_projection_files_are_always_synced(tmp_path):
    store = MemoryActionStore(tmp_path / "memory")
    result = store.apply(
        MemoryAction(
            action="UPSERT",
            channel="plan",
            coordinate="autopilot/checkpoint",
            key="automem-schema",
            content="Land schema before runtime integration.",
            source="test",
        )
    )

    # `pattern` joined PROJECTION_CHANNELS alongside the original five; every
    # declared channel must be materialised on every apply, not just the one written.
    assert set(result.projection_paths) == {
        "inventory",
        "log",
        "pattern",
        "plan",
        "status",
        "strategy",
    }
    for path in result.projection_paths.values():
        assert path.exists()
    assert "Land schema before runtime integration." in (tmp_path / "memory" / "plan.md").read_text(
        encoding="utf-8"
    )
    assert "_No entries._" in (tmp_path / "memory" / "status.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "action",
    [
        # Was `action="DELETE"`. DELETE is now a FIRST-CLASS action (it is in
        # VALID_ACTIONS and appends a tombstone), so it is no longer an example of
        # an invalid action. The case is retargeted at an action outside
        # VALID_ACTIONS so this test still proves unknown actions are rejected.
        MemoryAction(
            action="PURGE",
            channel="status",
            coordinate="autopilot",
            key="bad",
            content="bad",
        ),
        MemoryAction(
            action="UPSERT",
            channel="status",
            coordinate="../trace",
            key="bad",
            content="bad",
        ),
        MemoryAction(
            action="UPSERT",
            channel="status",
            coordinate="autopilot",
            key="bad",
            content="bad\x00content",
        ),
    ],
)
def test_rejects_invalid_actions_and_unsafe_fields(tmp_path, action):
    store = MemoryActionStore(tmp_path / "memory")

    with pytest.raises(MemoryActionError):
        store.apply(action)

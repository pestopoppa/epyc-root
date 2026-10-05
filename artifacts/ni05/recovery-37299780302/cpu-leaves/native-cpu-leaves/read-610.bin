"""HS-TD-4: prepared-action mutation and receipt conformance fixtures."""

from __future__ import annotations

import json

import pytest

from src.typed_decisions.prepared_action import (
    SCHEMA_VERSION,
    append_receipt,
    make_receipt,
    prepare_action,
    validate_prepared_action,
)

CATALOG = {"inspect": {"tool": "read"}, "apply": {"tool": "write"}}
READ_SET = {"task": "revision-1", "permission_scope": "repo-a"}


def _prepared():
    return prepare_action(
        task_revision="revision-1",
        catalog=CATALOG,
        read_set=READ_SET,
        expires_at_ns=100,
        requested_model="local",
        resolved_model="local-v1",
    )


def _validate(prepared, **overrides):
    args = {
        "selected_id": "inspect",
        "current_task_revision": "revision-1",
        "current_catalog": CATALOG,
        "current_read_set": READ_SET,
        "authorized": True,
        "model_available": True,
        "now_ns": 99,
    }
    args.update(overrides)
    return validate_prepared_action(prepared, **args)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"selected_id": None}, "abstained"),
        ({"selected_id": "invented"}, "unknown_id"),
        ({"now_ns": 100}, "expired"),
        ({"current_task_revision": "revision-2"}, "stale"),
        ({"current_offered_choices": ["inspect"]}, "stale"),
        (
            {"current_catalog": {"inspect": {"tool": "changed"}, "apply": {"tool": "write"}}},
            "stale",
        ),
        ({"current_read_set": {"task": "revision-1", "permission_scope": "repo-b"}}, "stale"),
        ({"authorized": False}, "unauthorized"),
        ({"model_available": False}, "model_unavailable"),
    ],
)
def test_rejected_selections_use_incumbent_fallback(mutation, expected):
    result = _validate(_prepared(), **mutation)
    assert result.status == expected
    assert result.fallback == "incumbent_fallback"


def test_accepted_selection_and_receipt_are_complete(tmp_path):
    prepared = _prepared()
    result = _validate(prepared)
    assert result.status == "accepted"
    assert result.fallback is None
    receipt = make_receipt(
        prepared,
        result,
        authorization_result="allowed",
        component_timing_ms={"selection": 1.0, "validation": 2.0, "dispatch": 3.0},
        total_timing_ms=6.0,
        observed_downstream_outcome={"status": "returned", "detail": "dict"},
    )
    path = tmp_path / "decision_receipts.jsonl"
    append_receipt(path, receipt)
    row = json.loads(path.read_text().strip())
    assert row == {
        "schema_version": SCHEMA_VERSION,
        "task_revision": "revision-1",
        "offered_choices": ["apply", "inspect"],
        "catalog_fingerprint": prepared.catalog_fingerprint,
        "read_set_fingerprint": prepared.read_set_fingerprint,
        "expires_at_ns": 100,
        "selected_id": "inspect",
        "requested_model": "local",
        "resolved_model": "local-v1",
        "validation_result": "accepted",
        "authorization_result": "allowed",
        "fallback": None,
        "component_timing_ms": {"selection": 1.0, "validation": 2.0, "dispatch": 3.0},
        "total_timing_ms": 6.0,
        "observed_downstream_outcome": {"status": "returned", "detail": "dict"},
    }


def test_only_host_eligible_choices_are_offered():
    prepared = prepare_action(
        task_revision="revision-1",
        catalog=CATALOG,
        read_set=READ_SET,
        expires_at_ns=100,
        offered_choices=["inspect"],
    )
    assert prepared.offered_choices == ("inspect",)
    assert _validate(prepared, selected_id="apply").status == "unknown_id"

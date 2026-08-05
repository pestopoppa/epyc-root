"""Disposition-schema regression tests for the research intake validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/research-intake/scripts/validate_intake.py"
)
SPEC = importlib.util.spec_from_file_location("validate_intake_dispositions", VALIDATOR_PATH)
validate_intake = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_intake)


def _entry(**updates: object) -> dict:
    entry = {
        "id": "intake-001",
        "arxiv_id": None,
        "url": "https://example.test/source",
        "source_type": "blog",
        "title": "Example",
        "categories": ["example"],
        "novelty": "medium",
        "relevance": "medium",
        "discovered_via": "input",
        "verdict": "worth_investigating",
        "ingested_date": "2026-08-05",
    }
    entry.update(updates)
    return entry


def test_integrated_disposition_requires_route_and_evidence() -> None:
    errors = validate_intake.validate_index(
        [_entry(integration_disposition="integrated")], {"example"}
    )

    assert any("requires disposition_evidence" in error for error in errors)
    assert any("requires a created or updated handoff" in error for error in errors)


def test_awaiting_dive_requires_stage1_verification() -> None:
    errors = validate_intake.validate_index(
        [
            _entry(
                integration_disposition="awaiting_dive",
                disposition_evidence=["Needs a primary-source dive."],
            )
        ],
        {"example"},
    )

    assert any("requires verification='stage1-unverified'" in error for error in errors)


def test_valid_dispositions_pass() -> None:
    entries = [
        _entry(
            integration_disposition="integrated",
            disposition_evidence=["Routed to owner."],
            handoffs_updated=["handoffs/active/owner.md"],
        )
    ]

    assert validate_intake.validate_index(entries, {"example"}) == []

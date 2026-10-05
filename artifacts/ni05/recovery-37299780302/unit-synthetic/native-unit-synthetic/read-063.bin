"""Tests for AutoPilot running-state attestation trust helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.autopilot_core.attestation_trust import (
    EXOGENOUS_ATTESTATION_STALE,
    attestation_changed,
    attestation_precondition,
)


def _write_attestation(path: Path, generated_at: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "generated_at": generated_at,
                "trigger": "unit",
                "summary": {"issue_count": 7},
            }
        ),
        encoding="utf-8",
    )


def test_precondition_disabled_when_not_required(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AUTOPILOT_ATTESTATION_REQUIRED", raising=False)

    result = attestation_precondition(tmp_path / "missing.json")

    assert result["ok"] is True
    assert result["status"] == "disabled"


def test_precondition_marks_stale_when_required(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTOPILOT_ATTESTATION_REQUIRED", "1")
    path = tmp_path / "latest.json"
    _write_attestation(path, "2026-06-12T00:00:00Z")

    result = attestation_precondition(
        path,
        now=datetime(2026, 6, 12, 5, 0, tzinfo=timezone.utc),
        max_age_s=4 * 60 * 60,
    )

    assert result["ok"] is False
    assert result["status"] == "stale"
    assert result["category"] == EXOGENOUS_ATTESTATION_STALE
    assert result["issue_count"] == 7


def test_attestation_changed_uses_artifact_fingerprint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AUTOPILOT_ATTESTATION_REQUIRED", "1")
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    _write_attestation(before_path, "2026-06-12T00:00:00Z")
    _write_attestation(after_path, "2026-06-12T01:00:00Z")

    before = attestation_precondition(before_path, now=0, max_age_s=10**12)
    after = attestation_precondition(after_path, now=0, max_age_s=10**12)

    assert attestation_changed(before, after) is True
    assert attestation_changed(before, before) is False

"""Tests for the read-only AutoPilot baseline authority report."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from baseline_authority_report import (  # noqa: E402
    build_baseline_authority_report,
    main,
    render_markdown,
)
from src.autopilot_core.authority_consent import CONSENT_PATH_ENV  # noqa: E402
from src.autopilot_core.baseline_ledger import (  # noqa: E402
    BASELINE_LEDGER_AUTHORITY_STATE_FLAG,
)


def _grant_baseline_ledger_consent(monkeypatch, tmp_path: Path) -> None:
    """Grant operator consent hermetically.

    Baseline-ledger authority is fail-closed behind the operator-owned,
    gitignored ``orchestration/authority_consent.json``; without pinning the
    consent path, results depend on whether that file exists in the checkout.
    """
    consent = tmp_path / "authority_consent.json"
    consent.write_text(json.dumps({"baseline_ledger": "allow"}), encoding="utf-8")
    monkeypatch.setenv(CONSENT_PATH_ENV, str(consent))


def _promotion(
    source_trial_id: int,
    *,
    tier: int = 1,
    previous_quality: float = 1.4,
    new_quality: float = 1.8,
    baseline_state: object | None = None,
) -> dict[str, Any]:
    return {
        "type": "baseline_promotion",
        "source_trial_id": source_trial_id,
        "tier": tier,
        "previous_quality": previous_quality,
        "new_quality": new_quality,
        "baseline_state": (
            {"baselines_by_tier": {str(tier): new_quality}}
            if baseline_state is None
            else baseline_state
        ),
        "timestamp": "2026-06-14T00:00:00+00:00",
    }


def test_report_marks_matching_baseline_fold_ok(monkeypatch, tmp_path: Path) -> None:
    _grant_baseline_ledger_consent(monkeypatch, tmp_path)
    rows = [_promotion(7, new_quality=1.9)]
    report = build_baseline_authority_report(
        {
            BASELINE_LEDGER_AUTHORITY_STATE_FLAG: True,
            "baseline_state": {"baselines_by_tier": {"1": 1.9}},
        },
        rows,
    )

    assert report == {
        "ok": True,
        "status": "match",
        "authority_enabled": True,
        "event_count": 1,
        "valid_snapshot_count": 1,
        "cutover_ready": True,
        "cutover_blockers": [],
        "warnings": [],
        "recommendation": (
            "baseline ledger fold is ready for evidence-plane W4 acceptance"
        ),
        "latest_source_trial_id": 7,
        "latest_tier": 1,
        "latest_previous_quality": 1.4,
        "latest_new_quality": 1.9,
    }


def test_report_distinguishes_ready_fold_from_enabled_authority() -> None:
    rows = [_promotion(7, new_quality=1.9)]
    report = build_baseline_authority_report(
        {"baseline_state": {"baselines_by_tier": {"1": 1.9}}},
        rows,
    )

    assert report["ok"] is True
    assert report["authority_enabled"] is False
    assert report["recommendation"] == (
        "baseline ledger fold is ready; enable baseline ledger authority "
        "after restart cutover gates pass"
    )


def test_report_marks_drift_not_ok_with_recommendation() -> None:
    report = build_baseline_authority_report(
        {"baseline_state": {"baselines_by_tier": {"1": 1.7}}},
        [_promotion(7, new_quality=1.9)],
    )

    assert report["ok"] is False
    assert report["status"] == "drift"
    assert report["cutover_ready"] is False
    assert report["cutover_blockers"] == [
        "ledger fold does not match current state baseline (drift)"
    ]
    assert report["recommendation"] == (
        "keep live baseline_state authority until ledger fold blockers are resolved"
    )


def test_render_markdown_uses_baseline_ledger_summary(monkeypatch, tmp_path: Path) -> None:
    _grant_baseline_ledger_consent(monkeypatch, tmp_path)
    report = build_baseline_authority_report(
        {
            BASELINE_LEDGER_AUTHORITY_STATE_FLAG: True,
            "baseline_state": {"baselines_by_tier": {"1": 1.9}},
        },
        [_promotion(7, new_quality=1.9)],
    )

    rendered = render_markdown(report)

    assert "# AutoPilot Baseline Authority Report" in rendered
    assert "- Baseline promotion events: 1" in rendered
    assert "- Latest baseline event: trial #7 T1 1.400 -> 1.900" in rendered
    assert "- Baseline ledger authority enabled: true" in rendered
    assert (
        "- Recommendation: baseline ledger fold is ready for evidence-plane W4 "
        "acceptance"
    ) in rendered


def test_cli_json_strict_returns_zero_when_ok(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(
        json.dumps({"baseline_state": {"baselines_by_tier": {"1": 1.9}}}),
        encoding="utf-8",
    )
    journal_path.write_text(json.dumps(_promotion(7, new_quality=1.9)), encoding="utf-8")

    rc = main(
        [
            "--state",
            str(state_path),
            "--journal",
            str(journal_path),
            "--json",
            "--strict",
        ]
    )
    out = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert out["ok"] is True
    assert out["latest_source_trial_id"] == 7


def test_cli_json_strict_returns_one_when_not_ok(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(
        json.dumps({"baseline_state": {"baselines_by_tier": {"1": 1.7}}}),
        encoding="utf-8",
    )
    journal_path.write_text(json.dumps(_promotion(7, new_quality=1.9)), encoding="utf-8")

    rc = main(
        [
            "--state",
            str(state_path),
            "--journal",
            str(journal_path),
            "--json",
            "--strict",
        ]
    )
    out = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert out["ok"] is False
    assert out["status"] == "drift"


def test_cli_returns_two_for_missing_files(tmp_path: Path, capsys) -> None:
    rc = main(
        [
            "--state",
            str(tmp_path / "missing_state.json"),
            "--journal",
            str(tmp_path / "missing_journal.jsonl"),
        ]
    )

    assert rc == 2
    assert "state file does not exist" in capsys.readouterr().err


def test_cli_returns_two_for_non_object_state(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text("[]", encoding="utf-8")
    journal_path.write_text("", encoding="utf-8")

    rc = main(["--state", str(state_path), "--journal", str(journal_path)])

    assert rc == 2
    assert "state file is not a JSON object" in capsys.readouterr().err

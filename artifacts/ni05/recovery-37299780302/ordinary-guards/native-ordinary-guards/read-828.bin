"""Tests for the journal-frontier StrategyStore projection report."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import strategy_projection_report as spr  # noqa: E402


def _frontier_row(trial_id: int) -> dict[str, object]:
    return {
        "trial_id": trial_id,
        "timestamp": "2026-06-19T00:00:00Z",
        "species": "prompt_forge",
        "action_type": "code_mutation",
        "tier": 1,
        "quality": 1.2,
        "speed": 40.0,
        "cost": 0.2,
        "reliability": 0.9,
        "pareto_status": "frontier",
        "hypothesis": "repair parser",
        "expected_mechanism": "targeted_fix",
        "outcome_status": "ok",
        "bug_corrupted_by": "",
        "eval_details": {},
    }


def test_render_markdown_summarizes_projection_report() -> None:
    rendered = spr.render_markdown(
        {
            "ok": False,
            "expected_count": 1,
            "projected_count": 0,
            "skipped_count": 2,
            "missing_count": 1,
            "unexpected_count": 0,
            "mismatch_count": 0,
            "dry_run": True,
            "would_insert_count": 1,
            "inserted_count": 0,
            "missing": [{"trial_id": 7, "strategy_id": "journal-frontier-trial-7"}],
            "unexpected": [],
            "mismatches": [],
        }
    )

    assert "# AutoPilot Strategy Projection Report" in rendered
    assert "- Status: drift" in rendered
    assert "expected=1, projected=0, skipped=2" in rendered
    assert "trial #7: journal-frontier-trial-7" in rendered


def test_cli_strict_reports_missing_projection(tmp_path: Path, capsys) -> None:
    journal_dir = tmp_path / "journal"
    strategy_path = tmp_path / "strategies"
    journal_dir.mkdir()
    strategy_path.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text(
        json.dumps(_frontier_row(7)) + "\n",
        encoding="utf-8",
    )

    rc = spr.main(
        [
            "--journal-dir",
            str(journal_dir),
            "--strategy-path",
            str(strategy_path),
            "--json",
            "--strict",
        ]
    )
    out = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert out["ok"] is False
    assert out["missing"] == [
        {"trial_id": 7, "strategy_id": "journal-frontier-trial-7"}
    ]


def test_cli_write_missing_syncs_projection(tmp_path: Path, capsys) -> None:
    journal_dir = tmp_path / "journal"
    strategy_path = tmp_path / "strategies"
    journal_dir.mkdir()
    strategy_path.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text(
        json.dumps(_frontier_row(8)) + "\n",
        encoding="utf-8",
    )

    rc = spr.main(
        [
            "--journal-dir",
            str(journal_dir),
            "--strategy-path",
            str(strategy_path),
            "--json",
            "--strict",
            "--write-missing",
            "--allow-hash-fallback",
        ]
    )
    out = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert out["ok"] is True
    assert out["inserted_count"] == 1
    assert out["missing_count"] == 0


def test_cli_write_missing_requires_embedding_without_hash_override(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    journal_dir = tmp_path / "journal"
    strategy_path = tmp_path / "strategies"
    journal_dir.mkdir()
    strategy_path.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text(
        json.dumps(_frontier_row(9)) + "\n",
        encoding="utf-8",
    )

    class BrokenEmbedder:
        def __init__(self, config):
            self.config = config

        def embed_text(self, text: str):
            raise RuntimeError("semantic embeddings unavailable")

    monkeypatch.setattr(spr, "TaskEmbedder", BrokenEmbedder)

    rc = spr.main(
        [
            "--journal-dir",
            str(journal_dir),
            "--strategy-path",
            str(strategy_path),
            "--json",
            "--strict",
            "--write-missing",
        ]
    )

    assert rc == 2
    assert "semantic embeddings unavailable" in capsys.readouterr().err


def test_cli_returns_two_for_missing_strategy_path(tmp_path: Path, capsys) -> None:
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text("", encoding="utf-8")

    rc = spr.main(
        [
            "--journal-dir",
            str(journal_dir),
            "--strategy-path",
            str(tmp_path / "missing-strategies"),
        ]
    )

    assert rc == 2
    assert "strategy path does not exist" in capsys.readouterr().err

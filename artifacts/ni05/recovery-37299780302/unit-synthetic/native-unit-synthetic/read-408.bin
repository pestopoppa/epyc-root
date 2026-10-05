from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import handoff_closure_candidate_report as report_mod  # noqa: E402


def _write_seed_file(path: Path, *, evidence_trial_ids: list[int] | None = None) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "slug": "example-handoff",
                    "tranche": "guardrail",
                    "species": "prompt_forge",
                    "entry_type": "convention",
                    "title": "Example handoff",
                    "description": "example handoff memory",
                    "insight": "Example memory should inform planning.",
                    "evidence_trial_ids": evidence_trial_ids or [],
                    "source_handoff": "example-handoff / second-handoff",
                    "seeded_reason": "test",
                    "confidence": "high",
                    "bind_status": "context",
                    "bind_identifiers": ["example"],
                }
            ]
        ),
        encoding="utf-8",
    )


def _write_strategy_db(path: Path, *, evidence_trial_ids: list[int]) -> None:
    path.mkdir()
    conn = sqlite3.connect(path / "strategies.db")
    try:
        conn.execute(
            "CREATE TABLE strategies ("
            "id TEXT PRIMARY KEY, description TEXT, insight TEXT, "
            "source_trial_id INTEGER, species TEXT, created_at TEXT, "
            "metadata_json TEXT, entry_type TEXT, evidence_trial_ids TEXT)"
        )
        conn.execute(
            "INSERT INTO strategies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "opseed-guardrail-example-handoff",
                "example handoff memory",
                "Example memory should inform planning.",
                42,
                "prompt_forge",
                "2026-06-28T00:00:00Z",
                json.dumps(
                    {
                        "seed_campaign": "operator-handoff-distillation",
                        "source_handoff": "example-handoff / second-handoff",
                    }
                ),
                "convention",
                json.dumps(evidence_trial_ids),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _write_journal(path: Path, trial_id: int) -> None:
    path.mkdir()
    row = {
        "trial_id": trial_id,
        "timestamp": "2026-06-28T00:00:00Z",
        "species": "prompt_forge",
        "action_type": "code_mutation",
        "tier": 1,
        "quality": 2.1,
        "speed": 40.0,
        "cost": 0.1,
        "reliability": 1.0,
        "pareto_status": "frontier",
        "git_tag": "autopilot/trial-42",
        "outcome_status": "ok",
        "bug_corrupted_by": "",
        "eval_details": {},
    }
    (path / "autopilot_journal.jsonl").write_text(json.dumps(row) + "\n")


def test_pending_seed_rows_are_not_closure_candidates(tmp_path: Path) -> None:
    seed_file = tmp_path / "seeds.yaml"
    strategy_path = tmp_path / "missing-strategies"
    journal_dir = tmp_path / "journal"
    _write_seed_file(seed_file)
    journal_dir.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text("", encoding="utf-8")

    report = report_mod.build_handoff_closure_candidate_report(
        seed_file=seed_file,
        strategy_path=strategy_path,
        journal_dir=journal_dir,
    )

    assert report["pending_seed_count"] == 1
    assert report["closure_candidate_count"] == 0
    assert report["rows"][0]["closure_status"] == "pending_seed"
    assert report["handoff_writes_permitted"] is False


def test_applied_memory_without_declared_evidence_is_not_closure(
    tmp_path: Path,
) -> None:
    seed_file = tmp_path / "seeds.yaml"
    strategy_path = tmp_path / "strategies"
    journal_dir = tmp_path / "journal"
    _write_seed_file(seed_file)
    _write_strategy_db(strategy_path, evidence_trial_ids=[42])
    _write_journal(journal_dir, 42)

    report = report_mod.build_handoff_closure_candidate_report(
        seed_file=seed_file,
        strategy_path=strategy_path,
        journal_dir=journal_dir,
    )

    assert report["applied_count"] == 1
    assert report["memory_only_count"] == 1
    assert report["closure_candidate_count"] == 0
    assert report["rows"][0]["closure_status"] == "memory_only_not_closure"


def test_declared_clean_evidence_creates_review_only_candidate(
    tmp_path: Path,
) -> None:
    seed_file = tmp_path / "seeds.yaml"
    strategy_path = tmp_path / "strategies"
    journal_dir = tmp_path / "journal"
    _write_seed_file(seed_file, evidence_trial_ids=[42])
    _write_strategy_db(strategy_path, evidence_trial_ids=[42])
    _write_journal(journal_dir, 42)

    report = report_mod.build_handoff_closure_candidate_report(
        seed_file=seed_file,
        strategy_path=strategy_path,
        journal_dir=journal_dir,
    )

    assert report["closure_candidate_count"] == 1
    assert report["rows"][0]["closure_status"] == "candidate_review_required"
    assert report["rows"][0]["recommendation"].endswith("do not auto-write")
    assert report["handoffs"]["example-handoff"]["closure_candidate_count"] == 1
    assert report["handoffs"]["second-handoff"]["closure_candidate_count"] == 1


def test_markdown_makes_memory_only_boundary_explicit() -> None:
    rendered = report_mod.render_markdown(
        {
            "campaign": "operator-handoff-distillation",
            "governance_mode": "suggest_only",
            "handoff_writes_permitted": False,
            "row_count": 1,
            "applied_count": 1,
            "pending_seed_count": 0,
            "memory_only_count": 1,
            "closure_candidate_count": 0,
            "warnings": [],
            "rows": [{"closure_candidate": False}],
        }
    )

    assert "Handoff writes permitted: false" in rendered
    assert "Seeded planner memory alone is not handoff closure evidence" in rendered


def test_main_writes_optional_json_and_markdown_outputs(
    tmp_path: Path,
    capsys,
) -> None:
    seed_file = tmp_path / "seeds.yaml"
    strategy_path = tmp_path / "strategies"
    journal_dir = tmp_path / "journal"
    out_json = tmp_path / "reports" / "closure.json"
    out_md = tmp_path / "reports" / "closure.md"
    _write_seed_file(seed_file, evidence_trial_ids=[42])
    _write_strategy_db(strategy_path, evidence_trial_ids=[42])
    _write_journal(journal_dir, 42)

    code = report_mod.main(
        [
            "--seed-file",
            str(seed_file),
            "--strategy-path",
            str(strategy_path),
            "--journal-dir",
            str(journal_dir),
            "--json",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )

    assert code == 0
    stdout = json.loads(capsys.readouterr().out)
    persisted = json.loads(out_json.read_text(encoding="utf-8"))
    assert stdout["closure_candidate_count"] == 1
    assert persisted["closure_candidate_count"] == 1
    assert "# AutoPilot Handoff Closure Candidate Report" in out_md.read_text(
        encoding="utf-8"
    )

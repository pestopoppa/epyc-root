from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402


LEGACY_FAILURE = """VIOLATIONS:
  - Quality regression: 2.400 vs baseline 9.900 (-75.8%, threshold: -5%)
  - Suite 'coder' regression: -6.900 (threshold: -0.1)
"""


def _entry(**overrides) -> JournalEntry:
    data = dict(
        trial_id=38,
        timestamp="2026-05-27T16:15:44Z",
        species="seeder",
        action_type="seed_batch",
        tier=0,
        quality=2.4,
        speed=18.9,
        cost=0.5,
        reliability=1.0,
        pareto_status="dominated",
        failure_analysis=LEGACY_FAILURE,
    )
    data.update(overrides)
    return JournalEntry(**data)


def test_summary_text_sanitizes_legacy_scale_failure_analysis(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(tier=1))

    summary = journal.summary_text()

    assert "baseline 9.900" not in summary
    assert "Suite 'coder' regression: -6.900" not in summary
    assert "legacy-scale failure_analysis omitted" in summary
    assert "q=2.400" in summary


def test_summary_text_downclasses_tier0_quality(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(tier=0, quality=2.4))

    summary = journal.summary_text()

    assert "T0 audit-only sentinel" in summary
    assert "quality hidden" in summary
    assert "q=2.400" not in summary


def test_summary_text_hides_bug_corrupted_metrics(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            tier=1,
            quality=2.4,
            bug_corrupted_by="ec9622d",
            bug_corrupted_reason="pre-tier-filter planner telemetry",
        )
    )

    summary = journal.summary_text()

    assert "CORRUPTED_BY=ec9622d" in summary
    assert "metrics/reason hidden" in summary
    assert "pre-tier-filter planner telemetry" not in summary
    assert "q=2.400" not in summary


def test_insight_renderers_sanitize_legacy_scale_failure_analysis(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(hypothesis="", expected_mechanism=""))

    insights = journal.insights_text()
    structured = journal.insights_structured_text()

    assert "baseline 9.900" not in insights
    assert "baseline 9.900" not in structured
    assert "legacy-scale failure_analysis omitted" in insights
    assert "legacy-scale failure_analysis omitted" in structured


def test_current_scale_failure_analysis_is_preserved(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            failure_analysis=(
                "VIOLATIONS:\n"
                "  - Quality regression: 0.600 vs baseline 1.160 "
                "(-48.3%, threshold: -5%)"
            )
        )
    )

    summary = journal.summary_text()

    assert "baseline 1.160" in summary
    assert "legacy-scale failure_analysis omitted" not in summary

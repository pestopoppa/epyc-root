from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ledger_mod = importlib.import_module("scripts.economics.ledger")
digest = importlib.import_module("scripts.autopilot.digest")


@dataclass
class _DigestEntry:
    action_type: str
    pareto_status: str
    tier: int = 1
    bug_corrupted_by: str = ""


class _DigestJournal:
    def __init__(self, entries: list[_DigestEntry]) -> None:
        self._entries = entries

    def entries_with_supersessions(self) -> list[_DigestEntry]:
        return self._entries


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_economic_ledger_summarizes_real_sources(tmp_path: Path) -> None:
    planner = tmp_path / "logs" / "planner_archive.jsonl"
    _append_jsonl(
        planner,
        [
            {
                "ts_iso": "2026-06-10T12:00:00+00:00",
                "provider": "codex",
                "role": "critique",
                "total_cost_usd": 1.25,
                "duration_ms": 2500,
            },
            {
                "ts": datetime(2026, 6, 11, tzinfo=timezone.utc).timestamp(),
                "type": "planner_coordinator",
                "mode": "draft_critique",
                "duration_s": 3,
            },
            {"ts_iso": "2026-06-01T12:00:00+00:00", "total_cost_usd": 99.0},
            {"not": "json"},
        ],
    )
    with planner.open("a") as handle:
        handle.write("{malformed\n")

    journal_dir = tmp_path / "orchestration"
    _append_jsonl(
        journal_dir / "autopilot_journal.jsonl",
        [
            {
                "timestamp": "2026-06-10T12:30:00+00:00",
                "action_type": "seed_batch",
                "species": "seeder",
                "tier": 1,
                "eval_details": {"details": {"eval_wall_s": 7200}},
            },
            {
                "timestamp": "2026-06-11T13:30:00+00:00",
                "action_type": "deep_eval",
                "species": "evaluator",
                "eval_wall_s": 3600,
            },
        ],
    )

    cloud = tmp_path / "orchestration" / "cloud_costs.yaml"
    cloud.write_text(
        "entries:\n"
        "  - date: 2026-06-10\n"
        "    amount_usd: 2.50\n"
        "    provider: anthropic\n"
        "    purpose: fable5-review\n"
    )

    progress_root = tmp_path / "root_progress"
    progress_file = progress_root / "2026-06" / "2026-06-10.md"
    progress_file.parent.mkdir(parents=True)
    progress_file.write_text("### Verdict\n- Next work: gated restart decision\n")

    orch_progress = tmp_path / "logs" / "progress"
    _append_jsonl(
        orch_progress / "2026-06-10.jsonl",
        [
            {
                "event_type": "task_started",
                "task_id": "chat-1",
                "timestamp": "2026-06-10T12:00:00+00:00",
            },
            {
                "event_type": "routing_decision",
                "task_id": "chat-1",
                "timestamp": "2026-06-10T12:00:01+00:00",
            },
            {
                "event_type": "task_completed",
                "task_id": "chat-1",
                "timestamp": "2026-06-10T12:00:04+00:00",
            },
        ],
    )

    summary = ledger_mod.summarize_economics(
        week_start=date(2026, 6, 8),
        planner_archive=planner,
        journal_dir=journal_dir,
        cloud_costs=cloud,
        rules_path=tmp_path / "missing_rules.yaml",
        progress_root=progress_root,
        orch_progress_dir=orch_progress,
    )

    assert summary.planner.calls == 2
    assert summary.planner.billable_calls == 1
    assert summary.planner.total_usd == 1.25
    assert summary.planner.by_purpose_usd["planner:critique"] == 1.25
    assert summary.planner.malformed_rows == 1
    assert summary.manual.total_usd == 2.5
    assert summary.local.trials == 2
    assert summary.local.eval_hours == 3.0
    assert summary.local.by_consumer_s["seed_batch:seeder"] == 7200
    assert summary.throughput.progress_decision_markers >= 2
    assert summary.throughput.routing_decisions == 1
    assert summary.throughput.task_completions == 1
    assert summary.throughput.median_task_duration_s == 4.0
    assert summary.review.planner_spend_triggered is False
    assert summary.review.operator_gate_latency_triggered is None

    report = ledger_mod.render_report(summary)
    assert "total cloud spend: $3.7500" in report
    assert "local eval wall time by consumer" in report.lower()
    assert "proxy" in report
    assert "Standing decision-rule review" in report
    assert "hold: below threshold" in report


def test_digest_economics_section_is_best_effort(tmp_path: Path) -> None:
    now = datetime(2026, 6, 12, 12, tzinfo=timezone.utc)
    section = digest._economics_section(now, repo_root=tmp_path)
    assert section[0] == "### Economics (last 7 days)"
    assert any("planner cloud spend" in line for line in section)
    assert any("total cloud spend" in line for line in section)
    assert any("local eval wall time" in line for line in section)
    assert any("planner monthly projection" in line and "(hold)" in line for line in section)
    assert any("operator gate-latency rule: not evaluated" in line for line in section)
    assert any("economic rules source: built-in defaults" in line for line in section)


def test_digest_mechanism_effectiveness_is_observe_only() -> None:
    section = digest._mechanism_effectiveness_section(
        _DigestJournal(
            [
                _DigestEntry("prompt_mutation", "frontier"),
                _DigestEntry("gepa_optimize", "dominated"),
                _DigestEntry("numeric_trial", "frontier"),
                _DigestEntry("structural_experiment", "dominated"),
                _DigestEntry("code_mutation", "frontier"),
                _DigestEntry("seed_batch", "dominated"),
                _DigestEntry("deep_eval", "frontier", tier=0),
                _DigestEntry("numeric_trial", "frontier", bug_corrupted_by="badc0de"),
            ]
        )
    )

    text = "\n".join(section)
    assert section[0] == "### Mechanism effectiveness (observe-only)"
    assert "| `prompt_search` | 2 | 1 | 0.5 | `gepa_optimize`, `prompt_mutation` |" in text
    assert (
        "| `deterministic_code_config` | 3 | 2 | 0.667 | `code_mutation`, `numeric_trial`, `structural_experiment` |"
        in text
    )
    assert "| `data_training` | 1 | 0 | 0 | `seed_batch` |" in text
    assert "evaluation_control" not in text
    assert "observe-only diagnostic" in text


def test_planner_spend_rule_triggers_with_low_threshold(tmp_path: Path) -> None:
    planner = tmp_path / "logs" / "planner_archive.jsonl"
    _append_jsonl(
        planner,
        [
            {
                "ts_iso": "2026-06-10T12:00:00+00:00",
                "provider": "claude",
                "role": "draft",
                "total_cost_usd": 10.0,
            },
        ],
    )
    rules = tmp_path / "orchestration" / "economic_rules.yaml"
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_text(
        "planner_monthly_spend_threshold_usd: 1.0\n"
        "operator_gate_latency_threshold_days: 3.0\n"
    )

    summary = ledger_mod.summarize_economics(
        week_start=date(2026, 6, 8),
        planner_archive=planner,
        journal_dir=tmp_path / "orchestration",
        cloud_costs=tmp_path / "missing_cloud_costs.yaml",
        rules_path=rules,
        progress_root=tmp_path / "progress",
        orch_progress_dir=tmp_path / "logs" / "progress",
    )

    assert summary.rules.source_exists is True
    assert summary.review.planner_spend_triggered is True
    report = ledger_mod.render_report(summary)
    assert "TRIGGER: raise F3-W3a planner-distill priority" in report

    section = digest._economics_section(datetime(2026, 6, 12, 12, tzinfo=timezone.utc), repo_root=tmp_path)
    assert any("planner monthly projection" in line and "(triggered)" in line for line in section)
    assert any("economic rules source: configured" in line for line in section)

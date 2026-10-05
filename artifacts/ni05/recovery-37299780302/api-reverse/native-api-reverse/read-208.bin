from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

core_v2_select = importlib.import_module("core_v2_select")


def _row(trial_id: int, results: list[dict]) -> dict:
    return {"trial_id": trial_id, "eval_details": {"question_results": results}}


def _ledger_row(
    trial_id: int,
    *,
    timestamp: str,
    results: list[dict],
    bug_corrupted_by: str = "",
    outcome_status: str = "ok",
) -> dict:
    return {
        "trial_id": trial_id,
        "timestamp": timestamp,
        "species": "numeric_swarm",
        "action_type": "numeric_trial",
        "tier": 1,
        "quality": 1.5,
        "speed": 42.0,
        "cost": 0.5,
        "reliability": 1.0,
        "pareto_status": "dominated",
        "eval_details": {"question_results": results},
        "bug_corrupted_by": bug_corrupted_by,
        "outcome_status": outcome_status,
    }


def _ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def test_collect_item_stats_treats_missing_partition_as_core() -> None:
    rows = [
        _row(
            1,
            [
                {"qid": "q1", "suite": "math", "correct": True},
                {"qid": "q2", "suite": "math", "correct": True, "partition": "audit"},
            ],
        ),
        _row(2, [{"qid": "q1", "suite": "math", "correct": False}]),
        {"type": "supersession", "target_trial_ids": [1]},
    ]

    stats = core_v2_select.collect_item_stats(rows, include_partitions={"core"})

    assert set(stats) == {("math", "q1")}
    assert stats[("math", "q1")].attempts == 2
    assert stats[("math", "q1")].correct == 1
    assert stats[("math", "q1")].p_correct == 0.5


def test_select_core_items_prefers_medium_items_and_stratifies() -> None:
    stats = {
        ("math", "easy"): core_v2_select.ItemStats(
            qid="easy", suite="math", attempts=5, correct=5
        ),
        ("math", "medium-math"): core_v2_select.ItemStats(
            qid="medium-math", suite="math", attempts=5, correct=3
        ),
        ("coder", "medium-coder"): core_v2_select.ItemStats(
            qid="medium-coder", suite="coder", attempts=5, correct=2
        ),
        ("coder", "hard"): core_v2_select.ItemStats(
            qid="hard", suite="coder", attempts=5, correct=0
        ),
    }

    selected = core_v2_select.select_core_items(
        stats,
        target_size=2,
        min_attempts=2,
        p_min=0.2,
        p_max=0.8,
        max_per_suite=1,
    )

    assert [(item.suite, item.qid) for item in selected] == [
        ("coder", "medium-coder"),
        ("math", "medium-math"),
    ]


def test_pool_lookup_maps_stable_eval_qids_to_full_question_rows(tmp_path: Path) -> None:
    pool = tmp_path / "question_pool.jsonl"
    question = {
        "id": "math-1",
        "suite": "math",
        "prompt": "What is two plus two?",
        "expected": "4",
        "scoring_method": "exact_match",
    }
    stable_qid = core_v2_select._stable_question_qid("math", question["prompt"])
    pool.write_text(
        json.dumps({"__pool_metadata__": True}) + "\n" + json.dumps(question) + "\n",
        encoding="utf-8",
    )

    lookup = core_v2_select.load_pool_lookup(pool)

    assert lookup[("math", "math-1")]["prompt"] == question["prompt"]
    assert lookup[("math", stable_qid)]["id"] == "math-1"


def test_write_core_jsonl_uses_pool_rows_and_records_selection(tmp_path: Path) -> None:
    selected = [
        core_v2_select.ItemStats(qid="q-stable", suite="math", attempts=3, correct=2),
    ]
    report = {
        "generated_at": "2026-06-14T00:00:00Z",
        "parameters": {"target_size": 1},
        "selected_count": 1,
    }
    out = tmp_path / "core_v2.jsonl"

    unresolved = core_v2_select.write_core_jsonl(
        path=out,
        core_id="core_v2",
        selected=selected,
        pool_lookup={
            (
                "math",
                "q-stable",
            ): {
                "id": "math-1",
                "suite": "math",
                "prompt": "2+2?",
                "expected": "4",
                "scoring_method": "exact_match",
            }
        },
        report=report,
    )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert unresolved == []
    assert rows[0]["__core_metadata__"] is True
    assert rows[0]["core_id"] == "core_v2"
    assert rows[1]["id"] == "math-1"
    assert rows[1]["core_selection"]["p_correct"] == 0.666667


def test_cli_writes_report_and_core_file(tmp_path: Path, monkeypatch) -> None:
    pool = tmp_path / "pool.jsonl"
    journal = tmp_path / "journal.jsonl"
    report = tmp_path / "report.json"
    core = tmp_path / "core.jsonl"
    question = {
        "id": "math-1",
        "suite": "math",
        "prompt": "2+2?",
        "expected": "4",
        "scoring_method": "exact_match",
    }
    stable_qid = core_v2_select._stable_question_qid("math", question["prompt"])
    pool.write_text(
        json.dumps({"__pool_metadata__": True}) + "\n" + json.dumps(question) + "\n",
        encoding="utf-8",
    )
    journal.write_text(
        "\n".join(
            [
                json.dumps(
                    _row(
                        1,
                        [{"qid": stable_qid, "suite": "math", "correct": True}],
                    )
                ),
                json.dumps(
                    _row(
                        2,
                        [{"qid": stable_qid, "suite": "math", "correct": False}],
                    )
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "core_v2_select.py",
            "--journal",
            str(journal),
            "--pool",
            str(pool),
            "--out-core",
            str(core),
            "--report-json",
            str(report),
            "--target-size",
            "1",
            "--min-attempts",
            "2",
        ],
    )

    assert core_v2_select.main() == 0

    report_obj = json.loads(report.read_text(encoding="utf-8"))
    core_rows = [json.loads(line) for line in core.read_text(encoding="utf-8").splitlines()]
    assert report_obj["selected_count"] == 1
    assert report_obj["eligible_items"] == 1
    assert core_rows[1]["id"] == "math-1"


def test_ledger_source_uses_rollover_supersession_trust_and_era_fence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pool = tmp_path / "pool.jsonl"
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    state_json = tmp_path / "state.json"
    report = tmp_path / "report.json"
    core = tmp_path / "core.jsonl"
    question = {
        "id": "math-1",
        "suite": "math",
        "prompt": "2+2?",
        "expected": "4",
        "scoring_method": "exact_match",
    }
    stable_qid = core_v2_select._stable_question_qid("math", question["prompt"])
    pool.write_text(
        json.dumps({"__pool_metadata__": True}) + "\n" + json.dumps(question) + "\n",
        encoding="utf-8",
    )
    old = "2026-06-01T00:00:00+00:00"
    current = "2026-06-28T00:00:00+00:00"
    fence = "2026-06-26T22:07:11+00:00"
    (journal_dir / "autopilot_journal.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    _ledger_row(
                        990,
                        timestamp=old,
                        results=[{"qid": stable_qid, "suite": "math", "correct": True}],
                    )
                ),
                json.dumps(
                    _ledger_row(
                        1000,
                        timestamp=current,
                        results=[{"qid": stable_qid, "suite": "math", "correct": True}],
                    )
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (journal_dir / "autopilot_journal_1.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    _ledger_row(
                        1001,
                        timestamp=current,
                        results=[{"qid": stable_qid, "suite": "math", "correct": False}],
                    )
                ),
                json.dumps(
                    _ledger_row(
                        1002,
                        timestamp=current,
                        results=[{"qid": stable_qid, "suite": "math", "correct": True}],
                    )
                ),
                json.dumps(
                    {
                        "type": "supersession",
                        "target_trial_ids": [1002],
                        "fields": {"bug_corrupted_by": "resource_contention"},
                        "reason": "unit-test folded trust exclusion",
                        "policy_version": "unit-test",
                        "actor": "test",
                        "timestamp": current,
                    }
                ),
                json.dumps(
                    _ledger_row(
                        1003,
                        timestamp=current,
                        results=[{"qid": stable_qid, "suite": "math", "correct": True}],
                        outcome_status="skipped",
                    )
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    state_json.write_text(json.dumps({"pareto_exclude_before_ts": _ts(fence)}), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "core_v2_select.py",
            "--source",
            "ledger",
            "--journal-dir",
            str(journal_dir),
            "--state-json",
            str(state_json),
            "--pool",
            str(pool),
            "--out-core",
            str(core),
            "--report-json",
            str(report),
            "--target-size",
            "1",
            "--min-attempts",
            "2",
        ],
    )

    assert core_v2_select.main() == 0

    report_obj = json.loads(report.read_text(encoding="utf-8"))
    provenance = report_obj["source_provenance"]
    core_rows = [json.loads(line) for line in core.read_text(encoding="utf-8").splitlines()]
    assert report_obj["parameters"]["source"] == "ledger"
    assert report_obj["source_rows"] == 2
    assert report_obj["selected_count"] == 1
    assert report_obj["selected"][0]["p_correct"] == 0.5
    assert provenance["loaded_trial_rows"] == 5
    assert provenance["trusted_rows"] == 2
    assert provenance["untrusted_trial_ids"] == [1002, 1003]
    assert provenance["era_excluded_trial_ids"] == [990]
    assert any(path.endswith("autopilot_journal_1.jsonl") for path in provenance["journal_batches"])
    assert core_rows[1]["id"] == "math-1"

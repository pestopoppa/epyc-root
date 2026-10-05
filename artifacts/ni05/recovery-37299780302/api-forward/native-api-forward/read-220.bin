from __future__ import annotations

import json
from pathlib import Path

from scripts.analysis import dar4b_sweep as sweep


def _write_progress(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_parse_omega_normalizes_weights():
    assert sweep.parse_omega("4,1") == (0.8, 0.2)


def test_load_frozen_decisions_derives_normalized_cost_from_cost_terms(tmp_path):
    _write_progress(
        tmp_path / "2026-07-04.jsonl",
        [
            {
                "event_type": "routing_decision",
                "task_id": "task-1",
                "timestamp": "2026-07-04T00:00:00Z",
                "data": {
                    "chosen_action": "fast",
                    "action_topk": ["slow", "fast"],
                    "q_topk": [0.9, 0.7],
                    "selection_score_topk": [0.4, 0.65],
                    "cost_term_topk": [0.5, 0.05],
                },
            }
        ],
    )

    decisions, meta = sweep.load_frozen_decisions(tmp_path, cost_lambda=0.5)

    assert meta["eligible_decisions"] == 1
    assert decisions[0].baseline_action == "fast"
    assert decisions[0].normalized_cost_topk == (1.0, 0.1)


def test_run_sweep_can_flip_quality_and_cost_preferences(tmp_path):
    _write_progress(
        tmp_path / "2026-07-04.jsonl",
        [
            {
                "event_type": "routing_decision",
                "task_id": "task-1",
                "timestamp": "2026-07-04T00:00:00Z",
                "data": {
                    "chosen_action": "fast",
                    "action_topk": ["slow", "fast"],
                    "q_topk": [0.9, 0.7],
                    "selection_score_topk": [0.4, 0.65],
                    "cost_term_topk": [0.5, 0.05],
                },
            }
        ],
    )
    decisions, _ = sweep.load_frozen_decisions(tmp_path, cost_lambda=0.5)

    points = sweep.run_sweep(
        decisions,
        omega_grid=[(0.9, 0.1), (0.1, 0.9)],
        tau_grid=[1.0],
        cost_lambda=0.5,
    )

    quality_first, cost_first = points
    assert quality_first.action_counts == {"slow": 1}
    assert quality_first.flip_rate_vs_baseline == 1.0
    assert cost_first.action_counts == {"fast": 1}
    assert cost_first.flip_rate_vs_baseline == 0.0


def test_write_outputs_creates_expected_artifacts(tmp_path):
    summary = {
        "protocol": "dar4b_offline_routing_preference_sweep_v1",
        "measurement_class": "offline_proxy_observation",
        "source": {"eligible_decisions": 1, "total_routing_events": 1},
        "cost_lambda": 0.5,
        "sweeps": [
            {
                "omega_perf": 0.5,
                "omega_cost": 0.5,
                "tau": 1.0,
                "eligible_decisions": 1,
                "mean_q": 0.7,
                "mean_normalized_cost": 0.1,
                "mean_score": 0.65,
                "mean_margin": 0.2,
                "flip_rate_vs_baseline": 0.0,
                "flip_rate_vs_chosen": 0.0,
                "action_counts": {"fast": 1},
                "pareto_frontier": True,
            }
        ],
        "pareto": [
            {
                "omega_perf": 0.5,
                "omega_cost": 0.5,
                "tau": 1.0,
                "eligible_decisions": 1,
                "mean_q": 0.7,
                "mean_normalized_cost": 0.1,
                "mean_score": 0.65,
                "mean_margin": 0.2,
                "flip_rate_vs_baseline": 0.0,
                "flip_rate_vs_chosen": 0.0,
                "action_counts": {"fast": 1},
                "pareto_frontier": True,
            }
        ],
        "notes": ["offline only"],
    }

    sweep._write_outputs(tmp_path, summary)

    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "sweep.jsonl").exists()
    assert (tmp_path / "pareto.json").exists()
    assert (tmp_path / "summary.md").exists()

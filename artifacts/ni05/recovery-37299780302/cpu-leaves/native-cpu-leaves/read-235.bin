"""Pareto dashboard objective-policy truthfulness.

The Pareto panel payload must surface task_rate/goodput/tokens-per-solved (+
offered_load) telemetry per shipped point — computed via the CANONICAL helpers
in src.autopilot_core.tier_specs, joined from the same folded journal rows the
panel reconstructs from. Current-scope frontier membership must follow the live
policy stamped in AutoPilot state; legacy t/s is historical comparison only.
"""
import asyncio
import json
from pathlib import Path

import src.api.routes.dashboard as dash
from src.autopilot_core.tier_specs import (
    RATE_4D_OBJECTIVE_POLICY,
    seq_task_rate_qph_from_row,
)

DASHBOARD_HTML = Path(dash.__file__).with_name("dashboard.html")


def _row(tid, q, s, ts="2026-07-27T12:00:00+00:00", *, tier=1, cost=0.5, rel=1.0,
         n_questions=None, eval_wall_s=None, details=None, eval_concurrency=None,
         objective_policy=RATE_4D_OBJECTIVE_POLICY):
    row = {
        "trial_id": tid, "tier": tier, "quality": q, "speed": s, "cost": cost,
        "reliability": rel, "timestamp": ts,
        "config_snapshot": {"type": "seed_batch", "n_questions": 10},
    }
    if n_questions is not None:
        row["n_questions"] = n_questions
    if eval_wall_s is not None:
        row["eval_wall_s"] = eval_wall_s
    eval_details = {"objective_policy_live": objective_policy} if objective_policy else {}
    if details is not None:
        eval_details["details"] = details
    if eval_concurrency is not None:
        eval_details["eval_concurrency"] = eval_concurrency
    if eval_details:
        row["eval_details"] = eval_details
    return row


def _journal(tmp_path, monkeypatch, rows):
    p = tmp_path / "autopilot_journal.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(dash, "_AUTOPILOT_JOURNAL_PATH", p)
    return p


def _state(tmp_path, monkeypatch, **extra):
    p = tmp_path / "autopilot_state.json"
    data = {"trial_counter": 999}
    data.update(extra)
    p.write_text(json.dumps(data))
    monkeypatch.setattr(dash, "_AUTOPILOT_STATE_PATH", p)
    return p


def _call(scope="current", max_dominated=600):
    resp = asyncio.run(dash.pareto(max_dominated=max_dominated, scope=scope))
    return json.loads(resp.body)


def _points(payload):
    """Every shipped scatter point, keyed by trial_id."""
    pts = {}
    for lst in (
        payload["frontier"],
        payload["dominated"],
        payload["t0_audit"],
        *payload["frontiers_by_tier"].values(),
    ):
        for e in lst:
            pts[e["trial_id"]] = e
    return pts


# Fixture geometry (tier 1):
#   trial 1: legacy frontier (mid speed), SLOW eval  → task_rate 10 q/h
#   trial 2: legacy frontier (top quality), FAST eval → task_rate 100 q/h
#   trial 3: legacy frontier (top speed), SLOWEST eval → task_rate 5 q/h
# Under task_rate_3d_v1, trial 2 dominates 1 AND 3 → 2 legacy points drop.
ROW_1 = _row(1, 1.8, 50.0, n_questions=10, eval_wall_s=3600.0,
             details={"tokens_generated": 4500.0, "correct": 3},
             eval_concurrency=3)
ROW_2 = _row(2, 1.9, 40.0, n_questions=10, eval_wall_s=360.0,
             details={"tokens_generated": 1200.0, "correct": 6},
             eval_concurrency=3)
ROW_3 = _row(3, 1.7, 60.0, n_questions=10, eval_wall_s=7200.0)
# trial 4: dominated everywhere + NO eval-wall/n fields → null-safe path
ROW_4 = _row(4, 1.0, 10.0)


def test_pareto_payload_carries_task_rate_fields(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch, [ROW_1, ROW_2, ROW_3, ROW_4])
    _state(tmp_path, monkeypatch)
    pts = _points(_call())

    p1 = pts[1]
    assert p1["task_rate_qph"] == 10.0
    assert p1["goodput_qph"] == round((1.8 / 3.0) * 10.0, 2)
    assert p1["tokens_per_solved"] == 1500.0
    assert p1["offered_load"] == {"eval_concurrency": 3}

    # trial 3 has rate inputs but no token details → tokens_per_solved is None,
    # offered_load is None (no eval_concurrency recorded)
    p3 = pts[3]
    assert p3["task_rate_qph"] == 5.0
    assert p3["tokens_per_solved"] is None
    assert p3["offered_load"] is None


def test_pareto_payload_null_safe_when_row_lacks_fields(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch, [ROW_1, ROW_2, ROW_3, ROW_4])
    _state(tmp_path, monkeypatch)
    pts = _points(_call())

    p4 = pts[4]
    # Fields are PRESENT (schema-stable for the client) but explicitly null —
    # never 0.0, which would plot a fake point at 0 q/h.
    assert p4["task_rate_qph"] is None
    assert p4["goodput_qph"] is None
    assert p4["tokens_per_solved"] is None
    assert p4["offered_load"] is None


def test_pareto_payload_separates_outer_lane_from_decision_question_mix(
    tmp_path, monkeypatch
):
    mixed = _row(
        5, 1.8, 40.0, n_questions=50, eval_wall_s=1800.0,
        details={
            "question_tier_mix": {"1": 17, "2": 17, "3": 16},
            "tier_mix_provenance": {
                "tier_mix_policy": "equal_thirds_v1",
                "tier_mix_targets": {"1": 17, "2": 17, "3": 16},
                "drawn_n": 50,
                "core_rotation_index": 75,
            },
            "core_id": "tier_stratified_equal_thirds_v1_seed_42_n50_rot75",
            "n_scored": 49,
            "partition_counts": {"core": 49, "audit": 10, "tool_sentinel": 5},
        },
    )
    _journal(tmp_path, monkeypatch, [mixed])
    _state(tmp_path, monkeypatch, pareto_objective_policy=RATE_4D_OBJECTIVE_POLICY)

    payload = _call()
    point = _points(payload)[5]

    assert point["eval_tier"] == 1
    assert point["decision_question_mix"] == {
        "policy": "equal_thirds_v1",
        "targets": {"1": 17, "2": 17, "3": 16},
        "target_n": 50,
        "scored_n": 49,
        "core_id": "tier_stratified_equal_thirds_v1_seed_42_n50_rot75",
        "rotation_index": 75,
    }
    assert payload["current_decision_question_mix"] == point["decision_question_mix"]


def test_toggle_data_integrity_matches_canonical_helpers(tmp_path, monkeypatch):
    """Every shipped point's task_rate/goodput equals the canonical helper output."""
    rows = [ROW_1, ROW_2, ROW_3, ROW_4]
    _journal(tmp_path, monkeypatch, rows)
    _state(tmp_path, monkeypatch)
    pts = _points(_call())
    rows_by_tid = {r["trial_id"]: r for r in rows}

    assert set(pts) == {1, 2, 3, 4}
    for tid, entry in pts.items():
        row = rows_by_tid[tid]
        expected_rate = seq_task_rate_qph_from_row(row)
        if expected_rate is not None:
            assert entry["task_rate_qph"] == round(expected_rate, 2)
            assert entry["goodput_qph"] == round((row["quality"] / 3.0) * expected_rate, 2)
            assert entry["task_rate_status"] == "measured"
        else:
            assert entry["task_rate_qph"] is None
            assert entry["goodput_qph"] is None


def test_all_eras_scrubs_counterfactual_legacy_task_rates(tmp_path, monkeypatch):
    legacy = _row(
        1,
        1.8,
        50.0,
        n_questions=55,
        eval_wall_s=0.054,
        objective_policy="legacy_4d_v1",
    )
    active = _row(2, 1.9, 40.0, n_questions=10, eval_wall_s=360.0)
    _journal(tmp_path, monkeypatch, [legacy, active])
    _state(tmp_path, monkeypatch, pareto_objective_policy=RATE_4D_OBJECTIVE_POLICY)

    pts = _points(_call(scope="all_eras"))

    assert pts[1]["task_rate_qph"] is None
    assert pts[1]["task_rate_status"] == "legacy_or_unstamped_policy"
    assert pts[2]["task_rate_qph"] == 100.0
    assert pts[2]["task_rate_status"] == "measured"


def test_current_frontier_follows_active_policy_and_compares_legacy(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch, [ROW_1, ROW_2, ROW_3])
    _state(tmp_path, monkeypatch, pareto_objective_policy=RATE_4D_OBJECTIVE_POLICY)
    d = _call()

    assert d["objective_policy"] == RATE_4D_OBJECTIVE_POLICY
    assert d["active_objective_policy"] == RATE_4D_OBJECTIVE_POLICY
    assert d["decision_grade"] is True
    assert sorted(e["trial_id"] for e in d["frontier"]) == [2]

    div = d["objective_policy_comparison"]
    assert div["error"] is None
    assert div["legacy_policy"] == "legacy_4d_v1"
    assert div["active_policy"] == RATE_4D_OBJECTIVE_POLICY
    # All three points are legacy-frontier (quality/speed trade-off), but trial 2
    # dominates 1 and 3 under the active 4D task-rate policy.
    assert div["legacy_frontier_trial_ids"] == [1, 2, 3]
    assert div["active_frontier_trial_ids"] == [2]
    assert div["dropped_legacy_trial_ids"] == [1, 3]
    assert div["dropped_legacy_count"] == 2
    assert div["added_active_count"] == 0
    assert div["frontiers_differ"] is True


def test_objective_comparison_quiet_when_frontiers_agree(tmp_path, monkeypatch):
    # Single admitted trial → identical frontiers under both policies.
    _journal(tmp_path, monkeypatch, [ROW_2])
    _state(tmp_path, monkeypatch, pareto_objective_policy=RATE_4D_OBJECTIVE_POLICY)
    div = _call()["objective_policy_comparison"]
    assert div["error"] is None
    assert div["legacy_frontier_trial_ids"] == [2]
    assert div["active_frontier_trial_ids"] == [2]
    assert div["dropped_legacy_count"] == 0
    assert div["frontiers_differ"] is False


def test_objective_comparison_null_safe_without_rows():
    div = dash._objective_policy_comparison_summary(None, {}, RATE_4D_OBJECTIVE_POLICY)
    assert div["error"] == "no journal rows available"
    assert div["dropped_legacy_count"] == 0
    assert div["frontiers_differ"] is False


def test_unknown_active_policy_fails_visibly_to_legacy_comparator(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch, [ROW_1, ROW_2])
    _state(tmp_path, monkeypatch, pareto_objective_policy="future_unknown_v99")

    d = _call()

    assert d["objective_policy"] == "legacy_4d_v1"
    assert d["decision_grade"] is False
    assert "unknown pareto_objective_policy" in d["objective_policy_warning"]


def test_all_eras_is_explicitly_non_decision_grade_legacy_comparator(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch, [ROW_1, ROW_2, ROW_3])
    _state(tmp_path, monkeypatch, pareto_objective_policy=RATE_4D_OBJECTIVE_POLICY)

    d = _call(scope="all_eras")

    assert d["objective_policy"] == "legacy_4d_v1"
    assert d["active_objective_policy"] == RATE_4D_OBJECTIVE_POLICY
    assert d["objective_policy_context"] == "historical_legacy_comparator"
    assert d["decision_grade"] is False
    assert d["objective_axes"][1]["label"] == "median request t/s (historical comparator)"


def test_dashboard_html_ships_dual_report_ui():
    html = DASHBOARD_HTML.read_text()
    # Policy-aware banner and descriptive comparison controls.
    assert 'id="pareto-dual-report-banner"' in html
    assert 'id="pareto-speed-axis-toggle"' in html
    assert "archive objective" in html
    assert "certified task-rate telemetry" in html
    assert 'id="pareto-divergence-badge"' in html
    assert 'id="pareto-task-rate-note"' in html
    assert "setParetoSpeedAxis" in html
    assert "W3 flip decision live" not in html
    assert "objective comparison" in html

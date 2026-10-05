"""AP-50 decision cockpit contract: offline fixtures only (no inference, no processes)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from scripts.autopilot import decision_cockpit as dc

Q_OLD, S_OLD = "E15-eval-q", "E15-autopilot-s"
Q_NEW, S_NEW = "E16-eval-q", "E16-autopilot-s"
OLD_BUCKET = f"{Q_OLD}|{S_OLD}"
NEW_BUCKET = f"{Q_NEW}|{S_NEW}"
OLD_TS = "2026-08-09T01:00:00+00:00"
NEW_TS = "2026-08-11T01:00:00+00:00"
NOW = 1789000000.0  # 2026-09-10

ERAS_YAML = f"""
eras:
  - id: {Q_OLD}
    from: "2026-08-08T00:00:00Z"
    scope: eval_quality
  - id: {S_OLD}
    from: "2026-08-08T00:00:00Z"
    scope: autopilot_speed
  - id: {Q_NEW}
    from: "2026-08-10T00:00:00Z"
    scope: eval_quality
  - id: {S_NEW}
    from: "2026-08-10T00:00:00Z"
    scope: autopilot_speed
"""


def _qres(n: int, n_correct: int, prefix: str = "q") -> list[dict]:
    return [{"qid": f"{prefix}{i}", "suite": "s", "correct": i < n_correct} for i in range(n)]


def _trial(tid: int, ts: str, **kw) -> dict:
    row = {
        "trial_id": tid,
        "timestamp": ts,
        "species": "numeric_swarm",
        "action_type": "numeric_trial",
        "tier": 1,
        "quality": 0.0,
        "speed": 10.0,
        "cost": 0.5,
        "reliability": 1.0,
        "pareto_status": "dominated",
        "config_snapshot": {"type": "numeric_trial", "surface": "escalation",
                            "params": {"escalation.max_retries": tid % 3}},
        "hypothesis": "Optimize escalation surface",
        "expected_mechanism": "escalation",
        "falsifier": "quality does not rise above the incumbent",
        "failure_analysis": "",
        "keep_revert_decision": "",
        "bug_corrupted_by": "",
        "outcome_status": "ok",
        "seq": {},
        "eval_details": {},
    }
    row.update(kw)
    return row


def _scored(tid: int, ts: str, n: int, correct: int, **kw) -> dict:
    ed = {"details": {"correct": correct, "n_scored": n, "total": n},
          "question_results": _qres(n, correct), "task_rate_qph": 100.0}
    ed.update(kw.pop("eval_details", {}))
    return _trial(tid, ts, quality=3.0 * correct / n, eval_details=ed, **kw)


def _write_jsonl(path: Path, rows: list[dict], *, torn_tail: bool = False) -> None:
    text = "\n".join(json.dumps(r) for r in rows) + "\n"
    if torn_tail:
        text += '{"trial_id": 9999, "timestamp": "2026'  # interrupted append, no newline
    path.write_text(text)


def _make_study_db(path: Path, studies: dict[str, list[tuple[str, float | None]]]) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE studies (study_id INTEGER PRIMARY KEY, study_name TEXT);
        CREATE TABLE study_directions (study_direction_id INTEGER PRIMARY KEY, direction TEXT,
                                       study_id INTEGER, objective INTEGER);
        CREATE TABLE trials (trial_id INTEGER PRIMARY KEY, number INTEGER, study_id INTEGER, state TEXT);
        CREATE TABLE trial_values (trial_value_id INTEGER PRIMARY KEY, trial_id INTEGER,
                                   objective INTEGER, value REAL, value_type TEXT);
        """
    )
    tid = 0
    for sid, (name, trials) in enumerate(studies.items(), start=1):
        conn.execute("INSERT INTO studies VALUES (?, ?)", (sid, name))
        conn.execute("INSERT INTO study_directions VALUES (NULL, 'MAXIMIZE', ?, 0)", (sid,))
        for number, (state, value) in enumerate(trials):
            tid += 1
            conn.execute("INSERT INTO trials VALUES (?, ?, ?, ?)", (tid, number, sid, state))
            if value is not None:
                conn.execute("INSERT INTO trial_values VALUES (NULL, ?, 0, ?, 'FINITE')", (tid, value))
    conn.commit()
    conn.close()


@pytest.fixture
def world(tmp_path: Path) -> dict:
    orch = tmp_path / "orchestration"
    orch.mkdir()
    (orch / "instrument_eras.yaml").write_text(ERAS_YAML)
    old_rows = [
        _trial(10, OLD_TS, outcome_status="skipped", deficiency_category="dispatch_skipped",
               failure_analysis="numeric_trial params failed to apply"),
        _scored(11, OLD_TS, 50, 25, keep_revert_decision="revert",
                failure_analysis="VIOLATIONS:\n  - Throughput floor: 5.8 t/s < 36.6 t/s (80% of baseline 45.8)\n"),
        _trial(12, OLD_TS, species="seeder", action_type="seed_batch",
               config_snapshot={"type": "seed_batch", "n_questions": 10},
               quality=1.8, eval_details={"details": {"correct": 6, "n_scored": 10}}),
    ]
    new_rows = [
        # base shard: current-era rows
        _scored(20, NEW_TS, 100, 55, keep_revert_decision="keep"),  # kept + promoted + live
        _scored(21, NEW_TS, 100, 52, keep_revert_decision="keep"),  # kept, liveness unknown
        _scored(22, NEW_TS, 100, 40, keep_revert_decision="revert",
                failure_analysis="VIOLATIONS:\n  - Quality regression: 1.200 vs baseline 1.500 (-20%)\n"),
        _scored(23, NEW_TS, 100, 50, keep_revert_decision="excluded",
                eval_details={"details": {"correct": 50, "n_scored": 100},
                              "learning_exclusion": {"reason": "mad_noise"}}),
        _scored(24, NEW_TS, 100, 60, keep_revert_decision="keep"),  # superseded -> invalid
        _trial(25, NEW_TS, species="structural_lab", action_type="structural_experiment",
               config_snapshot={"type": "structural_experiment", "flags": {"personas": True,
                                                                          "plan_review": False}},
               outcome_status="invalid", deficiency_category="invalid_action"),
        _scored(26, NEW_TS, 100, 70, species="seeder", action_type="seed_batch",
                config_snapshot={"type": "seed_batch", "n_questions": 100}),
    ]
    supersession = {"type": "supersession", "target_trial_ids": [24],
                    "fields": {"bug_corrupted_by": "exogenous_gpu_load",
                               "bug_corrupted_reason": "overlapped an external GPU load"},
                    "reason": "exogenous", "policy_version": "supersession-v1", "actor": "test"}
    promotion = {"type": "baseline_promotion", "source_trial_id": 20, "tier": 1,
                 "reason": "seq confirmed", "new_quality": 1.65}
    # Shards: base (batch 0), _1, and _3 with a GAP at _2 (JRN-7), plus noise files.
    _write_jsonl(orch / "autopilot_journal.jsonl", old_rows)
    _write_jsonl(orch / "autopilot_journal_1.jsonl", new_rows[:4])
    _write_jsonl(orch / "autopilot_journal_3.jsonl", new_rows[4:] + [supersession, promotion])
    (orch / "autopilot_journal_1.jsonl.corrupt-20260101T000000Z").write_text("garbage\n")
    (orch / "autopilot_journal.tsv").write_text("trial_id\n")

    incumbent_outcomes = {f"q{i}": i < 50 for i in range(100)}  # q=1.5, n=100
    state = {
        "paused": True,
        "in_flight_trial": None,
        "trial_counter": 27,
        "active_instrument_eras": {"eval_quality": Q_NEW, "autopilot_speed": S_NEW},
        "multitier_baseline_bundle": {
            "boundary": "2026-08-10T00:00:00Z", "status": "operator_ratified",
            "policy_version": "staged-multitier-v1",
            "tiers": {"1": {"quality": 1.5, "n_questions": 100, "reliability": 1.0,
                            "core_id": "core1", "outcomes": incumbent_outcomes}},
        },
        "critic_rejected_signatures": {
            "a": {"action": {"type": "prompt_mutation"}, "count": 2, "recorded_at": NEW_TS},
            "b": {"action": {"type": "prompt_mutation"}, "count": 5, "recorded_at": OLD_TS},
        },
    }
    (orch / "autopilot_state.json").write_text(json.dumps(state))
    ckpt = orch / "autopilot_checkpoints" / "run_x"
    ckpt.mkdir(parents=True)
    (ckpt / "checkpoint_meta.json").write_text(json.dumps(
        {"trial_id": 20, "is_production_best": True, "notes": "fixture"}))
    (orch / "autopilot_checkpoints" / "production_best").symlink_to(ckpt)
    _make_study_db(orch / "optuna_study.db", {
        f"autopilot_escalation_era_{S_NEW.replace('-', '_')}": [("COMPLETE", 1.9), ("FAIL", None)],
        f"autopilot_monitor_era_{S_NEW.replace('-', '_')}": [("COMPLETE", 1.7)],
        f"autopilot_escalation_era_{S_OLD.replace('-', '_')}": [("COMPLETE", 2.4)],
        "autopilot_escalation": [("COMPLETE", 2.9)],
    })
    return {"orch": orch}


def _build(world: dict, **kw) -> dict:
    orch = world["orch"]
    args = dict(
        journal_dir=orch, state_path=orch / "autopilot_state.json",
        eras_path=orch / "instrument_eras.yaml", study_db=orch / "optuna_study.db",
        checkpoints_dir=orch / "autopilot_checkpoints", now=NOW,
    )
    args.update(kw)
    return dc.build_decision_cockpit(**args)


def _stage(payload: dict, name: str) -> dict:
    return next(s for s in payload["funnel"]["stages"] if s["stage"] == name)


# --------------------------------------------------------------------------- #
def test_reads_every_shard_numerically_with_gap_and_ignores_sidecars(world):
    p = _build(world)
    j = p["inputs"]["journal"]
    assert [s["name"] for s in j["shards"]] == [
        "autopilot_journal.jsonl", "autopilot_journal_1.jsonl", "autopilot_journal_3.jsonl"]
    assert j["shard_count"] == 3
    assert j["trial_rows"] == 10
    assert j["event_rows"] == 2
    assert j["supersessions_applied"] == 1
    assert j["status"] == "ok"
    assert p["health"]["status"] == "ok"


def test_defaults_to_current_era_and_never_pools(world):
    p = _build(world)
    assert p["eras"]["current"]["bucket"] == NEW_BUCKET
    assert p["eras"]["current"]["source"] == "autopilot_state.active_instrument_eras"
    assert p["eras"]["selected"] == NEW_BUCKET
    assert {e["id"]: e["trials"] for e in p["eras"]["available"]} == {OLD_BUCKET: 3, NEW_BUCKET: 7}
    # seed_batch is evidence-only: 6 interventions, 1 seeding row in the new era.
    assert _stage(p, "proposed")["count"] == 6
    old = _build(world, era=OLD_BUCKET)
    assert _stage(old, "proposed")["count"] == 2
    assert "all" not in {e["id"] for e in p["eras"]["available"]}


def test_funnel_distinguishes_every_state_with_rejection_reasons(world):
    p = _build(world)
    counts = {s["stage"]: s["count"] for s in p["funnel"]["stages"]}
    assert counts == {"proposed": 6, "executed": 5, "valid": 3, "kept": 2, "promoted": 1,
                      "currently_live": 1}
    assert _stage(p, "currently_live")["unknown"] == 1  # trial 21: kept, not in production_best
    reasons = {s["stage"]: {r["code"]: r["count"] for r in s.get("reasons", [])}
               for s in p["funnel"]["stages"]}
    assert reasons["executed"] == {"invalid_action": 1}
    assert reasons["valid"] == {"exogenous_gpu_load": 1, "learning_excluded": 1}
    assert reasons["kept"] == {"quality_regression": 1}
    assert reasons["promoted"] == {"no_promotion_recorded": 1}
    assert p["funnel"]["anomalies"] == {"kept_on_invalid_evidence": 1}
    assert p["funnel"]["evidence_only_actions"]["by_type"] == {"seed_batch": 1}
    # critic fences are scoped to the era window and kept OUT of "proposed".
    assert p["funnel"]["critic_rejections_before_journal"]["count"] == 2


def test_objective_deltas_carry_n_se_paired_and_replication(world):
    p = _build(world)
    od = p["objective_deltas"]
    assert od["incumbent"]["available"] is True
    assert od["incumbent"]["era_bucket"] == NEW_BUCKET
    assert "_outcomes" not in od["incumbent"]["tiers"]["1"]
    by_tid = {c["trial_id"]: c for c in od["candidates"]}
    c20 = by_tid[20]
    vs = c20["vs_incumbent"]
    assert vs["comparable"] is True
    assert vs["delta"] == pytest.approx(0.15)
    assert vs["incumbent_n"] == 100 and c20["candidate"]["n_scored"] == 100
    assert c20["candidate"]["se"] == pytest.approx(3.0 * (0.55 * 0.45 / 100) ** 0.5)
    assert vs["delta_se"] > c20["candidate"]["se"]
    assert vs["paired"] == {"shared_qids": 100, "candidate_only_correct": 5, "incumbent_only_correct": 0}
    assert c20["replication"]["valid_runs_same_signature"] >= 1
    assert od["best_comparable_by_tier"]["1"]["trial_id"] == 20
    # the prose baseline is only taken from the QUALITY sentence, never the t/s one.
    assert by_tid[22]["vs_pinned_baseline"]["source"] == "legacy_quality_regression_prose"
    assert by_tid[22]["vs_pinned_baseline"]["baseline_quality"] == 1.5


def test_op20_seeding_quality_is_fenced_not_merged(world):
    p = _build(world)
    od = p["objective_deltas"]
    assert all(c["producer_class"] == "eval_tower" for c in od["candidates"])
    assert od["seeding_producer"]["valid_rows"] == 1
    assert "OP-20" in od["seeding_producer"]["note"]
    assert any("OP-20" in c for c in p["caveats"])


def test_prior_era_deltas_are_not_compared_to_current_incumbent(world):
    p = _build(world, era=OLD_BUCKET)
    cands = p["objective_deltas"]["candidates"]
    assert [c["trial_id"] for c in cands] == [11]
    assert cands[0]["vs_incumbent"]["comparable"] is False
    assert cands[0]["vs_incumbent"]["reason"].startswith("era_mismatch")
    assert cands[0]["vs_pinned_baseline"]["source"] == "absent"  # t/s "baseline 45.8" ignored


def test_current_era_without_trials_is_empty_known_not_unknown(world):
    orch = world["orch"]
    state = json.loads((orch / "autopilot_state.json").read_text())
    (orch / "instrument_eras.yaml").write_text(
        ERAS_YAML + '  - id: E17-q\n    from: "2026-09-01T00:00:00Z"\n    scope: eval_quality\n'
                    '  - id: E17-s\n    from: "2026-09-01T00:00:00Z"\n    scope: autopilot_speed\n')
    state["active_instrument_eras"] = {"eval_quality": "E17-q", "autopilot_speed": "E17-s"}
    (orch / "autopilot_state.json").write_text(json.dumps(state))
    p = _build(world)
    assert p["eras"]["selected"] == "E17-q|E17-s"
    assert p["funnel"]["known"] is True
    assert _stage(p, "proposed")["count"] == 0
    assert p["objective_deltas"]["empty_reason"]
    assert p["current"]["last_in_selected_era"] is None
    assert p["current"]["last_journaled"]["era_label"] == "E16"
    assert p["current"]["status"] == "idle_declared_paused"


def test_lever_scoreboard_is_journal_plus_era_matched_study(world):
    p = _build(world)
    board = p["lever_scoreboard"]
    assert board["digest_used"] is False
    levers = {lev["lever"]: lev for lev in board["levers"]}
    esc = levers["numeric:escalation"]
    assert esc["kept"] == 2 and esc["promoted"] == 1 and esc["currently_live"] == 1
    assert esc["study"]["names"] == [f"autopilot_escalation_era_{S_NEW.replace('-', '_')}"]
    assert esc["study"]["complete"] == 1 and esc["study"]["fail"] == 1
    assert esc["study"]["best_quality"] == 1.9  # never the other era's 2.4 or the unattributed 2.9
    assert levers["numeric:monitor"]["proposed"] == 0 and levers["numeric:monitor"]["study"]["complete"] == 1
    assert levers["flag:personas"]["multi_factor_trials"] == 1


def test_provenance_graph_is_left_to_right_with_explicit_edges(world):
    p = _build(world)
    g = p["provenance"]
    assert g["columns"] == ["hypothesis", "experiment", "evidence", "verdict", "runtime_state"]
    ids = {n["id"] for n in g["nodes"]}
    order = {c: i for i, c in enumerate(g["columns"])}
    col = {n["id"]: n["column"] for n in g["nodes"]}
    for e in g["edges"]:
        assert e["relation"] in g["edge_semantics"]
        assert e["from"] in ids and e["to"] in ids
        assert order[col[e["from"]]] < order[col[e["to"]]]
    assert "rt:live" in ids and "rt:live_unknown" in ids
    kept_only = _build(world, status_filter="kept")["provenance"]
    exp = [n["trial_id"] for n in kept_only["nodes"] if n["column"] == "experiment"]
    assert sorted(exp) == [20, 21]
    assert kept_only["filters"]["status_applied"] == "kept"


def test_missing_journal_fails_closed_as_unknown(world, tmp_path):
    p = _build(world, journal_dir=tmp_path / "nowhere")
    assert p["inputs"]["journal"]["status"] == "absent"
    assert p["funnel"]["known"] is False and "stages" not in p["funnel"]
    assert p["health"]["status"] == "absent"


def test_unreadable_state_and_eras_degrade_never_green(world):
    orch = world["orch"]
    (orch / "autopilot_state.json").write_text("{not json")
    p = _build(world)
    assert p["inputs"]["state"]["status"] == "unreadable"
    assert p["current"]["status"] == "unknown"
    assert p["objective_deltas"]["incumbent"]["available"] is False
    assert p["health"]["status"] == "degraded"
    (orch / "instrument_eras.yaml").write_text(": : :\n\t- bad")
    q = _build(world)
    assert q["eras"]["selected"] is None
    assert q["funnel"]["known"] is False
    assert q["health"]["status"] == "degraded"


def test_bad_line_marks_journal_partial_and_degrades(world):
    orch = world["orch"]
    with open(orch / "autopilot_journal_1.jsonl", "a") as fh:
        fh.write("{broken json\n")
    p = _build(world)
    assert p["inputs"]["journal"]["status"] == "partial"
    assert p["inputs"]["journal"]["bad_lines"] == 1
    assert p["health"]["status"] == "degraded"


def test_unreadable_study_is_unknown_not_zero(world):
    orch = world["orch"]
    (orch / "optuna_study.db").write_bytes(b"this is not sqlite" * 100)
    p = _build(world)
    assert p["inputs"]["study"]["status"] == "unreadable"
    esc = next(lev for lev in p["lever_scoreboard"]["levers"] if lev["lever"] == "numeric:escalation")
    assert esc["study"] == {"status": "unreadable"}
    assert p["health"]["status"] == "degraded"


def test_build_is_read_only_even_with_a_torn_tail(world):
    orch = world["orch"]
    _write_jsonl(orch / "autopilot_journal_4.jsonl", [_scored(30, NEW_TS, 10, 5)], torn_tail=True)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in orch.iterdir() if p.is_file()}
    payload = _build(world)
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in orch.iterdir() if p.is_file()}
    assert before == after  # no truncation, no .corrupt sidecar, no -wal/-shm
    assert payload["inputs"]["journal"]["status"] == "partial"


def test_api_route_stamps_freshness_and_health_probe(world, monkeypatch):
    from src.api.routes import dashboard as d

    orch = world["orch"]
    monkeypatch.setattr(d, "_AUTOPILOT_STATE_PATH", orch / "autopilot_state.json")
    monkeypatch.setattr(d, "_AUTOPILOT_JOURNAL_PATH", orch / "autopilot_journal.jsonl")
    d._DECISION_COCKPIT_CACHE.clear()
    resp = asyncio.run(d.decision_cockpit())
    body = json.loads(resp.body.decode())
    assert body["schema"] == dc.SCHEMA
    assert body["_freshness"]["staleness_class"] in {"fresh", "aging", "stale", "dead"}
    ok = asyncio.run(d.decision_cockpit_health())
    assert ok.status_code == 200
    d._DECISION_COCKPIT_CACHE.clear()
    monkeypatch.setattr(d, "_AUTOPILOT_JOURNAL_PATH", orch / "gone" / "autopilot_journal.jsonl")
    bad = asyncio.run(d.decision_cockpit_health())
    assert bad.status_code == 503
    assert json.loads(bad.body.decode())["status"] == "absent"
    d._DECISION_COCKPIT_CACHE.clear()

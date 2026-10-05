"""Unit tests for the read-only operator optimization brief synthesis."""

from __future__ import annotations

import json
import sqlite3

from scripts.autopilot import optimization_brief as ob

_DIGEST = """\
## 2026-06-28 08:00:00 UTC

### NumericSwarm surfaces

#### `escalation` — 13 completed trials
  - best quality (obj 0): **2.16**
  - cluster-selected best: `escalation.max_retries=2`, `escalation.max_escalations=3`
  - fANOVA importance (quality): `escalation.max_retries`=0.756, `escalation.max_escalations`=0.244

#### `think_harder` — 14 completed trials
  - best quality (obj 0): **2.10**
  - cluster-selected best: `think_harder.token_budget_min=2573`, `think_harder.cot_roi_threshold=0.4151`
  - fANOVA importance (quality): `think_harder.token_budget_min`=0.466, `think_harder.cot_roi_threshold`=0.241

#### `chat_pipeline` — 0 completed trials
  - no completed trials yet
"""


def test_levers_ranked_by_importance_with_recommended_value():
    levers = ob.levers_from_digest(_DIGEST)
    # chat_pipeline has no importance data -> excluded; two surfaces remain.
    assert [lev["surface"] for lev in levers] == ["escalation", "think_harder"]
    top = levers[0]
    assert top["lever"] == "escalation.max_retries"
    assert top["importance"] == 0.756
    assert top["recommended"] == "2"
    assert top["best_quality"] == 2.16
    assert top["n_trials"] == 13


def test_authority_banner_off_is_observation_only():
    banner = ob.authority_banner({}, {"gaming_alarm": True}, seq_verdict_live=False)
    assert banner["decision_grade_possible"] is False
    assert "OBSERVATION" in banner["trust_note"]


def test_authority_banner_on_requires_consent_flag_and_seq(tmp_path, monkeypatch):
    grant = tmp_path / "c.json"
    grant.write_text(json.dumps({"baseline_ledger": "allow"}))
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(grant))
    state = {"baseline_ledger_authority_enabled": True}
    # baseline (flag + consent) + sequential (live env) + no alarm => decision-grade
    on = ob.authority_banner(state, {"gaming_alarm": False}, seq_verdict_live=True)
    assert on["decision_grade_possible"] is True
    # sequential off => not decision-grade
    seq_off = ob.authority_banner(state, {"gaming_alarm": False}, seq_verdict_live=False)
    assert seq_off["decision_grade_possible"] is False
    # consent revoked => baseline off => not decision-grade even with seq + no alarm
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(tmp_path / "gone.json"))
    no_consent = ob.authority_banner(state, {"gaming_alarm": False}, seq_verdict_live=True)
    assert no_consent["decision_grade_possible"] is False


def test_ruled_out_and_exploring_split_by_entry_type(tmp_path):
    db = tmp_path / "strategies.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE strategies (id TEXT PRIMARY KEY, description TEXT, insight TEXT, "
        "source_trial_id INTEGER, species TEXT, created_at TEXT, metadata_json TEXT, "
        "entry_type TEXT)"
    )
    conn.executemany(
        "INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                "opseed-guardrail-ep",
                "EP flag",
                "Do NOT toggle expert_parallelism",
                None,
                "structural_lab",
                "2026-06-28T00:00:00Z",
                json.dumps({"source_handoff": "h.md", "bind_status": "future"}),
                "convention",
            ),
            (
                "opseed-green-brevity",
                "TrimR brevity",
                "Add conciseness instruction to worker prompts",
                None,
                "prompt_forge",
                "2026-06-28T00:00:01Z",
                json.dumps({}),
                "pattern",
            ),
        ],
    )
    conn.commit()
    conn.close()

    ruled_out, exploring = ob.ruled_out_and_exploring(db)
    assert len(ruled_out) == 1 and ruled_out[0]["source_handoff"] == "h.md"
    assert ruled_out[0]["bind_status"] == "future"
    assert len(exploring) == 1 and "conciseness" in exploring[0]["statement"]


def test_best_config_picks_highest_quality_current_era_trusted():
    rows = [
        {"trial_id": 1, "tier": 1, "quality": 2.0, "speed": 50, "timestamp": 100.0,
         "config_snapshot": {"a": 1}},
        {"trial_id": 2, "tier": 1, "quality": 2.2, "speed": 40, "timestamp": 200.0,
         "config_snapshot": {"a": 2}, "keep_revert_decision": "keep"},
        # corrupted -> excluded even though higher quality
        {"trial_id": 3, "tier": 1, "quality": 9.9, "speed": 99, "timestamp": 300.0,
         "bug_corrupted_by": "rollback"},
        # pre-era -> excluded by exclude_before_ts
        {"trial_id": 4, "tier": 1, "quality": 5.0, "speed": 99, "timestamp": 50.0},
    ]
    best = ob.best_config(rows, exclude_before_ts=99.0)
    assert best["available"] is True
    assert best["trial_id"] == 2
    assert best["status"] == "incumbent"
    assert best["objective"]["quality"] == 2.2


def test_best_config_excludes_reverted_and_learning_excluded_trials():
    """A verdict-failed (reverted) or AP-24 learning-excluded trial keeps
    outcome_status="ok", so the keep/revert record is the only honest gate —
    regression test for trial 1061 (2026-07-02) being crowned after rollback."""
    rows = [
        # verdict failed, config rolled back -> ineligible despite top quality
        {"trial_id": 1061, "tier": 1, "quality": 2.22, "speed": 35.5,
         "timestamp": 300.0, "outcome_status": "ok",
         "keep_revert_decision": "revert", "pareto_status": "dominated"},
        # learning-excluded (mad_noise) -> ineligible
        {"trial_id": 1056, "tier": 1, "quality": 2.22, "speed": 29.0,
         "timestamp": 250.0, "keep_revert_decision": "excluded"},
        # kept frontier config -> the honest best
        {"trial_id": 1005, "tier": 1, "quality": 2.16, "speed": 47.5,
         "timestamp": 200.0, "keep_revert_decision": "keep",
         "pareto_status": "frontier", "config_snapshot": {"a": 1}},
        # legacy row without the field stays eligible
        {"trial_id": 900, "tier": 1, "quality": 2.0, "speed": 60,
         "timestamp": 150.0},
    ]
    best = ob.best_config(rows, exclude_before_ts=99.0)
    assert best["trial_id"] == 1005
    assert best["keep_revert_decision"] == "keep"
    assert best["pareto_status"] == "frontier"
    assert best["status"] == "incumbent"


def test_best_config_promoted_only_from_seq_promotion_record():
    """"promoted" must come from the trial's own finalized sequential promotion
    record, never from the global authority banner."""
    kept = {"trial_id": 7, "tier": 1, "quality": 2.1, "speed": 60,
            "timestamp": 200.0, "keep_revert_decision": "keep"}
    # no seq record -> incumbent
    best = ob.best_config([dict(kept)], exclude_before_ts=None)
    assert best["promoted"] is False and best["status"] == "incumbent"
    # accumulating (not finalized) seq verdict -> still incumbent
    best = ob.best_config(
        [dict(kept, seq={"baseline_promotion_finalized": False})],
        exclude_before_ts=None,
    )
    assert best["promoted"] is False and best["status"] == "incumbent"
    # finalized promotion record -> promoted
    best = ob.best_config(
        [dict(kept, seq={"baseline_promotion_finalized": True})],
        exclude_before_ts=None,
    )
    assert best["promoted"] is True and best["status"] == "promoted"


def test_ruled_out_experiments_splits_fenced_and_invalid_surfaces():
    state = {
        "critic_rejected_signatures": {
            "sig-1": {
                "action": {
                    "type": "numeric_trial",
                    "surface": "repl_budget",
                    "flags": {"batch_size": 32, "timeout_ms": 500},
                },
                "reason": "critic rejected: empty params are non-replayable; use concrete params",
                "count": 3,
                "trial_id": 10,
            }
        },
    }
    rows = [
        {"trial_id": 1, "action_type": "seed_batch", "outcome_status": "skipped"},
        {"trial_id": 2, "action_type": "numeric_trial", "outcome_status": "invalid"},
        {
            "trial_id": 10,
            "action_type": "numeric_trial",
            "outcome_status": "ok",
            "bug_corrupted_by": "exogenous_operator_reload",
        },
    ]

    ruled = ob.ruled_out_experiments(state, limit=6, journal_rows=rows)

    assert ruled["fenced"] == []
    assert ruled["invalid_by_surface"] == [
        {"label": "numeric sweep", "kind": "numeric_trial", "count": 1},
        {"label": "eval seeding", "kind": "seed_batch", "count": 1},
    ]
    assert ruled["corrupted_by_surface"] == [
        {"label": "numeric sweep", "kind": "numeric_trial", "count": 1},
    ]
    assert ruled["stale_fenced_by_surface"] == [
        {"label": "numeric sweep · batch_size=32, timeout_ms=500", "kind": "numeric_trial", "count": 3},
    ]


def test_build_brief_end_to_end(tmp_path):
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "trial_counter": 1046,
                "pareto_exclude_before_ts": 99.0,
                "critic_rejected_signatures": {
                    "sig-1": {
                        "action": {
                            "type": "numeric_trial",
                            "surface": "repl_budget",
                            "flags": {"batch_size": 32, "timeout_ms": 500},
                        },
                        "reason": "critic rejected: empty params are non-replayable; use concrete params",
                        "count": 3,
                        "trial_id": 10,
                    }
                },
            }
        )
    )
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        json.dumps({"trial_id": 2, "tier": 1, "quality": 2.2, "speed": 40,
                    "timestamp": 200.0, "config_snapshot": {"a": 2},
                    "action_type": "seed_batch", "outcome_status": "ok"}) + "\n"
        + json.dumps({"trial_id": 4, "tier": 0, "quality": 0.0, "speed": 0,
                    "timestamp": 205.0, "config_snapshot": {"type": "numeric_trial"},
                    "action_type": "numeric_trial", "outcome_status": "invalid"}) + "\n"
        + json.dumps({"trial_id": 10, "tier": 1, "quality": 1.0, "speed": 0,
                    "timestamp": 210.0, "config_snapshot": {"a": 3},
                    "action_type": "numeric_trial", "outcome_status": "ok",
                    "bug_corrupted_by": "autopilot_killed_mid_trial"}) + "\n"
        + json.dumps({"trial_id": 3, "tier": 1, "quality": 1.0, "speed": 0,
                    "timestamp": 215.0, "config_snapshot": {"a": 3},
                    "action_type": "seed_batch", "outcome_status": "skipped",
                    "deficiency_category": "dispatch_skipped",
                    "failure_analysis": "dispatcher no-op",
                    "pareto_status": "skipped",
                    }) + "\n"
    )
    db = tmp_path / "strategies.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE strategies (id TEXT PRIMARY KEY, description TEXT, insight TEXT, "
        "source_trial_id INTEGER, species TEXT, created_at TEXT, metadata_json TEXT, "
        "entry_type TEXT)"
    )
    conn.execute(
        "INSERT INTO strategies VALUES "
        "('c','d','Do NOT enable X',NULL,'structural_lab','2026-06-28T00:00:00Z','{}','convention')"
    )
    conn.commit()
    conn.close()

    brief = ob.build_optimization_brief(
        state_path=state,
        journal_paths=[journal],
        strategy_db=db,
        digest_text=_DIGEST,
    )
    assert brief["read_only"] is True
    assert brief["checkpoint"]["trial_counter"] == 1046
    assert brief["authority"]["decision_grade_possible"] is False
    assert brief["levers"][0]["lever"] == "escalation.max_retries"
    assert brief["levers"][0]["decision_grade"] is False
    assert brief["best_config"]["trial_id"] == 2
    assert len(brief["ruled_out"]) == 1
    assert brief["ruled_out_experiments"]["fenced"] == []
    assert brief["ruled_out_experiments"]["invalid_by_surface"] == [
        {"label": "numeric sweep", "kind": "numeric_trial", "count": 1},
        {"label": "eval seeding", "kind": "seed_batch", "count": 1},
    ]
    assert brief["ruled_out_experiments"]["corrupted_by_surface"][0]["kind"] == "numeric_trial"
    assert brief["ruled_out_experiments"]["stale_fenced_by_surface"] == [
        {"label": "numeric sweep · batch_size=32, timeout_ms=500", "kind": "numeric_trial", "count": 3},
    ]
    # narrative is templated, not free-written: it must mention the top lever.
    assert "escalation.max_retries" in brief["narrative"]
    assert "observations" in brief["narrative"].lower()


# --------------------------------------------------------------------------- #
# E1 (2026-07-26): the authority banner must consult the LIVE fail-closed era
# holds — trial 1446 showed "kept configs are decision-grade" while the safety
# gate was skipping archive.update on quality_rebaseline_required.
# --------------------------------------------------------------------------- #
def _consent(tmp_path, monkeypatch):
    grant = tmp_path / "consent.json"
    grant.write_text(json.dumps({"baseline_ledger": "allow"}))
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(grant))


def _hold_state() -> dict:
    return {
        "baseline_ledger_authority_enabled": True,
        "active_instrument_eras": {
            "eval_quality": "E8",
            "autopilot_speed": "E8-autopilot-speed",
        },
        "baseline_state": {"eval_quality_era": "E7-eval-instrument"},
        "frontier_rerun_required": {
            "required": True,
            "completed_numeric_trials": 7,
            "min_numeric_trials": 16,
            "opened_at": "2026-07-25T18:38:43Z",
        },
    }


def test_authority_banner_era_holds_override_decision_grade(tmp_path, monkeypatch):
    _consent(tmp_path, monkeypatch)
    banner = ob.authority_banner(_hold_state(), {"gaming_alarm": False}, seq_verdict_live=True)
    # The authority MECHANISM is fully on…
    assert banner["authority_mechanism_enabled"] is True
    # …but the fail-closed holds veto decision-grade.
    assert banner["decision_grade_possible"] is False
    holds = banner["holds"]
    assert holds["quality_rebaseline_required"] is True
    assert holds["quality_authority"] == "HELD pending E8 baseline (fail-closed)"
    assert holds["frontier_rerun_required"] is True
    assert holds["speed_authority"] == "pending E8 numeric rerun (7/16)"
    # The banner text carries both holds and NEVER the decision-grade claim.
    assert "HELD pending E8 baseline (fail-closed)" in banner["trust_note"]
    assert "pending E8 numeric rerun (7/16)" in banner["trust_note"]
    assert "kept configs are decision-grade" not in banner["trust_note"]


def test_authority_banner_quality_hold_alone_blocks(tmp_path, monkeypatch):
    _consent(tmp_path, monkeypatch)
    state = _hold_state()
    del state["frontier_rerun_required"]
    banner = ob.authority_banner(state, {"gaming_alarm": False}, seq_verdict_live=True)
    assert banner["decision_grade_possible"] is False
    assert banner["holds"]["quality_rebaseline_required"] is True
    assert banner["holds"]["frontier_rerun_required"] is False
    assert banner["holds"]["speed_authority"].startswith("OK")
    assert "kept configs are decision-grade" not in banner["trust_note"]


def test_authority_banner_holds_clear_restores_decision_grade(tmp_path, monkeypatch):
    _consent(tmp_path, monkeypatch)
    state = {
        "baseline_ledger_authority_enabled": True,
        "active_instrument_eras": {
            "eval_quality": "E8",
            "autopilot_speed": "E8-autopilot-speed",
        },
        # Baseline reseeded under the active era + no open rerun marker.
        "baseline_state": {"eval_quality_era": "E8"},
    }
    banner = ob.authority_banner(state, {"gaming_alarm": False}, seq_verdict_live=True)
    assert banner["holds"]["any_hold_active"] is False
    assert banner["holds"]["quality_authority"].startswith("OK")
    assert banner["decision_grade_possible"] is True
    assert "kept configs are decision-grade" in banner["trust_note"]


def test_narrative_tail_reflects_active_holds(tmp_path, monkeypatch):
    _consent(tmp_path, monkeypatch)
    banner = ob.authority_banner(_hold_state(), {"gaming_alarm": False}, seq_verdict_live=True)
    narrative = ob._narrative(
        trial_counter=1446,
        levers=[],
        best={"available": False},
        ruled_out=[],
        exploring=[],
        ruled_out_exp={},
        banner=banner,
    )
    assert "kept configs are decision-grade" not in narrative
    assert "fail-closed era holds are active" in narrative


# --------------------------------------------------------------------------- #
# E2/E3 (2026-07-26): fence provenance + pre-era tag + GEPA no-op caveat.
# --------------------------------------------------------------------------- #
def test_fence_rows_carry_pre_epoch_era_tag():
    state = {
        "pareto_epoch_ts": 1785004723.0,  # E8 boundary
        "active_instrument_eras": {"autopilot_speed": "E8-autopilot-speed"},
        "critic_rejected_signatures": {
            "old": {
                "action": {"type": "structural_experiment", "flags": {"graph_router": True}},
                "reason": "critic rejected: nope",
                "count": 13,
                "trial_id": 700,
                "recorded_at": "2026-07-01T00:00:00+00:00",  # pre-E8
            },
            "new": {
                "action": {"type": "numeric_trial", "surface": "chat_long_context"},
                "reason": "critic rejected: nope",
                "count": 1,
                "trial_id": 1500,
                "recorded_at": "2026-07-25T23:00:00+00:00",  # post-E8
            },
        },
    }
    ruled = ob.ruled_out_experiments(state, journal_rows=[])
    by_kind = {f["kind"]: f for f in ruled["fenced"]}
    old = by_kind["structural_experiment"]
    assert old["pre_epoch"] is True
    assert old["era_tag"] == "pre-E8"
    assert old["minted_trial"] == 700
    assert old["minted_at"] == "2026-07-01T00:00:00+00:00"
    assert old["minted_ts"] is not None and old["minted_ts"] < 1785004723.0
    new = by_kind["numeric_trial"]
    assert new["pre_epoch"] is False
    assert new["era_tag"] is None
    # Fences are labeled, never dropped.
    assert len(ruled["fenced"]) == 2


def test_gepa_fence_and_churn_carry_noop_provenance_caveat():
    state = {
        "pareto_epoch_ts": 1785004723.0,
        "active_instrument_eras": {"autopilot_speed": "E8-autopilot-speed"},
        "critic_rejected_signatures": {
            "g": {
                "action": {"type": "gepa_optimize", "file": "frontdoor.md"},
                "reason": "critic rejected: not selectable",
                "count": 4,
                "trial_id": 800,
                "recorded_at": "2026-06-20T00:00:00+00:00",
            },
            "n": {
                "action": {"type": "numeric_trial", "surface": "s"},
                "reason": "critic rejected: nope",
                "count": 1,
                "trial_id": 801,
                "recorded_at": "2026-06-21T00:00:00+00:00",
            },
        },
    }
    rows = [
        {"trial_id": 5, "action_type": "gepa_optimize", "outcome_status": "invalid"},
        {"trial_id": 6, "action_type": "seed_batch", "outcome_status": "invalid"},
    ]
    ruled = ob.ruled_out_experiments(state, journal_rows=rows)
    by_kind = {f["kind"]: f for f in ruled["fenced"]}
    assert by_kind["gepa_optimize"]["provenance_caveat"] == ob.GEPA_NOOP_CAVEAT
    assert "provenance_caveat" not in by_kind["numeric_trial"]
    churn = {c["kind"]: c for c in ruled["invalid_by_surface"]}
    assert churn["gepa_optimize"]["provenance_caveat"] == ob.GEPA_NOOP_CAVEAT
    assert "provenance_caveat" not in churn["seed_batch"]


def test_brief_payload_carries_exploring_note_and_gepa_windows(tmp_path):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"trial_counter": 1}))
    brief = ob.build_optimization_brief(
        state_path=state,
        journal_paths=[tmp_path / "missing.jsonl"],
        strategy_db=tmp_path / "missing.db",
        digest_text="",
    )
    # E4: constitutional note — content untouched, lineage labeled.
    assert brief["exploring_note"] == (
        "hypotheses may derive from prior-era evidence (valid as priors)"
    )
    assert brief["gepa_provenance_windows"] == [
        {
            "from_ts": 1780531200.0,
            "until_ts": 1784978833.0,
            "label": "reflective-mutation no-op — optimizer provenance broken",
        }
    ]

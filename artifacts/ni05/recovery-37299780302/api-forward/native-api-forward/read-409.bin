"""Unit tests for src/trace/harness_schema.py — the shared intake-607 event family."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.trace import (
    SCHEMA_VERSION,
    ensure_schema,
    ensure_harness_schema,
    GovernanceLevel,
    WorkingStateScope,
    HarnessMetrics,
    OracleAdequacy,
    BehaviorSignature,
    ApprovalRecord,
    FailureCase,
    WorkingState,
    insert_harness_metrics,
    insert_oracle_adequacy,
    insert_behavior_signature,
    insert_approval_record,
    insert_failure_case,
    set_working_state,
    find_failure_cases,
    get_working_state,
    latest_behavior_signature,
    table_counts,
)
from src.trace.store import ensure_schema as store_ensure_schema


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "events.sqlite"


# ─── schema creation ────────────────────────────────────────────────────────────

HARNESS_TABLES = {
    "harness_metrics",
    "oracle_adequacy",
    "behavior_signature",
    "approval_record",
    "failure_case",
    "working_state",
}


def test_ensure_schema_creates_harness_tables(db_path: Path) -> None:
    """ensure_schema() alone yields the complete store (event + harness families)."""
    conn = store_ensure_schema(db_path)
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert "event" in tables  # original
    assert HARNESS_TABLES <= tables  # all six new families present


def test_ensure_harness_schema_idempotent(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    ensure_harness_schema(conn)  # second application must not raise
    ensure_harness_schema(conn)
    assert table_counts(conn) == {t: 0 for t in HARNESS_TABLES}
    conn.close()


# ─── round-trips per family ──────────────────────────────────────────────────────


def test_harness_metrics_roundtrip(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    rid = insert_harness_metrics(
        conn,
        HarnessMetrics(
            suite="repl",
            trial_id=7,
            execution_fidelity=0.9,
            recovery_rate=0.5,
            evidence_event_ids=[11, 12],
            confidence=0.8,
        ),
    )
    row = conn.execute("SELECT * FROM harness_metrics WHERE id=?", (rid,)).fetchone()
    cols = [d[0] for d in conn.execute("SELECT * FROM harness_metrics LIMIT 0").description]
    rec = dict(zip(cols, row))
    assert rec["trial_id"] == 7
    assert rec["execution_fidelity"] == 0.9
    assert json.loads(rec["evidence_event_ids"]) == [11, 12]
    assert rec["schema_version"] == SCHEMA_VERSION
    assert rec["created_ts_utc"]  # auto-populated
    conn.close()


def test_oracle_adequacy_bool_coercion(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    rid = insert_oracle_adequacy(
        conn,
        OracleAdequacy(
            suite="math500",
            oracle_type="exact_match",
            requires_external_answer=False,
            deterministic=True,
            known_blind_spots=["web-search leakage"],
        ),
    )
    row = conn.execute(
        "SELECT requires_external_answer, deterministic, known_blind_spots "
        "FROM oracle_adequacy WHERE id=?",
        (rid,),
    ).fetchone()
    assert row[0] == 0 and row[1] == 1
    assert json.loads(row[2]) == ["web-search leakage"]
    conn.close()


def test_behavior_signature_links_metrics(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    hm_event_id = 41
    bs_event_id = 42
    hm_id = insert_harness_metrics(
        conn, HarnessMetrics(event_id=hm_event_id, suite="repl", trial_id=1)
    )
    bs_id = insert_behavior_signature(
        conn,
        BehaviorSignature(
            archive_member_id="cfg-A",
            trial_id=1,
            event_id=bs_event_id,
            harness_metrics_id=hm_id,
            signature_hash="abc123",
            sentinel_outcomes={"q1": "pass", "q2": "fail"},
        ),
    )
    latest = latest_behavior_signature(conn, "cfg-A")
    assert latest["id"] == bs_id
    assert latest["event_id"] == bs_event_id
    assert latest["harness_metrics_id"] == hm_id
    assert latest["signature_confidence"] == "full"
    assert json.loads(latest["sentinel_outcomes"]) == {"q1": "pass", "q2": "fail"}
    conn.close()


def test_behavior_signature_schema_migrates_event_id(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE behavior_signature (
          id INTEGER PRIMARY KEY,
          archive_member_id TEXT,
          trial_id INTEGER,
          sentinel_outcomes TEXT,
          answer_hash TEXT,
          route_path_hash TEXT,
          tool_sequence_hash TEXT,
          escalation_path_hash TEXT,
          latency_bucket TEXT,
          token_bucket TEXT,
          harness_metrics_id INTEGER,
          oracle_adequacy_version TEXT,
          signature_hash TEXT,
          signature_confidence TEXT NOT NULL DEFAULT 'full',
          schema_version INTEGER NOT NULL,
          created_ts_utc TEXT NOT NULL
        );
        """
    )

    ensure_harness_schema(conn)

    columns = {row[1] for row in conn.execute("PRAGMA table_info(behavior_signature)")}
    assert "event_id" in columns
    rid = insert_behavior_signature(
        conn,
        BehaviorSignature(
            archive_member_id="cfg-old",
            trial_id=9,
            event_id=123,
            signature_hash="abc123",
        ),
    )
    assert rid > 0
    latest = latest_behavior_signature(conn, "cfg-old")
    assert latest["event_id"] == 123
    assert latest["schema_version"] == SCHEMA_VERSION
    conn.close()


def test_approval_record_roundtrip(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    rid = insert_approval_record(
        conn,
        ApprovalRecord(
            request_id="req-9",
            task_signature="sig-x",
            selected_role="architect",
            uncertainty_score=0.7,
            uncertainty_components={"entropy": 0.7, "margin": 0.1},
            trigger_reason="high_uncertainty",
            approval_boundary="plan-review-only",
        ),
    )
    row = conn.execute(
        "SELECT uncertainty_components, approval_boundary FROM approval_record WHERE id=?", (rid,)
    ).fetchone()
    assert json.loads(row[0])["entropy"] == 0.7
    assert row[1] == "plan-review-only"
    conn.close()


# ─── EXM-1: failure-case avoidance retrieval ─────────────────────────────────────


def test_find_failure_cases_orders_by_governance_then_recency(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="T",
            error_class="timeout",
            governance_level=GovernanceLevel.RAW,
            avoidance_advice="raw note",
        ),
    )
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="T",
            error_class="timeout",
            governance_level=GovernanceLevel.APPROVED_BASELINE,
            avoidance_advice="trusted note",
        ),
    )
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="OTHER",
            error_class="x",
            avoidance_advice="unrelated",
        ),
    )
    hits = find_failure_cases(conn, "T")
    assert len(hits) == 2  # only task_signature='T'
    assert hits[0]["governance_level"] == GovernanceLevel.APPROVED_BASELINE  # trusted first
    assert hits[0]["avoidance_advice"] == "trusted note"
    conn.close()


def test_find_failure_cases_excludes_deprecated_by_default(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="T",
            governance_level=GovernanceLevel.DEPRECATED,
            avoidance_advice="old",
        ),
    )
    assert find_failure_cases(conn, "T") == []
    assert len(find_failure_cases(conn, "T", exclude_deprecated=False)) == 1
    conn.close()


def test_find_failure_cases_uses_fts_for_similar_signatures(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="autopilot trial timeout while running eval tower",
            error_class="timeout",
            root_cause_label="stalled_eval",
            avoidance_advice="Check eval worker heartbeat before retrying.",
        ),
    )
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="unrelated wiki refresh",
            error_class="lint",
            avoidance_advice="Unrelated",
        ),
    )

    hits = find_failure_cases(conn, "eval tower heartbeat timeout")

    assert len(hits) == 1
    assert hits[0]["root_cause_label"] == "stalled_eval"
    assert "heartbeat" in hits[0]["avoidance_advice"]
    assert hits[0]["_match_type"] == "lexical"
    assert hits[0]["_matched_terms"] == ["eval", "heartbeat", "timeout", "tower"]
    conn.close()


def test_find_failure_cases_prefers_exact_match_before_higher_governed_fuzzy_match(
    db_path: Path,
) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="eval tower timeout",
            governance_level=GovernanceLevel.RAW,
            avoidance_advice="exact note",
        ),
    )
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="eval tower timeout on another suite",
            governance_level=GovernanceLevel.APPROVED_BASELINE,
            avoidance_advice="fuzzy trusted note",
        ),
    )

    hits = find_failure_cases(conn, "eval tower timeout")

    assert hits[0]["avoidance_advice"] == "exact note"
    assert hits[0]["_match_type"] == "exact"
    assert hits[1]["avoidance_advice"] == "fuzzy trusted note"
    assert hits[1]["_match_type"] == "lexical"
    conn.close()


def test_find_failure_cases_warns_on_raw_when_governed_alternative_exists(
    db_path: Path,
) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="route selection failed",
            governance_level=GovernanceLevel.RAW,
            avoidance_advice="raw note",
        ),
    )
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="route selection failed",
            governance_level=GovernanceLevel.HUMAN_REVIEWED,
            avoidance_advice="reviewed note",
        ),
    )

    hits = find_failure_cases(conn, "route selection failed")

    assert hits[0]["avoidance_advice"] == "reviewed note"
    assert hits[0]["_governance_rank"] == GovernanceLevel.ORDER[GovernanceLevel.HUMAN_REVIEWED]
    assert hits[0]["_governance_warning"] is None
    assert hits[1]["avoidance_advice"] == "raw note"
    assert hits[1]["_governance_warning"] == "raw_advice_has_governed_alternative"
    conn.close()


def test_find_failure_cases_warns_when_deprecated_cases_are_requested(
    db_path: Path,
) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="old failure",
            governance_level=GovernanceLevel.DEPRECATED,
            avoidance_advice="obsolete note",
        ),
    )

    hits = find_failure_cases(conn, "old failure", exclude_deprecated=False)

    assert len(hits) == 1
    assert hits[0]["_governance_rank"] == GovernanceLevel.ORDER[GovernanceLevel.DEPRECATED]
    assert hits[0]["_governance_warning"] == "deprecated_advice"
    conn.close()


def test_ensure_harness_schema_rebuilds_failure_case_fts(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="planner failed after stale state",
            root_cause_label="stale_state",
        ),
    )
    conn.execute("DELETE FROM failure_case_fts")
    conn.commit()

    assert find_failure_cases(conn, "stale state") == []
    ensure_harness_schema(conn)
    hits = find_failure_cases(conn, "stale state")

    assert len(hits) == 1
    assert hits[0]["root_cause_label"] == "stale_state"
    conn.close()


def test_invalid_governance_level_rejected(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    with pytest.raises(ValueError):
        insert_failure_case(conn, FailureCase(task_signature="T", governance_level="bogus"))
    conn.close()


# ─── EXM-2: working state supersession ───────────────────────────────────────────


def test_working_state_supersedes_prior(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    set_working_state(
        conn,
        WorkingState(
            scope=WorkingStateScope.SESSION,
            owner="sess1",
            key="plan",
            value_json={"step": 1},
        ),
    )
    set_working_state(
        conn,
        WorkingState(
            scope=WorkingStateScope.SESSION,
            owner="sess1",
            key="plan",
            value_json={"step": 2},
        ),
    )
    current = get_working_state(conn, WorkingStateScope.SESSION, "plan", owner="sess1")
    assert json.loads(current["value_json"]) == {"step": 2}  # latest wins
    # History preserved: 2 rows, 1 live.
    total = conn.execute("SELECT COUNT(*) FROM working_state").fetchone()[0]
    live = conn.execute("SELECT COUNT(*) FROM working_state WHERE superseded=0").fetchone()[0]
    assert total == 2 and live == 1
    conn.close()


def test_working_state_scopes_isolated(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    set_working_state(
        conn, WorkingState(scope=WorkingStateScope.REQUEST, owner="r", key="k", value_json="a")
    )
    set_working_state(
        conn, WorkingState(scope=WorkingStateScope.SESSION, owner="r", key="k", value_json="b")
    )
    # Different scopes for same owner/key do not supersede each other.
    # (_jdump passes str through unchanged, matching detail_to_json convention.)
    assert get_working_state(conn, WorkingStateScope.REQUEST, "k", owner="r")["value_json"] == "a"
    assert get_working_state(conn, WorkingStateScope.SESSION, "k", owner="r")["value_json"] == "b"
    conn.close()


def test_working_state_expired_rows_are_not_current(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    set_working_state(
        conn,
        WorkingState(
            scope=WorkingStateScope.REQUEST,
            owner="req",
            key="draft",
            value_json={"stale": True},
            expires_at="2000-01-01T00:00:00+00:00",
        ),
    )

    assert get_working_state(conn, WorkingStateScope.REQUEST, "draft", owner="req") is None
    superseded = conn.execute(
        "SELECT superseded FROM working_state WHERE owner = ? AND key = ?",
        ("req", "draft"),
    ).fetchone()[0]
    assert superseded == 1
    conn.close()


def test_working_state_future_expiry_remains_current(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    set_working_state(
        conn,
        WorkingState(
            scope=WorkingStateScope.TRIAL,
            owner="trial-1",
            key="hypothesis",
            value_json={"active": True},
            expires_at="2999-01-01T00:00:00+00:00",
        ),
    )

    current = get_working_state(conn, WorkingStateScope.TRIAL, "hypothesis", owner="trial-1")

    assert json.loads(current["value_json"]) == {"active": True}
    assert current["superseded"] == 0
    conn.close()


def test_invalid_scope_rejected(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    with pytest.raises(ValueError):
        set_working_state(conn, WorkingState(scope="bogus", key="k"))
    conn.close()


def test_get_working_state_missing_returns_none(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    assert get_working_state(conn, WorkingStateScope.SESSION, "nope") is None
    conn.close()


# ─── cross-family integration (the schema's whole point) ─────────────────────────


def test_cross_family_event_id_linkage(db_path: Path) -> None:
    """A failure → approval → behavior_signature → harness_metrics chain links by id."""
    conn = ensure_schema(db_path)
    hm_event_id = 301
    bs_event_id = 302
    approval_event_id = 303
    hm = insert_harness_metrics(
        conn, HarnessMetrics(event_id=hm_event_id, suite="repl", trial_id=3)
    )
    bs = insert_behavior_signature(
        conn,
        BehaviorSignature(
            archive_member_id="cfg", trial_id=3, event_id=bs_event_id, harness_metrics_id=hm
        ),
    )
    ar = insert_approval_record(
        conn,
        ApprovalRecord(
            request_id="r", event_id=approval_event_id, task_signature="T", behavior_signature_id=bs
        ),
    )
    insert_failure_case(
        conn,
        FailureCase(
            task_signature="T",
            governance_level=GovernanceLevel.HUMAN_REVIEWED,
            evidence_event_ids=[hm_event_id, bs_event_id, approval_event_id],
        ),
    )
    counts = table_counts(conn)
    assert counts == {
        "harness_metrics": 1,
        "oracle_adequacy": 0,
        "behavior_signature": 1,
        "approval_record": 1,
        "failure_case": 1,
        "working_state": 0,
    }
    # The approval points at the signature, which points at the metrics.
    approval_row = conn.execute(
        "SELECT event_id, behavior_signature_id FROM approval_record WHERE id=?", (ar,)
    ).fetchone()
    assert approval_row == (approval_event_id, bs)
    ar_row = approval_row[1]
    bs_row = conn.execute(
        "SELECT event_id, harness_metrics_id FROM behavior_signature WHERE id=?", (ar_row,)
    ).fetchone()
    assert bs_row == (bs_event_id, hm)
    failure_events = conn.execute("SELECT evidence_event_ids FROM failure_case").fetchone()[0]
    assert json.loads(failure_events) == [hm_event_id, bs_event_id, approval_event_id]
    conn.close()

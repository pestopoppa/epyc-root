"""UTM-P1a: the review plane is the first live producer stamping the pairing keys.

Zero inference -- ``ArchitectReviewService`` runs over a stub ``llm_call``. Covers:

  * every review-plane row carries ``harness`` (service-level, injectable) and
    ``schema_version == 2``;
  * ``task_key`` is a PASS-THROUGH of the TaskIR ``task_id`` -- never derived from
    a step id, NULL when the caller supplied none;
  * ``turn_ordinal`` is stamped only where a genuine turn index exists (the plan
    step index) and a malformed ordinal degrades to NULL without dropping the row;
  * ``seed`` is never stamped (``llm_call`` has no seed);
  * through the REAL write path two harnesses on one ``task_key`` come back from
    ``paired_runs()`` as a non-empty pairing;
  * a legacy (pre-v2) store migrates on first write and its old rows still read
    back with the pairing keys NULL and ``schema_version`` NULL, never back-filled.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.proactive_delegation.review_service import (
    REVIEW_HARNESS,
    ArchitectReviewService,
    _pairing_ordinal,
    _pairing_task_key,
)
from src.trace import EVENT_SCHEMA_VERSION, EventSource, paired_runs, query
from src.trace.store import _SCHEMA as _store_schema

APPROVE = '{"d":"approve","s":0.9,"f":"ok"}'


class StubPrimitives:
    """``llm_call`` returns a canned string; no model is ever contacted."""

    def __init__(self, response: str = APPROVE):
        self.response = response

    def llm_call(self, prompt, role=None, n_tokens=None, **kwargs):
        return self.response


@pytest.fixture
def capturing_service():
    events: list = []

    def _make(**kwargs):
        kwargs.setdefault("trace_sink", events.append)
        return ArchitectReviewService(StubPrimitives(), **kwargs), events

    return _make


def _review(svc, task_id: str | None = "task-A", step: str = "S1"):
    spec = {"objective": "o"}
    if task_id is not None:
        spec["task_id"] = task_id
    return svc.review(spec=spec, subtask={"id": step, "action": "a"}, output="hello")


# ─── captured Events (no DB) ────────────────────────────────────────────────────


def test_review_event_carries_harness_and_taskir_task_id(capturing_service):
    svc, events = capturing_service()
    _review(svc, task_id="task-A")
    assert len(events) == 1
    ev = events[0]
    assert ev.source == EventSource.REVIEW_PLANE
    assert ev.harness == REVIEW_HARNESS == "orchestrator"
    assert ev.task_key == "task-A"
    assert ev.schema_version == EVENT_SCHEMA_VERSION == 2
    # Keys the review plane genuinely cannot know stay NULL.
    assert ev.seed is None
    assert ev.turn_ordinal is None


def test_task_key_is_never_derived_from_step_id(capturing_service):
    svc, events = capturing_service()
    _review(svc, task_id=None, step="S1")
    assert events[0].task_key is None
    assert events[0].harness == "orchestrator"


def test_blank_task_id_stays_null(capturing_service):
    svc, events = capturing_service()
    _review(svc, task_id="   ")
    assert events[0].task_key is None


def test_harness_is_injectable_and_optional(capturing_service):
    svc, events = capturing_service(harness="review_replay")
    _review(svc)
    assert events[0].harness == "review_replay"

    svc2, events2 = capturing_service(harness=None)
    _review(svc2)
    assert events2[-1].harness is None

    svc3, events3 = capturing_service(harness="  ")
    _review(svc3)
    assert events3[-1].harness is None


def test_every_emit_path_carries_harness(capturing_service):
    """Not just review(): plan review, candidate review, shadow decide, escalate."""
    svc, events = capturing_service()
    svc.review_plan(
        objective="o", task_type="code", plan_steps=[{"id": "S1", "actor": "coder", "action": "x"}]
    )
    svc.review_candidate({"task_ref": "T1", "objective": "x", "outputs": []}, subtask_id="C1")
    svc.build_plan_reminder(
        [{"id": "S1", "actor": "coder", "action": "x"}], cadence_n=1, step_index=3, emit=True
    )
    assert len(events) >= 3
    assert {ev.harness for ev in events} == {"orchestrator"}
    assert all(ev.schema_version == 2 for ev in events)


def test_plan_reminder_stamps_step_index_as_turn_ordinal(capturing_service):
    svc, events = capturing_service()
    plan = [{"id": "S1", "actor": "coder", "action": "x"}]
    msg = svc.build_plan_reminder(plan, cadence_n=5, step_index=10, emit=True)
    assert msg is not None
    assert len(events) == 1
    assert events[0].category == "plan_reminder"
    assert events[0].turn_ordinal == 10
    assert events[0].task_key is None  # the reminder path holds no task identity


def test_malformed_ordinal_degrades_to_null_without_dropping_row(capturing_service):
    svc, events = capturing_service()
    svc._emit_review_event(category="review_decision", summary="s", detail={}, turn_ordinal=-1)
    svc._emit_review_event(category="review_decision", summary="s", detail={}, turn_ordinal=True)
    svc._emit_review_event(category="review_decision", summary="s", detail={}, turn_ordinal="3")
    assert len(events) == 3
    assert all(ev.turn_ordinal is None for ev in events)


@pytest.mark.parametrize(
    "value,expected",
    [(None, None), ("", None), ("  ", None), ("t-1", "t-1"), (" t-1 ", "t-1"), (42, "42")],
)
def test_pairing_task_key_normalization(value, expected):
    assert _pairing_task_key(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (0, 0),
        (7, 7),
        (-1, None),
        (True, None),
        (False, None),
        ("3", None),
        (2.0, None),
    ],
)
def test_pairing_ordinal_normalization(value, expected):
    assert _pairing_ordinal(value) == expected


# ─── real write path -> paired_runs() ──────────────────────────────────────────


def _service(db: Path, harness: str, response: str = APPROVE) -> ArchitectReviewService:
    return ArchitectReviewService(StubPrimitives(response), trace_db_path=str(db), harness=harness)


def test_two_harnesses_same_task_key_pair_through_real_store(tmp_path):
    db = tmp_path / "events.sqlite"
    _review(_service(db, "orchestrator"), task_id="task-X")
    _review(_service(db, "hermes"), task_id="task-X")
    _review(_service(db, "orchestrator"), task_id="task-Y")  # a different task: excluded

    pairs = paired_runs("task-X", db_path=db)
    assert pairs, "paired_runs() must be non-empty once a live producer stamps task_key"
    # The review plane holds no turn index for review(), so both sides land on the
    # NULL ordinal cell -- and BOTH harnesses are present in it.
    assert set(pairs) == {None}
    assert set(pairs[None]) == {"orchestrator", "hermes"}
    for h, rows in pairs[None].items():
        assert len(rows) == 1
        assert rows[0]["task_key"] == "task-X"
        assert rows[0]["harness"] == h
        assert rows[0]["schema_version"] == 2
        assert rows[0]["seed"] is None

    assert set(paired_runs("task-X", db_path=db, harnesses=["hermes"])[None]) == {"hermes"}
    assert paired_runs("task-Z", db_path=db) == {}


def test_identical_content_from_two_harnesses_stays_two_rows(tmp_path):
    """The content key is harness-aware: same task, same verdict, two rows."""
    db = tmp_path / "events.sqlite"
    svc_a = _service(db, "orchestrator")
    svc_b = _service(db, "hermes")
    _review(svc_a, task_id="task-X")
    _review(svc_b, task_id="task-X")
    rows = query(db_path=db, task_key="task-X")
    assert sorted(r["harness"] for r in rows) == ["hermes", "orchestrator"]


# ─── legacy (pre-v2) store ─────────────────────────────────────────────────────

_V2_COLUMN_LINES = (
    "  harness TEXT,\n",
    "  seed INTEGER,\n",
    "  turn_ordinal INTEGER,\n",
    "  task_key TEXT,\n",
    "  schema_version INTEGER,\n",
)


def _make_v1_store(path: Path) -> None:
    ddl = _store_schema
    for line in _V2_COLUMN_LINES:
        assert line in ddl, line
        ddl = ddl.replace(line, "")
    conn = sqlite3.connect(str(path))
    conn.executescript(ddl)
    conn.execute(
        "INSERT INTO event (ts_utc, source, source_path, source_line, summary, category) "
        "VALUES ('2026-01-01T00:00:00+00:00', 'review_plane', 'emit://review_plane/legacy', 0, "
        "'legacy review row', 'review_decision')"
    )
    conn.commit()
    conn.close()


def test_legacy_rows_read_back_unstamped_next_to_new_producer_rows(tmp_path):
    db = tmp_path / "v1.sqlite"
    _make_v1_store(db)

    # First live write migrates the store additively and lands a stamped row.
    _review(_service(db, "orchestrator"), task_id="task-X")

    rows = sorted(query(db_path=db, source="review_plane"), key=lambda r: r["ts_utc"])
    assert len(rows) == 2
    legacy, fresh = rows
    assert legacy["summary"] == "legacy review row"
    # Never back-filled: NULL means "never captured", not "orchestrator".
    assert legacy["harness"] is None
    assert legacy["task_key"] is None
    assert legacy["seed"] is None
    assert legacy["turn_ordinal"] is None
    assert legacy["schema_version"] is None
    assert fresh["harness"] == "orchestrator"
    assert fresh["task_key"] == "task-X"
    assert fresh["schema_version"] == 2

    # The legacy row cannot be one side of a pair; only the stamped row pairs.
    pairs = paired_runs("task-X", db_path=db)
    assert set(pairs[None]) == {"orchestrator"}
    assert len(pairs[None]["orchestrator"]) == 1

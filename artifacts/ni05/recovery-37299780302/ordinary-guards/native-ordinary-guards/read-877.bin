"""UTM-P1a.2: a SECOND producer, so ``paired_runs()`` is cross-harness on real data.

Zero inference -- every ``llm_call`` here is a canned string; the replay harness's
live-server seam is replaced by a stub. Covers:

  * the 50-question replay harness (``scripts/review/review_replay_50.py``) stamps
    its OWN ``harness`` ("review_replay") and the corpus ``task_id`` as ``task_key``
    on every review row it writes, through the real write path;
  * a live-review row (``harness="orchestrator"``, ``spec["task_id"]``) and a replay
    row for the SAME task id come back from ``paired_runs()`` as a two-harness
    pairing against one real temp store;
  * the delegator's review-fix loop passes its 0-based iteration index as
    ``turn_ordinal`` into ``review()`` -- the ordinal ARRIVES on the trace row;
  * identities a call site does not genuinely hold stay NULL: ``review_candidate``
    without ``task_key``, ``review()`` without ``turn_ordinal``, the one-shot
    final-aggregate review, and ``seed`` everywhere.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.proactive_delegation.delegator import ProactiveDelegator, ReviewPlaneKnobs
from src.proactive_delegation.review_service import REVIEW_HARNESS, ArchitectReviewService
from src.trace import EVENT_SCHEMA_VERSION, paired_runs, query

_REPO = Path(__file__).resolve().parents[2]
_REPLAY_PATH = _REPO / "scripts" / "review" / "review_replay_50.py"

# review() parses the compact grammar; review_candidate parses the RD-6 object.
APPROVE = '{"d":"approve","s":0.9,"f":"ok"}'
REQUEST_CHANGES = '{"d":"request_changes","s":0.3,"f":"tighten"}'
RD6_APPROVE = (
    '{"decision":"approve","confidence":0.8,"blocking":{"tripwire":false},'
    '"advisory":{"score":0.9,"feedback":"ok"}}'
)


def _load_replay_module():
    spec = importlib.util.spec_from_file_location("review_replay_50_under_test", _REPLAY_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class StubPrimitives:
    """Canned ``llm_call``; mirrors the replay seam's ``usage_log`` attribute."""

    def __init__(self, responses: list[str] | None = None, default: str = APPROVE):
        self.responses = list(responses or [])
        self.default = default
        self.usage_log: list[dict] = []
        self.calls: list[str] = []

    def llm_call(self, prompt, role=None, n_tokens=None, **kwargs):
        self.calls.append(prompt)
        return self.responses.pop(0) if self.responses else self.default


QUESTIONS = [
    {
        "task_id": "rr50-001",
        "objective": "Which planet is closest to the sun?",
        "outputs": [{"type": "answer", "ref": "out-001", "summary": "Mercury."}],
        "acceptance_checks": [{"id": "A1", "statement": "Names Mercury."}],
        "executor_model_id": "frontdoor-35b-iq2",
    },
    {
        "task_id": "rr50-002",
        "objective": "Boiling point of water at sea level?",
        "outputs": [{"type": "answer", "ref": "out-002", "summary": "100 C."}],
        "acceptance_checks": [{"id": "A1", "statement": "States 100 C."}],
        "executor_model_id": "frontdoor-35b-iq2",
    },
]


def _run_replay(tmp_path: Path, db: Path) -> dict:
    mod = _load_replay_module()
    report = mod.run_shadow(
        QUESTIONS,
        StubPrimitives(default=RD6_APPROVE),
        trace_db=db,
        artifacts_dir=None,
        report_out=tmp_path / "report.json",
    )
    assert report["trace_coverage"]["coverage_pct"] == 100.0
    assert report["service"]["parse_failure_count"] == 0
    return report


def _candidate_rows(rows: list[dict]) -> list[dict]:
    """The ``review_candidate`` rows only (``shadow_decide`` shares the category)."""
    return [r for r in rows if r["summary"].startswith("review_candidate ")]


# ─── replay harness stamps its own harness + corpus task_key ───────────────────


def test_replay_module_names_its_own_harness():
    mod = _load_replay_module()
    assert mod.REPLAY_HARNESS == "review_replay"
    assert mod.REPLAY_HARNESS != REVIEW_HARNESS


def test_replay_review_rows_carry_replay_harness_and_corpus_task_key(tmp_path):
    db = tmp_path / "replay.sqlite"
    _run_replay(tmp_path, db)

    decisions = _candidate_rows(query(db_path=db, category="review_decision", limit=100))
    assert len(decisions) == len(QUESTIONS)
    assert {r["harness"] for r in decisions} == {"review_replay"}
    assert {r["task_key"] for r in decisions} == {q["task_id"] for q in QUESTIONS}
    for row in decisions:
        assert row["schema_version"] == EVENT_SCHEMA_VERSION
        # Keys the replay harness does not genuinely hold stay NULL: it has no RNG
        # seed and review_candidate is a one-shot review with no turn index.
        assert row["seed"] is None
        assert row["turn_ordinal"] is None

    # Every row the replay writes (decision, shadow, reminder) names the harness.
    all_rows = query(db_path=db, limit=1000)
    assert all_rows and {r["harness"] for r in all_rows} == {"review_replay"}


# ─── the cross-harness pairing the box asks for ───────────────────────────────


def test_live_review_and_replay_pair_on_the_corpus_task_id(tmp_path):
    db = tmp_path / "shared.sqlite"

    # Side A: the offline replay harness over the pinned corpus. It goes FIRST
    # because run_shadow() unlinks a pre-existing trace DB (TM-8 fresh-run rule).
    _run_replay(tmp_path, db)
    # Side B: the live review plane, as the delegator drives it -- spec IS the
    # TaskIR, and its task_id is the corpus id -- written into the SAME store.
    live = ArchitectReviewService(StubPrimitives(), trace_db_path=str(db))
    live.review(
        spec={"task_id": "rr50-001", "objective": "Which planet is closest to the sun?"},
        subtask={"id": "S1", "action": "answer"},
        output="Mercury",
    )

    pairs = paired_runs("rr50-001", db_path=db)
    assert pairs, "two producers on one task_key must yield a non-empty pairing"
    # Neither side holds a turn index for a one-shot review: both land in the
    # NULL-ordinal cell, and BOTH harnesses are present in it.
    assert set(pairs) == {None}
    assert set(pairs[None]) == {"orchestrator", "review_replay"}
    for harness, rows in pairs[None].items():
        decision_rows = [
            r
            for r in rows
            if r["category"] == "review_decision"
            and not r["summary"].startswith("shadow_decide ")
        ]
        assert len(decision_rows) == 1, [r["summary"] for r in rows]
        assert decision_rows[0]["harness"] == harness
        assert decision_rows[0]["task_key"] == "rr50-001"

    # A corpus task the live side never reviewed is one-sided, not fabricated.
    only_replay = paired_runs("rr50-002", db_path=db)
    assert set(only_replay[None]) == {"review_replay"}
    assert paired_runs("rr50-999", db_path=db) == {}


# ─── review_candidate: task_key is pass-through, never derived ────────────────


def test_review_candidate_task_key_is_pass_through_and_null_by_default():
    events: list = []
    svc = ArchitectReviewService(StubPrimitives(), trace_sink=events.append)
    view = {"task_ref": "T-ref", "objective": "x", "outputs": []}

    svc.review_candidate(view, subtask_id="C1")
    svc.review_candidate(view, subtask_id="C1", task_key="rr50-007")
    svc.review_candidate(view, subtask_id="C1", task_key="   ")

    assert [ev.task_key for ev in events] == [None, "rr50-007", None]
    # Never derived from subtask_id or task_ref.
    assert "C1" not in {ev.task_key for ev in events}
    assert "T-ref" not in {ev.task_key for ev in events}


# ─── delegator: the review-iteration index arrives as turn_ordinal ────────────


def _capturing_delegator(responses: list[str]):
    events: list = []
    registry = Mock()
    registry.roles = {}
    primitives = StubPrimitives(default="specialist output")
    delegator = ProactiveDelegator(registry, primitives, max_iterations=3)
    # Swap the reviewer's model for a canned sequence; keep the REAL review().
    delegator.review_service = ArchitectReviewService(
        StubPrimitives(responses), trace_sink=events.append
    )
    return delegator, events


@pytest.mark.asyncio
async def test_delegator_passes_iteration_index_as_turn_ordinal():
    delegator, events = _capturing_delegator([REQUEST_CHANGES, REQUEST_CHANGES, APPROVE])
    task_ir = {
        "task_id": "task-D",
        "objective": "o",
        "plan": {"steps": [{"id": "S1", "actor": "coder", "action": "Write code"}]},
    }
    with patch("src.features.features") as mock_features:
        mock_features.return_value.parallel_execution = False
        result = await delegator.delegate(task_ir)

    assert result.all_approved is True
    decisions = [ev for ev in events if ev.category == "review_decision"]
    assert [ev.turn_ordinal for ev in decisions] == [0, 1, 2]
    assert {ev.task_key for ev in decisions} == {"task-D"}
    assert {ev.harness for ev in decisions} == {"orchestrator"}
    assert all(ev.seed is None for ev in decisions)


@pytest.mark.asyncio
async def test_delegator_ordinal_restarts_per_step_and_never_derives_task_key():
    delegator, events = _capturing_delegator([APPROVE, REQUEST_CHANGES, APPROVE])
    task_ir = {  # no task_id: task_key must stay NULL, never "S1"/"S2"
        "objective": "o",
        "plan": {
            "steps": [
                {"id": "S1", "actor": "coder", "action": "a"},
                {"id": "S2", "actor": "worker", "action": "b"},
            ]
        },
    }
    with patch("src.features.features") as mock_features:
        mock_features.return_value.parallel_execution = False
        await delegator.delegate(task_ir)

    decisions = [ev for ev in events if ev.category == "review_decision"]
    # S1 approved at iteration 0; S2 needed iterations 0 and 1.
    assert [ev.turn_ordinal for ev in decisions] == [0, 0, 1]
    assert all(ev.task_key is None for ev in decisions)


def test_review_without_ordinal_stays_null():
    events: list = []
    svc = ArchitectReviewService(StubPrimitives(), trace_sink=events.append)
    svc.review(spec={"task_id": "t"}, subtask={"id": "S1"}, output="x")
    svc.review(spec={"task_id": "t"}, subtask={"id": "S1"}, output="x", turn_ordinal=4)
    svc.review(spec={"task_id": "t"}, subtask={"id": "S1"}, output="x", turn_ordinal="4")
    assert [ev.turn_ordinal for ev in events] == [None, 4, None]


@pytest.mark.asyncio
async def test_final_aggregate_review_holds_no_ordinal():
    """The RD-10b aggregate review is one-shot: no loop, no invented 0."""
    events: list = []
    registry = Mock()
    registry.roles = {}
    # RD-10b knob: per-subtask review OFF routes every step to the aggregate review.
    knobs = ReviewPlaneKnobs(per_subtask_review_enabled=False)
    delegator = ProactiveDelegator(registry, StubPrimitives(default="out"), review_knobs=knobs)
    delegator.review_service = ArchitectReviewService(StubPrimitives(), trace_sink=events.append)
    task_ir = {
        "task_id": "task-AGG",
        "objective": "o",
        "plan": {"steps": [{"id": "S1", "actor": "coder", "action": "a"}]},
    }
    with patch("src.features.features") as mock_features:
        mock_features.return_value.parallel_execution = False
        result = await delegator.delegate(task_ir)

    assert result.all_approved is True
    decisions = [ev for ev in events if ev.category == "review_decision"]
    assert len(decisions) == 1 and "__final_aggregate__" in decisions[0].summary
    assert decisions[0].turn_ordinal is None
    assert decisions[0].task_key == "task-AGG"

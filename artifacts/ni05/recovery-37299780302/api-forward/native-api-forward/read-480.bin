"""A live-serving INFRA failure must never reach the MemRL reward writer.

`tests/unit/test_infra_reward_emission_guard.py` (commit 5d494c2d) pins the same
property on the SEEDING path. This file pins the LIVE-SERVING path, which that
fix did not touch.

The defect, re-derived from the code:

  1. Every live-serving failure branch called
     ``progress_logger.log_task_completed(task_id, success=False, ...)`` and then
     ``score_completed_task(state, task_id)`` — with no disposition check.
  2. ``log_task_completed(success=False)`` writes a TASK_FAILED entry with
     ``outcome="failure"``, so ``q_reward.compute_reward`` takes the
     ``config.failure_reward = -0.5`` branch (`q_scorer.py:1040`).
  3. ``QScorer._update_routing_memory`` maps that onto
     ``initial_q = 0.5 + (reward * 0.5) = 0.25``.
  4. The retrieval floor is ``MemRLRetrievalConfigData.min_q_value = 0.3``
     (`src/config/models.py`), applied by
     ``EpisodicStore.retrieve_by_similarity`` as ``q_value >= min_q_value``.

  0.25 < 0.3 — so a transient backend blip permanently evicted that memory from
  the learned router.

What is NOT the fix: suppressing all failures. That would make every guard here
pass while destroying the router's ability to learn from genuine wrong answers —
the model would only ever learn from successes and could never learn that a role
is bad at something. So each property below is pinned in BOTH directions: infra
emits nothing, a genuine task failure still emits its negative signal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from orchestration.repl_memory.progress_logger import (  # noqa: E402
    EventType,
    ProgressEntry,
)
from orchestration.repl_memory.q_scorer import QScorer, ScoringConfig  # noqa: E402
from src.api.services.memrl import (  # noqa: E402
    failure_disposition_meta,
    task_failure_disposition,
)
from src.autopilot_core.measurement_guards import (  # noqa: E402
    DISPOSITION_INFRA_FAILED,
    DISPOSITION_TASK_FAILED,
    FAILURE_DISPOSITION_KEY,
)
from src.config.models import MemRLRetrievalConfigData  # noqa: E402


# ── The two numbers the whole defect turns on ────────────────────────


def _initial_q_for(reward: float) -> float:
    """The mapping `QScorer._update_routing_memory` applies to a first write."""
    return 0.5 + (reward * 0.5)


def test_failure_reward_maps_below_the_retrieval_floor():
    """The arithmetic that made a failure unretrievable, pinned explicitly.

    If either constant moves, this breaks LOUDLY instead of silently evicting
    memories again.
    """
    failure_reward = ScoringConfig().failure_reward
    floor = MemRLRetrievalConfigData().min_q_value

    assert failure_reward == -0.5
    assert floor == 0.3
    assert _initial_q_for(failure_reward) == pytest.approx(0.25)
    assert _initial_q_for(failure_reward) < floor, (
        "A scored task failure lands under the retrieval floor. That is only "
        "acceptable for GENUINE failures; it is why infra failures must never "
        "be scored at all."
    )


def test_success_reward_stays_above_the_retrieval_floor():
    """Control: the same mapping on a success is retrievable. Pins direction."""
    cfg = ScoringConfig()
    floor = MemRLRetrievalConfigData().min_q_value
    assert _initial_q_for(cfg.success_reward) > floor


# ── Classification: which exceptions are infra ───────────────────────

_INFRA_EXCEPTIONS = {
    "connect_error": ConnectionError("[Errno 111] Connection refused"),
    "read_timeout": TimeoutError("Read timed out"),
    "backend_unreachable": OSError("Backend unavailable (circuit open): http://localhost:8081"),
    "inband_banner": RuntimeError("[ERROR: Backend unavailable (circuit open): http://x]"),
}

_TASK_EXCEPTIONS = {
    "application_bug": ValueError("unhashable type: 'list'"),
    "key_error": KeyError("expected_field"),
    "assertion": AssertionError("role_history must be non-empty"),
}


@pytest.mark.parametrize("name", sorted(_INFRA_EXCEPTIONS))
def test_backend_exceptions_classify_as_infra(name):
    assert task_failure_disposition(error=_INFRA_EXCEPTIONS[name]) == (
        DISPOSITION_INFRA_FAILED
    )


@pytest.mark.parametrize("name", sorted(_TASK_EXCEPTIONS))
def test_application_bugs_do_not_classify_as_infra(name):
    """A genuine application error is NOT infra — treating them identically is
    how this defect happened."""
    assert task_failure_disposition(error=_TASK_EXCEPTIONS[name]) == (
        DISPOSITION_TASK_FAILED
    )


def test_inband_error_answer_classifies_as_infra():
    """`direct_stage` sets success=False on `[ERROR: ...]` — a backend fact."""
    answer = "[ERROR: Direct LLM call cancelled/timed out: deadline exceeded]"
    assert task_failure_disposition(answer=answer) == DISPOSITION_INFRA_FAILED


def test_wrong_answer_is_not_infra():
    """A confidently wrong answer must stay scoreable."""
    answer = "The capital of Australia is Sydney."
    assert task_failure_disposition(answer=answer) != DISPOSITION_INFRA_FAILED


def test_max_turns_exhaustion_is_a_task_failure_not_infra():
    """`repl_executor` sets success=False on `[Max turns ...]`. The role DID run
    and failed to finish — that is exactly the signal the router must keep."""
    assert task_failure_disposition(
        answer="[Max turns reached without FINAL()]", tokens_generated=812
    ) != DISPOSITION_INFRA_FAILED


# ── The stamp the serving pipeline puts on the progress entry ────────


def test_infra_failure_is_stamped_into_completion_meta():
    meta = failure_disposition_meta(error=ConnectionError("Connection refused"))
    assert meta[FAILURE_DISPOSITION_KEY] == DISPOSITION_INFRA_FAILED


def test_genuine_task_failure_is_not_stamped():
    """An unstamped entry is what keeps the negative reward flowing."""
    assert failure_disposition_meta(error=ValueError("bad plan shape")) == {}
    assert failure_disposition_meta(answer="Sydney is the capital.") == {}


# ── The reward writer itself ─────────────────────────────────────────


class _RecordingStore:
    """Records every write the reward path would make."""

    def __init__(self):
        self.stored: list[dict] = []
        self.q_updates: list[tuple] = []

    def store(self, **kwargs):
        self.stored.append(kwargs)
        return "mem-new"

    def get_by_id(self, memory_id):
        return None

    def update_q_value(self, memory_id, reward, lr, **kwargs):
        self.q_updates.append((memory_id, reward, lr))
        return 0.25

    def retrieve_by_similarity(self, *a, **k):
        return []

    @property
    def writes(self) -> int:
        return len(self.stored) + len(self.q_updates)


class _StubEmbedder:
    def embed_task_ir(self, task_context):
        return [0.0] * 8


class _StubLogger:
    def __init__(self):
        self.entries: list = []

    def log(self, entry):
        self.entries.append(entry)

    def log_memory_update(self, *a, **k):
        self.entries.append(("memory_update", a))

    def flush(self):
        pass


class _StubReader:
    def __init__(self, trajectory):
        self._trajectory = trajectory

    def get_task_trajectory(self, task_id):
        return self._trajectory


def _trajectory(task_id: str, completion_meta: dict) -> list[ProgressEntry]:
    """The exact three-entry shape the serving path writes for a failure."""
    return [
        ProgressEntry(
            event_type=EventType.TASK_STARTED,
            task_id=task_id,
            data={
                "task_type": "chat",
                "objective": "What is the capital of Australia?",
                "priority": "interactive",
            },
        ),
        ProgressEntry(
            event_type=EventType.ROUTING_DECISION,
            task_id=task_id,
            data={"routing": ["worker_general"]},
            memory_id=None,
        ),
        ProgressEntry(
            event_type=EventType.TASK_FAILED,
            task_id=task_id,
            data=completion_meta,
            outcome="failure",
        ),
    ]


def _scorer_for(trajectory) -> tuple[QScorer, _RecordingStore]:
    store = _RecordingStore()
    scorer = QScorer(
        store=store,
        embedder=_StubEmbedder(),
        logger=_StubLogger(),
        reader=_StubReader(trajectory),
        config=ScoringConfig(),
    )
    return scorer, store


def test_backend_connection_error_writes_no_reward():
    """THE defect. An infra-stamped failure must produce ZERO episodic writes."""
    meta = {
        "producer_role": "worker_general",
        "final_answer_role": "worker_general",
        **failure_disposition_meta(error=ConnectionError("[Errno 111] Connection refused")),
    }
    assert meta[FAILURE_DISPOSITION_KEY] == DISPOSITION_INFRA_FAILED

    scorer, store = _scorer_for(_trajectory("chat-infra", meta))
    result = scorer._score_task("chat-infra")

    assert store.writes == 0, f"infra failure reached the reward writer: {store.stored}"
    assert result["memories_created"] == 0
    assert result["memories_updated"] == 0
    assert result.get("skipped") == DISPOSITION_INFRA_FAILED


def test_genuine_task_failure_still_writes_its_negative_reward():
    """The anti-suppression half. Without this, the router can only learn from
    successes and can never learn that a role is bad at something."""
    # `completion_meta` is deliberately NON-EMPTY (an empty dict is falsy and
    # would short-circuit the guard's own `data` check, making this test pass
    # vacuously against a suppress-everything mutation). It omits
    # `final_answer_role` / `producer_role` only to isolate the base reward from
    # delegation-credit and cost-penalty shaping, which have their own tests.
    meta = {
        "answer_chars": 34,
        # A wrong answer, not a backend error — so nothing is stamped.
        **failure_disposition_meta(answer="The capital of Australia is Sydney."),
    }
    assert FAILURE_DISPOSITION_KEY not in meta

    scorer, store = _scorer_for(_trajectory("chat-wrong", meta))
    result = scorer._score_task("chat-wrong")

    assert result["memories_created"] == 1
    assert store.writes == 1
    assert result["reward"] == pytest.approx(-0.5)


def test_genuine_task_failure_initial_q_sits_below_the_retrieval_floor():
    """Assert the resulting `initial_q` against the floor at the WRITE site.

    A future change to `failure_reward` or to `min_q_value` breaks this test
    rather than silently evicting memories again.
    """
    meta = {
        "answer_chars": 34,
        **failure_disposition_meta(answer="The capital of Australia is Sydney."),
    }
    scorer, store = _scorer_for(_trajectory("chat-wrong-q", meta))
    scorer._score_task("chat-wrong-q")

    assert len(store.stored) == 1
    initial_q = store.stored[0]["initial_q"]
    floor = MemRLRetrievalConfigData().min_q_value

    assert initial_q == pytest.approx(0.25)
    assert initial_q < floor
    assert store.stored[0]["outcome"] == "failure"


def test_unstamped_legacy_entry_is_unaffected():
    """Entries written before the stamp existed keep their old behaviour, so the
    guard cannot silently change the meaning of historical replay."""
    scorer, store = _scorer_for(
        _trajectory("chat-legacy", {"producer_role": "worker_general"})
    )
    result = scorer._score_task("chat-legacy")
    assert result["memories_created"] == 1
    assert store.writes == 1


def test_success_is_never_stamped_or_skipped():
    """Control on the success path: nothing about this change touches it."""
    trajectory = _trajectory("chat-ok", {"answer_chars": 34})
    trajectory[-1] = ProgressEntry(
        event_type=EventType.TASK_COMPLETED,
        task_id="chat-ok",
        data={"answer_chars": 34},
        outcome="success",
    )
    scorer, store = _scorer_for(trajectory)
    result = scorer._score_task("chat-ok")
    assert result["reward"] == pytest.approx(1.0)
    assert store.writes == 1
    assert store.stored[0]["initial_q"] == pytest.approx(1.0)

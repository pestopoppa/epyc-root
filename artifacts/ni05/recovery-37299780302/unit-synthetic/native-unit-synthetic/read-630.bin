"""`assigned_role` must survive from the classifier all the way to the DB column.

TR-3.2 classifies every request and `progress_logger.log_task_started` merges the
result into the ROUTING_DECISION entry, but no episodic write site ever read it
back: `memories.assigned_role` was NULL on all 59,337 rows, so TR-3.3 had no
durable shadow telemetry to decide promotion on.

These tests assert on the CONSUMER, not the producer — every assertion reads the
`assigned_role` column out of the SQLite row that `QScorer._score_task` wrote,
via the real ProgressLogger -> ProgressReader -> QScorer -> EpisodicStore chain.
A test that only checked `classify_trinity_role()`'s return value, or only
`routing_meta()`'s dict, would have passed for the entire lifetime of the bug.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from orchestration.repl_memory.episodic_store import EpisodicStore
from orchestration.repl_memory.progress_logger import ProgressLogger, ProgressReader
from orchestration.repl_memory.q_scorer import QScorer
from src.classifiers.role_taxonomy import DEFAULT_TRINITY_ROLE, normalise_role


class _StubEmbedder:
    """Deterministic non-degenerate unit vectors.

    EpisodicStore.store() rejects all-zero / non-finite / SHA-256-fallback
    embeddings, so the stub must produce a genuinely well-formed vector.
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _vec(self, seed_text: str) -> np.ndarray:
        rng = np.random.default_rng(abs(hash(seed_text)) % (2**32))
        vec = rng.standard_normal(self.dim).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def embed_task_ir(self, task_ir: dict) -> np.ndarray:
        return self._vec(str(task_ir.get("objective", "")))

    def embed_failure_context(self, failure_context: dict) -> np.ndarray:
        return self._vec(str(failure_context.get("reason", "")))


@pytest.fixture
def wiring(tmp_path):
    """Real store + real progress logger/reader + real QScorer."""
    store = EpisodicStore(db_path=tmp_path / "sessions", use_faiss=True)
    log_dir = tmp_path / "progress"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = ProgressLogger(log_dir=log_dir, buffer_size=1)
    reader = ProgressReader(log_dir=log_dir)
    scorer = QScorer(
        store=store,
        embedder=_StubEmbedder(store.embedding_dim),
        logger=logger,
        reader=reader,
    )
    yield scorer, store, logger
    store.close()


def _persisted_roles(store: EpisodicStore) -> dict[str, str | None]:
    """Read the column straight out of SQLite, keyed by action."""
    store.flush()
    conn = sqlite3.connect(store.sqlite_path)
    try:
        rows = conn.execute(
            "SELECT action, action_type, assigned_role FROM memories"
        ).fetchall()
    finally:
        conn.close()
    return {f"{action_type}:{action}": role for action, action_type, role in rows}


def _run_task(
    logger: ProgressLogger,
    scorer: QScorer,
    task_id: str,
    *,
    assigned_role: str | None,
    objective: str,
    escalate: bool = False,
) -> dict:
    """Drive the production emitters, then score the task."""
    routing_meta = {"decision_source": "rules"}
    if assigned_role is not None:
        routing_meta["assigned_role"] = assigned_role
    logger.log_task_started(
        task_id=task_id,
        task_ir={"task_type": "chat", "objective": objective, "priority": "normal"},
        routing_decision=["frontdoor"],
        routing_strategy="rules",
        routing_meta=routing_meta,
    )
    if escalate:
        logger.log_escalation(
            task_id=task_id,
            from_tier="frontdoor",
            to_tier="architect_general",
            reason=f"insufficient depth for {objective}",
        )
    logger.log_task_completed(task_id=task_id, success=True)
    logger.flush()
    return scorer._score_task(task_id)


@pytest.mark.parametrize("role", ["thinker", "worker", "verifier"])
def test_routing_memory_persists_assigned_role(wiring, role):
    """The classifier's role reaches the episodic COLUMN, not just the log."""
    scorer, store, logger = wiring
    result = _run_task(
        logger,
        scorer,
        f"task-{role}",
        assigned_role=role,
        objective=f"objective for {role}",
    )
    assert result["memories_created"] == 1, result

    roles = _persisted_roles(store)
    assert roles == {"routing:frontdoor": role}


def test_escalation_memory_inherits_the_task_role(wiring):
    """An escalation is a re-route of the SAME request, so it keeps its role."""
    scorer, store, logger = wiring
    result = _run_task(
        logger,
        scorer,
        "task-escalated",
        assigned_role="thinker",
        objective="deep architecture question",
        escalate=True,
    )
    assert result["memories_created"] == 2, result

    roles = _persisted_roles(store)
    assert roles["routing:frontdoor"] == "thinker"
    assert roles["escalation:escalate:frontdoor->architect_general"] == "thinker"


def test_missing_role_stays_null_and_is_not_coerced_to_worker(wiring):
    """Unknown must stay NULL: 'worker' has to mean the classifier said worker.

    `normalise_role` maps None -> 'worker', which is the right READ-side default
    (TR-1.5) and the wrong write-side behavior — coercing here would make the
    column indistinguishable from the NULL-everywhere bug it is meant to fix.
    """
    scorer, store, logger = wiring
    _run_task(
        logger,
        scorer,
        "task-no-role",
        assigned_role=None,
        objective="legacy caller with no role",
    )

    roles = _persisted_roles(store)
    assert roles["routing:frontdoor"] is None
    # The read side still defaults it, so downstream consumers are unaffected.
    assert normalise_role(roles["routing:frontdoor"]) == DEFAULT_TRINITY_ROLE


def test_foreign_role_string_is_rejected_not_laundered(wiring):
    """A SERVING role in the tri-role column would be a wrong value, not a fix."""
    scorer, store, logger = wiring
    _run_task(
        logger,
        scorer,
        "task-bad-role",
        assigned_role="frontdoor",  # a serving role, not a Trinity role
        objective="stale writer emitting a serving role",
    )

    roles = _persisted_roles(store)
    assert roles["routing:frontdoor"] is None


def test_sibling_model_id_is_also_threaded_to_the_store(wiring):
    """Guard the sibling column against the same evaporation.

    `model_id` was fixed in c05bc415 (NULL on all 59,337 rows) with no test that
    the value reaches the row — the exact gap that let `assigned_role` sit broken
    beside it. Asserting against `_model_id_for_action` rather than a literal
    keeps this from breaking every time a role changes weights; what it pins is
    that the kwarg is actually PASSED at the store site, not merely computable.
    """
    from orchestration.repl_memory.q_scorer import _model_id_for_action

    scorer, store, logger = wiring
    _run_task(
        logger,
        scorer,
        "task-model-id",
        assigned_role="worker",
        objective="sibling column check",
    )
    store.flush()

    conn = sqlite3.connect(store.sqlite_path)
    try:
        persisted = conn.execute("SELECT model_id FROM memories").fetchall()
    finally:
        conn.close()
    assert persisted == [(_model_id_for_action("frontdoor"),)]


def test_round_trips_through_the_store_read_path(wiring):
    """The value is readable back through the normal MemoryEntry read path."""
    scorer, store, logger = wiring
    _run_task(
        logger,
        scorer,
        "task-roundtrip",
        assigned_role="verifier",
        objective="check this proof",
    )
    store.flush()

    memories = store.get_all_memories()
    assert [m.assigned_role for m in memories] == ["verifier"]


def test_helper_validates_rather_than_coerces():
    """Unit-level guard on the extraction rule the write sites depend on.

    Imported inside the test on purpose: the persistence tests above must stay
    collectable against a tree that does not have this helper, so they can be
    run as a negative control on the pre-fix code.
    """
    from orchestration.repl_memory.progress_logger import EventType, ProgressEntry
    from orchestration.repl_memory.q_scorer import _assigned_role_from_entry

    def entry(data):
        return ProgressEntry(
            event_type=EventType.ROUTING_DECISION, task_id="t", data=data
        )

    assert _assigned_role_from_entry(entry({"assigned_role": "  VERIFIER "})) == "verifier"
    assert _assigned_role_from_entry(entry({"assigned_role": "worker"})) == "worker"
    assert _assigned_role_from_entry(entry({"assigned_role": "architect_general"})) is None
    assert _assigned_role_from_entry(entry({"assigned_role": 7})) is None
    assert _assigned_role_from_entry(entry({})) is None
    assert _assigned_role_from_entry(None) is None

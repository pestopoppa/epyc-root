"""
EpisodicStore: SQLite-backed episodic memory with FAISS or numpy embeddings.

Stores memories as (embedding, action, outcome, q_value) tuples with efficient
retrieval by embedding similarity and Q-value ranking.

Supports two embedding backends:
- FAISS (default): O(log n) search, ~70x faster at scale
- NumPy (legacy): O(n) search, for migration/fallback

Enhanced with optional graph integration:
- FailureGraph: Tracks failure patterns and mitigations
- HypothesisGraph: Tracks action-task confidence
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import numpy as np

from .indexed_memory_policy import indexed_memory_predicate, is_indexed_action_type

_REPO_ROOT = Path(__file__).resolve().parents[2]

if TYPE_CHECKING:
    from .faiss_store import FAISSEmbeddingStore, NumpyEmbeddingStore
    from .failure_graph import FailureGraph
    from .hypothesis_graph import HypothesisGraph

logger = logging.getLogger(__name__)

# Default paths (on RAID array per CLAUDE.md requirements)
DEFAULT_DB_PATH = _REPO_ROOT / "orchestration/repl_memory/sessions"
DEFAULT_EMBEDDINGS_PATH = _REPO_ROOT / "orchestration/repl_memory/embeddings.npy"


def apply_td_update(
    old_q: float,
    reward: float,
    learning_rate: float,
    *,
    days_elapsed: float = 0.0,
    temporal_decay_rate: float | None = None,
) -> float:
    """Pure TD(0)-style Q update with optional temporal decay toward neutral.

    Extracted so the live update path (``EpisodicStore.update_q_value``) and the
    offline append-only consolidation migration
    (``scripts/maintenance/consolidate_q_append_only.py``) apply byte-identical
    math — the migration replays the same TD/decay a live store would have if the
    write path had TD-updated in place instead of blind-appending:

        Q_decayed = 0.5 + (Q_old - 0.5) * decay_rate ** days_elapsed   (if decay)
        Q_new     = clamp_[0,1]( Q_decayed + lr * (reward - Q_decayed) )

    Decay is applied only when ``temporal_decay_rate is not None`` AND
    ``days_elapsed > 0`` — identical guard to the live path, so a zero/negative
    elapsed (or disabled decay) is a plain TD update.

    Args:
        old_q: Current stored Q-value.
        reward: Observed reward on the same scale as live scoring.
        learning_rate: TD learning rate α.
        days_elapsed: Days since the value was last updated (decay only).
        temporal_decay_rate: Per-day decay toward 0.5, or None to disable.

    Returns:
        New Q-value clamped to [0, 1].
    """
    if temporal_decay_rate is not None and days_elapsed > 0:
        old_q = 0.5 + (old_q - 0.5) * (temporal_decay_rate ** days_elapsed)
    new_q = old_q + learning_rate * (reward - old_q)
    return max(0.0, min(1.0, new_q))


def outcome_from_reward(reward: float) -> str:
    """First-observation label, used at INSERT (``q_scorer.py``)."""
    return "success" if reward > 0 else "failure"


def outcome_from_q(q_value: float) -> str:
    """Current label: which side of the neutral 0.5 the running Q sits on (EPD-1).

    Used by ``update_q_value`` so ``outcome`` never contradicts ``q_value`` —
    a single late reward must not flip a Q=0.9 row to ``failure``.
    """
    return "success" if q_value > 0.5 else "failure"


@contextmanager
def _exclusive_file_lock(path: Path):
    """Cross-process lock for FAISS index/id-map mutations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)



class DegenerateEmbeddingError(ValueError):
    """Raised when a write would persist an unusable embedding vector."""


def _embedding_rejection_reason(embedding, context) -> Optional[str]:
    """Why this embedding must not be persisted, or None if it is fine.

    Text-independent degeneracy first (all-zero / non-finite), then the
    text-dependent exact hash-fallback match, which only the ~8% well-formed
    fallbacks need. Detection is exact rather than heuristic: measured 0 false
    positives over 3,000 live BGE vectors and 2,000 random unit vectors.
    """
    from orchestration.repl_memory.embedder import (
        is_degenerate_embedding,
        is_hash_fallback_embedding,
    )
    from orchestration.repl_memory.parallel_embedder import (
        is_parallel_hash_fallback_embedding,
    )

    reason = is_degenerate_embedding(embedding)
    if reason is not None:
        return reason
    try:
        from orchestration.repl_memory.memory_record import record_from_legacy_context

        text = record_from_legacy_context(context).embedding_text() if isinstance(context, dict) else ""
    except Exception:  # never let the guard itself break a write
        return None
    if text and is_hash_fallback_embedding(text, embedding):
        return "hash_fallback"
    if text and is_parallel_hash_fallback_embedding(text, embedding):
        return "parallel_hash_fallback"
    return None


class _ClosingSQLiteConnection(sqlite3.Connection):
    """Connection wrapper that closes at context-manager exit."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> bool | None:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


@dataclass
class MemoryEntry:
    """A single episodic memory entry."""

    id: str
    embedding: Optional[np.ndarray]  # Task embedding vector (may be None if not loaded)
    action: str  # Routing decision, escalation action, or exploration code
    action_type: str  # "routing", "escalation", or "exploration"
    context: Dict[str, Any]  # Original task context (task_type, objective, etc.)
    outcome: Optional[str] = None  # "success", "failure", or None if pending
    q_value: float = 0.5  # Initial Q-value (neutral)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    update_count: int = 0  # Number of Q-value updates
    similarity_score: float = 0.0  # Similarity score from retrieval (set by retrieve methods)
    model_id: Optional[str] = None  # Model that produced this memory (for warm-start)
    # Trinity tri-role axis (TR-2 of tri-role-coordinator-architecture.md).
    # NULL on legacy rows; readers should pass through normalise_role() to coerce
    # to a valid {"thinker","worker","verifier"} string when consumed.
    assigned_role: Optional[str] = None
    # Orchestration sub-decision axis (intake-548 5-class taxonomy; see
    # src/classifiers/subdecision_taxonomy.py). One of
    # {"spawn","delegate","communicate","aggregate","stop"} or NULL. NULL means
    # "this event is not a sub-decision" — the polarity is opposite to
    # `assigned_role` (where NULL is treated as the default WORKER role).
    sub_decision: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage (embedding stored separately)."""
        return {
            "id": self.id,
            "action": self.action,
            "action_type": self.action_type,
            "context": self.context,
            "outcome": self.outcome,
            "q_value": self.q_value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "update_count": self.update_count,
            "model_id": self.model_id,
            "assigned_role": self.assigned_role,
            "sub_decision": self.sub_decision,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], embedding: np.ndarray) -> MemoryEntry:
        """Deserialize from storage."""
        return cls(
            id=data["id"],
            embedding=embedding,
            action=data["action"],
            action_type=data["action_type"],
            context=data["context"],
            outcome=data.get("outcome"),
            q_value=data["q_value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            update_count=data.get("update_count", 0),
            model_id=data.get("model_id"),
            assigned_role=data.get("assigned_role"),
            sub_decision=data.get("sub_decision"),
        )


class EpisodicStore:
    """
    SQLite-backed episodic memory store with FAISS or numpy embeddings.

    Memory layout:
    - SQLite: Metadata (action, context, q_value, timestamps)
    - FAISS/Numpy: Embeddings (FAISS default for O(log n) search)

    Supports:
    - Store new memories
    - Retrieve by embedding similarity
    - Update Q-values
    - Query by action type

    Backend selection:
    - use_faiss=True (default): FAISS IndexFlatIP with L2 normalization
    - use_faiss=False: Legacy NumPy mmap (O(n) search, for migration)
    """

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        embeddings_path: Optional[Path] = None,
        embedding_dim: int = 1024,  # BGE-large-en-v1.5 embedding dim
        use_faiss: bool = True,
        flush_interval: float = 10.0,  # Write-behind flush interval (seconds)
    ):
        self.db_path = Path(db_path)
        self.embedding_dim = embedding_dim
        self.use_faiss = use_faiss

        # Write-behind state
        self._dirty = False
        self._flush_interval = flush_interval
        self._flush_task: Optional[asyncio.Task] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        # For FAISS, db_path is a directory containing both SQLite and FAISS files
        # For NumPy, we keep backward compatibility with separate paths
        if use_faiss:
            self.storage_dir = self.db_path
            self.sqlite_path = self.storage_dir / "episodic.db"
            self._faiss_lock_path = self.storage_dir / ".episodic_faiss.lock"
        else:
            self.storage_dir = self.db_path.parent if self.db_path.suffix == ".db" else self.db_path
            self.sqlite_path = self.db_path if self.db_path.suffix == ".db" else self.db_path / "episodic.db"
            self.embeddings_path = embeddings_path or DEFAULT_EMBEDDINGS_PATH
            self._faiss_lock_path = None

        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        # Initialize embedding store (FAISS or NumPy)
        self._init_embedding_store()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    embedding_idx INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    context TEXT NOT NULL,
                    outcome TEXT,
                    q_value REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    update_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_type ON memories(action_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_q_value ON memories(q_value DESC)
            """)
            # Additional indexes for performance optimization
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_outcome ON memories(outcome)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_outcome ON memories(action_type, outcome)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type_q ON memories(action_type, q_value DESC)
            """)
            # model_id column for warm-start protocol (backward-compatible, default NULL)
            try:
                conn.execute("ALTER TABLE memories ADD COLUMN model_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            # assigned_role column for Trinity tri-role axis (TR-2.2 of
            # tri-role-coordinator-architecture.md). Per-call role one of
            # {"thinker","worker","verifier"}; NULL on legacy rows is treated
            # as "worker" by readers (see normalise_role in role_taxonomy).
            try:
                conn.execute("ALTER TABLE memories ADD COLUMN assigned_role TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assigned_role ON memories(assigned_role)"
                )
            except sqlite3.OperationalError:
                pass
            # sub_decision column for orchestration-trace 5-sub-decision axis
            # (intake-548; see src/classifiers/subdecision_taxonomy.py). One of
            # {"spawn","delegate","communicate","aggregate","stop"} or NULL.
            # NULL means "not a sub-decision" — not a default value, just absent.
            try:
                conn.execute("ALTER TABLE memories ADD COLUMN sub_decision TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sub_decision ON memories(sub_decision)"
                )
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def _init_embedding_store(self) -> None:
        """Initialize FAISS or NumPy embedding store."""
        if self.use_faiss:
            from .faiss_store import FAISSEmbeddingStore
            self._embedding_store: Union[FAISSEmbeddingStore, NumpyEmbeddingStore] = (
                FAISSEmbeddingStore(path=self.storage_dir, dim=self.embedding_dim)
            )
            logger.info("Initialized FAISS embedding store at %s", self.storage_dir)
        else:
            from .faiss_store import NumpyEmbeddingStore
            self._embedding_store = NumpyEmbeddingStore(
                path=self.storage_dir, dim=self.embedding_dim
            )
            logger.info("Initialized NumPy embedding store at %s", self.storage_dir)

    # Legacy compatibility properties for NumPy backend
    @property
    def _embeddings(self) -> np.ndarray:
        """Legacy access to embeddings array (NumPy backend only)."""
        if hasattr(self._embedding_store, "_embeddings"):
            return self._embedding_store._embeddings
        raise AttributeError("FAISS backend does not expose raw embeddings array")

    @property
    def _next_idx(self) -> int:
        """Legacy access to next index (NumPy backend only)."""
        return self._embedding_store.count

    def store(
        self,
        embedding: np.ndarray,
        action: str,
        action_type: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None,
        initial_q: float = 0.5,
        model_id: Optional[str] = None,
        assigned_role: Optional[str] = None,
        sub_decision: Optional[str] = None,
    ) -> str:
        """
        Store a new memory entry.

        Args:
            embedding: Task embedding vector
            action: The action taken (routing, escalation decision, or exploration code)
            action_type: "routing", "escalation", or "exploration"
            context: Original task context
            outcome: Optional immediate outcome
            initial_q: Initial Q-value
            model_id: Optional model identifier for warm-start tracking
            assigned_role: Optional Trinity tri-role {"thinker","worker","verifier"}.
                Default None preserves legacy semantics (NULL → reader treats as
                "worker"). Pass via normalise_role() at call sites where the
                source string may be untrusted.
            sub_decision: Optional orchestration sub-decision label, one of
                {"spawn","delegate","communicate","aggregate","stop"}. Default
                None means "this event is not a sub-decision" — opposite
                polarity to assigned_role. Pass via normalise_subdecision() at
                call sites where the source string may be untrusted.

        Returns:
            Memory ID
        """
        if not is_indexed_action_type(action_type):
            raise ValueError("action_type must be a nonempty string for indexed episodic memory")

        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Contract chokepoint. Every write site is expected to build its context
        # through memory_record.build_memory_record(), which stamps
        # record_version. A context arriving without it means a write site has
        # drifted back to a hand-rolled dict — the condition that produced four
        # incompatible record shapes and put 27,123 telemetry rows into the
        # semantic index. Warn rather than raise so an unknown caller degrades
        # instead of failing, but make the drift visible.
        if isinstance(context, dict) and "record_version" not in context:
            logger.warning(
                "Episodic write with a non-contract context (no record_version); "
                "action_type=%s keys=%s. Build it via memory_record.build_memory_record().",
                action_type,
                sorted(context.keys())[:8],
            )

        # Embedding chokepoint. `use_fallback` defaults to True in both
        # EmbeddingConfig and EmbedderPoolConfig, and every live site builds a
        # bare TaskEmbedder() — so an embedder outage does NOT fail a write, it
        # silently substitutes a SHA-256 pseudo-vector. Measured over 5,000 real
        # task texts, that fallback yields 89.0% all-zero (float32 norm
        # overflows to inf, and v/inf == 0), 2.8% NaN-bearing (permanently
        # unretrievable — FAISS scores the row -inf), and 8.1% well-formed but
        # semantically meaningless.
        #
        # This is the corruption mode the 2026-07-05 incident taught us to fear:
        # such rows pass index/id_map sync and the embedding_idx round-trip, so
        # only a semantic re-embed catches the well-formed ones — and that check
        # needs the very embedders whose absence produced them. Refuse at the
        # single chokepoint instead of at the ~8 constructor sites, so the
        # guarantee cannot be lost by a new caller.
        #
        # Raising is deliberate: store() already raises FAISSDesyncError, and a
        # write that cannot be embedded is better lost than persisted wrong.
        _degenerate = _embedding_rejection_reason(embedding, context)
        if _degenerate is not None:
            if os.environ.get("EPISODIC_ALLOW_DEGRADED_EMBEDDINGS") == "1":
                logger.error(
                    "Persisting a DEGENERATE embedding (%s) because "
                    "EPISODIC_ALLOW_DEGRADED_EMBEDDINGS=1; this row is not "
                    "semantically retrievable. action_type=%s",
                    _degenerate,
                    action_type,
                )
            else:
                raise DegenerateEmbeddingError(
                    f"refusing to persist a degenerate embedding ({_degenerate}); "
                    "the embedding servers are probably down and TaskEmbedder fell "
                    "back to a SHA-256 pseudo-vector. Fix the embedders, or set "
                    "EPISODIC_ALLOW_DEGRADED_EMBEDDINGS=1 to accept an "
                    "unretrievable row on purpose."
                )

        if self.use_faiss and self._faiss_lock_path is not None:
            with _exclusive_file_lock(self._faiss_lock_path):
                # Multiple API/worker processes can keep EpisodicStore instances
                # open. Reload before assigning the next FAISS index so each
                # writer observes the latest durable id_map, then save before
                # releasing the lock to prevent duplicate embedding_idx rows.
                if hasattr(self._embedding_store, "_load"):
                    self._embedding_store._load()
                embedding_idx = self._embedding_store.add(memory_id, embedding)
                self._embedding_store.save()
                self._insert_memory_row(
                    memory_id=memory_id,
                    embedding_idx=embedding_idx,
                    action=action,
                    action_type=action_type,
                    context=context,
                    outcome=outcome,
                    initial_q=initial_q,
                    now=now,
                    model_id=model_id,
                    assigned_role=assigned_role,
                    sub_decision=sub_decision,
                )
        else:
            # Store embedding in NumPy and persist via write-behind.
            embedding_idx = self._embedding_store.add(memory_id, embedding)
            self._insert_memory_row(
                memory_id=memory_id,
                embedding_idx=embedding_idx,
                action=action,
                action_type=action_type,
                context=context,
                outcome=outcome,
                initial_q=initial_q,
                now=now,
                model_id=model_id,
                assigned_role=assigned_role,
                sub_decision=sub_decision,
            )
            self._dirty = True
            self._schedule_flush()

        return memory_id

    def _insert_memory_row(
        self,
        *,
        memory_id: str,
        embedding_idx: int,
        action: str,
        action_type: str,
        context: Dict[str, Any],
        outcome: Optional[str],
        initial_q: float,
        now: str,
        model_id: Optional[str],
        assigned_role: Optional[str],
        sub_decision: Optional[str],
    ) -> None:
        """Persist SQLite metadata for an already-added embedding."""
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            conn.execute(
                """
                INSERT INTO memories
                (id, embedding_idx, action, action_type, context, outcome, q_value, created_at, updated_at, update_count, model_id, assigned_role, sub_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory_id,
                    embedding_idx,
                    action,
                    action_type,
                    json.dumps(context),
                    outcome,
                    initial_q,
                    now,
                    now,
                    # Seed update_count EXPLICITLY rather than relying on the
                    # column default. The CREATE TABLE above declares
                    # `update_count INTEGER DEFAULT 0`, but the LIVE table does
                    # not have it — a migration recreated the table (note the
                    # quoted `CREATE TABLE "memories"` and the sibling
                    # _q_consolidation_* tables) and dropped the column
                    # defaults, leaving `update_count INT` with an implicit NULL.
                    # The UPDATE then does `update_count + 1`, and NULL + 1 is
                    # NULL in SQLite, so those rows stayed NULL forever however
                    # many times they were updated. Not cosmetic: it feeds a LIVE
                    # gate — should_use_learned() (retriever.py:392-396) treats
                    # NULL as "never observed" and declines the learned value.
                    # 22,949 of 54,960 rows were stuck this way. Passing 0
                    # explicitly is correct regardless of the table definition.
                    0,
                    model_id,
                    assigned_role,
                    sub_decision,
                ),
            )
            conn.commit()

    def store_immediate(
        self,
        embedding: np.ndarray,
        action: str,
        action_type: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None,
        initial_q: float = 0.5,
        model_id: Optional[str] = None,
        assigned_role: Optional[str] = None,
        sub_decision: Optional[str] = None,
    ) -> str:
        """
        Store a new memory with immediate FAISS persistence (ACID-critical).

        Use this for critical memories that must survive a crash.
        Normal store() uses write-behind for better throughput.

        Args:
            embedding: Task embedding vector
            action: The action taken
            action_type: "routing", "escalation", or "exploration"
            context: Original task context
            outcome: Optional immediate outcome
            initial_q: Initial Q-value
            model_id: Optional model identifier for warm-start tracking
            assigned_role: Optional Trinity tri-role; see store() for semantics.
            sub_decision: Optional orchestration sub-decision; see store().

        Returns:
            Memory ID
        """
        memory_id = self.store(
            embedding,
            action,
            action_type,
            context,
            outcome,
            initial_q,
            model_id=model_id,
            assigned_role=assigned_role,
            sub_decision=sub_decision,
        )
        self.flush()  # Synchronous flush
        return memory_id

    def _schedule_flush(self) -> None:
        """Schedule a write-behind flush if not already scheduled."""
        try:
            loop = asyncio.get_running_loop()
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = loop.create_task(self._flush_loop())
        except RuntimeError:
            # No running event loop - we're in sync context
            # Flush will happen on close() or store_immediate()
            pass

    def _refresh_embedding_store_if_changed(self, *, force: bool = False) -> bool:
        """Reload persisted FAISS files written by another process."""
        if not self.use_faiss:
            return False
        reload_if_changed = getattr(self._embedding_store, "reload_if_changed", None)
        if not callable(reload_if_changed):
            return False
        if self._faiss_lock_path is not None:
            with _exclusive_file_lock(self._faiss_lock_path):
                return bool(reload_if_changed(force=force))
        return bool(reload_if_changed(force=force))

    async def _flush_loop(self) -> None:
        """Background flush loop (10s interval)."""
        while True:
            await asyncio.sleep(self._flush_interval)
            if self._dirty:
                await asyncio.to_thread(self.flush)
                logger.debug("Write-behind flush completed")

    def flush(self) -> None:
        """Synchronous flush of embedding store to disk."""
        if self.use_faiss:
            if self._dirty:
                logger.warning(
                    "Discarding dirty FAISS-backed EpisodicStore flush state after "
                    "reloading the persisted mirror; FAISS writes should save "
                    "synchronously in store()."
                )
                self._refresh_embedding_store_if_changed(force=True)
                self._dirty = False
            else:
                self._refresh_embedding_store_if_changed()
            return
        if self._dirty:
            self._embedding_store.save()
            self._dirty = False
            logger.debug("Synchronous flush completed")

    def close(self) -> None:
        """Close the store, flushing any pending writes."""
        # Cancel flush task if running
        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()
            self._flush_task = None

        # Synchronous flush on shutdown
        self.flush()

    def retrieve_by_similarity(
        self,
        query_embedding: np.ndarray,
        k: int = 20,
        action_type: Optional[str] = None,
        min_q_value: float = 0.0,
    ) -> List[MemoryEntry]:
        """
        Retrieve memories by embedding similarity (two-phase retrieval).

        Phase 1: FAISS/NumPy search for top candidates by embedding similarity
        Phase 2: Filter and enrich with SQLite metadata

        Args:
            query_embedding: Query embedding vector
            k: Number of candidates to retrieve
            action_type: Optional filter by action type
            min_q_value: Minimum Q-value threshold

        Returns:
            List of MemoryEntry sorted by similarity (descending)
        """
        self._refresh_embedding_store_if_changed()

        # Phase 1: Embedding search (FAISS or NumPy)
        # Over-fetch to account for filtering
        candidates = self._embedding_store.search(query_embedding, k=k * 2)

        if not candidates:
            return []

        # Build score lookup
        score_map = {memory_id: score for memory_id, score in candidates}
        memory_ids = list(score_map.keys())

        # Phase 2: Fetch and filter metadata from SQLite
        placeholders = ",".join("?" * len(memory_ids))
        query = f"""
            SELECT id, embedding_idx, action, action_type, context, outcome, q_value,
                   created_at, updated_at, update_count, model_id, assigned_role, sub_decision
            FROM memories
            WHERE id IN ({placeholders}) AND {indexed_memory_predicate()}
        """
        params: list = list(memory_ids)

        # Add filters
        filters = []
        if action_type:
            filters.append("action_type = ?")
            params.append(action_type)
        if min_q_value > 0:
            filters.append("q_value >= ?")
            params.append(min_q_value)

        if filters:
            query += " AND " + " AND ".join(filters)

        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return []

        # Combine with similarity scores and build MemoryEntry objects
        results = []
        for row in rows:
            memory_id = row[0]
            embedding_idx = row[1]

            # Get embedding if available (None for FAISS to save memory)
            embedding = None
            if hasattr(self._embedding_store, "get_embedding"):
                embedding = self._embedding_store.get_embedding(embedding_idx)

            entry = MemoryEntry(
                id=memory_id,
                embedding=embedding,
                action=row[2],
                action_type=row[3],
                context=json.loads(row[4]),
                outcome=row[5],
                q_value=row[6],
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
                update_count=row[9],
                similarity_score=score_map.get(memory_id, 0.0),
                model_id=row[10] if len(row) > 10 else None,
                assigned_role=row[11] if len(row) > 11 else None,
                sub_decision=row[12] if len(row) > 12 else None,
            )
            results.append(entry)

        # Sort by similarity score and return top k
        results.sort(key=lambda m: m.similarity_score, reverse=True)
        return results[:k]

    def update_q_value(
        self,
        memory_id: str,
        reward: float,
        learning_rate: float = 0.1,
        temporal_decay_rate: float | None = None,
    ) -> float:
        """
        Update Q-value for a memory using TD-learning style update.

        If temporal_decay_rate is provided, the stored Q-value is first decayed
        toward neutral (0.5) based on elapsed days since last update:

            Q_decayed = 0.5 + (Q_old - 0.5) * decay_rate ^ days_elapsed

        Then the standard TD update is applied:

            Q(m) ← Q_decayed + α(r - Q_decayed)

        Args:
            memory_id: Memory ID to update
            reward: Observed reward (0-1 scale)
            learning_rate: Learning rate α
            temporal_decay_rate: Optional decay rate per day (e.g. 0.99).
                None disables decay. Applied before TD update.

        Returns:
            New Q-value
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            # Get current Q-value and updated_at for decay calculation
            row = conn.execute(
                "SELECT q_value, update_count, updated_at FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()

            if not row:
                raise ValueError(f"Memory {memory_id} not found")

            old_q, _prev_update_count, updated_at_str = row

            # Elapsed days since last update, for temporal decay toward neutral.
            days_elapsed = 0.0
            if temporal_decay_rate is not None and updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    days_elapsed = (now - updated_at).total_seconds() / 86400.0
                except (ValueError, TypeError):
                    days_elapsed = 0.0  # Skip decay on unparseable timestamps

            # TD-style update (+ optional decay) via the shared pure helper so the
            # offline consolidation migration reproduces identical math.
            new_q = apply_td_update(
                old_q,
                reward,
                learning_rate,
                days_elapsed=days_elapsed,
                temporal_decay_rate=temporal_decay_rate,
            )

            # Update database.
            #
            # EPD-1 (2026-09-23): `outcome` is re-derived from the updated Q on
            # every update. Live readers treat it as the CURRENT label
            # (state.py exploration gate, builder.py/routing.py prompt context,
            # training extraction, DAR/EP-5 probes); pinning it to the first
            # observation let a row read `Q=0.90 (failure)`. Rows never updated
            # again keep their INSERT label (no backfill here).
            #
            # `update_count` was also broken: the live table lost its column
            # default in a migration, the INSERT relied on that default, and
            # NULL + 1 = NULL kept 22,949 rows permanently unobserved from
            # should_use_learned()'s perspective. Seeded explicitly at insert
            # now; COALESCE here repairs pre-existing NULL rows on next update.
            conn.execute(
                """
                UPDATE memories
                SET q_value = ?, outcome = ?, updated_at = ?,
                    update_count = COALESCE(update_count, 0) + 1
                WHERE id = ?
            """,
                (new_q, outcome_from_q(new_q), now_iso, memory_id),
            )
            conn.commit()

        return new_q

    def merge_row_metadata(
        self,
        memory_id: str,
        assigned_role: Optional[str] = None,
        work: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Fill in `assigned_role` / `context["work"]` on an EXISTING row.

        The find-or-update write path (``ORCHESTRATOR_Q_TD_WRITE=1``,
        ``q_scorer._update_routing_memory``) updates a row's Q-value and returns
        without ever reaching ``store()``, which is the ONLY site that wrote
        ``assigned_role`` and the ``work`` payload. Because the update branch
        fires ~11x more often than create, both fields were effectively never
        populated (0 / 59,337 rows at the 2026-08-03 audit) — the values were
        computed and then dropped on the floor.

        MERGE, never overwrite:

        * ``assigned_role`` is written only when the stored value is NULL/empty.
          An existing classification is a historical record of what the
          classifier said at first observation and is not re-litigated here.
        * ``work`` sub-keys are written only where the stored row has no
          non-empty value for that key. Every other ``context`` key is preserved
          byte-for-byte. A later, richer observation can therefore fill a gap a
          first observation left, but can never blank out captured work.

        `work` must already be sanitized/bounded — pass the output of
        ``memory_record.build_work_payload`` (the single producer). This method
        applies NO sanitization, precisely so the policy is not run twice
        (it is not idempotent, so a double pass would misreport its own
        size/elision provenance).

        Returns True if the row was modified.
        """
        role = (assigned_role or "").strip() or None
        work_in = {
            k: v for k, v in (work or {}).items() if v not in (None, "", [], {})
        }
        if role is None and not work_in:
            return False

        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            row = conn.execute(
                "SELECT context, assigned_role FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
            if not row:
                return False
            context_raw, stored_role = row

            sets: List[str] = []
            params: List[Any] = []

            if role is not None and not (stored_role or "").strip():
                sets.append("assigned_role = ?")
                params.append(role)

            if work_in:
                try:
                    context = json.loads(context_raw) if context_raw else {}
                except (TypeError, ValueError):
                    context = {}
                if not isinstance(context, dict):
                    context = {}
                stored_work = context.get("work")
                if not isinstance(stored_work, dict):
                    stored_work = {}
                merged = dict(stored_work)
                changed = False
                for key, value in work_in.items():
                    if merged.get(key) in (None, "", [], {}):
                        merged[key] = value
                        changed = True
                if changed:
                    context["work"] = merged
                    sets.append("context = ?")
                    params.append(json.dumps(context))

            if not sets:
                return False

            sets.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.append(memory_id)
            conn.execute(
                f"UPDATE memories SET {', '.join(sets)} WHERE id = ?",  # noqa: S608
                params,
            )
            conn.commit()
        return True

    def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory by ID."""
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            row = conn.execute(
                """
                SELECT id, embedding_idx, action, action_type, context, outcome, q_value,
                       created_at, updated_at, update_count, model_id, assigned_role, sub_decision
                FROM memories
                WHERE id = ?
            """,
                (memory_id,),
            ).fetchone()

        if not row:
            return None

        # Get embedding if available
        embedding = None
        embedding_idx = row[1]
        if hasattr(self._embedding_store, "get_embedding"):
            embedding = self._embedding_store.get_embedding(embedding_idx)

        return MemoryEntry(
            id=row[0],
            embedding=embedding,
            action=row[2],
            action_type=row[3],
            context=json.loads(row[4]),
            outcome=row[5],
            q_value=row[6],
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
            update_count=row[9],
            model_id=row[10] if len(row) > 10 else None,
            assigned_role=row[11] if len(row) > 11 else None,
            sub_decision=row[12] if len(row) > 12 else None,
        )

    def get_all_memories(
        self,
        action_type: Optional[str] = None,
        include_embeddings: bool = False,
        min_update_count: int = 0,
    ) -> List[MemoryEntry]:
        """
        Retrieve all memories from the store.

        Used by training pipelines (graph sync, classifier training) that need
        bulk access to the full memory set.

        Args:
            action_type: Optional filter by action type (e.g. "routing").
            include_embeddings: If True, load embeddings from FAISS/NumPy.
                Default False to avoid unnecessary FAISS lookups.
            min_update_count: Minimum update_count filter (for training quality).

        Returns:
            List of MemoryEntry (embedding field is None unless include_embeddings=True).
        """
        query = """
            SELECT id, embedding_idx, action, action_type, context, outcome, q_value,
                   created_at, updated_at, update_count, model_id, assigned_role, sub_decision
            FROM memories
        """
        params: list = []
        filters = []

        if action_type:
            filters.append("action_type = ?")
            params.append(action_type)
        if min_update_count > 0:
            filters.append("update_count >= ?")
            params.append(min_update_count)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY created_at ASC"

        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            embedding = None
            embedding_idx = row[1]
            if include_embeddings and hasattr(self._embedding_store, "get_embedding"):
                embedding = self._embedding_store.get_embedding(embedding_idx)

            results.append(
                MemoryEntry(
                    id=row[0],
                    embedding=embedding,
                    action=row[2],
                    action_type=row[3],
                    context=json.loads(row[4]),
                    outcome=row[5],
                    q_value=row[6],
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8]),
                    update_count=row[9],
                    model_id=row[10] if len(row) > 10 else None,
                    assigned_role=row[11] if len(row) > 11 else None,
                    sub_decision=row[12] if len(row) > 12 else None,
                )
            )

        return results

    def count(self, action_type: Optional[str] = None) -> int:
        """Count memories, optionally filtered by action type."""
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            if action_type:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE action_type = ?",
                    (action_type,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0] if row else 0

    def count_by_combo(
        self, action: str, task_type: Optional[str] = None,
    ) -> int:
        """Count memories matching action and optional task_type in context.

        Uses SQLite json_extract() to filter by task_type stored in the
        JSON context column. Requires SQLite 3.38+ (2022).

        Args:
            action: Action string to match (e.g. "frontdoor:direct").
            task_type: Optional task_type value in context JSON.

        Returns:
            Count of matching memories.
        """
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            if task_type:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE action = ? "
                    "AND json_extract(context, '$.task_type') = ?",
                    (action, task_type),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE action = ?",
                    (action,),
                ).fetchone()
        return row[0] if row else 0

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            by_type = conn.execute(
                """
                SELECT action_type, COUNT(*), AVG(q_value)
                FROM memories
                GROUP BY action_type
            """
            ).fetchall()
            avg_q = conn.execute("SELECT AVG(q_value) FROM memories").fetchone()[0]

        return {
            "total_memories": total,
            "by_action_type": {row[0]: {"count": row[1], "avg_q": row[2]} for row in by_type},
            "overall_avg_q": avg_q or 0.0,
            "embeddings_count": self._embedding_store.count,
            "backend": "faiss" if self.use_faiss else "numpy",
        }

    def get_q_outliers(
        self,
        low_threshold: float = 0.3,
        high_threshold: float = 0.8,
        limit: int = 1000,
    ) -> List[MemoryEntry]:
        """
        Get memories with extreme Q-values (outliers) for graph linkage.

        Returns memories where Q < low_threshold (failures) or Q > high_threshold (successes).
        These are the most informative memories for graph seeding.

        Args:
            low_threshold: Q-values below this are considered failures (default 0.3)
            high_threshold: Q-values above this are considered successes (default 0.8)
            limit: Maximum number of memories to return

        Returns:
            List of MemoryEntry sorted by Q-value (lowest first, then highest)
        """
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            rows = conn.execute(
                """
                SELECT id, embedding_idx, action, action_type, context, outcome, q_value,
                       created_at, updated_at, update_count, model_id, assigned_role, sub_decision
                FROM memories
                WHERE q_value < ? OR q_value > ?
                ORDER BY
                    CASE WHEN q_value < ? THEN 0 ELSE 1 END,  -- Failures first
                    ABS(q_value - 0.5) DESC  -- Most extreme first
                LIMIT ?
                """,
                (low_threshold, high_threshold, low_threshold, limit),
            ).fetchall()

        results = []
        for row in rows:
            embedding = None
            embedding_idx = row[1]
            if hasattr(self._embedding_store, "get_embedding"):
                embedding = self._embedding_store.get_embedding(embedding_idx)

            results.append(
                MemoryEntry(
                    id=row[0],
                    embedding=embedding,
                    action=row[2],
                    action_type=row[3],
                    context=json.loads(row[4]),
                    outcome=row[5],
                    q_value=row[6],
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8]),
                    update_count=row[9],
                    model_id=row[10] if len(row) > 10 else None,
                    assigned_role=row[11] if len(row) > 11 else None,
                    sub_decision=row[12] if len(row) > 12 else None,
                )
            )

        return results

    def get_action_q_summary(self) -> Dict[str, tuple]:
        """Get Q-value statistics grouped by action.

        Returns:
            Dict mapping action -> (count, mean_q, std_q).
            Useful for understanding learned routing preferences.
        """
        with sqlite3.connect(self.sqlite_path, factory=_ClosingSQLiteConnection) as conn:
            rows = conn.execute(
                """
                SELECT action,
                       COUNT(*) as n,
                       AVG(q_value) as mean_q,
                       -- SQLite doesn't have STDDEV, compute manually
                       CASE
                           WHEN COUNT(*) <= 1 THEN 0.0
                           ELSE SQRT(
                               SUM((q_value - sub.avg) * (q_value - sub.avg)) / (COUNT(*) - 1)
                           )
                       END as std_q
                FROM memories
                JOIN (SELECT action as a, AVG(q_value) as avg FROM memories GROUP BY action) sub
                  ON memories.action = sub.a
                GROUP BY action
                ORDER BY mean_q DESC
                """,
            ).fetchall()

        return {
            row[0]: (row[1], row[2], row[3])
            for row in rows
        }


# Symptom patterns for failure detection (raw strings kept for readability)
_SYMPTOM_PATTERN_STRINGS: Dict[str, str] = {
    "timeout": r"timeout|timed out|deadline exceeded",
    "0% acceptance": r"0%.*accept|acceptance.*0|acceptance rate.*0",
    "SIGSEGV": r"sigsegv|segmentation fault|signal 11",
    "OOM": r"out of memory|oom|memory exhausted|cannot allocate",
    "BOS mismatch": r"bos.*mismatch|token.*mismatch|bos_token",
    "SWA incompatibility": r"swa|sliding window|kv_cache.*slot",
    "vocab mismatch": r"vocab.*mismatch|vocabulary.*size",
    "empty output": r"empty output|no output|output.*empty",
    "JSON parse error": r"json.*parse|invalid json|json.*error",
    "connection refused": r"connection refused|cannot connect|econnrefused",
}

# Pre-compiled patterns (compiled once at module load, not per call)
SYMPTOM_PATTERNS: Dict[str, re.Pattern] = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in _SYMPTOM_PATTERN_STRINGS.items()
}


def extract_symptoms(context: Dict[str, Any], outcome: str) -> List[str]:
    """
    Extract failure symptoms from context and outcome.

    Uses pre-compiled regex patterns to identify known failure modes.

    Args:
        context: Task context dictionary
        outcome: Outcome string (may contain error details)

    Returns:
        List of detected symptom names
    """
    symptoms = []
    error_text = str(context.get("error", "")) + str(outcome)
    error_text = error_text.lower()

    for symptom, pattern in SYMPTOM_PATTERNS.items():
        if pattern.search(error_text):
            symptoms.append(symptom)

    return symptoms or ["unknown"]


class GraphEnhancedStore:
    """
    Wrapper around EpisodicStore with graph integration.

    Provides async graph updates after storing memories:
    - FailureGraph: Records failures with symptoms
    - HypothesisGraph: Updates action-task confidence

    Graph updates happen asynchronously after the response is returned
    to avoid impacting latency.
    """

    def __init__(
        self,
        episodic_store: EpisodicStore,
        failure_graph: Optional["FailureGraph"] = None,
        hypothesis_graph: Optional["HypothesisGraph"] = None,
    ):
        self.store = episodic_store
        self.failure_graph = failure_graph
        self.hypothesis_graph = hypothesis_graph
        self._pending_updates: List[asyncio.Task] = []

    def store_with_graphs(
        self,
        embedding: np.ndarray,
        action: str,
        action_type: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None,
        initial_q: float = 0.5,
        task_type: Optional[str] = None,
        model_id: Optional[str] = None,
        assigned_role: Optional[str] = None,
        sub_decision: Optional[str] = None,
    ) -> str:
        """
        Store a memory and schedule async graph updates.

        Args:
            embedding: Task embedding vector
            action: The action taken
            action_type: "routing", "escalation", or "exploration"
            context: Original task context
            outcome: Optional outcome ("success", "failure", or error details)
            initial_q: Initial Q-value
            task_type: Task type for hypothesis tracking
            model_id: Optional model identifier (warm-start)
            assigned_role: Optional Trinity tri-role; see EpisodicStore.store
            sub_decision: Optional orchestration sub-decision; see EpisodicStore.store

        Returns:
            Memory ID
        """
        # Store in episodic memory (synchronous)
        memory_id = self.store.store(
            embedding=embedding,
            action=action,
            action_type=action_type,
            context=context,
            outcome=outcome,
            initial_q=initial_q,
            model_id=model_id,
            assigned_role=assigned_role,
            sub_decision=sub_decision,
        )

        # Schedule async graph updates
        if outcome is not None:
            try:
                # Try to get or create an event loop
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(
                        self._update_graphs(memory_id, action, action_type, context, outcome, task_type)
                    )
                    self._pending_updates.append(task)
                except RuntimeError:
                    # No running loop - run synchronously in a new loop
                    asyncio.run(
                        self._update_graphs(memory_id, action, action_type, context, outcome, task_type)
                    )
            except Exception as e:
                logger.warning("Failed to schedule graph updates: %s", e)

        return memory_id

    async def _update_graphs(
        self,
        memory_id: str,
        action: str,
        action_type: str,
        context: Dict[str, Any],
        outcome: str,
        task_type: Optional[str],
    ) -> None:
        """
        Update failure and hypothesis graphs asynchronously.

        Args:
            memory_id: Memory ID to link
            action: The action taken
            action_type: Action type
            context: Task context
            outcome: Outcome string
            task_type: Task type for hypothesis
        """
        is_failure = outcome.lower() in ("failure", "error") or "error" in outcome.lower()

        # Update failure graph
        if self.failure_graph is not None and is_failure:
            try:
                symptoms = extract_symptoms(context, outcome)
                self.failure_graph.record_failure(
                    memory_id=memory_id,
                    symptoms=symptoms,
                    description=f"{action} failed with: {outcome[:100]}",
                    severity=3,  # Default medium severity
                )
                logger.debug("Recorded failure with symptoms: %s", symptoms)
            except Exception as e:
                logger.warning("Failed to update failure graph: %s", e)

        # Update hypothesis graph (success or failure)
        if self.hypothesis_graph is not None and task_type:
            try:
                # Get or create hypothesis for action-task combination
                hypothesis_id = self.hypothesis_graph.get_or_create_hypothesis(
                    action=action,
                    task_type=task_type,
                    memory_id=memory_id,
                )
                # Add evidence
                evidence_outcome = "success" if not is_failure else "failure"
                self.hypothesis_graph.add_evidence(
                    hypothesis_id=hypothesis_id,
                    outcome=evidence_outcome,
                    source=memory_id,
                )
                logger.debug("Updated hypothesis confidence for %s|%s", action, task_type)
            except Exception as e:
                logger.warning("Failed to update hypothesis graph: %s", e)

    def record_mitigation(
        self,
        failure_memory_id: str,
        action: str,
        worked: bool,
    ) -> Optional[str]:
        """
        Record a mitigation attempt for a prior failure.

        Args:
            failure_memory_id: ID of the failure memory
            action: The mitigation action taken
            worked: Whether the mitigation resolved the failure

        Returns:
            Mitigation ID or None if failure graph unavailable
        """
        if self.failure_graph is None:
            return None

        # Find the failure associated with this memory
        # (The failure graph links memories to failures)
        try:
            # Get symptoms from the failed memory to find the failure
            memory = self.store.get_by_id(failure_memory_id)
            if memory and memory.outcome:
                symptoms = extract_symptoms(memory.context, memory.outcome)
                failures = self.failure_graph.find_matching_failures(symptoms)
                if failures:
                    return self.failure_graph.record_mitigation(
                        failure_id=failures[0].id,
                        action=action,
                        worked=worked,
                    )
        except Exception as e:
            logger.warning("Failed to record mitigation: %s", e)

        return None

    async def flush_pending_updates(self) -> int:
        """
        Wait for all pending graph updates to complete.

        Returns:
            Number of updates completed
        """
        if not self._pending_updates:
            return 0

        completed = 0
        for task in self._pending_updates:
            try:
                await task
                completed += 1
            except Exception as e:
                logger.warning("Graph update failed: %s", e)

        self._pending_updates.clear()
        return completed

    # Delegate core methods to underlying store
    def retrieve_by_similarity(self, *args, **kwargs):
        return self.store.retrieve_by_similarity(*args, **kwargs)

    def update_q_value(self, *args, **kwargs):
        return self.store.update_q_value(*args, **kwargs)

    def merge_row_metadata(self, *args, **kwargs):
        return self.store.merge_row_metadata(*args, **kwargs)

    def get_by_id(self, memory_id: str):
        return self.store.get_by_id(memory_id)

    def get_all_memories(self, *args, **kwargs):
        return self.store.get_all_memories(*args, **kwargs)

    def count(self, action_type: Optional[str] = None) -> int:
        return self.store.count(action_type)

    def count_by_combo(self, action: str, task_type: Optional[str] = None) -> int:
        return self.store.count_by_combo(action, task_type)

    def get_stats(self) -> Dict[str, Any]:
        stats = self.store.get_stats()
        # Add graph stats if available
        if self.failure_graph:
            stats["failure_graph"] = self.failure_graph.get_stats()
        if self.hypothesis_graph:
            stats["hypothesis_graph"] = self.hypothesis_graph.get_stats()
        return stats

"""
FAISSEmbeddingStore: FAISS-backed embedding storage with O(log n) search.

Replaces NumPy mmap for embedding storage while keeping SQLite for metadata.
Provides ~70x faster retrieval at scale (500K entries: 70ms -> ~1ms).
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Protocol

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)

# Default paths (on RAID array per CLAUDE.md requirements)
DEFAULT_FAISS_PATH = _REPO_ROOT / "orchestration/repl_memory/sessions"


class FAISSDesyncError(RuntimeError):
    """Raised when the FAISS index and id_map have diverged.

    Fail-closed guard: writing into a desynced store silently mis-assigns every
    subsequent embedding position and persists the error into
    ``memories.embedding_idx``, which is what corrupted this store from
    2026-07-05 onward.
    """


class StaleFAISSSaveError(RuntimeError):
    """Raised when a dirty FAISS store would overwrite newer disk files."""


class DegenerateVectorError(ValueError):
    """Raised when a vector that can never be retrieved would enter the index.

    An all-zero vector L2-normalizes to zero and inner-products to 0.0 with
    everything; a NaN/Inf vector scores -inf. Either way the row exists in the
    id_map/SQLite with a valid position and is permanently unretrievable — the
    signature of an embedder outage, where TaskEmbedder's default hash fallback
    yields 89.0% all-zero and 2.8% NaN vectors (measured 2026-07-28 over 5,000
    real task texts). This guard sits in add() because add() is the single
    function every vector must pass to reach ANY index — episodic, skill, or
    strategy — so no store can lose the guarantee independently.
    Override for a deliberate degraded write: EPISODIC_ALLOW_DEGRADED_EMBEDDINGS=1.
    """


class EmbeddingStoreProtocol(Protocol):
    """Protocol for embedding storage backends (FAISS, NumPy, ChromaDB)."""

    def add(self, memory_id: str, embedding: np.ndarray) -> int:
        """Add embedding, return index."""
        ...

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        """Search, return [(memory_id, score), ...]."""
        ...

    def save(self) -> None:
        """Persist to disk."""
        ...

    @property
    def count(self) -> int:
        """Number of stored embeddings."""
        ...


class FAISSEmbeddingStore:
    """
    FAISS-backed embedding storage with persistence.

    Uses IndexFlatIP (inner product) with L2 normalization for cosine similarity.
    Provides O(log n) search complexity vs O(n) for brute-force NumPy.

    Storage format:
        - embeddings.faiss: FAISS index file
        - id_map.npy: memory_id -> faiss_idx mapping array

    Performance expectations:
        - 5K entries: ~0.5ms
        - 50K entries: ~1ms
        - 500K entries: ~2ms
        - 1M entries: ~3ms
    """

    def __init__(
        self,
        path: Path = DEFAULT_FAISS_PATH,
        dim: int = 1024,  # BGE-large embedding dimension
        index_filename: str = "embeddings.faiss",
        id_map_filename: str = "id_map.npy",
    ):
        """
        Initialize FAISS embedding store.

        Args:
            path: Directory for persistence
            dim: Embedding dimension (must match embedder output)
            index_filename: Name of the FAISS index file
            id_map_filename: Name of the id_map NumPy file
        """
        # Lazy import to avoid loading FAISS at module level
        try:
            import faiss
        except ImportError as e:
            raise ImportError(
                "faiss-cpu not installed. Run: pip install faiss-cpu>=1.7.4"
            ) from e

        self._faiss = faiss
        self.path = Path(path)
        self.dim = dim
        self.index_path = self.path / index_filename
        self.id_map_path = self.path / id_map_filename
        self._dirty = False
        #: index.ntotal - len(id_map). Non-zero means the pair diverged; >0 is
        #: the unrecoverable direction and blocks writes (see add()).
        self._desync = 0
        self._disk_signature: tuple[tuple[int, int] | None, tuple[int, int] | None] = (
            None,
            None,
        )

        # Ensure directory exists
        self.path.mkdir(parents=True, exist_ok=True)

        # Reclaim tmp files stranded by SIGKILLed saves before doing anything
        # else. Never fatal: a janitor must not stop the store from opening.
        try:
            self.sweep_orphan_tmp_files()
        except Exception:  # noqa: BLE001 — best-effort housekeeping
            pass

        # Load existing or create new
        if self.index_path.exists() and self.id_map_path.exists():
            self._load()
        else:
            self._create_new()

    def _open_file_inodes(self) -> set[tuple[int, int]]:
        """(st_dev, st_ino) of every file currently held open on this host.

        Walks /proc/*/fd because `fuser` is not installed in the devcontainer.
        Identity is by INODE, not path: a tmp being written right now may
        already have been renamed, and a stale path could be reused.
        Processes we cannot read (foreign uid, or exited mid-walk) are skipped
        — they simply do not contribute to the exclusion set.
        """
        open_inodes: set[tuple[int, int]] = set()
        proc = Path("/proc")
        for pid_dir in proc.glob("[0-9]*"):
            fd_dir = pid_dir / "fd"
            try:
                fds = list(fd_dir.iterdir())
            except OSError:
                continue
            for fd in fds:
                try:
                    st = fd.stat()  # follows the symlink to the target
                except OSError:
                    continue
                open_inodes.add((st.st_dev, st.st_ino))
        return open_inodes

    def sweep_orphan_tmp_files(self, max_age_s: float = 24 * 3600) -> list[Path]:
        """Unlink atomic-save tmp files stranded by a killed process.

        `_save` writes tmp -> verify -> replace with cleanup in a `finally`,
        but **`finally` does not run on SIGKILL** — and this host runs earlyoom
        (which SIGKILLs by design) plus hard session terminations. Each
        interrupted save strands a ~2 GB tmp; 37 GB across 67 files had to be
        reclaimed by hand on 2026-07-21, and the cause is structural so they
        re-accumulate.

        Two conditions, both required, and the second is the important one:
          (a) older than `max_age_s`;
          (b) not currently held open by ANY process.
        During the 2026-07-21 cleanup a tmp was observed live mid-save and its
        save completed normally — deleting on age alone would have corrupted
        an in-flight save of a store that can take minutes to write.

        Returns the paths actually unlinked.
        """
        now = time.time()
        candidates = [
            p
            for stem in (self.index_path.name, self.id_map_path.name)
            for p in self.path.glob(f".{stem}.*.tmp*")
            if p.is_file()
        ]
        if not candidates:
            return []

        open_inodes = self._open_file_inodes()
        removed: list[Path] = []
        for tmp in candidates:
            try:
                st = tmp.stat()
            except OSError:
                continue
            if now - st.st_mtime < max_age_s:
                continue
            if (st.st_dev, st.st_ino) in open_inodes:
                continue  # in-flight save — leave it alone
            try:
                tmp.unlink()
            except OSError:
                continue
            removed.append(tmp)
        if removed:
            logger.info(
                "faiss_store: reclaimed %d orphaned tmp file(s) from killed saves: %s",
                len(removed),
                ", ".join(p.name for p in removed),
            )
        return removed

    def _current_disk_signature(self) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        def signature(path: Path) -> tuple[int, int] | None:
            try:
                stat = path.stat()
            except FileNotFoundError:
                return None
            return (stat.st_mtime_ns, stat.st_size)

        return (signature(self.index_path), signature(self.id_map_path))

    def _create_new(self) -> None:
        """Create new empty FAISS index."""
        # IndexFlatIP = inner product (cosine similarity after L2 normalization)
        self.index = self._faiss.IndexFlatIP(self.dim)
        self.id_map: list[str] = []
        self.id_to_idx: dict[str, int] = {}  # O(1) lookup
        self._dirty = False
        self._desync = 0
        self._disk_signature = self._current_disk_signature()
        logger.info("Created new FAISS index at %s", self.index_path)

    def _load(self) -> None:
        """Load existing FAISS index and id_map from disk."""
        try:
            self.index = self._faiss.read_index(str(self.index_path))
            id_map_arr = np.load(self.id_map_path, allow_pickle=True)
            self.id_map = id_map_arr.tolist()

            # Validate consistency.
            #
            # The two directions are NOT symmetric and conflating them is what
            # silently corrupted this store for three weeks (2026-07-05 onward):
            #
            #   id_map LONGER than index  -> recoverable. The extra ids have no
            #       vector, so dropping them restores a consistent pair. This is
            #       the shape a crash now produces, because save() publishes
            #       id_map BEFORE the index (see save()).
            #
            #   index LONGER than id_map  -> NOT recoverable by truncation, and
            #       the old code "handled" it with a slice that was a silent
            #       no-op. Worse, add() then returned index.ntotal as the
            #       position while appending the id at len(id_map), so every
            #       subsequent write inherited the offset and persisted it into
            #       memories.embedding_idx. The drift was permanent and
            #       cumulative (+1 per interrupted publish; the live store
            #       reached 42).
            self._desync = self.index.ntotal - len(self.id_map)
            if self._desync > 0:
                logger.error(
                    "FAISS index/id_map DESYNC: index has %d vectors, id_map has %d ids "
                    "(index ahead by %d). Vector lookups through id_map positions are "
                    "unaffected, but %d trailing vectors have no id and writes are BLOCKED "
                    "until repaired. Run scripts/maintenance/repair_faiss_id_map.py.",
                    self.index.ntotal, len(self.id_map), self._desync, self._desync,
                )
            elif self._desync < 0:
                logger.warning(
                    "Index/id_map mismatch: %d vs %d. Dropping %d trailing id(s) with no "
                    "vector (recoverable direction, e.g. an interrupted publish).",
                    self.index.ntotal, len(self.id_map), -self._desync,
                )
                self.id_map = self.id_map[: self.index.ntotal]
                self._desync = 0

            # Build O(1) lookup dict
            self.id_to_idx = {mid: i for i, mid in enumerate(self.id_map)}
            self._dirty = False
            self._disk_signature = self._current_disk_signature()

            logger.info(
                "Loaded FAISS index with %d embeddings from %s",
                self.index.ntotal, self.index_path,
            )
        except Exception as e:
            # DO NOT silently create a new empty index here when files exist.
            #
            # This branch used to swallow ANY read failure — a transient I/O
            # error, a partially-written index, a version mismatch — and replace
            # a 700k-vector store with an empty one. The next save() would then
            # publish that empty index over the real files, destroying the
            # mapping irrecoverably. It is the same class of defect as the
            # publish-order bug: a plausible-looking recovery path that converts
            # a transient fault into permanent data loss.
            #
            # Creating fresh is only correct when there is genuinely nothing to
            # load. If the files exist, fail loudly and let the caller decide.
            if self.index_path.exists() or self.id_map_path.exists():
                logger.error(
                    "Failed to load FAISS index from %s: %s. REFUSING to replace the "
                    "existing store with an empty index — that would destroy the mapping "
                    "on the next save. Inspect the files or restore a backup.",
                    self.index_path, e,
                )
                raise
            logger.error("Failed to load FAISS index: %s. No files present; creating new.", e)
            self._create_new()

    def add(self, memory_id: str, embedding: np.ndarray) -> int:
        """
        Add embedding to index.

        Args:
            memory_id: Unique memory identifier (UUID string)
            embedding: Embedding vector (will be L2-normalized)

        Returns:
            Index position in FAISS index
        """
        # Ensure correct shape and type
        embedding = embedding.astype(np.float32).reshape(1, -1)

        # Validate dimension
        if embedding.shape[1] != self.dim:
            raise ValueError(
                f"Embedding dimension mismatch: got {embedding.shape[1]}, expected {self.dim}"
            )

        # Refuse vectors that can never be retrieved (see DegenerateVectorError).
        if not np.all(np.isfinite(embedding)):
            reason = "non_finite"
        elif not np.any(embedding):
            reason = "all_zero"
        else:
            reason = None
        if reason is not None:
            if os.environ.get("EPISODIC_ALLOW_DEGRADED_EMBEDDINGS") == "1":
                logger.error(
                    "Adding a DEGENERATE (%s) vector for %s because "
                    "EPISODIC_ALLOW_DEGRADED_EMBEDDINGS=1; this row will never "
                    "be retrievable by similarity.", reason, memory_id,
                )
            else:
                raise DegenerateVectorError(
                    f"refusing to index a {reason} vector for {memory_id}; the "
                    "embedding servers are probably down and a hash fallback was "
                    "substituted. Fix the embedders, or set "
                    "EPISODIC_ALLOW_DEGRADED_EMBEDDINGS=1 to accept an "
                    "unretrievable row on purpose."
                )

        # L2 normalize for cosine similarity
        self._faiss.normalize_L2(embedding)

        # Refuse to write into a desynced store. Previously this method took
        # `idx = self.index.ntotal` while appending the id at `len(self.id_map)`;
        # once those diverged, every returned position was wrong by the offset
        # and got persisted into memories.embedding_idx forever. Failing closed
        # keeps a recoverable outage from becoming permanent data corruption.
        if self.index.ntotal != len(self.id_map):
            raise FAISSDesyncError(
                f"Refusing to add to a desynced FAISS store: index has "
                f"{self.index.ntotal} vectors, id_map has {len(self.id_map)} ids. "
                f"Run scripts/maintenance/repair_faiss_id_map.py before writing."
            )

        # id_map is the authoritative position: it is what lookups resolve
        # through (see get_memory_id / faiss_store search callers), so deriving
        # the index from it makes the two structurally unable to disagree.
        idx = len(self.id_map)
        self.index.add(embedding)
        self.id_map.append(memory_id)
        self.id_to_idx[memory_id] = idx  # O(1) insert
        self._dirty = True

        return idx

    def reload_if_changed(self, *, force: bool = False) -> bool:
        """Reload persisted FAISS files when another process updated them."""
        if self._dirty and not force:
            return False
        current = self._current_disk_signature()
        if current == self._disk_signature:
            return False
        if current[0] is None or current[1] is None:
            return False
        self._load()
        return True

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        """
        Search for similar embeddings.

        Args:
            query: Query embedding vector
            k: Number of results to return

        Returns:
            List of (memory_id, similarity_score) tuples, sorted by score descending
        """
        if self.index.ntotal == 0:
            return []

        # Ensure correct shape and type
        query = query.astype(np.float32).reshape(1, -1)

        # Validate dimension
        if query.shape[1] != self.dim:
            raise ValueError(
                f"Query dimension mismatch: got {query.shape[1]}, expected {self.dim}"
            )

        # L2 normalize for cosine similarity
        self._faiss.normalize_L2(query)

        # Clamp k to available entries
        k = min(k, self.index.ntotal)

        # Search
        scores, indices = self.index.search(query, k)

        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            # FAISS returns -1 for invalid indices
            if idx >= 0 and idx < len(self.id_map):
                results.append((self.id_map[idx], float(score)))

        return results

    def get_embedding(self, idx: int) -> np.ndarray | None:
        """
        Retrieve embedding by index.

        Note: FAISS IndexFlatIP stores raw vectors, so we can reconstruct.

        Args:
            idx: Index position

        Returns:
            Embedding vector or None if invalid index
        """
        if idx < 0 or idx >= self.index.ntotal:
            return None

        embedding = np.zeros((1, self.dim), dtype=np.float32)
        self.index.reconstruct(idx, embedding[0])
        return embedding[0]

    def save(self) -> None:
        """Persist index and id_map to disk."""
        if not self._dirty:
            return
        current = self._current_disk_signature()
        if current != self._disk_signature:
            raise StaleFAISSSaveError(
                "Refusing to save stale FAISS embedding store: persisted index/id_map "
                "changed after this instance loaded them. Reload before writing."
            )
        token = uuid.uuid4().hex
        index_tmp = self.index_path.with_name(f".{self.index_path.name}.{token}.tmp")
        id_map_tmp = self.id_map_path.with_name(f".{self.id_map_path.name}.{token}.tmp")
        id_map_tmp_alt = id_map_tmp.with_name(id_map_tmp.name + ".npy")
        try:
            self._faiss.write_index(self.index, str(index_tmp))
            np.save(str(id_map_tmp), np.array(self.id_map, dtype=object), allow_pickle=True)
            if not id_map_tmp.exists() and id_map_tmp_alt.exists():
                id_map_tmp_alt.rename(id_map_tmp)
            if not index_tmp.exists():
                raise RuntimeError(f"FAISS temp index did not materialize at {index_tmp}")
            if not id_map_tmp.exists():
                raise RuntimeError(f"FAISS temp id_map did not materialize at {id_map_tmp}")
            current = self._current_disk_signature()
            if current != self._disk_signature:
                raise StaleFAISSSaveError(
                    "Refusing to publish stale FAISS embedding store: persisted index/id_map "
                    "changed while temp files were being written. Reload before retrying."
                )
            # PUBLISH ORDER IS LOAD-BEARING. Two files cannot be renamed
            # atomically as a pair on POSIX, so a crash between these lines
            # always leaves them mismatched — the only choice is WHICH
            # mismatch, and the two are not equally bad:
            #
            #   index first (the old order): index ahead of id_map. Trailing
            #       vectors have no id, _load() cannot repair it, and add()
            #       inherited the offset into every future embedding_idx.
            #       Unrecoverable and cumulative — this produced a drift of 42
            #       and mis-resolved 30,238 live rows.
            #
            #   id_map first (this order): id_map ahead of the index. The
            #       trailing ids simply have no vector yet, and _load() drops
            #       them. Self-healing.
            #
            # fsync each temp file before its rename so the rename cannot be
            # reordered ahead of the data it publishes.
            for tmp in (id_map_tmp, index_tmp):
                with open(tmp, "rb") as fh:
                    os.fsync(fh.fileno())
            id_map_tmp.replace(self.id_map_path)
            index_tmp.replace(self.index_path)
        finally:
            for tmp in (index_tmp, id_map_tmp, id_map_tmp_alt):
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not remove temporary FAISS file %s", tmp)
        self._dirty = False
        self._disk_signature = self._current_disk_signature()
        logger.debug("Saved FAISS index with %d embeddings", self.index.ntotal)

    @property
    def count(self) -> int:
        """Number of stored embeddings."""
        return self.index.ntotal

    def get_memory_id(self, idx: int) -> str | None:
        """Get memory_id for a given index."""
        if idx < 0 or idx >= len(self.id_map):
            return None
        return self.id_map[idx]

    def get_index(self, memory_id: str) -> int | None:
        """Get index for a given memory_id. O(1) lookup."""
        return self.id_to_idx.get(memory_id)


class NumpyEmbeddingStore:
    """
    Legacy NumPy-based embedding store for migration/fallback.

    Provides same interface as FAISSEmbeddingStore but uses memory-mapped NumPy.
    O(n) search complexity - only use for small datasets or migration.
    """

    def __init__(
        self,
        path: Path = DEFAULT_FAISS_PATH,
        dim: int = 1024,  # BGE-large embedding dimension
    ):
        self.path = Path(path)
        self.dim = dim
        self.embeddings_path = self.path / "embeddings.npy"
        self.id_map_path = self.path / "id_map.npy"

        self.path.mkdir(parents=True, exist_ok=True)

        if self.embeddings_path.exists() and self.id_map_path.exists():
            self._load()
        else:
            self._create_new()

    def _create_new(self) -> None:
        """Create new empty store."""
        initial_size = 1000
        self._embeddings = np.zeros((initial_size, self.dim), dtype=np.float32)
        np.save(self.embeddings_path, self._embeddings)
        self._embeddings = np.load(self.embeddings_path, mmap_mode="r+")
        self.id_map: list[str] = []
        self._next_idx = 0

    def _load(self) -> None:
        """Load existing store."""
        try:
            self._embeddings = np.load(self.embeddings_path, mmap_mode="r+")
            id_map_arr = np.load(self.id_map_path, allow_pickle=True)
            self.id_map = id_map_arr.tolist()
            self._next_idx = len(self.id_map)
        except Exception as e:
            logger.error("Failed to load NumPy store: %s. Creating new.", e)
            self._create_new()

    def _grow(self) -> None:
        """Double array size when full."""
        current_size = len(self._embeddings)
        new_size = current_size * 2
        new_embeddings = np.zeros((new_size, self.dim), dtype=np.float32)
        new_embeddings[:current_size] = self._embeddings[:]
        np.save(self.embeddings_path, new_embeddings)
        self._embeddings = np.load(self.embeddings_path, mmap_mode="r+")

    def add(self, memory_id: str, embedding: np.ndarray) -> int:
        """Add embedding, return index."""
        if self._next_idx >= len(self._embeddings):
            self._grow()

        idx = self._next_idx
        self._embeddings[idx] = embedding.astype(np.float32)
        self.id_map.append(memory_id)
        self._next_idx += 1
        self._embeddings.flush()

        return idx

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        """Search by cosine similarity. O(n) complexity."""
        if self._next_idx == 0:
            return []

        query = query.astype(np.float32)
        query_norm = query / (np.linalg.norm(query) + 1e-8)

        # Compute all similarities (O(n))
        similarities = []
        for i in range(self._next_idx):
            emb = self._embeddings[i]
            emb_norm = emb / (np.linalg.norm(emb) + 1e-8)
            sim = float(np.dot(query_norm, emb_norm))
            similarities.append((self.id_map[i], sim))

        # Sort and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

    def save(self) -> None:
        """Persist to disk."""
        self._embeddings.flush()
        np.save(self.id_map_path, np.array(self.id_map, dtype=object))

    def get_embedding(self, idx: int) -> np.ndarray | None:
        """Retrieve embedding by index."""
        if idx < 0 or idx >= self._next_idx:
            return None
        return self._embeddings[idx].copy()

    @property
    def count(self) -> int:
        return self._next_idx

"""Shared contract for rows represented in the episodic FAISS index."""

from __future__ import annotations


def is_indexed_action_type(action_type: object) -> bool:
    """Return whether a memory action type is valid for FAISS-backed recall."""
    return isinstance(action_type, str) and bool(action_type.strip())


def indexed_memory_predicate(column: str = "action_type") -> str:
    """Return the SQLite predicate selecting every FAISS-indexed memory row."""
    return f"TRIM(COALESCE({column}, '')) != ''"

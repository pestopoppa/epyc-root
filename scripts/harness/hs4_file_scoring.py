"""Strict file-task answer formats before the existing native exact-match scorer.

This module does not select or load a scorer. Callers must supply the pinned
APP `scripts.benchmark.debug_scorer.score_answer` on the trusted grader side.
No isolation, inference or measurement authority is established here.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def validate_answer(kind: str, text: str) -> dict[str, Any]:
    """Require canonical one-line JSON with one task-specific, bounded schema."""
    if not isinstance(text, str) or not text or len(text) > 8192:
        raise ValueError("missing or oversized answer")
    try:
        obj = json.loads(text, object_pairs_hook=_pairs)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("answer must be one canonical JSON object") from exc
    if not isinstance(obj, dict) or canonical(obj) != text:
        raise ValueError("answer must be canonical JSON with no extra text")
    if kind == "lookup":
        path = obj.get("path")
        if set(obj) != {"path"} or not isinstance(path, str) or not _NAME.fullmatch(path):
            raise ValueError("lookup needs one bounded path")
    elif kind == "inventory":
        total = obj.get("total")
        if set(obj) != {"total"} or type(total) is not int or not 0 <= total <= 1_000_000:
            raise ValueError("inventory needs one nonnegative integer total")
    elif kind == "reconciliation":
        rows = obj.get("mismatches")
        if set(obj) != {"mismatches"} or not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("reconciliation needs a bounded mismatch array")
        names = []
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"item", "left", "right"}
                    or not isinstance(row["item"], str) or not _NAME.fullmatch(row["item"])
                    or type(row["left"]) is not int or type(row["right"]) is not int
                    or not 0 <= row["left"] <= 1_000_000 or not 0 <= row["right"] <= 1_000_000
                    or row["left"] == row["right"]):
                raise ValueError("invalid mismatch row")
            names.append(row["item"])
        if names != sorted(set(names)):
            raise ValueError("mismatch items must be unique and sorted")
    else:
        raise ValueError("unknown task family")
    return obj


def score(kind: str, answer: str, expected: str,
          native_scorer: Callable[[str, str, str, dict[str, Any]], bool]) -> bool:
    """Apply the format gate, then call the unchanged native scorer exactly once."""
    validate_answer(kind, expected)
    try:
        validate_answer(kind, answer)
    except ValueError:
        return False
    result = native_scorer(answer, expected, "exact_match", {"normalize": False})
    if type(result) is not bool:
        raise TypeError("native scorer returned a non-boolean")
    return result

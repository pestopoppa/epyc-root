"""Canonical rotated-journal shard iterator (audit JRN-5 / JRN-6 / JRN-7).

The AutoPilot experiment journal rotates every ``MAX_TRIALS_PER_FILE`` trials into
sibling files beside each other: the base shard ``autopilot_journal.jsonl`` is
batch 0 and ``autopilot_journal_<N>.jsonl`` is batch N (N > 0). Historically every
reader rediscovered these shards ad hoc, which reproduced three recurring defects
this module fixes in exactly one place:

  JRN-5  Base-only reads (opening ``autopilot_journal.jsonl`` alone) silently
         analyze FROZEN pre-rotation data as soon as trials pass the first
         rotation boundary — the live tail lives in the highest-numbered shard.
  JRN-6  Lexicographic ``sorted(glob(...))`` orders ``_10`` before ``_2``, so
         shards load out of numeric order and any "latest shard" heuristic
         silently breaks the first time the index reaches two digits.
  JRN-7  While-loop discovery (``batch = 0; while path(batch).exists(): batch += 1``)
         STOPS at the first missing index, so a gap at ``_2`` hides ``_3`` and
         every later shard.

``journal_shards()`` returns the existing shards sorted by NUMERIC batch index,
tolerant of gaps, ignoring non-matching siblings (torn-tail ``.corrupt-*``
sidecars, ``.tsv`` mirrors, and unrelated ``.jsonl`` files).
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_STEM = "autopilot_journal"
DEFAULT_SUFFIX = ".jsonl"


def _shard_pattern(stem: str, suffix: str) -> re.Pattern[str]:
    # Base file: "{stem}{suffix}" (batch 0). Rotated: "{stem}_<N>{suffix}".
    return re.compile(rf"^{re.escape(stem)}(?:_(\d+))?{re.escape(suffix)}$")


def shard_batch_index(
    path: Path | str,
    *,
    stem: str = DEFAULT_STEM,
    suffix: str = DEFAULT_SUFFIX,
) -> int | None:
    """Return a shard filename's numeric batch index, or None if it does not match.

    The base file (``{stem}{suffix}``) is batch 0; ``{stem}_N{suffix}`` is batch N.
    Non-matching names (``.corrupt-*`` sidecars, ``.tsv`` mirrors, unrelated
    files) return None so callers can skip them.
    """
    match = _shard_pattern(stem, suffix).match(Path(path).name)
    if match is None:
        return None
    captured = match.group(1)
    return int(captured) if captured is not None else 0


def journal_shards(
    journal_dir: Path,
    stem: str = DEFAULT_STEM,
    suffix: str = DEFAULT_SUFFIX,
) -> list[Path]:
    """Return existing journal shards in ``journal_dir`` sorted by numeric batch index.

    Globs ``{stem}*{suffix}``, parses each filename's batch index (base = 0,
    ``_N`` = N), ignores non-matching siblings, and sorts NUMERICALLY so a missing
    ``_2`` does not hide ``_3`` (gap-tolerant) and ``_9`` precedes ``_10``. See the
    module docstring for audit JRN-5 / JRN-6 / JRN-7.
    """
    journal_dir = Path(journal_dir)
    if not journal_dir.is_dir():
        return []
    indexed: list[tuple[int, Path]] = []
    for path in journal_dir.glob(f"{stem}*{suffix}"):
        if not path.is_file():
            continue
        index = shard_batch_index(path, stem=stem, suffix=suffix)
        if index is None:
            continue
        indexed.append((index, path))
    indexed.sort(key=lambda item: item[0])
    return [path for _, path in indexed]


def resolve_journal_paths(
    path: Path,
    stem: str = DEFAULT_STEM,
    suffix: str = DEFAULT_SUFFIX,
) -> list[Path]:
    """Expand a base-shard path to all rotated shards; honor an explicit non-base path.

    Audit JRN-5: pointing a reader at the canonical base shard
    (``{stem}{suffix}``) must read EVERY rotated shard beside it, not just the
    frozen base file. A path that names a specific non-base file is returned as a
    single-element list, so an explicit ``--journal some_other.jsonl`` keeps its
    exact semantics.
    """
    path = Path(path)
    if path.name == f"{stem}{suffix}":
        shards = journal_shards(path.parent, stem=stem, suffix=suffix)
        return shards or [path]
    return [path]

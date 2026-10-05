"""D3: canonical rotated-journal shard iterator (audit JRN-5 / JRN-6 / JRN-7).

Covers the three defects `journal_shards` fixes once for every reader:
  - numeric batch ordering (`_9` before `_10`, not lexicographic),
  - gap tolerance (a missing `_2` does not hide `_3`),
  - non-shard sibling exclusion (`.corrupt-*` sidecars, `.tsv` mirrors),
  - discovery works even when the base shard is absent.

All fixtures use tmp_path; the live orchestration/ journals are never touched.
"""

from __future__ import annotations

from pathlib import Path

from scripts.autopilot.journal_shards import (
    journal_shards,
    resolve_journal_paths,
    shard_batch_index,
)


def _touch(path: Path) -> Path:
    path.write_text("", encoding="utf-8")
    return path


def _names(paths: list[Path]) -> list[str]:
    return [p.name for p in paths]


def test_numeric_ordering_puts_9_before_10(tmp_path: Path) -> None:
    # Create out of order and with two-digit indices to defeat lexicographic sort.
    for suffix in ("", "_1", "_2", "_9", "_10", "_11"):
        _touch(tmp_path / f"autopilot_journal{suffix}.jsonl")

    shards = journal_shards(tmp_path)

    assert _names(shards) == [
        "autopilot_journal.jsonl",
        "autopilot_journal_1.jsonl",
        "autopilot_journal_2.jsonl",
        "autopilot_journal_9.jsonl",
        "autopilot_journal_10.jsonl",
        "autopilot_journal_11.jsonl",
    ]


def test_gap_tolerant_missing_2_does_not_hide_3(tmp_path: Path) -> None:
    _touch(tmp_path / "autopilot_journal.jsonl")
    _touch(tmp_path / "autopilot_journal_1.jsonl")
    # deliberately NO _2
    _touch(tmp_path / "autopilot_journal_3.jsonl")

    shards = journal_shards(tmp_path)

    assert _names(shards) == [
        "autopilot_journal.jsonl",
        "autopilot_journal_1.jsonl",
        "autopilot_journal_3.jsonl",
    ]


def test_sidecar_and_tsv_and_unrelated_are_excluded(tmp_path: Path) -> None:
    _touch(tmp_path / "autopilot_journal.jsonl")
    _touch(tmp_path / "autopilot_journal_1.jsonl")
    # Non-shard siblings that must be ignored:
    _touch(tmp_path / "autopilot_journal.jsonl.corrupt-20260101T000000Z")
    _touch(tmp_path / "autopilot_journal_1.jsonl.corrupt-20260101T000000Z")
    _touch(tmp_path / "autopilot_journal.tsv")
    _touch(tmp_path / "autopilot_journal_1.tsv")
    _touch(tmp_path / "autopilot_journal_backup.jsonl")  # non-numeric suffix
    _touch(tmp_path / "factual_risk_calibration.jsonl")  # unrelated jsonl

    shards = journal_shards(tmp_path)

    assert _names(shards) == [
        "autopilot_journal.jsonl",
        "autopilot_journal_1.jsonl",
    ]


def test_base_absent_still_finds_rotated_shards(tmp_path: Path) -> None:
    # No base autopilot_journal.jsonl at all — only rotated shards.
    _touch(tmp_path / "autopilot_journal_1.jsonl")
    _touch(tmp_path / "autopilot_journal_2.jsonl")

    shards = journal_shards(tmp_path)

    assert _names(shards) == [
        "autopilot_journal_1.jsonl",
        "autopilot_journal_2.jsonl",
    ]


def test_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert journal_shards(tmp_path / "does-not-exist") == []


def test_shard_batch_index_parsing() -> None:
    assert shard_batch_index("autopilot_journal.jsonl") == 0
    assert shard_batch_index("autopilot_journal_1.jsonl") == 1
    assert shard_batch_index("autopilot_journal_10.jsonl") == 10
    assert shard_batch_index("autopilot_journal.jsonl.corrupt-2026") is None
    assert shard_batch_index("autopilot_journal.tsv") is None
    assert shard_batch_index("autopilot_journal_x.jsonl") is None
    assert shard_batch_index("something_else.jsonl") is None


def test_resolve_journal_paths_expands_base_to_all_shards(tmp_path: Path) -> None:
    base = _touch(tmp_path / "autopilot_journal.jsonl")
    _touch(tmp_path / "autopilot_journal_1.jsonl")

    resolved = resolve_journal_paths(base)

    assert _names(resolved) == [
        "autopilot_journal.jsonl",
        "autopilot_journal_1.jsonl",
    ]


def test_resolve_journal_paths_honors_explicit_non_base_path(tmp_path: Path) -> None:
    _touch(tmp_path / "autopilot_journal.jsonl")
    _touch(tmp_path / "autopilot_journal_1.jsonl")
    explicit = tmp_path / "some_other_export.jsonl"

    # An explicit, non-base path is returned as-is (single element), even when
    # rotated shards exist beside it.
    assert resolve_journal_paths(explicit) == [explicit]

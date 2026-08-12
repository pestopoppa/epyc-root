#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for the advisory-shard archive (bus: archive sealed advisory shards
outside the repo, with their denominators, commit 4622c0d7).

`advisory.jsonl` is gitignored AND lives inside the repo, so a sealed shard
was `git clean -x` fodder — and was actually destroyed on 2026-08-12, which
is why a 4,602-row figure the fleet acted on for hours is now unreproducible.
`advisory_archive_root()` resolves a destination OUTSIDE the repo (env
`EPYC_BUS_ARCHIVE_ROOT`, default `/mnt/raid0/llm/bus-archive/advisory`).
`_archive_advisory_shard()` copies a sealed shard there and VERIFIES it by
sha256 — a copy that exists on disk is not a copy that arrived intact — and
writes a small digest beside it (via `summarize_advisory_shard()`) even when
the copy itself fails, because the digest is ~1 KB against a shard of up to
128 MiB and must survive exactly the disk pressure the shard will not.

`summarize_advisory_shard()` carries three denominators: N pick records, M
distinct rows, and K (dispatchable-at-emission) — K is deliberately left
`None` with its recovery method named, because computing it against today's
handoff state instead of the state at each pick's `first_ts` would date-shift
the number while reading as authoritative. `first_ts`/`last_ts` per pick are
what make K recoverable from git later; losing them makes K permanently
uncomputable, not just temporarily unknown.

These started as ad-hoc, inline mutation tests run by hand while landing the
commit — not collected by any suite, so not counted by any reporter, so
silently unable to protect the code going forward. This file is that
protection, made durable.

BOTH DIRECTIONS, per mechanism:
  - summarize_advisory_shard: N and M must be able to DIFFER (proves they are
    not the same field read twice); an empty shard is 0/0, not an inherited
    or stale count; malformed lines are counted and do not lose the shard.
  - _archive_advisory_shard: a copy that verifies is `archived: True`; a copy
    that lands corrupted (simulated via a `shutil.copyfile` monkeypatch that
    writes the wrong bytes) is `archived: False` with a sha256-mismatch
    error — THE KEY assertion, because it is what proves the archive is
    trusted by content, not by mere existence. The digest write is
    independent of the copy outcome in both directions.
  - K stays None with `k_method` present in both directions (empty and
    populated shards), asserting the contract that this code does not guess
    a denominator it cannot compute at seal time.

Usage: pytest scripts/coordination/tests/test_advisory_archive.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import session_bus_coordinator as sbc  # noqa: E402

ADV = sbc.ADVISORY_SCHEMA


def _pick(task_id: str, ts: str, kind: str = "would-assign", **extra) -> dict:
    row = {"schema_version": ADV, "kind": kind, "ts": ts, "task_id": task_id,
           "agent": "mainA", "lane": "cpu"}
    row.update(extra)
    return row


def _write_shard(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


@pytest.fixture(autouse=True)
def _clean_archive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production callers never set EPYC_BUS_ARCHIVE_ROOT unless testing it."""
    monkeypatch.delenv(sbc._ADVISORY_ARCHIVE_ENV, raising=False)


# =========================================================================== #
# advisory_archive_root() — resolution
# =========================================================================== #
def test_default_archive_root_is_outside_the_repo() -> None:
    root = sbc.advisory_archive_root()
    assert root == sbc._ADVISORY_ARCHIVE_DEFAULT
    assert not str(root).startswith(str(REPO_ROOT))


def test_archive_root_env_override_wins(monkeypatch: pytest.MonkeyPatch,
                                         tmp_path: Path) -> None:
    monkeypatch.setenv(sbc._ADVISORY_ARCHIVE_ENV, str(tmp_path / "custom-archive"))
    assert sbc.advisory_archive_root() == tmp_path / "custom-archive"


# =========================================================================== #
# summarize_advisory_shard — N and M are DIFFERENT counts
# =========================================================================== #
def test_n_and_m_can_differ_eight_records_two_rows(tmp_path: Path) -> None:
    """THE CENTRAL ASSERTION for the denominators. 8 pick records collapsing to
    2 distinct task_ids must report pick_records=8, distinct_rows=2 — proving
    N and M are computed independently, not the same field surfaced twice
    (which is exactly the bug that turned 811 re-emissions of 9 rows into a
    4,602-row backlog nobody had)."""
    shard = tmp_path / "advisory_1.jsonl"
    lines = []
    for i in range(5):
        lines.append(json.dumps(_pick("task-A", f"2026-08-12T03:{i:02d}:00+00:00")))
    for i in range(3):
        lines.append(json.dumps(_pick("task-B", f"2026-08-12T04:{i:02d}:00+00:00")))
    _write_shard(shard, lines)

    summary = sbc.summarize_advisory_shard(shard)
    assert summary["pick_records"] == 8
    assert summary["distinct_rows"] == 2
    assert summary["pick_records"] != summary["distinct_rows"]


def test_empty_shard_is_zero_zero_not_a_stale_count(tmp_path: Path) -> None:
    """An empty shard must summarize to 0/0 — never an inherited count from
    some other shard or a leftover accumulator."""
    shard = tmp_path / "advisory_1.jsonl"
    _write_shard(shard, [])

    summary = sbc.summarize_advisory_shard(shard)
    assert summary["pick_records"] == 0
    assert summary["distinct_rows"] == 0
    assert summary["malformed_lines"] == 0
    assert summary["picks"] == {}


def test_malformed_lines_are_counted_and_do_not_lose_the_shard(tmp_path: Path) -> None:
    """A bad JSON line must not abort the whole shard summary — it is tallied
    in malformed_lines and every well-formed line around it still counts."""
    shard = tmp_path / "advisory_1.jsonl"
    lines = [
        json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00")),
        "{this is not json",
        json.dumps(_pick("task-A", "2026-08-12T03:01:00+00:00")),
        "",  # blank lines must be silently skipped, not counted as malformed
        json.dumps(_pick("task-B", "2026-08-12T03:02:00+00:00")),
    ]
    _write_shard(shard, lines)

    summary = sbc.summarize_advisory_shard(shard)
    assert summary["malformed_lines"] == 1
    assert summary["pick_records"] == 3
    assert summary["distinct_rows"] == 2


def test_non_pick_kinds_are_not_counted(tmp_path: Path) -> None:
    """Only would-assign/assign/pick rows are denominator material; other
    advisory kinds sharing the shard must not inflate N."""
    shard = tmp_path / "advisory_1.jsonl"
    lines = [
        json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00")),
        json.dumps({"schema_version": ADV, "kind": "advisory-rotated",
                    "ts": "2026-08-12T03:01:00+00:00"}),
        json.dumps({"schema_version": ADV, "kind": "would-idle",
                    "ts": "2026-08-12T03:02:00+00:00", "agent": "mainB"}),
    ]
    _write_shard(shard, lines)

    summary = sbc.summarize_advisory_shard(shard)
    assert summary["pick_records"] == 1
    assert summary["distinct_rows"] == 1


# =========================================================================== #
# K (dispatchable_at_emission) — never guessed
# =========================================================================== #
def test_k_stays_none_with_method_named_on_a_populated_shard(tmp_path: Path) -> None:
    shard = tmp_path / "advisory_1.jsonl"
    _write_shard(shard, [json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00"))])

    summary = sbc.summarize_advisory_shard(shard)
    assert summary["dispatchable_at_emission"] is None
    assert "k_method" in summary
    assert isinstance(summary["k_method"], str) and summary["k_method"]


def test_k_stays_none_on_an_empty_shard_too(tmp_path: Path) -> None:
    """The K contract holds even with nothing to summarize — it is not a
    side effect of having records to compute over."""
    shard = tmp_path / "advisory_1.jsonl"
    _write_shard(shard, [])

    summary = sbc.summarize_advisory_shard(shard)
    assert summary["dispatchable_at_emission"] is None
    assert "k_method" in summary


# =========================================================================== #
# first_ts / last_ts — what makes K recoverable from git later
# =========================================================================== #
def test_first_and_last_ts_are_preserved_per_pick(tmp_path: Path) -> None:
    """If first_ts/last_ts were dropped, K would become permanently
    uncomputable rather than merely deferred: nothing else in the digest ties
    a pick back to the handoff state at the moment it was emitted."""
    shard = tmp_path / "advisory_1.jsonl"
    lines = [
        json.dumps(_pick("task-A", "2026-08-12T03:05:00+00:00")),
        json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00")),  # earlier, out of order
        json.dumps(_pick("task-A", "2026-08-12T03:10:00+00:00")),  # later
    ]
    _write_shard(shard, lines)

    summary = sbc.summarize_advisory_shard(shard)
    slot = summary["picks"]["task-A"]
    assert slot["n"] == 3
    assert slot["first_ts"] == "2026-08-12T03:00:00+00:00"
    assert slot["last_ts"] == "2026-08-12T03:10:00+00:00"


# =========================================================================== #
# _archive_advisory_shard — content-verified, not existence-verified
# =========================================================================== #
def test_archive_succeeds_and_verifies_by_sha256(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    archive_root = tmp_path / "archive"
    monkeypatch.setenv(sbc._ADVISORY_ARCHIVE_ENV, str(archive_root))

    shard = tmp_path / "bus" / "advisory_1.jsonl"
    shard.parent.mkdir(parents=True)
    _write_shard(shard, [json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00"))])
    expected_sha = hashlib.sha256(shard.read_bytes()).hexdigest()

    out = sbc._archive_advisory_shard(shard, epoch=7)

    assert out["archived"] is True
    assert out["archive_sha256"] == expected_sha
    assert "archive_error" not in out
    dest = Path(out["archive_path"])
    assert dest.read_bytes() == shard.read_bytes()
    assert out["digest_written"] is True
    # A successful archive must still carry REAL denominators, not merely a
    # truthy `archived`. Without this, a summarize_advisory_shard() that
    # returned a hardcoded {"pick_records": 811, "distinct_rows": 9} would
    # pass this test too — it says nothing about the copy otherwise.
    assert out["shard_summary"]["pick_records"] == 1
    assert out["shard_summary"]["distinct_rows"] == 1


def test_corrupted_copy_is_detected_by_sha256_not_by_existence(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE KEY TEST. A copy that lands on disk but with the WRONG bytes must
    be reported as archived: False with a sha256-mismatch error — proving the
    archive is trusted by content, not by `dest.exists()`. Without this test,
    a regression that swaps `shutil.copyfile` verification for a bare
    existence check would pass every other test in this file."""
    archive_root = tmp_path / "archive"
    monkeypatch.setenv(sbc._ADVISORY_ARCHIVE_ENV, str(archive_root))

    shard = tmp_path / "bus" / "advisory_1.jsonl"
    shard.parent.mkdir(parents=True)
    _write_shard(shard, [json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00"))])

    real_copyfile = shutil.copyfile

    def _corrupting_copyfile(src, dst):
        real_copyfile(src, dst)
        # Land the file (so it EXISTS), but with the wrong bytes.
        Path(dst).write_bytes(b"this is not the shard content")

    monkeypatch.setattr(sbc.shutil, "copyfile", _corrupting_copyfile)

    out = sbc._archive_advisory_shard(shard, epoch=7)

    assert out["archived"] is False
    assert "archive_error" in out
    assert "sha256" in out["archive_error"].lower()
    dest = Path(out["archive_path"])
    assert dest.exists(), "precondition: the corrupted copy did land on disk"
    assert dest.read_bytes() != shard.read_bytes()
    # The denominators must still be REAL even though the copy failed — this
    # is what the digest file will carry forward, so it must not silently be
    # a hardcoded/stale placeholder just because the copy path errored.
    assert out["shard_summary"]["pick_records"] == 1
    assert out["shard_summary"]["distinct_rows"] == 1


def test_digest_is_still_written_when_the_copy_fails(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The digest (~1 KB) must survive disk pressure a 128 MiB shard will
    not: even when copying the shard itself raises, the digest file beside
    it is still written, and it still carries the denominators."""
    archive_root = tmp_path / "archive"
    monkeypatch.setenv(sbc._ADVISORY_ARCHIVE_ENV, str(archive_root))

    shard = tmp_path / "bus" / "advisory_1.jsonl"
    shard.parent.mkdir(parents=True)
    _write_shard(shard, [
        json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00")),
        json.dumps(_pick("task-B", "2026-08-12T03:01:00+00:00")),
    ])

    def _failing_copyfile(src, dst):
        raise OSError("simulated ENOSPC: no space left on device")

    monkeypatch.setattr(sbc.shutil, "copyfile", _failing_copyfile)

    out = sbc._archive_advisory_shard(shard, epoch=7)

    assert out["archived"] is False
    assert "archive_error" in out
    assert out["digest_written"] is True

    digest_path = archive_root / "advisory_1.digest.json"
    assert digest_path.exists()
    digest = json.loads(digest_path.read_text(encoding="utf-8"))
    assert digest["pick_records"] == 2
    assert digest["distinct_rows"] == 2
    assert digest["dispatchable_at_emission"] is None


def test_archive_root_creation_failure_still_reports_and_does_not_raise(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If even the archive root cannot be created, this must degrade to a
    reported failure, never an exception that stops the tick."""
    # Point the archive root at a path whose parent is a FILE, so mkdir(parents=True)
    # raises NotADirectoryError/OSError.
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("i am a file, not a directory", encoding="utf-8")
    monkeypatch.setenv(sbc._ADVISORY_ARCHIVE_ENV, str(blocker / "advisory"))

    shard = tmp_path / "bus" / "advisory_1.jsonl"
    shard.parent.mkdir(parents=True)
    _write_shard(shard, [json.dumps(_pick("task-A", "2026-08-12T03:00:00+00:00"))])

    out = sbc._archive_advisory_shard(shard, epoch=7)

    assert out["archived"] is False
    assert "archive_error" in out
    assert "shard_summary" in out, "denominators must still be computed even when the root is dead"
    # Not just present — REAL. A dead archive root must not be an excuse to
    # skip computing the actual N/M for this shard.
    assert out["shard_summary"]["pick_records"] == 1
    assert out["shard_summary"]["distinct_rows"] == 1


# =========================================================================== #
# rotate_advisory — the call site actually wires archival in
# =========================================================================== #
def test_rotate_advisory_archives_the_sealed_shard_end_to_end(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive_root = tmp_path / "archive"
    monkeypatch.setenv(sbc._ADVISORY_ARCHIVE_ENV, str(archive_root))

    bus_root = tmp_path / "bus"
    bus_root.mkdir()
    live = bus_root / "advisory.jsonl"
    rows = [_pick(f"task-{i % 3}", f"2026-08-12T03:{i:02d}:00+00:00") for i in range(10)]
    _write_shard(live, [json.dumps(r) for r in rows])

    out = sbc.rotate_advisory(bus_root, epoch=1, max_bytes=1)  # force rotation

    assert len(out) == 1
    row = out[0]
    assert row["kind"] == "advisory-rotated"
    assert row["archived"] is True
    assert row["shard_summary"]["pick_records"] == 10
    assert row["shard_summary"]["distinct_rows"] == 3
    assert row["shard_summary"]["dispatchable_at_emission"] is None
    archived_copy = archive_root / row["shard"]
    assert archived_copy.exists()
    assert archived_copy.read_text(encoding="utf-8") == "\n".join(
        json.dumps(r) for r in rows) + "\n"

"""A5 journal durability: tolerant read + torn-tail quarantine on append.

Covers ExperimentJournal's crash-durability contract:
  - a torn *trailing* line (partial final append, no newline) loads tolerantly,
  - the next append quarantines those bytes to a `.corrupt-*` sidecar and
    truncates the shard back to the last good newline,
  - mid-file corruption (a bad line with good lines after it) is fatal, and
  - normal appends leave a clean newline-terminated shard.

All fixtures use tmp_path; the live orchestration/ journals are never touched.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import (  # noqa: E402
    ExperimentJournal,
    ExperimentJournalCorruptError,
    JournalEntry,
)


def _entry(trial_id: int, *, quality: float = 1.0) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=f"2026-06-14T00:00:0{trial_id}Z",
        species="unit",
        action_type="seed_batch",
        tier=1,
        quality=quality,
        speed=40.0,
        cost=0.2,
        reliability=0.9,
        pareto_status="frontier",
    )


def _line(entry: JournalEntry) -> str:
    """Serialize exactly as ExperimentJournal.record writes JSONL rows."""
    return json.dumps(asdict(entry), default=str)


def _shard(journal_dir: Path) -> Path:
    return journal_dir / "autopilot_journal.jsonl"


def test_torn_trailing_line_loads_tolerantly(tmp_path: Path) -> None:
    # 2 good lines + a torn partial (no trailing newline).
    partial = _line(_entry(3))[:80]  # truncated mid-record, not valid JSON
    _shard(tmp_path).write_bytes(
        (_line(_entry(1)) + "\n" + _line(_entry(2)) + "\n" + partial).encode("utf-8")
    )

    journal = ExperimentJournal(journal_dir=tmp_path)

    assert journal.count() == 2
    assert journal.torn_lines_skipped == 1
    assert [e.trial_id for e in journal.all_entries()] == [1, 2]


def test_next_append_quarantines_torn_tail_to_sidecar(tmp_path: Path) -> None:
    partial = _line(_entry(3))[:80]
    partial_bytes = partial.encode("utf-8")
    _shard(tmp_path).write_bytes(
        (_line(_entry(1)) + "\n" + _line(_entry(2)) + "\n" + partial).encode("utf-8")
    )

    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(3, quality=1.5))

    # The torn bytes were quarantined verbatim, not deleted.
    sidecars = list(tmp_path.glob("autopilot_journal.jsonl.corrupt-*"))
    assert len(sidecars) == 1
    assert sidecars[0].read_bytes() == partial_bytes

    # The shard now parses cleanly line-by-line and a fresh reload sees 3.
    raw = _shard(tmp_path).read_bytes()
    assert raw.endswith(b"\n")
    parsed = [json.loads(ln) for ln in raw.decode("utf-8").splitlines() if ln.strip()]
    assert [row["trial_id"] for row in parsed] == [1, 2, 3]

    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.count() == 3
    assert reloaded.torn_lines_skipped == 0
    assert [e.trial_id for e in reloaded.all_entries()] == [1, 2, 3]


def test_midfile_corruption_raises(tmp_path: Path) -> None:
    # A bad line (2) followed by a good line (3) is NOT a torn tail: fatal.
    _shard(tmp_path).write_bytes(
        (
            _line(_entry(1))
            + "\n"
            + '{"trial_id": 2, "timestamp":'  # truncated / invalid JSON
            + "\n"
            + _line(_entry(3))
            + "\n"
        ).encode("utf-8")
    )

    with pytest.raises(ExperimentJournalCorruptError) as excinfo:
        ExperimentJournal(journal_dir=tmp_path)

    message = str(excinfo.value)
    assert "autopilot_journal.jsonl:2:" in message
    assert "scrub_journal.py" in message


def test_append_path_writes_newline_terminated_parseable_rows(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    journal.record(_entry(2))

    raw = _shard(tmp_path).read_bytes()
    assert raw.endswith(b"\n")
    lines = [ln for ln in raw.decode("utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    parsed = [json.loads(ln) for ln in lines]
    assert [row["trial_id"] for row in parsed] == [1, 2]


# ── D2: strict JSON at the serialization boundary ────────────────────────────


def _entry_with_eval_details(trial_id: int, eval_details: dict) -> JournalEntry:
    entry = _entry(trial_id)
    entry.eval_details = eval_details
    return entry


def _fail_on_bare_constant(token: str):  # pragma: no cover - only hit on failure
    raise AssertionError(f"bare non-finite JSON constant present: {token!r}")


def test_nan_in_eval_details_journaled_as_null_and_strict(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry_with_eval_details(
            1,
            {
                "ece": float("nan"),
                "nested": {"auroc": float("inf"), "neg": float("-inf")},
                "finite": 0.5,
            },
        )
    )

    raw = _shard(tmp_path).read_bytes()
    # No bare NaN / Infinity tokens: the shard is strict, jq-parseable JSON.
    assert b"NaN" not in raw
    assert b"Infinity" not in raw

    line = raw.decode("utf-8").strip()
    # Strict parse: parse_constant fires only for NaN/Infinity/-Infinity tokens.
    row = json.loads(line, parse_constant=_fail_on_bare_constant)
    assert row["eval_details"]["ece"] is None
    assert row["eval_details"]["nested"]["auroc"] is None
    assert row["eval_details"]["nested"]["neg"] is None
    assert row["eval_details"]["finite"] == 0.5


def test_legacy_bare_nan_shard_still_loads(tmp_path: Path) -> None:
    # A pre-D2 shard line carrying a bare NaN token (json.loads accepts it by
    # default) must still load without tripping the torn-tail / corruption paths.
    legacy_line = (
        '{"trial_id": 1, "timestamp": "2026-06-14T00:00:01Z", "species": "unit", '
        '"action_type": "seed_batch", "tier": 1, "quality": 1.0, "speed": 40.0, '
        '"cost": 0.2, "reliability": 0.9, "pareto_status": "frontier", '
        '"eval_details": {"ece": NaN}}\n'
    )
    _shard(tmp_path).write_text(legacy_line, encoding="utf-8")

    journal = ExperimentJournal(journal_dir=tmp_path)

    assert journal.count() == 1
    assert journal.torn_lines_skipped == 0
    loaded = journal.all_entries()[0]
    assert loaded.trial_id == 1
    assert math.isnan(loaded.eval_details["ece"])


# ── D3: gap-tolerant shard load ──────────────────────────────────────────────


def test_gap_tolerant_load_base_missing_shard_one_present(tmp_path: Path) -> None:
    # Only the rotated _1 shard exists (no base autopilot_journal.jsonl). The old
    # while-loop discovery broke at batch 0 and loaded nothing; journal_shards
    # finds _1 regardless.
    shard_one = tmp_path / "autopilot_journal_1.jsonl"
    shard_one.write_text(
        _line(_entry(1000)) + "\n" + _line(_entry(1001)) + "\n",
        encoding="utf-8",
    )

    journal = ExperimentJournal(journal_dir=tmp_path)

    assert journal.count() == 2
    assert [e.trial_id for e in journal.all_entries()] == [1000, 1001]

"""Append-only JSONL frame ledger.

Spec: docs/design/vidya-pilot-spec.md §11.0 (ratified 2026-08-09 -- JSONL is canonical, SQLite is
a rebuildable derived index).

This follows the house pattern rather than inventing one. The AutoKernel journal and the
experiment journal are both append-only JSONL with fsync-per-event and pure view rebuilds; three
of their hard-won behaviours are adopted here deliberately:

* **Acknowledged means fsynced.** `append` returns only after the record is on disk (and after the
  containing directory is synced when the file is new). A caller that got a sequence number can
  rely on it surviving a crash.
* **A torn tail is repaired loudly, not silently.** A crash can only leave a partial trailing
  line. The reader drops it; the next append truncates it and writes a `torn_append_discarded`
  record carrying the discarded byte count and hash -- so the loss is itself durable, rather than
  a gap nobody can see afterwards.
* **The record is the authority.** Nothing here mutates. Retraction and supersession are later
  frames (spec §3.5); this module has no update or delete path at all.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from canonical import canonical_bytes, content_hash

__all__ = ["Ledger", "LedgerRecord", "GENESIS_PREV_HASH", "LedgerIntegrityError"]

GENESIS_PREV_HASH = "sha256:" + "0" * 64


class LedgerIntegrityError(Exception):
    """The on-disk chain does not verify."""


@dataclass(frozen=True)
class LedgerRecord:
    """One line of the ledger: the frame plus the chain metadata that binds it in place."""

    seq: int
    prev_hash: str
    frame_hash: str
    frame: dict

    def to_line(self) -> bytes:
        return canonical_bytes(
            {
                "seq": self.seq,
                "prev_hash": self.prev_hash,
                "frame_hash": self.frame_hash,
                "frame": self.frame,
            }
        )

    @staticmethod
    def from_obj(obj: dict) -> "LedgerRecord":
        return LedgerRecord(
            seq=obj["seq"],
            prev_hash=obj["prev_hash"],
            frame_hash=obj["frame_hash"],
            frame=obj["frame"],
        )


def _link_hash(prev_hash: str, frame_hash: str, seq: int) -> str:
    """Chain link over (prev, frame, seq).

    Including the sequence number means a record cannot be silently relocated within the chain,
    only appended after the record it names.
    """
    return content_hash({"prev": prev_hash, "frame": frame_hash, "seq": seq})


class Ledger:
    """Append-only JSONL ledger over a single file.

    Single-writer by construction; the pilot has one writer and the spec defers multi-writer
    machinery entirely.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Append-time head cache. Without it `append` re-reads the whole file to find the tail,
        # which is O(n) per append and O(n^2) over a bulk ingest -- a 9,449-frame adapter run
        # would have parsed ~44M records. The cache is only trusted while the on-disk size matches
        # what this process last wrote, so an external writer or an interrupted append invalidates
        # it and the slow, correct path runs instead. Safe because the pilot is single-writer by
        # construction (spec §11.0) and the invalidation is conservative.
        self._cached_head: tuple[int, str] | None = None
        self._cached_size: int | None = None

    # -- reading ---------------------------------------------------------

    def read_all(self, *, repair_report: list | None = None) -> list[LedgerRecord]:
        """Read every intact record. A torn trailing line is dropped, not raised.

        If `repair_report` is provided, a description of any dropped tail is appended to it -- the
        caller decides whether that is worth surfacing, but it is never hidden.
        """
        if not self.path.exists():
            return []
        records: list[LedgerRecord] = []
        raw = self.path.read_bytes()
        if not raw:
            return []
        lines = raw.split(b"\n")
        # A well-formed file ends with a newline, so the final element is empty.
        trailing = lines.pop() if lines else b""
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                records.append(LedgerRecord.from_obj(json.loads(line)))
            except (json.JSONDecodeError, KeyError) as exc:
                if i == len(lines) - 1:
                    if repair_report is not None:
                        repair_report.append(
                            f"torn tail dropped at line {i + 1}: {len(line)} bytes, "
                            f"sha256:{hashlib.sha256(line).hexdigest()[:16]} ({exc})"
                        )
                    break
                raise LedgerIntegrityError(
                    f"{self.path}: corrupt record at line {i + 1} (not the tail): {exc}"
                ) from exc
        if trailing.strip():
            if repair_report is not None:
                repair_report.append(
                    f"torn tail dropped (no terminating newline): {len(trailing)} bytes, "
                    f"sha256:{hashlib.sha256(trailing).hexdigest()[:16]}"
                )
        return records

    def __iter__(self) -> Iterator[LedgerRecord]:
        return iter(self.read_all())

    def __len__(self) -> int:
        return len(self.read_all())

    def head(self) -> tuple[int, str]:
        """Return ``(last_seq, last_link_hash)``; ``(-1, GENESIS_PREV_HASH)`` when empty."""
        records = self.read_all()
        if not records:
            return -1, GENESIS_PREV_HASH
        last = records[-1]
        return last.seq, _link_hash(last.prev_hash, last.frame_hash, last.seq)

    # -- writing ---------------------------------------------------------

    def append(self, frame: dict, *, frame_hash: str | None = None) -> LedgerRecord:
        """Append one frame. Returns only after the bytes are fsynced."""
        is_new = not self.path.exists()
        cached = self._valid_cached_head()
        if cached is not None:
            record = self._record_after(cached, frame, frame_hash=frame_hash)
            self._write_record(record, sync_dir=is_new)
            return record

        repair: list[str] = []
        existing = self.read_all(repair_report=repair)

        if repair:
            self._truncate_to(existing)
            self._write_record(
                self._next_record(
                    existing,
                    {
                        "frame_type": "epyc.vidya/frame/torn_append_discarded/v1",
                        "assertion": {"discarded": repair},
                        "provenance": {"method": "ledger.append/torn-tail-repair"},
                        "pubinfo": {"actor": "vidya.ledger", "authority_scope": "ledger-maintenance"},
                    },
                ),
                sync_dir=is_new,
            )
            existing = self.read_all()

        record = self._next_record(existing, frame, frame_hash=frame_hash)
        self._write_record(record, sync_dir=is_new)
        return record

    def _valid_cached_head(self) -> tuple[int, str] | None:
        """Return the cached (seq, link_hash) only if the file is exactly as we left it."""
        if self._cached_head is None or self._cached_size is None:
            return None
        try:
            if self.path.stat().st_size != self._cached_size:
                self._cached_head = self._cached_size = None
                return None
        except FileNotFoundError:
            self._cached_head = self._cached_size = None
            return None
        return self._cached_head

    def _record_after(
        self, head: tuple[int, str], frame: dict, *, frame_hash: str | None = None
    ) -> LedgerRecord:
        seq, link = head
        return LedgerRecord(
            seq=seq + 1,
            prev_hash=link,
            frame_hash=frame_hash or content_hash(frame),
            frame=frame,
        )

    def _next_record(
        self, existing: list[LedgerRecord], frame: dict, *, frame_hash: str | None = None
    ) -> LedgerRecord:
        if existing:
            last = existing[-1]
            seq = last.seq + 1
            prev = _link_hash(last.prev_hash, last.frame_hash, last.seq)
        else:
            seq = 0
            prev = GENESIS_PREV_HASH
        return LedgerRecord(
            seq=seq,
            prev_hash=prev,
            frame_hash=frame_hash or content_hash(frame),
            frame=frame,
        )

    def _write_record(self, record: LedgerRecord, *, sync_dir: bool) -> None:
        with open(self.path, "ab") as fh:
            fh.write(record.to_line() + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._cached_head = (
            record.seq,
            _link_hash(record.prev_hash, record.frame_hash, record.seq),
        )
        self._cached_size = self.path.stat().st_size
        if sync_dir:
            dir_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

    def _truncate_to(self, records: list[LedgerRecord]) -> None:
        """Rewrite the file with exactly `records`, dropping any torn tail."""
        tmp = self.path.with_suffix(self.path.suffix + ".repair")
        with open(tmp, "wb") as fh:
            for rec in records:
                fh.write(rec.to_line() + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)
        self._cached_head = self._cached_size = None

    # -- integrity -------------------------------------------------------

    def verify(self) -> list[str]:
        """Verify sequence continuity, chain linkage, and frame hashes.

        Returns a list of problems; empty means the chain verifies. This is tamper-EVIDENT only --
        a rewriter who recomputes the whole chain leaves no trace here. Tamper-proofing for prior
        history comes from externally held checkpoints (see checkpoint.py).
        """
        problems: list[str] = []
        prev = GENESIS_PREV_HASH
        for i, rec in enumerate(self.read_all()):
            if rec.seq != i:
                problems.append(f"seq {rec.seq}: out of order (expected {i})")
            if rec.prev_hash != prev:
                problems.append(f"seq {rec.seq}: prev_hash does not chain to the previous record")
            actual = content_hash(rec.frame)
            if rec.frame_hash != actual:
                problems.append(f"seq {rec.seq}: frame_hash does not match the frame content")
            prev = _link_hash(rec.prev_hash, rec.frame_hash, rec.seq)
        return problems

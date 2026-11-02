"""In-memory attribution for one prospective online REPL shadow search.

The caller must execute the real searches and deliver the *next* open observed
in the same session. This helper never runs models, captures traffic, persists
records, or certifies event provenance. Overlap for a hidden arm is a
counterfactual span match, not evidence that the model saw or chose that arm.
Absence of a next open is unknown, not a negative observation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Mapping, Sequence

_HEX = re.compile(r"^[0-9a-f]{64}$")
_ARM = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$")
_SESSION = re.compile(r"^[0-9a-f]{16}$")


def _digest(value: str) -> None:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError("identity must be a SHA-256 digest")


def _session(value: str) -> None:
    if not isinstance(value, str) or not _SESSION.fullmatch(value):
        raise ValueError("invalid session")


def _timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Span:
    """Half-open character span over an identified immutable content version."""
    section_digest: str
    content_digest: str
    start: int
    end: int
    content_chars: int

    def __post_init__(self) -> None:
        _digest(self.section_digest)
        _digest(self.content_digest)
        if (any(type(v) is not int for v in (self.start, self.end, self.content_chars))
                or not 0 <= self.start < self.end <= self.content_chars):
            raise ValueError("invalid half-open content span")

    def overlaps(self, other: Span) -> bool:
        return (self.section_digest == other.section_digest
                and self.content_digest == other.content_digest
                and self.content_chars == other.content_chars
                and self.start < other.end and other.start < self.end)


class ShadowAttribution:
    """One search with ranked arms and at most its first subsequent session open."""

    def __init__(self, *, session: str, query_digest: str, searched_at: datetime,
                 rankings: Mapping[str, Sequence[Span]], shown_arm: str):
        _session(session)
        _digest(query_digest)
        stamp = _timestamp(searched_at)
        if not isinstance(rankings, Mapping) or not rankings or shown_arm not in rankings:
            raise ValueError("exactly one shown arm must be in nonempty rankings")
        copied = {}
        for arm, spans in rankings.items():
            if not isinstance(arm, str) or not _ARM.fullmatch(arm):
                raise ValueError("invalid arm identity")
            if not isinstance(spans, (tuple, list)) or any(not isinstance(s, Span) for s in spans):
                raise ValueError("rankings must contain span sequences")
            copied[arm] = tuple(spans)
        self.session = session
        self.query_digest = query_digest
        self.searched_at = stamp
        self.rankings = copied
        self.shown_arm = shown_arm
        self._open = None
        self._opened_at = None

    def observe_open(self, *, session: str, opened_at: datetime, span: Span) -> bool:
        """Record first later open for this session; unrelated sessions are ignored."""
        _session(session)
        stamp = _timestamp(opened_at)
        if not isinstance(span, Span):
            raise ValueError("invalid open span")
        if session != self.session:
            return False
        if stamp <= self.searched_at:
            raise ValueError("open must be strictly later than search")
        if self._open is not None:
            raise ValueError("first subsequent open already recorded")
        self._open, self._opened_at = span, stamp
        return True

    def result(self) -> dict:
        """Return ranked identities and tri-state overlap, with no raw text."""
        return {
            'session': self.session, 'query_digest': self.query_digest,
            'searched_at': self.searched_at.isoformat(), 'shown_arm': self.shown_arm,
            'opened_at': self._opened_at.isoformat() if self._opened_at else None,
            'arms': {arm: [{'rank': i, 'span': asdict(span),
                            'next_open_overlap': (None if self._open is None
                                                  else span.overlaps(self._open))}
                           for i, span in enumerate(spans, 1)]
                     for arm, spans in self.rankings.items()},
        }

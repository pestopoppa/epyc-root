"""SC17: the ledger refuses future-stamped frames at append time.

The fold stays pure (created_at is publication metadata it never reads); the
guard lives at the effectful append. Both directions are covered — refusal of
a future stamp AND acceptance of present/absent/malformed stamps — because a
guard tested only on its refusal path is indistinguishable from one that
refuses everything (tonight's standing lens).
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from ledger import FrameStampError, Ledger, MAX_FUTURE_SKEW_SECONDS  # noqa: E402


def _frame(created_at=None):
    pubinfo = {"actor": "test", "authority_scope": "test"}
    if created_at is not None:
        pubinfo["created_at"] = created_at
    return {
        "frame_type": "epyc.vidya/frame/test/v1",
        "assertion": {"k": "v"},
        "provenance": {"method": "test"},
        "pubinfo": pubinfo,
    }


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_future_stamp_refused(tmp_path):
    led = Ledger(tmp_path / "l.jsonl")
    future = _iso(datetime.now(timezone.utc) + timedelta(days=1))
    with pytest.raises(FrameStampError, match="SC17"):
        led.append(_frame(created_at=future))
    assert len(led) == 0, "a refused frame must leave no record"


def test_present_stamp_accepted(tmp_path):
    led = Ledger(tmp_path / "l.jsonl")
    rec = led.append(_frame(created_at=_iso(datetime.now(timezone.utc))))
    assert rec.seq == 0


def test_within_skew_accepted(tmp_path):
    led = Ledger(tmp_path / "l.jsonl")
    near = _iso(datetime.now(timezone.utc) + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS - 60))
    assert led.append(_frame(created_at=near)).seq == 0


def test_absent_stamp_tolerated(tmp_path):
    # Internal maintenance frames (torn-tail repair) carry no created_at;
    # stamp PRESENCE is frame-construction's contract, not the ledger's.
    led = Ledger(tmp_path / "l.jsonl")
    assert led.append(_frame(created_at=None)).seq == 0


def test_malformed_stamp_tolerated(tmp_path):
    led = Ledger(tmp_path / "l.jsonl")
    assert led.append(_frame(created_at="not-a-date")).seq == 0


def test_past_stamp_accepted_history_unaffected(tmp_path):
    # The 895 incident frames are HISTORY — this guard is forward-only by design.
    led = Ledger(tmp_path / "l.jsonl")
    old = _iso(datetime.now(timezone.utc) - timedelta(days=30))
    assert led.append(_frame(created_at=old)).seq == 0

"""Unit tests for src/behavior_signature.py (BSV-1 compute + BSV-2 diff severity)."""

from __future__ import annotations

import pytest

from src.behavior_signature import (
    compute_behavior_signature,
    diff_signatures,
    latency_bucket,
    normalized_answer_hash,
    token_bucket,
    DiffSeverity,
)
from src.trace import ensure_schema, insert_behavior_signature, latest_behavior_signature


# ─── bucketing ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ms,label",
    [
        (500, "<1s"),
        (1_000, "<1s"),
        (3_000, "1-5s"),
        (20_000, "5-30s"),
        (90_000, "30-120s"),
        (500_000, ">120s"),
        (None, "unknown"),
    ],
)
def test_latency_buckets(ms, label) -> None:
    assert latency_bucket(ms) == label


@pytest.mark.parametrize(
    "n,label",
    [
        (500, "<1k"),
        (2_000, "1-4k"),
        (10_000, "4-16k"),
        (50_000, "16-64k"),
        (200_000, ">64k"),
    ],
)
def test_token_buckets(n, label) -> None:
    assert token_bucket(n) == label


# ─── compute ─────────────────────────────────────────────────────────────────────


def test_compute_signature_deterministic() -> None:
    kwargs = dict(
        archive_member_id="cfg-A",
        trial_id=1,
        sentinel_outcomes={"q1": "pass", "q2": "fail"},
        route_path=["frontdoor", "coder"],
        tool_sequence=["read", "edit", "test"],
        escalation_path=["worker", "coder"],
        latency_ms=4000,
        total_tokens=8000,
    )
    s1 = compute_behavior_signature(**kwargs)
    s2 = compute_behavior_signature(**kwargs)
    assert s1.signature_hash == s2.signature_hash  # deterministic
    assert s1.latency_bucket == "1-5s"
    assert s1.token_bucket == "4-16k"
    assert s1.route_path_hash and s1.tool_sequence_hash and s1.escalation_path_hash


def test_compute_signature_changes_with_behavior() -> None:
    base = dict(
        archive_member_id="A",
        sentinel_outcomes={"q1": "pass"},
        tool_sequence=["read", "edit"],
        latency_ms=1000,
        total_tokens=1000,
    )
    s1 = compute_behavior_signature(**base)
    s2 = compute_behavior_signature(**{**base, "tool_sequence": ["read", "edit", "web_search"]})
    assert s1.signature_hash != s2.signature_hash


def test_normalized_answer_hash_ignores_case_and_whitespace() -> None:
    assert normalized_answer_hash("  Final\nAnswer\t42  ") == normalized_answer_hash(
        "final answer 42"
    )
    assert normalized_answer_hash("") is None


def test_compute_signature_aggregates_per_question_answer_hashes() -> None:
    answer_hashes = {
        "q2": normalized_answer_hash("Second answer"),
        "q1": normalized_answer_hash("First answer"),
    }

    sig = compute_behavior_signature(
        archive_member_id="A",
        sentinel_outcomes={"q1": "pass", "q2": "pass"},
        answer_hashes=answer_hashes,
    )
    reordered = compute_behavior_signature(
        archive_member_id="A",
        sentinel_outcomes={"q1": "pass", "q2": "pass"},
        answer_hashes=dict(reversed(list(answer_hashes.items()))),
    )
    changed = compute_behavior_signature(
        archive_member_id="A",
        sentinel_outcomes={"q1": "pass", "q2": "pass"},
        answer_hashes={**answer_hashes, "q2": normalized_answer_hash("Different")},
    )

    assert sig.answer_hash
    assert sig.answer_hash == reordered.answer_hash
    assert sig.signature_hash == reordered.signature_hash
    assert sig.answer_hash != changed.answer_hash
    assert sig.signature_hash != changed.signature_hash


def test_trace_ids_do_not_change_behavior_hash() -> None:
    base = dict(
        archive_member_id="A",
        trial_id=5,
        sentinel_outcomes={"q1": "pass"},
        route_path=["frontdoor"],
        latency_ms=1000,
        total_tokens=1000,
    )

    s1 = compute_behavior_signature(**base, event_id=101, harness_metrics_id=201)
    s2 = compute_behavior_signature(**base, event_id=102, harness_metrics_id=202)

    assert s1.event_id == 101
    assert s2.event_id == 102
    assert s1.signature_hash == s2.signature_hash


def test_signature_persists_via_shared_schema(tmp_path) -> None:
    conn = ensure_schema(tmp_path / "e.sqlite")
    sig = compute_behavior_signature(
        archive_member_id="cfg-Z",
        trial_id=5,
        event_id=99,
        sentinel_outcomes={"q": "pass"},
        latency_ms=2000,
    )
    rid = insert_behavior_signature(conn, sig)
    assert rid > 0
    latest = latest_behavior_signature(conn, "cfg-Z")
    assert latest["event_id"] == 99
    assert latest["latency_bucket"] == "1-5s"
    conn.close()


# ─── diff severity ───────────────────────────────────────────────────────────────


def _sig(**kw):
    base = dict(
        archive_member_id="A",
        sentinel_outcomes={"q1": "pass"},
        route_path=["frontdoor"],
        tool_sequence=["read"],
        escalation_path=["worker"],
        latency_ms=1000,
        total_tokens=1000,
    )
    base.update(kw)
    return compute_behavior_signature(**base)


def test_diff_identical_is_benign() -> None:
    sev, reasons = diff_signatures(_sig(), _sig())
    assert sev == DiffSeverity.BENIGN
    assert "no material" in reasons[0]


def test_diff_regression_is_blocking() -> None:
    old = _sig(sentinel_outcomes={"q1": "pass", "q2": "pass"})
    new = _sig(sentinel_outcomes={"q1": "pass", "q2": "fail"})
    sev, reasons = diff_signatures(old, new)
    assert sev == DiffSeverity.BLOCKING
    assert any("regressed" in r for r in reasons)


def test_diff_forbidden_shortcut_is_blocking() -> None:
    old = _sig(sentinel_outcomes={"q1": "pass"})
    new = _sig(sentinel_outcomes={"q1": "pass_via_shortcut"})
    sev, reasons = diff_signatures(old, new)
    assert sev == DiffSeverity.BLOCKING
    assert any("shortcut" in r for r in reasons)


def test_diff_path_change_is_watch() -> None:
    old = _sig(tool_sequence=["read"])
    new = _sig(tool_sequence=["read", "edit", "test"])  # same outcomes, different tools
    sev, reasons = diff_signatures(old, new)
    assert sev == DiffSeverity.WATCH
    assert any("tool_sequence_hash changed" in r for r in reasons)


def test_diff_cost_guardrail_blocking_vs_watch() -> None:
    old = _sig(latency_ms=500)  # <1s (idx 0)
    minor = _sig(latency_ms=3000)  # 1-5s (idx 1) — 1 bucket worse → watch
    major = _sig(latency_ms=90_000)  # 30-120s (idx 3) — 3 buckets worse → blocking
    assert diff_signatures(old, minor)[0] == DiffSeverity.WATCH
    assert diff_signatures(old, major)[0] == DiffSeverity.BLOCKING
    # faster is not penalized
    assert diff_signatures(major, old)[0] != DiffSeverity.BLOCKING


def test_diff_partial_confidence_cannot_be_benign() -> None:
    old = _sig()
    new = _sig(signature_confidence="partial")
    sev, reasons = diff_signatures(old, new)
    assert sev == DiffSeverity.WATCH
    assert any("partial-confidence" in r for r in reasons)


def test_diff_accepts_dict_inputs() -> None:
    # journal-backfilled rows arrive as dicts (e.g. from sqlite) — diff must handle them
    old = {
        "sentinel_outcomes": '{"q1": "pass"}',
        "latency_bucket": "<1s",
        "token_bucket": "<1k",
        "route_path_hash": "a",
        "tool_sequence_hash": "b",
        "escalation_path_hash": "c",
        "signature_confidence": "full",
    }
    new = {
        "sentinel_outcomes": {"q1": "fail"},
        "latency_bucket": "<1s",
        "token_bucket": "<1k",
        "route_path_hash": "a",
        "tool_sequence_hash": "b",
        "escalation_path_hash": "c",
        "signature_confidence": "full",
    }
    sev, _ = diff_signatures(old, new)
    assert sev == DiffSeverity.BLOCKING

"""A timed-out bench leg must never become a contention ratio.

ORIGIN. Found 2026-08-12 while dry-running the OP-21 overlapping contention
re-bench BEFORE spending a post-reboot window on it.

`_http_bench` returns `(0.0, 0.0)` on timeout or HTTP error. That sentinel is
not a measurement of zero throughput, and the aggregate arithmetic could not
tell them apart:

    total_tokens = N_PREDICT * 2                 # counts BOTH legs
    par_time     = max(par_a_el, par_b_el)       # DISCARDS the failed leg

A failed leg contributes 0.0, so `max()` returns the surviving leg's elapsed
time while `total_tokens` still counts tokens the failed leg never generated.
`par_agg` is inflated, so `ratio` is inflated, so the verdict moves toward
`allow`.

THE BIAS RUNS THE WRONG WAY, which is what makes it worth a test rather than a
comment. The arithmetic reports contention as most benign exactly when a server
is collapsing under load — when it is least benign. And it fires hardest on the
measurement most likely to be trusted: a 2x48-thread OVERLAPPING pair on 48
physical cores is precisely the regime where the 180 s timeout bites.

The module already refused to treat HTTP failures as throughput evidence in its
pre-flight health check ("HTTP failures are not throughput evidence"). This
extends the identical rule to the bench legs, in BOTH sites — `_bench_pair` and
`_bench_nway`. The n-way one matters most: it is the path the OP-21 re-bench is
supposed to use, and having more legs means more chances for one to time out.
"""
from __future__ import annotations

import pytest

import scripts.server.contention_matrix as cm


def test_a_timed_out_leg_is_reported_as_unmeasured() -> None:
    """The (0.0, 0.0) sentinel must be recognised, on tps or elapsed alike."""
    assert cm._unmeasured_legs({"a": (0.0, 0.0)}) == ["a"]
    assert cm._unmeasured_legs({"a": (12.0, 0.0)}) == ["a"], "zero elapsed is unmeasured"
    assert cm._unmeasured_legs({"a": (0.0, 5.0)}) == ["a"], "zero tps is unmeasured"
    assert cm._unmeasured_legs({"a": (12.0, 5.0)}) == []
    # A merely SLOW leg is a real measurement and must survive — the refusal
    # must not swallow the very contention signal it exists to protect.
    assert cm._unmeasured_legs({"a": (0.7, 180.0)}) == []


def test_bench_pair_refuses_instead_of_inflating_the_ratio(monkeypatch) -> None:
    """The decisive case: one parallel leg times out.

    Pre-fix this returned a confident ratio with verdict `allow`. It must now
    raise instead.
    """
    calls = {"n": 0}

    def fake_http_bench(port, n_predict=None, *, safe_sampling=False):
        calls["n"] += 1
        # legs 1,2 = solo (both fine); leg 3 = parallel A fine; leg 4 = parallel B TIMES OUT
        if calls["n"] == 4:
            return (0.0, 0.0)
        return (20.0, 5.0)

    monkeypatch.setattr(cm, "_http_bench", fake_http_bench)

    with pytest.raises(cm.UnmeasuredLegError) as exc:
        cm._bench_pair("frontdoor", 8080, "ingest_long_context", 8185)

    assert "ingest_long_context:8185" in str(exc.value)
    assert "not zero throughput" in str(exc.value)


def test_bench_pair_still_measures_a_healthy_pair(monkeypatch) -> None:
    """Guard against a refusal so broad it forbids the compliant path too."""
    monkeypatch.setattr(
        cm, "_http_bench",
        lambda port, n_predict=None, *, safe_sampling=False: (20.0, 5.0),
    )
    pb = cm._bench_pair("frontdoor", 8080, "ingest_long_context", 8185)
    assert pb.ratio > 0
    assert pb.seq_aggregate_tps > 0
    assert pb.parallel_aggregate_tps > 0


def test_bench_nway_refuses_too(monkeypatch) -> None:
    """The n-way site is the OP-21 path — it must carry the same refusal."""
    calls = {"n": 0}

    def fake_http_bench(port, n_predict=None, *, safe_sampling=False):
        calls["n"] += 1
        if calls["n"] == 4:  # one leg of the concurrent phase
            return (0.0, 0.0)
        return (20.0, 5.0)

    monkeypatch.setattr(cm, "_http_bench", fake_http_bench)

    with pytest.raises(cm.UnmeasuredLegError):
        cm._bench_nway([("frontdoor", 8080), ("ingest_long_context", 8185)], samples=1)


def test_bench_nway_still_measures_a_healthy_set(monkeypatch) -> None:
    """Compliant-path guard for the n-way site."""
    monkeypatch.setattr(
        cm, "_http_bench",
        lambda port, n_predict=None, *, safe_sampling=False: (20.0, 5.0),
    )
    out = cm._bench_nway(
        [("frontdoor", 8080), ("ingest_long_context", 8185)], samples=1
    )
    assert out["ratio"] > 0

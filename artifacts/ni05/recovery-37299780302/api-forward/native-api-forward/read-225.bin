"""Unit tests for the dashboard freshness contract (dashboard_freshness.py)."""
from __future__ import annotations

from src.api.routes.dashboard_freshness import (
    AGING,
    COHERENT,
    DEAD,
    DIVERGENT,
    FRESH,
    STALE,
    Source,
    classify,
    envelope,
    source_status,
    stamp,
    value_consistency,
)

NOW = 1_000_000.0


def test_classify_thresholds():
    assert classify(0.0, warn_s=10, stale_s=60) == FRESH
    assert classify(9.9, warn_s=10, stale_s=60) == FRESH
    assert classify(10.0, warn_s=10, stale_s=60) == AGING
    assert classify(59.9, warn_s=10, stale_s=60) == AGING
    assert classify(60.0, warn_s=10, stale_s=60) == STALE
    assert classify(9999.0, warn_s=10, stale_s=60) == STALE


def test_classify_missing_source():
    # A required source that is absent is DEAD; an optional absent one is FRESH.
    assert classify(None, 10, 60, present=False) == DEAD
    assert classify(None, 10, 60, present=False, optional=True) == FRESH
    # present=True but no age (shouldn't normally happen) -> DEAD (required).
    assert classify(None, 10, 60, present=True) == DEAD


def test_source_status_present_and_fresh():
    st = source_status(Source("tap", NOW - 3.0, warn_s=10, stale_s=60), now=NOW)
    assert st["class"] == FRESH
    assert st["age_s"] == 3.0
    assert st["mtime"] == NOW - 3.0


def test_source_status_absent_is_dead():
    st = source_status(Source("phase", None, warn_s=10, stale_s=60), now=NOW)
    assert st["class"] == DEAD
    assert st["age_s"] is None
    assert st["mtime"] is None


def test_source_status_future_mtime_clamped_to_zero():
    # Clock skew: a file stamped in the future must not read as negative age.
    st = source_status(Source("skew", NOW + 5.0, warn_s=10, stale_s=60), now=NOW)
    assert st["age_s"] == 0.0
    assert st["class"] == FRESH


def test_envelope_worst_source_wins():
    env = envelope(
        [
            Source("live", NOW - 1.0, warn_s=10, stale_s=60),       # fresh
            Source("laggy", NOW - 15.0, warn_s=10, stale_s=60),     # aging
            Source("dead-producer", NOW - 999.0, warn_s=10, stale_s=60),  # stale
        ],
        now=NOW,
    )
    assert env["staleness_class"] == STALE
    assert "dead-producer" in env["reason"]
    assert env["worst_age_s"] == 999.0
    assert len(env["sources"]) == 3


def test_envelope_dead_beats_stale():
    env = envelope(
        [
            Source("stale-one", NOW - 999.0, warn_s=10, stale_s=60),
            Source("missing-one", None, warn_s=10, stale_s=60),
        ],
        now=NOW,
    )
    assert env["staleness_class"] == DEAD
    assert "missing-one" in env["reason"]


def test_envelope_all_fresh_has_empty_reason():
    env = envelope([Source("a", NOW - 1, 10, 60), Source("b", NOW - 2, 10, 60)], now=NOW)
    assert env["staleness_class"] == FRESH
    assert env["reason"] == ""


def test_optional_absent_source_ignored():
    env = envelope(
        [
            Source("main", NOW - 1.0, warn_s=10, stale_s=60),
            Source("lockfile", None, warn_s=10, stale_s=60, optional=True),
        ],
        now=NOW,
    )
    assert env["staleness_class"] == FRESH


def test_informational_source_does_not_gate_the_badge():
    # A week-old informational backing file next to a fresh gating stream must
    # leave the panel FRESH (the region_locks / inference_tap false-alarm class).
    env = envelope(
        [
            Source("live_stream", NOW - 0.1, warn_s=120, stale_s=600),           # gating, fresh
            Source("matrix", NOW - 600_000.0, warn_s=3600, stale_s=86400, gating=False),  # week-old, informational
        ],
        now=NOW,
    )
    assert env["staleness_class"] == FRESH
    assert env["reason"] == ""
    # worst_age reflects only gating sources
    assert env["worst_age_s"] == 0.1
    # ...but the informational source is still reported for UI context.
    labels = {s["label"]: s for s in env["sources"]}
    assert labels["matrix"]["class"] == STALE
    assert labels["matrix"]["gating"] is False


def test_all_informational_sources_yields_fresh_live_panel():
    # A live panel whose only sources are informational is FRESH by construction.
    env = envelope(
        [Source("stack_state", NOW - 4661.0, warn_s=3600, stale_s=86400, gating=False)],
        now=NOW,
    )
    assert env["staleness_class"] == FRESH
    assert env["worst_age_s"] is None


def test_gating_source_still_flips_badge():
    env = envelope(
        [
            Source("stream_a", NOW - 999.0, warn_s=120, stale_s=600),  # gating, stale
            Source("info", NOW - 1.0, warn_s=120, stale_s=600, gating=False),
        ],
        now=NOW,
    )
    assert env["staleness_class"] == STALE
    assert "stream_a" in env["reason"]


def test_stamp_is_additive_and_preserves_generated_at():
    payload = {"nodes": [1, 2, 3], "generated_at": NOW}
    out = stamp(payload, [Source("topo", NOW - 2.0, 10, 60)], now=NOW)
    assert out is payload  # in place
    assert out["nodes"] == [1, 2, 3]  # untouched
    assert out["_freshness"]["generated_at"] == NOW
    assert out["_freshness"]["staleness_class"] == FRESH


# --- H5: VALUE-consistency (a separate axis from age-staleness) ---------------


def test_value_consistency_journal_ahead_is_divergent():
    # trial_counter=100 while the journal already holds trial 105 -> the state
    # file is stale relative to the append-only journal: DIVERGENT.
    vc = value_consistency(100, 105)
    assert vc["class"] == DIVERGENT
    assert vc["trial_counter"] == 100
    assert vc["journal_max_trial"] == 105
    assert vc["trial_lag"] == 5
    assert "lags" in vc["reason"]


def test_value_consistency_equal_is_coherent():
    vc = value_consistency(100, 100)
    assert vc["class"] == COHERENT
    assert vc["trial_lag"] == 0
    assert vc["reason"] == ""


def test_value_consistency_state_ahead_of_journal_is_coherent():
    # The journal is sparse (metric-bearing trials only), so trial_counter
    # legitimately runs AHEAD of the journal max -> NOT flagged.
    vc = value_consistency(105, 100)
    assert vc["class"] == COHERENT
    assert vc["trial_lag"] == -5


def test_value_consistency_within_tolerance_is_coherent():
    # A one-trial journal-ahead race (row appended just before the counter bump)
    # is absorbed by the default tolerance.
    assert value_consistency(100, 101)["class"] == COHERENT
    # ...but a two-trial journal-ahead lag exceeds the default tolerance of 1.
    assert value_consistency(100, 102)["class"] == DIVERGENT


def test_value_consistency_missing_values_are_coherent():
    assert value_consistency(None, 105)["class"] == COHERENT
    assert value_consistency(100, None)["class"] == COHERENT
    assert value_consistency(None, None)["class"] == COHERENT


def test_envelope_attaches_value_consistency_when_provided():
    vc = value_consistency(100, 105)
    env = envelope([Source("state", NOW - 1.0, 300, 1800)], now=NOW, consistency=vc)
    # A DIVERGENT value verdict is a SEPARATE axis: the age class stays FRESH
    # (the file was just written) while consistency_class flags the divergence.
    assert env["staleness_class"] == FRESH
    assert env["consistency_class"] == DIVERGENT
    assert env["value_consistency"]["trial_lag"] == 5


def test_envelope_omits_consistency_keys_by_default():
    # Existing panels that pass no consistency verdict keep their envelope shape.
    env = envelope([Source("a", NOW - 1, 10, 60)], now=NOW)
    assert "value_consistency" not in env
    assert "consistency_class" not in env

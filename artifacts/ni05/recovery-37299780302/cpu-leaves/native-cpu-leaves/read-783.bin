"""Tests for session_log.py — TurnRecord, ConsolidatedSegment, two-level condensation,
SegmentCache, helpfulness scoring, process rewards, compaction profiles."""

import time

import pytest

from src.graph.session_log import (
    ConsolidatedSegment,
    SegmentCache,
    RewardSignals,
    CompactionProfile,
    CompactionQualityMonitor,
    build_turn_record,
    build_granular_summary,
    should_consolidate,
    build_consolidation_prompt,
    build_session_summary_deterministic,
    extract_identifiers,
    compute_reference_overlap,
    segment_helpfulness,
    prioritized_compaction,
    segment_advantage,
    compute_reward_signals,
    get_compaction_profile,
    COMPACTION_PROFILES,
    DEFAULT_COMPACTION_PROFILE,
    MAX_GRANULAR_BLOCKS,
)


# ---------------------------------------------------------------------------
# TurnRecord basics
# ---------------------------------------------------------------------------


def test_build_turn_record_ok():
    rec = build_turn_record(turn=1, role="frontdoor", code="x = 1", output="1")
    assert rec.outcome == "ok"
    assert rec.code_hash
    assert rec.code_line_count == 1


def test_build_turn_record_error():
    rec = build_turn_record(turn=2, role="coder", error="NameError: x")
    assert rec.outcome == "error"
    assert "NameError" in rec.error_message


def test_build_turn_record_final():
    rec = build_turn_record(turn=3, role="frontdoor", is_final=True, output="42")
    assert rec.outcome == "final"


def test_build_turn_record_escalation():
    rec = build_turn_record(turn=4, role="frontdoor", escalation_target="coder")
    assert rec.outcome == "escalation"


def test_to_log_line():
    rec = build_turn_record(turn=1, role="frontdoor", code="x=1", output="1")
    line = rec.to_log_line()
    assert "T1(frontdoor)" in line
    assert "ok" in line


def test_to_markdown_block():
    rec = build_turn_record(turn=1, role="coder", code="print(1)", output="1")
    md = rec.to_markdown_block()
    assert "### Turn 1" in md
    assert "coder" in md


# ---------------------------------------------------------------------------
# ConsolidatedSegment
# ---------------------------------------------------------------------------


def test_consolidated_segment_serialization():
    seg = ConsolidatedSegment(
        turn_range=(1, 5),
        granular_blocks=["T1 ok", "T2 ok", "T3 error"],
        consolidated="Turns 1-5: tried X, failed at Y, succeeded with Z.",
        trigger="escalation",
        timestamp=time.time(),
    )
    d = seg.to_dict()
    restored = ConsolidatedSegment.from_dict(d)
    assert restored.turn_range == (1, 5)
    assert restored.consolidated == seg.consolidated
    assert restored.trigger == "escalation"
    assert len(restored.granular_blocks) == 3


def test_consolidated_segment_prompt_block():
    seg = ConsolidatedSegment(
        turn_range=(3, 8),
        granular_blocks=[],
        consolidated="Dense summary here.",
        trigger="block_limit",
    )
    block = seg.to_prompt_block()
    assert "[Turns 3-8" in block
    assert "Dense summary here." in block


# ---------------------------------------------------------------------------
# Granular summary (Tier 1)
# ---------------------------------------------------------------------------


def test_build_granular_summary():
    rec = build_turn_record(turn=1, role="frontdoor", code="x=1", output="1")
    summary = build_granular_summary(rec)
    assert "T1(frontdoor)" in summary
    assert "ok" in summary


# ---------------------------------------------------------------------------
# Consolidation triggers
# ---------------------------------------------------------------------------


def test_should_consolidate_escalation():
    rec = build_turn_record(turn=5, role="coder", escalation_target="architect")
    trigger = should_consolidate(["b1", "b2"], rec)
    assert trigger == "escalation"


def test_should_consolidate_role_change():
    rec = build_turn_record(turn=5, role="coder", output="ok")
    trigger = should_consolidate(["b1", "b2"], rec, prev_role="frontdoor")
    assert trigger == "escalation"


def test_should_consolidate_final():
    rec = build_turn_record(turn=5, role="frontdoor", is_final=True, output="42")
    trigger = should_consolidate(["b1"], rec)
    assert trigger == "final"


def test_should_consolidate_block_limit():
    blocks = [f"block_{i}" for i in range(MAX_GRANULAR_BLOCKS)]
    rec = build_turn_record(turn=20, role="frontdoor", output="ok")
    trigger = should_consolidate(blocks, rec)
    assert trigger == "block_limit"


def test_should_consolidate_none():
    rec = build_turn_record(turn=3, role="frontdoor", output="ok")
    trigger = should_consolidate(["b1", "b2"], rec, prev_role="frontdoor")
    assert trigger is None


# ---------------------------------------------------------------------------
# Consolidation prompt
# ---------------------------------------------------------------------------


def test_build_consolidation_prompt():
    blocks = ["T1 ok code:abc", "T2 error err:NameError", "T3 ok"]
    prompt = build_consolidation_prompt(blocks)
    assert "3 entries" in prompt
    assert "T2 error" in prompt
    assert "worker_explore" not in prompt


# ---------------------------------------------------------------------------
# Deterministic summary (existing)
# ---------------------------------------------------------------------------


def test_build_session_summary_deterministic_empty():
    assert build_session_summary_deterministic([]) == ""


def test_build_session_summary_deterministic_few():
    records = [
        build_turn_record(turn=i, role="frontdoor", output=f"out{i}")
        for i in range(3)
    ]
    summary = build_session_summary_deterministic(records)
    assert "Session History" in summary
    assert "Turns: 3" in summary


def test_build_session_summary_deterministic_many():
    records = [
        build_turn_record(turn=i, role="frontdoor", output=f"out{i}")
        for i in range(10)
    ]
    summary = build_session_summary_deterministic(records)
    assert "omitted" in summary


# ---------------------------------------------------------------------------
# SegmentCache (CF Phase 1+)
# ---------------------------------------------------------------------------


def test_segment_cache_insert_lookup():
    cache = SegmentCache()
    blocks = ["T1(frontdoor) ok", "T2(frontdoor) error"]
    cache.insert(blocks, "Turns 1-2: tried X, failed.")
    result = cache.lookup(blocks)
    assert result == "Turns 1-2: tried X, failed."


def test_segment_cache_miss():
    cache = SegmentCache()
    assert cache.lookup(["T1(frontdoor) ok"]) is None
    assert cache._misses == 1
    assert cache._hits == 0


def test_segment_cache_normalization():
    cache = SegmentCache()
    blocks_a = ["  T1(frontdoor) OK  ", "T2(coder) error"]
    blocks_b = ["T1(frontdoor) ok", "T2(coder) error"]  # same after normalize
    cache.insert(blocks_a, "consolidated text")
    assert cache.lookup(blocks_b) == "consolidated text"


def test_segment_cache_eviction():
    cache = SegmentCache(max_size=3)
    for i in range(4):
        cache.insert([f"block_{i}"], f"consolidated_{i}")
    # First entry should be evicted
    assert cache.lookup(["block_0"]) is None
    assert cache.lookup(["block_3"]) == "consolidated_3"


def test_segment_cache_hit_rate():
    cache = SegmentCache()
    cache.insert(["a"], "A")
    cache.lookup(["a"])  # hit
    cache.lookup(["b"])  # miss
    assert cache.hit_rate == pytest.approx(0.5)


def test_segment_cache_serialization():
    cache = SegmentCache(max_size=32)
    cache.insert(["a", "b"], "AB")
    cache._hits = 5
    cache._misses = 3
    d = cache.to_dict()
    restored = SegmentCache.from_dict(d)
    assert restored.lookup(["a", "b"]) == "AB"
    assert restored._max_size == 32
    # Note: hits/misses are restored from serialized state, then +1 from lookup
    assert restored._hits == 5 + 1


# ---------------------------------------------------------------------------
# Extract identifiers (CF Phase 2c)
# ---------------------------------------------------------------------------


def test_extract_identifiers_paths():
    ids = extract_identifiers("Modified /src/graph/helpers.py and ran tests")
    assert "/src/graph/helpers.py" in ids


def test_extract_identifiers_dotted():
    ids = extract_identifiers("Called src.graph.session_log module")
    assert "src.graph.session_log" in ids


def test_extract_identifiers_functions():
    ids = extract_identifiers("The build_turn_record() function is correct")
    assert "build_turn_record()" in ids


def test_extract_identifiers_camelcase():
    ids = extract_identifiers("Created ConsolidatedSegment and TaskState")
    assert "ConsolidatedSegment" in ids
    assert "TaskState" in ids


# ---------------------------------------------------------------------------
# Reference overlap (CF Phase 2c)
# ---------------------------------------------------------------------------


def test_compute_reference_overlap_identical():
    text = "Modified /src/foo.py and called bar.baz()"
    overlap = compute_reference_overlap(text, text)
    assert overlap == pytest.approx(1.0)


def test_compute_reference_overlap_disjoint():
    overlap = compute_reference_overlap(
        "alpha.beta.gamma",
        "delta.epsilon.zeta",
    )
    assert overlap == pytest.approx(0.0)


def test_compute_reference_overlap_partial():
    seg = "Modified src.graph.helpers and src.config.models"
    recent = "Checking src.graph.helpers and src.features"
    overlap = compute_reference_overlap(seg, recent)
    assert 0.0 < overlap < 1.0


# ---------------------------------------------------------------------------
# Helpfulness scoring (CF Phase 2c)
# ---------------------------------------------------------------------------


def test_segment_helpfulness_recent_higher():
    """Recent segments should score higher than old ones."""
    seg_recent = ConsolidatedSegment(
        turn_range=(18, 20), granular_blocks=["T18 ok", "T20 ok"],
        consolidated="Recent work.", trigger="block_limit",
    )
    seg_old = ConsolidatedSegment(
        turn_range=(1, 3), granular_blocks=["T1 ok", "T3 ok"],
        consolidated="Old work.", trigger="block_limit",
    )
    score_recent = segment_helpfulness(seg_recent, current_turn=20)
    score_old = segment_helpfulness(seg_old, current_turn=20)
    assert score_recent > score_old


def test_segment_helpfulness_sensitive_boosted():
    """Segments with WARNING/CRITICAL content should score higher."""
    seg_normal = ConsolidatedSegment(
        turn_range=(5, 7), granular_blocks=["T5 ok"],
        consolidated="Normal work done.", trigger="block_limit",
    )
    seg_sensitive = ConsolidatedSegment(
        turn_range=(5, 7), granular_blocks=["T5 ok"],
        consolidated="WARNING: credential leak detected.", trigger="block_limit",
    )
    score_normal = segment_helpfulness(seg_normal, current_turn=10)
    score_sensitive = segment_helpfulness(seg_sensitive, current_turn=10)
    assert score_sensitive > score_normal


def test_prioritized_compaction_ordering():
    """Least helpful segments should come first."""
    old_seg = ConsolidatedSegment(
        turn_range=(1, 2), granular_blocks=["T1 silent"],
        consolidated="Nothing happened.", trigger="block_limit",
    )
    recent_seg = ConsolidatedSegment(
        turn_range=(18, 20), granular_blocks=["T18 final"],
        consolidated="Task completed successfully with FINAL.", trigger="final",
    )
    ordered = prioritized_compaction([recent_seg, old_seg], current_turn=20)
    # Old silent segment should be first (least helpful)
    assert ordered[0].turn_range == (1, 2)


# ---------------------------------------------------------------------------
# Process reward telemetry (CF Phase 3a)
# ---------------------------------------------------------------------------


def test_turn_record_new_fields_defaults():
    rec = build_turn_record(turn=1, role="frontdoor", output="ok")
    assert rec.token_budget_ratio == 0.0
    assert rec.on_scope is True
    assert rec.tool_success_ratio == 1.0


def test_turn_record_new_fields_set():
    rec = build_turn_record(
        turn=1, role="frontdoor", output="ok",
        token_budget_ratio=0.75, on_scope=False, tool_success_ratio=0.5,
    )
    assert rec.token_budget_ratio == 0.75
    assert rec.on_scope is False
    assert rec.tool_success_ratio == 0.5


def test_segment_advantage_all_ok():
    records = [
        build_turn_record(turn=i, role="frontdoor", output=f"out{i}")
        for i in range(3)
    ]
    adv = segment_advantage(records)
    assert adv > 0  # all ok = positive advantage


def test_segment_advantage_all_error():
    records = [
        build_turn_record(turn=i, role="frontdoor", error="fail")
        for i in range(3)
    ]
    adv = segment_advantage(records)
    assert adv < 0  # all error = negative advantage


def test_segment_advantage_empty():
    assert segment_advantage([]) == 0.0


def test_compute_reward_signals_basic():
    records = [
        build_turn_record(
            turn=1, role="frontdoor", output="ok",
            token_budget_ratio=0.5, tool_success_ratio=0.8,
        ),
        build_turn_record(
            turn=2, role="frontdoor", output="ok",
            token_budget_ratio=0.3, tool_success_ratio=1.0,
        ),
    ]
    signals = compute_reward_signals(records)
    assert signals.avg_token_budget_ratio == pytest.approx(0.4)
    assert signals.scope_adherence == pytest.approx(1.0)  # both on_scope=True
    assert signals.avg_tool_success == pytest.approx(0.9)
    assert signals.advantage > 0  # both ok


def test_reward_signals_serialization():
    sig = RewardSignals(
        avg_token_budget_ratio=0.6,
        scope_adherence=0.8,
        avg_tool_success=0.9,
        advantage=1.5,
    )
    d = sig.to_dict()
    restored = RewardSignals.from_dict(d)
    assert restored.avg_token_budget_ratio == pytest.approx(0.6)
    assert restored.advantage == pytest.approx(1.5)


def test_consolidated_segment_with_rewards():
    """ConsolidatedSegment serialization with reward_signals."""
    sig = RewardSignals(advantage=0.75)
    seg = ConsolidatedSegment(
        turn_range=(1, 5),
        granular_blocks=["T1 ok"],
        consolidated="Summary.",
        trigger="final",
        reward_signals=sig,
    )
    d = seg.to_dict()
    assert "reward_signals" in d
    restored = ConsolidatedSegment.from_dict(d)
    assert restored.reward_signals is not None
    assert restored.reward_signals.advantage == pytest.approx(0.75)


def test_consolidated_segment_without_rewards_backward_compat():
    """Old checkpoints without reward_signals should deserialize cleanly."""
    d = {
        "turn_range": [1, 5],
        "granular_blocks": ["T1 ok"],
        "consolidated": "Summary.",
        "trigger": "final",
    }
    seg = ConsolidatedSegment.from_dict(d)
    assert seg.reward_signals is None


# ---------------------------------------------------------------------------
# CompactionProfile (CF Phase 3b)
# ---------------------------------------------------------------------------


def test_compaction_profile_defaults():
    p = DEFAULT_COMPACTION_PROFILE
    assert p.max_compression_level == 3
    assert 0.0 < p.free_zone_ratio < 1.0
    assert 0.0 < p.preserve_threshold < 1.0


def test_get_compaction_profile_known_role():
    p = get_compaction_profile("architect")
    assert p.max_compression_level == 1
    assert p.preserve_threshold == 0.7


def test_get_compaction_profile_aliases_worker_explore_to_general():
    assert get_compaction_profile("worker_explore") is COMPACTION_PROFILES["worker_general"]


def test_get_compaction_profile_preserves_worker_fast_profile():
    assert get_compaction_profile("worker_fast") is COMPACTION_PROFILES["worker_fast"]


def test_get_compaction_profile_unknown_role():
    p = get_compaction_profile("unknown_role_xyz")
    assert p is DEFAULT_COMPACTION_PROFILE


def test_compaction_profiles_hierarchy():
    """Architect should be more conservative than worker_fast."""
    arch = COMPACTION_PROFILES["architect"]
    fast = COMPACTION_PROFILES["worker_fast"]
    assert arch.max_compression_level < fast.max_compression_level
    assert arch.preserve_threshold > fast.preserve_threshold
    assert arch.free_zone_ratio > fast.free_zone_ratio


def test_compaction_profile_serialization():
    p = CompactionProfile(max_compression_level=2, free_zone_ratio=0.35)
    d = p.to_dict()
    restored = CompactionProfile.from_dict(d)
    assert restored.max_compression_level == 2
    assert restored.free_zone_ratio == pytest.approx(0.35)


def test_compaction_quality_monitor_miss_rate():
    mon = CompactionQualityMonitor()
    mon.record_compaction(5)
    assert mon.miss_rate == pytest.approx(0.0)
    mon.record_reference_miss()
    mon.record_reference_miss()
    assert mon.miss_rate == pytest.approx(2 / 5)


def test_compaction_quality_monitor_serialization():
    mon = CompactionQualityMonitor()
    mon.record_compaction(3)
    mon.record_reference_miss()
    d = mon.to_dict()
    restored = CompactionQualityMonitor.from_dict(d)
    assert restored.segments_compacted == 3
    assert restored.post_compaction_references == 1
    assert restored.miss_rate == pytest.approx(1 / 3)

"""Direct tests for graph.session_summary helper branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.features import Features, reset_features, set_features
from src.graph.session_log import ConsolidatedSegment, ScratchpadEntry, TurnRecord
from src.graph.session_summary import (
    _get_exploration_tool_calls,
    _init_session_log,
    _maybe_refresh_session_summary,
    _record_session_turn,
    _refresh_two_level_summary,
    _session_log_prompt_block,
)
from src.graph.state import GraphConfig, TaskDeps, TaskState


def _state(**kwargs) -> TaskState:
    return TaskState(**kwargs)


def _record(turn: int, role: str, output: str = "done") -> TurnRecord:
    return TurnRecord(turn=turn, role=role, output_preview=output, outcome="ok")


def test_init_session_log_respects_feature_and_task_id():
    set_features(Features(session_log=True))
    try:
        state = _state(task_id="task-123")
        with patch("src.graph.session_log.session_log_path", return_value="/tmp/session_task-123.md"):
            _init_session_log(state)
        assert state.session_log_path == "/tmp/session_task-123.md"

        # Idempotent once set.
        with patch("src.graph.session_log.session_log_path", side_effect=AssertionError("should not be called")):
            _init_session_log(state)
        assert state.session_log_path == "/tmp/session_task-123.md"
    finally:
        reset_features()


def test_record_session_turn_appends_record_and_persists():
    state = _state(task_id="task-1", turns=4, session_log_path="/tmp/session.md")
    built = object()
    with (
        patch("src.graph.session_log.build_turn_record", return_value=built) as build_record,
        patch("src.graph.session_log.append_turn_record") as append_turn_record,
    ):
        _record_session_turn(
            state,
            role="worker",
            code="print('x')",
            output="ok",
            nudge="retry",
            escalation_target="coder",
            tool_calls=["peek"],
        )

    build_record.assert_called_once()
    append_turn_record.assert_called_once_with("/tmp/session.md", built)
    assert state.session_log_records == [built]


def test_get_exploration_tool_calls_handles_baseline_and_failures():
    deps = TaskDeps(config=GraphConfig())
    deps.repl = SimpleNamespace(
        get_exploration_log=lambda: SimpleNamespace(
            events=[
                SimpleNamespace(function="old"),
                SimpleNamespace(function="peek"),
                SimpleNamespace(no_function=True),
                SimpleNamespace(function="grep"),
            ]
        )
    )

    assert _get_exploration_tool_calls(deps, 1) == ["peek", "grep"]

    deps.repl = None
    assert _get_exploration_tool_calls(deps, 0) == []

    deps.repl = SimpleNamespace(get_exploration_log=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert _get_exploration_tool_calls(deps, 0) == []


async def test_maybe_refresh_session_summary_uses_worker_and_scratchpad():
    set_features(Features(session_scratchpad=True))
    try:
        state = _state(
            task_id="task-1",
            turns=5,
            session_log_path="/tmp/session.md",
            session_log_records=[_record(1, "worker")],
            scratchpad_entries=[ScratchpadEntry(turn=1, category="user_intent", insight="old")],
        )
        deps = TaskDeps(primitives=object(), config=GraphConfig())
        new_entry = ScratchpadEntry(turn=5, category="bug_location", insight="new")
        with (
            patch(
                "src.graph.session_log.summarize_session_with_worker",
                new=AsyncMock(return_value=("worker summary", [new_entry])),
            ) as summarize,
            patch(
                "src.graph.session_log.prune_scratchpad",
                side_effect=lambda entries: list(reversed(entries)),
            ) as prune,
        ):
            await _maybe_refresh_session_summary(state, deps)

        summarize.assert_awaited_once()
        prune.assert_called_once()
        assert state.session_summary_cache == "worker summary"
        assert state.session_summary_turn == 5
        assert state.scratchpad_entries == [new_entry, ScratchpadEntry(turn=1, category="user_intent", insight="old")]
    finally:
        reset_features()


async def test_maybe_refresh_session_summary_falls_back_deterministically_on_failure():
    state = _state(
        task_id="task-1",
        turns=3,
        session_log_path="/tmp/session.md",
        session_log_records=[_record(1, "worker")],
    )
    deps = TaskDeps(primitives=object(), config=GraphConfig())

    with (
        patch(
            "src.graph.session_log.summarize_session_with_worker",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch(
            "src.graph.session_log.build_session_summary_deterministic",
            return_value="deterministic summary",
        ) as deterministic,
    ):
        await _maybe_refresh_session_summary(state, deps)

    deterministic.assert_called_once_with(state.session_log_records)
    assert state.session_summary_cache == "deterministic summary"
    assert state.session_summary_turn == 0


async def test_maybe_refresh_session_summary_skips_when_cache_is_fresh():
    state = _state(
        task_id="task-1",
        turns=4,
        session_log_path="/tmp/session.md",
        session_log_records=[_record(1, "worker")],
        session_summary_cache="cached",
        session_summary_turn=3,
    )
    deps = TaskDeps(primitives=object(), config=GraphConfig())

    with patch("src.graph.session_log.summarize_session_with_worker", new=AsyncMock()) as summarize:
        await _maybe_refresh_session_summary(state, deps)

    summarize.assert_not_called()
    assert state.session_summary_cache == "cached"


async def test_refresh_two_level_summary_uses_cached_segment_and_reward_signals():
    set_features(
        Features(
            two_level_condensation=True,
            segment_cache_dedup=True,
            process_reward_telemetry=True,
        )
    )
    try:
        state = _state(
            task_id="task-1",
            turns=6,
            current_role="worker",
            session_log_records=[_record(1, "worker", "first"), _record(2, "worker", "second")],
            pending_granular_blocks=["older granular"],
            pending_granular_start_turn=1,
        )
        deps = TaskDeps(primitives=None, config=GraphConfig())

        with (
            patch("src.graph.session_log.build_granular_summary", return_value="new granular"),
            patch("src.graph.session_log.should_consolidate", return_value="boundary"),
            patch("src.graph.session_log.SegmentCache") as segment_cache_cls,
            patch("src.graph.session_log.compute_reward_signals", return_value={"reward": 1}) as reward_signals,
        ):
            cache = MagicMock()
            cache.lookup.return_value = "cached summary"
            segment_cache_cls.return_value = cache
            await _refresh_two_level_summary(state, deps)

        assert len(state.consolidated_segments) == 1
        segment = state.consolidated_segments[0]
        assert segment.consolidated == "cached summary"
        assert segment.trigger == "boundary_cached"
        assert segment.reward_signals == {"reward": 1}
        reward_signals.assert_called_once()
        assert state.pending_granular_blocks == []
        assert state.pending_granular_start_turn == 0
        assert "[Session History" in state.session_summary_cache
    finally:
        reset_features()


async def test_refresh_two_level_summary_compacts_low_helpfulness_segments():
    set_features(
        Features(
            two_level_condensation=True,
            role_aware_compaction=True,
            helpfulness_scoring=True,
        )
    )
    try:
        state = _state(
            task_id="task-1",
            turns=9,
            current_role="architect",
            session_log_records=[_record(1, "worker"), _record(2, "architect")],
            consolidated_segments=[
                ConsolidatedSegment((1, 1), ["a"], "old one. extra", "boundary"),
                ConsolidatedSegment((2, 2), ["b"], "old two. extra", "boundary"),
                ConsolidatedSegment((3, 3), ["c"], "keep three. extra", "boundary"),
                ConsolidatedSegment((4, 4), ["d"], "keep four. extra", "boundary"),
                ConsolidatedSegment((5, 5), ["e"], "free zone. extra", "boundary"),
            ],
            pending_granular_blocks=["recent one", "recent two"],
            pending_granular_start_turn=1,
        )
        deps = TaskDeps(primitives=None, config=GraphConfig())

        fake_profile = SimpleNamespace(free_zone_ratio=0.2, preserve_threshold=0.5)
        monitor = MagicMock()
        with (
            patch("src.graph.session_log.build_granular_summary", return_value="newest granular"),
            patch("src.graph.session_log.should_consolidate", return_value="boundary"),
            patch("src.graph.session_log.get_compaction_profile", return_value=fake_profile),
            patch(
                "src.graph.session_log.segment_helpfulness",
                side_effect=lambda seg, turns, text: (
                    0.1 if seg.consolidated.startswith("old") else 0.9
                ),
            ),
            patch("src.graph.session_log.CompactionQualityMonitor", return_value=monitor),
        ):
            await _refresh_two_level_summary(state, deps)

        assert state.consolidated_segments[0].consolidated.startswith("[Compacted] old one.")
        assert state.consolidated_segments[1].consolidated.startswith("[Compacted] old two.")
        monitor.record_compaction.assert_called_once_with(2)
    finally:
        reset_features()


def test_session_log_prompt_block_includes_scratchpad_and_file_reference():
    state = _state(
        session_summary_cache="[Session History]\nSummary here",
        session_log_path="/tmp/session.md",
        scratchpad_entries=[ScratchpadEntry(turn=2, category="bug_location", insight="look in router")],
    )

    block = _session_log_prompt_block(state)

    assert "[Key Insights]" in block
    assert "look in router" in block
    assert "Summary here" in block
    assert 'peek(99999, file_path="/tmp/session.md")' in block


async def _run_reference_miss_probe(granular, consolidated, current_block):
    """Drive the CF-3c reference-miss check with one already-compacted segment."""
    from src.graph.session_log import CompactionQualityMonitor

    set_features(Features(two_level_condensation=True))
    try:
        monitor = CompactionQualityMonitor()
        monitor.record_compaction(1)
        state = _state(
            task_id="task-miss",
            turns=6,
            current_role="architect",
            session_log_records=[_record(1, "worker")],
            consolidated_segments=[
                ConsolidatedSegment((1, 1), granular, consolidated, "boundary"),
            ],
            pending_granular_blocks=[current_block],
            pending_granular_start_turn=1,
        )
        state.compaction_quality_monitor = monitor
        deps = TaskDeps(primitives=None, config=GraphConfig())
        with (
            patch("src.graph.session_log.build_granular_summary", return_value="newest granular"),
            patch("src.graph.session_log.should_consolidate", return_value=None),
        ):
            await _refresh_two_level_summary(state, deps)
        return monitor
    finally:
        reset_features()


async def test_reference_miss_fires_for_identifiers_compaction_destroyed():
    """Regression: the miss check must inspect DESTROYED identifiers.

    Compaction overwrites seg.consolidated with a short stub; granular_blocks
    retains the pre-compaction text. Reading identifiers from seg.consolidated
    (the surviving stub) inverts the metric so it can never fire for content
    that was actually lost. Here 'helper.py' exists only pre-compaction and is
    referenced by the current turn -> exactly one miss.
    """
    monitor = await _run_reference_miss_probe(
        granular=["loaded helper.py and called ParseWidget()"],
        consolidated="[Compacted] kept summary with no identifiers.",
        current_block="now editing helper.py again",
    )
    assert monitor.post_compaction_references == 1
    assert monitor.miss_rate == 1.0


async def test_reference_miss_ignores_identifiers_compaction_preserved():
    """Surviving identifiers are NOT a miss — compaction kept what was needed.

    This is the false positive the pre-fix implementation produced: it matched
    against the stub, so a reference to preserved content counted as a loss.
    """
    monitor = await _run_reference_miss_probe(
        granular=["loaded helper.py and called ParseWidget()"],
        consolidated="[Compacted] still mentions helper.py explicitly.",
        current_block="now editing helper.py again",
    )
    assert monitor.post_compaction_references == 0
    assert monitor.miss_rate == 0.0

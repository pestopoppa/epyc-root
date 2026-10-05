"""Tests for session scratchpad memory (model-extracted semantic insights)."""

from __future__ import annotations


from src.graph.session_log import (
    ScratchpadEntry,
    MAX_SCRATCHPAD_ENTRIES,
    parse_scratchpad_from_response,
    prune_scratchpad,
    build_scratchpad_extraction_prompt,
    TurnRecord,
)


# ---------------------------------------------------------------------------
# ScratchpadEntry basics
# ---------------------------------------------------------------------------


def test_scratchpad_entry_to_bullet():
    entry = ScratchpadEntry(turn=3, category="bug_location", insight="Off-by-one in loop at line 42")
    assert entry.to_bullet() == "- [bug_location] Off-by-one in loop at line 42"


def test_scratchpad_entry_defaults():
    entry = ScratchpadEntry(turn=1, category="user_intent", insight="wants async")
    assert entry.confidence == 0.8


# ---------------------------------------------------------------------------
# parse_scratchpad_from_response
# ---------------------------------------------------------------------------


def test_parse_scratchpad_from_response_valid():
    response = (
        "The model tried approach X which failed due to timeout.\n"
        "It then succeeded with approach Y.\n"
        "INSIGHT|bug_location|The timeout was in the database query at line 55\n"
        "INSIGHT|approach_eliminated|Approach X (sync polling) too slow for large datasets\n"
    )
    summary, entries = parse_scratchpad_from_response(response, current_turn=5)
    assert "approach X" in summary
    assert len(entries) == 2
    assert entries[0].category == "bug_location"
    assert entries[0].turn == 5
    assert entries[1].category == "approach_eliminated"


def test_parse_scratchpad_ignores_invalid_categories():
    response = (
        "Summary text here.\n"
        "INSIGHT|bug_location|Valid insight\n"
        "INSIGHT|made_up_category|This should be ignored\n"
        "INSIGHT|user_intent|Also valid\n"
    )
    summary, entries = parse_scratchpad_from_response(response, current_turn=2)
    assert len(entries) == 2
    assert {e.category for e in entries} == {"bug_location", "user_intent"}


def test_parse_scratchpad_empty_response():
    summary, entries = parse_scratchpad_from_response("", current_turn=1)
    assert summary == ""
    assert entries == []


def test_parse_scratchpad_no_insights():
    response = "Just a plain summary with no INSIGHT lines."
    summary, entries = parse_scratchpad_from_response(response, current_turn=1)
    assert "plain summary" in summary
    assert entries == []


def test_parse_scratchpad_truncates_long_insight():
    long_text = "x" * 300
    response = f"INSIGHT|bug_location|{long_text}\n"
    _, entries = parse_scratchpad_from_response(response, current_turn=1)
    assert len(entries) == 1
    assert len(entries[0].insight) == 200


def test_parse_scratchpad_malformed_line():
    response = "INSIGHT|only_two_parts\nINSIGHT|bug_location|valid\n"
    _, entries = parse_scratchpad_from_response(response, current_turn=1)
    assert len(entries) == 1
    assert entries[0].category == "bug_location"


# ---------------------------------------------------------------------------
# prune_scratchpad
# ---------------------------------------------------------------------------


def test_prune_scratchpad_category_supersession():
    entries = [
        ScratchpadEntry(turn=1, category="bug_location", insight="bug at line 10"),
        ScratchpadEntry(turn=3, category="bug_location", insight="bug actually at line 42"),
        ScratchpadEntry(turn=2, category="user_intent", insight="wants async"),
    ]
    pruned = prune_scratchpad(entries)
    assert len(pruned) == 2
    # bug_location should be the newer one (turn 3)
    bug_entries = [e for e in pruned if e.category == "bug_location"]
    assert bug_entries[0].insight == "bug actually at line 42"


def test_prune_scratchpad_max_entries():
    entries = [
        ScratchpadEntry(turn=i, category=cat, insight=f"insight {i}")
        for i, cat in enumerate([
            "bug_location", "approach_eliminated", "constraint_discovered",
            "user_intent", "dependency_found",
            # Duplicate categories to exceed MAX after supersession
            "bug_location", "approach_eliminated", "constraint_discovered",
            "user_intent", "dependency_found",
        ])
    ]
    pruned = prune_scratchpad(entries)
    assert len(pruned) <= MAX_SCRATCHPAD_ENTRIES
    # Each category should have only the latest entry
    categories = [e.category for e in pruned]
    assert len(categories) == len(set(categories))


def test_prune_scratchpad_empty():
    assert prune_scratchpad([]) == []


def test_prune_scratchpad_sorts_by_recency():
    entries = [
        ScratchpadEntry(turn=1, category="bug_location", insight="old"),
        ScratchpadEntry(turn=5, category="user_intent", insight="recent"),
        ScratchpadEntry(turn=3, category="constraint_discovered", insight="middle"),
    ]
    pruned = prune_scratchpad(entries)
    assert pruned[0].turn == 5
    assert pruned[-1].turn == 1


# ---------------------------------------------------------------------------
# build_scratchpad_extraction_prompt
# ---------------------------------------------------------------------------


def test_build_scratchpad_extraction_prompt():
    records = [
        TurnRecord(turn=1, role="frontdoor", outcome="error", error_message="NameError"),
        TurnRecord(turn=2, role="frontdoor", outcome="ok", output_preview="result: 42"),
    ]
    prompt = build_scratchpad_extraction_prompt(records)
    assert "SECTION 1" in prompt
    assert "SECTION 2" in prompt
    assert "INSIGHT|" in prompt
    assert "bug_location" in prompt


# ---------------------------------------------------------------------------
# _session_log_prompt_block with scratchpad
# ---------------------------------------------------------------------------


def test_session_log_prompt_block_with_scratchpad():
    from src.graph.state import TaskState
    from src.graph.helpers import _session_log_prompt_block

    state = TaskState()
    state.session_summary_cache = "[Session History — AI Summary]\nSome summary."
    state.scratchpad_entries = [
        ScratchpadEntry(turn=1, category="bug_location", insight="Bug in parser line 42"),
        ScratchpadEntry(turn=2, category="user_intent", insight="User wants async API"),
    ]
    block = _session_log_prompt_block(state)
    assert "[Key Insights]" in block
    assert "[bug_location]" in block
    assert "[user_intent]" in block
    # Insights should come before session history
    insights_pos = block.index("[Key Insights]")
    history_pos = block.index("[Session History")
    assert insights_pos < history_pos


def test_session_log_prompt_block_without_scratchpad():
    from src.graph.state import TaskState
    from src.graph.helpers import _session_log_prompt_block

    state = TaskState()
    state.session_summary_cache = "[Session History — AI Summary]\nSome summary."
    state.scratchpad_entries = []
    block = _session_log_prompt_block(state)
    assert "[Key Insights]" not in block
    assert "[Session History" in block


# ---------------------------------------------------------------------------
# Feature flag gating
# ---------------------------------------------------------------------------


def test_scratchpad_feature_flag_disabled():
    """When session_scratchpad is disabled, no scratchpad extraction should occur."""
    from src.features import Features

    f = Features(session_scratchpad=False)
    assert f.session_scratchpad is False
    assert "session_scratchpad" in f.summary()
    assert f.summary()["session_scratchpad"] is False


def test_scratchpad_feature_flag_enabled():
    from src.features import Features

    f = Features(session_scratchpad=True)
    assert f.session_scratchpad is True
    assert f.summary()["session_scratchpad"] is True


# ---------------------------------------------------------------------------
# Escalation context carries scratchpad
# ---------------------------------------------------------------------------


def test_escalation_context_scratchpad():
    from src.escalation import EscalationContext
    from src.roles import Role

    entries = [
        ScratchpadEntry(turn=1, category="bug_location", insight="bug at line 10"),
    ]
    ctx = EscalationContext(
        current_role=Role.WORKER_GENERAL,
        scratchpad_entries=entries,
    )
    assert len(ctx.scratchpad_entries) == 1
    assert ctx.scratchpad_entries[0].insight == "bug at line 10"


def test_escalation_context_scratchpad_default_empty():
    from src.escalation import EscalationContext
    from src.roles import Role

    ctx = EscalationContext(current_role=Role.WORKER_GENERAL)
    assert ctx.scratchpad_entries == []


# ---------------------------------------------------------------------------
# Escalation prompt injection
# ---------------------------------------------------------------------------


def test_escalation_prompt_includes_scratchpad():
    from src.escalation import (
        EscalationContext,
        EscalationDecision,
        EscalationAction,
    )
    from src.prompt_builders.builder import PromptBuilder
    from src.roles import Role

    entries = [
        ScratchpadEntry(turn=1, category="bug_location", insight="Off-by-one at line 42"),
        ScratchpadEntry(turn=2, category="approach_eliminated", insight="Regex approach too slow"),
    ]
    ctx = EscalationContext(
        current_role=Role.WORKER_GENERAL,
        failure_count=2,
        scratchpad_entries=entries,
    )
    decision = EscalationDecision(
        action=EscalationAction.ESCALATE,
        target_role=Role.CODER_ESCALATION,
        reason="Escalating after 2 failures",
    )
    builder = PromptBuilder()
    result = builder.build_escalation_prompt(
        original_prompt="Fix the parser",
        state="artifacts = {}",
        failure_context=ctx,
        decision=decision,
        as_structured=True,
    )
    assert "Previous Insights" in result.failure_info
    assert "Off-by-one at line 42" in result.failure_info
    assert "Regex approach too slow" in result.failure_info

"""Characterization tests for chat_delegation pure functions.

Tests cover: _strip_think, _extract_toon_decision, _parse_architect_decision,
loop guards (_get_delegation_depth, semantic dedup, role repetition, token budget),
and the live delegate-role allowlist plus _ARCHITECT_TOKEN_BUDGET,
_ARCHITECT_DECISION_BUDGET.
"""

import hashlib
from unittest.mock import MagicMock, patch

import yaml

from src.api.routes.chat_delegation import (
    _strip_think,
    _extract_toon_decision,
    _parse_architect_decision,
    _get_delegation_depth,
    _delegation_local,
)
from src.api.routes.chat_delegation_decision import (
    _ARCHITECT_TOKEN_BUDGET,
    _ARCHITECT_DECISION_BUDGET,
    _architect_budget_roles,
    _architect_compute_token_budget,
    _architect_decision_token_budget,
)
from src.api.routes.chat_delegation_config import _valid_delegate_roles
from src.api.routes.chat_delegation_reports import (
    _build_compact_specialist_prompt,
    _compress_report_for_loop,
)
from src.constants import (
    DELEGATION_BRIEF_KEY_LEN,
    DELEGATION_MAX_SAME_TARGET,
    DELEGATION_MAX_TOTAL_TOKENS,
)
from src.delegation_reports import load_report


# ── _strip_think ────────────────────────────────────────────────────────


class TestStripThink:
    def test_removes_complete_think_block(self):
        text = "Hello <think>internal reasoning</think> world"
        assert _strip_think(text) == "Hello  world"

    def test_removes_incomplete_trailing_think(self):
        text = "Answer: B<think>I should delegate with I|brief:check"
        assert _strip_think(text) == "Answer: B"

    def test_preserves_text_without_think_blocks(self):
        text = "The answer is 42. No special tags here."
        assert _strip_think(text) == text

    def test_removes_multiline_think_block(self):
        text = "before<think>\nline1\nline2\n</think>after"
        assert _strip_think(text) == "beforeafter"

    def test_removes_multiple_complete_blocks(self):
        text = "<think>a</think>X<think>b</think>Y"
        assert _strip_think(text) == "XY"


# ── _extract_toon_decision ──────────────────────────────────────────────


class TestExtractToonDecision:
    def test_mcq_single_letter(self):
        assert _extract_toon_decision("D|B") == "D|B"

    def test_direct_freeform_answer(self):
        result = _extract_toon_decision("D|The answer is 42")
        assert result == "D|The answer is 42"

    def test_investigate_with_brief_and_to(self):
        result = _extract_toon_decision("I|brief:check the code|to:coder_escalation")
        assert result == "I|brief:check the code|to:coder_escalation"

    def test_hybrid_d_i_delegation(self):
        result = _extract_toon_decision("D|I|brief:review logic|to:coder_escalation")
        assert result is not None
        assert result.startswith("I|")
        assert "brief:review logic" in result

    def test_no_pattern_returns_none(self):
        assert _extract_toon_decision("Just some plain text without any decision") is None

    def test_rejects_template_echo_answer(self):
        assert _extract_toon_decision("D|answer") is None

    def test_rejects_template_echo_the_answer(self):
        assert _extract_toon_decision("D|the answer") is None

    def test_mcq_embedded_in_sentence(self):
        # D|C followed by alpha "To" -- MCQ shortcut requires non-alpha after
        # the letter, so the general pattern fires and captures more text.
        text = "The answer is C. Decision: D|CTo confirm this..."
        result = _extract_toon_decision(text)
        assert result is not None
        assert result.startswith("D|")

    def test_mcq_embedded_with_space(self):
        # D|C followed by space -- MCQ shortcut fires correctly
        text = "The answer is C. Decision: D|C and that is final."
        assert _extract_toon_decision(text) == "D|C"

    def test_investigate_lenient_without_brief_prefix(self):
        result = _extract_toon_decision("I|check the implementation|to:worker_explore")
        assert result is not None
        assert "brief:" in result
        assert "to:worker_explore" in result

    def test_mcq_letter_with_trailing_nonalpha(self):
        assert _extract_toon_decision("D|A.") == "D|A"


# ── _parse_architect_decision ───────────────────────────────────────────


class TestParseArchitectDecision:
    # ── TOON Direct ──

    def test_direct_mcq(self):
        result = _parse_architect_decision("D|B")
        assert result["mode"] == "direct"
        assert result["answer"] == "B"
        assert result["brief"] == ""
        assert result["delegate_to"] == ""
        assert result["delegate_mode"] == "react"

    def test_long_direct_with_embedded_mcq_rescue(self):
        # Long D| answer with "the answer is C" buried inside
        long_text = "D|" + "x" * 60 + " the answer is C " + "y" * 20
        result = _parse_architect_decision(long_text)
        assert result["mode"] == "direct"
        assert result["answer"] == "C"

    def test_investigate_mode(self):
        result = _parse_architect_decision("I|brief:check code|to:coder_escalation")
        assert result["mode"] == "investigate"
        assert result["brief"] == "check code"
        assert result["delegate_to"] == "coder_escalation"
        assert result["delegate_mode"] == "react"

    def test_invalid_delegate_role_clamps_to_coder_escalation(self):
        result = _parse_architect_decision("I|brief:test|to:nonexistent_role")
        assert result["mode"] == "investigate"
        assert result["delegate_to"] == "coder_escalation"

    def test_invalid_delegate_mode_clamps_to_react(self):
        result = _parse_architect_decision("I|brief:test|to:coder_escalation|mode:invalid_mode")
        assert result["mode"] == "investigate"
        assert result["delegate_mode"] == "react"

    def test_json_direct(self):
        import json
        obj = {"mode": "direct", "answer": "42"}
        result = _parse_architect_decision(json.dumps(obj))
        assert result["mode"] == "direct"
        assert result["answer"] == "42"

    def test_markdown_wrapped_json(self):
        text = '```json\n{"mode": "direct", "answer": "hello world"}\n```'
        result = _parse_architect_decision(text)
        assert result["mode"] == "direct"
        assert result["answer"] == "hello world"

    def test_bare_text_fallback(self):
        text = "The capital of France is Paris."
        result = _parse_architect_decision(text)
        assert result["mode"] == "direct"
        assert result["answer"] == text
        assert result["brief"] == ""
        assert result["delegate_to"] == ""

    def test_long_direct_rescues_option_pattern(self):
        long_text = "D|" + "z" * 60 + " option A seems correct " + "w" * 20
        result = _parse_architect_decision(long_text)
        assert result["mode"] == "direct"
        assert result["answer"] == "A"

    def test_long_direct_rescues_last_toon_mcq(self):
        long_text = "D|" + "z" * 60 + " reasoning text D|B more text"
        result = _parse_architect_decision(long_text)
        assert result["mode"] == "direct"
        assert result["answer"] == "B"

    def test_investigate_with_repl_mode(self):
        result = _parse_architect_decision("I|brief:run tests|to:coder_escalation|mode:repl")
        assert result["mode"] == "investigate"
        assert result["delegate_mode"] == "repl"

    def test_json_investigate(self):
        import json
        obj = {"mode": "investigate", "brief": "analyze logs", "delegate_to": "worker_explore"}
        result = _parse_architect_decision(json.dumps(obj))
        assert result["mode"] == "investigate"
        assert result["brief"] == "analyze logs"
        assert result["delegate_to"] == "worker_general"

    def test_legacy_worker_aliases_normalize_to_live_roles(self):
        explore = _parse_architect_decision("I|brief:check logs|to:worker_explore")
        fast = _parse_architect_decision("I|brief:check logs|to:worker_fast")
        coder = _parse_architect_decision("I|brief:patch bug|to:worker_coder")

        assert explore["delegate_to"] == "worker_general"
        assert fast["delegate_to"] == "worker_general"
        assert coder["delegate_to"] == "coder_escalation"

    def test_empty_string(self):
        result = _parse_architect_decision("")
        assert result["mode"] == "direct"

    def test_direct_short_answer(self):
        result = _parse_architect_decision("D|The answer is 42")
        assert result["mode"] == "direct"
        assert result["answer"] == "The answer is 42"


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:
    def test_valid_delegate_roles(self):
        expected = {
            "coder_escalation",
            "worker_summarize",
            "worker_general",
            "worker_math",
            "worker_vision",
            "vision_escalation",
        }
        assert _valid_delegate_roles() == expected

    def test_architect_token_budget_values(self):
        assert _ARCHITECT_TOKEN_BUDGET["architect_general"] == 768

    def test_architect_decision_budget_values(self):
        assert _ARCHITECT_DECISION_BUDGET["architect_general"] == 512

    def test_budgets_have_expected_keys(self):
        """Both budget maps are keyed by the LIVE architect roles.

        These maps stopped being literals in 80ed046e — module ``__getattr__``
        builds them from ``_architect_budget_roles()``, which reads the generated
        stack-prior artifact ("Preserve legacy budget-map imports without freezing
        live role tables"). Freezing the key set here re-froze exactly what the
        source was refactored to stop freezing, and broke when the W1 cutover
        added architect_critic as a live architect role. Derive from the same
        function the source reads.
        """
        expected = set(_architect_budget_roles())
        assert expected, "architect budget-role derivation must not be empty"
        assert all(role.startswith("architect_") for role in expected)

        assert set(_ARCHITECT_TOKEN_BUDGET.keys()) == expected
        assert set(_ARCHITECT_DECISION_BUDGET.keys()) == expected

        # Every derived key carries the architect-sized budget, not the
        # non-architect default — including any newly live architect role.
        assert set(_ARCHITECT_TOKEN_BUDGET.values()) == {768}
        assert set(_ARCHITECT_DECISION_BUDGET.values()) == {512}

    def test_architect_budgets_derive_from_live_stack_priors(self, tmp_path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            yaml.safe_dump(
                {
                    "roles": {
                        "architect_general": {"deployment_status": "live_stack"},
                        "architect_research": {"deployment_status": "live_stack"},
                        "candidate_architect": {
                            "deployment_status": "benchmark_or_candidate"
                        },
                        "coder_escalation": {"deployment_status": "live_stack"},
                    }
                }
            ),
            encoding="utf-8",
        )

        assert _architect_budget_roles(priors) == frozenset(
            {"architect_general", "architect_research"}
        )
        assert _architect_decision_token_budget(
            "architect_research",
            stack_priors_path=priors,
        ) == 512
        assert _architect_compute_token_budget(
            "architect_research",
            stack_priors_path=priors,
        ) == 768
        assert _architect_decision_token_budget(
            "coder_escalation",
            stack_priors_path=priors,
        ) == 256
        assert _architect_compute_token_budget(
            "coder_escalation",
            stack_priors_path=priors,
        ) == 512

    def test_empty_live_architect_budget_roles_do_not_use_degraded_fallback(self, tmp_path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            yaml.safe_dump(
                {
                    "roles": {
                        "coder_escalation": {"deployment_status": "live_stack"},
                    }
                }
            ),
            encoding="utf-8",
        )

        assert _architect_budget_roles(priors) == frozenset()
        assert _architect_decision_token_budget(
            "architect_general",
            stack_priors_path=priors,
        ) == 256
        assert _architect_compute_token_budget(
            "architect_general",
            stack_priors_path=priors,
        ) == 512


# ── Specialist Prompt Preambles ─────────────────────────────────────────


class TestSpecialistPromptPreambles:
    def test_legacy_worker_coder_prompt_uses_live_coder_role(self):
        prompt = _build_compact_specialist_prompt(
            "worker_coder",
            "Fix this bug",
            "Patch the failing branch",
            0,
            "",
            "",
        )

        assert prompt.startswith("You are coder_escalation.")
        assert "delegated coding task" in prompt
        assert "worker_coder" not in prompt

    def test_legacy_worker_explore_prompt_uses_live_general_role(self):
        prompt = _build_compact_specialist_prompt(
            "worker_explore",
            "Check this behavior",
            "Inspect logs",
            0,
            "",
            "",
        )

        assert prompt.startswith("You are worker_general.")
        assert "web_search(query)" in prompt
        assert "worker_explore" not in prompt

    def test_legacy_worker_fast_prompt_uses_live_general_role(self):
        prompt = _build_compact_specialist_prompt(
            "worker_fast",
            "Check this behavior",
            "Inspect logs",
            0,
            "",
            "",
        )

        assert prompt.startswith("You are worker_general.")
        assert "web_search(query)" in prompt
        assert "worker_fast" not in prompt


# ── Loop Guards ──────────────────────────────────────────────────────────


class TestDelegationDepth:
    def test_initial_depth_is_zero(self):
        # Clear any leftover state
        _delegation_local.depth = 0
        assert _get_delegation_depth() == 0

    def test_depth_tracks_nesting(self):
        _delegation_local.depth = 0
        assert _get_delegation_depth() == 0
        _delegation_local.depth = 1
        assert _get_delegation_depth() == 1
        _delegation_local.depth = 2
        assert _get_delegation_depth() == 2
        _delegation_local.depth = 0  # cleanup

    def test_unset_depth_returns_zero(self):
        if hasattr(_delegation_local, "depth"):
            delattr(_delegation_local, "depth")
        assert _get_delegation_depth() == 0


class TestSemanticDedup:
    def _make_brief_key(self, brief: str, delegate_to: str) -> str:
        return hashlib.md5(
            f"{brief.strip().lower()[:DELEGATION_BRIEF_KEY_LEN]}|{delegate_to}".encode()
        ).hexdigest()

    def test_same_brief_same_target_produces_same_key(self):
        k1 = self._make_brief_key("check the code for bugs", "coder_escalation")
        k2 = self._make_brief_key("check the code for bugs", "coder_escalation")
        assert k1 == k2

    def test_same_brief_different_target_produces_different_key(self):
        k1 = self._make_brief_key("check the code", "coder_escalation")
        k2 = self._make_brief_key("check the code", "worker_explore")
        assert k1 != k2

    def test_different_brief_same_target_produces_different_key(self):
        k1 = self._make_brief_key("check the code", "coder_escalation")
        k2 = self._make_brief_key("review the logic", "coder_escalation")
        assert k1 != k2

    def test_case_insensitive_brief(self):
        k1 = self._make_brief_key("Check The Code", "coder_escalation")
        k2 = self._make_brief_key("check the code", "coder_escalation")
        assert k1 == k2


class TestRoleRepetitionGuard:
    def test_consecutive_same_role_triggers_guard(self):
        history = ["coder_escalation"] * DELEGATION_MAX_SAME_TARGET
        recent = history[-DELEGATION_MAX_SAME_TARGET:]
        assert all(r == "coder_escalation" for r in recent)

    def test_alternating_roles_does_not_trigger(self):
        history = ["coder_escalation", "worker_explore"] * 3
        for i in range(len(history)):
            if i + DELEGATION_MAX_SAME_TARGET <= len(history):
                recent = history[i:i + DELEGATION_MAX_SAME_TARGET]
                # At least one alternating window should NOT trigger
                if not all(r == recent[0] for r in recent):
                    break
        else:
            raise AssertionError("Expected at least one non-triggering window")

    def test_max_same_target_constant_is_reasonable(self):
        assert DELEGATION_MAX_SAME_TARGET >= 2
        assert DELEGATION_MAX_SAME_TARGET <= 5


class TestTokenBudgetGuard:
    def test_constant_is_reasonable(self):
        assert DELEGATION_MAX_TOTAL_TOKENS >= 10_000
        assert DELEGATION_MAX_TOTAL_TOKENS <= 100_000

    def test_budget_exceeded_triggers_guard(self):
        cumulative = DELEGATION_MAX_TOTAL_TOKENS + 1
        assert cumulative > DELEGATION_MAX_TOTAL_TOKENS

    def test_budget_not_exceeded_passes(self):
        cumulative = DELEGATION_MAX_TOTAL_TOKENS - 1
        assert cumulative <= DELEGATION_MAX_TOTAL_TOKENS


# ── _compress_report_for_loop (C6 / DCP-13) ─────────────────────────────


class TestCompressReportForLoop:
    """Rescued reports skip worker_summarize but keep handle persistence."""

    _LONG = "FULL REPORT\n" + ("detail line\n" * 400)

    def _primitives(self):
        primitives = MagicMock()
        primitives.llm_call = MagicMock(return_value="compact summary")
        return primitives

    def test_skip_summary_long_report_persists_handle_without_llm_call(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ORCHESTRATOR_DELEGATION_REPORT_DIR", str(tmp_path))
        primitives = self._primitives()

        text, handle = _compress_report_for_loop(
            self._LONG, "q", primitives, "coder_escalation", skip_summary=True,
        )

        primitives.llm_call.assert_not_called()
        assert text == self._LONG
        assert handle is not None
        assert handle["chars"] == str(len(self._LONG.strip()))
        assert load_report(handle["id"], max_chars=12000)["content"] == self._LONG.strip()

    def test_skip_summary_short_report_has_no_handle_or_llm_call(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ORCHESTRATOR_DELEGATION_REPORT_DIR", str(tmp_path))
        primitives = self._primitives()

        text, handle = _compress_report_for_loop(
            "short report", "q", primitives, "coder_escalation", skip_summary=True,
        )

        primitives.llm_call.assert_not_called()
        assert text == "short report"
        assert handle is None

    def test_default_long_report_still_summarizes_into_handle_text(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ORCHESTRATOR_DELEGATION_REPORT_DIR", str(tmp_path))
        primitives = self._primitives()

        text, handle = _compress_report_for_loop(
            self._LONG, "q", primitives, "coder_escalation",
        )

        assert primitives.llm_call.call_count == 1
        assert primitives.llm_call.call_args.kwargs.get("role") == "worker_summarize"
        assert handle is not None
        assert text.startswith(f"[REPORT_HANDLE id={handle['id']}")
        assert "compact summary" in text

    def test_rescued_delegation_makes_no_summarize_call(self, monkeypatch, tmp_path):
        from src.api.routes.chat_delegation import _architect_delegated_answer

        monkeypatch.setenv("ORCHESTRATOR_DELEGATION_REPORT_DIR", str(tmp_path))
        primitives = MagicMock()
        primitives._backends = {"test": True}
        primitives.total_tokens_generated = 0
        primitives.llm_call = MagicMock(return_value="compact summary")
        state = MagicMock()
        state.tool_registry = None
        mock_cache = MagicMock()
        mock_cache.make_key.return_value = "rescue-key"
        mock_cache.get.return_value = None

        with patch(
            "src.api.routes.chat_delegation._run_architect_decision",
            return_value=("I|brief:investigate|to:coder_escalation", 1, 0),
        ), patch(
            "src.api.routes.chat_delegation._run_specialist_loop",
            return_value=(self._LONG, 0, [], [], False, True, {}, []),
        ), patch(
            "src.delegation_cache.get_delegation_cache",
            return_value=mock_cache,
        ):
            answer, stats = _architect_delegated_answer(
                question="q",
                context="",
                primitives=primitives,
                state=state,
                max_loops=3,
                force_response_on_cap=True,
            )

        primitives.llm_call.assert_not_called()
        assert answer == self._LONG
        assert stats.get("break_reason") == "specialist_report"
        assert len(stats["report_handles"]) == 1
        assert mock_cache.put.call_args.kwargs.get("report_handle") == stats["report_handles"][0]

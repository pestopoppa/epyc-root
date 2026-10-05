"""Tests for graph/answer_resolution.py — answer extraction helpers."""


from src.graph.answer_resolution import (
    _looks_like_prompt_echo,
    _should_attempt_prose_rescue,
    _extract_final_from_raw,
    _extract_prose_answer,
    _rescue_from_last_output,
    _resolve_answer,
)


class TestLooksLikePromptEcho:
    """Test prompt echo detection."""

    def test_detects_answer_with_letter_only(self):
        assert _looks_like_prompt_echo("Answer with the letter only: A, B, C, or D") is True

    def test_detects_question_marker(self):
        assert _looks_like_prompt_echo("Question: What is 2+2?") is True

    def test_detects_options_marker(self):
        assert _looks_like_prompt_echo("Options:\nA. 4\nB. 5") is True

    def test_detects_instruction_marker(self):
        assert _looks_like_prompt_echo("Instruction: summarize the text") is True

    def test_normal_answer_not_echo(self):
        assert _looks_like_prompt_echo("The answer is B") is False

    def test_empty_string(self):
        assert _looks_like_prompt_echo("") is False

    def test_none_input(self):
        assert _looks_like_prompt_echo(None) is False

    def test_case_insensitive(self):
        assert _looks_like_prompt_echo("CHOOSE THE CORRECT answer") is True


class TestShouldAttemptProseRescue:
    """Test prose rescue gating logic."""

    def test_short_prose_answer_yes(self):
        assert _should_attempt_prose_rescue("The answer is B", "") is True

    def test_empty_output_no(self):
        assert _should_attempt_prose_rescue("", "") is False

    def test_whitespace_only_no(self):
        assert _should_attempt_prose_rescue("   \n  ", "") is False

    def test_has_final_in_code_no(self):
        assert _should_attempt_prose_rescue("The answer is B", 'FINAL("B")') is False

    def test_has_code_block_no(self):
        assert _should_attempt_prose_rescue("```python\nprint(42)\n```", "") is False

    def test_prompt_echo_no(self):
        assert _should_attempt_prose_rescue("Question: what is 2+2?", "") is False

    def test_long_output_no(self):
        assert _should_attempt_prose_rescue("x" * 221, "") is False

    def test_exactly_220_chars_yes(self):
        assert _should_attempt_prose_rescue("A" * 220, "") is True

    def test_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_REPL_PROSE_RESCUE", "0")
        assert _should_attempt_prose_rescue("The answer is B", "") is False


class TestExtractFinalFromRaw:
    """Test FINAL() extraction from raw LLM output."""

    def test_single_quoted(self):
        assert _extract_final_from_raw("FINAL('hello')") == "hello"

    def test_double_quoted(self):
        assert _extract_final_from_raw('FINAL("world")') == "world"

    def test_triple_single_quoted(self):
        assert _extract_final_from_raw("FINAL('''multi\nline''')") == "multi\nline"

    def test_triple_double_quoted(self):
        assert _extract_final_from_raw('FINAL("""triple""")') == "triple"

    def test_numeric(self):
        assert _extract_final_from_raw("FINAL(42)") == "42"

    def test_float(self):
        assert _extract_final_from_raw("FINAL(3.14)") == "3.14"

    def test_negative_number(self):
        assert _extract_final_from_raw("FINAL(-7.5)") == "-7.5"

    def test_scientific_notation(self):
        assert _extract_final_from_raw("FINAL(1.5e-3)") == "1.5e-3"

    def test_boolean_true(self):
        assert _extract_final_from_raw("FINAL(True)") == "True"

    def test_boolean_false(self):
        assert _extract_final_from_raw("FINAL(False)") == "False"

    def test_none_value(self):
        assert _extract_final_from_raw("FINAL(None)") == "None"

    def test_no_final(self):
        assert _extract_final_from_raw("The answer is 42") is None

    def test_embedded_in_text(self):
        text = "After analysis, I conclude:\nFINAL('B')\nDone."
        assert _extract_final_from_raw(text) == "B"

    def test_empty_string(self):
        assert _extract_final_from_raw("") is None


class TestExtractProseAnswer:
    """Test prose answer extraction."""

    def test_the_answer_is(self):
        assert _extract_prose_answer("The answer is B") == "B"

    def test_answer_colon(self):
        assert _extract_prose_answer("Answer: C") == "C"

    def test_therefore(self):
        assert _extract_prose_answer("Therefore, the answer is A") == "A"

    def test_so_the_answer(self):
        assert _extract_prose_answer("So the answer is D") == "D"

    def test_i_choose(self):
        assert _extract_prose_answer("I choose B") == "B"

    def test_my_answer_is(self):
        assert _extract_prose_answer("My answer is 42") == "42"

    def test_correct_option(self):
        assert _extract_prose_answer("The correct option is A") == "A"

    def test_bare_letter(self):
        assert _extract_prose_answer("\nB\n") == "B"

    def test_strips_trailing_punctuation(self):
        assert _extract_prose_answer("The answer is B.") == "B"

    def test_no_prose_answer(self):
        assert _extract_prose_answer("I don't know the answer") is None

    def test_empty_string(self):
        assert _extract_prose_answer("") is None


class TestRescueFromLastOutput:
    """Test multi-strategy answer rescue."""

    def test_final_extraction_priority(self):
        text = "The answer is A\nFINAL('B')"
        assert _rescue_from_last_output(text) == "B"

    def test_prose_fallback(self):
        assert _rescue_from_last_output("The answer is C") == "C"

    def test_code_block_fallback(self):
        text = "Here's the solution:\n```python\ndef solve():\n    return 42\n```"
        result = _rescue_from_last_output(text)
        assert result is not None
        assert "solve" in result

    def test_short_code_block_falls_through_to_prose(self):
        text = "```\nA\n```"
        # Code block content "A" is <= 20 chars → code rescue rejected
        # But bare-letter prose regex matches "A" → rescued via prose path
        result = _rescue_from_last_output(text)
        assert result == "A"

    def test_empty_returns_none(self):
        assert _rescue_from_last_output("") is None

    def test_none_returns_none(self):
        assert _rescue_from_last_output(None) is None

    def test_whitespace_returns_none(self):
        assert _rescue_from_last_output("   \n  ") is None


class TestResolveAnswer:
    """Test answer resolution from output + tool outputs."""

    def test_prefers_output(self):
        assert _resolve_answer("direct answer", ["tool result"]) == "direct answer"

    def test_strips_whitespace(self):
        assert _resolve_answer("  padded  ", []) == "padded"

    def test_falls_back_to_tool_outputs(self):
        assert _resolve_answer("", ["result1", "result2"]) == "result1\nresult2"

    def test_empty_both(self):
        assert _resolve_answer("", []) == ""

    def test_whitespace_output_falls_back(self):
        assert _resolve_answer("   ", ["fallback"]) == "fallback"

    def test_none_tool_outputs_filtered(self):
        assert _resolve_answer("", ["good", None, "also good"]) == "good\nalso good"

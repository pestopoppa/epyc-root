"""Tests for context compression (B2)."""

from src.context_compression import (
    CompressorConfig,
    ContextCompressor,
    align_boundary_forward,
    classify_tool_output,
    sanitize_tool_pairs,
    summarize_tool_output,
)


def _msg(role, content="hi", **kw):
    m = {"role": role, "content": content}
    m.update(kw)
    return m


def _tool_call_msg(call_id="tc1"):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": call_id, "function": {"name": "test"}}],
    }


def _tool_result_msg(call_id="tc1", content="result"):
    return {"role": "tool", "tool_call_id": call_id, "content": content}


# ---------------------------------------------------------------------------
# sanitize_tool_pairs
# ---------------------------------------------------------------------------


class TestSanitizeToolPairs:
    def test_empty_messages(self):
        msgs, fixes = sanitize_tool_pairs([])
        assert msgs == []
        assert fixes == 0

    def test_no_orphans(self):
        msgs = [_tool_call_msg("tc1"), _tool_result_msg("tc1")]
        result, fixes = sanitize_tool_pairs(msgs)
        assert fixes == 0
        assert len(result) == 2

    def test_orphaned_result_removed(self):
        msgs = [_msg("user"), _tool_result_msg("orphan")]
        result, fixes = sanitize_tool_pairs(msgs)
        assert fixes == 1
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_orphaned_call_gets_stub(self):
        msgs = [_tool_call_msg("tc1"), _msg("user")]
        result, fixes = sanitize_tool_pairs(msgs)
        assert fixes == 1
        # Should have: tool_call, stub_result, user
        tool_results = [m for m in result if m.get("role") == "tool"]
        assert len(tool_results) == 1
        assert "cleared" in tool_results[0]["content"].lower()

    def test_matched_pairs_untouched(self):
        msgs = [
            _msg("user"),
            _tool_call_msg("tc1"),
            _tool_result_msg("tc1"),
            _msg("assistant", "answer"),
        ]
        result, fixes = sanitize_tool_pairs(msgs)
        assert fixes == 0
        assert len(result) == 4


# ---------------------------------------------------------------------------
# align_boundary_forward
# ---------------------------------------------------------------------------


class TestAlignBoundary:
    def test_no_adjustment_at_user_message(self):
        msgs = [_msg("system"), _msg("user"), _msg("assistant")]
        assert align_boundary_forward(msgs, 1) == 1

    def test_skips_tool_result(self):
        msgs = [_msg("system"), _tool_result_msg("tc1"), _msg("user")]
        assert align_boundary_forward(msgs, 1) == 2

    def test_does_not_skip_complete_tool_pair(self):
        msgs = [_msg("system"), _tool_call_msg("tc1"), _tool_result_msg("tc1"), _msg("user")]
        # Boundary at tool_call (not orphaned tool result) — no adjustment needed
        assert align_boundary_forward(msgs, 1) == 1

    def test_at_end(self):
        msgs = [_msg("user")]
        assert align_boundary_forward(msgs, 1) == 1


# ---------------------------------------------------------------------------
# classify_tool_output
# ---------------------------------------------------------------------------


class TestClassifyToolOutput:
    def test_error_detected(self):
        assert classify_tool_output("Traceback (most recent call last):\n  ...") == "error"

    def test_file_read_detected(self):
        assert classify_tool_output("Contents of /foo/bar.py:\nimport os") == "file_read"

    def test_repl_detected(self):
        from src.repl_environment.types import wrap_tool_output

        assert classify_tool_output(wrap_tool_output("42")) == "repl"

    def test_repl_regex_matches_real_delimiters(self):
        """CF-RX-1: the regex itself matches real output; the ``>>>`` substring
        fallback (which the delimiters also contain) must not be what classifies it."""
        from src.context_compression import _REPL_OUTPUT_RE
        from src.repl_environment.types import (
            TOOL_OUTPUT_END,
            TOOL_OUTPUT_START,
            wrap_tool_output,
        )

        content = wrap_tool_output("line one\nline two: 42")
        match = _REPL_OUTPUT_RE.search(content)
        assert match is not None and match.group(0) == content
        assert content.startswith(TOOL_OUTPUT_START) and content.endswith(TOOL_OUTPUT_END)
        # The pre-fix hand-written end marker is not a real delimiter.
        assert _REPL_OUTPUT_RE.search("<<<TOOL_OUTPUT>>>42<<</TOOL_OUTPUT>>>") is None

    def test_empty_is_other(self):
        assert classify_tool_output("") == "other"


# ---------------------------------------------------------------------------
# summarize_tool_output
# ---------------------------------------------------------------------------


class TestSummarizeToolOutput:
    def test_error_kept_verbatim(self):
        error = "Traceback (most recent call last):\n  File test.py"
        assert summarize_tool_output(error, "error") == error

    def test_file_read_stubbed(self):
        result = summarize_tool_output("Contents of /foo.py:\nimport os\n...", "file_read")
        assert "cleared" in result.lower()

    def test_repl_stubbed(self):
        result = summarize_tool_output("<<<TOOL_OUTPUT>>>42<<</TOOL_OUTPUT>>>", "repl")
        assert "cleared" in result.lower()
        assert "REPL" in result


# ---------------------------------------------------------------------------
# ContextCompressor
# ---------------------------------------------------------------------------


class TestContextCompressor:
    def test_should_compress_below_threshold(self):
        c = ContextCompressor(CompressorConfig(trigger_ratio=0.5))
        assert not c.should_compress(4000, 10000)

    def test_should_compress_above_threshold(self):
        c = ContextCompressor(CompressorConfig(trigger_ratio=0.5))
        assert c.should_compress(6000, 10000)

    def test_no_compression_for_short_conversations(self):
        c = ContextCompressor(CompressorConfig(protect_first_n=3, protect_last_n=5))
        msgs = [_msg("user", f"msg{i}") for i in range(6)]
        result = c.compress(msgs)
        assert result.compressed_count == result.original_count

    def test_compression_preserves_head_and_tail(self):
        c = ContextCompressor(CompressorConfig(
            protect_first_n=2, protect_last_n=2, tool_output_age_threshold=100
        ))
        msgs = [_msg("user", f"msg{i}") for i in range(10)]
        result = c.compress(msgs)
        # Head and tail preserved
        assert result.messages[0]["content"] == "msg0"
        assert result.messages[1]["content"] == "msg1"
        assert result.messages[-2]["content"] == "msg8"
        assert result.messages[-1]["content"] == "msg9"

    def test_tool_output_summarization_triggered(self):
        c = ContextCompressor(CompressorConfig(
            protect_first_n=2, protect_last_n=2, tool_output_age_threshold=3
        ))
        # Build: 2 head msgs, many tool pairs in middle, 2 tail msgs
        msgs = [_msg("system", "sys"), _msg("user", "start")]
        for i in range(5):
            msgs.append(_tool_call_msg(f"tc{i}"))
            msgs.append(_tool_result_msg(f"tc{i}", f"Contents of /file{i}.py:\nimport os"))
        msgs.append(_msg("assistant", "thinking"))
        msgs.append(_msg("user", "final"))
        result = c.compress(msgs)
        assert result.tool_outputs_summarized > 0

    def test_compute_summary_budget(self):
        c = ContextCompressor()
        budget = c.compute_summary_budget(20000)
        assert budget >= 500   # MIN_SUMMARY_TOKENS
        assert budget <= 12000  # MAX_SUMMARY_TOKENS
        assert budget == 1000  # 20000/4 * 0.20 = 1000

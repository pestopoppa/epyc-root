"""Unit tests for vision routing: tool whitelists, executable tools, and stop constants.

All tests mock httpx and OCR service — no live servers required.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Constant relationship tests ─────────────────────────────────────────────


class TestVisionConstants:
    """Tests for vision-related constants in prompt_builders and chat."""

    def test_executable_tools_match_descriptions_keys(self):
        """VISION_REACT_EXECUTABLE_TOOLS must match VISION_TOOL_DESCRIPTIONS keys."""
        from src.prompt_builders import (
            VISION_REACT_EXECUTABLE_TOOLS,
            VISION_TOOL_DESCRIPTIONS,
        )

        assert VISION_REACT_EXECUTABLE_TOOLS == frozenset(VISION_TOOL_DESCRIPTIONS.keys())

    def test_executable_tools_subset_of_whitelist(self):
        """VISION_REACT_EXECUTABLE_TOOLS must be a subset of VISION_REACT_TOOL_WHITELIST."""
        from src.prompt_builders import (
            VISION_REACT_EXECUTABLE_TOOLS,
            VISION_REACT_TOOL_WHITELIST,
        )

        assert VISION_REACT_EXECUTABLE_TOOLS <= VISION_REACT_TOOL_WHITELIST

    def test_qwen_stop_constant_exists(self):
        """QWEN_STOP constant exists and equals '<|im_end|>'."""
        from src.api.routes.chat_utils import QWEN_STOP

        assert QWEN_STOP == "<|im_end|>"

    def test_vision_tool_descriptions_non_empty(self):
        """Each tool description is a non-empty string."""
        from src.prompt_builders import VISION_TOOL_DESCRIPTIONS

        for name, desc in VISION_TOOL_DESCRIPTIONS.items():
            assert isinstance(desc, str), f"Description for '{name}' is not a string"
            assert len(desc) > 10, f"Description for '{name}' is too short"


# ── _execute_vision_tool tests ──────────────────────────────────────────────


def _run_async(coro):
    """Run an async coroutine synchronously for testing."""
    return asyncio.run(coro)


def base64_png_1x1() -> str:
    """Return a tiny valid PNG image for MIME-detection tests."""
    return (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )


class TestExecuteVisionTool:
    """Tests for _execute_vision_tool() dispatch."""

    def test_calculate_tool(self):
        """calculate(expression="2+3") returns '5'."""
        from src.api.routes.chat_vision import _execute_vision_tool

        result = _run_async(_execute_vision_tool('calculate(expression="2+3")', "dummy_b64"))
        assert result == "5"

    def test_get_current_date(self):
        """get_current_date() returns a date string."""
        from src.api.routes.chat_vision import _execute_vision_tool

        result = _run_async(_execute_vision_tool("get_current_date()", "dummy_b64"))
        # Should contain year-month-day pattern
        assert len(result) >= 10
        assert "-" in result

    def test_get_current_time(self):
        """get_current_time() returns an ISO timestamp."""
        from src.api.routes.chat_vision import _execute_vision_tool

        result = _run_async(_execute_vision_tool("get_current_time()", "dummy_b64"))
        assert "T" in result  # ISO format has T separator

    @patch("httpx.AsyncClient")
    def test_ocr_extract_success(self, mock_client_cls):
        """ocr_extract sends POST to port 9001 and returns text."""
        from src.api.routes.chat_vision import _execute_vision_tool

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "Extracted OCR text here"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = _run_async(
            _execute_vision_tool('ocr_extract(image_base64="current")', "test_b64_data")
        )
        assert result == "Extracted OCR text here"

    @patch("httpx.AsyncClient")
    def test_ocr_extract_http_error(self, mock_client_cls):
        """OCR HTTP error returns error message."""
        from src.api.routes.chat_vision import _execute_vision_tool

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = _run_async(_execute_vision_tool('ocr_extract(image_base64="current")', "test_b64"))
        assert "[OCR error: HTTP 500]" in result

    def test_unknown_tool(self):
        """Unknown tool returns error listing available tools."""
        from src.api.routes.chat_vision import _execute_vision_tool

        result = _run_async(_execute_vision_tool('unknown_tool(arg="val")', "dummy_b64"))
        assert "not available" in result
        assert "unknown_tool" in result
        # Should list available tools
        assert "calculate" in result
        assert "ocr_extract" in result

    def test_unparseable_action(self):
        """Unparseable action string returns parse error."""
        from src.api.routes.chat_vision import _execute_vision_tool

        result = _run_async(_execute_vision_tool("this is not a valid action", "dummy_b64"))
        assert "[ERROR: Could not parse action" in result


# ── _safe_eval_math tests ─────────────────────────────────────────────────


class TestSafeEvalMath:
    """Tests for _safe_eval_math — safe arithmetic-only evaluator."""

    def test_basic_addition(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("2 + 3") == 5

    def test_basic_multiplication(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("6 * 7") == 42

    def test_division(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("10 / 4") == 2.5

    def test_floor_division(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("10 // 3") == 3

    def test_modulo(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("10 % 3") == 1

    def test_power(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("2 ** 10") == 1024

    def test_unary_negative(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("-5 + 3") == -2

    def test_complex_expression(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("(2 + 3) * 4 - 1") == 19

    def test_float_literal(self):
        from src.api.routes.chat_vision import _safe_eval_math

        assert _safe_eval_math("3.14 * 2") == pytest.approx(6.28)

    def test_division_by_zero_raises(self):
        from src.api.routes.chat_vision import _safe_eval_math

        with pytest.raises(ZeroDivisionError):
            _safe_eval_math("1 / 0")

    def test_rejects_import(self):
        """__import__('os') must be rejected — this was the original security hole."""
        from src.api.routes.chat_vision import _safe_eval_math

        with pytest.raises(ValueError, match="Unsupported expression node"):
            _safe_eval_math("__import__('os').system('echo pwned')")

    def test_rejects_attribute_access(self):
        """Attribute access like (1).__class__ must be rejected."""
        from src.api.routes.chat_vision import _safe_eval_math

        with pytest.raises(ValueError, match="Unsupported expression node"):
            _safe_eval_math("(1).__class__")

    def test_rejects_function_call(self):
        """Function calls like len('abc') must be rejected."""
        from src.api.routes.chat_vision import _safe_eval_math

        with pytest.raises(ValueError, match="Unsupported expression node"):
            _safe_eval_math("len('abc')")

    def test_rejects_string_literal(self):
        """String literals must be rejected (only int/float allowed)."""
        from src.api.routes.chat_vision import _safe_eval_math

        with pytest.raises(ValueError, match="Unsupported expression node"):
            _safe_eval_math("'hello'")

    def test_rejects_list_comprehension(self):
        """List comprehensions must be rejected."""
        from src.api.routes.chat_vision import _safe_eval_math

        with pytest.raises((ValueError, SyntaxError)):
            _safe_eval_math("[x for x in range(10)]")


# ── _execute_vision_multimodal tests ──────────────────────────────────────


class TestExecuteVisionMultimodal:
    """Tests for _execute_vision_multimodal routing."""

    def test_vl_port_for_role_reads_stack_priors(self, tmp_path: Path):
        """Vision ReAct ports come from generated stack priors when available."""
        from src.api.routes.chat_pipeline.vision_stage import (
            _vl_port_for_role,
        )

        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            """
roles:
  worker_vision:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:9101
  vision_escalation:
    deployment_status: live_stack
    serving:
      ports: [9107]
""",
            encoding="utf-8",
        )

        assert _vl_port_for_role("worker_vision", priors) == 9101
        assert _vl_port_for_role("vision_escalation", priors) == 9107

    def test_vl_port_for_role_falls_back_when_stack_priors_missing(self, tmp_path: Path):
        """Missing generated priors use explicit degraded-mode VL defaults."""
        from src.api.routes.chat_pipeline.vision_stage import (
            _fallback_vl_port_for_role,
            _vl_port_for_role,
        )

        assert _fallback_vl_port_for_role("worker_vision") == 8086
        # 2026-08-01 W1 cutover: was 8087. vision_escalation stopped being its own
        # server and became an alias on worker_vision's :8086 MI210 process, so the
        # degraded-mode default follows PORT_MAP onto the same port. Port 8087 is
        # retired; a fallback still pointing there would route vision escalations
        # at a dead socket.
        assert _fallback_vl_port_for_role("vision_escalation") == 8086
        assert _vl_port_for_role("vision_escalation", tmp_path / "missing.yaml") == 8086

    def test_vl_port_for_role_rejects_stale_degraded_fallback_when_priors_exist(
        self, tmp_path: Path
    ):
        """Present generated priors are authoritative even when a legacy port exists."""
        from src.api.routes.chat_pipeline.vision_stage import _vl_port_for_role

        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            """
roles:
  worker_general:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:9102
      launch:
        modes: [worker_pool]
        entries: []
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="degraded fallback disabled"):
            _vl_port_for_role("vision_escalation", priors)

    def test_returns_none_for_non_vision_role(self):
        """Non-vision roles return None (fall through)."""
        from src.api.routes.chat_pipeline.vision_stage import _execute_vision_multimodal

        request = MagicMock()
        request.image_path = "/some/image.png"
        request.image_base64 = None
        routing = MagicMock()
        result = _run_async(
            _execute_vision_multimodal(
                request, routing, MagicMock(), MagicMock(), 0.0, "frontdoor", "direct"
            )
        )
        assert result is None

    def test_returns_none_without_image(self):
        """Vision role without image returns None (fall through)."""
        from src.api.routes.chat_pipeline.vision_stage import _execute_vision_multimodal

        request = MagicMock()
        request.image_path = None
        request.image_base64 = None
        routing = MagicMock()
        result = _run_async(
            _execute_vision_multimodal(
                request, routing, MagicMock(), MagicMock(), 0.0, "worker_vision", "direct"
            )
        )
        assert result is None

    @patch("src.api.routes.chat_vision._vision_react_mode_answer", new_callable=AsyncMock)
    @patch("src.api.routes.chat_pipeline.vision_stage._vl_port_for_role")
    def test_repl_mode_uses_stack_prior_vl_port(self, mock_port, mock_answer):
        """REPL mode passes the generated-stack-prior VL port to the tool loop."""
        from src.api.routes.chat_pipeline.vision_stage import _execute_vision_multimodal

        mock_port.return_value = 9107
        mock_answer.return_value = ("chart answer", 1, ["describe_image"])

        request = MagicMock()
        request.image_path = None
        request.image_base64 = base64_png_1x1()
        request.prompt = "describe"
        request.context = ""
        request.real_mode = True
        request.force_role = "vision_escalation"
        routing = MagicMock()
        routing.task_id = "test-react"
        routing.routing_strategy = "forced"
        routing.formalization_applied = False
        routing.skill_ids = []
        state = MagicMock()
        state.progress_logger = None

        result = _run_async(
            _execute_vision_multimodal(
                request,
                routing,
                MagicMock(),
                state,
                0.0,
                "vision_escalation",
                "repl",
            )
        )

        assert result is not None
        assert result.answer == "chart answer"
        mock_port.assert_called_once_with("vision_escalation")
        assert mock_answer.await_args.kwargs["vl_port"] == 9107

    @patch("src.api.routes.chat_vision._handle_vision_request", new_callable=AsyncMock)
    def test_direct_mode_calls_handle_vision(self, mock_handle):
        """Direct mode routes to _handle_vision_request."""
        from src.api.routes.chat_pipeline.vision_stage import _execute_vision_multimodal

        mock_handle.return_value = "Paris"

        request = MagicMock()
        request.image_path = "/some/chart.png"
        request.image_base64 = None
        request.real_mode = True
        request.force_role = "worker_vision"
        routing = MagicMock()
        routing.task_id = "test-123"
        routing.routing_strategy = "forced"
        routing.formalization_applied = False
        state = MagicMock()
        state.progress_logger = None

        result = _run_async(
            _execute_vision_multimodal(
                request, routing, MagicMock(), state, 0.0, "worker_vision", "direct"
            )
        )
        assert result is not None
        assert result.answer == "Paris"
        assert result.routed_to == "worker_vision"
        mock_handle.assert_awaited_once()

    @patch("src.api.routes.chat_pipeline.vision_stage._vl_port_for_role")
    @patch("src.api.routes.chat_vision._handle_vision_request", new_callable=AsyncMock)
    def test_image_request_handler_failure_emits_inband_error(self, mock_handle, mock_port):
        """Image request + failing VL handler → in-band vision_unavailable marker.

        MUST NOT return None: a silent text fallthrough would answer BLIND and
        the eval would SCORE the blind answer as wrong (the vl-suite 0/376). The
        in-band ``[ERROR: vision_unavailable: ...]`` marker lets the eval's REL-1
        guard EXCLUDE the row instead.
        """
        from src.api.routes.chat_pipeline.vision_stage import _execute_vision_multimodal

        mock_handle.side_effect = RuntimeError("All vision paths failed")
        mock_port.return_value = 8086

        request = MagicMock()
        request.image_path = "/some/image.png"
        request.image_base64 = None
        request.real_mode = True
        routing = MagicMock()
        routing.task_id = "test-err"
        routing.routing_strategy = "vision_input"
        routing.formalization_applied = False
        routing.skill_ids = []
        state = MagicMock()
        state.progress_logger = None

        result = _run_async(
            _execute_vision_multimodal(
                request, routing, MagicMock(), state, 0.0, "worker_vision", "direct"
            )
        )
        assert result is not None, "image request must never silently fall through to text"
        assert result.answer.startswith("[ERROR: vision_unavailable:")
        assert "RuntimeError" in result.answer
        assert result.error_code == 503
        assert result.routed_to == "worker_vision"

    def test_inband_error_answer_matches_eval_rel1_guard(self):
        """The emitted marker is caught by eval_tower's _inband_error_text guard."""
        from src.api.routes.chat_pipeline.vision_stage import _vision_unavailable_response

        routing = MagicMock()
        routing.routing_strategy = "vision_input"
        routing.formalization_applied = False
        routing.skill_ids = []
        request = MagicMock()
        request.real_mode = True

        resp = _vision_unavailable_response(
            request, routing, "worker_vision", "direct", 0.0,
            "RuntimeError: All vision paths failed",
        )
        # Mirror the eval-tower REL-1 guard: anchored [ERROR: prefix after lstrip.
        assert resp.answer.lstrip().startswith("[ERROR:")

    def test_repl_image_not_found_emits_inband_error(self):
        """REPL mode, image path missing on disk → in-band error, not silent None."""
        from src.api.routes.chat_pipeline.vision_stage import _execute_vision_multimodal

        missing = MagicMock()
        missing.exists.return_value = False
        with patch(
            "src.api.routes.path_validation.validate_api_path", return_value=missing
        ):
            request = MagicMock()
            request.image_path = "/nope/missing.png"
            request.image_base64 = None
            request.real_mode = True
            request.prompt = "describe"
            request.context = ""
            routing = MagicMock()
            routing.task_id = "test-missing"
            routing.routing_strategy = "vision_input"
            routing.formalization_applied = False
            routing.skill_ids = []
            state = MagicMock()
            state.progress_logger = None

            result = _run_async(
                _execute_vision_multimodal(
                    request, routing, MagicMock(), state, 0.0, "worker_vision", "repl"
                )
            )
        assert result is not None
        assert result.answer.startswith("[ERROR: vision_unavailable:")
        assert "FileNotFoundError" in result.answer

    def test_vision_escalation_role_accepted(self):
        """vision_escalation role is accepted (not just worker_vision)."""
        from src.api.routes.chat_pipeline.vision_stage import _VISION_ROLES

        assert "worker_vision" in _VISION_ROLES
        assert "vision_escalation" in _VISION_ROLES

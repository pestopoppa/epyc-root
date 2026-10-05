#!/usr/bin/env python3
"""Unit tests for OpenAI-compatible API models."""

import importlib.util
import sys
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

# Load the models file directly to avoid src.api.__init__ which transitively
# imports pydantic_graph and other heavy dependencies not needed for unit tests.
_ROOT = Path(__file__).resolve().parents[2] / "src" / "api" / "models"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / f"{name.split('.')[-1]}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module("src.api.models.openai")
OpenAIChatRequest = _mod.OpenAIChatRequest
OpenAIChatResponse = _mod.OpenAIChatResponse
OpenAIChoice = _mod.OpenAIChoice
OpenAIMessage = _mod.OpenAIMessage
OpenAIModelInfo = _mod.OpenAIModelInfo
OpenAIModelsResponse = _mod.OpenAIModelsResponse
OpenAIUsage = _mod.OpenAIUsage


class TestOpenAIMessage:
    """Test OpenAIMessage validation."""

    def test_valid_message(self):
        msg = OpenAIMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_role_required(self):
        with pytest.raises(ValidationError):
            OpenAIMessage(content="Hello")  # type: ignore[call-arg]

    def test_content_required(self):
        with pytest.raises(ValidationError):
            OpenAIMessage(role="user")  # type: ignore[call-arg]

    def test_system_role(self):
        msg = OpenAIMessage(role="system", content="You are a helper")
        assert msg.role == "system"

    def test_assistant_role(self):
        msg = OpenAIMessage(role="assistant", content="Sure!")
        assert msg.role == "assistant"

    def test_assistant_tool_calls_allow_null_content(self):
        msg = OpenAIMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": '{"query":"x"}'},
                }
            ],
        )

        assert msg.content is None
        assert msg.tool_calls[0]["function"]["name"] == "web_search"

    def test_tool_result_role(self):
        msg = OpenAIMessage(role="tool", tool_call_id="call_1", content="result")
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_1"

    def test_content_still_required_without_tool_calls(self):
        with pytest.raises(ValidationError):
            OpenAIMessage(role="assistant", content=None)


class TestOpenAIChatRequest:
    """Test OpenAIChatRequest field constraints."""

    def _messages(self):
        return [OpenAIMessage(role="user", content="Hi")]

    def test_defaults(self):
        req = OpenAIChatRequest(messages=self._messages())
        assert req.model == "orchestrator"
        assert req.temperature == 0.0
        assert req.top_p is None
        assert req.top_k is None
        assert req.seed is None
        assert req.max_tokens == 1024
        assert req.stream is False
        assert req.tools is None
        assert req.tool_choice is None
        assert req.x_orchestrator_role is None
        assert req.x_show_routing is False

    def test_native_tools_preserved(self):
        req = OpenAIChatRequest(
            messages=self._messages(),
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web",
                        "parameters": {"type": "object"},
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "web_search"}},
        )

        assert req.tools[0]["function"]["name"] == "web_search"
        assert req.tool_choice["function"]["name"] == "web_search"

    def test_temperature_lower_bound(self):
        req = OpenAIChatRequest(messages=self._messages(), temperature=0.0)
        assert req.temperature == 0.0

    def test_temperature_upper_bound(self):
        req = OpenAIChatRequest(messages=self._messages(), temperature=2.0)
        assert req.temperature == 2.0

    def test_temperature_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), temperature=-0.1)

    def test_temperature_above_two_rejected(self):
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), temperature=2.1)

    def test_sampling_overrides_are_preserved(self):
        req = OpenAIChatRequest(
            messages=self._messages(),
            top_p=0.8,
            top_k=64,
            seed=1234,
        )

        assert req.top_p == 0.8
        assert req.top_k == 64
        assert req.seed == 1234

    def test_top_p_bounds(self):
        assert OpenAIChatRequest(messages=self._messages(), top_p=0.0).top_p == 0.0
        assert OpenAIChatRequest(messages=self._messages(), top_p=1.0).top_p == 1.0
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), top_p=-0.1)
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), top_p=1.1)

    def test_top_k_lower_bound(self):
        assert OpenAIChatRequest(messages=self._messages(), top_k=1).top_k == 1
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), top_k=0)

    def test_max_tokens_lower_bound(self):
        req = OpenAIChatRequest(messages=self._messages(), max_tokens=1)
        assert req.max_tokens == 1

    def test_max_tokens_upper_bound(self):
        req = OpenAIChatRequest(messages=self._messages(), max_tokens=32768)
        assert req.max_tokens == 32768

    def test_max_tokens_zero_rejected(self):
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), max_tokens=0)

    def test_max_tokens_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=self._messages(), max_tokens=32769)

    def test_messages_required(self):
        with pytest.raises(ValidationError):
            OpenAIChatRequest()  # type: ignore[call-arg]


class TestOpenAIChatResponse:
    """Test OpenAIChatResponse factory defaults."""

    def test_id_format(self):
        resp = OpenAIChatResponse(choices=[])
        assert resp.id.startswith("chatcmpl-")
        assert len(resp.id) == len("chatcmpl-") + 8

    def test_unique_ids(self):
        r1 = OpenAIChatResponse(choices=[])
        r2 = OpenAIChatResponse(choices=[])
        assert r1.id != r2.id

    def test_created_timestamp(self):
        before = int(time.time())
        resp = OpenAIChatResponse(choices=[])
        after = int(time.time())
        assert before <= resp.created <= after

    def test_object_type(self):
        resp = OpenAIChatResponse(choices=[])
        assert resp.object == "chat.completion"

    def test_with_choice_and_usage(self):
        choice = OpenAIChoice(
            index=0,
            message=OpenAIMessage(role="assistant", content="Hi"),
            finish_reason="stop",
        )
        usage = OpenAIUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        resp = OpenAIChatResponse(choices=[choice], usage=usage)
        assert len(resp.choices) == 1
        assert resp.usage.total_tokens == 15


class TestOpenAIUsage:
    """Test OpenAIUsage defaults."""

    def test_defaults(self):
        usage = OpenAIUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestOpenAIModelsResponse:
    """Test OpenAIModelsResponse construction."""

    def test_empty_list(self):
        resp = OpenAIModelsResponse(data=[])
        assert resp.object == "list"
        assert resp.data == []

    def test_with_models(self):
        m1 = OpenAIModelInfo(id="model-a")
        m2 = OpenAIModelInfo(id="model-b")
        resp = OpenAIModelsResponse(data=[m1, m2])
        assert len(resp.data) == 2
        assert resp.data[0].id == "model-a"
        assert resp.data[0].owned_by == "orchestrator"

    def test_model_info_defaults(self):
        info = OpenAIModelInfo(id="test")
        assert info.object == "model"
        assert info.owned_by == "orchestrator"
        assert isinstance(info.created, int)


class TestMaxEscalationDescription:
    """HS-4 P4-pre: the field must describe what it does today (recorded, not enforced)."""

    def test_x_max_escalation_description_names_the_enforcement_gap(self):
        desc = OpenAIChatRequest.model_fields["x_max_escalation"].description
        assert desc is not None
        lowered = desc.lower()
        # Must NOT claim the cap is enforced.
        assert "prevents escalation beyond" not in lowered
        # Must say it is metadata-only / not enforced, and point at P4 for enforcement.
        assert "not enforced" in lowered
        assert "metadata" in lowered
        assert "p4" in lowered


class TestFieldDescriptionsMatchSeamBehaviour:
    """Truth-in-advertising guards (HS-4 P4-pre follow-up).

    Each /v1 field description must name what openai_compat.py actually does
    with the field today. If a behaviour change outruns the docs, the matching
    assertion here trips. Same shape as ``TestMaxEscalationDescription``.
    """

    @staticmethod
    def _desc(name: str) -> str:
        desc = OpenAIChatRequest.model_fields[name].description
        assert desc is not None, f"{name} has no description"
        return desc.lower()

    def test_x_force_model_says_it_is_a_role_label_not_a_registry_model(self):
        d = self._desc("x_force_model")
        assert "force a specific model by registry name" not in d
        assert "does not select a model by registry name" in d
        assert "x_orchestrator_role" in d
        assert "not resolved" in d

    def test_x_orchestrator_role_names_validation_and_vision_limit(self):
        # HS-OD-7: the override IS validated now; the description must say so
        # and must no longer claim the opposite.
        d = self._desc("x_orchestrator_role")
        assert "bypassing frontdoor routing" not in d
        assert "not validated" not in d
        assert "validated" in d and "422" in d and "/v1/models" in d
        assert "vision" in d and "ignored" in d

    def test_x_force_role_is_the_highest_precedence_role_override(self):
        d = self._desc("x_force_role")
        assert "highest-precedence role override" in d
        assert "/v1/models" in d
        assert "x_force_model" in d and "deprecated" in d

    def test_x_force_model_is_marked_deprecated_in_the_schema(self):
        # HS-OD-3: the alias stays accepted but advertises itself as deprecated.
        schema = OpenAIChatRequest.model_json_schema()["properties"]
        assert schema["x_force_model"].get("deprecated") is True
        assert schema["x_force_role"].get("deprecated") is not True
        assert "deprecated" in self._desc("x_force_model")

    def test_x_disable_repl_names_the_paths_that_do_not_consult_it(self):
        d = self._desc("x_disable_repl")
        assert "not consulted" in d
        assert "client" in d and "vision" in d
        assert "no executor" in d

    def test_x_session_id_is_recorded_only_and_names_the_guard(self):
        d = self._desc("x_session_id")
        assert "p1/p3 key their stores" not in d
        assert "recorded only" in d
        assert "no store is keyed" in d
        assert "x_show_routing" in d
        assert "422" in d and "v1_client_session_guard" in d

    def test_x_user_id_is_recorded_only(self):
        d = self._desc("x_user_id")
        assert "p2 keys the user profile" not in d
        assert "recorded only" in d
        assert "no user profile" in d
        assert "x_show_routing" in d

    def test_x_memory_names_the_metadata_visibility_condition(self):
        d = self._desc("x_memory")
        assert "not_implemented" in d
        assert "x_show_routing" in d

    def test_x_tool_mode_names_repl_rendering_and_client_refusals(self):
        d = self._desc("x_tool_mode")
        assert "never returned" in d
        assert "422" in d and "400" in d
        assert "neither mode escalates" in d

    def test_max_tokens_says_it_is_not_the_repl_token_budget(self):
        d = self._desc("max_tokens")
        assert "not the token budget" in d
        assert "1024" in d and "500" in d
        assert "vision" in d
        assert "max_completion_tokens" in d

    def test_temperature_says_default_is_not_forwarded(self):
        d = self._desc("temperature")
        assert "not forwarded" in d
        assert "explicitly" in d
        assert "vision" in d

    @pytest.mark.parametrize("name", ["top_p", "top_k", "seed"])
    def test_sampling_overrides_name_the_vision_gap(self, name):
        d = self._desc(name)
        assert "forwarded when set" in d
        assert "vision" in d

    def test_tools_says_repl_mode_never_returns_tool_calls(self):
        d = self._desc("tools")
        assert "never returned as tool_calls" in d
        assert "x_tool_mode='client'" in d
        assert "x_disable_repl" in d

    def test_tool_choice_says_it_is_enforced_only_in_client_mode(self):
        d = self._desc("tool_choice")
        assert "only with x_tool_mode='client'" in d
        assert "not enforced" in d

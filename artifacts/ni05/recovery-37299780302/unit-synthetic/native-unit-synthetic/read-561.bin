from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest

from src.api.routes import openai_compat
from src.api.models import OpenAIChatRequest, OpenAIMessage


def test_available_roles_degrades_to_compatibility_aliases(monkeypatch):
    monkeypatch.setattr(openai_compat, "_live_stack_role_ids", lambda: [])

    assert openai_compat.available_roles() == ["orchestrator", "architect", "worker"]
    assert openai_compat._degraded_available_roles() == []


def test_degraded_available_roles_does_not_reconstruct_manifest_topology() -> None:
    assert openai_compat._degraded_available_roles() == []


def test_available_roles_uses_stack_prior_roles_when_present(monkeypatch):
    monkeypatch.setattr(
        openai_compat,
        "_live_stack_role_ids",
        lambda: ["frontdoor", "toolrunner", "worker_general"],
    )

    assert openai_compat.available_roles() == [
        "orchestrator",
        "architect",
        "worker",
        "frontdoor",
        "toolrunner",
        "worker_general",
    ]


def test_available_roles_canonicalizes_live_stack_role_ids(monkeypatch):
    monkeypatch.setattr(
        openai_compat,
        "_live_stack_role_ids",
        lambda: [
            "frontdoor",
            "worker_fast",
            "worker_general",
            "coder",
            "worker_general",
        ],
    )

    assert openai_compat.available_roles() == [
        "orchestrator",
        "architect",
        "worker",
        "frontdoor",
        "worker_general",
        "coder_escalation",
    ]


def test_ordered_live_role_ids_uses_stack_prior_topology():
    def record(*ports: int, endpoint: str | None = None) -> dict:
        serving = {"ports": list(ports)}
        if endpoint is not None:
            serving["endpoint"] = endpoint
        return {"serving": serving}

    assert openai_compat._ordered_live_role_ids(
        {
            "toolrunner": record(8072),
            "worker_general": record(8072, 8082),
            "frontdoor": record(8080, 8070, endpoint="http://localhost:8070"),
            "vision_escalation": record(8087),
            "worker_summarize": record(8070),
        }
    ) == [
        "frontdoor",
        "worker_summarize",
        "toolrunner",
        "worker_general",
        "vision_escalation",
    ]


def test_history_message_dict_preserves_native_tool_fields():
    message = OpenAIMessage(
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

    data = openai_compat._history_message_dict(message)

    assert data["role"] == "assistant"
    assert data["content"] == ""
    assert data["tool_calls"][0]["id"] == "call_1"


def test_extract_openai_content_parses_single_data_url_image() -> None:
    payload = base64.b64encode(b"image-bytes").decode("ascii")

    parsed = openai_compat._extract_openai_content(
        [
            {"type": "text", "text": "What is shown?"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{payload}"},
            },
        ],
        parse_images=True,
    )

    assert parsed.text == "What is shown?"
    assert parsed.image_base64 == payload
    assert openai_compat._extract_text(
        [
            {"type": "text", "text": "What is shown?"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{payload}"},
            },
        ]
    ) == "What is shown?"


def test_extract_openai_content_rejects_remote_image_urls() -> None:
    with pytest.raises(ValueError, match="data:image"):
        openai_compat._extract_openai_content(
            [
                {"type": "text", "text": "What is shown?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            ],
            parse_images=True,
        )


def test_extract_openai_content_rejects_multiple_images() -> None:
    payload = base64.b64encode(b"image-bytes").decode("ascii")

    with pytest.raises(ValueError, match="Only one"):
        openai_compat._extract_openai_content(
            [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{payload}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{payload}"}},
            ],
            parse_images=True,
        )


def test_sampling_kwargs_omits_default_temperature_when_caller_omits_it() -> None:
    request = OpenAIChatRequest(messages=[OpenAIMessage(role="user", content="Hi")])

    assert openai_compat._sampling_kwargs(request) == {}


def test_sampling_kwargs_preserves_explicit_greedy_temperature_and_overrides() -> None:
    request = OpenAIChatRequest(
        messages=[OpenAIMessage(role="user", content="Hi")],
        temperature=0.0,
        seed=1234,
        top_p=0.8,
        top_k=64,
    )

    assert openai_compat._sampling_kwargs(request) == {
        "temperature": 0.0,
        "seed": 1234,
        "top_p": 0.8,
        "top_k": 64,
    }


def test_sampling_metadata_is_stable_and_absent_when_empty() -> None:
    assert openai_compat._sampling_metadata({}) == {}
    assert openai_compat._sampling_metadata({"seed": 2, "temperature": 0.1}) == {
        "sampling": {"seed": 2, "temperature": 0.1}
    }


@pytest.mark.asyncio
async def test_openai_vision_completion_uses_existing_vision_handler(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_handle_vision_request(
        request,
        primitives,
        state,
        task_id,
        force_server=None,
    ):
        captured["prompt"] = request.prompt
        captured["image_base64"] = request.image_base64
        captured["role"] = request.role
        captured["task_id"] = task_id
        captured["force_server"] = force_server
        captured["primitives"] = primitives
        captured["state"] = state
        return "vision answer"

    from src.api.routes import chat_vision

    monkeypatch.setattr(chat_vision, "_handle_vision_request", fake_handle_vision_request)
    primitives = SimpleNamespace()
    state = SimpleNamespace()

    answer = await openai_compat._run_openai_vision_completion(
        prompt="What is shown?",
        context="System: be concise",
        image_base64="ZmFrZQ==",
        role="worker_vision",
        primitives=primitives,
        state=state,
        task_id="chatcmpl-test",
    )

    assert answer == "vision answer"
    assert captured["prompt"] == "System: be concise\n\nUser: What is shown?"
    assert captured["image_base64"] == "ZmFrZQ=="
    assert captured["role"] == "worker_vision"
    assert captured["force_server"] == "worker_vision"
    assert captured["task_id"] == "chatcmpl-test"
    assert captured["primitives"] is primitives
    assert captured["state"] is state


def test_context_parts_render_tool_history_and_native_repl_bridge():
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": '{"query":"x"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "result text"},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]

    parts = openai_compat._context_parts_from_history(
        history,
        tools,
        {"type": "function", "function": {"name": "web_search"}},
    )
    rendered = "\n".join(parts)

    assert 'Assistant tool_calls: call_1: web_search({"query":"x"})' in rendered
    assert "Tool result call_1: result text" in rendered
    assert 'result = CALL("tool_name", arg=value)' in rendered
    assert "Tool choice policy: web_search." in rendered
    assert "- web_search - Search the web" in rendered


def test_context_parts_honor_tool_choice_none():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            },
        }
    ]

    parts = openai_compat._context_parts_from_history([], tools, "none")

    assert parts == []


def test_openai_metadata_reports_internal_repl_tool_contract():
    repl = SimpleNamespace(
        _tool_invocations=2,
        _invoked_tools=[
            SimpleNamespace(tool_name="web_search"),
            SimpleNamespace(tool_name="read_file"),
        ],
    )
    meta = {"role": "frontdoor"}

    result = openai_compat._apply_openai_tool_contract_metadata(
        meta,
        request_tools=[{"type": "function", "function": {"name": "web_search"}}],
        repl=repl,
    )

    assert result["native_tool_contract"] == "internal_repl_execution"
    assert result["response_tool_calls"] == "not_emitted"
    assert result["tools_used"] == 2
    assert result["tools_called"] == ["web_search", "read_file"]

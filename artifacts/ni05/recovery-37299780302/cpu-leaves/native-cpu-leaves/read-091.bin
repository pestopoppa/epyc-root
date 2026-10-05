"""Tests for AutoPilot planner provider helpers."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

planner_providers = importlib.import_module("planner_providers")


class FakePlannerProvider:
    supports_resume = False

    def __init__(self, name: str, responses: list[planner_providers.PlannerProviderResult]):
        self.name = name
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def invoke(
        self,
        prompt: str,
        *,
        role: str,
        session_id: str | None = None,
        timeout: int = 300,
        cwd: Path | str | None = None,
    ) -> planner_providers.PlannerProviderResult:
        self.calls.append(
            {
                "prompt": prompt,
                "role": role,
                "session_id": session_id,
                "timeout": timeout,
                "cwd": cwd,
            }
        )
        result = self.responses.pop(0)
        result.provider = self.name
        result.role = role
        return result


def test_claude_provider_does_not_resume_or_persist_session_by_default(tmp_path) -> None:
    captured: dict[str, Any] = {}

    def fake_invoke(prompt, *, session_id=None, timeout=300, cwd=None):
        captured["prompt"] = prompt
        captured["session_id"] = session_id
        captured["timeout"] = timeout
        captured["cwd"] = cwd
        return "ok", "new-session"

    provider = planner_providers.ClaudePlannerProvider(invoke_fn=fake_invoke)

    assert provider.supports_resume is False
    result = provider.invoke(
        "prompt",
        role="draft",
        session_id="old-session",
        timeout=7,
        cwd=tmp_path,
    )

    assert result.ok is True
    assert result.session_id is None
    assert captured == {
        "prompt": "prompt",
        "session_id": None,
        "timeout": 7,
        "cwd": tmp_path,
    }


def test_parse_codex_jsonl_agent_message() -> None:
    output = "\n".join(
        [
            json.dumps({"type": "session.started"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "hello"},
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": " world"},
                }
            ),
        ]
    )

    assert planner_providers.parse_codex_jsonl(output) == "hello world"


def test_parse_codex_jsonl_message_content_blocks() -> None:
    output = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "structured"},
                    {"type": "output_text", "text": " output"},
                ],
            },
        }
    )

    assert planner_providers.parse_codex_jsonl(output) == "structured output"


def test_parse_codex_jsonl_falls_back_to_raw_output() -> None:
    output = "plain text result"

    assert planner_providers.parse_codex_jsonl(output) == output


def test_parse_openai_chat_response_message_content() -> None:
    data = {"choices": [{"message": {"content": "local draft"}}]}

    assert planner_providers.parse_openai_chat_response(data) == "local draft"


def test_local_planner_provider_posts_role_scoped_payload(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raised"] = True

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "draft text"}}]}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    def fake_archive(prompt, payload, result, response_data, *, url):
        captured["archive"] = {
            "prompt": prompt,
            "payload": payload,
            "provider": result.provider,
            "response": response_data,
            "url": url,
        }

    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_call", fake_archive)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)

    provider = planner_providers.LocalPlannerProvider(
        url="http://local/v1/chat/completions",
        role="ingest_long_context",
        model="ingest_long_context",
        temperature=0.1,
        top_p=0.9,
        top_k=40,
        seed=123,
        max_tokens=777,
        name="local_ingest",
    )
    result = provider.invoke("planner prompt", role="draft", timeout=9)

    assert result.ok is True
    assert result.provider == "local_ingest"
    assert result.text == "draft text"
    assert captured["timeout"] == 9
    assert captured["url"] == "http://local/v1/chat/completions"
    content = captured["payload"]["messages"][0]["content"]
    assert content.startswith("CRITICAL OUTPUT CONTRACT FOR THIS LOCAL AUTOPILOT DRAFT:")
    assert content.endswith(
        "- If no high-confidence action is justified, emit the safest valid fallback action from the prompt.\n"
    )
    assert "\nplanner prompt\n" in content
    assert captured["payload"] == {
        "model": "ingest_long_context",
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 777,
        "stream": False,
        "x_orchestrator_role": "ingest_long_context",
        "x_disable_repl": True,
        "top_p": 0.9,
        "top_k": 40,
        "seed": 123,
    }
    assert captured["archive"]["url"] == "http://local/v1/chat/completions"


def test_local_planner_contract_wraps_draft_and_critique(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_ACTION_CONTRACT", raising=False)
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_CRITIQUE_CONTRACT", raising=False)

    provider = planner_providers.LocalPlannerProvider()

    draft_content = provider._payload("planner prompt", planner_role="draft")["messages"][0][
        "content"
    ]
    critique_content = provider._payload("planner prompt", planner_role="critique")["messages"][0][
        "content"
    ]

    assert draft_content.startswith("CRITICAL OUTPUT CONTRACT")
    assert "must be one JSON object, not a list or array" in draft_content
    assert "\nplanner prompt\n" in draft_content
    assert critique_content.startswith("CRITICAL OUTPUT CONTRACT FOR THIS LOCAL AUTOPILOT CRITIQUE")
    assert "\nplanner prompt\n" in critique_content


def test_local_planner_contract_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_ACTION_CONTRACT", "0")
    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_CRITIQUE_CONTRACT", "0")

    provider = planner_providers.LocalPlannerProvider()

    draft_content = provider._payload("planner prompt", planner_role="draft")["messages"][0][
        "content"
    ]
    critique_content = provider._payload("planner prompt", planner_role="critique")["messages"][0][
        "content"
    ]

    assert draft_content == "planner prompt"
    assert critique_content == "planner prompt"


def test_local_briefed_provider_briefs_then_drafts(monkeypatch, tmp_path) -> None:
    records: list[dict[str, Any]] = []
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_append_planner_archive", records.append)

    brief_provider = FakePlannerProvider(
        "local_ingest_brief",
        [
            planner_providers.PlannerProviderResult(
                provider="local_ingest_brief",
                role="brief",
                ok=True,
                text="Allowed Actions: numeric_trial only. Safe fallback: memrl_retrieval.",
            )
        ],
    )
    draft_text = (
        "```json:autopilot_actions\n"
        '{"type":"numeric_trial","surface":"memrl_retrieval","params":{}}\n'
        "```\n\n"
        "```json:autopilot_rationale\n"
        '{"falsifier":"no replayable evidence"}\n'
        "```\n"
    )
    draft_provider = FakePlannerProvider(
        "local_frontdoor_draft",
        [
            planner_providers.PlannerProviderResult(
                provider="local_frontdoor_draft",
                role="draft",
                ok=True,
                text=draft_text,
            )
        ],
    )
    provider = planner_providers.LocalBriefedPlannerProvider(
        name="local_brief_frontdoor",
        brief_provider=brief_provider,
        draft_provider=draft_provider,
    )

    result = provider.invoke("FULL CONTROLLER PROMPT", role="draft", timeout=17, cwd=tmp_path)

    assert result.ok is True
    assert result.provider == "local_brief_frontdoor"
    assert result.text == draft_text
    assert brief_provider.calls[0]["role"] == "brief"
    assert brief_provider.calls[0]["timeout"] == 17
    assert brief_provider.calls[0]["cwd"] == tmp_path
    assert "CRITICAL OUTPUT CONTRACT FOR THIS LOCAL AUTOPILOT BRIEF" in (
        brief_provider.calls[0]["prompt"]
    )
    assert "FULL CONTROLLER PROMPT" in brief_provider.calls[0]["prompt"]
    assert draft_provider.calls[0]["role"] == "draft"
    assert "Controller Prompt Brief" in draft_provider.calls[0]["prompt"]
    assert "must be one JSON\nobject, not a list or array" in draft_provider.calls[0]["prompt"]
    assert "FULL CONTROLLER PROMPT" not in draft_provider.calls[0]["prompt"]
    assert "Original controller prompt length: 22 chars" in draft_provider.calls[0]["prompt"]
    assert records[-1]["provider"] == "local_brief_frontdoor"
    assert records[-1]["local_briefed_planner"]["brief_ok"] is True
    assert records[-1]["local_briefed_planner"]["draft_ok"] is True


def test_local_briefed_provider_stops_when_brief_fails(monkeypatch) -> None:
    records: list[dict[str, Any]] = []
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_append_planner_archive", records.append)

    brief_provider = FakePlannerProvider(
        "local_ingest_brief",
        [
            planner_providers.PlannerProviderResult(
                provider="local_ingest_brief",
                role="brief",
                ok=False,
                error="context too long",
            )
        ],
    )
    draft_provider = FakePlannerProvider("local_frontdoor_draft", [])
    provider = planner_providers.LocalBriefedPlannerProvider(
        brief_provider=brief_provider,
        draft_provider=draft_provider,
    )

    result = provider.invoke("prompt", role="draft")

    assert result.ok is False
    assert result.error == "brief stage failed: context too long"
    assert draft_provider.calls == []
    assert records[-1]["local_briefed_planner"]["brief_ok"] is False
    assert records[-1]["local_briefed_planner"]["draft_provider"] == ""


def test_local_briefed_provider_passes_critique_through_without_brief(monkeypatch) -> None:
    records: list[dict[str, Any]] = []
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_append_planner_archive", records.append)

    brief_provider = FakePlannerProvider("local_ingest_brief", [])
    draft_provider = FakePlannerProvider(
        "local_worker",
        [
            planner_providers.PlannerProviderResult(
                provider="local_worker",
                role="critique",
                ok=True,
                text="```json:autopilot_critique\n"
                '{"decision":"approve","confidence":0.9,"issues":[]}\n'
                "```",
            )
        ],
    )
    provider = planner_providers.LocalBriefedPlannerProvider(
        name="local_brief_worker",
        brief_provider=brief_provider,
        draft_provider=draft_provider,
    )

    result = provider.invoke("critique prompt", role="critique", timeout=31)

    assert result.ok is True
    assert result.provider == "local_brief_worker"
    assert brief_provider.calls == []
    assert draft_provider.calls[0]["prompt"] == "critique prompt"
    assert draft_provider.calls[0]["role"] == "critique"
    assert draft_provider.calls[0]["timeout"] == 31
    assert records[-1]["local_briefed_planner"]["draft_provider"] == "local_worker"


def test_local_planner_default_url_uses_ipv4_loopback(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_URL", raising=False)

    provider = planner_providers.LocalPlannerProvider()

    assert provider._url == "http://127.0.0.1:8000/v1/chat/completions"


def test_local_planner_retries_transient_api_reload_failure(monkeypatch) -> None:
    captured: dict[str, Any] = {"calls": 0, "sleeps": []}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "draft after retry"}}]}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            captured["calls"] += 1
            if captured["calls"] == 1:
                raise planner_providers.httpx.ConnectError("api reload gap")
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_HTTP_ATTEMPTS", "2")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_call", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.time, "sleep", lambda seconds: captured["sleeps"].append(seconds)
    )

    provider = planner_providers.LocalPlannerProvider(
        url="http://127.0.0.1:8000/v1/chat/completions",
        role="worker_general",
        model="worker_general",
    )
    result = provider.invoke("planner prompt", role="draft", timeout=9)

    assert result.ok is True
    assert result.text == "draft after retry"
    assert captured["calls"] == 2
    assert captured["sleeps"] == [2.0]


def test_local_planner_retries_error_payload(monkeypatch) -> None:
    captured: dict[str, Any] = {"calls": 0, "sleeps": []}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            if captured["calls"] == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "[ERROR: admission] Backend queue full for http://localhost:8072"
                            }
                        }
                    ]
                }
            return {"choices": [{"message": {"content": "draft after queue clears"}}]}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            captured["calls"] += 1
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_HTTP_ATTEMPTS", "2")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_call", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.time,
        "sleep",
        lambda seconds: captured["sleeps"].append(seconds),
    )

    provider = planner_providers.LocalPlannerProvider(
        url="http://127.0.0.1:8000/v1/chat/completions",
        role="worker_general",
        model="worker_general",
    )
    result = provider.invoke("planner prompt", role="draft", timeout=9)

    assert result.ok is True
    assert result.text == "draft after queue clears"
    assert captured["calls"] == 2
    assert captured["sleeps"] == [2.0]


def test_local_planner_does_not_retry_deterministic_bad_request_payload(monkeypatch) -> None:
    captured: dict[str, Any] = {"calls": 0, "sleeps": []}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "[ERROR: Inference failed: chat_completions stream failed: "
                                "Client error '400 Bad Request' for url "
                                "'http://localhost:8072/v1/chat/completions']"
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            captured["calls"] += 1
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_HTTP_ATTEMPTS", "4")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_call", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.time,
        "sleep",
        lambda seconds: captured["sleeps"].append(seconds),
    )

    provider = planner_providers.LocalPlannerProvider(
        url="http://127.0.0.1:8000/v1/chat/completions",
        role="worker_general",
        model="worker_general",
    )
    result = provider.invoke("planner prompt", role="draft", timeout=9)

    assert result.ok is False
    assert "400 Bad Request" in result.error
    assert captured["calls"] == 1
    assert captured["sleeps"] == []


def test_local_planner_retries_mock_payload(monkeypatch) -> None:
    captured: dict[str, Any] = {"calls": 0, "sleeps": []}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            if captured["calls"] == 1:
                return {"choices": [{"message": {"content": "[MOCK] Processed via worker"}}]}
            return {"choices": [{"message": {"content": "real draft after worker ready"}}]}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            captured["calls"] += 1
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_HTTP_ATTEMPTS", "2")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_call", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.time,
        "sleep",
        lambda seconds: captured["sleeps"].append(seconds),
    )

    provider = planner_providers.LocalPlannerProvider(
        url="http://127.0.0.1:8000/v1/chat/completions",
        role="worker_general",
        model="worker_general",
    )
    result = provider.invoke("planner prompt", role="draft", timeout=9)

    assert result.ok is True
    assert result.text == "real draft after worker ready"
    assert captured["calls"] == 2
    assert captured["sleeps"] == [2.0]


def test_local_ingest_alias_selects_long_context_role() -> None:
    provider = planner_providers.get_planner_provider("local_ingest")

    assert provider.name == "local_ingest"
    assert provider._payload("prompt")["x_orchestrator_role"] == "ingest_long_context"


def test_local_briefed_alias_selects_ingest_then_frontdoor() -> None:
    provider = planner_providers.get_planner_provider("local_ingest_frontdoor")

    assert provider.name == "local_brief_frontdoor"
    assert provider._brief_role == "ingest_long_context"
    assert provider._draft_role == "frontdoor"


def test_local_frontdoor_alias_ignores_ingest_env(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_ROLE", "ingest_long_context")
    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_MODEL", "ingest_long_context")

    provider = planner_providers.get_planner_provider("local_frontdoor")
    payload = provider._payload("prompt", planner_role="critique")

    assert provider.name == "local_frontdoor"
    assert payload["x_orchestrator_role"] == "frontdoor"
    assert payload["model"] == "frontdoor"
    assert "\nprompt\n" in payload["messages"][0]["content"]
    assert "CRITICAL OUTPUT CONTRACT FOR THIS LOCAL AUTOPILOT CRITIQUE" in payload[
        "messages"
    ][0]["content"]


def test_local_chat_alias_posts_draft_chat_payload_with_force_role(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raised"] = True

        def json(self) -> dict[str, Any]:
            return {"answer": "draft from answer"}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    def fake_archive(prompt, payload, result, response_data, *, url):
        captured["archive"] = {
            "prompt": prompt,
            "payload": payload,
            "provider": result.provider,
            "response": response_data,
            "url": url,
        }

    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_chat_call", fake_archive)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.delenv("AUTOPILOT_LOCAL_CHAT_PLANNER_FORCE_ROLE", raising=False)
    monkeypatch.setattr(
        planner_providers.uuid, "uuid4", lambda: type("U", (), {"hex": "0123456789abcdef"})()
    )

    provider = planner_providers.get_planner_provider("local_chat")
    result = provider.invoke("planner prompt", role="draft", timeout=11)

    assert provider.name == "local_chat"
    assert result.ok is True
    assert result.text == "draft from answer"
    assert captured["timeout"] == 11
    assert captured["url"] == "http://127.0.0.1:8000/chat"
    assert captured["payload"] == {
        "prompt": "planner prompt",
        "mock_mode": False,
        "real_mode": True,
        "max_turns": 1,
        "max_tokens": 2048,
        "request_priority": "background",
        "workload_class": "campaign",
        "request_id": "planner-local-chat-01234567",
        "force_role": "ingest_long_context",
    }
    assert captured["archive"]["url"] == "http://127.0.0.1:8000/chat"


def test_local_chat_alias_disabling_force_role_omits_payload_field(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raised"] = True

        def json(self) -> dict[str, Any]:
            return {"answer": "draft from answer"}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_CHAT_PLANNER_FORCE_ROLE", "off")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(
        planner_providers, "_archive_local_chat_call", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.uuid, "uuid4", lambda: type("U", (), {"hex": "0123456789abcdef"})()
    )

    provider = planner_providers.get_planner_provider("local_chat")
    result = provider.invoke("planner prompt", role="draft", timeout=11)

    assert result.ok is True
    assert captured["payload"] == {
        "prompt": "planner prompt",
        "mock_mode": False,
        "real_mode": True,
        "max_turns": 1,
        "max_tokens": 2048,
        "request_priority": "background",
        "workload_class": "campaign",
        "request_id": "planner-local-chat-01234567",
    }
    assert "force_role" not in captured["payload"]


def test_local_chat_alias_posts_critique_payload_without_force_role(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raised"] = True

        def json(self) -> dict[str, Any]:
            return {"answer": "critique from answer"}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_CHAT_PLANNER_FORCE_ROLE", "ingest_long_context")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(
        planner_providers, "_archive_local_chat_call", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.uuid, "uuid4", lambda: type("U", (), {"hex": "0123456789abcdef"})()
    )

    provider = planner_providers.get_planner_provider("local_chat")
    result = provider.invoke("planner prompt", role="critique", timeout=11)

    assert result.ok is True
    assert captured["payload"] == {
        "prompt": "planner prompt",
        "mock_mode": False,
        "real_mode": True,
        "max_turns": 1,
        "max_tokens": 2048,
        "request_priority": "background",
        "workload_class": "campaign",
        "request_id": "planner-local-chat-01234567",
    }
    assert "force_role" not in captured["payload"]


def test_local_chat_retries_server_disconnect(monkeypatch) -> None:
    captured: dict[str, Any] = {"calls": 0, "sleeps": []}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"answer": "chat draft after retry"}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            captured["calls"] += 1
            if captured["calls"] == 1:
                raise planner_providers.httpx.RemoteProtocolError(
                    "server disconnected without response"
                )
            return FakeResponse()

    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_HTTP_ATTEMPTS", "2")
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_local_chat_call", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner_providers.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        planner_providers.time, "sleep", lambda seconds: captured["sleeps"].append(seconds)
    )
    monkeypatch.setattr(
        planner_providers.uuid,
        "uuid4",
        lambda: type("U", (), {"hex": "0123456789abcdef"})(),
    )

    provider = planner_providers.get_planner_provider("local_chat")
    result = provider.invoke("planner prompt", role="draft", timeout=11)

    assert result.ok is True
    assert result.text == "chat draft after retry"
    assert captured["calls"] == 2
    assert captured["sleeps"] == [2.0]


def test_codex_provider_uses_current_read_only_cli(monkeypatch, tmp_path) -> None:
    captured = {}

    class FakeProcess:
        returncode = 0

        def communicate(self, input, timeout):
            captured["input"] = input
            captured["timeout"] = timeout
            return (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "ok"},
                    }
                ),
                "",
            )

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_codex_call", lambda *a, **k: None)
    monkeypatch.setattr(planner_providers.subprocess, "Popen", fake_popen)
    monkeypatch.setenv("AUTOPILOT_CODEX_EFFORT", "high")

    provider = planner_providers.CodexPlannerProvider(
        binary_path="codex",
        model="test-model",
    )
    result = provider.invoke("prompt", role="critique", timeout=7, cwd=tmp_path)

    assert result.ok
    assert captured["cmd"] == [
        "codex",
        "exec",
        "--json",
        "--config",
        'model_reasoning_effort="high"',
        "-m",
        "test-model",
        "-s",
        "read-only",
        "-",
    ]
    assert "--full-auto" not in captured["cmd"]
    assert captured["input"] == "prompt"
    assert captured["timeout"] == 7


def test_active_roster_refuses_claude_before_provider_construction(monkeypatch) -> None:
    from scripts.autopilot import planner_roster

    for key, value in planner_roster.apply_roster({}, planner_roster.DEFAULT_ROSTER).items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match="forbidden by the active sealed roster"):
        planner_providers.get_planner_provider("claude")


def test_active_roster_constructs_distinct_codex_model_cells(monkeypatch) -> None:
    from scripts.autopilot import planner_roster

    for key, value in planner_roster.apply_roster({}, planner_roster.DEFAULT_ROSTER).items():
        monkeypatch.setenv(key, value)
    primary = planner_providers.get_planner_provider("codex")
    critic = planner_providers.get_planner_provider("codex_critic")
    assert primary._model == "gpt-5.6-sol"
    assert critic._model == "gpt-5.6-terra"
    assert primary._effort == critic._effort == "high"


def test_active_roster_refuses_a_third_codex_alias(monkeypatch) -> None:
    from scripts.autopilot import planner_roster

    for key, value in planner_roster.apply_roster(
        {}, planner_roster.DEFAULT_ROSTER
    ).items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match="forbidden by the active sealed roster"):
        planner_providers.get_planner_provider("codex_reviewer")


def test_codex_provider_uses_configured_default_model_when_unspecified(
    monkeypatch, tmp_path
) -> None:
    captured = {}

    class FakeProcess:
        returncode = 0

        def communicate(self, input, timeout):
            captured["input"] = input
            captured["timeout"] = timeout
            return (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "ok"},
                    }
                ),
                "",
            )

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.delenv("AUTOPILOT_CODEX_MODEL", raising=False)
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_codex_call", lambda *a, **k: None)
    monkeypatch.setattr(planner_providers.subprocess, "Popen", fake_popen)

    provider = planner_providers.CodexPlannerProvider(binary_path="codex")
    result = provider.invoke("prompt", role="critique", timeout=7, cwd=tmp_path)

    assert result.ok
    assert captured["cmd"] == [
        "codex",
        "exec",
        "--json",
        "-s",
        "read-only",
        "-",
    ]
    assert captured["input"] == "prompt"
    assert captured["timeout"] == 7


def test_codex_critic_alias_uses_codex_with_distinct_provider_name(monkeypatch, tmp_path) -> None:
    captured = {}

    class FakeProcess:
        returncode = 0

        def communicate(self, input, timeout):
            captured["input"] = input
            captured["timeout"] = timeout
            return (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "ok"},
                    }
                ),
                "",
            )

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.delenv("AUTOPILOT_CODEX_MODEL", raising=False)
    monkeypatch.setattr(planner_providers, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(planner_providers, "_archive_codex_call", lambda *a, **k: None)
    monkeypatch.setattr(planner_providers.subprocess, "Popen", fake_popen)

    provider = planner_providers.get_planner_provider("codex_critic")
    result = provider.invoke("prompt", role="critique", timeout=7, cwd=tmp_path)

    assert provider.name == "codex_critic"
    assert result.provider == "codex_critic"
    assert result.ok
    assert captured["cmd"] == [
        "codex",
        "exec",
        "--json",
        "-s",
        "read-only",
        "-",
    ]
    assert captured["input"] == "prompt"
    assert captured["timeout"] == 7

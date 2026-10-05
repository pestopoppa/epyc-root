from __future__ import annotations

from src.api.routes.chat_routing import detect_tool_requirement


def test_detect_tool_requirement_for_explicit_tool_sentinel_prompt() -> None:
    prompt = (
        "Return executable Python only. No comments, no prose. "
        "Use exactly these two lines:\n"
        'secret = TOOL("get_eval_secret", name="alpha")\n'
        "FINAL(secret)"
    )

    assert detect_tool_requirement(prompt) == (True, "get_eval_secret")


def test_detect_tool_requirement_does_not_force_descriptive_call_mentions() -> None:
    prompt = 'Explain what CALL("web_search", query="x") would do in this codebase.'

    assert detect_tool_requirement(prompt) == (False, None)


def test_detect_tool_requirement_preserves_keyword_hints() -> None:
    assert detect_tool_requirement("Please grep for the handler") == (True, "grep")

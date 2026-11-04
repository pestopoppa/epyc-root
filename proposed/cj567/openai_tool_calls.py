"""Adapter from OpenAI-compatible chat response JSON to BFCL call data.

This module only validates/extracts structured tool calls. It does not score.
"""

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterResult:
    """A parse result, separate from any downstream official checker result."""

    ok: bool
    calls: list[dict[str, dict[str, Any]]] | None = None
    error: str | None = None


def _error(message: str) -> AdapterResult:
    return AdapterResult(ok=False, error=message)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Decode one JSON object while rejecting duplicate member names."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_non_json_constant(value: str) -> None:
    # Python's json module otherwise accepts NaN and Infinity extensions.
    raise ValueError(f"non-standard JSON constant {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("JSON number is outside the supported finite range")
    return parsed


def adapt_openai_tool_calls(response: Mapping[str, Any]) -> AdapterResult:
    """Return ordered ``[{name: kwargs}, ...]`` or a tagged adapter error.

    ``response`` is the OpenAI-compatible chat completion choice object, with
    ``finish_reason`` and ``message.tool_calls`` fields.
    """
    if not isinstance(response, Mapping):
        return _error("response must be an object")
    if response.get("finish_reason") != "tool_calls":
        return _error("finish_reason is not tool_calls")

    message = response.get("message")
    if not isinstance(message, Mapping):
        return _error("message is missing or is not an object")
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        return _error("tool_calls is missing, not an array, or empty")

    calls: list[dict[str, dict[str, Any]]] = []
    for index, tool_call in enumerate(tool_calls):
        if not isinstance(tool_call, Mapping):
            return _error(f"tool_calls[{index}] is not an object")
        if tool_call.get("type") != "function":
            return _error(f"tool_calls[{index}].type is not 'function'")
        function = tool_call.get("function")
        if not isinstance(function, Mapping):
            return _error(f"tool_calls[{index}].function is missing or not an object")
        name = function.get("name")
        if not isinstance(name, str) or not name.strip():
            return _error(f"tool_calls[{index}].function.name is not a nonempty string")
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            return _error(f"tool_calls[{index}].function.arguments is not a JSON string")
        try:
            kwargs = json.loads(
                arguments,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_non_json_constant,
                parse_float=_finite_float,
            )
        except (json.JSONDecodeError, TypeError, ValueError, RecursionError) as exc:
            return _error(f"tool_calls[{index}].function.arguments is invalid JSON: {exc}")
        if not isinstance(kwargs, dict):
            return _error(f"tool_calls[{index}].function.arguments JSON is not an object")
        calls.append({name: kwargs})

    return AdapterResult(ok=True, calls=calls)

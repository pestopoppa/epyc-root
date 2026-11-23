"""Improver-conformance replay (LH4c): send ONE proposer-shaped request through the improver proxy
and require what upstream requires of the response: an assistant choice carrying ``tool_calls``
(the request carries ``tools``) and non-negative INTEGER ``prompt_tokens`` / ``completion_tokens``
(``life_evolve/context.py::verify_usage``). Replayable offline: point it at any HTTP server that
returns a recorded response (the unit tests do), or at the live proxy after reboot.

The result names the unmet rule instead of raising, so a failure is a recordable verdict.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

from .proxy import IMPROVER_PREFIX, check_response

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
FLASH_NAME = "deepseek-v4-flash"  # the name the shipped proposer sends


def synthetic_request(tools: Sequence[dict[str, Any]], max_tokens: int = 2048) -> dict[str, Any]:
    """A proposer-shaped request built from the upstream tool list (``profile.TOOLS``): not a
    recorded session, but identical in request shape (model, messages, tools, tool_choice)."""
    name = tools[0]["function"]["name"]
    return {"model": FLASH_NAME, "tools": list(tools), "tool_choice": "auto", "max_tokens": max_tokens,
            "stream": False,
            "messages": [{"role": "system", "content": "You are the harness improver. Respond only by calling a tool."},
                         {"role": "user", "content": f"Conformance probe: call the tool `{name}` once with plausible arguments."}]}


def replay(request: dict[str, Any], base_url: str, *, path: str = IMPROVER_PREFIX + "/chat/completions",
           timeout: float = 600.0) -> dict[str, Any]:
    """POST ``request`` to ``base_url + path``; return a verdict dict with ``unmet`` rule names."""
    started = time.time()
    verdict: dict[str, Any] = {"url": base_url + path, "request_model": request.get("model"),
                               "tools_in_request": len(request.get("tools") or []), "unmet": []}
    body = json.dumps(request).encode()
    req = urllib.request.Request(base_url + path, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            payload = json.load(resp)
            verdict["http_status"] = resp.status
    except urllib.error.HTTPError as exc:
        verdict.update(http_status=exc.code, error=exc.read().decode(errors="replace")[:500])
        verdict["unmet"].append("http_ok")
    except Exception as exc:
        verdict.update(http_status=None, error=type(exc).__name__ + ": " + str(exc)[:300])
        verdict["unmet"].append("reachable")
    else:
        facts = check_response(payload, tools_requested=bool(request.get("tools")))
        verdict["facts"] = facts
        if not facts["has_choice"]:
            verdict["unmet"].append("assistant_choice")
        if not facts["usage_integer"]:
            verdict["unmet"].append("integer_usage")
        if not facts["tool_calls_ok"]:
            verdict["unmet"].append("tool_calls")
        usage = payload.get("usage") or {}
        verdict["usage"] = {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    verdict["ok"] = not verdict["unmet"]
    verdict["seconds"] = round(time.time() - started, 3)
    return verdict


def write_verdict(verdict: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")

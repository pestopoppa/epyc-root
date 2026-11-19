"""Bounded stateful planning episodes; endpoint custody belongs to the row.

The caller supplies complete(request, timeout_s), an isolated environment with
tools/execute/score, and a synchronous durable capture callback. This module
does not contact or start servers. Native transport/format/cap failures remain
UNKNOWN; a stopped textual answer is graded against the environment's state.
"""
from copy import deepcopy
import json
import math
import time


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate argument")
        result[key] = value
    return result


def run_episode(complete, environment, messages, capture, *, model, seed,
                max_turns=6, max_tokens=256, timeout_s=120, clock=time.monotonic):
    """Run one fresh environment, capturing requests and replies before execution.

    Supported tools deliberately use the existing order-service contract: exact
    required string arguments, no extra keys. Unsupported schemas fail offline.
    Capture failure propagates: no tool runs without its durable native receipt.
    """
    for value in (max_turns, max_tokens):
        if type(value) is not int or value <= 0:
            raise ValueError("positive integer bounds required")
    if (isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s) or timeout_s <= 0):
        raise ValueError("finite positive timeout required")
    schemas = {}
    for tool in environment.tools:
        function = tool["function"]
        schema = function["parameters"]
        keys = set(schema["properties"])
        if (tool["type"] != "function" or function["name"] in schemas
                or schema["type"] != "object" or schema.get("additionalProperties") is not False
                or set(schema["required"]) != keys
                or any(p.get("type") != "string" for p in schema["properties"].values())):
            raise ValueError("unsupported tool schema")
        schemas[function["name"]] = keys
    history = deepcopy(messages)
    started = clock()
    deadline = started + timeout_s
    seen_ids = set()
    turns = []
    totals = {"prompt_tokens": 0, "completion_tokens": 0}
    usage_complete = True
    rejections = repairs = 0
    pending_repair = False

    def finish(reason, score=None):
        return {
            "schema": "epyc.planning_depth.episode.v1", "model": model, "seed": seed,
            "status": "GRADED" if score is not None else "UNKNOWN",
            "reason": reason, "score": score, "turns": turns,
            "schema_rejections": rejections, "repairs": repairs,
            "usage_complete": usage_complete,
            "observed_usage": totals.copy(),
            "total_completion_tokens": totals["completion_tokens"] if usage_complete else None,
            "elapsed_s": max(0, clock() - started),
            "scope": "synthetic stateful planning diagnostic; no role or adoption verdict",
        }

    for index in range(max_turns):
        remaining = deadline - clock()
        if remaining <= 0:
            return finish("deadline")
        request = {"model": model, "messages": deepcopy(history),
                   "tools": deepcopy(environment.tools), "seed": seed,
                   "temperature": 0, "max_tokens": max_tokens,
                   "chat_template_kwargs": {"enable_thinking": False}}
        turn = {"index": index, "request": request}
        turns.append(turn)
        capture(deepcopy({"event": "request", **turn}))
        # Durable capture can consume time; never hand the transport the stale
        # budget calculated before its fsync.
        remaining = deadline - clock()
        if remaining <= 0:
            return finish("deadline")
        try:
            reply = complete(deepcopy(request), remaining)
        except (OSError, TimeoutError) as error:
            usage_complete = False
            turn["error"] = {"type": type(error).__name__, "message": str(error)}
            capture(deepcopy({"event": "transport_error", **turn}))
            return finish("transport_error")
        turn["response"] = deepcopy(reply)
        capture(deepcopy({"event": "response", **turn}))
        usage = reply.get("usage") if isinstance(reply, dict) else None
        valid_usage = (isinstance(usage, dict)
                       and all(type(usage.get(k)) is int and usage[k] >= 0 for k in totals)
                       and type(usage.get("total_tokens")) is int
                       and usage["total_tokens"] == sum(usage[k] for k in totals)
                       and usage["completion_tokens"] <= max_tokens)
        if valid_usage:
            for key in totals:
                totals[key] += usage[key]
        else:
            usage_complete = False
        if clock() >= deadline:
            return finish("deadline")
        try:
            choices = reply["choices"]
            if (not isinstance(choices, list) or len(choices) != 1
                    or type(choices[0]["index"]) is not int or choices[0]["index"] != 0):
                raise ValueError("single choice required")
            choice = choices[0]
            message, reason = choice["message"], choice["finish_reason"]
            if message["role"] != "assistant":
                raise ValueError("assistant required")
            calls = message.get("tool_calls") or []
            if not isinstance(calls, list):
                raise ValueError("tool call list required")
            if reason == "length":
                return finish("token_cap")
            if reason == "stop" and not calls and isinstance(message.get("content"), str):
                if not message["content"].strip():
                    return finish("empty_answer")
                return finish("stopped", environment.score(message["content"]))
            if reason != "tool_calls" or not calls:
                raise ValueError("finish reason disagrees with message")
            for call in calls:
                call_id = call["id"]
                if (not isinstance(call_id, str) or not call_id or call_id in seen_ids
                        or call["type"] != "function"
                        or not isinstance(call["function"]["name"], str)
                        or not isinstance(call["function"]["arguments"], str)):
                    raise ValueError("malformed or reused tool call")
                seen_ids.add(call_id)
        except (KeyError, TypeError, ValueError, IndexError):
            return finish("invalid_native_response")

        # Reject malformed arguments before exposing them to the state machine.
        # Multiple calls are rejected as a batch: order must be established by
        # tool observations, never by speculative parallel calls.
        valid = len(calls) == 1
        for call in calls:
            try:
                arguments = json.loads(call["function"]["arguments"], object_pairs_hook=unique_object)
                keys = schemas.get(call["function"]["name"])
                valid &= (keys is not None and isinstance(arguments, dict)
                          and set(arguments) == keys
                          and all(isinstance(v, str) for v in arguments.values()))
            except ValueError:
                valid = False
        history.append(deepcopy(message))
        if valid:
            observations, events = environment.execute(deepcopy(calls))
            if pending_repair and any(e["outcome"] != "rejected" for e in events):
                repairs += 1
                pending_repair = False
        else:
            rejections += 1
            pending_repair = True
            observations = [{"role": "tool", "tool_call_id": c["id"],
                             "content": '{"error":"Use one documented tool with exact string arguments."}'}
                            for c in calls]
            events = [{"tool": c["function"]["name"], "call_id": c["id"],
                       "outcome": "rejected"} for c in calls]
        turn["tool_events"] = deepcopy(events)
        turn["observations"] = deepcopy(observations)
        capture(deepcopy({"event": "tool_result", **turn}))
        history.extend(deepcopy(observations))
    return finish("turn_cap")

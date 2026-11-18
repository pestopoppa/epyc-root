"""Wire request and response contract shared by producer and diagnostic reader."""

import json

BUDGET = 8
PROMPT = (
    "A bus has 42 passengers. At the first stop one third leave and 9 board. "
    "At the next stop 5 leave and twice that many board. How many passengers "
    "are on the bus now? Give the final number."
)
ARMS = ("budget-omitted", "budget-8", "thinking-disabled")


def request_cells(model, max_tokens):
    registered = []
    for arm in ARMS:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT}],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "top_k": 1,
            "seed": 20261118,
            "cache_prompt": False,
            "verbose": True,
            "return_tokens": True,
            "reasoning_format": "deepseek",
            "chat_template_kwargs": {"enable_thinking": arm != "thinking-disabled"},
        }
        if arm == "budget-8":
            body["thinking_budget_tokens"] = BUDGET
        registered.append({"unit": arm, "body": body})
    return registered


def read_terminal(payload, request):
    body = json.loads(payload)
    if body["object"] != "chat.completion" or body["model"] != request["model"]:
        raise ValueError("native response object or served model differs")
    choice, = body["choices"]
    reason = choice["finish_reason"]
    message = choice["message"]
    if reason not in {"stop", "length"} or message["role"] != "assistant":
        raise ValueError("native response lacks an ordinary final chat choice")
    reasoning, content = message.get("reasoning_content"), message.get("content")
    if any(value is not None and not isinstance(value, str) for value in (reasoning, content)):
        raise ValueError("native response chat text has an invalid type")
    usage = body["usage"]
    prompt, completion, total = (usage[name] for name in (
        "prompt_tokens", "completion_tokens", "total_tokens",
    ))
    if (any(type(count) is not int for count in (prompt, completion, total))
            or prompt <= 0 or not 0 < completion <= request["max_tokens"]
            or total != prompt + completion):
        raise ValueError("native usage is missing, inconsistent or outside the token cap")
    verbose = body["__verbose"]
    tokens = verbose["tokens"]
    if not isinstance(tokens, list) or not tokens or any(type(token) is not int for token in tokens):
        raise ValueError("native response lacks decoded token IDs")
    return {
        "finish_reason": reason,
        "usage": usage,
        "reasoning_field_present": "reasoning_content" in message,
        "reasoning_content": reasoning,
        "content": content,
        "reasoning_nonempty": bool(reasoning and reasoning.strip()),
        "token_ids": tokens,
        "n_token_ids": len(tokens),
        "raw_content": verbose.get("content"),
        "rendered_prompt": verbose.get("prompt"),
        "generation_settings": verbose.get("generation_settings"),
        "system_fingerprint": body.get("system_fingerprint"),
    }

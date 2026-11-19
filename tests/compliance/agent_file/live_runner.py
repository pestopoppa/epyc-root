"""Live-LLM adapter for the compliance suite.

Wraps `runner.run_compliance_suite()` with an httpx-backed `llm_call`
that posts to a standard llama-server `/v1/chat/completions` endpoint.

Phase 3 (per handoffs/active/agent-file-prose-compression.md): replace
the deterministic fake LLM in runner.py with this live adapter to measure
real per-model compression-tolerance.

Usage:
    # Smoke against one model at one level:
    python3 tests/compliance/agent_file/live_runner.py \\
        --base-url http://localhost:8080 \\
        --model-id qwen3-coder-30b-a3b-q4 \\
        --agent-file agents/shared/ENGINEERING_STANDARDS.md \\
        --level mild \\
        --output data/compliance/2026-05-06-smoke.json

The runner loads the agent file, sends agent-file + each task prompt to
the model, and scores the response per the existing forbidden_actions /
procedure / instruction_recall task pools.
"""

from __future__ import annotations

import argparse

# AFC-P5.E3 r6 suite change (operator 2026-11-09): r5's NO_TOOLS_SUFFIX is REMOVED; the architect_general tool schema is
# offered instead (tools_architect_general.json, see gen_architect_tools.py) and tool-call replies are scored by
# classify_tool_calls() + runner.mk().
import json
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path

import urllib.request
import urllib.error

# Make repo root importable.
_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.compliance.agent_file.runner import run_compliance_suite  # noqa: E402

logger = logging.getLogger(__name__)

TOOLS_FILE = Path(__file__).with_name("tools_architect_general.json")
RAW_TOOL_MARKERS = ("<tool_call>", "<function=", "[TOOL_CALLS]")  # tool-call text the server failed to parse into tool_calls


def load_tools(path: Path | str | None = None) -> list[dict]:
    return json.loads(Path(path or TOOLS_FILE).read_text())


def classify_tool_calls(message: dict, content: str, tools: list[dict]) -> tuple[list[dict], str]:
    """Return (calls, verdict). verdict: "" | "ok_with_answer" | "tool_only" | "invalid_tool_call".

    A call is valid iff its name is in `tools`, its arguments parse as a JSON object, every required parameter is
    present and no undeclared parameter appears. Unparsed tool-call markup left in `content` counts as invalid.
    """
    specs = {t["function"]["name"]: t["function"]["parameters"] for t in tools}
    calls, invalid = [], False
    for tc in message.get("tool_calls") or []:
        fn = (tc or {}).get("function") or {}
        name, raw = fn.get("name", ""), fn.get("arguments", "")
        calls.append({"name": name, "arguments": raw if isinstance(raw, str) else json.dumps(raw)})
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            invalid = True
            continue
        spec = specs.get(name)
        if spec is None or not isinstance(args, dict):
            invalid = True
            continue
        props, req = spec.get("properties", {}), spec.get("required", [])
        if any(r not in args for r in req) or any(k not in props for k in args):
            invalid = True
    if any(m in content for m in RAW_TOOL_MARKERS):
        invalid = True
        calls = calls or [{"name": "", "arguments": "<unparsed tool-call text in content>"}]
    if not calls:
        return [], ""
    if invalid:
        return calls, "invalid_tool_call"
    return calls, "ok_with_answer" if content.strip() else "tool_only"


STUB_TOOL_RESULT = ("Tool result unavailable in this evaluation environment. "
                    "Answer from your own knowledge and the instructions you were given.")
MAX_TOOL_ROUNDS = 3  # r8: after this many tool rounds the next request is the FORCED final request
# v3b: the forced final request OMITS the `tools` and `tool_choice` keys entirely (tool_choice "none" with `tools` present was
# ignored by Qwen3.6-35B / Flash, which emitted <tool_call> markup) and appends this user nudge.
FORCED_NUDGE = "Tools are no longer available. Give your final answer in plain text now."
FORCED_RETRY_NUDGE = FORCED_NUDGE + " Do not write any tool call or tool-call markup."
FORCED_MARKUP = "forced_markup"  # tool_verdict of a task whose forced final reply still carried tool-call markup after the retry

RETRIES = 1  # r2: one retry per task before a reply is declared blank


def make_live_llm_call(
    base_url: str,
    model: str = "default",
    max_tokens: int = 512,
    temperature: float = 0.0,
    timeout_s: float = 90.0,
    enable_thinking: bool = False,
    tools: list[dict] | None = None,
):
    """Build an LLMCall closure that posts to /v1/chat/completions.

    The agent file is sent as a system message; the task prompt is the
    user message. Temperature 0 for reproducibility on smoke runs.

    `enable_thinking` defaults to False per `feedback_think_mode_benchmarks`:
    Qwen3.5+ / Qwen3.6 / Qwen3-Next reasoning models otherwise spend the
    entire max_tokens budget on a `<think>` block, producing 0 visible
    chars to the chat-completion API. Pass via `chat_template_kwargs`
    which llama-server forwards to the chat template.
    """

    def once(messages: list, force_plain: bool = False) -> tuple[str, str, list, str, dict]:
        """One POST. Returns (text, error, tool_calls, tool_verdict, message); error != "" means no usable reply (distinct from a wrong answer)."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
        }
        if tools and not force_plain:  # v3b: a forced request carries neither `tools` nor `tool_choice`
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        req = urllib.request.Request(
            url=f"{base_url.rstrip('/')}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:  # noqa: BLE001
                detail = ""
            return "", f"http_{e.code}: {detail}", [], "", {}
        except TimeoutError as e:
            return "", f"timeout: {e}", [], "", {}
        except urllib.error.URLError as e:
            return "", f"urlerror: {e}", [], "", {}
        except Exception as e:  # noqa: BLE001
            return "", f"exception: {type(e).__name__}: {e}", [], "", {}
        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            return body[:2000], "non_json_response", [], "", {}
        try:
            message = d["choices"][0]["message"]
            text = message.get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return "", "bad_response_shape: " + json.dumps(d)[:200], [], "", {}
        calls, verdict = classify_tool_calls(message, text, tools) if tools else ([], "")
        if (not text or not text.strip()) and not calls:
            return "", "empty_content finish_reason=%s" % (d.get("choices", [{}])[0].get("finish_reason"),), [], "", {}
        return text, "", calls, verdict, message

    def request(messages: list, force_plain: bool = False) -> tuple[str, str, list, str, dict, int]:
        """1 + RETRIES attempts of one request (timeout applies per request); the LAST attempt stands."""
        text, err, calls, verdict, msg, n = "", "", [], "", {}, 0
        for n in range(1, RETRIES + 2):
            text, err, calls, verdict, msg = once(messages, force_plain)
            if not err:
                break
            logger.warning("attempt %d failed: %s", n, err[:200])
        return text, err, calls, verdict, msg, n

    def detailed(agent_file_text: str, prompt: str) -> dict:
        """r8 multi-turn loop: valid tool calls get stub results and a re-request, up to MAX_TOOL_ROUNDS rounds; the
        next request is then forced plain (v3b: no tools/tool_choice keys + nudge; one retry; persistent markup => verdict forced_markup). Only the FINAL reply's text is scored. An invalid tool call
        in any round ends the loop as a failure; an empty final reply is blank."""
        messages = [{"role": "system", "content": agent_file_text}, {"role": "user", "content": prompt}]
        all_calls: list = []
        rounds, attempts, cap_hit = 0, 0, False
        while True:
            force = bool(tools) and rounds >= MAX_TOOL_ROUNDS
            if force:
                cap_hit = True
                text, err, calls, verdict, msg, n = request(messages + [{"role": "user", "content": FORCED_NUDGE}], True)
                attempts += n
                all_calls.extend(calls)
                if not err and verdict:  # markup / tool_calls despite no tools offered: retry the forced request once
                    text, err, calls, verdict, msg, n = request(messages + [{"role": "user", "content": FORCED_RETRY_NUDGE}], True)
                    attempts += n
                    all_calls.extend(calls)
                    if not err and verdict:
                        verdict = FORCED_MARKUP
                break
            text, err, calls, verdict, msg, n = request(messages, False)
            attempts += n
            all_calls.extend(calls)
            if err or verdict == "invalid_tool_call" or not calls:
                break
            rounds += 1
            wire = []
            for i, tc in enumerate(msg.get("tool_calls") or []):
                tc = dict(tc)
                tc["id"] = tc.get("id") or f"call_r{rounds}_{i}"
                tc.setdefault("type", "function")
                wire.append(tc)
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": wire})
            for tc in wire:
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": STUB_TOOL_RESULT})
        return {"text": text, "error": err, "attempts": attempts, "tool_calls": all_calls, "tool_verdict": verdict,
                "tool_rounds": rounds, "cap_hit": cap_hit}

    def call(agent_file_text: str, prompt: str) -> str:
        return detailed(agent_file_text, prompt)["text"]

    call.detailed = detailed  # type: ignore[attr-defined]
    return call


def health_check(base_url: str, timeout_s: float = 5.0) -> bool:
    """Probe /health (or /) for readiness."""
    for path in ("/health", "/v1/models", "/"):
        try:
            req = urllib.request.Request(url=f"{base_url.rstrip('/')}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="live_compliance", description=__doc__)
    p.add_argument("--base-url", default="http://localhost:8080")
    p.add_argument("--model-id", default="live-model", help="Identifier recorded in the result")
    p.add_argument("--agent-file", required=True, help="Path to the agent file under test")
    p.add_argument("--level", default="none", choices=["none", "mild", "medium", "aggressive"])
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=90.0)
    p.add_argument("--enable-thinking", action="store_true",
                   help="Enable Qwen3.5+/Qwen3.6/Qwen3-Next thinking mode (default: disabled per "
                        "feedback_think_mode_benchmarks; models otherwise spend max_tokens on "
                        "a <think> block and return 0 visible chars).")
    p.add_argument("--tools-file", default=str(TOOLS_FILE),
                   help="OpenAI-style tools array offered on every request (r6: architect_general schema). 'none' offers no tools.")
    p.add_argument("--output", help="Optional JSON output path")
    p.add_argument("--max-tasks", type=int, default=0,
                   help="Limit to N tasks per pool (0 = all). Useful for quick smokes.")
    p.add_argument("--concurrency", type=int, default=1,
                   help="Concurrent in-flight requests (pair with a server started with -np >= this).")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not health_check(args.base_url):
        print(f"ERROR: server at {args.base_url} not reachable", file=sys.stderr)
        return 2

    print(f"=== live compliance smoke ===")
    print(f"  base_url     : {args.base_url}")
    print(f"  model_id     : {args.model_id}")
    print(f"  agent_file   : {args.agent_file}")
    print(f"  level        : {args.level}")
    print(f"  max_tokens   : {args.max_tokens}")
    print(f"  temperature  : {args.temperature}")
    if args.max_tasks:
        print(f"  max_tasks    : {args.max_tasks} per pool")
    print()

    llm_call = make_live_llm_call(
        base_url=args.base_url,
        model=args.model_id,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout_s=args.timeout,
        enable_thinking=args.enable_thinking,
        tools=None if args.tools_file == "none" else load_tools(args.tools_file),
    )

    # Optionally truncate task pools for fast smoke. Patch in-place via runner.
    if args.max_tasks > 0:
        from tests.compliance.agent_file import (
            forbidden_actions, procedure_correctness, instruction_recall,
        )
        forbidden_actions.TASKS = forbidden_actions.TASKS[:args.max_tasks]
        procedure_correctness.TASKS = procedure_correctness.TASKS[:args.max_tasks]
        instruction_recall.TASKS = instruction_recall.TASKS[:args.max_tasks]
        print(f"  task pools truncated to {args.max_tasks} each")
        print()

    started = time.perf_counter()
    suite = run_compliance_suite(
        model_id=args.model_id,
        agent_file_path=args.agent_file,
        level=args.level,
        llm_call=llm_call,
        concurrency=max(1, args.concurrency),
        partial_path=(args.output + ".partial.jsonl") if args.output else None,
    )
    elapsed = time.perf_counter() - started

    d = suite.to_dict()
    d["elapsed_sec"] = round(elapsed, 1)
    d["base_url"] = args.base_url

    print(f"\n=== results ({elapsed:.1f}s) ===")
    print(f"  token_count          : {d['token_count']}")
    print(f"  status               : {d['status']} (blank replies after retry: {d['blank_count']})")
    print(f"  compliance_pass_rate : {d['compliance_pass_rate']}")
    print(f"  procedure_pass_rate  : {d['procedure_pass_rate']}")
    print(f"  recall_pass_rate     : {d['recall_pass_rate']}")
    print(f"  tool_call_counts     : {json.dumps(d['tool_call_counts'])}")
    print()

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_name(out_path.name + ".tmp")  # atomic: launch.sh skips on a non-empty FINAL file
        with tmp.open("w") as f:
            json.dump(d, f, indent=2, default=str)
        tmp.replace(out_path)
        print(f"  written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

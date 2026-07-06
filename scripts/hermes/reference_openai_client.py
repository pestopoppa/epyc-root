#!/usr/bin/env python3
"""Reference client for calling the orchestrator OpenAI-compatible endpoint.

This is a non-invasive helper: it prints a copy-pastable cURL and Python
OpenAI SDK recipe by default and only sends a request when ``--send`` is
explicitly passed.
"""

from __future__ import annotations

import argparse
import json
import pprint
import shutil
import subprocess
import sys


VALID_ESCALATION = {"A", "B1", "B2", "C", ""}


DEMO_NATIVE_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_orchestrator_status",
        "description": "Look up one high-level orchestrator status category.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["routing", "locks", "models"],
                    "description": "Status area to inspect.",
                }
            },
            "required": ["scope"],
            "additionalProperties": False,
        },
    },
}


def _json_arg(value: str, flag: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{flag} must be valid JSON: {exc}") from exc


def _tool_choice(args: argparse.Namespace) -> str | dict | None:
    if args.tool_choice_json:
        parsed = _json_arg(args.tool_choice_json, "--tool-choice-json")
        if not isinstance(parsed, dict):
            raise ValueError("--tool-choice-json must decode to an object")
        return parsed
    if args.tool_choice:
        return args.tool_choice
    if args.demo_tool or args.tools_json:
        return "auto"
    return None


def _build_payload(args: argparse.Namespace) -> dict:
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": args.stream,
        "x_max_escalation": args.x_max_escalation,
        "x_disable_repl": args.x_disable_repl,
        "x_show_routing": args.x_show_routing,
    }

    if args.x_orchestrator_role:
        payload["x_orchestrator_role"] = args.x_orchestrator_role
    if args.x_force_model:
        payload["x_force_model"] = args.x_force_model

    tools = []
    if args.demo_tool:
        tools.append(DEMO_NATIVE_TOOL)
    for tool_json in args.tools_json:
        parsed = _json_arg(tool_json, "--tools-json")
        if not isinstance(parsed, dict):
            raise ValueError("--tools-json must decode to an object")
        tools.append(parsed)
    if tools:
        payload["tools"] = tools

    tool_choice = _tool_choice(args)
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    return payload


def _print_reference(payload: dict, endpoint: str, api_key: str) -> None:
    standard_fields = {"model", "messages", "stream", "tools", "tool_choice"}
    extra_body = {k: v for k, v in payload.items() if k not in standard_fields}
    extra_body_py = pprint.pformat(extra_body, indent=4, width=100)
    messages_py = pprint.pformat(payload["messages"], indent=4, width=100)

    print("## Dry-run recipe\n")
    print("cURL:")
    print("cat <<'JSON' >/tmp/hermes_chat_request.json")
    print(json.dumps(payload, indent=2))
    print("JSON")
    print()
    print("curl -sS \\")
    print(f'  "{endpoint}" \\')
    print('  -H "Content-Type: application/json" \\')
    if api_key:
        print(f'  -H "Authorization: Bearer {api_key}" \\')
    print("  --data-binary @/tmp/hermes_chat_request.json")
    print()
    print("Python (OpenAI-compatible SDK):")
    print("from openai import OpenAI")
    print("")
    print(f'client = OpenAI(base_url="{endpoint.rsplit("/v1", 1)[0]}/v1", api_key="{api_key or "local"}")')
    print("")
    print("response = client.chat.completions.create(")
    print(f'    model="{payload["model"]}",')
    print(f"    messages={messages_py},")
    if payload.get("stream"):
        print("    stream=True,")
    if payload.get("tools"):
        tools_py = pprint.pformat(payload["tools"], indent=4, width=100)
        print(f"    tools={tools_py},")
    if "tool_choice" in payload:
        tool_choice_py = pprint.pformat(payload["tool_choice"], indent=4, width=100)
        print(f"    tool_choice={tool_choice_py},")
    print(f"    extra_body={extra_body_py},")
    print(")")
    if payload.get("stream"):
        print("for chunk in response:")
        print("    delta = chunk.choices[0].delta.content if chunk.choices else None")
        print("    if delta:")
        print("        print(delta, end='', flush=True)")
        print("print()")
    else:
        print("print(response.choices[0].message.content)")


def _run_send(endpoint: str, api_key: str, payload: dict, timeout: int) -> None:
    if shutil.which("curl") is None:
        raise RuntimeError("curl not found in PATH; install curl or run without --send")

    request_json = json.dumps(payload).encode("utf-8")
    command = [
        "curl",
        "-sS",
        "--fail-with-body",
        "--max-time",
        str(timeout),
        endpoint,
        "-H",
        "Content-Type: application/json",
        "-X",
        "POST",
    ]
    if api_key:
        command.extend(["-H", f"Authorization: Bearer {api_key}"])
    command.extend(["--data-binary", "@-"])

    print("Running:")
    print("  " + " ".join(f'"{piece}"' if " " in piece else piece for piece in command))
    print()
    if payload.get("stream"):
        completed = subprocess.run(
            command,
            input=request_json,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
        return

    completed = subprocess.run(
        command,
        input=request_json,
        capture_output=True,
        check=False,
    )
    print(completed.stdout.decode("utf-8", "replace") if isinstance(completed.stdout, (bytes, bytearray)) else completed.stdout)
    if completed.stderr:
        print(
            completed.stderr.decode("utf-8", "replace")
            if isinstance(completed.stderr, (bytes, bytearray))
            else completed.stderr,
            file=sys.stderr,
        )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a safe reference request for orchestrator /v1/chat/completions "
            "with Hermes x_* overrides."
        )
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base orchestrator URL.")
    parser.add_argument("--model", default="orchestrator", help="Orchestrator model alias (default: orchestrator).")
    parser.add_argument("--api-key", default="local", help="Authorization token sent as Bearer token.")
    parser.add_argument("--prompt", default="Summarize the active role and escalation context.", help="User message.")
    parser.add_argument(
        "--x-orchestrator-role",
        default="frontdoor",
        help="Set x_orchestrator_role (empty string to omit).",
    )
    parser.add_argument("--x-force-model", default="", help="Set x_force_model (optional).")
    parser.add_argument(
        "--x-max-escalation",
        default="B2",
        choices=sorted({v for v in VALID_ESCALATION if v}),
        help="Set x_max_escalation cap (A/B1/B2/C).",
    )
    parser.add_argument("--x-disable-repl", dest="x_disable_repl", action="store_true", help="Set x_disable_repl=true.")
    parser.add_argument(
        "--x-allow-repl",
        dest="x_disable_repl",
        action="store_false",
        help="Set x_disable_repl=false.",
    )
    parser.set_defaults(x_disable_repl=True)
    parser.add_argument(
        "--x-show-routing",
        action="store_true",
        help="Request x_orchestrator_metadata routing details.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Set stream=true so the request exercises SSE-compatible response handling.",
    )
    parser.add_argument(
        "--demo-tool",
        action="store_true",
        help="Add a small native OpenAI function-tool schema to the request.",
    )
    parser.add_argument(
        "--tools-json",
        action="append",
        default=[],
        metavar="JSON",
        help="Append a raw OpenAI tool object. May be passed multiple times.",
    )
    parser.add_argument(
        "--tool-choice",
        choices=["auto", "none", "required"],
        default="",
        help="Set standard tool_choice. Defaults to auto when tools are present.",
    )
    parser.add_argument(
        "--tool-choice-json",
        default="",
        metavar="JSON",
        help="Set raw object tool_choice, for example a forced function selection.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout seconds for --send (default: 10).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send the HTTP request (off by default).",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Keep dry-run behavior and only print recipes (default).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.print_only and args.send:
        print("error: cannot combine --send and --print-only.", file=sys.stderr)
        return 1

    if args.x_max_escalation not in VALID_ESCALATION:
        print(
            f"error: unsupported --x-max-escalation {args.x_max_escalation}",
            file=sys.stderr,
        )
        return 1

    endpoint = f"{args.base_url.rstrip('/')}/v1/chat/completions"
    try:
        payload = _build_payload(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_reference(payload, endpoint, args.api_key)

    if not args.send:
        print("\nDRY-RUN: no request sent. Add --send to call the endpoint.")
        return 0

    _run_send(endpoint, args.api_key, payload, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

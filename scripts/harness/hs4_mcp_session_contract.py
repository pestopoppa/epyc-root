#!/usr/bin/env python3
"""Check HS-4 session stamping on an MCP server without running inference.

Run with the server's pinned Python environment and PYTHONPATH. Select a safe,
read-only probe tool and valid arguments: the probe is called with session_id,
then with an undeclared argument. This also supports a separate memory server
via --module and --prefix memory_; an empty selection fails rather than passing.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json


async def check_server(server, *, probe_tool: str, probe_args: dict, prefix: str = "") -> dict:
    from fastmcp import Client

    probe_key = "hs4_undeclared_probe"
    if {"session_id", probe_key} & probe_args.keys():
        raise ValueError("probe arguments must not override contract keys")
    async with Client(server) as client:
        tools = {tool.name: tool.inputSchema for tool in await client.list_tools()
                 if tool.name.startswith(prefix)}
        if not tools or probe_tool not in tools:
            raise ValueError("no selected tools or probe tool outside selection")
        defects = []
        for name, schema in sorted(tools.items()):
            session = schema.get("properties", {}).get("session_id", {})
            if session.get("type") != "string" or "session_id" in schema.get("required", []):
                defects.append(f"{name}: session_id must be an optional string")
            if schema.get("additionalProperties") is not False:
                defects.append(f"{name}: undeclared arguments must be forbidden")
        if defects:
            raise ValueError("; ".join(defects))
        stamped = dict(probe_args, session_id="ses_hs4_contract")
        accepted = await client.call_tool(probe_tool, stamped, raise_on_error=False)
        if accepted.is_error:
            raise ValueError("stamped read-only probe failed")
        refused = await client.call_tool(
            probe_tool, dict(stamped, **{probe_key: "must refuse"}), raise_on_error=False
        )
        if not refused.is_error or not any(
            probe_key in getattr(content, "text", "") for content in refused.content
        ):
            raise ValueError("undeclared argument was not explicitly refused")
    return {"verdict": "pass", "tools": sorted(tools), "probe_tool": probe_tool,
            "stamped_call_accepted": True, "undeclared_argument_refused": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, help="module exposing the FastMCP server")
    parser.add_argument("--object", default="mcp")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--probe-tool", required=True, help="safe read-only tool")
    parser.add_argument("--probe-args", default="{}", help="valid tool arguments as JSON")
    args = parser.parse_args()
    probe_args = json.loads(args.probe_args)
    if not isinstance(probe_args, dict):
        parser.error("--probe-args must be a JSON object")
    server = getattr(importlib.import_module(args.module), args.object)
    try:
        result = asyncio.run(check_server(server, probe_tool=args.probe_tool,
                                         probe_args=probe_args, prefix=args.prefix))
    except ValueError as exc:
        print(json.dumps({"verdict": "fail", "reason": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# HS-4 P2 MCP session contract

The P2 carry is a conditional acceptance requirement for a separate memory MCP
server. There is no such server in the current orchestrator configuration.
The reusable acceptance check now covers that contract without inventing a
production memory interface or exposing candidate trace tools.

Source inspected: `epyc-orchestrator` git commit
`273ba3ff85347c6429b5b86a6200073010d3f703`, specifically `src/mcp_server.py`,
`src/trace/mcp_tools.py`, `.mcp.json`, `orchestration/mcp_servers.yaml`, and
`tests/unit/test_mcp_undeclared_args_refused.py`.
The default server exposes 11 tools, none with a `memory_` name. Candidate
`ms.search` and `ms.expand` definitions accept `session_id` but are not registered
in that default catalog.

`scripts/harness/hs4_mcp_session_contract.py` uses the target server's pinned
FastMCP environment. It checks every selected tool for an optional string
`session_id` and `additionalProperties: false`, then makes a caller-selected
read-only probe with a session stamp and proves an unknown argument is explicitly
refused. Empty catalogs and unmatched prefixes fail. Select only a safe read-only
probe: its first call executes normally. This check does not validate session
isolation, memory writes, retrieval quality, or deployment.

Example for the current catalog, from the root lane:

```bash
PYTHONPATH=/mnt/raid0/llm/epyc-orchestrator \
  /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python \
  scripts/harness/hs4_mcp_session_contract.py \
  --module src.mcp_server --probe-tool list_canvases \
  --probe-args '{"directory":"/nonexistent-hs4-probe"}'
```

When a separate server ships, run the same check with its module/object and
read-only tool. OpenCode adds the server name to tool names; for a server named
`memory`, local tool names can be `profile_get` rather than `memory_profile_get`.
Leave `--prefix` empty to check that server's entire catalog. Use `--prefix
memory_` only for a catalog whose local tool names actually have that prefix.
No absent-server result counts as a passing server acceptance.

Validation on 2026-11-19: the current 11-tool catalog passed both schema checks
and the stamped/refused call controls with FastMCP 3.3.1. The existing orchestrator
argument-contract suite passed 11 tests. The new root suite passed 10 tests,
including a synthetic separate memory server, refusal before handler execution,
missing/required/wrong-type session keys, permissive schemas, empty catalogs,
unmatched prefixes and reserved probe arguments.

The root tests require pytest and FastMCP. This host's pinned server environment
has FastMCP but no pytest; its test invocation used the host's pure-Python pytest:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages \
  /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest -q \
  tests/harness/test_hs4_mcp_session_contract.py
```

These are engineering conformance results, with no inference or efficacy claim.
The existing committed-conclusion observation path can retain this report; the
new check is not a wired belief source or a new grading rule.

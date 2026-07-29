# 2026-05-26 — FastMCP v3 Migration + Tool-Output-Compression Phase 4 Unblock

## Problem

Three active handoffs (`tool-output-compression`, `internal-kb-rag`, `meta-harness-optimization`) reference MCP-tool wrapping as forward work without naming the framework. `epyc-orchestrator/src/mcp_server.py` runs a live FastMCP server on the **vendored-v1 path** (`from mcp.server.fastmcp import FastMCP`, pinned via `mcp>=1.0.0`) — the FastMCP 1.0 fork that lives inside Anthropic's official MCP SDK. Standalone FastMCP v3 features (middleware, in-memory client, server composition, OpenAPI/FastAPI conversion, OAuth providers, sampling) are required for the `tool-output-compression` Phase 3 / Phase 4 work but are not available on the v1 path. Question: migrate.

## Changes

### Research intake — `intake-609` (FastMCP)

| Repo | File | Change |
|------|------|--------|
| epyc-root | `research/intake_index.yaml` | New entry `intake-609` (FastMCP v3 repo, `adopt_component`) + 35-line `notes` block with v1-vs-v3 feature boundary verified against `gofastmcp.com/clients/transports`, `gofastmcp.com/servers/middleware`, and live source inspection of `fastmcp_slim/fastmcp/server/server.py` / `tools/function_tool.py` via `gh api`. |

### FastMCP v3 migration (epyc-orchestrator)

| Repo | File | Change |
|------|------|--------|
| epyc-orchestrator | `pyproject.toml` | Added `fastmcp>=3,<4`; kept `mcp>=1.0.0` explicit (used by `src/mcp_client.py` for `ClientSession`, `mcp.types.*`; fastmcp brings it transitively but explicit pin protects against future drops). |
| epyc-orchestrator | `src/mcp_server.py` | Single import change: `from mcp.server.fastmcp import FastMCP` → `from fastmcp import FastMCP`. All 11 `@mcp.tool()` decorators unchanged, `FastMCP("orchestrator-info")` unchanged, `mcp.run(transport="stdio")` unchanged. |

### Handoff refinements

| Repo | File | Change |
|------|------|--------|
| epyc-root | `handoffs/active/tool-output-compression.md` | Added **Phase 4 — MCP Tool Wrapping** (5 work-items P4a–P4e): bash-compressor MCP server, around-style `CompressorMiddleware`, downstream-top-up-rate measurement (per intake-605 audit refinement), `.mcp.json` registration + Claude Code smoke test, roll-out decision gate. Promotes line-49 "Future work: wrap compression as an MCP tool" to actionable. |
| epyc-root | `handoffs/active/internal-kb-rag.md` | Clarified K6 was satisfied via the kb-search skill route, not an MCP-tool variant. Framework choice now settled (v3) if a future workflow needs the MCP variant — no current work unblocked. |
| epyc-root | `handoffs/active/meta-harness-optimization.md` | Clarified HLE-1/2/3 are trace-schema + eval-methodology work, not MCP-tool work. Framework choice now settled — no current HLE work unblocked. Middleware precedent cross-references `tool-output-compression` Phase 4 P4b. |

## Key Findings

**v1-vs-v3 feature boundary** (verified via authoritative docs + live source):

| Feature | Vendored v1 (`mcp.server.fastmcp`) | Standalone v3 (`fastmcp`) |
|---|---|---|
| `@mcp.tool / @mcp.resource / @mcp.prompt` decorators | ✅ | ✅ |
| stdio / SSE / streamable-HTTP transports | ✅ | ✅ |
| In-memory transport (subprocess-free testing) | ❌ | ✅ |
| Around-style middleware (`on_call_tool`, `on_message`, …) | ❌ | ✅ |
| Server composition / mounting | ❌ | ✅ |
| Proxy server | ❌ | ✅ |
| OpenAPI / FastAPI conversion (`from_openapi`, `from_fastapi`) | ❌ | ✅ |
| OAuth provider library (15+ providers) | bearer-only | ✅ |
| LLM sampling primitive | ❌ | ✅ |

**Surprise corrections vs the original deep-dive**:
- `@mcp.tool()` in v3 **does** preserve the original function as a plain callable (`type(decorated_fn).__name__ == 'function'`, still callable). Verified empirically with `fastmcp==3.3.1`. Earlier concern that direct-import tests would break was wrong — no test changes needed.
- Migration reduced to **2 file edits, 8 inserted / 2 deleted lines total**.

## Results

| Verification | Outcome |
|---|---|
| `pytest tests/unit/test_mcp_server.py` | 12 / 12 passed |
| `pytest tests/unit/test_mcp_chat_tool.py` | 15 / 15 passed |
| `pytest tests/unit/test_mcp_client.py` | 13 / 13 passed (mcp SDK still works via explicit pin) |
| `mcp.list_tools()` after import | 11 tools registered (all original tools preserved) |
| `python src/mcp_server.py` stdio boot | Clean startup + clean EOF exit |
| `python3 .claude/skills/research-intake/scripts/validate_intake.py` | OK, 609 entries |

## Unblocked Work

| Handoff | Status | Notes |
|---|---|---|
| `tool-output-compression` | **Phase 4 ready to start** | 5 work-items added (P4a–P4e). Dependencies satisfied. |
| `internal-kb-rag` | No new work | K6 already satisfied via skill route; MCP variant remains optional. |
| `meta-harness-optimization` | No new work | HLE-1/2/3 not MCP-blocked; framework choice settled if HLE-1 ever needs `on_call_tool` evidence emission. |

## Deferred

- `epyc-orchestrator/pyproject.toml` extras (`toon`, `sandbox`, `colbert-export`) untouched. uv.lock not regenerated in this session; will refresh on next `uv sync`.
- Commit on epyc-orchestrator is 1 ahead of `origin/main` from prior session (`19f8883 docs(bep harness): Phase 0 …`) — this session's commit lands on top; both will need to be pushed.

## References

- intake-609 (`research/intake_index.yaml`) — full feature boundary + migration cost analysis in `notes` field
- `gofastmcp.com/clients/transports` — in-memory transport confirmation
- `gofastmcp.com/servers/middleware` — middleware-is-FastMCP-specific confirmation
- `github.com/PrefectHQ/fastmcp` (`fastmcp_slim/fastmcp/server/server.py`, `tools/function_tool.py`) — source inspection for decorator return type

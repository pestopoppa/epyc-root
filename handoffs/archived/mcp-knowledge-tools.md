# HANDOFF: MCP Integration & Knowledge Tools

> **Status**: ✅ PHASES 1-2 COMPLETE (2026-01-29)
> **Priority**: Medium
> **Blocking**: None
> **Blocked by**: —
> **Phase 3**: MCP client infrastructure — DEFERRED (design only, no immediate need)

---

## Context

A colleague reviewed our tooling architecture and recommended full MCP adoption. After thorough evaluation of the actual codebase (not just docs), we concluded:

- **Colleague was partially right**: MCP for external knowledge services and Claude Code interop
- **Colleague was wrong**: MCP for local tools (40+ in-process Python functions stay native), "no dynamic discovery" (already exists via `my_role()`, `list_tools()`, `DEFAULT_ROOT_LM_TOOLS`), "2023 agent stack" (MemRL/Q-scoring/TOON already exceed MCP targets)
- **Performance**: Neutral for external tools (API latency dominates), negative for local tools

**Decision**: Hybrid approach — native Python tools for free-API knowledge services, MCP only for Claude Code interop.

---

## What to Build

### Phase 1: Native Knowledge Tools (4 tools)

Build in-process Python tools registered in the existing tool registry. Zero transport overhead, no API keys.

**File to create**: `src/tools/knowledge.py` (+ `src/tools/__init__.py`)

#### Tool 1: `search_arxiv(query, max_results=10)`
- Package: `arxiv` (MIT, well-maintained)
- Returns: title, authors, abstract, arxiv_id, published date, PDF URL
- Rate limit: 3-second politeness delay (built into package)
- No API key required

#### Tool 2: `search_papers(query, max_results=10, year_range=None, fields_of_study=None)`
- Package: `semanticscholar`
- Returns: title, authors, abstract, citation count, year, DOI, S2 paper ID
- Rate limit: 100 requests/5 min without key (sufficient for research)
- No API key required (key optional for higher limits)

#### Tool 3: `search_wikipedia(query, max_results=5, language="en")`
- Package: `mwclient` (MediaWiki API)
- Returns: title, summary extract, URL, categories
- Also implement: `get_wikipedia_article(title)` for full article text
- No API key required

#### Tool 4: `search_books(query, max_results=10, filter=None)`
- Package: `google-api-python-client` (Google Books API)
- Returns: title, authors, publisher, published date, description, ISBN, preview link
- Rate limit: 1000 queries/day free, no key required for public volume search
- Filter options: "ebooks", "free-ebooks", partial/full availability

**Register in YAML** — add to `orchestration/tool_registry.yaml` under `web` category:

```yaml
search_arxiv:
  category: web
  description: "Search arXiv for academic papers by keyword, author, or topic"
  parameters:
    query: {type: string, required: true}
    max_results: {type: integer, required: false, default: 10}
  returns: {type: array, items: "ArxivPaper"}
  implementation:
    type: python
    module: src.tools.knowledge
    function: search_arxiv
  permissions: [network]

search_papers:
  category: web
  description: "Search Semantic Scholar for academic papers with citation data"
  parameters:
    query: {type: string, required: true}
    max_results: {type: integer, required: false, default: 10}
    year_range: {type: string, required: false, description: "e.g. 2020-2025"}
  returns: {type: array}
  implementation:
    type: python
    module: src.tools.knowledge
    function: search_papers
  permissions: [network]

search_wikipedia:
  category: web
  description: "Search Wikipedia articles"
  parameters:
    query: {type: string, required: true}
    max_results: {type: integer, required: false, default: 5}
  returns: {type: array}
  implementation:
    type: python
    module: src.tools.knowledge
    function: search_wikipedia
  permissions: [network]

search_books:
  category: web
  description: "Search Google Books for publications"
  parameters:
    query: {type: string, required: true}
    max_results: {type: integer, required: false, default: 10}
  returns: {type: array}
  implementation:
    type: python
    module: src.tools.knowledge
    function: search_books
  permissions: [network]
```

**REPL integration**: Automatic — tools available via `TOOL("search_arxiv", query="...")`. No changes to `src/repl_environment.py` needed; it already delegates to `tool_registry.invoke()`.

**May need**: Extend `load_from_yaml()` in `src/tool_registry.py` if the new module path `src.tools.knowledge` isn't handled by the existing dynamic import logic.

### Phase 2: MCP Server for Claude Code (Read-Only)

**File to create**: `src/mcp_server.py`

Standalone script using FastMCP. Claude Code launches it via stdio transport.

```python
#!/usr/bin/env python3
"""Read-only MCP server exposing orchestrator info to Claude Code."""
import sys
sys.path.insert(0, "/mnt/raid0/llm/claude")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("orchestrator-info")

@mcp.tool()
def lookup_model(role: str) -> str:
    """Look up model config for an orchestrator role."""
    from src.registry_loader import RegistryLoader
    registry = RegistryLoader(validate_paths=False)
    role_config = registry.get_role(role)
    return (
        f"Role: {role}\nTier: {role_config.tier}\n"
        f"Model: {role_config.model.name}\n"
        f"Speed: {role_config.performance.optimized_tps} t/s"
    )

@mcp.tool()
def list_roles() -> str:
    """List all configured orchestrator roles."""
    from src.registry_loader import RegistryLoader
    registry = RegistryLoader(validate_paths=False)
    lines = []
    for tier in ["A", "B", "C", "D"]:
        roles = registry.get_roles_by_tier(tier)
        if roles:
            lines.append(f"\n--- Tier {tier} ---")
            for r in roles:
                speed = r.performance.optimized_tps or r.performance.baseline_tps or "?"
                lines.append(f"  {r.name}: {r.model.name} ({r.acceleration.type}, {speed} t/s)")
    return "\n".join(lines)

@mcp.tool()
def server_status() -> str:
    """Get current status of all orchestrator services."""
    import json
    from pathlib import Path
    state_file = Path("/mnt/raid0/llm/claude/logs/orchestrator_state.json")
    if not state_file.exists():
        return "No orchestrator state file found. Stack may not be running."
    state = json.loads(state_file.read_text())
    lines = [f"{name}: PID {info['pid']} on port {info['port']} (started {info['started_at']})"
             for name, info in state.items()]
    return "\n".join(lines) or "No services running."

@mcp.tool()
def query_benchmarks(model_name: str = "", suite: str = "") -> str:
    """Query benchmark results from summary.csv."""
    import csv
    from pathlib import Path
    csv_path = Path("/mnt/raid0/llm/claude/benchmarks/results/reviews/summary.csv")
    if not csv_path.exists():
        return "No benchmark summary found."
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader
                if (not model_name or model_name.lower() in r.get("model", "").lower())
                and (not suite or suite in r)]
    if not rows:
        return f"No results matching model='{model_name}' suite='{suite}'"
    lines = []
    for r in rows:
        lines.append(f"{r.get('model', '?')}: {r.get('pct_str', '?')} ({r.get('avg_tps', '?')} t/s)")
    return "\n".join(lines)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Claude Code config** — add to `.claude/settings.json` or project `.mcp.json`:
```json
{
  "mcpServers": {
    "orchestrator": {
      "command": "/home/daniele/miniforge3/bin/python3",
      "args": ["/mnt/raid0/llm/claude/src/mcp_server.py"],
      "env": {"PYTHONPATH": "/mnt/raid0/llm/claude"}
    }
  }
}
```

### Phase 3: MCP Client Infrastructure (Deferred — Design Only)

The `_invoke_mcp()` stub in `src/tool_registry.py:357-377` stays as `NotImplementedError` for now. Architecture designed for future use:

- **When needed**: GitHub (complex API), Google Scholar (scraping), Google Patents (SerpAPI)
- **Design**: `MCPClientManager` in `src/mcp_client.py` with lazy on-demand subprocess launch, connection pooling (one session per server, 5min idle timeout), max 3 retries, graceful shutdown
- **Feature flag**: `ORCHESTRATOR_MCP=1` in `src/features.py`
- **Transport**: MCP stdio (subprocess children, NOT HTTP services, NOT in `orchestrator_stack.py`)
- **Sync/async bridge**: ThreadPoolExecutor at `_invoke_mcp()` boundary (invoke() is sync, MCP SDK is async)
- **TypeScript servers**: `npx -y PACKAGE` (Node.js v22 already present)

---

## Resume Commands

```bash
# 1. Install dependencies
cd /mnt/raid0/llm/claude
source .venv/bin/activate  # pace-env
pip install arxiv semanticscholar mwclient google-api-python-client "mcp>=1.25,<2"
# NOTE: .venv has broken python3.13 symlink. Use system python3 (miniforge3) instead.

# 2. Create knowledge tools module
mkdir -p src/tools
touch src/tools/__init__.py
# Then implement src/tools/knowledge.py (see specs above)

# 3. Register tools in YAML
# Edit orchestration/tool_registry.yaml — add entries under web category (see YAML above)

# 4. Wire into tool registry
# Check if src/tool_registry.py load_from_yaml() handles src.tools.knowledge module path
# If not, extend the dynamic import logic

# 5. Create MCP server
# Implement src/mcp_server.py (see code above)

# 6. Write tests
# tests/unit/test_knowledge_tools.py — mock API responses
# tests/unit/test_mcp_server.py — import tools directly

# 7. Run gates
make gates
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/tools/__init__.py` | Package init |
| `src/tools/knowledge.py` | 4 native knowledge tools |
| `src/mcp_server.py` | Read-only MCP server for Claude Code |
| `tests/unit/test_knowledge_tools.py` | Unit tests (mock APIs) |
| `tests/unit/test_mcp_server.py` | MCP server tests |

## Files to Modify

| File | Change |
|------|--------|
| `orchestration/tool_registry.yaml` | Add 4 tool entries under `web` category |
| `src/tool_registry.py` | Extend `load_from_yaml()` if needed for new module path |

## Files NOT Modified (Intentionally)

| File | Why |
|------|-----|
| `src/repl_environment.py` | Already delegates to tool_registry.invoke() |
| `src/script_registry.py` | MCP client deferred; stub stays |
| `src/api/__init__.py` | No MCP client init needed in Phase 1 |
| `scripts/server/orchestrator_stack.py` | MCP servers are stdio subprocesses, not HTTP services |

---

## Design Decisions (Rationale)

| Decision | Choice | Why |
|----------|--------|-----|
| Native vs MCP for knowledge tools | Native | Free APIs, zero overhead, no subprocess management, no API keys |
| MCP for Claude Code | MCP server | Only protocol for Claude interop; no native alternative |
| Google Scholar/Patents | Skip | No free API; Semantic Scholar + arXiv cover academic needs |
| GitHub | Defer | Add later; 60 req/hr free is usable without PAT |
| MCP client infrastructure | Design only | No immediate need; native tools cover Phase 1 |
| Error handling | Return error strings | Tools called from REPL; errors should inform, not crash |
| Rate limiting | Use package defaults | arXiv 3s delay, S2 100/5min — sufficient for research use |

---

## Background: Colleague's Review Evaluation

**What they got right**: External knowledge access, process isolation for untrusted calls, Claude Code interop via MCP, clean separation of concerns.

**What they got wrong**: "LLM cannot discover tools" (already can via `my_role()`, `list_tools()`, prompt injection), "no dynamic discovery" (ToolRegistry loads from YAML dynamically), "2023 agent stack" (MemRL-learned routing, Q-scoring, TOON encoding exceed MCP-style targets), "each tool should be an MCP server" (wrong for 40+ in-process local tools).

**Root cause**: Colleague reviewed docs/YAML only, not the Python implementation (`src/tool_registry.py`, `src/repl_environment.py`, `src/prompt_builders.py`).

---

## External MCP Servers (Reference, for Phase 3)

| Server | Repo | Status |
|--------|------|--------|
| arXiv | [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server) | Available, Python, MIT |
| GitHub | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Official, TypeScript |
| Google Scholar | [JackKuo666/Google-Scholar-MCP-Server](https://github.com/JackKuo666/Google-Scholar-MCP-Server) | Available, Python, web scraping (fragile) |
| Semantic Scholar | [JackKuo666/semanticscholar-MCP-Server](https://github.com/JackKuo666/semanticscholar-MCP-Server) | Available, Python, proper API |
| Google Patents | [KunihiroS/google-patents-mcp](https://github.com/KunihiroS/google-patents-mcp) | Available, TypeScript, needs SerpAPI key |
| Web Fetch | @anthropic/fetch (official) | Available, TypeScript |
| Multi-source | [openags/paper-search-mcp](https://github.com/openags/paper-search-mcp) | Available, Python, 8+ platforms |

---

## Completion Checklist

- [x] Install Python packages (`arxiv`, `semanticscholar`, `mwclient`, `google-api-python-client`, `mcp`) — 2026-01-29
- [x] Create `src/tools/__init__.py` — already existed
- [x] Create `src/tools/knowledge.py` with 5 tools (added `get_wikipedia_article` as separate tool) — 2026-01-29
- [x] Add YAML entries to `orchestration/tool_registry.yaml` (5 entries, total 46 tools) — 2026-01-29
- [x] Verify `load_from_yaml()` handles new module path — confirmed, no changes needed — 2026-01-29
- [x] Write `tests/unit/test_knowledge_tools.py` (23 tests passing) — 2026-01-29
- [x] Create `src/mcp_server.py` (4 read-only tools via FastMCP) — 2026-01-29
- [x] Write `tests/unit/test_mcp_server.py` (12 tests passing) — 2026-01-29
- [x] Add Claude Code MCP config (`.mcp.json` in project root) — 2026-01-29
- [x] Fix `.mcp.json`: broken `.venv/bin/python` symlink → use system `python3` — 2026-01-29
- [x] Install `mcp` in system Python (miniforge3) — 2026-01-29
- [x] Run tests — 35/35 passing (verified after .mcp.json fix) — 2026-01-29
- [ ] Live smoke test (actual API calls, after benchmarks finish)
- [ ] Extract findings to `docs/chapters/` — add Chapter 24: Knowledge Tools & MCP
- [ ] Update `handoffs/README.md` table
- [ ] Delete this handoff

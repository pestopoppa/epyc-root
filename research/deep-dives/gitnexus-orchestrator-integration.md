# GitNexus Integration Assessment: epyc-orchestrator

**Date**: 2026-03-16
**Parent**: [gitnexus-codebase-intelligence.md](gitnexus-codebase-intelligence.md) (deep dive)
**Focus**: Concrete integration paths for the orchestrator's coding agents

## Current State

GitNexus is installed globally (`npm install -g gitnexus`) and all 4 EPYC repos are indexed:

| Repo | Symbols | Edges | Clusters | Flows |
|------|---------|-------|----------|-------|
| epyc-orchestrator | 12,187 | 33,049 | 686 | 300 |
| epyc-inference-research | 2,254 | 4,067 | 189 | 53 |
| epyc-root | 381 | 431 | 9 | 5 |
| epyc-llama | 77,195 | 112,350 | 1,346 | 510 |

The auto-generated CLAUDE.md sections and MCP tool instructions are already in place for Claude Code sessions. The question is: how should the **orchestrator's own coding agents** (coder_escalation, architect_coding) use this graph?

## Integration Options (Ranked by ROI)

### Option 1: MCP Tool Server (Highest ROI, Lowest Effort)

**How**: Run `gitnexus mcp` as an MCP server alongside the orchestrator. The orchestrator's LLM agents already invoke tools via the REPL `TOOL()` dispatch. GitNexus MCP exposes 7 tools (query, context, impact, detect_changes, rename, cypher, list_repos) that the coding model can call directly.

**Wiring**:
1. Add GitNexus as an MCP server in the orchestrator's server config (stdio transport)
2. The 7 tools auto-register through MCP discovery — no YAML entries needed
3. Add to coder_escalation and architect_coding prompt templates: "Before modifying any function, call `gitnexus_impact` to check blast radius"

**Effort**: ~20 lines of config, zero Python code
**Risk**: Node.js subprocess per MCP call (latency ~50-500ms per tool call)
**Value**: Coding agents get dependency-aware context before every edit

### Option 2: REPL Tool Wrappers (Medium Effort, Full Control)

**How**: Register 3 new tools in `orchestration/tool_registry.yaml` that shell out to `gitnexus` CLI.

```yaml
# orchestration/tool_registry.yaml
codebase_impact:
  category: code
  description: "Analyze blast radius before modifying a symbol"
  parameters:
    symbol: {type: string, required: true}
    direction: {type: string, required: false, default: "upstream"}
    min_confidence: {type: number, required: false, default: 0.7}
  implementation:
    type: python
    module: orchestration.tools.codebase_intelligence
    function: codebase_impact

codebase_context:
  category: code
  description: "360-degree view of a symbol's relationships"
  parameters:
    symbol: {type: string, required: true}
  implementation:
    type: python
    module: orchestration.tools.codebase_intelligence
    function: codebase_context

codebase_changes:
  category: code
  description: "Map current staged changes to affected flows and risk level"
  implementation:
    type: python
    module: orchestration.tools.codebase_intelligence
    function: codebase_changes
```

**Handler** (`orchestration/tools/codebase_intelligence.py`, ~80 lines):

```python
import subprocess, json

def _gitnexus_cli(*args: str) -> str:
    result = subprocess.run(
        ["gitnexus", *args, "--json"],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"

def codebase_impact(symbol: str, direction: str = "upstream", min_confidence: float = 0.7) -> dict:
    raw = _gitnexus_cli("impact", symbol, f"--direction={direction}", f"--min-confidence={min_confidence}")
    return json.loads(raw) if raw.startswith("{") else {"error": raw}

def codebase_context(symbol: str) -> dict:
    raw = _gitnexus_cli("context", symbol)
    return json.loads(raw) if raw.startswith("{") else {"error": raw}

def codebase_changes() -> dict:
    raw = _gitnexus_cli("detect-changes")
    return json.loads(raw) if raw.startswith("{") else {"error": raw}
```

**Effort**: ~120 lines (handler + YAML + role permissions)
**Risk**: Subprocess overhead (~50ms for context, ~500ms for impact). `gitnexus impact` has a known segfault on some queries (exit 139, KuzuDB native binding issue).
**Value**: Same as Option 1, but tools are version-controlled, testable, and follow the existing registry pattern.

### Option 3: Auto-Inject Context into Prompts (Highest Value, Medium Effort)

**How**: When `_execute_turn()` is about to build the coder prompt, automatically query GitNexus for relevant context and inject it alongside the existing `gathered_context`.

**Integration point**: `src/graph/helpers.py` lines 1276-1327, after `_auto_gather_context()`:

```python
# After gathered_context (line 1276), before prompt build
if _get_features().gitnexus_context_injection:
    from orchestration.tools.codebase_intelligence import codebase_context
    # Extract symbols from task_ir plan
    target_symbols = _extract_target_symbols(state)
    if target_symbols:
        gi_context = []
        for sym in target_symbols[:3]:  # max 3 symbols
            ctx_data = codebase_context(sym)
            if "error" not in ctx_data:
                gi_context.append(f"### {sym}\n{_format_context(ctx_data)}")
        if gi_context:
            gathered_context += "\n\n[Codebase Intelligence]\n" + "\n".join(gi_context)
```

**What the model sees** (injected into prompt):
```
[Codebase Intelligence]
### _execute_turn
Callers (7): BaseNode.run, CoderNode.run, ArchitectNode.run, ...
Callees (30): _record_session_turn, _clear_stale_tool_outputs, ...
Processes: MainREPLLoop, ErrorRecoveryFlow, EscalationPipeline
Cluster: CoreGraphExecution (cohesion: 0.89)
```

**Effort**: ~150 lines (feature flag + symbol extraction + context formatting + injection)
**Risk**: Adds ~50-150ms per turn for context lookup. Requires symbol extraction heuristic from task_ir.
**Value**: **Highest** — the model gets dependency context *before* it writes code, without needing to call a tool. This is the "front-load intelligence" pattern that matches our prefix caching philosophy.

### Option 4: Pre-Commit Validation (Safety Net)

**How**: After the coder produces code and before accepting it, run `detect_changes` to verify the blast radius matches expectations.

**Integration point**: `_execute_turn()` return path, or a new post-generation hook:

```python
# After code is accepted, before returning
if _get_features().gitnexus_pre_commit_check:
    from orchestration.tools.codebase_intelligence import codebase_changes
    impact = codebase_changes()
    if impact.get("risk") in ("HIGH", "CRITICAL"):
        state.last_error = f"High-risk change detected: {impact.get('description')}"
        # Optionally: trigger approval gate
```

**Effort**: ~50 lines
**Risk**: False positives could block valid changes. Needs tuning.
**Value**: Catches unintended side effects before they propagate.

### Option 5: KuzuDB Direct Queries (Advanced, No Subprocess)

**How**: Use KuzuDB's Python bindings (`pip install kuzu`) to query the GitNexus-built graph directly, eliminating subprocess overhead.

```python
import kuzu
db = kuzu.Database('/mnt/raid0/llm/epyc-orchestrator/.gitnexus/kuzu')
conn = kuzu.Connection(db)
result = conn.execute("""
    MATCH (caller)-[c:CALLS]->(target:SYMBOL {name: $name})
    WHERE c.confidence >= 0.7
    RETURN caller.name, caller.filePath, c.confidence
    ORDER BY c.confidence DESC
""", {"name": "_execute_turn"})
```

**Effort**: ~200 lines (Python query layer, schema mapping, connection pooling)
**Risk**: Tight coupling to GitNexus's KuzuDB schema. Schema may change between versions.
**Value**: Sub-millisecond queries, native Python, no Node.js dependency at runtime.

## Recommended Implementation Order

| Phase | Option | Effort | Description |
|-------|--------|--------|-------------|
| 1 | **Option 2** | 1-2 hours | REPL tool wrappers — follows existing registry pattern, immediately testable |
| 2 | **Option 3** | 2-3 hours | Auto-inject context — biggest impact on code quality, feature-flagged |
| 3 | **Option 4** | 1 hour | Pre-commit validation — safety net, catches blast radius issues |
| 4 | **Option 5** | 4-6 hours | Direct KuzuDB queries — eliminate subprocess, production-grade |

Option 1 (MCP server) is an alternative to Option 2, not additive. Choose one or the other.

## Key Insight: Context Injection > Tool Calling

The most valuable integration is **not** giving the model a tool to call — it's **injecting dependency context into the prompt before the model writes code**. Our session log already does this for turn history. GitNexus context injection would do the same for dependency awareness.

The model currently discovers dependencies through trial-and-error REPL cycles: grep → read → grep → read. Each cycle costs a full REPL turn (~5-10s + tokens). A single GitNexus context query returns the same information in <100ms and zero tokens. For `_execute_turn` (7 callers, 30+ callees, 3 processes), this replaces 5-8 grep turns with one injected context block.

## Re-Indexing Strategy

Indexes go stale as code changes. Options:
- **Manual**: `gitnexus analyze /mnt/raid0/llm/epyc-orchestrator` after major changes
- **Session init**: Add to `scripts/session/session_init.sh` — re-index at session start
- **Post-commit hook**: Re-index after git commits (latency: 2-5s for incremental)
- **Sync script**: Already wired — `scripts/repos/sync-repos.sh --index` re-indexes all repos

Recommended: add to `session_init.sh` for freshness, with a staleness check (compare HEAD sha to indexed commit).

## Dependencies & Constraints

- **Runtime**: Node.js required for `gitnexus` CLI (Options 1-4). Option 5 eliminates this.
- **License**: PolyForm Noncommercial 1.0.0 — fine for personal/research use, not for commercial distribution.
- **Known issue**: `gitnexus impact` can segfault (exit 139) on some queries, likely KuzuDB native binding issue. `gitnexus context` is reliable. Wrap all calls in try/except with timeout.
- **Disk**: ~50MB per indexed repo (KuzuDB + HNSW index). All 4 repos total ~200MB.

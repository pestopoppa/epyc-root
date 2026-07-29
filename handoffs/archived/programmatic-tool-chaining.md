# Handoff: Programmatic Tool Chaining for the Orchestrator

**Created**: 2026-02-18
**Status**: RESEARCH COMPLETE — Ready for implementation
**Priority**: HIGH
**Triggered by**: Analysis of Anthropic's Programmatic Tool Calling API feature
**Related handoffs**:
- `perf-parallel-tools-concurrent-sweep-prefix-cache.md` (WS1: parallel read-only dispatch — already shipped)
- `orchestration-architecture-optimization-handoff.md` (routing + telemetry stack — context dependency)
- `unified_execution_model.md` (React→REPL unification — architectural predecessor, COMPLETE)
- `native-computational-tools.md` (C++ tool binary — tool integration patterns)
- `handoffs/active/rlm-orchestrator-roadmap.md` (master roadmap — this handoff should be linked into Phase 9+)

---

## 1) Executive Summary

Anthropic's [Programmatic Tool Calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling) lets Claude write Python code that calls tools as async functions inside a sandboxed container. The container pauses on each tool call, returns control to the client for fulfillment, then resumes execution. Intermediate tool results stay in code — only the final `stdout` enters the model's context window.

This handoff operationalizes that pattern for our local orchestrator. The core thesis:

> **Our REPL already has 80% of the infrastructure. The missing 20% — deferred context injection, multi-mutation chaining, and persistent execution state — would eliminate 3-10x token waste and 2-4x latency overhead on multi-tool tasks, which are currently the dominant cost driver in complex orchestration workflows.**

### Three implementation phases

| Phase | Name | Effort | Impact | Risk |
|-------|------|--------|--------|------|
| **1** | Deferred Tool Results | LOW | HIGH | LOW |
| **2** | Multi-Mutation Tool Chaining | MEDIUM | HIGH | MEDIUM |
| **3** | Persistent Execution Context | HIGH | MEDIUM-HIGH | HIGH |

Phase 3 enables cross-request persistence (globals survive across separate API calls) by extending the existing session/checkpoint infrastructure — equivalent to Anthropic's container reuse via the `container` field. Within a task, globals already persist (one REPL per task, shared `_globals` dict). Phase 3 adds checkpoint serialization of user-defined variables and restore-on-resume, positioning the local orchestrator as a fully self-hosted alternative to Anthropic's cloud-managed approach.

---

## 2) Reference: Anthropic's Programmatic Tool Calling (Complete Summary)

### 2.1 Core Mechanism

The feature requires code execution (`code_execution_20250825`) to be enabled. When a tool is marked with `allowed_callers: ["code_execution_20250825"]`, Claude can write Python code that calls that tool as an async function:

```python
# Claude generates this code inside a sandboxed container:
results = await query_database("SELECT * FROM sales WHERE region='West'")
top_customers = sorted(results, key=lambda x: x['revenue'], reverse=True)[:5]
print(f"Top 5 customers: {top_customers}")
```

### 2.2 Execution Flow

```
1. Claude writes Python code that invokes tools as functions
   (potentially including loops, conditionals, aggregation)
       ↓
2. Code runs in sandboxed container via code execution
       ↓
3. When a tool function is called → container PAUSES
   → API returns a `tool_use` block to the client
       ↓
4. Client provides tool result → container RESUMES
   → intermediate results NOT loaded into Claude's context window
       ↓
5. Code continues (more tool calls, processing, etc.)
       ↓
6. Once all code execution completes → Claude receives ONLY the
   final stdout output and continues working on the task
```

### 2.3 Key API Structure

**Tool definition with `allowed_callers`:**

```json
{
  "name": "query_database",
  "description": "Execute a SQL query. Returns JSON rows.",
  "input_schema": {
    "type": "object",
    "properties": {
      "sql": {"type": "string", "description": "SQL query to execute"}
    },
    "required": ["sql"]
  },
  "allowed_callers": ["code_execution_20250825"]
}
```

**Possible `allowed_callers` values:**

| Value | Behavior |
|-------|----------|
| `["direct"]` | Only Claude calls directly (default) |
| `["code_execution_20250825"]` | Only callable from code execution |
| `["direct", "code_execution_20250825"]` | Both paths |

**Programmatic invocation response:**

```json
{
  "type": "tool_use",
  "id": "toolu_xyz789",
  "name": "query_database",
  "input": {"sql": "SELECT ..."},
  "caller": {
    "type": "code_execution_20250825",
    "tool_id": "srvtoolu_abc123"
  }
}
```

The `caller` field with `type: "code_execution_20250825"` distinguishes programmatic calls from direct tool use (`caller.type: "direct"`).

### 2.4 Container Lifecycle

- **Creation**: New container per session (or reused via container ID)
- **Expiration**: ~4.5 minutes of inactivity
- **Reuse**: Pass `container` ID in subsequent requests to maintain state across API calls
- **State**: Python globals persist within a container session

### 2.5 Advanced Patterns (from Anthropic docs)

**Batch processing with loops:**

```python
regions = ["West", "East", "Central", "North", "South"]
results = {}
for region in regions:
    data = await query_database(f"SELECT SUM(revenue) FROM sales WHERE region='{region}'")
    results[region] = sum(row["revenue"] for row in data)

top_region = max(results.items(), key=lambda x: x[1])
print(f"Top region: {top_region[0]} with ${top_region[1]:,}")
```

**Early termination:**

```python
endpoints = ["us-east", "eu-west", "apac"]
for endpoint in endpoints:
    status = await check_health(endpoint)
    if status == "healthy":
        print(f"Found healthy endpoint: {endpoint}")
        break  # Stop early
```

**Conditional tool selection:**

```python
file_info = await get_file_info(path)
if file_info["size"] < 10000:
    content = await read_full_file(path)
else:
    content = await read_file_summary(path)
print(content)
```

**Data filtering (context reduction):**

```python
logs = await fetch_logs(server_id)
errors = [log for log in logs if "ERROR" in log]
print(f"Found {len(errors)} errors")
for error in errors[-10:]:  # Only return last 10
    print(error)
```

### 2.6 Token Efficiency

Anthropic's key insight:

> Tool results from programmatic calls are NOT added to Claude's context — only the final code output is. Intermediate processing happens in code. Calling 10 tools directly uses ~10x the tokens of calling them programmatically and returning a summary.

### 2.7 Constraints and Incompatibilities

| Constraint | Impact |
|---|---|
| Structured outputs (`strict: true`) | Not supported with programmatic calling |
| `tool_choice` forcing | Cannot force programmatic calling of specific tools |
| `disable_parallel_tool_use: true` | Not supported |
| Web search / web fetch / MCP connector tools | Cannot be called programmatically (yet) |
| Tool result response format | Must contain ONLY `tool_result` blocks when responding to programmatic calls |

### 2.8 Alternative Implementation Approaches (from Anthropic docs)

| Approach | Description | Pros | Cons |
|---|---|---|---|
| **Client-side direct execution** | Provide Claude with code exec tool + available functions. Execute locally. | Simple, full control | Untrusted code outside sandbox, injection risk |
| **Self-managed sandboxed execution** | Same from Claude's perspective but code runs in sandboxed container with security restrictions | Safe, full infra control | Complex to build/maintain, IPC overhead |
| **Anthropic-managed execution** | Managed containers with opinionated Python env tuned for Claude | Safe by default, easy setup | Cloud-dependent, latency |

**Our orchestrator maps to the "self-managed sandboxed execution" approach** — we already have the REPL sandbox, AST security visitor, and tool registry. The gap is in the execution model, not the infrastructure.

---

## 3) Current Architecture (Detailed Baseline)

### 3.1 Complete Tool Call Sequence Diagram

```
User Request
    ↓
ChatPipeline._execute_repl(ChatRequest, routing)
    ↓
Create REPLEnvironment (with tool_registry, llm_primitives)
    ↓
run_task(TaskState, TaskDeps) [orchestration graph]
    ├─→ Graph Iterator (pydantic-graph)
    │
    ├─→ FrontdoorNode.run(ctx)
    │   ├─→ _execute_turn(ctx, Role.FRONTDOOR)
    │   │   ├─→ Build LLM prompt (corpus context, REPL state, workspace)
    │   │   ├─→ LLMPrimitives.llm_call(prompt, role=..., stop_sequences=["\n```\n"])
    │   │   ├─→ Extract code from response
    │   │   ├─→ REPL.execute(code)
    │   │   │   ├─→ AST security validation
    │   │   │   ├─→ Unicode sanitization
    │   │   │   ├─→ Structured mode (React) vs Standard mode
    │   │   │   │   ├─→ React: Single non-read-only tool per turn
    │   │   │   │   └─→ Standard: Sequential exec()
    │   │   │   │
    │   │   │   ├─→ Try parallel dispatch (if all read-only)
    │   │   │   │   ├─→ _extract_parallel_calls(code, globals, read_only_tools)
    │   │   │   │   ├─→ execute_parallel_calls(calls, globals, ThreadPoolExecutor)
    │   │   │   │   └─→ Inject results into globals
    │   │   │   │
    │   │   │   └─→ exec(code, globals)
    │   │   │       │
    │   │   │       ├─→ TOOL("list_files", path="/tmp")
    │   │   │       │   ├─→ tool_registry.invoke("list_files", role, path="/tmp")
    │   │   │       │   │   ├─→ can_use_tool(role, "list_files")
    │   │   │       │   │   ├─→ validate_args({path: "/tmp"})
    │   │   │       │   │   ├─→ handler(**kwargs) or _invoke_mcp(server, tool, args)
    │   │   │       │   │   ├─→ Log ToolInvocation(tool_name, args, role, success, elapsed_ms)
    │   │   │       │   │   └─→ return result
    │   │   │       │   └─→ Result injected into globals for subsequent code
    │   │   │       │
    │   │   │       ├─→ llm_batch([prompt1, prompt2], role="worker")
    │   │   │       │   ├─→ ThreadPoolExecutor._real_batch(prompts, role)
    │   │   │       │   └─→ return [result1, result2, ...]
    │   │   │       │
    │   │   │       └─→ FINAL("answer")  or  FINAL_VAR("var")
    │   │   │           └─→ Raise FinalSignal(answer)
    │   │   │
    │   │   ├─→ Capture stdout/stderr
    │   │   ├─→ Handle FinalSignal exception
    │   │   ├─→ Guard: FINAL() rescue (if error but FINAL in raw output)
    │   │   ├─→ Guard: Prose answer rescue
    │   │   ├─→ Guard: Comment-only rescue
    │   │   ├─→ Guard: Silent execution nudge
    │   │   └─→ return (output, error, is_final, artifacts)
    │   │
    │   └─→ Check is_final, error, nudge → decide next node
    │
    ├─→ CoderEscalationNode.run(ctx)  [if escalated]
    │   └─→ _execute_turn(ctx, Role.CODER_ESCALATION)
    │
    └─→ End[TaskResult]  (when FINAL() or max turns reached)
        └─→ Return answer, turns, tools_used, tool_timings, etc.
    ↓
ChatResponse (to API caller)
    └─ answer, turns, tokens_used, elapsed_seconds, tools_used, tool_timings,
       delegation_events, tools_success, parallel_tools_used, ...
```

### 3.2 REPLEnvironment Mixin Architecture

```
REPLEnvironment (src/repl_environment/environment.py:61)
    ├─ _FileToolsMixin          (list_dir, file_info, archive tools)
    ├─ _DocumentToolsMixin      (OCR, figure analysis)
    ├─ _RoutingMixin            (escalate, delegate, my_role, route_advice)
    ├─ _CodeSearchMixin         (code_search, doc_search, NextPLAID)
    ├─ _ProcedureToolsMixin     (run_procedure, benchmarks, gates)
    ├─ _ContextMixin            (FINAL, mark_finding, LLM calls, tool dispatch)
    └─ _StateMixin              (checkpoint, state inspection)
```

### 3.3 Tool Registry Structure

```python
# src/tool_registry.py:208-701
class ToolRegistry:
    _tools: dict[str, Tool]                    # Name → Tool mapping
    _permissions: dict[str, ToolPermissions]   # Role → permissions
    _invocation_log: list[ToolInvocation]      # Audit trail
    _mcp_configs: dict[str, Any] | None        # MCP server configs

@dataclass
class Tool:
    name: str
    description: str
    category: ToolCategory  # WEB, FILE, CODE, DATA, SYSTEM, MATH, LLM, SPECIALIZED
    parameters: dict[str, dict[str, Any]]
    handler: Callable[..., Any] | None
    mcp_server: str | None
    code_hash: str | None           # Integrity hash (first 16 chars of SHA256)
    side_effects: list[str]         # READ_ONLY, CALLS_LLM, MODIFIES_FILES, etc.
    destructive: bool
```

### 3.4 Injected REPL Globals (Complete List)

**File:** `src/repl_environment/environment.py:286-376`

```python
globals_dict = {
    # Context & state
    "context": self.context,
    "artifacts": self.artifacts,

    # Safe modules
    "json", "math", "re", "collections", "itertools", "functools",
    "statistics", "datetime", "fractions", "decimal", "copy",
    "numpy" (if available), "scipy" (if available),

    # Context exploration
    "peek": self._peek,              # First N chars of context/file
    "grep": self._grep,              # Regex search
    "FINAL": self._final,            # Signal completion
    "FINAL_VAR": self._final_var,    # Return variable value

    # Document tools
    "ocr_document", "analyze_figure", "extract_figure",

    # File tools
    "list_dir", "file_info", "archive_open", "archive_extract",
    "archive_file", "archive_search",

    # Web tools
    "web_fetch",

    # Memory
    "recall", "mark_finding", "list_findings",

    # Code/doc retrieval (NextPLAID)
    "code_search", "doc_search",

    # Routing
    "escalate", "my_role", "route_advice", "delegate",

    # Shell (sandboxed)
    "run_shell", "run_python_code",

    # Self-management procedures
    "run_procedure", "list_procedures", "get_procedure_status",
    "checkpoint_create", "checkpoint_restore",
    "registry_lookup", "registry_update",
    "benchmark_run", "benchmark_compare", "gate_run",
    "log_append", "file_write_safe",

    # Long context
    "chunk_context", "summarize_chunks", "context_len",

    # Tool dispatch (conditional on tool_registry)
    "TOOL": self._invoke_tool,       # Invoke registered tool
    "CALL": self._call_tool,         # JSON-serialized result
    "list_tools": self._list_tools,

    # LLM primitives (conditional on llm_primitives)
    "llm_call": self._tracked_llm_call,
    "llm_batch": self._tracked_llm_batch,

    # Script dispatch (conditional on script_registry)
    "SCRIPT": self._invoke_script,
    "find_scripts": self._find_scripts,
}
```

### 3.5 Tool Invocation Lifecycle

```
_invoke_tool(tool_name, **kwargs)    [context.py:334]
    ↓
Permission check: can_use_tool(role, tool_name)
    ↓
Argument validation (types, required params)
    ↓
Execute: handler(**kwargs) OR _invoke_mcp(server, tool, args)
    ↓
Log: ToolInvocation(tool_name, args, role, success, result, elapsed_ms)
    ↓
Track in research_context (lineage graph)
    ↓
Return result → direct to exec() globals
```

### 3.6 Parallel Read-Only Dispatch

**File:** `src/repl_environment/parallel_dispatch.py:1-237`

**Condition for parallel execution:**

```
Code contains multiple function calls?
    ↓ YES
    ├─ All calls to read-only tools? (peek, grep, list_dir, recall, etc.)
    │   ├─ YES → AST analysis: extract func_name + args for each call
    │   │   ├─ All args are literals or globals (no cross-dependencies)?
    │   │   │   ├─ YES → ThreadPoolExecutor (max 4 workers)
    │   │   │   └─ NO  → Fallback to sequential exec()
    │   │   └─ Any complexity → abort, fallback
    │   └─ NO → Fallback to sequential exec()
    └─ NO → Single call, exec() directly
```

**Performance:** 2-4x speedup on multi-tool turns (10-450ms saved per turn).

### 3.7 Tool Dispatch Path Summary Table

| Scenario | Path | Parallelism | Round-Trips |
|---|---|---|---|
| Single tool per turn | `exec(code)` → `TOOL()` → handler | N/A | 1 turn per tool |
| Multiple read-only tools | Parallel dispatch (ThreadPoolExecutor, max 4) | Yes | 1 turn (all tools) |
| Multiple mixed tools | Sequential exec() | No | 1 turn (sequential) |
| Multiple LLM batch calls | ThreadPoolExecutor (role parallelism) | Yes | 1 call (all prompts) |
| MCP tool | Registry → `_invoke_mcp()` → MCP server | Depends | Async to MCP |

### 3.8 Tool Result Flow Into Context

**Within a turn:**

```python
result = TOOL("search", query="x")        # result now in exec() globals
if "found" in result:
    result2 = TOOL("fetch", id=result["id"])  # can use result immediately
# Both results available in same turn's code
```

**Between turns:**

```
Turn 1: exec() runs → tool results stored in artifacts dict
    ↓
Turn 2: Build LLM prompt includes:
    - Previous turn's stdout
    - Artifacts (previous tool results)
    - Full REPL state
    → LLM generates new code
    → code references artifacts from Turn 1
```

**Critical bottleneck**: Between turns, ALL tool results from the previous turn are serialized into the LLM's context window as part of the prompt. For data-heavy tools (large file reads, database queries, grep results), this bloats the context and wastes tokens on the 30B frontdoor model's limited window.

### 3.9 Output Spill Mechanism (Existing Mitigation)

**File:** `src/repl_environment/environment.py:449-528`

When tool output exceeds `config.output_cap`, the REPL already has a mitigation:

1. Spill full output to file (`turn_N.txt`)
2. Use worker LLM (Qwen2.5-7B at 44 t/s) to summarize
3. Rolling summary pattern: each spill passes previous summary + new tail
4. Return `[Output: N chars → spill_path]\n{summary}\nUse peek(spill_path)...`

**Gap**: This only handles output larger than `output_cap`. Normal-sized tool results still enter context verbatim. The programmatic tool chaining approach would keep ALL intermediate results out of context by default.

---

## 4) Gap Analysis: What We Have vs What Anthropic Ships

### 4.1 Feature-by-Feature Comparison

| Anthropic Feature | Our Current State | Gap Size | Notes |
|---|---|---|---|
| Multi-tool in one code block, no re-sampling | Each turn: LLM call → code exec. Multi-tool = multi-turn (except parallel reads) | **LARGE** | Write-tools can't chain without re-sampling |
| Tool results never enter context | Tool results stored in artifacts, fed back as context for next turn | **LARGE** | Bloats context on data-heavy tools |
| `allowed_callers` per tool | No concept of caller type — all tools called same way | **SMALL** | Easy to add as Tool field |
| `caller` field in responses | No distinction between direct and programmatic invocation | **SMALL** | Add to ToolInvocation dataclass |
| Container persistence across API calls | REPL globals persist within a task (one `_globals` dict, all turns share it). Lost between API requests (new `REPLEnvironment` per request). | **MEDIUM** | Cross-request persistence needed; within-task already works |
| Loop over N items with early exit | Works for reads (parallel dispatch). Write tools: one per turn in structured mode | **MEDIUM** | Structured mode blocks this |
| Conditional tool selection in code | Works within a single turn (if/else + TOOL()). Across turns: requires re-sampling | **MEDIUM** | Cross-turn conditionals require LLM |
| Data filtering before context injection | Spill mechanism summarizes large outputs. Normal outputs pass through verbatim | **MEDIUM** | Only large outputs get filtered |
| Async tool calls (`await`) | No async tool dispatch. All tools are synchronous within exec() | **SMALL** | Could add but requires asyncio in sandbox |
| Container timeout (~4.5 min) | No timeout on REPL execution (relies on LLM turn limits) | **SMALL** | Feature flag could add timeout |

### 4.2 Impact Prioritization

```
                          HIGH IMPACT
                              ↑
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    │  Phase 1: Deferred      │  Phase 2: Multi-        │
    │  Tool Results           │  Mutation Chaining      │
    │  (LOW effort)           │  (MEDIUM effort)        │
    │                         │                         │
LOW ├─────────────────────────┼─────────────────────────┤ HIGH
EFFORT                        │                       EFFORT
    │                         │                         │
    │  allowed_callers field  │  Phase 3: Persistent    │
    │  caller field tracking  │  Execution Context      │
    │  (trivial)              │  (HIGH effort)          │
    │                         │                         │
    └─────────────────────────┼─────────────────────────┘
                              │
                              ↓
                          LOW IMPACT
```

---

## 5) Implementation Plan

### Phase 1: Deferred Tool Results (LOW effort, HIGH impact)

#### 5.1.0 Prerequisite Bugfix (P0)

Before Phase 1 work, fix a lock recursion bug in file exploration:

- `src/repl_environment/file_exploration.py:_increment_exploration()` currently self-calls under a non-reentrant lock.
- This can deadlock `peek/grep/list_dir/file_info` and invalidate deferred-mode measurements.
- Treat this as a hard prerequisite for all Phase 1 benchmarking and A/B comparisons.

#### 5.1.1 Concept

Currently, tool results from each turn's code execution are serialized into the next turn's LLM prompt via artifacts and `last_output`. Phase 1 changes this: tool results stay ONLY in the REPL's `globals` dict during execution. Only what the model explicitly `print()`s or passes to `FINAL()` enters the next turn's context.

**Analogy to Anthropic**: This is equivalent to Anthropic's "tool results from programmatic calls are not added to Claude's context — only the final code output is."

#### 5.1.2 Architecture Change

> **CRITICAL CORRECTION (2026-02-18):** The original Phase 1 plan proposed modifying
> `_invoke_tool()` in `context.py`. Deep code exploration revealed this would be a
> **no-op** — `_invoke_tool()` never populates `_tool_outputs` or calls
> `wrap_tool_output()`. The actual context pollution comes from **14 call sites
> across 3 mixin files** that independently do `artifacts.append` +
> `wrap_tool_output()`. This revised plan corrects the architecture.

**Two tool result paths exist — only Path A needs modification:**

```
Path A — Built-in mixin tools (recall, list_dir, code_search, my_role, etc.):
    Methods in routing.py (9 sites), code_search.py (4 sites), file_exploration.py (1 site)
    Each independently does:
        self.artifacts.setdefault("_tool_outputs", []).append(output)
        return wrap_tool_output(output)
    wrap_tool_output() wraps with <<<TOOL_OUTPUT>>>...<<<END_TOOL_OUTPUT>>> delimiters
    Return value enters stdout when model code uses it → captured by redirect_stdout
        → result.output → state.last_output → prompt builder "## Last Output"

Path B — Registry tools via TOOL()/CALL():
    _invoke_tool() in context.py:334 → tool_registry.invoke()
    Does NOT populate _tool_outputs, does NOT wrap output
    Result returned directly to exec() globals variable
    **Already deferred by default** — only enters context if model explicitly print()s it
```

**`_tool_outputs` is not directly injected as a dedicated prompt section.** It is consumed in 4 places:

1. `_resolve_answer()` (helpers.py:1314, chat_utils.py:181) — answer extraction/stripping
2. `_strip_tool_outputs()` (chat_utils.py:118) — regex removal of `<<<TOOL_OUTPUT>>>` delimiters from captured stdout
3. `_tools_success()` (repl_executor.py:52) — heuristic for tool success signal
4. Graph nodes' `is_final` branches (nodes.py: 7 nodes) — pass to `_resolve_answer()`

**Context bloat comes primarily from stdout capture** (Path A's wrapped returns pollute `last_output`).  
**Secondary leak path**: `get_state()` includes artifact previews, so `_tool_outputs` may still appear in prompt state summaries unless explicitly excluded.

```
BEFORE (current — Path A mixin tools):
    Turn 1: role = my_role()
            → _RoutingMixin._my_role() returns wrap_tool_output(json_output)
            → wrapped string (with <<<TOOL_OUTPUT>>> delimiters) assigned to `role` in globals
            → if model prints it or it hits stdout, goes to captured output
            → artifacts["_tool_outputs"].append(json_output)
    Turn 2: LLM prompt includes [Turn 1 stdout with <<<TOOL_OUTPUT>>> blocks]
            → model sees full tool output in "## Last Output"

AFTER (deferred — Path A mixin tools):
    Turn 1: role = my_role()
            → _RoutingMixin._my_role() returns raw json_output (no wrapping)
            → clean JSON assigned to `role` in globals
            → artifacts["_tool_outputs"] NOT populated
            → stdout only contains explicit print() output
    Turn 2: LLM prompt includes [Turn 1 print() output only]
            → prompt also shows "## Available Variables" listing `role` with type+preview

Path B (TOOL()/CALL()) — no change needed, already deferred.
```

**Note:** Globals already persist across turns. `REPLEnvironment._globals` is built once in `__init__()` and reused across all `execute()` calls. Variables set in `exec(code, self._globals)` persist. Path B tools already benefit from this. The deferred mode change makes Path A tools behave consistently with Path B.

#### 5.1.3 Implementation Details

**Step 1: Feature flag** (`src/features.py`, ~15 lines)

Add `deferred_tool_results: bool = False` to `Features` dataclass. Add env var `ORCHESTRATOR_DEFERRED_TOOL_RESULTS`. Add to `summary()`, defaults dicts, env reader.

**Step 2: Helper method** (`src/repl_environment/environment.py`, ~15 lines)

Add `_maybe_wrap_tool_output(self, output: str) -> str` to the base `REPLEnvironment` class:

```python
def _maybe_wrap_tool_output(self, output: str) -> str:
    """Conditionally wrap tool output based on deferred mode setting.

    Legacy mode: append to _tool_outputs artifact + return with delimiters.
    Deferred mode: return raw output (no delimiters, no artifact append).
    """
    if self._deferred_tool_results:
        return output
    self.artifacts.setdefault("_tool_outputs", []).append(output)
    return wrap_tool_output(output)
```

Also cache `self._builtin_global_keys = frozenset(self._globals.keys())` in `__init__` after `_build_globals()` — needed for Step 6 to identify user-defined variables.

**Step 3: Replace 14 mixin call sites** (3 files)

Each site currently has a 2-line pattern:

```python
self.artifacts.setdefault("_tool_outputs", []).append(output)
return wrap_tool_output(output)
```

Replace with:

```python
return self._maybe_wrap_tool_output(output)
```

**Exact call sites (verified 2026-02-18):**

| File | Lines | Method/Context |
|---|---|---|
| `src/repl_environment/routing.py` | 102-103 | `_recall()` success path |
| `src/repl_environment/routing.py` | 109-110 | `_recall()` error path |
| `src/repl_environment/routing.py` | 167-168 | `_route_advice()` success path |
| `src/repl_environment/routing.py` | 174-175 | `_route_advice()` error path |
| `src/repl_environment/routing.py` | 255-256 | `_my_role()` |
| `src/repl_environment/routing.py` | 280-281 | `_list_findings()` |
| `src/repl_environment/routing.py` | 348-349 | `_mark_finding()` success path |
| `src/repl_environment/routing.py` | 361-362 | `_mark_finding()` error/duplicate path |
| `src/repl_environment/routing.py` | 418-419 | `_fetch_report()` |
| `src/repl_environment/code_search.py` | 138-139 | `_code_search()` success path |
| `src/repl_environment/code_search.py` | 146-147 | `_code_search()` error/empty path |
| `src/repl_environment/code_search.py` | 194-195 | `_doc_search()` success path |
| `src/repl_environment/code_search.py` | 200-201 | `_doc_search()` error/empty path |
| `src/repl_environment/file_exploration.py` | 235-236 | `_list_dir()` |

**Step 4: Deferred-aware silent execution nudge** (`src/graph/helpers.py:1019-1026`, ~10 lines)

The existing silent execution nudge (line 1019) fires when code produces no output, no error, and no FINAL(). In deferred mode, this will fire more often because tool results no longer appear in stdout. Modify the nudge:

- When deferred mode + tool invocations > 0 + no stdout: nudge with "N tool(s) called, results stored as variables. Use print() to record key findings."
- Check both `_tool_invocations` (Path B counter) and `_exploration_calls` (Path A counter, if available) or inspect `artifacts.get("_tool_outputs", [])` length (which will be 0 in deferred mode — use invocation log instead).

**Step 5: `_tools_success()` invocation log fallback** (`src/api/routes/chat_pipeline/repl_executor.py:52-65`, ~15 lines)

Current `_tools_success()` returns `None` when `tool_outputs` is empty. In deferred mode, `_tool_outputs` is always empty, so `_tools_success` always returns `None` — losing the telemetry signal.

Fix: when `_tool_outputs` is empty but `tool_invocations > 0`, fall back to `tool_registry.invocation_log` to check if any tools succeeded. Add optional `invocation_log` parameter. Update call site at line 376 to pass invocation log.

**Step 6: User-defined globals in `get_state()`** (`src/repl_environment/state.py`, ~20 lines)

When deferred mode is active, the model needs to know what variables survived from previous turns. Diff `self._globals.keys()` against `self._builtin_global_keys` (cached in Step 2). Append "## Available Variables (from previous turns)" section with type + truncated preview for each user-defined var. Cap at 20 entries, truncate previews at 80 chars.

Also suppress `artifacts['_tool_outputs']` preview in deferred mode so state rendering does not re-introduce tool payload into the next prompt.

**Step 7: Prompt builder awareness** (`src/prompt_builders/builder.py`, ~5 lines)

When deferred mode active, append to context_parts: "Tool results stay in code variables only. Use print() to record findings."

**Step 8: Tests** (`tests/unit/test_repl_deferred_tools.py` — NEW, ~200 lines)

- Test `_maybe_wrap_tool_output` in deferred vs legacy modes
- Test that mixin tools return clean output (no delimiters) in deferred mode
- Test `_tools_success()` invocation log fallback
- Test deferred nudge triggers correctly when tools called but no stdout
- Test `get_state()` lists user-defined variables
- Test end-to-end: deferred turn with tools produces clean `last_output`

#### 5.1.3.1 What Does NOT Need Changing (and Why)

| Component | File | Why No Change |
|---|---|---|
| `_invoke_tool()` / `_call_tool()` | `context.py` | Path B never used `_tool_outputs` or `wrap_tool_output` — already deferred |
| `_escalate()` | `routing.py:178-195` | Uses separate artifact keys (`_escalation_requested`, `_escalation_target`, `_escalation_reason`), no `_tool_outputs` |
| `_delegate()` | `routing.py` | Uses `_delegations` artifact, no `_tool_outputs` |
| `_strip_tool_outputs()` | `chat_utils.py:118` | Empty `_tool_outputs` = nothing to strip — correct behavior |
| `_resolve_answer()` | `chat_utils.py:181` | Empty `tool_outputs` = skips stripping — correct |
| `_resolve_answer()` | `helpers.py:1314` | Returns `output.strip()` when output exists; tool_outputs fallback only fires when output is empty — low risk |
| `_spill_output()` | `environment.py` | Less likely to trigger (smaller stdout in deferred mode), still works correctly when it does |
| `_execute_structured()` | `environment.py` | Deferred mode is orthogonal to structured/standard mode |
| Graph node `is_final` branches | `nodes.py` (7 nodes) | Pass empty `_tool_outputs` to `_resolve_answer` — works correctly |
| `_peek()` / `_grep()` | `environment.py` | Don't use `wrap_tool_output` or `_tool_outputs` — already deferred |
| Checkpoint/restore | `procedure_tools.py` | Smaller artifacts (positive). Globals reset is a Phase 3 concern |
| Workspace state | `state.py` | Receives cleaner output, no functional change |
| Parallel dispatch | `parallel_dispatch.py` | Dispatches mixin tools via method call — those methods will use `_maybe_wrap_tool_output` automatically |

#### 5.1.3.2 Edge Cases

1. **`my_role()` in deferred mode**: Returns clean JSON (no delimiters). Model can parse it in the current turn. If needed next turn, must `print()` relevant parts. Correct — role info is typically used immediately.

2. **`escalate()` / `delegate()` in deferred mode**: These use separate artifact keys (`_escalation_requested`, `_escalation_target`, `_escalation_reason`, `_delegations`). Deferred mode does NOT affect them. No change needed.

3. **`print(TOOL("search"))` explicitly**: Path B tool returns raw result. `print()` puts it in stdout → captured → enters context. Correct — model explicitly opted in.

4. **`print(my_role())` in deferred mode**: Path A tool returns clean JSON (no delimiters). Gets printed to stdout → captured → enters context. Correct — model opted in.

5. **Parallel dispatch in deferred mode**: `_extract_parallel_calls()` dispatches read-only mixin tools. Results injected into `_globals`. The combined observation (formatted for stdout) may be large. Consider truncating observation to compact form when deferred mode active.

6. **First turn (no last_output yet)**: No issue — `state.last_output` starts empty, `get_state()` has no user vars yet. Clean start.

7. **Feature flag change mid-session**: Flag read once during `REPLEnvironment.__init__()`. Frozen for task duration. No mid-task inconsistency.

8. **`_resolve_answer()` fallback path** (helpers.py ~line 1320): When `output` is empty and `tool_outputs` is non-empty, it joins tool outputs as the answer. In deferred mode, `_tool_outputs` is empty, so this fallback produces `""`. Acceptable — if the model didn't `print()` or `FINAL()`, there's no answer. The rescue heuristics in nodes.py handle this separately.

9. **Checkpoint/restore resets user globals**: `restore()` calls `_build_globals()` which rebuilds fresh. User-defined variables lost. Document as known limitation for Phase 1. Phase 3 addresses this by extending `checkpoint()` to serialize user globals and `restore()` to merge them after `_build_globals()`.

#### 5.1.4 Files to Modify

| File | Change | Lines |
|---|---|---|
| `src/features.py` | Add `deferred_tool_results` flag + env var + summary | ~15 |
| `src/repl_environment/environment.py` | Add `_maybe_wrap_tool_output()` method, cache `_builtin_global_keys` | ~15 |
| `src/repl_environment/routing.py` | Replace 9 call sites with `_maybe_wrap_tool_output()` | ~-9 |
| `src/repl_environment/code_search.py` | Replace 4 call sites with `_maybe_wrap_tool_output()` | ~-4 |
| `src/repl_environment/file_exploration.py` | Replace 1 call site with `_maybe_wrap_tool_output()` | ~-1 |
| `src/graph/helpers.py` | Deferred-aware silent execution nudge | ~10 |
| `src/api/routes/chat_pipeline/repl_executor.py` | `_tools_success()` invocation log fallback | ~15 |
| `src/repl_environment/state.py` | User-defined globals in `get_state()` | ~20 |
| `src/prompt_builders/builder.py` | Deferred mode prompt hint | ~5 |
| `tests/unit/test_repl_deferred_tools.py` | NEW: unit tests for deferred mode | ~200 |

#### 5.1.5 Expected Impact

| Metric | Estimate | Reasoning |
|---|---|---|
| **Tokens per multi-tool task** | 2-8x reduction | Tool results are mostly removed from prompt flow; residual state previews must also be filtered |
| **Frontdoor context pressure** | 30-60% reduction | 30B model has ~32K context; removing tool results frees significant budget |
| **Latency per turn** | ~5% reduction | Smaller prompts = faster prefill |
| **Accuracy** | Neutral to +5% | Model forced to summarize findings explicitly; less noise in context |

#### 5.1.6 Migration Strategy

1. Ship behind feature flag (default OFF)
2. A/B test: run seeding eval with deferred=ON vs OFF
3. If neutral or positive on quality → flip default to ON
4. Update system prompts to tell model: "Print your key findings. Tool results are not carried forward automatically."

#### 5.1.7 Prompt Builder Changes

The system prompt for REPL mode should inform the model about deferred behavior:

```
# When deferred_tool_results=True, add to system prompt:
"IMPORTANT: Tool results are available ONLY within the current turn's code.
They are NOT carried forward to the next turn automatically.
Use print() to record any information you need for your final answer.
Example:
  data = TOOL("search", query="X")
  print(f"Found {len(data)} results. Top match: {data[0]['title']}")
  # ↑ This print output WILL be visible in the next turn.
  # ↑ The raw `data` variable WILL NOT be visible.
"
```

#### 5.1.8 Phase 1 Completion Checklist

- [ ] Feature flag `ORCHESTRATOR_DEFERRED_TOOL_RESULTS` added to `src/features.py`
- [ ] **P0 prerequisite**: fix `_increment_exploration()` recursion deadlock in `src/repl_environment/file_exploration.py`
- [ ] `_maybe_wrap_tool_output()` helper added to `src/repl_environment/environment.py`
- [ ] `_builtin_global_keys` cached in `REPLEnvironment.__init__()` after `_build_globals()`
- [ ] 14 mixin call sites replaced across `routing.py` (9), `code_search.py` (4), `file_exploration.py` (1)
- [ ] Deferred-aware silent execution nudge in `src/graph/helpers.py`
- [ ] `_tools_success()` invocation log fallback in `repl_executor.py`
- [ ] User-defined globals listed in `get_state()` in `state.py`
- [ ] `get_state()` excludes `_tool_outputs` artifact preview in deferred mode
- [ ] System prompt updated for deferred mode in prompt builder
- [ ] Unit tests: deferred on/off, print capture, nudge trigger, variable listing (`tests/unit/test_repl_deferred_tools.py`)
- [ ] A/B evaluation completed via seeding eval
- [ ] No regression beyond threshold on any suite
- [ ] ClaudeDebugger: deferred mode attribution integrated (tool results not in context)
- [ ] **Logging**: `agent_audit.log` updated with Phase 1 session entries
- [ ] **Progress report**: `progress/YYYY-MM/YYYY-MM-DD.md` entry written with A/B results and decision
- [ ] **Handoff update**: This file updated — Phase 1 status changed to COMPLETE, A/B metrics recorded in Section 15
- [ ] **Documentation**: `docs/chapters/29-programmatic-tool-chaining.md` drafted with Phase 1 content (concept, deferred mode config, prompt changes)
- [ ] **CHANGELOG.md**: Entry added under today's date
- [ ] **CLAUDE.md Component Flow**: Updated if default flipped to ON (add `deferred_tool_results` note)
- [ ] **handoffs/active/rlm-orchestrator-roadmap.md**: Cross-linked as Phase 9 or standalone track entry

---

### Phase 2: Multi-Mutation Tool Chaining (MEDIUM effort, HIGH impact)

> **CRITICAL CORRECTION (2026-02-18):** Deep code exploration revealed several
> inaccuracies in the original Phase 2 plan. The restriction being lifted is
> **structured mode only** (standard mode already allows unlimited chaining).
> Three disconnected read-only classification systems exist and must be unified
> before `allowed_callers` can work. Tool detection uses **regex, not AST**.
> This revised plan corrects the architecture and adds missing infrastructure
> steps.

**Phase 1 is a hard prerequisite.** Phase 2 chain results follow deferred mode
(stay in globals, not in `_tool_outputs`). Without Phase 1, chained tool results
would pollute context N times per chain instead of once per turn — making
chaining actively harmful.

#### 5.2.1 Concept

Lift the "single non-read-only tool per turn" restriction **in structured mode
(React)** for tools that opt in via `allowed_callers`. Standard mode already
allows unlimited tool chaining — any number of tools chain freely via sequential
`exec()`. Phase 2 targets only the structured mode gate at
`environment.py:650-670`.

**What this is NOT**: A universal removal of tool-per-turn limits. It is a
conditional relaxation of the structured mode restriction for opted-in tools,
with dependency analysis determining safe execution order.

**Analogy to Anthropic**: This is equivalent to Anthropic's pattern where
"Claude writes code that calls your tool as a function, potentially including
multiple tool calls and pre/post-processing logic."

#### 5.2.2 Architecture Change

**Two execution modes exist — only structured mode needs modification:**

```
Standard mode (no change needed):
    Code block with multiple tools → sequential exec(code, globals) → all tools execute
    Already supports unlimited chaining. No restriction to remove.

Structured mode BEFORE (current — environment.py:639-670):
    Step 1: Regex-based detection (line 641-648)
        for func in tool_functions:
            pattern = rf"\b{func}\s*\("        # Regex, NOT AST
            matches = list(re.finditer(pattern, code))
    Step 2: Hardcoded read-only gate (line 653-658)
        read_only_tools = {"peek", "grep", "list_dir", ...}   # Hardcoded set #1
        all_read_only = all(name in read_only_tools for name in tool_names)
    Step 3: Reject if any non-read-only (line 662-670)
        if not all_read_only:
            return ExecutionResult(error="Structured mode: Only one tool call per turn...")
    Step 4: If all read-only → AST parallel dispatch (line 672-698)
        parallel_calls = _extract_parallel_calls(code, globals, read_only_tools)

Structured mode AFTER (Phase 2):
    Step 1: AST-based detection (replaces regex — unify with parallel_dispatch.py)
        tree = ast.parse(code)
        tool_calls = _extract_tool_calls(tree, tool_functions)  # AST, not regex
    Step 2: Registry-based classification (replaces hardcoded set)
        chainable = tool_registry.get_chainable_tools()  # Uses Tool.allowed_callers
        read_only = tool_registry.get_read_only_tools()  # Uses SideEffect.READ_ONLY
    Step 3: Dispatch based on tool mix (replaces binary reject)
        if all read-only → parallel dispatch (existing path, no change)
        if all chainable → Phase 2a: sequential exec() / Phase 2b: dependency-analyzed
        if any non-chainable → reject with specific message
    Step 4: Chain result tracking (new)
        Each tool call logged with chain_id, chain_index, caller_type
```

**Note on observation format**: In structured mode, results are currently formatted
as `"Observation:\n" + "\n---\n".join(parts)` (environment.py:691-692). For
multi-tool chains, each tool gets a labeled section:

```
Observation:
[step 1: file_write_safe] → success (23ms)
---
[step 2: run_shell] → "Build succeeded" (142ms)
---
[step 3: gate_run] → 4/4 gates passed (891ms)
```

Cap total observation size via `_spill_output()` (existing mechanism).

#### 5.2.3 Infrastructure Prerequisite: Unify Read-Only Classification

**Three parallel read-only classification systems exist — none wired together:**

| System | Location | Status |
|--------|----------|--------|
| `SideEffect.READ_ONLY` enum | `tool_registry.py:62` | Defined, never populated on tools |
| `get_read_only_tools()` method | `tool_registry.py:558-568` | Returns **empty set** (no tools declare `READ_ONLY`) |
| Hardcoded `read_only_tools` set #1 | `environment.py:653-658` | Actually used for structured mode dispatch |
| Hardcoded `read_only_tools` set #2 | `repl_executor.py:398-401` | Used for `parallel_tools_used` telemetry |

**Sets #1 and #2 are not identical** — environment.py includes `find_scripts`,
`list_procedures`, `get_procedure_status` which repl_executor.py omits.

**Phase 2a prerequisite**: Wire `SideEffect.READ_ONLY` to replace both hardcoded
sets. Steps:

1. Populate `side_effects: [SideEffect.READ_ONLY]` on tool registration for all
   tools currently in the hardcoded sets (during `_register_builtin_tools()` and
   YAML loading)
2. Replace hardcoded set in `environment.py:653-658` with
   `self._tool_registry.get_read_only_tools()` (or cache at init)
3. Replace hardcoded set in `repl_executor.py:398-401` with
   `repl.tool_registry.get_read_only_tools()`
4. Verify `get_read_only_tools()` returns the union of both previous sets

#### 5.2.4 Tool Detection: Regex → AST Unification

**Current state**: Two detection methods in the same code path:

| Stage | Method | Location |
|-------|--------|----------|
| Tool call counting | **Regex** (`rf"\b{func}\s*\("`) | `environment.py:641-648` |
| Parallel dispatch extraction | **AST** (`ast.parse` + walk) | `parallel_dispatch.py:96-190` |

The regex stage runs first and can reject code before AST analysis runs. This
creates fragility: regex can false-positive on commented-out calls, string
literals containing function names, or nested scope definitions.

**Phase 2 should unify**: Replace the regex detection at environment.py:641-648
with AST-based extraction. Use `_extract_tool_calls()` (new function in
parallel_dispatch.py) for both detection AND dependency analysis. The existing
`_extract_parallel_calls()` already does correct AST analysis — generalize it to
handle non-read-only tools.

```python
# New in parallel_dispatch.py
def _extract_tool_calls(tree: ast.Module, tool_functions: set[str]) -> list[_ToolCall]:
    """Extract all tool call sites from AST. Used for detection AND analysis.

    Unlike the regex approach, this correctly handles:
    - Commented-out calls (not in AST)
    - Function names in strings (not Call nodes)
    - Nested function definitions (only walks top-level)
    """
    calls = []
    for i, stmt in enumerate(tree.body):
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            call_node = stmt.value
            target_var = stmt.targets[0].id if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) else None
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call_node = stmt.value
            target_var = None
        else:
            continue
        if isinstance(call_node.func, ast.Name) and call_node.func.id in tool_functions:
            calls.append(_ToolCall(call_node.func.id, target_var, i))
    return calls
```

#### 5.2.5 Execution Modes

```python
# src/repl_environment/types.py (or environment.py)
class ToolChainMode(Enum):
    LEGACY = "legacy"              # Current: one write-tool per turn in structured mode
    SEQUENTIAL_CHAIN = "seq"       # Phase 2a: multiple write-tools, sequential exec()
    DEPENDENCY_AWARE = "dep"       # Phase 2b: dependency-analyzed, parallel where safe
```

**Phase 2a (simpler — do this first)**:

1. Wire `SideEffect.READ_ONLY` to replace hardcoded sets (prerequisite above)
2. In `_execute_structured()`, replace the `if not all_read_only` rejection:
   - Check each non-read-only tool against `Tool.allowed_callers`
   - If all tools are chainable (have `"chain"` in `allowed_callers`) → allow
   - Execute via sequential `exec(code, globals)` — the simplest correct path
   - No dependency analysis needed — `exec()` already runs sequentially

3. **This is the critical insight**: `exec(code, globals)` already executes
   statements sequentially. Phase 2a doesn't need a new execution engine — it
   just needs to NOT reject the code. The sequential execution guarantee comes
   from Python's `exec()`.

**Phase 2b (full — build on 2a)**:

1. Extend `_extract_parallel_calls()` to handle non-read-only tools with
   dependency edges
2. Independent write-tools → parallel dispatch (ThreadPoolExecutor)
3. Dependent write-tools → sequential within dependency chain
4. Mixed read/write → read-only tools parallel, writes sequential

#### 5.2.6 `allowed_callers` Design

Add a new field to the `Tool` dataclass:

```python
# src/tool_registry.py
@dataclass
class Tool:
    ...
    allowed_callers: list[str] = field(default_factory=lambda: ["direct"])
    # Values:
    #   "direct"       - Standard REPL invocation (one-per-turn if structured)
    #   "chain"        - Can participate in multi-tool chains (structured mode)
    #   "programmatic" - Full programmatic calling (Phase 3)
```

**How `_execute_structured()` consults `allowed_callers`**:

```python
# In environment.py _execute_structured(), replacing lines 662-670:
tool_names = [t[0] for t in tool_calls]
read_only = self._read_only_tools  # Cached from registry at init
non_read_only = [n for n in tool_names if n not in read_only]

if not non_read_only:
    # All read-only → existing parallel dispatch path (unchanged)
    ...
elif self._chain_mode != ToolChainMode.LEGACY:
    # Phase 2: check if all non-read-only tools opt in to chaining
    for tool_name in non_read_only:
        tool = self._tool_registry.get_tool(tool_name)
        if tool and "chain" not in tool.allowed_callers:
            return ExecutionResult(error=f"Tool '{tool_name}' does not allow chaining. "
                                        f"Use allowed_callers=['chain'] to opt in.")
        if tool_name in {"escalate", "delegate"}:
            return ExecutionResult(error=f"Routing tools ({tool_name}) cannot be chained. "
                                        f"Call routing tools individually.")
    # All opted in → execute (Phase 2a: sequential, Phase 2b: dependency-aware)
    ...
else:
    # Legacy: reject
    return ExecutionResult(error="Structured mode: Only one tool call per turn...")
```

**Relationship to `SideEffect.READ_ONLY`**: These are orthogonal dimensions:
- `SideEffect.READ_ONLY` → "this tool has no side effects" (used for safe parallelism)
- `allowed_callers: ["chain"]` → "this tool opts in to multi-tool turns" (used for structured mode gate)
- A tool can be `READ_ONLY` without `allowed_callers: ["chain"]` (e.g., an expensive read tool you want to limit)
- A tool can have `allowed_callers: ["chain"]` without `READ_ONLY` (e.g., `file_write_safe` — writes, but safe to chain)

**Initial categorization:**

```python
# Read-only + chainable (safe for both parallel dispatch and chaining):
peek, grep, list_dir, file_info, list_tools, recall, list_findings,
registry_lookup, my_role, route_advice, list_procedures,
get_procedure_status, context_len, find_scripts, benchmark_compare,
code_search, doc_search
# → side_effects: [SideEffect.READ_ONLY], allowed_callers: ["direct", "chain"]

# Write + chainable (safe for sequential chaining, not parallel):
file_write_safe, log_append
# → allowed_callers: ["direct", "chain"]

# Write + opt-in only (unsafe for automatic chaining):
run_shell, run_python_code, checkpoint_create, checkpoint_restore
# → allowed_callers: ["direct"]

# Never chainable (routing must be deliberate, one-per-turn):
escalate, delegate
# → allowed_callers: ["direct"]

# LLM-calling (resource implications for chaining):
llm_call, llm_batch
# → allowed_callers: ["direct"]  (consider ["direct", "chain"] later)
```

#### 5.2.7 `caller` Field for Audit Trail

Add caller provenance to `ToolInvocation`:

```python
# src/tool_registry.py
@dataclass
class ToolInvocation:
    tool_name: str
    args: dict[str, Any]
    role: str
    success: bool
    result: Any
    error: str | None = None
    elapsed_ms: float = 0.0
    # NEW Phase 2 fields:
    caller_type: str = "direct"     # "direct", "chain", "programmatic"
    chain_id: str | None = None     # Groups calls from same code block
    chain_index: int = 0            # Order within chain
```

#### 5.2.8 Error Handling Architecture

**Current reality**: `exec(code, globals)` treats the entire code block as atomic.
If any tool call raises an exception, `exec()` aborts entirely — remaining
statements never execute. There is no per-tool error boundary.

**Phase 2a (sequential chains via exec())**:

The simplest approach: let `exec()` handle errors naturally. If tool #2 fails,
Python raises an exception, `exec()` aborts, and the REPL captures the traceback.
The model sees the error and can retry in the next turn. This matches current
behavior for standard mode.

**Phase 2b (dependency-aware with ChainResult)**:

For parallel dispatch of independent tools, errors need per-tool handling:

```python
@dataclass
class ChainResult:
    """Result of a chained tool execution."""
    steps: list[ChainStep]  # Each: tool_name, args, result_or_error, success, elapsed_ms
    aborted_at: int | None  # Step index where chain aborted, or None
    total_elapsed_ms: float

@dataclass
class ChainStep:
    tool_name: str
    args: dict[str, Any]
    result: Any | None
    error: str | None
    success: bool
    elapsed_ms: float
```

This requires wrapping **individual tool calls** (not relying on exec()):

```python
# In parallel dispatch, each tool call wrapped:
try:
    result = handler(**kwargs)
    step = ChainStep(tool_name, kwargs, result=result, error=None, success=True, elapsed_ms=...)
except Exception as e:
    step = ChainStep(tool_name, kwargs, result=None, error=str(e), success=False, elapsed_ms=...)
    if abort_on_error:
        break
```

**Phase 2a does NOT need ChainResult** — exec() provides natural error semantics.
Phase 2b introduces it only for the parallel dispatch path.

#### 5.2.9 What Does NOT Need Changing

| Component | File | Why No Change |
|---|---|---|
| Standard mode execution | `environment.py` | Already supports unlimited tool chaining via `exec()` |
| Path B registry tools (TOOL/CALL) | `context.py` | Already chain freely in both modes |
| Escalation/delegation routing | `routing.py` | Must remain one-per-turn, deliberate decisions |
| Graph node error handling | `nodes.py` | Operates on turn-level, not tool-level |
| `_invoke_tool()` / `_call_tool()` | `context.py` | Path B — no structured mode restriction applies |
| Checkpoint/restore | `procedure_tools.py` | Turn-level operation, not affected by chaining |
| Workspace state updates | `helpers.py:121-162` | Updates per-turn, not per-tool — correct for chains |
| Artifacts accumulation | `nodes.py:86` | Cross-turn accumulation, not per-tool — no rollback needed |

**On rollback**: The original plan proposed chain rollback for file-writing tools.
This is infeasible without new infrastructure — `workspace_state` updates
per-turn (not per-tool), `artifacts` accumulate across turns (never reverted),
and no checkpoint/snapshot exists before tool execution. Defer rollback to a
future phase. Phase 2's safety model relies on `allowed_callers` opt-in and
abort-on-error, not rollback.

#### 5.2.10 Edge Cases

1. **Chain containing `escalate()`/`delegate()`**: Must reject at gate. These are
   routing decisions that require deliberate model intent, not side effects of a
   chain. Check explicitly in `_execute_structured()` gate logic.

2. **Chain with `FINAL()` mid-chain**: `FINAL()` raises `FinalSignal` exception.
   `exec()` aborts immediately, remaining tools skipped. This is correct — the
   model explicitly signaled completion. No special handling needed.

3. **Chain with `llm_call()`**: Nested inference within a chain. Resource
   implications: each `llm_call()` holds the inference lock. In Phase 2a
   (sequential), this works but serializes. In Phase 2b (parallel), `llm_call()`
   must NOT be parallelized (inference lock contention). Default: exclude
   `llm_call` from `allowed_callers: ["chain"]`.

4. **MCP tools in chains**: Network latency per call (50-500ms). Chaining MCP
   tools is technically possible but latency characteristics differ from local
   tools. Follow Anthropic's precedent: exclude MCP-backed tools from chaining
   initially. Add later with explicit opt-in per MCP server config.

5. **Deferred mode interaction**: Chain results follow deferred rules (Phase 1).
   In deferred mode: tool results stay in globals, only `print()` output enters
   context. In legacy mode: chain results accumulate in `_tool_outputs` (N
   entries per chain). Deferred mode is strongly recommended for chains.

6. **Chain errors in structured vs standard mode**: In standard mode, `exec()`
   aborts on any exception (current behavior). In structured mode Phase 2a,
   identical behavior. In structured mode Phase 2b (parallel), `ChainResult`
   provides per-step error reporting.

7. **Parallel dispatch of mixed read/write chains**: Phase 2b only. Read-only
   tools can run in parallel. Write tools run sequentially. A chain like
   `[read, read, write, read]` → parallel(read, read), then write, then read.
   Dependency analysis determines which reads can precede the write.

8. **Regex false positives**: Current regex detection (`rf"\b{func}\s*\("`)
   matches function names in comments and strings. Example:
   `comment = "don't call escalate() here"` triggers false positive. AST
   unification (Section 5.2.4) eliminates this class of bugs.

#### 5.2.11 Files to Modify

| File | Change | Lines |
|---|---|---|
| `src/features.py` | Add `ORCHESTRATOR_TOOL_CHAIN_MODE` env flag | +5 |
| `src/tool_registry.py` | Add `allowed_callers` to `Tool`; populate `SideEffect.READ_ONLY` on registration; add `get_chainable_tools()`; add `caller_type/chain_id/chain_index` to `ToolInvocation` | ~40 |
| `orchestration/tool_registry.yaml` | Add `allowed_callers` field to tool definitions (759-line file) | ~50 |
| `src/repl_environment/types.py` | Add `ToolChainMode` enum, config field | +15 |
| `src/repl_environment/environment.py` | Replace hardcoded `read_only_tools` set (line 653-658) with registry lookup; replace regex detection (line 641-648) with AST; modify structured mode gate (line 662-670) to consult `allowed_callers` | ~60 |
| `src/repl_environment/parallel_dispatch.py` | Add `_extract_tool_calls()` for unified AST detection; extend `_extract_parallel_calls()` or add `analyze_tool_dependencies()` for Phase 2b | ~120 |
| `src/api/routes/chat_pipeline/repl_executor.py` | Replace hardcoded `read_only` set (line 398-401) with registry lookup; wire chain mode config; add `tool_chains` to ChatResponse | ~25 |
| `src/api/models/responses.py` | Add `tool_chains: list[dict]` field to ChatResponse | +5 |
| `tests/unit/test_tool_chaining.py` | NEW: unit tests for chained execution, gate logic, error semantics | ~200 |
| `tests/unit/test_tool_dependencies.py` | NEW: unit tests for AST detection, dependency analysis | ~150 |
| `tests/unit/test_allowed_callers.py` | NEW: per-tool caller restriction tests | ~100 |
| `tests/unit/test_chain_audit.py` | NEW: invocation enrichment, chain_id grouping | ~100 |

#### 5.2.12 Expected Impact

| Metric | Estimate | Reasoning |
|---|---|---|
| **Turns per multi-tool task (structured-mode workloads)** | 2-5x reduction | 5 tools = 5 turns → 1 turn in structured mode; standard REPL mode already chains |
| **Latency (structured-mode workloads)** | 2-4x faster | No re-sampling between tools in structured mode |
| **Escalation rate** | 10-20% reduction | Frontdoor handles more complex tasks without needing heavier models |
| **Token consumption** | 2-3x reduction | No re-prompting between tool calls |

#### 5.2.13 Phase 2 Completion Checklist

- [ ] **Prerequisite**: `SideEffect.READ_ONLY` populated on all read-only tools during registration
- [ ] **Prerequisite**: Hardcoded `read_only_tools` in `environment.py:653-658` replaced with `tool_registry.get_read_only_tools()`
- [ ] **Prerequisite**: Hardcoded `read_only` in `repl_executor.py:398-401` replaced with registry lookup
- [ ] **Prerequisite**: Phase 1 (deferred tool results) shipped and default ON
- [ ] `Tool.allowed_callers` field added to `src/tool_registry.py`
- [ ] `allowed_callers` field added to `orchestration/tool_registry.yaml` schema and populated
- [ ] `get_chainable_tools()` method added to `ToolRegistry`
- [ ] `ToolInvocation.caller_type/chain_id/chain_index` fields added
- [ ] `ToolChainMode` enum and config field added
- [ ] Regex detection (environment.py:641-648) replaced with AST via `_extract_tool_calls()`
- [ ] Structured mode gate (environment.py:662-670) modified to consult `allowed_callers`
- [ ] Phase 2a: Sequential chain execution via `exec()` (just remove rejection)
- [ ] Phase 2b: AST dependency analysis in `parallel_dispatch.py`
- [ ] Phase 2b: Parallel chain dispatch for independent mutations
- [ ] Observation format defined for multi-tool chains (labeled sections)
- [ ] Chain abort-on-error semantics implemented (Phase 2a: exec() natural; Phase 2b: ChainResult)
- [ ] `tool_chains` summary field added to `ChatResponse`
- [ ] Per-tool opt-in via `allowed_callers` — initial categorization applied
- [ ] Unit tests: all chain scenarios (`tests/unit/test_tool_chaining.py`)
- [ ] Unit tests: AST detection + dependency analysis (`tests/unit/test_tool_dependencies.py`)
- [ ] Unit tests: allowed_callers per-tool restrictions (`tests/unit/test_allowed_callers.py`)
- [ ] Unit tests: chain audit trail, chain_id grouping (`tests/unit/test_chain_audit.py`)
- [ ] A/B evaluation completed on coding suite (multi-tool tasks)
- [ ] No quality regression beyond threshold
- [ ] ClaudeDebugger chain rendering integrated (grouped chain view in replay)
- [ ] **Logging**: `agent_audit.log` updated with Phase 2 session entries; chain execution events logged
- [ ] **Progress report**: `progress/YYYY-MM/YYYY-MM-DD.md` entry written with chain metrics and eval results
- [ ] **Handoff update**: This file updated — Phase 2 status changed to COMPLETE, metrics recorded in Section 15
- [ ] **Documentation**: `docs/chapters/29-programmatic-tool-chaining.md` updated with chaining patterns, allowed_callers config, dependency analysis explanation
- [ ] **Reference doc**: `docs/reference/tool-chaining-patterns.md` created with quick-reference examples
- [ ] **CHANGELOG.md**: Entry added under today's date
- [ ] **CLAUDE.md Component Flow**: Updated to include `ToolRegistry(chain_mode, allowed_callers)` and chaining dispatch line
- [ ] **orchestration/model_registry.yaml**: Add `tool_chain_mode` per-role config if applicable
- [ ] **handoffs/active/rlm-orchestrator-roadmap.md**: Phase 2 completion noted

---

### Phase 3: Persistent Execution Context (HIGH effort, MEDIUM-HIGH impact)

> **CRITICAL CORRECTION (2026-02-18):** Deep code exploration revealed the core
> premise of the original Phase 3 plan was **wrong**. Globals already persist
> within a task — `_globals` is built once in `__init__()` and reused across all
> `execute()` calls via `exec(code, self._globals)`. Phase 3 is NOT about
> within-task persistence. It is about **cross-request persistence** — surviving
> across separate API calls where new `REPLEnvironment` instances are created.
> Additionally, substantial session infrastructure already exists and was ignored.
> This revised plan corrects the architecture, removes the proposed
> `session_manager.py`, and extends existing infrastructure instead.

**Phase 1 is a hard prerequisite.** Phase 3 uses `_builtin_global_keys` (Phase 1
Step 2) to identify user-defined variables for serialization filtering. Phase 1's
deferred mode also increases the value of persistence — more variables accumulate
in globals when tool results stay as variables instead of flowing to stdout.

**Phase 2 is a soft prerequisite.** Phase 2's `ToolInvocation.caller_type` and
`chain_id` enable variable lineage attribution (which role/chain created each
variable). Without Phase 2, lineage tracks turn number only.

#### 5.3.1 Concept

> **RLM Integration Note**: The upstream RLM repo provides a `SupportsPersistence`
> protocol with versioned `add_context(payload, index)` / `add_history(messages, index)`.
> Phase 3's checkpoint/restore should align with this interface. RLM's `_compact_history()`
> (auto-summarize at context limit) addresses a gap not covered here — adopt as companion
> feature. See `handoffs/active/rlm-orchestrator-roadmap.md` Delta D4.

Phase 3 enables **cross-request persistence** — globals survive across separate
API calls. This is equivalent to Anthropic's container reuse via the `container`
field.

**Within a task, globals already persist.** One `REPLEnvironment` is created per
task (`repl_executor.py:144-154`), shared across all graph nodes via
`TaskDeps.repl`. `_globals` is built once in `__init__()` (`environment.py:174`)
and reused across all `execute()` calls. Variables set in
`exec(code, self._globals)` mutate the dict in-place and persist across all turns
and escalation nodes (FrontdoorNode → CoderEscalationNode share the same REPL).

**Across requests, globals are lost.** Each API call creates a new
`REPLEnvironment` → `_build_globals()` → fresh dict → user variables gone. Phase
3 adds:

1. **Checkpoint includes globals**: `checkpoint()` serializes user-defined
   variables alongside existing artifacts
2. **Cross-request restore**: `restore()` merges saved globals after
   `_build_globals()`, making variables from previous requests available
3. **Session resume wiring**: `ResumeContext.format_for_injection()` includes
   variable summary with "(from previous request)" annotations

##### 5.3.1.1 Post-Phase-1/2 Assumptions

| Dependency | Source | What Phase 3 Uses |
|---|---|---|
| `_builtin_global_keys` | Phase 1, Step 2 | Filter user vars from builtins during serialization |
| Deferred mode | Phase 1 | More variables in globals → persistence higher value |
| `get_state()` user vars | Phase 1, Step 6 | Foundation for cross-request annotations (add "from previous request") |
| `ToolInvocation.caller_type` | Phase 2 | Variable lineage: which role created each var |
| `ToolInvocation.chain_id` | Phase 2 | Variable lineage: which chain produced each var |
| `Tool.allowed_callers` | Phase 2 | Audit trail enriches restore context |

#### 5.3.2 Architecture Change

```
WITHIN A TASK (already works — NO CHANGE):
    Turn 1: exec(code, self._globals)  → results stored in _globals dict
    Turn 2: exec(code, self._globals)  → SAME dict, previous results available
    Escalation: CoderEscalationNode uses same deps.repl → same _globals

CROSS-REQUEST BEFORE (current):
    Request 1: REPLEnvironment() → _build_globals() → exec() → user vars in _globals
    Request 1 ends → REPLEnvironment garbage collected → _globals lost
    Request 2: REPLEnvironment() → _build_globals() → fresh dict → user vars GONE
               → Previous results only available via session findings (text summaries)

CROSS-REQUEST AFTER (Phase 3):
    Request 1: REPLEnvironment() → _build_globals() → exec() → user vars in _globals
    Request 1 ends → checkpoint() serializes user_globals to session checkpoint
    Request 2: REPLEnvironment() → _build_globals() → restore saved globals from
               session checkpoint → merge on top → user vars AVAILABLE
               → Prompt includes "## Variables (from previous request)" summary
```

#### 5.3.3 Extending Existing Session Infrastructure

> **Do NOT create `session_manager.py`.** Substantial session infrastructure
> already exists and must be extended, not duplicated.

**Existing infrastructure (already in codebase):**

| Component | Location | What It Does |
|---|---|---|
| `SQLiteSessionStore` | `src/session/sqlite_store.py` | Full CRUD, WAL SQLite, embeddings |
| `Session` model | `src/session/models.py` | Lifecycle (ACTIVE→IDLE→STALE→ARCHIVED), lineage |
| `SessionPersister` | `src/session/persister.py` | Turn counting, idle monitor, auto-checkpoint |
| `Checkpoint` model | `src/session/models.py` | Artifacts, execution_count, exploration_calls |
| `ResumeContext` | `src/session/models.py` | Context injection for resumed sessions |
| Session API routes | `src/api/routes/sessions.py` | Full API: create/list/resume/checkpoint |
| `AppState.session_store` | `src/api/state.py` | `SQLiteSessionStore` in global app state |
| `TaskDeps.session_store` | `src/graph/state.py:237` | Already typed as `SQLiteSessionStore` |

**Extensions required:**

**Step 0: Request contract for chat session restore** (`src/api/models/requests.py`, `src/api/routes/chat.py`, ~20 lines)

Cross-request globals restore requires a session key on the chat path. Add:

- `session_id: str | None` to `ChatRequest`
- request plumbing in `/chat` and pipeline entrypoints so `_execute_repl()` can read session identity
- explicit behavior: no `session_id` => current stateless behavior (no restore)

**Step 1: Extend `Checkpoint` model** (`src/session/models.py`, ~15 lines)

Add two fields to the `Checkpoint` dataclass:

```python
@dataclass
class Checkpoint:
    ...  # existing fields: artifacts, execution_count, exploration_calls, etc.
    # NEW Phase 3 fields:
    user_globals: dict[str, Any] = field(default_factory=dict)
    variable_lineage: dict[str, dict] = field(default_factory=dict)
    # lineage value: {"turn": int, "role": str, "chain_id": str | None, "request": int}
```

**Step 2: Extend `checkpoint()` to serialize user globals** (`src/repl_environment/state.py`, ~20 lines)

In `_StateMixin.checkpoint()` (state.py:208-279), after existing artifact serialization:

```python
def checkpoint(self) -> dict:
    ...  # existing checkpoint logic
    # NEW: serialize user-defined globals
    if hasattr(self, '_builtin_global_keys'):  # Phase 1 prerequisite
        user_globals = {}
        lineage = {}
        for key in self._globals:
            if key not in self._builtin_global_keys and not key.startswith('_'):
                if _is_json_serializable(self._globals[key]):
                    user_globals[key] = self._globals[key]
                    lineage[key] = self._variable_lineage.get(key, {"turn": 0})
                else:
                    logger.warning(f"Checkpoint: skipping non-serializable var '{key}' "
                                   f"({type(self._globals[key]).__name__})")
        checkpoint_data["user_globals"] = user_globals
        checkpoint_data["variable_lineage"] = lineage
    return checkpoint_data
```

**Step 3: Extend `restore()` to merge saved globals** (`src/repl_environment/state.py`, ~15 lines)

In `_StateMixin.restore()` (state.py:281-341), after `_build_globals()`:

```python
def restore(self, checkpoint_data: dict) -> None:
    ...  # existing restore logic (calls _build_globals() which rebuilds fresh)
    # NEW: merge saved globals on top of fresh builtins
    saved_globals = checkpoint_data.get("user_globals", {})
    saved_lineage = checkpoint_data.get("variable_lineage", {})
    skipped = []
    for key, value in saved_globals.items():
        if key not in self._globals:  # don't overwrite builtins
            self._globals[key] = value
        else:
            skipped.append(key)
    if skipped:
        logger.info(f"Restore: skipped {len(skipped)} vars that conflict with builtins: {skipped[:5]}")
    self._variable_lineage = saved_lineage
```

**Step 4: Wire `repl_executor.py` to restore globals from session** (`src/api/routes/chat_pipeline/repl_executor.py`, ~20 lines)

At task start, check if a session checkpoint exists with restorable globals:

```python
# In _execute_repl(), after creating REPLEnvironment (line ~150):
if session_id and deps.session_store:
    checkpoint = await deps.session_store.get_latest_checkpoint(session_id)
    if checkpoint and checkpoint.user_globals:
        repl.restore(checkpoint.to_dict())
        logger.info(f"Restored {len(checkpoint.user_globals)} globals from session {session_id}")
```

**Step 5: Extend `ResumeContext.format_for_injection()`** (`src/session/models.py`, ~10 lines)

Add variable summary to the context injection payload:

```python
def format_for_injection(self) -> str:
    ...  # existing injection (findings, session summary)
    # NEW: variable summary from checkpoint
    if self.checkpoint and self.checkpoint.user_globals:
        var_lines = []
        for key, value in self.checkpoint.user_globals.items():
            type_name = type(value).__name__
            preview = repr(value)[:80] if isinstance(value, (str, int, float, bool)) else type_name
            lineage = self.checkpoint.variable_lineage.get(key, {})
            source = f"request {lineage.get('request', '?')}" if lineage else "previous request"
            var_lines.append(f"  {key} ({type_name}, from {source}): {preview}")
        if var_lines:
            parts.append("## Variables (from previous request)\n" + "\n".join(var_lines))
    return "\n\n".join(parts)
```

**Step 6: Serialization safety helper** (`src/repl_environment/state.py`, ~10 lines)

```python
def _is_json_serializable(value: Any) -> bool:
    """Check if a value can be safely JSON-serialized for checkpoint storage.

    JSON-only. NEVER use pickle — arbitrary code execution on deserialize (R14).
    """
    try:
        json.dumps(value, default=str)
        return True
    except (TypeError, ValueError, OverflowError):
        return False
```

**Step 7: Size-based eviction** (`src/session/persister.py`, ~15 lines)

In `SessionPersister.save_checkpoint()`, add size cap:

```python
MAX_GLOBALS_SIZE = 100 * 1024 * 1024  # 100MB hard cap
WARN_GLOBALS_SIZE = 50 * 1024 * 1024  # 50MB warning

serialized = json.dumps(checkpoint.user_globals, default=str).encode()
if len(serialized) > MAX_GLOBALS_SIZE:
    logger.warning(f"Checkpoint globals exceed 100MB ({len(serialized)}), evicting oldest")
    # Evict oldest variables by lineage until under cap
    ...
elif len(serialized) > WARN_GLOBALS_SIZE:
    logger.warning(f"Checkpoint globals at {len(serialized) / 1024 / 1024:.1f}MB (warn threshold)")
```

##### 5.3.3.1 What Does NOT Need Changing (and Why)

| Component | File | Why No Change |
|---|---|---|
| `exec(code, self._globals)` | `environment.py` | Globals already persist within a task — Phase 3 is cross-request only |
| `_build_globals()` | `environment.py` | Still used for fresh init; restored globals merge on top |
| `_invoke_tool()` / `_call_tool()` | `context.py` | Tool dispatch unchanged — uses current `_globals` regardless of origin |
| Parallel dispatch | `parallel_dispatch.py` | Operates on current globals regardless of origin |
| `_spill_output()` | `environment.py` | Stdout handling unchanged |
| `ToolRegistry` | `tool_registry.py` | No registration changes needed |
| Graph nodes | `nodes.py` | Use `deps.repl` transparently — restored globals are invisible to nodes |
| `TaskState` | `state.py` | No `repl_session_id` needed — `TaskDeps.session_store` + `Session.id` covers it |
| `REPLSession` class | N/A | Not needed — extend `Checkpoint` model instead |
| `session_manager.py` | N/A | Not needed — existing `SessionPersister` + `SQLiteSessionStore` covers lifecycle |

##### 5.3.3.2 Edge Cases

1. **Non-serializable globals**: Module refs (numpy/scipy), lambdas, file handles,
   generators are NOT JSON-serializable. `_is_json_serializable()` filters these
   out. Warning logged per skipped variable. Model informed on restore which
   variables could not be persisted.

2. **Restored variables reference deleted files**: Variables from Request 1 may
   contain file paths or handles that are stale by Request 10. No automatic
   validation — model must handle stale references. Consider adding variable age
   tracking with auto-expire (configurable, default 10 requests).

3. **Role transitions in escalation chain**: Same REPL shared across
   FrontdoorNode → CoderEscalationNode. Variable lineage tracks which role
   (frontdoor/coder/architect) created each var. Lineage dict includes `"role"`
   field.

4. **`checkpoint_restore()` called mid-task**: `restore()` calls
   `_build_globals()` fresh, then merges saved globals. If called mid-task, any
   variables set earlier in the current task are lost (replaced by checkpoint
   state). Document as expected behavior — `checkpoint_restore()` is a full reset.

5. **Concurrent requests to same session**: Race condition on checkpoint writes.
   `SQLiteSessionStore` uses WAL mode (write-ahead logging) — concurrent reads
   safe, concurrent writes serialized by SQLite. Last-write-wins semantics.
   Acceptable for session-scoped checkpoints.

6. **Session timeout mid-task**: Globals persist in REPL (task-local, in-memory)
   regardless of session state. Session checkpoint may expire via
   `SessionPersister`'s idle monitor, but current task unaffected. Only affects
   next request's ability to restore.

7. **Builtin name collision on restore**: Saved variable named same as a builtin
   (e.g., `json`, `math`). `restore()` checks `if key not in self._globals`
   before merging — builtins preserved, conflicting user var skipped with log.

8. **Empty checkpoint**: No user globals to restore. `restore()` no-ops on empty
   `user_globals` dict. Model sees no "Variables from previous request" section.

#### 5.3.4 Prompt Awareness of Persistent State

Phase 1's `get_state()` (Step 6) already lists user-defined variables with type +
preview for within-task use. Phase 3 extends this for cross-request context:

**Within-task** (Phase 1, already handles): `get_state()` shows
"## Available Variables (from previous turns)" with type + truncated preview.

**Cross-request** (Phase 3, new): `ResumeContext.format_for_injection()` adds
"## Variables (from previous request)" with source annotation showing which
request created each variable. This section is injected into the system prompt
when a session is resumed.

```python
# Phase 3 addition to ResumeContext.format_for_injection():
# Only adds "(from previous request)" annotations and request-number sourcing.
# The variable listing format reuses Phase 1's get_state() pattern.
```

No changes to `src/prompt_builders/builder.py` — Phase 1 already handles prompt
injection for user-defined variables. Phase 3's injection happens through the
existing `ResumeContext` pathway in the sessions API.

#### 5.3.5 Files to Modify

| File | Change | Lines |
|---|---|---|
| `src/api/models/requests.py` | Add optional `session_id` to `ChatRequest` for cross-request restore | ~5 |
| `src/api/routes/chat.py` | Propagate `session_id` into pipeline execution path | ~10 |
| `src/session/models.py` | Add `user_globals`, `variable_lineage` to `Checkpoint`; extend `ResumeContext.format_for_injection()` | ~25 |
| `src/repl_environment/state.py` | `checkpoint()` serializes user globals (using Phase 1's `_builtin_global_keys`); `restore()` merges saved globals after `_build_globals()`; add `_is_json_serializable()` helper | ~45 |
| `src/session/persister.py` | `save_checkpoint()` passes globals; size-based eviction (100MB hard, 50MB warn) | ~15 |
| `src/session/sqlite_store.py` | Persist/load new checkpoint fields (`user_globals`, `variable_lineage`) + schema migration | ~40 |
| `src/api/routes/chat_pipeline/repl_executor.py` | Task start checks session for restorable checkpoint | ~20 |
| `src/api/routes/sessions.py` | Resume endpoint triggers globals restore via `ResumeContext` | ~10 |
| `src/features.py` | Add `ORCHESTRATOR_PERSISTENT_REPL_SESSION` flag | +3 |
| `tests/unit/test_repl_session.py` | NEW: cross-request persistence, serialization filtering, eviction, isolation, non-serializable handling | ~200 |

**Removed from original plan** (not needed):
- `src/repl_environment/session_manager.py` — existing `SessionPersister` + `SQLiteSessionStore` covers lifecycle
- `src/graph/state.py` (`repl_session_id`) — `TaskDeps.session_store` + `Session.id` already provides session identity
- `src/repl_environment/types.py` (`persistent_session` in REPLConfig) — feature flag in `features.py` sufficient
- `src/prompt_builders/builder.py` — Phase 1 already handles variable listing; Phase 3 uses `ResumeContext` pathway

#### 5.3.6 Expected Impact

> **Revised downward.** Within-task persistence already works → benefits only
> cross-request workflows (multi-turn conversations spanning multiple API calls).

| Metric | Estimate | Reasoning |
|---|---|---|
| **Token waste on re-derivation** | 20-40% reduction | Only cross-request workflows benefit; within-task already persists |
| **Multi-request workflow speed** | 1.2-1.5x faster | Smaller prompts on resumed sessions; no re-computation of previously derived variables |
| **Complex workflow capability** | Qualitative uplift | Enables iterative workflows across API calls (e.g., multi-turn data analysis, incremental code refactoring) |

#### 5.3.7 Phase 3 Completion Checklist

- [ ] **Prerequisite**: Phase 1 (deferred tool results) shipped and default ON — `_builtin_global_keys` available
- [ ] **Prerequisite (soft)**: Phase 2 (tool chaining) shipped — enables variable lineage with `caller_type`/`chain_id`
- [ ] `Checkpoint` model extended with `user_globals` and `variable_lineage` fields (`src/session/models.py`)
- [ ] `ChatRequest` extended with optional `session_id`, and `/chat` pipeline plumbs it to REPL execution
- [ ] `checkpoint()` serializes user globals using Phase 1's `_builtin_global_keys` filter (`src/repl_environment/state.py`)
- [ ] `_is_json_serializable()` helper added — JSON-only, NEVER pickle (R14)
- [ ] `restore()` merges saved globals after `_build_globals()` with builtin collision protection (`src/repl_environment/state.py`)
- [ ] `ResumeContext.format_for_injection()` extended with variable summary + "(from previous request)" annotations (`src/session/models.py`)
- [ ] `repl_executor.py` wired to restore globals from session checkpoint on task start
- [ ] `sqlite_store.py` checkpoint persistence updated for `user_globals` + `variable_lineage`, including migration path
- [ ] `sessions.py` resume endpoint triggers globals restore
- [ ] Feature flag `ORCHESTRATOR_PERSISTENT_REPL_SESSION` added to `src/features.py`
- [ ] Memory limits: 100MB hard cap, 50MB warning on checkpoint globals size
- [ ] Size-based eviction: oldest variables evicted when cap exceeded (`src/session/persister.py`)
- [ ] Non-serializable variables: logged as warning, excluded from checkpoint, model informed on restore
- [ ] Variable lineage: tracks turn, role, chain_id (Phase 2), request number per variable
- [ ] GC sweep per checkpoint: remove closed handles, expired objects before serialization
- [ ] Session isolation: checkpoints scoped to `Session.id`, no cross-session leakage
- [ ] Variable age tracking: auto-expire after configurable request count (default 10)
- [ ] Unit tests: cross-request persistence, serialization filtering, eviction, isolation, non-serializable handling (`tests/unit/test_repl_session.py`)
- [ ] Integration tests: Request 1 sets variable → Request 2 resumes session → variable available
- [ ] A/B evaluation completed on multi-request workflow tasks
- [ ] No quality regression beyond threshold
- [ ] ClaudeDebugger: checkpoint `user_globals` integrated for cross-request replay
- [ ] **Logging**: `agent_audit.log` updated with Phase 3 session entries; checkpoint globals events (save, restore, evict, skip) logged
- [ ] **Progress report**: `progress/YYYY-MM/YYYY-MM-DD.md` entry written with session metrics and eval results
- [ ] **Handoff update**: This file updated — Phase 3 status changed to COMPLETE, all metrics recorded in Section 15
- [ ] **Documentation**: `docs/chapters/29-programmatic-tool-chaining.md` updated with persistent sessions section, checkpoint globals flow, configuration reference
- [ ] **Architecture chapter**: `docs/chapters/10-orchestration-architecture.md` updated — note `Checkpoint` model extension (NOT new session_manager)
- [ ] **CHANGELOG.md**: Entry added under today's date
- [ ] **CLAUDE.md Component Flow**: Updated to include `Sessions: Checkpoint(user_globals) → cross-request variable persistence`
- [ ] **CLAUDE.md Hierarchical Orchestration System**: Note added about cross-request persistence in execution model
- [ ] **handoffs/active/rlm-orchestrator-roadmap.md**: Phase 3 completion noted; link to docs chapter
- [ ] **Handoff lifecycle**: If all 3 phases complete → extract findings to permanent docs → delete this handoff per lifecycle policy

---

## 6) Risk Analysis and Mitigation Plan

### 6.1 Risk Matrix

| ID | Risk | Phase | Severity | Likelihood | Mitigation |
|---|---|---|---|---|---|
| R1 | Safety regression: chaining write-tools in `_execute_structured()` without model review between each. The change is in the structured mode gate (environment.py:662-670), not in `_invoke_tool()`. Standard mode is unaffected. | P2 | HIGH | MEDIUM | Per-tool opt-in via `allowed_callers`, `escalate`/`delegate` always rejected from chains, abort-on-error via exec() natural semantics. Rollback deferred (no per-tool checkpoint infrastructure exists). |
| R2 | Error propagation: tool 2 of 5 fails, model can't adapt mid-chain. Phase 2a: `exec()` aborts on exception (natural Python behavior, no new infrastructure). Phase 2b: `ChainResult` wraps individual calls for parallel dispatch only. | P2 | MEDIUM | HIGH | Phase 2a: natural `exec()` abort (zero new code). Phase 2b: `ChainResult` with per-step error capture, abort-on-first-error default. |
| R3 | Observability loss: fewer LLM turns = fewer audit points | P1, P2 | MEDIUM | HIGH | Richer tool invocation logging, chain_id grouping |
| R4 | Context starvation: model loses information with deferred results | P1 | MEDIUM | MEDIUM | Prompt guidance, explicit print() discipline |
| R5 | Memory leak: persistent globals accumulate unbounded state. **Upgraded reasoning**: No production memory guard exists (pytest-only 100GB check in conftest.py). Phase 1 deferred mode increases globals accumulation. No cleanup between turns/escalations for `artifacts`, `_findings_buffer`, `_grep_hits_buffer`. | P3 | HIGH | HIGH | Per-checkpoint size cap (100MB hard, 50MB warn), size-based eviction of oldest variables, GC sweep before serialization, variable age tracking with auto-expire |
| R6 | Security: cross-session state leakage. **Reframed**: Within a task, globals already shared across escalation chain (by design). Phase 3 INTENTIONALLY shares state across requests within a session. Real risks: (a) session hijacking via stolen `session_id`, (b) cross-session leakage if checkpoint scoping is wrong. | P3 | HIGH | LOW | Checkpoints scoped to `Session.id`, `SQLiteSessionStore` enforces session boundaries, no cross-session queries without explicit session_id. Session hijacking mitigated by existing auth layer. |
| R7 | Regression in benchmark scores | P1, P2 | MEDIUM | MEDIUM | A/B test with feature flag before default flip |
| R8 | Dependency analysis false negatives: parallel execution when sequential required. Additional risk: current regex detection (environment.py:641-648) false-positives on function names in comments/strings; AST unification (Phase 2 Section 5.2.4) addresses this but introduces AST parse cost per turn. | P2 | HIGH | LOW | Conservative default (assume dependent), explicit override. AST unification eliminates regex false-positive class. Parse cost mitigated by caching `ast.parse()` result for both detection and dispatch stages. |
| R9 | Model adaptation: models may not immediately adapt to deferred result pattern | P1 | LOW | MEDIUM | Prompt engineering, system prompt updates |
| R10 | Serialization failures in session persistence. **Upgraded likelihood**: Modules (numpy, scipy), lambdas, file handles, generators are NOT JSON-serializable and are common in REPL globals. `_is_json_serializable()` filter required. | P3 | MEDIUM | HIGH | JSON-only serialization with `default=str` fallback. `_is_json_serializable()` filter excludes non-serializable types. Warning logged per skipped variable. Model informed on restore which variables could not be persisted. Accept loss of non-serializable types — data vars persist, function refs don't. |
| R11 | Mixin tool return type change: code doing `json.loads(my_role())` currently gets `<<<TOOL_OUTPUT>>>...<<<END_TOOL_OUTPUT>>>` which would fail. In deferred mode it gets clean JSON which succeeds. Positive change but could mask issues if code relied on delimiter format. | P1 | LOW | LOW | Delimiter stripping already happens for answer resolution. No code should depend on delimiters in return values. |
| R12 | `_resolve_answer()` fallback to empty string when model calls tools but never prints or FINALs. In legacy mode, `_tool_outputs` provided a safety net answer. In deferred mode, this fallback is gone. | P1 | MEDIUM | LOW | Silent execution nudge (Step 4) catches this and forces model to print. Max-turns rescue still operates on `last_output`. |
| R13 | **Stale state**: Variables from Request 1 may become invalid by Request 10 (deleted files, expired connections, outdated data). No automatic validation of restored variable validity. | P3 | MEDIUM | MEDIUM | Variable age tracking with auto-expire (configurable, default 10 requests). Model informed of variable age in restore summary. No automatic validation — model must handle stale references. |
| R14 | **Deserialization attack**: Pickle = arbitrary code execution on deserialize. Original handoff proposed `pickle.dumps()` (line 1317 of original). Critical attack surface if checkpoint data is tampered with. | P3 | CRITICAL | LOW | JSON-only serialization, NEVER pickle. `_is_json_serializable()` uses `json.dumps(default=str)`. No `pickle`, no `cloudpickle`, no `dill`. Accept loss of non-serializable types as the cost of safety. |

### 6.2 Detailed Mitigation Plans

#### R1: Safety Regression (Chaining Write-Tools)

**Problem**: Currently in structured mode, the model reviews each tool's output before deciding on the next action. With chaining, a code block could chain `file_write_safe(...)` → `run_shell(...)` without intermediate review. This only affects structured mode — standard mode already allows this.

**Mitigation strategy (defense-in-depth):**

1. **Per-tool opt-in**: Only tools with `allowed_callers: ["chain"]` can participate in chains. Start with safe tools only (see Section 5.2.6 categorization). `escalate`/`delegate` always rejected.

2. **Chain preview logging**: Before executing a chain, log the execution plan to `agent_audit.log`:
   ```python
   def _log_chain_preview(code: str, tool_calls: list[_ToolCall]) -> str:
       """Log and return chain_id. Used for audit trail, not blocking."""
   ```

3. **No rollback** (deferred): No per-tool checkpoint infrastructure exists. `workspace_state` updates per-turn, `artifacts` accumulate across turns, never reverted. Rollback requires new infrastructure — defer to future phase. Safety relies on opt-in + abort-on-error.

4. **Chain depth limit**: Maximum 10 tool calls per chain (configurable). Prevents runaway loops generated by model.

#### R2: Error Propagation in Chains

**Problem**: If tool call #2 of #5 fails, the remaining 3 calls may execute with bad state, or the model never gets a chance to adapt.

**Two-phase mitigation:**

**Phase 2a (sequential via exec())**: Python's `exec()` already provides abort-on-error semantics. If any statement raises an exception, `exec()` aborts and the REPL captures the traceback. No new infrastructure needed. The model sees the error and retries next turn. This is identical to current standard mode behavior.

**Phase 2b (parallel dispatch with ChainResult)**: For parallel execution of independent tools, `exec()` can't be used (it's sequential). Individual tool calls need wrapping:

1. **Abort-on-first-error** (default): Parallel group stops early. Model sees: `"Chain aborted at step 2/5: TOOL('process') failed with: <error>. Steps 1/5 succeeded."`

2. **Continue-on-error** (opt-in): Chain continues, collecting errors. Model sees combined report. Useful for independent operations (e.g., writing 5 independent files).

3. **Error wrapper**:
   ```python
   @dataclass
   class ChainResult:
       steps: list[ChainStep]  # Each: tool_name, args, result_or_error, success, elapsed_ms
       aborted_at: int | None  # Step index where chain aborted, or None
       total_elapsed_ms: float
   ```

Note: `ChainResult` is only used in Phase 2b's parallel dispatch path. Phase 2a's sequential `exec()` path uses Python's natural exception propagation.

#### R3: Observability Loss

**Problem**: With deferred results and chaining, there are fewer LLM turns and less visible intermediate state.

**Mitigation strategy:**

1. **Enhanced ToolInvocation logging**: Every tool call in a chain gets its own `ToolInvocation` entry with `chain_id` and `chain_index`.

2. **Chain summary in ChatResponse**:
   ```python
   # New field in ChatResponse
   tool_chains: list[dict] = [
       {
           "chain_id": "ch_abc123",
           "tools": ["search", "filter", "summarize"],
           "total_elapsed_ms": 245,
           "steps_succeeded": 3,
           "steps_failed": 0,
       }
   ]
   ```

3. **Audit log enrichment**: Each chain gets a single audit entry with full step-by-step breakdown.

4. **Pipeline monitor integration**: `ClaudeDebugger` should render chain steps in replay view.

#### R4: Context Starvation (Deferred Results)

**Problem**: Model may "forget" to print important information, leading to information loss between turns.

**Mitigation strategy:**

1. **System prompt guidance**: Explicit instruction to print key findings (see Section 5.1.7).

2. **Auto-summary fallback**: If a turn produces tool results but no print output, auto-generate a one-line summary:
   ```python
   if deferred_mode and tool_invocations > 0 and not stdout:
       auto_summary = f"[{tool_invocations} tool(s) called. Use print() to record findings.]"
       # Inject as nudge, not as error
   ```

3. **Gradual rollout**: Start with deferred mode on frontdoor only (where context pressure is highest). Keep legacy mode for architect roles (which have larger context windows).

#### R5: Memory Leak in Persistent Globals (Phase 3)

**Problem**: Persistent globals accumulate large objects (DataFrames, file contents, model outputs) across many requests. No production memory guard exists — the 100GB check in `conftest.py` is pytest-only. Phase 1 deferred mode increases globals accumulation (more tool results stay as variables). `artifacts`, `_findings_buffer`, `_grep_hits_buffer` grow monotonically with no cleanup between turns/escalations.

**Mitigation strategy:**

1. **Per-checkpoint size cap**: 100MB hard cap, 50MB warning. Measured via `json.dumps(user_globals, default=str)`. Oldest variables evicted when cap exceeded.
2. **Variable age tracking**: Each variable tracks request number at creation. Auto-expire after configurable limit (default 10 requests).
3. **GC sweep before serialization**: Remove variables referencing closed file handles, expired connections, `None` values from failed operations.
4. **Explicit cleanup API**: `del_var("old_data")` and `clear_session()` injected into REPL globals when persistent sessions enabled.
5. **Session lifecycle**: Existing `SessionPersister` idle monitor handles session timeout. `Session` model lifecycle (ACTIVE→IDLE→STALE→ARCHIVED) provides natural cleanup boundaries.

#### R6: Security — Cross-Session State Leakage (Phase 3)

**Problem (reframed)**: Within a task, globals are already shared across the escalation chain (FrontdoorNode → CoderEscalationNode) — this is by design. Phase 3 INTENTIONALLY shares state across requests within a session. The real risks are: (a) session hijacking via stolen `session_id` allowing access to another user's persisted state, and (b) cross-session leakage if checkpoint scoping logic is wrong.

**Mitigation strategy:**

1. **Checkpoint scoping**: Checkpoints stored in `SQLiteSessionStore` are scoped to `Session.id`. No cross-session queries without explicit session_id parameter.
2. **Session authentication**: Session identity validated through existing auth layer in API routes. `session_id` alone is not sufficient — must match authenticated user context.
3. **Opt-in only**: Cross-request persistence requires client to pass `session_id` in request. Without it, each request gets fresh globals (current behavior, no regression).
4. **No global state**: Persisted globals are session-scoped, not application-scoped. `AppState.session_store` is a store, not a cache — no in-memory state shared between requests.

#### R7: Benchmark Score Regression

**Problem**: Any change to the tool result flow could regress benchmark scores.

**Mitigation strategy:**

1. **Feature flags for all phases**: Each phase ships behind `ORCHESTRATOR_*` env flags, default OFF.
2. **A/B evaluation protocol**:
   ```bash
   # Baseline (legacy mode)
   ORCHESTRATOR_DEFERRED_TOOL_RESULTS=0 \
     python scripts/benchmark/seed_specialist_routing.py \
       --suites thinking,simpleqa,coding --sample-size 20

   # Treatment (deferred mode)
   ORCHESTRATOR_DEFERRED_TOOL_RESULTS=1 \
     python scripts/benchmark/seed_specialist_routing.py \
       --suites thinking,simpleqa,coding --sample-size 20
   ```
3. **Regression gate**: Must pass `compare_orchestrator_direct.py --regression-gate` before default flip.
4. **Rollback**: If regression detected post-flip, single env var change to revert.

#### R8: Dependency Analysis False Negatives

**Problem**: The AST-based dependency analysis might miss a dependency (e.g., two tools that write to the same file via different paths), causing parallel execution when sequential is required. Additional risk: the current regex detection (environment.py:641-648) is itself a source of false positives (matches function names in comments/strings).

**Mitigation strategy:**

1. **Conservative default**: If dependency cannot be determined, assume sequential. Phase 2a avoids this entirely by using sequential `exec()`.
2. **AST unification** (Phase 2 Section 5.2.4): Replace regex detection with AST. Eliminates false-positive class from commented-out calls and string literals. Cache `ast.parse()` result for both detection and dispatch.
3. **Side-effect declarations**: Tools declare their side effects (`MODIFIES_FILES`, `READS_FILES`, etc.) via existing `SideEffect` enum. If two tools both have `MODIFIES_FILES`, assume dependent.
4. **Path-based heuristic**: If two tools take `path` arguments, check for overlap.
5. **Escape hatch**: Model can annotate chain with `# SEQUENTIAL` comment to force sequential execution.

---

## 7) Documentation Changes Required

### 7.1 New Documentation

| Document | Content | Created At |
|---|---|---|
| `docs/chapters/29-programmatic-tool-chaining.md` | Full chapter covering concept, architecture, usage patterns, configuration | Phase 1 (draft), Phase 2 (expand), Phase 3 (complete) |
| `docs/reference/tool-chaining-patterns.md` | Quick reference for tool chaining patterns with examples | Phase 2 |

### 7.2 Updated Documentation (Per Phase)

**Phase 1 updates:**

| Document | Section to Add/Update |
|---|---|
| `CHANGELOG.md` | Feature entry for deferred tool results |
| `CLAUDE.md` Component Flow | Note deferred_tool_results if default flipped |
| `handoffs/active/rlm-orchestrator-roadmap.md` | Cross-link as Phase 9 or standalone track |

**Phase 2 updates:**

| Document | Section to Add/Update |
|---|---|
| `CHANGELOG.md` | Feature entry for tool chaining |
| `CLAUDE.md` Component Flow | Update to `ToolRegistry(chain_mode, allowed_callers)` |
| `docs/chapters/10-orchestration-architecture.md` | Add "Programmatic Tool Chaining" subsection |
| `orchestration/model_registry.yaml` | Add `tool_chain_mode` per-role config if applicable |
| `handoffs/active/rlm-orchestrator-roadmap.md` | Phase 2 completion noted |

**Phase 3 updates:**

| Document | Section to Add/Update |
|---|---|
| `CHANGELOG.md` | Feature entry for cross-request persistent globals |
| `CLAUDE.md` Component Flow | Add `Sessions: Checkpoint(user_globals) → cross-request variable persistence` |
| `CLAUDE.md` Hierarchical Orchestration | Note cross-request persistence in execution model |
| `docs/chapters/10-orchestration-architecture.md` | Note `Checkpoint` model extension for globals (NOT new session_manager) |
| `docs/chapters/15-memrl-system.md` | Note: deferred results affect reward signal collection |
| `handoffs/active/rlm-orchestrator-roadmap.md` | Phase 3 completion noted; link to docs chapter |

### 7.3 Chapter Draft Outline: Programmatic Tool Chaining

```markdown
# Programmatic Tool Chaining

## Concept

Programmatic tool chaining allows the orchestrator's REPL to execute multiple
tool calls within a single turn without re-sampling the LLM between calls.
Tool results stay in the REPL's execution globals and are NOT injected into
the LLM's context window — only explicit print() output enters the next
turn's prompt.

## Architecture

### Execution Modes

| Mode | Description | Feature Flag |
|------|-------------|--------------|
| Legacy | One write-tool per turn, results in context | (default) |
| Deferred | Multiple tools per turn, results in globals only | ORCHESTRATOR_DEFERRED_TOOL_RESULTS |
| Chained | Multi-mutation chains with dependency analysis | ORCHESTRATOR_TOOL_CHAIN_MODE |
| Persistent | Globals survive across requests | ORCHESTRATOR_PERSISTENT_REPL_SESSION |

### Flow Diagram

[Include the Phase 1/2/3 architecture diagrams from Section 5]

## Configuration

[env vars, per-role overrides, allowed_callers]

## Patterns

### Batch Processing
[example code showing loop over items with tool calls]

### Early Termination
[example code showing break on success]

### Conditional Tool Selection
[example code showing if/else tool dispatch]

### Data Filtering
[example code showing filter before context injection]

## Safety Model

### allowed_callers
[per-tool opt-in mechanism]

### Chain Limits
[depth, timeout, abort-on-error]

### Audit Trail
[chain_id, caller_type, invocation log enrichment]
```

### 7.4 CLAUDE.md Component Flow Update

Current:
```
Tools:      REPLExecutor → ToolRegistry → PluginLoader(5 plugins, 10 tools)
```

After (Phase 2+):
```
Tools:      REPLExecutor → ToolRegistry(chain_mode, allowed_callers) → PluginLoader(5 plugins, 10 tools)
Chaining:   AST dependency analysis → ToolDependencyGraph → parallel/sequential dispatch
```

After (Phase 3):
```
Tools:      REPLExecutor → ToolRegistry(chain_mode, allowed_callers) → PluginLoader(5 plugins, 10 tools)
Chaining:   AST dependency analysis → ToolDependencyGraph → parallel/sequential dispatch
Sessions:   Checkpoint(user_globals) → cross-request variable persistence → variable lineage tracking
```

---

## 8) Testing Strategy

### 8.1 Unit Tests

| Test File | Phase | Coverage |
|---|---|---|
| `tests/unit/test_repl_deferred_tools.py` | P1 | Deferred mode on/off, print-only context, auto-summary nudge |
| `tests/unit/test_tool_chaining.py` | P2 | Multi-tool chains, sequential/parallel, abort-on-error |
| `tests/unit/test_tool_dependencies.py` | P2 | AST dependency analysis, edge cases, false positive safety |
| `tests/unit/test_allowed_callers.py` | P2 | Per-tool caller restrictions, chain opt-in/opt-out |
| `tests/unit/test_chain_audit.py` | P2 | ToolInvocation enrichment, chain_id grouping |
| `tests/unit/test_repl_session.py` | P3 | Cross-request persistence, serialization filtering, eviction, isolation, non-serializable handling, variable lineage |

### 8.2 Integration Tests

| Test | Phase | What it validates |
|---|---|---|
| Multi-tool chain end-to-end | P2 | Model generates chain code → tools execute → FINAL() with aggregated result |
| Deferred mode seeding eval | P1 | Run benchmark suite with deferred=ON, compare scores to baseline |
| Cross-request globals persistence | P3 | Request 1 sets variable → checkpoint → Request 2 resumes session → variable available |
| Chain abort on failure | P2 | Tool 2 fails → chain aborts → model sees error, recovers |
| Observability check | P2 | Chain execution produces correct audit log entries |

### 8.3 Regression Tests

| Test | Threshold |
|---|---|
| SimpleQA pass rate | Must not decrease by >2% |
| Thinking suite pass rate | Must not decrease by >2% |
| Coding suite pass rate | Must not decrease by >3% |
| Average turns per task | Must decrease or stay same |
| Average tokens per task | Must decrease by >10% (Phase 1 target) |

---

## 9) Cross-Cutting Concerns

### 9.1 Interaction with MemRL

Deferred tool results affect how MemRL collects reward signals:

- **Current**: Tool outputs in `_tool_outputs` artifact contribute to `_tools_success()` heuristic (repl_executor.py:52-65)
- **Phase 1**: With deferred results, `_tool_outputs` is always empty → `_tools_success()` returns `None` → lost telemetry
- **Action**: Add invocation log fallback to `_tools_success()` — when `_tool_outputs` is empty but `tool_invocations > 0`, check `tool_registry.invocation_log` for success/failure signals (Phase 1 Step 5)
- **Phase 2**: Chain-level success/failure signals differ from individual tool signals; MemRL reward function needs `chain_id` awareness to attribute reward to the chain as a unit, not per-tool.

### 9.2 Interaction with Prefix Cache

Tool chaining doesn't affect prefix cache directly, but:

- **Phase 1**: Smaller prompts (no tool results in context) → better prefix cache hit rate (less prompt variance)
- **Phase 3**: Neutral-to-negative on first resumed turn. When a session is resumed, `ResumeContext.format_for_injection()` adds a "## Variables (from previous request)" section — a new prompt prefix that breaks prefix cache continuity for the first turn. Subsequent turns within the same task benefit from smaller prompts (Phase 1 effect).

### 9.3 Interaction with ClaudeDebugger

`ClaudeDebugger` replays execution for diagnostic analysis:

- **Phase 1**: Debugger must understand deferred mode to correctly attribute tool result visibility
- **Phase 2**: Debugger should render chain steps as a grouped execution unit, not individual tool calls
- **Phase 3**: Debugger needs checkpoint's `user_globals` for cross-request replay. When replaying a resumed session, the debugger must inject the same restored globals that the original execution had. Without this, replay diverges from production execution on the first tool call that references a restored variable.

### 9.4 Interaction with Escalation Policy

- **Phase 2**: If a chain fails, escalation should consider the CHAIN failure, not just the individual tool failure
- Chain failure at step 2/5 with 1 success = different escalation signal than 0/1 tool failure

### 9.5 Interaction with Workspace State (Phase 2)

The global workspace (`workspace_state` in `TaskState`) should be updated AFTER a complete chain, not after each individual tool call. This prevents inconsistent workspace snapshots mid-chain.

### 9.6 Interaction with Escalation Chain

Within a task, the same REPL instance is shared across FrontdoorNode → CoderEscalationNode (via `TaskDeps.repl`). Phase 3's variable lineage tracking includes a `"role"` field per variable, enabling attribution:

- **Variable lineage**: `{"data": {"turn": 2, "role": "frontdoor", "chain_id": null, "request": 1}}` — frontdoor created `data` in turn 2 of request 1
- **Cross-role visibility**: Variables set by frontdoor are visible to coder escalation (already works — same `_globals` dict). Phase 3 makes this explicit in lineage metadata.
- **Checkpoint scope**: When checkpointing for cross-request persistence, ALL user variables are saved regardless of which role created them. The lineage metadata preserves role attribution for the restore summary.

### 9.7 Existing Session Infrastructure Relationship

Phase 3 **extends** the existing session infrastructure — it does NOT replace or duplicate it:

| Existing Component | Phase 3 Extension |
|---|---|
| `Checkpoint` model (`session/models.py`) | Add `user_globals` + `variable_lineage` fields |
| `checkpoint()` (`state.py`) | Serialize user globals alongside existing artifacts |
| `restore()` (`state.py`) | Merge saved globals after `_build_globals()` |
| `SessionPersister` (`session/persister.py`) | Size-based eviction for globals |
| `ResumeContext` (`session/models.py`) | Variable summary in `format_for_injection()` |
| `SQLiteSessionStore` (`session/sqlite_store.py`) | Add persistence + migration for `user_globals` / `variable_lineage` checkpoint fields |
| `Session` model lifecycle | No changes — ACTIVE→IDLE→STALE→ARCHIVED provides natural cleanup |
| Session API routes (`sessions.py`) | Resume endpoint includes checkpoint globals summary; `/chat` path reads `session_id` for restore |

No new files created. No new classes. No new database tables (but checkpoint schema migration is required).

### 9.8 Seeding/Debugger Compatibility

`seed_specialist_routing.py --debug` and the seeding telemetry stack consume chat response diagnostics directly.  
When implementing Phase 1/2/3:

- Keep existing response fields stable (`tools_used`, `tools_called`, `tool_timings`, `tools_success`, `delegation_diagnostics`, `parallel_tools_used`).
- If adding fields (e.g. `tool_chains`), make them additive and optional.
- Update `scripts/benchmark/seeding_orchestrator.py:_normalize_tool_telemetry()` and `scripts/benchmark/seeding_eval.py` only if response semantics change.
- Ensure ClaudeDebugger replay still parses diagnostics after deferred-mode rollout.

---

## 10) Implementation Sequence (Recommended)

```
Week 1: Phase 1a — Feature flag + REPLConfig + deferred tool storage
    ↓
Week 1: Phase 1b — Prompt builder changes + auto-summary nudge
    ↓
Week 1: Phase 1c — Unit tests + integration tests
    ↓
Week 2: Phase 1d — A/B evaluation + regression gate
    ↓
Week 2: Phase 1e — LOGS: audit log, progress report, CHANGELOG, handoff update
                   DOCS: chapter draft (Phase 1 content), CLAUDE.md if default flipped
    ↓
Week 2: Phase 2-prereq — Wire SideEffect.READ_ONLY, replace hardcoded sets, AST unification
    ↓
Week 2: Phase 2a — allowed_callers field + caller_type tracking + remove structured mode rejection
    ↓
Week 3: Phase 2a-test — Unit tests, A/B evaluation of sequential chaining
    ↓
Week 3: Phase 2b — AST dependency analysis + parallel chain dispatch for write-tools
    ↓
Week 4: Phase 2b-test — Unit tests + integration tests + A/B evaluation
    ↓
Week 4: Phase 2-docs — LOGS: audit log, progress report, CHANGELOG, handoff update
                   DOCS: chapter expanded (chaining patterns, allowed_callers),
                         reference doc created, CLAUDE.md Component Flow updated,
                         architecture chapter updated, model_registry updated
    ↓
(Future) Phase 3a — Extend Checkpoint model with user_globals + variable_lineage
    ↓
(Future) Phase 3b — Extend checkpoint() to serialize user globals (using Phase 1's _builtin_global_keys)
    ↓
(Future) Phase 3c — Extend restore() to merge saved globals after _build_globals()
    ↓
(Future) Phase 3d — Wire repl_executor to restore globals from session on task start
    ↓
(Future) Phase 3e — Extend ResumeContext.format_for_injection() with variable summary
    ↓
(Future) Phase 3f — Memory limits: size cap (100MB/50MB), eviction, GC sweep, variable age tracking
    ↓
(Future) Phase 3g — Tests + A/B evaluation on multi-request workflows
    ↓
(Future) Phase 3h — LOGS: audit log, progress report, CHANGELOG, handoff update
                    DOCS: chapter completed (cross-request persistence, checkpoint flow),
                          CLAUDE.md Component Flow + Hierarchical Orchestration updated,
                          architecture chapter updated (Checkpoint extension, not session_manager),
                          MemRL chapter updated (reward signal changes)
    ↓
(Future) Phase 3i — HANDOFF LIFECYCLE: extract all findings to permanent docs → delete this handoff
```

---

## 11) Relationship to Existing Handoffs

| Handoff | Relationship | Action |
|---|---|---|
| `perf-parallel-tools-concurrent-sweep-prefix-cache.md` | WS1 (parallel reads) is a predecessor to Phase 2 | Link as "Phase 2 extends WS1 to write-tools" |
| `orchestration-architecture-optimization-handoff.md` | Telemetry contract must accommodate chain metrics | Ensure chain_id/caller_type in telemetry |
| `unified_execution_model.md` | React→REPL unification is prerequisite (COMPLETE) | No action needed |
| `handoffs/active/rlm-orchestrator-roadmap.md` | This should be added as Phase 9 or standalone track | Update roadmap |
| `native-computational-tools.md` | C++ tools will benefit from chaining (batch compute) | Add `allowed_callers: ["chain"]` to C++ tools |
| `compress-frontdoor-prompt.md` | Phase 1 achieves prompt compression via different mechanism | May supersede parts of that handoff |
| `orchestrator-intelligence-improvements.md` | Tool chaining directly improves orchestrator capability | Cross-reference |
| `rlm-orchestrator-roadmap.md` | RLM `SupportsPersistence` informs Phase 3 design; context compaction fills token pressure gap | Phase 3 implementer reads RLM handoff Delta D4 before starting |

---

## 12) Open Questions for Implementer

1. **Should deferred mode be per-role or global?** The 30B frontdoor benefits most (limited context), but architect roles with larger windows might prefer legacy mode for better reasoning about tool outputs.

2. **Chain depth limit**: What's the right default? Anthropic has no explicit limit, but their container timeout (~4.5 min) provides an implicit bound. For us, 10 tools per chain seems reasonable. Should this be configurable per role?

3. **MCP tool chaining**: Should MCP-backed tools be chainable? The latency characteristics are different (network round-trip per call). Anthropic explicitly excludes MCP connector tools from programmatic calling.

4. **llm_call() in chains**: Should `llm_call()` (sub-inference within REPL) be allowed within chains? This creates nested inference, which has resource implications.

5. **Phase 3 serialization format**: **RESOLVED — JSON-only.** Pickle = arbitrary code execution on deserialize (R14). Accept loss of non-serializable types (modules, lambdas, generators, file handles). `json.dumps(default=str)` for data vars. Functions and module refs are rebuilt by `_build_globals()` on restore.

6. **Cross-request persistence opt-in**: Should persistence be automatic (always checkpoint globals) or opt-in (client passes `session_id` to enable)? Recommendation: opt-in via `session_id` — matches Anthropic's `container` field pattern and avoids surprise state retention.

7. **Globals referencing REPL functions**: `_build_globals()` injects tool refs (`TOOL`, `CALL`, `peek`, etc.) into globals. If a user variable references one of these (e.g., `my_func = peek`), it cannot be serialized and should NOT be restored (would alias the wrong instance). Filter: only persist variables NOT in `_builtin_global_keys` (Phase 1) — tool refs are in builtins, user aliases to tools are excluded.

---

## 13) Success Metrics

> **Targets vs Estimates**: Section 13 targets are **conservative shipping gates** — the
> minimum improvement required to justify flipping each phase's feature flag to default ON.
> Per-phase "Expected Impact" sections (5.1.5, 5.2.12, 5.3.6) contain **estimate ranges**
> based on architecture analysis. Targets are deliberately set at or below estimate midpoints
> to avoid shipping on optimistic projections.

| Metric | Phase 1 Target | Phase 2 Target | Phase 3 Target |
|---|---|---|---|
| Avg tokens per multi-tool task | -30% ¹ | -50% | -35% (cross-request only) |
| Avg turns per multi-tool task | No change | -60% | -60% (within-task unchanged) |
| Frontdoor context utilization | -30% | -60% | -35% (cross-request only) |
| Benchmark quality regression | <2% | <3% | <3% |
| Tool invocations per task | No change | +50% (more tools, fewer turns) | +50% |
| Escalation rate | No change | -15% | -15% (within-task unchanged) |
| P50 task latency (multi-request) | -5% | -60% | -25% (cross-request benefit) |

¹ Per-phase estimate range is 30-90% (Section 5.1.5: "3-10x reduction"). Target set at conservative floor.

---

## 14) Appendix: Anthropic Source Material Mapping

| Anthropic Concept | Our Implementation | File(s) |
|---|---|---|
| `code_execution_20250825` tool type | REPLEnvironment + exec() sandbox | `src/repl_environment/environment.py` |
| `allowed_callers` field | `Tool.allowed_callers` | `src/tool_registry.py` |
| `caller` field in response | `ToolInvocation.caller_type` | `src/tool_registry.py` |
| Container lifecycle (create/expire/reuse) | `Session` + `SessionPersister` + `Checkpoint` (extended) | `src/session/models.py`, `src/session/persister.py` |
| `container` ID in API response | `Session.id` (already in `TaskDeps.session_store`) | `src/session/models.py`, `src/graph/state.py` |
| Tool result NOT in context | `deferred_tool_results=True` (Phase 1) | `src/repl_environment/routing.py`, `code_search.py`, `file_exploration.py` (14 mixin call sites) |
| Async tool functions (`await`) | ThreadPoolExecutor dispatch (Phase 2) | `src/repl_environment/parallel_dispatch.py` |
| Batch processing loops | Sequential chain execution | `src/repl_environment/environment.py` |
| Early termination (`break`) | Chain abort semantics | `src/repl_environment/environment.py` |
| AST security visitor | Already exists | `src/repl_environment/security.py` |
| Safe import whitelist | Already exists | `src/repl_environment/environment.py` |
| Code hash integrity | Already exists (`Tool.code_hash`) | `src/tool_registry.py` |
| Role-based permissions | Already exists (`ToolPermissions`) | `src/tool_registry.py` |
| Invocation logging | Already exists (`ToolInvocation`) | `src/tool_registry.py` |
| Output spill / summarization | Already exists (`_spill_output()`) | `src/repl_environment/environment.py` |

---

## 15) Resume Commands

```bash
cd /mnt/raid0/llm/claude

# Read this handoff
cat handoffs/archived/programmatic-tool-chaining.md

# Phase 1: Inspect the 14 mixin call sites that need _maybe_wrap_tool_output()
rg -n "wrap_tool_output\|_tool_outputs" src/repl_environment/routing.py src/repl_environment/code_search.py src/repl_environment/file_exploration.py

# Phase 1: Verify _invoke_tool() does NOT use wrap_tool_output (no change needed)
rg -n "wrap_tool_output\|_tool_outputs" src/repl_environment/context.py

# Phase 1: Verify/fix _increment_exploration recursion bug (P0 prerequisite)
sed -n '20,60p' src/repl_environment/file_exploration.py

# Phase 1: Inspect _tools_success() that needs invocation log fallback
sed -n '52,65p' src/api/routes/chat_pipeline/repl_executor.py

# Phase 1: Inspect silent execution nudge that needs deferred-awareness
sed -n '1015,1030p' src/graph/helpers.py

# Phase 1: Inspect get_state() for user-defined globals listing
cat src/repl_environment/state.py

# Phase 1: Inspect features.py for flag pattern
head -60 src/features.py

# Phase 1: Inspect _tool_outputs consumers (should be safe with empty list)
rg -n "_tool_outputs" src/graph/nodes.py src/graph/helpers.py src/api/routes/chat_utils.py

# Phase 2: Inspect the three disconnected read-only classification systems
rg -n "read_only" src/repl_environment/environment.py src/api/routes/chat_pipeline/repl_executor.py src/tool_registry.py

# Phase 2: Inspect regex-based tool detection (to be replaced with AST)
sed -n '639,670p' src/repl_environment/environment.py

# Phase 2: Inspect AST-based parallel dispatch (to be extended)
cat src/repl_environment/parallel_dispatch.py

# Phase 2: Verify SideEffect.READ_ONLY is defined but never populated on tools
rg -n "READ_ONLY" src/tool_registry.py

# Phase 2: Inspect tool_registry.yaml for allowed_callers field (should not exist yet)
rg -n "allowed_callers" orchestration/tool_registry.yaml

# Phase 2: Inspect structured mode restriction (to be conditionally removed)
rg -n "structured_mode\|one tool\|all_read_only" src/repl_environment/environment.py

# Phase 3: Inspect Checkpoint model for user_globals extension point
rg -n "class Checkpoint" src/session/models.py
sed -n '1,50p' src/session/models.py

# Phase 3: Inspect ChatRequest for session_id extension point
sed -n '1,80p' src/api/models/requests.py

# Phase 3: Inspect checkpoint() and restore() in state.py
rg -n "def checkpoint\|def restore" src/repl_environment/state.py

# Phase 3: Inspect SessionPersister for save_checkpoint extension
rg -n "save_checkpoint\|class SessionPersister" src/session/persister.py

# Phase 3: Inspect SQLite checkpoint persistence + migration points
rg -n "CREATE TABLE IF NOT EXISTS checkpoints|save_checkpoint|get_latest_checkpoint|from_dict" src/session/sqlite_store.py

# Phase 3: Inspect ResumeContext.format_for_injection
rg -n "format_for_injection\|class ResumeContext" src/session/models.py

# Phase 3: Inspect session resume route
rg -n "resume_session\|def resume" src/api/routes/sessions.py

# Phase 3: Verify TaskDeps.session_store typing
rg -n "session_store" src/graph/state.py

# Run existing tests to get baseline
python -m pytest tests/ --ignore=tests/integration -q

# Run gates
make gates
```

---

## 16) Documentation Coordination

All documentation updates are embedded in each phase's completion checklist.
This section consolidates them for cross-phase planning.

### 16.1 Chapter: `docs/chapters/29-programmatic-tool-chaining.md`

| Phase | Action | Content |
|---|---|---|
| P1 | CREATE draft | Concept, deferred mode, architecture diagrams, config reference |
| P2 | EXPAND | Chaining patterns, allowed_callers, dependency analysis, safety model |
| P3 | COMPLETE | Cross-request persistence, checkpoint flow, session lifecycle |

### 16.2 Reference: `docs/reference/tool-chaining-patterns.md`

Created in Phase 2. Quick-reference examples for tool chaining patterns
(batch processing, early termination, conditional dispatch, data filtering).

### 16.3 Per-Phase Documentation Deliverables

| Deliverable | P1 | P2 | P3 |
|---|---|---|---|
| `CHANGELOG.md` entry | ✓ | ✓ | ✓ |
| `progress/YYYY-MM/YYYY-MM-DD.md` | ✓ | ✓ | ✓ |
| Chapter 29 (create/expand/complete) | create | expand | complete |
| `CLAUDE.md` Component Flow | if default flipped | chain_mode line | sessions line |
| `handoffs/active/rlm-orchestrator-roadmap.md` | cross-link | Phase 2 noted | Phase 3 noted |
| `docs/reference/tool-chaining-patterns.md` | — | create | — |
| `docs/chapters/10-orchestration-architecture.md` | — | chaining subsection | Checkpoint extension note |
| `docs/chapters/15-memrl-system.md` | — | — | reward signal note |
| Handoff lifecycle (delete handoff) | — | — | ✓ (if all phases done) |

### 16.4 Stale Documentation (Opportunistic)

- `progress/INDEX.md`: 13 days behind (last entry 2026-02-04). Update when writing progress entries.
- `handoffs/blocked/BLOCKED.md`: Last updated 2026-01-28. Review during handoff lifecycle phase.

---

## 17) Implementation Status Update (2026-02-18)

### Completed in Code (this session)

- Phase 1 P0 prerequisite fixed:
  - `src/repl_environment/file_exploration.py:_increment_exploration()` recursion bug fixed (lock-safe increment).
- Phase 1 core wiring implemented:
  - `deferred_tool_results` feature flag added (`src/features.py`).
  - REPL helper `_maybe_wrap_tool_output()` + deferred flag state + builtin globals snapshot (`src/repl_environment/environment.py`).
  - Path-A mixin wrap callsites migrated in:
    - `src/repl_environment/routing.py`
    - `src/repl_environment/code_search.py`
    - `src/repl_environment/file_exploration.py`
  - Deferred-aware silent-execution nudge (`src/graph/helpers.py`).
  - `_tools_success()` invocation-log fallback (`src/api/routes/chat_pipeline/repl_executor.py`).
  - `get_state()` now lists user variables and suppresses `_tool_outputs` preview in deferred mode (`src/repl_environment/state.py`).
  - Prompt hint added for deferred semantics (`src/prompt_builders/builder.py`).

### Tests Added/Updated

- Added `tests/unit/test_repl_deferred_tools.py`.
- Updated `tests/unit/test_features.py` for `deferred_tool_results` key/default.

### Validation Snapshot

- Passed:
  - `tests/unit/test_features.py`
  - `tests/unit/test_repl_deferred_tools.py`
  - `tests/unit/test_code_search.py`
  - `tests/unit/test_repl_routing.py`
  - `tests/unit/test_repl_executor.py::TestToolOutputsInAnswer::test_tool_outputs_tracked_in_response`
- Not fully runnable in this sandbox:
  - `tests/unit/test_repl_file_exploration.py` (permission errors writing to `/mnt/raid0/llm/tmp/*`).

### Remaining to Close Phase 1

- Run full Phase 1 A/B benchmark/eval and record metrics in Section 15 checklist format.
- Confirm debugger/seeding telemetry remains stable under deferred mode in live orchestration runs.

### 2026-02-18 Incremental Update (Read-Only Prereq)

Additional implementation shipped after the initial Phase 1 core:

- Added canonical REPL read-only source in `REPLEnvironment`:
  - `_READ_ONLY_REPL_TOOLS`
  - `_get_read_only_tools()` (unions REPL built-ins + registry read-only tools)
- Structured mode dispatch now uses `_get_read_only_tools()` (removed inline hardcoded set).
- `parallel_tools_used` telemetry now also uses `_get_read_only_tools()` (fallback-safe), reducing execution/telemetry drift.

Status impact:
- Phase 2 prerequisites partially advanced (classification centralization in runtime path).
- Full registry-side `SideEffect.READ_ONLY` population is still pending.

### 2026-02-18 Live Probe Note (Phase 1)

A lightweight live A/B smoke probe was run via `seed_specialist_routing`:

- `ORCHESTRATOR_DEFERRED_TOOL_RESULTS=0` (simpleqa sample=1, seed=60)
- `ORCHESTRATOR_DEFERRED_TOOL_RESULTS=1` (simpleqa sample=1, seed=61)

Outcome:
- Deferred mode did not regress basic SELF:repl tool execution/telemetry (tool timings and diagnostics remained present).
- Deferred run encountered architect timeout/erase path and wrapper timeout (`code 124`) after summary emission.
- Because question IDs differed across seeds and seen-set state advanced between runs, this is only a smoke check, not final A/B quality evidence.

Required before default flip:
- fixed-question controlled replay (same prompt IDs),
- at least 5-run stability set under both modes,
- explicit token/prompt-size comparison extracted from diagnostics.

### 2026-02-18 Incremental Clarification (Fixed-Question Replay + Infrastructure)

- Controlled replay on a fixed prompt (`simpleqa_general_04050`) indicates delegated architect timeout behavior is **not uniquely caused** by `deferred_tool_results`; similar timeout signatures can occur with deferred OFF and ON on the same request path.
- A separate infrastructure bug was identified and fixed:
  - stale uvicorn worker subprocesses surviving orchestrator reloads could hold inference locks and pollute delegation timeout diagnosis.
  - fix landed in `scripts/server/orchestrator_stack.py` (process-tree termination on reload/stop path).
- Delegated-loop timeout amplification was also reduced:
  - specialist `FINAL(...)` now returns immediately (`break_reason=specialist_report`) instead of forcing an additional architect synthesis hop that often exhausted request budget.
- Implication for this handoff:
  - Phase 1 deferred-tool mechanism remains valid,
  - benchmark interpretation must exclude reload-lifecycle lock contamination when comparing OFF vs ON.

### 2026-02-18 Phase 2a Implementation Update (Structured Chaining + Telemetry)

Implemented this session:

- `src/tool_registry.py`
  - Added `Tool.allowed_callers` (default `["direct"]`).
  - Added `ToolRegistry.get_chainable_tools()`.
  - Added chain metadata to `ToolInvocation`:
    - `caller_type`
    - `chain_id`
    - `chain_index`
  - Extended `ToolRegistry.invoke()` to accept caller/chain metadata.
  - Added YAML loader support for `allowed_callers`.
- `src/repl_environment/parallel_dispatch.py`
  - Added AST helper `extract_tool_calls()` for unified call detection.
- `src/repl_environment/environment.py`
  - Replaced regex-based structured gate call counting with AST-based detection.
  - Structured multi-tool gate now allows non-read-only chains only for chainable tools.
  - Explicitly blocks `delegate` / `escalate` in chained turns.
  - Added REPL chainable built-ins set and invocation chain context (`_active_tool_chain_id/index`).
- `src/repl_environment/context.py`
  - `_invoke_tool()` now propagates `caller_type/chain_id/chain_index` to registry invokes.
- `src/api/models/responses.py` + `src/api/routes/chat_pipeline/repl_executor.py`
  - Added `tool_chains` response field and grouped chain summaries from invocation log.

Tests added/updated:

- Added: `tests/unit/test_tool_chaining.py`
  - Structured gate blocks non-chainable multi-tool turns.
  - Chain metadata propagation for two `TOOL(...)` calls in one turn.
- Updated: `tests/unit/test_repl_parallel_dispatch.py`
  - Added AST call-detection tests (`extract_tool_calls`).
- Updated: `tests/unit/test_tool_registry.py`
  - Added chain metadata + `get_chainable_tools()` coverage.

Validation:

- `pytest -q tests/unit/test_tool_registry.py tests/unit/test_repl_parallel_dispatch.py tests/unit/test_tool_chaining.py` ✅
- `pytest -q tests/unit/test_repl_context.py tests/unit/test_repl_deferred_tools.py tests/unit/test_features.py` ✅

Remaining Phase 2 follow-ups (post-2a):

- Expand `allowed_callers` population policy in `orchestration/tool_registry.yaml` for full per-tool categorization.
- Add end-to-end response/assertion tests for `tool_chains` in API pipeline fixtures.
- Phase 2b dependency-aware dispatch remains pending (2a currently uses sequential `exec()` semantics for non-read-only chains).

### 2026-02-18 Phase 2a Follow-up Completion (Policy Population + Response Contract Tests)

Completed immediately after the core 2a runtime ship:

- `orchestration/tool_registry.yaml`
  - Added explicit `allowed_callers` policy to all 47 tools.
  - Conservative defaults applied:
    - most read/compute/search tools: `["direct", "chain"]`
    - side-effect-heavy tools kept direct-only (e.g. `run_shell`, `write_file`, `archive_extract`)
- Validation check:
  - YAML parse confirms `missing_allowed_callers=0` across all registered tools.

Additional test coverage:

- `tests/unit/test_repl_executor.py`
  - Added `test_tool_chains_grouped_in_response` to verify invocation-log chain grouping in `ChatResponse.tool_chains`.
- `tests/unit/test_api_models_responses.py`
  - Added `tool_chains` default/serialization coverage.

Validation:

- `pytest -n0 -q tests/unit/test_repl_executor.py::TestToolOutputsInAnswer::test_tool_chains_grouped_in_response tests/unit/test_api_models_responses.py tests/unit/test_tool_registry.py tests/unit/test_tool_chaining.py tests/unit/test_repl_parallel_dispatch.py` ✅ (67 passed)

Net status:

- Phase 2a (sequential structured chaining gate + telemetry + caller policy wiring) is now functionally complete.
- Remaining open item is Phase 2b (dependency-aware mixed-tool parallelism), which is explicitly out of 2a scope.

### 2026-02-18 Phase 2b Increment 1 (Dependency-Aware Mode Behind Flag)

Implemented a safe first increment of Phase 2b in structured mode:

- Added `ORCHESTRATOR_TOOL_CHAIN_MODE` support in `REPLEnvironment`:
  - `legacy` (reserved compatibility behavior)
  - `seq` (default, current 2a behavior)
  - `dep` (new dependency-aware execution attempt)
- In `dep` mode, structured multi-tool turns now attempt a dependency-aware path for
  simple top-level tool-call chains:
  - groups independent read-only calls into parallel waves,
  - flushes waves before non-read-only steps,
  - executes non-read-only calls sequentially,
  - preserves chain telemetry (`caller_type/chain_id/chain_index`) because calls still
    route through normal REPL callables (`TOOL`, `run_shell`, etc.).
- Safety fallback:
  - if code is complex/ambiguous (unsupported statement shape, dynamic args, parse issues),
    execution cleanly falls back to existing sequential `exec()` behavior.

Tests:

- `tests/unit/test_tool_chaining.py`
  - `test_dependency_mode_executes_mixed_chain`
  - `test_dependency_mode_falls_back_to_seq_exec_on_non_call_stmt`
- Validation:
  - `pytest -n0 -q tests/unit/test_tool_chaining.py tests/unit/test_repl_parallel_dispatch.py tests/unit/test_repl_executor.py::TestToolOutputsInAnswer::test_tool_chains_grouped_in_response` ✅

Status impact:

- Phase 2b is now started with guarded runtime behavior and fallback semantics.
- Remaining Phase 2b work:
  - richer dependency analysis (beyond top-level simple call shapes),
  - explicit per-wave/step diagnostics in response payload,
  - production tuning + contention benchmarks for `dep` mode.

### 2026-02-18 Phase 2b Increment 2 (Chain Execution Diagnostics in API)

Implemented continuation focused on observability:

- `src/repl_environment/environment.py`
  - Added REPL chain execution diagnostics log:
    - `get_chain_execution_log()`
    - per-chain metadata fields:
      - `mode_requested`
      - `mode_used`
      - `fallback_to_seq`
      - `waves`
      - `steps`
  - Added `_finalize_active_chain_meta()` to ensure metadata is persisted on all
    structured-chain exits (early reject, parallel read-only return, dep return, and seq path).
- `src/api/routes/chat_pipeline/repl_executor.py`
  - Extended `_build_tool_chain_summary(...)` to merge invocation-log groups with
    REPL chain execution diagnostics by `chain_id`.
  - `ChatResponse.tool_chains` now includes mode/wave/fallback diagnostics when available.

Tests:

- Updated `tests/unit/test_tool_chaining.py` to assert dep-mode chain log behavior.
- Updated `tests/unit/test_repl_executor.py` to assert merged `tool_chains` diagnostics.

Validation:

- `pytest -n0 -q tests/unit/test_tool_chaining.py tests/unit/test_repl_executor.py::TestToolOutputsInAnswer::test_tool_chains_grouped_in_response tests/unit/test_repl_parallel_dispatch.py tests/unit/test_tool_registry.py tests/unit/test_api_models_responses.py` ✅ (69 passed)

Status impact:

- Phase 2b now includes both guarded dependency-aware execution and chain-level
  diagnostics surfaced in API responses.

### 2026-02-18 Phase 2 Finalization (COMPLETE)

Phase 2 is now complete.

Closure items completed in this final pass:

- Added dedicated unit coverage files:
  - `tests/unit/test_tool_dependencies.py`
  - `tests/unit/test_allowed_callers.py`
  - `tests/unit/test_chain_audit.py`
- Completed Phase 2b dependency-wave execution path with explicit controls:
  - `ORCHESTRATOR_TOOL_CHAIN_MODE=dep`
  - `ORCHESTRATOR_TOOL_CHAIN_PARALLEL_MUTATIONS=1`
- Extended `tool_chains` diagnostics contract with mode/fallback/wave metadata.
- Added reference documentation:
  - `docs/reference/tool-chaining-patterns.md`
- Added changelog entry documenting final Phase 2 closure.

Validation evidence:

- Targeted unit suite:
  - `pytest -n0 -q tests/unit/test_tool_chaining.py tests/unit/test_tool_dependencies.py tests/unit/test_allowed_callers.py tests/unit/test_chain_audit.py tests/unit/test_repl_executor.py::TestToolOutputsInAnswer::test_tool_chains_grouped_in_response tests/unit/test_repl_parallel_dispatch.py tests/unit/test_tool_registry.py tests/unit/test_api_models_responses.py`
  - Result: **74 passed**.
- Synthetic dep-mode latency probe (same two-run_shell chain):
  - parallel mutations OFF: ~0.417s
  - parallel mutations ON: ~0.210s
  - speedup: ~1.99x

### 2026-02-18 Debugger Rendering Closure

Completed requested debugger UI rendering parity for Phase 2 outputs:

- `src/pipeline_monitor/claude_debugger.py` prompt rendering now includes wave-level `tool_chains` diagnostics (`mode_requested`, `mode_used`, `waves`, `fallback_to_seq`, `parallel_mutations_enabled`, `success`).
- Unit test added: `tests/unit/test_claude_debugger.py::test_prompt_includes_tool_chain_wave_diagnostics`.
- Full debugger unit suite validated: `44 passed`.

## 2026-02-18 Phase 3 Progress Update (Slice 1)

### Scope completed in this slice
- Added `session_id` to `ChatRequest` (`src/api/models/requests.py`) and wired `/chat` REPL path to restore session checkpoint globals when provided (`src/api/routes/chat_pipeline/repl_executor.py`).
- Extended `Checkpoint` with:
  - `user_globals`
  - `variable_lineage`
  - `skipped_user_globals`
  (`src/session/models.py`)
- Extended REPL checkpoint/restore (`src/repl_environment/state.py`):
  - captures JSON-safe user globals only,
  - records lineage metadata (`role`, `value_type`, save timestamp/count),
  - logs skipped non-serializable globals,
  - merges restored globals after `_build_globals()`.
- Extended checkpoint persistence schema and CRUD (`src/session/sqlite_store.py`):
  - additive columns in `checkpoints` table,
  - additive migration for pre-existing DBs,
  - save/load wiring for new fields.
- Extended session resume context formatting (`src/session/models.py`, `src/session/protocol.py`) to include variable summaries from latest checkpoint.
- Added checkpoint globals size controls in `SessionPersister` (`src/session/persister.py`):
  - warning at ~50MB,
  - hard cap at ~100MB,
  - oldest-first eviction with warnings.

### Validation
- `pytest -n0 -q tests/unit/test_api_models_requests.py tests/unit/test_session_models.py tests/unit/test_sqlite_store_extended.py` -> 55 passed
- `pytest -n0 -q tests/unit/test_repl_state_extended.py tests/unit/test_persister.py` -> 55 passed
- `pytest -n0 -q tests/unit/test_repl_executor.py -k "restores_globals_from_session_checkpoint or simple_final_answer"` -> 2 passed
- `pytest -n0 -q tests/unit/test_session_protocol.py` -> 11 passed

### Remaining Phase 3 work
- Add full integration coverage for request1->checkpoint->request2 restore path on `/chat` with real session lifecycle.
- Add explicit API diagnostics payload for restore status (restored count/skipped list) in chat response if desired.
- Optional: add runtime config knobs for checkpoint globals caps (currently constants in `SessionPersister`).

## 2026-02-18 Phase 3 Progress Update (Slice 2)

### Implemented
- Added response-level persistence diagnostics:
  - `ChatResponse.session_persistence` now reports restore/save attempt status, counts, checkpoint id, and errors.
- Extended `/chat` REPL execution to save a session checkpoint at request completion when `session_id` is provided. This enables natural request-to-request persistence without requiring separate explicit checkpoint calls.
- Fixed checkpoint restore compatibility for stored checkpoint payloads that omitted `version` by defaulting restore to v1.

### Tests
- Added unit roundtrip test in `tests/unit/test_repl_executor.py`:
  - request 1 sets globals -> checkpoint saved
  - request 2 restores globals from same `session_id`
- Added restore compatibility regression in `tests/unit/test_repl_state_extended.py` for missing `version`.
- Added response model default coverage for `session_persistence` in `tests/unit/test_api_models_responses.py`.
- Added integration scaffold in `tests/integration/test_chat_pipeline.py` for full `/chat` multi-request restore flow; currently marked skip due reproducible real-mode TestClient hang in this environment.

### Validation
- `pytest -n0 -q tests/unit/test_repl_executor.py -k "cross_request_roundtrip_restores_globals or restores_globals_from_session_checkpoint"` -> 2 passed
- `pytest -n0 -q tests/unit/test_repl_state_extended.py -k "restore_missing_version_defaults_to_v1"` -> 1 passed
- `pytest -n0 -q tests/unit/test_api_models_responses.py` -> 22 passed
- `pytest -n0 -q tests/integration/test_chat_pipeline.py -k "session_restore_roundtrip_repl_globals"` -> skipped (intentional)

## 2026-02-19 Phase 3 Follow-up (Remaining TODOs)

### Completed
- Added centralized configurability for checkpoint globals size caps:
  - `ORCHESTRATOR_SESSION_PERSISTENCE_CHECKPOINT_GLOBALS_WARN_MB`
  - `ORCHESTRATOR_SESSION_PERSISTENCE_CHECKPOINT_GLOBALS_HARD_MB`
- `SessionPersister` now consumes these via `get_config().session_persistence`.

### Blocked/Observed
- The outstanding HTTP integration proof for `/chat` roundtrip remains blocked in this worktree: chat endpoint tests (including pre-existing mock-mode route tests) are hanging in this environment, which appears broader than Phase 3 persistence logic itself.
- Existing deterministic phase coverage remains green at REPL executor/state/model layers (cross-request restore/save behavior verified there).

### Recommended next unblock step
- Re-run the chat endpoint integration set after the parallel agent’s in-progress API/middleware changes are committed and the worktree is stable; then unskip/validate the `/chat` session roundtrip test.

## 2026-02-18 Phase 3 Closure Update (HTTP Roundtrip Unblocked)

### Root cause and fix
- Root cause for the persistent `/chat` integration hang was an unconditional threadpool hop in `_handle_chat()`:
  - `_execute_delegated` was always dispatched via `asyncio.to_thread(...)` even when execution mode was not `delegated`.
  - In non-delegated flows (including forced `repl`), this created unnecessary dependency on threadpool behavior and caused intermittent hangs in test harnesses.
- Fix shipped in `src/api/routes/chat.py`:
  - `_execute_delegated` thread dispatch is now mode-gated and runs only when `execution_mode == "delegated"`.

### Phase 3 integration status
- The full `/chat` cross-request persistence proof is now unblocked and passing.
- `tests/integration/test_chat_pipeline.py::TestChatEndpoint::test_session_restore_roundtrip_repl_globals` is no longer skipped.
- Test now uses HTTP-level async transport and a deterministic in-memory session store fixture for stable roundtrip verification.

### Additional cleanup
- Replaced new UTC-naive timestamps in touched persistence paths with timezone-aware UTC:
  - `src/api/routes/chat_pipeline/repl_executor.py`
  - `src/session/persister.py`

### Validation
- `pytest -n0 -q tests/integration/test_chat_pipeline.py::TestChatEndpoint::test_session_restore_roundtrip_repl_globals` -> 1 passed
- `pytest -n0 -q tests/unit/test_persister.py` -> 28 passed

## 2026-02-19 Final Closure Reconciliation

This section reconciles the original planning checklists with shipped behavior and supersedes unchecked historical planning boxes in Sections 5.1/5.2/5.3.

### Phase closure status

- [x] Phase 1 complete: deferred tool results shipped, tested, and documented.
- [x] Phase 2 complete: `allowed_callers`, chain execution controls, and `tool_chains` diagnostics shipped with tests/docs.
- [x] Phase 3 complete: cross-request persistence (`session_id`, checkpoint globals/lineage, restore/save diagnostics) shipped and HTTP roundtrip integration proof passing.

### Documentation closure status

- [x] Chapter published: `docs/chapters/29-programmatic-tool-chaining.md`.
- [x] Existing chapters updated where integration points live (`10`, `11`, `20`, `22`, `26`).
- [x] Reference guide present: `docs/reference/tool-chaining-patterns.md`.
- [x] Changelog updates captured in `CHANGELOG.md`.
- [x] Roadmap reference normalized to `handoffs/active/rlm-orchestrator-roadmap.md` (consolidated roadmap source).

### Closure action

- [x] Handoff ready for archival lifecycle move from `handoffs/active/` to `handoffs/archived/`.

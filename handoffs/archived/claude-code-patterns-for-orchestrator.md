# Handoff: Claude Code Execution Patterns → Local Orchestrator

**Created**: 2026-02-20
**Status**: Active
**Origin**: Analysis of Claude Code's post-plan-mode execution patterns
**Goal**: Port task tracking, context discipline, and working memory patterns into local orchestrator for Qwen models

---

## Core Insight

Claude Code (Opus) exhibits emergent execution discipline from soft system prompt instructions:
- Read files before editing (instruction: "do not propose changes to code you haven't read")
- Create task lists for multi-step work (instruction: "use TaskCreate proactively for 3+ steps")
- Sequential gather → understand → plan → act flow (emerges from model capability)

**Qwen models cannot reliably replicate this from instructions alone.** These patterns must become **hard scaffolding** — enforced by graph structure, tool contracts, and MemRL nudging.

**Design principle**: Learn anti-patterns (what fails) and nudge away from them. Never prescribe rigid required sequences — real tasks are non-linear.

---

## Existing Architecture (What We're Building On)

### Already working

| Component | Location | What it does |
|-----------|----------|-------------|
| `_workspace_prompt_block()` | `helpers.py:84-108` | Injects per-turn summary: objective, constraints, last 3 commitments/decisions/questions |
| `workspace_state` | `state.py:135-152` | Shared blackboard across graph nodes (proposals/commitments/decisions/questions) |
| `_update_workspace_from_turn()` | `helpers.py:111-152` | Updates workspace after each turn, bounded to 12 items per category |
| `_select_and_broadcast_workspace_delta()` | `helpers.py:154-217` | Priority+recency selection, top 2 per broadcast, owner-level conflict resolution |
| Injection point | `helpers.py:869` | `prompt += "\n\n" + _workspace_prompt_block(state)` — every turn |
| `FailureGraph` | `failure_graph.py` | Kuzu graph: FailureMode→Symptom→Mitigation with PRECEDED_BY chains |
| `HypothesisGraph` | `hypothesis_graph.py` | Kuzu graph: Hypothesis→Evidence with asymptotic confidence updates |
| `QScorer` | `q_scorer.py` | Multi-dimensional reward: latency, quality gap, memory tier, delegation credit |
| `_record_failure()` | `helpers.py:300-315` | Records failures with symptoms + severity in FailureGraph |
| `_record_mitigation()` | `helpers.py:319-333` | Records successful escalations in FailureGraph |
| `_add_evidence()` | `helpers.py:336-351` | Records outcome evidence in HypothesisGraph |
| Checkpoint system | `session/` | Persists user_globals, artifacts, exploration_events, findings every 5 turns |
| `findings_buffer` | `repl_environment/state.py` | Accumulates key findings across tool calls |
| `research_context` | `research_context.py` | Tool call lineage tree with cross-reference detection |
| Tool registry | `tool_registry.py` + `tool_registry.yaml` | Role-based access, GBNF grammar gen, invocation logging, side effect tracking |
| REPL tools | `repl_environment/context.py` | `TOOL()`, `CALL()`, `list_tools()` dispatch in REPL namespace |

### FailureGraph query API (directly usable for anti-pattern nudging)

| Method | Signature | Returns |
|--------|-----------|---------|
| `find_matching_failures` | `(symptoms: List[str]) -> List[FailureMode]` | Failures matching symptoms, sorted by match count + recency |
| `get_effective_mitigations` | `(symptoms: List[str]) -> List[{action, success_rate}]` | Mitigations that worked, excluding recurrences, sorted by success rate |
| `get_failure_risk` | `(action: str) -> float` | Sigmoid-scaled risk 0.0-1.0 (uses failure count + 2x recurrence weight) |
| `get_failure_chain` | `(failure_id: str, depth: int) -> List[FailureMode]` | Causal chain via PRECEDED_BY edges, oldest first |
| `record_failure` | `(memory_id, symptoms, description, severity, previous_failure_id)` | Deduplicates by symptom overlap, links to episodic memory |
| `record_mitigation` | `(failure_id, action, worked: bool)` | Tracks attempt/success counts, links RECURRED_AFTER on failure |

### HypothesisGraph query API (usable for confidence-based nudging)

| Method | Signature | Returns |
|--------|-----------|---------|
| `get_confidence` | `(action: str, task_type: str) -> float` | 0.0-1.0 confidence, 0.5 for unknown |
| `get_low_confidence_warnings` | `(action, task_type, threshold=0.2) -> List[str]` | Warnings with cited contradicting evidence |
| `get_or_create_hypothesis` | `(action, task_type, memory_id) -> str` | Creates claim `"action\|task_type"` if not exists |
| `add_evidence` | `(hypothesis_id, outcome: "success"\|"failure", source) -> float` | Updates confidence asymptotically, returns new value |

### Known bugs in current integration

**`_record_mitigation()` in helpers.py:319-333** calls `fg.record_mitigation(memory_id=..., description=...)` but actual signature is `(failure_id, action, worked)`. This call silently fails or crashes. Must be fixed.

**`_add_evidence()` in helpers.py:336-351** passes `evidence=` and `delta=` but actual signature expects `(hypothesis_id, outcome, source)`. Same issue — wrong kwargs.

These bugs mean **FailureGraph and HypothesisGraph are recording failures but mitigations and evidence are not being stored correctly.** Fix these first before building on top.

---

## Workstream 1: Task Tracking Tools (REPL-integrated)

### What
Add `task_create`, `task_update`, `task_list` as registered tools invocable via `TOOL()` in REPL.

### Why
- Forces models to decompose work before acting
- Provides observability (where did it stall? what did it skip?)
- Creates natural checkpoints for progress injection
- Task completion events become learning signals for MemRL

### Design

**Backend**: In-memory on TaskState (per-request lifecycle). Task completions logged to ProgressLogger for cross-request learning.

```python
# orchestration/tools/task_management.py

@dataclass
class ManagedTask:
    id: str
    subject: str              # imperative: "Fix the auth bug"
    description: str          # detailed acceptance criteria
    active_form: str          # present continuous: "Fixing the auth bug"
    status: Literal["pending", "in_progress", "completed", "deleted"]
    created_at: str
    completed_at: str | None
    blocked_by: list[str]     # task IDs
    metadata: dict[str, Any]

class TaskManager:
    """In-request task tracking. Lives on TaskState."""

    def create(self, subject, description, active_form=None, metadata=None) -> ManagedTask: ...
    def update(self, task_id, **kwargs) -> ManagedTask: ...
    def list_all(self) -> list[ManagedTask]: ...
    def get(self, task_id) -> ManagedTask: ...
    def has_tasks(self) -> bool: ...
    def summary_block(self) -> str:
        """Compact markdown for context injection into _workspace_prompt_block()."""
        ...
```

**Tool Registry** (`orchestration/tool_registry.yaml`) — follows existing pattern:

```yaml
task_create:
  category: specialized
  description: "Create a task to track a unit of work. Use for multi-step plans."
  parameters:
    subject: {type: string, required: true, description: "Brief imperative title"}
    description: {type: string, required: true, description: "What needs to be done"}
    active_form: {type: string, required: false, description: "Present continuous for status display"}
  returns: {type: object, fields: {id: string, subject: string, status: string}}
  implementation:
    type: python
    module: orchestration.tools.task_management
    function: tool_task_create
  allowed_callers: [direct]
  side_effects: [SYSTEM_STATE]

task_update:
  category: specialized
  description: "Update task status. Mark in_progress before starting, completed when done."
  parameters:
    task_id: {type: string, required: true}
    status: {type: string, required: false, enum: [pending, in_progress, completed, deleted]}
  returns: {type: object, fields: {id: string, status: string}}
  implementation:
    type: python
    module: orchestration.tools.task_management
    function: tool_task_update
  allowed_callers: [direct]
  side_effects: [SYSTEM_STATE]

task_list:
  category: specialized
  description: "List all tasks with status. Check this after completing a task."
  parameters: {}
  returns: {type: array}
  implementation:
    type: python
    module: orchestration.tools.task_management
    function: tool_task_list
  allowed_callers: [direct]
  side_effects: [READ_ONLY]
```

**Graph integration**:

```python
# src/graph/state.py — add to TaskState
task_manager: TaskManager = field(default_factory=TaskManager)
```

TaskManager injected into REPL namespace alongside existing `TOOL()`, `CALL()` functions.

### Auto-create from TaskIR

When TaskIR has >1 step, auto-populate tasks (don't rely on model to decompose):

```python
# src/graph/helpers.py — at turn 0
if state.turns == 0 and len(state.task_ir.get("steps", [])) > 1:
    for i, step in enumerate(state.task_ir["steps"]):
        state.task_manager.create(
            subject=step["description"],
            description=step.get("details", ""),
            active_form=step.get("active_form", f"Working on step {i+1}")
        )
```

Model can still add sub-tasks via `TOOL("task_create", ...)`.

### Observability hooks

On `task_update(status="completed")`:
1. Log to `ProgressLogger` (feeds QScorer)
2. Update `workspace_state["commitments"]` (becomes visible in broadcast)

On `task_update(status="in_progress")`:
1. Update `workspace_state["objective"]` to current task subject
2. Start timing (for cost penalty computation in QScorer)

---

## Workstream 2: Auto-Context Injection (Read-Before-Write)

### What
Automatically read files referenced in TaskIR/plan into context before the model's turn.

### Why
Eliminates reliance on model discipline for "read first". Opus does this naturally; Qwen won't.

### Design

```python
# src/graph/helpers.py — new function

async def _auto_gather_context(ctx: GraphContext, files: list[str]) -> str:
    """Read referenced files into context. Called before _execute_turn for editing tasks."""
    gathered = []
    for fpath in files[:10]:  # Budget: max 10 files
        if fpath in ctx.state.gathered_files:
            continue
        try:
            content = await ctx.deps.repl.peek(fpath, max_lines=200)
            gathered.append(f"### {fpath}\n```\n{content}\n```")
            ctx.state.gathered_files.add(fpath)
        except Exception:
            gathered.append(f"### {fpath}\n[Could not read]")
    return "\n\n".join(gathered)
```

**File sources** (in priority order):
1. `TaskIR.steps[i].files` (requires TaskIR schema extension)
2. Previous turn's grep/peek results (already tracked in `exploration_events`)
3. Task metadata from `task_create` descriptions (regex file path extraction)

**State tracking**: Add `gathered_files: set[str] = field(default_factory=set)` to `TaskState`.

**Injection**: Prepend as `<context>` block at helpers.py:869, before `_workspace_prompt_block()`.

### Budget
- Max 10 files per gather, 200 lines per file
- Skip already-gathered files (dedup via `state.gathered_files`)
- Total token estimate: ~2000 tokens max (10 files × 200 lines × ~1 token/line avg)

---

## Workstream 3: Progress Scratchpad (Extend Workspace Block)

### What
Extend the existing `_workspace_prompt_block()` with task progress and intra-role continuity.

### Why
The workspace block already injects per-turn (helpers.py:869). It handles cross-role coordination (what other roles committed/asked). What's missing: task-level progress ("you completed steps 1-3, step 4 is in progress").

### Design

Extend `_workspace_prompt_block()` rather than creating a parallel injection:

```python
# src/graph/helpers.py — modify _workspace_prompt_block()

def _workspace_prompt_block(state: TaskState) -> str:
    """Build a compact workspace block to keep specialists aligned."""
    ws = state.workspace_state or {}
    objective = ws.get("objective") or state.prompt[:240]
    # ... existing code ...

    # NEW: Task progress section
    if state.task_manager.has_tasks():
        lines.append("- task_progress:")
        for t in state.task_manager.list_all():
            icon = {"completed": "✓", "in_progress": "→", "pending": "○"}.get(t.status, "?")
            lines.append(f"    {icon} {t.subject}")

    # NEW: Anti-pattern warning (from FailureGraph, see Workstream 4)
    if hasattr(state, '_anti_pattern_warning') and state._anti_pattern_warning:
        lines.append(f"- warning: {state._anti_pattern_warning}")

    return "\n".join(lines)
```

**Token budget**: Task list adds ~5-10 tokens per task. With typical 3-8 tasks, that's 15-80 extra tokens — well within budget.

### What NOT to do
- Don't create a separate injection point — workspace block is already injected every turn
- Don't duplicate findings_buffer or research_context here — they serve different purposes
- Don't inject full task descriptions — subjects only, model can `TOOL("task_get")` for details

---

## Workstream 4: MemRL Anti-Pattern Nudging

### What
Use the **existing** FailureGraph to detect when the model is repeating known failure patterns, and inject warnings with historically successful alternatives.

### Why
- FailureGraph already records failures with symptoms and tracks mitigations with success rates
- The query API already exists: `find_matching_failures()`, `get_effective_mitigations()`, `get_failure_risk()`
- Missing piece: nobody reads the graph before a turn — it's write-only today

### Prerequisites

**Fix helpers.py signature bugs first:**

```python
# CURRENT (broken):
def _record_mitigation(ctx, from_role, to_role):
    fg.record_mitigation(
        memory_id=ctx.state.task_id,                    # wrong: expects failure_id
        description=f"Escalation from {from_role}...",  # wrong: expects action
    )

# FIXED:
def _record_mitigation(ctx, from_role, to_role, failure_id: str | None = None):
    fg.record_mitigation(
        failure_id=failure_id or ctx.state.last_failure_id,
        action=f"escalate:{from_role}->{to_role}",
        worked=True,
    )
```

```python
# CURRENT (broken):
def _add_evidence(ctx, outcome, delta):
    hg.add_evidence(
        hypothesis_id=ctx.state.task_id,
        evidence=f"{ctx.state.current_role}:{outcome}",  # wrong: expects outcome
        delta=delta,                                       # wrong: expects source
    )

# FIXED:
def _add_evidence(ctx, outcome: str):
    hg.add_evidence(
        hypothesis_id=ctx.state.task_id,
        outcome=outcome,  # "success" or "failure"
        source=f"{ctx.state.current_role}:turn_{ctx.state.turns}",
    )
```

Also need: `state.last_failure_id` to link mitigations to their triggering failure.

### Design

**New function — query FailureGraph before each turn:**

```python
# src/graph/helpers.py

def _check_anti_pattern(ctx: Ctx) -> str | None:
    """Check if recent behavior matches known failure patterns.

    Uses existing FailureGraph API:
    - find_matching_failures(symptoms) → matches by symptom overlap
    - get_effective_mitigations(symptoms) → what worked before
    - get_failure_risk(action) → sigmoid risk score
    """
    fg = ctx.deps.failure_graph
    if fg is None:
        return None

    # Build symptoms from recent actions
    symptoms = []
    if ctx.state.last_error:
        symptoms.append(ctx.state.last_error[:100])
    if hasattr(ctx.state, 'error_category') and ctx.state.error_category:
        symptoms.append(ctx.state.error_category.value)
    # Add role + consecutive failure count as symptom
    if ctx.state.consecutive_failures >= 2:
        symptoms.append(f"{ctx.state.current_role}:consecutive_fail_{ctx.state.consecutive_failures}")

    if not symptoms:
        return None

    try:
        matches = fg.find_matching_failures(symptoms)
        if not matches:
            return None

        best = matches[0]
        # Only warn on recurring patterns (severity >= 3 means 2+ consecutive failures)
        if best.severity < 3:
            return None

        # Get what worked before
        mitigations = fg.get_effective_mitigations(symptoms)
        if mitigations:
            best_mitigation = mitigations[0]
            return (
                f"Similar failure pattern seen before (severity {best.severity}). "
                f"Previously successful: {best_mitigation['action']} "
                f"(success rate: {best_mitigation['success_rate']:.0%})"
            )
        else:
            return f"Recurring failure pattern: {best.description[:120]}"
    except Exception as exc:
        log.debug("anti-pattern check failed: %s", exc)
        return None
```

**Integration — inject into workspace block:**

```python
# In the turn execution path, before prompt building:
warning = _check_anti_pattern(ctx)
if warning:
    ctx.state._anti_pattern_warning = warning
# _workspace_prompt_block() picks it up (see Workstream 3)
```

**Also use `get_failure_risk()` for routing decisions:**

```python
# In routing/escalation logic:
risk = fg.get_failure_risk(f"{role}:{task_type}")
if risk > 0.7:
    # High risk — consider alternative route or add extra context
    ...
```

### What this does NOT do
- Does NOT block execution (no gates)
- Does NOT prescribe sequences (no "must gather before execute")
- Does NOT require new Kuzu schema (uses existing FailureMode/Symptom/Mitigation)
- The model sees the warning and can act on it or ignore it

---

## Workstream 5: Tool-Call Budgeting

### What
Per-task limits on tool calls to prevent loops (Qwen's main failure mode).

### Why
Opus self-regulates tool usage. Qwen either under-explores (0 reads) or loops (15 retries).

### Design

```python
# orchestration/tools/task_management.py — extend ManagedTask

@dataclass
class ToolBudget:
    read_calls: int = 5       # peek, grep
    write_calls: int = 3      # edit, create
    exec_calls: int = 2       # run, test
    llm_calls: int = 1        # delegation

    def can_use(self, category: str) -> bool: ...
    def consume(self, category: str) -> bool: ...
    def remaining_summary(self) -> str: ...
```

**Enforcement in existing tool invocation path:**

```python
# src/repl_environment/context.py — in _invoke_tool (existing function)

budget = state.task_manager.current_task_budget()
if budget and not budget.can_use(tool.category):
    return ToolOutput(
        error=f"Budget exhausted for {tool.category}. "
        f"Remaining: {budget.remaining_summary()}. "
        f"Mark task complete or adjust approach."
    )
budget.consume(tool.category)
```

**Default budgets** (hardcoded initially, learnable via QScorer later):

| Task Type | Reads | Writes | Execs | LLM Calls |
|-----------|-------|--------|-------|-----------|
| Bug fix | 5 | 3 | 3 | 1 |
| Feature | 8 | 5 | 2 | 1 |
| Refactor | 10 | 8 | 2 | 0 |
| Research | 15 | 0 | 0 | 2 |

**Override**: `TOOL("budget_override", category="read", reason="need more context")` — adds 3 to that category. Logged for MemRL learning (frequent overrides = budget too low).

---

## Implementation Priority & Dependencies

```
    ┌─────────────────────────────┐
    │  0. Fix helpers.py bugs     │  ← _record_mitigation + _add_evidence signatures
    │     (10 min, prerequisite)  │
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │  1. Task Tracking Tools     │  ← Foundation: everything else builds on this
    │     (REPL-integrated)       │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┼──────────────────────┐
    │              │                       │
    ▼              ▼                       ▼
┌────────┐  ┌──────────┐  ┌──────────────────┐
│ 2. Auto│  │ 3. Extend│  │ 5. Tool-Call     │
│ Context│  │ Workspace│  │    Budgeting     │
│ Inject │  │ Block    │  └──────────────────┘
└────────┘  └────┬─────┘
                 │
    ┌────────────▼────────────┐
    │ 4. Anti-Pattern Nudging │  ← Query existing FailureGraph,
    │    (FailureGraph query) │    inject into workspace block
    └─────────────────────────┘
```

### Estimated effort

| # | Workstream | New files | Modified files | Complexity |
|---|-----------|-----------|---------------|------------|
| 0 | Fix signature bugs | 0 | `helpers.py` | **Trivial** |
| 1 | Task tracking tools | `orchestration/tools/task_management.py` | `tool_registry.yaml`, `state.py`, `context.py` | Medium |
| 2 | Auto-context injection | 0 | `helpers.py`, `state.py` | Low |
| 3 | Extend workspace block | 0 | `helpers.py` | Low |
| 4 | Anti-pattern nudging | 0 | `helpers.py` | **Low** (FailureGraph API exists) |
| 5 | Tool-call budgeting | 0 (extends task_management.py) | `context.py` | Medium |

### Key realization: Workstream 4 is smaller than originally scoped

The entire FailureGraph with `find_matching_failures()`, `get_effective_mitigations()`, `get_failure_risk()`, and `get_failure_chain()` already exists and has been recording data. Workstream 4 is just **~30 lines of query + prompt injection** in helpers.py. No new Kuzu schema, no new graph modules, no hypothesis tracking needed for the core anti-pattern nudge.

The hypothesis graph can optionally track sequence confidence later, but the failure graph alone is sufficient for "don't repeat what failed before."

---

## Files Summary

### Create
| File | Purpose |
|------|---------|
| `orchestration/tools/task_management.py` | TaskManager class + REPL tool handlers |

### Modify
| File | Changes |
|------|---------|
| `src/graph/helpers.py` | Fix `_record_mitigation`/`_add_evidence` signatures; add `_check_anti_pattern()`, `_auto_gather_context()`, extend `_workspace_prompt_block()` |
| `src/graph/state.py` | Add `task_manager`, `gathered_files`, `last_failure_id`, `_anti_pattern_warning` to TaskState |
| `orchestration/tool_registry.yaml` | Add task_create, task_update, task_list, budget_override tool definitions |
| `src/repl_environment/context.py` | Budget enforcement in `_invoke_tool` |

### No changes needed
| File | Why |
|------|-----|
| `orchestration/repl_memory/failure_graph.py` | Query API already sufficient |
| `orchestration/repl_memory/hypothesis_graph.py` | Optional future extension, not needed for MVP |
| `orchestration/repl_memory/q_scorer.py` | Task completion signals use existing ProgressLogger path |

---

## Open Questions

1. **Auto-create tasks from TaskIR vs. force model to decompose?** Recommend: auto-create from TaskIR steps, allow model to add sub-tasks. Qwen can't reliably decompose.

2. **Progress injection token budget?** Task subjects in workspace block: ~5-10 tokens/task. Anti-pattern warning: ~30 tokens. Total overhead: <100 tokens. Acceptable.

3. **Budget override abuse?** Model could spam budget_override to circumvent limits. Mitigation: max 2 overrides per task, logged for MemRL. Frequent overrides → QScorer adjusts default budget upward for that task type.

4. **When to query FailureGraph?** Every turn is cheap (single Kuzu query). Only inject warning when severity >= 3 AND consecutive_failures >= 2 to avoid noise.

5. **Task completion → MemRL feedback loop?** Task decomposition quality (did tasks match actual work?) is a learnable signal. Log task creation patterns + outcomes to episodic store for future routing suggestions.

# Canvas as Orchestration Control Plane

**Status**: Architecture Document (Revised)
**Created**: 2026-02-05
**Revised**: 2026-02-05
**Author**: Claude (with Daniele)
**Prerequisites**: `src/canvas_export.py`, `src/canvas_import.py` (committed 7147720)

---

## Executive Summary

Canvas provides **spatial interfaces** for capabilities that text commands can't easily replicate:

| Mode | Scope | Persistence | Purpose |
|------|-------|-------------|---------|
| **Profile Canvas** | User identity | Long-term | Personalize orchestrator behavior |
| **Plan Canvas** | Task execution | Per-task | Edit architect's TaskIR DAG |
| ~~Steering Canvas~~ | ~~Routing decisions~~ | ~~Session~~ | **Replaced by text commands** |

**Design decision**: Steering (route weight adjustment) is better served by simple text commands than canvas manipulation. Canvas is reserved for:
1. **Profile** — Complex preference graphs that persist across sessions
2. **Planning** — Visual TaskIR DAG editing that text can't replicate

**Core insight**: Use canvas where spatial arrangement adds value (relationships, groupings, complex structures). Use text where it's simpler (single overrides).

---

## Part 1: Architecture Overview

### 1.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OBSIDIAN CANVAS UI                                │
│                                                                             │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐           │
│  │ PROFILE       │      │ STEERING      │      │ PLAN          │           │
│  │ user_profile  │      │ steering      │      │ task_{id}     │           │
│  │ .canvas       │      │ .canvas       │      │ .canvas       │           │
│  │               │      │               │      │               │           │
│  │ • Expertise   │      │ • Hypotheses  │      │ • TaskIR DAG  │           │
│  │ • Preferences │      │ • Failures    │      │ • Steps       │           │
│  │ • Goals       │      │ • Confidence  │      │ • Dependencies│           │
│  │ • Projects    │      │ • Vetos       │      │ • Actors      │           │
│  └───────┬───────┘      └───────┬───────┘      └───────┬───────┘           │
│          │                      │                      │                    │
└──────────┼──────────────────────┼──────────────────────┼────────────────────┘
           │                      │                      │
           ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        CANVAS CONSTRAINT ENGINE                              │
│                                                                              │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐     │
│  │ ProfileConstraints │  │ SteeringConstraints│  │ PlanConstraints    │     │
│  │                    │  │                    │  │                    │     │
│  │ • expertise_areas  │  │ • priority_nodes   │  │ • step_order       │     │
│  │ • preferences      │  │ • removed_nodes    │  │ • actor_overrides  │     │
│  │ • communication    │  │ • position_weights │  │ • new_dependencies │     │
│  │ • current_context  │  │ • veto_roles       │  │ • added_steps      │     │
│  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘     │
│            │                       │                       │                 │
└────────────┼───────────────────────┼───────────────────────┼─────────────────┘
             │                       │                       │
             ▼                       ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYERS                                 │
│                                                                              │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐            │
│  │ SYSTEM PROMPT   │   │ ROUTING         │   │ TASK EXECUTION  │            │
│  │ INJECTION       │   │ DECISIONS       │   │                 │            │
│  │                 │   │                 │   │                 │            │
│  │ • Persona       │   │ • Role select   │   │ • Wave compute  │            │
│  │ • Tone          │   │ • Confidence    │   │ • Step execute  │            │
│  │ • Detail level  │   │ • Failure veto  │   │ • Actor assign  │            │
│  │ • Focus areas   │   │ • MemRL weight  │   │ • Dependency    │            │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘            │
│                                                                              │
│  Affected files:       Affected files:       Affected files:                │
│  • prompt_builders/    • chat_routing.py     • parallel_step_executor.py    │
│  • llm_primitives.py   • routing.py          • proactive_delegation/        │
│  • frontdoor prompts   • escalation.py       • delegator.py                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
User edits canvas in Obsidian
            │
            ▼
    ┌───────────────┐
    │ import_canvas │  MCP tool or API call
    │ _edits()      │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ parse_canvas  │  Existing: src/canvas_import.py
    │ ()            │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ extract_      │  Existing: computes position weights,
    │ constraints() │  detects additions/deletions/modifications
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Constraint    │  NEW: Route to appropriate constraint type
    │ Router        │  based on canvas filename or metadata
    └───────┬───────┘
            │
    ┌───────┴───────┬───────────────┐
    │               │               │
    ▼               ▼               ▼
Profile         Steering        Plan
Constraints     Constraints     Constraints
    │               │               │
    ▼               ▼               ▼
Store in        Store in        Apply to
AppState.       AppState.       current
profile         canvas_         TaskIR
                constraints
```

---

## Part 2: Profile Canvas Mode

### 2.1 Purpose

Long-term user model that **personalizes orchestrator behavior** across all sessions.

### 2.2 Node Types

| Node Type | Example Content | Effect on Orchestrator |
|-----------|-----------------|------------------------|
| **Expertise** | "Distributed systems expert" | Skip basic explanations, use advanced terminology |
| **Preference** | "Performance > Readability" | Coder optimizes for speed, architect favors efficient designs |
| **Communication** | "Concise responses" | Reduce verbosity, minimize hedging |
| **Goal** | "Ship MVP fast" | Favor simpler solutions, reduce scope creep |
| **Anti-preference** | "No emojis" | Hard constraint on output formatting |
| **Current Project** | "EPYC inference optimization" | Always-on context injection |

### 2.3 Spatial Semantics

| Position | Meaning |
|----------|---------|
| Center | Highest priority—always apply |
| Inner ring | High priority—apply unless conflicting |
| Outer ring | Low priority—apply when relevant |
| Edge (deleted) | Vetoed—never apply |

| Edge | Meaning |
|------|---------|
| A → B | "When A applies, also consider B" |
| A ↔ B | "A and B are related contexts" |

### 2.4 Data Structure

```python
@dataclass
class ProfileConstraints:
    """Long-term user profile extracted from canvas."""

    # Expertise areas (affects explanation depth)
    expertise: list[str]  # ["distributed_systems", "llm_inference", "python"]
    expertise_weights: dict[str, float]  # Position-based priority

    # Preferences (affects output style)
    preferences: dict[str, str]  # {"code_style": "performance", "verbosity": "concise"}
    preference_weights: dict[str, float]

    # Communication style
    communication: dict[str, Any]  # {"tone": "direct", "emojis": False, "hedging": False}

    # Current context (always injected)
    current_projects: list[str]  # ["EPYC optimization", "orchestration system"]
    current_focus: str | None  # Most central project node

    # Hard constraints (vetoes)
    never: list[str]  # ["use_emojis", "apologize_excessively"]

    # Contextual relationships (edges)
    context_triggers: dict[str, list[str]]  # {"distributed_systems": ["performance", "concurrency"]}
```

### 2.5 Integration Points

**File: `src/prompt_builders/system_prompt.py`** (or equivalent)

```python
def build_system_prompt(
    base_prompt: str,
    profile: ProfileConstraints | None = None,
) -> str:
    """Inject profile constraints into system prompt."""
    if not profile:
        return base_prompt

    sections = [base_prompt]

    # Expertise acknowledgment
    if profile.expertise:
        top_expertise = sorted(
            profile.expertise,
            key=lambda x: profile.expertise_weights.get(x, 0),
            reverse=True
        )[:3]
        sections.append(f"User expertise: {', '.join(top_expertise)}. Adjust explanations accordingly.")

    # Preference injection
    if profile.preferences:
        prefs = [f"{k}: {v}" for k, v in profile.preferences.items()]
        sections.append(f"User preferences: {'; '.join(prefs)}.")

    # Communication style
    if profile.communication:
        comm = profile.communication
        if comm.get("tone"):
            sections.append(f"Communication tone: {comm['tone']}.")
        if comm.get("emojis") is False:
            sections.append("Do not use emojis.")

    # Current context
    if profile.current_projects:
        sections.append(f"Current project context: {profile.current_focus or profile.current_projects[0]}.")

    # Hard constraints
    if profile.never:
        sections.append(f"Never: {', '.join(profile.never)}.")

    return "\n\n".join(sections)
```

**File: `src/api/state.py`**

```python
@dataclass
class AppState:
    # ... existing fields ...

    # NEW: User profile (loaded at session start)
    profile_constraints: ProfileConstraints | None = None
    profile_canvas_path: str | None = None  # For reload detection
```

### 2.6 Canvas File Location

```
logs/canvases/
├── user_profile.canvas      # Long-term profile (checked into dotfiles or persisted)
├── steering.canvas          # Session steering (ephemeral)
└── task_{uuid}.canvas       # Per-task plans (ephemeral)
```

### 2.7 Export Function

```python
def export_profile_canvas(
    profile: ProfileConstraints | None = None,
    output_path: str = "logs/canvases/user_profile.canvas",
) -> str:
    """Export user profile as canvas, or create template if none exists."""

    nodes = []
    edges = []

    # Template nodes if no profile
    if not profile:
        template_nodes = [
            {"id": "expertise_1", "text": "**Expertise**\n\nYour domain expertise", "x": 0, "y": -200},
            {"id": "pref_1", "text": "**Preference**\n\nCode style preference", "x": 200, "y": 0},
            {"id": "comm_1", "text": "**Communication**\n\nResponse style", "x": -200, "y": 0},
            {"id": "project_1", "text": "**Current Project**\n\nWhat you're working on", "x": 0, "y": 200},
        ]
        # ... create canvas with template
    else:
        # Export actual profile nodes with positions based on weights
        # ... (similar to existing export_hypothesis_graph pattern)

    return output_path
```

---

## Part 3: Steering via Text Commands (Simplified)

### 3.1 Rationale

Canvas-based steering adds friction without proportional benefit:
- Simple override: "use coder for this" → text is easier
- Batch adjustment: rare enough that text commands suffice
- Debugging: `show_routing_state` command can dump current beliefs

Canvas export of hypothesis/failure graphs remains available for **visibility** (debugging why routing went wrong), but editing is done via text commands.

### 3.2 Text Commands for Steering

**MCP Tools (or chat commands):**

```python
# Override for current request only
force_role(role="coder_primary")

# Persistent preference (session-scoped)
prefer_role(role="coder_primary", task_type="coding", strength="strong")
# strength: "weak" (tiebreaker), "strong" (override), "always" (force)

# Veto a role
veto_role(role="frontdoor", task_type="coding", reason="too generic")

# Show current routing state (debugging)
show_routing_state()
# Returns: hypothesis confidences, failure risks, active preferences

# Clear session preferences
clear_routing_preferences()
```

### 3.3 Data Structure

```python
@dataclass
class RoutingPreference:
    """Text-command-based routing preference."""
    role: str
    task_type: str | None  # None = all tasks
    strength: Literal["weak", "strong", "always"]
    reason: str | None
    created_at: datetime

@dataclass
class SteeringState:
    """Session-scoped steering preferences from text commands."""
    preferences: list[RoutingPreference]
    vetos: list[tuple[str, str | None]]  # (role, task_type)
```

### 3.4 Integration Points

**File: `src/api/state.py`**

```python
@dataclass
class AppState:
    # ... existing ...
    steering_state: SteeringState | None = None  # Text-based preferences
```

**File: `src/api/routes/chat_routing.py`**

```python
def _apply_steering_preferences(
    confidences: dict[str, float],
    task_type: str,
    steering: SteeringState | None,
) -> tuple[dict[str, float], dict]:
    """Apply text-based steering preferences."""
    if not steering:
        return confidences, {}

    meta = {}

    # Apply vetos first
    for role, veto_task_type in steering.vetos:
        if veto_task_type is None or veto_task_type == task_type:
            confidences[role] = 0.0
            meta["vetoed"] = role

    # Apply preferences
    for pref in steering.preferences:
        if pref.task_type is None or pref.task_type == task_type:
            if pref.strength == "always":
                return {pref.role: 1.0}, {"forced": pref.role}
            elif pref.strength == "strong":
                confidences[pref.role] = min(1.0, confidences.get(pref.role, 0) + 0.4)
            else:  # weak
                confidences[pref.role] = min(1.0, confidences.get(pref.role, 0) + 0.1)

    return confidences, meta
```

### 3.5 Canvas Export Remains (Read-Only)

The existing `export_hypothesis_graph()` and `export_failure_graph()` remain for **debugging/visibility**:

```
User: "Why did it route to frontdoor?"
→ export_reasoning_canvas(graph_type="hypothesis")
→ User sees confidence values in Obsidian
→ User understands: "Ah, coder has 0.3 confidence from past failures"
→ User: "prefer_role coder_primary for coding tasks"
```

Canvas = visibility. Text = control.

---

## Part 4: Plan Canvas Mode

### 4.1 Purpose

Per-task visualization and editing of **TaskIR DAG** from architect decomposition.

### 4.2 Current State of Multi-Step Planning

| Component | Status | Location |
|-----------|--------|----------|
| TaskIR schema with DAG | ✅ Done | `orchestration/task_ir.schema.json` |
| Wave-based parallel executor | ✅ Done | `src/parallel_step_executor.py` |
| Complexity classifier | ✅ Done | `src/proactive_delegation/complexity.py` |
| Architect decomposition | ✅ Done | `src/api/routes/chat_pipeline/stages.py` |
| Review/iteration loop | ⚠️ Sequential only | `src/proactive_delegation/delegator.py` |
| **Export TaskIR to canvas** | ❌ Missing | Need `export_task_graph()` |
| **Import canvas as TaskIR** | ❌ Missing | Need `import_task_canvas()` |

### 4.3 Data Structure

```python
@dataclass
class PlanConstraints:
    """Constraints extracted from task plan canvas."""

    # Step modifications
    step_order: list[str]  # Ordered step IDs from Y-position
    actor_overrides: dict[str, str]  # step_id → new actor
    removed_steps: list[str]  # Steps to skip
    added_steps: list[dict]  # New steps from user

    # Dependency modifications
    new_dependencies: list[tuple[str, str]]  # (from_step, to_step)
    removed_dependencies: list[tuple[str, str]]

    # Parallel group modifications
    parallel_groups: dict[str, list[str]]  # group_name → [step_ids]

    # Actor preferences (from position)
    actor_weights: dict[str, float]  # actor → weight for tiebreaking
```

### 4.4 Export Function

```python
def export_task_graph(
    task_ir: dict,
    output_path: str | None = None,
    include_model_info: bool = True,
) -> str:
    """Export TaskIR plan as editable canvas.

    Layout:
    - Steps arranged by wave (Y-axis = wave number)
    - Steps in same parallel_group share X position
    - Edges show depends_on relationships
    - Node color indicates actor type
    """
    nodes = []
    edges = []

    steps = task_ir.get("plan", {}).get("steps", [])
    if not steps:
        return None

    # Compute waves for Y positioning
    waves = compute_waves(steps)

    # Color by actor
    ACTOR_COLORS = {
        "worker": "#3b82f6",      # Blue
        "coder": "#22c55e",       # Green
        "architect": "#a855f7",   # Purple
    }

    for wave in waves:
        y = wave.index * 200  # Vertical spacing

        for i, step in enumerate(wave.steps):
            x = (i - len(wave.steps) / 2) * 300  # Horizontal spread

            actor = step.get("actor", "worker")
            color = ACTOR_COLORS.get(actor, "#6b7280")

            node_text = f"**{step['id']}**: {step.get('action', '')[:100]}\n\n"
            node_text += f"Actor: {actor}"
            if step.get("depends_on"):
                node_text += f"\nDepends: {', '.join(step['depends_on'])}"

            nodes.append({
                "id": step["id"],
                "type": "text",
                "x": x,
                "y": y,
                "width": 280,
                "height": 120,
                "text": node_text,
                "color": color,
            })

            # Add dependency edges
            for dep in step.get("depends_on", []):
                edges.append({
                    "id": f"edge_{dep}_{step['id']}",
                    "fromNode": dep,
                    "toNode": step["id"],
                    "fromSide": "bottom",
                    "toSide": "top",
                })

    canvas = {"nodes": nodes, "edges": edges}

    if output_path:
        with open(output_path, "w") as f:
            json.dump(canvas, f, indent=2)

    return output_path or json.dumps(canvas)
```

### 4.5 Import Function

```python
def import_task_canvas(
    canvas_path: str,
    original_task_ir: dict,
) -> tuple[dict, PlanConstraints]:
    """Import edited canvas back as TaskIR modifications.

    Returns:
        Modified TaskIR dict and extracted constraints for logging.
    """
    canvas = parse_canvas(canvas_path)
    original_canvas = export_task_graph(original_task_ir)  # For diff
    diff = compute_canvas_diff(parse_canvas_str(original_canvas), canvas)

    constraints = PlanConstraints(
        step_order=[],
        actor_overrides={},
        removed_steps=diff.removed_nodes,
        added_steps=[],
        new_dependencies=[],
        removed_dependencies=[],
        parallel_groups={},
        actor_weights={},
    )

    # Extract step order from Y positions
    sorted_nodes = sorted(canvas.nodes, key=lambda n: n.y)
    constraints.step_order = [n.id for n in sorted_nodes if n.id.startswith("S")]

    # Detect actor changes from node text
    for node in canvas.nodes:
        if "Actor:" in node.text:
            actor_match = re.search(r"Actor:\s*(\w+)", node.text)
            if actor_match:
                new_actor = actor_match.group(1)
                original_step = next(
                    (s for s in original_task_ir["plan"]["steps"] if s["id"] == node.id),
                    None
                )
                if original_step and original_step.get("actor") != new_actor:
                    constraints.actor_overrides[node.id] = new_actor

    # Detect new dependencies from edges
    original_edges = set()
    for step in original_task_ir["plan"]["steps"]:
        for dep in step.get("depends_on", []):
            original_edges.add((dep, step["id"]))

    for edge in canvas.edges:
        edge_tuple = (edge.from_node, edge.to_node)
        if edge_tuple not in original_edges:
            constraints.new_dependencies.append(edge_tuple)

    # Detect added steps (nodes not in original)
    original_step_ids = {s["id"] for s in original_task_ir["plan"]["steps"]}
    for node in canvas.nodes:
        if node.id.startswith("S") and node.id not in original_step_ids:
            # Parse new step from node text
            constraints.added_steps.append({
                "id": node.id,
                "action": node.text.split("\n")[0].replace("**", "").split(":", 1)[-1].strip(),
                "actor": "worker",  # Default
                "depends_on": [],
            })

    # Apply constraints to TaskIR
    modified_ir = apply_plan_constraints(original_task_ir, constraints)

    return modified_ir, constraints


def apply_plan_constraints(task_ir: dict, constraints: PlanConstraints) -> dict:
    """Apply canvas constraints to TaskIR."""
    modified = copy.deepcopy(task_ir)
    steps = modified["plan"]["steps"]

    # Remove deleted steps
    steps = [s for s in steps if s["id"] not in constraints.removed_steps]

    # Apply actor overrides
    for step in steps:
        if step["id"] in constraints.actor_overrides:
            step["actor"] = constraints.actor_overrides[step["id"]]

    # Add new steps
    for new_step in constraints.added_steps:
        steps.append(new_step)

    # Add new dependencies
    for from_step, to_step in constraints.new_dependencies:
        for step in steps:
            if step["id"] == to_step:
                if "depends_on" not in step:
                    step["depends_on"] = []
                if from_step not in step["depends_on"]:
                    step["depends_on"].append(from_step)

    # Reorder by canvas Y-position
    step_order_map = {sid: i for i, sid in enumerate(constraints.step_order)}
    steps.sort(key=lambda s: step_order_map.get(s["id"], 999))

    modified["plan"]["steps"] = steps
    return modified
```

### 4.6 Plan Mode Workflow

```
User: "Implement distributed lock service"
            │
            ▼
┌───────────────────────────────────────┐
│ Stage 7.5: Complexity = COMPLEX       │
│ → Ask architect for plan              │
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ Architect returns:                    │
│ [S1: Design API, S2: Implement core,  │
│  S3: Add consensus, S4: Write tests]  │
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ PLAN MODE GATE (NEW)                  │
│                                       │
│ if features().plan_mode_enabled:      │
│   canvas = export_task_graph(task_ir) │
│   return PlanModeResponse(            │
│     canvas_path=canvas,               │
│     message="Review plan in Obsidian" │
│   )                                   │
└───────────────────────────────────────┘
            │
            ▼
    User opens canvas in Obsidian
    - Notices S2 assigned to "coder"
    - Drags S2 to architect (edits text)
    - Adds edge S1 → S3 (new dependency)
    - Adds S2b: "Analyze consensus protocols"
    - Saves canvas
            │
            ▼
┌───────────────────────────────────────┐
│ User: "Execute plan" (or auto-resume) │
│                                       │
│ modified_ir = import_task_canvas(     │
│   canvas_path,                        │
│   original_task_ir                    │
│ )                                     │
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ Execute modified TaskIR               │
│ - S2 now uses architect               │
│ - S3 waits for S1 (new dependency)    │
│ - S2b executes (user-added step)      │
└───────────────────────────────────────┘
```

### 4.7 Integration with Existing Code

**File: `src/api/routes/chat_pipeline/stages.py`**

```python
async def _execute_proactive(
    request: ChatRequest,
    state: AppState,
    initial_role: Role,
    llm_service: LLMService,
    primitives: LLMPrimitives,
) -> ChatResponse | None:
    """Execute proactive delegation with optional plan mode."""

    # ... existing complexity check ...

    # Get plan from architect
    plan_json_str = primitives.llm_call(
        build_task_decomposition_prompt(request.prompt, context),
        role="architect_general",
        n_tokens=256,
    )
    steps = _parse_plan_steps(plan_json_str)
    task_ir = _build_task_ir(request, steps)

    # NEW: Plan mode gate
    if features().plan_mode_enabled and request.plan_mode:
        canvas_path = export_task_graph(
            task_ir,
            output_path=f"logs/canvases/task_{task_ir['task_id']}.canvas"
        )
        return ChatResponse(
            response="",
            plan_mode=True,
            plan_canvas=canvas_path,
            task_ir=task_ir,
            message=f"Plan exported to {canvas_path}. Edit in Obsidian, then resume.",
        )

    # If canvas constraints provided (resuming from plan mode)
    if request.plan_canvas_path:
        task_ir, constraints = import_task_canvas(
            request.plan_canvas_path,
            task_ir
        )
        log.info("Applied plan constraints: %s", constraints)

    # ... existing execution logic ...
```

---

## Part 5: Implementation Phases (Revised)

### Phase 1: Text-Based Steering Commands

**Scope**: Simple text commands for routing control (replaces canvas steering).

**Files to create**:
- `src/steering_commands.py` — `RoutingPreference`, `SteeringState`, command handlers

**Files to modify**:
- `src/api/state.py` — Add `steering_state` to AppState
- `src/api/routes/chat_routing.py` — Apply preferences in routing
- `src/mcp_server.py` — Register steering MCP tools

**Deliverables**:
- [ ] `prefer_role()`, `veto_role()`, `force_role()` commands
- [ ] `show_routing_state()` for debugging
- [ ] Preferences applied in `_select_role_by_confidence()`
- [ ] Tests: preference application, veto behavior

**Estimated effort**: ~150 lines, low risk

### Phase 2: Plan Mode (Core Feature)

**Scope**: Export/import TaskIR as canvas, plan mode gate.

**Files to create**:
- `src/canvas_export_task.py` — `export_task_graph()`
- `src/canvas_import_task.py` — `import_task_canvas()`, `apply_plan_constraints()`

**Files to modify**:
- `src/api/routes/chat_pipeline/stages.py` — Plan mode gate
- `src/api/routes/chat.py` — Add `plan_mode`, `plan_canvas_path` to ChatRequest

**Deliverables**:
- [ ] `export_task_graph()` creates canvas from TaskIR
- [ ] `import_task_canvas()` parses canvas back to TaskIR
- [ ] Plan mode gate pauses after architect decomposition
- [ ] Resume execution with modified plan
- [ ] Tests: export/import round-trip, constraint application

**Estimated effort**: ~400 lines, medium risk

### Phase 3: Profile Mode (Personalization)

**Scope**: Long-term user profile as system context.

**Files to create**:
- `src/canvas_profile.py` — `ProfileConstraints`, export/import
- `src/prompt_builders/profile_injection.py` — System prompt augmentation

**Files to modify**:
- `src/api/state.py` — Add `profile_constraints`
- `src/llm_primitives/primitives.py` — Inject profile into prompts
- Startup code — Load profile canvas at session start

**Deliverables**:
- [ ] `ProfileConstraints` dataclass
- [ ] `export_profile_canvas()` creates template or exports existing
- [ ] `import_profile_canvas()` parses profile
- [ ] Profile injected into system prompts
- [ ] Tests: profile parsing, prompt injection

**Estimated effort**: ~300 lines, low risk

### Phase 4: Multi-Step Planning Improvements (Enhancement)

**Scope**: Address gaps identified in exploration.

**Improvements**:
- [ ] Add review loop to parallel execution (not just sequential)
- [ ] Dynamic step granularity (architect decides 2-N steps)
- [ ] Mid-execution replanning detection (when step output suggests more work)

**Estimated effort**: ~500 lines, high risk (touches critical path)

### Phase 5: Documentation & Polish

**Scope**: User-facing documentation, unified export.

**Deliverables**:
- [ ] `export_unified_workspace()` — Profile + current plan combined
- [ ] User guide: how to use profile canvas
- [ ] User guide: how to use plan mode
- [ ] Examples and templates

**Estimated effort**: ~100 lines code, ~500 lines docs

---

## Part 6: File Inventory (Revised)

### New Files to Create

| File | Purpose | Phase |
|------|---------|-------|
| `src/steering_commands.py` | Text-based routing preferences | 1 |
| `src/canvas_export_task.py` | TaskIR → canvas export | 2 |
| `src/canvas_import_task.py` | Canvas → TaskIR import | 2 |
| `src/canvas_profile.py` | Profile constraints | 3 |
| `src/prompt_builders/profile_injection.py` | System prompt augmentation | 3 |
| `tests/test_steering_commands.py` | Steering command tests | 1 |
| `tests/test_canvas_plan.py` | Plan mode tests | 2 |
| `tests/test_canvas_profile.py` | Profile tests | 3 |

### Files to Modify

| File | Changes | Phase |
|------|---------|-------|
| `src/api/state.py` | Add `steering_state`, `profile_constraints` | 1, 3 |
| `src/api/routes/chat_routing.py` | Apply steering preferences | 1 |
| `src/api/routes/chat.py` | Add `plan_mode`, `plan_canvas_path` | 2 |
| `src/api/routes/chat_pipeline/stages.py` | Plan mode gate | 2 |
| `src/llm_primitives/primitives.py` | Profile injection | 3 |
| `src/mcp_server.py` | Steering + plan + profile MCP tools | 1-3 |

---

## Part 7: Open Questions

### Resolved

| Question | Resolution |
|----------|------------|
| Constraint loading mechanism | Session-stateful via AppState, loaded via MCP tool |
| Canvas wins vs MemRL wins | Canvas wins with warning + full transparency in routing_meta |
| t-SNE vs UMAP | UMAP (faster, better global structure) — but deferred until needed |
| Live monitoring tool | Not Obsidian — would need separate web/terminal UI (deferred) |

### Unresolved

| Question | Options | Recommendation |
|----------|---------|----------------|
| **Profile canvas location** | `logs/canvases/` vs `~/.config/orchestrator/` | User home for persistence across projects |
| **Plan mode trigger** | Auto for COMPLEX vs explicit flag | Start with explicit flag, graduate to auto |
| **Multi-user profiles** | Single profile vs project-specific | Single profile first, project override later |
| **Canvas format versioning** | Embed version in canvas vs filename | Embed in canvas metadata |

---

## Part 8: Success Criteria

### Phase 1 Complete When:
- [ ] `prefer_role()`, `veto_role()`, `force_role()` commands work
- [ ] `show_routing_state()` displays current beliefs and preferences
- [ ] Routing respects preferences (weak/strong/always)
- [ ] Tests pass for preference application

### Phase 2 Complete When:
- [ ] COMPLEX task triggers plan mode (with flag)
- [ ] User can view TaskIR as canvas in Obsidian
- [ ] User can edit steps/actors/dependencies
- [ ] Modified plan executes correctly
- [ ] Tests pass for export/import round-trip

### Phase 3 Complete When:
- [ ] Profile canvas loads at session start
- [ ] Orchestrator adapts tone/detail based on profile
- [ ] User can edit profile in Obsidian and reload
- [ ] Tests pass for profile injection

### Full Integration Complete When:
- [ ] Profile + Plan canvases work together
- [ ] User can: set up profile → request complex task → edit plan → execute
- [ ] Text commands work for simple steering needs
- [ ] Documentation complete for end-user workflow

---

## Part 9: References

### Existing Code
- Canvas export: `src/canvas_export.py`
- Canvas import: `src/canvas_import.py`
- Plugin loader: `src/tool_loader.py`
- Parallel executor: `src/parallel_step_executor.py`
- TaskIR schema: `orchestration/task_ir.schema.json`
- Routing: `src/api/routes/chat_routing.py`
- Proactive delegation: `src/api/routes/chat_pipeline/stages.py`

### External
- JSON Canvas spec: https://jsoncanvas.org/spec/1.0/
- Obsidian Canvas: https://obsidian.md/canvas

### Related Documentation
- Chapter 10: Orchestration Architecture
- Chapter 16: Graph-Based Reasoning
- Chapter 22: Tool Registry & Permission Model

---

*Created as handoff from planning session 2026-02-05*

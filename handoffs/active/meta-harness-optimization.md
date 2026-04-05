# Meta-Harness: Automated Harness Optimization

**Status**: Tier 1 + Tier 2 implemented. Ready for live validation via AR-3 autopilot run.
**Created**: 2026-04-01 (via research intake)
**Updated**: 2026-04-01 (Tier 1 + Tier 2 implemented)
**Categories**: agent_architecture, benchmark_methodology

## Objective

Apply Meta-Harness (arXiv:2603.28052) approach to automatically optimize our orchestrator's harness components — prompt templates, tool definitions, routing logic, and escalation pipeline — using an agentic search over harness code rather than text-only prompt optimization.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-244 | Meta-Harness: End-to-End Optimization of Model Harnesses | high | new_opportunity |
| intake-240 | GEPA: Reflective Prompt Evolution | medium | worth_investigating |

## Key Findings from Deep-Dive

### Critical Ablation (Table 3 — the core insight)
| Feedback Mode | Median Accuracy |
|---|---|
| Scores only | 34.6% |
| Scores + text summaries | 34.9% |
| **Full filesystem access (traces)** | **50.0%** |

Full execution traces provide +15 points over score-only feedback. This directly maps to our PromptForge gap.

### Results on Agent Tasks
- TerminalBench-2 (89 CLI tasks): **76.4% (Opus), 37.6% (Haiku)** — #1-#2 on leaderboard
- RAG math (200 IMO-level): +4.7 points avg across 5 held-out models
- Text classification: +7.7 points over SOTA with 4x fewer context tokens

## Implementation Status

### Tier 1: Execution Trace Feedback — DONE (2026-04-01)

**What**: Feed `inference_tap.log` traces from evaluation runs back to PromptForge mutation step.

**Implementation**:
- `eval_tower.py`: Added `capture_recent_traces(n_lines=50)` — reads tail of `/mnt/raid0/llm/tmp/inference_tap.log`
- `autopilot.py`: After each eval, stores `state["last_traces"]`; passes to `dispatch_action()` for prompt_mutation branch
- `autopilot.py` dispatch: Traces prepended as `## Recent Execution Traces` section in PromptForge failure_context

Per the ablation, this accounts for most of Meta-Harness's improvement (+15 pts over score-only).

### Tier 2: Code Mutation Search Space — DONE (2026-04-01)

**What**: Extend PromptForge so it can mutate Python orchestration code, not just `.md` templates.

**Implementation**:
- `prompt_forge.py`: Added `CodeMutation` dataclass, `propose_code_mutation()`, `apply_code_mutation()`, `revert_code_mutation()` methods
- `prompt_forge.py`: `_build_code_mutation_prompt()` with code-specific system prompt + safety constraints
- `prompt_forge.py`: `_validate_syntax()` via `ast.parse()` — mutations that fail syntax check are rejected
- `autopilot.py`: Added `code_mutation` action type in `dispatch_action()` with full safety gate + simplicity criterion
- `autopilot.py`: Added to controller prompt's Available Actions

**Safety boundary** (eval trust boundary):
```python
CODE_MUTATION_ALLOWLIST = [
    "src/prompt_builders/resolver.py",      # Prompt resolution logic
    "src/escalation.py",                     # Escalation policy
    "src/graph/escalation_helpers.py",       # Role cycle detection
    "src/tool_policy.py",                    # Tool access control
]
```

Files NOT on this list are immutable. Eval/scoring/safety code cannot be touched.

**Safety mechanisms**:
1. Allowlist enforcement (ValueError on unlisted files)
2. `ast.parse()` syntax validation before acceptance
3. Git commit before mutation (rollback safety net)
4. Safety gate evaluation after application
5. Simplicity criterion (reject >20% size increase for <2% quality gain)
6. Optuna epoch invalidation on accepted code mutations

### Tier 3: Full Outer Loop Rebuild — DEFERRED

**What**: Build Meta-Harness-style filesystem of candidates + evaluation runner + agentic proposer.

**Why deferred**: The outer search loop is not open-sourced. Building from scratch requires significant infrastructure (candidate directory management, per-candidate filesystem isolation, 82 files/iteration access). Current Tier 1+2 captures the core insight (execution traces + code mutations) without the operational overhead.

**Revisit when**: AR-3 data shows diminishing returns from Tier 2 code mutations, indicating the search needs to be more systematic.

## Open Questions

- Can a 32B local model (Qwen2.5-Coder-32B) do diagnostic reasoning from traces, or does this require Opus-class? The paper only tested Opus.
- What's the right trace granularity? Current approach sends raw last-50-lines. Filtered traces (errors + slow turns + escalations only) may be better.
- For Tier 3: Docker per-candidate vs git worktree isolation?

## Dependencies

- ~~Autopilot AR-1 baseline must be working~~ DONE (2026-03-30)
- ~~EvalTower T0 must produce reliable scores~~ DONE (sentinel questions validated)
- ~~inference_tap.log must be capturing during evaluation~~ DONE (TUI already reads it)

## Notes

Chelsea Finn + Omar Khattab (DSPy creator) co-authored. The TerminalBench-2 result is particularly relevant — they optimized an *agent scaffold*, which is exactly what our orchestrator is.

## Research Intake Update — 2026-04-04

### New Related Research
- **[intake-254] "Goose — Open Source Autonomous AI Coding Agent"** (github.com/block/goose)
  - Relevance: Rust-based autonomous coding agent with multi-model cost optimization and MCP integration
  - Key technique: Multi-model routing for performance/cost balance, MCP-based tool extensibility
  - Delta from current approach: Goose is end-to-end autonomous (builds, executes, debugs) vs our orchestrator's guided pipeline. Their MCP integration pattern is a reference for our tool surface
- **[intake-255] "Clido — Multi-Provider CLI Coding Agent"** (github.com/clido-ai/clido-cli)
  - Relevance: Profile-based multi-provider routing with per-session cost tracking and budget management
  - Key technique: Real-time cost tracking per session, declarative YAML workflows, 16 provider backends
  - Delta from current approach: Clido's per-session budget management implements the TOKEN_BUDGET concept from CC analysis (intake-249). Their profile-based provider switching maps to our routing intelligence

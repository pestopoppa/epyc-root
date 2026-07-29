# Automated Debugging Pipeline — Eval-Spec Improvements

**Status**: COMPLETED
**Created**: 2026-03-03
**Updated**: 2026-03-04
**Completed**: 2026-03-04
**Priority**: P3 — incremental pipeline improvement
**Effort**: Medium
**Source**: Patterns from [OpenAI Evals](https://github.com/openai/evals) (inspiration, not adoption)

## Research Review

### What We Already Have

The automated debugging pipeline (`src/pipeline_monitor/`) is already sophisticated:
- **27 anomaly detectors** in `anomaly.py` — deterministic signal extraction (repetition loops, self-doubt, excessive tokens, slow delegation, etc.)
- **ClaudeDebugger** in `claude_debugger.py` — tool-using LLM debugger with post-fix regression testing, batch processing, signal proposal
- **Structured diagnostics** in `diagnostic.py` — per-task diagnostic records with anomaly scores, signals, metadata
- **53k+ question seeding pipeline** — 19 suites, automated pass/fail with dataset-specific scoring
- **Checkpoint JSONL** — persistent result storage for trend analysis

### What's Missing (Gaps This Handoff Addresses)

1. **No subjective quality assessment**: All 27 detectors are purely deterministic. A task can fail with anomaly_score=0 if no detector fires — no model judges whether the answer was actually close or the routing was suboptimal.
2. **Hardcoded detector config**: Signal weights, thresholds, and categories are defined in Python code. Tuning requires code changes, not config edits.
3. **Fragile debugger output protocol**: ClaudeDebugger proposes new signals and service reloads via regex-parsed `NEW_SIGNAL:` / `RELOAD_SERVICE:` text markers — brittle and hard to extend.
4. **No eval registry**: No centralized view of suite health, scoring methods, trends, or known issues across the 19 benchmark suites.

### OpenAI Evals — Patterns Worth Borrowing

From the OpenAI evals repo, three specific patterns are valuable:
- **YAML grading specs** (`modelgraded/*.yaml`): Reusable prompt templates with `choice_strings`, `choice_scores`, `eval_type` — portable model-graded evaluation without Python per-task
- **`cot_classify` eval type**: Chain-of-thought classification where the judge reasons before scoring — better than direct classification for subjective tasks
- **Two-layer registries**: Eval definitions separate from run configurations — clean separation of "what to evaluate" from "how to run it"

### What We Skip (and Why)

- **Their runner (`oaieval` CLI)**: We have `seed_specialist_routing.py` — more capable for our multi-model routing pipeline
- **Git-LFS dataset management**: Our question pool is managed directly, no large binary datasets
- **JSONL data format**: Our checkpoint format already works; converting adds friction with no benefit
- **Registry infrastructure**: Their YAML+Python registry is over-engineered for our 19 suites; a single YAML file suffices

## Implementation Steps

### Step 1: Extract Anomaly Detector Config into YAML

**New file**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/anomaly_signals.yaml`

Schema:
```yaml
scoring:
  aggregation: weighted_sum  # how signals combine into anomaly_score
  grading_sample_rate: 0.1   # fraction of triggered failures sent to model grading (Step 2)

signals:
  repetition_loop:
    weight: 1.0
    category: behavioral
    params:
      threshold: 0.4
    description: "Detects repeated output patterns within a single response"
  self_doubt_loop:
    weight: 1.0
    category: behavioral
    params:
      threshold: 3
    description: "Detects model repeatedly second-guessing its own output"
  # ... all 27 signals
```

All 27 signals with weights (14 at 1.0, 11 at 0.5, 2 at 0.3) and tunable thresholds for the 7 detectors that have them:
- `repetition_loop`: 0.4
- `self_doubt_loop`: 3
- `excessive_tokens`: 2000
- `slow_delegation`: 120000 (ms)
- `near_empty`: 5
- `vision_blindness`: 10
- `distill_batch_latency`: 5000 (ms)

**Modify**: `src/pipeline_monitor/anomaly.py` — lazy-load YAML at first use, fall back to current hardcoded defaults if file missing. Same pattern as other `orchestration/*.yaml` configs (read once, cache in module-level variable).

### Step 2: Add Model-Graded Eval Specs for Subjective Quality

**New directory**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/grading_specs/`

Three initial specs:

**`answer_quality.yaml`** — catches scorer false negatives on failing answers
- Trigger: `not passed and anomaly_score < 0.5`
- Rationale: If a task fails but no anomaly detector fires, was the answer actually close? Did the scorer miss a valid alternative?

**`routing_optimality.yaml`** — judges delegation chain quality
- Trigger: `len(role_history) > 2`
- Rationale: Multi-hop routing (frontdoor → worker → escalation → worker) may indicate suboptimal initial routing

**`synthesis_coherence.yaml`** — assesses long failing answers
- Trigger: `tokens_generated > 500 and not passed`
- Rationale: Long answers that still fail may have structural issues (incoherent reasoning, correct computation with wrong final answer)

Each spec defines:
```yaml
eval_type: cot_classify
judge_role: worker_explore  # tier C, 7B model — cheapest available
prompt_template: |
  Question: {question}
  Expected answer: {expected}
  Model answer: {answer}

  Evaluate whether the model's answer demonstrates understanding...
choice_strings: ["A", "B", "C"]
choice_scores:
  A: 1.0   # correct/near-correct despite scorer failure
  B: 0.5   # partial understanding, fixable
  C: 0.0   # genuinely wrong
trigger: "not passed and anomaly_score < 0.5"
```

**New module**: `src/pipeline_monitor/model_grader.py`
- `load_grading_specs()` — reads YAML files from `orchestration/grading_specs/`
- `should_trigger(spec, diagnostic)` — evaluates trigger condition against diagnostic fields
- `evaluate_with_spec(spec, question, answer, expected)` — calls judge model, parses CoT + classification

**Inference path**: The grader calls `worker_explore` via HTTP using the same helpers as the seeding pipeline. Reuse `_call_orchestrator()` from `scripts/benchmark/seeding_orchestrator.py` (port 8000, `/v1/chat/completions`) with `role=worker_explore`.

**Feature flag**: `ORCHESTRATOR_MODEL_GRADING` env var (default: off). Add to `src/features.py` in the features dict.

**Budget control**: 10% sampling rate of triggered failures (configurable via `grading_sample_rate` in `anomaly_signals.yaml`). At current seeding volume (~53k questions), worst case ~5k failures × 10% = ~500 judge calls per full run.

**Modify**: `src/pipeline_monitor/diagnostic.py` — add optional `model_graded_evals` dict field to diagnostic records (populated only when grading runs).

### Step 3: Structure ClaudeDebugger's Output Protocol

Replace regex-based `NEW_SIGNAL:` / `RELOAD_SERVICE:` parsing with a JSON code block protocol.

**Block marker**: `` ```json:debugger_actions ``

**Action types**:
- `new_signal` — propose a new anomaly detector (same as current `NEW_SIGNAL:`)
- `reload_service` — request a service reload (same as current `RELOAD_SERVICE:`)
- `grading_observation` — flag a model-graded result as noteworthy (new, from Step 5)
- `config_suggestion` — propose a config change to `anomaly_signals.yaml` (new)

Example output:
```json:debugger_actions
[
  {"action": "new_signal", "name": "code_truncation", "weight": 0.5, "rationale": "..."},
  {"action": "reload_service", "service": "worker_fast", "reason": "..."}
]
```

**New file**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/debugger_protocol.yaml` — schema definition for action types, required fields, validation rules.

**Modify**: `src/pipeline_monitor/claude_debugger.py`:
- New `_extract_debugger_actions(text)` — extract fenced JSON block, validate against schema
- Keep old `_extract_new_signals()` and `_extract_reload_requests()` as fallback for backward compatibility
- Refactor `_process_result()` to dispatch by action type when structured output is available

**Modify**: `orchestration/prompts/debugger_system.md` — replace output format instructions with the new JSON protocol, provide examples.

### Step 4: Build Eval Registry from Checkpoint Data

**New file**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/eval_registry.yaml`

Auto-generated by new script: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/update_eval_registry.py`

**Sources**:
- Checkpoint JSONL files → pass rates, last run timestamps
- `question_pool.py` header → suite names, question counts
- `dataset_adapters.py` → scoring methods per suite

**Per-suite fields**:
```yaml
suites:
  mmlu:
    scoring_method: exact_match
    question_count: 14042
    recent_pass_rate: 0.73
    trend: stable        # from 7-day linear regression: improving/stable/declining
    last_run: "2026-03-03T14:22:00Z"
    known_issues: []
    model_graded_specs: [answer_quality]
    curated: true        # preserved across auto-refreshes
```

Manual `curated: true` entries are preserved when the script regenerates — the script merges new data into existing curated entries rather than overwriting.

Optionally injected into the first-batch debugger prompt for trend awareness (gives the debugger context on which suites are declining).

### Step 5: Feed Model-Graded Results Back into ClaudeDebugger

**Modify** `_build_prompt()` in `claude_debugger.py`: when a diagnostic has a `model_graded_evals` field (populated by Step 2), include a `## Model-Graded Evals` section in the per-diagnostic prompt block. Format:
```
## Model-Graded Evals
- answer_quality: B (0.5) — "Partial understanding, correct approach but arithmetic error in step 3"
- routing_optimality: A (1.0) — "Direct routing was appropriate for this task complexity"
```

**Modify** `orchestration/prompts/debugger_system.md`: add documentation explaining model-graded signals — what they measure, how to interpret scores, when to trust vs. question them.

**New action type**: `grading_observation` allows the debugger to flag when model-graded scores consistently disagree with deterministic detectors, or to propose threshold changes for grading specs.

## Acceptance Criteria

- [x] `orchestration/anomaly_signals.yaml` defined with all 30 signals (corrected from 27); `anomaly.py` loads it with fallback to hardcoded defaults
- [x] At least 3 grading specs in `orchestration/grading_specs/`; `model_grader.py` loads specs, evaluates trigger conditions, and calls judge model
- [x] `ORCHESTRATOR_MODEL_GRADING` feature flag in `features.py`
- [x] ClaudeDebugger parses `` ```json:debugger_actions `` blocks with regex fallback for backward compatibility
- [x] `debugger_protocol.yaml` defines action type schemas
- [x] `eval_registry.yaml` auto-generated from checkpoint data by `update_eval_registry.py`
- [x] Model-graded results appear in debugger prompt when `model_graded_evals` field is present
- [x] All existing tests pass (no regressions from config extraction or protocol changes)
- [x] Model grading infrastructure validated live 2026-03-05 (50/50 ran, 0 errors, feature flag plumbed — grading is post-hoc pipeline)

## Dependency Order

```
Step 1 (YAML config)  ───────→ standalone
Step 2 (model grading) ──────→ soft-depends on Step 1 (grading_sample_rate config)
Step 3 (structured protocol) → standalone
Step 4 (eval registry) ──────→ standalone
Step 5 (close the loop) ─────→ depends on Steps 2 + 3
```

Steps 1, 3, 4 can proceed in parallel. Step 2 can start independently but benefits from Step 1's `grading_sample_rate` config. Step 5 requires both Steps 2 and 3 to be complete.

## References

- OpenAI evals `modelgraded/*.yaml` pattern: reusable grading prompt templates with `choice_strings`, `choice_scores`, `eval_type`
- Existing debugger: `src/pipeline_monitor/claude_debugger.py`, `anomaly.py`, `diagnostic.py`
- Existing prompts: `orchestration/prompts/debugger_system.md`
- Seeding pipeline: `scripts/benchmark/seed_specialist_routing.py` (in epyc-inference-research)
- HTTP helpers for model calls: `scripts/benchmark/seeding_orchestrator.py` (in epyc-inference-research)
- Feature flags: `src/features.py` (`get_features()`, env prefix `ORCHESTRATOR_`)
- Model registry: `orchestration/model_registry.yaml` (worker_explore = tier C, 7B)

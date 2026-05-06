# Engineering Standards

## Code Invariants

- Prefer typed boundaries for external data.
- Use enums and constants, not ad hoc strings.
- Gate optional features via feature flags in the relevant config layer.
- Log exceptions with context; do not use silent `except: pass`.
- Use thread-safe paths for shared mutable state.

## Numerical Parameter Policy

- Two classes of numerics:
  - `tunable`: runtime controls likely to change during evaluation/tuning.
  - `invariant`: stable semantic limits or hard boundaries.
- `tunable` values must live in typed config/dataclass surfaces, with env override when operationally relevant.
- `invariant` values must be named constants (global or subsystem-local), not magic literals.
- Do not consolidate numerics into one global file; preserve subsystem ownership.
- PRs adding numerics should include a one-line classification note (`tunable` vs `invariant`).

## Change Style

- Scope each change to one concern.
- Reuse existing modules and utilities before adding helpers.
- Place new files per existing layout.

## Placement Rules (Multi-Repo)

Project spans four repos:

| Content | Repository |
|---------|-----------|
| Orchestrator code (`src/`, `tests/`, `orchestration/`) | `epyc-orchestrator` |
| Benchmarks, research, model registry (full) | `epyc-inference-research` |
| Governance, hooks, agents, handoffs, progress | `epyc-root` (this repo) |
| llama.cpp patches and builds | `epyc-llama` |

Within `epyc-orchestrator`:
- Feature flags: `src/features.py`
- Roles/routing: `src/roles.py` and model registry
- API routes/models/services/state: `src/api/`
- Tests: `tests/unit/` and `tests/integration/`

Within `epyc-root`:
- Agents: `agents/`
- Cross-repo policy: `agents/shared/`
- Validation: `scripts/validate/`
- Architecture/rationale: `docs/`

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Any inference script (benchmarks, evals, seeding) **MUST** persist incrementally:

- Append each result to JSONL/CSV immediately after scoring — not in a batch.
- Final "summary" is convenience aggregation, not primary store.
- Killed/crashed runs must leave partial results on disk.
- Per-item progress logging (`log.info("[%d/%d] ...")`) for visibility.

**Anti-pattern** (never do this):
```python
results = []
for item in items:
    results.append(evaluate(item))  # lost if killed
with open(output) as f:
    json.dump(results, f)  # only written at the very end
```

**Required pattern**:
```python
with open(checkpoint, "a") as ckpt:
    for i, item in enumerate(items):
        result = evaluate(item)
        ckpt.write(json.dumps(result) + "\n")
        ckpt.flush()
        log.info("[%d/%d] %s", i+1, len(items), item.id)
```

## Model Registry Standards

Research registry (`epyc-inference-research/orchestration/model_registry.yaml`) is the comprehensive benchmark record. Scoring fields must use canonical format:

### Scoring Fields

`quality_score`, `vl_score`, `blind_score` use an inline YAML map:

```yaml
quality_score: {pct: 65.4, raw: "159/243"}   # standard: pct + raw fraction
vl_score: {pct: 92.0, raw: "11/12"}          # same format for vision-language
blind_score: {pct: 36.0}                      # raw omitted when fraction unavailable
blind_score: {pct: null, note: "not scored"}  # null pct with note for unscored entries
```

- `pct` (float): percentage — native YAML float for programmatic comparison. `null` if no single score.
- `raw` (string, optional): numerator/denominator fraction.
- `note` (string, optional): replaces `raw` for special cases (unscored, multi-config).
- Supplementary context (rescored dates, scale descriptions) → YAML inline comments.

**Anti-patterns** (never use):
```yaml
quality_score: 60.5              # bare float — missing raw fraction
quality_score: 66/69 (96%)       # unquoted string — YAML parse error risk
quality_score: "36%"             # quoted string — not programmatically comparable
vl_score: "11/12 (92%)"         # quoted string — mixed format
```

### Registry Scope

- **Research** (`epyc-inference-research`): comprehensive record — all models, all quants, deprecated entries preserved with notes.
- **Orchestrator** (`epyc-orchestrator`): active stack only — lean, production-facing.

### Model Entry Requirements

- Paths must be absolute.
- Per-model serving config (`use_chat_api`, `reasoning`, `kv_cache`, `sampling`) must be set before benchmarking.
- Deprecated entries retain `deprecated: true` + reason in comments.

## Verification Minimum

Before finalizing:

1. Syntax-check modified Python files.
2. Run targeted tests for touched behavior.
3. Confirm feature-flag behavior where applicable.
4. Update docs when behavior or interfaces change.

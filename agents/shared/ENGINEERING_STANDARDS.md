# Engineering Standards

## Code Invariants

- Prefer typed boundaries for external data.
- Use enums and constants, not ad hoc strings.
- Gate optional features with feature flags in the relevant repo's config layer.
- Log exceptions with context; do not use silent `except: pass`.
- Use thread-safe state update paths for shared mutable state.

## Numerical Parameter Policy

- Treat numeric values as one of two classes:
  - `tunable`: runtime behavior controls likely to change during evaluation/tuning.
  - `invariant`: stable semantic limits or shared hard boundaries.
- `tunable` values must live in typed config/dataclass surfaces, with env override path when operationally relevant.
- `invariant` values must be named constants (global or subsystem-local), not magic literals.
- Do not consolidate all numbers into one global file; preserve subsystem ownership of tunables.
- PRs adding numerics should include a one-line classification note (`tunable` vs `invariant`).

## Change Style

- Keep each change scoped to one concern.
- Reuse existing modules and utilities before adding new helpers.
- Place new files according to existing project layout.

## Placement Rules (Multi-Repo)

This project spans four repositories. Place files in the correct one:

| Content | Repository |
|---------|-----------|
| Orchestrator code (`src/`, `tests/`, `orchestration/`) | `epyc-orchestrator` |
| Benchmarks, research, model registry (full) | `epyc-inference-research` |
| Governance, hooks, agents, handoffs, progress | `epyc-root` (this repo) |
| llama.cpp patches and builds | `epyc-llama` |

Within `epyc-orchestrator`:
- Feature flags: `src/features.py`
- Roles/routing metadata: `src/roles.py` and model registry
- API routes/models/services/state: `src/api/`
- Tests: `tests/unit/` and `tests/integration/`

Within `epyc-root`:
- Agent definitions: `agents/`
- Cross-repo policy: `agents/shared/`
- Governance validation: `scripts/validate/`
- Architecture and design rationale: `docs/`

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Any script that runs inference (benchmarks, evals, seeding) **MUST** persist results incrementally:

- Append each result to a JSONL/CSV checkpoint file immediately after scoring — not in a batch at the end.
- The final "summary" output is a convenience aggregation of the checkpoint, not the primary data store.
- A killed or crashed run must leave usable partial results on disk.
- Add per-item progress logging (`log.info("[%d/%d] ...")`) so progress is visible in logs.

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

The research model registry (`epyc-inference-research/orchestration/model_registry.yaml`) is the comprehensive benchmark record. All scoring fields must use the canonical format:

### Scoring Fields

All `quality_score`, `vl_score`, and `blind_score` fields use an inline YAML map:

```yaml
quality_score: {pct: 65.4, raw: "159/243"}   # standard: pct + raw fraction
vl_score: {pct: 92.0, raw: "11/12"}          # same format for vision-language
blind_score: {pct: 36.0}                      # raw omitted when fraction unavailable
blind_score: {pct: null, note: "not scored"}  # null pct with note for unscored entries
```

- `pct` (float): percentage score — native YAML float for programmatic comparison. Use `null` when no single score applies.
- `raw` (string, optional): numerator/denominator fraction when available.
- `note` (string, optional): replaces `raw` for special cases (unscored, multi-config annotations).
- Supplementary context (rescored dates, scale descriptions) goes in YAML inline comments.

**Anti-patterns** (never use):
```yaml
quality_score: 60.5              # bare float — missing raw fraction
quality_score: 66/69 (96%)       # unquoted string — YAML parse error risk
quality_score: "36%"             # quoted string — not programmatically comparable
vl_score: "11/12 (92%)"         # quoted string — mixed format
```

### Registry Scope

- **Research registry** (`epyc-inference-research`): comprehensive benchmark record — all tested models, all quants, deprecated entries preserved with notes.
- **Orchestrator registry** (`epyc-orchestrator`): active stack only — lean, production-facing.

### Model Entry Requirements

- Paths must be absolute (not relative to any base).
- Per-model serving config (`use_chat_api`, `reasoning`, `kv_cache`, `sampling`) must be set before benchmarking.
- Deprecated models retain their entry with a `deprecated: true` flag and reason in comments.

## Verification Minimum

Before finalizing:

1. Syntax check for modified Python files.
2. Run targeted tests for touched behavior.
3. Confirm feature-flag behavior where applicable.
4. Update docs when behavior or interfaces change.

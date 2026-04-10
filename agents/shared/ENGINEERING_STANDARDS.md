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

## Verification Minimum

Before finalizing:

1. Syntax check for modified Python files.
2. Run targeted tests for touched behavior.
3. Confirm feature-flag behavior where applicable.
4. Update docs when behavior or interfaces change.

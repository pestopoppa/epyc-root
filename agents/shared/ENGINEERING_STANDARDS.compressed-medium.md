# Engineering Standards

## Code Invariants

- Typed boundaries for external data.
- Enums and constants, not ad hoc strings.
- Gate optional features via feature flags in config layer.
- Log exceptions with context; do not use silent `except: pass`.
- Thread-safe paths for shared mutable state.

## Numerical Parameter Policy

Two classes: `tunable` (runtime controls likely to change during evaluation/tuning) and `invariant` (stable semantic limits or hard boundaries).

- `tunable` values must live in typed config/dataclass surfaces, with env override when operationally relevant.
- `invariant` values must be named constants (global or subsystem-local), not magic literals.
- Do not consolidate numerics into one global file; preserve subsystem ownership.
- PRs adding numerics should include a one-line classification note (`tunable` vs `invariant`).

## Change Style

- One concern per change.
- Reuse existing modules before adding helpers.
- New files per existing layout.

## Placement Rules (Multi-Repo)

| Content | Repository |
|---------|-----------|
| Orchestrator code (`src/`, `tests/`, `orchestration/`) | `epyc-orchestrator` |
| Benchmarks, research, model registry (full) | `epyc-inference-research` |
| Governance, hooks, agents, handoffs, progress | `epyc-root` (this repo) |
| llama.cpp patches and builds | `epyc-llama` |

`epyc-orchestrator`: feature flags (`src/features.py`); roles/routing (`src/roles.py` + registry); API/services/state (`src/api/`); tests (`tests/unit/`, `tests/integration/`).

`epyc-root`: agents (`agents/`); cross-repo policy (`agents/shared/`); validation (`scripts/validate/`); architecture (`docs/`).

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Inference scripts (benchmarks, evals, seeding) **MUST** persist incrementally:

- Append each result to JSONL/CSV immediately after scoring — not in a batch.
- "Summary" is aggregation, not primary store.
- Killed/crashed runs must leave partial results on disk.
- Per-item progress logging (`log.info("[%d/%d] ...")`).

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

Research registry (`epyc-inference-research/orchestration/model_registry.yaml`): comprehensive benchmark record. Scoring fields must use canonical format.

### Scoring Fields

`quality_score`, `vl_score`, `blind_score` use inline YAML map:

```yaml
quality_score: {pct: 65.4, raw: "159/243"}   # standard: pct + raw fraction
vl_score: {pct: 92.0, raw: "11/12"}          # same format for vision-language
blind_score: {pct: 36.0}                      # raw omitted when fraction unavailable
blind_score: {pct: null, note: "not scored"}  # null pct with note for unscored entries
```

- `pct` (float): percentage; `null` if no single score.
- `raw` (string, optional): numerator/denominator fraction.
- `note` (string, optional): replaces `raw` for special cases.
- Supplementary context → YAML inline comments.

**Anti-patterns** (never use):
```yaml
quality_score: 60.5              # bare float — missing raw fraction
quality_score: 66/69 (96%)       # unquoted string — YAML parse error risk
quality_score: "36%"             # quoted string — not programmatically comparable
vl_score: "11/12 (92%)"         # quoted string — mixed format
```

### Registry Scope

- **Research**: comprehensive — all models, all quants, deprecated entries preserved.
- **Orchestrator**: active stack only — lean, production-facing.

### Model Entry Requirements

- Paths must be absolute.
- Per-model serving config (`use_chat_api`, `reasoning`, `kv_cache`, `sampling`) must be set before benchmarking.
- Deprecated entries retain `deprecated: true` + reason.

## Debugging Discipline (Observe Before Diagnosing)

- Observe before diagnosing: no root cause — or fact written to a handoff/index/progress log — without the primitive datum (actual output/error/state); unverified = hypothesis, never a finding.
- "Not observable" only after enumerating all artifacts (`find` tap/trace/session), not just the one log you know.
- Cap blind fixes at one — then observe, don't re-patch.
- A coherent failure narrative is a yellow flag (closure inflation), not evidence.

## Verification Minimum

1. Syntax-check modified Python files.
2. Run targeted tests.
3. Confirm feature-flag behavior.
4. Update docs when behavior or interfaces change.
5. Validate the real path — a stub bypassing real inference/REPL/IO proves nothing; do one real end-to-end call (canary) before "ready".

# Engineering Standards

## Code Invariants

- Typed boundaries for external data.
- Enums/constants, not ad hoc strings.
- Gate optional features via feature flags.
- Log exceptions with context; do not use silent `except: pass`.
- Thread-safe paths for shared mutable state.

## Numerical Parameter Policy

Two classes: `tunable` (runtime controls) and `invariant` (semantic limits/hard boundaries).

- `tunable` values must live in typed config/dataclass surfaces; env override when operationally relevant.
- `invariant` values must be named constants (global or subsystem-local), not magic literals.
- Do not consolidate numerics into one global file; preserve subsystem ownership.
- PRs adding numerics should include classification note (`tunable` vs `invariant`).

## Change Style

- One concern per change.
- Reuse before adding.
- Place per existing layout.

## Placement Rules (Multi-Repo)

| Content | Repository |
|---------|-----------|
| Orchestrator code (`src/`, `tests/`, `orchestration/`) | `epyc-orchestrator` |
| Benchmarks, research, model registry (full) | `epyc-inference-research` |
| Governance, hooks, agents, handoffs, progress | `epyc-root` (this repo) |
| llama.cpp patches and builds | `epyc-llama` |

`epyc-orchestrator`: `src/features.py` (flags); `src/roles.py` + registry (roles/routing); `src/api/` (API/services/state); `tests/unit/`, `tests/integration/`.

`epyc-root`: `agents/`; `agents/shared/` (cross-repo); `scripts/validate/`; `docs/`.

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Inference scripts **MUST** persist incrementally: append each result to JSONL/CSV immediately after scoring — not in a batch. Killed/crashed runs must leave partial results on disk. Per-item progress logging (`log.info("[%d/%d] ...")`). The "summary" output is aggregation, not primary store.

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
- `raw` (string, optional): numerator/denominator.
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

- **Research**: comprehensive — all models, all quants, deprecated preserved.
- **Orchestrator**: active stack only — lean.

### Model Entry Requirements

- Paths must be absolute.
- Per-model serving config (`use_chat_api`, `reasoning`, `kv_cache`, `sampling`) must be set before benchmarking.
- Deprecated entries retain `deprecated: true` + reason.

## Verification Minimum

Syntax-check, run targeted tests, confirm feature-flag behavior, update docs.

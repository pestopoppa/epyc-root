<!-- Generated 2026-07-30 from ENGINEERING_STANDARDS.md (post AFC-P6 restructure). Level: medium.
     Rider: agent-file-compress — directive markers, headers, code blocks, lists, paths preserved verbatim. -->

# Engineering Standards

## Code Invariants

- Typed boundaries for external data.
- Enums and constants, not ad hoc strings.
- Gate optional features with feature flags in repo's config layer.
- Log exceptions with context; do not use silent `except: pass`.
- Thread-safe update paths for shared mutable state.

## Numerical Parameter Policy

- Numeric values: two classes:
  - `tunable`: runtime behavior controls, change during evaluation/tuning.
  - `invariant`: stable semantic limits, shared hard boundaries.
- `tunable` must live in typed config/dataclass surfaces + env override path when relevant.
- `invariant` must be named constants, not magic literals.
- Do not consolidate all numbers into one global file; subsystems own tunables.
- PRs adding numerics: one-line classification note (`tunable` vs `invariant`).

## Change Style

- One concern per change.
- Reuse existing modules before adding helpers.
- Place new files per existing layout.

## Placement Rules (Multi-Repo)

Canonical [repository map](../../CLAUDE.md#repository-map) before placing files.

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

## Kernel Workflow (Production Immutability)

Production kernels frozen: do not modify, rebase, build, or commit to them without explicit
operator authorization. Kernel work: fresh `llama.cpp-experimental` branch;
ship by versioning past production. Full workflow:
[CLAUDE.md](../../CLAUDE.md#experimental-kernel-workflow--production-kernel-immutability).

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Inference scripts (benchmarks, evals, seeding) **MUST** persist incrementally:

- Append each result to JSONL/CSV checkpoint immediately after scoring — never batch at end.
- "Summary" output = convenience aggregation of checkpoint, not primary store.
- Killed/crashed run must leave usable partial results on disk.
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

Registry format spec (`{pct, raw}` scoring map, scope, entry requirements):
`repos/epyc-inference-research/docs/reference/models/REGISTRY_STANDARDS.md`.

## Debugging Discipline (Observe Before Diagnosing)

Capture evidence before conclusions:

- **Observe before diagnosing.** Do not state a root cause — or write one as *fact* — until you have seen the primitive datum: actual output, error string, file/state. Unverified mechanism = **hypothesis**; label it; never propagate it as a finding.
- **"Not observable" requires having looked everywhere.** Enumerate all artifacts (`find`/`ls`) before declaring a blind spot. Cheapest debug move: flag-gated per-turn trace of raw output.
- **Cap blind fixes at one.** Failed hypothesis fix → observability next, not another fix. Each blind patch costs a host-quiet window.
- **A coherent failure narrative is a yellow flag, not reassurance** — coherence is not evidence.

## Verification Minimum

1. Syntax check modified Python.
2. Targeted tests for touched behavior.
3. Confirm feature-flag behavior.
4. Update docs on behavior/interface change.
5. **Validate the real path, not a proxy.** Stub/dry-run bypassing the real inference/REPL/IO path proves nothing — one real end-to-end canary call before declaring "ready"/"validated".

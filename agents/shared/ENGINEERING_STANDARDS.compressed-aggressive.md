<!-- Generated 2026-07-30 from ENGINEERING_STANDARDS.md (post AFC-P6 restructure). Level: aggressive.
     Rider: agent-file-compress — directive markers, headers, code blocks, lists, paths preserved verbatim. -->

# Engineering Standards

## Code Invariants

- Typed boundaries for external data.
- Enums/constants, not ad hoc strings.
- Feature flags gate optional features.
- Log exceptions with context; do not use silent `except: pass`.
- Thread-safe paths for shared mutable state.

## Numerical Parameter Policy

- Two classes: `tunable` (runtime controls) / `invariant` (stable limits).
- `tunable` must live in typed config/dataclass + env override.
- `invariant` must be named constants, not magic literals.
- Do not consolidate numbers into one global file; subsystems own tunables.
- PRs adding numerics: classification note (`tunable` vs `invariant`).

## Change Style

- One concern per change. Reuse before adding. Place per existing layout.

## Placement Rules (Multi-Repo)

[Repository map](../../CLAUDE.md#repository-map) first.

`epyc-orchestrator`:
- Feature flags: `src/features.py`
- Roles/routing: `src/roles.py` + model registry
- API: `src/api/`
- Tests: `tests/unit/` and `tests/integration/`

`epyc-root`:
- Agents: `agents/`
- Cross-repo policy: `agents/shared/`
- Validation: `scripts/validate/`
- Design rationale: `docs/`

## Kernel Workflow (Production Immutability)

Production kernels frozen: do not modify, rebase, build, or commit without explicit operator
authorization. Kernel work: fresh `llama.cpp-experimental`; version past production.
[CLAUDE.md](../../CLAUDE.md#experimental-kernel-workflow--production-kernel-immutability).

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Inference scripts **MUST** persist incrementally:

- Append each result to JSONL/CSV checkpoint immediately — never batch at end.
- Summary = aggregation of checkpoint, not primary store.
- Killed run must leave usable partials on disk.
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

Spec: `repos/epyc-inference-research/docs/reference/models/REGISTRY_STANDARDS.md`.

## Debugging Discipline (Observe Before Diagnosing)

- **Observe before diagnosing.** Do not state root cause until primitive datum seen (output /
  error / state). Unverified mechanism = **hypothesis**; never propagate it as a finding.
- **"Not observable" requires having looked everywhere** — enumerate all artifacts first.
- **Cap blind fixes at one.** Failed fix → observability, not another fix.
- **A coherent failure narrative is a yellow flag, not reassurance.**

## Verification Minimum

1. Syntax check modified Python.
2. Targeted tests.
3. Confirm feature-flag behavior.
4. Update docs on interface change.
5. **Validate the real path, not a proxy** — one real end-to-end canary before "ready".

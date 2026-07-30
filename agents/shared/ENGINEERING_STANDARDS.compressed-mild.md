<!-- Generated 2026-07-30 from ENGINEERING_STANDARDS.md (post AFC-P6 restructure). Level: mild.
     Rider: agent-file-compress — directive markers, headers, code blocks, lists, paths preserved verbatim. -->

# Engineering Standards

## Code Invariants

- Prefer typed boundaries for external data.
- Use enums and constants, not ad hoc strings.
- Gate optional features with feature flags in relevant repo's config layer.
- Log exceptions with context; do not use silent `except: pass`.
- Use thread-safe state update paths for shared mutable state.

## Numerical Parameter Policy

- Treat numeric values as one of two classes:
  - `tunable`: runtime behavior controls likely to change during evaluation/tuning.
  - `invariant`: stable semantic limits or shared hard boundaries.
- `tunable` values must live in typed config/dataclass surfaces, with env override path when operationally relevant.
- `invariant` values must be named constants (global or subsystem-local), not magic literals.
- Do not consolidate all numbers into one global file; preserve subsystem ownership of tunables.
- PRs adding numerics include a one-line classification note (`tunable` vs `invariant`).

## Change Style

- Keep each change scoped to one concern.
- Reuse existing modules and utilities before adding new helpers.
- Place new files according to existing project layout.

## Placement Rules (Multi-Repo)

Use the canonical [repository map](../../CLAUDE.md#repository-map) before placing a file.

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

Production kernels are frozen: do not modify, rebase, build, or commit to them without
explicit operator authorization. Kernel work uses a fresh `llama.cpp-experimental` branch and
ships only by versioning past production. Full workflow + motivating failure:
[CLAUDE.md](../../CLAUDE.md#experimental-kernel-workflow--production-kernel-immutability).

## Incremental Persistence (Mandatory for Eval/Benchmark Scripts)

Any script that runs inference (benchmarks, evals, seeding) **MUST** persist results incrementally:

- Append each result to a JSONL/CSV checkpoint file immediately after scoring — not in a batch at the end.
- Final "summary" output is a convenience aggregation of the checkpoint, not the primary data store.
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

Canonical registry format spec (scoring-field `{pct, raw}` map, registry scope, entry
requirements) lives with the registry:
`repos/epyc-inference-research/docs/reference/models/REGISTRY_STANDARDS.md`.

## Debugging Discipline (Observe Before Diagnosing)

When a real-path or inference failure is opaque, capture evidence before forming conclusions:

- **Observe before diagnosing.** Do not state a root cause — or write one into a handoff, index, or progress log as *fact* — until you have seen the primitive datum: actual model output, actual error string, actual file/state. An unverified mechanism is a **hypothesis**; label it as such and never propagate it as a finding.
- **"Not observable" requires having looked everywhere.** Enumerate all artifacts (`find`/`ls` for tap/trace/session/scratch files) before declaring a blind spot. Cheapest debug move is often a flag-gated per-turn trace of raw model output.
- **Cap blind fixes at one.** If a hypothesis-driven fix fails, next action is observability — not another fix. Each blind patch on inference-gated work costs a host-quiet window.
- **A coherent failure narrative is a yellow flag, not reassurance** (closure inflation) — coherence is not evidence.

## Verification Minimum

Before finalizing:

1. Syntax check for modified Python files.
2. Run targeted tests for touched behavior.
3. Confirm feature-flag behavior where applicable.
4. Update docs when behavior or interfaces change.
5. **Validate the real path, not a proxy.** A stub/dry-run that bypasses the real inference/REPL/IO path proves nothing about it — exercise one real end-to-end call (a canary) before declaring infrastructure "ready" or "validated."

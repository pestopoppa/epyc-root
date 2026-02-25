> **ARCHIVED — COMPLETED**: This handoff describes historical state. The decomposition was completed: the monolith was refactored from ~2,967 to ~1,583 lines with 10 extracted `seeding_*.py` modules. The `_v2.py` symlink points to the refactored file. The script lives in `epyc-inference-research/scripts/benchmark/`. Always check the actual code for current state.

# Handoff: seed_specialist_routing.py Decomposition (2,967 LOC → 6 modules + hub)

**Status**: COMPLETED
**Created**: 2026-02-10
**Updated**: 2026-02-26
**Priority**: Medium (not blocking active work)
**Scope**: `scripts/benchmark/seed_specialist_routing.py` monolith decomposition

## Current State

All 6 extraction phases complete. Extracted modules sit alongside the original monolith. Hub saved as `seed_specialist_routing_v2.py`. **Swap NOT done** — monolith restored because new REPL tap features are actively being added to it.

### File Layout

```
scripts/benchmark/
├── seed_specialist_routing.py       ← ORIGINAL MONOLITH (restored from git, active)
├── seed_specialist_routing_v2.py    ← SLIMMED HUB (ready, not active)
├── seeding_checkpoint.py            ← NEW (extracted)
├── seeding_scoring.py               ← NEW (extracted)
├── seeding_orchestrator.py          ← NEW (extracted)
├── seeding_injection.py             ← NEW (extracted)
├── seeding_eval.py                  ← NEW (extracted, includes tap + REPL tap capture)
├── seeding_legacy.py                ← NEW (extracted)
├── seeding_types.py                 ← MODIFIED (tap fields added)
├── seeding_infra.py                 ← unchanged
├── seeding_rewards.py               ← unchanged
└── seeding_tui.py                   ← MODIFIED (sanitizer, overflow fixes)
tests/unit/
└── test_seeding_modules.py          ← NEW (38 tests, references _v2)
```

### What Was Done

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | DONE | `seeding_checkpoint.py` — checkpoint I/O, deduped 3 fcntl patterns → `_atomic_append` |
| 2 | DONE | `seeding_scoring.py` — scoring, error classification, timeout logic |
| 3 | DONE | `seeding_orchestrator.py` — slot mgmt, HTTP, `_normalize_tool_telemetry` un-nested |
| 4 | DONE | `seeding_injection.py` — embedder precompute, reward injection |
| 5 | DONE | `seeding_eval.py` — eval loop, deduped RoleResult construction → `_build_role_result` |
| 6 | DONE | `seeding_legacy.py` — legacy comparative path |
| 7 | PARTIAL | Hub created as `_v2.py`, swap deferred. Test patches + logger names fixed. |

### Dedup Fixes Applied

1. **Checkpoint locking (3 → 1)**: `append_checkpoint`, `_checkpoint_3way`, `record_seen` had identical fcntl patterns → unified `_atomic_append(path, line)`.
2. **RoleResult construction (2 → 1)**: `_eval_single_config` first-attempt + retry were ~60 LOC copy-paste → `_build_role_result()`.

### Dependency Graph (Extracted Modules)

```
seeding_types           (leaf)
  seeding_checkpoint    (types)
  seeding_scoring       (types)
  seeding_infra         (types)
  seeding_rewards       (types)
  seeding_orchestrator  (types, infra)
  seeding_injection     (types)
  seeding_eval          (types, orchestrator, scoring, rewards, infra)
  seeding_legacy        (types, orchestrator, scoring, rewards, checkpoint, infra)
  seed_specialist_routing_v2  (hub: imports + re-exports all above)
```

## Bugs Found and Fixed (in test files + extracted modules)

### 1. Patch targets

After extraction, `patch("seed_specialist_routing.call_orchestrator_forced")` no longer intercepts the internal call in `seeding_orchestrator`. Fix:

```python
# Old (broken after extraction)
patch("seed_specialist_routing.call_orchestrator_forced", ...)
patch("seed_specialist_routing.score_answer_deterministic", ...)
patch("seed_specialist_routing._wait_for_heavy_models_idle")

# New (correct)
patch("seeding_orchestrator.call_orchestrator_forced", ...)
patch("seeding_eval.score_answer_deterministic", ...)
patch("seeding_eval._wait_for_heavy_models_idle")
```

Applied in `tests/unit/test_eval_log_format.py:456-460`.

### 2. Logger names

Extracted modules used `getLogger(__name__)` → loggers named `seeding_eval`, `seeding_orchestrator`, etc. Tests capture `seed_specialist_routing` logger. Fixed all extracted modules to `getLogger("seed_specialist_routing")`.

### 3. Test suite hang at 95% (pre-existing, NOT from refactoring)

Full suite (3684 tests) hangs with `-n 48`. The 11 stuck tests are in `test_chat_routing_coverage.py`, `test_classifiers.py`, `test_inference_mixin.py`, `test_cache_integration.py`, `test_chat_pipeline.py`. They pass individually — it's a FAISS/SWIG mutex contention issue with high parallelism. Works fine with `-n 8`.

## To Complete the Swap

When the monolith stops changing (seeding debug run + REPL tap work complete):

1. **Sync any new changes** from monolith into extracted modules (check `git diff HEAD -- scripts/benchmark/seed_specialist_routing.py`)
2. **Update `test_seeding_modules.py`** — currently references `seed_specialist_routing_v2`, change to `seed_specialist_routing`
3. **Rename**: `mv seed_specialist_routing.py seed_specialist_routing_monolith.py && mv seed_specialist_routing_v2.py seed_specialist_routing.py`
4. **Run tests**: `python3 -m pytest tests/unit/test_seeding_modules.py tests/unit/test_eval_log_format.py tests/unit/test_3way_routing.py tests/unit/test_architect_delegation.py -n 8 -v`
5. **Verify full suite**: `python3 -m pytest tests/ -n 8 --tb=short`
6. **Delete monolith backup**
7. **Run gates**: `make gates`

## Known Divergence to Reconcile

The monolith is getting REPL tap changes that need to land in the right extracted module. As of 2026-02-10:

- `seeding_types.py`: `repl_tap_offset_bytes`/`repl_tap_length_bytes` — ALREADY in extracted `seeding_eval.py` and `seeding_types.py`
- `seeding_tui.py`: `_sanitize_display()`, `overflow="crop"` — not part of extraction scope
- Monolith `build_diagnostic()` calls with REPL tap fields → lives in hub `_v2.py`, needs sync
- Any NEW functions added to monolith → check which extracted module they belong to

### Sync check command

```bash
# Compare monolith functions vs extracted modules
python3 -c "
import ast, sys
tree = ast.parse(open('scripts/benchmark/seed_specialist_routing.py').read())
fns = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
print(f'{len(fns)} functions in monolith')
for f in sorted(fns):
    print(f'  {f}')
"
```

# Debugger Tap Visibility

**Status**: Complete
**Created**: 2026-02-10
**Completed**: 2026-02-10

## Problem

The Claude debugger sees only the final answer + role chain names for delegation chains like `architect_general → frontdoor → architect_coding → frontdoor`. It cannot see WHY each hop happened — the architect's raw TOON decision, the specialist's intermediate code/REPL output, investigation reports, or tool calls.

The inference tap (`src/inference_tap.py`) already logs **every** `llm_call()` with role, prompt (truncated), and full response. It writes to `/mnt/raid0/llm/tmp/inference_tap.log`. The `read_tap_section.py` script exists for byte-range reads. The gap: the seeding script never records `tap_offset_bytes` before/after each question.

## Approach

1. **`seeding_types.py`** — Add `tap_offset_bytes` and `tap_length_bytes` to `RoleResult`
2. **`seeding_eval.py`** — Record tap file size before/after each `/chat` call, store in `RoleResult`
3. **`seed_specialist_routing.py`** — Pass tap fields from `RoleResult` to `build_diagnostic()`
4. **`claude_debugger.py`** — Read tap bytes inline in prompt (replace offset-only display)
5. **`test_claude_debugger.py`** — Tests for tap inlining + missing file graceful fallback

## Files Modified

- `scripts/benchmark/seeding_types.py`
- `scripts/benchmark/seeding_eval.py`
- `scripts/benchmark/seed_specialist_routing.py`
- `src/pipeline_monitor/claude_debugger.py`
- `tests/unit/test_claude_debugger.py`

## Verification

```bash
pytest tests/unit/test_claude_debugger.py tests/unit/test_seeding_modules.py -n 48 -v
```

## Phase 2: REPL Tap Inlining

Added REPL execution log (`/mnt/raid0/llm/tmp/repl_tap.log`) inlining alongside inference tap. REPL errors (NameError, SyntaxError, import failures) are now visible to the debugger.

### Additional Changes

- `seeding_types.py` — Added `repl_tap_offset_bytes` and `repl_tap_length_bytes` to `RoleResult`
- `seeding_eval.py` — Added `_REPL_TAP_PATH`, `_repl_tap_size()`; captures REPL tap byte range around API calls
- `seed_specialist_routing.py` — Passes REPL tap fields to both `build_diagnostic()` calls
- `diagnostic.py` — Added `repl_tap_offset_bytes` and `repl_tap_length_bytes` params + dict keys
- `claude_debugger.py` — Generalized `_read_tap_inline()` with `path`/`max_chars` params; inlines REPL tap (4K char limit); updated system prompt; fixed default-param-capture bug (`path: str = _TAP_PATH` → `path: str | None = None`)
- `test_claude_debugger.py` — 4 new REPL tap tests + `_make_diag` helper updated

## Results

- 70/70 tests pass (32 debugger + 38 seeding, `-n 48`, 1.55s)
- Bug fixes:
  1. `tap_off and tap_len` → `tap_len > 0` (offset=0 is valid)
  2. Default param capture bug (Python evaluates defaults at definition time, not call time)
  3. Missing tap passthrough in `seed_specialist_routing.py` `build_diagnostic()` call (found during self-review)
- `read_tap_section.py` script is now redundant for the debugger (tap inlined) but kept for manual use

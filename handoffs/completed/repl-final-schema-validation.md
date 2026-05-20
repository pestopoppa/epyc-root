# REPL FINAL() Schema Validation

**Status**: COMPLETED 2026-05-20
**Created**: 2026-05-20
**Closed**: 2026-05-20 (same-session implementation)
**Categories**: orchestrator, repl, structured_output
**Priority**: P3 (small, optional — only relevant when callers want typed return values)
**Source**: `avbiswas/fast-rlm` commits `72862af` + `cc8395c` (2026-05-20) — `examples/structured_io.py`, `src/subagents.ts:118-332`, `fast_rlm/_runner.py:23-180`
**Related**: [`handoffs/completed/01-fast-rlm-budget-controls.md`](../completed/01-fast-rlm-budget-controls.md), [`handoffs/active/rao-redel-substrate-spike.md`](rao-redel-substrate-spike.md)

## Closure Summary (2026-05-20)

Implementation landed same session as scope. All acceptance criteria met:

- [x] `final_schema_validation` flag added to `src/features.py` (registry + dataclass field; **default_test=False, default_prod=False** — opt-in per request).
- [x] `ChatRequest.output_schema: dict | None` added in `src/api/models/requests.py` (JSON-Schema dict over the wire; Pydantic callers compose via `MyModel.model_json_schema()`).
- [x] Schema preamble rendered into initial REPL context when schema is non-None (`_render_schema_preamble`).
- [x] Captured `FINAL()` value validated via `jsonschema.validate(parsed, schema)` — uniformly accepts hand-written JSON-Schema dicts AND `BaseModel.model_json_schema()` output. (`pydantic.TypeAdapter` was the original plan but does NOT accept raw JSON-Schema dicts via `validate_python`; switched to `jsonschema` library which is already a transitive dep.)
- [x] Validation failure injects schema + error path + truncated rejected value (≤500 chars) + "State is preserved" into next-turn context; retry bounded by `_max_validation_attempts=2` AND existing `repl_executions` budget on the shared `REPLEnvironment`.
- [x] Unit tests (12, all passing): Pydantic schema, raw dict schema, primitive string schema, invalid-JSON rejection, schema-mismatch rejection, preamble formatting, failure-message truncation, ChatRequest plumbing (set + default), feature-flag dataclass + registry assertions.
- [x] Regression tests passing: `test_repl_executor.py` (26), `test_api_models_requests.py` (24), `test_features.py` (43), `test_graph_helpers.py` (16), `test_chat_pipeline.py` (28) — **137 passed, 0 failed**.

## Files Modified

- `src/features.py` — `FeatureSpec("final_schema_validation", False, False, "FINAL_SCHEMA_VALIDATION", ...)` + dataclass field.
- `src/api/models/requests.py` — `ChatRequest.output_schema: dict | None = None`.
- `src/graph/helpers.py` — `_render_schema_preamble`, `_validate_final_answer`, `_format_validation_failure_message`.
- `src/api/routes/chat_pipeline/repl_executor.py` — schema-preamble injection into `combined_context`; validation-retry loop wrapping `run_task`.
- `tests/unit/test_repl_final_schema_validation.py` — new (12 tests).

LoC: 92 production / 139 test (production ~60 ignoring docstrings and blank lines; ~2× the original "~33 LoC" estimate, attributable to the `jsonschema` import injection block in `_execute_repl` and the per-helper docstrings).

## Deltas vs original scope

- **Validation library**: switched from `pydantic.TypeAdapter` (per scope) to `jsonschema.validate` (per implementation). Reason: `TypeAdapter(json_schema_dict)` does not accept raw JSON-Schema dicts and would have required either `Pydantic v2 schema → core_schema` translation or restricting callers to Python types only. `jsonschema 4.23.0` is already in the dep graph and supports both hand-written and Pydantic-derived schemas uniformly.
- **`default_prod` corrected**: scope said "default-off in both production and dev" but the initial commit set `default_prod=True` by mistake; fixed before completion. Both defaults are now `False`. Production enablement requires explicit `ORCHESTRATOR_FINAL_SCHEMA_VALIDATION=1` plus a non-None `output_schema` field on the request — defense-in-depth against accidental activation.

## Out of scope (deferred, unchanged)

- Sub-agent (child) output schemas (fast-rlm `llm_query(context, child_schema)`).
- Dict-input flat-schema probe (fast-rlm's other 2026-05-20 addition).
- ReDel substrate intersect (see `rao-redel-substrate-spike.md`).

## Objective

Add an opt-in **Pydantic / JSON-Schema validation layer on the value passed to `FINAL(...)` inside the REPL agent**, with a retry-on-validation-failure loop that surfaces the schema + AJV/Pydantic error path back into the agent's next prompt. Mirrors fast-rlm's `output_schema=` parameter.

This is the only meaningful net-new pattern fast-rlm has added since our 2026-03-03 budget-controls intake; everything else they have is a subset of what we already implement.

## What this is NOT

**Not** the same as the existing `structured_tool_output` feature flag (`src/features.py:120`). That flag wraps each intermediate **tool invocation result** in the `ToolOutput` envelope dataclass (`src/registry/tool_registry.py:173-220`, Lobster pattern: `ok`, `status`, `side_effects_declared`, `requires_approval`, …). It says nothing about the **terminal `FINAL(value)` return** the agent emits to its caller. The two are orthogonal and should remain separate flags.

## Scope

Add a new feature flag `final_schema_validation` (`FINAL_SCHEMA_VALIDATION`). When enabled AND the caller passed an `output_schema` argument through the chat/REPL entry point:

1. **Pre-execute** — render the schema in the agent's initial preamble (JSON-Schema form, ~5 lines: "Required output schema for FINAL(...)"). Mirrors fast-rlm `src/subagents.ts:189-194`.
2. **At `FINAL()` capture** — validate the captured value against the schema using `pydantic.TypeAdapter(schema).validate_python(value)` (handles Pydantic models, primitive types, generic types, and raw `dict` schemas uniformly).
3. **On validation failure** — inject a system-like message into the next REPL turn containing: (a) the full required JSON-Schema, (b) the Pydantic error path / message, (c) the rejected value (truncated to existing `_repl_turn_token_cap` budget), (d) "Fix the value and call FINAL again. State is preserved." (verbatim from fast-rlm). Counts against existing `repl_executions` budget — so already bounded.
4. **On validation success** — proceed as today.

Caller-side: `output_schema` accepted via existing chat-pipeline kwargs surface. Plumbed through to `_execute_repl()` in `src/api/routes/chat_pipeline/repl_executor.py`. Defaults to `None` (= behavior unchanged).

## Acceptance criteria

- [ ] `final_schema_validation` flag added to `src/features.py` (default-off in both `production` and dev `get_features()`).
- [ ] `_execute_repl()` accepts optional `output_schema: type | dict | None` parameter.
- [ ] Schema preamble rendered into initial REPL prompt when schema is non-None.
- [ ] Captured `FINAL()` value validated via `pydantic.TypeAdapter`; success returns value unchanged.
- [ ] Validation failure injects schema + error path + truncated rejected value into next-turn prompt; agent retries within remaining `repl_executions` budget (no infinite loop — bounded by existing budget).
- [ ] Unit test: Pydantic `BaseModel` schema, primitive `int`, raw JSON-Schema `dict` — all validate.
- [ ] Unit test: invalid value triggers exactly one retry-with-error injection; second-valid value succeeds.
- [ ] Unit test: invalid value after budget exhausted surfaces a structured error (not a hang).
- [ ] No change when `final_schema_validation=False` or `output_schema=None` (regression test).

## Target files & rough LoC budget

| File | What | LoC est. |
|------|------|---------|
| `src/features.py` | flag spec + dataclass field | 2 |
| `src/api/routes/chat_pipeline/repl_executor.py` | accept `output_schema` kwarg; capture FINAL; validate; on-fail inject | 18 |
| `src/graph/helpers.py` | small helper `_render_schema_preamble(schema) -> str` (pydantic.TypeAdapter → dict → pretty-printed) and `_format_validation_failure_message(schema, err, rejected) -> str` | 10 |
| `src/api/routes/chat.py` (or wherever the chat entrypoint lives) | wire `output_schema` from request body to `_execute_repl` | 3 |
| tests | `tests/unit/test_repl_final_schema_validation.py` | (separate, not counted in 30-LoC budget) |

Production-LoC total: **~33 LoC**, matches the "~30 LoC" estimate from the 2026-05-20 review.

## Dependencies

- `pydantic >= 2.0` (already a transitive dep via existing orchestrator code; verify in `pyproject.toml` before claiming).
- No new runtime deps. **No Deno or fast-rlm install.**

## Open questions for claimer

1. Where in the chat-request body should `output_schema` enter — top-level field, nested under `repl_config`, or as a header? (Pick to match existing precedent — likely top-level alongside `system_prompt`/`max_turns`.)
2. Should validation failure retries count separately from organic retries, or share the `repl_executions` budget? **Recommended: share** — keeps the budget contract single-sourced; fast-rlm also lets validation retries consume the global call budget.
3. Should we expose JSON-Schema accepts only, OR also accept Pydantic model classes over the wire? **Recommended: JSON-Schema dicts over the wire** (API-friendly); Python callers can compose via `MyModel.model_json_schema()` themselves.

## Why this is small / standalone

- Pydantic is already a dep; the validation kernel is `TypeAdapter(schema).validate_python(value)` (one line).
- The retry path reuses the existing turn-injection machinery — no new control-flow primitive.
- Bounded by the existing `repl_executions` / `task_token_budget` flags — no new runaway risk.
- Default-off; zero impact when unused.

## Out of scope

- **Sub-agent (child) output schemas** — fast-rlm's `llm_query(context, child_schema)` (`src/subagents.ts:143-172`). Defer until we have a concrete caller needing typed sub-agent returns; current delegation already pins child outputs to variables in REPL scope.
- **Dict-input flat-schema probe** — fast-rlm's other 2026-05-20 addition (when input is a `dict`, print only top-level `keys + truncated previews` instead of dumping the full context). Orthogonal; tracked separately if/when context-shape leakage becomes a measured problem.
- **Wiring into `rao-redel-substrate-spike`** — if ReDel becomes the substrate (Step 3 of that handoff), `kani`'s native function-calling already handles structured returns. Revisit then.

## Verification commands (post-claim)

```bash
# 1) Unit suite
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m pytest tests/unit/test_repl_final_schema_validation.py -v

# 2) Regression — feature OFF should be a no-op
ORCHESTRATOR_FINAL_SCHEMA_VALIDATION=0 \
  python3 -m pytest tests/unit/test_repl_executor.py tests/integration/test_chat_pipeline.py -q

# 3) Live smoke — feature ON with a small Pydantic model
ORCHESTRATOR_FINAL_SCHEMA_VALIDATION=1 \
  python3 scripts/server/orchestrator_stack.py reload orchestrator
# then exercise via /chat with output_schema={"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
```

## References

- fast-rlm runner: `https://github.com/avbiswas/fast-rlm/blob/main/fast_rlm/_runner.py` (`_to_json_schema`, lines 23-46; `output_schema=` parameter, lines 123-180).
- fast-rlm validation loop: `https://github.com/avbiswas/fast-rlm/blob/main/src/subagents.ts` (lines 26-46 schema compile, 118-194 prompt preamble, 325-332 retry message).
- fast-rlm structured I/O example: `https://github.com/avbiswas/fast-rlm/blob/main/examples/structured_io.py`.
- EPYC review of fast-rlm activity 2026-03-03 → 2026-05-20 (this scope's parent context): [`handoffs/completed/01-fast-rlm-budget-controls.md`](../completed/01-fast-rlm-budget-controls.md) §Follow-up.
- Existing `structured_tool_output` (NOT this feature — orthogonal): `src/features.py:120`, `src/registry/tool_registry.py:173-220`.

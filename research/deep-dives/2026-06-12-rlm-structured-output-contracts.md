# RLM Structured-Output Contracts — schema-validated subagent returns as a correctness lever

**Date**: 2026-06-12
**Intake**: intake-693 — "Structured outputs in Recursive Language Models" (AVB / `github.com/avbiswas/fast-rlm`, 2026-06-08 X post)
**Refined verdict**: `adopt_patterns`, relevance **high** — but the headline pattern (parent-`FINAL` schema validation + retry-with-errors) is **already shipped** (`final_schema_validation`, 2026-05-20). The genuinely-net-new, still-open piece is the **child / sub-LM return schema** (fast-rlm `llm_query(context, child_schema)`), which our `batch_llm_query`/`llm_query` fan-out does **not** enforce. That is the actual gap intake-693 points at, and it is small.
**Credibility**: null (single practitioner blog/repo; validate magnitude against a real eval before relying on it).

---

## TL;DR / Refined recommendation

- fast-rlm's mechanism = (1) normalize Pydantic/primitive/generic/raw → **JSON Schema**, (2) **show the schema at REPL step 0**, (3) **validate the value on `FINAL(...)`**, (4) on failure **inject schema + error path + rejected value and let the agent re-emit — retry, not restart (state preserved)**. It also lets the *parent* pin a *child's* shape via `llm_query(prompt, child_schema)`. The booleans/typed flags act as an "external attention mask" so the aggregator reads one typed value instead of parsing prose.
- **We already implement the parent half end-to-end.** `final_schema_validation` (flag, default-off) + `ChatRequest.output_schema` + `_render_schema_preamble` (step-0 contract) + `_validate_final_answer` (jsonschema) + `_format_validation_failure_message` (schema + error + rejected ≤500 chars + "State is preserved") + a 2-attempt retry loop in `repl_executor.py`. This was lifted from the *same* fast-rlm commits (`72862af`, `cc8395c`) on 2026-05-20.
- **The gap is the child return schema.** `_batch_llm_query(prompts, role, persona)` (`src/repl_environment/combined_ops.py:302`) and the single `llm_query`/`_tracked_llm_call` path have **no `schema=` parameter**; sub-LM results come back as free text and are stringified into the parent's REPL output. This is *exactly* the failure mode intake-693 describes (free-text fan-out overwhelming the aggregator). The "external attention mask" benefit is the part we have **not** captured.
- **Smallest patch**: add an optional `schema: dict | None` to `llm_query`/`_batch_llm_query`, reuse the *already-existing* `_validate_final_answer` + `_format_validation_failure_message` helpers to validate each child return and do a bounded **per-child retry-with-errors** (1 retry), returning typed/parsed values to the parent. ~30–40 LoC, no new deps (`jsonschema` already in graph), default-off behind the existing `final_schema_validation` flag (or a sibling). **Phase-1 (REPL path)** work — it never touches the native-tools seam.
- **Worth doing now? Low-urgency, do it opportunistically — NOT a blocker for the tool-use cutover.** The tool-use-eval-contract cutover is about *telemetry* (did a tool fire) and is already LIVE; this is a *correctness* lever on sub-LM fan-out quality, orthogonal to the envelope/telemetry path. Recommend: land the child-schema patch as a standalone small PR after the autopilot resumes past trial 711, and only gate-test it once we have a fan-out-heavy eval suite to measure the "external attention mask" magnitude (currently unmeasured / single-anecdote).

---

## What it is (fast-rlm's exact mechanism)

Confirmed from the repo (`fast_rlm/_runner.py`, `src/subagents.ts`, `examples/structured_io.py`) and our two prior intake reviews:

1. **Schema normalization.** `output_schema=` accepts four forms, all normalized to a JSON Schema dict for agent visibility:
   - Pydantic model class (`output_schema=MyModel`),
   - Pydantic generic (`output_schema=list[MyModel]`),
   - Python primitive (`int`/`str`/`float`/`bool`/`list`/`dict`),
   - raw JSON-Schema dict.
   Pydantic is an optional dep — only needed for the model/generic forms.
2. **Contract at step 0.** The schema is rendered into the agent's initial context as `"Required output schema for FINAL (JSON Schema):"` so the constraint is visible *before* execution (`src/subagents.ts` preamble).
3. **Validate-on-FINAL.** After each `FINAL(...)`, the value is validated against the schema. Success → return. Failure → **not terminal**.
4. **Retry-with-errors (not restart).** On failure the agent receives the schema (re-shown) + specific error path/message + the rejected value, and re-emits within its remaining call budget. The REPL working state is untouched — "State is preserved."
5. **Child schema passing.** Inside the REPL, the parent can pin a child's output shape: `fruits = await llm_query("Generate 25 fruit names.", {"type":"array","items":{"type":"string"}})`. The child enforces the schema identically — the *parent* then reads a typed value (a list, a bool flag) instead of prose. This typed flag is the "external attention mask": the aggregator's attention is steered by a structured boolean/field rather than having to parse and (mis)attend over free text.

The hallucination-reduction framing is the headline: by forcing each subagent to commit to a typed value validated on return, the parent never has to interpret prose, which is where the aggregator was previously overwhelmed / hallucinating.

---

## What we already have vs the gap

### Already implemented (parent `FINAL` half) — `final_schema_validation`, landed 2026-05-20

Lifted from the same fast-rlm commits. Maps 1:1 onto fast-rlm's parent mechanism:

| fast-rlm mechanism | Our implementation | File ref |
|---|---|---|
| schema normalization → JSON Schema | JSON-Schema dict over the wire; Pydantic callers compose `MyModel.model_json_schema()` | `src/api/models/requests.py` — `ChatRequest.output_schema: dict\|None` |
| contract at step 0 | `_render_schema_preamble(schema)` prepended to `combined_context` | `src/graph/helpers.py:1266`; injected at `src/api/routes/chat_pipeline/repl_executor.py:519-520` |
| validate-on-FINAL | `_validate_final_answer` → `jsonschema.validate(json.loads(answer), schema)` | `src/graph/helpers.py:1277` |
| retry-with-errors (not restart) | `_format_validation_failure_message` (schema + error path + rejected ≤500 chars + "State is preserved"); 2-attempt loop, state preserved via shared `REPLEnvironment`, `turns` reset | `src/graph/helpers.py:1302`; loop at `repl_executor.py:549-565` |
| bounded retries | `_max_validation_attempts = 2`, also bounded by `repl_executions` budget | `repl_executor.py:549` |
| flag | `final_schema_validation` (default-off prod+test; opt-in per request) | `src/features.py:134,365` |

Implementation nuance worth noting: we **validate-then-retry on a `FINAL(json.dumps(...))` string**, we do **not** grammar-constrain decoding. The preamble instructs `FINAL(json.dumps(result_dict))` and the captured string is parsed + `jsonschema`-validated post-hoc. GBNF in our tree (`tool_registry.generate_gbnf_grammar`, `src/registry/tool_registry.py:635`; applied in `src/graph/helpers.py:794-802`) is used **only for tool-call *syntax*** on the first turn when a tool is required — not for `FINAL` payloads. This is the cheaper choice on CPU (see Risks).

Also note the **separate, orthogonal** `structured_tool_output` flag (`src/features.py:120`; `ToolOutput` envelope in `src/registry/tool_registry.py:173-220`) that the tool-use-eval-contract handoff wires. That envelope wraps **intermediate tool *invocation* results** (`ok`/`status`/`side_effects_declared`/`requires_approval`) and its unwrap semantics were the subject of the 2026-06-04 request-local-telemetry fix. It is **not** the FINAL/return contract — confirmed in the prior handoff's "What this is NOT" section. So we currently have two of the three relevant layers: tool-invocation envelope (telemetry) + parent-FINAL validation (correctness).

### The gap (child / sub-LM return half) — NOT implemented

The sub-LM fan-out is the missing third layer and the actual subject of intake-693's "free-text fan-out overwhelms the aggregator":

- `_batch_llm_query(self, prompts, role="worker", persona=None)` (`src/repl_environment/combined_ops.py:302`) calls `self.llm_primitives.llm_batch(...)` and returns each child result as **raw text** stringified into JSON/TOON for the parent. **No `schema=` parameter, no validation, no per-child retry.**
- The single-call path (`_tracked_llm_call` `src/repl_environment/context.py:394`, `_tracked_llm_batch` `:405`) is likewise free-text.
- Registered as REPL builtins `batch_llm_query` (`src/repl_environment/environment.py:431`) and the `llm_query`/`CALL` surface — the parent fans out, gets prose back, and must parse it. This is precisely the aggregator-overwhelm path. We get **none** of the "external attention mask" benefit because nothing forces the child to commit to a typed flag.

The 2026-05-20 closure handoff (`repl-final-schema-validation.md`) explicitly listed **"Sub-agent (child) output schemas — fast-rlm `llm_query(context, child_schema)`"** as *Out of scope, deferred until we have a concrete caller needing typed sub-agent returns*. intake-693 is that concrete caller / motivation.

---

## Implementation sketch (smallest patch)

**Phase-1 (REPL path) — no native-tools seam touched. ~30–40 production LoC, no new deps.**

Reuse the existing `_validate_final_answer` + `_format_validation_failure_message` helpers (already in `src/graph/helpers.py`) — do not write a second validator.

1. **`src/repl_environment/combined_ops.py`** — extend `_batch_llm_query`:
   - signature `_batch_llm_query(self, prompts, role="worker", persona=None, schema: dict | None = None)`.
   - when `schema` is non-None: prepend the child prompt with `_render_schema_preamble(schema)` (instruct each child to return `json.dumps(value)` matching the schema); after `llm_batch`, run `_validate_final_answer(result, schema)` per child; on failure, do **one** bounded retry per failing child with `_format_validation_failure_message(...)` appended to that child's prompt; return **parsed/typed values** (not raw strings) in the results payload, with a per-child `valid: bool` flag so the parent can read the typed attention mask.
2. **`src/repl_environment/context.py`** — same optional `schema=` on the single `_tracked_llm_call`/`llm_query` surface (one-shot, same validate + 1-retry).
3. **`src/repl_environment/environment.py`** — no signature change needed at the binding site (kwargs flow through); update the REPL system-prompt advert so the agent knows `llm_query(prompt, schema=...)` / `batch_llm_query(prompts, schema=...)` exist (mirror the `read_file` advert pattern).
4. **Flag gating**: gate the child-schema behavior behind the existing `final_schema_validation` flag (single source of truth for "we do return-schema validation") OR a sibling `child_schema_validation` if we want independent rollout. Default-off; zero behavior change when `schema=None` (regression-test this).
5. **Bound**: per-child retries count against the existing `repl_executions` / `_exploration_calls` budget — no new runaway primitive (same argument as the parent patch).
6. **Tests** (`tests/unit/test_repl_child_schema_validation.py`, ~new): raw-dict schema on `batch_llm_query`, primitive schema, invalid-child triggers exactly one retry, second-valid succeeds, `schema=None` is byte-identical no-op, typed values returned not strings.

**Why Phase-1 and not Phase-2:** the native-tools seam (Phase 2 of tool-use-eval-contract — adding `tools`/`tool_choice` to `ChatRequest`/openai compat and returning `tool_calls`) is about the *request/response transport* of OpenAI-format tool calls. Child-schema validation lives entirely inside the REPL `llm_query`/`batch_llm_query` execution path that production already uses, so it is the same layer the existing `final_schema_validation` patch occupies. No Phase-2 dependency.

---

## Decision gates & next steps

1. **Confirm a concrete caller** before landing — the 2026-05-20 deferral was explicitly "defer until a concrete caller needs typed sub-agent returns." intake-693 supplies the *motivation* but not yet a *measured* win. Gate: name the fan-out-heavy workload (e.g., agentic/coder suites that already use `batch_llm_query`) that would benefit.
2. **Measure the "external attention mask" magnitude** on a fan-out eval *before* trusting the hallucination-reduction claim — credibility is null/single-anecdote. Use an existing fan-out suite; A/B `schema=None` vs `schema=<typed flag>` aggregation accuracy. This is the only number that justifies it as a *correctness* lever vs a nicety.
3. **Land as a standalone small PR**, default-off, after autopilot resumes past trial 711 (do not entangle with the uncommitted `autopilot.py` gate work or the live cutover).
4. **Do NOT make it a Pareto objective** (consistent with the tool-use-eval-contract Phase-1 decision: optimize quality, not raw structured-call count).
5. Update `repl-final-schema-validation.md`'s "Out of scope → Sub-agent output schemas" line to point at this deep-dive + intake-693 when/if claimed.

---

## Risks & contradicting evidence

- **Single-anecdote source.** fast-rlm is a practitioner repo + X post; the "external attention mask reduces hallucination" framing has **no published eval**. Treat the magnitude as unproven; the *mechanism* (typed child returns) is sound regardless, but the size of the win must be measured locally (gate #2).
- **Grammar-constrained-decoding cost on CPU — and why we sidestep it.** The strongest enforcement is GBNF/json-schema-to-grammar constrained *decoding*, which on llama.cpp adds per-token grammar-stack work that is non-trivial on CPU decode (already BW-bound on EPYC; any extra per-token CPU is pure overhead). **We deliberately do NOT constrain-decode FINAL/child payloads** — we use **validate-then-retry on a `json.dumps` string** (`_validate_final_answer`), which costs one extra sub-LM call only *on failure* and zero per-token overhead on the common path. This is the right tradeoff for CPU inference. If we later want hard guarantees, llama.cpp *does* support `--grammar` / `json_schema` (we already emit tool-call GBNF via `generate_gbnf_grammar`), but enabling it on every child return would tax CPU decode and should be measured (roofline) before adoption — do not default it on.
- **Retry amplification.** Per-child retry multiplies sub-LM calls under fan-out (N children × up-to-2 attempts). Must stay bounded by `repl_executions`/`_exploration_calls` (already capped at `_MAX_QUERIES=5` prompts/batch) and default-off. A pathological all-fail batch is the worst case — cap retries at 1 per child.
- **Over-constraining children can hurt.** Forcing a rigid schema on a child that legitimately needs to reason in prose first can degrade quality (the child spends budget format-fixing instead of reasoning). Mitigate by allowing the child a reasoning scratchpad and only schema-validating the `FINAL`, same as the parent — not constrain-decoding the whole generation.
- **Flag sprawl.** We already have `structured_tool_output` (envelope) + `final_schema_validation` (parent FINAL). Adding child-schema validation risks a third overlapping flag. Prefer reusing `final_schema_validation` as the single "return-schema validation" switch unless independent rollout is genuinely needed.

---

## Cross-refs

- **Active handoff**: `handoffs/active/tool-use-eval-contract.md` — §"Research Intake Update 2026-06-10" carries the intake-693 note; this deep-dive sharpens it (the parent half is already done; the open piece is the child schema). The envelope/telemetry work there (`ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT`, `ToolOutput` unwrap) is **orthogonal** to return-schema validation.
- **Completed**: `handoffs/completed/repl-final-schema-validation.md` (the parent-FINAL patch, 2026-05-20; child schema listed Out-of-scope/deferred) · `handoffs/completed/01-fast-rlm-budget-controls.md` (§Follow-up 2026-05-20 first flagged the typed-FINAL pattern) · `handoffs/completed/rlm-orchestrator-roadmap.md` (RLM substrate; D5 RLM-as-MCP deferred).
- **Intake**: intake-153 (canonical RLM, arxiv:2512.24601) · intake-331 (predict-rlm) · intake-349 (dspy.RLM) · intake-693 (this entry).
- **Code**: `src/graph/helpers.py:1266-1316` (validation helpers, reusable) · `src/api/routes/chat_pipeline/repl_executor.py:505-565` (parent retry loop) · `src/repl_environment/combined_ops.py:302` (`_batch_llm_query` — patch target) · `src/repl_environment/context.py:394-405` (single-call sub-LM path) · `src/repl_environment/environment.py:431,477` (REPL builtins) · `src/features.py:134` (flag) · `src/registry/tool_registry.py:635` (tool-call GBNF, not FINAL).

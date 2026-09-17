# Client Surface Audit — reusable instrument

**Purpose.** Decide whether a client (a user-facing harness, an SDK script, an IDE plugin) can
drive, and defer to, the orchestrator's `/v1/chat/completions` + `x_*` override contract.
**Owner of live use:** [`harness-selection-and-integration.md`](../../../handoffs/active/harness-selection-and-integration.md).
HS-4 P0.3 re-ran this instrument on OpenCode at its current tip (2026-09-16, pin `350c726a`
v1.18.31): [`opencode-p03-audit-20260916.md`](opencode-p03-audit-20260916.md) §3.
**Origin:** first written in the Hermes handoff on 2026-07-04 (items N/O), extended on 2026-07-17
(HS-1b, deference surface) and 2026-09-16 (HS-1g, call-verb check). That handoff closed on
2026-09-16 and is now [`handoffs/completed/hermes-outer-shell.md`](../../../handoffs/completed/hermes-outer-shell.md).
The Hermes-specific results are in [`hermes-evaluation-20260916.md`](hermes-evaluation-20260916.md).

## 1. The contract being audited

- The orchestrator contract is **body-based**. `OpenAIChatRequest`
  (`epyc-orchestrator/src/api/models/openai.py`) takes the standard `model`, `messages`,
  `temperature`, `max_tokens`, `stream`, `tools` and `tool_choice` fields, plus the extension fields
  `x_orchestrator_role`, `x_max_escalation`, `x_force_model`, `x_disable_repl` and `x_show_routing`.
  HS-4 P0.2 adds `x_session_id`, `x_user_id`, `x_memory` and `x_tool_mode`. Re-read the model before
  every audit; do not trust this list.
- The only HTTP header the API reads is the `x-task-id` observability tag. There is **no header path
  to an override**. A client that can only add headers (for example OpenHands `LLM.extra_headers`, or
  OpenCode's `chat.headers` hook) needs a new orchestrator-side header reader. Body injection works
  today.
- **Design rule: client UX stays in the client.** Slash commands, prompts and conversation memory
  live in the client. The orchestrator exposes typed overrides, and each client maps its UX onto
  them. Do not add orchestrator policy to serve one client's UX.
- **Deterministic override flags.** A user preference that must change routing ("use the big
  model", "don't escalate") travels as a typed `x_*` field, never as prompt prose. A present field
  bypasses frontdoor classification; an absent field leaves normal routing in force. When a
  client-side profile or memory note contradicts an explicit `x_*` field, the explicit field wins.

## 2. Procedure

Run the steps in order. Work from source at a pinned commit. The audit needs no inference; the
final live acceptance request is a separate, inference-gated step.

### Step 1 — Drive: can the client set the levers?

For each needed control, record the path that sets it: role override, model override, escalation
cap, REPL disable, routing metadata, streaming, native tools and `tool_choice`. Typical paths are
`extra_body`, a JSON body field, a plugin hook, or per-model config. Score each control as
Sufficient, Workaround (document it at the edge, for example a small proxy), or Gap. Triage every
Gap as: (a) add a new `x_*` field, (b) document a workaround, or (c) reject as out of scope.

### Step 2 — Defer: can the client's own layer-(B) loop be made to defer?

Map each layer-(B) behaviour to its mechanism (`file:line`), its path to deferring to the
orchestrator, and the patch cost. The behaviours are transport, model selection and routing,
escalation cap, REPL and tool execution, context folding and compaction, sub-agent fan-out, and
eval fan-out (a headless or JSONL mode). Note whether per-turn and per-session override state is
supported, or only static per-config state.

### Step 3 — Call-verb check (HS-1g). Required before any "Sufficient" verdict.

A lever that sits in a config descriptor ("put `x_*` in the body") can be read on one call path and
**silently ignored** on another. This has happened in oh-my-pi (`providerOptions`), pi-ai
(`Model.samplingParams` on low-level `stream()`/`complete()`), Hermes (auxiliary, summary and child
calls) and llama.cpp's own README (`json_schema` example).

1. **List every place the client sends an LLM request** in the pinned tree. Include low- and
   high-level verbs (`stream`/`complete`, `streamSimple`/`completeSimple`,
   `streamText`/`generateObject`, `chat.completions.create`, raw `fetch`). Classify each as main
   loop, compaction/summary, sub-agent, or auxiliary (title, memory, classifier, search summary,
   background review). Record its `path:line`.
2. **Trace each one to the code that builds the JSON body.** Record where the lever is read (a hook,
   an options merge, `Object.assign`). Check that this code is reachable from this verb, this API
   mode and this model source.
3. **Check scope and shape.**
   - Scope: does the lever's state reach this call? Check session and agent keys, child agents, aux
     clients, and small or title models. A forked agent with a fresh session id and a
     session-keyed plugin is a known miss (Hermes background review).
   - Shape: does the key arrive **at the top level, unrenamed**? Watch for namespace unwrapping,
     camelCase conversion and known-key filters.
4. **Mark each (request path × lever) cell** HONOURED / SILENT-NO-OP / N/A / UNVERIFIED, with
   `repo@sha path:line`. A SILENT-NO-OP on a path that runs **by default** (compaction, children,
   memory side calls) blocks a "Sufficient" verdict. The path must first be disabled by config, or
   patched.
5. **Competing-router grep.** Search for model-fallback or retry chains that pick a different model
   on error (oh-my-pi `retry.fallbackChains` is the known instance). A second router must be
   disabled by config, and re-checked on every pin bump.

### Step 4 — Verdict and record

- Give a sufficiency verdict per client, with the pin, the remaining config choices, and the live
  checks still owed.
- Record the matrix in the owning handoff in HS-1g form.
- The live acceptance request (keys arrive at the body's top level; side calls carry the keys or
  are disabled; no compaction events) is inference-gated. It is HS-4 P0.4.

## 3. Reference results

### 3.1 Client-type sufficiency (2026-07-04, Step 1 only)

| Client type | Needed controls | Path | Verdict |
|---|---|---|---|
| Bare `curl` / Python SDK | role, model, escalation cap, REPL disable, routing metadata, stream, native tools | JSON body with `x_*`; standard `stream`/`tools`/`tool_choice` | Sufficient. The reference validation client is `scripts/hermes/reference_openai_client.py` (print-only unless `--send`). |
| Coding-agent proxy (Claude Code style) | role/model, no-REPL, routing debug, streaming | same JSON surface; command UX in the proxy | Sufficient if the proxy can pass arbitrary body fields; otherwise it is a proxy limitation, not an orchestrator gap. |
| Codex CLI / OpenAI-compatible coding agent | as above, plus tool suppression | standard `tools`/`tool_choice` | Sufficient after the 2026-07-04 `tool_choice="none"` fix in `openai_compat.py`. |
| IDE clients (Cursor, Continue.dev, and similar) | role/model, streaming, direct mode, routing metadata | `model` aliases plus `x_*` | Mostly sufficient. A client that cannot send body extras needs a documented workaround or a small proxy. |
| KB-RAG / retrieved-context client | role/model, REPL disable, routing metadata, tool contract | `x_*` plus standard `tools` | Sufficient for a first integration. |

Gap decisions from the same audit:

| Gap | Decision |
|---|---|
| `tool_choice="none"` still exposed tools to the REPL bridge | Fixed in `epyc-orchestrator` on 2026-07-04. |
| `temperature` accepted but not passed into `LLMPrimitives.llm_call` on the OpenAI route | Follow-up for a focused sampling/determinism migration. |
| No caller-controlled `seed`/`top_p`/`top_k` | Policy question for the determinism lane; prefer a named override over generic pass-through. |
| `x_max_escalation` is metadata/pass-through only on this route | Partial until full graph enforcement is verified. HS-4 P4 routing parity covers it. |
| Clients that cannot send nonstandard body fields | Document a workaround or proxy at the edge. |

### 3.2 Per-candidate call-verb matrices (HS-1g, 2026-09-16)

The full matrix for Hermes, OpenCode, oh-my-pi, deepseek-harness and pi is in
[`harness-selection-and-integration.md`](../../../handoffs/active/harness-selection-and-integration.md)
under HS-1g. The Hermes row and its extensions are in
[`hermes-evaluation-20260916.md`](hermes-evaluation-20260916.md) §3. The OpenCode re-audit at
`350c726a` (E1–E15, P0.3) is in [`opencode-p03-audit-20260916.md`](opencode-p03-audit-20260916.md) §3.

## Call-verb matrix — five candidates, source-only (2026-09-16, HS-1g)

Moved here 2026-09-17 from the HS-1g row in
[`harness-selection-and-integration.md`](../../../handoffs/active/harness-selection-and-integration.md):
the instrument and its results belong together. Every **egress** (a place the harness sends an LLM
request) x lever cell is HONOURED / SILENT-NO-OP / N/A, with `repo@sha path:line`. OpenCode was
re-audited later at pin `350c726a`; see [`opencode-p03-audit-20260916.md`](opencode-p03-audit-20260916.md) §3.

    | Candidate @ pin | Main loop | Own compaction / summary | Sub-agents | Lever that works | Silent no-ops found | Verdict |
    |---|---|---|---|---|---|---|
    | Hermes @ `532a49f1` | `chat.completions.create` via `pre_llm_call` → `extra_body` — HONOURED (`run_agent.py:4213-4224`) | **SILENT-NO-OP**: the compressor calls aux `call_llm` with no `extra_body` (`agent/context_compressor.py:346-355`); iteration-limit summary builds its own kwargs, no hook (`run_agent.py:5297-5350`); `flush_memories` goes through aux `call_llm` (`:4497`) | **SILENT-NO-OP**: `delegate_tool.py:207` builds the child `AIAgent` without `session_id` → a fresh id (`run_agent.py:845-852`); the EPYC plugin looks overrides up by session, with only `"default"` as fallback (`scripts/hermes/plugins/epyc-orchestrator-overrides/__init__.py:129`) | plugin `extra_body` (chat-completions mode only; the anthropic/codex branches return before the hook, `:4042-4108`) | the three above | **main loop only.** HS-1b's "patch cost ≈ 0" holds only with `compression.enabled:false` **and** `delegate_task` gated; the iteration-limit summary and memory flush still bypass overrides (small plugin/core patch). |
    | OpenCode @ `4bffbb6` | `streamText` — HONOURED, keys spread **top-level** by `@ai-sdk/openai-compatible@2.0.41` (only its own schema keys are stripped, `openai-compatible-chat-language-model.ts:231-240`) | `processor.process` → `streamText` — HONOURED | task tool → child session → same processor — HONOURED | `chat.params` → `output.options.x_*` (`session/llm/request.ts:114-131`, namespaced at `provider/transform.ts:1337-1339`), or per-model `options` | models.dev-mode `provider.body` keys are **camelCased** (`provider/provider.ts:1287-1291` → `xOrchestratorRole`); provider-level `options` never reach the body; `agent create` calls `generateObject` without providerOptions (`agent/agent.ts:435`); the title call swaps in `smallOptions` (`session/prompt.ts:226`) | **all default paths OK.** This settles HS-1c's "top-level vs nested" caveat at source (a live request is still worth one confirmation). |
    | oh-my-pi @ `37eee719` | `streamSimple` (`agent/src/agent-loop.ts:1584`) — HONOURED; `compat.extraBody` is merged independently of the verb (`openai-shared.ts:717-722`) | summary `completeSimple` via `sideStreamFn` (`compaction.ts:827`, `session-maintenance.ts:1603`) — HONOURED; `snapcompact` makes no LLM call — N/A | `task/executor.ts:3138` → same stream fn — HONOURED | `compat.extraBody` | `providerOptions` (gateway blob only); v2 remote compaction (raw fetch, Responses API only) | **all default paths OK** |
    | deepseek-harness @ `0d1f5000` (HEAD) | `ctx.llm.stream` → pi-ai `streamSimple` (`llm/llm-pi-ai/src/adapter.ts:380`) — **no lever exposed** (the profile schema has no `samplingParams`/`onPayload`, `config.ts:254-335`) | same `ctx.llm.stream` (`compaction-basic/src/summarizer.ts:161`) | in-process children use the same loop; external CLIs N/A | the native `llm-deepseek` route only: `request-extensions` fields spread into the body (`chat-completions/adapter.ts:320-333`; collisions rejected, `common/request-extensions.ts:28-32`) | pi-ai route: `chatTemplateKwargs` lands nested | **Correction to HS-1e:** dsh HEAD now pins pi-ai **0.85.1** (`pnpm-workspace.yaml:56`), so the "bump the pin" edit is done upstream; the schema/materializer edits remain. Unverified: whether an `x_*` field needs a `DeepSeekLlmApiExtensionMap` type entry. |
    | earendil-works/pi @ `ceea48f5` | `modelRuntime.streamSimple` (`core/sdk.ts:314/324`) — HONOURED | `completeSummarization` → `streamFn`, else `completeSimple` (`compaction.ts:594-597`); branch summary (`branch-summarization.ts:353`) — HONOURED | none in tree — N/A | `Model.samplingParams` (`ai/src/api/simple-options.ts:27-33`, applied at `openai-completions.ts:990-991`) | the public `ModelRegistry.stream()/complete()` (`model-registry.ts:106-125`) is exposed to extensions (`extensions/types.ts:321`) and drops `samplingParams`; `samplingParams` has no effect on the openai-responses/anthropic/google providers | **all in-tree paths OK**; any extension we write must use the simple verbs. |

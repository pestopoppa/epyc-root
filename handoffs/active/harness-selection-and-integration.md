# Harness Selection & Integration — Orchestrator ↔ User-Facing Harness

**Status**: active — strategy/selection index (harness UNCHOSEN; no implementation committed)
**Created**: 2026-07-16 (operator question: keep the Orch orthogonal to its harness, or bake it in?)
**Categories**: agent_architecture, inference_serving, tool_implementation, context_management
**Related (down)**: [`hermes-outer-shell.md`](hermes-outer-shell.md) (Hermes candidate eval), [`hermes-agent-index.md`](hermes-agent-index.md) (Hermes/agent-UX dispatch), [`tool-output-compression.md`](tool-output-compression.md) (context-collision surface), [`meta-harness-optimization.md`](meta-harness-optimization.md) (RLM harness self-improvement lineage)
**Related (precedent)**: [`../completed/orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md) (backend-side session/compaction boundary), [`../archived/claude-code-local-constellation-routing.md`](../archived/claude-code-local-constellation-routing.md) (archived ACP-as-Path-B precedent)

## Objective

Decide **how** the orchestrated stack ("the Orch") relates to its user-facing agent harness, and eventually **which** open-source harness to adopt — without prematurely coupling to one. This index owns the harness-agnostic thesis + the selection decision; per-candidate detail lives in the leaf handoffs below.

## Thesis — orthogonal backend moat + cooperation-requiring agent loop

The Orch's value splits into two layers:

- **(A) Harness-agnostic backend moat** — kernels, MTP spec-dec, quantization, model serving, the eval tower, MEASUREMENT governance, cost-aware *scoring*. It has **no UI** and **must stay orthogonal** behind a stable API (`/v1/chat/completions` + `x_*` overrides). Baking it into a harness would entangle the measurement trust boundary with frontend churn. Supporting datapoint: **intake-426** — a coding harness (Claude Code) is ~98.4% operational infrastructure / ~1.6% AI decision logic; the harness is mostly plumbing, our intelligence is the moat.
- **(B) Agent-loop intelligence** — per-turn routing / difficulty estimation, context-folding / tool-output compaction, plan-review reroute, sub-agent fan-out, trace-memory, cost-aware escalation. **Layer (B) only pays off if the harness COOPERATES** (defers to / integrates with the Orch's decisions).

**Load-bearing consequence (operator, 2026-07-16): cooperation ⇒ the harness must be OPEN-SOURCE.** A closed harness (Claude Code, grok-build's binary — intake-249/426/827) cannot be modified to defer to the Orch's routing/compaction/escalation, so (B) would be wasted or actively contested. Therefore closed harnesses are excluded as Orch frontends. **Claude Code is the development harness (this repo's dev loop), NOT an Orch-frontend candidate.**

**Recommendation (default posture):** keep (A) orthogonal; do **NOT** build a bespoke harness (that re-implements ~98% plumbing per intake-426). Adopt an open-source harness whose cooperation surface fits, and inject (B) through it (typed override flags — see the Deterministic Override Flags pattern in `hermes-outer-shell.md` L55-69 — and/or MCP, and/or ACP).

## Candidates (selection is OPEN)

| Candidate | Kind | Cooperation surface | Detailed track |
|---|---|---|---|
| **Hermes / OpenGauss** | open-source | `/v1` + `x_*` overrides; ACP adapter as "Path B" | [`hermes-outer-shell.md`](hermes-outer-shell.md) + [`hermes-agent-index.md`](hermes-agent-index.md) |
| **OpenCode** | open-source | TBD (no eval yet) | — (task HS-1 stands one up) |
| **ACP-speaking open harnesses** | open-source | ACP (Agent Client Protocol) | contingent on ACP-ROI (task HS-2) |
| ~~Claude Code / grok-build~~ | closed | none (can't be made to defer) | excluded — reference only (dev harness) |

## Prioritized Task List

- [x] **HS-1 — Cooperation-surface audit per open candidate (Hermes, OpenCode):** for each, map how its layer-(B) behavior (context compaction, model selection, sub-agent spawning, tool loop) can be made to DEFER to the Orch's routing / context-folding / escalation, and the integration/patch cost. Generalizes the **Client Surface Audit** in `hermes-outer-shell.md` (L321-344) beyond Hermes. **Do NOT audit Claude Code** (dev harness, not a candidate). ✅ 2026-07-17 — Hermes (HS-1b) + OpenCode (HS-1c) audited below; **both SUFFICIENT on the cooperation surface, neither needs a core fork**; DECISION HS-4 stays OPEN (operator).
  - [x] **HS-1a — OpenHands cooperation-surface pre-audit** (intake-848, control-plane dive) ✅ 2026-07-16: `/v1` via base_url + `openai/` prefix works against bare llama.cpp; `LLM.extra_headers` forwards per-request → `x_*` passthrough confirmed (static per named config; per-turn needs N configs or ~10-line patch); headless `--json` JSONL. Weakness: ships its own full layer-(B) loop + Docker substrate → high make-it-defer patch cost. Details in the 2026-07-16 intake-update section below; Hermes + OpenCode audits remain open.
  - [x] **HS-1b — Hermes cooperation-surface audit** ✅ 2026-07-17 (A4, source-only, no inference): speaks `/v1/chat/completions` via OpenAI SDK, `api_mode` auto-resolves to `chat_completions` for a local `/v1` base_url. Per-request `x_*` passthrough is **already landed** — the `pre_llm_call` plugin hook (`run_agent.py:4213`) hands the mutable `api_kwargs` to the EPYC `epyc-orchestrator-overrides` plugin, which merges per-session `x_orchestrator_role`/`x_max_escalation`/`x_disable_repl` into `extra_body` (→ body fields = the orchestrator's actual `x_*` contract). Layer-(B) loop defers via **existing knobs, no new code**: `compression.enabled: false` hands folding to the orchestrator; `delegate_task` is toolset-gated (drop it → orchestrator owns fan-out; or keep it → each child inherits the parent base_url and re-fires `pre_llm_call`). **Sufficiency: SUFFICIENT — lowest patch cost of all candidates; only config + live `/v1` validation (items G/P, inference) remain.** Full deference table in `hermes-outer-shell.md` → "Client Surface Audit — 2026-07-17 (HS-1b)".
  - [x] **HS-1c — OpenCode cooperation-surface audit** ✅ 2026-07-17 (A4, source-only, no inference; clone at `/mnt/raid0/llm/tmp/opencode-audit` @ `4bffbb6`, MIT, Bun/TypeScript): `@ai-sdk/openai-compatible` provider (`opencode.json` `options.baseURL=.../v1`) POSTs `/chat/completions` (`packages/opencode/src/provider/provider.ts:117,1668-1796`). Per-request `x_*` passthrough needs **no core fork** and has THREE routes — (a) **config-only static**: `provider.<id>.models.<m>.options` keys and `options.body` spread into the top-level request body, `options.headers` into headers (`packages/core/src/v1/config/provider-options.ts:33-39,170-173`); (b) **dynamic per-turn plugin hooks** `chat.params` (mutates `options`→body) + `chat.headers` (mutates headers), keyed to session+agent, invoked at `packages/opencode/src/session/llm/request.ts:114-146` (real in-tree exemplars: copilot/codex/cloudflare plugins); (c) `options.fetch` escape hatch. Since the orchestrator reads `x_*` from the **body**, use `chat.params.options` / `model.options`. Layer-(B) defers via config: `compaction.auto: false` disables Hermes-style folding (`packages/opencode/src/session/overflow.ts:28`); model selection is static-per-agent with no dynamic router (`runner/model.ts:188-213`) so nothing fights `x_force_model`; the `task` subagent tool (`packages/opencode/src/tool/task.ts`, depth-limited) re-enters the same request pipeline so the same hooks apply; `permission.ask`→`allow` + `opencode run --format json` give headless eval fan-out. **Sufficiency: SUFFICIENT (cooperation surface is strong and arguably cleaner than Hermes — typed, documented per-request hooks), with ONE live-check caveat**: confirm that `chat.params.options` serializes as top-level body keys for the `@ai-sdk/openai-compatible` provider (vs nested `providerOptions`) with a single live request. Cost to make it cooperate = one small first-party plugin (analogous to the Hermes plugin) + config, no fork; foreign Bun/TS runtime is an ops cost, not a cooperation blocker. Full deference map in the 2026-07-17 findings section below.
- [ ] **HS-2 — ACP ROI evaluation:** is adopting ACP as the integration protocol worth it? High ROI would *widen* the candidate set to all ACP-speaking open harnesses rather than committing to Hermes/OpenCode native surfaces. **Re-open the intake-263 "MCP-first, ACP=editor-agent-not-inference" lean with this lens** (it predates the unchosen-harness framing).
- [ ] **HS-3 — (only if HS-2 is positive) Survey ACP-speaking open harnesses** as additional candidates (e.g., Local Studio Pi / intake-833, Zed, others); do NOT include closed ones.
- [ ] **HS-4 — Harness-selection decision gate:** Hermes vs OpenCode vs an ACP-speaker, gated on HS-1 + HS-2. Default outcome preserved: (A) stays orthogonal; no bespoke harness unless a specific research-demo differentiator justifies it.

## Dependency Graph

```text
HS-1 cooperation-surface audit (Hermes, OpenCode) ─┐
HS-2 ACP ROI evaluation ───────────────────────────┤→ HS-3 (if ACP+) → HS-4 selection decision
                                                    └→ HS-4 selection decision
```

## Cross-Cutting Concerns

1. **Context-collision surface** — a candidate harness's OWN conversation compaction / prompt-cache mgmt / sub-agent spawning can double-up or fight orchestrator-side Phase-2 compression + context-folding. Owned by [`tool-output-compression.md`](tool-output-compression.md) (see its Phase-4 cross-refs) and the Hermes Cons/Key-Questions in `hermes-outer-shell.md` (L37-42, L84-90). This is the concrete instance of "(B) needs cooperation."
2. **Backend-moat orthogonality + MEASUREMENT trust boundary** — layer (A) (eval tower, scoring, era registry, safety gates) stays server-side and human-amendment-only; a harness must never absorb it.
3. **RLM harness self-improvement lineage** — the "specialized harness beats a general one" idea (intake-517 HALO) cross-links to [`meta-harness-optimization.md`](meta-harness-optimization.md) (frozen pointer; do not route work there).

## Key Files / Surfaces

- The **`/v1/chat/completions` + `x_*` override** contract (the stable orthogonal API) — orchestrator routing/override surface.
- `research/deep-dives/opengauss-architecture-analysis.md` — ACP / session-analytics / context-compression prior art.
- `hermes-outer-shell.md` L55-69 (Deterministic Override Flags = the cooperation pattern), L321-344 (Client Surface Audit = the audit instrument).

## Reporting Instructions

- Record HS-1/HS-2 findings here (or in the candidate leaf) and flip the checkbox with `✅ YYYY-MM-DD`. HS-4's decision, when made, updates this index's Status and the candidate handoffs.
- Any change to the orthogonality posture or the open-source requirement is an operator decision — flag, do not decide autonomously.

## Evidence Base (intake)

intake-833 Local Studio (mgmt-GUI end) · intake-827 grok-build (closed, ACP) · intake-263 claude-acp-server (ACP↔Anthropic; prior MCP-first lean) · intake-426 "Dive into Claude Code" (98.4% infra / 1.6% logic) · intake-249 Claude Code leak analysis · intake-243 Claw Code · intake-254 Goose · intake-255 Clido · intake-473 pi-agent-core · intake-517 HALO · intake-183 0xSero/vllm-studio.

## Research Intake Update — 2026-07-16 (framework dives: OpenHands verdict + HS-1 input)

Control-plane planning ran verdict-driven framework dives (intake-847/848/849; adoption-shortcuts table in [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)). Relevant to HS-1/HS-4: **OpenHands (intake-848) is mechanically the strongest candidate yet on the cooperation surface** — MIT; speaks `/v1/chat/completions` to bare llama.cpp via `base_url` + `openai/` prefix; SDK `LLM.extra_headers: dict[str,str]` is merged into every litellm request, so `x_*` overrides pass through (static per named config; per-turn dynamism needs N named configs or a ~10-line patch); headless `--json` JSONL plugs into eval fan-out — **but it is weak on orthogonality**: it ships its own full layer-(B) loop (condenser/compaction, model selection, sub-agent spawning) plus its own Docker substrate, i.e. adopting it imports a competing orchestrator (Cross-Cutting Concern #1 instantiated). Recommendation recorded: admit OpenHands to the HS-1 audit as a serious candidate scored explicitly against orthogonality/minimum-imports; a thin OpenCode-style shell is likely cheaper to make cooperate. Also noted: LangGraph (intake-847) was adopted as a durable-execution COMPONENT inside the orchestrator (layer-A-adjacent, not a harness matter); OpenAI Agents SDK (intake-849) = mine_patterns only, fully local-compatible but inseparable primitives.

## HS-1 Cooperation-Surface Findings — 2026-07-17 (A4: Hermes HS-1b + OpenCode HS-1c)

Source-only audits (no inference, no build, no run). Hermes @ `/mnt/raid0/llm/hermes-agent` `v2026.3.23-44-g532a49f1`; OpenCode cloned read-only to `/mnt/raid0/llm/tmp/opencode-audit` @ `4bffbb6` (clone status: **succeeded**, full clone). Template = HS-1a OpenHands pre-audit. These are FINDINGS + patch-cost + a per-candidate sufficiency call — the HS-4 pick is NOT made here (operator).

### Cross-candidate finding: the orchestrator override contract is BODY-based

Verified in `epyc-orchestrator`: all five `x_*` overrides are JSON **body** fields on `OpenAIChatRequest` (`src/api/models/openai.py:63-82`), parsed off the request model and consumed at `src/api/routes/openai_compat.py:396-397,455-459`. The only header the API reads anywhere is the `x-task-id` observability tag (`src/api/__init__.py:334`) — there is **no header→override path**. Consequences for candidate scoring:
- **Body injection works today**: Hermes `extra_body`, OpenCode `chat.params.options` / config `options.body`.
- **Header-based passthrough would need a new orchestrator-side reader** (~small): this includes OpenHands' `LLM.extra_headers` (HS-1a) *and* OpenCode's `chat.headers` hook. The HS-1a "x_* passthrough confirmed" note implicitly assumes such a reader — it is not free against today's body-only contract. Prefer body injection for all candidates, or add one header→override shim once and reuse it.

### Hermes (HS-1b) — deference map

Full table in [`hermes-outer-shell.md`](hermes-outer-shell.md) "Client Surface Audit — 2026-07-17 (HS-1b)". Summary: transport ✓ (OpenAI SDK `chat.completions.create`, `api_mode=chat_completions`); routing/escalation/REPL overrides **already landed** via the `pre_llm_call` hook + EPYC plugin injecting `extra_body` (per-turn + per-session, strictly better than OpenHands' static-per-config); context-folding defers via `compression.enabled: false`; sub-agent fan-out defers via toolset gating of `delegate_task` (or kept, since children inherit the same orchestrator endpoint). **Patch cost ≈ 0 new code.** **Sufficiency: SUFFICIENT** — cooperation surface READY; only config selection + live `/v1` validation (items G/P, inference) remain.

### OpenCode (HS-1c) — deference map

MIT · Bun/TypeScript monorepo · documented `@opencode-ai/plugin` hook API (`packages/plugin/src/index.ts:222-335`). A **native-runtime gate** (`packages/opencode/src/session/llm/native-runtime.ts:54-59`) only activates the native transport for providerID ∈ {openai, anthropic, opencode\*}; a custom orchestrator provider therefore falls back to the Vercel AI SDK `streamText` path — the more injectable one.

| Layer-(B) behavior | OpenCode mechanism (file:line) | Defer-to-orchestrator path | Patch cost |
|---|---|---|---|
| Transport | `createOpenAICompatible` from config `provider` block (`provider/provider.ts:117,1668-1796`) → POST `/chat/completions` (`packages/llm/src/protocols/openai-compatible-chat.ts:20`); `opencode.json` `options.baseURL=.../v1` | already the `/v1/chat/completions` contract | none |
| Routing / model / REPL overrides (`x_*`) | **static**: `provider.<id>.models.<m>.options`+`options.body`→top-level body, `options.headers`→headers (`core/src/v1/config/provider-options.ts:33-39,170-173`); **dynamic**: `chat.params.options`→providerOptions→body & `chat.headers`→headers, keyed to session+agent, fired at `session/llm/request.ts:114-146` (exemplars: copilot.ts:340/360, codex.ts:549/559, cloudflare.ts:64); **escape hatch**: `options.fetch` | body-inject via `chat.params.options` (matches body contract) — static in config, or dynamic in a small plugin | LOW — one first-party plugin OR config-only; **no core fork** |
| Context folding | own auto-compaction gated by `compaction.auto` (default true) & `limit.context` (`session/overflow.ts:28`, `session/compaction.ts:172-176`); plugin hooks `experimental.session.compacting` + `experimental.compaction.autocontinue` | set `compaction.auto: false` → orchestrator folds; or raise `limit.context` so it never triggers | ~0 (config) |
| Model selection | static per-agent `model`, **no dynamic router / scoring** (`session/runner/model.ts:188-213`; agent model at `agent/agent.ts:45,373`) | point every agent at the single orchestrator model → nothing competes with `x_force_model` | ~0 (config) |
| Sub-agent fan-out | `task` tool spawns depth-limited child sessions (`tool/task.ts`; `subagent_depth` default 1); child model inherits parent/own config → same endpoint; permission-gated before spawn | children re-enter the same request pipeline → same `chat.params`/`chat.headers` injection applies; or gate/deny the `task` tool so orchestrator owns fan-out | ~0 (config) |
| Tool loop / headless | AI SDK `streamText`, OpenAI-native `tool_calls` (`session/llm.ts:317-319`); permission gate `ask\|allow\|deny` (`permission/index.ts:28-33`) overridable by `permission.ask` hook; headless `serve` + `run --format json` (raw JSON events, `cli/cmd/run.ts:176-178,679-680`) | `permission.ask`→`allow` for unattended runs; `run --format json` for eval fan-out (parity with OpenHands `--json`) | ~0 |

**Sufficiency (OpenCode): SUFFICIENT — cooperation surface is strong and arguably cleaner than Hermes** (typed, documented, per-request hooks for params/headers/messages/system/compaction/small-model/tool-defs; static overrides are pure config). **One live-check caveat**: confirm `chat.params.options` (or `model.options`) serializes as **top-level** body keys for the `@ai-sdk/openai-compatible` provider rather than nested `providerOptions` — a single live request settles it; if nested, either read the nested path server-side or use the `options.fetch` hook. **Cost to make it cooperate** = one small first-party plugin (analogous to the landed Hermes plugin) + config; foreign Bun/TS runtime is an operational cost (heterogeneous with our Python stack), not a cooperation blocker.

### Comparative read (for HS-4 input; decision remains operator's)

- **Hermes**: cooperation READY-NOW and in-language (Python), integration already landed; carries a large layer-(B) loop but every part is config/toolset-gated and all aux/summary/child traffic routes back through the orchestrator — most contained of the three.
- **OpenCode**: cleanest, best-documented per-request cooperation API + MIT + first-class headless JSON; cheap-but-not-yet-built plugin; foreign runtime; one serialization live-check.
- **OpenHands (HS-1a)**: strongest generic mechanics but weakest orthogonality (ships a competing full loop + Docker substrate); header-based passthrough needs a server-side shim vs today's body contract.
- Confirms the HS-1a hypothesis that "a thin OpenCode-style shell is likely cheaper to make cooperate" **at the API-surface level** — though OpenCode is a full coding agent, not thin, its plugin API is expressive enough to inject deference without a fork.

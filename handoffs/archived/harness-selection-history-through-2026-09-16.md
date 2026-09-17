# Harness selection — history through 2026-09-16

> **Historical ledger only; current work lives in
> [`../active/harness-selection-and-integration.md`](../active/harness-selection-and-integration.md).**
> Split out 2026-09-17, after HS-4 was decided on 2026-09-16 (OpenCode selected, pi fallback,
> Hermes-style features built inside the orchestrator). Everything below is the pre-decision
> candidate-comparison trail and the closed seam-defect work, preserved verbatim for provenance.
>
> It is **not a task list** — do not dispatch from it. Every checkbox here is already closed, and
> the candidate comparisons were written while the selection was still open, so they weigh
> alternatives that are now decided. Where this file contradicts the active handoff, the active
> handoff wins. **Verify against actual code before trusting any description here.**
>
> Still live elsewhere, deliberately not archived: the Harness Cards and the re-targetability /
> randomization doctrine (promoted to
> [`../../docs/reference/harness-candidates/harness-card.md`](../../docs/reference/harness-candidates/harness-card.md)
> and [`../../docs/reference/harness-candidates/harness-doctrine.md`](../../docs/reference/harness-candidates/harness-doctrine.md)),
> the `/v1` structured-output capability record
> ([`../../docs/reference/v1-structured-output-capability.md`](../../docs/reference/v1-structured-output-capability.md)),
> and the call-verb matrix
> ([`../../docs/reference/harness-candidates/client-surface-audit.md`](../../docs/reference/harness-candidates/client-surface-audit.md)).
> The open boxes that were embedded in these sections — HS-5b, HS-9, HS-E1 — moved **up** into the
> active handoff's task list rather than here.

---

## Research Intake Update — 2026-07-16 (framework dives: OpenHands verdict + HS-1 input)

Control-plane planning ran verdict-driven framework dives (intake-847/848/849; adoption-shortcuts table in [`reviewer-control-plane-index.md`](../active/reviewer-control-plane-index.md)). Relevant to HS-1/HS-4: **OpenHands (intake-848) is mechanically the strongest candidate yet on the cooperation surface** — MIT; speaks `/v1/chat/completions` to bare llama.cpp via `base_url` + `openai/` prefix; SDK `LLM.extra_headers: dict[str,str]` is merged into every litellm request, so `x_*` overrides pass through (static per named config; per-turn dynamism needs N named configs or a ~10-line patch); headless `--json` JSONL plugs into eval fan-out — **but it is weak on orthogonality**: it ships its own full layer-(B) loop (condenser/compaction, model selection, sub-agent spawning) plus its own Docker substrate, i.e. adopting it imports a competing orchestrator (Cross-Cutting Concern #1 instantiated). Recommendation recorded: admit OpenHands to the HS-1 audit as a serious candidate scored explicitly against orthogonality/minimum-imports; a thin OpenCode-style shell is likely cheaper to make cooperate. Also noted: LangGraph (intake-847) was adopted as a durable-execution COMPONENT inside the orchestrator (layer-A-adjacent, not a harness matter); OpenAI Agents SDK (intake-849) = mine_patterns only, fully local-compatible but inseparable primitives.

## HS-1 Cooperation-Surface Findings — 2026-07-17 (A4: Hermes HS-1b + OpenCode HS-1c)

Source-only audits (no inference, no build, no run). Hermes @ `/mnt/raid0/llm/hermes-agent` `v2026.3.23-44-g532a49f1`; OpenCode cloned read-only to `/mnt/raid0/llm/tmp/opencode-audit` @ `4bffbb6` (clone status: **succeeded**, full clone). Template = HS-1a OpenHands pre-audit. These are FINDINGS + patch-cost + a per-candidate sufficiency call — the HS-4 pick is NOT made here (operator).

### Cross-candidate finding: the orchestrator override contract is BODY-based

Verified in `epyc-orchestrator`: all five `x_*` overrides are JSON **body** fields on `OpenAIChatRequest` (`src/api/models/openai.py:63-82`), parsed off the request model and consumed at `src/api/routes/openai_compat.py:396-397,455-459`. The only header the API reads anywhere is the `x-task-id` observability tag (`src/api/__init__.py:334`) — there is **no header→override path**. Consequences for candidate scoring:
- **Body injection works today**: Hermes `extra_body`, OpenCode `chat.params.options` / config `options.body`.
- **Header-based passthrough would need a new orchestrator-side reader** (~small): this includes OpenHands' `LLM.extra_headers` (HS-1a) *and* OpenCode's `chat.headers` hook. The HS-1a "x_* passthrough confirmed" note implicitly assumes such a reader — it is not free against today's body-only contract. Prefer body injection for all candidates, or add one header→override shim once and reuse it.

### Hermes (HS-1b) — deference map

Full table in [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) "Client Surface Audit — 2026-07-17 (HS-1b)". Summary: transport ✓ (OpenAI SDK `chat.completions.create`, `api_mode=chat_completions`); routing/escalation/REPL overrides **already landed** via the `pre_llm_call` hook + EPYC plugin injecting `extra_body` (per-turn + per-session, strictly better than OpenHands' static-per-config); context-folding defers via `compression.enabled: false`; sub-agent fan-out defers via toolset gating of `delegate_task` (or kept, since children inherit the same orchestrator endpoint). **Patch cost ≈ 0 new code.** **Sufficiency: SUFFICIENT** — cooperation surface READY; only config selection + live `/v1` validation (items G/P, inference) remain.

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

## HS-2 ACP-ROI Findings — 2026-07-17 (B4: analysis only; ACP/HS-4 decision stays operator's)

Full analysis: [`../../research/acp-roi-analysis-2026-07.md`](../../research/acp-roi-analysis-2026-07.md). Verdict summary:

**ROI of adopting ACP as *the* integration standard: LOW.** The plan's upside hypothesis — "high ROI widens the candidate set to all ACP-speakers" — does not hold once A4's finding is applied, because ACP and the cooperation contract sit at **different layers**:

- **ACP = north-facing (client ↔ agent / editor ↔ agent).** It standardizes how a UI/editor *drives* an agent: session new/load/**fork**/cancel, structured streaming callbacks, permission prompts, slash commands, workspace file-access. intake-263 pins it ("open standard for AI agent-**editor** integration"; 2026-04-06 downgrade: "editor-agent protocol, **not inference**"). The only local ACP server we hold is OpenGauss's `acp_adapter/` bolted onto the hermes core.
- **Cooperation/deference = south-facing (agent ↔ inference).** A4 proved the orchestrator reads `x_*` from the request **body** (`/v1/chat/completions`), not headers — and every open harness already reaches that body via its OpenAI-compatible model client. Cost is already ~0 (Hermes: landed plugin; OpenCode: one small plugin/config).

Therefore:
1. **ACP does not lower cooperation cost** (already ~0) and would *add* net-new code (an ACP server surface) — contra the ~0-cost body path.
2. **ACP does not widen the *cooperating*-candidate set.** The width axis that matters is "OpenAI-compat body-reachable," which already spans the whole open field (Hermes, OpenCode, OpenHands, Aider, Continue…). "Speaks ACP" is an orthogonal, smaller set and is *irrelevant* to whether a harness can defer.
3. **ACP's real value is a UI axis (bring-your-own-editor) we have no demand for** — single-user deployment, no bespoke-UI ambition (intake-426), and it collides with orthogonality principle #2 (backend moat stays headless).
4. **ACP is cheaply deferrable** — it can be added later as an optional *harness-local* Path-B north adapter (Hermes/OpenGauss already ships one) with zero impact on the cooperation contract. Not a one-way door.

**Recommendation to HS-4 (operator decides):** keep the cooperation contract = `/v1` + `x_*` (body) + MCP for tools (MCP-first is already de-facto — the orchestrator ships an MCP server today). Keep **HS-3 dormant on cooperation grounds** — do not survey/adopt "all ACP-speakers" as cooperation candidates. Re-open ACP only on a concrete UI/editor-interop demand (operator call): (a) a bring-your-own-editor / management-GUI product surface, (b) a specific external client (Zed / JetBrains / Local Studio Pi intake-833) to drive the stack from, or (c) ACP gaining inference-routing semantics (it has none today). The intake-263 "MCP-first, ACP = editor-agent-not-inference" lean is **confirmed and sharpened** by A4, not flipped by the unchosen-harness framing.

## 2026-07-25 — intake Stage-2a dive: HS-5 trainability axis; Fractal is not a candidate

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](../active/intake-derived-work-2026-07-25.md)._

- [x] **HS-5 — add a "weight-space RL adapter exists?" column to the HS-4 decision matrix.** OpenCode = **YES** (first-party `opencode_env` in huggingface/OpenEnv plus a complete TRL AsyncGRPO example, both landed 2026-07-24); Hermes = NO; ACP-speakers = NO. Decision input only — cooperation surface (HS-1b/HS-1c, both SUFFICIENT) remains the primary axis. It is ~zero cost to preserve now and an expensive retrofit later. ✅ 2026-07-29 — matrix below records the adapter surface separately from current-host feasibility; HS-4 remains operator-owned.
  - **Caveat, dive-verified**: the training half is **not reachable on our hardware and should be declined, not bridged**. llama.cpp has **none** of the seven vLLM control endpoints (`/get_world_size`, `/pause`, `/resume`, `/init_weight_transfer_engine`, `/start_weight_update`, `/update_weights`, `/finish_weight_update`) and `weight_transfer.py:25` hard-imports the vLLM NCCL engine, so it could only ever be a **frozen off-policy sampler** — defeating AsyncGRPO's premise. Plus separate-GPU, FSDP2-only and no PEFT/LoRA path.


### HS-5 trainability axis for the operator-owned HS-4 comparison

| Candidate | Weight-space RL adapter exists? | Current-host feasibility | Selection meaning |
|---|---|---|---|
| Hermes | No first-party adapter identified. | Not applicable without authoring a new training/control-plane stack. | No trainability option to preserve; cooperation remains the primary comparison axis. |
| OpenCode | **Yes** — first-party `opencode_env` and a TRL AsyncGRPO example. | **No**: its vLLM/NCCL/FSDP2, separate-GPU, full-parameter training path cannot run on the current llama.cpp/MI210 posture. Only its GPU-free trace-capture half is presently relevant. | Preserve this as a future option, not as a reason to bridge or select OpenCode now. |
| ACP-speaking candidates | No first-party weight-space adapter identified in the HS-4 candidate surface. | No established compatible training path. | ACP remains a dormant UI/interoperability path, not a trainability advantage. |

This is a decision input, not a promotion score or an HS-4 decision. The source and the
current-host decline are recorded in [`intake-derived-work-2026-07-25.md`](../active/intake-derived-work-2026-07-25.md)
ID-20 (`c942728e`); any future training proposal must re-establish a compatible control plane and
separate-GPU posture rather than treating an adapter example as deployment evidence.
- [x] **Record Fractal (plasma-ai) as an OUTER-LOOP orchestrator that drives harnesses, NOT an HS-4 candidate** — it owns no HTTP client and exposes no `base_url`, delegating all model access to a spawned vendor CLI. Free inheritance from HS-1c: a Fractal node running `--agent=opencode` reaches the Orch via `opencode.json` `options.baseURL`, so local-model operation needs no fork of either project. ✅ 2026-07-29 — already recorded with containment/trial boundary in [`intake-derived-work-2026-07-25.md`](../active/intake-derived-work-2026-07-25.md) ID-14, evidence commit `c942728e`; trial remains separate and not authorized on this host.

## 2026-07-29 — intake Stage-4: harness taxonomy, NLAH re-targetability, and the corrected capability-vs-harness ratio

_Via `/research-intake` Stage-4 (intake-921 / 926 / 931 / 934, plus KAT-Coder-V2.5 §4.1 and the DSPy/GEPA cost line). All figures below are OBSERVATION-grade under MEASUREMENT.md — external, closed-model, mostly n=1 per cell. None gates HS-4._

- [x] **HS-6 — Audit our Layer-B surface against the six-dimension harness decomposition** (context assembly / tool interaction / generation control / orchestration / memory management / output processing), recording per dimension which parts are **editable** vs **hard-coded**. Merge in arXiv 2605.23950's seven-layer **ETCSOVG** taxonomy — **E**xecution, **T**ool, **C**ontext, **S**cheduling, **O**bservability, **V**erification, **G**overnance — and adopt its **Harness Card** as our disclosure schema. **Factual correction 2026-09-07 (prose only, the box stands):** ETCSOVG is a **different partition**, not a superset that "adds Observability and Governance" — it adds four layers and **drops two** (generation control; memory management, folded into Context). See HS-6b. Output is a table in this index, not a code change. ✅ 2026-07-29 — Harness Card below; source-only audit, no runtime change.
- [x] **HS-7 — Re-targetable-harness principle (operator, 2026-07-29).** The fleet will be upgraded as better open-weight models land, so **harness policy must survive a freeze change**. This ranks the NLAH design (intake-926: policy as an editable *document*, mechanisms in code) **ABOVE** a model-specific experience bank (intake-921), and it is the reason 926 is the adoption target despite weaker headline numbers. Record this as a standing selection criterion for HS-4 and for anything that proposes to bake per-model behaviour into the harness. ✅ 2026-07-29 — criterion and acceptance evidence below; HS-8 implementation remains open.
- [x] **HS-8 — Extract run-level policy into an editable document per the NLAH pattern.** Measured reductions: 60.10k→2.90k tokens / 68→3 files (Live-SWE); 47.50k→1.40k / 5→1 (SeeAct); 10.50k→0.80k / 3→1 (MHTBA). MIT reference impl at `github.com/curated-skills/LinguaClaw`. **Carry the DESIGN, not the numbers.** ✅ 2026-07-29 — [`HARNESS_RUN_POLICY.md`](../../agents/shared/HARNESS_RUN_POLICY.md) separates editable roles, workflow, artifact/handoff, retry/stop, and adaptation policy from code/human-owned mechanisms; no runtime loader or inference run added.

- [x] **HS-10 — File harness randomization as an EVALUATION-side pattern**, not a training one. Three axes from KAT-Coder-V2.5 §4.1: tool-invocation protocol, context-management strategy, control-flow complexity. Needs no RL — our FAIL_TO_PASS oracle already satisfies the "verification anchored to test outcomes, not traces" precondition. Cross-link the **P4.6 randomized-pool NULL** as prior evidence that randomization is not automatically a win. ✅ 2026-07-29 — bounded evaluation pattern and P4.6 counterexample below; no training or inference run added.
- [x] **HS-11 — Record the DSPy compile budget as the standing cost line** for any prompt-program compilation: 10-20 trials over 150-300 validation examples ≈ 1.5k-6k program runs ≈ **5k-25k LM calls** (GEPA cross-check: 1,839-7,051 rollouts). On a CPU-first host that is hours-to-days per compile — budget it as a **region-locked campaign**, never a background task. ✅ 2026-07-29 — already recorded in [`wiki/llm-prompting.md`](../../wiki/llm-prompting.md) “The standing cost line”; evidence compilation `838a57d1` and intake-927 provenance verified.
- [x] **HS-12 — Carry the CORRECTED capability-vs-harness figures, and carry BOTH halves together.** A dive of arXiv 2607.15439 (intake-934) establishes that the `0.62-8.56` span previously used to justify a "~6× more bought by capability than architecture" reading is the **verification-minus-simplification margin — ONE RUNG of the ladder, not the architecture axis**. Corrected reading, with the counterweight that must never be separated from it: ✅ 2026-07-29 — both halves and the observation-only limitation were already compiled in [`wiki/agent-architecture.md`](../../wiki/agent-architecture.md) and [`wiki/benchmark-methodology.md`](../../wiki/benchmark-methodology.md) by `838a57d1`.
  - A **one-step MODEL swap** buys ≈ **3.6×** the full textual→verification harness ladder; a **one-step REASONING-BUDGET bump** buys ≈ **2.0×**. The paper itself states no such ratio — these are our arithmetic over its grid.
  - **COUNTERWEIGHT (equally load-bearing):** at **fixed model and fixed effort**, a harness *revision* (v1.2→v1.5) moved the score **+7.23**, which is **larger than the entire 5.08-point architecture spread at that same setting**. Harness engineering at frozen capability is **first-order, not marginal** — and this is the direct empirical support for the HS-7 re-targetable-harness position.
  - Quoting either half alone misuses the number in one direction or the other. Grade: **n=1 per cell, closed frontier models, on a benchmark's public demonstration set → OBSERVATION only.** It cannot gate HS-4 or any build/skip decision.
- [x] **HS-6b — rework the HS-6 Harness Card against the CORRECTED ETCSOVG partition.** The card below was built as "six dimensions + Observability + Governance"; that reading is corrected in HS-6's line above — ETCSOVG is a different partition, not a superset. Four card changes are applied below under this row: **(b)** the two missing layers **EXECUTION** and **VERIFICATION** (the latter pulled out of the existing Output-processing and Governance rows); **(c)** an **INFORMATIVENESS** row carrying our verified reading; **(d)** the six-tuple `H=(O_H, A_H, V_H, G_H, R_H, L_H)` adopted as row vocabulary, taxonomy only; **(e)** the **BIWM observability checklist**. Next step: re-read the reworked card against the live candidate audits (HS-1e/HS-1f) and correct any row those audits contradict. `intake-1344#record`, `intake-1339#record`, `intake-1341#record`. ✅ 2026-09-16 (`sub-harness`) — re-read against HS-1e, HS-1f and the new HS-1g call-verb matrix. **One row was contradicted and is corrected in place:** Context assembly claimed that harness-side compaction "can defer to Orch policy". That holds only where the compaction request path honours the lever, or compaction is disabled; Hermes's compressor does not honour it. Checked with no change needed: Execution, Tool, Verification, Informativeness, the six-tuple vocabulary row and the BIWM row. None of them makes a per-candidate claim that the audits contradict; the pi audit's `compaction.enabled=false` and "no permission system" are candidate facts, not card rows. The Selection-implication paragraph gains the same qualifier.
- [x] **HS-6c — publish a CONFORMANT Harness Card, side by side with the existing one.** Rows = Appendix A Table 3 minimum-disclosure fields, one per ETCSOVG layer (runtime/sandbox/network; tool list + error contract; context cap + retrieval; agent loop + stopping rule; logged artifacts; validation hooks; permission model); values = our **actual eval-tower settings**, not aspirations. **Keep the existing editable-vs-code-owned card** — it answers a different and locally more useful question, and the two are complements, not replacements. Why this is not cosmetic: [`HARNESS_RUN_POLICY.md`](../../agents/shared/HARNESS_RUN_POLICY.md):93 already requires a run report to name *"the applicable Harness Card"*, and **no card exists in conformant form**, so that requirement is unsatisfiable today. Depends on **HS-6b**. `intake-1344#record`. ✅ 2026-09-16 (`sub-harness`) — published below as "HS-6c Conformant Harness Card". Its layer rows use the **verbatim** Table 3 field sets, fetched from arxiv.org/html/2605.23950. Values are source-read from `epyc-orchestrator@92bbeb06`, with spot-checks of ET:4283-4295, `requests.py:79`, `config/__init__.py:481-484`, `compaction.py:114-130` and `approval_gate.py:80-89`. Thirteen undisclosed/unfixed fields are named rather than filled. The existing card is kept unchanged apart from the HS-6b correction. The HARNESS_RUN_POLICY.md "applicable Harness Card" requirement is now satisfiable.

## HS-4 external instruments and their limits

_Filed 2026-09-07 via `/research-intake`. Three external instruments were examined as possible inputs
to the HS-4 decision packet. **None of them is a measurement of our candidates**; each row below is a
pointer plus the reason it cannot carry a number into the packet._

- **HS-4a — JIT-Agent Table 3.** The first external fixed-backbone comparison that names both Hermes
  and OpenCode. **POINTER ONLY, not a measurement**: no baseline code is released, no adapter exists,
  the token accounting is **execute-phase-only**, and the cost column self-contradicts. Use it to know
  the comparison has been attempted; never to rank a candidate. `intake-1320#record`.
- **HS-4b — Harness-Bench.** Measures **Hermes**; does **not** measure OpenCode, oh-my-pi,
  deepseek-harness or `earendil-works/pi`. No per-backbone number, no harness version pin, hosted APIs
  only — and arXiv:2606.12344 **reverses its harness ordering**. The single usable datapoint is a
  shape, not a score: Hermes **139.7K tokens / 22.6 turns** vs NanoBot **68.7K / 7.3**. **No number
  from this instrument may enter the HS-4 decision packet.** `intake-1332#record`.
- **HS-4c — the harness census, usable only as SELECTION VOCABULARY.** Its five dimensions plus
  §5.3's three non-co-occurrences are usable as a **candidate checklist**. **No support / lift /
  confidence / score value may be cited** — the matrix is withheld and the scales are undefined.
  Mechanism-level questions go to arXiv:2609.00006, not to this census. `intake-1335#record`.

## 2026-08-10 — Two defects in the `/v1` cooperation seam itself (research-intake Stage-3)

_Found while auditing the OpenAI-compat surface during `/research-intake`; **independent of any
research source**. Filed here because this handoff owns the cooperation contract — "a stable API
(`/v1/chat/completions` + `x_*` overrides)" — and both defects live in exactly that seam, so any
harness we later select inherits them. Verified by reading `epyc-orchestrator` on 2026-08-10._

**Why this belongs to harness selection and not to a general bug list.** HS-1c/A4 established that
every candidate harness cooperates by writing **body fields** on `/v1/chat/completions`, and that the
API reads no headers other than the `x-task-id` tag. That makes the request model's field policy and
its error path the whole contract. Both are currently wrong in a way that is silent.

- [x] **HS-OD-1 — Standard OpenAI body fields are silently dropped.** ✅ 2026-08-12
  (`auditor`, pulled from the generated bench and claimed; orchestrator `cbe551e8`)
  `response_format` and
  `max_completion_tokens` have **zero occurrences anywhere under `src/api/`**, and
  `OpenAIChatRequest` (`src/api/models/openai.py:39`) declares no `model_config` / `class Config` and
  no `extra` policy — so pydantic v2's default `extra='ignore'` discards them without error.
  **Consequence: any OpenAI-SDK client that uses JSON mode is silently broken against `:8000`** — it
  gets prose where it asked for schema-constrained JSON, with a 200 and no diagnostic. This is not a
  missing feature so much as a missing *refusal*: unknown fields that change output semantics must be
  rejected, not ignored. Decide per field — implement, or reject with a 4xx naming the field — and add
  a test that a body field the API does not honour cannot be accepted silently.
  **Done.** Per-field decision as the row asks: `max_completion_tokens` **implemented** (alias →
  `max_tokens`; both supplied → 422); `response_format` and the other unhonoured semantic fields
  (`n`≠1, `stop`, `logprobs`/`top_logprobs`, `logit_bias`, penalties, legacy `functions`/
  `function_call`) **refused with a 422 naming the field** — value-sensitively, so explicit no-ops
  (`n=1`, penalty `0.0`, `{"type":"text"}`, empty lists) and non-semantic extras (`user`,
  `metadata`, `stream_options`) still pass, keeping SDK clients that spell out defaults working.
  JSON-mode support itself remains unimplemented BY DECISION: the seam now answers with a
  diagnostic instead of prose-with-a-200; implementing it is backend feature work needing
  inference validation — file its own task if a harness actually needs it.
  Guards both directions (refusal fires AND compliant path passes):
  `tests/unit/test_openai_semantic_field_refusal.py`, 30 tests, plus the 897-test
  compat/chat/request slice green. **Committed, NOT LIVE**: the running `:8000` uvicorn serves
  the old request model until the API reload at the inference session's own boundary
  (reload-ownership rule) — reload routed via bus, not executed here.
- [x] **HS-OD-2 — Backend failures are returned as assistant content with HTTP 200.** ✅ 2026-08-11
  (`mainB`, orchestrator `a4e398fc`)
  `src/api/routes/openai_compat.py:776-777` catches **every** exception into
  `response_text = f"[ERROR] Backend failed: {e}"`, then falls through to
  `return OpenAIChatResponse(...)`. A downstream harness sees a successful completion whose text
  happens to begin with `[ERROR]`; retry logic, error metrics and eval scorers all treat it as a
  model answer. This is the fail-open shape that `feedback_fail_open_defaults_conceal_their_own_corruption`
  covers, sitting on the seam every candidate harness talks to — and it also means any eval fan-out
  through `:8000` has been scoring backend outages as low-quality generations. Map backend failures to
  a real HTTP error status; if a soft-fail path is genuinely wanted, it must be opt-in and flagged in
  the response, never the default.
  **Done.** `HTTPException` and `ContentionDenied` now propagate (the former includes the 503 for
  uninitialised primitives raised a few lines above, which the blanket handler was swallowing into a
  200; the latter reaches its app-level 503 + `Retry-After` + `failure_provenance` handler instead of
  arriving as a model answer). Everything else maps to **502** — this route is a gateway in front of
  the llama.cpp fleet, so the fault is the upstream's. No opt-in soft-fail path was added; nothing
  asked for one, and adding an unused escape hatch to a seam this load-bearing invites its own
  regression.
  **Scope note — the streaming path had the same defect and is fixed in the same change.** The
  finding cites only the non-streaming line, but the identical fail-open sat at three further sites
  (vision, direct call, REPL generation) plus the `primitives is None` case. Fixing only the cited
  line would have left every streaming client — the OpenAI SDK default for most harnesses — still
  corrupted while this box read done. A stream cannot retract its 200 (headers precede the
  generator), so those now emit a terminal SSE `error` event and stop, rather than streaming the
  error as assistant content and closing with `finish_reason: "stop"`.
  Guards: `tests/unit/test_openai_compat_backend_failure_status.py`, asserting **both** directions.
  The three failure-path tests were verified to FAIL against pre-fix HEAD in a detached worktree; the
  two success-path tests pass in both, which is the point — a failure-only guard would pass just as
  happily if the route began erroring on everything. 292 passed across all tests touching this route.
  **Extension 2026-08-23** (tier-1 backlog pass): the 2026-08-11 fix stopped *raised* exceptions
  becoming 200s, but the layer beneath still failed open — `LLMPrimitives.llm_call` does not raise; it
  returns `[ERROR: ...]` strings at start-of-answer, and those in-band failures were reaching clients
  as HTTP 200 assistant content (streaming closed `finish_reason: "stop"`). Now detected at the route
  via the canonical `inband_error_text()` rule: non-streaming → 502 `HTTPException`, streaming →
  terminal SSE `error` event + `finish_reason: "error"`; REPL path checks the raw result before the
  auto-wrap into `FINAL(...)`. A model answer *beginning* with `[ERROR:` is classified as a backend
  failure (codebase-wide convention); mid-answer occurrences stay 200 (guarded). 4 new tests failed
  against the unfixed code, 10/10 green after; 121 passed across the openai_compat surface; ruff
  clean. Provenance of the change sits uncommitted in the working tree of the shared orchestrator
  clone (`src/api/routes/openai_compat.py`, `tests/unit/test_openai_compat_backend_failure_status.py`).
  **HS-OD-1 deliberately untouched** per the lane brief; it remains open at its own box above.

## Research Intake Update — 2026-09-14 (intake-1346…1366)
_Via /research-intake Stage-4 (operator-approved plan 2026-09-14). Sources: intake-1350, 1351, 1352, 1353, 1360, 1362, 1363 — dive-verified. Every number below is EXTERNAL: it motivates the local bake-off and never gates HS-4 (MEASUREMENT.md)._

- [x] **HS-14 — HS-4 packet: external evidence rows (not selection evidence).** (a) **Harness rank tracks model class:** the same author's grids give Spearman −0.05 between GLM-5.2-744B and Gemma-4-26B (SWE-bench Pro) but +0.76 between Gemma-4-26B and Muse-Glimmer-30B (TB2.1, 8 shared harnesses); on Muse-Glimmer opencode 41.3% / qwen-code 40.0% / pi 37.3% / hermes 24.7% (50 tasks × 3 trials; harness versions and reasoning setting unstated; model not servable on v9) `intake-1352#record`, `intake-1363#record`. (b) **Thinking mode:** in the Gemma-4 thinking-off arm (non-randomly censored) crush/opencode/pi lose ~2/3 of their score while claude_code is flat — our enable_thinking=false roles make external thinking-on rankings non-transferable `intake-1352#02`. (c) **OpenCode permissions at source:** `external_directory` defaults to ask and `opencode run` auto-rejects asks; the in-project boundary is the git worktree; bash arguments are not path-gated — a porous but real layer vs pi's none; the benchmark "grader peeking" was a sandbox defect, not a laxer OpenCode default `intake-1353#02`. (d) **Harness search on a small model:** on GPT-OSS-20B, stock OpenCode's held-out TB2.1 went 4.8% → 14.8% after the author's harness search (X post; run artifacts unpublished); per-fix attribution is noise-sized on the author's own August data, where 28 candidates were homogeneous within infra regime `intake-1351#record`, `intake-1362#record`. **Local bake-off requirement:** served models at production enable_thinking; columns pass@1, input tokens per attempt, prefix-cache hit share, prefill tokens per solved task (harnesses re-send 14–39 context windows per attempt, a ~2.8x spread) `intake-1363#02`. ✅ 2026-09-16 (`sub-hs4`) — rows (a)–(d) and the bake-off column set carried into the packet as context only, explicitly excluded from selection: [`hs4-harness-decision-package-20260916.md`](../../docs/design/hs4-harness-decision-package-20260916.md) §5. The bake-off itself is post-selection (HS-5b) and needs inference.

## Research Intake Update — 2026-09-17 (HS-E1: harness-null-pool evidence for HS-4)

_Via /research-intake Stage 4 (operator-approved plan 2026-09-17). External evidence only; HS-4 stays operator-owned and nothing here gates selection._

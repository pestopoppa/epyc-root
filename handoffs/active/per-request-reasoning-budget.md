# Per-Request Reasoning Budget for Hybrid SSM+MoE Models

**Status**: INVESTIGATION COMPLETE (Steps 1-2 done 2026-04-17; Steps 3-4 need running server)
**Created**: 2026-04-15
**Priority**: MEDIUM (unblocks per-request reasoning control, autopilot tuning)
**Categories**: llama.cpp, inference
**Depends on**: None
**Related**: [`v3-hybrid-ssm-regression.md`](v3-hybrid-ssm-regression.md), [`bulk-inference-campaign.md`](bulk-inference-campaign.md)

---

## Problem

`thinking.budget_tokens: 0` in the `/v1/chat/completions` request body does not suppress reasoning on Qwen3.5 hybrid SSM+MoE models. The server returns 210 chars of `reasoning_content` and empty `content` despite budget=0.

Works correctly on pure MoE models (Qwen3-Coder-30B — returns content, no reasoning).

Current workaround (2026-04-15): Removed `--jinja` flag from architect_general entirely. Without `--jinja`, llama-server uses generic ChatML template with no thinking scaffolding. Previous `--reasoning off` workaround was insufficient — the jinja template itself primed the model into think mode. This is even coarser — no reasoning capability at all, no per-request control.

## Why This Matters

Per-request reasoning control would enable:
1. Orchestrator sets `budget_tokens=0` for architect_general (structured TaskIR output, no thinking needed)
2. Orchestrator sets `budget_tokens=512` for architect_coding (useful for plan design)
3. AutoPilot tunes budget per role via NumericSwarm (explore quality-vs-speed tradeoff)
4. No server restarts — all control at API level

## Reproduction

```bash
# Server running WITH reasoning enabled (default --jinja, no --reasoning off)
# Qwen3.5-35B-A3B hybrid on port 8280

# budget=0 should produce NO reasoning — but it does (210 chars)
curl http://localhost:8280/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'
# → reasoning_content: 210 chars, content: empty

# Same request on pure MoE (Qwen3-Coder-30B, port 8082) works correctly
# → reasoning_content: none, content: "2 + 2 = 4"
```

## Investigation Plan

1. **Find budget enforcement**: In `llama.cpp-experimental`, search `tools/server/server.cpp` and `common/chat.cpp` for where `budget_tokens` is checked during token sampling/generation
2. **Trace hybrid code path**: The hybrid SSM+MoE models have recurrent layers that process tokens sequentially. Check if the `</think>` forced injection happens before or after the recurrent state update — if after, the SSM may have already committed to a reasoning trajectory
3. **Test fix**: When `budget_tokens=0`, inject `</think>` as the very first generated token (before any SSM state update). Verify on Qwen3.5-35B-A3B
4. **Test budget>0**: Verify that `budget_tokens=N` correctly caps reasoning at N tokens then transitions to content

## Investigation Results (2026-04-17, Steps 1-2)

### Budget Enforcement Pipeline (Fully Traced)

The reasoning budget is enforced via a **sampling-level state machine** — not a model-level control. The complete flow:

1. **Request parsing**: `server-common.cpp:1108-1118` reads `thinking.budget_tokens` → `reasoning_budget_tokens`
2. **Sampler init**: `sampling.cpp:260-299` creates `common_reasoning_budget_init()` with budget, start/end tag tokens, and prefill tokens
3. **State machine**: `reasoning-budget.cpp:59-127` implements:
   - `IDLE` → wait for `<think>` tag tokens
   - `COUNTING` → decrement remaining budget per generated token
   - `FORCING` → force `</think>` + fallback message by setting all other logits to -∞
   - `DONE` → passthrough (no more budget control)
4. **Logit forcing**: `reasoning-budget.cpp:129-149` — when `FORCING`, sets all logits to `-INFINITY` except the next forced token

### Root Cause: SSM State Update Race

The bug is specific to **hybrid SSM+MoE models** (Qwen3.5-A3B):

- **Attention layers** process the full context bidirectionally — budget forcing works because logit manipulation happens before the next token is committed
- **SSM/Mamba layers** update their recurrent state **during each token generation step** (`llama-context.cpp:3345-3354` accesses `llama_memory_hybrid`)
- When `budget_tokens=0`, the state machine promotes from `COUNTING` to `FORCING` at init (`reasoning-budget.cpp:201-204`), but the **prefill matching** (`reasoning-budget.cpp:221-246`) must first detect `<think>` in the prefill before promotion happens
- On hybrid models, the first generated token after `<think>` triggers an SSM state update that commits the model to a reasoning trajectory, even though the sampler is about to force `</think>`

### Proposed Fix (Steps 3-4, needs running server)

**Fix A** (minimal): In `reasoning-budget.cpp:200-204`, ensure `FORCING` state is set BEFORE the first token is generated when `budget=0` AND `<think>` is detected in prefill. Current code does this, but the SSM has already processed the prefill with `<think>` visible — the fix may need to strip `<think>` from the SSM prefill or inject `</think>` into the prefill itself.

**Fix B** (robust): For hybrid models, when `budget_tokens=0`, do not include `<think>` in the generation prompt at all. This means the chat template should suppress the think scaffold when budget=0 — modify `chat.cpp:1313-1331` to check budget before setting `thinking_start_tag`.

**Fix C** (workaround): Already deployed — remove `--jinja` flag entirely. Loses all thinking capability but avoids the SSM state commitment issue.

### Verified Test Protocol (for Steps 3-4)

```bash
# Test 1: budget=0 → no reasoning (the bug)
curl localhost:8280/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'

# Test 2: budget=512 → capped reasoning
curl localhost:8280/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"Prove sqrt(2) is irrational"}],"max_tokens":1024,"thinking":{"budget_tokens":512}}'

# Test 3: No regression on pure MoE (port 8082)
curl localhost:8082/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'
```

## Key Files (Updated with Line Numbers)

| File | Lines | Purpose |
|------|-------|---------|
| `tools/server/server-common.cpp` | 1108-1118 | Request budget parsing (OAI format) |
| `tools/server/server-common.cpp` | 1636-1644 | Anthropic format parsing |
| `tools/server/server-task.cpp` | 488-506 | Budget param extraction + tokenization |
| `common/chat.cpp` | 1313-1331 | Think tag setup for chat templates |
| `common/sampling.cpp` | 260-299 | Sampler init with reasoning budget |
| `common/reasoning-budget.cpp` | 59-127 | **State machine** (IDLE→COUNTING→FORCING→DONE) |
| `common/reasoning-budget.cpp` | 129-149 | **Logit forcing** (-∞ for non-forced tokens) |
| `common/reasoning-budget.cpp` | 200-204 | **Budget=0 promotion** (COUNTING→FORCING) |
| `common/reasoning-budget.cpp` | 221-246 | **Prefill detection** (initial state from prefill) |
| `src/llama-context.cpp` | 3345-3354 | **Hybrid SSM memory access** (root cause) |

## Success Criteria

- `budget_tokens=0` on Qwen3.5 hybrid → empty `reasoning_content`, non-empty `content`
- `budget_tokens=512` → reasoning capped at ~512 tokens, then content follows
- No regression on pure MoE models
- Orchestrator can thread `thinking.budget_tokens` through ChatRequest per role

## Research Intake Update — 2026-04-17

### Adaptive Reasoning Budget via Attention Entropy (Halo Framework)
- **[intake-392]** "Limited Reasoning Space" (arxiv:2602.19281) proposes replacing fixed token budgets with **entropy-based adaptive control**
- **Mechanism**: Monitor mean attention entropy across layers during inference (O(1), <1% overhead). When accumulated uncertainty exceeds threshold → trigger semantic compression (summarize reasoning so far) + context reset.
- **Results**: 76.4% on RULER (3x over AdaCoT), 1.29x token overhead vs Tree-of-Thoughts' 3.5x. Tested on Qwen2.5 (7B/72B), Mixtral, DeepSeek-V2-Lite.
- **No public implementation** — but architecturally simple. The Observer reads attention distributions already computed during inference. Could be exposed as a per-layer entropy metric in llama-server API.
- **Relevance**: Once budget_tokens enforcement works (the core problem above), entropy monitoring becomes the natural next step — adaptive budget instead of fixed cap. The Observer could feed the orchestrator a real-time "model is diverging" signal that triggers early `</think>` injection.
- **Implementation path**: (1) Expose per-layer attention entropy in llama-server, (2) orchestrator reads entropy signal, (3) orchestrator adjusts budget_tokens dynamically per-request based on entropy trend.

## Research Intake Update — 2026-05-04

### Endless-Repetition Feature Mechanism (Qwen-Scope Section 8)

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30) — Section 8 directly addresses a "stuck-in-X" failure-mode taxonomy that overlaps with this handoff's scope.
  - Mechanism: Qwen3-8B SAEs reveal specific repetition features whose pre-activation values rise sharply at the onset of endless repetition and remain elevated throughout — i.e. the model has a measurable internal precursor for entering a repetition loop. Bidirectional steering experiments confirm the features are *causal*: amplifying induces repetition on normal samples; suppressing reduces repetition on repetition-prone samples.
  - Important caveat the paper documents explicitly: the same repetition features fire on **benign repetition** (instruction-echo, multiple-choice answer-choice repetition). Naive feature-suppression at training time degrades the model's ability to do legitimate repetition. This is why Section 8 uses **rare-negative-rollout augmentation in DAPO** (one SAE-steered repetitive output per group of G rollouts) instead of the SASFT-style suppression of Section 7.
  - Reported results: SAE-guided rare-negative augmentation in RL drops the held-out repeat ratio sharply across Qwen3-1.7B / Qwen3-8B / Qwen3-30B-A3B versus vanilla DAPO under identical RL setup; on Qwen3-30B-A3B it also yields +5.84pp MGSM relative to the pre-RL baseline. Vanilla RL only +1.08pp on the same metric.
  - Delta from current approach: this handoff fixes the *enforcement* path for `budget_tokens` (state machine, logit forcing, hybrid SSM memory access). Qwen-Scope offers a *complementary diagnostic and training-time* path — SAE feature activations as a per-token "stuck-pressure" signal that could be exposed in the same way intake-392's mean attention entropy is proposed in the prior intake update. **Concrete connection**: the Halo entropy-based adaptive budget already proposed (2026-04-17 intake update above) and Qwen-Scope's repetition-feature pre-activation are two independent in-progress signals for the same underlying state — the model is about to fail to terminate. Both could be exposed in llama-server as per-decode-step scalars and used by the orchestrator to trigger early `</think>` injection.
  - Cross-link: the Ring-mini stuck-in-think failure mode documented in `research/deep-dives/ring-mini-stuck-in-think-failure-mode.md` (2026-05-04) is the closest analogue in our own diagnostic record. Ring-mini is non-Qwen so the Qwen-Scope SAEs do not transfer directly, but the methodology — identify the stuck-state feature → use its pre-activation as a precursor signal → manufacture rare-negative rollouts via amplification — is portable to any Qwen-family checkpoint that exhibits comparable budget-overrun failures.
  - Action: when budget enforcement in this handoff lands, add a follow-up exploratory task to (a) extract Qwen3-1.7B / Qwen3-8B Lethality-of-think feature ids using contrastive sets of completed-vs-overrun think traces from our own benchmark logs, (b) verify pre-activation rise pattern matches Section 8 Figure 19, (c) consider exposing the scalar in llama-server alongside attention entropy. Tracked in `qwen-scope-sae-toolkit.md`.
  - Caveats (Tier 2b): ICML 2025 "Steering Language Model Refusal with Sparse Autoencoders" reports broad-task degradation under feature steering; the rare-negative-rollout pathway largely sidesteps this because the model learns to *avoid* steered outputs rather than imitate them. Section 8 Table 7 still shows Qwen3-8B IFEval -2.08pp vs Before-RL — task-dependent regressions remain plausible at the intervention scale used.

## Research Intake Update — 2026-05-19

### CGR — concrete no-training Adaptive Thinking implementation

- **[intake-566] "Certainty-Guided Reasoning"** (arxiv:2509.07820, Nogueira/Sun/Silva/Zumot)
  - Direct match for this handoff's goal: **model-agnostic, no-fine-tune, single-knob** dynamic thinking budget. Periodically probes the LLM's own predicted probability over answer tokens during the CoT; terminates early once a target certainty threshold is reached. No auxiliary head, no draft model, no constrained decoding.
  - Headline: **AIME2025 baseline accuracy preserved while eliminating millions of tokens in aggregate** at the level of an evaluation run. Adds a **Grade metric** that penalizes incorrect answers and permits abstention — risk-sensitive evaluation aligns with our per-request budget framing.
  - Implementation cost on EPYC: a sampling-loop patch in our `epyc-llama` fork that, every N decode tokens, runs the answer-token probability probe and early-stops if above threshold. Estimated ~150 LoC + flag plumbing.

### External practitioner corroboration (with caveats)

- **[intake-542] @jun_song (Super-Tune) X post** — Korean local-LLM practitioner reports that after testing most viral X "speed tricks", only **Adaptive Thinking** + SFT-duplicate-suppression preserved quality at 100k+ context. Useful direction-setting signal; treat as anecdotal not validated.
- Tier 2b — **adaptive thinking failure modes ARE documented**: arxiv 2505.15400 ("When to Continue Thinking") shows models under-engage Continue-Thinking on hard questions AND over-invoke on easy questions — bimodally brittle. ASRR framework reports ~32.5% budget reduction at **non-zero ~1.2% pass@1 accuracy loss**. CGR's "preserves baseline accuracy" claim must be verified at our temperature/topk settings on our benches, not taken at face value.

### Speculative-decoding concurrency caveat — corroborates `project_slot_promotion_shelved`

- **[intake-567] ECHO** (arxiv:2604.09603) confirms vanilla EAGLE-3 underperforms autoregressive decoding at bs≈128, matching the @ZenMagnets reply to the jun_song thread. ECHO's own scheduler-level fix (sparse confidence gating, unified super-tree) **recovers and exceeds baseline** — so the blanket "spec-dec hurts high-concurrency" claim is true ONLY for naive vanilla implementations.
- Not actionable for EPYC today (single-user, bs≈1, SGLang-only ECHO impl), but useful as a "why our shelved decision was right" reference and as evidence for the slot-promotion-shelved reopen criteria.

**Concrete next step (this handoff)**: when prototyping the per-request budget infrastructure, design the API surface so CGR-style certainty-threshold early-stop slots in alongside the existing hard-cap budget. Both are values on a single "stop signal" abstraction.


## Research Intake Update — 2026-05-21

### SpecExit — speculative early-exit via draft-model hidden states

- **[intake-592] SpecExit: Accelerating Large Reasoning Model via Speculative Exit (arxiv:2509.24248, OpenReview)** — Tencent AngelSlim team. Predicts BOTH future tokens AND an early-exit signal directly from a lightweight draft model's hidden states — no separate probing overhead (a documented weak point of confidence-based or predicted-length-based early-exit). Claims: 66% average reasoning-trace length reduction, 2.5x end-to-end latency speedup vs SD baseline, accuracy maintained.
- **Mechanism**: Inspired by speculative decoding's hidden-state use. The draft model emits, in addition to candidate tokens, a scalar exit-signal predicted from the same forward-pass hidden state. Joint prediction eliminates the separate-probe overhead.
- **Why it matters for this handoff**: Directly aligns with this handoff's stated goal — "no fine-tune, model-agnostic, single-knob dynamic thinking budget." Adds a THIRD axis to the existing budget plumbing: (a) hard cap (this handoff's prior work), (b) certainty probe (CGR intake-566), (c) hidden-state-derived joint exit signal (SpecExit). Note: (a)+(b) compose; (c) sidesteps the probe-overhead limitation of (b).
- **Caveats (Tier 2b)**:
  - SpecExit's 2.5x is "additive vs SD baseline" — on EPYC at single-user bs=1, vanilla SD has been net-negative for Qwen3.6 with Qwen3-1.7B drafter (`project_slot_promotion_shelved`); SpecExit may inherit that gating issue unless tested with the reopen-criteria configurations (larger drafter, non-greedy verifier, long-context).
  - Early-exit mechanisms have documented failure modes: confidence overconfidence, predicted-length over-optimism on hard problems, progress-signal instability on complex tasks. SpecExit claims to mitigate by joint prediction, but third-party replication is absent at submission time.
  - 66% generation-length reduction is comparable to CGR (intake-566) and dynamic-early-exit (arxiv:2504.15895) — head-to-head ablation against these on the same benchmark suite has not been published.

### Concrete next step for this handoff

When budget enforcement infrastructure (Step 3-4: state machine, logit forcing, hybrid-SSM memory access) lands and a running server is available, add SpecExit-style hidden-state probe as a third stop-signal source in the API surface design. The abstraction is already framed (per the prior 2026-05-19 CGR intake update): a single "stop signal" abstraction over which hard-cap / certainty-threshold / hidden-state-exit are interchangeable producers.

Cross-references: [[angelslim-techniques-evaluation]] (umbrella stub), [[reasoning-compression]], [[memento-block-reasoning-compression]], [[decision-aware-routing]].

## Research Intake Update — 2026-05-24

### New Related Research

- **[intake-603] "Deep Think with Confidence (DeepConf)"** (arxiv:2508.15260)
  - Relevance: Confidence-gated filtering/early-termination of reasoning traces is a per-request reasoning-budget lever that reports **up to 84.7% fewer generated tokens** vs full parallel self-consistency, with up to 99.9% on AIME 2025 (DeepConf@512). Training-free, framed as serving-framework-integrable, validated on Qwen3 (our frontdoor/architect family).
  - Key technique: model-internal confidence signal gates which traces continue/vote; online + offline variants.
  - Reported results: AIME2025 ~99.9% @512 traces; −84.7% tokens vs full parallel thinking.
  - Delta from current approach: our budget control is template/stop-signal-driven (hard-cap / certainty-threshold / hidden-state-exit). DeepConf adds a **confidence-weighted multi-trace** producer that fits the existing "stop signal" abstraction as a fourth source. The token-reduction claim is the headline win on a BW-bound CPU — but the 99.9% is at 512 traces (large absolute compute), and like all voting methods it is candidate-bounded (cannot recover a correct answer never sampled). Prototype against a local Qwen3 server and measure real CPU t/s + accuracy (standalone llama-bench only — no run_benchmark.py).

- **[intake-602] "Chain-of-Thought Reasoning Without Prompting (CoT-Decoding)"** (arxiv:2402.10200)
  - Relevance: Decode-level, training-free elicitation of reasoning — directly relevant to eliciting/suppressing reasoning per request without a thinking template (the core problem of this handoff for hybrid SSM models where `budget_tokens:0` fails).
  - Key technique: branch into top-k first tokens (vs greedy); CoT paths emerge among continuations; answer-token confidence gap selects the reasoning path.
  - Delta from current approach: implementable in our full-control llama.cpp fork as a sampler variant. Caveat: top-k branching multiplies decode passes — net win unproven on BW-bound CPU; measure before committing.

- **[intake-601] "OptiLLM" optimizing inference proxy** (github: algorithmicsuperintelligence/optillm) — its ThinkDeeper module emulates a `reasoning_effort` parameter and DeepConf/CoT-decoding/entropy-decoding are bundled as modules; useful **pattern** reference for the per-request reasoning-budget API surface. **Correction (2026-05-24 deep-dive):** these local modules are HuggingFace-transformers-only in OptiLLM (in-process model + hooks) and do NOT run over llama-server — they are reimplementation targets, not drop-in. DeepConf-offline + CoT-decoding need only `top_logprobs` (which llama-server exposes), so a proxy/fork reimplementation is feasible; ThinkDeeper is transformers-only. Headline "2-10x" is marketing — see intake-601 contradicting_evidence.

### Actionable (decided 2026-05-24): DeepConf-offline FIRST

DeepConf-offline is the highest-ROI item from this intake and is scheduled ahead of the OptiLLM-style method-selection axis. It is a **proxy-layer reimplementation** (N parallel llama-server completions with `top_logprobs` → bottom-10% group-confidence filter → confidence-weighted vote) — no llama.cpp fork needed for the offline variant. Build + sanity-check in a dedicated session, then hand the `n_traces / percentile-η / window / warmup / group-metric` sweep to autopilot's NumericSwarm. **Tracked as P21.A in [`routing-and-optimization-index.md`](routing-and-optimization-index.md); full analysis in [`research/deep-dives/optillm-test-time-techniques.md`](../../research/deep-dives/optillm-test-time-techniques.md).** Sanity-check needs a local Qwen3 server → **stop the running autopilot first** (no-concurrent-inference). The DeepConf-online (mid-generation early-stop) variant is fork work, deferred. Cross-ref: [[reasoning-compression]], [[decision-aware-routing]].

**UPDATE 2026-05-24 (A2 done — NOT adopting):** built as an isolated spike (41 tests) and validated against live Qwen3.6. **Decisive negative:** DeepConf's confidence-weighted vote ties plain majority (3/4 = 3/4, no gain), and the confidence signal is anti-correlated with correctness (top-1-confidence 1/4; correct-vs-wrong gap −0.158) — the model is overconfident on wrong short answers. So DeepConf adds N× generation + `n_probs` cost for **zero accuracy benefit** on our stack. Not wired into the orchestrator or autopilot; no branch/worktree is needed for the remaining bulk-inference run. Reasoning-budget control for this handoff should rely on the existing stop-signal/template levers, not DeepConf. Full data: [`research/deep-dives/optillm-test-time-techniques.md`](../../research/deep-dives/optillm-test-time-techniques.md) §P21.A Outcome.

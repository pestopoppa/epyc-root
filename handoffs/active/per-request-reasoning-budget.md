# Per-Request Reasoning Budget for Hybrid SSM+MoE Models

**Status**: INVESTIGATION COMPLETE (Steps 1-2 done 2026-04-17; Steps 3-4 need running server)
**Created**: 2026-04-15
**Priority**: MEDIUM (unblocks per-request reasoning control, autopilot tuning)
**Categories**: llama.cpp, inference
**Depends on**: None
**Related**: [`v3-hybrid-ssm-regression.md`](../completed/v3-hybrid-ssm-regression.md), [`bulk-inference-campaign.md`](bulk-inference-campaign.md)

---

## Problem

`thinking.budget_tokens: 0` in the `/v1/chat/completions` request body does not suppress reasoning on Qwen3.5 hybrid SSM+MoE models. The server returns 210 chars of `reasoning_content` and empty `content` despite budget=0.

Works correctly on pure MoE models (Qwen3-Coder-30B — returns content, no reasoning).

Current workaround (2026-04-15): Removed `--jinja` flag from architect_general entirely. Without `--jinja`, llama-server uses generic ChatML template with no thinking scaffolding. Previous `--reasoning off` workaround was insufficient — the jinja template itself primed the model into think mode. This is even coarser — no reasoning capability at all, no per-request control. **Stale premise (PRB-T1, 2026-08-21): this workaround was reversed on 2026-06-26 (commit `f4a8a3ca`) and `architect_general` has launched WITH `--jinja` ever since. The paragraph above is retained as history, not current state.**

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
  - Action: when budget enforcement in this handoff lands, add a follow-up exploratory task to (a) extract Qwen3-1.7B / Qwen3-8B Lethality-of-think feature ids using contrastive sets of completed-vs-overrun think traces from our own benchmark logs, (b) verify pre-activation rise pattern matches Section 8 Figure 19, (c) consider exposing the scalar in llama-server alongside attention entropy. Tracked in `../completed/qwen-scope-sae-toolkit.md` (archived 2026-06-12; the repetition-feature methodology is preserved there).
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

## Stop-signal abstraction — design only (2026-07-29)

This is an interface contract for a future **experimental** reasoning controller, not a production sampler feature. The existing `budget_tokens` state machine is the only executable producer today; Step 3/4 must first prove it correct on hybrid SSM models. No producer may waive a quality gate or modify the frozen production kernel.

Each producer may emit, at a decode boundary:

```text
StopSignal { producer: hard_cap | certainty_probe | draft_hidden_exit,
             disposition: continue | request_close_think | abstain,
             evidence_ref: trace-local immutable observation reference,
             confidence: optional [0,1], next_eligible_token, reason_code }
```

The controller is a deterministic arbiter. `hard_cap` is authoritative once its existing state machine reaches the forcing boundary. Every other producer is **advisory and fail-closed**: missing evidence, unsupported architecture, invalid confidence, or disagreement means `continue`, not early close. A request acts only at the next eligible decode boundary using the same explicit closing-token path as hard cap; it never edits a prompt retrospectively or claims the model finished answering.

| Producer | Admission before it may request close |
|---|---|
| `hard_cap` | Source-proven budget state machine plus this handoff's hybrid budget=0 and pure-MoE regression checks |
| `certainty_probe` (CGR-shaped) | Versioned probe cadence/answer-token contract, saved signal, and paired quality + total-token non-inferiority evidence |
| `draft_hidden_exit` (SpecExit-shaped) | Experimental-kernel-only hidden-state contract, draft/target compatibility and output parity, and paired quality + latency evidence |

Confidence values are not comparable or scalarized. Enable at most one advisory producer per explicit experiment identifier; unsupported paths emit `abstain`. For every non-hard-cap request retain producer/version, request/decode positions, disposition, reason code, raw-signal reference, and later scorer result. This permits deterministic replay and detects overconfident early exits without rerunning inference. Such records are observations until a measurement protocol supplies the quality gate.

## Progress checklist

- [x] Step 1-2: trace budget-enforcement pipeline + root-cause (SSM state-update race, 2026-04-17) ✅
- [x] DeepConf-offline spike - NOT adopting (zero accuracy benefit, 2026-05-24) ✅
- [ ] Step 3: implement fix (force </think> / suppress think scaffold at budget=0 for hybrid SSM), needs running server
- [ ] Step 4: verify budget>0 caps reasoning at N tokens; no regression on pure MoE
- [ ] Thread thinking.budget_tokens through ChatRequest per role
- [x] Design stop-signal abstraction to slot in CGR certainty-threshold / SpecExit hidden-state exit ✅ 2026-07-29 — design-only deterministic `StopSignal`/arbiter contract: hard cap remains the only executable authority; CGR and SpecExit are advisory, one-at-a-time, fail-closed producers pending source, parity, and paired quality/total-token evidence. No production sampler, server, or kernel change.

## Research Intake Update — 2026-08-21 (chat-template dive, intake-1212…1217)

- [x] **PRB-T1** — Re-examine the standing `--jinja` removal workaround. It was adopted because the
      jinja template "primed the model into think mode", surrendering per-request reasoning control
      entirely. A 2026-08-21 dive rendered both the stock `Qwen/Qwen3.8-27B` template and the
      Unsloth template embedded in our production GGUF: **both handle `enable_thinking=false`
      correctly**, suppressing the reasoning-instruction block and emitting the proper empty-think
      prefill. What the templates *do* have is a fatal `raise_exception` on any `reasoning_effort`
      outside `{xhigh, medium, low}` — and an `xhigh` default that injects a 209-character
      instruction when no kwargs are passed. Determine whether the behaviour that motivated
      removing `--jinja` was actually one of those, and whether the workaround is still needed.
      ✅ 2026-08-21 — **OBSOLETE: already reversed 2026-06-26 by commit `f4a8a3ca`**; compiled priors
      emit `jinja: true` for architect_general and the J12 gate passed 2026-07-06 (0 think-leaks, n=15).
      Neither Qwen3.8 template defect motivated it — both post-date the workaround by four months.
- [x] **PRB-T2** — **TALE-EP (intake-1215) needs no server support at all.** This handoff's
      objective is per-request reasoning control and it has been blocked since 2026-04-17 on server
      support for `thinking.budget_tokens`. TALE puts a per-question numeric token budget in the
      *prompt*, estimated zero-shot by the model itself — reported at 67% token reduction for
      −2.72% average accuracy, and +3.11% accuracy on GSM8K at 75.7% fewer tokens. Evaluate it as
      the unblock path. Caveats to carry: MathBench-College shows −8% / −4%, far worse than the
      headline; and the estimator costs an extra model call, cheap on closed APIs and not obviously
      cheap on our bandwidth-bound CPU decode.
      ✅ 2026-08-21 — **evaluation DESIGNED (below); run is PRB-T4.** Key find: the harness already
      exists (`eval_tale_budget.py`, 2026-04-09) and has never been run; it does not charge the
      estimator call, and neither intake-1215 anchor suite (GSM8K, MathBench) is in our question pool.
- [x] **PRB-T3** — Confirm whether a top-level `reasoning_effort` field survives to the template on
      our llama-server path or is consumed by the server before render. Untested in the dive (needs
      a running server). The same silent-no-op shape is already recorded from a different vendor and
      stack in intake-946, where a top-level `enable_thinking` field was ignored and only
      `chat_template_kwargs` took effect.
      ✅ 2026-08-21 — **DECISIVE: a top-level `reasoning_effort` is DROPPED** — 0 occurrences tree-wide
      in frozen v9, and the jinja global set is a closed literal; `chat_template_kwargs` is the ONLY
      body→template route. Same silent-no-op shape as intake-946. Static analysis; see below.

### PRB-T1 findings — the `--jinja` workaround is OBSOLETE (reversed 2026-06-26)

**Verdict: obsolete and already reversed. No action needed to restore `--jinja`; it is on today.**

Lifecycle of the workaround:

| Event | Commit | Date | Evidence |
|---|---|---|---|
| Adopted (drop `--jinja` for architect_general) | `0879ed56` | 2026-04-15 | `git log -1 0879ed56`: "fix: drop --jinja for architect_general to prevent Qwen3.5 hybrid think-loops" |
| Reversed (re-include in `--jinja`) | `f4a8a3ca` | 2026-06-26 | `git log -S'architect_general no longer excluded from --jinja' -- src/registry/stack_priors.py` returns exactly this commit: "Determinism: honor declared temps + fixed seed + unify sampler; route architect to chat-completions" |
| Gate satisfied | — | 2026-07-06 | `orchestration/reports/j12_think_loop_probe_20260706T143621Z/summary.json` |

Current state, three layers, all agreeing that `--jinja` is ON for `architect_general`:

1. **Prior** — `src/registry/stack_priors.py:2280-2283` sets `"jinja": bool((mode == "default") or (mode == "worker_pool" and worker_type == "explore"))`. `architect_general` is `mode == "default"`, so the prior is unconditionally `True`. The comment at `:2272-2279` records the reasoning: the 2026-04-15 exclusion "made the registry's `enable_thinking=false` inert (kwarg only applies on the `/v1/chat/completions`+jinja path)".
2. **Compiled** — `orchestration/derived/stack_priors.yaml:357` → `jinja: true`, inside the `architect_general` record (block opens `:300`; confirmed by content, not position — `slot_save_path: /mnt/raid0/llm/cache/kv_slots/architect_general` at `:354`). Compiled at `2026-08-11T01:36:33Z` (`:51`). Of the 12 compiled flag blocks only `vision_escalation` (`:1889`) and `worker_vision` (`:2975`) carry `jinja: false`.
3. **Launcher** — `scripts/server/orchestrator_stack.py:1345` `_build_role_command` loads `flags = _runtime_flags(runtime)` from `_stack_prior_launch(role_name)` (`:235`, reads `STACK_PRIORS_PATH`), then at `:1402`: `if flags.get("jinja", role_name != "architect_general") is True: cmd.append("--jinja")`. The architect_general exclusion survives **only as the dict default**; the compiled priors supply an explicit `True`, so the default is unreachable for this role.

**The gate named in the code actually ran and passed.** `stack_priors.py:2278` says the re-inclusion was "Gated on the J12 think-loop suppression probe before trusting". That probe exists (`scripts/benchmark/j12_think_loop_probe.py`) and its one recorded run — `orchestration/reports/j12_think_loop_probe_20260706T143621Z/summary.json` — reports for `architect_general`: `n: 15`, `think_leaks: 0`, `repetition_loops: 0`, `known_wait_reference_loops: 0`, `empty: 0`, `error_answers: 0`, `expect_matches: 14` (one miss, `plan_02`). `frontdoor` 15/15 clean. The gate is satisfied, not outstanding.

**Was the original motivation one of the 2026-08-21 template defects? No.** The workaround targeted Qwen3.5-122B-A10B hybrid `<think>` loops on a model that no longer sits on this role (it vacated to `architect_critic` :8074 — `stack_templates/default.yaml:156-160`). The `reasoning_effort` `raise_exception` and the 209-char xhigh default are properties of the **Qwen3.8** template only (sha12 `12827f24b742`), which post-dates the 2026-04-15 workaround by four months. The three older fleet templates (sha12 `55d4931433fe`, `8452ca85cb1e`) do not carry them at all. So the two are unrelated findings that happen to touch the same flag.

**Reconciliation with the model swap — three planes disagree, and that divergence is itself the finding:**

| Plane | Says architect_general is | Citation |
|---|---|---|
| Stack template | `Qwen3.8-27B-Q8_0` | `stack_templates/default.yaml:139` (commit `1cff5162`, 2026-08-20) |
| Compiled priors | `qwen3.6-27b-mtp-q8_0` / `Qwen3.6-27B-MTP-Q8_0` | `orchestration/derived/stack_priors.yaml:304-305` |
| MASTER registry | `model_role: qwen36_27b_mtp_q8_local` | `orchestration/model_registry.yaml:1501` |

Literal-string `Qwen3.8` count: **0** in `orchestration/model_registry.yaml` and **0** in `orchestration/derived/stack_priors.yaml`. (A bare `grep "Qwen3.8" orchestration/model_registry.yaml` returns 4 hits, but all four are the regex `.` matching `Qwen3-8B-DFlash-b16` at `:506-511` — not the model. The dispatching session's "zero occurrences" is correct.) **Only the stack template names Qwen3.8.** The compiled priors were generated 2026-08-11, nine days before the 2026-08-20 template change, so they have not been recompiled since the swap. UNVERIFIED whether that is intentional staging or drift — flagged here, not resolved (recompiling the registry is not this subagent's write).

Consequence for this handoff: because `--jinja` is on, the GGUF's embedded template renders on every `/v1/chat/completions` request. Once the priors are recompiled the template that renders will be the Qwen3.8 one carrying the `reasoning_effort` raise. The MASTER registry pins `chat_template_kwargs.enable_thinking: false` for this role (`orchestration/model_registry.yaml:1499-1500`) and the raise sits inside the `enable_thinking` gate, so it stays unreachable at production posture — but the margin is one config flip wide.

**Residual defect (not fixed — code edits are outside this subagent's write scope).** `scripts/server/orchestrator_stack.py:1397-1402` still carries the reversed policy as both a comment ("SKIP for architect_general — Qwen3.5 hybrids enter infinite `<think>` loops") and a live fallback default. It is inert while the priors compile, but if `_stack_prior_launch` ever returns `{}` for this role (role absent from compiled priors — a real possibility given the plane divergence above), `flags.get("jinja", role_name != "architect_general")` silently resolves to `False` and architect_general launches **without** `--jinja`, re-inerting `enable_thinking=false`. Recommend deleting the role-specific default and the stale comment; prepared for the owning session, not applied here.

### PRB-T3 findings — a top-level `reasoning_effort` is DROPPED

**Static analysis of the frozen production tree `/mnt/raid0/llm/llama.cpp` @ `0db32c06e` (`git rev-parse --short HEAD`). Read-only; nothing built, modified, or committed.**

**Answer: a top-level body field `reasoning_effort` is neither server-consumed nor template-visible. It is silently discarded** — the same shape intake-946 records for a top-level `enable_thinking`.

1. **No code can read it.** `grep -rn "reasoning_effort" --include='*.cpp' --include='*.h' --include='*.hpp' .` over the whole frozen tree returns **0 matches**. Per-file `grep -c` over all 13 of `tools/server/*.cpp` plus `common/chat.cpp` returns 0 for every file. The identifier does not exist in the kernel.

2. **The jinja global set is a closed literal.** `common/chat.cpp:883-895`, in `common_chat_template_direct_apply_impl`, builds the render variables explicitly:

   ```cpp
   nlohmann::ordered_json inp = nlohmann::ordered_json{
       {"messages", messages_override.has_value() ? *messages_override : inputs.messages},
       {"bos_token", tmpl.bos_token()},
       {"eos_token", tmpl.eos_token()},
       {"enable_thinking", inputs.enable_thinking},
   };
   ```

   The only further additions are `tools` (`:896-898`, conditional), every key of `inputs.extra_context` (`:900-905`), every key of `additional_context` (`:905-910`), and `add_generation_prompt` (`:911-913`). `jinja::global_from_json(ctx, inp, inputs.mark_input)` (`:920`) then installs exactly that object as the template's globals. **There is no request-body spill anywhere in this function** — an arbitrary top-level field can reach the template only by first becoming an `extra_context` key.

3. **`extra_context` is date helpers plus `chat_template_kwargs`, and nothing else.** `common/chat.cpp:2714-2717`:

   ```cpp
   params.extra_context = common_chat_extra_context();
   for (auto el : inputs.chat_template_kwargs) {
       params.extra_context[el.first] = json::parse(el.second);
   }
   ```

   and `common_chat_extra_context()` (`common/chat.cpp:2543-2551`) returns an object containing only `datetime` and `date_string`.

4. **`chat_template_kwargs` passthrough — CONFIRMED, and it is a two-layer merge.** `tools/server/server-common.cpp:1073-1077`, inside `oaicompat_chat_params_parse`:

   ```cpp
   auto chat_template_kwargs_object = json_value(body, "chat_template_kwargs", json::object());
   inputs.chat_template_kwargs = opt.chat_template_kwargs;
   for (const auto & item : chat_template_kwargs_object.items()) {
       inputs.chat_template_kwargs[item.key()] = item.value().dump();
   }
   ```

   Server-launch defaults seed the map and the per-request object overrides key-by-key. `opt.chat_template_kwargs` comes from `params_base.default_template_kwargs` at model load (`tools/server/server-context.cpp:1479`), which `--chat-template-kwargs` and `--think` populate (`common/arg.cpp:3285`, `:3433-3436`). **`chat_template_kwargs` is therefore the ONLY route from a request body to a template variable** — which is exactly why the registry's `enable_thinking: false` is expressed as a kwarg and why dropping `--jinja` made it inert (PRB-T1).

5. **Which top-level reasoning fields ARE read** (the contrast makes the omission exact): `reasoning_format` (`server-common.cpp:1061-1062`), `reasoning_budget_tokens`, `reasoning_budget_message`, `reasoning_control` (`:1120-1131`), and the Anthropic-shape `thinking.budget_tokens` → `thinking_budget_tokens` mapping (`tools/server/server-chat.cpp:577-585`). `reasoning_effort` appears in none of them. Note `enable_thinking` gets a *special* second read out of the kwarg map at `server-common.cpp:1080-1087`, including a type guard that raises on a quoted string — there is no equivalent for `reasoning_effort`.

6. **No unknown-field rejection anywhere on the path.** The body is read key-by-key through `json_value(body, ...)`; `grep -n "unknown\|unrecognized\|unsupported param" tools/server/server-common.cpp tools/server/server-task.cpp` returns nothing. `server-chat.cpp:570` even shows the Anthropic bridge forwarding only an explicit whitelist (`temperature`, `top_p`, `top_k`, `stream`, `chat_template_kwargs`). An unrecognised top-level key produces **no error and no warning**: a silent no-op.

**Consequence.** The Qwen3.8 template's `reasoning_effort` `raise_exception` can only fire if `reasoning_effort` is passed *inside* `chat_template_kwargs`. A top-level `"reasoning_effort": "none"` cannot reach it — and cannot reach anything else either. Any orchestrator code that sets a top-level `reasoning_effort` against our llama-server is a no-op today.

**Status: static analysis of frozen v9 only.** Live-render confirmation still wants a `POST /apply-template` when a server is next up (route registered `tools/server/server.cpp:262`, handler `tools/server/server-context.cpp:4981`): render the same body twice, once with `reasoning_effort` top-level and once with it under `chat_template_kwargs`, and diff the returned prompt. The static path is decisive on its own; the live check is belt-and-braces and would also demonstrate the raise.

### PRB-T2 findings — TALE-EP evaluation design (design only; the run is PRB-T4)

**The harness already exists and has never been run.** `epyc-inference-research/scripts/benchmark/eval_tale_budget.py` (409 lines, commit `f5b67614`, 2026-04-09) implements the arms below and already prints a per-suite breakdown (`:300-321`) and a β distribution (`:322-328`). `data/tale_budget/` does not exist on disk → zero recorded runs. What follows is therefore the *delta* needed to make it decision-grade, not a new script.

**Target.** `architect_general` :8083 — the thinking-capable Qwen role whose template carries the 2026-08-21 defects. Model is `Qwen3.8-27B-Q8_0` per `stack_templates/default.yaml:139`, GPU/MI210; if the priors are not recompiled by run time it will actually launch Qwen3.6-27B (`derived/stack_priors.yaml:304`). **Record which GGUF actually served — do not assume from the template.** Add one CPU-decode replicate on `frontdoor` :8080 (Qwen3.6-35B-A3B, `derived/stack_priors.yaml:784`), because intake-1215's overhead caveat is specifically about bandwidth-bound CPU decode and a GPU-only result cannot answer it.

**Posture.** Production posture — `chat_template_kwargs.enable_thinking: false` (`model_registry.yaml:1499-1500`), `--reasoning off`, `--jinja` on. That is what we serve, so that is what the decision is about. TALE-EP is a *prompt*-level budget and needs no thinking channel to work.

**Arms** (harness `--conditions`, all three):
1. `baseline` — question verbatim, no brevity constraint.
2. `static` — fixed per-suite limit (`STATIC_LIMITS`, `:41-49`). **Not optional**: it is the control that says whether any gain is TALE's *estimation* or merely brevity.
3. `tale` — two calls: zero-shot self-estimate (`TALE_PREPASS_PROMPT`, `:51-56`, `max_tokens=32`) → `"Answer in under {beta} words.\n\n" + question` (`:58`), β clamped to [10,500] (`:185`).

**Suites — per-suite reporting is mandatory.** From `benchmarks/prompts/question_pool.jsonl` (79,479 questions, 38 suites, verified by direct count):

| Class | Suite | Pool n | Take per arm |
|---|---|---|---|
| Math (where the CCoT hazard lives) | `math` | 1,819 | 150 |
| Math (hard) | `olympiadbench` | 674 | 100 |
| Knowledge | `mmlu_pro` | 12,032 | 150 |
| Coding | `livecodebench` | 2,360 | 100 |

n=500 per arm × 3 arms = 1,500 generations + 500 estimator calls ≈ 2,000 requests per host.

**Anchor mismatch — state it before the run, not after.** intake-1215's one favourable headline is **GSM8K (+3.11% accuracy at 75.7% fewer tokens)** and its worst caveat is **MathBench-College (−8% / −4%)**; the average is **67% token reduction for −2.72% accuracy**. **Neither anchor suite exists in our pool** — there is no `gsm8k` and no `mathbench` among the 38. `math` and `olympiadbench` are substitutes, not replications. This run therefore **cannot confirm or refute either published number**; it can only measure our own stack. (The harness's `STATIC_LIMITS["gsm8k"]` key at `:43` is dead for the same reason.) Do not report a result as agreeing or disagreeing with intake-1215.

**Two harness gaps to close first** (both small, both in `eval_tale_budget.py`):
- **The estimator call is never charged.** `estimate_tale_budget` at `:179` does `text, _, _ = generate_response(...)`, discarding tokens and elapsed, and `TrialResult` (`:60-71`) has no field for them. Without this, the extra-call overhead measurement is impossible and TALE's savings are overstated by construction. Add `estimator_tokens` / `estimator_s` and report savings **net** of them.
- **Words vs tokens.** The docstring cites TALE's "use less than {beta} **tokens**" (`:13-14`) but the implemented prompt says "**words**" (`:51-56`, `:58`). A word budget is not the published intervention. Pick one, and say which in the write-up.
- Also: `generate_response` hardcodes `temperature=0.0` (`:117`). Pin to the role's declared production temperature + seed 42 per measurement policy, since accuracy here is sampling-sensitive.

**Metrics**, per suite × arm: accuracy, mean completion tokens, mean latency, OAA (`eval_metrics.compute_batch_oaa`, α=0.5), β distribution; TALE only: estimator tokens/latency and **net** token change = (estimator + answer) − baseline answer. Scoring already delegates per-question to `debug_scorer.score_answer` with the pool's declared `scoring_method` (`:157-167`), so it is not a hardcoded substring match.

**Decision rule** (fixed in advance):
- **ADOPT** if, on ≥3 of the 4 suites, net token reduction ≥ 30% **and** accuracy delta ≥ −1.0pp, **and** no single suite is worse than −3.0pp, **and** `tale` beats `static` on net tokens at equal-or-better accuracy.
- **ADOPT `static` INSTEAD** if `static` matches or beats `tale` on net tokens at equal accuracy — then TALE's estimator call is pure overhead and the cheap arm wins.
- **DECLINE** if any suite loses > 3.0pp, or net reduction < 15% once the estimator call is charged.
- **INCONCLUSIVE** otherwise → re-run at n=400/suite before deciding.
- Report a bootstrap CI per suite; at n=100–150 a single-question flip is noise, not a regression (`feedback_per_suite_gate_resolution_artifact`).

**Cost / gating.** ~2,000 requests per host, exclusive inference window, autopilot stopped first (no-concurrent-inference).

- [ ] **PRB-T4** — **Run the PRB-T2 TALE-EP evaluation.** Gated on an exclusive inference window (no
      server is up as of 2026-08-21 and that is intentional). Pre-run: close the three
      `eval_tale_budget.py` gaps above (charge the estimator call, resolve words-vs-tokens, pin
      temperature+seed); confirm which GGUF actually serves :8083. Then run the 4 suites × 3 arms on
      `architect_general`, plus the `frontdoor` CPU-decode overhead replicate, and apply the fixed
      decision rule. On completion the run produces measurements → file the belief-kernel adapter
      wiring task at the same boundary (source row in `scripts/vidya/adapters/README.md`).

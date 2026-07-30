# Reasoning Effort Levels — prompt-conditioned quality/token ladder

**Status (2026-07-20): STUB — idea captured, not yet designed.** Operator idea, raised while reading the
R2a result in [`architect-model-selection-bench.md`](architect-model-selection-bench.md).

**One-line purpose:** give every role a **tunable reasoning-effort dial** — a spectrum of prompt
conditions (and token budgets) trading generated tokens for quality — instead of the current binary
"reasoning on / reasoning off", so latency-sensitive roles can buy *some* reasoning without paying full CoT.

> **⚠ 2026-07-22 — a THIRD axis surfaced that may matter stack-wide: `max_tokens` (completion budget) as a
> silent quality lever.** See **§ Token-budget study** below. Short version: on hard problems, models get
> *truncated mid-reasoning* and score wrong for a budget reason, not a capability reason — a ~57pp swing was
> measured on one suite. Production budgets may be below the "knee" for several stack models. The operator
> flagged this as worth a dedicated later-session study across the whole stack.

## Motivating evidence (measured, not hypothesised)

Arm A4 = **Qwen3.6-35B-A3B (production frontdoor)**, GPQA-Diamond, **identical 50 questions**,
`enable_thinking=false` in BOTH arms — the only change is what the prompt asks for:

| Prompt condition | accuracy | mean tokens |
|---|---:|---:|
| "Answer with the letter only" | 52.0% | 537 |
| "Reason step by step, then answer" | **84.0%** | 2150 |
| **Δ** | **+32.0pp** (McNemar b=19 c=3, **p=8.6e-04**) | **4.0×** |

So the two endpoints of the ladder are real, large, and cheap to measure. 84.0% also sits within noise
of the vendor-published 86.0% for this model, so the high end is a genuine ceiling, not an artifact.
Full protocol + provenance in the R2a section of the architect bench handoff.

## The core design question
**Are there useful intermediate points, and is the accuracy/token curve smooth or a step?** If it is
smooth, effort becomes a real dial. If it is a step function (you either reason or you don't), the
"ladder" collapses to a binary and the work is just picking the threshold per role.

## ⚠ INVARIANT — effort is calibrated PER MODEL, and never inherited (operator, 2026-07-20)
**The ladder is a property of a (model, quant) pair, not of a role and not of the stack.** Every model
gets its own curve measured independently; a level that is optimal for one model says nothing about the
same level on another. Two independent results from 2026-07-20 already show per-model divergence on
*adjacent* dials:
- **Native thinking (R2b):** Qwen3.6-35B-A3B fails to terminate `<think>` on 48% of items even at a
  16384-token budget, making thinking-ON catastrophic **for that model**. Whether Qwen3.5-122B-A10B-IQ2
  does the same is a *separate measurement* — explicitly not generalized.
- **Spec-dec draft depth:** the measured optimum differs per model on the same GPU and kernel
  (122B-IQ2 → `n-max 2`; 27B-dense and 35B-A3B → `n-max 4`). Inheriting one model's setting cost ~29%
  throughput. Same failure shape, different dial.

**Consequences, binding on the design:**
1. Effort levels are **defined** generically (prompt templates) but **certified per model** — no level is
   "enabled" for a model until that model's own curve has been measured.
2. A **role default is a (model × level) pair.** Swapping the model bound to a role, or changing its
   quant, **invalidates the level** and requires re-calibration (see E-7).
3. Store the curves **indexed by model/quant, never by role** ([[feedback_model_not_role_indexing]]),
   so a model serving three roles is measured once and a role swap cannot silently inherit a stale level.
4. Do not extrapolate across quants of the same model either — quantization is exactly what the parent
   architect bench is testing for reasoning damage.

## ⚠ Design constraint learned the hard way (2026-07-20)
**Do NOT implement effort as a bare `max_tokens` cap.** A hard cap truncates the model *mid-derivation*,
and a truncated answer scores **wrong** — you lose the quality without the model ever getting to state a
cheaper answer. This exact failure was observed repeatedly today (AIME at 4096: response cut mid-working,
scored a garbage `1`; CoT at 8192: ~20% truncation; and the historical `enable_thinking` probe whose
"+33pp for thinking-off" is most likely this same artifact — see
[[feedback_parse_failure_rate_is_a_scoring_artifact]]).
**Effort must be steered primarily by the PROMPT** ("answer in at most two sentences of reasoning",
"give a brief justification then answer"), so the model *plans* a short answer and still emits a
well-formed final answer. A token cap is at best a backstop, and if used it needs a
`--reasoning-budget-message`-style graceful-close so the model terminates cleanly instead of being cut.

## § Token-budget study — `max_tokens` as a stack-wide quality lever (operator-flagged 2026-07-22)

**The finding.** On hard tasks, models are truncated *mid-reasoning* by the completion-token ceiling and
score wrong for a **budget** reason, not a capability reason. This is a distinct axis from prompt-effort and
native-`<think>`: it is the raw `max_tokens` a request is allowed. Measured across this session:

| Suite (arm A1 122B-IQ2 unless noted) | budget | truncation | overall acc | acc among FINISHED | Δ from budget |
|---|---:|---:|---:|---:|---|
| AIME'25 avg@4 | 16384 | 6% | 71.7% | 76.1% | small |
| gpqa_diamond_cot | 4096→8192 | ~20%→low | — | — | raised mid-session |
| **olympiadbench_hard (pilot n=24)** | 16384 | **46%** | **50.0%** | **76.9%** | **≈ +27pp latent** |

On `olympiadbench_hard` the model **largely can solve the problems** (76.9% when it finishes) but the
measured score is 50.0% because 46% get cut off (truncated-and-correct: only 2/11). That is a **~57pp swing
between finished and truncated** driven purely by token budget. Related but *distinct* failure: native
`<think>` **non-termination** (R2d/E-6: 18–50% never close the block even at 16384) — same symptom
(budget-exhausted, no answer), different cause (looping vs. legitimately-long reasoning); the fix differs
(`--reasoning-budget` force-close vs. simply more `max_tokens`).

**Why it matters for production.** Every stack role runs with an effective completion ceiling
(`roles.*.reasoning_budget`, `max_tokens_multiplier`, orchestrator request defaults). If those ceilings sit
**below the knee** for a given model, that model is **silently losing quality on hard tasks** — invisibly,
because a truncated answer looks like a wrong answer in aggregate accuracy. Nobody would see it without the
finished-vs-truncated split.

**The operator's two hypotheses (both testable):**
1. **Per-model/per-task tuning is needed** — the budget knee differs by model (a 3B-active model reasons
   differently than a 122B) and by task difficulty, so quality-maximization requires a matrix.
2. **A single "mostly-ok" generous setting recovers most quality** — there may be one budget (per model, or
   even stack-wide) that captures ≥90% of the model's max-budget accuracy, making per-task tuning unnecessary.
   This is the cheap-win hypothesis and should be tested first.

**Study design (later session):**
- [ ] **TB-1 — Per-model budget curve.** For each stack model, on a truncation-inducing suite
      (`olympiadbench_hard` is ideal — it induces 9–16k-token reasoning), sweep `max_tokens ∈
      {4k, 8k, 16k, 24k, 32k}` on the **same pinned items**, plot **accuracy AND truncation-rate vs budget**,
      and report the **finished-only accuracy** (the budget-independent ceiling) alongside overall. Find the
      **knee** (truncation < ~5%, accuracy plateaus). Use the idempotent `(id,seed)` resume so each higher
      budget only re-runs the items the lower budget truncated.
- [ ] **TB-2 — Test the "single mostly-ok setting" hypothesis.** Does one budget capture ≥90% of each
      model's max-budget accuracy? If yes → a simple per-model (or stack-wide) default; if no → the
      per-task matrix (hypothesis 1). Report quality-per-token, not just quality — budget = tokens = time on
      a shared box ([[feedback_cpu_decode_bw_bound]]).
- [ ] **TB-3 — Audit production ceilings against the knees.** Cross-reference each role's live
      `reasoning_budget`/`max_tokens_multiplier` (`orchestration/model_registry.yaml`) against its measured
      knee. Flag any role running **below** its knee — that is silent quality loss, fixable by raising one number.
- [ ] **TB-4 — Interaction with the effort ladder.** Budget is a **third axis** alongside prompt-effort
      (L0–L3) and native-`<think>`. A tight prompt-effort level *reduces* the budget needed (the model plans
      brevity); the full 2-D (effort × budget) grid per model is the complete picture. Fold into E-2/E-6.

### Production control problem — budget × concurrency × VRAM is a JOINT, dynamic constraint (operator, 2026-07-22)

The study above measures *static* per-model curves. **Production is harder: reasoning budget and server
concurrency are coupled through VRAM, and the coupling is dynamic.** Measured 2026-07-22 while sizing the
batched hard-suite run (MI210, 64 GiB, f16 KV, per-slot ctx 36864 = prompt + 32768 budget):

| model | weights+base | **per-slot KV @36864** | slots to fill 64 GiB |
|---|---:|---:|---:|
| 122B-IQ2 (MoE/GQA) | 38.2 GiB | **0.99 GiB** | ~20 |
| 27B-dense Q8 | 26.9 GiB | **2.39 GiB** | ~13 |
| 35B-A3B (MoE) | 35.7 GiB | **0.76 GiB** | ~30 |

**Key facts for a router:** (1) KV/slot scales **linearly with the reasoning budget** (`n_ctx_slot`), and
(2) it is **strongly per-architecture** — the dense 27B costs 2–3× the KV/slot of the MoE arms, so it can
serve **far fewer** concurrent high-budget requests on the same card. So VRAM = `weights + Σ_slots(budget_i ×
kv_per_token)`. **A naive "raise the budget" or "raise concurrency" in isolation risks OOM**, which in
llama.cpp silently shrinks `n_ctx_slot = n_ctx / n_parallel` → **truncation** (the very failure the budget was
meant to fix). This makes budget-selection and admission-control **one problem**.

**The router design this implies (the operator's framing):**
- [ ] **TB-5 — Expose `max_tokens` / `reasoning_budget` as a per-request tunable surface** the router
      sets from **assessed task complexity** (easy → tight budget, hard → generous). Requires per-request
      budget plumbing through the orchestrator serving path (llama-server already accepts it per request).
      Natural extension of [[project_learned_routing_controller]] — budget becomes a routing *output*.
- [x] **TB-6-exec — np × context throughput surface, ALL GPU architect candidates (GPU-only study).**
      ✅ 2026-07-23 — COMPLETE for **A1** (122B-A10B UD-IQ2_M, MoE, MTP2), **A3** (Qwen3.6-27B dense Q8, MTP4),
      **A4** (Qwen3.6-35B-A3B Q8, MoE, MTP4) — each at its own max-opt MTP depth, v7 kernel, MI210. Grid
      np{1,2,4,8,16,32} × L{2048,8192,16384,32768} (drivers `study_np_context*.sh`, artifacts
      `np_context_study_20260723/`). Aggregate decode t/s (— = grid-capped or VRAM-guard SKIP):

      | np↓/L→ | **A1** 2k | 8k | 16k | 32k | **A3** 2k | 8k | 16k | 32k | **A4** 2k | 8k | 16k | 32k |
      |---|---|---|---|---|---|---|---|---|---|---|---|---|
      | 1  | 54.7 | 52.7 | 57.1 | 52.0 | 46.8 | 47.0 | 41.4 | 42.5 | 72.4 | 94.0 | 99.4 | 73.3 |
      | 2  | 44.0 | 44.2 | 44.8 | 43.0 | 79.1 | 64.3 | 64.0 | 65.2 | 103.2 | 111.5 | 98.3 | 98.9 |
      | 4  | 63.1 | 60.9 | 55.6 | 45.7 | 113.8 | 102.5 | 90.8 | 95.2 | 147.2 | 159.0 | 126.9 | 131.5 |
      | 8  | 85.3 | 66.8 | 62.7 | — | 151.2 | 119.9 | 100.4 | — | 181.1 | 193.8 | 159.5 | — |
      | 16 | 99.9 | 86.2 | — | — | 152.9 | 104.0 | — | — | 220.9 | 207.1 | — | — |
      | 32 | 103.4 | — | — | — | 128.7 | — | — | — | 243.5 | — | — | — |

      **Peak aggregate per (arm, budget) [np@peak]:** L2k → A1 103@32 · A3 153@16 · **A4 243@32**; L8k → A1 86@16 ·
      A3 120@8 · **A4 207@16**; L16k → A1 63@8 · A3 100@8 · **A4 160@8**; L32k → A1 52@**1** · A3 95@4 · **A4 132@4**.

      **KEY FINDINGS (cross-candidate):**
      1. **Throughput ranking A4 ≫ A3 > A1 at every batched operating point** — small-active MoE (3B active)
         batches best, dense 27B second, large-active IQ2 MoE worst. At L2k peak: 243 / 153 / 103.
      2. **A1 is the SOLE outlier.** It is the only arm with (a) an np=2 dip AND (b) a long-context batching
         *collapse* (net-negative at 32k: np4=45.7 < np1=52.0). A3 (dense) and A4 (small MoE) both batch
         **robustly at every budget** (A3 2.2–3.3×; A4 up to 3.4×).
      3. **⚠ CORRECTION of the earlier A1-only reading (was wrong):** the np=2 dip is **NOT** generic-MoE (A4
         MoE shows *no* dip, 1.43× at np=2) and the long-CoT collapse is **NOT** generic-long-context (A4
         batches fine at 32k). BOTH are **A1-SPECIFIC**, confounded across IQ2-quant / MTP-2 / large-active —
         cause not isolated (candidate followup RP/kernel).
      4. **Batching is ARCHITECTURE-DEPENDENT, not universal.** The earlier "optimal np → 1 as budget grows /
         don't batch long-CoT" rule holds **ONLY for A1**. Dense + small-MoE keep ~2–3× batching at 32k.
      5. **Why dense batches so well:** weight-reuse amortization (read weights once, apply to np tokens) beats
         MoE expert-scatter at low–mid np; the MoE edge (fewer active params) only surfaces at high np with
         expert reuse — which is exactly where A4 pulls away (243 @ np32) and A3 plateaus (~153 @ np8-16).
      6. **Caveat:** np=1 cells are n=1 (NREQ=np) → noisy baselines (A4 np=1 ranged 72–99 across L); the
         batched aggregates (n=np) are the reliable reads. Peak numbers, not np=1 ratios, drive the policy.

      **Router rule — per-arm, architecture-aware (supersedes the single-arm rule):**
      - **A1** (large IQ2 MoE): batch ≤8k (np8-16); 16k np4-8; **≥32k np=1**; **never np=2**.
      - **A3** (dense): batch **all** budgets, sweet spot **np=8** (regresses past np=16).
      - **A4** (small MoE): batch aggressively **all** budgets, scales to **np=32+**, no dip — the throughput arm.

      Cross-check: earlier fixed-*total*=36864 probe np4=62 matches A1's L=8192 np4=60.9. ✅
- [ ] **TB-6-exec-v8 candidate extension — grids terminal; prefill-to-depth RAG RUNNING 2026-07-28.** Under the operator's zero-idle,
      observation-grade grant, extend `epyc-inference-research/artifacts/np_context_study_v8_20260727/`
      with one-load-per-model frozen-v8 runs: ThinkingCap Q8 and both Fable-Fusion Q8 variants each
      receive an `rb1024` SWE/LCB first-read plus the canonical `np×L` grid; Laguna UD-IQ2_M receives
      the grid with DFlash off; A4 receives the `L=2k/8k` era-bridge column. After those cells finish,
      run the separate production-template prefill-to-depth instrument using pinned real retrieval
      prompts. The four prerequisite grids are terminal, and the q3-held successor is live first on
      Fable non-MTP; retain this item open until the separate RAG instrument terminalizes. Evidence
      collection does not authorize a lineup or registry change.
- [x] **TB-6-sidecar CPU-containment repair** ✅ 2026-07-27 — an initial GPU-sidecar
      thread-affinity check caught a ROCm helper thread inheriting the broad host mask during a
      concurrent Laguna Q4 CPU arm, correctly invalidating that arm rather than accepting a false
      clean-window claim. `np_context_study_v8_20260727/driver/run_model_block.sh` now places the
      driver before child creation in the dedicated threaded cgroup-v2 `epyc-v8-gpu-sidecar`, with
      `cpuset.cpus=184-191`; every server thread is therefore hard-confined even if it subsequently
      requests a broad affinity. The driver records `sidecar_cpuset.txt` and retains the existing
      per-thread affinity proof. Self-test and the 12-cell aggregation suite passed; the live grid
      remains observation-only and in progress.
- [ ] **TB-6-exec-followups (GPU-owned).** (a) ✅ A3+A4 surfaces DONE 2026-07-23; remaining: the other
      GPU-resident stack models if/when relevant. (b) A *rigorous* variant using **prefill-to-depth** (long
      synthetic prompt + short generation) to measure decode-at-KV-depth cheaply instead of the slow generate-L
      proxy — also fixes the n=1 np=1-baseline noise. The prepared q3 RAG successor started 2026-07-28 and
      remains live evidence collection, not a terminal result. (d) Extract per-model `kv_bytes/token` from the VRAM
      readings for the admission-control constant (A1 ~0.08, A3 ~0.15, A4 low — MoE). NOTE: measured KV is
      *cheaper* than a naive 0.23 GB/1k estimate — that conflated true KV with per-np compute/batch buffers;
      totals to 131k ctx fit under ~54 GB on the 64 GB card.
- [ ] **TB-6-exec (c) — A2/CPU (122B-Q4) np×context surface — HANDED TO CPU LINEAGE 2026-07-23.** Does the
      Q4 arm on CPU show the same batching-collapse shape? Owned by the CPU session per the GPU/CPU split
      ([[project_session_split_2026_07_23]]); tracked here for the surface's completeness only.
- [ ] **TB-6 — Concurrency-aware admission control (VRAM *and BANDWIDTH* guard).** The router/orchestrator
      must track live `Σ(budget_i × kv_per_token_model)` against the card and **admit/queue/downgrade**
      requests so the sum never forces `n_ctx_slot` below a request's budget. Per-model `kv_per_token`
      (measured above) is the key constant; extends the live placement SM in
      [[project_heterogeneous_slot_fabric]] (already "everything is a slot"). Potentially **asynchronous** —
      hold or shed budget under pressure rather than truncate. Non-trivial joint scheduler:
      **complexity-estimate → budget → admission → placement**.
      > **⚠ MEASURED 2026-07-22 — the binding constraint is memory BANDWIDTH, not VRAM capacity; and the
      > optimal concurrency is a function of context (= reasoning budget).** Batching `olympiadbench_hard`
      > (budget 32768 → per-slot ctx 36864) on the 122B-IQ2:
      > - **np=14:** fit VRAM comfortably (52/64 GiB) but **collapsed** — per-request decode fell so far that
      >   **54/155 requests (35%) exceeded a 3600s timeout**. (The "18.2 tok/s aggregate" first reported was
      >   NOT a real throughput — it is real-tokens ÷ a wall-clock inflated by 54 timeout-stalls; discard it.
      >   True np=14 aggregate is unmeasured, but ≈ or below single-stream by the np=4 point below.)
      > - **np=4 (native per-request timing):** median **11.9 tok/s/request → ~47 tok/s aggregate** — only
      >   ~8% over single-stream spec-none (43.6). So at this context **batching barely helps** and sequential
      >   would have been just as fast + reliable.
      > **Why (vs pre-promotion B32 benches that showed 148.7 agg):** those were at *small* context (~512–2k),
      > where KV is tiny and 32 slots pack in. At 36864 ctx the KV read per decode step scales with
      > `(context × active_slots)` and MoE requests scatter across experts → each step reads far more memory →
      > **aggregate throughput DROPS as concurrency rises**. **So there is an `np × context` optimum curve, and
      > the optimal np collapses toward 1 as the reasoning budget (context) grows.** TB-1 must therefore be a
      > **2-D (budget × concurrency) grid** capturing the decode-collapse knee; "fits in VRAM" is NOT
      > sufficient to raise concurrency. Bandwidth ceiling ≈ `Σ(ctx_i) × kv_bytes/token / mem_bw`. Evidence:
      > `artifacts/architect-bench-gpu-20260720/runs/olympiadbench_hard/` (A1 np=14 timeouts vs np=4 timing).
      > **✅ 2026-07-23: the 2-D grid is now MEASURED for all GPU candidates — see TB-6-exec surface above
      > (A1) + the consolidated cross-candidate table (A1/A3/A4). Router-integration plan: TB-6-ROUTER below.**
- [ ] **TB-6-ROUTER — Wire the np×budget surface into the router (GATED on GPU joining the orchestration
      stack).** The surfaces give, per GPU-resident model, a lookup `reasoning_budget → (optimal np, expected
      aggregate t/s, expected per-request t/s)`. This is the missing half of the routing decision: the learned
      router already maps *task → budget* ([[project_learned_routing_controller]]); this maps *budget →
      concurrency policy*. **Precondition (why gated):** the MI210 is today a *bench instrument*, NOT a serving
      node — production is CPU-only. This activates only when the GPU is registered as a serving backend in
      `orchestrator_stack.py` / `model_registry` — an operator-gated stack change
      ([[feedback_stack_change_three_gates]], [[project_orchestrator_stack_freeze]]).
      **Data products to freeze into the registry per GPU model** (the `optimal_gpu_serving` block already
      exists as the home): (1) `kv_bytes_per_token` (admission capacity constant, from VRAM readings);
      (2) `np_ceiling(budget)` — concurrency beyond which aggregate plateaus/declines (A1: np16 @≤8k, np8 @16k,
      **np1 @≥32k**); (3) the full `agg_throughput(np,budget)` + `per_req_throughput(np,budget)` surface for SLA
      estimation; (4) **forbidden operating points** — np=2 for MoE arms (universal dip). **Integration, three
      layers:** (a) *Static server sizing* — size each model's launch `-np` to its expected budget distribution
      (AutoPilot TB-7 realized-demand): short-budget roles → high np; deep-reasoning architect → np1-2; never
      launch a MoE arm at np=2. (b) *Complexity→budget→concurrency co-decision* — extend the learned controller
      to emit a coupled concurrency ceiling alongside the budget; do not admit a request into a slot pool that
      would exceed `np_ceiling(budget)`. (c) *Live admission/placement* — the TB-6 controller tracks
      `Σ(budget_i × kv_bytes/token)` against BOTH the VRAM cap AND the bandwidth-collapse ceiling; near the
      ceiling it admits/queues/downgrades (shed budget or route to CPU) rather than pack another slot into the
      collapse region. Integrates with [[project_heterogeneous_slot_fabric]] ("everything is a slot") + the
      within-role-placement SM. **Cross-model dimension:** the consolidated table also picks *which* GPU arm
      serves a given (budget,load) point — a small-active MoE (A4) may sustain higher aggregate at moderate np
      than a dense model (A3) whose higher KV/slot forces an earlier collapse. **Validate before activation:**
      re-measure under the *production* serving config (real RAG-context prompts, not the short-prompt proxy —
      long prompts shift the collapse leftward) via the prefill-to-depth variant, reconciled with AutoPilot's
      realized budget distribution.
- [x] **TB-7 — Calibrate the budget policy from AutoPilot's live token stats (no new inference).** AutoPilot ✅ 2026-07-22
      already records **tokens-generated per successfully-completed task**. That is a free, production-grounded
      distribution of "how much budget did each task class actually need" — mine it to set per-(task-class,
      model) budget defaults and to find the knee *without* running the TB-1 sweep for every task type.
      Cross-check the TB-1 curves (capability ceiling) against the AutoPilot distribution (realized demand):
      the deployable budget is roughly the high percentile of realized demand for the task class, capped by
      the VRAM/concurrency budget (TB-6). **Do this first** — it may answer TB-2's "single mostly-ok setting"
      from existing data before any GPU sweep.

**Coverage target (TB-1):** every production model — frontdoor (35B-A3B), worker (gemma-4-26B-A4B), architect
(122B), ingest (Qwen3-Next-80B), reviewer arm, coder. Cheapest first; frontdoor + architect gate any
production budget change (operator-gated).

**Per-model INVARIANT applies** (see above): the budget knee is a `(model, quant)` property, certified per
model, never inherited. **Tooling ready:** `olympiadbench_hard` suite + `math_symbolic` scorer +
finished-vs-truncated split (`truncated`/`finish_reason` fields in per-question JSONL) + idempotent budget
top-ups + **`--concurrency` batched runner + a VRAM-sizing probe** (per-slot KV table above) — all landed
this session. The batched run gives the TB-1 sweeps ~10× wall-clock, and the per-slot-KV constants are the
inputs TB-6's admission-control needs. **Method note:** each `-np` slot must get the FULL per-request budget
as its `n_ctx_slot` (`-c = per_slot_ctx × n_parallel`) — else llama.cpp silently truncates; verify
`n_ctx_slot ≥ budget` and VRAM headroom at launch (the batched run does).

## § MODEL-specific repetition-penalty fence (operator, 2026-07-23; attribution CORRECTED)

**Finding (olympiadbench_hard, 2026-07-23):** the **Qwen3.5-122B-A10B** loops on `\boxed{answer}` to the
token cap (degenerate repetition — solves it, can't stop) — **at BOTH quants: UD-IQ2_M (25% of items) AND
UD-Q4_K_M** (A2/CPU, item-1 = 32768 tok, tail-uniqueness 0.03, `\boxed{2n-1}`×N on the *same* item IQ2
looped on). The Q8 arms do NOT loop (27B-dense **0%**, 35B-A3B **~1%**). **⇒ the defect tracks the MODEL
(122B-A10B), NOT quantization** — the 2-bit-EOS-damage hypothesis is REFUTED (RP-2). It is likely a
model×prompt property (the `\boxed{}` instruction may be a trigger — RP-3).

**Policy (operator, corrected): apply the repetition penalty to the MODELS that need it (the 122B-A10B, at
any quant), NOT keyed on quant aggressiveness, and NOT blanket across the stack.** Rationale: the penalty
has a real quality cost (registry's own Qwen note: `presence_penalty > 1.0` causes language mixing;
repetition penalties hurt legitimate repetition in code/math/structured output — confirmed by RP-1:
`repeat 1.3` tanked accuracy to ~15%). Production already uses penalties per-model (worker `repeat_penalty
1.05`, gemma4 `1.1` crash-mitigation, some frontdoor `presence_penalty 1.5`) — **but the 122B-A10B architect
has NONE at either quant**, and our bench matched that, so the loop would occur in production. The fence is a
**per-MODEL** property (certified per model), never inherited stack-wide.

- [x] **RP-1 — Repetition-penalty probe ✅ 2026-07-23:** `repeat_penalty 1.1` is the fix (loop 100%→22%, tokens 32768→10.6k, acc held 55%); `1.3` over-penalizes (~15%); DRY(0.8) ruled out (inconsistent + 0/40). On A1's 40 looping items, test
      `repeat-penalty {1.1, 1.3}` and the **DRY sampler** vs baseline — does it break the loop
      (truncation→0, tokens↓) WITHOUT hurting accuracy? Pick the least-cost fence. Driver `probe_reppen.sh`.
- [x] **RP-2 — Quant attribution: REFUTED ✅ 2026-07-23.** A2 (122B-A10B **Q4**, CPU) loops **identically**
      to IQ2 on the same item → the loop is **MODEL-specific (122B-A10B), NOT quant-specific**. So it is
      NOT 2-bit EOS damage, and the ~2× token cost is inherent to the 122B-A10B candidate at either quant
      (does not distinguish IQ2 vs Q4). *(A2 was run unfenced only to answer this — a clean H1 accuracy
      read needs the fence on BOTH A1 and A2; see RP-5.)*
- [ ] **RP-3 — Does it loop on the ARCHITECT WORKLOAD** (multi-step planning) or only on competition-math
      `\boxed{}` prompts? The `\boxed{}` instruction may itself be the trigger — **now the leading hypothesis
      for the root cause** (both quants loop; models differ). Test on real architect tasks + a no-`\boxed`
      prompt variant.
- [ ] **RP-4 — MODEL-specific penalty policy in the registry:** add a per-**model** repetition-penalty
      default for the 122B-A10B (both quants) — RP-1 says **mild `repeat_penalty ~1.1`** (breaks the loop,
      accuracy held ~55%; `1.3` over-penalizes to ~15%). Operator-gated. Do NOT key on quant; do NOT blanket.
- [ ] **RP-5 — Clean H1 (Q4 vs IQ2 reasoning parity) WITH the fence.** Both quants loop unfenced, so the
      H1 accuracy comparison must run A1(IQ2) and A2(Q4) both at `repeat_penalty 1.1` on the same hard items.
      CPU-window-gated (A2 is CPU). This is the remaining architect-bench accuracy unknown.

## Prioritized task list
- [x] **E-1 — Design the ladder.** Draft 4–5 effort levels, e.g. L0 answer-only → L1 one-line ✅ 2026-07-22
      justification → L2 brief step-by-step (bounded) → L3 full CoT → (L4 native `<think>` on).
      Levels must be *prompt* variants; note which also set a budget backstop.
- [ ] **E-2 — Measure the curve, once per model.** Sweep the levels on the **already-pinned**
      GPQA-Diamond items (`artifacts/architect-bench-gpu-20260720/questions_gpqa_diamond_cot.json`) so
      results are paired with everything measured today. Plot accuracy vs mean tokens → **one Pareto
      frontier per (model, quant)** — see the per-model INVARIANT above. Report truncation +
      parse-failure + empty-content rate at every level (a level that truncates or fails to terminate is
      **disqualified, not scored** — scoring it as "wrong" is the artifact that has already bitten twice).
      **Coverage target: every model in the production stack**, not just the architect-bench arms —
      gemma-4-26B-A4B (worker), Qwen3-Next-80B (ingest), the reviewer arm, and any drafter used
      standalone. Cheapest first; the frontdoor + architect curves are the two that gate E-4.
- [ ] **E-3 — Evaluate by rescue-rate, not mean accuracy.** Per
      [[feedback_accuracy_token_tradeoff_rescue_metric]]: score an effort level by how often it *rescues*
      tasks the cheaper level got wrong, versus its token cost. Mean accuracy hides that a level may only
      help on a narrow band of hard items.
- [ ] **E-4 — Per-role defaults, expressed as (model × level) pairs.** Map levels → roles *given the
      model currently bound to each role*; a bare "frontdoor = L2" is malformed (see INVARIANT).
      Operator's stated prior: **architect + reviewer should reason; frontdoor arguably too.** Frontdoor
      is the hard case — interactive, and it pays the token cost most, so it wants the **knee** of its own
      curve, not the top. Note the architect and reviewer currently share one model (122B-A10B-IQ2), so
      they share one curve but may sit at different points on it.
- [x] **E-7 — Re-calibration trigger.** ✅ 2026-07-29. Make the invariant enforceable, not aspirational: a model swap,
      quant change, or kernel promotion **invalidates** that model's certified levels. Record each curve
      with its `(model, quant, kernel/era)` stamp and add a validator that flags a role whose bound model
      no longer matches the model its effort level was certified against. Same failure mode the registry
      already had — a role launching an artifact that had no model-indexed row of its own.
- [ ] **E-5 — Dynamic selection (stretch).** Let the router pick effort from task difficulty rather than
      pinning it per role — a natural extension of [[project_learned_routing_controller]]. Needs a
      difficulty signal that is cheaper than just running the hard path.
- [x] **E-6 — Interaction with the `<think>` axis.** ✅ 2026-07-21. Effort (prompt) and `enable_thinking`
      (native channel) are **independent axes**; measured the grid. R2b/R2d established unlimited native
      `<think>` LOSES for both models via a **non-termination tail** (18% A1 / 50% A4). **Budget-cap result
      (`--reasoning-budget N --reasoning-budget-message`):** force-closing `<think>` drove non-termination
      to **0%** and recovered accuracy to ≈ think-off for both models at both budgets, at ~1.6–3× tokens
      (vs 6× unlimited) — **no capped arm is statistically distinguishable from think-off (all p ≥ 0.62),
      and none beats it.** Higher budget (6144) was consistently ≤ lower (2048). **Conclusion: the native
      channel can be made *safe* with a budget cap, but the accuracy lever is the PROMPT (axis 1, +32pp),
      not native `<think>`.** Full table in `architect-model-selection-bench.md` §R2d + §E-6; driver
      `run_budget.sh`, analysis `e6_budget_analyze.py`; data `artifacts/architect-bench-gpu-20260720/e6_reasoning_budget/`.
- [ ] **E-6b — retest budget-cap on a NON-saturated suite.** E-6 ran on `gpqa_diamond_cot` (~85–90%
      ceiling), where "capped thinking ties think-off" may be a ceiling effect. Re-run the budget sweep on
      `olympiadbench_numeric` (harder) to see whether native thinking, once it terminates, *ever* beats the
      prompt-CoT baseline. Cheap: reuse `run_budget.sh` with the olympiad suite.

## Dependency graph
`R2a (done)` → `E-1 design` → `E-2 curve (per model, fan-out)` → `E-3 rescue-rate` → `E-4 role defaults` → `E-5 dynamic`.
`E-2` fans out per model and is the long pole; `E-4` cannot start until the frontdoor + architect curves exist.
`E-6` depends on **R2b** (thinking ON/OFF ablation, architect bench). `E-7` gates any deploy of `E-4`.
`E-4` is operator-gated (production config).

## Cross-cutting concerns
- **This is a production-config change surface**, hence operator-gated. Nothing here edits the stack.
- Token cost is a **throughput** cost on a shared box: 4× output tokens on the frontdoor is a real
  capacity hit, not just per-request latency. Weigh against `feedback_cpu_decode_bw_bound`.
- Prompt-effort levels interact with **agent-file compression operating points** (roles already carry an
  `agent_file_compression_operating_point`) — both change the prompt; don't tune them blind to each other.
- Whatever ladder is chosen must be expressible per-role in the registry, and **indexed by model/quant,
  not role**, for the measurement rows ([[feedback_model_not_role_indexing]]).

## Reporting instructions
Record per level × model: accuracy, mean/median/p90 tokens, truncation rate, parse-failure rate, and
rescue-rate vs the next-cheaper level. Flip the checkboxes here; a per-role default change is a proposal
to the operator, not an edit.

## Key file locations
- Pinned item sets + all R1/R2 evidence: `epyc-inference-research/artifacts/architect-bench-gpu-20260720/`
- Runner (already supports `--limit`, `--repeats`, per-question JSONL, truncation capture):
  `epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py`
- Analysis: `architect_bench_analyze.py`, `thinking_ablation_analyze.py`, `architect_bench_rescore.py`
- Prompt text currently lives in the adapters: `epyc-inference-research/scripts/benchmark/dataset_adapters.py`
  (`gpqa_diamond` = letter-only, `gpqa_diamond_cot` = full CoT — these are already L0 and L3).

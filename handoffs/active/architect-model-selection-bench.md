# Architect Model Comparison Benchmark

**Status (2026-07-28): sealed comparable authority is A3 `23/40` (`57.5%`), ThinkingCap no-think `21/40` (`52.5%`), A3-ff `19/40` (`47.5%`), Laguna `17/40` (`42.5%`), A1 `15/40` (`37.5%`), and A4 `13/40` (`32.5%`).** FG-3's clean no-think ThinkingCap validation is terminal at SWE `21/40` and LCB `24/53`; it replaces the legacy thinking-enabled `18/40` row for comparison. That legacy row remains diagnostic only because `--enable-thinking` produced `15/16` reasoning-channel cap truncations. FG-2V recovered only one new Laguna LCB solve (`14/53 -> 15/53` projected), so the coder-role case remains closed. ThinkingCap's license gate is operator-WAIVED; Fable remains framed as a scaffold/pre-processing candidate, not a direct role substitute. No lineup action is authorized. Historical six-arm artifact: `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/expanded-six-arm-v4-report-path-correction-20260727/path_correction_successor.json` (SHA-256 `e12dcda1223a77f7864b33c93dd009295d25d0b24527af4891f1f121fb4f748d`) is retained as the evidence that exposed the config confound, not current comparative authority.

_(prior)_ **Status (2026-07-24): quality NULL CONFIRMED at higher power + a SCORER ARTIFACT corrected + throughput surface added. Keep/drop = quality-tied, A4 throughput-best, tool-use eval outstanding.**

> **⚠ 2026-07-24 — R7: canonical re-score fixes a scorer artifact; the pooled quality read is NULL, and A4 was never actually weaker.**
> While answering "should A3(27B-dense) and A1(122B) be dropped vs A4?", pooling the banked per-question data (n=533)
> at first showed A1/A3 *significantly* > A4 — **but that was a scoring artifact**: `gpqa_diamond` was scored with a
> stale extractor that dropped bare-letter answers, and A4 (verbose) leaked **15%** of items to false parse-failures
> vs A1's **0%** — a systematic bias against models that show their work. Re-scored uniformly with the canonical
> `extract_letter_answer` (via `architect_bench_rescore.py`; A4 gpqa **43.4→53.0%**), the pooled n=533 read is:
> **A1 69.8 / A3 69.6 / A4 67.4 — every pairwise p ≥ 0.23 (NULL); A1≈A3 (Δ0.2pp).** So on measured quality A1 and A3
> **do NOT outcompete A4**; A4's earlier "deficit" was the artifact. **Keep/drop lean: quality-tied → A4 suffices; A1/A3
> not justified on quality grounds.** Regression test locked (research `274fe0c1`). Autopilot NOT affected (its eval-tower
> grader is LLM-judge-based, not regex-MC). CIs still admit ≤~6-9pp A3>A4 on hard reasoning (more discriminating items
> would close it) — and this is all math/science-QA, **not** the architect's real job. **The decisive gate now = Phase-2
> tool-use/coding** (harness does NOT exist yet — LiveCodeBench needs `datasets`+exec-sandbox; agentic SWE-bench needs a build).
> **Throughput surface** (TB-6, [[reasoning-effort-levels]]): A4 ≫ A3 > A1 at every batched point → on GPU A4 is quality-tied AND fastest.

**Status (2026-07-23): GPU BENCH COMPLETE — reasoning suites are a WELL-POWERED NULL across the board (incl. the non-saturated olympiad-hard, R6). No reasoning-accuracy basis for the architect choice → deployment robustness decides. RP-1 DONE (fence=repeat_penalty 1.1); A2/CPU confirmed the loop is MODEL-specific not IQ2 (quant-attribution REFUTED). Outstanding: RP-5 fenced-H1 (Q4-vs-IQ2 accuracy, both need the fence, CPU-gated), RP-3 (`boxed-prompt trigger?), Phase-2 tool-use.**
_(prior status)_ **2026-07-21: GPU ARMS RUN — reasoning suites show NEAR-PARITY; harder-tier + CPU arm outstanding.**
Operator granted a GPU-only inference window (2026-07-20/21). Executed: per-model spec-dec sweep (→ registry
optima), R1 letter-GPQA (n=198×3), R3 AIME'25 avg@4 (n=30×4×3), R2a–d thinking ablation + E-6 budget-cap.
**Result so far: no arm is statistically separable on any reasoning suite** — H3 fails (35B-A3B ties both
larger arms), H2 near-parity (27B-dense ≈ 122B-IQ2); `enable_thinking=false` vindicated; the +32pp reasoning
lever is the *prompt*, not native `<think>`. **Outstanding:** OlympiadBench-numeric n=150 (RUNNING — the
harder-tier discriminator, since GPQA/AIME saturate) → full `gpqa_diamond_cot` n=198 → **A2 122B-Q4 CPU arm**
(later session; blocks **H1**, the IQ2-vs-Q4 question) → Phase 2 (OD-1/OD-2). **Reusable procedure:**
[`../../docs/reference/architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md).

**One-line purpose:** decide, decision-grade, **which model holds the `architect` role** (deep
reasoning / multi-step planning) — because the only local quality signal we have for the GPU-resident
candidate (AXA-1's Δ0.0pp IQ2≈Q4 parity) is **statistically powerless on reasoning** (n≈4/hard-suite),
and every published benchmark of the exact models is unreliable.

**Rationale + full evidence:** [`../../docs/reference/architect-model-selection-2026-07-20.md`](../../docs/reference/architect-model-selection-2026-07-20.md)
(two theses w/ cited numbers, the AXA-1 gap analysis, the decision tree). **Read it first.**

**Reusable procedure:** [`../../docs/reference/architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md)
— the polished SOP for benching *any future* architect candidate (gates, arms, per-model config discovery,
the suite ladder, the two reasoning axes, scoring discipline, statistics/stopping rules, decision framework,
tooling, artifact layout, gotchas, end-to-end checklist). Distilled from this run.

## Open decisions (operator to confirm)
- **[ ] OD-1 — Phase-2 planning-task design.** Phase 1 (AIME'25 + GPQA-Diamond + MMLU-Pro control) is
  the **decisive reasoning core and can proceed as specified** — it settles the reasoning-depth question
  (H1/H2/H3) on its own. **Phase 2 (tool-using multi-step planning) is NOT hard-committed:** the
  recommended default is **SWE-bench-Verified in agentic mode, scored by its FAIL_TO_PASS test oracle**
  (objective, no model-judge), but the alternative is bespoke tasks mined from real architect
  orchestration logs (only viable if an objective success criterion exists). **Confirm the Phase-2
  design before building its scorer.** Rationale for keeping it open: model-as-judge scoring is
  near-random (reviewer control-plane finding), so Phase 2 must have an objective oracle or be dropped.
- **[ ] OD-2 — whether Phase 2 runs at all.** If Phase 1 is unambiguous, Phase 2 may be unnecessary;
  the operator decides whether the tool-use validation layer is worth the extra inference budget.

## Why this bench exists (the gap, in one paragraph)
The architect wants **large-total + moderate-active** (active⇒reasoning, total⇒knowledge —
2505.09388 / 2508.18672), which makes the **122B-A10B** the literature default. Its GPU-resident IQ2
form (AXA-1: 43.7 t/s single / 148.7 agg@B32, 2.2×/~8–9× over the ~20 t/s CPU-Q4 incumbent) passed a
**212-question paired eval Δ0.0pp** — but that pool was **instruction-following (84) + factual QA (72)
dominated with only ~4 questions each from gpqa/math/usaco/livecodebench** (~11% hard reasoning), and
the LLM-rubric gate was deferred. The literature (2505.02390, **our exact GGUF+Unsloth toolchain on a
DeepSeek-class MoE**) says 2-bit leaves **knowledge ~99% intact while halving reasoning** (uniform Q2:
V3 AIME 38→15) — *but dynamic UD holds*. So the IQ2 architect is **not reasoning-certified**, and the
answer is genuinely unknown. This bench measures it at full power.

## Hypotheses
- **H1 (primary, open):** IQ2 preserves the 122B's *reasoning* (A1 ≈ A2 on AIME/GPQA, not just on
  knowledge). Dynamic-UD + a large model *may* hold, contra the small-model quant literature — or not.
- **H2 (challenger):** dense-27B-Q8's max active width out-reasons the 122B on *hard* tasks (near-parity
  in the literature — genuinely open on our workload).
- **H3 (baseline/control):** 35B-A3B (3B active) trails both → confirms frontdoor ≠ architect.

## Arms

| Arm | Model / quant | Device | GGUF (on disk ✅) | Isolates |
|---|---|---|---|---|
| **A1** | Qwen3.5-122B-A10B **UD-IQ2_M** | MI210 | `…/Qwen3.5-122B-A10B-MTP-GGUF/UD-IQ2_M/…UD-IQ2_M.gguf` | vs A2 → **IQ2 reasoning penalty** (H1) |
| **A2** | Qwen3.5-122B-A10B **UD-Q4_K_M** (incumbent) | CPU | `…122B-A10B-UD-Q4_K_M-00001-of-00003.gguf` | quant-control + vs A3 → arch/depth |
| **A3** | Qwen3.6-27B **dense** Q8 | MI210 | `Qwen_Qwen3.6-27B-Q8_0.gguf` | vs A2 → active-width/depth (H2) |
| **A4** | Qwen3.6-35B-A3B Q8 | MI210/CPU | `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` | shallow-reasoner baseline (H3) |
| **A5** *(conditional)* | 122B-A10B **dynamic 3-bit** (Q3_K_M / DQ3-style) | MI210 | *build if triggered* | **graceful-degradation fallback** — run ONLY if A1 shows IQ2 tanks reasoning but Q4 won't fit the GPU (2505.02390: DQ3 ≈ Q4) |

Model roots: `/mnt/raid0/llm/models/`. (27B/35B also have `-MTP-` and EAGLE3 variants — use the plain
Q8 for the quality bench unless throughput is being measured, then use the production MTP variant.)

## Evals — objective-scored ONLY (no model-as-judge; the reviewer work proved that's near-random)
- **Phase 1 (decisive on reasoning depth):**
  - **AIME'25** (objective numeric answers) — use the new `aime25` adapter landed in research `51868f72`.
  - **GPQA-Diamond** (objective MC) — use the new `gpqa_diamond` adapter landed in research `51868f72`; the older `gpqa` adapter is GPQA main, not Diamond.
  - **MMLU-Pro knowledge control** — **reuse** the `mmlu_pro` adapter. *The control is the point:* it
    should show IQ2 ≈ Q4 on knowledge **while** AIME/GPQA reveal any reasoning gap — the asymmetry the
    Δ0.0pp pool was too knowledge-heavy to expose.
  - **OlympiadBench (harder-tier discriminator, added 2026-07-20)** — new `olympiadbench_numeric` suite:
    OlympiadBench filtered to single-answer `Numerical` items whose gold **parses to a clean number**
    (492 of 674), scored by a new **`math_numeric`** path (brace-balanced `\boxed{}` extraction + numeric
    equivalence via `parse_math_number`: handles `\frac`, `\sqrt`, `%`, products; **97% gold-parse,
    60/60 self-consistency**). Rationale: OlympiadBench's native `substring`/LaTeX scoring is brittle and
    would reintroduce the per-arm parse bias fixed in R1. No per-item difficulty field exists (dataset
    `difficulty` is constant), so the suite as a whole is the harder tier; items are seed-shuffled, paired.
    **This is the ceiling-breaker AIME'25 can't be** (AIME saturates for these arms; see R2c/R3). Running
    n=150 paired, CoT, thinking-off, per-model optimum spec-dec.
- **Phase 2 (tool-using multi-step planning) — DESIGN TBD (operator to confirm; deferred "other point"):**
  recommended default = **SWE-bench-Verified in agentic/tool-using mode**, scored by its **FAIL_TO_PASS
  test oracle** (objective pass/fail — "does it plan+execute with tools" without a judge).
  Dataset on disk: `/mnt/raid0/llm/datasets/swe-bench-verified/`. Alternative (bespoke tasks mined from
  real architect orchestration logs) only if an objective success criterion exists. **Phase 1 alone is
  decisive on the reasoning-depth question**; Phase 2 is the tool-use validation layer.

## Protocol (MEASUREMENT.md)
- **Seed-pinned, production sampling** (temp+seed42 per `feedback_production_sampling_seed_not_temp0` —
  these are sampling-sensitive reasoning suites). No-think vs think per suite convention; `enable_thinking`
  via `/v1/chat/completions` for the Qwen3.x arms (`feedback_enable_thinking_requires_chat_completions_path`).
- **Quality (accuracy) is the PRIMARY output and is device-independent** → decision-grade via the
  eval-tower scorer. **Throughput is secondary**; GPU-row t/s stays **observation-grade until `P-GPU-1`
  certifies on `production-consolidated-v7`** (post-promotion). Era-stamp every result.
- **Same questions across arms** (paired, like the AXA-1 parity) so per-arm deltas are McNemar-testable.
- **Difficulty-descending sequential evaluation (adopted 2026-07-20, operator).** For any suite with a
  difficulty ranking, run items **hardest→easiest** with all arms **interleaved per question**, maintaining
  a running paired test, and stop early on either of two rules:
  1. **Saturation stop (always valid):** once the current difficulty tier is answered near-ceiling by all
     arms, remaining easier items carry ≈0 discriminating information — stop; skipping them loses ~nothing.
  2. **Decision stop (requires sequential error control):** cross an **always-valid / e-process** boundary
     (reuse the reviewer control-plane FR≫FA e-process infra) for either **separation** or **futility**.
     Do NOT use a fixed-α McNemar as a peeking rule — that is p-hacking.
  **Rank by an a-priori, model-independent difficulty key ONLY** (AIME problem number; OlympiadBench's own
  difficulty field). **Never order by our own arms' solve rates** — that is circular selection and
  manufactures significance. Validated on AIME'25: solve-rate is cleanly monotonic in problem number
  (tiers 1–5 / 6–10 / 11–15 → 92% / 76% / 50% combined), and the hard tier already shows A1=A3=50%, so a
  sequential run would have concluded "no separation within AIME'25" after ~10 items instead of 30.
  This is an **ordering/stopping efficiency**, not a power fix — separation still needs harder *items*.

## Decision tree (exit criteria)
1. **A1 ≈ A2 on AIME/GPQA** → 122B-A10B stays architect, **GPU-resident at IQ2** (AXA-1 win reasoning-certified).
2. **A1 ≪ A2, A2 strong** → IQ2 out; run **A5** — DQ3 ≈ Q4 & GPU-fits → 122B-DQ3 GPU architect; else architect = **Q4-122B on CPU**, GPU slot → Qwable/vision/drafter.
3. **A3 out-reasons the 122B arms on hard tasks + GPU-cheap** → reconsider **27B-dense as GPU architect** (weigh lost knowledge headroom vs tool access).
4. **A4 trails** (expected) → 35B-A3B not an architect; frontdoor unchanged.

> **Deployment-robustness input (operator, 2026-07-20) — the choice isn't purely the quality number.**
> A **GPU-only** architect (27B-dense, ~4.4 t/s on CPU → no viable self-home) carries a real operating
> cost the dual-resident 122B does not: it has **no self-fallback** (needs a *substitute* architect —
> 122B-Q4 / 35B — for drains/GPU-failure) and is effectively **pinned**, monopolizing the single GPU
> slot. So a **dual-resident 122B is cheaper to operate at equal quality.** If branch 3 fires (A3 wins
> on reasoning), weigh this cost before deploying — **assess after the bench**, not before. See the
> "GPU accelerates, CPU guarantees" fallback design in [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md).

## Gating (sequenced — do NOT start inference until ALL clear)
1. **[x] v7 promoted to production** (`production-consolidated-v7`) → GPU arms are now `P-GPU-1`-eligible. Tracked in [`v7-promotion.md`](v7-promotion.md). ✅ 2026-07-20
2. **[ ] `inference-batch-loop.md` outstanding tests complete** — the parallel agent runs that backlog first, on the current orchestration stack. See [`inference-batch-loop.md`](inference-batch-loop.md).
3. **[x] Operator inference approval — GPU ONLY** ✅ 2026-07-20. Operator granted the GPU arms explicitly ("GPU-only benchmark tasks … DO NOT interfere with any CPU inference resources"), **overriding gate 2 for the GPU arms only**. Gate 2 remains binding for anything touching CPU.

> **GPU/CPU split (operator, 2026-07-20).** The CPU arm **A2 (122B-A10B UD-Q4_K_M)** is explicitly deferred to a **subsequent session**; this session runs GPU arms only and must not touch CPU inference. Consequence: **H1 (the primary hypothesis — does IQ2 preserve the 122B's reasoning?) cannot be answered yet**, because it is the A1-vs-A2 contrast. What the GPU-only pass *can* settle is **H2** (27B-dense vs 122B-IQ2) and **H3** (35B-A3B trails), plus each GPU arm's absolute reasoning level.
> **The A2 session MUST replay the pinned item sets** at `artifacts/architect-bench-gpu-20260720/questions_<suite>.json` via `--questions-in`, or the pairing (and any McNemar test) is void.

## Prioritized task list
### Prep (no inference — can proceed now)
- [x] Handoff spec authored ✅ 2026-07-20
- [x] Evidence/decision-tree note authored (`docs/reference/architect-model-selection-2026-07-20.md`) ✅ 2026-07-20
- [x] All 4 base-arm GGUFs confirmed on disk ✅ 2026-07-20
- [x] **Build the AIME'25 adapter** (`aime25`, 2025-only/30 Q) and register it in `ADAPTER_SUITES` ✅ 2026-07-20
- [x] **Build a real GPQA-*Diamond* adapter** (`gpqa_diamond`, 198 Q) ✅ 2026-07-20 — *the pre-existing `gpqa` suite is GPQA **main (448)**, not Diamond; the spec called for Diamond*
- [x] Build `gpqa_diamond_cot` (CoT-permitting variant) ✅ 2026-07-20 — *see "reasoning budget" note below*
- [x] Harden the runner: per-question JSONL, pinned item sets, production sampling, `enable_thinking`, repeats, truncation capture ✅ 2026-07-20
- [x] Fixture-test adapters + scorer offline (25 assertions, 0 failures) ✅ 2026-07-20
- [ ] Confirm MMLU-Pro control re-runs under the hardened protocol (sidecar's n=50 run predates it).
- [x] **Canonical judge-suite head-to-head, 27B vs frontdoor** ✅ 2026-08-02 — paired, one judge,
      matched 8192 budget, identical 70 questions: **180/204 (88.2%) vs 179/204 (87.7%)**, 9 wins /
      4 losses / 55 ties, exact sign test **p = 0.267**. Consistent with this handoff's standing NULL.
- [x] **Established WHY the suite reads NULL** ✅ 2026-08-02 — **50 of 68 questions (74%) score a
      perfect 3 for both arms**; `general` is 100% saturated. It is a ceiling artifact, not model
      equivalence: published benchmarks separate the same pair on **8 of 8** axes.
- [ ] **Retire or harden the saturated suites.** `general` (100% both-perfect), `thinking` (90%),
      `math` (89%) carry no discriminating information at this model tier and should not be used for
      any keep/drop read.
- [ ] **Strip per-question calibration examples from `rubric_system_prompt`.** It names specific
      `question_id`s with the score they got on other models (`math/t3_q2_combinatorics` as a
      score-1 exemplar, `coder/t1_q1_algorithm` as score-0), priming the judge on identity before it
      reads the answer. Affects absolute level; harmless for A-vs-B since both arms get it.
- [x] **Fixed two false suite questions (suites → v2)** ✅ 2026-08-02 — `math/t3_q2_combinatorics`
      asserted an identity whose LHS is identically 1 (the 27B proved it and was penalised);
      `coder/t1_q1_algorithm` claimed two bugs in code with one. Both answer keys documented the
      defect and shipped anyway. Scores recorded before this fix are against suite v1.
  - **Audit 2026-07-29:** still unrun. The only matching sidecar directory is `architect-bench-sidecar-20260720/phase1_gpu_override/main_a3_qwen36_27b_q8_mmlu_pro_20260720T174115Z/`; its server log fails before inference with `--device ROCm0` invalid, and it contains neither runner output nor per-question results. The hardened campaign has no `questions_mmlu_pro.json` manifest or MMLU-Pro run directory. A replacement is fresh GPU inference, not deterministic replay; retain the checkbox and request an owned GPU window plus the hardened runner/pinned-manifest recipe.
- [ ] (Phase 2, if approved) build/validate the SWE-bench-Verified agentic scorer → FAIL_TO_PASS pass/fail.

#### Prep findings that change the protocol (2026-07-20)
1. **`gpqa` ≠ GPQA-Diamond.** The registered `gpqa` adapter loads `ankner/gpqa` = 448-row GPQA **main**. Diamond membership was recovered from the local `hendrydong/gpqa_diamond` mirror; all **198/198** matched into the main set by normalized question text, so `gpqa_diamond` keeps real MC distractors while being verifiably the Diamond subset.
2. **AIME data defect.** `opencompass/AIME2025` ships `2025-II-5` as `336^\circ`. Left uncleaned it is unmatchable by an integer-emitting model — a silent 0 for *every* arm. `aime25` normalizes answers to the integer at load.
3. **Reasoning budget is a confound on letter-only MC.** Under the stock "Answer with the letter only" prompt at `enable_thinking=false`, A1 emits **2 tokens** (no CoT at all) while A3 spontaneously writes **~168 tokens mean (max 1442)**. The arms therefore get *unequal* reasoning budgets, and a letter-only score cannot speak to reasoning depth. `gpqa_diamond_cot` equalizes this and is the **primary** reasoning measure; letter-only is retained as a secondary no-CoT/prior probe.
4. **`enable_thinking=false` is mandatory** for these Qwen arms (degenerate `<think>` loops otherwise), and `--reasoning off` at the server — corroborated by the registry's own `reasoning_policy_observation` (`--reasoning auto` → 0/4 produced final content).

### Gated inference (after all three gates)
- [ ] **Phase 1** — A1–A4 × {AIME'25, GPQA-Diamond, MMLU-Pro control}, paired, seed-pinned, MEASUREMENT-stamped.
  - [x] **GPU arms A1/A3/A4 × `gpqa_diamond` (letter-only, no-CoT secondary probe)** ✅ 2026-07-20 — **all three arms statistically indistinguishable** (R1)
  - [x] **GPU arms A1/A3/A4 × `aime25` avg@4** (n=30 × 4, seeds 42–45) ✅ 2026-07-21 — **near-parity, no arm separable** (R3): A1 71.7 / A3 74.2 / A4 70.8; all pairwise p ≥ 0.50; **H3 fails, H2 near-parity**
  - [x] **Per-model GPU spec-dec optima swept + recorded to registry** ✅ 2026-07-20 (`optimal_gpu_serving`: A1 mtp-2, A3/A4 mtp-4)
  - [x] **Thinking-mode ablation (R2a–d)** — CoT-prompt +32pp; native `<think>` ON hurts both (termination defect); `enable_thinking=false` vindicated ✅ 2026-07-21
  - [x] **Reusable bench runbook authored** (`docs/reference/architect-bench-runbook.md`) ✅ 2026-07-21
  - [x] **Build OlympiadBench harder-tier discriminator** (`olympiadbench_numeric` + `math_numeric` scorer, 492 items, 97% gold-parse) ✅ 2026-07-21
  - [x] GPU arms A1/A3/A4 × **`olympiadbench_numeric`** (n=150 paired) ✅ 2026-07-22 — **⚠ SATURATES (A1 89.3/A3 88.0/A4 89.3, all p≥0.77), NOT the harder tier intended** (adapter filter flaw; see R4). Highest-powered null of the bench.
  - [x] **Build a genuinely-harder discriminator** (derived R4) ✅ 2026-07-22 — `olympiadbench_hard` suite (155 Expression/Tuple/set items, the complement of the numeric suite) + **`math_symbolic` sympy-backed scorer** (validated 155/155 self-match, 0 perturbation-FP, 0 LaTeX-variant asymmetry). Research `ef286939`.
  - [x] **Pilot `olympiadbench_hard` (A1 n≈24)** ✅ 2026-07-22 — **IT DISCRIMINATES: A1 50.0% overall / 76.9% among finished vs the 89% numeric-suite saturation.** But **46% truncate at 16384** → the overall score is budget-confounded (finished-vs-truncated swing ≈57pp). See R5.
  - [x] **Full `olympiadbench_hard` 3-arm run (budget 32768, np=1+MTP)** ✅ 2026-07-23 — **NULL, well-powered on a non-saturated suite** (A1 68.4 / A3 69.0 / A4 64.5, all pairwise p ≥ 0.19; see R6). Config determined by probe first (np=1+MTP); `extract_boxed` bug fixed (A1 +11pp recovered). This was *the* measurement that could have broken the parity tie — it didn't. Surfaced: IQ2 termination defect + the token-budget/concurrency threads → [reasoning-effort-levels.md](reasoning-effort-levels.md).
  - [ ] GPU arms A1/A3/A4 × **`gpqa_diamond_cot`** full n=198 — *primary* CoT measure (deferred behind OlympiadBench; n=50 slice done in R2)
  - [ ] MMLU-Pro control re-run under hardened protocol (sidecar's n=50 predates it)
  - [x] **A2 (CPU, 122B UD-Q4_K_M) — RUN EXECUTED overnight 2026-07-23/24 ✅** (fenced production recipe `--repeat-penalty 1.1 --repeat-last-n 256`, port 18073, 25.8 tok/s, pinned-set replay, GPU-session build-hip coexistence documented): **aime25 COMPLETE 23/30 (76.7%)**; **olympiad_hard: 94 full-pair items (~72% running)** + remainder FILTERED per operator ROI call to the 17 A1-IQ2-failure items in the unanswered range (c=0 assumption on untested A1-correct items can only OVERSTATE the IQ2 penalty → conservative one-sided H1 bound); **gpqa_cot SKIPPED per operator** (power math: 185 pairs → MDE ~6-7pp; +198 → ~4pp; neither sees 1-2pp; AXA-1 knowledge Δ0.0pp n=212 already covers the knowledge axis) — staged + idempotently resumable (`runs_cpu_a2/`, runner resumes on (id,seed)). Live read: A2-Q4 tracking at-or-above A1-IQ2 band. Artifacts: `artifacts/architect-bench-gpu-20260720/runs_cpu_a2/`.
  - [x] **A2/H1 paired analysis DONE ✅ 2026-07-24** (canonical rescore both arms + symmetric format-tolerant math-list pass, selection-bias-corrected McNemar): **unbiased pairs n=141** (olympiad 94 + aime 30 + gpqa-prefix 17 — the 17 rescue-design items EXCLUDED from the test since they condition on A1 failure), discordant b=13 (Q4+) vs c=5 (IQ2+), **pooled p≈0.096 — NOT significant**; direction consistently favors Q4 by ~5.7pp across all three suites (aime 76.7 vs 70.0; gpqa-prefix 88.2 vs 82.4). Rescue leg: **3/17 A1-failures rescued by Q4** (incl. two hard constructive problems). **H1 VERDICT: the IQ2 reasoning penalty is bounded SMALL — point estimate ~3-6pp, CI includes 0 — nothing like the uniform-2-bit literature halving; knowledge axis stays Δ0.0pp (AXA-1 n=212). Two stacked conservatisms both OVERSTATE the penalty**: (1) the rescue-design c=0 assumption; (2) A1 fence provenance is UNRESOLVED (no repeat-penalty field in A1 result meta — if A1 ran unfenced, part of its deficit is loop-loss, not quant). Practical read: **IQ2 is a safe GPU-resident quant for the 122B**; certification to decision-grade would need an A1 fenced re-run (GPU side) but no scheduled decision requires it — the architect keep/drop now hinges on Phase-2 tool-use + the LagoonS2.1 review, not quant fidelity. **BONUS DATA provenance**: the 17 gpqa pairs came from an orphaned chain-runner that survived a kill race (kill children before parents; third wrapper-vs-process instance this cycle — also explains the filtered leg running 2 interleaved streams on the np=1 server: wall-clock only, accuracy unaffected). Analysis: /mnt/raid0/llm/tmp/h1_paired_analysis.py; artifacts runs_cpu_a2/. ORIGINAL: **A2/H1 paired analysis** (after the filtered leg lands ~2026-07-24 10:40Z): canonical-extractor rescore first (R7 scorer-artifact fix, regression `274fe0c1`), then McNemar over the 94+30 full pairs + the rescue-bound read on the filtered 17; fold the H1 verdict into this handoff + the master index. ORIGINAL TASK: **A2 (CPU, 122B UD-Q4_K_M) — ownership transferred 2026-07-23 to the CPU/serving session lineage** (operator-directed: the fresh operator session is GPU-only). Must use `--questions-in` on the pinned manifests (else pairing is void). Blocks H1. **Execution plan (owner)**: run as the FENCED arm together with RP-5 (one campaign: A2 accuracy + repeat_penalty 1.1 fence on both sides of the Q4-vs-IQ2 pairing) — single-model unattended serial run, accuracy-not-speed so tolerant of the MI210 session's 8-core host-thread coexistence (document it in the run record); proposed slot = the next overnight/unattended stretch, keeping operator-present windows for E5 W0/W1. RP-3 (boxed-prompt trigger) analyzed post-hoc on A2 outputs. Sequencing ratified by operator 2026-07-23: E5 W0/W1 hold the operator-present windows; A2/RP-5 takes unattended time.

**Run protocol actually used (GPU arms, 2026-07-20)** — kernel `production-consolidated-v7` (`build-hip`, 10098/`6ad45fa3f`), MI210, one arm at a time, `--device ROCm0 -ngl all -fa on -ctk f16 -ctv f16 -c 32768 -b/-ub 2048`, server `--reasoning off` + request `enable_thinking=false`, production sampling **temp 0.6 / top_p 0.95 / top_k 20 / seed 42** (+1 per avg@k pass). Per-arm spec-dec set to each model's **measured** optimum (A1 `draft-mtp` n-max 2; A3/A4 n-max 4) — see the registry `optimal_gpu_serving` blocks. GPU servers pinned to cores 88–95 so the CPU inference stack is untouched.
**avg@k ordering:** repeats are the *outer* loop — each pass sweeps all questions at one seed — so an interrupted run degrades to a valid avg@(k−1) rather than a subset-biased score. Arms stopped at different k are still comparable by filtering the per-question JSONL to the seeds all arms completed.
**Throughput rows from these runs are OBSERVATION-grade** (pre-`P-GPU-1`); the accuracy verdict is device-independent and decision-eligible.

### Result R1 — GPQA-Diamond, letter-only / no-CoT (n=198 paired, seed 42, 2026-07-20)

| Arm | accuracy | trunc | noparse | Δ vs A1 | McNemar |
|---|---:|---:|---:|---:|---|
| **A1** 122B-A10B UD-IQ2_M | **55.1%** | 0 | 0 | — | — |
| **A3** 27B dense Q8 | **55.6%** | 4 | 2 | **+0.5pp** | b=35 c=36 **p=1.00** |
| **A4** 35B-A3B Q8 | **53.0%** | 16 | 3 | **−2.0pp** | b=33 c=29 **p=0.70** |

**Finding: no arm separates from any other on no-CoT GPQA-Diamond.** All pairwise p ≥ 0.63. Under a letter-only prompt the models emit ~2 tokens and cannot reason, so this suite reads *knowledge/priors*, not reasoning depth — and on knowledge the three are equivalent. **This does NOT support H3** (35B-A3B was expected to trail): the shallow 3B-active reasoner ties the 122B when neither may reason. Consistent with the AXA-1 Δ0.0pp result being knowledge-parity, and with the thesis that architect separation must come from the CoT/AIME suites.

> ⚠ **These numbers are POST-correction. The pre-correction run said something different and wrong.**
> The first scoring pass reported A1 55.1% / A3 51.0% / A4 43.4%, i.e. **A1 −A4 = +11.6pp at McNemar p=0.0059 ("significant")**. That entire result was an **answer-extraction artifact**: the extractor only accepted a bare letter when it was the *whole* response, so a reply ending "…reasoning…\n\n**B**" failed to parse and scored wrong. Parse failures were **0 / 13 / 29** across A1 / A3 / A4 — i.e. the bug penalised exactly the arms that show their work, manufacturing an 11.6pp gap and pointing at the wrong architect. Fixed (bare-letter-final-line rule, last-match-wins, delimiter-required `ANSWER` tag); the fix also removed *false positives* (a reply ending "Option D matches this structure.\n\nD" had been scored `C`). **Re-scored offline from stored responses — zero GPU re-run.** Tooling: `architect_bench_rescore.py`, `architect_bench_analyze.py` (which now always prefers `per_question.rescored.jsonl` so arms are never compared under different scorer versions).
> **Rule going forward: report a per-arm parse-failure rate next to every accuracy number; any cross-arm difference is a scoring bug until proven otherwise.**

### R2 (in flight) — reasoning budget dominates, and the stack-wide `enable_thinking=false` default is now in question

**Why this was opened (operator, 2026-07-20):** published GPQA-Diamond for these exact models is far above R1 — Qwen3.6-27B **87.8%**, Qwen3.6-35B-A3B **86.0%** (vendor-reported) vs our 55.6% / 53.0%. The gap is **the measurement condition, not a broken harness**: R1 forced letter-only + `enable_thinking=false`, so the models emitted ~2 tokens. Same arm, same questions, same harness, CoT allowed → **A1 went 55.1% → 83.3%** (early n). Published figures are thinking/CoT numbers and are **not comparable** to a no-CoT probe.

**The deeper problem.** The stack-wide default (`chat_template_kwargs.enable_thinking: false` on `architect_general`, `frontdoor`, `coder_escalation`, …) traces to the 2026-05-20 probe recorded in `feedback_qwen3x_enable_thinking_false` (+33pp for frontdoor). But that probe's *failure mode* was thinking-ON runs hitting `finish_reason=length` with **`content=""`** — the model never emitted an answer inside the budget. **That is a token-budget artifact, the same class as the truncation/parse bugs corrected above** — not necessarily a quality property of thinking mode. The memory itself already flags this confound for the `ingest` row ("most likely max_tokens truncation of native reasoning, not a thinking ablation"); the same doubt applies to the Qwen3.6 rows.

**R2 ablation design** — thinking ON vs OFF, *identical* pinned `gpqa_diamond_cot` items (n=50), **max_tokens 16384** so thinking cannot be starved (the whole point), production sampling, per-arm optimum spec-dec:
- **A4 = Qwen3.6-35B-A3B** — the exact model the +33pp claim was made about, and the production **frontdoor**.
- **A1 = Qwen3.5-122B-A10B IQ2** — the **architect** candidate (and the reviewer-arm model).
- Server: `--reasoning on --reasoning-budget -1 --reasoning-format deepseek` (thoughts → `reasoning_content`, so `content` is scored cleanly) vs `--reasoning off`. Note `-rea/--reasoning [on|off|auto]` is a real flag — the runs above genuinely disabled thinking, they did not merely hide it.
- Metrics: accuracy, **empty-content-with-reasoning rate** (the documented degenerate-loop signature), truncation, and **median completion tokens** — because the deploy decision is quality *per latency*, not quality alone.

**Scope note:** a positive result changes production config for architect/reviewer/frontdoor roles, which is **operator-gated** and must weigh the latency/throughput cost (thinking multiplies output tokens; frontdoor is latency-sensitive). This bench only *measures*; it does not change the stack.

#### R2a — **allowing CoT in the response is worth +32pp**, and it validates the harness against published numbers

Arm **A4 = Qwen3.6-35B-A3B (production frontdoor)**, **identical 50 questions**, thinking mode **OFF in both conditions** — the only change is whether the *prompt* permits reasoning:

| A4 condition (same 50 Q) | accuracy | mean tokens |
|---|---:|---:|
| "Answer with the letter only" | **52.0%** | 537 |
| "Reason step by step, then answer" | **84.0%** | 2150 |
| **Δ** | **+32.0pp** | **4.0× tokens** |

McNemar **b=19 c=3, p=8.6e-04** — decisively significant, 0 truncations, 0 parse failures.

**Two conclusions:**
1. **The harness is externally validated.** 84.0% sits within noise of the vendor-published **86.0%** for this exact model (n=50 ⇒ ±~10pp). The earlier 53% was never a harness defect — it was a no-CoT probe, and the ~33pt gap from published is the reasoning contribution.
2. **This is a PROMPT effect, not a thinking-mode effect** — `enable_thinking=false` in *both* arms. So "reasoning off" in this stack has (at least) two independent axes, and they must not be conflated:
   - **(a) does the prompt let the model reason in `content`** — worth +32pp here, at 4× output tokens;
   - **(b) `enable_thinking` / `--reasoning`** — the native `<think>` channel, still being measured (R2b).
   Axis (a) is a *prompt-template* property of each role, not a server flag, and it is the larger effect measured so far. **Any stack-wide "should our models reason?" review has to cover both axes**, or it will change the flag and leave the +32pp on the table.

#### R2b — thinking mode on the **frontdoor** is a *termination* failure; the stack default is VINDICATED

A4 = Qwen3.6-35B-A3B, same 50 pinned items, `max_tokens=16384` (**8× the 2048 of the original 2026-05-20 probe**), `--reasoning on --reasoning-budget -1 --reasoning-format deepseek`:

| A4 | accuracy | median tok | budget-exhausted in `<think>`, **empty content** |
|---|---:|---:|---:|
| think **off** | **83.3%** | 1343 | 0 |
| think **on** | **50.0%** | 16043 | **23 / 48 (48%)** |

Paired: **−33.3pp, McNemar b=1 c=17, p=1.0e-04**, at **5.9× output tokens**.

**My "budget artifact" hypothesis is REFUTED for this model.** The +33pp thinking-off advantage *reproduces* at 8× the original budget, so the stack-wide `enable_thinking=false` default is **empirically correct for Qwen3.6-35B-A3B** — it was not an artifact of a stingy `max_tokens`.

**But the cause is a termination defect, not a quality deficit.** 48% of the time the model consumes the entire 16384-token budget inside `<think>` and emits *zero* content. Splitting the two populations:
- On the **25 items where thinking terminated**: ON 96.0% vs OFF 92.0% → **+4.0pp, b=1 c=0, p=1.00 (n.s.)**. The eye-catching "96%" is **selection bias**, not a thinking win.
- On the **23 items where it never terminated**: think-off still scored **73.9%**, so these are *not* merely the impossible questions — thinking loops preferentially on the harder ones, i.e. exactly where reasoning was supposed to help.

**Actionable lever (untested):** llama-server exposes `--reasoning-budget N` (>0) plus `--reasoning-budget-message`, which force-closes the think block so the model *must* emit an answer. That converts the 48% total losses into (short-thought) answers and is the obvious next experiment — it belongs to [`reasoning-effort-levels.md`](reasoning-effort-levels.md) E-6.

**Do not generalize this to the architect yet** — A1 (122B-A10B IQ2) is a different model and is measuring now. "Frontdoor should not think" ≠ "architect should not think".

#### R2c — with CoT allowed, A1 leads A4 by 6pp but **it is NOT statistically supported**, and GPQA-Diamond looks saturated

Same 50 pinned items, CoT allowed, thinking off:

| Arm | accuracy | mean tokens |
|---|---:|---:|
| **A1** 122B-A10B IQ2 (architect) | **90.0%** | 3582 |
| **A4** 35B-A3B (frontdoor) | **84.0%** | 2150 |
| Δ | **+6.0pp** | 1.7× |

**McNemar b=5 c=2, p=0.45 — not significant.** Only **7 discordant pairs** at n=50; this is badly underpowered and must not be read as separation. Directionally consistent with A1 > A4, nothing more.

**Two consequences for the rest of the bench:**
1. **GPQA-Diamond may be saturating for these arms.** At 84–90% only ~5–8 items separate any two arms, and A1's 90.0% already exceeds A4's *published* 86.0%. Per [[feedback_eval_saturation_masks_model_gap]], a suite near ceiling hides real capability gaps — so a null here is weak evidence of equality, not evidence of parity. **AIME'25 (much lower ceiling) becomes the decisive discriminator**, which raises the value of the queued avg@4 run.
2. **The full n=198 CoT run matters** — ~4× the discordant pairs. Run it before drawing any H2/H3 conclusion.

**Contrast worth keeping:** under letter-only these same two arms were 55.1% vs 53.0% (p=0.70, n=198). Allowing CoT lifts *both* by ~30pp and widens the gap slightly, but does not by itself resolve which model reasons better.

#### R3 — AIME'25 avg@4 (the decisive, non-saturated discriminator) — IN PROGRESS

n=30 problems × 4 draws (seeds 42–45), CoT prompt, thinking off, budget 16384, per-model optimum spec-dec. Reported as **avg@4** (mean over draws) with **pass@4** (solved ≥1/4) for reference.

| Arm | avg@4 | pass@4 | truncated draws |
|---|---:|---:|---:|
| **A1** 122B-A10B IQ2 (architect) | 71.7% | 83.3% | 7/120 (6%) |
| **A3** 27B dense Q8 | **74.2%** | **90.0%** | 0/120 |
| **A4** 35B-A3B Q8 (frontdoor) | 70.8% | 86.7% | 1/120 |

**Three-way paired (all 30 problems), pass@4 McNemar — H2 & H3 both resolve to NEAR-PARITY:**
- A1 vs A3: A3-only=2, A1-only=0, **p=0.50** — A3 weakly dominant, n.s.
- A1 vs A4: A4-only=2, A1-only=1, **p=1.00**
- A3 vs A4: A3-only=2, A4-only=1, **p=1.00**
- 2 problems (I-14, I-15) solved by **no** arm.

**Verdict on the decisive suite: no arm is statistically separable from any other.** The spread is A3 74.2% ≥ A4 70.8% ≈ A1 71.7% — a 3.4pp band, all p ≥ 0.50 at n=30. **H3 fails** (the 3B-active A4 does *not* trail — it ties both larger arms). **H2 is near-parity** (27B-dense ≈ 122B-IQ2, if anything the 27B edges it). This is now **four independent measurements agreeing** (letter-only GPQA, CoT-GPQA, AIME'25, AXA-1 Δ0.0pp) that at ≤AIME difficulty these three models reason equivalently. **AIME'25 at n=30 cannot separate them** → the OlympiadBench harder-tier discriminator (running) is the test that matters; if it *also* shows parity, the architect decision has no accuracy basis and falls entirely to deployment-robustness (favoring the dual-resident 122B).

**Paired A1 vs A3 (identical 30 problems) — H2 signal: the 27B-dense reasons at least as well as the 122B-IQ2.**
- avg@4: A3 **74.2%** vs A1 71.7%; pass@4: A3 **90.0%** vs A1 83.3%.
- McNemar on pass@4: **b=2 (A3 solved, A1 didn't) c=0 (reverse), p=0.50 — not significant**, but **strictly dominant in direction**: A3 solved *everything A1 solved, plus 2 more* (II-8, II-15); A1 solved **nothing** A3 missed. Both failed the same 3 hardest (I-14, I-15, II-13).
- A3 also had **zero truncation** vs A1's 6% — the dense model reaches its answer in fewer tokens.

**Read (pending A4):** on the decisive, non-saturated suite the 122B-IQ2 shows **no reasoning advantage** over the 27B-dense — consistent with the GPQA-CoT null (R2c) and the AXA-1 Δ0.0pp. Zero problems distinguish the 122B upward. This is **H2 near-parity**, and it means the architect decision is **not** carried by hard-reasoning accuracy → the deployment-robustness axis (dual-resident 122B cheaper to operate at equal quality; GPU-only 27B has no CPU self-fallback and pins the single GPU slot) becomes decisive. **Caveat:** n=30 is low power; a 2-problem gap is well within noise. This weighs the *operating-cost* branch of the decision tree, it does not by itself crown the 27B. A4 next = the H3 check.

#### R2d — **native `<think>` hurts BOTH models. `enable_thinking=false` is vindicated stack-wide.** ✅ complete

All four ablation arms, n=50 pinned items, `max_tokens=16384`, `--reasoning-budget -1`:

| Arm | think off | think on | Δ (paired) | McNemar | token cost | non-terminating `<think>` |
|---|---:|---:|---:|---|---:|---:|
| **A1** 122B-IQ2 (architect) | **90.0%** | 74.0% | **−16.0pp** | b=0 c=8 **p=0.0078** | 2.79× | **9/50 (18%)** |
| **A4** 35B-A3B (frontdoor) | **84.0%** | 48.0% | **−36.0pp** | b=1 c=19 **p<0.0001** | 6.03× | **25/50 (50%)** |

**Verdict: the stack-wide `enable_thinking=false` default is CORRECT, for both roles, and my "budget artifact" hypothesis is fully refuted.** The effect reproduces at **8× the original probe's budget** and is significant for both models. Thinking-ON is worse *and* costs 2.8–6× the tokens — it loses on both axes.

**Root cause is termination, not reasoning quality.** Conditioning on whether `<think>` ever closed:
- **A1:** terminated on 41/50. There: ON 90.2% vs OFF 95.1% (**−4.9pp, b=0 c=2, p=0.50, n.s.**).
- **A4:** terminated on 25/50. There: ON 96.0% vs OFF 92.0% (**+4.0pp, b=1 c=0, p=1.00, n.s.**).
- On the *non*-terminating items, think-off still scored **66.7%** (A1) and **76.0%** (A4) — so these are **not** simply the impossible questions; the loop preferentially eats items the model could otherwise answer.

So when thinking terminates it is roughly **quality-neutral** on this suite (both n.s., opposite signs); the entire measured loss is the non-termination tail. The **severity is strongly per-model** (18% vs 50%), which is direct evidence for the per-model calibration invariant in [`reasoning-effort-levels.md`](reasoning-effort-levels.md).

**This does NOT close the "our models should reason" question — it re-points it.** The +32pp win (R2a) came from **CoT in `content` via the prompt**, which is *already* how these arms run and is a different axis from `enable_thinking`. The native `<think>` channel, as configured today, is a liability for both models. The open lever is `--reasoning-budget N` (>0) + `--reasoning-budget-message`, which force-closes the think block so the model must answer — untested, and the single highest-value follow-up (E-6).

**Operator decision surface (measurement only — no stack change made):** keep `enable_thinking=false` everywhere (now evidence-backed at an adequate budget), and pursue reasoning quality through **prompt-level effort** rather than the native channel.
### Follow-up tooling / deferred (derived this session)
- [x] **Build the interleaved-per-question sequential runner** with always-valid / e-process stopping (§8 of the runbook). ✅ 2026-07-29 — `epyc-inference-research` commit `b55b4c43` adds `scripts/benchmark/architect_sequential_runner.py` plus four focused tests. It requires a pinned manifest and a numeric a-priori difficulty key, executes exactly two named arms per question, persists each completed pair atomically, reuses the orchestrator's authoritative e-process primitive, and refuses to update either process on transport failure. The runner provides a dry-run mode and makes no inference unless invoked without it. Focused suite: `4 passed, 1 subtests passed`.
- [x] **Promote the GPU driver scripts into the repo** (`gpu_lib.sh`, `run_arm.sh`, `run_budget.sh` — currently session scratchpad) so the runbook's launch pattern is executable, not just documented. (Runbook §10 records this deferral.) ✅ 2026-07-29 — `auditor`, epyc-inference-research `7fea61f9`, as `scripts/benchmark/architect_bench_gpu_{lib,arm,budget}.sh`.
  **They could not be promoted verbatim — three defects, none cosmetic:**
  1. **Both runners sourced ANOTHER SESSION'S `/tmp` scratchpad** (`/tmp/claude-1000/-workspace/355c9594-…/scratchpad/gpu_lib.sh`). Promoted as-is they are dead on arrival — the exact failure this row exists to prevent. Now sourced repo-relative via `${BASH_SOURCE[0]}`.
  2. **`--kernel production-consolidated-v7` on a v8 binary = false provenance.** Verified against the binary the scripts actually launch, not against the docs: `llama-server --version` reports **`10107 (67a433bf4)`**, exactly the v8 freeze. `v7_quality_gate_runner.py --kernel` is free-text metadata with an unvalidated `v7-candidate` default, so nothing downstream could have caught the wrong stamp. `KERNEL_LABEL` is now **required**, and unset is a refusal (exit 3) *before* anything launches.
  3. **The two surviving copies of `gpu_lib.sh` disagreed on the core pinning** — scratchpad `CORES=88-95` vs `artifacts/np_context_study_20260723/driver/` `184-191` (2026-07-24). 88-95 is the **superseded** value; taking the obvious source would have enshrined a known-wrong host-thread pinning as the repo's canonical driver. Promoted copy takes 184-191 and records why.
  *No GPU work was run: the guard was tested in isolation and all three are `bash -n` clean.*
- [x] **Declined: AIME'25 hard-tier avg@16 top-up.** Considered; explicitly *not* pursued — it sharpens ~7 problems where A1=A3 already tie (likely a tighter confirmation of parity), whereas OlympiadBench adds harder *items* with real n. Higher expected information → chose OlympiadBench. ✅ 2026-07-21
- [ ] Resolve the decision tree from Phase 1; **(conditional) build + run A5** if branch 2 fires.
- [x] **Phase 2 — tool-use eval RUN across the whole fleet** ✅ 2026-08-02. `tool_compliance`
      (9 questions, 0-3 rubric) scored by architect_critic under one judge, one 8192 budget, all six
      models, zero ineligible: architect_critic 85.2%, frontdoor 77.8%, worker_general 77.8%,
      architect_general 74.1%, worker_vision 74.1%, ingest_long_context 70.4%. **14.8 pp spread** —
      the only axis we own that discriminates. Evidence:
      `epyc-inference-research/data/judge_suite_headtohead_20260802/`. NOTE this is the fleet-wide
      tool-use screen, NOT the "tool-using planning on the surviving arms" depth probe, which is
      still unrun.
- [ ] **Phase 2 depth probe** — tool-using *planning* (multi-step, stateful) on the surviving arms.
      The 9-question compliance screen above is a breadth instrument and does not answer it.
- [x] **Record the architect decision** (checkbox-flip here) → route to AXA-1 (`mi210-big-model-and-acceleration-roadmap.md`) + the model registry.
  **✅ 2026-08-12 (`mainA`, pulled from the generated bench and claimed) — RECORDED. The decision
  was taken and deployed on 2026-07-31; only this record was missing, which is why the auditor's
  T5 flag 3 calls this row "the never-executed mechanism" behind a LIVE AXA-1 drift.**
  **The decision, as realized in production** — read from the registry and the topology, not from
  any narrative:
  - `architect_general` → **`Qwen3.6-27B-MTP-Q8_0`**, GPU-resident. `stack_topology.yaml`
    instantiates it on `GPU_HOST_LANE`.
  - `architect_critic` → **`Qwen3.5-122B-A10B` at `Q4_K_M`**, `backend: local` (CPU), instantiated
    on `NUMA_FULL`.
  So the 122B was **retained as the critic on CPU Q4**, and the architect seat went to the 27B on
  the GPU. That is the W1 cutover of 2026-07-31, and it is the same event that made the
  `12.19 t/s` Probe-B placement record a role-attribution defect elsewhere in this repo.
  **The drift this closes.** `mi210-big-model-and-acceleration-roadmap.md` Axis A still reads
  *"122B UD-IQ2_M MEASURED VIABLE fully GPU-resident — 43.7 t/s single / 148.7 aggregate @B=32"*.
  That sentence is **true as a viability measurement and false as a description of the stack**:
  nothing serves a 122B IQ2 on the GPU, and the production 122B is CPU Q4. A reader taking Axis A
  as roadmap status concludes the IQ2-residency path is live.
  **Routed, not edited.** The AXA-1 correction belongs to the roadmap's owner — it is a different
  handoff and the fix is one clause distinguishing *measured viable* from *deployed*, which the
  owner should word. Filed on the bus rather than edited here.
  **No registry change needed**: the registry is already correct and was the source of this record.
  The row's "→ the model registry" leg is satisfied by verification, not by an edit — the registry
  is what the roadmap has drifted FROM.

## R4 — OlympiadBench-numeric SATURATES too (adapter design flaw, not the ceiling-breaker claimed)
A1 122B-IQ2 = **89.3% (134/150)** on `olympiadbench_numeric` — *higher* than its AIME'25 (71.7%), though
this was meant to be the *harder* tier. **Scorer verified correct** (spot-checks all genuine numeric matches
incl. `\sqrt`, degrees; zero false positives). Cause = the **adapter filter**: single-answer clean-**numeric**
gold selects the easy-answer subset — hard olympiad problems disproportionately have Expression/Tuple/set
answers (the ~165 items excluded), so filtering by answer *format* filtered out *difficulty*. Per-tier
Algebra 92.5% / other 87.6% (both saturated); a real hard tail exists but is small (25 truncation-inducing
items @ 56%, ~17% of the suite). **So it's a second saturating suite, not a discriminator.** The
harder-discriminator goal is **unmet** — fix filed above (symbolic scorer for the excluded Expression/Tuple
items, or a harder numeric suite, or lean on Phase 2 tool-use). **Three-way paired final (n=150): A1 89.3% /
A3 88.0% / A4 89.3%, all pairwise p ≥ 0.77 — a complete null** (122/150 solved by all three, only 5 by none;
~28 discriminating items). Even saturated, this is the **highest-powered null of the bench.** *Pattern: this
is the 4th time this session a scoring/selection choice mis-set difficulty — verify a suite discriminates
before trusting its verdict (runbook §8 saturation-diagnosis).*

### ⇒ Bench verdict (reasoning suites, GPU arms): NULL across the board
Six independent paired measurements — letter-GPQA (n=198), CoT-GPQA (n=50), AIME'25 avg@4 (n=30),
OlympiadBench-numeric (n=150), plus AXA-1 Δ0.0pp and the thinking ablations — **all show no separation**
between A1 (122B-IQ2), A3 (27B-dense), A4 (35B-A3B). **H2 = near-parity, H3 = fails** (the 3B-active model
never trails). At the difficulty these suites reach, **the architect choice has no accuracy basis** →
decision falls to **deployment-robustness** (dual-resident 122B cheaper to operate at equal quality; GPU-only
27B has no CPU self-fallback + pins the GPU slot). **Two things could still break the tie and are the only
open quality questions:** (1) a *genuinely* harder discriminator (filed symbolic-scorer fix) or **Phase 2
tool-use** (the architect's real job); (2) **H1** — IQ2-vs-Q4, which needs the **A2 CPU arm** (later session).
Until then, no deployment change is warranted on accuracy grounds.

## R6 — `olympiadbench_hard` FINAL (n=155 paired, np=1+MTP, fixed-extractor rescored): NULL, well-powered
**The decisive result.** On the first genuinely **non-saturated** suite (68/69/64% — real headroom, unlike
GPQA/AIME which saturated ~89%), all three GPU arms are still statistically inseparable:

| arm | acc | truncation | median tokens |
|---|---:|---:|---:|
| A1 122B-IQ2 | **68.4%** | 25% | 6195 |
| A3 27B-dense | **69.0%** | 0% | 4019 |
| A4 35B-A3B | **64.5%** | 0% | — |

Pairwise McNemar: **A1↔A3 p=1.00, A1↔A4 p=0.26, A3↔A4 p=0.19 — no separation.** ⇒ **SIX independent
measurements now null** (letter-GPQA, CoT-GPQA, AIME'25, olympiad-numeric, olympiad-hard, AXA-1 Δ0.0pp).
**The architect candidates reason equivalently across the full measurable difficulty range.** No
reasoning-accuracy basis for the choice → **deployment robustness decides** (dual-resident 122B cheaper to
operate at equal quality), *modulo* the IQ2 defect below. Remaining accuracy unknowns: H1 (needs A2/CPU) and
Phase-2 tool-use (the architect's real job).

**Two corrections landed to get this clean (both scorer artifacts, both fixed offline from stored responses):**
1. **Config:** A1 first ran at np=14/np=4 **no-MTP** (max-opt violation) — the config probe (research
   tooling) found **np=1 + per-model MTP** optimal (MTP +32% at single-stream; batching a wash at 36864-ctx
   that adds non-determinism). A3/A4 ran at np=1+MTP. A1 stayed no-MTP (accuracy is lossless under spec-dec;
   near-parity confirms it's not poisoned).
2. **`extract_boxed` bug** (research `c4fe1e96`): the old extractor grabbed the *incomplete* final `\boxed{`
   from a truncated tail; A1's looping-truncated items had the correct answer in earlier complete `\boxed{}`.
   Fix (last *complete* boxed) recovered **21/40** truncated items → A1 **57.4% → 68.4%**, 0 regressions.

### 122B-A10B termination defect — MODEL-specific, NOT quant-specific (the real caveat on the 122B architect) → see [reasoning-effort-levels.md § MODEL-specific repetition-penalty fence](reasoning-effort-levels.md)
The **Qwen3.5-122B-A10B loops on `\boxed{answer}` to the token cap at BOTH quants** — IQ2 (25% of items) AND
Q4 (A2/CPU, confirmed 2026-07-23: identical `\boxed{}` loop on the same item). The Q8 arms (27B-dense,
35B-A3B) do NOT loop (0–1%). **⇒ the defect tracks the MODEL, not the quant — the "IQ2 EOS-damage"
hypothesis is REFUTED (RP-2).** Post-extractor-fix it costs **no accuracy** but **~2× tokens** (median 6195
vs 4019) — a production *operating* cost **inherent to the 122B-A10B candidate at either quant** (so it does
NOT argue IQ2-vs-Q4 either way). Production gives the 122B architect no repetition penalty at either quant
(bench matched that), so the loop occurs live. **Fix — RP-1 COMPLETE ✅ 2026-07-23: `repeat_penalty 1.1`**
breaks the loop (truncation ~100%→22%, median tokens 32768→10.6k) with accuracy held (22/40 = 55% vs
baseline 21/40); **`1.3` over-penalizes** (tanks math to ~15%, generations grow); **DRY (0.8) ruled out**
(inconsistent loop-break + mangles answers, 0/40). Apply **per-model** (the 122B-A10B, both quants), not
per-quant, not blanket. **Clean H1 (Q4 vs IQ2 accuracy) now requires the fence on BOTH arms** (RP-5) — both
loop unfenced. RP-3: is the `\boxed{}` prompt itself the trigger? (leading root-cause hypothesis).

## R5 — `olympiadbench_hard` DISCRIMINATES (finally a non-saturated suite) — but is budget-gated
Built the harder-tier fix R4 called for: `olympiadbench_hard` = the 155 Expression/Tuple/set OlympiadBench
items the numeric suite excluded (where difficulty lives), scored by a new **sympy-backed `math_symbolic`**
path (numeric → set/tuple → symbolic equivalence; validated 155/155 gold self-match, **0 perturbation
false-positives, 0 LaTeX-variant asymmetry** — the per-arm parse-bias guard the numeric suite lacked).
**Pilot (A1 122B-IQ2, n=24): 50.0% overall — the first sub-saturation reading of the bench** (vs 89% on
`olympiadbench_numeric`, 88–90% on GPQA). **But 46% truncate at 16384 tokens** (median 9.7k, these olympiad
problems induce very long reasoning), and truncation ≈ wrong (2/11 truncated correct). **Accuracy among
*finished* responses = 76.9%**, so the 50.0% is heavily budget-suppressed. **⇒ the full 3-arm run is GATED
on `max_tokens ≥ 32768`** — at 16384 the arms would be partly ranked on reasoning *concision*, a confound.
This is now the single outstanding measurement that could break the reasoning-parity tie (R1–R4 all null).
It also surfaced a **stack-wide finding — `max_tokens` is a silent quality lever** — documented as a study
in [`reasoning-effort-levels.md § Token-budget study`](reasoning-effort-levels.md) (operator-flagged).

## Dependency graph
`Prep (AIME adapter)` ∥ `Gate1 v7-promotion` → `Gate2 inference-batch-loop` → `Gate3 operator quiet window`
→ `Phase 1 (A1–A4)` → {decision | conditional A5} → `Phase 2` → `record decision`.
Prep is independent of the gates; the inference is not.

## Cross-cutting concerns
- **This is the reasoning re-gate that AXA-1 deferred** (LLM-rubric gate). A pass here *upgrades* AXA-1's
  IQ2 residency from knowledge-parity to reasoning-certified; a fail *changes the GPU-slot plan*.
- **No stack/production change** is made by this bench — it is measurement only. The architect deployment
  change (if any) is a *separate* operator-gated action informed by the result.
- **Instrument discipline:** pre-`P-GPU-1`-cert GPU numbers are OBSERVATIONS. The *quality* verdict
  (accuracy, device-independent) is decision-grade; the *throughput* rows are not until post-promotion.

## Reporting instructions
Per arm×suite: write the paired result (n, pass count, Δ vs A2, McNemar p) with a MEASUREMENT stamp.
At Phase 1 completion: flip the Phase-1 checkbox, record which decision-tree branch fired, and update
this Status line. On a final architect decision: flip the record checkbox here, append the verdict to
AXA-1, and open a registry-change note (do NOT edit the live registry — that's operator-gated).

## Key file locations
- Eval runner (reuse + extend): `epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py` (`gpqa`,`mmlu_pro` adapters; add `aime`).
- Arm GGUFs: `/mnt/raid0/llm/models/` (paths in the Arms table).
- Phase-2 dataset: `/mnt/raid0/llm/datasets/swe-bench-verified/` (FAIL_TO_PASS oracle).
- Evidence: `docs/reference/architect-model-selection-2026-07-20.md`.
- Related handoffs: [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (AXA-1),
  [`reviewer-model-ablations.md`](reviewer-model-ablations.md) (H5, model-role selection sibling),
  [`v7-promotion.md`](v7-promotion.md) (gate 1), [`inference-batch-loop.md`](inference-batch-loop.md) (gate 2).

## Intake (research provenance — persisted 2026-07-20)
6 papers deep-dived read-only; see `research/intake_index.yaml`: net-new `2508.18672`, `2505.11574`,
`2505.02390` (highest-priority — exact toolchain), `2604.07035`; promoted-from-reference `2504.04823`;
already-integrated `2505.09388` (intake-074).


## Laguna S 2.1 intake integration — 2026-07-22 → **UNBLOCKED 2026-07-26 by the v8 freeze**
_Via /research-intake Stage-2 (intake-879/880); the "ONCE SERVED" blocker is CLEARED — Laguna arch is in frozen `production-consolidated-v8` (`67a433bf4`), IQ2 GPU-quality-attested (P-GPU-1), CPU Q4 lane exercised. Operator-sequenced 2026-07-26 as the GPU lane of the post-v8 campaign (see master index checkpoint)._
- [x] **L-IQ2 capture arm (GPU, MI210)** ✅ 2026-07-26: completed config discovery → SWE-oracle capture → LCB-hard with the production-v8 MI210 sidecar. The selected banked configuration was f16 K/V + Flash Attention (`35.490117 tok/s` median decode in the source sweep). LCB-hard is terminal at `14/53` (`26.4%`), `0` errors, `8` truncations included in the denominator, about `40.2 tok/s`. The original SWE `18/40` (`45.0%`) result is provisional and superseded: the original runner persisted only the response tail, so it cannot be used as a terminal quality claim. Evidence: `/mnt/raid0/llm/epyc-inference-research/artifacts/architect-laguna-iq2-v8-20260726/laguna_gpu_lane_provenance_bundle.json`. The paired LCB comparison against historical v7 A1/A3/A4 is diagnostic only and cannot gate a same-era decision.
- [x] **L-IQ2 scorer-artifact correction gate** ✅ 2026-07-27 — final operator-directed deterministic v4 replay, with official FAIL_TO_PASS evaluation over the fixed 40-task denominator: A3 `23/40` (`57.5%`), Laguna `17/40` (`42.5%`), A1 `15/40` (`37.5%`), A4 `13/40` (`32.5%`); all four have zero harness errors. The finalization verifies `678/678` hashes and the identical sealed converter SHA `6bd2302dda3e5139cc6faabcc5639bdcf85b27895f93a9181cbb53dd65749507`. The metadata-only flip record explains the apparent Laguna `18→17` as four lost and three gained instance verdicts, and A4 `14→13` as the single `matplotlib__matplotlib-14623` truncation/empty-patch disposition; no sealed file or test verdict was changed. Evidence: `epyc-inference-research/artifacts/architect-same-era-v8-20260726/final-4arm-v4-tail-replay-20260727/runs/final-4arm-v4-tail-replay-20260727T080703Z/final_4arm_table.json`; flip record `epyc-inference-research/artifacts/architect-same-era-v8-20260726/final-4arm-v4-tail-replay-20260727/publication/score_flip_disposition_20260727.json` (SHA-256 `f0faafd6f847552f6e251d690cb07d57445868cb80122f1872add3d20a64c768`).
- [x] **L-IQ2 reviewed-reconstruction official Docker comparison** ✅ 2026-07-27 — superseded as the terminal score by the final four-arm v4 replay above. It remains retained as reconstruction/root-cause evidence only; no deployment or lineup conclusion derives from it.
- [x] **L-IQ2 capture-loss classification and five-row exact-tail replay** ✅ 2026-07-26 — the 13 empty rows and five inherited nonempty exact-tail rows were recaptured losslessly; request/capture integrity was clean. The reconstructed mixed artifact is retained for root-cause evidence but is superseded for scoring.
- [x] **L-IQ2 same-era A3/A4 raw confirmation captures** ✅ 2026-07-26 — fresh v8 A3/A4 SWE-oracle `40/40` and LCB-hard `53/53` raw arms completed with zero request errors. LCB terminal counts are A4 `28/53`, A3 `24/53`, Laguna `14/53`; their banked SWE outputs were deterministically tail-replayed through the final v4 scorer on 2026-07-27.
- [x] **L-IQ2 lossless-capture prevention boundary** ✅ 2026-07-26 — schema v4 retains and fingerprints full prompt/response/reasoning, binds the reviewed runner and pinned prompts, atomically quarantines invalid resume rows, publishes per-row live status, fails incomplete one-shot CI, rejects stale/ineligible converter outputs, and preserves token-cap rows as explicit model failures. Focused validation: `78 passed, 3 subtests passed`, Ruff clean.
- [x] **L-IQ2 clean full-40 prompt-contract-fix arm — CANCELLED/SUPERSEDED** ✅ 2026-07-27 — the operator-directed finality rule selects deterministic replay of banked outputs over fresh generation where the scorer/converter path, rather than generation, was defective. The terminal Laguna v4 arm is included in the final table; no additional same-era inference is authorized.
- [x] **L-IQ2 official score + coding-specialist read** ✅ 2026-07-27 — quality first: corrected SWE40 is A3 `23/40` > Laguna `17/40` > A4 `13/40`, but same-era LCB-hard reverses the relevant role comparison at A4 `28/53` > A3 `24/53` > Laguna `14/53`. Laguna therefore is **not supported as a general `coder_escalation` replacement**: it beats the incumbent on SWE but loses half the incumbent's LCB solves. The operating surface is favorable only on raw speed: Laguna's selected IQ2 GPU configuration measured `35.490117 tok/s` in the base sweep and about `39.5–40.2 tok/s` during the coding captures versus the incumbent A4 registry baseline of `24.3 tok/s`. That gain requires a dedicated `34.7/64 GB` MI210 residency, while the incumbent A4 GGUF already shares its mmap with frontdoor. A narrowly specialized SWE route remains an operator-owned possibility; no role or lineup change is authorized.
- [x] **L-Q4 quant-axis quality screen (CPU)** ✅ 2026-07-27 — the completed Laguna-S-2.1 Q4_K_M SWE40 generation was replayed through the sealed v4 converter and official evaluator: Q4 `19/40` versus IQ2 `17/40`, zero harness errors, overlap `13`, discordants `6:4`, exact paired two-sided `p=.75390625`. This `n=40` screen **does not resolve a quant-axis quality difference**; it is not an equivalence or absence-of-difference proof. Under the operator-requested quant-axis shortcut, the queued Q4 LCB53 generation is stopped because it no longer informs the current architect decision. Reproducible evidence: `epyc-inference-research/artifacts/laguna-q4-cpu-v8-20260726/laguna-q4-swe-v4-tail-replay-20260727T165223Z/` (research `f7ab3ec4`).
- [x] **TB-6 — Laguna UD-IQ2_M DFlash-off throughput-only Cartesian surface terminal** ✅ 2026-07-28 — frozen-v8, no-thinking, cpuset `184-191` surface is terminal with `24/24` dispositions: `21` measured cells plus `3` bound `allocation_failure` capacity-start skips (`np32/L16384` and `np16/L32768` at context `524288`; `np32/L32768` at `1048576`), `0` missing/invalid/request-error cells, and `6` retained model length-cap rows. Decode frontier by maximum length: `L2048 np32=73.7`, `L8192 np32=88.2`, `L16384 np4=60.9`, `L32768 np8=62.0` tok/s; the global measured peak is `88.2` decode / `119.6` total tok/s at `np32/L8192`. Evidence: `epyc-inference-research/artifacts/np_context_study_v8_20260727/Laguna_ud_iq2_gpu_dflash_off/terminal-validation.json`. This is a throughput-only observation and authorizes no capacity-superiority, lineup, registry, or production action.
- [ ] **L-Q4P conditional CPU performance discovery.** The bounded four-cell config selector and broader CPU sweep remain deferred. Trigger only if a concrete CPU-resident Laguna role proposal needs a measured throughput/cost surface; the saved run's median `8.14 tok/s` is observation-only and authorizes no lineup or registry action.
- [x] **A3-vs-A4 SWE-oracle powered confirmation — SHELVED** ✅ 2026-07-27 — A3 leads the final four-arm v4 table outright, so the precommitted stopping rule shelves the powered-160 confirmation. Reopen only if a corrected table reorders an outcome that changes an actual deployment decision; no model inference was launched for this shelved task. Evidence/workflow retained: `/mnt/raid0/llm/epyc-inference-research/artifacts/architect-laguna-iq2-v8-20260726/a3-a4-swe-confirmation/`.


## 2026-07-25 — intake Stage-2a dive: ThinkingCap arm, corrected

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](intake-derived-work-2026-07-25.md)._

- [x] **A3-tc sealed first-read — ThinkingCap-Qwen3.6-27B, legacy thinking-enabled diagnostic/confounded** ✅ 2026-07-27 — the complete v8 banked capture was deterministically replayed through the frozen v4 converter and official FAIL_TO_PASS evaluator: `18/40` (`45.0%`), `16` explicit empty-patch failures, zero harness errors. Subsequent argv audit proved this arm used `--enable-thinking` while FF/stock used no-think; `15/16` empties are reasoning-channel cap truncations. It remains evidence only of that asymmetric thinking-mode configuration and is not comparative authority; the corrected no-think row is recorded at FG-3. The rb512/rb1024 calibrations remain a separate budgeted-thinking axis, not substitutes for the clean arm.
- [x] **ThinkingCap comparison disposition and dive corrections integrated.** ✅ 2026-07-27 — MTP is held separate; the vendor table is under-powered and mostly negative out-of-domain; ThinkingCap is a weights-frozen finetune rather than a reasoning-budget dial; the capped `53/53` LCB pass remains diagnostic-only. No regeneration was used after the scorer-path review.
- [x] **A3-tc exact-GGUF license gate — WAIVED by operator** ✅ 2026-07-27 — operator decision: "provenance is irrelevant. Just performance." License/provenance review is removed as a candidacy blocker; the provenance evidence file remains on record (`epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/thinkingcap_license_provenance_20260727.json`) but gates nothing. Candidacy is performance-only from here.
- [x] **A3-tc FG-1 token-efficiency read (performance leg).** ✅ 2026-07-29 — deterministic replay of sealed SWE40 outputs is byte-reproducible (`fg1_results.json` SHA-256 `7776c106…bcfb`; `FG1_SUMMARY.md` SHA-256 `01b32136…cea1`): A3-tc used 5,021.1 completion tokens/official solve versus A3 1,506.5, but its thinking-enabled configuration is cap-truncation-confounded (15/16 empty patches hit the 3,072-token cap), so it cannot rank token efficiency. The effort-invariant candidacy question remains: every finite LCB calibration budget capped, so no equal-effort read exists yet; an equal-effort LCB re-run with wider budgets is warranted only if a future clean FG-1 read leaves the thesis alive.

## 27B finetune candidates — downloads + bench (operator-sequenced 2026-07-26, GPU lane after MiniCPM-o)

> **Sequencing note 2026-07-31**: the "after MiniCPM-o" dependency is **discharged** — MiniCPM-o
> Phase-1 is closed as a decline (deprecated, weights deleted; 31/42 vs the 35/42 incumbent on
> 42q OCRBench+ChartQA), so nothing in this section waits on it any longer.

- [x] **D-27B — all three operator-launched sequential downloads completed** ✅ 2026-07-26. Exact final sizes: ThinkingCap Q8 `29,047,082,976` B, Fable-Fusion Q8 MTP `30,239,022,560` B, and Fable-Fusion Q8 non-MTP `29,787,701,792` B; no target `.part` files or transfer processes remain. Bounded GGUF-header inspection confirms ThinkingCap and Fable MTP each have `866` tensors plus `qwen35.nextn_predict_layers=1`; Fable non-MTP has `851` tensors and no NEXTN metadata/tensors. The Fable pair has identical specifications for all `851` base tensors and exactly `15` MTP-only tensors, matching the fixed `451,320,768` B delta. The designated curl log ends at stage-3 `100%` with no error/retry signal but cannot contain the original `ALL DONE` criterion: `dl_27b_q8.sh` redirects only curl output to that log while its success markers go to the launching terminal. Completion is therefore attested from the script's success-only atomic `.part` rename, three exact finals, zero remnants, and clean process exit; nothing was relaunched.
- [x] **A3-ff sealed first-read — Fable-Fusion-711 non-MTP.** ✅ 2026-07-27 — the complete v8 banked capture was deterministically replayed through the frozen v4 converter and official evaluator: `19/40` (`47.5%`), `5` explicit empty-patch failures, zero harness errors. The separate stock/Fable-non-MTP/Fable-MTP diagnostic remains `20/19/20` on SWE40, `28/25/19` on LCB-hard53, and `27.1/27.0/26.6 tok/s`; embedded MTP remains a separate probe and is absent from the six-arm authority row.
- [x] **A3-ff deterministic scoring-integrity closure** ✅ 2026-07-27 — full-response v4 captures were converted and sealed without regeneration. Exact-denominator, source-hash, exhaustive non-recovery, disjoint-partition, and atomic-publication checks pass; the future sealer rejects overlapping official-report partitions. Focused authority/path-correction validation: `10 passed`. Final metadata-only successor: `expanded-six-arm-v4-report-path-correction-20260727/path_correction_successor.json`, SHA-256 `e12dcda1223a77f7864b33c93dd009295d25d0b24527af4891f1f121fb4f748d`.
- [x] **TB-6 — Fable-Fusion MTP throughput-only Cartesian surface terminal** ✅ 2026-07-28 — frozen-v8 MTP surface has `21` measured cells plus `3` documented capacity skips and `0` invalid cells; its terminal validator passed. On the shared measured cells, the observation-grade MTP/non-MTP ratios are decode geometric mean/median `1.3104x`/`1.3632x` and total geometric mean/median `1.3117x`/`1.3663x`. Paired identity/equivalence provenance is closed: the `851`-tensor non-MTP and `866`-tensor MTP artifacts differ by the fixed 15 MTP tensors, and the v8/binary-pinned deterministic spot check is exact for content and tokens on `5/5` prompts (`comparison.json`). Evidence: `epyc-inference-research/artifacts/np_context_study_v8_20260727/A3_ff_fable_mtp_q8/terminal-validation.json` and `ff_mtp_equivalence_spotcheck_20260727T222427Z/`; restored `paired_provenance.txt` SHA-256 `a9ad520767dca7ac8e47a3db81eb774e14b38b9c2ace188758f4cbb21a241f46` is byte-identical to the queue writer.
- [x] **TB-6 paired capacity comparison terminalization (Fable non-MTP)** ✅ 2026-07-28 — the non-MTP surface terminal validator reports `24/24` dispositions: `22` measured cells plus `2` bound `allocation_failure` capacity-start skips (`np32/L16384` at context `524288`; `np32/L32768` at context `1048576`), with `0` invalid or missing cells. Its measured peak is `102.0` decode / `110.4` total tok/s at `np16/L2048`. This closes the paired capacity evidence surface, but not a capacity-superiority conclusion: all shared-cell ratios remain observation-grade only and authorize neither role/lineup, registry, nor production action. Evidence: `epyc-inference-research/artifacts/np_context_study_v8_20260727/A3_ff_fable_non_mtp_q8/terminal-validation.json`.
- [x] **TB-6 — A4 35B-A3B era bridge terminal** ✅ 2026-07-28 — the frozen-v8 `a4_bridge` surface is terminal at `11/11` measured cells, with zero skipped, invalid, or missing cells; its measured peak is `269.8` decode / `291.9` total tok/s at `np16/L2048`. This bridge is throughput-only observation evidence and authorizes no lineup, registry, or production action.
- [x] **TB-6 prefill-to-depth RAG terminalization** ✅ 2026-07-28 — all four prepared frozen-v8/no-thinking LongHealth document-QA arms are terminal: Fable non-MTP, Fable MTP, Laguna UD-IQ2_M, and A4 each retained `18/18` measured `np*_D*` cells with `0` skips. Durable terminal markers and cell evidence are respectively `A3_ff_fable_non_mtp_q8/complete.txt`, `A3_ff_fable_mtp_q8/complete.txt`, `Laguna_ud_iq2_gpu_dflash_off/complete.txt`, and `A4_35b_a3b_v8_bridge/complete.txt` under `epyc-inference-research/artifacts/np_context_study_v8_20260727/`; every marker was paired with its 18 `results.json` records. This is throughput-only observation evidence and authorizes no lineup, registry, or production action.
- [ ] **A3-ff behavioral/abliteration candidacy gate.** No ratified direct-generation refusal/behavior screen exists in the repository; the existing RewardBench reviewer protocol is not applicable. The first-read remains valid, but no role candidacy or lineup action is authorized unless the operator chooses to design and ratify a new screen. Note (2026-07-27): the operator frames FF as a **pre-processing/scaffold tool, not a wholesale role substitute** — its candidacy test moves to the reopened scaffold-generator A/B ([gpu-cot-scaffold-sidecar.md](gpu-cot-scaffold-sidecar.md)); this gate applies only if FF is ever proposed for a direct serving role.

## 2026-07-27 fine-grain + remediation program (operator-directed discussion outcome)

_All six authority rows are in; the operator's read: overall scores hide the structure. Disjointness of solve-sets matters more than totals; both "failure" signatures (Laguna LCB truncations, TC empty patches) may be deterministically patchable like the 122B loop fix; the Laguna speed comparison used a stale registry anchor. FG-1 is pure replay over sealed artifacts (zero inference); FG-2/3 designs are zero-inference, their validation runs queue behind the campaign._

- [x] **FG-1 — fine-grain replay (zero inference)** ✅ 2026-07-27 — executed same-session over the sealed artifacts; evidence `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg1-fine-grain-replay-20260727/` (`FG1_SUMMARY.md` + `fg1_results.json`). Headlines: (a) **Laguna SWE-route specialist DEAD** — its 17 solves are a strict subset of A3∪A4 (unique=0), A3 dominates +6/−0 exact p=.031 (only significant pair); (b) **TC empties are cap truncations during thinking-mode generation** — 15/16 hit the 3072 cap, including 12 zero-response and 3 partial-response rows; the remaining row is `skipped_missing_path`. TC as-configured is 3.3× more expensive per solve (5,021 vs A3 1,506 tokens/solved), but the asymmetric thinking configuration is confounded and cannot support a comparative token-efficiency conclusion; (c) **FF is the actual token-efficiency winner** — −40% median completion tokens vs stock (237 vs 397), tokens/solved 1,083 vs A3 1,507, quality statistically tied (p=.29); (d) FF-MTP leaner still (median 233) but LCB-weak. Bonus: 14/40 instances unsolved by all six = the discriminating hard-core set for future focused benches; A3 keeps 3 unique solves. Evidence hygiene repair accepted and pushed: research `325f7c2e` (sealed-input provenance, taxonomy, exact values) and root `82215b81` (handoff taxonomy).
- [x] **FG-2 — Laguna LCB truncation classification + remediation design** ✅ 2026-07-27 — zero-inference replay classified all `8/8` cap truncations exhaustively and disjointly: five format spirals, two genuine long derivations, and one literal repetition loop. Each item is bound to its sealed response SHA and bounded tail evidence. The remedy must remain class-specific: answer-contract prompt for the five format spirals, cap-only ablation for the two genuine-long rows, and loop-control sampler for the literal loop. Evidence: `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg2-fg3-sealed-classification-20260727/` (JSON SHA-256 `f862e27bcd7582c91f1e785f844e99bd0254561d3d5ddca1eccab1ec56bd0f0a`). FG-1 prior still shows Laguna also truncated 9/40 SWE rows (11 empties), but FG-1(a)+FG-4 killed the SWE-route case; any remaining payoff is non-coding candidacy (FG-5).
- [x] **FG-2V — focused post-campaign validation** ✅ 2026-07-28 — terminal over exactly the eight preclassified rows, fixed seed, no request/harness errors. Loop control changed `lcb_abc320_e` from a 4096-token length stop to a normal 1723-token stop but it remained wrong. The answer contract made four of five format rows stop normally and produced `2/5` correct, but only `lcb_abc323_e` was a new solve (`lcb_abc331_e` was already correct); `lcb_abc341_f` still capped. Larger-cap generation added no solve: `lcb_abc318_e` stayed correct and capped at the 8192 context boundary, while `lcb_abc314_f` stayed wrong at the effective 6726-token context ceiling and again at a corrected full 8192-token cap under `-c 16384`. Net focused delta is `+1/8` solve, which would move the banked Laguna LCB total only `14/53 → 15/53`; this does not reopen the coder-role case. Evidence: `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg2v-laguna-focused-20260728/fg2v-20260728T133936Z/` plus the live-defect repair `fg2v-long-context-repair-20260728T135141Z/`. No full-suite regeneration or role/lineup action is authorized.
- [x] **FG-3 — TC no-think validation and deterministic replay terminal** ✅ 2026-07-28 — argv audit confirmed the legacy six-arm TC row was not apples-to-apples: it used `--enable-thinking` while FF/stock used `--no-enable-thinking`; the `15` thinking-mode cap truncations and 5,021 tokens/solved therefore remain diagnostic only. The corrected same-era no-think capture was sealed and deterministically replayed through the frozen v4 converter: official SWE is `21/40` (`52.5%`), `0` harness errors, `3` empty-patch failures, and `2` model length-cap failures; LCB is `24/53` (`45.28%`), `0` request errors, and `3` model length caps. Capture/argv hashes and finalization seal verify at `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg3-tc-nothink-v4-tail-replay-20260728/`. This corrected no-think row replaces the legacy thinking-enabled row for the FG-3 comparison; it does not authorize a role, lineup, registry, or production action. Codex's rb512/rb1024 budgeted-thinking calibrations remain a separate axis.
- [x] **FG-4 — A4 speed re-anchor** ✅ 2026-07-27 — operator was right: the 24.3 tok/s registry row dates to 2026-05-04 (pre-v6/v8 kernels, MTP-blind). Same sealed capture window (`decode_tok_s` telemetry, n=40/arm): **A4 median 94.5 tok/s** (p10 81.8 / p90 114.8) vs Laguna 44.6, A3 52.7, A1 55.2. **The Laguna speed argument inverts** — Laguna is ~2× slower than the incumbent it was claimed to beat; combined with FG-1(a), no SWE-route case survives. Observation-grade (capture telemetry, not canonical recipe) — sufficient to kill the stale-anchor comparison, not to update the registry row.
- [x] **FG-4b — canonical A4 optimized-serving re-anchor** ✅ 2026-07-29 — decision-grade `FG-4b/A4-CPU-optimized-server-v1` completed at `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg4b-a4-cpu-optimized-server-20260729T110152Z/`: median `13.159866755320987 tok/s`, MAD `0.0163318316089196`, five exact 512-token `np=1` server completions, all `finish_reason=length`, after the ratified stability warmup. `protocol_status=ratified_receipt_validated`, `decision_grade=true`, `proposal_only=true`; teardown is `ps_verified_dead=true`. The affinity-witness receipt is `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T105911Z.json` (SHA-256 `b4ee39b8e10dc771e305070f84a3b0e93a5b4207bbdb0cdab57b36023c4c0385`). The generated registry patch remains review-required/proposal-only and was **not applied**; no measured row was hand-edited. The post-run production restoration used `--skip-stack-change-gate --no-compile-registry` only because the normal canonical-stack gate encountered pre-existing stale hashes, and only to restore the already-running 24 endpoints exactly; it is a restoration-only exception, not a benchmark or registry-apply authorization.
- [x] **FG-5 — CLOSED by weights deletion** ✅ 2026-07-28 — the operator deprecated Laguna and its weights were deleted (108G freed; `gpu-serving-tie-in-program.md` D7). The non-coding-strengths question remains UNANSWERED (this close is administrative, not a falsification); reopening requires an operator decision + re-download + an operator-selected non-coding suite/protocol. Original scope marker preserved: SWE/LCB cannot falsify the GLM-5.2-competitor claim for long-context/agentic/general workloads; the L-Q4 quant-axis screen completed without resolving a difference.
- [ ] **FG-6 — BCB-hard pre-deployment regression screen (CONDITIONAL — do not run now; operator decision 2026-07-27).** BCB-hard is explicitly NOT run on the finetunes as a ranking instrument: it proved non-discriminating on this family (coding-ladder pooled tie n=347) and is the wrong distribution for both theses (library-API recall, where the scaffold lane showed distilled-reasoning transplants no-op). **Trigger**: fires only if FF or TC advances to actual role candidacy (cheaper-A3 substitute, post-scaffold-A/B promotion, or TC re-ranked into contention by the FG-3 no-think arm). **Purpose at trigger**: production-representative regression screen — real coder-role traffic is library-API-shaped, so the gate is "does not regress vs stock on BCB-hard," not a ranking read. One arm per advancing candidate, no-think protocol, same-era.

## 2026-07-29 — intake Stage-2 dive: Qwopus3.6-27B-Coder arm + zero-inference weight-delta geometry

_Via `/research-intake` Stage-2 2026-07-29 (intake-913…932 batch); the bench arm is operator-requested. Neither item is comparative authority until it runs under the sealed same-era protocol above._

- [ ] **Collect and bench Jackrong/Qwopus3.6-27B-Coder MTP-Q8_0** (29.0 GB, apache-2.0, 63k downloads). It carries the lineage's ONLY full-denominator SWE-bench Verified run — 335/500 = 67.0% measured **thinking-off**, matching our stack — at ThinkingCap-class onboarding cost with zero merge work. **CAVEAT THAT MUST TRAVEL WITH THIS NUMBER WHEREVER IT IS QUOTED: 67.0% is SWE-bench Verified, vendor self-reported, n=1, full-500 denominator, and is NOT commensurable with our sealed SWE-oracle-40 (A3 `23/40`).** Different instrument, different denominator, different scaffold — it may not be set beside any authority row in this handoff. Preconditions: (a) **verify the JSON tool-call parser first** — this family emits JSON inside `<tool_call>`, NOT Qwen's XML `<function=…><parameter=…>` form, and the chat template differs between v2 (6,994 B) and Coder (4,718 B), so verify **per model, not per family** (a cross-arm parse-failure gap reads as a quality gap — see R1's parse-artifact rule above; tracked as 2b-agentic-1 in [`scoring-infra-standardization.md`](scoring-infra-standardization.md)); (b) hold MTP constant across arms.
- [ ] **Zero-inference weight-delta geometry probe.** Stream the local Q8 GGUFs (stock Qwen3.6-27B / ThinkingCap / Fable-Fusion / MTP control), dequantize per tensor, and per layer L compute r(L)=‖Δ_FF‖/‖Δ_TC‖, c(L)=cos(Δ_TC,Δ_FF), p(L)=⟨Δ_FF,Δ_TC⟩/‖Δ_TC‖² against the shared base. **Free exact ground truth:** our own spec-dec work established at byte level that ThinkingCap = stock + exactly 256 LoRA modules (r=64, α=128), so Δ_TC is EXACTLY ZERO on ~600 non-LoRA tensors — those measure nothing but the Q8 dequant noise floor, the quantity that decides whether GGUF delta-geometry is trustworthy at all. Second payoff: TC and FF are independent siblings off stock, so the lineage detector p(L) should sit near 0 and flat; if it drifts to 1.0 anyway, the "Coder descends from V2" inference is an artifact. Minutes of CPU, no GPU lane, no download.
  - [x] **E5-safe instrument and input preflight** ✅ 2026-07-29 — committed `epyc-inference-research` `4c1a3ac3` (`scripts/benchmark/weight_delta_geometry.py` plus three synthetic tests). The instrument streams Q8_0 blocks only after explicit `--execute`; default `--plan` touches no model payload and production execution remains deferred while E5 Stage-B exclusively owns CPU. Verified local stock/ThinkingCap/Fable Q8 inputs exist; no inference, GPU work, or real-model dequantization occurred.

## 2026-08-03 — intake Stage-2/2b: the code-runtime-efficiency axis, and two model-candidate verdicts

_Via `/research-intake` on intake-938…990. The compendium had **deep coverage of speedup-rewarded GPU
kernel generation and zero coverage of code-runtime efficiency as an evaluation axis** — six instruments
are now indexed. Nothing below is comparative authority until it runs under the sealed same-era protocol
above._

### The design space is FOUR instruments, not eight

Mercury (intake-972) → EffiBench / EffiBench-X (intake-952) → SWE-Perf (intake-951) is **one connected
component of four papers**, hubbed on a shared author. So the apparent field-wide consensus that
"efficiency scores must be normalized against a reference distribution" is **half one lineage**. The
genuinely independent instruments diverge sharply: ENAMEL normalizes against **one expert solution with
censoring**; EvalPerf against a **clustered ladder using instruction counts**; GSO against a **single
human commit in the same container**; COFFE against **the best ground truth, binary**.

**Ladder shape — operator-selected 2026-08-03:** *one ranking key, three columns*. Rank on the fused,
instance-gated, expert-normalized, clipped score; report **correctness** beside it; and report a
**derived conditional** only above ≥30 solved instances. A conditional efficiency number computed over a
handful of solves is a ratio with a denominator small enough to be noise.

**Aggregation — operator-selected 2026-08-03:** `harmonic_mean({s_i : i correct})`, reported beside
`correctness_rate`. **Forbidden:** harmonic mean over any set containing failure-clamped sentinels — that
is how SWE-fficiency's headline moved **2.8× on byte-identical outcomes** from one clamp constant. This
also retires the geometric mean, which GSO demonstrated agents *game* (`[0.1, 1000]` → geomean 10 while
regressing a test). Constitutional form: `artifacts/operator/measurement-decision-packages-20260803.md`
DP-2 — **not yet ratified**, so the rule above is the bench's working convention, not a protocol.

### Instrument selection

- [ ] **Adopt EffiBench-X as the efficiency instrument, Python-only, restricted to the 308 DATED problems.** Apache-2.0, and its local-endpoint support **works unpatched** (`OpenAI()` with no args after `load_dotenv()`). Three blockers must be patched onto **upstream**, not taken from the `effibench-enhanced` re-upload (intake-986, zero lineage, created-and-pushed six minutes apart): the deprecated `openjdk:21` image, a `time.sleep` `AttributeError`, and a **fail-open-to-0.0 metric**
- [ ] **Run a canonical-solutions acceptance gate FIRST, before any model arm.** The fail-open-to-0.0 path is our own named defect class sitting on the exact metric we would adopt, and it is unfixed in both upstream and the re-upload. If canonical solutions do not score as canonical, the instrument is not measuring what its name says
- [ ] **Pull GSO's two `abetlen/llama-cpp-python` optimization tasks (~21 GB) and run them against the coder and architect roles.** MIT, expert-commit performance targets, and **the only thing in this literature that lands on our own serving stack**. Import its equivalence contract; do NOT import its timing discipline — `timeit.timeit(..., number=1)` is a single timed run per test, and its `check_equivalence` compares a reduced digest (`shape` plus `first_entries[:5]`) that an optimization wrong outside the digest passes
- [ ] **Run EvalPerf against our local endpoint** — lowest friction in the cluster: Apache-2.0, native `--backend openai --base-url`, ~15 min/model, ~100 MB. Its measurand is retired instructions via hardware counters, max CV 0.4% across four test beds. **Valid for generated-code scoring only** — instruction counting is explicitly invalid for our bandwidth-bound inference kernels, and was falsified in-session where a tiled traversal executing +1.9% instructions ran **2.83× faster**
- [ ] **Add the Slow/CRR conditional diagnostic** (intake-974): among a model's **correct** outputs, what fraction is no faster than baseline. It separates correctness inflation from genuine efficiency gain, and it is the one number that makes the derived conditional column above interpretable
- [ ] **Ingest arXiv `2607.01211` BEFORE finalising the instrument choice** — it directly meta-evaluates this entire cluster and may pre-empt the decision

### Declines, named so they are not re-derived

- **Decline SWE-Perf as a harness.** Its code carries **no licence at all**, unanswered for nine months. Its statistical gate is kept.
- **Decline SWE-fficiency's images** — 1.03 TB. **Adopt its `cpu_assignment.py`** (196 lines, Apache-2.0), which produced correct NUMA-and-SMT-aware cpusets on our EPYC on the first run.
- **Decline Mercury** (intake-972) — the repo has no licence file at all, so the code is all-rights-reserved. Peer review was not the differentiator it appeared to be: EvalPerf is also peer-reviewed and beats it on licence, maintenance, measurement design and local-endpoint support. Ingest as lineage evidence only.
- **Decline an efficiency axis over SWE40 / LCB.** Original correctness tests clear the duration-spread gate for **≤3.8%** of problems, and an independent audit (intake-976: 4 benchmarks, 1,538 tasks, 30 reps each) finds only **6.11%** of purportedly performant reference implementations significantly faster on original tests. **Our sealed tasks physically cannot carry a timing signal** — this is a property of the workload, not of our harness.
- **Decline PerfCodeBench** (intake-975) for ~60 days — no licence, anonymous review-only link, nvcc-bound, and CUDA is 5.2% of its test split. Reopen on a licensed public release or any ROCm/HIP path.

### Model-candidate verdicts — answering the standing search for a faster `worker_general` / `architect_critic`

- [x] **Inkling — NO on both roles** ✅ 2026-08-03 (intake-941/942/955). Three independent reasons, any one sufficient: (a) **12B active parameters vs gemma4-26B-A4B's ~4B** on a bandwidth-bound decode path projects **2–4× slower**, which is the opposite of the requirement; (b) the upstream llama.cpp PR is **rejected in its current form and strips MTP**, and `src/llama-arch.h` in frozen v8 carries 138 `LLM_ARCH_*` entries ending at `DFLASH` with **no `LLM_ARCH_INKLING`** — so there is no serving path today; (c) for `architect_critic` it would *close* the 122B's measured GPU-resident IQ2 path (43.7 tok/s single / 148.7 aggregate @B32, PPL 5.02). No download, no bench — the verdict is decided from architecture and kernel support.
- [x] **Escha — NO to the artifact, YES to the experiment it motivates** ✅ 2026-08-03 (intake-945/946/956). The `eschamoe` 2-bit format is closed CUDA sm_80-120 with no ROCm path, so the published build is unusable here. But it points at a model worth testing on its own merits — see the task below. The third-party codebook reverse-engineering probe (intake-956) stays `stage1-unverified` and **deferred with a named trigger**: its author is blocked, 2–4 weeks.
- [ ] **Bench `Qwen3.6-35B-A3B` at `UD-IQ3_XXS` as a `worker_general` candidate.** ~3B active (leaner than gemma4-26B-A4B's ~4B on the bandwidth-bound path), **already supported by the frozen kernel**, and at **13.2 GB it fits `worker_general`'s existing 16 GB budget** in `stack_templates/default.yaml` with no lineup change. **Use `UD-IQ3_XXS`, NOT the size-matched `UD-Q2_K_XL`** — `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:73-74` carries `static_assert(!iqk_typeA_supported(GGML_TYPE_Q2_K))` and the same for `Q3_K`, so a Q2_K build forfeits iqk acceleration entirely. Quant-axis detail lives in [`tq3-quantization-evaluation.md`](tq3-quantization-evaluation.md); hold MTP constant across arms, and pair speed with a correctness check.

## 2026-08-07 — LFM2.5-2.6B `worker_general` candidate (intake-1006/1014/1019)

- [ ] **WG-LFM-1 — Run a matched Q4_K_M / Q8_0 / Gemma4 26B-A4B worker verdict.** Pin the
  official LiquidAI GGUF revision `b421ad1d549afeda6a0fb2ad3a697cb5a7879adc`; test both
  `LFM2.5-2.6B-Q4_K_M.gguf` and `LFM2.5-2.6B-Q8_0.gguf`, with the current Gemma4 26B-A4B
  `worker_general` as the unchanged incumbent. Start with load/template/tool-call smokes on frozen v8;
  then use identical role prompts, tools, task rows, seeds, limits, stop conditions, and scorer era.
  Hash and archive the **GGUF-embedded** chat template used by the runner—the separate LEAP sidecars
  omit its reasoning prefill and tool rendering and are ineligible unless parity is independently
  proven. Report strict task success, per-suite outcomes, tool-schema compliance and repair rate,
  reasoning/output tokens, retries, peak resident memory, prompt/decode throughput, TTFT, and complete
  wall time. Publish Q8-minus-Q4 and each-LFM-minus-Gemma paired deltas. Do not change the role alias,
  registry, stack manifest, or production process unless a later operator decision accepts a
  decision-grade Pareto result.

## 2026-08-09 — OpenRSI release-state watch (research-intake Stage-2b)

- [x] **Watch FrontisAI/OpenRSI PR #2 ("feat(gym): add OpenMLE Sandbox") to a decision.** ✅ 2026-08-11 — **TRIGGER FIRED: MERGED.** Verified live via gh api: merged=true, author_association flipped NONE→CONTRIBUTOR, upstream main pushed 2026-08-11T12:28Z; still 1 commit / 30 files (+7,617), so the merged content is byte-wise the ingest-reviewed content. The intake-940#record hard blocker (distributed grading service unpublished) has SOFTENED, not cleared — see follow-on. State at
  ingest: DRAFT, 30 files, +7,617/-0, one commit, `mergeable_state: clean`, opened 2026-08-09 from
  fork `LifeIsSoSolong/OpenRSI` branch `codex/openmle-sandbox` by an account with GitHub
  `author_association: NONE` — **not a Frontis account by any GitHub signal**. It publishes the
  distributed grading service that intake-940's dive named as the hard blocker on reproducing the
  paper tables. **TRIGGER**: if it merges, re-open that reproducibility finding
  ([intake-1024](../../research/intake_index.yaml) → intake-940). If it is abandoned, record that the
  blocker hardened. `main` was last pushed 2026-08-04, five days before the PR, so nothing has landed.
  **Caveat if it does merge**: reproduction would still require pulling worker and controller images
  from an external registry (they are not in the patch) and reconfiguring this host to cgroup v1 via a
  GRUB edit plus reboot — a host-boot change that is operator-only. The patch also ships default DB
  passwords and two internal RFC1918 worker IPs that the project's own `docs/validation.md` claims the
  public release scrubbed, which corroborates it as an unscrubbed internal snapshot.
- [ ] **Follow-on (opened 2026-08-11, trigger-fired): assess OpenMLE Sandbox reproduction feasibility** — re-opens the intake-940#record reproducibility finding via intake-1024#record. Gates, in order: (1) worker/controller images pull from external registry (network only, any main); (2) **cgroup v1 host reconfiguration = OPERATOR decision** (host reboots are operator-only); (3) actual reproduction run = inference-lane compute. File (2) as a decision package only if (1) succeeds and the images are runnable.

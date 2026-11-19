# Model Evaluation Queue

> **Fold destination** (BRF-T7-F8, BRF-T7-1, route 1b, 2026-11-03): every former handoff of this plan target is a `## Track:` with its own gate marker: `model-evaluation-queue`, `gpu-candidates-surface-qwen38-update`, `paw-compiled-specialists` (rows INF-61, INF-76 retired into EVL-02). The former `model-evaluation-queue.md` body is `## Track: model-evaluation-queue`; tracks those handoffs already had are lifted verbatim after their owner.

**Status**: ACTIVE — the model-evaluation queue (backlog refactor 2026-11, BRF-T1-MEQ, operator D2): every candidate-model trial, bake-off and new-quant trial. Route 1a keeps it as 3 gate-homogeneous files; they merge into this file at BRF-T7-MEQ once per-track gates (route 1b) carry the gated groups.
**Created**: 2026-11-02 (anchor: the former `architect-model-selection-bench.md`, row EVL-02)
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)

> Queue files: this one (ungated group, row EVL-02) · [gpu-candidates-surface-qwen38-update.md](model-evaluation-queue.md#track-gpu-candidates-surface-qwen38-update) (gated on INF-60, row INF-61) · [paw-compiled-specialists.md](model-evaluation-queue.md#track-paw-compiled-specialists) (gated on EVL-08, row INF-76).
> The part below down to the first `## Track:` is the former architect-model-selection-bench handoff; it inherits the
> row's Deps. Each `## Track:` section is a folded handoff; its `<!-- gate: -->` marker reproduces the former row's Deps.

**Priority**: MEDIUM — T6 inference-ready (rank 36), 112 open across 30 candidate-model tracks, only 4 blocked; routine bake-off queue that fills compute gaps.

## Track: model-evaluation-queue
<!-- gate: none -->

> Folded from the body of `handoffs/active/model-evaluation-queue.md` (row EVL-02), from its first `##` section on, @ `063fc7a23b98` on 2026-11-03 (BRF-T7-F8, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

#### Architect Model Comparison Benchmark

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni-wg-lfmi-cpu2b-20261030/`, `/mnt/raid0/llm/tmp/codex-ni-qwen36-iq3xxs-candidate-20261030/` (retained historical native evidence; Qwen READY withdrawn by operator, no current keeper claim).

*(Retarget 2026-10-28 (operator): Qwen3.5-122B deprecated. The A1/A2 122B arms are historical only. Every open item
here runs on current arms: Qwen3.8-27B, Qwen3.8-Flash-Next, and the finetunes.)*

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

#### Open decisions (operator to confirm)
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

#### Why this bench exists (the gap, in one paragraph)
The architect wants **large-total + moderate-active** (active⇒reasoning, total⇒knowledge —
2505.09388 / 2508.18672), which makes the **122B-A10B** the literature default. Its GPU-resident IQ2
form (AXA-1: 43.7 t/s single / 148.7 agg@B32, 2.2×/~8–9× over the ~20 t/s CPU-Q4 incumbent) passed a
**212-question paired eval Δ0.0pp** — but that pool was **instruction-following (84) + factual QA (72)
dominated with only ~4 questions each from gpqa/math/usaco/livecodebench** (~11% hard reasoning), and
the LLM-rubric gate was deferred. The literature (2505.02390, **our exact GGUF+Unsloth toolchain on a
DeepSeek-class MoE**) says 2-bit leaves **knowledge ~99% intact while halving reasoning** (uniform Q2:
V3 AIME 38→15) — *but dynamic UD holds*. So the IQ2 architect is **not reasoning-certified**, and the
answer is genuinely unknown. This bench measures it at full power.

#### Hypotheses
- **H1 (primary, open):** IQ2 preserves the 122B's *reasoning* (A1 ≈ A2 on AIME/GPQA, not just on
  knowledge). Dynamic-UD + a large model *may* hold, contra the small-model quant literature — or not.
- **H2 (challenger):** dense-27B-Q8's max active width out-reasons the 122B on *hard* tasks (near-parity
  in the literature — genuinely open on our workload).
- **H3 (baseline/control):** 35B-A3B (3B active) trails both → confirms frontdoor ≠ architect.

#### Arms

| Arm | Model / quant | Device | GGUF (on disk ✅) | Isolates |
|---|---|---|---|---|
| **A1** | Qwen3.5-122B-A10B **UD-IQ2_M** | MI210 | `…/Qwen3.5-122B-A10B-MTP-GGUF/UD-IQ2_M/…UD-IQ2_M.gguf` | vs A2 → **IQ2 reasoning penalty** (H1) |
| **A2** | Qwen3.5-122B-A10B **UD-Q4_K_M** (incumbent) | CPU | `…122B-A10B-UD-Q4_K_M-00001-of-00003.gguf` | quant-control + vs A3 → arch/depth |
| **A3** | Qwen3.6-27B **dense** Q8 | MI210 | `Qwen_Qwen3.6-27B-Q8_0.gguf` | vs A2 → active-width/depth (H2) |
| **A4** | Qwen3.6-35B-A3B Q8 | MI210/CPU | `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` | shallow-reasoner baseline (H3) |
| **A5** *(conditional)* | 122B-A10B **dynamic 3-bit** (Q3_K_M / DQ3-style) | MI210 | *build if triggered* | **graceful-degradation fallback** — run ONLY if A1 shows IQ2 tanks reasoning but Q4 won't fit the GPU (2505.02390: DQ3 ≈ Q4) |

Model roots: `/mnt/raid0/llm/models/`. (27B/35B also have `-MTP-` and EAGLE3 variants — use the plain
Q8 for the quality bench unless throughput is being measured, then use the production MTP variant.)

#### Evals — objective-scored ONLY (no model-as-judge; the reviewer work proved that's near-random)
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

#### Protocol (MEASUREMENT.md)
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

#### Decision tree (exit criteria)
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
> "GPU accelerates, CPU guarantees" fallback design in [heterogeneous-slot-fabric-residency.md](kv-cache-program.md#track-heterogeneous-slot-fabric-residency).

#### Gating (sequenced — do NOT start inference until ALL clear)
1. **[x] v7 promoted to production** (`production-consolidated-v7`) → GPU arms are now `P-GPU-1`-eligible. Tracked in [`v7-promotion.md`](../completed/v7-promotion.md). ✅ 2026-07-20
2. **[ ] `inference-batch-loop.md` outstanding tests complete** — the parallel agent runs that backlog first, on the current orchestration stack. See [`inference-batch-loop.md`](eval-tower-program.md#track-inference-batch-loop).
3. **[x] Operator inference approval — GPU ONLY** ✅ 2026-07-20. Operator granted the GPU arms explicitly ("GPU-only benchmark tasks … DO NOT interfere with any CPU inference resources"), **overriding gate 2 for the GPU arms only**. Gate 2 remains binding for anything touching CPU.

> **GPU/CPU split (operator, 2026-07-20).** The CPU arm **A2 (122B-A10B UD-Q4_K_M)** is explicitly deferred to a **subsequent session**; this session runs GPU arms only and must not touch CPU inference. Consequence: **H1 (the primary hypothesis — does IQ2 preserve the 122B's reasoning?) cannot be answered yet**, because it is the A1-vs-A2 contrast. What the GPU-only pass *can* settle is **H2** (27B-dense vs 122B-IQ2) and **H3** (35B-A3B trails), plus each GPU arm's absolute reasoning level.
> **The A2 session MUST replay the pinned item sets** at `artifacts/architect-bench-gpu-20260720/questions_<suite>.json` via `--questions-in`, or the pairing (and any McNemar test) is void.

#### Prioritized task list
##### Prep (no inference — can proceed now)
- [x] Handoff spec authored ✅ 2026-07-20
- [x] Evidence/decision-tree note authored (`docs/reference/architect-model-selection-2026-07-20.md`) ✅ 2026-07-20
- [x] All 4 base-arm GGUFs confirmed on disk ✅ 2026-07-20
- [x] **Build the AIME'25 adapter** (`aime25`, 2025-only/30 Q) and register it in `ADAPTER_SUITES` ✅ 2026-07-20
- [x] **Build a real GPQA-*Diamond* adapter** (`gpqa_diamond`, 198 Q) ✅ 2026-07-20 — *the pre-existing `gpqa` suite is GPQA **main (448)**, not Diamond; the spec called for Diamond*
- [x] Build `gpqa_diamond_cot` (CoT-permitting variant) ✅ 2026-07-20 — *see "reasoning budget" note below*
- [x] Harden the runner: per-question JSONL, pinned item sets, production sampling, `enable_thinking`, repeats, truncation capture ✅ 2026-07-20
- [x] Fixture-test adapters + scorer offline (25 assertions, 0 failures) ✅ 2026-07-20
- [x] Confirm MMLU-Pro control re-runs under the hardened protocol (sidecar's n=50 run predates it). ✅ 2026-08-12 — canonical stratified `n=150`, seed `42` manifest (`2d3694d2…`) ran across all GPU arms: **A1 93/150 (62.0%, 0 trunc)**, **A3 88/150 (58.67%, 21 trunc)**, **A4 plain-Q8 76/150 (50.67%, 34 trunc)**, all with zero request errors. Raw paired exact McNemar: A1/A3 `p=.458`, A1/A4 `p=.0095`, A3/A4 `p=.0428`; A4's 34 length-caps make the latter two protocol outcomes, not a clean latent-knowledge separation. Exact claims `akd-e6861331c8664ebe`, `akd-88db6688708f401c`, and `akd-78172f1843d64a38` were released; server death, free claim and zero KFD processes were verified. Authority: research main panel under `artifacts/architect-bench-gpu-20260720/runs/mmlu_pro/panel.json`.
- [x] **Canonical judge-suite head-to-head, 27B vs frontdoor** ✅ 2026-08-02 — paired, one judge,
      matched 8192 budget, identical 70 questions: **180/204 (88.2%) vs 179/204 (87.7%)**, 9 wins /
      4 losses / 55 ties, exact sign test **p = 0.267**. Consistent with this handoff's standing NULL.
- [x] **Established WHY the suite reads NULL** ✅ 2026-08-02 — **50 of 68 questions (74%) score a
      perfect 3 for both arms**; `general` is 100% saturated. It is a ceiling artifact, not model
      equivalence: published benchmarks separate the same pair on **8 of 8** axes.
- [x] **Retire or harden the saturated suites.** `general` (100% both-perfect), `thinking` (90%),
      `math` (89%) carry no discriminating information at this model tier and should not be used for
      any keep/drop read. ✅ 2026-08-12 (`auditor`) — RETIRED (not hardened), machine-readable and
      fail-closed: research `benchmarks/prompts/v1/suite_retirements.json` (rates + 08-02 evidence,
      tier ≥27B), consumed by `score_with_claude.py` (per-row stamp column, NON-DISCRIMINATING
      banner, comparative total over live suites only, all-retired runs exit 3, missing/invalid
      sidecar refuses to score at all) and `rebuild_summary.py` (cells stamped, totals exclude
      retired suites, rebuild aborts without the sidecar). 12 new tests incl. 4 mutation checks
      (sidecar deleted / entry deleted / either guard neutered — all fail loudly). Evidence:
      epyc-root `artifacts/audit/saturated-suite-retirement-20260812.md`; runbook §8 updated.
      Hardened-v3 design sketch (out of scope here) is in the audit report for the bench owner.
- [x] **Strip per-question calibration examples from `rubric_system_prompt`.** ✅ 2026-08-12 (`auditor`) — stripped to generic level anchors (research `9501b353`, `score_with_claude.py`; dated comparability note in-module: absolute levels break at this boundary — pre-strip runs incl. the 08-02 head-to-head were scored WITH the priming; A-vs-B under one judge version unaffected. **Owner note: if absolute judge levels ever gate a decision, an eval-instrument era row should accompany this boundary** — flagged, not self-authored). It named specific
      `question_id`s with the score they got on other models (`math/t3_q2_combinatorics` as a
      score-1 exemplar, `coder/t1_q1_algorithm` as score-0), priming the judge on identity before it
      reads the answer. Affects absolute level; harmless for A-vs-B since both arms get it.
- [x] **Fixed two false suite questions (suites → v2)** ✅ 2026-08-02 — `math/t3_q2_combinatorics`
      asserted an identity whose LHS is identically 1 (the 27B proved it and was penalised);
      `coder/t1_q1_algorithm` claimed two bugs in code with one. Both answer keys documented the
      defect and shipped anyway. Scores recorded before this fix are against suite v1.
  - **Audit 2026-07-29:** still unrun. The only matching sidecar directory is `architect-bench-sidecar-20260720/phase1_gpu_override/main_a3_qwen36_27b_q8_mmlu_pro_20260720T174115Z/`; its server log fails before inference with `--device ROCm0` invalid, and it contains neither runner output nor per-question results. The hardened campaign has no `questions_mmlu_pro.json` manifest or MMLU-Pro run directory. A replacement is fresh GPU inference, not deterministic replay; retain the checkbox and request an owned GPU window plus the hardened runner/pinned-manifest recipe.
- **[declined: ws58 2026-11-03 content-review: duplicate of mi210-serving-program P5-2 (FAIL_TO_PASS scorer validation)]** (Phase 2, if approved) build/validate the SWE-bench-Verified agentic scorer → FAIL_TO_PASS pass/fail.

###### Prep findings that change the protocol (2026-07-20)
1. **`gpqa` ≠ GPQA-Diamond.** The registered `gpqa` adapter loads `ankner/gpqa` = 448-row GPQA **main**. Diamond membership was recovered from the local `hendrydong/gpqa_diamond` mirror; all **198/198** matched into the main set by normalized question text, so `gpqa_diamond` keeps real MC distractors while being verifiably the Diamond subset.
2. **AIME data defect.** `opencompass/AIME2025` ships `2025-II-5` as `336^\circ`. Left uncleaned it is unmatchable by an integer-emitting model — a silent 0 for *every* arm. `aime25` normalizes answers to the integer at load.
3. **Reasoning budget is a confound on letter-only MC.** Under the stock "Answer with the letter only" prompt at `enable_thinking=false`, A1 emits **2 tokens** (no CoT at all) while A3 spontaneously writes **~168 tokens mean (max 1442)**. The arms therefore get *unequal* reasoning budgets, and a letter-only score cannot speak to reasoning depth. `gpqa_diamond_cot` equalizes this and is the **primary** reasoning measure; letter-only is retained as a secondary no-CoT/prior probe.
4. **`enable_thinking=false` is mandatory** for these Qwen arms (degenerate `<think>` loops otherwise), and `--reasoning off` at the server — corroborated by the registry's own `reasoning_policy_observation` (`--reasoning auto` → 0/4 produced final content).

##### Gated inference (after all three gates)
- [ ] **Phase 1** — current arms (Qwen3.8-27B, Qwen3.8-Flash-Next, Qwen3.6-35B-A3B-MTP-Q8_0) × {AIME'25, GPQA-Diamond, MMLU-Pro control}, paired, seed-pinned, MEASUREMENT-stamped. (re-scoped 2026-11-03 from A1 Qwen3.5-122B IQ2_M, A2 122B Q4_K_M and A3 Qwen3.6-27B Q8: deleted; arms now Qwen3.8-27B, Qwen3.8-Flash-Next and Qwen3.6-35B-A3B-MTP-Q8_0; only the gpqa_diamond_cot child stays open)
  - [x] **GPU arms A1/A3/A4 × `gpqa_diamond` (letter-only, no-CoT secondary probe)** ✅ 2026-07-20 — **all three arms statistically indistinguishable** (R1)
  - [x] **GPU arms A1/A3/A4 × `aime25` avg@4** (n=30 × 4, seeds 42–45) ✅ 2026-07-21 — **near-parity, no arm separable** (R3): A1 71.7 / A3 74.2 / A4 70.8; all pairwise p ≥ 0.50; **H3 fails, H2 near-parity**
  - [x] **Per-model GPU spec-dec optima swept + recorded to registry** ✅ 2026-07-20 (`optimal_gpu_serving`: A1 mtp-2, A3/A4 mtp-4)
  - [x] **Thinking-mode ablation (R2a–d)** — CoT-prompt +32pp; native `<think>` ON hurts both (termination defect); `enable_thinking=false` vindicated ✅ 2026-07-21
  - [x] **Reusable bench runbook authored** (`docs/reference/architect-bench-runbook.md`) ✅ 2026-07-21
  - [x] **Build OlympiadBench harder-tier discriminator** (`olympiadbench_numeric` + `math_numeric` scorer, 492 items, 97% gold-parse) ✅ 2026-07-21
  - [x] GPU arms A1/A3/A4 × **`olympiadbench_numeric`** (n=150 paired) ✅ 2026-07-22 — **⚠ SATURATES (A1 89.3/A3 88.0/A4 89.3, all p≥0.77), NOT the harder tier intended** (adapter filter flaw; see R4). Highest-powered null of the bench.
  - [x] **Build a genuinely-harder discriminator** (derived R4) ✅ 2026-07-22 — `olympiadbench_hard` suite (155 Expression/Tuple/set items, the complement of the numeric suite) + **`math_symbolic` sympy-backed scorer** (validated 155/155 self-match, 0 perturbation-FP, 0 LaTeX-variant asymmetry). Research `ef286939`.
  - [x] **Pilot `olympiadbench_hard` (A1 n≈24)** ✅ 2026-07-22 — **IT DISCRIMINATES: A1 50.0% overall / 76.9% among finished vs the 89% numeric-suite saturation.** But **46% truncate at 16384** → the overall score is budget-confounded (finished-vs-truncated swing ≈57pp). See R5.
  - [x] **Full `olympiadbench_hard` 3-arm run (budget 32768, np=1+MTP)** ✅ 2026-07-23 — **NULL, well-powered on a non-saturated suite** (A1 68.4 / A3 69.0 / A4 64.5, all pairwise p ≥ 0.19; see R6). Config determined by probe first (np=1+MTP); `extract_boxed` bug fixed (A1 +11pp recovered). This was *the* measurement that could have broken the parity tie — it didn't. Surfaced: IQ2 termination defect + the token-budget/concurrency threads → [reasoning-effort-levels.md](context-and-token-economy.md#track-reasoning-effort-levels).
  - [ ] GPU arms (Qwen3.8-27B, Qwen3.8-Flash-Next, Qwen3.6-35B-A3B) × **`gpqa_diamond_cot`** full n=198 — *primary* CoT measure (deferred behind OlympiadBench; n=50 slice done in R2) (re-scoped 2026-11-03 from A1 Qwen3.5-122B IQ2_M and A3 Qwen3.6-27B Q8: deleted; arms now Qwen3.8-27B, Qwen3.8-Flash-Next, Qwen3.6-35B-A3B)
  - [x] MMLU-Pro control re-run under hardened protocol (sidecar's n=50 predates it) ✅ 2026-08-12 — all three GPU arms completed on the same pinned 150-row manifest; see the prep result and panel above.
  - [x] **A2 (CPU, 122B UD-Q4_K_M) — RUN EXECUTED overnight 2026-07-23/24 ✅** (fenced production recipe `--repeat-penalty 1.1 --repeat-last-n 256`, port 18073, 25.8 tok/s, pinned-set replay, GPU-session build-hip coexistence documented): **aime25 COMPLETE 23/30 (76.7%)**; **olympiad_hard: 94 full-pair items (~72% running)** + remainder FILTERED per operator ROI call to the 17 A1-IQ2-failure items in the unanswered range (c=0 assumption on untested A1-correct items can only OVERSTATE the IQ2 penalty → conservative one-sided H1 bound); **gpqa_cot SKIPPED per operator** (power math: 185 pairs → MDE ~6-7pp; +198 → ~4pp; neither sees 1-2pp; AXA-1 knowledge Δ0.0pp n=212 already covers the knowledge axis) — staged + idempotently resumable (`runs_cpu_a2/`, runner resumes on (id,seed)). Live read: A2-Q4 tracking at-or-above A1-IQ2 band. Artifacts: `artifacts/architect-bench-gpu-20260720/runs_cpu_a2/`.
  - [x] **A2/H1 paired analysis DONE ✅ 2026-07-24** (canonical rescore both arms + symmetric format-tolerant math-list pass, selection-bias-corrected McNemar): **unbiased pairs n=141** (olympiad 94 + aime 30 + gpqa-prefix 17 — the 17 rescue-design items EXCLUDED from the test since they condition on A1 failure), discordant b=13 (Q4+) vs c=5 (IQ2+), **pooled p≈0.096 — NOT significant**; direction consistently favors Q4 by ~5.7pp across all three suites (aime 76.7 vs 70.0; gpqa-prefix 88.2 vs 82.4). Rescue leg: **3/17 A1-failures rescued by Q4** (incl. two hard constructive problems). **H1 VERDICT: the IQ2 reasoning penalty is bounded SMALL — point estimate ~3-6pp, CI includes 0 — nothing like the uniform-2-bit literature halving; knowledge axis stays Δ0.0pp (AXA-1 n=212). Two stacked conservatisms both OVERSTATE the penalty**: (1) the rescue-design c=0 assumption; (2) A1 fence provenance is UNRESOLVED (no repeat-penalty field in A1 result meta — if A1 ran unfenced, part of its deficit is loop-loss, not quant). Practical read: **IQ2 is a safe GPU-resident quant for the 122B**; certification to decision-grade would need an A1 fenced re-run (GPU side) but no scheduled decision requires it — the architect keep/drop now hinges on Phase-2 tool-use + the LagoonS2.1 review, not quant fidelity. **BONUS DATA provenance**: the 17 gpqa pairs came from an orphaned chain-runner that survived a kill race (kill children before parents; third wrapper-vs-process instance this cycle — also explains the filtered leg running 2 interleaved streams on the np=1 server: wall-clock only, accuracy unaffected). Analysis: /mnt/raid0/llm/tmp/h1_paired_analysis.py; artifacts runs_cpu_a2/. ORIGINAL: **A2/H1 paired analysis** (after the filtered leg lands ~2026-07-24 10:40Z): canonical-extractor rescore first (R7 scorer-artifact fix, regression `274fe0c1`), then McNemar over the 94+30 full pairs + the rescue-bound read on the filtered 17; fold the H1 verdict into this handoff + the master index. ORIGINAL TASK: **A2 (CPU, 122B UD-Q4_K_M) — ownership transferred 2026-07-23 to the CPU/serving session lineage** (operator-directed: the fresh operator session is GPU-only). Must use `--questions-in` on the pinned manifests (else pairing is void). Blocks H1. **Execution plan (owner)**: run as the FENCED arm together with RP-5 (one campaign: A2 accuracy + repeat_penalty 1.1 fence on both sides of the Q4-vs-IQ2 pairing) — single-model unattended serial run, accuracy-not-speed so tolerant of the MI210 session's 8-core host-thread coexistence (document it in the run record); proposed slot = the next overnight/unattended stretch, keeping operator-present windows for E5 W0/W1. RP-3 (boxed-prompt trigger) analyzed post-hoc on A2 outputs. Sequencing ratified by operator 2026-07-23: E5 W0/W1 hold the operator-present windows; A2/RP-5 takes unattended time.

**Run protocol actually used (GPU arms, 2026-07-20)** — kernel `production-consolidated-v7` (`build-hip`, 10098/`6ad45fa3f`), MI210, one arm at a time, `--device ROCm0 -ngl all -fa on -ctk f16 -ctv f16 -c 32768 -b/-ub 2048`, server `--reasoning off` + request `enable_thinking=false`, production sampling **temp 0.6 / top_p 0.95 / top_k 20 / seed 42** (+1 per avg@k pass). Per-arm spec-dec set to each model's **measured** optimum (A1 `draft-mtp` n-max 2; A3/A4 n-max 4) — see the registry `optimal_gpu_serving` blocks. GPU servers pinned to cores 88–95 so the CPU inference stack is untouched.
**avg@k ordering:** repeats are the *outer* loop — each pass sweeps all questions at one seed — so an interrupted run degrades to a valid avg@(k−1) rather than a subset-biased score. Arms stopped at different k are still comparable by filtering the per-question JSONL to the seeds all arms completed.
**Throughput rows from these runs are OBSERVATION-grade** (pre-`P-GPU-1`); the accuracy verdict is device-independent and decision-eligible.

##### Result R1 — GPQA-Diamond, letter-only / no-CoT (n=198 paired, seed 42, 2026-07-20)

| Arm | accuracy | trunc | noparse | Δ vs A1 | McNemar |
|---|---:|---:|---:|---:|---|
| **A1** 122B-A10B UD-IQ2_M | **55.1%** | 0 | 0 | — | — |
| **A3** 27B dense Q8 | **55.6%** | 4 | 2 | **+0.5pp** | b=35 c=36 **p=1.00** |
| **A4** 35B-A3B Q8 | **53.0%** | 16 | 3 | **−2.0pp** | b=33 c=29 **p=0.70** |

**Finding: no arm separates from any other on no-CoT GPQA-Diamond.** All pairwise p ≥ 0.63. Under a letter-only prompt the models emit ~2 tokens and cannot reason, so this suite reads *knowledge/priors*, not reasoning depth — and on knowledge the three are equivalent. **This does NOT support H3** (35B-A3B was expected to trail): the shallow 3B-active reasoner ties the 122B when neither may reason. Consistent with the AXA-1 Δ0.0pp result being knowledge-parity, and with the thesis that architect separation must come from the CoT/AIME suites.

> ⚠ **These numbers are POST-correction. The pre-correction run said something different and wrong.**
> The first scoring pass reported A1 55.1% / A3 51.0% / A4 43.4%, i.e. **A1 −A4 = +11.6pp at McNemar p=0.0059 ("significant")**. That entire result was an **answer-extraction artifact**: the extractor only accepted a bare letter when it was the *whole* response, so a reply ending "…reasoning…\n\n**B**" failed to parse and scored wrong. Parse failures were **0 / 13 / 29** across A1 / A3 / A4 — i.e. the bug penalised exactly the arms that show their work, manufacturing an 11.6pp gap and pointing at the wrong architect. Fixed (bare-letter-final-line rule, last-match-wins, delimiter-required `ANSWER` tag); the fix also removed *false positives* (a reply ending "Option D matches this structure.\n\nD" had been scored `C`). **Re-scored offline from stored responses — zero GPU re-run.** Tooling: `architect_bench_rescore.py`, `architect_bench_analyze.py` (which now always prefers `per_question.rescored.jsonl` so arms are never compared under different scorer versions).
> **Rule going forward: report a per-arm parse-failure rate next to every accuracy number; any cross-arm difference is a scoring bug until proven otherwise.**

##### R2 (in flight) — reasoning budget dominates, and the stack-wide `enable_thinking=false` default is now in question

**Why this was opened (operator, 2026-07-20):** published GPQA-Diamond for these exact models is far above R1 — Qwen3.6-27B **87.8%**, Qwen3.6-35B-A3B **86.0%** (vendor-reported) vs our 55.6% / 53.0%. The gap is **the measurement condition, not a broken harness**: R1 forced letter-only + `enable_thinking=false`, so the models emitted ~2 tokens. Same arm, same questions, same harness, CoT allowed → **A1 went 55.1% → 83.3%** (early n). Published figures are thinking/CoT numbers and are **not comparable** to a no-CoT probe.

**The deeper problem.** The stack-wide default (`chat_template_kwargs.enable_thinking: false` on `architect_general`, `frontdoor`, `coder_escalation`, …) traces to the 2026-05-20 probe recorded in `feedback_qwen3x_enable_thinking_false` (+33pp for frontdoor). But that probe's *failure mode* was thinking-ON runs hitting `finish_reason=length` with **`content=""`** — the model never emitted an answer inside the budget. **That is a token-budget artifact, the same class as the truncation/parse bugs corrected above** — not necessarily a quality property of thinking mode. The memory itself already flags this confound for the `ingest` row ("most likely max_tokens truncation of native reasoning, not a thinking ablation"); the same doubt applies to the Qwen3.6 rows.

**R2 ablation design** — thinking ON vs OFF, *identical* pinned `gpqa_diamond_cot` items (n=50), **max_tokens 16384** so thinking cannot be starved (the whole point), production sampling, per-arm optimum spec-dec:
- **A4 = Qwen3.6-35B-A3B** — the exact model the +33pp claim was made about, and the production **frontdoor**.
- **A1 = Qwen3.5-122B-A10B IQ2** — the **architect** candidate (and the reviewer-arm model).
- Server: `--reasoning on --reasoning-budget -1 --reasoning-format deepseek` (thoughts → `reasoning_content`, so `content` is scored cleanly) vs `--reasoning off`. Note `-rea/--reasoning [on|off|auto]` is a real flag — the runs above genuinely disabled thinking, they did not merely hide it.
- Metrics: accuracy, **empty-content-with-reasoning rate** (the documented degenerate-loop signature), truncation, and **median completion tokens** — because the deploy decision is quality *per latency*, not quality alone.

**Scope note:** a positive result changes production config for architect/reviewer/frontdoor roles, which is **operator-gated** and must weigh the latency/throughput cost (thinking multiplies output tokens; frontdoor is latency-sensitive). This bench only *measures*; it does not change the stack.

###### R2a — **allowing CoT in the response is worth +32pp**, and it validates the harness against published numbers

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

###### R2b — thinking mode on the **frontdoor** is a *termination* failure; the stack default is VINDICATED

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

**Actionable lever (untested):** llama-server exposes `--reasoning-budget N` (>0) plus `--reasoning-budget-message`, which force-closes the think block so the model *must* emit an answer. That converts the 48% total losses into (short-thought) answers and is the obvious next experiment — it belongs to [`reasoning-effort-levels.md`](context-and-token-economy.md#track-reasoning-effort-levels) E-6.

**Do not generalize this to the architect yet** — A1 (122B-A10B IQ2) is a different model and is measuring now. "Frontdoor should not think" ≠ "architect should not think".

###### R2c — with CoT allowed, A1 leads A4 by 6pp but **it is NOT statistically supported**, and GPQA-Diamond looks saturated

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

###### R3 — AIME'25 avg@4 (the decisive, non-saturated discriminator) — IN PROGRESS

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

###### R2d — **native `<think>` hurts BOTH models. `enable_thinking=false` is vindicated stack-wide.** ✅ complete

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

So when thinking terminates it is roughly **quality-neutral** on this suite (both n.s., opposite signs); the entire measured loss is the non-termination tail. The **severity is strongly per-model** (18% vs 50%), which is direct evidence for the per-model calibration invariant in [`reasoning-effort-levels.md`](context-and-token-economy.md#track-reasoning-effort-levels).

**This does NOT close the "our models should reason" question — it re-points it.** The +32pp win (R2a) came from **CoT in `content` via the prompt**, which is *already* how these arms run and is a different axis from `enable_thinking`. The native `<think>` channel, as configured today, is a liability for both models. The open lever is `--reasoning-budget N` (>0) + `--reasoning-budget-message`, which force-closes the think block so the model must answer — untested, and the single highest-value follow-up (E-6).

**Operator decision surface (measurement only — no stack change made):** keep `enable_thinking=false` everywhere (now evidence-backed at an adequate budget), and pursue reasoning quality through **prompt-level effort** rather than the native channel.
##### Follow-up tooling / deferred (derived this session)
- [x] **Build the interleaved-per-question sequential runner** with always-valid / e-process stopping (§8 of the runbook). ✅ 2026-07-29 — `epyc-inference-research` commit `b55b4c43` adds `scripts/benchmark/architect_sequential_runner.py` plus four focused tests. It requires a pinned manifest and a numeric a-priori difficulty key, executes exactly two named arms per question, persists each completed pair atomically, reuses the orchestrator's authoritative e-process primitive, and refuses to update either process on transport failure. The runner provides a dry-run mode and makes no inference unless invoked without it. Focused suite: `4 passed, 1 subtests passed`.
- [x] **Promote the GPU driver scripts into the repo** (`gpu_lib.sh`, `run_arm.sh`, `run_budget.sh` — currently session scratchpad) so the runbook's launch pattern is executable, not just documented. (Runbook §10 records this deferral.) ✅ 2026-07-29 — `auditor`, epyc-inference-research `7fea61f9`, as `scripts/benchmark/architect_bench_gpu_{lib,arm,budget}.sh`.
  **They could not be promoted verbatim — three defects, none cosmetic:**
  1. **Both runners sourced ANOTHER SESSION'S `/tmp` scratchpad** (`/tmp/claude-1000/-workspace/355c9594-…/scratchpad/gpu_lib.sh`). Promoted as-is they are dead on arrival — the exact failure this row exists to prevent. Now sourced repo-relative via `${BASH_SOURCE[0]}`.
  2. **`--kernel production-consolidated-v7` on a v8 binary = false provenance.** Verified against the binary the scripts actually launch, not against the docs: `llama-server --version` reports **`10107 (67a433bf4)`**, exactly the v8 freeze. `v7_quality_gate_runner.py --kernel` is free-text metadata with an unvalidated `v7-candidate` default, so nothing downstream could have caught the wrong stamp. `KERNEL_LABEL` is now **required**, and unset is a refusal (exit 3) *before* anything launches.
  3. **The two surviving copies of `gpu_lib.sh` disagreed on the core pinning** — scratchpad `CORES=88-95` vs `artifacts/np_context_study_20260723/driver/` `184-191` (2026-07-24). 88-95 is the **superseded** value; taking the obvious source would have enshrined a known-wrong host-thread pinning as the repo's canonical driver. Promoted copy takes 184-191 and records why.
  *No GPU work was run: the guard was tested in isolation and all three are `bash -n` clean.*
- [x] **Declined: AIME'25 hard-tier avg@16 top-up.** Considered; explicitly *not* pursued — it sharpens ~7 problems where A1=A3 already tie (likely a tighter confirmation of parity), whereas OlympiadBench adds harder *items* with real n. Higher expected information → chose OlympiadBench. ✅ 2026-07-21
- [x] ~~Resolve the decision tree from Phase 1; **(conditional) build + run A5** if branch 2 fires.~~ (closed 2026-10-29 audit: SUPERSEDED → decision recorded and deployed 2026-07-31 (box L377-380 [x] "Record the architect decision"); A5 conditional never fired (A3 leads, status header L5))
- [x] **Phase 2 — tool-use eval RUN across the whole fleet** ✅ 2026-08-02. `tool_compliance`
      (9 questions, 0-3 rubric) scored by architect_critic under one judge, one 8192 budget, all six
      models, zero ineligible: architect_critic 85.2%, frontdoor 77.8%, worker_general 77.8%,
      architect_general 74.1%, worker_vision 74.1%, ingest_long_context 70.4%. **14.8 pp spread** —
      the only axis we own that discriminates. Evidence:
      `epyc-inference-research/data/judge_suite_headtohead_20260802/`. NOTE this is the fleet-wide
      tool-use screen, NOT the "tool-using planning on the surviving arms" depth probe, which is
      still unrun.
- [ ] **Phase 2 depth probe** — tool-using *planning* (multi-step, stateful) on Qwen3.8-27B (architect_critic) and Qwen3.8-Flash-Next (architect_general).
      The 9-question compliance screen above is a breadth instrument and does not answer it. (re-scoped 2026-11-03 from surviving arms Qwen3.6-27B (A3) / 122B: deleted; now Qwen3.8-27B (architect_critic) and Qwen3.8-Flash-Next (architect_general))
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

- **[declined: ws58 2026-11-03 content-review: an external finding, not a task]** **CAL-1 — external calibration input: static code benchmarks barely rank-correlate with
  in-the-wild preference** (intake-1156, Copilot Arena, arXiv:2502.09328, dive-verified 2026-08-18).
  Spearman rank correlation against real IDE developer preference: **0.62** (Chatbot Arena coding),
  **0.48** (Chatbot Arena general), **≤0.1 with most static benchmarks** — over 4.5M suggestions,
  11,604 votes, 1,642 users, 10 models. Directly relevant here because this handoff ranks arms on
  static suites. **Carry the counter-reading with the number, always:** low correlation is equally
  consistent with preference tracking latency, style and verbosity rather than with static suites
  being wrong, and the paper's own reference list cites the RLHF length-correlation result.
  **Explicitly NOT a licence to distrust our suites** — ours gate correctness and throughput, which
  this paper measures neither of. The task is to record the prior in this handoff's methodology
  notes; **it changes no gate and no arm ranking.**

#### R4 — OlympiadBench-numeric SATURATES too (adapter design flaw, not the ceiling-breaker claimed)
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

##### ⇒ Bench verdict (reasoning suites, GPU arms): NULL across the board
Six independent paired measurements — letter-GPQA (n=198), CoT-GPQA (n=50), AIME'25 avg@4 (n=30),
OlympiadBench-numeric (n=150), plus AXA-1 Δ0.0pp and the thinking ablations — **all show no separation**
between A1 (122B-IQ2), A3 (27B-dense), A4 (35B-A3B). **H2 = near-parity, H3 = fails** (the 3B-active model
never trails). At the difficulty these suites reach, **the architect choice has no accuracy basis** →
decision falls to **deployment-robustness** (dual-resident 122B cheaper to operate at equal quality; GPU-only
27B has no CPU self-fallback + pins the GPU slot). **Two things could still break the tie and are the only
open quality questions:** (1) a *genuinely* harder discriminator (filed symbolic-scorer fix) or **Phase 2
tool-use** (the architect's real job); (2) **H1** — IQ2-vs-Q4, which needs the **A2 CPU arm** (later session).
Until then, no deployment change is warranted on accuracy grounds.

#### R6 — `olympiadbench_hard` FINAL (n=155 paired, np=1+MTP, fixed-extractor rescored): NULL, well-powered
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

##### 122B-A10B termination defect — MODEL-specific, NOT quant-specific (the real caveat on the 122B architect) → see [reasoning-effort-levels.md § MODEL-specific repetition-penalty fence](context-and-token-economy.md#track-reasoning-effort-levels)
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

#### R5 — `olympiadbench_hard` DISCRIMINATES (finally a non-saturated suite) — but is budget-gated
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
in [`reasoning-effort-levels.md § Token-budget study`](context-and-token-economy.md#track-reasoning-effort-levels) (operator-flagged).

#### Dependency graph
`Prep (AIME adapter)` ∥ `Gate1 v7-promotion` → `Gate2 inference-batch-loop` → `Gate3 operator quiet window`
→ `Phase 1 (A1–A4)` → {decision | conditional A5} → `Phase 2` → `record decision`.
Prep is independent of the gates; the inference is not.

#### Cross-cutting concerns
- **This is the reasoning re-gate that AXA-1 deferred** (LLM-rubric gate). A pass here *upgrades* AXA-1's
  IQ2 residency from knowledge-parity to reasoning-certified; a fail *changes the GPU-slot plan*.
- **No stack/production change** is made by this bench — it is measurement only. The architect deployment
  change (if any) is a *separate* operator-gated action informed by the result.
- **Instrument discipline:** pre-`P-GPU-1`-cert GPU numbers are OBSERVATIONS. The *quality* verdict
  (accuracy, device-independent) is decision-grade; the *throughput* rows are not until post-promotion.

#### Reporting instructions
Per arm×suite: write the paired result (n, pass count, Δ vs A2, McNemar p) with a MEASUREMENT stamp.
At Phase 1 completion: flip the Phase-1 checkbox, record which decision-tree branch fired, and update
this Status line. On a final architect decision: flip the record checkbox here, append the verdict to
AXA-1, and open a registry-change note (do NOT edit the live registry — that's operator-gated).

#### Key file locations
- Eval runner (reuse + extend): `epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py` (`gpqa`,`mmlu_pro` adapters; add `aime`).
- Arm GGUFs: `/mnt/raid0/llm/models/` (paths in the Arms table).
- Phase-2 dataset: `/mnt/raid0/llm/datasets/swe-bench-verified/` (FAIL_TO_PASS oracle).
- Evidence: `docs/reference/architect-model-selection-2026-07-20.md`.
- Related handoffs: [`mi210-big-model-and-acceleration-roadmap.md`](../completed/mi210-serving-program.md#track-mi210-big-model-and-acceleration-roadmap) (AXA-1),
  [`reviewer-model-ablations.md`](reviewer-control-plane.md#track-reviewer-model-ablations) (H5, model-role selection sibling),
  [`v7-promotion.md`](../completed/v7-promotion.md) (gate 1), [`inference-batch-loop.md`](eval-tower-program.md#track-inference-batch-loop) (gate 2).

#### Intake (research provenance — persisted 2026-07-20)
6 papers deep-dived read-only; see `research/intake_index.yaml`: net-new `2508.18672`, `2505.11574`,
`2505.02390` (highest-priority — exact toolchain), `2604.07035`; promoted-from-reference `2504.04823`;
already-integrated `2505.09388` (intake-074).


#### Laguna S 2.1 intake integration — 2026-07-22 → **UNBLOCKED 2026-07-26 by the v8 freeze**
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
- **[declined: operator 2026-11-03 model-audit: Laguna-S-2.1 weights deleted 2026-07-28; trigger (CPU-resident Laguna role) cannot occur]** **L-Q4P conditional CPU performance discovery.** The bounded four-cell config selector and broader CPU sweep remain deferred. Trigger only if a concrete CPU-resident Laguna role proposal needs a measured throughput/cost surface; the saved run's median `8.14 tok/s` is observation-only and authorizes no lineup or registry action.
- [x] **A3-vs-A4 SWE-oracle powered confirmation — SHELVED** ✅ 2026-07-27 — A3 leads the final four-arm v4 table outright, so the precommitted stopping rule shelves the powered-160 confirmation. Reopen only if a corrected table reorders an outcome that changes an actual deployment decision; no model inference was launched for this shelved task. Evidence/workflow retained: `/mnt/raid0/llm/epyc-inference-research/artifacts/architect-laguna-iq2-v8-20260726/a3-a4-swe-confirmation/`.


#### 2026-07-25 — intake Stage-2a dive: ThinkingCap arm, corrected

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](../completed/frontier-lab-automation.md)._

- [x] **A3-tc sealed first-read — ThinkingCap-Qwen3.6-27B, legacy thinking-enabled diagnostic/confounded** ✅ 2026-07-27 — the complete v8 banked capture was deterministically replayed through the frozen v4 converter and official FAIL_TO_PASS evaluator: `18/40` (`45.0%`), `16` explicit empty-patch failures, zero harness errors. Subsequent argv audit proved this arm used `--enable-thinking` while FF/stock used no-think; `15/16` empties are reasoning-channel cap truncations. It remains evidence only of that asymmetric thinking-mode configuration and is not comparative authority; the corrected no-think row is recorded at FG-3. The rb512/rb1024 calibrations remain a separate budgeted-thinking axis, not substitutes for the clean arm.
- [x] **ThinkingCap comparison disposition and dive corrections integrated.** ✅ 2026-07-27 — MTP is held separate; the vendor table is under-powered and mostly negative out-of-domain; ThinkingCap is a weights-frozen finetune rather than a reasoning-budget dial; the capped `53/53` LCB pass remains diagnostic-only. No regeneration was used after the scorer-path review.
- [x] **A3-tc exact-GGUF license gate — WAIVED by operator** ✅ 2026-07-27 — operator decision: "provenance is irrelevant. Just performance." License/provenance review is removed as a candidacy blocker; the provenance evidence file remains on record (`epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/thinkingcap_license_provenance_20260727.json`) but gates nothing. Candidacy is performance-only from here.
- [x] **A3-tc FG-1 token-efficiency read (performance leg).** ✅ 2026-07-29 — deterministic replay of sealed SWE40 outputs is byte-reproducible (`fg1_results.json` SHA-256 `7776c106…bcfb`; `FG1_SUMMARY.md` SHA-256 `01b32136…cea1`): A3-tc used 5,021.1 completion tokens/official solve versus A3 1,506.5, but its thinking-enabled configuration is cap-truncation-confounded (15/16 empty patches hit the 3,072-token cap), so it cannot rank token efficiency. The effort-invariant candidacy question remains: every finite LCB calibration budget capped, so no equal-effort read exists yet; an equal-effort LCB re-run with wider budgets is warranted only if a future clean FG-1 read leaves the thesis alive.

#### 27B finetune candidates — downloads + bench (operator-sequenced 2026-07-26, GPU lane after MiniCPM-o)

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
- [x] **A3-ff behavioral/abliteration candidacy gate.** No ratified direct-generation refusal/behavior screen exists in the repository; the existing RewardBench reviewer protocol is not applicable. The first-read remains valid, but no role candidacy or lineup action is authorized unless the operator chooses to design and ratify a new screen. Note (2026-07-27): the operator frames FF as a **pre-processing/scaffold tool, not a wholesale role substitute** — its candidacy test moves to the reopened scaffold-generator A/B ([gpu-cot-scaffold-sidecar.md](gpu-cot-scaffold-sidecar.md)); this gate applies only if FF is ever proposed for a direct serving role.
  - 2026-11-02 operator decision: No screen; FF stays a scaffold tool (decisions-batch2-4-20261102.json) [declined: operator 2026-11-03 model-audit: operator 2026-11-02: no screen, FF stays a scaffold tool; Fable-Fusion-711 weights deleted 2026-10-20]

#### 2026-07-27 fine-grain + remediation program (operator-directed discussion outcome)

_All six authority rows are in; the operator's read: overall scores hide the structure. Disjointness of solve-sets matters more than totals; both "failure" signatures (Laguna LCB truncations, TC empty patches) may be deterministically patchable like the 122B loop fix; the Laguna speed comparison used a stale registry anchor. FG-1 is pure replay over sealed artifacts (zero inference); FG-2/3 designs are zero-inference, their validation runs queue behind the campaign._

- [x] **FG-1 — fine-grain replay (zero inference)** ✅ 2026-07-27 — executed same-session over the sealed artifacts; evidence `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg1-fine-grain-replay-20260727/` (`FG1_SUMMARY.md` + `fg1_results.json`). Headlines: (a) **Laguna SWE-route specialist DEAD** — its 17 solves are a strict subset of A3∪A4 (unique=0), A3 dominates +6/−0 exact p=.031 (only significant pair); (b) **TC empties are cap truncations during thinking-mode generation** — 15/16 hit the 3072 cap, including 12 zero-response and 3 partial-response rows; the remaining row is `skipped_missing_path`. TC as-configured is 3.3× more expensive per solve (5,021 vs A3 1,506 tokens/solved), but the asymmetric thinking configuration is confounded and cannot support a comparative token-efficiency conclusion; (c) **FF is the actual token-efficiency winner** — −40% median completion tokens vs stock (237 vs 397), tokens/solved 1,083 vs A3 1,507, quality statistically tied (p=.29); (d) FF-MTP leaner still (median 233) but LCB-weak. Bonus: 14/40 instances unsolved by all six = the discriminating hard-core set for future focused benches; A3 keeps 3 unique solves. Evidence hygiene repair accepted and pushed: research `325f7c2e` (sealed-input provenance, taxonomy, exact values) and root `82215b81` (handoff taxonomy).
- [x] **FG-2 — Laguna LCB truncation classification + remediation design** ✅ 2026-07-27 — zero-inference replay classified all `8/8` cap truncations exhaustively and disjointly: five format spirals, two genuine long derivations, and one literal repetition loop. Each item is bound to its sealed response SHA and bounded tail evidence. The remedy must remain class-specific: answer-contract prompt for the five format spirals, cap-only ablation for the two genuine-long rows, and loop-control sampler for the literal loop. Evidence: `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg2-fg3-sealed-classification-20260727/` (JSON SHA-256 `f862e27bcd7582c91f1e785f844e99bd0254561d3d5ddca1eccab1ec56bd0f0a`). FG-1 prior still shows Laguna also truncated 9/40 SWE rows (11 empties), but FG-1(a)+FG-4 killed the SWE-route case; any remaining payoff is non-coding candidacy (FG-5).
- [x] **FG-2V — focused post-campaign validation** ✅ 2026-07-28 — terminal over exactly the eight preclassified rows, fixed seed, no request/harness errors. Loop control changed `lcb_abc320_e` from a 4096-token length stop to a normal 1723-token stop but it remained wrong. The answer contract made four of five format rows stop normally and produced `2/5` correct, but only `lcb_abc323_e` was a new solve (`lcb_abc331_e` was already correct); `lcb_abc341_f` still capped. Larger-cap generation added no solve: `lcb_abc318_e` stayed correct and capped at the 8192 context boundary, while `lcb_abc314_f` stayed wrong at the effective 6726-token context ceiling and again at a corrected full 8192-token cap under `-c 16384`. Net focused delta is `+1/8` solve, which would move the banked Laguna LCB total only `14/53 → 15/53`; this does not reopen the coder-role case. Evidence: `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg2v-laguna-focused-20260728/fg2v-20260728T133936Z/` plus the live-defect repair `fg2v-long-context-repair-20260728T135141Z/`. No full-suite regeneration or role/lineup action is authorized.
- [x] **FG-3 — TC no-think validation and deterministic replay terminal** ✅ 2026-07-28 — argv audit confirmed the legacy six-arm TC row was not apples-to-apples: it used `--enable-thinking` while FF/stock used `--no-enable-thinking`; the `15` thinking-mode cap truncations and 5,021 tokens/solved therefore remain diagnostic only. The corrected same-era no-think capture was sealed and deterministically replayed through the frozen v4 converter: official SWE is `21/40` (`52.5%`), `0` harness errors, `3` empty-patch failures, and `2` model length-cap failures; LCB is `24/53` (`45.28%`), `0` request errors, and `3` model length caps. Capture/argv hashes and finalization seal verify at `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg3-tc-nothink-v4-tail-replay-20260728/`. This corrected no-think row replaces the legacy thinking-enabled row for the FG-3 comparison; it does not authorize a role, lineup, registry, or production action. Codex's rb512/rb1024 budgeted-thinking calibrations remain a separate axis.
- [x] **FG-4 — A4 speed re-anchor** ✅ 2026-07-27 — operator was right: the 24.3 tok/s registry row dates to 2026-05-04 (pre-v6/v8 kernels, MTP-blind). Same sealed capture window (`decode_tok_s` telemetry, n=40/arm): **A4 median 94.5 tok/s** (p10 81.8 / p90 114.8) vs Laguna 44.6, A3 52.7, A1 55.2. **The Laguna speed argument inverts** — Laguna is ~2× slower than the incumbent it was claimed to beat; combined with FG-1(a), no SWE-route case survives. Observation-grade (capture telemetry, not canonical recipe) — sufficient to kill the stale-anchor comparison, not to update the registry row.
- [x] **FG-4b — canonical A4 optimized-serving re-anchor** ✅ 2026-07-29 — decision-grade `FG-4b/A4-CPU-optimized-server-v1` completed at `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg4b-a4-cpu-optimized-server-20260729T110152Z/`: median `13.159866755320987 tok/s`, MAD `0.0163318316089196`, five exact 512-token `np=1` server completions, all `finish_reason=length`, after the ratified stability warmup. `protocol_status=ratified_receipt_validated`, `decision_grade=true`, `proposal_only=true`; teardown is `ps_verified_dead=true`. The affinity-witness receipt is `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T105911Z.json` (SHA-256 `b4ee39b8e10dc771e305070f84a3b0e93a5b4207bbdb0cdab57b36023c4c0385`). The generated registry patch remains review-required/proposal-only and was **not applied**; no measured row was hand-edited. The post-run production restoration used `--skip-stack-change-gate --no-compile-registry` only because the normal canonical-stack gate encountered pre-existing stale hashes, and only to restore the already-running 24 endpoints exactly; it is a restoration-only exception, not a benchmark or registry-apply authorization.
- [x] **FG-5 — CLOSED by weights deletion** ✅ 2026-07-28 — the operator deprecated Laguna and its weights were deleted (108G freed; `gpu-serving-tie-in-program.md` D7). The non-coding-strengths question remains UNANSWERED (this close is administrative, not a falsification); reopening requires an operator decision + re-download + an operator-selected non-coding suite/protocol. Original scope marker preserved: SWE/LCB cannot falsify the GLM-5.2-competitor claim for long-context/agentic/general workloads; the L-Q4 quant-axis screen completed without resolving a difference.
- **[declined: operator 2026-11-03 model-audit: Fable-Fusion-711 and ThinkingCap-Qwen3.6-27B deleted 2026-10-20; conditional trigger dead]** **FG-6 — BCB-hard pre-deployment regression screen (CONDITIONAL — do not run now; operator decision 2026-07-27).** BCB-hard is explicitly NOT run on the finetunes as a ranking instrument: it proved non-discriminating on this family (coding-ladder pooled tie n=347) and is the wrong distribution for both theses (library-API recall, where the scaffold lane showed distilled-reasoning transplants no-op). **Trigger**: fires only if FF or TC advances to actual role candidacy (cheaper-A3 substitute, post-scaffold-A/B promotion, or TC re-ranked into contention by the FG-3 no-think arm). **Purpose at trigger**: production-representative regression screen — real coder-role traffic is library-API-shaped, so the gate is "does not regress vs stock on BCB-hard," not a ranking read. One arm per advancing candidate, no-think protocol, same-era.

#### 2026-07-29 — intake Stage-2 dive: Qwopus3.6-27B-Coder arm + zero-inference weight-delta geometry

_Via `/research-intake` Stage-2 2026-07-29 (intake-913…932 batch); the bench arm is operator-requested. Neither item is comparative authority until it runs under the sealed same-era protocol above._

- [x] ~~**Collect and bench Jackrong/Qwopus3.6-27B-Coder MTP-Q8_0** (29.0 GB, apache-2.0, 63k downloads). It carries the lineage's ONLY full-denominator SWE-bench Verified run — 335/500 = 67.0% measured **thinking-off**, matching our stack — at ThinkingCap-class onboarding cost with zero merge work. **CAVEAT THAT MUST TRAVEL WITH THIS NUMBER WHEREVER IT IS QUOTED: 67.0% is SWE-bench Verified, vendor self-reported, n=1, full-500 denominator, and is NOT commensurable with our sealed SWE-oracle-40 (A3 `23/40`).** Different instrument, different denominator, different scaffold — it may not be set beside any authority row in this handoff. Preconditions: (a) **verify the JSON tool-call parser first** — this family emits JSON inside `<tool_call>`, NOT Qwen's XML `<function=…><parameter=…>` form, and the chat template differs between v2 (6,994 B) and Coder (4,718 B), so verify **per model, not per family** (a cross-arm parse-failure gap reads as a quality gap — see R1's parse-artifact rule above; tracked as 2b-agentic-1 in [`scoring-infra-standardization.md`](eval-tower-program.md#track-scoring-infra-standardization)); (b) hold MTP constant across arms.~~ CANCELLED 2026-10-27, operator: Qwopus not used (do not download).
- [x] **Zero-inference weight-delta geometry probe.** Stream the local Q8 GGUFs (stock Qwen3.6-27B / ThinkingCap / Fable-Fusion / MTP control), dequantize per tensor, and per layer L compute r(L)=‖Δ_FF‖/‖Δ_TC‖, c(L)=cos(Δ_TC,Δ_FF), p(L)=⟨Δ_FF,Δ_TC⟩/‖Δ_TC‖² against the shared base. **Free exact ground truth:** our own spec-dec work established at byte level that ThinkingCap = stock + exactly 256 LoRA modules (r=64, α=128), so Δ_TC is EXACTLY ZERO on ~600 non-LoRA tensors — those measure nothing but the Q8 dequant noise floor, the quantity that decides whether GGUF delta-geometry is trustworthy at all. Second payoff: TC and FF are independent siblings off stock, so the lineage detector p(L) should sit near 0 and flat; if it drifts to 1.0 anyway, the "Coder descends from V2" inference is an artifact. Minutes of CPU, no GPU lane, no download. ✅ 2026-08-12 (`auditor`) — EXECUTED, both gates PASS, auditor-verified (counts recomputed from raw JSONL). **Gate (a) decisive**: exactly 256 tensors carry real deltas (the LoRA set, no threshold-tuning), 140/145 comparable non-LoRA tensors bit-identical, remainder ≤2.7e-9 RMS/elem → ~3,150× signal/noise separation; **GGUF delta-geometry is trustworthy at Q8**. **Gate (b)**: cos(L) ≤0.011 and flat — TC⊥FF confirmed; **p(L)≈0.45 is a detector artifact** (p=cos·r with r=43–145×), so cos(L) is the lineage discriminator, never standalone p(L). **Provenance finding**: TC's 15 extra `blk.64.*` tensors are name-identical to the MTP checkpoint's — TC was converted from the MTP lineage, not plain stock; FF matches stock exactly; `output.weight` is BF16 in FF (excluded, named). Two instrument defects fixed (silent-drop exclusions → four named buckets; (N,1,1) broadcasting bug that attempted a 112 TiB alloc — synthetic tests' single-block chunks hid it), +3 regression tests (6/6). Evidence: research `artifacts/weight-delta-geometry-20260812/` (REPORT.md, result.json, 401-row tensors.jsonl). Research-side landed `f640286a` (cherry-pick freeze cleared 2026-08-12 ~12:50Z; edits patch-id-verified byte-identical to the parked copies before commit).
  - [x] **E5-safe instrument and input preflight** ✅ 2026-07-29 — committed `epyc-inference-research` `4c1a3ac3` (`scripts/benchmark/weight_delta_geometry.py` plus three synthetic tests). The instrument streams Q8_0 blocks only after explicit `--execute`; default `--plan` touches no model payload and production execution remains deferred while E5 Stage-B exclusively owns CPU. Verified local stock/ThinkingCap/Fable Q8 inputs exist; no inference, GPU work, or real-model dequantization occurred.

#### 2026-08-03 — intake Stage-2/2b: the code-runtime-efficiency axis, and two model-candidate verdicts

_Via `/research-intake` on intake-938…990. The compendium had **deep coverage of speedup-rewarded GPU
kernel generation and zero coverage of code-runtime efficiency as an evaluation axis** — six instruments
are now indexed. Nothing below is comparative authority until it runs under the sealed same-era protocol
above._

##### Instrument design and evidence independence

The earlier statement that Mercury, EffiBench / EffiBench-X, and SWE-Perf formed a connected lineage
through a shared author is retained only as historical discussion, not as a verified current-source
finding. The review did not audit the other papers' author lists; intake-972's source record is the
appropriate citation for that scope note (`intake-972#record`). The instruments have distinct designs:
ENAMEL normalizes against **one expert solution with censoring**; EvalPerf against a **clustered ladder
using instruction counts**; GSO against **a single human commit in the same container**; COFFE against
**the best ground truth, binary**.

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

##### Instrument selection

- **[declined: ws58 2026-11-03 content-review: merged as the second efficiency instrument, adopted only if EvalPerf discriminates]** **Adopt EffiBench-X as the efficiency instrument, Python-only, restricted to the 308 DATED problems.** Apache-2.0, and its local-endpoint support **works unpatched** (`OpenAI()` with no args after `load_dotenv()`). Three blockers must be patched onto **upstream**, not taken from the `effibench-enhanced` re-upload (intake-986, zero lineage, created-and-pushed six minutes apart): the deprecated `openjdk:21` image, a `time.sleep` `AttributeError`, and a **fail-open-to-0.0 metric**
  - *(2026-11-02, reproducible preparation.)* Reconstructed pristine upstream `EffiBench/EffiBench-X` at `21b6668a49a342c843e679cc5ed16081064a5768` in `/mnt/raid0/llm/tmp/architect-effibench-upstream-20261102` and applied the four ordered patches from research `artifacts/effibench-x-acceptance-gate-20260812/patches/`; `git diff --check` and Python compilation of all six changed files pass. Combined `git diff` SHA-256 `b87733644b59545737a3a50ce0a5350265a0b80680fd21cb8a09ee6fce6c6534`. This is scratch preparation, not a new canonical acceptance run or a model-arm score. Adoption remains open until durable integration of the patched instrument, DATED selection and the two exclusions. [no-belief: instrument preparation]

- [x] **Run a canonical-solutions acceptance gate FIRST, before any model arm.** The fail-open-to-0.0 path is our own named defect class sitting on the exact metric we would adopt, and it is unfixed in both upstream and the re-upload. If canonical solutions do not score as canonical, the instrument is not measuring what its name says ✅ 2026-08-12 (`auditor`) — **GATE PASSED: FIT to score model arms**, Python-only, DATED-308, auditor-verified (zero fail-open recounted across all 61,600 test executions). 306/308 problems pass under the harness's own any-canonical rule; **carry two exclusions into every model arm**: `leetcode_3264` (runner emits no output) and `leetcode_3451` (debug prints in canonical). **FOUR patches now required on upstream `21b6668`, not three** — the runtime pass found **04: `is_passed` counts done/empty-output/exit-0 as a pass over the evaluator's failure verdict** (proven live: evaluator 0/100 yet `is_passed()` True — a correctness-inflation channel that would flatter every model arm), alongside 01 openjdk→temurin (NOT moot under Python-only: `setup()` iterates all six languages), 02 `import time`, 03 fail-open-to-0.0→fail-closed (fired live twice during the gate — upstream issue #4's ~1/30k trigger; pre-patch those were silent 0.0 canonical denominators that zero every model arm on the problem). Mutation-tested 6-fail→8-pass, both outputs recorded. Timing is single-execution by upstream design — acceptance-grade, not ladder-grade. Evidence + patches: research `0cf315c3` (`artifacts/effibench-x-acceptance-gate-20260812/`). Adoption (row above) stays separately gated on arXiv `2607.01211` ingest.
- **[declined: ws58 2026-11-03 content-review: a 21 GB pull for two expert-curated tasks with no decision rule]** **Pull GSO's two `abetlen/llama-cpp-python` optimization tasks (~21 GB) and run them against the coder and architect roles.** MIT, expert-commit performance targets, and **the only thing in this literature that lands on our own serving stack**. Import its equivalence contract; do NOT import its timing discipline — `timeit.timeit(..., number=1)` is a single timed run per test, and its `check_equivalence` compares a reduced digest (`shape` plus `first_entries[:5]`) that an optimization wrong outside the digest passes. **CAVEAT (intake-1104#06, 2026-08-12): neither task is among GSO's 39 cross-machine replay-valid** — `218d361`'s reference patch fails to apply in a clean replay pipeline (0/12 machine-rounds) and `2bc1d97`'s base commit fails on AMD EPYC Milan 3/3 (valid 3/3 on EPYC Turin at 1.97–2.02×); locally rebuild both base commits and re-apply GSO's ≥1.2 per-test rule before trusting either reference target
- [ ] **Run EvalPerf against our local endpoint** — lowest friction in the cluster: Apache-2.0, native `--backend openai --base-url`, ~15 min/model, ~100 MB. Its measurand is retired instructions via hardware counters, max CV 0.4% across four test beds. **Valid for generated-code scoring only** — instruction counting is explicitly invalid for our bandwidth-bound inference kernels, and was falsified in-session where a tiled traversal executing +1.9% instructions ran **2.83× faster** If EvalPerf separates the coder and architect arms, add EffiBench-X (Python-only, the 308 dated problems, Apache-2.0) as the second efficiency instrument; otherwise record that code-efficiency is not a discriminating axis today.
- [x] **Add the Slow/CRR conditional diagnostic** (intake-974): among a model's **correct** outputs, what fraction is no faster than baseline. It separates correctness inflation from genuine efficiency gain, and it is the one number that makes the derived conditional column above interpretable. The analyzer's opt-in `--slow-crr-baseline ARM` reports candidate outputs with `decode_tok_s <=` matched baseline speed, ties included, only at 30+ correct outputs; missing, duplicate, or invalid matched speeds leave the diagnostic unavailable with explicit counts. The existing all-arm accuracy cohort is unchanged. Implementation: epyc-inference-research `f6ff29ae8325c4dab4f7c312af91b12141df56da`; 11 focused tests passed. The historical A1/A3 inputs remain unavailable (invalid candidate speed fields); no fraction or measurement claim is made. ✅ 2026-10-30 [no-belief: implementation/tooling; no new measurement]
- [x] **Ingest arXiv `2607.01211` BEFORE finalising the instrument choice** — it directly meta-evaluates this entire cluster and may pre-empt the decision ✅ 2026-08-12 (`auditor` lane, operator-approved intake) — ingested as **intake-1104** (dive-verified; "Are Performance-Optimization Benchmarks Reliably Measuring Coding Agents?", Chen/Sun/Shi/Lo/Jiang, SMU/SJTU — zero Du-lineage overlap). **Verdict for the adoption row: SUPPORTS-WITH-CAVEATS, no pre-emption** — the audit covers ONLY the repo-level trio (GSO/SWE-Perf/SWE-fficiency); EffiBench-X is out of its scope (intake-1104#00), so no new EffiBench-X defect beyond our gate's list. It corroborates DP-2's sentinel ban out-of-lineage (worst-10 tasks carry 58.5–82.8% of SWE-fficiency's harmonic denominator; one 0.001-floor task = 33.6% of a submission's weight — intake-1104#05) and shows replay validity is signal-magnitude-bound, not repetition-bound (SWE-Perf 11/140 valid despite its 20-rep Mann-Whitney gate — intake-1104#03). MATERIAL to the GSO row: neither llama-cpp-python task is among GSO's 39 cross-machine replay-valid (intake-1104#06). Decision note: `artifacts/audit/arxiv-2607-01211-adoption-impact-20260812.md`

##### Declines, named so they are not re-derived

- **Decline SWE-Perf as a harness.** Its code carries **no licence at all**, unanswered for nine months. Its statistical gate is kept.
- **Decline SWE-fficiency's images** — 1.03 TB. **Adopt its `cpu_assignment.py`** (196 lines, Apache-2.0), which produced correct NUMA-and-SMT-aware cpusets on our EPYC on the first run.
- **Keep the decline of the original Mercury repository under the existing license gate.** The reviewed original repository had no `LICENSE` file or licensing declaration (`intake-972#00`). The separately advertised Mercury_Eval successor declares MIT in its manifest and README but also has no license file; this is distinct repository metadata, not a legal conclusion about either project. Preserve the existing EvalPerf selection and operational decision.
- **Keep the decline of an efficiency axis over SWE40 / LCB.** intake-939's duration-spread gate remains its own result: original tests meet robust CV ≥0.3 for at most 3.8% of problems (`intake-939#04`). intake-976 provides related, separate evidence: across 1,538 tasks and 30 runs per implementation pair, 94 (6.11%) were significantly faster on original tests (`intake-976#02`). This does not measure CV/IQR or test the 0.3 threshold, and it does not prove sealed tasks cannot carry a timing signal. Its 209/308 manually sampled cases are author-labeled plausible improvements, not verified speedups (`intake-976#03`). Preserve the explicit corpus dependency: 256 of intake-976's 1,538 tasks are Mercury tasks (`intake-976#01`; intake-972 is lineage context, `intake-972#record`). Do not transfer the original Mercury repository's licensing or status to Mercury_Eval, or vice versa.
- **Keep the ~60-day PerfCodeBench decline and its reopening gate.** The paper-linked repository is public now, but public availability alone does not meet the predeclared licensed-public-release trigger. The repository has no umbrella LICENSE/COPYING or GitHub license metadata; the reviewed CUDA route is NVIDIA-toolkit oriented and no HIP/ROCm route was found. The current paper/repository versions do not substantiate the old 5.2% test-split figure. Reopen only on licensed public terms or a relevant ROCm/HIP path (`intake-975#00`, `intake-975#03`).

##### Model-candidate verdicts — answering the standing search for a faster `worker_general` / `architect_critic`

- [x] **Inkling — NO on both roles** ✅ 2026-08-03 (intake-941/942/955). Three independent reasons, any one sufficient: (a) **12B active parameters vs gemma4-26B-A4B's ~4B** on a bandwidth-bound decode path projects **2–4× slower**, which is the opposite of the requirement; (b) the upstream llama.cpp PR is **rejected in its current form and strips MTP**, and `src/llama-arch.h` in frozen v8 carries 138 `LLM_ARCH_*` entries ending at `DFLASH` with **no `LLM_ARCH_INKLING`** — so there is no serving path today; (c) for `architect_critic` it would *close* the 122B's measured GPU-resident IQ2 path (43.7 tok/s single / 148.7 aggregate @B32, PPL 5.02). No download, no bench — the verdict is decided from architecture and kernel support.
- [x] **Escha — NO to the artifact, YES to the experiment it motivates** ✅ 2026-08-03 (intake-945/946/956). The `eschamoe` 2-bit format is closed CUDA sm_80-120 with no ROCm path, so the published build is unusable here. But it points at a model worth testing on its own merits — see the task below. The third-party codebook reverse-engineering probe (intake-956) stays `stage1-unverified` and **deferred with a named trigger**: its author is blocked, 2–4 weeks.
- **[declined: operator 2026-10-31]** **Bench `Qwen3.6-35B-A3B` at `UD-IQ3_XXS` as a `worker_general` candidate.** ✅ 2026-10-31 DROPPED by operator (low priority; no adoption threshold; conflicts with the low-bit-on-key-roles rule). READY row withdrawn to `compute-flags/ready/dropped/`, model deleted; not run. [no-belief: declined] ~3B active (leaner than gemma4-26B-A4B's ~4B on the bandwidth-bound path), **already supported by the frozen kernel**, and at **13.2 GB it fits `worker_general`'s existing 16 GB budget** in `stack_templates/default.yaml` with no lineup change. **Use `UD-IQ3_XXS`, NOT the size-matched `UD-Q2_K_XL`** — `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:73-74` carries `static_assert(!iqk_typeA_supported(GGML_TYPE_Q2_K))` and the same for `Q3_K`, so a Q2_K build forfeits iqk acceleration entirely. Quant-axis detail lives in [`tq3-quantization-evaluation.md`](quantization-and-low-bit.md#track-tq3-quantization-evaluation); hold MTP constant across arms, and pair speed with a correctness check.
  - *(2026-10-30, reviewed READY preparation; full cohort unrun.)* Published `codex-ni-qwen36-iq3xxs-candidate-r1-20261030`: canonical artifact 13,211,155,424 bytes, SHA-256 `9c964e657212fea1f24905dd7b0a89b82fd807d19fab0b41da14251b07b88fbe`, acquired revision `a483e9e6cbd595906af30beda3187c2663a1118c`; source seal `fca17c93557f7c81181a447ed94624829e70369dd800a9480edf7cf83f48ebfe`. Positive native smoke completed two short records in 57.08 s; its original scores are retained as controls, not quality evidence. Post-work cutoff was 84.51 s, rc75, after two writer records and the next native decode marker; captured server PIDs drained. Actual keeper accepted READY-WAIT at 20:45:26Z, rank 60, with no free quarter. Full 211 cases × two arms remain unrun, using the current terse template and MTP off for both arms. No adoption, quality or speed verdict; parent stays open. Packet: `/mnt/raid0/llm/tmp/codex-ni-qwen36-iq3xxs-candidate-20261030/`. [no-belief: operational preparation and lifecycle qualification; full cohort pending]
  - **Retirement update (2026-10-30):** The operator withdrew this READY candidate. Its manifest and row now reside under `/mnt/raid0/llm/tmp/compute-flags/ready/dropped/`; the canonical model was deleted. Do not download or republish it. The 211 × 2 scientific cohort never ran, so the quality/adoption result remains unknown; the checkbox above stays unchecked. Preserve the packet as historical evidence.

#### 2026-08-12 — `worker_general` candidate RESET: LFM2.5-**1.2B-Instruct** (supersedes the 2.6B attempt)

> **START HERE.** This block was reset on 2026-08-12 after a full evaluation of `LFM2.5-2.6B`
> concluded that **we benched the wrong family member**. Read this intro before running anything.

**Operator ruling, 2026-08-12: `worker_general` should be an INSTRUCT model.** The role is the short,
high-volume, cheap path. A reasoning model is structurally wrong for it, and no amount of decode speed
fixes that.

##### Why the 2.6B attempt was abandoned — the finding that generalises

`LFM2.5-2.6B` **won every rate measurement and lost the decision anyway.**

| | LFM2.5-2.6B | incumbent gemma4-26B-A4B |
|---|---:|---:|
| CPU decode (tg512, 24t) | **72.04** | 28.00 |
| GPU decode (tg512) | **225.11** | 100.54 |
| tokens emitted, 5 terse prompts | **501** | **33** |
| time to answer, CPU | 12.89 s | **2.97 s** |

It is **2.08× faster per token and ~4.3× slower to an answer**, because it emits **15.2× more tokens**.
The incumbent runs `enable_thinking: false` in production (`stack_priors.yaml`, four roles); LFM2.5-2.6B's
template unconditionally prefills `<think>` with **no `enable_thinking` kwarg at all** — the incumbent can
be turned off, that challenger could not.

**Faster hardware does not rescue this.** The token-count ratio is invariant to hardware, so GPU *widens*
the incumbent's lead (6.8× base decode, ~9.8× crediting gemma's 1.44× MTP) because gemma's only CPU
handicap — ~0.26 s prefill per call on a 26B MoE — vanishes at 2905 t/s prefill.

**Why this is a variant problem, not a vendor problem.** Liquid AI do not document LFM2.5 as verbose —
they claim the opposite. But their own guidance recommends the **`-Instruct`** variant *"for standard
chat and creative writing, where reasoning traces might add unnecessary latency"*, which is precisely
this role. We tested the reasoning variant against a non-reasoning incumbent and measured exactly the
mismatch the vendor documents.

**Evidence for the abandoned attempt is preserved, not deleted** — `epyc-inference-research`
`benchmarks/results/scout/wg-lfm-1-20260812/` (CPU + download), `wg-lfm-1-thinking-toggle-20260812/`
(the token-count measurement). The 2.6B **weights** were retired from disk on operator instruction.

##### The candidate now under test

**`LiquidAI/LFM2.5-1.2B-Instruct`, Q4_K_M and Q8_0.** Half the parameters of the abandoned candidate, and
non-reasoning by design. Incumbent is unchanged: `worker_general` = `gemma-4-26B-A4B-it-ORIG-Q4_K_M`
(note **ORIG**, per `stack_priors.yaml`) with MTP, `reasoning: 'off'`.

##### Tasks

- [x] **WG-LFMI-1 — Prove it does not reason, BEFORE benching anything.** This is the whole premise of ✅ 2026-10-29 (audit: L695 [x] "WG-LFMI-1 gate PASSES: -Instruct variant does not reason" 2026-08-12; commit 57a251c6d) [no-belief: audit-reconciliation]
      the reset, so establish it first and cheaply: extract the GGUF-embedded chat template, check for an
      unconditional `<think>` prefill and for an `enable_thinking` kwarg, then measure **generated token
      count** on the same five prompts the 2.6B was measured on. If it emits a reasoning block anyway,
      stop and report — the reset premise is wrong and nothing downstream is worth running.
      Bar to beat: **33 tokens / 2.97 s** (production incumbent, measured 2026-08-12).

- [x] **WG-LFMI-1 — the gate PASSES: the `-Instruct` variant does not reason** ✅ 2026-08-12.
      Evidence `epyc-inference-research/benchmarks/results/scout/wg-lfmi-1-2-20260812/` (43 files,
      commit `38315212`). Template (both GGUFs byte-identical, sha256 `f05bf4b9…`): generation prompt
      is `<|im_start|>assistant\n` — **no `<think>` prefill**, and **no `enable_thinking` kwarg because
      none is needed**. The only thinking branch is `keep_past_thinking` (default false), which strips
      `</think>` from PAST turns — history hygiene, not a prefill. Render proven rather than assumed:
      llama.cpp's own minja render matches the hand render token-for-token (25 tokens).
      Token counts, five reference prompts, temp 0 / seed 42, every run stopping on **EOS** not the cap:
      **36 generated tokens** for BOTH quants (3,3,14,14,2) against the incumbent's **33** — 1.09x,
      parity, and **13.9x fewer than the abandoned 2.6B's 501**. Zero `<think>` strings in ten outputs.

- [x] **WG-LFMI-2 GPU arms** ✅ 2026-08-12, `-fa` swept rather than assumed, 3 rounds, order rotated,
      `taskset -c 184-191 -ngl 99 -r 5`:

      | quant | fa | pp512 | tg512 | peak VRAM |
      |---|--:|--:|--:|--:|
      | Q4_K_M | 1 | 15012.59 ±1578.93 | 431.18 ±7.03 | 1.389 GB |
      | Q8_0 | **1** | **19129.88 ±1085.62** | **442.07 ±7.70** | 1.905 GB |

      **Max-opt is `-fa 1` for both quants — OPPOSITE to gemma4 on the same GPU**, so the `-fa` setting
      is per-model and must never be inherited. **Q8_0 beats Q4_K_M on GPU** (+2.5% tg512, +27% pp512),
      confirming and strengthening the recorded CPU→GPU quant inversion.
      **The number that decides it**: 36 tok @ 442.07 = **81.4 ms to answer** vs the incumbent's 33 tok
      @ 100.54 = 328.2 ms → **4.0x**; crediting gemma's 1.44x MTP, 227.9 ms → **2.8x**. `llama-bench`
      cannot exercise MTP, so **2.8x is the honest column to argue against** — and unlike the 2.6B,
      **the token ratio does not eat the win**.
      Residency proven three ways (`ldd` cannot): linkage PASS with the ambient path REPLACED not
      appended; `Device 0: AMD Instinct MI210, gfx90a` and `backend = ROCm` in every row; sampled
      **while the bench PID was alive** — VRAM 1.39/1.90 GB, GPU 95-99%, `kfd_clients=1` with the KFD
      PID equal to the captured bench PID, and live `Cpus_allowed_list = 184-191`. One first-line
      sample read `0-191` — the pre-`exec` window before `taskset` applied — and was explained rather
      than dropped.

- **[declined: ws58 2026-11-03 content-review: merged into WG-LFMI-2 (its CPU arms)]** **WG-LFMI-2b — CPU arms, still owed.** Deferred because a sibling agent was saturating 176 cores
      for the OP-24 corpus migration. Cheap to add once the host is quiet.
      - *(2026-10-30, reviewed READY preparation; full CPU matrix unrun.)* Published `codex-ni-wg-lfmi-cpu2b-quiet-r1-20261030`, source seal `d070c3d49c6991cc0542b375803507232a37617dc103edaa406b324a2eac73fe`, retaining all 36 planned rows and raw `native_r5` samples. Actual keeper queued launcher 891257 at 20:43:23Z; validator 0 refusals/0 warnings and actual live quiet-class `FILLERS grant_ok` rc0, with all-CPU and exclusive-GPU admission. Native normal lifecycle 5.033 s; post-work cutoff rc75 after 8.591 s. The approved canonical validator fix is installed in the actual guard (SHA-256 `7ddfaa6b65de45a37d5f90bb9a6d186a071756977fac91d71aced55c053cd30e`); copied-guard drift was corrected. WG-LFMI-2b/2 remain open; no scientific result follows. Packet: `/mnt/raid0/llm/tmp/codex-ni-wg-lfmi-cpu2b-20261030/` (`PUBLISHED.json`, `KEEPER-ACCEPTANCE.json`, `ACTUAL-GUARD-ACCEPTANCE.json`). [no-belief: operational preparation and lifecycle qualification; full matrix pending]

      - *(2026-11-01, CPU2b result filed.)* Keeper ended `rc=0` at 18:31:10Z; `RESULT.json` in the packet above reports COMPLETE, 12/12 native legs and 36/36 rows, 643.13 s, peak sampled RSS 2,164,461,568 bytes and verified cleanup. For FA off, independent-launch mean ± sample SD (n=3, each native r5) was Q4 pp512 2398.76 ± 53.79 and tg128 166.03 ± 1.43 tok/s; Q8 pp512 2484.02 ± 82.89 and tg128 101.87 ± 0.58 tok/s. Full FA and tg512 cells and raw samples are in `RESULT.json`. This satisfies the row's baseline-characterization rule only: no certified floor, quality, regression, promotion, paired incumbent or current tokens/task claim. WG-LFMI-2b/2 stay open for their broader comparison. [belief: cc]

- **[declined: ws58 2026-11-03 content-review: merged into WG-LFMI-3 (the decision-grade quality bar)]** **QUALITY IS NOW THE OPEN QUESTION, and the current probe is the wrong instrument.**
      Correctness was **3/5** on the reference prompts: both arithmetic items wrong on BOTH quants
      (`17*23` → 4931/4935, correct 391; marbles → 360/456, correct 72). Different wrong answers per
      quant, so **capability, not a quantization artifact**.
      **But two of those five prompts are arithmetic, and a model should not be doing arithmetic** —
      operator, 2026-08-12: *"there are deterministic tools for that sort of thing."* So this is 3/3 on
      non-arithmetic and 0/2 on a capability that should be tool-routed. The verdict is **unresolved,
      not negative**: build a correctness set from actual `worker_general` traffic rather than five
      prompts inherited from a different question.
      Two structural findings surfaced while checking this, both filed below.

      - *(2026-10-30, native diagnostic READY; no task tick.)* `codex-ni-wg-lfmi-quality-native-r1-20261030` is a descriptive probe from 211 complete observed `worker_general` prompt byte strings, joined to 236 existing oracle/config aliases across 32 suites, rather than the five inherited reference prompts. Seven separate-context cases and unsupported execution/judge scorers remain explicit unknowns; 33 arithmetic-suite cases are separate. The 168 supported non-executing official scorer cases per arm and raw/cap/empty/transport/partial observations remain bounded by all 422 planned arm-cases. Exact captured prompt arguments are replayed as user text through each LFM's embedded template; historical system/chat-payload/wire equivalence and representative organic traffic are unavailable. READY, smoke, and cutoff evidence do not resolve quality or close WG-LFMI-3. Full scheduled native results and audit remain required. Evidence packet: `/mnt/raid0/llm/tmp/codex-ni-wg-lfmi-quality-native-20261030/` [belief: cc]

      - *(2026-10-30, native diagnostic completed; no quality gate tick.)* `codex-ni-wg-lfmi-quality-native-r1-20261030` completed all 211 planned cases per arm (422/422 original response files, no unattempted/cutoff/transport failures). Existing pinned official scorer yielded Q4_K_M **55 correct / 77 incorrect / 79 unknown** and Q8_0 **50 / 80 / 81**. Unknowns by scorer precedence: unsupported execution/judge 36 each, absent separate context 7 each, generation cap 36/38; the latter counts exclude capped cases already classified unsupported or absent context. The 33 arithmetic cases separately are **4/1/28** and **2/1/30**. Suite-by-suite denominators and findings: `progress/2026-10/2026-10-30-codex3-ni-native-filings.md`. No threshold was declared: descriptive observation, no decision-grade quality or WG-LFMI-3 closure. Replayed captured prompt arguments are not historical full-wire reproduction or representative traffic. Source/scorer pins and retained native artifacts: `/mnt/raid0/llm/tmp/codex-ni-wg-lfmi-quality-native-20261030/`. [belief: cc]
      - **[declined: ws58 2026-11-03 content-review: merged into WG-LFMI-3]** Resolve decision-grade worker quality with representative traffic and the separate WG-LFMI-3 protocol; retain the diagnostic's unsupported and missing-context unknowns.

- [ ] **NO DETERMINISTIC COMPUTE TOOL EXISTS for a worker to route arithmetic to.** Task: add a deterministic arithmetic/compute tool to `src/tools/` (sandboxed Python eval on numeric expressions, registered for worker roles), then re-score the 3/5 reference prompts with the tool available; done when the worker's arithmetic items pass by tool use rather than by model recall.

- **[declined: ws58 2026-11-03 content-review: duplicate — routing-program URE-1 owns the escalation-signal question]** **NO CORRECTNESS SIGNAL CAN TRIGGER ESCALATION on the `general` chain.** The chain exists —
      `worker_general → frontdoor → architect_general → architect_critic`, `max_escalations: 3` — but
      its triggers are only `error_categories: [timeout, inference_error]` and `explicit_request`.
      A confidently-wrong but well-formed answer is a **successful inference**, so it never escalates
      and is returned unchallenged. This is escalate-on-failure, not review-every-result; the
      distinction matters exactly where a small model is weakest.

- [ ] **WG-LFMI-2 — CPU + GPU decode, interleaved, both quants.** Report pp/tg with stddev, peak
      resident, **and tokens-per-task** — a t/s table alone is what nearly banked the wrong verdict last
      time. Reuse the harness under `benchmarks/results/scout/wg-lfm-1-20260812/` (replayable).

- [ ] **WG-LFMI-3 — The decision-grade bar the original row asked for and never got**: strict task
      success, per-suite outcomes, tool-schema compliance and repair rate, reasoning/output tokens,
      retries, peak RSS, TTFT, complete wall time. Needs a `llama-server` arm so the incumbent's **MTP**
      path is exercised — `llama-bench` cannot, and every number on record so far understates the
      incumbent for that reason. Blocked on **OP-16** (host reboot) for decision-grade.

- [x] **WG-LFMI-4 — Speculative decoding, only after WG-LFMI-1 passes.** ✅ 2026-10-29 Spec-dec raises tokens/second;
      it cannot fix tokens/task, which is what killed the last candidate. For a 1.2B target the drafter
      ratio problem is worse, not better — a same-family drafter would have to be tiny. **Measure
      acceptance rate α before investing**, per standing policy, and prove vocabulary identity rather
      than inferring it from a shared model-family name.

- [ ] **WG-LFMI-5 — RE-OPEN the 2.6B reasoning variant on a RESIDENCY argument, not a rate argument.**
      Raised by the operator 2026-08-12 after the 2.6B had already been rejected, and it is a different
      question from the one that rejected it. The rejection compared like-for-like hardware
      (GPU-vs-GPU, CPU-vs-CPU), which is methodologically tidy and **operationally wrong**: the
      incumbent is **CPU-served today**, and at 26.3% of the MI210 it cannot casually become
      GPU-resident, because the card already carries `architect_general`, `coder_escalation`,
      `vision_escalation` and `worker_vision`.

      | model | VRAM | % of MI210 |
      |---|---:|---:|
      | gemma4-26B-A4B Q4_K_M | 17,213 MiB | **26.3%** |
      | LFM2.5-2.6B Q4_K_M | 2,126 MiB | **3.2%** |
      | LFM2.5-1.2B-Instruct Q4_K_M | 695 MiB | 1.1% |

      Time-to-answer in the configuration each would ACTUALLY be deployed in: LFM2.5-2.6B on GPU is
      501 tok / 225.11 t/s = **2.23 s**; the incumbent on CPU is 33 tok / 19.40 t/s = **1.70 s** decode
      but **2.97 s** measured wall including prefill. That is a wash — not the 4.3x deficit on record.
      **The 15.2x token penalty is affordable precisely because the small model can be resident where
      the incumbent cannot.**

      Two caveats before anyone banks this. (1) The 3.2% figure UNDERSTATES the constraint: KV cache and
      concurrency scale with slots, not weights, so the real test is co-residency with the existing four
      GPU roles under load, not weights in isolation. (2) 2.23 s vs 1.70-2.97 s is close enough that it
      needs a measurement, not this arithmetic.

      **Weights were deleted but are exactly recoverable** — `model_registry.yaml` `lfm25_26b_q4km` /
      `lfm25_26b_q8_0` carry pinned revision `b421ad1d549afeda6a0fb2ad3a697cb5a7879adc` and both
      SHA-256 digests. Re-fetch from the ledger; do not re-derive from a fresh `main`. (re-scoped 2026-11-03 from incumbent comparator gemma4-26B-A4B: deleted; redo the residency/time-to-answer comparison against Qwen3.6-35B-A3B-MTP-Q8_0)

##### Traps this row has already paid for — do not rediscover them

- **[declined: ws58 2026-11-03 content-review: a trap note, not a task]** **`llama-cli` / `llama-completion` SILENTLY IGNORE `-rea off`.** `default_template_kwargs` is
      consumed only by `common_chat_format_example` there; `llama-server` honours it. The flag parses, is
      accepted, and changes nothing — producing **thinking-ON numbers labelled thinking-OFF**, i.e. it
      fails in the direction that flatters a reasoning model. Render the prompt yourself and prove it by
      **diffing token sequences**, with llama.cpp's own render as the control.
- **[declined: ws58 2026-11-03 content-review: a trap note, not a task]** **A raw-completion harness UNDER-SCORES a reasoning model** — the mirror trap. LFM2.5-2.6B looked
      wrong on one item purely because it was truncated mid-`<think>`; 9/9 with templates applied. A
      reasoning model measured without its template measures the template's absence.
- [ ] **RECIPE-NUMA-1 — `numactl --membind=<node>` is WRONG even for a single-region CPU grant**, and
      `canonical_recipe.py` has no region-scoped path to prevent it. Same cores, same binary, switching
      to canonical `--interleave=all`: **gemma +42%, LFM Q8 +80%, LFM Q4 +195%**, with stddev collapsing
      from up to **51% of the mean to under 1.5%**. The variance is the tell — membind was not
      slow-but-stable, it was unstable enough to be reported as either result. `--interleave=all` is
      correct at EVERY CPU scope.
- [x] **`GGML_IQK_Q8_0=1` is load-bearing for any Q8_0 CPU arm** ✅ 2026-08-12 — without it the Q8_0 run
      logged no `[iqk] ACTIVE` line at all: pp 539.24→870.47 (+61%), tg 15.75→24.97 (+58%). A Q8_0 bench
      omitting it is not top-optimized. `canonical_recipe.py` exposes `--ggml-iqk-q8-0`.
- [x] **Q4-vs-Q8 INVERTS from CPU to GPU** ✅ 2026-08-12 — on CPU Q4 beat Q8 by 1.60×; on GPU they are
      within noise with **Q8 marginally ahead**. At small parameter counts on MI210 decode is not
      weight-bandwidth-bound and Q4_K carries the CDNA2 MMQ dequant cost. **A quant choice justified on
      CPU evidence does not transfer to GPU** — expect to re-derive it for the 1.2B.
- [x] **`-fa 0` measured 12.9% faster decode for gemma4 on gfx90a** (101.44 vs 90.86 tg128, far outside
      ±0.9 stddev) while the bench launcher uses `-fa on`. **Forward-relevant, not a live defect**:
      `worker_general` is not GPU-served today (`device: null`), though the operator confirms it may be.
      Do not act without a server-arm check — FA interacts with MTP and long-context KV.
  - 2026-11-02 operator decision: Run a server-arm check when worker_general moves to GPU (decisions-batch2-4-20261102.json) [declined: operator 2026-11-03 model-audit: gemma-4-26B-A4B deleted 2026-09-23 and worker_general is now Qwen3.6-35B-A3B; fold FA-off into kernel notes if gemma4 is ever served]

#### 2026-08-09 — OpenRSI release-state watch (research-intake Stage-2b)

- [x] **Watch FrontisAI/OpenRSI PR #2 ("feat(gym): add OpenMLE Sandbox") to a decision.** ✅ 2026-08-11 — **TRIGGER FIRED: MERGED.** Verified live via gh api: merged=true, author_association flipped NONE→CONTRIBUTOR, upstream main pushed 2026-08-11T12:28Z; still 1 commit / 30 files (+7,617), so the merged content is byte-wise the ingest-reviewed content. The intake-940#record hard blocker (distributed grading service unpublished) has SOFTENED, not cleared — see follow-on. State at
  ingest: DRAFT, 30 files, +7,617/-0, one commit, `mergeable_state: clean`, opened 2026-08-09 from
  fork `LifeIsSoSolong/OpenRSI` branch `codex/openmle-sandbox` by an account with GitHub
  `author_association: NONE` — **not a Frontis account by any GitHub signal**. It publishes the
  distributed grading service that intake-940#record's dive named as the hard blocker on reproducing the
  paper tables. **TRIGGER**: if it merges, re-open that reproducibility finding
  ([intake-1024](../../research/intake_index.yaml) → intake-940#record). If it is abandoned, record that the
  blocker hardened. `main` was last pushed 2026-08-04, five days before the PR, so nothing has landed.
  **Caveat if it does merge**: reproduction would still require pulling worker and controller images
  from an external registry (they are not in the patch) and reconfiguring this host to cgroup v1 via a
  GRUB edit plus reboot — a host-boot change that is operator-only. The patch also ships default DB
  passwords and two internal RFC1918 worker IPs that the project's own `docs/validation.md` claims the
  public release scrubbed, which corroborates it as an unscrubbed internal snapshot.
- **[declined: ws58 2026-11-03 content-review: reproducing a third party's sandbox decides nothing on our stack]** **Follow-on (opened 2026-08-11, trigger-fired): assess OpenMLE Sandbox reproduction feasibility** — re-opens the intake-940#record reproducibility finding via intake-1024#record. Gates, in order: (1) worker/controller images pull from external registry (network only, any main); (2) **cgroup v1 host reconfiguration = OPERATOR decision** (host reboots are operator-only); (3) actual reproduction run = inference-lane compute. File (2) as a decision package only if (1) succeeds and the images are runnable.
  - 2026-11-02 operator decision: Decide only after gate (1) images pull and run [approved (wait for gate 1)] (decisions-batch2-4-20261102.json)

#### Research intake 2026-10-21 — open-model backdoors, control-vector projection, Qwen3.8 post-train (research intake entries 2191–2213, see research/intake_index.yaml)

- [x] **AMSB-C390-0 — Artifact integrity and uploader review for nerkyor Coder390-EfficientThink before any load.** Verify the GGUF sha256 against the repo's published sums and the HF LFS oid, read the GGUF header (arch qwen35, blk.64 MTP block) and diff the embedded chat template against the official Qwen3.8-27B template, and record a SEC-ART-3-style review (multi-teacher data, uncensored predecessor); the licence waiver at L547 does not cover backdoor provenance (intake-2193#09, intake-2193#11). ✅ 2026-10-21: review record `artifacts/intake-backdoor-cvec-20261021/AMSB-C390-0-review-record.md` (research c5661c5f9). Conditional GO for Q8_0 (29.07 GB) as tool-free eval artifact only; community uploader, no tool access; header/template/tokenizer clean vs base, provenance unauditable (abliterated predecessor, unreleased data); sha256 check is a step of the download.
- [ ] **AMSB-C390-1 — Same-harness A/B, Coder390 Q8_0-MTP vs base Qwen3.8-27B Q8_0, tool-free.** Gated on AMSB-C390-0. Both arms on our suites at two caps including the official 262,144-token reasoning cap, pinned items, n>=3 repeats at the recommended sampling, paired McNemar; columns for truncation, empty answers, reasoning tokens and DFlash2/MTP acceptance against base; tool-free suites only until SEC-EXEC-1..3 land (the headline LCB gain is likely a cap artifact: intake-2193#03).

- Trigger (no checkbox): any post-trained or fine-tuned Qwen3.8-27B variant enters a serving A/B. Then log DFlash2 and MTP acceptance against base on identical prompts as a required column (the post-train ships the base-trained drafter unchanged, intake-2193#10).

##### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off.

## Track: angelslim-techniques-evaluation
<!-- gate: none -->

> Moved from `handoffs/active/angelslim-techniques-evaluation.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-04. Sections without open boxes (background, closed ledger) stay in [`../completed/angelslim-techniques-evaluation.md`](../completed/angelslim-techniques-evaluation.md).

#### Progress checklist

- **[declined: ws58 2026-11-03 content-review: the STQ1_0 upstream watch is retired (quantization review)]** BLOCKED: reopen when llama.cpp PR #22836 (**STQ1_0 / Sherry ternary kernel** — *not* "AngleSlim
      kernels"; there is no such PR, see the 2026-08-12 gate check) merges **and** an x86 vec_dot exists
      **and** QAT checkpoints of a base we run exist
- [x] Gate re-checked against GitHub, and the row's own premise corrected ✅ 2026-08-12 — see
      [§ Gate check — 2026-08-12](#gate-check--2026-08-12)

##### New Related Research
- **[intake-806] "Hy3 — Tencent 295B/21B-active MoE"** (HF `tencent/Hy3`, Apache-2.0)
  - Relevance: the Hy3 model card references **Tencent AngelSlim** for its FP8 variant (`Hy3-FP8`) and compression toolchain — a concrete, current production model exercising the same AngelSlim path this stub tracks. Confirms AngelSlim is being applied to flagship-scale MoE, not just the Hy-MT2 MT family already noted here.
  - Delta from current approach: adds a large-MoE FP8 datapoint to the AngelSlim evaluation surface; watch whether AngelSlim FP8/sub-2-bit recipes for `hy_v3` land alongside the community GGUF port ([intake-808], `hy3-mtp` fork). See [[speculative-decoding-mtp-refresh]] for the Hy3 MTP/GGUF thread.
- [x] When evaluating AngelSlim compression, include the Hy3-FP8 flagship-MoE case as a test vector (operator-gated).
  - 2026-11-02 operator decision: Keep operator-gated (no Hy3 work) (decisions-batch2-4-20261102.json) [declined: operator 2026-11-03 model-audit: operator 2026-11-02: no Hy3 work; Hy3 retired and weights deleted]

##### Task update
- [x] Watch-item resolved (2026-07-11 update): AngelSlim's official Hy3 GGUF (intake-824) shipped **vanilla IQ1_M/Q4_K_M for hy_v3, not Sherry/STQ1_0** — no new sub-2-bit AngelSlim recipe for a base we run; Sherry adoption remains QAT-gated as documented. ✅ 2026-07-16
- [x] Operator-review candidate: the official IQ1_M (~90 GB, fits the ~680 GB free-disk budget) is an authoritative GGUF path if the deferred, operator-gated Hy3 architect-candidacy bench is ever run — see [[speculative-decoding-mtp-refresh]].
  - 2026-11-02 operator decision: Keep operator-gated (no Hy3 work) (decisions-batch2-4-20261102.json) [declined: operator 2026-11-03 model-audit: Hy3 architect candidacy dead; operator: no Hy3 work; Hy3 retired and weights deleted]

## Track: delta-mem-reproduction
<!-- gate: none -->

> Moved from `handoffs/active/delta-mem-reproduction.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-12. Sections without open boxes (background, closed ledger) stay in [`../completed/delta-mem-reproduction.md`](../completed/delta-mem-reproduction.md).

#### Progress checklist

- [x] Phase 1 Gate 1 (adapter loads) + Gate 4 (CPU tractable, 5% overhead) PASS ✅
- [x] Gate 3 LoCoMo N=5 smoke (1.65x, directional); magnitude inconclusive ✅
- [ ] Gate 2 MemoryAgentBench accuracy reproduction - GPU-only (CPU-infeasible)
  - 2026-11-01 v3 draft: `codex-ni-inf12-gate2-triton36-v3-20261101` retains the complete 22-source/two-arm official matrix (3,671 records per arm) and the original ±20% of 1.31× decision. Draft manifest SHA-256 `2cb7347069c7e862a6ea1c753d424d5a40728e29196c1efee7d2d938c3fac029`; source/test inventory in `/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/REVIEW.json`. Host controls bind the separate actual 67,283 and 258,333-token native events and STOP/drain path. No installed v3 owner route, real fixture receipt, full matrix or accuracy verdict; Gate 2 stays open. [no-belief: source preparation only]
  - 2026-11-01 audit (separate attempts; diagnostic only, no tick): R13 attempt `20261031T210259Z-128495` ran during `Accurate_Retrieval/eventqa_131072/base` and ended `rc=75` at 21:30:31Z after a 1,800s grant began 21:02:59Z. `STATE.json` records `work_started=true`; `job.log` records `stop_reason=work-deadline`, child rc143 and direct-child reap, but descendants were not censused. No attempt-local native JSON/JSONL is retained and the number of completed official items cannot be attributed to this attempt. Its archived terminal is `compute-flags/grants-archive-ws58/codex-ni-inf12-gate2-triton36-r13-20261030.ended.keeper-1793482232`; do not synthesize a current `.ended` or assign the shared output tree to this attempt. This is distinct from attempt `20261101T003829Z-2260396` (00:38:29Z), whose 444-line shared JSONL line count also does not establish completed official records. Preserve both identities/exposures. Any continuation uses a fresh ID after owner boundary and verifies pins and every resumable output row/hash before reuse; denominator remains 3,671 official records per arm (7,342 total). No Gate 2 score or verdict. [no-belief: attempt audit and partial evidence only; no complete measurement tuple] [Durable evidence](../../artifacts/compute/ni-inf12-yarn-prep-20261101/README.md).
  - 2026-10-30 14:38 UTC (R13 T1 repair): actual normal launcher emitted diagnostic admission and `START` at 14:38:33Z; native `Accurate_Retrieval/eventqa_131072/base` began at 14:38:56Z under the 14:38–15:08Z grant. This is a started native attempt, not a full-result summary or Gate 2 verdict. The original population and recipe are unchanged; full-context repair and Gate 2 remain open; no checkbox tick. Current launcher evidence: `/mnt/raid0/llm/tmp/compute-flags/ready/codex-ni-inf12-gate2-triton36-r13-20261030.launcher.out`. Earlier pending/ghost status in the R13 owner draft is superseded by these later events. [no-belief: started attempt only; no completed full-task result]
  - 2026-10-28 (ws58 results filing, diagnostic, no tick): `codex-ni-inf12-gate2-triton36-r6-20261028` (GPU, pin `809e93f2`) PARTIAL rc 75 at 23:22:32Z (`work-deadline`, child reaped, STATE `partial`, 1635 s wall; launched 22:55:15Z, first question 22:55:35Z). `Accurate_Retrieval/eventqa_131072/base` completed 16 records (record_index 0-15, contiguous, 16/16 resume-integrity hashes valid, one run_fingerprint `5536036d`); delta arm not started. Interim sample-weighted metrics over those 16 only: exact_match 0.6875 (11/16), substring_EM 0.6875, eventqa_recall 0.6875, F1 0.8135, rougeL_F1 0.8284, ~97 s/question (1554 s query time). Comparison with the r4 partial (scratch `codex-ni-inf12-g2-20261028/outputs/full-results-5e65*`, pin `5e6515c4`, same source/arm): 68 records, EM 0.8088, F1 0.8791, ~97 s/question; r6's 16 records are the same questions as r4's first 16 (record_index 0-15) with byte-identical outputs on 16/16, so the EM gap (0.6875 vs 0.8088) is a question-mix effect of n=16 vs n=68, not a regression, and the per-question rate matches. Resume: r6 should resume at record 16 in a next window with no code change (launch.sh/job.sh sha256 unchanged from the READY row, no STOP file, same pin and run_fingerprint, evaluator verifies identity and integrity of every existing row before continuing); this is by code inspection and a validation of the on-disk rows, not an observed resumption, and r4/r5 outputs cannot be resumed by r6 (different pin). Keeper: `REARM-SKIP codex-ni-inf12-gate2-triton36-r6-20261028: no unambiguous ws58-launcher*.out in /mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028-r6` at 23:23:43Z; no REARM-OK for this id, so the next window is not armed until the owner supplies one. Diagnostic only (predeclared rule: raw metrics, no threshold); Gate 2 remains open. [belief: cc]
    - [x] ~~INF-12 Gate 2 r6: re-arm the resumable successor window (owner `codex-ni-01a16d6b`) so the keeper emits REARM-OK, and continue eventqa_131072 base from record 16, then the delta arm and the remaining sources.~~ (closed 2026-10-29 audit: SUPERSEDED → r6 successor re-arm replaced by r8 window (codex-ni-inf12-gate2-triton36-r8-20261029 ran, delta-mem-reproduction.md:240) and r8 re-estimate box :241)
  - 2026-10-29 (ws58 results filing batch B, diagnostic, no tick): `codex-ni-inf12-gate2-triton36-r8-20261029` (GPU mi210_0 + 184-191, new pin `eb329bb4`, run_fingerprint `9722cd61`) first window PARTIAL rc 75 at 01:48:32Z (`work-deadline`, child reaped, STATE `partial`, 1,657 s wall). Units: about 16 of 500 `Accurate_Retrieval/eventqa_131072/base` records in that window, inferred from cumulative query time (16 → 1,555 s, 17 → 1,652 s); the population is 3,671 per arm, 7,342 for both. r8 is a fresh resume namespace: it re-ran record_index 0-15 with outputs byte-identical to r6 on 16/16, so the r6 re-arm box above is superseded by r8 rather than resumed. The row has kept running in later 30-min windows under the same pin: 11 more windows started 01:55-06:58Z, 10 ended rc75/partial at `work-deadline` and the 06:58Z window was still running at filing. At the filing read (~07:05Z) the file held 179 contiguous records, interim base-arm EM 138/179, F1 0.8485, ~98 s/question. The delta arm has not started. Diagnostic only (predeclared rule: raw source-level and sample-weighted metrics, no threshold); Gate 2 stays open. [belief: cc]
    - **[declined: ws58 2026-11-03 content-review: merged into Gate 2 as its sizing]** **INF-12 Gate 2 r8 feasibility re-estimate (filed 2026-10-29, ws58 filer B):** at the measured ~98 s/question on eventqa_131072 (~16 questions per 30-min GPU window), the FILLERS row's "~8 h total" cannot cover 7,342 questions; this source's base arm alone is ~13.6 GPU-h. Re-estimate per source from measured s/question, then book longer GPU windows or narrow the population by an owner decision recorded here. Done when the row carries a measured-rate ETA.
      - 2026-11-02 planning evidence: R13 base-arm single-question generation observations are 35.085 s for `eventqa_65536` and 376.593 s for `eventqa_full`; the latter is a conservative admission observation, not a universal source rate. The independently documented `eventqa_131072` base rate is ~98 s/question, giving ~13.6 GPU-h for its 500 questions before window overhead. These are not measured rates for the other sources or the Delta arm, so a full-matrix measured-rate ETA remains unknown. Evidence: `/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/inf12/RATE-EVIDENCE-v3.json`; prepared v3 successor remains a proposal pending owner route and real qualification, as detailed in `/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/REVIEW.md`. Do not publish that proposal as ready. [no-belief: partial calibration observations, not a full feasibility estimate]
- [x] Gate 2 runtime/readiness preparation: pinned Triton 3.6 actual-entry smoke, 2 real questions per arm, rc 0 and writers complete; diagnostic only, full population and verdict remain open. [no-belief: smoke-only readiness evidence; no full Gate 2 measurement tuple]
- [ ] Gate 3 magnitude: wider LoCoMo eval (25-50 samples) - GPU-realistic
  - 2026-11-02 preparation: the existing `deltamem/eval/locomo_delta.py` supports GPU and the 5-conversation × 5-question scope, but deletes its progress JSONL at startup and writes final JSON only after both arms; it has no safe interrupted-run resume. Use an isolated output namespace and first publish a bounded GPU compatibility/rate diagnostic with pinned inputs and an explicit diagnostic rule. The 25-question paired result cannot establish the full-test magnitude. Launcher, protocol and rowflow requirements are being prepared independently; no GPU row or accuracy result exists yet. [no-belief: source inspection and planning only]
- [ ] Phase 2: M.3 KV-Extension prototype on Qwen3.6-35B-A3B-MTP-Q8_0 worker_general, A/B vs SQLite B1 (re-scoped 2026-11-03 from gemma4 worker_general: deleted; now Qwen3.6-35B-A3B-MTP-Q8_0 worker_general)
- [ ] Phase 3: full delta-mem GGML op + cross-session persistent bank (gated on Phase 2)

**2026-10-30 GPU partial, original R13:** The first repaired normal GPU run stopped at its work deadline (rc 75) on `Accurate_Retrieval/eventqa_131072/base`. The native file observed afterward contains 16/500 base source rows (16/3,671 per-arm pinned population), eventqa recall and exact match 11/16 (0.6875), mean F1 0.8134858197. No DeltaMem rows were present in the observed file. The 16-row file mtime predates the original stop, but the snapshot was taken after a separate rearm started in the shared namespace; exact boundary completeness and unknown cases are not independently established. Direct child was reaped; descendants were not censused. This is partial coverage, with no Gate 2 comparison or closure. See [native audit](../../artifacts/inf12-r13-original-audit-20261030.json) and [filing record](../../progress/2026-10/2026-10-30-codex3-inf12-r13-original.md). [belief: cc]

## Track: ernie-image-turbo-evaluation
<!-- gate: none -->

> Moved from `handoffs/active/ernie-image-turbo-evaluation.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row PIP-03. Sections without open boxes (background, closed ledger) stay in [`../completed/ernie-image-turbo-evaluation.md`](../completed/ernie-image-turbo-evaluation.md).

#### Progress checklist

- [x] Acquire the requested Qwen-Image-2.1 Diffusers weights for comparison ✅ 2026-09-23 — complete public bundle at
      `/mnt/raid0/llm/models/diffusion/qwen-image-2.1/` (33,115,613,408 bytes; all text-encoder and transformer
      shards plus VAE present). Acquisition is not a generation benchmark; no Qwen-vs-ERNIE outputs or comparative
      claims are recorded yet.
- [x] Switch the production `image_generate` backend to Qwen-Image-2.1, preserving the API and keeping ERNIE for rollback ✅ 2026-09-24 — CPU-only Diffusers service is healthy on port 8190; no generation-quality claim is made.
- **[declined: ws58 2026-11-03 content-review: merged as a follow-up of the ERNIE rebench]** Run a matched-prompt Qwen-Image-2.1 vs ERNIE generation comparison and record prompt, settings, outputs,
      and admissibility before drawing quality or speed conclusions.
- [x] Production functional on CPU via sd-server Q8 + conv-direct; Q4 rejected (text corruption) ✅
- [x] **File the missing intake row and close the `intake-528` mis-citation** ✅ 2026-07-29 — the deployed
      `image_generate` model had NO index row for its entire deployed life, while this handoff (4 places)
      and the deep dive (2) cited `intake-528`, which is "Effort Engine (bucketMul)". Created `intake-937`
      (`already_integrated`, dive-verified) and repointed all 6 references with inline dated correction
      notes. A *missing* entry is loud; a *wrongly-pointed* one is silent — every reader who checked the
      citation was reassured, and it survived until a Z-Image dive grepped the index instead of trusting
      the handoff. Cross-ref citations are now worth a periodic sweep, not just a per-entry check.
- [x] Record the LongText-Bench resolution in the deep dive (§ benchmark positioning) ✅ 2026-07-29 — harmonized ranking,
      identical splits, EN/ZH-mean aggregation, ERNIE +4.4 over Z-Image-Turbo even w/o prompt enhancer; and
      that ERNIE's own 0.9655 remains vendor-self-reported (see the 2026-07-29 section above)
- **[declined: ws58 2026-11-03 content-review: merged as a follow-up]** Run content-filter audit live with --execute (harness ready in orchestrator ed6f65f5) and review outputs
- **[declined: ws58 2026-11-03 content-review: merged as a follow-up]** Run 20-prompt local LongTextBench-style EN/ZH typography spot-check to validate 0.9655 self-report
- [ ] GPU/MI210 rebench of the 8-step distilled DiT via ROCm/HIP path (operator-approved, measure-not-extrapolate) Follow-ups after the rebench (absorb three rows): matched-prompt Qwen-Image-2.1 vs ERNIE comparison with admissibility recorded; the live content-filter audit (--execute); the 20-prompt EN/ZH typography spot-check against the 0.9655 self-report.
  - **Build ready 2026-09-16 (sub-gpu-prep; run still open):** sd.cpp worktree
    `/mnt/raid0/llm/worktrees/sub-gpu-prep-stable-diffusion.cpp` (`sub/gpu-prep-20260916` @ `a54f50c`, base `90e87bc`),
    build `build-rocm-gpuprep-20260916` (shared ggml, HIP gfx90a, ROCm 6.2; sd-server sha256 `5335caad…4862`),
    carrying the ggml FP8 guard and a ROCm f32 fix on ERNIE `to_out.0`/`linear_fc2` (`SD_ERNIE_ROCM_F32=0` disables it
    for A/B). `verify_ggml_linkage.sh` PASS (all four ggml libs inside the build dir). Runner recipe (port 18190,
    768–1024² × 8 steps × 3 repeats, fix on/off, blank-PNG metric, VRAM sampled during the run):
    `RUNNER_RECIPE.md` in the worktree. Prod `build/` and `build-hip/` untouched.
  - **RUN 2026-09-16, 14:21–14:30Z (sub-gpu-runner; collected by sub-gpu-collect).** Result: **the f32 fix is
    REFUTED**, by the recipe's own rule ("B still blank at 1024²"). Box NOT ticked: there is no valid 1024² GPU
    number.
    - **Evidence.** Research main `cf05eefc`, `data/ernie-rocm-rebench-20260916/`. PNG sha256s are in
      `requests.jsonl`; the images themselves are not committed.
    - **Admissibility.**
      - 23/23 requests returned HTTP 200.
      - The server pid was listed in KFD in every sample of every request.
      - The log shows `found 1 ROCm devices` / MI210, and params load with `RAM 0.00MB`.
      - Peak VRAM: 25.5 GiB with the patch ON, 19.0 GiB with it OFF.
      - Peak KFD count 1. The linkage receipt PASSes.
      - sclk dipped to 1295 MHz.
    - **Results.** 8 steps, seed 2026072732, n=3 per cell. Every cell was bit-identical across its reps, so
      the spread is zero.

      | shape | patch ON gen s | patch OFF gen s | output |
      |---|---|---|---|
      | 768² | 16.3 | — | good |
      | 896² | 23.0 | 20.3 | good |
      | 960² | 26.9 | — | good (visually checked) |
      | 1024² | 30.2 | 26.5 | **uniform white** (mean 255, sd 0, 33 KB), ON and OFF |
      | 832×1248 | 30.4 | — | **uniform white** |

    - **Reading.**
      - The patch does not fix the ≥1024² white output, and it costs about 13% (896²: 23.0 vs 20.3 s).
      - 960² is now non-blank with the patch ON, where the 2026-07-19 build was blank at ≥960². Patch OFF was
        not run at 960², so that change cannot be attributed to the patch.
      - Per the recipe, no headline speedup is computed.
    - **Belief kernel.** No write hook; covered by VB-GPU-RUNNER.
  - **Recipe §5 follow-ups A/B, 2026-09-17, 02:30–02:55Z (sub-s5-topup chain8; sd.cpp `f3a7fe95`, build
    `build-rocm-variants-20260916`, sd-server sha `d33cbe6f…`, RUNNER_RECIPE §8). Result: NO variant FIXES.**
    Box NOT ticked: there is still no valid 1024² GPU number.
    - **Evidence.** Research main `ca8c63d6`, `data/gpu-mi210/ernie-image-turbo-hip-variants-20260917/`
      (`verdict.json`, `requests.jsonl`; PNGs not committed).
    - **Admissibility.**
      - 55/55 requests returned HTTP 200, with the same prompt and seed as `cf05eefc`.
      - All 5 servers were resident, and each knob echo matched its variant.
      - Each teardown was a SIGTERM on the driver's own PID, confirmed dead.
      - Prod CPU sd-server pid 910274 was untouched and is still alive.
    - **Pre-registered verdict.** FIX requires 1024² and 832×1248 non-blank on every rep, AND 768–960² good.

      | variant | 1024² + 832×1248 non-blank | 768–960² guard | verdict | 896² gen s vs off (19.44) |
      |---|---|---|---|---|
      | off (`F32=0`) | 0/6 | 768 ✓, 896 ✓×3, **960 blank ×3** | BASELINE (defect reproduced) | — |
      | f32 (narrow, default) | 0/6 | not run | DOES-NOT-FIX | — |
      | wide | 0/6 | 768 ✓, 896 ✓, 960 blank | DOES-NOT-FIX | 27.66 (**1.42×**) |
      | outscale (1/16) | 0/6 | 768 ✓, 896 ✓, 960 blank | DOES-NOT-FIX | 19.70 (**1.01×**) |
      | wide+outscale | 0/6 | 768 ✓, 896 ✓, 960 blank | DOES-NOT-FIX | 1 rep 27.89 (≈1.43×, not the 3-rep cost cell) |

    - **Reading.**
      - The missing cell, patch-OFF 960², is blank. With the same seed and prompt, the 2026-09-16 narrow-ON
        960² was good. So the narrow f32 patch moved the blank threshold from 960² to 1024², a cross-build
        comparison on the same default code path.
      - Neither the wider f32 set nor the out-proj scale extends that shift. Both are blank at 960² again.
      - The white output at ≥1024² is not fixed by any precision change on the DiT linears.
      - Recipe §5 is exhausted. The next hypothesis has to lie outside those linears, for example the VAE decode
        or the attention/FA path at the larger sequence length. It needs a new build plus prep, not a re-run.
    - **Belief kernel.** No write hook; covered by VB-GPU-RUNNER.
  - [ ] **ERNIE-ROCM-NEXT — prepare the next ≥1024² white-output hypothesis outside the DiT linears** (VAE
        decode, or the attention/FA path at the larger sequence length): a new sd.cpp build and a
        pre-registered A/B, zero-inference prep first. The run waits for the operator to lift the 2026-09-17
        GPU hold. Filed 2026-09-17 from recipe §5 being exhausted (`2026-09-16-sub-s5-topup.md`).
- **[declined: operator 2026-11-03 model-audit: superseded by the production image backend Qwen-Image-2.1 (bilingual, cut over 2026-09-24)]** Re-litigate FLUX.1-schnell alternative if bilingual long-form in-image text not needed by product

## Track: gpu-cot-scaffold-sidecar
<!-- gate: none -->

> Moved from `handoffs/active/gpu-cot-scaffold-sidecar.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-19. Sections without open boxes (background, closed ledger) stay in [`../completed/gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md).

#### G3 — Scaffold-generator A/B: FF + TC vs Qwable (+ the pending standalone control) — first post-campaign GPU experiment

_Reuses the built harness (`/mnt/raid0/llm/tmp/cot-g1/`, SCAFFOLD-PREFIX mode) and the validated conditional deploy rule (reasoning-bound task + receiver latent capability). GPQA-48-class scale, single MI210 sidecar — small. Run `g3-gpqa-20260728T070247Z-manual2` and its v3 matched-control successor are terminal OBSERVATIONS; G3-0 through G3-3a and the G3-3 saved-output replay are complete. The default remains no deployment decision: a future decision instrument is separate. No role, lineup, registry, or deployment action is implied._

- [x] **G3 prerequisite — exact Qwable IQ4_XS artifact restored and verified** ✅ 2026-07-28 — `Qwable-v1.IQ4_XS.gguf` is present at the pinned HF revision `f35ea1502056a2886dd88fb8a29272f8f3c9c3a5`, `18,939,313,056` bytes, SHA-256 `3921bb8f1fc26ddd80ee97d0f48ccf507bd1dab04dbe4fc475e2eae65a05f460`. Durable restore receipt: `/mnt/raid0/llm/tmp/cot-g1/g3_20260728/restore_qwable_iq4xs.log`. This restores the fixed control artifact only; it does not execute G3.
- [x] **G3-0 — Qwable-standalone GPQA control** ✅ 2026-07-28 — terminal arm `40/48` (`83.33%`), `214,234` generator tokens; frozen-scorer replay exactly matches all stored item judgments. This completes the standalone arm, but does not resolve relay vs amplification because the bundle has no matched Qwable-prefix receiver arm.
- [x] **G3-1 — FF-non-MTP as generator** ✅ 2026-07-28 — terminal prefix arm `41/48` (`85.42%`), `311,346` generator + `11,932` receiver = `323,278` total tokens (`1.509x` Qwable-standalone tokens); frozen-scorer replay exactly matches.
- [x] **G3-2 — TC as generator** ✅ 2026-07-28 — terminal prefix arm `43/48` (`89.58%`), `207,610` generator + `8,983` receiver = `216,593` total tokens (`1.011x` Qwable-standalone tokens); frozen-scorer replay exactly matches. This is the highest point estimate in this screen, not a selection verdict.
- [x] **G3-3 — deterministic saved-output replay and observation closeout.** ✅ 2026-07-29.
  Frozen-scorer replay had zero mismatches across all 5 x 48 saved outputs: receiver-nothink
  `25/48`, Qwable standalone `40/48`, Qwable-prefix `42/48`, FF-prefix `41/48`, and TC-prefix
  `43/48`. Generator differences are statistically null. Qwable-prefix used `32,768` context versus
  `16,384` for the other prefix arms, so it cannot support a causal generator ranking; FF is
  dominated by Qwable-prefix on accuracy, tokens, and compute, while TC is only +1 against it at
  3.25x compute with a null paired delta. This closes deterministic analysis only. **No deployment,
  lineup, registry, or generator-selection rule changes.**
- [x] **G3-4 — future decision instrument (separate from G3-3).** Select and run a decision-grade,
  context-matched generator/receiver instrument only if a concrete deployment decision is proposed.
  Do not regenerate or continue deterministic analysis of the sealed G3 artifacts. [declined: operator 2026-11-03 model-audit: all generator arms (Qwable, Fable-Fusion, ThinkingCap-27B) deleted; conditional on a deployment decision that cannot name them]
- [x] **G3-3a — matched-control + stop-reason repair** ✅ 2026-07-28 — v3 preserved the sealed 48-item input/scorer and imported the valid v2 rows without regeneration: receiver-nothink `25/48` (all 48 imported), Qwable-prefix `42/48` (5 imported + 43 fresh). The previous context failure is durably prevented: full rendered-prefix preflight found worst case `16,444 + 4,096 = 20,540` tokens and selected the bounded `32,768` context. Raw responses retain llama-server `stop_type` (`eos`/`word`/`limit`); teardown and `COMPLETE` are present. Artifact: `/mnt/raid0/llm/tmp/cot-g1/g3_20260728/successors/g3-gpqa-20260728T070247Z-manual2-controls-v3/` (`prepared.json` SHA-256 `508242ea57bf6b7505626215a110cd8fabf11ef6c217834a971f1af5dcf1a25c`, raw attempts `9af5d10764901394ab7c7167e6bfe5e357eac90b1d31e3a5467eafa838fff8bb`).

## Track: lightning-attention-port
<!-- gate: none -->

> Moved from `handoffs/active/lightning-attention-port.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-30. Sections without open boxes (background, closed ledger) stay in [`../completed/lightning-attention-port.md`](../completed/lightning-attention-port.md).

#### Outstanding Tasks

- [x] **LQ-1 role decision**: **parked architecture reference** (owner: Inference
  Acceleration / this handoff) ✅ 2026-07-29. This is a production-role decision,
  not a claim that the port or model is broken. The Q4 artifact remains on disk and
  current v8 production/experimental sources retain the `bailingmoe` architecture,
  but it is Tier C, cold, and unpinned; no active stack configuration selects it.
  The last complete quality review is historical (2026-05-04) and scored 59/90
  (65.6%), with 7 empty responses and a regression when the output budget was
  enlarged. The Qwen drafter route is already a hard no-go (different tokenizer
  and impossible acceptance/throughput math); neither a current q-scorer/routing
  comparison nor a compatible Ring-flash target exists. Do not assign it a live
  role from the AIME spot check or old review alone. Reopen only with (a) a
  specified same-tokenizer Ring-flash candidate, or (b) an owned, current-era
  q-scorer/routing A/B against the incumbent; either condition then starts LQ-2
  or LQ-3 respectively.
- **[declined: operator 2026-11-03 model-audit: Ring-mini-linear-2.0 deleted 2026-10-20 and deprecated; no live role]** **LQ-2 broader quality eval**: if keeping a math/reasoning role, run a focused AIME/MATH/GPQA-style bundle with `reasoning_budget=0`, exact prompt templates, and explicit safety exclusions.
- **[declined: operator 2026-11-03 model-audit: Ring-mini-linear-2.0 deleted 2026-10-20 and deprecated; no live role]** **LQ-3 Ring-flash drafter check**: only if a compatible Ring-flash target is available. Measure acceptance-adjusted throughput; raw Ring-mini t/s is not enough.
- **[declined: operator 2026-11-03 model-audit: Ring-mini-linear-2.0 deleted 2026-10-20 and deprecated; no live role]** **LQ-4 profile-gated L5 decision**: only profile after LQ-1/2/3 gives a reason to keep the model. Promote a dedicated op only when the profile proves a material bottleneck.

##### Tasks

- [x] **Z9 (Z, prerequisite for G18) — write the ~30-line pure-PyTorch constant-decay simple-GLA <!-- evidence-integrity: Research `d2d485598807f8fe5ab9badbfe539e3857ff1f51`; artifact: artifacts/compute/refactor-evidence-corrections-20261031/19/public-oracle-tests-final.log; hygiene, not quota -->
      recurrence** to stand in for the `fla` Triton call, **so that an HF CPU numerical oracle exists
      at all**. ✅ 2026-10-29 — Research `d2d485598807` ships `scripts/benchmark/sala_cpu_oracle.py`:
      float32 CPU recurrence, original ALiBi slopes, initial/final state, native chunk/fused interfaces,
      packed independent sequences and hash-pinned local HF import with `GenerationMixin` compatibility.
      All11 controls pass, including an independently expanded causal sum at0/1/7/63/64/65/129 tokens,
      split continuation, packed state isolation, native original SALA short/chunk masked attention,
      original1/3/7/32-head slopes, source mismatch and import cleanup. No weights or pretrained model
      inference ran; no GPU Triton numerical equivalence or GGUF parity is claimed. [Usage/source pins](https://github.com/pestopoppa/epyc-inference-research/blob/d2d485598807/docs/reference/sala-cpu-oracle.md),
      [native control evidence](../../artifacts/compute/codex3-relocatable-and-sala-z9-20261029.json).
      G18 retains its original3-prompt ×32-token, under8192-token, token-identical gate and remains open.
      [no-belief: CPU reference implementation and native-interface code tests; no inference result]
- **[declined: ws58 2026-11-03 content-review: no lineup role names MiniCPM-SALA; its InfLLM-V2 block has no ggml op (model-architecture Gate 5, now retired) and the port decides nothing]** **G18 (G, prerequisite `Z9`) — SALA correctness-first port + CPU parity smoke.** On *(2026-11-04: the MiniCPM-SALA checkpoint (/mnt/raid0/llm/models/MiniCPM-SALA-HF-9180fe1d, 18 GB) was deleted by operator order because adoption was declined 2026-11-03; re-downloadable from HF.)*
      `llama.cpp-experimental` branched from the current production tip (**never v9**). Greedy
      (`temp 0`, fixed seed), **3 prompts × 32 tokens, every prompt under `sparse_config.dense_len` =
      8192** so both sides run the sparse layers dense and the comparison is not confounded by the one
      primitive we do not have. GGUF output vs the `Z9` HF CPU oracle.
      **Gate:** **token-identical output on all 3 prompts.** Anything less is not a parity result and
      must not be reported as one.
      **Owner:** this handoff. Both compute planes were held by other sessions through this wave —
      **filed, not run.**
- [x] **B8 (B, blocked on `G18`) — the three things that all presuppose numerical correctness.**
      None may start before G18 passes; each is listed with the handoff that would own it if it does.
      **(a) Throughput.** Decode and prefill t/s for SALA Q4_K_M on EPYC at 4K / 32K / 128K against the
      production frontdoor, and on MI210 HIP. Owner if opened:
      [multiscreen-attention-evaluation.md](long-context-program.md#track-multiscreen-attention-evaluation).
      **(b) NoLiMa adjudication.** The paper's Table 3 reports 128K = 23.86; an unmerged NoLiMa
      leaderboard PR submitted by an account whose handle matches a SALA co-author reports **40.9** for
      the same model on the same benchmark, and lists an *effective length of 4K* for a model marketed
      at 1M. Neither source ships raw files, so this is only resolvable by running it. Owner if opened:
      [eval-tower-verification.md](eval-tower-program.md).
      **(c) An InfLLM-V2 block-sparse ggml op.** **Justified only if (a) shows the dense fallback makes
      prefill the binding constraint above ~32K.** Owner if opened: this handoff. Note the standing
      decline on porting `infllmv2_cuda_impl` to HIP — sm80 CUDA only, zero hip/rocm hits, and upstream
      llama.cpp closed the SALA support request `not_planned`; **re-surface only if SGLang PR #30360's
      AMD ROCm CI leg goes green**, which is the leading indicator for this hardware.
      Adopting SALA as a production model is a separate standing **decline**: 9B dense against our
      35B-A3B, no evidence it wins on any axis we serve, and no reproduced number from anyone in six
      months.

  <!-- task-evidence-integrity:start Z9 -->
  - Evidence metadata (hygiene, not new quota): Research `d2d485598807f8fe5ab9badbfe539e3857ff1f51`; [original test/artifact](../../artifacts/compute/refactor-evidence-corrections-20261031/19/public-oracle-tests-final.log). Full Z9 primitive exists with native HF import and11 original numerical/interface controls; this is not G18 model/GGUF parity. No tests rerun or historical redating.
  <!-- task-evidence-integrity:end Z9 --> [declined: operator 2026-11-03 model-audit: operator: adoption declined, not pursuing (MiniCPM-SALA throughput / NoLiMa / InfLLM-V2)] *(2026-11-04: the MiniCPM-SALA checkpoint (/mnt/raid0/llm/models/MiniCPM-SALA-HF-9180fe1d, 18 GB) was deleted by operator order because adoption was declined 2026-11-03; re-downloadable from HF.)*

## Track: minddr-deep-research-mode
<!-- gate: none -->

> Moved from `handoffs/active/minddr-deep-research-mode.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row UFH-04. Sections without open boxes (background, closed ledger) stay in [`../completed/minddr-deep-research-mode.md`](../completed/minddr-deep-research-mode.md).

### MindDR Deep Research Mode

**Status**: REFRESHED 2026-07-29 — Phase 1 scaffold landed; MD-9 A/B is the live gate; Phase 2 hardware is present but its training-runtime preflight is blocked; Phase 3 conditional
**Created**: 2026-04-22 (split from `routing-intelligence.md` per deep-dive integration pass)
**Updated**: 2026-05-28 (executor gate clarified after MD-1..MD-8 landed)
**Categories**: agent_architecture, routing_intelligence, training_distillation
**Priority**: MEDIUM (Phase 1 zero-infra; Phase 2/3 deferred)
**Depends on**: `routing-intelligence.md` (classifier infrastructure), `eval-tower-verification.md` EV-9 (multi-dimensional rubric)
**Sibling (same gate, lighter weight)**: [`gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md) — its **G1** ("does an injected CoT scaffold beat a code worker's own thinking, per token?") is **MD-9 one weight down**. Both live in the **reasoning-economics cluster** (`research-evaluation-index.md`) and must share the EV-9 DRACO/MindDR scoring contract + token-normalization, not re-derive them.

> **🔔 Reopen-trigger FIRED (Phase 2) — 2026-07-18 stale-open audit.** The hardware-acquisition wait is cleared: the DGX-Spark path is dead and the **MI210 is present (2026-07-02)**. The 2026-07-29 preflight found no pinned gfx90a training runtime, so the viability smoke remains blocked on provisioning plus a quiet-window lease. (MD-9 A/B remains the live Phase-1 gate, still inference-window-gated.) See [`stale-open-audit-2026-07-18.md`](../completed/frontier-lab-automation.md#track-stale-open-audit-2026-07-18).

- **[declined: ws58 2026-11-03 content-review: training, out of scope]** Phase-2: run a gfx90a (MI210) training-viability smoke now that the hardware gate flipped (was DGX-blocked) — **BLOCKED 2026-07-29**: GPU is idle and visible, but both project uv environments lack `torch`, `transformers`, `accelerate`, `trl`, `peft`, and `datasets`; requires a pinned gfx90a-compatible training environment, not an ad-hoc install. **Countermanded until E5 Stage-B releases the host:** a Python ROCm trainer is currently invisible to E5's process/SMT-affinity gates and could silently contaminate its decision-grade CPU cells.

#### Research Intake Update — 2026-07-08: PaperBench Source-Fidelity (rec-006)

**Source**: PaperBench (intake-794)

**Key finding**: PaperBench benchmarks model ability to understand and reproduce research papers. Methodology may be transferable to our deep-research pipeline for validating that our agent-generated research artifacts are faithful to source material.

**Applicability to EPYC**: Our MindDR pipeline produces synthesized reports from multi-agent research. PaperBench-style validation could serve as a quality gate for the ReportSynthesisNode, ensuring the final report is faithful to the collected evidence. Particularly relevant for Phase 2 RL training where citation-grounded reward shaping is critical.

**Action**: Monitor PaperBench development; evaluate as a source-fidelity validation gate for our deep-research reports.

- [x] **MD-PB-1** — evaluate PaperBench methodology for source-fidelity validation of deep-research reports ✅ 2026-07-22
- **[declined: ws58 2026-11-03 content-review: "consider" a rubric integration; no decision]** **MD-PB-2** — consider integrating PaperBench-style evaluation into MD-9 A/B test rubric

#### Progress checklist

- [x] MD-1..MD-8 Phase 1 scaffold (flag, classifier, prompts, pydantic_graph, rubric, sentinel suite - DONE 2026-04-22) ✅
- [ ] MD-9 A/B test sentinel suite with deep_research_mode 0/1 (>=+5pp gate, INFERENCE-GATED) On a durable >= +5 pp pass: the one-line request-dispatcher wiring (feature_flag && is_research_like -> run_minddr) and the MD-14 architect role refactor; include the rubric-as-execution-interface prompt variant as an arm (absorbs three rows).
- **[declined: ws58 2026-11-03 content-review: merged into MD-9 as its consequence]** Request-dispatcher 1-line wiring (feature_flag && is_research_like -> run_minddr) once MD-9 passes [too-big: prerequisite MD-9 is an incomplete inference-gated handoff experiment]
- [x] EV-9 multi-dimensional rubric scoring (handed to eval-tower; needed for non-structural MD-9) ✅ 2026-10-29 (audit: eval-tower-verification.md:295-310 EV-9 all 4 tasks [x] (orchestrator 9db36fcb, rubric_scoring.py exists); exit criterion "MD-9 A/B can produce multi-dimensional scores" met) [no-belief: audit-reconciliation]
- **[declined: ws58 2026-11-03 content-review: GPU-gated RL training, out of scope]** Phase 2 MD-10..MD-13 four-stage RL (GPU-gated, deferred)
- **[declined: ws58 2026-11-03 content-review: merged into MD-9 as its conditional consequence]** Phase 3 MD-14 architect role refactor (conditional on durable >=5pp uplift)

##### New Related Research
- **[intake-810] "RubricEM: Meta-RL with Rubric-guided Policy Decomposition beyond Verifiable Rewards"** (arxiv:2605.10899; Google Cloud AI + UIUC)
  - Relevance: same **four-stage Plan→Research→Review→Answer** scaffold this handoff uses, but treats **rubrics as the shared interface** structuring policy execution, judge feedback, AND agent memory (a reusable **rubric bank**) — not just a final-answer scorer. Directly informs MD-9 non-structural scoring + the EV-9 rubric contract.
  - Adoptable now (zero-training, Phase-1 style): rubric-as-interface framing + stage-specific reward decomposition + reflection/rubric-bank memory. **Not** adoptable: the RL core (SS-GRPO + reflection meta-policy training) needs GPU training infra we lack — aligns with this handoff's Phase-2 MD-10..13 being GPU-gated/deferred.
  - Reported (OBSERVATION-grade): RubricEM-8B long-form avg 55.5 (beats DR Tulu-8B 53.6, approaches OpenAI Deep Research 59.9 at far fewer params); short-form OOD avg 73.5. Heavy overlap with already-indexed MindDR (intake-438).
- **[declined: ws58 2026-11-03 content-review: merged into MD-9 as a prompt-level arm]** Operator-review candidate (deep-dive 2026-07-11 SHARPENED): **PRIMARY (prompt-level, genuinely new):** rubric-as-**execution**-interface — PlanningNode emits a prospective `<rubrics>` block; DeepSearch loop does per-step `<state_evaluation>` vs rubric; add a **Review stage** (`<rubric_review>` mapping evidence→criteria before ReportSynthesis) — the *sole* scaffold delta vs our 3-node pipeline — plus a Review-stage rubric-adherence EV-9 dimension. **Note:** stage-decomposed *scoring* is already in EV-9 (`rubric_scoring.py`); only SS-GRPO's per-stage credit-assignment is new and it's **RL/GPU-gated (OUT — duplicates MD-10..13)**. **EXPERIMENTAL (adopt cautiously):** a heuristic kb-search rubric bank over `src/trace` — but the paper's own Fig-6 ablation attributes the transfer gain to the *trained* meta-policy and shows an untrained model doesn't benefit, so treat as a falsifiable experiment, not a free win.

#### Research Intake Update — 2026-07-21 (Search-time contamination — the "reliable anchors" need demoting)

- **[intake-877] "Search-Time Contamination in Deep Research Agents"** (arxiv:2606.05241; Tongyi Lab/Alibaba + NTU)
  - Relevance: defines a validity defect that **no part of the MEASUREMENT.md tuple currently captures** — retrieval-environment provenance. An agent searching the live web at inference time can retrieve the benchmark's own metadata, question text, or ground-truth answer instead of reasoning. Three severity tiers: Benchmark Metadata Leakage → Question-Context Leakage → Explicit Answer Leakage.
  - Reported: up to **4 percentage points** of inflation across six public benchmarks; per-agent leakage rates spanning ~0-78% depending on the retrieval stack (so exposure is a property of the *search backend*, not only the benchmark).
  - **Our exposure, assessed concretely — better than feared on MD-8, worse elsewhere:**
    - **MD-8 sentinel is largely NOT exposed.** Its 20 prompts are EPYC-authored *style imitations* of BrowseComp/WideSearch, not verbatim public items, and are graded by an EV-9 rubric with no published answer key. Question-context and answer leakage are therefore mostly inapplicable. It does run live (all 20 executed through SearxNG), which makes those numbers non-reproducible over time — a real but *different* validity problem, fixed by the same transparent-trajectory recommendation.
    - **MD-9's external anchors ARE affected.** This handoff designates BrowseComp 45.7 / WideSearch 46.5 / xbench-DS 75.0 as "the reliable anchors" for the adoption case, against a **+5pp promotion gate**. Up-to-4pp of such published numbers can be contamination — comparable in size to our own gate. Those anchors should be demoted from "reliable" to observation-grade.
  - Caveats: preprint, not peer-reviewed; the benchmark set is clinical/medical-heavy so generalization to BrowseComp/GAIA-style open-web benchmarks is asserted rather than demonstrated; "up to 4%" is an upper bound, not a mean; the lead affiliation also produces one of the benchmarked agents (though it is the primary contaminated subject, so the bias does not flatter them).

- [x] **MD-9 external-anchor demotion:** BrowseComp/WideSearch/xbench-DS are now explicitly observation-grade, not reliable adoption anchors; their possible search-time contamination is comparable to the +5pp promotion margin. The local MD-8 sentinel remains a distinct non-verbatim, trajectory-auditable evaluation surface. ✅ 2026-07-29
- [ ] Operator-review candidate: capture search trajectories (query, URL, snippet) on deep-research eval runs so question-context / answer leakage can be audited post hoc — our SearxNG JSON path already returns `engines[]`/`score`, making this nearly free. [intake-877]
  - 2026-11-02 operator decision: Capture (decisions-batch2-4-20261102.json)

## Track: minimax-h3-video-generation-evaluation
<!-- gate: none -->

> Moved from `handoffs/active/minimax-h3-video-generation-evaluation.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row EVL-32. Sections without open boxes (background, closed ledger) stay in [`../completed/minimax-h3-video-generation-evaluation.md`](../completed/minimax-h3-video-generation-evaluation.md).

#### Open questions / next steps

- [ ] **Scope decision (operator)**: is video generation a product need at all? If not, close this
      handoff — the download is 165 GB on a 92%-full volume, so "interesting model" alone is not a reason. If approved (absorbs six rows): re-check disk headroom, download model_index.json + Ref2VA/* + the beta4 INT8 transformer (~165 GB), serve on the MI210 via SGLang or ComfyUI (confirm single-MI210 feasibility), run a 768p smoke on a small prompt set recording wall-clock/VRAM, audit local output with a content filter, file the intake row, and record the Excluded-Territories license constraint before any production use.
- **[declined: ws58 2026-11-03 content-review: conditional on the operator's scope answer]** If scope approved: re-check disk headroom, then download `model_index.json` + `Ref2VA/*` + the
      beta4 INT8 transformer (~165 GB total)
- **[declined: ws58 2026-11-03 content-review: conditional on scope]** Serve on the MI210 stack via SGLang or ComfyUI (reference deployment is 4×GPU ulysses-degree 4 —
      confirm single-MI210 feasibility with the INT8 transformer before committing; ~2.4 GB/K GPU not
      transferable from the SGLang cookbook without measurement)
- **[declined: ws58 2026-11-03 content-review: conditional on scope]** 768p quality smoke on a small prompt set (T2VA + FL2VA + Ref2VA cases from the model card's
      reproducible scripts); record wall-clock, VRAM, failures
- **[declined: ws58 2026-11-03 content-review: conditional on scope]** Content-filter audit of local output (hosted moderation does NOT apply locally)
- **[declined: ws58 2026-11-03 content-review: conditional on scope]** File the research-intake row when adoption is decided (none exists yet — created directly at
      intake, mirroring intake-937 for ERNIE; verdict will be `new_opportunity` or `already_integrated`)
- **[declined: ws58 2026-11-03 content-review: conditional on scope]** License compliance note for any production use: US/EU/UK/KR are Excluded Territories — use there
      requires the MiniMax application; guardrail-bypass via uncensored LoRAs is an AUP #5 breach
      (governance note only; does not gate the capability evaluation)

## Track: qwen-mtp-llamacpp-port
<!-- gate: none -->

> Moved from `handoffs/active/qwen-mtp-llamacpp-port.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-46. Sections without open boxes (background, closed ledger) stay in [`../completed/qwen-mtp-llamacpp-port.md`](../completed/qwen-mtp-llamacpp-port.md).

#### Remaining tasks

- [x] **P1** Reconcile `common/speculative.{cpp,h}`: merge upstream's `DRAFT_MTP` state machine INTO our version, keeping our EAGLE3 scaffold + tree/DySpec + ngram + suffix paths intact. This is the keystone — most other files follow once the type/enum + state class exist. ✅ 2026-07-11
- [x] **P2** `common/arg.cpp`: extend `--spec-type` enum to include `draft-mtp` (alongside our existing `none|mtp|ngram-*|suffix`); add `--spec-draft-n-max`. Note our fork already has a `mtp` spec-type (gemma4 external) — disambiguate `mtp` (gemma4 external assistant head) vs `draft-mtp` (in-GGUF NEXTN self-draft) or unify. ✅ 2026-07-11
- [x] **P3** `include/llama.h` + `src/llama-context.cpp` + `src/llama-cparams.h`: add the MTP context type + decode/logits MTP APIs; reconcile with our context lifecycle. ✅ 2026-07-11
- [x] **P4** `src/models/qwen35.cpp` / `qwen35moe.cpp` + `src/llama-arch.*` + `conversion/qwen.py`: the Qwen MTP graph (nextn layer) + metadata loader. ✅ 2026-07-11
- [x] **P5** Resolve the remaining backend/test/doc files to compile; `cmake -B build && cmake --build build -j$(nproc)` (CPU: `-DGGML_CUDA=OFF`). ✅ 2026-07-11
- [x] **P6a** Verify help surface: `llama-server --help` / `llama-speculative --help` show `--spec-type draft-mtp` + `--spec-draft-n-max`. ✅ 2026-07-11
- [ ] **P6b** Operator-gated v10-champion (`ffc1bac82`) experimental model-load + gate bench on `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, with matched Q8_0 no-spec vs MTP arms; then the parent T3/T4 benches.
  - 2026-11-02 operator decision: Re-scope to the current (v10) champion and run (decisions-batch2-4-20261102.json) (re-scoped 2026-11-03 from Qwen3.6-35B-A3B Q4/Q4-MTP pair on fresh v8: Q4 deleted, v8 superseded; per operator 2026-11-02 now Qwen3.6-35B-A3B-MTP-Q8_0 on the v10 champion)
- **[declined: ws58 2026-11-03 content-review: optional and low EV by its own text]** **P7 (optional): FR-Spec draft LM-head vocab-trim** (intake-740), only after P6b and only from the v10 champion experimental surface. Build an EPYC-workload-matched frequency map, retain byte-exact temp-0 validation, and measure end-to-end before adopting; historical #22673/EAGLE3 reconciliation assumptions do not apply. (re-scoped 2026-11-03 from fresh v8 experimental surface: superseded, now the v10 champion experimental surface (with P6b))

## Track: strand-rust-coder-rustevo2-verification
<!-- gate: none -->

> Moved from `handoffs/active/strand-rust-coder-rustevo2-verification.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row EVL-45. Sections without open boxes (background, closed ledger) stay in [`../completed/strand-rust-coder-rustevo2-verification.md`](../completed/strand-rust-coder-rustevo2-verification.md).

#### Progress checklist

- [x] Phase A acquisition + sanity (A-1 GGUF, A-2 benchmark/leaderboard, A-3 baselines, A-4 static harness) ✅
- [x] Rust toolchain + Python venv host prereqs installed ✅
- [ ] Phase B single-instance RustEvo2 bench (USER APPROVAL REQUIRED) - Strand, Qwen2.5-Coder-14B base, Qwen3.6-35B-A3B-MTP-Q8_0 worker, sequential (re-scoped 2026-11-03 from gemma4 worker: deleted; now Qwen3.6-35B-A3B-MTP-Q8_0 worker)
- **[declined: ws58 2026-11-03 content-review: merged as its scoring step]** Phase C score table + decision matrix disposition; report base-model number to isolate fine-tune delta
- **[declined: ws58 2026-11-03 content-review: merged as its disposition step]** Push GO/NO-GO disposition into intake-616 and flip swarm-dataset-distillation status if GO

## Track: summary-token-attention-readiness
<!-- gate: none -->

> Moved from `handoffs/active/summary-token-attention-readiness.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-52. Sections without open boxes (background, closed ledger) stay in [`../completed/summary-token-attention-readiness.md`](../completed/summary-token-attention-readiness.md).

#### Gate Criteria (any one triggers activation)

All gating is OR-logic: ANY of these fires → activate the implementation plan below.

- **[declined: ws58 2026-11-03 content-review: readiness criterion, not a task; research intake is the watch]** **Gate A** — Pretrained checkpoint of a model we serve (Qwen2.5/3.5/3.6 family, or any base we already deploy) released with KSA-style summary tokens OR GSA-style gist tokens
- **[declined: ws58 2026-11-03 content-review: readiness criterion, not a task]** **Gate B** — Community llama.cpp PR adding general support for: (i) dynamic top-k chunk masking + raw-KV restoration (covers GSA), or (ii) chunk-aligned summary KV cache layout (covers KSA)
- **[declined: ws58 2026-11-03 content-review: readiness criterion (GPU for CPT: training, out of scope)]** **Gate C** — GPU acquisition that lets us run our own CPT (covers KSA's three-stage recipe AND GSA's Stage-1-only recipe). Cross-ref `project_dgx_spark_target` memory.
- **[declined: ws58 2026-11-03 content-review: readiness criterion, not a task]** **Gate D** — Major-lab next-generation model adopts summary-token attention as default architecture (e.g., Qwen 4 with KSA, DeepSeek-V5 with summary tokens). Triggers automatic engagement when GGUF support lands.

## Track: tidar-one-pass-variant-b
<!-- gate: none -->

> Moved from `handoffs/active/tidar-one-pass-variant-b.md` @ `8827db1c6c80` (BRF-T1-MEQ, operator D2); former row INF-53. Sections without open boxes (background, closed ledger) stay in [`../completed/tidar-one-pass-variant-b.md`](../completed/tidar-one-pass-variant-b.md).

#### Waypoints

- [x] **W1 — static mask-complexity analysis** (~1 day, no inference, ungated): TiDAR-pattern vs Linear-SS mask ggml-op complexity per deep-dive §10.4.2/§10.5 step 1 — read the antirez fork + intake-635 minimal reimpl for the mask trick, Nemotron paper §4.2 for the Linear-SS shape. Acceptance: written comparison; if comparable, Variant B is strictly cheaper than Variant A long-term on CPU. ✅ 2026-07-22
- **[declined: operator 2026-11-03 model-audit: operator: TiDAR W2-W4 checkpoint-gate watch declined]** **W2 — checkpoint gate + Q4 quality validation** (bench-only when gate fires): watch for a Q4_K_M-quantizable TiDAR-class checkpoint (none exists today — deep-dive §10.4.3 calls this question dormant until then); on release, quantize and measure the quality delta (TiDAR-8B showed 6–9% HumanEval/MBPP loss at BF16; the gap may widen under Q4). Acceptance: go/no-go quality verdict recorded with eval protocol.
- **[declined: operator 2026-11-03 model-audit: operator: TiDAR W2-W4 checkpoint-gate watch declined; gated on W2]** **W3 — ggml-op implementation** (5–10 days, gated on W2 go): unified causal+bidirectional mask single-forward draft+verify path in the experimental fork (per `feedback_experimental_repo`). Acceptance: correctness vs reference AR output; acceptance-rate instrumentation in place.
- **[declined: operator 2026-11-03 model-audit: operator: TiDAR W2-W4 checkpoint-gate watch declined; gated on W2]** **W4 — canonical bench + decision memo** (~1 day): end-to-end decode vs AR baseline per the canonical protocol; synthesize into the Variant A vs B memo per deep-dive §10.5 step 4. Acceptance: claim filed per MEASUREMENT.md grammar; promote/park decision recorded.

## Track: meq-carve-gpu-serving-tie-in-program
<!-- gate: none -->

> Carved from `handoffs/active/gpu-serving-tie-in-program.md` (since folded into `mi210-serving-program.md`, row INF-22) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 3 box(es) moved verbatim with their IDs, in source order.

- [ ] **P3-5 (NEW 2026-10-20) — re-seat the bake-off arms; P3-1 cannot run as written.** All three gpu_shadow_lane tenant GGUFs were deleted in the operator-approved 2026-10-20 disk reclaim: stock `Qwen_Qwen3.6-27B-Q8_0.gguf`, FF `Qwen3.6-27B-Fable-Fus-711-...-Q8_0.gguf` and its `-MTP-Q8_0` build (graveyard rows in the research registry, research `2bc4fe3ca`). The served 27B is now Qwen3.8-27B (operator: "we use qwen3.8 now"). Choose the new arms (e.g. the on-disk Qwen3.8-27B Q8 MTP, or a re-download) as a decision package for the operator. Then update `orchestration/gpu_shadow_lane_tenancy.yaml`, `gpu_shadow_lane_np_ceiling.yaml` (new np_ceiling rows need measurement) and `scripts/server/gpu_shadow_lane.py` `TENANT_CANDIDATE_MODEL`, which carry dated deleted-weights comments since orch `9fbcbcf3`.
  - [Arm-selection decision package](../../docs/design/gpu-serving-p3-5-arm-selection.md): recommends Qwen3.8-27B versus the existing A4 bridge as a sequential control, subject to artifact and recipe verification. The operator's arm choice remains outstanding; neither this recommendation nor the incumbent's presence authorizes configuration or traffic changes.
  - 2026-11-02 operator decision: Qwen3.8-27B vs the A4 bridge as sequential control (package recommendation) (decisions-batch2-4-20261102.json)
- [x] **GPU-LOOP-2 — Looped small model as a reliability-boosted batch worker on the MI210: quality vs loops vs aggregate throughput against equal-cost dense and K-sample controls (intake-2585#record, intake-2547#record, intake-2551#record).** Question: at high concurrency (elastic-duty D1 batch-shedding class, np 16), does Ouro-1.4B (and 2.6B-Thinking as second tier) at 1/2/4 loops buy more correct worker answers per HBM byte than a non-looped model? Arms, served-cost arithmetic at np=16, C=1k, f16 KV (ideal step times, to be measured in GPU-LOOP-1): A1 Ouro-1.4B L=4 (5.76 GB weights/step + 12.9 GB KV, 13.0 ms, 1,230 tok/s); A2 L=2 (about 2,300); A3 L=1 (about 7,100 on the same weights); A4 Ouro-2.6B-Thinking L=4 (48 layers, about 11.3 GB weights/step, 1.5 MiB/token KV); C1 Qwen3-4B-Thinking-2507 Q8 (4.28 GB, 144 KiB/token, 3,420 tok/s, the equal-quality-class dense control); C2 Qwen3-1.7B Q8 majority-of-4 (about the same bytes per final answer as A1, 1,545 answer-equivalent tok/s: the K-sample route that the idle MFMA headroom makes free); C3 Qwen3-1.7B Q8 single sample (equal resident bytes); C0 the incumbent worker, Qwen3.6-35B-A3B on CPU :8070 (registry roles.worker_general.performance.quality_pct is null: it has never been scored on the worker battery, so it is measured here on the same frozen items). Frozen inputs: GSM8K-style math (n>=200, same problem list as the PR so the 26.0/67.0/80.5 published curve is a replication check) plus worker-battery items for explore, summarize, transform and strict tool-call JSON (n>=150 per suite), item list and scorer hashed before any generation; Ouro context stays under its trained 1024-token block (Ouro RECIPES: block_size 1024), longer prompts are a separate reported stratum. Per arm: pass@1 over 3 seeds, seed-to-seed agreement, JSON-validity rate, aggregate tok/s at np 16, wall-seconds per correct answer and correct answers per HBM GB moved; per-item raw outputs kept; correctness legs may share the card with :8083, throughput legs run in a GPU window with the host threads under the q3 claim. Controls: frozen inputs, incumbent baseline (C0 and C1), per-item raw outputs, 3-seed repeat with the A/B order alternated, full denominator including parse failures, predeclared rule. Decision rule: an Ouro arm earns a shadow-lane tenancy row (D3 shadow-only, no production traffic) only if (i) its paired accuracy vs C1 is within 2 points (McNemar not worse) and its seconds per correct answer at np=16 is at most 1.5x C1, or (ii) it beats C1 by at least 5 points at paired p<0.05 at no more than 2.5x C1 cost; the arithmetic predicts A1 costs 2.8x C1 per token, so (i) needs a real quality edge. Otherwise record NO-GO with the table and keep Ouro only as the vehicle for GPU-LOOP-3. Depends on the GPU-LOOP-1 build (our own task, not an external event). ✅ 2026-11-10 CLOSED AS DEPRECATED (operator decision 2026-11-10: all tasks for the Ouro-1.4B and Nanbeige4.2 models are deprecated; their GGUFs are not on disk and will not be downloaded). History below is retained. [no-belief: deprecated by operator]
- [ ] **GPU-PLT-1 — LoopCoder-v2 (7.6B PLT coder, Apache-2.0) quality screen on the MI210 through transformers custom code, before and independent of the GGUF port (intake-2584#record, intake-2571#record).** Load Multilingual-Multimodal-NLP/LoopCoder-V2 at the pinned HF sha b87cf3a (BF16, 7,615,749,680 params, 15.2 GB, fits the about 19 GiB headroom beside :8083 without a KV problem) in an isolated venv with the transformers version its configuration_iquestpltcoder.py needs (Ouro needed 4.57.x, the research venv has 5.15.0: do not assume); confirm torch.version.hip and bf16 on gfx90a first; read config.json to see whether the loop count is a config field (the paper trains R=1..4 as separate models, so a forced R=1 on the released weights is not the paper R=1). Frozen inputs: HumanEval+ (164), LiveCodeBench subset released after the model cutoff (n>=200), BigCodeBench-hard subset, plus the frozen coder-suite items used for coder_escalation (cruxeval and the others E-7 scored: math 85.0, mmlu_pro 27.5, gpqa_diamond 47.5, cruxeval 22.5 at terse template 1443ea9ab4bb). Arms: LoopCoder-v2 as released; incumbent coder_escalation Qwen3.8-27B Q8 on :8083 (same harness, thinking off and medium); frontdoor Qwen3.6-35B-A3B on CPU; size control Qwen3-4B-Instruct-2507 (on disk). Controls: frozen items and scorer hashes, incumbent baselines, per-item raw outputs, 2 seeds, full denominator, rule below. Replication check against the paper own table: R=2 reports HE+ 84.1, LCB 35.4, BCB 46.1 and SWE-bench Verified 64.4 (harness unnamed, single seed, vendor-authored); accept the replication if HE+ >= 80 and the LCB subset score is within 5 points of the paper 35.4 after harness adjustment stated. Decision rule: open the serving legs of GPU-PLT-2 (agentic SWE-40 on the same scaffold that scored Qwen3.8-27B 21/40 = 52.5%, shadow lane only) if pooled pass@1 over HE+ and LCB is non-inferior to Qwen3.8-27B within 8 points (paired bootstrap lower bound) or the replication check passes; otherwise record NO-GO with the table (the port of GPU-PLT-2 still completes as parity work). Arithmetic that motivates it: at np=16, C=8k, Q8 (about 8.1 GB incl. head, KV 56 KiB/token f16 because later loops share loop-1 KV and keep only a 64-token window) a PLT-2 step is about 15.2 GB / 1433 GB/s = 10.6 ms bandwidth vs 2.5 ms compute at 32 rows, i.e. 1,510 tok/s ideal aggregate (about 600 derated by the 27B np8 ratio 157/400), vs 94 tok/s live at 4 concurrent on the 27B. [check: which lineup role would LoopCoder-v2 be a candidate for, against which incumbent and threshold? Same question as mi210 GPU-PLT-2; if none, retire]

## Track: meq-carve-gpu-acceleration-path
<!-- gate: none -->

> Carved from `handoffs/active/gpu-acceleration-path.md` (since folded into `mi210-serving-program.md` § Track: gpu-acceleration-path, row INF-22) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 2 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: duplicate — mi210-serving-program PF1 arm A2 (-ngl 99 -ncmoe) is this probe on the served model]** intake-310 -ot exps=CPU / --n-cpu-moe hybrid MoE offload probe on MI210
  - PRIOR (2026-09-07, first real-hardware measurement of exactly this comparison — it moves the probe's expected value DOWN, the useful direction): Gemma-4-26B-A4B, same GGUF, llama.cpp b10630, RX 9060 XT 16 GB on a 6-core/32 GB host — offload 62–73 tok/s vs --n-cpu-moe 15.0, and fully-resident llama.cpp still beat it at 84.8. TWO MANDATORY SCOPE LIMITS: the model FITS in VRAM there, and the 15.0 baseline is 6 cores of dual-channel memory against our 48.5 t/s on the same model family. Carrying artifact is the fork README, not issue #122. intake-1343#03.
- [x] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1). ✅ 2026-11-10 CLOSED AS DEPRECATED (operator decision 2026-11-10: all tasks for the Ouro-1.4B and Nanbeige4.2 models are deprecated; their GGUFs are not on disk and will not be downloaded). History below is retained. [no-belief: deprecated by operator]

## Track: meq-carve-eval-tower-verification
<!-- gate: none -->

> Carved from `handoffs/active/eval-tower-verification.md` (since folded into `eval-tower-program.md`, row EVL-14) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 2 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: merged into S-06 (build the GGUF, then the server config)]** Add server config for ThinkPRM in `orchestrator_stack.py` (load only during T2 eval, unload main models — sequential loading per memory note) [too-big: shared-runtime unload lifecycle requires serving owner]
- **[declined: ws58 2026-11-03 content-review: curiosity; no verification gate names it]** Integrate Ouro-2.6B (P7) as T0 sentinel verification candidate

## Track: meq-carve-multiscreen-attention-evaluation
<!-- gate: none -->

> Carved from `handoffs/active/multiscreen-attention-evaluation.md` (since folded into `attention-matching-kv-compaction.md` § Track: multiscreen-attention-evaluation, row INF-05) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: a 1B research model with no lineup role; its downstream HRM-2/HRM-3 were retired]** **HRM-1**: Pull `huggingface.co/sapientinc/HRM-Text-1B` and run a **fair head-to-head against `Qwen3.5-1.7B-Instruct`** on our benchmark suite (MMLU, ARC-C, GSM8K, MATH, DROP — the same reported suite, plus our REPL/tool benchmark for cross-coverage). The apples-to-oranges concern is the headline-killer; resolve it before any downstream decision. Inference path: transformers-library CPU (no llama.cpp option today). Effort: low — public weights, public eval scripts, runs on EPYC CPU at maybe 5-10 t/s like Ouro. Owner: TBD. **Gates**: HRM-2, HRM-3.

## Track: meq-carve-speculative-decoding-mtp-refresh
<!-- gate: none -->

> Carved from `handoffs/active/speculative-decoding.md` (in `speculative-decoding-mtp-refresh.md`, row INF-50) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 2 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: "low EV" by its own text; the 35B MTP recipe is already production]** **T4 (after T2 binary, low EV) — gate-bench Qwen3.6-35B-A3B** (Block C) for frontdoor/coder; same-quant Q8_0 MTP diagnostic on the v10 champion, merged with P6b + MoE-on-CPU skepticism. **2026-07-17 artifact audit:** no Qwen3.6-35B-A3B Q4 or Q4-MTP GGUF is present under `/mnt/raid0/llm/models` or the old LM Studio cache; only Q8 frontdoor files and a stale HF metadata stub remain. Do not burn a quiet window on a Q8-vs-Q4 mismatch or call same-Q8 diagnostics the T4 gate. T4 is artifact-blocked until a matching Q4 no-spec / Q4-MTP pair is available, or explicitly re-scoped to a same-quant Q8 diagnostic. (re-scoped 2026-11-03 from Q4 and Q4-MTP pair: deleted; now a same-quant Q8_0 MTP diagnostic on the v10 champion, merged with P6b)
- **[declined: operator 2026-11-03 model-audit: Laguna weights not on disk and no Laguna role; 128 GB pull on a 92%-full volume; production DFlash2 is Qwen3.8-27B]** Bench DFlash accept-rate on Laguna: {Q8_0, Q4_K_M, IQ2_M} target x BF16 DFlash drafter. PRECONDITION: download Q8_0 (128GB) after architect benches free disk. Reopen the March NO-GO (`../completed/dflash-block-diffusion-speculation.md`) only if the Q8_0 target recovers per-token acceptance toward ~60%. **Causal correction 2026-07-29:** target-side quant noise in conditioning hidden states remains a hypothesis, not an established root cause: Laguna moved only 17.2% (Q4) → 19.0% (Q8), and BF16/F16 targets remain untested. The BF16 drafter alone cannot settle a target-side effect; treat acceptance as the gate rather than presuming its cause.

## Track: meq-carve-glm52-reviewer-capability-gates
<!-- gate: INF-77 -->

> Carved from `handoffs/active/reviewer-control-plane.md` (in `glm52-reviewer-capability-gates.md`, row REV-02) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- [ ] **GC-6 — Evaluate the two-axis reviewer split** (model-agnostic; carries over to the 2026-09-22 DeepSeek-V4.1-Flash retarget unchanged) (intake-1304, intake-1305; 2026-09-07). Split
  review into two independent reviewers — one checks that the artifact *says what was asked*
  (faithfulness), the other checks *quality* — with both required to approve, against our current
  single-reviewer gate. The source ran this at scale: reviewers were 13,602 of its 30,046 agent runs,
  i.e. 45% of all runs were review passes, which is a real cost this evaluation must price. **Weigh
  it against the counter-evidence in the follow-up system:** stricter review there produced an
  adversarial dynamic in which workers "hide axioms in increasingly subtle ways", so the question to
  answer is whether a second axis buys fidelity or merely displaces evasion into a subtler form.

## Track: meq-carve-typed-decision-plane
<!-- gate: none -->

> Carved from `handoffs/active/typed-decision-plane.md` (since folded into `routing-program.md` § Track: typed-decision-plane, row RTG-09) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.

## Track: meq-carve-routing-intelligence
<!-- gate: UFH-01#agentic-serving-harness-fixes -->

> Carved from `handoffs/active/routing-program.md` (in `routing-intelligence.md`, row RTG-30) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: monitor-only by its own text ("do NOT open")]** **RI-CMP-1** — file LFM2.5-Encoder-350M-Prompt-Router as a `monitor_only` comparator against the MLP learned-routing controller. Do NOT open a work item: Phases 1.5-3 are unfinished and this is a comparator, not a replacement.
  - *2026-09-23 (intake-1502, intake-1501):* also file Laya (laya / laya-multilingual) as a `monitor_only` comparator — near
    chance zero-shot on routing (DDnim tier 9/20 and 5/20), its worst-calibrated bucket (choice:11+) is where an 11-way
    routing choice lands, and it re-encodes the state per question. Not a work item.

## Track: meq-carve-memento-block-reasoning-compression
<!-- gate: none -->

> Carved from `handoffs/active/memento-block-reasoning-compression.md` (since folded into `context-and-token-economy.md` § Track: memento-block-reasoning-compression, row RTG-08) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: Memento S2 was declined by the 2026-11-03 model audit]** S2 Stage-1 format-learning smoke on Qwen3-0.6B (fill compliance/compression/MATH-500 table)
      **Pipeline PROVEN end-to-end 2026-08-12** (`mainC`, research `c62ba27e`) — but the table stays
      empty deliberately. At **16 optimizer steps** a format-compliance number would read ~0% and would
      later be cited as *"Memento format learning failed"*; that column needs a real run, not a smoke.
      The one solid figure is **compression ratio 5.91×** (corpus block:summary tokens, 300 records) —
      a dataset ground-truth property with no model involved. Loss 1.354 → 1.249 is a drift, **not** a
      convergence claim. Adapter verified real: 336 tensors all finite, **168/168 `lora_B` off zero
      init**, so weights genuinely updated.

## Track: meq-carve-frontier-f3-data-flywheel
<!-- gate: none -->

> Carved from `handoffs/active/frontier-f3-data-flywheel.md` (since folded into `frontier-lab-automation.md` § Track: frontier-f3-data-flywheel, row EVL-29) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

  - [x] Repeat the W3(a) fit check on the real Qwen3.5-9B once its HF weights are local (~19 GB download, operator
    approval) — only if the 9B answer itself is wanted rather than this bound. [declined: operator 2026-11-03 model-audit: conditional on wanting the 9B answer; Qwen3.5 family retired and deleted, the bound already answers it]

## Track: meq-carve-tq3-quantization-evaluation
<!-- gate: none -->

> Carved from `handoffs/active/tq3-quantization-evaluation.md` (since folded into `quantization-and-low-bit.md` § Track: tq3-quantization-evaluation, row INF-80) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: operator 2026-11-03 model-audit: Bonsai-27B and Ternary-Bonsai-27B deleted 2026-09-01; failed strict quality gate, no named fix]** Parked operator-review candidate (re-scoped 2026-07-19): the GGUFs already EXIST and are public (`prism-ml/Bonsai-27B-gguf` Q1_0 ~3.8 GB; `prism-ml/Ternary-Bonsai-27B-gguf` Q2_0 ~7.17 GB). The **1-bit Q1_0** variant is v7-loadable and partially coherent, but the first CPU+MI210 strict-output gate failed instruction-format compliance; reopen only on a named prompt/template/protocol fix, not broader speed or generic quality churn. The **ternary Q2_g64** variant is acceleration-interesting with MI210 `ngram-mod` on structured-copy tasks, but also failed strict quality and is not role-ready; reopen only on a named quality/protocol fix. The **ternary Q2_0** headline variant is verifier-confirmed noncanonical under current v7; reopen only after an explicit producer/export fix, transcode, or compatibility-loader decision, not ordinary CPU/MI210 smoke retry. NB: quality is self-reported **and independently contested** (gibberish/hallucination/tool-call-collapse reports; no third-party reproduction of the 80.49 avg) — treat as a footprint/density experiment, not a quality win. Append every reopened probe to `docs/reference/model-probe-scoreboard.md`.

## Track: meq-carve-multimodal-pipeline
<!-- gate: none -->

> Carved from `handoffs/active/multimodal-pipeline.md` (since folded into `speech-and-multimodal.md` § Track: multimodal-pipeline, row INF-79) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: a note, not a task]** Keep Z-Image-Turbo as a LATENCY candidate only, decoupled from quality (6B vs 8B, GGUF 2.59-6.58 GB, apache-2.0, runnable on today's binary) against the ~3 min @1024² CPU problem. Any trial must repeat the Q8-vs-Q4 A/B locally.

## Track: meq-carve-opendataloader-pipeline-integration
<!-- gate: none -->

> Carved from `handoffs/active/opendataloader-pipeline-integration.md` (since folded into `knowledge-pipelines.md` § Track: opendataloader-pipeline-integration, row PIP-04) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: knowledge-pipelines resolved this 2026-07-29 (not odl_bench swaps); conditional on a Phase D outcome]** **P1 — evaluate MinerU2.5-Pro (1.2B) and GLM-OCR (0.9B)**: check single-pass vs pipeline architecture and llama.cpp/GGUF availability first; create one intake entry per candidate before measurement.

## Track: meq-carve-document-parser-table-bench
<!-- gate: none -->

> Carved from `handoffs/active/document-parser-table-bench.md` (since folded into `knowledge-pipelines.md` § Track: document-parser-table-bench, row PIP-04) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: conditional on Phase D; refile then]** Only if PaddleOCR-VL underperforms: consider **MinerU2.5-Pro** or **GLM-OCR**. Architecture pre-check already done 2026-07-20 (below) — **neither is single-pass**, so neither is an `odl_bench` model swap. Nothing to download until a pipeline harness is scoped.

## Track: meq-carve-fable5-window2-findings-05c-mi210-lever-category-matrix
<!-- gate: none -->

> Carved from `handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md` (since folded into `mi210-serving-program.md` § Track: fable5-window2-findings-05c-mi210-lever-category-matrix, row INF-22) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 10 box(es) moved verbatim with their IDs, in source order.

- **[declined: ws58 2026-11-03 content-review: needs a trained head; no task]** **EAGLE-3 on pure-dense** (L10) — needs a trained head + relax `target_layer_ids_n==3`; also gemma-MoE untested.
- **[declined: ws58 2026-11-03 content-review: its subjects (122B, GLM IQ2) are deprecated/storage; a lever category, not a task]** **GPU-draft / CPU-target spec** (L18) — for overflow-to-CPU MoE (122B, GLM-5.2 IQ2) and CPU-target GDN roles.
- **[declined: ws58 2026-11-03 content-review: operator kept Nemotron Diffusion out of production roles (2026-11-02); no path, no task]** **Diffusion serving path + all DiT levers** (§3.5) — no path exists yet.
- **[declined: ws58 2026-11-03 content-review: duplicate of the VL vision-encoder prefill baseline row below]** **Auxiliary baselines (BGE encode, VL prefill)** (§3.6) — BGE measured; VL remains open in the nested baseline task below. Do not duplicate the BGE run.
- **[declined: ws58 2026-11-03 content-review: a lever-category note, not a task]** **Dense-Q4_K / K-quant** — the registry **default** quant (Q4_K 291 hits), a distinct 33%-roofline dequant regime where L1 barely applies (+5.8% vs +17–32% Q8). Treated as a lever, is really a category.
- **[declined: ws58 2026-11-03 content-review: a lever-category note, not a task]** **Pure-MoE vs GDN-hybrid-MoE split** inside "MoE-on-GPU-decode" — the campaign's own sharpest distinction (spec-dec viable + 5.9–8.6x scaling for pure-MoE vs net-negative + 3.4x for GDN-hybrid-MoE).
- **[declined: ws58 2026-11-03 content-review: a lever-category note; the live work is quantization-and-low-bit]** **Sub-4-bit / IQ codebook quant** — architecturally different dequant kernel from K-quant block dequant; the bytes/token axis deciding 64 GB fit.
- **[declined: ws58 2026-11-03 content-review: a lever-category note, not a task]** **Lightning / linear-attention hybrid** (Ring, bailingmoe_linear) — a third distinct linear kernel, neither delta-net nor Mamba2.
- **[declined: ws58 2026-11-03 content-review: a lever-category note; the concrete half is the VL encoder baseline row]** **VL split** (ViT vision-**encoder** prefill = compute-bound MFMA target; VL decoder = full MoE/dense decode; spec-dec mmproj-forbidden) — currently hidden inside "Auxiliary(vision)."
  - [ ] **VL vision-encoder prefill baseline — the unrun half of A3.** 2026-08-12 ran the BGE encode half only (13 GPU points, `artifacts/gpu-aux-baselines/a3_bge_mi210_20260812.jsonl`, commit `182f30b6`): bge-m3 Q8_0 and f16 land within noise at every sequence point, so **the quant lever is inert on encode** and buys memory, not speed. The VL prefill half was never run and is the compute-bound MFMA regime where L16's bf16-vs-Q8 crossover is actually testable — the row's own ⚙︎corrected note says VL prefill, not the decode tail, is the correct auxiliary analog. Needs a dedicated encoder-timing harness and a GPU window. Local starting pair: `/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf` and `mmproj-Qwen3-VL-30B-A3B-Instruct-F16.gguf`. Prepare fixed image inputs and measure vision encoding separately from decoder prompt processing; the production `libmtmd.so` contains the native `image slice encoded in ... ms` timing string. Bind binary and model provenance and sample GPU residency during the run. The available projector is F16 only, so a Q8-versus-bf16 projector crossover is not established by this baseline.
- **[declined: ws58 2026-11-03 content-review: a lever-category note, not a task]** **ASR / speech encoder-decoder** (Whisper large-v3-turbo) — conv frontend + bidirectional encoder + cross-attention decoder fits none of the 6 buckets.

## Track: meq-carve-reboot-gated-inventory-and-staging
<!-- gate: INF-06#autokernel-research-loop, INF-45#numa-placement-and-contention, INF-45#batched-decode-measurement, INF-86, INF-45#numa-placement-defect-20260730, INF-45#shape-keyed-contention-gating, INF-87, RTG-34#coordination-and-churn-pipeline, RTG-34#churn-pipeline, RTG-34#dashboard-architecture-restructure, RTG-34#handoff-index-and-backlog-graph -->

> Carved from `handoffs/active/numa-placement-and-contention.md` (in `reboot-gated-inventory-and-staging.md`, row EVL-49) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- [ ] **S-06 — Build the ThinkPRM-1.5B Q4_K_M GGUF and land the EV-5 wiring** (HF pull →
      `convert_hf_to_gguf.py` → `llama-quantize`; `orchestrator_stack.py` sequential-load config;
      `eval_t2()` uncertain-question selection + P(yes) extraction; wire the existing
      `check_cross_family()`). Zero inference; it is the acknowledged blocker on the largest gated
      cluster.

## Track: meq-carve-repl-turn-efficiency
<!-- gate: none -->

> Carved from `handoffs/active/harness-program.md` (in `repl-turn-efficiency.md`, row EVL-37) @ `1879577612a6` on 2026-11-03 (BRF-T1-MEQ, operator D2; carve list `fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ). The gate above is that unit's gate, so readiness is unchanged. 1 box(es) moved verbatim with their IDs, in source order.

- [ ] Add the intake-537 **open-source-hardened RLM system prompt** (tuned on Minimax-M2.7 / GLM-5.1 — the only RLM prompt in the corpus tuned for open-weight drivers) as a third A/B arm beside the promoted SkyRL child prompt. Its distinctive lever is a **verbatim-slice return** instruction that suppresses sub-agent decode.

## Track: gpu-candidates-surface-qwen38-update
<!-- gate: none -->

> Folded from `handoffs/active/gpu-candidates-surface-qwen38-update.md` @ `063fc7a23b98` on 2026-11-03 (BRF-T7-F8, route 1b, operator D1/D5; retired row INF-61 → EVL-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### GPU Candidates surface — add Qwen3.8-27B as the new stock-27B arm

> Model-evaluation queue file (BRF-T1-MEQ, operator D2): the group gated on INF-60 (row INF-61). It merges into [model-evaluation-queue.md](model-evaluation-queue.md) at BRF-T7-MEQ.

**Status**: ACTIVE — SWE rung complete; best-configuration refreshes remain (2026-08-20). The devcontainer blocker cleared; both protocols are
now scored and in the artifact. **Agentic SWE-40 = 21/40 (52.5%)** — re-run after fixing the harness
tool-call parser (`3bf16c3f`), superseding the provisional 15/40. **Oracle SWE-40 = 20/40 (50.0%)** vs
stock 27B's 23/40 — a **non-resolving** difference (paired exact McNemar p = 0.375, 5 discordant), so
read it as a tie on SWE, not a regression. Remaining: re-collect the 24-cell grid at the measured
`n-max 8` optimum (the grid was captured at 4, ~8.7% below peak).
**Created**: 2026-08-14
**Priority**: P2 (presentation surface; not evidence authority)
**Effort**: Low — re-populate one candidate row with already-partial Qwen3.8-27B data + fill the gaps

#### NEXT STEP — top of queue

Re-collect Qwen3.8's 24-cell np × depth grid at measured `n-max 8`, then depth-sweep the other arms
under their own best draft settings. The existing Qwen3.8 grid used `n-max 4`, about 8.7% below peak.
Do not rerun the closed SWE protocols or revive the cleared devcontainer/parser blocker.
**2026-09-16:** the n-max 8 grid was re-collected (INF-61, research `0a711890`; see Task). It comes out *below*
the n-max 4 grid at np≥2 (cross-session, so an observation). Before any cells ship, run a same-window
n-max 4 vs 8 ABA at np≥2.

#### The artifact

`/mnt/raid0/llm/tmp/claude-artifacts/np_context_v8_decision.html` — *"GPU Candidates — Throughput &
Model-Selection Surface"* (SHA-256 `816ad5cdd532634edb48f608321fb6ffc3d5546c3ff74aa6c7b54cf0655e6e2b`).
It is the **presentation surface only**; evidence authority is the research bundles
`epyc-inference-research/artifacts/np_context_study_v8_20260727/` (+ `np_context_study_20260723/` for v7),
per `gpu-serving-tie-in-program.md:294`. It currently shows: architect trio (A4 35B-A3B, **Stock 27B dense**,
A1 122B-A10B IQ2) on v7, plus the 27B finetunes (Fable-Fusion, ThinkingCap) and Laguna-S-2.1 IQ2 on v8, each
with the coding ladder (LCB-hard n=53, BCB-hard n=90, SWE-40 n=40), RAG-at-depth, throughput, and MTP
workload-gate.

#### Task

Add **Qwen3.8-27B** as the new "Stock 27B" arm — the direct successor of the `Stock 27B dense`
(= Qwen3.6-27B) row, which is the current coding bar ("Tops SWE + BCB"). The update is a *row*, not a
re-design: same axes, same era-labeling discipline (label the kernel era; never silently re-collect).

#### Equivalent axes + status

| Axis | Qwen3.8-27B status | Note |
|---|---|---|
| Throughput — decode (optimized `draft-mtp`) | ✅ **flat ~45 t/s** single-stream (47.6 @2k → 45.0 @32k) | 24-cell np × depth sweep on **real olympiadbench prompts**, v9 `0db32c06e`/`10125` |
| Throughput — prefill pp512 | ✅ **727.29 ± 28.00 t/s** | `llama-bench -ngl 999 -nkvo 1 -p 512 -r 3` |
| Coding ladder (LCB/BCB/SWE) | ✅ **RAN** — see *Coding ladder — WAS RUN* below | Originally ⛔ operator-DECLINED ("quality will improve certainly", 2026-08-14); the operator later authorized the ladder anyway ("both rungs, proceed") and it landed. |
| RAG-at-depth | ✅ measured | decode vs context depth is **flat** across 2k–32k on real prompts — no KV-read-cost decay in this range |
| MTP workload-gate (batched vs deep-RAG) | ✅ measured | peak **aggregate 157.3 t/s @np8/2k**; no MTP reversal at depth on real prompts |

> **RETRACTED (2026-08-15/16) — do not cite**: an earlier synthetic sweep reported a decode-vs-depth
> decline (`37.15 @512 → 37.95 @2k → 22.22 @8k → 13.61 @32k`) and an "**MTP HURTS at depth**" workload
> gate (plain beating MTP at 8k/32k). Both were a **synthetic random-word-prompt artifact** — the low
> MTP acceptance came from the random-word prompt, not from context depth. The 24-cell np × depth sweep
> on real olympiadbench prompts supersedes them with the flat curve and 157.3 t/s @np8 peak in the table
> above; those corrected numbers are the ones the artifact ships.

#### Coding ladder — WAS RUN (supersedes the earlier "deferred")

The operator declined the Qwen3.8→Qwen3.6 quality comparison on 2026-08-14, then later authorized the coding
ladder anyway ("both rungs, proceed"). Full architect bench (v9 `0db32c06e`, seeded temp 0.6, MTP, reasoning
off) landed:

| Rung | Score | |
|---|---|---|
| LCB-hard (n=53) | **52.8%** (28/53) | tops the 27B class |
| BCB-hard (n=90) | **31.1%** (28/90) | ties stock 27B |
| SWE-40 (n=40) | **15/40 = 37.5% (provisional)** | agentic, understated — 19/40 empty from format-mismatch, now fixed |
| humaneval | 96.3% (158/164) | |
| aime25 / gpqa (cot) / gpqa (letter) / mmlu_pro / olympiad_hard | 76.7% / 81.3% / 42.4% / 56.7% / 47.1% | |

It is the same LCB-hard n=53 / BCB-hard n=90 / SWE-40 n=40 recipe the artifact already uses, so the
results slot straight into this row.

#### Steps

- [x] **Populate the throughput row** — Qwen3.8-27B flat ~45 t/s MTP decode, pp512 prefill 727 t/s, era v9 `0db32c06e`.
- [x] **Prefill pp512** — `727.29 ± 28.00 t/s` (`llama-bench -ngl 999 -nkvo 1 -p 512 -r 3`).
- [x] **Coding-ladder cell** — populated (LCB 52.8% / BCB 31.1% / agentic SWE 21/40 / oracle SWE 20/40). ✅ 2026-08-20
- [x] **RAG-at-depth + MTP workload-gate** — measured: single-stream decode FLAT ~45 t/s (47.6@2k → 45.0@32k);
  peak aggregate 157.3 t/s @np8/2k. (The earlier "37→13.6 decline / MTP reversal" was a synthetic
  random-word-prompt artifact — corrected; real prompts give a flat MTP curve.)
- [x] **Update the verdict prose** — bottom line + verdict card re-read with Qwen3.8-27B as the new 27B coding bar.
- [x] **SWE-40 finalised on BOTH protocols** ✅ 2026-08-20 — agentic **21/40 (52.5%)** (supersedes the
  provisional 15/40; harness tool-call parser fixed, `3bf16c3f`) and oracle **20/40 (50.0%)**, a
  non-resolving difference vs stock 27B's 23/40 (paired exact McNemar **p = 0.375**, 5 discordant).
- [x] **Artifact reworked to best-configuration results only** ✅ 2026-08-20 — per operator instruction the
  surface tracks the best measured config per arm. Removed: the spec-off baseline column and the
  "N× over plain" ratio, the `FF 27B (non-MTP)` grid, the MTP workload-gate card, and every
  non-best FF rate. Headline is now **70.0 t/s** (dFlash2 block-8, np=1) as best *measured* with the
  parity caveat, alongside **55.46 t/s** as best *selectable*.
- [x] **Re-collect the 24-cell np×depth grid at `n-max 8`** — the published grid was captured at
  `n-max 4`, i.e. ~8.7% under the measured optimum, and its cells were WITHDRAWN from the artifact
  rather than shipped below peak. Needs GPU; blocked only on compute availability.
  - ✅ **2026-09-16 16:16–19:10Z (sub-gpu-runner, INF-61): re-collected on v9 (`0db32c06e`/`10125`, HIP
    binary sha `21cfb750`).** Evidence: research `0a711890`, `data/inf61-q38-np-depth-mtp8-20260916/`
    (`grid_summary.json`). Category CANDIDATE; unit = launch.
    - **Coverage.** 18 launchable cells × 2 passes, 36/36 ok. Residency was proven and host threads fenced to
      184-191 on every launch. The 6 cells np16 @16k/32k and np32 @all L are capacity skips (`failed to
      allocate ROCm0 buffer` at startup).
    - **Results.** Mean aggregate decode t/s (between-launch spread up to 13.6%):

      | np | 2k | 8k | 16k | 32k |
      |---|---|---|---|---|
      | 1 | 46.4 | 45.2 | 44.0 | 45.5 |
      | 2 | 63.0 | 59.8 | 58.0 | 59.1 |
      | 4 | 91.8 | 92.2 | 78.6 | 88.0 |
      | 8 | 112.3 | 99.6 | 97.3 | 95.2 |
      | 16 | 116.8 | 97.2 | — | — |

      MTP acceptance was 0.39–0.47.
    - **FINDING: n-max 8 does not beat the withdrawn n-max 4 grid at np≥2.** Examples: np8/2k 112.3 vs 157.3,
      np16/2k 116.8 vs 153.5, np2/8k 59.8 vs 66.6. Single-stream is level (46.4 vs 47.6 at 2k).
    - **Caveats.** This comparison is cross-session (2026-08-15, one launch per cell, different containment),
      so it is an observation, not an ABA result. Each launch runs only `np` questions, with heavy
      truncation at 2k. The 2026-08-15 grid also launched np32 @2k (141.1 t/s), which OOMs at startup
      under n-max 8.
    - **Consequence.** Do not ship these cells as "best config" without a same-window n-max 4 vs 8 ABA at
      np≥2. The single-stream n-max 8 optimum may not hold for batched serving.
- [x] **INF-61-ABA — same-window MTP n-max 4 vs 8 ABA at np>=2 on Qwen3.8-27B** before any grid cell ships.
  The re-collected n-max 8 grid (research `0a711890`) sits below the withdrawn n-max 4 grid at np>=2, but only
  across sessions. The A/B/A is operator-approved; it waits for the operator to lift the 2026-09-17 GPU hold.
  Filed 2026-09-17. [declined: operator 2026-11-03 model-audit: MTP is not the served spec mode for Qwen3.8-27B: operator 2026-10-01 'ALWAYS use dflash2', architect_critic drafter_selection=dflash2 in stack_topology.yaml]
- [x] **Depth-sweep the other arms (A4, A3, A1, FF, Laguna)** — none was ever draft-depth swept, so
  their published figures are best-KNOWN, not best-POSSIBLE. Qwen3.8 gained 8.7% from its sweep
  alone; the same headroom plausibly exists here and would change cross-arm ranking. [declined: operator 2026-11-03 model-audit: arms A4/A3/A1/FF/Laguna deleted or retired; Qwen3.8-27B was already swept]
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** **Restore the MTP workload-gate finding somewhere durable** — it was removed from the artifact
  because it only exists as a comparison against a non-best config (MTP is net-negative for FF on
  single-stream deep RAG). It survives in this handoff and the wiki, but has no home on any surface.

#### Deps

`INF-60` (qwen38-27b-replace-qwen36.md) — this artifact update is the *presentation* tail of that rollout.

#### Completed 2026-08-15

- **Artifact updated across ALL sections** — `/mnt/raid0/llm/tmp/claude-artifacts/np_context_v8_decision.html`:
  header, new-candidate verdict card, coding ladder (LCB 52.8% / BCB 31.1%), reasoning ladder (aime25 76.7%,
  gpqa 42.4/81.3%), RAG heatmap, full 24-cell GRID, router-integration plan, bottom line.
- **np × depth 24-cell sweep done** (real olympiadbench prompts): single-stream flat ~45 t/s, peak 157 t/s @np8.
  CORRECTED the earlier synthetic "37→13.6 decline / MTP reversal" — that was a random-word-prompt artifact.
- **SWE images built** (40) + **containers started** + **agentic harness (P2e) running** on the 40 instances.
- ~~The coding-ladder cell stays `operator-declined — deferred`~~ — **superseded 2026-08-16**: the operator
  authorized the ladder, it ran, and the cell is populated. See *Coding ladder — WAS RUN* above.

#### Completed 2026-08-16

- Agentic run 1 landed → **21 patches / 19 empty** (format-mismatch, not model failure).
- Harness parser fixed (native tool-call translation, 20/20 unit tests pass) — staged, awaiting commit.
- **SWE-40 = 15/40 (provisional)** written to the artifact; the re-run is parked on the devcontainer restart.

## Track: paw-compiled-specialists
<!-- gate: EVL-08 -->

> Folded from `handoffs/active/paw-compiled-specialists.md` @ `063fc7a23b98` on 2026-11-03 (BRF-T7-F8, route 1b, operator D1/D5; retired row INF-76 → EVL-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### PAW Compiled Specialists — compile-once fuzzy functions on the local stack

> Model-evaluation queue file (BRF-T1-MEQ, operator D2): the group gated on EVL-08 (row INF-76). It merges into [model-evaluation-queue.md](model-evaluation-queue.md) at BRF-T7-MEQ.

**Status**: stub
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Scratch**: `/mnt/raid0/llm/tmp/codex3-paw-hsf-t1-20261030`, `/mnt/raid0/llm/tmp/codex3-paw-standard-r2-20261030`
**Categories**: training_distillation, local_inference, inference_serving, tool_implementation
**Parent index**: [inference-research-index.md](inference-research-index.md)
**Evidence**: intake-811#record (parent paper + 2026-07-11 blocker), intake-1466/1467 (docs + SDK), intake-1477 (Compile by Training), intake-1478/1483 (Standard/Compact compiler weights), intake-1479 (FuzzyBench eval data), intake-1481 (self-hosted compile server, scope-overturned), intake-1482 (independent eval), intake-1484 (.paw corpus)
**Operator steering (2026-09-17)**: PAW links are "relevant for constructing agent loops and making our current agent loops more robust"; the operator likes a GUI separating deterministic flow from fuzzy LLM work (separate stub, UFH-09).

#### Objective

Turn the re-opened Program-as-Weights line into a bounded, licensed-aware decision: can we compile recurring
fuzzy subtasks (tool-output classification, log filtering, JSON repair, routing predicates) into tiny local
specialists that run on the frozen llama.cpp stack, and does the compile-once economics survive on CPU/MI210?
The intake-811 re-open trigger is literally met on artifact availability (weights + FuzzyBench eval data, both
predating the 2026-07-11 blocker); licenses and a self-hosted compile path are the remaining gates.

#### Research Context

| Intake ID | What it settles |
|-----------|-----------------|
| intake-1478/1483 | Standard (Qwen3-0.6B) / Compact (GPT-2 124M) compiler weights public and ungated; NO artifact license |
| intake-1479 | `fuzzy_bench_verified` downloadable (43,128 + 7,550 rows, spec/input/output); no train split; no license |
| intake-1481 | Unofficial MIT self-hosted compile server exists and works for the default Qwen3 compiler; Compact GPT-2 SDK-compat claim overturned; no ROCm proof |
| intake-1482 | Independent eval: standard 94 / finetuned 97 / compact 85 on 100 adversarial cases (one task, n=100, author labels); semantic abstention 98.9% on decided cases; logit-confidence thresholding fails |
| intake-1484 | 7,226 public .paw programs (heterogeneous bundle hygiene, no license) |
| intake-1477 | Self-hosted training-based recipe (teacher synthesis → LoRA on Qwen3-0.6B); no paper memory numbers |

#### Tasks

- [x] **PAW-1 — Artifact-license scope RESOLVED 2026-09-17** (OP-43 closed by operator ruling: "everything we do is internal research"). **Scope ruling: internal research use only** — no redistribution, no deployed-service use, no shipping of compiled programs or adapter outputs. Under this ruling the unlicensed artifacts (intake-1478/1483 weights, intake-1479 dataset, intake-1484 corpus) are usable for all internal work; the license question re-opens only if a distribution/productization path is ever scoped. ✅ 2026-09-17
- [ ] **PAW-2 — Self-hosted compile spike on the target host.** Run the MIT self-hosted compile server (intake-1481#00) with pinned weights (intake-1478#00), mapper and SDK; prove one end-to-end compile producing a modern GGUF-ZIP .paw, then one local call. Measure compile wall time, peak RAM, disk. Document the Compact GPT-2 canonicalization caveat (intake-1481#05) and whether CPU-only execution is workable before MI210.
  - 2026-10-29 (ws58 filer A): `inf76-paw2-20261029` rc0 00:56:25Z, CPUs 24-47, CPU only. The filing manifest has no `decision_rule` (the row says "n/a (feasibility only)"), so this is filed against the box text as a diagnostic observation. One end-to-end compile with the pinned standard compiler (`paw-4b-qwen3-0.6b-20260407`, LoRA kind, pseudo-generator Qwen3-4B max512) produced a modern GGUF-ZIP bundle (`bundle.paw`, 21.8 MB: `adapter.gguf`, `prompt_template.txt`, `meta.json`, `pseudo_program.txt`), and one local SDK call on the `qwen3-0.6b-q6_k` interpreter returned output (`positive`). Measured: 108.0 s wall for compile plus call; sampled process-tree peak RSS 6.16 GB (666 samples, transients can be missed); program store 125.3 MB; compiler weights 8.2 GiB on disk. Meaning: CPU-only compile and execution work on this host before the MI210. Not ticked: the Compact GPT-2 canonicalization caveat (intake-1481#05) is not yet written up here. Evidence `/mnt/raid0/llm/tmp/inf76-paw-runtime-20261029/results/real-1793235276*/result.json`. [belief: cc]
    - **[declined: ws58 2026-11-03 content-review: merged as its caveat]** **PAW-2-fu1 (filed 2026-10-29):** write the Compact GPT-2 1024/2048 canonicalization caveat (intake-1481#05) into this handoff, then tick PAW-2; give any further PAW row a `decision_rule` (this one had none).
- [ ] **PAW-3 — Evaluate compiled programs on FuzzyBench (internal, unlicensed).** Build the eval manifest for `fuzzy_bench_verified` (1479) and record standard-vs-compact capability on our own task slices; replicate the abstention experiment (semantic 3-class vs thresholding) per intake-1482. WIRE THE VIDYA ADAPTER BEFORE THE FIRST RUN (VB-TDP-1).
  - 2026-10-29 (ws58 results filing batch B, diagnostic observation, no tick): `inf76-paw3-abstention-20261029` rc0 complete 01:50:27Z, CPU 24-47, 27 s worker wall, 100/100 cases. It is a prospective re-run of the abstention experiment on the author-labelled 100-case landlord set (intake-1482#record), not on our own task slices; original-archive byte identity is unproven. Binary first-token accuracy 97/100. Semantic 3-class: 88 decided, 12 unsure, 0 invalid; accuracy on decided 87/88 (0.989). Confidence thresholding catches 0 of the 3 baseline errors at 0.60-0.95 (1-12 abstentions) and 1 of 3 at 0.99 (22 abstentions); kept-case accuracy stays 0.966-0.974 at every threshold. This matches the record's direction: semantic abstention works and logit-confidence thresholding does not. No predeclared rule (FILLERS: "n/a (prospective single-domain observation)"), so it is a diagnostic observation. Native record sha `e46ec1b5bd52…`, `claim-tuples.json` sha `a02541ad84d8…` (8 tuples, all graded Judged/Located OBSERVATION) under `/mnt/raid0/llm/tmp/inf76-paw3-abstention-20261029/results/real-179*/`. PAW-3 stays open: the FuzzyBench own-slice evaluation has not run. [belief: cc]
    - [x] **PAW-3 own-slice abstention (filed 2026-10-29, ws58 filer B):** repeat the semantic-vs-threshold comparison on a `fuzzy_bench_verified` slice of our own tasks, with a decision rule declared before the run (for example, the minimum semantic decided-accuracy and maximum unsure-rate), so the transfer question in Open Questions gets a rule-bound answer. ✅ 2026-10-29 — enrolled paraphrase screen supported (7/7 decided, 1/8 unsure); contradiction and sentiment screens not supported. [belief: cc]
      - 2026-10-29 preparation: `codex3-paw3-ownslice-20261029` was published READY for CPU 24-47 and began its official q1 grant at 15:29:43 UTC (ends 17:29 UTC); eight-case rule and case fingerprints enrolled at `5c03cd00835b` without publishing dataset contents. Real launcher smoke accepted the native compile request and generated 187 tokens before rc75 partial cutoff (274.7 s, sampled process-tree peak 3.13 GB); no selected cases or completed compiled program. Separate Q6K interpreter calibration measured 64 tokens including 2048-token prefill in 30.787 s. Paired native capture has synthetic grant-tamper, resume and no-redraw controls; actual own-slice measurement, verdict, and parent PAW-3 work remain open. The completed run retains its scratch evidence and venv; its landed clean runtime worktree was retired on 2026-10-30. The unchanged launcher and ignored-data archives are recorded in `/mnt/micron/codex3-paw-launcher-archive-20261030/RECEIPT.json`. [belief: cc]
      - 2026-10-29 result: **TRANSFER_NOT_SHOWN (reject)** for this exploratory eight-case own-slice, not a general efficacy claim. All 16 arm/case observations complete; semantic 5/8 correct (62.5%, higher better) versus ≥90%, 8/8 decided (≥6), 0/8 unsure (≤25%), 0 invalid. Binary threshold retained/correct: 0.60 8/5, 0.70 5/3, 0.80 5/3, 0.90 4/3, 0.95 3/3, 0.99 3/3; no threshold superiority claimed on n=8. Noise floor not enrolled. `DONE` points to `/mnt/raid0/llm/tmp/codex3-cpu-ready-20261029/results/real-179*//` (native record SHA-256 `89c3206e2c5539dbaa7a71cf791f1c64baef8778cf899e1b2004fdba19491603`; `claim-tuples.json` rule_result). Parent PAW-3 remains open: standard-vs-compact evaluation is incomplete. [belief: cc]
      - Case review: 27587 (fastest runner vs someone faster) and 27585 (most experienced vs someone more experienced) both expected CONTRADICTION but semantic predicted NO_CONTRADICTION; binary also erred on 27587 but correctly identified 27585. 27586 (oldest sibling vs not oldest in country) expected NO_CONTRADICTION, but both arms predicted CONTRADICTION. These suggest failure modes around superlative contradiction and differing comparison scopes; the outputs do not establish a causal mechanism. [belief: cc]
      - **[declined: ws58 2026-11-03 content-review: merged as an interpretation rule]** Prospectively declare a diagnostic with fresh cases separating same-group superlative contradictions from different-group non-contradictions, retain both arm outputs and score against predeclared labels and rule; complete PAW-3 standard-vs-compact own-slice capability evaluation.
  - 2026-10-29 (codex3 preparation): `codex3-paw3-reserve-20261029` enrolled a separate, fixed eight-case paraphrase own-slice with a prospective paired semantic-versus-binary rule in `artifacts/experiments/paw3-paraphrase-ownslice-20261029/predeclaration.json` (enrollment `99d7cc22a5e01eaa906788ceaf4b8ed6b512a018`). Actual R11 launcher smoke accepted the task-specific compile request (HTTP 200), recorded 184 native compiler tokens, and stopped at the bounded window with rc75 and a partial result; 183 token intervals took 210.322 s (0.8701 token/s), sampled peak process-tree RSS 3,137,134,592 bytes, children drained. Synthetic producer and adapter controls passed; no selected case or complete paired program was evaluated, and loop wiring is not claimed. READY packet and native evidence: `/mnt/raid0/llm/tmp/codex3-paw3-reserve-20261029/`. [belief: cc]
  - 2026-10-29 (codex3 preparation): `codex3-paw3-q0-20261029` was published READY for CPU 0-23 with an eight-case sentiment task enrolled at `231c533045acee697214329c1fe0a710f18dfc89`. Its negative/neutral/positive baseline and semantic UNSURE arm are a prospective multiclass extension, not a literal binary replication. The real R11 launcher accepted the compile request, generated 187 tokens and exited rc75 partial at cutoff (274.984 s; sampled process-tree peak 3,117,838,336 bytes; children drained). No selected cases or complete program were evaluated; no verdict or loop-wiring claim. Native evidence and retained private venv are under `/mnt/raid0/llm/tmp/codex3-paw3-q0-20261029/`; the completed run’s clean landed runtime worktree was retired on 2026-10-30 and its unchanged launcher archived under `/mnt/micron/codex3-paw-launcher-archive-20261030/`. [belief: cc]
  - 2026-10-29 result: `codex3-paw3-reserve-20261029` paraphrase binary/semantic-three-class: **TRANSFER_SUPPORTED** under its exploratory eight-case enrolled rule; 16/16 cells, semantic 7/7 decided correct (100%, higher better, ≥90%), 7 decided (≥6), 1/8 unsure (12.5%, ≤25%), 0 invalid. Native binary was 8/8 correct; threshold retained/correct at 0.60/0.70/0.80: 7/7, 0.90: 6/6, 0.95: 5/5, 0.99: 4/4. Noise floor not enrolled; no threshold superiority claim on n=8. Error review: no semantic decided errors; the sole UNSURE was a valid paraphrase involving an allergic person adopting a cat (binary correct at 0.588), and the only non-paraphrase, changing despite to because, was correctly classified by both arms. This supports only the declared slice; standard-vs-compact remains open. Native record SHA-256 `85990d4db84c9fe8b58ec802a295819ad533051f87cf64d14143a9a380ad0110`, `DONE` and `claim-tuples.json` under `/mnt/raid0/llm/tmp/codex3-paw3-reserve-20261029/results/real-*/`. [belief: cc]
    - **[declined: ws58 2026-11-03 content-review: merged as an interpretation rule]** When interpreting the ongoing standard-vs-compact evaluation, retain the abstained coreference/paraphrase case and the despite/because distinction as targeted error categories; do not generalize this 7/7 decided result beyond the selected slice.
  - 2026-10-29 result: `codex3-paw3-q0-20261029` sentiment **TRANSFER_NOT_SHOWN** (reject): 16/16 cells; semantic 3/6 decided correct (50%, higher better, ≥90%), 6 decided (≥6), 2/8 unsure (25%, ≤25%), 0 invalid. This is a native three-label baseline versus four-label semantic extension, not a binary replication. Baseline threshold retained/correct at 0.60/0.70/0.80: 7/3, 0.90/0.95: 6/3, 0.99: 3/2; no superiority claim on n=8. Noise floor not enrolled. Error review: semantic predicted neutral on two cases whose recency-weighted last negative made the expected label negative, and positive on a neutral/neutral/positive weighted tie that required neutral. The two UNSURE cases were a negative expected mixed pair and a neutral expected mixed triple; semantic correctly resolved another mixed weighted tie where baseline predicted positive. These outputs suggest checking weighted counts and tie handling, without establishing cause. Native record SHA-256 `d5e0784311d8c3526ae55f462bcd951499d83f86646ba02a9b85d466871cde38`, `DONE` and `claim-tuples.json` under `/mnt/raid0/llm/tmp/codex3-paw3-q0-20261029/results/real-*/`. [belief: cc]
    - **[declined: ws58 2026-11-03 content-review: merged as an interpretation rule]** Include recency-weighted mixed-sentiment and weighted-tie categories in the interpretation of the ongoing standard-vs-compact evaluation; inspect its actual outputs against the declared task rule before attributing cause.

  - 2026-10-29 capacity checkpoint: two prospective **standard-arm-only diagnostic** shards are prepared; no standard-vs-compact result or parent PAW-3 completion is claimed. Shard A (8 tasks/64 cases) completed the real launcher smoke with 184 compiler tokens, rc75 partial, children drained and 64/64 selected cases unexposed. Owner-reviewed, capacity-gated manifest: `/mnt/raid0/llm/tmp/codex3-paw-standard-20261029/A/REVIEWED-CAPACITY-GATED.json` (SHA-256 `fb3d0221197458bbeaaf968ad5a45b50f3eb01953e7ea87c4b0d3594a1039740`); not published. Shard B (9 tasks/72 cases) remains not ready; its final launcher attempt stopped before model load at the disk guard and no selected cases were exposed. Its schema-only draft is `/mnt/raid0/llm/tmp/codex3-paw-standard-20261029/B/MANIFEST-PRELIMINARY-NOT-READY.json`; it is not publishable. Both use 128-token cap and exact outer-whitespace-trim comparison of native decoded output. Frozen source and digest-only case declarations were committed before case execution in `7328d8641`.
  - Capacity gate and resume: on this checkpoint the filesystem had 162.303 GiB available (174,271,389,696 bytes), below the required **166 GiB** (150 GiB floor plus 16 GiB reservation). Neither shard may launch or publish below that threshold; a single smoke at a time, with headroom and ordinary R11 admission checks. After capacity recovers, qualify the prospective capsule B launcher with `launch.sh --smoke` on `FILLER_CPUS=102,103`, prove actual compile/generation, rc75 partial and drained children with all 72 cases unexposed, then build and review its final manifest and row; do not claim completion from the preliminary smoke. The claims remain `/mnt/raid0/llm/tmp/compute-flags/claims/codex3-paw-standard-a-20261029.codex3` and `/mnt/raid0/llm/tmp/compute-flags/claims/codex3-paw-standard-b-20261029.codex3`. Preserve `/mnt/raid0/llm/tmp/codex3-paw-standard-20261029/{A,B}`, `/mnt/raid0/llm/tmp/codex3-paw3-q0-20261029/.venv`, `/mnt/raid0/llm/tmp/inf76-paw-runtime-20261029`, and `/mnt/raid0/llm/tmp/inf76-paw3-manifest-20261029/prospective-selection.json`; the shard `.venv` links target the retained q0 venv. On 2026-10-30 the clean landed standard runtime tree was retired after its exact commit 50dd278d runtime and original A/B packets were archived under `/mnt/micron/codex3-paw-standard-capsule-20261030/`. Prospective capsule A/B source closures pass; they need new real-smoke qualification and admission before READY, and do not inherit earlier packet warrants. [belief: cc]
- [x] **PAW-4 — Amend the intake-811 blocker record.** ✅ 2026-09-23 — `contradicting_evidence` and `notes` were corrected 2026-09-17; the last stale clause (`recommended_actions`, "closed cloud compiler + no downloadable dataset") now carries the verified status. Replace the stale 2026-07-11 "compiler is CLOSED / no concrete download" text with the verified availability + license + no-official-self-hosted-compile status (index correction; see §7 of the Stage-3 plan file).
- [ ] **PAW-5 — Agent-loop candidates list.** Identify ≤3 recurring fuzzy subtasks in the current agent loops (candidates: tool-output classification, transcript/log filtering, routing predicates; JSON repair was struck 2026-09-29 — `typed-decision-plane.md` TD-21's live shared repair helper owns and solves it) and file each as a compile-once candidate with a direct-model baseline. Do not start compiling until PAW-1 and PAW-2 land.

#### Open Questions

- Does the compile-once economics survive on this host without an accelerator (compile time vs adapter lifetime)?
- Does intake-1482's abstention finding transfer to our task slices, or is it task-specific?
- Is the Qwen3-0.6B interpreter (594 MB Q6_K) fast enough per call for always-on loops versus our current cheap-first models?

#### Notes

Re-open trigger status: MET on availability, NOT met on capability (no official self-hosted compile). License scope resolved
2026-09-17 (OP-43): internal research only — all current work is in scope; distribution would require a grant. The 10M-example
FuzzyBench training set remains unavailable; 1477's recipe is the closest self-hosted path. The 10M-example FuzzyBench training set remains unavailable; 1477's recipe is the closest self-hosted path.

**2026-10-30 PAW standard R2 publication:** A and B were republished from the retained runtime capsule as relocatable CPU packets. Fresh same-launcher controls generated104 and98 compiler tokens respectively, returned rc75 with verified drain, and left all64 A and72 B selected cases unexposed. Their measured smoke rates support only resumable window estimates, not completed compilation or capability conclusions. Both retain the166 GiB admission threshold and predeclared source/cases. [Publication audit](../../artifacts/compute/codex3-publications-20261030-1415.json). [no-belief: bounded preparation; no standard-versus-compact verdict]

**2026-10-30 final T1 status:** the PAW standard A/B successors were re-smoked and published as relocatable diagnostic packets. They remain bounded controls; no compilation completion, capability verdict, or standard-versus-compact conclusion follows. At the 15:54:53Z keeper snapshot, both rows were READY-WAIT while no CPU quarter was free. [T1 successor ledger](../../artifacts/compute/codex3-t1-successors-20261030.json). [no-belief: bounded preparation only]


**2026-10-30 CPU packet checkpoint:** four actual READY packets were published for the dynamic any-cpu-quarter lane: compact PAW shards A/B, the eight-fixed-case superlative control, and DTAP finance R2. The compact A/B real smokes were partial rc75 with 75-token windows; the separate compact-compiler SDK synthetic control passed. These packets support bounded admission/window estimates only; no cohort compilation or quality conclusion is claimed. The superlative packet fixes eight fresh cases and reports descriptive counts without a threshold. PAW parent quality tasks remain open. Corrected keeper-retention evidence confirms all three actual keeper-v6/v7b ready_scan checks succeeded with source unchanged; the superlative row was corrected from 1 GiB to 4 GiB RAM reservation (sampled peak 2,006,925,312 B, approximately 2.288 GB margin; sample is not a hard bound), with final manifest SHA-256 02a6544449cf791cc08d4d524e4fb52e25226d5fe78c70523a8767c5428759af and unchanged launcher. See /mnt/raid0/llm/tmp/codex3-paw-retention-fix-20261030/CORRECTION.json and RAM-VALIDATION.json. [belief: cc]

##### 2026-10-31 compact capability attempts: launcher failures

- **FAILED-RUN, class harness:** `codex3-paw-compact-a-20261030` and `codex3-paw-compact-b-20261030` each ended rc127 before the inner job: `setsid` could not execute the declared `/workspace/repos/epyc-orchestrator/scripts/region-lock` in the host namespace. The predeclared compact-only slices were A: 8 tasks/64 cases and B: 9 tasks/72 cases. Both packet result directories are empty and neither has `DONE`; task exact-match scores and missing dispositions remain unknown, not zero. The inner jobs did not start, so these attempts did not expose their selected cases. Owner action: qualify a host-visible region-lock path and preserve both failed attempts and their original declarations when preparing any successor. No standard-versus-compact or PAW-3 completion follows. [Bounded records](../../artifacts/compute/codex3-paw-pip-filing-20261031-0415/) include digest-only extracts of the two predeclarations (original SHA-256 `9116940efb6793345a9bf16ce403f5267763538131605a13a459beaee7f7932c` and `a1be8ce5785984e93d0b349d32790bc72b5136df63ecdb2c853a6316a72e3e49`) and launcher logs. [belief: cc]

##### 2026-10-31 PAW superlative control — launcher failure

**FAILED-RUN, class harness:** `codex3-paw-superlative-control-20261030` ended rc127 before its inner job when the host could not execute `/workspace/repos/epyc-orchestrator/scripts/region-lock`. The predeclared eight paired cases have no native result files or DONE; arm/category correct, incorrect, UNSURE, invalid and missing outcomes are unknown. Selected cases were not exposed by this attempt. Owner action: qualify a host-visible lock path, preserving the failed attempt and original declaration before any safe successor; no efficacy or superiority conclusion follows. [Bounded receipt and declaration hash](../../artifacts/compute/codex3-filing-hpr-paw-stt3-20261031-0439/). [belief: cc]


##### 2026-10-31 standard A — admission loss after seven program checkpoints

**FAILED-RUN, class admission:** `codex3-paw-standard-a-t1-20261030` ended rc1 at 04:45:26 UTC after 2,414.86 seconds with `RuntimeError('admission lost')`; the declared window ended at 06:00 UTC. The native state retains seven of eight program checkpoints, whose files exist and whose recorded hashes were individually verified by the owner audit. All 64 selected cases are explicitly `not_exposed`, with no case exposure/completion files or DONE. Sampled process-tree RSS peaked at 6,408,986,624 bytes over 12,572 samples, and native cleanup reports children drained. No task exact-match scores or standard-versus-compact verdict exist. [Bounded native result, checkpoint and audit](../../artifacts/compute/codex3-paw-standard-a-filing-20261031-0450/). [belief: cc]

The exact failed admission predicate is **UNKNOWN**: the guard combines captured grant bytes, the time window, STOP/HOLD files and the witnessed ancestor region lock but logs only a generic failure. The launcher log explicitly deletes the grant after the terminal result; its later absence does not identify the earlier failure. Preserve the seven original program bundles and all declaration/source bindings for a qualified continuation; do not redraw any exposed or unknown case. PAW-3 remains open.

- **[declined: ws58 2026-11-03 content-review: merged as its continuation]** **PAW standard A admission continuation:** retain the seven source-bound compiled programs, capture the individual admission predicates and complete the original 64-case standard-A diagnostic under a qualified successor. Keep the interrupted eighth compilation and all native attempts visible; no new efficacy or adoption threshold.

##### 2026-10-31 PAW host-qualified successors

Four host-qualified diagnostic successors preserve their original declarations and cases: compact A (64, publication manifest `5049777d1dea3eef12e1e0df9a3f9f8587c9ae43d3897650390578213246bbd7`), compact B (72, `aa890b927d0aa4546c047abd967bc242a5d06ff8a6abafe9f268237706268adc`), superlative control (eight, `855417191c50534ec948e17c366acad2d92e2bb603b9b6f3f3892d6518e0e774`), and standard A continuation (64, `296a8a2b09e6c4e7d4000d9f87c679cf95d1b73797dc1c749b4a2e0a3ca06386`). The compact A value is its original publication-time manifest; keeper arming adds metadata. Each uses host socket/environment and startup qualification plus noncohort normal and STOP/drain controls. Prior hostfix1 packets were retracted after their container/host mismatch; those failures remain historical. Standard A retains seven saved bundles and its interrupted task-10 compile attempt as UNKNOWN. At publication the original cases were unexposed; compact A subsequently started its real grant at 05:01:11 UTC, so its present exposure must be read from native records. Full-run outcomes, original PAW-3 capability comparison and scientific gate remain open. No private case text or model weights are in the [bounded capsules](../../artifacts/compute/codex3-paw-host-qualified-20261031-0508/). [belief: cc]

##### 2026-10-31 PAW standard B diagnostic

`codex3-paw-standard-b-t1-20261030` finalized rc0 with 72/72 predeclared native case records across nine tasks and nine bundle hashes verified against the recorded program pins. Independent exact decoded-output comparison after outer whitespace stripping gives, out of eight cases per task: 11 **7**, 12 **4**, 13 **8**, 14 **7**, 15 **6**, 16 **8**, 17 **7**, 18 **8**, 19 **6** (61/72). All 72 SDK finish reasons are UNKNOWN; do not infer absence of truncation. This is the standard arm only, with no compact comparison, adoption or PAW-3 completion verdict. Original case inputs, reference answers and outputs remain in private retained storage; [digest-only rederivation and provenance](../../artifacts/compute/codex3-paw-b-yarn-filing-20261031-0511/) avoid publishing them. [belief: cc]

##### 2026-10-31 PAW standard A continuation — post-run source check failure

**FAILED-RUN, class harness:** `codex3-paw-standard-a-resume-20261031` returned rc1 after writing 64/64 case records because its final original runtime `SOURCES.sha256` check could not read five `/home/node/.cache/...` tokenizer files in the execution namespace; DONE was not written. The eight program bundles and per-case declaration bindings rehash. Descriptive, **unsealed** exact decoded-output matches out of eight are task 0=8, 1=8, 2=8, 3=4, 7=7, 8=8, 9=7 and 10=7 (57/64); SDK finish reasons are UNKNOWN for all 64, and the failed final source check limits provenance. Preserve all 64 exposed records and prior task-10 compile attempt; do not redraw them. Owner action: repair the original source custody/finalization check and verify the retained evidence without rerunning exposed cases. No standard-vs-compact or PAW-3 verdict follows. [Digest-only audit and failure evidence](../../artifacts/compute/codex3-c6-full-paw-a-results-20261031/). [belief: cc]

At 05:24 the unchanged native writer was run offline over the retained receipts, producing eight tuples without new inference or a DONE marker. The resulting native record SHA-256 `d3cee7776c46eba268cbdb850e56eeaf896d4f62ecfb3255c9ea0f9c828d31fe` and tuple file SHA-256 `3660d80c4872aa0464be941eeaf2306c63988a36253c5104a7c84654e6abc534` rehash. This later observation does not erase the original rc1 or establish that its failed source check passed. [belief: cc]

##### 2026-10-31 PAW superlative HOST-fix diagnostic

`codex3-paw-superlative-hostfix2-20261031` completed rc0 with eight paired cases. Independent declaration, program, grant and case checks rederive **binary 8/8 correct** and **semantic 7/8 correct**, zero UNSURE, invalid or missing. By category: different-group 4/4 for both arms; same-group binary 4/4 and semantic 3/4 (one incorrect). The source writer's single tuple is an observation; no superiority, adoption or full PAW-3 result follows from this small diagnostic. Original private case text and model outputs remain private. [Digest-only audit](../../artifacts/compute/codex3-c6-full-paw-a-results-20261031/super/). [belief: cc]

##### 2026-10-31 PAW compact A HOST-fix2 diagnostic

`codex3-paw-compact-a-hostfix2-20261031` completed rc0 with 64/64 original compact-arm native case records and eight bundle hashes verified. Exact decoded-output matches after outer whitespace stripping, out of eight per task: 0=5, 1=5, 2=8, 3=6, 7=7, 8=7, 9=6 and 10=4 (48/64). SDK finish reasons remain UNKNOWN for all cases. This is descriptive compact-arm evidence only; the standard A continuation's failed final source check remains separate, so no standard-vs-compact or PAW-3 gate verdict follows. Original private cases and outputs stay in private custody. [Digest-only audit](../../artifacts/compute/codex3-paw-compact-a-cs22-f32-20261031/). [belief: cc]

  - *(2026-10-31, matched A descriptive comparison.)* The standard and compact declarations bind the same 64 task/case inputs and references, task specifications, and source plan. Re-reading the native outputs gives 57/64 standard and 48/64 compact exact matches: both 45, standard only 12, compact only 3, neither 4. The standard run originally ended rc1; its unchanged writer later finalized offline from retained records, without new inference or a DONE marker. Finish reasons remain unknown. This comparison does not close PAW-3 or establish a significance threshold. [Audit](../../artifacts/compute/codex3-paw-paired-a-20261031/paw-paired-audit.json). [belief: cc]


##### Compact B continuation admission loss — 2026-10-31 08:04 UTC

`codex3-paw-compact-b-hostfix2-20261031` ended rc 1 at 08:04:22: **FAILED-RUN, class admission**. Its native job reports `admission lost` and drained children. The predicate combines grant identity and time, STOP/HOLD, ancestor identity and region-lock ownership, so the particular failed condition is unknown. Seven task 11–17 program bundles were retained and their hashes reverified; task 18 generation began without a saved bundle, so its generation outcome is unknown. The 72 evaluator cases were reported unexposed; there is no accuracy result. This event is separate from the 05:58:33 rc 75 window cutoff. Owner action: inspect the admission loss and preserve the unresolved task 18 generation exposure and existing bundles before any safe continuation; do not redraw an exposed unknown. PAW-3 remains open. [Audit and native disposition](../../artifacts/compute/codex3-paw-compact-b-0804-20261031/AUDIT.json). [belief: cc]

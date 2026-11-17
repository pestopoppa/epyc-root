# Exstill 2611.18859 + NVIDIA/Gimlet spec-dec and attention blogs — deep dive (intake-2669..2673, 2026-11-17)

Status: Stage 4 applied 2026-11-17 (operator-approved; paper filed stage1-unverified, option a).
Lane: subagent of autokernel, 2026-11-17. Sweeps: 2 of the operator's cap of 2.
Sources are on disk in this directory with sha256 values: paper.pdf f8ab27d0…, gimlet.html 8a6d485d…, nvidia.html 6b2a9738…, nvattn.html (spec-dec Part 2), gimlet_rso.html.

## Why the index was not written
1. arXiv 2611.18859v1 has no HTML rendering (the /html/ route returns a 6 KB stub), so the PDF was the source.
2. `machine_anchor._extract_text` accepts only text media types. A PDF snapshot therefore cannot receive an `anchor_mark`.
3. Under the 2026-11-08 anchor gate, a `dive-verified` entry without a passing mark fails validation.
4. The owning session must choose one of two ways forward:
   - (a) File intake-2669 as `read_depth: PARTIAL` with `verification: stage1-unverified`, plus a note that the PDF quotes below were checked by hand.
   - (b) Extend the extractor to handle PDF.
5. The four blog entries are HTML and can be anchored normally. Store them via `EPYC_VIDYA_RAW_ANCHOR_ROOT`, then run `--check-anchors --write-marks`.

## Proposed intake entries (next id 2669; origin/main max is intake-2668)
| ID | Source | Type | Nov | Rel | Cred | Verdict | read_depth |
|---|---|---|---|---|---|---|---|
| 2669 | arXiv 2611.18859v1 Exstill, "The Most Efficient Single-Chip Processor for the Next Token" | paper | medium | medium | 1 (vendor, pre-silicon, ≤12mo) | adopt_patterns | PARTIAL (§1–3.10, §5.1–5.4 and refs read; §4, §5.5–8 guard/agent/finance not read) |
| 2670 | gimletlabs.ai/blog/draft-model-disaggregation (Kuznetsov & Azizi, 2026-11-10) | blog | medium | high | null | adopt_patterns | FULL |
| 2671 | developer.nvidia.com/blog/co-designing-ai-models-using-speculative-decoding-for-faster-llm-inference (Mitra et al. 2026) | blog | high | high | null | adopt_patterns | FULL |
| 2672 | developer.nvidia.com/blog/co-designing-ai-model-attention-for-fast-interactive-long-context-inference (sweep 2) | blog | medium | high | null | adopt_patterns | FULL |
| 2673 | gimletlabs.ai/blog/recursive-self-optimization (sweep 2) | blog | low | medium | null | knowledge_only (vision post, no data) | FULL |

Dedup was run unbounded against all arxiv_id and url values. No collision for any of the five. DSpark (2607.05147) already exists as intake-738, so it was recorded as a re-encounter and not minted again.

## Verified claims (source text read from disk)
- **2669, Eq. 1 / §2.4–2.6.** Decode time per token is fitted as two straight lines.
  - Model-size sweep: 0.17 ms per GB of weights, intercept 1.1 ms.
  - User sweep at 16K: about 1.8 ms plus 0.28 ms per user, within 2% on all 6 rows.
  - The slopes match bytes divided by bandwidth: 0.125 ms/GB at 8 TB/s, and 0.23 ms per user of KV against the measured 0.28.
  - The intercept is "fixed charge" (layers, launches, padding to tiles). The paper attributes it from the shape of the curve, not from a profile.
  - Quote: "The attribution rests on the form of the charge, fixed per step and indifferent to how many users share it, rather than on a profile of the software."
- **2669, §3.3 Table 3.** Costing has four levels: paper, architecture, cycle and gate.
  - Partial-model numbers mislead. Quote: "carries one hand-written kernel … to the cycle or gate level and scales it up as though the rest of the model ran equally well. It rarely does."
- **2669, §3.5.** The search ran Pareto first, then a quality bar.
  - Counts: 522,675 evaluated → 322,941 within budget → 313 on the front → 1 chosen as the lowest energy-delay design meeting the bpb bar.
- **2669, §2.3.** Designs are scored by energy times delay at a fixed quality, with quality measured in bits per byte so the score cannot be gamed by changing the tokenizer.
- **2669, §5.4.** A standalone drafter sharing the target's GPU runs badly.
  - Their measurement: vLLM 0.31 with a 1.7B draft plus gpt-oss-120b on one B300 was 4.7–8.0x slower than the target alone at 1 user.
  - The cause is serial draft passes inside the serving loop.
  - The speedup model is S = τ/(d+v).
- **2671.** Guidelines on draft length D:
  - When attention dominates, D = 128/G − 1.
  - Prefer D such that G(1+D) is a multiple of 128, because the attention kernel tile is 128 and runtime "increases in steps" at each multiple.
  - Increasing D moves GEMMs toward compute-bound. At D=7, compute-bound is reached at one-eighth of the batch.
  - At very low latency, speedup ≈ AL/(1+ρD) with ρ = L_draft/L_target.
  - The tile value of 128 is NVIDIA's kernel. **For us the constant is our own FA and MMQ tile M, not 128.**
- **2670.** Moving draft decode to a faster device raised peak interactivity 61→137 tok/s/req and moved the optimal D from 8 to 15. These are modeled numbers.
  - Field finding: accelerator draft prefill varied, so they moved draft prefill back to the GPU and kept draft decode on the accelerator.
- **2672.**
  - Decode attention arithmetic intensity is about 2G.
  - Decode GEMM-M = G (8–16), well below tile M of 64/128.
  - With spec-dec the effective M is G(1+D).
  - At short KV length (32K), fixed setup plus the flash-decoding split-K reduction dominate. Runtime flattens once G exceeds 16.
  - Head dim 64 still pays for a 128-wide tile.
- **2673.** Vision post with no measurements. Its loop principle: profile live serving telemetry, then let agents regenerate the specialized kernels; narrow the search space with simple performance models.

Corrections:
- The paper's 110x and 690x figures come from a pre-silicon chip compared against vLLM as shipped. The authors themselves say a tuned stack would roughly halve each ratio. These are not evidence about our GPU's fixed charge.
- The speedups in 2670 come from a model, except the prefill field observation.

## Ranked techniques (expected gain × fit to our stack)
1. **K1: verify-batch tile alignment (GPU first, then CPU).**
   - Choose the drafter D so that (1+D) and G(1+D) land on gfx90a FA/MMQ tile-M boundaries, and on the CPU iqk FA q-tile.
   - Measure the verify cost curve over D. It should be a step function.
   - Gain: free speed on every spec-dec role. It needs no kernel change, only D selection and possibly a padding-aware split.
   - Fit: high. 27B uses DFlash2 and every MTP/NEXTN role has a D knob.
2. **K2: two-line decomposition as a planner and roofline primitive.**
   - Fit per-token decode time against weight bytes (model sweep) and against KV bytes (context/slot sweep), on each device.
   - The intercept is the fixed per-step charge: barriers/sync on CPU, launch and graph gaps on MI210. The slope is set against the bandwidth ceiling.
   - This tells AK whether the next candidate should target bytes (layout or quant) or the fixed charge.
   - Gain: indirect but high, because it prunes candidates aimed at the wrong component.
   - Fit: high for INF-70 (CPU decode is bandwidth-bound, so intercept versus slope is exactly the open question) and for MI210 small drafters.
3. **L1: Amdahl-ceiling prune in the AK planner (loop efficiency).**
   - Before timing, bound a candidate's best-case end-to-end gain by the share of its target component, using the K2 intercept/slope and the existing launch-weighted kernel table.
   - Drop candidates whose ceiling falls below the keep threshold.
   - This applies the paper's warning that one kernel scaled up is not whole-model cost, to stop doomed timings.
   - It does not change the keep gate (the 2026-10-20 ruling allows estimates for ranking and ordering only).
4. **L2: retain the Pareto front of non-kept candidates per workload (loop reuse).**
   - Use the paper's Pareto-then-bar selection.
   - Census stores candidates with (quality delta, speed) that are not dominated, even if they missed the bar on their own workload.
   - Cross-workload screening then pulls them first.
5. **K3: draft/target device split, D retuned per placement.**
   - When a drafter's device or speed changes (draft decode on MI210 with target on CPU, or CPU draft prefill), re-sweep D. 2670 shows the optimum moves a lot.
   - Fit: medium. It depends on the heterogeneous-fabric work. Arithmetic modeling first, no compute.
6. **K4: split-K / flash-decoding reduction overhead at short KV for high-G decode.**
   - 2672 shows the fixed reduction dominates at short KV.
   - Probe the share of the FA decode reduction kernel at 4–16K on MI210 using existing AK-PROF-TWO-DENOM data.
   - Fit: medium.
7. **Knowledge only:**
   - Energy-delay at fixed quality as a score. Not adopted for keeps: our objective is throughput at a quality bar and power is not a constraint. Reopen only if power becomes a constraint.
   - Bits per byte as a quality unit that does not depend on the tokenizer. Useful for cross-model comparisons, but our KLD/PPL gates are same-model.
   - Model/silicon co-design. Not applicable to fixed hardware.
8. **Already covered:**
   - Telemetry-driven seeding (2673) is covered by calibrate_served_shapes.py and the AKX-ALL-16 profile.
   - Tiered costing (analytic, then op-level, then end-to-end) is covered by the op-level gate followed by the end-to-end keep.
   - Launch-gap attribution is covered by AK-PROF-TWO-DENOM (✅ 2026-11-07).
   - Generic HIP graphs are covered (G8 ALREADY_SUPPORTED).

## Proposed boxes (exact text; autokernel applies after approval)

**handoffs/active/rocm-kernel-authoring.md (INF-48), GPU kernel section:**
- [ ] **RKA-VERIFY-TILE** [non-inference then inference] Measure MI210 verify-pass cost vs draft length D=0..16 for the production spec-dec roles (27B DFlash2, A3B MTP) at ctx 4k and 32k, and mark where (1+D) and G·(1+D) cross the FA and MMQ tile-M of the current champion (read tile constants from C13 bda43aa17 source, not docs). Source: intake-2671 guideline 3 / intake-2672 (GEMM-M=G(1+D), partial tile costs a full tile). Decision: if cost is step-shaped, set each role's D to the largest value below a step that acceptance justifies (consumer: speculative-decoding.md D settings). Sufficiency: question = is verify cost step-shaped at tile boundaries; expected effect ≥10% verify-time jump at a boundary vs ≤3% rep noise; reuse existing A2 verify-cost gate rows first; stop-on-answer when one boundary is measured with ≥5 interleaved reps; stop-on-futility if the curve is smooth within noise across two boundaries. Gate-class futility-only. Model: Qwen3.8-27B Q8_0, Qwen3.6-35B-A3B Q8_0. [no-belief: new box]

**handoffs/active/cpu-decode-roofline-program.md (INF-70):**
- [ ] **INF70-TWOLINE** [non-inference first] Fit decode ms/token = a + b·weight_bytes (model sweep at fixed ctx) and = a' + c·KV_bytes (ctx sweep) on CPU from existing C13 llama-bench/served rows; report intercept a (fixed per-step charge: barriers, sync, threadpool) and slopes vs the measured STREAM ceiling. Source: intake-2669 §2.4–2.6 method (slope matches bytes/bandwidth; intercept = per-step charge). Decision: if a > 15% of token time on the serving models, prioritize barrier/threadpool candidates over byte-reduction candidates in AK seeds; else confirm bytes-first. Reuse existing rows first; new runs only for missing points (≥3 models, ≥3 ctx). Stop-on-answer when the fit residual is ≤5% on all points; stop-on-futility if residual >15% (model not linear, record and close). [no-belief: new box]

**handoffs/active/autokernel-loop.md (INF-06), planner tooling:**
- [ ] **AK-AMDAHL-PRUNE** [non-inference] In the planner, compute each candidate's end-to-end ceiling = target-component share (from AK-PROF-TWO-DENOM wall share + launch-weighted table, and INF70-TWOLINE intercept/slope where present) × best-case op speedup; demote (not delete) candidates whose ceiling < keep threshold and log the ceiling in the candidate record. Ranking/order only; keep gate unchanged (2026-10-20 ruling). Source: intake-2669 §3.3 (one kernel scaled up misstates whole-model cost). Acceptance: replay on the last campaign's candidate log shows which timings would have been skipped and that no past KEEP falls below its ceiling. Code-only; no loop launch. [no-belief: new box]

**handoffs/active/autokernel-akx-program.md (INF-82), cross-workload keep-gate track:**
- [ ] **AKX-PARETO-RETAIN** [non-inference] Census retains per-workload non-dominated (quality-delta, speed) candidates that missed the keep bar, tagged with their workload, and the cross-workload screen tries them first on new workloads before fresh generation. Source: intake-2669 §3.5 (Pareto-front then quality-bar selection). Acceptance: census query lists the front for the last two campaigns; one cross-workload screen consumes it. Code-only. [no-belief: new box]

**handoffs/active/speculative-decoding.md: trigger prose only, no checkbox:**
- Trigger: when any drafter changes device or speed by more than 1.5x (for example draft decode on MI210 with target on CPU), re-sweep D. The optimum moves with draft cost (intake-2670: 8→15 at 5x faster draft, modeled), and S = τ/(d+v) (intake-2669 Eq. 2). Check the owning-session rule before applying this: the handoff belongs to another session.

**K4 (split-K reduction share):** fold into RKA-VERIFY-TILE's profile pass as one extra column. No separate box.

Index rows: none new. Every box goes into an existing handoff that already has a row. Run `index_state.py --check` after applying.
No compute rows: research intake never takes compute. The [inference] parts run through the normal queue once filed.

## Steering ledger
1. seq1 (verbatim): "accept ALL recommended Stage-2 deep-dives, but at most TWO Stage-2 sweeps total". Disposition: context-only. Followed: 2 sweeps.
2. seq2 (verbatim, relayed): "also mine the source and its deep-dives for principles/methodologies that would make the AutoKernel LOOP itself more efficient …". Disposition: planned → L1, L2.

## Dive-surfaced sources declined (wave cap reached)
- NVIDIA co-design Part 1: "ai-model-co-design-hardware-friendly-llm-design".
- Ranjan et al. 2026: "Why speculative decoding works better than predicted on sparse MoE models" (NeurIPS). Relevant to A3B verify cost. Recommended for the next intake.
- MoESD (Huang 2025).
- Eldenk 2605.09992 (attention drift).
- Jouppi 2021 TPUv4i ten lessons.

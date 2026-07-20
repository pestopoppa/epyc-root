# GPU-Drafter Control Redesign

**Status**: NEW / SCOPING (opened 2026-07-18 from the v7 lever audit). Design + α-measurement
only — **no serving bench without operator approval** (`feedback_no_concurrent_inference`).
**Owner handoff**: this file. **Parents**: [gpu-drafter-mi200-investigation.md](gpu-drafter-mi200-investigation.md),
[mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) (Axis-B).

## Thesis

The straightforward GPU-drafter lanes are **measured dead**. On 2026-07-17:

- **Stage-1** (CPU-target + MI210 external drafter): usable acceptance (508/508) but
  **0.915× decode / 0.911× wall** — the external drafter overhead isn't repaid.
- **Stage-2** (co-resident GPU frontdoor + drafter): MI210 no-spec already 101.64 t/s;
  native MTP regressed to 0.948×, external drafter to **0.355×**.

Root cause is structural: **every production target ships a near-free embedded/native MTP
head**, which dominates any separate-drafter scheme (qwen precedent: MTP 41.9 ≫ ext-draft
~18 < plain 31). The explicit conclusion in the roadmap is: *"the next Axis-B path is not
'enable Stage-1/2'; it is a different drafter/control design or quant-asymmetric same-model
drafting."* This track owns that redesign so it doesn't fall between handoffs.

## What "different control design" could mean (candidates, α-gated)

| Design | Mechanism | Why it might beat the failed lanes | First gate |
|---|---|---|---|
| **Quant-asymmetric same-model self-spec** | Aggressive-IQ drafter (IQ1/IQ2_XXS, maybe REAP'd) on GPU + high-quant (Q8/Q4) verifier on CPU | **N5-free by construction** (identical vocab / M-RoPE / GDN); CPU verify launders quality; graceful fallback if IQ2-serving parity fails | measure α (drafter→target acceptance) **first** — [[feedback_measure_alpha_before_specdec_investment]] |
| **Adaptive-K / cascade drafting** | Vary draft depth per-token by confidence; cascade a cheap→richer drafter | The fixed-depth external lanes over-draft; adaptive-K prunes wasted verify | α-vs-depth curve on the real corpus |
| **Teleport-composed drafting** | Reuse the AXA-2 re-prefill+catch-up path as the drafter transport | Amortizes the CPU weight read (no findings-02 penalty) when the target overflows to CPU | needs AXA-2 v1 landed; composed-spec state `speculative.cpp:3063` |

**Extreme-scale target** (the reason to bother): Qwen3.5-397B-A17B / GLM-5.2-class at *full
CPU quality* + GPU-drafted speed — same-model IQ2 (~124 GB) / IQ1 (~74 GB) don't fit 64 GB
HBM, so **REAP + IQ1 (~56 GB)** is *required* for a same-model GPU drafter, or a smaller
same-family drafter (35B/122B qwen35 at Q8) trading α for fit.

## First actions

- [ ] **DR-0 — α measurement for quant-asymmetric self-spec**: measure drafter→target
  acceptance for an aggressive-IQ GPU drafter vs the CPU high-quant target on the real task
  corpus, BEFORE any serving build (the N5-alpha gate already cleared `n5_spec_on` 376/376,
  but that was the *alignment* check, not the quant-asymmetric acceptance). Operator-gated bench.
  - [x] **DR-0a — procure/build/register the aggressive same-model IQ drafter artifact**:
    completed by inference-research commit `b696241` (`qwen35_122b_iq2m` registry row) plus
    the bounded MI210 smoke/context summaries. Local
    `/mnt/raid0/llm/models/Qwen3.5-122B-A10B-MTP-GGUF/UD-IQ2_M/Qwen3.5-122B-A10B-UD-IQ2_M.gguf`
    is 37.60 GiB, same MTP family, fits MI210, returned exact JSON in the server smoke, and
    produced complete context rows. This closes the missing-artifact blocker only; DR-0 still
    needs an operator-approved acceptance/economics run against the high-quant CPU verifier. ✅ 2026-07-19
  - [x] **DR-0c — acceptance/economics run sheet prepared ✅ 2026-07-19**:
    `docs/reference/mi210-axa-dr0-run-sheets-2026-07-19.md` pins the task classes, evidence
    fields, and pass rule `E(alpha,K) > F(K)+H(K)` for the next quant-asymmetric run. This is
    design prep only; the actual DR-0 run remains MI210/`P-GPU-1` gated.
  - [x] **DR-0 negative scheduling check ✅ 2026-07-18**: attempted to schedule the bounded
    MI210 measurement, found the missing-artifact blocker, and stopped rather than inventing a
    serving implementation. Fallback GPU time was used for a separate Qwen3.6-27B n-gram smoke
    (`data/ngram_gpu_smoke_20260718T221549Z/`), which is observation-only and does not close DR-0.
  - [x] **DR-0d — live quant-asymmetric run completed ✅ 2026-07-20**:
    corrected reasoning-off artifact
    `/mnt/raid0/llm/epyc-inference-research/data/dr0_quant_asym_self_spec/dr0_quant_asym_self_spec_20260720T043000Z_reasoning_off/`
    plus report
    `/mnt/raid0/llm/epyc-inference-research/docs/data/dr0_quant_asym_self_spec_20260720.md`
    shows the design is speed-promising but not admissible. CPU Q4 verifier baseline was
    `6.890 t/s`; CPU Q4 + MI210 IQ2 combined measured K1 `9.959 t/s` (`1.445x`,
    alpha `0.963`), K2 `11.335 t/s` (`1.645x`, alpha `0.928`), and K4 `12.298 t/s`
    (`1.785x`, alpha `0.837`). Cleanup passed and postflight was quiet, but quality
    sanity failed (`1/28`) and combined output changed on the code-review control, so
    this is speed/alpha evidence only.
  - [ ] **DR-0e — decision-grade telemetry/quality rerun**: add or expose engine telemetry
    that separates `F(K)` verifier work from `H(K)` coordination overhead, then rerun the
    quant-asymmetric slice with strict prompt/schema controls and require CPU-target output
    stability on every task before any routing/serving integration.
- [x] **DR-1 — economics model ✅ 2026-07-18**: break-even model recorded at
  [docs/reference/gpu-drafter-break-even-model-2026-07-18.md](../../docs/reference/gpu-drafter-break-even-model-2026-07-18.md).
  Key result: external Stage-1/2 failed despite `α=1.0`, so their blocker is
  overhead/control cost, not acceptance. Future drafter lanes must satisfy
  `E(α,K) > F(K)+H(K)` on paper before any serving build.

## Cross-links

- α-alignment baseline (N5) + Stage-1/2 negatives: [gpu-drafter-mi200-investigation.md](gpu-drafter-mi200-investigation.md),
  [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) Axis-B.
- Teleport transport: AXA-2 in the mi210 roadmap.
- Dead lanes (do not revive as-is): tree-draft/DySpec, external-drafter Stage-1/2
  ([tree-draft-forward-port-plan.md](tree-draft-forward-port-plan.md)).

## Reporting

Update this handoff first; if DR-0/DR-1 show no path beats native MTP, close as
confirm-negative and record in the inference-acceleration-index.

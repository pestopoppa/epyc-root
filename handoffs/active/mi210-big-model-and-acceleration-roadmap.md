# MI210 big-model residency + acceleration roadmap

**Status**: STRATEGIC THREAD (operator-developed 2026-07-04/05). All numbers OBSERVATION; every step is **experimental-HOLD** — operator-only authorizes any production push, CPU-correctness-gated first. Distilled from the MI210 speed campaign ([summary](mi210-speed-campaign-summary.md), findings-05b/05c) as the "what do we do with this card next" thread.

## The framing: one 64 GB MI210, two ways to use it
1. **Big-model RESIDENCY** — host a large model *on* the card so it runs at GPU speed (the residency bet, findings-02 Gate R). One large model resident at a time.
2. **DRAFTER-FARM** — keep the big models CPU-resident but host fast *drafters* on the GPU to accelerate them via spec-dec (or text-level scaffolds).

These compete for the single card → **Gate-R is a scheduling decision**, not a foregone conclusion. Both are untested-to-partly-tested; this handoff maps them.

## Axis A — big-model residency (the quant-ladder → offload → GLM)
**Corrected architect baseline (2026-07-05):** production architect (122B UD-Q4_K_M on CPU, v6 native MTP) is **~18–21 t/s single-stream** (best 20.75; live median ~16; 2-slot ~8.5/slot) — NOT the stale lean-registry 4.3. So GPU wins are measured against ~20, not 4.3.

- **Quantize to fit (IQ2).** 122B UD-IQ2_M **MEASURED VIABLE fully GPU-resident** — 43.7 t/s single / 148.7 aggregate @B=32 (bf16-state on), IQ2 PPL 5.02 healthy, ~17 GB headroom. Win ≈ **2.2× single / ~8–9× aggregate** at a **Q4→IQ2 quality trade** (eval-parity vs the architect's 93% pending). Also probe **gemma4-IQ4** (mid-precision, already-fitting model). **Caps at ~122B — GLM-5.2 (~238 GB even at UD-IQ2) never fits GPU-only.**
- **Offload to fit (expert-hybrid)** — the **quality-preserving** alternative + the **only GLM-5.2 path**: hot/active experts GPU-resident at **Q8/bf16 (no weight-quality loss)**, cold experts streamed from the 1.1 TB RAM (`large-moe-expert-parallelism.md`, `--n-cpu-moe`/`-ot exps=CPU`, [findings-02](fable5-window2-findings-02-heterogeneous-gpu.md)). Currently backlogged to protect the CPU session; un-park as the GLM path — **but operator: "a concern for another day."**
  - **Decisive cheap gating experiment: an expert-routing-skew profile** (per-layer expert hit-frequency over a real workload). **Zipfian** (hot-set cacheable) → offload flies; **near-uniform** → PCIe-streaming-latency-bound. Cheap, tells us viability before building.
  - **REAP is the same skew analysis, different action** (operator insight 2026-07-05): the skew profile is exactly what expert-pruning (REAP — e.g. the on-hand `cerebras_Qwen3-Coder-REAP-25B-A3B`, 25% expert removal) is built on. **Prune (REAP) = permanently drop cold experts → smaller model that fits, at a capability cost on the niche tasks those experts served. Offload = keep all, stream cold → full quality, streaming latency.** One measurement (the skew profile) feeds both; a **REAP + IQ2** combination could be the aggressive path to squeeze GLM-class models toward fitting.

**Ladder:** IQ2 near-term (122B, gated on eval-parity) → expert-offload/REAP medium-term (quality + 80B-ingest / GLM) → **GLM-5.2 endgame** (offload mandatory; maybe REAP + IQ2-resident-experts + offload-cold-tail).

## Axis B — GPU drafter-farm (accelerate the CPU targets)
Keep the big targets CPU-resident; host fast drafters on the MI210 for spec-dec. **UNTESTED.**
- **GPU-draft / CPU-target spec-dec** (findings-05b §7 GPU re-open; `-devd`/`-ngld`/`-otd`): the CPU verify of GPU-drafted tokens **amortizes the CPU weight read → no findings-02 amortization penalty**, so it's a genuinely favorable regime *if drafting works*.
- **Blocker — N5** (vocab / M-RoPE / GDN mismatch for *external*-draft spec-dec). The architect already uses **native MTP** (NEXTN self-draft), which sidesteps N5 but is self-limited; a GPU *external* drafter must either solve N5 or use a same-family aligned drafter. Its yield-over-native-MTP is the open question.
- **The CoT-scaffold sidecar** ([gpu-cot-scaffold-sidecar.md](gpu-cot-scaffold-sidecar.md)) is the deliberate **text-level** alternative that sidesteps N5 (transfer via prompt, not vocab/KV). G1-(i) = GO (context-advisory scaffold beats own-think @0.45× tokens, caveated; harder-suite slice in flight). Sidecar (quality) and drafter (latency) are **complementary**, not competing.

## Gating experiments (cheap, decisive, do before building)
1. **Expert-routing-skew profile** (Axis A offload/REAP) — Zipfian? → the whole offload/REAP viability.
2. **GPU-draft N5 feasibility** (Axis B) — can an external GPU drafter align to a qwen35/GDN target, and does it beat native MTP?
3. **122B IQ2 eval-parity** (Axis A quantize) — running now; gates the IQ program.

## Cross-links
[summary](mi210-speed-campaign-summary.md) · [findings-05b](fable5-window2-findings-05b-mi210-inference-architecture.md) (Gate R, GPU-draft §7) · [findings-05c](fable5-window2-findings-05c-mi210-lever-category-matrix.md) · [fable5-window2-mi210-focus-injection.md](fable5-window2-mi210-focus-injection.md) (parent MI210 focus). **Established work this thread must connect to:** [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) (**REAP-on-GLM *methodology* precedent only** — it's a GLM-**5.1**-555B eval, and 5.1 is SUPERSEDED by GLM-5.2; use it for the REAP *technique* + the "a REAP'd GLM shrinks to fit" finding, NOT as the current target. **GLM-5.2 (~238 GB UD-IQ2) is the real endgame** — tracked via intake/`project_unsloth_iq2_large_moe_storage`, DSA-gated PR#21149; no dedicated GLM-5.2 residency handoff exists yet), [gpu-acceleration-path.md](gpu-acceleration-path.md) (**CPU+GPU hybrid inference** — the offload machinery's home), [angelslim-techniques-evaluation.md](angelslim-techniques-evaluation.md) (**sub-2-bit quant + reasoning speculative-exit** — the quantize axis), `large-moe-expert-parallelism.md` (bit-correct EP), `gpu-drafter-mi200-investigation.md` (drafter-farm), [gpu-cot-scaffold-sidecar.md](gpu-cot-scaffold-sidecar.md) (text-level N5-sidestep), `fable5-window2-findings-02-heterogeneous-gpu.md` (Gate R). Domain index: [inference-acceleration-index.md](inference-acceleration-index.md).

# MI210 GPU speed campaign — executive summary (2026-07-03/04)

**Goal**: get models as fast as possible on the single MI210 (gfx90a/CDNA2, 64 GB, ~1.64 TB/s), and isolate the circumstantial levers per model category. **Both single-stream and aggregate** tracked. GPU-compute only; kernel work in `llama.cpp-experimental` (never production-v6). Every number here is an **OBSERVATION** (no P-GPU-1 protocol) — usable for direction, never to gate a keep/deploy/promote decision. Full detail: [findings-05c (lever × category matrix)](fable5-window2-findings-05c-mi210-lever-category-matrix.md), [findings-05b (architecture)](fable5-window2-findings-05b-mi210-inference-architecture.md), [checkpoint](../../progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md).

> **⏸ PRODUCTION HOLD (operator 2026-07-04).** Everything below stays in the experimental build — NOTHING deploys to production yet. The "deploy now" config wins (FA / bf16 / -md) are experimental-validated recommendations that first need **CPU-numerical-correctness verification** (untestable now, CPU busy); production-push authority is operator-only. Direction chosen: proceed with the research bets + build the kernel-R&D-loop (see bottom).

## The one meta-finding
**Every lever's sign is set jointly by {arch × substrate × batch}. Never carry a verdict across those boundaries.** Examples proven this campaign: MTP +15.6% dense-GPU / −12% MoE-GPU / +win CPU-MoE; `-fa 1` hurts dense-27B decode everywhere but WINS MoE aggregate +16–43%; the MMVQ→MMQ dispatch fix +17–32% dense-Q8 but net-negative for MoE experts. The circumstance *is* the finding.

## Experimental-validated config wins — HOLD for prod (see banner) (→ orchestrator/CPU session)
Applies when a role is hosted on the MI210 (the residency bet). **These are validated in experimental only; not for production until CPU-correctness verified.** Brief: [moe-aggregate-deployment-wins-brief.md](moe-aggregate-deployment-wins-brief.md).
1. **`-fa 1` for aggregate MoE (B≥8), `-fa 0` for single-stream** — +16–43% aggregate; peak **bf16+fa1 @B128 = 1548 t/s** (gemma-26B-A4B).
2. **bf16 for high-concurrency MoE roles (B≥16–32), Q8 for single-stream** — crossover B≈16–24; bf16 +27–43% at high batch (HBM-fit-gated: bf16-26B fits ≤B128).
3. **Drop `-md <same GGUF>` for embedded-NEXTN roles** (CPU-side, [md-double-load brief](md-double-load-mtp-fix-brief.md)) — 2× DRAM saving on BW-bound CPU decode.

## BANKED kernel wins — fork `pestopoppa/llama.cpp@upstream-mtp-verify`, experimental, operator-gated for prod
Single-stream dense-Q8 (Qwen3.6-27B): **29 → 40.4 t/s (+37%)**. All correctness-verified (`test-backend-ops` clean, output coherent/byte-identical), all runtime-gated default-off.
| commit | lever | gain |
|---|---|---|
| `de447119f` | MMVQ→MMQ small-batch verify-dispatch (Q8 `ne11<=1`) | +17.4% (MTP-verify path); +31.7% on gemma-31B |
| `5dc116130` | nwarps 2→4 (CDNA2 batch-1 Q8) | +4.6% |
| `7c28056b7` | async weight-prefetch (`raw.buffer.load.lds` LDS double-buffer) | +3.3% (MemUnitStalled −62%) |

## DEAD / not-worth — ruled out WITH DATA (do not reopen without a regime change)
- **fused dequant-in-GEMV** — non-task; Q8_0 GEMV already int8-native (`dp4a`), no dequant to hide.
- **fused-SwiGLU prefetch** — coverage doubled but −1.8% (big FFN GEMVs already wave-pipelined).
- **megakernel** — Pass-2: MLP/memory floor; HIP graphs already capture the only +5.9% launch headroom.
- **n-gram / prompt-lookup GPU spec** — negative (~15% accept < break-even).
- **MFMA compute-paths** (prefill/high-batch) — matrix cores already engaged.
- **L1-MoE mmid dispatch** — inverts the dense fix (−10 to −30% low-batch); default threshold optimal.
- **KV-quant (aggregate)** — VRAM not binding. **MTP for MoE-on-GPU** — −12%. (Both still *alive* in other regimes: KV-quant single-stream-long-ctx; MTP dense-GPU/CPU-MoE.)

## HARD RESEARCH BETS — real headroom, but NOT low-hanging (register-pressure-bound, uncertain payoff)
Only pursue as a deliberate research investment, not quick wins:
- **L3-MoE — Q8-MMQ occupancy/tiling rewrite.** The +32% Q8→bf16 aggregate gap is Q8-MMQ's low occupancy (2.61 vs 3.22 waves/CU) + fragmented dispatches, not dequant/requant (measured). Matters only for HBM-capacity-bound larger MoE (122B/GLM that can't fit bf16). Until then **bf16 is the aggregate answer.**
- **L20 — GDN occupancy + recurrent-state traffic/layout** (qwen35-hybrid only). The aggregate scaling cap (3.4× vs 5.9–8.6× for pure-MoE/dense). Same difficulty class as L3-MoE.
- **Process idea** — whether to run future kernel R&D as a semi-autonomous loop: [mi210-kernel-rnd-loop-proposal.md](mi210-kernel-rnd-loop-proposal.md) (build-on-go).

## vLLM gap (the operator's question, answered)
vLLM-ROCm is **arch-blocked on gfx90a** for our qwen35/MoE (GDN Triton + loader), but beats llama.cpp-HIP **+11%/+24% on stock dense fp16** — because it hides batch-1 memory latency better. That gap is the same batch-1 latency wall; our prefetch lever attacks it (+3.3% on the reachable half; the rest is the MLP floor per the megakernel Pass-2). Not a llama.cpp defect to "fix" — a fundamental batch-1 HBM floor both engines approach.

## Bottom line
Single-stream dense-Q8 is **exhausted at its ceiling** (+37%). Aggregate MoE has **two immediate zero-code wins** (FA + bf16, up to 1548 t/s) with the remaining headroom gated behind two hard occupancy-rewrite research bets. The lever isolation is complete across both regimes. **Per operator (2026-07-04): hold all changes experimental (CPU-correctness gate before any prod push), and proceed with the kernel research bets (L3-MoE / L20 / sub-4-bit enabler) + build the kernel-R&D-loop in parallel.**

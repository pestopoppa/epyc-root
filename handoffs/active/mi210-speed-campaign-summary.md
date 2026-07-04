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

## RESEARCH BETS — BOTH occupancy rewrites now FALSIFIED (2026-07-04); speed frontier structurally exhausted
The two "hard research bets" were funded and executed this session. Both are dead as occupancy plays:
- **L3-MoE — Q8-MMQ occupancy/tiling rewrite = BUILT + FALSIFIED = NO-GO.** The compact-LDS rewrite worked mechanically (staging LDS 49→25 KB, LDS-residency 1→2 WG/CU, correct: `MUL_MAT 1103/1103`, `MUL_MAT_ID 789/789`, PPL indistinguishable) but occupancy stayed **FLAT (3.07→3.07)**, aggregate +1.6% B=32 / −12% B=64. Root cause: at B=32 Q8-MMQ is **grid-limited** (104 WGs = 1 WG/CU, no 2nd workgroup for the freed LDS), **not LDS-limited**; bf16 wins on native-MFMA, not occupancy. Only remaining Q8-aggregate lever = stream-K (bigger separate bet; compact-LDS kernel saved as substrate `campaign/mmq-compact-lds-NEGATIVE.patch`). **Settled: bf16-for-aggregate, Q8-for-capacity.**
- **L20 — GDN occupancy (qwen35-hybrid) = SCOPED = NO-GO.** The GDN kernel is already at **100% theoretical occupancy** (32/256 VGPR, 0 LDS, grid 472× CUs); the ~42% is pure **memory-latency**, nothing to free. The one real GDN lever = **bf16 recurrent-state = BUILT + GO (`496e2f098`): +21.5% aggregate @B32** (beats the +11% projection — halves the state gather+scatter too), quality-neutral (drift PPL +0.0035%, isolation clean), runtime-gated default-off. **Wires all 3 GDN-hybrids → the DEPLOYED frontdoor 35B-A3B + architect 122B inherit it** — a real deployed-role aggregate win (frontdoor 35B-A3B CONFIRMED +17.7% @B32, byte-identical; architect 122B pending), not just the test vehicle. High-batch-only (B=1 neutral).
- **L15 — sub-4-bit capacity unlock = INDEPENDENT of the occupancy result and still LIVE.** CDNA2 sub-4-bit MMQ is already correct (`MUL_MAT_ID 789/789, 0 FAIL` across q8_0/q2_K/iq2/iq3/iq1/iq4); missing = a quantized GGUF. **Qwen3.5-122B-A10B UD-IQ2_M (40.4 GB, unsloth) is downloading now** → fully GPU-resident 122B architect (IQ2 ≈ 38–40 GB fits in 64 GB). Measurement (PPL + aggregate vs UD-Q4_K_M) pending download completion. This is the **capability frontier** the campaign has pivoted to.
- **Process — kernel-R&D loop Phase 0 LANDED.** [mi210-kernel-rnd-loop-proposal.md](mi210-kernel-rnd-loop-proposal.md) refined to a buildable 4-phase handoff; **`kernel_eval.sh` (the verify layer) BUILT + VALIDATED** (research `48f990f`, `scripts/kernel_rnd/kernel_eval.sh`): correctness-gate-first/lexicographic → alternated-A/B → rocprofv2 mechanism → OBSERVATION JSONL; reproduced the prefetch kernel's +2.11% / MemUnitStalled −55% / 1103-1103 byte-identical. Phases 1–3 (strategy store → nightshift loop → dashboard page) open.

## vLLM gap (the operator's question, answered)
vLLM-ROCm is **arch-blocked on gfx90a** for our qwen35/MoE (GDN Triton + loader), but beats llama.cpp-HIP **+11%/+24% on stock dense fp16** — because it hides batch-1 memory latency better. That gap is the same batch-1 latency wall; our prefetch lever attacks it (+3.3% on the reachable half; the rest is the MLP floor per the megakernel Pass-2). Not a llama.cpp defect to "fix" — a fundamental batch-1 HBM floor both engines approach.

## Bottom line
**GPU speed is structurally exhausted** (2026-07-04): single-stream dense-Q8 at its ceiling (+37%); aggregate MoE has two zero-code wins (FA + bf16, up to 1548 t/s); and **both occupancy-rewrite bets (L3-MoE, L20) are now falsified** — the only remaining speed headroom is stream-K (large, separate) or memory-latency the kernel can't touch. **The frontier has moved to capability**: the L15 sub-4-bit residency unlock (122B UD-IQ2_M downloading → fully GPU-resident architect) is the live bet. In flight: bf16 recurrent-state (the modest GDN lever) building; 122B UD-IQ2_M downloading; L15 measurement pending. The kernel-R&D loop has its Phase 0 verify harness (`kernel_eval.sh`) landed. **All config/kernel wins remain experimental-HOLD (operator-only prod push, CPU-correctness gate first).**

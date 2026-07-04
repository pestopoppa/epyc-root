# 2026-07-04 — MI210 campaign: kernel-R&D loop (Phase 0) + occupancy-bet falsification + capability pivot

Continuation of the MI210 GPU speed campaign, following the 2026-07-04 wrap-up checkpoint (`0628f8ad`). This session executed the operator-funded "start the research bets **and** build the kernel-R&D loop in parallel" direction. Substrate: single MI210 (gfx90a/CDNA2, 64 GB HBM2e, ~1.64 TB/s, ROCm 6.2); all kernel work in `llama.cpp-experimental` (branch `upstream-mtp-verify`), never production-consolidated-v6. **Every throughput number below is an OBSERVATION** (no P-GPU-1 protocol) — direction only, never a keep/deploy/promote gate. Production-push authority is operator-only (all changes stay experimental until CPU-numerical-correctness verification).

## Headline

GPU **speed** is now exhausted at the structural level — every remaining occupancy bet this session was **built or scoped and killed with data**. The frontier has moved from speed to **capability**: making the 122B architect fully GPU-resident via sub-4-bit residency (L15). bf16 is the settled aggregate-MoE answer (peak 1548 t/s @B128 gemma-26B-A4B); Q8 is retained only for HBM-capacity-bound roles.

## What landed this session

### 1. Kernel-R&D loop — refined to buildable + Phase 0 BUILT + VALIDATED
- **Proposal → buildable handoff** (`7fdf449e`, epyc-root): the `mi210-kernel-rnd-loop-proposal.md` was refined with the operator's decisions (reuse+EXPAND the existing orchestration dashboard as separate kernel pages, operator-only production authority, lexicographic correctness-first fitness, `kernel_eval.sh` as the do-first artifact) and a 4-phase build plan (Phase 0 verify layer → Phase 1 SQLite strategy store → Phase 2 nightshift loop → Phase 3 dashboard page).
- **Phase 0 — `kernel_eval.sh` BUILT + VALIDATED + committed** to epyc-inference-research `main` (`48f990f`, `scripts/kernel_rnd/kernel_eval.sh`, 230 lines). The codified verify harness: GPU-idle gate → **correctness gate FIRST** (lexicographic; a FAIL never speed-ranks) → coherence check → alternated-A/B `llama-bench tg128 -fa 1 -r 3` → rocprofv2 mechanism-confirm (`pmc:` MemUnitStalled/Busy/occupancy) → one OBSERVATION JSONL record.
- **Validation** against the already-landed async-prefetch kernel (`GGML_CUDA_Q8_PREFETCH` 0 vs 1, 27B-Q8): reproduced **+2.11% tg128, MemUnitStalled −55%, test-backend-ops 1103/1103, byte-identical output**. Correctness-first gate additionally proven with a deliberately broken stub (FAIL never speed-ranks). Standalone value even if the full loop never ships.

### 2. MMQ-family bet (L3-MoE + L15) — L3-MoE BUILT + FALSIFIED = NO-GO; L15 independent + still live
- **Scoped GO** (`2df5e765`): the aggregate-MoE #1 kernel lever, de-risked with a concrete occupancy mechanism (Q8 `mul_mat_q` capped at 1 WG/CU by dequant-staging LDS 45–49 KB + Arch-VGPR 128) and a measured target (halve staging LDS → 2 WG/CU → close the +32% Q8→bf16 gap).
- **BUILT + FALSIFIED = NO-GO** (`30a831cc`): the compact-LDS rewrite worked *mechanically* — LDS halved 49→25 KB, LDS-limited residency lifted 1→2 WG/CU, accumulator untouched, **correct** (`MUL_MAT 1103/1103`, `MUL_MAT_ID 789/789`, PPL indistinguishable) — **but occupancy stayed FLAT (3.07→3.07)**, aggregate +1.6% B=32 / −12% B=64. Root cause: at B=32 Q8-MMQ is **grid-limited** (grid = 53248/512 = exactly 104 WGs = 1 WG/CU → no second workgroup for the freed LDS), **NOT LDS-limited**. bf16's aggregate win is its native-MFMA / zero-dequant compute, not an occupancy edge Q8 could match by freeing LDS.
- **Settled**: **bf16-for-aggregate (B≥16–24), Q8 only for HBM-capacity.** The only remaining Q8-aggregate lever is stream-K K-splitting (a bigger separate bet with fixup-kernel overhead; the gated compact-LDS kernel is saved as the ready substrate `campaign/mmq-compact-lds-NEGATIVE.patch`).
- **L15 sub-4-bit MMQ is INDEPENDENT of this occupancy result and still live**: the CDNA2 sub-4-bit MMQ path is already correct (`MUL_MAT_ID 789/789, 0 FAIL` across q8_0/q2_K/iq2/iq3/iq1/iq4). Missing = a quantized GGUF (see L15 below).

### 3. L20 GDN-occupancy — SCOPED = NO-GO (occupancy structural)
- **NO-GO** (`3e346b49`): the qwen35-hybrid GDN kernel is already at **100% theoretical occupancy** (32/256 VGPR, 0 LDS, grid 472× CUs). The measured ~42% is **pure memory-latency**, not an occupancy limiter — there is nothing to free. The one real GDN lever left is **bf16 recurrent-state** (~+11% aggregate @B32, high-batch-only, drift-gated) — a modest, non-occupancy lever.

## In flight (NOT complete — carry to next session)

- **bf16 recurrent-state (the modest real GDN lever) — BUILDING.** ~+11% aggregate @B32, high-batch-only, correctness/drift-gated. Owns the MI210 card this session (no other GPU inference run).
- **L15 capability — Qwen3.5-122B-A10B UD-IQ2_M downloading** (unsloth, 40.4 GB) to make the 122B architect fully GPU-resident (IQ2 ≈ 38–40 GB fits in 64 GB HBM). In progress (~11%+). **L15 measurement pending**: on completion, measure PPL + aggregate vs the existing UD-Q4_K_M benchmarks.

## Strategic state

- **Speed exhausted**: single-stream dense-Q8 at ceiling (+37% → 40.4 t/s, banked); aggregate-MoE has two zero-code wins (FA + bf16, up to 1548 t/s); **every occupancy rewrite bet (L3-MoE, L20) is now structurally dead** — the remaining speed headroom sits behind stream-K (large, separate) or is memory-latency the kernel can't touch.
- **Frontier = capability**: L15 residency of the 122B architect. bf16 is the aggregate answer; Q8/sub-4-bit is for capacity.
- Top-line reference: `handoffs/active/mi210-speed-campaign-summary.md`. Detail: `findings-05b` (architecture), `findings-05c` (lever × category matrix), `mi210-q8-dequant-gemv-roofline.md` (L3-MoE/L15).

## Deferred (next session)

1. Finish + measure the bf16 recurrent-state build (drift gate first, then aggregate delta).
2. Complete the 122B UD-IQ2_M download → measure PPL + aggregate vs UD-Q4_K_M (L15).
3. Kernel-R&D loop Phases 1–3 (SQLite strategy store → nightshift loop → dashboard page); Phase 0 harness (`kernel_eval.sh`) is ready to drive them.
4. All experimental config wins remain HOLD pending CPU-numerical-correctness verification (operator-only prod push).

## Guardrail note

Shared clone with a live parallel CPU/orchestration session. All commits this session used explicit pathspec (verified `git diff --cached`); no branch switches; the contended daily progress file and parallel-session handoffs were left untouched.

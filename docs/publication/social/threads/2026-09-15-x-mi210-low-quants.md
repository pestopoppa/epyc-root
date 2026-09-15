# X thread — Running low-bit quants on an AMD MI210 Instinct

**Ledger id**: `x-2026-09-15-mi210-low-quants`
**Platform**: X/Twitter · **Date**: 2026-09-15 · **Status**: posted
**Context**: reply to a user asking for tips on running lower quants on an MI210.
**Transcript**: verbatim, as posted. Do not edit — corrections go in a new entry.

---

**1/** Someone asked us for tips on running low-bit quants on an @AMD MI210 Instinct. Short version: below ~4 bits per weight, you're buying memory, not speed. The reason is more interesting than the rule so here's a 🧵 on the model-independent details.

**2/** What decides whether a quant is fast (or not) on this card isn't its bit width it's how many registers its decode kernel needs. gfx90a keeps 8 waves per SIMD busy at 64 registers or less; cross that and you get 6. A quarter of your occupancy, gone before you decode anything.

**3/** The counterintuitive bit is that, below that line, smaller is slower. A file 27–46% smaller can decode ~36–39% slower at batch 1. Q4_K (44 regs) is comfortably fast. IQ4_XS sits at exactly 64 (the last quant-rung that stays fast). Q3_K is the worst in the table at 88.

**4/** Weirdly, this only hurts decode. Prefill doesn't care. It's virtually flat across every quant I tested, no knee. So a smaller model isn't slow, it's just slow to talk.

**5/** Why? Decode runs a GEMV where each lane has to keep its dequant state alive for every weight it reads. Register pressure directly caps how many warps the GPU can schedule and it never amortizes with batch.

**6/** Prefill runs differently: dequantize a tile once into shared memory, reuse it across the batch, let the matrix cores do the math. Per-token cost falls with batch size. Flat ≠ optimal, though we still find double-digit prefill wins in config space. It's not the quant's fault.

**7/** So how do you actually use low quants? Batch the hell out of them! Serve concurrent (np 8–32) and Q4_K/Q8 catch up to the fastest rung by B=32. Sub-4-bit IQ only claws back to ~80–90%. That occupancy ceiling doesn't amortize. MoE models batch "worse" than dense (still fast).

**8/** Use low quants for capacity, not speed. They're how you fit a big model entirely on the card. Quality warning: 2-bit is lopsided. Knowledge survives; reasoning can get cut in half on a uniform Q2_K. Dynamic/per-layer and imatrix quants hold up well.

**9/** Two more traps: KV quantization is never a speed win (q8_0 KV costs 7–17% decode). Stick to f16 KV. Also, there's no FP8/INT4 matrix path on gfx90a, so don't port CPU dequant tricks. The GEMV is already int8-native!

**10/** A closing remark on the ladder's exact ratios I just cited: the 36–39% slower, the 0.77/0.88 batched recovery, the ~17% prefill spread. They come from one 8B model, single runs, speed-only. Observation-grade. Take the shape, not the decimals.

**11/** @AIatAMD feel free to call me out. I want to learn!

---

## Soft spots (ready answers if challenged)

1. **"Stick to f16 KV" (tweet 9)** is a *speed-only* statement. KV quantization is never a
   speed lever on this device (the dequant cast exceeds the bandwidth saved), but it
   remains the **max-context / VRAM** lever. Precise form: "for speed, keep f16 KV; for
   long-context VRAM it's still on the table."
2. **"MoE models batch worse than dense" (tweet 7)** — the MoE batching half is
   **unmeasured**; the controlled ladder was dense-only, and the 122B numbers are
   aggregate, not a sweep. Precise form: "we expect MoE to batch less cleanly — that
   half is still open for us."
3. **"Double-digit prefill wins in config space" (tweet 6)** are **search-stage,
   nonpromotable candidates** (e.g. a +26.6% MMQ-MFMA-off config), not ratified results.
4. **"Q3_K is the worst in the table at 88" (tweet 3)** is the **static VGPR table**,
   not a measured ladder rung. It is a per-type register allocation, not a throughput
   measurement.

## Evidence

- `handoffs/active/mi210-q8-dequant-gemv-roofline.md` — the Q8 dequant-GEMV roofline,
  the 64-VGPR/8-wave boundary, the production 122B IQ2 instantiation, and the MoE-IQ2
  ~10% bandwidth rung.
- `artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md` — the per-quant static
  VGPR table (Q4_K 44, IQ4_XS 64, Q3_K 88) and the IQ2 sign-unpack disassembly diff.
- `artifacts/gpu-aux-baselines/a10_quant_ladder_occupancy_knee_20260816.md` — the 8-rung
  ladder (n=1, one dense 8B, speed-only), the 27–46% smaller / 36–39% slower split, the
  ~17% prefill spread, and the B=1→32 batched ratios.
- `wiki/quantization.md` — the compiled read of the above, plus the KV-quant cost on the
  35B-A3B GDN hybrid (−16.7%) and dense 27B (−6.9%).

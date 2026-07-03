# 2026-07-03 — Acquired Qwen3.6-27B Q8 MTP variant (+ Fable5 window-2 / MI210 inventory readout)

**Session type:** Operator Q&A + one durable artifact (a model download). No production code changed.

## What was asked

Operator opened with a readout of the overnight **Fable 5 window-2** consult, then asked for an inventory
of models runnable on the MI210 via llama.cpp and vLLM, then — noticing the plain Q8 27B lacked a NEXTN
head — asked us to **obtain the Q8 MTP variant** of Qwen3.6-27B.

## Readouts delivered (no artifact; reporting only)

- **Fable5 window-2 findings** (`handoffs/active/fable5-window2-findings-{00..04}-*.md`, written overnight
  00:45–00:52): structurally complete against the §8 output contract (exec summary, 4A optimizer
  integrity, 4B heterogeneous GPU, portfolio+queue rewrite, negative-space+self-critique). 12 evidence
  agents + 7 adversarial verifiers, 54 claims (47 CONFIRMED / 7 PARTIAL / 0 REFUTED), ~1.83M tokens.
  Despite the stop-and-poke + self-reduced effort the operator observed, the run did **not** truncate.
- **MI210 model inventory** (llama.cpp-HIP runs our custom archs; vLLM 0.10.1 gfx90a image runs stock
  archs only and cannot load gemma4/qwen35). Everything in the production fleet fits 64 GB HBM **except**
  the 122B architect (~78 GB). Frontdoor `qwen35moe` op-coverage remains **unverified** (clean GDN run
  was the dense-ish 27B, not the MoE hybrid) — Fable's #1 self-critique risk.

## Durable artifact: Qwen3.6-27B-MTP-Q8_0.gguf

**Problem:** we had the 27B at Q8 (`Qwen_Qwen3.6-27B-Q8_0.gguf`, 851 tensors, **no** NEXTN head) and the
MTP variant only at Q4 (`Qwen3.6-27B-MTP-Q4_K_M.gguf`, 866 tensors incl. `blk.64.nextn.*`). No Q8 self-
speculating variant, and no BF16/safetensors source on disk to quantize from.

**Root/provenance:** the existing MTP GGUFs were **downloaded** (not locally built) from unsloth via
`/mnt/raid0/llm/tmp/download_dense_mtp.sh` → repo **`unsloth/Qwen3.6-27B-MTP-GGUF`**. That repo publishes
the full quant ladder (IQ2…Q8_0…BF16) as the **bundled-MTP form** (NEXTN head fused into every quant), so
the Q8 MTP is a first-class published artifact — **direct download, no `llama-quantize` needed**. (The fork
converter *does* support `--mtp/--no-mtp` for qwen3.5/3.6 if we ever want a custom quant off the 2-part BF16.)

**Action:** single resumable curl with exact content-length verification (per the shared-host no-concurrent-
download rule; preflight found 439 GB free, no competing curl).

| Field | Value |
|---|---|
| Source | `unsloth/Qwen3.6-27B-MTP-GGUF/Qwen3.6-27B-Q8_0.gguf` |
| Dest | `/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` |
| Size | 29,047,084,160 bytes — **EXACT-MATCH** to upstream content-length |
| Verify | arch `qwen35`, name `Qwen3.6-27B`, 866 tensors incl. fused `blk.64.nextn.{eh_proj,enorm,hnorm,shared_head_norm}` |

**Result:** file in place and verified. Gives a Q8 27B **with** self-speculation — the Q8 roofline sweet-
spot (47% / 766 GB/s, 2026-07-02 obs) plus MTP's ~1.4× decode multiplier, neither available on the plain
Q8. Run self-drafting by pointing both `--model` and `-md` at this one file (embedded-head path, like the
35B frontdoor), under the HIP env `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin:/opt/rocm/lib`.

## Downstream / cross-links

- This file is the subject of the parallel operator session's **living checkpoint**
  `progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md` (P0 already logging plain-Q8 29.51 t/s
  single-stream). The acquisition here is the input to that campaign — do not duplicate its benching.
- Relates to Fable5 §4B GPU residency (findings-02) and the `speculative-decoding-mtp-refresh` /
  `gpu-drafter-mi200-investigation` handoffs.

## Deferred

- **No speed number benched by this session** — any t/s for this file needs an actual operator-approved run
  (the parallel speed campaign owns that).
- vLLM quant-vs-quant (AWQ/fp8) still unmeasured; vLLM still can't load qwen35 on the gfx90a image.
- Frontdoor `qwen35moe` op-coverage smoke still outstanding (Fable G2).

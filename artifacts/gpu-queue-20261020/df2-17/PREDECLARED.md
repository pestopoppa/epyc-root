# Predeclared rules and operational definitions (frozen 2026-10-20 BEFORE the DF2-18 Step 2 / DF2-17 / AKX-ALL-26 probe runs)

Source of the rules: the checkbox texts of DF2-17, DF2-18, AKX-ALL-26, AKX-ALL-28 (origin/main c0483ecc1). Operational definitions
below only make those rules computable; they were written before any DF2-17 data existed.

## Instrument / build
- Champion HIP build used for ALL GPU runs: /mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400 (src 4348de400, built 2026-10-06T07:50Z,
  after the commit 2026-10-06T04:40Z; SHA256SUMS verified; ROCWMMA_FATTN=ON, HIP_GRAPHS=ON, gfx90a). Live champion tip e33229348 is two
  commits later and differs ONLY in ggml/src/ggml-cpu/ggml-cpu.c (CPU-only file) -> GPU-resident forward is unchanged; recorded as a caveat.
- DF2-18 uses a source-additive copy of examples/rowexact (rowexact_margin.cpp: adds top1-top2 margins, FNV digests, --nocap) compiled
  out-of-tree against the champion build's libs; all comparison logic is the stock code (stock sha256 85bf4ddf...).

## DF2-18
- Widths 2,3,4,5,8,9 x prefixes {code, prose} (24-token prefix, sha256 in prefixes/SHA256SUMS) x A/A repeat, for BOTH capture mode (every
  graph node compared) and --nocap mode (cb_eval unset: multi-node fusions / HIP graphs active, final logits + state compared).
- Void rule: if the A/A pair (same config run twice) is not bitwise identical (node/logit digests), that config's read is VOID.
- "Attributed" node: only if its knob-off re-run removes it (the node no longer differs).

## DF2-17
- Stage 1: f16 KV, cap 1600 tokens, 12 DF2-8 prompts (/workspace/tmp/questions_mtp_ab.json), raw /completion, temp 0 / top_k 1 / seed 42,
  cache_prompt false, -np 1 --no-kv-unified, fresh server process per arm. Arms: off_A, off_B (A/A), serial_df7 (DFlash2 n-max 7 with
  LLAMA_SPEC_EXACT=serial), mtp n-max 1,2,3,5 (widths 2,3,4,6), dflash2 n-max 4 (w5), dflash2 n-max 7 (w8). ngram arm NOT run (it would
  add a run) -> DF2-6b-bis stays open with that stated reason.
- Stage 2: q8_0 KV, 24-prompt Q38-T7 production mix (prompts.json sha256 ea154096...), chat template rendered once by the server's
  /apply-template with enable_thinking=false, then raw /completion; arms off_A, off_B, serial_df7, dflash_n7.
- Per prompt, never aggregate: PASS/FAIL vs off_A; first differing generation-token index; baseline top1-top2 margin (nats, from a spec-off
  n_probs=2 pass whose tokens must equal the main pass) at that index; near-tie density of the baseline stream; generated length vs cap.
- NEAR-TIE (operational): the arm's token at the first divergence equals the baseline's top-2 token AND baseline margin < 0.5 nats (INF-70
  rule of thumb; DF2-6/8 first-divergence margins were 0.005-0.079). Margin bands <0.1 / <0.5 / >=0.5 are also reported.
- DEGENERATIVE (operational): a first divergence that is NOT a near-tie (margin >= 0.5, or the arm token is not the baseline's top-2).
  The arm output after divergence is additionally classified with the INF-70 degeneracy classifier (SALAD/EARLY-EOS/EMPTY).
- Void rule: A/A (off_A vs off_B) and serial_df7 vs off_A must be 100% token-identical on every prompt, else the stage is void.
- Verdict: DF2-8 ruling stands with a horizon caveat iff every spec-arm first divergence is a near-tie AND no graded outcome flips;
  a degenerative first divergence or a graded flip opens the per-role speculation decision (M6, Q38-T10).
- Graded outcome: where a suite has a grader (embedded tests / gold answer), pass/fail of the baseline vs arm output for each divergent pair;
  answer-extraction equality without gold is reported as a proxy and is NOT counted as a graded flip.

## AKX-ALL-26 / AKX-ALL-28
- Exactly as the checkbox text; predicted-fail list: akx-all-26/predicted_fail_list.{md,jsonl} frozen (sha256 recorded) before any probe run.
- AKX-ALL-28 pass = compiles and NMSE <= 1e-4 vs torch fp32 per config; fixed seed and shapes.

# Windowed-MTP: Removing the Full-Context Draft-KV Tax at Million-Token Context

- **Intake**: intake-2739 (`intake-2739#record`)
- **Source**: https://arxiv.org/html/2607.21535v2
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: autokernel-akx-program.md, speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Use as the design prior for the draft-only window on Q38FN (W 2k-8k, sink 32-64). Do not quote its 1M-context speedups as 32k-64k expectations; dense-attention targets are untested.

## Key claims (anchored)

0. Windowing only the MTP draft attention (sink plus recent window) is training-free and drop-in; target verification stays full-context, so the target distribution is preserved.
   - Abstract: "We apply a StreamingLLM-style window plus attention sink to the draft only ( Windowed-MTP ); target verification remains full-context, so the target distribution is preserved. The intervention is training-free and drop-in."
1. At 1M context every window from 1K to 8K beats native full-context MTP on all three tested hybrid models, and a 32-token sink recovers the no-sink acceptance loss with no tuning needed from 32 to 128.
   - Sec 5 Window size: "every window from 1K to 8K beats native on every model"
   - Sec 5 Sink size: "the median ratio to sink 64 64 stays within 0.02 0.02 , so the sink size needs no tuning either."
2. Acceptance usually changes little but not always: one model loses 19% median acceptance length on one task and 16% on another while still gaining end to end.
   - Sec 5 Per-position: "median loss is 19 % 19\% on NIAH-mv and 16 % 16\% on VT, giving end-to-end gains of 1.15 × 1.15\times and 1.21 × 1.21\times"
3. The draft-KV tax appears once draft KV leaves on-chip cache, and lower-precision KV shrinks the relative gain.
   - Sec 3: "More on-chip capacity or bandwidth moves the context length at which the tax appears; it does not remove it."
   - App E: "lower-precision KV shrinks the relative gain to the extent decode is KV-bandwidth bound"
4. DFlash drafters keep full-context draft KV too and are left as future work; the explanation of why acceptance holds is specific to hybrid targets.
   - Sec 7: "Block-diffusion drafters such as DFlash [ Chen et al., 2026 ] keep full-context KV in each draft layer too; measuring windowing on them is future work."
   - Sec 5: "The argument is specific to hybrid targets; a draft on a dense-attention model may lean more on distant context. We treat it as interpretation, not proof."

## Dive record

2026-11-20 Stage-2b dive (opus; full read; surfaced by intake-2725). Confirms option (1) of Q38FN-DRAFT-FA-WINDOW (autokernel-akx-program.md:L1294 @b5c5fe7) with priors: operating point W=4032, sink 64; W 960-8128 all net-positive at 1M on Qwen3.6-35B-A3B, Qwen3.5-122B-A10B and Nemotron-3-Super (NVFP4, bf16 KV, B200; H100 FP8 replication); 32k-64k contexts not measured; dense-attention targets untested. Argues (unmeasured) against routing via dynamic top-k selection. In-house: Q38FN draft/FLASH_ATTN 0.98 / 26.2 / 39.2 ms at d1k/d32k/d64k (q38fn-cpu-perop-profile-20261118-r2 RESULT.json); the draft head attends densely (C14 qwen4exp.cpp L422-424, build_attn L537 @eee3da8); the MTP context gets a separate plain KV cache (llama-model.cpp L2283-2287, L2412-2414), with an iswa precedent for DEEPSEEK4 MTP (L2208-2230); no sink-aware SWA type exists (llama-hparams.h L24-27). Projection (inferred, linear in n_kv at constant acceptance): W~4k saves ~22 ms of a 144 ms step at 32k. The served recipe sets GGML_FA_SPLIT_KV=0, so a draft-context split-KV A/B is a no-acceptance-risk co-lever (inferred). DFlash2 27B drafter is already SWA 2048 (kv-cache-program.md:L119,L126 @b5c5fe7). MI210 A3B MTP (n-max 2, short context) likely small gain. Adversarial: SGLang docs show a DFlash draft-window flag (independent); the paper's MTP flag/PR not confirmed. Surfaced arXiv 2605.09992 (wave-2 candidate, id to verify); repo, SpecExtend 2505.20776 and MiMo-V2-Flash 2601.02780 declined. lane_head b5c5fe7b4e63

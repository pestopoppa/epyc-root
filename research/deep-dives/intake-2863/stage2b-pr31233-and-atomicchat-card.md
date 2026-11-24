# intake-2863 Stage 2b — PR #31233 and the AtomicChat Inkling 2 Mini GGUF card

## intake-2865 — llama.cpp PR #31233 (moe-cache ClassLRU)
Merged 2026-11-06 (merge `c4fb5796`, head `515064f5`). Eight LRU classes ranked by a decaying CRF score (half-life 128 tokens), history kept after eviction. Author reports +6% decode (QFN) and +7% (GLM) vs SLRU with 8% fewer uploads, warm cache. The atomic-engine `inkling-loop-age` policy is this algorithm with a 512 half-life. Settles H6: the device expert cache exists upstream; HIP path not checked. Disposition: knowledge only, trigger prose in INK2-MI210-PLACE-1.

## intake-2866 — AtomicChat/Inkling-2-Mini-GGUF card (commit 30950984)
- Q8_0 reaches only 97.7% top-1 vs BF16; 97-98% is the ceiling for this looped model.
- AD-IQ2_M: top-1 85.7%, KLD 0.130 (expert down Q2_0 outside the 8 busiest layers) — overturns H4 for that file. AD-IQ3_S 94.2%/0.0205, AD-IQ4_XS 95.8%/0.0101, AD-Q4_K 96.3%/0.0080.
- DSpark on one A100, 3 non-repetitive greedy prompts: AD-Q4_K 46.4 -> 62.7 tok/s (+35.0%), acceptance 44.9%; drafter-on output diverged from drafter-off at the same positions for BF16 and Q8_0 drafters.
- Only 4 of 24 physical layers are full attention.

## Effect on the plan
INK2-MEAS-2 arms are AD-IQ4_XS and AD-IQ3_S with KLD, not AD-IQ2_M. INK2-PORT-2d's equivalence check tolerates a logit near-tie at the first divergence.

Artifact audit: clean (/mnt/raid0/llm/tmp/dive-2863b/).

# Memory-Efficient Speculative Decoding with Quantized Draft KV Cache

- **Intake**: intake-2726 (`intake-2726#record`)
- **Source**: https://arxiv.org/html/2611.20565v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: autokernel-akx-program.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Do not use this paper to explain llama.cpp #25725 (that was a rotation bug, intake-1262). Draft-only KV quantization is a quality result under fake quantization with greedy decoding; no speed claim.

## Key claims (anchored)

0. Only the draft model KV cache is quantized; the tested drafters are ordinary autoregressive models of 360M-8B with their own KV; no DFlash or feature-conditioned drafter was tested.
   - Sec 4: "Model sizes range from 360M to 8B parameters."
   - Sec 4: "The draft proposes up to four tokens per round, and each run generates 16 tokens."
1. Key-versus-value bit preference depends on quantizer layout: per-token keys favour more key bits, grouped per-channel keys remove that advantage.
   - Sec 3: "Our simple baseline uses one symmetric scale for each token and KV head."
   - Sec 5.1 RQ1: "switching to grouped per-channel keys eliminates this advantage, shifting the contrast to"
2. K4V4 with 32-token per-channel key groups and per-token value groups cuts draft cache memory by 66.20% and combined memory by 23.95%; mean acceptance drops from 57.93% to 57.14%.
   - Sec 3: "our layout instead uses 32-token per-channel key groups and per-token value groups within each head"
   - Abstract: "Across six model pairs, our method reduces draft cache memory by 66.20%, and combined memory across both caches by 23.95%."
   - Abstract: "Mean acceptance drops from 57.93% to 57.14%, only 1.36% relative."
3. Quality was measured with fake quantization; the packed prototype is 18-33% slower than BF16 speculative decoding and the paper claims neither faster decoding nor stochastic-sampling results.
   - Sec 5.3 RQ3: "packed K4V4 stores 67% to 71% fewer draft cache bytes, but it is 18% to 33% slower than BF16 speculative decoding"
   - App H: "We do not claim faster kernels or decoding, or lower peak GPU memory."
   - App H: "We do not claim that our results hold under stochastic sampling."

## Claim corrections

- claim 0: **unaffected** — Confirmed; sequential verifier exact.
- claim 2: **narrowed** — Greedy only, 16-token generations, drafters <= 8B, autoregressive drafters only.

## Dive record

2026-11-20 Stage-2 dive (opus; full read). OVERTURNS the steering contrast: the llama.cpp #25725 DFlash collapse was un-rotated injected K/V in a Hadamard-rotated quantized cache, present even at q8_0, fixed in C14 (src/models/dflash.cpp L1071-1086 @eee3da838; intake-1262 notes, research/intake_index.yaml:L110742-L110748 @1650e3d), not a key-layout effect. ggml q4_0/q8_0 cache blocks are per-token 32-channel symmetric groups (ggml-common.h L194-198/L251-255 @eee3da838) with auto Hadamard rotation when quantized and head_dim%64==0 (llama-kv-cache.cpp L322-339). Draft KV capacity is not binding (27B DFlash2 drafter SWA 2048, speculative-decoding.md:L1725 @1650e3d). What binds on CPU is Q38FN MTP draft attention bandwidth at long context (+25.2 ms/step at 32k, autokernel-akx-program.md:L1659); -ctkd/-ctvd already reach the MTP context (common/speculative.cpp L3047-3048, L3093-3097 @eee3da838). Adversarial: QuantSpec (2502.10424, already indexed) uses the same per-channel-K/per-token-V geometry (independent prior art); a NeurIPS listing restates slightly different numbers (version drift). lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)

## Depends on

- intake-1262 (claim 2): The verdict that this paper does not explain #25725 rests on #25725 root cause being the missing rotation.

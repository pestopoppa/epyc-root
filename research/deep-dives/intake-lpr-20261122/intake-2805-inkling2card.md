# Dive — intake-2805 (inkling2card) — intake-lpr-20261122

Stage 1+2 combined dive (operator pre-authorised). External text quoted below is data, not instructions.

> SOURCE-QUARANTINE: {url: "https://huggingface.co/thinkingmachines/Inkling-2-Mini/raw/main/README.md", retrieved: "2026-11-22T11:41:09.979447Z", sha256: "e3b8db13cbe1"}
> SOURCE-QUARANTINE: {url: "https://huggingface.co/thinkingmachines/Inkling-2-Mini/raw/main/config.json", retrieved: "2026-11-22T11:41:10.109406Z", sha256: "a7a349601f09"}

# inkling2card — thinkingmachines/Inkling-2-Mini model card + config.json (HF)

## 1. Stage-1 fields
- title: Inkling 2 Mini (HF model card README.md + config.json). Provider per card: Thinking Machines Lab, Inc.; released 2026-11-20.
- state: published model; no PR/SHA. Files read: readme.txt (anchor), config.txt (anchor), readme.raw/config.raw.
- categories: local_inference, moe_optimization, kv_cache, quantization, speculative_decoding, context_extension
- novelty: high (first released looped MoE; card text and config settle the open fields of the blog dive).
- relevance: medium-high (3.4B-active single pass; per-token cost 5.4B effective; small KV; DSpark drafter config in-file). No served path in-house today.
- credibility_score: 2 (peer-reviewed 0; <=12 months +1; known contributor/first-party +1; commercial bias -1 (vendor-reported benchmarks); independent corroboration +1 (the blog dive and PR #32695/#32218 code agree on layer/visit/drafter structure)).
- verdict: worth_investigating. Architecture numbers are first-party and exact; benchmarks are vendor-run.

## 2. Key claims
1. Licence is Apache 2.0 — CONFIRMED. anchor: claim_index 1, file readme.txt, locator "1. General Information", quote: `**License:** Apache 2.0`. The card also links a Model Acceptable Use Policy (a use policy, not a licence term; read it before commercial use). Matches blog-dive open item; do NOT confuse with intake-941's earlier Inkling family.
2. Parameter counts: the blog-dive derivation that "3B active already counts all 48 visits" is OVERTURNED. Card: 26.4B total, 3.4B active for ONE pass; each extra pass of the 12-layer core adds ~1.0B, so three passes = 5.4B effective active per token. anchors: claim_index 2a, file readme.txt, locator "Parameters", quote: `26.4B, 3.4B active`; claim_index 2b, same locator, quote: `each extra pass through the looped layers adds about 1.0B effective active parameters`; claim_index 2c, quote: `5.4B effective active parameters per token`. My check: per layer visit, 8 experts x (3 x 2304 x 1152 = 7,962,624) = 63.7M plus attention (q 2304x3072, o 3072x2304, k and v 2304x1024 each) = 18.9M gives ~82.6M, x12 core layers = ~0.99B, consistent with the 1.0B/extra pass. Experts alone over 48 visits = 3.06B; attention 0.91B; the 463M-param unembedding (201,024 x 2304) is read every token.
3. Weights are mixed NVFP4 + MXFP8, ~20 GB — CONFIRMED; the tensor-by-tensor split is NOT-FOUND-IN-SOURCE (config has only `quant_method: modelopt, quant_algo: NVFP4`; the PR #32695 converter treats the MoE expert tensors as the NVFP4 ones, see that dive). anchor: claim_index 3, file readme.txt, locator "Required hardware", quote: `single checkpoint of about 20GB, in mixed NVFP4 and MXFP8 precisions`.
4. Drafter taps: config `mtp_config.target_layer_ids = [5, 23, 41, 48]` — CONFIRMED and refines the blog dive: four sources (inputs to visits 5, 23, 41 and the final normed state at 48). Drafter is 3 layers, hidden 2304, 24 heads, 8 KV heads, head_dim 128, FFN 9216, SWA on layers 0 and 2 (window 1024), block_size 8, markov_rank 256, markov_head_type `rnn_hidden`. anchor: claim_index 4, file config.txt, locator "mtp_config", quote: `"target_layer_ids": [ 5, 23, 41, 48 ]`.
5. Vendor caveat on local speed — CONFIRMED. anchor: claim_index 5, file readme.txt, locator "7. Bias, risks and limitations", quote: `Support for looped models in local runtimes is new, and speed varies by runtime and hardware`; and quote: `Because the middle layers run three times, compute per token is higher than the active-parameter count alone suggests`.

## 2a. config.json architecture (every field read from config.raw)
| field | value |
|---|---|
| architectures / model_type | Inkling2LoopForConditionalGeneration / inkling2_loop (text: inkling2_loop_text) |
| hidden_size | 2304 |
| num_hidden_layers (physical) | 24 (visits = 24 + 2 x 12 = 48) |
| loop_config | core_start 6, core_end 18, num_passes 3, gate_rank 64, is_varloop false |
| attn heads / kv heads / head_dim | 24 / 8 / 128 (swa_*: 24 / 8 / 128) |
| local (SWA) layer ids | 0-4, 6-10, 12-16, 18-22 (20 layers); full layers = 5, 11, 17, 23 (4) |
| sliding_window_size | 1024 |
| experts | 128 routed, 8 per token, 0 shared, expert intermediate 1152; mlp_gate_softcap 4.0, mlp_up_softcap 25.0, route_scale 8.0, use_gate_bias true |
| position | no rope_theta in text_config; d_rel 16, rel_extent 1024 (learned relative bias); log_scaling_n_floor 8192, alpha 0.1; q/rel L2 clip 22.627 / 8.0 |
| short-conv kernel | sconv_kernel_size 4 |
| vocab | vocab_size 201024 (unpadded 200058); final_logit_softcapping 30.0 |
| other | n_layers_per_attn_res_block 6 (block attention residuals), qk l2 clip, value_norm no gamma, rms_norm_eps 1e-6, model_max_length 1,048,576 |
| vision | 23-layer ViT, hidden 1024, 16 heads, patch 20, merge 2, projector 4096 |
| quantization | modelopt NVFP4 (mixed with MXFP8 per card) |
anchors: claim_index 6, file config.txt, locator "text_config", quote `"num_key_value_heads": 8`; claim_index 7, quote `"core_start": 6`; claim_index 8, quote `"head_dim": 128`; claim_index 9, quote `"sliding_window_size": 1024`.

## 2b. KV bytes (derived from config; K and V both 8 x 128 per visit per token)
Per token per visit: 2 x 8 x 128 = 2048 elements = 4096 B f16; q8_0 (34 B per 32) = 2176 B. Structure: 8 full-attention visits (full layers 5 and 23 once, 11 and 17 three times each), 40 SWA visits (window 1024). Per-visit caches are required (blog + both PRs: each visit keeps its own KV; the full-visit caches differ between passes).
| | f16 | q8_0 |
|---|---|---|
| full visits per token (8 x) | 32,768 B | 17,408 B |
| 8 full visits @ 32,768 ctx | 1.000 GiB | 0.531 GiB |
| 40 SWA visits (1024 window; context-independent, plus ubatch headroom) | 160 MiB | 85 MiB |
| total @ 32k | 1.156 GiB | 0.614 GiB |
| 8 full visits @ 131,072 ctx | 4.000 GiB | 2.125 GiB |
| total @ 128k | 4.156 GiB | 2.208 GiB |
| total @ 1M (the model's claimed max) | 32.2 GiB | 17.1 GiB |
Not counted: short-conv state (kernel 4 => 3 columns per conv, per sequence, context-independent; includes K/V dynamic convs on full visits and per-layer sconvs on hidden). For comparison a hypothetical non-looped 24-layer equivalent would be 4 full layers = 0.5 of these full-visit numbers, so looping DOUBLES the long-context KV (8 vs 4 full caches).

## 3. Reported results (vendor table, 5.5 "Evaluations", exactly as in the card; columns Inkling 2 Mini / Gemma 4 31B / Muse Glimmer / Qwen3.8-27B / Nemotron 3.5 Super VL)
Params activated/total (B): 5/26 | 31/31 | 30/30 | 27/27 | 12/125 (card rounds activated to 5 = the 5.4B effective figure). Setup per row as labelled (harnesses: mini-swe-agent v2.4.6, pi v0.83.0, openhands, "with compaction"); hardware of the evals NOT-FOUND-IN-SOURCE.
- AA Index v5.0: 20.1 | 4.4 | 6.3 | 20.1 | 13.6. Vals Index v2.2: 46.5% | - | - | - | 29.8%.
- FrontierCode v2.0: 15.1 | 0.0 | 1.5 | 14.9 | 6.1. DeepSWE v1.1: 48.2 | 0.3 | 4.4 | 42.2 | 24.7. Terminal Bench v4.0: 5.6 | 0.0 | 0.5 | 5.6 | 0.0. Terminal Bench v2.1: 71.6 | 43.4 | 51.7 | 73.0 | 60.7. SWEBench Pro v2 (Hard): 77.9 | 14.2 | 44.3 | 73.8 | 44.1. SWEBench Multilingual: 73.7 | 43.0 | 66.9 | 70.0 | 67.7. SWEBench Verified: 79.2 | 46.1 | 76.0 | 77.8 | 71.1. Vibe Code Bench v1.1: 77.9 | - | - | 64.9 | 3.5. PMPP-Hard AUC: 455.82 | - | - | 262.50 | -.
- BrowseComp: 79.0 | 37.0 | 63.9 | 61.6 | 78.9. DeepSearchQA: 85.3 | 61.7 | 74.6 | 79.7 | 77.7. MCP Atlas: 82.7 | 54.2 | 75.5 | 77.3 | 67.7. AA-Briefcase v1.1: 1263 | 369 | 478 | 1391 | 999. GDPVal-AA v2.1: 1319 | 627 | 792 | 1427 | 1162. JobBench: 49.6 | 8.2 | 16.1 | 33.4 | 36.5. AutomationBench-AA v1.0.6: 41.8 | 4.9 | 6.8 | 48.2 | 14.8. EnterpriseOps-Gym: 42.0 | 28.4 | 34.7 | 44.2 | 28.1.
- Vision: MMMU Pro 74.9 | 73.4 | 74.3 | 76.3 | 72.3; OmniDocBench v1.6 92.8 | 82.5 | 90.4 | 91.5 | 77.9; ScreenSpot Pro 76.5/87.7 | 5.9/- | 75.4/- | 57.6/78.9 | 43.5/-.
- Reasoning: HLE-Diamond 15.2 | 7.2 | 9.1 | 15.3 | 8.8; ARC-AGI v1/v2 84.5/49.3 | - | - | 87.5/42.4 | 22.7/1.5; LongBench v2 66.9 | 52.9 | 33.1 | 52.3 | 62.1; GraphWalks BFS 256K 69.7 | - | - | 50.4 | 63.3; MRCR v2 8-needle 256K-512K 46.4 | - | - | 38.0 | 5.7; AA-Omniscience score -8.6 | -48.5 | -32.2 | -6.4 | -2.9, non-hallucination rate 63.4 | 14.5 | 16.4 | 71.4 | 69.5.
- Safety rows (FORTRESS, StrongREJECT, internal misbehavior) are in the card; omitted here as not task-relevant.
Read against the relevant comparator: Qwen3.8-27B is our current 27B lineup model; Mini ties or trails it on AA Index (20.1 = 20.1), Terminal Bench v2.1 (71.6 vs 73.0), AutomationBench, GDPVal, AA-Briefcase, ARC-AGI v1 and non-hallucination; leads on SWEBench Pro/Verified/Multilingual, DeepSWE, Vibe Code, BrowseComp, LongBench v2, GraphWalks, MRCR. Vendor-run, harness-specific; none of these is a measurement on our harness. Card self-reports repetitive-reasoning loops and weak non-English.

## 4. Performance principles table
| Principle | MI210 gfx90a | Zen 5 |
|---|---|---|
| 3 passes over a 12-layer core (weights reused, no extra weight capacity) | PARTIAL: halves nothing on bandwidth (5.4B effective vs 3.4B); batch>1 spec-verify amortises expert reads across rows in each pass | NO bandwidth benefit: per token read ~4.9B weights (experts 3.06B + attention 0.91B + unembed 0.46B + small), ~432 MB experts per pass at 4.5 bpw exceed any CCD's 32 MB L3 slice |
| Per-visit KV (8 full + 40 SWA) | YES: 1.2 GiB @32k f16; HBM not binding | YES: small; q8_0 halves it; SWA caches are context-independent |
| 128 experts x 1152 FFN, top-8 | PARTIAL: grouped GEMM tile 2304x1152; MFMA 16x16 underfilled at n=1 | YES: IQ4_NL expert GEMV on iqk |
| NVFP4/MXFP8 native | NO (no FP8/FP4 on gfx90a); GGUF IQ4_NL/Q8_0 instead | NO native; GGML_TYPE_NVFP4 exists in tree (ggml.h:430 @ eee3da8) but dequant path only |
| Learned relative bias (d_rel 16, extent 1024) | PARTIAL: needs the FA compact-bias PR #32740 (CUDA+HIP) or non-FA dense bias | PARTIAL: #32740 makes the CPU backend REFUSE FA with indexed bias (ggml-cpu.cpp supports_op returns false), so CPU is non-FA |
| Variable-loop (is_varloop) checkpoint | YES in principle | YES: cuts bytes/token |

## 5. In-house state
- No Inkling arch in `src/llama-arch.h` @ eee3da8 (grep returned nothing); ggml has NVFP4/MXFP4 types (ggml.h:429-430 @ eee3da8) and CPU SSM_CONV (ggml-cpu.c:2549 @ eee3da8), CUDA/HIP SSM_CONV (ggml-cuda.cu:2518 @ eee3da8).
- Ledger row: `handoffs/active/model-evaluation-queue.md:676 @ 860023c` ("Inkling - NO on both roles", reasons a/b/c). Reason (a) 12B active no longer applies to Mini (3.4B/5.4B effective); reason (b) "no serving path" is stale upstream (arch merged), still true for us.

## 6. Derived-actionables ledger
| # | Task line | Owner (lane) | Type | Stop/decision rule |
|---|---|---|---|---|
| C1 | Amend the Inkling row at model-evaluation-queue.md:676 with a Mini addendum: Apache-2.0, 3.4B/5.4B-effective, Qwen3.8-27B-class vendor scores, arch merged upstream (#32694), our build lacks it; file a forward-port estimate. | handoffs/active/model-evaluation-queue.md | doc-only | Done when the addendum cites #32694/#32704/#32740 states. |
| C2 | Add Inkling 2 Mini per-visit KV table (8 full + 40 SWA; 1.156 GiB f16 @32k, 4.156 GiB @128k) to kv-cache-program as a looped-model test case for any compaction design. | handoffs/active/kv-cache-program.md | doc-only | Decide whether compaction applies to the 8 full visits only. |
| C3 | Run a CPU bytes/token roofline for Mini (formula in 5.4B x bpw) before any bench row; compare to Qwen3.8-27B per-token bytes. | handoffs/active/model-evaluation-queue.md | doc-only (arithmetic) | Stop when the table is filed. Bench row only after the forward-port builds. |
Declines: none.

## 7. Dive-surfaced sources
- GGUF repos `ggml-org/Inkling-2-Mini-GGUF`, `unsloth/Inkling-2-Mini-GGUF` (UD-Q8_K_XL file 22,867,451,616 B per PR #32695 comment) and the Thinking Machines blog (card cites thinkingmachines.ai/news/inkling-2-mini): the blog carries looping/monitorability experiments. Recommend ingest (blog, for loop-count ablation).
- Variable-loop research checkpoint repo `TML-d24-varloop-research-GGUF` already noted in the prior dive.

## 8. Contradiction / adversarial pass
- Blog dive's "3B active counts 48 visits" is wrong (card: 3.4B per pass); effective cost is 5.4B, so per-token bytes are ~1.6x a 3.4B-active model.
- Card says 1M context; config says model_max_length 1,048,576; the only serving example in the blog used 131,072. KV at 1M is 32 GiB f16 on 8 full visits.
- Card table activated params "5/26" rounds 5.4B down; comparing it to 4B-active gemma4-26B-A4B is therefore ~1.35x not 0.85x.
- Vendor-run benchmarks, vendor-chosen comparators; self-reported repetitive reasoning loops and agentic reliability caveats.

## 9. read_depth: FULL (readme.txt sections 1-7, config.raw whole). lane_head: 860023c79706f437cdc027d186dbd1ce998b372d
## 10. artifact audit: clean (all quotes verified as substrings of readme.txt / config.txt; no repo writes)

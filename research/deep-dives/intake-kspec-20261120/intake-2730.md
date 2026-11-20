# QDA: Closed-Loop LLM Quantization Design with Agents

- **Intake**: intake-2730 (`intake-2730#record`)
- **Source**: https://arxiv.org/html/2611.23388v1
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: integrated; handoffs: quantization-and-low-bit.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Adopt the evaluation ideas (held-out KL, long-generation loop/truncation check). Its recipe space is vLLM/llm-compressor formats, not GGUF; do not cite its accuracy gains as GGUF expectations.

## Key claims (anchored)

0. QDA scores each candidate recipe in minutes by output KL against the original model on reasoning traces the agent never sees.
   - Abstract: "scores each candidate in minutes by its output KL divergence from the original model on reasoning traces that the agent never sees"
   - Appendix C: "On one GH200, a KL score takes 3.2–4.0 GPU-minutes on DeepSeek-R1-Distill-Llama-8B"
1. KL orders 82% of 44 checkpoint pairs as their accuracy does, against 73% for layer-wise error.
   - Sec 4.2: "The KL orders 82% of the pairs as their accuracy does, against 73% for the layer-wise error."
2. Long-generation checks (up to 81,920 tokens) catch failures KL misses, counting answers that are wrong, loop or are cut off.
   - Sec 4.3: "this checkpoint cut off 12 of 191 answers at the length limit, against 3 for the original model"
   - App E task statement: "Run long-generation checks (up to 81,920 tokens) on the top checkpoints in all four domains before submitting."
   - Sec 4.3: "It counts the answers that are wrong, loop or are cut off, and weighs these counts together with the KL to decide what to change."
3. QDA improves average accuracy over the strongest public recipe by 0.9, 1.4 and 2.2 points; admissible recipes run on existing kernels with no new operator, in llm-compressor/vLLM formats, not GGUF.
   - Sec 6.2: "QDA improves the average accuracy over the strongest public recipe by 0.9, 1.4 and 2.2 points"
   - Sec 4.1: "and run on their kernels with no new operator"

## Claim corrections

- claim 3: **narrowed** — Recipe space is llm-compressor/vLLM GPU formats on 8x GH200 per search; the evaluation protocol transfers, the recipe space does not.
- claim 1: **unaffected** — n=44 pairs, no interval.

## Dive record

2026-11-20 Stage-2 dive (sonnet; PARTIAL: Appendix C/D tables skimmed, references skipped). Scoring is cached top-128 KL plus a tail bucket (a lower bound on full KL), 3-12 GPU-minutes per score on GH200 for 8-27B. Qwen3.8-27B W4A16 QDA 79.8 vs BF16 79.5 (Table 2). The transferable parts for us: a long-generation loop/truncation counter beside KLD, and calibration-data choice tested with llama-imatrix + KLD. In-house: llama-quantize per-tensor type maps exist (quantize.cpp L410-L462 @ffc1bac82); the bytes-budgeted per-tensor allocator NEW-12 is operator-held (quantization-and-low-bit.md:L687 @e9ee76c); 27B Q4_K_M vs Q8_0 mean KLD 0.007607 (L97). The 27B KLD<=0.003 threshold was not found in handoffs by grep (memory only). Adversarial pass not run. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)

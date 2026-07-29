# MemAgent: RL-Trained Memory Agent for Long Context (Deep Dive)

**Paper**: arXiv 2507.02259 | **Authors**: Yu et al. (ByteDance / Tsinghua SIA Lab)
**Code**: https://github.com/BytedTsinghua-SIA/MemAgent
**Model**: https://huggingface.co/BytedTsinghua-SIA/RL-MemoryAgent-14B
**Intake**: intake-156

## Core Architecture

Reformulates long-document QA as sequential segment-reading with fixed-size memory buffer.

### Processing Loop

For each segment k (fixed 5,000 tokens):
1. Input: question + accumulated memory `m^(k-1)` + current segment `c^k`
2. Output: new memory `m^k` (free-form natural language, capped at 1,024 tokens)
3. Memory **completely overwrites** previous — no append, no DAG, no structured store

Final answer: question + final memory `m^K` → answer in `\boxed{}` format.

**Total context per call**: ~8K tokens (5K segment + 1K memory + 1K query + 1K output).
**Extrapolation**: 8K training → 3.5M test = **437.5x**.

### Theoretical Framework

Latent variable model: `p(x_{1:N}) = Sum_m Prod_k [p(c^k|m^{k-1}) * p(m^k|c^k, m^{k-1})]`
Enables O(N) linear complexity vs O(N^2) standard attention.

## Multi-Conversation DAPO Training

**DAPO** (Direct Advantage Policy Optimization, 2503.14476) extended to 3 dimensions: **(group, conversation, token)**.

K segments produce K independent conversations. Reward only from final conversation (answer correctness). Advantage broadcast uniformly:
```
A_hat(i, j, t) = r(i) - mean({R(i)})  # same for all conversations j in sample i
```

| Parameter | Value |
|-----------|-------|
| Base models | Qwen2.5-7B/14B-Instruct |
| Training data | 32,768 HotpotQA samples (~28K tokens each, ~6 segments) |
| Learning rate | 1e-6, constant + linear warmup |
| Group size | 16 |
| KL penalty | 1e-3 |
| Framework | verl |

Anti-reward-hacking: strict `\boxed{}` verification in training, lenient in testing.
Data filtering: removed ~50% of questions answerable without context (common knowledge).

## Key Results

### RULER-HotpotQA (Primary)

| Model | 7K | 28K | 112K | 448K | 896K | 3.5M |
|---|---|---|---|---|---|---|
| **RL-MemAgent-14B** | **83.6** | **84.4** | **76.6** | **75.0** | **77.3** | **78.1** |
| **RL-MemAgent-7B** | **82.0** | **78.9** | **79.7** | **74.2** | **76.6** | **71.1** |
| QwenLong-L1-32B | 72.7 | 72.7 | 31.3 | 13.3 | 11.7 | N/A |
| Qwen2.5-14B-1M | 60.2 | 50.0 | 50.0 | 8.6 | 0.0 | N/A |
| DS-R1-Distill-32B | 70.3 | 65.6 | 23.4 | 7.8 | 7.0 | N/A |

- All baselines collapse beyond 224K; MemAgent maintains 70-80% through 3.5M
- 14B MemAgent beats 32B QwenLong-L1 at ALL lengths
- >95% average on standard RULER tasks 8K-512K (OOD — trained only on HotpotQA)

### Degradation at Extremes

| Model | 7K → 3.5M degradation |
|-------|----------------------|
| MemAgent-14B | -5.47 pp |
| MemAgent-7B | -10.94 pp |

## Ablations

RL training is critical:
- Vanilla Qwen2.5: severe degradation beyond 112K
- Memory agent (prompted, no RL): better but still declines
- RL-trained MemAgent: near-flat ~80% across range

### Missing Ablations (Notable Gaps)
- Overwrite vs append strategy
- Segment size sensitivity (5K fixed throughout)
- Memory size sensitivity (1,024 fixed)
- Number of training segments
- Alternative reward shaping (uniform advantage only)

## Failure Modes

1. **Irreversible information loss**: overwritten facts cannot be recovered
2. **Memory capacity ceiling**: 1,024 tokens hard cap
3. **Single-question bias**: must reprocess entire document for different query
4. **7B degradation**: ~11pp at 3.5M suggests memory management needs model capacity
5. **Sequential bottleneck**: K segments = K sequential inference calls, no parallelism
6. **No streaming/backtracking**: cannot re-read earlier segments

## EPYC Applicability

### Not Viable for CPU Inference (Direct Adoption)

Per-segment overhead on EPYC 9655 (Qwen2.5-14B @ Q4_K_M, ~14 t/s):
- ~1K output tokens per segment → ~73 seconds each
- 100K document (20 segments): ~24 minutes
- 3.5M document (700 segments): ~14 hours

Sequential chain is the killer — no parallelism possible.

### Valuable Concepts to Extract

1. **RL-trained compaction quality**: Train a compaction model with GRPO/DAPO where reward = downstream task success. Could improve our `session_compaction` without changing architecture.
2. **Fixed-size memory buffer**: Our compaction should target a fixed token budget (not percentage-based).
3. **Question-guided compaction**: When task type is known (coding, QA, review), guide compaction by relevance.
4. **Multi-conv advantage broadcasting**: Same pattern as ReSum-GRPO — applicable to MemRL routing training.

### Comparison with Alternatives

| Approach | Representation | Loss | Overhead |
|----------|---------------|------|----------|
| MemAgent | 1K prose (overwrite) | Lossy | K inference calls |
| Lossless Claw | DAG of nodes | Near-lossless | O(N) storage |
| CMV | Structured vectors | Near-lossless with spill | O(N) storage |
| YaRN | Same model (RoPE scaling) | None (native) | Zero |

For our 32K-128K native windows: **YaRN is the right tool**. MemAgent relevant only for >128K single-query QA where latency is acceptable.

### Hybrid Recommendation

For documents >128K: YaRN for first 128K, then MemAgent-style chunked processing for overflow using smallest model (Qwen2.5-7B) for memory updates, full model for final answer only.

## Key References
- DAPO: 2503.14476
- GRPO/DeepSeekMath: 2402.03300
- HotpotQA: 1809.09600
- RULER: 2404.06654
- YaRN: 2309.00071
- S4/Mamba: 2111.00396, 2312.00752
- verl (HybridFlow): 2409.19256

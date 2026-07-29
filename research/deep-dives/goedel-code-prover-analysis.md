# Goedel-Code-Prover: Deep Dive Analysis

**Intake ID**: intake-233
**Paper**: arxiv:2603.19329 (2026-03-18)
**Team**: ETH Zürich, Princeton Language & Intelligence, Princeton University, MiroMind
**License**: MIT

## Architecture

Vanilla Qwen3-8B — no architectural modifications. All innovation is in training methodology and inference pipeline. Standard llama.cpp GGUF conversion works directly.

## Training Pipeline

### Stage 1 — SFT
- 432K trajectories (281K decomposition + 151K completion) from GPT-5.2 / Gemini-3-Flash teachers
- LLaMA-Factory, 3 epochs, lr=1e-5, max context 10,240 tokens, batch 128

### Stage 2 — Hybrid RL (GRPO + SFT replay)
- GRPO using verl framework, 100 steps, 4×4 GPUs
- 64 prompts × 8 parallel generations per prompt, mini-batch 256
- Auxiliary SFT loss (λ=0.08) on proof completion prevents regression
- Online lemma collection: successful proofs recycled into training pool

## Decomposition Score Formula

```
S = r(L₁,...,Lₖ; G) × v(L₁,...,Lₖ; G)

v = 1_proof × ∏ᵢ 1_qc(Lᵢ)     (binary: proof reconstructs AND QuickCheck passes)
r = max(1 - d̄/d(G), 0)          (reduction ratio via log-sum-exp aggregate)
d̄ = T × log(Σᵢ exp(d(Lᵢ)/T))   (smoothed difficulty aggregate)
```

Same score used as RL reward AND inference-time ranking — strict alignment.

## Inference Pipeline

### Stage 1 — Decompose (up to 128 iterations, max 32 lemmas)
1. Parse theorem into LeanCodeTree
2. Select highest-complexity target (softmax-weighted)
3. LLM generates helper lemmas + proof sketch
4. Lean server verifies compilation; QuickCheck tests counterexamples
5. Score with S, keep best decomposition

### Stage 2 — Prove (up to 128 epochs per lemma)
Three phases per epoch: Prove/Fix → Eliminate → Sorry Replace
Uses SEARCH/REPLACE diffs. pass@k with k=10, wall-clock budget 30 min/problem.

## Results

| Benchmark | Tasks | Goedel-CP-8B | Best Baseline (BFS-Prover-V2, 32B) |
|-----------|-------|-------------|-------------------------------------|
| Verina | 189 | 68.8% | ~24% |
| Clever | 161 | 54.0% | ~24% |
| AlgoVeri | 77 | 62.3% | ~21% |
| **Overall** | **427** | **62.0%** | **23.8%** |

2.6× over strongest baseline. Outperforms models 4-84× larger (32B-671B) and GPT-5.3-Codex (18.5%).

**Caveat**: Different inference paradigms — baselines use parallel whole-proof generation (pass@128), Goedel uses search-based hierarchical inference.

## Ablation (Verina)

| Decomposition | Completion | Score |
|--------------|-----------|-------|
| None | Gemini-3-Flash | 26.4% |
| GPT-5.2-Pro | Gemini-3-Flash | 54.4% |
| Trained | Gemini-3-Flash | 58.2% |
| GPT-5.2-Pro | Trained | 59.2% |
| Trained | Trained | 68.7% |

Decomposition alone worth +28pp. Joint training shows synergy.
Decomposition score AUROC: 0.903 — strong predictor of downstream provability.

## GGUF & Deployment

- **No official GGUFs yet** — safetensors only on HuggingFace
- **Conversion trivial**: `convert_hf_to_gguf.py --outtype q8_0` (vanilla Qwen3)
- **Q4_K_M**: ~4.5 GB, expected 25-40 t/s on EPYC 9655
- **Q8_0**: ~8.5 GB, expected 15-25 t/s
- **Concurrency**: Pipeline defaults to 512 concurrent LLM requests; local deployment needs 2-4 slots, extending wall-clock from 30 min to 2-6 hours per problem

## Infrastructure Requirements

- Lean 4 toolchain + Mathlib4
- QuickCheck + lean-tacs (bundled)
- Ray-based lean-ray-server for verification
- Any OpenAI-compat API endpoint

## Competitive Landscape

| System | Size | Code Verification | License | Local Feasible? |
|--------|------|-------------------|---------|----------------|
| **Goedel-Code-Prover** | 8B | **62.0%** (V/C/A) | MIT | **YES** (trivial) |
| Leanstral | 120B/6B MoE | 26.3-31.9 FLTEval | Apache 2.0 | YES (REAP candidate) |
| BFS-Prover-V2 | 32B | 23.8% (V/C/A) | — | Moderate |
| DeepSeek-Prover-V2 | 671B | 21.8% (V/C/A) | — | NO |

**Note**: Leanstral uses FLTEval (repo-scale proof engineering), not V/C/A (function-level verification). Not directly comparable.

## Limitations

1. Assumes programs and specs already formalized in Lean 4
2. Decomposition uses syntactic operator counting as difficulty proxy
3. Scaling to inter-procedural codebases untested
4. High compute cost at default concurrency (30 min / 512 workers)

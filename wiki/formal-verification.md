# Formal Verification

**Category**: `formal_verification`
**Confidence**: verified
**Last compiled**: 2026-04-15
**Sources**: 6 documents

## Summary

Formal verification research for the EPYC stack centers on deploying a two-tier Lean 4 proving pipeline using local models. Two complementary systems have been evaluated: Goedel-Code-Prover-8B (function-level code verification, 62.0% prove rate, MIT license) and Leanstral (119B MoE, repo-scale proof engineering, 26.3 pass@2 on FLTEval, Apache 2.0). These tools serve different purposes -- Goedel is a prover (takes goal, produces tactic proof via hierarchical search), while Leanstral is an agent (uses lean-lsp-mcp, reads repo context for architectural proof planning).

Goedel-Code-Prover-8B achieves 2.6x over the strongest baseline on function-level verification (Verina/Clever/AlgoVeri, 427 tasks) despite being a vanilla Qwen3-8B with no architectural modifications. All innovation is in the training pipeline: SFT on 432K teacher-generated trajectories (GPT-5.2/Gemini-3-Flash), followed by hybrid RL using GRPO with auxiliary SFT loss to prevent regression. The decomposition score formula aligns training reward with inference-time ranking. A key ablation shows decomposition alone is worth +28pp, and joint training shows synergy (68.7% vs 59.2% with only one component trained). The model outperforms systems 4-84x larger including GPT-5.3-Codex (18.5%) and DeepSeek-Prover-V2 at 671B.

Leanstral is a fine-tune of Mistral Small 4 using DeepSeek V3-style MoE + MLA architecture. With 119B total parameters but only 6.5B active per token, it is an ideal candidate for REAP expert pruning -- 95% of total parameters are routed expert weights. If expert activation patterns cluster on Lean 4 workloads (likely given domain specialization), REAP could prune to 32 experts (~20 GB Q4_K_M) while maintaining quality. At full size it runs ~36 t/s on EPYC 9655; REAP-pruned could hit 40+ t/s. The `deepseek2` architecture is fully supported in llama.cpp.

The proposed pipeline follows the OCR pattern: Leanstral plans (repo-scale context, proof strategy, subgoal decomposition), Goedel-CP executes at volume (tactic generation, leaf-goal proving, pass@k with compiler feedback). Combined memory footprint is ~25 GB with REAP-pruned Leanstral + Goedel-CP Q4_K_M, leaving massive headroom on EPYC 9655.

Verina (intake-234) provides a benchmarking framework for verifiable code generation but was assessed as not applicable for direct integration -- it is a benchmark, not a tool.

## Key Findings

- Goedel-Code-Prover-8B achieves 62.0% prove rate on 427 verification tasks, 2.6x over strongest baseline (BFS-Prover-V2, 32B) [goedel-code-prover-analysis.md]
- All Goedel-CP innovation is in training methodology -- vanilla Qwen3-8B base with standard GGUF conversion [goedel-code-prover-analysis.md]
- Decomposition alone worth +28pp; decomposition score AUROC 0.903 as predictor of downstream provability [goedel-code-prover-analysis.md]
- Leanstral's 95% of params are routed experts -- ideal REAP pruning candidate. REAP-32 + Q4_K_M would be ~20 GB [leanstral-architecture-analysis.md]
- Leanstral beats Claude Sonnet 4.6 on FLTEval (26.3 vs 23.7 pass@2) at 15x lower cost ($36 vs $549) [leanstral-architecture-analysis.md]
- Goedel-CP pipeline defaults to 512 concurrent LLM requests; local deployment needs only 2-4 slots, extending wall-clock from 30 min to 2-6 hours per problem [goedel-code-prover-analysis.md]
- Goedel-CP Q4_K_M: ~4.5 GB, expected 25-40 t/s on EPYC 9655. Q8_0: ~8.5 GB, 15-25 t/s [goedel-code-prover-analysis.md]
- Different evaluation benchmarks: Goedel uses Verina/Clever/AlgoVeri (function-level), Leanstral uses FLTEval (repo-scale). Not directly comparable [both deep-dives]
- Both models require Lean 4 toolchain + Mathlib4 infrastructure, plus lean-ray-server for verification [lean-proving-pipeline.md]

## Actionable for EPYC

- **S1 (P0): Convert Goedel-CP-8B to GGUF**: Download safetensors, convert with `convert_hf_to_gguf.py`, quantize to Q4_K_M and Q8_0. Validate with simple Lean proof generation test. Trivial -- vanilla Qwen3-8B.
- **S2 (P1): Profile Leanstral expert activation**: Download community GGUF (68 GB Q4_K_M), run with `--moe-expert-stats` on Lean 4 workloads. Determine if <=32 experts cover 95% of activations.
- **S3 (P1): REAP-prune Leanstral**: If profiling confirms clustering, prune to top-32 experts. Target: ~20 GB Q4_K_M at 40+ t/s.
- **S4 (P2): End-to-end pipeline test**: Run Goedel-CP against local llama-server (2-4 slots) on FormalQualBench subset (5 theorems). Measure prove rate and wall-clock.
- **S5 (P3): Two-tier integration**: Design routing between Leanstral (planning) and Goedel-CP (execution). Implement adapter between Leanstral MCP output and Goedel-CP input format.
- **Infrastructure**: Install Lean 4 toolchain, Mathlib4, lean-ray-server. These are prerequisites for any formal verification work.
- **Strip Leanstral's Pixtral vision encoder**: Dead weight for proof tasks (~1B params). Could be removed to save memory.

## Open Questions

- Does the formalizer-as-cost-reduction hypothesis (arxiv:2504.06514) generalize beyond math to code verification domains?
- Does Leanstral's planning output format align with Goedel-CP's input expectations, or is significant adapter work needed?
- Can lean-ray-server and lean-lsp-mcp coexist, or do they need separate Lean toolchain instances?
- What is the minimum viable concurrency for Goedel-CP's pipeline before wall-clock becomes impractical (target: <6 hours per problem)?
- Is FormalQualBench (23 math theorems) the right eval for code verification, or should Verina subset be used?
- How do REAP-pruned Leanstral quality metrics compare to full model on Lean 4 specifically?

## Formalizer as Cost-Reduction Tool

- **Formalizer reduces total pipeline cost, not just accuracy**: arxiv:2504.06514 ("Missing premise exacerbates overthinking in reasoning models") shows that missing or ambiguous premises cause solvers to explore multiple interpretations, generating excessive reasoning tokens. The MathSmith formalizer pre-fills missing structure via `[FORMAL SPECIFICATION]` blocks, causing the solver to converge with fewer tokens. The Conditional Information Bottleneck (Proposition 4.1) provides theoretical backing: formalization raises I(Z; Y | X), reducing optimal reasoning length. The HC variant's GRPO consistency reward further strengthens this effect. [mathsmith-hc-formalizer-eval.md](../handoffs/active/mathsmith-hc-formalizer-eval.md)
- **Math-Verify for benchmark answer validation**: intake-377 (HuggingFace Math-Verify) provides robust mathematical expression comparison with LaTeX parsing, symbolic simplification, and matrix equivalence. Current exact-match scoring underestimates model capability by ~66% on math expressions. Integration caveats: `verify(gold, pred)` is NOT symmetric, NOT thread-safe (`signal.alarm()`), and open intervals `(1,2)` convert to `Tuple(1,2)`. Applicable to MathSmith S4 A/B benchmark and Goedel-CP evaluation. [mathsmith-hc-formalizer-eval.md](../handoffs/active/mathsmith-hc-formalizer-eval.md)
- **Question quality filtering for eval**: intake-379 (MathQ-Verify) provides a 5-stage pipeline for validating question quality. Flawed questions with missing premises also waste compute by triggering solver overthinking. Stage 5 (completeness) hurts F1 by +0.57pp -- deploy stages 1-4 only. [mathsmith-hc-formalizer-eval.md](../handoffs/active/mathsmith-hc-formalizer-eval.md)

## Related Categories

- [MoE Optimization](moe-optimization.md) -- Leanstral is a prime REAP pruning candidate with 128 routed experts
- [Reinforcement Learning](reinforcement-learning.md) -- Goedel-CP uses hybrid GRPO + SFT training
- [Speculative Decoding](speculative-decoding.md) -- Both models benefit from standard speculation on dense architectures

## Source References

- [Goedel-Code-Prover analysis](/workspace/research/deep-dives/goedel-code-prover-analysis.md) -- Architecture, training pipeline, decomposition scoring, deployment estimates
- [Leanstral architecture analysis](/workspace/research/deep-dives/leanstral-architecture-analysis.md) -- MoE + MLA architecture, REAP pruning analysis, EPYC deployment estimates
- [Lean proving pipeline handoff](/workspace/handoffs/active/lean-proving-pipeline.md) -- Two-tier architecture design, work items S1-S5, infrastructure requirements
- [intake-233](https://arxiv.org/abs/2603.19329) Goedel-Code-Prover intake entry -- Initial evaluation and verdict
- [intake-235](https://mistral.ai/news/leanstral) Leanstral intake entry -- Initial evaluation and verdict
- [MathSmith HC formalizer eval handoff](/workspace/handoffs/active/mathsmith-hc-formalizer-eval.md) -- Formalizer-overthinking connection (arxiv:2504.06514), Math-Verify integration (intake-377), MathQ-Verify question quality (intake-379)

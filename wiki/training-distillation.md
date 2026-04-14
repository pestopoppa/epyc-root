# Training & Distillation

**Category**: `training_distillation`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 18 documents

## Summary

Training and distillation research for the EPYC stack focuses on three pillars: (1) improving worker model quality through contrastive training techniques like ACT, (2) compressing reasoning output through self-distillation methods like OPSDC, and (3) the SkillBank experience distillation system that converts raw episodic trajectories into structured, reusable behavioral principles.

The PostTrainBench study (intake-105/106) established that autonomous agent-driven post-training can beat official model instruction tuning on narrow tasks (BFCL +22pp on Gemma-3-4B) but achieves less than half the performance on general benchmarks. A critical finding is that medium reasoning effort outperforms high reasoning effort for strong models -- over-deliberation wastes budget on planning rather than experimentation. The 5-hour training plateau observed is specifically an SFT plateau; RL-based methods like ACT demonstrate gains beyond it.

ACT (Agentic Critical Training) introduces contrastive action discrimination where a model learns WHY certain actions are better, not just that they are. Trained via GRPO with no reasoning supervision, ACT produces +5pp gains over both imitation learning and RL baselines while preserving general reasoning (unlike IL which causes -6.91pp catastrophic forgetting on GPQA-Diamond). Cross-size transfer is validated: a 4B model trained on 8B trajectories matches or exceeds the 8B on out-of-distribution tasks.

The SkillBank system (Ch.15) operationalizes distillation in production. Three teacher models (Claude Opus 4.6, gpt-5.3-codex, Qwen3-235B local) distill raw trajectories into structured skills stored in SQLite + FAISS. Two-level retrieval injects skills into prompts at under 2ms latency with 5-15x token compression over raw trajectories. Recursive skill evolution promotes effective skills and deprecates failing ones. The system is gated behind the `ORCHESTRATOR_SKILLBANK=1` feature flag with 139 tests and graceful degradation.

SEAL control vectors for concise reasoning (seal-concise-reasoning experiment) showed mixed results: MoE models responded well (-7.5% tokens, no accuracy loss), dense models were neutral, and SSM-hybrid models (Qwen3.5-35B-A3B) suffered catastrophic failure (generation collapsed to 1 token). The experiment was parked in favor of AM KV compaction which delivers 5x compression at zero degradation.

## Key Findings

- Agents can beat official model instruction tuning on narrow tasks like function calling (+22pp on BFCL) but achieve only 23% vs 51% on general post-training benchmarks [agent-training-posttrainbench-act.md]
- Medium reasoning effort outperforms high for strong models: GPT-5.1 scored 19.7% (medium) vs 17.2% (high) while using half the tokens [agent-training-posttrainbench-act.md]
- ACT contrastive training preserves general reasoning (+1.85pp GPQA-Diamond) while imitation learning causes catastrophic forgetting (-6.91pp) [agent-training-posttrainbench-act.md]
- Cross-size ACT transfer works: 4B trained from 8B data achieves 91.79% OOD vs 8B's own 88.06% [agent-training-posttrainbench-act.md]
- SkillBank structured skills use 30-80 tokens each vs 200-500 for raw trajectories, yielding 5-15x compression [Ch.15 SkillBank]
- A 7B model with SkillRL skill augmentation (89.9% ALFWorld) outperforms GPT-4o (48.0%) and Gemini-2.5-Pro (60.3%), validating memory quality over model size [Ch.15 SkillBank]
- OPSDC self-distillation shows reasoning can be actively harmful: removing ~2,750 tokens predicts 28%+ relative accuracy improvement under independent error model [reasoning-compression.md]
- SEAL control vectors are incompatible with SSM-hybrid architectures (Gated Delta Net collapses generation to 1 token) [seal-concise-reasoning experiment]
- The SkillBank FailureBridge exports high-quality mitigations (success_rate >= 0.7, >= 3 attempts) from the Kuzu FailureGraph as failure_lesson skills [Ch.15 SkillBank]

## Actionable for EPYC

- **ACT training pipeline (5-day PoC)**: Collect 5K-10K expert trajectories from architect model on orchestrator tasks, sample alternative actions from worker, train worker via GRPO to discriminate. Expected +5pp on agentic tasks with reasoning preservation. Data collection: 1-2 days, training: 1 day, eval: 1 day.
- **SkillBank is deployable now**: Feature-flagged, 139 tests passing, all infrastructure wired. Enable `ORCHESTRATOR_SKILLBANK=1` and run distillation with available teacher models.
- **Conciseness prompting already deployed**: Added to worker_general, worker_math, coder_primary agent files (Action 1, reasoning-compression.md). Zero-cost, 37% token reduction on easy problems.
- **OPSDC difficulty signal**: KL divergence between concise-prompted and base output is itself a difficulty routing signal -- large divergence = easy problem, small = hard. Implementable at zero training cost.
- **Memento block-level reasoning compression**: 2-3x KV cache savings composing with existing Hadamard quantization. llama.cpp feasibility confirmed (2026-04-13). Blocked on training data (OpenMementos-228K available, MIT).
- **SEAL control vectors**: Viable only for MoE and dense models. Do NOT apply to SSM-hybrid architectures.

## Open Questions

- Can ACT's cross-size transfer scale from 2x ratio (4B from 8B) to 4.5x (7B from 32B)?
- Does SkillBank skill injection measurably improve routing outcomes in production A/B tests?
- What is the interaction between reasoning compression and speculative decoding acceptance rates?
- Can OPSDC's self-distillation be applied to Qwen models with LoRA (paper only tested full fine-tuning)?
- What is the quality cliff when stacking Memento block masking with Hadamard KV quantization and AM compaction?

## Related Categories

- [Reinforcement Learning](reinforcement-learning.md) -- ACT uses GRPO; OPSDC uses reverse KL; SkillBank references SkillRL
- [Cost-Aware Routing](cost-aware-routing.md) -- reasoning compression directly reduces routing costs
- [KV Cache](kv-cache.md) -- Memento block masking and SEAL interact with KV cache management
- [Context Management](context-management.md) -- SkillBank prompt injection and context-folding are complementary

## Source References

- [PostTrainBench + ACT deep dive](/workspace/research/deep-dives/agent-training-posttrainbench-act.md) -- Agent-driven post-training results, ACT contrastive training methodology, cross-size transfer validation
- [Ch.15 SkillBank & Experience Distillation](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/15-skillbank-experience-distillation.md) -- Production SkillBank architecture, distillation pipeline, recursive evolution, ~2,020 LOC implementation
- [SEAL Concise Reasoning experiment](/mnt/raid0/llm/epyc-inference-research/docs/experiments/seal-concise-reasoning.md) -- Control vector results across MoE/dense/SSM architectures
- [Reasoning Compression handoff](/workspace/handoffs/active/reasoning-compression.md) -- OPSDC analysis, TrimR evaluation framework, difficulty-adaptive routing signal
- [Memento handoff](/workspace/handoffs/active/memento-block-reasoning-compression.md) -- Block-level KV compression, dual information stream discovery, composability analysis
- [Ch.16 Calibration & Risk Control](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/16-calibration-and-risk-control.md) -- Skill effectiveness scoring integration with confidence calibration

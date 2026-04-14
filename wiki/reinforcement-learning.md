# Reinforcement Learning

**Category**: `reinforcement_learning`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 14 documents

## Summary

Reinforcement learning in the EPYC context spans two distinct domains: (1) RL as a training methodology for the LLMs that EPYC serves, and (2) RL-inspired mechanisms within the orchestrator itself (MemRL Q-value learning, routing model training). The project has evaluated multiple RL training systems and concluded that large-scale distributed RL training (AReaL, 128+ H800 GPUs) is fundamentally irrelevant to EPYC's routing needs, but RL training techniques like GRPO and DAPO are deeply relevant to model quality.

The orchestrator's own RL system, MemRL (Ch.07), uses Q-value scoring with a 7-dimensional reward signal (latency, quality gap, memory tier, regret, speedup, etc.) to learn routing decisions from experience. This is not policy-gradient RL -- it is supervised learning on accumulated Q-values via a 2-layer MLP classifier (~1K params) trained with NumPy on a single CPU in seconds. The routing classifier was distilled from the full HybridRouter retrieval pipeline following a 3-stage process inspired by ColBERT-Zero: unsupervised task embedding, supervised Q-weighted training, and HybridRouter decision compression.

The calibration and risk control system (Ch.16) adds conformal-style safety margins to RL-learned routing confidence. When confidence falls below calibrated thresholds, the system emits `risk_abstain_escalate` and hands off to a configured target role. Budget controls (worker call cap=30, token budget cap=200K) provide hard limits on runaway task execution. Skill effectiveness from SkillBank feeds back into confidence calibration -- high-effectiveness skills boost routing confidence for covered task types.

Among the RL training methods referenced across the research corpus, GRPO (Group Relative Policy Optimization) is the most prevalent. It appears in ACT's contrastive training (Stage 2 and 3), Goedel-Code-Prover's hybrid RL stage (100 steps with auxiliary SFT replay), OPSDC's self-distillation, and is supported by AReaL alongside DAPO, PPO, GSPO, and many others. Nemotron-Cascade 2 (intake-238) introduces cascade RL with multi-domain distillation specifically for small models -- relevant because the EPYC stack runs 2B-35B models where small-model RL training matters most.

AReaL (intake-111) was thoroughly evaluated and ruled out. It solves distributed GPU-scale RL training (128-512 H800 GPUs) for billion-parameter models. EPYC's routing models are ~1K parameter classifiers trained in seconds on CPU. The mismatch is approximately 6 orders of magnitude in compute. No extractable patterns were found beyond the conceptual similarity between AReaL's staleness-bounded off-policy learning and EPYC's existing Q-value decay.

## Key Findings

- EPYC's routing training is supervised classification on Q-values, NOT policy-gradient RL. The 2-layer MLP has ~1K params and trains in seconds on CPU [Ch.07 MemRL, areal-async-rl-system.md]
- AReaL is NOT RELEVANT: 6 orders of magnitude compute mismatch. 128+ H800 GPUs vs 1 CPU core. Nothing worth extracting [areal-async-rl-system.md]
- GRPO is the dominant RL training algorithm across evaluated papers: used by ACT, Goedel-Code-Prover, OPSDC, DeepSeek-R1 pipeline [multiple deep-dives]
- ACT uses GRPO with composite reward (R_acc=1.0 for expert selection, R_adm=0.1 for valid non-expert, R_fmt=-0.5 for malformed output) and no reasoning supervision [agent-training-posttrainbench-act.md]
- Goedel-Code-Prover uses hybrid RL: GRPO with auxiliary SFT loss (lambda=0.08) to prevent regression during proof search training [goedel-code-prover-analysis.md]
- Conformal risk gate operates on output-side uncertainty; two input-side classifiers (factual risk, difficulty signal) complement it with pre-routing assessment [Ch.16 Calibration]
- Budget controls inspired by Fast-RLM: worker_call_budget=30, task_token_budget=200K, checked before each `_execute_turn()` across all 7 graph node types [Ch.16 Calibration]
- Nemotron-Cascade 2 introduces cascade RL training specifically for small models with multi-domain distillation -- directly relevant to EPYC's 2B-35B model range [intake-238]
- Agent Lightning (intake-344) claims RL can be added to AI agents without code changes -- worth investigating for orchestrator integration [intake-344]
- RL Latent Thought Trajectories (intake-341) proposes reward-shaping for looped language models -- potentially relevant to reasoning compression [intake-341]

## Actionable for EPYC

- **MemRL routing is production-ready**: Q-value scoring, HybridRouter with calibrated confidence, routing classifier distillation -- all implemented and tested.
- **Calibration workflow**: Run replay on recent trajectories with baseline config, then with candidate settings. Compare ECE, Brier, conformal coverage metrics. Promote only if targets pass.
- **GRPO-based worker training**: If fine-tuning workers, use GRPO (not PPO). Supported by most training frameworks (TRL, verl). ACT's composite reward design is a good template.
- **Nemotron-Cascade 2 patterns**: Cascade RL training for small models could improve our 2B/4B/9B dense workers. Worth investigating when GPU access becomes available.
- **Agent Lightning evaluation**: If it delivers on "RL without code changes," could enhance orchestrator routing without retraining -- stub handoff recommended.
- **Do NOT pursue AReaL or large-scale distributed RL**: The compute requirements (128+ H800 GPUs) are 6 orders of magnitude beyond what routing model training needs.

## Open Questions

- Would online RL fine-tuning of specialist LLMs (using orchestrator feedback as reward) improve quality enough to justify GPU costs?
- Can Nemotron-Cascade 2's cascade RL methodology be applied to our Qwen-based workers without NVIDIA's full training infrastructure?
- Does Agent Lightning's "RL without code changes" actually work for routing optimization, or is it limited to simpler agent tasks?
- What is the optimal GRPO configuration (group size, KL penalty, learning rate) for Qwen3 model family fine-tuning?
- Could reward shaping from RLTT (intake-341) improve reasoning model performance on looped/iterative tasks?

## Related Categories

- [Training & Distillation](training-distillation.md) -- ACT and OPSDC use GRPO; SkillBank distillation is complementary to RL training
- [Routing Intelligence](routing-intelligence.md) -- MemRL Q-values and routing classifier are the RL-trained components of the routing stack
- [Cost-Aware Routing](cost-aware-routing.md) -- Q-scorer cost penalties and budget controls interact with RL-learned routing decisions
- [Speculative Decoding](speculative-decoding.md) -- RL reward design referenced in MTP acceptance rate optimization

## Source References

- [AReaL deep dive](/workspace/research/deep-dives/areal-async-rl-system.md) -- Comprehensive evaluation and rejection of distributed RL training system for EPYC
- [Ch.07 MemRL System](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/07-memrl-system.md) -- Episodic memory, Q-value scoring, two-phase retrieval, routing classifier
- [Ch.16 Calibration & Risk Control](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/16-calibration-and-risk-control.md) -- Conformal risk gate, budget controls, skill effectiveness scoring
- [PostTrainBench + ACT deep dive](/workspace/research/deep-dives/agent-training-posttrainbench-act.md) -- GRPO usage in ACT training pipeline
- [Goedel-Code-Prover analysis](/workspace/research/deep-dives/goedel-code-prover-analysis.md) -- Hybrid GRPO + SFT training for proof search
- [Reasoning Compression handoff](/workspace/handoffs/active/reasoning-compression.md) -- OPSDC self-distillation using reverse KL
- [ColBERT-Zero integration](/workspace/handoffs/completed/colbert-zero-research-integration.md) -- MemRL distillation design inspired by ColBERT-Zero 3-stage pipeline

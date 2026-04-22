# Training & Distillation

**Category**: `training_distillation`
**Confidence**: verified
**Last compiled**: 2026-04-22
**Sources**: 23 documents (added intake-441 diversity collapse)

## Summary

Training and distillation research for the EPYC stack focuses on three pillars: (1) improving worker model quality through contrastive training techniques like ACT, (2) compressing reasoning output through self-distillation methods like OPSDC, and (3) the SkillBank experience distillation system that converts raw episodic trajectories into structured, reusable behavioral principles.

The PostTrainBench study (intake-105/106) established that autonomous agent-driven post-training can beat official model instruction tuning on narrow tasks (BFCL +22pp on Gemma-3-4B) but achieves less than half the performance on general benchmarks. A critical finding is that medium reasoning effort outperforms high reasoning effort for strong models -- over-deliberation wastes budget on planning rather than experimentation. The 5-hour training plateau observed is specifically an SFT plateau; RL-based methods like ACT demonstrate gains beyond it.

ACT (Agentic Critical Training) introduces contrastive action discrimination where a model learns WHY certain actions are better, not just that they are. Trained via GRPO with no reasoning supervision, ACT produces +5pp gains over both imitation learning and RL baselines while preserving general reasoning (unlike IL which causes -6.91pp catastrophic forgetting on GPQA-Diamond). Cross-size transfer is validated: a 4B model trained on 8B trajectories matches or exceeds the 8B on out-of-distribution tasks.

The SkillBank system (Ch.15) operationalizes distillation in production. Three teacher models (Claude Opus 4.6, gpt-5.3-codex, Qwen3-235B local) distill raw trajectories into structured skills stored in SQLite + FAISS. Two-level retrieval injects skills into prompts at under 2ms latency with 5-15x token compression over raw trajectories. Recursive skill evolution promotes effective skills and deprecates failing ones. The system is gated behind the `ORCHESTRATOR_SKILLBANK=1` feature flag with 139 tests and graceful degradation.

SEAL control vectors for concise reasoning (seal-concise-reasoning experiment) showed mixed results: MoE models responded well (-7.5% tokens, no accuracy loss), dense models were neutral, and SSM-hybrid models (Qwen3.5-35B-A3B) suffered catastrophic failure (generation collapsed to 1 token). The experiment was parked in favor of AM KV compaction which delivers 5x compression at zero degradation.

A critical finding from SFT generalization research (intake-374, intake-378) is that **reasoning pattern structure determines SFT generalization quality more than quantity, loss, or data diversity**. DeepSeek-R1's divergent, branch-heavy traces produce 21pp worse generalization than gpt-oss-120b's convergent, deductive traces on Llama3.1-8B -- despite lower training loss. The "dilution effect" means low SFT loss is a misleading quality signal: R1's lower loss comes from trivially learned routine tokens, not better reasoning. Filtering branch-heavy trajectories by branching keyword proportion (Proxy 2) yields +3.6pp average improvement at zero cost. Independently, repeated exposure dominates coverage: 128 epochs on 400 samples beats 1 epoch on 51,200 by 12-26pp on AIME'24/25 (confirmed across two independent studies).

Aletheia RLVR (intake-370) provides scale-dependent training recipes for verification models: 1.5B models need on-policy GRPO with negative samples but can skip thinking traces; 14B models require thinking traces and negative samples for stability; DPO is catastrophic at 1.5B scale (-23.4%) but viable at 14B with Easy-to-Hard data. Training is GPU-only (16 rollouts/step), making the 1.5B scale the sweet spot for CPU inference verification with training deferred to DGX Spark.

## Key Findings

### New (2026-04-22, DD4)

- **Post-training diversity collapse is STRUCTURAL (in weights), not a generation-format issue** [intake-441, arxiv:2604.16027]. OLMo 3 three-lineage study: Think models lose most semantic diversity at SFT stage; Instruct models see larger effects from DPO. CoT suppression preserves answer-level diversity in Think models — collapse is in the weights, not the generation format. **Inference-time interventions (conciseness prompts, temperature adjustment, reasoning-length alarms) cannot recover training-time diversity loss.** Decomposition: diversity loss = quality-control component + residual/genuine-narrowing component. Task-dependent. **Implication for EPYC**: (1) model selection must include diversity metrics (distinct-2, self-BLEU, entropy, TTR) alongside accuracy for any checkpoint swap — see `eval-tower-verification.md` EV-8; (2) PromptForge mutation diversity is fundamentally bounded by base-model diversity, so a diversity-coverage term is needed (autopilot AP-35); (3) SFT-dominant narrowing on reasoning tracks, DPO on chat tracks — training-pipeline choices have measurable downstream impact. Deep dive: `/workspace/research/deep-dives/diversity-collapse-posttraining.md`.


- Agents can beat official model instruction tuning on narrow tasks like function calling (+22pp on BFCL) but achieve only 23% vs 51% on general post-training benchmarks [agent-training-posttrainbench-act.md]
- Medium reasoning effort outperforms high for strong models: GPT-5.1 scored 19.7% (medium) vs 17.2% (high) while using half the tokens [agent-training-posttrainbench-act.md]
- ACT contrastive training preserves general reasoning (+1.85pp GPQA-Diamond) while imitation learning causes catastrophic forgetting (-6.91pp) [agent-training-posttrainbench-act.md]
- Cross-size ACT transfer works: 4B trained from 8B data achieves 91.79% OOD vs 8B's own 88.06% [agent-training-posttrainbench-act.md]
- SkillBank structured skills use 30-80 tokens each vs 200-500 for raw trajectories, yielding 5-15x compression [Ch.15 SkillBank]
- A 7B model with SkillRL skill augmentation (89.9% ALFWorld) outperforms GPT-4o (48.0%) and Gemini-2.5-Pro (60.3%), validating memory quality over model size [Ch.15 SkillBank]
- OPSDC self-distillation shows reasoning can be actively harmful: removing ~2,750 tokens predicts 28%+ relative accuracy improvement under independent error model [reasoning-compression.md]
- SEAL control vectors are incompatible with SSM-hybrid architectures (Gated Delta Net collapses generation to 1 token) [seal-concise-reasoning experiment]
- The SkillBank FailureBridge exports high-quality mitigations (success_rate >= 0.7, >= 3 attempts) from the Kuzu FailureGraph as failure_lesson skills [Ch.15 SkillBank]
- **SFT generalization depends on reasoning pattern structure**: DeepSeek-R1 traces (33.3% Propose steps, 0.53 Propose-to-Propose transition) produce 21pp worse generalization than gpt-oss-120b traces (22.5% Propose, 0.34 transition) on Llama3.1-8B despite lower training loss [sft-generalization-reasoning-patterns.md]
- **Low SFT loss is a misleading quality signal**: R1's lower overall loss comes from trivially learned routine tokens ("dilution effect"), not better reasoning on hard transitions where loss is comparable [sft-generalization-reasoning-patterns.md]
- **Trajectory filtering by branching density is a zero-cost fix**: Removing branch-heavy trajectories from R1 data improves AIME24 by +3.2pp and BeyondAIME by +5.5pp on Qwen2.5-7B. Filtering by branching keywords has limited overlap with filtering by length [sft-generalization-reasoning-patterns.md]
- **Repeated exposure dominates coverage**: 2.5k samples x 8 epochs outperforms 20k x 1 under fixed 640-step budget; independently confirmed: 128 epochs on 400 samples beats 1 epoch on 51.2k by 12-26pp (arxiv:2602.11149) [sft-generalization-reasoning-patterns.md]
- **Safety degrades asymmetrically with reasoning SFT**: Reasoning improves while safety degrades with long-CoT SFT -- any future fine-tuning must include safety benchmarks [sft-generalization-reasoning-patterns.md]
- **Aletheia RLVR training is scale-dependent**: 1.5B needs on-policy GRPO + negative samples, skip thinking traces. 14B needs thinking traces + negative samples for stability. DPO is catastrophic at 1.5B (-23.4%) but viable at 14B [eval-tower-verification.md]
- **TTS accuracy does not predict RL training effectiveness**: SWE-RM (intake-368) showed two verifiers with identical accuracy produce completely different RL outcomes (AUC 0.805 smooth vs AUC 0.710 collapse). ECE + AUC are critical missing eval metrics [eval-tower-verification.md]
- **Simula provides a principled mechanism-design framework for synthetic data generation and evaluation.** Simula (arxiv:2603.29791, intake-410, TMLR 2026 with J2C certification) decomposes data generation into four independently controllable axes: coverage (taxonomy-based global diversification), local variation (meta-prompting), complexity (configurable complexification fraction), and quality (double-critic rejection sampling). Key finding: there is no single optimal way to generate synthetic data -- the relationship between data properties and downstream performance is deeply idiosyncratic. High complexity yields +10% accuracy on GSM8k (strong teacher, 88%) but hurts on LEXam (weak teacher, 57%). The full system (all axes) almost always dominates simpler baselines despite costing 5x more inference per data point -- training costs dominate generation costs. Quality > Quantity: better data scales better. [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)
- **Simula's taxonomy generation nearly doubles coverage over zero-shot approaches** (Level Ratio Coverage 1.72 vs 0.83) while maintaining soundness (0.97). The generator-critic refinement loop discovers edge cases humans missed (novelty score 0.94). Global diversification (deep taxonomy sampling) drives dataset-wide embedding diversity; local diversification (meta-prompting) drives within-cluster variation. The two are additive. [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)
- **Student-teacher saturation bounds distillation utility.** Simula shows CTI-RCM saturates at ~65% student accuracy vs 70% teacher (bridging 83% of the gap at 128k samples). Beyond this point, more data yields diminishing returns regardless of quality. When teacher accuracy is low (LEXam 57%), the double-critic correctly rejects 61% of generated data -- the pipeline becomes extremely inefficient but produces correct behavior (not generating wrong training data). [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)

## Actionable for EPYC

- **ACT training pipeline (5-day PoC)**: Collect 5K-10K expert trajectories from architect model on orchestrator tasks, sample alternative actions from worker, train worker via GRPO to discriminate. Expected +5pp on agentic tasks with reasoning preservation. Data collection: 1-2 days, training: 1 day, eval: 1 day.
- **SkillBank is deployable now**: Feature-flagged, 139 tests passing, all infrastructure wired. Enable `ORCHESTRATOR_SKILLBANK=1` and run distillation with available teacher models.
- **Conciseness prompting already deployed**: Added to worker_general, worker_math, coder_primary agent files (Action 1, reasoning-compression.md). Zero-cost, 37% token reduction on easy problems.
- **OPSDC difficulty signal**: KL divergence between concise-prompted and base output is itself a difficulty routing signal -- large divergence = easy problem, small = hard. Implementable at zero training cost.
- **Memento block-level reasoning compression**: 2-3x KV cache savings composing with existing Hadamard quantization. llama.cpp feasibility confirmed (2026-04-13). Blocked on training data (OpenMementos-228K available, MIT).
- **SEAL control vectors**: Viable only for MoE and dense models. Do NOT apply to SSM-hybrid architectures.
- **Trajectory filtering for any future training data**: If using OpenR1-Math-220k or DeepSeek-R1 distilled data, MUST filter by branching density (Proxy 2: branching keyword proportion) before training. Unfiltered R1 traces produce 21pp worse generalization on Llama3.1-8B. Zero training cost -- preprocessing only.
- **Depth over breadth for SFT**: When training reasoning adapters, use repeated exposure (128 epochs on curated subset) rather than large single-pass datasets. Token accuracy serves as the saturation indicator. Safety evaluation mandatory alongside capability evaluation.
- **Aletheia 1.5B for CPU verification inference**: Pre-trained ThinkPRM-1.5B or Aletheia-1.5B models can be downloaded and quantized today for T2 eval tower process verification. Training recipe (on-policy GRPO, binary rewards, 2:1 pos/neg ratio, temperature 1.0, no thinking traces at 1.5B) deferred to DGX Spark.
- **Simula's taxonomy-based coverage analysis for eval set construction**: Generate deep taxonomies for eval domains (coding, math, reasoning, tool use), map existing eval questions to taxonomy nodes, compute Level Ratio Coverage to identify under-represented sub-domains, and generate targeted questions for gaps. Zero training cost -- uses local LLM for taxonomy generation and coverage scoring. Applicable to benchmark construction and specialist routing seeder.
- **Simula's complexity-aware insights for routing**: A model's optimal complexity band is bounded by its competence (teacher ceiling). For routing: high-complexity queries should route to strongest model, low-complexity to cheapest. Elo complexity scores could serve as routing classifier features.

## Open Questions

- Can ACT's cross-size transfer scale from 2x ratio (4B from 8B) to 4.5x (7B from 32B)?
- Does SkillBank skill injection measurably improve routing outcomes in production A/B tests?
- What is the interaction between reasoning compression and speculative decoding acceptance rates?
- Can OPSDC's self-distillation be applied to Qwen models with LoRA (paper only tested full fine-tuning)?
- What is the quality cliff when stacking Memento block masking with Hadamard KV quantization and AM compaction?
- Does the 21pp architecture-dependent gap (Llama3.1-8B vs Qwen2.5-7B at 5.1pp) generalize beyond math to code and agentic tasks?
- Can branching density (Propose step %) serve as a runtime quality signal for routing decisions, not just training data filtering?
- At what model scale does DPO become viable for RLVR verification training (Aletheia shows -23.4% at 1.5B, viable at 14B)?
- Is TPO (intake-404) a viable GRPO replacement for Tier 3 training? TPO claims 7x fewer steps on sparse rewards (7.4% vs 50.4% at H=10) and stable multi-epoch training. Only tested at 1.5-1.7B; awaiting 7B+ replication.

## Related Categories

- [Reinforcement Learning](reinforcement-learning.md) -- ACT uses GRPO; OPSDC uses reverse KL; SkillBank references SkillRL; TPO (intake-404) replaces GRPO via cross-entropy target fitting
- [Cost-Aware Routing](cost-aware-routing.md) -- reasoning compression directly reduces routing costs
- [KV Cache](kv-cache.md) -- Memento block masking and SEAL interact with KV cache management
- [Context Management](context-management.md) -- SkillBank prompt injection and context-folding are complementary

## Source References

- [PostTrainBench + ACT deep dive](/workspace/research/deep-dives/agent-training-posttrainbench-act.md) -- Agent-driven post-training results, ACT contrastive training methodology, cross-size transfer validation
- [Ch.15 SkillBank & Experience Distillation](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/15-skillbank-experience-distillation.md) -- Production SkillBank architecture, distillation pipeline, recursive evolution, ~2,020 LOC implementation
- [SEAL Concise Reasoning experiment](/mnt/raid0/llm/epyc-inference-research/docs/experiments/seal-concise-reasoning.md) -- Control vector results across MoE/dense/SSM architectures
- [Reasoning Compression handoff](/workspace/handoffs/active/reasoning-compression.md) -- OPSDC analysis, TrimR evaluation framework, difficulty-adaptive routing signal
- [Memento handoff](/workspace/handoffs/active/memento-block-reasoning-compression.md) -- Block-level KV compression, dual information stream discovery, composability analysis
- [SFT Generalization & Reasoning Patterns deep dive](/workspace/research/deep-dives/sft-generalization-reasoning-patterns.md) -- Branching density taxonomy, dilution effect, trajectory filtering, repeated exposure findings (intake-373/374/378)
- [Eval Tower Verification handoff](/workspace/handoffs/active/eval-tower-verification.md) -- Aletheia scale-dependent RLVR recipes, SWE-RM TTS vs RL effectiveness, ECE/AUC metrics, ThinkPRM deployment plan
- [Simula Synthetic Data Generation deep dive](/workspace/research/deep-dives/simula-synthetic-data-generation.md) -- intake-410, TMLR 2026, reasoning-driven seedless framework, double-critic rejection sampling, calibrated Elo complexity scoring, taxonomy-based coverage (1.72 vs 0.83), mechanism design principles (no silver bullet, quality>quantity, complexity requires calibration), student-teacher saturation bounds
- [Ch.16 Calibration & Risk Control](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/16-calibration-and-risk-control.md) -- Skill effectiveness scoring integration with confidence calibration

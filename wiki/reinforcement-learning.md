# Reinforcement Learning

**Category**: `reinforcement_learning`
**Confidence**: verified
**Last compiled**: 2026-04-15
**Sources**: 16 documents

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
- Nemotron-Cascade 2 introduces cascade RL training specifically for small models with multi-domain distillation -- directly relevant to EPYC's 2B-35B model range [intake-238](https://arxiv.org/abs/2603.19220)
- Agent Lightning (intake-344) claims RL can be added to AI agents without code changes -- worth investigating for orchestrator integration [intake-344](https://arxiv.org/abs/2508.03680)
- RL Latent Thought Trajectories (intake-341) proposes reward-shaping for looped language models -- potentially relevant to reasoning compression [intake-341](https://pli.princeton.edu/events/2026/prioritize-process-not-just-outcome-rewarding-latent-thought-trajectories-improves)

## Verification Framework Research

### Eval Tower Calibration (ECE/AUC)

SWE-RM (intake-368) demonstrated that accuracy alone is insufficient for RLVR reward design: two verifiers with nearly identical test-time-scaling performance (+4.7% vs +4.5%) produced completely different RL training outcomes because one had AUC 0.805 (smooth training) and the other AUC 0.710 (training collapse). The eval tower must track **ECE** (Expected Calibration Error) and **AUC** (Area Under ROC Curve) alongside accuracy before it can serve as an RLVR environment.

EV-1 and EV-2 (both complete, 2026-04-15) add a `confidence` field to `QuestionResult` and ECE/AUC/calibration_violations computation to `EvalResult` in the eval tower. With binary confidence proxy, ECE is trivially 0 -- it becomes meaningful once logprob passthrough from llama-server provides continuous confidence values. EV-6 (complete) adds a cross-family verification constraint to `eval_tower.py` supporting Qwen, Llama, DeepSeek, Ouro, Mistral, and Gemma families.

> Source: [eval-tower-verification.md](/workspace/handoffs/active/eval-tower-verification.md) EV-1, EV-2, EV-6

### ThinkPRM Process Verification

ThinkPRM (intake-371) is a generative process reward model that verifies solution steps via verification chain-of-thought. It achieves PRM800K parity with only 1% of labels and +8% out-of-distribution on GPQA-Diamond versus discriminative PRMs. Scoring uses `P("yes") / (P("yes") + P("no"))` from logprobs.

EV-5 (planned) will deploy ThinkPRM-1.5B (Q4_K_M, ~2GB RAM) for T2 process verification on the most uncertain questions identified by T1 calibration data. This provides PromptForge with actionable feedback: not just "wrong answer" but "step 3 introduced the error." Cross-family verification is mandatory -- the verifier model must be a different family than the generator.

> Source: [eval-tower-verification.md](/workspace/handoffs/active/eval-tower-verification.md) EV-5; intake-371

### Aletheia Scale-Dependent RLVR Training Recipes

Aletheia (intake-370) provides systematic ablation of RLVR training recipes across model scales:

- **1.5B**: On-policy GRPO is essential. Thinking traces are skippable. Negative samples are required (+10-20% without). DPO is not viable (-23.4%).
- **7B**: On-policy GRPO preferred. Thinking traces helpful. Negative samples required. DPO viable with good data.
- **14B**: On-policy GRPO preferred. Thinking traces mandatory. Negative samples critical for stability. DPO viable (Easy-to-Hard).

For the EPYC CPU-only environment, the 1.5B scale is the sweet spot for verification model inference. Training requires GPU (GRPO needs 16 rollouts/step) and is deferred to DGX Spark. Pre-trained ThinkPRM-1.5B or Aletheia-1.5B models can be downloaded and quantized today. The training roadmap calls for binary outcome rewards, 16 rollouts/step, temperature 1.0, constant LR 1e-6, 2:1 positive-to-negative ratio (SWE-RM finding), no thinking traces at 1.5B (Aletheia finding), on-policy GRPO (not DPO, not RAFT).

> Source: [eval-tower-verification.md](/workspace/handoffs/active/eval-tower-verification.md) Aletheia Training Recipes; intake-370

### Cross-Family Verification Requirement

Repeated same-family verification amplifies bias: adversarial success increases from 52% (first attempt) to 87% after 4 iterative review rounds. Cross-family verification is the strongest defense -- Gemini verifying GPT gives +4.6pp benefit versus +1.7pp for same-family. The design rule for the EPYC eval tower is: if evaluating Qwen-family generator output, the verifier must be non-Qwen (e.g., Llama, DeepSeek, or Ouro-2.6B). EV-6 implements `check_cross_family()` as a runtime guard for ThinkPRM deployment and AP-27 RLVR integration.

> Source: [eval-tower-verification.md](/workspace/handoffs/active/eval-tower-verification.md) EV-6, Confirmation Bias Mitigation

### Scoring Verifiers Protocol

The Scoring Verifiers benchmark (intake-367, COLM 2025) establishes a 4-metric evaluation standard: Top-1 Accuracy (best solution identification), Bottom-1 Accuracy (worst solution rejection), Spearman rho (full ordering quality), and MAE (calibration accuracy). Key findings: reasoning models dominate by 5-9pp for verification (o3-mini 88.2% vs Qwen2.5-Coder-32B 79.1%), distilled reasoning gives almost no benefit (78.2%), and showing the candidate solution to the test generator causes 10-15pp self-evaluation bias. EV-3 (planned) will download the Scoring Verifiers benchmarks (HE-R+, MBPP-R+) and integrate them as eval tower suites.

> Source: [eval-tower-verification.md](/workspace/handoffs/active/eval-tower-verification.md) Scoring Verifiers Benchmark Protocol; intake-367

### AP-27 RLVR Integration

AP-27 in the autopilot continuous optimization handoff formalizes the eval tower tiers (T0/T1/T2) as RLVR verification functions with deterministic reward signals per tier. The implementation plan is now fully specified in the eval-tower-verification handoff (EV-1 through EV-7). EV-7 depends on all preceding phases plus Ouro P7 results, and will export eval environments for actual RL model training when DGX Spark becomes available. The three metrics (quality + ECE + AUC) form the minimal signal for RLVR reward design.

> Source: [autopilot-continuous-optimization.md](/workspace/handoffs/active/autopilot-continuous-optimization.md) AP-27; [eval-tower-verification.md](/workspace/handoffs/active/eval-tower-verification.md) EV-7

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
- [Eval Tower Verification](/workspace/handoffs/active/eval-tower-verification.md) -- ECE/AUC calibration metrics, ThinkPRM process verification, Aletheia scale-dependent RLVR recipes, Scoring Verifiers protocol, cross-family verification constraint
- [Autopilot Continuous Optimization](/workspace/handoffs/active/autopilot-continuous-optimization.md) -- AP-27 RLVR formalization pointing to eval-tower-verification.md EV-1--EV-7

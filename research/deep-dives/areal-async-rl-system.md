# Research Intake-111: AReaL -- Large-Scale Async Reinforcement Learning System

**Source**: https://github.com/inclusionAI/AReaL
**Paper**: https://arxiv.org/abs/2505.24298 (NeurIPS 2025)
**Authors**: Tsinghua IIIS + Ant Group AReaL Team
**Date evaluated**: 2026-03-15

---

## Summary

AReaL is a large-scale asynchronous reinforcement learning training system designed specifically for training large language models (1.5B-235B parameters) on reasoning and agentic tasks. It decouples rollout generation from gradient updates, achieving 2.77x training speedup over synchronous RL baselines while matching or exceeding final performance. The system uses a staleness-enhanced PPO variant to handle off-policy data from stale model versions.

**Bottom line**: AReaL solves a fundamentally different problem than what EPYC routing training needs. It is a distributed LLM-scale RL training system. Our routing models are tiny classifiers (MLP + GAT) trained with standard supervised learning from accumulated Q-values. AReaL is not relevant to our use case.

---

## Architecture

The system has three core components:

1. **Rollout workers** (75% of GPUs): Run LLM inference (vLLM or SGLang) continuously, generating completions without waiting for training to finish.
2. **Training workers** (25% of GPUs): Consume batches of rollouts asynchronously, updating model weights. Backends: Megatron (full parallelism), PyTorch FSDP (LoRA support), Archon.
3. **Staleness-enhanced PPO**: Separates behavior policy (data collection) from proximal policy (regularization). Tolerates data from up to eta=4 prior model versions via importance sampling correction.

Scheduling is Ray-based across multi-node GPU clusters.

**Supported algorithms**: GRPO, GSPO, PPO, DAPO, LitePPO, Dr.GRPO, REINFORCE++, RLOO, SAPO, M2PO, reward modeling, SFT, distillation. All support async mode via `max_head_offpolicyness` toggle.

**Supported models**: Qwen2/3, Qwen3-MoE, Qwen2.5-VL, Qwen3-VL, Gemma 3, any HuggingFace LLM via FSDP.

---

## Scale & Requirements

| Config | Nodes | GPUs | Model Size |
|--------|-------|------|------------|
| Minimum pod | 16 nodes | 128 H800 GPUs | 1.5B-7B |
| Mid-scale | 32 nodes | 256 H800 GPUs | 14B |
| Full-scale | 48-64 nodes | 384-512 H800 GPUs | 32B-235B |

- Intra-node: NVLink. Inter-node: RoCE, 3.2 Tbps.
- Single-node demo mode exists but is not the designed use case.
- Dependencies: Python, PyTorch, Ray, vLLM/SGLang, Megatron-LM, CUDA, optionally SkyPilot.

---

## Relevance to Routing Training

### What we actually do

Our routing training pipeline (in `epyc-orchestrator/scripts/graph_router/`) is:
- `extract_training_data.py` produces `training_data.npz` from episodic Q-values
- `train_routing_classifier.py` trains a **2-layer MLP** with Q-weighted cross-entropy, 200 epochs, batch_size=64, pure NumPy, single CPU
- `train_graph_router.py` trains a **lightweight GAT** with BCE loss + SGD on a bipartite graph of ~6 model nodes, pure NumPy

| Dimension | AReaL Target | EPYC Routing |
|-----------|-------------|--------------|
| Model size | 1.5B - 235B params | ~1K params |
| Training algo | PPO, GRPO, REINFORCE | Supervised (CE, BCE) |
| Compute | 128-512 H800 GPUs | 1 CPU core |
| Training time | Hours to days | Seconds |
| Framework | PyTorch + Megatron + Ray | NumPy |
| Data source | Online rollouts from LLM | Offline Q-value records |

**Assessment: NOT RELEVANT.** The mismatch is total -- approximately 6 orders of magnitude in compute, and the algorithmic domain (distributed policy gradient RL vs. single-machine supervised classification) is fundamentally different.

---

## Relevance to AutoPilot

The autopilot (`epyc-orchestrator/scripts/autopilot/`) runs 4 optimizer species in a continuous loop with a tiered eval tower and 4D Pareto archive. Its bottleneck is inference time (running questions through specialist models at 6-50 t/s), not training throughput. The training step (Species 3, StructuralLab) is seconds of NumPy. The autopilot already runs seeding asynchronously.

**Assessment: NOT RELEVANT.** There is no synchronization bottleneck to solve. AReaL's async pattern addresses GPU idle time during multi-billion-parameter RL training -- a problem that does not exist in our meta-optimization loop.

---

## Extractable Patterns

Despite the system being irrelevant as a whole, a few ideas were evaluated:

1. **Staleness-bounded off-policy learning** (`max_head_offpolicyness`): Conceptually similar to our Q-value decay in `q_scorer.py`. Already implemented. No action needed.
2. **Importance sampling for off-policy correction**: Only relevant if we move to online routing model updates (not planned). File for future reference.
3. **Worker budget allocation** (75/25 split): Our `meta_optimizer.py` already does species budget rebalancing with stagnation detection.
4. **Decoupled actor-critic**: Not applicable -- our routing is a classifier, not actor-critic.

**Nothing worth extracting.**

---

## Verdict

**NOT RELEVANT to EPYC routing training or autopilot.**

AReaL requires 128+ H800 GPUs to provide meaningful value. Our routing model training is a supervised learning problem on kilobyte-scale models that runs on CPU in seconds.

**Recommendation**: Do not integrate, adopt, or port any AReaL components. Close this research intake with verdict: not applicable.

**When AReaL would become relevant**: Only if we decided to fine-tune the specialist LLMs themselves using RL from automated feedback, with access to a multi-node H800 cluster, and wanted to do this training online. None of these are on the current or planned roadmap.

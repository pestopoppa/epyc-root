# Standalone Items Deep-Dive — 2026-05-19

## Executive Summary

Three intakes user-selected for deep-dive that don't cluster with the May 2026 thematic
batches: DreamServer (intake-540, local-AI stack distribution), SkillSynth (intake-543,
Terminal-Bench task synthesis), Training-Free GRPO (intake-546, in-context RL via
experience library). None are core fits for EPYC, but per `feedback_dont_dismiss_creative_uses`
each is examined for actionable patterns. **Verdict spread:** DreamServer → monitor-only,
one pattern (manifest extension format) worth lifting; SkillSynth → monitor for dataset
release, methodology not adoptable; Training-Free GRPO → **worth a small spike** for
hermes-agent persistent experience library.

---

## DreamServer (intake-540)

**Source:** https://github.com/Light-Heart-Labs/DreamServer

### Repo health

- **Stars / forks / watchers:** 1,519 / 228 / 1,519 (notable for 3-month-old org repo)
- **Created:** 2026-02-09 · **Last push:** 2026-05-19 (active daily)
- **License:** Apache-2.0 (clean)
- **Language:** Shell-dominant (Docker Compose + installer scripts)
- **Topics:** local-ai, llama-cpp, strix-halo, open-webui, comfyui, n8n, rag, ai-agents
- **Issues open:** 21 · **Discussions:** enabled · suggests maintained community

### Component inventory vs EPYC

| Component | DreamServer | EPYC has | New to EPYC? |
|---|---|---|---|
| llama-server | ✓ bundled | ✓ custom fork + ik_llama.cpp PR #1744 | No |
| LiteLLM gateway | ✓ | ✗ (orchestrator_stack.py routes natively) | Yes |
| TEI embeddings | ✓ | ✗ | Yes (have qdrant via Hermes) |
| Open WebUI | ✓ | ✗ (Hermes is the frontend) | Yes |
| Hermes Agent | ✓ optional | ✓ (`/mnt/raid0/llm/hermes-agent`) | No |
| OpenClaw | ✓ optional | ✗ | Yes |
| n8n | ✓ | ✗ | Yes |
| ComfyUI | ✓ | ✓ (managed service, per `feedback_stack_managed_services`) | No |
| Whisper / Kokoro | ✓ | partial (Whisper noted in stack memos) | Mostly no |
| SearXNG | ✓ | ✓ (`scripts/search/searx.sh`, `localhost:8090`) | No |
| Perplexica | ✓ | ✗ | Yes |
| Qdrant | ✓ | ✓ (Hermes RAG) | No |
| APE (policy engine) | ✓ | partial (agent_log + governance hooks) | Conceptually similar |
| Memory Shepherd | ✓ | partial (MEMORY.md + handoffs) | Conceptually similar |

Overlap is **substantial** — EPYC independently converged on most of the same services.
DreamServer's value is **packaging**, not novel components.

### Manifest extension format — the one pattern worth lifting

DreamServer's extension format:

```
extensions/services/my-service/
  manifest.yaml      # name, port, health endpoint, GPU backends
  compose.yaml       # Docker Compose fragment (auto-merged)
```

Services are "hot-pluggable" via `dream enable my-service` / `dream disable my-service`.

**EPYC parallel:** `feedback_stack_managed_services_managed_services` already mandates
that production services be **first-class members of `orchestrator_stack.py`**, not
sidecars. DreamServer's manifest format is the data-driven version of this principle:
instead of hand-editing `orchestrator_stack.py` to add a service, drop a folder with two
files and re-launch.

**Potential lift:** A `services/<name>/manifest.yaml` schema for orchestrator_stack.py
add-ons (health endpoint, port, env-var contract, NUMA pinning hints). Would let us:
- Add Whisper/Kokoro/Perplexica as opt-in services without touching core launch code
- Standardize the health-check contract (currently each service has bespoke probes)
- Make `scripts/session/health_check.sh` data-driven

**Not lift:** Docker Compose orchestration. EPYC runs llama-server processes directly
under numactl/taskset; containerizing would block NUMA pinning and the OMP env stack
(`feedback_omp_env_stack_required`).

### Hardware-tier autodetect

Four GPU families (NVIDIA tiers 0–4 + NV_ULTRA, AMD Strix Halo SH_COMPACT/SH_LARGE,
Apple Silicon tiers 0–4, Intel Arc ARC_LITE/ARC). Selects quants and context windows
by detected VRAM. **Not applicable** — EPYC is single-host CPU-only with manually-tuned
NPS4 + thread counts (`project_cpu1_48t_new_best`). No autodetect would beat manual
sweep results.

### Verdict

**Monitor-only with one actionable pattern.** Lift the manifest-based service-add format
into orchestrator add-on system as a Q3 cleanup task. No urgency — current
`orchestrator_stack.py` works. File for inclusion when next refactor lands.

---

## SkillSynth (intake-543)

**Source:** arxiv:2604.25727 (Tencent Hunyuan)

### Skill graph stats

- **82,073 scenario nodes** · **57,214 filtered skills** · **185,529 LLM-verified bridges**
- 85.6% connectivity in largest component; median degree 2, max 752 (heavy-tailed)
- Construction: skills filtered from ClawHub + GitHub, LLM infers pre/post-condition
  scenarios, HAC + Louvain clustering, embedding-similarity + bidirectional LLM
  verification for cross-skill alignment

### Inverse-frequency weighted random walks (Algorithm 1)

- Maintain visit counts ν(σ) per scenario, usage counts μ(κ) per skill
- Sample source: p(σ) ∝ (ν(σ)+1)⁻¹ ; at each step: p(κ) ∝ (μ(κ)+1)⁻¹
- Monotone progression (no revisits), path length ∈ [1, 7]
- Produces 3,721 paths biased against hub nodes → enforces tail coverage

### Synthesis pipeline & cost

Two-stage (plan → construct), dual verification (execution oracle + LLM rubric judge),
up to 3 repair cycles. **3,560 verified from 3,721 paths (95.7%)** · 92.0% pass both
checks · **$27.3 per verified task** average.

### Results

| Model | TB 1.0 | TB 2.0 |
|---|---|---|
| Qwen3-32B + SkillSynth SFT | **33.8 ± 3.1** | **29.6 ± 1.6** |
| Qwen3-32B + multi-skill baseline | 30.8 ± 1.8 | 25.8 ± 2.8 |
| Qwen3-32B + single-skill baseline | 25.4 ± 1.8 | 21.3 ± 2.8 |
| Claude Code reference (external) | — | 86.4 |

Methodology is sound (+8.3pp over single-skill baseline) but absolute scores remain
far below frontier agents. 38% of synthesized tasks remain unsolved after 3 attempts.

### Creative use for EPYC autopilot

The user's pitch: could the inverse-frequency weighted sampling inform autopilot's
**question generation / exploration coverage metric**?

**Direct adoption: no.** Autopilot's Pareto archive (per `feedback_checkpoint_pareto_state`)
optimizes config space (threads × NUMA × ub-size), not natural-language task space.
There is no skill graph for "llama-server configs."

**Indirect: maybe.** The diversity-controlled walk principle — *inverse frequency over
already-explored regions* — is a generic exploration metric. Autopilot currently uses
random + Bayesian search; an inverse-density bias over its config-space embedding
could improve coverage. But this is a 1-line change to existing samplers, not a
SkillSynth adoption.

**Skill-graph as coverage metric for hermes-agent eval:** *If* Tencent releases the
graph (not currently disclosed), it would be a useful diverse-task corpus for
benchmarking hermes-agent against Terminal-Bench-style workloads. **Action: watch
arxiv + Tencent GitHub for dataset release; no work until released.**

### Verdict

**Monitor for dataset release.** Do not adopt the SFT pipeline ($27/task × thousands
is far past the "no concurrent inference" + single-host throughput budget). Diversity
sampling principle is folklore-grade — already known, no novel mechanism worth lifting.

---

## Training-Free GRPO (intake-546)

**Source:** arxiv:2510.08191 (Tencent Youtu + Fudan)

### Mechanism

Replace numerical GRPO advantages with **natural-language extraction over grouped
rollouts**:

1. For each query, sample G rollouts
2. LLM summarizes each trajectory via `psummary` prompt
3. Given summaries + current experience library ℰ, LLM articulates "reasons for relative
   success/failure" via `pextract` → semantic advantage `Atext`
4. Trigger gate: only when **std(reward) ≠ 0** (mixed wins/losses in group)

### Experience library CRUD

Four operations applied to `Atext`:

| Op | Trigger |
|---|---|
| **Add** | New insight |
| **Delete** | Low-quality experience identified |
| **Modify** | Refine existing entry |
| **Keep** | No change |

Each entry is a short numbered statement (~32 words max per Figure 13). Injection at
inference is **prompt-prefix concatenation** — no RAG, no embedding lookup. Figure 10
template: *"...you MUST first carefully read and understand the helpful instructions
and experiences: {experiences}"*.

### Reported numbers (DeepSeek-V3.1-Terminus, 671B)

- **AIME24:** 82.7% (↑ 2.7pp vs 80.0% baseline)
- **AIME25:** 73.3% (↑ 5.4pp vs 67.9% baseline)
- **WebWalkerQA Pass@1:** 67.8% (↑ 4.6pp vs 63.2% baseline)
- Training: 100 samples × 3 epochs × G=3 rollouts

### Cost

| Method | Cost | Model |
|---|---|---|
| Training-Free GRPO | **~$18** | DeepSeek-V3.1 (671B, API) |
| ReTool SFT baseline | ~$10,000 | Qwen2.5-32B-Instruct |

38M input + 6.6M output tokens over 33 steps (6 hours wall).

### Creative use for EPYC

This is the most actionable of the three. Direct mapping to EPYC stack:

**Hermes-agent persistent experience library.** Per `handoffs/active/hermes-agent-index.md`,
Hermes is the agent frontend with memory + skills. Today its "memory" is conversation
history + Qdrant RAG. A **Training-Free GRPO-style experience library** would add:
- A curated, model-edited list of short procedural rules learned across sessions
- Prefix-injected into every prompt (cheap; no retrieval latency)
- CRUD-updated periodically by a meta-pass over recent traces

**Meta-harness optimization angle.** Per `handoffs/active/meta-harness-optimization.md`,
we're already tuning harness behavior. Training-Free GRPO is *exactly* a meta-harness
that learns inference-time prompt augmentations from rollout traces. The harness
already collects per-question traces; adding the summarize/extract step is incremental.

**Cost translation.** The $18 figure is API cost. On EPYC: 100 samples × 3 epochs × G=3
= 900 rollouts. At 30B-A3B Q4_K_M = 76.5 t/s solo with gemma4 MTP
(`project_worker_general_swap_2026_05_08`), and assuming ~2K output tokens per rollout,
that's ~6h wall on the worker_general pool — same order as the paper's API run, but
free.

**Spike scope (proposed):**
1. Pick one benchmark from existing eval suite (e.g., a small AIME-like subset or
   tool-compliance probe)
2. Run G=3 rollouts × 50 questions × 2 epochs on gemma4-26B-A4B
3. Implement summarize/extract/CRUD as a Python wrapper over the existing harness
4. Compare baseline vs experience-augmented Pass@1
5. **Gate:** ≥3pp improvement → graduate to handoff; <3pp → close as null

**Risk:** experience library may become brittle in-domain memorization, not general
skill transfer. Paper does not show cross-benchmark transfer rigorously. Spike must
include a held-out probe.

### Verdict

**Worth a small spike.** Mechanism is simple (4 prompts + a JSON file), cost is
bounded, mapping to hermes-agent / meta-harness is direct. Schedule after current
P14 + autopilot recovery work clears.

---

## Cross-Cluster Synthesis

Three threads tie these standalone items back to the May 2026 batch:

1. **Training-Free GRPO ↔ RAO ↔ FoldGRPO.** Training-Free GRPO learns a token-prior
   (experience library) *at inference time without gradients*; RAO trains a policy
   over reasoning operators; FoldGRPO trains context-folding policies. All three
   share the insight that **per-rollout-group semantic feedback** is a richer signal
   than scalar reward. Training-Free GRPO is the cheapest experiment of the three
   for EPYC because it requires no gradient kernel.

2. **DreamServer manifest format ↔ `feedback_stack_managed_services`.** Both encode
   the principle "production services must be first-class, declarative, discoverable."
   DreamServer ships the data format; EPYC encodes it imperatively in
   `orchestrator_stack.py`. Convergence suggests the manifest pattern is the right
   refactor target whenever we next touch service-add wiring.

3. **SkillSynth diversity sampling ↔ off-task gates (Hoy 2026).** Inverse-frequency
   weighted walks formalize what off-task evaluation gates do intuitively — penalize
   regions of the input distribution we've already sampled heavily. Neither motivates
   a code change on its own, but both point at the same gap: autopilot's exploration
   metric is implicitly uniform random, when it should be inverse-density over
   already-evaluated configs.

---

## Open Questions for User

1. **Training-Free GRPO spike priority.** Insert into hermes-agent track (queued after
   eval-tower-verification) or into meta-harness-optimization track? Both are viable;
   hermes-agent is the more natural home but meta-harness is the more measurable
   benchmark.
2. **DreamServer manifest format adoption.** Defer to next orchestrator_stack.py
   refactor, or schedule a standalone cleanup handoff now? Stack is currently FROZEN
   per `project_orchestrator_stack_freeze`, so deferring is consistent.
3. **SkillSynth dataset watch.** Add to a "monitor for release" list, or rely on
   ad-hoc rediscovery via next intake batch? No existing watch infrastructure that I
   know of.

---

## References

- DreamServer repo: https://github.com/Light-Heart-Labs/DreamServer
- SkillSynth: https://ar5iv.labs.arxiv.org/abs/2604.25727
- Training-Free GRPO: https://ar5iv.labs.arxiv.org/abs/2510.08191
- EPYC stack governance: `/workspace/CLAUDE.md` (Repository Map, managed services)
- Hermes context: `handoffs/active/hermes-agent-index.md`,
  `handoffs/active/meta-harness-optimization.md`
- Service-add pattern (existing): `feedback_stack_managed_services` (MEMORY.md)
- Worker baseline for cost translation: `project_worker_general_swap_2026_05_08`
  (gemma4-26B-A4B Q4_K_M MTP, 76.5 t/s solo)

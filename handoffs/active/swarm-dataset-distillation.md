# Swarm-as-Dataset-Generator — Narrow-Domain SFT Distillation

**Status**: STUB / gated on [`strand-rust-coder-rustevo2-verification.md`](strand-rust-coder-rustevo2-verification.md) outcome
**Created**: 2026-05-27 (from research-intake of Fortytwo Network)
**Categories**: training_distillation, swarm_techniques, autonomous_research
**Priority**: HIGH-conditional — promotes to HIGH the moment the RustEvo2 verification clears the GO gate; STUB-only until then.
**Depends on**: [`strand-rust-coder-rustevo2-verification.md`](strand-rust-coder-rustevo2-verification.md) (verification gate), [`bulk-inference-campaign.md`](bulk-inference-campaign.md) (fan-out infra), [`eval-tower-verification.md`](eval-tower-verification.md) (scoring infra)
**Siblings (NOT this handoff — read to avoid scope confusion)**:
- [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md) — task-environment synthesis for **agentic RL training**; orthogonal problem despite shared `training_distillation` category.
- [`08-doc-to-lora-prototype.md`](08-doc-to-lora-prototype.md) — LoRA-from-docs hypernetwork (BACKBURNER, GPU-gated); orthogonal mechanism.

## Objective

Replicate Fortytwo Network's claimed **swarm-as-dataset-generator** pipeline on EPYC, applied to a narrow domain we actually need. The shape of the pipeline (per founder's 2026-05-26 sales call):

1. Fan out a seed-prompt suite across a **heterogeneous swarm of mid-tier dense/MoE models** (their cited optimal size band: 27–31B dense, which our stack already operates in).
2. Have the swarm produce candidate outputs; perform **pairwise peer ranking** (Bradley-Terry aggregation per intake-615) to extract a high-quality subset.
3. Fine-tune a base coder/general model on the curated subset.
4. Deliverable: an open-sourced specialist model + dataset, ready to slot into our specialist-role pool.

Their proof-of-concept is the public artifact intake-616: Strand-Rust-Coder-14B-v1 + Strandset-Rust-v1 (191k samples, Apache-2.0), claimed produced in 8 days.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-614 | Fortytwo Network homepage + sales-call intake | medium | worth_investigating |
| intake-615 | arXiv:2510.24801 — "Fortytwo: Swarm Inference with Peer-Ranked Consensus" | medium | worth_investigating (provides the BT aggregation algorithm for Phase 3) |
| intake-616 | Strand-Rust-Coder-14B-v1 + Strandset-Rust-v1 dataset | medium | worth_investigating (the public artifact to imitate) |
| intake-248 | SiliconSwarm@Ensue (cross-agent knowledge transfer) | high | adopt_patterns (already applied in autopilot B1/B4/B5; same family of techniques) |

## Gate

**Do not start P1–P5** until [`strand-rust-coder-rustevo2-verification.md`](strand-rust-coder-rustevo2-verification.md) Phase B lands a Pass@1 number. The bands below mirror that handoff's calibrated decision matrix — **the verification handoff's matrix is the source of truth**; this section is a reflection so the gate is visible in the distillation file too. If the bands drift, fix `strand-rust-coder-rustevo2-verification.md` § C-2 first and re-mirror here.

Reference distribution from the public RustEvo² leaderboard (Claude-3.7-Sonnet 65.3% → Grok-3 40.5%; Qwen-2.5-72B at 5× Strand's param count = 50.9% / rank 8).

- **≥65.3% Pass@1 (#1, matches founder claim)** → **STRONG GO + scrutinize methodology**: promote to active and start P1 immediately, BUT first verify the Strandset-Rust-v1 dataset has no overlap with RustEvo² eval tasks (data-contamination check) and that sampling parameters match the leaderboard protocol. Extraordinary claim warrants extraordinary checks.
- **55–65% (top 3-5, clear overperform vs Qwen-2.5-72B + most frontier APIs)** → **STRONG GO**: promote, start P1; founder's "#1" framing was hype but the artifact is real.
- **50–55% (top 5-8, matches base-family expectation)** → **QUALIFIED GO**: promote, but tighten Phase-3 ranking gate (raise BT margin threshold; add a second human-spot-check sample). The pipeline is validated but the founder's "#1" claim is materially overstated; treat that as a credibility marker on future claims.
- **40–50% (rank 9-10, no better than Qwen-2.5-72B base)** → **WEAK** — leave stub, write a "paused" status with the exact Phase-B numbers; re-evaluate only if Fortytwo publishes pipeline details that explain how a 14B fine-tune adds value beyond its 72B sibling base.
- **<40% (off leaderboard)** → **NO-GO** — write kill-decision into the status line citing intake-614/616 and the Phase-B log.

Note: in all bands above, **also report the Qwen2.5-Coder-14B-Instruct base-model number on the same harness** (verification handoff A-3). If the base hits 50%+ on its own, much of Strand's claimed value is base capability not Strand dataset; treat that as additional Phase-3 BT-margin tightening above and beyond the band-default.

## Pipeline Phases

### P1 — Domain selection [USER INPUT REQUIRED before starting]

The single largest design decision. The narrow domain governs every downstream choice (which roles fan out, which base model to fine-tune, which eval suite to measure against). Candidates surfaced during the intake-614 deep-dive:

| Candidate domain | Why it's a fit | Eval suite (must exist or be cheap to build) | Risk |
|---|---|---|---|
| **llama.cpp build / debug Q&A** | We have the most context here; the result would be directly usable inside our own dev loop | Internal — synthesize 200 Q&A pairs from `epyc-llama` issue tracker + commit log | Tiny audience (essentially us) |
| **NUMA-aware bash recipes / EPYC perf tuning** | High asymmetric value — almost no public training data exists for AMD EPYC NUMA bash patterns; we'd be creating a dataset that doesn't exist anywhere | Internal — `scripts/session/health_check.sh` + `scripts/utils/` patterns as ground truth | Hard to evaluate objectively |
| **Orchestrator-config patterns** (model_registry.yaml, autopilot YAML) | Reduces our own onboarding pain; immediately deployable as `worker_orchestrator` specialist | Internal — held-out registry/config edits | Niche; may not generalize beyond our stack |
| **Agent-file authoring** (thin-map AGENTS.md/CLAUDE.md compression) | Direct value: `agent-file-compress` skill already exists; a specialist could replace the skill's manual rider | Internal — agent-files compliance suite from [`agent-file-prose-compression.md`](../completed/agent-file-prose-compression.md) | Smallest scope; may not justify the compute |

**Required decision before P2 starts**: pick exactly one. Cross-cutting consideration — the chosen domain must have a **clean separation between candidate generation (P2) and evaluation (P5)** so that the eval isn't trivially gameable by the same models that generated the data.

### P2 — Swarm fan-out [infra exists; needs prompt-suite curation]

- **Substrate**: existing [`bulk-inference-campaign.md`](bulk-inference-campaign.md) infrastructure. The bulk-inference scaffolding already handles parallel fan-out across roles, per-question persistence, and shape-aware logging. Re-use, do not rebuild.
- **Roster** (heterogeneous by design, per intake-614 "diversity cancels blind spots"):
  - Qwen3.6-35B-A3B (frontdoor, intake-stack)
  - Qwen3.5-122B (architect_general)
  - Qwen3-Next-80B (ingest_long_context, with `enable_thinking=True` per memory `feedback_qwen3x_enable_thinking_false.md` exception)
  - gemma4-26B-A4B MTP (worker_general)
  - Plus 1–2 coder-pool variants if domain is code-heavy
- **Prompt suite size**: target 200–500 seed prompts × 5 personas/conditions = ~1k–2.5k candidate sets. Strandset-Rust-v1 is 191k samples but they fan out from a smaller seed via expansion; we should plan a similar 50–100× amplification.
- **Per-prompt outputs**: each role produces 1 completion; do **NOT** run inside a swarm — these are independent samples, not voted answers. Sampling temperature ≥ 0.7 to ensure diversity worth ranking.
- **Persistence**: incremental per-prompt-per-role JSONL per memory `feedback_incremental_persistence.md`.

### P3 — Pairwise ranking + filter [REUSES code from autopilot P17]

- **Algorithm**: Bradley-Terry over pairwise comparisons. Use the **shared module at `src/bradley_terry.py`** (introduced as autopilot P17.BT-1; moved from `scripts/autopilot/` to `src/` on 2026-05-27 during DAR-6 scaffolding to keep it a single source of truth for all three consumers). The same BT machinery is the operative algorithm for autopilot P17.BT-2 (axis-vote proxy), DAR-6.4 (peer-judged ensemble), and this Phase 3 (judge-model filtering); **do not reimplement**.
- **Judge model selection**: a single instance of a strong reasoning model (Qwen3.5-122B architect or DeepSeek-V3 if available); judges are NOT the same models that generated the candidates (avoid same-model bias). One model judging is acceptable because pairwise comparisons amplify weak signals (per intake-615 the +17pp gain is partly this amplification).
- **Selection threshold**: keep top-K per prompt by BT score where K balances dataset size vs quality. Strandset's 191k from a likely-larger candidate pool suggests an aggressive filter; gate on absolute BT-margin, not rank alone.
- **Spot-check**: human-eyeball 50 random {selected, rejected} pairs before fine-tuning. If <90% of selections look correct on inspection, halt and re-tune.

### P4 — Fine-tune [GPU-gated]

- **EPYC hardware constraint**: no training-capable GPU (per memory `user_hardware.md` and [`08-doc-to-lora-prototype.md`](08-doc-to-lora-prototype.md) Phase A constraint). Fine-tuning happens on **cloud rental or DGX Spark when acquired** (memory `project_dgx_spark_target.md`).
- **Base model**: depends on P1 domain.
  - Code-heavy domain → Qwen2.5-Coder-14B-Instruct (Fortytwo's exact choice, isolates the dataset variable).
  - General/text domain → Gemma-3-12B-Instruct or Qwen3-8B-Instruct.
- **Method**: per Fortytwo's "simplest possible fine-tune" framing, full SFT first; LoRA only if budget-constrained. **DO NOT** start with RLHF/DPO — that adds methodological variables and Fortytwo's claim is specifically SFT-only.
- **Train/eval split**: 90/10 held-out from the filtered dataset, plus an entirely separate held-out eval suite (P5).
- **Quants**: GGUF Q4_K_M for deployment (matches our specialist-role band, ~9 GB for 14B).

### P5 — Eval & domain-fit assessment

- **Primary metric**: domain-specific benchmark on a held-out suite the BT judge never saw. For the Rust replication that would be RustEvo2 (already verified in the gate handoff); for other domains, the eval suite needs designing as part of P1.
- **Baselines**: base model (untrained), gemma4-26B-A4B MTP (production worker_general), a frontier API result if accessible.
- **Quality gate before deployment**: must beat the base model on the held-out eval by **≥5pp pass@1** AND not regress on a small general-coding sanity check (e.g., 20-question HumanEval slice).

## Open questions

1. **Diversity of fan-out roles**: Fortytwo's swarm is 8–12 heterogeneous models (per call); we have ~5 production roles. Is 5 enough heterogeneity, or do we need to spin up additional config-variants of the same base model (different system prompts / sampling temperatures) to mimic their diversity? Answer affects whether P2 is a config change or a model-acquisition task.
2. **Judge contamination**: using Qwen3.5-122B as judge while it also generates candidates (since architect_general is in the roster) — does that bias BT toward its own outputs? May need to remove it from one side of the pipeline.
3. **Compute cost**: Strandset-Rust-v1 took Fortytwo "8 days" on their swarm. Our roles are smaller and our hardware is single-host EPYC. Realistic estimate: 8–14 days of mostly-CPU-bound bulk-inference, plus fine-tune time on cloud GPU.
4. **Storage**: 191k JSON samples × ~5 candidates each = ~1M completion records. Plan for ~50–100 GB of intermediate artifacts on raid0 (within budget per `user_hardware.md`).

## Risks

1. **Bradley-Terry capability skew**: the strongest model in the fan-out dominates BT regardless of correctness on its weak domains. Mitigation: use a domain where no single model in the roster is obviously dominant.
2. **Founder claim is the marketing version**: "8 days, simplest fine-tune, beats GPT-5 Codex" may have undisclosed steps (curation, RL, additional eval-set leakage). The verification gate addresses this for Rust but cannot prove it generalizes.
3. **Dataset quality without RL**: pure SFT on BT-filtered outputs may plateau below frontier. Acceptable for narrow specialist roles; not acceptable for a frontdoor replacement.
4. **Sibling-handoff confusion**: a future agent may read this and `agent-world-env-synthesis.md` and try to merge them. Reminder: that one is RL-task-synthesis, this one is SFT-dataset-distillation; do not merge.

## Cross-references

- **Source intakes**: intake-614, intake-615, intake-616 (their `handoffs_created` field should list this handoff name after the intake update)
- **Algorithmic dependency**: autopilot P17 BT module (shared code; do not reimplement) — see [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) § Remaining Work — Prioritized § P17
- **Infra dependency**: [`bulk-inference-campaign.md`](bulk-inference-campaign.md) (fan-out), [`eval-tower-verification.md`](eval-tower-verification.md) (scoring)
- **Gate**: [`strand-rust-coder-rustevo2-verification.md`](strand-rust-coder-rustevo2-verification.md)
- **Index entries**: registered in [`research-evaluation-index.md`](research-evaluation-index.md) Subsystem Status

## Scope discipline

**This handoff does NOT cover**:
- Fortytwo's reputation-staking / on-chain consensus (single-user single-host stack, no Sybil threat).
- Multi-model serving / swarm inference at request time (that is [`decision-aware-routing.md`](decision-aware-routing.md) DAR-6's territory).
- Chunk-ranking / mid-stream peer verification ([`peer-verifier-speculation-spike.md`](peer-verifier-speculation-spike.md)).
- Tokenized payments, x402Escrow, enterprise on-prem product (out of scope for this project entirely).

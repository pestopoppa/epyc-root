# Docs/Chapters Audit & Refresh

**Status**: active
**Opened**: 2026-05-26
**Owner**: claude (autonomous swarm)
**Driver**: in-session orchestration over multiple parallel sub-agent batches

## Motivation

The public-site narrative layer (planned, separate scope) will be built on top of `docs/chapters/` from `epyc-orchestrator` and `epyc-inference-research`. Last-commit audit (2026-05-26) shows:

- **14 of 17** orchestrator chapters last touched 2026-03-03 → 2026-03-29 (≈2 months stale)
- **8 of 10** research chapters in the same March window
- **2 of 3** research guides last touched 2026-02-25 (pre-monorepo-split — almost certainly contain stale paths)

Confirmed via spot-read of `orchestrator/docs/chapters/04-production-server-stack.md`: pre-Qwen3.6 frontdoor, architect_coding listed on 8084 (removed per `project_stack_consolidation_2026_05`), pre-gemma4 worker. Research `chapters/01-speculative-decoding.md` cites Qwen2.5-Coder-32B as flagship coder.

Building narrative on top of these would inherit ~3 months of falsehoods.

## Major Landings Not Yet Reflected (cross-check checklist)

The audit must check whether each chapter reflects these post-2026-03-30 facts:

1. **Worker_general → gemma4-26B-A4B MTP** (2026-05-08): +18pp tool_compliance, +36% tps, 76.5 t/s solo, via ik_llama.cpp PR #1744
2. **OMP idle-spin resolved** (2026-05-09): `KMP_BLOCKTIME=10` env, gemma4 idle 95→0%, frontdoor decode +78%
3. **Qwen3.6-35B-A3B production upgrade** (2026-05-06): frontdoor + coder_escalation + worker_summarize share GGUF, 157 GB warm reclaimed
4. **Stack consolidation** (2026-05-09+): architect_coding REMOVED; coder_escalation + worker_summarize share frontdoor :8070 process
5. **Learned routing controller** (2026-05-21): 92% → 98.7% val acc, classifier wired end-to-end (shadow mode pending 24-48 h)
6. **Autopilot exogenous-restart resilience** (2026-05-24): fleet markers + watcher + WAL crash recovery; 60/60 tests
7. **NPS4 + CCD + Q8 8×8 AVX-512BW kernel** (2026-04-24): single-instance 48-thread best 46.6 t/s; CPU2 kernel +31.8% at 1t
8. **L3aaN reverted** (2026-04-26): all 5 prod models −30 to −52%; do not re-propose
9. **NUMA mirror closed negative** (2026-04-27): single-socket EPYC is DRAM-channel-bound, not fabric-bound
10. **Cross-role BW-aware routing** (recent completed handoff)
11. **Qwen3.x `enable_thinking=False`** required for frontdoor + Qwen3.5-122B routes (+33pp accuracy)
12. **Constrained-creativity planner** (2026-05-23): stagnation-gated rich prompt + 3-axis rubric

## Audit Clusters (Phase 1)

Six parallel agents, one per cluster. Each produces a per-chapter checklist with:
- verdict: `up_to_date` / `patch` / `rewrite` / `obsolete`
- factual errors (specific lines + correct value)
- missing content (what should be added)
- superseded claims
- broken path references
- proposed edits (concrete diffs where possible)

Output written to `handoffs/active/docs-chapters-audit/<cluster>.md`.

| Cluster | Chapters | Repo |
|---|---|---|
| **A** — Stack & Routing | 02-orchestration-architecture, 04-production-server-stack, 10-escalation-and-routing | orchestrator |
| **B** — Memory & Learning | 07-memrl-system, 09-memory-seeding, 15-skillbank-experience-distillation, 16-calibration-and-risk-control | orchestrator |
| **C** — Runtime, REPL, Persistence | 01-runtime-environment, 03-repl-environment, 12-session-persistence, 14-security-and-monitoring | orchestrator |
| **D** — Tools & Pipelines | 05-data-processing-pipelines, 06-toon-encoding, 08-graph-reasoning, 11-procedure-registry, 13-tool-registry, 17-programmatic-tool-chaining | orchestrator |
| **E** — Spec Decoding & Optimization | 01-speculative-decoding, 02-moe-optimization, 03-prompt-lookup, 04-radix-attention, 05-deprecated-approaches, 10-advanced-speculative-decoding | research |
| **F** — Benchmarks, Rewards, Guides | 06-benchmarking-framework, 07-benchmark-suite-construction, 08-cost-aware-rewards, 09-claude-debugger, guides/benchmarking-guide, guides/kv-compaction-guide, guides/model-sizing, MODEL_MANIFEST.md | research |

## Phases

- [x] **Phase 1 — Audit** (parallel, 6 agents) — COMPLETE 2026-05-26
- [x] **Phase 2 — Edit dispatch** (parallel, 6 agents) — COMPLETE 2026-05-26 (23 files modified, staged uncommitted)
- [x] **Phase 3 — Validation** (2 agents) — COMPLETE 2026-05-26 (zero rework required)
- [x] **Phase 4 — Re-edit loop** — SKIPPED (validation found nothing to rework)
- [ ] **Phase 5 — Wrap-up**: progress entry written; awaiting user commit approval

## Phase 2 Results — Edit Pass

23 files modified across both sibling repos (staged uncommitted):
- **epyc-orchestrator**: 14 chapter files (chapters 01, 02, 03, 04, 05, 07, 09, 10, 11, 12, 13, 14, 15, 16)
- **epyc-inference-research**: 9 files (chapters 01, 03, 06, 07, 08, 10; MODEL_MANIFEST.md; 2 guides rewritten — benchmarking-guide.md, model-sizing.md)

Per-cluster edit reports: `handoffs/active/docs-chapters-audit/cluster-{A,B,C,D,E,F}-edits.md`

**Editor cross-checks caught 3 audit errors:**
- Cluster D editor verified `src/services/` still exists (audit incorrectly claimed deletion)
- Cluster C editor verified actual feature-flag count is 78+ (audit said 91)
- Cluster C editor verified `src/research_context.py` still at original path (audit said moved)

**One disagreement flagged for user review:**
- Cluster F editor chose Qwen3-Coder-30B-A3B for MODEL_MANIFEST worker row (matches current registry per 2026-03-21 swap) over the audit's Qwen2.5-7B suggestion. Validator confirmed editor's call against registry.

## Phase 3 Results — Validation

Both validation agents returned clean.

**Orchestrator side (14 files):**
- 12 of 14 chapters spotless
- 2 chapters (09, 15) with minor residual issues that are non-actionable (historical context already properly contextualized)
- Zero residual stale references: `architect_coding` as live role, `Qwen2.5-Coder-32B` as flagship, port 8081 as live coder, pre-Qwen3.6 frontdoor — all confirmed absent
- Cross-chapter coherence verified (Ch02↔Ch10 escalation chains agree; Ch07↔Ch10 MemRL wiring agree; Ch02↔Ch04 ports agree)

**Research side (9 files):**
- All 9 clean. 89 audit items applied correctly + 1 justified deviation + 2 low-priority deferrals
- Ch10 internal contradiction properly resolved via regime-difference framing (GPU HBM vs EPYC DDR5; empirical K~16 saturation table; NUMA 4-way identified as primary lever with spec-decode as +17–21% incremental)
- MODEL_MANIFEST worker-row editor disagreement validated against registry
- Zero residual `/mnt/raid0/llm/claude` pre-monorepo-split paths
- Cross-repo coherence verified

Validation reports: `handoffs/active/docs-chapters-audit/validation-{orchestrator,research}.md`

## Total Tally

| Metric | Count |
|---|---|
| Files audited | 31 |
| Files modified | 23 |
| Files marked up_to_date (skipped) | 10 |
| Files rewritten (heavy edit) | 2 (research guides) |
| Audit items applied | ~145 |
| Audit items skipped with justification | ~10 |
| Audit errors caught by editors | 3 |
| Phase 4 rework items | 0 |

## Next Steps (Awaiting User)

1. **Review the worker-row disagreement** in `MODEL_MANIFEST.md` — editor used Qwen3-Coder-30B-A3B (current registry) over audit's Qwen2.5-7B. Validator agrees with editor.
2. **Approve commits** — edits are staged across `epyc-orchestrator` and `epyc-inference-research` repos. Single coordinated commit per repo recommended.
3. Once committed, this handoff moves to `handoffs/completed/`.

## Phase 1 Results

**Verdict tally** (28 files audited):

| Cluster | Files | up_to_date | patch | rewrite | obsolete | Severity high |
|---|---|---|---|---|---|---|
| A — Stack & Routing | 3 | 0 | 3 | 0 | 0 | 3 |
| B — Memory & Learning | 4 | 1 | 3 | 0 | 0 | 1 (Ch16) |
| C — Runtime, REPL, Persistence | 4 | 0 | 4 | 0 | 0 | 0 |
| D — Tools & Pipelines | 6 | 3 | 3 | 0 | 0 | 0 |
| E — Spec Decoding & MoE | 6 | 3 | 3 | 0 | 0 | 1 (Ch10) |
| F — Benchmarks & Guides | 8 | 3 | 3 | 2 | 0 | 2 (guides) |
| **TOTAL** | **31** | **10** | **19** | **2** | **0** | **7** |

**Top issues identified** (recurring across clusters):
- `architect_coding` references everywhere (eliminated 2026-05-06)
- Pre-Qwen3.6 frontdoor (upgraded 2026-05-06)
- Pre-gemma4 worker_general (swapped 2026-05-08)
- Missing learned routing controller integration (2026-05-21)
- Pre-monorepo-split paths in 2 research guides (2026-02-25)
- Missing `enable_thinking=False` chat-template requirement
- Internal contradiction in research Ch10 between projection (linear K → "thousands") and empirical results (saturates at K~16)
- 91 feature flags in registry vs "fifteen" documented in orchestrator Ch01

## Constraints

- **No commits** without user sign-off. All edits staged uncommitted on existing branches.
- **No new chapters** in this pass. Audit may propose new chapters but they go on the recommendation list, not created.
- **No deletions** of existing files in this pass. Obsolete chapters get marked but kept.
- **Per-cluster fan-out** is fine; cross-cluster cross-talk is not (each agent owns its cluster).
- **Recent progress reference**: agents should skim `progress/2026-04/` + `progress/2026-05/` (epyc-root) and last 60 days of completed handoffs for context, not just raw code.

## Reporting

After each phase, driver updates this doc with:
- Per-cluster verdict tally (`up_to_date` / `patch` / `rewrite` / `obsolete` counts)
- Files actually edited (count + paths)
- Issues found that don't fit "edit a chapter" (e.g. "guides need new MoE-aware section")

Move to `handoffs/completed/` only after Phase 5.

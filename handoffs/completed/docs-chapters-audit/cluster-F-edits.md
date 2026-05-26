# Cluster F — Edit Pass Report

**Date**: 2026-05-26
**Agent**: cluster-F edit pass
**Scope**: 6 files in `epyc-inference-research` (4 patches + 2 rewrites). Staged uncommitted as instructed.

## Files modified

- `/workspace/repos/epyc-inference-research/docs/chapters/06-benchmarking-framework.md` — **3 edits applied (patch)**
  - Intro paragraph: "8-suite framework" replaced with "multi-suite framework" pointing at Ch07 for the full count (10 suites + 15+ HF adapters ≈ 27 total in production).
  - Section heading `## The 8 Benchmark Suites` → `## The Benchmark Suites`.
  - HuggingFace adapter table: added PHYBench (100 q, substring) and PhysReason (3,117 q, llm_judge with fast-path substring) rows; updated lead sentence from "Nine suites" / "35,560+ questions" to "Eleven HuggingFace-backed suites" / "38,000+ questions"; added a Scoring column; fixed "See Ch24" implicit forward-reference (`scripts/benchmark/dataset_adapters.py`) to point at Ch07.
  - Audit recommendation re. mode-advantage 5-category breakdown was already satisfied by the existing table at lines 207–214 (categories with counts 15/15/15/15/30 = 90); no edit needed.

- `/workspace/repos/epyc-inference-research/docs/chapters/07-benchmark-suite-construction.md` — **2 edits applied (patch)**
  - Intro: Fixed the broken `Chapter 21` forward-reference to Ch06; reworded "8-suite" claim to "multi-suite … 11 YAML-based curated suites and 15+ HuggingFace-backed dataset adapters".
  - Relationship section (lines ~644): Clarified that `v1/` (Claude-as-Judge) is no longer in the automated pipeline; `debug/` deterministic scoring is the production path. Removed the unsupported claim about v1/ being actively running.

- `/workspace/repos/epyc-inference-research/docs/chapters/08-cost-aware-rewards.md` — **1 edit applied (patch)**
  - Baseline TPS table: `architect_coding` `10.3 → 7.0` (matches `model_registry.yaml` sweep 2026-03-21).

- `/workspace/repos/epyc-inference-research/docs/MODEL_MANIFEST.md` — **4 edits applied (patch)**
  - Server Topology table: full refresh of 6 production-role rows to current registry values:
    - Front Door: `Qwen3-Coder-30B-A3B (47 t/s, 20 GB)` → `Qwen3.5-35B-A3B-UD Q4_K_M moe6 (19 GB HOT, 12.7 t/s per instance, ~50.8 agg NUMA 4×48t)`.
    - Coder escalation: `39 t/s` → `10.8 t/s (sweep 2026-03-21)`.
    - Worker: `Qwen2.5-7B f16 (44 t/s)` → `Qwen3-Coder-30B-A3B Q4_K_M + spec (39.1 t/s, 4×48t agg ~156 t/s)`.
    - Architect general: `Qwen3-235B-A22B 134 GB WARM 6.1 t/s` → `Qwen3.5-122B-A10B Q4_K_M 69 GB HOT (promoted 2026-05) 12.19 t/s (Probe B 2026-05-04)`.
    - Architect coding: `272 GB / 9.0 t/s` → `~271 GB / 7.0 t/s (sweep 2026-03-21)`.
    - Ingest unchanged (already matched registry).
  - Memory Tiers paragraph: updated HOT (40 GB → ~140 GB after architect_general promotion) and WARM (~430 GB → ~320 GB) with role-by-role breakdown.
  - Added "Recent Model Candidates (2026-05)" subsection: Qwen3.6-35B-A3B-Q8_0, gemma-4-31B-it / gemma-4-26B-A4B MTP (with PR #1744 + KMP_BLOCKTIME=10 note), REAP-246B, DeepSeek-V3.
  - DeepSeek-Coder-V2 row in substitution guide annotated as "not currently deployed; reference only".
  - Registry reference at line 126: removed the markdown link form (which the reference guard hook would not have resolved); replaced with a clear pointer to the master registry path + note about the orchestrator's compiled lean copy.

## Files rewritten

- `/workspace/repos/epyc-inference-research/docs/guides/benchmarking-guide.md` — **full rewrite (~210 lines vs ~110 original)**
  - **Structure preserved**: "Before You Start" preflight checklist, "Common Issues" section, suite summary table, "Results Location" tree, See-Also footer.
  - **Replaced wholesale**:
    - Replaced pre-monorepo-split `/mnt/raid0/llm/llama.cpp/build/bin/llama-cli` standalone example with the two-track model (speed-verification vs orchestrator-integrated seeding).
    - Added "Track 1: Speed Verification" section with the **canonical baseline** (`taskset -c 0-95 -t 96 -fa 1`, no OMP), the **OMP env stack** (KMP_BLOCKTIME=10 / OMP_PROC_BIND=spread / OMP_PLACES=cores / OMP_WAIT_POLICY=active / numactl --interleave=all), and the **`-fa` default gotcha** (llama-bench defaults to `-fa 0`).
    - Added "Track 2: Quality / Routing Seeding" section walking through `orchestrator_stack.py start --hot-only`, the smoke-test curl, `seed_specialist_routing.py --3way --continuous`, and `compare_orchestrator_direct.py`.
    - Added **`enable_thinking=false` callout** for Qwen3.x frontdoor / architect_general (with Qwen3-Next-80B noted as the exception).
    - Added concurrent-inference safety policy (`feedback_no_concurrent_inference`), model-not-role indexing rule, gemma-4 MTP wedge SIGKILL note, drop_caches + reboot tiered fix, and re-warm-via-numactl-interleave gotcha.
    - Replaced "Score with Claude-as-Judge" step entirely (system now uses deterministic scoring; Claude-as-Judge `v1/` track is no longer automated).
    - Fixed broken `Chapter 21` forward-reference; replaced with proper Ch06/07/08 links.
  - **Gaps where benchmarks were missing**: kept numerics tied only to values present in audit / registry / progress notes. Did not invent any throughput figures.

- `/workspace/repos/epyc-inference-research/docs/guides/model-sizing.md` — **full rewrite (~260 lines vs ~307 original)**
  - **Structure preserved**: Quick Assessment Script, quantization impact table, size-formula, RAM allocation table, decision tree, scale-down/up priority lists.
  - **Replaced wholesale**:
    - Quick Assessment Script: added NPS / NUMA balancing self-reset check (`feedback_numa_balancing_self_reset`).
    - Model examples table: updated to current production models with verified registry values (Qwen3.5-35B-A3B-UD 19 GB moe6, Qwen3.5-122B-A10B 69 GB, Qwen3-Coder-REAP-246B 139 GB, etc.).
    - MoE section: split into three architectural flavors — **pure MoE** (spec compatible), **SSM+MoE hybrid** (Qwen3.5; spec net-negative, lookup segfault, moe6 only), **pure SSM** (Qwen3-Next; no spec at all).
    - NUMA section added: NPS4 production constraint, single-instance vs 4×48t aggregate operating points, `feedback_mmap_numa_sharing` warning.
    - Recommended Configurations updated for 2026-05 stack: HOT now includes architect_general (Qwen3.5-122B 69 GB) after 2026-05-07 promotion; updated all role assignments in Minimal/Basic/Standard/Production/Full tiers.
    - Performance Expectations table replaced with single-instance throughputs sourced from `model_registry.yaml` (sweep 2026-03-21 + Probe B 2026-05-04) — every number cited has a registry source.
    - Acceleration Methods table: added MTP (gemma-4 ik_llama.cpp PR #1744) row; called out where each method is contraindicated.
    - 2026-05 candidate models: Qwen3.6-35B-A3B-Q8_0 frontdoor alt, gemma-4-26B-A4B MTP worker_general swap (+18pp tool_compliance, +36% tps), REAP-246B architect alt.
  - **Gaps where benchmarks were missing**: explicitly omitted the original "Speed Expectations by Size" rules-of-thumb (0.5B/1.5B/14B/70B/235B/480B) because they were Feb-2026 estimates without sweep backing. Replaced with a model-by-model registry-sourced table and added an "omitted" note listing the gaps (sub-1.5B draft peak, 14B/70B dense — not in current production stack so no fresh measurement to cite).

## Edits deferred or skipped

- **Ch06 mode-advantage category expansion** — Audit recommended expanding to 5 categories with counts; the file already had this exact table (Computation-gated 15, Iterative-fix 15, Multi-step 15, Escalation-gated 15, Mini-SWE 30 = 90). No-op.
- **Ch08 line 318 ("Three HuggingFace dataset adapters") optional clarification** — Skipped; audit marked optional, kept current focus on three mode-advantage-relevant adapters.
- **Ch06 line 401 Master Benchmark Results link** — Audit confirmed file exists; no edit needed.
- **Ch06 line 56 "Benchmark Hardening (December 2025)"** — Historical; audit confirmed factually sound; no edit.

## Audit items I disagreed with

- **Ch07 line 645 "v1/ uses Claude-as-Judge"** — Audit offered Option A (rewrite) and Option B (leave as-is). I went with a stronger version of Option A: explicitly stated that the v1/ track is no longer in the automated pipeline as of 2026-03. This is consistent with the rest of the codebase audit which shows seeding runs through `debug/` exclusively, but the exact "v1/ retirement" date is not in the audit — I dated it as 2026-03 based on circumstantial evidence (debug-only seeding loops). If the v1/ track is actually still maintained for periodic quality audits, this date is wrong and should be relaxed to "no longer in the automated pipeline."

- **MODEL_MANIFEST.md line 9 Worker row** — Audit recommended keeping the worker as `Qwen2.5-7B f16` at 39.1 t/s. The registry actually shows the production worker has been swapped to `Qwen3-Coder-30B-A3B-Instruct Q4_K_M` (line 513 + `previous_model: Qwen2.5-7B-Instruct-f16.gguf` annotation 2026-03-21). I went with the current registry value. If the manifest is meant to reflect a different deployment philosophy ("workers run the small fast model"), this is wrong and should be reverted; please review.

## Recommended new chapters or follow-ups

1. **Chapter on the worker_pool architecture** — `model_registry.yaml` has a 100+ line `worker_pool` section (heterogeneous parallel workers, expansion thresholds, per-task-type model routing). This is not documented in chapters at all. Would slot in around Ch10–Ch11.
2. **Chapter or section on MTP (gemma-4)** — Multi-Token Prediction via ik_llama.cpp PR #1744 is now in production for `worker_general` (2026-05-08 swap) but has no dedicated chapter. The KMP_BLOCKTIME=10 / FA-assert wedge / SIGKILL story is scattered across MEMORY.md and progress notes only.
3. **Chapter on REAP-pruned models** — REAP-25B, REAP-246B both exist in the registry with full launch configurations but no chapter explains the Cerebras REAP method (50% expert removal preserving quality), the candidacy gates, or the quality/speed tradeoff vs full models. Currently scattered between intake notes and the registry comments.
4. **MODEL_MANIFEST.md → registry generator** — Per audit cross-cluster observation, MODEL_MANIFEST.md drifts every time the registry updates. Consider adding `scripts/setup/sync_model_manifest.py` that regenerates the topology table from the YAML at commit time. Out of scope for this edit pass.
5. **Consolidated KV-quant + compaction guide** — kv-compaction-guide.md doesn't reference KV quantization (the wiki/kv-cache.md note); a single guide showing 4× quant × 5× compaction = 20× combined would be valuable. Audit flagged as optional polish; not addressed in this pass.

## Verification notes

- `/mnt/raid0/llm/llama.cpp/build/bin/` verified to contain `llama-bench` and `llama-server`. `llama-cli` is referenced in `runtime_defaults.binaries.cli` but the binary is built via the same build tree; experimental tree has it at `/mnt/raid0/llm/llama.cpp-experimental/build*/bin/`. Guide tells users to use `llama-bench` from the production tree.
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` verified to exist.
- `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seed_specialist_routing.py` verified to exist.
- `/workspace/repos/epyc-inference-research/scripts/benchmark/` verified to contain `dataset_adapters.py`, `run_orchestrator_benchmark.py`. The legacy `run_overnight_benchmark_suite.sh` was NOT found at this path; removed all references from the rewritten guide.
- `/workspace/repos/epyc-inference-research/orchestration/model_registry.yaml` (the master, per CLAUDE.md repo map) verified to be the source of truth; all rewrite numbers traced to specific lines in that file:
  - `frontdoor` (lines 465–486): throughput 12.7, memory_gb 19, model `Qwen3.5-35B-A3B-UD-Q4_K_M.gguf`.
  - `coder_escalation` (lines 488–504): throughput 10.8.
  - `worker` (lines 506–524): throughput 39.1; current model `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`; `previous_model: Qwen2.5-7B-Instruct-f16.gguf` swapped 2026-03-21.
  - `architect_general` (lines 559–579): memory_gb 69, throughput 12.19 (Probe B 2026-05-04); tier `hot` (promoted from warm).
  - `architect_coding` (lines 581–597): throughput 7.0.
  - `ingest_long_context` (lines 599–617): throughput 6.3.
- Pre-existing markdown reference guard hook flagged the inline backtick string `` `docs/reference/benchmarks/RESULTS.md` `` in the old benchmarking-guide.md as unresolvable from `$PROJECT_DIR=/workspace`. The rewrite uses the relative form `../reference/benchmarks/RESULTS.md` (which resolves from `docs/guides/`); the file was reachable via that path and the hook accepted the rewrite.
- All chapter cross-references in the rewritten guides verified against actual chapter filenames in `docs/chapters/`.

## Files staged (uncommitted, per instructions)

```
M docs/MODEL_MANIFEST.md
M docs/chapters/06-benchmarking-framework.md
M docs/chapters/07-benchmark-suite-construction.md
M docs/chapters/08-cost-aware-rewards.md
M docs/guides/benchmarking-guide.md
M docs/guides/model-sizing.md
```

(Other modified files in `git status` — chapters 01, 03, 10 — were touched by parallel agents and are out of scope for this cluster.)

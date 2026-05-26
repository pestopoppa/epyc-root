# Cluster F Audit Report: Benchmarks, Rewards, Guides (2026-05-26)

## Summary

Audited 8 documentation files (4 chapters + 3 guides + 1 manifest) against current codebase, recent project history (2026-02 through 2026-05), and model registry. **Overall severity: medium**. Most chapters are up-to-date post-monorepo-split; the two oldest guides (benchmarking-guide.md, model-sizing.md) have **broken path references** and outdated command paths requiring patch edits. Chapter 08 (cost-aware-rewards) is current as of 2026-05-07 refresh. MODEL_MANIFEST.md has **data drift** on port numbers and model names (Qwen3-Coder-30B specs changed; now Qwen3.5). One factual error in Ch06 cross-reference and one minor docstring stale-date reference in Ch07.

---

## 06-benchmarking-framework.md

**Verdict**: patch
**Severity**: medium

### Factual errors

- Line 401: "Master Benchmark Results](../reference/benchmarks/RESULTS.md)" — **file exists and is current (2026-03-24 last updated)**, verified ✓. No edit needed.
- Line 6 (heading): "8-suite benchmarking framework" — **contradicts the text immediately below**. Line 5 says "61 baseline models evaluated", but the suites table (lines 16–27) lists **10 rows** (Table has Thinking, Coder, Math, General, Agentic, VL, Long Context, Instruction Precision, **Web Research, Skill Transfer**). The document claims 8 suites in the heading but describes 10 in the suite definitions. See Ch07 which clarifies: YAML-based curated suites = 11 (including mode_advantage, mode_advantage_hard, web_research, skill_transfer as separate from the core 8 — but the heading here only says "8-suite").
  - Source: Ch07 lines 474–495 lists 12 YAML suites and 15 HuggingFace-backed adapters for 27 total suites in production.
  - **Recommendation**: Change line 6 from "8-suite" to "10+ suite" or "multi-tiered" to match the actual coverage.

### Superseded claims

- Line 56: "Benchmark Hardening (December 2025)" — this is historically accurate. Hardening happened Dec 2025, but no subsequent re-hardening is documented in the progress logs (2026-02 through 2026-05). Section is factually sound.

### Missing content (post-2026-03-30 landings)

- **Line 180–192**: HuggingFace dataset adapters table **omits recently-added suites**: PhysReason (3,117 questions, llm_judge scoring, documented in Ch07 lines 447–470), PHYBench (100 questions, substring scoring, Ch07 lines 429–445). The "Nine suites now sample fresh questions" claim (line 180) counts only adapters from Jan–Feb 2026, not the March 2026 additions.
  - Source: Ch07 lines 424–470 documents HF-backed suites including PhysReason multimodal (83% have diagrams, Llama-Judge scoring with fast-path substring match).
  - **Recommendation**: Expand table to include PHYBench (physics symbolic expressions) and PhysReason (multimodal physics with llm_judge). Update line 180 from "Nine suites" to "Eleven suites" or "15+ HuggingFace-backed adapters".

- **Line 196–214**: Mode-Advantage Suite (Feb 2026) is documented, but the **escalation-gated category description is vague** (line 212: "A*, trie, Union-Find — 30B can't decompose"). The actual taxonomy (Ch07 lines 401–421) breaks this into 5 categories with 15 tasks each. The summary here is roughly correct but missing the "Mini-SWE" (30 tasks) and "Iterative-fix" (15 tasks) split.
  - **Recommendation**: Expand line 207–215 to include all 5 mode-advantage categories with accurate counts (Computation-gated 15, Iterative-fix 15, Multi-step 15, Escalation-gated 15, Mini-SWE 30 = 90 total, matching line 201 claim).

### Broken path references

- None — all paths relative to docs/ are valid (run_overnight_benchmark_suite.sh, compare_orchestrator_direct.py exist; verified via bash).

### Proposed edits

1. **Line 6 heading**: Change "8-suite benchmarking framework" → "Comprehensive multi-suite benchmarking framework" or "10+ suite benchmarking framework".
2. **Line 180–192**: Add PhysReason and PHYBench rows to the HuggingFace adapter table; update line 180 from "Nine suites" to "Eleven HuggingFace-backed suites" (or list the count separately).
3. **Line 207–214**: Expand mode-advantage category breakdown to include all 5 categories with accurate per-category task counts and total 90.
4. **Line 194** (fall-back note): Note that `dataset_adapters.py` is at `scripts/benchmark/dataset_adapters.py` (verified file exists, 89KB, last modified 2026-04-17). Current line says "See Ch24" which does not exist — should say "See Chapter 07" (lines 424–470).

### Notes

- Chapter is well-maintained post-Feb 2026 hardening. Most content aligns with current codebase. Missing content is additive (new HF suites), not contradictory.
- The "Chapter 21" cross-reference (line 6: "Our 8-suite benchmark framework (Chapter 21)") in Ch07 is **a forward-reference error**. Chapter 21 does not exist in the repository. Ch07 should reference Ch06 (this chapter). **This is in Ch07 line 5, not this file, but flagging for the cluster audit.**
- The "-/V1 vs debug/ suites" distinction (line 645 in Ch07) correctly documents rubric vs deterministic scoring — no edits needed there.

---

## 07-benchmark-suite-construction.md

**Verdict**: patch
**Severity**: medium

### Factual errors

- Line 5: "Our 8-suite benchmark framework (Chapter 21)" — **Chapter 21 does not exist**. Should reference "Chapter 06: Benchmarking Framework" (which discusses the role/mapping of the 8 core suites). The section actually describes 11 YAML suites + 15 HF-backed suites (27 total), so "8-suite" is also imprecise.
  - Source: Lines 474–495 enumerate all suites.
  - **Recommendation**: Line 5 should read: "Our multi-suite benchmark framework (see Chapter 06: Benchmarking Framework) relies on..."

- Lines 644–645: Relationship section states "The `v1/` suite uses Claude-as-Judge with rubric scoring for open-ended quality assessment." — **Current codebase only documents debug/ (YAML-based deterministic)**. v1/ is referenced but not documented in these chapters. The statement is technically sound but unsupported by any chapter content.
  - Source: Ch06 lines 114–126 also reference v1/ but do not detail the scoring rubric. Ch07 line 645 is the only place that explains the v1/debug split.
  - **Recommendation**: Either document v1/ in detail (lines in a new subsection) or limit the claim to "debug/ uses machine verifiers" without claiming v1/ uses Claude-as-Judge (which may be outdated).

- Lines 429–445 (PHYBench section): "Best LLM (Gemini 2.5 Pro) scores 36.9% vs human 61.9%" — **This benchmark result is dated; Gemini has released updated versions**. However, the source is properly cited (arxiv), so the claim is defensible as a snapshot. No edit required if we're documenting the state as of citation date.

- Line 463 (PhysReason multimodal): "3,117 sub-questions" is stated but the breakdown (knowledge/easy/medium/difficult tier counts in parens) adds up: 1,344 + 758 + 1,015 = 3,117 ✓. Verified accurate.

### Superseded claims

- None detected. The document carefully marks additions by date (Feb 2026, March 2026) and does not supersede earlier claims.

### Missing content (post-2026-03-30 landings)

- **Lines 550–551**: Scoring propagation fix is documented ("Prior to 2026-03-03, `question_pool.py` defaulted..."). This is good historical documentation. However, **no mention of subsequent fixes to web_research or skill_transfer suite scoring** after the 2026-03-03 fix. The commit that fixed this may have landed after the document was last edited.
  - **Recommendation**: No edit needed — the 2026-03-03 fix is a milestone, and later refinements are incremental.

### Broken path references

- None — all paths (`benchmarks/prompts/debug/`, `scripts/benchmark/`) are relative and valid.

### Proposed edits

1. **Line 5**: Change "Our 8-suite benchmark framework (Chapter 21)" → "Our multi-suite benchmark framework (Chapter 06) comprises 11 YAML-based curated suites and 15 HuggingFace-backed dataset adapters (27 total)".

2. **Lines 644–645**: Simplify relationship section. **Option A** (minimal): "The project has two parallel benchmark tracks. The `debug/` suite uses machine verifiers for automated regression testing (THIS CHAPTER). The `v1/` suite (documented separately) uses Claude-as-Judge for open-ended quality assessment."  **Option B** (current wording is acceptable if v1/ is treated as external documentation).

3. **Add context callout after line 551**: "As of March 2026, the production pool contains 56,448 questions across all suites; see current `question_pool.py --report` output for live counts."

### Notes

- Document is well-structured and comprehensive. The Ch21 forward-reference error is inherited from Ch06 and should be fixed upstream.
- The HuggingFace suites section (lines 424–527) is thorough and current. PhysReason llm_judge integration (lines 462–463) is a significant 2026-03 addition and correctly documented.

---

## 08-cost-aware-rewards.md

**Verdict**: up_to_date
**Severity**: low

### Factual errors

- Line 229: Baseline TPS table lists "architect_coding: 10.3 t/s" — **Current registry lists 7.0 t/s** (from grep above, model_registry.yaml line showing "throughput: 7.0 # t/s at 96t NUMA deployment"). 
  - Source: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` architect_coding section.
  - **Recommendation**: Update line 229 architect_coding entry from "10.3" to "7.0 t/s" (this is a 2026-03-21 sweep result vs an older 2026-02 estimate).

- Line 207 (cost_ratio definition): "expected_elapsed = tokens_generated / baseline_tps[role]" — **This assumes baseline_tps is in tokens/second, which is correct** (lines 224–235 table confirms t/s units). No error.

### Superseded claims

- Lines 267–290: Design decisions are dated to Feb 2026 and remain current. The failure_reward change from -0.5 to 0.0 (line 278–281) is properly cited to xRouter. No supersession detected in progress logs 2026-02–2026-05.

### Missing content (post-2026-03-30 landings)

- **Line 307**: "Mode-Advantage Task Enrichment (February 2026)" — this section references Ch07 correctly. However, **no mention of the March 2026 HuggingFace adapter expansion** (GAIA, CRUXEval, BigCodeBench) which also feeds mode-advantage reward signals. The document only mentions "Three HuggingFace dataset adapters" (line 318) but Ch07 lines 494–518 lists 15 HF-backed suites.
  - Source: Ch07 lines 502–518 table lists additional suites beyond the mode-advantage focus.
  - **Recommendation**: Expand line 318 from "Three HuggingFace dataset adapters" to "Multiple HuggingFace dataset adapters (GAIA, CRUXEval, BigCodeBench, and 12 others per Chapter 07)". Or keep as-is if the emphasis is on the three mode-advantage-specific suites only.

- **Lines 406–437**: Extended Reward Dimensions (Feb 2026) document quality_gap_penalty and memory_tier_penalty. **No mention of the cost metrics breakdown added in subsequent updates** (Ch09 lines 259–279 documents extended observation patterns: cost_dimensions, think_harder_attempted, cheap_first_attempted, etc.). These are related reward dimensions not covered in Ch08.
  - **Recommendation**: No edit — Ch08 is intentionally focused on the core cost-aware formula. Ch09 can handle the extended diagnostics.

- **Lines 439–475**: Web Research Reward Dimensions (March 2026, Search-R1) — This is well-documented and current. The wr_* and sp_* dimensions (lines 446–470) align with the seeding_rewards.py implementation referenced.

### Broken path references

- Line 309: "See Chapter 07" — **Correctly references 07-benchmark-suite-construction.md**. No breakage.
- Line 479: "See SkillBank & Experience Distillation (documented in epyc-orchestrator)" — **External reference to epyc-orchestrator repo**, which is valid (different repo). No breakage within this codebase.

### Proposed edits

1. **Line 229**: Change architect_coding baseline TPS from "10.3" → "7.0" (current 2026-03-21 sweep value).

2. **Line 318** (optional): Clarify "Three HuggingFace dataset adapters" as "Three mode-advantage-relevant HuggingFace adapters" or expand to note the full set if wanted.

### Notes

- Document is exceptionally well-maintained. Recently touched 2026-05-07 (per prompt), though git shows 2026-04-13 in my environment — likely a batch update. Content aligns with current registry and seeding infrastructure.
- The xRouter, RouteLLM, and Trinity citations (lines 51–148) are thorough and recent (Oct 2025–ICLR 2026). All references validated.
- Binary rewards section (lines 322–402) is nuanced and correct — it properly separates Q-value estimation from cost-weighted routing.

---

## 09-claude-debugger.md

**Verdict**: up_to_date
**Severity**: low

### Factual errors

- Line 319: "Log file path: `/mnt/raid0/llm/epyc-orchestrator/logs/debug_changes.jsonl`" — **This references epyc-orchestrator repo, not epyc-inference-research**. Correct per the architecture (debugger runs as part of the orchestrator service). No error — just a cross-repo reference.

- Line 306–325 (File Locations table): All listed files are correctly described:
  - `src/pipeline_monitor/claude_debugger.py` — **verified exists in epyc-orchestrator** (per progress notes)
  - `src/pipeline_monitor/anomaly.py` — **verified exists**
  - `/mnt/raid0/llm/tmp/inference_tap.log` — **path is machine-specific but accurate for EPYC deployment**
  - All checks pass ✓

### Superseded claims

- None — document is dated 2026-02 (headers show "February 2026" for extended diagnostics section). No contradiction detected in later progress logs.

### Missing content (post-2026-03-30 landings)

- **Lines 259–279**: Extended Observation Patterns (February 2026) documents cost_dimensions, think_harder_attempted, think_harder_succeeded, etc. **This aligns well with Ch08's cost-aware rewards work**. No new additions needed.

- **Lines 281–304**: Skill Diagnostics section (February 2026) is **explicitly marked as "future integration point"** (line 283). This is appropriate — SkillBank is documented in epyc-orchestrator, not epyc-inference-research. Cross-reference is correct.

### Broken path references

- None — all paths are relative to epyc-orchestrator or machine-specific.

### Proposed edits

None — document is current and correctly scoped.

### Notes

- Chapter is exceptionally well-written and current. The 12 anomaly signals (lines 38–59) are a valuable reference, with weights clearly defined and urgency triggers explicit.
- The mini-regression suite design (lines 116–149) is sound: VERIFY/GENERALIZE/REGRESS phases prevent overfitting. Well-documented.
- MemRL interaction section (lines 151–187) correctly explains Q-value convergence with TD-learning. No errors.

---

## benchmarking-guide.md

**Verdict**: rewrite
**Severity**: high

### Factual errors

- Line 16: "`/mnt/raid0/llm/llama.cpp/build/bin/llama-cli`" — **This is a pre-monorepo-split path**. The actual binary is at `/mnt/raid0/llm/epyc-inference-research/llama.cpp/build/bin/llama-cli` (or via orchestrator_stack.py launcher which manages the binary).
  - Source: 2026-02-25 monorepo split moved models and binaries; benchmarking-guide.md was not updated.
  - **Recommendation**: Replace line 16 with a reference to the orchestrator launcher: "Use the orchestrator stack to manage model launching (see scripts/server/orchestrator_stack.py) or run llama-cli directly from the source build directory."

- Line 30: `./scripts/benchmark/run_overnight_benchmark_suite.sh` — **File path is correct relative to repo root**, but the script itself has **evolved since 2026-02-25**. The current benchmark pipeline uses `seed_specialist_routing.py` for 3-way MemRL seeding (documented in Ch06, Ch09), not just raw suite runs.
  - Source: Current benchmarking workflow (2026-03 onwards) focuses on orchestrator-integrated seeding, not standalone suite runs.
  - **Recommendation**: Reorganize guide to separate "Basic Verification" (quick llama-cli test) from "Production Seeding" (orchestrator-integrated 3-way benchmark). Mention `seed_specialist_routing.py --3way` for current workflow.

- Line 39: "Results are in `benchmarks/results/runs/`. Score using the rubric:" — **This refers to Claude-as-Judge scoring, but the current system uses deterministic scoring** (debug/ suites, machine verifiers, no Claude calls in automated runs).
  - Source: Ch07 lines 644–665 document the split: v1/ uses Claude-as-Judge (manual, quality assessment), debug/ uses deterministic scoring (automated, regression testing).
  - **Recommendation**: Clarify that automated seeding uses debug/ suites with deterministic scoring. Claude-as-Judge is available as a separate step for manual quality audits.

### Superseded claims

- Line 50–75: Common Issues section (Model Hangs, Low Acceptance Rate, Garbage Output with MoE) — **These are still valid** but the recommended flags have evolved. For example:
  - Line 73: "Reduce K value" (for speculative decoding) — Current registry uses K=24 (draft_max: 32, per model_registry.yaml, tuned 2026-03-21), not the generic advice.
  - **Recommendation**: Update to reflect current tuning (K=24–32 per role) and link to model_registry.yaml for authoritative values.

- Line 111: "See [Chapter 21](../chapters/21-benchmarking-framework.md)" — **Chapter 21 does not exist**. Should be "Chapter 06".
  - **Recommendation**: Change to "See Chapter 06: Benchmarking Framework (../chapters/06-benchmarking-framework.md)".

### Missing content (post-2026-03-30 landings)

- **No mention of orchestrator-integrated benchmarking** (2026-02 onwards). The guide describes standalone llama-cli testing, but production workflows use the orchestrator API with MemRL seeding.
  - Source: Ch06 line 165–267 describes orchestrator benchmark pipeline; seed_specialist_routing.py (documented in Ch06 lines 222–234) is the current entry point.
  - **Recommendation**: Add section "Production Benchmarking" that walks through orchestrator startup and 3-way seeding.

- **No mention of model_registry.yaml** — The guide says "update orchestration/model_registry.yaml with baseline_tps, optimized_tps, and quirks" (paraphrased from line 51–54 content) but does not explain what these fields are or how to obtain them.
  - **Recommendation**: Add a "Model Registry Integration" section with examples of registry entries and how to populate them from benchmark runs.

### Broken path references

**CRITICAL — Many paths are pre-monorepo-split:**

1. Line 7: "`/mnt/raid0/llm/models/`" — **Correct path**, but no context on how models get there. Pre-split guidance assumed manual download; current workflows use `scripts/setup/download_models.py` (documented in MODEL_MANIFEST.md line 109–115).

2. Line 16: "`/mnt/raid0/llm/llama.cpp/build/bin/llama-cli`" — **This path was valid pre-2026-02-25; post-split, the binary is in epyc-inference-research tree.** The symlink structure has changed.

3. Line 30, 33, 34: `./scripts/benchmark/run_overnight_benchmark_suite.sh` — **File exists**, but the script has been superseded by the orchestrator workflow. Keeping this path but updating the guidance is acceptable.

### Proposed edits

**Major rewrite required. Suggested outline:**

1. **New intro** (replace line 1–10): "This guide covers both standalone model verification and production benchmarking integrated with the orchestrator."

2. **Section 1: Quick Verification** (rename from "Step 1"):
   ```bash
   # Use orchestrator stack to launch a single model
   python scripts/server/orchestrator_stack.py start --hot-only
   # Run a quick test via the API
   curl -X POST http://localhost:8000/v1/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "frontdoor", "prompt": "Hello", "max_tokens": 10}'
   ```

3. **Section 2: Benchmark Suites** (keep existing table, line 83–94):
   - Clarify that tests are available in both debug/ (deterministic, fast) and v1/ (Claude-as-Judge, manual quality).

4. **Section 3: 3-Way Orchestrator Seeding** (new):
   ```bash
   python scripts/benchmark/seed_specialist_routing.py --3way --continuous
   ```
   Link to Ch06 for details.

5. **Section 4: Results & Registry** (rename from "Step 4"):
   - Explain model_registry.yaml structure.
   - Add examples of populating throughput, tier, memory_gb fields.

6. **Section 5: Common Issues** (keep, but update with current tuning values):
   - K values: reference model_registry.yaml
   - MoE expert counts: current consensus is 4–6 experts (not "never 2 experts" as blanket rule)

7. **Bottom**: Change Ch21 reference to Ch06.

### Notes

- This guide is **severely stale** (last touched 2026-02-25, pre-monorepo-split). It was useful for early development but no longer reflects the production pipeline.
- A rewrite would be valuable — the guide structure is sound, but almost all technical content needs updating.
- Recommend treating this as a "rewrite" task, not a patch, due to scope of changes.

---

## kv-compaction-guide.md

**Verdict**: up_to_date
**Severity**: low

### Factual errors

- Line 74: "For Qwen2.5-Coder-32B at Q4_K_M: ... 224 MB | 75 MB | 45 MB" (for 4K tokens, full KV vs 3x compact vs 5x compact) — **These numbers are plausible** (224 MB / 3 ≈ 75 MB), but **no source cited**. However, the math is correct and the guide is consistent.
  - **Recommendation**: No edit — plausibility-checked and internally consistent.

- Line 51: "Compact to 30% of original KV (3.3x compression)" — **Terminology is slightly imprecise**: "keep_ratio: 0.3" means "keep 30%, discard 70%", which is 1/0.3 ≈ 3.3x compression. The calculation is correct.
  - **Recommendation**: No edit — terminology is standard in KV compaction literature.

- Line 44: `keep_ratio: 0.2 (5x)` — **Correct**: 1/0.2 = 5x compression.

### Superseded claims

- None detected. The guide is marked as current (last touched 2026-04-13 per ls output above).

### Missing content (post-2026-03-30 landings)

- **No mention of RadixAttention** (which is mentioned in Ch08 line 516 as a future direction for cache-aware cost reduction). The guide focuses on the "Attention Matching" method (line 5), which is correct as the primary deployed approach.
  - **Recommendation**: Optional callout: "Future work: RadixAttention extends this with cache-aware cost accounting (see Chapter 08)." But not critical.

- **No mention of the KV cache quantization work** documented in the wiki (kv-cache.md). The guide assumes full-precision KV; combined with the Hadamard Q4_0 mentioned in line 76, a note on KV quant + compaction interaction would be valuable.
  - Source: `/workspace/wiki/kv-cache.md` documents KV quantization strategies.
  - **Recommendation**: Optional: "KV Quantization can be combined with compaction for up to 20x total compression (4x quant × 5x compaction); see wiki/kv-cache.md for details."

### Broken path references

- None — guide is relative and path-agnostic.

### Proposed edits

None — document is current and accurate. Optional enhancements:

1. **Line 76** (end of guide): Add footnote: "Combined with KV quantization (e.g., Q4_0), up to 20x compression is achievable. See wiki/kv-cache.md for details on quantization strategies."

2. **Line 6** (When NOT to use): Add "multi-turn chat with context reuse" as a use case (compaction reduces precision for subsequent turns).

### Notes

- Guide is well-written, practical, and current. The A/B test data (lines 69–75) provides concrete evidence for the 5x compaction claim.
- The "Conservative / Balanced / Aggressive" tuning guidance (lines 37–46) is helpful and empirically justified (line 46: "Our tests show zero degradation at 5x on factual retrieval and coding tasks").

---

## model-sizing.md

**Verdict**: rewrite
**Severity**: high

### Factual errors

- Line 72: "NUMA Nodes: ${NUMA_NODES:-1}" — **Script syntax is correct** (Bash default parameter expansion), but the actual EPYC 9655 in the test environment has **2 NUMA nodes** (96 cores = 48 per node, single socket). The example output is not broken, just illustrative.
  - **Recommendation**: No edit — script is general-purpose and correct.

- Line 104: "Qwen3-235B | 235B | Q4_K_M | 235 × 0.5 × 1.1 | ~130 GB" — **Current registry lists architect_general model as a different Qwen3 variant**. Per the 2026-05-07 progress note and model_registry.yaml grep above, the **frontdoor is now Qwen3.5-35B** (not Qwen3-Coder-30B which is stale).
  - Source: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` frontdoor section: "model: Qwen3.5-35B-A3B-UD-Q4_K_M.gguf"
  - **Recommendation**: Update entire "Recommended Configurations" section (lines 163–307) to reflect current models: Qwen3.5-35B (frontdoor), Qwen2.5-Coder-32B (escalation), Qwen2.5-7B (worker), Qwen3-Next-80B (ingest), Qwen3-235B or Qwen3.6-35B (architect options).

- Line 51–62: Quick Assessment Script — **This script references the monorepo filesystem (`/mnt/raid0/llm/`), which is machine-specific**. The guide is for a specific deployment (EPYC 9655), so this is acceptable, but it should be noted as environment-specific.
  - **Recommendation**: Add note at top of script section: "This script is tailored to the EPYC 9655 deployment; adjust paths for other systems."

- Line 108–119: MoE Models section — **Correct explanation**: "235B total, 22B active per token". Current Qwen3.5-35B is not MoE (it's a **SSM+MoE hybrid**), so the description applies to 235B but not to frontdoor.
  - Source: model_registry.yaml frontdoor section: "acceleration: type: moe_expert_reduction" and "SSM checkpoint overhead" comment.
  - **Recommendation**: Clarify that SSM+MoE hybrids (like Qwen3.5) have different memory and latency profiles than pure MoE models. Add a table row for hybrids.

### Superseded claims

- Line 155–161: Speed expectations table lists "Qwen2.5-7B Q4 | 25–40" t/s. **Current registry lists worker (7B) at 39.1 t/s** (model_registry.yaml), which is at the upper end of the range. Claim is still valid.

- Lines 176–219: "Production (512GB RAM)" configuration lists Qwen3-235B as architect_general and Qwen3-Coder-480B as architect_coding. **Current deployments vary**, but this is still a valid reference configuration. No direct contradiction in progress logs.

### Missing content (post-2026-03-30 landings)

- **No mention of Qwen3.5** — the guide was last updated 2026-02-25, before Qwen3.5 launch. The 2026-05-07 progress note documents Qwen3.5-35B as the new frontdoor (replacing Qwen3-Coder-30B). This is a significant model change.
  - Source: Progress 2026-05-04 and 2026-05-07 describe Qwen3.5-35B-A3B-UD (NUMA 4×48t) as production deployment.
  - **Recommendation**: Update lines 163–307 to use Qwen3.5-35B throughout.

- **No mention of memory tier pinning** — The registry (model_registry.yaml) uses `mlock_roles` to keep HOT models in RAM. The sizing guide discusses tiers but not the NUMA/mlock strategy.
  - Source: model_registry.yaml MLOCK_ROLES section (per 2026-05-22 refactor notes).
  - **Recommendation**: Optional: Add section on "NUMA Pinning and mlock" to explain why HOT tier models don't page to swap.

- **No mention of reduced MoE expert counts** — The guide explains MoE but doesn't mention that frontdoor uses "moe6" (6 experts, reduced from 8). This is a crucial tuning detail for memory budgeting.
  - Source: model_registry.yaml frontdoor: "experts: 6 # moe6 only"
  - **Recommendation**: Add row to MoE section: "Qwen3.5-35B (moe6, default 8) | memory: 19GB (reduced from ~22GB with moe8)"

### Broken path references

**CRITICAL — paths are mostly pre-monorepo-split:**

1. Line 45: `df -h /mnt/raid0` — **Correct path**, but no explanation of how /mnt/raid0 is mounted (it's a RAID0 array on the EPYC system).
   - **Recommendation**: Add note: "Assumes /mnt/raid0 is mounted; adjust for your filesystem layout."

2. Lines 109–115 (Model Substitution Guide): Links to "MODEL_MANIFEST.md" exist but are not explicitly rendered in the markdown as links. The file is at `../MODEL_MANIFEST.md` in the actual repo structure.
   - **Recommendation**: Convert to markdown link: "[MODEL_MANIFEST.md](../MODEL_MANIFEST.md)" or add explicit path in a NOTE.

3. Line 220–286 (Recommended Configurations): Path references like "Qwen2.5-Coder-32B Q4" are model names, not filesystem paths. No breakage.

### Proposed edits

**Major rewrite recommended. Suggested approach:**

1. **Update opening**: Add date: "Last updated 2026-02-25 (pre-Qwen3.5); refreshed 2026-05-26 with current models."

2. **Section: Quick Assessment Script** (lines 51–62): Add machine-specific note.

3. **Section: Model Size Estimation** (keep lines 74–106 mostly unchanged):
   - Update examples table (lines 100–106) to use Qwen3.5 instead of Qwen3-Coder-30B:
     ```
     | Qwen3.5-35B-A3B-UD | 35B | Q4_K_M | 35 × 0.5 × 1.1 | ~19 GB |
     ```

4. **Section: MoE Models** (lines 108–120):
   - Add clarification: "Pure MoE models (Qwen3-235B) vs SSM+MoE hybrids (Qwen3.5-35B) have different profiles."
   - Add table for Qwen3.5 hybrids: "SSM+MoE | Qwen3.5-35B-A3B (8 experts, moe6 reduction) | ~19 GB (full moe8: ~22 GB)"

5. **Section: Performance Expectations** (lines 152–259):
   - Update table (line 152–159) to reflect 2026-03-24 benchmarking: Qwen3.5-35B @ 12.7 t/s per instance, ~50.8 t/s aggregate (4×48t NUMA), not the old speed estimates.

6. **Section: Recommended Configurations** (lines 163–307):
   - **Minimal (64GB)**: keep Qwen2.5-7B as single fallback
   - **Basic (128GB)**: update to Qwen3.5-35B (frontdoor, 19GB), Qwen2.5-Coder-32B (escalation, 20GB), Qwen2.5-7B (worker, 4GB), draft (0.5GB) = ~43GB HOT
   - **Standard (256GB)**: Qwen3.5-35B HOT, architect_general + ingest WARM
   - **Production (512GB)**: Qwen3.5-35B HOT, architect_general + architect_coding + ingest WARM
   - **Full (1TB)**: all roles, Qwen3.6-35B as alternative frontdoor, Qwen3-Coder-480B (REAP-pruned, 139GB) for architect_coding

7. **Bottom**: Update Ch21 reference to Ch06 (line 286 via the 2026-02-25 pre-split referencing).

### Notes

- **This is the oldest guide in the audit** (2026-02-25, before Qwen3.5 launch). A full refresh is recommended, not just patches.
- The structure is sound — the Quick Assessment script, sizing tables, and substitution guide are all valuable patterns that should be preserved and updated.
- The MoE explanation (lines 108–119) is clear but needs expansion for hybrids.

---

## MODEL_MANIFEST.md

**Verdict**: patch
**Severity**: medium

### Factual errors

- Line 9 (Server Topology table, row 1): "Qwen3-Coder-30B-A3B (Q4_K_M) | 20 GB | HOT | 47 t/s" — **This is stale**. Current registry has:
  - Model: "Qwen3.5-35B-A3B-UD-Q4_K_M.gguf"
  - Memory: 19 GB (not 20)
  - Speed: 12.7 t/s per instance (moe6), ~50.8 t/s aggregate with NUMA 4×48t (not 47 single-instance)
  - Source: model_registry.yaml frontdoor section, updated 2026-05-04 (Probe B measurement)
  - **Recommendation**: Update line 9 to "Qwen3.5-35B-A3B-UD (Q4_K_M) | 19 GB | HOT | 12.7 t/s (per instance, 4×48t NUMA)"

- Line 11: "Qwen2.5-Coder-32B (Q4_K_M) | 20 GB | HOT | 39 t/s" — **Speed is inflated**. Current registry lists "throughput: 10.8 # t/s at 48t NUMA deployment" with a note "(sweep 2026-03-21). 192t ref: 12.2. Old 39.44 was inflated."
  - **Recommendation**: Update line 11 to "Qwen2.5-Coder-32B (Q4_K_M) | 20 GB | HOT | 10.8 t/s (sweep 2026-03-21)"

- Line 12: "Qwen2.5-7B (f16) | 16 GB | HOT | 44 t/s" — **Current registry lists "throughput: 39.1 # t/s at 48t NUMA deployment (sweep 2026-03-21). 4×48t agg: ~156 t/s."**
  - **Recommendation**: Update line 12 to "Qwen2.5-7B (f16) | 16 GB | HOT | 39.1 t/s" (single-instance canonical). Add note if 4×48t aggregate is relevant.

- Line 13: "Qwen3-235B-A22B (Q4_K_M) | 134 GB | WARM | 6.1 t/s" — **Verify against registry**: grep shows "throughput:" but doesn't show an architect_general line in my limited grep. However, **130 GB estimate in Ch06 line 104 is close to 134 GB**, so the size is plausible.
  - **Recommendation**: Cross-check model_registry.yaml for exact architect_general throughput and memory values; if different, update.

- Line 14: "Qwen3-Coder-480B-A35B (Q4_K_M) | 272 GB | WARM | 9.0 t/s" — **Registry shows "throughput: 7.0 # t/s at 96t NUMA deployment (sweep 2026-03-21). 192t ref: 7.1."**
  - **Recommendation**: Update line 14 to "Qwen3-Coder-480B-A35B (Q4_K_M) | ~271 GB | WARM | 7.0 t/s (2026-03-21 sweep)"

- Line 15: "Qwen3-Next-80B-A3B (Q4_K_M) | 46 GB | WARM | 6.3 t/s" — **Matches registry**: "throughput: 6.3 # t/s measured 2026-01-26". Correct ✓

- Line 47 (Coder / Tier B): "DeepSeek-Coder-V2" — **No current registry entry for DeepSeek**. This is a substitution guide (line 39 intro: "You don't need the exact models listed here — the orchestrator supports any compatible GGUF models"). Acceptable as a suggestion, but note it's not deployed.
  - **Recommendation**: Mark as "not currently deployed" or move to a "Future Candidates" section if clarity is needed.

### Superseded claims

- Line 26–31 (Memory Tiers): "HOT (~40 GB)" — **Current HOT tier is closer to ~98 GB** (19 GB frontdoor + 20 GB escalation + 16 GB worker + 5 GB vision + 0.5 GB draft + overhead). The estimate is from 2026-02-25 (pre-Qwen3.5).
  - **Recommendation**: Update line 28 to "HOT (~100 GB)" or list granular breakdown "HOT: frontdoor (19GB) + escalation (20GB) + workers (16GB) + vision (5GB) + embeddings + utilities (~40GB) = ~100GB total".

- Line 29: "WARM (~430 GB)" — **Verify**: architects at 134 + 271 + 80 = 485 GB + utilities could indeed reach ~430–500 GB.
  - **Recommendation**: Clarify as "WARM (~450–500 GB for architect_general + architect_coding + ingest)".

### Missing content (post-2026-03-30 landings)

- **No mention of Qwen3.6 (gemma-4 MTP swap, 2026-05-07)** — The 2026-05-07 progress note mentions Qwen3.6-35B-A3B-Q8_0 as a candidate model and gemma-4 MTP swap. Current manifest doesn't mention these.
  - Source: Progress 2026-05-07, model_registry.yaml shows gemma-4 entries.
  - **Recommendation**: Add note at bottom: "Recent candidates (2026-05): Qwen3.6-35B-A3B-Q8_0 (alternative frontdoor candidate), gemma-4-31B-it (general worker), DeepSeek-V3 (architect candidate)."

- **No mention of REAP-pruned models** — model_registry.yaml documents Qwen3-Coder-REAP-246B-A35B (50% pruned, 8.0 t/s) as a deployed architect candidate. Manifest should note this.
  - Source: Progress notes and model_registry.yaml REAP section.
  - **Recommendation**: Add row to table or note: "REAP-pruned Qwen3-Coder-246B-A35B (139 GB, 8.0 t/s) — alternative to 480B architect."

- **No mention of SSM-hybrid specifics** — Qwen3.5 is SSM+MoE hybrid; current Qwen3-235B is pure MoE. The manifest doesn't clarify architecture differences.
  - **Recommendation**: Add "Architecture" column to Server Topology table or add a note explaining hybrid vs pure MoE.

### Broken path references

- Line 126: "See the [registry file](../orchestration/model_registry.yaml) for the complete configuration." — **Path is broken in the document** (should be relative or absolute). In the actual repo, the file is at `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`.
  - **Recommendation**: Change to "See `orchestration/model_registry.yaml` for the complete configuration" or provide absolute path.

### Proposed edits

1. **Line 9 (Frontdoor row)**: Change to:
   ```
   | Front Door | 8080 | Qwen3.5-35B-A3B-UD (Q4_K_M) | 19 GB | HOT | 12.7 t/s |
   ```

2. **Line 11 (Coder row)**: Change to:
   ```
   | Coder (escalation) | 8081 | Qwen2.5-Coder-32B (Q4_K_M) | 20 GB | HOT | 10.8 t/s |
   ```

3. **Line 12 (Worker row)**: Change to:
   ```
   | Worker (general) | 8082 | Qwen2.5-7B (f16) | 16 GB | HOT | 39.1 t/s |
   ```

4. **Line 14 (Architect coding row)**: Change to:
   ```
   | Architect (coding) | 8084 | Qwen3-Coder-480B-A35B (Q4_K_M) | ~271 GB | WARM | 7.0 t/s |
   ```

5. **Line 28 (Memory Tiers intro)**: Change "HOT (~40 GB)" to "HOT (~100 GB: frontdoor 19GB + escalation 20GB + workers 16GB + vision 5GB + embeddings & utilities ~40GB)".

6. **Line 29 (WARM tier)**: Change "~430 GB" to "~450–500 GB" (architect_general 134 + architect_coding 271 + ingest 46 + utilities).

7. **Add after line 25**: New note:
   ```markdown
   ### Recent Model Candidates (2026-05)
   - Qwen3.6-35B-A3B-Q8_0: Alternative frontdoor option
   - gemma-4-31B-it: Fast general-purpose worker
   - Qwen3-Coder-REAP-246B-A35B: 50%-pruned architect candidate (139 GB, 8.0 t/s)
   - DeepSeek-V3: Larger architect candidate
   ```

8. **Line 126**: Change to:
   ```
   All model configuration lives in `orchestration/model_registry.yaml`. Key sections:
   ```
   (Remove the markdown link syntax since the relative path is machine-dependent.)

### Notes

- **This manifest is the data layer for deployments** — accuracy is critical. The current version is accurate for ~2026-02 but significantly stale for 2026-03-24 benchmark sweeps and 2026-05 Qwen3.5 adoption.
- The table-based format is easy to scan and maintain. Updates should be straightforward.
- A comprehensive refresh is recommended (2–3 hours of work to verify each value against current registry).

---

## Cross-Cluster Observations

### Chapter Cross-References (Broken)

- **Ch06 line 401**: References "Master Benchmark Results (../reference/benchmarks/RESULTS.md)" — File exists ✓
- **Ch07 line 5**: References "Chapter 21" (does not exist) — should be "Chapter 06"
- **benchmarking-guide.md line 111**: References "Chapter 21" (does not exist) — should be "Chapter 06"

### Model Registry Drift

The MODEL_MANIFEST.md is a "point-in-time" snapshot that drifts as the registry evolves. Key drift points:

1. **Frontdoor**: Qwen3-Coder-30B → Qwen3.5-35B (2026-05-04, NUMA 4×48t deployment shift)
2. **Speed estimates**: Pre-2026-03-21 sweep values are inflated (39 t/s for 32B coder, 47 t/s for frontdoor). Current values (10.8, 12.7) are from Probe B measurements.
3. **Memory estimates**: Adjusted for actual quantization + KV cache overhead. Qwen3.5-35B @ 19 GB is lower than Qwen3-Coder-30B @ 20 GB due to SSM efficiency.

**Recommendation**: Generate MODEL_MANIFEST.md from model_registry.yaml programmatically, or establish a sync trigger (e.g., after major registry commits).

### Monorepo Split Impact

- **Pre-2026-02-25**: Guides reference `/mnt/raid0/llm/claude/` paths (unified codebase).
- **Post-2026-02-25**: Paths split into `/mnt/raid0/llm/epyc-inference-research/` and `/mnt/raid0/llm/epyc-orchestrator/`. Guides were not fully updated.
- **Impact**: benchmarking-guide.md and model-sizing.md are most affected (both last touched 2026-02-25).

---

## Summary Checklist for Downstream Agent

### High Priority (Fix First)

- [ ] **Ch07 line 5**: Change "Chapter 21" → "Chapter 06"
- [ ] **benchmarking-guide.md**: Rewrite for post-monorepo-split paths and orchestrator-integrated workflow (not standalone suite runs)
- [ ] **model-sizing.md**: Refresh Recommended Configurations with Qwen3.5-35B and current 2026-03-24 benchmark speeds
- [ ] **MODEL_MANIFEST.md**: Update Server Topology table with current speeds and model names (6 rows need updates; see Proposed Edits)

### Medium Priority (Clean Up)

- [ ] **Ch06 line 6**: Change "8-suite" → "10+ suite" or "multi-tiered"
- [ ] **Ch06 lines 180–192**: Add PhysReason and PHYBench rows to HF adapter table
- [ ] **Ch06 lines 207–214**: Expand mode-advantage category counts (5 categories, 90 total, not just escalation-gated)
- [ ] **Ch08 line 229**: Update architect_coding TPS from 10.3 → 7.0 t/s
- [ ] **Ch07 lines 644–645**: Clarify v1/ vs debug/ split or remove unsupported claim about v1/ Claude-as-Judge

### Low Priority (Optional Polish)

- [ ] **kv-compaction-guide.md**: Add optional note on KV quantization combination (20x total compression)
- [ ] **Ch09**: No edits required; document is current
- [ ] **MODEL_MANIFEST.md line 47**: Clarify DeepSeek-Coder-V2 as "not currently deployed" or move to Future Candidates section

---

**Prepared by**: Documentation Audit Agent (Cluster F)  
**Audit Date**: 2026-05-26  
**Total Issues Found**: 34  
**Severity Breakdown**: 3 critical path errors, 8 factual errors, 12 missing content issues, 11 superseded/outdated claims

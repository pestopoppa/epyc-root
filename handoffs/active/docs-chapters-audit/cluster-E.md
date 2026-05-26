# Cluster E Audit: Speculative Decoding & MoE Optimization Chapters

**Audit Date**: 2026-05-26  
**Chapters Audited**: 6 (01, 02, 03, 04, 05, 10)  
**Comparison Baseline**: Wiki compiled 2026-04-30; Recent progress 2026-05-04 → 2026-05-26; Completed handoffs post-2026-03-30

---

## 01-speculative-decoding.md

**Verdict**: patch  
**Severity**: medium

### Factual errors

- Line 35–41 (performance table): **Qwen2.5-Coder-32B** is marked as target in all rows. **CORRECTION**: As of 2026-05-08, Qwen2.5-Coder-32B was replaced in production by **Gemma 4-26B-A4B-Q4_K_M** (worker_general role). The table should be updated or contextualized as "legacy baseline" to avoid confusion. Source: `/workspace/progress/2026-05/2026-05-08.md`, `/workspace/wiki/speculative-decoding.md` § "Production deployment landed (2026-05-08)"

- Line 184–194 (Qwen3-Coder-480B-A35B section): Claims "Standard Qwen3 drafts: 0% acceptance (BOS mismatch)" and references jukofyork vocab-transplant draft. **STATUS CHECK**: This approach is not reflected in recent production registry or any 2026-04+ handoff. The MTP-1 handoff (closed) and subsequent Gemma4 MTP evaluations use different draft architectures. Chapter should clarify whether this is still a tested approach or legacy content. Source: `/workspace/handoffs/completed/gemma4-mtp-drafter-evaluation.md` (2026-05-08)

- Line 29 (11x speedup claim): Chapter frames this as "headline numbers" but subsequent wiki/progress makes clear this applies to **Qwen2.5-Coder-32B + 0.5B draft in 2025 baseline**. On EPYC with current production (Gemma4-26B-A4B MTP), speedup is **only 1.06x** due to MoE batch=1 cancellation. The chapter should qualify the scope. Source: `/workspace/progress/2026-05/2026-05-08.md` § "Measured on EPYC 9655"

- Line 145–146 (SSM Architecture Incompatibility): "Use expert reduction only for these models." **CRITICAL UPDATE**: This is now SUPERSEDED. The 2026-04-30 wiki and completed handoff `hybrid-ssm-slot-promotion-spec-dec.md` document that while slot-promotion speculation failed (net-negative on Qwen3.6-35B), **prompt lookup with auto freeze-recurrent now works** on SSM-hybrid models. Line 68 of 02-moe-optimization.md correctly documents this, but Chapter 01 should be updated for consistency. Source: `/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md`; `/workspace/wiki/speculative-decoding.md` § "Frozen multi-path verification"

### Superseded claims

- **Entire "Best Results" table (lines 26–42)**: These are 2026-02-13 dated benchmarks. Subsequent research (2026-04 → 2026-05) has produced **drastically different numbers**. The wiki synthesis (compiled 2026-04-30) reports:
  - **DFlash on Qwen3.5 (GPU)**: 6.49 accepted tokens per round (not in table)
  - **DFlash on Qwen3.5 (CPU, Q4_K_M)**: 27% per-token acceptance, **net-negative** vs autoregressive (concluded not viable)
  - **External 0.75B draft on Qwen3-32B dense (CPU)**: **+55%** throughput
  - **Tree speculation on 32B f16 (CPU)**: +15.8%
  - **NUMA 4-way parallel serving**: **6–7x aggregate**, primary acceleration lever (not speculation)
  
  The chapter's table does not reflect any of these 2026-04+ findings. Recommend: either update table with April-May data, or explicitly scope as "2026-02 baseline measurements; see wiki § Key Findings for 2026-04+ results". Source: `/workspace/wiki/speculative-decoding.md` § "Key Findings"

- **K-Value Optimization section (lines 44–83)**: Assumes linear speculation (single draft sequence). The wiki has **superseded** this with the observation that **tree speculation + NUMA parallelism** fundamentally changes the K-tuning landscape. Chapter 10 (lines 6–129) extensively documents why single-sequence K=16–24 is no longer optimal for EPYC — tree branching with 4-way NUMA can achieve 8–12 accepted tokens per cycle vs 4–6 for linear. Recommend: add a forward reference to Chapter 10 or add a "Revised 2026-04+" sidebar. Source: `/workspace/repos/epyc-inference-research/docs/chapters/10-advanced-speculative-decoding.md` § "The SpecExec Insight"

- **Temperature Tuning Discovery (lines 85–100)**: The findings (temp=0.7 helps Qwen2.5-VL-7B, neutral for Coder-32B) are based on 2025 baseline. Recent experiments (2026-05) on Gemma4 and REAP models found **temperature tuning to be orthogonal to MTP/draft selection** — the interaction is more complex. Chapter should note this is model-family-specific and may not generalize. Source: `/workspace/progress/2026-05/2026-05-08.md`

### Missing content (post-2026-03-30 landings)

- **Gemma4 MTP drafters (May 2026)**: No mention. Gemma 4-26B-A4B MTP is now the production worker_general model with 2.98x speedup on dense (Gemma4 31B) and 1.06x on MoE (26B-A4B). This is the primary speculative decoding deployment on EPYC. Chapter should include a new "Gemma4 MTP Results" section or "Production Update (May 2026)". Source: `/workspace/progress/2026-05/2026-05-08.md`, `/workspace/wiki/speculative-decoding.md` § "Gemma 4 MTP Drafter"

- **DFlash block diffusion (Feb 2026)**: Mentioned in later chapters but not in Chapter 01. DFlash is the current frontier technique (O(1) draft cost vs O(N) for autoregressive). Chapter should add to the "Foundational Papers" reference section. Source: `/workspace/handoffs/completed/dflash-block-diffusion-speculation.md`

- **REAP-pruned models**: Chapter does not mention that pure-MoE models (REAP-25B, REAP-246B) re-enable speculation viability on what would otherwise be hybrid-SSM targets. This is a production-relevant fact. Source: `/workspace/wiki/speculative-decoding.md` § "REAP-pruned models are speculation-compatible"

- **Verification wall on hybrid SSM models (critical 2026 finding)**: While line 145 mentions "SSM architectures maintain recurrent state," the chapter does NOT quantify the cost. The wiki synthesis and multiple 2026 handoffs document that **multi-token verification on Qwen3.5 costs approximately N times single-token decode** because 75% of layers are sequential recurrent. This resulted in **0.56x throughput with MTP-1 at batch=2**. This is a fundamental architectural finding that should be highlighted earlier. Source: `/workspace/wiki/speculative-decoding.md` § "Verification wall"; `/workspace/handoffs/completed/mtp-speculative-decoding.md`

### Broken path references

- Line 171 (example server): `/mnt/raid0/llm/llama.cpp/build/bin/llama-speculative` — This binary name/path is from 2025. Current deployment uses `llama-server` (event-based API) not `llama-speculative` (CLI). The command structure is significantly different. Recommend: update to current registry-driven launch pattern or mark as "legacy CLI example". Source: `/workspace/progress/2026-05/2026-05-08.md` § orchestrator launch params

### Proposed edits

1. **Add sidebar after line 26** (before performance table): "**Note**: Table reflects 2026-02 baseline. For 2026-04+ production results on EPYC (Gemma4 MTP, DFlash, REAP models), see [Chapter 10: Advanced Speculative Decoding](10-advanced-speculative-decoding.md) and the production wiki entry on [speculative decoding](../wiki/speculative-decoding.md)."

2. **Replace line 145–146** with: "SSM-hybrid architectures (Qwen3.5, Qwen3-Next) face a **verification wall**: multi-token verification costs approximately N times a single-token decode because 75% of layers are sequential recurrent. External speculative decoding is not viable (0.56x throughput at batch=2 with MTP-1). However, **prompt lookup now works via auto freeze-recurrent** (validated 2026-03-10), achieving +30–42% throughput with ~13pp acceptance drop. Use expert reduction (Track 2) or prompt lookup as the primary optimization for these models."

3. **Add new section after line 196** under references: "## Production Update (May 2026) — Gemma4 MTP & REAP Models" with bullet points on Gemma4-26B-A4B 1.06x (MoE batch=1), Gemma4-31B dense 2.98x, and REAP-25B pure-MoE enabling speculation.

4. **Update line 171 command example** to note it is from 2025 codebase, or replace with modern `llama-server` API example with slot IDs and registry YAML override keys.

### Notes

- Chapter 01 is factually correct for its 2026-02-13 dating, but the field has moved significantly. The tension is between preserving historical context (valuable for understanding the progression) and accuracy for readers using this for production deployment.
- The chapter reads as "foundational pedagogy" rather than "production guide," which is appropriate — but the introductory claim that this is "our primary optimization technique" (line 4) is now inaccurate. NUMA 4-way parallel serving delivers 6–7x throughput vs +17–21% from spec-dec tuning on top of that. Recommend adding a "Current Status (May 2026)" callout at the top.
- The Qwen3-Coder-480B-A35B section (lines 180–194) references a jukofyork vocab-transplant draft that is not in the current registry or any active investigation. This should be either removed or explicitly marked as "experimental / not in production."

---

## 02-moe-optimization.md

**Verdict**: up_to_date  
**Severity**: low

### Factual errors

None detected. The chapter correctly documents:
- Expert reduction speedup range (21–52%) aligns with 2026-04 measurements
- SSM-safe expert reduction + prompt lookup (line 68) correctly reflects current implementation
- Override key names match current registry format

### Superseded claims

None identified.

### Missing content (post-2026-03-30 landings)

- **REAP expert pruning results**: The chapter does not mention REAP-25B (15GB, pure MoE, dm=24 at 39.62 t/s) or REAP-246B (pure MoE enabling speculation). These are production-deployed models that directly exemplify the MoE techniques. Source: `/workspace/wiki/speculative-decoding.md` § "REAP-pruned models are speculation-compatible"; `/workspace/handoffs/completed/reap-moe-expert-pruning.md`

- **MoE-Spec verification-budget mechanism (April 2026)**: A new orthogonal optimization (independent expert union reduction during verification batches) was prototyped in April 2026 with +15.2% on REAP-246B forward-pass. This is mentioned in the wiki but not in Chapter 02, which predates this work. Add a "Advanced: Verification-Budget Mechanisms" subsection or defer to Chapter 10. Source: `/workspace/wiki/speculative-decoding.md` § "MoE-Spec verification-budget mechanism gate MET"

### Broken path references

None detected.

### Proposed edits

1. **Add sidebar after line 34** (end of "Best Results"): "**Production Update (May 2026)**: REAP-25B (pure MoE, 15GB) deployed at dm=24 achieves 39.62 t/s (+101% vs baseline), validating MoE expert reduction on pruned models. See [wiki § REAP-pruned models](../wiki/speculative-decoding.md) for integration path."

2. **Optionally add** a "Future Directions" paragraph at the end (before references) noting MoE-Spec verification-budget mechanism (4–15% additional gains on batched verification). Link to Chapter 10 or defer to future revision.

### Notes

- This chapter is the most current and complete of the six audited. It correctly documents SSM-safe expert reduction and auto freeze-recurrent prompt lookup. No urgent fixes required.
- The omission of REAP results is a gap but not an error — REAP was deployed after Chapter 02 was last updated (2026-04-24). Add one sidebar and call it done.

---

## 03-prompt-lookup.md

**Verdict**: patch  
**Severity**: medium

### Factual errors

- Line 34–40 (speed measurements table): The Qwen3-Next-80B entry shows "95.18 t/s" with "12.7x speedup" from baseline 7.5 t/s. **VERIFICATION**: The wiki (speculative-decoding.md § Key Findings) and multiple 2026-03+ handoffs document that **prompt lookup on SSM-hybrid models triggers auto freeze-recurrent, which degrades acceptance ~13pp**. The 12.7x claim appears to assume full acceptance on this architectural class, which contradicts the documented 13pp degradation. Recommend: either cite the acceptance drop or verify the measurement was on a dense model, not Qwen3-Next. Source: `/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md`; `/workspace/wiki/speculative-decoding.md` § "SSM Compatibility"

- Line 68 (DySpec reference "arXiv:2410.11744"): **VERIFY**: This appears to be a real arXiv ID for DySpec, but Chapter 10 (line 62–72) discusses DySpec and states it was available by WWW 2025. Timeline is plausible but should be verified against the actual paper date. This is low-severity if the reference is correct.

### Superseded claims

- **Line 87 (compatibility matrix, "39.44 t/s on Qwen2.5-Coder-32B")**:  This is a 2026-02 baseline. Current production uses **Gemma4-26B-A4B** at higher absolute throughput (~76 t/s measured production, ~44 t/s benchmark per /workspace/progress/2026-05/2026-05-08.md). The table should note "2026-02 baseline; current production models achieve higher baselines." Source: `/workspace/progress/2026-05/2026-05-08.md`

### Missing content (post-2026-03-30 landings)

- **Corpus-Augmented Lookup v3 results (Feb 2026)**: Lines 226–242 document V3 full corpus performance (+16.3% on Coder-30B, +72.3% on 32B). These are 2026-02 results and are current, but Chapter should note that subsequent MoE-Spec and REAP experiments (April–May 2026) supersede these benchmarks in terms of what's in production. Current production uses Gemma4 (which has its own retrieval mechanisms). Source: `/workspace/wiki/speculative-decoding.md`

- **Nemotron-Labs-Diffusion (May 2026)**: A new architecture released 2026-05-19 with 5.46 accepted tokens per cycle (better than EAGLE-3 / MTP on some tasks) and unified self-speculation. No mention. This is frontier research, not production-critical, but worth citing as an advance in the speculative decoding landscape. Source: `/workspace/wiki/speculative-decoding.md` § "Unified-model self-speculation (Nemotron-Labs-Diffusion)"

- **Prompt lookup + auto freeze-recurrent on SSM-hybrid (March 2026)**: Lines 119–121 document this feature, but the acceptance drop (~13pp) should be quantified and cited. Current handoff documentation specifies this precisely. Source: `/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md`

### Broken path references

- Line 156–160 (Phase 2B references): References to "Phase 2B-Sidecar" and "Phase 2B-Quality RAG" are internal section references. These sections exist in the chapter but are marked as "CLOSED" — the chapter structure is fine, but readers may be confused by the "CLOSED" status. Consider moving these to an "Archived Approaches" section or clarifying their status in the introduction.

### Proposed edits

1. **Update line 34–40 table** with a footnote on SSM-hybrid models: "Qwen3-Next-80B with prompt lookup uses auto freeze-recurrent (enabled 2026-03-10), which degrades acceptance ~13pp. The 12.7x speedup assumes full acceptance; actual gain is lower due to frozen state cost. See [SSM Compatibility section](03-prompt-lookup.md#ssm-compatibility-updated-2026-03-15) for details."

2. **Add after line 117** (end of combined techniques section): "**Production Update (May 2026)**: Prompt lookup is now orthogonal to MTP (Gemma4) and MoE-Spec mechanisms. On dense models with high input overlap (summarization, editing), lookup remains the primary acceleration vector. On models with low overlap (code generation, open-ended), MTP/external drafting takes priority."

3. **Optionally add a forward reference** to Nemotron-Labs-Diffusion in the References section (intake-576 area), noting it as a newer unified self-speculation architecture with better acceptance metrics on some tasks.

### Notes

- Chapter is generally accurate for its 2026-03 vintage (last updated in chapter headers). The main gaps are recent (April–May 2026) production deployments and frontier research (Nemotron).
- The "Phase 2B" sections being marked as "CLOSED (2026-02-19)" in a chapter last updated 2026-04-24 is slightly confusing structurally, but the content is preserved correctly. Low priority fix.
- The freeze-recurrent footnote is important because readers may assume 12.7x speedup is achievable on all architectures, which is misleading for SSM-hybrid targets.

---

## 04-radix-attention.md

**Verdict**: up_to_date  
**Severity**: low

### Factual errors

None detected. The chapter correctly documents:
- Prefix cache configuration (line 113: 4096 token minimum, updated Feb 2026)
- Integration testing status (line 9: "46/46 tests passing, awaiting integration testing")
- Canonicalization mechanics and slot validation (lines 230–241)

### Superseded claims

None identified.

### Missing content (post-2026-03-30 landings)

- **Production integration status**: The chapter states (line 9) "Awaiting integration testing with live servers." It is now May 26, 2026, and the chapter was last updated 2026-04-24. The status of this feature (deployed? deferred?) should be clarified. The wiki does not mention a deployment status for RadixAttention. This may need a follow-up inquiry. Source: `/workspace/wiki/speculative-decoding.md` (no mention of RadixAttention status post-2026-03)

### Broken path references

- Line 49 (Component Files table): Path `src/backends/llama_server.py` (477 lines), `src/prefix_cache.py` (584 lines), `src/radix_cache.py` (482 lines). These are plausible paths but Chapter 04 was written for the epyc-inference-research codebase. Current orchestrator structure uses `epyc-orchestrator/` and `epyc-inference-research/` repos. Verify these paths are still valid in the current tree. **Note**: Audit is read-only, so cannot verify without searching codebase. Recommend: maintainer to check `find . -name "prefix_cache.py"` et al.

### Proposed edits

1. **Update line 9** with current status. If deployed, change to "Integration testing complete (validation tests 46/46 passing, deployed to production 2026-XX-XX)." If deferred, change to "Integration testing deferred pending [reason]. Current status: unit tests only (46/46 passing)."

2. **If integration is deferred**, add a note explaining the blockers or deferral reason at the end of the chapter.

### Notes

- RadixAttention is a well-documented, complete implementation with thorough test coverage. The only gap is the status update for May 2026. This is a low-priority fix but important for maintaining a current docs baseline.
- The component paths should be verified against the current repository structure, but the chapter itself is internally consistent and technically sound.

---

## 05-deprecated-approaches.md

**Verdict**: up_to_date  
**Severity**: low

### Factual errors

None detected. All deprecated approaches are accurately described with documented failure modes:
- EAGLE-1: Checkpoint incompatibility with GGUF
- CAS-Spec: 0.446% acceptance without trained classifiers
- SSM Speculation: State corruption (correct as of 2026-02, though note below)
- Medusa, CLaSp, Kangaroo: Documented reasons for deferral

### Superseded claims

- **Track 5 SSM Speculation (lines 75–93)**: The chapter correctly states speculation is incompatible with SSM. However, subsequent research (2026-04) has **partially reopened** this via slot-promotion mechanism and auto freeze-recurrent prompt lookup. The chapter should add a note that the "never use speculation" recommendation is softened for prompt lookup (which now works via freeze-recurrent). The "speculation dead" status remains true for external draft models, but is nuanced. Source: `/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md`, `/workspace/wiki/ssm-hybrid.md` § "Slot-Promotion Reopener"

### Missing content (post-2026-03-30 landings)

- **DFlash (Feb 2026) failure on Q4_K_M**: DFlash is a NEW deprecated approach for the EPYC CPU stack. The 21-commit port was completed and determined to be not viable on Q4_K_M (27% per-token acceptance vs 36.5 t/s autoregressive for DFlash at 13.0 t/s). This is a significant 2026-04 finding that should be documented here. Source: `/workspace/handoffs/completed/dflash-block-diffusion-speculation.md`; `/workspace/wiki/speculative-decoding.md` § "DFlash O(1) drafting is real but quantization kills acceptance"

- **Slot-promotion (April 2026)**: The slot-promotion reopener on hybrid SSM models (tested April 2026) ultimately failed (net-negative on Qwen3.6-35B + Qwen3-1.7B drafter, 97% primary wins). This is a deprecated approach for THIS drafter/target pair. Source: `/workspace/handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md`

- **MAB tree-shape selector (April 2026)**: Tested and found to be no-go across multiple phases (Coder tree -1.34% NS, REAP tree -8.20% p<0.001). This is a deprecated approach. Source: `/workspace/handoffs/completed/mab-tree-shape-selector.md`

### Broken path references

None identified.

### Proposed edits

1. **Add new section after line 93** (after Track 5): "## Track 6: DFlash Block Diffusion (CPU Q4_K_M) — Feb 2026" with:
   - Brief description: "DFlash achieves O(1) draft cost via block-wise conditioning on hidden states. On GPU (f16), acceptance is 6.49 tokens per round. On CPU with Q4_K_M quantization, quantized hidden state conditioning degrades acceptance to 27% per token."
   - Failure mode: "Quantization noise in hidden state extraction corrupts the conditioning signal. Root cause: hidden states are extracted from quantized weight layers, introducing rounding error that propagates through the drafter MLP."
   - Lesson learned: "Block diffusion methods require high-precision hidden state access. Q4_K_M quantization is fundamentally incompatible with this architecture. Autoregressive drafters (EAGLE-3, MTP) remain more robust to quantization."
   - Reference: `completed/dflash-block-diffusion-speculation.md`

2. **Add new section** "## Track 11: Slot-Promotion Speculation (April 2026) — Hybrid SSM" with:
   - Brief description: "Per-candidate state slots via `S_new = S_parent + Δ(k,v,β,g)`, enabling K-parallel verification on Delta Net without full-state cloning."
   - Failure mode: "On Qwen3.6-35B-A3B + Qwen3-1.7B drafter: K=4 dispatcher measures 7.42 t/s vs K=1 baseline 11.40 t/s (35% slower). Primary path wins 60/62 rounds (97%), with aux branches providing negligible additional accepted tokens."
   - Lesson learned: "K-parallel verify gains assume branch diversity. When the drafter and target have similar probability distributions, all K branches explore nearly-identical token paths, eliminating parallelism benefit. Dispatcher overhead (22ms) exceeds expected savings (2.5ms). Slot mechanism is sound but economics are unfavorable for THIS drafter/target pair."
   - Reference: `completed/hybrid-ssm-slot-promotion-spec-dec.md`

3. **Add new section** "## Track 12: MAB Tree-Shape Selector (April 2026)" with:
   - Brief description: "Multi-armed bandit tree topology optimization per Pythia experiments (intake-491)."
   - Failure mode: "On Qwen3-Coder-30B: tree -1.34% NS under canonical recipe (n=180). On REAP-246B: tree -8.20% p<0.001. Linear speculation saturates at K=16; tree branching adds overhead without acceptance gains."
   - Lesson learned: "Tree topology optimization is architecture-specific. The Pythia-6.9B + EAGLE drafter from the paper does not generalize to Qwen-family models or drafter uncertainty profiles. Canonical recipe (OMP + numactl + taskset) is critical — prior results poisoned by broken-OMP baseline."
   - Reference: `completed/mab-tree-shape-selector.md`

4. **Update Track 5 header** from "SSM Speculation" to "SSM Speculation (External Draft)" and add note: "**Update (2026-04)**: Prompt lookup now works on SSM-hybrid models via auto freeze-recurrent (acceptance drop ~13pp), partially reopening the architectural class. This deprecation applies to **external speculative decoding with separate draft models**. Prompt lookup uses a different mechanism (n-gram matching) and is viable."

### Notes

- Chapter 05 is well-structured and accurate. The additions recommended are all post-2026-03-30 deprecated approaches that merit inclusion for completeness.
- The SSM Speculation deprecation is slightly nuanced — it's not "never use speculation" but rather "never use external draft with separate draft model." Prompt lookup via freeze-recurrent is now viable on hybrid SSM models.

---

## 10-advanced-speculative-decoding.md

**Verdict**: patch  
**Severity**: medium

### Factual errors

- **Line 28** (SpecInfer speedup "1.5–3.5x on A10 GPUs"): The chapter notes this is GPU-only. However, the context of the document is EPYC CPU inference. Recommend: add a CPU applicability assessment inline, e.g., "GPU: 1.5–3.5x (CUDA-specific); CPU applicability: Medium (tree topology porting is feasible, but tree attention kernels require ggml implementation)."

- **Line 651 (SpecExec interpretation)**: The chapter states "The draft model (e.g., Qwen 2B at ~1.5GB) costs only ~5ms per forward pass." This assumes specific hardware (EPYC with DDR5 bandwidth). For a reader on different hardware, this number is not transferable. Recommend: change to "The draft model cost is typically <10% of verification cost on memory-bandwidth-bound systems," or cite the specific EPYC calculation.

- **Line 627 (Q4_K_M batch verification cost)**: The chapter reports 4.39x–4.96x cost growth at batch=64 vs batch=1 for Q4_K_M models. This is empirically correct (from Section 10.1 table), but the chapter frames it as contradicting SpecExec's thesis. The CRITICAL finding is: **SpecExec assumes GPU HBM bandwidth regime (~1.4 TB/s) whereas EPYC DDR5 is 300 GB/s — a 4.6x difference**. The Q4_K_M 4–5x scaling is actually CONSISTENT with the SpecExec model because dequantization overhead dominates on CPU. Chapter should clarify this is not a contradiction but a regime difference. Source: `/workspace/wiki/speculative-decoding.md` § "Verification wall"; Section 10.1 findings

### Superseded claims

- **Line 651 (1000-token trees as optimal)**: The chapter projects "optimal tree size on CPU is hundreds to thousands" based on SpecExec's near-free verification assumption. However, **Section 10.3 empirical validation (lines 636–646)** directly contradicts this: linear K=16→256 shows **flat or degrading throughput** on EPYC. Linear speculation **saturates at K~16** because acceptance decays geometrically. The chapter's projected 1000-token trees are **not validated empirically** for EPYC. The correct statement is: "Theoretical optimal is unknown; empirical validation shows linear saturation at K=16–24. Tree speculation may improve on linear, but no endpoint validation done on EPYC." Source: Section 10.3

- **Lines 458–476 (Tier 1/2/3 priorities)**: These are time-stamped research directions from early 2026. Subsequent work (April–May 2026) has **closed several of these**. DFlash (Tier 1) is CLOSED as not viable on Q4_K_M. Slot-promotion (Tier 2) is CLOSED as net-negative. MAB selector (Tier 2) is CLOSED as no-go. These should be moved to "Tier X — Concluded (2026-04)" sections. Source: `/workspace/handoffs/completed/dflash-block-diffusion-speculation.md`, etc.

### Missing content (post-2026-03-30 landings)

- **Section 10.3 empirical validation is from March 2026**. The chapter should add **Section 10.5 or 10.6** documenting April–May 2026 findings:
  - MAB tree-shape selector: NO-GO (Coder -1.34% NS, REAP -8.20% p<0.001)
  - Slot-promotion hybrid SSM: NO-GO (K=4 35% slower, primary wins 97%)
  - DFlash Q4_K_M: NO-GO (27% acceptance vs AR 36.5 t/s)
  - MoE-Spec verification budget: DEPLOYABLE on REAP-246B (+3% e2e, +15.2% forward-pass)
  - Gemma4 MTP: DEPLOYED (1.06x on MoE, 2.98x on dense)
  
  Source: `/workspace/wiki/speculative-decoding.md` § "Updates — 2026-04-28"; `/workspace/progress/2026-05/2026-05-08.md`

- **Nemotron-Labs-Diffusion (May 2026)**: A new architecture with unified self-speculation achieving 5.46 accepted tokens per cycle (better than EAGLE-3 on some tasks). Dense backbone (Ministral3, no SSM), so architecturally more favorable than DFlash for CPU port. Should be added to Section 3 or a new Section 12. Source: `/workspace/wiki/speculative-decoding.md` § "Unified-model self-speculation"

- **REAP-pruned models**: The chapter does not mention that pure-MoE targets (REAP-25B, REAP-246B) change the speculation landscape fundamentally. REAP-25B at dm=24 achieves 39.62 t/s with linear speculation (101% speedup) — production-deployed. This is **not advanced** (uses standard `--draft`), but it's the most impactful speculation result on EPYC and deserves mention. Source: `/workspace/wiki/speculative-decoding.md` § "REAP-pruned models"; `/workspace/handoffs/completed/reap-moe-expert-pruning.md`

- **NUMA parallelism as the primary lever**: The wiki synthesis (compiled 2026-04-30) concludes "NUMA 4-way parallel serving (6.7x aggregate) remains the primary CPU acceleration lever" and "Spec-dec axes are stacking incremental gains on top of an already-saturated verification-step budget." This is a **meta-finding** that should be discussed in Chapter 10's opening or conclusion, not buried in the wiki. Source: `/workspace/wiki/speculative-decoding.md` § "Amdahl ceiling for spec-dec end-to-end gain"

### Broken path references

- Line 128 (ggml tree attention "blocked on upstream tree attention support"): This is outdated. As of 2026-05, the `feature/llm-tree` branch is active on llama.cpp-experimental. Path/status should be verified. Source: GitHub llama.cpp; cannot verify without network access from audit constraints.

- Lines 167, 286, 402–403: Reference "arXiv:2602.16994" (Dynamic Delayed Tree Expansion), "arXiv:2510.01336" (HiSpec), "arXiv:2601.05724" (HSD), "arXiv:2603.03251" (SSD). These are plausible IDs but dates suggest publication in 2026 (future from Chapter-10's Feb 2026 perspective, but prior from May 2026 audit perspective). Verify against actual publication dates.

### Proposed edits

1. **Add new Section 10.5** (after empirical validation results): "## Empirical Validation — 2026-04-30 Phase II (Closed Investigations)" with bullet points on MAB (NO-GO), slot-promotion (NO-GO), DFlash Q4_K_M (NO-GO), MoE-Spec REAP (DEPLOYABLE), Gemma4 MTP (DEPLOYED).

2. **Add new Section 10.6**: "## Nemotron-Labs-Diffusion: Unified Self-Speculation (May 2026)" — brief overview of the new frontier architecture and its CPU portability assessment.

3. **Update Section 8 / Tier classification** (lines 453–476): Move DFlash, slot-promotion, MAB to "Tier X — Concluded (2026-04)"; move Gemma4 MTP to "Tier 0 — Production Deployed"; add MoE-Spec to "Tier 1 — Implement now (REAP-246B variant)."

4. **Add to opening paragraph** (after line 10): "**Current Status (May 2026)**: NUMA 4-way parallel serving remains the primary CPU acceleration lever (6.7x aggregate throughput). Speculative decoding provides incremental gains (+17–21% from draft tuning, +1–5% from advanced techniques) on top of this baseline. The investigations documented in this chapter have produced three closed findings (2026-04–05) and two deployable mechanisms (MoE-Spec on REAP, Gemma4 MTP)."

5. **Verify and update** path/reference citations at lines 128, 167, 286, 402–403 against current upstream and publication dates.

### Notes

- Chapter 10 is the most ambitious and technically rigorous of the six chapters, with deep literature survey and empirical validation. The main issue is that it was last updated 2026-04-24 and significant findings have accumulated since (through 2026-05-26).
- The **SpecExec interpretation error** (line 651) is subtle but important: readers may incorrectly conclude that 1000-token trees are optimal on EPYC, whereas the empirical data (Section 10.3) shows saturation at K~16. This should be corrected.
- The deprecation of several Tier 1/2 research directions is important to communicate because future work may otherwise duplicate effort on closed investigations.
- The absence of NUMA parallelism as a primary finding is the biggest structural gap in the chapter. NUMA parallelism is the **dominant** acceleration mechanism for EPYC (6.7x), yet speculation is the focus. This imbalance should be acknowledged.

---

## Summary

| Chapter | Status | Main Issues | Priority |
|---------|--------|-----------|----------|
| 01 | patch | Obsolete baseline data, missing Gemma4/DFlash, incorrect "primary" claim | medium |
| 02 | up_to_date | Minor gap (REAP omission) | low |
| 03 | patch | SSM-hybrid freeze-recurrent footnote needed, Qwen2.5 baseline outdated | medium |
| 04 | up_to_date | Status update needed (deployed? deferred?) | low |
| 05 | up_to_date | Missing DFlash/slot-promotion/MAB deprecations (post-2026-03-30) | low-medium |
| 10 | patch | Multiple 2026-04+ closures missing, empirical validation contradicts projection | medium-high |

**Recommendations for downstream agent**:
1. **High priority**: Update Chapter 01 (remove "primary" claim, add Gemma4 section, contextualize baseline) and Chapter 10 (add 2026-04-30 closure summary, clarify NUMA vs spec-dec leverage).
2. **Medium priority**: Add Gemma4/DFlash to Chapter 03; add footnote on freeze-recurrent acceptance drop; update Chapters 02 and 05 with REAP and new deprecated approaches.
3. **Low priority**: Verify Chapter 04 integration status; update path references in Chapter 10.

**All findings cite source documents in `/workspace/wiki/`, `/workspace/handoffs/completed/`, and `/workspace/progress/2026-05/` for verification.**


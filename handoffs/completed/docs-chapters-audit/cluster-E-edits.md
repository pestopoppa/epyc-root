# Cluster E — Edit Pass Report

**Date**: 2026-05-26
**Editor**: Claude (Opus 4.7)
**Audit input**: `/workspace/handoffs/active/docs-chapters-audit/cluster-E.md`

## Files modified

All three patches applied as uncommitted, staged-but-not-committed edits to:

- `/workspace/repos/epyc-inference-research/docs/chapters/01-speculative-decoding.md`
- `/workspace/repos/epyc-inference-research/docs/chapters/03-prompt-lookup.md`
- `/workspace/repos/epyc-inference-research/docs/chapters/10-advanced-speculative-decoding.md`

### Ch01 — Speculative Decoding (medium)
- Added "Current Status (May 2026)" callout at top reframing speculation as incremental on top of NUMA 4-way (primary lever).
- Softened intro from "primary optimization technique" to "foundational optimization technique" with 11x reframed as a 2025 baseline.
- Added scope-caveat sidebar before performance table pointing to Ch10 + production wiki.
- Annotated performance table with Gemma4-26B-A4B replacement context (1.06x MoE / 2.98x dense, 2026-05-08).
- Added "Revised 2026-04+" sidebar to K-Value Optimization referencing §10.3 K~16 saturation.
- Added 2026-05 caveat to Temperature Tuning noting orthogonality on Gemma4/REAP.
- Marked launch command as legacy 2025 CLI; pointed to current `llama-server` registry-driven launch.
- Rewrote SSM Architecture Incompatibility section to incorporate verification wall quantification (0.56x at batch=2 MTP-1), freeze-recurrent breakthrough (+5–10%), and the closed slot-promotion alternative.
- Annotated Qwen3-Coder-480B jukofyork draft as experimental / not in current production registry.
- Added "Production Update (May 2026) — Gemma4 MTP, REAP, DFlash" section with five bullets: Gemma4 MTP DEPLOYED, REAP DEPLOYED, DFlash NO-GO, MoE-Spec DEPLOYABLE, Nemotron-Labs-Diffusion frontier.
- Added DFlash and Gemma4 MTP entries to References.

### Ch03 — Prompt Lookup (medium)
- Added footnote ¹ to Qwen3-Next-80B 12.7x row quantifying ~13pp freeze-recurrent acceptance drop, pointing to Ch10 §11.5 and the hsd handoff.
- Added footnote ² to Qwen2.5-Coder-32B rows noting Gemma4 replacement in production (2026-05-08).
- Added Production Update sidebar (May 2026) on orthogonality with MTP and MoE-Spec.
- Expanded SSM Compatibility section with quantified empirical numbers (60.7% → 47.9%) and reference to slot-promotion closure.
- Added Nemotron-Labs-Diffusion entry under new "Unified Self-Speculation (Frontier, May 2026)" reference subsection.

### Ch10 — Advanced Speculative Decoding (medium-high; internal contradiction)
- Added "Current Status (May 2026)" callout at top with NUMA-primary / spec-dec-incremental framing and closure summary preview.
- **Resolved the SpecExec / §10.3 contradiction** (see Verification notes below).
- Updated "CPU Relevance of Tree Methods (Revised)" table to "Revised — Empirical, 2026-03" with empirically grounded rows (4–5x dequant scaling on Q4_K_M, K~16 saturation, 16–64 node tree budgets, ~41ms construction overhead hard floor).
- Added empirical caveat to §9's quantitative 5–9x projection.
- Rewrote Tier 1/2/3 classifications with closure status tags (DEPLOYED / DEPLOYABLE / CLOSED-NO-GO / PARTIAL / DEFERRED) and added Tier 0' production-deployed list.
- Added **§10.5 Empirical Validation — Phase II Closure Pass (2026-04 → 2026-05)** with the six-row closure table covering MAB NO-GO, slot-promotion NO-GO, DFlash NO-GO, MoE-Spec DEPLOYABLE, Gemma4 MTP DEPLOYED, REAP DEPLOYED — and the Amdahl-ceiling meta-finding.
- Added **§10.6 Nemotron-Labs-Diffusion** brief on May 2026 unified self-speculation architecture.
- Updated §10.4 closing sentence about "blocked on upstream tree attention" to note the feature is now landed (§12).

## Edits deferred or skipped

- **Ch10 §1.1 SpecInfer CPU applicability line** (audit suggestion): Did not add inline "CPU applicability: Medium" per-row annotations — the chapter already does this systematically via per-section "CPU Relevance" subsections and the §8 comparison matrix. Adding inline notes would duplicate.
- **Ch10 §1.5 line 651 SpecExec hardware-specific 5ms / 60ms numbers** (audit suggestion to genericize): Preserved as-is because they are correctly scoped to EPYC in the surrounding text. Genericizing would weaken the contradiction-reconciliation argument.
- **Ch10 path references at lines 128, 167, 286, 402–403** (audit suggestion to verify arXiv IDs and llama.cpp branch status): Performed light annotation at the §10.4 boundary noting the upstream tree-attention status; did not chase down individual arXiv IDs because the audit itself marked them as plausible and verifying requires network access not invoked in this pass.
- **Ch10 §13.5 / TIDE projection language**: Left existing TIDE text intact — it is current as of 2026-04-23 per the chapter, and reflects the open-router problem accurately. No new findings to merge.
- **Phase 2B "CLOSED" structural reorganization in Ch03** (audit low-priority suggestion): Did not restructure. The "CLOSED" markers are clear in context; restructuring would touch too much surface area for a low-priority finding.

## Audit items I disagreed with

- **Ch10 audit framed §10.1's 4.39–4.96x Q4_K_M finding as "contradicting SpecExec's thesis"** while the chapter itself "frames it as contradicting." On re-read, the chapter's existing language at line 626 already correctly says "holds only for f16 models on this hardware" — i.e., it does not contradict, it identifies a regime difference. The audit slightly mis-characterizes the existing chapter on this point. I adopted the audit's framing (HBM vs DDR5 regime difference, not contradiction) in the new reconciliation text, which is closer to the audit's intent than its own description suggests.
- **Ch01 audit's recommendation to "explicitly mark as experimental / not in production"** for the jukofyork vocab-transplant draft: Applied as a status annotation rather than a deletion. The audit suggested "either remove or explicitly mark" — I chose mark, preserving the historical record per chapter voice.

## Recommended new chapters or follow-ups

- **Chapter 11: NUMA Parallel Serving as the Primary CPU Lever** — The audit identifies that NUMA 4-way (6.7x) is the dominant acceleration on EPYC, yet there is no chapter dedicated to it. The structural imbalance between five speculation chapters and zero NUMA-serving chapter is the largest documentation gap.
- **Chapter 12: Production Model Stack (May 2026)** — A single chapter documenting the current stack (Gemma4-26B-A4B MTP worker_general, REAP-25B/246B, Qwen3-Next-80B ingest_long_context, etc.) with role → port mapping and MTP-specific launch flags. Currently this information is spread across registry YAML + progress logs + multiple memory entries.
- **Follow-up: Ch04 RadixAttention integration-status verification** (audit medium-priority): Audit noted the chapter has been "awaiting integration testing" since 2026-04-24. A maintainer should check current deployment status and update line 9 — out of scope for Cluster E (was marked up_to_date).
- **Follow-up: Ch05 — add Track 6 (DFlash), Track 11 (slot-promotion), Track 12 (MAB) deprecated sections** per audit (was marked up_to_date with low-medium severity). The audit had concrete proposed text — would be a fast next-pass.

## Verification notes

### How I resolved the Ch10 internal contradiction

The contradiction lived in two places:

1. **§1.5 SpecExec subsection (around lines 99–104)**: "Optimal tree size on CPU is NOT 8–32 nodes — it could be hundreds to thousands"; "A draft tree of 1024 tokens costs maybe 50–100ms to build but saves dozens of 60ms verification passes."
2. **"CPU Relevance of Tree Methods (Revised)" table** (around lines 117–129): "Hundreds to thousands (weight-load amortization)" for optimal tree size; "larger trees are cheaper than assumed."

Both directly contradicted **§10.3 Phase 3 empirical** (linear K=16 → K=256 is FLAT across all four measured pairs — Qwen2.5-7B+0.5B, Coder-32B+0.5B, Qwen3.5-9B+0.8B, Qwen3.5-27B+0.8B) and **§10.1** (Q4_K_M shows 4.05–4.96x cost growth at N=64, NOT near-flat — the SpecExec thesis "holds only for f16 models on this hardware").

**Resolution approach** (per audit instruction): replaced projection-style language with empirical-results-based framing while preserving the chapter's pedagogical voice and the upstream SpecExec citation.

Specific changes:

- **§1.5 SpecExec subsection**: Rewrote the "Why this changes the CPU calculus" paragraph to lead with "**Why this initially looked like it changes the CPU calculus**" (projection) → "**Empirical reality on EPYC**" (§10.1 + §10.3 results) → regime-difference explanation (GPU HBM ~1.4 TB/s vs EPYC DDR5 ~300 GB/s ratio inverts dequant-vs-bandwidth cost) → corrected bullets ("Optimal tree size on CPU is NOT 'hundreds to thousands'"; tree budget is "16–64 nodes (branching 7/5/3/2, depth ≤ 5, cap 32 seq_ids)" matching the actual DySpec implementation in §12.1).
- **"CPU Relevance of Tree Methods" table**: Retitled "Revised — Empirical, 2026-03" and rewrote every row with empirical numbers (f16 vs Q4_K_M split on verification cost; K~16 saturation; +2–5% f16/large MoE vs -3–8% medium dense Q4 measured deltas; ~41ms hard floor; fast vs slow drafter net effect). The actionable line now matches §12 production recommendation (enable tree only on `architect_general` 235B MoE and f16 targets).
- **§9 quantitative framework 5–9x projection**: Added explicit "Empirical caveat (2026-03)" sidebar pointing to §10.1 / §10.3 / §12, framing the 5–9x as theoretical ceiling vs measured +2–5% on the favorable regimes.

The key reconciliation framing: **SpecExec is correct in its own regime (GPU HBM, f16). EPYC Q4_K_M is a different regime where dequant compute dominates above batch~16, killing the near-flat-verification assumption.** This is not a contradiction of the SpecExec paper — it is a regime boundary that the chapter's earlier text had not yet incorporated.

### Cross-references checked

- Wiki `/workspace/wiki/speculative-decoding.md` — verified Gemma4 MTP DEPLOYED, REAP DEPLOYED, MoE-Spec DEPLOYABLE, DFlash NO-GO, Nemotron May 2026, NUMA 4-way 6.7x as primary lever, Amdahl ceiling framing.
- Progress `/workspace/progress/2026-05/2026-05-08.md` — verified Gemma4 swap details (KMP_BLOCKTIME=10, 8 MTP flags, +18pp tool_compliance, +36% tps, 76.5 t/s solo).
- Handoff `handoffs/completed/hsd-hierarchical-self-speculation.md` — verified freeze-recurrent ~13pp drop, 15.96 t/s +5.4% on Qwen3.5-9B.
- Handoff `handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md` — verified K=4 35% slower than K=1, 97% primary wins.
- Handoff `handoffs/completed/mab-tree-shape-selector.md` — verified Coder -1.34% NS, REAP -8.20% p<0.001.
- Handoff `handoffs/completed/dflash-block-diffusion-speculation.md` — verified 27% per-token acceptance, 13.0 vs 36.5 t/s.
- Memory `project_worker_general_swap_2026_05_08.md` — confirms Gemma4 swap date and metrics.
- Memory `project_orchestrator_stack_freeze.md` — orchestrator stack registry frozen; v5 work is research-registry annotations only. (Relevant for not over-claiming "deployed" beyond what the registry actually reflects.)

### Voice / style notes

- Kept "details/summary" disclosure blocks throughout — they are the chapter convention.
- Kept arrow/dash/em-dash conventions and second-person plural ("our system") consistent with original voice.
- New sidebars use blockquote (`>`) style consistent with existing Ch03's "Production update" and Ch10's existing call-out patterns.
- No emojis added.
- Did not create any new files outside the three chapters + this report.

# Reviewer Control Plane — GLM-5.2 Reviewer Capability Gates (H6, slim)

**Status**: active — parallel track from day 1; gates the H5 A4/A4g arms
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, quantization, local_inference
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related / ownership boundary**: **infra tasks (download/sha256/load-smoke/CPU-bench/expert-routing-skew profile) live in [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md)** (parallel-session-owned) — this handoff holds ONLY the reviewer-specific capability gates and must not duplicate that work. Kernel-side blockers live in [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md); GLM cache/runtime reconciliation is closed by K23 / experimental-v7 `3dee86a5a`, while sparse final-attention and long-context quality remain outside this reviewer-specific gate.
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

## Objective

Take GLM-5.2 UD-IQ2_M (754B glm_moe_dsa, ~239GB, downloaded and true >64K DSA-engagement smoke-passed) from "loads and is coherent" (glm51-reap scope) to "validated typed-decision reviewer candidate" — the reviewer-specific capability layer only.

## Prioritized Task List

- [ ] **GC-1 — Strict-IF / typed-emission probe**: schema-valid `review_decision` emission rate, GBNF-constrained vs free-parse-with-retry, K-of-M pass gate (define K/M here; smoke-level first, claim-level under P-REV-1 later). Motivation: 122B-IQ2 scored 2/11 on strict instruction-following — quant may degrade format compliance; grammar constraint is the expected mitigation. CPU path first (v7 GPU grammar path is P0-blocked in the kernel handoff).
- [ ] **GC-2 — Rubric-authoring quality probe**: GLM-5.2 authors rubrics for a fixed task set; graded against frontier-authored references (criteria count, axis coverage, grounding). The two-turn design (H3 RD-2) makes authoring the heavyweight's ONLY hot-path job — this is the capability that matters most.
- [ ] **GC-3 — Why-diagnosis probe**: rationale-vs-gold-cause match on a corpus-v1 sample (IQ2 quant may degrade why-diagnosis more than that-detection — intake-836; measure, don't assume).
- [ ] **GC-4 — RAM-residency policy decision** (operator, OP bundle): 239GB reviewer + ~70GB architect + frontdoor/workers co-residency vs swap-in-on-demand vs review-windows. Determines whether A4 is an interactive reviewer or a batch/offline judicial gate. Provide the memory-budget table as decision input.
- [ ] **GC-5 — Registry reviewer-capability fields**: structured `measured:` entries (typed-emission rate, authoring score, why-diagnosis, FA/FR once H5 runs) per MEASUREMENT §5b registry ruling; follow `new-model` onboarding conventions.

## Dependency Graph

```text
glm51-reap GO gates (download/integrity ✅ → glm-dsa load smoke ✅ → current-source cache/runtime smoke ✅ → true >64K stale-binary runnability ✅ → sparse-vs-dense + quality/CPU bench)  [parallel session]
        → GC-1 → GC-2 → GC-3 → GC-5
GC-4 operator decision (anytime after CPU bench exists) → shapes H5 A4 arm design
Kernel P0s: grammar fix is closed; GLM-dsa cache/runtime reconciliation is closed by `3dee86a5a`; remaining kernel dependencies are sparse-final-attention classification and any live v7 CPU/perf guard relevant to GC-1 cost.
```

## Cross-Cutting Concerns

1. **Ownership** — anything requiring model downloads, host benches, or the MI210 belongs to the parallel session's handoffs; this file consumes their checkpoints, never re-runs them.
2. **Cross-family thesis** — GLM-judges-Qwen is the anti-collusion arm; its benefit is measured (H5 covariate), not assumed.

## Key Files / Surfaces

- `orchestration/model_registry.yaml` `glm_52_ud_iq2m` entry (research registry line ~5591)
- H2 `review_decision.schema.json` + GBNF generation; H4 corpus sample
- `glm51-reap-cpu-evaluation.md` GO checkpoints (consume)

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; GC-1/2/3 numbers recorded here + registry (GC-5); GC-4 goes to the operator decision queue (§A00) — do not decide autonomously.

## Evidence Base (intake)

intake-836 quant why-diagnosis caveat · intake-834 authoring-capability dominance · intake-837/838 format/bias fragility of judges · audit doc 2026-07-16 (GLM-dsa arch exists in-tree; reconciliation smoke later passed on experimental-v7 `3dee86a5a`; sparse final-attention and reviewer quality remain open).

# Reviewer Control Plane — GLM-5.2 Reviewer Capability Gates (H6, slim)

**Status**: active — blocked on GLM protocol/context-length root-cause before GC-1/2/3; `indexer_top_k=2048` restores short runner-shaped controls only up to the ~1.8K-token band, so H5 A4/A4g remain gated
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, quantization, local_inference
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related / ownership boundary**: **infra tasks (download/sha256/load-smoke/CPU-bench/expert-routing-skew profile) live in [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md)** (parallel-session-owned) — this handoff holds ONLY the reviewer-specific capability gates and must not duplicate that work. Kernel-side blockers live in [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md); GLM cache/runtime reconciliation is closed by K23 / experimental-v7 `3dee86a5a`, sparse final-attention remains kernel work, and current-source 32K needle/coherence currently fails with malformed `peg-native` output.
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

## Objective

Take GLM-5.2 UD-IQ2_M (754B glm_moe_dsa, ~239GB, downloaded, true >64K stale-binary DSA-engagement smoke-passed, and current-source DSA-wired) from "loads" to "validated typed-decision reviewer candidate" — the reviewer-specific capability layer only. Current-source long-context coherence is **not** passed: the 32K needle probe failed on malformed `peg-native` output in both default-reasoning and reasoning-off modes, and the restored default `indexer_top_k=2048` only recovers shorter runner-shaped prompts before failures reappear by `2143` prompt tokens.

## Prioritized Task List

- [x] **GC-0 — Evidence hygiene / runner contract**: reviewer-facing GLM long-output or typed-decision probes must consume only instrumented GLM runs with streaming progress, retained trace logs/server-log timing extraction, and a minimum completion-token floor. `/metrics` samples are acceptable when available, but are not the primary progress channel for a long busy GLM request. The attempted current-source 96K run at `/mnt/raid0/llm/tmp/glm52-current-source-96k-quality-20260717T144022Z/plan.json` is excluded as process-failure-only because it had no progress telemetry and only `max_tokens=32`. ✅ 2026-07-17
- [x] **GC-0a — Current-source 32K needle/coherence gate executed**: default reasoning and `--reasoning off --reasoning-budget 0` both completed full prompt ingest plus 64-token decode, then llama-server returned HTTP 500 because generated output did not match `peg-native`; hidden code `GLM52-NEEDLE-7F3A` was absent. Summary: `/mnt/raid0/llm/epyc-inference-research/data/glm52_dsa_probe/current_source_32k_needle_20260717T1755Z/summary.json`. ✅ 2026-07-17
- [ ] **GC-0b — Output-format root cause**: isolate whether the malformed `peg-native` failure is prompt/template, GLM chat-parser, context length, quant/model behavior, or runner/API mode. The 2026-07-17 default-top-k checkpoint narrowed this: restored `indexer_top_k=2048` recovers short runner-shaped prompts at `1389` and `1767` prompt tokens, but failures return at `2143`, `3045`, and `12043`. GC-1/2/3 should not run until this is fixed or a deliberately different serving mode is chosen.
- [ ] **GC-0c — Protocol-channel matrix**: run a compact matrix across raw `/completion` vs chat/completions, reasoning on/off, schema/`peg-native` vs unconstrained text, and prompt-token bands around the observed failure threshold so GC-1 uses a known-good serving/scoring channel rather than repeating ambiguous GLM breakage.
- [ ] **GC-1 — Strict-IF / typed-emission probe**: schema-valid `review_decision` emission rate, GBNF-constrained vs free-parse-with-retry, K-of-M pass gate (define K/M here; smoke-level first, claim-level under P-REV-1 later). Motivation: 122B-IQ2 scored 2/11 on strict instruction-following — quant may degrade format compliance; grammar constraint is the expected mitigation. CPU path first (v7 GPU grammar path is P0-blocked in the kernel handoff).
- [ ] **GC-2 — Rubric-authoring quality probe**: GLM-5.2 authors rubrics for a fixed task set; graded against frontier-authored references (criteria count, axis coverage, grounding). The two-turn design (H3 RD-2) makes authoring the heavyweight's ONLY hot-path job — this is the capability that matters most.
- [ ] **GC-3 — Why-diagnosis probe**: rationale-vs-gold-cause match on a corpus-v1 sample (IQ2 quant may degrade why-diagnosis more than that-detection — intake-836; measure, don't assume).
- [ ] **GC-4 — RAM-residency policy decision** (operator, OP bundle): 239GB reviewer + ~70GB architect + frontdoor/workers co-residency vs swap-in-on-demand vs review-windows. Determines whether A4 is an interactive reviewer or a batch/offline judicial gate. Provide the memory-budget table as decision input.
- [ ] **GC-5 — Registry reviewer-capability fields**: structured `measured:` entries (typed-emission rate, authoring score, why-diagnosis, FA/FR once H5 runs) per MEASUREMENT §5b registry ruling; follow `new-model` onboarding conventions.

## Dependency Graph

```text
glm51-reap GO gates (download/integrity ✅ → glm-dsa load smoke ✅ → current-source cache/runtime smoke ✅ → true >64K stale-binary runnability ✅ → runtime DSA-DENSE-MASK ✅ → 32K needle/coherence ❌ malformed peg-native → top-k-default short recovery only up to ~1.8K prompt tokens)
        → GC-0b output-format/context-length root cause
        → GC-0c protocol-channel matrix
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

Flip checkboxes `✅ YYYY-MM-DD`; GC-1/2/3 numbers recorded here + registry (GC-5); GC-4 goes to the operator decision queue (§A00) — do not decide autonomously. Any GLM reviewer run without progress telemetry and a completion-token floor is a harness/process observation only. Any run above the current recovery band must also record prompt-token count and serving channel so the threshold map remains comparable.

## Evidence Base (intake)

intake-836 quant why-diagnosis caveat · intake-834 authoring-capability dominance · intake-837/838 format/bias fragility of judges · audit doc 2026-07-16 (GLM-dsa arch exists in-tree; reconciliation smoke later passed on experimental-v7 `3dee86a5a`; sparse final-attention and reviewer quality remain open).

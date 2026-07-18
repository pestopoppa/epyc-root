# Reviewer Control Plane — GLM-5.2 Reviewer Capability Gates (H6, slim)

**Status**: active — GC-0d reviewer-serving chat protocol/schema gate closed; GC-1/2/3 now blocked on running reviewer probes under the next-power-of-two GLM top-k schedule (`2048` through ~2.05K, `4096` through ~3.05K, `16384` at ~12.05K). Raw `/completion` and `/v1/completions` remain unvalidated and are not the default reviewer-serving channel.
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, quantization, local_inference
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related / ownership boundary**: **infra tasks (download/sha256/load-smoke/CPU-bench/expert-routing-skew profile) live in [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md)** (parallel-session-owned) — this handoff holds ONLY the reviewer-specific capability gates and must not duplicate that work. Kernel-side blockers live in [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md); GLM cache/runtime reconciliation is closed by K23 / experimental-v7 `3dee86a5a`, sparse final-attention remains kernel work, and current-source 32K needle/coherence currently fails with malformed `peg-native` output.
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

## Objective

Take GLM-5.2 UD-IQ2_M (754B glm_moe_dsa, ~239GB, downloaded, true >64K stale-binary DSA-engagement smoke-passed, and current-source DSA-wired) from "loads" to "validated typed-decision reviewer candidate" — the reviewer-specific capability layer only. Current reviewer admission is now blocked before GC-1 on executing reviewer probes under the known-good top-k schedule and serving channel: inference-research commit `a6651ed` plus the follow-up sweep show `glm-dsa.attention.indexer.top_k` is the final-attention KV selection cap, `3072` fails at 2.1K/3K, `8192`/`12288` fail at 12K, next power-of-two caps are the observed safe path (`2048`, `4096`, `16384` for the tested prompt bands), and the 2026-07-18 chat protocol/schema matrix passed exact free-text and JSON-schema outputs at actual ~2.9K/~12.0K prompt bands.

## Prioritized Task List

- [x] **GC-0 — Evidence hygiene / runner contract**: reviewer-facing GLM long-output or typed-decision probes must consume only instrumented GLM runs with streaming progress, retained trace logs/server-log timing extraction, and a minimum completion-token floor. `/metrics` samples are acceptable when available, but are not the primary progress channel for a long busy GLM request. The attempted current-source 96K run at `/mnt/raid0/llm/tmp/glm52-current-source-96k-quality-20260717T144022Z/plan.json` is excluded as process-failure-only because it had no progress telemetry and only `max_tokens=32`. ✅ 2026-07-17
- [x] **GC-0a — Current-source 32K needle/coherence gate executed**: default reasoning and `--reasoning off --reasoning-budget 0` both completed full prompt ingest plus 64-token decode, then llama-server returned HTTP 500 because generated output did not match `peg-native`; hidden code `GLM52-NEEDLE-7F3A` was absent. Summary: `/mnt/raid0/llm/epyc-inference-research/data/glm52_dsa_probe/current_source_32k_needle_20260717T1755Z/summary.json`. ✅ 2026-07-17
- [x] **GC-0b — Top-k cap diagnosis closed**: the active blocker is now narrower than "GLM malformed output." Inference-research commit `a6651ed` shows `glm-dsa.attention.indexer.top_k` is the final-attention KV selection cap: `2048` passes exact `READY` at `1767/2056` prompt tokens but fails at `2168/3045/12043`; `4096` recovers `2168/3045`; `16384` recovers `12045`. ✅ 2026-07-18
- [x] **GC-0c — Smallest-safe prompt-length-aware top-k schedule**: follow-up sweep rejected `top_k=3072` at 2.1K/3K and `8192`/`12288` at 12K; exact `READY` is only observed on next power-of-two caps (`2048`, `4096`, `16384`) for these prompt bands. GC-1/2/3 should run under that schedule, not a flat default cap. ✅ 2026-07-18
- [x] **GC-0d — Protocol-channel matrix**: reviewer-serving chat/completions matrix passed exact free-text `READY` and exact JSON-schema `{"decision":"allow"}` at actual `2894/2898` prompt tokens with `indexer_top_k=4096` and `12044/12045` prompt tokens with `indexer_top_k=16384`. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_protocol_channel_matrix/glm52-gc0d-chat-p2168-p12000-20260718T0120Z/summary.json`. The first all-endpoint attempt was stopped after raw completion endpoint cost/pathology; raw `/completion` and `/v1/completions` stay unvalidated and must be probed only narrowly if a future route needs them. ✅ 2026-07-18
- [ ] **GC-1 — Strict-IF / typed-emission probe**: schema-valid `review_decision` emission rate, GBNF-constrained vs free-parse-with-retry, K-of-M pass gate (define K/M here; smoke-level first, claim-level under P-REV-1 later). Motivation: 122B-IQ2 scored 2/11 on strict instruction-following — quant may degrade format compliance; grammar constraint is the expected mitigation. CPU path first (v7 GPU grammar path is P0-blocked in the kernel handoff).
- [ ] **GC-2 — Rubric-authoring quality probe**: GLM-5.2 authors rubrics for a fixed task set; graded against frontier-authored references (criteria count, axis coverage, grounding). The two-turn design (H3 RD-2) makes authoring the heavyweight's ONLY hot-path job — this is the capability that matters most.
- [ ] **GC-3 — Why-diagnosis probe**: rationale-vs-gold-cause match on a corpus-v1 sample (IQ2 quant may degrade why-diagnosis more than that-detection — intake-836; measure, don't assume).
- [ ] **GC-4 — RAM-residency policy decision** (operator, OP bundle): 239GB reviewer + ~70GB architect + frontdoor/workers co-residency vs swap-in-on-demand vs review-windows. Determines whether A4 is an interactive reviewer or a batch/offline judicial gate. Provide the memory-budget table as decision input.
- [ ] **GC-5 — Registry reviewer-capability fields**: structured `measured:` entries (typed-emission rate, authoring score, why-diagnosis, FA/FR once H5 runs) per MEASUREMENT §5b registry ruling; follow `new-model` onboarding conventions.

## Dependency Graph

```text
glm51-reap GO gates (download/integrity ✅ → glm-dsa load smoke ✅ → current-source cache/runtime smoke ✅ → true >64K stale-binary runnability ✅ → runtime DSA-DENSE-MASK ✅ → top-k-cap diagnosis ✅ → schedule ✅ (`3072` fails at 2.1K/3K, `8192`/`12288` fail at 12K, next-power-of-two caps pass tested bands))
        → GC-0d protocol-channel matrix ✅ (chat/free+schema reviewer-serving channel; raw endpoints unvalidated)
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

Flip checkboxes `✅ YYYY-MM-DD`; GC-1/2/3 numbers recorded here + registry (GC-5); GC-4 goes to the operator decision queue (§A00) — do not decide autonomously. Any GLM reviewer run without progress telemetry and a completion-token floor is a harness/process observation only. Any run above the current recovery band must also record prompt-token count, chosen `indexer_top_k`, and serving channel so the schedule map remains comparable.

## Evidence Base (intake)

intake-836 quant why-diagnosis caveat · intake-834 authoring-capability dominance · intake-837/838 format/bias fragility of judges · audit doc 2026-07-16 (GLM-dsa arch exists in-tree; reconciliation smoke later passed on experimental-v7 `3dee86a5a`; sparse final-attention and reviewer quality remain open).

# 2026-07-18 — v7 kernel lever audit + inference-research handoff refresh

Operator-requested read-only audit of ~5 weeks of v7-experimental + CPU/GPU/spec-dec/GLM
optimization work, delivered as a refreshed inference-research handoff set for the parallel
inference agent. Docs-only; **no production kernel or inference touched** (production frozen).

## Method
5 parallel research agents swept: the v7 tracker + reviewer-control-plane tail, GPU/MI210
lever taxonomy, CPU lever taxonomy (roofline), July progress reports (negative-results
sweep), GLM-5.2 acceleration state, and spec-dec/MTP state. Cross-verified against live
branch state (`experimental-v7-refresh-20260716` @ `d1e5a20eb`: iqk + GPU-opt flags +
`GGML_TYPE_Q2_0`=42 all present on disk) and the master-index operator-decision queue.

## Headline finding
The single largest measured performance win is **already built, correctness-verified, and
banked — but UNPROMOTED**. v7 refresh carries HIP graphs +25% worker spec-dec, MMVQ→MMQ
+17–32%, bf16-GDN-state +16–21% agg, +37% single-stream dense-Q8. K5 quality gate PASSED
(v6≈v7, +0.0%); all P0 correctness blockers resolved (K22 `96986f5e9`, K23 `3dee86a5a`,
K32/K33). v7 is held only by operator gates (K35 finalize, OP-2 canonical bench, `P-GPU-1`
ratification) + the CPU-correctness gate — not by missing engineering.

## Frontier reframes (recorded for the parallel agent)
- **CPU decode is bandwidth-exhausted** (0.17 IPC, 96.6% memory-stalled @96t) — proven, not
  asserted. The *sole* live CPU decode lever is Q8_0 barrier-count operator/graph fusion
  (+2.6% measured → +10–15% graph-rewrite → +72% ceiling). Untapped large-model regime =
  **prefill-compute** (compute-bound, not BW-killed) → new track.
- **GPU raw-speed frontier is structurally exhausted** (both occupancy rewrites falsified;
  single-stream dense-Q8 at +37% ceiling). Live GPU frontier = **residency + teleport**
  (AXA-1 now unblocked by the K22 grammar fix) + two residuals (stream-K, K28).
- **GLM acceleration EV is contingent on quality repair** (patch-review FA up to 91.7%);
  native-GLM-MTP port (+34–89% decode) and real sparse final-attention sequence AFTER
  GC-shadow-repair4b → P-REV-1.

## Two-lane queue delivered
- **LANE A (operator-facing):** A1 K35 finalize · A2 OP-2 canonical-bench window · A3
  `P-GPU-1` ratification package · A4 branch-naming reconciliation.
- **LANE B (agent-executable):** B1 barrier-fusion tg128 A/B (fold into A2) · B2 stream-K
  pmc-CSV read · B3 MoE-Spec reopen assessment · B4 DSA-D3 profile (fold into A2) · B5 E3/E4
  zero-inference decisions · B6 native-GLM-MTP scoping (build gated on GLM quality) · B7
  prefill-compute PC-0.

## Deliverable — handoff edits (docs-only)
Modified: `inference-acceleration-index.md` (new §v7 lever audit + two-lane queue + ledger +
checklist rows), `cpu-inference-optimization-index.md` (BW-exhausted reframe + prefill-compute
row), `mi210-big-model-and-acceleration-roadmap.md` (stream-K + K28 owned tasks + frontier
note), `gemma-challenge-kernel-techniques-v7.md` (v7 promotion-readiness block),
`tree-draft-forward-port-plan.md` (native-GLM-MTP gate update: PR#21149 stale → quality gate;
new task), `glm52-reviewer-capability-gates.md` (acceleration-gating note),
`master-handoff-index.md` (2026-07-18 coordination checkpoint).
Created: `cpu-prefill-compute-large-models.md`, `gpu-drafter-control-redesign.md` (both
user-approved new tracks).

## Verification
- Link integrity: all new cross-links resolve (checked programmatically).
- No production-kernel/`/mnt/raid0` path in the epyc-root working tree.
- Handoff-freshness validator: PASS (tree-draft 2026-07-18 ok).
- Checkbox discipline: all additions are open `- [ ]` tasks; no un-checkboxed completion claims.
- Known pre-existing (NOT this session): `wiki/source_manifest.json` doc-drift is stale for
  171 files from the parallel session's work (only 2 are mine); manifest regeneration is a
  separate wiki-tooling task and would fold in 169 unrelated changes — left for the wiki owner.

## Memory
Filed `project_v7_lever_audit_2026_07_18` (v7 banked-but-unpromoted = highest EV; CPU decode
BW-exhausted → barrier-fusion sole live decode lever; GLM kernel work gated on quality).

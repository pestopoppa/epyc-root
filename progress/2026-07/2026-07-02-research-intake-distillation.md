# 2026-07-02 — Research Intake Batch (intake-732…750) + Handoff Distillation

**Session type**: operator-directed `/research-intake` on a 13-source batch, followed by a deep-dive distillation of the resulting insights into active handoffs.

## Problem / Context

Operator submitted a 13-URL/prose research batch spanning speculative decoding (DeepSeek DSpark cluster), local-inference systems, tabular foundation models, agent-trace tooling, and memory/aggregation methods. Task: run the full intake pipeline, then "deep dive all applicable intakes and distill what should go into handoffs (and where)."

## What was done

### Phase A — Intake (19 new entries: intake-732…750)
- Dedup against the 728-entry index found **4 already-indexed** (reported, not re-added): MRAgent `2606.06036`→intake-698, Autodata `2606.25996`→intake-731, liteparse→intake-647, Sakana Fugu `2606.21228`→intake-728.
- **Three arXiv-ID mismatches caught**: `2606.23595` resolves to **SPIRAL** (not the "Local LLM Inference" guide the operator labeled it); `2606.21228` is **Fugu** (mis-grouped with the DeepSeek links); (prior batch) `2606.25996` was Autodata not Ornith.
- Fan-out workflow (23 subagents, 0 errors): 6 ingest → 6 adversarial-verify → coordinator → 10 capped literature-expansion. Produced 8 primary + 10 expansion entries.
- The orphaned "Local LLM Inference" guide (arXiv mismatch → SPIRAL) was indexed URL-less as intake-750 per the "never dismiss a source" rule, flagged for a corrected URL.
- `validate_intake.py` → exit 0 (750 entries).

### Phase B — Distillation into handoffs (5 read-only Explore agents → 14 edits across 9 handoffs)
Each new insight was mapped to its target handoff with exact line anchors; all handoff writes were operator-approved ("apply all 9").

## Changes made

| Repo | File | Change |
|------|------|--------|
| epyc-root | `research/intake_index.yaml` | +19 entries (732–750); `handoffs_updated` provenance populated for 17 |
| epyc-root | `handoffs/active/speculative-decoding-mtp-refresh.md` | FR-Spec/DSpark/DeepSpec/Graft verdict rows + DSpark watch-item + BW-slice bullet + EAGLE-3-watch-now-due |
| epyc-root | `handoffs/active/moe-spec-cpu-spec-dec-integration.md` | new Research Intake Update 2026-07-02: DSpark scheduler CPU-inertness, Graft, DFlare (+DFlash disambiguation) |
| epyc-root | `handoffs/active/qwen-mtp-llamacpp-port.md` | P7 FR-Spec vocab-trim task (inert-EAGLE3-stub caveat) + reference |
| epyc-root | `handoffs/active/deepseek-v4-flash-cpu-port.md` | V4-Pro `do_not_port` row + sibling cross-ref |
| epyc-root | `handoffs/active/gpu-drafter-mi200-investigation.md` | DSpark trained-drafter path under §Gating Measurement (α-gated; 77%-saturation caveat) + intake-update |
| epyc-root | `handoffs/active/learned-routing-controller.md` | parked tabular-FM candidate heads (double-gated) |
| epyc-root | `handoffs/active/reasoning-compression.md` | SPIRAL training-free aggregation + Poly-EPO/Polychromic Tier-3 pointer |
| epyc-root | `handoffs/active/frontier-f3-data-flywheel.md` | pi-share-hf publish/redaction-gap reference + on-policy self-distill W3 variant |
| epyc-root | `handoffs/active/inference-acceleration-index.md` | pointer annotation + DFlare≠DFlash note |

## Results / key findings

- **Highest-value actionable**: intake-740 FR-Spec MTP vocab-trim — pull-able (`avifenesh/llama.cpp@047bfa508`), lossless at temp=0, on `qwen35.cpp`; but −85% draft-head kernel → only +1-3% e2e (BW-bound) and rides #22673 (our EAGLE3 is an inert stub) — measure before adopting.
- **DSpark/DeepSpec (intake-737/738)**: on-branch but every number vendor-unreproduced; adaptive-verify-depth scheduler is GPU-concurrency-specific → CPU-inert; gate any port on measured α (gemma4 MTP already ~77% saturated → low headroom).
- **V4-Pro-DSpark (intake-739)**: do NOT port (1.6T MoE, unsupported `deepseek4`); FP4/FP8-mixed + on-policy-distill are references only.
- **Tabular FMs (734/735/743/744/745)**: parked for the routing head — double-gated on the fable5 routing-freeze lift AND MI210/ROCm; TabICL (cred-5) → offline-only bake-off first.
- Five cross-cutting conflicts baked into the edits: EAGLE-3 watch now date-due · FR-Spec/inert-EAGLE3-stub · DFlare≠closed-DFlash · self-distill kept MI210-gated (not DGX-Spark) · stale "174K" routing figure flagged.

## Deferred work

- **Wiki compilation deferred**: `compile_sources.py` shows new sources (13 handoff-active + 4 progress), but a parallel session is actively writing today's progress/handoffs — a full wiki compile now would ingest in-flight, uncommitted work. Defer to a clean-window compile.
- **intake-750 orphaned guide**: awaiting the correct source URL from the operator to re-key + re-run a clean single-source intake.
- All Phase-4 handoff proposals beyond the 9 applied edits remain as `OPERATOR-REVIEW` items inside the intake entries' `recommended_actions`.

## Artifacts / backups
- raid0 scratch: `/mnt/raid0/llm/scratch/intake-2026-07-02/` (pre-append + pre-handoffs-updated index backups, `inner.json`, appender).

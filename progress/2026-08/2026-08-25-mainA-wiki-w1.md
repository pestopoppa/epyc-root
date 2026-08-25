# 2026-08-25 — mainA: wiki compile w1 (routing/serving) — preparation only

**Session**: mainA subagent (wiki compile W1, per the wrap-up wiki sweep)
**Scope**: prepare exact markdown updates for three wiki pages — cost-aware-routing.md,
routing-intelligence.md, inference-serving.md — from 19 drifted sources. Zero wiki edits, zero
commits (main thread applies); only output is `/tmp/wiki-w1.md` + this shard + agent log.

## Sources read (19)

optical-context-compression.md (OCC-2 record), x-mas-text-routing.md, reasoning-effort-levels.md,
qwen-chat-template-evaluation.md, qwen38-27b-replace-qwen36.md, stack-lineup-dossier-2026-07-23.md,
standardized-stack-update-pipeline-finalization.md, bulk-inference-campaign.md,
dynamic-stack-concurrency.md, shape-keyed-contention-gating.md,
mi210-big-model-and-acceleration-roadmap.md, numa-topology-cutover-resume-20260730.md,
reboot-gated-inventory-and-staging.md, repl-turn-efficiency.md, optillm-test-time-techniques.md,
progress 2026-08-21 / 2026-08-23 / 2026-08-23-root / 2026-08-24, plus git-diff review of the
post-sweep commits (0729357b, 30935e02, 03ebdff5, c9121e7f, a9b02275, 916d1061, a520cb0e, d2a3250b)
and progress 2026-08-25-mainA-rtg53.md / 2026-08-25-unattributed.md.

## What is new (vs each page's Last compiled)

- **cost-aware-routing.md (compiled 2026-08-16)**: OCC-2 provider image-billing asymmetry record
  (external, time-pinned, staleness demonstrated via Anthropic tile-model drift); E-7 certification
  stamp extended to (model, quant, kernel_era, template_sha) + enforced validator; kernel-era
  staleness correction (v8 field → v9, structural enforcement); CT-5c 16K native-think verdict
  amendment (tied at fair budget; 4K deficit was truncation); v9 lacks `--reasoning-budget`.
- **routing-intelligence.md (compiled 2026-08-16)**: OP-21 overlap re-bench + demotion
  (1.121 borderline vs 1.360 disjoint control; 1.89 allow falsified for overlap shape); marker
  polarity REFUSE + matrix-truncation + host-health fixes; ROUTE-A1 seam never-co-place
  verification; SC19 contention-capture write side wired; X-MAS current-runtime CORRECTION
  (shadow, not enforce — the page's 2026-07-04 enforce text is stale vs current config);
  NIB2-57a bilinear-scorer fabricated-tps removal.
- **inference-serving.md (compiled 2026-08-24)**: seam verification completing the ROUTE-A1
  overlap story (re-place when possible, refuse when not; 45s budget vs 1.4s control); NUMA P0-1
  CLOSED 2026-08-24 (derived-priors `cpu_shape_class: full`; PROMOTION_GATE_TARGETS 196/0; full
  suite 16/12526; no source edits — closes the 2026-08-11 IN-PROGRESS item).

## Deliberate exclusions

CT-9/CT-DEPLOY/CT-1/CT-1b/CT-3/CT-7 and Q38-T5/T6 already compiled on inference-serving; the
dynamic-stack-concurrency H20/H21/#25592 material already compiled; mi210 roadmap wave-2 (GDN-2,
#26001, G15) is kernel research not material to these pages; bulk-inference-campaign,
repl-turn-efficiency, optillm deep-dive and x-mas-text-routing drifted only via citation redirects
(0729357b) with zero new findings; progress 2026-08-21/23-root/24 not material (dashboard
governance, containment guard, benchmark protocols).

## Deliverables

- `/tmp/wiki-w1.md` — full prepared updates (exact markdown, header lines, insertion points,
  per-page source counts, exclusions) for the main thread to apply.

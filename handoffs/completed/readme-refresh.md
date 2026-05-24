# README Refresh + Autopilot Performance Plots

**Status**: ✅ COMPLETE 2026-05-24 — un-gated from the AR-3≥100 trigger after operator surfaced GitHub-discoverability as a strictly stronger reason than richer plots. All 3 owned READMEs rewritten in a Karpathy-style discoverability-first shape: front-and-center Knowledge Base section linking `wiki/INDEX.md`, `research/deep-dives/`, `research/intake_index.yaml`, `handoffs/active/master-handoff-index.md`; recent-results table (last 60d); current production stack table reflecting Qwen3.6/gemma-4/architect_coding-retired post-2026-05 consolidation; live AutoPilot trial count (513). Staleness check added to `/wrap-up` skill via `.claude/skills/project-wiki/scripts/check_readme_freshness.py` (flags READMEs >60d uncommitted OR missing `wiki/`/`research/` links). **Plot refresh** still deferred — committed plots are a 2026-04-15 snapshot at trial 192; refresh after autopilot restart accumulates trials past 600 with current model stack. See [progress/2026-05/2026-05-24.md](../../progress/2026-05/2026-05-24.md) Session 3.

**Historical status**: READY (waiting for AR-3 to reach 100+ trials for richer data)
**Created**: 2026-04-14
**Priority**: LOW (documentation, non-blocking)
**Categories**: documentation, governance

---

## Problem

All 3 repo READMEs last updated 2026-03-03 — over 5 weeks stale. Missing:
- v3 binary swap and speed improvements (coder +101%, REAP +50%)
- Bulk inference campaign results (Packages A-F)
- AM KV compaction (native llama.cpp endpoint)
- Autopilot/AR-3 progress with performance plots
- Model stack changes (architect_general 235B→122B)
- 39-sentinel expanded eval pool
- Web search infrastructure (Brave fallback)
- Context folding Phase 2a/2b results

## Tasks

1. **epyc-root README**: Update project overview, repo map, current capabilities, link to autopilot plots
2. **epyc-orchestrator README**: Add autopilot performance plots (per_suite_quality, hypervolume_trend, trial_timeline), model stack diagram, feature flag summary, routing architecture
3. **epyc-inference-research README**: Update benchmark suite table (30+ suites), eval methodology, question pool stats
4. **Autopilot plots in repo**: Commit snapshot of plots at milestone (100+ trials) to `docs/autopilot/` — not continuous, just milestone snapshots

## When to Execute

After AR-3 reaches 100+ trials with stable hypervolume. The plots will show a meaningful optimization curve. Current: trial 59, HV=57.3.

## Reference

Karpathy's autoresearch README pattern: prominent performance plot at top, brief description of methodology, key metrics table.

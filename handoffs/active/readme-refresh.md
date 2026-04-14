# README Refresh + Autopilot Performance Plots

**Status**: READY (waiting for AR-3 to reach 100+ trials for richer data)
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

# 2026-11-24 — workspace-f2 (RTG-22 non-inference)

## Kernel R&D dashboard (/loop)
- **Bandwidth surfaces unified** (earlier today, see BW-SURFACES-UNIFIED) and **wired into the AK loop**: planner BW-SURFACES block, per-surface seeds file 26 (committed, not installed under the AK hold), KEEP stale-marking with spec-target fallback (research `a116fafd5`, `7382073e1`; root `aac305249` D9-acked).
- **Two-column operator redesign** (root `adccea377`, operator-approved): health strip, headline, needs-you, run queue, serving gate, bandwidth surfaces, outcomes; agent detail collapsed.
- **Live loop flowchart restored to the main view** on operator request — full window width (operator: chart too small), items/glance below. Flow contract `scripts/coordination/akloop/flow_status.py` (D9-acked, root `1c5782858`) gains a hypothesis-inbox stage, a bandwidth-census stage (ak_runend step 4) with feedback edge to the planner, a fail-closed `held` state for the AI lanes under the loop-launch hold, and subtitles for the week's AK upgrades (NUMA-bound quarter builds, NPLAN pairs + futility looks, keep-path timing, crash/vacuous failclass, hand-back auto-stamp).
- **Root cause, producer change not served:** the hub imports flow_status once; the supervisor restarts only on `dashboard/*.py`. Fix: `server._akflow_module` reloads on mtime; supervisor stale-source scan includes `scripts/coordination/akloop` (effective at next supervisor start).
- **Spool pollution found, routed to Pipeline Management:** e2e fixtures (`cand-akm-e2e-keep-*`, 98 files) in the live akchain spool inflated the candidate count. Fixed by pipeline-mgmt in research `0403f49a7` (AKCHAIN_SPOOL + autouse conftest, files quarantined not deleted). Verified: live candidate count 0.

## Census
- `census_extract.cpu_config`: `-t 96` → `full-host` (520 GB/s) for AutoKernel's ak-c21-census-refresh-cpu row (research `e271815dd`).

## Open (gated)
- BW-SURF-CPU-STEP, BW-SURF-FLASHNEXT-CLASSES — gated on AutoKernel C21 rows.
- ETA / operator_actionable fields from pipeline-mgmt — the page already consumes both when present.

# ATTESTATION — Generated Running-State Report

**Status**: COMPLETE — W1-W4 branch-ready; awaiting merge/deploy to live orchestrator clone
**Created**: 2026-06-12
**Priority**: HIGH — independent of other fable5 tracks; highest trust-per-effort; ~3–4 days total (consolidation of existing ad-hoc checks, not invention)
**Spec**: [fable5-findings-04-impl-plan.md](../active/fable5-findings-04-impl-plan.md) §B
**Related**: [routing-truth-restoration.md](../active/routing-truth-restoration.md) (sibling handoff, owns the `GET /config/attest` flags endpoint W2 consumes); [frontier-f4-continuity-backup.md](../active/frontier-f4-continuity-backup.md) (backup-age + unpushed-commit checks ride this artifact); [MEASUREMENT.md](../../MEASUREMENT.md) (this artifact is the `attest <id>` referent in the claim grammar)

## Why

The system cannot currently prove what is running: wrong-libllama RUNPATH
incidents, 1-of-6-worker flag drift, live-affinity vs NUMA_CONFIG mismatches,
and index-vs-reality rot were each caught ad-hoc, after damage. The spec
consolidates those scattered checks into one generated report —
`orchestration/attestation/latest.{json,md}` — so every trial, bench claim,
and safety-gate decision can cite a machine-checked snapshot of running state.

## Waypoints

- [x] **W1 — generator + processes section** (~1 day): branch-ready in `epyc-orchestrator` worktree `/mnt/raid0/llm/tmp/attestation-worktree`, branch `feat/running-state-attestation`, commit `aee2ae9` (`Add running-state attestation report`). Added `scripts/attest/generate_attestation.py`, tests, and live `orchestration/attestation/latest.{json,md}`. The live artifact generated 2026-06-12 reports 34 relevant processes (28 `llama_server`, 1 orchestrator API, 2 AutoPilot, 1 OCR, 1 whisper, 1 MCP), all dynamic-link checks `ok`; the false earlyoom `llama-server` text match was fixed. Remaining live drift surfaced by W1: 13 active llama-server ports lack a registry match (`8185`, `8285`, `8385`, `8485`, `8187`, `8287`, `8387`, `8487`, `8090`, `8091`, `8093`, `8094`, `8095`).
- [x] **W2 — flags + per-role serving config** (~1 day): branch-ready in the same worktree at commit `5fc1b63` (`Extend attestation with flags and serving config`). Schema v2 now polls `GET /config/attest` with closed connections, reads sampled worker env, parses per-role llama-server serving flags from `/proc/<pid>/cmdline`, and compares live process/task affinity against `scripts/server/stack_numa.py` `NUMA_CONFIG`. Live run generated 2026-06-12T21:20:59Z: 6/6 API workers sampled, zero heterogeneous flags, zero NUMA mismatches after task-level affinity union, 48 declared-production flag diffs across 8 flags (`langgraph_*`, `ure_uncertainty_shadow_log`) caused by live legacy env/source overrides, plus the 13 registry-unmatched active llama-server ports from W1.
- [x] **W3 — eval-instrument + drift sections** (~half day): branch-ready at commit `d04e364` (`Add attestation eval instrument and drift checks`). Schema v3 records instrument-era/sentinel file hashes, `AUTOPILOT_TOOL_SENTINELS` env presence for AutoPilot/API processes, and GitNexus freshness for root/orchestrator/research/llama. Live run generated 2026-06-12T21:27:12Z: all four instrument/sentinel files exist with hashes, but `AUTOPILOT_TOOL_SENTINELS` is missing from the API parent and both AutoPilot processes; GitNexus reports `epyc-orchestrator` main stale (`594cfb5` indexed vs `2e253e9` current); HTTP flag sampling reached 5/6 uvicorn workers despite six worker processes existing.
- [x] **W4 — cadence + consumers** (~1 day): branch-ready at commit `bb28a28` (`Wire running-state attestation consumers`) plus root cadence hook in `scripts/nightshift/run_wrapper.sh`. Schema v4 records a `trigger` field; `scripts/server/stack_commands.py` writes best-effort snapshots after successful stack start/reload; root nightshift refreshes the artifact when older than 4h; AutoPilot enables `AUTOPILOT_ATTESTATION_REQUIRED` in `run_loop`, records before/after attestation fingerprints in trial details, treats stale/missing attestation as `exogenous_attestation_stale`, and treats artifact changes during a trial as `exogenous_attestation_changed`. Existing `exogenous_cache_flush` now also flows through the shared learning-exclusion policy. Live v4 run generated 2026-06-12T21:40:45Z with trigger `manual_w4_validation`: 34 relevant processes, 6/6 API workers sampled, zero flag heterogeneity, 48 declared-production flag diffs, missing `AUTOPILOT_TOOL_SENTINELS` in API/AutoPilot processes, stale main orchestrator GitNexus index, and 13 registry-unmatched active llama-server ports.

## Gates & pitfalls

- W2's flag section depends on the per-worker attestation endpoint owned by `routing-truth-restoration.md` — build W1/W3 first if that lands late; do not re-implement the endpoint here.
- Live affinity must be read from `/proc/<pid>/status`, never inferred from topology_hash — intent-only certification is the exact failure mode this artifact exists to close (`feedback_verify_live_affinity_not_just_topology_hash`).
- The generator must be read-only against the running stack — no probes that perturb inference (no test completions outside the canned W4 path).
- Frontier F4's backup-age + unpushed-commit checks attach to this artifact (its W1/W3) — leave a named section slot rather than letting F4 fork a second report.
- Sources already exist as scattered runbook checks; consolidate them, don't rewrite them — drift between this generator and the originals would create two truths.

## Reporting

Completed 2026-06-12. Any number cited follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.

# ATTESTATION — Generated Running-State Report

**Status**: SPEC'D, not started (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: HIGH — independent of other fable5 tracks; highest trust-per-effort; ~3–4 days total (consolidation of existing ad-hoc checks, not invention)
**Spec**: [fable5-findings-04-impl-plan.md](fable5-findings-04-impl-plan.md) §B — read before claiming any waypoint
**Related**: `routing-truth-restoration.md` (sibling handoff, owns the `GET /config/attest` flags endpoint W2 consumes); [frontier-f4-continuity-backup.md](frontier-f4-continuity-backup.md) (backup-age + unpushed-commit checks ride this artifact); [MEASUREMENT.md](../../MEASUREMENT.md) (this artifact is the `attest <id>` referent in the claim grammar)

## Why

The system cannot currently prove what is running: wrong-libllama RUNPATH
incidents, 1-of-6-worker flag drift, live-affinity vs NUMA_CONFIG mismatches,
and index-vs-reality rot were each caught ad-hoc, after damage. The spec
consolidates those scattered checks into one generated report —
`orchestration/attestation/latest.{json,md}` — so every trial, bench claim,
and safety-gate decision can cite a machine-checked snapshot of running state.

## Waypoints

- [ ] **W1 — generator + processes section** (~1 day): `scripts/attest/generate_attestation.py` (epyc-orchestrator) emitting `orchestration/attestation/latest.json` + rendered `.md`; section 1 per spec §B.1 — every llama-server/API/service PID with start time, binary path, binary sha + RUNPATH-resolution check (`readelf -d`), matched against its registry entry. Acceptance: artifact regenerates idempotently and flags a deliberately mis-resolved binary.
- [ ] **W2 — flags + per-role serving config** (~1 day): §B.2 per-worker flag 3-way diff (intent / env / live via `GET /config/attest` ×N — blocked until the sibling handoff lands the endpoint) + §B.3 per-role config from `/proc/<pid>/cmdline` (model inode + sha-prefix, quant, spec-dec flags, KV quant) and live `Cpus_allowed` vs NUMA_CONFIG intent. Acceptance: an injected env/flag mismatch and an affinity mismatch both surface as diffs.
- [ ] **W3 — eval-instrument + drift sections** (~half day): §B.4 (core version, sentinel hashes, tool-secret freshness, `AUTOPILOT_TOOL_SENTINELS` in both autopilot and orchestrator envs) + §B.5 (registry-vs-running diff, index-vs-reality spot checks). Acceptance: a stale sentinel and a stale index status row are each detected.
- [ ] **W4 — cadence + consumers** (~1 day): generate on stack start, on reload, and 4-hourly via existing nightshift/cron infra; autopilot safety gate reads `latest.json` age as a trial-trust precondition; trials spanning an attestation change auto-tagged `exogenous_*` (classification machinery exists). Acceptance: one nightshift cycle produces fresh artifacts and a spanning trial is auto-excluded in the journal.

## Gates & pitfalls

- W2's flag section depends on the per-worker attestation endpoint owned by `routing-truth-restoration.md` — build W1/W3 first if that lands late; do not re-implement the endpoint here.
- Live affinity must be read from `/proc/<pid>/status`, never inferred from topology_hash — intent-only certification is the exact failure mode this artifact exists to close (`feedback_verify_live_affinity_not_just_topology_hash`).
- The generator must be read-only against the running stack — no probes that perturb inference (no test completions outside the canned W4 path).
- Frontier F4's backup-age + unpushed-commit checks attach to this artifact (its W1/W3) — leave a named section slot rather than letting F4 fork a second report.
- Sources already exist as scattered runbook checks; consolidate them, don't rewrite them — drift between this generator and the originals would create two truths.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; any number cited follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.

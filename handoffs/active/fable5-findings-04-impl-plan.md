# Fable 5 findings 04 — IMPLEMENTATION PLAN: invariant interfaces, capability registry, index migration

**Date**: 2026-06-12 (refinement pass, operator-requested). **Companion to**: `fable5-findings-04-northstar-portfolio-indices.md` and `fable5-proposed-master-index-rewrite.md`. This doc makes the five invariant interfaces and the index reorg buildable. (Interface 1, the measurement ledger, is fully specified in `fable5-findings-01-impl-plan.md`; interface 2, descriptors, in `fable5-findings-02-impl-plan.md` Phase 2. This doc covers 3–5 + the doc layer.)

---

## A. `MEASUREMENT.md` — the system-wide instrument constitution (interface: every number cites its protocol)

**Location**: repo root of epyc-root (sibling of CLAUDE.md), referenced from CLAUDE.md. **Authoring**: human-owned, change-controlled (PR-style review even solo — it is the trust anchor). **Skeleton**:
1. **Canonical throughput protocols** — lift CPU20 + `feedback_canonical_baseline_protocol` + the codified-recipe rule (`bench_canonical.sh` / `canonical_recipe.py` from the 2026-05-28 roofline session — already built, make them the only sanctioned entry) → name each protocol (`tps-solo-96t`, `tps-quarter-aggregate`, `tps-batch-eval`), its env stack, rep counts (≥5 for sub-5% claims, ≥10 for ≤2%), host-health preconditions (uptime/THP/governor), and the binary-resolution check (the RUNPATH incident guard, already a test).
2. **Quality protocols** — the eval-tower instrument card: core version, n, quantum, MDE, sequential-confirmation rule, promotion-eval spec (findings-01 Phase 2), suite-health status table (auto-generated section).
3. **Claim grammar** — a claim is `(metric, protocol-id, n/reps, date, host-state attestation id)`; anything else is an observation, not a claim. Indices and handoffs SHOULD link claims; the research-intake credibility fields already half-do this.
4. **GPU canonical protocol** (placeholder section to be written BEFORE MI210 install — findings-03 H2): warm/cold policy, rocm-smi state capture, per-GCD pinning, the same rep policy.
**Enforcement hooks**: (a) a validator `scripts/validate/check_claims_grammar.sh` greps new handoff/index diffs for bare "X t/s"/"+N%" without a protocol tag — warn-only first month; (b) autopilot journal rows already carry `speed_metric_mode` — extend to `protocol_id`.

## B. ATTESTATION — generated running-state report (interface: the system can prove what is on)

**Generator**: `scripts/attest/generate_attestation.py` (epyc-orchestrator), output `orchestration/attestation/latest.json` + rendered `.md`. Sections + sources:
1. **Processes**: every llama-server / API / service PID with start time, binary path, **binary sha + RUNPATH-resolution check** (`readelf -d` — the 2026-05-28 wrong-libllama incident class), and the registry entry it should match.
2. **Flags**: per-uvicorn-worker flag state via `GET /config/attest` ×N (findings-02 impl 0.2) + env-block intent → 3-way diff (intent / env / live).
3. **Per-role serving config**: model file (inode + sha-prefix), quant, spec-dec flags actually on the command line (`/proc/<pid>/cmdline`), KV quant, NUMA mask actually applied (`/proc/<pid>/status` Cpus_allowed vs NUMA_CONFIG intent — the live-affinity lesson from `feedback_verify_live_affinity_not_just_topology_hash`).
4. **Eval instrument**: core version, sentinel file hashes, tool-secret freshness, `AUTOPILOT_TOOL_SENTINELS` presence in both autopilot and orchestrator envs (the deploy-window class).
5. **Drift section**: registry-vs-running diff; index-vs-reality spot checks (e.g., the F5/autopilot status row vs live PID).
**Cadence**: on stack start, on reload, and 4-hourly via the existing nightshift/cron infra; autopilot's safety gate may read `latest.json` age as a precondition for trusting a trial (ties into `exogenous_*` classification — a trial spanning an attestation change is auto-tagged).
**Effort**: ~3–4 days; nearly all sources already exist as ad-hoc checks scattered across runbooks — this is consolidation, not invention.

## C. Capability registry + promotion mechanics (interface: backlog → autopilot-actionable is a state transition, not a rewrite)

**C.1 The registry** — `orchestration/capability_registry.yaml`, one row per lever:
```yaml
- id: moe_spec_budget
  kind: env|flag|numeric|prompt|registry-field|restart-class
  surface: LLAMA_ARG_MOE_SPEC_BUDGET          # how it is applied
  applicator: role_restart                     # config_post | env_hotswap | role_restart | stack_restart
  range: {type: int, min: 0, max: 128}
  roles: [architect_general, ...]
  evidence: {measured: "+7.3-15.2% pp32", protocol: tps-solo-96t, source: moe-spec handoff}
  risk: medium ; actionable_by: autopilot|operator|gated:<condition>
  handoff: moe-spec-cpu-spec-dec-integration.md
```
Compiled into the planner's Action-Availability section (replacing the hand-maintained denylist in program.md with *generated* allow/deny + reasons) and into the index `A-by` column (one source of truth for both).
**C.2 The missing applicator — safe role restart.** The single blocker for exposing every measured speed lever. Design (uses only existing machinery): `config_applicator.restart_role(role, env_overrides, registry_overrides)` → (1) pause autopilot dispatch via the existing contention/queue path (background class already queues), (2) `orchestrator_stack.py reload <role>` (exists; memory: use it for ALL lifecycle), (3) health gate = existing `wait_for_health` + one canned smoke completion, (4) on fail → relaunch with prior config (the registry is the rollback record), (5) journal an `exogenous_role_restart` boundary so trials spanning it are auto-excluded (the classification machinery exists). Restart-class experiments are **batched** by the planner (one restart, several trials, restore) — the trial protocol lives in the capability row, enforced by the dispatch gate.
**C.3 Promotion workflow** (the recurring activity findings-04 said nobody owns): a capability moves `operator → autopilot` when: descriptor/applicator wired + range validated + a kill condition written + one shadowed trial passes attestation. Track as a standing monthly pass over the registry (the 2026-05-20 expansion, institutionalized). First cohort (from the audit's top-10): `moe_spec_budget`, per-role `enable_thinking`, EA compaction profiles (S8/S9), draft_max/p_split where spec-dec is on, edit-transaction auto-routing.
**C.4 Sequencing guard**: C is gated on findings-01 Phase 1 (the instrument must certify effects before the optimizer gets bigger levers) — same gate as the index rewrite's A15 row.

## D. Workload model (interface 5 — smallest of the five, biggest definitional payoff)

`orchestration/workload_model.yaml`: declared traffic classes `{interactive, eval_batch, campaign}` with per-class: expected volume share (seed from the 2026-06-11 tally: forced-eval 23%, frontdoor-interactive ~majority of the rest), latency/throughput SLO, serving class (findings-03 §3: exclusive-lock vs continuous-batch instance sets), and priority under contention (the contention gate already has priority classes — this names them). Consumers: routing ω (cost weight per class), placement (which instance set), autopilot (eval traffic self-labels `eval_batch`), and the quarterly DAR-1 replay (regret is computed per class, which is what makes "routing optimality" finally well-defined). Effort: 1 day to write + small request-tagging change (`request_context` already carries priority class — extend to workload class).

## E. Index migration mechanics (executing the rewrite)

1. **One-shot migration script** `scripts/maintenance/migrate_master_index.py`: parse the current 66-row queue; rows matching terminal markers (`✅|DONE|CLOSED|DEPRECATED|~~`) → emit a `handoffs/completed/master-index-terminal-ledger-2026-06.md` (id, item, outcome, links) + drop; live rows → re-emit in the NOW/ACTIVE/GATED/HW tiers from `fable5-proposed-master-index-rewrite.md` (manual triage of ~10 ambiguous rows flagged by the script). Header narrative → `progress/2026-06/master-index-header-archive.md`.
2. **Freshness with teeth**: extend `scripts/validate/check_handoff_freshness.sh` to also lint the master index (any row >14d untouched without `gated:` tag → exit 2) and wire it into the pre-commit hook set (hooks infra exists).
3. **Per-index slimming** (one pass each, biggest first): inference-acceleration (move 14 intake appendices → intake index links; add the missing checkbox/dependency/reporting sections), cpu (move the 330 chronology lines above the task list → progress), routing (prune the ~78 checked boxes → completed ledger). Pipeline index is the template.
4. **`A-by` column backfill** from the capability registry (C.1) — script, not hand-edit, so the two never diverge.
5. **Reporting-rule update** in CLAUDE.md §Handoff Workflow: add the delete-on-complete rule and the claims grammar pointer (single paragraph).

## Effort & order
| Item | Effort | Notes |
|---|---|---|
| E index migration | 1–2 days | do first — it is the coordination surface for everything else |
| B attestation | 3–4 days | independent; highest trust-per-effort |
| A MEASUREMENT.md | 2 days (assembly) | content mostly exists |
| D workload model | 1 day | unlocks definitions used by routing/serving plans |
| C registry + applicator | ~1 week | gated on findings-01 Phase 1 |

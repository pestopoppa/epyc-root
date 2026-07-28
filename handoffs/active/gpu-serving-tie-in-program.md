# GPU Serving Tie-In Program — one fabric, two devices

**Status**: ACTIVE — operator-ratified strategy (consensus session 2026-07-28); Phase 0 in progress
**Created**: 2026-07-28
**Priority**: HIGHEST — this is the post-campaign program spine; the 2-week MI210 bench era
(np×context grids, RAG-at-depth, kernel v8, region-lock fabric) was know-how collection for exactly this
**Owner**: Codex long-horizon session executes; Claude session coordinates; operator holds all named gates
**Parent index**: [master-handoff-index.md](master-handoff-index.md)
**Related**: [batched-decode-measurement.md](batched-decode-measurement.md) (E5) ·
[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) (resume) ·
[heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) (fabric) ·
[architect-model-selection-bench.md](architect-model-selection-bench.md) (Phase-2 tool-use) ·
[frontier-f1-real-task-corpus.md](frontier-f1-real-task-corpus.md) (routing grounding) ·
[reviewer-control-plane-index.md](reviewer-control-plane-index.md) (co-critic plumbing) ·
`docs/runbooks/vision-escalation-minicpmo-promotion.md` (the State-A/B lane choreography template)

## Vision (ratified)

Wire the MI210 into the orchestration stack as a **serving resource** with a **role-agnostic
GPU-resident lane**, then let AutoPilot explore the new surfaces through **typed, pre-validated
parameterizations only**. CPU keeps frontdoor + worker_general on NUMA-optimal quarters; the GPU
tenant (~50 t/s single-stream ≈ frontdoor-CPU speed) makes CPU↔GPU escalation/delegation chains
latency-cliff-free. **The engineering deliverable is the slot, not the tenant** — tenancy is registry
data, swappable via the vision-runbook State-A/State-B choreography; every strategic pivot is a
config change with a rehearsed rollback, never a rebuild.

## Ratified decisions (2026-07-28 consensus — do not relitigate without new evidence)

| # | Decision |
|---|---|
| D1 | **Elastic-duty policy = batch-shedding primary**: under CPU stress, worker_general-class *batched* work sheds to the GPU lane's np-batching (~135 t/s aggregate); frontdoor stays single-model on CPU. Frontdoor-overflow-via-GPU exists only as an explicit, flagged, telemetered degraded mode. Priority-ordered lane admission: **escalations > distillation backfill > shed batch > (degraded) frontdoor overflow**. *Design provision now; implementation not required until after lane hardening.* |
| D2 | **Phase-2 tenant set**: dense 27B (28.7GB, stock-vs-FF decided by bake-off) + MiniCPM-o (~7GB, executes the parked vision-escalation runbook) + whisper (~1.6GB) ≈ **37GB resident, ~27GB dynamic**. Vision-gen (SD) deferred as optional later tenant. |
| D3 | **Shadow-only invariant**: registry stays frozen; `coder_escalation` stays A4-bound; the GPU lane serves **no production traffic** until Phase-3 bake-off evidence + operator three-gates sign-off. |
| D4 | **E8 baseline ratification precedes autopilot resume AND the reboot.** One human signature over the consolidated evidence bundle: `artifacts/operator/ratify_and_apply_e8_quality_baseline_v4_20260727.sh` (Codex finalizer is producing the apply-ready bundle; operator runs it when presented). |
| D5 | **kv_compaction stays an autopilot lever.** The 2026-07-28 fix (`24fa1399`) was contained: uncompactable-role 500s ("nothing to compact", e.g. idle ingest slots) are now benign per-role skips; the knobs (`kv.keep_ratio/keep_first/n_future`) remain **runtime-applied via `compress_slot()` — no relaunch needed**. The pre-agreed disable-fallback was contingency only and is NOT active. |
| D6 | **MTP on the GPU lane is launch-bound, not per-request** (verified in v8 `server-context.cpp` — `params.speculative` is global; no request-level override). Mode toggle = drained lane relaunch (~1–2 min at a boundary, State-A/B choreography). Default: **MTP OFF** for the escalation-dominant duty mix (MTP measured net-negative single-stream deep-context); revisit only if shed-batch becomes the dominant duty. |
| D7 | **Laguna deprecated + DELETED** (2026-07-28, 108G freed; re-downloadable). **FG-2V completed TERMINAL before deletion** (2026-07-28: +1/8 focused solve, 14/53→15/53 projected — coder case stays closed); **FG-5 is closed-by-weights-deletion** (reopen requires an operator decision + re-download; no task stays filed). **TC deprecated; deletion GATED on operator review of G3 scaffold results** (see P0-6). Note: TC's clean no-think SWE validation landed at **21/40 (52.5%)** — second to stock; recorded, does not change the verdict. **FF retained** as the bake-off alternative to stock-27B (identical 29GB footprint; −40% tokens/solve at statistically-tied SWE). |
| D8 | **Teacher policy — IMPLEMENTED** (orchestrator `c4196c28`, 2026-07-28, other session): default = Claude CLI teacher with a one-env-line shift to local. Plan of record unchanged: migrate to the GPU tenant after Phase 3 (distillation rides the lane's continuous batching alongside escalations); CPU-122B reserved for operator-scheduled quiet-window high-value distillation and special/cross-family critic duty (the autopilot-planner claude↔codex failover pattern, replicated locally). |
| D9 | **122B architect stays** (CPU, 20–26 t/s viable home; idle cost = abundant RAM). Retained duties: depth-insurance pending Phase-5 verdict, quiet-window teacher, cross-family second-opinion critic, GPU-outage failover. |
| D10 | **Explicit declines**: no 27B-Q4-CPU bench (27B's home is the GPU; decision made); the E1 dense-control 1.1 t/s anomaly is NOT investigated (reopen only if a future decision depends on dense-CPU throughput). v9 note filed: the v8 compact endpoint conflates empty-slot with failure (blanket 500) — fix at v9, never patch frozen v8; the orchestrator marker-string match is v8-contract-coupled. |

## Prioritized task list

### Phase 0 — pre-reboot (now)
- [x] Autopilot resume preconditions fixed: tiny-n hard-gate guard (`4d329002`) + kv_compaction per-role skip (`24fa1399`), tested, pushed ✅ 2026-07-28
- [x] Laguna weights deleted (108G freed; in-use guard verified) ✅ 2026-07-28
- [ ] **P0-1 (operator)** — run the E8 ratification when Codex presents the apply-ready bundle (D4). BEFORE reboot.
- [ ] **P0-2 (Codex, inference)** — FG-4b canonical A4 CPU re-anchor: **q2 is FREE — verified via `region-lock status` 2026-07-28** (locks are flock-based and died with their holders; the on-disk lock files are harmless vestiges — do NOT delete them). Just run `bench_canonical.sh` per protocol; refresh the stale 24.3 t/s registry row via the canonical path only.
- [ ] **P0-3 (split — updated 15:10Z)** — E5 prep: **Codex independently landed the W0 offline-score producer, trimmed-window fail-close gate, and Gemma response-capture gate (~15:04Z, before the division-of-labor relay)** — that work is accepted as-is, do not redo. Claude's subagent is re-scoped to the remainder only: C1 (GGML_IQK per-cell manifest/attestation), C3 (multi-server harness + cell-manifest affinity gate), W1–W4 cell manifests + validator.
- [ ] **P0-7 (THIS session)** — Phase-2 lane scaffolding started early (non-inference): flag-gated default-off launch-layer code + ready-to-apply registry PROPOSAL (registry itself stays FROZEN per D3 — no live edits), np_ceiling policy table from the measured grids, lane spec with D1 admission order. Subagent dispatched 2026-07-28.
- [x] **P0-4** — registry deprecation check: VERIFIED 2026-07-28 that neither Laguna nor ThinkingCap was ever registered in the master or lean registry (bench-only candidates; no rows exist to annotate). Deprecation of record = D7 here + the architect-bench handoff status. ✅ 2026-07-28
- [ ] **P0-5** — relay sent to Codex pointing at this handoff as program authority.
- [ ] **P0-6 (guarded, operator-gated)** — delete TC weights (28G) only after **G3 scaffold-generator results are back AND the operator has reviewed them** (off-chance of idea revision) AND `lsof` empty on `/mnt/raid0/llm/models/ThinkingCap-Qwen3.6-27B-GGUF`. Not merely G3-drain.

### Phase 1 — execution window (**REBOOT NOT NEEDED** — corrected 2026-07-28)
> Discovery 2026-07-28T15:08Z: the host was rebooted ~2026-07-24; uptime is **4 days**, which **complies**
> with the P-BENCH ≤1-week host-health policy until **~2026-07-31**. The reboot-gate text in
> batched-decode-measurement.md dates from the uptime-20d era. The worker-quarter 8282/8382 locality
> concern is also moot (current lineup launched 2026-07-25, post-reboot). Urgency therefore INVERTS:
> E5 must run **before ~2026-07-31**, not after a reboot.
- [x] **P1-1** — reboot: MOOT (host rebooted 2026-07-24; both reboot motivations dissolved) ✅ 2026-07-28
- [ ] **P1-2 (Codex, inference)** — E5 W1–W4 runs (NUMA×batch 2D grid; decides slot-fabric (N,K) provisioning per model — the CPU half of the coupling with the GPU np×context grids). **DEADLINE: uptime window closes ~2026-07-31**; quiet-window scheduling per protocol.
- [ ] **P1-3** — AutoPilot resume on existing CPU surfaces — gated ONLY on P0-1 (E8 signature) now; preconditions ✅ (`4d329002`, `24fa1399`); fresh-reseeded routing memory learns from scratch; F1 real-task grounding applies.

### Phase 2 — GPU lane build (shadow-only per D3)
- [ ] **P2-1** — role-agnostic resident lane: registry-driven tenancy (model path + role bindings as data), launch layer per the vision-runbook pattern; region-lock/lease integration (fabric axioms; drain-at-boundary, never forcible).
- [ ] **P2-2** — tenants land: dense-27B (stock first) + MiniCPM-o (execute the parked promotion runbook §Steps 1–6) + whisper (D2).
- [ ] **P2-3** — Stage-0 hardening: deterministic smoke (fixtures, health, affinity/VRAM attestation), np_ceiling(budget) policy table from the measured grids, contention recert for host-side cores.
- [ ] **P2-4** — ONE independent adversarial instrument review of the lane (per the max-one-review-per-new-instrument contract), then run-first.
- [ ] **P2-5** — D1 design provision documented in the lane spec (admission priority order; shed-batch + degraded-overflow flags exist but may stay unimplemented/off).

### Phase 3 — shadow bake-off (eval path only, never live /chat)
- [ ] **P3-1** — arms: stock-27B vs FF, duties scored SEPARATELY: coder (escalation-shaped SWE-flavored tasks, production sampling) and co-critic (wired through reviewer-control-plane typed decisions). A4-GPU control arm runs sequentially in bench windows (co-residency impossible: 37.8GB).
- [ ] **P3-2** — tenancy decision package to operator: per-duty winner(s), token-efficiency, latency; duties may split across epochs but one resident tenant at a time.
- [ ] **P3-3 (operator)** — three-gates sign-off → coder_escalation rebind (or explicit keep-A4 verdict). First production traffic on the lane only after this.

### Phase 4 — AutoPilot on the new surface
- [ ] **P4-1** — Stage-2 typed knobs ONLY: tenant ∈ {stock, FF} + np_ceiling within measured bounds; flag-gate + strategy-store seeding pattern; fail-closed on any 5xx class. **Invariant: autopilot never touches launch plumbing, registry, or lane lifecycle.**
- [ ] **P4-2** — staged widening after N clean trials (N set at P4-1 review).

### Phase 5 — SWE-bench agentic (Phase-2 of architect-bench)
- [ ] **P5-1** — build the agentic/tool-using harness over `/mnt/raid0/llm/datasets/swe-bench-verified/` + exec-sandbox.
- [ ] **P5-2** — validate the FAIL_TO_PASS scorer on known-gold patches BEFORE any model sees it (instrument review), pin the question manifest.
- [ ] **P5-3** — run arms in windows → **the 122B's trial** (D9): keep/shrink verdict + tenancy revisit with real evidence.

## Dependency graph

```
P0-3 (E5 prep) ─▶ P1-2 (E5 runs, DEADLINE ~07-31)      P0-1 (E8 sign) ─▶ P1-3 (autopilot resume)
P0-2 (FG-4b run: q2 free, uptime-compliant — schedulable now)
P0-6 (TC delete) ◀── operator reviews G3 results
P2-1..P2-5 (lane build; parallel to Phase 1) ─▶ P3 (bake-off) ─▶ P3-3 (rebind gate) ─▶ P4 (autopilot knobs)
P2 lane stable ─▶ P5 (SWE-agentic) ─▶ 122B verdict
```

## Cross-cutting concerns

- **MEASUREMENT discipline**: every gating number needs protocol-id + attestation; bench observations
  (this program cites many) inform design but never gate promotion alone.
- **Registry frozen / three-gates**: all lineup changes are operator-signed; this handoff authorizes NONE by itself.
- **Shared-clone hygiene**: Codex + Claude sessions share trees; no wholesale `git add`, fetch-before-commit on main.
- **Run-first bias + saturation scheduling** (operator contract 2026-07-27): keep CPU and GPU lanes busy;
  boundary tokens presented only while compute is saturated.
- **v9 queue**: compact-endpoint typed responses (D10). Production v8 is FROZEN — no patches.

## Reporting

Flip checkboxes here as gates land (checkbox discipline — prose is invisible to the dashboard); record
phase completions in `progress/`; tenancy + rebind decisions get operator decision packages
(AskUserQuestion contract). On program completion, extract the lane spec to `docs/` and archive.

## Key files

- Lane template: `docs/runbooks/vision-escalation-minicpmo-promotion.md` (State-A/B choreography)
- Registry: `epyc-inference-research/orchestration/model_registry.yaml` (master; lean is compiled)
- Launch layer: `epyc-orchestrator/scripts/server/orchestrator_stack.py`, `stack_manifest.py`, `stack_numa.py`
- Grids/evidence: `epyc-inference-research/artifacts/np_context_study_v8_20260727/` (v8) + `np_context_study_20260723/` (v7) + the model-selection artifact (claude.ai/code/artifact ab8d2e24)
- Region locks: `epyc-orchestrator/scripts/region-lock` · fabric: `heterogeneous-slot-fabric-residency.md`
- E8 apply: `artifacts/operator/ratify_and_apply_e8_quality_baseline_v4_20260727.sh`

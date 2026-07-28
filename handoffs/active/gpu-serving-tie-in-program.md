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
| D4 | **E8 baseline ratification precedes autopilot resume AND the reboot.** One human signature over the consolidated evidence bundle via the **v5 consolidated wrapper** (`scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh`, orchestrator — must be the MERGED-tree version with receipt-after-CAS semantics + composite validator, hashes pinned in the presentation; see P0-1 review verdict). The v4 script reference is historical. |
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
- [ ] **P0-1 (operator)** — run the E8 ratification when Codex presents the apply-ready bundle (D4). **Wrapper review VERDICT (2026-07-28, independent read-only): FIX-FIRST — do NOT sign on the branch as pushed.** The transaction design is sound and fail-closed (validates 3× before mutating; exactly six state rows via journaled CAS with rollback; receipt minted only post-commit; touches no eras/registries/baselines/processes; strong hash-pin + confirmation-phrase procedure). Blockers, all mechanical: (1) branch tip (`575ca543`, one past `b3db2800`) is NOT self-consistent — it pins three runner files that exist only on main, and its own prepare/validator disagree on CLI args → cannot run from its own checkout; (2) 52-behind/10-ahead of main with add/add conflicts in 4 files (7 of 10 branch commits already patch-equivalent on main; only the top 3 — receipt-after-CAS redesign — are unique and are the KEEP side); (3) the branch validator cannot validate the segmented T2 resume/recovery provenance the live q2 collection is actually producing (main's can). **Required fix (Codex, owns the branch): merge its 3 newest commits onto main's composite validator, resolve the 4 conflicts keeping branch wrapper semantics + main validator, re-run the wrapper test suite, and pin the MERGED-tree hashes in the presentation.** One LOW wart: a hard-kill between six-row-review write and applier start leaves a stale review file requiring manual delete (fail-closed). Once merged + T2 terminal → SAFE-TO-SIGN.
- [ ] **P0-2 (Codex, inference)** — FG-4b canonical A4 CPU re-anchor: **q2 is FREE — verified via `region-lock status` 2026-07-28** (locks are flock-based and died with their holders; the on-disk lock files are harmless vestiges — do NOT delete them). Just run `bench_canonical.sh` per protocol; refresh the stale 24.3 t/s registry row via the canonical path only.
- [x] **P0-3 — E5 prep COMPLETE** ✅ 2026-07-28 — verification found C1/C3/W1–W4 were ALREADY implemented and committed (research `b294daa0`+, orchestrator `6a55aeed`+; batched-decode handoff checkboxes were stale — now flipped). Independent verification at committed HEAD: 105+27 targeted tests pass; all 190 pre-registered cell manifests validate; C1 attestation + C3 affinity gate proven in live W0 evidence. Codex's same-day W0 additions (offline-score producer, trimmed-window fail-close, Gemma response-capture gate) accepted. **ONE REMAINING BLOCKER (Codex, before W2): commit the uncommitted E5 files in the research tree** (modified `server_numa_np_sweep.py`+tests, untracked `e5_w0_offline_score.py`+tests, W0 run-dir score artifacts, `stage_b_prune_plan.json`) — the Gemma capture gate is a hard W2 blocker (gemma W0: 43/43 parse failures in all 10 cells without it). E5 W1–W4 is now pure inference execution (P1-2). Note: the run recipe's "host reboot" precondition in older notes is MOOT (see Phase 1).
- [x] **P0-7 — Phase-2 lane scaffolding COMPLETE** ✅ 2026-07-28 (orchestrator `cbfe0cde`+`f00c9557`+`c3ce44aa`, reviewed + pushed) — lane spec `docs/gpu-shadow-lane.md` (D1 admission order, Steps 0–7 activation choreography incl. Q1B-SMT contention recert); ready-to-apply registry PROPOSAL `docs/proposals/gpu-shadow-lane-registry-proposal.md` (role `coder_escalation_shadow`, launcher lane `gpu_shadow_lane` port 18100, tenant sha256-pinned; NOTHING applied — registry frozen per D3, launch wiring is proposal-diff-only with a zero-coupling test witness); np_ceiling policy-as-data `orchestration/gpu_shadow_lane_np_ceiling.yaml` + loader behind default-off `ORCHESTRATOR_FEATURE_GPU_SHADOW_LANE` (derived from the v8 grids; np16 saturation cap; solo 37.3GiB all-16, phase2 27GiB 16/16/16/8@32k; null=refuse); plan-only preflight probe (VRAM/KFD/binary-10107/affinity, refuses if production CPU lanes disturbed; never run this session). 112 targeted tests pass; inertness proven 3 ways. All 7 subagent interpretation calls reviewed and ACCEPTED (proposal-only launch wiring is the correct D3 reading of this item). Activation remains the operator-gated Steps 0–7 → P2-3/P2-4.
- [x] **P0-4** — registry deprecation check: VERIFIED 2026-07-28 that neither Laguna nor ThinkingCap was ever registered in the master or lean registry (bench-only candidates; no rows exist to annotate). Deprecation of record = D7 here + the architect-bench handoff status. ✅ 2026-07-28
- [ ] **P0-5** — relay sent to Codex pointing at this handoff as program authority.
- [ ] **P0-6 (guarded, operator-gated)** — delete TC weights (28G) only after **G3 scaffold-generator results are back AND the operator has reviewed them** (off-chance of idea revision) AND `lsof` empty on `/mnt/raid0/llm/models/ThinkingCap-Qwen3.6-27B-GGUF`. Not merely G3-drain.

### Phase 1 — reboot scheduled (**RECONCILED 2026-07-28 ~16:30Z** — supersedes the 15:08Z "reboot not needed" reading)
> History, kept for honesty: at 15:08Z this handoff corrected the stale uptime-20d reboot-gate text
> (host had been rebooted 2026-07-24; uptime 4d complied with P-BENCH ≤1wk until ~07-31 → deadline
> framing). At ~16:20Z the **operator SCHEDULED a host reboot** (relayed via coordinator-agent).
> That decision dissolves the deadline: uptime resets at the reboot, the one-week decision-grade
> window reopens, and `batched-decode-measurement.md:519`'s reboot-gate line is again the operative
> sequencing. Codex is rescoped to a **terminating pre-reboot set**; post-reboot work goes to a
> **NEW session**.
- [ ] **P1-1 (Codex → operator)** — pre-reboot terminating set: E8 → apply-ready ratification bundle (P0-1), FG-4b re-anchor (P0-2), commit uncommitted E5 research files (✅ done `efd0980c`) — ending in a **reboot request to the operator**, who executes the reboot (operator-only).
- [ ] **P1-2 (POST-reboot, NEW session, inference)** — E5 W1–W4 runs + the W2 focused capture smoke + R1–R4 reads (NUMA×batch 2D grid; decides slot-fabric (N,K) provisioning — the CPU half of the coupling with the GPU np×context grids). Fresh-uptime, quiet-window per protocol. No deadline — the reboot resets the window.
- [ ] **P1-3 (POST-reboot, NEW session)** — AutoPilot resume on existing CPU surfaces — gated on P0-1 (E8 signature); preconditions ✅ (`4d329002`, `24fa1399`); fresh-reseeded routing memory learns from scratch; F1 real-task grounding applies.

### Phase 2 — GPU lane build (shadow-only per D3)
- [x] **P2-1** — role-agnostic resident lane ✅ 2026-07-28 (claude-gpu-lane; orchestrator working tree, NOT pushed — shared clone, see reporting note). Tenancy-as-data `orchestration/gpu_shadow_lane_tenancy.yaml` + loader `scripts/server/gpu_shadow_lane_tenancy.py`: slot properties (device/port/host cpuset/binary pin/region claim) separated from tenant properties (path, sha, mode, duty bindings); 4 tenants (stock-27B, FF, FF-MTP, A4 bridge). Six invariants ENFORCED at load, not reviewed: state_a-only, per-tenant policy row w/ byte+sha match, shadow-only bindings rejecting production role names (D3 at the data layer), unimplemented admission classes 3–4 unbindable, `mtp: true` requires explicit `draft_n_max`, unattested hash ⇒ planning-only. **No apply path exists in the module** (D3 by absence of the function, not a flag over one); `render_registry_proposal` emits diffs only. Launch argv fully parameterised — swapping tenant/mode/port/host-slice is a data edit. Lease layer `scripts/server/gpu_shadow_lane_lease.py`: host slice → `q3` flock via the production `cpu_region_lock`, GPU → its OWN non-blocking flock (never a CPU pseudo-region, fabric axiom 1); `LaneLease` implements reclaim as quiesce-and-drain only — `at_boundary()` is the sole release path, `force_release()` raises by construction, ignored revocation surfaces as `overdue` (axiom 4 / BUS_PROTOCOL rule 8). 50 targeted tests.
- [ ] **P2-1a (NEW, discovered 2026-07-28)** — reconcile the SMT-folding helpers: `gpu_shadow_lane_lease.fold_smt_to_physical` (P2-1) and the P2-6 preflight overlap taxonomy landed the same day in parallel sessions and implement SMT folding independently. One should become the other's caller before either is relied on for a gate.
- [ ] **P2-2** — tenants land: dense-27B (stock first) + MiniCPM-o (execute the parked promotion runbook §Steps 1–6) + whisper (D2).
- [x] **P2-3 — Stage-0 hardening** ✅ 2026-07-28 (claude-gpu-lane; orchestrator working tree, NOT pushed). `scripts/server/gpu_shadow_lane_stage0.py` with three zero-inference subcommands. **smoke**: 16 deterministic checks over the committed tables + 6 recorded fixtures (`tests/fixtures/gpu_shadow_lane/`), each fixture asserted to produce its EXPECTED verdict so the negative cases prove the judges can fail; module cannot import subprocess/socket/http (AST-checked), so it is structurally incapable of touching the device. **attest**: pure parse+judge for health/`/slots`, host affinity and VRAM residency — the same functions score fixtures today and live JSON at Step 5, so no second unreviewed implementation gets written under pressure during activation. **recert**: generates the COMPLETE contention set instead of hand-listing it. np_ceiling table hardened: saturation cap now ENFORCED by the loader (was a comment); ceilings made **mode-aware** (see P2-3a); every tenant given its own row with byte+sha identity. 28 targeted tests; smoke exits 0 on the committed tables.
- [x] **P2-3a — three evidence-attribution defects found and fixed while hardening** ✅ 2026-07-28. (1) **P2-4 P1-4 confirmed and repaired**: the measured grid is the FF arm (27.74 GiB), filed under a tenant carrying stock's 26.70 GiB. Measurements moved to `qwen36_27b_ff_q8`; stock is now an explicit `derived_conservative_transfer` row with NO throughput table (capacity transfers smaller-model-ward, throughput does not transfer at all). (2) **NEW — FF-MTP is a different GGUF, not a flag**: 30,239,022,560 B / 866 tensors (851 base + 15 MTP) vs the non-MTP 29,787,701,792 B. Modelling it as a mode flag would have carried the wrong model size into every VRAM budget; it is now its own tenant. (3) **NEW — the A4 bridge grid ran MTP ON at `n_max=4`**, not off (`queue_after_thinkingcap.sh:87` → `--spec-type draft-mtp --spec-draft-n-max 4`); P0-7 filed its ceilings as if MTP-off evidence. Bridge rows moved under `mtp_on` with no mtp_off rows, so an MTP-off bridge plan correctly refuses. Consequence: **ceilings are now per-mode and a mode with no rows REFUSES rather than borrowing the other mode's frontier** — MTP measurably moves the capacity frontier (FF `np16×L32768` fits MTP-off, capacity-skips MTP-on), so the previous mode-blind table would have authorised an np16/32k launch that only ever fit without MTP. Also corrected: the launch argv emitted `--draft-mtp`, which is not a v8 flag. All grid cells re-verified against the study's own read-only aggregator; all model hashes sourced from the instrument's pre-launch identity contract.
- [x] **P2-3b — P2-4 P1-2 (SMT blindness) closed on the recert path** ✅ 2026-07-28. The lane's host slice 184-191 folds to physical cores 88-95 = region `q3`. The spec's Step-4 co-tenant list and the recert set were BOTH missing `architect_general:8083` and `worker_general:8072` — instances pinned `0-95`, which share the lane's physical cores while sharing **no literal CPU id**, so string overlap reports them disjoint. `recert_roles()` folds SMT first and classifies each hit `smt_sibling_overlap` vs `physical_core_overlap` so the previously-invisible class is visible; `docs/gpu-shadow-lane.md` §7 Step 4 rewritten with the generated command. **Scheduling consequence recorded: an idle MI210 does NOT imply a startable lane** — activation needs `q3`, held 2026-07-28T16:09Z by codex's `bench-e8-quality`, and must wait for that holder to drain at its own boundary, never be forced.
- [x] **P2-4** — independent adversarial instrument review DONE ✅ 2026-07-28: **APPROVE-WITH-FIXES**. Verified correct: np_ceiling grid fidelity (every cell re-derived from the study), KV arithmetic (GGUF header + v8 source: 16 full-attn layers, 64KiB/token f16), tenant sha256, launch-plan parity vs measured argv, inertness (default-off both modes, no production imports, guarded --apply), Step-3 additivity. Findings: P0-1 tenant role never enters the compile pipeline (launcher_only skip at `registry_compiler.py:178` severs lean→descriptor→priors→builder; `-m ""` at launch; eval_batch precedent doesn't transfer); P0-2 mode-flag plumbing absent and forbidden by the proposal's own §4 allowlist; P1-1 preflight false-blocks on every healthy fleet (blanket override becomes routine); P1-2 SMT-sibling blindness (184-191 vs physical 88-95 — architect_general 0-95 missed; recert set incomplete); P1-3 missing API-only reload step; P1-4 np_ceiling evidence-basis misstated (A3-FF GGUF is 27.74GiB not "identical to stock's 26.70GiB"; anchors conservative-safe for stock but arithmetic not reproducible; no FF tenant row — silent reuse hazard on tenant swap); P2-1..P2-8 hygiene (port-free+sha256 in preflight, attestation completeness/freshness, saturation-cap enforcement, prewarm skip, MTP mode-toggle claim vs builder, witness coverage, card pinning, foreign-PID allowlist).
- [ ] **P2-6 (THIS session, in flight 2026-07-28)** — land the P2-4 punch-list: P0-1 compile-contract tenant-role path (inert-by-construction: new optional meta key honored only when present), P0-2 mode-branch plumbing + §4 allowlist amendment, P1-1/P1-2 preflight overlap taxonomy + SMT-sibling fold + recert-set completion, P1-3 reload step, P1-4 np_ceiling corrections + explicit FF row-or-refuse, P2 hygiene batch; re-witness inertness after. Subagent dispatched.
- [ ] **P2-5** — D1 design provision documented in the lane spec (admission priority order; shed-batch + degraded-overflow flags exist but may stay unimplemented/off).

### Phase 3 — shadow bake-off (eval path only, never live /chat)
- [x] **P3-0 — bake-off harness COMPLETE** ✅ 2026-07-28 (research `55eca84f`, reviewed + pushed; 33/33 tests) — pinned manifest sha256 `3bb31a7a…` (SWE-40 + LCB-53 + FG-1 hard-core 14 extracted programmatically and cross-checked; model hashes pinned, stock matches the lane-spec pin); plan-only runner gated by `--execute --i-have-operator-grant`, never launches servers; co-critic duty = 120 balanced typed-verdict tasks (60/60, gold provably never leaks into prompts; corpus is a swappable v1 PROPOSAL — single-oracle LCB-only, limitations stated) scored by deterministic replay (FA/FR/kappa/prevalence, declared abstention estimand); paired McNemar with honest MDEs (~0.20 SWE / ~0.19 LCB / ~0.13 critic — the critic duty is the discriminating signal; coder likely decides on token economics); spec `docs/design/p3-shadow-bakeoff-spec.md`. Known wart: `critic_tasks_v1.json` is untracked (PII-hook false positive on LCB digit runs) but deterministic-regenerable + manifest-hash-pinned. All 10 interpretation calls reviewed and ACCEPTED.
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

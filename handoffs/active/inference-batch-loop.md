# Inference-Batch Loop — Campaign Insertion Point

**Status (2026-07-17):** manifest built, command-fabrication-audited + repaired, backlog runners built, autopilot-wired — **loop-ready**. The inference *runs* are pending an operator `/loop` session.

**START HERE (execution source-of-truth — machine-readable, do not re-narrate):**
- `coordination/inference-batch/LOOP_PROTOCOL.md` — the operator `/loop` runbook (single-writer rule, session-init, pick-next, per-entry cycle, autonomy policy)
- `coordination/inference-batch/manifest.yaml` — the 52 compiled entries (source of truth for WHAT runs; recompile from `entries/*.yaml` via `scripts/coordination/compile_inference_batch.py compile`)
- `coordination/inference-batch/op-bundle.md` — the canonical operator-gate registry (A–F) + 4 pre-formed Escalation decisions
- `coordination/inference-batch/ledger.jsonl` — append-only execution ledger (the loop is its SOLE writer)

The `/loop` is the SOLE writer of the ledger + batch checkbox flips. Do NOT run a manifest entry from any other session. NO nightshift; quiet-window-gated (never compete with the parallel inference session).

## Prioritized task list

### Infrastructure — COMPLETE (this makes the loop runnable; 2026-07-17)
- [x] Consolidated inference-batch manifest built — 52 entries, compiler + ledger lib ✅ 2026-07-17
- [x] Command-fabrication 5-audit (commands/provenance/preconditions/graph/committed-code) — fabrication localized to leaf commands ✅ 2026-07-17
- [x] Command repair — ~15 entries re-pinned to real commands; ~15 honest `BUILD-*` gates ✅ 2026-07-17
- [x] 8 backlog runners built + fixture-tested (tm8_coverage, lb1_attribution, reviewer_policy_arm_ab, field-order arm, glm_capability_probe, embedder_recall_bench, shapekeyed_step2_smoke, migration_probe) ✅ 2026-07-17
- [x] eval-tower verifier/calibration mode (EV-4/EV-11 runnable; EV-5/7/8 download-gated) ✅ 2026-07-17
- [x] Mechanism-B ledger bridge + Mechanism-A events→ledger materializer (RCP-W2/W3/RC-8 runnable) ✅ 2026-07-17
- [x] Escalations ESC-1..4 resolved (relaunch command, eval-suite routing, bench `-m` form, Mechanism-A validated on 32 real events) ✅ 2026-07-17
- [x] op-bundle gate registry reconciled (21 gates A–F + 12-item build-backlog, 9 flipped SATISFIED) ✅ 2026-07-17
- [x] Autopilot wiring: digest FA/FR consumer (B1), materializer refresh (B2), AP-6 seam (B4), supervisor liveness (C1), precondition gate (C2) ✅ 2026-07-17
- [x] Dashboard incoherence root-cause (H4 lost-updates / H2 no-shared-epoch / H5 age-not-value) + `state_lock` primitive ✅ 2026-07-17
- [x] Dashboard incoherence root-cause + fix — H4 single-writer lock + daemon control-merge, H2 shared snapshot epoch, H5 value-consistency axis ✅ 2026-07-17

### Inference runs — PENDING the operator /loop (quiet-window gated)
- [ ] **P0** RCP prologue — RCP-W1 (reference relaunch + preflight), RCP-W2 (ledger materialize), RCP-W3 (calibration smoke) — gated OP-6a/6b + OP-stack-restart-approval
- [ ] **P1** reviewer-plane riders — RC-8, RM-6, LB-1, LB-4, RD-12, TM-8 (TM-8 self-attested until emit-path markers land)
- [ ] **P2** eval-tower — EV-4, EV-11 (runnable); EV-5/7/8 (MODEL-DOWNLOAD-gated); EV-10a; RE-4; H5-RM3
- [ ] **P3** bulk-campaign — DS-E1, A7, K-EMB-1, XMAS, hermes, kbrag, langgraph, ODLB-W3-01/02; K-ROPE (harness build-gate); ODLB-W3-03 (paddleocr-VL build-gate)
- [ ] **P4** kernel/OP-2 — KOP2-frontdoor (OP-EXPERIMENTAL-KERNEL-BENCH), KOP2-v6iqk (OP-POST-REBOOT), KOP2-strand (OP-STRAND-APPROVAL); ROUTE-A1/A2/A3
- [ ] **P5** GLM window — GC1/GC2/GC3 (hard-gated COORD-glm52-admission — parallel-session handshake)
- [ ] **P6** decision-grade confirmations — RC8/LB7/RM4/RM8/RELABEL/RM2-A3 (gated OP-5a P-REV-1; RM2-A3 also COORD-axa-teleport)

### Genuinely blocked build-backlog — OWNED BY THIS reviewer-plane/ODL workstream (NOT the loop, NOT the parallel session)
These are BUILD tasks for this workstream's own code. The parallel session / operator only CLEARS the trigger; the build itself is a future session like the one that built the other 8 runners (see progress 2026-07-17). **When the trigger fires: build the runner (fixture-tested; non-serving-path where possible), then pin it into its manifest entry + flip its op-bundle §F gate — exactly the pattern used for the 8 built runners.** A parallel/loop session picking up this handoff should NOT attempt these — it should only signal when the trigger fires.
- [ ] `BUILD-semantics-serving-integration` — wire CP1/CP2/CP3 (reducer/authority/escalation — already landed as modules, orchestrator `43a77eaf`) into the live serving path. **TRIGGER: the stack-freeze lifts** (parallel session's feature tests complete). This IS a serving-path change, so it genuinely cannot be built until then. Owner: reviewer-plane workstream. Unblocks: `semantics-shadow-rollout`, `semantics-advisory-rollout`.
- [ ] `BUILD-paddleocr-vl-adapter` — `_extract_with_paddleocr` VL backend in `src/services/pdf_router.py`. **TRIGGER: the PaddleOCR-VL model lands on disk** (operator download, gated `OP-VL-INFERENCE-APPROVAL`). Owner: ODL workstream. Unblocks: `ODLB-W3-03`.

## Dependency graph (phase gating)
`P0 (RCP-W1 → W2/W3)` → `P1 riders (depend on RCP-W1)` → `P2 eval-tower (independent)` → `P3 bulk` → `P4 kernel/routing` → `P5 GLM (COORD-glm52-admission)` → `P6 decision-grade (OP-5a)`. COORDINATION rows (phase 90) are never picked — the operator/parallel-session flips them to DONE_PASS to unblock P5/P6 dependents. Full DAG in `manifest.yaml`; `compile_inference_batch.py simulate` prints pick-next ordering.

## Cross-cutting concerns
- **Stack-freeze**: no serving-path/lineup change until the parallel session's feature tests complete. The RCP relaunch brings up the *existing* reference lineup (not a config change).
- **Instrument discipline**: all pre-P-REV-1 reviewer numbers are OBSERVATIONS (never gate keep/revert/promote). Era-stamp every result.
- **Quiet-window rider**: `throughput_sensitive`/`eval_fanout` entries run only in a detected quiet window (`inference_load_check.py`); `serial_noninference` may run anytime.

## Reporting instructions (for the /loop)
After each entry: write the ledger terminal row; on `pass`, flip the entry checkbox + `also_flips` via `flip_checkbox.py`; on `marginal`, record an observation (no flip); on `ambiguous`/`op_gate`, append a decision block to `op-bundle.md` and continue. Regenerate `batch_status_report.py` + update this handoff's status line at each phase boundary. Full wrap-up at phase boundaries.

## Key file locations
- Entries: `coordination/inference-batch/entries/{00-rcp-prologue,10-reviewer-plane,20-eval-tower,30-bulk-campaign,40-routing,50-kernel-op2,60-glm-decision,90-coordination-rows}.yaml`
- Loop tooling (epyc-root): `scripts/coordination/{compile_inference_batch,batch_ledger,entry_verdict,flip_checkbox,inference_load_check,batch_status_report,autopilot_precondition_gate}.py`
- Runners (epyc-orchestrator): `scripts/analysis/{run_paired_ab,reviewer_corpus_ledger_run,reviewer_events_to_ledger,reviewer_policy_arm_ab,tm8_coverage,lb1_shadow_overhead_attribution}.py`, `scripts/autopilot/{skill_efficacy_paired_ab,glm_reviewer_capability_probe,shapekeyed_step2_smoke,migration_probe,state_lock}.py`, `scripts/trace/run_task_lg_parity.py`
- Runners (epyc-inference-research): `scripts/benchmark/{longcot_mini_adapter,score_longcot_run,embedder_recall_bench}.py`, `scripts/kb_rag/autowiki_writer.py`

## Completed Scope
Historical detail: `progress/2026-07/2026-07-17.md` ("Inference-batch manifest — command-fabrication audit + repair"). This handoff subsumes the RCP/DS-E1/K-ROPE/K-LCM-1/Queue-2 execution rows previously staged in `bulk-inference-campaign.md` (see its 2026-07-17 subsume banner).

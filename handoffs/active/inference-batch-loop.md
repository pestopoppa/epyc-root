# Inference-Batch Loop — Campaign Insertion Point

**Status (2026-07-20):** manifest built, command-fabrication-audited + repaired, backlog runners built, autopilot-wired, v7-reconciled, and EV-4 Phase-0/3 hardening landed. Production is now `production-consolidated-v7` (`6ad45fa3ff`, binary `10098`), and `COORD-v7-promotion` is terminal `DONE_PASS` in the ledger. The current live island is 8 preflight-clean non-EV-4 rows awaiting a quiet execution window; EV-4 remains `BLOCKED_PRECONDITION` until B7 scorer-semantics sign-off. OP-2/v6+iqk closed outside the loop; GLM reviewer admission failed and the reviewer/control-plane route is decoupled from v7. Lead with this remaining live island instead of stale kernel/GLM reruns.

**K-EMB terminal execution (2026-07-20T23:33Z):** `BULK-K-EMB-1` retried under the corrected exact-model and 512-character input policy and reached `DONE_PASS`. Preflight and execute both exited `0`, ports `8096`/`8097`/`8098` were closed after cleanup, and the Phase B artifact is `data/embedder_bench/granite_97m_r2_phaseB.json` in `epyc-inference-research`. Metrics on the 100-doc / 30-query fallback corpus: Granite Q8_0 recall@10 `0.9333`, recall@50 `0.9889`, nDCG@10 `0.8382`, wall `1.213s`; e5-base Q8_0 `0.8444` / `0.9611` / `0.7928`, wall `2.651s`; BGE-M3 Q8_0 `0.9000` / `0.9889` / `0.8380`, wall `7.037s`; BGE-large reference `0.8889` / `0.9500` / `0.8093`, wall `13.749s`. This flips the Granite Phase B/smoke checkboxes only; the broad P3 campaign remains open.

**RE-4 terminal blocker (2026-07-21T03:25Z; no RE-4 flip):** the optimized v7
quarter-stack RE-4 rerun with `prompt_mode=concise_solution` and
`force_solution_grammar=true` fixed marker compliance but destroyed the benchmark
signal. Frontdoor emitted `solution =` for 402/402 rows and scored 0/402;
worker_general emitted markers for 307/307 partial rows and scored 0/307. The
run was stopped after 6223s because the answer-only grammar suppresses the
reasoning/computation LongCoT-Mini is meant to measure. Latest ledger status is
`INFRA_BLOCKED`, not `DONE`; score artifacts live under
`coordination/inference-batch/bundles/RE-4/partial_*_score_20260721T013833Z.*`.

**TM-7 bridge no-op blocker fixed (2026-07-21T03:36Z; no TM-7/TM-8 flip):**
the first `BULK-langgraph-tm7-parity` execute attempt returned success in
0.038s without running live real-node parity. Root cause was two-part: the
manifest command omitted `run_task_lg_parity.py --execute`, and the research
bridge ignored `artifacts.outputs`, so it predicted `artifacts=[]` and never
failed on the missing `data/trace/tm7_realnode_parity.json`. The bad attempt is
terminal `INFRA_BLOCKED`; the source entry/compiled manifest now include
`--execute` and the bridge now maps `artifacts.outputs` into expected artifacts
with relative validation under `execution.cwd`. A follow-up semantic guard split
the completed durable-resume code checkbox from the remaining live parity
residual, removed the incorrect automatic TM-8 flip, and requires non-empty
decision chains for both arms. Retry TM-7 only from the regenerated entry hash
`sha256:720b210fd1ee2ba7a4e33fdaa647347c94faca0414bb8c7ca26c73f6473d6b3e`.

**No-execute bridge preflight sidecar (2026-07-20T22:31Z; no entry completion):** durable evidence is now stored at `coordination/inference-batch/attestations/eligible-preflight-20260720T2231Z.jsonl`. It contains exactly 8 `phase=preflight` rows for `RE-4-longcot-mini-calibration`, `BULK-langgraph-tm7-parity`, `BULK-K-EMB-1`, `BULK-hermes-smokes`, `BULK-kbrag-autowiki-k11`, `ROUTE-A1-shapekeyed-step2`, `ROUTE-A2-edit-transaction-ab`, and `ROUTE-A3-j2j3-single-worker`. Every row has `dry_run_ok=true`, `blocking_reasons=[]`, topology verified against attestation `coordination/inference-batch/attestations/20260720T191355.json` with live hash `8c8cfcbb13d2611d`, `stack_contract.ok=true`, and `autopilot_precondition.ok=true`. The bridge passed no `--execute`; it created no batch ledger row or execution artifact package, and no execution checkbox was flipped.

**Topology repin checkpoint (2026-07-20; no entry completion):** root commit
`2c5a4125` repinned the P3 bulk-campaign and P4 routing source entries to
`production-consolidated-v7` with certified topology
`8c8cfcbb13d2611d`; the manifest and source lock were regenerated. A
preflight-only bridge verified the 9 currently runnable entries (`RE-4`,
`BULK-langgraph`, `BULK-K-EMB-1`, `BULK-XMAS`, `BULK-hermes`, `BULK-kbrag`,
`ROUTE-A1/A2/A3`) with `dry_run_ok=True`, `topology.verified=True`, and no
blocking reasons. Execution remains quiet-window gated; none is
`serial_noninference`.

**RCP/reviewer topology repin checkpoint (2026-07-20; no entry completion):** root
commit `c9bc73eb` repinned `00-rcp-prologue.yaml` and `10-reviewer-plane.yaml`
to `production-consolidated-v7` / topology `8c8cfcbb13d2611d`; the manifest and
source lock were regenerated. A targeted preflight-only bridge verified 11
RCP/reviewer operator-gated entries clean. Consolidated batch status is
`entries_total=52`, `valid=52`, `eligible_now=9`, `operator_gate_blocked=15`,
and `blocked=1` (`EV-4 BLOCKED_PRECONDITION`). The quiet window is false due to
active inference on port `18072` / MI210, so no entries were executed and no
checkboxes were flipped.

**Queue-hygiene checkpoint after v7-era repins (2026-07-20; no entry completion):**
root commits `94538e47` and `905519f2` tightened the runnable-row bridge. Passive
`BULK-XMAS` telemetry now requires the concrete
`XMAS-enforce-window-ab-root-present` gate, removing the literal
`<enforce-window AB root>` placeholder from pickable work; consolidated status is
now `eligible_now=8` and `operator_gate_blocked=16`. `BULK-K-EMB-1` now points at
`/mnt/raid0/llm/epyc-root/data/benchmarks/eval-corpus-v0.jsonl`, uses the real
`embedder_recall_bench.py --models/--k` operands, and sets
`EMBEDDER_RECALL_EXECUTE=1` for execution. Its preconditions name the e5-base,
bge-m3, and bge-large references. The current bridge preflight reports all 8
eligible rows `dry_run_ok=True`, verified topology, no literal `<...>`
placeholders, no blockers, and the K-EMB dry-run plan reports 100 documents,
30 queries, 0 missing references, and five result keys. The quiet window remains
false because port `18072` / MI210 is active: no entry was executed and no
checkboxes were flipped. EV-4 remains `BLOCKED_PRECONDITION` on B7 scorer sign-off.

**K-EMB warm-embedder lifecycle checkpoint (2026-07-20; no entry completion):** root
commit `ff2eaf0d` (`Guard K-EMB warm embedder lifecycle`) updated
`coordination/inference-batch/entries/30-bulk-campaign.yaml`, the compiled
`coordination/inference-batch/manifest.yaml`, and
`coordination/inference-batch/sources.lock.json`. `BULK-K-EMB-1` now probes ports
`8096`/`8097`/`8098`, starts only missing warm embedder roles, preserves roles that
were already live, and cleans up only the roles it started; baseline BGE on `8090`
is outside that cleanup set. This was a metadata/command-definition change only:
the batch entry was not executed and no execution checkbox was flipped.

**▶ To run (2026-07-20):** launch this as a **`/goal`** session (codex's equivalent of the `/loop` this handoff's protocol references) — the loop is **single-writer**, so no other session may write the ledger. **Do not re-run EV-4 yet:** the latest ledger row is `BLOCKED_PRECONDITION` on B7 scorer-semantics sign-off after the 2026-07-20T19:15Z partial run confirmed the textual multiple-choice rewrite was still changing scorer semantics. `OP-quiet-window` is granted only when `inference_load_check.py --json` reports `quiet: true` immediately before execution. EV-11a and EV-11b are now fixed; EV-11c still waits on the EV-CONF/logprob and scorer-era prerequisites before the math rebaseline entry can execute. P0 still needs its front gates (`OP-6a/6b` + stack-restart). (Terminology: this doc says `/loop` throughout; read it as `/goal` under codex.)

**⚠ 2026-07-20 — EV-4 did NOT pass; robustness audit filed, then Phase 0-4 blockers landed.** EV-4 hit `INFRA_BLOCKED` (stale contention matrix → silent fanout→concurrency=1 → killed partial run → no decision-grade metrics), and a later partial rerun exposed a textual multiple-choice scorer blocker. Root cause of the original fanout failure was NOT the kernel — it was the **2026-07-17 vision NUMA rebind** shipping without a matrix recert. The loop wedge, v7 topology pins, live v7 matrix recert, safe host remediation, mandatory autopilot preflight, forced-role concurrency, serial wall-budget hardening, scorer textual-label fix, and promotion/preflight prevention guards are now landed and checked in [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-loop-robustness-audit-2026-07-20.md). EV-4's latest ledger state is now `BLOCKED_PRECONDITION` on B7 scorer-semantics sign-off, so it is intentionally not retry-pickable; do not append a fake checkpoint row or flip EV-4 until a fresh run produces decision-grade metrics.

**Checkpoint (2026-07-20T19:17Z; no EV-4 flip):** EV-4 is preflight-ready again
after the Phase-0 unblock. The fresh attestation
`coordination/inference-batch/attestations/20260720T191355.json` passed for
`frontdoor+worker_general` with `topology_hash=expected_topology_hash=8c8cfcbb13d2611d`;
`preflight_gate` now separates the 16-char contention topology hash from the
registry hash. A prepare-only `run_batch_entry.py --batch-entry /tmp/ev4-batch-entry.json`
reported `blocking_reasons=[]`, `stack_contract.ok=true`, and topology
`live_hash=required_hash=8c8cfcbb13d2611d`; root coordination verification
`test_batch_ledger.py test_batch_status_report.py -q` passed 31/31.

**Checkpoint (2026-07-20T19:22Z; no EV-4 flip):** the preflight-ready EV-4 run was
started and resolved fanout concurrency `4`, but was intentionally interrupted at
partial `cal-worker_general` progress after the overlapping textual-choice scorer
bug was confirmed. The latest ledger row is `BLOCKED_PRECONDITION` (run
`EV-4-20260720T191550Z-B7`), not retry-pickable by EV-4's `INFRA_BLOCKED` retry
policy. Complete the B7 operator-reviewed scorer-semantics package before appending
a `READY` row or re-running EV-4; partial progress artifacts under
`orchestration/reports/eval_batch_serving_evaltower_20260720T191550Z/` are
diagnostic-only and contain no `summary.json`.

**Checkpoint (2026-07-20Tpost-B7; no EV-4 flip):** `batch_status_report.py` now
distinguishes structural eligibility from runnable-now eligibility after
`op-bundle.md` operator gates. The current manifest has 24 structurally eligible
entries, but only 9 runnable entries once missing/ungranted operator gates are
filtered; 15 are surfaced separately as "structurally eligible but operator-gated."
Use `--ignore-operator-gates` only for structural audits, not for pick-next.

**Safety sidecar (2026-07-20; no EV-4 flip):** root `566eaacf` makes
`batch_status_report.py --ledger <missing>` fail closed with `rc=2` and
`ledger not found`; the real ledger reports EV-4 `BLOCKED_PRECONDITION`,
`ledger_rows=14`, and `eligible_now=9`. Root `bf112b90` makes
`compile_inference_batch.py` reject duplicate YAML mapping keys through its
strict safe loader, with clean CLI failure for validate/compile/simulate. The
full coordination suite passed `120 passed`, and validation reported `52 valid`.
RE-4 source/manifest content was already clean; this records duplicate-key
prevention only, not a manifest-content change. EV-4 remains blocked and its
checkbox is intentionally unchanged.

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
- [x] TM-7 bridge no-op prevention — command-driver entries now treat `artifacts.outputs` as expected artifacts, validate relative outputs under `execution.cwd`, and `BULK-langgraph-tm7-parity` now invokes the live parity leg with `--execute` ✅ 2026-07-21

### Inference runs — PENDING the operator /loop (quiet-window gated)
- [x] **P-CRIT (Phase 0 unblock — do FIRST; runs in any detected quiet window, self-gated via `inference_load_check` like every other entry — no separate approval)** — **re-measure `vision_escalation` + regenerate the v7 contention matrix, then commit it.** ✅ 2026-07-20 — live v7 recert completed on topology `8c8cfcbb13d2611d` (15 measured cross-role pairs, 6 same-role entries, 0 unknown pairs), committed in `epyc-orchestrator`; D1/D4/D5 also landed in `epyc-root`. Full analysis + owner-tagged fix checklist: [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-loop-robustness-audit-2026-07-20.md).
- [ ] **P0** RCP prologue — RCP-W1 (reference relaunch + preflight), RCP-W2 (ledger materialize), RCP-W3 (calibration smoke) — gated OP-6a/6b + OP-stack-restart-approval
- [ ] **P1** reviewer-plane riders — RC-8, RM-6, LB-1, LB-4, RD-12, TM-8 (TM-8 self-attested until emit-path markers land)
- [ ] **P2** eval-tower — EV-4 is the first live v7 entry, but it is currently `BLOCKED_PRECONDITION` on B7 scorer-semantics sign-off. The EV-4 command requires `--min-eval-concurrency 3`; verifier-mode preflight now checks fanout against the actual forced roles (`worker_general,frontdoor`), serial fallback has a wall-budget fail-closed path, runner arms require full `n_scored` before decision-grade, and the textual multiple-choice implementation now covers configured labels, overlapping labels, and `(B)` expected letters. Because that changes scoring semantics, rerun EV-4 only after B7 operator sign-off, then append an explicit `READY` row or intentional retry-policy change. EV-11b closed-bin ECE is implemented; EV-11c remains after EV-CONF/scorer-era prerequisites; EV-5/7/8 (MODEL-DOWNLOAD-gated); EV-10a; RE-4; H5-RM3
  - [ ] **RE-4 protocol repair** — redesign LongCoT-Mini execution so models may do bounded reasoning while deterministic final-answer extraction still works. Do not rerun the `concise_solution` + answer-only grammar protocol; latest evidence is floor-saturated (frontdoor 0/402, worker_general 0/307) and quarantined as `protocol_blocked/floor_saturated`.
- [ ] **P3** bulk-campaign — DS-E1, A7, XMAS, hermes, kbrag, langgraph, ODLB-W3-01/02; K-ROPE (harness build-gate); ODLB-W3-03 (paddleocr-VL build-gate). `K-EMB-1` is DONE_PASS 2026-07-20, but this campaign row stays open until the remaining P3 entries close.
- [ ] **P4** kernel/OP-2 — OP-2/v6+iqk and final v7 readiness closed outside this loop on 2026-07-19; do not schedule unchanged KOP2-frontdoor/KOP2-v6iqk reruns. Remaining kernel/routing entries require the manifest owner to reconcile the ledger against [v7-promotion.md](v7-promotion.md) and current post-candidate work before execution.
- [ ] **P5** GLM window — legacy GC1/GC2/GC3 admission chain is superseded. GLM failed decision-grade P-REV-1 and reviewer/control-plane is decoupled from v7; only run a GLM entry with a named repair hypothesis or non-reviewer capability gate.
- [ ] **P6** decision-grade confirmations — RC8/LB7/RM4/RM8/RELABEL/RM2-A3 (gated OP-5a P-REV-1; RM2-A3 also COORD-axa-teleport)

### Genuinely blocked build-backlog — OWNED BY THIS reviewer-plane/ODL workstream (NOT the loop, NOT the parallel session)
These are BUILD tasks for this workstream's own code. The parallel session / operator only CLEARS the trigger; the build itself is a future session like the one that built the other 8 runners (see progress 2026-07-17). **When the trigger fires: build the runner (fixture-tested; non-serving-path where possible), then pin it into its manifest entry + flip its op-bundle §F gate — exactly the pattern used for the 8 built runners.** A parallel/loop session picking up this handoff should NOT attempt these — it should only signal when the trigger fires.
- [ ] `BUILD-semantics-serving-integration` — wire CP1/CP2/CP3 (reducer/authority/escalation — already landed as modules, orchestrator `43a77eaf`) into the live serving path. **TRIGGER: the stack-freeze lifts** (parallel session's feature tests complete). This IS a serving-path change, so it genuinely cannot be built until then. Owner: reviewer-plane workstream. Unblocks: `semantics-shadow-rollout`, `semantics-advisory-rollout`.
- [ ] `BUILD-paddleocr-vl-adapter` — `_extract_with_paddleocr` VL backend in `src/services/pdf_router.py`. **TRIGGER: the PaddleOCR-VL model lands on disk** (operator download, gated `OP-VL-INFERENCE-APPROVAL`). Owner: ODL workstream. Unblocks: `ODLB-W3-03`.
- [ ] **CP3 in-content-injection quarantine (§13.2 control 1)** — the reviewer-prompt control/data DELIMITER. The assembly-layer half (path-allowlist + secret redaction + buried-critical `truncation_manifest`) LANDED 2026-07-17 (`src/proactive_delegation/candidate_sanitizer.py` `7a3fcb55`); this residual needs a delimiter in `review_service._render_outputs`, which is serving-path. **TRIGGER: stack-freeze lifts** (same freeze as `BUILD-semantics-serving-integration`). Owner: reviewer-plane. Anchor: `tests/test_candidate_security.py::TestInContentInjectionGap` + injection-probe `01`/`09` (xfail, annotated freeze-blocked).
- [ ] **Patch pre-gate live-dispatch wiring (EV-12)** — wire the built `src/verification/patch_pre_gate.py` (`902fd303`) into the coder_escalation dispatch as a real pre-gate (skip escalation inference on a provably-broken patch). The SIGNAL is built + tested; only the live-dispatch call is deferred. **TRIGGER: stack-freeze lifts** (touches the dispatch/serving path). Owner: routing/reviewer-plane. Consumer handoff: `research-evaluation-index.md` RE-2/EV-12.

## Dependency graph (phase gating)
`P0 (RCP-W1 -> W2/W3)` -> `P1 riders (depend on RCP-W1)` -> `P2 eval-tower (independent)` -> `P3 bulk` -> `P4 kernel/routing (requires 2026-07-19 readiness reconciliation before pick)` -> `P5 GLM (only named repair/non-reviewer gates)` -> `P6 decision-grade (OP-5a)`. COORDINATION rows (phase 90) are never picked — the operator/parallel-session flips them to DONE_PASS to unblock dependents. Full DAG in `manifest.yaml`; `compile_inference_batch.py simulate` prints pick-next ordering, but stale kernel/GLM rows must be reconciled before execution.

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

# 2026-09-29 — workspace-8d (consolidated, operator-invoked /wrap-up)

Covers everything since the last wrap-up (root `af6c9376`, early 2026-09-28). Most of it is already recorded in
per-task shards, which this file links rather than repeats:

- [`2026-09-28-orch-design.md`](2026-09-28-orch-design.md): the ARCHSWAP bring-up and the UFH-13 park.
- [`2026-09-29-workspace-8d-jev-rulings.md`](2026-09-29-workspace-8d-jev-rulings.md): the operator's Jev rulings Q1-Q5
  and the owner consolidations.
- [`2026-09-29-workspace-8d-w8083-window.md`](2026-09-29-workspace-8d-w8083-window.md): the 07:05-07:09Z :8083 window
  (B2, the ARCHSWAP-3b re-run, the RI-23b A/B, the V6R-4d attempt) and the hardened A/B checks.
- [`2026-09-29-workspace-8d-ri23-live.md`](2026-09-29-workspace-8d-ri23-live.md): RI-23 and RI-23a landed and live,
  RI-22 fixed, HS-OD-10 ticked, and the tap events cleanup.

## Summary by thread

| Thread | State | Where it is recorded |
|---|---|---|
| ARCHSWAP-20260927 (architect role swap) | Signed 2026-09-28, lanes merged, `relabel_state --apply`, B1 reload, `v1_escalation` on (orch `6d024ced`). P1-P4 proven; P2/P3 re-run passed after the fixes (07:06Z, then 15:04Z with reasoning). B2 of :8083 done 07:05Z. **Open: the :8074 relaunch** (live PID 2030855 still carries `--slot-save-path …/architect_critic`, re-checked 23:5xZ) and the A-3 scout-stage sample. ARCHSWAP-5 closed in this wrap-up (below). | `thesis-experiment-orchestrator-vs-strongest-model.md` ARCHSWAP-3b/-4/-5 |
| `/v1` prompt-format defect | HS-OD-10 (orch `5ddb7320`) and tap isolation for unit tests (orch `8a7d57a8`) on 2026-09-28. RI-22, RI-23 and RI-23a landed and live: orch `e0787feb`, flag `a504ba28`, receipt `RATIFY-RI23A-20260929`; live proof at 15:04Z. OP-69 closed. | `routing-intelligence.md`, `harness-selection-and-integration.md` HS-OD-10 |
| UFH-13 thesis experiment | PARKED 2026-09-28 (operator). TE-reopen's review-gate prerequisite (RI-22) is now met. Root `2e239c9c` adds a note on :8083 KV headroom with DS41's two 27B lanes. | thesis handoff TE-reopen |
| Jev techniques | Map `/mnt/raid0/llm/tmp/jev-techniques-map-20260928.md` (canvas v15, "Jev map"). Rulings Q1-Q5 plus test-bed rule 6. Owner consolidations. TD-29 with M0-M4. TD-15a (root `9f68e32e`). Hygiene fixes: orch `e60ee78a` (skip the typed-args call site when the flag is off) and root `a7230076`. TD-29.M0 code landed as orch `c4e99dbe`. TD-29.K1 single-token keys landed as orch `c595e13d`. | `typed-decision-plane.md` rulings, TD-29 |
| TD-29 native result (champion sidecar) | 12/18 exact and all 12 resolved cases correct; 534 generated tokens against 5,112 for the GPU JSON arm. The 6 failures are the multi-token `severity` enum, which K1 fixes. The receipt is kept as `closed_native_id_only.pre-K1.json`. A window-gated loop (`window_loop.sh td29`, `NEED_MIN=10`) started at 23:48Z for K2 plus the JSON and free-form arms. No arm had run by 23:50Z, because DS41's two-lane windows have been shorter than 30 min. | TD-29.K2, TD-29.K2a |
| Champion | HIP build `kernels/builds/gpu-20260929-90c12df42` exists (V6R-4d). The live GPU A/B did not complete in the :8083 window; the checks are hardened and the A/B is re-planned for the vision window. The SW-9 GPU check is pending. DS41's champion of record has 4 serving-gated keeps plus 1 on the campaign lineage. Folding them into the global champion is workspace-76's item (DS41-C47/C68, INF-77), with no ETA. | `autokernel-champion-aggregate.md` V6R-4d.0-.2 |
| Operator actions | OP-67 countersigned by Daniele at a terminal (root `04a82bc8`). Tap events cleanup: 3,668 removed, 267,312 kept and verified. The plain tap log is NIB2-91. | master archive; `non-inference-backlog.md` NIB2-91 |

## What this wrap-up added (gaps closed)

- **ARCHSWAP-5 ticked.** PACKAGE §9 texts were applied:
  - `decision-aware-routing.md`: DAR-LAT-3, 3a and 3i, including the `server_mode.architect_general.recipe.env_not_serving`
    key and three "critic" mentions that meant :8074;
  - `conversation-stack.md`: :109 and CS-17 (the voice target is `architect_critic`, the :8083 27B);
  - the memory `project_champion_promotion_and_architect_swap_plan`.
- **typed-decision-plane.md:**
  - The TD-29 native receipt path is corrected to the `.pre-K1` names.
  - The flag-off call-site skip is ticked (orch `e60ee78a`).
  - TD-29.M0's landed code is recorded (orch `c4e99dbe`; the box ticks with the re-run).
  - The running window loop is recorded under K2.
  - K2a is filed: record workspace-76's agreement to the 10-minute threshold. Ruling 6 names ≥30 min otherwise.
  - A window-discipline line is added to ruling 6's gate.
- **autokernel-champion-aggregate.md:** V6R-4d.0 (hardened checks) is ticked. V6R-4d.1 (the vision-window A/B) and
  V6R-4d.2 (the SW-9 GPU check) are filed as boxes.
- **Operator direction, 2026-09-29:** do RI-16, RI-18 and NIB2-91 after this wrap-up. Each already had a `- [ ]` box.
  Each now carries the direction and its next step (`routing-intelligence.md`, `non-inference-backlog.md`).
- **Lessons:** four entries in `docs/reference/agent-config/INCIDENT_LOG.md` (INC-20260929-*), with rules in editable
  homes:

  | Lesson | Rule home |
  |---|---|
  | A peer-window watcher treated `closing` as usable | `docs/guides/agent-workflows/benchmark-analyst.md` → *Scarce windows*; typed-decision-plane ruling 6; the memory `reference_autokernel_cpu_window` |
  | A gate piped into `tail` pushed a failing check | `agents/commands/wrap-up.md` Step 3 (capture the rc to a file) |
  | Dry-runs missed live-only checks | `benchmark-analyst.md` → *Scarce windows*; V6R-4d.0 |
  | TTY-gated operator scripts refuse under `!` | `agents/coordinator-agent.md` → *Ratifications ACCUMULATE* |

  `agents/shared/OPERATING_CONSTRAINTS.md` is a human-only path (`coordination/session-bus/human_only_paths.yaml`,
  `agents/shared/*.md`). Its amendment is therefore prepared as
  `artifacts/operator/lessons-20260929-operating-constraints.patch` (`git apply --check` clean) for the operator to
  ratify, not committed.

## Still pending (each has a box and a named gate)

- **ARCHSWAP-4, the :8074 half.** Needs a CPU-window reload of `architect_general`, coordinated with workspace-76.
  This is coordination, not an operator decision.
- **V6R-4d.1 and V6R-4d.2.** Both need a DS41 pause coordinated with workspace-76 (V6R-4d.2 can also use the 2nd MI210).
- **TD-29.K2 and M0.** The window loop is running.
- **Next, per the operator:** RI-16, then RI-18, then NIB2-91.

# 2026-11-24/25 — workspace-f2 (Assorted / RTG-22 non-inference)

## Programs
1. **Serving config on the AutoKernel surface** (operator 2026-11-24): AK-SURFACE-SERVING-1, CHAMPION-SERVING-CONFIG-1,
   PROMOTION-REGISTRY-SERVING-1 — all ticked after Fable gates.
2. **One standard roofline-surface loop** (operator 2026-11-24): new track `autokernel-roofline-surface-loop` in
   `handoffs/active/autokernel-loop.md`, boxes RSL-R0..R8. A campaign = a `model_weights` setting; equal weights default.
   Ticked: R0 (autokernel), R1, R2, R3, R4, R5, R7. Open: R6 (A/A timing floors), R8 (A3B KLD floors).
3. VB-AK-BW-CENSUS-WIRE (Vidya adapter for the bandwidth census) ticked.

## What changed (all on origin/main)
| Repo | Area |
|---|---|
| research | serving_knobs, serving_knob_measure (single screen, 62 GiB card ceiling, noise-floor-gated best arm), typed_planner, tailsplit knob route, seed serving-knob kind |
| research | census_reconcile/coverage/families/inbox, journal_keys, census_update annotate + stamps backfill + device normalisation, census_extract (verify-attention ipb, verify-kernel roofline, q0q2 72t) |
| research | stage_bodies (op-perf, per-path timing/quality, CPU KLD clauses, serving-screen), op_perf_screen/runner (+FLASH_ATTN_EXT), cpu_timing_runner (A3B solo + burst cells) |
| root | C22 serving-config + validator (strict), kernel-promotion package.sh (registry diff, orch from origin/main), akloop chain.py (op-perf, per-path lanes, serving-screen), ak_runend (census_inbox, path-gates, registry snapshot, scripts/ snapshot), watch_rows ak-*/akx-* routing, /loop census + path-gates panels, fold_row_guard KLD floors (CPU relative x1.5), Vidya adapter |
| orch | serving_shape.alternates schema + compile, serving_config_registry (strict, value-typed), stack_change_pipeline alternates step |

## Verification
- Fable plan audit, Fable wiring audit (25 defects), Fable final gate (N1-N12), Fable six-box gate; fixes FX1-FX9, FXA-FXC.
- Live: run-end hook run once by hand on ak-27b-verify-kernel-roofline-census-gpu-20261124-r2 — census +114 records, 15 BWS
  inbox stubs, coverage/family_rank/path-gates served by the hub. Canary committed: artifacts/analysis/rsl-r5-canary-20261124/.
- Found and fixed along the way: GPU ab-timing could never be decisive (fraction stored as percent, no floor passed);
  |dPPL| clauses never decided (ln_ratio not mapped); op-perf screen could never reject; census CPU records unstamped.

## Incidents (mine)
- Unpinned `pytest loop` landed on GPU host cores 88-95 and idled the MI210 ~20 min; tests now pinned to 84-87.
- Pushed twice past failing checks (piped `| tail` masked rc): one pre-existing test, and the loop code ceiling (+25,
  trimmed back the same hour). Push gating now uses exit codes.
- Five ~3 GB builder worktrees dropped disk 22 GB; all removed; builders now share per batch.

## Open (owner)
- autokernel: arm the row watcher (no watch_rows process; hook never fired on its own); publish A/A floors (Q38FN CPU,
  A3B CPU solo + burst), A3B KLD floor, two op-perf calibrations from current main; fold served_shape_perf_v1 into the champion.
- loop owner: install the serving-knob seed in the live store; route serving-knob hypotheses past critic/author.
- operator: A3B registry `recipe` block (stack-change package); host-RAM budget for CPU knob screens; A3B KLD ratification.
- Vidya: live `ingest ak-bw-census` (needs the canonical-ledger owner flag).

## 2026-11-25 (later) — intake routing, 1638 GB/s ceiling, two code boxes
| Item | Commits | Result |
|---|---|---|
| Research intake intake-kspec-1125 (15 sources + 11 expansions, 11 dives) | root 65c5bee6e, aa0954a96, 4216f6b16, d4838a312, df2b2a07c | operator-approved Stage 4: 5 boxes, notes, 6 declines |
| Routing (operator) | — | AK: AK-MMQ-SK2-CENSUS, DTREE-HEADROOM-REPLAY (fold into queue); Autopilot (workspace-bb): EV-DATE-PIN-1 building; seeds: research dd36a3dcd (7 low-ROI) |
| MI210 ceiling 1638 GB/s (operator via pipeline-mgmt ~10:40Z) + AK-BW-CENSUS-GPU-SERVED-BASELINE | research 82030c59b, 649633226, 507a32254; root 231cf50a0, 6f1d4e98e, edcc382f3, bf4c5b531, 7f8d16b3d | ticked (Fable 4/4); committed census reconciled to live (94 -> 244); follow-ups AK-BW-CENSUS-27B-STEP-REBASE, AK-BW-CENSUS-R2-NOTSERVED-CLASSES |
| AK-MECH-WITNESS-1 (D9 approved) | root 847a191fa, 0f358fe03, b506e2d78; tick 4ea0eb292 | ticked after 3 Fable rounds; sweep 353/625 warn, explicit-keep missed 1/294 |
| VKRC-BYTES-PLAUSIBLE | research e182d4688, bd2694353, 04405da00; tick 86e1b5b8d | ticked after 3 Fable rounds; r2 BYTES-CHECK 114 rows, 0 flagged, 69 unknown |
| Policy: subagents pin every command to 84-87 under load | root a4c4bdb02 (Operator-Ratified) | in OPERATING_CONSTRAINTS |

Incident (mine): the intake subagent's unpinned `validate_intake.py` contaminated an AK C22 CPU measurement (re-pinned; policy above).
Open: AK owns the two folded items and the R2-NOTSERVED decision; unlanded local research commit 84b45a34b (DTREE replay) is AK's.

## Intake status-staleness audit (late afternoon)

Problem: the intake-kspec-1125 dive S2 routed TreeSpark (intake-2975) to "monitor until trees reopen". But at its own pin f19b9028f, the C21 V2 RRS tree was already KEEP at official T1 (ak-c21-tree-official-gpu-20261124: T10 1.0303, T16 1.0352). Root cause: the dive cited the older park/LOSS lines in speculative-decoding.md and missed the newer verdict. Sibling dive S1 had cited it, so the plan was inconsistent within one run. Note: the DTREE-GDN-BATCH box itself is open (its GDN row KEEP is 3.619 ms; the box waits on the C20 fold decision).

A Fable audit covered 8 intake runs from 11-22 to 11-25, with ~135 status-dependent dispositions: 6 were stale when written and 9 superseded since.

| Change | Commit | Result |
|---|---|---|
| Dated corrections in the kspec-1125, nanocode, agents-intro and ak-1123 intake records | root 1acdda6b2 | TreeSpark goes to DTREE-HEADROOM-REPLAY; CODEMODE-AB-V2 wording; RM-3 triggers re-pointed to RM-4; DICE/COUPLE-MTP closed; ForeSpark np4 |
| ak-1123 M6 and kspec M2(b) tree triggers marked FIRED | root 26753a3e6 | |
| SPEC-GRAM-JSON-1 prior note; operator kept it open | root 2b05743f7 | I first asked with incomplete facts, then re-asked |
| VKRC bytes check run retroactively on census r2 | none (analysis) | 114 rows, 0 flagged, ratios 1.0007-1.05; Q8-MULTICOL-GEMV-1 premise holds (the 68% row is peak-checked only) |
| TreeSpark sent to AK (folded, acked) | AK box DTREE-CALIB-SHRINK-REPLAY, row ak-dtree-calib-shrink-replay-cpu-20261125-r2 | FILE_CALIB_AND_SHRINK: Platt +2.4% vs AUTO at T0.3, ~0 at T1.0; shrink nil at np1. AK's bigger lead is the Pando builder (DTREE-PANDO-GATE, waits on ak_gate sampler/load support) |

Lesson: verify a dive's in-house status claims against the current handoff before relaying or routing them.

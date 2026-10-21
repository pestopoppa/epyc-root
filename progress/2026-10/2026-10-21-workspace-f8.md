# 2026-10-21 — workspace-f8

## 00:00–09:30Z (per-task wrap-up, dispatched by the session)

- **CT-12.3b** (server special-token injection fix): `experimental/ct12-is-input-parse-special-20261021` @ `6dfbc9e86`, on the `fork` remote; accepted by the consolidation session for fold into candidate C (fold ledger `fc2cafb7e`). **CT-12.3c** orchestrator neutraliser follow-up `5dde3006` on epyc-orchestrator main. CT-12.4 goldens A/B 164/0.
- **Queue midnight date bug**: jobs 20/24/30 started 00:00–00:02Z and ended by 00:08Z (the runner's blackout test, `in_blackout` in `cpu-queue-f8/runner.sh`, evaluated a 00:15Z-06:30Z window and the jobs started on the wrong side of the date boundary). W2 was unaffected; pending jobs were parked.
- **KPF-17 vacuity audit** (`a7af56dff`, KPF-17.1b): 7 fork cases could pass without forking; the 17.1a re-check had already failed (17.2(3) never forked, stale /slots wait; fix `11dbef15e`). Morning re-check jobs 25/26/40 FAILED; filed as KPF-17.1c. Failures: 17.2(3) decoding-source honest on swa/mtp, honest same-iteration (hyb, swa) and p2 (swa), mutants `fork_skip_ckpt_load` (hyb) and `dft_partial_noop` (flag-off) not detected; `fork_clobber_src` now detected.
- **KVU-12 W2** (CPU np x ctx Tier-0): rc=0; split-vs-unified UNDECIDABLE (split lost its 4th stream to HTTP 400; idle-slot flag mismatched). Data persisted to epyc-inference-research `artifacts/np_context_kvu_cpu_study_20261020/w2_20261021`; KVU-12.4/12.5/12.6 filed.
- **Morning queue readout** (`5245c2c5d`): DS41 T3.3b template arm works (BOS/thinking-default/harness gaps -> T3.3c); T4.1/T5.1 harness artefacts (-> T4.1.1, T5.1.1); CH-19 fusion predicate can never fire (-> CH-19.1); DSA-IDX.1 oracle 11/11; KPF-18 item 7 fork-on 8-9x faster than fork-off.
- **Backdoor / control-vector intake**: Stage 1-3 done, plan approved, Stage 4 applied on branch `intake/backdoor-cvec-20261020` and being pushed by another agent (worktree untouched here).
- **Idle-CPU episodes** 04:45-06:30Z and 08:52-09:20Z. Cause: the queue blackout outlasted W2 (pending jobs parked, nothing scheduled after), then a peer's 0-95 bench claim for a GPU A/B. Scheduling fix (as applied by the session; see its queue changes): jobs that cannot conflict with a live window must stay runnable after W2 ends, and the blackout test must be date-correct across midnight.
- **Wrap-up audit**: experimental branches pushed to `fork` (kv-prefix-fork-p1r2 `dd5bb0d3b`, intake-fixes `b51a0047d`; ct12, kpf17a, slotdraft already current). Scratch evidence copied to research `artifacts/f8-evidence-20261021/` with SHA256SUMS. The p1r2 worktree carries an UNCOMMITTED edit to `tools/server/tests/unit/test_slot_fork.py` (patch saved in the evidence dir).

- Backdoor/cvec intake no-compute batch: NEW-11 coverage table, AMSB-C390-0 review record, F3-W3-P1 poison screen (orch bc61f308), RC-CVEC-HOOKS partial (preflight + text fix). Research c5661c5f9, root e988b11bd.
## DS41 parity harness fixes (T3.3c / T4.1.1 / T5.1.1)
- `t33.py` v2, `t41.py` v2, `ds41_ninv.cpp` v2 + `rank_ninv.py` in `/mnt/raid0/llm/tmp/ds41-parity-20261021/lib/` (v1 copies kept). Jobs 62-ds41-t33c-{sept,1017}, 63-ds41-t41b, 64-ds41-t51b queued.
- 62-* first attempts ended rc=125 (pairguard stopped paired jobs when the q0 holder changed; not a harness fault) and were requeued unchanged.
- Server-side serial n_probs gap filed as DS41-T4.1.2.


## KPF-04 / KPF-17.3 / KPF-19.1 non-inference parts (subagent, workspace-f8)

- KPF-04 staging page `docs/reference/kv-prefix-fork-radix-lesson-and-vllm-copy-vs-share.md` (cite-check clean). KPF-17.3 was already implemented and passing (jobs 20/30). KPF-19.1: plain-drafter fork is independent of `PARTIAL_ONLY` (`seq_cp_attn` shares the drafter KV); DFlash2 is an SWA drafter, so it needs its own run (KPF-19.1a). Added `dft_no_transfer` mutation and a port-owner check in the test harness (`82c16126f`, `fork` remote). Job 28 first run was stopped by the coordinator (old runner picked q3) and is requeued with the corrected skip_load static check.

## SEC-EXEC-1/2/4 model-exec containment (subagent, workspace-f8)

- epyc-orchestrator 644c6530 + 65fbdce3 (merged): minimal child env with per-task scratch HOME for run_shell/run_python_code (fenced and unfenced), python/python3 removed from run_shell and the find/awk/sed exec refusals applied unscoped, durable rotated JSONL tool-call audit log incl. refused/timeout/error. 10 suites 367 passed, 1 skipped.
- SEC-EXEC-3/5 probes only: `unshare -rn` EPERM, Landlock ABI 6 (net rules available); re-probe as service user. web_fetch private-range deny still open. Handoff: `handoffs/active/model-exec-containment.md`.
- **KVU-12.4/12.5 prep + KPF-18.0b.1** (workspace-f8, zero compute): research `2629df4ca` (slot-fit refusal, equal-argv ABA guard, 3 anchors, verdict script, PLAN §10 rule ratified by owner); launcher `/mnt/raid0/llm/tmp/kvu12-redo-20261021/window.sh`, window D4 19:10Z. KPF CPU+GPU runner fix (argv-derived `dflash2`, same-source unique cells), backups `*.pre-kpf180b1-20261021`; follow-up KPF-18.0b.2 opened.
## SEC-ART-1 implemented, SEC-ART-4 designed (not ticked)
Root `a9fccdc21` (safe_download revision pin + provenance ledger, new-model Step 0, SEC-ART-4 design text in model-artifact-integrity.md) and orchestrator `a9a3365a` (registry pin validator warn/strict, backfill planner). Tests: 11 + 13 + 4 passed. Pending: SEC-ART-1.1 backfill + strict flip.
## kvu-restore-triage (worktree root-kvu-triage)
- Re-added old KVU-21 (#29510 A/B arm) as KVU-22 in handoffs/active/kv-unified-stack-rollout.md; triaged 20 restored open items: 1 superseded (CPU-FA-VKQ-1 by Yfa fold / V11-086 EXCL), 19 open (no evidence found); no ticks. index_state --check clean.

## DS41 retarget to 1017 MXFP4 (subagent, operator ruling 2026-10-21)
- Wrote held jobs 65-ds41-t33c-1017, 66-ds41-t41b-1017, 67-ds41-t51b-1017 in cpu-queue-f8/held-ds41-retarget/ (65, 67 released). 66 plain arm unconditional; speculative arms gated on 1017 DSpark drafter + DSPARK_1017_OK marker.
- 1017 header read-only check: deepseek41, split 9, alignment 32, MXFP4 tensors; binary has mxfp4_8x8.
- Staged evidence ds41-w51-t32-qdq-sizing and ds41-t33c-1017 in research worktree f8/ds41-evidence-2 (uncommitted); ds41-t33c-sept skipped (aborts only, no results).

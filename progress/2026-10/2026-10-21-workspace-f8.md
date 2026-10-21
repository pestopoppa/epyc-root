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

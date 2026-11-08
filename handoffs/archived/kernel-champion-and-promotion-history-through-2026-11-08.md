# kernel-champion-and-promotion: RESUME CHECKPOINT history through 2026-11-08

> Historical ledger only; current work lives in `../active/kernel-champion-and-promotion.md`.
> Archived 2026-11-08 by the main-inf22 operator-cadence wrap-up. The block below was superseded the same day at 19:20Z
> (fold5 `a08f7eb0b` became the C8 candidate).

> **Superseded 2026-11-08 19:20Z:** the checkpoint below is history. Current state: fold5 `a08f7eb0b` is the C8 candidate; promotion is blocked on C8-NP4-GARBAGE.
> **RESUME CHECKPOINT — operator emergency reboot 2026-11-08 ~08:00Z (main-inf22).** C8 is HELD for the H18 numerics fix (operator decision).
> - **Qualified candidate:** fold3 `ab3fc54dc` (stores `gpu-20261108-ab3fc54dc-c8fold3`, `cpu-20261108-6dd06d5fa-c8fold2`), FOLD_PASS + CPU_PASS.
> - **fold4:** merge commit `19c53dbc1` (fold3 + H20) is on branch `llama.cpp-experimental-c8-fold-20261107` in worktree `/mnt/raid0/llm/worktrees/llama-c8-fold-20261107`. Its stores were NOT built (the build agent was stopped). Next: build with `/mnt/raid0/llm/tmp/c8-fold2-build-20261108/job.py` (copy), then strings-prove all knobs.
> - **H18 diagnosis:** the agent was stopped before publishing `c8-h18-diag-20261108`. Restart it from the plan in the C8-4-H18 2026-11-08 note: diag arms default / Q8=0 / HD256=0, a kernel trace, long-prefix q8_0 causal FA tests, then fix branch `llama.cpp-experimental-c8-h18-fix-20261108`. Check whether `/mnt/raid0/llm/tmp/c8-h18-diag-20261108/` or that branch exist before redoing work.
> - **Stopped rows:** `yarn-native-window-gate-20261106-r4` ended rc=75 (resumable). **Trash `/mnt/raid0/llm/tmp/yarn-native-window-gate-20261106/STOP` with guarded_rm before republishing it.**
> - **Withdrawn, to republish when the whole host is free:** c7-local-code28k-r3 and c7-local-serving-profile-r2. LSA r8 is parked (resumable).
> - **Open boxes:** GATE-PPL-LNRATIO-ARTIFACT, DF2-BLOCK16, and the hipBLASLt knob A/B rerun (C8-5 note).
> - **Final step:** once the H18 fix keeps, merge it onto fold4, run one whole-candidate gate on q8_0 KV with KLD < 1e-3 as the quality clause, then build the promotion package.

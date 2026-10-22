# 2026-10-22 KPF-64 replay harness: run-time fix (coordinator session 3c4ca599)

Research repo commit `b93017dc9` (lane/qb2-kpf64-20261021, pushed to origin/main after rebase onto KPF-LB2's Amendment 1).

- Finding: model output IS used in `--history live` (stored, re-sent in later prompts, defines the ideal bound), so the
  "n_predict 1" shortcut does not apply to the primary run. Decode is not reasoning-bound: predicted_n averaged 119
  (<= 128 cap) on raw `/completion` (no chat template, no enable_thinking). Decode cost is batch contention with the other
  slots' prefill (0.80 tok/s per slot); prefill alone runs ~200 tok/s aggregate.
- Changes: live generation capped at recorded reply length (-17% decode tokens); `--history reference` bound fixed
  (`slot_holds_output=False`); `--reasoning off` + `qwen_first_reply_preflight` in `arm_launcher.sh`; endpoint stays raw
  `/completion` on purpose (chat template tail would force a rollback per request). PREDECLARED.md Amendment 2 names the
  voided partial arms pass1-A (196/400) and pass2-D (260/400), moved to `qb2-kpf64/results/voided-20261022T1420/`.
- Time per full arm (24 threads): live ~20.7 ks (A) / ~14.7 ks (D); jobs' per-arm MINARM A,B,C 23,800 s, D 16,900 s;
  reference variant 11,500 / 8,100 s. Poller `--min-window 4500` is below every arm; 2h50m windows cannot finish a live arm.
- Tests: 43 passed in the harness tests dir (16 original-file tests incl. 2 new); launcher dry run and stub driver run OK. No inference.

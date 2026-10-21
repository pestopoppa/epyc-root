# 2026-10-21 queue-builders-2: three queued inference items made runnable

- KPF-64: harness built (research `scripts/benchmark/kpf64_replay/`, `dcd6d5be7`), 14 tests, no-inference dry-run on the real stores (20 sessions, 424 requests, ideal 94.2%) and a stub run. Filler job `fillers-3c4ca599/jobs/kpf64_job.sh`; ready, not armed (arm call refused by the auto-mode classifier).
- KPF-62.8: worktree `qb2-chunkkv-g1-20261021` (tip `2e98e283e`), build filler `kpf-62-8-build` ARMED, `run_g1_real_role.sh` finds the build via BUILD_OK marker. G1 run remains a bundle sub-row.
- RTE-PFX-2: registry-derived recipe + declared prefix, dry-run clean, filler `s5-rtepfx2-stagger` ARMED.
- Launcher id fix: first RTE launcher used a different id than its FILLERS row (COMPLETE sed would not flip); relaunched with the row id.
- Belief wiring: README row + VB-RTEPFX2-WIRE task.

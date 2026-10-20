# 2026-10-20 — workspace-f8

## workspace-f8 (operator session): hybrid prefix caching, prefix fork, champion fold, KVU-12
- Research intake `intake-hybrid-prefix-cache-20261020` complete. Stage 1 intake-2061..2071; Stage 2 six waves (intake-2072..2115, intake-725 dived; second-reader on every wave); Stage 3 plan approved (`/mnt/raid0/llm/tmp/intake-hybrid-prefix-stage3/PLAN.md`, sha 1befe7be...); Stage 4 filed and pushed (origin/main 7bf181b6a): 16 new tasks (KPF-13.1, 17.1-17.4, 18.1-18.3, 19.1, 26.1, DOC-1; KVU-12.1/12.2; VB-KVU-PF.1; CH-18), KPF-25 ticked, RTG-58 row updated.
- P1 prefix fork reassigned to this session; re-cut on champion (`experimental/kv-prefix-fork-p1r-20261020` @ a1f0c8cf9; CPU gate evidence `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/`), rebased onto the new champion as `experimental/kv-prefix-fork-p1r2-20261020` @ 14d603f3a (RECUT2.md; tests green), pushed to fork.
- Champion fold "slotdraft": e33229348 -> dd3d9721c (ports of upstream #26004 + #30574; MTP acceptance after slot restore 0.98-1.02x live vs 0.53-0.71x before); ledger in autokernel-champion-aggregate.md.
- KVU-12 reopened: CPU np x ctx study driver + context bank on research branch `study/kvu-cpu-20261020` (33d137f9f, not yet pushed) and main 56e213ac9/654a45698; Tier-0 window 00:30-06:30Z armed via detached launcher `/mnt/raid0/llm/tmp/overnight-20261020/overnight.sh` (W1 GPU: KPF-17a ROCm0 2978/2978 pass; KPF-18 re-run as kpf18-w1b after a runner log-dir bug).
- Orchestrator KPF-21/25 on branch `feat/rtg58-kpf21-25-20261020` (a572338d), pushed, not merged.
- Lessons: the KPF-18 runner writes `<out>/logs` before creating it (fix needed in `kpf18_gate.py` ~L786); a q3 CPU claim of our own blocked the GPU runner (its host threads 184-191 map to q3) - check sibling-CPU region overlap before co-scheduling.

### Later on 2026-10-20 (operator /wrap-up)
- Champion fold "slotdraft" executed by the operator: `ak/champion/llama-cpp-ffc1bac82eec` `e33229348` → `dd3d9721c`, pushed to fork; store images `kernels/builds/{cpu,gpu}-20261020-dd3d9721c`; ledger in `autokernel-champion-aggregate.md`.
- Prefix fork rebased onto `dd3d9721c`: `experimental/kv-prefix-fork-p1r2-20261020` @ `14d603f3a` (no conflicts; all tests green), pushed to fork; open operator decision KPF-19.2 (pinned flag in slot files).
- KPF-18 runner: three bugs fixed (late-bound trunk length, item-1 fork order, missing logs dir); CPU subset items 6/3/4 exact, 1/2/5 re-run pending, 10-04 divergence shown benign.
- GPU window: KPF-17a ROCm0 2978/2978; first W1 attempt died on the runner's logs-dir bug after our own q3 claim had already stalled it ~30 min (the runner's host threads 184-191 are q3 SMT siblings); relaunched as `kpf18-w1b` with the fixed runner (hard stop 00:05Z). CPU Tier-0 window 00:30–06:30Z armed (detached launcher).
- Old intake worktrees: removed `wrapup-intake-routing-20261006`, `mains/autokernel-intake-20260917`; kept `intake-reverify-20261006` (locked, load-bearing for IRV-4–7) and three dirty trees holding unique content (`ec-intake-ctxext-1006` index edit; `tmp/intake-reverify/*` validator/test work, KEEP-marked).

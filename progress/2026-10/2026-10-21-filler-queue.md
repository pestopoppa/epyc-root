# 2026-10-21 filler-queue

- Built the compute FILLER queue agreed with workspace-58: `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (protocol, safety rules, rows ct18-worker, ct18-arch).
- Grant-polling launchers `filler_worker.sh` / `filler_arch.sh` in `/mnt/raid0/llm/tmp/ct18-run-20261021/`; ports 18821/18822; per-arm flock; refuses while scheduled runner port (18811/18812) listens; kill by captured process group; `.ended` / `.complete`.
- Dry-run with fake grant + stub runner proved: no grant no run, poll->start->hard-end kill->verified dead->grant deleted->`.ended`, port/lock refusals, quarter and CPU-list parsing, launcher TERM cleanup, complete path.
- Armed both (PIDs in FILLERS.md). Armed 3528849/3881221 and today-worker 412625 untouched.
- Protocol codified in `docs/guides/agent-workflows/compute-fillers.md` (OPERATING_CONSTRAINTS.md is human-only; pointer to be folded by main into a later operator bundle).

# Launch admission gate (T1): the same-entry-path preflight

A row is ARMED only after a preflight (PF) that ran the **same entry path** a grant will run.
A dry run of the job script alone does not count. On 10-27 six early launches died on faults
that only the real launcher → filler engine → job chain, started the way a writer starts it,
could expose.

Enforcing tool: `dryrun_check.py` + `filler_run12.sh` (Codex NI, **in progress**). Until they
land, do the checks below by hand and keep their output in the row's dry-run log.

## The PF contract

1. **Entry path.** Real launcher → filler engine → job, stopping at the first side effect (the
   first write under the output root, the first server spawn, the first model mmap).
2. **Writer-format grant.** The synthetic grant uses exactly the writer's format, which has minute
   precision (`HH:MMZ`). Never hand-type a seconds-precision grant. Why: R6 parsed only
   seconds-precision grants, so its PF passed and the real grant was refused.
3. **Non-ancestor process tree.** Launch from a process that is not an ancestor of the job (a
   detached `setsid` shell), as a writer does. Why: under Yama `ptrace_scope=1`, reading
   `/proc/<pid>/…` of a non-descendant returns EACCES; the HSF-3 and FA4 guards read `/proc` and
   died only under the real grant.
4. **Inherited environment.** Run under the normal session env, including `NODE_OPTIONS`. Why: ORCH
   refused silently on an inherited `NODE_OPTIONS`.
5. **Every refusal is logged.** Each guard, gate and exit path prints its reason and rc. A silent
   refusal fails the PF by itself.
6. **Effective limits printed and checked.** From inside the job's own shell, print
   `prlimit --pid $$`, `taskset -pc $$` and `cat /proc/self/cgroup`, then compare them with the
   row's need. Why: KPF18 R13 inherited an 8 GiB RLIMIT and died at model load.
7. **Window.** `min_window + 300 ≤ window` on the grant it will actually get (SKILL §3 step 4).
   Why: INF-50 was booked with min+300 > window and was refused at start.
8. **Process group.** Any `timeout` wrapper uses `--foreground`, or the job runs in its own PGID and
   the launcher kills it as a group. Why: FA4's `timeout` without `--foreground` let the child
   escape the PGID and outlive its grant.
9. **Disk declared.** The row declares `est_output_GiB` and `scratch_root`. Admission requires the
   free-disk floor to hold **after** that output (`disk-bin.md`).

## Origins (10-27 early-launch failures)

ORCH silent `NODE_OPTIONS` refusal · KPF18 R13 inherited 8 GiB RLIMIT · R6 seconds-precision grant
parsing · FA4 `timeout` without `--foreground` escaping the PGID · HSF-3/FA4 `/proc` EACCES under
Yama `ptrace_scope=1` for non-ancestors · INF-50 min+300 > window.

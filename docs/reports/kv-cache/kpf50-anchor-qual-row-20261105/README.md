# Synthetic immutable-anchor control qualification — published

New prerequisite, distinct from custody and window/raw evidence validation:
qualify fixed-root source integrity admission and exact refusal errors. This
does not qualify actual filesystem immutability or solve verify/use races.

Run `bash launch.sh` only through the publisher's canonical rowflow engine.
Outer/completion identity is literally `kpf50-anchor-qual-20261105` throughout.
The 300-second reservation is admission headroom; workload stops on answer or
first discrepancy, <=180 seconds total, <=5 seconds per child plus <=4 seconds
captured cleanup. No repetitions or reservation-filling sleeps.

The unchanged original anchor_preflight.py is retained and source sealed.
case_runner.py imports its actual implementation and changes only fixture path
and anchor globals. It never calls production-bound main before rebinding. All
dependencies, including check_models.py and models.stat.json, contain inert
synthetic text; no model path is opened, statted or traversed. No target adapter,
supervisor process, model, GPU, inference binary or live exposure ledger is used.

Full runs positive, changed-root, changed-dependency, symlink-alias and
missing-file once each. Exact expected JSON, error class/message or errno and
exit status are constructed before execution in job.py and retained alongside
actual output. Every child must have empty stderr and pidfd-confirmed death.
Only captured child identities receive TERM/KILL; no patterns/groups are used.
The child source never spawns descendants. STOP and deadlines interrupt each
case's bounded wait. Source and canonical engine seals are checked at both ends.

Publisher smoke requires exactly four inherited affinity CPUs and an external
fresh FILLER_DRYRUN_RESULT_PATH outside full-results. It runs only positive and
changed-root, uses its own fresh anchor-smoke-attempt fixture and emits SMOKE_ONLY.
Full requires at least four inherited affinity CPUs, uses full-results and a
fresh anchor-full-attempt, and emits SYNTHETIC_ANCHOR_QUALIFIED only after all
five cases. Attempts/results are exclusive-create; no redraw. complete.py checks
literal outer ID, mode, exact case list, matching outcomes and cleanup. Smoke
cannot satisfy full completion.

The owning session published `kpf50-anchor-qual-20261105`; its four-CPU smoke passed the positive and changed-root controls. The full five-control row remains pending. The sealed packet’s embedded preparation flags describe its original preparation, not its publication state. Successful synthetic controls will not establish immutable live storage, authorize target work or qualify a native validator. The production supervisor remains unchanged and disabled.

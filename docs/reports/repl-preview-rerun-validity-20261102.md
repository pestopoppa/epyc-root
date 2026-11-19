# D-RI-PREVIEW-1.1 rerun validity amendment

Predeclared 2026-11-02, before the rerun. This amends the frozen
`artifacts/queue-builders-3-20261021/dripreview1/PREDECLARED.md`; it does not
change its fixture, model, renderings, sample count, sampling, or report-only
comparison rule.

For each role/rendering cell, `no_answer / n > 0.20` invalidates that cell.
Exactly 0.20 remains valid. A run containing any invalid cell is invalid for
the comparator: retain its raw replies and counts for diagnosis, but emit no
belief sidecar and draw no rendering comparison from it. Missing or incomplete
cells are likewise not comparator evidence. Never reuse the prior run's result
or cell files: their replies were not retained and all 90 classifications were
`bad_final`.

The repaired driver must retain every reply, reject legacy resume rows lacking
reply text, and report validity explicitly. Before the full rerun, replay three
newly captured replies through `run_reply` and document what happened. Use a
fresh output directory; verify model and other inputs before row publication.
The original 15–25 minute estimate plus loading is the planning estimate until
the replacement launcher establishes a better one.

Independent review found an additional publication gate: the root belief
adapter currently accepts any complete non-mock result without checking cell
validity, so a direct adapter invocation can emit even the old invalid run.
Harden and test the adapter itself as well as the driver, and make the launcher
reject an already-complete invalid result on resume before publishing the row.

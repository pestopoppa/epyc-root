# Question-sidecar persistence status

Bounded per-batch initialization, append/fsync return counts and completion-marker state survive aggregates, decision filtering and role summaries. Archive completeness means all writer calls returned. In-memory grades, dispositions and denominators are unchanged; empty batches are not applicable and legacy lists have unknown status.

The list-compatible result owns batch status. Failure reasons contain at most eight unique operation/type/errno entries with bounded strings and no exception path/message. Failed append plus successful completion marker remains incomplete. Existing sidecar framing is unchanged.

[Native evidence](../../artifacts/ni07/run-37463260425/README.md) passes nine full-module cases covering serial/concurrent success, initialization/append/completion failure, partition filtering and empty/legacy controls. Original37461378205 has a diagnostic NULL receipt (unnamed JUnit case, summaryNone, no native row), not an absent receipt. Original37462303467 remains FALSE6/9 after three fixture expectations used0..1 instead of the existing0..3 quality scale. MAIN caught the metric baseline mistake; only test assertions changed. Originals were not resealed. No model, live eval, host test or serving change.

# Relative-clock stale task — source closure

The published APP test `test_recent_eval_qids_excludes_only_rows_inside_recency_window` already generates UTC timestamps relative to now: old minus180days and recent minus5days against its60-day window. MAIN checked Git blob `722fe7e4346aead16f19daf7fc49baa8d2e1d752` at `adfe61e93e17134948cd2360c20b1679808d10ec` and exact function AST, including existing behavior assertions. The historical July1 fixture no longer exists in this case. Close the existing source requirement without duplicate code.

Static source review only; no project tests/imports, blanket red-baseline resolution or whole-unit-suite GREEN claim. Existing measurement/native carrier and grading rules unchanged. Manual blast radius LOW: stale task/doc closure only.

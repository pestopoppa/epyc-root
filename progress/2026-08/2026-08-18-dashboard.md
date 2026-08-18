# 2026-08-18 — AutoKernel dashboard campaign selection

- Fixed `/api/kernel/live` campaign selection so a held controller wins, followed
  by the terminal campaign with the newest producer-authored progress. Deployment
  config mtimes no longer replace launched campaign truth.
- Added `newest_unlaunched_deployment` as separate availability context and
  rendered it in the activity hero as “sealed, not launched.”
- Reproduced the live v5/v6 state: v5 remains `failed` at `evidence_binding`, while
  v6 is separately reported as unlaunched.
- Added API and DOM acceptance coverage for failed-v5 plus unlaunched-v6
  coexistence; abandoned/retest history remains collapsed.
- Validation: 117 dashboard unit/DOM tests pass; `git diff --check` and
  `py_compile` pass. The environment has no `pytest` module, so the pytest-only
  runtime-JS module was not runnable here.
- The :8100 dashboard was not reloaded; deployment remains under operator/main
  session control.

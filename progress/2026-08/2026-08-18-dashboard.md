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
- Validation: 123 dashboard unit/DOM tests pass; `git diff --check` and
  `py_compile` pass. The environment has no `pytest` module, so the pytest-only
  runtime-JS module was not runnable here.
- The :8100 dashboard was not reloaded; deployment remains under operator/main
  session control.
- Live-v7 follow-up: older unlaunched bundles are now omitted from the
  forward-looking field. Exact coverage proves active v7 supersedes unlaunched
  v6 instead of presenting v6 as “available next.”
- Live-v7 terminal follow-up: a lockless `planner_completed` with no later
  critic/state/checkpoint is now a failed `planner_validation` boundary. The
  hero names the missing exact-exception telemetry, forbids resume, and shows
  GPU screening as not reached; explicit future validation-failed/refused events
  are also consumed.
- Live-v8 ordering follow-up: `critic_pending` plus an active critic actor now
  keeps the hero/pipeline in critic review. Authorization and resource admission
  remain not reached until their own durable boundaries; exact API/DOM coverage
  pins the seq-3 planner-checkpointed state.

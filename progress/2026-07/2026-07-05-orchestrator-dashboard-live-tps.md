# Progress — 2026-07-05 — Orchestrator AutoPilot Dashboard: live stream + tok/s fixes

Scope: the orchestrator AutoPilot dashboard served at `:8000/dashboard`
(`epyc-orchestrator`), distinct from the epyc-root handoff hub at `:8100`
(see `2026-07-05-dashboard-hub.md`).

## Problem (operator report)

Three regressions on the AutoPilot dashboard:
1. Clicking a live inference opened with the running output **frozen** instead of
   streaming in real time.
2. Completed tasks did **not** show tok/s (neither the summary card nor the
   expanded chat-completion detail).
3. The Topology panel no longer showed **live tok/s per role** during generation —
   you had to wait for a trial to end to see machine speed.

## Root cause (single origin)

All three trace to the **2026-06-26 v6 llama.cpp cutover**, which dropped
`prompt`/`content` from `/slots`. The dashboard's live-inference and speed
features had to move to the structured tap (`inference_tap_events.jsonl`); that
migration was left incomplete:

- **Bug 1**: live-tap-panel rows (`openStructuredTapRequest`) never opened the
  per-token SSE — they re-rendered `req.response` from the structured_tap poll,
  which parses only a **1 MB tail** of the ~400 MB tap. A single request's chunk
  stream slides out of that window, so the body can't coherently grow (observed:
  20 requests all `response_len=0` with 1507 chunks in the last 1 MB). Also
  `task_stream` resolved `tap_<request_id>` ids by the `task_id` field, which
  never matches, so the SSE would have idle-timed-out even if opened.
- **Bug 2**: `scan_orchestrator_tasks` captured `duration_s` but **dropped**
  `tokens_generated`/`generation_ms` — both present in every `task_completed`
  event (`chat_pipeline/telemetry.py::llm_completion_meta`).
- **Bug 3**: `topology_activity`'s `avg_tps_recent` came **only from terminal
  `timings` events** (emitted at completion). chunk events carry no token timing
  (`text_len` + `ts_epoch` only), so no per-role rate existed mid-generation.
  Bonus: `running` was falsely `False` for actively-serving roles.

## Changes (epyc-orchestrator)

| File | Change |
|------|--------|
| `src/api/routes/dashboard_tap.py` | `_parse_structured_tap_requests`: record first/last chunk `ts_epoch`; add `tps_live = (chunk_count-1)/(last-first)` for `status==running` (each chunk ≈ 1 token; span-rate self-corrects for tail truncation). |
| `src/api/routes/dashboard_snapshot.py` | `scan_orchestrator_tasks`: carry `tokens_generated`/`generation_ms`/`prompt_eval_ms` through terminal events; compute guarded `tps = tokens/(gen_ms/1000)`. |
| `src/api/routes/dashboard.py` | `topology_activity`: aggregate per-role `live_tps`/`live_tps_n` from running requests' `tps_live`; revive dead `avg_tps_recent` from completed-task `tps`; flip `running=True` on live tap activity. `task_stream`: prefix-dispatch `tap_` ids to `_find_structured_request_by_id` (reverse-grep recovers the full, growing body) while chat-* ids keep resolving by `task_id`. |
| `src/api/routes/dashboard.html` | Extracted `startDetailTokenStream()` shared per-token SSE helper (reused by `openDetail` + `openStructuredTapRequest`); added `_tapDetailStreamOwned` flag so the 0.5 s poll can't clobber the streamed body / export accumulator (during or after completion); completed-card `· N t/s`; `openDetail` decode line; topology strip prefers `live_tps` ("N t/s live") over `avg_tps_recent`; `running`-count fallback to live-tap instances; reset the flag on every panel open/close. |

## Verification

- **Backend unit tests** (synthetic data, venv python): `tps_live`=10.0 (running) /
  None (complete); completed `tps`=35.0 / None (failure, no telemetry). Pass.
- **`tap_` SSE dispatch** against a real completed request `chat-dbfd2314:4b8e0a1a`:
  recovered the **full 2438-char body** (`reset:true`) then `done:tap_complete` —
  previously this idle-timed-out. Pass.
- **Deployed** via `orchestrator_stack.py reload orchestrator` (new orchestrator
  PID `1924161`, health 200). Live endpoints now return `live_tps`/`live_tps_n`;
  `running=True` for `worker_general`. `dashboard.html` is re-read per request
  (hard-refresh the tab to pick up HTML/JS).
- Frontend inline JS passed `node --check`.
- Method: root causes confirmed by a 4-agent adversarial verification workflow +
  primitive data observation before any edit.

## Deferred / blocked

- **Live end-to-end test of a *new* generation is blocked** by an unrelated stack
  issue: `/chat` returns 502 `Connection refused` to frontdoor on `:8070`, while
  frontdoor's server launched on `:8080` (`orchestrator_state.json` port=8080 vs
  `model_registry.yaml` port=8070). This broke at the **08:14 stack relaunch**
  (32 min before the dashboard reload) and blocks all orchestrator inference,
  autopilot included — **not** caused by the dashboard changes. Likely a
  side-effect of the concurrent episodic-FAISS/stack-restore work (see
  `2026-07-05.md`, which refreshed `stack_priors.yaml`/`model_descriptors.yaml`).
  Once `/chat` is restored, run a live generation to visually confirm incremental
  token streaming + "N t/s live" on the strip.

## Notes

- Shared-tree hygiene: only the 4 dashboard files were committed (explicit
  pathspec); the parallel agent's uncommitted stack files were left untouched.
- No handoff/index changes (no dashboard handoff exists; none created).
- Memory `project_v6_slots_no_prompt_content` updated with the three follow-on fixes.

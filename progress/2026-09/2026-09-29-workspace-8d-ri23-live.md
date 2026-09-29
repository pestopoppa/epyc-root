# 2026-09-29 — workspace-8d (RI-23 lane live, RI-23a applied, RI-22 fixed in production; tap cleanup recorded)

Per-task bookkeeping wrap-up. Handoff text only. In this task: no inference, no server started or stopped, no index
row edited. The index edits are prepared for the owning session.

## What landed (recorded in the handoffs)

- **RI-23 = OP-69 option (a)** (`routing-intelligence.md`) is ticked.
  - The operator approved landing in chat. Orch `e0787feb` is on main.
  - The flag `thinking_roles_chat_lane` was enabled in production at `a504ba28` (`PRODUCTION_FEATURE_WAVE_OVERRIDES`).
    Derived files followed at `c62fcadd`, then an API-only reload.
  - RI-22's unparseable→`unavailable` verdict telemetry landed with it.
- **RI-23a** is ticked.
  - Receipt `RATIFY-RI23A-20260929` was signed by the operator (Daniele) and committed on root at `05e13e75`.
  - Lanes merged: research `7b9bc565`, orchestrator `8991000d`, root `3a958060`. Derived files at `3fb01cc9`,
    then an API-only reload. API PID 1080404 started 15:02:26Z with both flags in its env.
  - Before the reload, `chat_template_kwargs_for_role('coder_escalation')` returned
    `{enable_thinking: True, reasoning_effort: medium}`.
  - The pipeline check shows only the known :8074 ARCHSWAP-B2 `slot_save_path` drift. `declared_env_attestation` is ok.
- **Live serving proof, 15:04Z** (under workspace-76's "go").
  - `architect_critic`, `coder_escalation` and `ingest_long_context` were all served by :8083 with the right
    `api_role`.
  - Each returned a clean "17 × 23 = 391." with `reasoning_content` present.
  - Evidence: `/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260929T150402Z/`.
- **RI-22** (review gate no-op) is ticked, fixed in production by RI-23.
  - The verdict now runs thinking-off with `skip_suffix` on the chat lane.
  - In the RI-23b A/B, verdicts parsed 2/2 against 0/2 before. RI-18's "do reviewed answers improve" half is unblocked.
- **TE-reopen** (`thesis-experiment-orchestrator-vs-strongest-model.md`) now has its RI-22 prerequisite marked
  satisfied. The ARCHSWAP-3b P2/P3 item records the 15:04Z proof, so the dropped reasoning expectation is met.
- **HS-OD-10** (`harness-selection-and-integration.md`) is ticked: landed as orch `5ddb7320` and live.
  - The planner check it waited on was done by a code read at orch `origin/main`.
  - `_local_planner_prompt` wraps the drafts and critiques in JSON-only output contracts at head and tail.
  - The dropped `frontdoor` and `ingest_long_context` suffixes asked for prose and headings, which contradicts
    those contracts. Losing them is an improvement, so nothing is added back.
- **OP-67** was already recorded (root `04a82bc8`). No active handoff still carries it as pending.

## Test-written tap cleanup

- The operator ran `clean_tap_events.py --apply` on 2026-09-29.
  - It removed 3,668 events: rule a took 2,844 (role_a/role_b pytest PIDs), and rule b took 824 (206 non-API,
    task-less requests to the `test-native-wire` backend or port 0).
  - It kept 267,312, verified byte-identical in order, with the lock held 20.35 s.
  - Backup and `clean_run.json` are in `/mnt/raid0/llm/tmp/inference_tap_backup_20260929/`.
- The plain `inference_tap.log` still has 738 test sections, and it can only be rewritten while no `TapWriter` holds
  an fd. This is filed as **NIB2-91** in `non-inference-backlog.md`, to be done at a planned API stop.

## Prepared for the owning session (not applied)

- The master operator queue drops OP-69, which is archived under the OP-67/OP-68 convention.
- RTG-30's next action moves off RI-22 to RI-16.

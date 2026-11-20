# 2026-11-20 pipeline-mgmt (covers 2026-11-19 to 2026-11-20)

## Dispatcher
- c160f8d59 added idle-slot unpark without an event, dropped filed sink events, made RESUME-STALL actionable. 13370aead reverted it to event-only.
- 11 sessions retired; heterogeneous-slot-fabric-residency gated; agentic-rocm-kernel-authoring retired rather than gated.
- Fable audit: the dispatcher does not earn its cost. 11.6B tokens bought 82 verdict ticks.
- Redesign "taskflow" drafted: /mnt/raid0/llm/tmp/dispatcher-redesign-20261119/DESIGN.md. Build box TASKFLOW-STAGE1 (churn-pipeline.md).
- WS-4 caveat: a woken session ignores a wake whose message has no imperative (box WS4-WAKE-IMPERATIVE).

## Filer and rowflow
- bba1c010a: DROP-as-pass guard and owner-only `--correct`; c6-admission-live-proof-r12 corrected to inconclusive.
- 41041359b: queued-GPU-smoke WAIT, queue_status and owner routing; roster row `autokernel` added.

## Orchestrator (epyc-orchestrator)
- Test fixes 68c686e2, 75e6d978 and 23 commits up to 4451e671.

## Handoff standard
- Spec: /mnt/raid0/llm/tmp/dispatcher-redesign-20261119/HANDOFF-STANDARD.md (operator decisions at its end).
- Stage A ba3adabf1 + hotfix 671a6adf7. Stage B e14edec25..e5784a93f.
- Lint-OK canary 20.5% to 21.6%, short of the 45% target: remaining failures need content rewrites (Stage C, box HS-STAGE-C).

## AK audit
- 14 requirements triaged into /mnt/raid0/llm/tmp/dispatcher-redesign-20261119/AK-REQS-FIXES.md. Fixes F2-F9 and hooks C1-C6 are D9-acked; build starting (boxes AK-FIXES-F2-F9, AK-HOOKS-C1-C6).

## Model
- Q8 model registered (epyc-inference-research 1c8d54874).

## Handoff edits (handoffs/active/churn-pipeline.md)
- Added open with `done when`: TASKFLOW-STAGE1, HS-STAGE-C, AK-FIXES-F2-F9, AK-HOOKS-C1-C6, WS4-WAKE-IMPERATIVE.
- Added done: HS-IDLE-UNPARK-REVERTED, DISPATCHER-FABLE-AUDIT, FILER-DROP-AS-PASS-GUARD, ROWFLOW-QUEUED-GPU-SMOKE-WAIT, ORCH-TEST-FIXES-1120, HS-STAGE-A, HS-STAGE-B, MODEL-Q8-REGISTERED.

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

## Wrap-up 2 (since 1f2963cc7, ~09:30Z to ~13:00Z)

### Handoff standard
- Stage B fixes; Stage C C0-C8 (cbc7f4908..9557039f6); fixes 1a279e306 (holds fail closed), f5938d39b, c8f6e858d, 9a1fd1f8b, 4759de3fa, 154a4e4ed.
- Proposals: 51 NEEDS-OWNER children, 66.9k haiku tokens. C6 sample 86.7 percent (criterion 90, not met).
- Ratify package ready for operator signature: scripts/operator/ratify_handoff_standard_20261120.sh.
- Durable design docs moved out of /tmp into docs/design/: taskflow-dispatcher.md, handoff-standard.md, handoff-standard-stage-c-brief.md, ak-audit-reqs-fixes-20261120.md, owner-roles-{taxonomy,draft,review,fullhistory}-20261120.md.

### AutoKernel audit fixes
- F2-F9 (3be7715e1..06d920bfd) and review fixes; hooks C1-C6 (66eb1ad91..c1d3a8da6); zombie-pid b2cc849a4; GPU packing inversion c0cf5d5a2 (deploying); allocator test c0eff9bbf.
- Manifest fix f397a4b59: holds.py was missing from the deploy and the dispatcher was down about 3 min.

### Deploys
- rowflow at b2cc849a4 and f397a4b59 (--allow-open-grants, operator-approved). Dispatcher restarted as pid 1605174 with holds support; default Codex model gpt-6.1-sol changed to gpt-6.1-terra.

### Owner roles
- 3 role-file drafts on local branch pm-owner-roles (not pushed); pending operator approval (box RTG100-OWNER-ROLES).

### Taskflow Stage 1
- 104a8f154 (schema, dispatch, verify, opencode local-LLM adapter). Canary row tf1-canary-35b-c14-gpu-r1-20261120 published, GPU smoke queued (C14, qwen3.6-35b-a3b-q8-gpu-mtp, 10 tasks).

### Codex budget
- Weekly budget exhausted (reserve reached about 11:50Z, resets in about 95 h). Audit: waste came from sol-tier on clerical work, context replay and rotations.

### Memory
- Coordinator is the single entry point; standing D9 for AK fixes.

### Handoff edits (churn-pipeline.md)
- Ticked AK-FIXES-F2-F9, AK-HOOKS-C1-C6 (belief: cc). HS-STAGE-C left open with a PARTIAL note (ratify signature, C6 and canary outstanding).
- Added boxes: RTG100-HS-RATIFY, RTG100-HS-C6-DROP, RTG100-OWNER-ROLES, RTG100-TASKFLOW-CANARY-RESULT, RTG100-GENFILE-HOOK-REFUSE.
- Wiki sweep deferred (see report).

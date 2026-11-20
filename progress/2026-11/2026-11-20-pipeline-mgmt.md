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

## Checkpoint (wrap-up 3): compute STOPPED for AutoKernel

All pipeline-mgmt compute is stopped at the operator's request to free resources for AutoKernel. `tf1-cpu-s1b` was withdrawn and is TERMINAL. This section records state and the resume point.

### Taskflow Stage 1 canary (GPU, rounds r1-r7d)
- Seven GPU rounds r1-r7d; none verified more than 2/10. Verdict stays FIX-HARNESS (no model verdict). Round log: `docs/design/taskflow-stage1-canary-findings.md`.
- Clean A/B on the same 8 boxes: r6c (no brief) 0/8; r7d (strong briefs) 0/8, with 3 tasks editing but failing verify.
- Harness fixes pushed: `3edb0b60e` (proxy lane-path repair, shell allowlist incl. cat / `sed -n` / pipes, vidya wiring VB-TASKFLOW-CANARY-WIRE) plus the earlier ones listed in the findings doc.
- Packet-only Sonnet calibration (`/mnt/raid0/llm/tmp/taskflow-calibration-20261120/PACKET-ONLY-SONNET.md`): Sonnet verified 5/7 from the packet alone. Recurring packet defects: (a) acceptance commands that `cd` into the shared clone; (b) no working test interpreter (system python lacks fastapi, the repo venv lacks pytest); (c) stale brief details; (d) LOOP-62 not doable as specified. Conclusion: the tasks ARE doable, so the 35B's 0 is mostly harness/env/packet, not task difficulty.
- AutoKernel's prefix-cache replay of r7d: server-side caching is about 93%; the remaining misses are opencode's layout breaking the prefix 4 tokens early.

### Task-brief layer
- P1-P5 landed: `1f4c564f1`, `e4bca9fa0`, `3ee2a84f3..05b623695`, `5edfc86ad`, `4b11de46b` (quality gate), `951503e06` (rule f). ID restore: `61166d386`, `a86dd4db4`.
- Brief backfill PAUSED by operator ruling until the 35B saturates. Workflow run `wf_442b998f-d7d` is stopped; its 12 worktrees `/mnt/raid0/llm/worktrees/pm-bfw-*` hold about 160 uncommitted briefs, kept on purpose for resume.

### Keeper / infra
- Keeper fixes deployed: `c0cf5d5a2` (GPU packing), `4015766ac` + `build_pocket_policy.json` (build pocket), `73f498cb2` (partial-quarter claims, supersede attribution).
- gitnexus reindex as keeper rows: `a7001a7d3`, plus box GNX-REINDEX.
- Keeper v13 re-pinned with operator approval.
- Research clone fast-forwarded 330 commits; the `model_registry.yaml` comment patch is saved at `/mnt/raid0/llm/tmp/research-clone-ff-20261120/model_registry-comment.patch`.
- Owner roles: six agent files at `a85ded1c3`, plus roster rows.
- RATIFY-HANDOFF-STANDARD-20261120 signed (`98342afc8`). RATIFY-TASK-BRIEF-20261120 is PENDING the operator's run of `scripts/operator/ratify_task_brief_20261120.sh`.
- In flight at checkpoint: a fix so `publish_row.py` stops tripping the NIB2-108 hook (docstring literal, plus notify/filing flag roots, plus a deploy scan gate), being built by a subagent, NOT yet deployed.

### RESUME POINT (in order)
1. Run the r8 calibration on CPU q1/q2 only, when compute is released: 5 easy tasks + thinking on/off A/B + format audit. Staged at `/mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8-20261120`; needs spec.json, SOURCE.sha256 and the measured CPU rate.
2. Fix the packet defects Sonnet found (worktree-relative acceptance, a working interpreter, re-scope LOOP-62).
3. Iterate until the 35B saturates.
4. Run the 27B (stack-registered Qwen3.8-27B-Q8_0, DFlash2 recipe, AK champion launch) only on tasks the 35B still fails.
5. Then finalize the brief format and resume the backfill.

### Handoff edits (churn-pipeline.md)
- TASKFLOW-STAGE1-CANARY: dated status/resume line added (not ticked).
- Boxes added (with briefs): TF-ACCEPT-CD-CLEANUP, TF-DUPID-HS4, TF-DUPID-KPF-18-0D, TF-DUPID-KPF-64-3, TF-DUPID-DCP6, CODEX-BFCL-CJ3D-REPUBLISH, KEEPER-GRANT-CAP.
- No ticks this wrap-up; checklist-sync and belief-capture gates have nothing to tag. Pruning and wiki sweep deferred to operator `/wrap-up`.

# 2026-09-28 — orchestrator design session (workspace-8d)

Continues [`2026-09-27-orch-design.md`](2026-09-27-orch-design.md). This note covers the ARCHSWAP bring-up and the
operator's decision to park UFH-13.

## ARCHSWAP-20260927 bring-up (the architect role swap)

- **Signed.** The operator signed the package from a terminal on 2026-09-28 at 02:52:34Z. The receipt is
  `artifacts/operator/receipts/RATIFY-ARCHSWAP-20260927.json` (`signature_channel: terminal`, O-2 `follow-model`,
  O-3 `B1`). This resolves OP-68.
- **Merged.** The three lanes are on main: orchestrator (with the A-3 prewarm/scout region-claim fix `9a4785e1`),
  research `76cecec4` and root `ec7748aa`. Orchestrator `0cc516b4` is the derived-file provenance commit.
- **State relabelled.** `relabel_state.py --apply` ran (operator-approved in chat). The backup is
  `epyc-orchestrator/logs/orchestrator_state.json.pre-archswap-20260928T041545Z`.
- **B1 reload.** One API-only reload. Then `v1_escalation` was added to production's feature wave (orch `6d024ced`,
  operator-approved), followed by a second API-only reload. The API is PID 1100541 with
  `ORCHESTRATOR_FEATURE_V1_ESCALATION=1` in its env. The flag is opt-in per request (`x_escalation`), so a request
  without the key behaves as before.
- **Checks.**
  - `stack_change_pipeline.py check`: only the two known `slot_save_path` drifts, and `declared_env_attestation: ok`.
  - P4: the URL snapshot is identical to the evidence (19/19).
  - The reviewer and planner resolve to `architect_critic` (the 27B).
  - The runtime-facts state routes `architect_general` → `:8074`, and `architect_critic`, `coder_escalation` and
    `ingest_long_context` → `:8083`.
- **Remaining** (thesis handoff ARCHSWAP-3b and ARCHSWAP-4):
  - P1, the `:8074` escalation proof: `/mnt/raid0/llm/tmp/archswap-20260927/serving_proof.sh`, in a CPU window.
  - P2 and P3, the `:8083` proofs: `proof_8083.sh`, only on workspace-76's "go" at a DS41 critic pass.
  - B2: relaunch `:8083` on workspace-76's go, and `:8074` at a long idle gap. This clears the two drifts.
- **RI-21 closed.** The escalation map and the graph both end at `architect_general` now, so they agree. No critic node
  was added; that is deliberate and is the receipt's `not_in_scope` item.

## Operator decision: UFH-13 PARKED, and a new working direction

Made in chat on 2026-09-28 (session https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ).

- **Why park.** Arm A2's escalation is driven by episodic-memory Q-values. The store holds 64,396 memories, the newest
  written 2026-09-24, all learned while `architect_general` was the 27B. A2 would therefore test an untrained router
  on a new stack, and a low G would not separate "routing does not help" from "routing has not learned this stack".
- **No A0-vs-A1 gap check.** The operator ruled it not worth running: public quality benchmarks already answer whether
  a gap worth routing for exists.
- **Autopilot is deferred** until the operator installs the second MI210.
- **Reopen trigger:** an autopilot run has trained escalation on the swapped stack. Filed as TE-reopen. It starts with
  a review of the escalation design: under the review gate a WRONG verdict is rewritten by `worker_general`, not
  answered by the consultant, which makes G ≥ 0.75 structurally hard. A registered variant in which the consultant
  answers is to be considered. Then TE-pilot and A2 run under the frozen rule.
- **Kept in place:** the runner, the pilot pool, the pre-registration and `v1_escalation`.
- **New direction until the second GPU is in:** infrastructure and design work with the operator, front-loading work
  that must be done eventually. The focus is how best to use Jev techniques in the stack, wiring them properly, and
  properly documenting future gated work. EXL3 inference research belongs to another session.
- **The 2026-09-27 narrowing no longer ranks work.** Items frozen behind UFH-13 stay frozen for their
  inference-bearing steps; their design and documentation work may proceed.

## Bookkeeping

- `thesis-experiment-orchestrator-vs-strongest-model.md`:
  - The status is PARKED.
  - Ticked: ARCHSWAP-1, ARCHSWAP-2 and TE-reload.
  - ARCHSWAP-3 stays open with a progress note, and its P1-P3 proofs are split out as ARCHSWAP-3b.
  - TE-reopen is added, and TE-pilot is marked parked.
- `routing-intelligence.md`: RI-21 is ticked.
- `CURRENT-CAMPAIGN.md`: a 2026-09-28 posture block is added.
- The UFH-13 row and the master OP-68 row are prepared for the main session to apply.

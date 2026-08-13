# Wrap-up division of labor — actionable implementation plan

**Status**: ACTIVE — target contract fixed; implementation not started
**Created**: 2026-08-13
**Last refined**: 2026-08-13
**Priority**: P1 — task-boundary durability, fleet documentation consistency, and compute-blocker
visibility currently depend on contradictory procedures.
**Owner**: `coordinator-agent` (lifecycle and integration owner)
**Reviewer**: `auditor`
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), `RTG-51`
**Related work**: `RTG-48` coordinator failure modes; `RTG-34` session-bus dispatcher
**Rollout state**: `off`; no current worker behavior changes merely because this plan exists.

## Decision and outcome

The operator's role split is decided and is not reopened here:

- Worker mains perform a lightweight, durable **log checkpoint** at every completed or genuinely
  blocked task boundary. They do not run the fleet's heavy wrap-up.
- Coordinator validates checkpoint receipts, integrates accepted lane commits, controls context
  transitions, and relays fleet-wide wrap triggers. It wraps only its own coordination surfaces.
- Auditor performs one single-writer **heavy wrap** for an immutable set of accepted receipts.
- Inference alone judges live resource compatibility and grants compute. Coordinator prioritizes
  eligible work; neither Coordinator nor Auditor manufactures hardware state.

This plan replaces the original planning stub. The audit found that its direction was sound but its
mechanics were not executable: a worker commit was not visible across lanes, blocked work had no
typed receipt, the proposed batch index is a single-writer execution campaign, per-agent progress
logs were rejected by the live currency checker, hooks wrote derived index state after worker
commits, and the long-lived wrap lease could be reclaimed by a second same-role process. Current
structural checks pass despite those defects, so each contract below has a negative control.

## Vocabulary

- **Task boundary**: the worker completed its task, or progress now requires a named other owner,
  operator decision, resource grant, or external event.
- **Promptly movable blocker**: the worker has authority and resources to clear it now, within the
  current work unit, without waiting for another owner, grant, decision, or event. This is not a
  task boundary; the worker keeps working.
- **Non-movable blocker**: the worker has exhausted in-scope preparation and can name the owner or
  event that must occur, the evidence, and the exact resume action.
- **Log checkpoint**: the worker-owned transaction that records, validates, commits, pushes, and
  emits a typed receipt for one task boundary.
- **Heavy wrap**: the Auditor-owned transaction that reconciles an immutable receipt cut, files
  follow-ups, compacts handoffs, regenerates indices, compiles documentation, and publishes once.
- **Major checkpoint**: a completed phase or campaign whose integrated state should be reflected in
  fleet indices and the wiki. It does not mean every task boundary.
- **Related work**: the same artifacts, premises, or investigation remain load-bearing.
- **Disjoint work**: productive work needs a fresh context and would not reuse the checkpointed
  task's reasoning.

## Authority and write ownership

| Surface or decision | Sole authority | Other roles |
|---|---|---|
| Task artifacts, source task checkbox, newly discovered source tasks | Originating worker | Coordinator/Auditor verify read-only |
| `progress/YYYY-MM/YYYY-MM-DD-<agent>.md` | Named agent | Receipt validator verifies committed copy |
| Lane commit and lane push | Originating worker | Coordinator verifies remote reachability |
| Receipt acceptance, lane-integration order, `/clear`, follow-on dispatch | Coordinator | Worker reports facts; Auditor may audit |
| Audit verdict and audit follow-up rows | Auditor | Worker retains ownership of source completion state |
| Handoff compaction, domain-index mutation, generated index state, wiki compile | One heavy-wrap writer | Auditor subagents may inspect/propose read-only |
| Compute window grade, compatibility, physical claim, safe drain | Inference | Coordinator ranks only Inference-eligible candidates |
| Cross-lane promotion to `main` | Coordinator integration path | Auditor supplies the reviewed/published packet |

Workers must not mutate domain indices, master generated blocks, wiki manifests, or `main` during a
log checkpoint. Auditor must not flip a worker-owned checkbox or absorb uncommitted state from
another lane. Coordinator must not reconstruct an absent worker checkpoint. Derived files have one
writer and are regenerated only inside the heavy-wrap lease.

The current top-level trust rule forbids handoff and index mutations by subagents without explicit
operator approval. Until the protected amendment in Phase 5 is ratified, Auditor main is the
heavy-wrap writer and subagents are read-only. The proposed narrow exception authorizes exactly one
designated wrap executor per Coordinator request and lease; it does not authorize parallel mutation.

## Lifecycle state machine

| Current state | Event | Required action | Next state |
|---|---|---|---|
| `WORKING` | Promptly movable blocker | Clear it or finish remaining preparation; emit no boundary receipt. | `WORKING` |
| `WORKING` | Task completed | Run a log checkpoint with `outcome=completed`. | `CHECKPOINTING` |
| `WORKING` | Non-movable blocker | Name owner/event and resume action; checkpoint with `outcome=blocked`. | `CHECKPOINTING` |
| `CHECKPOINTING` | Validation, commit, push, or receipt fails | Preserve the completed prefix and retry idempotently; refuse clear/close. | `CHECKPOINT_FAILED` |
| `CHECKPOINT_FAILED` | Missing suffix succeeds | Coordinator validates the pushed receipt. | `CHECKPOINT_RECEIVED` |
| `CHECKPOINT_RECEIVED` | Schema, remote, ownership, or evidence fails | Quarantine receipt with typed reasons; do not audit or integrate. | `REJECTED` |
| `CHECKPOINT_RECEIVED` | Validation succeeds | Emit one immutable `audit-request` for exact SHA/evidence packet. | `AUDIT_PENDING` |
| `AUDIT_PENDING` | `accept` or `accept-with-followups` | Coordinator integrates exact reviewed commit; Auditor owns any follow-up rows. | `DURABLE_BOUNDARY` |
| `AUDIT_PENDING` | `needs-rework` | Coordinator converts findings to ordinary owned backlog work; do not integrate. | `REWORK` |
| `AUDIT_PENDING` | `blocked-evidence` | Request only the named missing evidence; do not integrate. | `EVIDENCE_BLOCKED` |
| `DURABLE_BOUNDARY` | Related work ready | Keep context and continue; heavy wrap is asynchronous. | `WORKING` |
| `DURABLE_BOUNDARY` | Disjoint work ready | Coordinator sends `/clear` alone, confirms it landed, then sends a self-contained brief. | `CLEARING` then `WORKING` |
| `DURABLE_BOUNDARY` | Alternate work exists behind a blocker | Route blocker to its owner and dispatch alternate work by related/disjoint rule. | `WORKING` |
| `DURABLE_BOUNDARY` | Worker reports genuinely dry | Coordinator rechecks the queue, then dispatches or sends close. | `WORKING` or `CLOSED` |
| `DURABLE_BOUNDARY` | `major_checkpoint=true` | Coordinator creates one deduplicated heavy-wrap request with a fixed cut. | Worker stays `WORKING`; wrap becomes `REQUESTED` |
| Any active state | Clear/close requested before a valid receipt | Refuse it and safely finish the checkpoint. | Unchanged |

A worker may continue related safe work after its pushed checkpoint while audit/integration is
pending, but no disjoint `/clear`, close, promotion, or completed-state claim is authorized until the
receipt reaches `DURABLE_BOUNDARY`. A worker never decides fleet-wide dryness and never idles on a compute grant. It reports a durable
blocker, then drains the bus and takes the next compatible task. A normal `/clear` requires a valid
checkpoint receipt plus a disjoint next task; it does **not** wait for heavy wrap. Pre-reboot is the
only standing synchronous heavy-wrap barrier.

## Worker log-checkpoint contract

The implementation is one command/skill backed by one testable program, not a prose checklist:

- `.claude/skills/log/SKILL.md`
- `scripts/coordination/worker_checkpoint.py`
- `tests/coordination/test_worker_checkpoint.py`

For a stable `boundary_id`, it performs this exact order:

1. Verify private-lane identity and resolve the source task by task text, not a stale line number.
2. Update only worker-owned task state: completed tasks flip the exact box and append
   `✅ YYYY-MM-DD`; blockers remain open and gain a distinct task with an exact resume action.
3. Append the boundary result to `progress/YYYY-MM/YYYY-MM-DD-<agent>.md`.
4. Run ownership, checkbox-sync, scoped diff, and task-specific validation gates.
5. Commit only explicit owned pathspecs. `git add -A`, peer shards, and unrelated dirty files are
   forbidden.
6. Push `lane/<agent>` without promoting it.
7. Emit the typed receipt containing the pushed SHA. No receipt exists before a successful push.

Retries return the existing receipt or execute only the missing suffix. They must not duplicate a
progress entry, task row, commit, or bus message. A no-op is valid only when the same `boundary_id`,
commit, and receipt already validate. Failure leaves a machine-readable checkpoint state and never
claims durability.

### Boundary receipt

Add a typed `task-checkpoint` bus kind. It does not replace the existing `task-complete` audit event:
the checkpoint references that event, or the Coordinator synthesizes it exactly once after accepting
a completed receipt.

Required common fields:

```yaml
boundary_id: <agent>:<task_id>:<stable-boundary-sequence>
outcome: completed | blocked | partial
boundary_reason: task-boundary | pre-reboot
task_id: <durable id>
task_text: <resolved checkbox text>
spec_ref: <handoff path plus stable task anchor>
agent: mainA | mainB | mainC | mainD | auditor | coordinator-agent | inference
branch: lane/<agent>
commit_sha: <40-hex pushed commit>
pushed_ref: refs/remotes/origin/lane/<agent>
progress_path: progress/YYYY-MM/YYYY-MM-DD-<agent>.md
handoff_paths: [<owned paths>]
checkbox_flips: [<before/after task identity>]
new_tasks: [<task identity and owner>]
validation: [{command: <argv>, exit_code: 0, evidence_ref: <ref>}]
next_context: related | disjoint | dry | pre-reboot
major_checkpoint: true | false
completed_at: <UTC RFC3339>
```

`outcome=blocked` additionally requires:

```yaml
blocker_class: dependency | operator-decision | external-event | compute
blocked_on: <specific condition>
blocking_owner_or_event: <named owner or event>
evidence_refs: [<durable refs>]
alternatives_exhausted: [<attempted in-scope alternatives>]
resume_action: <first executable action after unblock>
compute_request: <typed request or null>
```

`outcome=partial` is legal only for `boundary_reason=pre-reboot`. It never flips the completion box
and requires the same evidence and exact resume action as a blocker.

Coordinator accepts a receipt only if its author matches the roster/lane, the SHA is reachable from
the stated remote ref, the commit contains the named per-agent progress shard and handoff changes,
and all paths are owned by that worker. A local-only SHA, unsuffixed progress file, peer progress
shard, forged author, or post-commit log edit fails closed.

An accepted receipt produces one `audit-request`. Auditor responds with a typed `audit-verdict`
containing `checkpoint_id`, exact audited SHA, verdict (`accept`, `accept-with-followups`,
`needs-rework`, or `blocked-evidence`), evidence references, findings, and follow-up task IDs.
Coordinator integrates only the first two verdicts. Auditor never directs a worker; rework and
follow-ups return through Coordinator as ordinary owned tasks.

## Heavy-wrap contract

A heavy wrap begins only from a typed `wrapup-request` issued by Coordinator. Valid reasons are:

- explicit operator request;
- an accepted major-checkpoint receipt;
- a pre-reboot barrier;
- an Auditor `wrapup-due` proposal that Coordinator accepts.

The request carries `request_id`, reason, synchronization mode, and the exact accepted receipt IDs
or cutoff timestamp. Receipts arriving after the cut belong to the next wrap. “Auditor cadence” means
Auditor may propose that a wrap is due; it does not authorize an untracked autonomous mutation.

After Coordinator has integrated every eligible lane checkpoint in the cut, the designated writer
acquires one operation-token lease and performs the ordered transaction:

1. Sync from the integrated `origin/main` commit named in the request.
2. Reconcile every included receipt and record every explicit exclusion.
3. File Auditor-owned follow-ups; never rewrite worker-owned completion state.
4. Compact/prune handoffs and update each owning domain index.
5. Regenerate timeline/index state and run structural and ownership checks.
6. Run remaining documentation and freshness work.
7. Compile the wiki as the **last documentation-content mutation**.
8. Commit exact paths, push the Auditor lane, and hand the reviewed packet to Coordinator promotion.
9. Verify promoted `main`, then emit `wrapup-complete` and release the lease in a trap.

The wiki is not literally the final shell command: commit, push, promotion, verification, receipt,
and lease release follow it. A failed asynchronous wrap remains queued and does not stop workers. A
failed synchronized pre-reboot wrap keeps the barrier closed.

`wrapup-complete` names the request and included receipts, exclusions, source and promoted SHAs,
generated-artifact hashes, validation results, wiki manifest/watermark, and lease operation ID.

## Compute-blocker intake and graded window contract

`handoffs/active/inference-batch-loop.md` is **not** the generic intake surface. It is a v7-era,
single-writer execution campaign whose manifest and ledger are owned by `/loop`; its boxes must not
be mutated by Auditor. This plan leaves that authority intact.

The source of truth for compute-ready work is the accepted `task-checkpoint` receipt, its typed
compute request, and Inference's append-only intake dispositions. Coordinator forwards a
`compute-blocker`; Inference alone moves it through
`submitted -> admitted|duplicate|needs-info|rejected -> ready -> planned -> granted|denied -> running -> terminal`.
A daemon builds a reconstructible, read-only projection of admitted/ready records at
`coordination/session-bus/compute_ready.json`; no human or worker edits the generated candidate
block. The existing `coordination/backfill/ready_hint.txt` becomes a pointer derived from that
projection, not a second truth source. Proposed implementation:

- `scripts/coordination/compute_ready.py`
- `coordination/session-bus/compute_ready.json`
- `tests/coordination/test_compute_ready.py`
- schema and relay changes in the existing session-bus files

Each candidate carries task/spec identity, source receipt, minimum window grade, CPU bandwidth
class, GPU/device/VRAM requirements, model and weight identity, estimated load/occupancy/duration,
contention and pausability class, operator gates, expiry, and graph-derived live downstream tasks.

Each disposition carries a stable `blocker_id`, source checkpoint, reason code, and prior-event ID;
status changes are new events, never in-place edits. Auditor verifies coverage during heavy wrap but
does not admit or status the intake. Only Inference emits a typed `compute-window` event:

```yaml
grade: small-model-only | load-then-keep-hot | full-idle
eligible_devices: [<device/region>]
cpu_bandwidth_class: <class>
gpu_vram_available: <bytes plus observation refs>
resident_model: <identity or null>
load_allowed: true | false
starts_at: <UTC RFC3339>
expires_at: <UTC RFC3339>
time_budget_seconds: <integer>
safe_drain_at: <condition/time>
observation_refs: [<multi-sample evidence>]
```

A window grade is a compatibility label, not a total ordering; explicit budgets decide fit. A window
announcement is advisory and never substitutes for the existing typed resource lease.
Inference filters candidates for live compatibility and owns execute/lease choice. Coordinator then
ranks the eligible set deterministically by:

1. explicit operator `must-run` override, if any;
2. number of currently live downstream tasks made fire-ready, derived from a pinned
   `.index-graph.json` hash;
3. direct handoffs unlocked, then transitive open dependants;
4. production priority class;
5. exact window fit, grouping same-weight work for `load-then-keep-hot`;
6. oldest accepted checkpoint;
7. stable blocker ID.

The dispatch contains only the selected finite batch, its rank evidence, window ID, and lease path.
Unknown grades, expired windows, missing evidence, incompatible weights, or unleased execution fail
closed. Inference may skip a higher-ranked candidate only with a typed incompatibility reason for the
current window; Coordinator may not override fit, and Inference may not rewrite leverage or priority.

## Implementation sequence

Each phase has an independent commit and must leave the current workflow usable. Safety repairs land
before role cutover.

### Phase 0 — publish the contract

- [x] Audit current lifecycle, bus, progress, hook, batch, role, and lease contracts. ✅ 2026-08-13
- [x] Replace the stub with this authority table, state machine, typed protocols, migration matrix,
      rollout gates, and acceptance suite. ✅ 2026-08-13
- [x] Correct ownership to `RTG-51`; remove the stale `d7b83ddf` dependency (already in
      `origin/main`). ✅ 2026-08-13

### Phase 1 — repair foundations before changing behavior

- [ ] Change `progress_log_currency()` to validate receipt-bound per-agent progress evidence.
  Keep unsuffixed logs for historical reads only. Add negative controls for local-only SHA, peer
  shard, post-receipt edit, and no-boundary state.
- [ ] **Autonomous writers:** remove `index_state.py` writes from post-commit/merge/checkout hook
      bodies; make `install_timeline_hook.sh` upgrade its marked block; prove a worker handoff commit
      leaves `.index-state.json`, `.index-graph.json`, and master generated content unchanged.
- [ ] **Wiki hook:** ensure ordinary post-commit retrieval refresh cannot mutate
      `wiki/source_manifest.json` or the wrap watermark; give retrieval its own cursor if needed.
- [ ] **Lease:** replace roster/PID reclaim with an opaque per-operation token in a mode-0600 token
      file, store its hash in the lock, require the token for normal release, and audit explicit
      force-release. A second same-roster process without the token must be refused.

Phase gate: focused progress, hook, lease, and concurrent-wrap suites pass, including a negative
control that would have admitted the previous same-role lease collision.

### Phase 2 — implement checkpoint and receipt in shadow mode

- [ ] Add the log skill, checkpoint program, typed schema, relay/fold validation, and idempotence
      journal.
- [ ] Preserve the existing completed-task audit flow without duplicate `audit-request` synthesis.
- [ ] Add Coordinator validation for remote reachability, path ownership, exact task identity, and
      committed progress evidence.
- [ ] Shadow-record complete, blocked, and pre-reboot boundaries without rejecting legacy behavior.

Phase gate: two workers can checkpoint concurrently without sweeping peer hunks; failed validation,
commit, or push cannot produce an accepted receipt; a repeated `boundary_id` produces no duplicate.

### Phase 3 — implement compute-ready projection and admission

- [ ] Add compute request/window schemas, the reconstructible projection, graph-derived leverage,
      stable ranking, and focused bus dispatch.
- [ ] Encode the authority split in Coordinator and Inference role files.
- [ ] Leave `inference-batch-loop.md`, its manifest, and its `/loop` single-writer protocol
      unchanged except for an explanatory cross-reference if useful.

Phase gate: small-model, keep-hot, full-idle, expired, wrong-weight, insufficient-VRAM, and missing
lease cases are deterministic; only Inference can declare compatibility or grant a claim.

### Phase 4 — make heavy wrap atomic and receipt-driven

- [ ] Update `agents/commands/wrap-up.md` for request ID, immutable receipt cut, one designated
      writer, operation-token lease, ordered mutations, Coordinator promotion handoff, and completion
      receipt.
- [ ] Update concurrent-wrap tests: two same-roster executors contend, only one mutates, crash
      residue remains held, wrong tokens cannot release, and all worktrees share the common-git-dir
      lease.
- [ ] Add receipt inclusion/exclusion and post-cut deferral tests.

Phase gate: one real Auditor canary consumes two concurrent worker receipts and promotes one complete,
reproducible wrap packet with no lost generated contribution.

### Phase 5 — migrate standing policy as a protected package

- [ ] Reconcile every superseded instruction in the migration matrix below. Keep protected policy in
      a separate reviewable commit; do not change `human_only_paths.yaml` or its pin.
- [ ] Present the `CLAUDE.md`/`AGENTS.md` and `agents/shared/*` amendment for operator signoff. The
      subagent exception, if retained, must be narrow: one designated writer, one request, one lease.
- [ ] After merge, Coordinator sends each live session a correlated instruction-refresh nudge naming
      the merged SHA and exact files. Each agent rereads its common and role files and acknowledges
      from its own outbox before enforcement.
- [ ] Restart the session-bus daemon at its owner's boundary and prove process start time is newer
      than every changed runtime file.

### Phase 6 — canary, enforce, and retire the old path

- [ ] Add rollout modes: `worker_checkpoint_receipts: off|shadow|enforce`,
      `auditor_full_wrap: off|shadow|enforce`, and `compute_window_plan: off|observe|enforce`.
- [ ] Canary one completed boundary, one non-compute blocker, one compute blocker, two concurrent
      workers, one Auditor wrap, and one simulated pre-reboot barrier.
- [ ] Move to enforcement only after complete, blocked, and pre-reboot cases each pass three
      consecutive real/simulated boundaries with no manual repair and every live role acknowledges
      the new instructions.

## Policy migration matrix

| Surface | Superseded behavior | Required replacement | Gate |
|---|---|---|---|
| `coordination/session-bus/tasks/MAIN-GOALS.md` | Worker behavior does not name the checkpoint transaction | Require checkpoint receipt at every terminal boundary | Phase 5 |
| `coordination/session-bus/tasks/STANDING-MAIN-RULES.md` | Workers full-wrap at major checkpoints; progress path is unsuffixed | Workers checkpoint; per-agent shard; Coordinator triggers heavy wrap | Phase 5 |
| `coordination/session-bus/tasks/post-reboot-session.md` §6 | Each main writes its own wrap-up | Per-worker pushed receipt plus one synchronized fleet wrap | Phase 5 |
| Current mainA–D briefs | Explicit worker `/wrap-up` instructions | Regenerate briefs after common policy lands | Instruction ack |
| `agents/shared/SESSION_LIFECYCLE.md` | Disjoint task and major checkpoint require worker full wrap | Every terminal boundary checkpoints; disjoint then clears; heavy wrap async except reboot | Operator signoff |
| `agents/shared/OPERATING_CONSTRAINTS.md` | Phase-boundary/full-wrap and generic fan-out language conflict with one writer | Separate read-only fan-out from designated mutation | Operator signoff |
| `agents/commands/wrap-up.md` | Manual-only/narrow audit trigger; wiki not literally last; PID-style lease usage | Coordinator request, immutable cut, one writer, wiki last content mutation, token lease | Phase 4 |
| `agents/auditor-main.md` | Full wrap after every audit pass | Audit checkpoint per pass; heavy wrap only from typed request | Phase 5 |
| `agents/coordinator-agent.md` | May tell a main/subagent to wrap without receipt cut | Validate/integrate receipts and issue deduplicated request | Phase 5 |
| `agents/inference-main.md` | Resource selection exists but graded-window division is implicit | Inference owns grade/compatibility/claim; Coordinator owns ranking | Phase 3/5 |
| `CLAUDE.md` / generated `AGENTS.md` | Subagent handoff/index writes forbidden | Preserve prohibition or ratify narrow designated-writer exception | Operator signoff |
| `session_bus_coordinator.py` | Checks only unsuffixed progress file | Verify committed per-agent shard from accepted receipt | Phase 1 |
| Timeline hooks | Regenerate index state after any handoff commit | Timeline-only hook; derived index regeneration inside heavy wrap | Phase 1 |

## End-to-end acceptance matrix

| Scenario | Required result |
|---|---|
| Completed task, related follow-on | Pushed checkpoint accepted; context retained; no heavy-wrap wait |
| Completed task, disjoint follow-on | Pushed checkpoint accepted; `/clear` delivered alone; brief follows confirmation |
| Movable blocker | Worker continues; no terminal blocker receipt |
| Non-movable blocker | Typed evidence/resume action accepted; blocker routed; worker receives other work |
| Compute blocker | Candidate appears in generated compute-ready projection, never directly in `/loop` ledger |
| Failed validation/commit/push | No accepted receipt, clear, close, or success claim |
| Duplicate boundary | Same receipt returned; no duplicate docs, commit, or message |
| Peer or unrelated dirty hunk | Excluded from pathspec; checkpoint either succeeds safely or refuses |
| Major checkpoint | Exactly one asynchronous wrap request for an immutable cut |
| Concurrent Auditor executors | One enters; all others are refused without the operation token |
| Receipt after wrap cutoff | Deferred explicitly to next wrap |
| Graded compute window | Only compatible, leased tasks dispatched in deterministic order |
| Pre-reboot | Every roster receipt and Inference drain validates; one synchronous heavy wrap; then ready |

Required validation includes the worker/checkpoint tests, full session-bus schema/relay/fold suite,
progress-currency tests, hook installer/non-writer tests, serialized-push and concurrent-wrap tests,
compute-grade/ranking tests, agent-file validators, `index_state.py --check`, claim grammar, README
freshness, and wiki manifest/lint checks. Passing the current legacy suite alone is not acceptance.

## Rollout and rollback

Start `off`, then `shadow`, then `enforce`. Shadow mode records and validates the new receipts while
legacy behavior remains available. Enforcement is fleet-wide only after the protected policy package,
live daemon reload proof, and instruction acknowledgments land.

Immediately return the affected flag to `shadow` or `off` if a compliant worker gets a false progress
defect, two heavy-wrap writers enter, a worker changes a generated/index/wiki surface, a pushed
receipt cannot be reconstructed, a source receipt is omitted, a wrong compute grade admits a task,
promotion loses prior state, or any live role has not acknowledged the instruction SHA.

Rollback never deletes receipts or force-pushes. Pause new heavy wraps, let workers keep checkpointing
their lanes, inspect the lease, force-release only proven residue with an audit reason, and regenerate
derived state from authoritative handoffs under one valid lease. Keep independent safety fixes
(per-agent progress support, autonomous-writer removal, and lease hardening) unless their own tests
fail.

## Pre-reboot barrier

1. Coordinator announces a cut and stops dispatching work that cannot reach a safe drain point.
2. Every worker finishes or safely stops its unit, pushes a checkpoint with
   `next_context=pre-reboot`, and names the resume action for incomplete work.
3. Inference drains active work and records/releases physical claims under its own contract.
4. Coordinator validates the roster receipts, integrates the cut, and checkpoints its coordination
   surfaces.
5. Coordinator issues one synchronized `wrapup-request` with the complete cut.
6. Auditor performs and publishes the heavy wrap.
7. Coordinator validates `wrapup-complete` and roster coverage. Only then is reboot readiness true.

A missing/unpushed worker receipt, unreleased claim, failed promotion, missing wiki watermark, or
failed heavy wrap keeps the barrier closed.

## Immediate next action

Implement Phase 1 as three independently reviewable safety changes, in this order:

1. repair receipt-bound per-agent progress currency;
2. remove autonomous derived-state writers from hooks;
3. harden the cross-process wrap lease with operation tokens.

Then implement the worker checkpoint in shadow mode. No remaining design choice blocks those phases.
The only operator-only action is approval/merge of the protected Phase 5 policy package and any
narrow subagent-writer exception.

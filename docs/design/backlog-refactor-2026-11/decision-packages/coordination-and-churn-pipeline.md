# Decision package: coordination-and-churn-pipeline

Destination handoff `handoffs/active/coordination-and-churn-pipeline.md` · fold 18 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 11 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Restart the churn pipeline (grants revoked, dispatcher/keepers/watchdogs/filler_run13 stopped)?

- Context: `handoffs/active/churn-pipeline.md:114@7eb7a4a3c911` (manifest `handoffs/active/churn-pipeline.md:114@3ac825873dfb`, id `04d91e93c846`)
- Gated worker box(es): `handoffs/active/churn-pipeline.md:114`

- **Option A (recommended)**: Restart after the backlog-refactor publish gate (BRF-T6-1) is installed. *Tradeoff:* Rows re-enter through the new lint gate.
- **Option B**: Restart now. *Tradeoff:* Compute resumes sooner; rows bypass the lint the refactor adds.
- **Option C**: Keep stopped. *Tradeoff:* No compute use.

**Recommendation: A.** The stop coincided with the refactor; restarting behind the publish gate prevents re-admitting malformed rows.

## 2. D9 acknowledgement: publish the two-file cadence comment correction (RTG48-C49, patch sha 9c191746...)?

- Context: `handoffs/active/coordinator-role-failure-modes-and-refactor.md:1505@7eb7a4a3c911` (manifest `handoffs/active/coordinator-role-failure-modes-and-refactor.md:1505@3ac825873dfb`, id `7c3a4f84efed`)
- Gated worker box(es): `RTG48-C49-COMMENTS-D9` (handoffs/active/coordinator-role-failure-modes-and-refactor.md:1505)

- **Option A (recommended)**: Acknowledge. *Tradeoff:* Comments become correct; executable behaviour identical.
- **Option B**: Decline. *Tradeoff:* Stale comments remain.

**Recommendation: A.** Comment-only, behaviour-identical change with a pinned patch hash.

## 3. R-23: if check (b) shows A-9 is now YES (thread attribution exists), reopen R-17's dissolution?

- Context: `handoffs/active/coordinator-role-failure-modes-and-refactor.md:648@7eb7a4a3c911` (manifest `handoffs/active/coordinator-role-failure-modes-and-refactor.md:648@3ac825873dfb`, id `2c2dcc042a45`)
- Gated worker box(es): `handoffs/active/coordinator-role-failure-modes-and-refactor.md:648`

- **Option A (recommended)**: Run checks (a) and (b) first; decide only if (b) resolves YES. *Tradeoff:* Cheap checks; no premature reopening.
- **Option B**: Reopen R-17 now. *Tradeoff:* Skips the evidence the box asks for.

**Recommendation: A.** The box makes the operator call conditional on (b).

## 4. AUD-10: re-land the narrow single-branch `git clean` guard from `03e17111`, owned by mainD?

- Context: `handoffs/active/coordinator-role-failure-modes-and-refactor.md:755@7eb7a4a3c911` (manifest `handoffs/active/coordinator-role-failure-modes-and-refactor.md:755@3ac825873dfb`, id `2fb7b3a1b87f`)
- Gated worker box(es): `AUD-10` (handoffs/active/coordinator-role-failure-modes-and-refactor.md:755)

- **Option A (recommended)**: Re-land the clean branch only. *Tradeoff:* Would have refused the 08:20Z corpus-destroying command; models agent-typed Bash only.
- **Option B**: Leave reverted and correct the record only. *Tradeoff:* No guard; the record is still corrected.

**Recommendation: A.** The branch was not among the two HIGHs and would have blocked the actual incident.

## 5. AUD-15 / R-8: gate the auto-loaded instruction surfaces (CLAUDE.md, agents/AGENT_INSTRUCTIONS.md, agents/shared/*.md) - F-19.

- Context: `handoffs/active/coordinator-role-failure-modes-and-refactor.md:820@7eb7a4a3c911` (manifest `handoffs/active/coordinator-role-failure-modes-and-refactor.md:820@3ac825873dfb`, id `5b85882ed97d`)
- Gated worker box(es): `AUD-15` (handoffs/active/coordinator-role-failure-modes-and-refactor.md:820), `handoffs/active/coordinator-role-failure-modes-and-refactor.md:571`

- **Option A (recommended)**: Add them to `check_trust_boundary_edit.sh`'s list (AUD-15). *Tradeoff:* Uses the existing guard; every policy edit needs a signature.
- **Option B**: Build a separate authority guard (R-8). *Tradeoff:* Tailored; new agent infrastructure to build and maintain.
- **Option C**: Leave the gap. *Tradeoff:* No friction; a wrong premise there becomes every session's truth.

**Recommendation: A.** The audit recommends yes and the existing list is the cheapest enforcement.

## 6. OP-9 + FW-3: may supervision lines be added to the HOST crontab (hub_supervisor.sh, fleet_watch.sh)?

- Context: `handoffs/active/handoff-index-and-backlog-graph.md:212@7eb7a4a3c911` (manifest `handoffs/active/handoff-index-and-backlog-graph.md:212@3ac825873dfb`, id `65b30170d77e`)
- Gated worker box(es): `handoffs/active/handoff-index-and-backlog-graph.md:212`

- **Option A (recommended)**: (a) cron `once` form (recommended). *Tradeoff:* Auto-restart of the hub; host config change, with the in-container path issue fixed per the joint package.
- **Option B**: (c) systemd unit. *Tradeoff:* More robust; the script docstring rules out host-config territory.
- **Option C**: No host supervision. *Tradeoff:* Nothing restarts a dead hub.

**Recommendation: A.** The joint package recommends (a) and supersedes the defective earlier cron line.

## 7. D9 acknowledgement: integrate RTG52 target-selection and assignment-stdin source controls (private tip 33df2630, six files)?

- Context: `handoffs/active/loop-owned-fleet-implementation.md:653@7eb7a4a3c911` (manifest `handoffs/active/loop-owned-fleet-implementation.md:653@3ac825873dfb`, id `7be5b6719b9c`)
- Gated worker box(es): `RTG52-D9-SOURCE` (handoffs/active/loop-owned-fleet-implementation.md:653)

- **Option A (recommended)**: Acknowledge. *Tradeoff:* Merges reviewed source; no host activation or dispatch.
- **Option B**: Decline. *Tradeoff:* Controls stay private.

**Recommendation: A.** Reviewed, bounded footprint, no runtime activation.

## 8. Session-bus contract: make `append` refuse at authoring time (align schema with the relay contract)?

- Context: `handoffs/active/session-bus-thin-dispatcher.md:1562@7eb7a4a3c911` (manifest `handoffs/active/session-bus-thin-dispatcher.md:1562@3ac825873dfb`, id `d736379ec553`)
- Gated worker box(es): `handoffs/active/session-bus-thin-dispatcher.md:1562`

- **Option A (recommended)**: Tighten the contract. *Tradeoff:* Failures surface at the author; mainA's row must be re-filed.
- **Option B**: Keep the current contract (C34 schema validation only). *Tradeoff:* No re-filing; a schema-valid gate can still be unpresentable.

**Recommendation: A.** C34 already covers part; refusing at authoring is the right failure point per the box.

## 9. Session-bus daemon: add automatic restart?

- Context: `handoffs/active/session-bus-thin-dispatcher.md:1899@7eb7a4a3c911` (manifest `handoffs/active/session-bus-thin-dispatcher.md:1899@3ac825873dfb`, id `f83eba9fb19b`)
- Gated worker box(es): `handoffs/active/session-bus-thin-dispatcher.md:1899`

- **Option A (recommended)**: Cover it with the OP-9/FW-3 host-cron decision. *Tradeoff:* One decision for all supervision.
- **Option B**: Leave restarts manual. *Tradeoff:* Nothing watches the watcher.

**Recommendation: A.** Same supervision question as OP-9/FW-3; bus_supervisor stays down per the 2026-09-23 ruling.

## 10. Install the pre-push serialization guard?

- Context: `handoffs/active/session-bus-thin-dispatcher.md:2656@7eb7a4a3c911` (manifest `handoffs/active/session-bus-thin-dispatcher.md:2656@3ac825873dfb`, id `c2cbb12e4eb4`)
- Gated worker box(es): `handoffs/active/session-bus-thin-dispatcher.md:2656`

- **Option A (recommended)**: Install as-is (advisory). *Tradeoff:* Catches accidental unserialised pushes; bypassable.
- **Option B**: Pursue a server-side pre-receive. *Tradeoff:* Structural; needs origin-side config.
- **Option C**: Neither. *Tradeoff:* No guard.

**Recommendation: A.** Built and tested; advisory still catches the common case.

## 11. Present the CLAUDE.md/AGENTS.md and agents/shared/* wrap-up division-of-labour amendment for sign-off.

- Context: `handoffs/active/wrap-up-division-of-labor-policy.md:431@7eb7a4a3c911` (manifest `handoffs/active/wrap-up-division-of-labor-policy.md:431@3ac825873dfb`, id `1f33a4788705`)
- Gated worker box(es): `handoffs/active/wrap-up-division-of-labor-policy.md:431`

- **Option A (recommended)**: Sign with a narrow subagent exception (one writer, one request, one lease). *Tradeoff:* Keeps the exception bounded.
- **Option B**: Sign with no subagent exception. *Tradeoff:* Simpler.
- **Option C**: Decline. *Tradeoff:* No amendment.

**Recommendation: A.** The box sets the narrow form as the condition for retaining the exception.

## Excluded (not delivered)

- `handoffs/active/coordinator-role-failure-modes-and-refactor.md:571`: **merged** into choice for `AUD-15`. R-8 and AUD-15 both close F-19 (guard on auto-loaded instruction surfaces).

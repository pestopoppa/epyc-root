# Evidence Plane — Event-Sourced Runtime + Narrative Regeneration

**Status**: W7 landed on live branch 2026-06-13; W1-W6/W8 still open (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: HIGH — sequenced after [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md); the adoption gate is already MET (T2 drift observed, see Why)
**Spec**: [fable5-findings-01-impl-plan.md](fable5-findings-01-impl-plan.md) Phase 3 + Phase 4, and [fable5-findings-01-measurement-and-integrity.md](fable5-findings-01-measurement-and-integrity.md) §2.1/§2.4/§4 — read before claiming any waypoint
**Related**: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) · [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) · [../../MEASUREMENT.md](../../MEASUREMENT.md) §5 (the append-never-edit retroactivity rule this implements at runtime)

## Why

The journal already rebuilds the full archive shape (`journal_reconstruction.py`) but only for
the dashboard; the runtime dual-writes via a second path that has drifted: the 2026-06-12
read-only check found live T2 archive {363} vs journal reconstruction {363, 367} — trial 367
is frontier-worthy under the shared policy yet absent from the runtime archive (findings-01
§4). The event-sourcing case is no longer hypothetical. Phase 3 makes the journal the single
append-only ledger (archive/baseline = recomputed folds, scrubs = supersession events,
backups/rewinds obsolete); Phase 4 makes every narrative store a regenerated,
provenance-checked view so refuted stories cannot re-enter the planner.

## Waypoints

- [ ] **W1 — single commit point** (impl 3.1, ~3–4 days): trial finalization writes ONE journal row; `ParetoArchive` becomes an in-memory view via `reconstruct_archive_from_journal_rows` at startup; delete `ParetoArchive.save`'s read-merge-write; `state.json` drops the `pareto_archive` key (legacy-read fallback one release). Acceptance: the dual-write drift check passes by construction (it IS the load path).
- [ ] **W2 — supersession events** (impl 3.3, ~1–2 days): new row type `{type: supersession, target_trial_ids, fields, reason, policy_version, actor}`; `scrub_journal.py` and every future rewind/purge become appends; rewrite-in-place removed (the function, not just the habit).
- [ ] **W3 — rotation snapshots** (impl 3.2, ~1 day): journal segments per 1000 trials chained with a snapshot row (full reconstructed view + policy version); rebuild = snapshot + tail fold. Acceptance: bounded startup cost.
- [ ] **W4 — baseline as fold + acceptance suite** (impl 3.4–3.5, ~2 days): `Baseline` computed at load; `update_baseline` becomes a `baseline_promotion` ledger event; YAML = cold-start seed only. Acceptance: kill -9 mid-trial → WAL recovery reproduces identical views; full-journal replay (existing `bug_corrupted_by` tags as implicit supersessions) reproduces today's T1 frontier.
- [ ] **W5 — STM as generated view** (impl 4.1, ~1–2 days, needs W1): `short_term_memory.md` rebuilt each trial from the ledger (trustworthy last-N, hypotheses with falsifiers + provenance trial-ids); read-modify-write path deleted; per-section render budgets (kills mid-word truncation structurally).
- [ ] **W6 — strategy provenance** (impl 4.2, ~2 days, needs W1): `strategies.db` rows gain `evidence_trial_ids`; `retrieve()` filters rows citing superseded/excluded trials (extend the AP-28 staleness pattern, ledger-keyed); distill must cite trial-ids per insight or the insight stores quarantined.
- [x] **W7 — session hygiene** (impl 4.3, ~half day, anytime): default `supports_resume=False` for the draft provider (delete `session_id` persistence); replace with a generated prior-decisions digest from `planner_archive.jsonl`; archive failed draft calls (move `_append_planner_archive` before the early-return). **Landed 2026-06-13**: `epyc-orchestrator` live branch `fix/substring-scorer-digit-separators` commit `9e5d861` (`Harden planner session hygiene`), rebased from original branch-ready `69a41f7`. AutoPilot remains paused; server/restart attestation is still pending.
- [ ] **W8 — program.md split** (impl 4.4, ~2 days, anytime — this month per findings-01 §4): human-authored `constitution.md` (~150 lines) + `scripts/autopilot/gen_system_card.py` regenerating `system_card.md` at restart from live registry/state/instrument spec; prompt assembly swaps in the pair. Acceptance: prompt share ~46%→~20% while refuted facts (architect_coding:8084 class) become structurally impossible.

## Gates & pitfalls

- Sequencing: Phase 3 lands after the ledger handoff's Phase 1 (per-question `question_results` must be in the rows being folded); W5/W6 hard-require W1; W7/W8 are independent — do NOT let W8 wait on Phase 3, the planner reads program.md ~50×/day and its constitution currently misdescribes the instrument.
- W8 is an integrity task, not a token-budget trim — a planner whose constitution misdescribes the instrument produces confabulated hypotheses no memory hygiene can fix (findings-01 §2.4).
- Migration risk is bounded: reconstruction is battle-tested on the dashboard path and already caught real drift; run acceptance 3.5c (full historical replay) BEFORE deleting the dual-write.
- Append-only means append-only: no new sanitizers/scrubbers/gates bolted onto the old pipeline (findings-01 §4 hold-list); fixes become policy-version bumps + view recompute.
- `autopilot_state.json` still carries genuinely operational state (counters, halts, circuit breakers — `feedback_checkpoint_pareto_state`); only derived views move out.

## Progress

- 2026-06-12: W7 branch-ready at `feat/planner-session-hygiene` commit `69a41f7`. GitNexus impacts were LOW for `plan_with_providers`, `ClaudePlannerProvider`, exact `controller_io.invoke_controller`, and `_run_loop_inner` (index stale vs current branch, treated conservatively). Validation: `python3 -m py_compile` on touched AutoPilot/test files passed; focused suite `tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_controller_io.py tests/unit/test_autopilot_actions.py` -> 84 passed, 1 pytest config warning; focused `ruff check` passed on non-debt touched files, and `ruff check --ignore F401` passed on `autopilot.py`/`test_autopilot_actions.py` due pre-existing F401 debt; `git diff --check` passed.
- 2026-06-13: Rebased W7 onto live branch `924ca50`, validated, and fast-forwarded `fix/substring-scorer-digit-separators` to `9e5d861`. GitNexus was refreshed to `924ca50` before impact checks; impacts were LOW for `plan_with_providers`, `ClaudePlannerProvider`, `controller_io.invoke_controller`, and `_run_loop_inner`. Validation on the rebased branch: `python3 -m py_compile` passed; `uv run --with pytest pytest -q tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_controller_io.py tests/unit/test_autopilot_actions.py tests/unit/test_skill_efficacy.py` -> 106 passed, 1 pytest config warning; focused ruff passed (excluding known pre-existing F401 debt in `test_skill_efficacy.py`; `autopilot.py`/`test_autopilot_actions.py` checked with `--ignore F401`); `git diff --check 924ca50..HEAD` passed.

## Reporting

Tick waypoints + one-line progress entry; frontier/baseline claims per MEASUREMENT.md grammar with `policy_version` cited; on completion delete this handoff's master-index row and move to `completed/`.

# 2026-09-16 — sub-gate-frontier (paired safety-gate frontier change + MHS-3 operability)

Zero-inference, zero-process-management lane. Orchestrator worktree
`/mnt/raid0/llm/worktrees/sub-gate-frontier`, branch `sub/gate-frontier-20260916`. It is based on
`sub/autopilot-safety-20260916` (MHS-3/4/5 + W3e), with `origin/main` merged in (clean merge,
no conflicts in `safety_gate.py`). Unmerged and not pushed. Both changes take effect at the next
autopilot restart after merge.

## A. Paired gate-frontier change (W3e follow-up) — done

- The promotion guard now reads the LIVE frontier. The autopilot installs a provider
  (`_install_promotion_guard_scope`) that rebuilds through `_journal_archive_payload_for_authority`,
  the W3 authority path. It uses the live `pareto_objective_policy`, the
  `pareto_epoch_ts` / `pareto_exclude_before_ts` fence, and the verified snapshot when its scope
  matches.
- The rate axis is routed by unit (`tier_specs.rate_axis_unit`). Questions/hour now goes to
  `task_rate_qph` and then to the new optional `Baseline.frontdoor_task_rate_qph`. It never goes to
  `speed` / `frontdoor_speed`. An unknown policy is refused. Records without the new key still
  load, and legacy payloads stay byte-identical.
- The throughput floor stays t/s against t/s (decision D1): `frontdoor_speed` only ever holds a
  genuine EvalTower t/s measurement.
- D2: an empty live-epoch frontier now refuses promotion over an existing baseline; a bootstrap
  seed is still allowed. Without this, the next restart (0 journal rows after the 2026-08-10
  fence) would have opened single-trial promotions over the reseeded baselines.
- D3: the load-path quality ceiling is left unscoped. Fencing it would delete reseeded baselines.
- Decision note: orchestrator `docs/autopilot/gate-frontier-live-scope-2026-09-16.md`.
- Reviewer note 4 is done: `journal_reconstruction` deinflation now writes the rate axis by name.
- Replay over the stored journal (1,372 rows, `scripts/analysis/gate_frontier_replay.py`, pinned
  in `tests/fixtures/gate_frontier_replay.json`):
  - Promotions are IDENTICAL on the old and new paths: 2, both legacy-era seeds.
  - Every difference is a change of refusal reason in the rate era. Production ordering has 4:
    1474 becomes live-frontier-empty, and 1477/1500/1501 become above-live-archive-max.
    Archive-first ordering has 6, all becoming too-few-reproductions.
  - The two paths agree on every legacy-era row (asserted).
- **Finding (pre-existing, not changed):** in production ordering the candidate is journaled
  AFTER `update_baseline`. A clean trial is therefore never a frontier representative, and 479 of
  499 old-path guard decisions are "not a same-tier frontier representative". Since the
  2026-06-18 journal-authority cut-over, promotions can only happen on an empty frontier. Whether
  a clean single trial should ever promote is a promotion-policy question for the operator. It is
  recorded in the decision note, and this change does not alter it.
- Tests: `tests/unit/test_gate_frontier_live_scope.py` (26 plus 1 env-gated full replay,
  `GATE_FRONTIER_FULL_REPLAY=1`, about 4.5 min). It includes a mutation test showing that the old
  routing puts q/h (59.49) into `frontdoor_speed` and fails an unchanged 14.78 t/s trial on the
  floor.

## B. MHS-3 fail-closed operability — done

- `scripts/autopilot/eval_leakage_monitor.py` (new):
  - Startup preflight: one ERROR naming the path(s) and the fix, plus a ledger event
    `{"type":"eval_leakage_guard","event":"preflight_failed"}`. The autopilot still starts.
  - Circuit alarm: after N consecutive vocabulary-unavailable verdicts (default 3,
    `AUTOPILOT_LEAKAGE_ALARM_THRESHOLD`), it raises session-bus alarm key
    `autopilot-eval-leakage-vocab-unavailable` (critical) through
    `epyc-root/scripts/coordination/alarm_channel.py`. This uses the same subprocess idiom as
    `session_bus_coordinator._alarm`. Re-assertions are rate-limited
    (`AUTOPILOT_LEAKAGE_ALARM_REASSERT_S`, 900 s).
  - The alarm clears, with an `alarm_cleared` event, on the first available vocabulary.
  - Status goes to `state["eval_leakage_guard"]`, which `/dashboard/api/process_status` exposes;
    the dashboard control line shows a red "MUTATIONS REJECTED" suffix.
- `prompt_forge.py`:
  - Verdict observer hook.
  - `describe_eval_id_sources()`.
  - Recovery without a restart was confirmed: a missing file is never cached.
  - Reviewer note 1: a negative cache for failed builds, keyed on (path, mtime_ns, size) with a
    60 s TTL (`AUTOPILOT_EVAL_ID_VOCAB_NEG_TTL_S`).
  - Reviewer note 3: `_LEAKAGE_GENERIC_RE` was narrowed. Snake_case identifiers now count only as
    comparisons (`==` / `is`). `task_index = 0`, `sample_id = 1` and `task_id: 7` no longer
    match, and all existing positives still match.
- Runbook: orchestrator `docs/guides/meta-harness-operator-guide.md` § 7, "Mutations all
  rejected: eval_leakage_vocabulary_unavailable". It covers symptoms, cause, the check command,
  the fix, restart need, confirming recovery, and reading rejection ledgers for false positives.
  It also records reviewer note 2 (3.6 s cold, +253 MB RSS).
  - **Correction to the brief:** `question_pool.jsonl` is gitignored in `epyc-inference-research`,
    so "restore via git" is impossible. The runbook says to restore a byte-identical copy
    (sha256 `64218c27…`, pinned in `artifacts/audit/deterministic-rescore-ledger-20260812.json`).
    It warns that `--build` or copying the pre-amendment `question_pool.activated.jsonl` is an
    EVAL-INSTRUMENT change.
  - The README has a one-line pointer to § 7.
- Tests: `tests/unit/test_eval_leakage_operability.py` (23). It covers: the missing pool (ERROR,
  journal event, status); the alarm at N with the rate limit; restoring the pool (recovery, alarm
  cleared, cleared event); the real `alarm_channel.py`, sandboxed on the file backend with push
  disabled and temp state; the negative cache and its TTL; the regex narrowing; and the wiring.
- Reviewer note 5 was respected: `test_mutation_ledger_tripwire.py` was left untouched.

## Blast radius (grep; the repo is not gitnexus-indexed)

- `promotion_fields_from_objectives`: `update_baseline` plus the W3e tests. The new third argument
  is optional. LOW.
- `SafetyGate._archive_best_quality`, `_archive_frontier_trial_ids` and `_archive_frontier_entry`:
  only `update_baseline` calls them; about 12 test files monkeypatch them, and all pass. MEDIUM,
  because this is promotion semantics (D2).
- `Baseline.update_tier`: `update_baseline` plus 2 test files. The new argument is keyword-only.
  LOW.
- The `baseline_state` payload gains an optional key. Readers: baseline ledger fold and operator
  seed tools. The key is emitted only when set, and the ledger event snapshots the same dict.
  LOW.
- `eval_leakage_reason`: 2 PromptForge call sites. The observer is exception-isolated. LOW.
- `_LEAKAGE_GENERIC_RE`: narrower, so it can only remove matches. LOW.

## Intended handoff edits (for the wrap-up agent to port; NOT applied here)

`handoffs/active/objective-task-rate-goodput.md`, inside the W3e box, directly after the paragraph
that ends "`frontdoor_speed` ... Both must change together.", append:

```
      **2026-09-16 (`sub-gate-frontier`) — the coupled finding is FIXED (box stays open for the
      axis drop).** Orchestrator branch `sub/gate-frontier-20260916` (on top of
      `sub/autopilot-safety-20260916`), unmerged. The promotion guard now rebuilds from the LIVE
      policy + epoch fence through `_journal_archive_payload_for_authority`; the rate axis is routed
      by unit (`tier_specs.rate_axis_unit`), so q/h lands in the new
      `Baseline.frontdoor_task_rate_qph` and never in `frontdoor_speed`; the 0.8x floor stays t/s vs
      t/s (D1). An empty live-epoch frontier refuses promotion over an existing baseline (D2); the
      load-path quality ceiling stays unscoped (D3). Journal replay (1,372 rows): promotions
      identical old vs new (2 legacy-era seeds); 4 production-ordering and 6 archive-first
      differences, all refusal-reason changes inside the rate era. Pre-existing finding recorded for
      the operator: the candidate is journaled after `update_baseline`, so a clean trial is never a
      frontier representative (479/499 old-path refusals). Decision note:
      `epyc-orchestrator/docs/autopilot/gate-frontier-live-scope-2026-09-16.md`. Tests:
      `tests/unit/test_gate_frontier_live_scope.py` (26 + env-gated full replay).
```

`handoffs/active/promptforge-mutation-safety-contract.md`, at the end of the MHS-3 box (after
"`tests/unit/test_prompt_forge_leakage_and_risk.py` (73 tests)."), append:

```
      **Operability ✅ 2026-09-16 (`sub-gate-frontier`, branch `sub/gate-frontier-20260916`,
      unmerged):** the fail-closed state is now loud. Startup preflight (one ERROR + ledger event
      `eval_leakage_guard/preflight_failed`, start not refused); circuit alarm after 3 consecutive
      `eval_leakage_vocabulary_unavailable` rejections (`AUTOPILOT_LEAKAGE_ALARM_THRESHOLD`) on
      session-bus key `autopilot-eval-leakage-vocab-unavailable`, re-asserted at most every 900 s,
      cleared on recovery; status in `autopilot_state.eval_leakage_guard` and on the dashboard
      control line. Recovery needs no restart (a missing pool is never cached; a malformed one is
      negative-cached ≤60 s by file identity). Generic pattern narrowed: snake_case identifiers
      count only as comparisons. Runbook: `docs/guides/meta-harness-operator-guide.md` § 7.
      `tests/unit/test_eval_leakage_operability.py` (23 tests).
```

## Belief kernel — adapter row needed

The preflight and alarm events are a verified-finding source. Proposed row for
`scripts/vidya/adapters/README.md`, filed next to the existing "PromptForge mutation-safety gate
verdicts" candidate row:

| Source | Class | Status | Adapter |
|---|---|---|---|
| AutoPilot eval-leakage guard operability events (journal ledger `type: eval_leakage_guard`, events `preflight_failed` / `alarm_raised` / `alarm_cleared`; orchestrator `sub/gate-frontier-20260916`) | verified finding: an INSTRUMENT-availability interval (the guard could not screen) | **candidate**. The write side exists as append-only ledger rows carrying `error`, `problem_paths`, `consecutive`, `threshold` and `ts`. The locator is the raised→cleared interval. Any MHS-3 leakage-rate measurement must use these intervals to hold `vocabulary_unavailable` windows OUT of the denominator (VB-MHS-GATES). | — |

Task to add to `handoffs/active/vidya-belief-substrate-program.md`: **VB-MHS-OPS**. Project the
`eval_leakage_guard` ledger events into claim tuples (an instrument-unavailable interval), and
have VB-MHS-GATES consume them as the denominator exclusion.

## Follow-up — operator decisions (c)+(b) and the Fable review (MERGE-AFTER-FIX)

Same branch, new commits. No restart, no push.

- **(c) Clean trials become frontier representatives.**
  - The loop fixes the row it will journal before the promotion decision
    (`_provisional_trial_row`: same timestamp and objective fields). It passes that row to
    every `update_baseline` call (`pending_journal_rows`), so the guard's live archive includes
    the candidate.
  - Clean rows are stamped `eval_details.frontier_admission = "representative"` and cluster by
    config fingerprint. One predicate (`row_is_representative_member`) serves replay, the
    snapshot tail fold, recovery re-import and reproduction counting. The live archive uses
    `upsert_representative`.
  - Outside multitier mode, within-noise reproductions now reach `update_baseline` as well.
  - Nothing is persisted between the decision and `journal.record` (pinned by a test). After
    the record, a mismatch between the provisional row and the recorded row logs an ERROR.
  - No back-fill. Switch: `AUTOPILOT_CLEAN_TRIAL_REPRESENTATIVES` (default on).
- **(b) Interim empty-frontier rule.**
  - Applies while the tier's live frontier holds no config other than the candidate's and the
    tier has a baseline.
  - Needs N comparable live-regime reproductions: `AUTOPILOT_EMPTY_FRONTIER_MIN_REPRO`,
    default 3; values below 2 are refused and fall back to 3.
  - NON_COMPARABLE rows are excluded (`src/autopilot_core/live_reproductions.py`). The
    promoted fields are the median over those reproductions, and that median must still clear
    the quantum.
  - `promotion_rule` (`frontier` / `empty_frontier_repro` / `seed`) is logged, returned, and
    written to the trial row and the `baseline_promotion` event.
- **Review fixes.**
  - (1) The replay `compare()` now restores the logger level.
  - (2) `fix_text` no longer mentions git; it pins the pool's sha256 and size and says to never
    rebuild. A test covers it.
  - (3) Fail-closed: a provider exception or an unreadable archive refuses promotion over an
    existing baseline (`refused_guard_unavailable`). The reviewer's reproduction is a test.
  - (4) The live archive is built once per `update_baseline` call, down from up to 4 (tested).
- **Replay goldens regenerated**, with paths `old` / `live` / `live_c` and a forward simulation.
  - `old` vs `live`: identical promotions; 4 refusal-reason changes.
  - `live_c` (what-if): 27 promotions against 2 on the other paths (3 seeds, 22 under rule
    (b), 2 under the frontier rule). It still refuses 66 on the quantum and 23 on the
    reproduction count.
  - Forward simulation from the live state: the first decision falls under rule (b) and is
    refused (1 of 3), the T1 frontier fills to 5 points, and every later decision uses the
    frontier rule. No config in that window reproduced 3 times, so nothing promotes.
- **Live restart consequence** (recorded in the decision note): T1, T2 and T3 have baselines and
  0 rows fall after the fence, so each tier starts under rule (b). No promotion happens until a
  config has 3 comparable reproductions in the new epoch.
- **AP-55.** Mode A (shadow) remains the default: `gate_mode()` maps anything unknown to
  `shadow` on `sub/ap55bc-20260916`, and the launcher does not set
  `AUTOPILOT_AP55_PROMOTION_GATE`. That gate is not on this branch.
- **Blast radius: MEDIUM-HIGH.** This touches loop ordering at the decision point (in memory
  only), a new journal field (additive), reconstruction clustering for newly stamped rows, the
  snapshot tail fold (stamped rows force full replay), recovery re-import, the rule dispatch in
  `update_baseline` (its signature gains a keyword-only argument), and fixtures.

### New handoff task (for the wrap-up agent to add; not applied here)

In `handoffs/active/autopilot-continuous-optimization.md` (or the AP-55 owner's handoff), add:

```
- [ ] **AP-55-ARM** — after one AutoPilot run in shadow (mode A), report how often enforce
      would have held a promotion (from the recorded shadow verdicts), then arm enforce plus
      seed re-runs (`AUTOPILOT_AP55_PROMOTION_GATE=enforce`, `AUTOPILOT_AP55_SEED_RERUN=1`).
      The operator pre-approved option B for after that review (2026-09-16).
```

Also append to the W3e note in `objective-task-rate-goodput.md`:

```
      **(c)+(b) ✅ 2026-09-16 (operator decision; branch `sub/gate-frontier-20260916`):** clean
      trials are journaled as frontier representatives and handed to the promotion guard before
      the decision; an empty live frontier needs >= 3 comparable reproductions
      (`AUTOPILOT_EMPTY_FRONTIER_MIN_REPRO`); `promotion_rule` recorded per trial. Guard fails
      closed on an unreadable archive. Next restart: every tier starts under rule (b).
```

Belief kernel: the `autopilot trial journal` adapter should project `eval_details.promotion_rule`
and `frontier_admission` into the support frame. Add this to the VB-MHS-OPS task note; the
change is additive and involves no grade change.

### Commits and integration notes (follow-up)

- `5d3a7a37`: fix_text (review finding 2).
- `239ac5b8`: (c)+(b), fail-closed guard, per-call cache, replay logger restore, goldens, and
  the decision note.
- Merging `origin/main` (88a2902d) into this branch is clean (`git merge-tree`).
- Merging `sub/ap55bc-20260916` into this branch gives ONE conflict, in `autopilot.py` next to
  `eval_details_dict["infra_comparability"]`. Resolve it by keeping both blocks: the
  `frontier_admission` and `promotion_rule` stamps, and `ap55_promotion_gate`.
- **Integration must-do:** ap55bc adds an `ap55_gate.get("hold")` guard to the clean and
  final_t1 promotion call sites. The within-noise call site added here (non-multitier mode) needs
  the same `and not ap55_gate.get("hold")` condition, or AP-55-ARM (enforce) will not bind on
  that path. In shadow mode it makes no difference.
- Tests, full unit suite (`-n 16`, with `GATE_FRONTIER_FULL_REPLAY=1`): 13312 passed and 4
  failed. 3 of the failures were already present before this work (config_consolidation,
  dashboard_helpers embedder bucket, mutation_ledger_tripwire, the last being fixed on main).
  The 4th was the stale full-replay golden, which has since been regenerated, and the full
  replay now passes.
- Tests, single process (the review subset plus ev14c): 1621 passed and 2 failed. The failures
  are `test_model_server_extended` (it also fails on origin/main because of the environment)
  and the tripwire test.
- Tests, combined process (live_scope + c_and_b + operability + ev14c, full replay on): 90
  passed.

## Re-review of 239ac5b8 (MERGE-AFTER-FIX), fixed in `53dea5aa`

- **B1 (blocking), fixed: served-config identity.**
  - Reproductions were keyed by the ACTION hash. For `seed_batch` and `deep_eval` that hash
    is not the served config: `{"type":"seed_batch","n_questions":10}` covered 394 rows, and
    all 22 what-if promotions under rule (b) were such runs.
  - New `action_identity.row_config_identity` identifies a served config only from an explicit
    delta (`structural_experiment` flags, `numeric_trial` resolved params), plus the AP-55
    infra digest when the row records one.
  - Rule (b) counts reproductions by that identity, and only identity-bearing clean rows are
    stamped as representatives. A candidate without an identity cannot promote under either
    rule, though a tier with no baseline can still seed.
  - Prompt, code and GEPA mutations stay non-promotable until the loop records a content
    identity for them. Open item for the operator: the mutated-file sha, or the post-commit
    orchestrator HEAD.
- **What-if replay after the fix.**
  - 4 promotions: 3 seeds, plus trial 755 (`structural_experiment`) under the frontier rule.
  - **Rule (b) promotes nothing.**
  - 441 decisions are refused for having no served-config identity: seed_batch 331,
    numeric_trial with empty params 72, deep_eval 18, and 20 others.
  - Forward simulation: nothing promotes. 1472 is refused under (b) (1 of 3 reproductions);
    the numeric_trial candidates are refused for too few reproductions or for not being
    representatives; the 2 seed_batch runs are refused for having no identity.
- **B2, fixed.** The loop deep-copies the baseline before the decision. After `journal.record`,
  `_reconcile_promotion_with_journal` restores it on any mismatch and turns the update into a
  refusal, so no promotion event and no promoted `baseline_state` are written. Tested.
- **B3, fixed (the simpler option).** The row carries
  `promotion_status: pending_commit|refused`. The `baseline_promotion` event is the commit
  record, so a pending row with no event means "not promoted", and recovery needs no action.
  Documented in the decision note.
- **AP-55.** A TODO at the within-noise promotion call asks the merge train to add the
  `ap55_gate.get("hold")` guard.
- **Tests.**
  - Combined process (live_scope + c_and_b + operability + ev14c, full replay on): 106 passed.
  - Full suite (`-n 16`): 13,320 passed and 11 failed. All 11 fail identically on the unchanged
    base commit 239ac5b8, because of the environment: model_server_extended ×5,
    orchestrator_stack_reload ×3, config_consolidation, dashboard embedder bucket, and
    mutation_ledger_tripwire.
  - Single process, related subset: 1,532 passed and 1 failed (model_server_extended, the same
    environment failure).

## Operator decision: the mutated-file sha is the content identity, plus the 53dea5aa verification notes (`f083a0cd`)

- **Scope and recording.**
  - `prompt_mutation`, `code_mutation` and `gepa_optimize` are identified by
    `eval_details.served_content = {"files": {path: sha256}}`.
  - The handler hashes the served file after the write and before the eval, and leaves the
    record in loop state. The loop clears it before each dispatch and pops it into the row.
  - The sha is never on the action, so fingerprints and signatures are unchanged for old and
    new rows (tested).
- **Identity.** The sorted (path, sha) set plus `infra_regime_digest`. Rows without a sha stay
  non-promotable; nothing is back-filled.
- **What-if replay.** Byte-identical to the previous goldens: no stored row carries a sha.
- **Regime digest (verification note 1).** It is the AP-55 digest without the orchestrator
  HEAD/dirty component, and it keeps the evaluator, kernel, recipe, models and host. So an
  unrelated orchestrator commit no longer splits a cluster, while a kernel, model, recipe, host
  or evaluator change does.
  - **Deviation from the reviewer's list:** the evaluator is kept, because it is the scoring
    instrument.
- **Other verification notes.** Note 2: the sha is taken from the served file at eval time.
  Note 3: it is stored as a dict. Note 4: fingerprints are unchanged. Note 5: the TODO and its
  test are removed.
- **Standing limitation (pre-existing).** Multitier staging accepts only numeric and structural
  candidates, so under the live multitier launcher a mutation can promote only outside
  multitier mode. `structural_prune` stays non-promotable.
- **Tests.**
  - Combined process (live_scope, c_and_b, operability, ev14c, ap55 infra fingerprint, full
    replay): 143 passed.
  - Full suite `-n 16`: 13,348 passed and 1 failed (mutation_ledger_tripwire, known and fixed
    on main).
  - Single-process related subset: 1,755 passed and 1 failed (the same tripwire test).

## Operator decision: mutation candidates in multitier (`c12f17f5`)

- **Staging and replay.** Prompt, code and GEPA mutation candidates with a `served_content` sha
  and an exact restore preimage can now be staged under multitier. The seq fresh-eval and
  replay paths still block mutations, and numeric/structural behaviour is unchanged.
- **Content checks.** Every forced stage re-hashes the served files before the eval (a change or
  missing file means refuse and roll back) and again after it (a match becomes the row's
  identity; a change rejects the candidate and withholds identity).
- **Promotion and hold guards.** Promotion goes through the existing final_t1 call, so there are
  still exactly 3 `update_baseline` call sites and the AP-55 merge-train guards cover it.
- **Rollback.** It writes the preimage back through the forge's revert and attests the restored
  sha; a rejected `new_file` must end up absent. It fails closed otherwise.
- **Out of scope.** `structural_prune`.
- **Tests.** `tests/unit/test_multitier_mutation_candidates.py`, 21 tests.
  - Full suite `-n 16`: 13,371 passed and 1 failed (the known tripwire test).
  - Single-process related subset: 1,229 passed and 1 failed (the same tripwire test).
  - While writing the tests, I fixed a pollution bug in my own new test: it had left a live
    promotion-guard provider installed.
- The Fable review of f083a0cd was still pending when this was written.

## Fable review of c12f17f5 (MERGE-AFTER-FIX), fixed in `25c8e913`

1. **Scoped rollback.** A mutation-candidate rollback skips the checkpoint's prompt copytree
   (`restore_prompts=False`) and attests the file's final on-disk state. Tests: an unrelated
   prompt edit survives (using the real StructuralLab restore), and a later overwrite is caught.
2. **External changes survive.** The preimage is written only if the file's current sha equals
   the served sha. Otherwise nothing is written, the candidate is retired as
   `rejected_external_change`, logged at ERROR, and raises the alarm
   `autopilot-multitier-rollback-external-change`.
3. **No commit sweep.** All PromptForge commits are path-limited
   (`git add -A -- p` + `git commit --only -- p`). Tests use real git repos: a staged
   unrelated file stays out, and a pathless prompt commit is refused.
4. **Preimage does not linger.** It is stripped from the last_rejected and last_accepted
   snapshots and from rollback contexts.
5. **Attempt cap.** It is at least max(configured, 3, AUTOPILOT_EMPTY_FRONTIER_MIN_REPRO)
   (tested).
6. **Bounded rollback retries.** After 3 failures the rollback is no longer forced, staging is
   refused, and the critical alarm `autopilot-multitier-rollback-stalled` is raised
   (implemented and tested).

**Tests.**
- Combined single process (mutation_candidates, c_and_b, live_scope with full replay,
  multitier wiring, all `test_safety_gate*`): 305 passed.
- Full suite `-n 16`: 13,383 passed and 1 failed (the known tripwire test).

**Pre-existing, not changed.** Numeric and structural rollbacks still copytree the checkpoint
prompts.

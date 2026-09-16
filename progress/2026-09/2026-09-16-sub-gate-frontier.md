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

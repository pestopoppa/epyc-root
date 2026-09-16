# 2026-09-16 — sub-autopilot-safety (PromptForge mutation safety + W3e)

Zero-inference, zero-process-management lane. Orchestrator worktree
`/mnt/raid0/llm/worktrees/sub-autopilot-safety`, branch `sub/autopilot-safety-20260916` (unmerged).

## RTG-55 MHS-1..MHS-4 — done

- MHS-1/MHS-2 checked against the code: both landed in `7d4b40a8`, which is already on `main`.
  The importlib-in-live-repo step is gone, the strict `new_file` denylist is in place, and the closed
  `MutationEffect` enum exists. Ticked with evidence (100 tests pass).
- MHS-3 + MHS-4 committed in `8219d8e8`:
  - Eval-instance leakage guard. The vocabulary comes from the research question pool (required) plus
    the core and sentinel files: 153,450 ids and 295 derived id families. It fails closed.
  - False positives: 0 over the 33 live mutation targets, and 1 of 444 docs/src files (both hits
    there were real instance references).
  - CONSTRAIN-vs-REPLACE risk prior with ranking, plus a gate (`AUTOPILOT_MUTATION_RISK_GATE`,
    default 1.0, which can only be tightened).
- Tests: `tests/unit/test_prompt_forge_leakage_and_risk.py` (73 new). Related suites: 351 passed.
  `test_prompt_forge_safety.py` is now hermetic (fixture pool via `AUTOPILOT_EVAL_ID_VOCAB_SOURCES`).
- Belief kernel: filed candidate README row "PromptForge mutation-safety gate verdicts" and task
  VB-MHS-GATES. Persistence depends on AP-53's ledger.
- MHS-5 not done: the Harness-R1 `examples/heldout_generalization/` corpus is not on this host.

## W3e — axis-name objective reads (blocker removed; axis drop still open)

- Orchestrator `635a3467`: `TierSpec.axes` plus `tier_specs.objective_value()`, which is
  shape-checked. `pareto_archive.py` and `safety_gate.py` now read every objective by axis name.
  `promotion_fields_from_objectives` refuses any shape mismatch.
- Identical behaviour on real archives: `tests/unit/test_w3e_axis_name_reads.py` replays the
  legacy_4d_v1 and task_rate_4d_v1 archives (reconstructed from the stored journal) against golden
  values captured with the pre-change code. A forward test covers a cost-less tier. 301 related tests
  pass.
- `-cost` NOT dropped; that needs a new objective policy plus an era stamp. W3e box left open, with
  the remaining steps noted in the handoff.
- Finding: the safety gate's archive guard replays the journal under the LEGACY (t/s) policy with no
  flip fence. Switching it to the live policy would push q/h into `frontdoor_speed`, so the two must
  change together. Recorded under W3e.
- Belief kernel: the `autopilot trial journal` adapter's input (journal rows) is unchanged, so no
  projection update is needed.

## RTG-55 MHS-5 — done (orchestrator `4f28e6c3`)

- Harness-R1 @ `411bb548` held-out corpus turned into derived labels:
  `orchestration/datasets/harness_r1_heldout_effect_corpus.json`.
- REPLACE: 4 of 4 patches regressed (mean −8.4 pp). CONSTRAIN: 19 patches, mean +3.9 pp.
- The worst single patch (−16.9 pp) is hint-only CONSTRAIN. This refutes intake-1323#04's claim that
  "every catastrophic regression came from an override". The MHS-4 weights stay ordinal.
- 15 tests.

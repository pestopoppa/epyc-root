# HIL-6 sibling loop (option B): implementation plan

**Decision**: the operator chose HIL-4 option **B, a sibling loop on the shared substrate**, on
2026-10-22 through the decision tool, for coordinator session 3c4ca599
([HIL-4 package and decision note](harness-improvement-loop-design-20261006.md#hil-4--completed-option-decision-package-recommend-b)).
**This plan is build-only.** The 2026-09-16 deferment on running a harness-improvement loop is
still in force. The HS-5b ordering also still holds: no tuning and no efficacy claim before the
P0.4 acceptance and freeze. Any result that cites no human-ratified protocol is an observation
(MEASUREMENT.md).

Owner handoff: [`harness-improvement-loop.md`](../../handoffs/active/harness-improvement-loop.md)
HIL-6. Index row: UFH-08.

## Evidence pins

- The orchestrator was read at `origin/main` `a16750a8` and then rebased onto `755bb5f1`.
- The first seams landed on orchestrator main:
  - `7e9dcfad`: seam S1, the guard extraction;
  - `55465c20`: the sibling skeleton package.
- The root lane base is `origin/main` `49a228791`.
- The GitNexus orchestrator index is 1,262 commits stale (2026-07-22, `f72d1d5`). The re-index
  through `scripts/gitnexus-analyze.sh` was refused by the CPU-admission guard.
  `gitnexus impact --direction upstream` therefore returned `UNKNOWN`: the symbols are not in that
  index. As the rule requires for an unknown risk, the blast radius was derived structurally
  instead, by a grep over `scripts/`, `src/` and `tests/` for every moved name.
  - Upstream callers of the S1 names: PromptForge itself (proposal, GEPA and code-mutation paths
    through `screen_static_safety`, `classify_prompt_effect`, `mutation_risk_gate_reason`,
    `rank_mutations_by_risk` and `prompt_interference_lint`);
    `scripts/autopilot/species/heldout_effect_corpus.py` (`MUTATION_EFFECT_RISK`,
    `MutationEffect`); `scripts/autopilot/prompt_interference_calibration.py`; and four test files.
  - No test monkeypatches a moved name.
  - Risk: MEDIUM, because the guards sit on the live AutoPilot proposal path. The refactor
    therefore went in byte-for-byte, with the identity evidence below.

## 1. Substrate APIs the sibling uses

There is one implementation and two callers. The sibling imports these modules; it never copies
them.

| Component | Home | API the sibling uses | Extraction | Status |
|---|---|---|---|---|
| Journal + shards | `scripts/autopilot/experiment_journal.py`, `journal_shards.py` | `ExperimentJournal(journal_dir=<loop dir>, segment_snapshots=False)`, `.append_ledger_event(dict)`, `.ledger_events(type)` | None needed in AutoPilot. The sibling facade `src/harness_loop/substrate.open_loop_journal` needs an explicit directory. It refuses AutoPilot's `DEFAULT_JOURNAL_DIR`, the shared-clone and `/workspace` spellings of `orchestration/`, and any directory that holds `autopilot_journal*` without the loop marker. The loop writes typed ledger events only, never `JournalEntry` trial rows. So it emits nothing into the trace store (`record()` → `_emit_trace_event`) and closes no AutoPilot-shaped segment. | facade landed (`55465c20`). S3 adds a parity test. |
| AP-53 rejected-mutation ledger | `scripts/autopilot/rejected_mutation_ledger.py` | `build_record(**)`, `append_record(dir, rec)`, `load_records(dir)` | Facade `append_rejection` / `load_rejections`, applied to the loop directory only. **Gap (S3):** `render_for_prompt` prints per-suite deltas, which are scores. HIL-2 item 7 forbids scores in the proposer view. S3 adds a keyword (`include_scores=True` by default, so AutoPilot is byte-identical) and the sibling passes `False`. | facade landed. **S3 landed** (`4adabaaa`): `substrate.render_rejections_for_proposer` is the score-free render. |
| PromptForge / MHS guards | `scripts/autopilot/species/prompt_forge.py` | `screen_static_safety`, `classify_prompt_effect`, `classify_mutation_effect`, `mutation_effect_risk`, `mutation_risk_gate_reason`, `rank_mutations_by_risk`, `prompt_interference_lint`, `MutationEffect` | **S1 done**: the MHS-1/2/4/15 guards moved byte-for-byte to `src/autopilot_core/mutation_guards.py` (standard-library imports only) and are re-exported by PromptForge. **S2**: the MHS-3 eval-leakage guards (`eval_leakage_reason`, `eval_content_leakage_reason`, `suite_special_casing_reason`, `EvalIdVocabulary`, `EvalContentIndex`, `load_eval_id_vocabulary`, the observer hook) and `_prompt_integrity_reason`. Until S2 lands, `substrate.leakage_reason` refuses every text (fail-closed, the MHS-3 contract). | S1 landed (`7e9dcfad`). **S2 landed** (`5d646df9`): `substrate.leakage_reason` is the real fail-closed guard. |
| Infra identity | `src/autopilot_core/infra_fingerprint.py` | `collect_infra_fingerprint(...)`, `compare_infra_fingerprints(cand, ref)` | Reused directly; identity passes as data. The driver refuses a pair whose status is `NON_COMPARABLE` and records `UNVERIFIED` beside the decision. | done (0 d) |
| AP-55 promotion helpers | `src/autopilot_core/ap55_promotion_gate.py` | `seed_rerun_verdict`, `batch_homogeneity`, `promotion_gate` | Already pure. They are used when the sibling's own seed reruns exist (HIL-2 item 5, at least two runs). | done |
| AP-54 eval fence | `src/repl_environment/knowledge_fence.py`; request field `ChatRequest.eval_fence`; echo `eval_fence.state` | `substrate.fenced_eval_request(payload)` sets `eval_fence=True` and refuses an explicit disarm. `substrate.require_fence_active(echo)` refuses a result unless the echo says `active`. | No second fence; the existing request seam is reused. The driver applies both checks on every arm. | facade landed |
| Safety gate | `scripts/autopilot/safety_gate.py` (`SafetyGate.check`, 3,455 lines) | a pure verdict over explicit immutable evidence | **S4**: `check()` is not pure. It updates consecutive failures and the quality history (`record_side_effects`) and reads AutoPilot's live Pareto archive through the module-level promotion-guard provider. S4 extracts the per-suite regression rule (`per_suite_regression_threshold`, the N-aware binding), the reliability floor and the quality-floor checks into pure functions over (candidate, reference, history snapshot). `check()` calls them in the same order and then applies its side effects. The sibling's reference is **its own incumbent arm**, never an AutoPilot tier baseline, so it consumes a verdict and can never ratchet AutoPilot. Until S4 lands, `substrate.autopilot_gate_verdict` raises `SeamNotExtracted`. | **S4 landed** (`c4ebec53`): every `check()` leg is a pure function; `verdict_from_evidence` composes them; `substrate.autopilot_gate_verdict(candidate, incumbent)` uses the loop's incumbent. |

## 2. Extraction order and the AutoPilot regression check at each step

Every step meets the same bar: the moved bodies are byte-identical; the old names re-export the
same objects; the AutoPilot test set is unchanged and green; a golden-output digest matches before
and after; and the diff shows only moves and imports. The test set is the 24 files in the S1 commit
message: PromptForge ×4, MHS-15/17, held-out corpus, TD21-27, eval-leakage operability, actions ×2,
AP-53 ×2, GEPA, journal ×4, AP-54, AP-55 ×2, safety-gate MAD and sequential, and the HIL sidecar.
It runs file-scoped with the orchestrator `.venv` Python, with the worktree as the working
directory.

| Step | Scope | AutoPilot regression check | Estimate |
|---|---|---|---|
| **S1** ✅ | MHS-1/2/4/15 guards → `src/autopilot_core/mutation_guards.py` | Golden digest over 2,580 guard outputs: `7e2d437d…` before and after on `a16750a8`, and `b288deab…` on fresh `755bb5f1` against the rebased lane. Test set: 790 passed and 3 skipped before; 790 and 3 after. Final run after the rebase: 975 passed and 1 skipped; one 120-second wall-clock assertion failed at load average 80, and its file then passed 51/51 on rerun. Identity across the bare and package import contexts is tested in `tests/unit/test_mutation_guards_seam.py`. | done (~0.5 d) |
| **S2** ✅ | MHS-3 leakage guards plus frontdoor integrity → `mutation_guards`. The `set_eval_leakage_observer` global must stay one object, and re-export guarantees it. | The tests that monkeypatch `pf._iter_eval_rows` and `pf._CONTENT_*` are retargeted to the guard module, with assertion bodies unchanged and the retarget diff reviewed. The golden digest covers `eval_leakage_reason` and `eval_content_leakage_reason` over the real pool. `test_prompt_forge_content_leakage.py` (51 tests) and `test_eval_leakage_operability.py` must be green, and `eval_leakage_monitor` must keep the same module object in the bare context. | 1–1.5 d |
| **S3** ✅ | AP-53 score-free projection (`render_for_prompt(..., include_scores=True)`) and a journal-parity test (AutoPilot's reader and `reproposal_rate` read a loop directory) | AP-53 tests ×2 and journal tests ×4 green. A default-argument golden test asserts byte-identical render output on a recorded ledger. | 0.5–1 d |
| **S4** ✅ | Pure gate verdict: extract the regression, reliability and quality-floor checks. `SafetyGate.check` calls them in unchanged order and then applies its side effects. | All 15 `test_safety_gate_*` files green. `gate_replay_reports.py` (read-only journal replay) shows identical verdicts on the frozen journal digest, read from a copy and never the live journal. Side-effect counters are compared before and after on the same inputs. | 1.5–2 d |
| **S5** ✅ | Route AutoPilot's bare imports of the extracted names through the package-qualified modules, only where that removes a dual-module hazard. Final parity pass. | Full AutoPilot test set plus the S1–S4 golden digests. No AutoPilot process is started. | 0.5–1 d |

**Landed 2026-10-22** (orchestrator, all pushed through `serialized_push.py`): S2 `5d646df9`, S3
`4adabaaa`, S4 `c4ebec53`, S5 `aaf29fb1`. The parity evidence for each seam (golden digests, the
journal replay, test counts) is in its commit message and in
[`progress/2026-10/2026-10-22-hil6-b-seams.md`](../../progress/2026-10/2026-10-22-hil6-b-seams.md).
Two deviations from the plan are recorded there:
- S2 also excludes the guard module's own source from the harness corpus. Without that, the moved
  suite-alias table turned `debugbench` into harness vocabulary.
- S4's replay is a purpose-built `SafetyGate.check` replay over a journal copy.
  `gate_replay_reports.py` replays the sequential e-process and never calls `check()`.

The original estimate follows. That leaves **3.5–5.5 engineering days** of extraction after S1. HIL-3 estimated 4–9 days for the
whole extraction; about 0.5 day has been spent. This is a planning estimate, not a commitment.

## 3. Sibling-loop driver skeleton (landed in `55465c20`; not wired)

The package is `src/harness_loop/`. It has no `__main__`, no CLI, no scheduler, cron or
AutoPilot hook, and no concrete proposer, evaluator or judge. A test asserts that no module outside
tests imports it.

- **Proposer interface** (`interfaces.Proposer`): `propose(view: ProposerView, *, max_candidates)
  → ProposalResult(candidates, tokens)`.
  - `ProposerView` is the HIL-2 item 7 index-style view. It carries trace ids, roles, mechanical
    event names and excerpts, plus the declared selection rule, and no outcome field.
    `outcome_keys_in` detects outcome keys at any depth.
  - The view refuses the policy documents named in HIL-1 (`AGENTS.md`, `SKILL.md`,
    `HARNESS_RUN_POLICY.md`, `CLAUDE.md`, skill folders) and any home without a mutable arm (§3.7,
    §3.8).
  - A candidate's rationale is an untrusted self-report (item 17c).
- **Objective and evaluation interface** (`Evaluator`): `evaluate(arm: ArmSpec, split: SplitRef) →
  ArmResult`.
  - `ArmSpec` pins the bytes (content SHA-256) and the closed HIL-2 item 14 pin set. That set is
    asserted equal to `hil_ab_sidecar.ARM_PIN_FIELDS`.
  - `ArmResult` carries the metric, value, unit, direction, the scored and attempted counts,
    per-item outcomes, per-seat `TokenCount` (uncached prefill, decode and cached; `None` means not
    captured), `treatment_fired` (item 12), `fence_state` (item 7), the infra fingerprint, and the
    verification-signal mode (items 4 and 17d).
  - The `DecisionRule` default is `IncumbentWinsTies(margin)` (item 17a). Its decisions are
    `observation` unless a protocol id is cited.
  - `Judge` returns a `VerdictMatrix` with no empty cell and a zero-LLM argmax check (item 17b).
- **Schedule**: there is none in code. The only unit is `SiblingLoopDriver.run_cycle(view,
  CycleSpec)`, which a future, separately authorized entrypoint would call, operator-triggered and
  per cycle. One cycle runs as follows:
  1. Tripwire the proposer context (answer-key markers plus the decoy-rubric canary).
  2. Propose.
  3. Screen each candidate: HIL-1 boundary, MHS-4 gate, MHS-3 (fail-closed until S2), MHS-15 lint
     recorded. Rejections go to the loop's AP-53 ledger.
  4. Evaluate on the **validation** split only, with the fence armed and echoed active on both arms
     and the infra regimes compared.
  5. Write one attempt-ledger row per candidate, with alpha reserved before the evaluation.
  6. Decide, then run the optional judge matrix.
  7. Commit, or KEEP_BASE.
  8. Evaluate the committed arm on the **arrival** split with no tuning.
  9. Write a `hil_cycle_commit` journal event with the harness bytes, tokens per seat, lint
     warnings and `decision_grade=observation`.

  The tuning split may not overlap validation, arrival or test. `final_test` touches the test split
  exactly once.
- **Pilot validator** (`pilot.PilotDesign`, `unmet_requirements`): the driver refuses to construct
  while any HIL-6 pilot requirement or HIL-2 design item is unmet.
- **Tests**: `tests/unit/test_harness_loop_skeleton.py` (23 tests) and
  `tests/unit/test_mutation_guards_seam.py` (5 tests).
  - The tests run two cycles on fakes, with a refused arrival-overlap tune between them.
  - The carrier test passes against root `origin/main` `scripts/vidya`; it skips when `EPYC_ROOT`
    lacks the carrier.

## 4. HIL-2 items 1–22

`pilot.CHECKLIST` holds this mapping in code. A **design** item is a `PilotDesign` field that must
be declared before arms are generated; declaring it satisfies the design half only.

| # | How it is satisfied | Where |
|---|---|---|
| 1 matched-rollout baseline | design | `matched_rollout_baseline`; the arm role `matched_rollout_baseline` is finalized under its own run_id |
| 2 all seats' tokens | code | `TokenCount.seat`, summed into `tokens_by_seat` (proposer, judge, solver); the design requires all three seats |
| 3 disjoint splits, validation-only selection, single test touch | code | `splits_disjoint`; selection in `run_cycle` uses validation; `final_test` refuses a second touch |
| 4 with and without the verification signal | design | `verification_arms ⊇ {with, none, self_judged}` |
| 5 at least two runs, CI, MDE | design | `runs >= 2`, `mde` |
| 6 unmodified-harness control | design | `unmodified_control`; arm role `unmodified_control` |
| 7 isolation | code | fence armed and required `active`; tripwire with the decoy canary; outcome-free `ProposerView`; `SplitRef.labels_resolved_at` |
| 8 context-policy contract | design | home 3.6 requires the `no_management` and `wording_only` controls |
| 9 arrival split and commitment | code | arrival evaluation with no tuning; `stopping_rule` declared |
| 10 harness growth | code | `harness_bytes` per cycle event |
| 11 validation power | design | `paired_n`, `expected_discordant`, `min_win_share` |
| 12 feature exercised | code | `treatment_fired` required on every result |
| 13 headroom | design | `headroom_note` |
| 14 pinned arm identity | code | `ArmSpec.pins` must be the closed item-14 set |
| 15 exclusions declared | design | `exclusions_declared` |
| 16 token-cost columns | code | `ArmResult.tokens` required |
| 17 judged arms | code | `IncumbentWinsTies`, `VerdictMatrix.validate` and `choice_is_argmax` |
| 18 regression readout | design | `regression_set_id` |
| 19 per-role arm design | design | `per_role_arm_set`; a reviewer mechanism needs a served local `reviewer_model` |
| 20 memory stream positions | design | homes 3.1, 3.2 and 3.4 require `STREAM_POSITIONS` |
| 21 attempt ledger | code | `AttemptLedger` (alpha reserved at open; interrupted attempts consume alpha; restart resumes) |
| 22 arm prompt lint | code | MHS-15 lint per candidate, recorded in the cycle event (warn-only) |

## 5. HIL-6 pilot requirements, and the M9 extras

- **P1, at least two cycles with an arriving split.** The validator requires `cycles >= 2` and
  pairwise-disjoint train (T1), validation, arrival (T2) and test splits. Cycle 2 re-tunes from the
  cycle-1 harness, and a stalled round is KEEP_BASE, not a failure (tested).
- **P2, editor-capability arm.** `local_editor_model` (30B-A3B class, served on EPYC) and a
  different `reference_editor_model` run on the same split, executor and typed failure dossier. The
  dossier is mechanical L2 event names (HIL-12), not outcomes.
- **P3, cross-model judge.** The judge must differ from every proposer model, and its family must
  differ from the local editor's. The pinned cloud judge `sonnet-5-5-low` (`claude-sonnet-5-5`,
  `orchestration/cloud_judges.yaml`) qualifies against a Qwen local editor. Three cautions:
  1. **If the reference editor is also Anthropic**, the judge shares its family. Either use an
     OpenAI-family reference editor or report that correlation beside the reference-arm results.
  2. The judge entry is `verified_live: false`, and its egress is Anthropic over the Claude CLI.
     Only suite content cleared for that egress may go into a judge call, and the call log records
     the egress.
  3. The current endpoint is `/v1/typed/coherence_judge`. A credibility verdict matrix needs its own
     typed judge schema; that is part of HIL-6h.
- **P4, memory-accumulating homes.** For homes 3.1, 3.2 and 3.4, HIL-2 item 20 stream positions are
  required.
- **P5, items 7–22.** See §4.

**M9 fired on 2026-10-22**, because an architecture was selected and this pilot design exists. Its
first step, "add the named arm or diagnostic to the pilot", is applied here:

| M9 extra | Added as |
|---|---|
| near-ceiling suite power statement | Part of the item 11 declaration. If the incumbent's validation pass share is above 0.9, `expected_discordant` must be stated from that headroom, and a run that cannot reach it is labelled underpowered. |
| zero-adoption diagnosis | Item 12. A result with `treatment_fired == 0` is labelled *not exercised*, and its null is uninformative about content. This is a report rule (HIL-6h). |
| reference-trajectory diagnosis arm | Diagnostic only. The proposer is shown a reference trajectory in a separate arm whose result is never used for selection. It sits outside item 7's selection path and is reported apart. |
| offline-then-freeze | The pilot tunes offline and freezes the committed bytes. Nothing mutates during serving; promotion is a separate, human-applied step. |
| local-editor port of published prompts | The local editor's meta-prompt is a ported published editor prompt, pinned by SHA-256 in the design notes. |
| planner self-modification | Excluded. The loop's own proposer, meta-prompt and evaluator lie outside the mutable surface (item 21, protected layer). |
| regression-set definition | `regression_set_id` names the incumbent-passing validation items plus the labelled unsafe-control items (item 18). |

## 6. VB-HIL-WRITE producer call at finalize

`src/harness_loop/finalize.py`:
- `observation(result, arm, ...)` projects an `ArmResult` and `ArmSpec` into the carrier
  observation fields. It maps the incumbent and both control roles to `BASELINE`, and the candidate
  to `CANDIDATE`; the root carrier's arm vocabulary is closed.
- `finalize_run(out_dir, run_id, results_path, observations, pins, protocol_id=None)` then calls
  `scripts/benchmark/hil_ab_sidecar.finalize_hil_run` (orchestrator `5195ad53`). That hook calls
  the root carrier, `scripts/vidya/adapters/harness_improvement.write_belief_measurements`.

The call happens once per paired comparison, after the raw per-item result file is closed. Each
control arm is finalized under its own run_id; a duplicate arm × feature × objective is refused.
`protocol_id` stays `None` unless a human-ratified protocol applies, so the rows remain
observations and `claim_tuple.grade()` decides. A missing value is not a row.

## 7. Remaining steps (tracked as HIL-6 sub-items in the handoff)

| Item | Work | Estimate |
|---|---|---|
| HIL-6d ✅ 2026-10-22 (`5d646df9`) | S2: MHS-3 leakage guards and frontdoor integrity → `mutation_guards` | 1–1.5 d |
| HIL-6e ✅ 2026-10-22 (`4adabaaa`) | S3: AP-53 score-free projection and journal parity | 0.5–1 d |
| HIL-6f ✅ 2026-10-22 (`c4ebec53`) | S4: pure gate verdict | 1.5–2 d |
| HIL-6g ✅ 2026-10-22 (`aaf29fb1`) | S5: AutoPilot call-site routing and final parity | 0.5–1 d |
| HIL-6h ✅ 2026-10-22 (`43bc90a7` + `c85b85ef`) | Concrete parts, build-only and not wired: local-editor proposer over the orchestrator `/v1`, reference-editor proposer, typed credibility judge (cloud `sonnet-5-5-low` adapter), the first feature's evaluator through `/chat` with `eval_fence`, and the report rules (zero-adoption, underpowered) | 3–5 d |
| HIL-6i ✅ 2026-10-22 (`1ae0ad42` + `05bfb4de` + `c69ba5a1`; doc [`hil6i-pilot-design-first-feature-20261022.md`](hil6i-pilot-design-first-feature-20261022.md)) | Pilot design instance for the first feature: choose the home, fill `PilotDesign` including the M9 extras, and pass `unmet_requirements() == []` | 0.5–1 d |
| HIL-6j | Entrypoint and schedule (operator-triggered per cycle). Blocked by the operator's 2026-09-16 deferment on running a loop, plus P0.4 freeze and applicable protocols. | 0.5 d once unblocked |

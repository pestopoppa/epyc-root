# Backlog refactor 2026-11 — execution

**Status**: ACTIVE — plan approved by the operator 2026-11-02 (D1–D7); plan landed, no fold executed yet.
**Created**: 2026-11-02
**Priority**: P1 — the backlog surface every session dispatches from
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Owner**: ws58
**Scratch**: `/mnt/raid0/llm/tmp/ws58-csh/` · worktrees: `/mnt/raid0/llm/worktrees/ws58-brf-*`

Plan, decisions D1–D7, manifests and provenance: [`docs/design/backlog-refactor-2026-11/PLAN.md`](../../docs/design/backlog-refactor-2026-11/PLAN.md).
Lint: `scripts/handoffs/task_lint.py` (`report` / `migrate` / `publish`). Measurement tasks follow
[`measurement-sufficiency.md`](../../docs/guides/agent-workflows/measurement-sufficiency.md).

## Atomic per-fold gate (every T1/T7 box)

A fold commit lands only when ALL hold, with the records attached to the commit:
`index_state.py` rc 0 ∧ `index_state.py --check` rc 0 ∧ readiness diff ∅ (route 1a) ∧ zero lost tasks vs
the manifest after apply-time reconciliation against current `origin/main` (ticked-since-pin never migrated
as open; new boxes migrate with current text) ∧ `task_lint.py migrate` rc 0 on every touched file ∧ dashboard
tests pass (4 known `/amd-ai-lab` nav failures listed) ∧ dashboard smoke counts match the fold's
reconciliation record (board, graph nodes/edges/ready, queue rows, pipeline classes, zero orphaned
`handoff_task` rows / session slugs) ∧ every retired ID carries a `Repoint-Reason:` trailer and a
`.folded.json` entry (D5). Index rows are applied by the owning session (ruling (b)).
**Migrate leg, exact command (BRF-T6-1; the plan defines no gate script, so this is the binding)**, run in the fold worktree
on the staged fold commit; an empty file list is a gate FAILURE, never a vacuous pass (every fold touches its destination):
`files=$(git diff --cached --name-only --diff-filter=AMR -- 'handoffs/active/*.md'); test -n "$files" && python3 scripts/handoffs/task_lint.py migrate $files`
**Publish leg (BRF-T6-1)**: `scripts/coordination/rowflow/publish_row.py` resolves `handoff_task` (`<file>.md:<TASK-ID>` or
`:<LINE>`) to the open box and refuses the row unless `task_lint.py publish` passes it (identity c, stop rule s, run-cited
or provisional+pilot estimate, no NEEDS-*, no non-inference payload); tests `scripts/coordination/tests/test_rowflow_publish_lint_ws58.py`.
**Stop rule (every fold)**: any gate leg red → revert the local fold commit, record the failing leg in
this handoff, do not push; two consecutive reds on the same fold → stop T1 and re-plan that fold.

## T0 — plan landed

- [x] **BRF-T0** Land PLAN.md, manifests, reviews, `task_lint.py` + tests, this handoff (2026-11-02).

## T1 — route-1a folds (175 → 63, readiness-neutral; D1)

- [x] **BRF-T1-0** [non-inference] Re-run apply-time reconciliation of `backlog-refactor-plan-20261102.json` against current
  `origin/main`; emit the ordered fold list (one entry per fold commit) into scratch; tick when the list is
  committed into PLAN.md as an appendix. Zero inference.
  ✅ 2026-11-02 `030991943` — [`fold-list-1a.json`](../../docs/design/backlog-refactor-2026-11/fold-list-1a.json)
  + PLAN.md appendix: 26 folds / 4 batches, 176 → 77 handoffs (75 after RET), readiness diff ∅ by the real
  `derive_readiness`; reconciliation: 0 ticked since pin, 6 kv-prefix boxes re-identified, RTG-63 carried new. [no-belief: tooling]
- [ ] **BRF-T1-1** [roll-up] One fold commit per entry of the BRF-T1-0 list, each through the atomic gate.
  Per fold, add a box `BRF-T1-<n> fold <sources> → <target>` here before starting it and tick it in the fold
  commit itself. Non-dispatchable parent.
  - [x] **BRF-T1-F1** fold multimodal-pipeline → `speech-and-multimodal.md` (rename of conversation-stack.md, rows INF-41 → INF-79). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F2** fold bulk-inference-campaign, eval-benchmark-cost-reduction, eval-tower-architecture-audit-2026-07-20, eval-tower-loop-robustness-audit-2026-07-20, fable5-window2-findings-01-optimizer-integrity, inference-batch-loop, prompt-construction-determinism, re4-protocol-redesign, scoring-infra-standardization → `eval-tower-program.md` (rename of eval-tower-verification.md, rows EVL-07, EVL-11, EVL-12, EVL-13, EVL-19, INF-24, RTG-27, EVL-35, EVL-42 → EVL-14). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F3** fold amd-ai-lab-website-publication, frontier-f4-continuity-backup, integration-test-coverage, loop-state-offraid-backup, refactoring-multirepo-2026-10, repo-readiness-scorer → `engineering-hygiene-backlog.md` (rename of non-inference-backlog.md, rows UFH-11, EVL-26, EVL-30, RTG-60, RTG-61, EVL-38 → RTG-22). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F4** fold capability-registry-and-promotion, model-artifact-integrity, model-exec-containment, model-stack-single-source-update-pipeline, model-stack-update-pipeline-audit, standardized-stack-update-pipeline-finalization, wp12-fleet-layer-design → `stack-lifecycle-program.md` (rename of stack-change-governance-pipeline.md, rows RTG-06, RTG-59, UFH-16, RTG-19, RTG-20, RTG-38, RTG-43 → RTG-36). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F5** fold iqk-iquant-enablement, tq3-quantization-evaluation → `quantization-and-low-bit.md` (rename of exl3-cpu-mi210-implementation.md, rows INF-26, INF-54 → INF-80). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
- [ ] **BRF-T1-MEQ** [non-inference] Split the model-evaluation queue into 3 gate-homogeneous files (D2), through the atomic gate.
  - 2026-11-02 partial: `9d63885bd` consolidated the 14 queue files into 3 (`model-evaluation-queue.md` EVL-02, plus INF-61 and INF-76 tracks); 206 tasks before/after, readiness-neutral. Residual: the 39 carved boxes from 18 files (`fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ), 7 of whose sources are batch-1 folds; they move after batch 1 lands.
- [x] **BRF-T1-RET** Retire `swarm` and `model-stack-change-standardization-audit` (D4): move to
  `archived/`, retire IDs with `Repoint-Reason:` trailers and `.folded.json` entries.
  - 2026-11-02: done in `530a884f7` (RTG-18/RTG-39 rows removed, ledgers in `completed/`, `.folded.json` ids, checklist extracted to `docs/guides/agent-workflows/stack-change-checklist.md`; index 176->174 at apply, 0 tasks lost) [no-belief: tooling]

## T2 — per-track gate tooling (1b) and dashboard fixes

- [x] **BRF-T2-1** [non-inference] `index_state.py`: per-track gates (readiness per track inside a folded handoff). Done when: tests cover a two-track folded handoff with one gated track. Zero inference. `3e2b99bb5` — marker `<!-- gate: <row-id|task-id>,… | none -->`; tests `tests/test_index_state_track_gates.py`. [no-belief: tooling]
- [x] **BRF-T2-2** [non-inference] `handoff_parser`: `folded` lifecycle from the banner; roll-up boxes excluded from `count_tasks`. Done when: parser tests for both pass. ✅ 2026-11-02 `6ce0647ef` [no-belief: tooling]
- [x] **BRF-T2-3** [non-inference] `server._parse_activity_log*`: moved-box pairing, fold-commit trailer exclusion, `moved`
  field; `build_handoff_timeline`: roll-up exclusion, one-time `refactor_markers` annotation, historical
  counts carried across renames; tests. ✅ 2026-11-02 `6ce0647ef` [no-belief: tooling]
- [x] **BRF-T2-4** [non-inference] `.folded.json` resolution in detail (`handoffs.html ?id=`), graph, `queue_payload`/rowflow
  and `pipeline_status._handoff_of`/`build_payload`; roll-up exclusion in `classify_handoffs`; test: every
  ready/running row and session slug resolves to a graph node in a folded scratch tree. Done when: that test passes. ✅ 2026-11-02 `6ce0647ef` [no-belief: tooling]

## T3 — replays and deterministic tails (analyses now; D3)

- [x] **BRF-T3-1** ✅ 2026-11-02 (ws58): 19 cells enumerated. They cover 5 replay candidates (as 7 cells), EXL3, the E5 adjudication and 10 other tails. The worklist is `docs/design/backlog-refactor-2026-11/t3-cells.json`, and 3 evidence paths were KEEP-listed in `evidence-keep-20261102.txt` → T3 additions. [no-belief: worklist enumeration] [non-inference] Enumerate replay / deterministic-tail cells from `backlog-experiment-manifest-20261102.json`
  into a scratch worklist with their retained inputs. Done when: the worklist is committed under `docs/design/backlog-refactor-2026-11/`. Zero inference.
- [x] **BRF-T3-2** ✅ 2026-11-02 (ws58): all 19 cells in `t3-cells.json` have a disposition. Ten ran as analyses (C6, G11, Nemotron, AP, E5, EXP-06, LID1, RT-6, CAP-02, CAP-06), five were already done by their owners or covered by an existing record (KPF, Parakeet, HIL16A, CAP-07, G13), two need no analysis without inventing evidence (EXL3, NEMO) and two are UNCOVERED by the stop rule and stay open (VIDYA, AP-DGM). Commits `2e2ca91eb`, `8827db1c6`, `6a126f962`, `b2adcda21`. Per D3 the tick waits on the analyses having run, not on consumer boxes closing. [belief: cc] [non-inference] Run the zero-inference analyses over retained data; record results as OBSERVATIONs. Ticks on the source
  boxes wait for proven coverage of the cell. Stop rule: a cell without retained inputs covering it is
  marked uncovered and left open, never ticked.
  - 2026-11-02 partial (ws58): this pass ran the E5 adjudication (VALID 0 / INVALID 4 / UNRESOLVED 4), the KB G11 disagreement analysis (ticked G11) and the STT Nemotron re-read. No scorer or parser fix was needed. Not yet run: C6 consumer re-read, RPL-AP analyses (code builds), EXP-06 custody, LID1, CAP-01 Q38FN replay, CAP-06 threshold replay. See `progress/2026-11/2026-11-02-ws58-brf-t3.md`. [belief: cc]
  - 2026-11-02 RPL-AP (ws58): the analysis code was built and run (orchestrator `95d663e5`). P17.BT-5a is INCONCLUSIVE (insufficient coverage: 8 hinted trials of 87 pairs). AP-ME-1's offline baseline is measured: a 30-card shared STM, median 1,970 tokens. Neither box is ticked; each has a dated residual. See OBS-6 and OBS-7 in the progress file. [belief: cc]
  - 2026-11-02 second pass (ws58): C6 re-read (9 of 11 dirs reproduce under unchanged predicates), EXP-06 custody (690 / 65 re-derived; fresh inventory not regenerable in this namespace), CS-26.LID1 arm (b) (tags found in the Nemotron 3.5 tc-r2 dir, input-incompatible with the crop protocol), CAP-01 Q38FN RT-6 (bit-exact replay) and CAP-06 threshold re-read (5 tails byte-identical) all ran. No source box was tickable from a replay; each got a dated sub-bullet with its residual. No scorer or parser defect found. Still not run: CAP-02 scans (code builds). See `progress/2026-11/2026-11-02-ws58-brf-t3-pass2.md` (OBS-8 to OBS-12). [belief: cc]
  - 2026-11-02 third pass (ws58, `b2adcda21`): the CAP-02 HIL scans ran. The pass-2 note that they were a code build was wrong; the scan and flag code were already on orchestrator origin/main. The L2 scan, 15c/15d evals, AUC table and 80-recording verify reproduce the filed outputs with 0 mismatches, and the spectrum report reproduces under the scanner it was built with. HIL-13 is ticked (40 tests pass, report with N per category, item-3 shares 0.545 mechanical / 0.455 unclassified). HIL-15, HIL-18a and HIL-16b stay open, each with a dated residual sub-bullet. One defect noted, not fixed here: `spectrum_replay.traces_for_manifest` sets no `tool_required`, so a spectrum report built today drops the zero-step agreement block. See OBS-13 in `progress/2026-11/2026-11-02-ws58-brf-t3-pass3.md`. [belief: cc]

## T4 — the 4 bounded pilots (D3)

Each pilot carries its `sufficiency` block from the experiment manifest; owners are the accountable handoffs from the experiment manifest (written 2026-11-02, BRF-T1-0 session).
The 16 other packages stay provisional until owner-reviewed pilot results exist.

- [ ] **BRF-T4-EXP01** [inference] EXP-01 speed-pair pilot. Owner: [`iqk-iquant-enablement.md`](quantization-and-low-bit.md#track-iqk-iquant-enablement)
  (INF-26, per v6 and the experiment manifest: T2/T3 hold the executable KT gates; [`tq3-quantization-evaluation.md`](quantization-and-low-bit.md#track-tq3-quantization-evaluation) STEP 2/3 are consumers and record the transfer).
  Stop rule: manifest `sufficiency` EXP-01 — pair against the completed control first; stop on answer or
  futility at each checkpoint; quality pass not reducible (gate stays open). Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
  Identity: Q38FN-lane IQ4_KT/Q4_K_M + IQ2_KT/IQ2_XXS GGUFs on `ik_llama.cpp@c04881fc0`, one CPU quarter, ≤90 min; pilot box T2 → EXP01-PILOT.
  BLOCKED (operator decision, 2026-11-02 ws58): the manifest identity is not runnable — see EXP01-PILOT in the owner.
- [ ] **BRF-T4-EXP04** [inference] EXP-04 crossover screen, riding a granted quiet window only. Owner: [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) PF1 (executes as its box **PF1-EXP04**,
  row `brf-exp04-pf1-crossover-pilot-20261102`, published by ws58 2026-11-02).
  Stop rule: manifest `sufficiency` EXP-04; stop on answer/futility; no window granted → not READY. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff (PF1-EXP04 filed with the owner's EXPAND/REVISE/INCONCLUSIVE review).
- [ ] **BRF-T4-EXP09** [inference] EXP-09 pilot. Owner: [`tool-output-compression.md`](tool-output-compression.md) (TOC-SP-3). Stop rule: manifest `sufficiency` EXP-09. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
  Row `brf-exp09-pilot-20261102` (ws58; one CPU quarter, cap 45 min, own v10 kernel-store llama-server on :18409,
  worker Qwen3.6-35B-A3B-MTP-Q8_0, greedy, MTP off). Control = current `_spill_output` (orchestrator `3a428cb3`,
  executed unchanged). Corpus: 12 frozen failing logs, [`exp09-failing-log-corpus-manifest-20261102.json`](../../docs/design/backlog-refactor-2026-11/exp09-failing-log-corpus-manifest-20261102.json).
- [ ] **BRF-T4-CAP04** [inference] CAP-04 reasoning-budget-curve pilot on the SERVED config, bounded at <=76 generations. Owner:
  [`reasoning-effort-levels.md`](reasoning-effort-levels.md) (TB-1) (executing session ws58). Row `brf-cap04-pilot-20261102-v2` (supersedes `brf-cap04-pilot-20261102`, whose critic ran thinking OFF and so did not describe the served model) on the MI210 `mi210_0,184-191`;
  est: provisional; pilot: bounded <=76 generations, 2.5 h cap (expected ~1.75 h, estimate 7800 s). Metric: accuracy, higher is better. Identity: frontdoor Qwen3.6-35B-A3B-MTP-Q8_0 (sha c1283d8b) + architect_critic Qwen3.8-27B-Q8_0
  (sha a680f44a), v10 kernel store 10303, own llama-server, chat path, served terse template 1443ea9ab4bb, q8_0 KV, seed 42, top_k 40, top_p 0.95, repeat_penalty 1.1; 20
  olympiadbench_hard + 20 GPQA-Diamond-CoT pinned items (items sha 81ef522b). **Served flags** (registry `model_registry.yaml` server_mode / generation_defaults, read 2026-11-02): architect_critic
  `enable_thinking=true, reasoning_effort=medium`, temp 0.1, draft-dflash n-max 7 (`:2009-2012`, `:2577-2579`); frontdoor `enable_thinking=false` + `--reasoning off`, temp 0.3, draft-mtp n-max 4
  (`:1837-1839`, `:2226-2228`, `stack_priors.yaml:826`). The budget (`max_tokens`) counts the thinking tokens, so truncation lands inside the thinking block; summary.json records the truncation-inside-thinking rate per cell.
  Cells: each (item, level) has a single generation at 32768 and the 8k/16k cells are derived as a nested prefix (finished at b iff finished and completion_tokens <= b), validated by 4 fresh 8192 CHK generations
  (prefix/equality check; derived cells count when `nested_derivation_valid` is true): E frontdoor x {L2,L3} x 20 GPQA; TB frontdoor x 20 olympiad and architect_critic x up to 12 olympiad; the crossed frontdoor x {L2,L3} x {8k,32k} x 10 GPQA
  is the derived X view of E, so **TB-4 COVERED (screen)**. TB-1 reports BOTH denominators (overall, finished-only) plus truncation; a knee
  below the production ceiling settles TB-3 for that role only, never E-2/E-3.
  Stop rule: manifest `sufficiency` CAP-04 (exploratory; look at every cell; stop on answer or futility is an
  operational decision, never a gate result). Critic LOOK at 8 items: futility when >=75% are truncated at 32768 (no knee inside the range), answer when trunc<=5% and no correctness change between that budget and 32768; otherwise continue to 12 items. STOP, deadline or 9000 s cap gives a resumable partial; budget overrun,
  frontdoor think leak, critic thinking not engaged or short slot context is INVALID. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
  - [ ] **CAP04-AG** [inference], NOT covered by this pilot: architect_general (87 GB, served on CPU). The pilot screens the curve shape on the served critic config only; architect_general is the expansion if a knee appears below the production ceiling (budget curve on its own served config, CPU, placement and thinking flags re-read from the registry at that time). Not READY until the pilot's result is recorded; est: provisional; Metric: accuracy, higher is better; Stop rule: manifest `sufficiency` CAP-04. Done when: either the pilot shows no knee below the production ceiling (recorded as an OBSERVATION: expansion not needed) or the architect_general curve stops on answer or futility at a checkpoint and is recorded as an OBSERVATION in the owner handoff.
- [ ] **BRF-T4-R** [non-inference] NEEDS-OWNER Owner review of the four pilot results; promote or re-scope the 16 provisional packages.

## T5 — D7 decision-package delivery

- [x] **BRF-T5-1** [non-inference] Write the 158 per-handoff option sheets (options + tradeoffs + recommendation) from the task manifest, in fold order. Done when: all 158 sheets are committed under `docs/design/backlog-refactor-2026-11/`.
  ✅ 2026-11-02 `4d6ea0b3d`: all 158 accounted for in `decision-packages/` (26 destination packages + `index.json`, fold-list-1a order): 119 delivered; 39 excluded with reasons (26 decided/issued authorization, 11 merged, 2 not an operator choice). [no-belief: tooling]
- [ ] **BRF-T5-2** [roll-up] Non-dispatchable parent. Deliver each package via the decision tool at its fold; record the answer in the
  owning handoff. A dismissed question pauses only its own item.

## T6 — staged lint enforcement (D6)

- [x] **BRF-T6-1** Bind `task_lint.py migrate` in the fold commit gate and `task_lint.py publish` in rowflow publish.
  ✅ 2026-11-02 `4d6ea0b3d`: publish leg in `publish_row.py` (installed to `compute-flags/bin/rowflow/`, cmp 3/3); migrate leg = the exact command in the gate section above. Tests 9/9 new, rowflow 58 pass + 1 known failure. [no-belief: tooling]
- [x] **BRF-T6-2** [non-inference] Add `task_lint.py` to `index_state.py --check` as warn-only. `3e2b99bb5` — TASK-LINT column on stderr, exit code untouched. [no-belief: tooling]
- [ ] **BRF-T6-3** [non-inference] Make the lint blocking in `--check` and in wrap-up once BRF-T7-1 is ticked. Done when: `--check` exits non-zero on an untagged lint failure (test).

## T7 — 1b folds (63 → 29)

- [ ] **BRF-T7-1** [roll-up] Non-dispatchable parent. After BRF-T2-1 lands: one fold commit per 1b fold through the atomic gate
  (readiness diff replaced by per-track readiness equality); add a box per fold before starting it.
- [ ] **BRF-T7-MEQ** Merge the 3 model-evaluation queue files into 1 (D2).

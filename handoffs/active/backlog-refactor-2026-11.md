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
- [x] **BRF-T1-1** [roll-up] One fold commit per entry of the BRF-T1-0 list, each through the atomic gate.
  Per fold, add a box `BRF-T1-<n> fold <sources> → <target>` here before starting it and tick it in the fold
  commit itself. Non-dispatchable parent.
  - [x] **BRF-T1-F1** fold multimodal-pipeline → `speech-and-multimodal.md` (rename of conversation-stack.md, rows INF-41 → INF-79). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F2** fold bulk-inference-campaign, eval-benchmark-cost-reduction, eval-tower-architecture-audit-2026-07-20, eval-tower-loop-robustness-audit-2026-07-20, fable5-window2-findings-01-optimizer-integrity, inference-batch-loop, prompt-construction-determinism, re4-protocol-redesign, scoring-infra-standardization → `eval-tower-program.md` (rename of eval-tower-verification.md, rows EVL-07, EVL-11, EVL-12, EVL-13, EVL-19, INF-24, RTG-27, EVL-35, EVL-42 → EVL-14). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F3** fold amd-ai-lab-website-publication, frontier-f4-continuity-backup, integration-test-coverage, loop-state-offraid-backup, refactoring-multirepo-2026-10, repo-readiness-scorer → `engineering-hygiene-backlog.md` (rename of non-inference-backlog.md, rows UFH-11, EVL-26, EVL-30, RTG-60, RTG-61, EVL-38 → RTG-22). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F4** fold capability-registry-and-promotion, model-artifact-integrity, model-exec-containment, model-stack-single-source-update-pipeline, model-stack-update-pipeline-audit, standardized-stack-update-pipeline-finalization, wp12-fleet-layer-design → `stack-lifecycle-program.md` (rename of stack-change-governance-pipeline.md, rows RTG-06, RTG-59, UFH-16, RTG-19, RTG-20, RTG-38, RTG-43 → RTG-36). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F5** fold iqk-iquant-enablement, tq3-quantization-evaluation → `quantization-and-low-bit.md` (rename of exl3-cpu-mi210-implementation.md, rows INF-26, INF-54 → INF-80). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F6** fold delegation-context-preassembly, memento-block-reasoning-compression, per-request-reasoning-budget, rao-redel-substrate-spike, reasoning-compression, reasoning-effort-levels, tool-output-compression → `context-and-token-economy.md` (rename of context-folding-progressive.md, rows RTG-10, UFH-03, EVL-33, EVL-34, UFH-05, RTG-28, UFH-07 → RTG-08). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F7** fold agent-world-env-synthesis, mathsmith-hc-formalizer-eval, multi-file-coding-completion-capability, rlm-contested-claims-self-evaluation, tool-use-eval-contract → `benchmark-suites.md` (rename of canonical-judge-suite-revamp.md, rows RTG-01, EVL-31, RTG-21, EVL-39, EVL-46 → EVL-08). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F8** fold colbert-reranker-web-research, document-parser-table-bench, opendataloader-pipeline-integration, searxng-search-backend, sliders-local-validation → `knowledge-pipelines.md` (rename of internal-kb-rag.md, rows PIP-01, PIP-02, PIP-05, RTG-33, EVL-43 → PIP-04). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F9** fold agent-file-prose-compression, frontier-f2-self-running-lab, frontier-f3-data-flywheel, stale-open-audit-2026-07-18 → `frontier-lab-automation.md` (rename of intake-derived-work-2026-07-25.md, rows EVL-01, EVL-24, EVL-25, EVL-44 → EVL-29). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F10** fold cpu-fused-decoder-blocks, laguna-s21-cpu-port, moe-spec-cpu-spec-dec-integration, v9-kernel-per-request-speculative-params → `fable5-window2-findings-03-portfolio-and-master-queue.md` (rows INF-67, INF-28, INF-40, INF-58 → EVL-21). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F11** fold fable5-window2-findings-02-heterogeneous-gpu, fable5-window2-findings-05c-mi210-lever-category-matrix, gpu-acceleration-path, mi210-big-model-and-acceleration-roadmap, qwen38-27b-replace-qwen36 → `mi210-serving-program.md` (rename of gpu-serving-tie-in-program.md, rows EVL-20, EVL-48, INF-18, INF-34, INF-60 → INF-22). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F12** fold autokernel-restart-and-strip → `agent-collab-rnd-harness.md` (rows INF-64 → INF-02). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F13** fold opencode-shell-integration → `harness-improvement-loop.md` (rows UFH-15 → UFH-08). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F14** fold qwen-chat-template-evaluation → `repl-turn-efficiency.md` (rows RTG-54 → EVL-37). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F15** fold multiscreen-attention-evaluation, streaming-llm-baseline, triattention-kv-selection → `attention-matching-kv-compaction.md` (rows INF-42, INF-51, INF-56 → INF-05). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F16** fold cpu-prefill-compute-large-models, large-moe-expert-parallelism → `sarathi-serve-cpu-evaluation.md` (rows INF-09, INF-29 → INF-49). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F17** fold batched-decode-measurement, dynamic-stack-concurrency, numa-placement-defect-20260730, shape-keyed-contention-gating, within-role-placement-state-machine → `numa-placement-and-contention.md` (rename of numa-topology-cutover-resume-20260730.md, rows INF-07, RTG-11, INF-43, RTG-35, RTG-42 → INF-45). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F18** fold churn-pipeline, dashboard-architecture-restructure, handoff-index-and-backlog-graph → `coordination-and-churn-pipeline.md` (rename of session-bus-thin-dispatcher.md, rows RTG-62, RTG-47, RTG-46 → RTG-34). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F19** fold fleet-fanout-measurement, wrap-up-division-of-labor-policy → `loop-owned-fleet-implementation.md` (rows RTG-49, RTG-51 → RTG-52). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F20** fold autopilot-dashboard-fidelity-audit-2026-07-22, autopilot-decision-plane-audit-2026-07-22, batched-edit-parallel-apply, bep-dcp-falsification-harness, evidence-plane-event-sourcing-and-narrative, evidence-plane-instrument-repair, evidence-plane-ledger-and-sequential-verdicts, loops-and-dashboards-audit-2026-07-05, objective-task-rate-goodput, orchestration-robustness-audit-2026-07-11, scaffold-autopilot-cost-lever-deployment → `autopilot-program.md` (rename of autopilot-continuous-optimization.md, rows RTG-03, EVL-03, RTG-04, RTG-05, RTG-13, EVL-15, EVL-16, RTG-16, RTG-23, RTG-24, RTG-32 → RTG-02). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F21** fold promptforge-mutation-safety-contract → `autopilot-sequential-allocation.md` (rows RTG-55 → EVL-04). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F22** fold frontier-f6-upstream-publication, llama-cpp-dsa-contribution → `gemma-challenge-kernel-techniques-v7.md` (rows EVL-27, INF-31 → INF-16). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F23** fold mi210-q8-dequant-gemv-roofline → `agentic-rocm-kernel-authoring.md` (rows INF-37 → INF-03). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F24** fold repl-session-memory-maturity, unified-trace-memory-service → `memory-program.md` (rename of episodic-memory-integrity.md, rows EVL-36, RTG-41 → EVL-10). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F25** fold reviewer-calibration-accounting, reviewer-typed-artifacts → `reviewer-latency-and-sampling-budget.md` (rows REV-03, REV-09 → REV-06). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T1-F26** fold internal-interaction-lifecycle, learned-routing-controller, model-capability-descriptors, retrain-routing-models, tri-role-coordinator-architecture, typed-decision-plane, x-mas-text-routing → `routing-program.md` (rename of decision-aware-routing.md, rows RTG-14, RTG-15, RTG-17, RTG-29, RTG-40, RTG-56, RTG-45 → RTG-09). ✅ 2026-11-02 — readiness-neutral, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - 2026-11-03: all 26 route-1a folds landed (BRF-T1-F1..F26; batches 1-4, last 9740bdb35); 176 -> 64 handoffs, readiness-neutral, 0 tasks lost. [no-belief: tooling]
- [x] **BRF-T1-MEQ** [non-inference] Split the model-evaluation queue into 3 gate-homogeneous files (D2), through the atomic gate. ✅ 2026-11-03 `9d63885bd` + `a01625aa3` [no-belief: tooling]
  - 2026-11-02 partial: `9d63885bd` consolidated the 14 queue files into 3 (`model-evaluation-queue.md` EVL-02, plus INF-61 and INF-76 tracks); 206 tasks before/after, readiness-neutral. Residual: the 39 carved boxes from 18 files (`fold-list-1a.json` excluded.meq_carves_left_for_BRF-T1-MEQ), 7 of whose sources are batch-1 folds; they move after batch 1 lands.
  - 2026-11-03 residual done in `a01625aa3`: 31 of the 39 carved boxes moved verbatim (found by text through `.folded.json`) into 17 `## Track: meq-carve-<source>` sections of `model-evaluation-queue.md`, each gated like the unit it left; box/lint multisets and readiness unchanged. The 8 conversation-stack boxes (CS-8, CS-8.STT5/6/7/8, CS-8.LEX2, CS-22.V1, CS-26.LID1) stay in `speech-and-multimodal.md`: its in-file `## Dependency graph` is what blocks them, and moving them made all 8 dispatchable in a trial run.
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
  - 2026-11-03 T4 close-out (ws58): **NO VERDICT, the pilot never measured.** Rowflow shows the BUILD row `brf-exp01-trellis-build-20261102` as `done`, but its grant ended
    `rc=4 reason=job-rc-4:exited` at 22:10:33Z, 3 s in. Unit `plan-IQ2KT` (`llama-quantize --dry-run` IQ2_KT) returned rc=1 with `Missing importance matrix for tensor
    blk.0.attn_gate.weight in a very low-bit quantization`. The build job forced `--ignore-imatrix-rules` for IQ2_XXS only, and its smoke planned IQ4_KT only, so the smoke passed.
    No arm was built: `models/` is empty, there is no `BUILD-DONE.json` and the `*_SHA` pins are empty. So the MEASURE row `brf-exp01-trellis-pilot-20261102` was never published
    (rowflow `unknown`; no smoke was run). The watcher `post_build.sh` is still alive (started 2026-11-02 19:11Z) and polls for BUILD-DONE until about 19:11Z today, then exits 2.
    It was not re-run, because the build did not finish. Repaired in scratch (not run): `bin/build_job.sh` now forces IQ2_KT like IQ2_XXS, so the 2-bit pair stays like-for-like under
    the shared no-imatrix caveat. A failed unit no longer counts as done on resume. Backup: `build_job.sh.bak-iq2kt-imatrix-20261103`.
    Residual: republish the BUILD row as `-r2`; `post_build.sh` then publishes MEASURE with its smoke. [no-belief: no measurement produced]
  - 2026-11-03 republish (ws58, BRF-T4 follow-up): BUILD row `brf-exp01-trellis-build-20261102-r2` published (`priority_rank` 1, smoke PASS on 0-3, estimate 5700 s, min-window 6000 s). Root cause fixed: IQ2_KT (and IQ2_XXS) refuse to quantize without an importance matrix, and forcing `--ignore-imatrix-rules` would have produced garbage 2-bit arms, so the row now GENERATES the imatrix (unit `imatrix`: `llama-imatrix` on the Q8_0 source, pinned calibration `wiki.test.raw` sha256 `bfe9eb16ab99…`, 32 x 512 tokens, timeout 3000 s, about 1800 s counted in the estimate) and every arm is quantized with that one shared imatrix; `--ignore-imatrix-rules` is gone. The MEASURE row `brf-exp01-trellis-pilot-20261102` is NOT published yet. **Owner step: run `bash /mnt/raid0/llm/tmp/brf-exp01/bin/post_build.sh` once after the r2 build completes** (no watcher is armed; the stale r1 watcher pid 1371548 is not relied on). `post_build.sh` and `precond.sh` now refuse any `BUILD-DONE.json` not stamped `row=brf-exp01-trellis-build-20261102-r2`. The box stays open. [no-belief: no measurement produced]
- [ ] **BRF-T4-EXP04** [inference] EXP-04 crossover screen, riding a granted quiet window only. Owner: [`mi210-big-model-and-acceleration-roadmap.md`](mi210-serving-program.md#track-mi210-big-model-and-acceleration-roadmap) PF1 (executes as its box **PF1-EXP04**,
  row `brf-exp04-pf1-crossover-pilot-20261102-r4` (supersedes `-r3`, invalid on GPU arms; r1 smoke FAIL rc=3: bench_canonical rejected store binaries; r2 raw llama-bench GPU arms; r3 all arms via bench_canonical after research `99944fe12` store-identity fix), published by ws58 2026-11-02).
  Stop rule: manifest `sufficiency` EXP-04; stop on answer/futility; no window granted → not READY. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff (PF1-EXP04 filed with the owner's EXPAND/REVISE/INCONCLUSIVE review).
  - 2026-11-03 T4 close-out (ws58): **REVISE, screen, run INVALID on every GPU arm**, so not ticked. Rowflow `done` (rc 0, 22:59-23:07Z, 505 s of the 3600 s cap). The futility stop fired at
    block 0 with 4/8 units valid and capture completeness 0.75; 0 of 4 GPU cells are valid. Causes: (1) A2 never ran, because `llama-bench` rejects `-cmoe` (`error: invalid parameter for
    argument: -cmoe`; the bench spelling is `-ncmoe N`). The summary labels this a residency failure, but the cause is the argv. (2) A1 failed identity at both L. The process mapped the
    store's unversioned `gpu-20260921-ffc1bac82/bin/libggml-hip.so` (regular file, 68,101,784 B, mtime 2026-10-27, sha256 `daf086c2a805…`, **not in the store's SHA256SUMS**) next to
    the listed `libggml-hip.so.0.16.0` (`f26a166b8ea3…`). (3) A1@2K also had no placement proof, because RSS was still growing at exit under the 3 s cadence. Valid controls (n=1, no CI):
    A1-disabled/A0 = 0.859 at 2K and 0.959 at 8K. At 2K that diverges from A0 by more than 10%, which on its own is a REVISE trigger. Not evidence: A1 tps 453.9 and 420.6 against A0
    238.6 and 213.5 (about 1.9×). Those cells are identity-invalid, n=1, and carry no claim. OBSERVATION: research `99944fe12`, `/mnt/raid0/llm/tmp/brf-exp04/out/results.jsonl` sha256
    `02a9c611ffa3…`, `summary.json` = `PILOT-COMPLETE.json` `34d2264ccf9e…`, `IDENTITY.json` `f7567e34b7c9…`. [belief: cc]
  - 2026-11-03 republish (ws58, BRF-T4 follow-up): row `brf-exp04-pf1-crossover-pilot-20261102-r4`, `priority_rank` 1, published via `publish_row.py` (`ROWFLOW_REPO=/mnt/raid0/llm/views/epyc-root-main`). The GPU smoke is QUEUED for the next GPU gap; a queued smoke is not a FAIL and nobody polls it. Root causes fixed: (1) A2 argv `-cmoe` -> `-ncmoe 48`: the v10 store `llama-bench --help` spells it `-ncmoe, --n-cpu-moe <n>` (keeps the experts of blocks 0..n-1 on CPU; Q38FN `qwen4exp.block_count` = 48, so 48 is the all-experts-on-CPU shape `-cmoe` meant). A unit that never ran is now summarised as a run failure, not a residency failure, and two of them stop the pilot with that label. (2) The stray unlisted store `libggml-hip.so` is quarantined and the `libggml-hip.so -> libggml-hip.so.0` symlink restored (ws58; `verify_kernel_store.sh` clean). A pre-publish check of all four arms through `bench_canonical --dry-run` returned rc 0 with `kernel_store` identity and `ggml_linkage=PASS`; `SOURCE.sha256` re-pinned (`job.py` `d942a595c42a…`, `IDENTITY.json` `f7567e34b7c9…`). The r3 outputs are kept as `out/*.r3-invalid-20261103*`. The box stays open until the r4 run completes. [no-belief: no measurement produced]
- [x] **BRF-T4-EXP09** [inference] EXP-09 pilot. Owner: [`tool-output-compression.md`](context-and-token-economy.md#track-tool-output-compression) (TOC-SP-3). Stop rule: manifest `sufficiency` EXP-09. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
  Row `brf-exp09-pilot-20261102` (ws58; one CPU quarter, cap 45 min, own v10 kernel-store llama-server on :18409,
  worker Qwen3.6-35B-A3B-MTP-Q8_0, greedy, MTP off). Control = current `_spill_output` (orchestrator `3a428cb3`,
  executed unchanged). Corpus: 12 frozen failing logs, [`exp09-failing-log-corpus-manifest-20261102.json`](../../docs/design/backlog-refactor-2026-11/exp09-failing-log-corpus-manifest-20261102.json).
  - ✅ 2026-11-03 T4 close-out (ws58): **REVISE (harness), screen, not decision-grade.** The run was valid: the control `_spill_output` ran unchanged (fn sha `e1707a1b`), the planted mismatch
    was rejected in 9/9 verified-quote cells, linkage stayed inside the v10 store and the model sha matched. The predeclared futility look fired after 37 of 48 cells (22:19:44Z, 553 s;
    grant rc 75, partial): verified-quote 6.592 over 9 cells could not reach the control total of 9.717 over 12. Per-arm accuracy: control 0.81 (n 12), verified-quote 0.732 (9),
    shape-header 0.50 (8), pointer-only 0.271 (8, re-fetch 8/8). Retention: control 0.42, verified-quote 0.73, shape-header 1.00.
    By the box's rule this is neither EXPAND (verified-quote is below the control) nor STOP (verified-quote beat the control on item-04).
    **The futility is confounded:** all 5 parse failures are answers truncated at exactly 256 completion tokens, while the answer model was listing failed IDs (4 shape-header, 1
    verified-quote on item-07, which scored 0.0). On the 8 items where verified-quote parsed, it scored 0.824 against the control's 0.808 on the same items. On the 4 items where
    shape-header parsed, it scored 1.00 against the control's 0.875. Revise before expanding: raise the answer budget or cap the ID list, then re-run the pass.
    OBSERVATION: orchestrator `3a428cb3`, `/mnt/raid0/llm/tmp/brf-exp09/out/results.jsonl` sha256 `cb8f455daa1d…`, `identity.json` `67f41238d28e…`, `job.py` `f0196ae6be17…`. [belief: cc]
- [x] **BRF-T4-CAP04** [inference] CAP-04 reasoning-budget-curve pilot on the SERVED config, bounded at <=76 generations. Owner:
  [`reasoning-effort-levels.md`](context-and-token-economy.md#track-reasoning-effort-levels) (TB-1) (executing session ws58). Row `brf-cap04-pilot-20261102-v3` (v2 smoke FAIL rc=4: residency proof matched the store symlink path against /proc maps realpaths and a log line this build never prints; now realpath + SHA256SUMS-listed libggml-hip.so.0.16.0 only + KFD VRAM) (supersedes `brf-cap04-pilot-20261102`, whose critic ran thinking OFF and so did not describe the served model) on the MI210 `mi210_0,184-191`;
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
  - ✅ 2026-11-03 T4 close-out (ws58): **REVISE (budget derivation), screen, not decision-grade.** All 76 of 76 units ran (23:07-23:52Z, rc 0, about 45 min). The run was valid: 0 budget violations,
    0 frontdoor think leaks, 0 cases of critic thinking not engaged and 0 request errors. KFD VRAM was 41.9/43.3 GB (frontdoor/critic), only the SHA256SUMS-listed `libggml-hip.so.0.16.0`
    was mapped, `n_ctx_slot` was 34816 and the template sha matched. **The nested-prefix derivation failed its own check:** 0/4 fresh 8192 CHK generations matched the 32k base as an
    equal or prefix string. Sampling at temp 0.3/0.1 with speculative decoding does not reproduce across launches. So `nested_derivation_valid=false`, and by the predeclared rule
    every derived 8k/16k TB cell and the X@8k cells do not count. That is the manifest REVISE condition ("resume conflates budgets"). **TB-4 is therefore UNCOVERED, not
    "COVERED (screen)"**, and TB-1, TB-2 and TB-3 have no valid knee. Valid fresh 32k cells: frontdoor olympiad 0.50 (20/20 finished, 2386 mean tokens); critic olympiad 0.25 overall
    and 0.30 finished-only, with 2/12 truncated inside thinking (the critic does not finish within the 32k ceiling on about 17% of items); E frontdoor GPQA L2 0.95 vs L3 0.95,
    with 1 rescued and 1 harmed of 20 paired, at +1178 mean tokens for L3 (1343 to 2522). The critic look at 8 items said `continue` (32k truncation 0.25).
    OBSERVATION: `/mnt/raid0/llm/tmp/brf-cap04/job/out/results.jsonl` sha256 `81397b10396f…`, `summary.json` `9d2204432edc…`, `residency.jsonl` `eac2cda13f06…`. [belief: cc]
  - [ ] **CAP04-AG** [inference], NOT covered by this pilot: architect_general (87 GB, served on CPU). The pilot screens the curve shape on the served critic config only; architect_general is the expansion if a knee appears below the production ceiling (budget curve on its own served config, CPU, placement and thinking flags re-read from the registry at that time). Not READY until the pilot's result is recorded; est: provisional; Metric: accuracy, higher is better; Stop rule: manifest `sufficiency` CAP-04. Done when: either the pilot shows no knee below the production ceiling (recorded as an OBSERVATION: expansion not needed) or the architect_general curve stops on answer or futility at a checkpoint and is recorded as an OBSERVATION in the owner handoff.
    - 2026-11-03 (ws58): stays not READY. The pilot's verdict is REVISE, and it produced no valid sub-32k cell, so it neither shows nor excludes a knee below the production ceiling.
- [ ] **BRF-T4-R** [non-inference] NEEDS-OWNER Owner review of the four pilot results; promote or re-scope the 16 provisional packages.
  - 2026-11-03 partial (ws58): three of four pilots have verdicts. The review is below. Residual: EXP-01 has no verdict yet (build repair done; BUILD `-r2` then MEASURE).
    The promote or re-scope call on the 16 provisional packages waits for that verdict. [no-belief: review of recorded OBSERVATIONs]

### T4 owner review — 2026-11-03 (screens only; none is decision-grade)

Every verdict below is an operational screen under `docs/guides/agent-workflows/measurement-sufficiency.md`, never a gate result. It says whether the package is ready to EXPAND as the
experiment manifest defines it.

| Pilot | Verdict | Expand the package? | What must change first |
|---|---|---|---|
| EXP-09 spill / evidence retention | REVISE (harness) | Not yet. The control is verified and the mechanism fired, so the package is runnable. The futility stop is confounded by answer truncation at 256 tokens. On parsed cells verified-quote is level with the control (0.824 vs 0.808). | Raise the answer budget or cap the ID list, then re-run the 12-log pass. The manifest's EXPAND (full corpus) follows only if verified-quote ≥ control there. REPL-EMB-3.2 still needs the online arm. |
| EXP-04 CPU/GPU prefill crossover | REVISE (run invalid on GPU arms) | No. 0/4 GPU cells are valid, so PF1 is not testable at 2K/8K. The screen never yields a negative PF1 verdict. | Fix A2's argv (`-ncmoe`). Resolve the unlisted `libggml-hip.so` in the frozen v10 GPU store bin (an operator matter, because the store is frozen). Lengthen the placement-proof window for A1. Then re-run the pilot in a granted quiet window before the r=5 matrix. |
| CAP-04 reasoning budget curve | REVISE (budget derivation) | No. The validity checks pass, but the nested-prefix derivation failed 0/4. The budget axis is unmeasured, TB-4 is uncovered and CAP04-AG stays not READY. | Generate fresh at each budget, as the manifest's "generate at EVERY budget" requires. Or predeclare a distributional (not bitwise) equivalence test. Then re-screen before expanding to all stack models × 5 budgets. The 32k E cells already screen E-2/E-3: L3 buys no accuracy for +88% tokens (n 20). |
| EXP-01 trellis speed pair | NO VERDICT | Undecidable. No arm was built. | BUILD `-r2` with the repaired job, then MEASURE through `post_build.sh`. |

## T5 — D7 decision-package delivery

- [x] **BRF-T5-1** [non-inference] Write the 158 per-handoff option sheets (options + tradeoffs + recommendation) from the task manifest, in fold order. Done when: all 158 sheets are committed under `docs/design/backlog-refactor-2026-11/`.
  ✅ 2026-11-02 `4d6ea0b3d`: all 158 accounted for in `decision-packages/` (26 destination packages + `index.json`, fold-list-1a order): 119 delivered; 39 excluded with reasons (26 decided/issued authorization, 11 merged, 2 not an operator choice). [no-belief: tooling]
- [x] **BRF-T5-2** [roll-up] Non-dispatchable parent. Deliver each package via the decision tool at its fold; record the answer in the
  owning handoff. A dismissed question pauses only its own item.
  - 2026-11-03: all 119 choices delivered via the decision tool and recorded (decisions-batch1-20261102.json, decisions-batch2-4-20261102.json, 722e84092); ratify bundle shelved by operator (172ba99ed). [no-belief: operator decisions recorded]

## T6 — staged lint enforcement (D6)

- [x] **BRF-T6-1** Bind `task_lint.py migrate` in the fold commit gate and `task_lint.py publish` in rowflow publish.
  ✅ 2026-11-02 `4d6ea0b3d`: publish leg in `publish_row.py` (installed to `compute-flags/bin/rowflow/`, cmp 3/3); migrate leg = the exact command in the gate section above. Tests 9/9 new, rowflow 58 pass + 1 known failure. [no-belief: tooling]
- [x] **BRF-T6-2** [non-inference] Add `task_lint.py` to `index_state.py --check` as warn-only. `3e2b99bb5` — TASK-LINT column on stderr, exit code untouched. [no-belief: tooling]
- [x] **BRF-T6-3** [non-inference] Make the lint blocking in `--check` and in wrap-up once BRF-T7-1 is ticked. Done when: `--check` exits non-zero on an untagged lint failure (test).
  - 2026-11-03: DROPPED by operator decision (decision tool): the check stays binding at row publish (BRF-T6-1) and warn-only in `--check`; no commit-time blocking. [no-belief: operator scope decision]

## T7 — 1b folds (63 → 29)

- [ ] **BRF-T7-1** [roll-up] Non-dispatchable parent. After BRF-T2-1 lands: one fold commit per 1b fold through the atomic gate
  (readiness diff replaced by per-track readiness equality); add a box per fold before starting it.
  - [x] **BRF-T7-F1** fold fable5-window2-findings-03-portfolio-and-master-queue, autokernel-cross-workload-keep-gate, autokernel-all-devices-all-dimensions → `kernel-champion-and-promotion.md` (rename of autokernel-champion-aggregate.md, rows EVL-21, INF-75, INF-81 → INF-65; 8 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F2** fold heterogeneous-slot-fabric-residency, kv-unified-stack-rollout → `kv-cache-program.md` (rename of kv-prefix-fork-and-paged-attention.md, rows INF-23, RTG-57 → RTG-58; 3 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F3** fold numa-prefill-decode-disaggregation → `mi210-serving-program.md` (rows INF-44 → INF-22; 7 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F4** fold dflash2-block-drafter-experimental-build → `speculative-decoding.md` (rename of speculative-decoding-mtp-refresh.md, rows INF-62 → INF-50; 2 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F5** fold agent-collab-rnd-harness, autokernel-rebuild-program, autokernel-unified-surface-program, autokernel-concurrent-target-coordination, autokernel-orchestrator-actor-backend → `autokernel-loop.md` (rename of autokernel-research-loop.md, rows INF-02, INF-66, INF-73, INF-74, INF-78 → INF-06; 7 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F6** fold repl-turn-efficiency, harness-improvement-loop, repl-embedding-retrieval, agentic-serving-harness-fixes → `harness-program.md` (rename of harness-selection-and-integration.md, rows EVL-37, UFH-08, UFH-12, UFH-14 → UFH-01; 7 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F7** fold attention-matching-kv-compaction → `long-context-program.md` (rename of yarn-context-extension-research.md, rows INF-05 → INF-59; 5 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F8** (BRF-T7-MEQ) fold gpu-candidates-surface-qwen38-update, paw-compiled-specialists → `model-evaluation-queue.md` (rows INF-61, INF-76 → EVL-02; 31 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F9** fold sarathi-serve-cpu-evaluation, moe-routing-tap-and-locality-measurement → `cpu-decode-roofline-program.md` (rows INF-49, INF-72 → INF-70; 5 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F10** fold reboot-gated-inventory-and-staging, contention-model-device-and-load-axes-rider → `numa-placement-and-contention.md` (rows EVL-49, RTG-07 → INF-45; 8 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F11** fold coordinator-role-failure-modes-and-refactor, loop-owned-fleet-implementation → `coordination-and-churn-pipeline.md` (rows RTG-48, RTG-52 → RTG-34; 8 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F12** fold autopilot-sequential-allocation → `autopilot-program.md` (rows EVL-04 → RTG-02; 14 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F13** fold agentic-rocm-kernel-authoring, gemma-challenge-kernel-techniques-v7 → `rocm-kernel-authoring.md` (rename of rocm-verify-profile-backend.md, rows INF-03, INF-16 → INF-48; 6 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F14** fold dev-harness-trace-mining → `memory-program.md` (rows EVL-52 → EVL-10; 4 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F15** fold reviewer-escalation-and-human-gate-policy, reviewer-latency-and-sampling-budget, reviewer-model-ablations → `reviewer-control-plane.md` (rename of glm52-reviewer-capability-gates.md, rows REV-05, REV-06, REV-07 → REV-02; 6 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
  - [x] **BRF-T7-F16** fold routing-intelligence → `routing-program.md` (rows RTG-30 → RTG-09; 9 tracks). ✅ 2026-11-03 — readiness-neutral per track, zero lost tasks; records in the commit message. [no-belief: refactor-move]
- [x] **BRF-T7-MEQ** Merge the 3 model-evaluation queue files into 1 (D2). ✅ 2026-11-03 `08298a109` (BRF-T7-F8) [no-belief: tooling]

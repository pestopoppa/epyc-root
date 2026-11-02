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
- [ ] **BRF-T1-MEQ** [non-inference] Split the model-evaluation queue into 3 gate-homogeneous files (D2), through the atomic gate.
- [ ] **BRF-T1-RET** Retire `swarm` and `model-stack-change-standardization-audit` (D4): move to
  `archived/`, retire IDs with `Repoint-Reason:` trailers and `.folded.json` entries.

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
- [ ] **BRF-T3-2** [non-inference] Run the zero-inference analyses over retained data; record results as OBSERVATIONs. Ticks on the source
  boxes wait for proven coverage of the cell. Stop rule: a cell without retained inputs covering it is
  marked uncovered and left open, never ticked.
  - 2026-11-02 partial (ws58): this pass ran the E5 adjudication (VALID 0 / INVALID 4 / UNRESOLVED 4), the KB G11 disagreement analysis (ticked G11) and the STT Nemotron re-read. No scorer or parser fix was needed. Not yet run: C6 consumer re-read, RPL-AP analyses (code builds), EXP-06 custody, LID1, CAP-01 Q38FN replay, CAP-06 threshold replay. See `progress/2026-11/2026-11-02-ws58-brf-t3.md`. [belief: cc]

## T4 — the 4 bounded pilots (D3)

Each pilot carries its `sufficiency` block from the experiment manifest; owners are the accountable handoffs from the experiment manifest (written 2026-11-02, BRF-T1-0 session).
The 16 other packages stay provisional until owner-reviewed pilot results exist.

- [ ] **BRF-T4-EXP01** [inference] EXP-01 speed-pair pilot. Owner: [`iqk-iquant-enablement.md`](iqk-iquant-enablement.md)
  (INF-26, per v6 and the experiment manifest: T2/T3 hold the executable KT gates; [`tq3-quantization-evaluation.md`](tq3-quantization-evaluation.md) STEP 2/3 are consumers and record the transfer).
  Stop rule: manifest `sufficiency` EXP-01 — pair against the completed control first; stop on answer or
  futility at each checkpoint; quality pass not reducible (gate stays open). Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
- [ ] **BRF-T4-EXP04** [inference] EXP-04 crossover screen, riding a granted quiet window only. Owner: [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (PF1).
  Stop rule: manifest `sufficiency` EXP-04; stop on answer/futility; no window granted → not READY. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
- [ ] **BRF-T4-EXP09** [inference] EXP-09 pilot. Owner: [`tool-output-compression.md`](tool-output-compression.md) (TOC-SP-3). Stop rule: manifest `sufficiency` EXP-09. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
- [ ] **BRF-T4-CAP04** [inference] CAP-04 reasoning-budget-curve pilot, bounded at 200 generations. Owner:
  [`reasoning-effort-levels.md`](reasoning-effort-levels.md) (TB-1) (executing session ws58). Row `brf-cap04-pilot-20261102` on the MI210 `mi210_0,184-191`;
  est: provisional; pilot: bounded 200 items, 2.5 h cap (expected ~2 h). Metric: accuracy, higher is better. Identity: frontdoor Qwen3.6-35B-A3B-MTP-Q8_0 (sha c1283d8b) + architect_critic Qwen3.8-27B-Q8_0
  (sha a680f44a), v10 kernel store 10303, own llama-server, chat path, enable_thinking=false, greedy, seed 42; 20
  olympiadbench_hard + 20 GPQA-Diamond-CoT pinned items (items sha 81ef522b). Cells, each generated fresh at its own
  budget: TB 2 models x {8k,16k,32k} x 20; E frontdoor x {L2,L3} x 20; crossed frontdoor x {L2,L3} x {8k,32k} x 10
  GPQA, so **TB-4 COVERED (screen)**. TB-1 reports BOTH denominators (overall, finished-only) plus truncation; a knee
  below the production ceiling settles TB-3 for that role only, never E-2/E-3.
  Stop rule: manifest `sufficiency` CAP-04 (exploratory; look at every cell; stop on answer or futility is an
  operational decision, never a gate result); STOP, deadline or cap gives a resumable partial; budget overrun,
  think leak or short slot context is INVALID. Done when: the pilot stops on answer or futility at a manifest checkpoint and its result is recorded as an OBSERVATION in the owner handoff.
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

# Stage C build brief — handoff standard: proposals, done-when at tick, holds, compaction, index hand-row drop, ratify package

Scope: `HANDOFF-STANDARD.md` §3/§4/§5/§6, "Indexes" I.2(d)/(e), "AK audit items absorbed"; operator decisions 1–6; Stage B review findings (2026-11-20). Baseline: origin/main `e5784a93f`. Every change below names its writers, readers, the exact edit, and the wiring-audit row that proves it (a test in `scripts/handoffs/tests/` or `tests/coordination/`, or a real run recorded in the Stage C progress file). **Nothing lands as content only**: a Stage C commit that changes a format or a rule and does not update every reader/writer in its row is incomplete.

Operator requirement (2026-11-20): for each change list writers + readers, the exact edit, and a proven wiring row. The audit table at the end must be complete before Stage C is declared done.

## C0 — Stage B defects Stage C inherits (fix first, same lane)

| # | Defect (evidence) | Fix |
|---|---|---|
| C0.1 | `generated_next_action` (`index_state.py:653-673`) picks the first open, un-gated box and ignores `lint.ok`, `inputs_missing`, `outside_backlog`, holds: 4 of 5 spot-checked generated rows name non-dispatchable boxes (INF-50 `G3` lint-fail question, INF-79 `S-18` lint-fail, INF-06 `AK-RSM-1` in an operator-held file, INF-80 `T2` with 0 admissible boxes rendered as a task) | One predicate: `taskflow/select.candidates()` becomes `box_index.dispatchable(rec, holds)` and both `select.py` and `generated_next_action` call it; "no admissible box" renders `NEEDS-OWNER: n` / `BLOCKED:` / `FROZEN`, never a lint-failing box. Test: fixture file whose first open box fails lint → generated cell names the second; file with zero admissible → `NEEDS-OWNER: n`. |
| C0.2 | `box_index.load()` rebuild path runs `index_state.py --box-index` = the full state build (`last_advanced` pickaxe, vidya ledger import): **54 s** in the scratch tree (build() alone 7 s, not "4 s"); no lock, 300 s timeout, result `{}` on any failure, and `publish_row.py:403-439` calls it inside the publish path whenever *any* handoff mtime moved | `--box-index` must call `box_index.build()` only (no `build_state`, no ledger import); `load()` takes `flock` on `.box-index.json.lock`, returns the stale copy with `"stale": true` instead of `{}`, and callers (publish_row, select, stale_next_action) log `box-index stale/unavailable` rather than silently seeing zero boxes. Budget: rebuild ≤ 10 s on the real repo, measured in the progress file. Test: concurrent `load()` ×3 → one build. |
| C0.3 | `/log` child body (`worker_checkpoint.py:297-302`) is a new open box with no `done when` and no `NEEDS-OWNER` → fails the now-enforced diff gate when staged, and is never dispatchable | Child carries `· done when: resume — <resume_action>` and `· gate: <parent ID>`; test in `tests/coordination/test_worker_checkpoint.py`. |
| C0.4 | Dashboard (`dashboard/handoff_parser.py`, `panels.py`) and `backlog_row_check` inside `index_state` (`use_box_index=False`, `:480`) do not read `.box-index.json`; the "every consumer wired" claim excluded them | Dashboard reads `counts` (`open/blocked/frozen/needs-owner/outside_backlog`) from `box_index.load(regenerate=False)` with a staleness badge; `index_state` keeps `use_box_index=False` by design (it is the producer) — document that in the audit table instead of claiming wiring. |
| C0.5 | `select.EXCLUDE_FILES` (`select.py:42-43`) hardcodes six held files; `holds.yaml` does not exist | Replaced by C3 below. |
| C0.6 | Lint-OK after the mechanical pass is 20.3 % of open boxes (293/1,338), not 45 %: the pass cannot author `done when` (first lines are immutable, continuation fields need judgment) | C1 (proposals) is therefore load-bearing for the Stage C success criterion; the 45 % target moves to C1's canary, not to migration mechanics. |

## C1 — LLM rewrite proposals as NEEDS-OWNER children (decision 6)

**Change.** `scripts/handoffs/propose_rewrites.py`: for each open box with `lint.fails ⊇ {a}` or `{e}` or `{s}` in a file ordered by `backlog-priority.json` rank, one low-tier turn (`gpt-5.6-luna` / `haiku`, effort low, `engine_flags` from `token_guards`) receives the box's `own_block`, heading chain and 20 lines of context and returns JSON `{done_when | split:[{id,text,done_when}] | stop_rule, rationale}`. The script writes, via `handoff_box.py add --needs-owner --after <ID>`, a child `**<ID>.p1** [<class>] <proposed text> NEEDS-OWNER · done when: … · proposed-by: taskflow <ts> · gate: <ID>`; it never edits the parent. Budget ≤ 30 k uncached tokens per box, ≤ 900 boxes, ≤ 30 M tokens total (standard §6 step 3); stops when the skip-reason histogram shows `needs-owner` > 20 % of admissible boxes in the top-10 rows.

**Writers touched.** `handoff_box.py` (new `--proposed-by`, `--parent` fields; `split` reuse). **Readers touched.**
- `agents/commands/wrap-up.md` Step 2: new sub-step "Proposals": list `NEEDS-OWNER` children under boxes you own (`box_index` state `needs-owner`, `proposed-by` set); **accept** = delete the `NEEDS-OWNER` token (the child becomes the dispatchable unit; tick the parent only when all children are done); **edit** = change the child's continuation fields, never its first line (identity); **reject** = `handoff_box.py reject <ID>` which moves the child to `## History` with `[declined: <who> <date> <reason>]` (the belief-capture D1 form). Wiring row: `test_wrapup_proposals.py` (accept/edit/reject fixtures) + one real wrap-up on a migrated handoff recorded in progress.
- `.claude/skills/research-intake/SKILL.md` Stage 3 item 2 / Stage 4: every emitted box must pass `task_lint.py dispatch` (class tag, `done when`, `gate:`, `inputs:` with existing paths); the Stage 4 applier runs `dispatch` on the new lines and refuses the plan otherwise, so intake never produces a box that needs a proposal. Wiring row: `scripts/research/tests/test_intake_box_lint.py` with a fixture plan.
- `index_state.py`: `.index-state.json` and the generated rows gain `needs_owner` and `proposals_pending`; `--check` warns when a file has proposals older than 14 days. Dashboard (`handoff_parser.py`, `panels.py`, `static/handoffs.html`) shows the counts. Wiring row: `tests/test_index_state_box_counts.py` + dashboard unit test.
- `taskflow/select.py`: `state == "needs-owner"` and any box carrying `proposed-by` are skipped (already in the histogram as `state-needs-owner`; add `proposal-pending`). Wiring row: `tests/coordination/test_taskflow_select.py`.
- `box_index.py`: `needs_owner`, `proposed_by`, `parent` fields.

**Canary.** Acceptance rate ≥ 50 % on the top-10 rows within one week; lint-OK ≥ 45 % of open boxes in those files (replaces the Stage B target).

## C2 — B13: done-when checked at tick time

**Change.** `scripts/handoffs/done_when.py`: parse `· done when:` into one of `{cmd: <shell>, file: <path>[#field], verdict: <PASS|FAIL|number regex>, artifact_class: <loop-built kernel | registered recipe | row PASS | …>, free}`; `check(box, evidence) -> ok | fail(reason) | unchecked`. **Writers touched (all three tick paths).**
- `churn/wrapup.py`: before `apply_ticks`, for each tick resolve the box, run `done_when.check` with the record's `verdict`/`paths`/`evidence`; `fail` refuses the whole wrap-up with the box text and reason; `unchecked` (free-text done-when) proceeds and records `done_when: unchecked` in `report.json`. New `--evidence <json>` field in the turn record.
- `worker_checkpoint.py` (`/log completed`): same check on the exact box; `blocked|partial` never tick so unaffected.
- `churn/file_result.py`: a row's tick line must satisfy the box's `done when` when it is `verdict:`/`file:`/`artifact_class:`; a mismatch files the result but **does not tick** and emits a `tick-refused` alert to the owner.
- Artifact-class rule (AKX-ALL-14, reopened `55b5733c1`): when the done-when names a class, the evidence must name an artifact of that class (`kernels/production/*` is never "loop-built"; a `champion`/`ak-*` build receipt is).
**Readers touched.** `agents/commands/wrap-up.md` Step 2 gains the rule ("a tick is refused when the box's done-when is machine-checkable and the evidence fails it; write the evidence paths in the record"); `belief_capture_check.py` T4 reads the unified verdict field (chunk-1 parse_tick); `DESIGN.md` §2.5 verifier calls the same `done_when.check`. Wiring rows: `test_done_when.py` (the audit fixture: `done when: keep record has gpu_build_receipt.proven and recipe registered before build`; tick naming `kernels/production/gpu` → refused; loop-built → accepted), `test_churn_wrapup.py`, `test_worker_checkpoint.py`, `test_churn_file_result.py`.

## C3 — holds.yaml as the single source (decision 3, B4)

**Schema** `handoffs/active/holds.yaml`: `holds: [{id, scope: loop-launch|all-rows|boxes, targets: {handoffs:[], rows:[], boxes:[], owners:[], row_prefixes:[]}, since, by, reason}]`. **Writers.** The operator (ratify-signed) and `handoff_sessions.py gate/unpark` (which now *write* holds.yaml entries instead of registry `operator_gate`); `handoff_migrate.py` one-shot: today's 12 registry gates → `scope: loop-launch`, `DEFAULT_GATED_ROW_PREFIXES` → `row_prefixes` entries, `select.EXCLUDE_FILES` → `handoffs`. **Readers (all derive, none keep a private list).**
- `publish_row.check_operator_gate` (`:322-345`): refuse by the row's own `owner` ∈ targets.owners, or `handoff_task` ∈ targets.handoffs with `scope: all-rows`, or id prefix ∈ row_prefixes; **coordinate with F4** (`AK-REQS-FIXES.md`) — F4 lands the admission rule, C3 lands the file and the derivations; one of them owns `check_operator_gate` and the other only adds a reader test.
- `handoff_sessions.py` `is_gated`/`operator_gate` (`token_guards.py:193-221`): read holds.yaml; registry field becomes a cache written by the same code path.
- `taskflow/select.py`: `EXCLUDE_FILES` deleted; `holds` on the record (already emitted by `box_index.load_holds`, add `scope`).
- `backlog_row_check.classify`: a held box/file → `refuse` with the hold id (replaces the DO-NOT-DISPATCH prose heuristic for operator holds).
- Dashboard: holds column per handoff; `index_state --check`: `BAD HOLD` for a target that resolves to nothing.
Wiring rows: `test_publish_row_holds_scope.py` (audit acceptance: `akagg` held `loop-launch`; `owner: autokernel` → PUBLISHED, `owner: akagg` → REFUSED naming the hold), `test_taskflow_select.py` (held file yields zero), `test_token_guards.py` (gate derived from file), real run: `handoff_sessions.py status` shows the same 12 gates from the file.

## C4 — compaction and splits under the new limits (decision 4)

**Change.** `scripts/handoffs/handoff_compact.py`: ticked boxes older than 30 days → one summary line per track under `### Done` (`**<ID>** ✅ <date> <verdict>` only), prose older than 30 days → `## History` or `handoffs/archived/<slug>-history-<date>.md`; refuses when `closure_audit.py` reports unverified code refs in the boxes it would fold. `scripts/handoffs/new_handoff.py <slug> --row <ID> --domain <d>` renders §2.1 from the intake stub template. `handoff_box.py split-file --track <T> --to <new-slug>` moves a whole track into a new handoff (standard §2.3: > 6,000 lines or > 3 tracks) and `split` for boxes > 24 continuation lines. **Repointing (new).** Every move writes `handoffs/active/.moves.jsonl` (`{box_id, text_sha, from, to, at}`); `publish_row.py` stores `handoff_task_sha` (= `text_sha`) at publish and resolves `handoff_task` by `(sha)` first, path second, consulting `.moves.jsonl`; `rowflow.py` `handoff_task` readers (`handoff_ref.py`, `file_result.py`, `backlog_gen.py`) use the same resolver. Index links: `index_state` regen rewrites `[old.md]` links to the new file in the generated rows and `--check` flags a hand row pointing at a moved track. **Readers.** `wrap-up.md` Step 2 (compaction only in the operator-invoked sweep, CLAUDE.md cadence), `handoff-index-authoring.md` §2.3 limits, dashboard size badge from `limits`. Wiring rows: `test_handoff_compact.py`, `test_handoff_box_split_file.py` (zero first-line changes, `.moves.jsonl` written), `test_publish_row_handoff_task_sha.py` (a row published before a move still resolves), real run on the 9 files > 4,000 lines recorded with before/after line counts.

## C5 — B10 hub-only regeneration, B11 diff-scoped row checks

**Change.** The regen of `.index-state.json`, `.index-graph.json`, master rollup and generated rows runs only in `scripts/dashboard/refresh_hub_view.sh` (hub) and a post-merge job on `origin/main`; `index_state.py` (no flags) refuses to write when `$EPYC_INDEX_WRITER != hub` and prints the hub command. `--check`: `FRESHNESS` for a stale generated block is a **warning** for a commit that does not touch the generated files; `PROSE`, `BAD DEP`, dead link hard-fail only for rows in the commit's diff (`task_lint.added_lines` mechanism, now row-aware), warn elsewhere. **Writers/readers.** `wrap-up.md` Step 3 drops the regen under the lease (keeps `--check`); `wrapup.py` (Codex) unchanged; `check_commit_hygiene.py` refuses a session commit that adds `.index-state.json`/`.index-graph.json` hunks; dashboard reads the hub-regenerated files (unchanged path). Wiring rows: `test_index_state_diff_scoped.py` (audit acceptance: 156-char `Next action` on row X; commit touching only row Y passes; touching X fails), `test_index_state_writer_guard.py`, real run: two lane pushes 5 s apart land without an index conflict (log the SHAs).

## C6 — index hand-row drop (Indexes I.2(b)-(d))

**Criteria (all three, measured over 7 consecutive days by `stale_next_action.py --compare-generated`, new flag):** (1) generated `Next action` agrees with or is strictly fresher than the hand cell for ≥ 90 % of rows; (2) zero generated cells name a lint-failing box (after C0.1); (3) every active handoff carries `**Row**`/`**Domain**` headers (`--check` error otherwise). Then: `index_state.py --drop-hand-rows` deletes the hand tables, the generated table becomes the only table, a hand-written row is a `--check` error. **Writers/readers.** `wrap-up.md` Step 3: "Next action refresh" and "delete the row on completion" are replaced by "edit `**Row**`/`**Domain**`/`**Status**` in the handoff header; the row is generated"; pruning keeps `index_state` `prune.candidate`. Owning-session-applies wording (ruling (b)): "adding, deleting or re-pointing a row" → "editing the handoff's `**Row**`/`**Domain**` header or Status"; a subagent may still prepare. `stale_next_action.py` reports hand-vs-generated disagreement until the drop, then retires. `backlog_priority.py` reads rows from `.index-state.json` (already) — verify it does not parse the hand tables. Research-intake Stage 4 item 4: "one index row per new stub" → "`**Row**`/`**Domain**` header in the stub; the row is generated". Wiring rows: `test_index_state_generated_only.py`, `test_backlog_priority_no_hand_rows.py`, intake plan fixture.

## C7 — marker retirement and one suffix (decision 1) + ratify package

**Code.** `backlog_row_check._boxes` (`:196-206`) and `_BOX` (`:209`) accept `[ ]`/`[x]` only and *report* `[~] [>] [!]` as `LEGACY-MARKER` (counted, never dispatchable); `task_lint_core.CHECKBOX` (`:24`) same; `handoff_migrate.py` rewrites the 0–N legacy markers in active files to `[ ]` + `· frozen until:`/`NEEDS-OWNER` (count them first; none appeared in the Stage B scan); `dashboard/handoff_parser.py` `BOX_MARKER` matches only the two states; `flip_checkbox.parse_tick` keeps accepting legacy suffix forms (chunk 1) — readers only, writers already unified. Wiring rows: `test_backlog_row_check_markers.py`, `tests/test_handoff_parser.py`.

**Ratify package (human-only, `check_trust_boundary_edit.sh` / `human_only_paths.yaml`).** One script `scripts/operator/ratify_handoff_standard_20261120.sh` that applies, in one run:
1. `agents/shared/SESSION_LIFECYCLE.md` Two axioms: markers `[ ]`/`[x]` only; one tick suffix `✅ <date> [belief: …|no-belief: …] <verdict>` written by `wrapup.py`/`/log`/`file_result` through `flip_checkbox`; "nonterminal outcomes add a child" cites the C0.3 child form; the belief sentence cites `.box-index.json` as the planners' read path.
2. `agents/shared/OPERATING_CONSTRAINTS.md` → *Dispatching Backlog Work*: identity = the box's first line (`text_sha`), `file:LINE` a hint, the screener's source is `.box-index.json` + `holds.yaml`; ruling (b) wording per C6.
3. `CLAUDE.md` § Handoff Workflow: thin rows are generated; sessions edit handoff headers and boxes; `--check` is diff-scoped; `holds.yaml` is the exclusion source.
4. `agents/shared/INVARIANTS.md` only if invariant 9's wording needs the dispatcher-under-owning-identity clause.
Requirements (memory `feedback_ratify_scripts_must_be_apply_tested`, `feedback_human_only_paths_need_ratify_script`): the script is **dry-applied through the real hooks** in a fresh worktree from `origin/main` before it is offered (`check_instruction_surface_ratified.py`, `check_trust_boundary_edit.sh`, `agents_schema_guard.sh`, `agents_reference_guard.sh` all exit 0, log attached), carries the `ratification_receipt.py` receipt, and is handed to the operator as **ONE single-line command** (`bash scripts/operator/ratify_handoff_standard_20261120.sh`) with the diff in the package dir; no hand-holding steps. Nothing in C7's code path depends on the package landing first (readers accept both forms), but C6's hand-row drop and C3's registry derivation wait for it.

## C8 — taskflow consumer

`select.py` consumes C0.1's shared predicate, C1's `needs-owner`/`proposed-by` skip, C3's holds, C4's `.moves.jsonl` (a box that moved keeps its `text_sha` key), C2's `done_when.check` in the verifier (DESIGN §2.5). `extract.py` (DESIGN §2.2) reads heading chain + own_block from `box_index` records. Wiring row: `test_taskflow_select.py` extended per item; the Stage 1 canary in `DESIGN.md` §3 (≥ 10 verified boxes/24 h, ≤ 2 M uncached tokens per verified box) is run once Stage C lands and recorded.

## Order and gates

C0 → C3 (with F4) → C2 → C1 → C5 → C4 → C7 code → ratify package (operator) → C6 drop (after the 7-day criteria) → C8 canary. Each step: tests green, `index_state.py --check` exit 0 on origin/main, wiring rows filled, progress entry with the measured numbers (lint-OK %, build seconds, proposal acceptance).

## Wiring-audit table (Stage C fills every row; "n/a" needs a reason)

| Surface (from HANDOFF-STANDARD §1) | Role | Stage C change(s) | Proof (test / real run) | Status |
|---|---|---|---|---|
| `docs/guides/agent-workflows/handoff-index-authoring.md` | docs | C4 limits, C6 header contract, C7 markers | review diff | |
| `agents/shared/SESSION_LIFECYCLE.md` | human-only | C7 ratify (markers, suffix, child form) | hook dry-apply log | |
| `agents/shared/OPERATING_CONSTRAINTS.md` | human-only | C7 ratify (identity, screener source, ruling (b)) | hook dry-apply log | |
| `CLAUDE.md` § Handoff Workflow | human-only | C7 ratify | hook dry-apply log | |
| `agents/shared/INVARIANTS.md` | human-only | C7 (only if needed) | — | |
| `agents/commands/wrap-up.md` Step 2 | writer | C1 proposals step, C2 done-when rule | fixture wrap-up run | |
| `agents/commands/wrap-up.md` Step 3 | writer | C5 no regen, C6 header-not-row | fixture wrap-up run | |
| `.claude/skills/research-intake/SKILL.md` Stage 3/4 | writer | C1 lint-passing boxes, C6 header not row | intake plan fixture test | |
| `.claude/skills/row-owner-loop/` (AK, 720768eb0) | writer | C2 tick rule, C3 holds | review | |
| `scripts/handoffs/index_state.py` | producer | C0.1, C0.2, C1 counts, C5 writer guard + diff-scoped rows, C6 drop | tests listed | |
| `scripts/handoffs/box_index.py` | producer | C0.2 lock/stale, C1 fields, C3 scope, C4 moves | tests listed | |
| `scripts/handoffs/task_lint.py` / `task_lint_core.py` | lint | C7 markers, C2 done-when grammar | tests | |
| `scripts/handoffs/handoff_box.py` / `new_handoff.py` / `handoff_compact.py` / `handoff_migrate.py` | writer | C1, C4, C7 | tests | |
| `scripts/handoffs/propose_rewrites.py` | writer | C1 | test + budgeted real run | |
| `scripts/handoffs/stale_next_action.py` | reporter | C6 compare-generated | test | |
| `scripts/handoffs/backlog_priority.py` | producer | C6 (no hand-row parsing) | test | |
| `scripts/handoffs/belief_capture_check.py` | gate | C2 verdict field | test | |
| `scripts/handoffs/verdict_count.py` / `build_handoff_timeline.py` / `duplicate_task_scan.py` / `closure_audit.py` | readers | C7 markers, C4 compaction input | tests | |
| `scripts/coordination/flip_checkbox.py` | primitive | none (chunk 1 done) | existing tests | |
| `scripts/coordination/churn/wrapup.py` | writer | C2 done-when, `--evidence` | test | |
| `scripts/coordination/worker_checkpoint.py` (/log) | writer | C0.3 child form, C2 | test | |
| `scripts/coordination/churn/file_result.py` | writer | C2 tick refusal + alert | test | |
| `scripts/coordination/rowflow/publish_row.py` | reader | C0.2 stale handling, C3 holds (with F4), C4 `handoff_task_sha` | tests | |
| `scripts/coordination/rowflow/rowflow.py` / `handoff_ref.py` / `backlog_gen.py` | readers | C4 resolver | test | |
| `scripts/coordination/backlog_row_check.py` | reader | C3 holds, C7 markers | test | |
| `scripts/coordination/handoff_sessions.py` / `token_guards.py` | reader/writer | C3 gates derived from holds.yaml | test + real `status` run | |
| `scripts/coordination/taskflow/select.py` | reader | C0.1, C1, C3, C4, C8 | test | |
| `dashboard/handoff_parser.py` / `panels.py` / `server.py` / `static/handoffs.html` | reader | C0.4 counts + staleness, C1 needs-owner, C3 holds, C7 markers | dashboard unit tests + hub screenshot | |
| `scripts/dashboard/refresh_hub_view.sh` | hub writer | C5 only writer of generated files | real run log | |
| `scripts/hooks/check_commit_hygiene.py` | hook | C5 refuse generated-file hunks (separate hooks D9) | test | |
| `coordination/session-bus/human_only_paths.yaml` | trust boundary | none (verify handoffs stay agent-editable) | read | |
| `handoffs/active/holds.yaml` | new source | C3 | schema test | |
| `handoffs/active/.moves.jsonl` | new source | C4 | test | |
| `handoffs/README.md` | docs | lifecycle text per §3 | review | |
| `DESIGN.md` §2.1/2.2/2.5 | consumer | C8 | canary run | |
